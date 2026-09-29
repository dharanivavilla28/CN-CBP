#!/bin/bash
# =============================================================================
# Run Script for ML-Enhanced SDN Emergency Communication Network
# Starts both FastAPI Backend (port 8000) and Vite React Frontend (port 5173)
# =============================================================================

echo "Starting Emergency SDN Backend on http://localhost:8000..."
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

echo "Starting Frontend UI on http://localhost:5173..."
cd frontend
npm run dev -- --host &
FRONTEND_PID=$!
cd ..

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT

echo ""
echo "========================================================================"
echo "  EMERGENCY SDN NETWORK RUNNING:"
echo "  - Network Dashboard:    http://localhost:5173/dashboard"
echo "  - Topology & Routing:   http://localhost:5173/topology"
echo "  - Backend REST API:     http://localhost:8000/docs"
echo "  - WebSocket Stream:     ws://localhost:8000/ws/network"
echo "========================================================================"
echo "Press Ctrl+C to terminate both servers."

wait
