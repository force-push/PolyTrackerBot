#!/bin/bash
# Start all PolyTrackerBot services for Phase 3 Demo Trading

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

echo "🚀 PolyTrackerBot - Phase 3 Demo Trading Startup"
echo "=================================================="
echo ""

# Check venv
if [ ! -d "venv" ]; then
  echo "❌ Virtual environment not found. Run: python3 -m venv venv && pip install -r requirements.txt"
  exit 1
fi

source venv/bin/activate

# Check dashboard deps
if [ ! -d "dashboard/node_modules" ]; then
  echo "⏳ Installing dashboard dependencies..."
  cd dashboard && npm install && cd ..
fi

echo ""
echo "Starting services..."
echo ""

# 1. Start Bot
echo "1️⃣  Starting bot process (DEMO mode)..."
python -m polytracker.main > logs/bot.log 2>&1 &
BOT_PID=$!
echo "   Bot PID: $BOT_PID"
sleep 2

# 2. Start API Server
echo "2️⃣  Starting API server (port 8000)..."
python -m polytracker.api.server > logs/api.log 2>&1 &
API_PID=$!
echo "   API PID: $API_PID"
sleep 2

# 3. Start Dashboard
echo "3️⃣  Starting dashboard (port 3000)..."
cd dashboard
npm run dev > ../logs/dashboard.log 2>&1 &
DASHBOARD_PID=$!
echo "   Dashboard PID: $DASHBOARD_PID"
cd ..

echo ""
echo "=================================================="
echo "✅ All services started!"
echo ""
echo "📊 Dashboard:    http://localhost:3000"
echo "🔌 API Server:   http://localhost:8000"
echo "📡 Bot:          Running (DEMO mode)"
echo ""
echo "Process IDs:"
echo "  Bot:       $BOT_PID"
echo "  API:       $API_PID"
echo "  Dashboard: $DASHBOARD_PID"
echo ""
echo "Logs:"
echo "  Bot:       tail -f logs/bot.log"
echo "  API:       tail -f logs/api.log"
echo "  Dashboard: tail -f logs/dashboard.log"
echo "  All:       tail -f logs/polytracker.log"
echo ""
echo "Mode control:"
echo "  curl http://localhost:8000/api/mode/current"
echo "  curl -X POST http://localhost:8000/api/mode/set -H 'Content-Type: application/json' -d '{\"mode\": \"DEMO\"}'"
echo ""
echo "To stop all services:"
echo "  kill $BOT_PID $API_PID $DASHBOARD_PID"
echo ""

# Keep script running
wait
