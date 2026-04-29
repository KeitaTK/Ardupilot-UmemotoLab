import pandas as pd
import matplotlib.pyplot as plt
import os

csv_path = "/home/umemoto/Ardupilot-UmemotoLab/analysis/ekf_eval/flight/data/csv/00000081_obsv.csv"
out_dir = "/home/umemoto/Ardupilot-UmemotoLab/scratch/plots_00000081"
os.makedirs(out_dir, exist_ok=True)

df = pd.read_csv(csv_path)

# Plot DX
plt.figure(figsize=(12, 6))
plt.plot(df['TimeUS'] / 1e6, df['PLX'], label='PLX (Measurement)', color='gray', alpha=0.5)
plt.plot(df['TimeUS'] / 1e6, df['DX'], label='DX (EKF Estimate)', color='blue', linewidth=2)
plt.title('DX vs PLX (00000081)')
plt.xlabel('Time [s]')
plt.ylabel('Force [N]')
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(out_dir, "dx_vs_plx.png"), dpi=150)

# Plot P matrix elements if they exist? No, P matrix is not logged in OBSV.
# Let's plot CY (offset) to see if it diverges
if 'CY' in df.columns:
    plt.figure(figsize=(12, 6))
    plt.plot(df['TimeUS'] / 1e6, df['CY'], label='CY (EKF Estimate offset)', color='red', linewidth=2)
    plt.title('CY vs Time')
    plt.xlabel('Time [s]')
    plt.ylabel('Force Offset [N]')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "cy_vs_time.png"), dpi=150)

print("Plots saved.")
