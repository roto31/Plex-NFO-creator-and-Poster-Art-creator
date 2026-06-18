# Distribution policy — public vs private

## Public repository (`Plex-NFO-creator-and-Poster-Art-creator`)

### Git tree (this repo)

**Only documentation** — no `.py`, `.swift`, or script source in git:

- `README.md`, `CHANGELOG.md`, `docs/`
- `release/<tag>/` checksum metadata

### GitHub Releases

**Only Python CLI script packages:**

- Asset: **`Plex-NFO-Scripts-<version>.zip`**
- Contains: `scraper.py`, `extract_artwork.py`, `rename_movies.py`, `preflight.py`, `metadata-generator/`, `SCRIPT_USAGE.md`
- Usage docs: [script-usage.md](script-usage.md) and the [GitHub Wiki](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki)

Scripts are **not** committed to public git (prevents drive-by cloning from the default branch). They are attached as **release zip assets** only.

### Not on public Releases

- Native macOS `.app` / DMG (private build pipeline only)
- Application Swift source

## Private repository (`Plex-NFO-Artwork-Creator`)

All source code, native app builds, signing secrets, and CI.

## Why scripts ship as zip, not git source

Publishing `.py` files on public `main` allows one-click repo cloning of all script source. Release zips deliver runnable scripts to users while keeping the default branch docs-only.

## Native macOS app

Built and signed from the private repo. Not attached to this public Releases page.
