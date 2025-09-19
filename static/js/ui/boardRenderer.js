// static/js/ui/boardRenderer.js
// Renders the current board state into a container.
// onMove(move) will be called when the local player makes a move.
export function renderBoard(boardState, container, onMove) {
  if (!container) return;

  // simple placeholder; swap with your real board UI
  container.innerHTML = '';
  const pre = document.createElement('pre');
  pre.style.whiteSpace = 'pre-wrap';
  pre.textContent = JSON.stringify(boardState ?? { status: 'waiting for start' }, null, 2);
  container.appendChild(pre);

  // Example “make a move” button to demonstrate the API
  const btn = document.createElement('button');
  btn.textContent = 'Make Example Move';
  btn.addEventListener('click', () => onMove?.({ type: 'example_move' }));
  container.appendChild(btn);
}
