#!/usr/bin/env python3
"""Compare thresholded EKF modes and smoother parameter sets for AP_Observer."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, cast

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


TARGET_HZ = 0.45
FORCE_HOLD_MAX = 1.5
FORCE_REJECT_MIN = 5.0


@dataclass
class Case:
    tag: str
    args: List[str]
    q_w: float
    r_meas: float


def ensure_csv_from_input(input_path: Path, outdir: Path) -> Path:
    if input_path.suffix.lower() != ".bin":
        return input_path

    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / f"{input_path.stem}_from_bin.csv"
    cmd = [
        "python3",
        "analysis/replay/bin_to_replay_csv.py",
        "--input",
        str(input_path),
        "--output",
        str(csv_path),
    ]
    subprocess.run(cmd, check=True)
    return csv_path


def run_replay(binary: Path, input_csv: Path, outdir: Path, case: Case) -> Path:
    run_dir = outdir / case.tag
    run_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(binary),
        "--input",
        str(input_csv),
        "--outdir",
        str(run_dir),
        "--tag",
        case.tag,
        *case.args,
    ]
    subprocess.run(cmd, check=True)
    return run_dir / f"{case.tag}_result.csv"


def read_result(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def step_metrics(df: pd.DataFrame) -> Dict[str, float]:
    mask = df["SW"] == 1 if "SW" in df.columns else np.ones(len(df), dtype=bool)
    t = df.loc[mask, "Time_s"].to_numpy(dtype=float)
    f = df.loc[mask, "EstFreq_Hz"].to_numpy(dtype=float)
    if f.size < 2:
        return {"samples": int(f.size), "mean_hz": float("nan"), "std_hz": float("nan"), "mae_hz": float("nan"), "p95_step_hz": float("nan")}
    steps = np.abs(np.diff(f))
    return {
        "samples": int(f.size),
        "mean_hz": float(np.mean(f)),
        "std_hz": float(np.std(f)),
        "mae_hz": float(np.mean(np.abs(f - TARGET_HZ))),
        "p95_step_hz": float(np.percentile(steps, 95)),
        "max_step_hz": float(np.max(steps)),
    }


def _band_power_ratio(signal: np.ndarray, dt: float, low: Tuple[float, float], high: Tuple[float, float]) -> float:
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


def force_metrics(df: pd.DataFrame) -> Dict[str, float]:
    if not {"PLX", "PLY", "PLZ"}.issubset(df.columns):
        return {"force_mean_abs": float("nan"), "force_p95_abs": float("nan"), "force_reject_ratio": float("nan")}
    force = np.sqrt(df["PLX"].to_numpy(dtype=float) ** 2 + df["PLY"].to_numpy(dtype=float) ** 2 + df["PLZ"].to_numpy(dtype=float) ** 2)
    return {
        "force_mean_abs": float(np.mean(np.abs(force))),
        "force_p95_abs": float(np.percentile(np.abs(force), 95)),
        "force_reject_ratio": float(np.mean(force >= FORCE_REJECT_MIN)),
    }


def build_cases() -> List[Case]:
    base = [
        "--ekf-force-hold-max",
        f"{FORCE_HOLD_MAX}",
        "--ekf-force-reject-min",
        f"{FORCE_REJECT_MIN}",
        "--ekf-axis-gate",
        "0",
    ]
    return [
        Case("always_default", ["--sw-mode", "always-on", "--ekf-reset-on-switch", "0", *base], 0.0005, 0.08),
        Case("switch_default", ["--sw-mode", "log", "--ekf-reset-on-switch", "0", *base], 0.0005, 0.08),
        Case("always_smooth_1", ["--sw-mode", "always-on", "--ekf-reset-on-switch", "0", *base, "--ekf-q-w", "0.00005", "--ekf-r-meas", "0.20"], 0.00005, 0.20),
        Case("always_smooth_2", ["--sw-mode", "always-on", "--ekf-reset-on-switch", "0", *base, "--ekf-q-w", "0.00001", "--ekf-r-meas", "0.50"], 0.00001, 0.50),
        Case("always_smooth_3", ["--sw-mode", "always-on", "--ekf-reset-on-switch", "0", *base, "--ekf-q-w", "0.000001", "--ekf-r-meas", "1.00"], 0.000001, 1.00),
    ]


def get_axis_result(series: pd.DataFrame, q_w: float, r_meas: float, target_hz: float = TARGET_HZ) -> Dict[str, object]:
    t = series["Time_s"].to_numpy(dtype=float)
    x = series["PLX"].to_numpy(dtype=float)
    y = series["PLY"].to_numpy(dtype=float)
    z = series["PLZ"].to_numpy(dtype=float)
    sw = series["SW"].to_numpy(dtype=int)

    omega_init = 3.7699
    omega_min = 2.1991
    omega_max = 5.7180
    q_d = 0.02
    q_d_dot = 0.05
    q_c = 0.001
    init_cov = 100.0

    n = t.size
    freq_axes = np.zeros((n, 3), dtype=float)
    amp_axes = np.zeros((n, 3), dtype=float)
    force_abs = np.sqrt(x * x + y * y + z * z)

    states = [np.array([0.0, 0.0, 0.0, omega_init], dtype=float) for _ in range(3)]
    covs = [np.eye(4, dtype=float) * init_cov for _ in range(3)]
    prev_sw = 0

    for i in range(n):
        if sw[i] == 1 and prev_sw == 0:
            states = [np.array([0.0, 0.0, 0.0, omega_init], dtype=float) for _ in range(3)]
            covs = [np.eye(4, dtype=float) * init_cov for _ in range(3)]

        active = sw[i] == 1
        measurements = [x[i], y[i], z[i]]
        for axis in range(3):
            state = states[axis]
            cov = covs[axis]

            omega_prev = float(state[3])
            abs_force = float(abs(measurements[axis]))
            hold_omega = abs_force <= FORCE_HOLD_MAX
            reject = abs_force >= FORCE_REJECT_MIN

            omega = float(np.clip(state[3], omega_min, omega_max))
            d = float(state[0])
            d_dot = float(state[1])
            c = float(state[2])

            x_pred = np.zeros(4, dtype=float)
            x_pred[0] = d + 0.01 * d_dot
            x_pred[1] = d_dot + 0.01 * (-(omega * omega) * d)
            x_pred[2] = c
            x_pred[3] = omega

            F = np.array(
                [
                    [1.0, 0.01, 0.0, 0.0],
                    [-0.01 * omega * omega, 1.0, 0.0, -2.0 * 0.01 * omega * d],
                    [0.0, 0.0, 1.0, 0.0],
                    [0.0, 0.0, 0.0, 1.0],
                ],
                dtype=float,
            )
            with np.errstate(over="ignore", invalid="ignore"):
                p_pred = F @ cov @ F.T
            p_pred[0, 0] += q_d
            p_pred[1, 1] += q_d_dot
            p_pred[2, 2] += q_c
            p_pred[3, 3] += 0.0 if (hold_omega or reject or not active) else q_w

            if not np.all(np.isfinite(p_pred)):
                p_pred = np.eye(4, dtype=float) * init_cov

            if reject:
                states[axis] = x_pred.copy()
                states[axis][3] = omega_prev
                covs[axis] = p_pred.copy()
                continue

            y_pred = x_pred[0] + x_pred[2]
            innov = float(measurements[axis] - y_pred)
            h = np.array([1.0, 0.0, 1.0, 0.0], dtype=float)
            with np.errstate(over="ignore", invalid="ignore"):
                ph = p_pred @ h
            s = float(h @ ph + max(r_meas, 1.0e-6))
            if abs(s) < 1.0e-9:
                states[axis] = x_pred.copy()
                states[axis][3] = omega_prev
                covs[axis] = p_pred.copy()
                continue

            k = ph / s
            if hold_omega:
                k[3] = 0.0
            with np.errstate(over="ignore", invalid="ignore"):
                x_new = x_pred + k * innov
            if not np.all(np.isfinite(x_new)):
                x_new = x_pred.copy()
                x_new[3] = omega_prev
            if hold_omega:
                x_new[3] = omega_prev

            i_kh = np.eye(4, dtype=float) - np.outer(k, h)
            with np.errstate(over="ignore", invalid="ignore"):
                p_new = i_kh @ p_pred
            p_new = 0.5 * (p_new + p_new.T)
            if hold_omega:
                x_new[3] = omega_prev
                p_new[3, :] = p_pred[3, :]
                p_new[:, 3] = p_pred[:, 3]

            if not np.all(np.isfinite(p_new)):
                p_new = np.eye(4, dtype=float) * init_cov

            p_new = np.clip(p_new, -1.0e6, 1.0e6)

            x_new[3] = float(np.clip(x_new[3], omega_min, omega_max))
            states[axis] = x_new
            covs[axis] = p_new
            freq_axes[i, axis] = x_new[3] / (2.0 * math.pi)
            amp_axes[i, axis] = abs(x_new[0])

        prev_sw = int(sw[i])

        if active:
            for axis in range(3):
                freq_axes[i, axis] = states[axis][3] / (2.0 * math.pi)
                amp_axes[i, axis] = abs(states[axis][0])

    fused = np.mean(freq_axes, axis=1)
    freq_axes = np.nan_to_num(
        freq_axes,
        nan=omega_init / (2.0 * math.pi),
        posinf=omega_max / (2.0 * math.pi),
        neginf=omega_min / (2.0 * math.pi),
    )
    amp_axes = np.nan_to_num(amp_axes, nan=0.0, posinf=1.0e6, neginf=0.0)
    fused = np.mean(freq_axes, axis=1)
    on_mask = sw == 1
    if not np.any(on_mask):
        on_mask = np.ones_like(sw, dtype=bool)

    t_on = t[on_mask]
    fused_on = fused[on_mask]
    dt = float(np.mean(np.diff(t_on))) if t_on.size > 1 else 0.01
    return {
        "freq_axes": freq_axes,
        "amp_axes": amp_axes,
        "fused": fused,
        "metrics": {
            "mean_hz": float(np.mean(fused_on)),
            "std_hz": float(np.std(fused_on)),
            "mae_hz": float(np.mean(np.abs(fused_on - target_hz))),
            "p95_step_hz": float(np.percentile(np.abs(np.diff(fused_on)), 95)) if fused_on.size > 1 else float("nan"),
            "hf_power_ratio": _band_power_ratio(fused_on, dt, (0.0, 0.5), (2.0, 20.0)),
        },
        "axis_metrics": {
            "x_mean_hz": float(np.mean(freq_axes[on_mask, 0])),
            "y_mean_hz": float(np.mean(freq_axes[on_mask, 1])),
            "z_mean_hz": float(np.mean(freq_axes[on_mask, 2])),
            "x_std_hz": float(np.std(freq_axes[on_mask, 0])),
            "y_std_hz": float(np.std(freq_axes[on_mask, 1])),
            "z_std_hz": float(np.std(freq_axes[on_mask, 2])),
        },
        "force_metrics": {
            "force_mean_abs": float(np.mean(np.abs(force_abs))),
            "force_p95_abs": float(np.percentile(np.abs(force_abs), 95)),
            "force_reject_ratio": float(np.mean(force_abs >= FORCE_REJECT_MIN)),
        },
    }


def plot_mode_compare(traces: Dict[str, pd.DataFrame], out_png: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 5))
    for tag in ["always_default", "switch_default"]:
        df = traces[tag]
        ax.plot(df["Time_s"], df["EstFreq_Hz"], label=tag, linewidth=1.0)
    ax.axhline(TARGET_HZ, color="black", linestyle="--", linewidth=1.0, label=f"target={TARGET_HZ:.2f}Hz")
    ax.set_title("Thresholded EKF: always-on vs switch-controlled")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Estimated frequency [Hz]")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def plot_force_thresholds(df: pd.DataFrame, out_png: Path) -> None:
    force = np.sqrt(df["PLX"] ** 2 + df["PLY"] ** 2 + df["PLZ"] ** 2)
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(df["Time_s"], force, color="tab:blue", linewidth=1.0, label="|force|")
    ax.axhline(FORCE_HOLD_MAX, color="tab:green", linestyle="--", linewidth=1.0, label="hold max 1.5N")
    ax.axhline(FORCE_REJECT_MIN, color="tab:red", linestyle="--", linewidth=1.0, label="reject min 5.0N")
    ax.set_title("Force thresholds used for omega hold/reject")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("|force| [N]")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def plot_axis_compare(results: Dict[str, Dict[str, object]], out_png: Path) -> None:
    tags = list(results.keys())
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharex=True)
    labels = ["X-axis", "Y-axis", "Z-axis", "Fused"]
    for idx, ax in enumerate(axes.ravel()):
        for tag in tags:
            fused = cast(np.ndarray, results[tag]["fused"])
            freq_axes = cast(np.ndarray, results[tag]["freq_axes"])
            t = cast(np.ndarray, results[tag]["time"])
            series = fused if idx == 3 else freq_axes[:, idx]
            ax.plot(t, series, linewidth=1.0, label=tag)
        ax.axhline(TARGET_HZ, color="black", linestyle="--", linewidth=0.9)
        ax.set_title(labels[idx])
        ax.grid(True, alpha=0.3)
    axes[1, 0].set_xlabel("Time [s]")
    axes[1, 1].set_xlabel("Time [s]")
    axes[0, 0].set_ylabel("Freq [Hz]")
    axes[1, 0].set_ylabel("Freq [Hz]")
    axes[0, 0].legend(loc="best", fontsize=8)
    fig.suptitle("Axis-wise EKF comparison with force thresholds")
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def plot_metric_bars(results: Dict[str, Dict[str, object]], out_png: Path) -> None:
    tags = list(results.keys())
    maes = [results[tag]["metrics"]["mae_hz"] for tag in tags]  # type: ignore[index]
    p95s = [results[tag]["metrics"]["p95_step_hz"] for tag in tags]  # type: ignore[index]
    fig, ax1 = plt.subplots(figsize=(12, 4.5))
    x = np.arange(len(tags))
    ax1.bar(x - 0.18, maes, width=0.36, label="MAE [Hz]", color="tab:blue")
    ax1.set_ylabel("MAE [Hz]")
    ax1.set_xticks(x)
    ax1.set_xticklabels(tags, rotation=15)
    ax1.grid(True, axis="y", alpha=0.25)
    ax2 = ax1.twinx()
    ax2.bar(x + 0.18, p95s, width=0.36, label="P95 step [Hz]", color="tab:orange")
    ax2.set_ylabel("P95 step [Hz]")
    fig.suptitle("Bias / smoothness tradeoff across parameter sets")
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def write_json(path: Path, payload: Dict[str, object]) -> None:
    with path.open("w") as f:
        json.dump(payload, f, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Thresholded EKF smoothing analysis")
    parser.add_argument("--replay-bin", default="build/sitl/examples/RLS_CSV_Replay")
    parser.add_argument("--input", default="analysis/replay/data/00000444.BIN")
    parser.add_argument("--outdir", default="analysis/replay/results/diagnostics/ekf_force_gate_smoothing_2026-04-04")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    input_path = Path(args.input)
    input_csv = ensure_csv_from_input(input_path, outdir)
    binary = Path(args.replay_bin)

    cases = build_cases()
    replay_traces: Dict[str, pd.DataFrame] = {}
    axis_results: Dict[str, Dict[str, object]] = {}
    summary_rows: List[Dict[str, object]] = []

    for case in cases:
        result_csv = run_replay(binary, input_csv, outdir, case)
        df = read_result(result_csv)
        replay_traces[case.tag] = df
        metrics = step_metrics(df)
        metrics.update(force_metrics(df))
        metrics.update({"q_w": case.q_w, "r_meas": case.r_meas})

        axis = get_axis_result(df, case.q_w, case.r_meas)
        axis["time"] = df["Time_s"].to_numpy(dtype=float)
        axis_results[case.tag] = axis

        metrics.update(cast(Dict[str, float], axis["axis_metrics"]))
        summary_rows.append({"tag": case.tag, **metrics})

    pd.DataFrame(summary_rows).to_csv(outdir / "summary_metrics.csv", index=False)

    plot_mode_compare(replay_traces, outdir / "mode_compare_thresholded.png")
    plot_force_thresholds(replay_traces["always_default"], outdir / "force_thresholds.png")
    plot_axis_compare(axis_results, outdir / "axis_compare_thresholded.png")
    plot_metric_bars(axis_results, outdir / "tradeoff_bars.png")

    payload = {
        "thresholds": {
            "hold_max_n": FORCE_HOLD_MAX,
            "reject_min_n": FORCE_REJECT_MIN,
        },
        "cases": summary_rows,
    }
    write_json(outdir / "summary.json", payload)

    print(f"Wrote {outdir / 'summary_metrics.csv'}")
    print(f"Wrote {outdir / 'summary.json'}")
    print("Generated figures:")
    print(" - mode_compare_thresholded.png")
    print(" - force_thresholds.png")
    print(" - axis_compare_thresholded.png")
    print(" - tradeoff_bars.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())