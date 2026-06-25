# Tools for getting started with patching

Writing a Morphe patch almost always starts outside Morphe: you need to read decompiled code to find
what to fingerprint, and sometimes inspect network traffic or runtime behavior to understand what an
app is actually doing. This is a quick map of the common tools for that, roughly in the order a newbie
would reach for them.

## 1. Reading the app — JADX

[JADX](https://github.com/skylot/jadx) is by far the best Java decompiler for Android APKs, and should
be the first thing you reach for when inspecting a new app. Open the APK in `jadx-gui` (or use the CLI)
to get readable, deobfuscated-as-much-as-possible Java source, browse resources/strings, and search for
method/class names or string literals — this is exactly what you need to find the unique strings,
method calls, or literals that go into a Morphe `Fingerprint(...)` (see `fingerprinting.md`).

JADX has its own MCP server — [jadx-mcp-server](https://github.com/zinja-coder/jadx-mcp-server) — which
exposes the currently-open JADX project (decompiled classes, methods, search) as MCP tools. Combining it
with `morphe-mcp` in the same client is a strong workflow: ask the JADX MCP tools to find/read the
relevant decompiled Java for a feature, then ask `morphe-mcp` (`docs_search`, `repo_grep`, etc.) how to
express that as a Fingerprint + bytecode patch.

## 2. Inspecting network traffic — HTTP Toolkit

[HTTP Toolkit](https://httptoolkit.com/) is the go-to tool for inspecting an app's HTTP(S) traffic
(useful for endpoint-spoofing, ad/tracking-blocking, or signature-spoofing patches — see
`official-patches`' `shared/misc/spoof` patches for real examples of what this kind of investigation
leads to). The catch: most apps pin their TLS certificate and/or restrict trusted CAs at the network
security config level, so HTTP Toolkit's MITM proxy won't see anything by default. You need to remove
that restriction first:

- **Manual (most reliable):** decompile the APK, remove/relax the network security config
  (`res/xml/network_security_config.xml`) and any certificate-pinning code, then recompile and re-sign
  before installing. This is the most work, but doesn't change anything else about the app.
- **Automatic — apk-mitm:** [apk-mitm](https://github.com/shroudedcode/apk-mitm) does the network
  security config + pinning removal for you automatically. The trade-off: it re-signs the APK with a
  new (different) signature, which can break anything that depends on the original signature — app
  updates over the original install, signature-verification checks the app itself does, Play Integrity,
  or any patch that assumes the original cert. Fine for a quick look, but be aware of what it changes.
- **Rooted device (easiest):** if your test device is rooted, you don't need to modify the APK at all
  for this part. Install the original, unmodified APK, connect HTTP Toolkit via ADB, and use its
  experimental Frida-based "bypass SSL pinning" option — it injects a Frida script at runtime to defeat
  pinning, all from the HTTP Toolkit interface with a click. This works for most apps without any manual
  decompiling/resigning, and keeps the original signature intact.

## 3. Dynamic instrumentation — Frida (advanced)

[Frida](https://frida.re/) lets you hook into a running app and inspect or **modify** a function's
parameters and return values live, without writing a static patch — useful for quickly testing a
hypothesis (e.g. "does forcing this method to return `true` actually unlock the feature?") before
committing to the equivalent smali change in a real patch.

- **Rooted device:** install `frida-server` on the device — this gives Frida full capabilities and is
  the simplest setup (also what HTTP Toolkit's SSL-pinning bypass above relies on).
- **Non-rooted device:** use **Frida Gadget** instead — a `.so` library injected into the APK itself
  (repack + re-sign required, similar caveats to apk-mitm above regarding signature changes), which lets
  Frida attach without root but requires modifying the APK up front.

## Why this matters for Morphe patches

These tools answer "what is the obfuscated code actually doing" and "what should I fingerprint/hook" —
the investigative step before writing the patch. Once you know the target method/class/string, the
actual patch implementation follows the conventions in `patch-dsl.md`, `fingerprinting.md`, and
`smali-patterns.md`.
