# rename_movies.py Reference

## Overview

`rename_movies.py` cleans movie folder and file names before running `scraper.py`. Files acquired from download sources, ripping tools, or legacy imports often contain noise — quality tags, source identifiers, codec names, leading numbering — that causes TMDB's search to fail or match incorrectly.

This script strips that noise. It **always runs as a dry run by default** — you must explicitly pass `--rename` to make any changes.

---

## Command Line Interface

```bash
python3 rename_movies.py <path> [--rename]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `path` | Yes | Absolute path to the movies root directory |
| `--rename` | No | Actually rename files and folders. Without this, dry run only. |

### Recommended Workflow

```bash
# Step 1 — always preview first
python3 rename_movies.py "/Volumes/iTunes 5/Movies"

# Step 2 — review output carefully. Look for:
#   - Titles where the year was stripped (it shouldn't be)
#   - Numeric titles that lost their numbers
#   - Anything that doesn't look right

# Step 3 — apply if output looks correct
python3 rename_movies.py "/Volumes/iTunes 5/Movies" --rename

# Step 4 — re-run scraper since folder names changed
python3 scraper.py movies "/Volumes/iTunes 5/Movies" --force
```

---

## What Gets Cleaned

### `clean_name()` transformation steps

1. **Strip 1–2 digit leading prefix** (only when followed by a letter)
2. **Strip quality/source tags** in brackets or parentheses
3. **Strip remaining `[...]` content**
4. **Strip trailing `_ - .` characters**
5. **Replace `_` with space**
6. **Collapse double spaces**

The year in parentheses — e.g. `(1985)` — is **preserved**. This differs from `clean_title()` in `scraper.py`, which strips the year before searching.

### Tags Stripped

Quality indicators:
```
HD, 1080p, 1080i, 720p, 2160p, 4K, UHD
BluRay, Blu-Ray, BDRip, BRRip
WEB-DL, WEBRip, HDTV, DVDRip, DVD
x264, x265, H.264, H.265, HEVC, AVC
AAC, AC3, DTS, DD5.1
Unrated, Extended, Remastered
4K77, 4K80, 4K83
```

Source tags:
```
YTS, YTS.MX, YIFY, RARBG
```

Any remaining `[...]` content not matched above.

### Examples

| Before | After |
|--------|-------|
| `03 Forrest Gump (HD)` | `Forrest Gump` |
| `The_Dark_Knight_[BluRay][1080p]` | `The Dark Knight` |
| `Inception (2010) [YTS.MX]` | `Inception (2010)` |
| `Star.Wars.4K77.v2.(No.DNR)` | `Star Wars` |
| `Les Misérables (2012)` | `Les Misérables (2012)` ← accents preserved |
| `127 Hours (2010)` | `127 Hours (2010)` ← numeric title preserved |
| `2001 A Space Odyssey` | `2001 A Space Odyssey` ← 4-digit number preserved |
| `50 50 (2011)` | `50 50 (2011)` ← digit followed by digit, not letter |

---

## What is NOT Renamed

| Item | Reason |
|------|--------|
| Year in parentheses `(1985)` | Used by Plex and TMDB for disambiguation |
| Multi-part folders | Skipped entirely — see Multi-Part Detection below |
| Hidden folders (`.` prefix) | System/metadata folders |
| Numeric titles with 3+ leading digits | Regex only matches 1–2 digits |
| Any folder where the name wouldn't change | No-op, counted as "already clean" |

---

## Multi-Part Detection

Folders matching multi-part patterns are **skipped entirely** — no rename is attempted:

```
Gone with the Wind - Disc 1     → ⏭ Skipping (multi-part)
Cinderella Man 1 of 2           → ⏭ Skipping (multi-part)
Lawrence of Arabia Part 1       → ⏭ Skipping (multi-part)
```

Note: `The Godfather - Part II` is **not** skipped — it doesn't match the patterns because it uses the Roman numeral `II`, not a standalone digit.

Patterns detected: `Part N`, `Part I/II/III`, `Disc N`, `N of M`, `Vol N`, `Vol. N`, `Volume N`, `Chapter N`, `CD N`, `File N`, `Pt N`, `Pt. N`

---

## Rename Order

Files inside a folder are renamed **before** the folder itself. This avoids `FileNotFoundError` caused by the old folder path becoming invalid before its contents are renamed.

---

## File Types Renamed

Only files with these extensions are renamed alongside the folder:

```
.mkv  .mp4  .mov  .avi  .m4v
.nfo  .jpg  .png  .srt  .sub
```

Other files in the folder are left untouched.

---

## Terminal Output

### Dry Run (default)

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

### With `--rename`

```
RENAMING FILES
============================================================
[FOLDER] 03 Forrest Gump (HD)
  RENAMED: 03 Forrest Gump (HD).m4v
       → Forrest Gump.m4v
  RENAMED: 03 Forrest Gump (HD)
       → Forrest Gump

============================================================
RENAME COMPLETE
  Folders renamed: 47
  Files renamed:   52
  Unchanged:       1713
```

---

## Differences from `clean_title()` in scraper.py

| Behavior | `rename_movies.py` `clean_name()` | `scraper.py` `clean_title()` |
|----------|----------------------------------|------------------------------|
| Year `(1985)` | **Preserved** in output name | **Stripped** before searching |
| Purpose | Produce clean folder/file names for the filesystem | Produce clean search strings for TMDB/TVDB |
| Accents | Preserved | Preserved (ASCII folding only in fuzzy variants) |
