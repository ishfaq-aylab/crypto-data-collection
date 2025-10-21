#!/bin/bash
# start_services.sh - Start Crypto Data Collection & API Services

echo "🚀 Starting Crypto Data Collection & API Services..."
echo "=================================================="

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not activated. Activating now..."
    source venv/bin/activate
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.12+"
    exit 1
fi

# Check if MongoDB is running
echo "📊 Checking MongoDB status..."
if ! pgrep -x "mongod" > /dev/null; then
    echo "⚠️  MongoDB not running. Starting MongoDB..."
    sudo systemctl start mongod
    sleep 3
else
    echo "✅ MongoDB is already running"
fi

# Wait for MongoDB to be ready
echo "⏳ Waiting for MongoDB to be ready..."
sleep 3

# Check if services are already running
if pgrep -f "run_data_collection" > /dev/null; then
    echo "⚠️  Data collection is already running. Stopping it first..."
    pkill -f run_data_collection
    sleep 2
fi

if pgrep -f "realtime_api" > /dev/null; then
    echo "⚠️  API server is already running. Stopping it first..."
    pkill -f realtime_api
    sleep 2
fi

# Start Real-time Data Collection (WebSocket + REST)
echo "📡 Starting real-time data collection..."
nohup python3 run_data_collection.py > data_collection.log 2>&1 &
DATA_PID=$!

# Wait for data collection to initialize
echo "⏳ Waiting for data collection to initialize..."
sleep 5

# Check if data collection started successfully
if ! kill -0 $DATA_PID 2>/dev/null; then
    echo "❌ Failed to start data collection. Check data_collection.log for errors."
    exit 1
fi

# Start Real-time API Server
echo "🌐 Starting real-time API server..."
nohup python3 realtime_api.py > api_server.log 2>&1 &
API_PID=$!

# Wait for API server to start
echo "⏳ Waiting for API server to start..."
sleep 3

# Check if API server started successfully
if ! kill -0 $API_PID 2>/dev/null; then
    echo "❌ Failed to start API server. Check api_server.log for errors."
    kill $DATA_PID 2>/dev/null
    exit 1
fi

# Save PIDs for later reference
echo $DATA_PID > data_collection.pid
echo $API_PID > api_server.pid

# Test API health
echo "🔍 Testing API health..."
sleep 2
if curl -s http://localhost:5001/health > /dev/null; then
    echo "✅ API server is responding"
else
    echo "⚠️  API server may not be ready yet. Check api_server.log"
fi

echo ""
echo "🎉 Services started successfully!"
echo "=================================================="
echo "📊 Data Collection PID: $DATA_PID"
echo "🌐 API Server PID: $API_PID"
echo ""
echo "📋 Service URLs:"
echo "  API Server: http://localhost:5001"
echo "  Health Check: http://localhost:5001/health"
echo "  Real-time Data: http://localhost:5001/realtime"
echo ""
echo "📝 Logs:"
echo "  Data Collection: tail -f data_collection.log"
echo "  API Server: tail -f api_server.log"
echo "  Both Logs: tail -f data_collection.log api_server.log"
echo ""
echo "🛑 To stop services:"
echo "  ./stop_services.sh"
echo "  OR"
echo "  kill \$(cat data_collection.pid)"
echo "  kill \$(cat api_server.pid)"
echo ""
echo "🔍 Quick test:"
echo "  curl http://localhost:5001/health"
echo "  curl http://localhost:5001/realtime | jq ."
echo ""
echo "=================================================="
