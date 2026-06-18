# Strategy-1 spikes (Sprint 0)

## NFO pretty-print (`NFOPrettyXML`)

- **Approach:** `XMLDocument` with `.nodePrettyPrint`
- **Verdict:** **GO** — handles fixture `movie_minimal.nfo`; sufficient for scraper output normalization
- **Risk:** exotic entities / non-UTF8; mitigated by UTF-8 enforcement at write time

## ffmpeg bundling

- **Approach:** `Resources/ffmpeg/ffmpeg` universal binary; `BundleDataManifest.dataRevision.ffmpeg` bumps on payload change
- **Verdict:** **GO** — `FFmpegLocator` resolves bundle → dev path → `which ffmpeg`
- **Risk:** binary size; document separate data revision in About

## Full Swift port of Python metadata generator

- **Verdict:** **Phased** — base scan in Swift; extended music/TVDB flows remain parity-tested against fixtures through Phase 1
