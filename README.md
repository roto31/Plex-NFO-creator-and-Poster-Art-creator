# Plex NFO Creator & Poster Art Extractor

A suite of Python scripts that generate Plex-compatible `.nfo` metadata files and extract embedded poster artwork from your local media library — no GUI required, fully automated, resume-safe, and cross-platform (macOS, Linux, Windows).

> **Built because Plex's built-in metadata matching stopped working reliably on large libraries.** See the [full story on the Wiki →](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki)

---

## Scripts

### Core Suite

| Script | Purpose |
|--------|---------|
| [`scraper.py`](scraper.py) | Queries TMDB / TVDB and generates `.nfo` sidecar files for every movie, show, season, and episode |
| [`extract_artwork.py`](extract_artwork.py) | Extracts embedded cover art from MP4/M4V files and saves as `poster.jpg` sidecar files |
| [`rename_movies.py`](rename_movies.py) | Cleans folder and file names (strips quality tags, leading numbers, junk) before scraping |
| [`preflight.py`](preflight.py) | Shared module: dependency checks, auto-install, OS-native notifications, progress window, and logging |

### Metadata Generator (Automated Scheduling)

| Script | Purpose |
|--------|---------|
| [`metadata-generator/plex_metadata_generator.py`](metadata-generator/plex_metadata_generator.py) | Automated daily TV show NFO generator with Tunarr/TVDB/TMDB integration and Plex auto-refresh |
| [`metadata-generator/plex_metadata_generator_extended.py`](metadata-generator/plex_metadata_generator_extended.py) | Extended version with Music library support (iTunes Search API + Apple MusicKit + MusicBrainz) |
| [`metadata-generator/health-check.py`](metadata-generator/health-check.py) | System diagnostics — verifies config, API connectivity, scheduling, and disk space |

The Metadata Generator is a complementary automation layer: the core suite handles batch initial processing, while the Metadata Generator runs daily to pick up new content and trigger Plex refreshes automatically. See [`METADATA_GENERATOR_INTEGRATION.md`](METADATA_GENERATOR_INTEGRATION.md) for how to use them together.

---

## Requirements

- **Python 3.8+** (pre-installed on macOS; available at [python.org](https://www.python.org/downloads/) for Windows/Linux)
- **ffmpeg** — required by `extract_artwork.py` only; the script will offer to install it automatically on first run
- **TMDB API key** — free at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)
- **TVDB API key** — free at [thetvdb.com/api-information](https://thetvdb.com/api-information)

No third-party Python packages required — standard library only.

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator.git
cd Plex-NFO-creator-and-Poster-Art-creator

# 2. Add your API keys to scraper.py (lines 25–26)
#    TMDB_API_KEY = "your_key_here"
#    TVDB_API_KEY = "your_key_here"

# 3. (Optional) Clean up folder names first
python3 rename_movies.py "/Volumes/YourDrive/Movies"           # dry run preview
python3 rename_movies.py "/Volumes/YourDrive/Movies" --rename  # apply

# 4. Generate NFO metadata files
python3 scraper.py movies  "/Volumes/YourDrive/Movies"
python3 scraper.py tvshows "/Volumes/YourDrive/TV Shows"

# 5. Extract embedded poster artwork
python3 extract_artwork.py movies  "/Volumes/YourDrive/Movies"  --extract
python3 extract_artwork.py tvshows "/Volumes/YourDrive/TV Shows" --extract
```

On first run, each script performs a **preflight check** that verifies all requirements are met. If ffmpeg is missing, a dialog appears offering to install it automatically.

---

## What Happens When You Run a Script

### 1. Preflight Checks

Before any processing begins, each script checks:

| Check | Scripts |
|-------|---------|
| Python 3.8+ | All |
| TMDB + TVDB API keys set | `scraper.py` only |
| ffmpeg on PATH | `extract_artwork.py` only |
| Write permission on target directory | All (when writing files) |

If a check fails, you get a clear error message explaining what is missing and how to fix it.

### 2. Auto-Install (if ffmpeg is missing)

An OS-native dialog asks whether to install ffmpeg automatically:
- **macOS:** installs via Homebrew (installs Homebrew first if needed)
- **Linux:** uses `apt`, `dnf`, `pacman`, `zypper`, or Homebrew
- **Windows:** uses `winget` or Chocolatey
- **If you choose No:** detailed PATH setup instructions are printed and the ffmpeg download page opens in your browser

### 3. Progress Window

A dark-themed GUI window shows real-time progress:
- Progress bar with item count
- Done / Errors / Skipped counters
- Scrollable timestamped log
- Cancel button
- Open Log button

If tkinter is unavailable (headless server), output falls back to the terminal.

### 4. Log Files

Every run writes a timestamped log file that persists after the window closes:

| Platform | Location |
|----------|----------|
| macOS | `~/Library/Logs/PlexNFOCreator/` |
| Linux | `~/.local/share/plex-nfo-creator/logs/` |
| Windows | `%APPDATA%\PlexNFOCreator\Logs\` |

On macOS, logs open in Console.app. The **Open Log** button in the progress window opens the current run's log.

### 5. Completion Notification

An OS-native system notification appears when processing finishes, showing the done/errors/skipped summary.

---

## Usage Reference

### scraper.py

```bash
python3 scraper.py movies  <path>           # generate Movie.nfo for each movie folder
python3 scraper.py tvshows <path>           # generate tvshow/season/episode .nfo files
python3 scraper.py movies  <path> --force   # overwrite existing .nfo files
python3 scraper.py tvshows <path> --force
```

### extract_artwork.py

```bash
python3 extract_artwork.py movies  <path>                    # dry run (preview only)
python3 extract_artwork.py movies  <path> --extract          # extract poster.jpg files
python3 extract_artwork.py tvshows <path> --extract          # extract show/season/episode art
python3 extract_artwork.py movies  <path> --extract --force  # overwrite existing
```

### rename_movies.py

```bash
python3 rename_movies.py <path>           # dry run
python3 rename_movies.py <path> --rename  # apply renames
```

---

## Expected Folder Structure

### Movies
```
/Movies/
├── Back to the Future (1985)/
│   ├── Back to the Future (1985).mp4
│   ├── Movie.nfo       ← generated by scraper.py
│   └── poster.jpg      ← extracted by extract_artwork.py
```

### TV Shows
```
/TV Shows/
├── Breaking Bad/
│   ├── tvshow.nfo      ← generated by scraper.py
│   ├── poster.jpg      ← extracted by extract_artwork.py
│   ├── Season 1/
│   │   ├── season.nfo
│   │   ├── poster.jpg
│   │   ├── Breaking Bad - S01E01.mp4
│   │   ├── Breaking Bad - S01E01.nfo
│   │   └── Breaking Bad - S01E01-thumb.jpg
```

---

## After Running the Scripts

1. Open Plex Web UI (`http://localhost:32400/web`)
2. Go to **Settings → Libraries → [Your Library] → Edit**
3. Under **Agents**, move **Local Media Assets** to the **top** of the list
4. Save, then go to **⋯ → Manage Library → Refresh All Metadata**

---

## Platform Support

| Feature | macOS | Linux | Windows |
|---------|-------|-------|---------|
| NFO generation | ✓ | ✓ | ✓ |
| Artwork extraction | ✓ | ✓ | ✓ |
| Folder renaming | ✓ | ✓ | ✓ |
| Auto-install ffmpeg | Homebrew | apt/dnf/pacman/zypper | winget/choco |
| Native notifications | Notification Center | notify-send | System tray |
| Native dialogs | AppleScript | zenity / kdialog | PowerShell |
| Log viewer | Console.app | text editor | Notepad |

---

## Documentation

Full documentation, Mermaid process diagrams, NFO format reference, and troubleshooting guide are in the [Wiki](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki).

| Page | Contents |
|------|----------|
| [Installation & Setup](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Installation) | Requirements, API keys, first-run walkthrough |
| [preflight.py Reference](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/preflight.py-Reference) | All checks, auto-install, log format, progress window API |
| [scraper.py Reference](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/scraper.py-Reference) | NFO format, fuzzy matching, API usage |
| [extract_artwork.py Reference](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/extract_artwork.py-Reference) | Extraction strategies, TV show artwork structure |
| [rename_movies.py Reference](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/rename_movies.py-Reference) | Cleaning rules, what is and isn't renamed |
| [Process Flow Diagrams](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Diagrams) | Mermaid flowcharts for every decision path |
| [NFO Format Reference](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/NFO-Format-Reference) | XML structure, all supported fields |
| [Plex Configuration](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Plex-Configuration) | Agent setup, refresh procedure |
| [Troubleshooting](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Troubleshooting) | Common errors and fixes |
| [FAQ](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/FAQ) | Frequently asked questions |

### Metadata Generator Documentation

| File | Contents |
|------|----------|
| [`METADATA_GENERATOR_INTEGRATION.md`](METADATA_GENERATOR_INTEGRATION.md) | How the Metadata Generator fits alongside the core suite |
| [`metadata-generator/README.md`](metadata-generator/README.md) | 5-minute quick start, configuration reference, scheduling, troubleshooting |
| [`metadata-generator/INSTALL.md`](metadata-generator/INSTALL.md) | Detailed platform-specific install guide |
| [`docs/INTEGRATION_GUIDE.md`](docs/INTEGRATION_GUIDE.md) | Unified workflow guide for using both tools together |
| [`docs/WORKFLOWS_AND_DIAGRAMS.md`](docs/WORKFLOWS_AND_DIAGRAMS.md) | 13 Mermaid architecture and workflow diagrams |
| [`docs/MUSIC_GUIDE.md`](docs/MUSIC_GUIDE.md) | Setting up Music metadata with Spotify + MusicBrainz |
| [`docs/RELEASE_NOTES_v1.1.md`](docs/RELEASE_NOTES_v1.1.md) | v1.1 changelog |

---

## License

MIT
