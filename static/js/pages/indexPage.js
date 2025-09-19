// static/js/pages/indexPage.js
import { EVT } from '../shared/events.js';
import { getSocket } from '../shared/socket.js';

document.addEventListener('DOMContentLoaded', function() {
    const createTab = document.getElementById('create-tab');
    const joinTab = document.getElementById('join-tab');
    const createContent = document.getElementById('create-content');
    const joinContent = document.getElementById('join-content');
    const createForm = document.getElementById('create-form');
    const joinForm = document.getElementById('join-form');
    const createUsername = document.getElementById('create-username');
    const roomCreatedDiv = document.getElementById('room-created');
    const roomCodeSpan = document.getElementById('room-code');
    const playersList = document.getElementById('players-list');
    const startGameBtn = document.getElementById('start-game');
    const copyCodeBtn = document.getElementById('copy-code');

    // Debug function
    function debug(message) {
        console.log(`[DEBUG] ${message}`);
    }

    debug('indexPage.js loaded');

    createTab.addEventListener('click', function() {
        createTab.classList.add('active');
        joinTab.classList.remove('active');
        createContent.classList.remove('hidden');
        joinContent.classList.add('hidden');
    });

    joinTab.addEventListener('click', function() {
        joinTab.classList.add('active');
        createTab.classList.remove('active');
        joinContent.classList.remove('hidden');
        createContent.classList.add('hidden');
    });

    let socket = null;  // global

    // Create game form handler (UNCHANGED LOGIC)
    createForm.addEventListener('submit', function(e) {
        e.preventDefault();
        debug('Create form submitted');

        if (!createUsername.value.trim()) {
            alert('Please enter your name');
            return;
        }

        // API call
        fetch('/api/create-room', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: createUsername.value.trim()
            })
        })
        .then(response => {
            // Check if the response is ok
            if (!response.ok) {
                console.error('Server response error:', response.status, response.statusText);
                return response.json().then(data => {
                    throw new Error(data.message || 'Unknown server error');
                }).catch(() => {
                    throw new Error('Server returned an error response: ' + response.status);
                });
            }
            return response.json();
        })
        .then(data => {
            // Handle success as before
            if (data.success) {
                // Show room created screen
                document.querySelector('.card').classList.add('hidden');
                roomCreatedDiv.classList.remove('hidden');
                roomCodeSpan.textContent = data.room_code;

                // Store player info in localStorage
                localStorage.setItem('player_id', data.player_id);
                localStorage.setItem('room_code', data.room_code);
                localStorage.setItem('username', createUsername.value.trim());
                localStorage.setItem('is_moderator', 'true');  // Mark as moderator

                // Connect to Socket.IO
                connectToSocketIO(data.room_code, data.player_id, true);

                // Add host to player list
                const li = document.createElement('li');
                li.textContent = createUsername.value.trim() + ' (You) (Moderator)';
                playersList.appendChild(li);
            } else {
                alert('Failed to create room: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error details:', error);
            alert('An error occurred: ' + error.message);
        });
    });

    // Join game form handler (UNCHANGED LOGIC)
    joinForm.addEventListener('submit', function(e) {
        e.preventDefault();
        debug('Join form submitted');

        const joinCode = document.getElementById('join-code');
        const joinUsername = document.getElementById('join-username');

        if (!joinCode.value.trim() || !joinUsername.value.trim()) {
            alert('Please enter both the game code and your name');
            return;
        }

        fetch('/api/join-room', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                room_code: joinCode.value.trim(),
                username: joinUsername.value.trim()
            })
        })
        .then(response => {
            if (!response.ok) {
                console.error('Server response error:', response.status, response.statusText);
                return response.json().then(data => {
                    throw new Error(data.message || 'Unknown server error');
                }).catch(() => {
                    throw new Error('Server returned an error response: ' + response.status);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                debug(`Joined room: ${data.room_code}, player ID: ${data.player_id}`);

                localStorage.setItem('player_id', data.player_id);
                localStorage.setItem('room_code', data.room_code);
                localStorage.setItem('username', joinUsername.value.trim());
                localStorage.setItem('is_moderator', 'false');  // Not a moderator

                // Redirect to game page
                window.location.href = '/game/' + data.room_code;
            } else {
                debug(`Failed to join room: ${data.message}`);
                alert('Failed to join room: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error joining room:', error);
            debug(`Error joining room: ${error.message}`);
            alert('An error occurred. Please try again.');
        });
    });

    // Only change here: use shared socket + event names;
    // Logic inside remains the SAME as your old file.
    function connectToSocketIO(roomCode, playerId, isModerator = false) {
        debug(`Connecting to Socket.IO, room: ${roomCode}, player: ${playerId}, moderator: ${isModerator}`);

        // use the shared singleton instead of io()
        socket = getSocket();

        socket.on('connect', function() {
            debug('Connected to Socket.IO');

            // use shared event name
            socket.emit(EVT.JOIN_GAME, {
                room_code: roomCode,
                player_id: playerId,
                is_moderator: isModerator
            });

            debug(`Sent ${EVT.JOIN_GAME} event for room ${roomCode}`);
        });

        socket.on('connect_error', function(error) {
            debug(`Socket connection error: ${error.message}`);
        });

        // use shared event names below
        socket.on(EVT.ROOM_STATE, function(data) {
            debug(`Room state received: ${JSON.stringify(data)}`);
            playersList.innerHTML = '';

            const players = data.room.players;
            for (const pid in players) {
                const player = players[pid];
                if (player.is_moderator) continue; // Skip moderator in player list

                const li = document.createElement('li');
                li.textContent = player.username;
                li.dataset.playerId = pid;
                playersList.appendChild(li);
            }

            // If 2 or more players have joined and this user is moderator, show start button
            if (Object.keys(players).filter(pid => !players[pid].is_moderator).length >= 2 && isModerator) {
                startGameBtn.classList.remove('hidden');
                startGameBtn.disabled = false;
            }
        });

        socket.on(EVT.PLAYER_JOINED, function(data) {
            debug(`Player joined event: ${JSON.stringify(data)}`);
            // Skip if this is for the moderator
            if (data.is_moderator) {
                debug('Skipping moderator in player list');
                return;
            }

            const existingPlayer = Array.from(playersList.children).find(li =>
                li.dataset.playerId === data.player_id
            );

            if (!existingPlayer) {
                const li = document.createElement('li');
                li.textContent = data.username;
                li.dataset.playerId = data.player_id;
                playersList.appendChild(li);

                // If 2 or more players have joined and this user is moderator, show start button
                if (playersList.children.length >= 2 && isModerator) {
                    startGameBtn.classList.remove('hidden');
                    startGameBtn.disabled = false;
                }
            }
        });

        socket.on('error', function(data) {
            debug(`Error received: ${JSON.stringify(data)}`);
            alert(`Error: ${data.message}`);
        });

        socket.on(EVT.GAME_START, function() {
            debug('Game start event received');
            window.location.href = '/game/' + roomCode;
        });

        if (startGameBtn) {
            startGameBtn.addEventListener('click', function() {
                debug('Start game button clicked');
                socket.emit(EVT.START_GAME, {
                    room_code: roomCode,
                    player_id: playerId
                });

                startGameBtn.disabled = true;
                startGameBtn.textContent = 'Starting game...';
            });
        }
    }

    if (copyCodeBtn) {
        copyCodeBtn.addEventListener('click', function() {
            const roomCode = roomCodeSpan.textContent.trim();
            if (!roomCode) {
                alert('No room code to copy!');
                return;
            }

            navigator.clipboard.writeText(roomCode)
                .then(() => {
                    copyCodeBtn.textContent = 'Copied!';
                    setTimeout(() => {
                        copyCodeBtn.textContent = 'Copy';
                    }, 2000);
                })
                .catch(err => {
                    console.error('Failed to copy:', err);
                    alert('Failed to copy room code.');
                });
        });
    }

});
