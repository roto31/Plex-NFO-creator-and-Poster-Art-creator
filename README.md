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

See [Getting Started](docs/getting-started.md), [Installation](docs/installation.md), and the [Native macOS App wiki](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Native-macOS-App-Home).

## Python CLI

**Script source is not published** in this repository. Plain `.py` files in a public git repo can always be copied; the supported model is documentation plus signed release binaries only.

| Need | Where |
|------|--------|
| How the CLI works | [GitHub Wiki](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki) |
| Runnable macOS GUI | [GitHub Releases](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/releases) (signed DMG) |
| Distribution policy | [docs/distribution-policy.md](docs/distribution-policy.md) |

Future CLI builds (if offered) would ship as **compiled release artifacts**, not readable source in git.

## Requirements (native app)

| Requirement | Notes |
|-------------|-------|
| macOS | 14 (Sonoma) or later |
| API keys | Free TMDB and TVDB accounts |
| ffmpeg | Optional; required for Artwork tab |
| Library access | Write access to media folders |

## License

See repository license file. Third-party API use (TMDB, TVDB, etc.) is subject to each provider's terms.
