# Sprint 13 — Metadata Generator Extended

| Field | Value |
|-------|-------|
| Milestone | M2 |
| Target app version | 0.9.0 |
| Sprint goal | Music mode + merged Metadata Generator tab. |
| Points budget | 20 / 20 |
| Duration | 2 weeks |
| Status | **Complete** |
| GitHub label | sprint-13 |

## Objective

Extended music providers integrated into single MG tab.

## User stories

| ID | Story | Points | Priority |
|----|-------|--------|----------|
| SN-01 | As a user I want music library NFOs like the extended generator. | 13 | P0 |

## Tasks

| Pts | Task | GitHub issue | Acceptance criteria |
|-----|------|--------------|---------------------|
| 5 | MusicBrainz REST client — Rate-limited REST. | `[Sprint 13][5] MusicBrainz REST client` | Lookup returns MBID. |
| 3 | iTunes Search client — No auth search. | `[Sprint 13][3] iTunes Search client` | Album metadata fetched. |
| 5 | MusicKit JWT signing — Keychain .p8 + JWT. | `[Sprint 13][5] MusicKit JWT signing` | Token generated. |
| 5 | Music NFO generators — album/artist/track goldens. | `[Sprint 13][5] Music NFO generators` | Music goldens pass. |
| 2 | MG music toggle UI — Enable music mode. | `[Sprint 13][2] MG music toggle UI` | Toggle persists. |

**Point total: 20**

## Technical scope

**Modules / paths:**

- `Domain/MetadataGenerator/Music/`
- `MG tab UI`

**Python reference:** `metadata-generator/plex_metadata_generator_extended.py`

## Definition of Done

- [x] All tasks closed on [Kanban](https://github.com/users/roto31/projects/2/views/7)
- [x] `swift build` + `swift test` green (if code touched)
- [x] `CHANGELOG.md` `[Unreleased]` updated
- [x] Sprint review demo completed

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| MusicKit key handling | Follow Apple entitlement rules. |

## Dependencies

- **Depends on:** Sprint 12

## Sprint review notes

**2026-06-17** — Phase 2 port: MusicBrainz, iTunes Search, MusicKit JWT signing, music NFO generators, MG music toggle UI. Closed #70–#74.

## Retrospective

_Keep / Stop / Start — to be filled at sprint end._
