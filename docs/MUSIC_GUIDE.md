# Plex Metadata Generator — Music Support Guide

## Overview

The extended metadata generator (`plex_metadata_generator_extended.py`) supports TV shows, movies, and music libraries. Music metadata is sourced from three providers in priority order:

| Priority | Provider | Auth required | What it provides |
|----------|----------|--------------|-----------------|
| 1 | **Local MusicBrainz** | No | Local PostgreSQL DB or JSON dump — fastest, no rate limits |
| 2 | **Apple MusicKit** | Yes (Apple Developer account, optional) | Higher-res artwork, richer artist metadata |
| 3 | **iTunes Search API** | No — always active | Album art at 3000×3000, full album/artist metadata, zero auth |
| 4 | **MusicBrainz REST** | No | MBID, ISRC, release info — rate-limited to 1 req/sec |

iTunes Search API is always active and requires no configuration. Apple MusicKit is an optional upgrade. There is no Spotify dependency — Spotify requires an active Premium subscription on the developer account and was removed in v1.1.

---

## Music Library Structure

```
/mnt/media/Music/
├── Artist Name 1/
│   ├── artist.nfo                    ← Artist metadata
│   ├── artist.jpg                    ← Artist image
│   ├── Album Name 1/
│   │   ├── album.nfo                 ← Album metadata
│   │   ├── folder.jpg                ← Album cover art (3000×3000 from iTunes)
│   │   ├── 01 - Track Title.mp3
│   │   ├── 01 - Track Title.nfo      ← Track metadata
│   │   ├── 02 - Another Song.mp3
│   │   └── 02 - Another Song.nfo
│   └── Album Name 2/
│       └── (same structure)
└── Artist Name 2/
    └── (same structure)
```

### Track naming conventions supported

```
# Standard (preferred)
01 - Track Title.mp3

# Also recognized
01_Track_Title.mp3
01. Track Title.mp3
Track Title.mp3          ← track number from filesystem order
```

---

## Generated NFO Files

### Artist NFO (`artist.nfo`)

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<artist>
  <name>The Beatles</name>
  <plot>Music artist: The Beatles</plot>
  <appleid>136975</appleid>
  <genre>Rock</genre>
  <genre>Pop</genre>
</artist>
```

`<appleid>` is the iTunes artist ID. It replaces the former `<spotifyid>` tag.

### Album NFO (`album.nfo`)

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<album>
  <title>Abbey Road</title>
  <artist>The Beatles</artist>
  <year>1969</year>
  <releasedate>1969-09-26</releasedate>
  <plot>Music album</plot>
  <rating>0</rating>
  <label>℗ 1969 Apple Records</label>
  <tracks>17</tracks>
  <appleid>401241649</appleid>
  <genre>Rock</genre>
  <cover>https://is1-ssl.mzstatic.com/image/thumb/.../3000x3000bb.jpg</cover>
</album>
```

Album art URLs are rewritten to request 3000×3000 resolution directly from Apple's CDN.

### Track NFO (`track.nfo`)

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<track>
  <title>Here Comes the Sun</title>
  <artist>The Beatles</artist>
  <album>Abbey Road</album>
  <tracknumber>7</tracknumber>
  <rating>0</rating>
  <duration>185</duration>
  <genre>Rock</genre>
</track>
```

---

## Setting Up Music Providers

### iTunes Search API (automatic — no setup)

iTunes Search API is built into the extended script and active by default. No credentials, no registration, no rate-limit concerns for typical personal library use.

- Album art delivered at **3000×3000** resolution by rewriting the Apple CDN URL size segment
- Covers artist search, album search, track listing, genre, release date, label (via copyright field), iTunes collection ID

No configuration changes needed. It just works.

### Apple MusicKit (optional)

MusicKit provides higher-resolution artist images and richer metadata for users with an Apple Developer account ($99/yr).

**First-run setup dialog:**

On first run with a music library configured, a native macOS console dialog appears:

```
╔══════════════════════════════════════════════════════════╗
║       Apple MusicKit API  (optional enhancement)        ║
╠══════════════════════════════════════════════════════════╣
║  The free iTunes Search API is already active.          ║
║  MusicKit (requires Apple Developer account, $99/yr)    ║
║  adds higher-resolution artwork and richer metadata.    ║
╚══════════════════════════════════════════════════════════╝

Do you have an Apple Developer account and want to set up MusicKit? [y/N]
```

If you answer **y**, you will be prompted for:
- **Team ID** — 10-character string from [developer.apple.com/account](https://developer.apple.com/account) → Membership
- **Key ID** — from Keys section in developer portal (create a MusicKit key type)
- **Private key path** — the `.p8` file downloaded when you created the key
- **Storefront** — iTunes Store country code (default: `us`)

The script validates credentials with a live API call before saving. Tokens are ES256 JWTs valid for 6 months (Apple's maximum). The `cryptography` package is required: `pip3 install cryptography`.

**Manual config:**

```json
{
  "apple_musickit": {
    "enabled": true,
    "team_id": "ABCDE12345",
    "key_id": "ABC1234567",
    "private_key_path": "/path/to/AuthKey_ABC1234567.p8",
    "storefront": "us",
    "skip": false
  }
}
```

Set `"skip": true` to permanently suppress the dialog without enabling MusicKit.

### MusicBrainz (fallback)

MusicBrainz is used as a fallback when iTunes/MusicKit don't return a match. The REST API is free with no key required — just a contact email in the `User-Agent` header per their terms.

The script enforces a **1.1-second minimum delay** between MusicBrainz requests and uses exponential backoff (2^n seconds) on 503 responses to respect their rate limit policy.

```json
{
  "musicbrainz": {
    "contact": "your@email.com"
  }
}
```

If you have a local MusicBrainz PostgreSQL database or JSON dump, the script queries it first (zero network calls, no rate limits).

---

## Configuration

### Minimal (iTunes only — works out of the box)

```json
{
  "music_library_root": "/mnt/media/Music",
  "plex": {
    "url": "http://localhost:32400",
    "token": "YOUR_PLEX_TOKEN",
    "music_library_key": "3"
  },
  "metadata_priority": {
    "music": ["apple_musickit", "itunes", "musicbrainz"]
  }
}
```

### Full extended config

```json
{
  "music_library_root": "/mnt/media/Music",
  "cache_dir": "/var/cache/plex-metadata",

  "apple_musickit": {
    "enabled": false,
    "team_id": "",
    "key_id": "",
    "private_key_path": "",
    "storefront": "us",
    "skip": false
  },

  "musicbrainz": {
    "contact": "your@email.com"
  },

  "plex": {
    "url": "http://localhost:32400",
    "token": "YOUR_PLEX_TOKEN",
    "music_library_key": "3"
  },

  "metadata_priority": {
    "music": ["apple_musickit", "itunes", "musicbrainz"]
  }
}
```

---

## Running Music Metadata Generation

```bash
# Music only
python3 metadata-generator/plex_metadata_generator_extended.py \
  --config /etc/plex-metadata-generator-extended.conf \
  --media-type music

# Single artist
python3 metadata-generator/plex_metadata_generator_extended.py \
  --config /etc/plex-metadata-generator-extended.conf \
  --media-type music --item "The Beatles"

# All media types
python3 metadata-generator/plex_metadata_generator_extended.py \
  --config /etc/plex-metadata-generator-extended.conf \
  --media-type all

# Force regenerate everything
python3 metadata-generator/plex_metadata_generator_extended.py \
  --config /etc/plex-metadata-generator-extended.conf \
  --media-type music --force
```

---

## How It Works

### Artist processing

1. Scan artist directory (`/Music/Artist Name/`)
2. Check skip conditions: `artist.nfo` exists AND `artist.jpg` exists → skip entirely
3. Query providers in priority order (MusicBrainz local → MusicKit → iTunes → MusicBrainz REST)
4. Write `artist.nfo` with name, genre, Apple ID
5. Download `artist.jpg` (MusicKit artist image if available, otherwise iTunes artwork)
6. Process all album subdirectories

### Album processing

1. Scan album directory (`/Music/Artist/Album/`)
2. Check skip conditions: `album.nfo` exists AND `folder.jpg` (or `cover.jpg`) exists → skip
3. Query providers for album metadata
4. Write `album.nfo` with title, artist, year, genre, label, track count, iTunes collection ID
5. Download `folder.jpg` at 3000×3000 (Apple CDN URL rewrite: `\d+x\d+bb` → `3000x3000bb`)
6. Process all audio tracks

### Track processing

1. Find audio files in album directory (`.mp3`, `.flac`, `.m4a`, `.aac`, `.ogg`, `.opus`, `.wma`, `.wav`)
2. Check skip: `{stem}.nfo` exists → skip
3. Write `{stem}.nfo` with title, artist, album, track number, duration, genre

---

## Plex Configuration for Music

1. Open Plex Web: `http://localhost:32400/web/`
2. **Settings → Libraries → Music → Edit**
3. **Agents** tab: drag **Local Media Assets** to the top
4. **Save Changes**
5. **Manage Library → Refresh All Metadata**

Plex reads `artist.nfo`, `album.nfo`, `artist.jpg`, and `folder.jpg` directly from the filesystem when Local Media Assets is the top agent.

---

## Troubleshooting

### Album cover not showing

```bash
ls -la "/Music/Artist/Album/folder.jpg"
```

- If the file is missing, run the generator with `--force` for that artist
- Verify Plex agent priority: Local Media Assets must be first
- After placing artwork, trigger: **three dots → Manage Library → Refresh All Metadata**

### Artist image not showing

```bash
ls -la "/Music/Artist/artist.jpg"
```

- Without Apple MusicKit configured, artist images come from iTunes search, which may not always return a photo. This is normal — the `artist.nfo` will still work for metadata.
- To get artist photos, configure Apple MusicKit (see setup above)

### MusicBrainz 503 / rate limit errors

The script enforces 1.1s between requests with exponential backoff. If you still see 503 floods:
- Ensure only one instance of the script is running
- Check that `_MIN_INTERVAL = 1.1` is in place in `MusicBrainzProvider._get()`

### "Could not find metadata" for an album

- Check if the album name on disk closely matches what iTunes knows
- Try running with `--item "Artist Name"` and `--debug` to see the search queries
- iTunes Search API fuzzy-matches, but very unusual/obscure albums may not be in the catalog

### Apple MusicKit token errors

- Verify the `.p8` file path is correct and readable
- Confirm the Key ID matches the key on [developer.apple.com](https://developer.apple.com)
- MusicKit tokens expire after 6 months — re-run the setup dialog or regenerate the token

---

## Log diagnostics

```bash
# iTunes provider activity
grep -i "itunes" /var/log/plex-metadata-generator.log

# MusicKit activity
grep -i "musickit" /var/log/plex-metadata-generator.log

# MusicBrainz rate limiting
grep -i "musicbrainz.*503\|wait" /var/log/plex-metadata-generator.log

# All music processing
grep -i "music" /var/log/plex-metadata-generator.log

# Follow in real time
tail -f /var/log/plex-metadata-generator.log | grep -i music
```

---

## Supported Audio Formats

`.mp3`, `.flac`, `.m4a`, `.aac`, `.ogg`, `.opus`, `.wma`, `.wav`

Mixed formats within the same album directory are supported.

---

## Performance Notes

- **Per artist:** ~1–3 seconds (iTunes Search API is fast)
- **Per album:** ~0.5–2 seconds
- **MusicBrainz fallback:** adds 1.1 sec/request (rate limit enforced)
- **Subsequent runs:** items with complete NFO + artwork are skipped with zero API calls

---

**Version:** 1.1 (iTunes + Apple MusicKit replaces Spotify)
**Last Updated:** June 2026
