# Build and release — Native macOS App

## Install from Releases

Download `Plex NFO Creator-<version>-macos.dmg` from [GitHub Releases](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/releases). Verify SHA-256 using `release/<tag>/checksums.sha256` in this repository after sync.

## Versioning

- Marketing version follows release tags (`vMAJOR.MINOR.PATCH`)
- Bundled data revisions are tracked in the release manifest when applicable

## Distribution channels

| Channel | Status |
|---------|--------|
| Developer ID + notarized DMG | Current — CI-published from private source repo |
| Unsigned tarball | Dev-only via `scripts/release_package_macos.sh` |
| Mac App Store | Future |

## Source

Application source is maintained in a private repository. This public repository receives **release artifacts and consumer documentation only**.
