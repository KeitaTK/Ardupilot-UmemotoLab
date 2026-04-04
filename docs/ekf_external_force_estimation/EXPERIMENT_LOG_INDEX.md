# 実験ログ対応表

## 1. 解析対象ログ（ローカル存在確認済み）
- analysis/logs/Pixhawk6CLogs/00000420.BIN
- analysis/logs/Pixhawk6CLogs/00000422.BIN
- analysis/logs/Pixhawk6CLogs/00000434.BIN
- analysis/logs/Pixhawk6CLogs/00000435.BIN
- analysis/logs/Pixhawk6CLogs/00000437.BIN
- analysis/logs/Pixhawk6CLogs/00000438.BIN
- analysis/logs/Pixhawk6CLogs/00000443.BIN
- analysis/logs/Pixhawk6CLogs/00000444.BIN

## 2. 主要評価ログ
- 00000443
- 00000444

理由:
- 各レポートで共通して比較対象として使われている。
- 単一周波数固定EKF、ノイズ調査、ゲート比較、FFT解析の中心ログ。

## 3. 補助CSV
- analysis/logs/CSV/OBSV_data_00000435.csv
- analysis/logs/CSV/replay_data_00000437.csv
- analysis/logs/CSV/replay_data_00000438.csv

## 4. 注意点
- 現ブランチの analysis/replay 配下には、解析スクリプトと結果ファイル実体がほぼ欠落している。
- 再解析が必要な場合は、feature/ekf-dual-component-prototype から復元するか、同等スクリプトを再配置して実行する。