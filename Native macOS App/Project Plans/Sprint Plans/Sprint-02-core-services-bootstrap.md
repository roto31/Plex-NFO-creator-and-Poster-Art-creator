# Sprint 02 — Core Services Bootstrap

| Field | Value |
|-------|-------|
| Milestone | M0 |
| Target app version | 0.1.0 |
| Sprint goal | Config paths, logging, minimal app window launches. |
| Points budget | 20 / 20 |
| Duration | 2 weeks |
| Status | Complete |
| GitHub label | sprint-02 |

## Objective

App launches with tab shell; config and logging infrastructure ready for modules.

## User stories

| ID | Story | Points | Priority |
|----|-------|--------|----------|
| SN-01 | As a user I want the app to launch with a clear shell so that modules have a home. | 5 | P0 |
| SN-02 | As a developer I want ConfigStore and os.Logger so that modules share infrastructure. | 8 | P0 |

## Tasks

| Pts | Task | GitHub issue | Acceptance criteria |
|-----|------|--------------|---------------------|
| 3 | ConfigStore Application Support — Application Support dir + atomic JSON write. | `[Sprint 02][3] ConfigStore Application Support` | Writes `.tmp` then rename. |
| 5 | Codable config schemas — Models for artwork + metadata-generator JSON (read). | `[Sprint 02][5] Codable config schemas` | Round-trip sample JSON. |
| 3 | LoggingService os.Logger — Subsystem `com.roto31.PlexNFOCreator` + categories. | `[Sprint 02][3] LoggingService os.Logger` | Logs visible in Console.app. |
| 5 | App entry and tab shell — SwiftUI `@main`, main window, empty tabs. | `[Sprint 02][5] App entry and tab shell` | App launches. |
| 2 | About screen version display — Show VERSION + dataRevision. | `[Sprint 02][2] About screen version display` | About matches VERSION file. |
| 2 | CI swift test green — At least one passing Core test. | `[Sprint 02][2] CI swift test green` | CI green. |

**Point total: 20**

## Technical scope

**Modules / paths:**

- `Packages/PlexNFOCore/Sources/ConfigStore/`
- `LoggingService/`
- `PlexNFOCreatorApp/`

**Python reference:** `preflight.py log_directory()`

## Definition of Done

- [x] All tasks closed on [Kanban](https://github.com/users/roto31/projects/2/views/7)
- [x] `swift build` + `swift test` green (if code touched)
- [x] `CHANGELOG.md` `[Unreleased]` updated
- [x] Sprint review demo completed

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Application Support permissions | Use standard user paths only. |

## Dependencies

- **Depends on:** Sprint 01

## Sprint review notes

Core services landed 2026-06-17: `ConfigStore`, Codable schemas, `LoggingService`, tab shell, About/version display, CI tests green. Issues #11–#16 closed; master board Status → Done.

## Retrospective

_Keep / Stop / Start — to be filled at sprint end._
