# Fingerprinting in Morphe

A fingerprint is a partial description of a method used to locate it in an obfuscated APK.
All filters in a fingerprint must match for it to resolve. Filters must appear in the same order as
the instructions in the target method, but non-declared instructions can appear between them (unless
`MatchAfterImmediately` is used).

## Filter reference

```kotlin
// Ordered string constant
string("someStringLiteral")

// Unordered strings (only for enum-type methods with many unordered strings)
strings = listOf("foo", "bar")

// Single opcode
opcode(Opcode.MOVE_RESULT)
opcode(Opcode.MOVE_RESULT, MatchAfterImmediately()) // must be next instruction

// Method call
methodCall(name = "equals", definingClass = "Ljava/lang/String;", returnType = "Z")
methodCall(smali = "Landroid/net/Uri;->parse(Ljava/lang/String;)Landroid/net/Uri;") // smali shorthand

// Field access
fieldAccess(opcode = Opcode.IGET, definingClass = "this", type = "Ljava/util/Map;")
fieldAccess(smali = "Landroid/os/Build;->MODEL:Ljava/lang/String;") // smali shorthand

// Integer/long literal (feature flags use large longs)
literal(45685201L)
literal(255)

// Android resource ID literal
resourceLiteral(ResourceType.ID, "bottom_bar_container")
resourceLiteral(ResourceType.STRING, "some_string_key")

// Exact opcode sequence (no gaps allowed — fragile, avoid unless no other option)
filters = OpcodesFilter.opcodesToFilters(Opcode.CHECK_CAST, Opcode.IF_EQZ, Opcode.RETURN_VOID)

// Match any of several alternatives (for version-specific variance)
anyInstruction(
    string("old string in early version"),
    string("new string in later version")
)
```

## InstructionLocation modifiers

All filter functions accept an optional `location` parameter:

```kotlin
opcode(Opcode.MOVE_RESULT)                      // anywhere after previous filter
opcode(Opcode.MOVE_RESULT, MatchAfterImmediately())  // must be the very next instruction
opcode(Opcode.IF_EQZ, MatchAfterWithin(5))       // within 5 instructions of previous
string("foo", MatchFirst())                      // must be first instruction of method
```

## Fingerprint class anatomy

```kotlin
internal object MyFingerprint : Fingerprint(
    definingClass = "Lcom/google/android/apps/youtube/SomeClass;", // optional, use when non-obfuscated
    name = "onMeasure",                                             // optional, use when non-obfuscated
    accessFlags = listOf(AccessFlags.PUBLIC, AccessFlags.FINAL),
    returnType = "Z",
    parameters = listOf("Ljava/lang/String;", "I", "L"),           // "L" = obfuscated object
    strings = listOf("unordered", "strings"),                       // optional legacy field
    filters = listOf(                                               // ordered instruction filters
        string("showBannerAds"),
        methodCall(name = "equals", definingClass = "Ljava/lang/String;"),
        opcode(Opcode.MOVE_RESULT, MatchAfterImmediately()),
        literal(1337),
        opcode(Opcode.IF_EQ)
    )
)
```

This shows every field a `Fingerprint` can take — real fingerprints should use as few of these as
possible. See "Keep fingerprints minimal" below.

## Keep fingerprints minimal

If `definingClass` + `name` alone uniquely identify the target method, add nothing else — no
`accessFlags`, `returnType`, `parameters`, `strings`, or `filters`. Extra fields add nothing once the
method is already uniquely identified, and only make the fingerprint *more* fragile (e.g. an
`accessFlags` check that breaks if a future APK version changes a method's visibility).

```kotlin
// official-patches: extension method names are unique by construction, so name + definingClass
// is already a precise match — nothing else is needed.
internal object ShowOldPlaybackSpeedMenuExtensionFingerprint : Fingerprint(
    definingClass = EXTENSION_CLASS,
    name = "showOldPlaybackSpeedMenu"
)

// instagram-morphe-patches-library: same idea for a non-obfuscated app entry point.
Fingerprint(
    name = "onCreate",
    definingClass = "/InstagramAppShell;",
)
```

Only add `returnType` / `parameters` when the name alone is ambiguous — i.e. the method is overloaded.
`Activity.onCreate` is a real case: the SDK declares both `onCreate(Bundle)` and
`onCreate(Bundle, PersistableBundle)`, so omitting `parameters` would let the fingerprint match either
one nondeterministically:

```kotlin
internal object GoogleApiActivityOnCreateFingerprint : Fingerprint(
    definingClass = "Lcom/google/android/gms/common/api/GoogleApiActivity;",
    name = "onCreate",
    returnType = "V",
    parameters = listOf("Landroid/os/Bundle;"),  // disambiguates from onCreate(Bundle, PersistableBundle)
)
```

`filters` should only be added when you need to locate something *inside* the method body (an
instruction index to inject at) — never just to "help" identify the method itself once
`definingClass` + `name` (plus disambiguating `returnType`/`parameters` if needed) already do that.

## classFingerprint — narrowing to a class

Use when you want to restrict fingerprint matching to the class found by another fingerprint:

```kotlin
// Step 1: find the class via a unique string somewhere in that class
private object AdsLoaderClassFingerprint : Fingerprint(
    filters = listOf(string("Error fetching CastContext."))
)

// Step 2: find the exact method within that class
internal object ShowAdsFingerprint : Fingerprint(
    classFingerprint = AdsLoaderClassFingerprint,
    returnType = "Z",
    parameters = listOf("Ljava/lang/String;"),
    filters = listOf(
        methodCall(name = "getValue", returnType = "Z"),
        opcode(Opcode.MOVE_RESULT, MatchAfterImmediately())
    )
)
```

## Accessing match results

```kotlin
// Mutable method (for modifications)
MyFingerprint.method

// Mutable class
MyFingerprint.classDef

// Immutable originals (preferred for read-only)
MyFingerprint.originalMethod
MyFingerprint.originalClassDef

// Null-safe variants (when a match may not exist)
MyFingerprint.methodOrNull
MyFingerprint.matchOrNull

// Instruction match positions
val matchIndex = MyFingerprint.instructionMatches[0].index
val matchInstruction = MyFingerprint.instructionMatches[0].getInstruction<OneRegisterInstruction>()
```

## Multiple modifications — work last to first

When modifying the same method multiple times, always apply changes from the **last** matched index
to the **first**, because adding/removing instructions shifts subsequent indices:

```kotlin
MyFingerprint.let {
    // Modify index 5 first, then index 2 — never the other way around
    it.method.removeInstruction(it.instructionMatches[5].index)
    val reg = it.method.getInstruction<OneRegisterInstruction>(it.instructionMatches[2].index).registerA
    it.method.addInstructions(it.instructionMatches[2].index + 1, "const/4 v$reg, 0x0")
}
```

If you need to re-query indices after a modification, call `clearMatch()` then `match()`.

When the block's purpose is mutating the method itself, prefer `fingerprint.method.apply { ... }` over
`with(fingerprint.method) { ... }` — `apply` returns the (now-mutated) method, `with` returns the
block's last expression. See `smali-patterns.md` → "apply vs with" for the full rule and examples.

## matchAll — match every occurrence

A fingerprint matches a single method by default (the first one found, cached). `matchAll` variants
instead search **every method in scope** and return a `List<Match>`:

```kotlin
// Across the whole app
fingerprint.matchAll()          // List<Match>, throws PatchException if none match
fingerprint.matchAllOrNull()    // List<Match>?, null if none match

// Restricted to one class (e.g. a class already found via classFingerprint)
fingerprint.matchAll(classDef)          // throws if none match
fingerprint.matchAllOrNull(classDef)    // null if none match

// Validate how many matches are expected — throws PatchException if the count
// falls outside the range. A range including 0 is allowed (returns an empty list).
fingerprint.matchAll(2 .. 3)
fingerprint.matchAll(classDef, 0 .. 1)
```

Basic usage — replace every const-string match for a given string literal:

```kotlin
val filter = string("some string")
Fingerprint(filters = listOf(filter)).matchAllOrNull()?.forEach { match ->
    match.method.findInstructionIndicesReversedOrThrow(filter).forEach { index ->
        val register = match.method.getInstruction<OneRegisterInstruction>(index).registerA
        match.method.replaceInstruction(index, "const-string v$register, \"replacement\"")
    }
}
```

Real example, `VideoInformationPatch.kt` — the channel-info method exists once per video type
(regular + Shorts, and possibly MDX casting), so the fingerprint is expected to match 2 or 3 times.
Passing the range both documents that expectation and fails loudly if a future APK update changes it:

```kotlin
ChannelInformationFingerprint.let {
    val matches = it.matchAll(2 .. 3)

    val playerResponseType = matches.first().method.parameterTypes.first().toString()

    // ... build a shared helper method once, using info derived from any one match ...

    // ... then hook every matched method (regular, Shorts, and MDX if present):
    matches.forEach { match ->
        match.method.addInstruction(
            0,
            "invoke-direct { p0, p1 }, ${match.classDef.type}->setChannelInformation($playerResponseType)V"
        )
    }
}
```

Use `matchAll(range)` instead of plain `matchAll()` whenever the number of matches is a meaningful
invariant you want validated — an unexpected count usually means the obfuscation pattern changed and
the patch needs review, rather than silently hooking the wrong number of call sites.

## Manual matching

```kotlin
// Match within a known class
val match = MyFingerprint.match(someClassDef)

// Match within a list of classes
val match = MyFingerprint.match(classes)
```

## Rules

1. Never use obfuscated names (`definingClass`, `name`) — they change every APK update
2. If a class/method is NOT obfuscated (e.g. framework classes), always use `definingClass` + `name` —
   and add nothing else unless the method is overloaded (see "Keep fingerprints minimal" above)
3. Prefer `string()` and `literal()` over raw opcode sequences
4. `OpcodesFilter.opcodesToFilters()` requires exact opcodes with no gaps — last resort only
5. Fingerprints match only once by default (cached) — shared safely between patches
6. Use `@Suppress("unused")` on top-level patch vals loaded reflectively
