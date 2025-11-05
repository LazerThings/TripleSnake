# TriplePong.io

A real-time multiplayer triangle-based 3-player Pong game built with Quart and Canvas 2D.

## What is TriplePong.io?

TriplePong.io is a .io-style multiplayer game where three players compete in a triangular arena. Each player defends one side of the triangle with a paddle, and the goal is to prevent the ball from hitting your wall while trying to score on your opponents.

## How It Works

- **Triangle Arena**: The playing field is a triangle, with each player defending one side
- **Unique Scoring**: When the ball hits your wall (behind your paddle), **both other players score 1 point**
- **Camera Rotation**: Each player always sees themselves at the bottom of the screen - the camera rotates based on your position
- **First to 19**: The first player to reach 19 points wins!

## Features

- **3-Player Multiplayer**: Up to 3 players compete simultaneously
- **Live Lobbies**: Create or join lobbies with 7-digit codes
- **18 Color Choices**: Players choose from 18 different colors (9 light, 9 dark)
- **Bot Support**: Empty slots automatically filled with bots (Robot & Botsy)
- **Real-time Gameplay**: WebSocket-based live multiplayer at 60 FPS
- **Retro Terminal Aesthetic**: Dark theme with monospace fonts and green accents

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
4. **Start Game**: The lobby creator clicks "Start Game" (bots fill empty slots)
5. **Controls**: Use LEFT/RIGHT arrow keys or A/D to move your paddle
6. **Defend**: Prevent the ball from hitting your wall
7. **Score**: When an opponent misses and the ball hits their wall, you and the other player score
8. **Win**: First to 19 points wins!

## Gameplay Details

- **Paddle Movement**: Move left and right along your edge to intercept the ball
- **Ball Physics**: Ball bounces off paddles and reflects at realistic angles
- **Scoring System**: If player A's wall is hit, players B and C each get 1 point
- **Camera Rotation**: Your paddle is always shown at the bottom, regardless of which player you are

## Production Deployment

The app is designed to run on port 9103 with Hypercorn and Nginx. Configure your production server accordingly.

## Tech Stack

- **Backend**: Quart 0.20.0 (async Python web framework)
- **WebSockets**: Real-time bidirectional communication
- **Frontend**: Vanilla JavaScript with Canvas 2D
- **Server**: Hypercorn 0.17.3
- **Game Physics**: Triangle geometry with rotation matrices
