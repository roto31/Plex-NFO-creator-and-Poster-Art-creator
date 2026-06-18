# Feasibility Study: Plex NFO Creator Suite → Native macOS Swift Application

**Document status:** Working draft for go/no-go and sprint planning  
**Repository analyzed:** `Plex-NFO-creator-and-Poster-Art-creator` (Python scripts, ~8,450 LOC across 7 modules)  
**Target platform (Phase 1):** macOS  
**Deferred:** Windows, Linux  
**Application root:** `Native macOS App/` — all GUI application source, Xcode project, assets, and macOS-specific code live here (100% of the native app; Python scripts remain in the repo root for CLI use during transition)  
**Prepared for:** Technical decision-makers  

---

## Executive Summary

Converting this repository into a self-contained native macOS app is **technically feasible** and aligns well with existing macOS-first behaviors (folder pickers, Notification Center, `~/Library/Logs/PlexNFOCreator/`, Console.app integration). The suite is already modular at the script level; the main work is reimplementing ~8,450 lines of Python (plus external tooling) in Swift and replacing tkinter/AppleScript UI with SwiftUI/AppKit.

**Recommendation:** Proceed in two phases. **Phase 1 (MVP)** ships the four core-suite modules (`scraper`, `extract_artwork`, `rename_movies`, shared preflight/logging) as a SwiftUI tabbed app with preserved JSON config formats and Keychain-backed secrets. **Phase 2** ports the Metadata Generator subsystem (~4,900 LOC, `requests`, optional PostgreSQL, launchd scheduling), which is substantially more complex and currently assumes server-style install paths (`/usr/local/etc/`, `/var/log/`).

**Critical pre-development decision:** Choose between a **full Swift port** (true self-contained app, highest upfront cost) vs. a **hybrid shell** (Swift UI orchestrating embedded/bundled Python for Phase 1, then incremental Swift migration). This document assumes the stated goal of a **self-contained Swift app** residing entirely under `Native macOS App/`, but flags hybrid as a de-risking option.

**HIG version note:** The request references “macOS 26.5.1.” No such macOS version exists as of June 2026. This document targets **current Apple Human Interface Guidelines for macOS** ([macOS HIG](https://developer.apple.com/design/human-interface-guidelines/designing-for-macos)) and recommends **macOS 14 (Sonoma) minimum deployment** with forward compatibility for macOS 15+. Verify deployment target against your user base before sprint 1.

---

## 1. Scope & Architecture

### 1.1 Current Repository Inventory

| Module | File | ~LOC | Role | Config today |
|--------|------|------|------|--------------|
| Shared preflight | `preflight.py` | 931 | Checks, progress UI, logging, notifications, ffmpeg install | N/A (library) |
| NFO scraper | `scraper.py` | 770 | TMDB/TVDB → `.nfo` XML | **API keys in source** (`TMDB_API_KEY`, `TVDB_API_KEY` lines 47–48) |
| Artwork extractor | `extract_artwork.py` | 1,085 | ffmpeg → `poster.jpg` | `plex-extract-artwork.conf` (JSON) |
| Movie renamer | `rename_movies.py` | 274 | Folder/file cleanup | CLI path only |
| Metadata Generator | `plex_metadata_generator.py` | 2,780 | Scheduled TV/movie NFO + Plex refresh | `plex-metadata-generator.conf` (JSON) |
| Metadata Generator Extended | `plex_metadata_generator_extended.py` | 2,085 | + Music (MusicBrainz, Apple MusicKit) | `plex-metadata-generator-extended.conf` |
| Health check | `health-check.py` | 521 | Diagnostics | Reads `/etc/plex-metadata-generator.conf` |

**Evidence:** README documents six user-facing scripts; core suite uses stdlib-only Python; Metadata Generator requires **`requests`** and optionally **`psycopg2`** for local MusicBrainz PostgreSQL.

### 1.2 Proposed Tab → Module Mapping

Each script becomes a **tab** in a single `NavigationSplitView` or toolbar-tabbed main window inside the native app:

| Tab | Source | Primary user actions |
|-----|--------|----------------------|
| **Rename** | `rename_movies.py` | Pick library folder, dry-run preview, apply renames |
| **Scraper** | `scraper.py` | Movies / TV mode, path selection, `--force`, run |
| **Artwork** | `extract_artwork.py` | Movies / TV / Music, dry-run vs extract, `--force` |
| **Metadata Generator** | `plex_metadata_generator*.py` | Manual run + schedule config (Phase 2) |
| **Health Check** | `health-check.py` | Read-only diagnostics report (Phase 2) |

**Settings** is not a tab—it is a separate **Settings window** (`Settings { }` scene in SwiftUI), per [macOS Settings pattern](https://developer.apple.com/design/human-interface-guidelines/settings).

**Design choice to resolve early:** Merge `plex_metadata_generator.py` and `_extended.py` into one tab with a “Music enabled” toggle, mirroring how `extract_artwork.py` handles multiple media types in one module.

### 1.3 Proposed Application Architecture

All paths below are relative to `Native macOS App/`:

```
Native macOS App/
├── PlexNFOCreator.xcodeproj
├── PlexNFOCreatorApp/              # SwiftUI @main, scenes, assets
│   ├── AppState.swift
│   ├── FirstLaunchCoordinator.swift
│   ├── MainWindow/               # Tabbed module views
│   │   ├── RenameModuleView.swift
│   │   ├── ScraperModuleView.swift
│   │   ├── ArtworkModuleView.swift
│   │   └── MetadataGeneratorModuleView.swift  # Phase 2
│   └── Settings/                 # Settings scene
├── Packages/
│   └── PlexNFOCore/              # SPM: domain logic (portable core)
│       ├── ConfigStore/
│       ├── PreflightService/
│       ├── JobRunner/
│       ├── LoggingService/
│       └── Domain/               # Scraper, Artwork, Rename, MetadataGen
└── Resources/
    └── ffmpeg/                   # Bundled ffmpeg/ffprobe (macOS)
```

```
┌─────────────────────────────────────────────────────────────┐
│  PlexNFOCreatorApp (SwiftUI @main)                          │
│  ├── AppState / FirstLaunchCoordinator                      │
│  ├── SettingsScene (editable config + Keychain secrets)     │
│  └── MainWindow (tabbed modules)                            │
│       ├── RenameModuleView                                  │
│       ├── ScraperModuleView                                 │
│       ├── ArtworkModuleView                                 │
│       └── MetadataGeneratorModuleView (Phase 2)             │
├─────────────────────────────────────────────────────────────┤
│  PlexNFOCore (Swift Package — under Native macOS App/)      │
│  ├── ConfigStore (JSON read/write, schema validation)       │
│  ├── PreflightService (deps, permissions, ffmpeg)           │
│  ├── JobRunner (async work, cancellation, progress stream)  │
│  ├── LoggingService (os.Logger + optional file mirror)      │
│  └── Domain: Scraper / Artwork / Rename / MetadataGen       │
├─────────────────────────────────────────────────────────────┤
│  PlatformKit (macOS target in same package or app target)   │
│  ├── FolderPicker, Notifications, Sandbox/bookmarks         │
│  ├── FFmpegLocator (bundle or PATH)                         │
│  └── SchedulingService (launchd wrapper, Phase 2)             │
└─────────────────────────────────────────────────────────────┘
```

**Repository layout rule:** Python scripts, shell installers, and Docker assets stay at the repo root (`scraper.py`, `metadata-generator/`, etc.). **Only** the native GUI application—Xcode project, Swift sources, app icons, bundled tools, and macOS entitlements—lives under `Native macOS App/`.

**Framework choices (recommended):**

| Layer | Technology | Rationale |
|-------|------------|-----------|
| UI | **SwiftUI** (primary) + **AppKit bridges** where needed | Native tabs, Settings, sheets, `ProgressView`, `NSOpenPanel` via `NSViewRepresentable` if required |
| Core logic | **Swift** in `PlexNFOCore` SPM target | Testable; package colocated under `Native macOS App/Packages/` |
| Networking | `URLSession` | Replaces `urllib` / `requests` |
| XML/NFO | `XMLCoder` or `Foundation.XMLDocument` | Replaces `xml.etree` |
| Concurrency | `async/await`, `Task`, `AsyncStream` | Replaces `threading` + `ThreadPoolExecutor` |
| Logging | **`os.Logger`** (Unified Logging) | Console.app visibility per [Logging documentation](https://developer.apple.com/documentation/os/logging) |
| Secrets | **Keychain** | API keys, Plex token, OpenSubtitles credentials |
| Media extraction | **Bundled ffmpeg** (recommended) or `Process` to system ffmpeg | Matches current `subprocess` calls to `ffmpeg`/`ffprobe` |

Use **Xcode project + Swift Package** inside `Native macOS App/` for modular boundaries; distribute via Developer ID signing + notarization for Gatekeeper compliance.

### 1.4 Configuration File Handling

#### Formats to preserve

1. **`plex-extract-artwork.conf`** — JSON with `movies_library_roots`, `tv_library_roots`, `music_library_roots` and singular shortcuts (see repo root file).

2. **`plex-metadata-generator.conf` / `-extended.conf`** — Nested JSON: `plex`, `tvdb`, `tmdb`, `fanart_tv`, `subtitles`, `musicbrainz_db`, `scheduling`, etc.

3. **Scraper API keys** — Currently **not** in a config file; hardcoded in `scraper.py`. **Migration required** before Settings can edit them:
   - Introduce `plex-nfo-creator.conf` (or extend artwork config) with `tmdb.api_key` / `tvdb.api_key`.
   - On first launch, offer import from legacy `scraper.py` placeholders or manual entry.
   - **Uncertainty:** Confirm whether you want one unified config file or per-module files. Recommendation: **one app config** + backward-compatible readers for existing JSON files.

#### Storage locations (macOS)

| Config | Current (scripts) | Proposed (app) |
|--------|-------------------|----------------|
| Artwork roots | Repo-adjacent `plex-extract-artwork.conf` | `~/Library/Application Support/PlexNFOCreator/plex-extract-artwork.conf` |
| Metadata generator | `/usr/local/etc/plex-metadata-generator.conf` (install script) | Same path **or** Application Support (user-writable without sudo) |
| API keys | Source code / JSON placeholders | Keychain + non-secret fields in JSON |

Use **atomic writes** (`write to .tmp`, `rename`) matching `preflight.py`’s pattern for state files.

#### First-launch preflight (parity with scripts)

Replicate existing flows:

| Check | Scripts | Swift equivalent |
|-------|---------|------------------|
| Runtime | Python 3.8+ | N/A (bundled binary) |
| API keys | `check_api_keys()` | Keychain + Settings validation |
| ffmpeg | `check_ffmpeg()` + Homebrew auto-install | Detect bundled ffmpeg **or** offer to install via Homebrew (`Process`) |
| Write permission | `.plex_nfo_write_test` probe | `FileManager` + security-scoped bookmarks for sandbox |
| Library paths | AppleScript `choose folder` | `NSOpenPanel` / `.fileImporter` |

`extract_artwork.py` and metadata generator already use **first-run folder-picker dialogs** and optional “save to config?” prompts—map these to a **First Launch wizard** (single sheet sequence) that writes the same JSON keys.

### 1.5 Settings Menu Integration

Per [macOS HIG — Settings](https://developer.apple.com/design/human-interface-guidelines/settings):

- **Standard app menu → Settings…** (⌘,)
- Group fields mirroring JSON structure:
  - **Libraries:** path lists with +/- buttons and folder picker
  - **API Keys:** secure fields → Keychain
  - **Plex:** URL, token, library keys
  - **Advanced:** cache dir, logging level, scheduling (Phase 2)
- Validate on save; surface errors inline (not modal alert chains).
- **Import/Export config** for power users migrating from script installs.

---

## 2. Technical Feasibility

### 2.1 Straightforward to Port

| Capability | Python implementation | Swift port complexity |
|------------|----------------------|------------------------|
| Folder traversal + rename rules | `rename_movies.py` regex + `os.replace` | **Low** — `FileManager`, `NSRegularExpression` |
| JSON config load/save | `json` module | **Low** — `Codable` |
| Rate-limited HTTP to TMDB/TVDB | `urllib` + threading | **Medium** — `URLSession` + actor-based throttle |
| NFO XML generation | `xml.etree` + `minidom` | **Medium** — must match existing XML shape exactly (Plex compatibility) |
| Progress callbacks | `progress_cb`, `log_cb`, `cancel` kwargs | **Low** — `AsyncStream<JobEvent>` |
| Notifications | `osascript` display notification | **Low** — `UserNotifications` framework |
| Log files per run | `logging.FileHandler` → `~/Library/Logs/PlexNFOCreator/` | **Low** — optional mirror; primary = `os.Logger` |

### 2.2 Requires Architectural Change

| Capability | Challenge | Recommended approach |
|------------|-----------|---------------------|
| **ffmpeg artwork extraction** | Heavy `subprocess` usage in `extract_artwork.py` | Bundle signed ffmpeg/ffprobe in `Native macOS App/Resources/ffmpeg/`; invoke via `Process` |
| **ffmpeg auto-install via Homebrew** | `preflight._auto_install_ffmpeg()` runs `brew install` | Keep as optional “Install ffmpeg” action with explicit user consent; document that bundled ffmpeg is preferred for sandboxed distribution |
| **Metadata Generator scheduling** | launchd plist, cron, systemd installers | Phase 2: `SMAppService` / user `LaunchAgents` plist generation; in-app “Enable daily run” toggle |
| **Tunarr SQLite integration** | `sqlite3` reads external DB | Port queries to Swift `SQLite` (e.g. GRDB or swift-sqlite); validate schema against Tunarr versions |
| **Music: Apple MusicKit JWT** | `.p8` private key signing in Python | Use `CryptoKit` + JWT library; store key in Keychain |
| **Music: local MusicBrainz PostgreSQL** | `psycopg2` optional dependency | **Defer** or use REST-only path initially; PostgreSQL from a Mac app is uncommon and heavy |
| **Subtitle embedding** | ffmpeg embed in MG | Same as artwork—`Process` to bundled ffmpeg |
| **Scraper API keys in source** | Not config-driven today | **Config migration** before Settings parity |
| **Concurrent API workers** | `ThreadPoolExecutor(max_workers=4)` | `TaskGroup` with bounded parallelism; respect TMDB 4 req/s (`RATE_SLEEP = 0.28` in `scraper.py`) |

### 2.3 Language-Specific Dependencies → Swift Equivalents

| Python dependency | Used by | Swift replacement |
|-------------------|---------|-------------------|
| stdlib only (core) | scraper, rename, preflight | Native Foundation |
| `tkinter` | `ProgressWindow` in `preflight.py` | SwiftUI progress sheet |
| `subprocess` + `osascript` | dialogs, ffmpeg, notifications | AppKit/SwiftUI, `Process`, `UserNotifications` |
| `requests` | metadata generator, health-check | `URLSession` |
| `sqlite3` | metadata generator (Tunarr) | SQLite Swift package |
| `psycopg2` | health-check, optional MB DB | Defer / REST fallback |
| `webbrowser` | open API signup pages | `NSWorkspace.shared.open` |

### 2.4 Cross-Platform Considerations (Future Windows/Linux)

Decisions in Phase 1 that affect later ports:

| Decision | macOS-first | Cross-platform impact |
|----------|-------------|----------------------|
| Put domain logic in **SPM `PlexNFOCore`** under `Native macOS App/Packages/` | Yes | Reuse on Linux; Windows would need Swift on Windows or a shared Rust/Go core |
| **Keychain** for secrets | Yes | Abstract `SecretsStore` protocol; implement Credential Manager / libsecret later |
| **Bundled ffmpeg** per platform | Yes | Ship platform-specific binaries in release artifacts |
| **SwiftUI** for UI | Yes | SwiftUI on Windows is immature; long-term may need separate UI shells over shared core |
| **Config JSON format** unchanged | Yes | Enables script → app migration on all platforms |
| **`os.Logger`** | macOS/iOS only | Abstract `LogBackend`; file logs as portable fallback |

**Recommendation:** Treat `PlexNFOCore` as the portability boundary; keep macOS UI in the app target under `Native macOS App/`.

---

## 3. Progress Logging & Status UI

### 3.1 Real-Time Status Window Design

Replace tkinter `ProgressWindow` (`preflight.py` lines 661–931) with a native **modal or auxiliary window**:

| Element | Current (tkinter) | Proposed (SwiftUI) |
|---------|-------------------|-------------------|
| Progress bar | `ttk.Progressbar` | `ProgressView(value:total:)` |
| Counters | Done / Errors / Skipped labels | `LabeledContent` or HStack of badges |
| Log area | Scrolled `Text` widget, VS Code Dark+ colors | `TextEditor` or `ScrollView` + monospaced `Text`; semantic colors via asset catalog (support Light/Dark Mode per HIG) |
| Cancel | Sets `threading.Event` | `Task.cancel()` + cooperative checks in work loops |
| Open Log | `open -a Console` | Button opens Console.app filtered to subsystem |
| Completion | Native notification | `UNUserNotificationCenter` |

**HIG alignment:** Use a **sheet** attached to the module window for focused tasks; allow detaching to a separate window for long runs ([macOS windows](https://developer.apple.com/design/human-interface-guidelines/windows)). Do not use custom dark chrome as default—prefer system semantic colors and respect user appearance.

**Concurrency model:**

```swift
// Conceptual pattern matching existing work_fn API
func runJob<T>(_ work: @Sendable (JobProgressHandler) async throws -> JobSummary) async
```

Mirror existing callback contract: `progress_cb(current, total, name, status, done, errors, skipped)` and `log_cb(message, level)`.

### 3.2 macOS Native Logging (`os.log` + Console.app)

**Current behavior:** Python `logging` writes plain text to `~/Library/Logs/PlexNFOCreator/<script>_YYYY-MM-DD_HHMMSS.log` (documented in README and `preflight.log_directory()`).

**Target behavior (per requirements):** Emit to **Unified Logging** so entries appear in **Console.app** under a dedicated subsystem.

| Aspect | Implementation |
|--------|----------------|
| Subsystem | `com.roto31.PlexNFOCreator` (or your bundle ID) |
| Categories | `scraper`, `artwork`, `rename`, `metadata`, `preflight` |
| Levels | `debug`, `info`, `error` mapped from Python log levels |
| Persistence | Unified Logging persists per system policy; optionally **also** write human-readable files to `~/Library/Logs/PlexNFOCreator/` for parity and user “Open Log” expectations |
| Console filtering | Document filter: `subsystem:com.roto31.PlexNFOCreator` |

Reference: [Generating log messages](https://developer.apple.com/documentation/os/logging/generating_log_messages), [Viewing log messages in Console](https://support.apple.com/guide/console/).

**“Open Log” button:** Use `NSWorkspace.shared.open` for Console.app and pass subsystem hint via in-app help, or open the mirrored log file path (current script behavior at `preflight.open_log_in_viewer()`).

### 3.3 Log Persistence & Retrieval

| Mechanism | Purpose |
|-----------|---------|
| `os.Logger` | Primary; Console.app, Instruments |
| File mirror (optional) | Backward compatibility with script-era logs in `~/Library/Logs/PlexNFOCreator/` |
| In-app log viewer | Last run only in progress sheet; full history via Console or log folder in Finder |

---

## 4. macOS HIG Compliance

### 4.1 Key HIG Principles for This App

| Area | Guideline | Application |
|------|-----------|-------------|
| **Navigation** | Prefer sidebar or toolbar tabs for peer modules | Tab per script module; avoid deep nesting |
| **Settings** | Separate Settings window, not in main content | API keys, library paths, scheduling |
| **Progress** | Use standard `ProgressView`; explain what’s happening | Show current item name + counts |
| **Alerts** | Use sparingly; prefer inline validation | First-launch wizard instead of chained dialogs |
| **File access** | Use Open panels; respect sandbox | Security-scoped bookmarks for NAS/external drives |
| **Typography** | System fonts (SF Pro, SF Mono for logs) | Drop tkinter “VS Code Dark+” as fixed theme |
| **Accessibility** | VoiceOver labels on progress and log | Required for Mac App Store; good practice otherwise |

References: [Designing for macOS](https://developer.apple.com/design/human-interface-guidelines/designing-for-macos), [Toolbars](https://developer.apple.com/design/human-interface-guidelines/toolbars), [Sheets](https://developer.apple.com/design/human-interface-guidelines/sheets).

### 4.2 Conflicts with Current Script Behavior

| Script behavior | HIG conflict | Adjustment |
|-----------------|--------------|------------|
| Custom dark tkinter theme | Non-native appearance | System colors + Dark Mode support |
| Blocking `mainloop()` | No native app lifecycle | Async tasks; app remains responsive |
| AppleScript Yes/No for ffmpeg install | Non-standard install UX | Standard alert with explicit action; link to docs |
| API keys “edit scraper.py” message | Not appropriate for GUI app | Settings secure fields |
| Metadata generator `/var/log/` paths | Root/admin assumptions | User-writable Application Support logs |
| Health-check assumes `/etc/` config | Not macOS consumer pattern | Probe Application Support first |

### 4.3 Recommended Native Paradigms

- **Document-based optional:** Each module remembers last-used library path in config.
- **Toolbar:** Run, Dry Run, Force overwrite toggles per module.
- **Menu commands:** File → Open Library Folder, Window → Show Progress Log.
- **Help:** Link to existing wiki docs from Help menu.

---

## 5. Implementation Effort & Risk

### 5.1 Complexity Breakdown (Rough Engineering Estimates)

Assumes 1 senior Swift engineer, part-time domain review. Calendar times include UI polish and testing.

| Component | Effort | Notes |
|-----------|--------|-------|
| Xcode project in `Native macOS App/`, SPM layout, signing | 1–2 weeks | CI: `macos-latest` build + test |
| Config + Keychain + first-launch wizard | 2–3 weeks | JSON `Codable` schemas; migration from script configs |
| Shared `JobRunner` + progress sheet + `os.Logger` | 2 weeks | Replaces `preflight.ProgressWindow` |
| **Rename module** | 1 week | Lowest risk; good MVP validator |
| **Scraper module** | 3–4 weeks | API clients, XML parity, rate limiting, fuzzy match port |
| **Artwork module** | 3–4 weeks | ffmpeg bundling, music/TV hierarchy |
| **Settings UI** | 1–2 weeks | All editable config surfaces |
| **Metadata Generator (Phase 2)** | 8–12 weeks | Largest subsystem; scheduling, Plex API, music providers |
| **Health Check (Phase 2)** | 1–2 weeks | Mostly read-only diagnostics |
| QA, edge cases, large-library perf | 3–4 weeks | NAS paths, cancellation, resume semantics |

**Phase 1 MVP (core suite):** ~10–14 weeks  
**Full parity (incl. Metadata Generator):** ~20–28 weeks  

### 5.2 Key Technical Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| NFO XML output drift breaks Plex | High | Golden-file tests comparing Python vs Swift output on fixture libraries |
| ffmpeg licensing/bundling | Medium | Use GPL/LGPL-compliant distribution; document in app |
| App Sandbox vs NAS write access | High | Security-scoped bookmarks; possibly **non-sandboxed** Developer ID build initially |
| Metadata Generator scope creep | High | Phase 2; ship core suite first |
| Apple MusicKit key handling | Medium | Keychain + Apple doc compliance |
| Performance on 10k+ item libraries | Medium | Bounded concurrency; benchmark early |
| Losing script users’ workflows | Medium | Export configs; CLI scripts remain in repo during transition |

### 5.3 Third-Party Dependencies (Proposed)

| Dependency | Required? | Purpose |
|------------|-----------|---------|
| Bundled ffmpeg/ffprobe | **Yes** (recommended) | Artwork + subtitle embed |
| XMLCoder or similar | Optional | Ergonomic NFO XML |
| GRDB / SQLite.swift | Phase 2 | Tunarr DB reads |
| Swift JWT library | Phase 2 | Apple MusicKit |
| None for core HTTP | — | `URLSession` sufficient |

Core suite Python uses **stdlib only**; Metadata Generator adds **`requests`** today—no need to embed Python if porting to Swift.

---

## 6. Recommendations & Next Steps

### 6.1 Primary Technology Stack

| Layer | Choice |
|-------|--------|
| Location | `Native macOS App/` (100% GUI application) |
| UI | SwiftUI + Settings scene |
| Core | Swift Package (`PlexNFOCore` under `Native macOS App/Packages/`) |
| Logging | `os.Logger` + optional file mirror to `~/Library/Logs/PlexNFOCreator/` |
| Secrets | Keychain |
| Media | Bundled ffmpeg via `Process` |
| Distribution | Signed, notarized `.app` + optional Homebrew cask later |

### 6.2 Suggested Development Phases

#### Phase 1 — MVP (macOS core suite)

- Scaffold Xcode project under `Native macOS App/`
- Tabs: Rename, Scraper, Artwork
- First-launch preflight wizard
- Settings for library paths + API keys
- Progress sheet + Unified Logging
- Config: `plex-extract-artwork.conf` format + new unified secrets store
- **Out of scope:** Metadata Generator, scheduling, music providers

#### Phase 2 — Automation layer

- Metadata Generator tab (merge standard + extended)
- Health Check tab
- launchd scheduling UI
- Plex API refresh integration
- Music metadata providers

#### Phase 3 — Cross-platform

- Extract portable core; evaluate Windows/Linux UI strategy

### 6.3 Decisions Required Before Development

1. **Full Swift port vs hybrid Phase 1** (Swift UI + bundled Python runtime).
2. **Unified config file schema** vs per-module JSON files (and scraper key migration).
3. **Sandboxing:** Mac App Store (strict) vs Developer ID direct (easier file access).
4. **ffmpeg strategy:** bundle vs require system install.
5. **Metadata Generator config path:** keep `/usr/local/etc/` or standardize on Application Support.
6. **Minimum macOS version:** recommend **14.0** unless you need older.
7. **Tab scope:** six tabs vs merged Metadata Generator tab.

### 6.4 Immediate Validation Tasks (1–2 days)

- [ ] Generate NFO/XML fixtures from `scraper.py` for automated parity tests.
- [ ] Inventory all `ffmpeg` command lines in `extract_artwork.py` for bundling scope.
- [ ] Confirm target users need NAS/external volume writes (drives sandbox decision).
- [ ] Define unified `Codable` config schema covering artwork + scraper + MG fields.
- [ ] Prototype `os.Logger` + Console.app visibility with test subsystem in `Native macOS App/`.

---

## Appendix A: Evidence from Current Codebase

**Shared preflight contract** (all core scripts call `run_preflight` patterns):

```724:766:scraper.py
    # ── Preflight ──────────────────────────────────────────────────────────────
    logger, log_file = preflight.setup_logging("scraper")
    ...
    win = preflight.ProgressWindow(
        title    = f"Plex NFO Creator — {label}",
        total    = total,
        log_file = log_file,
    )
```

**Log directory on macOS:**

```42:48:preflight.py
    if SYSTEM == "Darwin":
        d = Path.home() / "Library" / "Logs" / "PlexNFOCreator"
```

**Artwork config format to preserve:**

```1:15:plex-extract-artwork.conf
{
  "movies_library_roots":  [],
  "tv_library_roots":      [],
  "music_library_roots":   [],
  ...
}
```

**Scraper keys not yet externalized (migration needed):**

```47:48:scraper.py
TMDB_API_KEY = "your_tmdb_api_key_here"
TVDB_API_KEY = "your_tvdb_api_key_here"
```

---

## Go / No-Go Summary

| Criterion | Assessment |
|-----------|------------|
| Technical feasibility | **Go** — no exotic blockers; ffmpeg and XML parity are main engineering challenges |
| HIG-compliant native UX | **Go** — tkinter/AppleScript maps cleanly to SwiftUI |
| Config preservation | **Go with migration** — scraper keys must move out of source |
| Self-contained app in `Native macOS App/` | **Go** — bundle ffmpeg; avoid Python runtime if full port |
| Timeline realism | **Phase 1 in ~3 months**; full suite **6–7 months** for one engineer |
| Risk level | **Medium** — dominated by Metadata Generator scope and sandbox/file access |

**Suggested go/no-go:** Approve **Phase 1 MVP** with explicit exit criteria (NFO/XML parity tests, artwork byte-identical on sample files, config round-trip). Re-evaluate Phase 2 funding after MVP dogfooding on a real Plex library.

---

## Documentation

- [Docs index](../docs/README.md) *(if present)*
- [Integration guide](../docs/INTEGRATION_GUIDE.md)
- [preflight reference](../docs/preflight.md)
- [Wiki home](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki)
