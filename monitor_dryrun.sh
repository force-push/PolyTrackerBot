#!/bin/bash

# Monitor dry run execution
# Shows real-time log updates and extracts key metrics

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$PROJECT_DIR/logs/dryrun_20260601_161026.log"

echo "📊 PolyTrackerBot Dry Run Monitor"
echo "📁 Log: $LOG_FILE"
echo "⏱️  Mode: DRY_RUN (signals detected, zero orders placed)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Show startup
echo "📋 Startup Status:"
grep "Database connected\|Scheduler started\|Bot is running" "$LOG_FILE" | tail -3

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔴 LIVE LOG STREAM (press Ctrl+C to stop)"
echo ""

# Stream log with color
tail -f "$LOG_FILE" | while IFS= read -r line; do
  if echo "$line" | grep -q "ERROR\|❌"; then
    echo "🔴 $line"
  elif echo "$line" | grep -q "WARNING\|⚠️"; then
    echo "🟡 $line"
  elif echo "$line" | grep -q "Processing signal\|DRY RUN\|Risk check"; then
    echo "🟢 $line"
  elif echo "$line" | grep -q "✅"; then
    echo "✅ $line"
  else
    echo "   $line"
  fi
done
