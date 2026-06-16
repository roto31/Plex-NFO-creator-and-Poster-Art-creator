# Installation & Setup

## Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.8+ | Pre-installed on macOS 10.15+ |
| ffmpeg | Any recent | Only required for `extract_artwork.py` |
| TMDB API key | — | Free, required for `scraper.py` |
| TVDB API key | — | Free, required for `scraper.py` TV mode |

---

## Step 1 — Download the Scripts

```bash
git clone https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator.git
cd Plex-NFO-creator-and-Poster-Art-creator
```

Or download the ZIP from the [Releases page](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/releases).

---

## Step 2 — Install ffmpeg (for artwork extraction only)

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install ffmpeg
brew install ffmpeg

# Verify
ffmpeg -version
```

If you only plan to use `scraper.py` and `rename_movies.py`, ffmpeg is not needed.

---

## Step 3 — Get API Keys

### TMDB API Key (for movies)

1. Create a free account at [themoviedb.org](https://www.themoviedb.org)
2. Go to **Settings → API**
3. Request an API key (choose "Developer")
4. Copy the **API Key (v3 auth)** value

### TVDB API Key (for TV shows)

1. Create a free account at [thetvdb.com](https://www.thetvdb.com)
2. Go to **[API Information](https://thetvdb.com/api-information)**
3. Generate a **Project API Key**
4. Copy the key (it looks like `a1313d27-4e2f-4d61-9ab8-cf7a22d53fbb`)

---

## Step 4 — Add API Keys to scraper.py

Open `scraper.py` in any text editor and update lines 25–26:

```python
TMDB_API_KEY = "your_tmdb_key_here"
TVDB_API_KEY = "your_tvdb_key_here"
```

Save the file.

---

## Step 5 — Verify Python Version

```bash
python3 --version
# Should print Python 3.8.x or higher
```

---

## Step 6 — Configure Plex (before running scripts)

Before running the scripts, configure your Plex libraries to use Local Media Assets as the primary agent:

1. Open Plex Web UI at `http://localhost:32400/web`
2. Go to **Settings → Libraries**
3. Click **Edit** on your Movies library
4. Click the **Agents** tab
5. Find **Local Media Assets (Movies)** in the list
6. Drag it to the **very top** of the agent priority list
7. Click **Save Changes**
8. Repeat for your TV Shows library, using **Local Media Assets (TV)**

> **This step is critical.** If Local Media Assets is not at the top, Plex will ignore your `.nfo` files and continue using its online agents.

---

## Recommended Run Order

```bash
# 1. Preview folder name changes
python3 rename_movies.py "/path/to/Movies"

# 2. Apply renames if they look correct
python3 rename_movies.py "/path/to/Movies" --rename

# 3. Generate NFO files
python3 scraper.py movies "/path/to/Movies"
python3 scraper.py tvshows "/path/to/TV Shows"

# 4. Extract embedded poster art
python3 extract_artwork.py movies "/path/to/Movies" --extract
python3 extract_artwork.py tvshows "/path/to/TV Shows" --extract

# 5. In Plex: Refresh All Metadata for both libraries
```

---

## macOS Permissions

On macOS, if your media is on an external drive, you may need to grant Python permission to access it:

1. Go to **System Settings → Privacy & Security → Files and Folders** (or **Full Disk Access**)
2. Add **Terminal** (or your terminal app) to the allowed list
3. Re-run the script

If you see `PermissionError: [Errno 13] Permission denied`, this is the cause.
