# Sprint 07 — Scraper NFO Generation

| Field | Value |
|-------|-------|
| Milestone | M1 |
| Target app version | 0.5.0 |
| Sprint goal | NFO XML builders pass scraper golden tests. |
| Points budget | 20 / 20 |
| Duration | 2 weeks |
| Status | Planned |
| GitHub label | sprint-07 |

## Objective

Core Plex metadata output for movies and TV from scraper path.

## User stories

| ID | Story | Points | Priority |
|----|-------|--------|----------|
| SN-01 | As Plex I need identical NFO XML so that Local Media Assets match. | 16 | P0 |

## Tasks

| Pts | Task | GitHub issue | Acceptance criteria |
|-----|------|--------------|---------------------|
| 5 | Port build_movie_nfo — Movie XML all fields. | `[Sprint 07][5] Port build_movie_nfo` | Golden movie.nfo match. |
| 8 | Port TV NFO builders — tvshow, season, episode. | `[Sprint 07][8] Port TV NFO builders` | TV goldens pass. |
| 3 | Canonical NFOSerializer — Document declaration choice. | `[Sprint 07][3] Canonical NFOSerializer` | ADR or spike alignment. |
| 3 | Scraper NFO golden tests — CI runs goldens. | `[Sprint 07][3] Scraper NFO golden tests` | Tests green. |
| 1 | write_nfo skip logic — Skip unless --force. | `[Sprint 07][1] write_nfo skip logic` | Idempotent writes. |

**Point total: 20**

## Technical scope

**Modules / paths:**

- `NFOSerializer/`
- `Domain/Scraper/NFO/`

**Python reference:** `scraper.py build_*_nfo, pretty_xml`

## Definition of Done

- [ ] All tasks closed on [Kanban](https://github.com/users/roto31/projects/2/views/7)
- [ ] `swift build` + `swift test` green (if code touched)
- [ ] `CHANGELOG.md` `[Unreleased]` updated
- [ ] Sprint review demo completed

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| XML declaration | Match scraper.py line 163 exactly. |

## Dependencies

- **Depends on:** Sprint 06

## Sprint review notes

_To be filled at sprint end._

## Retrospective

_Keep / Stop / Start — to be filled at sprint end._
