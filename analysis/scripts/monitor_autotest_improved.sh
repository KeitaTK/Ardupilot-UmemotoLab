#!/bin/bash

# 改善版オートテスト監視スクリプト
# 別ターミナルで実行し、リアルタイムでテスト状況を表示

LOG_FILE="${1:-/tmp/autotest_run.log}"
CHECK_INTERVAL=30  # 30秒ごとにチェック
STALL_THRESHOLD=300  # 5分間変化がなければスタック判定

if [ ! -f "$LOG_FILE" ]; then
    echo "Error: Log file $LOG_FILE not found"
    exit 1
fi

echo "======================================"
echo " ArduPilot Autotest Monitor (Improved)"
echo "======================================"
echo "Log file: $LOG_FILE"
echo "Check interval: ${CHECK_INTERVAL}s"
echo "Press Ctrl+C to stop monitoring"
echo "======================================"
echo ""

last_size=0
stall_counter=0

while true; do
    # テストプロセスの確認
    if ! pgrep -f "autotest.py" > /dev/null; then
        echo "[$(date '+%H:%M:%S')] ⚠️  autotest.py process not found - test may have completed"
        
        # 最終結果を表示
        echo ""
        echo "========== FINAL RESULTS =========="
        total_tests=$(grep -E "(PASSED|FAILED):" "$LOG_FILE" 2>/dev/null | wc -l)
        passed=$(grep "PASSED:" "$LOG_FILE" 2>/dev/null | wc -l)
        failed=$(grep "FAILED:" "$LOG_FILE" 2>/dev/null | wc -l)
        
        echo "Total tests: $total_tests"
        echo "✅ PASSED: $passed"
        echo "❌ FAILED: $failed"
        
        if [ $failed -gt 0 ]; then
            echo ""
            echo "Failed tests:"
            grep "FAILED:" "$LOG_FILE" | tail -20
        fi
        
        exit 0
    fi
    
    # 現在のログファイルサイズ
    current_size=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null)
    
    # 進捗確認
    if [ "$current_size" -gt "$last_size" ]; then
        # 進捗あり
        size_diff=$((current_size - last_size))
        stall_counter=0
        
        # 最新の結果を表示
        passed=$(grep "PASSED:" "$LOG_FILE" 2>/dev/null | wc -l)
        failed=$(grep "FAILED:" "$LOG_FILE" 2>/dev/null | wc -l)
        
        # 現在実行中のテスト
        current_test=$(tail -50 "$LOG_FILE" | grep -E "^AT-[0-9]+\.[0-9]+: #+" | tail -1 | sed 's/.*##/##/')
        
        echo "[$(date '+%H:%M:%S')] 📊 Progress: ✅$passed ❌$failed (+${size_diff} bytes)"
        if [ -n "$current_test" ]; then
            echo "   └─ Current: ${current_test:0:80}"
        fi
    else
        # 進捗なし
        stall_counter=$((stall_counter + CHECK_INTERVAL))
        
        if [ $stall_counter -ge $STALL_THRESHOLD ]; then
            echo "[$(date '+%H:%M:%S')] ⚠️  WARNING: No progress for ${stall_counter}s - test may be stuck"
            echo "   Last 10 lines:"
            tail -10 "$LOG_FILE" | sed 's/^/   | /'
        else
            echo "[$(date '+%H:%M:%S')] ⏳ Waiting... (no change for ${stall_counter}s)"
        fi
    fi
    
    last_size=$current_size
    sleep $CHECK_INTERVAL
done
