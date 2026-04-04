#!/usr/bin/env python3
"""Diagnose EKF frequency jumps from replay results and synthetic tests."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np


@dataclass
class ReplaySeries:
    tag: str
    time_s: np.ndarray
    plx: np.ndarray
    ply: np.ndarray
    plz: np.ndarray
    est_freq: np.ndarray
    real_freq: np.ndarray
    sw: np.ndarray


@dataclass
class AxisEKFResult:
    freq_axes_hz: np.ndarray  # shape: [N, 3] for X/Y/Z
    freq_avg_hz: np.ndarray   # shape: [N]
    amp_axes: np.ndarray      # shape: [N, 3]
    summary: Dict[str, object]


def read_result_csv(path: Path, tag: str) -> ReplaySeries:
    time_s: List[float] = []
    plx: List[float] = []
    ply: List[float] = []
    plz: List[float] = []
    est_freq: List[float] = []
    real_freq: List[float] = []
    sw: List[int] = []

    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            time_s.append(float(row["Time_s"]))
            plx.append(float(row["PLX"]))
            ply.append(float(row["PLY"]))
            plz.append(float(row["PLZ"]))
            est_freq.append(float(row["EstFreq_Hz"]))
            real_freq.append(float(row["RealFreq_Hz"]))
            sw.append(int(row["SW"]))

    return ReplaySeries(
        tag=tag,
        time_s=np.asarray(time_s, dtype=float),
        plx=np.asarray(plx, dtype=float),
        ply=np.asarray(ply, dtype=float),
        plz=np.asarray(plz, dtype=float),
        est_freq=np.asarray(est_freq, dtype=float),
        real_freq=np.asarray(real_freq, dtype=float),
        sw=np.asarray(sw, dtype=int),
    )


def dominant_freq(signal: np.ndarray, time_s: np.ndarray, fmin: float, fmax: float) -> float:
    if signal.size < 128:
        return float("nan")
    dt = float(np.mean(np.diff(time_s)))
    if dt <= 0.0:
        return float("nan")
    fs = 1.0 / dt
    x = signal - np.mean(signal)
    win = np.hanning(x.size)
    spec = np.fft.rfft(x * win)
    freq = np.fft.rfftfreq(x.size, d=1.0 / fs)
    power = np.abs(spec) ** 2
    mask = (freq >= fmin) & (freq <= fmax)
    if not np.any(mask):
        return float("nan")
    return float(freq[mask][np.argmax(power[mask])])


def band_power_ratio(signal: np.ndarray, time_s: np.ndarray, low_band: Tuple[float, float], high_band: Tuple[float, float]) -> float:
    if signal.size < 128:
        return float("nan")
    dt = float(np.mean(np.diff(time_s)))
    if dt <= 0.0:
        return float("nan")
    fs = 1.0 / dt
    x = signal - np.mean(signal)
    win = np.hanning(x.size)
    spec = np.fft.rfft(x * win)
    freq = np.fft.rfftfreq(x.size, d=1.0 / fs)
    power = np.abs(spec) ** 2

    low_mask = (freq >= low_band[0]) & (freq < low_band[1])
    high_mask = (freq >= high_band[0]) & (freq < high_band[1])
    low_p = float(np.sum(power[low_mask]))
    high_p = float(np.sum(power[high_mask]))
    if low_p <= 1.0e-12:
        return float("inf") if high_p > 0.0 else 1.0
    return high_p / low_p


def find_switch_edges(series: ReplaySeries) -> List[float]:
    idx = np.where(np.diff(series.sw) != 0)[0]
    return [float(series.time_s[i + 1]) for i in idx]


def summarize_series(series: ReplaySeries, anchor_time: float) -> Dict[str, object]:
    t = series.time_s
    f = series.est_freq

    edges = find_switch_edges(series)
    df = np.diff(f)
    dt = np.maximum(np.diff(t), 1.0e-6)
    rate = df / dt

    max_step_idx = int(np.argmax(df)) if df.size else 0
    max_rate_idx = int(np.argmax(rate)) if rate.size else 0

    pre_mask = (t >= (anchor_time - 6.0)) & (t < anchor_time)
    post_mask = (t >= anchor_time) & (t < (anchor_time + 6.0))

    dom_pre = dominant_freq(series.plx[pre_mask], t[pre_mask], 0.2, 2.0) if np.any(pre_mask) else float("nan")
    dom_post = dominant_freq(series.plx[post_mask], t[post_mask], 0.2, 2.0) if np.any(post_mask) else float("nan")

    ratio_pre = band_power_ratio(series.plx[pre_mask], t[pre_mask], (0.35, 0.65), (0.65, 0.91)) if np.any(pre_mask) else float("nan")
    ratio_post = band_power_ratio(series.plx[post_mask], t[post_mask], (0.35, 0.65), (0.65, 0.91)) if np.any(post_mask) else float("nan")

    return {
        "tag": series.tag,
        "samples": int(t.size),
        "duration_s": float(t[-1] - t[0]) if t.size else 0.0,
        "est_freq_min_hz": float(np.min(f)) if f.size else float("nan"),
        "est_freq_max_hz": float(np.max(f)) if f.size else float("nan"),
        "est_freq_mean_hz": float(np.mean(f)) if f.size else float("nan"),
        "switch_edges_s": edges,
        "anchor_time_s": float(anchor_time),
        "mean_pre_6s_hz": float(np.mean(f[pre_mask])) if np.any(pre_mask) else float("nan"),
        "mean_post_6s_hz": float(np.mean(f[post_mask])) if np.any(post_mask) else float("nan"),
        "dominant_plx_pre_hz": dom_pre,
        "dominant_plx_post_hz": dom_post,
        "high_over_low_power_pre": ratio_pre,
        "high_over_low_power_post": ratio_post,
        "largest_positive_step": {
            "time_s": float(t[max_step_idx + 1]) if df.size else float("nan"),
            "from_hz": float(f[max_step_idx]) if df.size else float("nan"),
            "to_hz": float(f[max_step_idx + 1]) if df.size else float("nan"),
            "delta_hz": float(df[max_step_idx]) if df.size else float("nan"),
        },
        "largest_positive_rate": {
            "time_s": float(t[max_rate_idx + 1]) if rate.size else float("nan"),
            "delta_hz_per_s": float(rate[max_rate_idx]) if rate.size else float("nan"),
        },
    }


def plot_overview(series: ReplaySeries, out_png: Path, anchor_time: float) -> None:
    t = series.time_s
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=False)

    axes[0].plot(t, series.est_freq, label="Replay est", linewidth=1.0)
    axes[0].set_ylabel("Freq [Hz]")
    axes[0].set_title(f"{series.tag}: estimated frequency")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best")

    axes[1].plot(t, series.sw, label="SW", color="tab:orange", linewidth=1.0)
    axes[1].set_ylabel("SW")
    axes[1].set_title(f"{series.tag}: frequency estimation switch")
    axes[1].grid(True, alpha=0.3)

    zoom_mask = (t >= (anchor_time - 6.0)) & (t <= (anchor_time + 6.0))
    axes[2].plot(t[zoom_mask], series.est_freq[zoom_mask], label="Replay est", linewidth=1.2)
    axes[2].axvline(anchor_time, color="red", linestyle="--", linewidth=1.0, label="anchor")
    axes[2].set_ylabel("Freq [Hz]")
    axes[2].set_xlabel("Time [s]")
    axes[2].set_title(f"{series.tag}: zoom around {anchor_time:.2f}s")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(loc="best")

    fig.tight_layout()
    fig.savefig(out_png, dpi=160)
    plt.close(fig)


def plot_fft_before_after(series: ReplaySeries, out_png: Path, anchor_time: float) -> None:
    pre_mask = (series.time_s >= (anchor_time - 6.0)) & (series.time_s < anchor_time)
    post_mask = (series.time_s >= anchor_time) & (series.time_s < (anchor_time + 6.0))

    def get_spectrum(signal: np.ndarray, time_s: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if signal.size < 128:
            return np.asarray([]), np.asarray([])
        dt = float(np.mean(np.diff(time_s)))
        fs = 1.0 / dt
        x = signal - np.mean(signal)
        win = np.hanning(x.size)
        spec = np.fft.rfft(x * win)
        freq = np.fft.rfftfreq(x.size, d=1.0 / fs)
        power = np.abs(spec) ** 2
        return freq, power

    pre_f, pre_p = get_spectrum(series.plx[pre_mask], series.time_s[pre_mask])
    post_f, post_p = get_spectrum(series.plx[post_mask], series.time_s[post_mask])

    fig, ax = plt.subplots(figsize=(10, 4))
    if pre_f.size:
        m = (pre_f >= 0.2) & (pre_f <= 2.0)
        ax.plot(pre_f[m], pre_p[m], label="Before window", linewidth=1.0)
    if post_f.size:
        m = (post_f >= 0.2) & (post_f <= 2.0)
        ax.plot(post_f[m], post_p[m], label="After window", linewidth=1.0)
    ax.set_title(f"{series.tag}: PLX spectrum around anchor")
    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("Power")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_png, dpi=160)
    plt.close(fig)


def plot_compare(series_list: List[ReplaySeries], out_png: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 4))
    for series in series_list:
        ax.plot(series.time_s, series.est_freq, label=f"{series.tag} est", linewidth=1.0)
    ax.set_title("Estimated frequency comparison")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Freq [Hz]")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_png, dpi=160)
    plt.close(fig)


def _constrain(value: float, low: float, high: float) -> float:
    return low if value < low else high if value > high else value


def _ekf_step_axis(
    x: np.ndarray,
    p: np.ndarray,
    measurement: float,
    active: bool,
    dt: float,
    q_d: float,
    q_d_dot: float,
    q_c: float,
    q_omega: float,
    r_meas: float,
    omega_min: float,
    omega_max: float,
) -> Tuple[np.ndarray, np.ndarray]:
    omega = _constrain(float(x[3]), omega_min, omega_max)
    d = float(x[0])
    d_dot = float(x[1])
    c = float(x[2])

    x_pred = np.zeros(4, dtype=float)
    x_pred[0] = d + dt * d_dot
    x_pred[1] = d_dot + dt * (-(omega * omega) * d)
    x_pred[2] = c
    x_pred[3] = _constrain(omega, omega_min, omega_max)

    f = np.array(
        [
            [1.0, dt, 0.0, 0.0],
            [-dt * omega * omega, 1.0, 0.0, -2.0 * dt * omega * d],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )

    p_pred = f @ p @ f.T
    p_pred[0, 0] += q_d
    p_pred[1, 1] += q_d_dot
    p_pred[2, 2] += q_c
    p_pred[3, 3] += q_omega if active else 0.0

    h = np.array([1.0, 0.0, 1.0, 0.0], dtype=float)
    innov = measurement - (x_pred[0] + x_pred[2])
    pht = p_pred @ h
    s = float(h @ pht + max(r_meas, 1.0e-6))
    if abs(s) < 1.0e-9:
        return x, p

    k = pht / s
    x_new = x_pred + k * innov

    p_new = (np.eye(4, dtype=float) - np.outer(k, h)) @ p_pred
    p_new = 0.5 * (p_new + p_new.T)
    x_new[3] = _constrain(float(x_new[3]), omega_min, omega_max)
    return x_new, p_new


def _masked_axis_average(freq_axes_hz: np.ndarray, axis_mask: np.ndarray, fallback: np.ndarray) -> np.ndarray:
    denom = np.sum(axis_mask, axis=1)
    out = fallback.copy()
    valid = denom > 0.0
    if np.any(valid):
        out[valid] = np.sum(freq_axes_hz[valid] * axis_mask[valid], axis=1) / denom[valid]
    return out


def simulate_axiswise_ekf(series: ReplaySeries, target_freq_hz: float = 0.45) -> AxisEKFResult:
    # Defaults are aligned with AP_Observer replay path.
    q_d = 0.02
    q_d_dot = 0.05
    q_c = 0.001
    q_omega = 0.0005
    r_meas = 0.08
    omega_init = 3.7699
    omega_min = 2.1991
    omega_max = 5.7180
    init_cov = 100.0

    n = int(series.time_s.size)
    freq_axes_hz = np.zeros((n, 3), dtype=float)
    amp_axes = np.zeros((n, 3), dtype=float)

    x_states = [np.array([0.0, 0.0, 0.0, omega_init], dtype=float) for _ in range(3)]
    p_states = [np.eye(4, dtype=float) * init_cov for _ in range(3)]
    prev_sw = 0

    for i in range(n):
        cur_sw = int(series.sw[i])
        if cur_sw == 1 and prev_sw == 0:
            x_states = [np.array([0.0, 0.0, 0.0, omega_init], dtype=float) for _ in range(3)]
            p_states = [np.eye(4, dtype=float) * init_cov for _ in range(3)]

        active = cur_sw == 1
        measurements = [float(series.plx[i]), float(series.ply[i]), float(series.plz[i])]
        for axis in range(3):
            x_states[axis], p_states[axis] = _ekf_step_axis(
                x_states[axis],
                p_states[axis],
                measurements[axis],
                active,
                dt=0.01,
                q_d=q_d,
                q_d_dot=q_d_dot,
                q_c=q_c,
                q_omega=q_omega,
                r_meas=r_meas,
                omega_min=omega_min,
                omega_max=omega_max,
            )

            omega = max(float(x_states[axis][3]), 1.0e-6)
            freq_axes_hz[i, axis] = omega / (2.0 * math.pi)
            # Use |d| as a stable excitation proxy for threshold studies.
            amp_axes[i, axis] = abs(float(x_states[axis][0]))

        prev_sw = cur_sw

    freq_avg_hz = np.mean(freq_axes_hz, axis=1)
    rmse = float(np.sqrt(np.mean((freq_avg_hz - series.est_freq) ** 2)))
    mae = float(np.mean(np.abs(freq_avg_hz - series.est_freq)))

    switch_edges = find_switch_edges(series)
    on_time = switch_edges[0] if len(switch_edges) >= 1 else 72.0
    off_time = switch_edges[1] if len(switch_edges) >= 2 else float(series.time_s[-1])

    pre_mask = (series.time_s >= max(0.0, on_time - 12.0)) & (series.time_s < on_time)
    post_mask = (series.time_s >= on_time) & (series.time_s < off_time)

    fx = freq_axes_hz[:, 0]
    fy = freq_axes_hz[:, 1]
    fz = freq_axes_hz[:, 2]
    f_xy = 0.5 * (fx + fy)

    # Evaluate a simple per-axis amplitude gate candidate.
    amp_threshold_scan: Dict[str, Dict[str, float]] = {}
    for th in (0.2, 0.3, 0.4, 0.5):
        axis_mask = (amp_axes >= th).astype(float)
        gated = _masked_axis_average(freq_axes_hz, axis_mask, fallback=fx)
        amp_threshold_scan[f"amp_ge_{th:.1f}"] = {
            "pre_mean_hz": float(np.mean(gated[pre_mask])) if np.any(pre_mask) else float("nan"),
            "post_mean_hz": float(np.mean(gated[post_mask])) if np.any(post_mask) else float("nan"),
        }

    high_region = (series.sw == 1) & (freq_avg_hz > 0.62)

    summary = {
        "target_frequency_hz": float(target_freq_hz),
        "reproduction_rmse_hz": rmse,
        "reproduction_mae_hz": mae,
        "switch_on_s": float(on_time),
        "switch_off_s": float(off_time),
        "pre_on_window_s": [float(max(0.0, on_time - 12.0)), float(on_time)],
        "post_on_window_s": [float(on_time), float(off_time)],
        "pre_on": {
            "replay_mean_hz": float(np.mean(series.est_freq[pre_mask])) if np.any(pre_mask) else float("nan"),
            "xyz_mean_hz": float(np.mean(freq_avg_hz[pre_mask])) if np.any(pre_mask) else float("nan"),
            "x_mean_hz": float(np.mean(fx[pre_mask])) if np.any(pre_mask) else float("nan"),
            "y_mean_hz": float(np.mean(fy[pre_mask])) if np.any(pre_mask) else float("nan"),
            "z_mean_hz": float(np.mean(fz[pre_mask])) if np.any(pre_mask) else float("nan"),
            "x_abs_error_vs_target_hz": float(np.mean(np.abs(fx[pre_mask] - target_freq_hz))) if np.any(pre_mask) else float("nan"),
        },
        "post_on": {
            "replay_mean_hz": float(np.mean(series.est_freq[post_mask])) if np.any(post_mask) else float("nan"),
            "xyz_mean_hz": float(np.mean(freq_avg_hz[post_mask])) if np.any(post_mask) else float("nan"),
            "xy_mean_hz": float(np.mean(f_xy[post_mask])) if np.any(post_mask) else float("nan"),
            "x_mean_hz": float(np.mean(fx[post_mask])) if np.any(post_mask) else float("nan"),
            "y_mean_hz": float(np.mean(fy[post_mask])) if np.any(post_mask) else float("nan"),
            "z_mean_hz": float(np.mean(fz[post_mask])) if np.any(post_mask) else float("nan"),
            "x_abs_error_vs_target_hz": float(np.mean(np.abs(fx[post_mask] - target_freq_hz))) if np.any(post_mask) else float("nan"),
            "amp_mean": {
                "x": float(np.mean(amp_axes[post_mask, 0])) if np.any(post_mask) else float("nan"),
                "y": float(np.mean(amp_axes[post_mask, 1])) if np.any(post_mask) else float("nan"),
                "z": float(np.mean(amp_axes[post_mask, 2])) if np.any(post_mask) else float("nan"),
            },
        },
        "high_freq_region_sw_on": {
            "samples": int(np.sum(high_region)),
            "start_s": float(series.time_s[high_region][0]) if np.any(high_region) else float("nan"),
            "end_s": float(series.time_s[high_region][-1]) if np.any(high_region) else float("nan"),
            "axis_mean_hz": {
                "x": float(np.mean(fx[high_region])) if np.any(high_region) else float("nan"),
                "y": float(np.mean(fy[high_region])) if np.any(high_region) else float("nan"),
                "z": float(np.mean(fz[high_region])) if np.any(high_region) else float("nan"),
            },
        },
        "amp_threshold_scan": amp_threshold_scan,
    }

    return AxisEKFResult(
        freq_axes_hz=freq_axes_hz,
        freq_avg_hz=freq_avg_hz,
        amp_axes=amp_axes,
        summary=summary,
    )


def plot_axis_ekf_result(series: ReplaySeries, axis_result: AxisEKFResult, out_png: Path, anchor_time: float) -> None:
    t = series.time_s
    fx = axis_result.freq_axes_hz[:, 0]
    fy = axis_result.freq_axes_hz[:, 1]
    fz = axis_result.freq_axes_hz[:, 2]

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    axes[0].plot(t, series.est_freq, label="Replay est", linewidth=1.0, color="tab:blue")
    axes[0].plot(t, axis_result.freq_avg_hz, label="Axis-model avg", linewidth=1.0, color="tab:purple", alpha=0.9)
    axes[0].plot(t, fx, label="Axis X", linewidth=0.9)
    axes[0].plot(t, fy, label="Axis Y", linewidth=0.9)
    axes[0].plot(t, fz, label="Axis Z", linewidth=0.9)
    axes[0].axhline(0.45, color="black", linestyle="--", linewidth=1.0, label="target=0.45Hz")
    axes[0].set_ylabel("Freq [Hz]")
    axes[0].set_title(f"{series.tag}: axis-wise EKF frequency")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best", ncol=3)

    # Cap visualization range so outliers do not dominate the subplot.
    amp = axis_result.amp_axes
    amp_clip = 2.0
    axes[1].plot(t, np.minimum(amp[:, 0], amp_clip), label="Amp X", linewidth=1.0)
    axes[1].plot(t, np.minimum(amp[:, 1], amp_clip), label="Amp Y", linewidth=1.0)
    axes[1].plot(t, np.minimum(amp[:, 2], amp_clip), label="Amp Z", linewidth=1.0)
    axes[1].set_ylabel("Estimated amp")
    axes[1].set_title("Per-axis estimated harmonic amplitude (clipped)")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best")

    axes[2].plot(t, series.sw, label="SW", color="tab:orange", linewidth=1.0)
    axes[2].axvline(anchor_time, color="red", linestyle="--", linewidth=1.0, label="switch-on")
    axes[2].set_ylabel("SW")
    axes[2].set_xlabel("Time [s]")
    axes[2].set_title("Frequency estimation switch")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(loc="best")

    fig.tight_layout()
    fig.savefig(out_png, dpi=160)
    plt.close(fig)


def write_synthetic_input(path: Path, sw_mode: str, duration_s: float, dt_s: float, base_freq_hz: float) -> None:
    n = int(duration_s / dt_s)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["TimeUS", "PLX", "PLY", "PLZ", "SW", "F", "P"])
        for i in range(n):
            t = i * dt_s
            time_us = int(round(t * 1.0e6))
            base = math.sin(2.0 * math.pi * base_freq_hz * t)
            hf = 0.08 * math.sin(2.0 * math.pi * 1.8 * t)
            noise = 0.03 * math.sin(2.0 * math.pi * 7.3 * t)

            if sw_mode == "off_all":
                sw = 0
                amp = 1.0 if t < 100.0 else 0.2
            elif sw_mode == "on_all":
                sw = 1
                amp = 1.0 if t < 100.0 else 0.2
            elif sw_mode == "on_then_off":
                sw = 1 if 20.0 <= t < 100.0 else 0
                amp = 1.0 if t < 100.0 else 0.2
            else:
                raise ValueError(sw_mode)

            plx = amp * base + hf + noise
            writer.writerow([time_us, f"{plx:.6f}", "0.0", "0.0", sw, f"{base_freq_hz:.4f}", "0.0"])


def run_replay(
    binary: Path,
    input_path: Path,
    outdir: Path,
    tag: str,
    extra_args: List[str] | None = None,
) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [str(binary), "--input", str(input_path), "--outdir", str(outdir), "--tag", tag]
    if extra_args:
        cmd.extend(extra_args)
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return outdir / f"{tag}_result.csv"


def summarize_target_tracking(series: ReplaySeries, target_hz: float) -> Dict[str, float]:
    on_mask = series.sw == 1
    eval_mask = on_mask if np.any(on_mask) else np.ones_like(series.est_freq, dtype=bool)
    freq = series.est_freq[eval_mask]
    err = freq - target_hz

    rising_edges = np.where(np.diff(series.sw) > 0)[0]
    jump_on = float("nan")
    if rising_edges.size:
        idx = int(rising_edges[0])
        jump_on = float(series.est_freq[idx + 1] - series.est_freq[idx])

    return {
        "samples": int(freq.size),
        "mean_hz": float(np.mean(freq)),
        "std_hz": float(np.std(freq)),
        "min_hz": float(np.min(freq)),
        "max_hz": float(np.max(freq)),
        "mae_vs_target_hz": float(np.mean(np.abs(err))),
        "rmse_vs_target_hz": float(np.sqrt(np.mean(err * err))),
        "jump_at_first_on_hz": jump_on,
    }


def plot_reset_gate_scenarios(
    traces: Dict[str, ReplaySeries],
    out_png: Path,
    target_hz: float,
) -> None:
    fig, ax = plt.subplots(figsize=(12, 4))
    order = ["baseline_reset_log", "noreset_log", "noreset_always_on", "best_gate_always_on"]
    for key in order:
        if key in traces:
            ax.plot(traces[key].time_s, traces[key].est_freq, linewidth=1.0, label=key)
    ax.axhline(target_hz, color="black", linestyle="--", linewidth=1.0, label=f"target={target_hz:.2f}Hz")
    ax.set_title("Switch reset / always-on / axis-gate comparison")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Estimated freq [Hz]")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_png, dpi=160)
    plt.close(fig)


def noreset_gate_validation(
    binary: Path,
    outdir: Path,
    input_bin_444: Path,
    target_hz: float = 0.45,
) -> Dict[str, object]:
    outdir.mkdir(parents=True, exist_ok=True)

    scenarios = {
        "baseline_reset_log": ["--sw-mode", "log", "--ekf-reset-on-switch", "1", "--ekf-axis-gate", "0"],
        "noreset_log": ["--sw-mode", "log", "--ekf-reset-on-switch", "0", "--ekf-axis-gate", "0"],
        "noreset_always_on": ["--sw-mode", "always-on", "--ekf-reset-on-switch", "0", "--ekf-axis-gate", "0"],
    }

    traces: Dict[str, ReplaySeries] = {}
    scenario_summary: Dict[str, Dict[str, float]] = {}
    gate_scan: List[Dict[str, object]] = []
    summary: Dict[str, object] = {
        "target_hz": target_hz,
        "scenarios": scenario_summary,
        "gate_scan": gate_scan,
    }

    for name, args in scenarios.items():
        result_csv = run_replay(binary, input_bin_444, outdir / name, name, extra_args=args)
        series = read_result_csv(result_csv, name)
        traces[name] = series
        scenario_summary[name] = summarize_target_tracking(series, target_hz)

    gate_candidates = [
        {"amp_min": 0.08, "amp_max": 1.20, "innov_max": 0.80, "nis_max": 6.0},
        {"amp_min": 0.10, "amp_max": 1.00, "innov_max": 0.70, "nis_max": 4.0},
        {"amp_min": 0.12, "amp_max": 0.90, "innov_max": 0.60, "nis_max": 3.5},
        {"amp_min": 0.15, "amp_max": 0.90, "innov_max": 0.60, "nis_max": 3.0},
        {"amp_min": 0.18, "amp_max": 0.80, "innov_max": 0.50, "nis_max": 2.5},
    ]

    best_candidate: Dict[str, object] | None = None
    best_series: ReplaySeries | None = None
    best_mae = float("inf")

    for idx, cand in enumerate(gate_candidates):
        tag = f"gate_scan_{idx:02d}"
        args = [
            "--sw-mode",
            "always-on",
            "--ekf-reset-on-switch",
            "0",
            "--ekf-axis-gate",
            "1",
            "--ekf-amp-min",
            f"{cand['amp_min']}",
            "--ekf-amp-max",
            f"{cand['amp_max']}",
            "--ekf-innov-max",
            f"{cand['innov_max']}",
            "--ekf-nis-max",
            f"{cand['nis_max']}",
        ]
        result_csv = run_replay(binary, input_bin_444, outdir / tag, tag, extra_args=args)
        series = read_result_csv(result_csv, tag)
        metric = summarize_target_tracking(series, target_hz)
        entry = {
            "tag": tag,
            "params": cand,
            "metric": metric,
        }
        gate_scan.append(entry)
        if metric["mae_vs_target_hz"] < best_mae:
            best_mae = metric["mae_vs_target_hz"]
            best_candidate = entry
            best_series = series

    if best_candidate is not None and best_series is not None:
        summary["best_gate_always_on"] = best_candidate
        traces["best_gate_always_on"] = best_series

    plot_reset_gate_scenarios(traces, outdir / "reset_gate_compare_00000444.png", target_hz)
    return summary


def synthetic_hold_test(binary: Path, outdir: Path) -> Dict[str, object]:
    outdir.mkdir(parents=True, exist_ok=True)
    synth_dir = outdir / "synthetic_inputs"
    synth_dir.mkdir(parents=True, exist_ok=True)

    cases = ["off_all", "on_all", "on_then_off"]
    summaries: Dict[str, object] = {}
    traces: Dict[str, ReplaySeries] = {}

    for case in cases:
        input_csv = synth_dir / f"{case}.csv"
        write_synthetic_input(input_csv, case, duration_s=160.0, dt_s=0.01, base_freq_hz=0.6)
        result_csv = run_replay(binary, input_csv, outdir / case, case)
        series = read_result_csv(result_csv, case)
        traces[case] = series

        off_mask = series.sw == 0
        on_mask = series.sw == 1
        summaries[case] = {
            "est_freq_min_hz": float(np.min(series.est_freq)),
            "est_freq_max_hz": float(np.max(series.est_freq)),
            "est_freq_mean_hz": float(np.mean(series.est_freq)),
            "off_span_hz": float(np.max(series.est_freq[off_mask]) - np.min(series.est_freq[off_mask])) if np.any(off_mask) else 0.0,
            "on_span_hz": float(np.max(series.est_freq[on_mask]) - np.min(series.est_freq[on_mask])) if np.any(on_mask) else 0.0,
        }

    fig, ax = plt.subplots(figsize=(12, 5))
    for case, series in traces.items():
        ax.plot(series.time_s, series.est_freq, label=case, linewidth=1.0)
    ax.axhline(0.6, color="black", linestyle="--", linewidth=1.0, label="true=0.6Hz")
    ax.set_title("Synthetic hold behavior test")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Estimated freq [Hz]")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(outdir / "synthetic_hold_behavior.png", dpi=160)
    plt.close(fig)

    return summaries


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose EKF replay frequency jump")
    parser.add_argument("--result-443", default="analysis/replay/results/runs/00000443/00000443_bin_result.csv")
    parser.add_argument("--result-444", default="analysis/replay/results/runs/00000444/00000444_bin_result.csv")
    parser.add_argument("--input-bin-444", default="analysis/replay/data/00000444.BIN")
    parser.add_argument("--outdir", default="analysis/replay/results/diagnostics")
    parser.add_argument("--replay-bin", default="build/sitl/examples/RLS_CSV_Replay")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    series_443 = read_result_csv(Path(args.result_443), "00000443")
    series_444 = read_result_csv(Path(args.result_444), "00000444")

    anchor_443 = find_switch_edges(series_443)[0] if find_switch_edges(series_443) else 72.0
    anchor_444 = find_switch_edges(series_444)[0] if find_switch_edges(series_444) else 72.0

    summary_443 = summarize_series(series_443, anchor_443)
    summary_444 = summarize_series(series_444, anchor_444)

    axis_ekf_443 = simulate_axiswise_ekf(series_443, target_freq_hz=0.45)
    axis_ekf_444 = simulate_axiswise_ekf(series_444, target_freq_hz=0.45)

    plot_overview(series_443, outdir / "overview_00000443.png", anchor_443)
    plot_overview(series_444, outdir / "overview_00000444.png", anchor_444)
    plot_fft_before_after(series_443, outdir / "spectrum_00000443.png", anchor_443)
    plot_fft_before_after(series_444, outdir / "spectrum_00000444.png", anchor_444)
    plot_compare([series_443, series_444], outdir / "compare_443_444.png")
    plot_axis_ekf_result(series_443, axis_ekf_443, outdir / "axis_ekf_00000443.png", anchor_443)
    plot_axis_ekf_result(series_444, axis_ekf_444, outdir / "axis_ekf_00000444.png", anchor_444)

    replay_bin = Path(args.replay_bin)
    synthetic_summary = synthetic_hold_test(replay_bin, outdir / "synthetic")
    noreset_gate_summary = noreset_gate_validation(
        replay_bin,
        outdir / "switch_gate_validation",
        Path(args.input_bin_444),
        target_hz=0.45,
    )

    summary = {
        "run_00000443": summary_443,
        "run_00000444": summary_444,
        "axis_ekf_00000443": axis_ekf_443.summary,
        "axis_ekf_00000444": axis_ekf_444.summary,
        "synthetic_hold_test": synthetic_summary,
        "switch_gate_validation_00000444": noreset_gate_summary,
    }
    with (outdir / "diagnostic_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    print(f"Wrote summary: {outdir / 'diagnostic_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
