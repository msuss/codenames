import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

export const api = {
    createGame: async (difficulty = 'normal', players = null, llmModel = 'gpt-4o', boardSize = 25, accessToken = null) => {
        const config = accessToken ? { headers: { 'X-Access-Token': accessToken } } : {};
        const res = await axios.post(`${API_URL}/game/create`, { difficulty, players, llm_model: llmModel, board_size: boardSize }, config);
        return res.data;
    },

    getGameState: async (gameId) => {
        const res = await axios.get(`${API_URL}/game/${gameId}`);
        return res.data;
    },

    sendMove: async (gameId, actionType, payload) => {
        const res = await axios.post(`${API_URL}/game/${gameId}/move`, {
            action_type: actionType,
            payload
        });
        return res.data;
    },

    triggerAgent: async (gameId, turnCount, accessToken = null) => {
        const params = turnCount !== undefined ? `?expected_turn_count=${turnCount}` : '';
        const config = accessToken ? { headers: { 'X-Access-Token': accessToken } } : {};
        const res = await axios.post(`${API_URL}/game/${gameId}/agent-move${params}`, {}, config);
        return res.data;
    },

    // History/Replay API
    listHistory: async () => {
        const res = await axios.get(`${API_URL}/history/list`);
        return res.data;
    },

    getHistory: async (gameId) => {
        const res = await axios.get(`${API_URL}/history/${gameId}`);
        return res.data;
    }
};

export class GameSocket {
    constructor(gameId, onMessage) {
        this.gameId = gameId;
        this.onMessage = onMessage;
        this.socket = null;
    }

    connect() {
        this.socket = new WebSocket(`${WS_URL}/${this.gameId}`);

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.onMessage(data);
        };

        this.socket.onopen = () => {
            console.log('WebSocket Connected');
        };

        this.socket.onclose = () => {
            console.log('WebSocket Disconnected');
        };
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}
