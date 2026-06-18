# Native macOS App

This directory is the **sole home** for the Plex NFO Creator native macOS GUI application:

- Xcode project and targets
- SwiftUI views, Settings scene, and app lifecycle
- Swift packages (`PlexNFOCore`, platform adapters)
- App icons, entitlements, and bundled resources (e.g. ffmpeg)

Python scripts and CLI tooling remain at the repository root during the transition. New GUI work belongs here—not in `scraper.py`, `preflight.py`, or other script paths.

## Planning

- [macOS Swift feasibility study](macOS-Swift-Feasibility.md)
- [Project Plans index](Project%20Plans/README.md) — 15 SCRUM sprints (20 pts each)
- [Roadmap](Project%20Plans/Roadmap/ROADMAP.md) (markdown + mermaid)
- [GitHub Kanban](https://github.com/users/roto31/projects/2/views/7) · [GitHub Roadmap](https://github.com/users/roto31/projects/2/views/4)

## Status

Sprint 01 foundation implemented:

- SwiftPM package (`Package.swift`) with **PlexNFOCore** library + **PlexNFOCreator** SwiftUI app
- `PlexNFOCreator.xcodeproj` (XcodeGen `project.yml`) — open in Xcode or build with `swift build`
- `VERSION` `0.1.0` + `BundleDataManifest.json` (`dataRevision.ffmpeg: 0`)
- CI: `.github/workflows/native-macos-app-ci.yml` · release: `native-macos-app-release.yml` (`native-v*` tags)
- Config in `~/Library/Application Support/PlexNFOCreator/`; API keys in Keychain (`com.roto31.PlexNFOCreator`)

```bash
cd "Native macOS App"
swift build && swift test
```

