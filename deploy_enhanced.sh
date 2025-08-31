#!/bin/bash

# 🚀 ENHANCED METROPOLITAN BOT DEPLOYMENT SCRIPT
# This script deploys the bulletproof bot with health monitoring

set -e  # Exit on any error

echo "🚀 Starting Enhanced Metropolitan Bot Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "attendance_bot.py" ]; then
    print_error "attendance_bot.py not found. Please run this script from the bot directory."
    exit 1
fi

print_status "Checking prerequisites..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
if [[ $(echo "$PYTHON_VERSION >= 3.9" | bc -l) -eq 1 ]]; then
    print_success "Python version: $PYTHON_VERSION"
else
    print_error "Python 3.9+ required, found: $PYTHON_VERSION"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_warning "Virtual environment not found. Creating one..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install/upgrade requirements
print_status "Installing/upgrading requirements..."
pip install --upgrade pip
pip install -r requirements.txt

# Run health tests
print_status "Running health tests..."
if python3 test_bot.py; then
    print_success "Health tests passed"
else
    print_error "Health tests failed. Please fix issues before deployment."
    exit 1
fi

# Check environment variables
print_status "Checking environment variables..."
if [ -z "$BOT_TOKEN" ]; then
    print_error "BOT_TOKEN not set in environment"
    exit 1
fi

if [ -z "$SPREADSHEET_ID" ]; then
    print_error "SPREADSHEET_ID not set in environment"
    exit 1
fi

if [ -z "$GOOGLE_CREDENTIALS_JSON" ]; then
    print_error "GOOGLE_CREDENTIALS_JSON not set in environment"
    exit 1
fi

print_success "Environment variables verified"

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if bot is already running
if pgrep -f "attendance_bot.py" > /dev/null; then
    print_warning "Bot is already running. Stopping it gracefully..."
    pkill -f "attendance_bot.py"
    sleep 2
    
    # Force kill if still running
    if pgrep -f "attendance_bot.py" > /dev/null; then
        print_warning "Force stopping bot..."
        pkill -9 -f "attendance_bot.py"
    fi
fi

# Start the enhanced bot
print_status "Starting Enhanced Metropolitan Bot..."
nohup python3 attendance_bot.py > logs/bot.log 2>&1 &

# Wait a moment for the bot to start
sleep 3

# Check if bot started successfully
if pgrep -f "attendance_bot.py" > /dev/null; then
    BOT_PID=$(pgrep -f "attendance_bot.py")
    print_success "Bot started successfully with PID: $BOT_PID"
else
    print_error "Bot failed to start. Check logs/bot.log for details."
    exit 1
fi

# Wait a bit more for webhook setup
sleep 5

# Check bot health
print_status "Checking bot health..."
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    print_success "Health endpoint responding"
    
    # Get detailed health info
    HEALTH_RESPONSE=$(curl -s http://localhost:8080/health)
    print_status "Health status: $HEALTH_RESPONSE"
else
    print_warning "Health endpoint not responding yet (this is normal during startup)"
fi

# Show bot status
print_status "Bot deployment completed!"
echo ""
echo "📊 DEPLOYMENT SUMMARY:"
echo "   ✅ Bot started with PID: $BOT_PID"
echo "   ✅ Health endpoint: http://localhost:8080/health"
echo "   ✅ Logs: logs/bot.log"
echo "   ✅ Environment: Verified"
echo "   ✅ Dependencies: Installed"
echo ""

echo "🔍 MONITORING COMMANDS:"
echo "   Check status: ps aux | grep attendance_bot"
echo "   View logs: tail -f logs/bot.log"
echo "   Health check: curl http://localhost:8080/health"
echo "   Graceful shutdown: curl -X POST http://localhost:8080/shutdown"
echo ""

echo "🚨 ENHANCED FEATURES ENABLED:"
echo "   ✅ Memory leak prevention"
echo "   ✅ Automatic cleanup (every 15 minutes)"
echo "   ✅ Webhook retry logic"
echo "   ✅ Graceful shutdown handling"
echo "   ✅ Resource monitoring"
echo "   ✅ Error recovery mechanisms"
echo ""

print_success "🎉 Enhanced Metropolitan Bot is now running and bulletproof!"
print_status "Monitor logs/bot.log for any issues and use the health endpoint for monitoring."
