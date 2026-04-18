#!/usr/bin/env python3
"""Sweep non-frequency EKF Q/R ratio on concatenated replay input.

Frequency-estimation settings are fixed. Only state estimation (Q_D/Q_DD/Q_C/R_MEAS)
is changed per ratio to evaluate X-axis smoothing behavior.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import subprocess
import zoneinfo
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports"
REPLAY_BIN = REPO_ROOT / "build/sitl/examples/EKF_CSV_Replay"

CONCAT_INPUT = (
    REPORT_DIR
    / "results/2026-04-16_robust_smooth_m30_concat_direct_replay/concat_input/00000443_00000444_concat_input.csv"
)

BASE_Q_D = 0.02
BASE_Q_DD = 0.05
BASE_Q_C = 0.001
BASE_R_MEAS = 0.08

FIXED_Q_W = 1.0e-6
FIXED_SH_BETA = 0.10


@dataclass
class SweepCase:
    name: str
    factor: float


CASES: List[SweepCase] = [
    SweepCase("stateqr_x1", 1.0),
    SweepCase("stateqr_x2", 2.0),
    SweepCase("stateqr_x4", 4.0),
    SweepCase("stateqr_x8", 8.0),
]


def run_replay(case: SweepCase, out_replay_dir: Path) -> Path:
    q_d = BASE_Q_D / case.factor
    q_dd = BASE_Q_DD / case.factor
    q_c = BASE_Q_C / case.factor
    r_meas = BASE_R_MEAS * case.factor

    tag = f"00000443_00000444_concat_{case.name}"
    cmd = [
        str(REPLAY_BIN),
        "--input",
        str(CONCAT_INPUT),
        "--outdir",
        str(out_replay_dir),
        "--tag",
        tag,
        "--sw-mode",
        "always-on",
        "--ekf-axis-mask",
        "3",
        "--ekf-energy-gate",
        "1",
        "--ekf-energy-rms-on",
        "0.20",
        "--ekf-energy-rms-off",
        "0.16",
        "--ekf-energy-tau",
        "2.0",
        "--ekf-robust-update",
        "1",
        "--ekf-robust-nis-reject",
        "3.0",
        "--ekf-q-w",
        f"{FIXED_Q_W}",
        "--ekf-sh-beta",
        f"{FIXED_SH_BETA}",
        "--ekf-innov-max",
        "0.70",
        "--ekf-nis-max",
        "4.00",
        "--ekf-q-d",
        f"{q_d}",
        "--ekf-q-dd",
        f"{q_dd}",
        "--ekf-q-c",
        f"{q_c}",
        "--ekf-r-meas",
        f"{r_meas}",
    ]
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)
    return out_replay_dir / f"{tag}_result.csv"


def read_result_csv(path: Path) -> Dict[str, np.ndarray]:
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))

    def col(name: str) -> np.ndarray:
        return np.array([float(r[name]) for r in rows], dtype=float)

    return {
        "t": col("Time_s"),
        "plx": col("PLX"),
        "prx": col("PRX"),
        "est_hz": col("EstFreq_Hz"),
    }


def plot_x_axis(out_png: Path, t: np.ndarray, raw: np.ndarray, est: np.ndarray, title: str) -> None:
    fig, ax = plt.subplots(figsize=(13, 4.6))
    ax.plot(t, raw, color="0.72", linewidth=0.8, alpha=0.6, label="Raw X (PLX)")
    ax.plot(t, est, color="tab:blue", linewidth=1.3, label="Estimate X (PRX)")
    ax.set_title(title)
    ax.set_xlabel("Replay Time [s]")
    ax.set_ylabel("X-axis force")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_frequency(out_png: Path, t: np.ndarray, est_hz: np.ndarray, title: str) -> None:
    fig, ax = plt.subplots(figsize=(13, 3.8))
    ax.plot(t, est_hz, color="tab:purple", linewidth=1.2, label="EstFreq_Hz")
    ax.axhline(0.454, color="tab:green", linestyle=":", linewidth=1.0, label="Target=0.454 Hz")
    ax.set_title(title)
    ax.set_xlabel("Replay Time [s]")
    ax.set_ylabel("Frequency [Hz]")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep state EKF Q/R ratio on concatenated replay")
    parser.add_argument("--date", type=str, default="", help="Override date folder (YYYY-MM-DD)")
    args = parser.parse_args()

    if not REPLAY_BIN.exists():
        raise RuntimeError(f"Replay binary not found: {REPLAY_BIN}")
    if not CONCAT_INPUT.exists():
        raise RuntimeError(f"Concatenated input CSV not found: {CONCAT_INPUT}")

    jst = zoneinfo.ZoneInfo("Asia/Tokyo")
    now = datetime.datetime.now(jst)
    date_str = args.date if args.date else now.strftime("%Y-%m-%d")
    ts = now.strftime("%H-%M-%S")

    result_root = REPORT_DIR / f"results/{date_str}_state_qr_sweep_concat"
    replay_dir = result_root / "replay"
    fig_dir = result_root / "figures"
    replay_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    report_path = REPORT_DIR / f"{date_str}_{ts}_X軸平滑化_非周波数EKF比スイープ_連結リプレイ検証.md"

    rows: List[str] = []
    rows.append(f"# {date_str} X軸平滑化: 非周波数EKF比スイープ（連結リプレイ）")
    rows.append("")
    rows.append(f"**作成日時（JST）: {now.strftime('%Y-%m-%d %H:%M:%S')}**")
    rows.append("")
    rows.append("## 目的")
    rows.append("- 周波数推定は現行採用値（R/Q x10相当）で固定し、X軸推定(PRX)のノイズをさらに平滑化できるか検証する。")
    rows.append("- 周波数推定パラメータと、それ以外のEKFパラメータを分離して評価する。")
    rows.append("")
    rows.append("## 固定設定（周波数推定系）")
    rows.append(f"- `EKF_Q_W={FIXED_Q_W}`")
    rows.append(f"- `EKF_SH_BETA={FIXED_SH_BETA}`")
    rows.append("- `SW mode=always-on`")
    rows.append("- `robust update=ON`, `NIS reject=3.0`")
    rows.append("")
    rows.append("## スイープ設定（非周波数EKF系）")
    rows.append("- 基準: `Q_D=0.02`, `Q_DD=0.05`, `Q_C=0.001`, `R_MEAS=0.08`")
    rows.append("- 係数 `k` に対して、`Q_D/Q_DD/Q_C` を `1/k`、`R_MEAS` を `k` 倍に設定（状態推定のR/Qを増加）。")
    rows.append("")
    rows.append("| case | k | Q_D | Q_DD | Q_C | R_MEAS |")
    rows.append("|---|---:|---:|---:|---:|---:|")
    for c in CASES:
        rows.append(
            f"| {c.name} | {c.factor:.1f} | {BASE_Q_D / c.factor:.8g} | {BASE_Q_DD / c.factor:.8g} | {BASE_Q_C / c.factor:.8g} | {BASE_R_MEAS * c.factor:.8g} |"
        )

    rows.append("")
    rows.append("## 結果サマリ")
    rows.append("")
    rows.append("| case | X RMSE | X MAE | PRX std | std(diff(PRX)) | p95(|diff(PRX)|) | max(|diff(PRX)|) | EstFreq std [Hz] | EstFreq p95 step [Hz] |")
    rows.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")

    for c in CASES:
        csv_path = run_replay(c, replay_dir)
        d = read_result_csv(csv_path)

        prx_diff = np.abs(np.diff(d["prx"]))
        est_diff = np.abs(np.diff(d["est_hz"]))
        x_rmse = float(np.sqrt(np.mean((d["plx"] - d["prx"]) ** 2)))
        x_mae = float(np.mean(np.abs(d["plx"] - d["prx"])))

        rows.append(
            "| "
            + f"{c.name} | {x_rmse:.6f} | {x_mae:.6f} | {np.std(d['prx']):.6f} | {np.std(np.diff(d['prx'])):.6f} | {np.percentile(prx_diff, 95):.6f} | {np.max(prx_diff):.6f} | {np.std(d['est_hz']):.6f} | {np.percentile(est_diff, 95):.6f} |"
        )

        x_png = fig_dir / f"{c.name}_x_raw_vs_est.png"
        f_png = fig_dir / f"{c.name}_frequency.png"
        plot_x_axis(
            x_png,
            d["t"],
            d["plx"],
            d["prx"],
            title=(
                f"{c.name}: X raw vs estimate "
                f"(Q_D={BASE_Q_D / c.factor:.4g}, Q_DD={BASE_Q_DD / c.factor:.4g}, "
                f"Q_C={BASE_Q_C / c.factor:.4g}, R_MEAS={BASE_R_MEAS * c.factor:.4g})"
            ),
        )
        plot_frequency(
            f_png,
            d["t"],
            d["est_hz"],
            title=f"{c.name}: Frequency estimate (fixed Q_W={FIXED_Q_W}, SH_BETA={FIXED_SH_BETA})",
        )

        rows.append("")
        rows.append(f"### {c.name}")
        rows.append(f"- 結果CSV: `{csv_path.relative_to(REPO_ROOT)}`")
        rows.append(f"- X図: ![{c.name} x](results/{date_str}_state_qr_sweep_concat/figures/{c.name}_x_raw_vs_est.png)")
        rows.append(f"- 周波数図: ![{c.name} frequency](results/{date_str}_state_qr_sweep_concat/figures/{c.name}_frequency.png)")

    rows.append("")
    rows.append("## 判定の見方")
    rows.append("- X軸平滑化は `std(diff(PRX))` / `p95(|diff(PRX)|)` / `max(|diff(PRX)|)` を優先。")
    rows.append("- 周波数推定への副作用は `EstFreq std` / `EstFreq p95 step` で確認。")

    report_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Wrote report: {report_path}")


if __name__ == "__main__":
    main()
