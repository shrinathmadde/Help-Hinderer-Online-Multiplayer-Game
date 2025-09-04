"""
Main application entry point
"""
import logging
from flask import Flask
from flask_socketio import SocketIO

import config

logger = logging.getLogger(__name__)

# Check if original game components are available
try:
    from backend.engine import Engine, EngineImpl, TrialResult
    from backend.engine_state import EngineState, isEngineStateTransitionAllowed
    from backend.game_state import GameState, isValidGameState
    from backend.util import Direction
    from backend.block_provider import BlockProvider, BlockProviderFromPremade
    from backend.player_input import PlayerInput
    from backend.saver import Saver, AppendFileSaver
    from backend.trial_provider import TrialProvider, TrialProviderFromPremade
    from assets.premade_trials.index import namedPremadeIndex
    from assets.premade_blocks.test_blocks import premade_test_blocks

    ORIGINAL_GAME_IMPORTS = True
    logger.info("Successfully imported original game components")
except ImportError as e:
    ORIGINAL_GAME_IMPORTS = False
    logger.error(f"Failed to import original game components: {e}")

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
    logger.info(f"Original game imports successful: {ORIGINAL_GAME_IMPORTS}")

    # Print available routes for debugging
    logger.info("Available routes:")
    for rule in app.url_map.iter_rules():
        logger.info(f"  {rule}")

    logger.info("Starting Socket.IO server...")

    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
