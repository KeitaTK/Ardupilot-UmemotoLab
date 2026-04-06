# XY EKF Strategy Report (2026-04-05)

## 目的
- xy 軸だけで EKF 周波数を統合し、z 軸は使わない。
- 3 つの戦略を replay で比較し、周波数だけを遅く更新する設定が有効か確認する。

## まとめ
- replay 対象: `00000443.BIN`, `00000444.BIN`
- 生成物: [analysis/replay/results/diagnostics/xy_ekf_2026-04-05/XY_EKF_STRATEGY_REPORT_2026-04-05.md](../../../analysis/replay/results/diagnostics/xy_ekf_2026-04-05/XY_EKF_STRATEGY_REPORT_2026-04-05.md)
- 主要設定: `OBS_EKF_AX_MASK=3`, `OBS_EKF_SW_HOLD=1`, `OBS_EKF_Q_W` スイープ

## 戦略比較
| strategy | mean_mae_hz | mean_std_hz | mean_p95_step_hz | note |
| --- | --- | --- | --- | --- |
| xy_always_on | 0.0122 | 0.0324 | 0.0002 | 今回データでは総合最良 |
| xy_sw_hold | 0.0302 | 0.0141 | 0.0000 | SW OFF 中の保持が安定 |
| xy_sw_amp_gate | 0.0573 | 0.0157 | 0.0000 | 振幅ゲートは改善が限定的 |

## omega だけを遅くする設定
- `OBS_EKF_Q_W` は omega 状態だけに効くため、d/d_dot/c を速く保ったまま周波数だけをゆっくり更新できる。
- 今回の replay では `q_w=1e-05` 近辺が最良だった。

## 関連ファイル
- [replay analysis script](../../../analysis/replay/ekf_xy_strategy_analysis.py)
- [strategy metrics CSV](../../../analysis/replay/results/diagnostics/xy_ekf_2026-04-05/strategy_metrics.csv)
- [q_w sweep CSV](../../../analysis/replay/results/diagnostics/xy_ekf_2026-04-05/qw_sweep_metrics.csv)

## 備考
- z 軸は別共振を持つため、今回の比較では融合対象から外している。