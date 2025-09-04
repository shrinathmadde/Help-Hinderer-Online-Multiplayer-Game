// static/js/game.js
document.addEventListener('DOMContentLoaded', function() {
    // Get room code from URL
    const pathParts = window.location.pathname.split('/');
    const ROOM_CODE = pathParts[pathParts.length - 1]; // Extract from URL path

    // Debug function
    function debug(message) {
        console.log(`[GAME-DEBUG] ${message}`);
    }

    debug(`Game.js loaded for room: ${ROOM_CODE}`);

    // Game constants
    const Direction = {
        UP: "UP",
        RIGHT: "RIGHT",
        DOWN: "DOWN",
        LEFT: "LEFT"
    };

    // Game UI colors - matching your Python UI colors
    const UI_COLORS = {
        p0Color: '#4CAF50',        // Player 0 (green in your UI)
        p1Color: '#2196F3',        // Player 1 (blue in your UI)
        targetColor: '#FF9800',    // Target (orange in your UI)
        wallColor: '#9E9E9E',      // Walls (gray in your UI)
        gridColor: '#444444',      // Grid lines
        disabledColor: '#9C27B0',  // Disabled blocks
        movableBoxColor: '#795548', // Movable boxes
        playerTurnIndicatorColor: '#FFEB3B' // Yellow indicator for current player
    };

    // Cell size in pixels
    const CELL_SIZE = 60;

    // Game state
    let gameState = null;
    let playerInfo = {
        id: localStorage.getItem('player_id'),
        roomCode: localStorage.getItem('room_code') || ROOM_CODE,
        username: localStorage.getItem('username'),
        playerNumber: null,
        isModerator: localStorage.getItem('is_moderator') === 'true',
        scores: [0, 0]
    };

    debug(`Player info: ${JSON.stringify(playerInfo)}`);

    // Canvas setup
    const canvas = document.getElementById('game-board');
    const ctx = canvas.getContext('2d');

    // Initial canvas drawing to confirm it's working
    if (canvas && ctx) {
        canvas.width = 480;
        canvas.height = 480;
        ctx.fillStyle = '#333';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = 'white';
        ctx.font = '24px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Connecting to game...', canvas.width/2, canvas.height/2);
        debug('Initial canvas setup completed');
    } else {
        debug('ERROR: Canvas or context not available');
    }

    // Game elements
    const waitingOverlay = document.getElementById('waiting-overlay');
    const resultOverlay = document.getElementById('result-overlay');
    const readyBtn = document.getElementById('ready-btn');
    const startGameBtn = document.getElementById('start-game-btn');
    const nextRoundBtn = document.getElementById('next-round-btn');
    const playersList = document.getElementById('players-list');
    const turnDisplay = document.getElementById('turn-display');
    const leaveGameBtn = document.getElementById('leave-game');
    const resultMessage = document.getElementById('result-message');
    const finalScore0 = document.getElementById('final-score-0');
    const finalScore1 = document.getElementById('final-score-1');

    // Show/hide moderator controls based on role
    if (playerInfo.isModerator) {
        // Show start game button for moderator
        if (startGameBtn) {
            startGameBtn.classList.remove('hidden');
            debug("Showing start game button for moderator");
        }
        // Hide ready button for moderator
        if (readyBtn) {
            readyBtn.classList.add('hidden');
            debug("Hiding ready button for moderator");
        }
    } else {
        // Hide start game button for regular players
        if (startGameBtn) {
            startGameBtn.classList.add('hidden');
            debug("Hiding start game button (not moderator)");
        }
        // Show ready button for regular players
        if (readyBtn) {
            readyBtn.classList.remove('hidden');
            debug("Showing ready button for regular player");
        }
    }

    // Movement buttons
    const moveUpBtn = document.getElementById('move-up');
    const moveLeftBtn = document.getElementById('move-left');
    const moveDownBtn = document.getElementById('move-down');
    const moveRightBtn = document.getElementById('move-right');
    const placeBlockBtn = document.getElementById('place-block');

    // Mobile controls
    const mobilePlaceBlockBtn = document.getElementById('mobile-place-block');
    const swipeArea = document.getElementById('swipe-area');

    // Socket.IO connection
    const socket = io();

    // Connect to Socket.IO
    socket.on('connect', function() {
        debug('Connected to Socket.IO');

        // Join the game room
        socket.emit('join_game', {
            room_code: playerInfo.roomCode,
            player_id: playerInfo.id,
            is_moderator: playerInfo.isModerator
        });
        debug(`Sent join_game event for room ${playerInfo.roomCode}`);
    });

    socket.on('connect_error', function(error) {
        debug(`Socket connection error: ${error.message}`);
    });

    // Handle room state
    socket.on('room_state', function(data) {
        debug(`Room state received: ${JSON.stringify(data)}`);

        // Set player info
        const players = data.room.players;
        for (let pid in players) {
            if (pid === playerInfo.id) {
                playerInfo.playerNumber = players[pid].player_number;
                debug(`Set playerNumber to ${playerInfo.playerNumber}`);
                break;
            }
        }

        // Populate players list
        updatePlayersList(data.room.players);

        // Update game state
        if (data.game_started) {
            // Game is already started, hide waiting overlay
            if (waitingOverlay) waitingOverlay.classList.add('hidden');
            debug("Game already started, waiting for updates");
        }

        // Update player names in the header
        updatePlayerNames(data.room.players);
    });

    // Start game button handler (for moderator)
    if (startGameBtn) {
        startGameBtn.addEventListener('click', function() {
            debug("Start game button clicked");
            socket.emit('start_game', {
                room_code: playerInfo.roomCode,
                player_id: playerInfo.id
            });

            startGameBtn.disabled = true;
            startGameBtn.textContent = 'Starting game...';
        });
    }

    // Handle player joined
    socket.on('player_joined', function(data) {
        debug(`Player joined: ${JSON.stringify(data)}`);

        // Add player to list if not already there
        if (!playersList) {
            debug("Player list element not found");
            return;
        }

        const existingPlayer = Array.from(playersList.children).find(li =>
            li.dataset.playerId === data.player_id
        );

        if (!existingPlayer) {
            const li = document.createElement('li');
            let playerText = data.username;

            if (data.player_id === playerInfo.id) {
                playerText += ' (You)';
            }

            if (data.is_moderator) {
                playerText += ' (Moderator)';
            }

            li.textContent = playerText;
            li.dataset.playerId = data.player_id;
            li.dataset.playerNumber = data.player_number;
            playersList.appendChild(li);
            debug(`Added player ${data.username} to players list`);
        }
    });

    // Handle room full event
    socket.on('room_full', function() {
        debug("Room full event received");
        // Enable ready button when room is full
        if (readyBtn && !playerInfo.isModerator) {
            readyBtn.disabled = false;
        }

        // Enable start button for moderator
        if (startGameBtn && playerInfo.isModerator) {
            startGameBtn.disabled = false;
        }
    });

    // Handle game start
    socket.on('game_start', function(data) {
        debug('Game started event received');
        if (waitingOverlay) waitingOverlay.classList.add('hidden');

        // Set up initial canvas size - will be updated when game state arrives
        if (canvas) {
            canvas.width = 480;  // Default width
            canvas.height = 480; // Default height

            // Clear the canvas with black background
            ctx.fillStyle = 'black';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Display loading message
            ctx.fillStyle = 'white';
            ctx.font = '24px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Game started! Waiting for first update...', canvas.width/2, canvas.height/2);
            debug("Canvas updated with game started message");
        }
    });

    // Handle error messages
    socket.on('error', function(data) {
        debug(`Error received: ${JSON.stringify(data)}`);
        alert(`Error: ${data.message}`);
    });

    // Handle game updates
    socket.on('game_update', function(data) {
        debug(`Game update received: ${JSON.stringify(data)}`);
        gameState = data;

        // Set canvas size based on field size if needed
        if (canvas && gameState.field_size && (canvas.width !== gameState.field_size[0] * CELL_SIZE ||
                                     canvas.height !== gameState.field_size[1] * CELL_SIZE)) {
            canvas.width = gameState.field_size[0] * CELL_SIZE;
            canvas.height = gameState.field_size[1] * CELL_SIZE;
            debug(`Canvas resized to ${canvas.width}x${canvas.height}`);
        }

        // Draw the game
        drawGame();

        // Update turn display
        updateTurnDisplay();

        // Update scores
        updateScores();
    });

    // Handle player scored
    socket.on('player_scored', function(data) {
        debug(`Player scored: ${JSON.stringify(data)}`);

        // Update scores
        playerInfo.scores = data.scores;
        updateScores();

        // Show result screen
        showResultScreen(data.player_number, data.result);
    });

    // Handle next block event
    socket.on('next_block', function(data) {
        debug(`Next block event received: ${JSON.stringify(data)}`);

        // Hide result overlay
        if (resultOverlay) resultOverlay.classList.add('hidden');

        // Update game state with new block data
        if (data.game_state) {
            gameState = data.game_state;
            drawGame();
            updateTurnDisplay();
            updateScores();
        }
    });

    // Ready button click
    if (readyBtn) {
        readyBtn.addEventListener('click', function() {
            debug("Ready button clicked");
            socket.emit('player_ready', {
                room_code: playerInfo.roomCode,
                player_id: playerInfo.id
            });

            readyBtn.disabled = true;
            readyBtn.textContent = 'Waiting for moderator to start...';
        });
    }

    // Next round button click
    if (nextRoundBtn) {
        nextRoundBtn.addEventListener('click', function() {
            debug("Next round button clicked");
            if (resultOverlay) resultOverlay.classList.add('hidden');

            // If this is the moderator, send next_block command
            if (playerInfo.isModerator) {
                debug("Sending next_block as moderator");
                socket.emit('next_block', {
                    room_code: playerInfo.roomCode,
                    player_id: playerInfo.id
                });
            }
        });
    }

    // Leave game button click
    if (leaveGameBtn) {
        leaveGameBtn.addEventListener('click', function() {
            debug("Leave game button clicked");
            if (confirm('Are you sure you want to leave the game?')) {
                window.location.href = '/';
            }
        });
    }

    // Movement controls
    if (moveUpBtn) {
        moveUpBtn.addEventListener('click', function() {
            debug("Move up button clicked");
            sendMoveCommand(Direction.UP);
        });
    }

    if (moveLeftBtn) {
        moveLeftBtn.addEventListener('click', function() {
            debug("Move left button clicked");
            sendMoveCommand(Direction.LEFT);
        });
    }

    if (moveDownBtn) {
        moveDownBtn.addEventListener('click', function() {
            debug("Move down button clicked");
            sendMoveCommand(Direction.DOWN);
        });
    }

    if (moveRightBtn) {
        moveRightBtn.addEventListener('click', function() {
            debug("Move right button clicked");
            sendMoveCommand(Direction.RIGHT);
        });
    }

    if (placeBlockBtn) {
        placeBlockBtn.addEventListener('click', function() {
            debug("Place block button clicked");
            sendSpecialCommand("PLACE_BLOCK");
        });
    }

    if (mobilePlaceBlockBtn) {
        mobilePlaceBlockBtn.addEventListener('click', function() {
            debug("Mobile place block button clicked");
            sendSpecialCommand("PLACE_BLOCK");
        });
    }

    // Set up mobile swipe controls
    if (swipeArea) {
        debug("Setting up swipe controls");
        setupSwipeControls();
    }

    // Keyboard controls with key down/up tracking
    document.addEventListener('keydown', function(e) {
        if (!gameState) return;

        // Don't handle repeated keydown events (key held down)
        if (e.repeat) return;

        // Send key down event to server
        switch (e.key) {
            case 'ArrowUp':
            case 'w':
                debug("Up key pressed");
                socket.emit('key_down', {
                    room_code: playerInfo.roomCode,
                    player_id: playerInfo.id,
                    key: 'up'
                });
                sendMoveCommand(Direction.UP);
                break;
            case 'ArrowRight':
            case 'd':
                debug("Right key pressed");
                socket.emit('key_down', {
                    room_code: playerInfo.roomCode,
                    player_id: playerInfo.id,
                    key: 'right'
                });
                sendMoveCommand(Direction.RIGHT);
                break;
            case 'ArrowDown':
            case 's':
                debug("Down key pressed");
                socket.emit('key_down', {
                    room_code: playerInfo.roomCode,
                    player_id: playerInfo.id,
                    key: 'down'
                });
                sendMoveCommand(Direction.DOWN);
                break;
            case 'ArrowLeft':
            case 'a':
                debug("Left key pressed");
                socket.emit('key_down', {
                    room_code: playerInfo.roomCode,
                    player_id: playerInfo.id,
                    key: 'left'
                });
                sendMoveCommand(Direction.LEFT);
                break;
            case ' ':  // Space key
                debug("Space key pressed");
                socket.emit('key_down', {
                    room_code: playerInfo.roomCode,
                    player_id: playerInfo.id,
                    key: 'space'
                });
                sendSpecialCommand("PLACE_BLOCK");
                break;
            case 'Enter':
                debug("Enter key pressed");
                socket.emit('key_down', {
                    room_code: playerInfo.roomCode,
                    player_id: playerInfo.id,
                    key: 'return'
                });

                // If moderator and result screen showing, handle next block
                if (playerInfo.isModerator && resultOverlay && !resultOverlay.classList.contains('hidden')) {
                    nextRoundBtn.click();
                }
                break;
        }
    });

    document.addEventListener('keyup', function(e) {
        if (!gameState) return;

        // Send key up event to server
        switch (e.key) {
            case 'ArrowUp':
            case 'w':
                socket.emit('key_up', {
                    room_code: playerInfo.roomCode,
                    player_id: playerInfo.id,
                    key: 'up'
                });
                break;
            case 'ArrowRight':
            case 'd':
                socket.emit('key_up', {
                    room_code: playerInfo.roomCode,
                    player_id: playerInfo.id,
                    key: 'right'
                });
                break;
            case 'ArrowDown':
            case 's':
                socket.emit('key_up', {
                    room_code: playerInfo.roomCode,
                    player_id: playerInfo.id,
                    key: 'down'
                });
                break;
            case 'ArrowLeft':
            case 'a':
                socket.emit('key_up', {
                    room_code: playerInfo.roomCode,
                    player_id: playerInfo.id,
                    key: 'left'
                });
                break;
            case ' ':  // Space key
                socket.emit('key_up', {
                    room_code: playerInfo.roomCode,
                    player_id: playerInfo.id,
                    key: 'space'
                });
                break;
            case 'Enter':
                socket.emit('key_up', {
                    room_code: playerInfo.roomCode,
                    player_id: playerInfo.id,
                    key: 'return'
                });
                break;
        }
    });

    // Set up mobile swipe controls
    function setupSwipeControls() {
        let touchStartX = 0;
        let touchStartY = 0;

        swipeArea.addEventListener('touchstart', function(e) {
            touchStartX = e.changedTouches[0].screenX;
            touchStartY = e.changedTouches[0].screenY;
        }, false);

        swipeArea.addEventListener('touchend', function(e) {
            const touchEndX = e.changedTouches[0].screenX;
            const touchEndY = e.changedTouches[0].screenY;

            handleSwipe(touchStartX, touchStartY, touchEndX, touchEndY);
        }, false);
    }

    function handleSwipe(startX, startY, endX, endY) {
        const minSwipeDistance = 50;  // Minimum distance for a swipe

        const diffX = endX - startX;
        const diffY = endY - startY;

        // Check if swipe distance is significant enough
        if (Math.abs(diffX) < minSwipeDistance && Math.abs(diffY) < minSwipeDistance) {
            return;  // Not a swipe
        }

        // Determine direction by greatest difference
        if (Math.abs(diffX) > Math.abs(diffY)) {
            // Horizontal swipe
            if (diffX > 0) {
                debug("Swipe right detected");
                sendMoveCommand(Direction.RIGHT);
            } else {
                debug("Swipe left detected");
                sendMoveCommand(Direction.LEFT);
            }
        } else {
            // Vertical swipe
            if (diffY > 0) {
                debug("Swipe down detected");
                sendMoveCommand(Direction.DOWN);
            } else {
                debug("Swipe up detected");
                sendMoveCommand(Direction.UP);
            }
        }
    }

    // Send movement command to server
    function sendMoveCommand(direction) {
        if (!gameState || !isPlayerTurn()) {
            debug(`Cannot move: gameState=${!!gameState}, isPlayerTurn=${isPlayerTurn()}`);
            return;
        }

        debug(`Sending move command: ${direction}`);
        socket.emit('player_move', {
            room_code: playerInfo.roomCode,
            player_id: playerInfo.id,
            direction: direction,
            special: null
        });
    }

    // Send special command to server
    function sendSpecialCommand(special) {
        if (!gameState || !isPlayerTurn()) {
            debug(`Cannot use special: gameState=${!!gameState}, isPlayerTurn=${isPlayerTurn()}`);
            return;
        }

        debug(`Sending special command: ${special}`);
        socket.emit('player_move', {
            room_code: playerInfo.roomCode,
            player_id: playerInfo.id,
            direction: null,
            special: special
        });
    }

    // Check if it's the current player's turn
    function isPlayerTurn() {
        return gameState && gameState.player_turn === playerInfo.playerNumber;
    }

    // Update the list of players in the waiting room
    function updatePlayersList(players) {
        if (!playersList) {
            debug("Players list element not found");
            return;
        }

        debug(`Updating players list: ${JSON.stringify(players)}`);
        playersList.innerHTML = ''; // Clear current list

        for (const pid in players) {
            const player = players[pid];
            const li = document.createElement('li');

            let displayText = player.username || `Player ${player.player_number + 1}`;

            if (pid === playerInfo.id) {
                displayText += ' (You)';
            }

            if (player.is_moderator) {
                displayText += ' (Moderator)';
            }

            li.textContent = displayText;
            li.dataset.playerId = pid;
            li.dataset.playerNumber = player.player_number;
            playersList.appendChild(li);
        }

        // If moderator and enough players, enable start button
        if (playerInfo.isModerator && startGameBtn) {
            const playerCount = Object.values(players).filter(p => !p.is_moderator).length;
            if (playerCount >= 2) {
                startGameBtn.disabled = false;
                debug("Enabling start button - enough players joined");
            }
        }
    }

    // Update the player names in the header
    function updatePlayerNames(players) {
        const player0Name = document.getElementById('player-0-name');
        const player1Name = document.getElementById('player-1-name');

        if (!player0Name || !player1Name) {
            debug("Player name elements not found");
            return;
        }

        debug("Updating player names in header");
        for (let playerId in players) {
            const player = players[playerId];
            const isCurrentPlayer = playerId === playerInfo.id;
            const modIndicator = player.is_moderator ? ' (Mod)' : '';

            if (player.player_number === 0) {
                player0Name.textContent = (player.username || 'Player 1') +
                                        (isCurrentPlayer ? ' (You)' : '') +
                                        modIndicator;
                // Update color to match the UI_COLORS
                const playerColor0 = document.querySelector('.player-0 .player-color');
                if (playerColor0) {
                    playerColor0.style.backgroundColor = UI_COLORS.p0Color;
                }
                debug(`Updated player 0 name: ${player0Name.textContent}`);
            } else if (player.player_number === 1) {
                player1Name.textContent = (player.username || 'Player 2') +
                                        (isCurrentPlayer ? ' (You)' : '') +
                                        modIndicator;
                // Update color to match the UI_COLORS
                const playerColor1 = document.querySelector('.player-1 .player-color');
                if (playerColor1) {
                    playerColor1.style.backgroundColor = UI_COLORS.p1Color;
                }
                debug(`Updated player 1 name: ${player1Name.textContent}`);
            }
        }
    }

    // Update the turn display
    function updateTurnDisplay() {
        if (!gameState || !turnDisplay) {
            return;
        }

        // Extract state from enum string format (like "P0TURN" or "P1TURN")
        const stateStr = gameState.engine_state;
        debug(`Updating turn display for state: ${stateStr}`);

        const player0Elem = document.querySelector('.player-0');
        const player1Elem = document.querySelector('.player-1');

        if (stateStr.includes('P0TURN')) {
            turnDisplay.textContent = "Player 1's turn";
            if (player0Elem) player0Elem.classList.add('active-turn');
            if (player1Elem) player1Elem.classList.remove('active-turn');
        } else if (stateStr.includes('P1TURN')) {
            turnDisplay.textContent = "Player 2's turn";
            if (player1Elem) player1Elem.classList.add('active-turn');
            if (player0Elem) player0Elem.classList.remove('active-turn');
        } else if (stateStr.includes('RESULT')) {
            turnDisplay.textContent = "Round complete";
            if (player0Elem) player0Elem.classList.remove('active-turn');
            if (player1Elem) player1Elem.classList.remove('active-turn');
        } else if (stateStr.includes('WAITSTART')) {
            turnDisplay.textContent = "Waiting to start";
            if (player0Elem) player0Elem.classList.remove('active-turn');
            if (player1Elem) player1Elem.classList.remove('active-turn');
        } else {
            turnDisplay.textContent = stateStr.replace('_', ' ');
            if (player0Elem) player0Elem.classList.remove('active-turn');
            if (player1Elem) player1Elem.classList.remove('active-turn');
        }
        debug(`Turn display updated to: ${turnDisplay.textContent}`);
    }

    // Update the scores display
    function updateScores() {
        if (!gameState || !gameState.scores) {
            debug("No scores to update");
            return;
        }

        const player0Score = document.getElementById('player-0-score');
        const player1Score = document.getElementById('player-1-score');

        if (player0Score) player0Score.textContent = gameState.scores[0];
        if (player1Score) player1Score.textContent = gameState.scores[1];
        debug(`Updated scores: ${gameState.scores[0]} - ${gameState.scores[1]}`);
    }

    // Show the result screen
    function showResultScreen(winnerNumber, resultType) {
        if (!resultOverlay || !resultMessage || !finalScore0 || !finalScore1) {
            debug("Result overlay elements not found");
            return;
        }

        debug(`Showing result screen: winner=${winnerNumber}, result=${resultType}`);

        if (winnerNumber === 0) {
            resultMessage.textContent = "Player 1 scored!";
        } else if (winnerNumber === 1) {
            resultMessage.textContent = "Player 2 scored!";
        } else {
            resultMessage.textContent = "Round ended in a draw";
        }

        // Update final scores
        finalScore0.textContent = gameState.scores[0];
        finalScore1.textContent = gameState.scores[1];

        // Show the overlay
        resultOverlay.classList.remove('hidden');

        // Update button text based on role
        if (nextRoundBtn) {
            if (playerInfo.isModerator) {
                nextRoundBtn.textContent = "Start Next Round";
                nextRoundBtn.disabled = false;
            } else {
                nextRoundBtn.textContent = "Wait for Next Round";
                nextRoundBtn.disabled = true;
            }
        }
    }

    // Draw the game board based on the current state
    function drawGame() {
        if (!gameState || !canvas || !ctx) {
            debug("Cannot draw game: missing gameState or canvas");
            return;
        }

        // Clear the canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        debug("Drawing game state");

        // Draw the grid
        drawGrid();

        // Draw walls
        drawWalls();

        // Draw disabled blocks
        drawDisabledBlocks();

        // Draw player-placed blocks
        drawPlayerPlacedBlocks();

        // Draw movable boxes
        drawMovableBoxes();

        // Draw target
        drawTarget();

        // Draw players
        drawPlayers();
    }

    // Draw the grid
    function drawGrid() {
        if (!gameState || !gameState.field_size) {
            debug("Cannot draw grid: missing field size");
            return;
        }

        const fieldSize = gameState.field_size;
        const width = fieldSize[0] * CELL_SIZE;
        const height = fieldSize[1] * CELL_SIZE;

        ctx.strokeStyle = UI_COLORS.gridColor;
        ctx.lineWidth = 1;

        // Draw vertical lines
        for (let x = 0; x <= fieldSize[0]; x++) {
            ctx.beginPath();
            ctx.moveTo(x * CELL_SIZE, 0);
            ctx.lineTo(x * CELL_SIZE, height);
            ctx.stroke();
        }

        // Draw horizontal lines
        for (let y = 0; y <= fieldSize[1]; y++) {
            ctx.beginPath();
            ctx.moveTo(0, y * CELL_SIZE);
            ctx.lineTo(width, y * CELL_SIZE);
            ctx.stroke();
        }
    }

    // Draw the walls
    function drawWalls() {
        if (!gameState.wall_locations) return;

        ctx.strokeStyle = UI_COLORS.wallColor;
        ctx.lineWidth = 4;

        for (const wall of gameState.wall_locations) {
            // Each wall is a 3-tuple (x, y, direction)
            const x = wall[0];
            const y = wall[1];
            const direction = wall[2];

            const centerX = (x + 0.5) * CELL_SIZE;
            const centerY = (y + 0.5) * CELL_SIZE;
            const halfSize = CELL_SIZE / 2;

            ctx.beginPath();

            switch (direction) {
                case Direction.UP:
                    // Top wall
                    ctx.moveTo(centerX - halfSize, centerY - halfSize);
                    ctx.lineTo(centerX + halfSize, centerY - halfSize);
                    break;
                case Direction.RIGHT:
                    // Right wall
                    ctx.moveTo(centerX + halfSize, centerY - halfSize);
                    ctx.lineTo(centerX + halfSize, centerY + halfSize);
                    break;
                case Direction.DOWN:
                    // Bottom wall
                    ctx.moveTo(centerX - halfSize, centerY + halfSize);
                    ctx.lineTo(centerX + halfSize, centerY + halfSize);
                    break;
                case Direction.LEFT:
                    // Left wall
                    ctx.moveTo(centerX - halfSize, centerY - halfSize);
                    ctx.lineTo(centerX - halfSize, centerY + halfSize);
                    break;
            }

            ctx.stroke();
        }
    }

    // Draw the disabled blocks
    function drawDisabledBlocks() {
        if (!gameState.disabled_blocks) return;

        ctx.lineWidth = 3;
        ctx.strokeStyle = UI_COLORS.disabledColor;

        for (const block of gameState.disabled_blocks) {
            const x = block[0];
            const y = block[1];

            const centerX = (x + 0.5) * CELL_SIZE;
            const centerY = (y + 0.5) * CELL_SIZE;
            const halfSize = CELL_SIZE * 0.4;

            // Draw an X for disabled blocks
            ctx.beginPath();
            ctx.moveTo(centerX - halfSize, centerY - halfSize);
            ctx.lineTo(centerX + halfSize, centerY + halfSize);
            ctx.stroke();

            ctx.beginPath();
            ctx.moveTo(centerX + halfSize, centerY - halfSize);
            ctx.lineTo(centerX - halfSize, centerY + halfSize);
            ctx.stroke();
        }
    }

    // Draw the player-placed blocks
    function drawPlayerPlacedBlocks() {
        if (!gameState.player_placed_blocks) return;

        for (const [posStr, playerNumber] of Object.entries(gameState.player_placed_blocks)) {
            // Parse the position string "(x, y)" or "x,y"
            let x, y;

            // Handle different formats of position string
            if (posStr.includes(',')) {
                const coords = posStr.replace(/[()[\]]/g, '').split(',').map(Number);
                x = coords[0];
                y = coords[1];
            }

            if (isNaN(x) || isNaN(y)) continue;

            const centerX = (x + 0.5) * CELL_SIZE;
            const centerY = (y + 0.5) * CELL_SIZE;
            const size = CELL_SIZE * 0.7;

            // Use player's color with transparency
            ctx.globalAlpha = 0.5;
            ctx.fillStyle = playerNumber === 0 ? UI_COLORS.p0Color : UI_COLORS.p1Color;

            // Draw a square block
            ctx.fillRect(centerX - size/2, centerY - size/2, size, size);

            // Reset transparency
            ctx.globalAlpha = 1.0;
        }
    }

    // Draw the movable boxes
    function drawMovableBoxes() {
        if (!gameState.movable_boxes_positions) return;

        ctx.fillStyle = UI_COLORS.movableBoxColor;

        for (const box of gameState.movable_boxes_positions) {
            const x = box[0];
            const y = box[1];

            const centerX = (x + 0.5) * CELL_SIZE;
            const centerY = (y + 0.5) * CELL_SIZE;
            const size = CELL_SIZE * 0.8;

            // Draw a box
            ctx.fillRect(centerX - size/2, centerY - size/2, size, size);
        }
    }

    // Draw the target
    function drawTarget() {
        if (!gameState.target_position) return;

        const x = gameState.target_position[0];
        const y = gameState.target_position[1];

        const centerX = (x + 0.5) * CELL_SIZE;
        const centerY = (y + 0.5) * CELL_SIZE;
        const outerRadius = CELL_SIZE * 0.45;
        const innerRadius = outerRadius * 0.4;

        // Draw a star (similar to your PsychoPy shape)
        ctx.fillStyle = UI_COLORS.targetColor;
        drawStar(centerX, centerY, 5, outerRadius, innerRadius);
    }

    // Draw a star shape
    function drawStar(cx, cy, spikes, outerRadius, innerRadius) {
        let rot = Math.PI / 2 * 3;
        let x = cx;
        let y = cy;
        const step = Math.PI / spikes;

        ctx.beginPath();
        ctx.moveTo(cx, cy - outerRadius);

        for (let i = 0; i < spikes; i++) {
            x = cx + Math.cos(rot) * outerRadius;
            y = cy + Math.sin(rot) * outerRadius;
            ctx.lineTo(x, y);
            rot += step;

            x = cx + Math.cos(rot) * innerRadius;
            y = cy + Math.sin(rot) * innerRadius;
            ctx.lineTo(x, y);
            rot += step;
        }

        ctx.lineTo(cx, cy - outerRadius);
        ctx.closePath();
        ctx.fill();
    }

    // Draw the players
    function drawPlayers() {
        // Draw Player 0
        if (gameState.p0_position) {
            const x0 = gameState.p0_position[0];
            const y0 = gameState.p0_position[1];

            const centerX0 = (x0 + 0.5) * CELL_SIZE;
            const centerY0 = (y0 + 0.5) * CELL_SIZE;
            const radius0 = CELL_SIZE * 0.4;

            // Draw player circle
            ctx.fillStyle = UI_COLORS.p0Color;
            ctx.beginPath();
            ctx.arc(centerX0, centerY0, radius0, 0, 2 * Math.PI);
            ctx.fill();

            // Draw turn indicator if it's player 0's turn
            if (gameState.player_turn === 0) {
                ctx.fillStyle = UI_COLORS.playerTurnIndicatorColor;
                ctx.beginPath();
                ctx.arc(centerX0, centerY0, radius0 * 0.5, 0, 2 * Math.PI);
                ctx.fill();
            }
        }

        // Draw Player 1
        if (gameState.p1_position) {
            const x1 = gameState.p1_position[0];
            const y1 = gameState.p1_position[1];

            const centerX1 = (x1 + 0.5) * CELL_SIZE;
            const centerY1 = (y1 + 0.5) * CELL_SIZE;
            const radius1 = CELL_SIZE * 0.4;

            // Draw player circle
            ctx.fillStyle = UI_COLORS.p1Color;
            ctx.beginPath();
            ctx.arc(centerX1, centerY1, radius1, 0, 2 * Math.PI);
            ctx.fill();

            // Draw turn indicator if it's player 1's turn
            if (gameState.player_turn === 1) {
                ctx.fillStyle = UI_COLORS.playerTurnIndicatorColor;
                ctx.beginPath();
                ctx.arc(centerX1, centerY1, radius1 * 0.5, 0, 2 * Math.PI);
                ctx.fill();
            }
        }
    }
});