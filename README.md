# LLM Tagger API

Automated text tagging service for repair notes using a hybrid rules engine + LLM pipeline. Designed for high throughput (17k req/sec) with deterministic rules running fast and an LLM layer for complex, ambiguous cases.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [How the Pipeline Works](#how-the-pipeline-works)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Configuration & Environment Variables](#configuration--environment-variables)
- [Getting Started](#getting-started)
- [All Commands Reference](#all-commands-reference)
- [Running Tests](#running-tests)
- [Observability](#observability)
- [Database Migrations](#database-migrations)
- [LLM Providers](#llm-providers)

---

## Architecture Overview

```
                        ┌─────────────────────────────────────────────┐
                        │                FastAPI App                   │
                        │   POST /tag  GET /taxonomy  CRUD /rules      │
                        └──────────────────┬──────────────────────────┘
                                           │
                        ┌──────────────────▼──────────────────────────┐
                        │              Orchestrator                     │
                        │  1. Load taxonomy from DB (Redis cached)     │
                        │  2. Invoke LangGraph pipeline                │
                        │  3. Persist results to tag_results table     │
                        └──────────────────┬──────────────────────────┘
                                           │
                        ┌──────────────────▼──────────────────────────┐
                        │           LangGraph Pipeline                  │
                        │                                               │
                        │  ┌──────────────┐     ┌──────────────────┐  │
                        │  │  Rules Engine │────▶│    LLM Chain     │  │
                        │  │  <1ms / note  │     │ (async, provider │  │
                        │  │  confidence=1 │     │  agnostic)       │  │
                        │  └──────────────┘     └────────┬─────────┘  │
                        │         │                       │             │
                        │         └──────────┬────────────┘            │
                        │                    ▼                         │
                        │             Merge & Deduplicate              │
                        │         (rules win on conflict)              │
                        └──────────────────────────────────────────────┘
                                           │
                        ┌──────────────────▼──────────────────────────┐
                        │              PostgreSQL (via pgBouncer)       │
                        │         asyncpg · async SQLAlchemy           │
                        └─────────────────────────────────────────────┘
```

### Tagging Modes

| Mode | Behavior |
|---|---|
| `RULES_ONLY` | Runs keyword/regex rules only. Deterministic, ~1ms/note. |
| `LLM_ONLY` | Skips rules, calls LLM for every note. |
| `HYBRID` | Rules run first. LLM fills the gaps. Results merged intelligently. |

Rules always win when the same tag is produced by both sources (confidence=1.0 vs probabilistic).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI + Uvicorn |
| Pipeline | LangGraph (state machine DAG) |
| LLM providers | Ollama, OpenAI, Azure OpenAI, Anthropic |
| LLM orchestration | LangChain |
| Database | PostgreSQL 16 + pgBouncer (connection pooler) |
| ORM | SQLAlchemy (async) + asyncpg driver |
| Migrations | Alembic |
| Cache / Queue | Redis (hiredis) + ARQ (async job queue) |
| Observability | Langfuse (LLM traces) + Prometheus + Grafana |
| Package manager | uv |
| Linter/Formatter | Ruff |
| Type checker | MyPy (strict) |

---

## Project Structure

```
llm-tagger-api/
├── src/tagging/
│   ├── config.py                    # Pydantic-settings config, validated at startup
│   ├── domain/                      # Business logic — no external dependencies
│   │   ├── tag.py                   # Tag entity
│   │   ├── tag_category.py          # Category grouping
│   │   ├── tag_rule.py              # Deterministic rule definition
│   │   ├── tag_rule_condition.py    # Condition within a rule (keyword/regex)
│   │   ├── tag_result.py            # Pipeline output (tag + confidence + source)
│   │   ├── note_context.py          # Pipeline input (note text + identifiers)
│   │   └── enums/                   # Enumerations (provider, source, mode, etc.)
│   ├── application/
│   │   ├── orchestrator.py          # Coordinates full tag_note() flow
│   │   ├── pipeline.py              # LangGraph state machine (3 nodes)
│   │   ├── rules_engine.py          # Keyword/regex rule evaluator
│   │   └── interfaces.py            # ITagRepository abstract interface
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── models.py            # SQLAlchemy ORM models
│   │   │   └── repository.py        # PostgreSQL implementation of ITagRepository
│   │   └── llm/
│   │       ├── factory.py           # Builds LLM client from config (provider agnostic)
│   │       ├── chain.py             # Prompt → LLM → JSON parse → filter
│   │       ├── prompts.py           # Loads prompt templates from .md files
│   │       └── templates/
│   │           ├── system.md        # System prompt (taxonomy context)
│   │           └── user.md          # User prompt (note text + instructions)
│   └── api/
│       ├── app.py                   # FastAPI app factory, middleware, routers
│       ├── dependencies.py          # Dependency injection (DB, repo, orchestrator)
│       ├── schemas.py               # Pydantic request/response models
│       └── routers/
│           ├── health.py            # GET /health
│           ├── tagging.py           # POST /tag
│           ├── taxonomy.py          # GET/POST taxonomy, categories, tags
│           └── rules.py             # Full CRUD for /rules
├── tests/                           # pytest test suite
├── alembic/                         # Database migration scripts
│   ├── env.py                       # Async Alembic config
│   └── versions/
│       ├── 032f68276466_create_taxonomy_tables.py
│       └── 13f9bb00e29d_add_tag_results_table.py
├── scripts/
│   ├── seed_taxonomy.py             # Seeds 8 categories, 30+ tags, 8 rules via API
│   ├── clickhouse-config.xml        # ClickHouse single-node cluster config (Langfuse v3)
│   ├── postgres-init.sql            # DB init script (run by Docker)
│   ├── prometheus.yml               # Prometheus scrape config
│   └── grafana-datasources.yml      # Grafana datasource config
├── Dockerfile                       # Multi-stage: base → dependencies → dev/prod
├── docker-compose.yml               # Full local stack (14 services)
├── pyproject.toml                   # Dependencies, tool config
├── uv.lock                          # Locked dependency tree
├── alembic.ini                      # Alembic config file
└── Makefile                         # All developer commands
```

---

## How the Pipeline Works

### 1. Request arrives at `POST /tag`

```json
{
  "note_id": "note-abc",
  "ro_id": "ro-123",
  "shop_id": "shop-456",
  "text": "Customer needs front brake pads replaced, insurance claim approved.",
  "event_type": "repair_note"
}
```

### 2. Orchestrator loads taxonomy

All active tags and rules are fetched from PostgreSQL (cached in Redis for 5 minutes).

### 3. LangGraph state machine runs

**Node 1 — Rules Engine** (`<1ms`):
- Evaluates every enabled rule against the note text
- Condition types: `KEYWORD_ANY`, `KEYWORD_NONE`, `PHRASE`, `REGEX`
- All conditions in a rule must pass (AND logic)
- Produces `TagResult` with `confidence=1.0`, `source=rules`

**Node 2 — LLM Chain** (async):
- Builds a prompt with the full tag taxonomy as context
- Calls the configured LLM provider asynchronously
- Parses JSON response, validates tag slugs against taxonomy
- Filters results below the confidence threshold
- If the LLM fails for any reason, returns an empty list (rules results still used)

**Node 3 — Merge**:
- Rules results always take precedence (same tag from both → keep rules result)
- LLM-only results added if confidence ≥ threshold
- Final list sorted by confidence descending

### 4. Results persisted to `tag_results` table

### 5. Response returned

```json
{
  "note_id": "note-abc",
  "results": [
    {
      "tag_slug": "brake-repair",
      "tag_name": "Brake Repair",
      "confidence": 1.0,
      "source": "rules",
      "reasoning": "Matched rule: brake-keyword-rule"
    },
    {
      "tag_slug": "insurance-claim",
      "tag_name": "Insurance Claim",
      "confidence": 0.92,
      "source": "llm",
      "reasoning": "Note explicitly mentions insurance claim approval."
    }
  ]
}
```

### Pipeline Routing Logic

```
START
  │
  ├─ LLM_ONLY? ──────────────────────────────▶ run_llm ──▶ merge ──▶ END
  │
  └─ RULES_ONLY / HYBRID ──▶ run_rules
                                   │
                                   ├─ RULES_ONLY? ──────────────▶ merge ──▶ END
                                   │
                                   └─ HYBRID ──▶ run_llm ──▶ merge ──▶ END
```

---

## API Reference

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Returns `{"status": "ok", "version": "0.1.0"}` |

### Tagging

| Method | Path | Description |
|---|---|---|
| `POST` | `/tag` | Tag a repair note. Returns list of matching tags with confidence + reasoning. |

**Request body:**
```json
{
  "note_id": "string",
  "ro_id": "string",
  "shop_id": "string",
  "text": "string",
  "event_type": "string"
}
```

### Taxonomy

| Method | Path | Description |
|---|---|---|
| `GET` | `/taxonomy` | All categories and tags with counts |
| `GET` | `/taxonomy/categories` | List all categories |
| `GET` | `/taxonomy/tags` | List all tags |
| `POST` | `/taxonomy/categories` | Create a category (returns 201) |
| `POST` | `/taxonomy/tags` | Create a tag (returns 201) |

**Create category:**
```json
{
  "name": "Brakes",
  "slug": "brakes",
  "description": "Brake-related repair tags",
  "sort_order": 1
}
```

**Create tag:**
```json
{
  "name": "Brake Pad Replacement",
  "slug": "brake-pad-replacement",
  "category_id": "uuid-of-category",
  "description": "Front or rear brake pad replacement",
  "color": "#FF6B6B",
  "icon": "wrench",
  "priority": 10
}
```

### Rules

| Method | Path | Description |
|---|---|---|
| `GET` | `/rules` | List all rules |
| `GET` | `/rules/{rule_id}` | Get a single rule with all conditions |
| `POST` | `/rules` | Create a rule (returns 201) |
| `PUT` | `/rules/{rule_id}` | Update a rule and its conditions |
| `DELETE` | `/rules/{rule_id}` | Delete a rule (204, cascades to conditions) |

**Create rule:**
```json
{
  "tag_id": "uuid-of-tag",
  "name": "brake-keyword-rule",
  "priority": 10,
  "is_enabled": true,
  "conditions": [
    {
      "condition_type": "keyword_any",
      "operator": "and",
      "values": ["brake", "brakes", "brake pad"]
    },
    {
      "condition_type": "keyword_none",
      "operator": "and",
      "values": ["estimate", "quote"]
    }
  ]
}
```

**Condition types:**

| Type | Behavior |
|---|---|
| `keyword_any` | Passes if ANY value is found in the note text (case-insensitive) |
| `keyword_none` | Passes if NONE of the values are found (exclusion logic) |
| `phrase` | Passes if ANY exact phrase is found |
| `regex` | Passes if ANY regex pattern matches (uses `re.IGNORECASE`) |

All conditions within a single rule use AND logic — every condition must pass for the rule to fire.

---

## Database Schema

```
tag_categories
  id (UUID PK)
  name, slug (UNIQUE), description
  is_active, sort_order
  created_at, updated_at

tags
  id (UUID PK)
  category_id → tag_categories (FK RESTRICT)
  name, slug (UNIQUE), description
  color (#RRGGBB), icon, priority
  is_active
  created_at, updated_at

tag_rules
  id (UUID PK)
  tag_id → tags (FK RESTRICT)
  name, priority, is_enabled
  created_at, updated_at

tag_rule_conditions
  id (UUID PK)
  rule_id → tag_rules (FK CASCADE DELETE)
  condition_type (keyword_any|keyword_none|phrase|regex)
  operator (and|or)
  values (JSON array of strings)
  created_at

tag_results
  id (UUID PK)
  note_id, ro_id, shop_id (indexed for querying)
  tag_id → tags (FK RESTRICT)
  confidence (0.0–1.0)
  source (rules|llm)
  reasoning (text)
  created_at
```

---

## Configuration & Environment Variables

Copy `.env.example` to `.env` and fill in values before running.

```bash
make env   # copies .env.example → .env
```

### Application

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development`, `staging`, or `production` |
| `LOG_LEVEL` | `info` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Database

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | `postgresql+asyncpg://user:pass@host:port/db` |
| `DATABASE_POOL_SIZE` | `20` | asyncpg connection pool size per worker |
| `DATABASE_MAX_OVERFLOW` | `10` | Extra connections beyond pool size |

> In Docker, point to pgBouncer: `postgresql+asyncpg://tagger:tagger@pgbouncer:5432/tagger`

### Redis

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | General cache + taxonomy cache |
| `ARQ_REDIS_URL` | `redis://localhost:6379/1` | ARQ background job queue |
| `REDIS_TAXONOMY_TTL` | `300` | Taxonomy cache TTL in seconds |

### Tagging Pipeline

| Variable | Default | Description |
|---|---|---|
| `TAGGING_MODE` | `hybrid` | `rules_only`, `llm_only`, or `hybrid` |
| `LLM_CONFIDENCE_THRESHOLD` | `0.7` | Global LLM result filter (0.0–1.0) |
| `LLM_CONFIDENCE_PARTS` | `0.70` | Per-category threshold override |
| `LLM_CONFIDENCE_CUSTOMER` | `0.85` | Higher bar to avoid false positives |
| `LLM_CONFIDENCE_INSURANCE` | `0.80` | Insurance category threshold |
| `LLM_CONFIDENCE_PRODUCTION` | `0.75` | Production category threshold |
| `LLM_TIMEOUT_SECONDS` | `30` | Max wait for LLM response |
| `LLM_MAX_RETRIES` | `2` | Retry attempts on LLM failure |

### LLM Provider

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | — | **Required.** `ollama`, `openai`, `azure_openai`, or `anthropic` |

**Ollama (local):**

| Variable | Default |
|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` |
| `OLLAMA_MODEL` | `gemma2:9b` |

**OpenAI:**

| Variable | Default |
|---|---|
| `OPENAI_API_KEY` | — |
| `OPENAI_MODEL` | `gpt-4o-mini` |
| `OPENAI_MAX_TOKENS` | `500` |

**Azure OpenAI:**

| Variable | Default |
|---|---|
| `AZURE_OPENAI_ENDPOINT` | — |
| `AZURE_OPENAI_API_KEY` | — |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4o-mini` |
| `AZURE_OPENAI_API_VERSION` | `2024-02-01` |

**Anthropic:**

| Variable | Default |
|---|---|
| `ANTHROPIC_API_KEY` | — |
| `ANTHROPIC_MODEL` | `claude-3-5-haiku-20241022` |
| `ANTHROPIC_MAX_TOKENS` | `500` |

### API

| Variable | Default | Description |
|---|---|---|
| `API_HOST` | `0.0.0.0` | Bind address |
| `API_PORT` | `8000` | Port |
| `WORKERS` | `4` | Uvicorn worker count in production. Formula: `(2 × CPU cores) + 1` |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |

### Langfuse (optional — enables LLM tracing)

| Variable | Description |
|---|---|
| `LANGFUSE_PUBLIC_KEY` | `pk-lf-...` — from Langfuse project settings |
| `LANGFUSE_SECRET_KEY` | `sk-lf-...` — from Langfuse project settings |
| `LANGFUSE_HOST` | `http://localhost:3001` (outside Docker) |
| `LANGFUSE_NEXTAUTH_SECRET` | Fixed random string — set once, never change |
| `LANGFUSE_SALT` | Fixed random string — set once, never change |
| `LANGFUSE_ENCRYPTION_KEY` | 64-char hex — generate with `openssl rand -hex 32` |

### Worker (ARQ)

| Variable | Default | Description |
|---|---|---|
| `WORKER_MAX_JOBS` | `10` | Concurrent LLM jobs per worker |
| `WORKER_JOB_TIMEOUT` | `60` | Seconds before job is considered failed |
| `WORKER_RETRY_JOBS` | `true` | Whether to retry failed jobs |
| `WORKER_MAX_TRIES` | `3` | Max retry attempts per job |

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker + Docker Compose v2)
- [uv](https://github.com/astral-sh/uv) — Python package manager
- An LLM: [Ollama](https://ollama.ai) running locally (free, recommended for dev), or an API key for OpenAI / Azure OpenAI / Anthropic

---

### Step 1 — Clone and configure

```bash
git clone <repo-url>
cd llm-tagger-api

make env          # copies .env.example → .env
```

Open `.env` and set at minimum:

```bash
# Pick one LLM provider:
LLM_PROVIDER=ollama          # or openai / azure_openai / anthropic

# Ollama (if using local):
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma2:9b

# OpenAI (if using cloud):
# OPENAI_API_KEY=sk-...

# Langfuse — set these once and never change them.
# They keep your API keys stable across container restarts.
LANGFUSE_NEXTAUTH_SECRET=<any-fixed-random-string>
LANGFUSE_SALT=<any-fixed-random-string>
LANGFUSE_ENCRYPTION_KEY=<64-char-hex — generate with: openssl rand -hex 32>
```

> **Ollama setup:** install from https://ollama.ai, then run `ollama pull gemma2:9b`.
> The app connects to it via `host.docker.internal` from inside Docker — no extra config needed.

---

### Step 2 — Start the full stack

```bash
make up
```

This pulls images and starts all services (~30–60s on first run):

| Service | URL | Notes |
|---|---|---|
| **API** | http://localhost:8000 | FastAPI + hot reload |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **Langfuse** | http://localhost:3001 | LLM trace viewer |
| **MinIO Console** | http://localhost:9011 | Object storage UI (admin / langfuse123) |
| **Prometheus** | http://localhost:9090 | Metrics scraper |
| **Grafana** | http://localhost:3002 | Dashboards (admin / admin) |

Internal-only (no exposed port): PostgreSQL, pgBouncer, Redis, ClickHouse, Langfuse Redis, Langfuse worker.

> **Tip:** First startup is slow while ClickHouse and Langfuse run migrations.
> Run `make logs` to watch progress.

---

### Step 3 — Run database migrations

```bash
make migrate
```

This runs Alembic against the app's PostgreSQL database (`tagger`). Only needed on first run and after schema changes.

---

### Step 4 — Seed the taxonomy

```bash
make seed
```

Creates the full repair-order taxonomy via the API:
- **8 categories** (Parts, Customer, Insurance, Production, Sublet, Rental, Communication, Financial)
- **30+ tags** with names, slugs, colors, and icons
- **8 detection rules** with keyword conditions

You only need to run this once. The script is idempotent — re-running it skips existing records.

---

### Step 5 — Set up Langfuse API keys

Every LLM call is traced in Langfuse. To enable it:

1. Open http://localhost:3001 and sign up with any email/password
2. Create a project (e.g. `llm-tagger`)
3. Go to **Settings → API Keys**, generate a key pair
4. Copy the keys into `.env`:
   ```bash
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_HOST=http://localhost:3001   # outside Docker
   ```
5. Restart the app to pick up the new keys:
   ```bash
   make restart
   ```
6. Verify tracing is on:
   ```bash
   docker logs llm-tagger-app 2>&1 | grep Langfuse
   # Langfuse tracing ON → http://langfuse:3000
   ```

> **Keep API keys stable:** set `LANGFUSE_NEXTAUTH_SECRET`, `LANGFUSE_SALT`, and `LANGFUSE_ENCRYPTION_KEY`
> to fixed strings in `.env` before first run and never change them. Never run `docker compose down -v`
> (removes volumes and wipes the Langfuse database).

---

### Step 6 — Verify and tag a note

```bash
curl http://localhost:8000/health
# {"status": "ok", "version": "0.1.0"}
```

```bash
curl -X POST http://localhost:8000/tag \
  -H "Content-Type: application/json" \
  -d '{
    "note_id": "note-001",
    "ro_id": "ro-001",
    "shop_id": "shop-001",
    "text": "Customer needs front brake pads replaced. Insurance claim approved.",
    "event_type": "repair_note"
  }'
```

You should get back matched tags with confidence scores and reasoning. Open http://localhost:3001 to see the trace.

---

## All Commands Reference

### Setup

```bash
make install         # Install all dependencies with uv
make env             # Copy .env.example → .env
```

### Docker

```bash
make up              # Start all services
make down            # Stop all services
make restart         # Restart app + worker only (fast)
make logs            # Follow all container logs
make logs-app        # Follow app logs only
make logs-worker     # Follow worker logs only
```

### Database

```bash
make migrate                    # Apply all pending migrations (alembic upgrade head)
make seed                       # Seed taxonomy: 8 categories, 30+ tags, 8 rules (idempotent)
make migrate-create name=foo    # Generate new migration from ORM model changes
make migrate-down               # Roll back the last migration
make db-reset                   # Full reset: drop DB, recreate, migrate (destructive)
```

### Testing

```bash
make test            # Full test suite (pytest -v)
make test-unit       # Unit tests only (-m unit, no I/O)
make test-int        # Integration tests (-m integration, needs real DB + Redis)
make test-contract   # API contract tests (-m contract)
make test-cov        # Full suite + HTML coverage report (open coverage-html/index.html)
make test-watch      # Watch mode — reruns on file change
```

### Code Quality

```bash
make lint            # Ruff linter
make format          # Ruff formatter + auto-fix
make typecheck       # MyPy strict type checking
make check           # Lint + typecheck together
```

### Load Testing

```bash
make load-test       # Start Locust (opens browser UI at http://localhost:8089)
                     # Target: 17k req/sec against POST /tag
```

### Local Dev (without Docker)

```bash
make dev             # Starts uvicorn with hot reload on port 8001
make clean           # Remove __pycache__, .mypy_cache, coverage-html
```

---

## Running Tests

The test suite uses real PostgreSQL and Redis via Testcontainers (no mocking of the database).

```bash
# Full suite
make test

# Only fast unit tests (no I/O)
make test-unit

# Integration tests — spins up real Postgres + Redis containers
make test-int

# With coverage report
make test-cov
# Open coverage-html/index.html in your browser
```

Test markers:

| Marker | Description |
|---|---|
| `unit` | Pure logic, no I/O |
| `integration` | Requires real DB and Redis |
| `contract` | API schema validation |
| `slow` | Takes more than 1 second |

Coverage threshold: **80%** (configured in `pyproject.toml`). Builds fail below this.

---

## Observability

### Langfuse — LLM Tracing

Every LLM call is automatically traced in Langfuse using the SDK v3 `CallbackHandler`. Each `/tag` request creates one parent trace (keyed by `note_id`) with the LLM generation span nested inside, giving full prompt/response visibility.

**Setup:** covered in [Step 5](#step-5--set-up-langfuse-api-keys) above.

**Stack (Langfuse v3):** the compose file runs four Langfuse-related services:

| Service | Role |
|---|---|
| `langfuse` | Web UI + REST API (port 3001) |
| `langfuse-worker` | Processes ingested events from Redis queue into ClickHouse |
| `langfuse-db` | PostgreSQL — stores users, projects, and API keys |
| `clickhouse` | ClickHouse — stores all traces and spans |
| `minio` | MinIO — S3-compatible object store used as the event queue |

**Tracing implementation:** the app creates a parent `span` via `Langfuse.start_observation()` with `note_id`/`shop_id` metadata, then passes a `CallbackHandler` with `trace_context` to `llm.ainvoke()`. LangChain spans become children of the parent trace automatically.

**Troubleshooting API keys not persisting:**
- Never run `docker compose down -v` — this deletes volumes including the Langfuse database.
- Set `LANGFUSE_NEXTAUTH_SECRET`, `LANGFUSE_SALT`, and `LANGFUSE_ENCRYPTION_KEY` to fixed strings in `.env` before first run and never change them.

### Prometheus + Grafana — Metrics

- Prometheus scrapes `/metrics` from the FastAPI app
- Grafana dashboards available at http://localhost:3002 (admin/admin)
- Tracks: request count, latency histograms, error rates

### Structured Logging

Set `LOG_LEVEL=DEBUG` in `.env` to see pipeline routing decisions, rule evaluations, and LLM responses in the app logs:

```bash
make logs-app
```

---

## Database Migrations

Migrations are managed with Alembic. The migration runner is async (required for asyncpg).

```bash
# Apply all pending migrations
make migrate

# Generate a new migration after editing ORM models in infrastructure/db/models.py
make migrate-create name=add_note_metadata_column

# Roll back one migration
make migrate-down

# Full reset (WARNING: destroys all data)
make db-reset
```

Migration files live in `alembic/versions/`. Always review auto-generated migrations before committing — Alembic may miss complex constraints or index changes.

---

## LLM Providers

Switch providers by setting `LLM_PROVIDER` in `.env`. No code changes required.

### Ollama (local, free)

Best for development. Install Ollama, pull a model, then run:

```bash
ollama pull gemma2:9b
# Set in .env:
# LLM_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=gemma2:9b
```

> Inside Docker, use `OLLAMA_BASE_URL=http://host.docker.internal:11434`

### OpenAI

```bash
# Set in .env:
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o-mini
```

### Azure OpenAI

```bash
# Set in .env:
# LLM_PROVIDER=azure_openai
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
# AZURE_OPENAI_API_KEY=...
# AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
```

### Anthropic

```bash
# Set in .env:
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
# ANTHROPIC_MODEL=claude-3-5-haiku-20241022
```

Config is validated at startup — if a required variable for the selected provider is missing, the app will fail immediately with a clear error message.
