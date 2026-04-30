#!/bin/bash
# AP_Observer 本オートテストスクリプト
# 使い方: ./run_autotest_full.sh [--speedup=N]
#   --speedup=N  : シミュレーション倍速設定（デフォルト: 2000）
#
# このスクリプトは test.CopterTests2b を実行する。
# tests2b には Observer テストに加えて MotorVibration, FFT, GPS 等が含まれる。

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"

# デフォルト値
SPEEDUP=2000

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
echo " AP_Observer Full Autotest (tests2b)"
echo " Speedup: ${SPEEDUP}"
echo "=========================================="

# SITL ビルド（必要に応じて --no-clean でスキップ）
echo ""
echo "[1/2] Building SITL..."
source venv/bin/activate
./waf configure --board sitl
./waf build --target bin/arducopter
echo "Build complete."

# tests2b 実行
echo ""
echo "[2/2] Running test.CopterTests2b..."
timeout 1200 Tools/autotest/autotest.py \
    --no-clean \
    --speedup="${SPEEDUP}" \
    build.Copter \
    test.CopterTests2b

echo ""
echo "=========================================="
echo " AP_Observer Full Autotest COMPLETE"
echo "=========================================="
