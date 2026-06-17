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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/plex-metadata-generator.log'),
        logging.StreamHandler(sys.stdout)
    ]
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
                label = data['label-info'][0].get('label', {}).get('name')
            
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
        
        # Music providers
        mbid_key = config.get('musicbrainz_api_key')
        self.musicbrainz = None
        if mbid_key:
            self.musicbrainz = MusicBrainzProvider(user_agent=f"PlexMetadataGenerator/1.0 (+{config.get('musicbrainz_contact', 'contact@example.com')})")
        
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
        
        # Search for artist metadata
        artist_metadata = None
        
        if self.spotify:
            results = self.spotify.search_artist(artist_name)
            if results:
                artist_id = results[0]['id']
                # Get additional artist info
                artist_metadata = ArtistMetadata(
                    name=results[0]['name'],
                    spotify_id=artist_id,
                    genres=results[0].get('genres', []),
                    image_url=results[0].get('images', [{}])[0].get('url') if results[0].get('images') else None
                )
                logger.info(f"Found artist '{artist_name}' on Spotify")
        
        if not artist_metadata and self.musicbrainz:
            results = self.musicbrainz.search_artist(artist_name)
            if results:
                artist_metadata = ArtistMetadata(
                    name=results[0]['name'],
                    mbid=results[0]['id']
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
        
        # Search for album metadata
        album_metadata = None
        
        # Try Spotify first
        if self.spotify:
            results = self.spotify.search_album(album_name, artist_name)
            if results:
                album_id = results[0]['id']
                album_metadata = self.spotify.get_album(album_id)
                if album_metadata:
                    logger.info(f"Found album '{album_name}' on Spotify")
        
        # Fallback to MusicBrainz
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
                if self.tunarr.connect():
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
