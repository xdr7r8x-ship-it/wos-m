#!/bin/bash
# WOS-M Bot Start Script
# This script keeps the bot running 24/7

cd /workspace/project/wos-m

echo "Starting WOS-M Bot..."
echo "Log file: bot.log"
echo "To stop: kill this process or press Ctrl+C"

# Create data directories
mkdir -p data/logs data/backups

# Install dependencies if needed
pip install -r requirements.txt -q 2>/dev/null

# Run bot with automatic restart
while true; do
    echo "$(date) - Starting bot..." >> bot.log
    python main.py 2>&1 | tee -a bot.log
    EXIT_CODE=$?
    echo "$(date) - Bot exited with code $EXIT_CODE, restarting in 10 seconds..." >> bot.log
    sleep 10
done
