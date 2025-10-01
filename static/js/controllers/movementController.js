// Handles per-window keyboard input + local validation + tiny optimistic dot move.
// Expects a renderer with updatePlayer(role, [x,y]) and a getSnapshot() function
// returning { size, positions:{R:[x,y],B:[x,y]}, target:[x,y], turn:'R'|'B', capturer:'R'|'B', myRole:'R'|'B' }.

import { EVT } from "../shared/events.js";
import { getSocket } from "../shared/socket.js";

const DIRS = {
  ArrowUp: [0, -1],
  ArrowDown: [0, 1],
  ArrowLeft: [-1, 0],
  ArrowRight: [1, 0],
  w: [0, -1],
  s: [0, 1],
  a: [-1, 0],
  d: [1, 0],
  W: [0, -1],
  S: [0, 1],
  A: [-1, 0],
  D: [1, 0],
};

export function attachMovement({ socket, getSnapshot, roomCode, playerId }) {
  let cooldownAt = 0;
  const COOLDOWN = 70;
  let inputLocked = false;

  function setLocked(v) {
    inputLocked = v;
  }

  function canMoveNow(snap) {
    if (inputLocked) return false;
    return snap.turn === snap.myRole; // only current player may move
  }

  function inBounds(s, x, y) {
    return x >= 0 && y >= 0 && x < s.size && y < s.size;
  }
  function occupied(s, x, y, myRole) {
    const other = myRole === "R" ? "B" : "R";
    const op = s.positions[other];
    return op && op[0] === x && op[1] === y;
  }
  function isStar(s, x, y) {
    return s.target && s.target[0] === x && s.target[1] === y;
  }
  function capturerIsMe(s) {
    return s.capturer === s.myRole;
  }

  function tryMove(dx, dy) {
    const now = Date.now();
    if (now - cooldownAt < COOLDOWN) return;
    cooldownAt = now;

    const s = getSnapshot();
    if (!canMoveNow(s)) return;

    const mePos = s.positions[s.myRole];
    if (!mePos) return;

    const nx = mePos[0] + dx,
      ny = mePos[1] + dy;
    if (!inBounds(s, nx, ny)) return;
    if (occupied(s, nx, ny, s.myRole)) return;
    if (isStar(s, nx, ny) && !capturerIsMe(s)) return;

    // lock a bit if we captured; server remains authoritative
    const captured = isStar(s, nx, ny) && capturerIsMe(s);
    if (captured) setLocked(true);

    // emit to server so it can persist to Redis and toggle turn

    // use shared event name
    socket.emit(EVT.BOARD_UPDATE, {
      room_code: roomCode,
      player_id: playerId,
      move: { dx, dy },
    });
  }

  function onKey(e) {
    const dir = DIRS[e.key];
    if (!dir) return;
    e.preventDefault();
    tryMove(dir[0], dir[1]);
  }

  window.addEventListener("keydown", onKey, { passive: false });

  return {
    lock: () => setLocked(true),
    unlock: () => setLocked(false),
    destroy: () => window.removeEventListener("keydown", onKey),
  };
}
