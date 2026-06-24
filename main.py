from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from tools.files import read_file, list_files, grep_codebase
from tools.docs import get_system_instructions, search_docs, list_docs, read_doc
from config import HOST, PORT

mcp = FastMCP(
    "morphe-knowledge",
    instructions=get_system_instructions(),
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    )
)


# ── Repo tools ────────────────────────────────────────────────────────────────

@mcp.tool()
def repo_read_file(repo: str, file_path: str) -> str:
    """Read a source file from a morphe repo.

    Args:
        repo: one of 'morphe-patches', 'instagram-library', 'morphe-patcher'
        file_path: relative path within the repo (e.g. 'patches/HideReshareButtonPatch.kt')
    """
    return read_file(repo, file_path)


@mcp.tool()
def repo_list_files(repo: str, subdir: str = "", extension: str = "") -> str:
    """List files in a morphe repo.

    Args:
        repo: one of 'morphe-patches', 'instagram-library', 'morphe-patcher'
        subdir: optional subdirectory to list within the repo
        extension: optional file extension filter, e.g. '.kt', '.java', '.smali'
    """
    return list_files(repo, subdir, extension)


@mcp.tool()
def repo_grep(repo: str, pattern: str, extension: str = ".kt") -> str:
    """Grep for a pattern across source files in a morphe repo.
    Useful to find usages of a Fingerprint, class name, method, or smali opcode.

    Args:
        repo: one of 'morphe-patches', 'instagram-library', 'morphe-patcher'
        pattern: text or regex pattern to search for
        extension: file extension to search in, default '.kt'
    """
    return grep_codebase(repo, pattern, extension)


# ── Knowledge / docs tools ────────────────────────────────────────────────────

@mcp.tool()
def docs_search(query: str) -> str:
    """Search the morphe knowledge base (markdown docs) for a topic or keyword.
    Use this to find documentation about fingerprinting, the patch DSL, smali patterns,
    register constraints, extension classes, and other morphe concepts.

    Args:
        query: keyword or topic to search for
    """
    return search_docs(query)


@mcp.tool()
def docs_list() -> str:
    """List all available knowledge documents in the morphe knowledge base."""
    return list_docs()


@mcp.tool()
def docs_read(name: str) -> str:
    """Read a specific knowledge document in full by name (without .md extension).

    Args:
        name: document name, e.g. 'fingerprinting', 'smali-patterns', 'patch-dsl'
    """
    return read_doc(name)


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
