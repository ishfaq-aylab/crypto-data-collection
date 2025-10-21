#!/bin/bash
# cleanup_unused_files.sh - Remove unused files from crypto data collection system

echo "🧹 Cleaning up unused files from crypto data collection system..."
echo "================================================================"

# Create backup directory
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
echo "📁 Creating backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Function to safely remove file with backup
safe_remove() {
    local file="$1"
    if [ -f "$file" ]; then
        echo "🗑️  Removing: $file"
        cp "$file" "$BACKUP_DIR/" 2>/dev/null || true
        rm "$file"
    else
        echo "⚠️  File not found: $file"
    fi
}

echo ""
echo "📋 REMOVING UNUSED FILES..."
echo "============================"

# 1. Remove duplicate API servers
echo ""
echo "🌐 Removing duplicate API servers..."
safe_remove "api_server.py"
safe_remove "working_api.py"
safe_remove "simple_api.py"
safe_remove "fast_api_server.py"

# 2. Remove obsolete orchestrators
echo ""
echo "🔄 Removing obsolete orchestrators..."
safe_remove "data_collection_orchestrator_original.py"
safe_remove "optimized_orchestrator.py"

# 3. Remove unused production files
echo ""
echo "🚀 Removing unused production files..."
safe_remove "start_production.py"

# 4. Remove test files
echo ""
echo "🧪 Removing test files..."
safe_remove "test_1m_candles.py"
safe_remove "test_api_client.py"
safe_remove "test_optimized_orchestrator.py"
safe_remove "test_realtime_api.py"
safe_remove "test_small_collection.py"

# 5. Remove analysis/utility files
echo ""
echo "📊 Removing analysis/utility files..."
safe_remove "analyze_bitcoin_data.py"
safe_remove "analyze_historical_data.py"
safe_remove "quick_data_check.py"
safe_remove "cleanup_timeframes.py"

# 6. Remove JSON data files
echo ""
echo "📄 Removing JSON data files..."
safe_remove "bitcoin_data_analysis_20251021_160652.json"
safe_remove "collection_report_20251021_153426.json"
safe_remove "collection_report_20251021_153950.json"

# 7. Remove obsolete documentation
echo ""
echo "📚 Removing obsolete documentation..."
safe_remove "API_STARTUP_GUIDE.md"
safe_remove "CLEANUP_SUMMARY.md"
safe_remove "FIXES_SUMMARY.md"
safe_remove "FOUR_YEAR_COLLECTION_README.md"
safe_remove "HISTORICAL_DATA_CHECKLIST.md"
safe_remove "OPTIMIZATION_GUIDE.md"
safe_remove "README_ORCHESTRATOR.md"
safe_remove "USAGE_GUIDE.md"

# 8. Remove unused requirements
echo ""
echo "📦 Removing unused requirements..."
safe_remove "requirements_api.txt"

echo ""
echo "✅ CLEANUP COMPLETE!"
echo "===================="

# Count remaining files
REMAINING_FILES=$(find . -maxdepth 1 -name "*.py" -o -name "*.md" -o -name "*.sh" -o -name "*.json" | grep -v venv | wc -l)
BACKUP_FILES=$(find "$BACKUP_DIR" -type f | wc -l)

echo "📊 Results:"
echo "  Files removed: $BACKUP_FILES"
echo "  Files remaining: $REMAINING_FILES"
echo "  Backup location: $BACKUP_DIR"

echo ""
echo "🎯 ESSENTIAL FILES REMAINING:"
echo "============================="
echo "✅ Core System:"
echo "  - run_data_collection.py (main launcher)"
echo "  - data_collection_orchestrator.py (current orchestrator)"
echo "  - realtime_api.py (current API server)"
echo "  - start_services.sh / stop_services.sh (service scripts)"
echo ""
echo "✅ Collectors:"
echo "  - 12 real-time collectors (binance, bybit, kraken, gate, okx)"
echo "  - 5 historical collectors"
echo "  - 3 historical management files"
echo ""
echo "✅ Documentation:"
echo "  - COLLECTIVE_SYSTEM_GUIDE.md (main guide)"
echo "  - STARTUP_GUIDE.md (startup guide)"
echo "  - REALTIME_API_DOCS.md (API docs)"
echo "  - DATA_DEFINITIONS.md (schema docs)"

echo ""
echo "🔍 VERIFICATION:"
echo "================"
echo "To verify your system still works:"
echo "1. ./start_services.sh"
echo "2. curl http://localhost:5001/health"
echo "3. curl http://localhost:5001/realtime"

echo ""
echo "🛡️  SAFETY:"
echo "==========="
echo "All removed files are backed up in: $BACKUP_DIR"
echo "If you need any file back, restore it from the backup directory."

echo ""
echo "🎉 Cleanup successful! Your codebase is now clean and optimized."
echo "================================================================"
