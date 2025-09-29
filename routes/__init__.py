"""
Routes package
"""
import logging
from flask import Flask
from flask_socketio import SocketIO

from .game_routes import init_routes as init_game_routes
from .api_routes import init_routes as init_api_routes

logger = logging.getLogger(__name__)


def init_routes(app: Flask, socketio: SocketIO):
    """Initialize all application routes

    Args:
        app: Flask application
        socketio: Socket.IO instance
    """
    logger.info("Initializing application routes")

    # Make socketio available to services (like game_service)
    import services.game_service as game_service
    game_service.set_socketio(socketio)

    # Initialize game routes
    init_game_routes(app)

    # Initialize API routes
    init_api_routes(app, socketio)

    logger.info("Routes initialization complete")
    
