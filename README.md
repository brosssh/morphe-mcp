# morphe-mcp

An MCP server that gives an AI coding assistant read-only access to the [Morphe](https://github.com/MorpheApp)
patch-bundle repositories and a curated knowledge base, so it can answer questions about Morphe and help
write/review patches grounded in real, current code instead of guessing from training data.

It exposes two kinds of tools:

- **Repo tools** — read files, list directories, and grep across the Morphe repos checked out as git
  submodules in this server.
- **Docs tools** — search and read a small set of hand-written knowledge docs (`knowledge/*.md`) covering
  conventions that aren't always obvious from a quick repo read (fingerprint style, the `extendWith`/
  `dependsOn` pattern, stubbing, etc).

## Repositories

Only the three repos with **`official`** in their key are actually part of Morphe. The rest are
third-party bundles/libraries built on top of it — listed below, but never "official".

| Repo key | Official? | What it is |
|---|---|---|
| `official-patches` | Yes | **Morphe Patches** — the official patch bundle (YouTube, YouTube Music, Reddit). Default repo for all repo tools; prefer this first for any general example. |
| `official-patches-library` | Yes | Shared library consumed by every bundle below — `morphe-patches-library` (shared patch code) and `morphe-extensions-library` (shared extension runtime code). |
| `official-patcher` | Yes | The patcher API all patch bundles depend on. Its `docs/` are the canonical Morphe DSL documentation. |
| `brosssh-patches` | **No** | Instagram-specific patches by brosssh. Secondary source, used when Morphe Patches has no equivalent (it doesn't cover Instagram). |
| `hoodles-patches` | **No** | Multi-app patches unlocking premium features in various apps. Secondary source. |
| `instagram-morphe-patches-library` | **No** | Brosssh-published library extending `official-patches-library` with Instagram-specific shared code. Last resort, Instagram-only. |

All of the above are git submodules (see `.gitmodules`) checked out next to this server and read directly
from disk — no network calls per request.

## Setup

```bash
git clone --recurse-submodules <this repo>
cp .env.example .env   # MCP_HOST / MCP_PORT, defaults: 0.0.0.0:8080
uv run main.py
```

The server runs over MCP's Streamable HTTP transport, mounted at `/mcp` (e.g. `http://localhost:8080/mcp`).

### Connecting a client

A deployed instance is already running at **`https://morphe-mcp.brosssh.com/mcp`** — use this URL
directly instead of standing up your own server, unless you specifically need to run a local/modified copy.

- **Claude Code:**
  ```bash
  claude mcp add --transport http morphe-mcp https://morphe-mcp.brosssh.com/mcp
  ```
  or in `.mcp.json`:
  ```json
  { "mcpServers": { "morphe-mcp": { "type": "http", "url": "https://morphe-mcp.brosssh.com/mcp" } } }
  ```
- **Claude Desktop / Claude.ai:** Settings → Connectors → Add custom connector → enter
  `https://morphe-mcp.brosssh.com/mcp`. (Claude Desktop's `claude_desktop_config.json` does not support
  remote HTTP servers via a `url` field — use the Connectors UI instead.)

For a local/self-hosted instance, replace the URL above with `http://localhost:8080/mcp` (or wherever
you've deployed it).

## MCP tools

### Repo tools

| Tool | Args | Description |
|---|---|---|
| `repo_read_file` | `file_path`, `repo` (default `official-patches`) | Read a source file from a Morphe repo. |
| `repo_list_files` | `repo` (default `official-patches`), `subdir`, `extension` | List files in a repo, optionally filtered by subdirectory/extension. |
| `repo_grep` | `pattern`, `repo` (default `official-patches`), `extension` (default `.kt`) | Grep for a pattern (Fingerprint name, class, method, smali opcode, ...) across a repo. |

### Knowledge docs tools

| Tool | Args | Description |
|---|---|---|
| `docs_search` | `query` | Search all knowledge docs for a keyword/topic. |
| `docs_list` | — | List the available knowledge documents. |
| `docs_read` | `name` | Read one knowledge document in full, by name (no `.md`). |

Current knowledge docs (`knowledge/`): `fingerprinting`, `patch-dsl`, `smali-patterns`, `stubbing`, `tools`.
(`SYSTEM.md` is the assistant's system prompt, not a browsable doc.)

## Example interactions

> "Show me an example Morphe patch and explain how it works"
→ `repo_read_file(file_path="patches/src/main/kotlin/app/morphe/patches/youtube/layout/hide/time/HideTimestampPatch.kt")`
(default `repo="official-patches"`) — reads a real, simple patch to walk through.

> "How does `matchAll` work, and when should I use the range overload?"
→ `docs_read(name="fingerprinting")` — covers the full `matchAll`/`matchAllOrNull` API with a real example.

> "Find every patch that uses `dependsOn(sharedExtensionPatch)`"
→ `repo_grep(pattern="dependsOn(sharedExtensionPatch", repo="official-patches")`

> "What's the right way to load a `.mpe` extension from a patch?"
→ `docs_search(query="extendWith")` — surfaces the `extendWith`/`dependsOn` convention from `patch-dsl.md`.

> "I'm new to this — what tools do I need to start reverse engineering an app?"
→ `docs_read(name="tools")` — JADX, HTTP Toolkit, Frida, with setup caveats for each.

> "Is there a patch in brosssh-patches that overrides a mobile config flag?"
→ `repo_grep(pattern="overrideMobileConfigBooleanFlag", repo="brosssh-patches")`, then
`repo_read_file(repo="instagram-morphe-patches-library", file_path="patch-library/src/main/kotlin/app/morphe/patches/instagram/misc/OverrideMobileConfigBooleanFlagPatch.kt")`
for the underlying implementation.
