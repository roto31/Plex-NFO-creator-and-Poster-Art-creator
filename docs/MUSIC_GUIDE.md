# Plex Metadata Generator - Music Support Guide

## Overview

The extended metadata generator now supports **both TV shows and music** with automatic library structure detection and metadata from multiple sources:

- **TV Shows**: TVDb, TMDb, Tunarr (unchanged from v1.0)
- **Music**: Spotify, MusicBrainz (NEW in v1.1)

---

## Music Library Structure

The system expects music to be organized as:

```
/mnt/media/Music/
├── Artist Name 1/
│   ├── artist.nfo                    ← Artist metadata
│   ├── artist.jpg                    ← Artist image
│   ├── Album Name 1/
│   │   ├── album.nfo                 ← Album metadata
│   │   ├── folder.jpg                ← Album cover art
│   │   ├── 01 - Track Title.mp3
│   │   ├── 01 - Track Title.nfo      ← Track metadata (optional)
│   │   ├── 02 - Another Song.mp3
│   │   └── 02 - Another Song.nfo
│   └── Album Name 2/
│       └── (same structure)
└── Artist Name 2/
    └── (same structure)
```

### Alternative Formats Supported

The system automatically handles various track naming conventions:

```
# Standard (preferred)
01 - Track Title.mp3
02 - Another Song.mp3

# Alternative formats
01_Track_Title.mp3
Track Title.mp3 (track number parsed from filesystem order)
song-name.mp3
01. Track Title.mp3
```

---

## Generated NFO Files

### Artist NFO (`artist.nfo`)

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<artist>
  <name>The Beatles</name>
  <plot>Music artist: The Beatles</plot>
  <mbid>72c90f5a-aaeb-3ec4-b9a3-32ac26b58fe9</mbid>
  <spotifyid>3WrFJ7ztbogyGnTv1OqLmh</spotifyid>
  <genre>Rock</genre>
  <genre>Pop</genre>
  <member>John Lennon</member>
  <member>Paul McCartney</member>
  <image>https://i.scdn.co/image/...</image>
</artist>
```

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
  <label>Apple Records</label>
  <tracks>17</tracks>
  <mbid>9a66fb6e-86ff-4282-bb7f-dc99d619ec91</mbid>
  <spotifyid>0VjIjW4GlUZAMYd2vXMwbU</spotifyid>
  <genre>Rock</genre>
  <cover>https://i.scdn.co/image/...</cover>
</album>
```

### Track NFO (`track.nfo`)

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<track>
  <title>Here Comes the Sun</title>
  <artist>The Beatles</artist>
  <album>Abbey Road</album>
  <tracknumber>3</tracknumber>
  <rating>0</rating>
  <duration>185</duration>
  <genre>Rock</genre>
  <mbid>e1a3c9f4-6be5-4b6e-b42c-9edac27c6f9a</mbid>
  <isrc>GBUM71000111</isrc>
</track>
```

---

## Setting Up Music Metadata Sources

### 1. Spotify Setup (Recommended)

Best for: Album art, popularity metrics, comprehensive coverage

**Steps:**

1. Go to https://developer.spotify.com/dashboard
2. Create an app (free account required)
3. Accept terms and create app
4. Copy **Client ID** and **Client Secret**
5. Add to configuration:

```json
{
  "spotify": {
    "client_id": "your_client_id_here",
    "client_secret": "your_client_secret_here",
    "enabled": true
  }
}
```

**What you get:**
- Album cover art (high-resolution)
- Genre information
- Artist profiles with images
- Release dates
- Track counts
- Popularity data

**Limitations:**
- Client Credentials flow (no user-specific data)
- Rate limit: 40 requests/second
- High-resolution images cached locally

---

### 2. MusicBrainz Setup (Fallback)

Best for: Comprehensive metadata, ISRCs, multiple release dates

**Steps:**

1. Go to https://musicbrainz.org/
2. Create free account
3. Your API access is automatic (no key needed for basic use)
4. Add to configuration:

```json
{
  "musicbrainz": {
    "contact": "your_email@example.com",
    "enabled": true
  }
}
```

Replace `your_email@example.com` with your contact email (MusicBrainz requires this for API access).

**What you get:**
- Comprehensive release information
- MBID (MusicBrainz identifiers)
- ISRC codes (international recording codes)
- Artist relationships
- Record label information
- Multiple release versions (you pick primary)

**Limitations:**
- No cover art (use Spotify for that)
- Rate limit: 1 request/second (built-in delay)
- Community-maintained (occasional data gaps)

---

## Configuration for Music

### Minimal Configuration

```json
{
  "music_library_root": "/mnt/media/Music",
  
  "spotify": {
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "enabled": true
  },
  
  "plex": {
    "url": "http://localhost:32400",
    "token": "YOUR_PLEX_TOKEN",
    "music_library_key": "2"
  }
}
```

### Complete Configuration

```json
{
  "music_library_root": "/mnt/media/Music",
  "cache_dir": "/var/cache/plex-metadata",
  
  "spotify": {
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "enabled": true
  },
  
  "musicbrainz": {
    "contact": "your_email@example.com",
    "enabled": true
  },
  
  "plex": {
    "url": "http://localhost:32400",
    "token": "YOUR_PLEX_TOKEN",
    "music_library_key": "2"
  },
  
  "metadata_priority": {
    "music": ["spotify", "musicbrainz"]
  },
  
  "logging": {
    "level": "INFO",
    "file": "/var/log/plex-metadata-generator.log"
  }
}
```

---

## Running Music Metadata Generation

### Process All Media (TV + Music)

```bash
plex-metadata-generator --media-type all
```

### Process Music Only

```bash
plex-metadata-generator --media-type music
```

### Process Specific Artist

```bash
plex-metadata-generator --media-type music --item "The Beatles"
```

### Debug Mode

```bash
plex-metadata-generator --media-type music --debug
```

---

## How It Works

### Artist Processing

1. **Detect artist directory** (`/mnt/media/Music/Artist Name/`)
2. **Search metadata sources:**
   - Spotify: Search for artist by name
   - MusicBrainz: Search for artist (fallback)
3. **Generate artist.nfo** with:
   - Name, biography, genres
   - Member list (if available)
   - Image URL
   - MusicBrainz/Spotify IDs
4. **Download artist image** to `artist.jpg`
5. **Process all albums** in artist directory

### Album Processing

1. **Detect album directory** (`/mnt/media/Music/Artist/Album/`)
2. **Search metadata sources:**
   - Spotify: Search for album by title + artist
   - MusicBrainz: Search for release
3. **Generate album.nfo** with:
   - Title, artist, year, release date
   - Genre, label, track count
   - Cover art URL
   - MusicBrainz/Spotify IDs
4. **Download cover art** to `folder.jpg`
5. **Process all tracks** in album directory

### Track Processing

1. **Detect audio files** (`.mp3`, `.flac`, `.m4a`, etc.)
2. **Parse track info from filename:**
   - Extract track number (from leading digits)
   - Extract track title (from filename after number)
3. **Generate track.nfo** with:
   - Title, artist, album, track number
   - Duration, genre
   - MusicBrainz/Spotify IDs
   - ISRC code

---

## Plex Configuration for Music

### Enable Local Media Agent

1. Open Plex Web: http://localhost:32400/web/
2. Settings → Libraries → Music
3. **Agents** section:
   - Move **"Local Media Assets"** to **top** (highest priority)
4. Scroll down → **Save**

### Add Music Library

1. Settings → Libraries → **+ Add Library**
2. Choose **Music**
3. Add folder: `/mnt/media/Music`
4. Click **Add Library**
5. Wait for initial scan
6. Library will auto-refresh when metadata is generated

### Verify Metadata

1. Click any album
2. Should show:
   - Cover art (from `folder.jpg`)
   - Album details (from `album.nfo`)
   - Track listing with metadata (from track NFOs)
3. Click artist
4. Should show:
   - Artist image (from `artist.jpg`)
   - Artist biography
   - All albums

---

## Troubleshooting Music Metadata

### Album cover not showing

1. Check if `folder.jpg` exists:
```bash
ls -la /mnt/media/Music/"Artist"/"Album"/folder.jpg
```

2. Verify cover size (should be > 100x100):
```bash
identify /mnt/media/Music/"Artist"/"Album"/folder.jpg
```

3. Check Plex agent config:
   - Settings → Libraries → Music → Agents
   - "Local Media Assets" should be first

4. Manually refresh album:
   - Right-click album → **Refresh metadata**

### Artist image not showing

1. Check if `artist.jpg` exists:
```bash
ls -la /mnt/media/Music/"Artist"/artist.jpg
```

2. Verify artist NFO:
```bash
cat /mnt/media/Music/"Artist"/artist.nfo
```

3. Refresh artist:
   - Click artist → three dots → **Refresh metadata**

### Track metadata missing

1. Check if `track.nfo` exists:
```bash
ls -la /mnt/media/Music/"Artist"/"Album"/*.nfo
```

2. Verify NFO content:
```bash
cat /mnt/media/Music/"Artist"/"Album"/01\ -\ Track.nfo
```

3. Check log for errors:
```bash
grep "track" /var/log/plex-metadata-generator.log | grep ERROR
```

### Spotify connection failed

1. Verify credentials in config:
```bash
cat /etc/plex-metadata-generator.conf | grep spotify
```

2. Test API manually:
```bash
curl -X POST https://accounts.spotify.com/api/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=YOUR_ID&client_secret=YOUR_SECRET"
```

3. Check logs:
```bash
tail -f /var/log/plex-metadata-generator.log | grep Spotify
```

### MusicBrainz rate limiting

MusicBrainz has 1 request/second limit. If running into issues:

1. Check if throttling is happening:
```bash
grep "MusicBrainz" /var/log/plex-metadata-generator.log | grep -i "rate\|limit\|throttle"
```

2. Script includes automatic 1-second delay between requests
3. If still hitting limits, increase delay in config (future version)

---

## Performance Notes

### Music Library Processing

- **First run (100 albums):** 15-45 minutes
- **Subsequent runs (cached):** 5-15 minutes
- **Per artist:** ~2-5 seconds
- **Per album:** ~3-8 seconds
- **Per track:** <1 second (metadata embedded in NFO)

### Spotify Limits

- Authenticated: 40 requests/second
- Rate limiting built-in (1 sec/album = 3600 albums/hour)

### MusicBrainz Limits

- Public API: 1 request/second (automatic delay included)
- Very stable, no authentication needed

### Disk Usage

- Cover art (avg 200 KB per album): ~20 GB for 1000 albums
- NFO files: ~100 KB per 100 tracks
- Total cache: ~500 MB for large libraries

---

## Advanced: Media Type Detection

The system **automatically detects** whether a library contains TV or music:

```python
# Detection logic:
# If directory contains: .mp3, .flac, .m4a, .aac → Music
# If directory contains: .mkv, .mp4, .avi → TV
# Default: TV (if ambiguous)
```

You can override detection by specifying `--media-type` flag:

```bash
# Force music processing
plex-metadata-generator --media-type music --config /etc/plex-metadata-generator.conf

# Force TV processing  
plex-metadata-generator --media-type tv --config /etc/plex-metadata-generator.conf

# Process both (with auto-detection)
plex-metadata-generator --media-type all --config /etc/plex-metadata-generator.conf
```

---

## Supported Audio Formats

The generator recognizes and processes:

- **MP3** (.mp3)
- **FLAC** (.flac)
- **AAC** (.aac)
- **M4A** (.m4a)
- **Opus** (.opus)
- **WMA** (.wma)
- **WAV** (.wav)
- **OGG** (.ogg)

Mixed formats in same album are supported.

---

## Examples

### Example 1: Small Music Library Setup

```json
{
  "music_library_root": "/mnt/media/Music",
  
  "spotify": {
    "client_id": "abc123def456",
    "client_secret": "secret123",
    "enabled": true
  },
  
  "plex": {
    "url": "http://localhost:32400",
    "token": "plex_token_here",
    "music_library_key": "2"
  }
}
```

Run:
```bash
plex-metadata-generator --media-type music
```

### Example 2: Large Library (TV + Music)

```json
{
  "tv_library_root": "/mnt/media/TV",
  "music_library_root": "/mnt/media/Music",
  
  "spotify": {
    "client_id": "...",
    "client_secret": "...",
    "enabled": true
  },
  
  "musicbrainz": {
    "contact": "admin@example.com",
    "enabled": true
  },
  
  "tvdb": {
    "api_key": "...",
    "enabled": true
  },
  
  "tmdb": {
    "api_key": "...",
    "enabled": true
  },
  
  "plex": {
    "url": "http://localhost:32400",
    "token": "...",
    "tv_library_key": "1",
    "music_library_key": "2"
  }
}
```

Scheduled via cron:
```bash
# Process TV at 2 AM
0 2 * * * plex-metadata-generator --media-type tv

# Process music at 4 AM (after TV complete)
0 4 * * * plex-metadata-generator --media-type music
```

### Example 3: Spotify-Only Setup

```json
{
  "music_library_root": "/mnt/media/Music",
  
  "spotify": {
    "client_id": "...",
    "client_secret": "...",
    "enabled": true
  },
  
  "plex": {
    "url": "http://localhost:32400",
    "token": "...",
    "music_library_key": "2"
  }
}
```

Fast, simple, excellent cover art.

---

## Scheduling Music Generation

### Option 1: Systemd Timer (Separate from TV)

Create `/etc/systemd/system/plex-metadata-generator-music.timer`:

```ini
[Unit]
Description=Plex Metadata Generator - Music
Requires=plex-metadata-generator-music.service

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 04:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Create `/etc/systemd/system/plex-metadata-generator-music.service`:

```ini
[Unit]
Description=Plex Metadata Generator - Music Service
After=network-online.target

[Service]
Type=oneshot
User=plex
ExecStart=/usr/local/bin/plex-metadata-generator --media-type music

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable plex-metadata-generator-music.timer
sudo systemctl start plex-metadata-generator-music.timer
```

### Option 2: Cron (Simplest)

```bash
# TV at 2 AM, Music at 4 AM
0 2 * * * /usr/local/bin/plex-metadata-generator --media-type tv
0 4 * * * /usr/local/bin/plex-metadata-generator --media-type music
```

### Option 3: Docker Compose

Add service for music:

```yaml
services:
  plex-metadata-generator-music:
    build: .
    image: plex-metadata-generator:latest
    environment:
      - PLEX_URL=http://plex:32400
      - PLEX_TOKEN=${PLEX_TOKEN}
      - SPOTIFY_CLIENT_ID=${SPOTIFY_CLIENT_ID}
      - SPOTIFY_CLIENT_SECRET=${SPOTIFY_CLIENT_SECRET}
    volumes:
      - /mnt/media/Music:/mnt/media/Music:rw
      - plex-metadata-cache:/var/cache/plex-metadata
    entrypoint: >
      sh -c "
      echo 'Starting Plex Music Metadata Generator...' &&
      python3 /app/plex_metadata_generator.py 
        --media-type music 
        --config /app/plex-metadata-generator.conf &&
      sleep 86400
      "
```

---

## Limitations & Future Enhancements

### Current Limitations

- **Track-level artwork:** Individual track cover art not supported (uses album art)
- **Ratings:** No user ratings imported (MusicBrainz/Spotify don't expose these)
- **Audio file metadata:** Existing ID3 tags not read (full NFO generation only)
- **Playlists:** Not supported (Plex handles these separately)

### Planned for v1.2+

- [ ] Read existing ID3 tags as fallback
- [ ] Support for Last.fm popularity/ratings
- [ ] Discography generation (all albums per artist)
- [ ] Genre-based auto-organization
- [ ] Lyric embedding (NFO field)
- [ ] Album reviews/descriptions from AllMusic
- [ ] Compilation album special handling

---

## Support & Issues

### Run Health Check

```bash
python3 health-check.py
```

Will report:
- Config validity
- Spotify connection status
- MusicBrainz availability
- File permissions
- Disk space
- Recent errors

### Check Logs

```bash
# Spotify-related errors
grep -i spotify /var/log/plex-metadata-generator.log

# MusicBrainz-related errors
grep -i musicbrainz /var/log/plex-metadata-generator.log

# All music processing
grep -i music /var/log/plex-metadata-generator.log

# Follow in real-time
tail -f /var/log/plex-metadata-generator.log | grep -i music
```

### Common Issues

**"Could not find metadata for album..."**
- Album may not exist on Spotify/MusicBrainz
- Try alternate artist/album names
- Check for typos in folder names

**"Permission denied writing NFO"**
- Check file ownership: `ls -la /mnt/media/Music/`
- Fix: `sudo chown -R plex:plex /mnt/media/Music/`

**"Spotify authentication failed"**
- Verify credentials in config
- Check Client ID/Secret for typos
- Ensure Spotify app created at developer.spotify.com

---

## Version Info

**Version:** 1.1.0 (Music Support)  
**Added:** June 2026  
**Backward Compatible:** Yes (TV functionality unchanged)

---

**Last Updated:** June 2026
