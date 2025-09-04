"""
Configuration settings for the application
"""
import logging
import os

# Flask settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')  # Change this in production
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

# Socket.IO settings
CORS_ALLOWED_ORIGINS = "*"

# Game settings
DEFAULT_MAX_PLAYERS = 2
ROOM_CODE_LENGTH = 6

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Game constants
TICK_RATE = 0.05  # 20 FPS