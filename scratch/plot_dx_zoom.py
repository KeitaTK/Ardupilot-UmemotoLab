import pandas as pd
import matplotlib.pyplot as plt

csv_path = "/home/umemoto/Ardupilot-UmemotoLab/analysis/replay/results/runs/00000078/00000078_bin_result.csv"
df = pd.read_csv(csv_path)

# Filter time range 0s to 90s
df_range = df[(df['Time_s'] >= 0) & (df['Time_s'] <= 90)]

# Plot X
plt.figure(figsize=(12, 6))
plt.plot(df_range['Time_s'], df_range['PLX'], label='PLX (Measurement)', color='gray', alpha=0.5)
plt.plot(df_range['Time_s'], df_range['DX'], label='DX (EKF Estimate)', color='blue', linewidth=2)
plt.title('DX vs PLX (Time: 0s - 90s) - Fixed EKF')
plt.xlabel('Time [s]')
plt.ylabel('Force [N]')
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend()
plt.tight_layout()
plt.savefig("/home/umemoto/Ardupilot-UmemotoLab/analysis/replay/results/runs/00000078/plots/dx_vs_plx_0_90.png", dpi=150)

# Plot Y
plt.figure(figsize=(12, 6))
plt.plot(df_range['Time_s'], df_range['PLY'], label='PLY (Measurement)', color='gray', alpha=0.5)
plt.plot(df_range['Time_s'], df_range['DY'], label='DY (EKF Estimate)', color='green', linewidth=2)
plt.title('DY vs PLY (Time: 0s - 90s) - Fixed EKF')
plt.xlabel('Time [s]')
plt.ylabel('Force [N]')
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend()
plt.tight_layout()
plt.savefig("/home/umemoto/Ardupilot-UmemotoLab/analysis/replay/results/runs/00000078/plots/dy_vs_ply_0_90.png", dpi=150)

print("Plots saved.")
