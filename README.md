# TripleSnake

A real-time multiplayer 3-player snake game built with Quart and Canvas 2D.

## Features

- **3-Player Multiplayer**: Up to 3 players compete simultaneously
- **Live Lobbies**: Create or join lobbies with 7-digit codes
- **18 Color Choices**: Players choose from 18 different colors
- **Bot Support**: Empty slots automatically filled with bots (Robot & Botsy)
- **Real-time Gameplay**: WebSocket-based live multiplayer
- **Unique Scoring**: When the ball hits a wall, the two players on the opposite sides score points
- **Win Condition**: First player to reach 19 points wins!

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

The app will be available at `http://localhost:9103`

## How to Play

1. **Create Lobby**: Click "Create Lobby", enter your username, and choose a color
2. **Share Code**: Share the 7-digit join code with other players
3. **Join Lobby**: Others can click "Join Lobby" and enter the code
4. **Start Game**: The lobby creator clicks "Play" to start (bots fill empty slots)
5. **Controls**: Use arrow keys or WASD to control your snake
6. **Scoring**: When the ball hits a wall, both players on the opposite two sides gain a point
7. **Win**: First to 19 points wins!

## Production Deployment

The app is designed to run on port 9103 with Hypercorn and Nginx. Configure your production server accordingly.

## Tech Stack

- **Backend**: Quart 0.20.0 (async Python web framework)
- **WebSockets**: Real-time bidirectional communication
- **Frontend**: Vanilla JavaScript with Canvas 2D
- **Server**: Hypercorn 0.17.3
