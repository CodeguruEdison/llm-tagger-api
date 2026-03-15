"""
ARQ worker entrypoint.

Runs the background job worker. Register job functions on WorkerSettings.functions
and enqueue them from the API. When no jobs are registered, the worker still runs
and will process jobs once they are added.

Usage:
  python -m tagging.worker.main

Docker (docker-compose):
  command: uv run python -m tagging.worker.main
"""
import asyncio
import logging

from arq.connections import RedisSettings
from arq.worker import Worker

from tagging.config import get_settings

logger = logging.getLogger(__name__)


def get_redis_settings() -> RedisSettings:
    """Build ARQ RedisSettings from app config."""
    settings = get_settings()
    return RedisSettings.from_dsn(settings.arq_redis_url)


# Placeholder so ARQ accepts the worker (requires at least one function).
# Replace or add real jobs (e.g. tag_note) as needed.
async def _noop_job(ctx: dict) -> None:
    """No-op; required because ARQ needs at least one registered function."""
    pass


# Job functions go here. Example:
# async def tag_note(ctx, note_id: str) -> None:
#     ...
#
# WorkerSettings.functions = [_noop_job, tag_note]
class WorkerSettings:
    """ARQ worker configuration. Used by arq CLI and by main() below."""

    functions: list = [_noop_job]
    redis_settings = None  # set in main() from config
    max_jobs = 10
    job_timeout = 300
    max_tries = 5

    @classmethod
    def from_settings(cls) -> "WorkerSettings":
        s = get_settings()
        inst = cls()
        inst.redis_settings = RedisSettings.from_dsn(s.arq_redis_url)
        inst.max_jobs = s.worker_max_jobs
        inst.job_timeout = s.worker_job_timeout
        inst.max_tries = s.worker_max_tries
        return inst


def main() -> None:
    """Run the ARQ worker (blocking)."""
    logging.basicConfig(
        level=get_settings().log_level,
        format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    )
    ws = WorkerSettings.from_settings()
    worker = Worker(
        functions=WorkerSettings.functions,
        redis_settings=ws.redis_settings,
        max_jobs=ws.max_jobs,
        job_timeout=ws.job_timeout,
        max_tries=ws.max_tries,
    )
    names = [getattr(f, "name", getattr(f, "__name__", str(f))) for f in WorkerSettings.functions]
    logger.info("Starting ARQ worker (functions=%s)", names)
    worker.run()


if __name__ == "__main__":
    main()
