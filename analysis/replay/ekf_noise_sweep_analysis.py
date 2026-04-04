#!/usr/bin/env python3
"""Run EKF replay sweeps and generate a noise-focused analysis report dataset."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


TARGET_HZ = 0.45


@dataclass
class RunCase:
    tag: str
    args: List[str]


def run_replay(binary: Path, input_path: Path, outdir: Path, case: RunCase) -> Path | None:
    run_dir = outdir / "runs" / case.tag
    run_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(binary),
        "--input",
        str(input_path),
        "--outdir",
        str(run_dir),
        "--tag",
        case.tag,
    ]
    cmd.extend(case.args)
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"[WARN] replay failed for {case.tag}: {exc}")
        return None
    return run_dir / f"{case.tag}_result.csv"


def _band_power_ratio(signal: np.ndarray, dt: float, low: tuple[float, float], high: tuple[float, float]) -> float:
    if signal.size < 256 or dt <= 0.0:
        return float("nan")
    x = signal - np.mean(signal)
    win = np.hanning(x.size)
    spec = np.fft.rfft(x * win)
    freq = np.fft.rfftfreq(x.size, dt)
    power = np.abs(spec) ** 2

    low_mask = (freq >= low[0]) & (freq < low[1])
    high_mask = (freq >= high[0]) & (freq < high[1])
    low_p = float(np.sum(power[low_mask]))
    high_p = float(np.sum(power[high_mask]))
    if low_p <= 1.0e-12:
        return float("inf") if high_p > 0.0 else 1.0
    return high_p / low_p


def summarize_result(path: Path, target_hz: float) -> Dict[str, float]:
    df = pd.read_csv(path)
    if "RealSW" in df.columns:
        mask = df["RealSW"] == 1
    else:
        mask = df["SW"] == 1
    if int(mask.sum()) < 20:
        mask = np.ones(len(df), dtype=bool)

    t = df.loc[mask, "Time_s"].to_numpy(dtype=float)
    f = df.loc[mask, "EstFreq_Hz"].to_numpy(dtype=float)
    dt = float(np.mean(np.diff(t))) if t.size > 1 else 0.01
    diff = np.diff(f) if f.size > 1 else np.asarray([0.0])
    p95_step = float(np.percentile(np.abs(diff), 95)) if diff.size else 0.0
    iqr_step = float(np.percentile(np.abs(diff), 75) - np.percentile(np.abs(diff), 25)) if diff.size else 0.0
    hf_ratio = _band_power_ratio(f, dt, low=(0.0, 0.5), high=(2.0, 20.0))

    return {
        "samples": int(f.size),
        "mean_hz": float(np.mean(f)),
        "std_hz": float(np.std(f)),
        "mae_hz": float(np.mean(np.abs(f - target_hz))),
        "rmse_hz": float(np.sqrt(np.mean((f - target_hz) ** 2))),
        "p95_abs_step_hz": p95_step,
        "iqr_abs_step_hz": iqr_step,
        "hf_power_ratio": hf_ratio,
    }


def build_cases() -> tuple[List[RunCase], List[RunCase]]:
    base_args = ["--sw-mode", "always-on", "--ekf-reset-on-switch", "0", "--ekf-axis-gate", "0"]

    key_cases = [
        RunCase("always_default", list(base_args)),
        RunCase("always_low_qw", list(base_args) + ["--ekf-q-w", "0.00001"]),
        RunCase("always_high_r", list(base_args) + ["--ekf-r-meas", "0.5"]),
        RunCase("always_low_qw_high_r", list(base_args) + ["--ekf-q-w", "0.00001", "--ekf-r-meas", "0.5"]),
        RunCase("noreset_log_ref", ["--sw-mode", "log", "--ekf-reset-on-switch", "0", "--ekf-axis-gate", "0"]),
    ]

    q_w_list = [0.000001, 0.00001, 0.00005, 0.0001, 0.0005, 0.001]
    r_list = [0.08, 0.2, 0.5, 1.0]

    grid_cases: List[RunCase] = []
    for q_w in q_w_list:
        for r in r_list:
            tag = f"grid_qw_{q_w:.5f}_r_{r:.2f}".replace(".", "p")
            args = list(base_args) + ["--ekf-q-w", f"{q_w}", "--ekf-r-meas", f"{r}"]
            grid_cases.append(RunCase(tag, args))

    return key_cases, grid_cases


def plot_key_traces(outdir: Path, traces: Dict[str, pd.DataFrame]) -> None:
    fig, ax = plt.subplots(figsize=(12, 5))
    order = ["always_default", "always_low_qw", "always_high_r", "always_low_qw_high_r", "noreset_log_ref"]
    for key in order:
        df = traces[key]
        mask = (df["RealSW"] == 1) if "RealSW" in df.columns else (df["SW"] == 1)
        t = df.loc[mask, "Time_s"].to_numpy(dtype=float)
        f = df.loc[mask, "EstFreq_Hz"].to_numpy(dtype=float)
        ax.plot(t, f, linewidth=1.1, label=key)
    ax.axhline(TARGET_HZ, color="black", linestyle="--", linewidth=1.0, label=f"target={TARGET_HZ:.2f}Hz")
    ax.set_title("Estimated frequency in RealSW=1 window")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Freq [Hz]")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(outdir / "key_trace_comparison.png", dpi=170)
    plt.close(fig)


def plot_dx_cx_reference(outdir: Path, df: pd.DataFrame) -> None:
    mask = (df["RealSW"] == 1) if "RealSW" in df.columns else (df["SW"] == 1)
    t = df.loc[mask, "Time_s"].to_numpy(dtype=float)
    freq = df.loc[mask, "EstFreq_Hz"].to_numpy(dtype=float)
    dx = df.loc[mask, "DX"].to_numpy(dtype=float)
    cx = df.loc[mask, "CX"].to_numpy(dtype=float)

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    axes[0].plot(t, freq, color="tab:blue", linewidth=1.1)
    axes[0].axhline(TARGET_HZ, color="black", linestyle="--", linewidth=0.9)
    axes[0].set_ylabel("EstFreq [Hz]")
    axes[0].set_title("always_default: frequency vs model states")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(t, dx, color="tab:red", linewidth=1.0)
    axes[1].set_ylabel("DX [N]")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(t, cx, color="tab:green", linewidth=1.0)
    axes[2].set_ylabel("CX [N]")
    axes[2].set_xlabel("Time [s]")
    axes[2].grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(outdir / "always_default_freq_dx_cx.png", dpi=170)
    plt.close(fig)


def _plot_heatmap(df_grid: pd.DataFrame, value_col: str, out_png: Path, title: str) -> None:
    table = df_grid.pivot(index="q_w", columns="r_meas", values=value_col).sort_index()
    vals = table.to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    im = ax.imshow(vals, aspect="auto", origin="lower")
    ax.set_xticks(np.arange(table.shape[1]))
    ax.set_xticklabels([f"{v:.2f}" for v in table.columns])
    ax.set_yticks(np.arange(table.shape[0]))
    ax.set_yticklabels([f"{v:.5f}" for v in table.index])
    ax.set_xlabel("R_meas")
    ax.set_ylabel("Q_omega")
    ax.set_title(title)

    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            v = vals[i, j]
            ax.text(j, i, f"{v:.4f}", ha="center", va="center", color="white", fontsize=8)

    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def plot_tradeoff(df_all: pd.DataFrame, out_png: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    grid = df_all[df_all["kind"] == "grid"]
    ax.scatter(grid["mae_hz"], grid["p95_abs_step_hz"], s=35, alpha=0.85, label="grid cases")

    for _, row in df_all[df_all["kind"] == "key"].iterrows():
        ax.scatter(row["mae_hz"], row["p95_abs_step_hz"], s=70)
        ax.text(row["mae_hz"], row["p95_abs_step_hz"], row["tag"], fontsize=8)

    ax.set_xlabel("MAE vs target [Hz]")
    ax.set_ylabel("P95 abs step [Hz]")
    ax.set_title("Bias-noise tradeoff")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def parse_grid_tag(tag: str) -> tuple[float, float]:
    # grid_qw_0p00010_r_0p50 -> (0.00010, 0.50)
    body = tag.replace("grid_qw_", "")
    qw_s, r_s = body.split("_r_")
    return float(qw_s.replace("p", ".")), float(r_s.replace("p", "."))


def write_json(path: Path, payload: Dict[str, object]) -> None:
    with path.open("w") as f:
        json.dump(payload, f, indent=2)


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="EKF noise sweep analysis")
    parser.add_argument("--replay-bin", default="build/sitl/examples/RLS_CSV_Replay")
    parser.add_argument("--input", default="analysis/replay/data/00000444.BIN")
    parser.add_argument("--outdir", default="analysis/replay/results/diagnostics/ekf_noise_investigation_2026-04-04")
    parser.add_argument("--target-hz", type=float, default=TARGET_HZ)
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    binary = Path(args.replay_bin)
    input_path = Path(args.input)

    key_cases, grid_cases = build_cases()

    all_rows: List[Dict[str, object]] = []
    traces: Dict[str, pd.DataFrame] = {}

    for case in key_cases:
        result_csv = run_replay(binary, input_path, outdir, case)
        if result_csv is None:
            continue
        traces[case.tag] = pd.read_csv(result_csv)
        metrics = summarize_result(result_csv, args.target_hz)
        row = {"tag": case.tag, "kind": "key", **metrics}
        all_rows.append(row)

    for case in grid_cases:
        result_csv = run_replay(binary, input_path, outdir, case)
        if result_csv is None:
            continue
        metrics = summarize_result(result_csv, args.target_hz)
        q_w, r_meas = parse_grid_tag(case.tag)
        row = {"tag": case.tag, "kind": "grid", "q_w": q_w, "r_meas": r_meas, **metrics}
        all_rows.append(row)

    all_df = pd.DataFrame(all_rows)
    if all_df.empty:
        raise RuntimeError("No successful runs. Check replay binary and input data.")
    all_df.to_csv(outdir / "sweep_metrics.csv", index=False)

    if "always_default" in traces:
        plot_dx_cx_reference(outdir, traces["always_default"])
    if all(tag in traces for tag in ["always_default", "always_low_qw", "always_high_r", "always_low_qw_high_r", "noreset_log_ref"]):
        plot_key_traces(outdir, traces)

    grid_df = all_df[all_df["kind"] == "grid"].copy()
    if not grid_df.empty:
        _plot_heatmap(grid_df, "mae_hz", outdir / "heatmap_mae.png", "MAE vs target (RealSW=1)")
        _plot_heatmap(grid_df, "p95_abs_step_hz", outdir / "heatmap_p95_step.png", "Noise index: P95 abs step")
        _plot_heatmap(grid_df, "hf_power_ratio", outdir / "heatmap_hf_ratio.png", "HF power ratio (>2Hz / <0.5Hz)")
    plot_tradeoff(all_df, outdir / "tradeoff_mae_vs_noise.png")

    best_mae = grid_df.sort_values("mae_hz", ascending=True).head(5)
    best_noise = grid_df.sort_values("p95_abs_step_hz", ascending=True).head(5)
    payload = {
        "target_hz": args.target_hz,
        "key_cases": all_df[all_df["kind"] == "key"].sort_values("tag").to_dict(orient="records"),
        "best_by_mae": best_mae.to_dict(orient="records"),
        "best_by_noise": best_noise.to_dict(orient="records"),
    }
    write_json(outdir / "summary.json", payload)

    print(f"Wrote: {outdir / 'sweep_metrics.csv'}")
    print(f"Wrote: {outdir / 'summary.json'}")
    print("Generated figures:")
    print(" - key_trace_comparison.png")
    print(" - always_default_freq_dx_cx.png")
    print(" - heatmap_mae.png")
    print(" - heatmap_p95_step.png")
    print(" - heatmap_hf_ratio.png")
    print(" - tradeoff_mae_vs_noise.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())