# Patch DSL Reference

## Patch types

```kotlin
bytecodePatch { }       // modifies Dalvik bytecode
resourcePatch { }       // modifies decoded XML resources (triggers full resource decode/build)
rawResourcePatch { }    // modifies arbitrary APK files without full resource decode
```

Use `rawResourcePatch` or `bytecodePatch` when possible — `resourcePatch` is slow because it decodes
and rebuilds all resources.

## bytecodePatch skeleton

```kotlin
@Suppress("unused")
val myPatch = bytecodePatch(
    name = "Short human-readable name",      // required for PatchLoader to pick it up
    description = "Does X in third person.", // optional but recommended
    default = true,                          // whether enabled by default
) {
    compatibleWith(COMPATIBILITY_YOUTUBE)    // or COMPATIBILITY_MUSIC, your own Compatibility object

    dependsOn(
        settingsPatch,
        versionCheckPatch,
        myResourcePatch,
    )

    extendWith("my-extension.mpe")           // optional: merge a precompiled DEX extension

    execute {
        // patch logic here
    }

    finalize {
        // called after all dependent patches finish (reverse order of execution)
    }
}
```

## Compatibility declaration

```kotlin
val COMPATIBILITY_YOUTUBE = Compatibility(
    name = "YouTube",
    packageName = "com.google.android.youtube",
    appIconColor = 0xFF0000,
    targets = listOf(
        AppTarget(version = "20.47.62"),
        AppTarget(version = "20.31.42", isExperimental = false),
        AppTarget(version = "21.19.280", isExperimental = true),
    )
)
```

- `isExperimental = true` marks a target as not yet officially supported
- Omit `targets` entirely to indicate compatibility with any version

## dependsOn

Dependencies are executed before the dependent patch. If a dependency throws, the dependent is skipped.
Use `dependsOn` to compose patches modularly.

```kotlin
dependsOn(
    lithoFilterPatch,        // sets up Litho filter infrastructure
    settingsPatch,           // injects settings activity
    clientContextHookPatch,  // hooks context for OS/endpoint hooks
    engagementPanelHookPatch,
)
```

## extendWith

Merges a compiled `.mpe` DEX file into `context.classes` before `execute` runs.
The `.mpe` file lives in `extensions/` of the patches repo and is referenced by filename only.

```kotlin
extendWith("ads-filter.mpe")
```

In smali, call methods from the extension using their full Smali descriptor:
```smali
invoke-static {}, Lapp/morphe/extension/youtube/patches/components/AdsFilter;->filterAds()Z
```

## execute block

The execute block runs in a `BytecodePatchContext` (or `ResourcePatchContext`/`RawResourcePatchContext`).

Key APIs in `BytecodePatchContext`:

```kotlin
execute {
    // Iterate all classes
    classDefForEach { classDef ->
        val mutableClass by lazy { mutableClassDefBy(classDef) }
        classDef.methods.forEach { method -> ... }
    }

    // Add Litho filter
    addLithoFilter("Lapp/morphe/extension/youtube/patches/components/MyFilter;")

    // Add engagement panel hook
    addEngagementPanelIdHook("LMyFilter;->hook(Ljava/lang/String;)Z")

    // Add OS name hook (for endpoint spoofing)
    addOSNameHook(Endpoint.BROWSE, "LMyClass;->hook(Ljava/lang/String;)Ljava/lang/String;")

    // Hook element proto (for proto-based filtering)
    hookElement("LMyFilter;->filterElement([B)[B")

    // Resource ID lookup
    val id = getResourceId(ResourceType.ID, "ad_attribution")
}
```

## Settings preferences

In `resourcePatch {}` depending on `settingsPatch`:

```kotlin
PreferenceScreen.GENERAL.addPreferences(
    SwitchPreference("morphe_my_key"),
    TextPreference(key = "morphe_text_key", titleKey = "...", summaryKey = "...", inputType = InputType.TEXT),
    ListPreference(key = "morphe_list_key", tag = "app.morphe.extension.shared.SortedListPreference"),
    NonInteractivePreference(key = "...", tag = "com.example.CustomPreference", selectable = true),
    IntentPreference(titleKey = "...", summaryKey = null, intent = newIntent(MORPHE_SETTINGS_INTENT)),
)
```

Available `PreferenceScreen` buckets (YouTube): `ADS`, `FEED`, `GENERAL`, `PLAYER`, `SHORTS`,
`SEEKBAR`, `SWIPE_CONTROLS`, `RETURN_YOUTUBE_DISLIKE`, `SPONSORBLOCK`, `MISC`, `VIDEO`,
`ALTERNATIVE_THUMBNAILS`.

## Shared library (official-patches-library)

Every patch bundle (`official-patches`, `brosssh-patches`, `hoodles-patches`) depends on the shared
`official-patches-library` repo instead of reimplementing common patch/extension code. It publishes two
artifacts:

```kotlin
// patches/build.gradle.kts
implementation(libs.morphe.patches.library)        // app.morphe:morphe-patches-library — shared patches/utils

// extensions/<app>/build.gradle.kts
compileOnly(libs.morphe.extensions.library)         // app.morphe:morphe-extensions-library — Utils, Logger, Setting, UI helpers
```

Declare the version catalog entries in `gradle/libs.versions.toml` pointing at `app.morphe:morphe-patches-library`
/ `app.morphe:morphe-extensions-library` — that's the entire setup for a new bundle, resolved from the
project's configured Maven repo. See `docs_read("SYSTEM")` (the "official-patches-library" section) for
the full breakdown of what each artifact provides and the local composite-build option for active
development against the library source.

## File and package conventions

```
patches/src/main/kotlin/app/morphe/patches/<app>/<category>/
  Fingerprints.kt   ← all fingerprints for the category
  MyFeaturePatch.kt ← patch implementation
```

- Top-level patch `val` must be annotated `@Suppress("unused")`
- Only patches with a `name` are loaded by `PatchLoader`
- Keep extension-only logic out of patch code (smali should just delegate to extension classes)
- Document non-obvious decisions with inline comments

## PatchException

Throw to signal failure at any point:
```kotlin
throw PatchException("Could not find required method")
```

## Patch options

```kotlin
val myPatch = bytecodePatch(name = "Patch") {
    val threshold by intOption(
        key = "threshold",
        default = 5,
        title = "Threshold",
        description = "Controls threshold",
    )

    execute {
        println(threshold)
    }
}
```

Set options after loading:
```kotlin
patches.first { it.name == "Patch" }.options["threshold"] = 10
```
