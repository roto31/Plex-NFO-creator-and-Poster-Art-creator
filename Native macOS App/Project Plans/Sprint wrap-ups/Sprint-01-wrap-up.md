# Sprint 01 wrap-up — Repo & CI Foundation

| Field | Value |
|-------|-------|
| Milestone | M0 |
| Status | Complete |
| Wrap-up date | 2026-06-17 |
| App version | 0.1.0 |

## Completed

- `Native macOS App/VERSION` (`0.1.0`) and `BundleDataManifest.json` (`dataRevision.ffmpeg: 0`)
- GitHub Actions: `native-macos-app-ci.yml`, `native-macos-app-release.yml` (`native-v*` tags)
- `PlexNFOCreator.xcodeproj` via XcodeGen `project.yml`
- SwiftPM: `PlexNFOCore` library + `PlexNFOCreator` executable scaffold
- Root `CHANGELOG.md` `[Unreleased]` native app section
- Closed issues: [#5](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/5)–[#10](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/10); Sprint board [#4](https://github.com/users/roto31/projects/4) → Done

## Not completed / blockers

None.

## Evidence

- `swift build` / `swift test` green on `macos-latest` (CI path-filtered)
- [Sprint plan](../Sprint%20Plans/Sprint-01-repo-ci-foundation.md)

## Next sprint

[Sprint 02 — Core Services Bootstrap](../Sprint%20Plans/Sprint-02-core-services-bootstrap.md)
