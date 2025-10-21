#!/usr/bin/env python3
"""Script to update existing files to use environment variables from config.py"""

import os
import re
from pathlib import Path

def update_realtime_api():
    """Update realtime_api.py to use environment variables."""
    file_path = "realtime_api.py"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add import
    if "from config import Config" not in content:
        content = content.replace(
            "from flask import Flask, jsonify, request\nfrom flask_cors import CORS",
            "from flask import Flask, jsonify, request\nfrom flask_cors import CORS\nfrom config import Config"
        )
    
    # Replace MongoDB connection
    content = re.sub(
        r'client = MongoClient\("mongodb://localhost:27017", serverSelectionTimeoutMS=3000\)',
        'client = MongoClient(Config.MONGODB_URL, serverSelectionTimeoutMS=Config.MONGODB_TIMEOUT)',
        content
    )
    
    # Replace API server configuration
    content = re.sub(
        r"app\.run\(host='0\.0\.0\.0', port=5001, debug=False\)",
        "app.run(host=Config.API_HOST, port=Config.API_PORT, debug=Config.API_DEBUG)",
        content
    )
    
    # Replace port in print statement
    content = re.sub(
        r'print\("🚀 Starting Real-time Crypto Data API Server on port 5001\.\.\."\)',
        'print(f"🚀 Starting Real-time Crypto Data API Server on port {Config.API_PORT}...")',
        content
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated {file_path}")

def update_simple_mongodb_collector():
    """Update simple_mongodb_collector.py to use environment variables."""
    file_path = "simple_mongodb_collector.py"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add import
    if "from config import Config" not in content:
        content = content.replace(
            "from pymongo import MongoClient",
            "from pymongo import MongoClient\nfrom config import Config"
        )
    
    # Replace default parameters
    content = re.sub(
        r'def __init__\(self, mongodb_url: str = "mongodb://localhost:27017", database_name: str = "crypto_trading_data"\):',
        'def __init__(self, mongodb_url: str = Config.MONGODB_URL, database_name: str = Config.MONGODB_DATABASE):',
        content
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated {file_path}")

def update_collector_config():
    """Update collector_config.py to use environment variables."""
    file_path = "collector_config.py"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add import
    if "from config import Config" not in content:
        content = content.replace(
            "from typing import Dict, List, Any",
            "from typing import Dict, List, Any\nfrom config import Config"
        )
    
    # Replace COLLECTION_CONFIG
    content = re.sub(
        r'COLLECTION_CONFIG = \{\s*"default_duration_seconds": 3600,\s*"default_poll_interval": 30,\s*"log_level": "INFO",\s*"graceful_shutdown_timeout": 30,\s*\}',
        '''COLLECTION_CONFIG = {
    "default_duration_seconds": Config.COLLECTION_DURATION,
    "default_poll_interval": Config.COLLECTION_POLL_INTERVAL,
    "log_level": Config.COLLECTION_LOG_LEVEL,
    "graceful_shutdown_timeout": Config.COLLECTION_SHUTDOWN_TIMEOUT,
}''',
        content,
        flags=re.DOTALL
    )
    
    # Replace MONGODB_CONFIG
    content = re.sub(
        r'"host": "localhost",\s*"port": 27017,',
        '"host": Config.MONGODB_URL.split("://")[1].split(":")[0],\n    "port": int(Config.MONGODB_URL.split(":")[-1]),',
        content
    )
    
    content = re.sub(
        r'"database": "crypto_trading_data",',
        '"database": Config.MONGODB_DATABASE,',
        content
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated {file_path}")

def update_run_data_collection():
    """Update run_data_collection.py to use environment variables."""
    file_path = "run_data_collection.py"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add import
    if "from config import Config" not in content:
        content = content.replace(
            "from data_collection_orchestrator import SimpleOptimizedOrchestrator as DataCollectionOrchestrator",
            "from data_collection_orchestrator import SimpleOptimizedOrchestrator as DataCollectionOrchestrator\nfrom config import Config"
        )
    
    # Replace hardcoded values
    content = re.sub(
        r'print\(f"⏱️  Default duration: \{COLLECTION_CONFIG\[\'default_duration_seconds\'\]\} seconds"\)',
        'print(f"⏱️  Default duration: {Config.COLLECTION_DURATION} seconds")',
        content
    )
    
    content = re.sub(
        r'print\(f"🔄 Default poll interval: \{COLLECTION_CONFIG\[\'default_poll_interval\'\]\} seconds"\)',
        'print(f"🔄 Default poll interval: {Config.COLLECTION_POLL_INTERVAL} seconds")',
        content
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated {file_path}")

def create_env_file():
    """Create .env file from env.example if it doesn't exist."""
    if not os.path.exists('.env'):
        if os.path.exists('env.example'):
            with open('env.example', 'r') as f:
                content = f.read()
            
            with open('.env', 'w') as f:
                f.write(content)
            
            print("✅ Created .env file from env.example")
        else:
            print("❌ env.example not found")
    else:
        print("ℹ️  .env file already exists")

def main():
    """Main function to update all files."""
    print("🔧 Updating files to use environment variables...")
    print("=" * 60)
    
    # Update files
    update_realtime_api()
    update_simple_mongodb_collector()
    update_collector_config()
    update_run_data_collection()
    
    # Create .env file
    create_env_file()
    
    print("=" * 60)
    print("✅ All files updated successfully!")
    print("")
    print("📋 Next steps:")
    print("1. Review the updated files")
    print("2. Copy env.example to .env and modify as needed")
    print("3. Test the system with: ./start_services.sh")
    print("4. Check configuration with: python -c 'from config import Config; Config.print_config()'")

if __name__ == "__main__":
    main()
