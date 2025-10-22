#!/usr/bin/env python3
"""
AWS Lambda Function for On-Demand Historical Data Collection
===========================================================

This Lambda function triggers historical data collection on demand.
"""

import json
import boto3
import os
import subprocess
import tempfile
import shutil
from datetime import datetime

def lambda_handler(event, context):
    """
    Lambda function to trigger historical data collection
    
    Event parameters:
    - start_date: Start date for collection (default: 2021-01-01)
    - end_date: End date for collection (default: 2024-12-31)
    - exchanges: List of exchanges to collect from (default: all)
    - symbols: List of symbols to collect (default: BTC pairs)
    - timeframes: List of timeframes (default: 1m, 1h)
    """
    try:
        # Parse event parameters
        start_date = event.get('start_date', '2021-01-01')
        end_date = event.get('end_date', '2024-12-31')
        exchanges = event.get('exchanges', ['binance', 'bybit', 'kraken', 'gate'])
        symbols = event.get('symbols', ['BTCUSDT', 'BTCUSDC', 'BTCBUSD'])
        timeframes = event.get('timeframes', ['1m', '1h'])
        
        # Set environment variables
        os.environ['MONGODB_URL'] = event.get('mongodb_url', os.environ.get('MONGODB_URL', 'mongodb://localhost:27017'))
        os.environ['MONGODB_DATABASE'] = event.get('mongodb_database', os.environ.get('MONGODB_DATABASE', 'model-collections'))
        
        # Create temporary directory for code
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy necessary files to temp directory
            # Note: In production, these files should be packaged with the Lambda
            files_to_copy = [
                'manage_historical_collection.py',
                'four_year_historical_collector.py',
                'simple_mongodb_collector.py',
                'config.py',
                'collection_config.json'
            ]
            
            for file in files_to_copy:
                if os.path.exists(file):
                    shutil.copy2(file, temp_dir)
            
            # Change to temp directory
            os.chdir(temp_dir)
            
            # Prepare collection command
            cmd = [
                'python', 'manage_historical_collection.py', 'start',
                '--start-date', start_date,
                '--end-date', end_date,
                '--exchanges', ','.join(exchanges),
                '--symbols', ','.join(symbols),
                '--timeframes', ','.join(timeframes)
            ]
            
            # Run historical collection
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=900  # 15 minutes timeout
            )
            
            # Return results
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Historical data collection completed',
                    'start_date': start_date,
                    'end_date': end_date,
                    'exchanges': exchanges,
                    'symbols': symbols,
                    'timeframes': timeframes,
                    'output': result.stdout,
                    'error': result.stderr,
                    'return_code': result.returncode,
                    'timestamp': datetime.now().isoformat()
                })
            }
            
    except subprocess.TimeoutExpired:
        return {
            'statusCode': 408,
            'body': json.dumps({
                'error': 'Collection timeout - process took longer than 15 minutes',
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        }

def create_lambda_package():
    """
    Create a deployment package for the Lambda function
    """
    import zipfile
    
    # Files to include in the package
    files_to_include = [
        'lambda/historical-collection.py',
        'manage_historical_collection.py',
        'four_year_historical_collector.py',
        'simple_mongodb_collector.py',
        'config.py',
        'collection_config.json',
        'requirements_production.txt'
    ]
    
    with zipfile.ZipFile('historical-collection-lambda.zip', 'w') as zip_file:
        for file in files_to_include:
            if os.path.exists(file):
                zip_file.write(file)
    
    print("Lambda package created: historical-collection-lambda.zip")

if __name__ == "__main__":
    # Test the function locally
    test_event = {
        'start_date': '2024-01-01',
        'end_date': '2024-01-31',
        'exchanges': ['binance'],
        'symbols': ['BTCUSDT'],
        'timeframes': ['1h']
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
