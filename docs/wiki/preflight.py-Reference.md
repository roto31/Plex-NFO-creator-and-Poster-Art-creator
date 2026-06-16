# preflight.py Reference

## Overview

`preflight.py` is a shared support module imported by all three scripts in this suite. It runs before any processing begins and is responsible for:

1. **Dependency checks** — verifying Python version, ffmpeg/ffprobe availability, API keys, and write permissions
2. **OS-native notifications and dialogs** — system notifications on completion, and Yes/No install dialogs when dependencies are missing
3. **Automatic installation** — installing ffmpeg via the platform's native package manager if the user consents
4. **Logging** — writing a timestamped log file per run to the OS-native log directory
5. **Progress window** — a dark-themed GUI window with a live progress bar, scrollable log, and Cancel/Open Log buttons

`preflight.py` uses only the Python standard library — no `pip install` is required.

---

## How It Is Used

`preflight.py` is not run directly. It is imported by `scraper.py`, `extract_artwork.py`, and `rename_movies.py`:

```python
import preflight

logger, log_file = preflight.setup_logging("scraper")

if not preflight.check_python_version(logger=logger): sys.exit(1)
if not preflight.check_api_keys(TMDB_KEY, TVDB_KEY, logger=logger): sys.exit(1)
if not preflight.check_ffmpeg(logger=logger): sys.exit(1)
if not preflight.check_write_permission(path, logger=logger): sys.exit(1)

win = preflight.ProgressWindow(title="Plex NFO Creator", total=total, log_file=log_file)
win.run(work_function)
```

---

## Startup Sequence

When any script runs, the following checks execute in order:

```
1. check_python_version()   → must be 3.8+
2. check_api_keys()         → TMDB + TVDB keys must be set (scraper.py only)
3. check_ffmpeg()           → ffmpeg must be on PATH (extract_artwork.py only)
4. check_write_permission() → target directory must be writable (when writing files)
5. ProgressWindow.run()     → launch GUI and begin processing
```

If any check fails, the script exits with a clear error message written to the log file and terminal.

---

## Dependency Check — ffmpeg

`check_ffmpeg()` uses `shutil.which("ffmpeg")` to detect whether ffmpeg is on the system PATH. This is the same mechanism used by the shell — if `ffmpeg` is not on PATH, the script will not find it regardless of where it is installed on disk.

> **Important:** Simply downloading the ffmpeg binary is not sufficient. It must be installed to a directory that is on your system PATH. The auto-installer handles this correctly. If you install manually, follow the PATH instructions printed by the script.

### When ffmpeg Is Missing

1. An OS-native dialog appears asking: **"ffmpeg is required. Install it automatically?"**
2. **If Yes:** the auto-installer runs (see [Auto-Installation](#auto-installation))
3. **If No:** detailed manual instructions are printed to the terminal and log, and the ffmpeg download page is opened in your default browser

---

## Auto-Installation

When the user consents to automatic installation, the script detects the platform and uses the appropriate package manager:

| Platform | Install method | What happens |
|----------|---------------|--------------|
| macOS | Homebrew (`brew install ffmpeg`) | Homebrew is installed first if not present, then ffmpeg |
| Linux (Debian/Ubuntu) | `apt-get install -y ffmpeg` | Runs with `sudo` |
| Linux (Fedora/RHEL) | `dnf install -y ffmpeg` | Runs with `sudo` |
| Linux (Arch/Manjaro) | `pacman -S --noconfirm ffmpeg` | Runs with `sudo` |
| Linux (openSUSE) | `zypper install -y ffmpeg` | Runs with `sudo` |
| Linux (Homebrew) | `brew install ffmpeg` | Fallback if no system package manager |
| Windows | `winget install ffmpeg`, then `choco install ffmpeg` | Tries winget first, falls back to Chocolatey |

Install output is streamed line by line into the log window in real time.

After installation completes, `check_ffmpeg()` is called again to verify the install succeeded. If ffmpeg is still not found on PATH after installation, manual instructions are printed.

---

## OS-Native Notifications

`notify(title, message)` sends a system notification banner at the end of each run.

| Platform | Mechanism | Opens in |
|----------|-----------|---------|
| macOS | AppleScript `display notification` | Notification Center |
| Linux | `notify-send` command | Desktop notification daemon |
| Windows | PowerShell `System.Windows.Forms.NotifyIcon` | System tray |

Notifications fire even if the progress window is closed, and include the done/errors/skipped counts.

---

## OS-Native Dialogs

`show_dialog(title, message) → bool` presents a Yes/No dialog to the user.

| Platform | Mechanism |
|----------|-----------|
| macOS | AppleScript `display dialog` with "Yes" / "No" buttons |
| Linux | `zenity --question` (GNOME) or `kdialog --yesno` (KDE) |
| Windows | PowerShell `System.Windows.Forms.MessageBox` |

Returns `True` if the user clicked Yes/Install, `False` if No/Cancel.

---

## Log Files

Each script run writes one log file. Log files are never overwritten — a new file is created per run with a timestamp in the name.

### Log Directories

| Platform | Log Directory |
|----------|--------------|
| macOS | `~/Library/Logs/PlexNFOCreator/` |
| Linux | `~/.local/share/plex-nfo-creator/logs/` |
| Windows | `%APPDATA%\PlexNFOCreator\Logs\` |

### Log File Naming

```
scraper_2026-06-16_143022.log
extract_artwork_2026-06-16_151437.log
rename_movies_2026-06-16_163500.log
```

Format: `<script-name>_YYYY-MM-DD_HHMMSS.log`

### Log Format

```
2026-06-16 14:30:22,841 [INFO    ] Mode: movies  Path: /Volumes/iTunes 5/Movies  Force: False
2026-06-16 14:30:22,843 [INFO    ] Python 3.12.3 — OK
2026-06-16 14:30:22,844 [INFO    ] API keys set — OK
2026-06-16 14:30:22,845 [INFO    ] Write permission OK: /Volumes/iTunes 5/Movies
2026-06-16 14:30:23,112 [INFO    ] [1/1760] ✓  Back to the Future (1985)
2026-06-16 14:30:23,884 [INFO    ] [2/1760] ✓  Batman (1989)
2026-06-16 14:30:24,201 [WARNING ] [3/1760] ✗  Batman (1943) — not found
2026-06-16 14:58:10,003 [INFO    ] Finished — done=1625 errors=75 skipped=60
```

### Opening Logs

The **Open Log** button in the progress window opens the log file in the OS-native log viewer:

| Platform | Application |
|----------|------------|
| macOS | Console.app (log appears under "~/Library/Logs") |
| Linux | Opens in the default text editor |
| Windows | Opens in Notepad |

You can also open logs manually:
- **macOS:** Open Console.app → click "~/Library/Logs" in the sidebar → PlexNFOCreator
- **Linux:** `cat ~/.local/share/plex-nfo-creator/logs/scraper_2026-06-16_143022.log`
- **Windows:** Navigate to `%APPDATA%\PlexNFOCreator\Logs\` in Explorer

---

## Progress Window

The `ProgressWindow` class creates a dark-themed tkinter GUI that displays during processing.

### Window Layout

```
┌─────────────────────────────────────────────────────────┐
│  Plex NFO Creator — Movies                              │
├─────────────────────────────────────────────────────────┤
│  [████████████████████░░░░░░░░░░░░░]  847 / 1760       │
│  ✓ Done: 820   ✗ Errors: 15   ⏭ Skipped: 12           │
├─────────────────────────────────────────────────────────┤
│  14:30:23  ✓  Back to the Future (1985)                 │
│  14:30:24  ✓  Batman (1989)                             │
│  14:30:24  ✗  Batman (1943) — not found                 │
│  14:30:25  ⏭  Batman Begins (2005) — already done       │
│  ...                                                    │
├─────────────────────────────────────────────────────────┤
│  [Cancel]                            [Open Log]         │
└─────────────────────────────────────────────────────────┘
```

### Color Scheme (VS Code Dark+)

| Element | Color |
|---------|-------|
| Background | `#1e1e1e` |
| Log text (info) | `#d4d4d4` (light grey) |
| Log text (success `✓`) | `#4ec9b0` (teal) |
| Log text (warning `⚠`) | `#dcdcaa` (yellow) |
| Log text (error `✗`) | `#f44747` (red) |
| Progress bar | `#0e70c0` (blue) |

### Threading Model

The progress window runs the tkinter `mainloop()` on the **main thread** (required on macOS/Cocoa). The processing work runs in a **background daemon thread**. Communication between threads uses a `queue.Queue` — the window polls the queue every 100ms via `root.after(100, _poll)`.

This design ensures:
- The GUI remains responsive during processing
- Cancel is near-instant (sets a threading Event that the worker checks per item)
- The window can be closed without killing the process abruptly

### Headless Fallback

If tkinter is unavailable (headless server, minimal Python install), `ProgressWindow.run()` automatically detects this and calls the work function directly in the current thread with `None` callbacks. Output falls back to terminal print statements.

---

## API Reference

### `setup_logging(script_name) → (logger, log_file_path)`

Creates the log directory (if it doesn't exist), opens a new timestamped log file, and configures a Python `logging.Logger` with both a file handler and a stderr handler.

```python
logger, log_file = preflight.setup_logging("scraper")
logger.info("Processing started")
logger.warning("Item not found")
logger.error("Write failed")
```

---

### `check_python_version(logger=None) → bool`

Verifies `sys.version_info >= (3, 8)`. Returns `True` if the version is sufficient, `False` otherwise (with the error logged and printed).

---

### `check_api_keys(tmdb_key, tvdb_key, logger=None) → bool`

Verifies that neither key is empty or a placeholder string (e.g. `"your_key_here"`). Returns `True` if both are set.

---

### `check_ffmpeg(logger=None) → bool`

Uses `shutil.which("ffmpeg")` to test PATH availability. If not found:
1. Calls `notify()` to alert the user
2. Calls `show_dialog()` to ask permission to auto-install
3. If Yes: calls `_auto_install_ffmpeg()`, then re-checks
4. If No: calls `show_manual_ffmpeg_instructions()` and opens the download page
5. Returns `True` if ffmpeg is on PATH after the check (or after install)

---

### `check_write_permission(path, logger=None) → bool`

Attempts to create and immediately delete a temporary file at the target path. Returns `True` if the write succeeds, `False` with a logged error if it fails (e.g. permissions, read-only volume).

---

### `notify(title, message)`

Sends an OS-native notification. Silently no-ops if the notification mechanism is unavailable.

---

### `show_dialog(title, message) → bool`

Shows an OS-native Yes/No dialog. Returns `True` for Yes. Falls back to a `tkinter.messagebox` if OS-native dialogs are unavailable.

---

### `show_manual_ffmpeg_instructions()`

Prints detailed, platform-specific installation instructions to the terminal and log, including explicit PATH setup instructions and the ffmpeg download URL.

---

### `open_log_in_viewer(log_file_path)`

Opens the log file in the appropriate viewer: Console.app on macOS, the default text editor on Linux, and Notepad on Windows.

---

### `ProgressWindow(title, total, log_file)`

Constructor. Does not open the window — call `.run()` to start.

| Parameter | Type | Description |
|-----------|------|-------------|
| `title` | `str` | Window title bar text |
| `total` | `int` | Total number of items to process |
| `log_file` | `str` | Path to the current run's log file (for the Open Log button) |

---

### `ProgressWindow.run(work_fn, *args, **kwargs) → (done, errors, skipped)`

Builds the tkinter UI, starts `work_fn` in a daemon thread, and enters `mainloop()`. Blocks until processing is complete or the window is closed.

`work_fn` receives three keyword arguments injected by the framework:

| Kwarg | Type | Description |
|-------|------|-------------|
| `progress_cb` | `callable` or `None` | Call with `(current, total, name, status, done, errors, skipped)` to update the progress bar and counters |
| `log_cb` | `callable` or `None` | Call with `(message, level)` to write a line to the scrollable log. `level` is `"info"`, `"warning"`, or `"error"` |
| `cancel` | `callable` or `None` | Call with no args; returns `True` if the Cancel button has been pressed |

```python
def work(progress_cb, log_cb, cancel):
    for idx, item in enumerate(items, 1):
        if cancel and cancel():
            break
        result = process(item)
        log_cb(f"✓ {item}", "info")
        progress_cb(idx, total, item, "done", done, errors, skipped)
    return done, errors, skipped

win.run(work)
```

Returns `(done, errors, skipped)` — the tuple returned by `work_fn`.

---

## Functions Reference

| Function | Description |
|----------|-------------|
| `log_directory()` | Returns the OS-appropriate log directory path as a `Path` object |
| `setup_logging(script_name)` | Create log dir, open log file, configure logger; returns `(logger, log_file)` |
| `open_log_in_viewer(log_file)` | Open log file in OS-native viewer |
| `notify(title, message)` | Send OS-native notification banner |
| `show_dialog(title, message)` | Show OS-native Yes/No dialog; returns bool |
| `show_manual_ffmpeg_instructions()` | Print platform-specific PATH install instructions |
| `_stream_install(cmd)` | Run install command, stream output line by line |
| `_auto_install_ffmpeg()` | Detect platform, run package manager, verify success |
| `check_ffmpeg(logger)` | Check PATH + offer install if missing; returns bool |
| `check_python_version(logger)` | Verify Python ≥ 3.8; returns bool |
| `check_api_keys(tmdb, tvdb, logger)` | Verify keys are non-empty non-placeholder; returns bool |
| `check_write_permission(path, logger)` | Write-test the target directory; returns bool |
| `ProgressWindow.__init__(title, total, log_file)` | Initialize window (does not open it) |
| `ProgressWindow.run(work_fn, ...)` | Open window, run work in thread, block until done |
| `ProgressWindow.update(...)` | Thread-safe: enqueue a progress update |
| `ProgressWindow.log(message, level)` | Thread-safe: enqueue a log line |
| `ProgressWindow.done(done, errors, skipped)` | Thread-safe: signal completion |

---

## Platform Notes

### macOS

- Notification Center permission may be required the first time AppleScript sends a notification. macOS will prompt for this automatically.
- The AppleScript dialog (`display dialog`) blocks until the user clicks — this is intentional so the script waits for the user's install decision.
- Log files appear in Console.app under **Reports** → expand `~/Library/Logs` → `PlexNFOCreator`.
- tkinter on macOS requires the Python distributed by python.org or Homebrew (`brew install python-tk`). The system Python on macOS does not include tkinter. If tkinter is not available, the script falls back to terminal output.

### Linux

- `notify-send` must be installed for notifications (`apt install libnotify-bin` on Debian/Ubuntu).
- For GUI dialogs, `zenity` (GNOME) or `kdialog` (KDE) must be installed. On headless systems, dialogs are skipped and the install proceeds automatically if the user passed `-y` or confirmed via terminal.
- Log files are at `~/.local/share/plex-nfo-creator/logs/` and can be viewed with any text editor or `cat`.

### Windows

- PowerShell 5+ is required for notifications and dialogs (included in Windows 10/11).
- `winget` is included in Windows 10 (1709+) and Windows 11. Chocolatey is the fallback.
- Log files are at `%APPDATA%\PlexNFOCreator\Logs\` — type this path directly into Explorer's address bar.
- The scripts must be run from a terminal with Python on PATH. If `python` is not recognized, install Python from python.org and check "Add Python to PATH" during installation.
