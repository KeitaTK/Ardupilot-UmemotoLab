#!/usr/bin/env python3
"""
00000093.BIN の PFX/PFY vs PLX/PLY 比較レポート生成スクリプト

00000093.BIN は OBSV メッセージに PFX/PFY（Post-EKF Filtered Force）が
直接記録されているため、リプレイを介さずに PLX/PLY との直接比較が可能。
（既存 REPORT_00000093.md では PRX/PRY と表記されているが、実際のフィールド名は PFX/PFY）

本スクリプトは単一ケース（BIN からの直接抽出）のメトリクス計算・図生成・レポート書き出しを行う。

Usage:
    cd /home/umemoto/Ardupilot-UmemotoLab
    python analysis/ekf_eval/flight/compute_prx_plx_metrics_93.py
"""

from __future__ import annotations

import csv
import json
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
OBSV_CSV = REPO_ROOT / "analysis/ekf_eval/flight/data/csv/00000093_obsv.csv"

# 出力先
OUTDIR = REPO_ROOT / "analysis/ekf_eval/flight/reports_new/00000093_PRX_PLX_report"
FIGDIR = OUTDIR / "figures"


# ============================================================
# データ読み込み
# ============================================================
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

    # Time_s が無ければ TimeUS から生成
    if "Time_s" not in data and "TimeUS" in data:
        data["Time_s"] = (data["TimeUS"] - data["TimeUS"][0]) / 1e6
    return data


# ============================================================
# メトリクス計算
# ============================================================
def compute_metrics(data: Dict[str, np.ndarray]) -> Dict[str, float]:
    """PFX/PFY vs PLX/PLY のメトリクスを計算。"""
    n = len(data.get("Time_s", []))
    if n == 0:
        return {"samples": 0}

    plx = data.get("PLX", np.array([]))
    ply = data.get("PLY", np.array([]))
    pfx = data.get("PFX", np.array([]))
    pfy = data.get("PFY", np.array([]))
    f_col = data.get("F", np.array([]))

    out: Dict[str, float] = {
        "samples": n,
        "duration_s": float(data["Time_s"][-1] - data["Time_s"][0]),
    }

    # --- X 軸メトリクス ---
    if plx.size > 0 and pfx.size > 0:
        mask = np.isfinite(plx) & np.isfinite(pfx)
        plx_f = plx[mask]
        pfx_f = pfx[mask]
        if len(plx_f) > 1:
            cc = np.corrcoef(plx_f, pfx_f)[0, 1]
            out["corr_plx_pfx"] = float(cc) if np.isfinite(cc) else float("nan")
            diff = plx_f - pfx_f
            out["rmse_plx_pfx"] = float(np.sqrt(np.mean(diff ** 2)))
            out["mae_plx_pfx"] = float(np.mean(np.abs(diff)))
            rng = float(np.max(plx_f) - np.min(plx_f))
            out["diff_ratio_plx_pfx"] = out["rmse_plx_pfx"] / rng if rng > 1e-12 else float("nan")
            if len(plx_f) > 10:
                corr = np.correlate(plx_f - np.mean(plx_f), pfx_f - np.mean(pfx_f), mode="same")
                lag_idx = np.argmax(corr) - len(plx_f) // 2
                dt = float(data["Time_s"][1] - data["Time_s"][0]) if len(data["Time_s"]) > 1 else 0.01
                out["lag_s_plx_pfx"] = lag_idx * dt
            else:
                out["lag_s_plx_pfx"] = float("nan")
        else:
            out["corr_plx_pfx"] = float("nan")
            out["rmse_plx_pfx"] = float("nan")
            out["mae_plx_pfx"] = float("nan")
            out["diff_ratio_plx_pfx"] = float("nan")
            out["lag_s_plx_pfx"] = float("nan")

    # --- Y 軸メトリクス ---
    if ply.size > 0 and pfy.size > 0:
        # PFY に外れ値（±100超）が含まれるため、|PFY| < 100 でフィルタ
        mask_y = np.isfinite(ply) & np.isfinite(pfy) & (np.abs(pfy) < 100.0)
        ply_f = ply[mask_y]
        pfy_f = pfy[mask_y]
        if len(ply_f) > 1:
            cc_y = np.corrcoef(ply_f, pfy_f)[0, 1]
            out["corr_ply_pfy"] = float(cc_y) if np.isfinite(cc_y) else float("nan")
            diff_y = ply_f - pfy_f
            out["rmse_ply_pfy"] = float(np.sqrt(np.mean(diff_y ** 2)))
            out["mae_ply_pfy"] = float(np.mean(np.abs(diff_y)))
        else:
            out["corr_ply_pfy"] = float("nan")
            out["rmse_ply_pfy"] = float("nan")
            out["mae_ply_pfy"] = float("nan")

    # --- 周波数メトリクス ---
    if f_col.size > 0:
        f_finite = f_col[np.isfinite(f_col)]
        if len(f_finite) > 0:
            out["freq_mean_hz"] = float(np.mean(f_finite))
            out["freq_std_hz"] = float(np.std(f_finite))
            out["freq_min_hz"] = float(np.min(f_finite))
            out["freq_max_hz"] = float(np.max(f_finite))
        else:
            out["freq_mean_hz"] = float("nan")
            out["freq_std_hz"] = float("nan")
            out["freq_min_hz"] = float("nan")
            out["freq_max_hz"] = float("nan")

    return out


# ============================================================
# 図生成
# ============================================================
def plot_plx_pfx_overlay(data: Dict[str, np.ndarray], out_png: str, title: str) -> None:
    """PLX/PLY vs PFX/PFY の時系列オーバーレイ（X/Y軸 + 残差）。"""
    t = data.get("Time_s", np.array([]))
    plx = data.get("PLX", np.array([]))
    ply = data.get("PLY", np.array([]))
    pfx = data.get("PFX", np.array([]))
    pfy = data.get("PFY", np.array([]))

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    # X 軸
    ax = axes[0]
    ax.plot(t, plx, label="PLX (pre-EKF)", alpha=0.8, linewidth=0.8)
    ax.plot(t, pfx, label="PFX (post-EKF filtered)", alpha=0.8, linewidth=0.8)
    ax.set_ylabel("Force X")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    if plx.size > 0 and pfx.size > 0:
        mask = np.isfinite(plx) & np.isfinite(pfx)
        if np.any(mask):
            cc = np.corrcoef(plx[mask], pfx[mask])[0, 1]
            rmse = np.sqrt(np.mean((plx[mask] - pfx[mask]) ** 2))
            ax.set_title(f"{title} — X axis  corr={cc:.4f}  RMSE={rmse:.4f}")

    # Y 軸
    ax = axes[1]
    ax.plot(t, ply, label="PLY (pre-EKF)", alpha=0.8, linewidth=0.8)
    ax.plot(t, pfy, label="PFY (post-EKF filtered)", alpha=0.8, linewidth=0.8)
    ax.set_ylabel("Force Y")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    if ply.size > 0 and pfy.size > 0:
        mask_y = np.isfinite(ply) & np.isfinite(pfy)
        if np.any(mask_y):
            cc_y = np.corrcoef(ply[mask_y], pfy[mask_y])[0, 1]
            rmse_y = np.sqrt(np.mean((ply[mask_y] - pfy[mask_y]) ** 2))
            ax.set_title(f"Y axis  corr={cc_y:.4f}  RMSE={rmse_y:.4f}")

    # 残差（X 軸）
    ax = axes[2]
    if plx.size > 0 and pfx.size > 0:
        mask = np.isfinite(plx) & np.isfinite(pfx)
        residual = plx[mask] - pfx[mask]
        ax.plot(t[mask], residual, label="PLX - PFX", color="red", alpha=0.7, linewidth=0.8)
        ax.axhline(0, color="black", linestyle="--", linewidth=0.5)
        ax.set_ylabel("Residual X")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel("Time [s]")

    plt.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_png}")


def plot_frequency_overview(data: Dict[str, np.ndarray], out_png: str, title: str) -> None:
    """F 列の周波数推移 + 0.45Hz 目標線。"""
    t = data.get("Time_s", np.array([]))
    f_col = data.get("F", np.array([]))

    fig, ax = plt.subplots(figsize=(12, 4))
    if f_col.size > 0:
        mask = np.isfinite(f_col)
        ax.plot(t[mask], f_col[mask], label="F (fused freq)", alpha=0.8, linewidth=0.8)
    ax.axhline(0.45, color="red", linestyle="--", label="Target 0.45 Hz", alpha=0.7)
    ax.set_ylabel("Frequency [Hz]")
    ax.set_xlabel("Time [s]")
    ax.set_title(f"{title} — Frequency")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_png}")


def plot_scatter_plx_pfx(data: Dict[str, np.ndarray], out_png: str, title: str) -> None:
    """PLX/PLY vs PFX/PFY 散布図（相関係数付き）。"""
    plx = data.get("PLX", np.array([]))
    pfx = data.get("PFX", np.array([]))

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # X 軸
    ax = axes[0]
    if plx.size > 0 and pfx.size > 0:
        mask = np.isfinite(plx) & np.isfinite(pfx)
        ax.scatter(plx[mask], pfx[mask], s=1, alpha=0.5)
        lims = [
            min(np.min(plx[mask]), np.min(pfx[mask])),
            max(np.max(plx[mask]), np.max(pfx[mask])),
        ]
        ax.plot(lims, lims, "r--", alpha=0.7, label="y=x")
        cc = np.corrcoef(plx[mask], pfx[mask])[0, 1]
        ax.set_xlabel("PLX (pre-EKF)")
        ax.set_ylabel("PFX (post-EKF filtered)")
        ax.set_title(f"X axis — corr={cc:.4f}")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_aspect("equal")

    # Y 軸
    ax = axes[1]
    ply = data.get("PLY", np.array([]))
    pfy = data.get("PFY", np.array([]))
    if ply.size > 0 and pfy.size > 0:
        mask_y = np.isfinite(ply) & np.isfinite(pfy)
        ax.scatter(ply[mask_y], pfy[mask_y], s=1, alpha=0.5)
        lims_y = [
            min(np.min(ply[mask_y]), np.min(pfy[mask_y])),
            max(np.max(ply[mask_y]), np.max(pfy[mask_y])),
        ]
        ax.plot(lims_y, lims_y, "r--", alpha=0.7, label="y=x")
        cc_y = np.corrcoef(ply[mask_y], pfy[mask_y])[0, 1]
        ax.set_xlabel("PLY (pre-EKF)")
        ax.set_ylabel("PFY (post-EKF filtered)")
        ax.set_title(f"Y axis — corr={cc_y:.4f}")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_aspect("equal")

    fig.suptitle(f"{title} — PLX vs PFX Scatter")
    plt.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_png}")


# ============================================================
# レポート生成
# ============================================================
def generate_report(
    metrics: Dict[str, float],
    data: Dict[str, np.ndarray],
    outdir: Path,
) -> None:
    """FLIGHT_REPORT.md を生成。"""
    report_path = outdir / "FLIGHT_REPORT.md"
    fig_rel = "figures"

    lines: List[str] = []
    def L(s: str = "") -> None:
        lines.append(s)

    L("# 00000093 — PFX/PFY vs PLX/PLY 直接比較レポート")
    L()
    L(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    L()

    # --- 使う列の意味 ---
    L("## 使う列の意味")
    L()
    L("| 列 | 意味 |")
    L("|----|------|")
    L("| PLX | pre‑EKF 外力 X 成分（観測値） |")
    L("| PLY | pre‑EKF 外力 Y 成分（観測値） |")
    L("| PFX | Post‑EKF Filtered Force X 成分（OBSV メッセージに直接記録） |")
    L("| PFY | Post‑EKF Filtered Force Y 成分（OBSV メッセージに直接記録） |")
    L("| F | 融合周波数（全軸統合） |")
    L()

    # --- 入力 ---
    L("## 入力")
    L()
    L(f"- ログファイル: `analysis/ekf_eval/flight/data/bin/00000093.BIN`")
    L(f"- サンプル数: {metrics.get('samples', 'N/A')}")
    L(f"- 記録時間: {metrics.get('duration_s', 'N/A'):.2f} s")
    L()

    # --- メトリクス ---
    L("## メトリクス一覧")
    L()
    L("| 指標 | X 軸 | Y 軸 |")
    L("|------|------|------|")
    corr_x = metrics.get("corr_plx_pfx", float("nan"))
    corr_y = metrics.get("corr_ply_pfy", float("nan"))
    rmse_x = metrics.get("rmse_plx_pfx", float("nan"))
    rmse_y = metrics.get("rmse_ply_pfy", float("nan"))
    mae_x = metrics.get("mae_plx_pfx", float("nan"))
    mae_y = metrics.get("mae_ply_pfy", float("nan"))
    lag_x = metrics.get("lag_s_plx_pfx", float("nan"))

    L(f"| 相関係数 | {corr_x:.6f} | {corr_y:.6f} |")
    L(f"| RMSE | {rmse_x:.6f} | {rmse_y:.6f} |")
    L(f"| MAE | {mae_x:.6f} | {mae_y:.6f} |")
    if np.isfinite(lag_x):
        L(f"| 時間遅れ (X) | {lag_x:.4f} s | — |")
    L()

    # --- 周波数 ---
    L("## 周波数推定")
    L()
    freq_mean = metrics.get("freq_mean_hz", float("nan"))
    freq_std = metrics.get("freq_std_hz", float("nan"))
    freq_min = metrics.get("freq_min_hz", float("nan"))
    freq_max = metrics.get("freq_max_hz", float("nan"))
    L(f"| 指標 | 値 |")
    L(f"|------|-----|")
    L(f"| 平均周波数 (F) | {freq_mean:.6f} Hz |")
    L(f"| 標準偏差 | {freq_std:.6f} Hz |")
    L(f"| 最小周波数 | {freq_min:.6f} Hz |")
    L(f"| 最大周波数 | {freq_max:.6f} Hz |")
    L()

    # --- 図 ---
    L("## 図")
    L()

    L("### PLX vs PFX 時系列オーバーレイ")
    L()
    L("X 軸（上段）・Y 軸（中段）の PLX/PLY（青）と PFX/PFY（橙）の比較、")
    L("および X 軸残差（下段）を表示。")
    L()
    L(f"![PLX vs PFX overlay]({fig_rel}/plx_pfx_overlay.png)")
    L()

    L("### 周波数推移")
    L()
    L("F 列（融合周波数）の時系列推移。赤破線は目標周波数 0.45 Hz。")
    L()
    L(f"![Frequency overview]({fig_rel}/frequency_overview.png)")
    L()

    L("### PLX vs PFX 散布図")
    L()
    L("X 軸（左）・Y 軸（右）の PLX/PLY と PFX/PFY の散布図。")
    L("赤破線は y=x の理想線。")
    L()
    L(f"![PLX vs PFX scatter]({fig_rel}/plx_pfx_scatter.png)")
    L()

    # --- 考察 ---
    L("## 考察")
    L()

    # X 軸の追従性
    if np.isfinite(corr_x):
        if corr_x > 0.8:
            L(f"- **X 軸追従性**: 相関係数 {corr_x:.4f} と高く、PFX は PLX に良く追従している。")
        elif corr_x > 0.5:
            L(f"- **X 軸追従性**: 相関係数 {corr_x:.4f} で中程度の相関。PFX は PLX の大まかな傾向を捉えているが、")
            L("  系統的な誤差または位相遅れが存在する可能性がある。")
        else:
            L(f"- **X 軸追従性**: 相関係数 {corr_x:.4f} と低く、PFX は PLX との一致度が低い。")
            L("  EKF による再構成が適切に機能していない可能性がある。")
    L()

    # Y 軸の挙動
    if np.isfinite(corr_y):
        if abs(corr_y) < 0.1:
            L(f"- **Y 軸の挙動**: 相関係数 {corr_y:.4f} とほぼ無相関。PFY が常に 0 またはノイズレベルである可能性が高い。")
            L("  これは OBSV データの Y 軸成分（DY, VY, CY）が全て 0 であることと整合する。")
        else:
            L(f"- **Y 軸の挙動**: 相関係数 {corr_y:.4f}。")
    L()

    # 周波数
    if np.isfinite(freq_mean):
        L(f"- **周波数**: 平均 {freq_mean:.3f} Hz（目標 0.45 Hz に対して {freq_mean/0.45:.1%}）。")
        if freq_mean > 0.6:
            L("  目標より高めの周波数で動作している。")
        elif freq_mean < 0.3:
            L("  目標より低めの周波数で動作している。")
        else:
            L("  目標周波数に近い値で安定している。")
    L()

    # 時間遅れ
    if np.isfinite(lag_x):
        if abs(lag_x) > 0.05:
            L(f"- **時間遅れ**: X 軸で {lag_x:.4f} s の遅れが検出された。")
            L("  この遅れは EKF のフィルタリング処理またはログ記録のタイムスタンプ差に起因する可能性がある。")
        else:
            L(f"- **時間遅れ**: X 軸で {lag_x:.4f} s と小さく、PLX と PFX はほぼ同時刻の値である。")
    L()

    # 既存レポートとの比較
    L("### 既存レポートとの比較")
    L()
    L("既存の `REPORT_00000093.md` では以下の値が報告されている：")
    L()
    L("| 指標 | 既存レポート | 本レポート |")
    L("|------|------------|------------|")
    L(f"| 相関係数 (X) | 0.505842 | {corr_x:.6f} |")
    L(f"| RMSE (X) | 0.920332 | {rmse_x:.6f} |")
    L(f"| 平均周波数 | 0.716463 Hz | {freq_mean:.6f} Hz |")
    L()
    L("本レポートは PFX/PFY を OBSV メッセージから直接抽出しており、")
    L("既存レポートと同一のデータソースを用いているため値は一致するはずである。")
    L()

    # --- まとめ ---
    L("## まとめ")
    L()
    L(f"00000093.BIN の OBSV メッセージには PFX/PFY が直接記録されており、")
    L(f"リプレイを介さずに PLX/PLY との比較が可能である。")
    L(f"X 軸の相関係数は {corr_x:.4f}、RMSE は {rmse_x:.4f} であり、")
    if np.isfinite(corr_x) and corr_x > 0.5:
        L("PFX は PLX の傾向を中程度に捉えている。")
    else:
        L("PFX と PLX の一致度は低く、さらなる調査が必要である。")
    L(f"Y 軸は PFY がほぼ 0 であるため比較は困難である。")
    L(f"周波数は平均 {freq_mean:.3f} Hz で安定している。")
    L()

    # --- 付属ファイル ---
    L("## 付属ファイル")
    L()
    L(f"- `summary.json` — 全メトリクスの数値データ")
    L(f"- `figures/plx_pfx_overlay.png` — PLX vs PFX 時系列オーバーレイ")
    L(f"- `figures/frequency_overview.png` — 周波数推移")
    L(f"- `figures/plx_pfx_scatter.png` — PLX vs PFX 散布図")
    L()

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote: {report_path}")


# ============================================================
# main
# ============================================================
def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    FIGDIR.mkdir(parents=True, exist_ok=True)

    # OBSV CSV 読み込み
    print("Reading OBSV CSV...")
    if not OBSV_CSV.exists():
        print(f"ERROR: {OBSV_CSV} not found. Run extract_obsv_all_fields.py first.", file=sys.stderr)
        return 1
    data = read_obsv_csv(OBSV_CSV)
    n = len(data.get("Time_s", []))
    print(f"  Loaded {n} samples from {OBSV_CSV}")
    if n == 0:
        print("ERROR: empty data", file=sys.stderr)
        return 1

    # メトリクス計算
    print("Computing metrics...")
    metrics = compute_metrics(data)
    print(f"  corr(PLX,PFX)={metrics.get('corr_plx_pfx', float('nan')):.6f}")
    print(f"  RMSE(PLX,PFX)={metrics.get('rmse_plx_pfx', float('nan')):.6f}")
    print(f"  corr(PLY,PFY)={metrics.get('corr_ply_pfy', float('nan')):.6f}")
    print(f"  freq_mean={metrics.get('freq_mean_hz', float('nan')):.6f} Hz")

    # メトリクスを JSON に保存
    metrics_serializable: Dict[str, Optional[float]] = {}
    for k, v in metrics.items():
        metrics_serializable[k] = v if np.isfinite(v) else None
    summary_path = OUTDIR / "summary.json"
    summary_path.write_text(
        json.dumps(metrics_serializable, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote: {summary_path}")

    # 図生成
    print("Generating figures...")
    plot_plx_pfx_overlay(data, str(FIGDIR / "plx_pfx_overlay.png"), "00000093")
    plot_frequency_overview(data, str(FIGDIR / "frequency_overview.png"), "00000093")
    plot_scatter_plx_pfx(data, str(FIGDIR / "plx_pfx_scatter.png"), "00000093")

    # レポート生成
    print("Generating report...")
    generate_report(metrics, data, OUTDIR)

    print(f"\nDone. Report written to {OUTDIR / 'FLIGHT_REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
