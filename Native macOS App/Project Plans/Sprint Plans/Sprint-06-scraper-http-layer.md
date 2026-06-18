# Sprint 06 — Scraper HTTP Layer

| Field | Value |
|-------|-------|
| Milestone | M1 |
| Target app version | 0.5.0 |
| Sprint goal | TMDB/TVDB clients with rate limiting and mocks. |
| Points budget | 20 / 20 |
| Duration | 2 weeks |
| Status | Planned |
| GitHub label | sprint-06 |

## Objective

Network layer ready for NFO generation sprints.

## User stories

| ID | Story | Points | Priority |
|----|-------|--------|----------|
| SN-01 | As the scraper I need rate-limited API clients so that keys are not banned. | 13 | P0 |

## Tasks

| Pts | Task | GitHub issue | Acceptance criteria |
|-----|------|--------------|---------------------|
| 5 | TMDB client rate limit — URLSession + throttle actor (`RATE_SLEEP 0.28`). | `[Sprint 06][5] TMDB client rate limit` | Mock tests pass. |
| 5 | TVDB client auth — v4 login + actor token cache. | `[Sprint 06][5] TVDB client auth` | Token reused across requests. |
| 3 | Port fuzzy_variants — NFKD folding parity. | `[Sprint 06][3] Port fuzzy_variants` | Variant lists match fixtures. |
| 3 | API mock test harness — URLProtocol + fixture loader. | `[Sprint 06][3] API mock test harness` | Tests run offline. |
| 2 | Scraper tab shell — Placeholder tab. | `[Sprint 06][2] Scraper tab shell` | Tab visible. |
| 2 | Wire API fixtures — Load Sprint 04 fixtures. | `[Sprint 06][2] Wire API fixtures` | Fixtures in test bundle. |

**Point total: 20**

## Technical scope

**Modules / paths:**

- `Networking/TMDB/`
- `Networking/TVDB/`
- `ScraperModuleView.swift (shell)`

**Python reference:** `scraper.py lines 71–145, 210–245`

## Definition of Done

- [ ] All tasks closed on [Kanban](https://github.com/users/roto31/projects/2/views/7)
- [ ] `swift build` + `swift test` green (if code touched)
- [ ] `CHANGELOG.md` `[Unreleased]` updated
- [ ] Sprint review demo completed

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| TVDB token race | Actor-isolated cache. |

## Dependencies

- **Depends on:** Sprint 05

## Sprint review notes

_To be filled at sprint end._

## Retrospective

_Keep / Stop / Start — to be filled at sprint end._
