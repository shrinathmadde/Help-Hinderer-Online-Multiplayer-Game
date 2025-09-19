"""
Main application entry point
"""
import logging
from flask import Flask
from flask_socketio import SocketIO
import os
import config

logger = logging.getLogger(__name__)


def create_app():
    """Create and configure the Flask application

    Returns:
        tuple: Flask application and Socket.IO instance
    """
    # Initialize Flask application
    app = Flask(__name__)
    app.config['SECRET_KEY'] = config.SECRET_KEY
    # Initialize Socket.IO
    socketio = SocketIO(app, cors_allowed_origins=config.CORS_ALLOWED_ORIGINS)

    # Import services first (order matters to avoid circular imports)
    from services import room_service, game_service

    # Initialize networking components
    from networking import init_networking
    init_networking(socketio, room_service, game_service)

    # Initialize routes last
    from routes import init_routes
    init_routes(app, socketio)

    return app, socketio

# Create the application
app, socketio = create_app()

# Start the server if run directly
if __name__ == '__main__':
    logger.info("Starting Multiplayer Puzzle Game server...")

    # Print available routes for debugging
    logger.info("Available routes:")
    for rule in app.url_map.iter_rules():
        logger.info(f"  {rule}")

    logger.info("Starting Socket.IO server...")

    socketio.run(app, host="0.0.0.0", port=5001, debug=False, use_reloader=False)
