#!/usr/bin/env python3
"""
Plex Metadata NFO Generator with Multi-Media Support
Supports: TV Shows + Music (Albums, Artists, Tracks)
Integrates with: Tunarr, TVDb, TMDb, MusicBrainz, Spotify APIs
"""

import os
import sys
import json
import logging
import requests
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
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
    mbid: Optional[str] = None  # MusicBrainz ID
    spotify_id: Optional[str] = None
    cover_url: Optional[str] = None
    release_date: Optional[str] = None
    track_count: int = 0
    label: Optional[str] = None


@dataclass
class ArtistMetadata:
    """Container for music artist metadata"""
    name: str
    mbid: Optional[str] = None
    spotify_id: Optional[str] = None
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
    
    def __init__(self, user_agent: str = 'PlexMetadataGenerator/1.0'):
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
    
    def search_release(self, album_title: str, artist: str) -> List[Dict]:
        """Search for an album release"""
        try:
            query = f'release:"{album_title}" artist:"{artist}"'
            params = {
                'query': query,
                'fmt': 'json',
                'limit': 10
            }
            
            response = self.session.get(
                f'{self.BASE_URL}/release',
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
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
            
            response = self.session.get(
                f'{self.BASE_URL}/release/{mbid}',
                params=params,
                timeout=10
            )
            response.raise_for_status()
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
            
            response = self.session.get(
                f'{self.BASE_URL}/artist',
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
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


class SpotifyProvider:
    """Fetch metadata from Spotify API"""
    
    BASE_URL = 'https://api.spotify.com/v1'
    AUTH_URL = 'https://accounts.spotify.com/api/token'
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expiry = None
    
    def authenticate(self) -> bool:
        """Get access token using Client Credentials flow"""
        try:
            auth = (self.client_id, self.client_secret)
            data = {'grant_type': 'client_credentials'}
            
            response = requests.post(self.AUTH_URL, auth=auth, data=data, timeout=10)
            response.raise_for_status()
            
            self.access_token = response.json()['access_token']
            self.token_expiry = datetime.now() + timedelta(hours=1)
            logger.info("Successfully authenticated with Spotify")
            return True
        except requests.RequestException as e:
            logger.error(f"Spotify authentication failed: {e}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Return authorization headers"""
        return {'Authorization': f'Bearer {self.access_token}'}
    
    def search_album(self, album_title: str, artist: str) -> List[Dict]:
        """Search for an album"""
        if not self.access_token:
            return []
        
        try:
            query = f'album:{album_title} artist:{artist}'
            params = {'q': query, 'type': 'album', 'limit': 10}
            
            response = requests.get(
                f'{self.BASE_URL}/search',
                headers=self._get_headers(),
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            results = response.json().get('albums', {}).get('items', [])
            logger.debug(f"Spotify search for '{album_title}' returned {len(results)} results")
            return results
        except requests.RequestException as e:
            logger.error(f"Spotify album search failed: {e}")
            return []
    
    def get_album(self, album_id: str) -> Optional[AlbumMetadata]:
        """Fetch complete album metadata by Spotify ID"""
        if not self.access_token:
            return None
        
        try:
            response = requests.get(
                f'{self.BASE_URL}/albums/{album_id}',
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract metadata
            artists = [a['name'] for a in data.get('artists', [])]
            artist = ', '.join(artists) or 'Unknown Artist'
            
            # Parse year from release date
            release_date = data.get('release_date', '')
            year = int(release_date.split('-')[0]) if release_date else 0
            
            # Get cover art
            cover_url = None
            images = data.get('images', [])
            if images:
                # Prefer larger image
                images_sorted = sorted(images, key=lambda x: x.get('width', 0), reverse=True)
                cover_url = images_sorted[0]['url']
            
            metadata = AlbumMetadata(
                title=data.get('name', ''),
                artist=artist,
                year=year,
                rating=0.0,  # Spotify doesn't have ratings, could use popularity (0-100)
                spotify_id=album_id,
                cover_url=cover_url,
                release_date=release_date,
                track_count=data.get('total_tracks', 0),
                genres=data.get('genres', [])
            )
            
            logger.info(f"Retrieved Spotify metadata for '{metadata.title}' by '{metadata.artist}'")
            return metadata
        except requests.RequestException as e:
            logger.error(f"Failed to fetch Spotify album {album_id}: {e}")
            return None
    
    def search_artist(self, artist_name: str) -> List[Dict]:
        """Search for an artist"""
        if not self.access_token:
            return []
        
        try:
            params = {'q': artist_name, 'type': 'artist', 'limit': 10}
            
            response = requests.get(
                f'{self.BASE_URL}/search',
                headers=self._get_headers(),
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            results = response.json().get('artists', {}).get('items', [])
            logger.debug(f"Spotify artist search for '{artist_name}' returned {len(results)} results")
            return results
        except requests.RequestException as e:
            logger.error(f"Spotify artist search failed: {e}")
            return []


class PlexNFOGenerator:
    """Generate Plex-compliant NFO files for all media types"""
    
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
        
        return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + \
               ET.tostring(root, encoding='unicode')
    
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
        
        return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + \
               ET.tostring(root, encoding='unicode')
    
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
        
        # Spotify ID
        if metadata.spotify_id:
            ET.SubElement(root, 'spotifyid').text = metadata.spotify_id
        
        # Genres
        for genre in (metadata.genres or []):
            ET.SubElement(root, 'genre').text = genre
        
        # Cover art
        if metadata.cover_url:
            ET.SubElement(root, 'cover').text = metadata.cover_url
        
        return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + \
               ET.tostring(root, encoding='unicode')
    
    def generate_artist_nfo(self, metadata: ArtistMetadata) -> str:
        """Generate artist.nfo XML for music"""
        root = ET.Element('artist')
        
        ET.SubElement(root, 'name').text = metadata.name
        ET.SubElement(root, 'plot').text = metadata.bio or f'Music artist: {metadata.name}'
        
        if metadata.mbid:
            ET.SubElement(root, 'mbid').text = metadata.mbid
        
        if metadata.spotify_id:
            ET.SubElement(root, 'spotifyid').text = metadata.spotify_id
        
        for genre in (metadata.genres or []):
            ET.SubElement(root, 'genre').text = genre
        
        for member in (metadata.members or []):
            ET.SubElement(root, 'member').text = member
        
        if metadata.image_url:
            ET.SubElement(root, 'image').text = metadata.image_url
        
        return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + \
               ET.tostring(root, encoding='unicode')
    
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
        
        return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + \
               ET.tostring(root, encoding='unicode')


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
        
        # Music providers — priority: local MB (PostgreSQL) → local MB (JSON) → Spotify → REST API
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

        spotify_config = config.get('spotify', {})
        self.spotify = None
        if spotify_config.get('client_id') and spotify_config.get('client_secret'):
            self.spotify = SpotifyProvider(
                spotify_config['client_id'],
                spotify_config['client_secret']
            )
            self.spotify.authenticate()
        
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
    
    def process_music_library(self):
        """Process music library (artists and albums)"""
        logger.info("Processing music library")
        
        if not self.music_library_root.exists():
            logger.error(f"Music library root does not exist: {self.music_library_root}")
            return
        
        # Structure: Artist / Album / Tracks
        for artist_dir in self.music_library_root.iterdir():
            if artist_dir.is_dir():
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
        
        # Search for artist metadata — priority: local MB DB → local MB JSON → Spotify → MB REST API
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

        # 2. Local MusicBrainz JSON dump (no PostgreSQL needed)
        if not artist_metadata and self.mb_json and self.mb_json.available:
            results = self.mb_json.search_artist(artist_name)
            if results:
                artist_metadata = ArtistMetadata(
                    name=results[0]['name'],
                    mbid=results[0]['id'],
                )
                logger.info(f"Found artist '{artist_name}' in local MusicBrainz JSON dump")

        # 3. Spotify (richer images and genres)
        if not artist_metadata and self.spotify:
            results = self.spotify.search_artist(artist_name)
            if results:
                artist_id = results[0]['id']
                artist_metadata = ArtistMetadata(
                    name=results[0]['name'],
                    spotify_id=artist_id,
                    genres=results[0].get('genres', []),
                    image_url=results[0].get('images', [{}])[0].get('url') if results[0].get('images') else None,
                )
                logger.info(f"Found artist '{artist_name}' on Spotify")

        # 3. MusicBrainz REST API (fallback, rate-limited)
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
        
        # Download artist image if available
        if artist_metadata.image_url:
            self.downloader.download_image(
                artist_metadata.image_url,
                artist_path,
                'artist.jpg'
            )
        
        # Process albums in this artist directory
        for album_dir in artist_path.iterdir():
            if album_dir.is_dir() and not album_dir.name.startswith('.'):
                self._process_music_album(album_dir, artist_name, artist_metadata)
    
    def _process_music_album(self, album_path: Path, artist_name: str, artist_metadata: ArtistMetadata):
        """Process album directory with tracks"""
        album_name = album_path.name
        logger.info(f"Processing album: {album_name} by {artist_name}")
        
        # Search for album metadata — priority: local MB (PG) → local MB (JSON) → Spotify → REST
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

        # 3. Spotify (has cover art URLs)
        if not album_metadata and self.spotify:
            results = self.spotify.search_album(album_name, artist_name)
            if results:
                album_id = results[0]['id']
                album_metadata = self.spotify.get_album(album_id)
                if album_metadata:
                    logger.info(f"Found album '{album_name}' on Spotify")

        # 3. MusicBrainz REST API
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
        
        # Download cover art
        if album_metadata.cover_url:
            self.downloader.download_image(
                album_metadata.cover_url,
                album_path,
                'folder.jpg'
            )
        
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
                # Delegate to base script's process_movie_library
                from plex_metadata_generator import PlexMetadataOrchestrator as BaseOrchestrator
                base = BaseOrchestrator(self.config, force=self.force)
                base.process_movie_library(specific_movie=specific_item)

            if media_type in ('music', 'all'):
                logger.info("Starting music metadata generation")
                self.process_music_library()
                self.refresh_plex_library(self.music_library_key)

            logger.info("Metadata generation complete")
        except Exception as e:
            logger.error(f"Fatal error during metadata generation: {e}", exc_info=True)
            raise


def load_config(config_file: str = '/etc/plex-metadata-generator.conf') -> Dict:
    """Load configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded configuration from {config_file}")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration: {e}")
        sys.exit(1)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Plex Metadata NFO Generator with TV + Music Support'
    )
    parser.add_argument(
        '--config',
        default='/etc/plex-metadata-generator.conf',
        help='Configuration file path'
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
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    config = load_config(args.config)
    orchestrator = PlexMetadataOrchestrator(config)
    orchestrator.force = getattr(args, 'force', False)
    orchestrator.run(args.media_type, args.item)
