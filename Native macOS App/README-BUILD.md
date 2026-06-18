# Building Plex NFO Creator (Native macOS)

`Package.swift` is the **primary** build entry point for development and CI.

## Requirements

- macOS 14+
- Xcode 15+ or Swift 5.9+ toolchain

## SwiftPM commands

```bash
cd "Native macOS App"
swift build
swift test
swift run PlexNFOCreator
```

Release build:

```bash
swift build -c release
.build/release/PlexNFOCreator
```

## Xcode

**Option A — generated project (recommended for GUI work):**

```bash
open PlexNFOCreator.xcodeproj
```

Regenerate after `project.yml` changes: `xcodegen generate` (requires [XcodeGen](https://github.com/yonaskolb/XcodeGen)).

**Option B — Swift package:**

```bash
open Package.swift
```

Select the **PlexNFOCreator** executable scheme to run the SwiftUI app.

## Versioning

- Marketing version: `VERSION` (currently `0.1.0`)
- Bundled data revision: `Resources/BundleDataManifest.json` (`dataRevision.ffmpeg`)

## Layout

| Path | Purpose |
|------|---------|
| `Packages/PlexNFOCore/` | Shared library (config, jobs, rename, scraper, artwork, health) |
| `PlexNFOCreator/Sources/PlexNFOCreator/` | SwiftUI executable |
| `Resources/` | Bundled manifest (ffmpeg revision tracking) |
