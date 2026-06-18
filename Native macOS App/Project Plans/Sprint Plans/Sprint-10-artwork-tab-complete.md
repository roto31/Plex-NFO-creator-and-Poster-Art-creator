# Sprint 10 — Artwork Tab Complete

| Field | Value |
|-------|-------|
| Milestone | M1 |
| Target app version | 0.5.0 |
| Sprint goal | Artwork tab — movies/TV/music, dry-run and extract. |
| Points budget | 20 / 20 |
| Duration | 2 weeks |
| Status | Planned |
| GitHub label | sprint-10 |

## Objective

Artwork tab demo-ready; M1 milestone criteria met.

## User stories

| ID | Story | Points | Priority |
|----|-------|--------|----------|
| SN-01 | As a user I want artwork extraction for movies/TV/music from the app. | 13 | P0 |

## Tasks

| Pts | Task | GitHub issue | Acceptance criteria |
|-----|------|--------------|---------------------|
| 3 | Artwork config roots — Plural/singular keys from config. | `[Sprint 10][3] Artwork config roots` | Roots resolve correctly. |
| 8 | Port artwork process walks — movies/tvshows/music trees. | `[Sprint 10][8] Port artwork process walks` | Dry-run counts match Python. |
| 5 | Artwork tab UI — Type, extract, force. | `[Sprint 10][5] Artwork tab UI` | Full UI. |
| 2 | Import plex-extract-artwork.conf — First-launch migration. | `[Sprint 10][2] Import plex-extract-artwork.conf` | Legacy paths import. |
| 2 | CHANGELOG Artwork tab — Unreleased. | `[Sprint 10][2] CHANGELOG Artwork tab` | CHANGELOG updated. |

**Point total: 20**

## Technical scope

**Modules / paths:**

- `ArtworkModuleView.swift`
- `Domain/Artwork/Process/`

**Python reference:** `extract_artwork.py`

## Definition of Done

- [ ] All tasks closed on [Kanban](https://github.com/users/roto31/projects/2/views/7)
- [ ] `swift build` + `swift test` green (if code touched)
- [ ] `CHANGELOG.md` `[Unreleased]` updated
- [ ] Sprint review demo completed

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Music library depth | Progress granularity. |

## Dependencies

- **Depends on:** Sprint 09

## Sprint review notes

_To be filled at sprint end._

## Retrospective

_Keep / Stop / Start — to be filled at sprint end._
