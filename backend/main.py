from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import uuid
import json
import asyncio

from game_engine import CodenamesGame, GameConfig, Team, GamePhase, GameState
from agents import SpymasterAgent, GuesserAgent
import os

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
games: Dict[str, CodenamesGame] = {}

from fastapi import Header

async def verify_token(x_access_token: Optional[str] = Header(None)):
    if ACCESS_TOKEN and x_access_token != ACCESS_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing Access Token")
    return x_access_token

# Connection manager for WebSockets
class ConnectionManager:
    def __init__(self):
        # game_id -> list of websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_id: str):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = []
        self.active_connections[game_id].append(websocket)

    def disconnect(self, websocket: WebSocket, game_id: str):
        if game_id in self.active_connections:
            self.active_connections[game_id].remove(websocket)
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]

    async def broadcast(self, game_id: str, message: dict):
        if game_id in self.active_connections:
            for connection in self.active_connections[game_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass # Handle closed connections gracefully-ish

manager = ConnectionManager()

# --- API Data Models ---

class CreateGameRequest(BaseModel):
    difficulty: str = "normal"
    board_size: int = 25
    llm_model: str = "gpt-4o"
    players: Dict[str, str] = {
        "RED_SPYMASTER": "human",
        "RED_GUESSER": "human",
        "BLUE_SPYMASTER": "human",
        "BLUE_GUESSER": "human"
    }

class JoinGameRequest(BaseModel):
    role: str # "SPYMASTER" or "GUESSER"
    team: str # "RED" or "BLUE"

class ActionRequest(BaseModel):
    action_type: str # "CLUE" or "GUESS" or "END_TURN"
    payload: dict # {word: str, number: int} for clue, {word: str} for guess

# --- Endpoints ---

from fastapi import Depends

@app.post("/api/game/create")
async def create_game(request: CreateGameRequest, token: str = Depends(verify_token)):
    game_id = str(uuid.uuid4())[:8]
    config = GameConfig(
        difficulty=request.difficulty,
        board_size=request.board_size,
        llm_model=request.llm_model,
        players=request.players
    )
    game = CodenamesGame(id=game_id, config=config)
    games[game_id] = game
    return {"game_id": game_id}


@app.get("/api/game/{game_id}")
async def get_game_state(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    return games[game_id].get_state()

@app.post("/api/game/{game_id}/move")
async def make_move(game_id: str, list_request: ActionRequest):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    
    try:
        if list_request.action_type == "CLUE":
            # Infer team from current turn
            game.give_clue(game.current_turn, list_request.payload['word'], list_request.payload['number'])
        elif list_request.action_type == "GUESS":
            game.guess_card(game.current_turn, list_request.payload['word'])
        elif list_request.action_type == "END_TURN":
            game.end_turn_manually(game.current_turn)
            
        # Broadcast update
        await manager.broadcast(game_id, {"type": "STATE_UPDATE", "state": game.get_state().dict()})
        
        return {"status": "success", "state": game.get_state()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/game/{game_id}/agent-move")
async def trigger_agent_move(game_id: str, expected_turn_count: Optional[int] = None, token: str = Depends(verify_token)):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    
    # Validate turn count from client to prevent stale requests
    if expected_turn_count is not None and expected_turn_count != game.turn_count:
        print(f"STALE REQUEST: Client expected turn {expected_turn_count} but current is {game.turn_count}. Ignoring.")
        return {"status": "ignored", "reason": f"Stale request. Expected turn {expected_turn_count}, current is {game.turn_count}"}
    
    # Determine which agent to call based on phase
    current_team = game.current_turn
    is_spymaster = game.phase in [GamePhase.RED_SPYMASTER, GamePhase.BLUE_SPYMASTER]
    
    agent = None
    if is_spymaster:
        agent = SpymasterAgent(current_team, llm_model=game.config.llm_model)
    else:
        agent = GuesserAgent(current_team, llm_model=game.config.llm_model)
        
    # Capture state ID to prevent race conditions (server-side double check)
    start_turn_count = game.turn_count

    
    try:
        move = await agent.get_move(game.get_state())
        
        # Verify race condition
        if game.turn_count != start_turn_count:
            print(f"RACE CONDITION DETECTED: Agent started at turn {start_turn_count} but now it is {game.turn_count}. Discarding move.")
            return {"status": "ignored", "reason": "State changed during processing"}
        
        # Log reasoning
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        
        reasoning_entry = {
            "role": f"{current_team.value} {'SPYMASTER' if is_spymaster else 'GUESSER'}",
            "action": f"Clue: {move.get('word')} {move.get('number')}" if is_spymaster else f"Guess Plan: {move.get('words')}",
            "reasoning": move.get("reasoning") or f"Reasoning missing. Raw keys: {list(move.keys())}",
            "timestamp": timestamp
        }

        game.reasoning_log.append(reasoning_entry)
        
        # Apply move
        state_updates = []
        if is_spymaster:
            game.give_clue(current_team, move["word"], move["number"])
            state_updates.append(f"Clue: {move['word']} {move['number']}")
        
        # For Guesser, we simply return the "words" plan. 
        # The frontend will execute them one by one to create the animation effect.
                
        # Broadcast update (mainly for Spymaster clue, or just log update)
        await manager.broadcast(game_id, {"type": "STATE_UPDATE", "state": game.get_state().dict()})
        
        return {"status": "success", "move": move, "state": game.get_state(), "updates": state_updates}



    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


# --- History Replay Endpoints ---

@app.get("/api/history/list")
async def list_game_history():
    """List all saved game histories."""
    import os
    from pathlib import Path
    
    history_dir = Path("history")
    if not history_dir.exists():
        return {"games": []}
    
    games_list = []
    for game_file in history_dir.glob("game_history_*.json"):
        game_id = game_file.stem.replace("game_history_", "")
        try:
            with open(game_file, 'r') as f:
                data = json.load(f)
            games_list.append({
                "game_id": game_id,
                "winner": data.get("winner"),
                "final_score": data.get("final_score"),
                "has_cards": "cards" in data
            })
        except (json.JSONDecodeError, IOError):
            games_list.append({
                "game_id": game_id,
                "winner": None,
                "final_score": None,
                "has_cards": False,
                "error": "corrupted"
            })
    
    return {"games": games_list}


@app.get("/api/history/{game_id}")
async def get_game_history(game_id: str):
    """Get a specific game's history for replay."""
    import os
    
    history_path = f"history/game_history_{game_id}.json"
    if not os.path.exists(history_path):
        raise HTTPException(status_code=404, detail="Game history not found")
    
    try:
        with open(history_path, 'r') as f:
            history = json.load(f)
        return history
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Corrupted game history")


@app.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    await manager.connect(websocket, game_id)
    try:
        while True:
            # Just keep connection alive, maybe handle chat later
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, game_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
