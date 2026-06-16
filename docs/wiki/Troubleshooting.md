# Troubleshooting

---

## scraper.py Issues

### "401 Unauthorized" from TVDB

**Cause:** The raw TVDB API key cannot be used as a Bearer token. TVDB v4 requires JWT authentication via a login endpoint.

**Fix:** The script handles this automatically via `tvdb_login()`. If you see this error, verify your `TVDB_API_KEY` is correct — it should look like `a1313d27-4e2f-4d61-9ab8-cf7a22d53fbb` (a UUID-format project key from thetvdb.com).

Check you are using a **Project API Key** from `https://thetvdb.com/api-information`, not a subscriber key.

---

### Movie not found / wrong match

**Cause:** The folder name contains noise that survives all 8 fuzzy matching passes, or the film is not in TMDB.

**Diagnosis:** Check what folder name the script is searching. The script logs the folder name for each error.

**Common causes:**
- Foreign language title in the folder but English title in TMDB
- The film is a home recording or fan edit not in TMDB
- Folder name has a serious typo (beyond what ASCII folding catches)

**Fix options:**
1. Manually rename the folder to match the TMDB title, then re-run with `--force`
2. For foreign films: rename to the title as it appears on TMDB (usually the original title or the English title)
3. For items genuinely not in TMDB: create a minimal `Movie.nfo` by hand, or use "Fix Incorrect Match" in Plex

---

### TV show found but episodes missing

**Cause:** Episode filenames don't follow the `S01E01` pattern, or TVDB has different episode numbering.

**Diagnosis:** Look at the season directory. Episode files must contain `S##E##` somewhere in the filename. Files named like `Breaking.Bad.101.mkv` (season 1, episode 1 encoded as `101`) will not be matched.

**Fix:** Rename episode files to include `S01E01` format, then re-run scraper.

For episode numbering mismatches (TVDB uses DVD order, your files use broadcast order, etc.): check which ordering TVDB uses for that show. TVDB's "official" ordering is what the script uses — it fetches from the `episodes/official` endpoint.

---

### Script killed / process terminated

**Cause:** Out of memory, or macOS terminated the process (this happened during large `--force` runs). The script is resume-safe.

**Fix:** Simply run the same command again. Existing `.nfo` files are skipped automatically. If you want to re-process everything, use `--force`.

---

### "No module named requests"

```bash
pip3 install requests
```

---

### Rate limit errors from TMDB

If TMDB returns HTTP 429:
- The default `RATE_SLEEP = 0.28` (0.28s between calls × 4 workers = ~14 calls/sec) is within TMDB's 40 req/10s limit
- If you consistently hit 429, increase `RATE_SLEEP` to `0.5` or higher

---

## extract_artwork.py Issues

### "ffmpeg: command not found"

```bash
brew install ffmpeg
```

Verify: `ffmpeg -version`

---

### poster.jpg is created but is tiny / corrupted

**Cause:** ffmpeg ran but produced output smaller than 1,000 bytes (the script's minimum size check). The file was deleted and logged as a failure.

**Cause:** The video file may not contain embedded artwork in the secondary video stream. This is normal for:
- Files ripped from Blu-ray or DVD
- Files downloaded from non-iTunes sources
- Files encoded with tools that don't embed artwork

iTunes-purchased files and Subler-processed files consistently have embedded artwork. Other sources usually don't.

---

### "Permission denied" writing poster.jpg

Grant Terminal full disk access:
1. **System Settings → Privacy & Security → Full Disk Access**
2. Add **Terminal** (or your terminal emulator) to the list
3. Re-run the script

---

### Episode thumbnails look like wrong scene / black frame

**Cause:** `Strategy 1` extracted from stream index 1, but that stream was a different video track (chapter thumbnail, preview, etc.) rather than cover art.

This is uncommon in standard iTunes files but can occur in complex Matroska containers. No workaround in the current version — the thumbnail extracted is whatever is in stream index 1.

---

## Plex Issues

### NFO files are present but Plex is still showing wrong metadata

1. Verify **Local Media Assets** is at the top of the agent list: **Settings → Libraries → [Library] → Edit → Agents tab**
2. Run **Manage Library → Refresh All Metadata** (not just "Scan Library Files")
3. Check one specific item: three dots → Get Info → Metadata Source should say "Local Media Assets"

If the source is not "Local Media Assets" after a full refresh, the agent is not at the top.

---

### Plex refreshed but some items still show the old/wrong poster

Plex caches artwork. Try:
1. Three dots on the item → **Refresh Metadata** (single item)
2. Three dots → **Fix Incorrect Match** if the underlying match is wrong

---

### Metadata was correct before, now it's wrong after a refresh

If a Plex library refresh overwrites your NFO-sourced metadata with online data, the Local Media Assets agent is no longer at the top. Re-check agent priority.

---

### `tvshow.nfo` exists but seasons show as "Unknown Season"

**Cause:** Season directories are not named in a recognized format.

Recognized patterns: `Season 1`, `Season 01`, `Season1`, `Specials`, `Season 0`

Not recognized: `Series 1`, `S01`, `Year 1`, `Part 1`

**Fix:** Rename season directories to `Season N` format, then re-run `scraper.py tvshows --force`.

---

## Getting More Information

### Check what NFO was written

```bash
cat "/Volumes/iTunes 5/Movies/Back to the Future (1985)/Movie.nfo"
```

### Check what Plex sees

**Settings → Troubleshooting → Download Logs** — search the log for the title showing issues.

### Count NFOs

```bash
# Movie NFOs
find "/Volumes/iTunes 5/Movies" -name "Movie.nfo" | wc -l

# Show NFOs
find "/Volumes/iTunes 5/TV Shows" -name "tvshow.nfo" | wc -l

# Episode NFOs
find "/Volumes/iTunes 5/TV Shows" -name "*.nfo" ! -name "tvshow.nfo" ! -name "season.nfo" | wc -l
```

### Find errors (movies without NFO)

```bash
for d in "/Volumes/iTunes 5/Movies"/*/; do
  [ ! -f "${d}Movie.nfo" ] && echo "$d"
done
```
