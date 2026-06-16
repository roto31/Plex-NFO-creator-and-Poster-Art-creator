#!/usr/bin/env python3
"""
Movie Folder & File Renamer
Strips leading numbers, quality tags, and junk from movie folder names and video filenames.

Usage:
    python3 rename_movies.py "/Volumes/iTunes 5/Movies"           # dry run (preview only)
    python3 rename_movies.py "/Volumes/iTunes 5/Movies" --rename  # actually rename

Always run dry run first to verify before committing changes.
"""

import os
import re
import sys
from pathlib import Path

# Video and metadata file extensions to rename alongside the folder
RENAME_EXTENSIONS = {'.mkv', '.mp4', '.mov', '.avi', '.m4v', '.nfo', '.jpg', '.png', '.srt', '.sub'}

def clean_name(name):
    """
    Strip junk from a folder or file name, preserving the year in parentheses.
    """
    original = name

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
    result = working + ext if has_ext else working

    return result


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
    """Return True if the name actually changed."""
    return original != cleaned


def rename_item(old_path, new_path, dry_run=True):
    """Rename a file or folder."""
    if dry_run:
        print(f"  WOULD RENAME: {os.path.basename(old_path)}")
        print(f"             → {os.path.basename(new_path)}")
    else:
        try:
            os.rename(old_path, new_path)
            print(f"  RENAMED: {os.path.basename(old_path)}")
            print(f"       → {os.path.basename(new_path)}")
        except Exception as e:
            print(f"  ERROR renaming {old_path}: {e}")


def process_movies(movies_dir, dry_run=True):
    """Process all movie folders and their contents."""
    movies_dir = Path(movies_dir)
    
    if not movies_dir.exists():
        print(f"Error: Directory not found: {movies_dir}")
        sys.exit(1)

    folders = sorted([
        f for f in movies_dir.iterdir()
        if f.is_dir() and not f.name.startswith('.')
    ])

    total = len(folders)
    renamed_folders = 0
    renamed_files = 0
    unchanged = 0

    print(f"\n{'DRY RUN — No changes will be made' if dry_run else 'RENAMING FILES'}")
    print(f"{'=' * 60}")
    print(f"Found {total} movie folders in {movies_dir}\n")

    for folder in folders:
        folder_name = folder.name

        if is_multipart(folder_name):
            unchanged += 1
            continue

        clean_folder_name = clean_name(folder_name)

        folder_changed = should_rename(folder_name, clean_folder_name)

        # Determine new folder path
        new_folder_path = folder.parent / clean_folder_name

        # Process files inside folder first (before renaming folder)
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

        # Print header for this folder if anything changes
        if folder_changed or file_changes:
            print(f"[FOLDER] {folder_name}")

            # Rename files first (while folder name is still original)
            for old_file, new_file in file_changes:
                rename_item(old_file, new_file, dry_run=dry_run)
                renamed_files += 1

            # Then rename the folder itself
            if folder_changed:
                rename_item(folder, new_folder_path, dry_run=dry_run)
                renamed_folders += 1

            print()
        else:
            unchanged += 1

    print(f"{'=' * 60}")
    if dry_run:
        print(f"DRY RUN COMPLETE — Nothing was changed")
        print(f"  Folders that WOULD be renamed: {renamed_folders}")
        print(f"  Files that WOULD be renamed:   {renamed_files}")
        print(f"  Already clean (unchanged):     {unchanged}")
        print(f"\nTo apply these changes, run with --rename flag:")
        print(f"  python3 rename_movies.py \"{movies_dir}\" --rename")
    else:
        print(f"RENAME COMPLETE")
        print(f"  Folders renamed: {renamed_folders}")
        print(f"  Files renamed:   {renamed_files}")
        print(f"  Unchanged:       {unchanged}")
        print(f"\nNext step: Re-run the scraper to generate .nfo files for renamed folders:")
        print(f'  python3 "/Users/roto1231/XCode Projects/scraper.py" movies "/Volumes/iTunes 5/Movies"')


if __name__ == '__main__':
    args = sys.argv[1:]

    if not args:
        print("Usage:")
        print("  python3 rename_movies.py <directory>           # dry run")
        print("  python3 rename_movies.py <directory> --rename  # apply changes")
        sys.exit(1)

    movies_dir = args[0]
    dry_run = '--rename' not in args

    process_movies(movies_dir, dry_run=dry_run)