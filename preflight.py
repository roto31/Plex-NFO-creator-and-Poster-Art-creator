#!/usr/bin/env python3
"""
preflight.py — Startup dependency checks, OS-native notifications, auto-install,
tkinter progress window, and system logging for the Plex NFO Creator suite.

  macOS   — Dialogs via AppleScript. Notifications via Notification Centre.
             Logs written to ~/Library/Logs/PlexNFOCreator/ (open in Console.app).
  Linux   — Dialogs via zenity or kdialog. Notifications via notify-send.
             Logs written to ~/.local/share/plex-nfo-creator/logs/.
  Windows — Dialogs via PowerShell MessageBox. Notifications via system tray balloon.
             Logs written to %APPDATA%\\PlexNFOCreator\\Logs\\.

All three scripts (scraper.py, extract_artwork.py, rename_movies.py) import this
module and call run_preflight() at startup.
"""

import os
import sys
import subprocess
import platform
import logging
import webbrowser
import queue
import threading
import shutil
from pathlib import Path
from datetime import datetime

# ─── Platform ─────────────────────────────────────────────────────────────────

SYSTEM = platform.system()   # 'Darwin', 'Linux', 'Windows'

# ─── Logging ──────────────────────────────────────────────────────────────────

def log_directory() -> Path:
    """Return the OS-native log directory for this suite, creating it if needed.

    macOS   → ~/Library/Logs/PlexNFOCreator/
    Windows → %APPDATA%/PlexNFOCreator/Logs/
    Linux   → ~/.local/share/plex-nfo-creator/logs/
    """
    if SYSTEM == "Darwin":
        d = Path.home() / "Library" / "Logs" / "PlexNFOCreator"
    elif SYSTEM == "Windows":
        d = Path(os.environ.get("APPDATA", Path.home())) / "PlexNFOCreator" / "Logs"
    else:
        d = Path.home() / ".local" / "share" / "plex-nfo-creator" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def setup_logging(script_name: str):
    """
    Configure Python logging to write to the OS-native log location.
    Returns (logger, log_file_path).

    Log format:  2026-06-16 14:32:01  [INFO    ]  message text
    The log file is named <script>_YYYY-MM-DD_HHMMSS.log so each run
    produces its own file and old runs are never overwritten.

    macOS: open ~/Library/Logs/PlexNFOCreator/ in Console.app to view all logs.
    """
    ts       = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_file = log_directory() / f"{script_name}_{ts}.log"

    fmt = logging.Formatter(
        fmt="%(asctime)s  [%(levelname)-8s]  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger(script_name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Warnings and above also appear on stderr so they're visible in terminals
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.WARNING)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    logger.info("=" * 72)
    logger.info(f"Plex NFO Creator — {script_name} — session started")
    logger.info(f"Platform : {platform.platform()}")
    logger.info(f"Python   : {sys.version.split()[0]}")
    logger.info(f"Log file : {log_file}")
    logger.info("=" * 72)

    return logger, log_file


def open_log_in_viewer(log_file: Path):
    """Open the log file in the OS-native log viewer."""
    try:
        if SYSTEM == "Darwin":
            # Console.app is the native log viewer; -a forces it to open the file
            subprocess.Popen(["open", "-a", "Console", str(log_file)])
        elif SYSTEM == "Windows":
            os.startfile(str(log_file))          # opens in default text app
        else:
            # Try common Linux text editors/viewers in order of preference
            for app in ("gnome-text-editor", "gedit", "kate", "mousepad",
                        "xed", "featherpad", "xdg-open"):
                if shutil.which(app):
                    subprocess.Popen([app, str(log_file)])
                    return
    except Exception:
        pass


# ─── OS-native notifications (fire-and-forget banner) ─────────────────────────

def _notify_macos(title: str, message: str):
    script = f'display notification "{_esc(message)}" with title "{_esc(title)}"'
    subprocess.Popen(["osascript", "-e", script],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _notify_linux(title: str, message: str):
    if shutil.which("notify-send"):
        subprocess.Popen(
            ["notify-send", "--urgency=critical", "--icon=dialog-warning", title, message],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def _notify_windows(title: str, message: str):
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$n = New-Object System.Windows.Forms.NotifyIcon; "
        "$n.Icon = [System.Drawing.SystemIcons]::Warning; "
        "$n.Visible = $true; "
        f"$n.ShowBalloonTip(6000, '{_esc_ps(title)}', '{_esc_ps(message)}', "
        "[System.Windows.Forms.ToolTipIcon]::Warning); "
        "Start-Sleep 3; $n.Dispose()"
    )
    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def notify(title: str, message: str):
    """Send an OS-native informational notification banner (non-blocking)."""
    try:
        if SYSTEM == "Darwin":
            _notify_macos(title, message)
        elif SYSTEM == "Windows":
            _notify_windows(title, message)
        else:
            _notify_linux(title, message)
    except Exception:
        pass  # Notifications are best-effort


# ─── OS-native Yes / No dialogs ───────────────────────────────────────────────

def _esc(s: str) -> str:
    """Escape a string for use inside AppleScript double-quoted strings."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _esc_ps(s: str) -> str:
    """Escape a string for use inside PowerShell single-quoted strings."""
    return s.replace("'", "''")


def _dialog_macos(title: str, message: str) -> bool:
    """AppleScript modal dialog with Yes / No buttons. Returns True for Yes."""
    script = (
        f'tell application "System Events"\n'
        f'    activate\n'
        f'    set r to display dialog "{_esc(message)}" '
        f'buttons {{"No", "Yes"}} default button "Yes" '
        f'with title "{_esc(title)}" with icon caution\n'
        f'    return button returned of r\n'
        f'end tell'
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=120,
        )
        return result.stdout.strip() == "Yes"
    except Exception:
        return _dialog_terminal(title, message)


def _dialog_linux(title: str, message: str) -> bool:
    """zenity or kdialog yes/no dialog. Returns True for Yes."""
    if shutil.which("zenity"):
        try:
            r = subprocess.run(
                ["zenity", "--question", "--title", title,
                 "--text", message, "--width", "520", "--height", "200"],
                timeout=120,
            )
            return r.returncode == 0
        except Exception:
            pass
    if shutil.which("kdialog"):
        try:
            r = subprocess.run(
                ["kdialog", "--yesno", message, "--title", title],
                timeout=120,
            )
            return r.returncode == 0
        except Exception:
            pass
    return _dialog_terminal(title, message)


def _dialog_windows(title: str, message: str) -> bool:
    """PowerShell MessageBox yes/no dialog. Returns True for Yes."""
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$r = [System.Windows.Forms.MessageBox]::Show("
        f"'{_esc_ps(message)}', '{_esc_ps(title)}', "
        "[System.Windows.Forms.MessageBoxButtons]::YesNo, "
        "[System.Windows.Forms.MessageBoxIcon]::Question); "
        "if ($r -eq 'Yes') { exit 0 } else { exit 1 }"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            timeout=120,
        )
        return r.returncode == 0
    except Exception:
        return _dialog_terminal(title, message)


def _dialog_terminal(title: str, message: str) -> bool:
    """Plain-terminal fallback when no GUI dialog is available."""
    sep = "─" * 64
    print(f"\n{sep}\n  {title}\n{sep}\n{message}\n{sep}", flush=True)
    try:
        ans = input("  Install now? [y/N]: ").strip().lower()
        return ans in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def show_dialog(title: str, message: str) -> bool:
    """Show a yes/no dialog using the OS-native mechanism."""
    if SYSTEM == "Darwin":
        return _dialog_macos(title, message)
    elif SYSTEM == "Windows":
        return _dialog_windows(title, message)
    else:
        return _dialog_linux(title, message)


# ─── Manual install instructions ──────────────────────────────────────────────

_FFMPEG_URLS = {
    "Darwin":  "https://ffmpeg.org/download.html#build-mac",
    "Linux":   "https://ffmpeg.org/download.html#build-linux",
    "Windows": "https://www.gyan.dev/ffmpeg/builds/",
}

_FFMPEG_INSTRUCTIONS = {
    "Darwin": """\

  Manual ffmpeg installation — macOS
  ────────────────────────────────────────────────────────────────
  ffmpeg and ffprobe must be installed and reachable on your PATH.
  The script checks your PATH at startup — placing the binaries in
  your Downloads folder or Desktop will not work.

  Option 1 — Homebrew (recommended):
    1. Install Homebrew if you do not already have it:
         /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    2. Install ffmpeg (also installs ffprobe automatically):
         brew install ffmpeg
    3. Verify:  ffmpeg -version

  Option 2 — Pre-built static binary:
    Download page:  https://evermeet.cx/ffmpeg/
    1. Download both  ffmpeg  and  ffprobe
    2. Move them to /usr/local/bin/:
         sudo mv ffmpeg ffprobe /usr/local/bin/
         sudo chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe
    3. Verify:  ffmpeg -version

  PATH tip: run  echo $PATH  in Terminal to see your current PATH.
  ────────────────────────────────────────────────────────────────
""",
    "Linux": """\

  Manual ffmpeg installation — Linux
  ────────────────────────────────────────────────────────────────
  ffmpeg and ffprobe must be installed and reachable on your PATH.
  Run  which ffmpeg  to check if it is already installed.

  Debian / Ubuntu / Linux Mint:
    sudo apt update && sudo apt install ffmpeg

  Fedora / RHEL / CentOS (RPM Fusion required):
    sudo dnf install ffmpeg

  Arch Linux / Manjaro:
    sudo pacman -S ffmpeg

  openSUSE:
    sudo zypper install ffmpeg

  Static build (any distro — no root needed):
    https://johnvansickle.com/ffmpeg/
    1. Download the release build for your architecture
    2. Extract:  tar xf ffmpeg-release-amd64-static.tar.xz
    3. Copy both binaries to ~/.local/bin/:
         mkdir -p ~/.local/bin
         cp ffmpeg-*/ffmpeg ffmpeg-*/ffprobe ~/.local/bin/
         chmod +x ~/.local/bin/ffmpeg ~/.local/bin/ffprobe
    4. Ensure ~/.local/bin is on your PATH:
         echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
         source ~/.bashrc
    5. Verify:  ffmpeg -version

  PATH tip: run  echo $PATH  in your shell to see your current PATH.
  ────────────────────────────────────────────────────────────────
""",
    "Windows": """\

  Manual ffmpeg installation — Windows
  ────────────────────────────────────────────────────────────────
  ffmpeg.exe and ffprobe.exe must be installed and on your system
  PATH. The script will NOT find them if they are only in your
  Downloads folder — they must be on the PATH to be discovered.

  Option 1 — winget (Windows 10 1709+ / Windows 11):
    Open PowerShell or Command Prompt and run:
      winget install --id Gyan.FFmpeg -e --accept-source-agreements

  Option 2 — Chocolatey:
      choco install ffmpeg

  Option 3 — Manual download:
    Download page:  https://www.gyan.dev/ffmpeg/builds/
    1. Download "ffmpeg-release-essentials.zip"
    2. Extract the zip — locate ffmpeg.exe and ffprobe.exe inside the bin\\ folder
    3. Create a permanent location, e.g.:  C:\\ffmpeg\\bin\\
    4. Copy ffmpeg.exe and ffprobe.exe to  C:\\ffmpeg\\bin\\
    5. Add C:\\ffmpeg\\bin\\ to your system PATH:
         Windows key → "Environment Variables" → System Variables →
         Path → Edit → New → type  C:\\ffmpeg\\bin\\  → OK
    6. Open a NEW Command Prompt window (existing ones won't see the change)
    7. Verify:  ffmpeg -version

  PATH tip: run  echo %PATH%  in Command Prompt to see your current PATH.
  ────────────────────────────────────────────────────────────────
""",
}


def show_manual_ffmpeg_instructions():
    """Print platform-specific manual install instructions and open the download page."""
    print(_FFMPEG_INSTRUCTIONS.get(SYSTEM, _FFMPEG_INSTRUCTIONS["Linux"]))
    url = _FFMPEG_URLS.get(SYSTEM, _FFMPEG_URLS["Linux"])
    print(f"  Opening download page in your browser: {url}\n")
    webbrowser.open(url)


# ─── Auto-install helpers ─────────────────────────────────────────────────────

def _stream_install(cmd: list, logger=None) -> bool:
    """Run an install command, streaming its output line by line. Returns True on success."""
    print(f"\n  Running: {' '.join(cmd)}\n", flush=True)
    if logger:
        logger.info(f"Auto-install command: {' '.join(cmd)}")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in proc.stdout:
            line = line.rstrip()
            print(f"    {line}", flush=True)
            if logger:
                logger.info(f"[install] {line}")
        proc.wait()
        ok = proc.returncode == 0
        if logger:
            logger.info(f"Install exit code: {proc.returncode} ({'success' if ok else 'FAILED'})")
        return ok
    except Exception as exc:
        msg = f"Install command failed: {exc}"
        print(f"  ❌ {msg}", flush=True)
        if logger:
            logger.error(msg)
        return False


def _detect_linux_pm():
    """Return (pm_name, ffmpeg_install_cmd) for the first available package manager."""
    candidates = [
        ("apt",    ["sudo", "apt", "install", "-y", "ffmpeg"]),
        ("dnf",    ["sudo", "dnf", "install", "-y", "ffmpeg"]),
        ("pacman", ["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"]),
        ("zypper", ["sudo", "zypper", "install", "-y", "ffmpeg"]),
        ("brew",   ["brew", "install", "ffmpeg"]),  # Linuxbrew
    ]
    for name, cmd in candidates:
        if shutil.which(name):
            return name, cmd
    return None, None


def _auto_install_ffmpeg(logger=None) -> bool:
    """Run the platform-appropriate ffmpeg auto-installer. Returns True on success."""
    if SYSTEM == "Darwin":
        if not shutil.which("brew"):
            print("\n  Homebrew is not installed. Installing Homebrew first…", flush=True)
            if logger:
                logger.info("Homebrew not found — installing Homebrew first")
            brew_cmd = [
                "/bin/bash", "-c",
                'curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | bash'
            ]
            if not _stream_install(brew_cmd, logger):
                print("  ❌ Homebrew install failed. Please install manually: https://brew.sh", flush=True)
                return False
            print("  ✓ Homebrew installed.\n", flush=True)
        return _stream_install(["brew", "install", "ffmpeg"], logger)

    elif SYSTEM == "Windows":
        if shutil.which("winget"):
            ok = _stream_install(
                ["winget", "install", "--id", "Gyan.FFmpeg", "-e",
                 "--accept-source-agreements", "--accept-package-agreements"],
                logger,
            )
            if ok:
                return True
        if shutil.which("choco"):
            return _stream_install(["choco", "install", "ffmpeg", "-y"], logger)
        print("  ❌ Neither winget nor Chocolatey found on this system.", flush=True)
        if logger:
            logger.error("Auto-install: no package manager available on Windows")
        return False

    else:  # Linux
        pm_name, cmd = _detect_linux_pm()
        if not pm_name:
            print("  ❌ No supported package manager found (apt / dnf / pacman / zypper).", flush=True)
            if logger:
                logger.error("Auto-install: no supported Linux package manager found")
            return False
        print(f"  Detected package manager: {pm_name}", flush=True)
        return _stream_install(cmd, logger)


# ─── Dependency checks ────────────────────────────────────────────────────────

def check_ffmpeg(logger=None) -> bool:
    """
    Verify that ffmpeg and ffprobe are on PATH.

    If either is missing:
      • Sends an OS-native notification banner
      • Shows a yes/no dialog:
          Yes → auto-install using the platform package manager
          No  → print detailed manual instructions + open download page in browser

    Returns True only when both ffmpeg and ffprobe are confirmed on PATH.
    The script WILL NOT function correctly without them — ffprobe performs the
    dry-run artwork probe and ffmpeg performs the actual extraction.
    """
    ffmpeg_ok  = bool(shutil.which("ffmpeg"))
    ffprobe_ok = bool(shutil.which("ffprobe"))

    if ffmpeg_ok and ffprobe_ok:
        if logger:
            logger.info(f"ffmpeg  found: {shutil.which('ffmpeg')}")
            logger.info(f"ffprobe found: {shutil.which('ffprobe')}")
        return True

    missing = [t for t, ok in [("ffmpeg", ffmpeg_ok), ("ffprobe", ffprobe_ok)] if not ok]
    missing_str = " and ".join(missing)

    if logger:
        logger.warning(f"Missing dependencies: {missing_str}")

    notify(
        "Plex NFO Creator — Missing Dependency",
        f"{missing_str} not found on PATH. Artwork extraction cannot run without it.",
    )

    dialog_msg = (
        f"{missing_str} is required but was not found on your system PATH.\n\n"
        f"extract_artwork.py calls ffmpeg to read the artwork stream embedded inside "
        f"your MP4 and MKV files, and ffprobe to detect whether artwork is present "
        f"during dry-run mode. Neither tool is optional.\n\n"
        f"IMPORTANT: {missing_str} must be installed in a standard system location "
        f"and be reachable on your PATH. Placing the files in your Downloads folder, "
        f"Desktop, or any folder not on the PATH will not work — the script will not "
        f"find them there.\n\n"
        f"Would you like to install {missing_str} automatically now?"
    )

    user_said_yes = show_dialog(f"Missing: {missing_str}", dialog_msg)

    if user_said_yes:
        print(f"\n  Installing {missing_str}…", flush=True)
        if logger:
            logger.info(f"User chose auto-install for {missing_str}")

        ok = _auto_install_ffmpeg(logger)

        if ok and shutil.which("ffmpeg"):
            print(f"\n  ✓ ffmpeg is now available at: {shutil.which('ffmpeg')}", flush=True)
            if logger:
                logger.info(f"ffmpeg now on PATH: {shutil.which('ffmpeg')}")
            if not shutil.which("ffprobe"):
                # ffprobe usually ships with ffmpeg; if still missing, warn
                print(
                    "  ⚠ ffprobe is still not on PATH. It is included with most ffmpeg "
                    "installations — you may need to open a new terminal window and re-run "
                    "the script for the PATH update to take effect.",
                    flush=True,
                )
                if logger:
                    logger.warning("ffprobe still not on PATH after install — PATH may need reload")
                return False
            return True
        else:
            print("\n  ❌ Automatic installation did not complete successfully.", flush=True)
            print("  Please install manually:", flush=True)
            if logger:
                logger.error("Auto-install failed or ffmpeg still not on PATH after install")
            show_manual_ffmpeg_instructions()
            return False

    else:
        if logger:
            logger.info("User declined auto-install — showing manual instructions")
        show_manual_ffmpeg_instructions()
        return False


def check_python_version(logger=None) -> bool:
    """Verify Python 3.8+ is running. Exits with notification if not."""
    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 8):
        if logger:
            logger.info(f"Python {major}.{minor}: OK")
        return True
    msg = (
        f"Python 3.8 or newer is required. "
        f"You are running Python {major}.{minor}.\n"
        f"Download Python from: https://www.python.org/downloads/"
    )
    print(f"❌ {msg}", flush=True)
    if logger:
        logger.error(msg)
    notify("Plex NFO Creator — Python Version", msg)
    webbrowser.open("https://www.python.org/downloads/")
    return False


def check_api_keys(tmdb_key: str, tvdb_key: str, logger=None) -> bool:
    """
    Verify that API keys in scraper.py are not still set to their placeholder values.
    Opens the relevant API sign-up pages in the browser if keys are missing.
    """
    placeholders = {
        "your_tmdb_api_key_here", "YOUR_TMDB_API_KEY",
        "your_tvdb_api_key_here", "YOUR_TVDB_API_KEY", "YOUR_TVDB_APLI_KEY",
        "", None,
    }
    tmdb_ok = tmdb_key not in placeholders and len(str(tmdb_key)) > 10
    tvdb_ok = tvdb_key not in placeholders and len(str(tvdb_key)) > 10
    missing = [k for k, ok in [("TMDB_API_KEY", tmdb_ok), ("TVDB_API_KEY", tvdb_ok)] if not ok]

    if not missing:
        if logger:
            logger.info("TMDB and TVDB API keys: configured ✓")
        return True

    msg = (
        f"API key(s) not configured: {', '.join(missing)}\n\n"
        f"Open scraper.py in a text editor and replace the placeholder values "
        f"at the top of the file (the TMDB_API_KEY and TVDB_API_KEY lines).\n\n"
        f"  TMDB free key → https://www.themoviedb.org/settings/api\n"
        f"  TVDB free key → https://thetvdb.com/api-information"
    )
    print(f"❌ {msg}", flush=True)
    if logger:
        logger.error(f"API keys not set: {', '.join(missing)}")
    notify("Plex NFO Creator — API Keys Not Set", f"Missing: {', '.join(missing)}")
    if not tmdb_ok:
        webbrowser.open("https://www.themoviedb.org/settings/api")
    if not tvdb_ok:
        webbrowser.open("https://thetvdb.com/api-information")
    return False


def check_write_permission(path: str, logger=None) -> bool:
    """
    Verify the target directory is writable by creating and removing a test file.
    Prints macOS / Linux / Windows instructions if permission is denied.
    """
    p = Path(path)
    probe = p / ".plex_nfo_write_test"
    try:
        probe.touch()
        probe.unlink()
        if logger:
            logger.info(f"Write permission OK: {path}")
        return True
    except Exception as exc:
        if SYSTEM == "Darwin":
            hint = (
                "On macOS: System Settings → Privacy & Security → Files and Folders\n"
                "          Grant Terminal (or your terminal app) access to this location.\n"
                "          Alternatively: Full Disk Access → add Terminal."
            )
        elif SYSTEM == "Windows":
            hint = (
                "On Windows: right-click the folder → Properties → Security tab.\n"
                "            Ensure your user account has Write permission."
            )
        else:
            hint = (
                f"On Linux: check permissions with:  ls -la \"{path}\"\n"
                f"          Fix with:  chmod u+w \"{path}\""
            )
        msg = f"Cannot write to: {path}\nError: {exc}\n{hint}"
        print(f"❌ {msg}", flush=True)
        if logger:
            logger.error(f"Write permission denied: {path}: {exc}")
        notify("Plex NFO Creator — Permission Denied", f"Cannot write to: {path}")
        return False


# ─── Progress Window ──────────────────────────────────────────────────────────

try:
    import tkinter as tk
    from tkinter import ttk
    import tkinter.font as tkfont
    _TK_AVAILABLE = True
except ImportError:
    _TK_AVAILABLE = False

# Pick monospace font for the log area
_MONO_FONT = (
    "Menlo"            if SYSTEM == "Darwin"  else
    "Consolas"         if SYSTEM == "Windows" else
    "DejaVu Sans Mono"
)


class ProgressWindow:
    """
    A dark-themed tkinter progress window.

    Work runs in a background thread; the UI updates every 100 ms via a queue.
    Falls back to plain terminal output if tkinter is unavailable (headless Linux).

    Usage:

        def my_work(progress_cb, log_cb, cancel_event):
            for i, item in enumerate(items):
                if cancel_event.is_set():
                    break
                # … do work …
                status = "done"  # or "error" / "skipped"
                progress_cb(i + 1, total, item_name, status, done, errors, skipped)
                log_cb(f"[{i+1}/{total}] processed {item_name}", level=status)
            return done, errors, skipped

        win = ProgressWindow("Plex NFO Creator — Movies", total=1760, log_file=log_file)
        win.run(my_work)   # blocks until complete or cancelled
    """

    # Log colours (VS Code Dark+ palette)
    _COLOURS = {
        "done":    "#4ec9b0",   # teal
        "error":   "#f48771",   # salmon
        "skipped": "#808080",   # grey
        "warning": "#dcdcaa",   # yellow
        "info":    "#d4d4d4",   # off-white
        "header":  "#569cd6",   # blue
    }

    def __init__(self, title: str, total: int, log_file: Path = None):
        self._title     = title
        self._total     = max(total, 1)
        self._log_file  = log_file
        self._queue     = queue.Queue()
        self._cancel    = threading.Event()
        self._finished  = threading.Event()
        self._root      = None
        self._available = _TK_AVAILABLE

    # ── Public thread-safe API ────────────────────────────────────────────────

    @property
    def cancel_event(self) -> threading.Event:
        return self._cancel

    def update(self, current: int, total: int, name: str, status: str,
               done: int = 0, errors: int = 0, skipped: int = 0):
        """Report one completed item. Safe to call from any thread."""
        self._queue.put(("progress", current, total, name, status, done, errors, skipped))

    def log(self, message: str, level: str = "info"):
        """Append a line to the log area. Safe to call from any thread."""
        self._queue.put(("log", message, level))

    def done(self, done: int, errors: int, skipped: int):
        """Signal that all work is complete. Safe to call from any thread."""
        self._queue.put(("finish", done, errors, skipped))

    # ── tkinter UI ───────────────────────────────────────────────────────────

    def _build(self):
        self._root = tk.Tk()
        self._root.title(self._title)
        self._root.configure(bg="#1e1e1e")
        self._root.minsize(760, 520)
        self._root.resizable(True, True)
        self._root.protocol("WM_DELETE_WINDOW", self._on_cancel)

        style = ttk.Style(self._root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(".", background="#1e1e1e", foreground="#d4d4d4",
                        fieldbackground="#252526", troughcolor="#3c3c3c")
        style.configure("TFrame",    background="#1e1e1e")
        style.configure("TLabel",    background="#1e1e1e", foreground="#d4d4d4")
        style.configure("TButton",   background="#3c3c3c", foreground="#d4d4d4", padding=4)
        style.configure("TLabelframe",       background="#1e1e1e", foreground="#808080")
        style.configure("TLabelframe.Label", background="#1e1e1e", foreground="#808080")
        style.configure("Horizontal.TProgressbar",
                        troughcolor="#3c3c3c", background="#007acc", thickness=16)

        pad = {"padx": 14, "pady": 6}

        # ── Title ──
        title_lbl = tk.Label(
            self._root, text=self._title,
            font=(_MONO_FONT, 13, "bold"),
            bg="#1e1e1e", fg="#d4d4d4",
        )
        title_lbl.pack(anchor="w", **pad)

        # ── Progress bar row ──
        pbar_frame = tk.Frame(self._root, bg="#1e1e1e")
        pbar_frame.pack(fill=tk.X, padx=14, pady=(0, 2))

        self._pbar = ttk.Progressbar(
            pbar_frame, maximum=self._total,
            mode="determinate", length=600,
        )
        self._pbar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self._pct_var = tk.StringVar(value="  0%")
        tk.Label(pbar_frame, textvariable=self._pct_var, width=5,
                 bg="#1e1e1e", fg="#808080", font=(_MONO_FONT, 10)).pack(side=tk.LEFT)

        # ── Current item ──
        self._current_var = tk.StringVar(value="Initialising…")
        tk.Label(self._root, textvariable=self._current_var,
                 bg="#1e1e1e", fg="#569cd6", font=(_MONO_FONT, 10),
                 anchor="w").pack(fill=tk.X, padx=14, pady=(0, 6))

        # ── Log area ──
        log_frame = tk.LabelFrame(
            self._root, text=" Log ", labelanchor="nw",
            bg="#1e1e1e", fg="#808080", bd=1, relief=tk.SOLID,
        )
        log_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 6))

        self._log = tk.Text(
            log_frame, state="disabled", wrap="none",
            font=(_MONO_FONT, 10),
            bg="#131313", fg="#d4d4d4",
            insertbackground="#d4d4d4",
            selectbackground="#264f78",
            bd=0, relief=tk.FLAT,
        )
        self._log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0), pady=4)

        vsb = ttk.Scrollbar(log_frame, orient="vertical", command=self._log.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._log.configure(yscrollcommand=vsb.set)

        for tag, colour in self._COLOURS.items():
            self._log.tag_configure(tag, foreground=colour)

        # ── Bottom stats + buttons ──
        bottom = tk.Frame(self._root, bg="#252526")
        bottom.pack(fill=tk.X, side=tk.BOTTOM)

        self._stats_var = tk.StringVar(value="Done: 0   Errors: 0   Skipped: 0")
        tk.Label(bottom, textvariable=self._stats_var,
                 bg="#252526", fg="#808080", font=(_MONO_FONT, 10),
                 anchor="w").pack(side=tk.LEFT, padx=14, pady=6)

        btn_frame = tk.Frame(bottom, bg="#252526")
        btn_frame.pack(side=tk.RIGHT, padx=14, pady=4)

        if self._log_file:
            ttk.Button(btn_frame, text="Open Log",
                       command=lambda: open_log_in_viewer(self._log_file)
                       ).pack(side=tk.LEFT, padx=(0, 6))

        self._cancel_btn = ttk.Button(btn_frame, text="Cancel",
                                      command=self._on_cancel)
        self._cancel_btn.pack(side=tk.LEFT)

    def _append(self, message: str, tag: str = "info"):
        self._log.configure(state="normal")
        self._log.insert(tk.END, message + "\n", tag)
        self._log.see(tk.END)
        self._log.configure(state="disabled")

    def _poll(self):
        """Drain the update queue and refresh the UI. Called every 100 ms."""
        try:
            while True:
                item = self._queue.get_nowait()
                kind = item[0]

                if kind == "progress":
                    _, cur, total, name, status, dn, err, sk = item
                    pct = int(cur / max(total, 1) * 100)
                    self._pbar.configure(maximum=total, value=cur)
                    self._pct_var.set(f"{pct:3d}%")
                    self._current_var.set(f"  {name}")
                    self._stats_var.set(
                        f"Done: {dn}   Errors: {err}   Skipped: {sk}"
                        f"   [{cur}/{total}]"
                    )
                    icon = {"done": "✓", "error": "✗", "skipped": "⏭"}.get(status, " ")
                    self._append(f"  [{cur:>5}/{total}]  {icon}  {name}", tag=status)

                elif kind == "log":
                    _, message, level = item
                    self._append(f"  {message}", tag=level)

                elif kind == "finish":
                    _, dn, err, sk = item
                    self._pbar.configure(value=self._total)
                    self._pct_var.set("100%")
                    self._current_var.set("  Complete.")
                    self._stats_var.set(
                        f"Done: {dn}   Errors: {err}   Skipped: {sk}   — Finished"
                    )
                    self._cancel_btn.configure(text="Close")
                    self._append("")
                    self._append(
                        f"  ─── Finished ───  done={dn}  errors={err}  skipped={sk}",
                        tag="header",
                    )
                    self._finished.set()
                    return  # stop polling — button closes the window

        except queue.Empty:
            pass

        if not self._finished.is_set() and not self._cancel.is_set():
            self._root.after(100, self._poll)

    def _on_cancel(self):
        self._cancel.set()
        if self._root:
            self._root.after(300, self._root.destroy)

    def _worker(self, work_fn, args, kwargs):
        try:
            result = work_fn(
                *args,
                progress_cb=self.update,
                log_cb=self.log,
                cancel=self._cancel,
                **kwargs,
            )
            if isinstance(result, tuple) and len(result) == 3:
                self.done(*result)
            else:
                self.done(0, 0, 0)
        except Exception as exc:
            self.log(f"Fatal error in worker: {exc}", level="error")
            self.done(0, 1, 0)

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self, work_fn, *args, **kwargs):
        """
        Run work_fn in a background thread and show the progress window on the
        main thread.  Blocks until the window is closed.

        work_fn must accept the keyword arguments:
            progress_cb(current, total, name, status, done, errors, skipped)
            log_cb(message, level="info")
            cancel  — threading.Event; check .is_set() to stop early

        It should return (done, errors, skipped).

        If tkinter is not available (headless environment), work_fn is called
        directly in the current thread with None callbacks.
        """
        if not self._available:
            # Headless fallback — run without GUI
            work_fn(*args, progress_cb=None, log_cb=None,
                    cancel=threading.Event(), **kwargs)
            return

        self._build()

        t = threading.Thread(
            target=self._worker,
            args=(work_fn, args, kwargs),
            daemon=True,
        )
        t.start()

        self._root.after(100, self._poll)
        self._root.mainloop()
