# Plex Metadata Generator — Reference

The Plex Metadata Generator is a scheduled automation layer that complements the core suite (`scraper.py`, `extract_artwork.py`). It runs daily, picks up newly added media, generates NFO files, downloads the complete FileBot-compatible artwork set, and triggers a Plex library refresh automatically.

---

## Scripts

| Script | Media types | Extra providers |
|--------|-------------|----------------|
| [`plex_metadata_generator.py`](../../metadata-generator/plex_metadata_generator.py) | TV shows + Movies | TVDB, TMDB, FanArt.tv, Tunarr |
| [`plex_metadata_generator_extended.py`](../../metadata-generator/plex_metadata_generator_extended.py) | TV shows + Movies + Music | + Spotify, MusicBrainz |

Both scripts write the **identical NFO format** as `scraper.py` — they are fully interchangeable and produce no conflicts.

---

## How Selective Processing Works

**The script never re-processes a complete item.** Before any API call, it checks whether the item already has both its NFO file and all expected artwork files. If everything is present, the item is logged as `⏭ already complete` and skipped entirely.

Each artwork file is checked independently — if `poster.jpg` exists but `logo.png` is missing, only `logo.png` is fetched (and only FanArt.tv is called, not TMDB).

### Skip conditions per item type

| Item | NFO | Artwork (ALL must exist to skip) |
|------|-----|----------------------------------|
| Movie folder | `Movie.nfo` | `poster.jpg` `folder.jpg` `backdrop.jpg` `clearart.png` `disc.png` `logo.png` |
| TV show root | `tvshow.nfo` | `poster.jpg` `banner.jpg` `fanart.jpg` `clearart.png` `logo.png` `landscape.jpg` |
| Season folder | `season.nfo` | `poster.jpg` |
| Episode | `{stem}.nfo` | `{stem}-thumb.jpg` |
| Music album | `album.nfo` | `cover.jpg` |
| Music artist | `artist.nfo` | `artist.jpg` |

Use `--force` to override all skip checks and regenerate everything.

### NFO-first ID extraction

When `Movie.nfo` already exists but artwork is missing, the script reads the `<uniqueid type="tmdb">` tag from the existing NFO to get the TMDB ID directly — skipping the search API call. Re-runs over an already-catalogued library make **zero** search API calls; only the image download calls for missing files are made.

---

## First-Run Setup Dialogs

When you run the script for the first time (or when required settings are missing from the config file), a series of native OS dialogs guides you through setup — no config file editing required.

### 1 — Library paths (Movies, TV Shows, Music)

For each media type, a dialog asks whether you have that library. If you click **Yes**, a native folder-browser opens so you can select the root volume. After each selection you see:

> **Add another volume?** — **Yes** | **No**

Click **Yes** to add a second drive, NAS share, or USB volume of the same type. Click **No** (Done) when all volumes for that media type have been added. Repeat for TV Shows and Music.

All selected paths are written to the config as a list (`movies_library_roots`, `tv_library_roots`, `music_library_roots`) so every volume is scanned on every run.

### 2 — API keys

For each service whose key is missing or contains a placeholder value, a dialog shows the service name, what it's used for, where to get a free key, and a text field to enter it. After you enter a key it is **validated against the live API** before being accepted — if the key is rejected, an error dialog explains what went wrong and offers to retry. Required keys (TMDB, TVDB) show a warning if skipped; optional keys (FanArt.tv, Plex token, OpenSubtitles) are silently skipped.

### 3 — Scan mode

After path and key setup, a dialog asks:

> **Force a full rescan of all media?**
> • **Yes** — process every item, even those that already have NFO files and artwork *(first-time setup or full refresh)*
> • **No** — skip items that are already complete *(recommended for ongoing / scheduled use)*

Choosing **Yes** is equivalent to passing `--force` on the command line.

### 4 — Save to config

After each dialog group (paths, keys) a **Save?** dialog offers to write the answers back to the config file so you are never prompted again for that information.

### 15-day API key revalidation

Every 15 days (tracked in `{cache_dir}/key_validation_state.json`) the script tests all configured API keys against their respective live APIs. This check runs in **both interactive and scheduled (`--no-prompts`) modes** — because an expired key means the scheduled job cannot do useful work.

If a key has expired or been deactivated, a blocking dialog appears with the message:

> *"The API key for [service] has expired or is inactive. Please enter a new valid key. The current job will pause and not continue until a new key is entered."*

The new key is validated before being accepted. If the new key also fails, the user is asked whether to try again or skip that service for this run. If skipped, processing continues for all other services; the affected service's functionality (metadata lookup, artwork, subtitles) is unavailable until the key is updated.

The validation timestamp is written after each full check. The next check is due 15 days later.

### Suppressing dialogs for scheduled runs

Initial setup dialogs (paths, missing keys, force flag) are bypassed when `--no-prompts` is passed. Every scheduling artifact (LaunchAgent, systemd service, cron, Windows Task Scheduler) includes this flag automatically.

**Exception:** the expired-key blocking dialog always appears when a key fails the 15-day revalidation check, regardless of `--no-prompts`. A scheduled job with an expired key would silently produce no output — the dialog ensures the problem is surfaced and fixed before the run continues.

---

## CLI Reference

### `plex_metadata_generator.py`

```bash
python3 plex_metadata_generator.py [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--config PATH` | `/etc/plex-metadata-generator.conf` | Config file path |
| `--media-type {tv,movies,all}` | `tv` | Which library to process |
| `--show NAME` | — | Process only this TV show folder |
| `--movie NAME` | — | Process only this movie folder |
| `--force` | off | Overwrite existing NFO and artwork |
| `--no-prompts` | off | Skip all setup dialogs (for unattended/scheduled runs) |
| `--debug` | off | Enable debug logging |

### `plex_metadata_generator_extended.py`

```bash
python3 plex_metadata_generator_extended.py [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--config PATH` | `/etc/plex-metadata-generator.conf` | Config file path |
| `--media-type {tv,movies,music,all}` | `all` | Which library to process |
| `--item NAME` | — | Process only a specific show, movie, or artist |
| `--force` | off | Overwrite existing NFO and artwork |
| `--debug` | off | Enable debug logging |

---

## Configuration Reference

### `plex-metadata-generator.conf` (TV + Movies)

Single-volume example (the setup dialogs populate this automatically):

```json
{
  "tv_library_root": "/mnt/media/TV",
  "movies_library_root": "/mnt/media/Movies",
  "cache_dir": "/var/cache/plex-metadata",

  "plex": {
    "url": "http://localhost:32400",
    "token": "YOUR_PLEX_TOKEN",
    "tv_library_key": "1",
    "movies_library_key": "2"
  },

  "tunarr": { "db_path": "/opt/tunarr/cache/tunarr.db" },

  "tvdb": { "api_key": "YOUR_TVDB_KEY" },
  "tmdb": { "api_key": "YOUR_TMDB_KEY" },

  "fanart_tv": { "api_key": "YOUR_FANART_TV_KEY" },

  "metadata_priority": ["tvdb", "tmdb", "tunarr"]
}
```

`fanart_tv.api_key` is optional — if absent, `clearart.png`, `disc.png`, and `logo.png` are skipped with a warning. All other artwork downloads (poster, backdrop, folder) still work without it.

**Multi-volume example** — when you have media spread across multiple drives:

```json
{
  "tv_library_roots":     ["/Volumes/Drive1/TV", "/Volumes/Drive2/TV"],
  "movies_library_roots": ["/Volumes/Drive1/Movies", "/Volumes/NAS/Movies"],
  "music_library_roots":  ["/Volumes/Drive1/Music"]
}
```

The plural keys (`*_library_roots`) take priority over the singular keys (`*_library_root`). The setup dialogs populate the plural form automatically when you add more than one volume.

### Extended config adds

```json
{
  "music_library_root": "/mnt/media/Music",
  "plex": { "music_library_key": "3" },
  "musicbrainz": { "contact": "your@email.com" },
  "spotify": {
    "client_id": "YOUR_SPOTIFY_CLIENT_ID",
    "client_secret": "YOUR_SPOTIFY_CLIENT_SECRET"
  }
}
```

---

## Expected Folder Structures

### Movies

```
/Movies/
├── Back to the Future (1985)/
│   ├── Back to the Future (1985).mp4
│   ├── Movie.nfo           ← generated
│   ├── poster.jpg          ← TMDB official poster (preferred) or FanArt.tv fallback
│   ├── folder.jpg          ← copy of poster.jpg (Plex alternate naming)
│   ├── backdrop.jpg        ← TMDB backdrop or FanArt.tv fallback
│   ├── clearart.png        ← FanArt.tv hdmovieclearart
│   ├── disc.png            ← FanArt.tv moviedisc (bluray → dvd → any)
│   └── logo.png            ← FanArt.tv hdmovielogo
```

### TV Shows

```
/TV Shows/
├── Breaking Bad/
│   ├── tvshow.nfo          ← generated
│   ├── poster.jpg          ← TVDB series poster
│   ├── banner.jpg          ← TVDB series banner
│   ├── fanart.jpg          ← TVDB series background
│   ├── clearart.png        ← FanArt.tv hdclearart
│   ├── logo.png            ← FanArt.tv hdtvlogo
│   ├── landscape.jpg       ← FanArt.tv tvthumb
│   ├── Season 1/
│   │   ├── season.nfo
│   │   ├── poster.jpg      ← TVDB season poster
│   │   ├── Breaking Bad - S01E01.mp4
│   │   ├── Breaking Bad - S01E01.nfo
│   │   └── Breaking Bad - S01E01-thumb.jpg
```

### Music (extended script only)

```
/Music/
├── Pink Floyd/
│   ├── artist.nfo          ← generated
│   ├── artist.jpg          ← Spotify artist image
│   ├── The Dark Side of the Moon/
│   │   ├── album.nfo
│   │   ├── cover.jpg       ← Spotify album art
│   │   ├── 01 - Speak to Me.flac
│   │   └── 01 - Speak to Me.nfo
```

---

## Artwork Download — Source Priority

| File | Primary source | Fallback |
|------|---------------|---------|
| `poster.jpg` | TMDB `poster_path` (official studio art) | FanArt.tv `movieposter` |
| `folder.jpg` | Copy of `poster.jpg` | — |
| `backdrop.jpg` | TMDB `backdrop_path` | FanArt.tv `moviebackground` |
| `clearart.png` | FanArt.tv `hdmovieclearart` | FanArt.tv `movieart` |
| `disc.png` | FanArt.tv `moviedisc` (bluray) | dvd → any |
| `logo.png` | FanArt.tv `hdmovielogo` | FanArt.tv `movielogo` |

**Original studio posters are always preferred** — TMDB serves official artwork from studios. FanArt.tv is used as a fallback for poster/backdrop and as the exclusive source for clearart, disc, and logo.

All downloaded files are validated to be > 1000 bytes before being saved (same threshold as `extract_artwork.py`). Plex ignores zero-byte or truncated files.

---

## Plex Local Media Assets Compatibility

All output filenames are the exact filenames Plex's **Local Media Assets** agent reads natively. No custom plugin required.

| Filename | Plex reads as | Location |
|----------|--------------|---------|
| `Movie.nfo` | Movie metadata | Movie folder |
| `poster.jpg` | Primary poster/thumbnail | Movie folder, Show root, Season folder |
| `folder.jpg` | Folder icon | Movie folder |
| `backdrop.jpg` | Background/fanart art | Movie folder |
| `fanart.jpg` | Background/fanart art | Show root |
| `clearart.png` | Clear art (Plex themes) | Movie folder, Show root |
| `banner.jpg` | Banner | Show root |
| `logo.png` | Studio/title logo | Movie folder, Show root |
| `disc.png` | Disc art | Movie folder |
| `landscape.jpg` | Landscape/thumb | Show root |
| `tvshow.nfo` | Show metadata | Show root |
| `season.nfo` | Season metadata | Season folder |
| `{stem}.nfo` | Episode metadata | Season folder |
| `{stem}-thumb.jpg` | Episode thumbnail | Season folder |

To activate: go to **Plex → Settings → Libraries → [Your Library] → Edit → Agents** and drag **Local Media Assets** to the top of the list.

---

## NFO Format

Output NFO files use the same XML format as `scraper.py` — they are fully interchangeable.

### Movie.nfo

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<movie>
  <title>Back to the Future</title>
  <originaltitle>Back to the Future</originaltitle>
  <year>1985</year>
  <plot>Marty McFly travels back in time...</plot>
  <rating>8.5</rating>
  <runtime>116</runtime>
  <genre>Adventure</genre>
  <genre>Comedy</genre>
  <studio>Universal Pictures</studio>
  <director>Robert Zemeckis</director>
  <actor><name>Michael J. Fox</name><role>Marty McFly</role></actor>
  <uniqueid type="tmdb" default="true">105</uniqueid>
  <uniqueid type="imdb" default="false">tt0088763</uniqueid>
</movie>
```

### tvshow.nfo

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<tvshow>
  <title>Breaking Bad</title>
  <year>2008</year>
  <plot>A high school chemistry teacher...</plot>
  <rating>9.5</rating>
  <runtime>47</runtime>
  <status>Ended</status>
  <uniqueid type="tvdb" default="true">81189</uniqueid>
  <uniqueid type="tmdb" default="false">1396</uniqueid>
  <uniqueid type="imdb" default="false">tt0903747</uniqueid>
  <genre>Crime</genre>
  <genre>Drama</genre>
</tvshow>
```

---

## API Providers

| Provider | Used for | API key required | Free tier |
|----------|----------|-----------------|-----------|
| **TVDB** (v4) | TV show + episode metadata, season/episode artwork | Yes | Yes — [thetvdb.com/api-information](https://thetvdb.com/api-information) |
| **TMDB** (v3) | Movie metadata, movie poster + backdrop | Yes | Yes — [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) |
| **FanArt.tv** (v3) | Movie clearart, disc, logo; TV clearart, logo, landscape; poster/backdrop fallback | Yes | Yes — [fanart.tv/get-an-api-key](https://fanart.tv/get-an-api-key/) |
| **Tunarr** | TV show fallback metadata | No (local DB) | — |
| **Spotify** | Music artist + album metadata, artwork | Yes | Yes — [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) |
| **MusicBrainz** | Music fallback metadata | No | Yes |
| **Plex** | Library refresh after generation | Token | — |

---

## "Now Playing" Board — Future Architecture

The complete local folder structure (NFO + all 6 artwork files per movie, full artwork set per show) is designed to support a future **digital "Now Playing" board**:

- Queries the Plex API or Apple TV "Now Playing" state for what's currently playing
- Looks up the matching local folder by title/year
- Serves `poster.jpg`, `backdrop.jpg`, `logo.png`, and NFO metadata directly to a display board — no additional API calls needed at display time

Everything is already cached locally after the generator runs. This makes the future feature viable without runtime API dependencies.

---

## Scheduling

See [`metadata-generator/scheduling/`](../../metadata-generator/scheduling/) for platform-specific install scripts:

| Platform | Method | Installer |
|----------|--------|-----------|
| macOS | LaunchAgent | `install-macos.sh` |
| Linux | systemd timer | `install-linux.sh` |
| Windows | Task Scheduler | `install-windows.ps1` |
| Any | Cron | `plex-metadata-generator-cron` |
| Docker | `docker-compose.yml` | — |

The default schedule runs daily at 2 AM. Thanks to selective processing, subsequent daily runs typically complete in 1–5 minutes regardless of library size — only newly added items are processed.

---

## `health-check.py`

```bash
python3 metadata-generator/health-check.py
```

Checks:
- Configuration file validity and required keys
- API connectivity (TVDB, TMDB, FanArt.tv, Plex)
- Tunarr database accessibility
- systemd timer / cron status
- Recent log entries and error count
- File permissions on library roots and cache directory
- Disk space

---

## Subtitle Download + Embedding

When `subtitles.enabled` is `true` in the config, the generator automatically downloads subtitles for each movie and TV episode after processing its NFO and artwork.

### What gets written

For each video file (`Movie.mp4`, `Show - S01E01.mp4`, etc.):

| Output | Purpose |
|--------|---------|
| `{stem}.{lang}.srt` | Plex sidecar — picked up automatically by Local Media Assets |
| Embedded `mov_text` track in MP4/M4V | Apple TV local media playback — same track type Subler writes |

MKV files receive the sidecar only; `mov_text` embedding requires an MP4/M4V container.

### Language detection

Language is resolved in this order:
1. `subtitles.language` in config — if not `"auto"`, this value is used directly (e.g., `"en"`, `"fr"`)
2. macOS `AppleLanguages` system preference (`defaults read -g AppleLanguages`)
3. Python `locale.getdefaultlocale()` — cross-platform fallback
4. `"en"` — hard fallback if detection fails

### Subtitle sources

**OpenSubtitles** (primary) — free API key at [opensubtitles.com/consumers](https://www.opensubtitles.com/consumers)

| Account type | Downloads/day |
|---|---|
| No account (API key only) | 5 |
| Free account with credentials | 40 |

**Subdl** (fallback) — no key required; optional API key improves rate limits

Both are tried in order per video file. The script logs `requests_remaining` after each OpenSubtitles download so you can monitor quota.

### Selective skip logic

A video file is skipped if **both** of these are true:
1. `{stem}.{lang}.srt` sidecar already exists
2. The video already has an embedded subtitle stream (detected via `ffprobe`)

This means re-runs are zero-cost for already-subtitled files.

### Embed behavior

ffmpeg writes the subtitle as a `mov_text` (tx3g) track — the same format Subler uses — tagged with the ISO 639-2 language code (`eng`, `fra`, etc.) and marked as the default subtitle track. The operation is atomic: ffmpeg writes to a `.tmp.mp4` file first, then replaces the original only after a size sanity check (temp must be ≥ 95% of original).

If ffmpeg is not on PATH, sidecar-only mode is used automatically with a warning logged.

### Configuration

```json
"subtitles": {
  "enabled": true,
  "language": "auto",
  "sidecar": true,
  "embed_in_file": true,
  "opensubtitles": {
    "api_key": "YOUR_OPENSUBTITLES_API_KEY",
    "username": "YOUR_OPENSUBTITLES_USERNAME",
    "password": "YOUR_OPENSUBTITLES_PASSWORD"
  },
  "subdl": {
    "api_key": "YOUR_SUBDL_API_KEY_OR_LEAVE_EMPTY"
  }
}
```

`username` and `password` are optional — omitting them gives anonymous mode (5 downloads/day per IP). With credentials, the limit rises to 40/day per API key. OpenSubtitles API key registration is free and requires no credit card.

### "Now Playing" board note

The `{stem}.{lang}.srt` sidecar placed alongside the video means a future "Now Playing" board can serve synchronized subtitles directly from the local folder — no subtitle API call needed at display time.

---

## Log Files

The generator writes to the system log at `/var/log/plex-metadata-generator.log` when running with sufficient permissions, and always echoes to stdout. Format:

```
2026-06-17 02:00:01 - __main__ - INFO - Processing movie: Back to the Future (1985)
2026-06-17 02:00:01 - __main__ - INFO -   ✓ Wrote Movie.nfo
2026-06-17 02:00:02 - __main__ - INFO -   Downloaded: poster.jpg → /mnt/media/Movies/Back to the Future (1985)
2026-06-17 02:00:02 - __main__ - INFO -   ✓ Copied poster.jpg → folder.jpg
2026-06-17 02:00:03 - __main__ - INFO -   Downloaded: logo.png → /mnt/media/Movies/Back to the Future (1985)
2026-06-17 02:00:03 - __main__ - INFO - ⏭ The Dark Knight (2008) — already complete
```
