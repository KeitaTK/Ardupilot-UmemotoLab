# EKF Summary — 2026-04-05

目的：
- 機体固有の共振周波数を特定し、EKF に固定値として組み込む検証を行う。

実施内容：
- 生データ（`PLX`/`PLY`/`PLZ`）に対する FFT を 0–3 Hz 帯域で実行し、支配的な共振周波数を特定。
- リプレイ環境で固定周波数 EKF を実行（初期周波数 0.45 Hz、`q_w=1e-9`、`r_meas=0.08`）し、既存 EKF と比較。

主な結果：
- 対象ログ（00000443, 00000444）で XY 軸に約 0.45 Hz の優勢ピークを確認。
- 固定周波数 EKF は該当例で周波数推定のジッタを低減し、推定安定化に寄与する傾向を示した。
- Z 軸は異なる挙動を示すため、軸別の扱いや追加検証が必要。

結論：
- 初期検証では単一の固定周波数モデルが有効であり、ランタイムで固定周波数を選択するオプションを実装する価値がある。
- 二成分（long/short）プロトタイプは保持済み（`feature/ekf-dual-component-prototype` ブランチ）。

次のステップ：
- `feature/ekf-single-frequency` ブランチ上で `AP_Observer` にパラメータ（例：`OBS_EKF_W_FIXED_HZ`）とランタイム固定周波数オプションを追加。
- 追加ログで広域検証を実施し、パラメータスイープを行う。

参照：
- analysis/replay/results/diagnostics/fft_resonance_2026-04-04/
- analysis/replay/results/diagnostics/single_freq_2026-04-05/
- /memories/repo/ekf_frequency_notes.md

作成日: 2026-04-05
# EKF 周波数推定 — ここまでのまとめ (2026-04-05)

概要
- 目的: 外力（振動）を観測し周波数を推定するEKF/RLS系の安定化と運用性改善。
- これまでの作業: EKF外力ゲーティング、2成分周波数プロトタイプ、FFT解析、固定周波数リプレイ検証を実施。

主要実装／成果物
- C++ (ライブラリ)
  - `libraries/AP_Observer/` 内にEKFのゲーティング/設定に関する実装（リプレイ用setter関数含む）。
  - リプレイ実行バイナリ: `libraries/AP_Observer/examples/RLS_CSV_Replay/RLS_CSV_Replay.cpp` にコマンドラインオプションを追加。

- Python (解析/再現)
  - `analysis/replay/dual_component_frequency_replay_analysis.py`: 軸別に長周期/短周期の二成分推定を行い、長周期採用アルゴリズムを比較。
  - `analysis/replay/fft_resonance_analysis.py`: 生データ(PLX/PLY/PLZ)に対するFFT解析（現在は 0–3Hz 帯に制限）を実行し、図とレポートを生成。
  - `analysis/replay/fixed_frequency_ekf_replay.py`: 固定周波数（例: 0.45Hz）でリプレイを実行し、既存EKFとの比較メトリクスを出力。

- レポート/結果
  - FFTレポート: `analysis/replay/results/diagnostics/fft_resonance_2026-04-04/FFT_RESONANCE_REPORT_2026-04-04.md`
  - 固定周波数リプレイ比較: `analysis/replay/results/diagnostics/single_freq_2026-04-05/SINGLE_FREQ_EKF_REPORT_2026-04-05.md`
  - 比較メトリクスCSV: `analysis/replay/results/diagnostics/single_freq_2026-04-05/single_freq_ekf_metrics.csv`

主要所見（要点）
- FFT解析により `00000443` と `00000444` の XY 軸は主ピークが約 0.45Hz に集中。Z軸は別のピーク（例: ~0.89Hz等）を示し、性質が異なる。
- 以上より、本データセットでは「単一周波数モデル（≈0.45Hz）を採用する方針が適切」である可能性が高い。
- 固定周波数（または非常に小さいプロセス雑音）を用いるとEKFのギザつきや周波数ジャンプが減少し、安定性が向上する傾向を再現できた。

推奨アクション
1. `AP_Observer` にランタイムで設定可能な固定周波数オプションを追加（パラメータ名例: `OBS_EKF_W_FIXED_HZ`、もしくは `OBS_EKF_Q_W=very_small` を提供）。
2. 実機・別ログでピークの一般性を検証（姿勢・荷重・運用モードごとに変化するか）。
3. 固定周波数モード実装後、リプレイ + 実機で比較評価（既存メトリクス: MAE, std, p95_step_hz 等）。
4. もし条件によって複数ピークが出るケースが確認されたら、その時点で二成分モデルを再検討。

次の作業候補
- 単一周波数モードのAP_Observerへの実装（小変更で済む: リプレイ用の `set_ekf_w_init_hz_for_replay()` に対応するランタイムパラメータと、q_wを低く抑えるロジック）。
- 実機ログを追加で解析し、ピークの安定性を評価。

---
作成: 自動生成 (作業履歴を元に要約) 
関連ファイルは `analysis/replay/` 以下にまとまっています。
