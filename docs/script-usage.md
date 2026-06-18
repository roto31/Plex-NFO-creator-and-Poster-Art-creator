# Python CLI scripts — usage guide

Download **`Plex-NFO-Scripts-<version>.zip`** from [GitHub Releases](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/releases). Script source is **not** in the public git tree — only in release zip assets.

## Requirements

| Requirement | Notes |
|-------------|-------|
| Python 3.8+ | macOS, Linux, or Windows |
| TMDB + TVDB API keys | Free accounts — [Wiki: API Keys](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/API-Keys) |
| ffmpeg | For `extract_artwork.py` only |
| `requests` | For `metadata-generator/` only: `pip install requests` |

## Install

```bash
unzip Plex-NFO-Scripts-*.zip -d ~/PlexNFO-Scripts
cd ~/PlexNFO-Scripts
```

## Configure API keys

Edit `scraper.py` (lines 47–48) or use environment variables as documented on the wiki:

```python
TMDB_API_KEY = "your_tmdb_key"
TVDB_API_KEY = "your_tvdb_key"
```

## Core workflow

```bash
# 1. Optional: clean folder names
python3 rename_movies.py "/path/to/Movies"           # preview
python3 rename_movies.py "/path/to/Movies" --rename  # apply

# 2. Generate NFO sidecars
python3 scraper.py movies  "/path/to/Movies"
python3 scraper.py tvshows "/path/to/TV Shows"

# 3. Extract embedded posters
python3 extract_artwork.py movies  "/path/to/Movies"  --extract
python3 extract_artwork.py tvshows "/path/to/TV Shows" --extract
```

Each script runs **preflight checks** on first launch (Python version, keys, ffmpeg).

## Metadata Generator (automation)

See `metadata-generator/README.md` inside the zip and [Wiki: metadata generator](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/metadata-generator-Reference).

```bash
pip install requests
python3 metadata-generator/plex_metadata_generator.py --help
```

## Plex refresh

After generating NFOs, set Plex **Local Media Assets** as the primary agent and refresh libraries.  
[Wiki: Plex Configuration](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Plex-Configuration)

## Logs

| OS | Log directory |
|----|----------------|
| macOS | `~/Library/Logs/PlexNFOCreator/` |
| Linux | `~/.local/share/plex-nfo-creator/logs/` |
| Windows | `%APPDATA%\PlexNFOCreator\Logs\` |

## More documentation

- [Wiki home](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki)
- [Installation (wiki)](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Installation)
- [Troubleshooting](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Troubleshooting)
- [NFO format reference](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/NFO-Format-Reference)

## Native macOS app

The SwiftUI GUI is built and distributed separately (private build pipeline). This public repository’s **Releases** ship the **Python CLI zip** and documentation only.
