# ArduPilot Custom Observer - Development Instructions

## Quick Start

1. **Make code changes** to `libraries/AP_Observer/` or `ArduCopter/`

2. **Run the "Build & Mandatory Tests" skill**
   - Open VS Code Command Palette (Ctrl+Shift+P / Cmd+Shift+P)
   - Type: **"Build & Mandatory Tests (SITL)"**
   - The skill will handle venv activation, build, and all mandatory SITL tests
   - ✅ All tests MUST PASS before hardware build

3. **Run replay validation** (if frequency estimation logic changed)
   - Open VS Code Command Palette
   - Type: **"RLS CSV Replay & Analysis"**
   - Verify convergence in `analysis/replay/results/`

4. **Document changes** in `CHANGELOG_DEVELOPMENT.md` with format:
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
- Record in `.github/CHANGELOG_DEVELOPMENT.md` (MANDATORY)
- Include failed attempts to prevent repeating mistakes
- Update after: code changes, bug fixes, tests, problem-solving

### 3. ALWAYS Use Clean Build for Hardware
- Use the **"Clean Build for Pixhawk6C Hardware"** skill (in VS Code Command Palette)
- This skill automatically:
  - Removes build cache
  - Configures for Pixhawk6C
  - Performs clean hardware build
- ⚠️  Only run this after all Phase 1 SITL tests PASS

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

## Available Skills

Three automated skills are available in VS Code Command Palette (Ctrl+Shift+P):

| Skill Name | Purpose | When to Use |
|-----------|---------|-------------|
| **Build & Mandatory Tests (SITL)** | Activate venv → Build → Run all mandatory SITL tests | After ANY code change to AP_Observer |
| **RLS CSV Replay & Analysis** | Build replay tool → Run simulation → Generate graphs | After frequency estimation logic changes |
| **Clean Build for Pixhawk6C Hardware** | Remove build cache → Configure board → Build hardware firmware | Only after Phase 1 tests PASS |

---

## Development Phases

### Phase 1: SITL Development (MANDATORY)
1. **Modify code** in `libraries/AP_Observer/` or `ArduCopter/`
2. **Run "Build & Mandatory Tests (SITL)" skill** (tests must PASS)
3. **Run "RLS CSV Replay & Analysis" skill** (if frequency estimation changed)
4. **Document in CHANGELOG_DEVELOPMENT.md** (mandatory after any change)

### Phase 2: Hardware Build (Pixhawk6C)
- ✅ Only after Phase 1 tests PASS
- Use **"Clean Build for Pixhawk6C Hardware"** skill (fully automated)

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
- Use the **"Build & Mandatory Tests (SITL)"** skill after ANY code change
- Run **"RLS CSV Replay & Analysis"** skill when frequency estimation logic changes
- Document in CHANGELOG_DEVELOPMENT.md (MANDATORY)
- Use **"Clean Build for Pixhawk6C Hardware"** skill only after Phase 1 tests PASS

❌ **NEVER**
- Skip Phase 1 tests
- Deploy to hardware without SITL validation
- Use dynamic memory allocation in embedded code
- Forget to document changes
- Manual build/test when skill automation is available

---

*Last updated: 2026-02-12*
