"""
Game-related routes for the application
"""
import logging
from flask import Blueprint, render_template, redirect, url_for
from services import room_service

logger = logging.getLogger(__name__)

# Create blueprint for game routes
game_blueprint = Blueprint('game', __name__)





@game_blueprint.route('/')
def index():
    """Home page

    Returns:
        HTML: Index page
    """
    return render_template('index.html')


@game_blueprint.route('/game/<room_code>')
def game(room_code):
    """Game page

    Args:
        room_code: Room code

    Returns:
        HTML: Game page or error page
    """
    logger.info(f"Game page requested for room {room_code}")

    # Make sure the room code is uppercase
    room_code = room_code.upper()

    room = room_service.get_room(room_code)
    if not room:
        logger.warning(f"Room {room_code} not found. Available rooms: {room_service.get_active_rooms()}")
        return render_template('error.html',
                               error_title="Room Not Found",
                               error_message=f"The room '{room_code}' does not exist or has expired.",
                               home_link=True), 404

    # Check if the room has started
    if not room.started:
        logger.info(f"Room {room_code} exists but game has not started. Redirecting to waiting page.")
        return redirect(url_for('game.waiting', room_code=room_code))

    return render_template('game.html', room_code=room_code)


@game_blueprint.route('/waiting/<room_code>')
def waiting(room_code):
    """Waiting room page

    Args:
        room_code: Room code

    Returns:
        HTML: Waiting room page or error page
    """
    logger.info(f"Waiting page requested for room {room_code}")

    # Make sure the room code is uppercase
    room_code = room_code.upper()

    if not room_service.get_room(room_code):
        logger.warning(f"Room {room_code} not found. Available rooms: {room_service.get_active_rooms()}")
        return render_template('error.html',
                               error_title="Room Not Found",
                               error_message=f"The room '{room_code}' does not exist or has expired.",
                               home_link=True), 404

    return render_template('waiting.html', room_code=room_code)


@game_blueprint.route('/debug/<room_code>')
def debug_room(room_code):
    """Debug page for examining room state

    Args:
        room_code: Room code

    Returns:
        HTML: Debug page or error page
    """
    logger.info(f"Debug page requested for room {room_code}")

    # Make sure the room code is uppercase
    room_code = room_code.upper()

    room = room_service.get_room(room_code)
    if not room:
        logger.warning(f"Room {room_code} not found. Available rooms: {room_service.get_active_rooms()}")
        return render_template('error.html',
                               error_title="Room Not Found",
                               error_message=f"The room '{room_code}' does not exist or has expired.",
                               home_link=True), 404

    room_info = room.to_dict()

    # Format room info for display
    formatted_info = {
        'room_code': room_info['room_code'],
        'started': room_info['started'],
        'max_players': room_info['max_players'],
        'players': []
    }

    for player_id, player_data in room_info['players'].items():
        formatted_player = {
            'id': player_id,
            'username': player_data.get('username', 'Unknown'),
            'player_number': player_data.get('player_number', 'N/A'),
            'moderator': player_data.get('moderator', False),
            'ready': player_data.get('ready', False),
            'sids': player_data.get('sids', [])
        }
        formatted_info['players'].append(formatted_player)

    # Get game engine state if available
    engine_state = None
    if room.engine:
        try:
            engine_state = {
                'engine_state': str(room.engine.getEngineState()),
                'scores': room.engine.getScores() if hasattr(room.engine, 'getScores') else [0, 0],
                'player_turn': room.engine._gameState.playerTurn if hasattr(room.engine, '_gameState') and hasattr(
                    room.engine._gameState, 'playerTurn') else None
            }
        except Exception as e:
            logger.exception(f"Error getting engine state: {e}")
            engine_state = {'error': str(e)}

    return render_template('debug.html', room=formatted_info, engine_state=engine_state)


# Error handlers
@game_blueprint.errorhandler(404)
def page_not_found(e):
    return render_template('error.html',
                           error_title="Page Not Found",
                           error_message="The page you requested could not be found.",
                           home_link=True), 404


@game_blueprint.errorhandler(500)
def server_error(e):
    logger.exception(f"Server error: {e}")
    return render_template('error.html',
                           error_title="Server Error",
                           error_message="An internal server error occurred.",
                           error_details=str(e),
                           home_link=True,
                           refresh_link=True), 500


def init_routes(app):
    """Initialize game routes

    Args:
        app: Flask application
    """
    # Register blueprint with Flask app
    app.register_blueprint(game_blueprint)

    # Register error handlers
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, server_error)

    logger.info("Game routes initialized")