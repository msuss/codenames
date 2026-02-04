import React from 'react';
import { motion } from 'framer-motion';

const TYPE_COLORS = {
    RED: 'bg-code-red text-white',
    BLUE: 'bg-code-blue text-white',
    NEUTRAL: 'bg-code-neutral text-gray-900',
    ASSASSIN: 'bg-code-assassin text-white',
    UNKNOWN: 'bg-white/90 text-gray-800 hover:bg-white', // Default unrevealed
};

const BORDER_COLORS = {
    RED: 'border-code-red',
    BLUE: 'border-code-blue',
    NEUTRAL: 'border-code-neutral',
    ASSASSIN: 'border-code-assassin',
    UNKNOWN: 'border-transparent'
};

const Card = ({ word, type, revealed, isSpymaster, onClick, disabled }) => {
    // Determine display style
    // If revealed, show actual type color.
    // If not revealed but spymaster, show border/tint or specific style?
    // Standard Codenames: Spymaster sees color. Guesser sees plain card.

    const getCardStyle = () => {
        if (revealed) {
            return TYPE_COLORS[type] || TYPE_COLORS.UNKNOWN;
        }
        if (isSpymaster) {
            // Spymaster view of unrevealed card:
            // Show color as a tint or border? Usually full color but darker/tinted to show it's unrevealed.
            // Let's use a subtle gradient or full color with opacity for premium feel.
            // OR simply use the color but maybe with an "UNREVEALED" texture.
            return `${TYPE_COLORS[type]} opacity-70`;
            // Actually, if spymaster sees it, they need to know the color.
            // Let's stick to full color but formatted differently?
            // Or just the same color.
        }
        return TYPE_COLORS.UNKNOWN;
    };

    const baseStyle = "relative w-full aspect-[16/9] rounded-lg md:rounded-xl shadow-lg cursor-pointer flex items-center justify-center font-bold select-none transition-all duration-300";

    // Dynamic text size based on card count/density if passed, 
    // but for now let's just make it a bit smaller generally and use responsive classes
    const fontSizeStyle = "text-[10px] sm:text-xs md:text-sm lg:text-base px-1 text-center truncate";

    const colorStyle = getCardStyle();

    return (
        <motion.div
            className={`${baseStyle} ${colorStyle} ${revealed ? 'ring-4 ring-yellow-400 shadow-[0_0_15px_rgba(250,204,21,0.5)]' : ''}`}
            onClick={!revealed && !disabled ? onClick : undefined}
            whileHover={!revealed && !disabled ? { scale: 1.05, y: -5 } : {}}
            whileTap={!revealed && !disabled ? { scale: 0.95 } : {}}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
        >
            <span className={`z-10 uppercase tracking-tight md:tracking-widest ${fontSizeStyle}`}>{word}</span>

            {/* Premium overlay for unrevealed cards to give them texture */}
            {!revealed && !isSpymaster && (
                <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-white/40 to-transparent pointer-events-none" />
            )}

            {/* Revealed overlay marker (optional, cross or check) */}
            {revealed && type === 'ASSASSIN' && (
                <div className="absolute inset-0 flex items-center justify-center text-4xl opacity-50">☠️</div>
            )}
        </motion.div>
    );
};

export default Card;
