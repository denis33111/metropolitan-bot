#!/bin/bash

# 🔍 METROPOLITAN BOT MONITORING SCRIPT
# Continuous monitoring and health checks for the enhanced bot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Configuration
BOT_URL="http://localhost:8080"
HEALTH_ENDPOINT="$BOT_URL/health"
LOG_FILE="logs/bot.log"
CHECK_INTERVAL=30  # seconds

echo "🔍 Metropolitan Bot Monitoring Started"
echo "   Health endpoint: $HEALTH_ENDPOINT"
echo "   Log file: $LOG_FILE"
echo "   Check interval: ${CHECK_INTERVAL}s"
echo "   Press Ctrl+C to stop monitoring"
echo ""

# Function to check bot health
check_bot_health() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Check if bot process is running
    if ! pgrep -f "attendance_bot.py" > /dev/null; then
        print_error "[$timestamp] Bot process not running!"
        return 1
    fi
    
    # Check health endpoint
    if curl -s "$HEALTH_ENDPOINT" > /dev/null 2>&1; then
        local health_response=$(curl -s "$HEALTH_ENDPOINT")
        print_success "[$timestamp] Health check: $health_response"
        
        # Parse JSON response for status
        if echo "$health_response" | grep -q '"status":"critical"'; then
            print_error "[$timestamp] 🚨 CRITICAL STATUS DETECTED!"
        elif echo "$health_response" | grep -q '"status":"warning"'; then
            print_warning "[$timestamp] ⚠️ WARNING STATUS DETECTED!"
        fi
    else
        print_error "[$timestamp] Health endpoint not responding"
        return 1
    fi
    
    # Check memory usage
    local memory_usage=$(ps aux | grep "attendance_bot.py" | grep -v grep | awk '{print $6}' | head -1)
    if [ ! -z "$memory_usage" ]; then
        local memory_mb=$((memory_usage / 1024))
        print_status "[$timestamp] Memory usage: ${memory_mb}MB"
        
        if [ $memory_mb -gt 500 ]; then
            print_warning "[$timestamp] ⚠️ High memory usage detected"
        fi
    fi
    
    # Check log file for recent errors
    local recent_errors=$(tail -100 "$LOG_FILE" 2>/dev/null | grep -c "ERROR\|Exception\|Traceback" || echo "0")
    if [ $recent_errors -gt 0 ]; then
        print_warning "[$timestamp] Found $recent_errors recent errors in logs"
    fi
    
    return 0
}

# Function to show bot status
show_bot_status() {
    echo ""
    echo "📊 BOT STATUS SUMMARY"
    echo "====================="
    
    # Process status
    if pgrep -f "attendance_bot.py" > /dev/null; then
        local pid=$(pgrep -f "attendance_bot.py")
        local uptime=$(ps -o etime= -p $pid 2>/dev/null || echo "Unknown")
        print_success "Process: Running (PID: $pid, Uptime: $uptime)"
    else
        print_error "Process: Not running"
    fi
    
    # Health endpoint
    if curl -s "$HEALTH_ENDPOINT" > /dev/null 2>&1; then
        print_success "Health endpoint: Responding"
    else
        print_error "Health endpoint: Not responding"
    fi
    
    # Memory usage
    local memory_usage=$(ps aux | grep "attendance_bot.py" | grep -v grep | awk '{print $6}' | head -1)
    if [ ! -z "$memory_usage" ]; then
        local memory_mb=$((memory_usage / 1024))
        print_status "Memory usage: ${memory_mb}MB"
    fi
    
    # Recent log activity
    if [ -f "$LOG_FILE" ]; then
        local last_log=$(tail -1 "$LOG_FILE" 2>/dev/null | cut -c1-19 || echo "No logs")
        print_status "Last log entry: $last_log"
    fi
    
    echo ""
}

# Main monitoring loop
trap 'echo ""; show_bot_status; echo "Monitoring stopped."; exit 0' INT

while true; do
    check_bot_health
    sleep $CHECK_INTERVAL
done
