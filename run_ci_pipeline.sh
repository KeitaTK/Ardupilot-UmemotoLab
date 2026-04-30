#!/bin/bash
# AP_Observer CI パイプラインスクリプト
# 使い方: ./run_ci_pipeline.sh [--speedup=N]
#   --speedup=N  : シミュレーション倍速設定（デフォルト: 1000）
#
# パイプライン:
#   1. SITL ビルド
#   2. Lite オートテスト (test.CopterObserver)
#   3. Medium オートテスト (test.CopterMedium)
#   4. Pixhawk6C クリーンビルド
#
# 注意: test.CopterTests2b（本テスト）は手動実行推奨。
#       このパイプラインは Medium テスト通過後のクイックチェック用。

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
echo " AP_Observer CI Pipeline"
echo " Speedup: ${SPEEDUP}"
echo "=========================================="

# Step 1: SITL ビルド
echo ""
echo "[1/4] Building SITL..."
source venv/bin/activate
./waf configure --board sitl
./waf build --target bin/arducopter
echo "Build complete."

# Step 2: Lite オートテスト
echo ""
echo "[2/4] Running Lite autotest (test.CopterObserver)..."
timeout 600 Tools/autotest/autotest.py \
    --no-clean \
    --speedup="${SPEEDUP}" \
    build.Copter \
    test.CopterObserver
echo "Lite autotest passed."

# Step 3: Medium オートテスト
echo ""
echo "[3/4] Running Medium autotest (test.CopterMedium)..."
timeout 300 Tools/autotest/autotest.py \
    --no-clean \
    --speedup="${SPEEDUP}" \
    build.Copter \
    test.CopterMedium
echo "Medium autotest passed."

# Step 4: Pixhawk6C クリーンビルド
echo ""
echo "[4/4] Building Pixhawk6C (clean build)..."
./build_pixhawk6c.sh
echo "Pixhawk6C build complete."

echo ""
echo "=========================================="
echo " AP_Observer CI Pipeline COMPLETE"
echo "=========================================="
