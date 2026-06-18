# Sprint 15 — Release 1.0.0

| Field | Value |
|-------|-------|
| Milestone | M3 |
| Target app version | 1.0.0 |
| Sprint goal | Ship complete app — all five tabs, 1.0.0 tag, release artifact. |
| Points budget | 20 / 20 |
| Duration | 2 weeks |
| Status | Planned |
| GitHub label | sprint-15 |

## Objective

Production release of full native app.

## User stories

| ID | Story | Points | Priority |
|----|-------|--------|----------|
| SN-01 | As a user I want a signed 1.0.0 app with all five tabs. | 15 | P0 |

## Tasks

| Pts | Task | GitHub issue | Acceptance criteria |
|-----|------|--------------|---------------------|
| 5 | E2E dogfood all tabs — Real library subset. | `[Sprint 15][5] E2E dogfood all tabs` | Sign-off checklist complete. |
| 3 | NAS bookmark testing — Network volume writes. | `[Sprint 15][3] NAS bookmark testing` | NAS test doc. |
| 5 | Release workflow 1.0.0 — Build, notarize scope, upload. | `[Sprint 15][5] Release workflow 1.0.0` | Workflow runs on tag. |
| 3 | VERSION 1.0.0 release — CHANGELOG dated, git tag. | `[Sprint 15][3] VERSION 1.0.0 release` | Tag v3.0.0 or app version policy. |
| 3 | Accessibility pass — VoiceOver on tabs + progress. | `[Sprint 15][3] Accessibility pass` | A11y notes fixed. |
| 1 | README ship status — Native macOS App README. | `[Sprint 15][1] README ship status` | README says 1.0.0 shipped. |

**Point total: 20**

## Technical scope

**Modules / paths:**

- `Release workflow`
- `VERSION`
- `CHANGELOG`
- `all tabs QA`

**Python reference:** `N/A`

## Definition of Done

- [ ] All tasks closed on [Kanban](https://github.com/users/roto31/projects/2/views/7)
- [ ] `swift build` + `swift test` green (if code touched)
- [ ] `CHANGELOG.md` `[Unreleased]` updated
- [ ] Sprint review demo completed

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Notarization scope | May ship unsigned first release. |

## Dependencies

- **Depends on:** Sprints 01–14

## Sprint review notes

_To be filled at sprint end._

## Retrospective

_Keep / Stop / Start — to be filled at sprint end._
