#!/usr/bin/env python3
"""Prototype dual-component frequency estimation on replay logs.

This script compares:
- Current single-component EKF estimate from replay output
- Single-peak spectral estimate (per-axis + fused)
- Dual-component estimate per axis (long/short period components)
- Long-period adoption algorithms for fused output
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


TARGET_HZ = 0.45
FORCE_HOLD_MAX = 0.0
FORCE_REJECT_MIN = 5.0


@dataclass
class ReplayRun:
    tag: str
    input_path: Path
    result_csv: Path


@dataclass
class DualAxisEstimate:
    single_freq: np.ndarray
    dual_long_freq: np.ndarray
    dual_short_freq: np.ndarray
    single_amp: np.ndarray
    dual_long_amp: np.ndarray
    dual_short_amp: np.ndarray
    residual_rms: np.ndarray


def ensure_csv(input_path: Path, outdir: Path) -> Path:
    if input_path.suffix.lower() != ".bin":
        return input_path
    outdir.mkdir(parents=True, exist_ok=True)
    out_csv = outdir / f"{input_path.stem}_from_bin.csv"
    cmd = [
        "python3",
        "analysis/replay/bin_to_replay_csv.py",
        "--input",
        str(input_path),
        "--output",
        str(out_csv),
    ]
    subprocess.run(cmd, check=True)
    return out_csv


def run_replay(binary: Path, input_path: Path, outdir: Path, tag: str) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(binary),
        "--input",
        str(input_path),
        "--outdir",
        str(outdir),
        "--tag",
        tag,
        "--sw-mode",
        "log",
        "--ekf-reset-on-switch",
        "0",
        "--ekf-force-hold-max",
        f"{FORCE_HOLD_MAX}",
        "--ekf-force-reject-min",
        f"{FORCE_REJECT_MIN}",
        "--ekf-axis-gate",
        "0",
    ]
    subprocess.run(cmd, check=True)
    return outdir / f"{tag}_result.csv"


def ewma(signal: np.ndarray, alpha: float) -> np.ndarray:
    out = np.zeros_like(signal)
    if signal.size == 0:
        return out
    out[0] = signal[0]
    for i in range(1, signal.size):
        out[i] = alpha * signal[i] + (1.0 - alpha) * out[i - 1]
    return out


def _find_two_peaks(freq: np.ndarray, power: np.ndarray, min_sep_hz: float) -> Tuple[float, float, float]:
    if power.size < 3:
        idx = int(np.argmax(power))
        f0 = float(freq[idx])
        return f0, f0, float(power[idx])

    local = np.where((power[1:-1] > power[:-2]) & (power[1:-1] >= power[2:]))[0] + 1
    if local.size == 0:
        local = np.array([int(np.argmax(power))])

    ranked = local[np.argsort(power[local])[::-1]]
    i0 = int(ranked[0])
    f0 = float(freq[i0])
    p0 = float(power[i0])

    i1 = i0
    for cand in ranked[1:]:
        if abs(float(freq[cand]) - f0) >= min_sep_hz:
            i1 = int(cand)
            break

    f1 = float(freq[i1])
    if f1 < f0:
        f0, f1 = f1, f0
    return f0, f1, p0


def _fit_dual_component(t: np.ndarray, y: np.ndarray, f_long: float, f_short: float) -> Tuple[float, float, float]:
    tau = t - t[0]
    a = np.column_stack(
        [
            np.sin(2.0 * np.pi * f_long * tau),
            np.cos(2.0 * np.pi * f_long * tau),
            np.sin(2.0 * np.pi * f_short * tau),
            np.cos(2.0 * np.pi * f_short * tau),
            np.ones_like(tau),
        ]
    )
    coef, _, _, _ = np.linalg.lstsq(a, y, rcond=None)
    amp_long = float(np.hypot(coef[0], coef[1]))
    amp_short = float(np.hypot(coef[2], coef[3]))
    resid = y - a @ coef
    rms = float(np.sqrt(np.mean(resid * resid)))
    return amp_long, amp_short, rms


def _fit_single_component(t: np.ndarray, y: np.ndarray, f: float) -> float:
    tau = t - t[0]
    a = np.column_stack(
        [
            np.sin(2.0 * np.pi * f * tau),
            np.cos(2.0 * np.pi * f * tau),
            np.ones_like(tau),
        ]
    )
    coef, _, _, _ = np.linalg.lstsq(a, y, rcond=None)
    return float(np.hypot(coef[0], coef[1]))


def estimate_dual_axis(
    t: np.ndarray,
    y: np.ndarray,
    fs_out: float = 20.0,
    window_sec: float = 12.0,
    hop_sec: float = 0.25,
    fmin: float = 0.25,
    fmax: float = 1.20,
    min_sep_hz: float = 0.08,
    smooth_alpha: float = 0.20,
) -> DualAxisEstimate:
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)

    t_u = np.arange(t[0], t[-1], 1.0 / fs_out)
    y_u = np.interp(t_u, t, y)

    n_win = int(window_sec * fs_out)
    n_hop = max(1, int(hop_sec * fs_out))
    if n_win < 32:
        raise ValueError("window_sec too short")

    half = n_win // 2
    centers: List[float] = []
    f_single_raw: List[float] = []
    f_long_raw: List[float] = []
    f_short_raw: List[float] = []
    amp_single_raw: List[float] = []
    amp_long_raw: List[float] = []
    amp_short_raw: List[float] = []
    residual_raw: List[float] = []

    prev_single = None
    prev_long = None
    prev_short = None

    for c in range(half, len(t_u) - half, n_hop):
        seg = y_u[c - half : c + half]
        seg_t = t_u[c - half : c + half]
        seg_z = seg - np.mean(seg)
        w = np.hanning(seg_z.size)
        spec = np.fft.rfft(seg_z * w)
        freq = np.fft.rfftfreq(seg_z.size, d=1.0 / fs_out)
        power = np.abs(spec) ** 2
        mask = (freq >= fmin) & (freq <= fmax)
        if not np.any(mask):
            continue
        f_band = freq[mask]
        p_band = power[mask]

        fl, fs, _ = _find_two_peaks(f_band, p_band, min_sep_hz=min_sep_hz)
        fdom = float(f_band[int(np.argmax(p_band))])

        if prev_long is not None and prev_short is not None and prev_single is not None:
            fl = smooth_alpha * fl + (1.0 - smooth_alpha) * prev_long
            fs = smooth_alpha * fs + (1.0 - smooth_alpha) * prev_short
            fdom = smooth_alpha * fdom + (1.0 - smooth_alpha) * prev_single

        if fs < fl + 0.01:
            fs = fl + 0.01

        amp_l, amp_s, rms = _fit_dual_component(seg_t, seg, fl, fs)
        amp_1 = _fit_single_component(seg_t, seg, fdom)

        centers.append(float(t_u[c]))
        f_single_raw.append(fdom)
        f_long_raw.append(fl)
        f_short_raw.append(fs)
        amp_single_raw.append(amp_1)
        amp_long_raw.append(amp_l)
        amp_short_raw.append(amp_s)
        residual_raw.append(rms)

        prev_single = fdom
        prev_long = fl
        prev_short = fs

    if len(centers) < 2:
        fill = np.full_like(t, 0.6, dtype=float)
        zeros = np.zeros_like(t, dtype=float)
        return DualAxisEstimate(fill, fill, fill + 0.01, zeros, zeros, zeros, zeros)

    c_t = np.asarray(centers, dtype=float)

    def interp(v: List[float]) -> np.ndarray:
        return np.interp(t, c_t, np.asarray(v, dtype=float), left=v[0], right=v[-1])

    return DualAxisEstimate(
        single_freq=interp(f_single_raw),
        dual_long_freq=interp(f_long_raw),
        dual_short_freq=interp(f_short_raw),
        single_amp=interp(amp_single_raw),
        dual_long_amp=interp(amp_long_raw),
        dual_short_amp=interp(amp_short_raw),
        residual_rms=interp(residual_raw),
    )


def metrics(freq: np.ndarray, t: np.ndarray, sw: np.ndarray, target: float = TARGET_HZ) -> Dict[str, float]:
    mask = sw == 1
    if not np.any(mask):
        mask = np.ones_like(sw, dtype=bool)
    f = freq[mask]
    tt = t[mask]
    if f.size < 2:
        return {"mean_hz": float("nan"), "std_hz": float("nan"), "mae_hz": float("nan"), "p95_step_hz": float("nan"), "max_step_hz": float("nan")}
    step = np.abs(np.diff(f))
    dt = float(np.mean(np.diff(tt))) if tt.size > 1 else 0.01
    x = f - np.mean(f)
    win = np.hanning(x.size)
    spec = np.fft.rfft(x * win)
    fr = np.fft.rfftfreq(x.size, d=dt)
    pw = np.abs(spec) ** 2
    low = float(np.sum(pw[(fr >= 0.0) & (fr < 0.5)]))
    high = float(np.sum(pw[(fr >= 2.0) & (fr < 20.0)]))
    hf_ratio = high / max(low, 1.0e-12)
    return {
        "mean_hz": float(np.mean(f)),
        "std_hz": float(np.std(f)),
        "mae_hz": float(np.mean(np.abs(f - target))),
        "p95_step_hz": float(np.percentile(step, 95)),
        "max_step_hz": float(np.max(step)),
        "hf_ratio": hf_ratio,
    }


def select_long_component_algorithm(
    long_fused: np.ndarray,
    amp_long_stack: np.ndarray,
    amp_short_stack: np.ndarray,
) -> Dict[str, np.ndarray]:
    # Candidate A: raw long component
    cand_a = long_fused.copy()

    # Candidate B: EWMA smooth
    cand_b = ewma(long_fused, alpha=0.15)

    # Candidate C: reliability-aware hold + EWMA
    ratio = np.mean(amp_long_stack / np.maximum(amp_short_stack, 1.0e-4), axis=1)
    out = np.zeros_like(long_fused)
    out[0] = long_fused[0]
    for i in range(1, long_fused.size):
        if ratio[i] < 0.55:
            raw = out[i - 1]
        else:
            raw = long_fused[i]
        out[i] = 0.18 * raw + 0.82 * out[i - 1]
    cand_c = out

    return {
        "dual_long_raw": cand_a,
        "dual_long_ewma": cand_b,
        "dual_long_reliability_hold": cand_c,
    }


def plot_axis_two_frequency(run_tag: str, t: np.ndarray, sw: np.ndarray, axes: Dict[str, DualAxisEstimate], out_png: Path) -> None:
    fig, axs = plt.subplots(3, 1, figsize=(13, 9), sharex=True)
    axis_order = ["x", "y", "z"]
    colors = {"single": "tab:gray", "long": "tab:blue", "short": "tab:orange"}

    for i, ax_name in enumerate(axis_order):
        est = axes[ax_name]
        axs[i].plot(t, est.single_freq, color=colors["single"], linewidth=0.9, label="single-peak")
        axs[i].plot(t, est.dual_long_freq, color=colors["long"], linewidth=1.0, label="dual-long")
        axs[i].plot(t, est.dual_short_freq, color=colors["short"], linewidth=1.0, label="dual-short")
        axs[i].set_ylabel(f"{ax_name.upper()} [Hz]")
        axs[i].grid(True, alpha=0.3)
        if i == 0:
            axs[i].legend(loc="upper right")
        sw_scaled = 0.25 * sw + 0.25
        axs[i].plot(t, sw_scaled, "k--", linewidth=0.6, alpha=0.5, label="SW")

    axs[2].set_xlabel("Time [s]")
    fig.suptitle(f"{run_tag}: per-axis two-frequency estimation")
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def plot_fused_compare(
    run_tag: str,
    t: np.ndarray,
    sw: np.ndarray,
    ekf_single: np.ndarray,
    single_fused: np.ndarray,
    long_fused: np.ndarray,
    candidates: Dict[str, np.ndarray],
    best_name: str,
    out_png: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.plot(t, ekf_single, linewidth=0.9, label="current EKF(single)", color="tab:purple")
    ax.plot(t, single_fused, linewidth=0.9, label="single-peak fused", color="tab:gray")
    ax.plot(t, long_fused, linewidth=1.0, label="dual-long fused(raw)", color="tab:blue", alpha=0.7)
    ax.plot(t, candidates[best_name], linewidth=1.4, label=f"selected: {best_name}", color="tab:red")
    ax.axhline(TARGET_HZ, color="black", linestyle="--", linewidth=1.0, label=f"target={TARGET_HZ:.2f}Hz")
    ax.plot(t, 0.25 * sw + 0.25, "k--", linewidth=0.6, alpha=0.45, label="SW")
    ax.set_title(f"{run_tag}: fused frequency comparison")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Frequency [Hz]")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", ncol=2)
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def plot_amplitude_ratio(run_tag: str, t: np.ndarray, axes: Dict[str, DualAxisEstimate], out_png: Path) -> None:
    fig, ax = plt.subplots(figsize=(13, 4.5))
    for name, color in [("x", "tab:red"), ("y", "tab:green"), ("z", "tab:blue")]:
        est = axes[name]
        ratio = est.dual_long_amp / np.maximum(est.dual_short_amp, 1.0e-4)
        ax.plot(t, ratio, linewidth=0.9, label=f"{name.upper()} long/short amp", color=color)
    ax.axhline(0.55, color="black", linestyle="--", linewidth=0.9, label="reliability threshold")
    ax.set_title(f"{run_tag}: long/short amplitude ratio")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Amplitude ratio")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Dual-component frequency replay analysis")
    parser.add_argument("--replay-bin", default="build/sitl/examples/RLS_CSV_Replay")
    parser.add_argument("--input-443", default="analysis/replay/data/00000443.BIN")
    parser.add_argument("--input-444", default="analysis/replay/data/00000444.BIN")
    parser.add_argument("--outdir", default="analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    replay_bin = Path(args.replay_bin)
    runs_dir = outdir / "runs"
    fig_dir = outdir / "figures"
    runs_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    # Prepare and run both logs.
    inputs = {
        "00000443": Path(args.input_443),
        "00000444": Path(args.input_444),
    }

    replay_runs: Dict[str, ReplayRun] = {}
    for tag, src in inputs.items():
        csv_input = ensure_csv(src, runs_dir / tag)
        result_csv = run_replay(replay_bin, csv_input, runs_dir / tag, f"{tag}_dual_eval")
        replay_runs[tag] = ReplayRun(tag=tag, input_path=src, result_csv=result_csv)

    all_metric_rows: List[Dict[str, object]] = []
    best_choice_per_log: Dict[str, str] = {}

    for tag, rr in replay_runs.items():
        df = pd.read_csv(rr.result_csv)
        t = df["Time_s"].to_numpy(dtype=float)
        sw = df["SW"].to_numpy(dtype=int)

        axes_est = {
            "x": estimate_dual_axis(t, df["PLX"].to_numpy(dtype=float)),
            "y": estimate_dual_axis(t, df["PLY"].to_numpy(dtype=float)),
            "z": estimate_dual_axis(t, df["PLZ"].to_numpy(dtype=float)),
        }

        single_fused = (axes_est["x"].single_freq + axes_est["y"].single_freq + axes_est["z"].single_freq) / 3.0

        amp_long_stack = np.column_stack([axes_est["x"].dual_long_amp, axes_est["y"].dual_long_amp, axes_est["z"].dual_long_amp])
        amp_short_stack = np.column_stack([axes_est["x"].dual_short_amp, axes_est["y"].dual_short_amp, axes_est["z"].dual_short_amp])
        f_long_stack = np.column_stack([axes_est["x"].dual_long_freq, axes_est["y"].dual_long_freq, axes_est["z"].dual_long_freq])

        w = amp_long_stack / np.maximum(np.sum(amp_long_stack, axis=1, keepdims=True), 1.0e-6)
        long_fused = np.sum(w * f_long_stack, axis=1)

        candidates = select_long_component_algorithm(long_fused, amp_long_stack, amp_short_stack)

        metric_map = {
            "ekf_single": metrics(df["EstFreq_Hz"].to_numpy(dtype=float), t, sw),
            "single_peak_fused": metrics(single_fused, t, sw),
            "dual_long_raw": metrics(candidates["dual_long_raw"], t, sw),
            "dual_long_ewma": metrics(candidates["dual_long_ewma"], t, sw),
            "dual_long_reliability_hold": metrics(candidates["dual_long_reliability_hold"], t, sw),
        }

        best_name = ""
        best_score = float("inf")
        for name, m in metric_map.items():
            score = float(m["p95_step_hz"]) + 0.3 * float(m["mae_hz"]) + 0.1 * float(m["std_hz"])
            if score < best_score:
                best_score = score
                best_name = name
            all_metric_rows.append(
                {
                    "log": tag,
                    "method": name,
                    "score": score,
                    **m,
                }
            )

        best_choice_per_log[tag] = best_name

        plot_axis_two_frequency(tag, t, sw, axes_est, fig_dir / f"{tag}_axis_two_frequency.png")
        plot_fused_compare(
            tag,
            t,
            sw,
            df["EstFreq_Hz"].to_numpy(dtype=float),
            single_fused,
            long_fused,
            candidates,
            best_name,
            fig_dir / f"{tag}_fused_comparison.png",
        )
        plot_amplitude_ratio(tag, t, axes_est, fig_dir / f"{tag}_amp_ratio.png")

        # Save per-sample outputs for reproducibility.
        out_df = pd.DataFrame(
            {
                "Time_s": t,
                "SW": sw,
                "EKF_Single_Hz": df["EstFreq_Hz"],
                "SingleFused_Hz": single_fused,
                "DualLongFusedRaw_Hz": candidates["dual_long_raw"],
                "DualLongEWMA_Hz": candidates["dual_long_ewma"],
                "DualLongReliabilityHold_Hz": candidates["dual_long_reliability_hold"],
                "X_Single_Hz": axes_est["x"].single_freq,
                "Y_Single_Hz": axes_est["y"].single_freq,
                "Z_Single_Hz": axes_est["z"].single_freq,
                "X_DualLong_Hz": axes_est["x"].dual_long_freq,
                "Y_DualLong_Hz": axes_est["y"].dual_long_freq,
                "Z_DualLong_Hz": axes_est["z"].dual_long_freq,
                "X_DualShort_Hz": axes_est["x"].dual_short_freq,
                "Y_DualShort_Hz": axes_est["y"].dual_short_freq,
                "Z_DualShort_Hz": axes_est["z"].dual_short_freq,
                "X_LongAmp": axes_est["x"].dual_long_amp,
                "Y_LongAmp": axes_est["y"].dual_long_amp,
                "Z_LongAmp": axes_est["z"].dual_long_amp,
                "X_ShortAmp": axes_est["x"].dual_short_amp,
                "Y_ShortAmp": axes_est["y"].dual_short_amp,
                "Z_ShortAmp": axes_est["z"].dual_short_amp,
            }
        )
        out_df.to_csv(outdir / f"{tag}_dual_component_series.csv", index=False)

    metrics_df = pd.DataFrame(all_metric_rows)
    metrics_df.to_csv(outdir / "dual_component_method_metrics.csv", index=False)

    # Choose one global best method across logs.
    agg = metrics_df.groupby("method", as_index=False).agg(
        score=("score", "mean"),
        mae_hz=("mae_hz", "mean"),
        p95_step_hz=("p95_step_hz", "mean"),
        std_hz=("std_hz", "mean"),
    )
    global_best = str(agg.sort_values("score", ascending=True).iloc[0]["method"])

    summary = {
        "thresholds": {
            "hold_max_n": FORCE_HOLD_MAX,
            "reject_min_n": FORCE_REJECT_MIN,
        },
        "best_per_log": best_choice_per_log,
        "global_best_method": global_best,
        "global_method_ranking": agg.sort_values("score", ascending=True).to_dict(orient="records"),
        "replay_runs": {
            k: {"input": str(v.input_path), "result_csv": str(v.result_csv)} for k, v in replay_runs.items()
        },
    }
    with (outdir / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    print(f"Wrote {outdir / 'dual_component_method_metrics.csv'}")
    print(f"Wrote {outdir / 'summary.json'}")
    print(f"Global best method: {global_best}")
    print("Figures:")
    print(" - figures/00000443_axis_two_frequency.png")
    print(" - figures/00000443_fused_comparison.png")
    print(" - figures/00000443_amp_ratio.png")
    print(" - figures/00000444_axis_two_frequency.png")
    print(" - figures/00000444_fused_comparison.png")
    print(" - figures/00000444_amp_ratio.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
