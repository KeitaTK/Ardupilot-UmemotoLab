#!/bin/bash
# Example: Restore modules/mavlink and verify build

set -e

cd /home/memoto/Ardupilot-UmemotoLab

echo "=== Checking if modules/mavlink restoration is needed ==="
if [ ! -d "modules/mavlink" ] && [ -d ".git/modules/modules/mavlink" ]; then
    echo "Restoring modules/mavlink from Git metadata..."
    mkdir -p modules/mavlink
    git --git-dir=.git/modules/modules/mavlink -c core.worktree=$(pwd)/modules/mavlink checkout -f
    echo "✓ Restoration complete"
else
    echo "✓ modules/mavlink already exists or restoration not needed"
fi

echo ""
echo "=== Building for Pixhawk6C with MAVLink fix ==="
source venv/bin/activate
./waf distclean
./waf configure --board Pixhawk6C
./waf copter

echo ""
echo "=== Verifying build artifacts ==="
for artifact in build/Pixhawk6C/bin/arducopter build/Pixhawk6C/bin/arducopter.apj build/Pixhawk6C/bin/arducopter.bin; do
    if [ -f "$artifact" ]; then
        echo "✓ $artifact"
    else
        echo "✗ $artifact NOT FOUND"
        exit 1
    fi
done

echo ""
echo "✅ Build successful! MAVLink fix verified."
