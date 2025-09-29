# services/room_service.py
import json
import random
import string
import logging
from typing import Dict, Optional, List, Tuple

from models.game_room import GameRoom
import config

from services.redis_client import get_redis  # NEW

logger = logging.getLogger(__name__)

# In-process map for live Engine/UI (optional for now; used only after start_game)


def _redis_key(room_code: str) -> str:
    return f"room:{room_code.upper()}"

def generate_room_code(length: int = config.ROOM_CODE_LENGTH) -> str:
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if not get_redis.exists(_redis_key(code)):
            return code

def create_room(username: str, max_players: int = config.DEFAULT_MAX_PLAYERS) -> Tuple[str, str, GameRoom]:
    from uuid import uuid4
    room_code = generate_room_code()
    moderator_id = str(uuid4())

    room = GameRoom(room_code, max_players)
    room.add_player(moderator_id, username, is_moderator=True)

    # Save metadata to Redis
    get_redis.set(_redis_key(room_code), json.dumps(room.to_meta()))
    logger.info(f"Created room {room_code} with moderator {username} ({moderator_id})")

    return room_code, moderator_id, room

def _get_meta(room_code: str) -> Optional[dict]:
    raw = get_redis.get(_redis_key(room_code))
    return json.loads(raw) if raw else None

def get_room(room_code: str) -> Optional[GameRoom]:
    room_code = room_code.upper()
    meta = _get_meta(room_code)
    if not meta:
        return None
    return GameRoom.from_meta(meta)

def save_room(room: GameRoom) -> None:
    """Persist metadata changes to Redis."""
    get_redis.set(_redis_key(room.room_code), json.dumps(room.to_meta()))

def join_room(room_code: str, username: str) -> Tuple[bool, str, str]:
    from uuid import uuid4
    room_code = room_code.upper()

    meta = _get_meta(room_code)
    if not meta:
        logger.warning(f"Room not found: {room_code}")
        return False, "", "Room not found"

    room = GameRoom.from_meta(meta)

    if room.is_full():
        logger.warning(f"Room is full: {room_code}")
        return False, "", "Room is full"

    player_id = str(uuid4())
    success = room.add_player(player_id, username)
    if not success:
        return False, "", "Failed to join room"

    save_room(room)  # persist back
    logger.info(f"Player {player_id} ({username}) joined room {room_code}")
    return True, player_id, ""

def remove_player(room_code: str, player_id: str) -> bool:
    room_code = room_code.upper()
    
    if not room:
        meta = _get_meta(room_code)
        if not meta:
            return False
        room = GameRoom.from_meta(meta)

    success = room.remove_player(player_id)
    if success:
        if room.is_empty():
            remove_room(room_code)
        else:
            save_room(room)
    return success

def remove_room(room_code: str) -> bool:
    room_code = room_code.upper()

    return bool(get_redis.delete(_redis_key(room_code)))

def get_active_rooms() -> List[str]:
    keys = get_redis.keys("room:*")
    return [k.split("room:", 1)[1] for k in keys]

def cleanup_inactive_rooms() -> int:
    removed = 0
    for code in get_active_rooms():
        meta = _get_meta(code)
        if not meta:
            continue
        room = GameRoom.from_meta(meta)
        if not room.active or room.is_empty():
            if remove_room(code):
                removed += 1
    return removed
