# AP_Observer EKF Flight BIN Evaluation: 00000081

## Input
- Source BIN: analysis/ekf_eval/flight/data/bin/00000081.BIN
- Samples: 9011
- Duration: 90.10 s
- Mean sample rate: 100.00 Hz

## Key Metrics
- sw_active_ratio: 1.0
- sw_transitions: 0
- F_mean: 0.6928631067276001
- F_std: 0.0
- F_min: 0.6928631067276001
- F_max: 0.6928631067276001
- freq_p95_step_hz: 0.0
- plx_dom_freq_hz: 0.4771919024753884
- ply_dom_freq_hz: 0.4882893885794672
- freq_mean_vs_dom_abs_err_hz: 0.2156712042522117
- VZ_max: 0.0
- CY_std: 1.4348932740236632e-07

## Replay Baseline Comparison (existing reports)
| source | sw_active_ratio | sw_transitions | freq_mean_hz | freq_std_hz |
| --- | --- | --- | --- | --- |
| analysis/replay/results/runs/00000443/00000443_bin_result.csv | 0.4878 | 2 | 0.5392 | 0.0645 |
| analysis/replay/results/runs/00000444/00000444_bin_result.csv | 0.3554 | 2 | 0.5435 | 0.0819 |

## Findings
- [MEDIUM] 推定周波数と入力支配周波数の乖離が大きい: 平均Fと支配周波数の差が 0.216 Hz です。ゲート条件か周波数更新則を再点検してください。

## Assessment
- 既存リプレイではSWが一定割合でONかつ遷移が確認される一方、本実機ログではSWが常時0です。
- そのため、レポート上の良好な推定挙動が実機運用条件で再現されていない可能性が高いです。
- Z系状態量の異常スケールも見られるため、OBSV出力の軸別状態更新/ログ格納の整合を要確認です。

## Artifacts
- obsv_csv: analysis/ekf_eval/flight/data/csv/00000081_obsv.csv
- overview_png: analysis/ekf_eval/flight/reports/00000081_20260428_191959/overview.png
- summary_json: analysis/ekf_eval/flight/reports/00000081_20260428_191959/summary.json
