from game_engine import CodenamesGame, GameConfig, Team, CardType

def test_counts(size):
    config = GameConfig(board_size=size)
    game = CodenamesGame(id="test", config=config)
    
    red = sum(1 for c in game.cards if c.type == CardType.RED)
    blue = sum(1 for c in game.cards if c.type == CardType.BLUE)
    neutral = sum(1 for c in game.cards if c.type == CardType.NEUTRAL)
    assassin = sum(1 for c in game.cards if c.type == CardType.ASSASSIN)
    
    print(f"Size {size}: Red={red}, Blue={blue}, Neutral={neutral}, Assassin={assassin}, Total={red+blue+neutral+assassin}")

test_counts(25)
test_counts(36)
test_counts(49)
test_counts(64)
