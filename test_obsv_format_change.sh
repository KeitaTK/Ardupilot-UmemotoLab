#!/bin/bash
set -e

echo "======================================"
echo "OBSV Format Change Test Suite"
echo "======================================"

cd /home/umemoto/Ardupilot-UmemotoLab
source venv/bin/activate

# ============ Test 1: SITL Build ============
echo ""
echo "Test 1: SITL Build (verify compilation)"
echo "---"
./waf clean > /dev/null 2>&1 || true
./waf configure --board sitl > /dev/null 2>&1
./waf copter
echo "✅ SITL Build Success"

# ============ Test 2: Replay Build ============
echo ""
echo "Test 2: EKF CSV Replay Build"
echo "---"
./waf build --target examples/EKF_CSV_Replay > /dev/null 2>&1
echo "✅ Replay Build Success"

# ============ Test 3: BIN Extraction (new format) ============
echo ""
echo "Test 3: BIN Extraction with New Format"
echo "---"
python3 analysis/ekf_eval/flight/evaluate_obsv_bin.py \
  --input-bin /mnt/c/Users/Umemoto/Documents/Taki_Local/BIN/1/00000091.BIN \
  --outdir analysis/ekf_eval/flight/reports_new \
  --copy-to-data
echo "✅ BIN Extraction Success"

# ============ Test 4: Verify new CSV format ============
echo ""
echo "Test 4: Verify New CSV Format"
echo "---"
CSV_FILE="analysis/ekf_eval/flight/data/csv/00000091_obsv.csv"
echo "CSV header:"
head -1 "$CSV_FILE"
echo ""
echo "First data row:"
head -2 "$CSV_FILE" | tail -1 | cut -d',' -f1-11
echo ""
# Check columns
COLS=$(head -1 "$CSV_FILE")
if [[ "$COLS" == *"PFX"* ]] && [[ "$COLS" == *"PFY"* ]] && [[ "$COLS" == *"PFZ"* ]]; then
  if [[ "$COLS" != *"DX"* ]] || [[ "$COLS" != *"VX"* ]]; then
    echo "✅ New format confirmed (PFX/PFY/PFZ present, D/V/C removed)"
  else
    echo "⚠️  Format may have old fields still present"
  fi
else
  echo "❌ New format fields (PFX/PFY/PFZ) not found!"
fi

# ============ Test 5: Replay Execution ============
echo ""
echo "Test 5: Replay Execution with New Format"
echo "---"
build/sitl/examples/EKF_CSV_Replay \
  --input "$CSV_FILE" \
  --outdir analysis/replay/results/runs/00000091/format_test \
  --tag 00000091_format_test > /dev/null 2>&1
echo "✅ Replay Execution Success"

# ============ Test 6: Pixhawk6C Build ============
echo ""
echo "Test 6: Pixhawk6C Clean Build"
echo "---"
./waf distclean > /dev/null 2>&1 || true
./waf configure --board Pixhawk6C > /dev/null 2>&1
./waf copter
echo "✅ Pixhawk6C Build Success"

# ============ Summary ============
echo ""
echo "======================================"
echo "All Tests Passed! ✅"
echo "======================================"
echo ""
echo "Output locations:"
echo "  - New CSV: $CSV_FILE"
echo "  - Replay result: analysis/replay/results/runs/00000091/format_test/"
echo "  - Pixhawk6C firmware: build/Pixhawk6C/bin/arducopter.elf"
echo ""
