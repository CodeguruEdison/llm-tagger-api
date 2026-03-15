"""
LLM prompt templates — loaded from .md files.

Why .md files:
- Prompts are editable without touching Python code
- Non-developers can improve prompts directly
- Git shows exactly what changed in each prompt version
- Readable in GitHub with proper formatting

Templates location: src/tagging/infrastructure/llm/templates/
system.md  ← system prompt (role + taxonomy + rules)
user.md    ← user prompt (note text + output format)
"""

from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

# Path to templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"
def _load_template(filename: str) -> str:
    """
    Load a prompt template from a .md file.

    Why Path(__file__).parent:
      Always resolves relative to this file's location.
      Works regardless of where the app is launched from.
      Critical for Docker containers where working directory varies.
    """
    template_path = TEMPLATES_DIR / filename
    if not template_path.exists():
        raise FileNotFoundError(
            f"Prompt template not found: {template_path}. "
            f"Expected at: {TEMPLATES_DIR}"
        )
    return template_path.read_text(encoding="utf-8").strip()

def build_taxonomy_context(tags: list) -> str:
    """
    Build taxonomy string injected into the system prompt.

    Format:
    - parts-delay: Apply when notes indicate waiting on parts...
    - customer-concern: Apply when notes indicate customer issues...

    Why rich descriptions matter:
    The LLM uses these to understand WHEN to apply each tag.
    Better descriptions = higher accuracy.
    This is the LLM's context for your taxonomy.
    """
    if not tags:
        return "No tags available."

    lines = [f"  - {tag.slug}: {tag.description}" for tag in tags]
    return "\n".join(lines)

def build_tagging_prompt() -> ChatPromptTemplate:
    """
    Build the complete tagging prompt template from .md files.

    Called once at startup — templates are cached after first load.
    Variables injected at runtime: {taxonomy} and {note_text}
    """
    system_template = _load_template("system.md")
    user_template = _load_template("user.md")

    return ChatPromptTemplate.from_messages([
        ("system", system_template),
        ("human", user_template),
    ])
 # Build once at module load — templates are static files
TAGGING_PROMPT = build_tagging_prompt()
