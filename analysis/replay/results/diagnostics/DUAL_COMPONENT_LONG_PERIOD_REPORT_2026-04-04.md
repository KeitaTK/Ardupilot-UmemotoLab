# Dual Component Frequency Prototype Report (2026-04-04)

## 1. Goal
- Prototype a two-amplitude-component model and compare it against the current single-component EKF output.
- Estimate two frequencies on each axis (X, Y, Z).
- Adopt the longer-period component as the target estimate.
- Run replay on both logs and report results with figures.

## 2. Replay and Data
- Log A: analysis/replay/data/00000443.BIN
- Log B: analysis/replay/data/00000444.BIN
- Replay output (single-component EKF baseline):
  - analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/runs/00000443/00000443_dual_eval_result.csv
  - analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/runs/00000444/00000444_dual_eval_result.csv
- Analysis script:
  - analysis/replay/dual_component_frequency_replay_analysis.py

## 3. Two-Component Prototype Model
Per axis, we model payload force as:

y(t) = A1*sin(2*pi*f1*t + p1) + A2*sin(2*pi*f2*t + p2) + c

Procedure per axis:
1. Sliding-window spectral analysis extracts two peaks.
2. Two frequencies are ordered by period:
   - long-period component: lower frequency
   - short-period component: higher frequency
3. Least-squares fit estimates amplitudes for both components.
4. Time-series interpolation gives per-sample estimates for each axis.

## 4. Long-Period Adoption Algorithms
We compared three fused long-period candidates:
- dual_long_raw
- dual_long_ewma
- dual_long_reliability_hold

Global best across both logs:
- dual_long_ewma
- Source: analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/summary.json

## 5. Why the Current Output Becomes Choppy
Main causes identified:
1. Model mismatch: single-frequency model is too small when motion contains at least two frequency components.
2. Axis heterogeneity: X/Y/Z contain different dominant components, so fusion can produce up/down toggling.
3. Switching behavior: gating and mode transitions introduce piecewise updates, visible as corners.

In short, the choppiness is not only parameter tuning noise. It is also structural, caused by forcing a multi-component signal into a single-component state model.

## 6. Results on Both Logs

### 6.1 Per-axis two-frequency estimates
- 00000443:
  - analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/figures/00000443_axis_two_frequency.png
- 00000444:
  - analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/figures/00000444_axis_two_frequency.png

### 6.2 Fused comparison (current EKF vs single-peak vs long-period adoption)
- 00000443:
  - analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/figures/00000443_fused_comparison.png
- 00000444:
  - analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/figures/00000444_fused_comparison.png

### 6.3 Long/short amplitude ratio
- 00000443:
  - analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/figures/00000443_amp_ratio.png
- 00000444:
  - analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/figures/00000444_amp_ratio.png

## 7. Quantitative Comparison
Metrics file:
- analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/dual_component_method_metrics.csv

Average ranking over both logs (lower is better):
1. dual_long_ewma
   - mae_hz: 0.0400
   - p95_step_hz: 0.00106
2. dual_long_reliability_hold
   - mae_hz: 0.0400
   - p95_step_hz: 0.00106
3. dual_long_raw
   - mae_hz: 0.0401
   - p95_step_hz: 0.00118
4. single_peak_fused
   - mae_hz: 0.0824
5. ekf_single (current)
   - mae_hz: 0.1455

Interpretation:
- Two-component long-period adoption substantially improved target tracking and reduced structural oscillation versus current ekf_single.
- The smoothest practical choice with stable behavior on both logs was dual_long_ewma.

## 8. Is it reasonable that EKF is less smooth than RLS?
Yes, it is generally reasonable.
- RLS-style outputs can look smoother because they behave like strong parameter averaging under fixed model assumptions.
- EKF is a state estimator that reacts to innovation and model mismatch; when the real signal contains mixed components, state updates can visibly move unless model order is increased or output smoothing is added.
- Therefore, with a single-component state, non-smooth behavior is expected under multi-component excitation.

## 9. Recommended Adoption for This Prototype
Use long-period component adoption with temporal smoothing:
- Selected method: dual_long_ewma
- Keep per-axis dual-frequency estimation, but publish the fused long-period component as the main estimate.

## 10. Reproducibility Outputs
- Summary JSON:
  - analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/summary.json
- Method metrics CSV:
  - analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/dual_component_method_metrics.csv
- Per-sample output:
  - analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/00000443_dual_component_series.csv
  - analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/00000444_dual_component_series.csv
