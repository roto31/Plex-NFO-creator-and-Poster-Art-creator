#!/usr/bin/env python3
"""
Plex Metadata NFO Generator with Multi-Media Support
Supports: TV Shows + Music (Albums, Artists, Tracks)
Integrates with: Tunarr, TVDb, TMDb, MusicBrainz, iTunes Search API, Apple MusicKit API
"""

import os
import re
import sys
import json
import logging
import requests
import sqlite3
import unicodedata
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from urllib.parse import quote
import xml.etree.ElementTree as ET
import time
import hashlib

# Configure logging
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


class MediaType(Enum):
    """Supported media types"""
    TV_SHOW = "tv_show"
    MOVIE = "movie"
    MUSIC_ALBUM = "music_album"
    MUSIC_ARTIST = "music_artist"
    MUSIC_TRACK = "music_track"


@dataclass
class ShowMetadata:
    """Container for TV show metadata"""
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
    """Container for episode metadata"""
    title: str
    season: int
    episode: int
    plot: str
    air_date: str
    rating: float
    guest_stars: List[str] = field(default_factory=list)
    director: Optional[str] = None
    writer: Optional[str] = None


@dataclass
class AlbumMetadata:
    """Container for music album metadata"""
    title: str
    artist: str
    year: int
    rating: float
    plot: str = ""
    genres: List[str] = field(default_factory=list)
    mbid: Optional[str] = None      # MusicBrainz ID
    apple_id: Optional[str] = None  # iTunes / Apple Music collection ID
    cover_url: Optional[str] = None
    release_date: Optional[str] = None
    track_count: int = 0
    label: Optional[str] = None


@dataclass
class ArtistMetadata:
    """Container for music artist metadata"""
    name: str
    mbid: Optional[str] = None
    apple_id: Optional[str] = None  # iTunes / Apple Music artist ID
    bio: str = ""
    genres: List[str] = field(default_factory=list)
    image_url: Optional[str] = None
    members: List[str] = field(default_factory=list)


@dataclass
class TrackMetadata:
    """Container for music track metadata"""
    title: str
    artist: str
    album: str
    track_number: int
    rating: float
    duration: int = 0  # seconds
    genre: Optional[str] = None
    mbid: Optional[str] = None
    isrc: Optional[str] = None  # International Standard Recording Code


class MusicBrainzProvider:
    """Fetch metadata from MusicBrainz API"""

    BASE_URL = 'https://musicbrainz.org/ws/2'
    # MusicBrainz policy: max 1 req/sec; back off on 503
    _MIN_INTERVAL = 1.1

    def __init__(self, user_agent: str = 'PlexMetadataGenerator/1.0'):
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
        self._last_request_time: float = 0.0

    def _get(self, url: str, params: dict, retries: int = 4) -> requests.Response:
        """Rate-limited GET with exponential backoff on 503."""
        import time
        for attempt in range(retries):
            elapsed = time.time() - self._last_request_time
            if elapsed < self._MIN_INTERVAL:
                time.sleep(self._MIN_INTERVAL - elapsed)
            self._last_request_time = time.time()
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 503:
                wait = 2 ** attempt
                logger.warning(f"MusicBrainz 503 — retrying in {wait}s (attempt {attempt+1}/{retries})")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        resp.raise_for_status()
        return resp

    def search_release(self, album_title: str, artist: str) -> List[Dict]:
        """Search for an album release"""
        try:
            query = f'release:"{album_title}" artist:"{artist}"'
            params = {
                'query': query,
                'fmt': 'json',
                'limit': 10
            }

            response = self._get(f'{self.BASE_URL}/release', params)

            results = response.json().get('releases', [])
            logger.debug(f"MusicBrainz search for '{album_title}' by '{artist}' returned {len(results)} results")
            return results
        except requests.RequestException as e:
            logger.error(f"MusicBrainz search failed: {e}")
            return []

    def get_release(self, mbid: str) -> Optional[AlbumMetadata]:
        """Fetch complete album metadata by MusicBrainz ID"""
        try:
            params = {
                'fmt': 'json',
                'inc': 'artists+labels+recordings'
            }

            response = self._get(f'{self.BASE_URL}/release/{mbid}', params)
            data = response.json()
            
            # Extract metadata
            title = data.get('title', '')
            
            # Get artist from release-group or artists
            artist_list = []
            if 'artist-credit' in data:
                for ac in data['artist-credit']:
                    if isinstance(ac, dict):
                        artist_list.append(ac.get('artist', {}).get('name', ''))
            
            artist = ', '.join(filter(None, artist_list)) or 'Unknown Artist'
            
            # Parse date
            date_str = data.get('date', '')
            year = int(date_str.split('-')[0]) if date_str else 0
            
            # Get label
            label = None
            if 'label-info' in data and data['label-info']:
                label = (data['label-info'][0].get('label') or {}).get('name')
            
            metadata = AlbumMetadata(
                title=title,
                artist=artist,
                year=year,
                rating=0.0,  # MusicBrainz doesn't have ratings
                mbid=mbid,
                release_date=date_str,
                track_count=len(data.get('media', [{}])[0].get('tracks', [])) if data.get('media') else 0,
                label=label
            )
            
            logger.info(f"Retrieved MusicBrainz metadata for '{title}' by '{artist}'")
            return metadata
        except requests.RequestException as e:
            logger.error(f"Failed to fetch MusicBrainz release {mbid}: {e}")
            return None
    
    def search_artist(self, artist_name: str) -> List[Dict]:
        """Search for an artist"""
        try:
            params = {
                'query': f'artist:"{artist_name}"',
                'fmt': 'json',
                'limit': 5
            }

            response = self._get(f'{self.BASE_URL}/artist', params)

            results = response.json().get('artists', [])
            logger.debug(f"MusicBrainz artist search for '{artist_name}' returned {len(results)} results")
            return results
        except requests.RequestException as e:
            logger.error(f"MusicBrainz artist search failed: {e}")
            return []


class LocalMusicBrainzProvider:
    """
    Query a locally-hosted MusicBrainz PostgreSQL database.

    Requires the mbdump imported into PostgreSQL.
    Download: https://data.metabrainz.org/pub/musicbrainz/data/fullexport/
    Schema:   https://musicbrainz.org/doc/MusicBrainz_Database/Schema

    Uses psycopg2 (pip install psycopg2-binary).  Falls back gracefully
    to the REST API provider if psycopg2 is not installed or the
    connection cannot be established.

    Key schema tables used:
      artist, release_group, release, recording,
      medium, track, artist_credit, artist_credit_name
    """

    def __init__(self, host: str, port: int, dbname: str, user: str, password: str,
                 schema: str = 'musicbrainz'):
        self.dsn = dict(host=host, port=port, dbname=dbname, user=user, password=password)
        self.schema = schema
        self._conn = None
        self._available = False

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Return True if connection succeeded; sets self._available."""
        try:
            import psycopg2  # noqa: PLC0415
            import psycopg2.extras  # noqa: PLC0415
            self._psycopg2 = psycopg2
            self._conn = psycopg2.connect(**self.dsn)
            self._conn.autocommit = True
            self._available = True
            logger.info(f"Connected to local MusicBrainz DB at {self.dsn['host']}:{self.dsn['port']}/{self.dsn['dbname']}")
            return True
        except ImportError:
            logger.warning("psycopg2 not installed — local MusicBrainz DB unavailable. "
                           "Install with: pip install psycopg2-binary")
            return False
        except Exception as e:
            logger.warning(f"Could not connect to local MusicBrainz DB: {e}")
            return False

    def disconnect(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
            self._available = False

    @property
    def available(self) -> bool:
        return self._available and self._conn is not None

    def _q(self, sql: str, params=()) -> list:
        """Execute query and return list of dicts."""
        import psycopg2.extras  # noqa: PLC0415
        with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # Artist search  (mirrors MusicBrainzProvider.search_artist interface)
    # ------------------------------------------------------------------

    def search_artist(self, artist_name: str) -> List[Dict]:
        """
        Return up to 5 artist dicts matching name.  Result shape matches the
        MusicBrainz REST API: {'id': mbid, 'name': ..., 'sort-name': ...}
        """
        if not self.available:
            return []
        s = self.schema
        sql = f"""
            SELECT a.gid::text  AS id,
                   a.name,
                   a.sort_name  AS "sort-name",
                   a.comment,
                   at.name      AS type,
                   area.name    AS area
            FROM   {s}.artist       a
            LEFT JOIN {s}.artist_type at   ON at.id = a.type
            LEFT JOIN {s}.area       area  ON area.id = a.area
            WHERE  unaccent(lower(a.name))      = unaccent(lower(%s))
               OR  unaccent(lower(a.sort_name)) = unaccent(lower(%s))
            ORDER BY
                (lower(a.name) = lower(%s)) DESC,
                a.name
            LIMIT 5
        """
        try:
            rows = self._q(sql, (artist_name, artist_name, artist_name))
            if not rows:
                # Fuzzy fallback with ILIKE
                sql_like = f"""
                    SELECT a.gid::text AS id, a.name, a.sort_name AS "sort-name", a.comment
                    FROM   {s}.artist a
                    WHERE  unaccent(a.name) ILIKE unaccent(%s)
                    ORDER BY length(a.name)
                    LIMIT 5
                """
                rows = self._q(sql_like, (f'%{artist_name}%',))
            return rows
        except Exception as e:
            logger.debug(f"Local MB artist search error: {e}")
            return []

    # ------------------------------------------------------------------
    # Release (album) search  (mirrors MusicBrainzProvider.search_release)
    # ------------------------------------------------------------------

    def search_release(self, album_title: str, artist: str) -> List[Dict]:
        """
        Return up to 10 release dicts.
        Result shape: {'id': mbid, 'title': ..., 'date': ..., 'artist-credit': [...]}
        """
        if not self.available:
            return []
        s = self.schema
        sql = f"""
            SELECT r.gid::text  AS id,
                   r.name       AS title,
                   COALESCE(r.date_year::text, '') AS date,
                   ac.name      AS artist_credit_name
            FROM   {s}.release          r
            JOIN   {s}.artist_credit    ac  ON ac.id = r.artist_credit
            WHERE  unaccent(lower(r.name)) = unaccent(lower(%s))
              AND  unaccent(lower(ac.name)) ILIKE unaccent(%s)
            ORDER BY
                r.date_year DESC NULLS LAST
            LIMIT 10
        """
        try:
            rows = self._q(sql, (album_title, f'%{artist}%'))
            if not rows:
                sql_like = f"""
                    SELECT r.gid::text AS id, r.name AS title,
                           COALESCE(r.date_year::text, '') AS date,
                           ac.name AS artist_credit_name
                    FROM   {s}.release r
                    JOIN   {s}.artist_credit ac ON ac.id = r.artist_credit
                    WHERE  unaccent(r.name) ILIKE unaccent(%s)
                      AND  unaccent(ac.name) ILIKE unaccent(%s)
                    ORDER BY r.date_year DESC NULLS LAST
                    LIMIT 10
                """
                rows = self._q(sql_like, (f'%{album_title}%', f'%{artist}%'))
            return rows
        except Exception as e:
            logger.debug(f"Local MB release search error: {e}")
            return []

    # ------------------------------------------------------------------
    # Full release fetch  (mirrors MusicBrainzProvider.get_release)
    # ------------------------------------------------------------------

    def get_release(self, mbid: str) -> Optional['AlbumMetadata']:
        """Fetch complete album metadata including tracks by release MBID."""
        if not self.available:
            return None
        s = self.schema
        try:
            # Release header
            rows = self._q(f"""
                SELECT r.name AS title,
                       r.date_year AS year,
                       r.date_month, r.date_day,
                       ac.name AS artist,
                       l.name  AS label
                FROM   {s}.release r
                JOIN   {s}.artist_credit ac ON ac.id = r.artist_credit
                LEFT JOIN {s}.release_label rl ON rl.release = r.id
                LEFT JOIN {s}.label         l  ON l.id = rl.label
                WHERE  r.gid = %s
                LIMIT  1
            """, (mbid,))
            if not rows:
                return None
            row = rows[0]

            # Track count
            tc_rows = self._q(f"""
                SELECT COUNT(*) AS cnt
                FROM   {s}.track t
                JOIN   {s}.medium m ON m.id = t.medium
                JOIN   {s}.release r ON r.id = m.release
                WHERE  r.gid = %s
            """, (mbid,))
            track_count = tc_rows[0]['cnt'] if tc_rows else 0

            date_str = '-'.join(filter(None, [
                str(row['year']) if row['year'] else None,
                f"{row['date_month']:02d}" if row['date_month'] else None,
                f"{row['date_day']:02d}" if row['date_day'] else None,
            ]))

            return AlbumMetadata(
                title=row['title'],
                artist=row['artist'],
                year=row['year'] or 0,
                rating=0.0,
                mbid=mbid,
                release_date=date_str,
                track_count=track_count,
                label=row['label'],
            )
        except Exception as e:
            logger.debug(f"Local MB get_release error: {e}")
            return None

    # ------------------------------------------------------------------
    # Track list for a release
    # ------------------------------------------------------------------

    def get_tracks(self, release_mbid: str) -> List[Dict]:
        """
        Return ordered list of tracks:
        {'position': int, 'title': str, 'length_ms': int, 'recording_gid': str}
        """
        if not self.available:
            return []
        s = self.schema
        try:
            return self._q(f"""
                SELECT m.position  AS disc,
                       t.position  AS position,
                       t.name      AS title,
                       rec.length  AS length_ms,
                       rec.gid::text AS recording_gid
                FROM   {s}.track     t
                JOIN   {s}.medium    m   ON m.id = t.medium
                JOIN   {s}.recording rec ON rec.id = t.recording
                JOIN   {s}.release   r   ON r.id = m.release
                WHERE  r.gid = %s
                ORDER  BY m.position, t.position
            """, (release_mbid,))
        except Exception as e:
            logger.debug(f"Local MB get_tracks error: {e}")
            return []


class LocalJsonMusicBrainzProvider:
    """
    Query MusicBrainz JSON dump files without needing PostgreSQL.

    Download: https://data.metabrainz.org/pub/musicbrainz/data/json-dumps
    Schema:   https://musicbrainz.org/doc/MusicBrainz_Database/Schema

    Expected directory layout (as extracted from the dump tarballs):
        <dump_dir>/
            artist/               ← one .json per artist MBID
            release/              ← one .json per release MBID
            release-group/        ← one .json per release-group MBID
            recording/            ← one .json per recording MBID

    On first use the provider builds lightweight in-memory indexes from the
    artist and release-group name → MBID mappings so searches are fast.
    Index build is O(n) over the file count; subsequent lookups are O(1).
    """

    def __init__(self, dump_dir: str):
        self.dump_dir = Path(dump_dir)
        self._artist_index: Dict[str, str] = {}       # lower(name) → mbid
        self._rg_index: Dict[str, List[str]] = {}     # lower(title) → [mbid, ...]
        self._indexed = False
        self._available = False

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Verify dump_dir exists and contains expected sub-directories."""
        if not self.dump_dir.exists():
            logger.warning(f"MusicBrainz JSON dump directory not found: {self.dump_dir}")
            return False
        required = ['artist', 'release-group']
        missing = [d for d in required if not (self.dump_dir / d).is_dir()]
        if missing:
            logger.warning(f"MusicBrainz JSON dump missing sub-dirs: {missing} in {self.dump_dir}")
            return False
        self._available = True
        logger.info(f"MusicBrainz JSON dump found at {self.dump_dir} — building name indexes…")
        self._build_indexes()
        return True

    def _build_indexes(self):
        """Scan artist/ and release-group/ once to build name → MBID maps."""
        artist_dir = self.dump_dir / 'artist'
        rg_dir = self.dump_dir / 'release-group'

        count_a = 0
        for p in artist_dir.glob('*.json'):
            try:
                data = json.loads(p.read_text(encoding='utf-8'))
                name = data.get('name', '')
                mbid = data.get('id', p.stem)
                if name:
                    self._artist_index[name.lower()] = mbid
                    # Also index sort-name
                    sn = data.get('sort-name', '')
                    if sn and sn.lower() != name.lower():
                        self._artist_index[sn.lower()] = mbid
                    count_a += 1
            except Exception:
                pass

        count_rg = 0
        for p in rg_dir.glob('*.json'):
            try:
                data = json.loads(p.read_text(encoding='utf-8'))
                title = data.get('title', '')
                mbid = data.get('id', p.stem)
                if title:
                    key = title.lower()
                    self._rg_index.setdefault(key, []).append(mbid)
                    count_rg += 1
            except Exception:
                pass

        self._indexed = True
        logger.info(f"  MusicBrainz JSON index: {count_a:,} artists, {count_rg:,} release-groups")

    @property
    def available(self) -> bool:
        return self._available

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_json(self, subdir: str, mbid: str) -> Optional[dict]:
        path = self.dump_dir / subdir / f'{mbid}.json'
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return None

    @staticmethod
    def _unaccent(s: str) -> str:
        """Very lightweight accent-stripping (covers common Latin diacritics)."""
        import unicodedata  # noqa: PLC0415
        return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('ascii').lower()

    # ------------------------------------------------------------------
    # Artist search
    # ------------------------------------------------------------------

    def search_artist(self, artist_name: str) -> List[Dict]:
        if not self._indexed:
            return []
        key = artist_name.lower()
        ua_key = self._unaccent(artist_name)

        # Exact match
        mbid = self._artist_index.get(key) or self._artist_index.get(ua_key)
        if mbid:
            data = self._read_json('artist', mbid)
            if data:
                return [{'id': mbid, 'name': data.get('name', artist_name),
                          'sort-name': data.get('sort-name', '')}]

        # Prefix / substring fallback (linear scan — only reached on miss)
        matches = []
        for name_lower, mid in self._artist_index.items():
            if key in name_lower or self._unaccent(name_lower).startswith(ua_key[:4]):
                data = self._read_json('artist', mid)
                if data:
                    matches.append({'id': mid, 'name': data.get('name', ''),
                                    'sort-name': data.get('sort-name', '')})
                if len(matches) >= 5:
                    break
        return matches

    # ------------------------------------------------------------------
    # Release search
    # ------------------------------------------------------------------

    def search_release(self, album_title: str, artist: str) -> List[Dict]:
        """Search release-group index then find a matching release inside it."""
        if not self._indexed:
            return []
        key = album_title.lower()
        ua_key = self._unaccent(album_title)
        artist_lower = artist.lower()

        candidates = (self._rg_index.get(key) or
                      self._rg_index.get(ua_key) or [])

        # Substring fallback
        if not candidates:
            for title_lower, mbids in self._rg_index.items():
                if key in title_lower:
                    candidates.extend(mbids)
                if len(candidates) >= 20:
                    break

        results = []
        for rg_mbid in candidates[:20]:
            rg = self._read_json('release-group', rg_mbid)
            if not rg:
                continue
            # Check artist-credit matches
            ac_names = [ac.get('artist', {}).get('name', '').lower()
                        for ac in rg.get('artist-credit', [])
                        if isinstance(ac, dict)]
            if artist_lower and not any(artist_lower in n for n in ac_names):
                continue
            # Return the first release MBID listed in the release-group
            releases = rg.get('releases', [])
            if releases:
                rel_id = releases[0].get('id', rg_mbid)
                results.append({'id': rel_id, 'title': rg.get('title', album_title),
                                 'date': rg.get('first-release-date', '')})
        return results

    # ------------------------------------------------------------------
    # Full release fetch
    # ------------------------------------------------------------------

    def get_release(self, mbid: str) -> Optional['AlbumMetadata']:
        data = self._read_json('release', mbid)
        if not data:
            return None
        artist_credits = data.get('artist-credit', [])
        artist = ', '.join(
            ac.get('artist', {}).get('name', '')
            for ac in artist_credits if isinstance(ac, dict)
        ) or 'Unknown Artist'
        date_str = data.get('date', '')
        year = int(date_str.split('-')[0]) if date_str and date_str[0].isdigit() else 0
        label = None
        label_info = data.get('label-info', [])
        if label_info and isinstance(label_info[0], dict):
            label = label_info[0].get('label', {}).get('name')
        media = data.get('media', [])
        track_count = sum(m.get('track-count', 0) for m in media if isinstance(m, dict))
        return AlbumMetadata(
            title=data.get('title', ''),
            artist=artist,
            year=year,
            rating=0.0,
            mbid=mbid,
            release_date=date_str,
            track_count=track_count,
            label=label,
        )

    def get_tracks(self, release_mbid: str) -> List[Dict]:
        data = self._read_json('release', release_mbid)
        if not data:
            return []
        tracks = []
        for disc_idx, medium in enumerate(data.get('media', []), 1):
            if not isinstance(medium, dict):
                continue
            for track in medium.get('tracks', []):
                if not isinstance(track, dict):
                    continue
                rec = track.get('recording', {})
                tracks.append({
                    'disc': disc_idx,
                    'position': track.get('position', 0),
                    'title': track.get('title') or rec.get('title', ''),
                    'length_ms': rec.get('length') or track.get('length'),
                    'recording_gid': rec.get('id', ''),
                })
        return tracks


class iTunesProvider:
    """
    Fetch music metadata from the free iTunes Search API.

    No API key or account required.  Artwork URLs are returned at 100×100
    by default; _artwork_url() upscales them to full resolution (up to 3000×3000)
    by rewriting the size segment in the CDN path.
    """

    SEARCH_URL  = 'https://itunes.apple.com/search'
    LOOKUP_URL  = 'https://itunes.apple.com/lookup'
    # Rate limit: Apple doesn't publish an exact number but 20 req/s is safe.
    _MIN_INTERVAL = 0.1

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'PlexMetadataGenerator/1.0'})
        self._last_request_time: float = 0.0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get(self, url: str, params: dict) -> Optional[dict]:
        """Rate-limited GET; returns parsed JSON or None on error."""
        import re
        elapsed = time.time() - self._last_request_time
        if elapsed < self._MIN_INTERVAL:
            time.sleep(self._MIN_INTERVAL - elapsed)
        self._last_request_time = time.time()
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.debug(f"iTunes API error: {e}")
            return None

    @staticmethod
    def _artwork_url(url: str, size: int = 3000) -> str:
        """Replace the WxHbb size token in an Apple CDN URL to get full-res art."""
        import re
        return re.sub(r'\d+x\d+bb', f'{size}x{size}bb', url) if url else url

    # ------------------------------------------------------------------
    # Artist search
    # ------------------------------------------------------------------

    def search_artist(self, artist_name: str) -> List[Dict]:
        """Return iTunes artist records matching artist_name."""
        data = self._get(self.SEARCH_URL, {
            'term': artist_name,
            'entity': 'musicArtist',
            'limit': 5,
        })
        if not data:
            return []
        results = [r for r in data.get('results', [])
                   if r.get('wrapperType') == 'artist']
        logger.debug(f"iTunes artist search '{artist_name}' → {len(results)} results")
        return results

    # ------------------------------------------------------------------
    # Album search + fetch
    # ------------------------------------------------------------------

    def search_album(self, album_title: str, artist: str) -> List[Dict]:
        """Return iTunes collection records matching album + artist."""
        data = self._get(self.SEARCH_URL, {
            'term': f'{album_title} {artist}',
            'entity': 'album',
            'limit': 10,
        })
        if not data:
            return []
        results = [r for r in data.get('results', [])
                   if r.get('wrapperType') == 'collection']
        logger.debug(f"iTunes album search '{album_title}' by '{artist}' → {len(results)} results")
        return results

    def get_album(self, collection_id: str) -> Optional[AlbumMetadata]:
        """Fetch full album metadata by iTunes collection ID."""
        data = self._get(self.LOOKUP_URL, {
            'id': collection_id,
            'entity': 'song',
        })
        if not data or not data.get('results'):
            return None

        results = data['results']
        # First result is the collection itself; remaining are tracks.
        album_rec = results[0]
        if album_rec.get('wrapperType') != 'collection':
            return None

        release_date = album_rec.get('releaseDate', '')
        year = int(release_date[:4]) if release_date else 0
        track_count = album_rec.get('trackCount', len(results) - 1)
        raw_art = album_rec.get('artworkUrl100', '')
        cover_url = self._artwork_url(raw_art) if raw_art else None

        genres = []
        if album_rec.get('primaryGenreName'):
            genres = [album_rec['primaryGenreName']]

        metadata = AlbumMetadata(
            title=album_rec.get('collectionName', ''),
            artist=album_rec.get('artistName', 'Unknown Artist'),
            year=year,
            rating=0.0,
            apple_id=str(collection_id),
            cover_url=cover_url,
            release_date=release_date[:10] if release_date else '',
            track_count=track_count,
            genres=genres,
            label=album_rec.get('copyright', ''),
        )
        logger.info(f"Retrieved iTunes metadata for '{metadata.title}' by '{metadata.artist}'")
        return metadata

    # ------------------------------------------------------------------
    # Convenience: build ArtistMetadata from a search result row
    # ------------------------------------------------------------------

    def build_artist_metadata(self, record: dict) -> ArtistMetadata:
        raw_art = record.get('artworkUrl100', '')
        return ArtistMetadata(
            name=record.get('artistName', ''),
            apple_id=str(record.get('artistId', '')),
            genres=[record['primaryGenreName']] if record.get('primaryGenreName') else [],
            image_url=self._artwork_url(raw_art) if raw_art else None,
        )


# Optional dependency — only imported when MusicKit credentials are configured.
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.backends import default_backend
    import base64 as _b64
    _CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    _CRYPTOGRAPHY_AVAILABLE = False


class AppleMusicKitProvider:
    """
    Fetch music metadata from the Apple MusicKit API.

    Requires an Apple Developer account (99 USD/yr) with a MusicKit key:
      1. developer.apple.com → Certificates, Identifiers & Profiles → Keys
      2. Create a key with "MusicKit" enabled → download the .p8 file
      3. Note the Key ID (shown on the key page) and your Team ID (top-right
         of the developer portal, 10-char string like "ABCDE12345")

    Tokens are JWTs signed with ES256 (the .p8 key).  They last up to 6 months;
    this class regenerates one lazily whenever the current one is within 60 s of
    expiry.
    """

    BASE_URL = 'https://api.music.apple.com/v1'

    def __init__(self, team_id: str, key_id: str, private_key_path: str,
                 storefront: str = 'us'):
        self.team_id = team_id
        self.key_id = key_id
        self.private_key_path = private_key_path
        self.storefront = storefront
        self._token: Optional[str] = None
        self._token_expiry: float = 0.0
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _make_token(self) -> Optional[str]:
        if not _CRYPTOGRAPHY_AVAILABLE:
            logger.warning(
                "Apple MusicKit requires the 'cryptography' package: "
                "pip install cryptography"
            )
            return None
        try:
            with open(self.private_key_path, 'rb') as f:
                private_key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )
        except Exception as e:
            logger.error(f"Could not load MusicKit private key: {e}")
            return None

        now = int(time.time())
        exp = now + 15_777_000  # 6 months (Apple's maximum)

        # Build JWT manually (avoid PyJWT dependency for simplicity)
        import json as _json
        import struct

        def _b64url(data: bytes) -> str:
            return _b64.urlsafe_b64encode(data).rstrip(b'=').decode()

        header  = _b64url(_json.dumps({'alg': 'ES256', 'kid': self.key_id}).encode())
        payload = _b64url(_json.dumps({'iss': self.team_id, 'iat': now, 'exp': exp}).encode())
        signing_input = f'{header}.{payload}'.encode()

        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
        signature_der = private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))

        # Convert DER signature to raw r||s (64 bytes) for ES256
        r, s = decode_dss_signature(signature_der)
        sig_bytes = r.to_bytes(32, 'big') + s.to_bytes(32, 'big')

        self._token = f'{header}.{payload}.{_b64url(sig_bytes)}'
        self._token_expiry = exp - 60  # refresh 60 s before actual expiry
        logger.info("Generated Apple MusicKit developer token")
        return self._token

    def _get_token(self) -> Optional[str]:
        if not self._token or time.time() >= self._token_expiry:
            return self._make_token()
        return self._token

    def _headers(self) -> Optional[dict]:
        token = self._get_token()
        if not token:
            return None
        return {'Authorization': f'Bearer {token}'}

    # ------------------------------------------------------------------
    # Availability check
    # ------------------------------------------------------------------

    def available(self) -> bool:
        """Return True if we can generate a valid token."""
        return self._get_token() is not None

    # ------------------------------------------------------------------
    # Internal GET
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict = None) -> Optional[dict]:
        hdrs = self._headers()
        if not hdrs:
            return None
        try:
            resp = self.session.get(
                f'{self.BASE_URL}{path}',
                headers=hdrs,
                params=params or {},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.debug(f"Apple MusicKit API error: {e}")
            return None

    # ------------------------------------------------------------------
    # Artwork helper (same CDN pattern as iTunes)
    # ------------------------------------------------------------------

    @staticmethod
    def _artwork_url(template: str, size: int = 3000) -> str:
        """Replace {w}x{h} template tokens with actual pixel dimensions."""
        return template.replace('{w}', str(size)).replace('{h}', str(size)) if template else template

    # ------------------------------------------------------------------
    # Artist search
    # ------------------------------------------------------------------

    def search_artist(self, artist_name: str) -> List[Dict]:
        data = self._get(f'/catalog/{self.storefront}/search', {
            'term': artist_name,
            'types': 'artists',
            'limit': 5,
        })
        if not data:
            return []
        items = data.get('results', {}).get('artists', {}).get('data', [])
        logger.debug(f"MusicKit artist search '{artist_name}' → {len(items)} results")
        return items

    def build_artist_metadata(self, record: dict) -> ArtistMetadata:
        attrs = record.get('attributes', {})
        art = attrs.get('artwork', {})
        image_url = self._artwork_url(art.get('url', '')) if art else None
        return ArtistMetadata(
            name=attrs.get('name', ''),
            apple_id=record.get('id', ''),
            genres=attrs.get('genreNames', []),
            image_url=image_url,
        )

    # ------------------------------------------------------------------
    # Album search + fetch
    # ------------------------------------------------------------------

    def search_album(self, album_title: str, artist: str) -> List[Dict]:
        data = self._get(f'/catalog/{self.storefront}/search', {
            'term': f'{album_title} {artist}',
            'types': 'albums',
            'limit': 10,
        })
        if not data:
            return []
        items = data.get('results', {}).get('albums', {}).get('data', [])
        logger.debug(f"MusicKit album search '{album_title}' by '{artist}' → {len(items)} results")
        return items

    def get_album(self, apple_id: str) -> Optional[AlbumMetadata]:
        data = self._get(f'/catalog/{self.storefront}/albums/{apple_id}')
        if not data or not data.get('data'):
            return None
        rec   = data['data'][0]
        attrs = rec.get('attributes', {})

        release_date = attrs.get('releaseDate', '')
        year = int(release_date[:4]) if release_date else 0
        art  = attrs.get('artwork', {})
        cover_url = self._artwork_url(art.get('url', '')) if art else None

        metadata = AlbumMetadata(
            title=attrs.get('name', ''),
            artist=attrs.get('artistName', 'Unknown Artist'),
            year=year,
            rating=0.0,
            apple_id=apple_id,
            cover_url=cover_url,
            release_date=release_date,
            track_count=attrs.get('trackCount', 0),
            genres=attrs.get('genreNames', []),
            label=attrs.get('recordLabel', ''),
        )
        logger.info(f"Retrieved MusicKit metadata for '{metadata.title}' by '{metadata.artist}'")
        return metadata


class PlexNFOGenerator:
    """Generate Plex-compliant NFO files for all media types"""

    @staticmethod
    def _pretty(root: ET.Element) -> str:
        import xml.dom.minidom
        raw = ET.tostring(root, encoding='unicode')
        dom = xml.dom.minidom.parseString(raw)
        return dom.toprettyxml(indent='  ', encoding=None).replace(
            '<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        )

    def generate_show_nfo(self, metadata: ShowMetadata) -> str:
        """Generate tvshow.nfo XML"""
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
            ET.SubElement(root, 'tvdbid').text = str(metadata.tvdb_id)
        if metadata.tmdb_id:
            ET.SubElement(root, 'tmdbid').text = str(metadata.tmdb_id)
        if metadata.imdb_id:
            ET.SubElement(root, 'imdbid').text = metadata.imdb_id
        
        for genre in (metadata.genres or []):
            ET.SubElement(root, 'genre').text = genre
        
        if metadata.poster_url:
            ET.SubElement(root, 'poster').text = metadata.poster_url
        
        return self._pretty(root)
    
    def generate_episode_nfo(self, metadata: EpisodeMetadata) -> str:
        """Generate episode NFO XML"""
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
    
    def generate_album_nfo(self, metadata: AlbumMetadata) -> str:
        """Generate album.nfo XML for music"""
        root = ET.Element('album')
        
        ET.SubElement(root, 'title').text = metadata.title
        ET.SubElement(root, 'artist').text = metadata.artist
        
        if metadata.year:
            ET.SubElement(root, 'year').text = str(metadata.year)
        
        if metadata.release_date:
            ET.SubElement(root, 'releasedate').text = metadata.release_date
        
        ET.SubElement(root, 'plot').text = metadata.plot or 'Music album'
        ET.SubElement(root, 'rating').text = str(metadata.rating or 0)
        
        if metadata.label:
            ET.SubElement(root, 'label').text = metadata.label
        
        ET.SubElement(root, 'tracks').text = str(metadata.track_count)
        
        # MusicBrainz ID
        if metadata.mbid:
            ET.SubElement(root, 'mbid').text = metadata.mbid

        # Apple Music / iTunes ID
        if metadata.apple_id:
            ET.SubElement(root, 'appleid').text = metadata.apple_id

        # Genres
        for genre in (metadata.genres or []):
            ET.SubElement(root, 'genre').text = genre
        
        # Cover art
        if metadata.cover_url:
            ET.SubElement(root, 'cover').text = metadata.cover_url
        
        return self._pretty(root)
    
    def generate_artist_nfo(self, metadata: ArtistMetadata) -> str:
        """Generate artist.nfo XML for music"""
        root = ET.Element('artist')
        
        ET.SubElement(root, 'name').text = metadata.name
        ET.SubElement(root, 'plot').text = metadata.bio or f'Music artist: {metadata.name}'
        
        if metadata.mbid:
            ET.SubElement(root, 'mbid').text = metadata.mbid

        if metadata.apple_id:
            ET.SubElement(root, 'appleid').text = metadata.apple_id

        for genre in (metadata.genres or []):
            ET.SubElement(root, 'genre').text = genre
        
        for member in (metadata.members or []):
            ET.SubElement(root, 'member').text = member
        
        if metadata.image_url:
            ET.SubElement(root, 'image').text = metadata.image_url
        
        return self._pretty(root)
    
    def generate_track_nfo(self, metadata: TrackMetadata) -> str:
        """Generate track.nfo XML for individual songs"""
        root = ET.Element('track')
        
        ET.SubElement(root, 'title').text = metadata.title
        ET.SubElement(root, 'artist').text = metadata.artist
        ET.SubElement(root, 'album').text = metadata.album
        
        ET.SubElement(root, 'tracknumber').text = str(metadata.track_number)
        ET.SubElement(root, 'rating').text = str(metadata.rating or 0)
        
        if metadata.duration:
            ET.SubElement(root, 'duration').text = str(metadata.duration)
        
        if metadata.genre:
            ET.SubElement(root, 'genre').text = metadata.genre
        
        if metadata.mbid:
            ET.SubElement(root, 'mbid').text = metadata.mbid
        
        if metadata.isrc:
            ET.SubElement(root, 'isrc').text = metadata.isrc
        
        return self._pretty(root)


class MediaTypeDetector:
    """Detect media type from library structure"""
    
    @staticmethod
    def detect_type(path: Path) -> MediaType:
        """
        Determine media type from directory structure
        
        TV Shows: Show Name / Season N / episode.mkv
        Music: Artist / Album / 01 - Track.mp3
        """
        
        # Check for audio files
        audio_extensions = {'.mp3', '.flac', '.m4a', '.aac', '.opus', '.wma', '.wav'}
        video_extensions = {'.mkv', '.mp4', '.avi', '.m4v', '.mov'}
        
        for file_path in path.rglob('*'):
            suffix = file_path.suffix.lower()
            
            if suffix in audio_extensions:
                # This is music
                # Check structure: if 2+ parent dirs and contains audio, assume music
                parents = list(file_path.parents)
                if len(parents) >= 2:
                    return MediaType.MUSIC_ALBUM
                return MediaType.MUSIC_TRACK
            
            elif suffix in video_extensions:
                return MediaType.TV_SHOW
        
        return MediaType.TV_SHOW  # Default fallback


class PlexMetadataOrchestrator:
    """Main orchestrator for metadata generation (TV + Music)"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.tv_library_root = Path(config.get('tv_library_root', '/mnt/media/TV'))
        self.music_library_root = Path(config.get('music_library_root', '/mnt/media/Music'))
        
        self.plex_url = config.get('plex_url', 'http://localhost:32400')
        self.plex_token = config.get('plex_token')
        self.tv_library_key = config.get('tv_library_key', '1')
        self.music_library_key = config.get('music_library_key', '2')
        
        # Initialize providers
        self.nfo_generator = PlexNFOGenerator()
        
        # Music providers — priority: local MB (PostgreSQL) → local MB (JSON) → Apple MusicKit → iTunes → MB REST
        # Local MusicBrainz PostgreSQL database (optional)
        self.mb_local: Optional[LocalMusicBrainzProvider] = None
        mb_db_cfg = config.get('musicbrainz_db', {})
        if mb_db_cfg.get('skip') is not True and (mb_db_cfg.get('host') or mb_db_cfg.get('dbname')):
            provider = LocalMusicBrainzProvider(
                host=mb_db_cfg.get('host', 'localhost'),
                port=int(mb_db_cfg.get('port', 5432)),
                dbname=mb_db_cfg.get('dbname', 'musicbrainz'),
                user=mb_db_cfg.get('user', 'musicbrainz'),
                password=mb_db_cfg.get('password', ''),
                schema=mb_db_cfg.get('schema', 'musicbrainz'),
            )
            if provider.connect():
                self.mb_local = provider
            else:
                logger.warning("Local MusicBrainz DB configured but unreachable — trying JSON dump next")

        # Local MusicBrainz JSON dump (optional; used if PostgreSQL provider unavailable)
        self.mb_json: Optional[LocalJsonMusicBrainzProvider] = None
        if self.mb_local is None:
            json_dump_dir = config.get('musicbrainz_json_dump_dir', '')
            if json_dump_dir:
                json_provider = LocalJsonMusicBrainzProvider(json_dump_dir)
                if json_provider.connect():
                    self.mb_json = json_provider
                else:
                    logger.warning("MusicBrainz JSON dump configured but unavailable — falling back to REST API")

        # MusicBrainz REST API (no key required, just user-agent)
        self.musicbrainz = MusicBrainzProvider(
            user_agent=f"PlexMetadataGenerator/1.0 (+{config.get('musicbrainz_contact', 'contact@example.com')})"
        )

        # iTunes Search API — always available, no credentials needed
        self.itunes = iTunesProvider()
        logger.info("iTunes Search API provider ready (no auth required)")

        # Apple MusicKit API — optional; requires Apple Developer credentials
        self.musickit: Optional[AppleMusicKitProvider] = None
        mk_cfg = config.get('apple_musickit', {})
        if (mk_cfg.get('enabled', False) and
                mk_cfg.get('team_id') and mk_cfg.get('key_id') and mk_cfg.get('private_key_path')):
            provider = AppleMusicKitProvider(
                team_id=mk_cfg['team_id'],
                key_id=mk_cfg['key_id'],
                private_key_path=mk_cfg['private_key_path'],
                storefront=mk_cfg.get('storefront', 'us'),
            )
            if provider.available():
                self.musickit = provider
                logger.info("Apple MusicKit API provider ready")
            else:
                logger.warning("Apple MusicKit credentials configured but token generation failed — falling back to iTunes")
        
        # TV providers (from previous implementation)
        from plex_metadata_generator import TVDbProvider, TMDbProvider, TunarrMetadataProvider, MetadataDownloader
        
        tvdb_key = config.get('tvdb_api_key')
        self.tvdb = TVDbProvider(tvdb_key) if tvdb_key else None
        if self.tvdb:
            self.tvdb.authenticate()
        
        tmdb_key = config.get('tmdb_api_key')
        self.tmdb = TMDbProvider(tmdb_key) if tmdb_key else None
        
        self.tunarr = TunarrMetadataProvider(config.get('tunarr_db_path'))
        self.downloader = MetadataDownloader(config.get('cache_dir'))
        
        self.media_detector = MediaTypeDetector()
    
    def process_tv_library(self):
        """Process TV show library"""
        logger.info("Processing TV show library")
        
        if not self.tv_library_root.exists():
            logger.error(f"TV library root does not exist: {self.tv_library_root}")
            return
        
        for show_dir in self.tv_library_root.iterdir():
            if show_dir.is_dir():
                self._process_tv_show(show_dir.name, show_dir)
    
    def process_music_library(self, specific_artist: str = None):
        """Process music library (artists and albums)"""
        workers = getattr(self, 'workers', 1)
        logger.info(f"Processing music library ({workers} worker(s))")

        if not self.music_library_root.exists():
            logger.error(f"Music library root does not exist: {self.music_library_root}")
            return

        # Structure: Artist / Album / Tracks
        artist_dirs = [
            d for d in sorted(self.music_library_root.iterdir())
            if d.is_dir() and not d.name.startswith('.')
            and (not specific_artist or d.name == specific_artist)
        ]

        if workers > 1:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futures = {ex.submit(self._process_music_artist, d): d for d in artist_dirs}
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Error processing {futures[future].name}: {e}")
        else:
            for artist_dir in artist_dirs:
                self._process_music_artist(artist_dir)
    
    def _process_tv_show(self, show_name: str, show_path: Path):
        """Process a single TV show (existing implementation)"""
        logger.info(f"Processing TV show: {show_name}")
        # Implementation from original plex_metadata_generator.py
        # Search metadata and generate NFO files
        pass
    
    def _process_music_artist(self, artist_path: Path):
        """Process artist directory with albums"""
        artist_name = artist_path.name
        logger.info(f"Processing music artist: {artist_name}")
        
        # Search for artist metadata — priority: local MB PG → local MB JSON → MusicKit → iTunes → MB REST
        artist_metadata = None

        # 1. Local MusicBrainz PostgreSQL DB (fastest, no rate limits)
        if not artist_metadata and self.mb_local and self.mb_local.available:
            results = self.mb_local.search_artist(artist_name)
            if results:
                artist_metadata = ArtistMetadata(
                    name=results[0]['name'],
                    mbid=results[0]['id'],
                )
                logger.info(f"Found artist '{artist_name}' in local MusicBrainz DB")

        # 2. Local MusicBrainz JSON dump
        if not artist_metadata and self.mb_json and self.mb_json.available:
            results = self.mb_json.search_artist(artist_name)
            if results:
                artist_metadata = ArtistMetadata(
                    name=results[0]['name'],
                    mbid=results[0]['id'],
                )
                logger.info(f"Found artist '{artist_name}' in local MusicBrainz JSON dump")

        # 3. Apple MusicKit API (rich artwork + genres; requires Developer account)
        if not artist_metadata and self.musickit:
            results = self.musickit.search_artist(artist_name)
            if results:
                artist_metadata = self.musickit.build_artist_metadata(results[0])
                logger.info(f"Found artist '{artist_name}' via Apple MusicKit")

        # 4. iTunes Search API (free, no auth, always available)
        if not artist_metadata and self.itunes:
            results = self.itunes.search_artist(artist_name)
            if results:
                artist_metadata = self.itunes.build_artist_metadata(results[0])
                logger.info(f"Found artist '{artist_name}' via iTunes")

        # 5. MusicBrainz REST API (rate-limited fallback)
        if not artist_metadata and self.musicbrainz:
            results = self.musicbrainz.search_artist(artist_name)
            if results:
                artist_metadata = ArtistMetadata(
                    name=results[0]['name'],
                    mbid=results[0]['id'],
                )
                logger.info(f"Found artist '{artist_name}' on MusicBrainz")
        
        if not artist_metadata:
            # Create basic metadata
            artist_metadata = ArtistMetadata(name=artist_name)
            logger.warning(f"Could not find metadata for artist '{artist_name}'")
        
        # Generate artist NFO
        nfo_content = self.nfo_generator.generate_artist_nfo(artist_metadata)
        nfo_path = artist_path / 'artist.nfo'
        
        try:
            nfo_path.write_text(nfo_content, encoding='utf-8')
            logger.info(f"Wrote artist NFO: {nfo_path}")
        except IOError as e:
            logger.error(f"Failed to write artist NFO: {e}")
        
        # Download artist image — prefer embedded artwork from first track in first album
        artist_img_path = artist_path / 'artist.jpg'
        if not artist_img_path.exists():
            first_audio = None
            for album_dir in sorted(artist_path.iterdir()):
                if album_dir.is_dir() and not album_dir.name.startswith('.'):
                    first_audio = self._first_audio_in_dir(album_dir)
                    if first_audio:
                        break
            if first_audio and self._extract_embedded_artwork(first_audio, artist_img_path):
                logger.info(f"  ✓ Extracted artist.jpg from embedded artwork ({first_audio.name})")
            elif artist_metadata.image_url:
                self.downloader.download_image(artist_metadata.image_url, artist_img_path)
        
        # Process albums in this artist directory
        for album_dir in artist_path.iterdir():
            if album_dir.is_dir() and not album_dir.name.startswith('.'):
                self._process_music_album(album_dir, artist_name, artist_metadata)
    
    def _process_music_album(self, album_path: Path, artist_name: str, artist_metadata: ArtistMetadata):
        """Process album directory with tracks"""
        album_name = album_path.name
        logger.info(f"Processing album: {album_name} by {artist_name}")
        
        # Search for album metadata — priority: local MB PG → local MB JSON → MusicKit → iTunes → MB REST
        album_metadata = None

        # 1. Local MusicBrainz PostgreSQL DB
        if not album_metadata and self.mb_local and self.mb_local.available:
            results = self.mb_local.search_release(album_name, artist_name)
            if results:
                mbid = results[0]['id']
                album_metadata = self.mb_local.get_release(mbid)
                if album_metadata:
                    logger.info(f"Found album '{album_name}' in local MusicBrainz DB")

        # 2. Local MusicBrainz JSON dump
        if not album_metadata and self.mb_json and self.mb_json.available:
            results = self.mb_json.search_release(album_name, artist_name)
            if results:
                mbid = results[0]['id']
                album_metadata = self.mb_json.get_release(mbid)
                if album_metadata:
                    logger.info(f"Found album '{album_name}' in local MusicBrainz JSON dump")

        # 3. Apple MusicKit API (high-res artwork + full metadata)
        if not album_metadata and self.musickit:
            results = self.musickit.search_album(album_name, artist_name)
            if results:
                apple_id = results[0].get('id', '')
                album_metadata = self.musickit.get_album(apple_id)
                if album_metadata:
                    logger.info(f"Found album '{album_name}' via Apple MusicKit")

        # 4. iTunes Search API (free, no auth)
        if not album_metadata and self.itunes:
            results = self.itunes.search_album(album_name, artist_name)
            if results:
                collection_id = results[0].get('collectionId', '')
                album_metadata = self.itunes.get_album(collection_id)
                if album_metadata:
                    logger.info(f"Found album '{album_name}' via iTunes")

        # 5. MusicBrainz REST API (rate-limited fallback)
        if not album_metadata and self.musicbrainz:
            results = self.musicbrainz.search_release(album_name, artist_name)
            if results:
                mbid = results[0]['id']
                album_metadata = self.musicbrainz.get_release(mbid)
                if album_metadata:
                    logger.info(f"Found album '{album_name}' on MusicBrainz")
        
        if not album_metadata:
            # Create basic metadata
            album_metadata = AlbumMetadata(
                title=album_name,
                artist=artist_name,
                year=0,
                rating=0.0,
                plot=f"Album: {album_name}"
            )
            logger.warning(f"Could not find metadata for album '{album_name}'")
        
        # Generate album NFO
        nfo_content = self.nfo_generator.generate_album_nfo(album_metadata)
        nfo_path = album_path / 'album.nfo'
        
        try:
            nfo_path.write_text(nfo_content, encoding='utf-8')
            logger.info(f"Wrote album NFO: {nfo_path}")
        except IOError as e:
            logger.error(f"Failed to write album NFO: {e}")
        
        # Download cover art — prefer embedded artwork from first track in album
        cover_path = album_path / 'folder.jpg'
        if not cover_path.exists():
            first_audio = self._first_audio_in_dir(album_path)
            if first_audio and self._extract_embedded_artwork(first_audio, cover_path):
                logger.info(f"  ✓ Extracted album cover from embedded artwork ({first_audio.name})")
            elif album_metadata.cover_url:
                self.downloader.download_image(album_metadata.cover_url, cover_path)
        
        # Process individual tracks
        self._process_album_tracks(album_path, album_metadata, artist_metadata)
    
    def _process_album_tracks(self, album_path: Path, album_metadata: AlbumMetadata, 
                             artist_metadata: ArtistMetadata):
        """Generate metadata for individual tracks"""
        
        # Audio file extensions
        audio_extensions = {'.mp3', '.flac', '.m4a', '.aac', '.opus', '.wma', '.wav'}
        
        audio_files = []
        for ext in audio_extensions:
            audio_files.extend(album_path.glob(f'*{ext}'))
        
        audio_files.sort()
        
        for idx, audio_file in enumerate(audio_files, 1):
            # Extract track info from filename if possible
            # Format: "01 - Song Title.mp3" or "01 Song Title.mp3"
            
            track_title = audio_file.stem
            # Try to parse track number
            track_num = 1
            if track_title and track_title[0].isdigit():
                parts = track_title.split('-', 1)
                try:
                    track_num = int(parts[0].strip())
                    track_title = parts[1].strip() if len(parts) > 1 else f"Track {track_num}"
                except ValueError:
                    track_title = track_title
            else:
                track_num = idx
            
            # Create track metadata
            track_metadata = TrackMetadata(
                title=track_title,
                artist=artist_metadata.name,
                album=album_metadata.title,
                track_number=track_num,
                rating=album_metadata.rating,
                genre=', '.join(artist_metadata.genres) if artist_metadata.genres else ''
            )
            
            # Generate track NFO
            nfo_content = self.nfo_generator.generate_track_nfo(track_metadata)
            nfo_path = audio_file.with_suffix('.nfo')
            
            try:
                nfo_path.write_text(nfo_content, encoding='utf-8')
                logger.info(f"Wrote track NFO: {nfo_path}")
            except IOError as e:
                logger.error(f"Failed to write track NFO: {e}")
    
    @staticmethod
    def _extract_embedded_artwork(source_path: Path, dest_path: Path) -> bool:
        """Extract embedded cover art from a media file using ffmpeg (3-strategy cascade)."""
        import subprocess as _sp
        src = str(source_path)
        dst = str(dest_path)
        for cmd in [
            ['ffmpeg', '-i', src, '-an', '-vframes', '1', '-map', '0:v:1', '-y', dst],
            ['ffmpeg', '-i', src, '-map', '0:v', '-map', '-0:V', '-vframes', '1', '-y', dst],
            ['ffmpeg', '-i', src, '-an', '-vsync', '2', '-y', dst],
        ]:
            try:
                r = _sp.run(cmd, capture_output=True, timeout=30)
                if r.returncode == 0 and dest_path.exists() and dest_path.stat().st_size > 1000:
                    return True
                dest_path.unlink(missing_ok=True)
            except Exception:
                pass
        return False

    @staticmethod
    def _first_audio_in_dir(directory: Path) -> Optional[Path]:
        """Return the first audio file found in a directory (sorted), or None."""
        audio_exts = {'.mp3', '.m4a', '.aac', '.flac', '.ogg', '.opus', '.wav', '.aiff', '.alac'}
        for f in sorted(directory.iterdir()):
            if f.is_file() and f.suffix.lower() in audio_exts:
                return f
        return None

    def refresh_plex_library(self, library_key: str) -> bool:
        """Trigger Plex library refresh"""
        if not self.plex_token:
            logger.warning("Plex token not configured, skipping library refresh")
            return False
        
        try:
            headers = {'X-Plex-Token': self.plex_token}
            response = requests.post(
                f'{self.plex_url}/library/sections/{library_key}/refresh',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Plex library {library_key} refresh triggered successfully")
                return True
            else:
                logger.warning(f"Plex refresh returned status {response.status_code}")
                return False
        except requests.RequestException as e:
            logger.error(f"Failed to trigger Plex refresh: {e}")
            return False
    
    def run(self, media_type: str = 'all', specific_item: str = None):
        """
        Main execution method

        Args:
            media_type: 'tv', 'movies', 'music', or 'all'
            specific_item: Process only a specific show/artist/movie if provided
        """
        try:
            if media_type in ('tv', 'all'):
                logger.info("Starting TV show metadata generation")
                self.tunarr.connect()  # optional; failures are logged and tolerated
                self.process_tv_library()
                self.tunarr.disconnect()
                self.refresh_plex_library(self.tv_library_key)

            if media_type in ('movies', 'all'):
                logger.info("Starting movie metadata generation")
                # Delegate to base script's process_movie_library (full NFO + artwork)
                from plex_metadata_generator import PlexMetadataOrchestrator as BaseOrchestrator
                base = BaseOrchestrator(self.config, force=self.force,
                                        workers=getattr(self, 'workers', 1))
                base.process_movie_library(specific_movie=specific_item)

            if media_type in ('music', 'all'):
                logger.info("Starting music metadata generation")
                self.process_music_library(specific_artist=specific_item)
                self.refresh_plex_library(self.music_library_key)

            logger.info("Metadata generation complete")
        except Exception as e:
            logger.error(f"Fatal error during metadata generation: {e}", exc_info=True)
            raise


def _apple_musickit_dialog_tkinter() -> Optional[dict]:
    """
    Show a native macOS Tkinter form to collect Apple Developer credentials.
    Returns a dict with keys team_id, key_id, private_key_path, storefront,
    or None if the user cancelled.
    """
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
    except ImportError:
        return None

    result: dict = {}
    root = tk.Tk()
    root.title("Apple MusicKit Credentials")
    root.resizable(False, False)

    # Try to make it look native on macOS
    try:
        root.tk.call('::tk::unsupported::MacWindowStyle', 'style', root._w, 'moveableModal', '')
    except Exception:
        pass

    pad = {'padx': 12, 'pady': 6}

    tk.Label(root, text="Apple MusicKit API Setup", font=('Helvetica', 14, 'bold')).grid(
        row=0, column=0, columnspan=3, pady=(14, 4))
    tk.Label(root,
             text="Enter your Apple Developer credentials to enable the MusicKit API.\n"
                  "Get these at developer.apple.com → Certificates, Identifiers & Profiles → Keys.",
             justify='left', wraplength=480).grid(row=1, column=0, columnspan=3, **pad)

    fields = [
        ('Team ID',    'team_id',          'Your 10-character Apple Developer Team ID  (e.g. ABCDE12345)'),
        ('Key ID',     'key_id',           '10-character Key ID shown on your MusicKit key page'),
        ('Storefront', 'storefront',        'Two-letter country code for catalog searches (default: us)'),
    ]

    entries: dict = {}
    for row_idx, (label, key, hint) in enumerate(fields, start=2):
        tk.Label(root, text=label + ':', anchor='e', width=14).grid(row=row_idx, column=0, **pad, sticky='e')
        var = tk.StringVar(value='us' if key == 'storefront' else '')
        entry = tk.Entry(root, textvariable=var, width=40)
        entry.grid(row=row_idx, column=1, **pad, sticky='w')
        tk.Label(root, text=hint, fg='grey', font=('Helvetica', 10)).grid(
            row=row_idx, column=2, padx=(0, 12), sticky='w')
        entries[key] = var

    # Private key picker
    pk_row = len(fields) + 2
    tk.Label(root, text='Private Key (.p8):', anchor='e', width=14).grid(row=pk_row, column=0, **pad, sticky='e')
    pk_var = tk.StringVar()
    pk_entry = tk.Entry(root, textvariable=pk_var, width=40)
    pk_entry.grid(row=pk_row, column=1, **pad, sticky='w')
    tk.Button(root, text='Browse…', command=lambda: pk_var.set(
        filedialog.askopenfilename(title='Select .p8 private key', filetypes=[('P8 key', '*.p8'), ('All', '*')])
    )).grid(row=pk_row, column=2, padx=(0, 12), pady=6)

    def on_ok():
        team = entries['team_id'].get().strip()
        key  = entries['key_id'].get().strip()
        sf   = entries['storefront'].get().strip() or 'us'
        pk   = pk_var.get().strip()
        if not team or not key or not pk:
            messagebox.showerror('Missing fields', 'Team ID, Key ID, and the .p8 file are all required.')
            return
        if not os.path.isfile(pk):
            messagebox.showerror('File not found', f'Private key not found:\n{pk}')
            return
        result.update({'team_id': team, 'key_id': key, 'private_key_path': pk, 'storefront': sf})
        root.quit()

    def on_cancel():
        root.quit()

    btn_frame = tk.Frame(root)
    btn_frame.grid(row=pk_row + 1, column=0, columnspan=3, pady=(8, 14))
    tk.Button(btn_frame, text='Cancel', width=10, command=on_cancel).pack(side='left', padx=8)
    tk.Button(btn_frame, text='OK', width=10, default='active', command=on_ok).pack(side='left', padx=8)
    root.bind('<Return>', lambda e: on_ok())
    root.bind('<Escape>', lambda e: on_cancel())

    root.update_idletasks()
    # Centre on screen
    w, h = root.winfo_width(), root.winfo_height()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f'+{(sw - w) // 2}+{(sh - h) // 2}')

    root.mainloop()
    try:
        root.destroy()
    except Exception:
        pass

    return result if result else None


def _apple_musickit_dialog_console() -> Optional[dict]:
    """Sequential console prompts as a fallback when no display is available."""
    print('\n── Apple MusicKit API Setup ──────────────────────────────────')
    print('Enter your Apple Developer credentials (Ctrl-C to skip).')
    print('Get them at developer.apple.com → Certificates → Keys\n')
    try:
        team_id = input('  Team ID (e.g. ABCDE12345): ').strip()
        if not team_id:
            return None
        key_id  = input('  Key ID: ').strip()
        if not key_id:
            return None
        pk_path = input('  Path to .p8 private key file: ').strip()
        if not pk_path or not os.path.isfile(pk_path):
            print('  ⚠ File not found — skipping MusicKit setup.')
            return None
        storefront = input('  Storefront (default: us): ').strip() or 'us'
        return {'team_id': team_id, 'key_id': key_id,
                'private_key_path': pk_path, 'storefront': storefront}
    except (KeyboardInterrupt, EOFError):
        print()
        return None


def prompt_apple_music_credentials(config: dict, config_path: str) -> dict:
    """
    Pre-flight dialog for Apple MusicKit credentials.

    If credentials are already configured (and the key file exists), this is a
    no-op.  If the user declines, apple_musickit.skip is set to True so the
    question is not asked again on future runs.

    The iTunes Search API is always active regardless of this dialog.
    """
    import platform

    mk = config.get('apple_musickit', {})

    # Already fully configured → nothing to ask
    if (mk.get('team_id') and mk.get('key_id') and mk.get('private_key_path')
            and os.path.isfile(mk.get('private_key_path', ''))):
        logger.info("Apple MusicKit credentials already configured")
        return config

    # User previously said no → respect it
    if mk.get('skip') is True:
        return config

    # --- Ask the user ---
    print('\n╔══════════════════════════════════════════════════════════╗')
    print('║       Apple MusicKit API  (optional enhancement)        ║')
    print('╠══════════════════════════════════════════════════════════╣')
    print('║  The free iTunes Search API is already active.          ║')
    print('║  MusicKit (requires Apple Developer account, $99/yr)    ║')
    print('║  adds higher-resolution artwork and richer metadata.    ║')
    print('╚══════════════════════════════════════════════════════════╝')
    try:
        answer = input('\nDo you have an Apple Developer account and want to set up MusicKit? [y/N] ').strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        answer = 'n'

    if answer not in ('y', 'yes'):
        config.setdefault('apple_musickit', {})['skip'] = True
        _save_config_if_agreed(config, config_path)
        return config

    # --- Collect credentials ---
    creds = None

    # Try native Tkinter dialog on macOS with a display
    if platform.system() == 'Darwin' and os.environ.get('DISPLAY', '') != '' or \
            (platform.system() == 'Darwin' and 'TERM_PROGRAM' not in os.environ):
        # On macOS the display is always available even without $DISPLAY
        creds = _apple_musickit_dialog_tkinter()

    if creds is None:
        creds = _apple_musickit_dialog_console()

    if not creds:
        print('  MusicKit setup skipped — iTunes Search API will be used instead.')
        config.setdefault('apple_musickit', {})['skip'] = True
        _save_config_if_agreed(config, config_path)
        return config

    # --- Test the token ---
    print('  Testing MusicKit credentials…', end=' ', flush=True)
    provider = AppleMusicKitProvider(**creds)
    if provider.available():
        print('✓ Token generated successfully')
        config['apple_musickit'] = {**creds, 'enabled': True, 'skip': False}
    else:
        print('✗ Token generation failed')
        if not _CRYPTOGRAPHY_AVAILABLE:
            print("  Install the 'cryptography' package:  pip install cryptography")
        print('  MusicKit setup failed — iTunes Search API will be used instead.')
        config.setdefault('apple_musickit', {})['skip'] = True
        _save_config_if_agreed(config, config_path)
        return config

    _save_config_if_agreed(config, config_path)
    return config


def _save_config_if_agreed(config: dict, config_path: str):
    """Offer to persist updated config to disk (shared helper)."""
    try:
        answer = input('  Save these settings to config file? [Y/n] ').strip().lower()
    except (KeyboardInterrupt, EOFError):
        answer = 'n'
    if answer in ('', 'y', 'yes'):
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            print(f'  ✓ Saved to {config_path}')
        except Exception as e:
            print(f'  ✗ Could not save: {e}')


def _default_config_path() -> str:
    """Return a writable per-user default config path."""
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


def _prompt_library_paths(config: dict, config_path: str) -> dict:
    """Interactive first-run setup: ask for library root paths for each media type."""
    import platform

    def _pick_folder(prompt_label: str) -> Optional[str]:
        """Native folder picker (macOS) or terminal input (other platforms)."""
        if platform.system() == 'Darwin':
            import subprocess
            try:
                result = subprocess.run(
                    ['osascript', '-e',
                     f'POSIX path of (choose folder with prompt "{prompt_label}")'],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                pass
        # Terminal fallback
        print(f'\n  {prompt_label}')
        path = input('  Path (or leave blank to skip): ').strip().rstrip('/')
        return path if path else None

    print('\n╔══════════════════════════════════════════════════════════╗')
    print('║       Plex Metadata Generator — First Run Setup         ║')
    print('╠══════════════════════════════════════════════════════════╣')
    print('║  No configuration file found. Let\'s set one up.        ║')
    print('║  You can edit the saved file any time to make changes.  ║')
    print('╚══════════════════════════════════════════════════════════╝\n')

    for media_key, label in [
        ('movies', 'Movies'),
        ('tv', 'TV Shows'),
        ('music', 'Music'),
    ]:
        plural_key = f'{media_key}_library_roots'
        singular_key = f'{media_key}_library_root'

        # Already configured — skip
        if config.get(plural_key) or config.get(singular_key):
            continue

        try:
            answer = input(f'  Do you have a {label} library? [Y/n] ').strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if answer in ('n', 'no'):
            continue

        roots: List[str] = []
        while True:
            verb = 'Select' if not roots else 'Add another'
            path = _pick_folder(f'{verb} your {label} library root folder')
            if path and os.path.isdir(path):
                roots.append(path)
                print(f'  ✓ Added: {path}')
            elif path:
                print(f'  ✗ Directory not found: {path}')
            else:
                break  # blank / cancelled

            try:
                more = input(f'  Add another {label} volume? [y/N] ').strip().lower()
            except (KeyboardInterrupt, EOFError):
                break
            if more not in ('y', 'yes'):
                break

        if roots:
            config[plural_key] = roots

    # Plex connection
    if not config.get('plex', {}).get('url'):
        print('\n  Plex server settings (optional — needed for auto-refresh):')
        try:
            url = input('  Plex URL [http://localhost:32400]: ').strip() or 'http://localhost:32400'
            token = input('  Plex token (leave blank to skip): ').strip()
        except (KeyboardInterrupt, EOFError):
            url, token = 'http://localhost:32400', ''
        config.setdefault('plex', {})['url'] = url
        if token:
            config['plex']['token'] = token

    # API keys
    key_prompts = [
        ('tmdb',   'api_key', 'TMDB API key (movies)',    'https://www.themoviedb.org/settings/api'),
        ('tvdb',   'api_key', 'TVDB API key (TV shows)',  'https://thetvdb.com/api-information'),
        ('fanart_tv', 'api_key', 'FanArt.tv API key (artwork, optional)', 'https://fanart.tv/get-an-api-key/'),
    ]
    for section, field_name, label, url in key_prompts:
        existing = config.get(section, {}).get(field_name, '')
        if existing and not existing.startswith('YOUR_'):
            continue
        print(f'\n  {label}')
        print(f'  Get it free at: {url}')
        try:
            val = input('  Key (leave blank to skip): ').strip()
        except (KeyboardInterrupt, EOFError):
            val = ''
        if val:
            config.setdefault(section, {})[field_name] = val

    # Contact email for MusicBrainz
    if not config.get('musicbrainz_contact'):
        try:
            email = input('\n  Your email (used in MusicBrainz User-Agent, not shared publicly): ').strip()
        except (KeyboardInterrupt, EOFError):
            email = ''
        if email:
            config['musicbrainz_contact'] = email

    # Save
    try:
        answer = input(f'\n  Save configuration to {config_path}? [Y/n] ').strip().lower()
    except (KeyboardInterrupt, EOFError):
        answer = 'y'
    if answer in ('', 'y', 'yes'):
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            print(f'  ✓ Saved to {config_path}')
        except Exception as e:
            print(f'  ✗ Could not save config: {e}')

    return config


def load_config(config_file: str) -> Dict:
    """Load configuration from JSON file; run first-run setup if file is missing."""
    if not os.path.exists(config_file):
        logger.info(f"Config not found at {config_file} — running first-run setup")
        config = _prompt_library_paths({}, config_file)
        return config
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded configuration from {config_file}")
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file {config_file}: {e}")
        sys.exit(1)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Plex Metadata NFO Generator with TV + Music Support'
    )
    parser.add_argument(
        '--config',
        default=_default_config_path(),
        help='Configuration file path (default: OS-appropriate user config directory)'
    )
    parser.add_argument(
        '--media-type',
        default='all',
        choices=['tv', 'movies', 'music', 'all'],
        help='Which media type to process (default: all)'
    )
    parser.add_argument(
        '--item',
        help='Process only a specific show, movie, or artist'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing NFO files and artwork'
    )
    parser.add_argument(
        '--workers', type=int, default=1, metavar='N',
        help='Parallel workers for movie/TV processing (default: 1; use 4 for bulk runs)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    config = load_config(args.config)

    # Pre-flight: prompt for Apple MusicKit credentials if not already set
    config = prompt_apple_music_credentials(config, args.config)

    orchestrator = PlexMetadataOrchestrator(config)
    orchestrator.force = getattr(args, 'force', False)
    orchestrator.workers = max(1, getattr(args, 'workers', 1))
    orchestrator.run(args.media_type, args.item)
