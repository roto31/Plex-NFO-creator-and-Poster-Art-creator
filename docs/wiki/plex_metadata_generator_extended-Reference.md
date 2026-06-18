# plex_metadata_generator_extended.py — Reference

The extended metadata generator is a superset of `plex_metadata_generator.py`. It adds full **Music library support** on top of the base script's Movies and TV capabilities, and integrates iTunes Search API, optional Apple MusicKit, MusicBrainz (local JSON dump or PostgreSQL), and Discogs as a final fallback for vinyl, older releases, classical, and jazz.

If you don't have a music library in Plex, use `plex_metadata_generator.py` instead — it has no music-related dependencies and is lighter weight.

---

## At a Glance

| Feature | Base script | Extended script |
|---------|-------------|-----------------|
| Movie NFO + artwork | ✅ | ✅ |
| TV show NFO + artwork | ✅ | ✅ |
| Music artist/album/track NFO | ❌ | ✅ |
| iTunes Search API | ❌ | ✅ (always active, no key needed) |
| Apple MusicKit | ❌ | ✅ (optional) |
| MusicBrainz JSON dump (local, no DB) | ❌ | ✅ (auto-detected) |
| MusicBrainz local PostgreSQL DB | ❌ | ✅ (optional) |
| Discogs | ❌ | ✅ (fallback for vinyl/older/classical) |
| Music fuzzy matching | ❌ | ✅ (album name variants + accent folding) |
| Music checkpoint/resume | ❌ | ✅ (survives Ctrl+C mid-library) |
| Subtitle download + embedding | ✅ | ✅ |
| Fuzzy title matching (movies/TV) | ✅ | ✅ |
| `--workers N` parallel processing | ✅ | ✅ (thread-safe up to 16) |
| Selective skip (zero API calls if complete) | ✅ | ✅ |
| First-run setup dialogs | ✅ | ✅ |
| 15-day API key revalidation | ✅ | ✅ |

---

## CLI Reference

```bash
python3 plex_metadata_generator_extended.py [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--config PATH` | `/etc/plex-metadata-generator.conf` | Config file path |
| `--media-type {tv,movies,music,all}` | `all` | Which library type(s) to process |
| `--item NAME` | — | Process only the named show, movie, or artist folder |
| `--force` | off | Regenerate all NFOs and artwork even if already present |
| `--workers N` | `1` | Parallel workers. Up to `16` is safe (all providers use class-level thread locks). Use `4`–`8` for initial bulk runs; `1` for daily scheduled runs. |
| `--debug` | off | Verbose per-item logging |

### Examples

```bash
# Process everything (recommended for daily scheduled use)
python3 plex_metadata_generator_extended.py --media-type all

# Initial bulk pass with parallel workers (up to 16 safe)
python3 plex_metadata_generator_extended.py --media-type all --workers 8

# Music library only
python3 plex_metadata_generator_extended.py --media-type music

# One artist only
python3 plex_metadata_generator_extended.py --media-type music --item "Pink Floyd"

# Music with max workers
python3 plex_metadata_generator_extended.py --media-type music --workers 16

# Force regenerate everything
python3 plex_metadata_generator_extended.py --media-type all --force
```

---

## Configuration Reference

The extended script uses the same config file as the base script, with additional music-specific sections.

### Full annotated configuration

```json
{
  "comment": "Plex Metadata Generator — Extended (TV + Movies + Music)",

  "movies_library_roots": ["/Volumes/Movies"],
  "tv_library_roots":     ["/Volumes/TV"],
  "music_library_roots":  ["/Volumes/Music"],

  "comment_single_volume": "Or use the singular forms for a single drive:",
  "movies_library_root":   "/Volumes/Movies",
  "tv_library_root":       "/Volumes/TV",
  "music_library_root":    "/Volumes/Music",

  "cache_dir": "/var/cache/plex-metadata",

  "plex": {
    "url": "http://localhost:32400",
    "token": "YOUR_PLEX_TOKEN",
    "movies_library_key": "1",
    "tv_library_key":     "2",
    "music_library_key":  "3"
  },

  "tunarr": {
    "db_path": "/opt/tunarr/cache/tunarr.db"
  },

  "tmdb":   { "api_key": "YOUR_TMDB_API_KEY",   "enabled": true },
  "tvdb":   { "api_key": "YOUR_TVDB_API_KEY",   "enabled": true },
  "fanart_tv": { "api_key": "YOUR_FANART_TV_KEY" },

  "comment_music": "Music providers — priority: Apple MusicKit → iTunes → MusicBrainz JSON dump → Discogs",

  "musicbrainz_contact": "your@email.com",

  "musicbrainz_db": {
    "comment": "Optional local PostgreSQL mirror — instant, no rate limits",
    "host":     "localhost",
    "port":     5432,
    "dbname":   "musicbrainz",
    "user":     "musicbrainz",
    "password": "",
    "schema":   "musicbrainz",
    "skip":     true
  },

  "musicbrainz_json_dump_dir": "",
  "comment_mb_json": "Leave empty to auto-detect from ~/Library/Application Support/PlexMetadataGenerator/mb-json/ (macOS)",

  "discogs": {
    "comment": "Optional — free personal token at discogs.com/settings/developers; best for vinyl, older releases, classical, jazz",
    "token": "YOUR_DISCOGS_PERSONAL_TOKEN"
  },

  "apple_musickit": {
    "comment": "Optional — requires Apple Developer account ($99/yr)",
    "enabled": false,
    "team_id": "YOUR_APPLE_TEAM_ID",
    "key_id":  "YOUR_MUSICKIT_KEY_ID",
    "private_key_path": "/path/to/AuthKey_KEYID.p8",
    "storefront": "us",
    "skip": false
  },

  "subtitles": {
    "enabled": false,
    "language": "auto",
    "sidecar": true,
    "embed_in_file": true,
    "opensubtitles": {
      "api_key":  "YOUR_OPENSUBTITLES_API_KEY",
      "username": "YOUR_OPENSUBTITLES_USERNAME",
      "password": "YOUR_OPENSUBTITLES_PASSWORD"
    },
    "subdl": {
      "api_key": ""
    }
  },

  "metadata_priority": {
    "tv":     ["tvdb", "tmdb", "tunarr"],
    "movies": ["tmdb"],
    "music":  ["apple_musickit", "itunes", "mb_json", "discogs"]
  },

  "logging": {
    "level": "INFO",
    "file":  "/var/log/plex-metadata-generator.log",
    "max_size_mb": 100,
    "backup_count": 5
  }
}
```

### Multi-volume libraries

When media is spread across multiple drives or NAS volumes, use the plural `_roots` keys:

```json
{
  "movies_library_roots": ["/Volumes/Drive1/Movies", "/Volumes/NAS/Movies"],
  "tv_library_roots":     ["/Volumes/Drive1/TV",     "/Volumes/Drive2/TV"],
  "music_library_roots":  ["/Volumes/Music1",        "/Volumes/Music2"]
}
```

The plural form takes priority over the singular form. The first-run setup dialogs always write the plural form.

---

## Expected Folder Structures

### Movies

```
/Movies/
├── Back to the Future (1985)/
│   ├── Back to the Future (1985).mp4
│   ├── Movie.nfo               ← TMDB metadata
│   ├── poster.jpg              ← TMDB official poster
│   ├── folder.jpg              ← copy of poster.jpg (Plex alternate)
│   ├── backdrop.jpg            ← TMDB backdrop
│   ├── clearart.png            ← FanArt.tv transparent title art
│   ├── disc.png                ← FanArt.tv Blu-ray disc face
│   ├── logo.png                ← FanArt.tv studio/franchise logo
│   ├── Back to the Future (1985).en.srt  ← subtitle sidecar (if enabled)
```

### TV Shows

```
/TV Shows/
├── Breaking Bad/
│   ├── tvshow.nfo              ← TVDB series metadata
│   ├── poster.jpg              ← TVDB series poster
│   ├── banner.jpg              ← TVDB series banner
│   ├── fanart.jpg              ← TVDB series background
│   ├── clearart.png            ← FanArt.tv transparent title art
│   ├── logo.png                ← FanArt.tv series logo
│   ├── landscape.jpg           ← FanArt.tv wide thumbnail
│   ├── Season 1/
│   │   ├── season.nfo
│   │   ├── poster.jpg          ← TVDB season poster
│   │   ├── Breaking Bad - S01E01 - Pilot.mp4
│   │   ├── Breaking Bad - S01E01 - Pilot.nfo    ← episode metadata
│   │   ├── Breaking Bad - S01E01 - Pilot-thumb.jpg
│   │   └── Breaking Bad - S01E01 - Pilot.en.srt ← subtitle sidecar
```

### Music (extended script only)

```
/Music/
├── Pink Floyd/
│   ├── artist.nfo              ← MusicBrainz / iTunes artist metadata
│   ├── artist.jpg              ← MusicKit artist image or iTunes fallback
│   ├── The Dark Side of the Moon/
│   │   ├── album.nfo           ← iTunes / MusicBrainz album metadata
│   │   ├── cover.jpg           ← iTunes 3000×3000 album art
│   │   ├── folder.jpg          ← copy of cover.jpg
│   │   ├── 01 - Speak to Me.flac
│   │   ├── 01 - Speak to Me.nfo  ← track metadata (MBID, ISRC)
│   │   ├── 02 - Breathe.flac
│   │   └── 02 - Breathe.nfo
```

---

## Music Processing — Provider Chain

Music metadata is sourced from a cascading chain of providers, tried in priority order:

```
Apple MusicKit (optional — richer metadata, requires Developer account)
  ↓ if not configured or no result
iTunes Search API (always active — free, no key, covers mainstream catalog)
  ↓ if no result
MusicBrainz JSON dump (optional — local, no rate limits, ~80 GB)
  ↓ if not configured or no result
Discogs (optional — best for vinyl, older releases, imports, classical, jazz)
  ↓ if no result
⚠ Warning logged — item skipped, no NFO written
```

Each provider is tried with up to 7 **fuzzy name variants** before moving to the next provider. See [Music Fuzzy Matching](#music-fuzzy-matching) below.

### iTunes Search API

The iTunes Search API is **always active** with no configuration required. It handles the majority of artist and album lookups for mainstream and independent artists.

- Album art is retrieved at 3000×3000 resolution (URL substitution: `re.sub(r'\d+x\d+bb', '3000x3000bb', url)`)
- NFO tag written: `<appleid>`
- Rate-limited at 20 req/s class-level — safe under `--workers 16`

### Apple MusicKit (optional upgrade)

When configured (`apple_musickit.enabled: true`), MusicKit is tried **first** and provides:
- Higher-confidence artwork from Apple's official catalog masters
- ISRC codes for each track
- Composer credits
- Content advisory (explicit flag)
- Richer artist images

Authentication is done locally using ES256 JWT signing — no server required. Tokens are generated from your `.p8` private key file, valid for 6 months per Apple's maximum. The `cryptography` package is required:
```bash
pip3 install cryptography
```

### MusicBrainz JSON dump (local, optional)

The recommended MusicBrainz mode — no database, no rate limits, runs entirely from local files.

**Setup using the included downloader script:**
```bash
python3 metadata-generator/download_mb_json.py
```
Downloads `artist.tar.xz` and `release-group.tar.xz` from the latest MusicBrainz weekly export and extracts to `~/Library/Application Support/PlexMetadataGenerator/mb-json/` (macOS). No configuration needed — the script auto-detects this path.

Options:
```
--check           Show what would be downloaded without downloading
--dir PATH        Override output directory
--keep-tarballs   Keep the .tar.xz files after extraction
```

Re-run monthly to keep the data current. MusicBrainz publishes new dumps weekly.

**Manual configuration** (if you extracted to a different path):
```json
"musicbrainz_json_dump_dir": "/path/to/mb-json"
```

### MusicBrainz local PostgreSQL database (optional, fastest)

For very large music libraries where even the JSON dump lookup is too slow:
- Download the full export from [data.metabrainz.org](https://data.metabrainz.org/pub/musicbrainz/data/fullexport/)
- Import with the included `setup-musicbrainz-db.sh`
- Requires: `pip3 install psycopg2-binary`
- Set `musicbrainz_db.skip: false` in config

### Discogs (optional fallback)

Discogs is the best source for **vinyl pressings, older releases, imports, classical, and jazz** — genres and formats where iTunes and MusicBrainz often have sparse coverage.

**Setup:**
1. Create a free account at [discogs.com](https://www.discogs.com)
2. Go to Settings → Developers → Generate a personal access token
3. Add to config:
```json
"discogs": {
  "token": "YOUR_DISCOGS_PERSONAL_TOKEN"
}
```

A personal token gives full image access and high rate limits (60 req/min). Rate limiting is enforced class-level — safe under `--workers 16`.

**What Discogs provides over iTunes:**
- Vinyl and 7"/12" single releases
- Catalog numbers and matrix numbers
- Label and sub-label details
- Physical format (Vinyl, CD, Cassette, etc.)
- Country of pressing
- Tracklist with positions for multi-disc/vinyl sets (e.g. `A1`, `B2`, `2-4`)

---

## Music NFO Formats

### artist.nfo

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<artist>
  <name>Pink Floyd</name>
  <formed>1965</formed>
  <biography>English rock band formed in London...</biography>
  <genre>Progressive Rock</genre>
  <genre>Psychedelic Rock</genre>
  <uniqueid type="musicbrainz">83d91898-7763-47d7-b03b-b92132375c47</uniqueid>
  <uniqueid type="appleid" default="true">563418514</uniqueid>
</artist>
```

### album.nfo

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<album>
  <title>The Dark Side of the Moon</title>
  <artist>Pink Floyd</artist>
  <year>1973</year>
  <label>Harvest Records</label>
  <genre>Progressive Rock</genre>
  <review>A concept album exploring themes of conflict, greed, time, and mental illness...</review>
  <uniqueid type="musicbrainz">b52a8f31-b5ab-34e9-92f4-f5b7110220f0</uniqueid>
  <uniqueid type="appleid" default="true">966330693</uniqueid>
</album>
```

### track.nfo (per audio file)

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<musicvideo>
  <title>Money</title>
  <artist>Pink Floyd</artist>
  <album>The Dark Side of the Moon</album>
  <year>1973</year>
  <track>7</track>
  <duration>382</duration>
  <uniqueid type="musicbrainz_recording">04762803-7573-4ef6-8b96-c0dd70888440</uniqueid>
  <uniqueid type="isrc">GBAYE7400068</uniqueid>
</musicvideo>
```

---

## Selective Processing — Music

The same selective skip logic from movies and TV applies to music items:

| Item | Skip if… |
|------|----------|
| Artist folder | `artist.nfo` exists AND `artist.jpg` exists |
| Album folder | `album.nfo` exists AND `cover.jpg` exists |
| Audio track | `{stem}.nfo` exists |

If only one file is missing (e.g. `cover.jpg` missing but `album.nfo` exists), only the missing file is fetched — no redundant metadata API calls are made.

---

## Music Fuzzy Matching

When an album or artist name returns no results from any provider, the script retries with progressively-cleaned variants via `_music_fuzzy_variants()`. Music fuzzy matching is separate from movie/TV fuzzy matching and includes music-specific patterns:

| Step | Transform | Example input → output |
|------|-----------|----------------------|
| 1 | Original | `The Dark Side of the Moon` |
| 2 | Strip disc/volume suffix | `Complete Works, Vol. 1` → `Complete Works` |
| 3 | Strip year in parens | `Abbey Road (Remastered 2009)` → `Abbey Road (Remastered)` |
| 4 | Strip feat./ft. | `Lose Yourself (feat. Eminem)` → `Lose Yourself` |
| 5 | Strip punctuation | `It's Alright, Ma` → `Its Alright Ma` |
| 6 | Remove leading article | `The Dark Side of the Moon` → `Dark Side of the Moon` |
| 7 | ASCII-fold accents | `Ágætis byrjun` → `Agaetis byrjun` |

All 7 variants are tried against all providers in chain order before giving up on an item. This handles the most common causes of missed albums:
- Remaster/anniversary edition suffixes (`(Deluxe Edition)`, `(Remastered 2015)`)
- Volume and disc numbers (`Vol. 2`, `Disc 1`)
- Featured artist credits in album titles
- Punctuation differences (`It's a` vs. `Its a`)
- Articles at different positions (`The ` prefix)
- Accented characters in non-English artist and album names

---

## Music Checkpoint / Resume

When processing a large music library, the script writes a checkpoint after every completed artist to:

```
~/Library/Caches/PlexMetadataGenerator/music_progress.json   (macOS)
~/.cache/plex-metadata-generator/music_progress.json          (Linux)
%LOCALAPPDATA%\PlexMetadataGenerator\music_progress.json      (Windows)
```

If the script is interrupted (Ctrl+C, power loss, system sleep), the next run automatically picks up where it left off — already-completed artists are skipped instantly with a `⏭ already completed (checkpoint)` log line.

To restart from scratch (ignore the checkpoint):
```bash
python3 plex_metadata_generator_extended.py --media-type music --force
```

`--force` clears the checkpoint and reprocesses every artist regardless of whether `artist.nfo` + `artist.jpg` already exist.

The checkpoint file is written atomically (temp file → replace) and is thread-safe under `--workers N`.

---

## Subtitle Download + Embedding

When `subtitles.enabled: true`, the extended script downloads subtitles for every movie and TV episode after processing NFO and artwork.

### What gets written

| Output | Purpose |
|--------|---------|
| `{stem}.{lang}.srt` | Plex sidecar — picked up automatically by Local Media Assets |
| Embedded `mov_text` track in MP4/M4V | Apple TV local playback (same format as Subler) |

MKV files receive the sidecar only.

### Language detection

1. `subtitles.language` in config (if not `"auto"`)
2. macOS `AppleLanguages` preference (`defaults read -g AppleLanguages`)
3. Python `locale.getdefaultlocale()`
4. `"en"` hard fallback

### Subtitle providers

**OpenSubtitles** (primary):
- API key required; free at [opensubtitles.com/consumers](https://www.opensubtitles.com/consumers)
- 5 downloads/day with key only; 40/day with username + password
- Searches by IMDb ID (from existing NFO) — no title-search overhead

**Subdl** (automatic fallback):
- No key required; API key optional for higher limits
- Used automatically when OpenSubtitles is unavailable or quota exhausted

### Embed behavior

ffmpeg writes a `mov_text` (tx3g) track tagged with ISO 639-2 language code, marked as default subtitle. Atomic write: temp file → sanity check (≥ 95% of original size) → replace original.

---

## First-Run Setup Dialogs

On first run (or when required config is missing), native OS dialogs guide you through setup:

1. **Library paths** — folder picker for each media type (Movies, TV, Music); supports multiple volumes per type
2. **API keys** — per-service dialog with sign-up URL; keys validated live before saving; invalid key shows error and re-prompts; optional keys have a Skip button
3. **Scan mode** — force full rescan vs. selective (skip already-complete items)
4. **Save to config** — writes all entered values back to the config file so subsequent runs are silent

The extended script has no `--no-prompts` flag — it runs unattended by default when all required config keys are present.

---

## Parallel Processing (`--workers N`)

```bash
# Initial bulk run — high throughput
python3 plex_metadata_generator_extended.py --workers 8 --media-type all

# Daily scheduled run — sequential (most items are already complete)
python3 plex_metadata_generator_extended.py --media-type all
```

| Workers | Best for | Notes |
|---------|----------|-------|
| 1 (default) | Daily scheduled runs | Zero overhead; most items skip immediately |
| 4–8 | Initial bulk pass | Good balance of throughput vs. API rate limits |
| 16 | Very large music libraries | Thread-safe — all providers use class-level locks; API rate limits are the only constraint |

Music is artist-parallel: with `--workers 8`, eight artists are processed simultaneously (all their albums and tracks included). All rate-limiting is enforced at the class level so all workers share a single serialized request timer per provider — no 429s or SSL errors from simultaneous bursts.

---

## Fuzzy Title Matching

All three search paths (movies, TV shows, TV fallback) use `fuzzy_variants()`:

| Step | Transform | Example |
|------|-----------|---------|
| 1 | Original | `Léon: The Professional` |
| 2 | Strip punctuation | `Léon  The Professional` |
| 3 | Remove leading article | *(no change here)* |
| 4 | Move trailing `, The` | `The Professional` *(if ends with ", The")* |
| 5 | Strip subtitle after ` - ` or `: ` | `Léon` |
| 6 | ASCII-fold accents | `Leon: The Professional` |
| 7 | ASCII-fold + strip punctuation | `Leon  The Professional` |

Returns on first hit — remaining variants not tried once a result is found.

---

## Scheduling

Every platform installer includes `--no-prompts` and runs the extended script at 2 AM daily.

| Platform | Method | Installer |
|----------|--------|-----------|
| macOS | LaunchAgent | `install-macos.sh` |
| Linux | systemd timer | `install-linux.sh` |
| Windows | Task Scheduler | `install-windows.ps1` |
| Any | Cron | `plex-metadata-generator-cron` |
| Docker | `docker-compose.yml` | — |

Typical daily run time: **1–5 minutes** regardless of library size, because selective processing skips all already-complete items.

---

## Differences from Base Script

| Aspect | `plex_metadata_generator.py` | `plex_metadata_generator_extended.py` |
|--------|-----------------------------|-----------------------------------------|
| `--media-type` choices | `tv`, `movies`, `all` | `tv`, `movies`, `music`, `all` |
| `--item` flag | `--show` / `--movie` | `--item` (any type) |
| Default `--media-type` | `tv` | `all` |
| Music providers | None | iTunes, Apple MusicKit, MusicBrainz JSON dump, Discogs |
| MusicBrainz PostgreSQL DB | Not imported | Imported when `musicbrainz_db.skip: false` |
| `cryptography` package | Not needed | Needed for Apple MusicKit only |
| Config keys | `tv_*`, `movies_*` | Same + `music_*`, `apple_musickit`, `musicbrainz_*`, `discogs` |
| Music fuzzy matching | No | `_music_fuzzy_variants()` — music-specific patterns |
| Music checkpoint | No | Auto-saves after each artist; survives interrupts |

Both scripts produce **identical NFO format** — they are fully interchangeable for movies and TV shows and produce no conflicts.

---

## Troubleshooting

**Music artist or album not found:**
- Use `--debug` to see which fuzzy variants were tried and which provider was reached
- Verify the iTunes result manually: `python3 -c "import urllib.request, urllib.parse, json; r = urllib.request.urlopen('https://itunes.apple.com/search?term=' + urllib.parse.quote('Pink Floyd') + '&media=music&entity=musicArtist&limit=5'); print(json.loads(r.read())['results'][0]['artistName'])"`
- If the album is a vinyl pressing, cassette, or pre-1980 release, iTunes may not have it — enable Discogs as a fallback (see Configuration)
- Artist disambiguation numbers in Discogs (e.g. `"Prince (3)"`) are automatically stripped

**Albums have NFO but no `cover.jpg`:**
- Most common cause: album name in folder doesn't match any provider's name closely enough for even the fuzzy variants to hit
- Run `--debug` to see which variant came closest and which provider returned a result
- The MusicBrainz JSON dump and Discogs both have broader physical-media coverage than iTunes for pre-digital releases

**MusicBrainz 503 errors:**
- This happens when hitting the REST API with parallel workers — but the REST API is not in the active provider chain
- The JSON dump is rate-limit-free; download it with `python3 metadata-generator/download_mb_json.py` and it auto-loads on the next run

**Music processing stopped mid-library:**
- Normal — Ctrl+C or system sleep is safe; the checkpoint saves after every completed artist
- Just re-run the same command; already-completed artists are skipped automatically
- To restart from scratch: add `--force`

**Apple MusicKit JWT errors:**
- Verify `team_id` (10 chars, from Membership section) and `key_id` (10 chars, from Keys section) are correct
- Verify the `.p8` file is the one downloaded when you created the key (re-download is not possible; create a new key if lost)
- Run `python3 -c "from cryptography.hazmat.primitives.asymmetric import ec; print('cryptography ok')"` to verify the package is installed

**Subtitle quota exhausted:**
- Check `requests_remaining` in the log after each OpenSubtitles download
- Subdl is tried automatically when OpenSubtitles fails — check `--debug` output
- Consider a free OpenSubtitles account (40/day vs. 5/day with key only)

**`clearart.png` / `disc.png` / `logo.png` not downloaded:**
- FanArt.tv key missing or invalid — check `fanart_tv.api_key` in config
- FanArt.tv 404 for that specific title (not all titles have FanArt.tv entries) — expected; warning logged; other artwork still downloads

---

## health-check.py

```bash
python3 metadata-generator/health-check.py
python3 metadata-generator/health-check.py --revalidate  # force key revalidation
```

Checks: config validity, API connectivity (TMDB, TVDB, FanArt.tv, OpenSubtitles, MusicKit), Plex reachability, MusicBrainz DB/JSON dump availability, systemd/launchd timer status, file permissions, disk space, recent log error count.

---

*See also: [Metadata Generator Reference](metadata-generator-Reference) · [API Keys Guide](API-Keys) · [Diagrams](Diagrams) · [Installation](Installation)*
