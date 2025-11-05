// Constants - 18 colors (9 light, 9 dark)
const COLORS = [
    // Light colors
    "#FF3333", "#33FF33", "#3333FF", "#FFFF33", "#FF33FF", "#33FFFF",
    "#FF9933", "#FF3399", "#99FF33",
    // Dark colors
    "#990000", "#009900", "#000099", "#996600", "#990099", "#009999",
    "#663300", "#660066", "#336600"
];

// Triangle geometry constants
const CANVAS_SIZE = 800;
const TRIANGLE_CENTER = CANVAS_SIZE / 2;
const TRIANGLE_RADIUS = 350;
const PADDLE_LENGTH = 120;
const PADDLE_WIDTH = 15;
const BALL_RADIUS = 8;

// Game state
let ws = null;
let currentScreen = 'menu';
let selectedColor = COLORS[0];
let lobbyCode = null;
let isCreator = false;
let gameState = null;
let myPlayerIndex = 0;
let myUsername = '';
let usedColors = [];
let keysPressed = {};

// Canvas
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    renderColorPickers();
    showScreen('menu');
    gameLoop(); // Start the game loop
});

function setupEventListeners() {
    // Menu buttons
    document.getElementById('createLobbyBtn').addEventListener('click', () => {
        showScreen('createScreen');
    });

    document.getElementById('joinLobbyBtn').addEventListener('click', () => {
        showScreen('joinScreen');
    });

    // Create lobby
    document.getElementById('confirmCreateBtn').addEventListener('click', createLobby);
    document.getElementById('backFromCreateBtn').addEventListener('click', () => {
        showScreen('menu');
    });

    // Join lobby
    document.getElementById('confirmJoinBtn').addEventListener('click', joinLobby);
    document.getElementById('backFromJoinBtn').addEventListener('click', () => {
        showScreen('menu');
    });

    // Lobby
    document.getElementById('startGameBtn').addEventListener('click', startGame);
    document.getElementById('leaveLobbyBtn').addEventListener('click', leaveLobby);

    // Game over
    document.getElementById('backToMenuBtn').addEventListener('click', () => {
        showScreen('menu');
        if (ws) {
            ws.close();
            ws = null;
        }
    });

    // Keyboard controls
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('keyup', handleKeyUp);
}

function renderColorPickers() {
    const createPicker = document.getElementById('createColorPicker');
    const joinPicker = document.getElementById('joinColorPicker');

    COLORS.forEach(color => {
        // Create screen color
        const div1 = document.createElement('div');
        div1.className = 'color-option';
        div1.style.backgroundColor = color;
        div1.dataset.color = color;
        div1.addEventListener('click', () => selectColor(color, 'create'));
        createPicker.appendChild(div1);

        // Join screen color
        const div2 = document.createElement('div');
        div2.className = 'color-option';
        div2.style.backgroundColor = color;
        div2.dataset.color = color;
        div2.addEventListener('click', () => selectColor(color, 'join'));
        joinPicker.appendChild(div2);
    });

    // Select first color by default
    selectColor(COLORS[0], 'create');
    selectColor(COLORS[0], 'join');
}

function selectColor(color, screen) {
    if (usedColors.includes(color) && screen === 'join') {
        return;
    }

    selectedColor = color;
    const picker = screen === 'create' ?
        document.getElementById('createColorPicker') :
        document.getElementById('joinColorPicker');

    picker.querySelectorAll('.color-option').forEach(opt => {
        if (opt.dataset.color === color) {
            opt.classList.add('selected');
        } else {
            opt.classList.remove('selected');
        }
    });
}

function showScreen(screen) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screen).classList.add('active');
    currentScreen = screen;
}

function showMessage(message, type = 'error') {
    const msgBox = document.getElementById('messageBox');
    msgBox.textContent = message;
    msgBox.className = `message-box show ${type}`;

    setTimeout(() => {
        msgBox.classList.remove('show');
    }, 3000);
}

function connectWebSocket() {
    return new Promise((resolve, reject) => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

        ws.onopen = () => {
            console.log('WebSocket connected');
            resolve();
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            reject(error);
        };

        ws.onmessage = (event) => {
            handleWebSocketMessage(JSON.parse(event.data));
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected');
        };
    });
}

function handleWebSocketMessage(message) {
    console.log('Received:', message);

    switch (message.type) {
        case 'lobby_created':
            lobbyCode = message.code;
            isCreator = true;
            document.getElementById('lobbyCode').textContent = lobbyCode;
            document.getElementById('startGameBtn').style.display = 'block';
            showScreen('lobbyScreen');
            break;

        case 'lobby_joined':
            lobbyCode = message.code;
            isCreator = false;
            document.getElementById('lobbyCode').textContent = lobbyCode;
            document.getElementById('startGameBtn').style.display = 'none';
            showScreen('lobbyScreen');
            break;

        case 'lobby_update':
            updateLobbyDisplay(message);
            break;

        case 'game_update':
            gameState = message;
            myPlayerIndex = message.your_index;
            renderGame();
            break;

        case 'game_over':
            showGameOver(message.winner);
            break;

        case 'error':
            showMessage(message.message, 'error');
            break;
    }
}

async function createLobby() {
    const username = document.getElementById('createUsername').value.trim();

    if (!username) {
        showMessage('Please enter a username', 'error');
        return;
    }

    myUsername = username;

    try {
        await connectWebSocket();
        ws.send(JSON.stringify({
            type: 'create_lobby',
            username: username,
            color: selectedColor
        }));
    } catch (error) {
        showMessage('Failed to connect to server', 'error');
    }
}

async function joinLobby() {
    const code = document.getElementById('joinCode').value.trim();
    const username = document.getElementById('joinUsername').value.trim();

    if (!code || code.length !== 7) {
        showMessage('Please enter a 7-digit lobby code', 'error');
        return;
    }

    if (!username) {
        showMessage('Please enter a username', 'error');
        return;
    }

    myUsername = username;

    try {
        await connectWebSocket();
        ws.send(JSON.stringify({
            type: 'join_lobby',
            code: code,
            username: username,
            color: selectedColor
        }));
    } catch (error) {
        showMessage('Failed to connect to server', 'error');
    }
}

function startGame() {
    if (ws) {
        ws.send(JSON.stringify({
            type: 'start_game'
        }));
    }
}

function leaveLobby() {
    if (ws) {
        ws.close();
        ws = null;
    }
    showScreen('menu');
}

function updateLobbyDisplay(message) {
    const playersList = document.getElementById('playersList');
    playersList.innerHTML = '';

    usedColors = [];

    for (let i = 0; i < 3; i++) {
        const player = message.players[i];

        if (player) {
            usedColors.push(player.color);

            const playerDiv = document.createElement('div');
            playerDiv.className = 'player-item';
            playerDiv.style.borderLeftColor = player.color;

            const colorDiv = document.createElement('div');
            colorDiv.className = 'player-color';
            colorDiv.style.backgroundColor = player.color;

            const nameDiv = document.createElement('div');
            nameDiv.className = 'player-name';
            nameDiv.textContent = player.username;
            if (player.is_bot) {
                nameDiv.innerHTML += ' <span class="player-bot">(Bot)</span>';
            }

            playerDiv.appendChild(colorDiv);
            playerDiv.appendChild(nameDiv);
            playersList.appendChild(playerDiv);
        } else {
            const emptyDiv = document.createElement('div');
            emptyDiv.className = 'empty-slot';
            emptyDiv.textContent = 'Empty Slot';
            playersList.appendChild(emptyDiv);
        }
    }

    if (message.game_started) {
        showScreen('gameScreen');
    }
}

function getTriangleVertices() {
    const vertices = [];
    for (let i = 0; i < 3; i++) {
        const angle = (i * 120 - 90) * Math.PI / 180;
        const x = TRIANGLE_CENTER + TRIANGLE_RADIUS * Math.cos(angle);
        const y = TRIANGLE_CENTER + TRIANGLE_RADIUS * Math.sin(angle);
        vertices.push({x, y});
    }
    return vertices;
}

function rotatePoint(x, y, angle, centerX, centerY) {
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);
    const dx = x - centerX;
    const dy = y - centerY;
    return {
        x: centerX + dx * cos - dy * sin,
        y: centerY + dx * sin + dy * cos
    };
}

function gameLoop() {
    // Send continuous paddle movement while keys are held
    if (currentScreen === 'gameScreen' && ws && ws.readyState === WebSocket.OPEN) {
        updatePaddleMovement();
    }
    renderGame();
    requestAnimationFrame(gameLoop);
}

function renderGame() {
    if (!gameState) return;

    // Clear canvas
    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Calculate rotation angle so current player is at bottom
    // Player 0 is at bottom (no rotation needed for them)
    // Player 1 needs -120° rotation
    // Player 2 needs +120° rotation
    const rotationAngle = -myPlayerIndex * 120 * Math.PI / 180;

    // Save context
    ctx.save();

    // Draw triangle
    const vertices = getTriangleVertices();
    ctx.strokeStyle = '#00ff00';
    ctx.lineWidth = 3;
    ctx.beginPath();
    for (let i = 0; i < 3; i++) {
        const v = rotatePoint(vertices[i].x, vertices[i].y, rotationAngle, TRIANGLE_CENTER, TRIANGLE_CENTER);
        if (i === 0) {
            ctx.moveTo(v.x, v.y);
        } else {
            ctx.lineTo(v.x, v.y);
        }
    }
    ctx.closePath();
    ctx.stroke();

    // Draw paddles
    gameState.players.forEach((player, index) => {
        if (player) {
            // Get edge endpoints for this player
            const edgeMap = {0: [1, 2], 1: [2, 0], 2: [0, 1]};
            const [v1Idx, v2Idx] = edgeMap[player.player_index];
            const v1 = vertices[v1Idx];
            const v2 = vertices[v2Idx];

            // Calculate paddle position along edge
            const paddleX = v1.x + (v2.x - v1.x) * player.paddle_position;
            const paddleY = v1.y + (v2.y - v1.y) * player.paddle_position;

            // Edge direction
            const edgeDx = v2.x - v1.x;
            const edgeDy = v2.y - v1.y;
            const edgeLen = Math.sqrt(edgeDx * edgeDx + edgeDy * edgeDy);
            const edgeUnitX = edgeDx / edgeLen;
            const edgeUnitY = edgeDy / edgeLen;

            // Paddle endpoints
            const halfLen = PADDLE_LENGTH / 2;
            const p1 = {
                x: paddleX - edgeUnitX * halfLen,
                y: paddleY - edgeUnitY * halfLen
            };
            const p2 = {
                x: paddleX + edgeUnitX * halfLen,
                y: paddleY + edgeUnitY * halfLen
            };

            // Rotate for current player's view
            const rp1 = rotatePoint(p1.x, p1.y, rotationAngle, TRIANGLE_CENTER, TRIANGLE_CENTER);
            const rp2 = rotatePoint(p2.x, p2.y, rotationAngle, TRIANGLE_CENTER, TRIANGLE_CENTER);

            // Draw paddle
            ctx.strokeStyle = player.color;
            ctx.lineWidth = PADDLE_WIDTH;
            ctx.lineCap = 'round';
            ctx.beginPath();
            ctx.moveTo(rp1.x, rp1.y);
            ctx.lineTo(rp2.x, rp2.y);
            ctx.stroke();
        }
    });

    // Draw ball
    if (gameState.ball) {
        const ball = rotatePoint(gameState.ball.x, gameState.ball.y, rotationAngle, TRIANGLE_CENTER, TRIANGLE_CENTER);

        // Ball glow
        const gradient = ctx.createRadialGradient(ball.x, ball.y, 0, ball.x, ball.y, BALL_RADIUS * 2);
        gradient.addColorStop(0, '#ffffff');
        gradient.addColorStop(0.5, '#ffff00');
        gradient.addColorStop(1, 'rgba(255, 136, 0, 0)');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(ball.x, ball.y, BALL_RADIUS * 2, 0, Math.PI * 2);
        ctx.fill();

        // Ball core
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(ball.x, ball.y, BALL_RADIUS, 0, Math.PI * 2);
        ctx.fill();
    }

    ctx.restore();

    // Update scoreboard
    updateScoreboard();
}

function updateScoreboard() {
    if (!gameState) return;

    const scoreBoard = document.getElementById('scoreBoard');
    scoreBoard.innerHTML = '';

    gameState.players.forEach((player, index) => {
        if (player) {
            const scoreItem = document.createElement('div');
            scoreItem.className = 'score-item';
            scoreItem.style.borderLeftColor = player.color;

            const colorDiv = document.createElement('div');
            colorDiv.className = 'player-color';
            colorDiv.style.backgroundColor = player.color;
            colorDiv.style.width = '20px';
            colorDiv.style.height = '20px';
            colorDiv.style.borderRadius = '50%';

            const nameDiv = document.createElement('div');
            nameDiv.className = 'score-name';
            nameDiv.textContent = player.username;

            const scoreValue = document.createElement('div');
            scoreValue.className = 'score-value';
            scoreValue.textContent = player.score;

            scoreItem.appendChild(colorDiv);
            scoreItem.appendChild(nameDiv);
            scoreItem.appendChild(scoreValue);
            scoreBoard.appendChild(scoreItem);
        }
    });
}

function handleKeyDown(event) {
    if (currentScreen !== 'gameScreen' || !ws) return;
    keysPressed[event.key] = true;
    event.preventDefault(); // Prevent arrow key scrolling
}

function handleKeyUp(event) {
    if (currentScreen !== 'gameScreen' || !ws) return;
    keysPressed[event.key] = false;
}

function updatePaddleMovement() {
    let direction = 0;

    if (keysPressed['ArrowLeft'] || keysPressed['a'] || keysPressed['A']) {
        direction = -1;
    }
    if (keysPressed['ArrowRight'] || keysPressed['d'] || keysPressed['D']) {
        direction = 1;
    }

    // Always send the current direction (0 means no movement)
    ws.send(JSON.stringify({
        type: 'paddle_move',
        direction: direction
    }));
}

function showGameOver(winner) {
    document.getElementById('winnerText').textContent = `${winner} WINS!`;
    showScreen('gameOverScreen');
}
