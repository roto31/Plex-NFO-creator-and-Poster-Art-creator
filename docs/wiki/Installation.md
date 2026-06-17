# Installation & Setup

## Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.8+ | Pre-installed on macOS 10.15+; download from python.org for Windows/Linux |
| ffmpeg | Any recent | Only required for `extract_artwork.py`; offered for auto-install on first run |
| TMDB API key | — | Free, required for `scraper.py` |
| TVDB API key | — | Free, required for `scraper.py` TV mode |

No third-party Python packages are required. All four scripts use only the Python standard library.

---

## Step 1 — Download the Scripts

```bash
git clone https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator.git
cd Plex-NFO-creator-and-Poster-Art-creator
```

Or download the ZIP from the [Releases page](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/releases).

---

## Step 2 — Get API Keys

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

## Step 3 — Add API Keys to scraper.py

Open `scraper.py` in any text editor and update lines 25–26:

```python
TMDB_API_KEY = "your_tmdb_key_here"
TVDB_API_KEY = "your_tvdb_key_here"
```

Save the file.

---

## Step 4 — ffmpeg (for extract_artwork.py only)

`extract_artwork.py` requires ffmpeg on your system PATH. **You do not need to install it manually** — on first run the script detects whether ffmpeg is present and offers to install it automatically.

### Automatic Install (Recommended)

When you run `extract_artwork.py` without ffmpeg installed, a system dialog appears:

> **"ffmpeg is required for artwork extraction. Install it automatically?"**

Click **Yes** and the script installs ffmpeg using your platform's package manager:

| Platform | Package manager used |
|----------|---------------------|
| macOS | Homebrew (`brew install ffmpeg`). Homebrew itself is installed first if not present. |
| Linux | `apt-get`, `dnf`, `pacman`, `zypper`, or Homebrew — whichever is detected first |
| Windows | `winget install ffmpeg`. Falls back to Chocolatey if winget is unavailable. |

Install output streams into the progress window log in real time.

### Manual Install

If you click **No** or prefer to install manually, detailed platform-specific instructions are printed to the terminal and a log file. The ffmpeg download page opens automatically in your browser.

> **PATH requirement:** ffmpeg must be in a directory on your system PATH. Downloading the binary alone is not sufficient — the scripts find ffmpeg via PATH lookup, not by searching your filesystem. The automatic installer handles PATH correctly. If you install manually, follow the PATH setup instructions printed by the script.

#### macOS

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install ffmpeg
brew install ffmpeg

# Verify ffmpeg is on PATH
ffmpeg -version
```

#### Linux

```bash
# Debian / Ubuntu
sudo apt-get update && sudo apt-get install -y ffmpeg

# Fedora / RHEL
sudo dnf install -y ffmpeg

# Arch / Manjaro
sudo pacman -S --noconfirm ffmpeg

# openSUSE
sudo zypper install -y ffmpeg

# Verify
ffmpeg -version
```

#### Windows

```powershell
# Using winget (Windows 10 1709+ / Windows 11)
winget install ffmpeg

# Using Chocolatey
choco install ffmpeg

# Verify (in a new terminal)
ffmpeg -version
```

After installing ffmpeg manually, open a **new** terminal so the PATH changes take effect before running the script.

---

## Step 5 — Verify Python Version

```bash
python3 --version
# Should print Python 3.8.x or higher
```

On Windows:
```powershell
python --version
```

If Python is not found, download it from [python.org](https://www.python.org/downloads/). On Windows, check **"Add Python to PATH"** during installation.

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
# 1. Preview folder name changes (dry run — nothing is changed)
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

Each script opens a **progress window** showing real-time status and writes a **log file** to the OS-native log directory (see [preflight.py Reference](preflight.py-Reference) for log locations).

---

## First Run Walkthrough

The first time you run any script, the preflight system runs before processing begins:

1. **Python version check** — if Python is too old, the script exits with instructions
2. **API key check** (scraper.py only) — if keys are placeholder values, the script exits with instructions
3. **ffmpeg check** (extract_artwork.py only) — if not on PATH, the install dialog appears
4. **Write permission check** — if the target directory is not writable, the script exits with instructions
5. **Progress window opens** — processing begins, all output goes to the window and the log file

---

## macOS Permissions

On macOS, if your media is on an external drive, you may need to grant Python permission to access it:

1. Go to **System Settings → Privacy & Security → Files and Folders** (or **Full Disk Access**)
2. Add **Terminal** (or your terminal app) to the allowed list
3. Re-run the script

If you see `PermissionError: [Errno 13] Permission denied`, this is the cause.

---

## Windows Notes

- Run scripts from **Command Prompt** or **PowerShell** — not from the Windows Store Python launcher's interactive shell
- If `python3` is not recognized, try `python` instead
- ffmpeg auto-install requires an internet connection and may take a few minutes
- The first PowerShell notification/dialog may trigger a Windows Defender prompt — this is normal

---

## Linux Notes

- tkinter is required for the progress window: `sudo apt-get install python3-tk` on Debian/Ubuntu
- `notify-send` is needed for completion notifications: `sudo apt-get install libnotify-bin`
- `zenity` or `kdialog` is needed for install dialogs. On headless systems, the dialog is skipped and the auto-install proceeds automatically
- If running as a non-root user, the `sudo`-based package manager commands will prompt for your password in the terminal during install

---

## Metadata Generator Setup

### 1. Get API Keys

In addition to the core TMDB + TVDB keys, the Metadata Generator uses:

| Key | Required for | Where to get |
|-----|-------------|-------------|
| TMDB | Movies, TV posters/backdrops | [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) |
| TVDB | TV show + episode metadata | [thetvdb.com/api-information](https://thetvdb.com/api-information) |
| FanArt.tv | clearart, disc, logo artwork | [fanart.tv/get-an-api-key](https://fanart.tv/get-an-api-key/) — free personal key |
| Plex token | Library auto-refresh | View page source at `http://localhost:32400/web/`, search `authenticationToken` |
| Spotify (extended only) | Music metadata | [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) |

### 2. Configure

```bash
cp metadata-generator/plex-metadata-generator.conf /etc/plex-metadata-generator.conf
# or macOS:
cp metadata-generator/plex-metadata-generator.conf ~/Library/Preferences/plex-metadata-generator.conf
```

Edit the config and fill in your keys and library paths:

```json
{
  "tv_library_root": "/path/to/TV Shows",
  "movies_library_root": "/path/to/Movies",
  "plex": {
    "url": "http://localhost:32400",
    "token": "YOUR_PLEX_TOKEN",
    "tv_library_key": "1",
    "movies_library_key": "2"
  },
  "tvdb":      { "api_key": "YOUR_TVDB_KEY" },
  "tmdb":      { "api_key": "YOUR_TMDB_KEY" },
  "fanart_tv": { "api_key": "YOUR_FANART_TV_KEY" }
}
```

Find your Plex library key: in Plex Web, open the library and note the number in the URL (`/library/sections/2/`).

### 3. Test Run

```bash
python3 metadata-generator/plex_metadata_generator.py \
  --config /etc/plex-metadata-generator.conf \
  --media-type all --debug
```

### 4. Enable Scheduling

**macOS (LaunchAgent — runs daily at 2 AM):**
```bash
bash metadata-generator/scheduling/install-macos.sh
```

**Linux (systemd timer):**
```bash
bash metadata-generator/scheduling/install-linux.sh
sudo systemctl enable plex-metadata-generator.timer
sudo systemctl start plex-metadata-generator.timer
```

**Windows (Task Scheduler):**
```powershell
.\metadata-generator\scheduling\install-windows.ps1
```

### 5. Health Check

```bash
python3 metadata-generator/health-check.py
```

This verifies your configuration, tests API connectivity (including FanArt.tv), checks scheduling status, and reports recent log activity.
