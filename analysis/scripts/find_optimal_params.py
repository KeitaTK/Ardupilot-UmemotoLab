import pandas as pd
import glob
import os
import re

target_freq = 0.488

results_dir = "analysis/replay/results/"
files = glob.glob(results_dir + "*_alpha*.csv")

data = []

for f in files:
    try:
        # Extract Log ID and Alpha from filename
        # Format: 00000443_alpha0.01.csv
        basename = os.path.basename(f)
        match = re.search(r"(\d+)_alpha(\d+\.\d+)\.csv", basename)
        if not match:
            continue
            
        log_id = match.group(1)
        alpha = float(match.group(2))
        
        df = pd.read_csv(f)
        
        if "EstFreq_Hz" not in df.columns:
            continue
            
        start_freq = df["EstFreq_Hz"].iloc[0]
        end_freq = df["EstFreq_Hz"].iloc[-1]
        
        # Calculate convergence metric (error at end)
        error = abs(end_freq - target_freq)
        
        # Calculate stability (std dev of last 100 samples)
        # Assuming 200Hz or similar, 100 samples is 0.5s.
        if len(df) > 100:
            stability = df["EstFreq_Hz"].tail(100).std()
        else:
            stability = 0.0
            
        data.append({
            "Log": log_id,
            "Alpha": alpha,
            "StartFreq": start_freq,
            "EndFreq": end_freq,
            "Error": error,
            "Stability": stability
        })
        
    except Exception as e:
        print(f"Error processing {f}: {e}")

df_res = pd.DataFrame(data)
df_res = df_res.sort_values(by=["Log", "Alpha"])

print(f"Target Frequency: {target_freq} Hz")
print("-" * 80)
print(f"{'Log':<10} {'Alpha':<10} {'EndFreq':<10} {'Error':<10} {'Stability':<10}")
print("-" * 80)

best_params = {}

for index, row in df_res.iterrows():
    print(f"{row['Log']:<10} {row['Alpha']:<10.2f} {row['EndFreq']:<10.4f} {row['Error']:<10.4f} {row['Stability']:<10.5f}")

print("\nBest Parameters per Log (Min Error):")
for log_id in df_res["Log"].unique():
    log_df = df_res[df_res["Log"] == log_id]
    best_row = log_df.loc[log_df["Error"].idxmin()]
    print(f"Log {log_id}: Alpha={best_row['Alpha']:.2f} (EndFreq={best_row['EndFreq']:.4f}, Error={best_row['Error']:.4f})")
