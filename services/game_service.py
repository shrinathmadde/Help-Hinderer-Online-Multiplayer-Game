# services/game_service.py
import json, time, logging
from typing import Optional, Dict, Any, List

from services.redis_client import get_redis          # <- ensure you have a getter (or your redis_client)
from services.room_service import get_room, save_room, promote_to_live
from services import game_config                     # <- holds GAME_CONFIG
import config

logger = logging.getLogger(__name__)

# ---- Redis keys for this feature ----
def _k_trials(code: str):       return f"room:{code}:trials"
def _k_trial_idx(code: str):    return f"room:{code}:trial_index"
def _k_board(code: str):        return f"room:{code}:board"
def _k_deadline(code: str):     return f"room:{code}:trial_deadline"

def _r(r=None):
    """Return a Redis client; accept an override for testability."""
    return r or get_redis
# ---- Helpers to read/write trials meta ----
def _store_trials(room_code: str, trials: List[dict], r=None):
    r = _r(r)
    r.set(_k_trials(room_code), json.dumps(trials))

def _load_trials(room_code: str, r=None) -> Optional[List[dict]]:
    r = _r(r)
    raw = r.get(_k_trials(room_code))
    return json.loads(raw) if raw else None

def _set_trial_idx(room_code: str, idx: int, r=None):
    r = _r(r)
    r.set(_k_trial_idx(room_code), str(idx))

def _get_trial_idx(room_code: str, r=None) -> int:
    r = _r(r)
    raw = r.get(_k_trial_idx(room_code))
    return int(raw) if raw is not None else 0

def _save_board(room_code: str, board: dict, r=None):
    r = _r(r)
    r.set(_k_board(room_code), json.dumps(board))

def _load_board(room_code: str, r=None) -> Optional[dict]:
    r = _r(r)
    raw = r.get(_k_board(room_code))
    return json.loads(raw) if raw else None

def _set_deadline(room_code: str, ts: float, r=None):
    r = _r(r)
    r.set(_k_deadline(room_code), str(int(ts)))

def _get_deadline(room_code: str, r=None) -> Optional[int]:
    r = _r(r)
    raw = r.get(_k_deadline(room_code))
    return int(raw) if raw else None

# ---- Trial/board initialization ----
def _player_map(room, max_players=2) -> Dict[int, str]:
    """Create {0: player_id_for_R, 1: player_id_for_B} from room.players."""
    mapping = {}
    # your room stores players as dict; pick any two non-moderators by their assigned player_number if present
    for pid, pdata in room.players.items():
        if pdata.get('moderator'): 
            continue
        pn = pdata.get('player_number')
        if pn in (0, 1):
            mapping[pn] = pid
        # fallback if no player_number assigned: fill in order
        if 'player_number' not in pdata and len(mapping) < 2:
            mapping[len(mapping)] = pid
    return mapping

def _init_board_from_trial(room_code: str, trial: dict, room) -> dict:
    """Build the authoritative board for this trial and save it."""
    pm = _player_map(room)
    # trial.start_positions has "R" and "B" → map to player indexes 0/1
    start = trial["start_positions"]
    board = {
        "size": game_config.GAME_CONFIG.get("board_size", 4),
        "players": [
            {"id": pm.get(0), "username": room.players.get(pm.get(0), {}).get("username"), "pos": start["R"], "color": "red"},
            {"id": pm.get(1), "username": room.players.get(pm.get(1), {}).get("username"), "pos": start["B"], "color": "blue"},
        ],
        "target": trial["target"],
        "capturer": trial["capturer"],  # "R" or "B"
        "winner": None,
    }
    _save_board(room_code, board)
    return board

def _emit(sio, event: str, payload: dict, room_code: str):
    if sio:
        sio.emit(event, payload, to=room_code)

def _start_trial(room_code: str, idx: int, sio=None):
    r = _r()
    trials = _load_trials(room_code, r) or []
    if idx >= len(trials):
        # no more trials
        _emit(sio, "game_over", {"message": "All trials finished"}, room_code)
        return None

    room = get_room(room_code)
    trial = trials[idx]
    board = _init_board_from_trial(room_code, trial, room)

    # set deadline
    deadline = int(time.time()) + int(trial.get("time_limit_sec", 20))
    _set_deadline(room_code, deadline, r)
    _set_trial_idx(room_code, idx, r)

    # broadcast start (reuse GAME_START for each trial)
    _emit(sio, "game_start", {
        "trial_index": idx,
        "trial_total": len(trials),
        "board": board,
        "deadline": deadline,
    }, room_code)

    # optional: background timer to auto-advance when time runs out
    bg = globals().get("socketio", None)
    if bg:
        bg.start_background_task(_trial_timer_task, room_code)

    return board

def _trial_timer_task(room_code: str):
    sio = globals().get("socketio", None)
    r = _r()
    while True:
        deadline = _get_deadline(room_code, r)
        if deadline is None:
            return
        now = int(time.time())
        if now >= deadline:
            # time’s up → advance
            _advance_trial(room_code, reason="timeout", sio=sio)
            return
        # sleep a bit
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

    # notify completion
    _emit(sio, "trial_complete", {"trial_index": idx, "reason": reason}, room_code)

    next_idx = idx + 1
    if next_idx >= len(trials):
        _emit(sio, "game_over", {"message": "All trials finished"}, room_code)
        return

    _start_trial(room_code, next_idx, sio)

# ---- PUBLIC API you already call in sockets ----
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
        save_room(room)
        promote_to_live(room)

        # NEW: load trials from config and persist under room code
        trials = game_config.GAME_CONFIG.get("trials", [])
        _store_trials(room_code, trials)

        # Kick off trial #0 (sets board + deadline in Redis and emits GAME_START)
        _start_trial(room_code, 0, sio=globals().get("socketio"))
        return {"success": True, "message": "Game started successfully"}

    return {"success": False, "message": "Failed to start game"}

def apply_move_and_maybe_advance(room_code: str, player_id: str, dx: int, dy: int):
    """Called by your socket handler on each BOARD_UPDATE intent."""
    r = _r()
    board = _load_board(room_code, r)
    if not board:
        return None

    # find mover
    me = next((p for p in board["players"] if p["id"] == player_id), None)
    if not me:
        return board

    size = board["size"]
    x, y = me["pos"]
    nx = max(0, min(size - 1, x + dx))
    ny = max(0, min(size - 1, y + dy))
    me["pos"] = [nx, ny]

    # capture check: only the allowed player can capture this trial’s star
    capturer = board.get("capturer")  # "R" or "B"
    mover_is_R = (me is board["players"][0])
    if me["pos"] == board["target"] and ((capturer == "R" and mover_is_R) or (capturer == "B" and not mover_is_R)):
        board["winner"] = me["id"]
        _save_board(room_code, board, r)
        # advance to next trial
        _advance_trial(room_code, reason="captured", sio=globals().get("socketio"))
        return board

    _save_board(room_code, board, r)
    return board
