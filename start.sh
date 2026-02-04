#!/bin/bash

# Kill any existing processes on common ports
lsof -ti:8000,5173 | xargs kill -9 2>/dev/null || true

# Start Backend
echo "Starting Backend..."
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# Start Frontend
echo "Starting Frontend..."
cd frontend && source ~/.nvm/nvm.sh && nvm use 22 && npm run dev -- --port 5173 &
FRONTEND_PID=$!

echo "Both servers are starting!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"

# Wait for both
cleanup() {
    # Disable trap to avoid recursion
    trap - SIGINT SIGTERM EXIT
    echo "Shutting down servers..."
    # Send SIGTERM first
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    # Give them a moment, then force-kill any leftovers on these ports
    sleep 1
    lsof -ti:8000,5173 | xargs kill -9 2>/dev/null || true
    echo "Done."
    exit
}

trap cleanup SIGINT SIGTERM EXIT
wait
