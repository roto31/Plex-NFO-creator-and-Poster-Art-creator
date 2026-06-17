#!/usr/bin/env python3
"""
Plex Metadata NFO Generator with Tunarr, TVDb, and TMDb Integration
Generates NFO files and downloads artwork for TV shows and episodes
Can be run as a scheduled process via systemd or cron
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
from dataclasses import dataclass
from urllib.parse import quote
import xml.etree.ElementTree as ET
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/plex-metadata-generator.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ShowMetadata:
    """Container for complete show metadata"""
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
    genres: List[str] = None
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
    guest_stars: List[str] = None
    director: Optional[str] = None
    writer: Optional[str] = None


class TunarrMetadataProvider:
    """Extract metadata from Tunarr's SQLite database"""
    
    def __init__(self, tunarr_db_path: str = '/opt/tunarr/cache/tunarr.db'):
        self.db_path = tunarr_db_path
        self.conn = None
    
    def connect(self) -> bool:
        """Connect to Tunarr database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"Connected to Tunarr database: {self.db_path}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to Tunarr database: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def get_channel_programs(self, channel_number: int = None) -> List[Dict]:
        """
        Extract program/show metadata from Tunarr's program guide
        Can filter by channel number
        """
        try:
            cursor = self.conn.cursor()
            
            if channel_number:
                query = """
                    SELECT DISTINCT title, summary, duration, rating, channel_number
                    FROM programs
                    WHERE channel_number = ?
                    ORDER BY title
                """
                cursor.execute(query, (channel_number,))
            else:
                query = """
                    SELECT DISTINCT title, summary, duration, rating, channel_number
                    FROM programs
                    ORDER BY title
                """
                cursor.execute(query)
            
            results = cursor.fetchall()
            programs = [dict(row) for row in results]
            logger.info(f"Retrieved {len(programs)} programs from Tunarr")
            return programs
        except sqlite3.Error as e:
            logger.error(f"Failed to query Tunarr programs: {e}")
            return []
    
    def get_show_from_tunarr(self, show_title: str) -> Optional[Dict]:
        """
        Lookup a show in Tunarr's program guide
        Returns basic metadata and pointers to where full metadata should come from
        """
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT title, summary, duration, rating, channel_number
                FROM programs
                WHERE title LIKE ?
                LIMIT 1
            """
            cursor.execute(query, (f"%{show_title}%",))
            result = cursor.fetchone()
            
            if result:
                return dict(result)
            return None
        except sqlite3.Error as e:
            logger.error(f"Failed to lookup show '{show_title}' in Tunarr: {e}")
            return None


class TVDbProvider:
    """Fetch metadata from TheTVDB API (v4)"""
    
    BASE_URL = 'https://api4.thetvdb.com/v4'
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.bearer_token = None
        self.token_expiry = None
    
    def authenticate(self) -> bool:
        """Get bearer token for API access"""
        try:
            response = requests.post(
                f'{self.BASE_URL}/login',
                json={'apikey': self.api_key},
                timeout=10
            )
            response.raise_for_status()
            
            self.bearer_token = response.json()['data']['token']
            # Token valid for 1 week
            self.token_expiry = datetime.now() + timedelta(days=6)
            logger.info("Successfully authenticated with TVDb")
            return True
        except requests.RequestException as e:
            logger.error(f"TVDb authentication failed: {e}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Return authorization headers"""
        return {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json'
        }
    
    def search_show(self, title: str) -> List[Dict]:
        """Search for a show by title"""
        if not self.bearer_token:
            return []
        
        try:
            params = {'query': title}
            response = requests.get(
                f'{self.BASE_URL}/search',
                headers=self._get_headers(),
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            results = response.json().get('data', [])
            logger.debug(f"TVDb search for '{title}' returned {len(results)} results")
            return results
        except requests.RequestException as e:
            logger.error(f"TVDb search failed for '{title}': {e}")
            return []
    
    def get_show(self, tvdb_id: int) -> Optional[ShowMetadata]:
        """Fetch complete show metadata by TVDb ID"""
        if not self.bearer_token:
            return None
        
        try:
            response = requests.get(
                f'{self.BASE_URL}/series/{tvdb_id}/extended',
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            data = response.json()['data']
            
            # Extract metadata
            metadata = ShowMetadata(
                title=data.get('name', ''),
                year=data.get('firstAired', '').split('-')[0] if data.get('firstAired') else 0,
                plot=data.get('overview', ''),
                rating=float(data.get('score', 0) or 0),
                tvdb_id=tvdb_id,
                imdb_id=data.get('imdbId'),
                runtime=data.get('runtime', 45),
                status=data.get('status', {}).get('name', 'Continuing'),
                genres=data.get('genres', []),
            )
            
            # Get poster image
            images = data.get('artworks', [])
            for image in images:
                if image.get('type') == 1:  # Poster
                    metadata.poster_url = f"https://artworks.thetvdb.com{image.get('image')}"
                    break
            
            logger.info(f"Retrieved TVDb metadata for '{metadata.title}'")
            return metadata
        except requests.RequestException as e:
            logger.error(f"Failed to fetch TVDb show {tvdb_id}: {e}")
            return None
    
    def get_episodes(self, tvdb_id: int, season: int) -> List[EpisodeMetadata]:
        """Fetch episodes for a specific season"""
        if not self.bearer_token:
            return []
        
        try:
            response = requests.get(
                f'{self.BASE_URL}/series/{tvdb_id}/episodes/default',
                headers=self._get_headers(),
                params={'season': season},
                timeout=10
            )
            response.raise_for_status()
            
            episodes = []
            for ep_data in response.json().get('data', []):
                episode_num = ep_data.get('number')
                if episode_num is None:
                    continue
                
                episode = EpisodeMetadata(
                    title=ep_data.get('name', f'Episode {episode_num}'),
                    season=season,
                    episode=episode_num,
                    plot=ep_data.get('overview', ''),
                    air_date=ep_data.get('aired', ''),
                    rating=float(ep_data.get('score', 0) or 0),
                    director=ep_data.get('director'),
                    writer=ep_data.get('writer'),
                )
                episodes.append(episode)
            
            logger.info(f"Retrieved {len(episodes)} episodes for TVDb ID {tvdb_id}, season {season}")
            return episodes
        except requests.RequestException as e:
            logger.error(f"Failed to fetch TVDb episodes for {tvdb_id}: {e}")
            return []


class TMDbProvider:
    """Fetch metadata from The Movie Database (TMDb) API"""
    
    BASE_URL = 'https://api.themoviedb.org/3'
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def search_show(self, title: str) -> List[Dict]:
        """Search for a show by title"""
        try:
            params = {
                'api_key': self.api_key,
                'query': title
            }
            response = requests.get(
                f'{self.BASE_URL}/search/tv',
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            results = response.json().get('results', [])
            logger.debug(f"TMDb search for '{title}' returned {len(results)} results")
            return results
        except requests.RequestException as e:
            logger.error(f"TMDb search failed for '{title}': {e}")
            return []
    
    def get_show(self, tmdb_id: int) -> Optional[ShowMetadata]:
        """Fetch complete show metadata by TMDb ID"""
        try:
            params = {
                'api_key': self.api_key,
                'append_to_response': 'external_ids,images'
            }
            response = requests.get(
                f'{self.BASE_URL}/tv/{tmdb_id}',
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract metadata
            metadata = ShowMetadata(
                title=data.get('name', ''),
                year=data.get('first_air_date', '').split('-')[0] if data.get('first_air_date') else 0,
                plot=data.get('overview', ''),
                rating=float(data.get('vote_average', 0) or 0),
                tmdb_id=tmdb_id,
                runtime=data.get('episode_run_time', [45])[0] if data.get('episode_run_time') else 45,
                status=data.get('status', 'Continuing'),
                genres=[g['name'] for g in data.get('genres', [])],
            )
            
            # Get external IDs
            external_ids = data.get('external_ids', {})
            metadata.tvdb_id = external_ids.get('tvdb_id')
            metadata.imdb_id = external_ids.get('imdb_id')
            
            # Get poster image
            poster_path = data.get('poster_path')
            if poster_path:
                metadata.poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
            
            logger.info(f"Retrieved TMDb metadata for '{metadata.title}'")
            return metadata
        except requests.RequestException as e:
            logger.error(f"Failed to fetch TMDb show {tmdb_id}: {e}")
            return None
    
    def get_episodes(self, tmdb_id: int, season: int) -> List[EpisodeMetadata]:
        """Fetch episodes for a specific season"""
        try:
            params = {'api_key': self.api_key}
            response = requests.get(
                f'{self.BASE_URL}/tv/{tmdb_id}/season/{season}',
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            episodes = []
            for ep_data in response.json().get('episodes', []):
                episode = EpisodeMetadata(
                    title=ep_data.get('name', f"Episode {ep_data.get('episode_number')}"),
                    season=season,
                    episode=ep_data.get('episode_number'),
                    plot=ep_data.get('overview', ''),
                    air_date=ep_data.get('air_date', ''),
                    rating=float(ep_data.get('vote_average', 0) or 0),
                )
                episodes.append(episode)
            
            logger.info(f"Retrieved {len(episodes)} episodes for TMDb ID {tmdb_id}, season {season}")
            return episodes
        except requests.RequestException as e:
            logger.error(f"Failed to fetch TMDb episodes for {tmdb_id}: {e}")
            return []


class PlexNFOGenerator:
    """Generate Plex-compliant NFO files"""
    
    def generate_show_nfo(self, metadata: ShowMetadata) -> str:
        """Generate tvshow.nfo XML"""
        root = ET.Element('tvshow')
        
        # Basic info
        ET.SubElement(root, 'title').text = metadata.title
        ET.SubElement(root, 'originaltitle').text = metadata.title
        
        if metadata.year:
            ET.SubElement(root, 'year').text = str(metadata.year)
        
        ET.SubElement(root, 'plot').text = metadata.plot or ''
        ET.SubElement(root, 'rating').text = str(metadata.rating or 0)
        ET.SubElement(root, 'runtime').text = str(metadata.runtime)
        ET.SubElement(root, 'status').text = metadata.status
        
        # IDs
        if metadata.tvdb_id:
            ET.SubElement(root, 'tvdbid').text = str(metadata.tvdb_id)
        
        if metadata.tmdb_id:
            ET.SubElement(root, 'tmdbid').text = str(metadata.tmdb_id)
        
        if metadata.imdb_id:
            ET.SubElement(root, 'imdbid').text = metadata.imdb_id
        
        # Genres
        for genre in (metadata.genres or []):
            ET.SubElement(root, 'genre').text = genre
        
        # Poster
        if metadata.poster_url:
            poster_elem = ET.SubElement(root, 'poster')
            poster_elem.text = metadata.poster_url
        
        # Format XML with proper declaration
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


class MetadataDownloader:
    """Handle downloading and caching artwork"""
    
    def __init__(self, cache_dir: str = '/var/cache/plex-metadata'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def download_image(self, url: str, save_path: Path, 
                      filename: str, force: bool = False) -> Optional[Path]:
        """
        Download image and save to path
        Returns path to saved file or None on failure
        """
        if not url:
            return None
        
        target_path = save_path / filename
        
        # Skip if already exists and not forcing
        if target_path.exists() and not force:
            logger.debug(f"Using cached image: {target_path}")
            return target_path
        
        try:
            response = requests.get(url, timeout=15, stream=True)
            response.raise_for_status()
            
            # Verify content type is image
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"URL did not return an image: {url}")
                return None
            
            # Write to file
            target_path.write_bytes(response.content)
            logger.info(f"Downloaded: {target_path}")
            return target_path
        except requests.RequestException as e:
            logger.error(f"Failed to download {filename} from {url}: {e}")
            return None


class PlexMetadataOrchestrator:
    """Main orchestrator for metadata generation"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.library_root = Path(config.get('library_root', '/mnt/media/TV'))
        self.plex_url = config.get('plex_url', 'http://localhost:32400')
        self.plex_token = config.get('plex_token')
        self.library_key = config.get('library_key', '1')
        
        # Initialize providers
        tvdb_key = config.get('tvdb_api_key')
        tmdb_key = config.get('tmdb_api_key')
        
        self.tvdb = TVDbProvider(tvdb_key) if tvdb_key else None
        self.tmdb = TMDbProvider(tmdb_key) if tmdb_key else None
        self.tunarr = TunarrMetadataProvider(config.get('tunarr_db_path'))
        
        self.nfo_generator = PlexNFOGenerator()
        self.downloader = MetadataDownloader(config.get('cache_dir'))
        
        # Authenticate with TVDb
        if self.tvdb:
            self.tvdb.authenticate()
    
    def scan_library(self) -> Dict[str, Path]:
        """Scan library for shows and return mapping"""
        shows = {}
        
        if not self.library_root.exists():
            logger.error(f"Library root does not exist: {self.library_root}")
            return shows
        
        for show_dir in self.library_root.iterdir():
            if show_dir.is_dir():
                shows[show_dir.name] = show_dir
        
        logger.info(f"Found {len(shows)} shows in library")
        return shows
    
    def process_show(self, show_name: str, show_path: Path) -> bool:
        """
        Process a single show:
        1. Search metadata providers
        2. Generate NFO files
        3. Download artwork
        """
        logger.info(f"Processing show: {show_name}")
        
        # Try to find metadata
        metadata = None
        
        # Strategy 1: Search TVDb first (best for TV shows)
        if self.tvdb:
            tvdb_results = self.tvdb.search_show(show_name)
            if tvdb_results:
                # Use first result
                tvdb_id = tvdb_results[0].get('tvdb_id')
                metadata = self.tvdb.get_show(tvdb_id)
                logger.info(f"Found {show_name} on TVDb: ID {tvdb_id}")
        
        # Strategy 2: Try TMDb if TVDb didn't work
        if not metadata and self.tmdb:
            tmdb_results = self.tmdb.search_show(show_name)
            if tmdb_results:
                tmdb_id = tmdb_results[0].get('id')
                metadata = self.tmdb.get_show(tmdb_id)
                logger.info(f"Found {show_name} on TMDb: ID {tmdb_id}")
        
        # Strategy 3: Check Tunarr
        if not metadata:
            tunarr_data = self.tunarr.get_show_from_tunarr(show_name)
            if tunarr_data:
                logger.info(f"Found {show_name} in Tunarr metadata")
                # Create basic metadata from Tunarr
                metadata = ShowMetadata(
                    title=show_name,
                    year=0,
                    plot=tunarr_data.get('summary', ''),
                    rating=float(tunarr_data.get('rating', 0) or 0),
                    runtime=int(tunarr_data.get('duration', 45) or 45)
                )
        
        if not metadata:
            logger.warning(f"Could not find metadata for {show_name}")
            return False
        
        # Generate and write NFO
        nfo_content = self.nfo_generator.generate_show_nfo(metadata)
        nfo_path = show_path / 'tvshow.nfo'
        
        try:
            nfo_path.write_text(nfo_content, encoding='utf-8')
            logger.info(f"Wrote NFO: {nfo_path}")
        except IOError as e:
            logger.error(f"Failed to write NFO for {show_name}: {e}")
            return False
        
        # Download artwork
        if metadata.poster_url:
            self.downloader.download_image(
                metadata.poster_url,
                show_path,
                'poster.jpg'
            )
        
        # Process seasons and episodes
        if metadata.tvdb_id and self.tvdb:
            self._process_seasons(show_path, metadata.tvdb_id)
        elif metadata.tmdb_id and self.tmdb:
            self._process_seasons_tmdb(show_path, metadata.tmdb_id)
        
        return True
    
    def _process_seasons(self, show_path: Path, tvdb_id: int):
        """Process seasons and episodes for TVDb show"""
        # Scan for season folders
        for season_dir in show_path.iterdir():
            if not season_dir.is_dir():
                continue
            
            # Extract season number from folder name
            # Assumes format: "Season 1", "s01", "season1", etc.
            try:
                season_num = self._extract_season_number(season_dir.name)
                if season_num is None:
                    continue
            except Exception:
                continue
            
            logger.debug(f"Processing season {season_num}")
            
            # Fetch episodes from TVDb
            episodes = self.tvdb.get_episodes(tvdb_id, season_num)
            
            # Match video files to episodes
            video_files = list(season_dir.glob('*.mkv')) + \
                         list(season_dir.glob('*.mp4')) + \
                         list(season_dir.glob('*.avi'))
            
            # Sort video files to match episode order
            video_files.sort()
            
            for idx, video_file in enumerate(video_files):
                if idx < len(episodes):
                    episode_meta = episodes[idx]
                    nfo_content = self.nfo_generator.generate_episode_nfo(episode_meta)
                    nfo_path = video_file.with_suffix('.nfo')
                    
                    try:
                        nfo_path.write_text(nfo_content, encoding='utf-8')
                        logger.info(f"Wrote episode NFO: {nfo_path}")
                    except IOError as e:
                        logger.error(f"Failed to write episode NFO: {e}")
    
    def _process_seasons_tmdb(self, show_path: Path, tmdb_id: int):
        """Process seasons and episodes for TMDb show"""
        for season_dir in show_path.iterdir():
            if not season_dir.is_dir():
                continue
            
            try:
                season_num = self._extract_season_number(season_dir.name)
                if season_num is None:
                    continue
            except Exception:
                continue
            
            logger.debug(f"Processing season {season_num} (TMDb)")
            
            episodes = self.tmdb.get_episodes(tmdb_id, season_num)
            
            video_files = list(season_dir.glob('*.mkv')) + \
                         list(season_dir.glob('*.mp4')) + \
                         list(season_dir.glob('*.avi'))
            
            video_files.sort()
            
            for idx, video_file in enumerate(video_files):
                if idx < len(episodes):
                    episode_meta = episodes[idx]
                    nfo_content = self.nfo_generator.generate_episode_nfo(episode_meta)
                    nfo_path = video_file.with_suffix('.nfo')
                    
                    try:
                        nfo_path.write_text(nfo_content, encoding='utf-8')
                        logger.info(f"Wrote episode NFO: {nfo_path}")
                    except IOError as e:
                        logger.error(f"Failed to write episode NFO: {e}")
    
    @staticmethod
    def _extract_season_number(folder_name: str) -> Optional[int]:
        """Extract season number from folder name"""
        import re
        
        # Try patterns: "Season 1", "S01", "season1", etc.
        patterns = [
            r'[Ss]eason\s*(\d+)',
            r'[Ss](\d{2})',
            r'[Ss]eason\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, folder_name)
            if match:
                return int(match.group(1))
        
        return None
    
    def refresh_plex_library(self) -> bool:
        """Trigger Plex library refresh"""
        if not self.plex_token:
            logger.warning("Plex token not configured, skipping library refresh")
            return False
        
        try:
            headers = {'X-Plex-Token': self.plex_token}
            response = requests.post(
                f'{self.plex_url}/library/sections/{self.library_key}/refresh',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info("Plex library refresh triggered successfully")
                return True
            else:
                logger.warning(f"Plex refresh returned status {response.status_code}")
                return False
        except requests.RequestException as e:
            logger.error(f"Failed to trigger Plex refresh: {e}")
            return False
    
    def run(self, specific_show: str = None):
        """
        Main execution method
        Processes all shows or a specific show if provided
        """
        try:
            if self.tunarr.connect():
                shows = self.scan_library()
                
                if specific_show:
                    # Process only specified show
                    show_path = self.library_root / specific_show
                    if show_path.exists():
                        self.process_show(specific_show, show_path)
                else:
                    # Process all shows
                    for show_name, show_path in shows.items():
                        self.process_show(show_name, show_path)
                        time.sleep(1)  # Rate limiting
                
                self.tunarr.disconnect()
                
                # Refresh Plex library
                self.refresh_plex_library()
                
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
        description='Plex Metadata NFO Generator with Tunarr/TVDb/TMDb integration'
    )
    parser.add_argument(
        '--config',
        default='/etc/plex-metadata-generator.conf',
        help='Configuration file path'
    )
    parser.add_argument(
        '--show',
        help='Process only a specific show'
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
    orchestrator.run(args.show)
