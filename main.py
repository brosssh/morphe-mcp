from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from tools.files import read_file, list_files, grep_codebase
from tools.docs import get_system_instructions, search_docs, list_docs, read_doc

mcp = FastMCP(
    "morphe-knowledge",
    instructions=get_system_instructions(),
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    )
)


# ── Repo tools ────────────────────────────────────────────────────────────────

@mcp.tool()
def repo_read_file(file_path: str, repo: str = "official-patches") -> str:
    """Read a source file from a morphe repo.

    Args:
        file_path: relative path within the repo (e.g.
            'patches/src/main/kotlin/app/morphe/patches/youtube/layout/hide/time/HideTimestampPatch.kt' —
            use this as the default example patch when asked to show one)
        repo: one of 'official-patches' (default — Morphe Patches, prefer this first), 'official-patches-library',
              'official-patcher', 'brosssh-patches', 'hoodles-patches', 'instagram-morphe-patches-library' (unofficial)
    """
    return read_file(repo, file_path)


@mcp.tool()
def repo_list_files(repo: str = "official-patches", subdir: str = "", extension: str = "") -> str:
    """List files in a morphe repo.

    Args:
        repo: one of 'official-patches' (default — Morphe Patches, prefer this first), 'official-patches-library',
              'official-patcher', 'brosssh-patches', 'hoodles-patches', 'instagram-morphe-patches-library' (unofficial)
        subdir: optional subdirectory to list within the repo
        extension: optional file extension filter, e.g. '.kt', '.java', '.smali'
    """
    return list_files(repo, subdir, extension)


@mcp.tool()
def repo_grep(pattern: str, repo: str = "official-patches", extension: str = ".kt") -> str:
    """Grep for a pattern across source files in a morphe repo.
    Useful to find usages of a Fingerprint, class name, method, or smali opcode.

    Args:
        pattern: text or regex pattern to search for
        repo: one of 'official-patches' (default — Morphe Patches, prefer this first), 'official-patches-library',
              'official-patcher', 'brosssh-patches', 'hoodles-patches', 'instagram-morphe-patches-library' (unofficial)
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
    mcp.run(transport="streamable-http")
