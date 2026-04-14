#!/usr/bin/env python3
"""Tune EKF smoothing parameters (without changing frequency settings) and generate X-axis report."""

from __future__ import annotations

import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
REPLAY_BIN = REPO_ROOT / "build/sitl/examples/RLS_CSV_Replay"

RESULT_ROOT = REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports/results/2026-04-14_観測値ゼロ強制_平滑化調整"
REPORT_PATH = REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports/2026-04-14_20:30_X軸推定値_平滑化パラメータ比較.md"


@dataclass
class Case:
    tag: str
    input_csv: Path


@dataclass
class Preset:
    name: str
    q_d: float
    q_dd: float
    q_c: float
    r_meas: float


CASES: List[Case] = [
    Case(
        tag="00000443_w35_100",
        input_csv=REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports/2026-04-13_443_444リプレイ検証_model_strong/00000443_w35_100_input.csv",
    ),
    Case(
        tag="00000444_w40_110",
        input_csv=REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports/2026-04-13_443_444リプレイ検証_model_strong/00000444_w40_110_input.csv",
    ),
]


# Frequency-related settings are intentionally kept fixed.
PRESETS: List[Preset] = [
    Preset("base", q_d=0.020, q_dd=0.050, q_c=0.00100, r_meas=0.080),
    Preset("smooth_l1", q_d=0.015, q_dd=0.035, q_c=0.00070, r_meas=0.100),
    Preset("smooth_l2", q_d=0.010, q_dd=0.020, q_c=0.00040, r_meas=0.120),
    Preset("smooth_l3", q_d=0.007, q_dd=0.012, q_c=0.00025, r_meas=0.150),
    Preset("smooth_l4", q_d=0.004, q_dd=0.008, q_c=0.00015, r_meas=0.200),
    Preset("smooth_l5", q_d=0.002, q_dd=0.004, q_c=0.00008, r_meas=0.300),
    Preset("smooth_l6", q_d=0.0012, q_dd=0.0025, q_c=0.00005, r_meas=0.450),
    Preset("smooth_l7", q_d=0.0008, q_dd=0.0015, q_c=0.00003, r_meas=0.600),
]


def run_cmd(cmd: List[str]) -> None:
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)


def read_csv_columns(csv_path: Path) -> Dict[str, np.ndarray]:
    with csv_path.open(newline="") as f:
        rows = list(csv.DictReader(f))

    def col(name: str) -> np.ndarray:
        return np.array([float(r[name]) for r in rows], dtype=float)

    return {
        "t": col("Time_s"),
        "plx": col("PLX"),
        "prx": col("PRX"),
        "est_hz": col("EstFreq_Hz"),
        "real_hz": col("RealFreq_Hz"),
    }


def to_report_rel(path: Path) -> str:
    return str(path.relative_to(REPORT_PATH.parent))


def smooth_metric(sig: np.ndarray) -> float:
    if sig.size < 2:
        return float("nan")
    return float(np.std(np.diff(sig)))


def estimate_delay_seconds(plx: np.ndarray, prx: np.ndarray, dt: float, max_lag_s: float = 2.0) -> float:
    """Estimate PRX delay against PLX. Positive value means PRX is delayed."""
    if plx.size < 4 or prx.size < 4 or dt <= 0.0:
        return float("nan")

    max_lag = min(int(max_lag_s / dt), plx.size - 2)
    if max_lag < 1:
        return 0.0

    best_lag = 0
    best_corr = -1.0

    for lag in range(-max_lag, max_lag + 1):
        if lag > 0:
            ref = plx[:-lag]
            est = prx[lag:]
        elif lag < 0:
            shift = -lag
            ref = plx[shift:]
            est = prx[:-shift]
        else:
            ref = plx
            est = prx

        if ref.size < 8:
            continue

        ref_c = ref - np.mean(ref)
        est_c = est - np.mean(est)
        denom = float(np.linalg.norm(ref_c) * np.linalg.norm(est_c))
        if denom <= 1e-12:
            continue

        corr = float(np.dot(ref_c, est_c) / denom)
        if corr > best_corr:
            best_corr = corr
            best_lag = lag

    return float(best_lag * dt)


def run_case_preset(case: Case, preset: Preset) -> Path:
    run_dir = RESULT_ROOT / case.tag / preset.name
    run_dir.mkdir(parents=True, exist_ok=True)

    out_tag = f"{case.tag}_{preset.name}"
    cmd = [
        str(REPLAY_BIN),
        "--input",
        str(case.input_csv),
        "--outdir",
        str(run_dir),
        "--tag",
        out_tag,
        "--sw-mode",
        "log",
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
        "--ekf-q-d",
        f"{preset.q_d}",
        "--ekf-q-dd",
        f"{preset.q_dd}",
        "--ekf-q-c",
        f"{preset.q_c}",
        "--ekf-r-meas",
        f"{preset.r_meas}",
    ]
    run_cmd(cmd)
    return run_dir / f"{out_tag}_result.csv"


def plot_prx_only(case_tag: str, preset: Preset, t: np.ndarray, prx: np.ndarray) -> Path:
    fig_dir = RESULT_ROOT / "comparison/figures_prx_only"
    fig_dir.mkdir(parents=True, exist_ok=True)
    out_png = fig_dir / f"{case_tag}_{preset.name}_prx_only.png"

    fig, ax = plt.subplots(figsize=(14, 4))
    ax.plot(t, prx, color="tab:orange", linewidth=1.0, label=f"PRX ({preset.name})")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("PRX")
    ax.set_title(f"{case_tag} - PRX Estimate Only ({preset.name})")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_png


def plot_raw_only(case_tag: str, t: np.ndarray, plx: np.ndarray) -> Path:
    fig_dir = RESULT_ROOT / "comparison/figures_raw_only"
    fig_dir.mkdir(parents=True, exist_ok=True)
    out_png = fig_dir / f"{case_tag}_raw_plx_only.png"

    fig, ax = plt.subplots(figsize=(14, 3.5))
    ax.plot(t, plx, color="black", linewidth=1.0, label="PLX raw")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("PLX")
    ax.set_title(f"{case_tag} - Raw X-axis Data (PLX) Only")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_png


def main() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    lines.append("# 2026-04-14 X軸推定値 平滑化パラメータ比較（周波数設定固定）")
    lines.append("")
    lines.append("## 方針")
    lines.append("- 周波数推定に関わる設定（`OBS_EKF_Q_W`, 初期周波数）は変更しない。")
    lines.append("- 平滑化寄与が大きい `Q_D`, `Q_DD`, `Q_C`, `R_MEAS` を段階的に調整する。")
    lines.append("- 生データ（PLX）のみの図を追加し、遅れ（ラグ）と合わせて比較する。")
    lines.append("- 各設定で X軸推定値（PRX）を可視化し、より強い平滑化プリセットも試行する。")
    lines.append("")

    lines.append("## 調整プリセット")
    lines.append("")
    lines.append("| preset | Q_D | Q_DD | Q_C | R_MEAS |")
    lines.append("|---|---:|---:|---:|---:|")
    for p in PRESETS:
        lines.append(f"| {p.name} | {p.q_d:.6f} | {p.q_dd:.6f} | {p.q_c:.6f} | {p.r_meas:.6f} |")
    lines.append("")

    for case in CASES:
        metrics_rows: List[str] = []
        figs: List[tuple[str, Path]] = []
        raw_fig: Path | None = None
        for p in PRESETS:
            result_csv = run_case_preset(case, p)
            d = read_csv_columns(result_csv)
            if raw_fig is None:
                raw_fig = plot_raw_only(case.tag, d["t"], d["plx"])

            prx_smooth = smooth_metric(d["prx"])
            freq_mae = float(np.mean(np.abs(d["est_hz"] - d["real_hz"])))
            dt = float(np.median(np.diff(d["t"]))) if d["t"].size >= 2 else float("nan")
            delay_ms = estimate_delay_seconds(d["plx"], d["prx"], dt) * 1000.0
            metrics_rows.append(f"| {p.name} | {prx_smooth:.6f} | {freq_mae:.6f} | {delay_ms:.1f} |")
            figs.append((p.name, plot_prx_only(case.tag, p, d["t"], d["prx"])))

        lines.append(f"## {case.tag}")
        lines.append("")
        lines.append("### Raw Data Only (PLX)")
        lines.append("")
        if raw_fig is not None:
            lines.append(f"![{case.tag} raw plx only]({to_report_rel(raw_fig)})")
            lines.append("")

        lines.append("### 指標サマリ")
        lines.append("")
        lines.append("| preset | PRX差分標準偏差（小さいほど滑らか） | 周波数MAE[Hz] | PRX遅れ[ms]（+は遅れ） |")
        lines.append("|---|---:|---:|---:|")
        lines.extend(metrics_rows)
        lines.append("")
        lines.append("### PRX Estimate by Preset")
        lines.append("")
        for preset_name, fig_path in figs:
            lines.append(f"#### {preset_name}")
            lines.append("")
            lines.append(f"![{case.tag} {preset_name} prx only]({to_report_rel(fig_path)})")
            lines.append("")

    lines.append("## 結論（暫定）")
    lines.append("")
    lines.append("- `smooth_l1 -> smooth_l2 -> smooth_l3 -> smooth_l4 -> smooth_l5 -> smooth_l6 -> smooth_l7` と進むほど、PRX差分標準偏差は段階的に低下しやすい。")
    lines.append("- 周波数推定設定は固定しているため、周波数系のチューニング方針には影響を与えない。")
    lines.append("- 一方で平滑化を強めるほど遅れが増える可能性があるため、遅れ指標も同時に確認して採用設定を決める。")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
