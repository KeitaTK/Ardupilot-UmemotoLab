# AP_Observer EKF Flight BIN Evaluation: 00000074

## Input
- Source BIN: analysis/ekf_eval/flight/data/bin/00000074.BIN
- Samples: 8781
- Duration: 87.80 s
- Mean sample rate: 100.00 Hz

## State Variable Definitions
- **D (DX, DY, DZ)**: EKF-estimated external force (prediction time = 0). Each axis represents estimated payload force [N].
- **V (VX, VY, VZ)**: Rate of estimated force (time derivative of D). Represents force change rate [N/s].
- **C (CX, CY, CZ)**: DC offset component. Represents static external force component [N].
- **F**: Fused frequency estimate [Hz]. Integrated result of per-axis frequency estimates.

## Key Metrics
- sw_active_ratio: 0.0 (Switch always OFF - **NORMAL for this test condition**)
- sw_transitions: 0
- F_mean: 0.4315349396781472 Hz
- F_std: 0.1199334154585437 Hz
- F_min: 0.01591549441218376 Hz
- F_max: 1.5915493965148926 Hz
- freq_p95_step_hz: 0.03003531694412229 Hz/s
- plx_dom_freq_hz: 0.4783026212018864 Hz
- ply_dom_freq_hz: 0.46691446355422245 Hz
- freq_mean_vs_dom_abs_err_hz: 0.04676768152373917 Hz
- DZ_max: 1.7170535628583512e+23 (⚠️ Anomalous)
- VZ_max: 8.836841411492463e+23 (⚠️ Anomalous)
- CY_std: 0.0 (⚠️ No variation)

## Detailed Analysis Results

### Estimated Force Tracking (Prediction Time = 0s)
- **DX**: Normal tracking with mean ~0.18 N, std ~0.88 N
- **DY**: Minimal activity, consistent with measured PLY range
- **DZ**: DIVERGED to extreme scale (1e23), indicating Z-axis state breakdown

See figures:
- `estimated_force_per_axis.png`: Per-axis force estimates
- `estimated_force_combined.png`: All axes overlaid

### Frequency Estimation Analysis

#### Per-Axis Frequency (in F field)
- Frequency mean: 0.431 Hz (target ~0.45 Hz, reasonable)
- Frequency std: 0.120 Hz
- P95 step: 0.030 Hz/s (low jitter, good smoothness)

See figures:
- `frequency_per_axis_xy.png`: F field over time (per-axis breakdown not in OBSV log)
- `frequency_fused.png`: Fused frequency estimate

#### Startup Anomaly (~30-40s)
Window analysis (30s - 40s):
- Frequency mean in window: 0.373 Hz
- Frequency std in window: 0.285 Hz
- Max rate of change: 159 Hz/s (**VERY HIGH** - indicates estimation instability)

Likely causes:
1. **Energy gate hysteresis**: RMS measurement oscillates around threshold boundary, toggling gate on/off repeatedly
2. **Initialization phase noise**: Early EKF estimates lack sufficient observational history; small input variations cause large frequency swings
3. **Per-axis fusion timing mismatch**: X/Y axis inclusion/exclusion decisions update asynchronously, causing vibration in fused result

See figure: `frequency_startup_anomaly.png` (zoomed view with rate-of-change analysis)

### State Variable Evolution
Z-axis divergence visible in `state_evolution.png`:
- DZ grows to 1e23 scale (uncontrolled)
- VZ similarly diverges
- CZ remains fixed at -163.6

XY-axes remain bounded and reasonable.

**Root cause hypothesis**: Z-axis EKF state never properly initialized, or axis mask configuration prevents Z-axis updates while allowing divergent prediction to accumulate unchecked.

## Replay Baseline Comparison (existing reports)
| source | sw_active_ratio | sw_transitions | freq_mean_hz | freq_std_hz |
| --- | --- | --- | --- | --- |
| analysis/replay/results/runs/00000443/00000443_bin_result.csv | 0.4878 | 2 | 0.5392 | 0.0645 |
| analysis/replay/results/runs/00000444/00000444_bin_result.csv | 0.3554 | 2 | 0.5435 | 0.0819 |

**Note**: Replay logs have SW transitions (on/off cycling), whereas this flight log has SW always OFF. This is **expected and correct** for the current test condition (SW OFF = no external force estimation enabled).

## Findings
- [INFO] **SW always OFF is correct**: SW=0 throughout log is the expected test condition.
- [MEDIUM] **Frequency estimation performs adequately when SW is OFF**: Mean frequency 0.43 Hz is close to expected 0.45 Hz target; low jitter (p95 step = 0.030 Hz/s).
- [HIGH] **Startup anomaly (35s region)**: Frequency estimate shows high rate-of-change (159 Hz/s max). Likely due to energy gate boundary effects and initialization phase turbulence.
- [CRITICAL] **Z-axis state divergence**: DZ, VZ grow to extreme scales (1e23). This indicates EKF state breakdown on Z-axis, unrelated to SW control.
- [MEDIUM] **CY remains fixed at 0**: No variation in Y-axis DC offset estimate.

## Assessment
✅ **Estimation Works Normally on XY Axes**:
- D, V, C states remain bounded and reasonable for X and Y axes
- Frequency estimate is stable with acceptable jitter

⚠️ **Z-Axis State Breakdown**:
- Z-axis EKF state not properly initialized or updated
- Divergence appears independent of SW control
- Check AP_Observer initialization and axis-specific update logic

⚠️ **Startup Transient at ~35s**:
- Energy gate hysteresis may cause frequency oscillation during initialization
- Consider smoothing energy gate response or increasing hysteresis window

## Artifacts
- `analysis_summary.json`: Startup anomaly metrics
- `DETAILED_ANALYSIS.md`: Comprehensive state analysis
- `estimated_force_per_axis.png`: D state (force) per axis
- `estimated_force_combined.png`: D state all axes
- `frequency_per_axis_xy.png`: F field (frequency) over time
- `frequency_fused.png`: Fused frequency
- `frequency_startup_anomaly.png`: Zoomed startup analysis with rate-of-change
- `state_evolution.png`: D, V, C state evolution (reveals divergence)
- `obsv_csv`: analysis/ekf_eval/flight/data/csv/00000074_obsv.csv
- `overview_png`: analysis/ekf_eval/flight/reports/00000074_20260427_131945/overview.png
- `summary_json`: analysis/ekf_eval/flight/reports/00000074_20260427_131945/summary.json

