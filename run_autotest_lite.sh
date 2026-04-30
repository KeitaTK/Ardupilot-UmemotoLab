#!/bin/bash
# AP_Observer 簡易オートテストスクリプト
# 使い方: ./run_autotest_lite.sh [--speedup=N]
#   --speedup=N  : シミュレーション倍速設定（デフォルト: 300）
#
# このスクリプトは以下を実行する:
#   1. SITL ビルド（差分ビルド）
#   2. test.CopterObserver（Observer 3テストのみ: Parameters, Logging, EKFOperation）

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"

# デフォルト値
SPEEDUP=1000

# 引数解析
for arg in "$@"; do
    case $arg in
        --speedup=*)
            SPEEDUP="${arg#*=}"
            shift
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Usage: $0 [--speedup=N]"
            exit 1
            ;;
    esac
done

echo "=========================================="
echo " AP_Observer Lite Autotest"
echo " Speedup: ${SPEEDUP}"
echo "=========================================="

# Step 1: SITL ビルド
echo ""
echo "[1/2] Building SITL..."
source venv/bin/activate
./waf configure --board sitl
./waf build --target bin/arducopter
echo "Build complete."

# Step 2: Observer テスト実行
echo ""
echo "[2/2] Running test.CopterObserver..."
timeout 600 Tools/autotest/autotest.py \
    --no-clean \
    --speedup="${SPEEDUP}" \
    build.Copter \
    test.CopterObserver

echo ""
echo "=========================================="
echo " AP_Observer Lite Autotest COMPLETE"
echo "=========================================="
