#!/bin/bash
# WOS-M Bot Persistent Runner
# Keeps the bot running 24/7 with automatic restart

BOT_DIR="/workspace/project/wos-m"
LOG_FILE="$BOT_DIR/bot.log"
PID_FILE="$BOT_DIR/bot.pid"

echo "=========================================="
echo "  WOS-M Bot - Persistent Runner"
echo "  $(date)"
echo "=========================================="

cd "$BOT_DIR"

# Create directories
mkdir -p data/logs data/backups

# Install dependencies if needed
pip install -r requirements.txt -q 2>/dev/null

# Run bot with automatic restart
while true; do
    echo "$(date) - Starting WOS-M Bot..." >> "$LOG_FILE"
    
    # Save PID
    echo $$ > "$PID_FILE"
    
    # Run the bot
    python main.py 2>&1 | tee -a "$LOG_FILE"
    
    EXIT_CODE=$?
    echo "$(date) - Bot exited with code $EXIT_CODE" >> "$LOG_FILE"
    echo "Restarting in 10 seconds..." >> "$LOG_FILE"
    sleep 10
done
