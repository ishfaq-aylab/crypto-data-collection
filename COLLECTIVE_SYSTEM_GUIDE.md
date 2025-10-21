# 🚀 Collective System Guide - Complete Data Collection & API

This guide shows you how to run your crypto data collection system **collectively** - meaning both data collection and API server working together as a unified system.

## 🎯 **What "Collective System" Means**

Your system has **two main components** that work together:

1. **📡 Data Collection Engine** - Collects real-time data from 5 exchanges
2. **🌐 API Server** - Serves the collected data via REST API

When running **collectively**, both components work together to:
- ✅ Collect real-time data continuously
- ✅ Store data in MongoDB
- ✅ Serve data via API endpoints
- ✅ Provide real-time access to your team

---

## 🚀 **Quick Start - Collective System**

### **Option 1: Automated Startup (Recommended)**

```bash
# Start both services together
./start_services.sh

# Check status
curl http://localhost:5001/health

# Get real-time data
curl http://localhost:5001/realtime
```

### **Option 2: Manual Startup**

```bash
# Terminal 1: Start data collection
python3 run_data_collection.py

# Terminal 2: Start API server
python3 realtime_api.py
```

---

## 📊 **System Status Verification**

### **1. Check Services Are Running**
```bash
# Check if both services are active
ps aux | grep -E "(run_data_collection|realtime_api)"

# Should show both processes running
```

### **2. Test Data Collection**
```bash
# Check data collection logs
tail -f data_collection.log

# Look for messages like:
# "Stored 8000 messages to MongoDB"
# "📊 Binance MARKET DATA: BTCUSDT"
```

### **3. Test API Server**
```bash
# Health check
curl http://localhost:5001/health

# Get real-time data
curl http://localhost:5001/realtime | jq .

# Get specific exchange data
curl http://localhost:5001/realtime/binance | jq .
```

---

## 🔄 **Data Flow - How It Works Collectively**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Exchanges     │───▶│  Data Collection │───▶│    MongoDB      │───▶│   API Server    │
│ (Binance, etc.) │    │    Engine        │    │   (Storage)     │    │  (Port 5001)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │   Your Team     │
                                                │ (API Clients)   │
                                                └─────────────────┘
```

### **Step-by-Step Process:**

1. **📡 Data Collection Engine** connects to all 5 exchanges via WebSocket
2. **🔄 Real-time Data** flows continuously from exchanges
3. **💾 MongoDB Storage** stores all data with proper schema
4. **🌐 API Server** serves data via REST endpoints
5. **👥 Your Team** accesses data via API calls

---

## 📈 **Real-time Data Collection Status**

### **Current Collection Status:**
- **✅ Market Data**: Real-time price, volume, bid/ask
- **✅ Order Book**: Real-time order book updates
- **✅ Trades**: Real-time trade executions
- **✅ Volume/Liquidity**: Real-time volume metrics
- **✅ Funding Rates**: 8-hour interval updates
- **✅ Open Interest**: 5-15 minute updates

### **Exchange Coverage:**
- **Binance**: ✅ Active (BTCUSDT, BTCUSDC, BTCBUSD)
- **Bybit**: ✅ Active (BTCUSDT, BTCUSDC)
- **Kraken**: ✅ Active (XXBTZUSD, XBT/USD, etc.)
- **Gate.io**: ✅ Active (BTC_USDT, BTC_USDC)
- **OKX**: ✅ Active (BTC-USDT, BTC-USDC)

---

## 🎯 **API Endpoints - Live Data Access**

### **Health & Status**
```bash
# System health
curl http://localhost:5001/health

# Available exchanges
curl http://localhost:5001/exchanges

# Available symbols
curl http://localhost:5001/symbols
```

### **Real-time Data**
```bash
# All real-time data
curl http://localhost:5001/realtime

# Exchange-specific data
curl http://localhost:5001/realtime/binance
curl http://localhost:5001/realtime/kraken

# Symbol-specific data
curl http://localhost:5001/realtime/binance/BTCUSDT
```

### **Data Type Specific**
```bash
# Market data only
curl http://localhost:5001/market-data?limit=10

# Trades only
curl http://localhost:5001/trades?limit=10

# OHLCV candles
curl http://localhost:5001/ohlcv?limit=10

# Funding rates
curl http://localhost:5001/funding-rates?limit=5

# Open interest
curl http://localhost:5001/open-interest?limit=5

# Volume/liquidity
curl http://localhost:5001/volume-liquidity?limit=5
```

---

## 📊 **Monitoring Your Collective System**

### **1. Data Collection Monitoring**
```bash
# Watch data collection logs
tail -f data_collection.log

# Check for errors
grep -i error data_collection.log

# Check collection rate
grep "Stored.*messages" data_collection.log | tail -10
```

### **2. API Server Monitoring**
```bash
# Watch API server logs
tail -f api_server.log

# Check API health
curl -s http://localhost:5001/health | jq .status

# Test API response time
time curl -s http://localhost:5001/realtime > /dev/null
```

### **3. Database Monitoring**
```bash
# Check data volume
python3 quick_data_check.py

# Analyze Bitcoin data
python3 analyze_bitcoin_data.py

# Check specific exchange
curl -s "http://localhost:5001/realtime/binance" | jq '.data.market_data | length'
```

---

## 🛠️ **Troubleshooting Collective System**

### **Common Issues & Solutions**

#### **1. Data Collection Not Working**
```bash
# Check if data collection is running
ps aux | grep run_data_collection

# If not running, restart
./stop_services.sh
./start_services.sh

# Check logs for errors
tail -f data_collection.log
```

#### **2. API Server Not Responding**
```bash
# Check if API server is running
ps aux | grep realtime_api

# If not running, restart
./stop_services.sh
./start_services.sh

# Check API logs
tail -f api_server.log
```

#### **3. No Data in API Responses**
```bash
# Check if data is being collected
tail -f data_collection.log | grep "Stored.*messages"

# Check database connection
curl -s http://localhost:5001/health | jq .mongodb

# Check data volume
python3 quick_data_check.py
```

#### **4. High Memory Usage**
```bash
# Check memory usage
ps aux | grep -E "(run_data_collection|realtime_api)" | awk '{print $2, $4, $6}'

# Restart services if needed
./stop_services.sh
sleep 5
./start_services.sh
```

---

## 🔧 **Advanced Configuration**

### **1. Run Data Collection for Specific Duration**
```bash
# Run for 1 hour
python3 run_data_collection.py 3600

# Run for 2 hours
python3 run_data_collection.py 7200

# Run indefinitely (production)
python3 run_data_collection.py 0
```

### **2. Custom API Configuration**
```bash
# Start API on different port
python3 realtime_api.py --port 5002

# Start with debug mode
python3 realtime_api.py --debug
```

### **3. Data Collection with Polling**
```bash
# Run with 60-second polling
python3 run_data_collection.py 3600 60

# Run with 30-second polling
python3 run_data_collection.py 3600 30
```

---

## 📈 **Performance Metrics**

### **Expected Performance:**
- **Data Collection Rate**: 200+ messages/second
- **API Response Time**: <100ms
- **Memory Usage**: <500MB per service
- **Database Growth**: ~1GB per day
- **Uptime**: 99.9% with auto-recovery

### **Monitoring Commands:**
```bash
# Check collection rate
grep "Stored.*messages" data_collection.log | tail -1

# Check API response time
time curl -s http://localhost:5001/health > /dev/null

# Check memory usage
ps aux | grep -E "(run_data_collection|realtime_api)" | awk '{print $2, $4, $6}'
```

---

## 🎯 **Production Deployment**

### **1. Start Services in Background**
```bash
# Start with nohup for production
nohup ./start_services.sh > system_startup.log 2>&1 &

# Check if started successfully
sleep 10
curl http://localhost:5001/health
```

### **2. Monitor System Health**
```bash
# Create monitoring script
cat > monitor_system.sh << 'EOF'
#!/bin/bash
while true; do
    echo "=== System Status $(date) ==="
    curl -s http://localhost:5001/health | jq .
    echo ""
    sleep 60
done
EOF

chmod +x monitor_system.sh
./monitor_system.sh
```

### **3. Auto-restart on Failure**
```bash
# Create auto-restart script
cat > auto_restart.sh << 'EOF'
#!/bin/bash
while true; do
    if ! curl -s http://localhost:5001/health > /dev/null; then
        echo "System down, restarting..."
        ./stop_services.sh
        sleep 5
        ./start_services.sh
    fi
    sleep 30
done
EOF

chmod +x auto_restart.sh
nohup ./auto_restart.sh > auto_restart.log 2>&1 &
```

---

## 🎉 **Success Indicators**

Your collective system is working correctly when you see:

### **✅ Data Collection Working:**
- Logs show: `"Stored XXXX messages to MongoDB"`
- Logs show: `"📊 Exchange MARKET DATA: Symbol"`
- Database records increasing

### **✅ API Server Working:**
- `curl http://localhost:5001/health` returns status: "healthy"
- `curl http://localhost:5001/realtime` returns data
- API responses are fast (<100ms)

### **✅ End-to-End Working:**
- Real-time data flows from exchanges → MongoDB → API
- API serves fresh data (timestamps within last minute)
- All 5 exchanges providing data
- All 7 data types being collected

---

## 🚀 **Quick Commands Summary**

```bash
# Start collective system
./start_services.sh

# Check system status
curl http://localhost:5001/health

# Get real-time data
curl http://localhost:5001/realtime

# Monitor logs
tail -f data_collection.log api_server.log

# Stop system
./stop_services.sh

# Restart system
./stop_services.sh && ./start_services.sh
```

**Your collective crypto data system is now running!** 🎉

The system is collecting real-time data from 5 exchanges and serving it via API endpoints for your team to access.
