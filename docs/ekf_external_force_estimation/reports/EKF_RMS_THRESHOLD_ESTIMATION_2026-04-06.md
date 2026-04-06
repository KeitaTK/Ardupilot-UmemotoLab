# EKF 振幅ゲーティング閾値推定レポート (2026-04-06)

目的
- 実データで観察された「PLX が強く PLY が弱い」状況を踏まえ、振幅（エネルギー）に基づいて周波数推定をゲーティングする閾値を実験的に決定する。

手法（概要）
- 抽出済み OBSV CSV（各ウィンドウ）から短時間（STFT 風）に 0.45Hz 帯域の振幅を推定（窓幅 2.0 s、ステップ 1.0 s、Hann 窓）。
- 閾値候補（絶対値: 0.01..0.20、PLX 比率に基づく相対候補）について、各窓で「PLX 振幅が閾値以上である区間割合」と「PLY 振幅が閾値以上である区間割合」を算出。
- 目標条件（実験的）: PLX の割合 >= 0.25 かつ PLY の割合 <= 0.10 を満たす閾値を選定。満たすものが無ければ条件を緩和して候補を提示。

解析対象ファイル
- `analysis/replay/results/diagnostics/fixed_060_qw_sweep_2026-04-06/csv/00000443_w35_100_extracted.csv`
- `analysis/replay/results/diagnostics/fixed_060_qw_sweep_2026-04-06/csv/00000443_w40_110_extracted.csv`
- `analysis/replay/results/diagnostics/fixed_060_qw_sweep_2026-04-06/csv/00000444_w35_100_extracted.csv` (今回抽出)
- `analysis/replay/results/diagnostics/fixed_060_qw_sweep_2026-04-06/csv/00000444_w40_110_extracted.csv` (今回抽出)

主要出力
- 閾値評価テーブル（各窓・候補閾値ごとの割合）: `analysis/replay/results/diagnostics/rms_threshold_estimation_2026-04-06/thresholds_summary.csv`
- 窓別の閾値評価CSV と振幅時系列図: `analysis/replay/results/diagnostics/rms_threshold_estimation_2026-04-06/` 以下（
  - `*_threshold_eval.csv`
  - `*_amps.png`
  - `thresholds_summary.csv`
)

実験結果（抜粋）

推奨（実験的）閾値: **0.20**（振幅の単位はログ内の PLX/PLY と同じ）

窓ごとの主要統計:

| 抽出CSV | global mean PLX amp (@0.45Hz) | 推奨閾値 | PLX 比（閾値に対する割合） | PLX % above | PLY % above |
|---|---:|---:|---:|---:|---:|
| 00000443_w35_100_extracted.csv | 0.72465 | 0.20 | 27.6% | 69.84% | 9.52% |
| 00000443_w40_110_extracted.csv | 0.63206 | 0.20 | 31.6% | 57.35% | 8.82% |
| 00000444_w35_100_extracted.csv | 1.06424 | 0.20 | 18.8% | 87.50% | 3.13% |
| 00000444_w40_110_extracted.csv | 0.98683 | 0.20 | 20.3% | 75.36% | 2.90% |

解釈
- 結果として絶対閾値 `0.20` が全ての対象ウィンドウで「PLY の 0.45Hz 帯はほとんど閾値以下（<=~10% 以下の区間で超過）」かつ「PLX の 0.45Hz 帯は多くの区間で閾値を上回る（>25% 以上）」という条件を満たしました。
- これは、PLX が目立つ実データに対して「閾値 0.20」を使うと Y 軸（PLY）由来の弱い振動成分がある場合に周波数更新をブロックできることを示唆します。

実装上の推奨パラメータ（組み込み向け）
- 短時間振幅推定: 窓幅 = 2 s、更新間隔 = 1 s（本解析設定）。
- 実機向け低コスト設計: 2s 程度の IIR/EMA によるバンド限定 RMS を推奨（詳細は下記）。
- 閾値: `EKF_MIN_AMP = 0.20`（絶対値）
- ヒステリシス: `ON = 0.20`, `OFF = 0.16`（OFF = ON * 0.8）

実装メモ（簡潔）
- 組み込み側では FFT を避け、バンドパス (0.4–0.5Hz 相当) を通した後に二乗値を EMA で積分して RMS を得る実装が低コストかつ安定です。EMA 時定数は約 2–5 s が実用的。
- 判定ロジック: `if rms < OFF: disable observation; elif rms > ON: enable observation`（ヒステリシス付き）。
- ログ/テレメトリ: `OBSV.RMS`, `OBSV.GATE` 等を出して閾値運用の妥当性確認を容易にしてください。

次の提案
- この `0.20` は本解析対象のログに対する経験的候補です。運用で採用する前に複数ログ（異なる風条件/飛行状況）で同解析を回して閾値の堅牢性を確認してください。
- 組み込み実装用に `EKF_MIN_AMP` と `EKF_MIN_AMP_HYST` のパラメータ追加を行い、WIP パッチを作成できます（希望があれば実装します）。

参照ファイル
- 閾値評価結果: `analysis/replay/results/diagnostics/rms_threshold_estimation_2026-04-06/thresholds_summary.csv`
- 窓別図: `analysis/replay/results/diagnostics/rms_threshold_estimation_2026-04-06/*_amps.png`
