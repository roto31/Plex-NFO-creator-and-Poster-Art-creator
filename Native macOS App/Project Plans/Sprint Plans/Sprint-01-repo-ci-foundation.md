# Sprint 01 — Repo & CI Foundation

| Field | Value |
|-------|-------|
| Milestone | M0 |
| Target app version | 0.1.0 |
| Sprint goal | Versioning files, CI green on empty Swift package, Xcode scaffold exists. |
| Points budget | 20 / 20 |
| Duration | 2 weeks |
| Status | Complete |
| GitHub label | sprint-01 |

## Objective

Deliver VERSION/CI/Xcode scaffold so every subsequent sprint builds on a notarized dev workflow.

## User stories

| ID | Story | Points | Priority |
|----|-------|--------|----------|
| SN-01 | As a developer I want SemVer and CI so that every merge is build-verified. | 5 | P0 |
| SN-02 | As a developer I want Xcode + PlexNFOCore so that feature work has a home. | 10 | P0 |
| SN-03 | As an operator I want CHANGELOG discipline so that releases are traceable. | 1 | P0 |

## Tasks

| Pts | Task | GitHub issue | Acceptance criteria |
|-----|------|--------------|---------------------|
| 2 | VERSION file and Xcode marketing version — Add `Native macOS App/VERSION` (`0.1.0`); wire `MARKETING_VERSION` in Xcode. | `[Sprint 01][2] VERSION file and Xcode marketing version` | `VERSION` exists; About placeholder reads it. |
| 2 | BundleDataManifest skeleton — Create `Resources/BundleDataManifest.json` with `dataRevision.ffmpeg: 0`. | `[Sprint 01][2] BundleDataManifest skeleton` | Valid JSON committed. |
| 1 | CHANGELOG Unreleased native app section — Extend root `CHANGELOG.md` for native app work. | `[Sprint 01][1] CHANGELOG Unreleased native app section` | Unreleased lists Project Plans + rules. |
| 5 | GitHub Actions CI workflow — `.github/workflows/native-macos-app-ci.yml` — macos-latest, path filter, pinned SHAs. | `[Sprint 01][5] GitHub Actions CI workflow` | Workflow runs on `Native macOS App/**` changes. |
| 5 | Xcode project scaffold — `PlexNFOCreator.xcodeproj` + empty app target. | `[Sprint 01][5] Xcode project scaffold` | Project opens in Xcode. |
| 5 | PlexNFOCore SPM package — Local package + empty test target. | `[Sprint 01][5] PlexNFOCore SPM package` | `swift build` succeeds. |

**Point total: 20**

## Technical scope

**Modules / paths:**

- `Native macOS App/VERSION`
- `Native macOS App/Resources/BundleDataManifest.json`
- `.github/workflows/`
- `PlexNFOCreator.xcodeproj`
- `Packages/PlexNFOCore/`

**Python reference:** `N/A`

## Definition of Done

- [x] All tasks closed on [Kanban](https://github.com/users/roto31/projects/2/views/7)
- [x] `swift build` + `swift test` green (if code touched)
- [x] `CHANGELOG.md` `[Unreleased]` updated
- [x] Sprint review demo completed

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Xcode project path with spaces | Quote paths in CI; use `working-directory`. |

## Dependencies

- **Depends on:** None

## Sprint review notes

M0 foundation delivered 2026-06-17: `VERSION` 0.1.0, `BundleDataManifest.json`, CI workflows, `PlexNFOCreator.xcodeproj`, and `PlexNFOCore` SwiftPM package. Issues #5–#10 closed; Sprint 01 board (#4) Status → Done.

## Retrospective

_Keep / Stop / Start — to be filled at sprint end._
