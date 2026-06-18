# Milestone M0 — Foundation

| Field | Value |
|-------|-------|
| Sprints | 01–04 |
| Target version | 0.1.0 |
| Status | Accomplished |
| Completed date | 2026-06-18 |

Sprints 01–04 **Complete** (2026-06-18). All M0 issues closed including carry-over [#21](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/21) and [#25](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/25).

## Scope delivered

- SemVer `VERSION`, `BundleDataManifest.json`, CI on `macos-latest`
- Xcode project + `PlexNFOCore` Swift package
- ConfigStore, LoggingService (`os.Logger`), KeychainStore, JobRunner, ProgressSheet
- NFO/ffmpeg spikes; `export_nfo_fixtures.py` golden pipeline (scraper + metadata-generator)
- `JobRunnerTests`, `LibraryWriteProbe`, `MetadataFixtureTests` (26 unit tests)

## Evidence

- Git tag / `Native macOS App/VERSION`: `v0.1.0` / **0.1.0**
- CI workflows: [native-macos-app-ci.yml](../../../../.github/workflows/native-macos-app-ci.yml), [native-macos-app-release.yml](../../../../.github/workflows/native-macos-app-release.yml)
- Closed issues: [#5](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/5)–[#26](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/26) (M0 sprint tasks)

## Exit criteria checklist

- [x] Sprints 01–04 all **Complete** in [Project Plans README](../../README.md)
- [x] `swift build` + `swift test` green in CI (26 tests)
- [x] Spike report recommends **Go** — [SPIKE-REPORT.md](../../../docs/SPIKE-REPORT.md)
- [x] Golden fixtures under `PlexNFOCore/Tests/Fixtures/` (scraper + `mg-*.nfo`)

## Next actions

1. Begin [Sprint 05](../../Sprint%20Plans/Sprint-05-rename-module.md) (M1)
