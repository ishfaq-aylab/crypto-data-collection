# 🚀 Production Deployment Guide

Complete guide for deploying the Crypto Data Collection API Server in production.

## 📋 Prerequisites

- Ubuntu 20.04+ or CentOS 8+
- Python 3.12+
- MongoDB 7.0+
- Nginx (optional, for reverse proxy)
- SSL certificates (for HTTPS)

## 🛠️ Installation Steps

### 1. Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.12 python3.12-venv nginx supervisor

# CentOS/RHEL
sudo yum install -y python312 python312-pip nginx supervisor
```

### 2. Install Production Requirements

```bash
# Install production dependencies
pip install -r requirements_production.txt

# Or install Gunicorn separately
pip install gunicorn
```

### 3. Configure Environment Variables

```bash
# Copy and edit environment file
cp env.example .env

# Edit production settings
nano .env
```

**Production Environment Variables:**
```bash
# Database
MONGODB_URL="mongodb://localhost:27017"
MONGODB_DATABASE="crypto_trading_data"

# API Server
API_HOST="0.0.0.0"
API_PORT="5001"
API_DEBUG="false"
API_LOG_LEVEL="WARNING"

# Security
ALERT_ON_FAILURE="true"
MONITORING_ENABLED="true"
```

## 🚀 Deployment Options

### Option 1: Direct Gunicorn (Recommended)

```bash
# Start production server
./start_production_api.sh

# Stop production server
./stop_production_api.sh

# Check status
ps aux | grep gunicorn
```

### Option 2: Systemd Service

```bash
# Copy service file
sudo cp crypto-api.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable crypto-api
sudo systemctl start crypto-api

# Check status
sudo systemctl status crypto-api

# View logs
sudo journalctl -u crypto-api -f
```

### Option 3: Supervisor (Process Management)

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

## 🌐 Nginx Reverse Proxy (Optional)

### 1. Install and Configure Nginx

```bash
# Install Nginx
sudo apt install nginx

# Copy configuration
sudo cp nginx.conf /etc/nginx/sites-available/crypto-api
sudo ln -s /etc/nginx/sites-available/crypto-api /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### 2. SSL Configuration (HTTPS)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 Monitoring and Health Checks

### 1. Health Monitoring

```bash
# Run health check once
python3 monitor_api.py once

# Run continuous monitoring
python3 monitor_api.py continuous 60

# Check logs
tail -f logs/api_monitor.log
```

### 2. System Monitoring

```bash
# Check API server status
curl http://localhost:5001/health

# Check real-time data
curl http://localhost:5001/realtime?limit=1

# Check system resources
htop
```

### 3. Log Management

```bash
# View API logs
tail -f logs/gunicorn.log
tail -f logs/access.log
tail -f logs/error.log

# Rotate logs (add to crontab)
0 0 * * * /usr/sbin/logrotate /etc/logrotate.d/crypto-api
```

## 🔧 Configuration Files

### Gunicorn Configuration (`gunicorn.conf.py`)
- Worker processes: `CPU cores * 2 + 1`
- Timeout: 30 seconds
- Max requests: 1000 per worker
- Logging: Access and error logs

### Nginx Configuration (`nginx.conf`)
- Rate limiting: 10 req/s (API), 50 req/s (realtime)
- Security headers
- Proxy settings
- SSL support

### Systemd Service (`crypto-api.service`)
- Auto-restart on failure
- Resource limits
- Security settings
- Logging to journal

## 🚨 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   sudo lsof -i :5001
   sudo kill -9 <PID>
   ```

2. **Permission Denied**
   ```bash
   sudo chown -R $USER:$USER /path/to/project
   chmod +x *.sh
   ```

3. **MongoDB Connection Failed**
   ```bash
   sudo systemctl status mongodb
   sudo systemctl start mongodb
   ```

4. **High Memory Usage**
   ```bash
   # Reduce workers in gunicorn.conf.py
   workers = 2
   ```

### Log Locations

- **API Logs**: `logs/gunicorn.log`
- **Access Logs**: `logs/access.log`
- **Error Logs**: `logs/error.log`
- **Monitor Logs**: `logs/api_monitor.log`
- **System Logs**: `/var/log/syslog`

## 📈 Performance Optimization

### 1. Gunicorn Tuning

```python
# In gunicorn.conf.py
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"  # For async workloads
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
```

### 2. MongoDB Optimization

```javascript
// Create indexes
db.market_data.createIndex({"exchange": 1, "symbol": 1, "timestamp": -1})
db.historical_data.createIndex({"exchange": 1, "symbol": 1, "timeframe": 1, "timestamp": -1})
```

### 3. Nginx Optimization

```nginx
# In nginx.conf
worker_processes auto;
worker_connections 1024;
gzip on;
gzip_types text/plain application/json;
```

## 🔒 Security Considerations

1. **Firewall Rules**
   ```bash
   sudo ufw allow 22    # SSH
   sudo ufw allow 80    # HTTP
   sudo ufw allow 443   # HTTPS
   sudo ufw deny 5001   # Block direct API access
   ```

2. **User Permissions**
   ```bash
   # Create dedicated user
   sudo useradd -m -s /bin/bash crypto-api
   sudo chown -R crypto-api:crypto-api /path/to/project
   ```

3. **SSL/TLS**
   - Use Let's Encrypt for free certificates
   - Enable HSTS headers
   - Use strong cipher suites

## 📊 Production Checklist

- [ ] Environment variables configured
- [ ] Production requirements installed
- [ ] Gunicorn configuration optimized
- [ ] Nginx reverse proxy configured
- [ ] SSL certificates installed
- [ ] Systemd service enabled
- [ ] Log rotation configured
- [ ] Monitoring setup
- [ ] Firewall rules applied
- [ ] Backup strategy implemented
- [ ] Health checks working
- [ ] Load testing completed

## 🎯 Quick Start Commands

```bash
# 1. Install dependencies
pip install -r requirements_production.txt

# 2. Configure environment
cp env.example .env
nano .env

# 3. Start production server
./start_production_api.sh

# 4. Test health
curl http://localhost:5001/health

# 5. Monitor
python3 monitor_api.py continuous
```

## 📞 Support

For issues and questions:
- Check logs: `logs/gunicorn.log`
- Monitor health: `python3 monitor_api.py once`
- System status: `sudo systemctl status crypto-api`
