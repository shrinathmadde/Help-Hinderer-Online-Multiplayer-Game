// static/js/game/positionsState.js
export function createPositionsState(initial = {}) {
  // canonical shape persisted in Redis (server is authoritative)
  // size: number, R: [x,y], B: [x,y], star: [x,y], capturer: 'R'|'B'
  let state = {
    size: initial.size ?? 4,
    R: initial.R ?? [0, 0],
    B: initial.B ?? [3, 3],
    star: initial.star ?? [2, 1],
    capturer: initial.capturer ?? 'R',
  };

  const get = () => state;
  const set = (next) => { state = { ...state, ...next }; return state; };
  const setAll = (next) => { state = { ...next }; return state; };
  const roleOf = (playerId, idsMap) => {
    // prefer server-provided mapping: idsMap = { R: 'pidR', B: 'pidB' }
    if (idsMap?.R === playerId) return 'R';
    if (idsMap?.B === playerId) return 'B';
    return null;
  };

  return { get, set, setAll, roleOf };
}
