# Sprint 04 — Spikes & Fixtures

| Field | Value |
|-------|-------|
| Milestone | M0 |
| Target app version | 0.1.0 |
| Sprint goal | Technical go/no-go; golden fixture pipeline for parity tests. |
| Points budget | 20 / 20 |
| Duration | 2 weeks |
| Status | Complete |
| GitHub label | sprint-04 |

## Objective

Prove NFO and ffmpeg ports are feasible; establish golden test pipeline.

## User stories

| ID | Story | Points | Priority |
|----|-------|--------|----------|
| SN-01 | As a developer I want golden NFO fixtures so that Swift matches Python. | 10 | P0 |
| SN-02 | As a tech lead I want a spike report so that we commit to full Swift port. | 2 | P0 |

## Tasks

| Pts | Task | GitHub issue | Acceptance criteria |
|-----|------|--------------|---------------------|
| 5 | Spike NFO XML parity — Port `pretty_xml` + `build_movie_nfo` sample. | `[Sprint 04][5] Spike NFO XML parity` | Report: match or gap list. |
| 3 | Spike ffmpeg extraction — Strategy 1 via Process. | `[Sprint 04][3] Spike ffmpeg extraction` | Poster bytes from sample MP4. |
| 5 | export_nfo_fixtures scraper — `scripts/export_nfo_fixtures.py` scraper goldens. | `[Sprint 04][5] export_nfo_fixtures scraper` | Files under Tests/Fixtures/. |
| 5 | export_nfo_fixtures metadata-gen — Same for metadata-generator NFO. | `[Sprint 04][5] export_nfo_fixtures metadata-gen` | MG goldens committed. |
| 2 | Spike go/no-go report — `Native macOS App/docs/spike-report.md`. | `[Sprint 04][2] Spike go/no-go report` | Go/no-go decision recorded. |

**Point total: 20**

## Technical scope

**Modules / paths:**

- `scripts/export_nfo_fixtures.py`
- `PlexNFOCore/Tests/Fixtures/` (`mg-tvshow.nfo`, `mg-episode.nfo`, `mg-movie.nfo`)
- `docs/SPIKE-REPORT.md`

**Python reference:** `scraper.py`, `metadata-generator/plex_metadata_generator.py`

## Definition of Done

- [x] All tasks closed on [Kanban](https://github.com/users/roto31/projects/2/views/7)
- [x] `swift build` + `swift test` green (if code touched)
- [x] `CHANGELOG.md` `[Unreleased]` updated
- [x] Sprint review demo completed

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| NFO whitespace drift | Normalize or semantic DOM compare in tests. |

## Dependencies

- **Depends on:** Sprint 03

## Sprint review notes

Completed 2026-06-18: `export_nfo_fixtures.py` exports metadata-generator tvshow/episode/movie goldens; `MetadataFixtureTests` validates Swift `MetadataNFOGenerator` parity. Issues #22–#26 closed.

## Retrospective

_Keep / Stop / Start — to be filled at sprint end._
