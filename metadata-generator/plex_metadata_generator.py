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
        if not self.bearer_token:
            return []
        try:
            resp = requests.get(f'{self.BASE_URL}/search', headers=self._headers(),
                                params={'query': title}, timeout=10)
            resp.raise_for_status()
            return resp.json().get('data', [])
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
                rating=float(data.get('score', 0) or 0),
                tvdb_id=tvdb_id,
                imdb_id=data.get('imdbId'),
                runtime=data.get('runtime', 45),
                status=data.get('status', {}).get('name', 'Continuing'),
                genres=data.get('genres', []),
            )
            # Poster
            for image in data.get('artworks', []):
                if image.get('type') == 1:
                    meta.poster_url = f"https://artworks.thetvdb.com{image['image']}"
                    break
            # Banner
            for image in data.get('artworks', []):
                if image.get('type') == 2:
                    meta.banner_url = f"https://artworks.thetvdb.com{image['image']}"
                    break
            # Fanart/background
            for image in data.get('artworks', []):
                if image.get('type') == 3:
                    meta.fanart_url = f"https://artworks.thetvdb.com{image['image']}"
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
        try:
            return self._get('/search/tv', query=title).get('results', [])
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
        """Return TMDB ID for best match, or None. Retries without year if needed."""
        try:
            kwargs = {'query': title}
            if year:
                kwargs['year'] = year
            results = self._get('/search/movie', **kwargs).get('results', [])
            if not results and year:
                # Retry without year
                results = self._get('/search/movie', query=title).get('results', [])
            return results[0]['id'] if results else None
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

    def __init__(self, cache_dir: str = '/var/cache/plex-metadata'):
        self.cache_dir = Path(cache_dir)
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

    def __init__(self, config: Dict, force: bool = False):
        self.config = config
        self.force = force

        # Library roots — support both old flat key and new split keys
        self.tv_library_root = Path(
            config.get('tv_library_root') or config.get('library_root', '/mnt/media/TV')
        )
        self.movies_library_root = (
            Path(config['movies_library_root']) if config.get('movies_library_root') else None
        )

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
        self.dl = MetadataDownloader(config.get('cache_dir', '/var/cache/plex-metadata'))

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
        if not self.movies_library_root:
            logger.warning("movies_library_root not configured — skipping movie processing")
            return
        if not self.movies_library_root.exists():
            logger.error(f"Movie library root does not exist: {self.movies_library_root}")
            return

        folders = sorted(self.movies_library_root.iterdir())
        for folder in folders:
            if not folder.is_dir() or folder.name.startswith('.'):
                continue
            if specific_movie and folder.name != specific_movie:
                continue
            if is_multipart(folder.name):
                logger.info(f"⏭ {folder.name} — multi-part, skipping")
                continue
            self._process_one_movie(folder)
            time.sleep(0.5)  # gentle rate limiting

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
            # Need to search — extract year from folder name
            year_match = re.search(r'\((\d{4})\)', folder.name)
            year = int(year_match.group(1)) if year_match else None
            title = re.sub(r'\s*\(\d{4}\)\s*$', '', folder.name).strip()
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

        if need_poster and poster_url:
            if self.dl.download_image(poster_url, folder / 'poster.jpg'):
                # Copy to folder.jpg (Plex alternate name)
                shutil.copy2(folder / 'poster.jpg', folder / 'folder.jpg')
                logger.info(f"  ✓ Copied poster.jpg → folder.jpg")
            elif not poster_url:
                logger.warning(f"  ⚠ No poster source found for {folder.name}")
        elif 'folder.jpg' in missing_art and (folder / 'poster.jpg').exists():
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
        if not self.tv_library_root.exists():
            logger.error(f"TV library root does not exist: {self.tv_library_root}")
            return

        for show_dir in sorted(self.tv_library_root.iterdir()):
            if not show_dir.is_dir() or show_dir.name.startswith('.'):
                continue
            if specific_show and show_dir.name != specific_show:
                continue
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

            # Download TVDB/TMDB artwork
            if 'poster.jpg' in missing_art and meta.poster_url:
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
        # TVDb first
        if self.tvdb:
            results = self.tvdb.search_show(show_name)
            if results:
                tvdb_id = results[0].get('tvdb_id')
                if tvdb_id:
                    return self.tvdb.get_show(tvdb_id)
        # TMDb fallback
        if self.tmdb_tv:
            results = self.tmdb_tv.search_show(show_name)
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

            # Download season poster from TVDB if missing
            if needs_season_poster and show_meta and show_meta.tvdb_id and self.tvdb:
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
                if artwork.get('season') == season_num:
                    url = f"https://artworks.thetvdb.com{artwork['image']}"
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

def load_config(config_file: str = '/etc/plex-metadata-generator.conf') -> Dict:
    try:
        with open(config_file) as f:
            # Strip // comments (not valid JSON but common in conf files)
            text = re.sub(r'//[^\n]*', '', f.read())
            return json.loads(text)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration: {e}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Plex Metadata NFO Generator — TV shows and Movies'
    )
    parser.add_argument('--config', default='/etc/plex-metadata-generator.conf',
                        help='Configuration file path')
    parser.add_argument('--media-type', choices=['tv', 'movies', 'all'], default='tv',
                        help='Which library to process (default: tv)')
    parser.add_argument('--show', help='Process only this TV show folder name')
    parser.add_argument('--movie', help='Process only this movie folder name')
    parser.add_argument('--force', action='store_true',
                        help='Overwrite existing NFO files and artwork')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    config = load_config(args.config)
    orchestrator = PlexMetadataOrchestrator(config, force=args.force)

    specific = args.show or args.movie
    orchestrator.run(media_type=args.media_type, specific_item=specific)
