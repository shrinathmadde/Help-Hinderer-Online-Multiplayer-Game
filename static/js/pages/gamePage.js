// static/js/pages/gamePage.js
import { EVT } from '../shared/events.js';
import { getSocket } from '../shared/socket.js';

// ===== Bootstrapping =====
const BOOT = window.GAME_BOOTSTRAP || {};
const ROOM_CODE = (BOOT.roomCode || window.ROOM_CODE || '').toString().toUpperCase();
const USERNAME  = (BOOT.username || localStorage.getItem('username') || 'Player').trim();
const PLAYER_ID = localStorage.getItem('player_id') || null;

const canvas = document.getElementById('board');
const ctx = canvas?.getContext('2d');

// DPI-safe canvas sizing
function fitCanvasDPR(cnv) {
  const dpr = window.devicePixelRatio || 1;
  const { width, height } = cnv.getBoundingClientRect();
  cnv.width  = Math.round(width * dpr);
  cnv.height = Math.round(height * dpr);
  cnv.style.width  = `${width}px`;
  cnv.style.height = `${height}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

// ===== Board Model (client view) =====
// Server should be authoritative and persist this structure to Redis.
const BOARD_SIZE = 4;

// Canonical state the server should own/persist; we keep a mirror here.
// Positions are [col, row], 0-based, (0,0) = top-left.
let board = {
  size: BOARD_SIZE,
  players: [
    // Server will fill ids/usernames and positions. We include defaults for dev.
    { id: null, username: null, color: 'red',  pos: [0, 0] }, // player index 0
    { id: null, username: null, color: 'blue', pos: [3, 3] }, // player index 1
  ],
  target: [2, 1], // default; server may override
};

window.BOARD_STATE = board; // exposed for debugging in console

// Utility: regenerate a 4x4 matrix view (helpful for debugging)
function toMatrix(state) {
  const m = Array.from({ length: state.size }, () => Array(state.size).fill('.'));
  const [tx, ty] = state.target;
  m[ty][tx] = '★';
  state.players.forEach((p, idx) => {
    if (!p?.pos) return;
    const [x, y] = p.pos;
    m[y][x] = idx === 0 ? 'R' : 'B';
  });
  return m;
}
window.BOARD_MATRIX = () => toMatrix(board);

// ===== Drawing =====
function draw() {
  if (!ctx || !canvas) return;
  fitCanvasDPR(canvas);

  const W = canvas.getBoundingClientRect().width;
  const H = canvas.getBoundingClientRect().height;
  const N = board.size;
  const cs = Math.min(W, H) / N; // cell size

  // background
  ctx.fillStyle = '#111';
  ctx.fillRect(0, 0, W, H);

  // chessboard
  for (let r = 0; r < N; r++) {
    for (let c = 0; c < N; c++) {
      const x = c * cs;
      const y = r * cs;
      const dark = (r + c) % 2 === 0;
      ctx.fillStyle = dark ? '#1b1b1b' : '#232323';
      ctx.fillRect(x, y, cs, cs);
    }
  }

  // grid lines (subtle)
  ctx.strokeStyle = '#2b2b2b';
  ctx.lineWidth = 1;
  for (let i = 0; i <= N; i++) {
    ctx.beginPath();
    ctx.moveTo(i * cs, 0); ctx.lineTo(i * cs, N * cs); ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0, i * cs); ctx.lineTo(N * cs, i * cs); ctx.stroke();
  }

  // target star
  drawStar(board.target, cs);

  // players
  drawPlayer(board.players[0], cs, '#ff4d4f'); // red
  drawPlayer(board.players[1], cs, '#4da6ff'); // blue
}

function drawPlayer(player, cs, fill) {
  if (!player?.pos) return;
  const [cx, cy] = player.pos;
  const x = (cx + 0.5) * cs;
  const y = (cy + 0.5) * cs;
  const r = cs * 0.22;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  ctx.fillStyle = fill;
  ctx.fill();
}

function drawStar(pos, cs) {
  const [cx, cy] = pos;
  const x = (cx + 0.5) * cs;
  const y = (cy + 0.5) * cs;
  const spikes = 5, outerR = cs * 0.26, innerR = cs * 0.11;

  let rot = Math.PI / 2 * 3;
  let step = Math.PI / spikes;

  ctx.beginPath();
  ctx.moveTo(x, y - outerR);
  for (let i = 0; i < spikes; i++) {
    let x1 = x + Math.cos(rot) * outerR;
    let y1 = y + Math.sin(rot) * outerR;
    ctx.lineTo(x1, y1);
    rot += step;

    x1 = x + Math.cos(rot) * innerR;
    y1 = y + Math.sin(rot) * innerR;
    ctx.lineTo(x1, y1);
    rot += step;
  }
  ctx.lineTo(x, y - outerR);
  ctx.closePath();
  ctx.fillStyle = '#ffd43b';
  ctx.strokeStyle = '#a88400';
  ctx.lineWidth = 2;
  ctx.fill();
  ctx.stroke();
}

// ===== Input (local) =====
// We emit intent; server validates, updates Redis, and broadcasts EVT.BOARD_UPDATE.
const KEY_TO_DIR = {
  ArrowUp: [0, -1],    w: [0, -1], W: [0, -1],
  ArrowDown: [0, 1],   s: [0, 1],  S: [0, 1],
  ArrowLeft: [-1, 0],  a: [-1, 0], A: [-1, 0],
  ArrowRight: [1, 0],  d: [1, 0],  D: [1, 0],
};

function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }

function handleMoveIntent(dx, dy) {
  const socket = getSocket();
  const payload = {
    roomCode: ROOM_CODE,
    playerId: PLAYER_ID,
    username: USERNAME,
    move: { dx, dy }, // server computes next pos and win/score if any
  };
  socket.emit(EVT.BOARD_UPDATE, payload);
}

window.addEventListener('keydown', (e) => {
  const dir = KEY_TO_DIR[e.key];
  if (!dir) return;
  e.preventDefault();
  handleMoveIntent(dir[0], dir[1]);
});

// Also support clicking a cell to move one step toward it (optional UX nicety)
canvas?.addEventListener('click', (e) => {
  const rect = canvas.getBoundingClientRect();
  const cs = rect.width / BOARD_SIZE;
  const col = clamp(Math.floor((e.clientX - rect.left) / cs), 0, BOARD_SIZE - 1);
  const row = clamp(Math.floor((e.clientY - rect.top) / cs), 0, BOARD_SIZE - 1);

  // Move 1 step toward clicked cell (client intent; server authoritative)
  const me = board.players.find(p => p?.username === USERNAME) || board.players[0];
  if (!me?.pos) return;
  const [mx, my] = me.pos;
  const dx = col === mx ? 0 : (col > mx ? 1 : -1);
  const dy = row === my ? 0 : (row > my ? 1 : -1);
  handleMoveIntent(dx, dy);
});

// ===== Socket wiring =====
(function initSockets() {
  const socket = getSocket();
  const joinPayload = {
    roomCode: ROOM_CODE,
    playerId: PLAYER_ID,
    username: USERNAME,
  };

  const emitJoin = () => socket.emit(EVT.JOIN_GAME, joinPayload);
  if (socket.connected) emitJoin();
  socket.on('connect', emitJoin);

  // Server announces initial board when moderator starts the game
  socket.on(EVT.GAME_START, (payload) => {
    // payload example: { board: { size, players:[{id,username,pos},...], target:[x,y] } }
    if (payload?.board) board = payload.board;
    window.BOARD_STATE = board;
    draw();
  });

  // Every approved move -> broadcast with authoritative board
  socket.on(EVT.BOARD_UPDATE, (payload) => {
    if (payload?.board) board = payload.board;
    window.BOARD_STATE = board;
    draw();
  });

  // Keep a lightweight room mirror if you want (optional)
  socket.on(EVT.ROOM_STATE, (state) => {
    // If server includes player positions here, you could update board too
    if (state?.board) {
      board = state.board;
      window.BOARD_STATE = board;
      draw();
    }
  });
})();

// ===== First paint =====
if (canvas && ctx) {
  // fit once; if the game hasn't started yet, show an idle board/background
  fitCanvasDPR(canvas);
  draw();
  window.addEventListener('resize', () => draw());
}
