#!/bin/bash

echo "🚀 Starting TCG Research System..."

# Function to kill background processes on exit
cleanup() {
    echo "🛑 Stopping all services..."
    kill $API_PID $WEB_PID 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

# Start the API server
echo "📡 Starting API server on port 8000..."
cd src
PYTHONPATH=. python -m uvicorn tcg_research.api.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

# Wait a bit for API to start
sleep 3

# Start the web interface
echo "🌐 Starting web interface on port 3000..."
cd ..
npm run dev &
WEB_PID=$!

echo "✅ System is running!"
echo ""
echo "🔗 Web Interface: http://localhost:3000"
echo "📋 API Docs: http://localhost:8000/docs"
echo "🧪 Mock Data: http://localhost:8000/tcg/scan/mock"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for either process to exit
wait $API_PID $WEB_PID