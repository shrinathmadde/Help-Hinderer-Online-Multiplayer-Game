# services/game_service.py
import json, time, logging
from typing import Optional, Dict, Any, List, Tuple

from services.redis_client import get_redis          # client instance (NOT a function)
from services.room_service import get_room, save_room
from conf import game_config
import config

logger = logging.getLogger(__name__)



# services/game_service.py
_socketio = None
def set_socketio(sio):  # call once at startup
    global _socketio
    _socketio = sio

def _emit(event, payload, room_code):
    if _socketio:
        _socketio.emit(event, payload, to=room_code)



# ----------------------- Redis Keys -----------------------
def _k_trials(code: str)    -> str: return f"room:{code}:trials"
def _k_trial_idx(code: str) -> str: return f"room:{code}:trial_index"
def _k_positions(code: str) -> str: return f"room:{code}:positions"      # positions-only JSON
def _k_deadline(code: str)  -> str: return f"room:{code}:trial_deadline"

def _r(r=None):
    return r or get_redis   # get_redis is already a StrictRedis client in your project

# ----------------------- R/W helpers -----------------------
def _store_trials(room_code: str, trials: List[dict], r=None):
    r = _r(r); r.set(_k_trials(room_code), json.dumps(trials))

def _load_trials(room_code: str, r=None) -> Optional[List[dict]]:
    r = _r(r); raw = r.get(_k_trials(room_code))
    return json.loads(raw) if raw else None

def _set_trial_idx(room_code: str, idx: int, r=None):
    r = _r(r); r.set(_k_trial_idx(room_code), str(idx))

def _get_trial_idx(room_code: str, r=None) -> int:
    r = _r(r); raw = r.get(_k_trial_idx(room_code))
    return int(raw) if raw is not None else 0

def _save_positions(room_code: str, positions: dict, r=None):
    r = _r(r); r.set(_k_positions(room_code), json.dumps(positions))

def _load_positions(room_code: str, r=None) -> Optional[dict]:
    r = _r(r); raw = r.get(_k_positions(room_code))
    return json.loads(raw) if raw else None

def _set_deadline(room_code: str, ts: float, r=None):
    r = _r(r); r.set(_k_deadline(room_code), str(int(ts)))

def _get_deadline(room_code: str, r=None) -> Optional[int]:
    r = _r(r); raw = r.get(_k_deadline(room_code))
    return int(raw) if raw else None

# ----------------------- Utils -----------------------
def _emit(sio, event: str, payload: dict, room_code: str):
    if sio:
        sio.emit(event, payload, to=room_code)

def _player_map_RB(room) -> Dict[str, Optional[str]]:
    """
    Return {"R": player_id_for_red, "B": player_id_for_blue}.
    Uses room.players; expects players to have player_number 0/1 or fills by order.
    """
    red_id = blue_id = None
    # first pass: assigned numbers
    for pid, pdata in room.players.items():
        if pdata.get('moderator'):
            continue
        pn = pdata.get('player_number')
        if pn == 0:
            red_id = pid
        elif pn == 1:
            blue_id = pid
    # fallback: fill by encounter
    for pid, pdata in room.players.items():
        if pdata.get('moderator'):
            continue
        if red_id is None:
            red_id = pid; continue
        if blue_id is None and pid != red_id:
            blue_id = pid
            break
    return {"R": red_id, "B": blue_id}




# ----------------------- Trial control -----------------------
def _start_trial(room_code: str, idx: int, sio=None):
    r = _r()
    trials = _load_trials(room_code, r) or []
    if idx >= len(trials):
        _emit(sio, "game_over", {"message": "All trials finished"}, room_code)
        return None

    room = get_room(room_code)
    trial = trials[idx]
    positions, ids = None,None

    # deadline
    deadline = int(time.time()) + int(trial.get("time_limit_sec", 20))
    _set_deadline(room_code, deadline, r)
    _set_trial_idx(room_code, idx, r)

    # Broadcast start (positions-only). Include ids mapping so clients know their role.
    payload = {
        "trial_index": idx,
        "trial_total": len(trials),
        "positions": positions,
        "turn": positions["turn"],
        "ids": ids,                    # clients can map player_id -> 'R'/'B'
        "deadline": deadline,
    }
    # _emit(sio, "game_start", payload, room_code)

    # # Optional: background timer
    # bg = globals().get("socketio", None)
    # if bg:
    #     bg.start_background_task(_trial_timer_task, room_code)

    return payload

def _trial_timer_task(room_code: str):
    sio = globals().get("socketio", None)
    r = _r()
    while True:
        deadline = _get_deadline(room_code, r)
        if deadline is None:
            return
        now = int(time.time())
        if now >= deadline:
            _advance_trial(room_code, reason="timeout", sio=sio)
            return
        if sio:
            sio.sleep(1)
        else:
            time.sleep(1)

def _advance_trial(room_code: str, reason: str, sio=None):
    r = _r()
    idx = _get_trial_idx(room_code, r)
    trials = _load_trials(room_code, r) or []
    if idx >= len(trials):
        return

    _emit(sio, "trial_complete", {"trial_index": idx, "reason": reason}, room_code)

    next_idx = idx + 1
    if next_idx >= len(trials):
        _emit(sio, "game_over", {"message": "All trials finished"}, room_code)
        return

    _start_trial(room_code, next_idx, sio)

# ----------------------- Public API -----------------------
def start_game(room_code: str, player_id: str) -> Dict[str, Any]:
    room_code = room_code.upper()
    room = get_room(room_code)
    if not room:
        return {"success": False, "message": "Room not found"}

    if room.moderator_id != player_id:
        return {"success": False, "message": "Only the moderator can start the game"}

    real_players = [pid for pid, pdata in room.players.items() if not pdata.get('moderator', False)]
    if len(real_players) < room.max_players:
        return {"success": False, "message": f"Need {room.max_players} players to start (currently {len(real_players)})"}

    if room.start_game():
        return {"success": True, "message": "Game started successfully"}

    return {"success": False, "message": "Failed to start game"}

# ----------------------- Movement & Persistence -----------------------

# services/game_service.py
def mark_player_ready(room_code: str, player_id: str) -> bool:
    """
    Mark a player as ready. If all real (non-moderator) players are ready and the room is full,
    auto-start the game using the moderator id.
    """
    room_code = room_code.upper()
    room = get_room(room_code)
    if not room:
        logger.warning(f"[ready] room not found: {room_code}")
        return False
    if player_id not in room.players:
        logger.warning(f"[ready] player not in room: {player_id} / {room_code}")
        return False

    # flag ready
    pdata = room.players[player_id] or {}
    pdata["ready"] = True
    room.players[player_id] = pdata
    save_room(room)

    return True


# services/game_service.py
from typing import Any, Dict, Optional
import json

def _get_positions(room_code: str, r=None) -> Dict[str, Any]:
    """Return authoritative positions dict: {'R':[x,y], 'B':[x,y], 'size':int, 'capturer':'R'|'B', 'turn':'R'|'B'}."""
    r = r or _r()
    # PREFERRED: if you already have a helper, use it here (replace this function).
    # Common patterns (uncomment the one you actually use):

    # 1) Single JSON blob
    raw = r.get(f"game:{room_code}:positions")
    if raw:
        return json.loads(raw)

    # 2) Hash fields (R,B,size,capturer,turn)
    h = r.hgetall(f"game:{room_code}:positions")
    if h:
        def j(v): 
            try: return json.loads(v) 
            except Exception: return v
        pos = {k.decode(): j(v) for k, v in h.items()}
        # Ensure lists are lists (not strings)
        for k in ("R", "B"):
            if isinstance(pos.get(k), str):
                try: pos[k] = json.loads(pos[k])
                except Exception: pass
        return pos

    return {}  # nothing stored yet


def _get_ids_map(room_code: str, r=None) -> Optional[Dict[str, str]]:
    """Return {'R': <player_id>, 'B': <player_id>} if available."""
    r = r or _r()
    raw = r.get(f"game:{room_code}:ids")
    if raw:
        return json.loads(raw)

    # If you don't store ids separately, you can derive from the Room if roles are saved there.
    room = get_room(room_code)
    if room:
        # Example if you store role on each player: pdata['role'] in {'R','B'}
        mapping = {}
        for pid, pdata in room.players.items():
            role = (pdata or {}).get("role")
            if role in ("R", "B"):
                mapping[role] = pid
        if mapping:
            return mapping

    return None







