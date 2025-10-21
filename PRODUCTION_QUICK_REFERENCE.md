# 🚀 Production Quick Reference

Quick commands and status checks for the production crypto data API server.

## 🎯 Essential Commands

### Start/Stop Production Server
```bash
# Start production server
./start_production_api.sh

# Stop production server
./stop_production_api.sh

# Restart production server
./stop_production_api.sh && ./start_production_api.sh
```

### Health Checks
```bash
# Quick health check
curl http://localhost:5001/health

# Real-time data check
curl "http://localhost:5001/realtime?limit=1"

# All exchanges
curl http://localhost:5001/exchanges

# All symbols
curl http://localhost:5001/symbols
```

### Monitoring
```bash
# Run health monitoring once
python3 monitor_api.py once

# Continuous monitoring (every 60 seconds)
python3 monitor_api.py continuous 60

# Check system resources
htop
```

### Process Management
```bash
# Check if server is running
ps aux | grep gunicorn

# Check server logs
tail -f logs/gunicorn.log

# Check access logs
tail -f logs/access.log

# Check error logs
tail -f logs/error.log
```

## 🔧 System Service Commands

### Systemd Service
```bash
# Enable and start service
sudo systemctl enable crypto-api
sudo systemctl start crypto-api

# Check status
sudo systemctl status crypto-api

# Stop service
sudo systemctl stop crypto-api

# View logs
sudo journalctl -u crypto-api -f
```

### Supervisor Service
```bash
# Start supervisor
supervisord -c supervisor.conf

# Check status
supervisorctl status

# Control services
supervisorctl start crypto-api
supervisorctl stop crypto-api
supervisorctl restart crypto-api
```

## 📊 API Endpoints

| **Endpoint** | **Description** | **Example** |
|--------------|-----------------|-------------|
| `/health` | Server health status | `curl http://localhost:5001/health` |
| `/realtime` | All real-time data | `curl http://localhost:5001/realtime` |
| `/realtime?limit=10` | Limited real-time data | `curl "http://localhost:5001/realtime?limit=10"` |
| `/realtime/binance` | Binance data only | `curl http://localhost:5001/realtime/binance` |
| `/exchanges` | List all exchanges | `curl http://localhost:5001/exchanges` |
| `/symbols` | List all symbols | `curl http://localhost:5001/symbols` |
| `/market-data` | Market data only | `curl http://localhost:5001/market-data` |
| `/order-book` | Order book data only | `curl http://localhost:5001/order-book` |
| `/trades` | Trade data only | `curl http://localhost:5001/trades` |
| `/funding-rates` | Funding rates only | `curl http://localhost:5001/funding-rates` |
| `/open-interest` | Open interest only | `curl http://localhost:5001/open-interest` |

## 🚨 Troubleshooting

### Common Issues

1. **Server Not Responding**
   ```bash
   # Check if process is running
   ps aux | grep gunicorn
   
   # Check logs for errors
   tail -20 logs/gunicorn.log
   
   # Restart server
   ./stop_production_api.sh && ./start_production_api.sh
   ```

2. **Port Already in Use**
   ```bash
   # Find process using port 5001
   sudo lsof -i :5001
   
   # Kill the process
   sudo kill -9 <PID>
   ```

3. **MongoDB Connection Issues**
   ```bash
   # Check MongoDB status
   sudo systemctl status mongodb
   
   # Start MongoDB
   sudo systemctl start mongodb
   
   # Test connection
   python3 -c "from config import Config; from pymongo import MongoClient; MongoClient(Config.MONGODB_URL).admin.command('ping')"
   ```

4. **High Memory Usage**
   ```bash
   # Check memory usage
   free -h
   
   # Check process memory
   ps aux --sort=-%mem | head -10
   
   # Restart server to free memory
   ./stop_production_api.sh && ./start_production_api.sh
   ```

### Log Locations

- **Main Log**: `logs/gunicorn.log`
- **Access Log**: `logs/access.log`
- **Error Log**: `logs/error.log`
- **Monitor Log**: `logs/api_monitor.log`
- **System Log**: `/var/log/syslog`

## 📈 Performance Monitoring

### System Resources
```bash
# CPU usage
top -p $(pgrep gunicorn)

# Memory usage
free -h

# Disk usage
df -h

# Network connections
netstat -tulpn | grep :5001
```

### API Performance
```bash
# Response time test
time curl -s http://localhost:5001/health > /dev/null

# Load test (install apache bench first)
ab -n 100 -c 10 http://localhost:5001/health

# Monitor real-time
watch -n 1 'curl -s http://localhost:5001/health | jq .status'
```

## 🔒 Security Checks

### Firewall Status
```bash
# Check firewall rules
sudo ufw status

# Allow/deny ports
sudo ufw allow 5001
sudo ufw deny 5001
```

### Process Security
```bash
# Check process owner
ps aux | grep gunicorn

# Check file permissions
ls -la *.sh
ls -la logs/
```

## 📋 Maintenance Tasks

### Daily Checks
```bash
# Health check
curl http://localhost:5001/health

# Monitor resources
python3 monitor_api.py once

# Check logs for errors
grep -i error logs/gunicorn.log | tail -10
```

### Weekly Tasks
```bash
# Restart server (memory cleanup)
./stop_production_api.sh && ./start_production_api.sh

# Check disk space
df -h

# Update dependencies
pip install -r requirements_production.txt --upgrade
```

### Monthly Tasks
```bash
# Rotate logs
sudo logrotate /etc/logrotate.d/crypto-api

# Update system
sudo apt update && sudo apt upgrade

# Backup database
mongodump --db crypto_trading_data --out backup/
```

## 🎯 Quick Status Check

```bash
#!/bin/bash
echo "🔍 Crypto API Server Status Check"
echo "================================="
echo "Health: $(curl -s http://localhost:5001/health | jq -r .status)"
echo "Processes: $(ps aux | grep gunicorn | grep -v grep | wc -l)"
echo "Memory: $(free -h | grep Mem | awk '{print $3"/"$2}')"
echo "Disk: $(df -h / | awk 'NR==2{print $5}')"
echo "Uptime: $(uptime | awk '{print $3,$4}' | sed 's/,//')"
```

Save this as `status_check.sh` and make it executable:
```bash
chmod +x status_check.sh
./status_check.sh
```
