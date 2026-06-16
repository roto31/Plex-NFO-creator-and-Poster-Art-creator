#!/usr/bin/env python3
"""
Plex Artwork Extractor
Extracts embedded cover art from MP4/MKV files and saves as sidecar poster.jpg files.

Compatible with macOS, Linux, and Windows (Python 3.8+). Requires ffmpeg in PATH.

Usage (macOS / Linux):
    python3 extract_artwork.py movies "/path/to/Movies"            # dry run
    python3 extract_artwork.py movies "/path/to/Movies" --extract  # extract
    python3 extract_artwork.py tvshows "/path/to/TV Shows"         # dry run
    python3 extract_artwork.py tvshows "/path/to/TV Shows" --extract

Usage (Windows):
    python extract_artwork.py movies "D:\\Media\\Movies" --extract
    python extract_artwork.py tvshows "D:\\Media\\TV Shows" --extract

Add --force to re-extract even if poster.jpg already exists.
"""

import sys
import os
import re
import subprocess
import platform

# ─── Cross-platform UTF-8 output ──────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VIDEO_EXTS = {'.mkv', '.mp4', '.mov', '.avi', '.m4v'}


# ─── ffmpeg check ─────────────────────────────────────────────────────────────

def _ffmpeg_install_hint():
    """Return platform-appropriate ffmpeg install instructions."""
    system = platform.system()
    if system == "Darwin":
        return "  Install with: brew install ffmpeg"
    elif system == "Windows":
        return (
            "  Install from: https://ffmpeg.org/download.html#build-windows\n"
            "  Or via winget:      winget install ffmpeg\n"
            "  Or via Chocolatey:  choco install ffmpeg\n"
            "  After installing, ensure ffmpeg.exe is on your PATH."
        )
    else:  # Linux
        return (
            "  Debian / Ubuntu:  sudo apt install ffmpeg\n"
            "  Fedora / RHEL:    sudo dnf install ffmpeg\n"
            "  Arch:             sudo pacman -S ffmpeg"
        )


def check_ffmpeg():
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


# ─── Multi-part detection ─────────────────────────────────────────────────────

def is_multipart(name):
    patterns = [
        r'\bPart\s*\d+\b',
        r'-\s*part\s*\d+',
        r'\(\s*part\s*\d+\s*\)',
        r'\bDisc\s*\d+\b',
        r'\bDisk\s*\d+\b',
        r'\bD\d+\b',
        r'\b\d+\s*of\s*\d+\b',
        r'\bpt\s*\d+\b',
        r'\bVolume\s*\d+\b',
        r'\bVol\s*\.?\s*\d+\b',
        r'\bChapter\s*\d+\b',
    ]
    for pattern in patterns:
        if re.search(pattern, name, re.IGNORECASE):
            return True
    return False


# ─── Artwork extraction ───────────────────────────────────────────────────────

def extract_embedded_artwork(video_path, output_path):
    """
    Extract embedded cover art from a video file using ffmpeg.
    Tries multiple strategies. Returns True on success, False if no artwork found.
    Never falls back to extracting a video frame.
    """
    # Strategy 1: Secondary video stream (Subler/iTunes MP4 — stream 0=video, stream 1=cover art)
    try:
        result = subprocess.run(
            ['ffmpeg', '-i', video_path,
             '-an', '-vframes', '1',
             '-map', '0:v:1',
             '-y', output_path],
            capture_output=True, timeout=30
        )
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
        if os.path.exists(output_path):
            os.remove(output_path)
    except Exception:
        pass

    # Strategy 2: attached_pic stream (MKV, some MP4 formats)
    try:
        result = subprocess.run(
            ['ffmpeg', '-i', video_path,
             '-map', '0:v', '-map', '-0:V',
             '-vframes', '1',
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


def find_video(folder_path):
    """Return the first video file found in a folder, or None."""
    for f in sorted(os.listdir(folder_path)):
        if os.path.splitext(f)[1].lower() in VIDEO_EXTS:
            return os.path.join(folder_path, f)
    return None


def find_first_episode(season_path):
    """Return the first video file in a season folder (sorted), or None."""
    videos = sorted([
        f for f in os.listdir(season_path)
        if os.path.splitext(f)[1].lower() in VIDEO_EXTS
    ])
    return os.path.join(season_path, videos[0]) if videos else None


# ─── Movies ───────────────────────────────────────────────────────────────────

def process_movies(root_dir, extract, force):
    folders = sorted([
        e for e in os.listdir(root_dir)
        if os.path.isdir(os.path.join(root_dir, e)) and not e.startswith('.')
    ])
    total = len(folders)

    mode_label = "EXTRACTING ARTWORK" if extract else "DRY RUN — No files will be written"
    print(f"\n{mode_label}")
    print("=" * 60)
    print(f"Found {total} movie folders\n")

    n_extracted = n_exists = n_multipart = n_no_art = n_no_video = 0

    for idx, folder_name in enumerate(folders, 1):
        folder_path = os.path.join(root_dir, folder_name)
        prefix = f"[{idx}/{total}] {folder_name}"

        if is_multipart(folder_name):
            if not extract:
                print(f"{prefix}\n  ⏭ Skipping — multi-part file\n")
            else:
                print(f"{prefix} ⏭ multi-part")
            n_multipart += 1
            continue

        poster_path = os.path.join(folder_path, "poster.jpg")
        if os.path.exists(poster_path) and not force:
            if not extract:
                print(f"{prefix}\n  ⏭ poster.jpg already exists\n")
            else:
                print(f"{prefix} ⏭ already exists")
            n_exists += 1
            continue

        video_path = find_video(folder_path)
        if not video_path:
            n_no_video += 1
            continue

        video_name = os.path.basename(video_path)

        if not extract:
            # Dry run: probe whether artwork exists without writing anything
            probe = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_streams',
                 '-select_streams', 'v', '-of', 'json', video_path],
                capture_output=True, timeout=15
            )
            has_art = False
            if probe.returncode == 0:
                import json
                try:
                    streams = json.loads(probe.stdout).get('streams', [])
                    # artwork is a secondary video stream or one with attached_pic=1
                    has_art = len(streams) > 1 or any(
                        s.get('disposition', {}).get('attached_pic') == 1 for s in streams
                    )
                except Exception:
                    pass
            print(f"{prefix}")
            print(f"  Video: {video_name}")
            if has_art:
                print(f"  WOULD EXTRACT → poster.jpg\n")
                n_extracted += 1
            else:
                print(f"  WOULD EXTRACT → poster.jpg (no embedded artwork — would skip)\n")
                n_no_art += 1
        else:
            success = extract_embedded_artwork(video_path, poster_path)
            if success:
                print(f"{prefix} ✓ → poster.jpg")
                n_extracted += 1
            else:
                print(f"{prefix} ❌ no embedded artwork")
                n_no_art += 1

    print("\n" + "=" * 60)
    if not extract:
        print("DRY RUN COMPLETE")
        print(f"  Would extract:  {n_extracted} posters")
        print(f"  Already exist:  {n_exists} posters")
        print(f"  Multi-part:     {n_multipart} skipped")
        print(f"  No artwork:     {n_no_art} skipped")
        print(f"  No video file:  {n_no_video} skipped")
        print(f"  Total folders:  {total}")
        print(f'\nTo apply: python3 extract_artwork.py movies "{root_dir}" --extract')
    else:
        print("COMPLETE")
        print(f"  Extracted:    {n_extracted} poster.jpg files")
        print(f"  Already had:  {n_exists}")
        print(f"  Multi-part:   {n_multipart} skipped")
        print(f"  No artwork:   {n_no_art} skipped")
        print(f"  No video:     {n_no_video} skipped")


# ─── TV Shows ─────────────────────────────────────────────────────────────────

def process_tvshows(root_dir, extract, force):
    shows = sorted([
        e for e in os.listdir(root_dir)
        if os.path.isdir(os.path.join(root_dir, e)) and not e.startswith('.')
    ])
    total = len(shows)

    mode_label = "EXTRACTING ARTWORK" if extract else "DRY RUN — No files will be written"
    print(f"\n{mode_label}")
    print("=" * 60)
    print(f"Found {total} TV show folders\n")

    n_show_posters = n_season_posters = n_ep_thumbs = 0
    n_exists = n_no_art = 0

    for idx, show_name in enumerate(shows, 1):
        show_path = os.path.join(root_dir, show_name)
        prefix = f"[{idx}/{total}] {show_name}"
        print(prefix)

        # Find season dirs
        season_dirs = sorted([
            d for d in os.listdir(show_path)
            if os.path.isdir(os.path.join(show_path, d)) and not d.startswith('.')
            and re.match(r'[Ss]eason\s*\d+|[Ss]pecials?', d)
        ])

        # Show-level poster: from first episode of Season 1
        show_poster = os.path.join(show_path, "poster.jpg")
        if not os.path.exists(show_poster) or force:
            source = None
            for sd in season_dirs:
                ep = find_first_episode(os.path.join(show_path, sd))
                if ep:
                    source = ep
                    break
            if source:
                if not extract:
                    print(f"  WOULD EXTRACT → poster.jpg (from {os.path.basename(source)})")
                    n_show_posters += 1
                else:
                    if extract_embedded_artwork(source, show_poster):
                        print(f"  ✓ poster.jpg")
                        n_show_posters += 1
                    else:
                        print(f"  ❌ poster.jpg — no embedded artwork")
                        n_no_art += 1
            else:
                print(f"  ⏭ poster.jpg — no source episode found")
        else:
            print(f"  ⏭ poster.jpg already exists")
            n_exists += 1

        # Per-season processing
        for season_dir in season_dirs:
            season_path = os.path.join(show_path, season_dir)
            videos = sorted([
                f for f in os.listdir(season_path)
                if os.path.splitext(f)[1].lower() in VIDEO_EXTS
            ])
            if not videos:
                continue

            # Season poster from first episode
            season_poster = os.path.join(season_path, "poster.jpg")
            if not os.path.exists(season_poster) or force:
                source = os.path.join(season_path, videos[0])
                if not extract:
                    print(f"    {season_dir}: WOULD EXTRACT → poster.jpg")
                    n_season_posters += 1
                else:
                    if extract_embedded_artwork(source, season_poster):
                        print(f"    {season_dir} ✓ → poster.jpg")
                        n_season_posters += 1
                    else:
                        print(f"    {season_dir} ❌ poster.jpg — no embedded artwork")
                        n_no_art += 1
            else:
                n_exists += 1

            # Episode thumbnails
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

        print()

    print("=" * 60)
    if not extract:
        print("DRY RUN COMPLETE")
        print(f"  Show posters:    {n_show_posters}")
        print(f"  Season posters:  {n_season_posters}")
        print(f"  Episode thumbs:  {n_ep_thumbs}")
        print(f"  Already exist:   {n_exists}")
        print(f"  No artwork:      {n_no_art}")
        print(f'\nTo apply: python3 extract_artwork.py tvshows "{root_dir}" --extract')
    else:
        print("COMPLETE")
        print(f"  Show posters extracted:   {n_show_posters}")
        print(f"  Season posters extracted: {n_season_posters}")
        print(f"  Episode thumbs extracted: {n_ep_thumbs}")
        print(f"  Already existed:          {n_exists}")
        print(f"  No embedded artwork:      {n_no_art}")


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    if not check_ffmpeg():
        print("❌ ffmpeg not found. ffmpeg must be installed and available on your PATH.")
        print(_ffmpeg_install_hint())
        sys.exit(1)

    args = sys.argv[1:]
    extract = '--extract' in args
    force = '--force' in args
    args = [a for a in args if not a.startswith('--')]

    if len(args) < 2:
        print("Usage: python3 extract_artwork.py <movies|tvshows> <path> [--extract] [--force]")
        sys.exit(1)

    mode, path = args[0], args[1]

    if not os.path.isdir(path):
        print(f"Error: '{path}' is not a directory")
        sys.exit(1)

    if mode == 'movies':
        process_movies(path, extract, force)
    elif mode == 'tvshows':
        process_tvshows(path, extract, force)
    else:
        print(f"Unknown mode '{mode}'. Use 'movies' or 'tvshows'.")
        sys.exit(1)


if __name__ == '__main__':
    main()
