# Changelog — Plex NFO Creator

All notable **Plex NFO Creator** release changes are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Install macOS builds from [GitHub Releases](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/releases). Application source is not published in this repository.

## Documentation

- [Docs index](docs/README.md)
- [Installation](docs/installation.md)
- [Getting started](docs/getting-started.md)
- [Build & release](docs/build-and-release.md)
- [Distribution policy](docs/distribution-policy.md)

---

## [Unreleased]

### Docs

- Public allowlist sync documentation; [distribution-policy.md](docs/distribution-policy.md), [installation.md](docs/installation.md).

---

## [0.1.0] - 2026-06-18

### Added

- **Native macOS app (M0)** — SwiftUI app with Rename, Scraper, Artwork, Metadata, and Health Check tabs; Keychain-backed API keys; `PlexNFOCore` library (macOS 14+).
- **Python CLI suite** — documented on [Wiki](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki): `scraper.py`, `extract_artwork.py`, `rename_movies.py`, `preflight.py`, and Metadata Generator scripts.
- GitHub Wiki with installation, troubleshooting, NFO format reference, and native app documentation.

### Build/CI

- Signed, notarized macOS DMG (`Plex NFO Creator-<version>-macos.dmg`) published via private-repo tag workflow.
