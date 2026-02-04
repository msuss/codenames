import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import Board from './Board';
import { ChevronLeft, ChevronRight, SkipBack, SkipForward, Play, Pause, History, Eye } from 'lucide-react';

function ReplayView({ onBack, initialGameId }) {
    const [games, setGames] = useState([]);
    const [selectedGame, setSelectedGame] = useState(null);
    const [history, setHistory] = useState(null);
    const [currentStep, setCurrentStep] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);
    const [boardState, setBoardState] = useState([]);
    const [godMode, setGodMode] = useState(true);

    // Load game list and handle deep linking
    useEffect(() => {
        loadGames();
        if (initialGameId) {
            loadHistory(initialGameId);
        }
    }, [initialGameId]);

    // Auto-play
    useEffect(() => {
        if (isPlaying && history) {
            const maxSteps = history.log?.length || 0;
            if (currentStep < maxSteps - 1) {
                const timer = setTimeout(() => {
                    setCurrentStep(prev => prev + 1);
                }, 1000);
                return () => clearTimeout(timer);
            } else {
                setIsPlaying(false);
            }
        }
    }, [isPlaying, currentStep, history]);

    // Reconstruct board state when step changes
    useEffect(() => {
        if (history?.cards) {
            reconstructBoardState(currentStep);
        }
    }, [currentStep, history]);

    const loadGames = async () => {
        try {
            const data = await api.listHistory();
            setGames(data.games || []);
        } catch (err) {
            console.error('Failed to load games:', err);
        }
    };

    const loadHistory = async (gameId) => {
        try {
            const data = await api.getHistory(gameId);
            setHistory(data);
            setSelectedGame(gameId);
            setCurrentStep(0);
            setIsPlaying(false);

            // Initialize board state (all unrevealed)
            if (data.cards) {
                setBoardState(data.cards.map(c => ({ ...c, revealed: false })));
            }
        } catch (err) {
            console.error('Failed to load history:', err);
            alert('Failed to load game history');
        }
    };

    const reconstructBoardState = (step) => {
        if (!history?.cards || !history?.log) return;

        // Start with all cards unrevealed
        const newState = history.cards.map(c => ({ ...c, revealed: false }));

        // Process log entries up to current step to determine revealed cards
        for (let i = 0; i <= step && i < history.log.length; i++) {
            const entry = history.log[i];
            // Look for "guesses WORD..." pattern (handles both old and new combined format)
            const guessMatch = entry.match(/guesses (\S+)\.\.\./);
            if (guessMatch) {
                const guessedWord = guessMatch[1];
                const cardIndex = newState.findIndex(c => c.word === guessedWord);
                if (cardIndex !== -1) {
                    newState[cardIndex].revealed = true;
                }
            }
        }

        setBoardState(newState);
    };

    const maxSteps = history?.log?.length || 0;
    const currentLogEntry = history?.log?.[currentStep] || '';

    // Find matching reasoning for current action
    const currentReasoning = (() => {
        if (!history?.reasoning_log || !history?.log) return null;

        const entry = history.log[currentStep];
        if (!entry) return null;

        // Try to find the reasoning that matches this specific log entry
        // 1. If it's a clue
        if (entry.includes('gives clue:')) {
            const clueMatch = entry.match(/gives clue: (\S+) (\d+)/);
            if (clueMatch) {
                const searchStr = `Clue: ${clueMatch[1]} ${clueMatch[2]}`;
                // Find the reasoning entry for this clue
                return history.reasoning_log.find(r => r.action && r.action.includes(searchStr));
            }
        }

        // 2. If it's a guess
        if (entry.includes('guesses')) {
            const guessMatch = entry.match(/guesses (\S+)\.\.\./);
            if (guessMatch) {
                const guessedWord = guessMatch[1];
                // Find the latest reasoning that includes this word in its Guess Plan
                // We search backwards from the current estimated point to find the most RECENT plan for this word
                return history.reasoning_log
                    .slice()
                    .reverse()
                    .find(r => r.action && r.action.includes('Guess Plan') && r.action.includes(`'${guessedWord}'`));
            }
        }

        return null;
    })();

    if (!selectedGame) {
        // Game selection view
        return (
            <div className="min-h-screen bg-slate-900 text-white p-8">
                <div className="max-w-4xl mx-auto">
                    <div className="flex items-center gap-4 mb-8">
                        <button
                            onClick={onBack}
                            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors"
                        >
                            <ChevronLeft size={24} />
                        </button>
                        <h1 className="text-3xl font-bold flex items-center gap-3">
                            <History size={32} /> Game History
                        </h1>
                    </div>

                    {games.length === 0 ? (
                        <div className="text-center text-gray-500 py-20">
                            <History size={64} className="mx-auto mb-4 opacity-50" />
                            <p>No saved games found.</p>
                            <p className="text-sm mt-2">Play some games first!</p>
                        </div>
                    ) : (
                        <div className="grid gap-4">
                            {games.map(game => (
                                <button
                                    key={game.game_id}
                                    onClick={() => loadHistory(game.game_id)}
                                    disabled={game.error}
                                    className={`p-4 rounded-xl text-left transition-all ${game.error
                                        ? 'bg-slate-800/50 text-gray-500 cursor-not-allowed'
                                        : 'bg-slate-800 hover:bg-slate-700 hover:scale-[1.02]'
                                        }`}
                                >
                                    <div className="flex justify-between items-center">
                                        <div>
                                            <span className="font-mono text-lg">{game.game_id}</span>
                                            {!game.has_cards && !game.error && (
                                                <span className="ml-2 text-xs text-yellow-500">(no board data)</span>
                                            )}
                                            {game.error && (
                                                <span className="ml-2 text-xs text-red-500">(corrupted)</span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-4">
                                            {game.final_score && (
                                                <div className="text-sm">
                                                    <span className="text-red-400">RED: {game.final_score.RED}</span>
                                                    <span className="mx-2 text-gray-500">|</span>
                                                    <span className="text-blue-400">BLUE: {game.final_score.BLUE}</span>
                                                </div>
                                            )}
                                            {game.winner && (
                                                <span className={`px-3 py-1 rounded-full text-sm font-bold ${game.winner === 'RED' ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400'
                                                    }`}>
                                                    {game.winner} WINS
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // Replay view
    return (
        <div className="min-h-screen bg-slate-900 text-white">
            {/* Header */}
            <header className="fixed top-0 inset-x-0 h-16 glass-panel z-50 px-6 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => setSelectedGame(null)}
                        className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors"
                    >
                        <ChevronLeft size={20} />
                    </button>
                    <h1 className="font-bold text-xl">
                        REPLAY: <span className="font-mono text-blue-400">{selectedGame}</span>
                    </h1>
                </div>
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => setGodMode(!godMode)}
                        className={`p-2 rounded-lg transition-all ${godMode ? 'bg-yellow-500 text-black shadow-[0_0_10px_rgba(234,179,8,0.3)]' : 'bg-slate-800 text-gray-500'}`}
                        title={godMode ? "Switch to Player View" : "Switch to Spymaster View"}
                    >
                        <Eye size={20} />
                    </button>
                    {history?.winner && (
                        <span className={`px-3 py-1 rounded-full text-sm font-bold ${history.winner === 'RED' ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400'
                            }`}>
                            {history.winner} WINS
                        </span>
                    )}
                </div>
            </header>

            {/* Main content */}
            <main className="pt-24 pb-32 px-4 max-w-6xl mx-auto">
                {/* Board */}
                {boardState.length > 0 ? (
                    <Board
                        cards={boardState}
                        isSpymaster={godMode}
                        onCardClick={() => { }}
                        disabled={true}
                    />
                ) : (
                    <div className="text-center text-gray-500 py-20">
                        <p>No board data available for this game.</p>
                    </div>
                )}

                {/* Current log entry */}
                <div className="mt-8 p-4 rounded-xl bg-slate-800/50 border border-slate-700">
                    <div className="flex justify-between items-center mb-2">
                        <span className="text-xs text-gray-500 uppercase tracking-widest">
                            Step {currentStep + 1} of {maxSteps}
                        </span>
                    </div>
                    <p className="text-lg font-mono">{currentLogEntry || 'Game Start'}</p>

                    {currentReasoning && (
                        <div className="mt-3 pt-3 border-t border-slate-700">
                            <p className="text-xs text-yellow-500 uppercase tracking-widest mb-1">
                                {currentReasoning.role} Reasoning
                            </p>
                            <p className="text-sm text-gray-300 italic">"{currentReasoning.reasoning}"</p>
                        </div>
                    )}
                </div>
            </main>

            {/* Playback controls */}
            <div className="fixed bottom-0 inset-x-0 glass-panel p-4">
                <div className="max-w-2xl mx-auto">
                    {/* Progress bar */}
                    <div className="mb-4">
                        <input
                            type="range"
                            min={0}
                            max={Math.max(0, maxSteps - 1)}
                            value={currentStep}
                            onChange={(e) => setCurrentStep(parseInt(e.target.value))}
                            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                        />
                    </div>

                    {/* Control buttons */}
                    <div className="flex justify-center items-center gap-4">
                        <button
                            onClick={() => setCurrentStep(0)}
                            disabled={currentStep === 0}
                            className="p-3 rounded-full bg-slate-800 hover:bg-slate-700 disabled:opacity-30 transition-all"
                        >
                            <SkipBack size={20} />
                        </button>
                        <button
                            onClick={() => setCurrentStep(prev => Math.max(0, prev - 1))}
                            disabled={currentStep === 0}
                            className="p-3 rounded-full bg-slate-800 hover:bg-slate-700 disabled:opacity-30 transition-all"
                        >
                            <ChevronLeft size={24} />
                        </button>
                        <button
                            onClick={() => setIsPlaying(!isPlaying)}
                            className={`p-4 rounded-full transition-all ${isPlaying
                                ? 'bg-yellow-500 text-black hover:bg-yellow-400'
                                : 'bg-blue-500 text-white hover:bg-blue-400'
                                }`}
                        >
                            {isPlaying ? <Pause size={28} /> : <Play size={28} />}
                        </button>
                        <button
                            onClick={() => setCurrentStep(prev => Math.min(maxSteps - 1, prev + 1))}
                            disabled={currentStep >= maxSteps - 1}
                            className="p-3 rounded-full bg-slate-800 hover:bg-slate-700 disabled:opacity-30 transition-all"
                        >
                            <ChevronRight size={24} />
                        </button>
                        <button
                            onClick={() => setCurrentStep(maxSteps - 1)}
                            disabled={currentStep >= maxSteps - 1}
                            className="p-3 rounded-full bg-slate-800 hover:bg-slate-700 disabled:opacity-30 transition-all"
                        >
                            <SkipForward size={20} />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default ReplayView;
