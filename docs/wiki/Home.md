# Plex NFO Creator & Poster Art Extractor

## Why We Built This

### The Problem

We manage a large local media library on macOS — over 1,700 movies and 300 TV shows with nearly 20,000 episodes, stored on external drives. For years, Plex handled metadata matching automatically: point it at your folders, wait a few minutes, and your library would populate with poster art, plot summaries, cast lists, ratings, and genres pulled from The Movie Database (TMDB) and TheTVDB.

Then it stopped working.

Not catastrophically — not all at once. It was gradual. Plex's metadata agents began failing silently on large numbers of titles. Some movies would match correctly; others would either match to the wrong film entirely (a 1954 western matching to a 2018 remake, or a documentary pulling the metadata from a similarly-titled feature film), or fail to match at all and display only a gray placeholder. Re-running "Fix Incorrect Match" through the Plex UI helped on a title-by-title basis, but with thousands of items in the library, doing this manually was not a realistic option.

TV shows were even more problematic. Plex's agent would correctly identify a series but then either skip entire seasons, pull episode data in the wrong order, or fail to retrieve episode-level detail (synopsis, air date, director, guest stars) even when the show-level match was correct. Episodes numbered differently from TheTVDB's canonical ordering — especially for older shows, anthology series, and shows that aired differently internationally — would simply show up as "Unknown Episode."

### What We Tried First

Before writing a single line of code, we exhausted the standard remedies:

**1. Refreshing the library.** Plex offers "Refresh All Metadata" and "Refresh Metadata" at the individual title level. Both were tried extensively. The refresh would run, the spinner would spin, and the result would be the same wrong match — or no match at all. Plex's documentation acknowledges that refreshing re-runs the same matching algorithm with the same inputs, so if the original match failed, refreshing fails the same way.

**2. "Fix Incorrect Match" via the Plex UI.** This worked — when it worked. You click the three dots on a title, choose "Fix Incorrect Match," type the correct title, and pick from a list of search results. For a library of 50 titles, this is manageable. For a library of 1,700+ movies and 300 TV shows, this is weeks of tedious manual work. And because it must be done through the Plex web interface, there is no way to automate or batch it.

**3. Renaming files to match Plex's expected format.** Plex's documentation specifies exact naming conventions: `Movie Title (Year)/Movie Title (Year).ext` for movies, `Show Name/Season N/Show Name - SXXEXX.ext` for TV. Many of our files already followed this convention. Those that didn't were renamed. It helped at the margins but did not solve the underlying matching failures.

**4. Third-party metadata tools.** Several tools exist in the Plex ecosystem — Plex Meta Manager (now Kometa), TinyMediaManager, and others — that promise to solve exactly this problem. In practice:

- **Kometa** is a powerful tool but it is designed for managing collections, overlays, and playlists within Plex, not for fixing broken initial metadata matching. Its metadata writing capabilities require a running Plex server and operate on already-matched items.
- **TinyMediaManager** runs on Java, requires a graphical interface, and is designed primarily for the Kodi ecosystem. Its Plex integration is incomplete, and configuring it for a library this large produced inconsistent results — some titles updated correctly, others were skipped, and a subset were re-matched to wrong entries.
- **Subler and MP4Box** are excellent tools for embedding metadata *inside* MP4 files, and we use Subler extensively. But the metadata embedded in the file's atoms is read by Apple's TV.app natively — Plex does not read embedded MP4 metadata. The embedded poster art, the embedded title, the embedded synopsis — all invisible to Plex.

**5. Switching Plex agents.** Plex supports multiple metadata agents per library — The Movie Database, The Movie Database (Legacy), Plex Movie, Plex TV Series, TheTVDB, and Local Media Assets. We tried various combinations. Each agent has different strengths and different failure modes. None solved the problem completely, and mixing agents produced inconsistent results across the library.

### The Root Cause

After considerable experimentation, the underlying issue became clear: **Plex's metadata agents perform a fuzzy text search against their respective databases using your folder/file names as input.** When those names contain noise — quality tags like `[1080p]` or `[BluRay]`, source tags like `[YTS.MX]` or `[RARBG]`, codec identifiers, leading numbering from download managers, accented characters in folder names, or typos — the search returns no results or the wrong results.

The agents have no way to know that `Léon The Professional [1080p] [BluRay] [YTS.MX]` is the same film as `Léon: The Professional (1994)`. Or that `Harry Potter and the Sorcerors Stone` (misspelled) is `Harry Potter and the Sorcerer's Stone`. Or that `Star Wars 4K77 v2(No DNR)` is not a TMDB entry at all.

Plex's matching is also connection-dependent. Large library refreshes make thousands of API calls to TMDB and TVDB. If the server's connection is interrupted mid-refresh, or if the external APIs return errors or rate-limit responses, Plex silently moves on — and the items that failed during that refresh may not be retried unless you manually trigger another refresh.

### The Solution

The Plex ecosystem has long supported a mechanism called **Local Media Assets** — a built-in Plex agent that reads metadata from sidecar files placed alongside your video files rather than fetching from the internet. The format is `.nfo` — an XML file containing structured metadata (title, year, plot, cast, ratings, genre, and critically, database IDs).

When Local Media Assets is set as the primary agent and a correctly-formatted `.nfo` file is present in the same folder as the video, Plex reads the metadata directly from that file. No internet search. No fuzzy matching. No wrong-title matches. The metadata is exactly what the `.nfo` file contains.

This approach is used extensively in the Kodi/XBMC ecosystem, where NFO scraping and local metadata management have been mature for over a decade. The tools built for Kodi, however, do not map cleanly onto Plex's library structure and agent configuration. We needed something that:

1. Understood our exact folder structure (one movie per folder, TV shows in `Season N` subdirectories)
2. Used TMDB for movies and TVDB for TV shows — the same sources Plex itself uses
3. Wrote NFO files in Plex's expected format, not Kodi's
4. Handled the noise in our folder names — quality tags, source tags, accents, typos
5. Ran without a GUI, could be stopped and restarted, and reported progress clearly
6. Also extracted the embedded poster artwork from our iTunes/Subler-encoded MP4 files, since Plex cannot read embedded MP4 artwork but can read `poster.jpg` sidecar files

None of the existing tools did all of this. So we built it.

---

## What These Scripts Do

### [`preflight.py`](preflight.py)

A shared support module imported by all three scripts. It runs before any processing begins and handles:
- **Dependency checks:** Python 3.8+, ffmpeg on PATH, API keys set, write permissions
- **Auto-installation:** if ffmpeg is missing, an OS-native dialog offers to install it via Homebrew, apt, dnf, pacman, winget, or Chocolatey depending on the platform
- **OS-native notifications and dialogs:** system alerts on completion, platform-native Yes/No dialogs for install consent
- **Logging:** one timestamped log file per run, written to `~/Library/Logs/PlexNFOCreator/` (macOS), `~/.local/share/plex-nfo-creator/logs/` (Linux), or `%APPDATA%\PlexNFOCreator\Logs\` (Windows)
- **Progress window:** a dark-themed tkinter GUI with a live progress bar, scrollable log, done/errors/skipped counters, Cancel button, and Open Log button

### [`scraper.py`](scraper.py)

The core script. For each movie folder, it:
1. Cleans the folder name (strips quality tags, leading numbers, brackets)
2. Searches TMDB for the movie
3. If not found, tries up to 8 fuzzy variants (strip punctuation, remove leading articles, ASCII-fold accents, strip subtitles)
4. Fetches full details including credits and external IDs (IMDb)
5. Writes a `Movie.nfo` file with title, year, plot, runtime, rating, genres, studio, director, cast, and `<uniqueid>` tags for TMDB and IMDb

For TV shows, it does the same at three levels — show, season, and episode — using TVDB.

The `<uniqueid>` tags are particularly important. They tell Plex exactly which TMDB/TVDB/IMDb entry corresponds to each item, enabling precise matching without any fuzzy search.

### [`extract_artwork.py`](extract_artwork.py)

Our media files were purchased through the iTunes Store or encoded with Subler. Both embed poster artwork directly inside the MP4 container as a secondary video stream. The Apple TV app reads this artwork natively. Plex does not.

This script uses `ffmpeg` to extract that embedded artwork and save it as a `poster.jpg` sidecar file alongside each video. For TV shows, it also generates season-level `poster.jpg` files and per-episode `-thumb.jpg` thumbnails.

### [`rename_movies.py`](rename_movies.py)

A preprocessing tool. Before running the scraper, this script cleans up folder and file names — stripping torrent-style tags, quality indicators, source identifiers, and leading numbering. It always runs as a dry run first, showing exactly what would change before anything is renamed.

### Metadata Generator

A complementary, scheduled automation layer that runs daily to pick up newly added content and keep metadata current. Unlike the core suite (which is run on-demand), the generator runs unattended.

**Key behaviors:**
- **Selective processing** — each item is checked before any API call; if both NFO and all artwork are already present, the item is skipped entirely with zero API calls
- **Full FileBot artwork set** — downloads `poster.jpg`, `folder.jpg`, `backdrop.jpg`, `clearart.png`, `disc.png`, and `logo.png` per movie; plus `banner.jpg`, `fanart.jpg`, `clearart.png`, `logo.png`, and `landscape.jpg` per TV show — the same files FileBot fetches when "fetch data" is selected
- **Original posters preferred** — TMDB official artwork is fetched first; FanArt.tv is used as a fallback for poster/backdrop and as the exclusive source for clearart, disc, and logo
- **Plex auto-refresh** — triggers a Plex library refresh automatically after each run
- **`--media-type tv | movies | all`** — process only what you need

Two scripts are available:
- `metadata-generator/plex_metadata_generator.py` — TV shows + Movies
- `metadata-generator/plex_metadata_generator_extended.py` — TV shows + Movies + Music (iTunes Search API + Apple MusicKit + MusicBrainz)

See the [Metadata Generator Reference](metadata-generator-Reference) for full documentation.

---

## Results

On a library of 1,762 movies and 309 TV shows (19,754 episodes):

| Metric | Count |
|--------|-------|
| Movies with NFO | 1,625 (92%) |
| TV shows with NFO | 254 (82%) |
| Episode NFOs | ~18,000+ |
| Movie posters extracted | 1,692 |
| Episode thumbnails extracted | 19,700+ |
| Movies not found (home recordings, unofficial cuts) | 75 |
| TV shows not found (local/niche content) | 55 |

The 75 movies and 55 TV shows that could not be matched are genuinely not in TMDB or TVDB — home recordings, local news segments, unofficial fan restorations of classic films, and obscure educational content. These require manual Plex matching or will remain without metadata.

---

## Navigation

### Core Suite
- **[Installation & Setup](Installation)**
- **[preflight.py Reference](preflight.py-Reference)** — dependency checks, auto-install, progress window, logging
- **[scraper.py Reference](scraper.py-Reference)**
- **[extract_artwork.py Reference](extract_artwork.py-Reference)**
- **[rename_movies.py Reference](rename_movies.py-Reference)**

### Metadata Generator
- **[Metadata Generator Reference](metadata-generator-Reference)** — selective processing, movie + TV support, full artwork set, scheduling, subtitles, fuzzy matching, parallel workers
- **[Extended Script Reference](plex_metadata_generator_extended-Reference)** — everything above plus Music libraries: iTunes Search API, Apple MusicKit, MusicBrainz local DB + JSON dump, artist/album/track NFOs

### Reference
- **[API Keys Guide](API-Keys)** — every API key used by this suite: what it's for, how to get it, where to put it
- **[Process Flow Diagrams](Diagrams)** — Mermaid flowcharts for every decision path (31 diagrams including full extended-script architecture and music provider flows)
- **[NFO Format Reference](NFO-Format-Reference)**
- **[Plex Configuration](Plex-Configuration)**
- **[Troubleshooting](Troubleshooting)**
- **[FAQ](FAQ)**
