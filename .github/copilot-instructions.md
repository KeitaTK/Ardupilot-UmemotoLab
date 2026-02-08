# ArduPilot Custom Observer - Development Instructions

## Quick Start

1. **Activate environment** (every session)
   - Always use the existing virtual environment `venv_ardupilot`.
   - Do NOT create a new virtual environment.
   ```bash
   cd /home/memoto/Ardupilot-UmemotoLab
   source venv_ardupilot/bin/activate
   ```

2. **Make code changes** to `libraries/AP_Observer/` or `ArduCopter/`

3. **Build and test**
   ```bash
   ./waf -j$(nproc) copter
   timeout 300 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.ArmFeatures || exit 1
   timeout 600 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.TestRLSBasicEstimation || exit 1
   ```

4. **Document** in `CHANGELOG_DEVELOPMENT.md` with format:
   - If needed, you may refer to `CHANGELOG_DEVELOPMENT.md` to search for past cases and examples.
   ```
   ### YYYY-MM-DD: [Component]
   - Problem: [Issue]
   - Investigation: [Root cause]
   - Attempted: [What was tried]
   - Result: [Outcome]
   ```

---

## Mandatory Rules

### 1. ALWAYS Test Before Hardware
- Run ALL mandatory tests after ANY change to AP_Observer
- Tests must PASS before Pixhawk6C build (Phase 2)
- See `.github/AUTOTEST_SPECIFICATION.md` for test details

### 2. ALWAYS Document Changes
- Record in `CHANGELOG_DEVELOPMENT.md` (MANDATORY)
- Include failed attempts to prevent repeating mistakes
- Update after: code changes, bug fixes, tests, problem-solving

### 3. ALWAYS Use Clean Build for Hardware
```bash
rm -rf build/
./waf configure --board Pixhawk6C
./waf -j$(nproc) copter
```

---

## Project-Specific Rules

### AP_Observer Library (`libraries/AP_Observer/`)
- **Coding style**: C++11, embedded-friendly
- **Memory**: NO dynamic allocation (use stack arrays)
- **Logging**: 4-char label max, 2-3 char field names
- **Debug**: Use `gcs().send_text()` for messages, `AP_Logger::Write()` for logs

### ArduPilot Coding Standards
- **Headers**: `#pragma once` (not include guards)
- **Naming**: `AP_` prefix for classes, `UPPER_SNAKE_CASE` for constants
- **Includes**: Standard libs → ArduPilot libs → Local headers
- **Error handling**: Always check pointers for nullptr
- **Comments**: Explain algorithm intent, specify units `[rad/s]`, `[Hz]`, `[N]`

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Test fails with "label too long" | Log label > 4 chars | Shorten field names |
| Compiler error "unused variable" | Unused variable defined | Remove or use `(void)var;` |
| Phase correction = 0 | Wrong phase buffer | Use `ab_phase_unwrapped[0]` |

---

## RC Frequency Estimation Control

**Recommended**: RC Aux Function (RC8_OPTION=316)
- PWM > center: Estimation ON
- PWM < center: Estimation OFF
- Verification: GCS message `RLS Freq Est: ON/OFF`, log field `OBSV.SW` (1=ON, 0=OFF)

---

## Development Phases

### Phase 1: SITL Development (MANDATORY)
1. Modify code
2. Build: `./waf copter`
3. Run mandatory tests (must PASS)
4. Document in CHANGELOG_DEVELOPMENT.md

### Phase 2: Hardware Build (Pixhawk6C)
- Only after Phase 1 tests PASS
- Clean build recommended: `rm -rf build/`

---

## Key Directories
```
├── libraries/AP_Observer/     # Custom observer library
├── ArduCopter/               # Main copter code
├── Tools/autotest/           # Autotest scripts
└── logs/                     # Log output
```

---


## References

- **Autotest Specs**: `.github/AUTOTEST_SPECIFICATION.md`
- **Development History**: `CHANGELOG_DEVELOPMENT.md` (You may search this file for past cases if needed)
- **ArduPilot Docs**: https://ardupilot.org/dev/

---

## Summary

✅ **ALWAYS**
- Activate venv before building
- Run mandatory tests after changes
- Document in CHANGELOG_DEVELOPMENT.md
- Use clean build for hardware

❌ **NEVER**
- Skip Phase 1 tests
- Deploy to hardware without SITL validation
- Use dynamic memory allocation in embedded code
- Forget to document changes

---

*Last updated: 2026-01-28*
