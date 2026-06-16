# extract_artwork.py — Reference Documentation

## Overview

`extract_artwork.py` extracts embedded cover art from your MP4 and M4V video files and saves it as sidecar `poster.jpg` files that Plex can read natively.

**Why this is needed:** When you purchase or rip movies through iTunes/TV.app, Subler, or similar tools, the cover artwork is embedded directly inside the video file's MP4 container. The Apple TV app reads this embedded artwork automatically. **Plex does not** — Plex requires the artwork to exist as a separate file (`poster.jpg`) in the same folder as the video.

This script bridges that gap.

---

## Requirements

- **Python 3.8+**
- **ffmpeg** — must be installed and in PATH
  ```bash
  brew install ffmpeg
  ```

---

## Command Line Interface

```bash
python3 extract_artwork.py <mode> <path> [--extract] [--force]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `mode` | Yes | `movies` or `tvshows` |
| `path` | Yes | Absolute path to root media directory |
| `--extract` | No | Actually write files. **Without this flag, runs as a dry run.** |
| `--force` | No | Overwrite existing `poster.jpg` / `-thumb.jpg` files |

### Examples

```bash
# Dry run — see what would be extracted, nothing written
python3 extract_artwork.py movies "/Volumes/iTunes 5/Movies"

# Extract movie posters
python3 extract_artwork.py movies "/Volumes/iTunes 5/Movies" --extract

# Extract TV show posters + season posters + episode thumbnails
python3 extract_artwork.py tvshows "/Volumes/iTunes 5/TV Shows" --extract

# Re-extract everything (overwrite existing files)
python3 extract_artwork.py movies "/Volumes/iTunes 5/Movies" --extract --force
python3 extract_artwork.py tvshows "/Volumes/iTunes 5/TV Shows" --extract --force
```

---

## Output Files

### Movies

One `poster.jpg` per movie folder, placed alongside the video file:

```
/Movies/Back to the Future (1985)/
├── Back to the Future (1985).mp4
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
│   ├── Breaking Bad - S01E01.mp4
│   ├── Breaking Bad - S01E01.nfo
│   └── Breaking Bad - S01E01-thumb.jpg   ← episode thumbnail
├── Season 2/
│   ├── poster.jpg          ← season poster (from S02E01)
│   ├── Breaking Bad - S02E01.mp4
│   └── Breaking Bad - S02E01-thumb.jpg
```

---

## Extraction Strategy

The script tries three ffmpeg strategies in order. If one fails, it falls back to the next.

### Strategy 1 — Secondary Video Stream (iTunes/Subler Format)

Subler embeds artwork as a second video stream inside the MP4 container:
- Stream 0: actual video content
- Stream 1: cover art image

```bash
ffmpeg -i "movie.mp4" -an -vframes 1 -map 0:v:1 -y "poster.jpg"
```

### Strategy 2 — Attached Picture Stream (MKV / some MP4)

Some containers use the `attached_pic` disposition flag:

```bash
ffmpeg -i "movie.mp4" -map 0:v -map -0:V -vframes 1 -y "poster.jpg"
```

### Strategy 3 — No Artwork Found

**The script does NOT fall back to extracting a video frame.** Only actual embedded artwork is saved. If no artwork stream is found, the file is logged as `❌ no embedded artwork` and skipped.

This is intentional — a random video frame makes a terrible poster and would require manual cleanup in Plex.

---

## Artwork Source for TV Shows

| Artifact | Source |
|----------|--------|
| Show `poster.jpg` | First episode of the first season found |
| Season `poster.jpg` | First episode of that season |
| Episode `-thumb.jpg` | The episode's own video file |

The show-level poster source is the first available episode, sorted alphabetically by season directory name.

---

## Output Format

### Dry Run
```
DRY RUN — No files will be written
============================================================
Found 1761 movie folders

[1/1761] Back to the Future (1985)
  Video: Back to the Future (1985).mp4
  WOULD EXTRACT → poster.jpg

[2/1761] The Dark Knight (2008)
  ⏭ poster.jpg already exists

[3/1761] Cinderella Man - Disc 1
  ⏭ Skipping — multi-part file
```

### With --extract
```
EXTRACTING ARTWORK
============================================================
[1/1761] Back to the Future (1985) ✓ → poster.jpg
[2/1761] The Dark Knight (2008) ⏭ already exists
[3/1761] Cinderella Man - Disc 1 ⏭ multi-part
[4/1761] Home Recording ❌ no embedded artwork
```

---

## Resume Safety

Without `--force`, the script skips any folder where `poster.jpg` (or `-thumb.jpg`) already exists. This means:

- The script can be interrupted and restarted safely
- Only unfinished items are processed on subsequent runs
- TV show processing with ~19,000+ episode thumbnails typically takes 10–20 hours total; the script is designed to be run in multiple sessions

---

## Performance

ffmpeg spawns one process per video file. Each extraction takes ~0.5–2 seconds depending on file size and codec. For large libraries:

| Scope | Count | Estimated Time |
|-------|-------|---------------|
| Movie posters | 1,760 | ~30–60 minutes |
| TV show + season posters | ~1,500 | ~30–60 minutes |
| Episode thumbnails (19,000+) | 19,000 | 10–20 hours |

The episode thumbnail step is the long pole. It can be run overnight and is fully resumable.

---

## Error Handling

| Error | Behavior |
|-------|---------|
| ffmpeg not found | Print install instructions and exit immediately |
| ffmpeg timeout (>30s) | Skip file, log nothing (treated as no artwork) |
| No embedded artwork | Log `❌ no embedded artwork`, continue |
| Output file < 1000 bytes | Treat as failed extraction, delete partial file |
| File write error | Caught by exception handler, continue |
