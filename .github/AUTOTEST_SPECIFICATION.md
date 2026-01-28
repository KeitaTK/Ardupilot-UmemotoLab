# ArduPilot Custom Autotest Specification

## Mandatory Tests

All code changes affecting AP_Observer must pass these tests:

| Test | Purpose | Timeout | Freq |
|------|---------|---------|------|
| `test.Copter.ArmFeatures` | Core ArduPilot arming | 300s | Every change |
| `test.Copter.TestRLSBasicEstimation` | RLS estimation with known frequency | 600s | Every AP_Observer change |
| `test.Copter.TestRLSRC8SwitchControl` | RC Aux Function (RC8_OPTION=316) control | 600s | After RC/integration changes |
| `RLS_CSV_Replay (Simulation)` | Offline replay of flight data | ~30s | After frequency estimation code changes |

---

## Log Simulation & Offline Analysis

When modifying frequency estimation logic, you **MUST** run the offline simulation to verify convergence and stability using real flight data.

### 1. Build & Run Replay
```bash
# Build the replay example
./waf examples --targets=RLS_CSV_Replay
# Run simulation (Input: analysis/replay/data/replay_data.csv)
./build/sitl/libraries/AP_Observer/examples/RLS_CSV_Replay
```

### 2. Generate Comparison Graph
```bash
# Generate PNG (Output: analysis/replay/results/rls_freq_compare.png)
python3 analysis/scripts/plot_rls_freq_compare.py
```

### 3. Analyze SITL/Flight BIN Logs
If you have a `.BIN` log from SITL or flight:
```bash
# Convert BIN to CSV using MAVExplorer or Mavlink tools, then:
python3 analysis/scripts/analyze_log.py path/to/log.csv
# Output: analysis/results/log_analysis.png
```

---

## Mandatory Tests

These tests are experimental or require long execution time:

| Test | Purpose | Timeout | Notes |
|------|---------|---------|-------|
| `test.Copter.TestRLSFrequencyEstimation` | Frequency estimation with phase correction | 800s | Timing-sensitive, may timeout |
| `test.Copter.TestRLSFrequencyEstimationMulti` | Multi-scenario frequency convergence | 1200s | 20+ min execution, before releases only |
| `test.Copter.TestRLSWindowedEstimation` | Time-windowed frequency estimation | 600s | Specific use case |

---

## Quick Test Command

```bash
cd /home/memoto/Ardupilot-UmemotoLab
source venv_ardupilot/bin/activate
./waf -j$(nproc) copter
timeout 300 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.ArmFeatures || exit 1
timeout 600 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.TestRLSBasicEstimation || exit 1
timeout 600 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.TestRLSRC8SwitchControl || exit 1
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
  - Phase correction: OFF
  - Test force injection: ON
- **Success criteria**: RLS accurately estimates known disturbance
- **Run frequency**: Every AP_Observer change

### test.Copter.TestRLSRC8SwitchControl
- **Category**: AP_Observer UI control
- **Parameters**:
  - RC channel: RC8
  - RC8_OPTION: 316 (RLS_FREQ_EST)
  - Switch logic: HIGH = ON, LOW = OFF
- **Success criteria**: Frequency estimation toggles correctly
- **Run frequency**: After RC control or integration changes

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
- **Date**: 2026-01-28
- **Author**: Development team
