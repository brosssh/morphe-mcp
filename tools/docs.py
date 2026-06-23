from pathlib import Path
from config import KNOWLEDGE_DIR


def get_system_instructions() -> str:
    """Return the custom system knowledge / persona loaded from SYSTEM.md."""
    f = KNOWLEDGE_DIR / "SYSTEM.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def search_docs(query: str) -> str:
    """Search knowledge markdown files for a keyword or topic."""
    query_lower = query.lower()
    results = []
    for md_file in sorted(KNOWLEDGE_DIR.glob("*.md")):
        if md_file.name == "SYSTEM.md":
            continue
        content = md_file.read_text(encoding="utf-8", errors="replace")
        if query_lower in content.lower():
            results.append(f"## {md_file.stem}\n\n{content[:3000]}")
    return "\n\n---\n\n".join(results) if results else f"No docs matched '{query}'."


def list_docs() -> str:
    """List all available knowledge documents."""
    files = [f.stem for f in sorted(KNOWLEDGE_DIR.glob("*.md")) if f.name != "SYSTEM.md"]
    return "\n".join(files) if files else "No knowledge documents found."


def read_doc(name: str) -> str:
    """Read a specific knowledge document by name (without .md extension)."""
    path = KNOWLEDGE_DIR / f"{name}.md"
    if not path.exists():
        available = list_docs()
        return f"Document '{name}' not found.\n\nAvailable docs:\n{available}"
    return path.read_text(encoding="utf-8")
