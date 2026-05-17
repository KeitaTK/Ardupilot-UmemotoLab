#!/bin/bash
# ==========================================
# run_autotest_medium.sh
# Medium autotest: Observer + core functionality tests (~2min)
# ==========================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# デフォルト設定
SPEEDUP=${SPEEDUP:-1000}
TIMEOUT=${TIMEOUT:-300}  # 5分タイムアウト

echo "=========================================="
echo "Medium Autotest Start"
echo "  Target: test.CopterMedium"
echo "  Speedup: ${SPEEDUP}"
echo "  Timeout: ${TIMEOUT}s"
echo "=========================================="

source .venv/bin/activate

# SITLビルド
echo "--- SITL Build ---"
./waf configure --board sitl
./waf build --target bin/arducopter

# Mediumテスト実行
echo "--- Running Medium Test ---"
timeout ${TIMEOUT} ./Tools/autotest/autotest.py \
    --speedup ${SPEEDUP} \
    test.CopterMedium

RESULT=$?
if [ $RESULT -eq 0 ]; then
    echo "=========================================="
    echo "Medium Autotest: PASSED"
    echo "=========================================="
else
    echo "=========================================="
    echo "Medium Autotest: FAILED (exit code: $RESULT)"
    echo "=========================================="
fi
exit $RESULT
