import pandas as pd
import matplotlib.pyplot as plt
import glob
import os

# Results directory
results_dir = "analysis/replay/results/"

def plot_result(csv_path):
    print(f"Plotting {csv_path}...")
    try:
        df = pd.read_csv(csv_path, comment="#", skip_blank_lines=True)
    except Exception as e:
        print(f"Skipping {csv_path}: {e}")
        return

    # Basic cleanup
    if df.columns[0] != "Time_s" and "Time_s" not in df.columns:
         pass 
    
    df = df[pd.to_numeric(df["Time_s"], errors="coerce").notnull()]
    df["Time_s"] = df["Time_s"].astype(float)
    if "EstFreq_Hz" in df.columns:
        df["EstFreq_Hz"] = df["EstFreq_Hz"].astype(float)
    
    plt.figure(figsize=(10,6))
    
    if "EstFreq_Hz" in df.columns:
        plt.plot(df["Time_s"], df["EstFreq_Hz"], label="Replay Est Freq", alpha=0.9, linewidth=1.5)
    
    if "RealFreq_Hz" in df.columns:
        df["RealFreq_Hz"] = pd.to_numeric(df["RealFreq_Hz"], errors='coerce')
        plt.plot(df["Time_s"], df["RealFreq_Hz"], label="Real Machine Freq", alpha=0.7, linestyle="--", linewidth=1.5)

    # Plot Target and Start lines
    plt.axhline(y=0.5794, color='g', linestyle=':', label='Start Target (0.74m)')
    plt.axhline(y=0.4880, color='r', linestyle=':', label='End Target (1.04m)')

    plt.xlabel("Time [s]")
    plt.ylabel("Frequency [Hz]")
    basename = os.path.basename(csv_path)
    plt.title(f"RLS Frequency: {basename}")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    
    outpath = results_dir + basename.replace(".csv", ".png")
    plt.savefig(outpath, dpi=150)
    print(f"Saved {outpath}")

# Find all result CSVs
csv_files = glob.glob(results_dir + "*_result.csv")
for f in csv_files:
    plot_result(f)
