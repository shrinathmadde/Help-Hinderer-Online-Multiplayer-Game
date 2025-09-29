"""
Networking package
"""
import logging
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

def init_networking(socketio: SocketIO, room_service=None, game_service=None):
    """Initialize networking components

    Args:
        socketio: Socket.IO instance
        room_service: Room service instance
        game_service: Game service instance
    """
    logger.info("Initializing networking components")

    # Import here to avoid circular import
    from .socket_events import init_socket_events

    # Initialize Socket.IO event handlers
    init_socket_events(socketio, room_service, game_service)

    logger.info("Networking initialization complete")