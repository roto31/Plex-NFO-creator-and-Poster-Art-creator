# Frequently Asked Questions

---

## General

**Q: Do I need to run all three scripts?**

A: No. Each script is independent:
- `rename_movies.py` — optional preprocessing. Only needed if your folder names contain quality tags, source identifiers, or leading numbering.
- `scraper.py` — required to generate `.nfo` files. This is the core script.
- `extract_artwork.py` — only needed if your files have embedded artwork (iTunes purchases, Subler-processed files) and you want Plex to display that artwork.

If your folder names are already clean and you don't care about embedded artwork, you only need `scraper.py`.

---

**Q: Will these scripts modify my video files?**

A: No. All three scripts only create or rename sidecar files (`.nfo`, `.jpg`) and folder/file names. They never modify the contents of your video files.

`extract_artwork.py` reads video files with ffmpeg to extract the artwork stream but does not write back to the video file.

---

**Q: Can I run the scripts multiple times?**

A: Yes. All scripts are resume-safe. Without `--force`, they skip items that already have output files. You can safely re-run after an interruption and only the remaining items will be processed.

---

**Q: How long does the scraper take?**

A: Approximate runtimes on a typical home library:

| Library | Size | Approximate Runtime |
|---------|------|---------------------|
| 1,760 movies | — | 30–60 minutes |
| 309 shows / 19,754 episodes | — | 3–6 hours |

Runtime depends on API response times and your internet connection. The 4-worker parallel execution provides a significant speedup over sequential processing.

---

**Q: Do the scripts require an internet connection?**

A: `scraper.py` requires an internet connection to query TMDB and TVDB. `extract_artwork.py` and `rename_movies.py` are fully offline.

Once NFO files are generated, Plex reads them locally with no internet needed.

---

**Q: Do these scripts work on Windows and Linux?**

A: Yes. All scripts are cross-platform (macOS, Linux, Windows). The `preflight.py` module handles platform differences for notifications, dialogs, installation, and log file locations. The core processing logic is identical across all platforms.

---

## Preflight & Installation

**Q: What does "preflight" mean?**

A: Before any processing begins, each script runs a set of preflight checks — verifying that Python is a sufficient version, that required tools (ffmpeg) are installed and on PATH, that API keys are set, and that the script has write permission to the target directory. If any check fails, you get a clear explanation and (for ffmpeg) an offer to install automatically.

---

**Q: Do I need to install ffmpeg before running the scripts?**

A: No. When you run `extract_artwork.py` without ffmpeg installed, a dialog appears offering to install it automatically. If you click Yes, the script installs ffmpeg using your platform's native package manager (Homebrew on macOS, apt/dnf/pacman/zypper on Linux, winget/choco on Windows). If you click No, instructions are printed and the ffmpeg download page opens in your browser.

---

**Q: I downloaded ffmpeg manually but the script still says it's missing. Why?**

A: The script uses PATH lookup (`shutil.which("ffmpeg")`) — the same mechanism used by the shell. If you downloaded the ffmpeg binary but did not add its directory to your PATH, the script cannot find it. Open a **new terminal** after installation and run `ffmpeg -version` to verify it's on PATH. If that command fails, ffmpeg is not on PATH regardless of where it's installed on disk.

The auto-installer handles this correctly for all platforms — it installs via package managers that put binaries on PATH automatically.

---

**Q: Will the auto-installer make changes to my system without permission?**

A: No. A dialog always asks before any installation begins. On Linux, the installer runs package manager commands that may require your `sudo` password — this is prompted in the terminal. If you click No in the dialog, nothing is installed and instructions are printed instead.

---

**Q: Can I skip the preflight checks?**

A: There is no flag to skip preflight. The checks are fast (under a second) and are designed to fail clearly rather than fail silently mid-run. If a check is causing a false failure, please open an issue with details.

---

## Progress Window & Logging

**Q: What is the progress window?**

A: When any script starts processing, a dark-themed GUI window opens showing a real-time progress bar, done/errors/skipped counters, a scrollable log of each item processed, a Cancel button, and an Open Log button. It uses tkinter, which is included with most Python installations.

---

**Q: The progress window didn't open — is something wrong?**

A: If tkinter is not available on your Python installation, the script automatically falls back to terminal output. Processing continues normally — you just won't see the GUI. To get tkinter:
- **macOS:** `brew install python-tk`
- **Linux:** `sudo apt-get install python3-tk`
- **Windows:** Reinstall Python from python.org with "tcl/tk and IDLE" checked

---

**Q: Where are the log files stored?**

A: One log file is written per run, with a timestamp in the filename so runs are never overwritten.

| Platform | Location |
|----------|----------|
| macOS | `~/Library/Logs/PlexNFOCreator/` |
| Linux | `~/.local/share/plex-nfo-creator/logs/` |
| Windows | `%APPDATA%\PlexNFOCreator\Logs\` |

The **Open Log** button in the progress window opens the current run's log file in the OS-native viewer (Console.app on macOS, text editor on Linux/Windows).

---

**Q: How do I open old log files?**

A: Log files are plain text. You can open them in any text editor. On macOS, they also appear in Console.app:
1. Open Console.app
2. In the sidebar, expand **Reports**
3. Expand your home folder → Library → Logs → PlexNFOCreator

On Windows, navigate to `%APPDATA%\PlexNFOCreator\Logs\` in Explorer.

---

**Q: Can I cancel a run mid-way through?**

A: Yes. Click the **Cancel** button in the progress window. The current item finishes processing, then the run stops. Progress made up to that point is saved (`.nfo` files already written remain). Re-running without `--force` will pick up where you left off.

---

**Q: I got a notification when the run finished. Where did it come from?**

A: The preflight module sends an OS-native notification at the end of every run showing the done/errors/skipped counts. On macOS this appears in Notification Center, on Linux via notify-send, and on Windows as a system tray balloon. This is normal behavior.

---

## API Keys

**Q: Are the API keys free?**

A: Yes. Both TMDB and TVDB offer free API keys for personal use. See the [Installation guide](Installation) for how to get them.

---

**Q: Can I use the same API keys on multiple machines?**

A: Yes. API keys are not machine-locked.

---

**Q: Will my API keys expire?**

A: TMDB keys do not expire. TVDB keys do not expire, but TVDB JWT login tokens have a limited lifetime (~1 month). The script obtains a fresh JWT each time it runs, so this is handled automatically.

---

## Matching

**Q: What percentage of movies get matched successfully?**

A: On the library this was built for (1,762 movies), 1,625 (92%) were matched. The 75 failures were:
- Home recordings and personal videos
- Fan restorations and unofficial cuts (e.g., `Star Wars 4K77`)
- Extremely obscure titles not in TMDB

A well-organized library with commercially released content will typically see 95%+ match rates.

---

**Q: What should I do with the movies that weren't matched?**

A: Three options:
1. **Rename the folder** to exactly match the TMDB title and re-run with `--force`
2. **Create a minimal NFO manually** — just title and uniqueid tags are enough for Plex
3. **Use "Fix Incorrect Match" in Plex** — for content that is in TMDB but the scraper couldn't find it

For content genuinely not in any database (home recordings, local news), no automated solution exists.

---

**Q: The scraper matched the right movie but the wrong year (remakes)**

A: This can happen when there are multiple films with the same title. Including the year in the folder name improves accuracy: `Scarface (1983)` vs `Scarface (1932)` — the scraper extracts the year from the folder name and passes it to TMDB as a filter.

If a remake is being matched to the original, ensure your folder has the correct year in parentheses.

---

**Q: Can this handle anime, foreign films, or documentary series?**

A: Yes, with some caveats:
- **Anime:** TMDB has good anime coverage. Folder names with English titles work best. Japanese/romanized titles also work via ASCII folding in the fuzzy variants.
- **Foreign films:** Use the title as it appears in TMDB. For French films, TMDB often lists both the French original title and an English title — either usually works.
- **Documentaries:** TMDB and TVDB both have documentary coverage. Multi-part documentary series may need the folder structure to match TV Shows format rather than Movies.

---

## NFO Files

**Q: What happens if I delete an NFO file?**

A: The next time you run `scraper.py` (without `--force`), nothing happens — the script skips items that already have NFOs and only processes new ones. To regenerate a deleted NFO, either add back just that one file's folder to a test run, or run the whole library with `--force`.

In Plex, deleting an NFO and triggering a refresh will cause Plex to fall through to the next agent (TMDB online, etc.). The match may or may not be correct.

---

**Q: Can I edit NFO files manually?**

A: Yes. NFO files are plain XML. You can open them in any text editor and change any field. After editing, trigger a "Refresh Metadata" on that specific item in Plex to pick up the change.

The `<uniqueid>` tags are the most important — if those are correct, Plex will reliably match the item even if other fields are missing.

---

**Q: Will Plex overwrite my NFO files?**

A: No. Plex reads NFO files but never writes to them. Your `.nfo` files are safe.

---

## Artwork

**Q: Why can't Plex see the artwork already embedded in my MP4 files?**

A: MP4 embedded artwork (stored in the `covr` atom) is part of the iTunes/MP4 container metadata standard. Apple's TV.app reads this natively. Plex's Local Media Assets agent only looks for sidecar `poster.jpg` files — it does not parse MP4 atoms for artwork. This is a longstanding Plex limitation. The `extract_artwork.py` script works around it by pulling the artwork out and saving it where Plex can find it.

---

**Q: The show poster looks like an episode still, not the official poster**

A: The show poster is extracted from the first episode of the first season. If that episode's embedded artwork is an episode thumbnail rather than the official show art, you'll get a still instead of a poster.

This can happen with older TV files or files processed by tools other than iTunes/Subler. Fix: replace `poster.jpg` in the show root folder with the correct poster image (download from TVDB or TMDB and save as `poster.jpg`).

---

**Q: Can I use a higher-resolution poster from TMDB/TVDB instead of the embedded artwork?**

A: Yes. Simply download the poster from TMDB or TVDB and save it as `poster.jpg` in the movie or show folder, overwriting the extracted image. Plex will use whichever `poster.jpg` is present.

The core scripts (`extract_artwork.py`) only extract embedded MP4 artwork. The **Metadata Generator** downloads official posters from TMDB/TVDB automatically — see the [Metadata Generator Reference](metadata-generator-Reference).

---

## Metadata Generator Setup

**Q: Do I need to edit the config file before running?**

A: No. On first run, the script shows a series of native OS dialogs that walk you through setup:
1. **Library paths** — a folder browser for Movies, TV Shows, and Music (with Add/Done to add multiple volumes)
2. **API keys** — a text-input dialog for each service whose key is missing
3. **Scan mode** — Yes/No dialog asking whether to process everything or only new items
4. **Save** — offers to write your answers back to the config file so you are never prompted again

All dialogs are bypassed by passing `--no-prompts` (used automatically by the scheduling installers).

---

**Q: I have movies on two different drives. How do I add both?**

A: During the first-run setup dialog for Movies, click **Yes** when asked "Add another volume?" and select your second drive. You can add as many volumes as you have. All paths are saved to `movies_library_roots` in the config as a list and scanned on every run.

You can also edit the config directly:
```json
"movies_library_roots": ["/Volumes/Drive1/Movies", "/Volumes/NAS/Movies"]
```

---

**Q: How does the script verify my API keys?**

A: When you enter a key in a setup dialog, it is immediately tested against the live API before being saved. If the key is rejected, an error dialog explains the reason (invalid key, expired, quota exceeded, etc.) and offers to let you try again. You can retry as many times as needed or skip to continue without that service.

For already-configured keys, the script runs a full validation check every 15 days. If a key has expired since the last check, a **blocking dialog** appears — the job pauses until you enter a valid replacement key. This applies even in unattended/scheduled mode, because a job with an invalid key would silently produce no output.

---

**Q: What does "Force a full rescan" mean?**

A: The force-scan dialog (shown at the end of first-run setup) is equivalent to passing `--force` on the command line. Choosing **Yes** causes the script to process every item — even those that already have NFO files and artwork. Choosing **No** (the default for ongoing use) skips anything already complete.

---

## Metadata Generator

**Q: Does the Metadata Generator replace `scraper.py`?**

A: No. They serve different purposes:
- `scraper.py` is for **initial, on-demand batch processing** — run it once to generate NFOs for your entire library
- The Metadata Generator is for **ongoing automated updates** — it runs daily and only processes items that are new or missing files

Use `scraper.py` first to bootstrap your library, then add the Metadata Generator to keep it current.

---

**Q: Can I run movies only with the Metadata Generator?**

A: Yes: `python3 plex_metadata_generator.py --media-type movies`

---

**Q: Will the Metadata Generator overwrite files it already generated?**

A: No. Selective processing checks every NFO file and every artwork file individually before any API call. If an item already has both its NFO and all expected artwork files, it is logged as `⏭ already complete` and skipped entirely.

Use `--force` to override this behavior and regenerate everything.

---

**Q: What is the difference between `plex_metadata_generator.py` and `plex_metadata_generator_extended.py`?**

A: Both handle TV shows and Movies. The extended script additionally supports Music libraries (Spotify + MusicBrainz for artist, album, and track metadata). If you don't have a music library in Plex, use the standard script.

---

**Q: Do I need a FanArt.tv API key?**

A: It is optional but highly recommended. Without it, `clearart.png`, `disc.png`, and `logo.png` are skipped (a warning is logged). `poster.jpg`, `folder.jpg`, and `backdrop.jpg` still download from TMDB. FanArt.tv personal API keys are free at [fanart.tv/get-an-api-key](https://fanart.tv/get-an-api-key/).

---

**Q: How does the Metadata Generator's artwork download differ from `extract_artwork.py`?**

A: They are complementary, not redundant:

| | `extract_artwork.py` | Metadata Generator |
|--|---------------------|--------------------|
| Source | Embedded MP4 artwork stream | TMDB + FanArt.tv + TVDB APIs |
| Files written | `poster.jpg` (movie, show, season), `-thumb.jpg` (episode) | Full set: `poster.jpg`, `folder.jpg`, `backdrop.jpg`, `clearart.png`, `disc.png`, `logo.png` |
| Requires internet | No | Yes |
| Requires ffmpeg | Yes | No |
| When to use | iTunes/Subler-encoded files with embedded art | Any file — API-sourced art regardless of what's embedded |

If you have iTunes-purchased files, run both. If your files have no embedded artwork, skip `extract_artwork.py` and use the Metadata Generator directly.

---

**Q: Do I need both the sidecar `.srt` and the embedded subtitle track?**

A: Yes — they serve different players:

| Format | Read by |
|--------|--------|
| `{stem}.{lang}.srt` | Plex (Local Media Assets picks it up automatically) |
| Embedded `mov_text` track | Apple TV local media playback |

Plex does not read embedded subtitle tracks from MP4 files. Apple TV's local player does not read sidecar `.srt` files. You need both for full coverage.

---

**Q: What is the OpenSubtitles download limit?**

A: By default (API key only, no account credentials): **5 downloads/day**. With a free OpenSubtitles account and credentials in the config: **40 downloads/day** per API key. Subdl is used as a fallback if OpenSubtitles is exhausted or unavailable, with no account required.

API key registration is free at [opensubtitles.com/consumers](https://www.opensubtitles.com/consumers) — no credit card.

---

**Q: Will subtitle embedding modify my video files?**

A: Yes. When `embed_in_file: true`, ffmpeg writes the subtitle track into the MP4/M4V file. The process is atomic — ffmpeg writes to a temp file first, then replaces the original only after a size sanity check passes. The disk space required during the operation is equal to the file size (temp + original exist simultaneously until the replace).

MKV files are never modified — sidecar-only is used automatically for `.mkv`.
