@echo off
TITLE ML-Enhanced SDN Emergency Communication Network
echo =========================================================================
echo   Starting ML-Enhanced SDN Emergency Communication System
echo =========================================================================

echo Starting FastAPI Backend server on port 8000...
start "SDN Backend" cmd /k "cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo Starting Vite React Frontend server on port 5173...
start "SDN Frontend" cmd /k "cd frontend && npm run dev"

timeout /t 3 >nul

echo.
echo =========================================================================
echo   SYSTEM READY:
echo   - Network Dashboard:  http://localhost:5173/dashboard
echo   - Topology & Routing: http://localhost:5173/topology
echo   - FastAPI Docs:       http://localhost:8000/docs
echo =========================================================================
echo.
pause
