"""
API routes for the application
"""
import logging
from flask import Blueprint, request, jsonify

from services import room_service, game_service

logger = logging.getLogger(__name__)

# Create blueprint for API routes
api_blueprint = Blueprint('api', __name__)


@api_blueprint.route('/create-room', methods=['POST'])
def create_room():
    """Create a new game room

    Returns:
        JSON: Response with room code and player ID
    """
    username = request.json.get('username', 'Host')

    room_code, player_id, _ = room_service.create_room(username)

    return jsonify({
        'success': True,
        'room_code': room_code,
        'player_id': player_id
    })


@api_blueprint.route('/join-room', methods=['POST'])
def join_room():
    """Join an existing game room

    Returns:
        JSON: Response with room code and player ID
    """
    room_code = request.json.get('room_code', '').upper()
    username = request.json.get('username', 'Player')

    logger.info(f"Join room request: {room_code}, username: {username}")

    success, player_id, error_message = room_service.join_room(room_code, username)

    if not success:
        logger.warning(f"Failed to join room: {error_message}")
        return jsonify({
            'success': False,
            'message': error_message
        })

    # Notify all clients in the room that a new player has joined
    # (This is handled by the socket_events.py module)
    socketio = api_blueprint.socketio

    if socketio:
        room = room_service.get_room(room_code)
        if room:
            player_info = room.players[player_id]
            socketio.emit('player_joined', {
                'player_id': player_id,
                'username': username,
                'player_number': player_info.get('player_number'),
                'moderator': False
            }, to=room_code)

            # Also emit updated room state to all clients
            socketio.emit('room_state', {
                'room': room.to_dict(),
                'game_started': room.started
            }, to=room_code)

    return jsonify({
        'success': True,
        'room_code': room_code,
        'player_id': player_id
    })


@api_blueprint.route('/rooms', methods=['GET'])
def list_rooms():
    """List all active rooms (for debugging)

    Returns:
        JSON: List of active rooms
    """
    rooms = []

    for room_code in room_service.get_active_rooms():
        room = room_service.get_room(room_code)
        if room:
            rooms.append({
                'room_code': room_code,
                'player_count': len([p for p in room.players.values() if not p.get('moderator', False)]),
                'started': room.started
            })

    return jsonify({
        'success': True,
        'rooms': rooms
    })


@api_blueprint.route('/room/<room_code>', methods=['GET'])
def get_room_info(room_code):
    """Get information about a specific room

    Args:
        room_code: Room code

    Returns:
        JSON: Room information
    """
    room = room_service.get_room(room_code)

    if not room:
        return jsonify({
            'success': False,
            'message': 'Room not found'
        }), 404

    # Get game state if available
    game_state = game_service.get_game_state(room_code)

    return jsonify({
        'success': True,
        'room': {
            'room_code': room.room_code,
            'player_count': len([p for p in room.players.values() if not p.get('moderator', False)]),
            'max_players': room.max_players,
            'started': room.started,
            'players': [
                {
                    'id': pid,
                    'username': p['username'],
                    'player_number': p.get('player_number'),
                    'moderator': p.get('moderator', False),
                    'ready': p.get('ready', False)
                }
                for pid, p in room.players.items()
            ],
            'game_state': game_state
        }
    })


def init_routes(app, socketio_instance):
    """Initialize API routes

    Args:
        app: Flask application
        socketio_instance: Socket.IO instance
    """
    # Store Socket.IO instance for use in routes
    api_blueprint.socketio = socketio_instance

    # Register blueprint with Flask app
    app.register_blueprint(api_blueprint, url_prefix='/api')

    logger.info("API routes initialized")