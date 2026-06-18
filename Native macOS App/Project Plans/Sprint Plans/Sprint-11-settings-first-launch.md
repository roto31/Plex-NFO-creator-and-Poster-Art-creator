# Sprint 11 — Settings & First Launch

| Field | Value |
|-------|-------|
| Milestone | M2 |
| Target app version | 0.9.0 |
| Sprint goal | All configs and secrets editable; first-launch wizard complete. |
| Points budget | 20 / 20 |
| Duration | 2 weeks |
| Status | **Partial** *(#62, #64 open)* |
| GitHub label | sprint-11 |

## Objective

Settings scene covers core + metadata-generator configs.

## User stories

| ID | Story | Points | Priority |
|----|-------|--------|----------|
| SN-01 | As a user I want Settings for all API keys and paths so that I never edit Python files. | 10 | P0 |
| SN-02 | As a new user I want a first-launch wizard so that setup matches script preflight. | 5 | P0 |

## Tasks

| Pts | Task | GitHub issue | Acceptance criteria |
|-----|------|--------------|---------------------|
| 5 | Settings library paths — +/- lists, folder pickers. | `[Sprint 11][5] Settings library paths` | Paths persist. |
| 5 | Settings API secrets — Keychain fields all providers. | `[Sprint 11][5] Settings API secrets` | No secrets in JSON. |
| 5 | Settings MG config editor — Nested JSON fields. | `[Sprint 11][5] Settings MG config editor` | MG config round-trip. |
| 3 | First-launch wizard — Paths + keys + save. | `[Sprint 11][3] First-launch wizard` | Skippable after first run. |
| 2 | Legacy config migration — /usr/local/etc + repo files. | `[Sprint 11][2] Legacy config migration` | Import succeeds. |

**Point total: 20**

## Technical scope

**Modules / paths:**

- `Settings/`
- `FirstLaunchCoordinator.swift`

**Python reference:** `extract_artwork prompt_missing_library_paths, metadata-generator prompts`

## Definition of Done

- [x] All tasks closed on [Kanban](https://github.com/users/roto31/projects/2/views/7) *(#62, #64 carry-over)*
- [x] `swift build` + `swift test` green (if code touched)
- [x] `CHANGELOG.md` `[Unreleased]` updated
- [x] Sprint review demo completed

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| MG config complexity | Phased fields by section. |

## Dependencies

- **Depends on:** Sprint 10

## Sprint review notes

**2026-06-17** — Phase 2 port (e18ffd28): Settings scene with library paths, Keychain API secrets, MG config fields (Tunarr, Plex keys, MusicBrainz, subtitles), first-launch wizard. Closed #60, #61, #63. **Carry-over:** [#62](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/62) Apple MusicKit nested Settings fields; [#64](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/64) legacy config migration (partial `importLegacyJSON` only).

## Retrospective

_Keep / Stop / Start — to be filled at sprint end._
