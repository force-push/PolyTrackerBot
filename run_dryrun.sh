#!/bin/bash

# PolyTrackerBot Dry Run Launcher
# Creates logs directory and starts bot in dry run mode

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Create logs directory
mkdir -p logs

# Activate venv
source venv/bin/activate

# Export environment
export EXECUTION_MODE=dry_run
export TELEGRAM_BOT_TOKEN="test_token_dryrun"
export TELEGRAM_CHANNEL_ID="-1"
export DATABASE_URL="postgresql+asyncpg://polytracker:polytracker_dev@localhost:5432/polytracker"

# Get timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/dryrun_${TIMESTAMP}.log"

echo "🚀 Starting PolyTrackerBot Dry Run"
echo "📝 Logging to: $LOG_FILE"
echo "⏱️  Mode: DRY_RUN (signals detected, zero orders placed)"
echo ""

# Start bot
python -m polytracker.main 2>&1 | tee "$LOG_FILE"
