# Sprint 04 wrap-up — Spikes & Fixtures

| Field | Value |
|-------|-------|
| Milestone | M0 |
| Status | Complete |
| Wrap-up date | 2026-06-18 |
| App version | 0.1.0 |

## Completed

- NFO XML spike — `NFOSerializer` / `NFOPrettyXML`; verdict **GO** ([SPIKE-REPORT.md](../../docs/SPIKE-REPORT.md))
- ffmpeg strategy-1 spike — `ArtworkExtractor` + `FFmpegLocator` (system/bundled path)
- `scripts/export_nfo_fixtures.py` — scraper goldens (`sample-movie.nfo/json`)
- Metadata-generator goldens — `mg-tvshow.nfo`, `mg-episode.nfo`, `mg-movie.nfo`, `mg-tvshow.json`
- `MetadataFixtureTests` — Swift parity checks against MG fixtures
- Closed issues: [#22](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/22)–[#26](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/26) (including #25 on 2026-06-18)

## Not completed / blockers

None (issue #25 closed 2026-06-18 with metadata-gen fixture export).

## Evidence

- Fixtures: `Packages/PlexNFOCore/Tests/PlexNFOCoreTests/Fixtures/`
- M0 milestone **Accomplished** — [M0-Foundation.md](../Roadmap/Milestones/M0-Foundation.md)

## Next sprint

[Sprint 05 — Rename Module](../Sprint%20Plans/Sprint-05-rename-module.md) (M1)
