# services/board_service.py
import json
import random
from typing import Dict, Any, Tuple, Optional
from services.redis_client import get_redis

BOARD_SIZE = 4

def _key(room_code: str) -> str:
    return f"board:{room_code.upper()}"

def _empty_board() -> Dict[str, Any]:
    # matrix is optional here (we'll derive the draw from coordinates),
    # but we keep it for easy debugging/inspection.
    return {
        "size": BOARD_SIZE,
        "matrix": [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)],
        "players": {
            # player_number -> {"row": int, "col": int}
            "0": None,
            "1": None
        },
        "target": None
    }

def init_board(room_code: str, player_ids_by_number: Dict[int, str]) -> Dict[str, Any]:
    """
    Initialize a 4x4 board with:
      - player 0 (red) at a random empty cell
      - player 1 (blue) at a different random empty cell
      - a star at a third random empty cell
    The players mapping lets you keep track later if needed.
    """
    state = _empty_board()

    # Choose three distinct cells
    cells = [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE)]
    random.shuffle(cells)
    p0 = cells.pop()
    p1 = cells.pop()
    target = cells.pop()

    state["players"]["0"] = {"row": p0[0], "col": p0[1], "id": player_ids_by_number.get(0)}
    state["players"]["1"] = {"row": p1[0], "col": p1[1], "id": player_ids_by_number.get(1)}
    state["target"] = {"row": target[0], "col": target[1]}

    # Fill matrix for debugging (optional)
    mat = state["matrix"]
    mat[p0[0]][p0[1]] = "P0"
    mat[p1[0]][p1[1]] = "P1"
    mat[target[0]][target[1]] = "STAR"

    get_redis.set(_key(room_code), json.dumps(state))
    return state

def get_board(room_code: str) -> Optional[Dict[str, Any]]:
    raw = get_redis.get(_key(room_code))
    return json.loads(raw) if raw else None

def set_board(room_code: str, state: Dict[str, Any]) -> None:
    get_redis.set(_key(room_code), json.dumps(state))

def move_player(room_code: str, player_number: int, drow: int, dcol: int) -> Optional[Dict[str, Any]]:
    """
    Simple movement helper (no collisions/turns enforced here—extend as needed).
    """
    state = get_board(room_code)
    if not state:
        return None

    key = str(player_number)
    cur = state["players"].get(key)
    if not cur:
        return None

    size = state["size"]
    nr, nc = cur["row"] + drow, cur["col"] + dcol
    if 0 <= nr < size and 0 <= nc < size:
        # update matrix (optional maintenance)
        mat = state["matrix"]
        mat[cur["row"]][cur["col"]] = None
        mat[nr][nc] = f"P{player_number}"

        cur["row"], cur["col"] = nr, nc
        set_board(room_code, state)
        return state

    return state
