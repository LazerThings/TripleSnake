// Constants - 18 colors (9 light, 9 dark)
const COLORS = [
    // Light colors
    "#FF3333", "#33FF33", "#3333FF", "#FFFF33", "#FF33FF", "#33FFFF",
    "#FF9933", "#FF3399", "#99FF33",
    // Dark colors
    "#990000", "#009900", "#000099", "#996600", "#990099", "#009999",
    "#663300", "#660066", "#336600"
];

// Game state
let ws = null;
let currentScreen = 'menu';
let selectedColor = COLORS[0];
let lobbyCode = null;
let isCreator = false;
let gameState = null;
let playerDirection = { x: 0, y: 0 };
let myUsername = '';
let usedColors = [];

// Canvas
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    renderColorPickers();
    showScreen('menu');
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
    document.addEventListener('keydown', handleKeyPress);
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
        return; // Can't select used colors when joining
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

function updateJoinColorPicker(availableColors) {
    const picker = document.getElementById('joinColorPicker');
    picker.querySelectorAll('.color-option').forEach(opt => {
        const color = opt.dataset.color;
        if (!availableColors.includes(color)) {
            opt.classList.add('disabled');
        } else {
            opt.classList.remove('disabled');
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

    // Track used colors
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

    // If game started, show game screen
    if (message.game_started) {
        showScreen('gameScreen');
    }
}

function renderGame() {
    if (!gameState) return;

    // Clear canvas
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw border
    ctx.strokeStyle = '#444';
    ctx.lineWidth = 2;
    ctx.strokeRect(0, 0, canvas.width, canvas.height);

    // Draw grid
    ctx.strokeStyle = '#2a2a2a';
    ctx.lineWidth = 1;
    for (let i = 0; i < canvas.width; i += 40) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i, canvas.height);
        ctx.stroke();
    }
    for (let i = 0; i < canvas.height; i += 40) {
        ctx.beginPath();
        ctx.moveTo(0, i);
        ctx.lineTo(canvas.width, i);
        ctx.stroke();
    }

    // Draw snakes
    gameState.players.forEach((player, index) => {
        if (player && player.snake && player.snake.length > 0) {
            ctx.strokeStyle = player.color;
            ctx.lineWidth = 8;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';

            // Draw snake body
            ctx.beginPath();
            ctx.moveTo(player.snake[0].x, player.snake[0].y);
            for (let i = 1; i < player.snake.length; i++) {
                ctx.lineTo(player.snake[i].x, player.snake[i].y);
            }
            ctx.stroke();

            // Draw snake head
            const head = player.snake[0];
            ctx.fillStyle = player.color;
            ctx.beginPath();
            ctx.arc(head.x, head.y, 6, 0, Math.PI * 2);
            ctx.fill();

            // Draw glow effect on head
            const gradient = ctx.createRadialGradient(head.x, head.y, 0, head.x, head.y, 15);
            gradient.addColorStop(0, player.color + '88');
            gradient.addColorStop(1, player.color + '00');
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(head.x, head.y, 15, 0, Math.PI * 2);
            ctx.fill();
        }
    });

    // Draw ball
    if (gameState.ball) {
        const ball = gameState.ball;

        // Ball glow
        const gradient = ctx.createRadialGradient(ball.x, ball.y, 0, ball.x, ball.y, 20);
        gradient.addColorStop(0, '#ffffff');
        gradient.addColorStop(0.5, '#ffff00');
        gradient.addColorStop(1, '#ff8800');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(ball.x, ball.y, 12, 0, Math.PI * 2);
        ctx.fill();

        // Ball core
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(ball.x, ball.y, 6, 0, Math.PI * 2);
        ctx.fill();
    }

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

function handleKeyPress(event) {
    if (currentScreen !== 'gameScreen' || !ws) return;

    let direction = null;

    switch (event.key) {
        case 'ArrowUp':
        case 'w':
        case 'W':
            direction = { x: 0, y: -1 };
            event.preventDefault();
            break;
        case 'ArrowDown':
        case 's':
        case 'S':
            direction = { x: 0, y: 1 };
            event.preventDefault();
            break;
        case 'ArrowLeft':
        case 'a':
        case 'A':
            direction = { x: -1, y: 0 };
            event.preventDefault();
            break;
        case 'ArrowRight':
        case 'd':
        case 'D':
            direction = { x: 1, y: 0 };
            event.preventDefault();
            break;
    }

    if (direction) {
        playerDirection = direction;
        ws.send(JSON.stringify({
            type: 'player_input',
            direction: direction
        }));
    }
}

function showGameOver(winner) {
    document.getElementById('winnerText').textContent = `${winner} wins!`;
    showScreen('gameOverScreen');
}
