import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import decimate, butter, filtfilt

# NOTE: Run this script inside the project's Python virtual environment (venv).
# NOTE (JP): このスクリプトはプロジェクトの仮想環境 (venv) 内で実行してください。詳細は .github/INSTRUCTIONS.md を参照。

# ==========================================
# CONFIGURATION
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV_CANDIDATES = [
    os.path.join(BASE_DIR, "../logs/CSV/OBSV_data_00000434.csv"),
    os.path.join(BASE_DIR, "../replay/data/00000434.csv"),
]
TARGET_COLUMN = "PLX"
ANALYSIS_START_TIME_SEC = 22.0
ANALYSIS_DURATION_SEC = 10.0
DOWNSAMPLE_FACTOR = 2
BANDPASS_LOW_HZ = 0.4
BANDPASS_HIGH_HZ = 0.8
TIME_OFFSET_SEC = -1.0
SCAN_AROUND_START_SEC = 2.0

OUTPUT_PATH = os.path.join(BASE_DIR, "../results/zero_cross_result.png")

# ==========================================
# Zero-cross frequency estimation
# ==========================================

def estimate_frequency_zero_cross(time_s, signal):
    mean_val = np.mean(signal)
    centered_signal = signal - mean_val
    zero_crossings = np.where(np.diff(np.sign(centered_signal)))[0]
    if len(zero_crossings) < 2:
        return 0.0, 0

    crossing_times = time_s[zero_crossings]
    intervals = np.diff(crossing_times)
    mean_interval = np.mean(intervals)
    if mean_interval == 0:
        return 0.0, len(zero_crossings)

    period = 2 * mean_interval
    frequency = 1.0 / period
    return frequency, len(zero_crossings)


def resolve_csv_path():
    for path in DEFAULT_CSV_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def main():
    csv_path = resolve_csv_path()
    if csv_path is None:
        print("Error: CSV file not found.")
        print("Checked:")
        for path in DEFAULT_CSV_CANDIDATES:
            print(f"  - {path}")
        return

    print(f"Using CSV: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"Columns: {list(df.columns)}")

    if TARGET_COLUMN not in df.columns:
        print(f"Error: TARGET_COLUMN '{TARGET_COLUMN}' not found.")
        return

    if "Time" in df.columns:
        t_raw = np.array(df["Time"].values) / 1000.0
        t_raw = t_raw - t_raw[0]
        time_label = "Time(ms)"
    elif "TimeUS" in df.columns:
        t_raw = np.array(df["TimeUS"].values) * 1e-6
        t_raw = t_raw - t_raw[0]
        time_label = "TimeUS"
    else:
        t_raw = np.arange(len(df), dtype=float)
        time_label = "Index"

    data_raw = np.array(df[TARGET_COLUMN].values)

    if time_label in ("Time(ms)", "TimeUS") and len(t_raw) > 1:
        dt = float(np.mean(np.diff(t_raw)))
        fs_original = 1.0 / dt if dt > 0 else 1.0
    else:
        fs_original = 100.0

    print(f"fs_original: {fs_original:.3f} Hz")

    def compute_window(start_time_s):
        start_idx = int(start_time_s * fs_original)
        if ANALYSIS_DURATION_SEC is not None:
            end_idx = int(start_idx + ANALYSIS_DURATION_SEC * fs_original)
        else:
            end_idx = len(data_raw)
        return start_idx, end_idx

    effective_start_time_sec = ANALYSIS_START_TIME_SEC + TIME_OFFSET_SEC
    print(f"effective_start_time_sec: {effective_start_time_sec:.3f} s")
    start_idx, end_idx = compute_window(effective_start_time_sec)

    print(f"segment idx: {start_idx} -> {end_idx} (len={end_idx - start_idx})")

    t_segment = np.array(t_raw[start_idx:end_idx])
    data_segment = np.array(data_raw[start_idx:end_idx])

    if len(t_segment) == 0:
        print("Error: No data in the specified time range.")
        return

    def process_window(t_seg, data_seg):
        if DOWNSAMPLE_FACTOR > 1:
            data_proc = np.array(decimate(data_seg, DOWNSAMPLE_FACTOR))
            fs_final_local = fs_original / DOWNSAMPLE_FACTOR
            t_proc = np.arange(len(data_proc)) * (1.0 / fs_final_local) + t_seg[0]
        else:
            data_proc = np.array(data_seg)
            t_proc = np.array(t_seg)
            fs_final_local = fs_original
        return t_proc, data_proc, fs_final_local

    t_processed, data_processed, fs_final = process_window(t_segment, data_segment)

    print(f"fs_final: {fs_final:.3f} Hz")
    print(f"processed len: {len(data_processed)}")

    nyq = 0.5 * fs_final
    low = BANDPASS_LOW_HZ / nyq
    high = BANDPASS_HIGH_HZ / nyq
    b, a = butter(N=4, Wn=[low, high], btype="band")
    filtered_signal = filtfilt(b, a, data_processed)

    freq, zero_cross_count = estimate_frequency_zero_cross(t_processed, filtered_signal)
    print(f"Zero-cross count: {zero_cross_count}")
    print(f"Estimated frequency: {freq:.4f} Hz")

    if SCAN_AROUND_START_SEC > 0:
        print("Scan around start time:")
        scan_start = int(effective_start_time_sec - SCAN_AROUND_START_SEC)
        scan_end = int(effective_start_time_sec + SCAN_AROUND_START_SEC)
        for start_time_s in range(scan_start, scan_end + 1):
            scan_start_idx, scan_end_idx = compute_window(start_time_s)
            if scan_end_idx <= scan_start_idx or scan_end_idx > len(data_raw):
                continue
            scan_t_seg = np.array(t_raw[scan_start_idx:scan_end_idx])
            scan_data_seg = np.array(data_raw[scan_start_idx:scan_end_idx])
            scan_t_proc, scan_data_proc, scan_fs_final = process_window(scan_t_seg, scan_data_seg)
            scan_nyq = 0.5 * scan_fs_final
            scan_low = BANDPASS_LOW_HZ / scan_nyq
            scan_high = BANDPASS_HIGH_HZ / scan_nyq
            scan_b, scan_a = butter(N=4, Wn=[scan_low, scan_high], btype="band")
            scan_filtered = filtfilt(scan_b, scan_a, scan_data_proc)
            scan_freq, scan_crosses = estimate_frequency_zero_cross(scan_t_proc, scan_filtered)
            print(f"  start={start_time_s:>3}s freq={scan_freq:.4f}Hz crosses={scan_crosses}")

    plt.figure(figsize=(10, 5))
    plt.plot(t_processed, data_processed, label="Original")
    plt.plot(t_processed, filtered_signal, label=f"Filtered ({BANDPASS_LOW_HZ}-{BANDPASS_HIGH_HZ}Hz)")

    mean_val = np.mean(filtered_signal)
    plt.axhline(mean_val, color="gray", linestyle="--", label=f"Mean: {mean_val:.4f}")

    g = 9.8
    length = g / ((2 * np.pi * freq) ** 2) if freq > 0 else float("nan")
    ax = plt.gca()
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    xpos = xlim[1] - (xlim[1] - xlim[0]) * 0.05
    ypos = ylim[1] - (ylim[1] - ylim[0]) * 0.05
    plt.text(
        xpos,
        ypos,
        f"Pendulum length = {length:.2f} m",
        fontsize=12,
        color="blue",
        ha="right",
        va="top",
        bbox=dict(facecolor="white", alpha=0.7, edgecolor="blue"),
    )

    plt.title(f"Time Domain Signal ({TARGET_COLUMN})")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    plt.savefig(OUTPUT_PATH)
    print(f"Saved plot: {OUTPUT_PATH}")
    plt.show()


if __name__ == "__main__":
    main()
