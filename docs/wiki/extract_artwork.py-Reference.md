# extract_artwork.py Reference

## Overview

`extract_artwork.py` extracts embedded poster artwork from iTunes/Subler-encoded MP4 files and saves it as Plex-compatible `poster.jpg` sidecar files. For TV shows, it also generates per-episode `-thumb.jpg` thumbnails and season-level `poster.jpg` files.

Embedded MP4 artwork (stored in the `covr` atom) is readable by Apple's TV.app natively. Plex cannot read embedded MP4 artwork — it requires sidecar `poster.jpg` files. This script bridges that gap.

On startup, `extract_artwork.py` runs preflight checks via [`preflight.py`](preflight.py-Reference): Python version, ffmpeg PATH check (with auto-install offer if missing), and write permission on the target directory. A progress window with a real-time log opens before processing begins.

---

## Command Line Interface

```bash
python3 extract_artwork.py <mode> <path> [--extract] [--force]
```

| Argument | Required | Values | Description |
|----------|----------|--------|-------------|
| `mode` | Yes | `movies` or `tvshows` | Which library to process |
| `path` | Yes | Absolute path | Root directory of the library |
| `--extract` | No | — | Actually write files. **Without this, runs as a dry run.** |
| `--force` | No | — | Overwrite existing `poster.jpg` / `-thumb.jpg` files |

### Examples

```bash
# Dry run — preview what would be extracted
python3 extract_artwork.py movies "/Volumes/iTunes 5/Movies"
python3 extract_artwork.py tvshows "/Volumes/iTunes 5/TV Shows"

# Actually extract
python3 extract_artwork.py movies "/Volumes/iTunes 5/Movies" --extract
python3 extract_artwork.py tvshows "/Volumes/iTunes 5/TV Shows" --extract

# Re-extract even if poster.jpg already exists
python3 extract_artwork.py movies "/Volumes/iTunes 5/Movies" --extract --force
```

---

## Requirement: ffmpeg

This script requires `ffmpeg` in your PATH. On first run without ffmpeg, a system dialog appears offering to install it automatically. See [Installation → Step 4](Installation#step-4--ffmpeg-for-extract_artworkpy-only) for details.

> **PATH requirement:** The script uses `shutil.which("ffmpeg")` to find ffmpeg — the same as the shell. If ffmpeg is not on PATH, the script cannot find it regardless of where it is installed on disk. Open a new terminal after manual installation.

---

## How Artwork Extraction Works

MP4 files from iTunes and Subler store poster art as a secondary video stream (the primary stream is the actual movie). ffmpeg can extract this stream as a JPEG image.

The script tries two strategies per file:

### Strategy 1: `-map 0:v:1`

```bash
ffmpeg -i input.m4v -map 0:v:1 -frames:v 1 -f image2 poster.jpg
```

Selects the **second video stream** (index 1). In iTunes/Subler files, stream 0 is the movie and stream 1 is the embedded artwork. This is the most reliable strategy for these files.

### Strategy 2: `attached_pic`

```bash
ffmpeg -i input.m4v -map 0:v -map -0:V -frames:v 1 -f image2 poster.jpg
```

Selects all video streams, then de-selects non-`attached_pic` streams. Catches artwork stored differently in some encoders.

After each strategy, the script checks `os.path.getsize(output_path) > 1000` to verify the file is a real image (not a zero-byte error output).

There is no video frame fallback — if neither strategy finds embedded artwork, the file is logged as having no embedded artwork. Extracting a video frame would produce episode stills, not poster art.

---

## Movies Mode

For each movie folder:

1. Check for existing `poster.jpg` (skip if present and not `--force`)
2. Find first video file (`.m4v`, `.mp4`, `.mkv`, `.mov`, `.avi`)
3. Run Strategy 1, then Strategy 2 if needed
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

### Show Poster (`poster.jpg` in show root)

Extracted from the **first episode of the first available season**. If the show folder already has a `poster.jpg`, it is skipped.

### Season Poster (`poster.jpg` in each season folder)

Extracted from the **first episode of that season**. If a season already has a `poster.jpg`, it is skipped.

### Episode Thumbnail (`{episode-stem}-thumb.jpg`)

Extracted from each individual episode video file. The output filename is the video filename with the extension replaced by `-thumb.jpg`.

Example: `Breaking Bad - S01E01.m4v` → `Breaking Bad - S01E01-thumb.jpg`

### Output Structure

```
TV Shows/
└── Breaking Bad/
    ├── poster.jpg                              ← show poster
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

## Multi-Part Detection

Like `scraper.py`, this script uses `is_multipart()` to detect multi-part movie folders and skips them entirely. Multi-part TV episodes are processed normally (each has its own thumbnail).

---

## Progress Window & Logging

`extract_artwork.py` opens a progress window before processing begins. Each item's result is shown in the scrollable log and written to the run's log file.

The log file location:

| Platform | Path |
|----------|------|
| macOS | `~/Library/Logs/PlexNFOCreator/extract_artwork_YYYY-MM-DD_HHMMSS.log` |
| Linux | `~/.local/share/plex-nfo-creator/logs/extract_artwork_YYYY-MM-DD_HHMMSS.log` |
| Windows | `%APPDATA%\PlexNFOCreator\Logs\extract_artwork_YYYY-MM-DD_HHMMSS.log` |

Click **Open Log** in the progress window to open it in Console.app (macOS) or your default text editor.

### Log / Window Output

```
[  1/1760] ✓ → poster.jpg  Back to the Future (1985)
[  2/1760] ✓ → poster.jpg  Batman (1989)
[  3/1760] ⏭ already exists  Batman Begins (2005)
[  4/1760] ❌ no embedded artwork  Some Home Recording (1987)
```

### Final Summary (TV Shows)

```
============================================================
COMPLETE
  Show posters extracted:   254
  Season posters extracted: 843
  Episode thumbs extracted: 19,754
  Already existed:          0
  No embedded artwork:      187
============================================================
```

An OS-native notification is sent when processing completes.

---

## Functions Reference

| Function | Description |
|----------|-------------|
| `is_multipart(name)` | Returns True for multi-part folder names |
| `extract_embedded_artwork(video_path, output_path)` | Try both strategies; return True if successful |
| `find_video(folder)` | Find first video file in a folder |
| `find_first_episode(season_path)` | Find first video file in a season folder |
| `process_movies(root, extract, force, progress_cb, log_cb, cancel)` | Entry point for movies mode; returns `(done, errors, skipped)` |
| `process_tvshows(root, extract, force, progress_cb, log_cb, cancel)` | Entry point for TV shows mode; returns `(done, errors, skipped)` |

---

## Troubleshooting

**ffmpeg not found / check fails**
Run the script and click Yes when offered auto-install. Or install manually — see [Installation → Step 4](Installation#step-4--ffmpeg-for-extract_artworkpy-only). After manual install, open a new terminal before re-running.

**"Permission denied" writing poster.jpg**
Add Terminal to Full Disk Access in System Settings → Privacy & Security.

**poster.jpg is very small or corrupted**
The file failed the `> 1000 byte` size check on a previous run and was deleted. The video may not have embedded artwork — this is common for ripped discs, downloaded files, or files not purchased through iTunes.

**No artwork extracted from any file**
Your files may not have been purchased through iTunes or processed with Subler. Files ripped from Blu-ray or downloaded typically do not have embedded poster artwork in the MP4 container.

**Progress window does not appear**
tkinter is not available. Install it (`brew install python-tk` on macOS, `sudo apt-get install python3-tk` on Linux) and re-run. Processing continues in the terminal without the GUI.
