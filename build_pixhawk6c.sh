#!/bin/bash
# Pixhawk6C Hardware Build Script
# Always performs clean build with full log output

set -e

cd "$(dirname "$0")"

echo "=========================================="
echo "Pixhawk6C Hardware Build (Clean)"
echo "=========================================="

# Activate virtual environment
source venv/bin/activate

# Display environment info
echo ""
echo "Python version: $(python3 --version)"
echo "WAF version: $(./waf --version 2>&1 | head -1)"
echo ""

# Step 1: Clean all previous build artifacts
echo "[1/4] Cleaning previous build artifacts..."
./waf distclean

# Step 2: Configure for Pixhawk6C
echo ""
echo "[2/4] Configuring for Pixhawk6C board..."
./waf configure --board Pixhawk6C

# Step 3: Build ArduCopter
echo ""
echo "[3/4] Building ArduCopter firmware..."
./waf copter

# Step 4: Verify build artifacts
echo ""
echo "[4/4] Verifying build artifacts..."
if [ -f build/Pixhawk6C/bin/arducopter.bin ] && [ -f build/Pixhawk6C/bin/arducopter.apj ]; then
    ls -lh build/Pixhawk6C/bin/arducopter.*
    echo ""
    echo "=========================================="
    echo "✅ Build successful!"
    echo "=========================================="
    echo "Firmware: build/Pixhawk6C/bin/arducopter.bin"
    echo "APJ:      build/Pixhawk6C/bin/arducopter.apj"
    echo ""
    exit 0
else
    echo "❌ Build failed - artifacts not found"
    exit 1
fi
