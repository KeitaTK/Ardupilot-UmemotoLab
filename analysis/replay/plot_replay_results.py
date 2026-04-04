#!/usr/bin/env python3
"""Generate replay plots from a replay result CSV."""

import argparse
import csv
import json
import os

import matplotlib.pyplot as plt


def read_result_csv(path):
    time_s = []
    plx = []
    prx = []
    est_freq = []
    real_freq = []

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            time_s.append(float(row["Time_s"]))
            plx.append(float(row["PLX"]))
            prx.append(float(row["PRX"]))
            est_freq.append(float(row["EstFreq_Hz"]))
            real_freq.append(float(row["RealFreq_Hz"]))

    return {
        "time_s": time_s,
        "plx": plx,
        "prx": prx,
        "est_freq": est_freq,
        "real_freq": real_freq,
    }


def summarize(data):
    n = len(data["time_s"])
    if n == 0:
        return {"samples": 0}

    abs_err = [abs(a - b) for a, b in zip(data["plx"], data["prx"])]
    return {
        "samples": n,
        "duration_s": data["time_s"][-1] - data["time_s"][0],
        "est_freq_start_hz": data["est_freq"][0],
        "est_freq_end_hz": data["est_freq"][-1],
        "est_freq_min_hz": min(data["est_freq"]),
        "est_freq_max_hz": max(data["est_freq"]),
        "mean_abs_wave_error_x": sum(abs_err) / n,
    }


def plot_frequency(data, outpath, title):
    # この関数は使わなくなります（個別グラフ出力廃止）
    pass


def plot_waveform(data, outpath, title):
    # この関数は使わなくなります（個別グラフ出力廃止）
    pass


def plot_combined(data, outpath, title):
    plt.figure(figsize=(12, 8))
    # 上段: 周波数推定
    ax1 = plt.subplot(2, 1, 1)
    ax1.plot(data["time_s"], data["est_freq"], label="Estimated frequency", linewidth=1.0)
    ax1.set_xlabel("")
    ax1.set_ylabel("Frequency [Hz]")
    ax1.set_title(f"{title} - Frequency transition")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # 下段: 波形比較
    ax2 = plt.subplot(2, 1, 2, sharex=ax1)
    ax2.plot(data["time_s"], data["plx"], label="Measured x-axis waveform (PLX)", linewidth=1.0)
    ax2.plot(data["time_s"], data["prx"], label="Observer output waveform (PRX)", linewidth=1.0)
    ax2.set_xlabel("Time [s]")
    ax2.set_ylabel("Force proxy")
    ax2.set_title(f"{title} - Measured vs observer waveform (x-axis)")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    plt.tight_layout()
    plt.savefig(outpath, dpi=150)
    plt.close()

def main():
    parser = argparse.ArgumentParser(description="Create replay result plots")
    parser.add_argument("--input", required=True, help="Replay result CSV path")
    parser.add_argument("--outdir", required=True, help="Output directory for plots")
    parser.add_argument("--title", default="Replay", help="Plot title prefix")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    data = read_result_csv(args.input)
    if not data["time_s"]:
        raise SystemExit("No rows found in replay result CSV")


    # 出力ファイル名を統一
    combined_plot = os.path.join(args.outdir, "result_combined.png")
    summary_path = os.path.join(args.outdir, "summary.json")

    # 1つの図にまとめて出力
    plot_combined(data, combined_plot, args.title)

    with open(summary_path, "w") as f:
        json.dump(summarize(data), f, indent=2)

    print(f"Wrote: {combined_plot}")
    print(f"Wrote: {summary_path}")


if __name__ == "__main__":
    main()
