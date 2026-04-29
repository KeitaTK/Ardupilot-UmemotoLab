import pandas as pd
import matplotlib.pyplot as plt
import os

csv_path = "/home/umemoto/Ardupilot-UmemotoLab/analysis/replay/results/runs/00000081_fixed/00000081_fixed_result.csv"
out_dir = "/home/umemoto/Ardupilot-UmemotoLab/scratch/plots_00000081_fixed"
os.makedirs(out_dir, exist_ok=True)

df = pd.read_csv(csv_path)

# Plot DX
plt.figure(figsize=(12, 6))
plt.plot(df['Time_s'], df['PLX'], label='PLX (Measurement)', color='gray', alpha=0.5)
plt.plot(df['Time_s'], df['DX'], label='DX (EKF Estimate)', color='blue', linewidth=2)
plt.title('DX vs PLX (00000081_fixed)')
plt.xlabel('Time [s]')
plt.ylabel('Force [N]')
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(out_dir, "dx_vs_plx_fixed.png"), dpi=150)

# Check max DX to see if it diverged
max_dx = df['DX'].abs().max()
print(f"Max DX: {max_dx}")
if max_dx > 1e4:
    print("WARNING: DX appears to have diverged!")
else:
    print("SUCCESS: DX did not diverge.")

print("Plots saved.")
