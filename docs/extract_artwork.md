# extract_artwork.py — Reference Documentation

## Overview

`extract_artwork.py` extracts embedded cover art from video and audio files and saves it as Plex-compatible sidecar image files (`poster.jpg`, `-thumb.jpg`, `folder.jpg`, `artist.jpg`).

**Why this is needed:** iTunes, Subler, and most audio encoders embed artwork inside the file's container. Apple TV.app reads embedded art directly. **Plex does not** — it requires artwork as separate files in the same folder. This script bridges that gap.

Supports three media types:
- **Movies** → `poster.jpg` per movie folder
- **TV Shows** → `poster.jpg` (show/season level) + `-thumb.jpg` per episode
- **Music** → `artist.jpg` per artist folder + `folder.jpg` per album subfolder

On startup it runs preflight checks (Python version, ffmpeg PATH check with auto-install offer, write permission) via `preflight.py`, then opens a progress window and writes a timestamped log file. See [`preflight.py` Reference](preflight.md) for details.

---

## Requirements

- **Python 3.8+**
- **ffmpeg** — must be installed and in PATH. If not present, the script offers to install it automatically on first run.
  ```bash
  brew install ffmpeg         # macOS
  sudo apt install ffmpeg     # Linux
  winget install ffmpeg       # Windows
  ```

---

## Command Line Interface

### New-style (config-driven)

```bash
python3 extract_artwork.py [--config FILE] [--media-type TYPE] [--extract] [--force]
                           [--no-prompts] [--movie NAME] [--show NAME] [--artist NAME]
```

| Flag | Description |
|------|-------------|
| `--config PATH` | Config file path (default: `plex-extract-artwork.conf` next to the script) |
| `--media-type` | `movies`, `tvshows`, `music`, or `all` |
| `--extract` | Actually write files. **Without this, runs as a dry run.** |
| `--force` | Overwrite existing artwork files |
| `--no-prompts` | Skip first-run setup dialogs (for scheduled/automated runs) |
| `--movie NAME` | Process only this single movie folder name |
| `--show NAME` | Process only this single TV show folder |
| `--artist NAME` | Process only this single music artist folder |
| `--debug` | Enable verbose debug logging |

### Legacy positional-arg (backward compatible)

```bash
python3 extract_artwork.py <mode> <path> [--extract] [--force]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `mode` | Yes | `movies`, `tvshows`, or `music` |
| `path` | Yes | Absolute path to root media directory |
| `--extract` | No | Actually write files (dry run without this) |
| `--force` | No | Overwrite existing artwork files |

### Examples

```bash
# Config-driven — all media types at once
python3 extract_artwork.py --media-type all --extract

# Legacy — movie posters only
python3 extract_artwork.py movies "/Volumes/iTunes 5/Movies" --extract

# Legacy — TV episode thumbnails
python3 extract_artwork.py tvshows "/Volumes/iTunes 5/TV Shows" --extract

# Legacy — music album art
python3 extract_artwork.py music "/Volumes/Media/Music" --extract

# Re-extract everything (overwrite existing files)
python3 extract_artwork.py movies "/Volumes/iTunes 5/Movies" --extract --force

# Process only one artist
python3 extract_artwork.py --media-type music --artist "The Beatles" --extract
```

---

## Configuration File (`plex-extract-artwork.conf`)

```json
{
  // Run without arguments for guided first-run setup
  "movies_library_roots":  ["/Volumes/Media/Movies"],
  "tv_library_roots":      ["/Volumes/Media/TV Shows"],
  "music_library_roots":   ["/Volumes/Media/Music"],

  // Single-volume shortcuts (auto-populated on first run)
  "movies_library_root":   "",
  "tv_library_root":       "",
  "music_library_root":    ""
}
```

Arrays support multiple drives / NAS shares. Processed in order, counts accumulated.

---

## Output Files

### Movies

One `poster.jpg` per movie folder:

```
/Movies/Back to the Future (1985)/
├── Back to the Future (1985).m4v
├── Movie.nfo
└── poster.jpg      ← extracted here
```

### TV Shows

Three levels of artwork:

```
/TV Shows/Breaking Bad/
├── tvshow.nfo
├── poster.jpg              ← show poster (from S01E01)
├── Season 1/
│   ├── season.nfo
│   ├── poster.jpg          ← season poster (from S01E01)
│   ├── Breaking Bad - S01E01.m4v
│   ├── Breaking Bad - S01E01.nfo
│   └── Breaking Bad - S01E01-thumb.jpg   ← episode thumbnail
└── Season 2/
    ├── poster.jpg          ← season poster (from S02E01)
    ├── Breaking Bad - S02E01.m4v
    └── Breaking Bad - S02E01-thumb.jpg
```

### Music

`artist.jpg` at the artist level, `folder.jpg` per album:

```
/Music/The Beatles/
├── artist.jpg              ← from first audio file in first album
├── Abbey Road/
│   ├── folder.jpg          ← from first audio file in this album
│   ├── 01 - Come Together.mp3
│   └── 02 - Something.mp3
└── Let It Be/
    ├── folder.jpg          ← per-album
    └── 01 - Two of Us.mp3
```

`folder.jpg` is what Plex reads as the album cover when Local Media Assets is the top agent.

**Supported audio formats:** `.mp3`, `.m4a`, `.flac`, `.aac`, `.ogg`, `.opus`, `.wma`, `.wav`

---

## Extraction Strategy

The script tries three ffmpeg strategies in order per file. If one fails, it falls back to the next.

### Strategy 1 — Secondary Video Stream (iTunes/Subler Format)

Subler embeds artwork as a second video stream:
- Stream 0: actual video content
- Stream 1: cover art image

```bash
ffmpeg -i "movie.m4v" -an -vframes 1 -map 0:v:1 -y "poster.jpg"
```

### Strategy 2 — `attached_pic` Disposition (MKV / some MP4 / audio files)

```bash
ffmpeg -i "movie.m4v" -map 0:v -map -0:V -vframes 1 -y "poster.jpg"
```

### Strategy 3 — Explicit `attached_pic` with `-vsync 2`

Fallback for encoders that set `attached_pic` but require explicit selection:

```bash
ffmpeg -i "movie.m4v" -map 0:v:0 -vsync 2 -frames:v 1 -y "poster.jpg"
```

**There is no video frame fallback.** Only genuine embedded artwork is saved. If no artwork stream is found, the file is logged as `❌ no embedded artwork`.

---

## Resume Safety

Without `--force`, the script skips any folder where the target file already exists:
- Can be interrupted and restarted safely — only unfinished items are processed
- TV episode thumbnail passes (~19,000+ files) typically take 10–20 hours and are designed to run in multiple sessions overnight

---

## Performance

| Scope | Estimated Time |
|-------|---------------|
| Movie posters (1,760 folders) | ~30–60 minutes |
| TV show + season posters (~1,500) | ~30–60 minutes |
| Episode thumbnails (19,000+) | 10–20 hours |
| Music albums (1,000 albums) | ~30–60 minutes |

---

## Error Handling

| Situation | Behavior |
|-----------|---------|
| ffmpeg not found | Offer auto-install; exit if declined |
| All 3 strategies fail | Log `❌ no embedded artwork`, continue |
| Output file < 1000 bytes | Treat as failed, delete partial file |
| Write permission denied | Log error, continue |
| ffmpeg timeout (>30s per file) | Skip file, log timeout, continue |
| Cancel button clicked | Clean stop after current file |
