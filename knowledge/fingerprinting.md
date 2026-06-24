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

## matchAllOrNull — match every occurrence

```kotlin
val filter = string("some string")
Fingerprint(filters = listOf(filter)).matchAllOrNull()?.forEach { match ->
    match.method.findInstructionIndicesReversedOrThrow(filter).forEach { index ->
        val register = match.method.getInstruction<OneRegisterInstruction>(index).registerA
        match.method.replaceInstruction(index, "const-string v$register, \"replacement\"")
    }
}
```

## Manual matching

```kotlin
// Match within a known class
val match = MyFingerprint.match(someClassDef)

// Match within a list of classes
val match = MyFingerprint.match(classes)
```

## Rules

1. Never use obfuscated names (`definingClass`, `name`) — they change every APK update
2. If a class/method is NOT obfuscated (e.g. framework classes), always use `definingClass` + `name`
3. Prefer `string()` and `literal()` over raw opcode sequences
4. `OpcodesFilter.opcodesToFilters()` requires exact opcodes with no gaps — last resort only
5. Fingerprints match only once by default (cached) — shared safely between patches
6. Use `@Suppress("unused")` on top-level patch vals loaded reflectively
