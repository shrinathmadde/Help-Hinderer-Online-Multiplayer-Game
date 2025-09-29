// /static/js/shared/socketApi.js
// A tiny, opinionated wrapper around Socket.IO for your game.
// Assumes <script src="/socket.io/socket.io.js"></script> is loaded (global `io`).

const DEFAULTS = {
  path: "/socket.io",
  autoConnect: true,
  transports: ["websocket", "polling"],
};

// Event names used by server <-> client
export const EVT = {
  // server -> client
  GAME_START: "game_start",
  BOARD_UPDATE: "board_update",
  TRIAL_COMPLETE: "trial_complete",
  GAME_OVER: "game_over",
  ERROR: "error",

  // client -> server
  JOIN_ROOM: "join_room",
  LEAVE_ROOM: "leave_room",
  PLAYER_READY: "player_ready",
  START_GAME: "start_game",
  MOVE: "move",
  REQUEST_LIVE: "request_live_state",
};

let _socket = null;
let _connected = false;
let _roomInfo = { roomCode: null, username: null, playerId: null };

/** Initialize (or return) a singleton socket connection. */
export function getSocket(opts = {}) {
  if (_socket) return _socket;

  const url = opts.url || undefined; // same origin by default
  const s = (window.io ? window.io(url, { ...DEFAULTS, ...opts }) : null);
  if (!s) throw new Error("socketApi: window.io not found. Make sure socket.io client is loaded.");

  // base lifecycle
  s.on("connect", () => {
    _connected = true;
    // If we already have room info, re-join on reconnect
    if (_roomInfo.roomCode && _roomInfo.username && _roomInfo.playerId) {
      _emit(EVT.JOIN_ROOM, { ..._roomInfo, reconnect: true });
    }
  });

  s.on("disconnect", () => {
    _connected = false;
  });

  _socket = s;
  return _socket;
}

/** True if the socket is connected. */
export function isConnected() {
  return _connected && !!_socket && _socket.connected;
}

/** Subscribe to an event with a handler; returns an unsubscribe fn. */
export function on(event, handler) {
  const s = getSocket();
  s.on(event, handler);
  return () => s.off(event, handler);
}

/** One-time subscription. */
export function once(event, handler) {
  const s = getSocket();
  s.once(event, handler);
}

/** Unsubscribe a handler (or all handlers for an event if handler missing). */
export function off(event, handler) {
  const s = getSocket();
  if (handler) s.off(event, handler);
  else s.removeAllListeners(event);
}

/** Internal emit helper that guards on socket existence. */
function _emit(event, payload) {
  const s = getSocket();
  s.emit(event, payload);
}

/* =========================
   High-level, typed emits
   ========================= */

/** Join a room and remember identity for auto-rejoin on reconnect. */
export function joinRoom({ roomCode, username, playerId }) {
  _roomInfo = { roomCode: String(roomCode).toUpperCase(), username: String(username || "Player"), playerId: String(playerId || "") };
  _emit(EVT.JOIN_ROOM, _roomInfo);
}

/** Leave the current room. */
export function leaveRoom() {
  if (_roomInfo.roomCode) {
    _emit(EVT.LEAVE_ROOM, { roomCode: _roomInfo.roomCode, playerId: _roomInfo.playerId });
  }
}

/** Mark self ready (used on waiting screen). */
export function playerReady() {
  if (!_roomInfo.roomCode) return;
  _emit(EVT.PLAYER_READY, { roomCode: _roomInfo.roomCode, playerId: _roomInfo.playerId });
}

/** Moderator starts the game. */
export function startGame() {
  if (!_roomInfo.roomCode) return;
  _emit(EVT.START_GAME, { roomCode: _roomInfo.roomCode, playerId: _roomInfo.playerId });
}

/** Ask server for the latest authoritative live payload (positions, ids, deadline…). */
export function requestLive() {
  if (!_roomInfo.roomCode) return;
  _emit(EVT.REQUEST_LIVE, { roomCode: _roomInfo.roomCode });
}

/** Send a move delta (dx, dy). */
export function move(dx, dy) {
  if (!_roomInfo.roomCode) return;
  _emit(EVT.MOVE, { roomCode: _roomInfo.roomCode, playerId: _roomInfo.playerId, dx, dy });
}

/* =========================
   Event-specific helpers
   (thin sugar over `on`)
   ========================= */

export const subscribe = {
  gameStart: (cb) => on(EVT.GAME_START, cb),
  boardUpdate: (cb) => on(EVT.BOARD_UPDATE, cb),
  trialComplete: (cb) => on(EVT.TRIAL_COMPLETE, cb),
  gameOver: (cb) => on(EVT.GAME_OVER, cb),
  error: (cb) => on(EVT.ERROR, cb),
  connect: (cb) => on("connect", cb),
  disconnect: (cb) => on("disconnect", cb),
};

/** Allow external access to the raw socket if truly needed. */
export function raw() { return getSocket(); }
