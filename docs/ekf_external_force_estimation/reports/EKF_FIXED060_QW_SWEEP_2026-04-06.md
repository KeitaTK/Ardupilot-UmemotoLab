# Fixed init 0.60Hz q_w スイープ レポート (2026-04-06)

## 目的
- Fixed init 0.60Hz に対して複数の `q_w` をスイープし、2つの時間窓で推定収束性を評価する。

## 実行概要
- 対象ログ: `00000443.BIN`
- ウィンドウ:
  - 35s–100s
  - 40s–110s
- 初期周波数: 0.60Hz（固定）
- スイープした `q_w` 値: 1e-9, 1e-7, 1e-5, 1e-4, 1e-3, 1e-2
- 実行スクリプト: analysis/replay/fixed_init_060_qw_sweep.py
- 出力:
  - metrics CSV: analysis/replay/results/diagnostics/fixed_060_qw_sweep_2026-04-06/windowed_metrics.csv
  - figures: analysis/replay/results/diagnostics/fixed_060_qw_sweep_2026-04-06/figures

## 図

### 35s–100s
![00000443 w35-100 fixed060 q_w sweep](../../../analysis/replay/results/diagnostics/fixed_060_qw_sweep_2026-04-06/figures/00000443_w35_100_fixed060_qw_comparison.png)

### 40s–110s
![00000443 w40-110 fixed060 q_w sweep](../../../analysis/replay/results/diagnostics/fixed_060_qw_sweep_2026-04-06/figures/00000443_w40_110_fixed060_qw_comparison.png)

## 指標（windowed_metrics.csv より）

### 35s–100s
| q_w | mean_hz | std_hz | mae_hz | p95_step_hz |
| --- | ---: | ---: | ---: | ---: |
| 1e-9 | 0.5584610785 | 0.0002324743 | 0.1084610785 | 0.0 |
| 1e-7 | 0.5584610785 | 0.0002324743 | 0.1084610785 | 0.0 |
| 1e-5 | 0.5583686049 | 0.0002576411 | 0.1083686049 | 0.0 |
| 1e-4 | 0.5575344197 | 0.0004875008 | 0.1075344197 | 0.0 |
| 1e-3 | 0.5523499648 | 0.0019740736 | 0.1023499648 | 0.0 |
| 1e-2 | 0.5451791559 | 0.0042843885 | 0.0951791559 | 0.0 |

### 40s–110s
| q_w | mean_hz | std_hz | mae_hz | p95_step_hz |
| --- | ---: | ---: | ---: | ---: |
| 1e-9 | 0.5533370180 | 0.0001600422 | 0.1033370180 | 0.0 |
| 1e-7 | 0.5533370180 | 0.0001600422 | 0.1033370180 | 0.0 |
| 1e-5 | 0.5532431339 | 0.0001825192 | 0.1032431339 | 0.0 |
| 1e-4 | 0.5526825261 | 0.0003345710 | 0.1026825261 | 0.0 |
| 1e-3 | 0.5490319658 | 0.0013332942 | 0.0990319658 | 0.0 |
| 1e-2 | 0.5440887749 | 0.0032256889 | 0.0940887749 | 0.0 |

## 結論（簡潔）
- `q_w` を大きくすると mean が目標 0.45Hz に近づく傾向（MAE 減少）が見られるが、今回の q_w 範囲では 0.60→0.45 への完全な収束は観測されなかった。
- ただし、得られた変化は限定的であり、q_w を大きくしただけで実用的に十分な収束改善が得られるとは言い切れない。
- さらなる検討案としては、より大きな `q_w` 範囲の探索、SW 挙動（hold/off）の組み合わせ試験、または初期化シーケンスの変更を推奨する。

## 生成物へのリンク
- metrics CSV: ../../../analysis/replay/results/diagnostics/fixed_060_qw_sweep_2026-04-06/windowed_metrics.csv
- figures: ../../../analysis/replay/results/diagnostics/fixed_060_qw_sweep_2026-04-06/figures
