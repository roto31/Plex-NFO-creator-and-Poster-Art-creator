# Troubleshooting

---

## Preflight Issues

### "Python 3.8 or higher is required"

Your system Python is too old. Install a current version from [python.org](https://www.python.org/downloads/).

On macOS you can also use Homebrew:
```bash
brew install python
```

Then use `python3` to invoke scripts.

---

### API keys are not set / "placeholder value detected"

Open `scraper.py` and replace the placeholder values:

```python
TMDB_API_KEY = "your_actual_tmdb_key_here"
TVDB_API_KEY = "your_actual_tvdb_key_here"
```

See [Installation → Step 2](Installation#step-2--get-api-keys) for how to get free API keys.

---

### ffmpeg auto-install dialog does not appear

On Linux, `zenity` (GNOME) or `kdialog` (KDE) is needed for the GUI dialog. If neither is installed, the dialog falls back to a terminal `input()` prompt. Install zenity:

```bash
sudo apt-get install zenity      # Debian/Ubuntu
sudo dnf install zenity          # Fedora
```

On headless systems (no display), the dialog is skipped and you will be asked via the terminal instead.

---

### ffmpeg installed but script still says it is missing

The script uses PATH lookup — `shutil.which("ffmpeg")` — not a filesystem search. If you installed ffmpeg manually, you must open a **new terminal** after installation so the updated PATH takes effect.

Verify ffmpeg is on PATH in the current terminal:
```bash
which ffmpeg         # macOS / Linux
where ffmpeg         # Windows
ffmpeg -version      # should print version info
```

If these commands fail, ffmpeg is not on PATH. Check the PATH setup instructions printed by the script, or re-run the auto-installer.

---

### "Permission denied" writing to target directory

On macOS with an external drive, grant Full Disk Access to Terminal:
1. **System Settings → Privacy & Security → Full Disk Access**
2. Add your terminal application
3. Re-run the script

On Linux/Windows, verify the user running the script has write access to the target directory.

---

### Log file not written / log directory not created

The log directory is created automatically on first run. If it fails:

- **macOS:** Check that `~/Library/Logs/` is writable (it normally is for all users)
- **Linux:** Check that `~/.local/share/` is writable
- **Windows:** Check that `%APPDATA%` is accessible

If the log directory cannot be created, processing still runs but output goes to stderr only.

---

### Progress window does not appear / tkinter error

tkinter is included with most Python distributions but not all.

**macOS:** Install via Homebrew: `brew install python-tk` (the system Python on macOS does not include tkinter)

**Linux:** `sudo apt-get install python3-tk` (Debian/Ubuntu) or `sudo dnf install python3-tkinter` (Fedora)

**Windows:** Reinstall Python from [python.org](https://www.python.org/downloads/) and ensure "tcl/tk and IDLE" is checked during installation.

If tkinter cannot be loaded, the script falls back to terminal output and continues normally.

---

### Notifications do not appear

**macOS:** Notification Center permission is required. macOS prompts for this on first use. If you dismissed the prompt:
1. Open **System Settings → Notifications**
2. Find **Script Editor** or **Terminal** in the list
3. Enable notifications

**Linux:** `notify-send` must be installed: `sudo apt-get install libnotify-bin`

**Windows:** Notifications require PowerShell 5+ (included in Windows 10/11). If PowerShell is restricted by policy, notifications are silently skipped.

---

## scraper.py Issues

### "401 Unauthorized" from TVDB

**Cause:** The raw TVDB API key cannot be used as a Bearer token. TVDB v4 requires JWT authentication via a login endpoint.

**Fix:** The script handles this automatically via `tvdb_login()`. If you see this error, verify your `TVDB_API_KEY` is correct — it should look like `a1313d27-4e2f-4d61-9ab8-cf7a22d53fbb` (a UUID-format project key from thetvdb.com).

Check you are using a **Project API Key** from `https://thetvdb.com/api-information`, not a subscriber key.

---

### Movie not found / wrong match

**Cause:** The folder name contains noise that survives all 8 fuzzy matching passes, or the film is not in TMDB.

**Diagnosis:** Check the log file for that item's entry — the log shows the folder name the script searched.

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

### "ffmpeg: command not found" / ffmpeg check fails

Run the script and click **Yes** when asked to auto-install, or follow the manual install instructions at [Installation → Step 4](Installation#step-4--ffmpeg-for-extract_artworkpy-only).

Remember: ffmpeg must be on PATH, not just downloaded. Open a new terminal after manual installation.

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

### Check the log file

Every run writes a log file. The **Open Log** button in the progress window opens it directly.

Manual paths:
```bash
# macOS
ls ~/Library/Logs/PlexNFOCreator/
cat ~/Library/Logs/PlexNFOCreator/scraper_2026-06-16_143022.log

# Linux
ls ~/.local/share/plex-nfo-creator/logs/

# Windows (PowerShell)
dir $env:APPDATA\PlexNFOCreator\Logs\
```

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

---

## Metadata Generator Issues

### NFO files not being generated for movies

1. Ensure `movies_library_root` is set in the config and the path exists
2. Check that `tmdb.api_key` is a real key (not `YOUR_TMDB_API_KEY_HERE`)
3. Run with `--debug` to see what TMDB search queries are being made
4. Verify the movie folder name includes the year: `Movie Title (1985)/` — without the year, the scraper retries but may match the wrong version

```bash
python3 metadata-generator/plex_metadata_generator.py \
  --config /etc/plex-metadata-generator.conf \
  --media-type movies --movie "Back to the Future (1985)" --debug
```

### `clearart.png`, `disc.png`, `logo.png` are not being downloaded

These come exclusively from FanArt.tv and require `fanart_tv.api_key` in the config. Check:

```bash
grep fanart_tv /etc/plex-metadata-generator.conf
```

If the key reads `YOUR_FANART_TV_API_KEY_HERE` or is absent, get a free personal key at [fanart.tv/get-an-api-key](https://fanart.tv/get-an-api-key/) and add it to the config. The script logs a warning (not an error) when this key is missing.

### Artwork files exist but Plex is not showing them

1. Verify Plex's agent priority: **Settings → Libraries → [Library] → Edit → Agents** — **Local Media Assets** must be the top-ranked agent
2. After placing new artwork files, trigger a refresh: **⋯ → Manage Library → Refresh All Metadata**
3. Verify file sizes are > 0 bytes: `ls -la "/path/to/movie/poster.jpg"`
4. Check filename case — Plex on Linux is case-sensitive; the filenames must be lowercase (`poster.jpg`, not `Poster.jpg`)

### Plex library refresh not triggering after generation

Check config:
```json
"plex": {
  "url": "http://localhost:32400",
  "token": "YOUR_PLEX_TOKEN",
  "tv_library_key": "1",
  "movies_library_key": "2"
}
```

- `token` — visible by viewing page source at `http://localhost:32400/web/` and searching for `authenticationToken`
- `tv_library_key` / `movies_library_key` — visible in the URL when viewing that library in Plex Web (`/library/sections/2/`)

Test manually:
```bash
curl -X POST -H "X-Plex-Token: YOUR_TOKEN" \
  http://localhost:32400/library/sections/2/refresh
```

### Script runs but marks everything as "already complete" on first run

This means all items already have both NFO and artwork. Run with `--force` to regenerate:

```bash
python3 metadata-generator/plex_metadata_generator.py \
  --config /etc/plex-metadata-generator.conf \
  --media-type all --force
```

### health-check.py reports config issues

Common config fixes:

| Message | Fix |
|---------|-----|
| `Missing config keys: ['tv_library_root']` | Add `"tv_library_root": "/path/to/TV"` to config (or use the old `"library_root"` key) |
| `Config contains placeholder API keys` | Replace all `YOUR_*_HERE` values with real keys |
| `fanart_tv.api_key not set` | Warning only — add key to get clearart/disc/logo artwork |
| `Tunarr DB not found` | Normal if not using Tunarr — it is an optional fallback source |
