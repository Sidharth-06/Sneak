@echo off
cd /d "%~dp0"

echo.
echo ========================================
echo Starting Company Insights Platform
echo ========================================
echo.

REM Start SearXNG via Docker
echo Starting SearXNG on http://localhost:8080...
docker compose up searxng -d

REM Start backend in new terminal
echo Starting Backend API on http://localhost:8000...
start cmd /k "cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

REM Wait a bit for backend to start
timeout /t 3 /nobreak

REM Start Celery worker in new terminal
echo Starting Celery worker...
start cmd /k "cd backend && python -m celery -A core.celery_app worker --loglevel=info -P solo"

REM Wait a bit
timeout /t 2 /nobreak

REM Start frontend in new terminal  
echo Starting Frontend on http://localhost:3000...
start cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo Console windows opened for:
echo - Backend API: http://localhost:8000
echo - Frontend: http://localhost:3000
echo - API Docs: http://localhost:8000/docs
echo ========================================
echo.
echo Press any key to close this window...
pause
