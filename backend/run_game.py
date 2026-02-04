#!/usr/bin/env python3
"""
Headless Codenames Game Runner

Run a full agent-vs-agent game without the frontend UI.

Usage:
    python run_game.py                    # Run a new game
    python run_game.py --replay <id>      # Replay a saved game
"""

import asyncio
import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from game_engine import CodenamesGame, GameConfig, Team, GamePhase
from agents import SpymasterAgent, GuesserAgent

# ANSI colors for terminal output
class Colors:
    RED = '\033[91m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def print_board(game: CodenamesGame, reveal_all: bool = False):
    """Print the game board in a nice grid format."""
    print("\n" + "="*60)
    print(f"{Colors.BOLD}BOARD{Colors.RESET}")
    print("="*60)
    
    for i, card in enumerate(game.cards):
        if card.revealed or reveal_all:
            if card.type.value == "RED":
                color = Colors.RED
            elif card.type.value == "BLUE":
                color = Colors.BLUE
            elif card.type.value == "ASSASSIN":
                color = Colors.GRAY + Colors.BOLD
            else:
                color = Colors.YELLOW
            status = "✓" if card.revealed else " "
        else:
            color = Colors.RESET
            status = " "
        
        word = f"{card.word:12}"
        print(f"{color}{word}{Colors.RESET}[{status}]", end="  ")
        if (i + 1) % 5 == 0:
            print()
    print()


def print_scores(game: CodenamesGame):
    """Print current scores."""
    red_total = sum(1 for c in game.cards if c.type.value == "RED")
    blue_total = sum(1 for c in game.cards if c.type.value == "BLUE")
    red_found = sum(1 for c in game.cards if c.type.value == "RED" and c.revealed)
    blue_found = sum(1 for c in game.cards if c.type.value == "BLUE" and c.revealed)
    
    print(f"{Colors.RED}RED: {red_found}/{red_total}{Colors.RESET}  |  {Colors.BLUE}BLUE: {blue_found}/{blue_total}{Colors.RESET}")


async def run_game(delay: float = 1.0):
    """Run a full agent-vs-agent game."""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}       CODENAMES - AGENT VS AGENT{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    # Create game with all agents
    config = GameConfig(players={
        "RED_SPYMASTER": "agent",
        "RED_GUESSER": "agent",
        "BLUE_SPYMASTER": "agent",
        "BLUE_GUESSER": "agent"
    })
    
    import uuid
    game_id = str(uuid.uuid4())[:8]
    game = CodenamesGame(id=game_id, config=config)
    
    print(f"Game ID: {game_id}")
    print_board(game, reveal_all=True)  # Show full board at start (spymaster view)
    print_scores(game)
    
    turn_count = 0
    max_turns = 50  # Safety limit
    
    while game.phase != GamePhase.GAME_OVER and turn_count < max_turns:
        turn_count += 1
        current_team = game.current_turn
        is_spymaster = game.phase in [GamePhase.RED_SPYMASTER, GamePhase.BLUE_SPYMASTER]
        
        team_color = Colors.RED if current_team == Team.RED else Colors.BLUE
        role = "SPYMASTER" if is_spymaster else "GUESSER"
        
        print(f"\n{team_color}{Colors.BOLD}--- Turn {turn_count}: {current_team.value} {role} ---{Colors.RESET}")
        
        # Create agent
        if is_spymaster:
            agent = SpymasterAgent(current_team)
        else:
            agent = GuesserAgent(current_team)
        
        # Get move
        print(f"{Colors.GRAY}Agent thinking...{Colors.RESET}")
        move = await agent.get_move(game.get_state())
        
        # Log reasoning
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        reasoning_entry = {
            "role": f"{current_team.value} {role}",
            "action": f"Clue: {move.get('word')} {move.get('number')}" if is_spymaster else f"Guess: {move.get('words')}",
            "reasoning": move.get("reasoning", ""),
            "timestamp": timestamp
        }
        game.reasoning_log.append(reasoning_entry)
        
        # Apply move
        if is_spymaster:
            clue_word = move.get("word", "PASS")
            clue_num = move.get("number", 0)
            print(f"{team_color}Clue: {Colors.BOLD}{clue_word} {clue_num}{Colors.RESET}")
            print(f"{Colors.GRAY}Reasoning: {move.get('reasoning', 'N/A')}{Colors.RESET}")
            
            try:
                game.give_clue(current_team, clue_word, clue_num)
            except ValueError as e:
                print(f"{Colors.RED}Error: {e}{Colors.RESET}")
                break
        else:
            words = move.get("words", [])
            print(f"{team_color}Guesses: {Colors.BOLD}{words}{Colors.RESET}")
            print(f"{Colors.GRAY}Reasoning: {move.get('reasoning', 'N/A')}{Colors.RESET}")
            
            if "END_TURN" in words or not words:
                game.end_turn_manually(current_team)
                print(f"{Colors.GRAY}Ending turn.{Colors.RESET}")
            else:
                for word in words:
                    if word == "END_TURN":
                        game.end_turn_manually(current_team)
                        print(f"{Colors.GRAY}Ending turn.{Colors.RESET}")
                        break
                    
                    try:
                        turn_ended = game.guess_card(current_team, word)
                        card = next(c for c in game.cards if c.word == word)
                        
                        if card.type.value == current_team.value:
                            print(f"{Colors.GREEN}✓ {word} - Correct!{Colors.RESET}")
                        elif card.type.value == "ASSASSIN":
                            print(f"{Colors.GRAY}{Colors.BOLD}☠ {word} - ASSASSIN! Game Over.{Colors.RESET}")
                        elif card.type.value == "NEUTRAL":
                            print(f"{Colors.YELLOW}○ {word} - Neutral. Turn ends.{Colors.RESET}")
                        else:
                            print(f"{Colors.RED if card.type.value == 'RED' else Colors.BLUE}✗ {word} - Opponent's card! Turn ends.{Colors.RESET}")
                        
                        if turn_ended:
                            break
                            
                    except ValueError as e:
                        print(f"{Colors.RED}Error guessing {word}: {e}{Colors.RESET}")
                        break
                
                # End turn after all guesses if turn didn't end naturally
                if game.phase not in [GamePhase.GAME_OVER, GamePhase.RED_SPYMASTER, GamePhase.BLUE_SPYMASTER]:
                    game.end_turn_manually(current_team)
        
        print_scores(game)
        time.sleep(delay)  # Small delay for readability
    
    # Game over
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}                  GAME OVER{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    
    if game.winner:
        winner_color = Colors.RED if game.winner == Team.RED else Colors.BLUE
        print(f"\n{winner_color}{Colors.BOLD}🏆 {game.winner.value} WINS! 🏆{Colors.RESET}\n")
    
    print_board(game, reveal_all=True)
    
    # Save history
    history_file = game.save_history()
    print(f"\n{Colors.GREEN}Game saved to: {history_file}{Colors.RESET}")
    
    return game


def replay_game(game_id: str, delay: float = 1.0):
    """Replay a saved game from history."""
    history_path = f"history/game_history_{game_id}.json"
    
    if not os.path.exists(history_path):
        print(f"{Colors.RED}Error: Game history not found: {history_path}{Colors.RESET}")
        return
    
    with open(history_path, 'r') as f:
        history = json.load(f)
    
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}       CODENAMES - GAME REPLAY{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"Game ID: {game_id}")
    print(f"Winner: {history.get('winner', 'Unknown')}")
    
    # Display board if cards are available
    cards = history.get("cards", [])
    if cards:
        print("\n" + "="*60)
        print(f"{Colors.BOLD}INITIAL BOARD{Colors.RESET}")
        print("="*60)
        
        for i, card in enumerate(cards):
            card_type = card.get("type", "NEUTRAL")
            if card_type == "RED":
                color = Colors.RED
            elif card_type == "BLUE":
                color = Colors.BLUE
            elif card_type == "ASSASSIN":
                color = Colors.GRAY + Colors.BOLD
            else:
                color = Colors.YELLOW
            
            word = f"{card.get('word', '???'):12}"
            print(f"{color}{word}{Colors.RESET}", end="  ")
            if (i + 1) % 5 == 0:
                print()
        print()
    
    print()
    
    # Replay log
    print(f"{Colors.BOLD}--- Game Log ---{Colors.RESET}")
    for entry in history.get("log", []):
        print(f"  {entry}")
        time.sleep(delay * 0.3)
    
    print()

    
    # Replay reasoning
    print(f"{Colors.BOLD}--- Agent Reasoning ---{Colors.RESET}")
    for entry in history.get("reasoning_log", []):
        role = entry.get("role", "Unknown")
        action = entry.get("action", "")
        reasoning = entry.get("reasoning", "")
        
        if "RED" in role:
            color = Colors.RED
        else:
            color = Colors.BLUE
        
        print(f"\n{color}{Colors.BOLD}{role}{Colors.RESET}")
        print(f"  Action: {action}")
        print(f"  {Colors.GRAY}Reasoning: {reasoning}{Colors.RESET}")
        time.sleep(delay)
    
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}                END OF REPLAY{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")


def list_games():
    """List all saved games."""
    history_dir = Path("history")
    if not history_dir.exists():
        print("No games found.")
        return
    
    games = list(history_dir.glob("game_history_*.json"))
    if not games:
        print("No games found.")
        return
    
    print(f"\n{Colors.BOLD}Saved Games:{Colors.RESET}")
    for game_file in games:
        game_id = game_file.stem.replace("game_history_", "")
        try:
            with open(game_file, 'r') as f:
                data = json.load(f)
            winner = data.get("winner", "Incomplete")
        except (json.JSONDecodeError, IOError):
            winner = "Corrupted"
        print(f"  {game_id} - Winner: {winner}")
    print()



def main():
    parser = argparse.ArgumentParser(description="Codenames Headless Game Runner")
    parser.add_argument("--replay", type=str, help="Replay a game by ID")
    parser.add_argument("--list", action="store_true", help="List all saved games")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between turns (seconds)")
    
    args = parser.parse_args()
    
    if args.list:
        list_games()
    elif args.replay:
        replay_game(args.replay, delay=args.delay)
    else:
        asyncio.run(run_game(delay=args.delay))


if __name__ == "__main__":
    main()
