#!/usr/bin/env python3
"""Detailed OBSV log analysis with state and frequency breakdown visualizations."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def read_obsv_csv(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if "Time_s" not in df.columns:
        df["Time_s"] = (df["TimeUS"].astype(float) - float(df["TimeUS"].iloc[0])) / 1e6
    return df


def compute_filtered_force(df: pd.DataFrame, prediction_time_s: float) -> pd.DataFrame:
    """Reconstruct the post-EKF force used by AP_Observer."""
    filtered = pd.DataFrame(index=df.index)
    for axis in ("X", "Y", "Z"):
        d_col = f"D{axis}"
        if d_col not in df.columns:
            continue
        v_col = f"V{axis}"
        c_col = f"C{axis}"
        d = df[d_col].astype(float)
        v = df[v_col].astype(float) if v_col in df.columns else 0.0
        c = df[c_col].astype(float) if c_col in df.columns else 0.0
        filtered[f"PF{axis}"] = d + prediction_time_s * v + c
    return filtered


def plot_estimated_force_all_axes(df: pd.DataFrame, outdir: Path, title: str, prediction_time_s: float) -> None:
    """Plot pre-EKF input force against reconstructed post-EKF force."""
    t = df["Time_s"].to_numpy(dtype=float)
    filtered = compute_filtered_force(df, prediction_time_s)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    if "PFX" in filtered.columns:
        axes[0].plot(t, filtered["PFX"].to_numpy(dtype=float), linewidth=1.2, label=f"post-EKF filtered force X (dt={prediction_time_s:.3f}s)", color="tab:red")
    if "PLX" in df.columns:
        axes[0].plot(t, df["PLX"].to_numpy(dtype=float), linewidth=1.0, label="PLX (measured)", color="tab:orange", alpha=0.85)
    axes[0].axhline(0, color="black", linestyle="--", linewidth=0.5, alpha=0.5)
    axes[0].set_ylabel("Force [N]")
    axes[0].set_title(f"{title} - Force Overlay: pre-EKF PLX vs post-EKF filtered force X")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best")

    if "PFY" in filtered.columns:
        axes[1].plot(t, filtered["PFY"].to_numpy(dtype=float), linewidth=1.2, label=f"post-EKF filtered force Y (dt={prediction_time_s:.3f}s)", color="tab:green")
    if "PLY" in df.columns:
        axes[1].plot(t, df["PLY"].to_numpy(dtype=float), linewidth=1.0, label="PLY (measured)", color="tab:blue", alpha=0.85)
    axes[1].axhline(0, color="black", linestyle="--", linewidth=0.5, alpha=0.5)
    axes[1].set_ylabel("Force [N]")
    axes[1].set_title(f"{title} - Force Overlay: pre-EKF PLY vs post-EKF filtered force Y")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best")

    axes[1].set_xlabel("Time [s]")
    fig.tight_layout()
    fig.savefig(outdir / "estimated_force_per_axis.png", dpi=170)
    plt.close(fig)


def plot_estimated_force_combined(df: pd.DataFrame, outdir: Path, title: str, prediction_time_s: float) -> None:
    """Plot combined force view for XY only; do not mix in replay-only PRX/PRY."""
    t = df["Time_s"].to_numpy(dtype=float)
    filtered = compute_filtered_force(df, prediction_time_s)

    fig, ax = plt.subplots(figsize=(14, 6))

    for key, color in [("PFX", "tab:red"), ("PFY", "tab:green")]:
        if key in filtered.columns:
            ax.plot(t, filtered[key].to_numpy(dtype=float), linewidth=1.2, label=f"{key} (reconstructed, dt={prediction_time_s:.3f}s)", color=color)
    if "PLX" in df.columns:
        ax.plot(t, df["PLX"].to_numpy(dtype=float), linewidth=1.0, label="PLX (measured)", color="tab:orange", alpha=0.8)
    if "PLY" in df.columns:
        ax.plot(t, df["PLY"].to_numpy(dtype=float), linewidth=1.0, label="PLY (measured)", color="tab:blue", alpha=0.8)

    ax.axhline(0, color="black", linestyle="--", linewidth=0.5, alpha=0.5)
    ax.set_ylabel("Force [N]")
    ax.set_xlabel("Time [s]")
    ax.set_title(f"{title} - Combined Force Overlay (pre-EKF vs post-EKF filtered force)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", ncol=2)

    fig.tight_layout()
    fig.savefig(outdir / "estimated_force_combined.png", dpi=170)
    plt.close(fig)


def plot_frequency_per_axis(df: pd.DataFrame, outdir: Path, title: str) -> None:
    """Plot per-axis and fused frequency from the actual OBSV log.

    F is the fused frequency, FX/FY are the per-axis frequencies.
    """
    t = df["Time_s"].to_numpy(dtype=float)

    x_col = "EstFreq_X_Hz" if "EstFreq_X_Hz" in df.columns else None
    y_col = "EstFreq_Y_Hz" if "EstFreq_Y_Hz" in df.columns else None
    f_col = "F" if "F" in df.columns else None
    if x_col is None and y_col is None and f_col is None:
        return

    fig, ax = plt.subplots(figsize=(14, 6))
    if x_col is not None:
        ax.plot(t, df[x_col].to_numpy(dtype=float), linewidth=1.3, label="X-axis estimate", color="tab:red")
    if y_col is not None:
        ax.plot(t, df[y_col].to_numpy(dtype=float), linewidth=1.3, label="Y-axis estimate", color="tab:green")
    if f_col is not None:
        ax.plot(t, df[f_col].to_numpy(dtype=float), linewidth=1.2, label="F (fused)", color="tab:purple")
    ax.set_ylabel("Frequency [Hz]")
    ax.set_xlabel("Time [s]")
    ax.set_title(f"{title} - Per-axis Frequency Estimates and Fused Result (logged)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    ax.set_ylim(0.0, 1.2)

    fig.tight_layout()
    fig.savefig(outdir / "frequency_per_axis_xy.png", dpi=170)
    plt.close(fig)


def plot_frequency_fused(df: pd.DataFrame, outdir: Path, title: str) -> None:
    """Plot fused estimated frequency only when a separate view is useful."""
    t = df["Time_s"].to_numpy(dtype=float)
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    if "F" in df.columns:
        ax.plot(t, df["F"].to_numpy(dtype=float), linewidth=1.5, label="F (fused frequency)", color="tab:purple")
    
    ax.axhline(0.45, color="green", linestyle="--", linewidth=1.0, alpha=0.7, label="Target 0.45Hz")
    ax.set_ylabel("Estimated Frequency [Hz]")
    ax.set_xlabel("Time [s]")
    ax.set_title(f"{title} - Estimated Frequency (Fused Result)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    ax.set_ylim(0.0, 1.0)
    
    fig.tight_layout()
    fig.savefig(outdir / "frequency_fused.png", dpi=170)
    plt.close(fig)


def analyze_startup_anomaly(df: pd.DataFrame, outdir: Path, title: str, window_start: float = 30.0, window_end: float = 40.0) -> Dict[str, float]:
    """Analyze the frequency estimation anomaly around startup (e.g., 35-40 seconds)."""
    mask = (df["Time_s"] >= window_start) & (df["Time_s"] <= window_end)
    window_df = df[mask]
    
    if "F" not in window_df.columns:
        return {}
    
    f = window_df["F"].to_numpy(dtype=float)
    t = window_df["Time_s"].to_numpy(dtype=float)
    
    # Calculate derivatives and statistics
    df_dt = np.diff(f) / np.diff(t) if t.size > 1 else np.array([])
    
    metrics = {
        "window_start_s": float(window_start),
        "window_end_s": float(window_end),
        "samples_in_window": int(mask.sum()),
        "freq_mean_hz": float(np.mean(f)),
        "freq_std_hz": float(np.std(f)),
        "freq_min_hz": float(np.min(f)),
        "freq_max_hz": float(np.max(f)),
        "df_dt_max_hz_per_s": float(np.max(np.abs(df_dt))) if df_dt.size else float("nan"),
        "df_dt_mean_abs_hz_per_s": float(np.mean(np.abs(df_dt))) if df_dt.size else float("nan"),
    }
    
    # Plot zoomed-in view
    fig, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True)
    
    axes[0].plot(t, f, linewidth=1.5, marker="o", markersize=3, label="Frequency")
    axes[0].axhline(0.45, color="green", linestyle="--", linewidth=1.0, alpha=0.7, label="Target 0.45Hz")
    axes[0].set_ylabel("Estimated Frequency [Hz]")
    axes[0].set_title(f"{title} - Startup Anomaly Analysis ({window_start:.1f}-{window_end:.1f}s)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best")
    
    if df_dt.size > 0:
        axes[1].plot(t[1:], df_dt, linewidth=1.2, marker="s", markersize=3, color="tab:red")
        axes[1].axhline(0, color="black", linestyle="-", linewidth=0.5, alpha=0.5)
    axes[1].set_ylabel("dF/dt [Hz/s]")
    axes[1].set_xlabel("Time [s]")
    axes[1].grid(True, alpha=0.3)
    
    fig.tight_layout()
    fig.savefig(outdir / "frequency_startup_anomaly.png", dpi=170)
    plt.close(fig)
    
    return metrics


def plot_state_evolution(df: pd.DataFrame, outdir: Path, title: str) -> None:
    """Plot state evolution (D, V, C) to understand why Z diverges."""
    t = df["Time_s"].to_numpy(dtype=float)
    
    fig, axes = plt.subplots(3, 3, figsize=(16, 12), sharex="col")
    
    states = [("DX", "DY", "DZ"), ("VX", "VY", "VZ"), ("CX", "CY", "CZ")]
    labels = ["D (External Force)", "V (Velocity)", "C (DC Offset)"]
    
    for row, (keys, label) in enumerate(zip(states, labels)):
        for col, key in enumerate(keys):
            if key in df.columns:
                data = df[key].to_numpy(dtype=float)
                # Check for extreme values
                if np.abs(data).max() > 1e10:
                    # Log scale for divergence visualization
                    axes[row, col].semilogy(t, np.abs(data) + 1e-30, linewidth=1.0, label=key, color=["tab:red", "tab:green", "tab:blue"][col])
                    axes[row, col].set_ylabel(f"|{key}| [log scale]")
                else:
                    axes[row, col].plot(t, data, linewidth=1.0, label=key, color=["tab:red", "tab:green", "tab:blue"][col])
                    axes[row, col].set_ylabel(f"{key}")
            
            axes[row, col].set_title(f"{label} - {key}")
            axes[row, col].grid(True, alpha=0.3)
        
        axes[row, 0].set_ylabel(label)
    
    for col in range(3):
        axes[2, col].set_xlabel("Time [s]")
    
    fig.suptitle(f"{title} - State Evolution (D, V, C)", fontsize=14)
    fig.tight_layout()
    fig.savefig(outdir / "state_evolution.png", dpi=170)
    plt.close(fig)


def generate_analysis_report(outdir: Path, csv_path: Path, metrics: Dict[str, float], prediction_time_s: float) -> None:
    """Generate a detailed analysis report."""
    report = []
    report.append(f"# Detailed OBSV Analysis Report\n")
    report.append(f"## Input\n")
    report.append(f"- CSV: {csv_path}\n")
    report.append(f"- Prediction time used for reconstructed post-EKF force: {prediction_time_s:.3f} s\n")
    report.append(f"- Generated: {datetime.now().isoformat()}\n\n")
    
    report.append(f"## State Variable Explanation\n")
    report.append(f"- **PLX / PLY**: EKF に入る前の実機外力入力。\n")
    report.append(f"- **Post-EKF filtered force**: D + pred_dt * V + C, matching AP_Observer::get_predicted_force().\n")
    report.append(f"- **V (VX, VY, VZ)**: Rate state of D [N/s].\n")
    report.append(f"- **C (CX, CY, CZ)**: DC offset state [N].\n")
    report.append(f"- **F**: Fused frequency estimate [Hz]. Integrated result of per-axis frequency estimates.\n")
    report.append(f"- **FX / FY**: X/Y axis frequency estimates [Hz]. Use these together with F in the frequency figure.\n")
    report.append(f"- **SW**: Switch state (always 0 = OFF in this flight log).\n\n")

    report.append(f"## 軸別 force/state の読み方\n")
    report.append(f"- 前半の実機比較は、PLX / PLY と post-EKF filtered force を並べて見る。\n")
    report.append(f"- replay は後半の検証だけに使い、PRX / PRY は実機 OBSV の前半には混ぜない。\n")
    report.append(f"- F / FX / FY は周波数推定。F は融合結果、FX/FY は軸別推定。\n\n")
    
    report.append(f"## Frequency Estimation Anomaly Analysis (~35s)\n")
    if metrics:
        report.append(f"Startup window ({metrics.get('window_start_s')}s - {metrics.get('window_end_s')}s):\n")
        report.append(f"- Samples: {metrics.get('samples_in_window')}\n")
        report.append(f"- Frequency mean: {metrics.get('freq_mean_hz', float('nan')):.4f} Hz\n")
        report.append(f"- Frequency std: {metrics.get('freq_std_hz', float('nan')):.6f} Hz\n")
        report.append(f"- Max frequency rate of change: {metrics.get('df_dt_max_hz_per_s', float('nan')):.6f} Hz/s\n\n")
        report.append(f"Likely causes of frequency noise:\n")
        report.append(f"1. **Energy gate hysteresis**: At startup, RMS crosses threshold with oscillation as on/off cycle repeats.\n")
        report.append(f"2. **Initialization phase noise**: Early estimates lack sufficient history; small force variations cause large frequency swings.\n")
        report.append(f"3. **Per-axis gate timing mismatch**: X/Y axis inclusion/exclusion timing differs, causing fused frequency vibration.\n\n")
    else:
        report.append(f"Detailed analysis skipped (insufficient data).\n")
    
    report.append(f"## Artifacts\n")
    report.append(f"- `estimated_force_per_axis.png`: Estimated force per axis (PLX/PLY vs reconstructed post-EKF force)\n")
    report.append(f"- `estimated_force_combined.png`: Estimated force combined (XY only, pre/post EKF)\n")
    if (outdir / "frequency_per_axis_xy.png").exists():
        report.append(f"- `frequency_per_axis_xy.png`: Per-axis and fused frequency estimates (F/FX/FY)\n")
    report.append(f"- `frequency_fused.png`: Fused frequency estimate\n")
    report.append(f"- `frequency_startup_anomaly.png`: Startup anomaly detail (zoomed)\n")
    report.append(f"- `state_evolution.png`: State variable evolution (D, V, C)\n")
    
    (outdir / "DETAILED_ANALYSIS.md").write_text("\n".join(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Detailed OBSV log analysis with state breakdown")
    parser.add_argument("--input-csv", required=True, help="Path to OBSV CSV")
    parser.add_argument("--outdir", default=".", help="Output directory")
    parser.add_argument("--startup-window-start", type=float, default=30.0, help="Startup anomaly window start [s]")
    parser.add_argument("--startup-window-end", type=float, default=40.0, help="Startup anomaly window end [s]")
    args = parser.parse_args()

    csv_path = Path(args.input_csv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = read_obsv_csv(csv_path)
    tag = csv_path.stem

    prediction_time_s = 0.01
    plot_estimated_force_all_axes(df, outdir, tag, prediction_time_s)
    plot_estimated_force_combined(df, outdir, tag, prediction_time_s)
    plot_frequency_per_axis(df, outdir, tag)
    plot_frequency_fused(df, outdir, tag)
    plot_state_evolution(df, outdir, tag)

    metrics = analyze_startup_anomaly(df, outdir, tag, args.startup_window_start, args.startup_window_end)
    generate_analysis_report(outdir, csv_path, metrics, prediction_time_s)

    summary = {"metrics": metrics}
    (outdir / "analysis_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {outdir / 'DETAILED_ANALYSIS.md'}")
    print(f"Wrote {outdir / 'analysis_summary.json'}")
    print(f"Generated figures:")
    print(f"  - estimated_force_per_axis.png")
    print(f"  - estimated_force_combined.png")
    if (outdir / "frequency_per_axis_xy.png").exists():
        print(f"  - frequency_per_axis_xy.png")
    print(f"  - frequency_fused.png")
    print(f"  - frequency_startup_anomaly.png")
    print(f"  - state_evolution.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
