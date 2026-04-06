#!/usr/bin/env python3
"""Estimate RMS/amp thresholds for gating frequency updates.

Computes short-time amplitude at target frequency (0.45Hz) using overlapping
FFT windows, evaluates candidate thresholds (absolute and relative to PLX),
and selects recommended threshold(s) that keep Y below threshold while X is
often above it.

Outputs CSV summary and figures per input window and a recommended value.
"""

from __future__ import annotations

import argparse
from math import ceil
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

TARGET_HZ = 0.45


def read_signal(csv_path: Path, col: str):
    df = pd.read_csv(csv_path)
    if 'TimeUS' in df.columns:
        t = df['TimeUS'].to_numpy(dtype=float) / 1e6
        t = t - t[0]
    elif 'Time_s' in df.columns:
        t = df['Time_s'].to_numpy(dtype=float)
    else:
        raise RuntimeError('No time column')
    y = df[col].to_numpy(dtype=float)
    return t, y


def stft_amplitude_at_f(t: np.ndarray, y: np.ndarray, f0: float, window_sec: float = 2.0, step_sec: float = 1.0):
    # Estimate sampling rate
    dt = np.median(np.diff(t))
    fs = 1.0 / dt
    Nw = max(8, int(round(window_sec * fs)))
    if Nw % 2 == 1:
        Nw += 1
    step = max(1, int(round(step_sec * fs)))

    hann = np.hanning(Nw)
    amps = []
    times = []
    k_target = int(round(f0 * Nw / fs))

    for start in range(0, len(y) - Nw + 1, step):
        seg = y[start:start + Nw]
        seg = seg - np.mean(seg)
        S = np.fft.rfft(seg * hann)
        # amplitude estimate (single-sided)
        A = 2.0 * np.abs(S[k_target]) / np.sum(hann)
        amps.append(A)
        times.append(t[start + Nw // 2])

    return np.array(times), np.array(amps)


def evaluate_thresholds(times_x, amps_x, times_y, amps_y, thr_candidates):
    # Align by STFT frames (times may be identical lengths)
    # For simplicity assume same frame times
    assert len(amps_x) == len(amps_y)
    rows = []
    for thr in thr_candidates:
        frac_x = float(np.mean(amps_x > thr))
        frac_y = float(np.mean(amps_y > thr))
        rows.append({'threshold': float(thr), 'frac_x_above': frac_x, 'frac_y_above': frac_y})
    return pd.DataFrame(rows)


def plot_amps(out_png: Path, times, amps_x, amps_y, thr_list):
    fig, ax = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
    ax[0].plot(times, amps_x, label='PLX amp @0.45Hz', color='tab:red')
    ax[0].grid(True, alpha=0.3)
    ax[0].legend()
    ax[1].plot(times, amps_y, label='PLY amp @0.45Hz', color='tab:green')
    ax[1].grid(True, alpha=0.3)
    for thr in thr_list:
        ax[0].axhline(thr, color='k', linestyle='--', alpha=0.4)
        ax[1].axhline(thr, color='k', linestyle='--', alpha=0.4)
    ax[1].legend()
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description='Estimate RMS/amp thresholds for EKF gating')
    parser.add_argument('--inputs', nargs='*', default=[
        'analysis/replay/results/diagnostics/fixed_060_qw_sweep_2026-04-06/csv/00000443_w35_100_extracted.csv',
        'analysis/replay/results/diagnostics/fixed_060_qw_sweep_2026-04-06/csv/00000443_w40_110_extracted.csv',
        'analysis/replay/results/diagnostics/fixed_060_qw_sweep_2026-04-06/csv/00000444_w35_100_extracted.csv',
        'analysis/replay/results/diagnostics/fixed_060_qw_sweep_2026-04-06/csv/00000444_w40_110_extracted.csv',
    ])
    parser.add_argument('--outdir', default='analysis/replay/results/diagnostics/rms_threshold_estimation_2026-04-06')
    parser.add_argument('--window-sec', type=float, default=2.0)
    parser.add_argument('--step-sec', type=float, default=1.0)
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    thr_abs_candidates = np.array([0.01, 0.02, 0.03, 0.04, 0.05, 0.075, 0.10, 0.15, 0.20])
    results = []

    for inp in args.inputs:
        p = Path(inp)
        if not p.exists():
            print('Missing input:', p)
            continue
        times_x, amps_x = stft_amplitude_at_f(*read_signal(p, 'PLX'), TARGET_HZ, args.window_sec, args.step_sec)
        times_y, amps_y = stft_amplitude_at_f(*read_signal(p, 'PLY'), TARGET_HZ, args.window_sec, args.step_sec)

        # relative candidates based on PLX global amp
        global_amp_plx = float(np.mean(amps_x))
        rel_candidates = np.array([0.05, 0.1, 0.15, 0.2, 0.3]) * global_amp_plx
        thr_candidates = np.concatenate([thr_abs_candidates, rel_candidates])

        df_eval = evaluate_thresholds(times_x, amps_x, times_y, amps_y, thr_candidates)
        df_eval['file'] = str(p.name)
        df_eval['global_plx_mean_amp'] = global_amp_plx
        results.append(df_eval)

        # select recommended thresholds: prefer ones where frac_x >= 0.25 and frac_y <= 0.10
        good = df_eval[(df_eval.frac_x_above >= 0.25) & (df_eval.frac_y_above <= 0.10)]
        if good.empty:
            # relax to frac_x >= 0.20
            good = df_eval[(df_eval.frac_x_above >= 0.20) & (df_eval.frac_y_above <= 0.12)]

        rec = good.iloc[0].to_dict() if not good.empty else None

        # write per-file outputs
        base_stem = p.stem
        df_eval.to_csv(outdir / f'{base_stem}_threshold_eval.csv', index=False)
        plot_amps(outdir / f'{base_stem}_amps.png', times_x, amps_x, times_y, thr_candidates)
        print('Wrote eval for', p.name, 'recommended:', rec)

    if results:
        merged = pd.concat(results, ignore_index=True)
        merged.to_csv(outdir / 'thresholds_summary.csv', index=False)
        print('Wrote summary:', outdir / 'thresholds_summary.csv')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
