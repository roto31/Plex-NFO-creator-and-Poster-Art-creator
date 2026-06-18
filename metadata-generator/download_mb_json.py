#!/usr/bin/env python3
"""
Download and extract the MusicBrainz JSON dumps (artist + release-group).

Downloads from: https://data.metabrainz.org/pub/musicbrainz/data/json-dumps/
Extracts to:    ~/Library/Application Support/PlexMetadataGenerator/mb-json/  (macOS)
                ~/.local/share/plex-metadata-generator/mb-json/               (Linux)
                %APPDATA%/PlexMetadataGenerator/mb-json/                      (Windows)

Once extracted the metadata generator picks up the dump automatically —
no configuration needed. Re-run this script monthly to refresh the data.

Usage:
    python3 download_mb_json.py              # download + extract
    python3 download_mb_json.py --check      # show what would be downloaded
    python3 download_mb_json.py --dir /path  # override output directory
"""

import os
import sys
import tarfile
import hashlib
import argparse
import platform
import urllib.request
import urllib.error
from pathlib import Path
from html.parser import HTMLParser

# ── Constants ────────────────────────────────────────────────────────────────

BASE_URL   = 'https://data.metabrainz.org/pub/musicbrainz/data/json-dumps/'
# Only these two subdumps are needed for artist + album lookups
WANTED_DUMPS = ('mbdump-artist', 'mbdump-release-group')


# ── Default output directory ──────────────────────────────────────────────────

def _default_output_dir() -> Path:
    system = platform.system()
    if system == 'Darwin':
        base = Path.home() / 'Library' / 'Application Support' / 'PlexMetadataGenerator' / 'mb-json'
    elif system == 'Windows':
        base = Path(os.environ.get('APPDATA', Path.home())) / 'PlexMetadataGenerator' / 'mb-json'
    else:
        base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'plex-metadata-generator' / 'mb-json'
    return base


# ── Directory listing parser ──────────────────────────────────────────────────

class _LinkParser(HTMLParser):
    """Extract hrefs from a plain Apache/nginx directory listing."""
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for name, val in attrs:
                if name == 'href' and val and not val.startswith('?') and not val.startswith('/'):
                    self.links.append(val.rstrip('/'))


def _list_latest_dump() -> tuple[str, list[str]]:
    """Return (dump_date_dir_url, [tarball_filename, ...]) for the latest export."""
    print(f"Fetching dump index from {BASE_URL} …")
    with urllib.request.urlopen(BASE_URL, timeout=30) as r:
        html = r.read().decode()
    p = _LinkParser()
    p.parse(html)
    # Entries look like "20250601-001425/" — pick the last one
    date_dirs = sorted(l for l in p.links if l[:4].isdigit())
    if not date_dirs:
        raise RuntimeError("Could not find any dated dump directories at the index URL.")
    latest = date_dirs[-1]
    latest_url = BASE_URL + latest + '/'
    print(f"Latest dump: {latest}")

    print(f"Fetching file list from {latest_url} …")
    with urllib.request.urlopen(latest_url, timeout=30) as r:
        html = r.read().decode()
    p2 = _LinkParser()
    p2.parse(html)
    tarballs = [l for l in p2.links if l.endswith('.tar.bz2')
                and any(l.startswith(w) for w in WANTED_DUMPS)]
    return latest_url, tarballs


# ── Download helpers ──────────────────────────────────────────────────────────

def _human(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _download(url: str, dest: Path):
    """Download url → dest with a progress bar."""
    print(f"\nDownloading {dest.name}")
    print(f"  URL: {url}")

    tmp = dest.with_suffix('.tmp')
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            total = int(resp.headers.get('Content-Length', 0))
            downloaded = 0
            chunk = 1 << 20  # 1 MB
            with open(tmp, 'wb') as f:
                while True:
                    block = resp.read(chunk)
                    if not block:
                        break
                    f.write(block)
                    downloaded += len(block)
                    if total:
                        pct = downloaded / total * 100
                        bar = '#' * int(pct / 2)
                        print(f"\r  [{bar:<50}] {pct:5.1f}%  {_human(downloaded)}/{_human(total)}", end='', flush=True)
                    else:
                        print(f"\r  {_human(downloaded)} downloaded", end='', flush=True)
        print()
        tmp.replace(dest)
        print(f"  ✓ Saved to {dest}")
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


# ── Extract helpers ───────────────────────────────────────────────────────────

def _extract(tarball: Path, output_dir: Path):
    """Extract a MusicBrainz dump tarball into output_dir."""
    print(f"\nExtracting {tarball.name} …")
    output_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tarball, 'r:bz2') as tf:
        members = tf.getmembers()
        total = len(members)
        for i, member in enumerate(members, 1):
            # Strip leading 'mbdump/' prefix from paths inside the tarball
            member.name = member.name.replace('mbdump/', '', 1)
            if not member.name:
                continue
            tf.extract(member, path=output_dir)
            if i % 5000 == 0 or i == total:
                print(f"\r  Extracted {i:,}/{total:,} files", end='', flush=True)
    print(f"\n  ✓ Extracted to {output_dir}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true',
                        help='Show what would be downloaded without downloading')
    parser.add_argument('--dir', metavar='PATH', default=None,
                        help='Override output directory (default: OS-appropriate app data dir)')
    parser.add_argument('--keep-tarballs', action='store_true',
                        help='Keep the downloaded .tar.bz2 files after extraction')
    args = parser.parse_args()

    output_dir = Path(args.dir) if args.dir else _default_output_dir()

    try:
        latest_url, tarballs = _list_latest_dump()
    except Exception as e:
        print(f"ERROR: Could not fetch dump index: {e}", file=sys.stderr)
        sys.exit(1)

    if not tarballs:
        print("ERROR: No matching tarballs found (artist / release-group).", file=sys.stderr)
        sys.exit(1)

    print(f"\nFiles to download:")
    for t in tarballs:
        print(f"  {t}")
    print(f"\nOutput directory: {output_dir}")

    if args.check:
        print("\n(--check mode — nothing downloaded)")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = output_dir / '_download_tmp'
    tmp_dir.mkdir(exist_ok=True)

    try:
        for filename in tarballs:
            url = latest_url + filename
            tarball_path = tmp_dir / filename

            # Download
            try:
                _download(url, tarball_path)
            except Exception as e:
                print(f"ERROR downloading {filename}: {e}", file=sys.stderr)
                sys.exit(1)

            # Extract
            # Determine subdirectory name: mbdump-artist → artist, mbdump-release-group → release-group
            subdir_name = filename.replace('mbdump-', '').split('.')[0]
            subdir = output_dir / subdir_name

            # Remove old data before extracting fresh
            if subdir.exists():
                import shutil
                print(f"  Removing old {subdir_name}/ directory …")
                shutil.rmtree(subdir)

            try:
                _extract(tarball_path, output_dir)
            except Exception as e:
                print(f"ERROR extracting {filename}: {e}", file=sys.stderr)
                sys.exit(1)

            if not args.keep_tarballs:
                tarball_path.unlink(missing_ok=True)

    finally:
        # Clean up temp dir if empty
        try:
            tmp_dir.rmdir()
        except OSError:
            pass

    print(f"\n✓ MusicBrainz JSON dump ready at: {output_dir}")
    print("  The metadata generator will use it automatically on next run.")
    print("\n  Tip: Re-run this script monthly to keep the data current.")
    print(f"       MusicBrainz publishes new dumps weekly at:\n       {BASE_URL}")


if __name__ == '__main__':
    main()
