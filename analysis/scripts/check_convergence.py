import math
import pandas as pd
import sys

def analyze_csv(path, target_freq=0.488, length_min_m=None, length_max_m=None):
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
    print(f"  Replay End:   {end_freq:.4f} Hz (Target {target_freq:.4f}Hz)")
    print(f"  Real Start:   {real_start:.4f} Hz")
    print(f"  Real End:     {real_end:.4f} Hz")
    
    diff_replay = end_freq - target_freq
    print(f"  Replay Final Error: {diff_replay:.4f} Hz")
    
    diff_real = real_end - target_freq
    print(f"  Real Final Error:   {diff_real:.4f} Hz")

    if length_min_m is not None and length_max_m is not None:
        g = 9.8
        f_min = (1.0 / (2.0 * math.pi)) * math.sqrt(g / length_max_m)
        f_max = (1.0 / (2.0 * math.pi)) * math.sqrt(g / length_min_m)
        print(f"  Acceptable Range: {f_min:.4f} Hz to {f_max:.4f} Hz")
        if f_min <= end_freq <= f_max:
            print("  ✅ Replay within length bounds.")
        else:
            print("  ⚠️ Replay OUTSIDE length bounds.")
    else:
        if abs(diff_replay) < 0.05:
             print("  ✅ Replay Converged close to target.")
        else:
             print("  ⚠️ Replay did NOT converge to target.")

    if abs(end_freq - real_end) < 0.02:
        print("  ✅ Replay matches Real Machine result.")
    else:
        print("  ⚠️ Replay differs from Real Machine.")
    print("-" * 40)

cases = [
    ("analysis/replay/results/00000434_zero_cross.csv", 0.4913, 0.90, 1.10),
    ("analysis/replay/results/00000443_result.csv", 0.488, None, None),
    ("analysis/replay/results/00000444_result.csv", 0.488, None, None),
]

for f, target, len_min, len_max in cases:
    analyze_csv(f, target_freq=target, length_min_m=len_min, length_max_m=len_max)
