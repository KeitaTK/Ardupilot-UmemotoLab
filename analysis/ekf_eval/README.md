# EKF Evaluation Workspace

`analysis/ekf_eval` は、AP_Observer EKFの評価資産を以下の2系統に分離して管理します。

- `flight/`: 実機DataFlash BINの評価
- `replay/`: 既存リプレイ結果（CSV/図/レポート）の評価

## Directory Layout

- `common/`
  - `bin_to_obsv_csv.py`: DataFlash BIN内の`OBSV`をCSV抽出（既存`analysis/replay/bin_to_replay_csv.py`は互換ラッパー）
- `flight/`
  - `data/bin/`: 実機BINの保管
  - `data/csv/`: 抽出CSV
  - `reports/<tag>/`: 実機評価レポート、図、summary
  - `evaluate_obsv_bin.py`: 実機BIN評価スクリプト
- `replay/`
  - `evaluate_replay_csv.py`: リプレイ結果CSV評価スクリプト
  - `plot_replay_results.py`: 既存リプレイ可視化スクリプト（移設）
  - `reports/`: リプレイ評価レポート
  - `reports/archive/`: 過去レポート保管

## Usage

### Flight BIN evaluation

```bash
cd ~/Ardupilot-UmemotoLab
source venv/bin/activate
python analysis/ekf_eval/flight/evaluate_obsv_bin.py \
  --input-bin /mnt/c/Users/Umemoto/Documents/Taki_Local/BIN/1/00000074.BIN \
  --copy-to-data
```

### Replay result evaluation

```bash
cd ~/Ardupilot-UmemotoLab
source venv/bin/activate
python analysis/ekf_eval/replay/evaluate_replay_csv.py \
  --input-csv analysis/replay/results/runs/00000444/00000444_bin_result.csv
```
