// static/js/pages/gamePage.js
import { EVT } from "../shared/events.js";
import { getSocket } from "../shared/socket.js";
import { BoardRenderer } from "../ui/boardRenderer.js";
import { attachMovement } from "../controllers/movementController.js";

const BOOT = window.GAME_BOOTSTRAP || {};
const ROOM_CODE = String(
  BOOT.roomCode || localStorage.getItem("room_code") || ""
).toUpperCase();
const USERNAME = String(
  BOOT.username || localStorage.getItem("username") || "Player"
).trim();
const PLAYER_ID = localStorage.getItem("player_id") || null;

// ---- minimal client state (positions-only) ----
const state = {
  size: 4,
  positions: { R: null, B: null },
  target: null,
  capturer: "R",
  turn: "R",
  myRole: "R",
  colors: { R: "#ff4d4f", B: "#4da6ff" },
};

function getSnapshot() {
  return { ...state, positions: { ...state.positions } };
}

let renderer = null;
let movement = null;

function log(...a) {
  // eslint-disable-next-line no-console
  console.debug("[gamePage]", ...a);
}

function ensureRendererSize(canvasEl) {
  const rect = canvasEl.getBoundingClientRect();
  // If the canvas renders with 0 size (before layout), ensure it has dimensions.
  if (rect.width === 0 || rect.height === 0) {
    if (!canvasEl.style.width)
      canvasEl.style.width = (canvasEl.width || 480) + "px";
    if (!canvasEl.style.height)
      canvasEl.style.height = (canvasEl.height || 480) + "px";
  }
}

function drawInitial() {
  if (!renderer) return;
  renderer.drawBoard();
  if (state.target) renderer.drawTarget(state.target);
  if (state.positions.R)
    renderer.setPlayer("R", state.colors.R, state.positions.R);
  if (state.positions.B)
    renderer.setPlayer("B", state.colors.B, state.positions.B);
}

(function init() {
  // Basic guards
  if (!ROOM_CODE) {
    console.error("[gamePage] Missing ROOM_CODE. Cannot continue.");
    return;
  }
  if (!PLAYER_ID) {
    alert("Missing player ID. Returning to home.");
    window.location.href = "/";
    return;
  }

  // ---- Canvas / Renderer init
  const canvasEl = document.getElementById("board");
  if (!canvasEl) {
    console.error(
      "[gamePage] #board canvas not found. Ensure this script runs after the canvas or use defer."
    );
    return;
  }
  ensureRendererSize(canvasEl);
  renderer = new BoardRenderer(canvasEl, { size: state.size });
  renderer.drawBoard();

  // ---- Socket wiring
  const socket = getSocket();

  // Avoid duplicate handlers if this module gets re-executed
  // socket.off("connect");
  // socket.off(EVT.GAME_START);
  // socket.off(EVT.BOARD_UPDATE);

  const joinPayload = {
    room_code: ROOM_CODE,
    player_id: PLAYER_ID,
    username: USERNAME,
  };

  const emitJoin = () => {
    log("Emitting JOIN_GAME", joinPayload);
    socket.emit(EVT.JOIN_GAME, joinPayload);
  };

  if (socket.connected) emitJoin();
  socket.on("connect", emitJoin);

  // GAME_START (authoritative initial snapshot)
  socket.on("room_state", (data) => {
    log("room_state:", data);

    // ---- Step 1: basic room players (optional for meta UI)
    // updatePlayersList(data.room.players) ... if needed

    // ---- Step 2: derive current trial from index
    const trialIndex = data?.current_trial_index;
    const trials = data?.trials;
    if (typeof trialIndex === "number" && Array.isArray(trials)) {
      const trial = trials[trialIndex];
      if (trial) {
        // update state from trial config
        state.size = trial.board_size || state.size; // fallback if missing
        state.positions = { ...trial.start_positions };
        state.target = trial.target;
        state.capturer = trial.capturer;
        state.turn = trial.turn || "R";

        // identify my role if possible
        const players = data.room?.players || {};
        const ids = {};
        for (const pid in players) {
          if (players[pid].role) {
            ids[players[pid].role] = pid;
          }
        }
        if (PLAYER_ID && (ids.R === PLAYER_ID || ids.B === PLAYER_ID)) {
          state.myRole = ids.R === PLAYER_ID ? "R" : "B";
        }

        // redraw everything from fresh state
        renderer?.clearAndRedrawAll?.();
        drawInitial();

        // attach movement controller
        if (movement) movement.destroy();
        movement = attachMovement({
          renderer,
          getSnapshot,
          roomCode: ROOM_CODE,
          playerId: PLAYER_ID,
        });
        if (movement)
          state.turn === state.myRole ? movement.unlock() : movement.lock();

        // label
        const label = document.getElementById("roomLabel");
        if (label && data.trials_total != null) {
          label.textContent = `${ROOM_CODE} — Trial ${trialIndex + 1}/${
            data.trials_total
          }`;
        }
      }
    } else {
      log("room_state: no trial data (game not started?)");
    }
  });

  // BOARD_UPDATE (authoritative incremental updates)
  socket.on(EVT.BOARD_UPDATE, (payload) => {
    log("BOARD_UPDATE payload:", payload);

    // positions
    if (payload?.positions) {
      const prevR = state.positions.R;
      const prevB = state.positions.B;
      const nextR = payload.positions.R ?? prevR;
      const nextB = payload.positions.B ?? prevB;

      if (renderer) {
        if (
          nextR &&
          (!prevR || prevR[0] !== nextR[0] || prevR[1] !== nextR[1])
        ) {
          if (prevR) renderer.updatePlayer?.("R", nextR);
          else renderer.setPlayer("R", state.colors.R, nextR);
        }
        if (
          nextB &&
          (!prevB || prevB[0] !== nextB[0] || prevB[1] !== nextB[1])
        ) {
          if (prevB) renderer.updatePlayer?.("B", nextB);
          else renderer.setPlayer("B", state.colors.B, nextB);
        }
      }

      state.positions.R = nextR;
      state.positions.B = nextB;
    }

    // target/star changes
    const nextTarget = payload?.target ?? payload?.star;
    if (nextTarget) {
      state.target = nextTarget;
      if (renderer) {
        renderer.clearAndRedrawAll?.();
        renderer.drawBoard?.();
        renderer.drawTarget(state.target);
        if (state.positions.R)
          renderer.setPlayer("R", state.colors.R, state.positions.R);
        if (state.positions.B)
          renderer.setPlayer("B", state.colors.B, state.positions.B);
      }
    }

    // turn changes
    if (payload?.turn) {
      state.turn = payload.turn;
      if (movement)
        state.turn === state.myRole ? movement.unlock() : movement.lock();
    }

    // win/terminal
    if (payload?.winner) {
      movement?.lock?.();
    }
  });
})();
