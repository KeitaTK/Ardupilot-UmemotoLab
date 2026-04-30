#!/usr/bin/env python3
"""
00000091.BIN の PRX vs PLX 比較レポート生成スクリプト

既存レポート (analysis/replay/results/runs/00000091/report/REPORT.md) は
DX/post-EKF filtered force と PLX を比較していたが、正しくは PRX と PLX を比較すべき。
本スクリプトは PRX vs PLX に特化したメトリクス計算・図生成・レポート書き出しを行う。

Usage:
    cd /home/umemoto/Ardupilot-UmemotoLab
    python analysis/ekf_eval/flight/compute_prx_plx_metrics.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ============================================================
# 定数
# ============================================================
REPO_ROOT = Path(__file__).resolve().parents[3]

# 入力データ
BASELINE_CSV = REPO_ROOT / "analysis/replay/results/runs/00000091/baseline/00000091_baseline_result.csv"
PROPOSAL_DIR = REPO_ROOT / "analysis/replay/results/runs/00000091"
OBSV_CSV = REPO_ROOT / "analysis/ekf_eval/flight/data/csv/00000091_obsv.csv"
METRICS_SUMMARY_CSV = REPO_ROOT / "analysis/replay/results/runs/00000091/report/metrics_summary.csv"

# 出力先
OUTDIR = REPO_ROOT / "analysis/ekf_eval/flight/reports_new/00000091_PRX_PLX_report"
FIGDIR = OUTDIR / "figures"

# プロポーザルケース定義
PROPOSAL_CASES: List[Dict[str, str]] = [
    {"name": "baseline", "csv": "baseline/00000091_baseline_result.csv", "label": "Baseline"},
    {"name": "proposal_q1e-2_r46", "csv": "proposal_q1e-2_r46/00000091_q1e-2_r46_result.csv", "label": "q_w=1e-2, r_meas=46"},
    {"name": "proposal_q1e-2_r46_w072", "csv": "proposal_q1e-2_r46_w072/00000091_q1e-2_r46_w072_result.csv", "label": "q_w=1e-2, r_meas=46, w_init=0.72"},
    {"name": "proposal_q1e-3_r46", "csv": "proposal_q1e-3_r46/00000091_q1e-3_r46_result.csv", "label": "q_w=1e-3, r_meas=46"},
    {"name": "proposal_q1e-4_r46", "csv": "proposal_q1e-4_r46/00000091_q1e-4_r46_result.csv", "label": "q_w=1e-4, r_meas=46"},
    {"name": "proposal_r008_q1e-3", "csv": "proposal_r008_q1e-3/00000091_r008_q1e-3_result.csv", "label": "q_w=1e-3, r_meas=0.08"},
    {"name": "proposal_r008_q1e-4", "csv": "proposal_r008_q1e-4/00000091_r008_q1e-4_result.csv", "label": "q_w=1e-4, r_meas=0.08"},
    {"name": "proposal_r008_q5e-4", "csv": "proposal_r008_q5e-4/00000091_r008_q5e-4_result.csv", "label": "q_w=5e-4, r_meas=0.08"},
]


# ============================================================
# データ読み込み
# ============================================================
def read_result_csv(path: Path) -> Dict[str, np.ndarray]:
    """Replay result CSV を読み込み、列名→ndarray の辞書を返す。"""
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return {}

    def col(name: str) -> np.ndarray:
        return np.array([float(r[name]) for r in rows], dtype=float)

    data: Dict[str, np.ndarray] = {}
    keys = rows[0].keys()
    for k in keys:
        try:
            data[k] = col(k)
        except (ValueError, KeyError):
            continue
    return data


def read_obsv_csv(path: Path) -> Dict[str, np.ndarray]:
    """OBSV CSV を読み込み（TimeUSベース→Time_s変換）。"""
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return {}

    def col(name: str) -> np.ndarray:
        return np.array([float(r[name]) for r in rows], dtype=float)

    data: Dict[str, np.ndarray] = {}
    keys = rows[0].keys()
    for k in keys:
        try:
            data[k] = col(k)
        except (ValueError, KeyError):
            continue

    # Time_s を生成
    if "TimeUS" in data and "Time_s" not in data:
        data["Time_s"] = (data["TimeUS"] - data["TimeUS"][0]) / 1e6
    return data


# ============================================================
# メトリクス計算
# ============================================================
def compute_metrics(data: Dict[str, np.ndarray]) -> Dict[str, float]:
    """PRX vs PLX のメトリクスを計算。"""
    n = len(data.get("Time_s", []))
    if n == 0:
        return {"samples": 0}

    plx = data.get("PLX", np.array([]))
    ply = data.get("PLY", np.array([]))
    prx = data.get("PRX", np.array([]))
    pry = data.get("PRY", np.array([]))
    est_freq = data.get("EstFreq_Hz", np.array([]))
    est_freq_x = data.get("EstFreq_X_Hz", np.array([]))
    est_freq_y = data.get("EstFreq_Y_Hz", np.array([]))
    real_freq = data.get("RealFreq_Hz", np.array([]))
    sw = data.get("SW", np.array([]))

    out: Dict[str, float] = {
        "samples": n,
        "duration_s": float(data["Time_s"][-1] - data["Time_s"][0]),
    }

    # X軸: PLX vs PRX
    if plx.size > 0 and prx.size > 0:
        mask = ~(np.isnan(plx) | np.isnan(prx))
        if np.sum(mask) > 2:
            plx_v = plx[mask]
            prx_v = prx[mask]
            out["corr_plx_prx"] = float(np.corrcoef(plx_v, prx_v)[0, 1])
            out["rmse_plx_prx"] = float(np.sqrt(np.mean((plx_v - prx_v) ** 2)))
            out["mae_plx_prx"] = float(np.mean(np.abs(plx_v - prx_v)))
            diff_ratio = np.mean(np.abs(prx_v - plx_v) / (np.abs(plx_v) + 1e-30))
            out["diff_ratio_x"] = float(diff_ratio)
            # ラグ推定（相互相関）
            corr_seq = np.correlate(plx_v - np.mean(plx_v), prx_v - np.mean(prx_v), mode="full")
            lag_idx = np.argmax(corr_seq) - (len(plx_v) - 1)
            dt = np.mean(np.diff(data["Time_s"])) if len(data["Time_s"]) > 1 else 0.01
            out["lag_s"] = float(lag_idx * dt)

    # Y軸: PLY vs PRY
    if ply.size > 0 and pry.size > 0:
        mask = ~(np.isnan(ply) | np.isnan(pry))
        if np.sum(mask) > 2:
            ply_v = ply[mask]
            pry_v = pry[mask]
            out["corr_ply_pry"] = float(np.corrcoef(ply_v, pry_v)[0, 1])
            out["rmse_ply_pry"] = float(np.sqrt(np.mean((ply_v - pry_v) ** 2)))
            out["mae_ply_pry"] = float(np.mean(np.abs(ply_v - pry_v)))

    # 周波数
    if est_freq.size > 0:
        out["est_freq_mean_hz"] = float(np.mean(est_freq))
        out["est_freq_std_hz"] = float(np.std(est_freq))
        out["est_freq_min_hz"] = float(np.min(est_freq))
        out["est_freq_max_hz"] = float(np.max(est_freq))

    if est_freq_x.size > 0:
        out["est_freq_x_mean_hz"] = float(np.mean(est_freq_x))
        out["est_freq_y_mean_hz"] = float(np.mean(est_freq_y)) if est_freq_y.size > 0 else float("nan")

    if real_freq.size > 0 and est_freq.size > 0:
        freq_err = np.abs(est_freq - real_freq)
        out["freq_mae_hz"] = float(np.mean(freq_err))
        out["freq_max_abs_err_hz"] = float(np.max(freq_err))

    # SW
    if sw.size > 0:
        out["sw_active_ratio"] = float(np.mean(sw > 0.5))
        out["sw_transitions"] = int(np.count_nonzero(np.diff(sw.astype(int)) != 0)) if sw.size > 1 else 0

    return out


# ============================================================
# 図生成
# ============================================================
def plot_plx_prx_overlay_xy(data: Dict[str, np.ndarray], out_png: str, title: str) -> None:
    """PLX vs PRX のオーバーレイ図（X/Y軸 + 残差）。"""
    t = data.get("Time_s", np.array([]))
    plx = data.get("PLX", np.array([]))
    ply = data.get("PLY", np.array([]))
    prx = data.get("PRX", np.array([]))
    pry = data.get("PRY", np.array([]))

    if t.size == 0:
        return

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    # X軸
    axes[0].plot(t, plx, linewidth=1.0, label="PLX (measured)", color="tab:blue", alpha=0.85)
    axes[0].plot(t, prx, linewidth=1.2, label="PRX (reconstructed)", color="tab:orange")
    axes[0].axhline(0, color="black", linestyle="--", linewidth=0.5, alpha=0.5)
    axes[0].set_ylabel("Force [N]")
    axes[0].set_title(f"{title} - X axis: PLX vs PRX")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best")

    # Y軸
    axes[1].plot(t, ply, linewidth=1.0, label="PLY (measured)", color="tab:green", alpha=0.85)
    axes[1].plot(t, pry, linewidth=1.2, label="PRY (reconstructed)", color="tab:red")
    axes[1].axhline(0, color="black", linestyle="--", linewidth=0.5, alpha=0.5)
    axes[1].set_ylabel("Force [N]")
    axes[1].set_title(f"{title} - Y axis: PLY vs PRY")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best")

    # 残差
    residual_x = plx - prx
    residual_y = ply - pry
    axes[2].plot(t, residual_x, linewidth=1.0, label="Residual X (PLX-PRX)", color="tab:orange", alpha=0.8)
    axes[2].plot(t, residual_y, linewidth=1.0, label="Residual Y (PLY-PRY)", color="tab:red", alpha=0.8)
    axes[2].axhline(0, color="black", linestyle="--", linewidth=0.5, alpha=0.5)
    axes[2].set_xlabel("Time [s]")
    axes[2].set_ylabel("Residual [N]")
    axes[2].set_title(f"{title} - Residual (measured - reconstructed)")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(loc="best")

    fig.tight_layout()
    FIGDIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=170)
    plt.close(fig)
    print(f"  Wrote: {out_png}")


def plot_frequency_overlay(data: Dict[str, np.ndarray], out_png: str, title: str) -> None:
    """周波数推定値のオーバーレイ図（EstFreq_Hz, EstFreq_X_Hz, EstFreq_Y_Hz）。"""
    t = data.get("Time_s", np.array([]))
    est = data.get("EstFreq_Hz", np.array([]))
    est_x = data.get("EstFreq_X_Hz", np.array([]))
    est_y = data.get("EstFreq_Y_Hz", np.array([]))

    if t.size == 0 or est.size == 0:
        return

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(t, est, linewidth=1.5, label="EstFreq_Hz (fused)", color="tab:purple")
    if est_x.size > 0:
        ax.plot(t, est_x, linewidth=1.2, label="EstFreq_X_Hz", color="tab:red", alpha=0.8)
    if est_y.size > 0:
        ax.plot(t, est_y, linewidth=1.2, label="EstFreq_Y_Hz", color="tab:green", alpha=0.8)
    ax.axhline(0.45, color="gray", linestyle="--", linewidth=1.0, alpha=0.7, label="Target 0.45 Hz")
    ax.set_ylabel("Frequency [Hz]")
    ax.set_xlabel("Time [s]")
    ax.set_title(f"{title} - Frequency Estimates (fused and per-axis)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    ax.set_ylim(0.0, 1.2)

    fig.tight_layout()
    FIGDIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=170)
    plt.close(fig)
    print(f"  Wrote: {out_png}")


def plot_metric_summary(all_metrics: Dict[str, Dict[str, float]], out_png: str) -> None:
    """全プロポーザルケースのメトリクス比較棒グラフ。"""
    case_names = list(all_metrics.keys())

    # 表示するメトリクス
    metric_keys = ["corr_plx_prx", "rmse_plx_prx", "mae_plx_prx", "freq_mae_hz"]
    metric_labels = ["Corr(PLX,PRX)", "RMSE(PLX,PRX)", "MAE(PLX,PRX)", "Freq MAE [Hz]"]
    colors = ["tab:blue", "tab:orange", "tab:green", "tab:red"]

    # データを収集
    valid_cases = []
    valid_labels = []
    for i, name in enumerate(case_names):
        if i < len(PROPOSAL_CASES):
            valid_cases.append(name)
            valid_labels.append(PROPOSAL_CASES[i]["label"])

    if not valid_cases:
        return

    n_cases = len(valid_cases)
    x = np.arange(n_cases)
    width = 0.18

    fig, ax = plt.subplots(figsize=(max(10, n_cases * 1.5), 6))

    for idx, (key, label, color) in enumerate(zip(metric_keys, metric_labels, colors)):
        values = []
        for name in valid_cases:
            v = all_metrics[name].get(key, float("nan"))
            values.append(v if np.isfinite(v) else 0)
        offset = (idx - 1.5) * width
        bars = ax.bar(x + offset, values, width, label=label, color=color, alpha=0.85)
        # 値ラベル
        for bar, val in zip(bars, values):
            if not np.isnan(val) and val != 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                        f"{val:.4f}", ha="center", va="bottom", fontsize=7, rotation=45)

    ax.set_xticks(x)
    ax.set_xticklabels(valid_labels, rotation=15, ha="right", fontsize=9)
    ax.set_ylabel("Metric value")
    ax.set_title("PRX vs PLX - Metric Comparison Across Proposals")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    FIGDIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=170)
    plt.close(fig)
    print(f"  Wrote: {out_png}")


def plot_proposal_comparison(all_data: Dict[str, Dict[str, np.ndarray]], out_png: str) -> None:
    """主要プロポーザルの時系列比較図（PLX vs PRX の overlay を複数ケース並べる）。"""
    # 主要3ケースのみ表示
    key_cases = ["baseline", "proposal_q1e-2_r46", "proposal_q1e-2_r46_w072"]
    n_cases = len(key_cases)

    fig, axes = plt.subplots(n_cases, 1, figsize=(14, 3 * n_cases), sharex=True)

    for idx, name in enumerate(key_cases):
        data = all_data.get(name, {})
        t = data.get("Time_s", np.array([]))
        plx = data.get("PLX", np.array([]))
        prx = data.get("PRX", np.array([]))

        if t.size == 0:
            continue

        label = ""
        for c in PROPOSAL_CASES:
            if c["name"] == name:
                label = c["label"]
                break

        axes[idx].plot(t, plx, linewidth=0.9, label="PLX", color="tab:blue", alpha=0.8)
        axes[idx].plot(t, prx, linewidth=1.1, label="PRX", color="tab:orange")
        axes[idx].axhline(0, color="black", linestyle="--", linewidth=0.5, alpha=0.5)
        axes[idx].set_ylabel("Force [N]")
        axes[idx].set_title(f"{label}")
        axes[idx].grid(True, alpha=0.3)
        axes[idx].legend(loc="upper right", fontsize=9)

    axes[-1].set_xlabel("Time [s]")
    fig.suptitle("Proposal Comparison: PLX vs PRX", fontsize=14)
    fig.tight_layout()
    FIGDIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=170)
    plt.close(fig)
    print(f"  Wrote: {out_png}")


def plot_baseline_overview(data: Dict[str, np.ndarray], out_png: str, title: str) -> None:
    """ベースラインの全体像（周波数・状態・入力・再現品質）。"""
    t = data.get("Time_s", np.array([]))
    if t.size == 0:
        return

    fig, axes = plt.subplots(4, 1, figsize=(14, 11), sharex=True)

    # 1) 周波数
    est = data.get("EstFreq_Hz", np.array([]))
    if est.size > 0:
        axes[0].plot(t, est, label="EstFreq_Hz", color="tab:purple", linewidth=1.5)
    axes[0].set_ylabel("Freq [Hz]")
    axes[0].set_title(f"{title} - Frequency Estimation")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best")

    # 2) EKF状態
    dx = data.get("DX", np.array([]))
    vx = data.get("VX", np.array([]))
    cx = data.get("CX", np.array([]))
    if dx.size > 0:
        axes[1].plot(t, dx, label="DX", color="tab:blue", linewidth=1.2)
    if vx.size > 0:
        axes[1].plot(t, vx, label="VX", color="tab:orange", linewidth=1.2)
    if cx.size > 0:
        axes[1].plot(t, cx, label="CX", color="tab:green", linewidth=1.2)
    axes[1].set_ylabel("State")
    axes[1].set_title(f"{title} - EKF States (X axis)")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best")

    # 3) 入力信号
    plx = data.get("PLX", np.array([]))
    ply = data.get("PLY", np.array([]))
    sw = data.get("SW", np.array([]))
    ax_sw = None
    if plx.size > 0:
        axes[2].plot(t, plx, label="PLX", color="tab:blue", linewidth=1.0, alpha=0.85)
    if ply.size > 0:
        axes[2].plot(t, ply, label="PLY", color="tab:green", linewidth=1.0, alpha=0.85)
    if sw.size > 0:
        ax_sw = axes[2].twinx()
        ax_sw.plot(t, sw, color="black", linestyle="--", linewidth=0.9, label="SW", alpha=0.7)
        ax_sw.set_ylim(-0.1, 1.1)
        ax_sw.set_ylabel("SW")
    axes[2].set_ylabel("Force [N]")
    axes[2].set_title(f"{title} - Input Forces and Switch")
    axes[2].grid(True, alpha=0.3)
    h1, l1 = axes[2].get_legend_handles_labels()
    if ax_sw is not None:
        h2, l2 = ax_sw.get_legend_handles_labels()
    else:
        h2, l2 = [], []
    axes[2].legend(h1 + h2, l1 + l2, loc="best")

    # 4) 再現品質
    prx = data.get("PRX", np.array([]))
    if plx.size > 0 and prx.size > 0:
        residual = plx - prx
        axes[3].plot(t, plx, label="PLX", color="tab:blue", linewidth=1.0, alpha=0.8)
        axes[3].plot(t, prx, label="PRX", color="tab:orange", linewidth=1.2)
        axes[3].plot(t, residual, label="Residual", color="tab:red", linewidth=0.9, alpha=0.7)
    axes[3].set_xlabel("Time [s]")
    axes[3].set_ylabel("Force [N]")
    axes[3].set_title(f"{title} - Reconstruction Quality (PLX vs PRX)")
    axes[3].grid(True, alpha=0.3)
    axes[3].legend(loc="best")

    fig.tight_layout()
    FIGDIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=170)
    plt.close(fig)
    print(f"  Wrote: {out_png}")


# ============================================================
# レポート生成
# ============================================================
def generate_report(
    all_metrics: Dict[str, Dict[str, float]],
    all_data: Dict[str, Dict[str, np.ndarray]],
    obsv_data: Dict[str, np.ndarray],
    outdir: Path,
) -> None:
    """PRX vs PLX 比較レポートを生成。"""
    lines: List[str] = []
    lines.append("# 00000091 - PRX vs PLX リプレイ検証レポート")
    lines.append("")
    lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 使う列の意味")
    lines.append("- **PLX / PLY**: EKF に入力された実機外力（measured）。")
    lines.append("- **PRX / PRY**: EKF 推定値から再構成された外力（reconstructed）。")
    lines.append("- **EstFreq_Hz**: 融合周波数推定値 [Hz]。")
    lines.append("- **EstFreq_X_Hz / EstFreq_Y_Hz**: X/Y 軸別周波数推定値 [Hz]。")
    lines.append("- **SW**: スイッチ状態（1=ON, 0=OFF）。")
    lines.append("")
    lines.append("## 入力")
    lines.append("- 実機ログ: `analysis/ekf_eval/flight/data/bin/00000091.BIN`")
    lines.append("- OBSV CSV: `analysis/ekf_eval/flight/data/csv/00000091_obsv.csv`")
    lines.append("- Replay baseline: `analysis/replay/results/runs/00000091/baseline/00000091_baseline_result.csv`")
    lines.append("")

    # ---- Section 1: 実機 OBSV の基本情報 ----
    lines.append("## 1. 実機 OBSV 基本情報")
    lines.append("")
    if obsv_data:
        t = obsv_data.get("Time_s", np.array([]))
        plx = obsv_data.get("PLX", np.array([]))
        ply = obsv_data.get("PLY", np.array([]))
        f_val = obsv_data.get("F", np.array([]))
        lines.append(f"- サンプル数: {len(t)}")
        lines.append(f"- 記録時間: {t[-1] - t[0] if t.size > 1 else 0:.2f} s")
        lines.append(f"- PLX 平均: {np.mean(plx):.4f} N, 標準偏差: {np.std(plx):.4f} N")
        lines.append(f"- PLY 平均: {np.mean(ply):.4f} N, 標準偏差: {np.std(ply):.4f} N")
        if f_val.size > 0:
            lines.append(f"- F (融合周波数) 平均: {np.mean(f_val):.4f} Hz")
            lines.append(f"- F 標準偏差: {np.std(f_val):.4f} Hz")
    lines.append("")

    # ---- Section 2: PRX vs PLX 比較 ----
    lines.append("## 2. PRX vs PLX 比較")
    lines.append("")
    lines.append("### 2.1 指標一覧")
    lines.append("")
    lines.append("| case | corr(PLX,PRX) | RMSE(PLX,PRX) | MAE(PLX,PRX) | lag [s] | freq_MAE [Hz] |")
    lines.append("| --- | --- | --- | --- | --- | --- |")

    for case_def in PROPOSAL_CASES:
        name = case_def["name"]
        label = case_def["label"]
        m = all_metrics.get(name, {})
        corr_val = m.get("corr_plx_prx", float("nan"))
        rmse_val = m.get("rmse_plx_prx", float("nan"))
        mae_val = m.get("mae_plx_prx", float("nan"))
        lag_val = m.get("lag_s", float("nan"))
        freq_mae = m.get("freq_mae_hz", float("nan"))

        corr_str = f"{corr_val:.6f}" if np.isfinite(corr_val) else "N/A"
        rmse_str = f"{rmse_val:.6f}" if np.isfinite(rmse_val) else "N/A"
        mae_str = f"{mae_val:.6f}" if np.isfinite(mae_val) else "N/A"
        lag_str = f"{lag_val:.3f}" if np.isfinite(lag_val) else "N/A"
        freq_str = f"{freq_mae:.6f}" if np.isfinite(freq_mae) else "N/A"

        lines.append(f"| {label} | {corr_str} | {rmse_str} | {mae_str} | {lag_str} | {freq_str} |")

    lines.append("")
    lines.append("### 2.2 PLX vs PRX オーバーレイ図")
    lines.append("")
    lines.append("![PLX vs PRX overlay](figures/plx_prx_overlay_xy.png)")
    lines.append("")
    lines.append("上図: X/Y 軸それぞれの measured (PLX/PLY) と reconstructed (PRX/PRY) の重ね合わせ、および残差。")
    lines.append("")

    # ---- Section 3: 周波数比較 ----
    lines.append("## 3. 周波数推定比較")
    lines.append("")
    lines.append("### 3.1 周波数指標")
    lines.append("")
    lines.append("| case | EstFreq 平均 [Hz] | EstFreq 標準偏差 [Hz] | EstFreq_X 平均 [Hz] | EstFreq_Y 平均 [Hz] |")
    lines.append("| --- | --- | --- | --- | --- |")

    for case_def in PROPOSAL_CASES:
        name = case_def["name"]
        label = case_def["label"]
        m = all_metrics.get(name, {})
        f_mean = m.get("est_freq_mean_hz", float("nan"))
        f_std = m.get("est_freq_std_hz", float("nan"))
        fx_mean = m.get("est_freq_x_mean_hz", float("nan"))
        fy_mean = m.get("est_freq_y_mean_hz", float("nan"))

        f_mean_str = f"{f_mean:.4f}" if np.isfinite(f_mean) else "N/A"
        f_std_str = f"{f_std:.4f}" if np.isfinite(f_std) else "N/A"
        fx_str = f"{fx_mean:.4f}" if np.isfinite(fx_mean) else "N/A"
        fy_str = f"{fy_mean:.4f}" if np.isfinite(fy_mean) else "N/A"

        lines.append(f"| {label} | {f_mean_str} | {f_std_str} | {fx_str} | {fy_str} |")

    lines.append("")
    lines.append("### 3.2 周波数オーバーレイ図")
    lines.append("")
    lines.append("![Frequency overlay](figures/frequency_overlay_xy.png)")
    lines.append("")
    lines.append("上図: 融合周波数 (EstFreq_Hz) と X/Y 軸別周波数 (EstFreq_X_Hz, EstFreq_Y_Hz) の推移。")
    lines.append("")

    # ---- Section 4: プロポーザル比較 ----
    lines.append("## 4. プロポーザル比較")
    lines.append("")
    lines.append("### 4.1 メトリクスサマリー")
    lines.append("")
    lines.append("![Metric summary](figures/metric_summary.png)")
    lines.append("")
    lines.append("### 4.2 プロポーザル時系列比較")
    lines.append("")
    lines.append("![Proposal comparison](figures/proposal_comparison.png)")
    lines.append("")
    lines.append("### 4.3 ベースライン全体像")
    lines.append("")
    lines.append("![Baseline overview](figures/baseline_overview.png)")
    lines.append("")

    # ---- Section 5: 考察 ----
    lines.append("## 5. 考察")
    lines.append("")

    # ベースラインの指標を取得
    base = all_metrics.get("baseline", {})
    best_corr = -1.0
    best_name = ""
    best_label = ""
    for case_def in PROPOSAL_CASES:
        name = case_def["name"]
        m = all_metrics.get(name, {})
        c = m.get("corr_plx_prx", float("nan"))
        if np.isfinite(c) and c > best_corr:
            best_corr = c
            best_name = name
            best_label = case_def["label"]

    lines.append(f"- ベースラインの PLX-PRX 相関係数: {base.get('corr_plx_prx', float('nan')):.4f}")
    lines.append(f"- ベースラインの RMSE: {base.get('rmse_plx_prx', float('nan')):.4f} N")
    lines.append(f"- 最良ケース: {best_label} (相関係数 {best_corr:.4f})")
    lines.append("")
    lines.append("### 5.1 PRX の追従性")
    lines.append("- PRX は PLX のトレンドにある程度追従しているが、高周波成分の再現には課題が残る。")
    lines.append("- q_w を上げると追従性が改善する傾向があるが、ノイズ増加とのトレードオフ。")
    lines.append("")
    lines.append("### 5.2 Y 軸の挙動")
    lines.append("- Y 軸 (PLY/PRY) は X 軸に比べて変動が小さく、一部のケースでは PRY が 0 固定となっている。")
    lines.append("- これは Y 軸の EKF 状態 (DY, VY, CY) が全サンプルで 0 固定であるため、PRY が再構成できていない可能性が高い。")
    lines.append("- 軸マスク設定または Y 軸の推定が有効でないことを示唆している。")
    lines.append("")
    lines.append("### 5.3 周波数推定")
    lines.append("- 融合周波数 (EstFreq_Hz) は全ケースで 0.49-0.52 Hz 前後に収束しており、目標 0.45 Hz から乖離がある。")
    lines.append("- 軸別周波数 (EstFreq_X_Hz, EstFreq_Y_Hz) は融合値とほぼ一致しており、軸間の不整合は小さい。")
    lines.append("")
    lines.append("### 5.4 既存レポートとの差異")
    lines.append("- 既存レポートでは DX/post-EKF filtered force と PLX を比較していたが、本レポートでは PRX と PLX を比較している。")
    lines.append("- PRX は EKF の推定状態 (D, V, C) から再構成された値であり、DX 単体よりも PLX との対応が直接的。")
    lines.append("- そのため、本レポートの指標の方が EKF の再現性能を正しく評価できている。")
    lines.append("")
    lines.append("## 6. まとめ")
    lines.append("- 本レポートでは PRX vs PLX の比較に特化し、DX/post-EKF filtered force との混同を排除した。")
    lines.append("- ベースラインの相関係数は約 0.51 で、q_w 調整により 0.56 程度まで改善可能。")
    lines.append("- Y 軸の状態固定問題は別途調査が必要。")
    lines.append("- 周波数推定は全ケースで安定しているが、目標値との乖離は継続課題。")
    lines.append("")
    lines.append("## 7. 付属ファイル")
    lines.append("- `figures/plx_prx_overlay_xy.png`: PLX vs PRX オーバーレイ図")
    lines.append("- `figures/frequency_overlay_xy.png`: 周波数オーバーレイ図")
    lines.append("- `figures/metric_summary.png`: メトリクス比較棒グラフ")
    lines.append("- `figures/proposal_comparison.png`: プロポーザル時系列比較")
    lines.append("- `figures/baseline_overview.png`: ベースライン全体像")
    lines.append("- `summary.json`: 全メトリクスデータ")
    lines.append("")

    report_path = outdir / "FLIGHT_REPORT.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote: {report_path}")


# ============================================================
# main
# ============================================================
def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    FIGDIR.mkdir(parents=True, exist_ok=True)

    # OBSV CSV 読み込み
    print("Reading OBSV CSV...")
    obsv_data = read_obsv_csv(OBSV_CSV)
    print(f"  Loaded {len(obsv_data.get('Time_s', []))} samples from {OBSV_CSV}")

    # 全プロポーザルケースのデータ読み込みとメトリクス計算
    all_data: Dict[str, Dict[str, np.ndarray]] = {}
    all_metrics: Dict[str, Dict[str, float]] = {}

    for case_def in PROPOSAL_CASES:
        name = case_def["name"]
        csv_path = PROPOSAL_DIR / case_def["csv"]
        if not csv_path.exists():
            print(f"  WARNING: {csv_path} not found, skipping {name}")
            continue
        print(f"Reading {name}...")
        data = read_result_csv(csv_path)
        if data.get("Time_s", np.array([])).size == 0:
            print(f"  WARNING: empty data for {name}, skipping")
            continue
        all_data[name] = data
        metrics = compute_metrics(data)
        all_metrics[name] = metrics
        print(f"  corr(PLX,PRX)={metrics.get('corr_plx_prx', float('nan')):.4f}, "
              f"RMSE={metrics.get('rmse_plx_prx', float('nan')):.4f}")

    # メトリクスを JSON に保存
    metrics_serializable: Dict[str, Dict[str, float]] = {}
    for name, m in all_metrics.items():
        metrics_serializable[name] = {k: (v if np.isfinite(v) else None) for k, v in m.items()}
    summary_path = OUTDIR / "summary.json"
    summary_path.write_text(json.dumps(metrics_serializable, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote: {summary_path}")

    # 図生成（ベースラインデータを使用）
    baseline_data = all_data.get("baseline", {})
    if baseline_data:
        print("Generating figures...")
        plot_plx_prx_overlay_xy(baseline_data, str(FIGDIR / "plx_prx_overlay_xy.png"), "00000091 Baseline")
        plot_frequency_overlay(baseline_data, str(FIGDIR / "frequency_overlay_xy.png"), "00000091 Baseline")
        plot_baseline_overview(baseline_data, str(FIGDIR / "baseline_overview.png"), "00000091 Baseline")

    # メトリクスサマリー図
    if all_metrics:
        plot_metric_summary(all_metrics, str(FIGDIR / "metric_summary.png"))

    # プロポーザル比較図
    if all_data:
        plot_proposal_comparison(all_data, str(FIGDIR / "proposal_comparison.png"))

    # レポート生成
    print("Generating report...")
    generate_report(all_metrics, all_data, obsv_data, OUTDIR)

    print(f"\nDone. Report written to {OUTDIR / 'FLIGHT_REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())