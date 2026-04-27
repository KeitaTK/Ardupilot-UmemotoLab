# ArduPilot Custom Observer - Development Instructions

## Virtual Environment Setup

**IMPORTANT**: Before running any tests or builds, activate the Python virtual environment:

```bash
source venv/bin/activate
```

This virtual environment includes all required dependencies (empy 3.3.4, MAVProxy, etc.) for ArduPilot development and testing.

---

## Quick Start

1. **Activate virtual environment** (required before any testing):
   ```bash
   source venv/bin/activate
   ```

2. **Make code changes** to `libraries/AP_Observer/` or `ArduCopter/`

3. **Run the "Build & Mandatory Tests" skill**
   - Make sure venv is activated first (see step 1)
   - Open VS Code Command Palette (Ctrl+Shift+P / Cmd+Shift+P)
   - Type: **"Build & Mandatory Tests (SITL)"**
   - The skill will build ArduCopter and run all mandatory SITL tests
   - ✅ All tests MUST PASS before hardware build

4. **Run replay validation** (if observer estimation logic changed)
   - Ensure venv is activated
   - Open VS Code Command Palette
   - Type: **"EKF CSV/BIN Replay & Analysis"**
   - Verify convergence in `analysis/replay/results/`

5. **Run MATLAB EKF reference comparison** (required during EKF migration)
   - Reference path: `C:\Users\Umemoto\Documents\Taki_Local\Matlab\EKF`
   - Confirm consistency for convergence trend, steady-state bias, and frequency estimate behavior

6. **Document changes** in `CHANGELOG_DEVELOPMENT.md` with format:
   - If needed, you may refer to `CHANGELOG_DEVELOPMENT.md` to search for past cases and examples.
   ```
   ### YYYY-MM-DD: [Component]
   - Problem: [Issue]
   - Investigation: [Root cause]
   - Attempted: [What was tried]
   - Result: [Outcome]
   ```

---

## Pre-Test Setup Sequence (Execute Before Running ANY Tests)

### Complete Command Sequence


#### 仮想環境の有効化状態の確認について

**必ずテストやビルドの前に、仮想環境(venv)が有効化されていることを確認してください。**
もし有効化されていない場合は、必ず `source venv/bin/activate` をコマンドの先頭に追加してください。
スクリプトや自動化コマンドでは、常に仮想環境の有効化コマンドを明示的に含めることを推奨します。
（すでに有効化済みの場合は、再度有効化しても問題ありません）

---

Always execute these commands in order **every time** before running any autotest:

```bash
# Step 1: Navigate to workspace directory
cd ~/Ardupilot-UmemotoLab

# Step 2: Activate the Python virtual environment (MANDATORY)
source venv/bin/activate

# Step 3: Clean any previous build artifacts
./waf clean

# Step 4: Configure for SITL (software-in-the-loop simulator)
./waf configure --board sitl

# Step 5: Build ArduCopter
./waf copter

# Step 6: You are now ready to run any mandatory autotest
# (Proceed to the test execution section below)
```

**⚠️ CRITICAL**: Never skip the venv activation in Step 2. All subsequent commands depend on it.

---

## Mandatory Rules

### 1. ALWAYS Test Before Hardware
- Activate venv first: `source venv/bin/activate`
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

## RC Frequency Estimation Control (Migration Policy)

**Recommended**: RC Aux Function (RC8_OPTION=316)
- PWM > center: Estimation ON
- PWM < center: Estimation OFF
- Verification (current): GCS message `RLS Freq Est: ON/OFF`, log field `OBSV.SW` (1=ON, 0=OFF)
- Verification (after EKF switch): equivalent EKF estimation ON/OFF telemetry must be provided

---

## Available Skills

Three automated skills are available in VS Code Command Palette (Ctrl+Shift+P):

### 1. Build & Mandatory Tests (SITL)

**Purpose**: Full build and SITL test automation

**Commands executed by this skill**:
```bash
# Activate venv
source venv/bin/activate

# Clean and configure
./waf clean
./waf configure --board sitl

# Build
./waf copter

# Run all mandatory SITL tests
timeout 300 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.ModeLoiter || exit 1
timeout 300 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.GCSFailsafe || exit 1
timeout 300 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.GuidedSubModeChange || exit 1
timeout 300 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.TakeoffCheck || exit 1
```

**When to use**: After ANY code change to AP_Observer or ArduCopter
**Expected time**: ~30-45 minutes
**Success criteria**: All 4 tests PASS ✅

---

### 2. EKF CSV/BIN Replay & Analysis (Baseline Replay)

**Purpose**: Validates frequency estimation logic with recorded flight data

**Commands executed by this skill**:
```bash
# Activate venv
source venv/bin/activate

# Build replay example
./waf build --target examples/EKF_CSV_Replay

# Run replay directly from BIN (or CSV)
./build/sitl/examples/EKF_CSV_Replay --input analysis/replay/data/00000444.BIN --plot

# Optional: regenerate plots from an existing replay result CSV
python3 analysis/replay/plot_replay_results.py \
   --input analysis/replay/results/runs/00000444/00000444_bin_result.csv \
   --outdir analysis/replay/results/runs/00000444/plots \
   --title 00000444
```

**When to use**: After any change to observer estimation algorithm (observer estimation path)
**Expected time**: ~5-10 minutes
**Output**: `analysis/replay/results/runs/<tag>/` with result CSV and plots

---

### 3. Clean Build for Pixhawk6C Hardware

**Purpose**: Complete hardware build with no artifacts

**Commands executed by this skill**:
```bash
# Activate venv
source venv/bin/activate

# Remove all build artifacts
./waf distclean

# Configure for Pixhawk6C
./waf configure --board Pixhawk6C

# Build firmware
./waf copter

# Binary location
# Output firmware: build/Pixhawk6C/bin/arducopter.elf
```

**⚠️ When to use**: ONLY after all Phase 1 SITL tests PASS
**Expected time**: ~20-30 minutes
**Result**: `build/Pixhawk6C/bin/arducopter.elf` (ready for upload)

---


## 必須オートテスト（通信・モード動作検証）


## テスト運用方針

### 日常的な開発・小規模な変更時
- **通信・モード系の動作確認のみで十分な場合は、以下の2テストのみを実行してください（高速化推奨）：**
   - `test.Copter.ModeLoiter` … Loiterモードの自動検証
   - `test.Copter.GCSFailsafe` … GCS通信フェイルセーフ検証

   **実行例（100倍速・ビルド再利用）：**
   ```bash
   cd ~/Ardupilot-UmemotoLab
   source venv/bin/activate
   ./waf configure --board sitl
   ./waf copter
   timeout 300 Tools/autotest/autotest.py --no-clean --speedup=300 build.Copter test.Copter.ModeLoiter || exit 1
   timeout 300 Tools/autotest/autotest.py --no-clean --speedup=300 build.Copter test.Copter.GCSFailsafe || exit 1
      timeout 300 Tools/autotest/autotest.py --no-clean --speedup=300 build.Copter test.Copter.ArmFeatures || exit 1
   ```

### 仕様追加・リリース前・重要な検証時
- **下記の全必須テストを必ず実行し、すべてパスすることを確認してください：**
   - `test.Copter.ModeLoiter`
   - `test.Copter.GCSFailsafe`
   - `test.Copter.GuidedSubModeChange`
   - `test.Copter.TakeoffCheck`

   **実行例：**
   ```bash
   cd ~/Ardupilot-UmemotoLab
   source venv/bin/activate
   ./waf configure --board sitl
   ./waf copter
   timeout 300 Tools/autotest/autotest.py --no-clean --speedup=300 build.Copter test.Copter.ModeLoiter || exit 1
   timeout 300 Tools/autotest/autotest.py --no-clean --speedup=300 build.Copter test.Copter.GCSFailsafe || exit 1
   timeout 300 Tools/autotest/autotest.py --no-clean --speedup=300 build.Copter test.Copter.GuidedSubModeChange || exit 1
   timeout 300 Tools/autotest/autotest.py --no-clean --speedup=300 build.Copter test.Copter.TakeoffCheck || exit 1
   timeout 300 Tools/autotest/autotest.py --no-clean --speedup=300 build.Copter test.Copter.ArmFeatures || exit 1
   ```

   または、VS Codeの「Build & Mandatory Tests (SITL)」スキルで全テストを自動実行してください。

**ワークフロー例：**
- 日常的な開発では通信系2テストのみでOK
- 重要な変更・リリース前は全必須テストを実施
- テスト失敗時は原因を調査し、`CHANGELOG_DEVELOPMENT.md`に記録
- テスト追加や仕様変更時は`.github/AUTOTEST_SPECIFICATION.md`も更新


### Phase 1: SITL Development (MANDATORY)
1. **Modify code** in `libraries/AP_Observer/` or `ArduCopter/`
2. **Run "Build & Mandatory Tests (SITL)" skill** (tests must PASS)
3. **Run "EKF CSV/BIN Replay & Analysis" skill** (if observer estimation changed)
4. **Compare with MATLAB EKF reference** (`C:\Users\Umemoto\Documents\Taki_Local\Matlab\EKF`) when EKF logic is touched
5. **Document in CHANGELOG_DEVELOPMENT.md** (mandatory after any change)

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
- Activate venv first: `source venv/bin/activate` (required before any testing)
- Use the **"Build & Mandatory Tests (SITL)"** skill after ANY code change
- Run **"EKF CSV/BIN Replay & Analysis"** skill when frequency estimation logic changes
- During EKF migration, compare replay behavior against MATLAB EKF reference workspace
- Document in CHANGELOG_DEVELOPMENT.md (MANDATORY)
- Use **"Clean Build for Pixhawk6C Hardware"** skill only after Phase 1 tests PASS

❌ **NEVER**
- Skip venv activation before running tests
- Skip Phase 1 tests
- Deploy to hardware without SITL validation
- Use dynamic memory allocation in embedded code
- Forget to document changes
- Manual build/test when skill automation is available

---

## EKF Tuning Policy (AP_Observer)

**Q/R Parameter Guidelines for Smooth Force Estimation (DX/DY)**:
- **Problem**: If `Q` (process noise) is too large (e.g. `0.01`) and `R` (measurement noise) is too small (e.g. `0.5`), the EKF will overfit to high-frequency sensor noise, resulting in jagged, noisy `DX`/`DY` outputs.
- **Solution**: To act as a strict narrow-bandpass filter, EKF process noise must be extremely small.
  - `OBS_EKF_Q_D` and `Q_DD` should be on the order of `1e-11` to `1e-12`.
  - `OBS_EKF_R_MEAS` should be large (e.g., `40.0` to `50.0`).
- **Axis Gating & Sharing**:
  - To prevent hysteresis (gating on/off chatter), set `OBS_EKF_EN_TAU` to a longer duration (e.g., `4.0s`).
  - Keep `OBS_EKF_SH_BETA` at `0.5` to allow axes (X/Y) to share frequency estimates and stabilize each other when one axis gates off.
  - Z-axis is currently excluded from fusion (`OBS_EKF_AX_MASK = 3`).

---

*Last updated: 2026-04-27*
