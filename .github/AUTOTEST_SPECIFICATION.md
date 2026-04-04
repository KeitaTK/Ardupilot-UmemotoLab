# ArduPilot Custom Autotest Specification (Observer RLS->EKF Migration)

## Mandatory Tests

All code changes affecting AP_Observer must pass these tests.

During EKF migration, the following tests are kept as regression guards for current behavior.

| Test | Purpose | Timeout | Freq |
|------|---------|---------|------|
| `test.Copter.ArmFeatures` | Core ArduPilot arming | 300s | Every change |
| `test.Copter.TestRLSBasicEstimation` | Baseline harmonic estimation regression | 600s | Every AP_Observer change |
| `test.Copter.TestRLSRC8SwitchControl` | RC Aux Function (RC8_OPTION=316) control | 600s | After RC/integration changes |
| `test.Copter.TestRLSWindowedEstimation` | RC-gated frequency estimation regression | 600s | After frequency estimation changes |
| `RLS_CSV_Replay (Simulation)` | Offline replay of flight data | ~30s | After frequency estimation code changes |

---

## Log Simulation & Offline Analysis

When modifying observer estimation logic (RLS or EKF path), you **MUST** run the offline simulation to verify convergence and stability using real flight data.

During EKF migration, replay analysis must additionally evaluate:

- frequency trajectory (`f_est`) against baseline replay results
- disturbance reconstruction quality (NRMSE)
- innovation trend (mean and lag-1 correlation)

### 1. Build & Run Replay
```bash
# Build the replay example
./waf build --target examples/RLS_CSV_Replay

# Run simulation from BIN directly (single-input mode)
./build/sitl/examples/RLS_CSV_Replay --input analysis/replay/data/00000444.BIN --plot
```

### 2. Generate Comparison Graph
```bash
# Optional standalone plotting from replay output CSV
python3 analysis/replay/plot_replay_results.py \
  --input analysis/replay/results/runs/00000444/00000444_bin_result.csv \
  --outdir analysis/replay/results/runs/00000444/plots \
  --title 00000444
```

### 3. Analyze SITL/Flight BIN Logs
If you have a `.BIN` log from SITL or flight:
```bash
# Replay can now read BIN directly and emit plots in one run:
./build/sitl/examples/RLS_CSV_Replay --input path/to/log.BIN --plot
# Output: analysis/replay/results/runs/<tag>/
#   - *_from_bin.csv
#   - *_result.csv
#   - plots/frequency_transition.png
#   - plots/waveform_compare_x.png
```

---

## Extended / Long Tests

These tests are experimental or require long execution time:

| Test | Purpose | Timeout | Notes |
|------|---------|---------|-------|
| `test.Copter.TestRLSFrequencyEstimation` | Zero-cross estimation with injected force | 800s | Timing-sensitive, may timeout |
| `test.Copter.TestRLSFrequencyEstimationMulti` | Multi-scenario zero-cross convergence | 1200s | 20+ min execution, before releases only |

---

## Quick Test Command

```bash
cd /home/memoto/Ardupilot-UmemotoLab
source venv/bin/activate
./waf -j$(nproc) copter
timeout 300 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.ArmFeatures || exit 1
timeout 600 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.TestRLSBasicEstimation || exit 1
timeout 600 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.TestRLSRC8SwitchControl || exit 1
timeout 600 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.TestRLSWindowedEstimation || exit 1
```

---

## Test Details

### test.Copter.ArmFeatures
- **Category**: Core ArduPilot functionality
- **Run frequency**: Every code change
- **Success criteria**: Vehicle arms correctly

### test.Copter.TestRLSBasicEstimation
- **Category**: AP_Observer core functionality
- **Parameters**: 
  - Test frequency: 0.6 Hz
  - Test amplitude: 10.0 N
  - Zero-cross window: 10s (RC8 OFF during test)
  - Test force injection: ON
- **Success criteria**: RLS accurately estimates known disturbance
- **Run frequency**: Every AP_Observer change

### test.Copter.TestRLSRC8SwitchControl
  - RC channel: RC8
  - RC8_OPTION: 316 (RLS_FREQ_EST)
  - OBS_FREQ_WIN: 10s
  - Switch logic: HIGH = ON, LOW = OFF

---

## Test Failure Debugging

| Failure | Cause | Solution |
|---------|-------|----------|
| ArmFeatures timeout | SITL startup issue | Reboot SITL, check resources |
| TestRLSBasicEstimation fails | Estimation not converging | Increase hover time, check RLS parameters |
| TestRLSRC8SwitchControl fails | RC Aux Function misconfigured | Verify RC8_OPTION=316 is set |

---

## Development Workflow Integration

### Phase 1: SITL Development (MANDATORY)
1. Make code changes
2. Build: `./waf copter`
3. **Run ALL mandatory tests**
4. If tests fail → Debug and repeat
5. **Do NOT proceed to Phase 2 until all tests pass**

### EKF Migration Validation (Required when EKF logic changes)
1. Run all mandatory regression tests above
2. Run replay simulation and graph generation
3. Compare EKF-side estimates to RLS baseline and MATLAB reference behavior
4. Record convergence/stability observations in `.github/CHANGELOG_DEVELOPMENT.md`

### Phase 2: Hardware Build (Pixhawk6C)
- Only after Phase 1 tests PASS
- Clean build: `rm -rf build/ && ./waf configure --board Pixhawk6C && ./waf copter`

---

## Test Execution Time

- **Mandatory tests**: ~10 minutes total
- **With optional tests**: 30+ minutes
- **TestRLSFrequencyEstimationMulti alone**: 20+ minutes

---

## Last Updated
- **Date**: 2026-04-04
- **Author**: Development team
