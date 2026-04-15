#!/usr/bin/env python3
"""Sweep `ekf-q-w` for Fixed init 0.60Hz and generate comparison plots/metrics.

Runs replay for multiple `q_w` values with `--ekf-w-init-hz 0.60` on the same windows
used in the windowed comparison (35-100, 40-110). Produces figures and a metrics CSV.
"""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

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


DEFAULT_QWS = ["1e-9", "1e-7", "1e-5", "1e-4", "1e-3", "1e-2"]


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


def run_replay(replay_bin: Path, csv_input: Path, outdir: Path, tag: str, q_w: str) -> Path:
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
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    return outdir / f"{tag}_result.csv"


def compute_metrics(freq: np.ndarray, time_s: np.ndarray, sw: np.ndarray) -> Dict[str, float]:
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
    elif "Time_s" in df.columns:
        t = df["Time_s"].to_numpy(dtype=float)
    else:
        raise ValueError("Neither TimeUS nor Time_s column found")

    sw = df["SW"].to_numpy(dtype=int)
    plx = df["PLX"].to_numpy(dtype=float)
    ply = df["PLY"].to_numpy(dtype=float)
    plz = df["PLZ"].to_numpy(dtype=float)

    plx_z = plx - np.mean(plx)
    ply_z = ply - np.mean(ply)
    plz_z = plz - np.mean(plz)

    fig, (ax_top, ax_btm) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    ax_top.plot(t, plx_z, color="tab:red", linewidth=0.8, label="PLX (dc removed)")
    ax_top.plot(t, ply_z, color="tab:green", linewidth=0.8, label="PLY (dc removed)")
    ax_top.plot(t, plz_z, color="tab:blue", linewidth=0.8, alpha=0.85, label="PLZ (dc removed)")
    ax_top.set_ylabel("Payload force (relative)")
    ax_top.grid(True, alpha=0.3)
    ax_top.legend(loc="upper right", ncol=2)

    ax_sw = ax_top.twinx()
    ax_sw.plot(t, sw, "k--", linewidth=0.9, alpha=0.75, label="SW")
    ax_sw.set_ylabel("SW")
    ax_sw.set_ylim(-0.1, 1.1)

    cmap = plt.get_cmap("tab10")
    colors = [cmap(i) for i in range(len(traces))]
    for (i, (q_label, f)) in enumerate(traces.items()):
        ax_btm.plot(t, f, linewidth=1.0, color=colors[i % len(colors)], label=f"q_w={q_label}")

    ax_btm.axhline(TARGET_HZ, color="black", linestyle="--", linewidth=1.0, label=f"Target={TARGET_HZ:.2f}Hz")
    ax_btm.set_title(f"{tag}: Fixed 0.60Hz q_w sweep")
    ax_btm.set_xlabel("Time [s]")
    ax_btm.set_ylabel("Estimated frequency [Hz]")
    ax_btm.grid(True, alpha=0.3)
    ax_btm.legend(loc="best", ncol=2)

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sweep q_w for fixed 0.60Hz EKF replay")
    parser.add_argument("--replay-bin", default="build/sitl/examples/EKF_CSV_Replay")
    parser.add_argument("--outdir", default="analysis/replay/results/diagnostics/fixed_060_qw_sweep_2026-04-06")
    parser.add_argument("--qws", nargs="*", default=DEFAULT_QWS, help="q_w values (strings, e.g. 1e-9)")
    args = parser.parse_args()

    windows = [
        WindowConfig(tag="00000443_w35_100", input_bin=Path("analysis/replay/data/00000443.BIN"), start_sec=35, end_sec=100),
        WindowConfig(tag="00000443_w40_110", input_bin=Path("analysis/replay/data/00000443.BIN"), start_sec=40, end_sec=110),
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

        traces = {}
        results_dir = outdir / "runs" / win.tag
        results_dir.mkdir(parents=True, exist_ok=True)

        for q_w in args.qws:
            tag = f"{win.tag}_fixed060_q{q_w}"
            result_csv = run_replay(replay_bin, csv_input, results_dir / f"q_{q_w}", tag, q_w)
            df = pd.read_csv(result_csv)
            t_ref = df["Time_s"].to_numpy(dtype=float)
            f = df["EstFreq_Hz"].to_numpy(dtype=float)
            traces[q_w] = f

            sw = df["SW"].to_numpy(dtype=int)
            met = compute_metrics(f, t_ref, sw)
            metrics_rows.append({"log": win.tag, "q_w": q_w, **met})

        # Plot
        make_plot(win.tag, csv_input, traces, fig_dir / f"{win.tag}_fixed060_qw_comparison.png")

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_csv = outdir / "windowed_metrics.csv"
    metrics_df.to_csv(metrics_csv, index=False)
    print(f"Wrote: {metrics_csv}")
    print(f"Figures: {fig_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
