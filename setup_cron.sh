#!/bin/bash

# Metropolitan Bot - Cron Job Setup Script
# This script sets up automated monthly sheet creation at 00:00 every day

echo "🤖 Metropolitan Bot - Cron Job Setup"
echo "====================================="

# Get the current directory
CURRENT_DIR=$(pwd)
SCRIPT_PATH="$CURRENT_DIR/create_monthly_sheets.py"

echo "📍 Current directory: $CURRENT_DIR"
echo "📝 Script path: $SCRIPT_PATH"

# Check if the script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Error: create_monthly_sheets.py not found!"
    echo "   Make sure you're running this from the bot directory"
    exit 1
fi

# Make the script executable
chmod +x "$SCRIPT_PATH"
echo "✅ Made script executable"

# Create the cron job entry
CRON_JOB="0 0 * * * cd $CURRENT_DIR && python3 $SCRIPT_PATH >> $CURRENT_DIR/cron.log 2>&1"

echo "⏰ Setting up cron job to run at 00:00 every day..."
echo "📋 Cron job: $CRON_JOB"

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ Cron job added successfully!"
echo ""
echo "📊 What this does:"
echo "   • Runs every day at 00:00 (midnight)"
echo "   • Creates next month's sheet if it doesn't exist"
echo "   • Applies beautiful styling (light blue names, light green dates)"
echo "   • Logs output to cron.log file"
echo ""
echo "🔍 To check if it's working:"
echo "   • View cron.log: tail -f cron.log"
echo "   • List cron jobs: crontab -l"
echo "   • Remove cron job: crontab -r"
echo ""
echo "🎯 Your monthly sheets will now be created automatically!"
echo "   No more waiting for users to trigger sheet creation!"
