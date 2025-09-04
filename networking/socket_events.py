"""
Socket.IO event handlers
"""
import logging
from flask import request
from flask_socketio import emit, join_room, leave_room

# Remove direct imports to avoid circular dependency
# from services import room_service, game_service

logger = logging.getLogger(__name__)

# Will be set by the main application
socketio = None
# These will be set during initialization to avoid circular imports
room_service = None
game_service = None

def init_socket_events(socket_io, room_svc=None, game_svc=None):
    """Initialize Socket.IO event handlers

    Args:
        socket_io: Socket.IO instance
        room_svc: Room service instance
        game_svc: Game service instance
    """
    global socketio, room_service, game_service
    socketio = socket_io

    # Set services if provided
    if room_svc:
        room_service = room_svc
    if game_svc:
        game_service = game_svc

    # Import and set socketio in network_ui module
    from networking import network_ui
    network_ui.socketio = socket_io

    logger.info("Socket.IO event handlers initialized")


def register_handlers():
    """Register Socket.IO event handlers"""

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        logger.info(f'Client connected: {request.sid}')

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        logger.info(f'Client disconnected: {request.sid}')

        # Find and remove player from any rooms they were in
        for room_code in room_service.get_active_rooms():
            room = room_service.get_room(room_code)
            if not room:
                continue

            for player_id in list(room.players.keys()):
                if 'sids' in room.players[player_id] and request.sid in room.players[player_id]['sids']:
                    logger.info(f"Player {player_id} disconnected from room {room_code}")

                    # Remove this connection ID
                    room.players[player_id]['sids'].remove(request.sid)

                    # Only remove the player completely if they have no active connections
                    if not room.players[player_id]['sids']:
                        logger.info(f"Player {player_id} has no active connections, removing from room")
                        room.remove_player(player_id)
                        socketio.emit('player_left', {'player_id': player_id}, to=room_code)

                        # If room is empty, remove it
                        if room.is_empty():
                            logger.info(f"Room {room_code} is now empty, removing")
                            room.active = False  # Stop the game loop
                            room_service.remove_room(room_code)

                    # Even if the player has other connections, notify everyone about the disconnect
                    socketio.emit('room_state', {
                        'room': room.to_dict(),
                        'game_started': room.started
                    }, to=room_code)

                    break

    @socketio.on('join_game')
    def handle_join_game(data):
        """Handle player joining a game room

        Args:
            data: Event data with room_code and player_id
        """
        room_code = data.get('room_code')
        player_id = data.get('player_id')

        logger.info(f"Player {player_id} attempting to join room {room_code}")

        if not room_code or not player_id:
            logger.warning(f"Missing room_code or player_id: {data}")
            emit('error', {'message': 'Invalid room or player'})
            return

        if not room_service.get_room(room_code):
            logger.warning(f"Room {room_code} not found. Available rooms: {room_service.get_active_rooms()}")
            emit('error', {'message': 'Room not found'})
            return

        room = room_service.get_room(room_code)

        if player_id not in room.players:
            logger.warning(f"Error: Player {player_id} not found in room {room_code}.")
            logger.warning(f"Players in room: {list(room.players.keys())}")
            emit('error', {'message': 'Player not in this room'})
            return

        # Add socket ID to player's data for tracking
        if 'sids' not in room.players[player_id]:
            room.players[player_id]['sids'] = []

        # Only add the socket ID if not already registered
        if request.sid not in room.players[player_id]['sids']:
            room.players[player_id]['sids'].append(request.sid)

        # Join the Socket.IO room
        join_room(room_code)
        logger.info(f"Player {player_id} joined Socket.IO room {room_code}")

        # Notify others that player joined
        player_info = room.players[player_id]
        logger.debug(f"Player info: {player_info}")

        # Emit to everyone in the room EXCEPT the joining player
        emit('player_joined', {
            'player_id': player_id,
            'username': player_info['username'],
            'player_number': player_info.get('player_number'),
            'moderator': player_info.get('moderator', False)
        }, to=room_code, include_self=False)

        # Send room state to the player who just joined
        emit('room_state', {
            'room': room.to_dict(),
            'game_started': room.started
        })

        logger.info(f"Sent room state to player {player_id}")

    @socketio.on('start_game')
    def handle_start_game(data):
        """Handle game start request

        Args:
            data: Event data with room_code and player_id
        """
        room_code = data.get('room_code')
        player_id = data.get('player_id')

        logger.info(f"Start game request received: room={room_code}, player={player_id}")

        result = game_service.start_game(room_code, player_id)

        if not result['success']:
            emit('error', {'message': result['message']})
            return

        # Start the game loop in the background
        room = room_service.get_room(room_code)
        if room:
            socketio.start_background_task(game_service.run_game_loop, room, socketio)
            # Notify all players that the game has started
            socketio.emit('game_start', {}, to=room_code)

    @socketio.on('player_ready')
    def handle_player_ready(data):
        """Handle player ready event

        Args:
            data: Event data with room_code and player_id
        """
        room_code = data.get('room_code')
        player_id = data.get('player_id')

        logger.info(f"Player ready: room={room_code}, player={player_id}")

        if not game_service.mark_player_ready(room_code, player_id):
            emit('error', {'message': 'Failed to mark player as ready'})
            return

        # Notify all clients about the updated state
        room = room_service.get_room(room_code)
        if room:
            socketio.emit('room_state', {
                'room': room.to_dict(),
                'game_started': room.started
            }, to=room_code)

    @socketio.on('player_move')
    def handle_player_move(data):
        """Handle player movement event

        Args:
            data: Event data with room_code, player_id, direction, and special
        """
        room_code = data.get('room_code')
        player_id = data.get('player_id')
        direction = data.get('direction')
        special = data.get('special')

        game_service.process_player_input(room_code, player_id, direction, special)

    @socketio.on('key_down')
    def handle_key_down(data):
        """Handle key press event

        Args:
            data: Event data with room_code, player_id, and key
        """
        room_code = data.get('room_code')
        player_id = data.get('player_id')
        key = data.get('key')

        if not room_code or not player_id or not key:
            return

        game_service.process_key_down(room_code, player_id, key)

    @socketio.on('key_up')
    def handle_key_up(data):
        """Handle key release event

        Args:
            data: Event data with room_code, player_id, and key
        """
        room_code = data.get('room_code')
        player_id = data.get('player_id')
        key = data.get('key')

        if not room_code or not player_id or not key:
            return

        game_service.process_key_up(room_code, player_id, key)

    logger.info("Socket.IO event handlers registered")