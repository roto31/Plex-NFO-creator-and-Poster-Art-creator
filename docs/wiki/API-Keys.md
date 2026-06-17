# API Keys — Where to Get Them

Every API key used by this suite is **free** (or optionally paid for higher limits). This page covers every service, what it is used for, and exactly how to obtain a key.

---

## Quick Reference

| Service | Used by | Required? | Cost | Link |
|---------|---------|-----------|------|------|
| **TMDB** | scraper.py, metadata generator | ✅ Yes (movies) | Free | [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) |
| **TVDB v4** | scraper.py, metadata generator | ✅ Yes (TV) | Free | [thetvdb.com/api-information](https://thetvdb.com/api-information) |
| **FanArt.tv** | metadata generator | ⚠ Recommended | Free | [fanart.tv/get-an-api-key](https://fanart.tv/get-an-api-key/) |
| **Plex Token** | metadata generator | ⚠ For auto-refresh | Free | [See below](#plex-token) |
| **OpenSubtitles** | metadata generator (subtitles) | ⚠ If using subtitles | Free (5/day); 40/day with account | [opensubtitles.com/consumers](https://www.opensubtitles.com/consumers) |
| **Subdl** | metadata generator (subtitle fallback) | ❌ Optional | Free | [subdl.com](https://subdl.com) |
| **Apple MusicKit** | extended script (music) | ❌ Optional | $99/yr Apple Developer | [developer.apple.com/account](https://developer.apple.com/account) |
| **iTunes Search API** | extended script (music) | ✅ Auto (no key needed) | Free | No registration |
| **MusicBrainz** | extended script (music) | ✅ Auto (no key needed) | Free | No key — just set contact email |

---

## TMDB — The Movie Database

**Used for:** Movie metadata (title, year, plot, rating, runtime, genres, cast, director, IMDb ID, poster art, backdrop art)

**Required for:** `scraper.py --media-type movies`, both metadata generator scripts when processing movies

### How to get your TMDB API key

1. Go to [themoviedb.org](https://www.themoviedb.org) and click **Join TMDB** (top right)
2. Fill in your name, email, and password — then verify your email
3. After verifying, go to your account Settings: click your avatar → **Settings**
4. In the left sidebar, click **API**
5. Under "Request an API Key", click the link for **Developer**
6. Fill in the form:
   - **Type of Use:** Personal
   - **Application Name:** Plex NFO Creator (or any name)
   - **Application URL:** `http://localhost` (acceptable for personal use)
   - **Application Summary:** A brief description (e.g. "Generate NFO sidecar files for my local Plex library")
7. Accept the terms and click **Submit**
8. Your key appears immediately on the API page under **API Key (v3 auth)**

> The v3 key is a 32-character hex string, e.g. `a1b2c3d4e5f6789012345678901234ab`

**Free tier limits:** 50 requests per second — far more than needed for library processing.

### Where to put it

`scraper.py` — edit lines 25–26:
```python
TMDB_API_KEY = "your_key_here"
```

Metadata generator config (`plex-metadata-generator.conf`):
```json
"tmdb": { "api_key": "your_key_here" }
```

---

## TVDB — TheTVDB

**Used for:** TV show metadata (title, year, overview, status, network, genres), season artwork, episode details (title, air date, overview, director, writers, guest stars), TVDB episode IDs, IMDb cross-links

**Required for:** `scraper.py --media-type tvshows`, both metadata generator scripts when processing TV shows

### How to get your TVDB API key

1. Go to [thetvdb.com](https://www.thetvdb.com) and click **Register** (top right)
2. Create an account with your email and a password — verify your email
3. After logging in, go to [thetvdb.com/api-information](https://thetvdb.com/api-information)
4. Scroll to the **API Keys** section and click **Generate API Key**
5. Give your key a name (e.g. "Plex NFO Creator") and click **Generate**
6. Copy the key — it looks like `a1313d27-4e2f-4d61-9ab8-cf7a22d53fbb` (UUID format)

> **Important:** TVDB keys expire if unused. If you get 401 errors after a long gap, generate a new key from the same page.

**Free tier limits:** No stated limit for personal use.

### Where to put it

`scraper.py`:
```python
TVDB_API_KEY = "your_key_here"
```

Metadata generator config:
```json
"tvdb": { "api_key": "your_key_here" }
```

---

## FanArt.tv

**Used for:** High-quality supplemental artwork that TMDB and TVDB don't provide:

| File | What FanArt.tv provides |
|------|------------------------|
| `clearart.png` | Title with transparent background (no poster; just text/logo art) |
| `disc.png` | Blu-ray or DVD disc face artwork |
| `logo.png` | Studio or franchise logo on transparent background |
| `landscape.jpg` | Wide-format TV show landscape thumbnail |

**Required for:** metadata generator only; clearart/disc/logo are silently skipped if this key is absent (a warning is logged; all other artwork downloads still work)

### How to get your FanArt.tv API key

1. Go to [fanart.tv](https://fanart.tv) and click **Sign Up** (top right)
2. Create a free account with email and password
3. After logging in, go to [fanart.tv/get-an-api-key](https://fanart.tv/get-an-api-key/)
4. Under **Personal API Key**, click **Generate API Key**
5. Copy the key (32-character hex string)

> The Personal API key has no rate limit for personal/private use. A Project API key is available for public applications.

**Free tier limits:** Unlimited for personal use.

### Where to put it

Metadata generator config:
```json
"fanart_tv": { "api_key": "your_key_here" }
```

---

## Plex Token

**Used for:** Triggering an automatic Plex library refresh after the metadata generator finishes writing NFO and artwork files. Without a token, metadata is still generated correctly — you just need to trigger a Plex refresh manually.

**Required for:** metadata generator (optional — skip if you prefer to refresh Plex manually)

### How to get your Plex Token

**Method 1 — from Plex Web (easiest):**
1. Open [app.plex.tv](https://app.plex.tv) or `http://localhost:32400/web` in your browser
2. Open Developer Tools (F12 or Cmd+Option+I on Mac)
3. Go to the **Network** tab and reload the page
4. Click any request to `localhost:32400`
5. In the **Request Headers**, look for `X-Plex-Token` — copy its value

**Method 2 — from terminal (macOS/Linux):**
```bash
curl -s "http://localhost:32400/web/" | grep -oE 'authToken=[a-zA-Z0-9_-]+' | head -1 | cut -d= -f2
```

**Method 3 — from Plex preferences file (macOS):**
```bash
defaults read com.plexapp.plexmediaserver PlexOnlineToken 2>/dev/null
```

**Method 4 — Plex account page:**
1. Go to [plex.tv/claim](https://www.plex.tv/claim/)
2. Sign in to your Plex account
3. The claim token is shown — note this is a temporary token; for a permanent server token use Method 1 or 2 above

### Finding your Plex library key

The library key is the number shown in the URL when you click on a library in Plex Web, e.g. `http://localhost:32400/web/#!/server/.../com.plexapp.plugins.library?source=2` — the number after `source=` is your library key.

Or via API:
```bash
curl -s "http://localhost:32400/library/sections" \
  -H "X-Plex-Token: YOUR_TOKEN" | grep -E "key|title"
```

### Where to put it

```json
"plex": {
  "url": "http://localhost:32400",
  "token": "your_plex_token_here",
  "tv_library_key": "1",
  "movies_library_key": "2",
  "music_library_key": "3"
}
```

---

## OpenSubtitles

**Used for:** Downloading subtitle files (`.srt`) for movies and TV episodes. Primary subtitle provider.

**Required for:** metadata generator subtitle feature (`subtitles.enabled: true`)

### Download limits by account type

| Account type | Downloads/day |
|---|---|
| API key only (no account) | 5 |
| Free account with username + password | 40 |

### How to get your OpenSubtitles API key

1. Go to [opensubtitles.com](https://www.opensubtitles.com) and click **Register**
2. Create a free account — no credit card required
3. After logging in, go to [opensubtitles.com/consumers](https://www.opensubtitles.com/consumers)
4. Click **Add Consumer**
5. Enter a name for your app (e.g. "Plex NFO Creator") and click **Create**
6. Copy the API key shown — it's a long alphanumeric string

### Where to put it

```json
"subtitles": {
  "enabled": true,
  "language": "auto",
  "opensubtitles": {
    "api_key": "your_key_here",
    "username": "your_opensubtitles_username",
    "password": "your_opensubtitles_password"
  }
}
```

`username` and `password` are optional (anonymous mode gives 5/day). With credentials you get 40/day.

---

## Subdl

**Used for:** Subtitle download fallback when OpenSubtitles is unavailable or quota is exhausted. No login required.

**Required for:** Nothing — optional fallback; works with no configuration at all

### How to get an optional Subdl API key

1. Go to [subdl.com](https://subdl.com) and register (free)
2. After logging in, go to your profile settings
3. Copy your API key from the API section

An API key is **not required** — Subdl works without one (lower rate limits). Add it only if you hit rate limits.

### Where to put it

```json
"subtitles": {
  "subdl": {
    "api_key": "your_key_or_leave_empty"
  }
}
```

---

## iTunes Search API

**Used for:** Music metadata (artist name, album title, release year, genre, track count, label, album art at 3000×3000). Primary music metadata source in the extended script.

**Required for:** Extended script music processing

### No key required

The iTunes Search API is completely free and requires no registration, no API key, and no account. It works out of the box — the extended script uses it automatically.

**Endpoint:** `https://itunes.apple.com/search?term=...&media=music&entity=album`

**Rate limits:** Apple does not publish official limits. For library processing (not real-time), no rate limit issues are expected in practice. The extended script adds a small delay between requests as a courtesy.

---

## Apple MusicKit (Optional)

**Used for:** Enhanced music metadata — higher-resolution artist images, ISRC codes, composer credits, content advisory (explicit flag), richer catalog data. This is an **optional upgrade** over the always-free iTunes Search API.

**Required for:** Nothing — the extended script runs fully without this. iTunes Search API handles all music lookups automatically. Add MusicKit only if you want the enriched metadata.

**Cost:** Requires an Apple Developer Program membership at **$99/year USD**.

### What MusicKit adds over iTunes Search API

| Feature | iTunes Search API | Apple MusicKit |
|---------|-----------------|---------------|
| Album art (max res) | 3000×3000 (URL trick) | Native 3000×3000+ |
| Artist images | Limited | Full catalog |
| ISRC codes | ❌ | ✅ |
| Composer credits | ❌ | ✅ |
| Content advisory | ❌ | ✅ |
| Auth required | ❌ None | ✅ ES256 JWT |

### How to get Apple MusicKit credentials

1. Enroll in the [Apple Developer Program](https://developer.apple.com/programs/) ($99/yr)
2. Sign in to [developer.apple.com/account](https://developer.apple.com/account)
3. Go to **Certificates, Identifiers & Profiles** → **Keys**
4. Click **+** to create a new key
5. Give it a name (e.g. "Plex MusicKit"), check **MusicKit**, click **Continue → Register**
6. Click **Download** — save the `.p8` file somewhere permanent (you can only download it once)
7. Note the **Key ID** shown on the key detail page (10-character string, e.g. `AB12CD34EF`)
8. Note your **Team ID** — shown in the top-right of the developer portal (10-character string, e.g. `A1B2C3D4E5`)

### Required dependency

```bash
pip3 install cryptography
```

This is needed for ES256 JWT signing (how MusicKit authentication works locally, without a server).

### Where to put it

```json
"apple_musickit": {
  "enabled": true,
  "team_id": "A1B2C3D4E5",
  "key_id": "AB12CD34EF",
  "private_key_path": "/path/to/AuthKey_AB12CD34EF.p8",
  "storefront": "us"
}
```

`storefront` is the iTunes Store country code for your region (`us`, `gb`, `ca`, `au`, `de`, `fr`, `jp`, etc.).

---

## MusicBrainz

**Used for:** Music metadata fallback — artist, album, track details, MBIDs (MusicBrainz IDs), ISRCs, and label information. Used when iTunes Search API / Apple MusicKit don't return results.

**Required for:** Nothing — MusicBrainz requires no API key. It only requires you to set a contact email in the `User-Agent` header (MusicBrainz ToS requirement).

### No key required

MusicBrainz's REST API (`https://musicbrainz.org/ws/2/`) is completely free with no registration. You only need to identify your application in the User-Agent header:

```json
"musicbrainz_contact": "your@email.com"
```

This email appears in your requests' `User-Agent` header as `PlexMetadataGenerator/2.x (your@email.com)`. MusicBrainz uses this to contact you if your usage causes problems — it is not shared publicly.

### Rate limits

MusicBrainz enforces **1 request per second** for the REST API. The extended script automatically enforces a 1.1-second minimum interval and retries with exponential backoff on 503 responses.

### Optional: Local MusicBrainz database (no rate limits)

For large music libraries, you can download the MusicBrainz database for fully local, instant, rate-limit-free lookups:

**Option A — PostgreSQL dump** (~30 GB; fastest lookups):
- Download from [data.metabrainz.org/pub/musicbrainz/data/fullexport/](https://data.metabrainz.org/pub/musicbrainz/data/fullexport/)
- Import with: `setup-musicbrainz-db.sh` (included in the repo)
- Requires PostgreSQL and `pip3 install psycopg2-binary`

**Option B — JSON dump** (~80 GB; no database required):
- Download from [data.metabrainz.org/pub/musicbrainz/data/json-dumps/](https://data.metabrainz.org/pub/musicbrainz/data/json-dumps/)
- Extract to any directory; set `musicbrainz_json_dump_dir` in config
- No additional dependencies

Config for local database:
```json
"musicbrainz_db": {
  "host": "localhost",
  "port": 5432,
  "dbname": "musicbrainz",
  "user": "musicbrainz",
  "password": "",
  "schema": "musicbrainz",
  "skip": false
}
```

Config for JSON dump:
```json
"musicbrainz_json_dump_dir": "/path/to/json-dump"
```

---

## Complete Config Example

Full `plex-metadata-generator-extended.conf` with all keys filled in:

```json
{
  "movies_library_roots": ["/Volumes/Movies"],
  "tv_library_roots":     ["/Volumes/TV"],
  "music_library_roots":  ["/Volumes/Music"],

  "plex": {
    "url": "http://localhost:32400",
    "token": "YOUR_PLEX_TOKEN",
    "movies_library_key": "1",
    "tv_library_key":     "2",
    "music_library_key":  "3"
  },

  "tmdb":      { "api_key": "YOUR_TMDB_KEY",      "enabled": true },
  "tvdb":      { "api_key": "YOUR_TVDB_KEY",      "enabled": true },
  "fanart_tv": { "api_key": "YOUR_FANART_TV_KEY"                  },

  "apple_musickit": {
    "enabled": false,
    "team_id": "YOUR_TEAM_ID",
    "key_id":  "YOUR_KEY_ID",
    "private_key_path": "/path/to/AuthKey.p8",
    "storefront": "us"
  },

  "musicbrainz_contact": "your@email.com",

  "subtitles": {
    "enabled": true,
    "language": "auto",
    "sidecar": true,
    "embed_in_file": true,
    "opensubtitles": {
      "api_key":  "YOUR_OPENSUBTITLES_KEY",
      "username": "YOUR_OPENSUBTITLES_USERNAME",
      "password": "YOUR_OPENSUBTITLES_PASSWORD"
    },
    "subdl": { "api_key": "" }
  }
}
```

---

## Key Validation

The metadata generator validates all configured API keys at startup with a **15-day cached result**. If a key has expired or been revoked since the last check, a blocking dialog appears and the job pauses until a valid key is entered.

You can force immediate revalidation of all keys:
```bash
python3 metadata-generator/health-check.py --revalidate
```

---

*See also: [Metadata Generator Reference](metadata-generator-Reference) · [Extended Script Reference](plex_metadata_generator_extended-Reference) · [Installation](Installation)*
