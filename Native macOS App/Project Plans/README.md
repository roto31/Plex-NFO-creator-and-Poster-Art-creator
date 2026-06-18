# Project Plans — Plex NFO Creator (Native macOS App)

Planning artifacts for the Swift/SwiftUI port. **SCRUM:** 15 two-week sprints, 20 story points max each.

## Links

| Resource | Location |
|----------|----------|
| Feasibility study | [macOS-Swift-Feasibility.md](../macOS-Swift-Feasibility.md) |
| App README | [README.md](../README.md) |
| Sprint plans | [Sprint Plans/](Sprint%20Plans/) |
| Sprint wrap-ups | [Sprint wrap-ups/](Sprint%20wrap-ups/) |
| Roadmap | [Roadmap/](Roadmap/) |
| **Sprint Kanban** | [Plex NFO Creator — Sprint Kanban (view 7)](https://github.com/users/roto31/projects/2/views/7) |
| **Status board** | [Backlog by Status (view 1)](https://github.com/users/roto31/projects/2/views/1) |
| **Master Roadmap** | [Project 2 — Roadmap view](https://github.com/users/roto31/projects/2/views/4) |
| Sprint boards index | [github-sprint-boards.json](github-sprint-boards.json) |
| Issue index | [github-issues.json](github-issues.json) |

## GitHub projects

**Master board** — [Plex NFO Creator — Native macOS App (Master)](https://github.com/users/roto31/projects/2): **86 items** (82 sprint tasks + 4 roadmap milestones #87–#90). **Sprints 01–04 (M0):** complete; all sprint tasks closed on master board (2026-06-18). **Sprints 11–14 (M2, Phase 2 port):** 17 issues closed, Status → Done (2026-06-17); carry-over [#62](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/62), [#64](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/64), [#68](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/68), [#79](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/issues/79). Sprints 05–10, 15 remain in backlog.

**Per-sprint boards** (projects #4–#18) — one board per sprint, cloned from master via `gh project copy`; see [github-sprint-boards.json](github-sprint-boards.json) for URLs and project numbers.

| Sprint | Issues | Board (#) |
|--------|--------|-----------|
| 01 | 6 | [Repo & CI Foundation](https://github.com/users/roto31/projects/4) (#4) |
| 02 | 6 | [Core Services Bootstrap](https://github.com/users/roto31/projects/5) (#5) |
| 03 | 5 | [Job Runner & Secrets](https://github.com/users/roto31/projects/6) (#6) |
| 04 | 5 | [Spikes & Fixtures](https://github.com/users/roto31/projects/7) (#7) |
| 05 | 6 | [Rename Module](https://github.com/users/roto31/projects/8) (#8) |
| 06 | 6 | [Scraper HTTP Layer](https://github.com/users/roto31/projects/9) (#9) |
| 07 | 5 | [Scraper NFO Generation](https://github.com/users/roto31/projects/10) (#10) |
| 08 | 6 | [Scraper Tab Complete](https://github.com/users/roto31/projects/11) (#11) |
| 09 | 5 | [Artwork Extraction Core](https://github.com/users/roto31/projects/12) (#12) |
| 10 | 5 | [Artwork Tab Complete](https://github.com/users/roto31/projects/13) (#13) |
| 11 | 5 | [Settings & First Launch](https://github.com/users/roto31/projects/14) (#14) |
| 12 | 5 | [Metadata Generator Base](https://github.com/users/roto31/projects/15) (#15) |
| 13 | 5 | [Metadata Generator Extended](https://github.com/users/roto31/projects/16) (#16) |
| 14 | 6 | [Health Check & Scheduling](https://github.com/users/roto31/projects/17) (#17) |
| 15 | 6 | [Release 1.0.0](https://github.com/users/roto31/projects/18) (#18) |

**View setup (GitHub UI — not available via [`gh project`](https://cli.github.com/manual/gh_project) CLI):**

The [GitHub CLI `project` command](https://github.blog/developer-skills/github/github-cli-project-command-is-now-generally-available/) can create boards, fields, and items (`project create`, `field-create`, `item-add`, `project copy`), but **cannot configure view grouping**. On the master board:

- **Sprint Kanban (view 7)** — **Column by** → **Sprint** (configured; persisted as saved view **Sprint Kanban**).
- **Backlog (view 1)** — default **Status** columns (workflow board).
- **Roadmap (view 4)** — ensure **Start date** and **Target date** columns are visible (dates set per sprint and milestone issues #87–#90).

Re-run after new issues (requires [`project` auth scope](https://github.blog/developer-skills/github/github-cli-project-command-is-now-generally-available/#getting-started)):

```bash
gh auth refresh -h github.com -s project,read:project
python3 scripts/setup-github-projects.py --check   # preflight only
python3 scripts/setup-github-projects.py           # full idempotent setup
```

## Sprint status

| Sprint | Milestone | Version | Status | Plan |
|--------|-----------|---------|--------|------|
| 01 | M0 | 0.1.0 | **Complete** | [Sprint 01](Sprint%20Plans/Sprint-01-repo-ci-foundation.md) |
| 02 | M0 | 0.1.0 | **Complete** | [Sprint 02](Sprint%20Plans/Sprint-02-core-services-bootstrap.md) |
| 03 | M0 | 0.1.0 | **Complete** | [Sprint 03](Sprint%20Plans/Sprint-03-job-runner-secrets.md) |
| 04 | M0 | 0.1.0 | **Complete** | [Sprint 04](Sprint%20Plans/Sprint-04-spikes-fixtures.md) |
| 05 | M1 | 0.5.0 | Planned | [Sprint 05](Sprint%20Plans/Sprint-05-rename-module.md) |
| 06 | M1 | 0.5.0 | Planned | [Sprint 06](Sprint%20Plans/Sprint-06-scraper-http-layer.md) |
| 07 | M1 | 0.5.0 | Planned | [Sprint 07](Sprint%20Plans/Sprint-07-scraper-nfo-generation.md) |
| 08 | M1 | 0.5.0 | Planned | [Sprint 08](Sprint%20Plans/Sprint-08-scraper-tab-complete.md) |
| 09 | M1 | 0.5.0 | Planned | [Sprint 09](Sprint%20Plans/Sprint-09-artwork-extraction-core.md) |
| 10 | M1 | 0.5.0 | Planned | [Sprint 10](Sprint%20Plans/Sprint-10-artwork-tab-complete.md) |
| 11 | M2 | 0.9.0 | **Partial** *(#62, #64 open)* | [Sprint 11](Sprint%20Plans/Sprint-11-settings-first-launch.md) |
| 12 | M2 | 0.9.0 | **Partial** *(#68 open)* | [Sprint 12](Sprint%20Plans/Sprint-12-metadata-generator-base.md) |
| 13 | M2 | 0.9.0 | **Complete** | [Sprint 13](Sprint%20Plans/Sprint-13-metadata-generator-extended.md) |
| 14 | M2 | 0.9.0 | **Partial** *(#79 open)* | [Sprint 14](Sprint%20Plans/Sprint-14-health-check-scheduling.md) |
| 15 | M3 | 1.0.0 | Planned | [Sprint 15](Sprint%20Plans/Sprint-15-release-1-0-0.md) |

## Milestones

| Milestone | Sprints | Target | Doc |
|-----------|---------|--------|-----|
| M0 Foundation | 1–4 | v0.1.0 | [M0-Foundation.md](Roadmap/Milestones/M0-Foundation.md) |
| M1 Core batch | 5–10 | v0.5.0 | [M1-Core-Batch-Tools.md](Roadmap/Milestones/M1-Core-Batch-Tools.md) |
| M2 Automation | 11–14 | v0.9.0 | [M2-Automation-Suite.md](Roadmap/Milestones/M2-Automation-Suite.md) |
| M3 Release | 15 | v1.0.0 | [M3-Release-1-0-0.md](Roadmap/Milestones/M3-Release-1-0-0.md) |
