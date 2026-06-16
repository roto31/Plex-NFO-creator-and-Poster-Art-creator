# preflight.py — Reference Documentation

## Overview

`preflight.py` is a shared support module imported by all three processing scripts. It is not run directly.

It runs before any processing begins and provides:
- Dependency checks (Python version, ffmpeg on PATH, API keys, write permissions)
- OS-native notifications and Yes/No install dialogs
- Automatic ffmpeg installation via platform package managers
- Per-run log files written to the OS-native log directory
- A dark-themed tkinter progress window with real-time logging

See the full reference in the [Wiki: preflight.py Reference](https://github.com/roto31/Plex-NFO-creator-and-Poster-Art-creator/wiki/preflight.py-Reference).

---

## Log File Locations

| Platform | Directory |
|----------|-----------|
| macOS | `~/Library/Logs/PlexNFOCreator/` |
| Linux | `~/.local/share/plex-nfo-creator/logs/` |
| Windows | `%APPDATA%\PlexNFOCreator\Logs\` |

One log file is written per run: `<script-name>_YYYY-MM-DD_HHMMSS.log`

---

## Auto-Install Decision Flow

When `extract_artwork.py` starts and ffmpeg is not on PATH:

1. OS-native notification: "ffmpeg is required"
2. OS-native dialog: "Install automatically?" — Yes / No
3. **Yes:** install via platform package manager, re-check PATH
4. **No:** print PATH instructions, open ffmpeg download page in browser, exit

Package managers used:

| Platform | Manager |
|----------|---------|
| macOS | Homebrew (installed first if missing) |
| Linux | apt, dnf, pacman, zypper, or brew — whichever is detected |
| Windows | winget, then Chocolatey |

---

## Progress Window

All three scripts open a tkinter progress window showing:
- Progress bar with `current / total` count
- Done / Errors / Skipped counters
- Scrollable timestamped log (VS Code Dark+ color theme)
- **Cancel** button — stops after the current item
- **Open Log** button — opens the run log in the OS-native viewer

Falls back to terminal output if tkinter is unavailable.

---

## Public API

```python
import preflight

# Logging
logger, log_file = preflight.setup_logging("script_name")

# Checks (each returns bool; logs and prints on failure)
preflight.check_python_version(logger=logger)
preflight.check_api_keys(tmdb_key, tvdb_key, logger=logger)
preflight.check_ffmpeg(logger=logger)
preflight.check_write_permission(path, logger=logger)

# Notifications
preflight.notify("Title", "Message")

# Progress window
win = preflight.ProgressWindow(title="...", total=n, log_file=log_file)
done, errors, skipped = win.run(work_fn)
# work_fn receives: progress_cb, log_cb, cancel kwargs
```
