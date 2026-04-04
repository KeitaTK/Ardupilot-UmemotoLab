# EKF外力推定 実験整理ノート

## 1. 目的
単一周波数モデルを使った外力推定EKFの検証状況を、散在していたレポート・ログ・比較結果から再整理し、現状と課題を明確化する。

## 2. 整理後の配置
- このディレクトリ: 実験全体の要約とインデックス
- reports/: 主要レポートとメトリクスのスナップショット

本整理では、現ブランチに欠落していた解析成果物を参照可能にするため、`feature/ekf-dual-component-prototype` から主要レポートを抽出して `reports/` に集約した。

## 3. データセット
ログ一覧は [EXPERIMENT_LOG_INDEX.md](EXPERIMENT_LOG_INDEX.md) を参照。
主に評価に使われたログは `00000443` と `00000444`。

## 4. 実験の流れと結果

### 4.1 リセット起因ジャンプの特定
参照:
- reports/REPLAY_VALIDATION_2026-04-04.md
- reports/diagnostic_summary.json

主要結果（00000444）:
- baseline_reset_log: mean 0.6330 Hz, MAE 0.1831 Hz, first-on jump +0.1340 Hz
- noreset_log: mean 0.4835 Hz, MAE 0.0335 Hz, first-on jump 0.0 Hz

解釈:
- SW ONエッジ時のリセットがジャンプの主因。
- resetを切るとジャンプは解消し、目標0.45Hzへの誤差も大幅改善。

### 4.2 ゲート・平滑化パラメータ検証
参照:
- reports/EKF_FORCE_GATE_SMOOTHING_REPORT_2026-04-04.md
- reports/EKF_NOISE_ROOT_CAUSE_REPORT_2026-04-04.md

主要結果（always-on）:
- ゲートのみでは改善は限定的（best gateでもMAEは0.154Hz付近）
- Qw低減 + R増加でステップノイズは減る
- ただし、運用全体としては noreset_log の再現が最も安定

解釈:
- パラメータ調整だけでは構造的問題（軸間不一致、融合バイアス）を完全に解消できない。

### 4.3 二成分モデル試作
参照:
- reports/DUAL_COMPONENT_LONG_PERIOD_REPORT_2026-04-04.md

主要結果:
- dual_long_ewma が2ログ平均で最良
- ekf_singleよりMAEが大幅改善（レポート値: 0.1455 -> 0.0400 付近）

解釈:
- 多成分信号に対し単一成分モデルは構造的に不利。
- ただし実装・運用コストが増える。

### 4.4 FFTで主ピーク確認
参照:
- reports/FFT_RESONANCE_REPORT_2026-04-04.md

主要結果:
- 00000443 X: 0.4542 Hz, Y: 0.4850 Hz
- 00000444 X: 0.4500 Hz, Yの有効ピークは0.5022 Hz（主ピーク0.0065 Hzは低周波成分）
- Z軸はXYと性質が異なるピークを持つ

解釈:
- XY主成分は約0.45Hz周辺に集まり、単一周波数近似の根拠になる。

### 4.5 単一周波数固定EKF比較
参照:
- reports/SINGLE_FREQ_EKF_REPORT_2026-04-05.md
- reports/single_freq_ekf_metrics.csv

主要結果:
- 00000443: MAE 0.1373 -> 0.0277
- 00000444: MAE 0.1537 -> 0.0299
- どちらもstd低下、p95_stepは0へ

解釈:
- 現在のデータセットでは、単一周波数固定（0.45Hz）または極小Qw運用が最も安定。

## 5. 現状の問題点
1. 現ブランチでは `analysis/replay` 配下の解析スクリプト・結果ファイル実体が欠落しており、再実行性が低い。
2. always-on運用では軸間不一致（特にY/Z）が融合推定を高周波側へ引っ張る。
3. ゲート閾値調整だけでは、noreset_log相当の精度には到達しにくい。
4. 固定周波数で改善する一方、飛行条件が変わると固定値の一般性が崩れる可能性がある。

## 6. 現時点の実務的結論
1. 単一周波数モデル方針は有効（少なくとも00000443/444では強く有利）。
2. 実装方針は以下のどちらかが現実的。
   - fixed frequency option（例: 0.45Hz）
   - very low Qw mode（ゆっくり更新）
3. noreset運用（SW ON時リセット無効化）は必須級の改善項目。

## 7. 次アクション
1. AP_Observerにランタイム設定可能な固定周波数または低Qwモードを追加。
2. 追加ログ（機体/条件違い）で主ピークの安定性を検証。
3. `analysis/replay` の解析資産を現ブランチへ復元し、再現手順を固定化。

## 8. 収集済み資料
- reports/EKF_SUMMARY_2026-04-05.md
- reports/REPLAY_VALIDATION_2026-04-04.md
- reports/EKF_NOISE_ROOT_CAUSE_REPORT_2026-04-04.md
- reports/EKF_FORCE_GATE_SMOOTHING_REPORT_2026-04-04.md
- reports/DUAL_COMPONENT_LONG_PERIOD_REPORT_2026-04-04.md
- reports/FFT_RESONANCE_REPORT_2026-04-04.md
- reports/SINGLE_FREQ_EKF_REPORT_2026-04-05.md
- reports/single_freq_ekf_metrics.csv
- reports/diagnostic_summary.json
