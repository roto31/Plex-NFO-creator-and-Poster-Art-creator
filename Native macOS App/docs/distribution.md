# Distribution — Plex NFO Creator (macOS)

## Channels

| Channel | Signing | Notes |
|---------|---------|-------|
| **Developer ID** (recommended) | Apple Developer ID Application | Notarized `.dmg` or `.zip`; ffmpeg bundled; full filesystem access with user-granted folders |
| **Mac App Store** | Apple Distribution + sandbox | Requires sandbox entitlements; library access via security-scoped bookmarks; ffmpeg may need JIT/hardening review |

## Developer ID (primary target)

1. Archive with `swift build -c release` or Xcode **Archive**.
2. Sign with `codesign --force --options runtime --sign "Developer ID Application: …"`.
3. Notarize via `notarytool submit` + staple.
4. Ship unsigned helper scripts are **not** required; the app embeds Swift logic.

### Notarization scope (M0 foundation)

- Sign the `PlexNFOCreator` executable and any bundled `ffmpeg` binary.
- Hardened runtime enabled.
- No privileged helpers in 0.1.0.

## Mac App Store (future)

- Enable App Sandbox.
- Store API keys only in Keychain (already implemented).
- Use security-scoped bookmarks for library roots.
- Metadata scheduled jobs: prefer `SMAppService` LaunchAgent (macOS 14+) over unsigned shell installers.

## ffmpeg bundling

- Track revision in `Resources/BundleDataManifest.json` (`dataRevision.ffmpeg`).
- Any ffmpeg binary update ⇒ PATCH SemVer bump + manifest revision increment.

## CI

- Build and test on `macos-latest` with `swift build` and `swift test`.
- Release workflow (future): attach notarized artifact to GitHub Release matching `VERSION`.
