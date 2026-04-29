# Detailed OBSV Analysis Report

## Input

- CSV: analysis/ekf_eval/flight/data/csv/00000091_obsv.csv

- Prediction time used for reconstructed post-EKF force: 0.010 s

- Generated: 2026-04-29T18:35:04.043636


## State Variable Explanation

- **PLX / PLY**: EKF に入る前の実機外力入力。

- **Post-EKF filtered force**: D + pred_dt * V + C, matching AP_Observer::get_predicted_force().

- **V (VX, VY, VZ)**: Rate state of D [N/s].

- **C (CX, CY, CZ)**: DC offset state [N].

- **F**: Fused frequency estimate [Hz]. Integrated result of per-axis frequency estimates.

- **FX / FY**: X/Y axis frequency estimates [Hz]. Use these together with F in the frequency figure.

- **SW**: Switch state (always 0 = OFF in this flight log).


## 軸別 force/state の読み方

- 前半の実機比較は、PLX / PLY と post-EKF filtered force を並べて見る。

- replay は後半の検証だけに使い、PRX / PRY は実機 OBSV の前半には混ぜない。

- F / FX / FY は周波数推定。F は融合結果、FX/FY は軸別推定。


## Frequency Estimation Anomaly Analysis (~35s)

Startup window (30.0s - 40.0s):

- Samples: 1000

- Frequency mean: 0.7336 Hz

- Frequency std: 0.013501 Hz

- Max frequency rate of change: 1.149769 Hz/s


Likely causes of frequency noise:

1. **Energy gate hysteresis**: At startup, RMS crosses threshold with oscillation as on/off cycle repeats.

2. **Initialization phase noise**: Early estimates lack sufficient history; small force variations cause large frequency swings.

3. **Per-axis gate timing mismatch**: X/Y axis inclusion/exclusion timing differs, causing fused frequency vibration.


## Artifacts

- `estimated_force_per_axis.png`: Estimated force per axis (PLX/PLY vs reconstructed post-EKF force)

- `estimated_force_combined.png`: Estimated force combined (XY only, pre/post EKF)

- `frequency_per_axis_xy.png`: Per-axis and fused frequency estimates (F/FX/FY)

- `frequency_fused.png`: Fused frequency estimate

- `frequency_startup_anomaly.png`: Startup anomaly detail (zoomed)

- `state_evolution.png`: State variable evolution (D, V, C)
