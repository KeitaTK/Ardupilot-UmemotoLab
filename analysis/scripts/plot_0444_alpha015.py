import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

def plot_convergence(csv_path, out_path):
    print(f"Reading {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    plt.figure(figsize=(10, 6))
    
    # Plot Estimated Frequency
    if "EstFreq_Hz" in df.columns:
        plt.plot(df["Time_s"], df["EstFreq_Hz"], label="Estimated Freq", color='blue', alpha=0.8)
    
    # Plot Real Frequency if available
    if "RealFreq_Hz" in df.columns:
        # Filter out 0 or weird values if necessary, but usually it's fine
        plt.plot(df["Time_s"], df["RealFreq_Hz"], label="Real Freq (Truth)", color='green', linestyle='--', alpha=0.6)

    # Plot Switch state (scaled to be visible? or on secondary axis?)
    # For now, just frequency
    
    plt.title(f"Frequency Estimation Convergence (Alpha=0.15)\n{os.path.basename(csv_path)}")
    plt.xlabel("Time [s]")
    plt.ylabel("Frequency [Hz]")
    plt.legend()
    plt.grid(True)
    
    print(f"Saving plot to {out_path}")
    plt.savefig(out_path)
    print("Done.")

if __name__ == "__main__":
    csv_file = "analysis/replay/results/00000444_alpha0.15.csv"
    out_file = "analysis/results/00000444_alpha0.15_plot.png"
    
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    if len(sys.argv) > 2:
        out_file = sys.argv[2]
        
    plot_convergence(csv_file, out_file)
