import pandas as pd
import sys

def analyze_csv(path, target_freq=0.488):
    print(f"Analyzing {path} ...")
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return

    if "EstFreq_Hz" not in df.columns:
        print("EstFreq_Hz column missing")
        return

    start_freq = df["EstFreq_Hz"].iloc[0]
    end_freq = df["EstFreq_Hz"].iloc[-1]
    
    real_start = df["RealFreq_Hz"].iloc[0] if "RealFreq_Hz" in df.columns else float('nan')
    real_end = df["RealFreq_Hz"].iloc[-1] if "RealFreq_Hz" in df.columns else float('nan')

    print(f"  Replay Start: {start_freq:.4f} Hz (Target 0.74m/0.579Hz)")
    print(f"  Replay End:   {end_freq:.4f} Hz (Target 1.04m/{target_freq:.4f}Hz)")
    print(f"  Real Start:   {real_start:.4f} Hz")
    print(f"  Real End:     {real_end:.4f} Hz")
    
    diff_replay = end_freq - target_freq
    print(f"  Replay Final Error: {diff_replay:.4f} Hz")
    
    diff_real = real_end - target_freq
    print(f"  Real Final Error:   {diff_real:.4f} Hz")

    if abs(diff_replay) < 0.05:
         print("  ✅ Replay Converged close to target.")
    else:
         print("  ⚠️ Replay did NOT converge to target.")

    if abs(end_freq - real_end) < 0.02:
        print("  ✅ Replay matches Real Machine result.")
    else:
        print("  ⚠️ Replay differs from Real Machine.")
    print("-" * 40)

files = [
    "analysis/replay/results/00000443_result.csv",
    "analysis/replay/results/00000444_result.csv"
]

for f in files:
    analyze_csv(f)
