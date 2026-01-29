import pandas as pd
import matplotlib.pyplot as plt
import os

# Configuration
log_id = "00000443"
alpha_bad = "0.05"
alpha_good = "0.15"
target_freq = 0.488

# Paths
base_dir = "analysis/replay/results/"
file_bad = os.path.join(base_dir, f"{log_id}_alpha{alpha_bad}.csv")
file_good = os.path.join(base_dir, f"{log_id}_alpha{alpha_good}.csv")

# Read Data
try:
    df_bad = pd.read_csv(file_bad)
    df_good = pd.read_csv(file_good)
except FileNotFoundError:
    print("Files not found! Please run the replay sweep first.")
    exit(1)

# Plotting
plt.figure(figsize=(12, 6))

# Plot Bad (Baseline)
plt.plot(df_bad['Time_s'], df_bad['EstFreq_Hz'], label=f'Alpha={alpha_bad} (Baseline)', color='red', alpha=0.7, linestyle='--')

# Plot Good (Optimal)
plt.plot(df_good['Time_s'], df_good['EstFreq_Hz'], label=f'Alpha={alpha_good} (Optimal)', color='green', linewidth=2)

# Plot Target
plt.axhline(y=target_freq, color='blue', linestyle='-.', label=f'Target ({target_freq} Hz)')

plt.title(f'Frequency Estimation Improvement: Log {log_id}\nTarget: {target_freq} Hz (1.04m)')
plt.xlabel('Time (s)')
plt.ylabel('Frequency (Hz)')
plt.legend()
plt.grid(True)
plt.ylim(0.3, 0.7)  # Focus on the relevant range

output_file = "analysis/results/optimization_result_443.png"
plt.savefig(output_file)
print(f"Plot saved to {output_file}")
