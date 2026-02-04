import React, { useState, useEffect, useRef } from 'react';
import Board from './components/Board';
import Controls from './components/Controls';
import ReplayView from './components/ReplayView';
import { api, GameSocket } from './services/api';
import { Users, User, Eye, Cpu, Brain, History, RefreshCw } from 'lucide-react';

function App() {
  const [view, setView] = useState('LOBBY'); // LOBBY, GAME, REPLAY
  const [gameId, setGameId] = useState('');
  const [role, setRole] = useState('GUESSER');
  const [team, setTeam] = useState('RED');
  const [players, setPlayers] = useState({
    RED_SPYMASTER: 'agent',
    RED_GUESSER: 'agent',
    BLUE_SPYMASTER: 'agent',
    BLUE_GUESSER: 'agent'
  });
  const [autoPlay, setAutoPlay] = useState(false);
  const [godMode, setGodMode] = useState(false);
  const [instantMoves, setInstantMoves] = useState(false);
  const [gameState, setGameState] = useState(null);
  const [isAgentThinking, setIsAgentThinking] = useState(false);
  const [llmModel, setLlmModel] = useState('gpt-5-mini');
  const [boardSize, setBoardSize] = useState(25);
  const [replayGameId, setReplayGameId] = useState(null);
  const [accessToken, setAccessToken] = useState(localStorage.getItem('access_token') || '');
  const socketRef = useRef(null);

  useEffect(() => {
    localStorage.setItem('access_token', accessToken);
  }, [accessToken]);

  // cleanup socket on unmount
  useEffect(() => {
    return () => {
      if (socketRef.current) socketRef.current.disconnect();
    };
  }, []);

  // Auto-play logic
  useEffect(() => {
    console.log("Autoplay check:", { autoPlay, phase: gameState?.phase, players: gameState?.players, isAgentThinking });
    if (!autoPlay || !gameState || gameState.phase === 'GAME_OVER' || isAgentThinking) {
      if (!autoPlay) console.log("Autoplay is OFF");
      if (isAgentThinking) console.log("Agent is already thinking, skipping autoplay trigger");
      return;
    }

    const currentRole = gameState.phase;
    console.log("Current role:", currentRole, "Player type:", gameState.players[currentRole]);

    if (gameState.players[currentRole] === 'agent') {
      console.log("Triggering agent move in 1.5s...");
      const timer = setTimeout(() => {
        onAgentMove();
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [gameState, autoPlay]); // gameState changes on every move/phase change, so this should trigger


  const handleCreateGame = async () => {
    try {
      const data = await api.createGame('normal', players, llmModel, boardSize, accessToken);
      setGameId(data.game_id);
    } catch (err) {
      console.error(err);
      alert('Failed to create game');
    }
  };

  const handleJoinGame = async () => {
    if (!gameId) return;
    try {
      socketRef.current = new GameSocket(gameId, (data) => {
        if (data.type === 'STATE_UPDATE') {
          setGameState(data.state);
        }
      });
      socketRef.current.connect();

      const state = await api.getGameState(gameId);
      setGameState(state);
      setView('GAME');
    } catch (err) {
      console.error(err);
      alert('Failed to join game');
    }
  };

  const onGiveClue = async (word, number) => {
    try {
      const res = await api.sendMove(gameId, 'CLUE', { word, number });
      if (res.state) setGameState(res.state);
      return res.state;
    } catch (err) {
      alert(err.response?.data?.detail || 'Error sending clue');
    }
  };

  const onGuessCard = async (word, isAgentForced = false) => {
    if (!isAgentForced && view === 'GAME' && gameState && gameState.players[gameState.phase] === 'agent') return; // Don't allow human guess if agent is active
    try {
      const res = await api.sendMove(gameId, 'GUESS', { word });
      if (res.state) setGameState(res.state);
      return res.state;
    } catch (err) {
      alert(err.response?.data?.detail || 'Error guessing card');
    }
  };

  const onEndTurn = async () => {
    try {
      const res = await api.sendMove(gameId, 'END_TURN', {});
      if (res.state) setGameState(res.state);
      return res.state;
    } catch (err) {
      console.error(err);
    }
  };

  const onAgentMove = async (isForced = false) => {
    if (isAgentThinking) return;

    setIsAgentThinking(true);
    try {
      const turnCount = gameState?.turn_count;
      const res = await api.triggerAgent(gameId, turnCount, accessToken);

      // Check if request was ignored due to stale state
      if (res.status === 'ignored') {
        console.log('Agent move ignored:', res.reason);
        return;
      }

      const move = res.move;
      const startPhase = gameState?.phase;

      // Update state immediately from response
      if (res.state) setGameState(res.state);

      // If it's a guesser and has "words" to guess
      if (move.words && move.words.length > 0) {
        if (move.words.includes("END_TURN") && move.words.length === 1) {
          await onEndTurn();
        } else {
          // Animate guesses
          for (const word of move.words) {
            if (word === "END_TURN") {
              await onEndTurn();
              break;
            }

            // Artificial delay for "thinking" unless instant moves is on
            if (!instantMoves) {
              await new Promise(r => setTimeout(r, 1500));
            }

            try {
              const newState = await onGuessCard(word, true); // Force agent move

              // If phase changed (turn ended due to bad guess or win), stop guessing
              if (newState && newState.phase !== startPhase) {
                console.log("Turn ended early or game over, stopping agent guesses.");
                return;
              }
            } catch (e) {
              console.error("Agent guess failed:", e);
              break;
            }
          }

          // Only end turn manually if the turn is STILL active for this team
          // (i.e. if the agent made all correct guesses and wants to pass)
          const finalState = await api.getGameState(gameId);
          if (finalState.phase === startPhase) {
            await onEndTurn();
          }
        }
      }
    } catch (err) {
      console.error(err);
      // If it fails, disable auto-play to prevent potential infinite error loops
      setAutoPlay(false);
      alert('Agent move failed. Auto-play disabled.');
    } finally {
      setIsAgentThinking(false);
    }
  };

  const togglePlayerType = (roleKey) => {
    setPlayers(prev => ({
      ...prev,
      [roleKey]: prev[roleKey] === 'human' ? 'agent' : 'human'
    }));
  };

  // REPLAY view
  if (view === 'REPLAY') {
    return <ReplayView initialGameId={replayGameId} onBack={() => setView('LOBBY')} />;
  }

  if (view === 'LOBBY') {

    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 p-4 relative overflow-hidden">
        {/* Background blobs */}
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-code-red/20 rounded-full blur-3xl" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-code-blue/20 rounded-full blur-3xl" />

        <div className="glass-panel p-8 rounded-2xl w-full max-w-md z-10">
          <h1 className="text-4xl font-black mb-8 text-center bg-gradient-to-r from-code-red to-code-blue bg-clip-text text-transparent">
            CODENAMES
          </h1>

          <div className="space-y-6">
            <div className="space-y-4">
              <p className="text-xs text-gray-400 uppercase tracking-widest font-bold">Player Configuration</p>
              <div className="grid grid-cols-2 gap-4">
                {/* RED TEAM CONFIG */}
                <div className="space-y-2">
                  <p className="text-[10px] text-code-red font-bold">RED TEAM</p>
                  <button
                    onClick={() => togglePlayerType('RED_SPYMASTER')}
                    className={`w-full text-[10px] py-2 rounded border transition-colors ${players.RED_SPYMASTER === 'agent' ? 'bg-code-red/20 border-code-red text-white' : 'border-slate-700 text-gray-500 hover:border-slate-500'}`}
                  >
                    Spy: {players.RED_SPYMASTER === 'agent' ? '🤖 AGENT' : '👤 HUMAN'}
                  </button>
                  <button
                    onClick={() => togglePlayerType('RED_GUESSER')}
                    className={`w-full text-[10px] py-2 rounded border transition-colors ${players.RED_GUESSER === 'agent' ? 'bg-code-red/20 border-code-red text-white' : 'border-slate-700 text-gray-500 hover:border-slate-500'}`}
                  >
                    Guess: {players.RED_GUESSER === 'agent' ? '🤖 AGENT' : '👤 HUMAN'}
                  </button>
                </div>
                {/* BLUE TEAM CONFIG */}
                <div className="space-y-2">
                  <p className="text-[10px] text-code-blue font-bold">BLUE TEAM</p>
                  <button
                    onClick={() => togglePlayerType('BLUE_SPYMASTER')}
                    className={`w-full text-[10px] py-2 rounded border transition-colors ${players.BLUE_SPYMASTER === 'agent' ? 'bg-code-blue/20 border-code-blue text-white' : 'border-slate-700 text-gray-500 hover:border-slate-500'}`}
                  >
                    Spy: {players.BLUE_SPYMASTER === 'agent' ? '🤖 AGENT' : '👤 HUMAN'}
                  </button>
                  <button
                    onClick={() => togglePlayerType('BLUE_GUESSER')}
                    className={`w-full text-[10px] py-2 rounded border transition-colors ${players.BLUE_GUESSER === 'agent' ? 'bg-code-blue/20 border-code-blue text-white' : 'border-slate-700 text-gray-500 hover:border-slate-500'}`}
                  >
                    Guess: {players.BLUE_GUESSER === 'agent' ? '🤖 AGENT' : '👤 HUMAN'}
                  </button>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <p className="text-xs text-gray-400 uppercase tracking-widest font-bold">Host Settings</p>
              <div className="space-y-2">
                <label className="text-[10px] text-gray-500 uppercase tracking-tight">Access Token (Host Secret)</label>
                <input
                  type="password"
                  value={accessToken}
                  onChange={(e) => setAccessToken(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 p-2 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 outline-none"
                  placeholder="Enter token for AI/Game Creation"
                />
              </div>

              <p className="text-xs text-gray-400 uppercase tracking-widest font-bold">Lobby Configuration</p>

              <div className="space-y-2">
                <label className="text-[10px] text-gray-500 uppercase tracking-tight">AI Agent Model</label>
                <select
                  value={llmModel}
                  onChange={(e) => setLlmModel(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 p-2 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  <option value="gpt-4.1-mini">gpt-4.1-mini</option>
                  <option value="gpt-5-mini">gpt-5-mini</option>
                  <option value="gpt-5-nano">gpt-5-nano</option>
                  <option value="gpt-5.2">gpt-5.2</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] text-gray-500 uppercase tracking-tight">Board Size</label>
                <select
                  value={boardSize}
                  onChange={(e) => setBoardSize(parseInt(e.target.value))}
                  className="w-full bg-slate-800 border border-slate-700 p-2 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  <option value={25}>5x5 (25 cards)</option>
                  <option value={36}>6x6 (36 cards)</option>
                  <option value={49}>7x7 (49 cards)</option>
                  <option value={64}>8x8 (64 cards)</option>
                </select>
              </div>
            </div>

            <div>

              <p className="text-sm text-gray-400 mb-2">Create New Game</p>
              <button
                onClick={handleCreateGame}
                className="w-full bg-slate-800 hover:bg-slate-700 py-3 rounded-xl transition-all border border-slate-700"
              >
                Initialize Game Session
              </button>

              <button
                onClick={() => {
                  setReplayGameId(null);
                  setView('REPLAY');
                }}
                className="w-full mt-3 bg-slate-800/50 hover:bg-slate-700 py-2 rounded-xl transition-all border border-slate-700/50 flex items-center justify-center gap-2 text-gray-400 hover:text-white"
              >
                <History size={16} /> View Game History
              </button>
            </div>

            <div className="relative">
              <div className="absolute inset-x-0 top-1/2 h-px bg-slate-700/50"></div>
              <span className="relative z-10 bg-slate-900/50 px-2 text-xs text-gray-500 block w-max mx-auto">OR JOIN EXISTING</span>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-widest">Game ID</label>
                <input
                  value={gameId}
                  onChange={(e) => setGameId(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 p-3 rounded-lg mt-1 font-mono text-center tracking-widest text-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  placeholder="ENTER CODE"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-gray-500 uppercase tracking-widest">Team</label>
                  <div className="flex bg-slate-800 p-1 rounded-lg mt-1">
                    <button
                      onClick={() => setTeam('RED')}
                      className={`flex-1 py-1 rounded text-sm ${team === 'RED' ? 'bg-code-red text-white' : 'text-gray-400'}`}
                    >Red</button>
                    <button
                      onClick={() => setTeam('BLUE')}
                      className={`flex-1 py-1 rounded text-sm ${team === 'BLUE' ? 'bg-code-blue text-white' : 'text-gray-400'}`}
                    >Blue</button>
                  </div>
                </div>

                <div>
                  <label className="text-xs text-gray-500 uppercase tracking-widest">Role</label>
                  <div className="flex bg-slate-800 p-1 rounded-lg mt-1">
                    <button
                      onClick={() => setRole('SPYMASTER')}
                      className={`flex-1 py-1 rounded flex items-center justify-center ${role === 'SPYMASTER' ? 'bg-gray-600 text-white' : 'text-gray-400'}`}
                    ><User size={16} /></button>
                    <button
                      onClick={() => setRole('GUESSER')}
                      className={`flex-1 py-1 rounded flex items-center justify-center ${role === 'GUESSER' ? 'bg-gray-600 text-white' : 'text-gray-400'}`}
                    ><Eye size={16} /></button>
                  </div>
                </div>
              </div>

              <button
                onClick={handleJoinGame}
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 py-3 rounded-xl font-bold shadow-lg shadow-blue-900/20 transition-all active:scale-95"
              >
                ENTER GAME
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* HUD Bar */}
      <header className="fixed top-0 inset-x-0 h-16 glass-panel z-50 px-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="font-bold text-xl tracking-tighter">CODENAMES <span className="text-blue-400">AI</span></h1>
          <div className="px-3 py-1 bg-slate-800 rounded text-xs font-mono text-gray-400">ID: {gameId}</div>
        </div>

        <div className="flex items-center gap-6">
          {view === 'GAME' && (
            <div className="flex gap-2">
              <button
                onClick={() => setGodMode(!godMode)}
                className={`p-2 rounded-full transition-all ${godMode ? 'bg-yellow-500 text-black shadow-[0_0_15px_rgba(234,179,8,0.5)]' : 'bg-slate-800 text-gray-500'}`}
                title="God View (See Everything)"
              >
                <Eye size={20} />
              </button>
              <button
                onClick={() => setInstantMoves(!instantMoves)}
                className={`p-2 rounded-full transition-all ${instantMoves ? 'bg-purple-500 text-white' : 'bg-slate-800 text-gray-500'}`}
                title="Instant Moves (No Animation)"
              >
                <Cpu size={20} />
              </button>
            </div>
          )}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setAutoPlay(!autoPlay)}
              className={`px-3 py-1 rounded-full text-[10px] font-bold border transition-all ${autoPlay ? 'bg-green-600 border-green-500 text-white' : 'bg-slate-800 border-slate-700 text-gray-500'}`}
            >
              {autoPlay ? 'AUTO-PLAY: ON' : 'AUTO-PLAY: OFF'}
            </button>
            <div className={`w-3 h-3 rounded-full ${team === 'RED' ? 'bg-code-red' : 'bg-code-blue'}`} />
            <span className="font-bold text-sm">{team}: {role}</span>
            <button
              onClick={() => setRole(role === 'SPYMASTER' ? 'GUESSER' : 'SPYMASTER')}
              className="p-1 hover:bg-slate-800 rounded transition-colors text-gray-400 hover:text-white"
              title="Switch Role"
            >
              <RefreshCw size={14} />
            </button>
          </div>


          <div className="flex gap-4 text-sm font-bold">
            <span className="text-code-red">RED: {gameState?.score?.RED || 0}</span>
            <span className="text-code-blue">BLUE: {gameState?.score?.BLUE || 0}</span>
          </div>
        </div>
      </header>

      {/* Main Game Area */}
      <main className={`pt-24 pb-12 px-4 flex gap-4 ${godMode ? 'max-w-[1400px] mx-auto' : ''}`}>
        <div className="flex-1">
          {gameState && (
            <>
              <Board
                cards={gameState.cards}
                isSpymaster={role === 'SPYMASTER' || godMode}
                onCardClick={onGuessCard}
                disabled={gameState.phase === 'GAME_OVER' || (!godMode && (role === 'GUESSER' && (!gameState.phase.includes(team) || !gameState.phase.includes('GUESSER'))))}
              />

              <div className="mt-8">
                <Controls
                  phase={gameState.phase}
                  role={role}
                  team={team}
                  turn={gameState.current_turn}
                  lastClue={gameState.last_clue}
                  remainingGuesses={gameState.remaining_guesses}
                  onGiveClue={onGiveClue}
                  onEndTurn={onEndTurn}
                  onAgentMove={onAgentMove}
                  isAgentThinking={isAgentThinking}
                  log={gameState.log}
                  godMode={godMode}
                  onToggleRole={() => setRole(role === 'SPYMASTER' ? 'GUESSER' : 'SPYMASTER')}
                />
              </div>
            </>
          )}
        </div>

        {/* God View Panel */}
        {godMode && gameState && (
          <div className="w-[350px] glass-panel rounded-xl p-4 overflow-hidden flex flex-col max-h-[calc(100vh-120px)] sticker-panel">
            <h2 className="text-yellow-500 font-bold mb-4 flex items-center gap-2 uppercase tracking-widest text-sm">
              <Brain size={16} /> Agent Reasoning Log
            </h2>
            <div className="flex-1 overflow-y-auto space-y-4 pr-2">
              {gameState.reasoning_log?.slice().reverse().map((entry, i) => (
                <div key={i} className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/50">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-[10px] font-bold text-gray-400 uppercase">{entry.role}</span>
                    <span className="text-[9px] text-gray-600 font-mono">{new Date(entry.timestamp).toLocaleTimeString()}</span>
                  </div>
                  <p className="text-xs font-mono text-blue-300 mb-2">{entry.action}</p>
                  <p className="text-xs text-gray-300 italic">"{entry.reasoning}"</p>
                </div>
              ))}
              {(!gameState.reasoning_log || gameState.reasoning_log.length === 0) && (
                <p className="text-center text-gray-500 text-xs italic mt-10">No agent reasoning recorded yet.</p>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Game Over Overlay */}
      {gameState?.phase === 'GAME_OVER' && (
        <div className="fixed inset-0 z-[100] bg-black/80 flex items-center justify-center p-4">
          <div className="glass-panel p-8 rounded-2xl max-w-lg w-full text-center">
            <h2 className="text-5xl font-black mb-4">GAME OVER</h2>
            <p className="text-2xl mb-8">
              <span className={gameState.winner === 'RED' ? 'text-code-red' : 'text-code-blue'}>{gameState.winner}</span> WINS!
            </p>
            <div className="flex flex-col gap-3">
              <button
                onClick={() => setView('LOBBY')}
                className="w-full bg-white text-black px-8 py-3 rounded-xl font-bold hover:bg-gray-200 transition-colors"
              >
                Back to Lobby
              </button>
              <button
                onClick={() => {
                  setReplayGameId(gameId);
                  setView('REPLAY');
                }}
                className="w-full bg-slate-800 text-white px-8 py-3 rounded-xl font-bold hover:bg-slate-700 transition-colors border border-slate-700 flex items-center justify-center gap-2"
              >
                <History size={20} /> View Game History
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
