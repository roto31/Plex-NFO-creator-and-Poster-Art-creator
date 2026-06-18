# Plex NFO Creator — Python CLI

**Plex NFO Creator** generates Plex-compatible `.nfo` metadata sidecars and extracts embedded poster artwork from your local media library.

## Download scripts

Install from [GitHub Releases](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/releases):

1. Download **`Plex-NFO-Scripts-<version>.zip`**
2. Unzip anywhere on your machine
3. Read **`SCRIPT_USAGE.md`** inside the zip (also mirrored at [docs/script-usage.md](docs/script-usage.md))

> **Script source is not in this git repository.** Releases attach the zip; the repo holds **documentation only**.

## Quick start

```bash
unzip Plex-NFO-Scripts-*.zip -d ~/PlexNFO-Scripts && cd ~/PlexNFO-Scripts
# Edit scraper.py API keys, then:
python3 scraper.py movies "/path/to/Movies"
```

Full guide: [docs/script-usage.md](docs/script-usage.md)

## Documentation

| Resource | Link |
|----------|------|
| **Script usage** | [docs/script-usage.md](docs/script-usage.md) |
| **GitHub Wiki** | [wiki home](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki) |
| **Installation (wiki)** | [Installation](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Installation) |
| **Troubleshooting** | [Troubleshooting](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Troubleshooting) |
| **Distribution policy** | [docs/distribution-policy.md](docs/distribution-policy.md) |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Requirements

Python 3.8+, TMDB/TVDB API keys, ffmpeg (artwork only), `pip install requests` (metadata-generator only).

## Native macOS app

The SwiftUI GUI is built from a **private source repository** and is not published on this Releases page. This public project distributes the **Python CLI scripts** and documentation.
