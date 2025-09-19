// static/js/shared/state.js
let _state = {};

export function getState() {
  return _state;
}

export function setState(next) {
  _state = structuredClone(next);
  return _state;
}

export function updateState(mutator) {
  // simple immutable-ish update with a shallow deep clone
  const draft = structuredClone(_state);
  mutator(draft);
  _state = draft;
  return _state;
}
