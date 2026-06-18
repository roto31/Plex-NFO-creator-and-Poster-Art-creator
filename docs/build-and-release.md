# Build and release — Plex NFO Creator

## For end users

Download **`Plex NFO Creator-<version>-macos.dmg`** from [GitHub Releases](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/releases).

See [installation.md](installation.md) for mount, install, and Gatekeeper verification.

## Integrity checks

After each release sync, this repo may contain:

```
release/v0.1.0/checksums.sha256
release/v0.1.0/artifact-manifest.json
```

Compare the DMG SHA-256 before installing:

```bash
shasum -a 256 ~/Downloads/Plex*.dmg
cat release/v0.1.0/checksums.sha256
```

## Versioning

- Tags follow **`vMAJOR.MINOR.PATCH`** (e.g. `v0.1.0`)
- Release notes: [CHANGELOG.md](../CHANGELOG.md)

## Distribution channels

| Channel | Status |
|---------|--------|
| **Developer ID + notarized DMG** | Current — published from private CI on tag push |
| Signed native app only | No script source on this public repo |
| Mac App Store | Not offered |

## Source code

Application source is maintained in a **private** repository and is not published here. This repository receives:

1. Allowlisted documentation (`docs/`, README, CHANGELOG)
2. Release checksum metadata
3. GitHub Release binaries (DMG)

See [distribution-policy.md](distribution-policy.md).

## Maintainer note

Signing, notarization, and publish automation are documented in the **private** operator guide (not shipped on public `main`). Public consumers only need this page, [installation.md](installation.md), and Releases.
