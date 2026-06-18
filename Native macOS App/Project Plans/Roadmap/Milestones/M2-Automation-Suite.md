# Milestone M2 — Automation Suite

| Field | Value |
|-------|-------|
| Sprints | 11–14 |
| Target version | 0.9.0 |
| Status | **In Progress** |
| Completed date | — |

## Scope delivered

- Settings scene + first-launch wizard (all configs + Keychain secrets)
- **Metadata Generator** tab — `plex_metadata_generator.py` + `_extended.py` (music toggle)
- **Health Check** tab — `health-check.py`
- In-app scheduling replacing `metadata-generator/scheduling/install-macos.sh`

## Evidence

- Git tag / `Native macOS App/VERSION`: 0.1.0 (M2 code landed pre-0.9.0 bump)
- CI run URL: `native-macos-app-ci.yml` (SwiftPM build/test on macOS)
- Closed issues: #60, #61, #63, #65–#67, #69–#78, #80 (2026-06-17, Phase 2 port e18ffd28)

## Exit criteria checklist

- [ ] Sprints 11–14 all **Complete** *(Sprint 13 complete; 11, 12, 14 partial)*
- [x] All five tabs functional
- [x] Daily scheduling generates valid LaunchAgent/SMAppService plist
- [ ] MG NFO goldens (base + music) pass *(base TV scan tests pass; full golden suite pending)*

## Blockers (required if Status is Blocked or milestone not accomplished)

| Blocker | Impact | Owner | Resolution needed |
|---------|--------|-------|-------------------|
| [#62](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/62) Apple MusicKit nested Settings UI | MusicKit config not editable in Settings | — | Add `appleMusicKit` fields to Settings MG section |
| [#64](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/64) Legacy config migration | `/usr/local/etc` + repo file import incomplete | — | Full migration path beyond `importLegacyJSON` |
| [#68](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/68) Fanart.tv full client | Poster/art download deferred | — | Port full Fanart.tv download client |
| [#79](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/79) Subtitle embed | ffmpeg subtitle embed not wired | — | Integrate bundled ffmpeg subtitle embed path |

## Next actions

1. Close carry-over issues #62, #64, #68, #79
2. Bump `VERSION` to 0.9.0 when exit criteria met
3. Begin [Sprint 15](../../Sprint%20Plans/Sprint-15-release-1-0-0.md) after M2 accomplished
