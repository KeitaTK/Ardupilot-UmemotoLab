#!/usr/bin/env python3
"""Run replay validation for measurement-zero deadband strategy and generate comparison artifacts."""

from __future__ import annotations

import csv
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
REPLAY_BIN = REPO_ROOT / "build/sitl/examples/EKF_CSV_Replay"
PLOT_SCRIPT = REPO_ROOT / "analysis/replay/plot_replay_results.py"

OLD_BASE = REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports/2026-04-13_443_444リプレイ検証_model_strong"
NEW_BASE = REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports/results/2026-04-14_観測値ゼロ強制_結果"

COMMON_ARGS: List[str] = []


@dataclass
class Case:
    tag: str
    input_csv: Path
    variant: str
    old_result_csv: Path


def run_cmd(cmd: List[str]) -> None:
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)


def read_result_metrics(csv_path: Path) -> Dict[str, float]:
    with csv_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    t = np.array([float(r["Time_s"]) for r in rows], dtype=float)
    plx = np.array([float(r["PLX"]) for r in rows], dtype=float)
    prx = np.array([float(r["PRX"]) for r in rows], dtype=float)
    est = np.array([float(r["EstFreq_Hz"]) for r in rows], dtype=float)
    real = np.array([float(r["RealFreq_Hz"]) for r in rows], dtype=float)

    rmse = float(np.sqrt(np.mean((plx - prx) ** 2)))
    corr = float(np.corrcoef(plx, prx)[0, 1])
    plx_diff_std = float(np.std(np.diff(plx)))
    prx_diff_std = float(np.std(np.diff(prx)))
    smooth_ratio = prx_diff_std / plx_diff_std if plx_diff_std > 0.0 else float("nan")

    freq_err = np.abs(est - real)
    return {
        "samples": float(len(rows)),
        "duration_s": float(t[-1] - t[0]),
        "rmse": rmse,
        "corr": corr,
        "smooth_ratio": float(smooth_ratio),
        "freq_mae_hz": float(np.mean(freq_err)),
        "freq_max_hz": float(np.max(freq_err)),
    }


def plot_old_vs_new_xaxis(old_csv: Path, new_csv: Path, out_png: Path, title: str) -> None:
    def load(path: Path):
        with path.open(newline="") as f:
            rows = list(csv.DictReader(f))
        t = np.array([float(r["Time_s"]) for r in rows], dtype=float)
        plx = np.array([float(r["PLX"]) for r in rows], dtype=float)
        prx = np.array([float(r["PRX"]) for r in rows], dtype=float)
        return t, plx, prx

    t_old, plx_old, prx_old = load(old_csv)
    t_new, plx_new, prx_new = load(new_csv)

    # Old result CSV keeps absolute window time (e.g. 35-100s), while new replay output
    # starts from 0s. Align both onto the same relative window timeline for fair overlay.
    t_old_rel = t_old - t_old[0]
    t_new_rel = t_new - t_new[0]

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    axes[0].plot(t_old_rel, plx_old, color="tab:gray", linewidth=0.8, alpha=0.8, label="PLX (same input)")
    axes[0].plot(t_old_rel, prx_old, color="tab:blue", linewidth=1.0, label="PRX 2026-04-13 baseline")
    axes[0].plot(t_new_rel, prx_new, color="tab:green", linewidth=1.0, label="PRX 2026-04-14 measurement=0")
    axes[0].set_ylabel("Force proxy")
    axes[0].set_title(f"{title}: X-axis waveform (aligned to window-relative time)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="upper right")

    axes[1].plot(t_old_rel, plx_old - prx_old, color="tab:blue", linewidth=0.9, label="Residual 2026-04-13 baseline")
    axes[1].plot(t_new_rel, plx_new - prx_new, color="tab:green", linewidth=0.9, label="Residual 2026-04-14 measurement=0")
    axes[1].set_xlabel("Time from window start [s]")
    axes[1].set_ylabel("PLX - PRX")
    axes[1].set_title("Residual comparison")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="upper right")

    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    NEW_BASE.mkdir(parents=True, exist_ok=True)

    cases = [
        Case(
            tag="00000443_w35_100",
            input_csv=OLD_BASE / "00000443_w35_100_input.csv",
            variant="standard_fix",
            old_result_csv=REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports/2026-04-13_443_444リプレイ検証/00000443_w35_100/00000443_recheck__w35_100_windowed.csv",
        ),
        Case(
            tag="00000444_w40_110",
            input_csv=OLD_BASE / "00000444_w40_110_input.csv",
            variant="standard_fix",
            old_result_csv=REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports/2026-04-13_443_444リプレイ検証/00000444_w40_110/00000444_recheck__w40_110_windowed.csv",
        ),
    ]

    metric_rows: List[Dict[str, float | str]] = []

    for c in cases:
        run_dir = NEW_BASE / f"{c.tag}_{c.variant}"
        run_dir.mkdir(parents=True, exist_ok=True)

        replay_cmd = [
            str(REPLAY_BIN),
            "--input",
            str(c.input_csv),
            "--outdir",
            str(run_dir),
            "--tag",
            f"{c.tag}_{c.variant}",
            *COMMON_ARGS,
        ]
        run_cmd(replay_cmd)

        result_csv = run_dir / f"{c.tag}_{c.variant}_result.csv"
        plot_cmd = [
            sys.executable,
            str(PLOT_SCRIPT),
            "--input",
            str(result_csv),
            "--outdir",
            str(run_dir / "plots"),
            "--title",
            f"{c.tag}_{c.variant}",
        ]
        run_cmd(plot_cmd)

        old_m = read_result_metrics(c.old_result_csv)
        new_m = read_result_metrics(result_csv)

        metric_rows.append(
            {
                "case": c.tag,
                "variant_old": "standard_old",
                "variant_new": c.variant,
                "rmse_old": old_m["rmse"],
                "rmse_new": new_m["rmse"],
                "rmse_delta_new_minus_old": new_m["rmse"] - old_m["rmse"],
                "corr_old": old_m["corr"],
                "corr_new": new_m["corr"],
                "corr_delta_new_minus_old": new_m["corr"] - old_m["corr"],
                "smooth_ratio_old": old_m["smooth_ratio"],
                "smooth_ratio_new": new_m["smooth_ratio"],
                "smooth_ratio_delta_new_minus_old": new_m["smooth_ratio"] - old_m["smooth_ratio"],
                "freq_mae_old_hz": old_m["freq_mae_hz"],
                "freq_mae_new_hz": new_m["freq_mae_hz"],
                "freq_mae_delta_new_minus_old_hz": new_m["freq_mae_hz"] - old_m["freq_mae_hz"],
                "freq_max_old_hz": old_m["freq_max_hz"],
                "freq_max_new_hz": new_m["freq_max_hz"],
                "freq_max_delta_new_minus_old_hz": new_m["freq_max_hz"] - old_m["freq_max_hz"],
            }
        )

        fig_path = NEW_BASE / "comparison/figures" / f"{c.tag}_xaxis_old_vs_fix_standard.png"
        plot_old_vs_new_xaxis(c.old_result_csv, result_csv, fig_path, f"{c.tag} standard")

    comparison_dir = NEW_BASE / "comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    out_csv = comparison_dir / "metrics_old_vs_fix.csv"
    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(metric_rows[0].keys()))
        writer.writeheader()
        writer.writerows(metric_rows)

    print(f"Wrote {out_csv}")


if __name__ == "__main__":
    main()
