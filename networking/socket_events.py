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
    """Register Socket.IO event handlers"""
    global socketio, room_service, game_service
    socketio, room_service, game_service = socket_io, room_svc, game_svc
    
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
        """Handle player joining a game room"""
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

        # Track this socket id for the player
        room.players.setdefault(player_id, {}).setdefault('sids', [])
        if request.sid not in room.players[player_id]['sids']:
            room.players[player_id]['sids'].append(request.sid)

        # Join the Socket.IO room
        join_room(room_code)
        logger.info(f"Player {player_id} joined Socket.IO room {room_code}")

        # Notify others in the room (not the joiner)
        try:
            current_trial_index = int(getattr(room, "current_trial_index", 0) or 0)
        except Exception:
            current_trial_index = 0

        trials = list(getattr(room, "trials", []) or [])
        # Send room metadata to the joiner, with trial info included
        emit('room_state', {
            'room': room.to_dict(),
            'game_started': room.started,
            # ---- NEW fields ----
            'current_trial_index': current_trial_index,
            'trials': trials,
            'trials_total': len(trials),
        }, to=room_code, include_self=True)

        logger.info(
            f"has_trial={trials is not None}) to player {player_id}"
        )
        
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
            logger.info(f"Start game started")
            socketio.emit('game_start',to=room_code)
        return
    
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
            
        return
            
    @socketio.on('board_update')
    def handle_board_update(data):
        room_code = data.get("room_code")
        player_id = data.get("player_id")
        move = data.get("move", {})
        
        logger.info(f"Board_Update: room={room_code}, player={player_id}, move={move}")
        dx, dy = move.get("dx"), move.get("dy")
        if not room_code or not player_id or dx is None or dy is None:
            emit("error", {"message": "Invalid board update payload"})
            return

        trial = game_service.update_position(room_code, player_id, dx, dy)
        if not trial:
            emit("error", {"message": "Failed to update position"})
            return

        handle_join_game(data)
        return
