import json
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict
from game_engine import GameState, Team, CardState, CardType
from llm import LLMService

class Agent(ABC):
    def __init__(self, team: Team, llm_provider: str = "openai", llm_model: str = None):
        self.team = team
        self.llm = LLMService(provider=llm_provider, model=llm_model)

    @abstractmethod
    async def get_move(self, game_state: GameState) -> dict:
        pass
    
    def _format_board(self, game_state: GameState, is_spymaster: bool) -> str:
        board_str = "Current Board:\n"
        for card in game_state.cards:
            status = "(REVEALED)" if card.revealed else ""
            if is_spymaster or card.revealed:
                # Spymaster sees everything, or everyone sees revealed
                type_str = card.type.value
            else:
                type_str = "UNKNOWN"
                
            board_str += f"- {card.word} [{type_str}] {status}\n"
        return board_str
    
    def _format_clue_history(self, clue_history: List[Dict]) -> str:
        """Format clue history concisely for LLM context."""
        if not clue_history:
            return "No clues given yet."
        
        lines = []
        for entry in clue_history:
            team = entry.get("team", "?")
            clue = entry.get("clue", "?")
            number = entry.get("number", 0)
            guesses = entry.get("guesses", [])
            
            if guesses:
                guess_strs = [f"{g['word']}({g['result']})" for g in guesses]
                lines.append(f"{team}: {clue} {number} → {', '.join(guess_strs)}")
            else:
                lines.append(f"{team}: {clue} {number} → (no guesses yet)")
        
        return "\n".join(lines)

class SpymasterAgent(Agent):
    async def get_move(self, game_state: GameState) -> dict:
        # 1. Identify valid targets
        my_words = [c.word for c in game_state.cards if c.type.value == self.team.value and not c.revealed]
        
        if not my_words:
             return {"word": "WIN", "number": 0, "reasoning": "No words left to hint at!"}

        opp_words = [c.word for c in game_state.cards if c.type.value != self.team.value and c.type != CardType.ASSASSIN and c.type != CardType.NEUTRAL and not c.revealed]

        assassin = [c.word for c in game_state.cards if c.type == CardType.ASSASSIN and not c.revealed]
        neutral = [c.word for c in game_state.cards if c.type == CardType.NEUTRAL and not c.revealed]

        history = self._format_clue_history(game_state.clue_history)
        system_prompt = f"""
        You are an expert Codenames Spymaster for Team {self.team.value}.
        Your goal is to be the FIRST to contact all your team's words. You want to beat the opponent.
        Give a single-word clue that connects as many of your team's cards as possible, while strictly avoiding (in order of importance) the Assassin, the Opposing team's cards, and the Neutral cards.
        
        STRATEGY:
        1. Look for semantic intersections between 2, 3, or more of your words.
        2. "Stretch" connections are okay if they are distinct from the "Bad" words.
        3. Prioritize clues with numbers >= 2. A clue for 1 word is weak unless it's the last one.
        4. Keep in mind that Guessers will look at previous clues from you to see if they missed any connections. You can use this to "guide" them toward words that were previously hinted at but not guessed.
        5. ABSOLUTELY forbidden to give a clue that relates more strongly to the Assassin than your target words.
        
        RULES:
        1. Clue must be a single word (no spaces, no hyphens).
        2. Clue cannot be any of the words currently visible on the board (unrevealed).
        3. Clue cannot contain a board word as a substring (e.g. "PINEAPPLE" for "APPLE"), and a board word cannot contain the clue as a substring.

        
        Game History:
        {history}
        
        Your remaining words: {my_words}
        BAD words (Avoid!): {assassin} (Assassin), {opp_words} (Opponent)
        
        Output JSON format: 
        {{
            "reasoning": "Brief and concise thought process (max 2 sentences)",
            "word": "CLUE_WORD", 
            "number": INTEGER
        }}
        """
        
        user_prompt = self._format_board(game_state, is_spymaster=True)

        
        valid = False
        attempts = 0
        response = {}
        
        while not valid and attempts < 3:
            try:
                response = await self.llm.generate_response(system_prompt, user_prompt)
                clue_word = response.get("word", "").upper().strip()
                
                # Validation: Substring and board-word check (sync with engine)
                for c in game_state.cards:
                    if c.revealed: continue
                    board_word = c.word.upper()
                    
                    if clue_word == board_word:
                        raise ValueError(f"Clue '{clue_word}' is on the board")
                    if board_word in clue_word:
                        raise ValueError(f"Clue '{clue_word}' contains board word '{board_word}' as substring")
                    if clue_word in board_word:
                        raise ValueError(f"Clue '{clue_word}' is part of board word '{board_word}'")
                
                valid = True
            except Exception as e:
                attempts += 1
                print(f"Agent retry {attempts}: {e}")
        
        if not valid:
            # Fallback
            return {"word": "PASS", "number": 0, "reasoning": "Failed to generate valid clue."}

        return {"word": response["word"], "number": response["number"], "reasoning": response.get("reasoning", "")}

class GuesserAgent(Agent):
    async def get_move(self, game_state: GameState) -> dict:
        if not game_state.last_clue:
            return {"action": "END_TURN"}
            
        clue_word, clue_number = game_state.last_clue
        
        history = self._format_clue_history(game_state.clue_history)
        system_prompt = f"""
        You are an expert Codenames Guesser for Team {self.team.value}.
        The Spymaster has given you the clue: "{clue_word}" associated with {clue_number} cards. You are trying to find all your words before your opponent does.
        
        STRATEGY:
        1. Analyze the clue "{clue_word}" for all possible meanings (polysemy).
        2. Rank the unrevealed words on the board by their semantic distance to the clue.
        3. Select the top {clue_number} words that are strongest matches.
        4. CONTEXT MATTERS: Look at your Spymaster's PREVIOUS clues in the Game History. If they previously gave a clue that you didn't fully resolve (e.g., they said "Animal 2" and you only guessed "DOG"), consider if "{clue_word}" helps confirm those old words as well.
        5. If you are very confident (often due to historical context), you can guess one extra word (clue_number + 1) to catch up on missed previous clues.
        6. It is risky to guess if the next best word is weak or ambiguous.
        
        Game History:
        {history}
        
        Output JSON format: 
        {{
            "reasoning": "Brief and concise analysis (max 2 sentences)",
            "words": ["GUESS_1", "GUESS_2"]
        }}
        If you have no confident guesses, return ["END_TURN"] in the words list.
        """
        
        user_prompt = self._format_board(game_state, is_spymaster=False)

        
        response = await self.llm.generate_response(system_prompt, user_prompt)
        
        words = response.get("words", [])
        if "END_TURN" in words:
            return {"action": "END_TURN", "reasoning": response.get("reasoning", "Decided to end turn.")}
            
        return {"words": words, "reasoning": response.get("reasoning", "")}
