# EKFアルゴリズム比較レポート (2026-04-06)

## 目的
- 複数EKF実装方針の周波数推定結果を、同一ログ・同一時間軸で比較する。
- 各ログで上段に生データの揺れとSW、下段に推定周波数を重ねて挙動差を評価する。

## 比較対象
- Baseline EKF (3軸融合, log SW)
- XY EKF always-on
- XY EKF SW-hold
- XY EKF SW+amp-gate
- Fixed init 0.45Hz (q_w=1e-9)
- Fixed init 0.60Hz (q_w=1e-9)

## 作図
- 00000443: figures/00000443_ekf_algorithm_comparison.png
- 00000444: figures/00000444_ekf_algorithm_comparison.png

## 評価指標
- mean_hz, std_hz, mae_hz (target=0.45Hz)
- p95_step_hz, max_step_hz (時間差分の滑らかさ)
- hf_ratio (2-20Hz / 0-0.5Hz パワー比)
- final_abs_err_hz
- 合成スコア = p95_step + 0.30*MAE + 0.10*std + 0.05*final_abs_err

## 総合ランキング (2ログ平均)
| method_label | score | mae_hz | std_hz | p95_step_hz | hf_ratio | final_abs_err_hz |
| --- | --- | --- | --- | --- | --- | --- |
| Fixed init 0.45Hz (q_w=1e-9) | 0.0063 | 0.0107 | 0.0074 | 0.0000 | 0.0001 | 0.0471 |
| XY EKF always-on | 0.0075 | 0.0097 | 0.0115 | 0.0000 | 0.0004 | 0.0691 |
| XY EKF SW-hold | 0.0148 | 0.0302 | 0.0141 | 0.0000 | 0.0786 | 0.0861 |
| XY EKF SW+amp-gate | 0.0237 | 0.0573 | 0.0157 | 0.0000 | 0.0031 | 0.0999 |
| Fixed init 0.60Hz (q_w=1e-9) | 0.0349 | 0.1031 | 0.0118 | 0.0000 | 0.0001 | 0.0558 |
| Baseline EKF (3-axis, log SW) | 0.0514 | 0.1455 | 0.0283 | 0.0011 | 0.1196 | 0.0774 |

最良方式: Fixed init 0.45Hz (q_w=1e-9)

## ログ別ランキング

### 00000443
| method_label | score | mae_hz | std_hz | p95_step_hz | hf_ratio | final_abs_err_hz |
| --- | --- | --- | --- | --- | --- | --- |
| Fixed init 0.45Hz (q_w=1e-9) | 0.0126 | 0.0214 | 0.0147 | 0.0000 | 0.0002 | 0.0942 |
| XY EKF always-on | 0.0128 | 0.0130 | 0.0226 | 0.0000 | 0.0001 | 0.1317 |
| XY EKF SW-hold | 0.0148 | 0.0201 | 0.0217 | 0.0000 | 0.0002 | 0.1321 |
| XY EKF SW+amp-gate | 0.0179 | 0.0344 | 0.0164 | 0.0000 | 0.0005 | 0.1195 |
| Fixed init 0.60Hz (q_w=1e-9) | 0.0353 | 0.1077 | 0.0236 | 0.0000 | 0.0001 | 0.0132 |
| Baseline EKF (3-axis, log SW) | 0.0477 | 0.1373 | 0.0377 | 0.0013 | 0.0407 | 0.0284 |

### 00000444
| method_label | score | mae_hz | std_hz | p95_step_hz | hf_ratio | final_abs_err_hz |
| --- | --- | --- | --- | --- | --- | --- |
| Fixed init 0.45Hz (q_w=1e-9) | 0.0000 | 0.0001 | 0.0000 | 0.0000 | 0.0001 | 0.0001 |
| XY EKF always-on | 0.0023 | 0.0064 | 0.0005 | 0.0000 | 0.0007 | 0.0065 |
| XY EKF SW-hold | 0.0147 | 0.0403 | 0.0065 | 0.0000 | 0.1570 | 0.0401 |
| XY EKF SW+amp-gate | 0.0296 | 0.0801 | 0.0151 | 0.0000 | 0.0056 | 0.0803 |
| Fixed init 0.60Hz (q_w=1e-9) | 0.0345 | 0.0984 | 0.0001 | 0.0000 | 0.0001 | 0.0984 |
| Baseline EKF (3-axis, log SW) | 0.0551 | 0.1537 | 0.0190 | 0.0008 | 0.1985 | 0.1265 |

## 方針検討に向けた所見
- XY系はZ軸混入を避けるため、ログによってはBaselineより安定化しやすい。
- SW-holdはSW OFF区間のドリフト抑制に有効だが、ON/OFF運用次第で追従性とのトレードオフが出る。
- 固定初期値EKFは初期値依存性が明確で、0.60Hz初期はバイアス残留リスクが高い。
- 実運用方針としては、XYベース + 低q_w + 必要に応じたSW-holdの組合せが現実的。

## 出力ファイル
- metrics CSV: analysis/replay/results/diagnostics/ekf_algorithm_comparison_2026-04-06/ekf_algorithm_metrics.csv
- ranking CSV: analysis/replay/results/diagnostics/ekf_algorithm_comparison_2026-04-06/ekf_algorithm_ranking.csv
- report: analysis/replay/results/diagnostics/ekf_algorithm_comparison_2026-04-06/EKF_ALGORITHM_COMPARISON_REPORT_2026-04-06.md