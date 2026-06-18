# Sprint 09 — Artwork Extraction Core

| Field | Value |
|-------|-------|
| Milestone | M1 |
| Target app version | 0.5.0 |
| Sprint goal | Bundled ffmpeg extracts posters matching Python SHA tests. |
| Points budget | 20 / 20 |
| Duration | 2 weeks |
| Status | Planned |
| GitHub label | sprint-09 |

## Objective

ffmpeg bundle + extraction logic ported.

## User stories

| ID | Story | Points | Priority |
|----|-------|--------|----------|
| SN-01 | As a user I want poster.jpg extracted like extract_artwork.py. | 13 | P0 |

## Tasks

| Pts | Task | GitHub issue | Acceptance criteria |
|-----|------|--------------|---------------------|
| 5 | Bundle ffmpeg binary — Universal binary + manifest bump. | `[Sprint 09][5] Bundle ffmpeg binary` | ffprobe runs from bundle. |
| 3 | FFmpegLocator — Process wrapper. | `[Sprint 09][3] FFmpegLocator` | Locates bundled binary. |
| 8 | Port artwork extraction — Three strategies, >1000 byte rule. | `[Sprint 09][8] Port artwork extraction` | SHA matches Python. |
| 3 | Artwork SHA tests — Fixture media. | `[Sprint 09][3] Artwork SHA tests` | CI green. |
| 1 | CHANGELOG ffmpeg bundle — Data tag. | `[Sprint 09][1] CHANGELOG ffmpeg bundle` | CHANGELOG updated. |

**Point total: 20**

## Technical scope

**Modules / paths:**

- `Resources/ffmpeg/`
- `Domain/Artwork/`
- `FFmpegLocator.swift`

**Python reference:** `extract_artwork.py lines 436–478`

## Definition of Done

- [ ] All tasks closed on [Kanban](https://github.com/users/roto31/projects/2/views/7)
- [ ] `swift build` + `swift test` green (if code touched)
- [ ] `CHANGELOG.md` `[Unreleased]` updated
- [ ] Sprint review demo completed

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| GPL compliance | NOTICE in app bundle. |

## Dependencies

- **Depends on:** Sprint 08

## Sprint review notes

_To be filled at sprint end._

## Retrospective

_Keep / Stop / Start — to be filled at sprint end._
