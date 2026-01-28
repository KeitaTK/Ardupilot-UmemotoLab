#!/bin/bash
# Autotest monitoring script

LOG_FILE="/tmp/autotest_run2.log"
LAST_SIZE=0
STUCK_COUNT=0
MAX_STUCK=5

echo "=== Autotest Monitor Started ==="
echo "Monitoring log file: $LOG_FILE"
echo ""

while true; do
    # Check if autotest process is still running
    if ! pgrep -f "autotest.py test.Copter" > /dev/null; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Autotest process has terminated"
        break
    fi
    
    # Check current file size
    if [ -f "$LOG_FILE" ]; then
        CURRENT_SIZE=$(wc -c < "$LOG_FILE")
        
        # If file size hasn't changed, increment stuck counter
        if [ "$CURRENT_SIZE" -eq "$LAST_SIZE" ]; then
            STUCK_COUNT=$((STUCK_COUNT + 1))
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] No progress detected ($STUCK_COUNT/$MAX_STUCK)"
            
            # Show last few lines to see where it's stuck
            echo "--- Last 10 lines ---"
            tail -10 "$LOG_FILE"
            echo "-------------------"
        else
            STUCK_COUNT=0
            # Show test progress
            PASSED=$(grep -c "PASSED:" "$LOG_FILE" 2>/dev/null || echo 0)
            FAILED=$(grep -c "FAILED:" "$LOG_FILE" 2>/dev/null || echo 0)
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Progress: PASSED=$PASSED, FAILED=$FAILED, Size=$CURRENT_SIZE bytes"
            
            # Show current test
            CURRENT_TEST=$(tail -50 "$LOG_FILE" | grep "##########" | tail -1)
            if [ -n "$CURRENT_TEST" ]; then
                echo "Current: $CURRENT_TEST"
            fi
        fi
        
        LAST_SIZE=$CURRENT_SIZE
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Log file not found yet"
    fi
    
    # Sleep for 60 seconds
    sleep 60
done

echo ""
echo "=== Autotest Monitor Finished ==="
echo "=== Final Summary ==="
if [ -f "$LOG_FILE" ]; then
    echo "PASSED tests:"
    grep "PASSED:" "$LOG_FILE" | wc -l
    echo ""
    echo "FAILED tests:"
    grep "FAILED:" "$LOG_FILE" | wc -l
    echo ""
    echo "Last 30 lines of log:"
    tail -30 "$LOG_FILE"
fi
