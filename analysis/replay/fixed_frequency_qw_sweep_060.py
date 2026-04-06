#!/usr/bin/env python3
"""Sweep q_w for a 0.60 Hz initial-frequency EKF replay.

This script evaluates whether the filter can forget a 0.60 Hz initial value
and converge to the 0.45 Hz target quickly enough while staying stable.
It uses the xy-only fusion mask and switch-off omega hold.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPLAY_BIN = Path("build/sitl/examples/RLS_CSV_Replay")
INPUTS = {
    "00000443": Path("analysis/replay/data/00000443.BIN"),
    "00000444": Path("analysis/replay/data/00000444.BIN"),
}
OUTBASE = Path("analysis/replay/results/diagnostics/fixed_init_060_qw_sweep_2026-04-05")
RUNS = OUTBASE / "runs"
TARGET_HZ = 0.45
INIT_HZ = 0.60
Q_W_VALUES = [1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2]
SETTLE_TOL_HZ = 0.01
SETTLE_HOLD_S = 5.0

OUTBASE.mkdir(parents=True, exist_ok=True)
RUNS.mkdir(parents=True, exist_ok=True)


@dataclass
class SweepResult:
    log: str
    q_w: float
    mean_hz: float
    std_hz: float
    mae_hz: float
    p95_step_hz: float
    max_step_hz: float
    hf_ratio: float
    final_hz: float
    final_err_hz: float
    settle_time_s: float


def ensure_csv(input_path: Path, outdir: Path) -> Path:
    if input_path.suffix.lower() != ".bin":
        return input_path

    outdir.mkdir(parents=True, exist_ok=True)
    out_csv = outdir / f"{input_path.stem}_from_bin.csv"
    cmd = [
        "python3",
        "analysis/replay/bin_to_replay_csv.py",
        "--input",
        str(input_path),
        "--output",
        str(out_csv),
    ]
    subprocess.run(cmd, check=True)
    return out_csv


def run_replay(binary: Path, input_path: Path, outdir: Path, tag: str, q_w: float) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(binary),
        "--input",
        str(input_path),
        "--outdir",
        str(outdir),
        "--tag",
        tag,
        "--sw-mode",
        "log",
        "--ekf-reset-on-switch",
        "0",
        "--ekf-axis-mask",
        "3",
        "--ekf-hold-omega-off",
        "1",
        "--ekf-force-hold-max",
        "1.5",
        "--ekf-force-reject-min",
        "5.0",
        "--ekf-axis-gate",
        "0",
        "--ekf-w-init-hz",
        f"{INIT_HZ}",
        "--ekf-q-w",
        f"{q_w}",
        "--ekf-r-meas",
        "0.08",
    ]
    subprocess.run(cmd, check=True)
    return outdir / f"{tag}_result.csv"


def metrics(freq: np.ndarray, t: np.ndarray, sw: np.ndarray, target: float = TARGET_HZ) -> Dict[str, float]:
    mask = sw == 1
    if not np.any(mask):
        mask = np.ones_like(sw, dtype=bool)

    f = freq[mask]
    tt = t[mask]
    if f.size < 2:
        return {
            "mean_hz": float("nan"),
            "std_hz": float("nan"),
            "mae_hz": float("nan"),
            "p95_step_hz": float("nan"),
            "max_step_hz": float("nan"),
            "hf_ratio": float("nan"),
            "final_hz": float("nan"),
            "final_err_hz": float("nan"),
            "settle_time_s": float("nan"),
        }

    step = np.abs(np.diff(f))
    dt = float(np.mean(np.diff(tt))) if tt.size > 1 else 0.01
    x = f - np.mean(f)
    win = np.hanning(x.size)
    spec = np.fft.rfft(x * win)
    fr = np.fft.rfftfreq(x.size, d=dt)
    pw = np.abs(spec) ** 2
    low = float(np.sum(pw[(fr >= 0.0) & (fr < 0.5)]))
    high = float(np.sum(pw[(fr >= 2.0) & (fr < 20.0)]))
    hf_ratio = high / max(low, 1.0e-12)

    final_hz = float(f[-1])
    final_err = abs(final_hz - target)
    settle_time = convergence_time(f, tt, target=target, tol=SETTLE_TOL_HZ, hold_sec=SETTLE_HOLD_S)

    return {
        "mean_hz": float(np.mean(f)),
        "std_hz": float(np.std(f)),
        "mae_hz": float(np.mean(np.abs(f - target))),
        "p95_step_hz": float(np.percentile(step, 95)),
        "max_step_hz": float(np.max(step)),
        "hf_ratio": hf_ratio,
        "final_hz": final_hz,
        "final_err_hz": final_err,
        "settle_time_s": settle_time,
    }


def convergence_time(freq: np.ndarray, t: np.ndarray, target: float, tol: float, hold_sec: float) -> float:
    if freq.size < 2:
        return float("nan")

    err = np.abs(freq - target)
    dt = float(np.mean(np.diff(t))) if t.size > 1 else 0.01
    hold_samples = max(1, int(round(hold_sec / max(dt, 1.0e-6))))
    if err.size < hold_samples:
        return float("nan")

    within = (err <= tol).astype(int)
    window = np.ones(hold_samples, dtype=int)
    stable = np.convolve(within, window, mode="valid") >= hold_samples
    idx = np.where(stable)[0]
    if idx.size == 0:
        return float("nan")
    return float(t[int(idx[0])])


def plot_sweep(results: pd.DataFrame, out_png: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    for log, group in results.groupby("log"):
        ordered = group.sort_values("q_w")
        axes[0].plot(ordered["q_w"], ordered["settle_time_s"], marker="o", label=log)
        axes[1].plot(ordered["q_w"], ordered["mae_hz"], marker="o", label=log)

    for ax in axes:
        ax.set_xscale("log")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")

    axes[0].set_ylabel("Settle time [s]")
    axes[0].set_title("0.60 Hz init convergence sweep")
    axes[1].set_ylabel("MAE [Hz]")
    axes[1].set_xlabel("q_w")

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def pick_best(group: pd.DataFrame) -> pd.Series:
    ranked = group.copy()
    ranked["settle_sort"] = ranked["settle_time_s"].fillna(1.0e9)
    ranked["mae_sort"] = ranked["mae_hz"].fillna(1.0e9)
    return ranked.sort_values(["settle_sort", "mae_sort", "std_hz"]).iloc[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Sweep q_w for 0.60Hz initial value")
    parser.add_argument("--replay-bin", default=str(REPLAY_BIN))
    parser.add_argument("--outdir", default=str(OUTBASE))
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    runs_dir = outdir / "runs"
    fig_dir = outdir / "figures"
    runs_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    replay_bin = Path(args.replay_bin)
    rows: List[Dict[str, object]] = []
    run_map: Dict[str, Dict[str, str]] = {}

    for tag, src in INPUTS.items():
        csv_input = ensure_csv(src, runs_dir / tag)
        run_map[tag] = {}

        for q_w in Q_W_VALUES:
            run_tag = f"{tag}_init_{INIT_HZ:.2f}Hz_qw_{q_w:.0e}".replace(".", "p")
            run_dir = runs_dir / tag / f"qw_{q_w:.0e}".replace(".", "p")
            result_csv = run_replay(replay_bin, csv_input, run_dir, run_tag, q_w)
            run_map[tag][f"q_w={q_w:.0e}"] = str(result_csv)

            df = pd.read_csv(result_csv)
            t = df["Time_s"].to_numpy(dtype=float)
            sw = df["SW"].to_numpy(dtype=int)
            m = metrics(df["EstFreq_Hz"].to_numpy(dtype=float), t, sw)
            rows.append({"log": tag, "q_w": q_w, **m})

    result_df = pd.DataFrame(rows)
    result_df["score"] = result_df.apply(
        lambda row: (1.0e9 if math.isnan(float(row["settle_time_s"])) else float(row["settle_time_s"]))
        + 10.0 * float(row["mae_hz"])
        + 2.0 * float(row["std_hz"]),
        axis=1,
    )
    result_df.to_csv(outdir / "fixed_init_060_qw_sweep_metrics.csv", index=False)

    plot_sweep(result_df, outdir / "fixed_init_060_qw_sweep.png")

    per_log = {}
    for tag, group in result_df.groupby("log"):
        best = pick_best(group)
        per_log[tag] = {
            "best_q_w": float(best["q_w"]),
            "best_settle_time_s": float(best["settle_time_s"]),
            "best_mae_hz": float(best["mae_hz"]),
            "best_final_err_hz": float(best["final_err_hz"]),
        }

    ranked = result_df.copy()
    ranked["settle_sort"] = ranked["settle_time_s"].fillna(1.0e9)
    ranked["mae_sort"] = ranked["mae_hz"].fillna(1.0e9)
    ranked = ranked.sort_values(["settle_sort", "mae_sort", "std_hz"])

    report = []
    report.append("# 0.60 Hz Initial Convergence Sweep")
    report.append("")
    report.append("- initial frequency: 0.60 Hz")
    report.append(f"- target frequency: {TARGET_HZ:.2f} Hz")
    report.append(f"- settle band: ±{SETTLE_TOL_HZ:.2f} Hz for {SETTLE_HOLD_S:.1f} s")
    report.append("")
    report.append("## Ranked Results")
    report.append(ranked[["log", "q_w", "settle_time_s", "mae_hz", "std_hz", "final_err_hz", "p95_step_hz", "max_step_hz"]].to_string(index=False))
    report.append("")
    report.append("## Per-log Best")
    report.append(json.dumps(per_log, indent=2))
    report.append("")
    report.append("## Interpretation")
    report.append("- Larger q_w values reduce the memory of the 0.60 Hz starting point.")
    report.append("- The best setting is the one that both enters the 0.45 Hz band quickly and keeps the final error small.")
    report.append("- If the best q_w still leaves a noticeable final bias, the filter is stable but not fast enough to forget its initial value.")

    report_path = outdir / "FIXED_INIT_060_QW_SWEEP_REPORT_2026-04-05.md"
    report_path.write_text("\n".join(report), encoding="utf-8")

    summary = {
        "target_hz": TARGET_HZ,
        "init_hz": INIT_HZ,
        "settle_tol_hz": SETTLE_TOL_HZ,
        "settle_hold_s": SETTLE_HOLD_S,
        "result_csv": str(outdir / "fixed_init_060_qw_sweep_metrics.csv"),
        "report": str(report_path),
        "per_log_best": per_log,
        "run_map": run_map,
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Wrote {outdir / 'fixed_init_060_qw_sweep_metrics.csv'}")
    print(f"Wrote {report_path}")
    print(f"Wrote {outdir / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())