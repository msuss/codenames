# Codenames with AI Agents

A high-performance Codenames web application featuring strategic AI agents, dynamic board sizes, and secure hosting capabilities.

## 🌟 Features

- **Strategic AI Agents**: Spymasters and Guessers powered by LLMs (OpenAI, Anthropic, Gemini). Agents use game history to find complex semantic connections.
- **Dynamic Board Sizes**: Choose from 5x5, 6x6, 7x7, or 8x8 grids with balanced card distributions.
- **God Mode & Reasoning Logs**: Peek behind the curtain to see the AI's internal thought process and all hidden cards.
- **Game Replay**: Step-by-step playback of past games with deep-link support.
- **Secure Hosting**: Built-in `ACCESS_TOKEN` protection to keep your API credits safe when hosting online.
- **Premium UI**: Dark-mode aesthetic with smooth animations and high-density layouts for large boards.

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- API Key (OpenAI, Anthropic, or Gemini)

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
```
Edit `.env` and add your `OPENAI_API_KEY`.

### 3. Frontend Setup
```bash
cd frontend
npm install
```

### 4. Running Locally
Run the helper script:
```bash
./start.sh
```
The game will be available at `http://localhost:5173`.

## 🛠️ Tech Stack

- **Frontend**: React, Vite, Framer Motion, Lucide Icons, Tailwind CSS.
- **Backend**: FastAPI, Uvicorn, Pydantic.
- **AI**: Structured JSON prompting with multi-provider support.
- **Persistence**: JSON-based game history logging.
