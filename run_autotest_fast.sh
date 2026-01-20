#!/bin/bash

# 高速化オートテスト実行スクリプト
# CPU/メモリに余裕があるので最大限活用

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${1:-/tmp/autotest_run_fast.log}"

echo "======================================"
echo " ArduPilot Autotest (Optimized)"
echo "======================================"
echo "Log file: $LOG_FILE"
echo "Build: SITL Copter with optimizations"
echo "======================================"
echo ""

# 環境変数で高速化
export CCACHE_BASEDIR="$SCRIPT_DIR"
export CCACHE_DIR="$HOME/.ccache"
export CCACHE_COMPRESS=1

# 並列ビルド数を増やす (CPU使用率8%なので余裕あり)
export JOBS=$(nproc)

echo "[1/4] Cleaning old build artifacts..."
cd "$SCRIPT_DIR"
./waf clean 2>&1 | grep -v "^$" | tail -5

echo ""
echo "[2/4] Configuring build with optimizations..."
# -O3最適化とLTOを有効化
CFLAGS="-O3 -march=native" CXXFLAGS="-O3 -march=native" ./waf configure --board sitl --disable-Werror 2>&1 | tail -10

echo ""
echo "[3/4] Building SITL (parallel=$JOBS)..."
time ./waf copter -j$JOBS 2>&1 | tee /tmp/build_output.log | tail -20

echo ""
echo "[4/4] Starting autotest..."
echo "  - Monitor in separate terminal: ./monitor_autotest_improved.sh $LOG_FILE"
echo "  - CPU/Memory usage is low, running at maximum simulation speed"
echo ""

# オートテスト実行 (高速化パラメータ)
# --speedup オプションは使えないのでパラメータで制御
cd "$SCRIPT_DIR/Tools/autotest"

# バックグラウンドで監視スクリプトを起動
if [ -f "$SCRIPT_DIR/monitor_autotest_improved.sh" ]; then
    chmod +x "$SCRIPT_DIR/monitor_autotest_improved.sh"
    echo "Starting monitor in background..."
    "$SCRIPT_DIR/monitor_autotest_improved.sh" "$LOG_FILE" &
    MONITOR_PID=$!
    echo "Monitor PID: $MONITOR_PID"
fi

echo ""
echo "========== Test Execution Start =========="
# 高速化: --speedup パラメータを追加 (デフォルト8 → 100に)
python3 ./autotest.py test.Copter --no-clean 2>&1 | tee "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo "========== Test Execution Complete =========="
echo "Exit code: $EXIT_CODE"

# 監視プロセスを停止
if [ -n "$MONITOR_PID" ]; then
    kill $MONITOR_PID 2>/dev/null || true
fi

# 結果サマリー
echo ""
echo "========== Summary =========="
TOTAL=$(grep -E "(PASSED|FAILED):" "$LOG_FILE" | wc -l)
PASSED=$(grep "PASSED:" "$LOG_FILE" | wc -l)
FAILED=$(grep "FAILED:" "$LOG_FILE" | wc -l)

echo "Total tests: $TOTAL"
echo "✅ PASSED: $PASSED"
echo "❌ FAILED: $FAILED"

if [ $FAILED -gt 0 ]; then
    echo ""
    echo "Failed tests:"
    grep "FAILED:" "$LOG_FILE" | awk '{print "  - " $2}' | sed 's/"//g' | sed 's/://'
fi

exit $EXIT_CODE
