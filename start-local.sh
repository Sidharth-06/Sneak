#!/bin/bash

cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "Starting Company Insights Platform"
echo "========================================"
echo ""
echo "Prerequisites:"
echo "- PostgreSQL running on localhost:5432"
echo "- Redis running on localhost:6379"
echo ""

# Start backend
echo "Starting Backend API on http://localhost:8000..."
cd backend
source venv/bin/activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

sleep 3

# Start frontend
echo "Starting Frontend on http://localhost:3000..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo "Backend API: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

wait
