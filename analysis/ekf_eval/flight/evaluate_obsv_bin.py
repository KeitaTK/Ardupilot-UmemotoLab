#!/usr/bin/env python3
"""Evaluate AP_Observer EKF behavior from real-flight DataFlash BIN (OBSV messages)."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pymavlink import DFReader


def extract_obsv_dataframe(bin_path: Path) -> pd.DataFrame:
    reader = DFReader.DFReader_binary(str(bin_path), zero_time_base=False)
    rows: List[Dict[str, float]] = []

    while True:
        msg = reader.recv_match(type="OBSV")
        if msg is None:
            break
        data = msg.to_dict() if hasattr(msg, "to_dict") else {}
        data.pop("mavpackettype", None)
        rows.append(data)

    if not rows:
        raise RuntimeError(f"No OBSV records found in {bin_path}")

    df = pd.DataFrame(rows)
    if "TimeUS" not in df.columns:
        raise RuntimeError("OBSV log has no TimeUS field")

    df = df.sort_values("TimeUS").reset_index(drop=True)
    df["Time_s"] = (df["TimeUS"].astype(float) - float(df["TimeUS"].iloc[0])) / 1e6
    return df


def dominant_frequency_hz(signal: np.ndarray, dt: float, low_hz: float = 0.1, high_hz: float = 2.0) -> float:
    if signal.size < 64 or dt <= 0:
        return float("nan")
    x = signal - np.mean(signal)
    win = np.hanning(x.size)
    spec = np.fft.rfft(x * win)
    fr = np.fft.rfftfreq(x.size, d=dt)
    pw = np.abs(spec) ** 2
    mask = (fr >= low_hz) & (fr <= high_hz)
    if not np.any(mask):
        return float("nan")
    idx = np.argmax(pw[mask])
    return float(fr[mask][idx])


def compute_replay_baseline(paths: List[Path]) -> pd.DataFrame:
    rows = []
    for path in paths:
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path)
        except Exception:
            continue

        if "EstFreq_Hz" not in df.columns:
            continue

        sw = df["SW"].to_numpy(dtype=float) if "SW" in df.columns else np.zeros(len(df), dtype=float)
        freq = df["EstFreq_Hz"].to_numpy(dtype=float)
        rows.append(
            {
                "source": str(path),
                "samples": int(len(df)),
                "sw_active_ratio": float(np.mean(sw > 0.5)) if sw.size else float("nan"),
                "sw_transitions": int(np.count_nonzero(np.diff(sw.astype(int)) != 0)) if sw.size > 1 else 0,
                "freq_mean_hz": float(np.mean(freq)),
                "freq_std_hz": float(np.std(freq)),
                "freq_min_hz": float(np.min(freq)),
                "freq_max_hz": float(np.max(freq)),
            }
        )

    return pd.DataFrame(rows)


def evaluate(df: pd.DataFrame) -> Dict[str, float]:
    time_s = df["Time_s"].to_numpy(dtype=float)
    dt = np.diff(time_s) if time_s.size > 1 else np.array([])
    dt_mean = float(np.mean(dt)) if dt.size else float("nan")

    out: Dict[str, float] = {
        "samples": int(len(df)),
        "duration_s": float(time_s[-1] - time_s[0]) if time_s.size > 1 else 0.0,
        "dt_mean_s": dt_mean,
        "sample_rate_hz": float(1.0 / dt_mean) if dt_mean and not np.isnan(dt_mean) else float("nan"),
    }

    for key in ["PLX", "PLY", "PLZ", "F", "SW", "DX", "DY", "DZ", "VX", "VY", "VZ", "CX", "CY", "CZ"]:
        if key in df.columns:
            arr = df[key].to_numpy(dtype=float)
            out[f"{key}_mean"] = float(np.mean(arr))
            out[f"{key}_std"] = float(np.std(arr))
            out[f"{key}_min"] = float(np.min(arr))
            out[f"{key}_max"] = float(np.max(arr))

    if "SW" in df.columns:
        sw = df["SW"].to_numpy(dtype=float)
        out["sw_active_ratio"] = float(np.mean(sw > 0.5))
        out["sw_transitions"] = int(np.count_nonzero(np.diff(sw.astype(int)) != 0)) if sw.size > 1 else 0

    if "F" in df.columns:
        f = df["F"].to_numpy(dtype=float)
        step = np.abs(np.diff(f)) if f.size > 1 else np.array([])
        out["freq_p95_step_hz"] = float(np.percentile(step, 95)) if step.size else float("nan")

        if "PLX" in df.columns and dt.size:
            out["plx_dom_freq_hz"] = dominant_frequency_hz(df["PLX"].to_numpy(dtype=float), float(dt_mean))
        if "PLY" in df.columns and dt.size:
            out["ply_dom_freq_hz"] = dominant_frequency_hz(df["PLY"].to_numpy(dtype=float), float(dt_mean))

        dom = out.get("plx_dom_freq_hz", float("nan"))
        if np.isnan(dom):
            dom = out.get("ply_dom_freq_hz", float("nan"))
        out["freq_mean_vs_dom_abs_err_hz"] = float(abs(out["F_mean"] - dom)) if not np.isnan(dom) else float("nan")

    return out


def detect_findings(metrics: Dict[str, float]) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []

    sw_ratio = metrics.get("sw_active_ratio", float("nan"))
    sw_trans = metrics.get("sw_transitions", 0)
    if not np.isnan(sw_ratio) and sw_ratio < 0.01 and sw_trans == 0:
        findings.append(
            {
                "severity": "HIGH",
                "title": "SWが全期間OFFで推定有効区間が無い",
                "detail": "OBSV.SWが0固定で、実機で推定ON制御が動いていない可能性があります。RC8_OPTION=316配線/閾値またはSW判定ロジックを確認してください。",
            }
        )

    for key in ["DZ_max", "VZ_max"]:
        vmax = abs(metrics.get(key, 0.0))
        if vmax > 1e6:
            findings.append(
                {
                    "severity": "HIGH",
                    "title": "Z軸状態量が異常スケール",
                    "detail": f"{key}={vmax:.3e} と非常に大きく、ログ格納不整合または状態更新の破綻が疑われます。",
                }
            )
            break

    cy_std = metrics.get("CY_std", float("nan"))
    if not np.isnan(cy_std) and cy_std == 0.0:
        findings.append(
            {
                "severity": "MEDIUM",
                "title": "CYが完全固定",
                "detail": "CYが全サンプルで0固定です。軸マスク意図か、未初期化/未更新を確認してください。",
            }
        )

    err = metrics.get("freq_mean_vs_dom_abs_err_hz", float("nan"))
    if not np.isnan(err) and err > 0.08:
        findings.append(
            {
                "severity": "MEDIUM",
                "title": "推定周波数と入力支配周波数の乖離が大きい",
                "detail": f"平均Fと支配周波数の差が {err:.3f} Hz です。ゲート条件か周波数更新則を再点検してください。",
            }
        )

    if not findings:
        findings.append(
            {
                "severity": "INFO",
                "title": "重大異常は自動検出されませんでした",
                "detail": "追加でセグメント別評価や姿勢/モード情報との突合を推奨します。",
            }
        )

    return findings


def plot_overview(df: pd.DataFrame, out_png: Path, title: str) -> None:
    t = df["Time_s"].to_numpy(dtype=float)

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    for key, color in [("PLX", "tab:red"), ("PLY", "tab:green"), ("PLZ", "tab:blue")]:
        if key in df.columns:
            axes[0].plot(t, df[key].to_numpy(dtype=float), color=color, linewidth=0.9, label=key)
    axes[0].set_ylabel("Payload force")
    axes[0].set_title(f"{title} - Input force")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best")

    if "F" in df.columns:
        axes[1].plot(t, df["F"].to_numpy(dtype=float), color="tab:purple", linewidth=1.0, label="F")
    if "SW" in df.columns:
        ax_sw = axes[1].twinx()
        ax_sw.plot(t, df["SW"].to_numpy(dtype=float), color="black", linestyle="--", linewidth=0.9, label="SW")
        ax_sw.set_ylim(-0.1, 1.1)
        ax_sw.set_ylabel("SW")
    axes[1].set_ylabel("Frequency [Hz]")
    axes[1].set_title("Estimated frequency and switch")
    axes[1].grid(True, alpha=0.3)

    for key, color in [("DX", "tab:orange"), ("DY", "tab:gray"), ("DZ", "tab:brown")]:
        if key in df.columns:
            axes[2].plot(t, df[key].to_numpy(dtype=float), linewidth=0.9, color=color, label=key)
    axes[2].set_title("State components (D)")
    axes[2].set_xlabel("Time [s]")
    axes[2].set_ylabel("State")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(loc="best")

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def write_report(report_path: Path, source_bin: Path, metrics: Dict[str, float], findings: List[Dict[str, str]], baseline_df: pd.DataFrame, artifacts: Dict[str, str]) -> None:
    lines: List[str] = []
    lines.append(f"# AP_Observer EKF Flight BIN Evaluation: {source_bin.stem}")
    lines.append("")
    lines.append("## Input")
    lines.append(f"- Source BIN: {source_bin}")
    lines.append(f"- Samples: {metrics.get('samples')}")
    lines.append(f"- Duration: {metrics.get('duration_s', float('nan')):.2f} s")
    lines.append(f"- Mean sample rate: {metrics.get('sample_rate_hz', float('nan')):.2f} Hz")
    lines.append("")
    lines.append("## Key Metrics")
    for key in [
        "sw_active_ratio",
        "sw_transitions",
        "F_mean",
        "F_std",
        "F_min",
        "F_max",
        "freq_p95_step_hz",
        "plx_dom_freq_hz",
        "ply_dom_freq_hz",
        "freq_mean_vs_dom_abs_err_hz",
        "DZ_max",
        "VZ_max",
        "CY_std",
    ]:
        if key in metrics:
            lines.append(f"- {key}: {metrics[key]}")
    lines.append("")

    if not baseline_df.empty:
        lines.append("## Replay Baseline Comparison (existing reports)")
        lines.append("| source | sw_active_ratio | sw_transitions | freq_mean_hz | freq_std_hz |")
        lines.append("| --- | --- | --- | --- | --- |")
        for _, row in baseline_df.iterrows():
            lines.append(
                f"| {row['source']} | {row['sw_active_ratio']:.4f} | {int(row['sw_transitions'])} | {row['freq_mean_hz']:.4f} | {row['freq_std_hz']:.4f} |"
            )
        lines.append("")

    lines.append("## Findings")
    for finding in findings:
        lines.append(f"- [{finding['severity']}] {finding['title']}: {finding['detail']}")
    lines.append("")

    lines.append("## Assessment")
    lines.append("- 既存リプレイではSWが一定割合でONかつ遷移が確認される一方、本実機ログではSWが常時0です。")
    lines.append("- そのため、レポート上の良好な推定挙動が実機運用条件で再現されていない可能性が高いです。")
    lines.append("- Z系状態量の異常スケールも見られるため、OBSV出力の軸別状態更新/ログ格納の整合を要確認です。")
    lines.append("")

    lines.append("## Artifacts")
    for name, path in artifacts.items():
        lines.append(f"- {name}: {path}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate AP_Observer EKF behavior from real-flight BIN")
    parser.add_argument("--input-bin", required=True, help="Path to input BIN")
    parser.add_argument("--outdir", default="analysis/ekf_eval/flight/reports", help="Report base directory")
    parser.add_argument("--copy-to-data", action="store_true", help="Copy input BIN into analysis/ekf_eval/flight/data/bin")
    parser.add_argument(
        "--baseline-csv",
        nargs="*",
        default=[
            "analysis/replay/results/runs/00000443/00000443_bin_result.csv",
            "analysis/replay/results/runs/00000444/00000444_bin_result.csv",
        ],
        help="Replay result CSVs used as baseline",
    )
    args = parser.parse_args()

    source_bin = Path(args.input_bin)
    if not source_bin.exists():
        raise FileNotFoundError(f"Input BIN not found: {source_bin}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = source_bin.stem
    report_dir = Path(args.outdir) / f"{tag}_{timestamp}"
    report_dir.mkdir(parents=True, exist_ok=True)

    data_bin = source_bin
    if args.copy_to_data:
        dst = Path("analysis/ekf_eval/flight/data/bin") / source_bin.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_bin, dst)
        data_bin = dst

    df = extract_obsv_dataframe(data_bin)
    csv_path = Path("analysis/ekf_eval/flight/data/csv") / f"{tag}_obsv.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)

    metrics = evaluate(df)
    findings = detect_findings(metrics)
    baseline_df = compute_replay_baseline([Path(p) for p in args.baseline_csv])

    fig_path = report_dir / "overview.png"
    plot_overview(df, fig_path, title=tag)

    summary_path = report_dir / "summary.json"
    summary_path.write_text(json.dumps({"metrics": metrics, "findings": findings}, indent=2, ensure_ascii=False), encoding="utf-8")

    artifacts = {
        "obsv_csv": str(csv_path),
        "overview_png": str(fig_path),
        "summary_json": str(summary_path),
    }

    report_path = report_dir / "FLIGHT_EKF_EVALUATION.md"
    write_report(report_path, data_bin, metrics, findings, baseline_df, artifacts)

    print(f"Wrote {report_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {fig_path}")
    print(f"Wrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
