import random
import json
from enum import Enum
from typing import List, Optional, Tuple, Dict
from pydantic import BaseModel
import uuid


class Team(str, Enum):
    RED = "RED"
    BLUE = "BLUE"
    NEUTRAL = "NEUTRAL" # For bystanders
    ASSASSIN = "ASSASSIN"

class CardType(str, Enum):
    RED = "RED"
    BLUE = "BLUE"
    NEUTRAL = "NEUTRAL"
    ASSASSIN = "ASSASSIN"

class CardState(BaseModel):
    word: str
    type: CardType
    revealed: bool = False
    
    def dict_for_player(self, is_spymaster: bool = False, game_over: bool = False):
        return {
            "word": self.word,
            "revealed": self.revealed,
            "type": self.type if (is_spymaster or self.revealed or game_over) else None,
            "team": self.type if (is_spymaster or self.revealed or game_over) else None # Alias for frontend convenience
        }

class GamePhase(str, Enum):
    RED_SPYMASTER = "RED_SPYMASTER"
    RED_GUESSER = "RED_GUESSER"
    BLUE_SPYMASTER = "BLUE_SPYMASTER"
    BLUE_GUESSER = "BLUE_GUESSER"
    GAME_OVER = "GAME_OVER"

class GameConfig(BaseModel):
    word_list: List[str] = []
    difficulty: str = "normal"
    board_size: int = 25
    llm_model: str = "gpt-4o"  # Default model
    # (Team, Role) -> "human" or "agent"
    players: Dict[str, str] = {
        "RED_SPYMASTER": "human",
        "RED_GUESSER": "human",
        "BLUE_SPYMASTER": "human",
        "BLUE_GUESSER": "human"
    }
    
class GameState(BaseModel):
    id: str
    cards: List[CardState]
    current_turn: Team
    phase: GamePhase
    players: Dict[str, str]
    llm_model: str
    score: Dict[Team, int]
    winner: Optional[Team] = None
    last_clue: Optional[Tuple[str, int]] = None
    remaining_guesses: int = 0
    turn_count: int = 0
    log: List[str] = []
    clue_history: List[Dict] = []  # [{team, clue, number, guesses: [{word, result}]}]
    reasoning_log: List[Dict] = [] # [{role: str, action: str, reasoning: str, timestamp: str}]



    class Config:
        arbitrary_types_allowed = True

class CodenamesGame:
    def __init__(self, id: str, config: GameConfig = GameConfig()):
        self.id = id
        self.config = config
        self.cards: List[CardState] = []
        self.current_turn = Team.RED  # Red starts by default usually
        self.phase = GamePhase.RED_SPYMASTER
        self.winner = None
        self.last_clue = None
        self.last_clue = None
        self.remaining_guesses = 0
        self.turn_count = 0
        self.log = []
        self.clue_history = []  # Structured clue log for agents
        self.reasoning_log = []
        self._initialize_board()

    def _initialize_board(self):
        # Default word list if none provided
        words = self.config.word_list
        if not words:
            words = [
                "AFRICA", "AGENT", "AIR", "ALIEN", "ALPS", "AMAZON", "AMBULANCE", "AMERICA", "ANGEL", "ANTARCTICA",
                "APPLE", "ARM", "ATLANTIS", "AUSTRALIA", "AZTEC", "BACK", "BALL", "BAND", "BANK", "BAR",
                "BARK", "BAT", "BATTERY", "BEACH", "BEAR", "BEAT", "BED", "BEIJING", "BELL", "BELT",
                "BERLIN", "BERMUDA", "BERRY", "BILL", "BLOCK", "BOARD", "BOLT", "BOMB", "BOND", "BOOM",
                "BOOT", "BOTTLE", "BOW", "BOX", "BRIDGE", "BRUSH", "BUCK", "BUFFALO", "BUG", "BUGLE",
                "BUTTON", "CALF", "CANADA", "CAP", "CAPITAL", "CAR", "CARD", "CARROT", "CASINO", "CAST",
                "CAT", "CELL", "CENTAUR", "CENTER", "CHAIR", "CHANGE", "CHARGE", "CHECK", "CHEST", "CHICK",
                "CHINA", "CHOCOLATE", "CHURCH", "CIRCLE", "CLIFF", "CLOAK", "CLUB", "CODE", "COLD", "COMIC",
                "COMPOUND", "CONCERT", "CONDUCTOR", "CONTRACT", "COOK", "COPPER", "COTTON", "COURT", "COVER", "CRANE",
                "CRASH", "CRICKET", "CROSS", "CROWN", "CYCLE", "CZECH", "DANCE", "DATE", "DAY", "DEATH",
                "DECK", "DEGREE", "DIAMOND", "DICE", "DINOSAUR", "DISEASE", "DOCTOR", "DOG", "DRAFT", "DRAGON",
                "DRESS", "DRILL", "DROP", "DUCK", "DWARF", "EAGLE", "EGYPT", "EMBASSY", "ENGINE", "ENGLAND",
                "EUROPE", "EYE", "FACE", "FAIR", "FALL", "FAN", "FENCE", "FIELD", "FIGHTER", "FIGURE",
                "FILE", "FILM", "FIRE", "FISH", "FLUTE", "FLY", "FOOT", "FORCE", "FOREST", "FORK",
                "FRANCE", "GAME", "GAS", "GENIUS", "GERMANY", "GHOST", "GIANT", "GLASS", "GLOVE", "GOLD",
                "GRACE", "GRASS", "GREECE", "GREEN", "GROUND", "HAM", "HAND", "HAWK", "HEAD", "HEART",
                "HELICOPTER", "HIMALAYAS", "HOLE", "HOLLYWOOD", "HONEY", "HOOD", "HOOK", "HORN", "HORSE",
                "HORSESHOE", "HOSPITAL", "HOTEL", "ICE", "ICE CREAM", "INDIA", "IRON", "IVORY", "JACK",
                "JAM", "JET", "JUPITER", "KANGAROO", "KETCHUP", "KEY", "KID", "KING", "KIWI", "KNIFE",
                "KNIGHT", "LAB", "LAP", "LASER", "LAWYER", "LEAD", "LEMON", "LEPRECHAUN", "LIFE", "LIGHT",
                "LIMOUSINE", "LINE", "LINK", "LION", "LITTER", "LOCH NESS", "LOCK", "LOG", "LONDON", "LUCK",
                "MAIL", "MAMMOTH", "MAPLE", "MARBLE", "MARCH", "MASS", "MATCH", "MERCURY", "MEXICO",
                "MICROSCOPE", "MILLIONAIRE", "MINE", "MINT", "MISSILE", "MODEL", "MOLE", "MOON", "MOSCOW",
                "MOUNT", "MOUSE", "MOUTH", "MUG", "NAIL", "NEEDLE", "NET", "NEW YORK", "NIGHT", "NINJA",
                "NOTE", "NOVEL", "NURSE", "NUT", "OCTOPUS", "OIL", "OLIVE", "OLYMPUS", "OPERA", "ORANGE",
                "ORGAN", "PALM", "PAN", "PANTS", "PAPER", "PARACHUTE", "PARK", "PART", "PASS", "PASTE",
                "PENGUIN", "PHOENIX", "PIANO", "PIE", "PILOT", "PIN", "PIPE", "PIRATE", "PISTOL", "PIT",
                "PITCH", "PLANE", "PLASTIC", "PLATE", "PLATYPUS", "PLAY", "PLOT", "POINT", "POISON",
                "POLE", "POLICE", "POOL", "PORT", "POST", "POUND", "PRESS", "PRINCESS", "PUMPKIN", "PUPIL",
                "PYRAMID", "QUEEN", "RABBIT", "RACKET", "RAY", "REVOLUTION", "RING", "ROBIN", "ROBOT",
                "ROCK", "ROME", "ROOT", "ROSE", "ROULETTE", "ROUND", "ROW", "RULER", "SATELLITE", "SATURN",
                "SCALE", "SCHOOL", "SCIENTIST", "SCORPION", "SCREEN", "SCUBA DIVER", "SEAL", "SERVER",
                "SHADOW", "SHAKESPEARE", "SHARK", "SHIP", "SHOE", "SHOP", "SHOT", "SINK", "SKYSCRAPER",
                "SLIP", "SLUG", "SMUGGLER", "SNOW", "SNOWMAN", "SOCK", "SOLDIER", "SOUL", "SOUND", "SPACE",
                "SPELL", "SPIDER", "SPIKE", "SPINE", "SPOT", "SPRING", "SPY", "SQUARE", "STADIUM", "STAFF",
                "STAR", "STATE", "STICK", "STOCK", "STRAW", "STREAM", "STRIKE", "STRING", "SUB", "SUIT",
                "SUPERHERO", "SWING", "SWITCH", "TABLE", "TABLET", "TAG", "TAIL", "TAP", "TEACHER",
                "TELESCOPE", "TEMPLE", "THEATER", "THIEF", "THUMB", "TICK", "TIE", "TIME", "TOKYO",
                "TOOTH", "TORCH", "TOWER", "TRACK", "TRAIN", "TRIANGLE", "TRIP", "TRUNK", "TUBE", "TURKEY",
                "UNDERTAKER", "UNICORN", "VACUUM", "VAN", "VET", "WAKE", "WALL", "WAR", "WASHER",
                "WASHINGTON", "WATCH", "WATER", "WAVE", "WEB", "WELL", "WHALE", "WHIP", "WIND", "WITCH",
                "WORM", "YARD"
            ]
        
        size = self.config.board_size
        selected_words = random.sample(words, size)
        
        # Calculate card distribution
        if size == 25:
            red_count, blue_count, assassin_count = 9, 8, 1
        elif size == 36:
            red_count, blue_count, assassin_count = 12, 11, 2
        elif size == 49:
            red_count, blue_count, assassin_count = 17, 16, 2
        elif size == 64:
            red_count, blue_count, assassin_count = 20, 19, 3
        else:
            # Safe default fallback for any other sizes if ever allowed
            red_count = (size // 3) + 1
            blue_count = red_count - 1
            assassin_count = max(1, size // 25)
            
        neutral_count = size - red_count - blue_count - assassin_count
        
        types = ([CardType.RED] * red_count) + ([CardType.BLUE] * blue_count) + \
                ([CardType.NEUTRAL] * neutral_count) + ([CardType.ASSASSIN] * assassin_count)
        
        random.shuffle(types)
        
        self.cards = [CardState(word=w, type=t) for w, t in zip(selected_words, types)]
        self.log.append("Game initialized. Team RED starts.")

    def give_clue(self, team: Team, word: str, number: int):
        if self.phase not in [GamePhase.RED_SPYMASTER, GamePhase.BLUE_SPYMASTER]:
            raise ValueError(f"Invalid Move: It is currently {self.phase}. Only Spymasters can move now.")
        if team != self.current_turn:
            raise ValueError(f"Invalid Turn: It is {self.current_turn}'s turn, but {team} tried to move.")
        
        # Basic validation
        clue_upper = word.upper()
        if any(c.word.upper() == clue_upper and not c.revealed for c in self.cards):
             raise ValueError("Clue cannot be a word currently on the board!")
        
        # Check that clue doesn't contain a board word as a substring (or vice versa)
        for c in self.cards:
            if c.revealed:
                continue
            board_word = c.word.upper()
            # Clue contains board word as substring (e.g., "PINEAPPLE" contains "APPLE")
            if board_word in clue_upper and board_word != clue_upper:
                raise ValueError(f"Clue '{word}' cannot contain the board word '{c.word}' as a substring!")
            # Board word contains clue as substring (e.g., "APPLE" is in "PINEAPPLE")
            if clue_upper in board_word and clue_upper != board_word:
                raise ValueError(f"Clue '{word}' cannot be a part of the board word '{c.word}'!")


        self.last_clue = (word, number)
        # Using 0 or -1 for unlimited? Standard rules say number + 1 guesses allowed.
        # If number is 0 (special rule usually means unlimited), let's just treat it as simple N
        # Standard implementation: they get N + 1 guesses.
        self.remaining_guesses = number + 1 
        
        self.log.append(f"{team.value} Spymaster gives clue: {word} {number}")
        self.turn_count += 1
        
        # Add to structured clue history
        self.clue_history.append({
            "team": team.value,
            "clue": word,
            "number": number,
            "guesses": []
        })

        
        # Switch phase
        if self.current_turn == Team.RED:
            self.phase = GamePhase.RED_GUESSER
        else:
            self.phase = GamePhase.BLUE_GUESSER

            
        self.save_history()


    def guess_card(self, team: Team, word: str):
        if self.phase not in [GamePhase.RED_GUESSER, GamePhase.BLUE_GUESSER]:
            raise ValueError(f"Invalid Move: It is currently {self.phase}. Only Guessers can move now.")
        if team != self.current_turn:
            raise ValueError(f"Invalid Turn: It is {self.current_turn}'s turn, but {team} tried to move.")
        
        card = next((c for c in self.cards if c.word == word), None)
        if not card:
            raise ValueError("Card not found")
        if card.revealed:
            raise ValueError("Card already revealed")

        card.revealed = True
        log_msg = f"{team.value} guesses {word}..."
        self.turn_count += 1

        
        # Add to current clue's guess history
        if self.clue_history:
            self.clue_history[-1]["guesses"].append({
                "word": word,
                "result": card.type.value  # RED, BLUE, NEUTRAL, or ASSASSIN
            })


        if card.type == CardType.ASSASSIN:
            self.log.append(f"{log_msg} It's the ASSASSIN! Game Over.")
            self.winner = Team.BLUE if self.current_turn == Team.RED else Team.RED
            self.phase = GamePhase.GAME_OVER
            self.save_history() # Auto-save
            return True # Turn ends

        if card.type == CardType.NEUTRAL:
            self.log.append(f"{log_msg} It's a Civilian. Turn Over.")
            self._end_turn()
            return True

        if card.type == Team(self.config.opponent_team(self.current_turn)):
            self.log.append(f"{log_msg} It's the Opponent's card! Turn Over.")
            # Check if this reveal caused the opponent to win
            if self._check_win():
                self.phase = GamePhase.GAME_OVER
                return True
            self._end_turn()
            return True

            
        # Correct guess
        self.log.append(f"{log_msg} Correct!")
        self.remaining_guesses -= 1
        
        # Check win condition
        if self._check_win():
             self.phase = GamePhase.GAME_OVER
             return True

        if self.remaining_guesses <= 0:
            self.log.append("Out of guesses. Turn Over.")
            self._end_turn()
            return True
            
        self.save_history()
        return False # Turn continues


    def end_turn_manually(self, team: Team):
        if self.phase not in [GamePhase.RED_GUESSER, GamePhase.BLUE_GUESSER]:
             raise ValueError("Cannot end turn now")
        if team != self.current_turn:
             raise ValueError("Not your turn")
        
        self.log.append(f"{team.value} ends turn manually.")
        self._end_turn()
        self.save_history()


    def _end_turn(self):
        self.turn_count += 1
        self.last_clue = None
        self.remaining_guesses = 0
        if self.current_turn == Team.RED:
            self.current_turn = Team.BLUE
            self.phase = GamePhase.BLUE_SPYMASTER
        else:
            self.current_turn = Team.RED
            self.phase = GamePhase.RED_SPYMASTER

    def _check_win(self) -> bool:
        red_cards_left = sum(1 for c in self.cards if c.type == CardType.RED and not c.revealed)
        blue_cards_left = sum(1 for c in self.cards if c.type == CardType.BLUE and not c.revealed)
        
        if red_cards_left == 0:
            self.winner = Team.RED
            self.log.append("Team RED wins!")
            self.save_history() # Auto-save
            return True
        elif blue_cards_left == 0:
            self.winner = Team.BLUE
            self.log.append("Team BLUE wins!")
            self.save_history() # Auto-save
            return True
        return False

    def get_state(self):
        return GameState(
            id=self.id,
            cards=self.cards,
            current_turn=self.current_turn,
            phase=self.phase,
            players=self.config.players,
            llm_model=self.config.llm_model,
            score={

                Team.RED: sum(1 for c in self.cards if c.type == CardType.RED and c.revealed),
                Team.BLUE: sum(1 for c in self.cards if c.type == CardType.BLUE and c.revealed)
            },
            winner=self.winner,
            last_clue=self.last_clue,
            remaining_guesses=self.remaining_guesses,
            turn_count=self.turn_count,
            log=self.log,
            clue_history=self.clue_history,
            reasoning_log=self.reasoning_log
        )

        
    def save_history(self):
        filename = f"history/game_history_{self.id}.json"
        data = {
            "game_id": self.id,
            "cards": [{"word": c.word, "type": c.type.value, "revealed": c.revealed} for c in self.cards],
            "winner": self.winner,
            "log": self.log,
            "reasoning_log": self.reasoning_log,
            "final_score": {
                Team.RED: sum(1 for c in self.cards if c.type == CardType.RED and c.revealed),
                Team.BLUE: sum(1 for c in self.cards if c.type == CardType.BLUE and c.revealed)
            }
        }

        with open(filename, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return filename

# Helper extension for opponents
def opponent_team(self, team: Team) -> Team:
    return Team.BLUE if team == Team.RED else Team.RED


GameConfig.opponent_team = opponent_team
