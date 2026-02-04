import React from 'react';
import Card from './Card';

const Board = ({ cards, isSpymaster, onCardClick, disabled }) => {
    const cols = Math.sqrt(cards.length || 25);

    const isLargeBoard = cards.length > 25;

    return (
        <div
            className={`grid ${isLargeBoard ? 'gap-1 md:gap-1.5' : 'gap-1.5 md:gap-2 lg:gap-3'} p-2 md:p-4 max-w-7xl mx-auto`}
            style={{
                gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`,
                width: '100%'
            }}
        >
            {cards.map((card, index) => (
                <Card
                    key={`${card.word}-${index}`}
                    word={card.word}
                    type={card.team || card.type} // Backend might send 'team' or 'type'
                    revealed={card.revealed}
                    isSpymaster={isSpymaster}
                    onClick={() => onCardClick(card.word)}
                    disabled={disabled}
                />
            ))}
        </div>
    );
};

export default Board;
