# Spike Report — Native Swift Port (M0)

**Date:** 2026-06-17  
**Verdict:** **GO** for full Swift port

## NFO parity

| Area | Python (`scraper.py`) | Swift (`NFOSerializer`) | Status |
|------|----------------------|-------------------------|--------|
| XML declaration | `<?xml version='1.0' encoding='utf-8'?>` | Same | Pass |
| Pretty indent | `minidom.toprettyxml(indent="  ")` | `XMLDocument` + `.nodePrettyPrint` | Pass |
| `uniqueid` attrs | `type`, `default` | Ported | Pass |
| Golden fixture | `Tests/Fixtures/sample-movie.nfo` | Generated output matches key fields | Pass |

**NFO verdict:** GO

## ffmpeg / artwork

| Check | Result |
|-------|--------|
| `FFmpegLocator` bundle path lookup | Implemented |
| System `which ffmpeg` fallback | Implemented |
| Bundled ffmpeg binary | Not yet shipped (`dataRevision.ffmpeg: 0`) |
| Strategy 1 extract command | Skeleton matches `extract_artwork.py` frame grab |

**ffmpeg verdict:** GO (bundle ffmpeg in Sprint 09; locator + Process wrapper proven)

## Supporting spikes

| Module | Risk | Notes |
|--------|------|-------|
| Rename rules | Low | Regex parity with `rename_movies.py` covered by unit tests |
| Keychain secrets | Low | Standard `Security` framework |
| Job runner + SwiftUI | Low | `AsyncStream` events map cleanly to progress sheet |
| TVDB/TMDB clients | Medium | URLSession + rate limiter; login flow stubbed |
| Metadata generator | Medium | Large surface; port incrementally from Python |
| LaunchAgent / `SMAppService` | Low | plist generation implemented |

## Recommendation

Proceed with phased Swift implementation per roadmap (Sprints 05–15). Python scripts remain reference until feature parity per tab.

Regenerate fixtures:

```bash
python3 scripts/export_nfo_fixtures.py
```
