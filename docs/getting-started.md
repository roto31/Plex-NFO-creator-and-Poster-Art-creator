# Getting started — Native macOS App

**Plex NFO Creator** (native) is a SwiftUI app for rename, NFO scraping, artwork extraction, scheduled metadata scans, and health diagnostics.

Current version: see release tag on [GitHub Releases](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/releases).

## Requirements

| Requirement | Notes |
|-------------|-------|
| macOS 14+ | Sonoma or later |
| TMDB + TVDB API keys | Stored in Keychain via Settings |
| ffmpeg (optional) | Required for Artwork tab |
| Write access to library folders | Verified before batch jobs |

## Install

1. Download `Plex NFO Creator-<version>-macos.dmg` from [Releases](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/releases)
2. Open the DMG and drag **Plex NFO Creator** to Applications
3. Launch from Applications (macOS 14+)

## First launch

1. Complete the **First Launch Wizard**
2. Enter TMDB and TVDB API keys (Keychain service `com.roto31.PlexNFOCreator`)
3. Set library roots and optional Plex server URL
4. Config is stored at `~/Library/Application Support/PlexNFOCreator/config.json`

## Daily workflow

1. **Rename** (optional) — clean folder names before scraping
2. **Scraper** — generate `.nfo` sidecars
3. **Artwork** — extract embedded posters with ffmpeg
4. **Metadata** — selective scan; enable daily schedule in Settings
5. **Health Check** — verify API keys, paths, and disk space

After bulk NFO creation, set Plex **Local Media Assets** as the primary agent and refresh libraries. See [Wiki: Plex Configuration](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Plex-Configuration).

## Logs

macOS logs: `~/Library/Logs/PlexNFOCreator/`

## Related

- [Wiki: Native macOS App home](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Native-macOS-App-Home)
- [Wiki: Troubleshooting](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Troubleshooting)
