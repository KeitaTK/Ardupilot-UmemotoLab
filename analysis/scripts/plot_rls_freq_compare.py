import pandas as pd
import matplotlib.pyplot as plt

# ファイルパス
csv_005 = "analysis/replay/results/result.csv"
csv_001 = "analysis/replay/results/result_alpha001.csv"

# CSV読み込み（先頭行スキップや重複ヘッダ対策）
def read_freq_csv(path):
    df = pd.read_csv(path, comment="#", skip_blank_lines=True)
    # ヘッダが重複している場合は除去
    if df.columns[0] != "Time_s":
        df.columns = ["Time_s", "PLX", "PLY", "EstFreq_Hz", "PhaseCorr", "SW", "RealSW"]
    df = df[pd.to_numeric(df["Time_s"], errors="coerce").notnull()]
    df["Time_s"] = df["Time_s"].astype(float)
    df["EstFreq_Hz"] = df["EstFreq_Hz"].astype(float)
    return df

df_005 = read_freq_csv(csv_005)
df_001 = read_freq_csv(csv_001)

plt.figure(figsize=(10,5))
plt.plot(df_005["Time_s"], df_005["EstFreq_Hz"], label="Alpha=0.05", alpha=0.8)
plt.plot(df_001["Time_s"], df_001["EstFreq_Hz"], label="Alpha=0.01", alpha=0.8)
plt.xlabel("Time [s]")
plt.ylabel("Estimated Frequency [Hz]")
plt.title("RLS Frequency Estimation: Alpha=0.05 vs 0.01")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("analysis/replay/results/rls_freq_compare.png", dpi=150)
plt.show()