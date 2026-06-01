#!/bin/bash
# Phase 2: Paper Trading with Dashboard
# Run these in separate terminal windows

# Terminal 1: Start the Dashboard
# cd ~/code/openclaw/projects/PolyTrackerBot/dashboard
# npm run dev

# Terminal 2: Start the Bot in Paper Mode
# cd ~/code/openclaw/projects/PolyTrackerBot
# source venv/bin/activate
# python -m polytracker.main

# Terminal 3: Monitor Logs
# cd ~/code/openclaw/projects/PolyTrackerBot
# tail -f logs/polytracker.log | grep -E "Signal|Trade|Risk|Paper"

echo "🚀 Phase 2 Paper Trading Setup"
echo ""
echo "Dashboard is ready at: http://localhost:5173"
echo "Bot is running in PAPER mode (no real orders)"
echo "Database: ./data/polytracker.db"
echo "Logs: ./logs/polytracker.log"
