#!/usr/bin/env python3
from __future__ import annotations
"""Generate X/Y overlay figures and a markdown report from current EKF replay results."""

def plot_prx_only(t: np.ndarray, prx: np.ndarray, axis_name: str, title: str, out_png: Path) -> None:
    axis_upper = axis_name.upper()
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.plot(t, prx, color="tab:orange", linewidth=1.0, label=f"推定値 PR{axis_upper}")
    ax.set_ylabel(f"PR{axis_upper}")
    ax.set_xlabel("Time [s]")
    ax.set_title(f"{title} - {axis_upper}軸 推定値のみ")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import datetime
import zoneinfo


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports/results/2026-04-14_観測値ゼロ強制_結果"
REPORT_PATH = REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports/2026-04-14_18:30_XY軸重ね合わせ_観測値ゼロ強制リプレイ.md"
FIG_DIR = RESULT_ROOT / "comparison/figures_xy_overlay"


@dataclass
class Case:
    tag: str
    result_csv: Path


def read_result_csv(path: Path) -> Dict[str, np.ndarray]:
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))

    def col(name: str) -> np.ndarray:
        return np.array([float(r[name]) for r in rows], dtype=float)

    return {
        "t": col("Time_s"),
        "plx": col("PLX"),
        "ply": col("PLY"),
        "prx": col("PRX"),
        "pry": col("PRY"),
    }


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


def corr(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3:
        return float("nan")
    if float(np.std(a)) == 0.0 or float(np.std(b)) == 0.0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def plot_single_axis(t: np.ndarray, meas: np.ndarray, recon: np.ndarray, axis_name: str, title: str, out_png: Path) -> Tuple[float, float]:
    axis_upper = axis_name.upper()
    e = meas - recon
    axis_rmse = rmse(meas, recon)
    axis_corr = corr(meas, recon)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    axes[0].plot(t, meas, color="tab:blue", linewidth=0.9, label=f"Original {axis_upper} (PL{axis_upper})")
    axes[0].plot(t, recon, color="tab:orange", linewidth=1.0, label=f"Reconstructed {axis_upper} (PR{axis_upper})")
    axes[0].set_ylabel("Force proxy")
    axes[0].set_title(f"{title} - {axis_upper} axis overlay")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="upper right")

    axes[1].plot(t, e, color="tab:red", linewidth=0.9, label=f"Residual PL{axis_upper}-PR{axis_upper}")
    axes[1].set_xlabel("Time [s]")
    axes[1].set_ylabel("Residual")
    axes[1].set_title(f"Residual (RMSE={axis_rmse:.4f}, Corr={axis_corr:.4f})")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="upper right")

    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return axis_rmse, axis_corr


def to_repo_rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def main() -> None:
    cases: List[Case] = [
        Case(
            tag="00000443_w35_100_standard_fix",
            result_csv=RESULT_ROOT / "00000443_w35_100_standard_fix/00000443_w35_100_standard_fix_result.csv",
        ),
        Case(
            tag="00000444_w40_110_standard_fix",
            result_csv=RESULT_ROOT / "00000444_w40_110_standard_fix/00000444_w40_110_standard_fix_result.csv",
        ),
    ]

    # JSTでの現在時刻を取得し、レポート先頭に追加
    jst = zoneinfo.ZoneInfo("Asia/Tokyo")
    now_jst = datetime.datetime.now(jst)
    dt_str = now_jst.strftime("%Y-%m-%d %H:%M:%S")

    lines: List[str] = []
    lines.append(f"# 2026-04-14 XY軸重ね合わせ 観測値ゼロ強制リプレイ\n\n**作成日時（JST）: {dt_str}**\n")
    lines.append("---")
    lines.append("")
    lines.append("## Purpose")
    lines.append("This report overlays original replay signals and EKF-reconstructed signals for X and Y axes separately.")
    lines.append("")
    lines.append("## Data Source")
    lines.append("- Current EKF replay outputs under results/2026-04-14_観測値ゼロ強制_結果")
    lines.append("- Signals: PLX/PLY (original), PRX/PRY (reconstructed)")
    lines.append("")

    for c in cases:
        data = read_result_csv(c.result_csv)
        t = data["t"]

        x_png = FIG_DIR / f"{c.tag}_x_overlay.png"
        y_png = FIG_DIR / f"{c.tag}_y_overlay.png"

        x_prx_only_png = FIG_DIR / f"{c.tag}_x_prx_only.png"

        x_rmse, x_corr = plot_single_axis(t, data["plx"], data["prx"], "x", c.tag, x_png)
        y_rmse, y_corr = plot_single_axis(t, data["ply"], data["pry"], "y", c.tag, y_png)

        plot_prx_only(t, data["prx"], "x", c.tag, x_prx_only_png)

        lines.append(f"## {c.tag}")
        lines.append("")
        lines.append(f"- 結果CSV: `{to_repo_rel(c.result_csv)}`")
        x_corr_text = f"{x_corr:.6f}" if np.isfinite(x_corr) else "N/A"
        y_corr_text = f"{y_corr:.6f}" if np.isfinite(y_corr) else "N/A"
        lines.append(f"- X軸指標: RMSE = {x_rmse:.6f}、相関係数 = {x_corr_text}")
        lines.append(f"- Y軸指標: RMSE = {y_rmse:.6f}、相関係数 = {y_corr_text}")
        if not np.any(np.abs(data["pry"]) > 1.0e-12):
            lines.append("- 備考: 現在のEKFリプレイ出力では `PRY` が全サンプルで 0 の定数になっています。")
        lines.append("")
        lines.append("### X軸（元データと推定値の重ね合わせ）")
        lines.append("")
        lines.append(f"![{c.tag} x overlay]({to_repo_rel(x_png)})")
        lines.append("")
        lines.append("#### X軸（推定値のみ）")
        lines.append("")
        lines.append(f"![{c.tag} x prx only]({to_repo_rel(x_prx_only_png)})")
        lines.append("")
        lines.append("### Y軸")
        lines.append("")
        lines.append(f"![{c.tag} y overlay]({to_repo_rel(y_png)})")
        lines.append("")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
