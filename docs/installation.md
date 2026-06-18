# Installation — Python CLI scripts

## Download

1. Open [GitHub Releases](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/releases)
2. Download **`Plex-NFO-Scripts-<version>.zip`**
3. Unzip to a folder of your choice

Script source is **not** in the public git repository — only in release zip assets.

## Setup

```bash
unzip Plex-NFO-Scripts-*.zip -d ~/PlexNFO-Scripts
cd ~/PlexNFO-Scripts
```

Read **`SCRIPT_USAGE.md`** inside the zip, or [docs/script-usage.md](script-usage.md) in this repo.

## Requirements

| Requirement | Notes |
|-------------|-------|
| Python 3.8+ | macOS, Linux, or Windows |
| TMDB + TVDB keys | [Wiki: API Keys](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/API-Keys) |
| ffmpeg | Artwork extraction only |
| `requests` | Metadata Generator: `pip install requests` |

## First run

```bash
python3 scraper.py movies "/path/to/Movies"
```

Preflight checks run automatically (Python version, API keys, optional ffmpeg).

## More help

- [Script usage guide](script-usage.md)
- [Wiki: Installation](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Installation)
- [Wiki: Troubleshooting](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Troubleshooting)
