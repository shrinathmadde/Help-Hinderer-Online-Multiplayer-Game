"""
Service for game-related operations
"""
import logging
from typing import Optional, Dict, Any

from models.game_room import GameRoom
from services.room_service import get_room
import config

logger = logging.getLogger(__name__)


def start_game(room_code: str, player_id: str) -> Dict[str, Any]:
    """Start a game in a room

    Args:
        room_code: Room code
        player_id: ID of the player trying to start the game (must be moderator)

    Returns:
        Dict[str, Any]: Result with success flag and message
    """
    # Normalize room code to upper case
    room_code = room_code.upper()

    room = get_room(room_code)

    if not room:
        logger.warning(f"Room {room_code} not found")
        return {"success": False, "message": "Room not found"}

    # Verify the player is the moderator
    if room.moderator_id != player_id:
        logger.warning(f"Non-moderator tried to start game: player={player_id}, moderator={room.moderator_id}")
        return {"success": False, "message": "Only the moderator can start the game"}

    # Check if the game is already started
    if room.started:
        logger.warning(f"Game already started in room {room_code}")
        return {"success": False, "message": "Game already started"}

    # Make sure we have enough players
    real_players = [pid for pid, pdata in room.players.items() if not pdata.get('moderator', False)]
    logger.info(f"Players in room {room_code}: {len(real_players)}/{room.max_players}")

    if len(real_players) < room.max_players:
        logger.warning(f"Not enough players to start game: {len(real_players)}/{room.max_players}")
        return {
            "success": False,
            "message": f"Need {room.max_players} players to start (currently {len(real_players)})"
        }

    # Start the game
    if room.start_game():
        logger.info(f"Game successfully started in room {room_code}")
        return {"success": True, "message": "Game started successfully"}
    else:
        logger.error(f"Failed to start game in room {room_code}")
        return {"success": False, "message": "Failed to start game"}


def process_player_input(room_code: str, player_id: str,
                         direction: Optional[str] = None,
                         special: Optional[str] = None) -> bool:
    """Process player input in a game

    Args:
        room_code: Room code
        player_id: Player ID
        direction: Movement direction (UP, DOWN, LEFT, RIGHT)
        special: Special action (e.g., PLACE_BLOCK)

    Returns:
        bool: True if input was processed, False otherwise
    """
    # Normalize room code to upper case
    room_code = room_code.upper()

    room = get_room(room_code)

    if not room or not room.started or player_id not in room.players:
        return False

    # Get player number
    player_number = room.players[player_id].get('player_number')
    if player_number is None:
        return False

    # Set input in the network input adapter
    if room.playerInput:
        if special == "PLACE_BLOCK":
            logger.debug(f"Player {player_number} placing block in room {room_code}")
            room.playerInput.set_player_input(player_number, None, 0, "PLACE_BLOCK")
        else:
            logger.debug(f"Player {player_number} moving {direction} in room {room_code}")
            room.playerInput.set_player_input(player_number, direction, 1, None)
        return True

    return False


def process_key_down(room_code: str, player_id: str, key_name: str) -> bool:
    """Process key press in a game

    Args:
        room_code: Room code
        player_id: Player ID
        key_name: Name of the key

    Returns:
        bool: True if key press was processed, False otherwise
    """
    # Normalize room code to upper case
    room_code = room_code.upper()

    room = get_room(room_code)

    if not room or not room.started or player_id not in room.players:
        return False

    # Get player number
    player_number = room.players[player_id].get('player_number')
    if player_number is None:
        return False

    # Set key state in the network input adapter
    if room.playerInput:
        room.playerInput.key_down(player_number, key_name)
        return True

    return False


def process_key_up(room_code: str, player_id: str, key_name: str) -> bool:
    """Process key release in a game

    Args:
        room_code: Room code
        player_id: Player ID
        key_name: Name of the key

    Returns:
        bool: True if key release was processed, False otherwise
    """
    # Normalize room code to upper case
    room_code = room_code.upper()

    room = get_room(room_code)

    if not room or not room.started or player_id not in room.players:
        return False

    # Get player number
    player_number = room.players[player_id].get('player_number')
    if player_number is None:
        return False

    # Set key state in the network input adapter
    if room.playerInput:
        room.playerInput.key_up(player_number, key_name)
        return True

    return False


def mark_player_ready(room_code: str, player_id: str) -> bool:
    """Mark a player as ready

    Args:
        room_code: Room code
        player_id: Player ID

    Returns:
        bool: True if player was marked as ready, False otherwise
    """
    # Normalize room code to upper case
    room_code = room_code.upper()

    room = get_room(room_code)

    if not room or player_id not in room.players:
        return False

    # Mark player as ready
    room.players[player_id]['ready'] = True
    logger.info(f"Player {player_id} is now ready in room {room_code}")

    return True


def get_game_state(room_code: str) -> Optional[Dict[str, Any]]:
    """Get the current game state

    Args:
        room_code: Room code

    Returns:
        Optional[Dict[str, Any]]: Game state or None if game is not running
    """
    # Normalize room code to upper case
    room_code = room_code.upper()

    room = get_room(room_code)

    if not room or not room.started or not room.engine:
        return None

    try:
        return {
            'engine_state': str(room.engine.getEngineState()),
            'scores': room.engine.getScores(),
            'player_turn': room.engine._gameState.playerTurn if hasattr(room.engine, '_gameState') else 0
        }
    except Exception as e:
        logger.exception(f"Error getting game state: {e}")
        return None


def run_game_loop(room: GameRoom, socketio) -> None:
    """Run the game loop for a room

    Args:
        room: Game room instance
        socketio: Socket.IO instance for communication
    """
    logger.info(f"Starting game loop for room {room.room_code}")

    # Make sure the game engine and UI are initialized
    if not room.engine or not room.ui:
        logger.error(f"ERROR: Engine or UI not initialized for room {room.room_code}")
        room.active = False
        return

    try:
        # Initialize frame counter for debugging
        frame_count = 0
        last_state = None

        # Run the game loop as long as the room is active and the engine is running
        while room.active and room.engine and room.engine.isActive():
            # Tick the game engine
            try:
                room.engine.tick()

                # Get current state for logging
                current_state = room.engine.getEngineState()
                if current_state != last_state:
                    logger.info(f"Game state changed in room {room.room_code}: {current_state}")
                    last_state = current_state

                # Update the UI
                room.ui.flip()

                # Print debug info every 100 frames
                frame_count += 1
                if frame_count % 100 == 0:
                    player0_pos = room.engine.getPlayerPosition(0)
                    player1_pos = room.engine.getPlayerPosition(1)
                    target_pos = room.engine.getTargetPosition()
                    logger.debug(f"Frame {frame_count}: P0={player0_pos}, P1={player1_pos}, Target={target_pos}")

                # Throttle the loop to around 20 FPS
                socketio.sleep(config.TICK_RATE)
            except Exception as e:
                logger.exception(f"Error in game loop tick for room {room.room_code}: {e}")
                socketio.sleep(1)  # Sleep longer on error

    except Exception as e:
        logger.exception(f"Fatal error in game loop for room {room.room_code}: {e}")
        room.active = False

    logger.info(f"Game loop ended for room {room.room_code}")

    # Notify clients that the game has ended
    socketio.emit('game_ended', {'message': 'Game has ended'}, to=room.room_code)