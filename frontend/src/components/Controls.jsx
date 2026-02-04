import React, { useState } from 'react';
import { Send, SkipForward } from 'lucide-react';

const Controls = ({ phase, role, team, turn, lastClue, remainingGuesses, onGiveClue, onEndTurn, onAgentMove, isAgentThinking, log, godMode, onToggleRole }) => {
    const [clueWord, setClueWord] = useState('');
    const [clueNumber, setClueNumber] = useState(1);
    const [error, setError] = useState(null);

    // In local multiplayer/debug mode, we essentially play as both teams
    const isMyTurn = true; // Allow interaction for whoever's turn it is
    const isSpymasterPhase = phase.includes('SPYMASTER');
    const isGuesserPhase = phase.includes('GUESSER');

    const handleSubmitClue = (e) => {
        e.preventDefault();
        setError(null);
        if (!clueWord.trim()) {
            setError("Clue word is required");
            return;
        }
        if (/\s/.test(clueWord.trim())) {
            setError("Clue must be a single word");
            return;
        }
        onGiveClue(clueWord.trim(), parseInt(clueNumber));
        setClueWord('');
        setClueNumber(1);
    };

    return (
        <div className="w-full max-w-5xl mx-auto p-4 flex flex-col md:flex-row gap-4">
            {/* Game Status Panel */}
            <div className="flex-1 glass-panel rounded-xl p-4 min-h-[150px] flex flex-col justify-between">
                <div>
                    <h2 className="text-xl font-bold mb-2">
                        Turn: <span className={turn === 'RED' ? 'text-code-red' : 'text-code-blue'}>{turn}</span> ({isSpymasterPhase ? 'Spymaster' : 'Guesser'})
                    </h2>
                    {lastClue && (
                        <div className="bg-slate-800/50 p-2 rounded-lg mb-2">
                            <span className="text-gray-400 text-sm">Current Clue:</span>
                            <div className="text-lg font-mono">
                                "{lastClue[0]}" for {lastClue[1]} <span className="text-xs text-gray-500">({remainingGuesses} guesses left)</span>
                            </div>
                        </div>
                    )}
                </div>

                {/* Helper Action: Trigger Agent */}
                {isMyTurn && (
                    <div className="flex items-center gap-3">
                        <button
                            onClick={onAgentMove}
                            disabled={isAgentThinking}
                            className={`mt-2 bg-purple-600 hover:bg-purple-700 text-white text-xs py-1 px-3 rounded self-start transition-colors ${isAgentThinking ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                            {isAgentThinking ? '🤖 Thinking...' : 'Ask Agent to Move'}
                        </button>
                        {isAgentThinking && (
                            <div className="flex items-center gap-2 mt-1">
                                <span className="relative flex h-2 w-2">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-purple-500"></span>
                                </span>
                                <span className="text-[10px] text-purple-400 font-bold uppercase animate-pulse">Agent is thinking...</span>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Action Panel */}
            <div className="flex-1 glass-panel rounded-xl p-4 flex items-center justify-center">
                {isMyTurn && isSpymasterPhase && (role === 'SPYMASTER' || godMode) ? (
                    <form onSubmit={handleSubmitClue} className="flex flex-col gap-3 w-full max-w-md">
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={clueWord}
                                onChange={(e) => setClueWord(e.target.value)}
                                placeholder="Clue Word"
                                autoFocus
                                className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
                            />
                            <input
                                type="number"
                                min="0"
                                max="25"
                                value={clueNumber}
                                onChange={(e) => setClueNumber(e.target.value)}
                                className="w-16 bg-slate-800 border-slate-700 rounded-lg px-2 text-center"
                            />
                        </div>
                        {error && <p className="text-red-400 text-xs">{error}</p>}
                        <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg flex items-center justify-center gap-2 transition-transform active:scale-95">
                            <Send size={18} /> Give Clue
                        </button>
                    </form>
                ) : isMyTurn && isGuesserPhase && (role === 'GUESSER' || godMode) ? (
                    <div className="text-center">
                        <p className="mb-3 text-lg">Select a card to guess...</p>
                        <button
                            onClick={onEndTurn}
                            className="bg-red-600 hover:bg-red-700 text-white px-6 py-2 rounded-lg flex items-center gap-2 mx-auto transition-transform active:scale-95"
                        >
                            <SkipForward size={18} /> End Turn
                        </button>
                    </div>
                ) : (
                    <div className="text-gray-400 text-center space-y-3">
                        <p className="animate-pulse italic">
                            Waiting for {turn} {isSpymasterPhase ? 'Spymaster' : 'Guesser'}...
                        </p>
                        {onToggleRole && (
                            <button
                                onClick={onToggleRole}
                                className="text-[10px] bg-slate-800 hover:bg-slate-700 px-3 py-1 rounded-full border border-slate-700 text-blue-400 transition-colors"
                            >
                                Switch to {isSpymasterPhase ? 'Spymaster' : 'Guesser'} View
                            </button>
                        )}
                    </div>
                )}
            </div>

            {/* Log Panel */}
            <div className="flex-1 glass-panel rounded-xl p-4 h-[150px] overflow-y-auto text-xs font-mono text-gray-300">
                <h3 className="text-gray-500 font-bold mb-2 uppercase tracking-wider text-[10px]">Game Log</h3>
                {log.slice().reverse().map((entry, i) => (
                    <div key={i} className="mb-1 border-b border-white/5 pb-1 last:border-0">{entry}</div>
                ))}
            </div>
        </div>
    );
};

export default Controls;
