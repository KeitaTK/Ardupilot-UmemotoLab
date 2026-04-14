#!/usr/bin/env python3
"""Generate replay plots from a replay result CSV."""

import argparse
import csv
import json
import os
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np


def _read_float(row: Dict[str, str], key: str, default: float = float("nan")) -> float:
    value = row.get(key)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def read_result_csv(path: str) -> Dict[str, List[float]]:
    time_s: List[float] = []
    plx: List[float] = []
    ply: List[float] = []
    plz: List[float] = []
    prx: List[float] = []
    est_freq: List[float] = []
    real_freq: List[float] = []
    sw: List[float] = []
    real_sw: List[float] = []
    dx: List[float] = []
    vx: List[float] = []
    cx: List[float] = []
    real_phase: List[float] = []

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            time_s.append(_read_float(row, "Time_s"))
            plx.append(_read_float(row, "PLX"))
            ply.append(_read_float(row, "PLY"))
            plz.append(_read_float(row, "PLZ"))
            prx.append(_read_float(row, "PRX"))
            est_freq.append(_read_float(row, "EstFreq_Hz"))
            real_freq.append(_read_float(row, "RealFreq_Hz"))
            sw.append(_read_float(row, "SW"))
            real_sw.append(_read_float(row, "RealSW"))
            dx.append(_read_float(row, "DX"))
            vx.append(_read_float(row, "VX"))
            cx.append(_read_float(row, "CX"))
            real_phase.append(_read_float(row, "RealPhase"))

    return {
        "time_s": time_s,
        "plx": plx,
        "ply": ply,
        "plz": plz,
        "prx": prx,
        "est_freq": est_freq,
        "real_freq": real_freq,
        "sw": sw,
        "real_sw": real_sw,
        "dx": dx,
        "vx": vx,
        "cx": cx,
        "real_phase": real_phase,
    }


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return float("nan")
    return numerator / denominator


def summarize(data: Dict[str, List[float]]) -> Dict[str, float]:
    n = len(data["time_s"])
    if n == 0:
        return {"samples": 0}

    plx = np.asarray(data["plx"], dtype=float)
    prx = np.asarray(data["prx"], dtype=float)
    est = np.asarray(data["est_freq"], dtype=float)
    real = np.asarray(data["real_freq"], dtype=float)

    abs_err = np.abs(plx - prx)
    rmse = float(np.sqrt(np.mean((plx - prx) ** 2)))
    mae = float(np.mean(abs_err))
    corr = float(np.corrcoef(plx, prx)[0, 1]) if n > 2 else float("nan")

    # 高周波寄与の簡易指標: 一次差分の標準偏差
    plx_diff_std = float(np.std(np.diff(plx))) if n > 2 else float("nan")
    prx_diff_std = float(np.std(np.diff(prx))) if n > 2 else float("nan")

    sw = np.asarray(data["sw"], dtype=float)
    active_ratio = float(np.mean(sw > 0.5)) if len(sw) else float("nan")

    freq_err = np.abs(est - real)
    return {
        "samples": n,
        "duration_s": data["time_s"][-1] - data["time_s"][0],
        "est_freq_start_hz": data["est_freq"][0],
        "est_freq_end_hz": data["est_freq"][-1],
        "est_freq_min_hz": min(data["est_freq"]),
        "est_freq_max_hz": max(data["est_freq"]),
        "mean_abs_wave_error_x": mae,
        "rmse_wave_error_x": rmse,
        "corr_plx_prx": corr,
        "plx_diff_std": plx_diff_std,
        "prx_diff_std": prx_diff_std,
        "diff_std_ratio_prx_over_plx": _safe_ratio(prx_diff_std, plx_diff_std),
        "freq_mae_hz": float(np.mean(freq_err)),
        "freq_max_abs_err_hz": float(np.max(freq_err)),
        "ekf_sw_active_ratio": active_ratio,
    }


def plot_frequency(data, outpath, title):
    # この関数は使わなくなります（個別グラフ出力廃止）
    pass


def plot_waveform(data, outpath, title):
    # この関数は使わなくなります（個別グラフ出力廃止）
    pass


def plot_combined(data: Dict[str, List[float]], outpath: str, title: str) -> None:
    t = data["time_s"]
    fig, axes = plt.subplots(4, 1, figsize=(14, 11), sharex=True)

    # 1) 周波数推定
    # NOTE: Reference frequency (real_freq from log) has been found to contain incorrect values
    # and is excluded from plots. Only Estimated frequency from EKF is plotted.
    # Target frequency: ~0.45 Hz (for 00000443/00000444 logs)
    axes[0].plot(t, data["est_freq"], label="Estimated frequency", linewidth=1.0)
    axes[0].set_ylabel("Freq [Hz]")
    axes[0].set_title(f"{title} - Frequency")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="upper right")

    # 2) EKF内部状態（推定結果）
    axes[1].plot(t, data["dx"], label="DX", linewidth=0.9)
    axes[1].plot(t, data["vx"], label="VX", linewidth=0.9)
    axes[1].plot(t, data["cx"], label="CX", linewidth=0.9)
    axes[1].set_ylabel("State")
    axes[1].set_title(f"{title} - EKF states")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="upper right", ncol=3)

    # 3) 入力信号とSW
    axes[2].plot(t, data["plx"], label="PLX", linewidth=0.8)
    axes[2].plot(t, data["ply"], label="PLY", linewidth=0.8)
    axes[2].plot(t, data["plz"], label="PLZ", linewidth=0.8, alpha=0.8)
    ax2_sw = axes[2].twinx()
    ax2_sw.plot(t, data["sw"], "k--", label="SW", linewidth=0.8, alpha=0.7)
    if not all(np.isnan(np.asarray(data["real_sw"], dtype=float))):
        ax2_sw.plot(t, data["real_sw"], color="gray", linestyle=":", label="RealSW", linewidth=0.8, alpha=0.8)
    axes[2].set_ylabel("Payload force")
    ax2_sw.set_ylabel("SW")
    axes[2].set_title(f"{title} - Input forces and switch")
    axes[2].grid(True, alpha=0.3)
    h1, l1 = axes[2].get_legend_handles_labels()
    h2, l2 = ax2_sw.get_legend_handles_labels()
    axes[2].legend(h1 + h2, l1 + l2, loc="upper right", ncol=3)

    # 4) 観測と再現波形
    residual = np.asarray(data["plx"], dtype=float) - np.asarray(data["prx"], dtype=float)
    axes[3].plot(t, data["plx"], label="Measured PLX", linewidth=0.8)
    axes[3].plot(t, data["prx"], label="Reconstructed PRX", linewidth=0.9)
    axes[3].plot(t, residual, label="Residual (PLX-PRX)", linewidth=0.8, alpha=0.8)
    axes[3].set_xlabel("Time [s]")
    axes[3].set_ylabel("Force proxy")
    axes[3].set_title(f"{title} - Reconstruction quality")
    axes[3].grid(True, alpha=0.3)
    axes[3].legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(outpath, dpi=150)
    plt.close(fig)


def plot_original_vs_reconstructed(data: Dict[str, List[float]], outpath: str, title: str) -> None:
    t = np.asarray(data["time_s"], dtype=float)
    plx = np.asarray(data["plx"], dtype=float)
    prx = np.asarray(data["prx"], dtype=float)

    fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharex="col")

    axes[0, 0].plot(t, plx, color="tab:blue", linewidth=0.9)
    axes[0, 0].set_title("Original replay input - X axis (PLX)")
    axes[0, 0].set_ylabel("Force proxy")
    axes[0, 0].grid(True, alpha=0.3)

    axes[1, 0].plot(t, np.asarray(data["ply"], dtype=float), color="tab:green", linewidth=0.9)
    axes[1, 0].set_title("Original replay input - Y axis (PLY)")
    axes[1, 0].set_xlabel("Time [s]")
    axes[1, 0].set_ylabel("Force proxy")
    axes[1, 0].grid(True, alpha=0.3)

    axes[0, 1].plot(t, prx, color="tab:orange", linewidth=0.9)
    axes[0, 1].set_title("Reconstructed from estimate (PRX)")
    axes[0, 1].set_ylabel("Force proxy")
    axes[0, 1].grid(True, alpha=0.3)

    axes[1, 1].plot(t, plx, color="tab:blue", linewidth=0.8, label="PLX")
    axes[1, 1].plot(t, prx, color="tab:orange", linewidth=0.9, label="PRX")
    axes[1, 1].plot(t, plx - prx, color="tab:red", linewidth=0.8, alpha=0.8, label="Residual")
    axes[1, 1].set_title("Overlay for filter check")
    axes[1, 1].set_xlabel("Time [s]")
    axes[1, 1].set_ylabel("Force proxy")
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].legend(loc="upper right")

    fig.suptitle(f"{title} - Original vs reconstructed", y=1.01)
    fig.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)


def build_ekf_params(args: argparse.Namespace) -> Dict[str, str]:
    params: Dict[str, str] = {}
    if args.ekf_q_w is not None:
        params["q_w"] = f"{args.ekf_q_w}"
    if args.ekf_r_meas is not None:
        params["r_meas"] = f"{args.ekf_r_meas}"
    if args.ekf_w_init_hz is not None:
        params["w_init_hz"] = f"{args.ekf_w_init_hz}"
    if args.ekf_axis_mask is not None:
        params["axis_mask"] = f"{args.ekf_axis_mask}"
    if args.ekf_axis_gate is not None:
        params["axis_gate"] = f"{args.ekf_axis_gate}"
    if args.ekf_reset_on_switch is not None:
        params["reset_on_switch"] = f"{args.ekf_reset_on_switch}"
    if args.ekf_force_hold_max is not None:
        params["force_hold_max"] = f"{args.ekf_force_hold_max}"
    if args.ekf_force_reject_min is not None:
        params["force_reject_min"] = f"{args.ekf_force_reject_min}"

    for item in args.ekf_param:
        if "=" in item:
            k, v = item.split("=", 1)
            params[k.strip()] = v.strip()
    return params


def write_markdown_report(
    outpath: str,
    input_csv: str,
    combined_png: str,
    compare_png: str,
    summary: Dict[str, float],
    ekf_params: Dict[str, str],
    title: str,
) -> None:
    lines: List[str] = []
    lines.append(f"# {title} - EKF リプレイ検証レポート")
    lines.append("")
    lines.append("## 入力データ")
    lines.append(f"- リプレイ結果CSV: {input_csv}")
    lines.append("")
    lines.append("## EKF パラメータ")
    if ekf_params:
        param_map = {
            "q_w": "プロセスノイズ（周波数推定）",
            "w_init_hz": "初期周波数",
            "axis_mask": "軸マスク",
            "axis_gate": "振幅ゲート（従来）",
            "sw_mode": "スイッチモード",
            "ekf_energy_gate": "エネルギーゲート有効",
            "ekf_energy_rms_on": "エネルギーゲート閾値（ON）",
            "ekf_energy_rms_off": "エネルギーゲート閾値（OFF）",
            "ekf_energy_tau": "エネルギーゲート時定数",
            "force_hold_max": "最大保持力",
            "force_reject_min": "最小棄却力",
            "reset_on_switch": "スイッチリセット",
        }
        for key, value in ekf_params.items():
            label = param_map.get(key, key)
            lines.append(f"- {label}: {value}")
        # パラメータ解説を追加
        lines.append("")
        lines.append("### パラメータ解説")
        lines.append("- プロセスノイズ（周波数推定）q_w：周波数推定の変動許容量。大きいほど推定が敏感になる。")
        lines.append("- 初期周波数 w_init_hz：EKF開始時の周波数初期値。")
        lines.append("- 軸マスク axis_mask：推定・制御対象とする軸の選択（例：X軸のみ等）。")
        lines.append("- 振幅ゲート（従来）axis_gate：従来方式の振幅しきい値による外力判定。")
        lines.append("- スイッチモード sw_mode：外力推定のON/OFF切替方式。");
        lines.append("- エネルギーゲート有効 ekf_energy_gate：エネルギーゲート機能の有効/無効。");
        lines.append("- エネルギーゲート閾値（ON）ekf_energy_rms_on：エネルギーゲートがONになるRMSしきい値。");
        lines.append("- エネルギーゲート閾値（OFF）ekf_energy_rms_off：エネルギーゲートがOFFになるRMSしきい値。");
        lines.append("- エネルギーゲート時定数 ekf_energy_tau：エネルギーゲートの応答速度（時定数）。");
        lines.append("- 最大保持力 force_hold_max：外力推定値の最大保持値。");
        lines.append("- 最小棄却力 force_reject_min：外力推定値の最小棄却値（ノイズ抑制）。");
        lines.append("- スイッチリセット reset_on_switch：スイッチON時にEKF状態をリセットするか。");
    else:
        lines.append("- （パラメータなし）")
    lines.append("")
    lines.append("## 検証メトリクス")
    lines.append(f"- サンプル数: {summary.get('samples')}")
    lines.append(f"- 処理時間: {summary.get('duration_s'):.2f} 秒")
    lines.append(f"- 周波数推定誤差（MAE）: {summary.get('freq_mae_hz'):.6f} Hz")
    lines.append(f"- 周波数推定誤差（最大）: {summary.get('freq_max_abs_err_hz'):.6f} Hz")
    lines.append(f"- 波形再現誤差（RMSE）: {summary.get('rmse_wave_error_x'):.6f}")
    lines.append(f"- 波形相関係数: {summary.get('corr_plx_prx'):.6f}")
    lines.append(f"- 高周波抑制指標（PRX/PLX差分比）: {summary.get('diff_std_ratio_prx_over_plx'):.6f} （小さいほど良い）")
    lines.append(f"- スイッチ有効率: {summary.get('ekf_sw_active_ratio'):.4f}")
    lines.append("")
    lines.append("## 可視化図")
    lines.append("### 1. 拡張パラメータ可視化")
    lines.append("EKF推定値（DX, VX, CX）、推定周波数、入力信号、スイッチ状態、再現誤差をまとめて表示。")
    lines.append("フィルタ挙動の安定性と推定品質を総合的に確認できます。")
    lines.append(f"![combined]({os.path.basename(combined_png)})")
    lines.append("")
    lines.append("### 2. 元データ vs 再現信号（フィルタ機能確認）")
    lines.append("リプレイ入力（PLX, PLY）と EKF 推定値から再現した信号（PRX）を比較。")
    lines.append("X軸とY軸のみで、Z軸は除外し、フィルタ機能を確認します。")
    lines.append("波形一致度、残差、高周波抑制効果を視覚的に評価できます。")
    lines.append(f"![compare]({os.path.basename(compare_png)})")
    lines.append("")
    lines.append("## フィルタ機能確認ポイント")
    lines.append("### 確認項目")
    lines.append("- **PR信号追従性**: PRX が PLX のトレンドに追従しているか")
    lines.append("- **高周波抑制**: PLX の高周波ノイズが PRX で抑制されているか")
    lines.append("- **Y軸挙動**: PLY がエネルギーゲートで適切に制御されているか")
    lines.append("- **残差分布**: 残差（PLX - PRX）が小さく、一定のバイアスを示さないか")
    lines.append("")
    lines.append("### 判定基準")
    lines.append("- 相関係数 > 0.8：良好な追従性")
    lines.append("- 差分比 < 0.5：効果的な高周波抑制")
    lines.append("- スイッチ有効率 > 0.3：十分なゲート動作")

    with open(outpath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def main():
    parser = argparse.ArgumentParser(description="Create replay result plots")
    parser.add_argument("--input", required=True, help="Replay result CSV path")
    parser.add_argument("--outdir", required=True, help="Output directory for plots")
    parser.add_argument("--title", default="Replay", help="Plot title prefix")
    parser.add_argument("--ekf-q-w", type=float, default=None)
    parser.add_argument("--ekf-r-meas", type=float, default=None)
    parser.add_argument("--ekf-w-init-hz", type=float, default=None)
    parser.add_argument("--ekf-axis-mask", type=int, default=None)
    parser.add_argument("--ekf-axis-gate", type=int, default=None)
    parser.add_argument("--ekf-reset-on-switch", type=int, default=None)
    parser.add_argument("--ekf-force-hold-max", type=float, default=None)
    parser.add_argument("--ekf-force-reject-min", type=float, default=None)
    parser.add_argument(
        "--ekf-param",
        action="append",
        default=[],
        help="Additional EKF parameter in k=v format. Can be passed multiple times.",
    )
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    data = read_result_csv(args.input)
    if not data["time_s"]:
        raise SystemExit("No rows found in replay result CSV")


    # 出力ファイル名を統一
    combined_plot = os.path.join(args.outdir, "result_combined.png")
    compare_plot = os.path.join(args.outdir, "original_vs_reconstructed.png")
    summary_path = os.path.join(args.outdir, "summary.json")
    report_path = os.path.join(args.outdir, "REPLAY_EKF_REPORT.md")

    # 拡張グラフを出力
    plot_combined(data, combined_plot, args.title)
    plot_original_vs_reconstructed(data, compare_plot, args.title)

    ekf_params = build_ekf_params(args)
    summary = summarize(data)
    summary["ekf_params"] = ekf_params
    summary["artifacts"] = {
        "combined_plot": combined_plot,
        "compare_plot": compare_plot,
        "report": report_path,
    }

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    write_markdown_report(
        outpath=report_path,
        input_csv=args.input,
        combined_png=combined_plot,
        compare_png=compare_plot,
        summary=summary,
        ekf_params=ekf_params,
        title=args.title,
    )

    print(f"Wrote: {combined_plot}")
    print(f"Wrote: {compare_plot}")
    print(f"Wrote: {summary_path}")
    print(f"Wrote: {report_path}")


if __name__ == "__main__":
    main()
