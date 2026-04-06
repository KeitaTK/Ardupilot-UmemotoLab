# EKF Algorithm Comparison Report (2026-04-06)

## Scope
- Compare multiple EKF implementation policies on identical replay logs.
- Use common x-axis time and y-axis estimated frequency for direct comparison.
- Include raw payload oscillation and SW on the top panel for each log.

## Logs
- 00000443
- 00000444

## Compared Methods
1. Baseline EKF (3-axis fusion, log SW)
2. XY EKF always-on
3. XY EKF SW-hold
4. XY EKF SW + amplitude gate
5. Fixed init 0.45Hz (q_w=1e-9)
6. Fixed init 0.60Hz (q_w=1e-9)

## Main Figures
- [00000443 comparison panel](../../../analysis/replay/results/diagnostics/ekf_algorithm_comparison_2026-04-06/figures/00000443_ekf_algorithm_comparison.png)
- [00000444 comparison panel](../../../analysis/replay/results/diagnostics/ekf_algorithm_comparison_2026-04-06/figures/00000444_ekf_algorithm_comparison.png)

Each figure uses:
- Top panel: PLX/PLY/PLZ (DC removed) + SW (secondary axis)
- Bottom panel: Estimated frequency traces for all methods

## Evaluation Metrics
- mean_hz, std_hz, mae_hz (target = 0.45Hz)
- p95_step_hz, max_step_hz (smoothness)
- hf_ratio = band power ratio (2-20Hz) / (0-0.5Hz)
- final_abs_err_hz
- Composite score:

$$
\mathrm{score} = p95\_step + 0.30\cdot MAE + 0.10\cdot std + 0.05\cdot final\_abs\_err
$$

## Aggregate Ranking (2 logs average)

| method_label | score | mae_hz | std_hz | p95_step_hz | hf_ratio | final_abs_err_hz |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Fixed init 0.45Hz (q_w=1e-9) | 0.0063 | 0.0107 | 0.0074 | 0.0000 | 0.0001 | 0.0471 |
| XY EKF always-on | 0.0075 | 0.0097 | 0.0115 | 0.0000 | 0.0004 | 0.0691 |
| XY EKF SW-hold | 0.0148 | 0.0302 | 0.0141 | 0.0000 | 0.0786 | 0.0861 |
| XY EKF SW+amp-gate | 0.0237 | 0.0573 | 0.0157 | 0.0000 | 0.0031 | 0.0999 |
| Fixed init 0.60Hz (q_w=1e-9) | 0.0349 | 0.1031 | 0.0118 | 0.0000 | 0.0001 | 0.0558 |
| Baseline EKF (3-axis, log SW) | 0.0514 | 0.1455 | 0.0283 | 0.0011 | 0.1196 | 0.0774 |

## Detailed Interpretation For Policy Selection

### 1) Baseline 3-axis fusion is weakest on this dataset
- Z-axis contribution appears to degrade fused frequency behavior for these logs.
- Highest MAE and highest HF ratio among compared methods.

### 2) XY-only policy is consistently effective
- XY EKF always-on is 2nd overall and near-best in both logs.
- This supports the prior observation that XY resonance around ~0.45Hz is dominant.

### 3) SW-hold is useful as an operational safety option
- SW-hold score is lower than XY always-on, but it reduces OFF-window drift risk.
- Recommended as a selectable mode when operator-side SW behavior is important.

### 4) Fixed-frequency behavior has strongest smoothness but clear initialization sensitivity
- Fixed init 0.45Hz gives the best score.
- Fixed init 0.60Hz is clearly biased, showing insufficient forgetting with tiny q_w.
- This indicates fixed-frequency mode should only be used when initialization can be trusted.

## Recommended Direction (Practical)
1. Default candidate: XY EKF always-on + low q_w (frequency-only slow update).
2. Add operator option: SW-hold mode for OFF-window drift suppression.
3. Keep fixed-frequency mode as optional fallback, not as universal default.
4. Validate on additional logs/airframes before freezing runtime defaults.

## Reproducibility Artifacts
- [Detailed auto report](../../../analysis/replay/results/diagnostics/ekf_algorithm_comparison_2026-04-06/EKF_ALGORITHM_COMPARISON_REPORT_2026-04-06.md)
- [Per-log x method metrics CSV](../../../analysis/replay/results/diagnostics/ekf_algorithm_comparison_2026-04-06/ekf_algorithm_metrics.csv)
- [Aggregate ranking CSV](../../../analysis/replay/results/diagnostics/ekf_algorithm_comparison_2026-04-06/ekf_algorithm_ranking.csv)
- [Input run map CSV](../../../analysis/replay/results/diagnostics/ekf_algorithm_comparison_2026-04-06/input_run_map.csv)
