#!/usr/bin/env python3
"""Generate EKF comparison report with time-windowed replay data.

This script extracts specified time windows from BIN logs, runs replays
for multiple EKF strategies, and generates comparison plots/reports.
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
class MethodSpec:
    name: str
    label: str
    color: str
    args: list


@dataclass(frozen=True)
class WindowConfig:
    tag: str
    input_bin: Path
    start_sec: float
    end_sec: float


METHODS: list = [
    MethodSpec(
        name="baseline_3axis_logsw",
        label="Baseline EKF (3-axis, log SW)",
        color="tab:purple",
        args=[],
    ),
    MethodSpec(
        name="xy_always_on",
        label="XY EKF always-on",
        color="tab:green",
        args=["--ekf-axis-mask", "3"],
    ),
    MethodSpec(
        name="xy_hold_omega_off",
        label="XY EKF hold-omega-off",
        color="tab:blue",
        args=["--ekf-axis-mask", "3", "--ekf-hold-omega-off", "1"],
    ),
    MethodSpec(
        name="fixed_045",
        label="Fixed init 0.45Hz (q_w=1e-9)",
        color="tab:red",
        args=["--ekf-w-init-hz", "0.45", "--ekf-q-w", "1e-9"],
    ),
    MethodSpec(
        name="fixed_060",
        label="Fixed init 0.60Hz (q_w=1e-9)",
        color="tab:orange",
        args=["--ekf-w-init-hz", "0.60", "--ekf-q-w", "1e-9"],
    ),
]


def extract_csv_with_window(bin_path: Path, csv_output: Path, start_sec: float, end_sec: float) -> None:
    """Extract BIN to CSV with time window."""
    cmd = [
        "python3",
        "analysis/replay/bin_to_replay_csv.py",
        "--input", str(bin_path),
        "--output", str(csv_output),
        "--start-time-sec", str(start_sec),
        "--end-time-sec", str(end_sec),
    ]
    print(f"Extracting window {start_sec}s-{end_sec}s from {bin_path}")
    subprocess.run(cmd, check=True)


def run_replay(replay_bin: Path, csv_input: Path, outdir: Path, tag: str, method_args: list) -> Path:
    """Run replay with specified arguments."""
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(replay_bin),
        "--input", str(csv_input),
        "--outdir", str(outdir),
        "--tag", tag,
        "--sw-mode", "log",
        "--ekf-reset-on-switch", "0",
        "--ekf-force-hold-max", "0.0",
        "--ekf-force-reject-min", "5.0",
        "--ekf-axis-gate", "0",
        *method_args,
    ]
    subprocess.run(cmd, check=True)
    return outdir / f"{tag}_result.csv"


def compute_metrics(freq: np.ndarray, time_s: np.ndarray, sw: np.ndarray) -> Dict[str, float]:
    on_mask = sw == 1
    if not np.any(on_mask):
        on_mask = np.ones_like(sw, dtype=bool)

    f = freq[on_mask]
    t = time_s[on_mask]
    if f.size < 2:
        return {
            "mean_hz": float("nan"),
            "std_hz": float("nan"),
            "mae_hz": float("nan"),
            "p95_step_hz": float("nan"),
        }

    step = np.abs(np.diff(f))
    return {
        "mean_hz": float(np.mean(f)),
        "std_hz": float(np.std(f)),
        "mae_hz": float(np.mean(np.abs(f - TARGET_HZ))),
        "p95_step_hz": float(np.percentile(step, 95)) if step.size > 0 else 0.0,
    }


def make_plot(tag: str, csv_input: Path, traces: Dict[str, np.ndarray], method_map: Dict[str, MethodSpec], out_png: Path) -> None:
    """Create comparison plot from extracted CSV and replay results."""
    df = pd.read_csv(csv_input)
    
    # Convert TimeUS to Time_s
    if 'TimeUS' in df.columns:
        t = df['TimeUS'].to_numpy(dtype=float) / 1e6 - df['TimeUS'].iloc[0] / 1e6
    elif 'Time_s' in df.columns:
        t = df['Time_s'].to_numpy(dtype=float)
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

    for method_name, f in traces.items():
        spec = method_map[method_name]
        ax_btm.plot(t, f, linewidth=1.0, color=spec.color, label=spec.label)

    ax_btm.axhline(TARGET_HZ, color="black", linestyle="--", linewidth=1.0, label=f"Target={TARGET_HZ:.2f}Hz")
    ax_btm.set_title(f"{tag}: EKF frequency estimation (windowed)")
    ax_btm.set_xlabel("Time [s]")
    ax_btm.set_ylabel("Estimated frequency [Hz]")
    ax_btm.grid(True, alpha=0.3)
    ax_btm.legend(loc="best", ncol=2)

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate windowed EKF comparison report")
    parser.add_argument("--replay-bin", default="build/sitl/examples/RLS_CSV_Replay")
    parser.add_argument("--outdir", default="analysis/replay/results/diagnostics/ekf_windowed_comparison_2026-04-06")
    args = parser.parse_args()

    windows = [
        WindowConfig(
            tag="00000443_w35_100",
            input_bin=Path("analysis/replay/data/00000443.BIN"),
            start_sec=35,
            end_sec=100,
        ),
        WindowConfig(
            tag="00000443_w40_110",
            input_bin=Path("analysis/replay/data/00000443.BIN"),
            start_sec=40,
            end_sec=110,
        ),
    ]

    outdir = Path(args.outdir)
    fig_dir = outdir / "figures"
    csv_dir = outdir / "csv"
    outdir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)

    replay_bin = Path(args.replay_bin)
    method_map = {m.name: m for m in METHODS}

    metrics_rows: list = []

    for win in windows:
        # Extract windowed CSV
        csv_input = csv_dir / f"{win.tag}_extracted.csv"
        extract_csv_with_window(win.input_bin, csv_input, win.start_sec, win.end_sec)

        # Run replays
        traces: Dict[str, np.ndarray] = {}
        results_dir = outdir / "runs" / win.tag
        results_dir.mkdir(parents=True, exist_ok=True)

        for method in METHODS:
            result_csv = run_replay(replay_bin, csv_input, results_dir / method.name, f"{win.tag}_{method.name}", method.args)
            df = pd.read_csv(result_csv)
            t_ref = df["Time_s"].to_numpy(dtype=float)
            f = df["EstFreq_Hz"].to_numpy(dtype=float)
            traces[method.name] = f

            # Compute metrics
            sw = df["SW"].to_numpy(dtype=int)
            met = compute_metrics(f, t_ref, sw)
            metrics_rows.append({
                "log": win.tag,
                "method": method.name,
                "method_label": method.label,
                **met,
            })

        # Create plot
        make_plot(
            tag=win.tag,
            csv_input=csv_input,
            traces=traces,
            method_map=method_map,
            out_png=fig_dir / f"{win.tag}_comparison.png",
        )

    # Write metrics CSV
    metrics_df = pd.DataFrame(metrics_rows)
    metrics_csv = outdir / "windowed_metrics.csv"
    metrics_df.to_csv(metrics_csv, index=False)

    print(f"Wrote: {metrics_csv}")
    print(f"Figures: {fig_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
