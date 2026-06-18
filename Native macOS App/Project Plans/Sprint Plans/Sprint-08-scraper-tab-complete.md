# Sprint 08 — Scraper Tab Complete

| Field | Value |
|-------|-------|
| Milestone | M1 |
| Target app version | 0.5.0 |
| Sprint goal | End-to-end movie/TV scrape from UI. |
| Points budget | 20 / 20 |
| Duration | 2 weeks |
| Status | Planned |
| GitHub label | sprint-08 |

## Objective

Scraper tab demo-ready at sprint review.

## User stories

| ID | Story | Points | Priority |
|----|-------|--------|----------|
| SN-01 | As a user I want to generate NFOs from the UI so that I skip the terminal. | 13 | P0 |

## Tasks

| Pts | Task | GitHub issue | Acceptance criteria |
|-----|------|--------------|---------------------|
| 5 | Port scraper process loops — process_movies/tvshows + cancel. | `[Sprint 08][5] Port scraper process loops` | Processes test library. |
| 5 | Scraper tab UI — Mode, path, force. | `[Sprint 08][5] Scraper tab UI` | Full UI wired. |
| 3 | Scraper progress integration — ProgressSheet + notify. | `[Sprint 08][3] Scraper progress integration` | Matches preflight UX. |
| 3 | Scraper preflight keys — Keychain validation. | `[Sprint 08][3] Scraper preflight keys` | Clear error if keys missing. |
| 2 | Scraper integration test — Mock APIs, temp dirs. | `[Sprint 08][2] Scraper integration test` | CI integration test. |
| 2 | CHANGELOG Scraper tab — Unreleased. | `[Sprint 08][2] CHANGELOG Scraper tab` | CHANGELOG updated. |

**Point total: 20**

## Technical scope

**Modules / paths:**

- `Domain/Scraper/`
- `ScraperModuleView.swift`

**Python reference:** `scraper.py main()`

## Definition of Done

- [ ] All tasks closed on [Kanban](https://github.com/users/roto31/projects/2/views/7)
- [ ] `swift build` + `swift test` green (if code touched)
- [ ] `CHANGELOG.md` `[Unreleased]` updated
- [ ] Sprint review demo completed

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Large libraries | Bounded concurrency. |

## Dependencies

- **Depends on:** Sprint 07

## Sprint review notes

_To be filled at sprint end._

## Retrospective

_Keep / Stop / Start — to be filled at sprint end._
