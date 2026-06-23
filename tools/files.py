import subprocess
from pathlib import Path
from config import REPOS


def _safe_path(repo_root: Path, relative: str) -> Path:
    resolved = (repo_root / relative).resolve()
    if not str(resolved).startswith(str(repo_root.resolve())):
        raise ValueError("Path traversal denied")
    return resolved


def read_file(repo: str, file_path: str) -> str:
    """Read a file from a local repo."""
    root = REPOS.get(repo)
    if not root:
        return f"Unknown repo '{repo}'. Available: {list(REPOS.keys())}"
    if not root.exists():
        return f"Repo path does not exist on this server: {root}"
    path = _safe_path(root, file_path)
    if not path.exists():
        return f"File not found: {file_path}"
    return path.read_text(encoding="utf-8", errors="replace")


def list_files(repo: str, subdir: str = "", extension: str = "") -> str:
    """List files in a repo, optionally filtered by subdir or extension."""
    root = REPOS.get(repo)
    if not root:
        return f"Unknown repo '{repo}'. Available: {list(REPOS.keys())}"
    if not root.exists():
        return f"Repo path does not exist on this server: {root}"
    target = _safe_path(root, subdir) if subdir else root
    pattern = f"**/*{extension}" if extension else "**/*"
    files = [str(p.relative_to(root)) for p in sorted(target.glob(pattern)) if p.is_file()]
    return "\n".join(files[:300]) or "No files found."


def grep_codebase(repo: str, pattern: str, extension: str = ".kt") -> str:
    """Grep for a pattern across a repo."""
    root = REPOS.get(repo)
    if not root:
        return f"Unknown repo '{repo}'. Available: {list(REPOS.keys())}"
    if not root.exists():
        return f"Repo path does not exist on this server: {root}"
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include", f"*{extension}", pattern, str(root)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        output = result.stdout.strip()
        return output[:8000] if output else "No matches found."
    except subprocess.TimeoutExpired:
        return "Grep timed out — try a more specific pattern."
    except FileNotFoundError:
        return "grep not available on this system."
