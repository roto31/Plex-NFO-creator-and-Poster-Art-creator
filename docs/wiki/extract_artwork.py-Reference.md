# extract_artwork.py Reference

## Overview

`extract_artwork.py` extracts embedded poster artwork from iTunes/Subler-encoded MP4 files and saves it as Plex-compatible `poster.jpg` sidecar files. For TV shows, it also generates per-episode `-thumb.jpg` thumbnails and season-level `poster.jpg` files.

Embedded MP4 artwork (stored in the `covr` atom) is readable by Apple's TV.app natively. Plex cannot read embedded MP4 artwork — it requires sidecar `poster.jpg` files. This script bridges that gap.

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

This script requires `ffmpeg` in your PATH. Installation:

```bash
brew install ffmpeg
```

Verify: `ffmpeg -version`

The script calls `check_ffmpeg()` on startup and exits with instructions if ffmpeg is not found.

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

## Terminal Output

### Dry Run

```
DRY RUN — run with --extract to write files
============================================================
[Movies] Scanning: /Volumes/iTunes 5/Movies
[  1/1760] WOULD EXTRACT poster: Back to the Future (1985)
[  2/1760] WOULD EXTRACT poster: Batman (1989)
[  3/1760] ⏭ SKIP: poster exists: Batman Begins (2005)
...
============================================================
DRY run complete — 1692 would be extracted, 60 would be skipped
```

### With --extract

```
============================================================
[  1/1760] ✓ poster: Back to the Future (1985)
[  2/1760] ✓ poster: Batman (1989)
[  3/1760] ⏭ SKIP: poster exists: Batman Begins (2005)
[  4/1760] ✗ NO ARTWORK: Some Home Recording (1987)
```

### Final Summary (TV Shows)

```
============================================================
TV Shows complete
  Show posters:    254
  Season posters:  843
  Episode thumbs:  19,754
  No artwork:      187
  Skipped:         0
============================================================
```

---

## Functions Reference

| Function | Description |
|----------|-------------|
| `check_ffmpeg()` | Verify ffmpeg is in PATH; exit with instructions if not |
| `is_multipart(name)` | Returns True for multi-part folder names |
| `find_video_file(folder)` | Find first video file in a folder |
| `extract_embedded_artwork(video_path, output_path)` | Try both strategies; return True if successful |
| `process_movies(root, extract, force)` | Entry point for movies mode |
| `process_tvshows(root, extract, force)` | Entry point for TV shows mode |

---

## Troubleshooting

**"ffmpeg: command not found"**
Install with `brew install ffmpeg`.

**"Permission denied" writing poster.jpg**
Add Terminal to Full Disk Access in System Settings → Privacy & Security.

**poster.jpg is very small or corrupted**
The file failed the `> 1000 byte` size check on a previous run and was deleted. The video may not have embedded artwork — this is common for ripped discs, downloaded files, or files not purchased through iTunes.

**No artwork extracted from any file**
Your files may not have been purchased through iTunes or processed with Subler. Files ripped from Blu-ray or downloaded typically do not have embedded poster artwork in the MP4 container.
