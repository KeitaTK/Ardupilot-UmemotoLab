#!/usr/bin/env python3
"""Validate RMS-energy gated EKF on windowed log 00000444.

Compares X-only, Y-only, and XY frequency estimates for representative q_w values
on windows where the new energy threshold was found to keep X active and Y mostly
below threshold.
"""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


TARGET_HZ = 0.45


@dataclass(frozen=True)
class WindowConfig:
    tag: str
    input_bin: Path
    start_sec: float
    end_sec: float


DEFAULT_QWS = ["1e-9", "1e-5", "1e-2"]
AXES = [
    ("x", "1"),
    ("y", "2"),
    ("xy", "3"),
]


def extract_csv_with_window(bin_path: Path, csv_output: Path, start_sec: float, end_sec: float) -> None:
    cmd = [
        "python3",
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
    print(f"Extracting window {start_sec}s-{end_sec}s from {bin_path}")
    subprocess.run(cmd, check=True)


def run_replay(replay_bin: Path, csv_input: Path, outdir: Path, tag: str, q_w: str, axis_mask: str) -> Path:
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
        "--ekf-w-init-hz",
        "0.60",
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
        return {"mean_hz": float("nan"), "std_hz": float("nan"), "mae_hz": float("nan"), "p95_step_hz": float("nan")}
    step = np.abs(np.diff(f))
    return {
        "mean_hz": float(np.mean(f)),
        "std_hz": float(np.std(f)),
        "mae_hz": float(np.mean(np.abs(f - TARGET_HZ))),
        "p95_step_hz": float(np.percentile(step, 95)) if step.size > 0 else 0.0,
    }


def make_plot(tag: str, csv_input: Path, traces: Dict[str, np.ndarray], out_png: Path) -> None:
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
    ax_btm.set_title(f"{tag}: X/Y/XY estimates with RMS gate")
    ax_btm.set_xlabel("Time [s]")
    ax_btm.set_ylabel("Estimated frequency [Hz]")
    ax_btm.grid(True, alpha=0.3)
    ax_btm.legend(loc="best")

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate RMS-gated EKF on 00000444 windows")
    parser.add_argument("--replay-bin", default="build/sitl/examples/RLS_CSV_Replay")
    parser.add_argument("--outdir", default="analysis/replay/results/diagnostics/xy_axis_comparison_00000444_energy_gate_2026-04-07")
    parser.add_argument("--qws", nargs="*", default=DEFAULT_QWS)
    args = parser.parse_args()

    windows = [
        WindowConfig(tag="00000444_w35_100", input_bin=Path("analysis/replay/data/00000444.BIN"), start_sec=35, end_sec=100),
        WindowConfig(tag="00000444_w40_110", input_bin=Path("analysis/replay/data/00000444.BIN"), start_sec=40, end_sec=110),
    ]

    outdir = Path(args.outdir)
    fig_dir = outdir / "figures"
    csv_dir = outdir / "csv"
    outdir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)

    replay_bin = Path(args.replay_bin)
    metrics_rows = []

    for win in windows:
        csv_input = csv_dir / f"{win.tag}_extracted.csv"
        extract_csv_with_window(win.input_bin, csv_input, win.start_sec, win.end_sec)

        results_dir = outdir / "runs" / win.tag
        results_dir.mkdir(parents=True, exist_ok=True)

        for q_w in args.qws:
            traces: Dict[str, np.ndarray] = {}
            for label, mask in AXES:
                tag = f"{win.tag}_fixed060_q{q_w}_axis_{label}"
                result_csv = run_replay(replay_bin, csv_input, results_dir / f"q_{q_w}" / label, tag, q_w, mask)
                df = pd.read_csv(result_csv)
                traces[label] = df["EstFreq_Hz"].to_numpy(dtype=float)
                met = compute_metrics(traces[label], df["SW"].to_numpy(dtype=int))
                metrics_rows.append({"log": win.tag, "q_w": q_w, "axis": label, **met})

            make_plot(f"{win.tag} q={q_w}", csv_input, traces, fig_dir / f"{win.tag}_q{q_w}_x_y_xy.png")

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_csv = outdir / "windowed_metrics.csv"
    metrics_df.to_csv(metrics_csv, index=False)
    print(f"Wrote: {metrics_csv}")
    print(f"Figures: {fig_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
