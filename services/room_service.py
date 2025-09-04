"""
Service for managing game rooms
"""
import random
import string
import logging
from typing import Dict, Optional, List, Tuple

from models.game_room import GameRoom
import config

logger = logging.getLogger(__name__)

# Global storage for active rooms
active_rooms: Dict[str, GameRoom] = {}

def generate_room_code(length: int = config.ROOM_CODE_LENGTH) -> str:
    """Generate a unique room code

    Args:
        length: Length of the room code

    Returns:
        str: Unique room code
    """
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if code not in active_rooms:
            return code

def create_room(username: str, max_players: int = config.DEFAULT_MAX_PLAYERS) -> Tuple[str, str, GameRoom]:
    """Create a new game room

    Args:
        username: Username of the moderator
        max_players: Maximum number of players allowed

    Returns:
        Tuple[str, str, GameRoom]: Room code, moderator ID, and room instance
    """
    from uuid import uuid4
    print("creating room")
    room_code = generate_room_code()
    moderator_id = str(uuid4())

    room = GameRoom(room_code, max_players)
    room.add_player(moderator_id, username, is_moderator=True)
    active_rooms[room_code] = room

    logger.info(f"Created room {room_code} with moderator {username} ({moderator_id})")
    logger.info(f"Active rooms: {list(active_rooms.keys())}")
    print("created room")
    return room_code, moderator_id, room

def join_room(room_code: str, username: str) -> Tuple[bool, str, str]:
    """Add a player to an existing room

    Args:
        room_code: Room code
        username: Player's username

    Returns:
        Tuple[bool, str, str]: Success flag, player ID, and error message
    """
    from uuid import uuid4

    # Normalize room code to upper case
    room_code = room_code.upper()

    if room_code not in active_rooms:
        logger.warning(f"Room not found: {room_code}")
        return False, "", "Room not found"

    room = active_rooms[room_code]

    if room.is_full():
        logger.warning(f"Room is full: {room_code}")
        return False, "", "Room is full"

    player_id = str(uuid4())
    success = room.add_player(player_id, username)

    if not success:
        logger.warning(f"Failed to add player to room: {room_code}")
        return False, "", "Failed to join room"

    logger.info(f"Player {player_id} ({username}) successfully joined room {room_code}")
    logger.info(f"Players in room: {list(room.players.keys())}")

    return True, player_id, ""

def get_room(room_code: str) -> Optional[GameRoom]:
    """Get a room by code

    Args:
        room_code: Room code

    Returns:
        Optional[GameRoom]: Room instance or None if not found
    """
    # Normalize room code to upper case
    room_code = room_code.upper()
    return active_rooms.get(room_code)

def remove_room(room_code: str) -> bool:
    """Remove a room

    Args:
        room_code: Room code

    Returns:
        bool: True if room was removed, False if room was not found
    """
    # Normalize room code to upper case
    room_code = room_code.upper()

    if room_code in active_rooms:
        room = active_rooms[room_code]
        room.active = False  # Stop any running game loops
        del active_rooms[room_code]
        logger.info(f"Removed room {room_code}")
        return True

    return False

def remove_player(room_code: str, player_id: str) -> bool:
    """Remove a player from a room

    Args:
        room_code: Room code
        player_id: Player ID

    Returns:
        bool: True if player was removed, False otherwise
    """
    # Normalize room code to upper case
    room_code = room_code.upper()

    if room_code not in active_rooms:
        return False

    room = active_rooms[room_code]
    success = room.remove_player(player_id)

    # If room is now empty, remove it
    if success and room.is_empty():
        logger.info(f"Room {room_code} is now empty, removing")
        remove_room(room_code)

    return success

def get_active_rooms() -> List[str]:
    """Get a list of all active room codes

    Returns:
        List[str]: List of active room codes
    """
    return list(active_rooms.keys())

def cleanup_inactive_rooms() -> int:
    """Remove rooms that are no longer active

    Returns:
        int: Number of rooms removed
    """
    removed = 0
    for room_code in list(active_rooms.keys()):
        room = active_rooms[room_code]
        if not room.active or room.is_empty():
            remove_room(room_code)
            removed += 1

    return removed