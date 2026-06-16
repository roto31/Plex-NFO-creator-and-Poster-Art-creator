# scraper.py — Reference Documentation

## Overview

`scraper.py` is the core script of this suite. It walks your Movies and TV Shows directories, queries TMDB (for movies) and TVDB (for TV shows), and writes Plex-compatible `.nfo` XML sidecar files alongside every video file.

It uses 4 parallel worker threads and fuzzy title matching to maximize coverage without sacrificing accuracy.

---

## Command Line Interface

```bash
python3 scraper.py <mode> <path> [--force]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `mode` | Yes | `movies` or `tvshows` |
| `path` | Yes | Absolute path to the root media directory |
| `--force` | No | Overwrite existing `.nfo` files. Without this flag, existing files are skipped. |

### Examples

```bash
# Movies — skip already-processed folders
python3 scraper.py movies "/Volumes/iTunes 5/Movies"

# TV Shows — skip already-processed shows/episodes
python3 scraper.py tvshows "/Volumes/iTunes 5/TV Shows"

# Force re-generate all NFOs (e.g. after adding uniqueid support)
python3 scraper.py movies "/Volumes/iTunes 5/Movies" --force
python3 scraper.py tvshows "/Volumes/iTunes 5/TV Shows" --force
```

---

## Configuration

Edit these constants at the top of `scraper.py`:

```python
TMDB_API_KEY = "your_tmdb_key_here"
TVDB_API_KEY = "your_tvdb_key_here"

RATE_SLEEP  = 0.28    # seconds between API calls (global, across all threads)
TIMEOUT     = 15      # HTTP request timeout in seconds
MAX_WORKERS = 4       # parallel worker threads
RETRY_SLEEP = 10      # seconds to wait after HTTP 429 rate limit response
```

---

## Output Files

### Movies → `Movie.nfo`

Placed inside the movie's folder:

```
/Movies/Back to the Future (1985)/
├── Back to the Future (1985).mp4
└── Movie.nfo
```

### TV Shows → `tvshow.nfo`, `season.nfo`, `{episode}.nfo`

```
/TV Shows/Breaking Bad/
├── tvshow.nfo
├── Season 1/
│   ├── season.nfo
│   ├── Breaking Bad - S01E01.mp4
│   └── Breaking Bad - S01E01.nfo
```

---

## NFO File Formats

### Movie.nfo

```xml
<?xml version='1.0' encoding='utf-8'?>
<movie>
  <title>Back to the Future</title>
  <uniqueid type="tmdb" default="true">105</uniqueid>
  <uniqueid type="imdb" default="false">tt0088763</uniqueid>
  <year>1985</year>
  <plot>Marty McFly is accidentally sent back in time to 1955...</plot>
  <runtime>116</runtime>
  <rating>8.5</rating>
  <genre>Adventure</genre>
  <genre>Comedy</genre>
  <genre>Science Fiction</genre>
  <studio>Universal Pictures</studio>
  <director>Robert Zemeckis</director>
  <actor>
    <name>Michael J. Fox</name>
    <role>Marty McFly</role>
  </actor>
</movie>
```

### tvshow.nfo

```xml
<?xml version='1.0' encoding='utf-8'?>
<tvshow>
  <title>Breaking Bad</title>
  <uniqueid type="tvdb" default="true">81189</uniqueid>
  <uniqueid type="tmdb" default="false">1396</uniqueid>
  <uniqueid type="imdb" default="false">tt0903747</uniqueid>
  <year>2008</year>
  <plot>A high school chemistry teacher diagnosed with cancer...</plot>
  <runtime>47</runtime>
  <rating>9.5</rating>
  <genre>Drama</genre>
  <genre>Crime</genre>
  <network>AMC</network>
  <actor>
    <name>Bryan Cranston</name>
    <role>Walter White</role>
  </actor>
</tvshow>
```

### season.nfo

```xml
<?xml version='1.0' encoding='utf-8'?>
<season>
  <title>Season 1</title>
  <season>1</season>
</season>
```

### Episode .nfo

```xml
<?xml version='1.0' encoding='utf-8'?>
<episodedetails>
  <title>Pilot</title>
  <season>1</season>
  <episode>1</episode>
  <uniqueid type="tvdb" default="true">349232</uniqueid>
  <uniqueid type="imdb" default="false">tt0959621</uniqueid>
  <plot>Walter White, a chemistry teacher, is diagnosed with inoperable lung cancer...</plot>
  <rating>9.0</rating>
  <aired>2008-01-20</aired>
  <runtime>58</runtime>
  <director>Vince Gilligan</director>
  <actor>
    <name>Bryan Cranston</name>
    <role>Walter White</role>
  </actor>
</episodedetails>
```

---

## Title Cleaning & Fuzzy Matching

Before searching TMDB/TVDB, folder names are cleaned through two stages:

### Stage 1 — `clean_title()`

Strips noise from folder names in this order:

1. Leading 1–2 digit padding prefix (e.g. `01 The Hangover` → `The Hangover`)
   - Only strips if followed by a letter — preserves `127 Hours`, `2001 A Space Odyssey`
2. Trailing `(year)` — e.g. `(1985)`
3. Quality/source tags in brackets — `[1080p]`, `(BluRay)`, `[YTS.MX]`, `(4K)`, etc.
4. Remaining bracketed content
5. Trailing underscores, dashes, dots
6. Underscores → spaces
7. Multiple spaces → single space

### Stage 2 — `fuzzy_variants()`

If Stage 1 title returns no results, progressively tries:

| Pass | Transformation | Example |
|------|---------------|---------|
| 1 | Exact clean title + year | `Harry Potter and the Sorcerers Stone` + `2001` |
| 2 | Exact clean title, no year | `Harry Potter and the Sorcerers Stone` |
| 3 | Strip punctuation | `Harry Potter and the Sorcerers Stone` (apostrophes removed) |
| 4 | Remove leading article | `Dark Knight` (from `The Dark Knight`) |
| 5 | Move trailing article | `Godfather, The` → `The Godfather` |
| 6 | Strip subtitle | `Alien: Covenant` → `Alien` |
| 7 | ASCII-fold accents | `Amélie` → `Amelie`, `Léon` → `Leon` |
| 8 | Combined punct + ASCII | Both transforms together |

---

## Multi-Part Detection

Folders matching any of these patterns are skipped automatically:

| Pattern | Examples |
|---------|---------|
| `Part N` | `Cinderella Man Part 1`, `Gone with the Wind - Part 2` |
| `Disc N` / `Disk N` | `Avatar Disc 1`, `LOTR Disk 2` |
| `N of M` | `Band of Brothers 1 of 10` |
| `Vol N` / `Volume N` | `Planet Earth Volume 1` |
| `Chapter N` | `Shogun Chapter 1` |

---

## API Details

### TMDB (Movies)

- **Base URL:** `https://api.themoviedb.org/3`
- **Auth:** `api_key` query parameter
- **Search:** `GET /search/movie?query=TITLE&year=YEAR`
- **Details:** `GET /movie/{id}?append_to_response=credits,external_ids`
- **Rate limit:** ~40 requests/10 seconds

### TVDB (TV Shows)

- **Base URL:** `https://api4.thetvdb.com/v4`
- **Auth:** JWT bearer token obtained by `POST /login` with API key
- **Search:** `GET /search?query=TITLE&type=series`
- **Series:** `GET /series/{id}/extended?meta=episodes&short=true`
- **Episodes:** `GET /series/{id}/episodes/default?season=N`

The TVDB login is performed once at startup and the token is cached for the entire run.

---

## Performance

| Mode | Items | Workers | Estimated Time |
|------|-------|---------|---------------|
| Movies | 1,760 | 4 | ~15 minutes |
| TV Shows (307 shows, 19,600 episodes) | ~21,000 NFOs | 4 | ~45–60 minutes |

Performance is bounded by API rate limits, not CPU. The 4-worker thread pool keeps multiple HTTP requests in-flight simultaneously while staying within TMDB's 40 req/10s limit.

---

## Resume Safety

Without `--force`, the script skips any folder that already has the target `.nfo` file. This means:

- If the script is interrupted mid-run, simply re-run the same command
- Only unfinished items will be processed
- Already-completed items are never re-fetched or overwritten

---

## Error Handling

| Error | Behavior |
|-------|---------|
| API timeout | Retry once after 2 seconds, then skip |
| HTTP 429 (rate limited) | Sleep 10 seconds, retry once |
| No search results | Log `❌ Not found`, continue |
| No video file in folder | Skip silently |
| File write error | Log `❌ Write failed`, continue |
| TVDB auth failure | Exit immediately with error message |

No single failure stops the run. Every error is logged per-item and the script continues.
