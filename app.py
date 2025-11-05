import asyncio
import random
import string
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from quart import Quart, render_template, websocket, jsonify
import json

app = Quart(__name__)

# Color palette (18 colors)
COLORS = [
    "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF",
    "#FF8000", "#8000FF", "#00FF80", "#FF0080", "#80FF00", "#0080FF",
    "#FF4040", "#40FF40", "#4040FF", "#FFAA00", "#AA00FF", "#00AAFF"
]

BOT_NAMES = ["Robot", "Botsy"]

@dataclass
class Player:
    username: str
    color: str
    is_bot: bool = False
    ws: Optional[object] = None
    score: int = 0
    snake: List[Dict[str, float]] = field(default_factory=list)
    direction: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})

@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float

@dataclass
class Lobby:
    code: str
    players: List[Optional[Player]]
    creator_ws: object
    game_started: bool = False
    ball: Optional[Ball] = None
    last_update: float = field(default_factory=time.time)

# Global state
lobbies: Dict[str, Lobby] = {}
ws_to_lobby: Dict[object, str] = {}

def generate_lobby_code() -> str:
    """Generate a unique 7-digit lobby code"""
    while True:
        code = ''.join(random.choices(string.digits, k=7))
        if code not in lobbies:
            return code

def get_available_colors(lobby: Lobby) -> List[str]:
    """Get list of colors not used by current players"""
    used_colors = {p.color for p in lobby.players if p is not None}
    return [c for c in COLORS if c not in used_colors]

def create_bot(lobby: Lobby) -> Optional[Player]:
    """Create a bot player with random name and available color"""
    available_colors = get_available_colors(lobby)
    if not available_colors:
        return None

    # Choose bot name that isn't already taken
    used_names = {p.username for p in lobby.players if p is not None}
    available_bot_names = [name for name in BOT_NAMES if name not in used_names]

    if not available_bot_names:
        # If both bot names are taken, use Robot1, Robot2, etc.
        bot_name = f"Robot{random.randint(1, 99)}"
    else:
        bot_name = random.choice(available_bot_names)

    return Player(
        username=bot_name,
        color=random.choice(available_colors),
        is_bot=True,
        ws=None
    )

def initialize_game(lobby: Lobby):
    """Initialize the game state when starting"""
    # Initialize ball in center with random direction
    angle = random.uniform(0, 2 * 3.14159)
    speed = 200
    lobby.ball = Ball(
        x=400, y=400,
        vx=speed * (random.random() * 0.4 + 0.8) * (1 if random.random() > 0.5 else -1),
        vy=speed * (random.random() * 0.4 + 0.8) * (1 if random.random() > 0.5 else -1)
    )

    # Initialize player snakes at three sides of the triangle
    positions = [
        {"x": 400, "y": 50, "angle": 90},   # Top
        {"x": 100, "y": 650, "angle": 330}, # Bottom left
        {"x": 700, "y": 650, "angle": 210}  # Bottom right
    ]

    for i, player in enumerate(lobby.players):
        if player is not None:
            pos = positions[i]
            # Initialize snake with 5 segments
            player.snake = []
            for j in range(5):
                player.snake.append({
                    "x": pos["x"],
                    "y": pos["y"] + j * 10
                })
            # Set initial direction based on position
            angle_rad = pos["angle"] * 3.14159 / 180
            player.direction = {
                "x": 0,
                "y": 0
            }
            player.score = 0

async def broadcast_lobby_state(lobby: Lobby):
    """Send lobby state to all connected players"""
    players_data = []
    for p in lobby.players:
        if p is None:
            players_data.append(None)
        else:
            players_data.append({
                "username": p.username,
                "color": p.color,
                "is_bot": p.is_bot,
                "score": p.score
            })

    message = {
        "type": "lobby_update",
        "code": lobby.code,
        "players": players_data,
        "game_started": lobby.game_started
    }

    # Send to all connected players
    for player in lobby.players:
        if player is not None and player.ws is not None:
            try:
                await player.ws.send(json.dumps(message))
            except:
                pass

async def broadcast_game_state(lobby: Lobby):
    """Send game state to all connected players"""
    if not lobby.game_started or lobby.ball is None:
        return

    players_data = []
    for p in lobby.players:
        if p is None:
            players_data.append(None)
        else:
            players_data.append({
                "username": p.username,
                "color": p.color,
                "score": p.score,
                "snake": p.snake,
                "direction": p.direction
            })

    message = {
        "type": "game_update",
        "ball": {
            "x": lobby.ball.x,
            "y": lobby.ball.y
        },
        "players": players_data
    }

    # Send to all connected players
    for player in lobby.players:
        if player is not None and player.ws is not None:
            try:
                await player.ws.send(json.dumps(message))
            except:
                pass

async def game_loop(lobby: Lobby):
    """Main game loop for a lobby"""
    while lobby.game_started:
        try:
            current_time = time.time()
            dt = current_time - lobby.last_update
            lobby.last_update = current_time

            if dt > 0.1:  # Cap dt to prevent huge jumps
                dt = 0.1

            # Update ball position
            if lobby.ball:
                lobby.ball.x += lobby.ball.vx * dt
                lobby.ball.y += lobby.ball.vy * dt

                # Ball collision with walls - award points to opposite players
                scored = False
                if lobby.ball.y <= 10:  # Top wall hit
                    lobby.ball.y = 10
                    lobby.ball.vy = abs(lobby.ball.vy)
                    # Award points to bottom two players (indices 1 and 2)
                    if lobby.players[1]: lobby.players[1].score += 1
                    if lobby.players[2]: lobby.players[2].score += 1
                    scored = True
                elif lobby.ball.y >= 790:  # Bottom wall hit
                    lobby.ball.y = 790
                    lobby.ball.vy = -abs(lobby.ball.vy)
                    # Award points to top player and right diagonal (indices 0 and 2)
                    if lobby.players[0]: lobby.players[0].score += 1
                    if lobby.players[2]: lobby.players[2].score += 1
                    scored = True

                if lobby.ball.x <= 10:  # Left wall hit
                    lobby.ball.x = 10
                    lobby.ball.vx = abs(lobby.ball.vx)
                    # Award points to right two players (indices 0 and 2)
                    if lobby.players[0]: lobby.players[0].score += 1
                    if lobby.players[2]: lobby.players[2].score += 1
                    scored = True
                elif lobby.ball.x >= 790:  # Right wall hit
                    lobby.ball.x = 790
                    lobby.ball.vx = -abs(lobby.ball.vx)
                    # Award points to left two players (indices 0 and 1)
                    if lobby.players[0]: lobby.players[0].score += 1
                    if lobby.players[1]: lobby.players[1].score += 1
                    scored = True

                # Check for win condition
                for player in lobby.players:
                    if player and player.score >= 19:
                        winner_message = {
                            "type": "game_over",
                            "winner": player.username
                        }
                        for p in lobby.players:
                            if p is not None and p.ws is not None:
                                try:
                                    await p.ws.send(json.dumps(winner_message))
                                except:
                                    pass
                        lobby.game_started = False
                        return

            # Update bot AI
            for player in lobby.players:
                if player and player.is_bot and lobby.ball:
                    # Simple bot AI: move towards ball
                    if len(player.snake) > 0:
                        head = player.snake[0]
                        dx = lobby.ball.x - head["x"]
                        dy = lobby.ball.y - head["y"]
                        length = (dx*dx + dy*dy) ** 0.5
                        if length > 0:
                            player.direction = {
                                "x": dx / length,
                                "y": dy / length
                            }

            # Update player snakes
            for player in lobby.players:
                if player and len(player.snake) > 0:
                    speed = 100
                    head = player.snake[0].copy()
                    head["x"] += player.direction["x"] * speed * dt
                    head["y"] += player.direction["y"] * speed * dt

                    # Keep snake within bounds
                    head["x"] = max(20, min(780, head["x"]))
                    head["y"] = max(20, min(780, head["y"]))

                    player.snake.insert(0, head)

                    # Keep snake at fixed length
                    while len(player.snake) > 50:
                        player.snake.pop()

            await broadcast_game_state(lobby)
            await asyncio.sleep(0.016)  # ~60 FPS

        except Exception as e:
            print(f"Error in game loop: {e}")
            await asyncio.sleep(0.1)

@app.route('/')
async def index():
    return await render_template('index.html')

@app.websocket('/ws')
async def ws():
    try:
        while True:
            data = await websocket.receive()
            message = json.loads(data)
            msg_type = message.get('type')

            if msg_type == 'create_lobby':
                username = message.get('username', 'Player')
                color = message.get('color', COLORS[0])

                # Create new lobby
                code = generate_lobby_code()
                player = Player(username=username, color=color, ws=websocket)
                lobby = Lobby(
                    code=code,
                    players=[player, None, None],
                    creator_ws=websocket
                )
                lobbies[code] = lobby
                ws_to_lobby[websocket] = code

                await websocket.send(json.dumps({
                    "type": "lobby_created",
                    "code": code
                }))
                await broadcast_lobby_state(lobby)

            elif msg_type == 'join_lobby':
                code = message.get('code', '')
                username = message.get('username', 'Player')
                color = message.get('color', COLORS[0])

                if code not in lobbies:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Lobby not found"
                    }))
                    continue

                lobby = lobbies[code]

                if lobby.game_started:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Game already started"
                    }))
                    continue

                # Check if color is available
                if color not in get_available_colors(lobby):
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Color already taken"
                    }))
                    continue

                # Find empty slot
                slot = None
                for i in range(3):
                    if lobby.players[i] is None:
                        slot = i
                        break

                if slot is None:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Lobby is full"
                    }))
                    continue

                player = Player(username=username, color=color, ws=websocket)
                lobby.players[slot] = player
                ws_to_lobby[websocket] = code

                await websocket.send(json.dumps({
                    "type": "lobby_joined",
                    "code": code
                }))
                await broadcast_lobby_state(lobby)

            elif msg_type == 'start_game':
                if websocket not in ws_to_lobby:
                    continue

                code = ws_to_lobby[websocket]
                lobby = lobbies[code]

                # Only creator can start
                if websocket != lobby.creator_ws:
                    continue

                # Fill empty slots with bots
                for i in range(3):
                    if lobby.players[i] is None:
                        bot = create_bot(lobby)
                        if bot:
                            lobby.players[i] = bot

                lobby.game_started = True
                initialize_game(lobby)

                await broadcast_lobby_state(lobby)

                # Start game loop
                asyncio.create_task(game_loop(lobby))

            elif msg_type == 'player_input':
                if websocket not in ws_to_lobby:
                    continue

                code = ws_to_lobby[websocket]
                lobby = lobbies[code]

                if not lobby.game_started:
                    continue

                # Find player
                player = None
                for p in lobby.players:
                    if p and p.ws == websocket:
                        player = p
                        break

                if player:
                    direction = message.get('direction', {})
                    player.direction = direction

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Clean up on disconnect
        if websocket in ws_to_lobby:
            code = ws_to_lobby[websocket]
            if code in lobbies:
                lobby = lobbies[code]

                # Remove player
                for i in range(3):
                    if lobby.players[i] and lobby.players[i].ws == websocket:
                        lobby.players[i] = None

                # If lobby is empty or game not started, remove lobby
                if all(p is None for p in lobby.players) or not lobby.game_started:
                    del lobbies[code]
                else:
                    await broadcast_lobby_state(lobby)

            del ws_to_lobby[websocket]

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9103)
