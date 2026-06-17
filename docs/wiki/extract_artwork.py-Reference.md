# extract_artwork.py Reference

## Overview

`extract_artwork.py` extracts embedded cover artwork from video and audio files and saves it as Plex-compatible sidecar image files. It supports three media types:

| Mode | Input | Output |
|------|-------|--------|
| **Movies** | `.mp4`, `.m4v`, `.mkv`, `.mov`, `.avi` | `poster.jpg` per movie folder |
| **TV Shows** | `.mp4`, `.m4v`, `.mkv`, `.mov`, `.avi` | `poster.jpg` (show + season), `-thumb.jpg` per episode |
| **Music** | `.mp3`, `.m4a`, `.flac`, `.aac`, `.ogg`, `.opus`, `.wma`, `.wav` | `artist.jpg` per artist folder, `folder.jpg` per album subfolder |

**Why this is needed:** iTunes, Subler, and most audio encoders embed cover art inside the file's MP4/M4V/audio container. Apple TV.app and most media players read this directly. Plex does not — it requires artwork as separate sidecar files. This script bridges that gap.

On startup, `extract_artwork.py` runs preflight checks via [`preflight.py`](preflight.py-Reference): Python version, ffmpeg PATH check with auto-install offer, and write permission on the target directory. A progress window with a real-time log opens before processing begins.

---

## Command Line Interface

### New-style (config-driven, recommended)

```bash
python3 extract_artwork.py [options]
```

| Flag | Description |
|------|-------------|
| `--config PATH` | Config file (default: `plex-extract-artwork.conf` next to the script) |
| `--media-type TYPE` | `movies`, `tvshows`, `music`, or `all` (default: inferred from config) |
| `--extract` | Actually write files. **Without this, runs as a dry run.** |
| `--force` | Overwrite existing artwork files |
| `--no-prompts` | Skip first-run dialogs (for scheduled/unattended runs) |
| `--movie NAME` | Process only this movie folder name |
| `--show NAME` | Process only this TV show folder name |
| `--artist NAME` | Process only this music artist folder name |
| `--debug` | Enable verbose debug logging |

### Legacy positional-arg (backward compatible)

```bash
python3 extract_artwork.py <mode> <path> [--extract] [--force]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `mode` | Yes | `movies`, `tvshows`, or `music` |
| `path` | Yes | Absolute path to the root library directory |
| `--extract` | No | Actually write files (dry run without this) |
| `--force` | No | Overwrite existing artwork files |

Both invocation styles are fully supported. The legacy positional form takes priority when the first argument is `movies`, `tvshows`, or `music`.

---

## First-Run Setup

When run without `--no-prompts` and no library paths are configured, the script shows native OS dialogs to guide setup:

1. **Library type prompt** — "Do you have a [Movies/TV/Music] library to scan?" (per media type)
2. **Folder picker** — native macOS/Windows/Linux folder browser
3. **Multiple paths** — "Add another [type] folder?" for multi-volume libraries
4. **Save to config** — offer to save paths to the config file for future runs

After library paths are saved to `plex-extract-artwork.conf`, subsequent runs require no interaction when launched with `--no-prompts`.

---

## Configuration File

`plex-extract-artwork.conf` (JSON with comments) next to `extract_artwork.py`:

```json
{
  // Library roots — arrays support multiple drives / NAS shares
  "movies_library_roots":  ["/Volumes/Media/Movies"],
  "tv_library_roots":      ["/Volumes/Media/TV Shows"],
  "music_library_roots":   ["/Volumes/Media/Music"],

  // Single-volume shortcuts (auto-populated on first run with one path)
  "movies_library_root":   "",
  "tv_library_root":       "",
  "music_library_root":    ""
}
```

Multiple library roots are processed in order and counts are accumulated.

---

## Extraction Strategy

The script tries three ffmpeg strategies per file, in order. If one fails (output < 1000 bytes), it falls back to the next.

### Strategy 1 — Secondary Video Stream (iTunes/Subler format)

Subler and iTunes encode the cover art as a second video stream inside the MP4 container:
- Stream 0: actual movie video
- Stream 1: cover art image

```bash
ffmpeg -i "movie.m4v" -an -vframes 1 -map 0:v:1 -y "poster.jpg"
```

### Strategy 2 — `attached_pic` Disposition Flag

Some MP4 encoders and most MKV files use the `attached_pic` disposition flag for embedded artwork:

```bash
ffmpeg -i "movie.m4v" -map 0:v -map -0:V -vframes 1 -y "poster.jpg"
```

### Strategy 3 — Explicit `attached_pic` with `-vsync 2`

Fallback for encoders that set `attached_pic` but require explicit stream selection to prevent ffmpeg from discarding the stream as a duplicate:

```bash
ffmpeg -i "movie.m4v" -map 0:v:0 -vsync 2 -frames:v 1 -y "poster.jpg"
```

**There is no video frame fallback.** Only genuine embedded artwork is extracted. If all three strategies fail, the file is logged as `❌ no embedded artwork` and skipped.

---

## Movies Mode

For each movie folder:

1. Check for existing `poster.jpg` (skip if present and not `--force`)
2. Find first video file (`.m4v`, `.mp4`, `.mkv`, `.mov`, `.avi`)
3. Run strategies 1 → 2 → 3 until successful
4. Save as `poster.jpg` in the movie folder

### Output

```
Movies/
└── Back to the Future (1985)/
    ├── Back to the Future (1985).m4v
    ├── Movie.nfo
    └── poster.jpg          ← extracted here
```

---

## TV Shows Mode

TV show processing creates three types of artwork:

| Artifact | Source |
|----------|--------|
| Show `poster.jpg` | First episode of the first available season |
| Season `poster.jpg` | First episode of that season |
| Episode `-thumb.jpg` | The episode's own video file |

### Output Structure

```
TV Shows/
└── Breaking Bad/
    ├── poster.jpg                              ← show poster (from S01E01)
    ├── tvshow.nfo
    ├── Season 1/
    │   ├── poster.jpg                          ← season 1 poster
    │   ├── Breaking Bad - S01E01.m4v
    │   ├── Breaking Bad - S01E01-thumb.jpg     ← episode thumbnail
    │   ├── Breaking Bad - S01E02.m4v
    │   └── Breaking Bad - S01E02-thumb.jpg
    └── Season 2/
        ├── poster.jpg                          ← season 2 poster
        ├── Breaking Bad - S02E01.m4v
        └── Breaking Bad - S02E01-thumb.jpg
```

---

## Music Mode

For each artist folder:

1. Find first audio file in any album subdirectory → extract and save as `artist.jpg` in the artist root
2. For each album subdirectory: find first audio file → extract and save as `folder.jpg`

The album cover art serves as the artist image when no dedicated artist photo is embedded — this is the standard behavior for iTunes-encoded audio files.

### Supported Audio Formats

`.mp3`, `.m4a`, `.flac`, `.aac`, `.ogg`, `.opus`, `.wma`, `.wav`

### Output Structure

```
Music/
└── The Beatles/
    ├── artist.jpg                  ← extracted from first album's first track
    ├── Abbey Road/
    │   ├── folder.jpg              ← extracted from first audio file in album
    │   ├── 01 - Come Together.mp3
    │   └── 02 - Something.mp3
    └── Let It Be/
        ├── folder.jpg              ← extracted per-album
        └── 01 - Two of Us.mp3
```

`folder.jpg` is what Plex reads as the album cover when Local Media Assets is the top agent.

---

## Progress Window & Logging

The script opens a progress window before processing begins. Each item's result is logged in real time.

| Platform | Log path |
|----------|----------|
| macOS | `~/Library/Logs/PlexNFOCreator/extract_artwork_YYYY-MM-DD_HHMMSS.log` |
| Linux | `~/.local/share/plex-nfo-creator/logs/extract_artwork_YYYY-MM-DD_HHMMSS.log` |
| Windows | `%APPDATA%\PlexNFOCreator\Logs\extract_artwork_YYYY-MM-DD_HHMMSS.log` |

### Sample Log Output (Movies)

```
[  1/1760] ✓ → poster.jpg  Back to the Future (1985)
[  2/1760] ✓ → poster.jpg  Batman (1989)
[  3/1760] ⏭ already exists  Batman Begins (2005)
[  4/1760] ❌ no embedded artwork  Some Home Recording (1987)
```

### Final Summary (Music)

```
============================================================
COMPLETE — Music
  Artist images extracted: 142
  Album covers extracted:  891
  Already existed:         234
  No embedded artwork:     18
============================================================
```

An OS-native notification fires when processing completes.

---

## Multi-Volume Support

The config supports multiple library roots per media type. All roots are processed in sequence and counts accumulated:

```json
{
  "movies_library_roots": [
    "/Volumes/Drive1/Movies",
    "/Volumes/Drive2/Movies"
  ]
}
```

The legacy positional CLI accepts one path only. Use the config-driven CLI for multi-volume setups.

---

## Resume Safety

Without `--force`, the script skips any folder where the target file already exists. This means:

- The script can be interrupted and restarted safely
- Only unprocessed items are touched on subsequent runs
- TV episode thumbnail passes (~19,000+ files) can be run in multiple sessions overnight

---

## Functions Reference

| Function | Description |
|----------|-------------|
| `is_multipart(name)` | Returns True for multi-part/disc folder names — these are skipped |
| `extract_embedded_artwork(source, output)` | Tries all 3 strategies; returns True if successful |
| `_find_video(folder)` | First video file in a folder |
| `_find_audio(folder)` | First audio file in a folder |
| `_find_first_episode(season_path)` | First video file in a season folder |
| `process_movies(root, extract, force, ...)` | Movies mode; returns `(done, errors, skipped)` |
| `process_tvshows(root, extract, force, ...)` | TV shows mode; returns `(done, errors, skipped)` |
| `process_music(root, extract, force, specific_artist, ...)` | Music mode; returns `(done, errors, skipped)` |
| `_run_for_roots(roots, fn, ...)` | Dispatches `fn` across all library root paths |
| `load_config(config_file)` | Load JSON config; returns `{}` if file doesn't exist |
| `prompt_missing_library_paths(config, path)` | Show folder-picker dialogs for unconfigured roots |
| `_collect_library_paths(label)` | Dialog loop: ask yes/no then pick folder, repeat |
| `_resolve_roots(config, plural_key, singular_key)` | Resolve library root list from config |

---

## Troubleshooting

**ffmpeg not found**
Run the script and click Yes when offered auto-install. Or install manually:
```bash
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Linux
winget install ffmpeg        # Windows
```
After manual install, open a new terminal before re-running.

**"Permission denied" writing poster.jpg / folder.jpg**
Add Terminal (macOS) or your user to Full Disk Access in System Settings → Privacy & Security.

**poster.jpg or folder.jpg is very small / corrupted**
Output failed the `> 1000 byte` size check. The file was deleted. The source may lack embedded artwork — common for Blu-ray rips or downloaded files not from iTunes.

**Music: artist.jpg shows album cover, not artist photo**
This is expected. iTunes and most audio encoders embed album art, not artist photos. To get dedicated artist images, run the Metadata Generator (extended script) with Apple MusicKit configured — it downloads artist photos from the Apple Music catalog.

**No artwork extracted from any music file**
Your audio files may not have embedded album art. Embed artwork using MusicBrainz Picard, Mp3tag, or Subler before running this script.

**Progress window does not appear**
tkinter is not available. Install it (`brew install python-tk` on macOS, `sudo apt-get install python3-tk` on Linux) and re-run. Processing continues in the terminal without the GUI.
