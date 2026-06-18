# Sprint 12 wrap-up — Metadata Generator Base

| Field | Value |
|-------|-------|
| Milestone | M2 |
| Status | Partial |
| Wrap-up date | 2026-06-18 |
| App version | 0.1.0 |

## Completed

- `TunarrMetadataProvider` — SQLite show lookup
- `PlexClient` — connectivity + library refresh
- `MetadataNFOGenerator` / `MetadataGeneratorService` — TV/movie NFO write path, scan orchestration
- Metadata tab shell wired to `JobRunner`
- Closed issues: [#65](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/65)–[#67](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/67), [#69](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/69)

## Not completed / blockers

| Item | Blocker | Next step |
|------|---------|-----------|
| [#68](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/68) Fanart.tv client | Full artwork download stack from Python `MetadataDownloader` not ported | Implement Fanart.tv fetch + poster/banner write in `MetadataArtwork` |

## Evidence

- `MetadataGeneratorService.swift`, `TunarrMetadataProvider.swift`, `MetadataTabView.swift`
- [Sprint plan](../Sprint%20Plans/Sprint-12-metadata-generator-base.md)

## Next sprint

[Sprint 13 — Metadata Generator Extended](../Sprint%20Plans/Sprint-13-metadata-generator-extended.md)
