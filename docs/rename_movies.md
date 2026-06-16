# rename_movies.py — Reference Documentation

## Overview

`rename_movies.py` cleans movie folder names and video filenames before running `scraper.py`. Many media files acquired from torrent sites, ripping tools, or legacy imports contain quality tags, source tags, codec identifiers, or leading numbering that confuse TMDB's search API.

This script strips that noise so `scraper.py` can find the correct match.

**Always run `scraper.py` after `rename_movies.py`** — renamed folders need fresh NFO files.

On startup it runs preflight checks (Python version, and write permission when `--rename` is active) via `preflight.py`, then opens a progress window and writes a timestamped log file. See [`preflight.py` Reference](preflight.md) for details.

---

## Command Line Interface

```bash
python3 rename_movies.py <path> [--rename]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `path` | Yes | Absolute path to the movies root directory |
| `--rename` | No | Actually rename files/folders. **Without this flag, runs as a dry run.** |

### Recommended Workflow

```bash
# Step 1: Always preview first
python3 rename_movies.py "/Volumes/iTunes 5/Movies"

# Step 2: Review the output carefully
# Step 3: Apply only if the renames look correct
python3 rename_movies.py "/Volumes/iTunes 5/Movies" --rename

# Step 4: Re-run scraper to generate NFOs for renamed folders
python3 scraper.py movies "/Volumes/iTunes 5/Movies"
```

---

## What Gets Renamed

### Leading Number Prefixes

Only strips **1–2 digit** prefixes followed by a letter. Preserves numeric titles.

| Folder Name | Renamed To | Notes |
|-------------|-----------|-------|
| `01 The Hangover` | `The Hangover` | ✓ Leading index stripped |
| `03 Forrest Gump (HD)` | `Forrest Gump` | ✓ Index + quality tag stripped |
| `127 Hours` | `127 Hours` | ✓ Preserved — 3-digit number is part of title |
| `2001 A Space Odyssey` | `2001 A Space Odyssey` | ✓ Preserved — 4-digit number |
| `50 50` | `50 50` | ✓ Preserved — next char is a digit, not a letter |

### Quality & Source Tags

Stripped from anywhere in the name, in parentheses or brackets:

```
HD, 1080p, 1080i, 720p, 2160p, 4K, UHD
BluRay, Blu-Ray, BDRip, BRRip
WEB-DL, WEBRip, HDTV, DVDRip, DVD
x264, x265, H.264, H.265, HEVC, AVC
AAC, AC3, DTS, DD5.1
Unrated, Extended, Remastered
4K77, 4K80, 4K83
YTS, YTS.MX, YIFY, RARBG
```

### Remaining Bracketed Content

Any `[...]` content not caught above is stripped (e.g. `[Despecialized]`, `[Group]`).

### Trailing Junk

- Trailing underscores, dashes, dots
- Underscores anywhere → spaces
- Multiple consecutive spaces → single space

---

## Multi-Part Detection

Folders matching multi-part patterns are skipped entirely — they often represent intentional naming and the rename would break them:

```
All the President's Men - Disc 1   →   ⏭ Skipping — multi-part
Cinderella Man 1 of 2              →   ⏭ Skipping — multi-part
Gone with the Wind Part 1          →   ⏭ Skipping — multi-part
```

---

## What Does NOT Get Renamed

- The **year in parentheses** — `(1985)` is preserved. Plex and TMDB both use the year for matching.
- Numeric titles (`127 Hours`, `2001 A Space Odyssey`, `50 50`, `1917`)
- Multi-part folders
- Hidden folders (starting with `.`)

---

## Output Format

### Dry Run
```
DRY RUN — No changes will be made
============================================================
Found 1760 movie folders in /Volumes/iTunes 5/Movies

[FOLDER] 03 Forrest Gump (HD)
  WOULD RENAME: 03 Forrest Gump (HD).m4v
             → Forrest Gump.m4v
  WOULD RENAME: 03 Forrest Gump (HD)
             → Forrest Gump

[FOLDER] The_Dark_Knight_[BluRay][1080p]
  WOULD RENAME: The_Dark_Knight_[BluRay][1080p].mkv
             → The Dark Knight.mkv
  WOULD RENAME: The_Dark_Knight_[BluRay][1080p]
             → The Dark Knight

============================================================
DRY RUN COMPLETE — Nothing was changed
  Folders that WOULD be renamed: 47
  Files that WOULD be renamed:   52
  Already clean (unchanged):     1713
```

### With --rename
```
RENAMING FILES
============================================================
[FOLDER] 03 Forrest Gump (HD)
  RENAMED: 03 Forrest Gump (HD).m4v
       → Forrest Gump.m4v
  RENAMED: 03 Forrest Gump (HD)
       → Forrest Gump
```

---

## File Types Processed

Only these extensions are renamed alongside the folder:

```
.mkv  .mp4  .mov  .avi  .m4v
.nfo  .jpg  .png  .srt  .sub
```

Other file types (`.txt`, `.md`, etc.) inside the folder are left untouched.

---

## Rename Order

To avoid path-not-found errors, files inside a folder are renamed **before** the folder itself is renamed. This ensures the old folder path is still valid when renaming its contents.
