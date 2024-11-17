import os
import logging
import vlc
import json
import hashlib
import requests
import threading
import argparse
from pathlib import Path
from datetime import datetime, time
from dotenv import load_dotenv
from plexapi.server import PlexServer
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TimeBasedPlaylist:
    def __init__(self, name, start_hour):
        self.name = name
        self.start_hour = start_hour

class PlexPlaylistPlayer:
    def __init__(self, force_time_slot=None):
        # Load environment variables
        load_dotenv()
        
        # Plex server configuration
        self.plex_url = os.getenv('PLEX_SERVER_URL')
        self.plex_token = os.getenv('PLEX_TOKEN')
        
        # Configure time-based playlists
        self.playlists = {
            'morning': TimeBasedPlaylist(os.getenv('MORNING_PLAYLIST'), int(os.getenv('MORNING_START', '6'))),
            'afternoon': TimeBasedPlaylist(os.getenv('AFTERNOON_PLAYLIST'), int(os.getenv('AFTERNOON_START', '14'))),
            'evening': TimeBasedPlaylist(os.getenv('EVENING_PLAYLIST'), int(os.getenv('EVENING_START', '19')))
        }
        
        self.force_time_slot = force_time_slot
        
        # Setup cache directory
        self.cache_dir = Path('cache')
        self.cache_dir.mkdir(exist_ok=True)
        self.playlist_cache_file = self.cache_dir / 'playlist_cache.json'
        self.media_cache_dir = self.cache_dir / 'media'
        self.media_cache_dir.mkdir(exist_ok=True)
        
        # Download configuration
        self.max_concurrent_downloads = 3
        self.download_progress = {}
        self.download_lock = threading.Lock()
        
        # Validate configuration
        if not all([self.plex_url, self.plex_token] + [p.name for p in self.playlists.values()]):
            raise ValueError("Missing Plex configuration. Check your .env file.")
        
        # Initialize Plex server connection
        try:
            self.plex_server = PlexServer(self.plex_url, self.plex_token)
            logger.info(f"Connected to Plex server: {self.plex_server.friendlyName}")
        except Exception as e:
            logger.error(f"Failed to connect to Plex server: {e}")
            raise
        
        # VLC instance for playback
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()

    def get_current_playlist(self):
        """Determine which playlist to play based on current time or forced time slot."""
        if self.force_time_slot:
            if self.force_time_slot in self.playlists:
                logger.info(f"Using forced time slot: {self.force_time_slot}")
                return self.playlists[self.force_time_slot].name
            else:
                raise ValueError(f"Invalid time slot: {self.force_time_slot}. Must be one of: {', '.join(self.playlists.keys())}")
        
        current_hour = datetime.now().hour
        
        # Sort playlists by start hour in reverse to find the latest applicable playlist
        sorted_playlists = sorted(self.playlists.values(), key=lambda x: x.start_hour, reverse=True)
        
        for playlist in sorted_playlists:
            if current_hour >= playlist.start_hour:
                logger.info(f"Current time: {current_hour}:00, selecting playlist: {playlist.name}")
                return playlist.name
        
        # If no playlist matches, return morning playlist
        return self.playlists['morning'].name

    def get_safe_filename(self, title, media_id):
        """Generate a safe filename from the title and media ID."""
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        return f"{safe_title}_{media_id}"

    def get_cached_file_path(self, item):
        """Get the path where a media file should be cached."""
        safe_name = self.get_safe_filename(item.title, item.ratingKey)
        return self.media_cache_dir / f"{safe_name}.mp4"

    def download_media_file(self, item, stream_url):
        """Download a single media file to cache."""
        file_path = self.get_cached_file_path(item)
        
        if file_path.exists():
            logger.info(f"File already cached: {item.title}")
            return file_path
        
        temp_path = file_path.with_suffix('.temp')
        
        try:
            response = requests.get(stream_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024  # 1 KB
            downloaded = 0
            
            with open(temp_path, 'wb') as f:
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    f.write(data)
                    
                    # Update progress
                    with self.download_lock:
                        self.download_progress[item.title] = (downloaded, total_size)
                        
                    # Log progress every 5%
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        if percent % 5 < (block_size / total_size * 100):
                            logger.info(f"Downloading {item.title}: {percent:.1f}%")
            
            # Rename temp file to final file
            temp_path.rename(file_path)
            logger.info(f"Download completed: {item.title}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error downloading {item.title}: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise
    
    def download_all_media(self, playlist_items):
        """Download all media files in parallel."""
        logger.info("Starting media downloads...")
        
        with ThreadPoolExecutor(max_workers=self.max_concurrent_downloads) as executor:
            future_to_item = {
                executor.submit(self.download_media_file, item, item.getStreamURL()): item
                for item in playlist_items
            }
            
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Failed to download {item.title}: {e}")
    
    def get_playlist_hash(self, playlist):
        """Generate a hash of the playlist contents for comparison."""
        playlist_data = [
            {
                'title': item.title,
                'duration': item.duration,
                'rating_key': item.ratingKey,
                'updated_at': str(item.updatedAt) if hasattr(item, 'updatedAt') else None
            }
            for item in playlist.items()
        ]
        return hashlib.md5(json.dumps(playlist_data, sort_keys=True).encode()).hexdigest()
    
    def load_cached_playlist(self, playlist_name):
        """Load the cached playlist if it exists."""
        cache_file = self.cache_dir / f"playlist_cache_{playlist_name}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading cached playlist: {e}")
                return None
        return None
    
    def save_playlist_cache(self, playlist_name, playlist_data):
        """Save playlist data to cache."""
        try:
            cache_file = self.cache_dir / f"playlist_cache_{playlist_name}.json"
            with open(cache_file, 'w') as f:
                json.dump(playlist_data, f)
            logger.info(f"Playlist cache updated for {playlist_name}")
        except Exception as e:
            logger.error(f"Error saving playlist cache: {e}")
    
    def get_playlist(self, playlist_name):
        """Retrieve the specified playlist from Plex and handle caching."""
        try:
            # Get current playlist from server
            current_playlist = self.plex_server.playlist(playlist_name)
            current_hash = self.get_playlist_hash(current_playlist)
            
            # Load cached playlist
            cached_data = self.load_cached_playlist(playlist_name)
            
            if cached_data and cached_data.get('hash') == current_hash:
                logger.info(f"Using cached playlist - no changes detected for {playlist_name}")
                return current_playlist, False  # False indicates no update needed
            
            # If we reach here, playlist has changed or cache doesn't exist
            logger.info(f"Playlist changes detected or no cache exists for {playlist_name}")
            
            # Download all media files
            self.download_all_media(current_playlist.items())
            
            # Save playlist data with local file paths
            playlist_data = {
                'hash': current_hash,
                'last_updated': datetime.now().isoformat(),
                'items': [
                    {
                        'title': item.title,
                        'local_path': str(self.get_cached_file_path(item)),
                        'duration': item.duration,
                        'rating_key': item.ratingKey
                    }
                    for item in current_playlist.items()
                ]
            }
            self.save_playlist_cache(playlist_name, playlist_data)
            return current_playlist, True  # True indicates update was needed
            
        except Exception as e:
            logger.error(f"Could not find playlist {playlist_name}: {e}")
            raise
    
    def play_playlist(self):
        """Play the appropriate playlist based on current time."""
        try:
            playlist_name = self.get_current_playlist()
            logger.info(f"Selected playlist for current time: {playlist_name}")
            
            playlist, was_updated = self.get_playlist(playlist_name)
            
            if was_updated:
                logger.info(f"Playing updated playlist: {playlist_name}")
            else:
                logger.info(f"Playing cached playlist: {playlist_name}")
            
            # Load cached playlist data
            cached_data = self.load_cached_playlist(playlist_name)
            if not cached_data:
                logger.error(f"Could not load cached playlist data for {playlist_name}")
                return
            
            # Iterate through playlist items
            for item_data in cached_data['items']:
                logger.info(f"Playing: {item_data['title']}")
                
                local_path = Path(item_data['local_path'])
                if not local_path.exists():
                    logger.error(f"Cached file not found: {local_path}")
                    continue
                
                # Create media and set to player
                media = self.instance.media_new(str(local_path))
                self.player.set_media(media)
                
                # Start playback
                self.player.play()
                
                # Wait for current track to finish
                while self.player.is_playing():
                    pass
        
        except Exception as e:
            logger.error(f"Playback error: {e}")
    
    def stop(self):
        """Stop playback."""
        self.player.stop()

    def cleanup_cache(self, max_age_days=30):
        """Clean up old cached files that haven't been accessed recently."""
        try:
            current_time = datetime.now()
            for file_path in self.media_cache_dir.glob('*'):
                if file_path.is_file():
                    file_age = datetime.fromtimestamp(file_path.stat().st_mtime)
                    age_days = (current_time - file_age).days
                    
                    if age_days > max_age_days:
                        logger.info(f"Removing old cached file: {file_path.name}")
                        file_path.unlink()
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")

def main():
    parser = argparse.ArgumentParser(description='Plex Playlist Player')
    parser.add_argument('--time-slot', choices=['morning', 'afternoon', 'evening'],
                      help='Force a specific time slot (morning, afternoon, or evening)')
    args = parser.parse_args()

    try:
        playlist_player = PlexPlaylistPlayer(force_time_slot=args.time_slot)
        playlist_player.play_playlist()
    except Exception as e:
        logger.error(f"Application error: {e}")

if __name__ == "__main__":
    main()
