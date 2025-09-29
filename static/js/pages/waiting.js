document.addEventListener('DOMContentLoaded', function () {
  const roomCode = document.body.dataset.roomCode;
  const playerId = localStorage.getItem('player_id');
  const username = localStorage.getItem('username');

  const playersList = document.getElementById('players-list');
  const startGameBtn = document.getElementById('start-game-btn');
  const readyBtn = document.getElementById('ready-btn');
  const debugArea = document.getElementById('debug-area');

  // Debug helper
  function debug(message) {
    // eslint-disable-next-line no-console
    console.log(message);
    if (!debugArea) return;
    const time = new Date().toLocaleTimeString();
    debugArea.textContent += `[${time}] ${message}\n`;
    debugArea.scrollTop = debugArea.scrollHeight;
  }

  // Toggle debug area with Ctrl + D
  document.addEventListener('keydown', function (e) {
    if (e.key === 'd' && e.ctrlKey) {
      debugArea.classList.toggle('hidden');
    }
  });

  // If "?debug" in URL, show debug area
  if (window.location.search.includes('debug')) {
    debugArea.classList.remove('hidden');
  }

  debug(`Room code: ${roomCode}`);
  debug(`Player ID: ${playerId}`);
  debug(`Username: ${username}`);

  // Guard: require player identity
  if (!playerId || !username) {
    alert('Missing player information. Returning to home page.');
    window.location.href = '/';
    return;
  }

  // Persist current room code
  localStorage.setItem('room_code', roomCode);

  // Connect to Socket.IO
  const socket = io();

  // Prevent duplicate handlers if this script runs twice somehow
  socket.off('connect');
  socket.off('connect_error');
  socket.off('room_state');
  socket.off('player_joined');
  socket.off('game_start');
  socket.off('error');

  socket.on('connect', function () {
    debug('Connected to Socket.IO');

    // Join the game room
    socket.emit('join_game', {
      room_code: roomCode,
      player_id: playerId
    });

    debug(`Sent join_game event for room ${roomCode}`);
  });

  socket.on('connect_error', function (error) {
    debug(`Connection error: ${error.message}`);
  });

  // Full room state (snapshot)
  socket.on('room_state', function (data) {
    debug(`Room state received: ${JSON.stringify(data)}`);

    // Update players list
    updatePlayersList(data.room.players);

  });

  // Incremental: a player joined
  socket.on('player_joined', function (data) {
    debug(`Player joined: ${JSON.stringify(data)}`);

    // Avoid duplicates
    const existing = document.querySelector(`[data-player-id="${data.player_id}"]`);
    if (!existing) {
      const el = document.createElement('div');
      el.classList.add('player-item');
      el.dataset.playerId = data.player_id;
      el.textContent = data.username + (data.player_id === playerId ? ' (You)' : '');
      playersList.appendChild(el);
    }
  });

  // Game start signal
  socket.on('game_start', function () {
    debug('Game is starting, redirecting to game page');
    window.location.href = '/game/' + roomCode;
  });

  // Generic error messages from server
  socket.on('error', function (data) {
    debug(`Error received: ${JSON.stringify(data)}`);
    alert(`Error: ${data.message}`);
  });

  // “I’m Ready” button
  readyBtn.addEventListener('click', function () {
    debug('Sending player_ready event');
    socket.emit('player_ready', {
      room_code: roomCode,
      player_id: playerId
    });
    readyBtn.disabled = true;
    readyBtn.textContent = 'Ready ✓';
  });

  // Start Game (moderator only)

  // Helpers
  function updatePlayersList(players) {
    debug(`Updating players list: ${JSON.stringify(players)}`);
    playersList.innerHTML = '';

    let count = 0;
    for (const pid in players) {
      const player = players[pid];
      debug(`Processing player: ${JSON.stringify(player)}`);

      // Skip moderator in the visible list
      if (player.moderator) {
        debug('Skipping moderator in display');
        continue;
      }

      count++;
      const item = document.createElement('div');
      item.classList.add('player-item');
      item.dataset.playerId = pid;
      item.textContent = player.username + (pid === playerId ? ' (You)' : '');
      playersList.appendChild(item);
    }

    if (count === 0) {
      const empty = document.createElement('div');
      empty.classList.add('player-item');
      empty.textContent = 'Waiting for players to join...';
      playersList.appendChild(empty);
    }
  }
});
