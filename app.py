import asyncio
import random
import string
import time
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from quart import Quart, render_template, websocket, jsonify
import json

app = Quart(__name__)

# Color palette (18 colors - 9 light, 9 dark)
COLORS = [
    # Light colors
    "#FF3333", "#33FF33", "#3333FF", "#FFFF33", "#FF33FF", "#33FFFF",
    "#FF9933", "#FF3399", "#99FF33",
    # Dark colors
    "#990000", "#009900", "#000099", "#996600", "#990099", "#009999",
    "#663300", "#660066", "#336600"
]

BOT_NAMES = ["Robot", "Botsy"]

# Triangle geometry constants
CANVAS_SIZE = 800
TRIANGLE_CENTER = CANVAS_SIZE / 2
TRIANGLE_RADIUS = 350  # Distance from center to vertices
PADDLE_LENGTH = 120
PADDLE_WIDTH = 15
BALL_RADIUS = 8

@dataclass
class Paddle:
    position: float = 0.5  # 0 to 1, representing position along the edge

@dataclass
class Player:
    username: str
    color: str
    is_bot: bool = False
    ws: Optional[object] = None
    score: int = 0
    paddle: Paddle = field(default_factory=Paddle)
    player_index: int = 0  # 0, 1, or 2
    direction: int = 0  # Current input direction: -1 (left), 0 (none), 1 (right)
    bot_target: float = 0.5  # Bot's current target position
    bot_last_update: float = 0.0  # Last time bot updated its target

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

    used_names = {p.username for p in lobby.players if p is not None}
    available_bot_names = [name for name in BOT_NAMES if name not in used_names]

    if not available_bot_names:
        bot_name = f"Robot{random.randint(1, 99)}"
    else:
        bot_name = random.choice(available_bot_names)

    return Player(
        username=bot_name,
        color=random.choice(available_colors),
        is_bot=True,
        ws=None
    )

def get_triangle_vertices():
    """Get the three vertices of the triangle"""
    vertices = []
    for i in range(3):
        angle = (i * 120 - 90) * math.pi / 180  # Start from top
        x = TRIANGLE_CENTER + TRIANGLE_RADIUS * math.cos(angle)
        y = TRIANGLE_CENTER + TRIANGLE_RADIUS * math.sin(angle)
        vertices.append((x, y))
    return vertices

def get_edge_endpoints(player_index):
    """Get the two endpoints of an edge for a player"""
    vertices = get_triangle_vertices()
    # Player 0: bottom edge (vertices 1-2)
    # Player 1: top-right edge (vertices 2-0)
    # Player 2: top-left edge (vertices 0-1)
    if player_index == 0:
        return vertices[1], vertices[2]
    elif player_index == 1:
        return vertices[2], vertices[0]
    else:
        return vertices[0], vertices[1]

def get_paddle_position(player_index, paddle_pos):
    """Get paddle center position based on player index and paddle position (0-1)"""
    p1, p2 = get_edge_endpoints(player_index)
    # Interpolate between endpoints
    x = p1[0] + (p2[0] - p1[0]) * paddle_pos
    y = p1[1] + (p2[1] - p1[1]) * paddle_pos
    return (x, y)

def point_in_triangle(px, py):
    """Check if point is inside the triangle"""
    vertices = get_triangle_vertices()
    v0, v1, v2 = vertices

    def sign(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

    d1 = sign((px, py), v0, v1)
    d2 = sign((px, py), v1, v2)
    d3 = sign((px, py), v2, v0)

    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)

    return not (has_neg and has_pos)

def line_intersection(p1, p2, p3, p4):
    """Find intersection point of two line segments"""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 0.0001:
        return None

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

    if 0 <= t <= 1 and 0 <= u <= 1:
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        return (x, y)
    return None

def check_paddle_collision(ball_x, ball_y, ball_vx, ball_vy, player):
    """Check if ball collides with a paddle"""
    p1, p2 = get_edge_endpoints(player.player_index)
    paddle_center = get_paddle_position(player.player_index, player.paddle.position)

    # Calculate paddle endpoints based on edge direction
    edge_dx = p2[0] - p1[0]
    edge_dy = p2[1] - p1[1]
    edge_len = math.sqrt(edge_dx**2 + edge_dy**2)
    edge_dx /= edge_len
    edge_dy /= edge_len

    # Paddle endpoints
    half_len = PADDLE_LENGTH / 2
    paddle_p1 = (paddle_center[0] - edge_dx * half_len, paddle_center[1] - edge_dy * half_len)
    paddle_p2 = (paddle_center[0] + edge_dx * half_len, paddle_center[1] + edge_dy * half_len)

    # Check distance from ball to paddle line segment
    px, py = paddle_center
    dx = ball_x - px
    dy = ball_y - py
    dist = abs(dx * (-edge_dy) + dy * edge_dx)

    if dist < BALL_RADIUS + PADDLE_WIDTH / 2:
        # Check if ball is within paddle length
        proj = dx * edge_dx + dy * edge_dy
        if abs(proj) < half_len:
            return True
    return False

def initialize_game(lobby: Lobby):
    """Initialize the game state when starting"""
    # Initialize ball in center with random direction
    angle = random.uniform(0, 2 * math.pi)
    speed = 250
    lobby.ball = Ball(
        x=TRIANGLE_CENTER,
        y=TRIANGLE_CENTER,
        vx=speed * math.cos(angle),
        vy=speed * math.sin(angle)
    )

    # Set player indices
    for i, player in enumerate(lobby.players):
        if player is not None:
            player.player_index = i
            player.paddle.position = 0.5
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

    # Send different view to each player
    for current_player in lobby.players:
        if current_player is None or current_player.ws is None:
            continue

        players_data = []
        for p in lobby.players:
            if p is None:
                players_data.append(None)
            else:
                players_data.append({
                    "username": p.username,
                    "color": p.color,
                    "score": p.score,
                    "paddle_position": p.paddle.position,
                    "player_index": p.player_index
                })

        message = {
            "type": "game_update",
            "ball": {
                "x": lobby.ball.x,
                "y": lobby.ball.y
            },
            "players": players_data,
            "your_index": current_player.player_index
        }

        try:
            await current_player.ws.send(json.dumps(message))
        except:
            pass

async def game_loop(lobby: Lobby):
    """Main game loop for a lobby"""
    while lobby.game_started:
        try:
            current_time = time.time()
            dt = current_time - lobby.last_update
            lobby.last_update = current_time

            if dt > 0.1:
                dt = 0.1

            if lobby.ball:
                # Update ball position
                lobby.ball.x += lobby.ball.vx * dt
                lobby.ball.y += lobby.ball.vy * dt

                vertices = get_triangle_vertices()

                # Check collision with each edge
                for i in range(3):
                    v1 = vertices[i]
                    v2 = vertices[(i + 1) % 3]

                    # Get the player defending this edge
                    # Player 0 defends bottom (edge 1-2)
                    # Player 1 defends right (edge 2-0)
                    # Player 2 defends left (edge 0-1)
                    edge_to_player = {0: 2, 1: 0, 2: 1}
                    player = lobby.players[edge_to_player[i]]

                    # Calculate distance to edge
                    edge_dx = v2[0] - v1[0]
                    edge_dy = v2[1] - v1[1]
                    edge_len = math.sqrt(edge_dx**2 + edge_dy**2)
                    edge_nx = -edge_dy / edge_len
                    edge_ny = edge_dx / edge_len

                    # Distance from ball to edge
                    ball_to_v1_x = lobby.ball.x - v1[0]
                    ball_to_v1_y = lobby.ball.y - v1[1]
                    dist = ball_to_v1_x * edge_nx + ball_to_v1_y * edge_ny

                    # Check if ball is close to this edge
                    if abs(dist) < BALL_RADIUS + 10:
                        # Check if ball hit paddle or wall
                        if player and check_paddle_collision(lobby.ball.x, lobby.ball.y,
                                                             lobby.ball.vx, lobby.ball.vy, player):
                            # Bounce off paddle with randomness
                            # Calculate base reflection
                            dot = lobby.ball.vx * edge_nx + lobby.ball.vy * edge_ny
                            lobby.ball.vx -= 2 * dot * edge_nx
                            lobby.ball.vy -= 2 * dot * edge_ny

                            # Add random angle variation (±30 degrees)
                            current_angle = math.atan2(lobby.ball.vy, lobby.ball.vx)
                            angle_variation = random.uniform(-math.pi/6, math.pi/6)  # ±30°
                            new_angle = current_angle + angle_variation

                            # Maintain ball speed but change direction
                            speed = math.sqrt(lobby.ball.vx**2 + lobby.ball.vy**2)
                            lobby.ball.vx = speed * math.cos(new_angle)
                            lobby.ball.vy = speed * math.sin(new_angle)

                            # Move ball away from paddle
                            lobby.ball.x += edge_nx * (BALL_RADIUS + 10 - abs(dist))
                            lobby.ball.y += edge_ny * (BALL_RADIUS + 10 - abs(dist))
                        elif dist < 0:  # Ball went past paddle (scored)
                            # Award points to other two players
                            for j, p in enumerate(lobby.players):
                                if p and j != edge_to_player[i]:
                                    p.score += 1

                            # Reset ball
                            lobby.ball.x = TRIANGLE_CENTER
                            lobby.ball.y = TRIANGLE_CENTER
                            angle = random.uniform(0, 2 * math.pi)
                            speed = 250
                            lobby.ball.vx = speed * math.cos(angle)
                            lobby.ball.vy = speed * math.sin(angle)

                            # Check win condition
                            for p in lobby.players:
                                if p and p.score >= 19:
                                    winner_message = {
                                        "type": "game_over",
                                        "winner": p.username
                                    }
                                    for player in lobby.players:
                                        if player and player.ws:
                                            try:
                                                await player.ws.send(json.dumps(winner_message))
                                            except:
                                                pass
                                    lobby.game_started = False
                                    return

            # Update bot AI and player movement
            PLAYER_SPEED = 0.8  # Units per second for human players
            BOT_SPEED = PLAYER_SPEED * 0.9  # Bots move at 90% player speed
            BOT_REACTION_DELAY = 0.08  # Bots update target every 0.08 seconds

            for player in lobby.players:
                if not player:
                    continue

                if player.is_bot and lobby.ball:
                    # Bot AI: move paddle toward ball's position along edge
                    # Update target position only every BOT_REACTION_DELAY seconds
                    if current_time - player.bot_last_update >= BOT_REACTION_DELAY:
                        player.bot_last_update = current_time

                        p1, p2 = get_edge_endpoints(player.player_index)

                        # Project ball position onto edge
                        edge_dx = p2[0] - p1[0]
                        edge_dy = p2[1] - p1[1]
                        edge_len = math.sqrt(edge_dx**2 + edge_dy**2)

                        ball_to_p1_x = lobby.ball.x - p1[0]
                        ball_to_p1_y = lobby.ball.y - p1[1]
                        proj = (ball_to_p1_x * edge_dx + ball_to_p1_y * edge_dy) / (edge_len**2)

                        # Add imperfect tracking: ±10% random offset
                        tracking_error = random.uniform(-0.1, 0.1)
                        proj += tracking_error

                        proj = max(0.1, min(0.9, proj))
                        player.bot_target = proj

                    # Move toward target position
                    target_diff = player.bot_target - player.paddle.position
                    move_speed = BOT_SPEED * dt
                    if abs(target_diff) < move_speed:
                        player.paddle.position = player.bot_target
                    elif target_diff > 0:
                        player.paddle.position += move_speed
                    else:
                        player.paddle.position -= move_speed
                else:
                    # Human player: use their input direction
                    if player.direction != 0:
                        move_speed = PLAYER_SPEED * dt
                        player.paddle.position += player.direction * move_speed

                # Clamp paddle position to valid range
                player.paddle.position = max(0.1, min(0.9, player.paddle.position))

            await broadcast_game_state(lobby)
            await asyncio.sleep(0.016)  # ~60 FPS

        except Exception as e:
            print(f"Error in game loop: {e}")
            import traceback
            traceback.print_exc()
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

                if color not in get_available_colors(lobby):
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Color already taken"
                    }))
                    continue

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
                asyncio.create_task(game_loop(lobby))

            elif msg_type == 'paddle_move':
                if websocket not in ws_to_lobby:
                    continue

                code = ws_to_lobby[websocket]
                lobby = lobbies[code]

                if not lobby.game_started:
                    continue

                # Find player and update their direction
                for p in lobby.players:
                    if p and p.ws == websocket:
                        p.direction = message.get('direction', 0)  # -1 left, 0 none, 1 right
                        break

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if websocket in ws_to_lobby:
            code = ws_to_lobby[websocket]
            if code in lobbies:
                lobby = lobbies[code]

                for i in range(3):
                    if lobby.players[i] and lobby.players[i].ws == websocket:
                        lobby.players[i] = None

                if all(p is None for p in lobby.players) or not lobby.game_started:
                    del lobbies[code]
                else:
                    await broadcast_lobby_state(lobby)

            del ws_to_lobby[websocket]

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9103)
