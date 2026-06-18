# Sprint 14 wrap-up — Health Check & Scheduling

| Field | Value |
|-------|-------|
| Milestone | M2 |
| Status | Partial |
| Wrap-up date | 2026-06-18 |
| App version | 0.1.0 |

## Completed

- `HealthCheckService` — config, API keys, library paths, Tunarr, scheduling, logs, disk space; optional network checks
- Health Check tab — pass/fail diagnostic list
- In-app daily scheduling — `DailySchedulingManager`, `SMAppService` (macOS 14+) + `LaunchAgentScheduler` fallback (`com.roto31.PlexNFOCreator.metadata.plist`)
- Scheduling Settings UI; `--metadata-scheduled` CLI entry
- [distribution.md](../../docs/distribution.md) — Developer ID primary (#80)
- Replaces `metadata-generator/scheduling/install-macos.sh` for macOS app path
- Closed issues: [#75](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/75)–[#78](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/78), [#80](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/80)

## Not completed / blockers

| Item | Blocker | Next step |
|------|---------|-----------|
| [#79](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/79) Subtitle embed | OpenSubtitles/Subdl + ffmpeg embed pipeline not ported | Port subtitle providers from Python; integrate with `ArtworkExtractor`/ffmpeg |

## Evidence

- `HealthCheckTabView.swift`, `LaunchAgentScheduler.swift`, `MetadataPhase2Tests`
- M2 **In Progress** — [M2-Automation-Suite.md](../Roadmap/Milestones/M2-Automation-Suite.md)
- [Sprint plan](../Sprint%20Plans/Sprint-14-health-check-scheduling.md)

## Next sprint

[Sprint 15 — Release 1.0.0](../Sprint%20Plans/Sprint-15-release-1-0-0.md) (after M1 Sprints 05–10)
