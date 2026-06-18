# Sprint 03 — Job Runner & Secrets

| Field | Value |
|-------|-------|
| Milestone | M0 |
| Target app version | 0.1.0 |
| Sprint goal | Shared async job infrastructure and Keychain ready for modules. |
| Points budget | 20 / 20 |
| Duration | 2 weeks |
| Status | Complete |
| GitHub label | sprint-03 |

## Objective

JobRunner + ProgressSheet match preflight ProgressWindow contract; secrets in Keychain.

## User stories

| ID | Story | Points | Priority |
|----|-------|--------|----------|
| SN-01 | As a user I want progress feedback during long jobs so that I can cancel safely. | 10 | P0 |
| SN-02 | As a user I want API keys in Keychain so that secrets are not in JSON. | 5 | P0 |

## Tasks

| Pts | Task | GitHub issue | Acceptance criteria |
|-----|------|--------------|---------------------|
| 5 | KeychainStore API keys — CRUD for TMDB/TVDB keys. | `[Sprint 03][5] KeychainStore API keys` | Keys persist across launches. |
| 5 | JobRunner async events — AsyncStream; progress_cb/log_cb/cancel parity. | `[Sprint 03][5] JobRunner async events` | Cancel stops cooperative work. |
| 5 | ProgressSheet SwiftUI — ProgressView, log, cancel, Open Console. | `[Sprint 03][5] ProgressSheet SwiftUI` | Sheet presents from any tab. |
| 3 | PreflightService write probe — `.plex_nfo_write_test` in target dir. | `[Sprint 03][3] PreflightService write probe` | Matches preflight.py behavior. |
| 2 | JobRunner unit tests — Cancellation test. | `[Sprint 03][2] JobRunner unit tests` | Test passes in CI. |

**Point total: 20**

## Technical scope

**Modules / paths:**

- `JobRunner/`
- `ProgressSheet/`
- `KeychainStore/`
- `PreflightService/`
- `LibraryWriteProbe.swift`

**Python reference:** `preflight.py ProgressWindow (lines 661–931)`, `check_write_permission`

## Definition of Done

- [x] All tasks closed on [Kanban](https://github.com/users/roto31/projects/2/views/7)
- [x] `swift build` + `swift test` green (if code touched)
- [x] `CHANGELOG.md` `[Unreleased]` updated
- [x] Sprint review demo completed

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Keychain sandbox | Document entitlements for MAS path. |

## Dependencies

- **Depends on:** Sprint 02

## Sprint review notes

Completed 2026-06-18: `JobRunnerTests` (cancellation + success), `LibraryWriteProbe` (`.plex_nfo_write_test`), ProgressSheet Cancel + Open Console. Issues #17–#21 closed.

## Retrospective

_Keep / Stop / Start — to be filled at sprint end._
