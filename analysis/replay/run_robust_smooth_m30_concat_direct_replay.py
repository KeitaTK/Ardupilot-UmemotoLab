#!/usr/bin/env python3
"""Run replay on concatenated input log using Robust + Smooth M30 settings."""

from __future__ import annotations

import csv
import datetime
import subprocess
import zoneinfo
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports"
REPLAY_BIN = REPO_ROOT / "build/sitl/examples/EKF_CSV_Replay"

INPUT_A = REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports/2026-04-13_443_444リプレイ検証_model_strong/00000443_w35_100_input.csv"
INPUT_B = REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports/2026-04-13_443_444リプレイ検証_model_strong/00000444_w40_110_input.csv"

# Robust + Smooth M30 from the previous sweep.
M30_Q_D = 9.5367432e-12
M30_Q_DD = 2.3841858e-11
M30_Q_C = 4.7683716e-13
M30_R_MEAS = 46.0


def read_csv_rows(path: Path) -> tuple[List[Dict[str, str]], List[str]]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if reader.fieldnames is None:
            raise RuntimeError(f"No header in CSV: {path}")
        return rows, list(reader.fieldnames)


def median_dt_us(rows: List[Dict[str, str]]) -> int:
    t = np.array([int(float(r["TimeUS"])) for r in rows], dtype=np.int64)
    if t.size < 2:
        return 10000
    return int(np.median(np.diff(t)))


def build_concatenated_input(out_csv: Path) -> Dict[str, float]:
    rows_a, fields_a = read_csv_rows(INPUT_A)
    rows_b, fields_b = read_csv_rows(INPUT_B)

    if fields_a != fields_b:
        raise RuntimeError("Input CSV headers differ and cannot be concatenated safely.")

    t_a = np.array([int(float(r["TimeUS"])) for r in rows_a], dtype=np.int64)
    t_b = np.array([int(float(r["TimeUS"])) for r in rows_b], dtype=np.int64)
    dt_a = median_dt_us(rows_a)

    offset_us = int(t_a[-1] + dt_a - t_b[0])

    rows_out: List[Dict[str, str]] = []
    rows_out.extend(rows_a)

    for rb in rows_b:
        new_row = dict(rb)
        new_t = int(float(rb["TimeUS"])) + offset_us
        new_row["TimeUS"] = str(new_t)
        rows_out.append(new_row)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields_a)
        writer.writeheader()
        writer.writerows(rows_out)

    split_timeus = int(t_b[0] + offset_us)
    start_timeus = int(t_a[0])
    split_time_s = (split_timeus - start_timeus) * 1.0e-6

    return {
        "rows_a": float(len(rows_a)),
        "rows_b": float(len(rows_b)),
        "rows_total": float(len(rows_out)),
        "split_time_s": float(split_time_s),
    }


def run_replay(input_csv: Path, out_dir: Path, tag: str) -> Path:
    if not REPLAY_BIN.exists():
        raise RuntimeError(f"Replay binary not found: {REPLAY_BIN}")

    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(REPLAY_BIN),
        "--input",
        str(input_csv),
        "--outdir",
        str(out_dir),
        "--tag",
        tag,
        "--sw-mode",
        "log",
        "--ekf-axis-mask",
        "3",
        "--ekf-axis-gate",
        "0",
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
        "--ekf-innov-max",
        "0.70",
        "--ekf-nis-max",
        "4.00",
        "--ekf-q-d",
        f"{M30_Q_D}",
        "--ekf-q-dd",
        f"{M30_Q_DD}",
        "--ekf-q-c",
        f"{M30_Q_C}",
        "--ekf-r-meas",
        f"{M30_R_MEAS}",
    ]
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)
    return out_dir / f"{tag}_result.csv"


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
    return {
        "count": float(n),
        "ratio": float(n / raw.size),
        "est_rms": float(np.sqrt(np.mean(est_low**2))),
        "est_mae_to_zero": float(np.mean(np.abs(est_low))),
        "est_within_thr_ratio": float(np.mean(np.abs(est_low) <= threshold)),
    }


def format_corr(v: float) -> str:
    return f"{v:.6f}" if np.isfinite(v) else "N/A"


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

    # Make raw trace moderately opaque so the estimate line is easier to inspect.
    axes[0].plot(t, raw, color="0.70", alpha=0.60, linewidth=0.8, label="Raw (PL)")
    axes[0].plot(t, est, color="tab:blue", linewidth=1.6, label="Estimate (PR)")
    axes[0].axvline(split_t, color="tab:red", linestyle="--", linewidth=1.0, alpha=0.7, label="443/444 split")
    axes[0].set_ylabel(y_label)
    axes[0].set_title(title)
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="upper right")

    axes[1].plot(t, np.abs(raw), color="0.70", alpha=0.60, linewidth=0.8, label="|Raw|")
    axes[1].plot(t, np.abs(est), color="tab:orange", linewidth=1.3, label="|Estimate|")
    axes[1].axhline(threshold, color="tab:green", linestyle=":", linewidth=1.2, label=f"threshold={threshold:.3f}")
    axes[1].axvline(split_t, color="tab:red", linestyle="--", linewidth=1.0, alpha=0.7)
    axes[1].set_xlabel("Replay Time [s]")
    axes[1].set_ylabel("Absolute magnitude")
    axes[1].set_title("Absolute magnitude vs threshold (low-amplitude / zero-convergence check)")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="upper right")

    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_frequency(out_png: Path, t: np.ndarray, est_hz: np.ndarray, split_t: float, title: str) -> None:
    fig, ax = plt.subplots(figsize=(14, 4.8))
    ax.plot(t, est_hz, color="tab:purple", linewidth=1.5, label="EstFreq_Hz")
    ax.axhline(0.454, color="tab:green", linestyle=":", linewidth=1.3, label="Target=0.454 Hz")
    ax.axvline(split_t, color="tab:red", linestyle="--", linewidth=1.0, alpha=0.7, label="443/444 split")
    ax.set_xlabel("Replay Time [s]")
    ax.set_ylabel("Frequency [Hz]")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


def to_report_rel(report_path: Path, path: Path) -> str:
    return str(path.relative_to(report_path.parent))


def metrics_table_for_range(d: Dict[str, np.ndarray], mask: np.ndarray) -> Dict[str, float]:
    est = d["est_hz"][mask]
    return {
        "x_rmse": rmse(d["plx"][mask], d["prx"][mask]),
        "x_mae": mae(d["plx"][mask], d["prx"][mask]),
        "x_corr": corr(d["plx"][mask], d["prx"][mask]),
        "y_rmse": rmse(d["ply"][mask], d["pry"][mask]),
        "y_mae": mae(d["ply"][mask], d["pry"][mask]),
        "y_corr": corr(d["ply"][mask], d["pry"][mask]),
        "est_freq_mean": float(np.mean(est)),
        "est_freq_std": float(np.std(est)),
    }


def main() -> None:
    jst = zoneinfo.ZoneInfo("Asia/Tokyo")
    now = datetime.datetime.now(jst)
    date_str = now.strftime("%Y-%m-%d")
    ts = now.strftime("%H:%M:%S")

    result_root = REPORT_DIR / f"results/{date_str}_robust_smooth_m30_concat_direct_replay"
    concat_input_csv = result_root / "concat_input/00000443_00000444_concat_input.csv"
    replay_out = result_root / "replay"
    tag = "00000443_00000444_concat_robust_smooth_m30"
    report_path = REPORT_DIR / f"{date_str}_{ts}_ロバスト観測更新_Robust+SmoothM30_連結ログ直接リプレイ検証.md"

    concat_info = build_concatenated_input(concat_input_csv)
    result_csv = run_replay(concat_input_csv, replay_out, tag)
    d = read_result_csv(result_csv)

    split_t = concat_info["split_time_s"]
    threshold = 0.10

    fig_dir = result_root / "figures"
    x_png = fig_dir / "concat_direct_replay_x_raw_vs_est.png"
    y_png = fig_dir / "concat_direct_replay_y_raw_vs_est.png"
    f_png = fig_dir / "concat_direct_replay_frequency_est_vs_real.png"

    plot_axis_overlay(
        x_png,
        d["t"],
        d["plx"],
        d["prx"],
        threshold,
        split_t,
        "Robust + Smooth M30: X-axis (replay on concatenated input)",
        "X-axis force",
    )
    plot_axis_overlay(
        y_png,
        d["t"],
        d["ply"],
        d["pry"],
        threshold,
        split_t,
        "Robust + Smooth M30: Y-axis (replay on concatenated input)",
        "Y-axis force",
    )
    plot_frequency(
        f_png,
        d["t"],
        d["est_hz"],
        split_t,
        "Robust + Smooth M30: Estimated frequency (replay on concatenated input)",
    )

    all_mask = np.ones_like(d["t"], dtype=bool)
    a_mask = d["t"] < split_t
    b_mask = ~a_mask
    m_all = metrics_table_for_range(d, all_mask)
    m_a = metrics_table_for_range(d, a_mask)
    m_b = metrics_table_for_range(d, b_mask)

    low_x_all = low_amp_metrics(d["plx"], d["prx"], threshold)
    low_y_all = low_amp_metrics(d["ply"], d["pry"], threshold)

    lines: List[str] = []
    lines.append(f"# {date_str} Robust + Smooth M30 連結ログ直接リプレイ検証（443 -> 444）")
    lines.append("")
    lines.append(f"**作成日時（JST）: {now.strftime('%Y-%m-%d %H:%M:%S')}**")
    lines.append("")
    lines.append("## 目的")
    lines.append("- 2ログを後処理で連結するのではなく、入力ログを先に連結した上で1回のリプレイを実施する。")
    lines.append("- `Robust + Smooth M30` 条件で、X/Yの推定と低振幅時の0収束、および推定周波数の挙動を検証する。")
    lines.append("")
    lines.append("## 入力ログ連結")
    lines.append(f"- 入力A: `{INPUT_A.relative_to(REPO_ROOT)}`")
    lines.append(f"- 入力B: `{INPUT_B.relative_to(REPO_ROOT)}`")
    lines.append(f"- 連結入力CSV: `{concat_input_csv.relative_to(REPO_ROOT)}`")
    lines.append(f"- サンプル数: A={int(concat_info['rows_a'])}, B={int(concat_info['rows_b'])}, Total={int(concat_info['rows_total'])}")
    lines.append(f"- 境界時刻: t={split_t:.6f}s （この時刻で443区間と444区間が切り替わる）")
    lines.append("")
    lines.append("## リプレイ設定（Robust + Smooth M30）")
    lines.append("- robust update: ON (`--ekf-robust-update 1`) / NIS reject: 3.0")
    lines.append(f"- Q_D={M30_Q_D:.8g}, Q_DD={M30_Q_DD:.8g}, Q_C={M30_Q_C:.8g}, R_MEAS={M30_R_MEAS:.3f}")
    lines.append("- 結果CSV: `" + str(result_csv.relative_to(REPO_ROOT)) + "`")
    lines.append("")

    lines.append("## 指標サマリ")
    lines.append("")
    lines.append("| segment | X RMSE | X MAE | X Corr | Y RMSE | Y MAE | Y Corr | EstFreq mean [Hz] | EstFreq std [Hz] |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    lines.append(f"| all | {m_all['x_rmse']:.6f} | {m_all['x_mae']:.6f} | {format_corr(m_all['x_corr'])} | {m_all['y_rmse']:.6f} | {m_all['y_mae']:.6f} | {format_corr(m_all['y_corr'])} | {m_all['est_freq_mean']:.6f} | {m_all['est_freq_std']:.6f} |")
    lines.append(f"| first (443) | {m_a['x_rmse']:.6f} | {m_a['x_mae']:.6f} | {format_corr(m_a['x_corr'])} | {m_a['y_rmse']:.6f} | {m_a['y_mae']:.6f} | {format_corr(m_a['y_corr'])} | {m_a['est_freq_mean']:.6f} | {m_a['est_freq_std']:.6f} |")
    lines.append(f"| second (444) | {m_b['x_rmse']:.6f} | {m_b['x_mae']:.6f} | {format_corr(m_b['x_corr'])} | {m_b['y_rmse']:.6f} | {m_b['y_mae']:.6f} | {format_corr(m_b['y_corr'])} | {m_b['est_freq_mean']:.6f} | {m_b['est_freq_std']:.6f} |")
    lines.append("")

    lines.append("## 閾値以下での0収束性（全区間）")
    lines.append("")
    lines.append(f"評価条件: `|PL| <= {threshold:.2f}`")
    lines.append("")
    lines.append("| axis | low-amp samples | low-amp ratio | RMS(PR) in low-amp | MAE(PR,0) in low-amp | ratio(|PR|<=thr) |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    lines.append(f"| X | {int(low_x_all['count'])} | {low_x_all['ratio']:.4f} | {low_x_all['est_rms']:.6f} | {low_x_all['est_mae_to_zero']:.6f} | {low_x_all['est_within_thr_ratio']:.4f} |")
    lines.append(f"| Y | {int(low_y_all['count'])} | {low_y_all['ratio']:.4f} | {low_y_all['est_rms']:.6f} | {low_y_all['est_mae_to_zero']:.6f} | {low_y_all['est_within_thr_ratio']:.4f} |")
    lines.append("")
    lines.append("注記:")
    lines.append("- `RMS(PR) in low-amp` と `MAE(PR,0)` が小さいほど0収束性が高い。")
    lines.append("- `ratio(|PR|<=thr)` が高いほど、低振幅区間で推定が閾値内に留まる。")
    lines.append("- 下段グラフ（Absolute magnitude vs threshold）は、`|Raw|` と `|Estimate|` を閾値線と比較し、低振幅区間で推定が0近傍へ収束しているかを確認するための図。")
    lines.append("")

    lines.append("## 図")
    lines.append("")
    lines.append("### X軸: 生データと推定値（連結ログを直接リプレイ）")
    lines.append(f"![concat direct replay x]({to_report_rel(report_path, x_png)})")
    lines.append("")
    lines.append("### Y軸: 生データと推定値（連結ログを直接リプレイ）")
    lines.append(f"![concat direct replay y]({to_report_rel(report_path, y_png)})")
    lines.append("")
    lines.append("### 周波数推定: EstFreq_Hz（連結ログを直接リプレイ）")
    lines.append(f"![concat direct replay frequency]({to_report_rel(report_path, f_png)})")

    report_path.write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote report: {report_path}")


if __name__ == "__main__":
    main()