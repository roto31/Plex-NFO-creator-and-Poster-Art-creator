# Changelog — Plex NFO Creator

All notable **Plex NFO Creator** release changes are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Install Python CLI scripts from [GitHub Releases](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/releases) (`Plex-NFO-Scripts-<version>.zip`). Script source is not published in this git repository — see [script-usage.md](docs/script-usage.md).

## Documentation

- [Docs index](docs/README.md)
- [Script usage](docs/script-usage.md)
- [Installation](docs/installation.md)
- [Build & release](docs/build-and-release.md)
- [Distribution policy](docs/distribution-policy.md)

---

## [Unreleased]

---

## [2.5.0] - 2026-06-18

### Changed

- **Public Releases scrubbed** — removed all legacy DMG/app releases (v0.1.0–v2.4.0). Releases now ship **Python CLI scripts only** as `Plex-NFO-Scripts-2.5.0.zip`.
- **Distribution model** — public git holds documentation only; runnable scripts attach to GitHub Releases. See [distribution-policy.md](docs/distribution-policy.md) and [script-usage.md](docs/script-usage.md).

### Docs

- [script-usage.md](docs/script-usage.md), updated [installation.md](docs/installation.md), [build-and-release.md](docs/build-and-release.md), [distribution-policy.md](docs/distribution-policy.md).

---

## [0.1.0] - 2026-06-18

### Added

- **Python CLI suite** — documented on [Wiki](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki): `scraper.py`, `extract_artwork.py`, `rename_movies.py`, `preflight.py`, and Metadata Generator scripts.
- GitHub Wiki with installation, troubleshooting, and NFO format reference.

### Removed (superseded by 2.5.0 policy)

- Native macOS DMG releases are no longer published on this public Releases page.
