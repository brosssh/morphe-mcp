# Stubbing in Morphe

Extension code (Java/Kotlin compiled to a `.mpe` DEX, see `patch-dsl.md` → `extendWith`) frequently
needs to call methods on classes it cannot compile against directly: classes belonging to the target
app rather than Morphe, or classes whose name is obfuscated and only known at patch time. Morphe uses
two distinct **stubbing** techniques to bridge this gap, depending on which case applies.

## 1. Compile-time source stubs (`:stub` Gradle modules)

Use this when the real class has a **stable, known name** — an app library class or an Android SDK
class — but the extension module must not actually link against the real app/SDK jar.

A hand-written copy of the class, containing only the members the extension calls, is placed in a
sibling `:stub` Gradle module:

```
extensions/<app>/stub/src/main/java/<original/package/path>/<ClassName>.java   ← stub copy
extensions/<app>/build.gradle.kts                                              ← wires it in
```

Wiring, from `official-patches/extensions/reddit/build.gradle.kts` and
`extensions/youtube/build.gradle.kts`:

```kotlin
dependencies {
    compileOnly(project(":extensions:shared:library"))
    compileOnly(project(":extensions:reddit:stub"))   // <- the stub module
    compileOnly(libs.morphe.extensions.library)
}
```

`compileOnly` is the key: the stub is on the **compile classpath only**, so the extension source
resolves and compiles against it, but it's excluded from the runtime/packaged classpath. At runtime,
the actual class from the patched APK is what's loaded — the stub's method bodies are never executed,
so they just throw or return a dummy value.

There's also a project-wide stub module for the patches module itself: `patches/stub`, included via
`include(":patches:stub")` in `settings.gradle.kts` and consumed as `compileOnly(project(":patches:stub"))`
in `patches/build.gradle.kts`. It stubs Android SDK classes the patcher's own Kotlin code references but
shouldn't link against — e.g. `patches/stub/src/main/java/android/os/Build.java` stubs `Build.MODEL`,
`Build.MANUFACTURER`, etc. as `null` constants.

### Flavor A — stubbing an unmodified class, just enough surface to compile

`extensions/reddit/stub/src/main/java/com/reddit/domain/model/ILink.java`:

```java
public class ILink {
    public boolean getPromoted() {
        throw new UnsupportedOperationException("Stub");
    }
}
```

Used directly in the extension exactly like the real interface:
`extensions/reddit/src/main/java/.../HideAdsPatch.java`:
```java
if (!(item instanceof ILink iLink) || !iLink.getPromoted()) { ... }
```

### Flavor B — stubbing a method a bytecode patch adds/renames onto an existing class

The method doesn't exist on the real class at all until a bytecode patch injects it — by convention
such methods are prefixed `patch_` so it's obvious in extension code that they're synthetic.

`extensions/youtube/stub/src/main/java/com/airbnb/lottie/LottieAnimationView.java`:

```java
public class LottieAnimationView {
    public void patch_setAnimation(InputStream stream, String cacheKey) {
        throw new RuntimeException("stub");
    }
    public final void patch_setAnimation(int rawResInt) {
        throw new RuntimeException("stub");
    }
}
```

Called from `extensions/youtube/.../SeekbarColorPatch.java` as `view.patch_setAnimation(resourceId)`.

## 2. Bytecode interface injection (for obfuscated classes)

Use this when the class itself is **obfuscated** — there's no stable package/class name to write a
source-level stub against. The class is only discoverable per-APK-version via a `Fingerprint` at patch
time. Instead of a source file, the patch mutates the matched `ClassDef` directly inside `execute {}`:

1. Define an interface in the **extension** with the methods the extension needs to call, named with
   a `patch_` prefix and commented as synthetic:

   `extensions/youtube/src/main/java/.../VideoInformation.java`:
   ```java
   public interface PlaybackController {
       // Methods are added during patching.
       boolean patch_seekTo(long videoTime);
       void patch_seekToRelative(long videoTimeOffset);
       long patch_getVideoTime();
   }
   ```

2. In the patch, find the obfuscated class via its `Fingerprint`, add the interface to its
   `interfaces` list, and add a concrete method body for each interface method via `ImmutableMethod` —
   the body bridges to the *real* obfuscated member, whose name is now known from the fingerprint match:

   `NavigationBarHookPatch.kt#L213-244`:
   ```kotlin
   // Add interface for extensions code to call obfuscated methods.
   AppCompatToolbarBackButtonFingerprint.let {
       it.classDef.apply {
           interfaces.add(EXTENSION_TOOLBAR_INTERFACE)

           val definingClass = type
           val obfuscatedMethodName = it.originalMethod.name
           val returnType = "Landroid/graphics/drawable/Drawable;"

           methods.add(
               ImmutableMethod(
                   definingClass,
                   "patch_getNavigationIcon",
                   listOf(),
                   returnType,
                   AccessFlags.PUBLIC.value or AccessFlags.FINAL.value,
                   null,
                   null,
                   MutableMethodImplementation(2),
               ).toMutable().apply {
                   addInstructions(
                       0,
                       """
                           invoke-virtual { p0 }, $definingClass->$obfuscatedMethodName()$returnType
                           move-result-object v0
                           return-object v0
                       """
                   )
               }
           )
       }
   }
   ```

3. The extension then treats any instance as the interface type — it never needs to know the
   obfuscated class or method name:

   `NavigationBar.java`:
   ```java
   AppCompatToolbarPatchInterface toolbar = toolbarResultsRef.get();
   return toolbar != null && toolbar.patch_getNavigationIcon() != null;
   ```

More examples from `VideoInformationPatch.kt`:

- `VideoQualityFingerprint` → adds `EXTENSION_VIDEO_QUALITY_INTERFACE` with `patch_getQualityName()` /
  `patch_getResolution()`, each reading a field found by type (`fields.single { field.type == ... }`)
  rather than by obfuscated name.
- `SetVideoQualityFingerprint` → adds `EXTENSION_VIDEO_QUALITY_MENU_INTERFACE` with `patch_setQuality(...)`,
  which delegates to the real (matched) `setQualityMenuIndexMethod` after a `check-cast`.
- `addPlayerInterfaceMethods()` → adds `EXTENSION_PLAYER_INTERFACE` with `patch_seekTo`,
  `patch_seekToRelative`, `patch_getVideoTime` onto the player class, reusable across both the regular
  player and the MDX (cast) player class since both get the same interface.

Method bodies built this way commonly:
- Delegate to a real method found via the fingerprint match, by `invoke-virtual`/`invoke-direct` using
  its now-known name/descriptor (`patch_getNavigationIcon`, `patch_setQuality`).
- Read/write a field found by **type** rather than name when there's only one field of that type on the
  class (`fields.single { it.type == "Ljava/lang/String;" }`), as in `patch_getQualityName`.

## Choosing between the two

| | Source `:stub` module | Bytecode interface injection |
|---|---|---|
| Target class | Real, stable name (app library or Android SDK class) | Obfuscated, name only known after a `Fingerprint` match |
| Where defined | `extensions/<app>/stub/src/main/java/<pkg>/<Class>.java` | Inside the patch's `execute {}`, via `ClassDef.interfaces` / `ClassDef.methods` |
| How wired in | `compileOnly(project(":extensions:<app>:stub"))` | `classDef.interfaces.add(...)`; `classDef.methods.add(ImmutableMethod(...))` |
| What the extension compiles against | The stub class itself (excluded from runtime classpath) | A plain Java interface defined in the extension |
| Method naming | Same name as the real method, or `patch_`-prefixed if the patch injects/renames it | Always `patch_`-prefixed — the method never existed before patching |

Both achieve the same goal: give extension code a **compile-time-safe type** to call through, while the
actual implementation only exists once the APK has been patched.

## Rules

1. Stub method bodies in `:stub` modules must never run — throw (`UnsupportedOperationException`,
   `RuntimeException("stub")`) or return an inert default; the real implementation always wins at runtime.
2. Prefix any method that doesn't exist on the original class — whether stubbed at compile time or
   injected at the bytecode level — with `patch_`, so it's unambiguous in extension code that the method
   is synthetic.
3. For bytecode interface injection, the interface and its method signatures must be defined in the
   extension first; the patch's `ImmutableMethod` additions must match those signatures exactly.
4. Find obfuscated members to delegate to via `Fingerprint` (name/descriptor from the match), or by
   unique field **type** when there's exactly one field of that type — never hardcode an obfuscated name.
5. Use a source `:stub` module only for classes with a name that's actually stable across APK updates
   (app libraries, Android SDK); obfuscated app classes must use bytecode interface injection instead.
