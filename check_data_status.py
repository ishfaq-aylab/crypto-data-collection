#!/usr/bin/env python3
"""Check data collection status and statistics."""

import asyncio
import sys
import argparse
from datetime import datetime, timedelta
from pymongo import MongoClient
from loguru import logger

from collector_config import get_enabled_exchanges, MONGODB_CONFIG


async def check_data_status(exchange_filter=None, detailed=False, recent=False):
    """Check the status of data collection across all exchanges."""
    client = MongoClient(f"mongodb://{MONGODB_CONFIG['host']}:{MONGODB_CONFIG['port']}")
    db = client[MONGODB_CONFIG['database']]
    
    print("=" * 80)
    print("📊 DATA COLLECTION STATUS REPORT")
    print("=" * 80)
    print(f"📅 Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get enabled exchanges and data types
    all_exchanges = get_enabled_exchanges()
    exchanges = [exchange_filter] if exchange_filter else all_exchanges
    data_types = ['market_data', 'tick_prices', 'order_book_data', 'volume_liquidity', 'funding_rates', 'open_interest']
    
    # Create status table
    print("| Exchange | Market Data | Tick Prices | Order Book | Volume/Liquidity | Funding Rates | Open Interest |")
    print("|----------|-------------|-------------|------------|------------------|---------------|---------------|")
    
    for exchange in exchanges:
        row = [exchange.upper()]
        for data_type in data_types:
            collection = db[data_type]
            count = collection.count_documents({'exchange': exchange})
            status = '✅' if count > 0 else '❌'
            row.append(f'{status} ({count:,})')
        
        print('| ' + ' | '.join(row) + ' |')
    
    print()
    
    # Detailed statistics
    print("📈 DETAILED STATISTICS:")
    print()
    
    for exchange in exchanges:
        print(f"=== {exchange.upper()} ===")
        
        for data_type in data_types:
            collection = db[data_type]
            total_count = collection.count_documents({'exchange': exchange})
            
            if total_count > 0:
                # Get recent data (last 5 minutes)
                recent_time = datetime.now() - timedelta(minutes=5)
                recent_count = collection.count_documents({
                    'exchange': exchange,
                    'timestamp': {'$gte': recent_time}
                })
                
                # Get latest document
                latest = collection.find_one(
                    {'exchange': exchange}, 
                    sort=[('timestamp', -1)]
                )
                
                latest_time = latest.get('timestamp', 'Unknown') if latest else 'No data'
                
                print(f"  {data_type}:")
                print(f"    Total documents: {total_count:,}")
                print(f"    Recent (5min): {recent_count:,}")
                print(f"    Latest: {latest_time}")
            else:
                print(f"  {data_type}: No data")
        
        print()
    
    # Overall summary
    print("🎯 OVERALL SUMMARY:")
    total_documents = 0
    working_exchanges = 0
    
    for exchange in exchanges:
        exchange_total = 0
        for data_type in data_types:
            collection = db[data_type]
            count = collection.count_documents({'exchange': exchange})
            exchange_total += count
        
        total_documents += exchange_total
        if exchange_total > 0:
            working_exchanges += 1
    
    print(f"  Total documents: {total_documents:,}")
    print(f"  Working exchanges: {working_exchanges}/{len(exchanges)}")
    print(f"  Data types: {len(data_types)}")
    
    # Check data freshness
    print()
    print("🕒 DATA FRESHNESS CHECK:")
    for exchange in exchanges:
        print(f"  {exchange.upper()}:")
        for data_type in data_types:
            collection = db[data_type]
            latest = collection.find_one(
                {'exchange': exchange}, 
                sort=[('timestamp', -1)]
            )
            
            if latest:
                latest_time = latest.get('timestamp')
                if isinstance(latest_time, datetime):
                    age_minutes = (datetime.now() - latest_time).total_seconds() / 60
                    if age_minutes < 5:
                        status = "🟢 Fresh"
                    elif age_minutes < 30:
                        status = "🟡 Recent"
                    else:
                        status = "🔴 Stale"
                    
                    print(f"    {data_type}: {status} ({age_minutes:.1f} min ago)")
                else:
                    print(f"    {data_type}: ⚠️  Unknown timestamp format")
            else:
                print(f"    {data_type}: ❌ No data")
    
    client.close()
    print()
    print("=" * 80)
    print("✅ Status check completed!")
    print("=" * 80)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Check data collection status')
    parser.add_argument('--exchange', help='Filter by specific exchange')
    parser.add_argument('--detailed', action='store_true', help='Show detailed statistics')
    parser.add_argument('--recent', action='store_true', help='Show only recent data (last 5 minutes)')
    
    args = parser.parse_args()
    
    try:
        await check_data_status(
            exchange_filter=args.exchange,
            detailed=args.detailed,
            recent=args.recent
        )
    except Exception as e:
        logger.error(f"❌ Error checking data status: {e}")
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
