#!/usr/bin/env python3
"""Generate a concatenated replay report for Robust + Smooth M30 (443 then 444)."""

from __future__ import annotations

import csv
import datetime
import zoneinfo
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports"
RESULT_ROOT = REPORT_DIR / "results/2026-04-15_robust_smooth_m30_concat"


@dataclass
class Case:
    tag: str
    result_csv: Path


CASES: List[Case] = [
    Case(
        tag="00000443_w35_100",
        result_csv=REPO_ROOT
        / "docs/experiments/ekf_external_force_estimation/reports/results/2026-04-15_robust_qr_smoothing/00000443_w35_100/smooth_m30/00000443_w35_100_smooth_m30_result.csv",
    ),
    Case(
        tag="00000444_w40_110",
        result_csv=REPO_ROOT
        / "docs/experiments/ekf_external_force_estimation/reports/results/2026-04-15_robust_qr_smoothing/00000444_w40_110/smooth_m30/00000444_w40_110_smooth_m30_result.csv",
    ),
]


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
        "est_hz": col("EstFreq_Hz"),
        "real_hz": col("RealFreq_Hz"),
    }


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


def mae(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a - b)))


def corr(a: np.ndarray, b: np.ndarray) -> float:
    if a.size < 3 or b.size < 3:
        return float("nan")
    if float(np.std(a)) <= 1.0e-12 or float(np.std(b)) <= 1.0e-12:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def concat_time_series(cases_data: List[Dict[str, np.ndarray]]) -> Dict[str, np.ndarray]:
    offsets: List[float] = []
    cur = 0.0
    for idx, d in enumerate(cases_data):
        if idx == 0:
            offsets.append(0.0)
            cur = float(d["t"][-1])
            continue
        dt_prev = float(np.median(np.diff(cases_data[idx - 1]["t"]))) if cases_data[idx - 1]["t"].size > 1 else 0.01
        start_offset = cur + dt_prev
        offsets.append(start_offset)
        cur = start_offset + float(d["t"][-1])

    def join(key: str) -> np.ndarray:
        if key == "t":
            return np.concatenate([d["t"] + off for d, off in zip(cases_data, offsets)])
        return np.concatenate([d[key] for d in cases_data])

    return {
        "t": join("t"),
        "plx": join("plx"),
        "ply": join("ply"),
        "prx": join("prx"),
        "pry": join("pry"),
        "est_hz": join("est_hz"),
        "real_hz": join("real_hz"),
        "offsets": np.array(offsets, dtype=float),
    }


def low_amp_metrics(raw: np.ndarray, est: np.ndarray, threshold: float) -> Dict[str, float]:
    mask = np.abs(raw) <= threshold
    n = int(np.sum(mask))
    if n == 0:
        return {
            "count": 0.0,
            "ratio": 0.0,
            "est_rms": float("nan"),
            "est_mae_to_zero": float("nan"),
            "est_within_thr_ratio": float("nan"),
        }

    est_low = est[mask]
    est_rms = float(np.sqrt(np.mean(est_low**2)))
    est_mae0 = float(np.mean(np.abs(est_low)))
    est_within_thr = float(np.mean(np.abs(est_low) <= threshold))
    return {
        "count": float(n),
        "ratio": float(n / raw.size),
        "est_rms": est_rms,
        "est_mae_to_zero": est_mae0,
        "est_within_thr_ratio": est_within_thr,
    }


def to_report_rel(report_path: Path, path: Path) -> str:
    return str(path.relative_to(report_path.parent))


def plot_axis_overlay(
    out_png: Path,
    t: np.ndarray,
    raw: np.ndarray,
    est: np.ndarray,
    threshold: float,
    split_t: float,
    title: str,
    y_label: str,
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    axes[0].plot(t, raw, color="0.35", linewidth=0.9, label="Raw (PL)")
    axes[0].plot(t, est, color="tab:blue", linewidth=1.1, label="Estimate (PR)")
    axes[0].axvline(split_t, color="tab:red", linestyle="--", linewidth=1.0, alpha=0.7, label="443/444 split")
    axes[0].set_ylabel(y_label)
    axes[0].set_title(title)
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="upper right")

    axes[1].plot(t, np.abs(raw), color="0.45", linewidth=0.9, label="|Raw|")
    axes[1].plot(t, np.abs(est), color="tab:orange", linewidth=1.0, label="|Estimate|")
    axes[1].axhline(threshold, color="tab:green", linestyle=":", linewidth=1.2, label=f"threshold={threshold:.3f}")
    axes[1].axvline(split_t, color="tab:red", linestyle="--", linewidth=1.0, alpha=0.7)
    axes[1].set_xlabel("Concatenated Time [s]")
    axes[1].set_ylabel("Absolute magnitude")
    axes[1].set_title("Low-amplitude and convergence-to-zero check")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="upper right")

    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_frequency(
    out_png: Path,
    t: np.ndarray,
    est_hz: np.ndarray,
    real_hz: np.ndarray,
    split_t: float,
    title: str,
) -> None:
    fig, ax = plt.subplots(figsize=(14, 4.8))
    ax.plot(t, real_hz, color="0.3", linewidth=1.0, linestyle="--", label="RealFreq_Hz")
    ax.plot(t, est_hz, color="tab:purple", linewidth=1.2, label="EstFreq_Hz")
    ax.axvline(split_t, color="tab:red", linestyle="--", linewidth=1.0, alpha=0.7, label="443/444 split")
    ax.set_xlabel("Concatenated Time [s]")
    ax.set_ylabel("Frequency [Hz]")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


def format_corr(v: float) -> str:
    return f"{v:.6f}" if np.isfinite(v) else "N/A"


def main() -> None:
    jst = zoneinfo.ZoneInfo("Asia/Tokyo")
    now = datetime.datetime.now(jst)
    report_name = now.strftime("%Y-%m-%d_%H:%M:%S_ロバスト観測更新_Robust+SmoothM30_連結リプレイ検証.md")
    report_path = REPORT_DIR / report_name

    threshold = 0.10

    cases_data = [read_result_csv(c.result_csv) for c in CASES]
    concat = concat_time_series(cases_data)
    split_t = float(concat["offsets"][1])

    fig_dir = RESULT_ROOT / "figures"
    x_png = fig_dir / "concat_x_raw_vs_est.png"
    y_png = fig_dir / "concat_y_raw_vs_est.png"
    f_png = fig_dir / "concat_frequency_est_vs_real.png"

    plot_axis_overlay(
        x_png,
        concat["t"],
        concat["plx"],
        concat["prx"],
        threshold,
        split_t,
        "Robust + Smooth M30: X-axis (443 -> 444 concatenated)",
        "X-axis force",
    )
    plot_axis_overlay(
        y_png,
        concat["t"],
        concat["ply"],
        concat["pry"],
        threshold,
        split_t,
        "Robust + Smooth M30: Y-axis (443 -> 444 concatenated)",
        "Y-axis force",
    )
    plot_frequency(
        f_png,
        concat["t"],
        concat["est_hz"],
        concat["real_hz"],
        split_t,
        "Robust + Smooth M30: Frequency estimate (443 -> 444 concatenated)",
    )

    case_metrics: List[Dict[str, float]] = []
    for case, d in zip(CASES, cases_data):
        case_metrics.append(
            {
                "tag": case.tag,
                "x_rmse": rmse(d["plx"], d["prx"]),
                "x_mae": mae(d["plx"], d["prx"]),
                "x_corr": corr(d["plx"], d["prx"]),
                "y_rmse": rmse(d["ply"], d["pry"]),
                "y_mae": mae(d["ply"], d["pry"]),
                "y_corr": corr(d["ply"], d["pry"]),
                "freq_mae": mae(d["est_hz"], d["real_hz"]),
            }
        )

    concat_metrics = {
        "x_rmse": rmse(concat["plx"], concat["prx"]),
        "x_mae": mae(concat["plx"], concat["prx"]),
        "x_corr": corr(concat["plx"], concat["prx"]),
        "y_rmse": rmse(concat["ply"], concat["pry"]),
        "y_mae": mae(concat["ply"], concat["pry"]),
        "y_corr": corr(concat["ply"], concat["pry"]),
        "freq_mae": mae(concat["est_hz"], concat["real_hz"]),
    }

    low_x_concat = low_amp_metrics(concat["plx"], concat["prx"], threshold)
    low_y_concat = low_amp_metrics(concat["ply"], concat["pry"], threshold)

    lines: List[str] = []
    lines.append(f"# {now.strftime('%Y-%m-%d')} Robust + Smooth M30 連結リプレイ検証（443 -> 444）")
    lines.append("")
    lines.append(f"**作成日時（JST）: {now.strftime('%Y-%m-%d %H:%M:%S')}**")
    lines.append("")
    lines.append("## 目的")
    lines.append("- `Robust + Smooth M30` の2リプレイ結果（443, 444）を前後連結し、単一の連続時系列として評価する。")
    lines.append("- X軸・Y軸それぞれで、生データ（PL）と推定値（PR）を比較する。")
    lines.append(f"- 閾値 `|PL| <= {threshold:.2f}` の低振幅区間で、推定値が0近傍へ収束するかを定量確認する。")
    lines.append("- 生データと周波数推定（EstFreq_Hz/RealFreq_Hz）の両方を報告する。")
    lines.append("")
    lines.append("## 入力データ")
    lines.append(f"- 443: `{CASES[0].result_csv.relative_to(REPO_ROOT)}`")
    lines.append(f"- 444: `{CASES[1].result_csv.relative_to(REPO_ROOT)}`")
    lines.append("- 連結方法: 443の末尾時刻の次サンプル時刻から444を接続（時間ギャップなし）。")
    lines.append("")

    lines.append("## ケース別サマリ（M30）")
    lines.append("")
    lines.append("| case | X RMSE | X MAE | X Corr | Y RMSE | Y MAE | Y Corr | Freq MAE [Hz] |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for m in case_metrics:
        lines.append(
            f"| {m['tag']} | {m['x_rmse']:.6f} | {m['x_mae']:.6f} | {format_corr(m['x_corr'])} | {m['y_rmse']:.6f} | {m['y_mae']:.6f} | {format_corr(m['y_corr'])} | {m['freq_mae']:.6f} |"
        )
    lines.append("")

    lines.append("## 連結後サマリ（443 -> 444）")
    lines.append("")
    lines.append("| X RMSE | X MAE | X Corr | Y RMSE | Y MAE | Y Corr | Freq MAE [Hz] |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|")
    lines.append(
        f"| {concat_metrics['x_rmse']:.6f} | {concat_metrics['x_mae']:.6f} | {format_corr(concat_metrics['x_corr'])} | {concat_metrics['y_rmse']:.6f} | {concat_metrics['y_mae']:.6f} | {format_corr(concat_metrics['y_corr'])} | {concat_metrics['freq_mae']:.6f} |"
    )
    lines.append("")

    lines.append("## 閾値以下での0収束性（連結後）")
    lines.append("")
    lines.append(f"評価条件: `|PL| <= {threshold:.2f}` を低振幅区間とし、その区間内の推定値PRの0近傍性を比較。")
    lines.append("")
    lines.append("| axis | low-amp samples | low-amp ratio | RMS(PR) in low-amp | MAE(PR,0) in low-amp | ratio(|PR|<=thr) |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    lines.append(
        f"| X | {int(low_x_concat['count'])} | {low_x_concat['ratio']:.4f} | {low_x_concat['est_rms']:.6f} | {low_x_concat['est_mae_to_zero']:.6f} | {low_x_concat['est_within_thr_ratio']:.4f} |"
    )
    lines.append(
        f"| Y | {int(low_y_concat['count'])} | {low_y_concat['ratio']:.4f} | {low_y_concat['est_rms']:.6f} | {low_y_concat['est_mae_to_zero']:.6f} | {low_y_concat['est_within_thr_ratio']:.4f} |"
    )
    lines.append("")
    lines.append("解釈メモ:")
    lines.append("- `RMS(PR) in low-amp` と `MAE(PR,0)` が小さいほど、低振幅時に0へ収束しているとみなせる。")
    lines.append("- `ratio(|PR|<=thr)` が高いほど、閾値以下区間で推定値が0近傍に留まれている。")
    lines.append("")

    lines.append("## 図")
    lines.append("")
    lines.append("### X軸: 生データと推定値（連結）")
    lines.append("")
    lines.append(f"![concat x raw vs estimate]({to_report_rel(report_path, x_png)})")
    lines.append("")
    lines.append("### Y軸: 生データと推定値（連結）")
    lines.append("")
    lines.append(f"![concat y raw vs estimate]({to_report_rel(report_path, y_png)})")
    lines.append("")
    lines.append("### 周波数推定: EstFreq_Hz と RealFreq_Hz（連結）")
    lines.append("")
    lines.append(f"![concat frequency estimate vs real]({to_report_rel(report_path, f_png)})")
    lines.append("")

    lines.append("## まとめ")
    lines.append("")
    lines.append("- Robust + Smooth M30 条件で、443/444連結時系列に対して X/Y とも生データ・推定値・周波数推定を一括確認できる形に整理した。")
    lines.append(f"- 低振幅判定（|PL| <= {threshold:.2f}）における0収束性を、X/Y別の同一指標で比較可能にした。")

    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote report: {report_path}")


if __name__ == "__main__":
    main()