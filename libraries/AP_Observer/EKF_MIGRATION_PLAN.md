# AP_Observer EKF Migration Plan (RLS_only Base)

## 1. Scope

This document compares:

- Current in-firmware implementation: `libraries/AP_Observer/AP_Observer.cpp` + `libraries/AP_Observer/AP_Observer.h`
- MATLAB EKF reference: `C:\Users\Umemoto\Documents\Taki_Local\Matlab\EKF`

Objective:

- Replace the current RLS-based harmonic estimator with a harmonic-model EKF while keeping existing AP_Observer integration points and safety behavior.

## 2. Current Program vs MATLAB EKF

### 2.1 State and Model Structure

- Current AP_Observer:
  - Uses 3-axis independent RLS parameter vectors `theta=[A,B,C]`
  - Harmonic basis uses explicit phase (`sin(omega*t)`, `cos(omega*t)`)
  - Frequency management is external to state (`estimated_frequency` + zero-cross window)
- MATLAB EKF reference (`docs/02_ekf_design_math.md`, `scripts/ekf_harmonic_step.m`):
  - Uses EKF state `x=[d, d_dot, c, omega]^T`
  - Nonlinear process model with `omega` as state
  - Measurement model `y=d+c+v`

### 2.2 Frequency Estimation Strategy

- Current AP_Observer:
  - Frequency estimated by zero-crossing window (`FREQ_WIN`) gated by RC8 switch
  - Estimated frequency then drives harmonic RLS basis
- MATLAB EKF:
  - Frequency (omega) is continuously estimated in the filter state
  - No separate zero-cross observer is required in core algorithm

### 2.3 Covariance and Tuning Parameters

- Current AP_Observer:
  - `RLS_LAMBDA`, `RLS_COV_INIT`
  - Deterministic parameter adaptation + covariance recursion in RLS form
- MATLAB EKF:
  - `Q` and `R` are primary tuning parameters
  - `omega` random-walk process noise (`q_omega`) is key for responsiveness/stability tradeoff

### 2.4 Prediction Output

- Current AP_Observer:
  - Predicts force at `t + PRED_TIME` from `A,B,C`
- EKF target:
  - Keep same public behavior (`get_predicted_force()` and correction outputs)
  - Internally compute predicted disturbance from EKF state propagation

## 3. File-Level Change Targets (Detailed)

## 3.1 `libraries/AP_Observer/AP_Observer.h`

Required changes:

- Replace or isolate RLS-specific members:
  - `rls_theta`, `rls_P`, `RLS_PARAM_SIZE`, `RLS_NUM_AXES`
  - `rls_init()`, `rls_update(...)`, RLS getters naming
- Introduce EKF state and covariance structures per axis:
  - Example state: `[d, d_dot, c, omega]`
  - Example covariance: `4x4` per axis
- Introduce EKF tunable parameters via `AP_Param`:
  - `EKF_Q_D`, `EKF_Q_DDOT`, `EKF_Q_C`, `EKF_Q_OMEGA`, `EKF_R_MEAS`
  - `EKF_OMEGA_INIT` (or initialize from existing `DIST_FREQ`)
  - `EKF_OMEGA_MIN`, `EKF_OMEGA_MAX`
- Keep existing integration API stable where possible:
  - `update()`, `get_predicted_force()`, correction getters

Compatibility note:

- Keep existing externally consumed methods temporarily (or provide compatibility wrappers) to avoid immediate breaks in logs/tests.

## 3.2 `libraries/AP_Observer/AP_Observer.cpp`

Required changes:

- Parameter table (`var_info`) update:
  - Deprecate RLS-only parameters in staged manner
  - Add EKF parameters with ranges/defaults aligned to MATLAB tuning
- Replace core update path:
  - Current: `rls_update(...)` + zero-cross frequency update
  - Target: `ekf_update_axis(...)` (per axis) with nonlinear prediction and measurement update
- Frequency handling:
  - Move from zero-cross as primary estimator to EKF omega state
  - RC8 switch semantics decision (must be documented):
    - Option A: switch controls EKF omega adaptation ON/OFF
    - Option B: switch controls entire EKF update ON/OFF
- Prediction:
  - Use EKF state transition to predict at `t + PRED_TIME`
  - Preserve correction pipeline behavior and safety clamping
- Logging:
  - Add EKF-focused fields (state/cov/frequency confidence)
  - Keep existing OBSV essentials for backward compatibility during migration

## 3.3 `libraries/AP_Observer/README.md`

Required changes:

- Replace algorithm section from RLS equations to EKF equations
- Add migration status and compatibility section
- Update parameter table to EKF tuning parameters
- Update logs section with EKF state fields and meaning

## 3.4 `.github/AUTOTEST_SPECIFICATION.md`

Required changes:

- Keep existing mandatory tests for regression during transition
- Add EKF migration validation block:
  - EKF convergence (frequency/offset/state)
  - Initial frequency mismatch robustness
  - High-frequency interference robustness
- Clarify replay/analysis requirement for every EKF core change

## 3.5 `.github/copilot-instructions.md` and `.github/skills/*.yaml`

Required changes:

- Update wording from "RLS-only" to "Observer estimation (RLS/EKF migration)"
- Add mandatory MATLAB EKF comparison workflow after observer algorithm changes
- Keep command examples valid for current repo tools and paths

## 3.6 `.github/CHANGELOG_DEVELOPMENT.md`

Required changes:

- Record migration planning and document updates immediately
- Continue logging failed attempts and tuning findings during implementation

## 4. Behavior Mapping (Current -> EKF)

- Current `DIST_FREQ` initialization -> EKF `omega_init`
- Current `FREQ_WIN` zero-cross window -> optional fallback/diagnostic only
- Current `RLS_LAMBDA`, `RLS_COV_INIT` -> EKF `Q`/`R` and `P0`
- Current `A,B,C` logs -> EKF `d,d_dot,c` (+ derived amplitude/phase if needed)

## 5. Risks and Countermeasures

- Risk: Observability loss when disturbance amplitude is very small
  - Mitigation: gate omega adaptation by amplitude/innovation quality, clamp omega range
- Risk: Numerical instability on embedded target
  - Mitigation: bounded covariances, symmetric covariance enforcement, finite checks
- Risk: Test breakage due to renamed log/params
  - Mitigation: staged compatibility layer, update tests and docs together

## 6. Incremental Implementation Plan

1. Introduce EKF data structures/params behind feature flag (no behavior change)
2. Add offline replay comparison path (RLS vs EKF outputs side-by-side)
3. Enable EKF in SITL only, keep RLS fallback
4. Migrate logs/tests to EKF canonical fields
5. Remove RLS core path after convergence/stability criteria pass

## 7. Acceptance Criteria (Documentation + Environment Stage)

- EKF migration plan documented with file-level tasks and risk controls
- Instructions/specs updated for EKF migration workflow
- Branch prepared from `RLS_only` locally and remotely for implementation
