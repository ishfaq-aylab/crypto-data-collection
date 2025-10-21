#!/bin/bash
# Crypto API Server Status Check
# ==============================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Crypto API Server Status Check${NC}"
echo "================================="

# Health check
echo -n "Health: "
if curl -s http://localhost:5001/health > /dev/null 2>&1; then
    health_status=$(curl -s http://localhost:5001/health | jq -r .status 2>/dev/null || echo "unknown")
    if [ "$health_status" = "healthy" ]; then
        echo -e "${GREEN}✅ $health_status${NC}"
    else
        echo -e "${YELLOW}⚠️  $health_status${NC}"
    fi
else
    echo -e "${RED}❌ Not responding${NC}"
fi

# Process count
process_count=$(ps aux | grep gunicorn | grep -v grep | wc -l)
echo -n "Processes: "
if [ "$process_count" -gt 0 ]; then
    echo -e "${GREEN}✅ $process_count running${NC}"
else
    echo -e "${RED}❌ None running${NC}"
fi

# Memory usage
memory_usage=$(free -h | grep Mem | awk '{print $3"/"$2}')
echo -n "Memory: "
memory_percent=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ "$memory_percent" -lt 80 ]; then
    echo -e "${GREEN}✅ $memory_usage${NC}"
elif [ "$memory_percent" -lt 90 ]; then
    echo -e "${YELLOW}⚠️  $memory_usage${NC}"
else
    echo -e "${RED}❌ $memory_usage${NC}"
fi

# Disk usage
disk_usage=$(df -h / | awk 'NR==2{print $5}' | sed 's/%//')
echo -n "Disk: "
if [ "$disk_usage" -lt 80 ]; then
    echo -e "${GREEN}✅ $(df -h / | awk 'NR==2{print $5}')${NC}"
elif [ "$disk_usage" -lt 90 ]; then
    echo -e "${YELLOW}⚠️  $(df -h / | awk 'NR==2{print $5}')${NC}"
else
    echo -e "${RED}❌ $(df -h / | awk 'NR==2{print $5}')${NC}"
fi

# Uptime
uptime_info=$(uptime | awk '{print $3,$4}' | sed 's/,//')
echo -e "Uptime: ${BLUE}$uptime_info${NC}"

# API response time
echo -n "Response Time: "
if curl -s http://localhost:5001/health > /dev/null 2>&1; then
    response_time=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:5001/health 2>/dev/null)
    if (( $(echo "$response_time < 1.0" | bc -l) )); then
        echo -e "${GREEN}✅ ${response_time}s${NC}"
    elif (( $(echo "$response_time < 3.0" | bc -l) )); then
        echo -e "${YELLOW}⚠️  ${response_time}s${NC}"
    else
        echo -e "${RED}❌ ${response_time}s${NC}"
    fi
else
    echo -e "${RED}❌ N/A${NC}"
fi

# Recent errors
echo -n "Recent Errors: "
if [ -f "logs/gunicorn.log" ]; then
    error_count=$(grep -i error logs/gunicorn.log | tail -5 | wc -l)
    if [ "$error_count" -eq 0 ]; then
        echo -e "${GREEN}✅ None${NC}"
    else
        echo -e "${YELLOW}⚠️  $error_count in last 5 lines${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  No log file${NC}"
fi

echo "================================="
