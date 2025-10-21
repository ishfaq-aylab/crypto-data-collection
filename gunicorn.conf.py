#!/usr/bin/env python3
"""
Gunicorn Configuration for Production
====================================

Production configuration for the crypto data API server.
"""

import os
import multiprocessing
from pathlib import Path

# Server socket
bind = f"0.0.0.0:{os.getenv('API_PORT', '5001')}"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = os.getenv('API_LOG_LEVEL', 'info').lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "crypto-api-server"

# Server mechanics
daemon = False
pidfile = "logs/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (uncomment and configure for HTTPS)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Preload app for better performance
preload_app = True

# Worker timeout
graceful_timeout = 30

# Max header line size
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Security
forwarded_allow_ips = "*"
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}

# Environment variables
raw_env = [
    f"FLASK_ENV=production",
    f"PYTHONPATH={Path(__file__).parent}",
]

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("🚀 Crypto API Server is ready to accept connections")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("🔄 Worker received SIGINT or SIGQUIT")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info(f"🔄 Worker spawned (pid: {worker.pid})")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"✅ Worker spawned (pid: {worker.pid})")

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.error(f"❌ Worker aborted (pid: {worker.pid})")

def on_exit(server):
    """Called just before exiting."""
    server.log.info("👋 Crypto API Server shutting down")
