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
import json
import preflight

# ─── Cross-platform UTF-8 output ──────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VIDEO_EXTS = {'.mkv', '.mp4', '.mov', '.avi', '.m4v'}


# ─── ffmpeg checks and install are handled by preflight.check_ffmpeg() ────────


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

def process_movies(root_dir, extract, force,
                   progress_cb=None, log_cb=None, cancel=None):
    folders = sorted([
        e for e in os.listdir(root_dir)
        if os.path.isdir(os.path.join(root_dir, e)) and not e.startswith('.')
    ])
    total = len(folders)

    def _log(msg, level="info"):
        if log_cb:
            log_cb(msg, level)
        else:
            print(msg, flush=True)

    mode_label = "EXTRACTING ARTWORK" if extract else "DRY RUN — No files will be written"
    _log(f"\n{mode_label}")
    _log("=" * 60)
    _log(f"Found {total} movie folders\n")

    n_extracted = n_exists = n_multipart = n_no_art = n_no_video = 0

    for idx, folder_name in enumerate(folders, 1):
        if cancel and cancel():
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

        video_path = find_video(folder_path)
        if not video_path:
            _log(f"{prefix} ⚠ no video file found", "warning")
            n_no_video += 1
            if progress_cb:
                progress_cb(idx, total, folder_name, "skipped",
                            n_extracted, n_no_art, n_exists + n_multipart + n_no_video)
            continue

        if not extract:
            probe = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_streams',
                 '-select_streams', 'v', '-of', 'json', video_path],
                capture_output=True, timeout=15
            )
            has_art = False
            if probe.returncode == 0:
                try:
                    streams = json.loads(probe.stdout).get('streams', [])
                    has_art = len(streams) > 1 or any(
                        s.get('disposition', {}).get('attached_pic') == 1 for s in streams
                    )
                except Exception:
                    pass
            if has_art:
                _log(f"{prefix}  WOULD EXTRACT → poster.jpg")
                n_extracted += 1
            else:
                _log(f"{prefix}  no embedded artwork — would skip", "warning")
                n_no_art += 1
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
        _log("DRY RUN COMPLETE")
        _log(f"  Would extract:  {n_extracted} posters")
        _log(f"  Already exist:  {n_exists} posters")
        _log(f"  Multi-part:     {n_multipart} skipped")
        _log(f"  No artwork:     {n_no_art} skipped")
        _log(f"  No video file:  {n_no_video} skipped")
        _log(f"  Total folders:  {total}")
        _log(f'\nTo apply: python3 extract_artwork.py movies "{root_dir}" --extract')
    else:
        _log("COMPLETE")
        _log(f"  Extracted:    {n_extracted} poster.jpg files")
        _log(f"  Already had:  {n_exists}")
        _log(f"  Multi-part:   {n_multipart} skipped")
        _log(f"  No artwork:   {n_no_art} skipped")
        _log(f"  No video:     {n_no_video} skipped")

    return n_extracted, n_no_art, n_exists + n_multipart + n_no_video


# ─── TV Shows ─────────────────────────────────────────────────────────────────

def process_tvshows(root_dir, extract, force,
                    progress_cb=None, log_cb=None, cancel=None):
    shows = sorted([
        e for e in os.listdir(root_dir)
        if os.path.isdir(os.path.join(root_dir, e)) and not e.startswith('.')
    ])
    total = len(shows)

    def _log(msg, level="info"):
        if log_cb:
            log_cb(msg, level)
        else:
            print(msg, flush=True)

    mode_label = "EXTRACTING ARTWORK" if extract else "DRY RUN — No files will be written"
    _log(f"\n{mode_label}")
    _log("=" * 60)
    _log(f"Found {total} TV show folders\n")

    n_show_posters = n_season_posters = n_ep_thumbs = 0
    n_exists = n_no_art = 0

    for idx, show_name in enumerate(shows, 1):
        if cancel and cancel():
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
                ep = find_first_episode(os.path.join(show_path, sd))
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
            progress_cb(idx, total, show_name, "done",
                        n_done, n_no_art, n_exists)

    _log("=" * 60)
    if not extract:
        _log("DRY RUN COMPLETE")
        _log(f"  Show posters:    {n_show_posters}")
        _log(f"  Season posters:  {n_season_posters}")
        _log(f"  Episode thumbs:  {n_ep_thumbs}")
        _log(f"  Already exist:   {n_exists}")
        _log(f"  No artwork:      {n_no_art}")
        _log(f'\nTo apply: python3 extract_artwork.py tvshows "{root_dir}" --extract')
    else:
        _log("COMPLETE")
        _log(f"  Show posters extracted:   {n_show_posters}")
        _log(f"  Season posters extracted: {n_season_posters}")
        _log(f"  Episode thumbs extracted: {n_ep_thumbs}")
        _log(f"  Already existed:          {n_exists}")
        _log(f"  No embedded artwork:      {n_no_art}")

    n_done = n_show_posters + n_season_posters + n_ep_thumbs
    return n_done, n_no_art, n_exists


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    extract = '--extract' in args
    force = '--force' in args
    args = [a for a in args if not a.startswith('--')]

    if len(args) < 2:
        print("Usage: python3 extract_artwork.py <movies|tvshows> <path> [--extract] [--force]")
        sys.exit(1)

    mode, path = args[0], args[1]

    if mode not in ('movies', 'tvshows'):
        print(f"Unknown mode '{mode}'. Use 'movies' or 'tvshows'.")
        sys.exit(1)

    if not os.path.isdir(path):
        print(f"Error: '{path}' is not a directory")
        sys.exit(1)

    label = "Movies" if mode == "movies" else "TV Shows"
    logger, log_file = preflight.setup_logging("extract_artwork")
    logger.info(f"Mode: {mode}  Path: {path}  Extract: {extract}  Force: {force}")

    if not preflight.check_python_version(logger=logger):
        sys.exit(1)
    if not preflight.check_ffmpeg(logger=logger):
        sys.exit(1)
    if extract and not preflight.check_write_permission(path, logger=logger):
        sys.exit(1)

    total = sum(
        1 for e in os.listdir(path)
        if os.path.isdir(os.path.join(path, e)) and not e.startswith('.')
    )

    win = preflight.ProgressWindow(
        title=f"Plex Artwork Extractor — {label}",
        total=total,
        log_file=log_file,
    )

    def work(progress_cb, log_cb, cancel):
        if mode == 'movies':
            done, errors, skipped = process_movies(
                path, extract, force,
                progress_cb=progress_cb, log_cb=log_cb, cancel=cancel,
            )
        else:
            done, errors, skipped = process_tvshows(
                path, extract, force,
                progress_cb=progress_cb, log_cb=log_cb, cancel=cancel,
            )
        logger.info(f"Finished — done={done} errors={errors} skipped={skipped}")
        action = "Extracted" if extract else "Would extract"
        preflight.notify(
            "Plex Artwork Extractor — Complete",
            f"{label}: {action} {done}, {errors} errors, {skipped} skipped.",
        )
        return done, errors, skipped

    win.run(work)


if __name__ == '__main__':
    main()
