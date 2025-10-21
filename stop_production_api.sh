#!/bin/bash
# Production API Server Stop Script
# =================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/ishfaq/Documents/dev/aylabs/exchanges-websockets"
LOG_DIR="$PROJECT_DIR/logs"
PID_FILE="$LOG_DIR/gunicorn.pid"

echo -e "${BLUE}🛑 Stopping Production Crypto API Server${NC}"
echo "=============================================="

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}⚠️  No PID file found. Server may not be running.${NC}"
    
    # Try to find and kill by process name
    PIDS=$(pgrep -f "gunicorn.*wsgi:application" || true)
    if [ -n "$PIDS" ]; then
        echo -e "${YELLOW}⚠️  Found running Gunicorn processes: $PIDS${NC}"
        echo -e "${YELLOW}⚠️  Killing processes...${NC}"
        echo "$PIDS" | xargs kill -TERM
        sleep 3
        echo -e "${GREEN}✅ Processes terminated${NC}"
    else
        echo -e "${YELLOW}⚠️  No running Gunicorn processes found${NC}"
    fi
    exit 0
fi

# Read PID
PID=$(cat "$PID_FILE")

# Check if process is running
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Process $PID is not running. Removing stale PID file.${NC}"
    rm -f "$PID_FILE"
    exit 0
fi

echo -e "${BLUE}🔄 Gracefully stopping server (PID: $PID)...${NC}"

# Send TERM signal for graceful shutdown
kill -TERM "$PID"

# Wait for graceful shutdown (up to 30 seconds)
for i in {1..30}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Server stopped gracefully${NC}"
        rm -f "$PID_FILE"
        exit 0
    fi
    echo -n "."
    sleep 1
done

echo ""
echo -e "${YELLOW}⚠️  Graceful shutdown timeout. Force killing...${NC}"

# Force kill if graceful shutdown failed
kill -KILL "$PID" 2>/dev/null || true

# Wait a moment
sleep 2

# Check if killed
if ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${RED}❌ Failed to stop server${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Server stopped forcefully${NC}"
    rm -f "$PID_FILE"
fi

# Clean up any remaining processes
REMAINING_PIDS=$(pgrep -f "gunicorn.*wsgi:application" || true)
if [ -n "$REMAINING_PIDS" ]; then
    echo -e "${YELLOW}⚠️  Cleaning up remaining processes: $REMAINING_PIDS${NC}"
    echo "$REMAINING_PIDS" | xargs kill -KILL 2>/dev/null || true
fi

echo -e "${GREEN}🎉 API server stopped successfully${NC}"
