# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Documentation

- [Integration guide](docs/INTEGRATION_GUIDE.md)
- [Native macOS app feasibility](Native%20macOS%20App/macOS-Swift-Feasibility.md)
- [Project Plans index](Native%20macOS%20App/Project%20Plans/README.md)
- [Roadmap](Native%20macOS%20App/Project%20Plans/Roadmap/ROADMAP.md)
- [Wiki home](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki)

## [Unreleased]

### Build/CI

- GitHub Actions: `native-macos-app-ci.yml` (SwiftPM build/test on `macos-latest`, path-filtered) and `native-macos-app-release.yml` (unsigned release tarball on `native-v*` tags; notarization out of scope).

### Added

- **Sprint 03/04 completion** — `JobRunnerTests` (cancellation), `LibraryWriteProbe` (`.plex_nfo_write_test`), ProgressSheet Cancel + Open Console; metadata-generator golden fixtures (`mg-tvshow.nfo`, `mg-episode.nfo`, `mg-movie.nfo`) via extended `export_nfo_fixtures.py`; `MetadataFixtureTests` (26 unit tests total).
- **Phase 2 metadata / health / scheduling (native app)** — Ports core paths from `metadata-generator/plex_metadata_generator.py`, `plex_metadata_generator_extended.py`, and `health-check.py` into `PlexNFOCore`: Tunarr SQLite lookup, library scanning (TV/movies/music), NFO generation, Plex library refresh, MusicBrainz / iTunes / Apple MusicKit JWT providers, expanded health diagnostics, and in-app daily scheduling via `SMAppService` with `LaunchAgentScheduler` fallback (`~/Library/LaunchAgents/com.roto31.PlexNFOCreator.metadata.plist`). Metadata and Health Check tabs wired to `JobRunner` progress; 8 new unit tests (21 total).
- **M0 Swift foundation** (`Native macOS App/`) — SwiftPM package with `PlexNFOCore` library and `PlexNFOCreator` SwiftUI executable (macOS 14+); **`PlexNFOCreator.xcodeproj`** via [`project.yml`](Native%20macOS%20App/project.yml).
- Five-tab UI (Rename, Scraper, Artwork, Metadata, Health), first-launch wizard, Settings scene, progress sheet.
- [distribution.md](Native%20macOS%20App/docs/distribution.md) (Developer ID primary), [spikes.md](Native%20macOS%20App/docs/spikes.md) (NFO/ffmpeg GO).
- `VERSION` `0.1.0`, `BundleDataManifest.json` (`dataRevision.ffmpeg: 0`); 13 unit tests; `scripts/export_nfo_fixtures.py`.
- **`Native macOS App/`** directory as the dedicated root for the future Swift/SwiftUI macOS GUI (100% of native app source and Xcode assets).
- [macOS Swift feasibility study](Native%20macOS%20App/macOS-Swift-Feasibility.md) — scope, architecture, HIG alignment, logging (`os.log` / Console.app), effort estimates, and phased implementation plan for porting the Python script suite to a tabbed native app.
- **Project Plans** — [15 two-week SCRUM sprint plans](Native%20macOS%20App/Project%20Plans/Sprint%20Plans/) (20 story points max each), [markdown + mermaid roadmap](Native%20macOS%20App/Project%20Plans/Roadmap/ROADMAP.md), and [milestone trackers M0–M3](Native%20macOS%20App/Project%20Plans/Roadmap/Milestones/) with blocker templates.
- **Cursor rules** — `.cursor/rules/native-macos-app-scrum.mdc` and `native-macos-app-project-plans.mdc` for sprint discipline and documentation conventions.
- `scripts/add-issues-to-project.sh` — batch-add sprint issues to GitHub Project 2 after `gh auth refresh -s project`.
- `scripts/setup-github-projects.py` — configure master Project 2 (Sprint field, dates, estimates, status) and create 15 per-sprint GitHub project boards (#4–#18, including Sprints 11–15 / projects #14–#18); writes [github-sprint-boards.json](Native%20macOS%20App/Project%20Plans/github-sprint-boards.json).

### Changed

- GitHub Project 2 + Sprint boards 11–14 (projects #14–#17): closed Phase 2 issues **#60, #61, #63, #65–#67, #69–#78, #80**; Status → Done (2026-06-17). Carry-over open: **#62** (Apple MusicKit Settings fields), **#64** (legacy config migration), **#68** (Fanart.tv full client), **#79** (subtitle embed).
- GitHub Project 2: closed M0 carry-over **#21**, **#25**; Status → Done (2026-06-18). **M0 Accomplished.**
- `scripts/setup-github-projects.py` — refactored to use `gh project` CLI instead of hardcoded GraphQL field IDs: runtime `field-list` discovery, `item-edit` for field updates, `project copy` for sprint boards (cloned from master field layout), auth scope check at startup, `--check` dry-run mode, and `item-list --query` for sprint board population.
- Master project **Sprint Kanban** (view 7): board columns grouped by **Sprint** field — [view](https://github.com/users/roto31/projects/2/views/7). Repo Kanban links updated from view 1 (Status **Backlog** board) to view 7.

### Docs

- **Sprint wrap-ups** — [Sprint wrap-ups/](Native%20macOS%20App/Project%20Plans/Sprint%20wrap-ups/) (completed/partial sprint summaries; rule: `.cursor/rules/native-macos-app-sprint-wrapups.mdc`)
- Sprint tracking: [GitHub Project 2 Sprint Kanban](https://github.com/users/roto31/projects/2/views/7) · [Roadmap view](https://github.com/users/roto31/projects/2/views/4) · [Per-sprint boards](Native%20macOS%20App/Project%20Plans/github-sprint-boards.json) — see [Project Plans README](Native%20macOS%20App/Project%20Plans/README.md) for board URLs and view notes.
