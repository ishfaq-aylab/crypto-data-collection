#!/usr/bin/env python3
"""
WSGI Application Entry Point for Production
==========================================

This file provides the WSGI application entry point for production deployment
using Gunicorn, uWSGI, or other WSGI servers.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the Flask application
from realtime_api import app

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')

# WSGI application entry point
application = app

if __name__ == "__main__":
    # This should not be used in production
    print("⚠️  WARNING: This is a development server!")
    print("   For production, use: gunicorn wsgi:application")
    app.run(host='0.0.0.0', port=5001, debug=False)
