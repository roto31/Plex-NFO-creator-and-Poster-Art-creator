#!/usr/bin/env python3
"""
Plex Artwork Extractor
Extracts embedded cover art from MP4/MKV/audio files and saves as sidecar
poster.jpg / folder.jpg / artist.jpg files for Plex.

Compatible with macOS, Linux, and Windows (Python 3.8+). Requires ffmpeg in PATH.

New-style usage (guided first-run setup):
    python3 extract_artwork.py                              # guided, all media
    python3 extract_artwork.py --media-type movies          # movies only
    python3 extract_artwork.py --media-type all --extract   # extract all
    python3 extract_artwork.py --no-prompts --extract       # unattended

Legacy usage (still fully supported):
    python3 extract_artwork.py movies "/path/to/Movies"            # dry run
    python3 extract_artwork.py movies "/path/to/Movies" --extract  # extract
    python3 extract_artwork.py tvshows "/path/to/TV Shows" --extract
    python3 extract_artwork.py music "/path/to/Music" --extract

Add --force to re-extract even if output file already exists.
Add --config to specify a custom config file path.
"""

import sys
import os
import re
import subprocess
import json
import platform
import shutil
import logging
import argparse
from pathlib import Path
from typing import Optional, List

import preflight

# ─── Cross-platform UTF-8 output ──────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VIDEO_EXTS  = {'.mkv', '.mp4', '.mov', '.avi', '.m4v'}
AUDIO_EXTS  = {'.mp3', '.m4a', '.flac', '.aac', '.ogg', '.opus', '.wma', '.wav'}

_DEFAULT_CONFIG = 'plex-extract-artwork.conf'
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ─── Multi-part detection ─────────────────────────────────────────────────────

_MULTIPART_RE = re.compile(
    r'(?i)(?:'
    r'\bpart\s*\d+\b'
    r'|\bpart\s+[ivxIVX]+\b'
    r'|\bdisc\s*\d+\b'
    r'|\bdisk\s*\d+\b'
    r'|\b\d+\s+of\s+\d+\b'
    r'|\bvol(?:ume)?\s*\d+\b'
    r'|\bchapter\s*\d+\b'
    r'|\bpt\s*\d+\b'
    r')'
)


def is_multipart(name: str) -> bool:
    return bool(_MULTIPART_RE.search(name))


# ─── Native OS dialog infrastructure ─────────────────────────────────────────
# Mirrored from plex_metadata_generator.py so extract_artwork.py is self-contained.

def _esc_apl(s: str) -> str:
    return s.replace('\\', '\\\\').replace('"', '\\"')


def _esc_ps(s: str) -> str:
    return s.replace("'", "''")


def _input_macos(title: str, message: str, default: str = '') -> Optional[str]:
    script = (
        'tell application "System Events"\n'
        '    activate\n'
        f'    set r to display dialog "{_esc_apl(message)}" '
        f'default answer "{_esc_apl(default)}" '
        f'with title "{_esc_apl(title)}" buttons {{"Skip", "OK"}} '
        'default button "OK"\n'
        '    if button returned of r is "OK" then\n'
        '        return text returned of r\n'
        '    else\n'
        '        return ""\n'
        '    end if\n'
        'end tell'
    )
    try:
        result = subprocess.run(['osascript', '-e', script],
                                capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            return None
        text = result.stdout.strip()
        return text if text else None
    except Exception:
        return None


def _input_linux(title: str, message: str, default: str = '') -> Optional[str]:
    if shutil.which('zenity'):
        try:
            r = subprocess.run(
                ['zenity', '--entry', f'--title={title}', f'--text={message}',
                 f'--entry-text={default}', '--width=500'],
                capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                return r.stdout.strip() or None
        except Exception:
            pass
    if shutil.which('kdialog'):
        try:
            r = subprocess.run(
                ['kdialog', '--inputbox', message, default, f'--title={title}'],
                capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                return r.stdout.strip() or None
        except Exception:
            pass
    return _input_terminal(title, message, default)


def _input_windows(title: str, message: str, default: str = '') -> Optional[str]:
    ps = (
        'Add-Type -AssemblyName Microsoft.VisualBasic; '
        '$r = [Microsoft.VisualBasic.Interaction]::InputBox('
        f"'{_esc_ps(message)}', '{_esc_ps(title)}', '{_esc_ps(default)}'); "
        'Write-Output $r'
    )
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                           capture_output=True, text=True, timeout=300)
        if r.returncode == 0:
            text = r.stdout.strip()
            return text if text else None
    except Exception:
        pass
    return _input_terminal(title, message, default)


def _input_terminal(title: str, message: str, default: str = '') -> Optional[str]:
    sep = '─' * 64
    prompt = f"  Enter value (or press Enter to skip): "
    if default:
        prompt = f"  Enter value [default: {default}]: "
    print(f'\n{sep}\n  {title}\n{sep}\n{message}\n{sep}', flush=True)
    try:
        ans = input(prompt).strip()
        return ans or default or None
    except (EOFError, KeyboardInterrupt):
        return None


def _yesno_macos(title: str, message: str, default_yes: bool = True) -> bool:
    default_btn = '"Yes"' if default_yes else '"No"'
    script = (
        'tell application "System Events"\n'
        '    activate\n'
        f'    set r to display dialog "{_esc_apl(message)}" '
        f'buttons {{"No", "Yes"}} default button {default_btn} '
        f'with title "{_esc_apl(title)}" with icon note\n'
        '    return button returned of r\n'
        'end tell'
    )
    try:
        result = subprocess.run(['osascript', '-e', script],
                                capture_output=True, text=True, timeout=120)
        return result.stdout.strip() == 'Yes'
    except Exception:
        return default_yes


def _yesno_linux(title: str, message: str, default_yes: bool = True) -> bool:
    if shutil.which('zenity'):
        try:
            r = subprocess.run(
                ['zenity', '--question', '--title', title,
                 '--text', message, '--width', '480'],
                timeout=120)
            return r.returncode == 0
        except Exception:
            pass
    if shutil.which('kdialog'):
        try:
            r = subprocess.run(['kdialog', '--yesno', message, f'--title={title}'],
                               timeout=120)
            return r.returncode == 0
        except Exception:
            pass
    try:
        default_hint = '[Y/n]' if default_yes else '[y/N]'
        ans = input(f"\n{title}\n{message}\n  {default_hint}: ").strip().lower()
        if not ans:
            return default_yes
        return ans in ('y', 'yes')
    except (EOFError, KeyboardInterrupt):
        return default_yes


def _yesno_windows(title: str, message: str, default_yes: bool = True) -> bool:
    ps = (
        'Add-Type -AssemblyName System.Windows.Forms; '
        '$r = [System.Windows.Forms.MessageBox]::Show('
        f"'{_esc_ps(message)}', '{_esc_ps(title)}', "
        '[System.Windows.Forms.MessageBoxButtons]::YesNo, '
        '[System.Windows.Forms.MessageBoxIcon]::Question); '
        "if ($r -eq 'Yes') { exit 0 } else { exit 1 }"
    )
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-Command', ps], timeout=120)
        return r.returncode == 0
    except Exception:
        return default_yes


def _prompt_yesno(title: str, message: str, default_yes: bool = True) -> bool:
    _sys = platform.system()
    if _sys == 'Darwin':
        return _yesno_macos(title, message, default_yes)
    elif _sys == 'Windows':
        return _yesno_windows(title, message, default_yes)
    else:
        return _yesno_linux(title, message, default_yes)


def _pick_folder_macos(prompt: str) -> Optional[str]:
    script = (
        'tell application "System Events"\n'
        '    activate\n'
        f'    set f to choose folder with prompt "{_esc_apl(prompt)}"\n'
        '    return POSIX path of f\n'
        'end tell'
    )
    try:
        r = subprocess.run(['osascript', '-e', script],
                           capture_output=True, text=True, timeout=300)
        path = r.stdout.strip()
        return path if path else None
    except Exception:
        return None


def _pick_folder_linux(prompt: str) -> Optional[str]:
    if shutil.which('zenity'):
        try:
            r = subprocess.run(
                ['zenity', '--file-selection', '--directory',
                 f'--title={prompt}', '--width=600'],
                capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                return r.stdout.strip() or None
        except Exception:
            pass
    if shutil.which('kdialog'):
        try:
            r = subprocess.run(
                ['kdialog', '--getexistingdirectory', '/mnt', f'--title={prompt}'],
                capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                return r.stdout.strip() or None
        except Exception:
            pass
    sep = '─' * 64
    print(f'\n{sep}\n  {prompt}\n{sep}', flush=True)
    try:
        path = input('  Enter folder path (or press Enter to skip): ').strip()
        return path or None
    except (EOFError, KeyboardInterrupt):
        return None


def _pick_folder_windows(prompt: str) -> Optional[str]:
    ps = (
        'Add-Type -AssemblyName System.Windows.Forms; '
        '$d = New-Object System.Windows.Forms.FolderBrowserDialog; '
        f"$d.Description = '{_esc_ps(prompt)}'; "
        '$d.ShowNewFolderButton = $false; '
        '[void]$d.ShowDialog(); '
        'Write-Output $d.SelectedPath'
    )
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                           capture_output=True, text=True, timeout=300)
        path = r.stdout.strip()
        return path if path else None
    except Exception:
        return None


def _pick_folder(prompt: str) -> Optional[str]:
    _sys = platform.system()
    if _sys == 'Darwin':
        return _pick_folder_macos(prompt)
    elif _sys == 'Windows':
        return _pick_folder_windows(prompt)
    else:
        return _pick_folder_linux(prompt)


def _collect_library_paths(media_label: str) -> List[str]:
    """Show repeated folder-picker dialogs until the user clicks Done."""
    paths: List[str] = []
    has_media = _prompt_yesno(
        f'Plex Artwork Extractor — {media_label} Library',
        f'Do you have a {media_label} library to extract artwork from?\n\n'
        f'Click Yes to select folder(s), or No to skip {media_label}.'
    )
    if not has_media:
        return paths
    while True:
        picked = _pick_folder(f'Select {media_label} folder to scan')
        if picked:
            paths.append(picked.rstrip('/').rstrip('\\'))
            paths_display = '\n'.join(f'  • {p}' for p in paths)
            add_more = _prompt_yesno(
                f'Plex Artwork Extractor — {media_label} Library',
                f'Added:\n{paths_display}\n\nAdd another {media_label} volume?'
            )
            if not add_more:
                break
        else:
            break
    return paths


# ─── Config file support ──────────────────────────────────────────────────────

def _default_config_path() -> str:
    return os.path.join(_SCRIPT_DIR, _DEFAULT_CONFIG)


def load_config(config_file: str) -> dict:
    """Load config JSON, returning an empty dict if the file does not exist yet."""
    if not os.path.exists(config_file):
        return {}
    try:
        with open(config_file, encoding='utf-8') as f:
            text = re.sub(r'(?<!:)//[^\n]*', '', f.read())
            return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {config_file}: {e}")
        return {}


def _save_config_if_agreed(config: dict, config_path: str, question: str = None):
    """Offer to persist config to disk."""
    if not config_path:
        return
    q = question or f'Save settings to config file?\n\n{config_path}'
    if _prompt_yesno('Plex Artwork Extractor — Save Settings', q):
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            logger.info(f"  Config saved to {config_path}")
        except IOError as e:
            logger.warning(f"  Could not save config: {e}")


def _already_configured(config: dict, plural_key: str, singular_key: str) -> bool:
    roots = config.get(plural_key, [])
    if roots and isinstance(roots, list) and roots[0] and 'YOUR_' not in str(roots[0]):
        return True
    single = config.get(singular_key, '')
    return bool(single) and 'YOUR_' not in str(single)


def prompt_missing_library_paths(config: dict, config_path: str) -> dict:
    """Show folder-picker dialogs for any unconfigured library roots."""
    changed = False
    media_types = [
        ('Movies',    'movies_library_roots', 'movies_library_root'),
        ('TV Shows',  'tv_library_roots',     'tv_library_root'),
        ('Music',     'music_library_roots',  'music_library_root'),
    ]
    for label, plural_key, singular_key in media_types:
        if _already_configured(config, plural_key, singular_key):
            continue
        paths = _collect_library_paths(label)
        if paths:
            config[plural_key] = paths
            config[singular_key] = paths[0]
            changed = True
            logger.info(f"  {label} library root(s): {paths}")
    if changed:
        _save_config_if_agreed(
            config, config_path,
            'Save these library paths to the config file so you are not prompted again?\n\n'
            + config_path
        )
    return config


def prompt_force_flag() -> bool:
    """Ask whether to force full re-extraction."""
    return _prompt_yesno(
        'Plex Artwork Extractor — Extraction Mode',
        'Is this your first time running the Artwork Extractor, or do you want\n'
        'to force re-extraction of all artwork?\n\n'
        '• Yes — extract artwork for EVERY item, even those that already have\n'
        '  poster.jpg / folder.jpg / artist.jpg  (first-time or full refresh)\n\n'
        '• No — skip items that already have artwork\n'
        '  (recommended for ongoing / scheduled use)\n\n'
        'Force a full re-extraction?',
        default_yes=False,
    )


def _resolve_roots(config: dict, plural_key: str, singular_key: str) -> List[str]:
    """Return the list of library roots from config (plural or singular key)."""
    roots = config.get(plural_key)
    if roots and isinstance(roots, list):
        return [r for r in roots if r]
    single = config.get(singular_key, '')
    return [single] if single else []


# ─── Artwork extraction ───────────────────────────────────────────────────────

def extract_embedded_artwork(source_path: str, output_path: str) -> bool:
    """
    Extract embedded cover art from a video or audio file using ffmpeg.
    Tries multiple strategies. Returns True on success.
    Never falls back to extracting a video frame.
    """
    # Strategy 1: Secondary video stream (Subler/iTunes MP4: stream 0=video, 1=cover art)
    try:
        result = subprocess.run(
            ['ffmpeg', '-i', source_path,
             '-an', '-vframes', '1', '-map', '0:v:1',
             '-y', output_path],
            capture_output=True, timeout=30
        )
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
        if os.path.exists(output_path):
            os.remove(output_path)
    except Exception:
        pass

    # Strategy 2: attached_pic stream (MKV, some MP4, most audio files)
    try:
        result = subprocess.run(
            ['ffmpeg', '-i', source_path,
             '-map', '0:v', '-map', '-0:V',
             '-vframes', '1', '-y', output_path],
            capture_output=True, timeout=30
        )
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
        if os.path.exists(output_path):
            os.remove(output_path)
    except Exception:
        pass

    # Strategy 3: explicit attached_pic flag (fallback for some encoders)
    try:
        result = subprocess.run(
            ['ffmpeg', '-i', source_path,
             '-an', '-vsync', '2',
             '-y', output_path],
            capture_output=True, timeout=30
        )
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
        if os.path.exists(output_path):
            os.remove(output_path)
    except Exception:
        pass

    return False


def _find_video(folder_path: str) -> Optional[str]:
    for f in sorted(os.listdir(folder_path)):
        if os.path.splitext(f)[1].lower() in VIDEO_EXTS:
            return os.path.join(folder_path, f)
    return None


def _find_audio(folder_path: str) -> Optional[str]:
    """Return the first audio file found in a folder, or None."""
    for f in sorted(os.listdir(folder_path)):
        if os.path.splitext(f)[1].lower() in AUDIO_EXTS:
            return os.path.join(folder_path, f)
    return None


def _find_first_episode(season_path: str) -> Optional[str]:
    videos = sorted([
        f for f in os.listdir(season_path)
        if os.path.splitext(f)[1].lower() in VIDEO_EXTS
    ])
    return os.path.join(season_path, videos[0]) if videos else None


# ─── Movies ───────────────────────────────────────────────────────────────────

def process_movies(root_dir: str, extract: bool, force: bool,
                   specific_movie: str = None,
                   progress_cb=None, log_cb=None, cancel=None):
    folders = sorted([
        e for e in os.listdir(root_dir)
        if os.path.isdir(os.path.join(root_dir, e)) and not e.startswith('.')
    ])
    if specific_movie:
        folders = [f for f in folders if f == specific_movie]

    total = len(folders)

    def _log(msg, level="info"):
        if log_cb:
            log_cb(msg, level)
        else:
            print(msg, flush=True)

    mode_label = "EXTRACTING ARTWORK" if extract else "DRY RUN — No files will be written"
    _log(f"\n{mode_label} — Movies: {root_dir}")
    _log("=" * 60)
    _log(f"Found {total} movie folder(s)\n")

    n_extracted = n_exists = n_multipart = n_no_art = n_no_video = 0

    for idx, folder_name in enumerate(folders, 1):
        if cancel and cancel.is_set():
            _log("Cancelled by user.", "warning")
            break

        folder_path = os.path.join(root_dir, folder_name)
        prefix = f"[{idx}/{total}] {folder_name}"

        if is_multipart(folder_name):
            _log(f"{prefix} ⏭ multi-part — skipped", "info")
            n_multipart += 1
            if progress_cb:
                progress_cb(idx, total, folder_name, "skipped",
                            n_extracted, n_no_art, n_multipart + n_no_video)
            continue

        poster_path = os.path.join(folder_path, "poster.jpg")
        if os.path.exists(poster_path) and not force:
            _log(f"{prefix} ⏭ poster.jpg already exists", "info")
            n_exists += 1
            if progress_cb:
                progress_cb(idx, total, folder_name, "skipped",
                            n_extracted, n_no_art, n_exists + n_multipart + n_no_video)
            continue

        video_path = _find_video(folder_path)
        if not video_path:
            _log(f"{prefix} ⚠ no video file found", "warning")
            n_no_video += 1
            if progress_cb:
                progress_cb(idx, total, folder_name, "skipped",
                            n_extracted, n_no_art, n_exists + n_multipart + n_no_video)
            continue

        if not extract:
            _log(f"{prefix}  WOULD EXTRACT → poster.jpg")
            n_extracted += 1
        else:
            success = extract_embedded_artwork(video_path, poster_path)
            if success:
                _log(f"{prefix} ✓ → poster.jpg")
                n_extracted += 1
                if progress_cb:
                    progress_cb(idx, total, folder_name, "done",
                                n_extracted, n_no_art, n_exists + n_multipart + n_no_video)
            else:
                _log(f"{prefix} ❌ no embedded artwork", "error")
                n_no_art += 1
                if progress_cb:
                    progress_cb(idx, total, folder_name, "error",
                                n_extracted, n_no_art, n_exists + n_multipart + n_no_video)
            continue

        if progress_cb:
            progress_cb(idx, total, folder_name, "done",
                        n_extracted, n_no_art, n_exists + n_multipart + n_no_video)

    _log("\n" + "=" * 60)
    if not extract:
        _log("DRY RUN COMPLETE — Movies")
        _log(f"  Would extract:  {n_extracted}")
        _log(f"  Already exist:  {n_exists}")
        _log(f"  Multi-part:     {n_multipart} skipped")
        _log(f"  No artwork:     {n_no_art} skipped")
        _log(f"  No video file:  {n_no_video} skipped")
        _log(f'\nTo apply: python3 extract_artwork.py --media-type movies --extract')
    else:
        _log("COMPLETE — Movies")
        _log(f"  Extracted:    {n_extracted} poster.jpg files")
        _log(f"  Already had:  {n_exists}")
        _log(f"  Multi-part:   {n_multipart} skipped")
        _log(f"  No artwork:   {n_no_art} skipped")
        _log(f"  No video:     {n_no_video} skipped")

    return n_extracted, n_no_art, n_exists + n_multipart + n_no_video


# ─── TV Shows ─────────────────────────────────────────────────────────────────

def process_tvshows(root_dir: str, extract: bool, force: bool,
                    specific_show: str = None,
                    progress_cb=None, log_cb=None, cancel=None):
    shows = sorted([
        e for e in os.listdir(root_dir)
        if os.path.isdir(os.path.join(root_dir, e)) and not e.startswith('.')
    ])
    if specific_show:
        shows = [s for s in shows if s == specific_show]

    total = len(shows)

    def _log(msg, level="info"):
        if log_cb:
            log_cb(msg, level)
        else:
            print(msg, flush=True)

    mode_label = "EXTRACTING ARTWORK" if extract else "DRY RUN — No files will be written"
    _log(f"\n{mode_label} — TV Shows: {root_dir}")
    _log("=" * 60)
    _log(f"Found {total} TV show folder(s)\n")

    n_show_posters = n_season_posters = n_ep_thumbs = 0
    n_exists = n_no_art = 0

    for idx, show_name in enumerate(shows, 1):
        if cancel and cancel.is_set():
            _log("Cancelled by user.", "warning")
            break

        show_path = os.path.join(root_dir, show_name)
        _log(f"[{idx}/{total}] {show_name}")

        season_dirs = sorted([
            d for d in os.listdir(show_path)
            if os.path.isdir(os.path.join(show_path, d)) and not d.startswith('.')
            and re.match(r'[Ss]eason\s*\d+|[Ss]pecials?', d)
        ])

        show_poster = os.path.join(show_path, "poster.jpg")
        if not os.path.exists(show_poster) or force:
            source = None
            for sd in season_dirs:
                ep = _find_first_episode(os.path.join(show_path, sd))
                if ep:
                    source = ep
                    break
            if source:
                if not extract:
                    _log(f"  WOULD EXTRACT → poster.jpg (from {os.path.basename(source)})")
                    n_show_posters += 1
                else:
                    if extract_embedded_artwork(source, show_poster):
                        _log(f"  ✓ poster.jpg")
                        n_show_posters += 1
                    else:
                        _log(f"  ❌ poster.jpg — no embedded artwork", "error")
                        n_no_art += 1
            else:
                _log(f"  ⏭ poster.jpg — no source episode found", "warning")
        else:
            _log(f"  ⏭ poster.jpg already exists")
            n_exists += 1

        for season_dir in season_dirs:
            season_path = os.path.join(show_path, season_dir)
            videos = sorted([
                f for f in os.listdir(season_path)
                if os.path.splitext(f)[1].lower() in VIDEO_EXTS
            ])
            if not videos:
                continue

            season_poster = os.path.join(season_path, "poster.jpg")
            if not os.path.exists(season_poster) or force:
                source = os.path.join(season_path, videos[0])
                if not extract:
                    _log(f"    {season_dir}: WOULD EXTRACT → poster.jpg")
                    n_season_posters += 1
                else:
                    if extract_embedded_artwork(source, season_poster):
                        _log(f"    {season_dir} ✓ → poster.jpg")
                        n_season_posters += 1
                    else:
                        _log(f"    {season_dir} ❌ poster.jpg — no embedded artwork", "error")
                        n_no_art += 1
            else:
                n_exists += 1

            for vfile in videos:
                stem = os.path.splitext(vfile)[0]
                thumb_path = os.path.join(season_path, f"{stem}-thumb.jpg")
                if os.path.exists(thumb_path) and not force:
                    n_exists += 1
                    continue
                video_path = os.path.join(season_path, vfile)
                if not extract:
                    n_ep_thumbs += 1
                else:
                    if extract_embedded_artwork(video_path, thumb_path):
                        n_ep_thumbs += 1
                    else:
                        n_no_art += 1

        _log("")
        n_done = n_show_posters + n_season_posters + n_ep_thumbs
        if progress_cb:
            progress_cb(idx, total, show_name, "done", n_done, n_no_art, n_exists)

    _log("=" * 60)
    if not extract:
        _log("DRY RUN COMPLETE — TV Shows")
        _log(f"  Show posters:    {n_show_posters}")
        _log(f"  Season posters:  {n_season_posters}")
        _log(f"  Episode thumbs:  {n_ep_thumbs}")
        _log(f"  Already exist:   {n_exists}")
        _log(f"  No artwork:      {n_no_art}")
        _log(f'\nTo apply: python3 extract_artwork.py --media-type tvshows --extract')
    else:
        _log("COMPLETE — TV Shows")
        _log(f"  Show posters extracted:   {n_show_posters}")
        _log(f"  Season posters extracted: {n_season_posters}")
        _log(f"  Episode thumbs extracted: {n_ep_thumbs}")
        _log(f"  Already existed:          {n_exists}")
        _log(f"  No embedded artwork:      {n_no_art}")

    n_done = n_show_posters + n_season_posters + n_ep_thumbs
    return n_done, n_no_art, n_exists


# ─── Music ────────────────────────────────────────────────────────────────────

def process_music(root_dir: str, extract: bool, force: bool,
                  specific_artist: str = None,
                  progress_cb=None, log_cb=None, cancel=None):
    """
    Extract embedded artwork from music files.
    - Artist root: extracts from first audio file found anywhere under the artist
      dir and saves as artist.jpg (the embedded art is typically the album cover,
      which serves as the artist image when no dedicated photo exists).
    - Album subdir: extracts from first audio file and saves as folder.jpg
      (Plex reads this as the album cover).
    """
    artists = sorted([
        e for e in os.listdir(root_dir)
        if os.path.isdir(os.path.join(root_dir, e)) and not e.startswith('.')
    ])
    if specific_artist:
        artists = [a for a in artists if a == specific_artist]

    total = len(artists)

    def _log(msg, level="info"):
        if log_cb:
            log_cb(msg, level)
        else:
            print(msg, flush=True)

    mode_label = "EXTRACTING ARTWORK" if extract else "DRY RUN — No files will be written"
    _log(f"\n{mode_label} — Music: {root_dir}")
    _log("=" * 60)
    _log(f"Found {total} artist folder(s)\n")

    n_artist = n_album = n_exists = n_no_art = 0

    for idx, artist_name in enumerate(artists, 1):
        if cancel and cancel.is_set():
            _log("Cancelled by user.", "warning")
            break

        artist_path = os.path.join(root_dir, artist_name)
        _log(f"[{idx}/{total}] {artist_name}")

        # --- artist.jpg — grab the first audio file anywhere under artist dir ---
        artist_jpg = os.path.join(artist_path, "artist.jpg")
        if not os.path.exists(artist_jpg) or force:
            # Find first audio file in any album subdir
            source_for_artist = None
            for album_entry in sorted(os.listdir(artist_path)):
                album_p = os.path.join(artist_path, album_entry)
                if os.path.isdir(album_p) and not album_entry.startswith('.'):
                    af = _find_audio(album_p)
                    if af:
                        source_for_artist = af
                        break
            if source_for_artist is None:
                source_for_artist = _find_audio(artist_path)

            if source_for_artist:
                if not extract:
                    _log(f"  WOULD EXTRACT → artist.jpg (from {os.path.basename(source_for_artist)})")
                    n_artist += 1
                else:
                    if extract_embedded_artwork(source_for_artist, artist_jpg):
                        _log(f"  ✓ artist.jpg")
                        n_artist += 1
                    else:
                        _log(f"  ⏭ artist.jpg — no embedded artwork in audio", "warning")
                        n_no_art += 1
            else:
                _log(f"  ⏭ artist.jpg — no audio files found", "warning")
        else:
            _log(f"  ⏭ artist.jpg already exists")
            n_exists += 1

        # --- Album subdirs: folder.jpg per album ---
        album_dirs = sorted([
            d for d in os.listdir(artist_path)
            if os.path.isdir(os.path.join(artist_path, d)) and not d.startswith('.')
        ])
        for album_dir in album_dirs:
            album_path = os.path.join(artist_path, album_dir)
            folder_jpg = os.path.join(album_path, "folder.jpg")

            if os.path.exists(folder_jpg) and not force:
                n_exists += 1
                continue

            audio_file = _find_audio(album_path)
            if not audio_file:
                continue

            if not extract:
                _log(f"    {album_dir}: WOULD EXTRACT → folder.jpg")
                n_album += 1
            else:
                if extract_embedded_artwork(audio_file, folder_jpg):
                    _log(f"    {album_dir} ✓ → folder.jpg")
                    n_album += 1
                else:
                    _log(f"    {album_dir} ⏭ folder.jpg — no embedded artwork", "warning")
                    n_no_art += 1

        _log("")
        n_done = n_artist + n_album
        if progress_cb:
            progress_cb(idx, total, artist_name, "done", n_done, n_no_art, n_exists)

    _log("=" * 60)
    if not extract:
        _log("DRY RUN COMPLETE — Music")
        _log(f"  Artist images:  {n_artist} would extract")
        _log(f"  Album covers:   {n_album} would extract")
        _log(f"  Already exist:  {n_exists}")
        _log(f"  No artwork:     {n_no_art}")
        _log(f'\nTo apply: python3 extract_artwork.py --media-type music --extract')
    else:
        _log("COMPLETE — Music")
        _log(f"  Artist images extracted: {n_artist}")
        _log(f"  Album covers extracted:  {n_album}")
        _log(f"  Already existed:         {n_exists}")
        _log(f"  No embedded artwork:     {n_no_art}")

    n_done = n_artist + n_album
    return n_done, n_no_art, n_exists


# ─── Multi-volume dispatcher ──────────────────────────────────────────────────

def _run_for_roots(roots: List[str], fn, extract: bool, force: bool,
                   specific: str = None,
                   progress_cb=None, log_cb=None, cancel=None):
    """Call processing function fn for each root directory, accumulating counts."""
    total_done = total_errors = total_skipped = 0
    for root in roots:
        if not os.path.isdir(root):
            logger.warning(f"  Library root not found: {root}")
            continue
        done, errors, skipped = fn(
            root, extract, force, specific,
            progress_cb=progress_cb, log_cb=log_cb, cancel=cancel,
        )
        total_done += done
        total_errors += errors
        total_skipped += skipped
    return total_done, total_errors, total_skipped


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    # ── Detect legacy positional-argument invocation ─────────────────────────
    # Legacy: python3 extract_artwork.py movies "/path" [--extract] [--force]
    raw = sys.argv[1:]
    legacy_modes = {'movies', 'tvshows', 'music'}
    if raw and raw[0] in legacy_modes:
        # Legacy path — strip flags and dispatch directly
        extract_flag = '--extract' in raw
        force_flag   = '--force'   in raw
        positional   = [a for a in raw if not a.startswith('--')]
        mode = positional[0]
        path = positional[1] if len(positional) > 1 else None

        if not path or not os.path.isdir(path):
            print(f"Usage: python3 extract_artwork.py {mode} \"/path/to/library\" [--extract] [--force]")
            sys.exit(1)

        _, log_file = preflight.setup_logging("extract_artwork")
        if not preflight.check_python_version(logger=logger):
            sys.exit(1)
        if not preflight.check_ffmpeg(logger=logger):
            sys.exit(1)
        if extract_flag and not preflight.check_write_permission(path, logger=logger):
            sys.exit(1)

        label_map = {'movies': 'Movies', 'tvshows': 'TV Shows', 'music': 'Music'}
        label = label_map[mode]
        total = sum(
            1 for e in os.listdir(path)
            if os.path.isdir(os.path.join(path, e)) and not e.startswith('.')
        )
        win = preflight.ProgressWindow(
            title=f"Plex Artwork Extractor — {label}",
            total=total, log_file=log_file,
        )
        fn_map = {'movies': process_movies, 'tvshows': process_tvshows, 'music': process_music}

        def work(progress_cb, log_cb, cancel):
            done, errors, skipped = fn_map[mode](
                path, extract_flag, force_flag,
                progress_cb=progress_cb, log_cb=log_cb, cancel=cancel,
            )
            logger.info(f"Finished — done={done} errors={errors} skipped={skipped}")
            action = "Extracted" if extract_flag else "Would extract"
            preflight.notify(
                "Plex Artwork Extractor — Complete",
                f"{label}: {action} {done}, {errors} errors, {skipped} skipped.",
            )
            return done, errors, skipped

        win.run(work)
        return

    # ── New-style argparse invocation ─────────────────────────────────────────
    parser = argparse.ArgumentParser(
        description='Plex Artwork Extractor — extract embedded art from video and audio files'
    )
    parser.add_argument('--config', default=_default_config_path(),
                        help='Config file path (default: plex-extract-artwork.conf)')
    parser.add_argument('--media-type',
                        choices=['movies', 'tvshows', 'music', 'all'], default=None,
                        help='Which library to process (default: guided by first-run dialog)')
    parser.add_argument('--extract', action='store_true',
                        help='Actually extract artwork (default is dry run)')
    parser.add_argument('--force', action='store_true',
                        help='Overwrite existing artwork files')
    parser.add_argument('--no-prompts', action='store_true',
                        help='Skip first-run setup dialogs (for scheduled/unattended runs)')
    parser.add_argument('--movie',  help='Process only this movie folder name')
    parser.add_argument('--show',   help='Process only this TV show folder name')
    parser.add_argument('--artist', help='Process only this music artist folder name')
    parser.add_argument('--debug',  action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # ── Load / create config ──────────────────────────────────────────────────
    config = load_config(args.config)

    # ── First-run setup dialogs ───────────────────────────────────────────────
    if not args.no_prompts:
        config = prompt_missing_library_paths(config, args.config)
        if not args.force:
            args.force = prompt_force_flag()

    # ── Resolve which media types to process ──────────────────────────────────
    media_type = args.media_type
    if media_type is None:
        # Infer from which roots are configured
        has_movies  = bool(_resolve_roots(config, 'movies_library_roots', 'movies_library_root'))
        has_tv      = bool(_resolve_roots(config, 'tv_library_roots',     'tv_library_root'))
        has_music   = bool(_resolve_roots(config, 'music_library_roots',  'music_library_root'))
        if has_movies or has_tv or has_music:
            media_type = 'all'
        else:
            print("No library paths configured. Run without --no-prompts for guided setup, "
                  "or pass --media-type and a config file with library_roots.")
            sys.exit(1)

    # ── preflight ─────────────────────────────────────────────────────────────
    logger_pf, log_file = preflight.setup_logging("extract_artwork")
    if not preflight.check_python_version(logger=logger_pf):
        sys.exit(1)
    if not preflight.check_ffmpeg(logger=logger_pf):
        sys.exit(1)

    # Build list of (fn, roots, label, specific) tasks
    tasks = []
    if media_type in ('movies', 'all'):
        roots = _resolve_roots(config, 'movies_library_roots', 'movies_library_root')
        if roots:
            tasks.append((process_movies, roots, "Movies", args.movie))
        elif media_type == 'movies':
            print("No movies library roots configured.")
            sys.exit(1)

    if media_type in ('tvshows', 'all'):
        roots = _resolve_roots(config, 'tv_library_roots', 'tv_library_root')
        if roots:
            tasks.append((process_tvshows, roots, "TV Shows", args.show))
        elif media_type == 'tvshows':
            print("No TV library roots configured.")
            sys.exit(1)

    if media_type in ('music', 'all'):
        roots = _resolve_roots(config, 'music_library_roots', 'music_library_root')
        if roots:
            tasks.append((process_music, roots, "Music", args.artist))
        elif media_type == 'music':
            print("No music library roots configured.")
            sys.exit(1)

    if not tasks:
        print("Nothing to process — no configured library roots match the requested media type.")
        sys.exit(1)

    if args.extract:
        for _, roots, _, _ in tasks:
            for root in roots:
                if root and not preflight.check_write_permission(root, logger=logger_pf):
                    sys.exit(1)

    # Count total top-level folders across all tasks for the progress window
    total_folders = 0
    for _, roots, _, _ in tasks:
        for root in roots:
            if os.path.isdir(root):
                total_folders += sum(
                    1 for e in os.listdir(root)
                    if os.path.isdir(os.path.join(root, e)) and not e.startswith('.')
                )

    labels = ' + '.join(t[2] for t in tasks)
    win = preflight.ProgressWindow(
        title=f"Plex Artwork Extractor — {labels}",
        total=total_folders,
        log_file=log_file,
    )

    def work(progress_cb, log_cb, cancel):
        grand_done = grand_errors = grand_skipped = 0
        for fn, roots, label, specific in tasks:
            done, errors, skipped = _run_for_roots(
                roots, fn, args.extract, args.force, specific,
                progress_cb=progress_cb, log_cb=log_cb, cancel=cancel,
            )
            grand_done    += done
            grand_errors  += errors
            grand_skipped += skipped

        logger_pf.info(
            f"Finished — done={grand_done} errors={grand_errors} skipped={grand_skipped}"
        )
        action = "Extracted" if args.extract else "Would extract"
        preflight.notify(
            "Plex Artwork Extractor — Complete",
            f"{labels}: {action} {grand_done}, {grand_errors} errors, {grand_skipped} skipped.",
        )
        return grand_done, grand_errors, grand_skipped

    win.run(work)


if __name__ == '__main__':
    main()
