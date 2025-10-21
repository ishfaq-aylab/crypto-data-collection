#!/bin/bash
# Production API Server Startup Script
# ====================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/ishfaq/Documents/dev/aylabs/exchanges-websockets"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="$PROJECT_DIR/logs"
PID_FILE="$LOG_DIR/gunicorn.pid"

echo -e "${BLUE}🚀 Starting Production Crypto API Server${NC}"
echo "================================================"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Do not run as root! Use a regular user.${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}❌ Virtual environment not found at $VENV_DIR${NC}"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements_production.txt"
    exit 1
fi

# Check if requirements are installed
if [ ! -f "$VENV_DIR/bin/gunicorn" ]; then
    echo -e "${YELLOW}⚠️  Installing production requirements...${NC}"
    source "$VENV_DIR/bin/activate"
    pip install -r requirements_production.txt
fi

# Create logs directory
mkdir -p "$LOG_DIR"

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  API server is already running (PID: $PID)${NC}"
        echo "To restart, run: ./stop_production_api.sh && ./start_production_api.sh"
        exit 1
    else
        echo -e "${YELLOW}⚠️  Removing stale PID file${NC}"
        rm -f "$PID_FILE"
    fi
fi

# Check MongoDB connection
echo -e "${BLUE}🔍 Checking MongoDB connection...${NC}"
if ! python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
from config import Config
from pymongo import MongoClient
try:
    client = MongoClient(Config.MONGODB_URL, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print('✅ MongoDB connection successful')
except Exception as e:
    print(f'❌ MongoDB connection failed: {e}')
    sys.exit(1)
"; then
    echo -e "${RED}❌ MongoDB connection failed. Please check your database.${NC}"
    exit 1
fi

# Start the server
echo -e "${BLUE}🚀 Starting Gunicorn server...${NC}"
cd "$PROJECT_DIR"
source "$VENV_DIR/bin/activate"

# Start Gunicorn in background
nohup gunicorn --config gunicorn.conf.py wsgi:application > "$LOG_DIR/gunicorn.log" 2>&1 &

# Wait a moment for startup
sleep 3

# Check if started successfully
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API server started successfully (PID: $PID)${NC}"
        echo -e "${BLUE}📊 Server running on: http://0.0.0.0:${API_PORT:-5001}${NC}"
        echo -e "${BLUE}📝 Logs: $LOG_DIR/gunicorn.log${NC}"
        echo -e "${BLUE}📝 Access logs: $LOG_DIR/access.log${NC}"
        echo -e "${BLUE}📝 Error logs: $LOG_DIR/error.log${NC}"
        
        # Test health endpoint
        echo -e "${BLUE}🔍 Testing health endpoint...${NC}"
        sleep 2
        if curl -s http://localhost:${API_PORT:-5001}/health > /dev/null; then
            echo -e "${GREEN}✅ Health check passed${NC}"
        else
            echo -e "${YELLOW}⚠️  Health check failed - server may still be starting${NC}"
        fi
        
        echo ""
        echo -e "${GREEN}🎉 Production API server is running!${NC}"
        echo "To stop: ./stop_production_api.sh"
        echo "To view logs: tail -f $LOG_DIR/gunicorn.log"
        echo "To check status: ps aux | grep gunicorn"
        
    else
        echo -e "${RED}❌ Failed to start API server${NC}"
        echo "Check logs: cat $LOG_DIR/gunicorn.log"
        exit 1
    fi
else
    echo -e "${RED}❌ PID file not created. Check logs: cat $LOG_DIR/gunicorn.log${NC}"
    exit 1
fi
