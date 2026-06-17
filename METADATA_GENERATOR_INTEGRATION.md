# Plex Metadata Generator — Integration Guide

This repository includes a second, complementary tool: the **Plex Metadata Generator**. It works alongside the three core scripts (`scraper.py`, `extract_artwork.py`, `rename_movies.py`) to provide automated, scheduled, ongoing metadata management.

---

## At a Glance

| | NFO Creator (this repo) | Metadata Generator |
|--|------------------------|-------------------|
| **Purpose** | One-time / on-demand batch processing | Automated daily updates |
| **Trigger** | Manual (`python3 scraper.py ...`) | Scheduled (cron / systemd / Docker) |
| **TV Shows** | ✅ Full NFO + episode metadata | ✅ Full NFO + episode metadata |
| **Movies** | ✅ Full NFO | ✅ TMDB NFO + full artwork set |
| **Music** | ❌ | ✅ iTunes Search API + Apple MusicKit + MusicBrainz (extended script) |
| **Artwork extraction** | ✅ Embedded MP4 art → `poster.jpg` | ✅ Downloads full set from TMDB + FanArt.tv + TVDB |
| **Artwork files (movies)** | `poster.jpg` only | `poster.jpg` + `folder.jpg` + `backdrop.jpg` + `clearart.png` + `disc.png` + `logo.png` |
| **Artwork files (TV shows)** | `poster.jpg` only | `poster.jpg` + `banner.jpg` + `fanart.jpg` + `clearart.png` + `logo.png` + `landscape.jpg` |
| **Selective processing** | Skip if NFO exists (without `--force`) | Skip if NFO + all artwork present — zero API calls per complete item |
| **Plex refresh** | ❌ Manual | ✅ Automatic after each run |
| **Tunarr integration** | ❌ | ✅ |
| **Scheduling** | ❌ | ✅ systemd / cron / macOS LaunchAgent / Docker |
| **Health monitoring** | ❌ | ✅ `health-check.py` |
| **NFO format** | Plex-compatible XML | Plex-compatible XML (same format) |

**They write the same NFO format — no conflicts.** Use them together for maximum coverage.

---

## Recommended Workflow

### Initial Setup (use NFO Creator)

```bash
# 1. Clean folder names
python3 rename_movies.py "/path/to/Movies" --rename

# 2. Generate all NFOs — movies + TV
python3 scraper.py movies  "/path/to/Movies"
python3 scraper.py tvshows "/path/to/TV Shows"

# 3. Extract embedded artwork
python3 extract_artwork.py movies  "/path/to/Movies"  --extract
python3 extract_artwork.py tvshows "/path/to/TV Shows" --extract
```

### Ongoing Automation (add Metadata Generator)

```bash
# Install and configure
cd metadata-generator
# Edit plex-metadata-generator.conf with your API keys + paths
# Run the platform installer:
bash scheduling/install-macos.sh    # macOS LaunchAgent
bash scheduling/install-linux.sh    # Linux systemd
```

The Metadata Generator then runs daily, picking up new shows/episodes and refreshing Plex automatically.

---

## Files

```
metadata-generator/
├── plex_metadata_generator.py          ← Core script (TV shows)
├── plex_metadata_generator_extended.py ← Extended script (TV + Music)
├── plex-metadata-generator.conf        ← Configuration template (TV)
├── plex-metadata-generator-extended.conf ← Configuration template (TV + Music)
├── health-check.py                     ← System diagnostics
├── Dockerfile                          ← Docker image
├── docker-compose.yml                  ← Docker Compose setup
├── README.md                           ← Full documentation
├── INSTALL.md                          ← Detailed install guide
└── scheduling/
    ├── install-macos.sh                ← macOS LaunchAgent installer
    ├── install-linux.sh                ← Linux systemd installer
    ├── install-windows.ps1             ← Windows Task Scheduler installer
    ├── com.plexmetadata.generator.plist ← macOS LaunchAgent plist
    ├── plex-metadata-generator.service ← Linux systemd service
    ├── plex-metadata-generator.timer   ← Linux systemd timer
    ├── plex-metadata-generator-cron    ← Cron alternative
    └── plex-metadata-generator-windows.xml ← Windows Task Scheduler XML

docs/
├── INTEGRATION_GUIDE.md               ← How to use both tools together
├── WORKFLOWS_AND_DIAGRAMS.md          ← 13 Mermaid workflow diagrams
├── MUSIC_GUIDE.md                     ← Music library metadata guide
└── RELEASE_NOTES_v1.1.md             ← v1.1 changelog
```

---

## Quick Start

See [`metadata-generator/README.md`](metadata-generator/README.md) for the full 5-minute setup guide.

See [`docs/INTEGRATION_GUIDE.md`](docs/INTEGRATION_GUIDE.md) for guidance on using both tools together.
