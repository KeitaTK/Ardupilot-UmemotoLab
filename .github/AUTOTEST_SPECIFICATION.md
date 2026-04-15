# ArduPilot Custom Autotest Specification (Observer EKF Fixed Policy)

## Mandatory SITL Tests

All code changes affecting AP_Observer, ArduCopter integration, or RC-based switching must pass these tests.

| Test | Purpose | Timeout | Freq |
|------|---------|---------|------|
| `test.Copter.ArmFeatures` | Core arming and safety path | 300s | Every change |
| `test.Copter.ModeLoiter` | Loiter mode behavior regression | 300s | Every AP_Observer change |
| `test.Copter.GCSFailsafe` | GCS link loss failsafe behavior | 300s | Every AP_Observer change |
| `test.Copter.GuidedSubModeChange` | Guided sub-mode transition safety | 300s | Integration changes / pre-release |
| `test.Copter.TakeoffCheck` | Takeoff gate and safety checks | 300s | Integration changes / pre-release |
| `EKF_CSV_Replay` | Offline replay convergence check | ~30s | After observer estimation changes |

---

## Legacy Test Status

Legacy injected-force observer autotests (`TestRLS*`) are no longer part of default Copter suites under the EKF-fixed policy.
These tests depended on removed parameters (for example `OBS_TEST_*`, `OBS_PHASE_*`, `OBS_FREQ_WIN`) and are retained only as historical references in source code.

---

## Log Replay and Offline Analysis

When modifying observer estimation logic, you MUST run offline replay for convergence/stability checks.

### 1. Build and Run Replay

```bash
./waf build --target examples/EKF_CSV_Replay
./build/sitl/examples/EKF_CSV_Replay --input analysis/replay/data/00000444.BIN --plot
```

### 2. Generate Plots from Existing Replay Output (Optional)

```bash
python3 analysis/replay/plot_replay_results.py \
  --input analysis/replay/results/runs/00000444/00000444_bin_result.csv \
  --outdir analysis/replay/results/runs/00000444/plots \
  --title 00000444
```

### 3. Analyze Any SITL/Flight BIN

```bash
./build/sitl/examples/EKF_CSV_Replay --input path/to/log.BIN --plot
```

Expected output directory:

- `analysis/replay/results/runs/<tag>/`
- `*_from_bin.csv`
- `*_result.csv`
- `plots/frequency_transition.png`
- `plots/waveform_compare_x.png`

---

## Quick Mandatory Test Command Sequence

```bash
cd /home/memoto/Ardupilot-UmemotoLab
source venv/bin/activate
./waf clean
./waf configure --board sitl
./waf -j$(nproc) copter
timeout 300 Tools/autotest/autotest.py --no-clean --speedup=300 build.Copter test.Copter.ModeLoiter || exit 1
timeout 300 Tools/autotest/autotest.py --no-clean --speedup=300 build.Copter test.Copter.GCSFailsafe || exit 1
timeout 300 Tools/autotest/autotest.py --no-clean --speedup=300 build.Copter test.Copter.GuidedSubModeChange || exit 1
timeout 300 Tools/autotest/autotest.py --no-clean --speedup=300 build.Copter test.Copter.TakeoffCheck || exit 1
timeout 300 Tools/autotest/autotest.py --no-clean --speedup=300 build.Copter test.Copter.ArmFeatures || exit 1
```

---

## Test Details

### test.Copter.ArmFeatures

- Category: Core ArduPilot functionality
- Success criteria: Vehicle arms/disarms with expected gating behavior

### test.Copter.ModeLoiter

- Category: Flight mode regression
- Success criteria: Loiter mode remains stable and command transitions are valid

### test.Copter.GCSFailsafe

- Category: Communication failsafe
- Success criteria: Correct failsafe behavior when GCS link is lost/restored

### test.Copter.GuidedSubModeChange

- Category: Guided mode transitions
- Success criteria: Sub-mode transitions occur without unexpected disarm/crash states

### test.Copter.TakeoffCheck

- Category: Takeoff safety
- Success criteria: Takeoff checks and mode interactions behave as expected

---

## Test Failure Debugging

| Failure | Likely Cause | Suggested Action |
|---------|--------------|------------------|
| `ModeLoiter` timeout | SITL startup/config mismatch | Re-run from clean configure/build sequence |
| `GCSFailsafe` failure | Link/failsafe parameter drift | Verify failsafe params and expected mode transitions |
| `GuidedSubModeChange` failure | Guided transition regression | Inspect mode switch and state machine logs |
| `TakeoffCheck` failure | Pre-arm/takeoff gating regression | Check pre-arm status and takeoff condition changes |
| `ArmFeatures` failure | Core arming regression | Validate arming checks and RC defaults |

---

## Development Workflow Integration

### Phase 1: SITL Development (Mandatory)

1. Make code changes.
2. Build (`./waf configure --board sitl` and `./waf copter`).
3. Run all mandatory SITL tests above.
4. If any test fails, debug and rerun until all pass.
5. Do not proceed to hardware build until Phase 1 is green.

### EKF Validation (Required When Estimation Logic Changes)

1. Run all mandatory SITL tests.
2. Run replay simulation and generate plots.
3. Compare EKF behavior with recent EKF baseline results and MATLAB reference trends.
4. Record results in `.github/CHANGELOG_DEVELOPMENT.md`.

### Phase 2: Hardware Build (Pixhawk6C)

- Run only after all mandatory SITL tests pass.
- Clean build command: `rm -rf build/ && ./waf configure --board Pixhawk6C && ./waf copter`

---

## Test Execution Time (Reference)

- Mandatory SITL tests: about 10 to 20 minutes depending on host performance
- Replay validation: about 5 to 10 minutes

---

## Last Updated

- Date: 2026-04-15
- Author: Development team