#!/usr/bin/env python3
"""
Plex Metadata NFO Generator with Tunarr, TVDb, TMDb, and FanArt.tv Integration
Generates NFO files and downloads the full FileBot-compatible artwork set for TV shows,
movies, and their seasons/episodes. Selective processing: skips items that already have
both NFO and all artwork files present.
"""

import io
import os
import re
import sys
import json
import locale
import platform
import shutil
import logging
import sqlite3
import subprocess
import zipfile
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set
from dataclasses import dataclass, field
import xml.etree.ElementTree as ET
import xml.dom.minidom
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# Logging — file handler added after permissions are known
# ---------------------------------------------------------------------------
_LOG_FILE = '/var/log/plex-metadata-generator.log'
_handlers: list = [logging.StreamHandler(sys.stdout)]
try:
    _handlers.append(logging.FileHandler(_LOG_FILE))
except (OSError, PermissionError):
    pass  # running without root; console-only is fine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=_handlers,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Multi-part detection (ported from scraper.py is_multipart())
# ---------------------------------------------------------------------------
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
    """Return True if folder name looks like one disc/part of a multi-part set."""
    return bool(_MULTIPART_RE.search(name))


def fuzzy_variants(title: str) -> List[str]:
    """
    Return progressively-cleaned title variants for fuzzy search fallback.
    Ported from scraper.py — tries up to 6 variants until an API returns a hit.
    """
    seen: Set[str] = {title}
    variants: List[str] = [title]

    def _add(v: str):
        v = v.strip()
        if v and v not in seen:
            seen.add(v)
            variants.append(v)

    # Strip punctuation that search engines trip on
    _add(re.sub(r"[',:\.\-]", ' ', title).replace('  ', ' '))
    # Remove leading article
    _add(re.sub(r'^(The|A|An)\s+', '', title, flags=re.IGNORECASE))
    # Move trailing ", The" / ", A" to front
    m = re.match(r'^(.*),\s*(The|A|An)$', title, re.IGNORECASE)
    if m:
        _add(f"{m.group(2)} {m.group(1)}")
    # Strip subtitle after " - " or ": "
    _add(re.split(r'\s[-:]\s', title)[0])
    # ASCII-fold accented characters (Amélie → Amelie, Léon → Leon)
    ascii_ver = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii')
    _add(ascii_ver)
    # ASCII-fold + strip punctuation
    _add(unicodedata.normalize('NFKD', re.sub(r"[',:\.\-]", ' ', title))
         .encode('ascii', 'ignore').decode('ascii').strip())

    return variants


# ---------------------------------------------------------------------------
# Native OS dialogs — text input and yes/no
# (same conventions as preflight.py in the core suite)
# ---------------------------------------------------------------------------

def _esc_apl(s: str) -> str:
    """Escape for AppleScript double-quoted string."""
    return s.replace('\\', '\\\\').replace('"', '\\"')


def _esc_ps(s: str) -> str:
    """Escape for PowerShell single-quoted string."""
    return s.replace("'", "''")


def _input_macos(title: str, message: str, default: str = '') -> Optional[str]:
    """Native macOS text-input dialog via AppleScript. Returns text or None on Cancel."""
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
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            return None
        text = result.stdout.strip()
        return text if text else None
    except Exception:
        return None


def _input_linux(title: str, message: str, default: str = '') -> Optional[str]:
    """Text-input dialog via zenity, kdialog, or terminal fallback."""
    if shutil.which('zenity'):
        try:
            r = subprocess.run(
                ['zenity', '--entry', f'--title={title}', f'--text={message}',
                 f'--entry-text={default}', '--width=500'],
                capture_output=True, text=True, timeout=300,
            )
            if r.returncode == 0:
                return r.stdout.strip() or None
        except Exception:
            pass
    if shutil.which('kdialog'):
        try:
            r = subprocess.run(
                ['kdialog', '--inputbox', message, default, f'--title={title}'],
                capture_output=True, text=True, timeout=300,
            )
            if r.returncode == 0:
                return r.stdout.strip() or None
        except Exception:
            pass
    return _input_terminal(title, message, default)


def _input_windows(title: str, message: str, default: str = '') -> Optional[str]:
    """Text-input dialog via PowerShell InputBox."""
    ps = (
        'Add-Type -AssemblyName Microsoft.VisualBasic; '
        '$r = [Microsoft.VisualBasic.Interaction]::InputBox('
        f"'{_esc_ps(message)}', '{_esc_ps(title)}', '{_esc_ps(default)}'); "
        'Write-Output $r'
    )
    try:
        r = subprocess.run(
            ['powershell', '-NoProfile', '-Command', ps],
            capture_output=True, text=True, timeout=300,
        )
        if r.returncode == 0:
            text = r.stdout.strip()
            return text if text else None
    except Exception:
        pass
    return _input_terminal(title, message, default)


def _input_terminal(title: str, message: str, default: str = '') -> Optional[str]:
    """Plain-terminal fallback for headless environments."""
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


def _yesno_macos(title: str, message: str) -> bool:
    script = (
        'tell application "System Events"\n'
        '    activate\n'
        f'    set r to display dialog "{_esc_apl(message)}" '
        f'buttons {{"No", "Yes"}} default button "Yes" '
        f'with title "{_esc_apl(title)}" with icon note\n'
        '    return button returned of r\n'
        'end tell'
    )
    try:
        result = subprocess.run(['osascript', '-e', script],
                                capture_output=True, text=True, timeout=120)
        return result.stdout.strip() == 'Yes'
    except Exception:
        return False


def _yesno_linux(title: str, message: str) -> bool:
    if shutil.which('zenity'):
        try:
            r = subprocess.run(
                ['zenity', '--question', '--title', title,
                 '--text', message, '--width', '480'],
                timeout=120,
            )
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
        ans = input(f"\n{title}\n{message}\n  Save? [y/N]: ").strip().lower()
        return ans in ('y', 'yes')
    except (EOFError, KeyboardInterrupt):
        return False


def _yesno_windows(title: str, message: str) -> bool:
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
        return False


def _prompt_text(title: str, message: str, default: str = '') -> Optional[str]:
    """Show a native OS text-input dialog. Returns the entered value, or None on Skip."""
    _sys = platform.system()
    if _sys == 'Darwin':
        return _input_macos(title, message, default)
    elif _sys == 'Windows':
        return _input_windows(title, message, default)
    else:
        return _input_linux(title, message, default)


def _prompt_yesno(title: str, message: str) -> bool:
    """Show a native OS yes/no dialog. Returns True for Yes."""
    _sys = platform.system()
    if _sys == 'Darwin':
        return _yesno_macos(title, message)
    elif _sys == 'Windows':
        return _yesno_windows(title, message)
    else:
        return _yesno_linux(title, message)


# ---------------------------------------------------------------------------
# Native folder-picker dialogs (for library path selection)
# ---------------------------------------------------------------------------

def _pick_folder_macos(prompt: str) -> Optional[str]:
    """Native macOS folder browser via AppleScript 'choose folder'."""
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
    """Folder browser via zenity, kdialog, or terminal path entry."""
    if shutil.which('zenity'):
        try:
            r = subprocess.run(
                ['zenity', '--file-selection', '--directory',
                 f'--title={prompt}', '--width=600'],
                capture_output=True, text=True, timeout=300,
            )
            if r.returncode == 0:
                return r.stdout.strip() or None
        except Exception:
            pass
    if shutil.which('kdialog'):
        try:
            r = subprocess.run(
                ['kdialog', '--getexistingdirectory', '/mnt', f'--title={prompt}'],
                capture_output=True, text=True, timeout=300,
            )
            if r.returncode == 0:
                return r.stdout.strip() or None
        except Exception:
            pass
    # Terminal fallback
    sep = '─' * 64
    print(f'\n{sep}\n  {prompt}\n{sep}', flush=True)
    try:
        path = input('  Enter folder path (or press Enter to skip): ').strip()
        return path or None
    except (EOFError, KeyboardInterrupt):
        return None


def _pick_folder_windows(prompt: str) -> Optional[str]:
    """Folder browser via PowerShell FolderBrowserDialog."""
    ps = (
        'Add-Type -AssemblyName System.Windows.Forms; '
        '$d = New-Object System.Windows.Forms.FolderBrowserDialog; '
        f"$d.Description = '{_esc_ps(prompt)}'; "
        '$d.ShowNewFolderButton = $false; '
        '[void]$d.ShowDialog(); '
        'Write-Output $d.SelectedPath'
    )
    try:
        r = subprocess.run(
            ['powershell', '-NoProfile', '-Command', ps],
            capture_output=True, text=True, timeout=300,
        )
        path = r.stdout.strip()
        return path if path else None
    except Exception:
        return None


def _pick_folder(prompt: str) -> Optional[str]:
    """Show a native OS folder-picker dialog. Returns the selected path or None."""
    _sys = platform.system()
    if _sys == 'Darwin':
        return _pick_folder_macos(prompt)
    elif _sys == 'Windows':
        return _pick_folder_windows(prompt)
    else:
        return _pick_folder_linux(prompt)


def _collect_library_paths(media_label: str) -> List[str]:
    """
    Show repeated folder-picker dialogs until the user clicks Done.
    Returns the list of selected paths (may be empty if user skips).
    """
    paths: List[str] = []

    # First ask whether user has this media type
    has_media = _prompt_yesno(
        f'Plex Metadata Generator — {media_label} Library',
        f'Do you have a {media_label} library to configure?\n\n'
        f'Click Yes to select folder(s), or No to skip {media_label}.'
    )
    if not has_media:
        return paths

    while True:
        picked = _pick_folder(f'Select {media_label} folder to scan')
        if picked:
            paths.append(picked.rstrip('/').rstrip('\\'))
            # Show current list and offer Add / Done
            paths_display = '\n'.join(f'  • {p}' for p in paths)
            add_more = _prompt_yesno(
                f'Plex Metadata Generator — {media_label} Library',
                f'Added:\n{paths_display}\n\n'
                f'Add another {media_label} volume?'
            )
            if not add_more:
                break
        else:
            # User cancelled the picker — treat as Done
            break

    return paths


def prompt_missing_library_paths(config: dict, config_path: str) -> dict:
    """
    If library paths are not yet configured, show native folder-picker dialogs
    for Movies, TV Shows, and Music. Updates config in-place and offers to save.
    """
    changed = False

    def _already_set(plural_key: str, singular_key: str) -> bool:
        roots = config.get(plural_key, [])
        if roots and isinstance(roots, list) and roots[0] and 'YOUR_' not in roots[0]:
            return True
        single = config.get(singular_key, '')
        return bool(single) and 'YOUR_' not in str(single) and single != '/mnt/media/TV' \
               and single != '/mnt/media/Movies' and single != '/mnt/media/Music'

    media_types = [
        ('Movies',    'movies_library_roots', 'movies_library_root'),
        ('TV Shows',  'tv_library_roots',     'tv_library_root'),
        ('Music',     'music_library_roots',  'music_library_root'),
    ]

    for label, plural_key, singular_key in media_types:
        if _already_set(plural_key, singular_key):
            continue
        paths = _collect_library_paths(label)
        if paths:
            config[plural_key] = paths
            # Keep singular key pointing at first path for backward compat
            config[singular_key] = paths[0]
            changed = True
            logger.info(f"  {label} library root(s): {paths}")

    if not changed:
        return config

    save = _prompt_yesno(
        'Plex Metadata Generator — Save Library Paths',
        'Save these library paths to the config file so you are not prompted again?\n\n'
        + config_path
    )
    if save:
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            logger.info(f'  ✓ Config saved: {config_path}')
        except IOError as e:
            logger.error(f'  Failed to save config: {e}')

    return config


def prompt_force_flag() -> bool:
    """
    Ask the user whether to force a full rescan (--force behaviour).
    Returns True if they want to process all items regardless of existing metadata.
    """
    return _prompt_yesno(
        'Plex Metadata Generator — Scan Mode',
        'Is this your first time running the Metadata Generator, or do you want '
        'to force a full rescan of your media folders?\n\n'
        '• Yes — process EVERY item, even those that already have NFO files and artwork\n'
        '  (use for first-time setup or to refresh everything)\n\n'
        '• No — skip items that are already complete\n'
        '  (recommended for ongoing / scheduled use)\n\n'
        'Force a full rescan of all media?'
    )


# ---------------------------------------------------------------------------
# Local MusicBrainz DB pre-flight dialog
# ---------------------------------------------------------------------------

def _test_mb_db_connection(cfg: dict) -> tuple:
    """
    Try connecting to the local MusicBrainz PostgreSQL database described
    by cfg (keys: host, port, dbname, user, password, schema).
    Returns (ok: bool, message: str).
    """
    try:
        import psycopg2  # noqa: PLC0415
    except ImportError:
        return False, ("psycopg2 is not installed.\n\n"
                       "Install it with:\n    pip install psycopg2-binary\n\n"
                       "then re-run to use the local database.")
    try:
        conn = psycopg2.connect(
            host=cfg.get('host', 'localhost'),
            port=int(cfg.get('port', 5432)),
            dbname=cfg.get('dbname', 'musicbrainz'),
            user=cfg.get('user', 'musicbrainz'),
            password=cfg.get('password', ''),
            connect_timeout=5,
        )
        schema = cfg.get('schema', 'musicbrainz')
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {schema}.artist LIMIT 1")
        conn.close()
        return True, ''
    except Exception as e:
        return False, str(e)


def prompt_musicbrainz_local_db(config: dict, config_path: str) -> dict:
    """
    Pre-flight dialog: offer to configure a local MusicBrainz PostgreSQL
    database for music metadata lookups (faster, no rate limits).

    Skipped if musicbrainz_db is already fully configured and reachable,
    or if the user has previously declined (musicbrainz_db.skip == true).
    """
    mb_cfg = config.get('musicbrainz_db', {})

    # Already fully configured and connected — nothing to do
    if mb_cfg.get('host') or mb_cfg.get('dbname'):
        ok, _ = _test_mb_db_connection(mb_cfg)
        if ok:
            return config

    # User previously chose to skip
    if mb_cfg.get('skip') is True:
        return config

    wants_local = _prompt_yesno(
        'Plex Metadata Generator — Music Metadata',
        'Do you have a local MusicBrainz database?\n\n'
        'A local database provides instant music lookups with no rate limits\n'
        'or internet dependency — ideal for large music libraries.\n\n'
        'Two download options:\n'
        '  PostgreSQL dump (recommended for this script):\n'
        '  https://data.metabrainz.org/pub/musicbrainz/data/fullexport/\n\n'
        '  JSON dump (lightweight alternative, no PostgreSQL needed):\n'
        '  https://data.metabrainz.org/pub/musicbrainz/data/json-dumps\n\n'
        'If you select No, the MusicBrainz REST API is used instead\n'
        '(free, but rate-limited to ~1 request/second).\n\n'
        'Do you want to connect to a local MusicBrainz database?'
    )

    if not wants_local:
        # Remember the choice so we don't ask again
        config.setdefault('musicbrainz_db', {})['skip'] = True
        _save_config_if_agreed(config, config_path,
                               'Save your choice (skip local MusicBrainz DB) to config?')
        return config

    # Ask which format the user has
    wants_pg = _prompt_yesno(
        'Plex Metadata Generator — MusicBrainz Format',
        'Which MusicBrainz data format do you have?\n\n'
        '• Yes  — PostgreSQL dump (fullexport)\n'
        '         Fastest lookups; requires PostgreSQL to be running\n'
        '         Download: data.metabrainz.org/pub/musicbrainz/data/fullexport/\n\n'
        '• No   — JSON dump (json-dumps)\n'
        '         No database server needed; files queried directly\n'
        '         Download: data.metabrainz.org/pub/musicbrainz/data/json-dumps\n\n'
        'Do you have the PostgreSQL (fullexport) dump?'
    )

    if not wants_pg:
        # JSON dump path
        existing_json_dir = config.get('musicbrainz_json_dump_dir', '')
        json_dir = _prompt_text(
            'Plex Metadata Generator — MusicBrainz JSON Dump',
            'Enter the path to the extracted MusicBrainz JSON dump directory.\n\n'
            'This should be the folder containing sub-directories:\n'
            '  artist/  release/  release-group/  recording/\n\n'
            'Download: https://data.metabrainz.org/pub/musicbrainz/data/json-dumps',
            default=existing_json_dir,
        )
        if json_dir and os.path.isdir(json_dir):
            config['musicbrainz_json_dump_dir'] = json_dir.rstrip('/').rstrip('\\')
            config.setdefault('musicbrainz_db', {})['skip'] = True
            _save_config_if_agreed(config, config_path,
                                   'Save MusicBrainz JSON dump path to config?')
        else:
            logger.warning(f"  Directory not found: {json_dir} — will use REST API")
        return config

    # Gather PostgreSQL connection details
    defaults = {
        'host':     mb_cfg.get('host', 'localhost'),
        'port':     str(mb_cfg.get('port', 5432)),
        'dbname':   mb_cfg.get('dbname', 'musicbrainz'),
        'user':     mb_cfg.get('user', 'musicbrainz'),
        'password': mb_cfg.get('password', ''),
        'schema':   mb_cfg.get('schema', 'musicbrainz'),
    }

    fields = [
        ('host',     'PostgreSQL host',     'e.g. localhost or 192.168.1.10'),
        ('port',     'PostgreSQL port',     'default: 5432'),
        ('dbname',   'Database name',       'default: musicbrainz'),
        ('user',     'Database user',       'default: musicbrainz'),
        ('password', 'Database password',   'leave blank if no password'),
        ('schema',   'Schema name',         'default: musicbrainz'),
    ]

    new_cfg: dict = {}
    for key, label, hint in fields:
        value = _prompt_text(
            f'Plex Metadata Generator — MusicBrainz DB ({label})',
            f'{label}\n({hint})',
            default=defaults[key],
        )
        new_cfg[key] = value if value else defaults[key]

    # Validate immediately
    while True:
        logger.info("  Testing local MusicBrainz DB connection…")
        ok, err = _test_mb_db_connection(new_cfg)
        if ok:
            logger.info("  ✓ Local MusicBrainz DB connection verified")
            config['musicbrainz_db'] = new_cfg
            config['musicbrainz_db'].pop('skip', None)
            _save_config_if_agreed(config, config_path,
                                   'Save local MusicBrainz DB settings to config?')
            return config

        retry = _prompt_yesno(
            'Plex Metadata Generator — MusicBrainz DB Connection Failed',
            f'Could not connect to the local MusicBrainz database:\n\n'
            f'{err}\n\n'
            'Common causes:\n'
            '• PostgreSQL is not running  (sudo systemctl start postgresql)\n'
            '• Wrong host / port / credentials\n'
            '• Database not yet imported  (mbdump: data.metabrainz.org/pub/musicbrainz/data/fullexport/)\n'
            '• psycopg2 not installed     (pip install psycopg2-binary)\n\n'
            'Tip: if PostgreSQL is unavailable, select No and use the JSON dump instead\n'
            '(data.metabrainz.org/pub/musicbrainz/data/json-dumps — no database needed)\n\n'
            'Try entering the connection details again?'
        )
        if not retry:
            logger.info("  Skipping local MusicBrainz DB — will use REST API")
            return config

        # Re-prompt all fields
        for key, label, hint in fields:
            value = _prompt_text(
                f'Plex Metadata Generator — MusicBrainz DB ({label})',
                f'{label}\n({hint})',
                default=new_cfg.get(key, defaults[key]),
            )
            new_cfg[key] = value if value else new_cfg.get(key, defaults[key])


def _save_config_if_agreed(config: dict, config_path: str, question: str):
    """Offer to persist config to disk; silently skip if path is unknown."""
    if not config_path or not os.path.exists(os.path.dirname(os.path.abspath(config_path)) or '.'):
        return
    if _prompt_yesno('Plex Metadata Generator — Save Settings', question):
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            logger.info(f"  Config saved to {config_path}")
        except IOError as e:
            logger.warning(f"  Could not save config: {e}")


# ---------------------------------------------------------------------------
# API key definitions — what to check and how to prompt
# ---------------------------------------------------------------------------

def _get_nested(d: dict, *keys) -> str:
    """Walk nested dict; return empty string if any key is missing."""
    for k in keys:
        if not isinstance(d, dict):
            return ''
        d = d.get(k, {})
    return d if isinstance(d, str) else ''


def _set_nested(d: dict, keys: list, value: str):
    """Set a nested dict value, creating intermediate dicts as needed."""
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def _is_placeholder(v: str) -> bool:
    return not v or 'YOUR_' in v


# ---------------------------------------------------------------------------
# API key validators — each returns (is_valid: bool, error_message: str)
# ---------------------------------------------------------------------------

def _validate_tmdb(key: str, _config: dict) -> tuple:
    try:
        r = requests.get(
            'https://api.themoviedb.org/3/configuration',
            params={'api_key': key}, timeout=10
        )
        if r.status_code == 200:
            return True, ''
        if r.status_code == 401:
            return False, r.json().get('status_message', 'Invalid API key')
        return False, f'Unexpected response: HTTP {r.status_code}'
    except requests.RequestException as e:
        return False, f'Network error — could not reach TMDB: {e}'


def _validate_tvdb(key: str, _config: dict) -> tuple:
    try:
        r = requests.post(
            'https://api4.thetvdb.com/v4/login',
            json={'apikey': key}, timeout=10
        )
        if r.status_code == 200:
            return True, ''
        msg = r.json().get('message', '') if r.headers.get('content-type', '').startswith('application/json') else ''
        return False, msg or f'HTTP {r.status_code} — check that your TVDB key is active'
    except requests.RequestException as e:
        return False, f'Network error — could not reach TVDB: {e}'


def _validate_plex(token: str, config: dict) -> tuple:
    plex_url = config.get('plex', {}).get('url', 'http://localhost:32400')
    try:
        r = requests.get(
            f'{plex_url}/library/sections',
            headers={'X-Plex-Token': token, 'Accept': 'application/json'},
            timeout=10
        )
        if r.status_code == 200:
            return True, ''
        if r.status_code == 401:
            return False, 'Token rejected — it may have been revoked or expired'
        return False, f'HTTP {r.status_code} from Plex at {plex_url}'
    except requests.RequestException as e:
        return False, f'Could not reach Plex at {plex_url}: {e}'


def _validate_fanart(key: str, _config: dict) -> tuple:
    # Use TMDB ID 550 (Fight Club) as a known-good probe
    try:
        r = requests.get(
            f'https://webservice.fanart.tv/v3/movies/550',
            params={'api_key': key}, timeout=10
        )
        if r.status_code == 200:
            return True, ''
        if r.status_code in (401, 403):
            return False, 'API key not recognised — verify it at fanart.tv/profile'
        return False, f'HTTP {r.status_code} from FanArt.tv'
    except requests.RequestException as e:
        return False, f'Network error — could not reach FanArt.tv: {e}'


def _validate_opensubtitles(key: str, config: dict) -> tuple:
    try:
        r = requests.get(
            'https://api.opensubtitles.com/api/v1/infos/user',
            headers={'Api-Key': key, 'Content-Type': 'application/json'},
            timeout=10
        )
        # 200 = authenticated, 401 = bad key, 403 = quota exceeded (key still valid)
        if r.status_code in (200, 403):
            return True, ''
        if r.status_code == 401:
            return False, 'API key not recognised — verify it at opensubtitles.com/consumers'
        return False, f'HTTP {r.status_code} from OpenSubtitles'
    except requests.RequestException as e:
        return False, f'Network error — could not reach OpenSubtitles: {e}'


def _validate_subdl(key: str, _config: dict) -> tuple:
    if not key:
        return True, ''   # Subdl works without a key
    try:
        r = requests.get(
            'https://api.subdl.com/api/v1/subtitles',
            params={'imdb_id': 'tt0133093', 'languages': 'EN', 'api_key': key},
            timeout=10
        )
        if r.status_code in (200, 204):
            return True, ''
        if r.status_code in (401, 403):
            return False, 'API key not recognised — verify it at subdl.com/account'
        return False, f'HTTP {r.status_code} from Subdl'
    except requests.RequestException as e:
        return False, f'Network error — could not reach Subdl: {e}'


def _validate_api_key(spec: dict, value: str, config: dict) -> tuple:
    """Dispatch to the correct validator for this spec. Returns (valid, error_str)."""
    validator = spec.get('validator')
    if validator is None:
        return True, ''   # no validator defined — assume valid
    try:
        return validator(value, config)
    except Exception as e:
        return False, f'Validation error: {e}'


# Keys to check; 'required' means a missing value blocks the run (not just a warning)
_KEY_SPECS = [
    {
        'path': ['tmdb', 'api_key'],
        'name': 'TMDB (The Movie Database)',
        'used_for': 'movie and TV show metadata, poster and backdrop images',
        'url': 'https://www.themoviedb.org/settings/api',
        'required': True,
        'validator': _validate_tmdb,
    },
    {
        'path': ['tvdb', 'api_key'],
        'name': 'TheTVDB',
        'used_for': 'TV show and episode metadata, season/episode artwork',
        'url': 'https://thetvdb.com/api-information',
        'required': True,
        'validator': _validate_tvdb,
    },
    {
        'path': ['plex', 'token'],
        'name': 'Plex',
        'used_for': 'triggering a Plex library refresh after each run',
        'url': 'https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/',
        'required': False,
        'validator': _validate_plex,
    },
    {
        'path': ['fanart_tv', 'api_key'],
        'name': 'FanArt.tv',
        'used_for': 'clearart, disc art, and logo images for movies and TV shows',
        'url': 'https://fanart.tv/get-an-api-key/',
        'required': False,
        'validator': _validate_fanart,
    },
    {
        'path': ['subtitles', 'opensubtitles', 'api_key'],
        'name': 'OpenSubtitles',
        'used_for': 'automatic subtitle download (primary source, 40 downloads/day free)',
        'url': 'https://www.opensubtitles.com/consumers',
        'required': False,
        'condition': lambda cfg: cfg.get('subtitles', {}).get('enabled', False),
        'validator': _validate_opensubtitles,
    },
    {
        'path': ['subtitles', 'subdl', 'api_key'],
        'name': 'Subdl',
        'used_for': 'subtitle download fallback (optional — works without a key)',
        'url': 'https://subdl.com/api',
        'required': False,
        'optional_skip': True,
        'condition': lambda cfg: cfg.get('subtitles', {}).get('enabled', False),
        'validator': _validate_subdl,
    },
]


def _prompt_key_with_validation(spec: dict, config: dict,
                                title_prefix: str = '') -> Optional[str]:
    """
    Show a text-input dialog for one API key. After entry, validate the key
    against the live API. If invalid, show an error dialog and offer a retry.
    Returns the valid value, or None if the user skipped.
    """
    service = spec['name']
    url = spec['url']
    used_for = spec['used_for']
    optional_skip = spec.get('optional_skip', False)
    required_label = '' if spec['required'] or optional_skip else ' (optional — press Skip to skip)'

    if optional_skip:
        base_msg = (
            f"{service} API key is optional — the service works without one.\n\n"
            f"Used for: {used_for}\n\n"
            f"Get a key at:\n{url}\n\n"
            f"Enter your {service} API key, or press Skip to continue without one:"
        )
    else:
        base_msg = (
            f"{service} API key is not configured.\n\n"
            f"Used for: {used_for}\n\n"
            f"Get a free key at:\n{url}\n\n"
            f"Enter your {service} API key{required_label}:"
        )

    title = f"{title_prefix}Plex Metadata Generator — {service} Key"

    while True:
        value = _prompt_text(title, base_msg)
        if not value or _is_placeholder(value):
            return None

        # Validate the entered key
        logger.info(f"  Validating {service} API key...")
        valid, error_msg = _validate_api_key(spec, value, config)

        if valid:
            logger.info(f"  ✓ {service} API key validated")
            return value

        # Key failed validation — show error and offer retry
        retry = _prompt_yesno(
            f'Plex Metadata Generator — {service} Key Invalid',
            f'The {service} API key could not be verified:\n\n'
            f'{error_msg}\n\n'
            f'Please verify the key is correct and active at:\n{url}\n\n'
            f'Try entering the key again?'
        )
        if not retry:
            logger.warning(f"  ⚠ {service} key skipped after failed validation")
            return None
        # Loop — show the input dialog again


def prompt_missing_api_keys(config: dict, config_path: str) -> dict:
    """
    For each API key that is missing or a placeholder, show a native input
    dialog, validate the entered key against the live API, and retry on failure.
    Offer to save the updated config to disk when done.
    """
    prompted: list = []   # (path, value) pairs that were successfully entered

    for spec in _KEY_SPECS:
        condition = spec.get('condition')
        if condition and not condition(config):
            continue

        current = _get_nested(config, *spec['path'])
        if not _is_placeholder(current):
            continue  # already set — handled by revalidation, not here

        value = _prompt_key_with_validation(spec, config)

        if value:
            _set_nested(config, spec['path'], value)
            prompted.append((spec['path'], value))
        elif spec['required']:
            logger.warning(f"  ⚠ {spec['name']} key skipped — {spec['used_for']} will not work")
        else:
            logger.info(f"  ⏭ {spec['name']} key skipped")

    if not prompted:
        return config

    keys_label = ', '.join(path[-1].replace('_', ' ') for path, _ in prompted)
    save = _prompt_yesno(
        'Plex Metadata Generator — Save API Keys',
        f"You entered {len(prompted)} API key(s): {keys_label}\n\n"
        f"Save to config file so you are not prompted again?\n\n"
        f"{config_path}"
    )
    if save:
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            logger.info(f"  ✓ Config saved: {config_path}")
        except IOError as e:
            logger.error(f"  Failed to save config: {e}")

    return config


# ---------------------------------------------------------------------------
# 15-day scheduled key revalidation
# ---------------------------------------------------------------------------

_REVALIDATION_INTERVAL_DAYS = 15
_STATE_FILENAME = 'key_validation_state.json'


def _state_file_path(cache_dir: str) -> Path:
    return Path(cache_dir) / _STATE_FILENAME


def _load_validation_state(cache_dir: str) -> dict:
    p = _state_file_path(cache_dir)
    try:
        if p.exists():
            return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        pass
    return {}


def _save_validation_state(cache_dir: str, state: dict):
    p = _state_file_path(cache_dir)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state, indent=2), encoding='utf-8')
    except Exception as e:
        logger.debug(f"Could not save validation state: {e}")


def revalidate_all_keys(config: dict, config_path: str,
                        cache_dir: Optional[str] = None) -> dict:
    if cache_dir is None:
        cache_dir = _default_cache_dir()
    """
    Check whether 15 days have passed since the last API key validation.
    If so, test every configured key against its live API. For any key that
    fails, show a blocking dialog with the exact expiry message and loop
    until a valid key is entered (or the user explicitly skips).
    Always updates the validation timestamp when a full check is performed.
    """
    state = _load_validation_state(cache_dir)
    last_raw = state.get('last_validated')

    if last_raw:
        try:
            last_dt = datetime.fromisoformat(last_raw)
            elapsed = datetime.now() - last_dt
            if elapsed.days < _REVALIDATION_INTERVAL_DAYS:
                logger.debug(
                    f"API key validation not due yet "
                    f"(last checked {elapsed.days}d ago; next in "
                    f"{_REVALIDATION_INTERVAL_DAYS - elapsed.days}d)"
                )
                return config
        except ValueError:
            pass  # malformed date — revalidate now

    logger.info(f"Running scheduled API key validation (every {_REVALIDATION_INTERVAL_DAYS} days)...")
    any_changed = False

    for spec in _KEY_SPECS:
        condition = spec.get('condition')
        if condition and not condition(config):
            continue

        current = _get_nested(config, *spec['path'])
        if not current or _is_placeholder(current):
            continue  # unconfigured keys are handled by prompt_missing_api_keys

        service = spec['name']
        url = spec['url']
        logger.info(f"  Checking {service} API key...")
        valid, error_msg = _validate_api_key(spec, current, config)

        if valid:
            logger.info(f"  ✓ {service} key OK")
            state[' '.join(spec['path'])] = {
                'valid': True,
                'checked_at': datetime.now().isoformat(),
            }
            continue

        # Key has expired or is inactive — show the blocking dialog
        logger.warning(f"  ✗ {service} key invalid: {error_msg}")

        while True:
            new_value = _prompt_text(
                f'Plex Metadata Generator — {service} Key Expired',
                f'The API key for {service} has expired or is inactive.\n\n'
                f'Please enter a new valid key.\n\n'
                f'The current job will pause and not continue until a new key is entered.\n\n'
                f'Error: {error_msg}\n\n'
                f'Get a new key at:\n{url}\n\n'
                f'Enter your new {service} API key:'
            )

            if not new_value or _is_placeholder(new_value):
                # User dismissed the dialog without entering a key
                skip = _prompt_yesno(
                    f'Plex Metadata Generator — Skip {service}?',
                    f'No new key was entered for {service}.\n\n'
                    f'The job will continue but {spec["used_for"]} will be unavailable.\n\n'
                    f'Skip {service} and continue?'
                )
                if skip:
                    logger.warning(f"  {service} skipped — {spec['used_for']} unavailable this run")
                    state[' '.join(spec['path'])] = {
                        'valid': False,
                        'checked_at': datetime.now().isoformat(),
                    }
                    break
                # User said No to skip — loop back to show the key-entry dialog again
                continue

            # Validate the newly entered key
            valid2, error2 = _validate_api_key(spec, new_value, config)
            if valid2:
                _set_nested(config, spec['path'], new_value)
                any_changed = True
                logger.info(f"  ✓ {service} key updated and validated")
                state[' '.join(spec['path'])] = {
                    'valid': True,
                    'checked_at': datetime.now().isoformat(),
                }
                break
            else:
                # Still invalid — ask whether to try again or skip
                try_again = _prompt_yesno(
                    f'Plex Metadata Generator — {service} Key Still Invalid',
                    f'The new key entered for {service} is also invalid:\n\n'
                    f'{error2}\n\n'
                    f'Please verify the key at:\n{url}\n\n'
                    f'Try entering the key again? (No = skip {service} for this run)'
                )
                if not try_again:
                    logger.warning(f"  {service} skipped after repeated invalid key")
                    state[' '.join(spec['path'])] = {
                        'valid': False,
                        'checked_at': datetime.now().isoformat(),
                    }
                    break

    state['last_validated'] = datetime.now().isoformat()
    _save_validation_state(cache_dir, state)

    if any_changed:
        save = _prompt_yesno(
            'Plex Metadata Generator — Save Updated Keys',
            f'One or more API keys were updated during validation.\n\n'
            f'Save changes to config file?\n\n{config_path}'
        )
        if save:
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
                logger.info(f"  ✓ Config saved with updated keys: {config_path}")
            except IOError as e:
                logger.error(f"  Failed to save config: {e}")

    return config


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

# ISO 639-1 → ISO 639-2/B (for ffmpeg -metadata:s:s language= tag)
_LANG2TO3: Dict[str, str] = {
    'en': 'eng', 'fr': 'fra', 'de': 'deu', 'es': 'spa', 'it': 'ita',
    'pt': 'por', 'ja': 'jpn', 'ko': 'kor', 'zh': 'zho', 'nl': 'nld',
    'ru': 'rus', 'ar': 'ara', 'sv': 'swe', 'no': 'nor', 'da': 'dan',
    'fi': 'fin', 'pl': 'pol', 'tr': 'tur', 'he': 'heb', 'cs': 'ces',
    'hu': 'hun', 'ro': 'ron', 'uk': 'ukr', 'el': 'ell', 'th': 'tha',
}


def detect_system_language() -> str:
    """Return ISO 639-1 two-letter language code derived from the OS locale."""
    # macOS: AppleLanguages pref is the most reliable indicator
    if platform.system() == 'Darwin':
        try:
            out = subprocess.check_output(
                ['defaults', 'read', '-g', 'AppleLanguages'],
                text=True, stderr=subprocess.DEVNULL
            )
            m = re.search(r'"([a-z]{2})[-_]', out, re.IGNORECASE)
            if m:
                return m.group(1).lower()
        except Exception:
            pass
    # Cross-platform: Python locale
    try:
        lang_str = locale.getdefaultlocale()[0]
        if lang_str:
            return lang_str.split('_')[0].lower()
    except Exception:
        pass
    return 'en'


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class ShowMetadata:
    title: str
    year: int
    plot: str
    rating: float
    tvdb_id: Optional[int] = None
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    poster_url: Optional[str] = None
    banner_url: Optional[str] = None
    fanart_url: Optional[str] = None
    genres: List[str] = field(default_factory=list)
    runtime: int = 45
    status: str = 'Continuing'


@dataclass
class EpisodeMetadata:
    title: str
    season: int
    episode: int
    plot: str
    air_date: str
    rating: float
    guest_stars: List[str] = field(default_factory=list)
    director: Optional[str] = None
    writer: Optional[str] = None
    thumb_url: Optional[str] = None


@dataclass
class MovieMetadata:
    title: str
    year: Optional[int] = None
    plot: Optional[str] = None
    rating: Optional[float] = None
    runtime: Optional[int] = None
    genres: List[str] = field(default_factory=list)
    studios: List[str] = field(default_factory=list)
    director: Optional[str] = None
    cast: List[dict] = field(default_factory=list)   # [{"name": ..., "role": ...}]
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None


# ---------------------------------------------------------------------------
# API Providers
# ---------------------------------------------------------------------------

class TunarrMetadataProvider:
    """Extract metadata from Tunarr's SQLite database."""

    def __init__(self, tunarr_db_path: str = '/opt/tunarr/cache/tunarr.db'):
        self.db_path = tunarr_db_path
        self.conn = None

    def connect(self) -> bool:
        if not self.db_path:
            return False
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"Connected to Tunarr database: {self.db_path}")
            return True
        except sqlite3.Error as e:
            logger.warning(f"Could not connect to Tunarr database: {e}")
            return False

    def disconnect(self):
        if self.conn:
            self.conn.close()

    def get_show_from_tunarr(self, show_title: str) -> Optional[Dict]:
        if not self.conn:
            return None
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT title, summary, duration, rating FROM programs WHERE title LIKE ? LIMIT 1",
                (f"%{show_title}%",)
            )
            result = cursor.fetchone()
            return dict(result) if result else None
        except sqlite3.Error as e:
            logger.error(f"Failed to lookup '{show_title}' in Tunarr: {e}")
            return None


def _tvdb_rating(score) -> float:
    """Convert TVDB score to a 0-10 rating.
    TVDB v4 /extended returns a raw popularity count in `score`, not a 0-10 average.
    Return 0 for any value > 10 (raw count) and clamp valid ratings to [0, 10].
    """
    try:
        v = float(score or 0)
    except (TypeError, ValueError):
        return 0.0
    return round(v, 1) if 0 < v <= 10 else 0.0


class TVDbProvider:
    """Fetch metadata from TheTVDB API (v4)."""

    BASE_URL = 'https://api4.thetvdb.com/v4'

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.bearer_token = None
        self.token_expiry = None

    def authenticate(self) -> bool:
        try:
            resp = requests.post(
                f'{self.BASE_URL}/login',
                json={'apikey': self.api_key},
                timeout=10
            )
            resp.raise_for_status()
            self.bearer_token = resp.json()['data']['token']
            self.token_expiry = datetime.now() + timedelta(days=6)
            logger.info("Authenticated with TVDb")
            return True
        except requests.RequestException as e:
            logger.error(f"TVDb authentication failed: {e}")
            return False

    def _headers(self) -> Dict:
        return {'Authorization': f'Bearer {self.bearer_token}', 'Content-Type': 'application/json'}

    def search_show(self, title: str) -> List[Dict]:
        """Search TVDB with fuzzy title variant fallback. Returns first non-empty result set."""
        if not self.bearer_token:
            return []
        try:
            for variant in fuzzy_variants(title):
                resp = requests.get(f'{self.BASE_URL}/search', headers=self._headers(),
                                    params={'query': variant}, timeout=10)
                resp.raise_for_status()
                data = resp.json().get('data', [])
                if data:
                    return data
            return []
        except requests.RequestException as e:
            logger.error(f"TVDb search failed for '{title}': {e}")
            return []

    def get_show(self, tvdb_id: int) -> Optional[ShowMetadata]:
        if not self.bearer_token:
            return None
        try:
            resp = requests.get(f'{self.BASE_URL}/series/{tvdb_id}/extended',
                                headers=self._headers(), timeout=10)
            resp.raise_for_status()
            data = resp.json()['data']

            meta = ShowMetadata(
                title=data.get('name', ''),
                year=int(data.get('firstAired', '').split('-')[0]) if data.get('firstAired') else 0,
                plot=data.get('overview', ''),
                rating=_tvdb_rating(data.get('score', 0)),
                tvdb_id=tvdb_id,
                imdb_id=data.get('imdbId'),
                runtime=data.get('runtime', 45),
                status=data.get('status', {}).get('name', 'Continuing'),
                genres=[g['name'] for g in data.get('genres', []) if isinstance(g, dict)],
            )
            def _tvdb_img(path: str) -> str:
                """Return a full TVDB artwork URL — path may be relative or already absolute."""
                if path.startswith('http'):
                    return path
                return f"https://artworks.thetvdb.com{path}"

            # Poster
            for image in data.get('artworks', []):
                if not isinstance(image, dict): continue
                if image.get('type') == 1:
                    meta.poster_url = _tvdb_img(image['image'])
                    break
            # Banner
            for image in data.get('artworks', []):
                if not isinstance(image, dict): continue
                if image.get('type') == 2:
                    meta.banner_url = _tvdb_img(image['image'])
                    break
            # Fanart/background
            for image in data.get('artworks', []):
                if not isinstance(image, dict): continue
                if image.get('type') == 3:
                    meta.fanart_url = _tvdb_img(image['image'])
                    break
            return meta
        except requests.RequestException as e:
            logger.error(f"Failed to fetch TVDb show {tvdb_id}: {e}")
            return None

    def get_episodes(self, tvdb_id: int, season: int) -> List[EpisodeMetadata]:
        if not self.bearer_token:
            return []
        try:
            resp = requests.get(
                f'{self.BASE_URL}/series/{tvdb_id}/episodes/default',
                headers=self._headers(),
                params={'season': season},
                timeout=10
            )
            resp.raise_for_status()
            episodes = []
            for ep in resp.json().get('data', []):
                if not isinstance(ep, dict):
                    continue
                num = ep.get('number')
                if num is None:
                    continue
                episodes.append(EpisodeMetadata(
                    title=ep.get('name', f'Episode {num}'),
                    season=season,
                    episode=num,
                    plot=ep.get('overview', ''),
                    air_date=ep.get('aired', ''),
                    rating=float(ep.get('score', 0) or 0),
                    director=ep.get('director'),
                    writer=ep.get('writer'),
                    thumb_url=ep.get('image'),
                ))
            return episodes
        except requests.RequestException as e:
            logger.error(f"Failed to fetch TVDb episodes for {tvdb_id} s{season}: {e}")
            return []


class TMDbProvider:
    """Fetch TV show metadata from TMDb."""

    BASE_URL = 'https://api.themoviedb.org/3'
    IMG_BASE = 'https://image.tmdb.org/t/p/original'

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _get(self, path: str, **params) -> dict:
        resp = requests.get(f'{self.BASE_URL}{path}',
                            params={'api_key': self.api_key, **params}, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def search_show(self, title: str) -> List[Dict]:
        """Search TMDb TV with fuzzy variant fallback."""
        try:
            for variant in fuzzy_variants(title):
                results = self._get('/search/tv', query=variant).get('results', [])
                if results:
                    return results
            return []
        except requests.RequestException as e:
            logger.error(f"TMDb TV search failed for '{title}': {e}")
            return []

    def get_show(self, tmdb_id: int) -> Optional[ShowMetadata]:
        try:
            data = self._get(f'/tv/{tmdb_id}', append_to_response='external_ids')
            ext = data.get('external_ids', {})
            meta = ShowMetadata(
                title=data.get('name', ''),
                year=int(data.get('first_air_date', '').split('-')[0]) if data.get('first_air_date') else 0,
                plot=data.get('overview', ''),
                rating=float(data.get('vote_average', 0) or 0),
                tmdb_id=tmdb_id,
                tvdb_id=ext.get('tvdb_id'),
                imdb_id=ext.get('imdb_id'),
                runtime=(data.get('episode_run_time') or [45])[0],
                status=data.get('status', 'Continuing'),
                genres=[g['name'] for g in data.get('genres', [])],
            )
            if data.get('poster_path'):
                meta.poster_url = f"{self.IMG_BASE}{data['poster_path']}"
            if data.get('backdrop_path'):
                meta.fanart_url = f"{self.IMG_BASE}{data['backdrop_path']}"
            return meta
        except requests.RequestException as e:
            logger.error(f"Failed to fetch TMDb show {tmdb_id}: {e}")
            return None

    def get_episodes(self, tmdb_id: int, season: int) -> List[EpisodeMetadata]:
        try:
            data = self._get(f'/tv/{tmdb_id}/season/{season}')
            episodes = []
            for ep in data.get('episodes', []):
                episodes.append(EpisodeMetadata(
                    title=ep.get('name', f"Episode {ep.get('episode_number')}"),
                    season=season,
                    episode=ep.get('episode_number'),
                    plot=ep.get('overview', ''),
                    air_date=ep.get('air_date', ''),
                    rating=float(ep.get('vote_average', 0) or 0),
                    thumb_url=(f"{self.IMG_BASE}{ep['still_path']}" if ep.get('still_path') else None),
                ))
            return episodes
        except requests.RequestException as e:
            logger.error(f"Failed to fetch TMDb episodes for {tmdb_id} s{season}: {e}")
            return []


class TMDbMovieProvider:
    """Fetch movie metadata from TMDb."""

    BASE_URL = 'https://api.themoviedb.org/3'
    IMG_BASE = 'https://image.tmdb.org/t/p/original'

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _get(self, path: str, **params) -> dict:
        resp = requests.get(f'{self.BASE_URL}{path}',
                            params={'api_key': self.api_key, **params}, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def search_movie(self, title: str, year: Optional[int] = None) -> Optional[int]:
        """Return TMDB ID for best match, or None. Tries fuzzy title variants on failure."""
        try:
            for variant in fuzzy_variants(title):
                if year:
                    results = self._get('/search/movie', query=variant, year=year).get('results', [])
                    if results:
                        return results[0]['id']
                results = self._get('/search/movie', query=variant).get('results', [])
                if results:
                    return results[0]['id']
            return None
        except requests.RequestException as e:
            logger.error(f"TMDb movie search failed for '{title}': {e}")
            return None

    def get_movie(self, tmdb_id: int) -> Optional[MovieMetadata]:
        """Fetch full movie metadata including credits and external IDs."""
        try:
            data = self._get(f'/movie/{tmdb_id}',
                             append_to_response='credits,external_ids')
            meta = MovieMetadata(
                title=data.get('title', ''),
                year=int(data.get('release_date', '').split('-')[0]) if data.get('release_date') else None,
                plot=data.get('overview', ''),
                rating=float(data.get('vote_average', 0) or 0),
                runtime=data.get('runtime'),
                genres=[g['name'] for g in data.get('genres', [])],
                studios=[c['name'] for c in data.get('production_companies', [])[:3]],
                tmdb_id=tmdb_id,
                imdb_id=data.get('external_ids', {}).get('imdb_id') or data.get('imdb_id'),
            )
            # Director
            for crew in data.get('credits', {}).get('crew', []):
                if crew.get('job') == 'Director':
                    meta.director = crew['name']
                    break
            # Cast (top 10)
            meta.cast = [
                {'name': a['name'], 'role': a.get('character', '')}
                for a in data.get('credits', {}).get('cast', [])[:10]
            ]
            # Artwork
            if data.get('poster_path'):
                meta.poster_url = f"{self.IMG_BASE}{data['poster_path']}"
            if data.get('backdrop_path'):
                meta.backdrop_url = f"{self.IMG_BASE}{data['backdrop_path']}"
            return meta
        except requests.RequestException as e:
            logger.error(f"Failed to fetch TMDb movie {tmdb_id}: {e}")
            return None


class FanartTvProvider:
    """Fetch extended artwork from FanArt.tv API."""

    BASE_URL = 'https://webservice.fanart.tv/v3'

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_movie_artwork(self, tmdb_id: int) -> dict:
        """
        Return dict of artwork URLs for a movie.
        Keys: clearart_url, disc_url, logo_url, poster_url (fallback), backdrop_url (fallback)
        """
        try:
            resp = requests.get(
                f'{self.BASE_URL}/movies/{tmdb_id}',
                params={'api_key': self.api_key},
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                'clearart_url': self._pick(data, 'hdmovieclearart', 'movieart'),
                'disc_url':     self._pick_disc(data.get('moviedisc', [])),
                'logo_url':     self._pick(data, 'hdmovielogo', 'movielogo'),
                'poster_url':   self._pick(data, 'movieposter'),
                'backdrop_url': self._pick(data, 'moviebackground'),
            }
        except requests.RequestException as e:
            logger.warning(f"FanArt.tv movie artwork fetch failed for TMDB {tmdb_id}: {e}")
            return {}

    def get_tv_artwork(self, tvdb_id: int) -> dict:
        """
        Return dict of artwork URLs for a TV show.
        Keys: clearart_url, logo_url, landscape_url
        """
        try:
            resp = requests.get(
                f'{self.BASE_URL}/tv/{tvdb_id}',
                params={'api_key': self.api_key},
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                'clearart_url':  self._pick(data, 'hdclearart', 'clearart'),
                'logo_url':      self._pick(data, 'hdtvlogo', 'clearlogo'),
                'landscape_url': self._pick(data, 'tvthumb'),
            }
        except requests.RequestException as e:
            logger.warning(f"FanArt.tv TV artwork fetch failed for TVDB {tvdb_id}: {e}")
            return {}

    def _pick(self, data: dict, *keys: str) -> Optional[str]:
        for k in keys:
            items = data.get(k, [])
            if items:
                return items[0].get('url')
        return None

    def _pick_disc(self, items: list) -> Optional[str]:
        for disc_type in ('bluray', 'dvd', None):
            for item in items:
                if disc_type is None or item.get('disc_type') == disc_type:
                    return item.get('url')
        return None


# ---------------------------------------------------------------------------
# Subtitle Providers
# ---------------------------------------------------------------------------

class OpenSubtitlesProvider:
    """Download subtitles from OpenSubtitles REST API v1."""

    BASE_URL = 'https://api.opensubtitles.com/api/v1'

    def __init__(self, cfg: dict):
        self.api_key = cfg.get('api_key', '')
        self.username = cfg.get('username', '')
        self.password = cfg.get('password', '')
        self._token: Optional[str] = None

    def _headers(self) -> dict:
        h = {'Api-Key': self.api_key, 'Content-Type': 'application/json'}
        if self._token:
            h['Authorization'] = f'Bearer {self._token}'
        return h

    def authenticate(self) -> bool:
        if not (self.username and self.password):
            return True  # anonymous mode — API key only
        try:
            resp = requests.post(
                f'{self.BASE_URL}/login',
                json={'username': self.username, 'password': self.password},
                headers={'Api-Key': self.api_key, 'Content-Type': 'application/json'},
                timeout=15
            )
            if resp.status_code == 200:
                self._token = resp.json().get('token')
                return True
        except requests.RequestException:
            pass
        return False

    def search_movie(self, imdb_id: Optional[str], tmdb_id: Optional[int], lang: str) -> List[dict]:
        params: dict = {'languages': lang, 'order_by': 'download_count'}
        if imdb_id:
            # Strip 'tt' prefix — OpenSubtitles expects numeric IMDb ID
            params['imdb_id'] = imdb_id.lstrip('t')
        elif tmdb_id:
            params['tmdb_id'] = tmdb_id
            params['type'] = 'movie'
        else:
            return []
        try:
            resp = requests.get(f'{self.BASE_URL}/subtitles', headers=self._headers(),
                                params=params, timeout=15)
            if resp.status_code == 401:
                self.authenticate()
                resp = requests.get(f'{self.BASE_URL}/subtitles', headers=self._headers(),
                                    params=params, timeout=15)
            resp.raise_for_status()
            return resp.json().get('data', [])
        except requests.RequestException as e:
            logger.debug(f"OpenSubtitles movie search failed: {e}")
            return []

    def search_episode(self, show_imdb_id: str, season: int, episode: int, lang: str) -> List[dict]:
        params = {
            'parent_imdb_id': show_imdb_id.lstrip('t'),
            'season_number': season,
            'episode_number': episode,
            'languages': lang,
            'order_by': 'download_count',
        }
        try:
            resp = requests.get(f'{self.BASE_URL}/subtitles', headers=self._headers(),
                                params=params, timeout=15)
            if resp.status_code == 401:
                self.authenticate()
                resp = requests.get(f'{self.BASE_URL}/subtitles', headers=self._headers(),
                                    params=params, timeout=15)
            resp.raise_for_status()
            return resp.json().get('data', [])
        except requests.RequestException as e:
            logger.debug(f"OpenSubtitles episode search failed: {e}")
            return []

    def download(self, candidate: dict) -> Optional[bytes]:
        """Download SRT bytes for the best file in this candidate."""
        files = candidate.get('attributes', {}).get('files', [])
        if not files:
            return None
        file_id = files[0].get('file_id')
        if not file_id:
            return None
        try:
            resp = requests.post(
                f'{self.BASE_URL}/download',
                json={'file_id': file_id},
                headers=self._headers(),
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            remaining = data.get('requests_remaining')
            if remaining is not None:
                logger.info(f"  OpenSubtitles quota: {remaining} downloads remaining today")
            link = data.get('link')
            if not link:
                return None
            dl = requests.get(link, timeout=60)
            dl.raise_for_status()
            return dl.content
        except requests.RequestException as e:
            logger.debug(f"OpenSubtitles download failed: {e}")
            return None


class SubdlProvider:
    """Download subtitles from Subdl API (fallback)."""

    SEARCH_URL = 'https://api.subdl.com/api/v1/subtitles'
    DOWNLOAD_BASE = 'https://dl.subdl.com'

    def __init__(self, cfg: dict):
        self.api_key = cfg.get('api_key', '')

    def _params(self, extra: dict) -> dict:
        p = {'languages': 'EN', **extra}
        if self.api_key:
            p['api_key'] = self.api_key
        return p

    def search_movie(self, imdb_id: Optional[str], tmdb_id: Optional[int], lang: str) -> List[dict]:
        params = self._params({'languages': lang.upper()})
        if imdb_id:
            params['imdb_id'] = imdb_id  # Subdl wants tt-prefixed ID
        elif tmdb_id:
            params['tmdb_id'] = tmdb_id
            params['type'] = 'movie'
        else:
            return []
        try:
            resp = requests.get(self.SEARCH_URL, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json().get('subtitles', [])
        except requests.RequestException as e:
            logger.debug(f"Subdl movie search failed: {e}")
            return []

    def search_episode(self, show_imdb_id: str, season: int, episode: int, lang: str) -> List[dict]:
        params = self._params({
            'imdb_id': show_imdb_id,
            'season': season,
            'episode': episode,
            'languages': lang.upper(),
        })
        try:
            resp = requests.get(self.SEARCH_URL, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json().get('subtitles', [])
        except requests.RequestException as e:
            logger.debug(f"Subdl episode search failed: {e}")
            return []

    def download(self, candidate: dict) -> Optional[bytes]:
        """Download and extract the first SRT from the zip."""
        url_path = candidate.get('url')
        if not url_path:
            return None
        try:
            resp = requests.get(f'{self.DOWNLOAD_BASE}{url_path}', timeout=60)
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                for name in zf.namelist():
                    if name.lower().endswith('.srt'):
                        return zf.read(name)
        except Exception as e:
            logger.debug(f"Subdl download failed: {e}")
        return None


class SubtitleDownloader:
    """Orchestrate subtitle download, sidecar writing, and MP4 embedding."""

    def __init__(self, cfg: dict, lang: str):
        self.lang = lang                              # e.g. 'en'
        self.lang3 = _LANG2TO3.get(lang, lang)       # e.g. 'eng'
        self.do_embed = cfg.get('embed_in_file', True)
        self.do_sidecar = cfg.get('sidecar', True)
        self.providers: List = []

        os_cfg = cfg.get('opensubtitles', {})
        if os_cfg.get('api_key'):
            prov = OpenSubtitlesProvider(os_cfg)
            prov.authenticate()
            self.providers.append(prov)

        sd_cfg = cfg.get('subdl')
        if sd_cfg is not None:
            self.providers.append(SubdlProvider(sd_cfg if isinstance(sd_cfg, dict) else {}))

    # --- skip checks ---

    def _sidecar_path(self, video_path: Path) -> Path:
        return video_path.parent / f"{video_path.stem}.{self.lang}.srt"

    def _sidecar_exists(self, video_path: Path) -> bool:
        return self._sidecar_path(video_path).exists()

    def _embedded_sub_exists(self, video_path: Path) -> bool:
        """Use ffprobe to detect existing subtitle tracks in the video."""
        if not shutil.which('ffprobe'):
            return False
        try:
            out = subprocess.check_output(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json',
                 '-show_streams', '-select_streams', 's', str(video_path)],
                text=True, stderr=subprocess.DEVNULL, timeout=30
            )
            streams = json.loads(out).get('streams', [])
            if not streams:
                return False
            for s in streams:
                lang_tag = s.get('tags', {}).get('language', '')
                if lang_tag in (self.lang, self.lang3):
                    return True
            return True  # embedded subtitle present (wrong lang — still skip re-embed)
        except Exception:
            return False

    def _should_skip(self, video_path: Path) -> bool:
        if not self._sidecar_exists(video_path):
            return False
        if self.do_embed and not self._embedded_sub_exists(video_path):
            return False
        return True

    # --- download pipeline ---

    def _fetch_srt(self, candidates: List[dict]) -> Optional[bytes]:
        for candidate in candidates[:5]:  # try top 5 results
            for prov in self.providers:
                srt = prov.download(candidate)
                if srt and len(srt) > 100:
                    return srt
        return None

    def process_movie(self, folder: Path, video_path: Path,
                      imdb_id: Optional[str], tmdb_id: Optional[int]):
        if self._should_skip(video_path):
            logger.debug(f"  ⏭ Subtitle already present for {video_path.name}")
            return

        candidates: List[dict] = []
        for prov in self.providers:
            candidates = prov.search_movie(imdb_id, tmdb_id, self.lang)
            if candidates:
                break

        if not candidates:
            logger.debug(f"  No subtitles found for {video_path.name} [{self.lang}]")
            return

        srt_bytes = self._fetch_srt(candidates)
        if not srt_bytes:
            logger.warning(f"  ⚠ Subtitle download failed for {video_path.name}")
            return

        self._write_and_embed(video_path, srt_bytes)

    def process_episode(self, video_path: Path, show_imdb_id: str,
                        season: int, episode: int):
        if self._should_skip(video_path):
            logger.debug(f"  ⏭ Subtitle already present for {video_path.name}")
            return

        candidates: List[dict] = []
        for prov in self.providers:
            candidates = prov.search_episode(show_imdb_id, season, episode, self.lang)
            if candidates:
                break

        if not candidates:
            logger.debug(f"  No subtitles found for {video_path.name} S{season:02d}E{episode:02d}")
            return

        srt_bytes = self._fetch_srt(candidates)
        if not srt_bytes:
            logger.warning(f"  ⚠ Subtitle download failed for {video_path.name}")
            return

        self._write_and_embed(video_path, srt_bytes)

    def _write_and_embed(self, video_path: Path, srt_bytes: bytes):
        srt_path = self._sidecar_path(video_path)

        if self.do_sidecar:
            try:
                srt_path.write_bytes(srt_bytes)
                logger.info(f"  ✓ Subtitle sidecar: {srt_path.name}")
            except IOError as e:
                logger.error(f"  Failed to write sidecar: {e}")
                return

        if self.do_embed:
            self._embed_subtitle(video_path, srt_path)

    def _embed_subtitle(self, video_path: Path, srt_path: Path):
        if not shutil.which('ffmpeg'):
            logger.warning("  ffmpeg not found — cannot embed subtitle (sidecar only)")
            return

        if video_path.suffix.lower() not in ('.mp4', '.m4v'):
            logger.info(f"  ⚠ Embed skipped — {video_path.suffix} not MP4/M4V (sidecar only)")
            return

        tmp = video_path.with_name(video_path.stem + '.tmp.mp4')
        try:
            result = subprocess.run(
                [
                    'ffmpeg', '-y',
                    '-i', str(video_path),
                    '-i', str(srt_path),
                    '-c', 'copy',
                    '-c:s', 'mov_text',
                    '-metadata:s:s:0', f'language={self.lang3}',
                    '-metadata:s:s:0', f'title={self.lang.upper()} Subtitles',
                    '-disposition:s:0', 'default',
                    str(tmp)
                ],
                capture_output=True,
                timeout=600
            )
            if result.returncode != 0:
                err = result.stderr.decode(errors='replace')[:300]
                logger.error(f"  ffmpeg embed failed: {err}")
                tmp.unlink(missing_ok=True)
                return

            # Sanity check: temp file must be ≥ 95% of original
            orig_size = video_path.stat().st_size
            if tmp.stat().st_size < orig_size * 0.95:
                logger.error(f"  Embed sanity check failed — temp file too small, aborting")
                tmp.unlink(missing_ok=True)
                return

            tmp.replace(video_path)
            logger.info(f"  ✓ Embedded subtitle track ({self.lang3}) into {video_path.name}")

        except subprocess.TimeoutExpired:
            logger.error(f"  ffmpeg timed out for {video_path.name}")
            tmp.unlink(missing_ok=True)
        except Exception as e:
            logger.error(f"  Embed failed: {e}")
            tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# NFO Generator
# ---------------------------------------------------------------------------

class PlexNFOGenerator:
    """Generate Plex-compliant NFO files (same XML format as scraper.py)."""

    @staticmethod
    def _pretty(root: ET.Element) -> str:
        raw = ET.tostring(root, encoding='unicode')
        dom = xml.dom.minidom.parseString(raw)
        return dom.toprettyxml(indent='  ', encoding=None).replace(
            '<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        )

    def generate_show_nfo(self, metadata: ShowMetadata) -> str:
        root = ET.Element('tvshow')
        ET.SubElement(root, 'title').text = metadata.title
        ET.SubElement(root, 'originaltitle').text = metadata.title
        if metadata.year:
            ET.SubElement(root, 'year').text = str(metadata.year)
        ET.SubElement(root, 'plot').text = metadata.plot or ''
        ET.SubElement(root, 'rating').text = str(metadata.rating or 0)
        ET.SubElement(root, 'runtime').text = str(metadata.runtime)
        ET.SubElement(root, 'status').text = metadata.status
        if metadata.tvdb_id:
            uid = ET.SubElement(root, 'uniqueid')
            uid.set('type', 'tvdb')
            uid.set('default', 'true')
            uid.text = str(metadata.tvdb_id)
        if metadata.tmdb_id:
            uid = ET.SubElement(root, 'uniqueid')
            uid.set('type', 'tmdb')
            uid.set('default', 'false' if metadata.tvdb_id else 'true')
            uid.text = str(metadata.tmdb_id)
        if metadata.imdb_id:
            uid = ET.SubElement(root, 'uniqueid')
            uid.set('type', 'imdb')
            uid.set('default', 'false')
            uid.text = metadata.imdb_id
        for genre in (metadata.genres or []):
            ET.SubElement(root, 'genre').text = genre
        return self._pretty(root)

    def generate_episode_nfo(self, metadata: EpisodeMetadata) -> str:
        root = ET.Element('episodedetails')
        ET.SubElement(root, 'title').text = metadata.title
        ET.SubElement(root, 'season').text = str(metadata.season)
        ET.SubElement(root, 'episode').text = str(metadata.episode)
        ET.SubElement(root, 'plot').text = metadata.plot or ''
        if metadata.air_date:
            ET.SubElement(root, 'aired').text = metadata.air_date
        ET.SubElement(root, 'rating').text = str(metadata.rating or 0)
        if metadata.director:
            ET.SubElement(root, 'director').text = metadata.director
        if metadata.writer:
            ET.SubElement(root, 'writer').text = metadata.writer
        return self._pretty(root)

    def generate_movie_nfo(self, metadata: MovieMetadata) -> str:
        """Generate Movie.nfo — identical format to scraper.py build_movie_nfo()."""
        root = ET.Element('movie')
        ET.SubElement(root, 'title').text = metadata.title
        ET.SubElement(root, 'originaltitle').text = metadata.title
        if metadata.year:
            ET.SubElement(root, 'year').text = str(metadata.year)
        ET.SubElement(root, 'plot').text = metadata.plot or ''
        if metadata.rating is not None:
            ET.SubElement(root, 'rating').text = f"{metadata.rating:.1f}"
        if metadata.runtime:
            ET.SubElement(root, 'runtime').text = str(metadata.runtime)
        for genre in (metadata.genres or []):
            ET.SubElement(root, 'genre').text = genre
        for studio in (metadata.studios or []):
            ET.SubElement(root, 'studio').text = studio
        if metadata.director:
            ET.SubElement(root, 'director').text = metadata.director
        for actor in (metadata.cast or []):
            act_el = ET.SubElement(root, 'actor')
            ET.SubElement(act_el, 'name').text = actor.get('name', '')
            ET.SubElement(act_el, 'role').text = actor.get('role', '')
        # IDs — same format as scraper.py
        if metadata.tmdb_id:
            uid = ET.SubElement(root, 'uniqueid')
            uid.set('type', 'tmdb')
            uid.set('default', 'true')
            uid.text = str(metadata.tmdb_id)
        if metadata.imdb_id:
            uid = ET.SubElement(root, 'uniqueid')
            uid.set('type', 'imdb')
            uid.set('default', 'false')
            uid.text = metadata.imdb_id
        return self._pretty(root)


# ---------------------------------------------------------------------------
# Artwork Downloader
# ---------------------------------------------------------------------------

class MetadataDownloader:
    """Download and cache artwork files."""

    MIN_VALID_BYTES = 1000   # Same threshold as extract_artwork.py

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path(_default_cache_dir())
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def download_image(self, url: str, dest: Path, force: bool = False) -> bool:
        """Download url to dest. Returns True on success."""
        if not url:
            return False
        if dest.exists() and not force:
            logger.debug(f"Already exists: {dest}")
            return True
        try:
            resp = requests.get(url, timeout=15, stream=True)
            resp.raise_for_status()
            content = resp.content
            if len(content) < self.MIN_VALID_BYTES:
                logger.warning(f"Downloaded file too small ({len(content)} bytes), skipping: {dest}")
                return False
            dest.write_bytes(content)
            logger.info(f"Downloaded: {dest.name} → {dest.parent}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to download {dest.name}: {e}")
            return False


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------

# Plex Local Media Assets — complete artwork filenames per item type
_MOVIE_ART_FILES = ('poster.jpg', 'folder.jpg', 'backdrop.jpg',
                    'clearart.png', 'disc.png', 'logo.png')
_TV_SHOW_ART_FILES = ('poster.jpg', 'banner.jpg', 'fanart.jpg',
                      'clearart.png', 'logo.png', 'landscape.jpg')


class PlexMetadataOrchestrator:
    """Main orchestrator for metadata generation and artwork download."""

    def __init__(self, config: Dict, force: bool = False, workers: int = 1):
        self.config = config
        self.force = force
        self.workers = max(1, workers)

        # Library roots — support list (plural) or single-path (singular) config keys
        self.tv_library_roots = self._resolve_roots(
            config, 'tv_library_roots', 'tv_library_root', 'library_root'
        )
        self.movies_library_roots = self._resolve_roots(
            config, 'movies_library_roots', 'movies_library_root'
        )
        self.music_library_roots = self._resolve_roots(
            config, 'music_library_roots', 'music_library_root'
        )
        # Backward-compat aliases (single Path) — used by code that hasn't been updated yet
        self.tv_library_root = self.tv_library_roots[0] if self.tv_library_roots else Path('/mnt/media/TV')
        self.movies_library_root = self.movies_library_roots[0] if self.movies_library_roots else None

        # Plex config
        plex = config.get('plex', {})
        self.plex_url = plex.get('url', 'http://localhost:32400')
        self.plex_token = plex.get('token')
        self.tv_library_key = str(plex.get('tv_library_key') or plex.get('library_key', '1'))
        self.movies_library_key = str(plex.get('movies_library_key', ''))

        # API providers
        tvdb_cfg = config.get('tvdb', {})
        tmdb_cfg = config.get('tmdb', {})
        fanart_cfg = config.get('fanart_tv', {})
        tunarr_cfg = config.get('tunarr', {})

        self.tvdb = TVDbProvider(tvdb_cfg['api_key']) if tvdb_cfg.get('api_key') else None
        self.tmdb_tv = TMDbProvider(tmdb_cfg['api_key']) if tmdb_cfg.get('api_key') else None
        self.tmdb_movie = TMDbMovieProvider(tmdb_cfg['api_key']) if tmdb_cfg.get('api_key') else None
        self.fanart = FanartTvProvider(fanart_cfg['api_key']) if fanart_cfg.get('api_key') else None
        self.tunarr = TunarrMetadataProvider(
            tunarr_cfg.get('db_path', '/opt/tunarr/cache/tunarr.db')
        )

        self.nfo = PlexNFOGenerator()
        self.dl = MetadataDownloader(config.get('cache_dir') or None)

        if self.fanart is None:
            logger.warning("fanart_tv.api_key not configured — clearart, disc, and logo artwork will be skipped")

        if self.tvdb:
            self.tvdb.authenticate()

        # Subtitle downloader — only active when subtitles.enabled is true in config
        sub_cfg = config.get('subtitles', {})
        if sub_cfg.get('enabled', False):
            lang = sub_cfg.get('language', 'auto')
            if lang == 'auto':
                lang = detect_system_language()
            logger.info(f"Subtitle language: {lang} ({'OS locale' if sub_cfg.get('language', 'auto') == 'auto' else 'config'})")
            self.subtitle_dl: Optional[SubtitleDownloader] = SubtitleDownloader(sub_cfg, lang)
        else:
            self.subtitle_dl = None

    # ------------------------------------------------------------------
    # Library root helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_roots(config: dict, plural_key: str, *singular_keys: str) -> List[Path]:
        """
        Return a list of Path objects for a library type.
        Checks plural_key (list) first, then each singular_key in order.
        Returns [] if nothing is configured.
        """
        roots = config.get(plural_key)
        if roots and isinstance(roots, list):
            return [Path(r) for r in roots if r]
        for key in singular_keys:
            v = config.get(key)
            if v:
                return [Path(v)]
        return []

    # ------------------------------------------------------------------
    # Selective processing helpers
    # ------------------------------------------------------------------

    def _needs_nfo(self, nfo_path: Path) -> bool:
        return self.force or not nfo_path.exists()

    def _missing_art(self, folder: Path, filenames: tuple) -> Set[str]:
        """Return set of artwork filenames not yet present in folder."""
        if self.force:
            return set(filenames)
        return {f for f in filenames if not (folder / f).exists()}

    @staticmethod
    def _extract_tmdb_id_from_nfo(nfo_path: Path) -> Optional[int]:
        """Parse existing NFO for <uniqueid type="tmdb"> to skip search API call."""
        try:
            tree = ET.parse(nfo_path)
            for uid in tree.findall('uniqueid'):
                if uid.get('type') == 'tmdb' and uid.text:
                    return int(uid.text.strip())
        except Exception:
            pass
        return None

    @staticmethod
    def _extract_imdb_id_from_nfo(nfo_path: Path) -> Optional[str]:
        """Parse existing NFO for <uniqueid type="imdb"> — used for subtitle lookup."""
        try:
            tree = ET.parse(nfo_path)
            for uid in tree.findall('uniqueid'):
                if uid.get('type') == 'imdb' and uid.text:
                    return uid.text.strip()
        except Exception:
            pass
        return None

    @staticmethod
    def _find_video_file(folder: Path) -> Optional[Path]:
        """Return the primary video file in a folder (largest file wins when ambiguous)."""
        exts = {'.mp4', '.m4v', '.mkv', '.avi', '.mov'}
        files = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in exts]
        if not files:
            return None
        return max(files, key=lambda f: f.stat().st_size)

    # ------------------------------------------------------------------
    # Movie library processing
    # ------------------------------------------------------------------

    def process_movie_library(self, specific_movie: str = None):
        if not self.movies_library_roots:
            logger.warning("movies_library_root not configured — skipping movie processing")
            return

        for root in self.movies_library_roots:
            if not root.exists():
                logger.error(f"Movie library root does not exist: {root}")
                continue
            logger.info(f"Scanning movie library: {root} ({self.workers} worker(s))")
            folders = [
                f for f in sorted(root.iterdir())
                if f.is_dir() and not f.name.startswith('.')
                and (not specific_movie or f.name == specific_movie)
                and not is_multipart(f.name)
            ]
            if self.workers > 1:
                with ThreadPoolExecutor(max_workers=self.workers) as ex:
                    futures = {ex.submit(self._process_one_movie, f): f for f in folders}
                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            logger.error(f"Error processing {futures[future].name}: {e}")
            else:
                for folder in folders:
                    self._process_one_movie(folder)
                    time.sleep(0.5)

        if self.movies_library_key:
            self.refresh_plex_library(self.movies_library_key)

    def _process_one_movie(self, folder: Path):
        nfo_path = folder / 'Movie.nfo'
        needs_nfo = self._needs_nfo(nfo_path)
        missing_art = self._missing_art(folder, _MOVIE_ART_FILES)

        if not needs_nfo and not missing_art:
            logger.info(f"⏭ {folder.name} — already complete")
            return

        logger.info(f"Processing movie: {folder.name}")

        # --- Resolve TMDB ID ---
        tmdb_id = None
        meta = None

        if not needs_nfo and nfo_path.exists():
            # Art-only run — get ID from existing NFO, skip search
            tmdb_id = self._extract_tmdb_id_from_nfo(nfo_path)
            if tmdb_id:
                logger.debug(f"  Found TMDB ID {tmdb_id} in existing NFO")

        if tmdb_id is None:
            # Check for embedded TMDB ID in folder name, e.g. "Inception (2010) {tmdb-27205}"
            folder_tmdb_match = re.search(r'\{tmdb-(\d+)\}', folder.name, re.IGNORECASE)
            if folder_tmdb_match:
                tmdb_id = int(folder_tmdb_match.group(1))
                logger.debug(f"  Using TMDB ID {tmdb_id} from folder name tag")

        if tmdb_id is None:
            # Need to search — extract year and clean title from folder name
            year_match = re.search(r'\((\d{4})\)', folder.name)
            year = int(year_match.group(1)) if year_match else None
            # Strip {…} tags and trailing year before searching
            title = re.sub(r'\s*\{[^}]+\}\s*', ' ', folder.name)
            title = re.sub(r'\s*\(\d{4}\)\s*$', '', title).strip()
            tmdb_id = self.tmdb_movie.search_movie(title, year) if self.tmdb_movie else None
            if not tmdb_id:
                logger.warning(f"  ❌ Could not find TMDB match for: {folder.name}")
                return

        # --- Fetch full metadata ---
        if needs_nfo or meta is None:
            meta = self.tmdb_movie.get_movie(tmdb_id) if self.tmdb_movie else None
            if not meta:
                logger.warning(f"  ❌ Failed to fetch TMDB metadata for ID {tmdb_id}")
                return

        # --- Write NFO ---
        if needs_nfo:
            nfo_content = self.nfo.generate_movie_nfo(meta)
            try:
                nfo_path.write_text(nfo_content, encoding='utf-8')
                logger.info(f"  ✓ Wrote Movie.nfo")
            except IOError as e:
                logger.error(f"  Failed to write Movie.nfo: {e}")

        # --- Download TMDB artwork (poster + backdrop) ---
        need_poster = 'poster.jpg' in missing_art or 'folder.jpg' in missing_art
        need_backdrop = 'backdrop.jpg' in missing_art

        # Determine poster URL: TMDB preferred, FanArt.tv fallback
        poster_url = meta.poster_url if meta else None
        backdrop_url = meta.backdrop_url if meta else None

        # Pre-fetch FanArt.tv data if any FanArt.tv files are missing
        fanart_data = {}
        need_fanart_files = missing_art & {'clearart.png', 'disc.png', 'logo.png'}
        need_fanart_fallbacks = (not poster_url and need_poster) or (not backdrop_url and need_backdrop)

        if self.fanart and (need_fanart_files or need_fanart_fallbacks):
            fanart_data = self.fanart.get_movie_artwork(tmdb_id)
            if not poster_url:
                poster_url = fanart_data.get('poster_url')
            if not backdrop_url:
                backdrop_url = fanart_data.get('backdrop_url')

        if need_poster:
            # Try embedded artwork first (Subler/iTunes MP4 preferred over API download)
            video_file = self._find_video_file(folder)
            if video_file and self._extract_embedded_artwork(video_file, folder / 'poster.jpg'):
                shutil.copy2(folder / 'poster.jpg', folder / 'folder.jpg')
                logger.info(f"  ✓ Extracted poster.jpg from embedded artwork ({video_file.name})")
                need_poster = False  # satisfied from embedded art
            elif poster_url and self.dl.download_image(poster_url, folder / 'poster.jpg'):
                shutil.copy2(folder / 'poster.jpg', folder / 'folder.jpg')
                logger.info(f"  ✓ Copied poster.jpg → folder.jpg")
            elif not poster_url:
                logger.warning(f"  ⚠ No poster source found for {folder.name}")
        if 'folder.jpg' in missing_art and (folder / 'poster.jpg').exists():
            shutil.copy2(folder / 'poster.jpg', folder / 'folder.jpg')

        if need_backdrop and backdrop_url:
            self.dl.download_image(backdrop_url, folder / 'backdrop.jpg')
        elif need_backdrop:
            logger.warning(f"  ⚠ No backdrop source found for {folder.name}")

        # --- Download FanArt.tv exclusive artwork ---
        if need_fanart_files:
            if not self.fanart:
                logger.warning(f"  ⚠ FanArt.tv not configured — skipping clearart/disc/logo")
            else:
                if not fanart_data:
                    fanart_data = self.fanart.get_movie_artwork(tmdb_id)
                art_map = {
                    'clearart.png': fanart_data.get('clearart_url'),
                    'disc.png':     fanart_data.get('disc_url'),
                    'logo.png':     fanart_data.get('logo_url'),
                }
                for fname, url in art_map.items():
                    if fname in missing_art:
                        if url:
                            self.dl.download_image(url, folder / fname)
                        else:
                            logger.debug(f"  ⚠ No FanArt.tv source for {fname}")

        # --- Download subtitles ---
        if self.subtitle_dl:
            video_file = self._find_video_file(folder)
            if video_file:
                imdb_id = (meta.imdb_id if meta else None) or self._extract_imdb_id_from_nfo(nfo_path)
                tmdb_id_sub = meta.tmdb_id if meta else tmdb_id
                self.subtitle_dl.process_movie(folder, video_file, imdb_id, tmdb_id_sub)
            else:
                logger.debug(f"  No video file in {folder.name} — skipping subtitles")

    # ------------------------------------------------------------------
    # TV library processing
    # ------------------------------------------------------------------

    def process_tv_library(self, specific_show: str = None):
        if not self.tv_library_roots:
            logger.error("tv_library_root not configured — skipping TV processing")
            return

        for root in self.tv_library_roots:
            if not root.exists():
                logger.error(f"TV library root does not exist: {root}")
                continue
            logger.info(f"Scanning TV library: {root} ({self.workers} worker(s))")
            shows = [
                d for d in sorted(root.iterdir())
                if d.is_dir() and not d.name.startswith('.')
                and (not specific_show or d.name == specific_show)
            ]
            if self.workers > 1:
                with ThreadPoolExecutor(max_workers=self.workers) as ex:
                    futures = {ex.submit(self._process_one_show, d): d for d in shows}
                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            logger.error(f"Error processing {futures[future].name}: {e}")
            else:
                for show_dir in shows:
                    self._process_one_show(show_dir)
                    time.sleep(0.5)

        self.refresh_plex_library(self.tv_library_key)

    def _process_one_show(self, show_dir: Path):
        nfo_path = show_dir / 'tvshow.nfo'
        needs_nfo = self._needs_nfo(nfo_path)
        missing_art = self._missing_art(show_dir, _TV_SHOW_ART_FILES)

        meta = None

        if needs_nfo or missing_art:
            logger.info(f"Processing show: {show_dir.name}")
            meta = self._find_show_metadata(show_dir.name)
            if not meta:
                logger.warning(f"  ❌ Could not find metadata for: {show_dir.name}")
                return

            if needs_nfo:
                try:
                    nfo_path.write_text(self.nfo.generate_show_nfo(meta), encoding='utf-8')
                    logger.info(f"  ✓ Wrote tvshow.nfo")
                except IOError as e:
                    logger.error(f"  Failed to write tvshow.nfo: {e}")

            # Download artwork — try embedded extraction from first episode before API
            if 'poster.jpg' in missing_art:
                first_ep = None
                for sd in sorted(show_dir.iterdir()):
                    if sd.is_dir() and self._extract_season_number(sd.name) is not None:
                        first_ep = self._first_video_in_dir(sd)
                        if first_ep:
                            break
                if first_ep and self._extract_embedded_artwork(first_ep, show_dir / 'poster.jpg'):
                    logger.info(f"  ✓ Extracted show poster.jpg from embedded artwork ({first_ep.name})")
                elif meta.poster_url:
                    self.dl.download_image(meta.poster_url, show_dir / 'poster.jpg')
            if 'banner.jpg' in missing_art and meta.banner_url:
                self.dl.download_image(meta.banner_url, show_dir / 'banner.jpg')
            if 'fanart.jpg' in missing_art and meta.fanart_url:
                self.dl.download_image(meta.fanart_url, show_dir / 'fanart.jpg')

            # FanArt.tv artwork for show
            fanart_need = missing_art & {'clearart.png', 'logo.png', 'landscape.jpg'}
            if fanart_need and self.fanart and meta.tvdb_id:
                fa = self.fanart.get_tv_artwork(meta.tvdb_id)
                for fname, key in [('clearart.png', 'clearart_url'),
                                    ('logo.png', 'logo_url'),
                                    ('landscape.jpg', 'landscape_url')]:
                    if fname in fanart_need and fa.get(key):
                        self.dl.download_image(fa[key], show_dir / fname)
        else:
            logger.debug(f"⏭ {show_dir.name} — show level complete")

        # Resolve show IMDb ID for subtitle lookups (from metadata or existing NFO)
        show_imdb_id: Optional[str] = None
        if meta and meta.imdb_id:
            show_imdb_id = meta.imdb_id
        elif nfo_path.exists():
            show_imdb_id = self._extract_imdb_id_from_nfo(nfo_path)

        # Always scan seasons/episodes (they may have missing items even if show root is done)
        self._process_seasons(show_dir, meta, show_imdb_id)

    def _find_show_metadata(self, show_name: str) -> Optional[ShowMetadata]:
        # Extract IDs embedded in folder name, e.g. "Friends {tmdb-1668}" or "Friends {tvdb-79168}"
        tmdb_id_match = re.search(r'\{tmdb-(\d+)\}', show_name, re.IGNORECASE)
        tvdb_id_match = re.search(r'\{tvdb-(\d+)\}', show_name, re.IGNORECASE)
        # Strip all {…} tags to get a clean search title
        clean_name = re.sub(r'\s*\{[^}]+\}\s*', ' ', show_name).strip()

        # Direct TVDB lookup by ID when present
        if tvdb_id_match and self.tvdb:
            result = self.tvdb.get_show(int(tvdb_id_match.group(1)))
            if result:
                return result

        # Direct TMDB lookup by ID when present
        if tmdb_id_match and self.tmdb_tv:
            result = self.tmdb_tv.get_show(int(tmdb_id_match.group(1)))
            if result:
                return result

        # TVDb search with clean name
        if self.tvdb:
            results = self.tvdb.search_show(clean_name)
            if results:
                tvdb_id = results[0].get('tvdb_id')
                if tvdb_id:
                    return self.tvdb.get_show(tvdb_id)
        # TMDb fallback with clean name
        if self.tmdb_tv:
            results = self.tmdb_tv.search_show(clean_name)
            if results:
                return self.tmdb_tv.get_show(results[0]['id'])
        # Tunarr fallback
        td = self.tunarr.get_show_from_tunarr(show_name)
        if td:
            return ShowMetadata(
                title=show_name,
                year=0,
                plot=td.get('summary', ''),
                rating=float(td.get('rating', 0) or 0),
                runtime=int(td.get('duration', 45) or 45),
            )
        return None

    def _process_seasons(self, show_dir: Path, show_meta: Optional[ShowMetadata],
                         show_imdb_id: Optional[str] = None):
        for season_dir in sorted(show_dir.iterdir()):
            if not season_dir.is_dir():
                continue
            season_num = self._extract_season_number(season_dir.name)
            if season_num is None:
                continue

            # Season NFO and poster
            season_nfo = season_dir / 'season.nfo'
            season_poster = season_dir / 'poster.jpg'
            needs_season_nfo = self._needs_nfo(season_nfo)
            needs_season_poster = not season_poster.exists() or self.force

            if needs_season_nfo:
                # Minimal season.nfo
                root = ET.Element('season')
                ET.SubElement(root, 'seasonnumber').text = str(season_num)
                if show_meta:
                    ET.SubElement(root, 'title').text = f"{show_meta.title} — Season {season_num}"
                content = PlexNFOGenerator._pretty(root)
                try:
                    season_nfo.write_text(content, encoding='utf-8')
                    logger.debug(f"  ✓ Wrote season.nfo for S{season_num:02d}")
                except IOError:
                    pass

            # Season poster — prefer embedded artwork from first episode of the season
            if needs_season_poster:
                first_ep = self._first_video_in_dir(season_dir)
                if first_ep and self._extract_embedded_artwork(first_ep, season_dir / 'poster.jpg'):
                    logger.info(f"  ✓ Extracted S{season_num:02d} poster.jpg from embedded artwork ({first_ep.name})")
                elif show_meta and show_meta.tvdb_id and self.tvdb:
                    self._download_season_poster(season_dir, show_meta.tvdb_id, season_num)

            # Process episodes
            self._process_episodes(season_dir, show_meta, season_num, show_imdb_id)

    def _download_season_poster(self, season_dir: Path, tvdb_id: int, season_num: int):
        try:
            resp = requests.get(
                f'https://api4.thetvdb.com/v4/series/{tvdb_id}/artworks',
                headers=self.tvdb._headers(),
                params={'type': 7},  # type 7 = season poster
                timeout=10
            )
            resp.raise_for_status()
            for artwork in resp.json().get('data', []):
                if not isinstance(artwork, dict):
                    continue
                if artwork.get('season') == season_num:
                    img = artwork['image']
                    url = img if img.startswith('http') else f"https://artworks.thetvdb.com{img}"
                    self.dl.download_image(url, season_dir / 'poster.jpg')
                    return
        except requests.RequestException:
            pass

    def _process_episodes(self, season_dir: Path, show_meta: Optional[ShowMetadata],
                          season_num: int, show_imdb_id: Optional[str] = None):
        video_exts = {'.mkv', '.mp4', '.avi', '.m4v', '.mov'}
        video_files = sorted(f for f in season_dir.iterdir()
                             if f.is_file() and f.suffix.lower() in video_exts)
        if not video_files:
            return

        # Fetch episode metadata if any episode is missing NFO or thumb
        episodes_by_num: Dict[int, EpisodeMetadata] = {}
        needs_any = any(
            self._needs_nfo(vf.with_suffix('.nfo')) or
            not (season_dir / f"{vf.stem}-thumb.jpg").exists()
            for vf in video_files
        )
        if needs_any and show_meta:
            ep_list = []
            if show_meta.tvdb_id and self.tvdb:
                ep_list = self.tvdb.get_episodes(show_meta.tvdb_id, season_num)
            elif show_meta.tmdb_id and self.tmdb_tv:
                ep_list = self.tmdb_tv.get_episodes(show_meta.tmdb_id, season_num)
            episodes_by_num = {ep.episode: ep for ep in ep_list}

        for vf in video_files:
            nfo_path = vf.with_suffix('.nfo')
            thumb_path = season_dir / f"{vf.stem}-thumb.jpg"
            needs_nfo = self._needs_nfo(nfo_path)
            needs_thumb = not thumb_path.exists() or self.force

            if not needs_nfo and not needs_thumb:
                continue

            # Try to match episode number from filename
            ep_match = re.search(r'[Ss]\d+[Ee](\d+)', vf.name)
            ep_num = int(ep_match.group(1)) if ep_match else None
            ep_meta = episodes_by_num.get(ep_num) if ep_num else None

            if needs_nfo and ep_meta:
                try:
                    nfo_path.write_text(self.nfo.generate_episode_nfo(ep_meta), encoding='utf-8')
                    logger.debug(f"  ✓ {vf.name} → NFO")
                except IOError:
                    pass

            if needs_thumb and ep_meta and ep_meta.thumb_url:
                self.dl.download_image(ep_meta.thumb_url, thumb_path)

            # Download subtitles for this episode
            if self.subtitle_dl and show_imdb_id and ep_num is not None:
                self.subtitle_dl.process_episode(vf, show_imdb_id, season_num, ep_num)

    @staticmethod
    def _extract_season_number(folder_name: str) -> Optional[int]:
        m = re.search(r'[Ss]eason\s*(\d+)|[Ss](\d{2})', folder_name)
        if m:
            return int(m.group(1) or m.group(2))
        return None

    @staticmethod
    def _extract_embedded_artwork(source_path: Path, dest_path: Path) -> bool:
        """Extract embedded cover art from a media file using ffmpeg (3-strategy cascade).
        Returns True if an image was successfully extracted to dest_path."""
        import subprocess as _sp
        src = str(source_path)
        dst = str(dest_path)

        # Strategy 1: secondary video stream (Subler/iTunes MP4: stream 0=video, 1=cover art)
        try:
            r = _sp.run(['ffmpeg', '-i', src, '-an', '-vframes', '1', '-map', '0:v:1', '-y', dst],
                        capture_output=True, timeout=30)
            if r.returncode == 0 and dest_path.exists() and dest_path.stat().st_size > 1000:
                return True
            dest_path.unlink(missing_ok=True)
        except Exception:
            pass

        # Strategy 2: attached_pic stream (MKV, some MP4, most audio files)
        try:
            r = _sp.run(['ffmpeg', '-i', src, '-map', '0:v', '-map', '-0:V', '-vframes', '1', '-y', dst],
                        capture_output=True, timeout=30)
            if r.returncode == 0 and dest_path.exists() and dest_path.stat().st_size > 1000:
                return True
            dest_path.unlink(missing_ok=True)
        except Exception:
            pass

        # Strategy 3: explicit vsync fallback
        try:
            r = _sp.run(['ffmpeg', '-i', src, '-an', '-vsync', '2', '-y', dst],
                        capture_output=True, timeout=30)
            if r.returncode == 0 and dest_path.exists() and dest_path.stat().st_size > 1000:
                return True
            dest_path.unlink(missing_ok=True)
        except Exception:
            pass

        return False

    @staticmethod
    def _first_video_in_dir(directory: Path) -> Optional[Path]:
        """Return the first video file found in a directory (sorted), or None."""
        video_exts = {'.mp4', '.m4v', '.mkv', '.avi', '.mov'}
        for f in sorted(directory.iterdir()):
            if f.is_file() and f.suffix.lower() in video_exts:
                return f
        return None

    # ------------------------------------------------------------------
    # Plex refresh
    # ------------------------------------------------------------------

    def refresh_plex_library(self, library_key: str = '') -> bool:
        key = library_key or self.tv_library_key
        if not self.plex_token or not key:
            logger.warning("Plex token or library key not configured — skipping refresh")
            return False
        try:
            resp = requests.post(
                f'{self.plex_url}/library/sections/{key}/refresh',
                headers={'X-Plex-Token': self.plex_token},
                timeout=30
            )
            if resp.status_code == 200:
                logger.info(f"Plex library {key} refresh triggered")
                return True
            logger.warning(f"Plex refresh returned status {resp.status_code}")
            return False
        except requests.RequestException as e:
            logger.error(f"Failed to trigger Plex refresh: {e}")
            return False

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, media_type: str = 'tv', specific_item: str = None):
        """
        Run metadata generation.
        media_type: 'tv' | 'movies' | 'all'
        """
        try:
            self.tunarr.connect()  # OK if it fails — just a fallback source

            if media_type in ('tv', 'all'):
                self.process_tv_library(specific_show=specific_item)

            if media_type in ('movies', 'all'):
                self.process_movie_library(specific_movie=specific_item)

            logger.info("Metadata generation complete")
        except Exception as e:
            logger.error(f"Fatal error during metadata generation: {e}", exc_info=True)
            raise
        finally:
            self.tunarr.disconnect()


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def _default_config_path() -> str:
    """Return a writable per-user default config path (no root required)."""
    import platform
    system = platform.system()
    if system == 'Darwin':
        base = Path.home() / 'Library' / 'Application Support' / 'PlexMetadataGenerator'
    elif system == 'Windows':
        base = Path(os.environ.get('APPDATA', Path.home())) / 'PlexMetadataGenerator'
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'plex-metadata-generator'
    base.mkdir(parents=True, exist_ok=True)
    return str(base / 'plex-metadata-generator.conf')


def _default_cache_dir() -> str:
    """Return a writable per-user cache directory (no root required)."""
    import platform
    system = platform.system()
    if system == 'Darwin':
        base = Path.home() / 'Library' / 'Caches' / 'PlexMetadataGenerator'
    elif system == 'Windows':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'PlexMetadataGenerator' / 'Cache'
    else:
        base = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'plex-metadata-generator'
    base.mkdir(parents=True, exist_ok=True)
    return str(base)


def load_config(config_file: str) -> Dict:
    if not os.path.exists(config_file):
        logger.info(f"Config not found at {config_file} — a blank config will be created during setup")
        return {}
    try:
        with open(config_file) as f:
            # Strip // comments (not valid JSON but common in conf files)
            # Use negative lookbehind to avoid stripping URLs (http://, https://)
            text = re.sub(r'(?<!:)//[^\n]*', '', f.read())
            return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file {config_file}: {e}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Plex Metadata NFO Generator — TV shows and Movies'
    )
    parser.add_argument('--config', default=_default_config_path(),
                        help='Configuration file path (default: OS-appropriate user config directory)')
    parser.add_argument('--media-type', choices=['tv', 'movies', 'all'], default='tv',
                        help='Which library to process (default: tv)')
    parser.add_argument('--show', help='Process only this TV show folder name')
    parser.add_argument('--movie', help='Process only this movie folder name')
    parser.add_argument('--force', action='store_true',
                        help='Overwrite existing NFO files and artwork')
    parser.add_argument('--no-prompts', action='store_true',
                        help='Skip API key dialogs (for unattended/scheduled runs)')
    parser.add_argument('--workers', type=int, default=1, metavar='N',
                        help='Parallel workers for movie/TV processing (default: 1; '
                             'use 4 for initial bulk runs)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    config = load_config(args.config)
    cache_dir = config.get('cache_dir') or _default_cache_dir()

    if not args.no_prompts:
        config = prompt_missing_library_paths(config, args.config)
        config = prompt_missing_api_keys(config, args.config)
        if not args.force:
            args.force = prompt_force_flag()

    # 15-day scheduled revalidation — runs in both interactive and --no-prompts modes.
    # Shows blocking dialogs if a key has expired, regardless of --no-prompts.
    config = revalidate_all_keys(config, args.config, cache_dir)

    orchestrator = PlexMetadataOrchestrator(config, force=args.force, workers=args.workers)

    specific = args.show or args.movie
    orchestrator.run(media_type=args.media_type, specific_item=specific)
