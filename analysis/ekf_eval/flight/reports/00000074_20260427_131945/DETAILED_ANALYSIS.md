# Detailed OBSV Analysis Report

## Input

- CSV: analysis/ekf_eval/flight/data/csv/00000074_obsv.csv

- Generated: 2026-04-27T13:32:37.649757


## State Variable Explanation

- **D (DX, DY, DZ)**: EKF-estimated external force (prediction time = 0). Estimated payload force per axis [N].

- **V (VX, VY, VZ)**: Rate of estimated force (time derivative of D). Force change rate [N/s].

- **C (CX, CY, CZ)**: DC offset component. Static external force component [N].

- **F**: Fused frequency estimate [Hz]. Integrated result of per-axis frequency estimates.

- **SW**: Switch state (always 0 = OFF in this flight log).


## 発散分析（Z軸状態が飛行終了後に発散）

OBSDivergence Analysis (Z-axis state diverges after flight)

The Z-axis statistics show extreme scales (1e23 order) for DZ, VZ, CZ:

- DZ_max: 1.717e+23

- VZ_max: 8.836e+23

- CZ_std: 0.0 (fixed)

This indicates Z-axis EKF state breakdown due to uninitialization or axis mask mismatch.

XY axes appear normal, so check per-axis initialization and update logic consistency.


## Frequency Estimation Anomaly Analysis (~35s)

Startup window (30.0s - 40.0s):

- Samples: 1000

- Frequency mean: 0.3730 Hz

- Frequency std: 0.284695 Hz

- Max frequency rate of change: 159.026433 Hz/s


Likely causes of frequency noise:

1. **Energy gate hysteresis**: At startup, RMS crosses threshold with oscillation as on/off cycle repeats.

2. **Initialization phase noise**: Early estimates lack sufficient history; small force variations cause large frequency swings.

3. **Per-axis gate timing mismatch**: X/Y axis inclusion/exclusion timing differs, causing fused frequency vibration.


## Artifacts

- `estimated_force_per_axis.png`: Estimated force per axis

- `estimated_force_combined.png`: Estimated force combined

- `frequency_per_axis_xy.png`: Frequency estimates X/Y (separate)

- `frequency_fused.png`: Fused frequency estimate

- `frequency_startup_anomaly.png`: Startup anomaly detail (zoomed)

- `state_evolution.png`: State variable evolution (D, V, C)
