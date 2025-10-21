#!/usr/bin/env python3
"""
API Server Health Monitor
========================

Monitors the health and performance of the production API server.
"""

import requests
import time
import json
import psutil
import os
from datetime import datetime
from pathlib import Path

class APIMonitor:
    """Monitor API server health and performance."""
    
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.log_file = Path("logs/api_monitor.log")
        self.log_file.parent.mkdir(exist_ok=True)
    
    def log(self, message):
        """Log message with timestamp."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {message}\n"
        print(log_entry.strip())
        with open(self.log_file, "a") as f:
            f.write(log_entry)
    
    def check_health(self):
        """Check API health endpoint."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Health check passed: {data}")
                return True
            else:
                self.log(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"❌ Health check error: {e}")
            return False
    
    def check_realtime_data(self):
        """Check real-time data endpoint."""
        try:
            response = requests.get(f"{self.base_url}/realtime?limit=1", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    self.log(f"✅ Real-time data available: {len(data['data'])} records")
                    return True
                else:
                    self.log("⚠️  Real-time data endpoint empty")
                    return False
            else:
                self.log(f"❌ Real-time data check failed: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"❌ Real-time data error: {e}")
            return False
    
    def check_system_resources(self):
        """Check system resource usage."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available = memory.available / (1024**3)  # GB
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free = disk.free / (1024**3)  # GB
            
            # Check for Gunicorn processes
            gunicorn_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
                try:
                    if 'gunicorn' in proc.info['name'].lower() or any('gunicorn' in str(arg) for arg in proc.info['cmdline']):
                        gunicorn_processes.append({
                            'pid': proc.info['pid'],
                            'cpu_percent': proc.info['cpu_percent'],
                            'memory_percent': proc.info['memory_percent']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            self.log(f"📊 System Resources:")
            self.log(f"   CPU: {cpu_percent}%")
            self.log(f"   Memory: {memory_percent}% ({memory_available:.1f}GB available)")
            self.log(f"   Disk: {disk_percent}% ({disk_free:.1f}GB free)")
            self.log(f"   Gunicorn processes: {len(gunicorn_processes)}")
            
            for proc in gunicorn_processes:
                self.log(f"     PID {proc['pid']}: CPU {proc['cpu_percent']}%, Memory {proc['memory_percent']}%")
            
            # Alert if resources are high
            if cpu_percent > 80:
                self.log(f"⚠️  High CPU usage: {cpu_percent}%")
            if memory_percent > 80:
                self.log(f"⚠️  High memory usage: {memory_percent}%")
            if disk_percent > 90:
                self.log(f"⚠️  High disk usage: {disk_percent}%")
            
            return True
            
        except Exception as e:
            self.log(f"❌ System resource check error: {e}")
            return False
    
    def check_response_times(self):
        """Check API response times."""
        endpoints = [
            "/health",
            "/realtime?limit=1",
            "/exchanges",
            "/symbols"
        ]
        
        for endpoint in endpoints:
            try:
                start_time = time.time()
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # ms
                
                if response.status_code == 200:
                    self.log(f"✅ {endpoint}: {response_time:.2f}ms")
                else:
                    self.log(f"❌ {endpoint}: {response.status_code} ({response_time:.2f}ms)")
                    
            except Exception as e:
                self.log(f"❌ {endpoint}: Error - {e}")
    
    def run_monitoring_cycle(self):
        """Run a complete monitoring cycle."""
        self.log("🔍 Starting API monitoring cycle")
        
        # Health check
        health_ok = self.check_health()
        
        # Real-time data check
        data_ok = self.check_realtime_data()
        
        # System resources
        resources_ok = self.check_system_resources()
        
        # Response times
        self.check_response_times()
        
        # Summary
        if health_ok and data_ok and resources_ok:
            self.log("✅ All checks passed")
        else:
            self.log("❌ Some checks failed")
        
        self.log("=" * 50)
    
    def run_continuous_monitoring(self, interval=60):
        """Run continuous monitoring."""
        self.log(f"🚀 Starting continuous monitoring (interval: {interval}s)")
        
        try:
            while True:
                self.run_monitoring_cycle()
                time.sleep(interval)
        except KeyboardInterrupt:
            self.log("🛑 Monitoring stopped by user")
        except Exception as e:
            self.log(f"❌ Monitoring error: {e}")

def main():
    """Main function."""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "once":
            monitor = APIMonitor()
            monitor.run_monitoring_cycle()
        elif sys.argv[1] == "continuous":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            monitor = APIMonitor()
            monitor.run_continuous_monitoring(interval)
        else:
            print("Usage: python monitor_api.py [once|continuous] [interval_seconds]")
    else:
        print("API Server Health Monitor")
        print("========================")
        print("Usage:")
        print("  python monitor_api.py once                    # Run once")
        print("  python monitor_api.py continuous [60]         # Run continuously")

if __name__ == "__main__":
    main()
