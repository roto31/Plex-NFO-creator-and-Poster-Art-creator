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

The scripts do not download posters from the API — they only extract embedded artwork. Adding API-based poster downloads is a possible future enhancement.
