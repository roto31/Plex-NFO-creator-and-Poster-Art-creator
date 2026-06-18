# Sprint 11 wrap-up — Settings & First Launch

| Field | Value |
|-------|-------|
| Milestone | M2 |
| Status | Partial |
| Wrap-up date | 2026-06-18 |
| App version | 0.1.0 |

## Completed

- Settings scene — library paths, Keychain API secrets (TMDB/TVDB/Plex/Fanart)
- Metadata generator settings in `AppConfig` / Settings (Tunarr, Plex URL, music/subtitle toggles)
- First-launch wizard — library root + API keys
- Closed issues: [#60](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/60), [#61](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/61), [#63](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/63)

## Not completed / blockers

| Item | Blocker | Next step |
|------|---------|-----------|
| [#62](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/62) MG config editor — Apple MusicKit | Settings UI missing nested fields: `teamID`, `keyID`, `privateKeyPath`, `storefront` | Add MusicKit section to Settings; wire to `MetadataGeneratorSettings` |
| [#64](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/64) Legacy config migration | Only `importLegacyJSON` helper exists; no full import flow for all legacy conf files | Implement import for `plex-metadata-generator.conf` + artwork conf on first launch |

## Evidence

- Phase 2 port (2026-06-17); `SettingsView.swift`, `FirstLaunchWizardView.swift`
- [Sprint plan](../Sprint%20Plans/Sprint-11-settings-first-launch.md)

## Next sprint

[Sprint 12 — Metadata Generator Base](../Sprint%20Plans/Sprint-12-metadata-generator-base.md)
