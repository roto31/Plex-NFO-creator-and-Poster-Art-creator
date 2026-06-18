# Build and release — Plex NFO Creator (Python CLI)

## For end users

Download **`Plex-NFO-Scripts-<version>.zip`** from [GitHub Releases](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/releases).

See [installation.md](installation.md) and [script-usage.md](script-usage.md) for setup and commands.

Script source is **not** in this git repository — only attached as release zip assets.

## Integrity checks

After each release sync, this repo may contain:

```
release/v2.5.0/checksums.sha256
release/v2.5.0/artifact-manifest.json
```

Compare the zip SHA-256 before extracting:

```bash
shasum -a 256 ~/Downloads/Plex-NFO-Scripts-*.zip
cat release/v2.5.0/checksums.sha256
```

## Versioning

- Tags follow **`vMAJOR.MINOR.PATCH`** (e.g. `v2.5.0`)
- Release notes: [CHANGELOG.md](../CHANGELOG.md)

## Distribution channels

| Channel | Status |
|---------|--------|
| **Python scripts zip** | Current — published from private CI on `v*` tag push |
| Native macOS `.app` / DMG | Private build only (`app-v*` tags); not on this Releases page |
| Mac App Store | Not offered |

## Source code

Application and script source are maintained in a **private** repository. This public repository receives:

1. Allowlisted documentation (`docs/`, README, CHANGELOG)
2. Release checksum metadata
3. GitHub Release zip assets (Python CLI scripts only)

See [distribution-policy.md](distribution-policy.md).

## Maintainer note

Packaging and publish automation run in the **private** repo (`scripts-public-release.yml` on `v*` tags). Public consumers only need this page, [script-usage.md](script-usage.md), and Releases.
