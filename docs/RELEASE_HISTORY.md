# Plex NFO Creator & Artwork Suite — Complete Release History

Full script evolution from initial movie scraper (v0.1.0) through the fully integrated metadata platform (v2.4.0). All releases are available on the [GitHub Releases page](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/releases).

---

## Script Evolution Overview

| Phase | Versions | Focus |
|-------|----------|-------|
| **Scraper origins** | v0.1.0 – v0.6.0 | Core NFO generation: movies → TV shows → fuzzy matching → parallel processing |
| **Tooling expansion** | v0.7.0 – v0.8.0 | Artwork extraction + folder rename utility |
| **Platform maturity** | v1.0.0 – v1.2.0 | Stable release, cross-platform support, OS-native UX |
| **Metadata generator** | v1.3.0 – v1.4.0 | New Python orchestrator: movies + TV + selective processing + full artwork set |
| **Enrichment layer** | v1.5.0 – v1.9.0 | Subtitles, native dialogs, API key validation, bug fixes |
| **Music & databases** | v2.0.0 – v2.2.0 | MusicBrainz local DB + JSON dump, iTunes/MusicKit replaces Spotify |
| **Suite consolidation** | v2.3.0 – v2.4.0 | extract_artwork.py expanded for all media, scraper.py capabilities merged in |

---

## v0.x — Scraper Origins

### v0.1.0 — Initial Movie Scraper
*First public release*

Single-purpose Python script (`scraper.py`) that reads a flat movie folder structure, searches TMDB by folder name, and writes `Movie.nfo` files compatible with Plex's Local Media Assets agent.

**Capabilities:**
- Reads `Movies/Movie Name (Year)/` folder structure
- Extracts year from folder name via `(YYYY)` regex
- Searches TMDB `/search/movie` with title + year
- Falls back to title-only search if year search returns no results
- Writes `Movie.nfo` with: title, year, plot, rating, runtime, genres, director, cast (top 10), TMDb ID, IMDb ID
- Skips folders where `Movie.nfo` already exists
- Rate-limits TMDB calls to avoid 429 responses

**NFO format (established in this version, unchanged through v2.4.0):**
```xml
<movie>
  <title>The Dark Knight</title>
  <year>2008</year>
  <plot>...</plot>
  <rating>9.0</rating>
  <runtime>152</runtime>
  <genre>Action</genre>
  <director>Christopher Nolan</director>
  <actor><name>Christian Bale</name><role>Bruce Wayne / Batman</role></actor>
  <uniqueid type="tmdb" default="true">155</uniqueid>
  <uniqueid type="imdb" default="false">tt0468569</uniqueid>
</movie>
```

---

### v0.2.0 — TV Shows Support

Extends `scraper.py` to handle TV show libraries alongside movies. Introduces the `--media-type` flag.

**New capabilities:**
- `--media-type tv` mode scans `TV/Show Name/Season N/` structure
- Searches TVDB v4 API by show name
- Writes `tvshow.nfo` at the show root level
- Writes `{stem}.nfo` per episode (S01E01 etc.) with: title, plot, aired date, guest stars, director, writer, season/episode numbers, TVDB ID
- TVDB authentication: POST `/v4/login` with API key → Bearer token; token cached for session duration
- Fallback to TMDB `/search/tv` if TVDB search returns no results
- Skips episodes where `{stem}.nfo` already exists

---

### v0.3.0 — TVDB Authentication Fix

**Bug fix release.**

TVDB v4 changed their login endpoint behavior: tokens now expire after 30 days rather than being session-scoped. Scripts that ran for multiple days without restart hit 401 errors mid-run.

**Fix:** Added token expiry tracking. If the stored token is older than 29 days, `_authenticate()` is called automatically before the next TVDB request. No user action required.

---

### v0.4.0 — 8-Pass Fuzzy Title Matching

Many titles fail exact search due to punctuation, accents, leading articles, or subtitle suffixes. v0.4.0 adds `fuzzy_variants()` — a cascade of up to 8 title transformations tried in sequence until a result is found.

**Fuzzy variant sequence:**
1. Original title (unchanged)
2. Strip punctuation
3. Remove leading article (The, A, An)
4. Move trailing `, The` → prefix `The `
5. Strip subtitle after ` - `
6. Strip subtitle after `: `
7. ASCII-fold accented characters (Amélie → Amelie)
8. ASCII-fold + strip punctuation (combined)

**Impact:** Titles like *Amélie*, *Se7en: The Film*, *Matrix, The* now resolve on first run without manual intervention.

---

### v0.5.0 — Parallel Processing (4 Workers)

Initial bulk runs over large libraries (5,000+ movies) were slow due to sequential API calls. v0.5.0 adds `ThreadPoolExecutor` with configurable worker count.

**Changes:**
- `--workers N` flag (default: 4 for scraper.py; 1 recommended for scheduled daily runs)
- `process_library()` submits each folder as a future; `as_completed()` collects results
- Each worker has its own rate-limit window to avoid shared-state contention
- Progress counter uses threading.Lock to safely increment across workers
- Typical throughput: ~4× improvement vs sequential on a 5,000-movie library

---

### v0.6.0 — `<uniqueid>` Tags for Precise Plex Matching

Plex's Local Media Assets agent uses `<uniqueid type="tmdb">` and `<uniqueid type="tvdb">` tags to match NFO files to its internal database rather than guessing by title. Without these tags, Plex falls back to fuzzy title matching, which occasionally picks the wrong entry for titles with common names.

**Changes:**
- All NFOs now write `<uniqueid type="tmdb" default="true">` for movies
- TV show NFOs write `<uniqueid type="tvdb" default="true">` and `<uniqueid type="tmdb" default="false">` (both)
- Episode NFOs write TVDB episode ID: `<uniqueid type="tvdb">123456</uniqueid>`
- Plex now matches by ID rather than title — zero wrong-match incidents in testing

---

## v0.7.x – v0.8.x — Tooling Expansion

### v0.7.0 — Embedded Artwork Extractor (`extract_artwork.py`)

New companion script that extracts embedded cover art from MP4/M4V movie files using ffmpeg and saves it as `poster.jpg` alongside the video file — ready for Plex Local Media Assets.

**How it works:**
- Iterates all `.mp4` and `.m4v` files in the specified movie library root
- Calls ffmpeg with `-map 0:v:1` to extract the cover art stream (stream index 1 = artwork in most MP4s)
- Falls back to `-map 0:v:0` if stream 1 extraction fails
- Skips files where `poster.jpg` already exists (unless `--force`)
- Output: `poster.jpg` in the same directory as the video file

**Usage:**
```bash
python3 extract_artwork.py movies "/path/to/Movies" --extract
python3 extract_artwork.py tvshows "/path/to/TV" --extract
```

**Dependencies:** ffmpeg must be on PATH.

---

### v0.8.0 — Folder Name Cleaner (`rename_movies.py`)

New utility that standardizes movie folder names to `Movie Title (Year)` format — the format both scraper.py and the Metadata Generator expect for year extraction and TMDB search.

**Transformations:**
- Strips codec/quality tags: `1080p`, `BluRay`, `x264`, `HEVC`, `HDR`, `WEBRip`, `REMUX`, etc.
- Normalizes separators: dots and underscores → spaces
- Moves trailing year to `(YYYY)` format
- Capitalizes title words (title-case, respecting articles)
- Dry-run mode by default (`--dry-run`); pass `--apply` to rename

**Usage:**
```bash
# Preview changes
python3 rename_movies.py "/path/to/Movies" --dry-run

# Apply
python3 rename_movies.py "/path/to/Movies" --apply
```

---

## v1.x — Platform Maturity & Feature Expansion

### v1.0.0 — Stable Release

First stable release of the complete suite: `scraper.py`, `rename_movies.py`, `extract_artwork.py`. All three scripts tested against a 12,000-item library.

**Stabilization changes:**
- Comprehensive error handling — no script exits on a single item failure; errors logged and processing continues
- Consistent logging format across all three scripts (timestamp, level, item path)
- `health-check.py` — new standalone diagnostic that validates config, API connectivity, permissions, and ffmpeg availability
- `--debug` flag on all scripts for verbose per-item logging
- All three scripts accept `--help` with full usage documentation

---

### v1.1.0 — Cross-Platform Support (macOS, Linux, Windows)

Scripts were previously macOS-only (hardcoded paths, shell calls). v1.1.0 makes all three scripts run on macOS, Linux, and Windows without modification.

**Platform abstractions:**
- Path handling: `pathlib.Path` throughout (no hardcoded `/` separators)
- ffmpeg detection: `shutil.which('ffmpeg')` replaces `/usr/local/bin/ffmpeg`
- Log directories: OS-appropriate defaults
  - macOS: `~/Library/Logs/PlexNFOCreator/`
  - Linux: `~/.local/share/PlexNFOCreator/logs/`
  - Windows: `%APPDATA%\PlexNFOCreator\logs\`
- Config paths: same OS-appropriate defaults
- Platform detection: `platform.system()` used throughout

**New platform installers:**
- `install-macos.sh` — installs scripts, config, and LaunchAgent plist
- `install-linux.sh` — installs scripts, config, and systemd timer
- `install-windows.ps1` — installs scripts, config, and Task Scheduler XML
- `docker-compose.yml` + `Dockerfile` for containerized deployment

---

### v1.2.0 — Preflight Checks, Progress Window & OS-Native Logging

**Preflight system (`preflight.py`):**
- Runs before any script as an import
- Checks: Python version ≥ 3.9, required packages installed, config file readable, API keys not placeholder values, library paths exist, ffmpeg on PATH
- Exits with clear error message if any check fails — prevents cryptic mid-run failures

**Progress window (macOS):**
- On macOS, a native NSProgressPanel appears during bulk processing runs
- Shows: current item name, items processed / total, estimated time remaining
- Implemented via PyObjC (`AppKit.NSProgressIndicator`) with a background thread
- Non-macOS platforms show a simple terminal progress bar via `tqdm`

**OS-native logging:**
- macOS: logs to `~/Library/Logs/PlexNFOCreator/` (visible in Console.app)
- Linux: logs to systemd journal when running under systemd; file log otherwise
- Windows: logs to Windows Event Log (Application source) + file

---

### v1.3.0 — Plex Metadata Generator Integration

New Python orchestrator (`plex_metadata_generator.py`) that replaces the shell-based scheduling approach with a single script handling TV shows with full selective processing.

**Architecture:**
- `PlexNFOGenerator` — writes NFO files from metadata dataclasses
- `TMDbProvider` — TMDB TV search + episode/season details
- `TVDbProvider` — TVDB v4 search + episode details (primary for TV)
- `TunarrProvider` — reads Tunarr SQLite DB for channel-assigned show metadata
- `PlexMetadataOrchestrator` — coordinates all providers; handles selective skip logic
- `MetadataDownloader` — URL-to-file download with retry and size validation

**Selective processing:**
- `_needs_nfo()` — returns True only if NFO file is missing or `--force` set
- `_missing_art()` — returns set of missing artwork filenames per item type
- Items with both NFO and all artwork files: zero API calls, logged as skipped
- `--force` flag overrides all skip checks

**TV show artwork (per show root):**
`poster.jpg`, `banner.jpg`, `fanart.jpg`, `clearart.png`, `logo.png`, `landscape.jpg`

**Season + episode artwork:**
Season: `poster.jpg` — Episode: `{stem}-thumb.jpg`

**Config-driven:** `plex-metadata-generator.conf` (JSON)

---

### v1.4.0 — Movie Support, FanArt.tv Artwork, Selective Processing

Adds full movie support to the Metadata Generator with the complete FileBot-compatible artwork set sourced from TMDB + FanArt.tv.

**New: `TMDbMovieProvider`**
- `search_movie(title, year)` — TMDB `/search/movie`; retries without year if no results
- `get_movie(tmdb_id)` — `/movie/{id}?append_to_response=credits,external_ids`
- Returns `MovieMetadata` dataclass

**New: `FanartTvProvider`**
- `get_movie_artwork(tmdb_id)` — FanArt.tv v3 `/movies/{tmdb_id}`
- `get_tv_artwork(tvdb_id)` — FanArt.tv v3 `/tv/{tvdb_id}`
- Bluray → DVD → any disc type priority for `disc.png`
- HD variants preferred over SD (`hdmovieclearart` > `movieart`)
- Gracefully skipped if `fanart_tv.api_key` not in config (warning logged; TMDB art still downloads)

**Full 6-file movie artwork set:**

| Filename | Source | Notes |
|----------|--------|-------|
| `poster.jpg` | TMDB `poster_path` | Official/original studio art preferred |
| `folder.jpg` | Copy of `poster.jpg` | Plex alternate naming |
| `backdrop.jpg` | TMDB `backdrop_path` | |
| `clearart.png` | FanArt.tv `hdmovieclearart` | Falls back to `movieart` |
| `disc.png` | FanArt.tv `moviedisc` | Bluray → DVD → any |
| `logo.png` | FanArt.tv `hdmovielogo` | Falls back to `movielogo` |

**NFO-first ID extraction:**
- If `Movie.nfo` exists, parses `<uniqueid type="tmdb">` to get TMDB ID directly
- Skips TMDB search entirely — one fewer API call per re-run over already-catalogued movies

**Multi-part movie detection (`is_multipart()`):**
Folders matching `Part N`, `Disc N`, `N of M`, `Vol N` etc. are skipped entirely.

**Config additions:** `movies_library_root`, `fanart_tv.api_key`

---

### v1.5.0 — Subtitle Download + Embedding

Automatic subtitle download and embedding for movies and TV episodes. Subtitles are written as sidecar files (Plex) and optionally embedded into MP4/M4V containers (Apple TV local playback).

**Language detection:**
- macOS: reads `AppleLanguages` preference via `defaults read -g AppleLanguages`
- All platforms: `locale.getdefaultlocale()` fallback
- Config override: `subtitles.language: en` (two-letter ISO 639-1)

**Providers:**
- **OpenSubtitles REST API v1** — primary; free API key; searches by IMDb ID or TMDB ID; 5 downloads/day free, 40/day with credentials
- **Subdl** — fallback; no login required; IMDb ID + season/episode for TV; ZIP download, first SRT extracted

**Selective skip:**
- Skips if both `{stem}.{lang}.srt` sidecar exists AND (embed disabled OR embedded subtitle track already present)
- `ffprobe -select_streams s` used to check for existing subtitle streams

**Embedding:**
- MP4/M4V only: `ffmpeg -c:s mov_text` (same track type Subler writes; Apple TV reads natively)
- Marked as default subtitle track with language metadata
- Sanity check: temp file must be ≥ 95% of original size before replacing
- MKV: sidecar only (logged; Plex reads MKV sidecars natively)

**Config:**
```json
"subtitles": {"enabled": true, "language": "auto", "sidecar": true, "embed_in_file": true,
  "opensubtitles": {"api_key": "...", "username": "...", "password": "..."},
  "subdl": {"api_key": ""}}
```

---

### v1.6.0 — Native OS API Key Prompts

Missing or placeholder API keys are now requested via native OS dialogs at startup rather than requiring manual config file editing.

**Dialog flow:**
1. Script detects missing or placeholder key values
2. macOS: `osascript` AppleScript dialog with service name, sign-up URL, and text field
3. Linux/Windows: rich terminal prompt with same information
4. Entered key validated live against the provider API before saving
5. Invalid key: error shown, re-prompted (does not write invalid key to config)
6. Valid key: written back to config file in-place; used immediately for current run
7. Optional keys (FanArt.tv, Apple MusicKit, subtitle providers): Skip button available

**Validated endpoints:**
- TVDB: POST `/v4/login` — confirms token returned
- TMDB: GET `/configuration` — confirms 200
- OpenSubtitles: GET `/infos/user` — confirms API key accepted

---

### v1.7.0 — Native OS Setup Dialogs for Library Paths

Extends the native dialog system to library path configuration. Missing library paths are requested via folder picker dialogs.

**Dialog flow:**
- macOS: native Finder folder picker via `osascript choose folder`
- Linux/Windows: terminal input with example path shown
- Selected path validated: directory must exist and be readable
- Multi-volume: after path selected, dialog asks if additional volumes exist; repeats until user declines

**Multi-volume config format (new):**
```json
"tv_library_roots": ["/mnt/NAS1/TV", "/mnt/NAS2/TV"]
```

Both `tv_library_root` (string) and `tv_library_roots` (array) accepted. Dialog writes array format.

---

### v1.8.0 — Live API Key Validation + 15-Day Revalidation

API keys are validated at startup with a 15-day cached result to avoid hitting provider login endpoints daily.

**Validation cache:**
- `last_validated` timestamp stored in config per key
- If within 15 days: skip live validation
- If older than 15 days: re-validate against provider
- If validation fails: native dialog prompts for new key

**`health-check.py` additions:**
- Shows last validated date and pass/fail per key
- `--revalidate` flag forces immediate revalidation of all keys

---

### v1.9.0 — Bug Fixes (local test run)

Three bugs discovered during testing on a real media library.

**Fix 1: `cancel.is_set()` — threading.Event check was wrong**
`cancel()` was called as a function; the correct method is `cancel.is_set()`. Caused `AttributeError` when subtitle processing was interrupted.

**Fix 2: Multi-part movie regex false positive on years**
`is_multipart()` matched folder names where a year followed by a numeral (e.g. *Blade Runner 2049 (1982)*) triggered the Part N pattern. Tightened regex to require explicit prefix words (`Part`, `Pt`, `Disc`, etc.).

**Fix 3: FanArt.tv 404 not handled gracefully**
HTTP 404 from FanArt.tv (movie has no artwork in their DB) raised an unhandled `HTTPError` and aborted artwork download for the entire folder. Now caught specifically; logs at DEBUG level; TMDB-sourced files still downloaded.

---

## v2.x — Music, Databases & Suite Consolidation

### v2.0.0 — MusicBrainz Local PostgreSQL Database Support

Major feature enabling zero-latency, zero-rate-limit music metadata lookups from a locally mirrored MusicBrainz database.

**`MusicBrainzLocalProvider` class:**
- `search_artist(name)` — fuzzy match against `artist.name` + `artist.sort_name`
- `get_album(artist_mbid, title)` — join `release_group` + `release`
- `get_tracks(release_mbid)` — full tracklist with ISRC and duration

**Priority chain (updated):**
Local PostgreSQL DB → Apple MusicKit → iTunes Search API → MusicBrainz REST API

**Setup:** Download PostgreSQL dump from data.metabrainz.org; import with provided `setup-musicbrainz-db.sh`.

**Dependencies:** `psycopg2-binary` (only imported when `musicbrainz_db.skip: false`).

---

### v2.1.0 — MusicBrainz JSON Dump Support

Offline MusicBrainz lookups without PostgreSQL. The JSON dump directory (MBID-keyed JSON files) is queried directly.

**`MusicBrainzJsonProvider` class:**
- Reads MBID-keyed JSON files from dump directory
- Builds name-to-MBID index on first use; caches as `artist_index.json`
- No dependencies beyond stdlib

**Priority chain:** Local PostgreSQL DB → JSON Dump → Apple MusicKit → iTunes Search API → MusicBrainz REST API

| Feature | PostgreSQL | JSON Dump |
|---------|-----------|-----------|
| Setup complexity | High | Low |
| Disk space | ~30 GB | ~80 GB |
| Lookup speed | <1ms | ~5ms |
| Dependencies | psycopg2 | None |

---

### v2.1.1 — Fix null label-info crash in MusicBrainz get_release

**Bug fix.** `KeyError` crash on releases with no associated label (independent releases, promo copies).

MusicBrainz release JSON can contain `null` entries in the `label-info` array. Fixed with a null guard:
```python
labels = [li['label']['name'] for li in data.get('label-info', []) if li and li.get('label')]
```
Fix applied to both `MusicBrainzJsonProvider` and `MusicBrainzProvider` (REST).

---

### v2.1.2 — Fix MusicBrainz rate limiting and enabled flag

**Three bug fixes.**

**Fix 1: Rate limiting applied before request instead of after.** `time.sleep()` was positioned before the request; moved to after. Back-to-back calls were firing without any gap.

**Fix 2: 503 responses not retried.** Added exponential backoff: 2s, 4s, 8s, 16s before raising.

**Fix 3: `enabled` flag not checked.** `MusicBrainzProvider` made REST calls even when `enabled: false`. Added check in `__init__()`; provider removed from active list when disabled.

**Fix 4 (bonus):** Contact email now included in User-Agent header as required by MusicBrainz ToS: `PlexMetadataGenerator/2.1 (your@email.com)`.

---

### v2.2.0 — iTunes Search API + Apple MusicKit (replaces Spotify)

**Breaking change:** Spotify removed from all providers. Replaced with iTunes Search API (always active, free) and optional Apple MusicKit (richer metadata, Apple Developer required).

**iTunes Search API:**
- Endpoint: `https://itunes.apple.com/search?term={artist}+{album}&media=music&entity=album`
- Artwork: URL substitution for 3000×3000: `re.sub(r'\d+x\d+bb', '3000x3000bb', url)`
- NFO tag: `<appleid>` replaces `<spotifyid>`
- Zero dependencies; no auth

**Apple MusicKit:**
- ES256 JWT signed locally with `.p8` private key
- Requires: `pip3 install cryptography`
- Richer metadata: ISRC codes, composer credits, explicit flag

**Config migration:**
Remove `spotify` block; optionally add `apple_musickit` block. Existing `<spotifyid>` NFO tags are not modified.

---

### v2.3.0 — expand extract_artwork.py: music, config, dialogs, multi-volume

`extract_artwork.py` expanded from a single-purpose movie MP4 extractor into a full-suite artwork tool covering all three media types.

**New: Music mode**
- `artist.jpg` — copied from first audio file in first album subdir
- `folder.jpg` — extracted per album dir from first audio file
- Audio formats: `.mp3`, `.m4a`, `.flac`, `.aac`, `.ogg`, `.opus`, `.wma`, `.wav`

**New: Config-driven operation**
`plex-extract-artwork.conf` stores library roots; first run prompts for paths via native dialogs.

**New: ffmpeg strategy cascade**
1. `-map 0:v:1` (cover art stream)
2. `-map 0:v:0` (first video stream)
3. `-vsync 2 -frames:v 1` (single-frame fallback)

**New CLI flags:** `--config`, `--media-type`, `--extract`, `--force`, `--no-prompts`, `--movie`, `--show`, `--artist`, `--debug`

**Legacy positional-arg compatibility maintained:**
```bash
python3 extract_artwork.py movies "/path/to/Movies" --extract  # still works
```

---

### v2.4.0 — fuzzy_variants + --workers merged into metadata generator

Two capabilities from `scraper.py` ported into the Metadata Generator, making `scraper.py` optional preprocessing only.

**`fuzzy_variants()` — 6-variant fuzzy title matching**

| Step | Transform | Example |
|------|-----------|---------|
| 1 | Original title | The Dark Knight Rises |
| 2 | Strip punctuation | The Dark Knight Rises |
| 3 | Remove leading article | Dark Knight Rises |
| 4 | Move trailing `, The` to front | The Matrix |
| 5 | Strip subtitle after ` - ` or `: ` | Se7en |
| 6 | ASCII-fold accented chars | Amelie |
| 6b | ASCII-fold + strip punctuation | combined |

Applied in: `TMDbMovieProvider.search_movie()`, `TVDbProvider.search_show()`, `TMDbProvider.search_show()`.

**`--workers N` — parallel processing**

```bash
python3 plex_metadata_generator.py --workers 4 --media-type all
```

| Workers | Recommended for |
|---------|----------------|
| 1 | Daily scheduled runs (default) |
| 4 | Initial bulk runs (~4× throughput) |
| 8 | Very large libraries (10k+ items) |

Uses `ThreadPoolExecutor` + `as_completed()`; default of 1 means zero overhead vs. before.

**`scraper.py` retirement:** All unique capabilities are now native to the Metadata Generator. `scraper.py` and `rename_movies.py` are optional preprocessing tools only.

---

## API Provider Summary (v2.4.0)

| Provider | Media | Auth | Cost |
|----------|-------|------|------|
| TMDB | Movies + TV | API key | Free |
| TVDB v4 | TV (primary) | API key | Free |
| FanArt.tv | Movies + TV (artwork) | API key | Free personal key |
| Tunarr | TV (channel metadata) | None | Local SQLite |
| iTunes Search API | Music (primary) | None | Free |
| Apple MusicKit | Music (optional) | ES256 JWT + .p8 | $99/yr Apple Developer |
| MusicBrainz REST | Music (fallback) | Contact email in UA | Free |
| MusicBrainz PostgreSQL | Music (local, fastest) | None | Local DB |
| MusicBrainz JSON Dump | Music (local, no DB) | None | Local files |
| OpenSubtitles | Subtitles (primary) | API key | Free (5/day); 40/day with key |
| Subdl | Subtitles (fallback) | Optional key | Free |

---

*See [RELEASE_NOTES_v1.1.md](RELEASE_NOTES_v1.1.md) for the v1.1.0 extended changelog including migration notes from v1.0.0.*
