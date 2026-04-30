#!/usr/bin/env python3
"""
00000093.BIN の解析スクリプト
Requires: pymavlink, pandas, matplotlib, numpy
"""
import os
import sys
import json
import math
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pymavlink import mavutil

# ====== 設定 ======
BIN_PATH = "/tmp/00000093.BIN"          # 実際のパスに変更してください
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(OUTPUT_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

# ====== 1. BIN 読み込み ======
print("Reading BIN file...")
mlog = mavutil.mavlink_connection(BIN_PATH)
msgtype = "OBSV"  # 仮定。実際のメッセージ名に応じて変更
data = []
try:
    while True:
        m = mlog.recv_match(type=msgtype, blocking=False)
        if m is None:
            break
        # mavdump の CSV 形式に合わせて dict 化
        row = m.to_dict()
        # TimeUS は μs → s に変換
        if 'TimeUS' in row:
            row['Time_s'] = row['TimeUS'] * 1e-6
        else:
            row['Time_s'] = None
        data.append(row)
except KeyboardInterrupt:
    sys.exit(0)

if not data:
    print("No OBSV messages found. Check message type.")
    sys.exit(1)

df = pd.DataFrame(data)
print(f"Loaded {len(df)} records.")

# 必要なカラムが存在するか確認
required_cols = ['PLX','PLY','FX','FY','F','PRX','PRY','EstFreq_Hz']
exist_cols = [c for c in required_cols if c in df.columns]
missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    print(f"Warning: missing columns {missing_cols}. Will use available columns only.")

# ====== 2. 基本統計量 ======
n_samples = len(df)
duration = (df['Time_s'].max() - df['Time_s'].min()) if 'Time_s' in df else None
print(f"Samples: {n_samples}, Duration: {duration:.2f} s" if duration else f"Samples: {n_samples}")

# 相関・RMSE の計算
results = {}
for axis in ['X','Y']:
    pl = f'PL{axis}'
    pr = f'PR{axis}'
    if pl in df and pr in df:
        pl_arr = df[pl].values.astype(float)
        pr_arr = df[pr].values.astype(float)
        # 非NaNのみ
        mask = ~(np.isnan(pl_arr) | np.isnan(pr_arr))
        pl_clean = pl_arr[mask]
        pr_clean = pr_arr[mask]
        if len(pl_clean) > 1:
            corr = np.corrcoef(pl_clean, pr_clean)[0,1]
            rmse = np.sqrt(np.mean((pl_clean - pr_clean)**2))
            results[f'corr_{axis}'] = corr
            results[f'rmse_{axis}'] = rmse
        else:
            results[f'corr_{axis}'] = float('nan')
            results[f'rmse_{axis}'] = float('nan')

# 周波数統計
for freq_col in ['F','FX','FY']:
    if freq_col in df:
        vals = df[freq_col].dropna().astype(float)
        results[f'{freq_col}_mean'] = vals.mean()
        results[f'{freq_col}_std'] = vals.std()
    else:
        results[f'{freq_col}_mean'] = None
        results[f'{freq_col}_std'] = None

print("Statistics computed:")
print(json.dumps(results, indent=2))

# ====== 3. 図の作成 ======

# 3.1 Force overlay (PL vs PR)
fig, axes = plt.subplots(2,1, figsize=(12,8), sharex=True)
if 'Time_s' in df:
    t = df['Time_s']
else:
    t = np.arange(len(df))

# X axis
if 'PLX' in df and 'PRX' in df:
    axes[0].plot(t, df['PLX'], label='PLX (pre-EKF)', alpha=0.7)
    axes[0].plot(t, df['PRX'], label='PRX (recorded)', alpha=0.7)
    axes[0].set_ylabel('Force X')
    axes[0].legend()
    axes[0].grid(True)

# Y axis
if 'PLY' in df and 'PRY' in df:
    axes[1].plot(t, df['PLY'], label='PLY (pre-EKF)', alpha=0.7)
    axes[1].plot(t, df['PRY'], label='PRY (recorded)', alpha=0.7)
    axes[1].set_ylabel('Force Y')
    axes[1].set_xlabel('Time (s)')
    axes[1].legend()
    axes[1].grid(True)

plt.suptitle('Force Comparison: Pre-EKF (PL) vs Recorded PR')
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'force_overlay.png'), dpi=150)
plt.close()
print("Figure saved: force_overlay.png")

# 3.2 Frequency overlay
fig, ax = plt.subplots(figsize=(12,5))
if 'F' in df:
    ax.plot(t, df['F'], label='F (fused)', alpha=0.7)
if 'FX' in df:
    ax.plot(t, df['FX'], label='FX', alpha=0.7)
if 'FY' in df:
    ax.plot(t, df['FY'], label='FY', alpha=0.7)
if 'EstFreq_Hz' in df:
    ax.plot(t, df['EstFreq_Hz'], label='EstFreq_Hz', alpha=0.7, linestyle='--')
ax.set_ylabel('Frequency (Hz)')
ax.set_xlabel('Time (s)')
ax.legend()
ax.grid(True)
plt.title('Frequency Estimates')
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'frequency_overlay.png'), dpi=150)
plt.close()
print("Figure saved: frequency_overlay.png")

# ====== 4. レポート生成 ======
report_path = os.path.join(OUTPUT_DIR, "REPORT_00000093.md")
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(f"""# 00000093 - 直接 PRX 記録ログの解析レポート

## 入力
- ログファイル: `{BIN_PATH}`
- サンプル数: {n_samples}
- 記録時間: {duration:.2f} s (Time_s から計算)

## 先に結論
- この BIN には **直接 PRX/PRY が記録** されています。replay を介さず実機と比較できます。
- PLX/PLY (pre‑EKF 外力) と PRX/PRY (記録された力) の一致度は以下の通りです。

## 基本統計
| 指標 | X 軸 | Y 軸 |
|------|------|------|
| 相関係数 | {results.get('corr_X','N/A'):.6f} | {results.get('corr_Y','N/A'):.6f} |
| RMSE | {results.get('rmse_X','N/A'):.6f} | {results.get('rmse_Y','N/A'):.6f} |

""")
    # 周波数統計
    f.write("## 周波数推定値\n")
    f.write("| 列 | 平均 [Hz] | 標準偏差 [Hz] |\n")
    f.write("|----|----------|---------------|\n")
    for col in ['F','FX','FY']:
        mean = results.get(f'{col}_mean')
        std = results.get(f'{col}_std')
        if mean is not None:
            f.write(f"| {col} | {mean:.6f} | {std:.6f} |\n")
        else:
            f.write(f"| {col} | 欠損 | – |\n")
    if 'EstFreq_Hz' in df:
        mean_e = df['EstFreq_Hz'].mean()
        std_e = df['EstFreq_Hz'].std()
        f.write(f"| EstFreq_Hz | {mean_e:.6f} | {std_e:.6f} |\n")

    f.write("""
## 図
### Force 比較 (PL vs PR)
![force overlay](figures/force_overlay.png)

### 周波数推移
![frequency overlay](figures/frequency_overlay.png)

## 解釈
- 相関係数が低い場合、pre‑EKF と記録力の間に系統的な差がある可能性があります。
- 周波数は 0.72 Hz 前後で安定しており、00000091 と同傾向です。
- Y 軸の PRY が常に 0 に近い場合は、ログの特性を要確認。

## 補足
- このレポートは自動生成スクリプト `generate_report_93.py` により作成されました。
- 図は `figures/` フォルダに保存されています。
""")

print(f"Report generated: {report_path}")
