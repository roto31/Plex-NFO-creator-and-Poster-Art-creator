#!/usr/bin/env python3
"""
Plex NFO Metadata Scraper
Generates .nfo files for movies (TMDB) and TV shows (TVDB).
Uses 4 parallel workers and fuzzy title matching for better coverage.

Usage:
    python3 scraper.py movies "YOUR_MOVIES_VOLUME PATH"
    python3 scraper.py tvshows "YOUR_TV_SHOWS_PATH"
    python3 scraper.py movies "/path" --force
"""

import sys
import os
import re
import time
import json
import threading
import unicodedata
import urllib.request
import urllib.parse
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from xml.etree.ElementTree import Element, SubElement, tostring, parse as parse_xml
from xml.dom import minidom

# ─── Config ──────────────────────────────────────────────────────────────────

TMDB_API_KEY = "YOUR_TMDB_API_KEY"
TVDB_API_KEY = "YOUR_TVDB_APLI_KEY"

TMDB_BASE = "https://api.themoviedb.org/3"
TVDB_BASE = "https://api4.thetvdb.com/v4"

VIDEO_EXTS = {".mkv", ".mp4", ".mov", ".avi", ".m4v"}
RATE_SLEEP  = 0.28   # ~3.5 req/sec globally — comfortably under TMDB's 4 req/sec limit
RETRY_SLEEP = 10
TIMEOUT     = 15
MAX_WORKERS = 4

# ─── Thread-safe globals ──────────────────────────────────────────────────────

_TVDB_TOKEN      = None
_tvdb_login_lock = threading.Lock()

_rate_lock        = threading.Lock()
_last_request_ts  = 0.0

_print_lock = threading.Lock()

# ─── Rate limiter ─────────────────────────────────────────────────────────────

def _throttle():
    """Enforce global minimum interval between API request starts."""
    global _last_request_ts
    with _rate_lock:
        now  = time.time()
        wait = RATE_SLEEP - (now - _last_request_ts)
        if wait > 0:
            time.sleep(wait)
        _last_request_ts = time.time()

# ─── Thread-safe print ────────────────────────────────────────────────────────

def tprint(*args, **kwargs):
    with _print_lock:
        print(*args, **kwargs)

# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def _get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            tprint("    ⚠ Rate limited — sleeping 10s…", flush=True)
            time.sleep(RETRY_SLEEP)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        raise
    except Exception:
        time.sleep(2)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))


def tmdb_get(path, params=None):
    p = {"api_key": TMDB_API_KEY}
    if params:
        p.update(params)
    url = f"{TMDB_BASE}{path}?{urllib.parse.urlencode(p)}"
    _throttle()
    return _get(url)


def tvdb_login():
    global _TVDB_TOKEN
    with _tvdb_login_lock:
        if _TVDB_TOKEN:
            return _TVDB_TOKEN
        url     = f"{TVDB_BASE}/login"
        payload = json.dumps({"apikey": TVDB_API_KEY}).encode("utf-8")
        req     = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
            _TVDB_TOKEN = data["data"]["token"]
    return _TVDB_TOKEN


def tvdb_get(path, params=None):
    token = tvdb_login()
    p     = params or {}
    url   = f"{TVDB_BASE}{path}"
    if p:
        url += "?" + urllib.parse.urlencode(p)
    _throttle()
    return _get(url, headers={"Authorization": f"Bearer {token}"})

# ─── XML helpers ──────────────────────────────────────────────────────────────

def _el(parent, tag, text):
    e = SubElement(parent, tag)
    if text is not None:
        e.text = str(text)
    return e


def _uid(parent, id_type, value, default=False):
    uid = SubElement(parent, "uniqueid")
    uid.set("type", id_type)
    uid.set("default", "true" if default else "false")
    uid.text = str(value)


def pretty_xml(root):
    raw    = tostring(root, encoding="unicode")
    parsed = minidom.parseString(raw)
    lines  = parsed.toprettyxml(indent="  ", encoding=None).splitlines()
    lines[0] = "<?xml version='1.0' encoding='utf-8'?>"
    return "\n".join(lines)


def write_nfo(path, root):
    with open(path, "w", encoding="utf-8") as f:
        f.write(pretty_xml(root))

# ─── Name / path parsing ──────────────────────────────────────────────────────

def extract_year(name):
    m = re.search(r'\((\d{4})\)', name)
    return m.group(1) if m else None


def clean_title(name):
    stem, ext   = os.path.splitext(name)
    _known_exts = {'.mkv', '.mp4', '.mov', '.avi', '.m4v',
                   '.nfo', '.jpg', '.png', '.srt', '.sub'}
    has_ext = ext.lower() in _known_exts
    w = stem if has_ext else name

    # Strip 1-2 digit padding prefix only when followed by a letter
    w = re.sub(r'^\d{1,2}\s+(?=[A-Za-z])', '', w).strip()
    # Strip trailing (year)
    w = re.sub(r'\s*\(\d{4}\)\s*$', '', w).strip()
    # Strip quality/source/codec tags in brackets
    qtags = (
        r'HD|1080p|1080i|720p|2160p|4K|UHD|'
        r'Blu-?Ray|BluRay|BDRip|BRRip|'
        r'WEB-?DL|WEBRip|HDTV|DVDRip|DVD|'
        r'x264|x265|H\.?264|H\.?265|HEVC|AVC|'
        r'AAC|AC3|DTS|DD5\.1|'
        r'Unrated|Extended|Remastered|'
        r'4K83|4K77|4K80|YTS|YTS\.MX|YIFY|RARBG'
    )
    w = re.sub(rf'\s*[\(\[]({qtags})[\)\]]', '', w, flags=re.IGNORECASE).strip()
    # Strip remaining bracketed tags
    w = re.sub(r'\s*\[.*?\]\s*', '', w).strip()
    # Clean up trailing junk
    w = w.rstrip('_-. ').strip()
    w = w.replace('_', ' ').strip()
    w = re.sub(r'\s{2,}', ' ', w).strip()

    return w + ext if has_ext else w


def fuzzy_variants(title):
    """
    Return progressively-cleaned title variants for fuzzy search fallback.
    Tries in order until TMDB/TVDB returns a hit.
    """
    seen     = {title}
    variants = [title]

    def _add(v):
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
    # Also try ascii fold of the punctuation-stripped version
    _add(unicodedata.normalize('NFKD', re.sub(r"[',:\.\-]", ' ', title))
         .encode('ascii', 'ignore').decode('ascii'))

    return variants


def is_multipart(name):
    patterns = [
        r'\bPart\s*\d+\b', r'-\s*part\s*\d+', r'\(\s*part\s*\d+\s*\)',
        r'\bDisc\s*\d+\b', r'\bDisk\s*\d+\b', r'\bD\d+\b',
        r'\b\d+\s*of\s*\d+\b', r'\bpt\s*\d+\b',
        r'\bVolume\s*\d+\b', r'\bVol\s*\.?\s*\d+\b',
        r'\bEpisode\s*\d+\b', r'\bChapter\s*\d+\b',
    ]
    for p in patterns:
        if re.search(p, name, re.IGNORECASE):
            return True
    return False


def parse_season_episode(filename):
    m = re.search(r'[Ss](\d+)[Ee](\d+)', filename)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def has_video(folder):
    return any(
        os.path.splitext(f)[1].lower() in VIDEO_EXTS
        for f in os.listdir(folder)
    )

# ─── TMDB ────────────────────────────────────────────────────────────────────

def tmdb_search(title, year=None):
    """Search TMDB with fuzzy fallback. Returns movie_id or None."""
    for variant in fuzzy_variants(title):
        if year:
            data    = tmdb_get("/search/movie", {"query": variant, "year": year})
            results = data.get("results", [])
            if results:
                return results[0]["id"]
        data    = tmdb_get("/search/movie", {"query": variant})
        results = data.get("results", [])
        if results:
            return results[0]["id"]
    return None


def tmdb_details(movie_id):
    return tmdb_get(f"/movie/{movie_id}", {"append_to_response": "credits,external_ids"})


def build_movie_nfo(details):
    root = Element("movie")
    _el(root, "title", details.get("title"))

    if details.get("id"):
        _uid(root, "tmdb", details["id"], default=True)
    imdb_id = (details.get("external_ids") or {}).get("imdb_id")
    if imdb_id:
        _uid(root, "imdb", imdb_id)

    rd = details.get("release_date", "")
    _el(root, "year",    rd[:4] if rd else None)
    _el(root, "plot",    details.get("overview"))
    _el(root, "runtime", details.get("runtime"))
    _el(root, "rating",  details.get("vote_average"))

    for g in details.get("genres", []):
        _el(root, "genre", g["name"])

    companies = details.get("production_companies", [])
    if companies:
        _el(root, "studio", companies[0]["name"])

    for person in (details.get("credits") or {}).get("crew", []):
        if person.get("job") == "Director":
            _el(root, "director", person["name"])

    for person in (details.get("credits") or {}).get("cast", [])[:10]:
        actor = SubElement(root, "actor")
        _el(actor, "name", person["name"])
        _el(actor, "role", person.get("character"))

    return root

# ─── TVDB ────────────────────────────────────────────────────────────────────

def _tvdb_remote_ids(remote_ids):
    tmdb_id = imdb_id = None
    for rid in (remote_ids or []):
        src = rid.get("sourceName", "")
        val = rid.get("id", "")
        if "MovieDB" in src or rid.get("type") == 12:
            tmdb_id = val
        elif "IMDB" in src or rid.get("type") == 2:
            imdb_id = val
    return tmdb_id, imdb_id


def tvdb_search(title):
    """Search TVDB with fuzzy fallback. Returns series_id or None."""
    for variant in fuzzy_variants(title):
        data    = tvdb_get("/search", {"query": variant, "type": "series"})
        results = data.get("data", []) or []
        if results:
            return results[0]["tvdb_id"]
    return None


def tvdb_series_extended(series_id):
    data = tvdb_get(f"/series/{series_id}/extended", {"meta": "episodes", "short": "true"})
    return data.get("data", {})


def tvdb_episodes(series_id, season_num, page=0):
    data = tvdb_get(
        f"/series/{series_id}/episodes/default",
        {"season": season_num, "page": page}
    )
    return (data.get("data") or {}).get("episodes", []) or []


def build_tvshow_nfo(series):
    root = Element("tvshow")
    _el(root, "title", series.get("name"))

    if series.get("id"):
        _uid(root, "tvdb", series["id"], default=True)
    tmdb_id, imdb_id = _tvdb_remote_ids(series.get("remoteIds"))
    if tmdb_id:
        _uid(root, "tmdb", tmdb_id)
    if imdb_id:
        _uid(root, "imdb", imdb_id)

    fa = series.get("firstAired", "")
    _el(root, "year",    fa[:4] if fa else None)
    _el(root, "plot",    series.get("overview"))
    _el(root, "runtime", series.get("averageRuntime"))
    _el(root, "rating",  series.get("score"))

    for g in series.get("genres", []) or []:
        name = g.get("name") if isinstance(g, dict) else g
        if name:
            _el(root, "genre", name)

    networks = series.get("networks", []) or []
    if networks:
        _el(root, "network", networks[0].get("name"))

    for char in (series.get("characters", []) or []):
        if char.get("type") == 1 or char.get("peopleType") == "Actor":
            actor = SubElement(root, "actor")
            _el(actor, "name", char.get("personName") or char.get("name"))
            _el(actor, "role", char.get("name") if char.get("personName") else None)

    return root


def build_season_nfo(season_num):
    root = Element("season")
    _el(root, "title",  "Specials" if season_num == 0 else f"Season {season_num}")
    _el(root, "season", season_num)
    return root


def build_episode_nfo(ep, series_chars=None):
    root = Element("episodedetails")
    _el(root, "title",   ep.get("name"))
    _el(root, "season",  ep.get("seasonNumber"))
    _el(root, "episode", ep.get("number"))

    if ep.get("id"):
        _uid(root, "tvdb", ep["id"], default=True)
    _, imdb_ep_id = _tvdb_remote_ids(ep.get("remoteIds"))
    if imdb_ep_id:
        _uid(root, "imdb", imdb_ep_id)

    _el(root, "plot",    ep.get("overview"))
    _el(root, "rating",  ep.get("score") or ep.get("siteRating"))
    _el(root, "aired",   ep.get("aired"))
    _el(root, "runtime", ep.get("runtime"))

    for person in ep.get("directors", []) or []:
        name = person.get("name") if isinstance(person, dict) else person
        if name:
            _el(root, "director", name)

    chars = ep.get("characters", []) or series_chars or []
    for char in chars[:10]:
        if isinstance(char, dict):
            actor = SubElement(root, "actor")
            _el(actor, "name", char.get("personName") or char.get("name"))
            _el(actor, "role", char.get("name") if char.get("personName") else None)

    return root

# ─── Movie processing ─────────────────────────────────────────────────────────

def _process_one_movie(args):
    idx, total, folder_name, folder_path, force = args
    nfo_path = os.path.join(folder_path, "Movie.nfo")
    prefix   = f"[{idx}/{total}] {folder_name}"

    if is_multipart(folder_name):
        tprint(f"{prefix} ⏭ multi-part — skipped", flush=True)
        return "skipped"

    if os.path.exists(nfo_path) and not force:
        tprint(f"{prefix} ⏭ Already has NFO", flush=True)
        return "skipped"

    if not has_video(folder_path):
        return "skipped"

    title = clean_title(folder_name)
    year  = extract_year(folder_name)

    try:
        movie_id = tmdb_search(title, year)
        if not movie_id:
            tprint(f"{prefix} ❌ Not found", flush=True)
            return "error"

        details  = tmdb_details(movie_id)
        root_xml = build_movie_nfo(details)
        write_nfo(nfo_path, root_xml)
        tprint(f"{prefix} ✓ → Movie.nfo", flush=True)
        return "done"

    except Exception as exc:
        tprint(f"{prefix} ❌ Error: {exc}", flush=True)
        return "error"


def process_movies(root_dir, force):
    entries = sorted([
        e for e in os.listdir(root_dir)
        if os.path.isdir(os.path.join(root_dir, e)) and not e.startswith(".")
    ])
    total = len(entries)
    print(f"Processing {total} movies… ({MAX_WORKERS} parallel workers)\n", flush=True)

    tasks = [
        (idx, total, name, os.path.join(root_dir, name), force)
        for idx, name in enumerate(entries, 1)
    ]

    done = errors = skipped = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for status in ex.map(_process_one_movie, tasks):
            if status == "done":    done    += 1
            elif status == "error": errors  += 1
            else:                   skipped += 1

    print(f"\n✓ Completed: {done} movies ({errors} errors, {skipped} skipped)", flush=True)

# ─── TV Show processing ───────────────────────────────────────────────────────

def _read_tvdb_id_from_nfo(nfo_path):
    """Read TVDB series ID from <uniqueid type="tvdb"> in an existing tvshow.nfo."""
    try:
        tree = parse_xml(nfo_path)
        for uid in tree.getroot().findall("uniqueid"):
            if uid.get("type") == "tvdb" and uid.text:
                return int(uid.text)
    except Exception:
        pass
    # Legacy fallback: old-style tvdb_id= comment
    try:
        with open(nfo_path, encoding="utf-8") as f:
            for line in f:
                m = re.search(r'tvdb_id=(\d+)', line)
                if m:
                    return int(m.group(1))
    except Exception:
        pass
    return None


def _process_seasons(show_path, series_id, series_chars, force):
    season_dirs = sorted([
        d for d in os.listdir(show_path)
        if os.path.isdir(os.path.join(show_path, d)) and not d.startswith(".")
        and re.match(r'[Ss]eason\s*\d+|[Ss]pecials?', d)
    ])

    for season_dir in season_dirs:
        season_path = os.path.join(show_path, season_dir)

        if re.match(r'[Ss]pecials?', season_dir):
            season_num = 0
        else:
            m = re.search(r'\d+', season_dir)
            season_num = int(m.group()) if m else None
            if season_num is None:
                continue

        season_nfo = os.path.join(season_path, "season.nfo")
        if not os.path.exists(season_nfo) or force:
            try:
                write_nfo(season_nfo, build_season_nfo(season_num))
                tprint(f"    {season_dir} ✓ → season.nfo", flush=True)
            except Exception as exc:
                tprint(f"    {season_dir} ❌ season.nfo: {exc}", flush=True)

        try:
            ep_list = tvdb_episodes(series_id, season_num)
            ep_map  = {(e["seasonNumber"], e["number"]): e for e in ep_list}
        except Exception as exc:
            tprint(f"    {season_dir} ❌ Episode fetch failed: {exc}", flush=True)
            ep_map = {}

        video_files = sorted([
            f for f in os.listdir(season_path)
            if os.path.splitext(f)[1].lower() in VIDEO_EXTS
        ])

        for vfile in video_files:
            ep_nfo = os.path.join(season_path, os.path.splitext(vfile)[0] + ".nfo")
            if os.path.exists(ep_nfo) and not force:
                continue

            s, e = parse_season_episode(vfile)
            if s is None:
                continue

            ep_data = ep_map.get((s, e))
            if not ep_data:
                tprint(f"      {vfile} ❌ S{s:02d}E{e:02d} not found in TVDB", flush=True)
                continue

            try:
                write_nfo(ep_nfo, build_episode_nfo(ep_data, series_chars))
                tprint(f"      {vfile} ✓ → {os.path.basename(ep_nfo)}", flush=True)
            except Exception as exc:
                tprint(f"      {vfile} ❌ Write failed: {exc}", flush=True)


def _process_one_show(args):
    idx, total, show_name, show_path, force = args
    show_nfo = os.path.join(show_path, "tvshow.nfo")
    prefix   = f"[{idx}/{total}] {show_name}"

    if os.path.exists(show_nfo) and not force:
        tprint(f"{prefix} ⏭ Already has NFO", flush=True)
        series_id = _read_tvdb_id_from_nfo(show_nfo)
        if series_id:
            _process_seasons(show_path, series_id, None, force)
        return "skipped"

    title = clean_title(show_name)

    try:
        series_id = tvdb_search(title)
        if not series_id:
            tprint(f"{prefix} ❌ Not found", flush=True)
            return "error"

        series       = tvdb_series_extended(series_id)
        series_chars = series.get("characters", []) or []

        write_nfo(show_nfo, build_tvshow_nfo(series))
        tprint(f"{prefix} ✓ → tvshow.nfo", flush=True)

        _process_seasons(show_path, series_id, series_chars, force)
        return "done"

    except Exception as exc:
        tprint(f"{prefix} ❌ Error: {exc}", flush=True)
        return "error"


def process_tvshows(root_dir, force):
    shows = sorted([
        e for e in os.listdir(root_dir)
        if os.path.isdir(os.path.join(root_dir, e)) and not e.startswith(".")
    ])
    total = len(shows)
    print(f"Processing {total} TV shows… ({MAX_WORKERS} parallel workers)\n", flush=True)

    # Authenticate once before threads start
    try:
        tvdb_login()
    except Exception as e:
        print(f"❌ TVDB login failed: {e}")
        sys.exit(1)

    tasks = [
        (idx, total, name, os.path.join(root_dir, name), force)
        for idx, name in enumerate(shows, 1)
    ]

    done = errors = skipped = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for status in ex.map(_process_one_show, tasks):
            if status == "done":    done    += 1
            elif status == "error": errors  += 1
            else:                   skipped += 1

    print(f"\n✓ Completed: {done} shows ({errors} errors, {skipped} skipped)", flush=True)

# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    args  = sys.argv[1:]
    force = "--force" in args
    args  = [a for a in args if a != "--force"]

    if len(args) < 2:
        print("Usage: python3 scraper.py <movies|tvshows> <path> [--force]")
        sys.exit(1)

    mode, path = args[0], args[1]

    if not os.path.isdir(path):
        print(f"Error: '{path}' is not a directory")
        sys.exit(1)

    if mode == "movies":
        process_movies(path, force)
    elif mode == "tvshows":
        process_tvshows(path, force)
    else:
        print(f"Unknown mode '{mode}'. Use 'movies' or 'tvshows'.")
        sys.exit(1)


if __name__ == "__main__":
    main()
