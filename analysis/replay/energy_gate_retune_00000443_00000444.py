#!/usr/bin/env python3
"""Retune the EKF energy gate on 00000443/00000444.

This script reruns the selected windows for both logs with an initial frequency
of 0.60 Hz, compares a small set of energy-gate thresholds, and writes summary
figures that highlight the X-dominant behavior requested in the retune pass.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


TARGET_HZ = 0.45
DEFAULT_W_INIT_HZ = 0.60
DEFAULT_Q_W = "1e-9"
DEFAULT_THRESHOLDS = [0.20, 0.25, 0.30, 0.35]
DEFAULT_TAU_SEC = 2.0


@dataclass(frozen=True)
class WindowConfig:
    log: str
    tag: str
    input_bin: Path
    start_sec: float
    end_sec: float


WINDOWS: Sequence[WindowConfig] = (
    WindowConfig("00000443", "00000443_w35_100", Path("analysis/replay/data/00000443.BIN"), 35, 100),
    WindowConfig("00000443", "00000443_w40_110", Path("analysis/replay/data/00000443.BIN"), 40, 110),
    WindowConfig("00000444", "00000444_w35_100", Path("analysis/replay/data/00000444.BIN"), 35, 100),
    WindowConfig("00000444", "00000444_w40_110", Path("analysis/replay/data/00000444.BIN"), 40, 110),
)

AXES: Sequence[Tuple[str, str]] = (
    ("x", "1"),
    ("y", "2"),
    ("xy", "3"),
)


def extract_csv_with_window(bin_path: Path, csv_output: Path, start_sec: float, end_sec: float) -> None:
    cmd = [
        sys.executable,
        "analysis/replay/bin_to_replay_csv.py",
        "--input",
        str(bin_path),
        "--output",
        str(csv_output),
        "--start-time-sec",
        str(start_sec),
        "--end-time-sec",
        str(end_sec),
    ]
    print(f"Extracting {bin_path} [{start_sec}, {end_sec}] -> {csv_output}")
    subprocess.run(cmd, check=True)


def run_replay(
    replay_bin: Path,
    csv_input: Path,
    outdir: Path,
    tag: str,
    q_w: str,
    axis_mask: str,
    energy_on: float,
    energy_off: float,
    energy_tau: float,
    w_init_hz: float,
) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(replay_bin),
        "--input",
        str(csv_input),
        "--outdir",
        str(outdir),
        "--tag",
        tag,
        "--sw-mode",
        "log",
        "--ekf-reset-on-switch",
        "0",
        "--ekf-force-hold-max",
        "0.0",
        "--ekf-force-reject-min",
        "5.0",
        "--ekf-axis-gate",
        "0",
        "--ekf-energy-gate",
        "1",
        "--ekf-energy-rms-on",
        f"{energy_on:.3f}",
        "--ekf-energy-rms-off",
        f"{energy_off:.3f}",
        "--ekf-energy-tau",
        f"{energy_tau:.3f}",
        "--ekf-w-init-hz",
        f"{w_init_hz:.3f}",
        "--ekf-q-w",
        q_w,
        "--ekf-axis-mask",
        axis_mask,
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    return outdir / f"{tag}_result.csv"


def compute_metrics(freq: np.ndarray, sw: np.ndarray) -> Dict[str, float]:
    on_mask = sw == 1
    if not np.any(on_mask):
        on_mask = np.ones_like(sw, dtype=bool)

    f = freq[on_mask]
    if f.size < 2:
        return {
            "mean_hz": float("nan"),
            "std_hz": float("nan"),
            "mae_hz": float("nan"),
            "final_hz": float("nan"),
        }

    return {
        "mean_hz": float(np.mean(f)),
        "std_hz": float(np.std(f)),
        "mae_hz": float(np.mean(np.abs(f - TARGET_HZ))),
        "final_hz": float(f[-1]),
    }


def make_selection_plot(tag: str, csv_input: Path, traces: Dict[str, np.ndarray], out_png: Path) -> None:
    df = pd.read_csv(csv_input)
    if "TimeUS" in df.columns:
        t = df["TimeUS"].to_numpy(dtype=float) / 1e6 - df["TimeUS"].iloc[0] / 1e6
    else:
        t = df["Time_s"].to_numpy(dtype=float)

    sw = df["SW"].to_numpy(dtype=int)
    plx = df["PLX"].to_numpy(dtype=float)
    ply = df["PLY"].to_numpy(dtype=float)
    plz = df["PLZ"].to_numpy(dtype=float)

    fig, (ax_top, ax_btm) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    ax_top.plot(t, plx - np.mean(plx), color="tab:red", linewidth=0.8, label="PLX (dc removed)")
    ax_top.plot(t, ply - np.mean(ply), color="tab:green", linewidth=0.8, label="PLY (dc removed)")
    ax_top.plot(t, plz - np.mean(plz), color="tab:blue", linewidth=0.8, alpha=0.85, label="PLZ (dc removed)")
    ax_top.set_ylabel("Payload force (relative)")
    ax_top.grid(True, alpha=0.3)
    ax_top.legend(loc="upper right", ncol=2)

    ax_sw = ax_top.twinx()
    ax_sw.plot(t, sw, "k--", linewidth=0.9, alpha=0.75, label="SW")
    ax_sw.set_ylabel("SW")
    ax_sw.set_ylim(-0.1, 1.1)

    colors = {"x": "tab:orange", "y": "tab:green", "xy": "tab:blue"}
    for label, arr in traces.items():
        ax_btm.plot(t, arr, linewidth=1.0, color=colors[label], label=f"{label.upper()} estimate")

    ax_btm.axhline(TARGET_HZ, color="black", linestyle="--", linewidth=1.0, label=f"Target={TARGET_HZ:.2f}Hz")
    ax_btm.set_title(f"{tag}: X/Y/XY estimates with retuned energy gate")
    ax_btm.set_xlabel("Time [s]")
    ax_btm.set_ylabel("Estimated frequency [Hz]")
    ax_btm.grid(True, alpha=0.3)
    ax_btm.legend(loc="best")

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def make_sweep_plot(sweep_df: pd.DataFrame, out_png: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharex=True, sharey=True)
    axes_flat = axes.flat
    for idx, log in enumerate(sorted(sweep_df["log"].unique())):
        ax = axes_flat[idx]
        sub = sweep_df[sweep_df["log"] == log]
        for window in sorted(sub["window"].unique()):
            win_df = sub[sub["window"] == window].sort_values("energy_on")
            ax.plot(win_df["energy_on"], win_df["mean_hz"], marker="o", linewidth=1.2, label=window)
        ax.axhline(TARGET_HZ, color="black", linestyle="--", linewidth=1.0, alpha=0.8)
        ax.set_title(log)
        ax.set_xlabel("Energy gate ON threshold")
        ax.set_ylabel("Mean estimate [Hz]")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")

    for ax in axes_flat:
        ax.set_xlim(0.18, 0.37)
        ax.set_ylim(0.33, 0.50)

    fig.suptitle("Retune sweep: initial 0.60 Hz, q_w fixed, XY output")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Retune the EKF energy gate across 00000443 and 00000444")
    parser.add_argument("--replay-bin", default="build/sitl/examples/EKF_CSV_Replay")
    parser.add_argument("--outdir", default="analysis/replay/results/diagnostics/xy_axis_retune_00000443_00000444_2026-04-07")
    parser.add_argument("--q-w", default=DEFAULT_Q_W)
    parser.add_argument("--w-init-hz", type=float, default=DEFAULT_W_INIT_HZ)
    parser.add_argument("--energy-on", type=float, default=0.20)
    parser.add_argument("--energy-off", type=float, default=0.16)
    parser.add_argument("--energy-tau", type=float, default=DEFAULT_TAU_SEC)
    parser.add_argument("--thresholds", nargs="*", type=float, default=DEFAULT_THRESHOLDS)
    args = parser.parse_args()

    outdir = Path(args.outdir)
    fig_dir = outdir / "figures"
    csv_dir = outdir / "csv"
    outdir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)

    replay_bin = Path(args.replay_bin)
    metrics_rows: List[Dict[str, object]] = []
    sweep_rows: List[Dict[str, object]] = []

    for win in WINDOWS:
        csv_input = csv_dir / f"{win.tag}_extracted.csv"
        extract_csv_with_window(win.input_bin, csv_input, win.start_sec, win.end_sec)

        results_dir = outdir / "runs" / win.tag
        results_dir.mkdir(parents=True, exist_ok=True)

        traces: Dict[str, np.ndarray] = {}
        for label, mask in AXES:
            tag = f"{win.tag}_on{args.energy_on:.2f}_init{args.w_init_hz:.2f}_q{args.q_w}_axis_{label}"
            result_csv = run_replay(
                replay_bin,
                csv_input,
                results_dir / f"selected_{label}",
                tag,
                args.q_w,
                mask,
                args.energy_on,
                args.energy_off,
                args.energy_tau,
                args.w_init_hz,
            )
            df = pd.read_csv(result_csv)
            traces[label] = df["EstFreq_Hz"].to_numpy(dtype=float)
            metrics = compute_metrics(traces[label], df["SW"].to_numpy(dtype=int))
            metrics_rows.append({"log": win.log, "window": win.tag, "axis": label, "config": "selected", **metrics})

        make_selection_plot(
            f"{win.tag} on={args.energy_on:.2f} init={args.w_init_hz:.2f}",
            csv_input,
            traces,
            fig_dir / f"{win.tag}_selected_x_y_xy.png",
        )

        for threshold in args.thresholds:
            threshold_off = threshold * 0.8
            result_csv = run_replay(
                replay_bin,
                csv_input,
                results_dir / f"sweep_on_{threshold:.2f}",
                f"{win.tag}_sweep_on{threshold:.2f}",
                args.q_w,
                "3",
                threshold,
                threshold_off,
                args.energy_tau,
                args.w_init_hz,
            )
            df = pd.read_csv(result_csv)
            metrics = compute_metrics(df["EstFreq_Hz"].to_numpy(dtype=float), df["SW"].to_numpy(dtype=int))
            sweep_rows.append(
                {
                    "log": win.log,
                    "window": win.tag,
                    "energy_on": threshold,
                    "energy_off": threshold_off,
                    "q_w": args.q_w,
                    **metrics,
                }
            )

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_csv = outdir / "selected_metrics.csv"
    metrics_df.to_csv(metrics_csv, index=False)

    sweep_df = pd.DataFrame(sweep_rows)
    sweep_csv = outdir / "threshold_sweep_metrics.csv"
    sweep_df.to_csv(sweep_csv, index=False)

    make_sweep_plot(sweep_df, fig_dir / "threshold_sweep_summary.png")

    print(f"Wrote: {metrics_csv}")
    print(f"Wrote: {sweep_csv}")
    print(f"Figures: {fig_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())