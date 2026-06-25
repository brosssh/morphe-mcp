# Smali Patterns in Morphe

Smali is the assembly language for Dalvik VM bytecode. Morphe patches inject smali instructions
directly into APK methods using the patcher API.

## Register types

| Prefix | Meaning |
|--------|---------|
| `v0`, `v1`, ... | local registers |
| `p0` | `this` (instance methods) or first parameter (static methods) |
| `p1`, `p2`, ... | parameters |

Registers are 32-bit. Wide types (long, double) occupy two consecutive registers: `v0` + `v1`.
Maximum usable register index is **v15** for most opcodes (range: v0–v15). Some opcodes (`invoke-range`,
`const-wide`) support higher indices but `addInstructions` without `cloneMutableAndPreserveParameters`
will fail if you exceed available registers.

## apply vs with — mutating a method

When a patch is **mutating the method itself** (calling `addInstructions`, `addInstruction`,
`replaceInstruction`, `removeInstruction`, adding fields/methods to a `classDef`, etc.), use
`method.apply { ... }`, not `with(method) { ... }`. `apply` returns the receiver — so the block reads
as "make these changes to this method" and you still hold a reference to the (now-mutated) method
afterward. `with` returns the block's *last expression*, not the receiver — it's for grouping reads off
a receiver to compute some other value, not for signaling a mutation.

```kotlin
// Mutating the method — use .apply
MyFingerprint.method.apply {
    addInstructions(0, "invoke-static {}, LMyExtension;->hook()V")
}
```

```kotlin
// Read-only scoping (no mutation of the receiver itself) — with() is fine here.
// Real example, VideoInformationPatch.kt: classDef is read repeatedly, but nothing mutates
// MdxPlayerDirectorSetVideoStageFingerprint or its classDef directly in this block.
with(MdxPlayerDirectorSetVideoStageFingerprint) {
    val mdxInitMethod = classDef.methods.first { MethodUtil.isConstructor(it) }
    val mdxSeekFingerprintResultMethod = MdxSeekFingerprint.match(classDef).method
    addPlayerInterfaceMethods(classDef, mdxSeekFingerprintResultMethod, ...)
}
```

`.let { it.method... }` is unrelated to this distinction — it's used to unwrap a `Fingerprint`'s match
result (`it.method`, `it.classDef`, `it.instructionMatches`) when you need `it` as a value rather than
as the implicit receiver; see `fingerprinting.md`.

## Common injection patterns

### Early return with feature flag

```smali
invoke-static {}, Lapp/morphe/extension/youtube/patches/MyPatch;->isEnabled()Z
move-result v0
if-eqz v0, :skip
return-void
:skip
nop
```

### Override a boolean value

```smali
invoke-static { v0 }, Lapp/morphe/extension/youtube/patches/MyPatch;->allowAds(Z)Z
move-result v0
```

### Call hook with an object argument

```smali
invoke-static { v0 }, Lapp/morphe/extension/youtube/patches/MyPatch;->onBind(Ljava/lang/Object;)V
```

### Conditional hide

```smali
invoke-static {}, LMyExtension;->hideEnabled()Z
move-result v0
if-nez v0, :show
return-void
:show
nop
```

### Inject at a filter match index

```kotlin
MyFingerprint.let {
    val index = it.instructionMatches[2].index
    val register = it.method.getInstruction<OneRegisterInstruction>(index).registerA
    it.method.addInstructionsWithLabels(
        index + 1,
        """
            invoke-static { v$register }, LMyExtension;->hook(Ljava/lang/Object;)V
        """
    )
}
```

### Replace a single instruction

```kotlin
it.method.replaceInstruction(
    index,
    "invoke-static { v$listReg, v$objectReg }, LMyExtension;->filter(Ljava/util/List;Ljava/lang/Object;)V"
)
```

### Hide a view (injectHideViewCall)

```kotlin
mutableMethod.injectHideViewCall(
    insertIndex,    // index after the view register is available
    viewRegister,   // register holding the View reference
    EXTENSION_CLASS,
    "hideMyView"    // static method in extension: public static void hideMyView(View view)
)
```

### insertLiteralOverride (feature flags)

Used to intercept a `const` instruction loading a feature flag integer/long and override the result:

```kotlin
MyFeatureFlagFingerprint.let {
    it.method.insertLiteralOverride(
        it.instructionMatches.first().index,
        "Lapp/morphe/extension/youtube/MyClass;->myFeatureEnabled(Z)Z"
    )
}
```

The extension method signature must match `(Z)Z` (takes the original boolean, returns the override).

## Adding a method to a class (ImmutableMethod)

Beyond editing existing instructions, you can add a brand-new method directly to a matched `ClassDef` —
this is how obfuscated classes get a stable, named entry point that extension code can call. See
`docs_read("stubbing")` for the full obfuscated-class-stubbing technique this enables.

```kotlin
someFingerprint.classDef.apply {
    methods.add(
        ImmutableMethod(
            type,                       // defining class = this same class
            "patch_methodName",
            listOf(/* ImmutableMethodParameter("J", null, "time"), ... */),
            "V",                         // return type descriptor
            AccessFlags.PUBLIC.value or AccessFlags.FINAL.value,
            null, null,
            MutableMethodImplementation(2),   // register count for the new method body
        ).toMutable().apply {
            addInstructions(
                0,
                """
                    # method body — typically bridges to a real member found via fingerprint
                    return-void
                """
            )
        }
    )
}
```

To make the new method satisfy a contract the extension can reference by type (not by the obfuscated
class name), also add an interface declared on the extension side before adding the method:

```kotlin
classDef.interfaces.add(EXTENSION_INTERFACE_DESCRIPTOR)  // e.g. "Lapp/morphe/extension/.../MyInterface;"
```

## Smali type descriptors

| Java type | Smali descriptor |
|-----------|-----------------|
| `void` | `V` |
| `boolean` | `Z` |
| `int` | `I` |
| `long` | `J` |
| `float` | `F` |
| `double` | `D` |
| `String` | `Ljava/lang/String;` |
| `Object` | `Ljava/lang/Object;` |
| `List` | `Ljava/util/List;` |
| `View` | `Landroid/view/View;` |
| `obfuscated class` | `L` (just the prefix, no full name) |
| `int[]` | `[I` |

## Instruction extension API

```kotlin
// Add instructions (no label support)
method.addInstructions(index, "smali string")

// Add instructions with :label support
method.addInstructionsWithLabels(index, "smali with :labels")

// Replace a single instruction
method.replaceInstruction(index, "new smali instruction")

// Remove an instruction
method.removeInstruction(index)

// Get a typed instruction at index
method.getInstruction<OneRegisterInstruction>(index).registerA
method.getInstruction<TwoRegisterInstruction>(index).registerA  // .registerB
method.getInstruction<FiveRegisterInstruction>(index).registerC // .registerD etc.
method.getInstruction<Instruction35c>(index)  // for invoke-virtual/static with 5 regs
method.getInstruction<Instruction31i>(index).wideLiteral  // for const with wide int/long
```

## addInstructionsWithLabels example

```kotlin
it.method.addInstructionsWithLabels(
    index,
    """
        invoke-static {}, LMyExtension;->shouldHide()Z
        move-result v0
        if-eqz v0, :allow
        const/4 v1, 0x0
        const/4 v2, 0x0
        :allow
        nop
    """
)
```

## Common gotchas

- **Register ceiling**: `addInstructions` is limited to v0–v15. Use `cloneMutableAndPreserveParameters()`
  (adds extra registers by shifting parameter registers) when the method is already register-tight.
- **Wide types**: `long` and `double` occupy 2 registers. A `const-wide` on `v0` also uses `v1`.
  Never use `v1` independently after a `const-wide v0`.
- **Label uniqueness**: label names (`:skip`, `:allow`) must be unique within the method.
  Prefix with something unique if injecting into the same method multiple times.
- **Instruction index drift**: adding/removing instructions shifts subsequent indices.
  Always modify from last index to first, or call `clearMatch()` + re-match after mutations.
- **invoke-static vs invoke-virtual**: extension methods hooked from smali must be `static`.
  Use `invoke-static { vN }, LMyClass;->method(...)V` not `invoke-virtual`.
