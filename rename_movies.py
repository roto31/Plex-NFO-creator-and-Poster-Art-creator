#!/usr/bin/env python3
"""
Movie Folder & File Renamer
Strips leading numbers, quality tags, and junk from movie folder names and video filenames.

Compatible with macOS, Linux, and Windows (Python 3.8+).

Usage (macOS / Linux):
    python3 rename_movies.py "/path/to/Movies"           # dry run (preview only)
    python3 rename_movies.py "/path/to/Movies" --rename  # actually rename

Usage (Windows):
    python rename_movies.py "D:\\Media\\Movies"           # dry run
    python rename_movies.py "D:\\Media\\Movies" --rename  # apply

Always run dry run first to verify before committing changes.
"""

import os
import re
import sys
from pathlib import Path
import preflight

# ─── Cross-platform UTF-8 output ──────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Video and metadata file extensions to rename alongside the folder
RENAME_EXTENSIONS = {'.mkv', '.mp4', '.mov', '.avi', '.m4v', '.nfo', '.jpg', '.png', '.srt', '.sub'}

def clean_name(name):
    """
    Strip junk from a folder or file name, preserving the year in parentheses.
    """
    # Separate the file extension if present
    stem, ext = os.path.splitext(name)
    has_ext = ext.lower() in RENAME_EXTENSIONS
    working = stem if has_ext else name

    # Step 1: Strip leading 1-2 digit padding prefix followed by a letter
    # e.g. "01 The Hangover" → "The Hangover", "03 Forrest Gump" → "Forrest Gump"
    # Does NOT strip "127 Hours", "2001 A Space Odyssey", "50 50", etc.
    working = re.sub(r'^\d{1,2}\s+(?=[A-Za-z])', '', working).strip()

    # Step 2: Strip quality/source tags in parentheses or brackets
    # e.g. "(HD)", "[1080p]", "(4K)", "[BluRay]", "(Unrated)", etc.
    quality_tags = (
        r'HD|1080p|1080i|720p|2160p|4K|UHD|'
        r'Blu-?Ray|BluRay|BDRip|BRRip|'
        r'WEB-?DL|WEBRip|HDTV|DVDRip|DVD|'
        r'x264|x265|H\.?264|H\.?265|HEVC|AVC|'
        r'AAC|AC3|DTS|DD5\.1|'
        r'Unrated|Extended|Remastered|'
        r'4K83|4K77|4K80|'
        r'YTS|YTS\.MX|YIFY|RARBG'
    )
    working = re.sub(
        rf'\s*[\(\[]({quality_tags})[\)\]]',
        '', working, flags=re.IGNORECASE
    ).strip()

    # Step 3: Strip remaining bracketed content like [YTS.MX] [BluRay] [Despecialized]
    working = re.sub(r'\s*\[.*?\]\s*', '', working).strip()

    # Step 4: Strip trailing underscores, dashes, dots, spaces
    working = working.rstrip('_-. ').strip()

    # Step 5: Replace underscores with spaces (e.g. "The_Dark_Knight" → "The Dark Knight")
    working = working.replace('_', ' ').strip()

    # Step 6: Collapse multiple spaces
    working = re.sub(r'\s{2,}', ' ', working).strip()

    # Rebuild with extension if needed
    return working + ext if has_ext else working


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
        r'\bEpisode\s*\d+\b',
        r'\bChapter\s*\d+\b',
    ]
    for pattern in patterns:
        if re.search(pattern, name, re.IGNORECASE):
            return True
    return False


def should_rename(original, cleaned):
    return original != cleaned


def rename_item(old_path, new_path, dry_run=True, log_fn=None):
    def _out(msg):
        if log_fn:
            log_fn(msg)
        else:
            print(msg, flush=True)

    if dry_run:
        _out(f"  WOULD RENAME: {os.path.basename(old_path)}")
        _out(f"             → {os.path.basename(new_path)}")
    else:
        try:
            # os.replace is atomic and works on all platforms including Windows,
            # where os.rename raises FileExistsError if the destination exists.
            os.replace(old_path, new_path)
            _out(f"  RENAMED: {os.path.basename(old_path)}")
            _out(f"       → {os.path.basename(new_path)}")
        except Exception as e:
            _out(f"  ERROR renaming {old_path}: {e}")


def process_movies(movies_dir, dry_run=True,
                   progress_cb=None, log_cb=None, cancel=None):
    movies_dir = Path(movies_dir)

    if not movies_dir.exists():
        msg = f"Error: Directory not found: {movies_dir}"
        if log_cb:
            log_cb(msg, "error")
        else:
            print(msg)
        sys.exit(1)

    def _log(msg, level="info"):
        if log_cb:
            log_cb(msg, level)
        else:
            print(msg, flush=True)

    folders = sorted([
        f for f in movies_dir.iterdir()
        if f.is_dir() and not f.name.startswith('.')
    ])

    total = len(folders)
    renamed_folders = 0
    renamed_files = 0
    unchanged = 0

    _log(f"\n{'DRY RUN — No changes will be made' if dry_run else 'RENAMING FILES'}")
    _log("=" * 60)
    _log(f"Found {total} movie folders in {movies_dir}\n")

    for idx, folder in enumerate(folders, 1):
        if cancel and cancel():
            _log("Cancelled by user.", "warning")
            break

        folder_name = folder.name

        if is_multipart(folder_name):
            unchanged += 1
            if progress_cb:
                progress_cb(idx, total, folder_name, "skipped",
                            renamed_folders, 0, unchanged)
            continue

        clean_folder_name = clean_name(folder_name)
        folder_changed = should_rename(folder_name, clean_folder_name)
        new_folder_path = folder.parent / clean_folder_name

        files_in_folder = sorted([
            f for f in folder.iterdir()
            if f.is_file() and not f.name.startswith('.')
        ])

        file_changes = []
        for file in files_in_folder:
            file_name = file.name
            clean_file_name = clean_name(file_name)
            if should_rename(file_name, clean_file_name):
                file_changes.append((file, folder / clean_file_name))

        if folder_changed or file_changes:
            _log(f"[FOLDER] {folder_name}")

            for old_file, new_file in file_changes:
                rename_item(old_file, new_file, dry_run=dry_run, log_fn=lambda m: _log(m))
                renamed_files += 1

            if folder_changed:
                rename_item(folder, new_folder_path, dry_run=dry_run, log_fn=lambda m: _log(m))
                renamed_folders += 1

            _log("")
        else:
            unchanged += 1

        if progress_cb:
            progress_cb(idx, total, folder_name,
                        "done" if (folder_changed or file_changes) else "skipped",
                        renamed_folders, 0, unchanged)

    _log("=" * 60)
    if dry_run:
        _log("DRY RUN COMPLETE — Nothing was changed")
        _log(f"  Folders that WOULD be renamed: {renamed_folders}")
        _log(f"  Files that WOULD be renamed:   {renamed_files}")
        _log(f"  Already clean (unchanged):     {unchanged}")
        _log(f"\nTo apply these changes, run with --rename flag:")
        _log(f'  python3 rename_movies.py "{movies_dir}" --rename')
    else:
        _log("RENAME COMPLETE")
        _log(f"  Folders renamed: {renamed_folders}")
        _log(f"  Files renamed:   {renamed_files}")
        _log(f"  Unchanged:       {unchanged}")
        _log(f"\nNext step: Re-run the scraper to generate .nfo files for renamed folders:")
        _log(f'  python3 scraper.py movies "{movies_dir}"')

    return renamed_folders, 0, unchanged


if __name__ == '__main__':
    args = sys.argv[1:]

    if not args:
        print("Usage:")
        print("  python3 rename_movies.py <directory>           # dry run")
        print("  python3 rename_movies.py <directory> --rename  # apply changes")
        sys.exit(1)

    movies_dir = args[0]
    dry_run = '--rename' not in args

    logger, log_file = preflight.setup_logging("rename_movies")
    logger.info(f"Path: {movies_dir}  DryRun: {dry_run}")

    if not preflight.check_python_version(logger=logger):
        sys.exit(1)
    if not dry_run and not preflight.check_write_permission(movies_dir, logger=logger):
        sys.exit(1)

    total = sum(
        1 for e in os.listdir(movies_dir)
        if os.path.isdir(os.path.join(movies_dir, e)) and not e.startswith('.')
    ) if os.path.isdir(movies_dir) else 0

    label = "Rename Movies" if not dry_run else "Rename Movies (Dry Run)"
    win = preflight.ProgressWindow(
        title=f"Plex Movie Renamer — {label}",
        total=total,
        log_file=log_file,
    )

    def work(progress_cb, log_cb, cancel):
        done, errors, skipped = process_movies(
            movies_dir, dry_run,
            progress_cb=progress_cb, log_cb=log_cb, cancel=cancel,
        )
        logger.info(f"Finished — renamed={done} skipped={skipped}")
        action = "Would rename" if dry_run else "Renamed"
        preflight.notify(
            "Plex Movie Renamer — Complete",
            f"{action} {done} folders, {skipped} unchanged.",
        )
        return done, errors, skipped

    win.run(work)
