# scraper.py Reference

## Overview

`scraper.py` generates Plex-compatible `.nfo` XML metadata sidecar files for movies and TV shows. It queries TMDB for movies and TVDB for TV shows, writes structured XML with `<uniqueid>` tags for precise Plex matching, and runs fully automated with 4 parallel workers and resume-safe skip logic.

On startup, `scraper.py` runs preflight checks via [`preflight.py`](preflight.py-Reference): Python version, API key validation, and write permission on the target directory. A progress window with a real-time log opens before processing begins, and a log file is written to the OS-native log directory for the duration of the run.

---

## Command Line Interface

```bash
python3 scraper.py <mode> <path> [--force]
```

| Argument | Required | Values | Description |
|----------|----------|--------|-------------|
| `mode` | Yes | `movies` or `tvshows` | Which library to process |
| `path` | Yes | Absolute path | Root directory of the library |
| `--force` | No | — | Overwrite existing `.nfo` files |

### Examples

```bash
# Generate NFOs for all movies (skip already-done)
python3 scraper.py movies "/Volumes/iTunes 5/Movies"

# Regenerate all movie NFOs (including already-done)
python3 scraper.py movies "/Volumes/iTunes 5/Movies" --force

# TV shows
python3 scraper.py tvshows "/Volumes/iTunes 5/TV Shows"
python3 scraper.py tvshows "/Volumes/iTunes 5/TV Shows" --force
```

---

## Configuration

These constants are at the top of `scraper.py`:

```python
TMDB_API_KEY = "your_tmdb_key_here"   # TMDB v3 API key
TVDB_API_KEY = "your_tvdb_key_here"   # TVDB v4 project API key

RATE_SLEEP   = 0.28    # Seconds between API calls (global)
MAX_WORKERS  = 4       # Parallel worker threads
TMDB_BASE    = "https://api.themoviedb.org/3"
TVDB_BASE    = "https://api4.thetvdb.com/v4"
```

---

## Expected Folder Structure

### Movies

```
Movies/
├── Back to the Future (1985)/
│   └── Back to the Future (1985).m4v
├── The Dark Knight (2008)/
│   └── The Dark Knight (2008).m4v
└── Inception (2010)/
    └── Inception (2010).m4v
```

Each movie must be in **its own folder**. The script scans one level deep.

### TV Shows

```
TV Shows/
└── Breaking Bad/
    ├── Season 1/
    │   ├── Breaking Bad - S01E01.m4v
    │   └── Breaking Bad - S01E02.m4v
    └── Season 2/
        └── Breaking Bad - S02E01.m4v
```

Season directories are matched by the regex `season\s*\d+` (case-insensitive), or named `Specials`.

---

## Output Files

### Movies

| File | Location | Description |
|------|----------|-------------|
| `Movie.nfo` | Movie folder | Movie metadata XML |

### TV Shows

| File | Location | Description |
|------|----------|-------------|
| `tvshow.nfo` | Show root | Show metadata XML |
| `season.nfo` | Each season dir | Season metadata XML |
| `{episode-filename}.nfo` | Season dir | Episode metadata XML |

---

## Resume Safety

Without `--force`, the script skips:
- Movie folders where `Movie.nfo` already exists
- Shows where `tvshow.nfo` exists — reads the TVDB ID from the existing file and proceeds directly to episodes
- Season directories where `season.nfo` exists
- Episode files where `{stem}.nfo` already exists

This means you can interrupt the script at any time (Ctrl+C) and restart it without losing progress.

---

## Title Cleaning — `clean_title()`

Before searching TMDB/TVDB, folder names are cleaned via this 7-step pipeline:

| Step | Regex / Operation | Example |
|------|------------------|---------|
| 1 | Strip 1-2 digit leading prefix (if followed by a letter) | `03 Alien` → `Alien` |
| 2 | Strip trailing year `(YYYY)` | `Alien (1979)` → `Alien` |
| 3 | Strip quality tags in `[...]` or `(...)` | `Alien [1080p BluRay]` → `Alien` |
| 4 | Strip remaining `[...]` brackets | `Alien [YTS]` → `Alien` |
| 5 | Strip trailing `_ - .` | `Alien_` → `Alien` |
| 6 | Replace `_` with space | `The_Dark_Knight` → `The Dark Knight` |
| 7 | Collapse double spaces | `Star  Wars` → `Star Wars` |

**Numeric titles preserved:** `127 Hours`, `2001 A Space Odyssey`, `50 50`, `1917` — none of these start with 1-2 digits followed by a letter when the number is 3+ digits, or when followed by another digit.

---

## Fuzzy Matching — `fuzzy_variants()`

If the cleaned title returns no results, up to 8 fuzzy variants are tried:

| Pass | Variant |
|------|---------|
| 1 | Cleaned title + year |
| 2 | Cleaned title, no year |
| 3 | Strip all punctuation |
| 4 | Remove leading article (`The `, `A `, `An `) |
| 5 | Move trailing article (`Title, The` → `The Title`) |
| 6 | Strip subtitle (everything after ` - ` or `: `) |
| 7 | ASCII-fold accents (`Amélie` → `Amelie`, `Léon` → `Leon`) |
| 8 | Punctuation strip + ASCII fold combined |

Each variant is tried with year first, then without. The first result with a non-zero `id` wins.

---

## TMDB API Usage

### Authentication

All TMDB calls use the v3 API key as a query parameter: `?api_key=...`

### Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `GET /search/movie` | Search for movie by title and year |
| `GET /movie/{id}?append_to_response=credits,external_ids` | Full movie details, cast, IMDb ID |

### Rate Limiting

A global thread-safe rate limiter (`_throttle()`) enforces a minimum of `RATE_SLEEP` (0.28s) between all API calls across all threads. This keeps combined call rates well within TMDB's 40 req/10s limit.

---

## TVDB API Usage

### Authentication

TVDB v4 uses JWT tokens, not direct API keys. The script calls `tvdb_login()` before spawning threads:

```python
POST https://api4.thetvdb.com/v4/login
Body: {"apikey": TVDB_API_KEY}
Response: {"data": {"token": "eyJ..."}}
```

The JWT is cached in `_TVDB_TOKEN` (global, protected by `_tvdb_login_lock`).

### Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `GET /search?type=series&q=...` | Search for series by title |
| `GET /series/{id}/extended` | Full series data including remoteIds |
| `GET /series/{id}/episodes/official?season={n}&page={n}` | Episode list for a season |

All requests send `Authorization: Bearer {token}`.

---

## Thread Safety

Four threads run in parallel via `ThreadPoolExecutor`. Thread safety is handled by three locks:

| Lock | Protects |
|------|---------|
| `_rate_lock` | `_last_request_ts` — global rate limiter state |
| `_tvdb_login_lock` | `_TVDB_TOKEN` — prevents double-login race |
| `_print_lock` | Terminal output — prevents interleaved lines |

---

## Multi-Part Detection — `is_multipart()`

Folders matching these patterns are skipped. The patterns detect multi-file movies (Disc 1/2, Part 1/2, etc.):

```
Part N        Part I/II/III    Disc N       N of M
N of M        Vol N            Vol. N       Volume N
Chapter N     CD N             File N       Pt N / Pt. N
```

Example: `The Godfather - Part II` is **not** skipped — that's the actual title. But `The Godfather (Disc 1)` **is** skipped.

---

## `<uniqueid>` Tag Generation

The `_uid()` helper creates uniqueid SubElements:

```python
def _uid(parent, id_type, value, default=False):
    el = ET.SubElement(parent, "uniqueid")
    el.set("type", id_type)
    el.set("default", "true" if default else "false")
    el.text = str(value)
```

### Movie uniqueid Tags

```xml
<uniqueid type="tmdb" default="true">105</uniqueid>
<uniqueid type="imdb" default="false">tt0088763</uniqueid>
```

Source: TMDB `id` and `external_ids.imdb_id`.

### TV Show uniqueid Tags

```xml
<uniqueid type="tvdb" default="true">81189</uniqueid>
<uniqueid type="tmdb" default="false">1396</uniqueid>
<uniqueid type="imdb" default="false">tt0903747</uniqueid>
```

Source: TVDB `id` for primary; `remoteIds` scanned for `sourceName` containing `"MovieDB"` (TMDB) and `"IMDB"`.

### Episode uniqueid Tags

```xml
<uniqueid type="tvdb" default="true">349232</uniqueid>
<uniqueid type="imdb" default="false">tt0959621</uniqueid>
```

---

## Progress Window & Logging

`scraper.py` opens a progress window (via `preflight.ProgressWindow`) before processing begins. All per-item output goes to both the scrollable log in the window and the run log file.

The log file location:

| Platform | Path |
|----------|------|
| macOS | `~/Library/Logs/PlexNFOCreator/scraper_YYYY-MM-DD_HHMMSS.log` |
| Linux | `~/.local/share/plex-nfo-creator/logs/scraper_YYYY-MM-DD_HHMMSS.log` |
| Windows | `%APPDATA%\PlexNFOCreator\Logs\scraper_YYYY-MM-DD_HHMMSS.log` |

Click **Open Log** in the progress window to open the current run's log in Console.app (macOS) or your default text editor.

### Log / Window Output Format

```
[118/1760] ✓  Back to the Future (1985)
[119/1760] ✓  Batman (1989)
[120/1760] ✗  Batman (1943) — not found
[121/1760] ⏭  Batman Returns (1992) — skipped
```

Progress format: `[current/total] status  title — reason`

### Final Summary

```
============================================================
Movies complete
  Done:    1625
  Errors:  75
  Skipped: 60
============================================================
```

An OS-native notification is sent when processing completes.

---

## Functions Reference

| Function | Description |
|----------|-------------|
| `_throttle()` | Global rate limiter, called before every API request |
| `tprint(msg)` | Thread-safe print via `_print_lock` |
| `tvdb_login()` | POST to TVDB /login, cache JWT in `_TVDB_TOKEN` |
| `clean_title(name)` | 7-step folder name → search title |
| `fuzzy_variants(title)` | Returns list of up to 8 fuzzy variants |
| `is_multipart(name)` | Returns True if name matches multi-part patterns |
| `_uid(parent, type, value, default)` | Create `<uniqueid>` SubElement |
| `tmdb_search(title, year)` | Search TMDB with fuzzy variants, return movie dict |
| `tmdb_details(movie_id)` | Fetch full movie data from TMDB |
| `build_movie_nfo(details)` | Build XML ElementTree for movie |
| `write_nfo(root, path)` | Serialize to pretty-printed XML file |
| `tvdb_search(title)` | Search TVDB with fuzzy variants, return series dict |
| `tvdb_series_extended(series_id)` | Fetch full series data from TVDB |
| `tvdb_episodes(series_id, season)` | Fetch all episodes for a season |
| `build_tvshow_nfo(series)` | Build XML ElementTree for TV show |
| `build_season_nfo(season_num)` | Build XML ElementTree for season |
| `build_episode_nfo(ep, chars)` | Build XML ElementTree for episode |
| `_read_tvdb_id_from_nfo(path)` | Parse TVDB ID from existing tvshow.nfo |
| `_tvdb_remote_ids(remote_ids)` | Extract TMDB and IMDb IDs from TVDB remoteIds |
| `_process_one_movie(args)` | Worker: process one movie folder |
| `_process_one_show(args)` | Worker: process one TV show |
| `_process_seasons(show_path, series_id, series_chars, force, log_fn)` | Process all seasons for a show |
| `process_movies(root, force, progress_cb, log_cb, cancel)` | Entry point: scan and process all movies; returns `(done, errors, skipped)` |
| `process_tvshows(root, force, progress_cb, log_cb, cancel)` | Entry point: login TVDB, scan and process all shows; returns `(done, errors, skipped)` |

---

## Error Handling

| Situation | Behavior |
|-----------|---------|
| TMDB search returns no results | Try all 8 fuzzy variants; log `✗ not found` if all fail |
| TMDB/TVDB API returns non-200 | Log HTTP error, count as error, continue |
| Connection timeout | `requests` default timeout applies; log and continue |
| Folder has no video file | Skip silently |
| TV episode S/E not in TVDB | Log `not found in TVDB`, continue to next episode |
| NFO write fails (disk full, permissions) | Exception propagates, logged as error |
