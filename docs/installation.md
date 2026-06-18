# Installation — Plex NFO Creator (macOS)

Install the **native macOS app** from GitHub Releases. This public repository does **not** contain application source code.

## Download

1. Open [GitHub Releases](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/releases)
2. Download **`Plex NFO Creator-<version>-macos.dmg`** (or similarly named DMG for your version)
3. Optional: verify SHA-256 using `release/<tag>/checksums.sha256` in this repo after sync

## Install

1. Double-click the DMG to mount it
2. Drag **Plex NFO Creator** to **Applications**
3. Eject the DMG
4. Launch from Applications

First launch opens the **setup wizard** for TMDB and TVDB API keys (stored in macOS Keychain).

## Requirements

| Requirement | Notes |
|-------------|-------|
| macOS 14+ | Sonoma or later |
| TMDB + TVDB API keys | Free accounts — see [Wiki: API Keys](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/API-Keys) |
| ffmpeg | Optional; required for Artwork extraction |
| Library folder access | Write access to your media libraries |

## Verify the download (optional)

After mounting the DMG:

```bash
spctl -a -vvv -t install "/Volumes/Plex NFO Creator/Plex NFO Creator.app"
```

A notarized build shows `accepted` and `source=Notarized Developer ID`.

## Python CLI scripts

**Script source is not published in this repository.** For how the Python tools work (scraper, artwork extraction, metadata generator), see the [GitHub Wiki](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki).

For the supported distribution model, see [distribution-policy.md](distribution-policy.md).

## More help

- [Getting started](getting-started.md)
- [Build & release info](build-and-release.md)
- [Wiki: Troubleshooting](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Troubleshooting)
- [Native macOS App wiki hub](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/Native-macOS-App-Home)
