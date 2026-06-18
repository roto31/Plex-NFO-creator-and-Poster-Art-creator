# Sprint 05 — Rename Module

| Field | Value |
|-------|-------|
| Milestone | M1 |
| Target app version | 0.5.0 |
| Sprint goal | Rename tab functional — dry run and apply. |
| Points budget | 20 / 20 |
| Duration | 2 weeks |
| Status | Planned |
| GitHub label | sprint-05 |

## Objective

First feature tab ships; validates JobRunner end-to-end.

## User stories

| ID | Story | Points | Priority |
|----|-------|--------|----------|
| SN-01 | As a user I want to preview renames before applying so that I avoid mistakes. | 8 | P0 |
| SN-02 | As a user I want folder cleanup matching rename_movies.py so that scraper matches. | 5 | P0 |

## Tasks

| Pts | Task | GitHub issue | Acceptance criteria |
|-----|------|--------------|---------------------|
| 3 | Port rename regex rules — `clean_name`, `is_multipart`, `should_rename`. | `[Sprint 05][3] Port rename regex rules` | Unit tests match Python samples. |
| 5 | Port process_movies — Dry-run and apply with os.replace semantics. | `[Sprint 05][5] Port process_movies` | Folder renames work on temp dir. |
| 5 | Rename tab UI — Folder picker, dry-run/apply toggle. | `[Sprint 05][5] Rename tab UI` | UI triggers JobRunner. |
| 3 | Rename JobRunner integration — Progress + notifications. | `[Sprint 05][3] Rename JobRunner integration` | Completion notification fires. |
| 3 | Rename unit tests — Golden folder name cases. | `[Sprint 05][3] Rename unit tests` | CI green. |
| 1 | CHANGELOG Rename tab — Unreleased entry. | `[Sprint 05][1] CHANGELOG Rename tab` | CHANGELOG updated. |

**Point total: 20**

## Technical scope

**Modules / paths:**

- `Packages/PlexNFOCore/Sources/Domain/Rename/`
- `RenameModuleView.swift`

**Python reference:** `rename_movies.py`

## Definition of Done

- [ ] All tasks closed on [Kanban](https://github.com/users/roto31/projects/2/views/7)
- [ ] `swift build` + `swift test` green (if code touched)
- [ ] `CHANGELOG.md` `[Unreleased]` updated
- [ ] Sprint review demo completed

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| NAS paths | Test security-scoped bookmarks early. |

## Dependencies

- **Depends on:** Sprint 04 go

## Sprint review notes

_To be filled at sprint end._

## Retrospective

_Keep / Stop / Start — to be filled at sprint end._
