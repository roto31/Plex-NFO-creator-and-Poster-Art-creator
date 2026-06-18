# Plex NFO Creator & Poster Art Extractor

**Plex NFO Creator** generates Plex-compatible `.nfo` metadata sidecars and extracts embedded poster artwork from your local media library. Use the **native macOS app** for a tabbed GUI, or the **Python CLI** for headless and cross-platform batch jobs.

## Download (macOS app)

Install from [GitHub Releases](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/releases):

1. Download `Plex NFO Creator-<version>-macos.dmg` for your tagged version
2. Open the DMG and drag **Plex NFO Creator** to Applications
3. On first launch, complete the wizard and save TMDB/TVDB keys to Keychain

Verify the SHA-256 checksum in `release/<tag>/checksums.sha256` before installing.

> **Source code** is maintained in a private repository. This public repo ships **documentation and release binaries only**.

## Quick start (native app)

1. Launch **Plex NFO Creator**
2. Enter **TMDB** and **TVDB** API keys in the first-launch wizard (stored in Keychain)
3. Set library roots for Movies and TV Shows
4. Use **Rename** → **Scraper** → **Artwork** → **Metadata** → **Health Check** as needed

See [Getting Started](docs/getting-started.md) and the [Native macOS App wiki](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Native-macOS-App-Home).

## Python CLI (Wiki)

The Python scripts remain documented on the [GitHub Wiki](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki) for operators who prefer CLI or non-macOS hosts. Script source is not published here.

| Resource | Link |
|----------|------|
| **Installation** | [Wiki: Installation](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Installation) |
| **Scraper reference** | [Wiki: scraper.py](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/scraper.py-Reference) |
| **Troubleshooting** | [Wiki: Troubleshooting](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Troubleshooting) |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Requirements (native app)

| Requirement | Notes |
|-------------|-------|
| macOS | 14 (Sonoma) or later |
| API keys | Free TMDB and TVDB accounts |
| ffmpeg | Optional; required for Artwork tab |
| Library access | Write access to media folders |

## License

See repository license file. Third-party API use (TMDB, TVDB, etc.) is subject to each provider's terms.
