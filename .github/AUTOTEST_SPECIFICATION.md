# ArduPilot Custom Autotest Specification

## Mandatory Tests

All code changes affecting AP_Observer must pass these tests:

| Test | Purpose | Timeout | Freq |
|------|---------|---------|------|
| `test.Copter.ArmFeatures` | Core ArduPilot arming | 300s | Every change |
| `test.Copter.TestRLSBasicEstimation` | RLS estimation with known frequency | 600s | Every AP_Observer change |

---

## Log Simulation & Offline Analysis



---

## Mandatory Tests

These tests are experimental or require long execution time:

| Test | Purpose | Timeout | Notes |
|------|---------|---------|-------|


---

## Quick Test Command

```bash
cd /home/memoto/Ardupilot-UmemotoLab
source venv_ardupilot/bin/activate
./waf -j$(nproc) copter
timeout 300 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.ArmFeatures || exit 1
timeout 600 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.TestRLSBasicEstimation || exit 1
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
