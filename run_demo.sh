#!/bin/bash

# PolyTrackerBot Demo Mode Launcher
# Paper trading at live prices

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Create logs directory
mkdir -p logs

# Activate venv
source venv/bin/activate

# Export environment
export EXECUTION_MODE=demo
export DEFAULT_POSITION_SIZE_USD=100
export MAX_POSITION_SIZE_USD=5000
export MAX_DAILY_LOSS_USD=1000
export MAX_DAILY_VOLUME_USD=10000
export MAX_CONCURRENT_POSITIONS=5
export TELEGRAM_BOT_TOKEN="test_token_demo"
export TELEGRAM_CHANNEL_ID="-1"
export DATABASE_URL="postgresql+asyncpg://polytracker:polytracker_dev@localhost:5432/polytracker"

# Get timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/demo_${TIMESTAMP}.log"

echo "🚀 Starting PolyTrackerBot Demo Mode"
echo "📝 Logging to: $LOG_FILE"
echo "⏱️  Mode: DEMO (paper trading at live prices)"
echo "💰 Position sizing: $DEFAULT_POSITION_SIZE_USD USD"
echo ""

# Start bot
python -m polytracker.main 2>&1 | tee "$LOG_FILE"
