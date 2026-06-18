# Distribution policy — public vs private

## Public repository (`Plex-NFO-creator-and-Poster-Art-creator`)

This repository contains **only**:

- Consumer documentation (`README.md`, `docs/`, `CHANGELOG.md`)
- Release checksum metadata under `release/<tag>/`
- **GitHub Releases** binaries (signed macOS DMG for the native app)
- [GitHub Wiki](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki) (operator reference; no proprietary source)

**No application source code** (Swift, Python, or scripts) is published here.

## Private repository (`Plex-NFO-Artwork-Creator`)

All source code, CI signing secrets, sprint plans, and development history live in the private repo.

## Native macOS app

Install from [GitHub Releases](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/releases) — download the signed DMG. Source is not available.

## Python CLI scripts

The Python CLI suite is **not distributed as source** on the public repository.

| Need | Option |
|------|--------|
| GUI on macOS | Native app DMG (Releases) |
| How scripts behave | [GitHub Wiki](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki) |
| Runnable Python source | **Not published** — plain `.py` files cannot be hidden if committed to a public repo |

If CLI binaries are offered in the future, they would ship as **compiled release artifacts** (e.g. PyInstaller zip on Releases), not as readable source in git.

## Why source is not on the public repo

Plain-text Python and Swift in a public git repository can always be copied. The supported model is: **docs + signed binaries on public**, **full source on private**.
