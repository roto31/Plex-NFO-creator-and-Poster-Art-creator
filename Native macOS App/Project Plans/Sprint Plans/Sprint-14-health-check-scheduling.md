# Sprint 14 — Health Check & Scheduling

| Field | Value |
|-------|-------|
| Milestone | M2 |
| Target app version | 0.9.0 |
| Sprint goal | Diagnostics tab + in-app daily run replaces install-macos.sh. |
| Points budget | 20 / 20 |
| Duration | 2 weeks |
| Status | **Partial** *(#79 open)* |
| GitHub label | sprint-14 |

## Objective

Health Check + scheduling complete M2.

## User stories

| ID | Story | Points | Priority |
|----|-------|--------|----------|
| SN-01 | As a user I want health diagnostics like health-check.py. | 8 | P0 |
| SN-02 | As a user I want in-app scheduling instead of install-macos.sh. | 7 | P0 |

## Tasks

| Pts | Task | GitHub issue | Acceptance criteria |
|-----|------|--------------|---------------------|
| 5 | Port health-check — macOS launchd probes, API pings. | `[Sprint 14][5] Port health-check` | Report matches Python structure. |
| 3 | Health Check tab — Read-only diagnostics UI. | `[Sprint 14][3] Health Check tab` | Tab shows status. |
| 5 | In-app scheduling service — LaunchAgent/SMAppService plist. | `[Sprint 14][5] In-app scheduling service` | Plist generated from Settings. |
| 3 | Scheduling Settings UI — Daily time, enable. | `[Sprint 14][3] Scheduling Settings UI` | Scheduling toggles work. |
| 3 | Subtitle embed integration — Reuse ffmpeg bundle. | `[Sprint 14][3] Subtitle embed integration` | Embed path works. |
| 1 | Distribution decision doc — MAS vs Developer ID. | `[Sprint 14][1] Distribution decision doc` | Doc in repo. |

**Point total: 20**

## Technical scope

**Modules / paths:**

- `HealthCheckModuleView.swift`
- `SchedulingService.swift`

**Python reference:** `health-check.py, scheduling/install-macos.sh`

## Definition of Done

- [x] All tasks closed on [Kanban](https://github.com/users/roto31/projects/2/views/7) *(#79 carry-over)*
- [x] `swift build` + `swift test` green (if code touched)
- [x] `CHANGELOG.md` `[Unreleased]` updated
- [x] Sprint review demo completed

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| SMAppService approval | Fallback LaunchAgent only. |

## Dependencies

- **Depends on:** Sprint 13

## Sprint review notes

**2026-06-17** — Phase 2 port: health-check diagnostics, Health Check tab, in-app scheduling (`SMAppService` + LaunchAgent fallback), scheduling Settings UI, distribution doc. Closed #75–#78, #80. **Carry-over:** [#79](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/79) subtitle embed integration deferred.

## Retrospective

_Keep / Stop / Start — to be filled at sprint end._
