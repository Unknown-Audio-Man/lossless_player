import os
import logging
import json
import time
import re
from pathlib import Path
from mutagen import File as MutagenFile
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3

from config import MOUNT_POINT, MusicLibraryCache, LIBRARY_CACHE
from network import NetworkManager

logger = logging.getLogger(__name__)

class MusicLibrary:
    """Handles indexing and searching the music collection"""
    
    def __init__(self):
        self.library = {}
        self.albums = {}
        self.artists = {}
        self.indexed_time = 0
        self.load_cache()
    
    def load_cache(self):
        """Load music library from cache"""
        cache_data = MusicLibraryCache.load()
        if cache_data:
            self.library = cache_data.get('tracks', {})
            self.albums = cache_data.get('albums', {})
            self.artists = cache_data.get('artists', {})
            self.indexed_time = cache_data.get('indexed_time', 0)
            logger.info(f"Loaded music library cache with {len(self.albums)} albums")
            return True
        return False
    
    def save_cache(self):
        """Save music library to cache"""
        cache_data = {
            'tracks': self.library,
            'albums': self.albums,
            'artists': self.artists,
            'indexed_time': self.indexed_time
        }
        MusicLibraryCache.save(cache_data)
        logger.info(f"Saved music library cache with {len(self.albums)} albums")
    
    def index_library(self, force=False):
        """Index all music files on the server"""
        # Ensure server is mounted
        if not NetworkManager.mount_server():
            logger.error("Failed to mount music server, cannot index library")
            return False
        
        # Skip indexing if already done within the last 24 hours unless forced
        if not force and self.indexed_time > time.time() - 86400 and self.albums:
            logger.info("Using cached library index (less than 24 hours old)")
            return True
        
        logger.info("Starting music library indexing...")
        start_time = time.time()
        
        # Reset library
        self.library = {}
        self.albums = {}
        self.artists = {}
        
        supported_extensions = ('.flac', '.mp3', '.wav', '.aac', '.m4a', '.ogg', '.alac')
        
        # Walk through all files in the mounted directory
        for root, _, files in os.walk(MOUNT_POINT):
            for file in files:
                # Skip macOS metadata files (._filename)
                if file.startswith('._'):
                    continue
                    
                if file.lower().endswith(supported_extensions):
                    try:
                        file_path = os.path.join(root, file)
                        self._process_audio_file(file_path)
                    except Exception as e:
                        logger.error(f"Error processing file {file}: {e}")
        
        # Organize albums and artists
        self._organize_library()
        
        # Update indexed time and save cache
        self.indexed_time = int(time.time())
        self.save_cache()
        
        duration = time.time() - start_time
        logger.info(f"Indexed {len(self.library)} tracks in {len(self.albums)} albums ({duration:.2f} seconds)")
        return True
    
    def _process_audio_file(self, file_path):
        """Process a single audio file and extract metadata"""
        try:
            # Skip macOS hidden files and system files
            filename = os.path.basename(file_path)
            if filename.startswith('.') or filename.startswith('._'):
                return
                
            audio = MutagenFile(file_path)
            
            if audio is None:
                return
                
            # Extract basic metadata
            track_info = {
                'path': file_path,
                'filename': os.path.basename(file_path),
                'size': os.path.getsize(file_path),
                'album': '',
                'artist': '',
                'title': '',
                'track_number': 0,
                'duration': 0
            }
            
            # Extract metadata based on file type
            if isinstance(audio, FLAC):
                if 'album' in audio:
                    track_info['album'] = audio['album'][0]
                if 'artist' in audio:
                    track_info['artist'] = audio['artist'][0]
                if 'title' in audio:
                    track_info['title'] = audio['title'][0]
                if 'tracknumber' in audio:
                    try:
                        track_info['track_number'] = int(audio['tracknumber'][0].split('/')[0])
                    except (ValueError, IndexError):
                        pass
                track_info['duration'] = int(audio.info.length)
                
            elif isinstance(audio, MP3):
                # Use EasyID3 for MP3 tags
                try:
                    id3 = EasyID3(file_path)
                    if 'album' in id3:
                        track_info['album'] = id3['album'][0]
                    if 'artist' in id3:
                        track_info['artist'] = id3['artist'][0]
                    if 'title' in id3:
                        track_info['title'] = id3['title'][0]
                    if 'tracknumber' in id3:
                        try:
                            track_info['track_number'] = int(id3['tracknumber'][0].split('/')[0])
                        except (ValueError, IndexError):
                            pass
                except:
                    # Fallback to filename for title if ID3 fails
                    track_info['title'] = os.path.splitext(track_info['filename'])[0]
                
                track_info['duration'] = int(audio.info.length)
            
            else:
                # Generic audio file handling
                track_info['title'] = os.path.splitext(track_info['filename'])[0]
                if hasattr(audio.info, 'length'):
                    track_info['duration'] = int(audio.info.length)
            
            # Use file structure for album/artist if tags are missing
            if not track_info['album'] or not track_info['artist']:
                parts = file_path.replace(str(MOUNT_POINT), '').split(os.sep)
                if len(parts) >= 3:  # Assuming /Artist/Album/Track.flac structure
                    if not track_info['artist']:
                        track_info['artist'] = parts[-3]
                    if not track_info['album']:
                        track_info['album'] = parts[-2]
            
            # Add to library
            track_id = str(hash(file_path))
            self.library[track_id] = track_info
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
    
    def _organize_library(self):
        """Organize tracks into albums and artists"""
        for track_id, track in self.library.items():
            album_key = f"{track['artist']} - {track['album']}".lower()
            
            # Add to albums dictionary
            if album_key not in self.albums:
                self.albums[album_key] = {
                    'name': track['album'],
                    'artist': track['artist'],
                    'tracks': [],
                    'track_count': 0
                }
            
            self.albums[album_key]['tracks'].append(track_id)
            self.albums[album_key]['track_count'] += 1
            
            # Add to artists dictionary
            artist_key = track['artist'].lower()
            if artist_key not in self.artists:
                self.artists[artist_key] = {
                    'name': track['artist'],
                    'albums': set(),
                    'tracks': []
                }
            
            self.artists[artist_key]['albums'].add(album_key)
            self.artists[artist_key]['tracks'].append(track_id)
        
        # Sort album tracks by track number
        for album in self.albums.values():
            album['tracks'].sort(key=lambda track_id: self.library[track_id]['track_number'])
    
    def search_album(self, query):
        """Search for albums matching query"""
        if not self.albums:
            if not self.index_library():
                return []
        
        query = query.lower()
        results = []
        
        for album_key, album in self.albums.items():
            # Search in album name and artist name
            if query in album_key or query in album['name'].lower() or query in album['artist'].lower():
                results.append({
                    'key': album_key,
                    'name': album['name'],
                    'artist': album['artist'],
                    'track_count': album['track_count']
                })
        
        # Sort results by relevance (exact matches first)
        results.sort(key=lambda x: (
            0 if x['name'].lower() == query else 
            1 if query in x['name'].lower() else 
            2
        ))
        
        return results
    
    def get_album_tracks(self, album_key):
        """Get list of tracks for an album"""
        if album_key not in self.albums:
            return []
        
        album = self.albums[album_key]
        tracks = []
        
        for track_id in album['tracks']:
            if track_id in self.library:
                tracks.append(self.library[track_id])
        
        return sorted(tracks, key=lambda t: t['track_number'])
    
    def get_random_album(self):
        """Get a random album"""
        import random
        if not self.albums:
            if not self.index_library():
                return None
                
        album_key = random.choice(list(self.albums.keys()))
        return {
            'key': album_key,
            'name': self.albums[album_key]['name'],
            'artist': self.albums[album_key]['artist'],
            'track_count': self.albums[album_key]['track_count']
        }
