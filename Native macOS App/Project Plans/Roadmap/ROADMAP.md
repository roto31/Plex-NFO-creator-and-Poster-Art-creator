# Product Roadmap — Plex NFO Creator (Native macOS App)

**Method:** 15 two-week SCRUM sprints · 20 story points max per sprint · **30 weeks** total  
**Repository:** [`Native macOS App/`](../../)  
**Planning index:** [Project Plans README](../README.md)

## Executive timeline

| Phase | Milestone | Sprints | Weeks | App version | Deliverable |
|-------|-----------|---------|-------|-------------|-------------|
| Foundation | M0 | 1–4 | 8 | 0.1.0 | Xcode, CI, Core services, spikes, fixtures |
| Core batch | M1 | 5–10 | 12 | 0.5.0 | Rename, Scraper, Artwork tabs |
| Automation | M2 | 11–14 | 8 | 0.9.0 | Settings, Metadata Generator, Health Check, scheduling |
| Release | M3 | 15 | 2 | 1.0.0 | QA, signed artifact, git tag |

## Milestone exit criteria

### M0 — Foundation (v0.1.0)

- `swift build` + `swift test` green on `macos-latest` CI
- `VERSION` = `0.1.0`; `BundleDataManifest.json` present
- JobRunner, ProgressSheet, Keychain, ConfigStore, LoggingService implemented
- NFO/ffmpeg spikes complete; `export_nfo_fixtures.py` produces goldens
- Doc: [M0-Foundation.md](Milestones/M0-Foundation.md)

### M1 — Core batch tools (v0.5.0)

- **Rename**, **Scraper**, and **Artwork** tabs demo-ready from UI
- Scraper + artwork NFO/poster parity tests pass
- Bundled ffmpeg in app resources
- Doc: [M1-Core-Batch-Tools.md](Milestones/M1-Core-Batch-Tools.md)

### M2 — Automation suite (v0.9.0)

- **Settings** + first-launch wizard for all configs/secrets
- **Metadata Generator** tab (TV/movies + music toggle)
- **Health Check** tab + in-app scheduling (replaces `install-macos.sh`)
- Doc: [M2-Automation-Suite.md](Milestones/M2-Automation-Suite.md)

### M3 — Release (v1.0.0)

- All five tabs + scheduling production-ready
- `VERSION` = `1.0.0`; dated CHANGELOG; git tag; release workflow artifact
- Doc: [M3-Release-1-0-0.md](Milestones/M3-Release-1-0-0.md)

## Architecture diagram

```mermaid
flowchart TB
  subgraph timeline [ReleaseTimeline]
    V01["v0.1.0 M0 Foundation"]
    V05["v0.5.0 M1 Core Batch"]
    V09["v0.9.0 M2 Automation"]
    V10["v1.0.0 M3 Release"]
  end
  V01 --> V05 --> V09 --> V10

  subgraph m0 [M0_Foundation_Sprints_1_to_4]
    S1[Sprint01_CI]
    S2[Sprint02_Core]
    S3[Sprint03_JobRunner]
    S4[Sprint04_Spikes]
    S1 --> S2 --> S3 --> S4
  end

  subgraph m1 [M1_CoreBatch_Sprints_5_to_10]
    S5[Sprint05_Rename]
    S6[Sprint06_ScraperHTTP]
    S7[Sprint07_ScraperNFO]
    S8[Sprint08_ScraperUI]
    S9[Sprint09_ArtworkCore]
    S10[Sprint10_ArtworkUI]
    S5 --> S6 --> S7 --> S8 --> S9 --> S10
  end

  subgraph m2 [M2_Automation_Sprints_11_to_14]
    S11[Sprint11_Settings]
    S12[Sprint12_MGBase]
    S13[Sprint13_MGExtended]
    S14[Sprint14_HealthSchedule]
    S11 --> S12 --> S13 --> S14
  end

  subgraph m3 [M3_Release_Sprint_15]
    S15[Sprint15_Release]
  end

  m0 --> m1 --> m2 --> m3
```

Source: [ROADMAP.mmd](ROADMAP.mmd)

## Sprint calendar (TBD at kickoff)

| Sprint | Milestone | Plan document |
|--------|-----------|---------------|
| 01 | M0 | [Sprint 01](../Sprint%20Plans/Sprint-01-repo-ci-foundation.md) |
| 02 | M0 | [Sprint 02](../Sprint%20Plans/Sprint-02-core-services-bootstrap.md) |
| 03 | M0 | [Sprint 03](../Sprint%20Plans/Sprint-03-job-runner-secrets.md) |
| 04 | M0 | [Sprint 04](../Sprint%20Plans/Sprint-04-spikes-fixtures.md) |
| 05 | M1 | [Sprint 05](../Sprint%20Plans/Sprint-05-rename-module.md) |
| 06 | M1 | [Sprint 06](../Sprint%20Plans/Sprint-06-scraper-http-layer.md) |
| 07 | M1 | [Sprint 07](../Sprint%20Plans/Sprint-07-scraper-nfo-generation.md) |
| 08 | M1 | [Sprint 08](../Sprint%20Plans/Sprint-08-scraper-tab-complete.md) |
| 09 | M1 | [Sprint 09](../Sprint%20Plans/Sprint-09-artwork-extraction-core.md) |
| 10 | M1 | [Sprint 10](../Sprint%20Plans/Sprint-10-artwork-tab-complete.md) |
| 11 | M2 | [Sprint 11](../Sprint%20Plans/Sprint-11-settings-first-launch.md) |
| 12 | M2 | [Sprint 12](../Sprint%20Plans/Sprint-12-metadata-generator-base.md) |
| 13 | M2 | [Sprint 13](../Sprint%20Plans/Sprint-13-metadata-generator-extended.md) |
| 14 | M2 | [Sprint 14](../Sprint%20Plans/Sprint-14-health-check-scheduling.md) |
| 15 | M3 | [Sprint 15](../Sprint%20Plans/Sprint-15-release-1-0-0.md) |

## External tracking

- [GitHub Project 2 — Kanban](https://github.com/users/roto31/projects/2/views/7)
- [GitHub Project 2 — Roadmap](https://github.com/users/roto31/projects/2/views/4)
