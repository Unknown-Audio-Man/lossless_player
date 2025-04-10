import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
HOME_DIR = Path('/home/jay')
PROJECT_DIR = HOME_DIR / 'lossless_player'
LOG_DIR = PROJECT_DIR / 'logs'
LOG_FILE = LOG_DIR / 'player.log'

# Create necessary directories
LOG_DIR.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Server configuration
MUSIC_SERVER_IP = os.getenv('MUSIC_SERVER_IP', '192.168.0.3')
MUSIC_SERVER_SHARE = os.getenv('MUSIC_SERVER_SHARE', 'music')
MUSIC_SERVER_USERNAME = os.getenv('MUSIC_SERVER_USERNAME', '')
MUSIC_SERVER_PASSWORD = os.getenv('MUSIC_SERVER_PASSWORD', '')
MOUNT_POINT = HOME_DIR / 'music_server'

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ALLOWED_TELEGRAM_USERS = [int(id.strip()) for id in os.getenv('ALLOWED_TELEGRAM_USERS', '').split(',') if id.strip()]

# Library configuration
LIBRARY_CACHE = PROJECT_DIR / 'music_library.json'

# Player configuration
PLAYER_VOLUME = int(os.getenv('PLAYER_VOLUME', '70'))

class MusicLibraryCache:
    """Class to manage music library cache"""
    
    @staticmethod
    def load():
        """Load music library from cache file"""
        if not LIBRARY_CACHE.exists():
            return {}
            
        try:
            with open(LIBRARY_CACHE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Error loading library cache from {LIBRARY_CACHE}")
            return {}
    
    @staticmethod
    def save(library):
        """Save music library to cache file"""
        try:
            with open(LIBRARY_CACHE, 'w') as f:
                json.dump(library, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving library cache: {e}")