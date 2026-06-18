# Sprint 12 — Metadata Generator Base

| Field | Value |
|-------|-------|
| Milestone | M2 |
| Target app version | 0.9.0 |
| Sprint goal | TV/movie automation core — Tunarr, Plex refresh, MG NFO goldens. |
| Points budget | 20 / 20 |
| Duration | 2 weeks |
| Status | **Partial** *(#68 open)* |
| GitHub label | sprint-12 |

## Objective

Base metadata generator port without music.

## User stories

| ID | Story | Points | Priority |
|----|-------|--------|----------|
| SN-01 | As a user I want daily TV/movie NFO updates like plex_metadata_generator.py. | 13 | P0 |

## Tasks

| Pts | Task | GitHub issue | Acceptance criteria |
|-----|------|--------------|---------------------|
| 5 | Tunarr SQLite reader — Read tunarr.db paths from config. | `[Sprint 12][5] Tunarr SQLite reader` | Queries return expected rows. |
| 3 | Plex refresh client — Library refresh API. | `[Sprint 12][3] Plex refresh client` | Refresh call succeeds in test. |
| 8 | MG NFO generators base — show/episode/movie + goldens. | `[Sprint 12][8] MG NFO generators base` | MG goldens pass. |
| 3 | Fanart.tv client — Poster/art download. | `[Sprint 12][3] Fanart.tv client` | Downloads to cache. |
| 1 | MG tab shell — Tab placeholder. | `[Sprint 12][1] MG tab shell` | Tab visible. |

**Point total: 20**

## Technical scope

**Modules / paths:**

- `Domain/MetadataGenerator/`
- `MetadataGeneratorModuleView.swift`

**Python reference:** `metadata-generator/plex_metadata_generator.py`

## Definition of Done

- [x] All tasks closed on [Kanban](https://github.com/users/roto31/projects/2/views/7) *(#68 carry-over)*
- [x] `swift build` + `swift test` green (if code touched)
- [x] `CHANGELOG.md` `[Unreleased]` updated
- [x] Sprint review demo completed

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Tunarr schema drift | Version note in docs. |

## Dependencies

- **Depends on:** Sprint 11

## Sprint review notes

**2026-06-17** — Phase 2 port: Tunarr SQLite reader, Plex refresh client, MG NFO generators (TV/movie), Metadata tab shell. Closed #65–#67, #69. **Carry-over:** [#68](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/68) Fanart.tv full download client deferred.

## Retrospective

_Keep / Stop / Start — to be filled at sprint end._
