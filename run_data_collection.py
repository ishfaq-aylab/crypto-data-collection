#!/usr/bin/env python3
"""Simple launcher script for data collection orchestrator."""

import sys
import asyncio
from datetime import datetime
from loguru import logger

from data_collection_orchestrator import SimpleOptimizedOrchestrator as DataCollectionOrchestrator
from config import Config
from collector_config import COLLECTION_CONFIG, get_enabled_exchanges, get_enabled_data_types


def print_banner():
    """Print startup banner."""
    print("=" * 80)
    print("🚀 CRYPTO DATA COLLECTION ORCHESTRATOR")
    print("=" * 80)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  Default duration: {Config.COLLECTION_DURATION} seconds")
    print(f"🔄 Default poll interval: {Config.COLLECTION_POLL_INTERVAL} seconds")
    print()


def print_configuration():
    """Print current configuration."""
    print("📋 CONFIGURATION:")
    print(f"  Enabled exchanges: {', '.join(get_enabled_exchanges())}")
    print(f"  Enabled data types: {', '.join(get_enabled_data_types())}")
    print()


def print_usage():
    """Print usage information."""
    print("USAGE:")
    print("  python run_data_collection.py [duration_seconds] [poll_interval_seconds]")
    print()
    print("EXAMPLES:")
    print("  python run_data_collection.py                    # Run for 1 hour (default)")
    print("  python run_data_collection.py 7200               # Run for 2 hours")
    print("  python run_data_collection.py 3600 60            # Run for 1 hour, poll every 60 seconds")
    print("  python run_data_collection.py 0                  # Run indefinitely (until Ctrl+C)")
    print()


def parse_arguments():
    """Parse command line arguments."""
    duration = COLLECTION_CONFIG['default_duration_seconds']
    poll_interval = COLLECTION_CONFIG['default_poll_interval']
    
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
            if duration < 0:
                print("❌ Duration must be positive or 0 for indefinite")
                sys.exit(1)
        except ValueError:
            print("❌ Invalid duration. Must be a number.")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        try:
            poll_interval = int(sys.argv[2])
            if poll_interval <= 0:
                print("❌ Poll interval must be positive")
                sys.exit(1)
        except ValueError:
            print("❌ Invalid poll interval. Must be a number.")
            sys.exit(1)
    
    return duration, poll_interval


async def main():
    """Main entry point."""
    print_banner()
    print_configuration()
    
    # Parse arguments
    duration, poll_interval = parse_arguments()
    
    # Print run parameters
    if duration == 0:
        print(f"🔄 Poll interval: {poll_interval} seconds")
        print("⏰ Duration: INDEFINITE (Ctrl+C to stop)")
    else:
        print(f"⏱️  Duration: {duration} seconds")
        print(f"🔄 Poll interval: {poll_interval} seconds")
    
    print()
    print("🚀 Starting data collection...")
    print("=" * 80)
    
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        level=COLLECTION_CONFIG['log_level'],
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    )
    
    # Create and run orchestrator
    orchestrator = DataCollectionOrchestrator(
        duration_seconds=duration,
        poll_interval=poll_interval
    )
    
    try:
        await orchestrator.start_collection()
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Print final summary
        status = orchestrator.get_status()
        print()
        print("=" * 80)
        print("📊 FINAL SUMMARY")
        print("=" * 80)
        print(f"Total collectors: {status.get('total_collectors', 0)}")
        print(f"Total tasks: {status.get('total_tasks', 0)}")
        print(f"Running tasks: {status.get('running_tasks', 0)}")
        print(f"Uptime: {status.get('uptime_seconds', 0):.1f} seconds")
        print(f"Health status: {status.get('health_status', {}).get('status', 'unknown')}")
        print()
        print("✅ Data collection completed!")
        print("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
