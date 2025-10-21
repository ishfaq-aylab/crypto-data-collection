#!/bin/bash
# stop_services.sh - Stop Crypto Data Collection & API Services

echo "🛑 Stopping Crypto Data Collection & API Services..."
echo "=================================================="

# Stop data collection
if [ -f data_collection.pid ]; then
    DATA_PID=$(cat data_collection.pid)
    if kill -0 $DATA_PID 2>/dev/null; then
        echo "📡 Stopping data collection (PID: $DATA_PID)..."
        kill $DATA_PID
        sleep 2
        if kill -0 $DATA_PID 2>/dev/null; then
            echo "⚠️  Force killing data collection..."
            kill -9 $DATA_PID
        fi
        echo "✅ Data collection stopped"
    else
        echo "ℹ️  Data collection was not running"
    fi
    rm -f data_collection.pid
else
    echo "📡 Stopping data collection (by process name)..."
    pkill -f run_data_collection
    if [ $? -eq 0 ]; then
        echo "✅ Data collection stopped"
    else
        echo "ℹ️  No data collection process found"
    fi
fi

# Stop API server
if [ -f api_server.pid ]; then
    API_PID=$(cat api_server.pid)
    if kill -0 $API_PID 2>/dev/null; then
        echo "🌐 Stopping API server (PID: $API_PID)..."
        kill $API_PID
        sleep 2
        if kill -0 $API_PID 2>/dev/null; then
            echo "⚠️  Force killing API server..."
            kill -9 $API_PID
        fi
        echo "✅ API server stopped"
    else
        echo "ℹ️  API server was not running"
    fi
    rm -f api_server.pid
else
    echo "🌐 Stopping API server (by process name)..."
    pkill -f realtime_api
    if [ $? -eq 0 ]; then
        echo "✅ API server stopped"
    else
        echo "ℹ️  No API server process found"
    fi
fi

# Clean up any remaining processes
echo "🧹 Cleaning up any remaining processes..."
pkill -f run_data_collection 2>/dev/null
pkill -f realtime_api 2>/dev/null

# Check if any processes are still running
REMAINING_DATA=$(pgrep -f run_data_collection)
REMAINING_API=$(pgrep -f realtime_api)

if [ -n "$REMAINING_DATA" ] || [ -n "$REMAINING_API" ]; then
    echo "⚠️  Some processes may still be running:"
    [ -n "$REMAINING_DATA" ] && echo "  Data Collection PIDs: $REMAINING_DATA"
    [ -n "$REMAINING_API" ] && echo "  API Server PIDs: $REMAINING_API"
    echo "  You may need to kill them manually: kill -9 <PID>"
else
    echo "✅ All services stopped successfully"
fi

echo ""
echo "📊 Service Status:"
echo "  Data Collection: $(pgrep -f run_data_collection > /dev/null && echo "❌ Still running" || echo "✅ Stopped")"
echo "  API Server: $(pgrep -f realtime_api > /dev/null && echo "❌ Still running" || echo "✅ Stopped")"
echo ""
echo "🔍 To verify services are stopped:"
echo "  ps aux | grep -E '(run_data_collection|realtime_api)'"
echo ""
echo "🚀 To start services again:"
echo "  ./start_services.sh"
echo ""
echo "=================================================="
