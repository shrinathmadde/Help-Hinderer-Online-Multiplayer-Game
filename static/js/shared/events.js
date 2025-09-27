// static/js/shared/events.js
export const EVT = Object.freeze({
  ROOM_STATE: 'room_state',
  GAME_START: 'game_start',
  BOARD_UPDATE: 'board_update',
  PLAYER_JOINED: 'player_joined',
  ROOM_FULL: 'room_full',
  PLAYER_READY: 'player_ready',
  START_GAME: 'start_game',
  JOIN_GAME: 'join_game',

  TRIAL_START: 'trial_start',   // -> { trial_idx, board, deadline_ts }
  TRIAL_END: 'trial_end',       // -> { trial_idx, reason: 'captured'|'timeout', board }
  GAME_OVER: 'game_over',       // -> { results }
});
