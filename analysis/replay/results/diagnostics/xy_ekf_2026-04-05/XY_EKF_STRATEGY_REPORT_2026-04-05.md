# XY EKF Strategy Comparison and Omega Slow-Update Sweep

## Scope
- xy-axis fusion only; z-axis is excluded from fused frequency updates
- two flight logs: 00000443 and 00000444
- compare three strategies and one omega-only q_w sweep

## Strategy Configurations
| strategy | description | note |
| --- | --- | --- |
| xy_sw_hold | xy fusion + SW log + omega hold when switch is off | estimation freezes during SW off |
| xy_sw_amp_gate | xy fusion + SW log + amplitude gating | amp gate dominates; innovation/NIS left loose |
| xy_always_on | xy fusion + always-on estimation | baseline for continuous updating |

## Aggregate Strategy Ranking
| strategy | score | mae_hz | std_hz | p95_step_hz | max_step_hz |
| --- | --- | --- | --- | --- | --- |
| xy_always_on | 0.0083 | 0.0162 | 0.0324 | 0.0002 | 0.3750 |
| xy_sw_hold | 0.0105 | 0.0302 | 0.0141 | 0.0000 | 0.1654 |
| xy_sw_amp_gate | 0.0188 | 0.0573 | 0.0157 | 0.0000 | 0.1168 |

Best strategy by composite score: **xy_always_on**

## Per-Log Strategy Metrics
### 00000443
| strategy | score | mae_hz | std_hz | p95_step_hz | max_step_hz |
| --- | --- | --- | --- | --- | --- |
| xy_sw_hold | 0.0082 | 0.0201 | 0.0217 | 0.0000 | 0.2088 |
| xy_sw_amp_gate | 0.0120 | 0.0344 | 0.0164 | 0.0000 | 0.0878 |
| xy_always_on | 0.0123 | 0.0243 | 0.0496 | 0.0000 | 0.2794 |

### 00000444
| strategy | score | mae_hz | std_hz | p95_step_hz | max_step_hz |
| --- | --- | --- | --- | --- | --- |
| xy_always_on | 0.0043 | 0.0081 | 0.0152 | 0.0004 | 0.4707 |
| xy_sw_hold | 0.0127 | 0.0403 | 0.0065 | 0.0000 | 0.1221 |
| xy_sw_amp_gate | 0.0255 | 0.0801 | 0.0151 | 0.0000 | 0.1459 |

## Omega-Only Slow Update Sweep
- This sweep changes only q_w, so d/d_dot/c keep the same tuning while omega adaptation slows down.
- Best q_w by composite score: **1.0e-05**

| q_w | score | mae_hz | std_hz | p95_step_hz |
| --- | --- | --- | --- | --- |
| 1e-05 | 0.0066 | 0.0137 | 0.0244 | 0.0000 |
| 1e-07 | 0.0068 | 0.0144 | 0.0245 | 0.0000 |
| 1e-06 | 0.0068 | 0.0144 | 0.0245 | 0.0000 |
| 1e-04 | 0.0072 | 0.0140 | 0.0287 | 0.0001 |
| 5e-04 | 0.0083 | 0.0162 | 0.0324 | 0.0002 |

## Artifacts
- strategy metrics CSV: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/strategy_metrics.csv
- q_w sweep CSV: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/qw_sweep_metrics.csv
- strategy figure: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/strategy_comparison.png
- q_w figure: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/qw_sweep.png

## Run Map
### Strategy runs
- 00000443
  - xy_sw_hold: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/00000443/xy_sw_hold/00000443_xy_sw_hold_result.csv
  - xy_sw_amp_gate: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/00000443/xy_sw_amp_gate/00000443_xy_sw_amp_gate_result.csv
  - xy_always_on: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/00000443/xy_always_on/00000443_xy_always_on_result.csv
- 00000444
  - xy_sw_hold: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/00000444/xy_sw_hold/00000444_xy_sw_hold_result.csv
  - xy_sw_amp_gate: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/00000444/xy_sw_amp_gate/00000444_xy_sw_amp_gate_result.csv
  - xy_always_on: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/00000444/xy_always_on/00000444_xy_always_on_result.csv
### q_w runs
- 00000443
  - q_w=5e-04: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/00000443/qw_5e-04/00000443_qw_5e-04_result.csv
  - q_w=1e-04: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/00000443/qw_1e-04/00000443_qw_1e-04_result.csv
  - q_w=1e-05: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/00000443/qw_1e-05/00000443_qw_1e-05_result.csv
  - q_w=1e-06: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/00000443/qw_1e-06/00000443_qw_1e-06_result.csv
  - q_w=1e-07: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/00000443/qw_1e-07/00000443_qw_1e-07_result.csv
- 00000444
  - q_w=5e-04: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/00000444/qw_5e-04/00000444_qw_5e-04_result.csv
  - q_w=1e-04: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/00000444/qw_1e-04/00000444_qw_1e-04_result.csv
  - q_w=1e-05: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/00000444/qw_1e-05/00000444_qw_1e-05_result.csv
  - q_w=1e-06: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/00000444/qw_1e-06/00000444_qw_1e-06_result.csv
  - q_w=1e-07: analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/00000444/qw_1e-07/00000444_qw_1e-07_result.csv

## Conclusion
- xy-only fusion avoids using the z-axis, which matches the observed resonance split between XY and Z.
- SW-off omega hold is the cleanest way to prevent frequency drift while still letting the other EKF states update.
- q_w is the right knob for slowing frequency-only updates; it does not need to slow d/d_dot/c if the firmware keeps the state noises separate.
- On this data set, the current best q_w sweep point is 1.0e-05, but the ranking should be rechecked on other logs before changing the runtime default.