# Sprint 02 wrap-up — Core Services Bootstrap

| Field | Value |
|-------|-------|
| Milestone | M0 |
| Status | Complete |
| Wrap-up date | 2026-06-17 |
| App version | 0.1.0 |

## Completed

- `ConfigStore` — Application Support JSON, atomic writes
- Codable config schemas (`AppConfig`, `LibraryPathsConfig`)
- `LoggingService` — `os.Logger` subsystem `com.roto31.PlexNFOCreator`
- SwiftUI `@main` app with five-tab shell
- About screen via `VersionInfo`
- CI `swift test` with initial Core tests
- Closed issues: [#11](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/11)–[#16](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/16)

## Not completed / blockers

None.

## Evidence

- App launches with tab shell; config round-trip tests pass
- [Sprint plan](../Sprint%20Plans/Sprint-02-core-services-bootstrap.md)

## Next sprint

[Sprint 03 — Job Runner & Secrets](../Sprint%20Plans/Sprint-03-job-runner-secrets.md)
