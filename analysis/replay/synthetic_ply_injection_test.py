#!/usr/bin/env python3
"""Synthetic PLY injection test.

Generates a CSV containing only a PLY sinusoid at 0.45 Hz and runs the
EKF_CSV_Replay for Y-only (`--ekf-axis-mask 2`) across a set of `q_w` values.
Writes metrics and figures to the output directory.
"""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


TARGET_HZ = 0.45


def ensure_dirs(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_synthetic_csv(csv_path: Path, duration_s: float, fs: float, amp: float) -> None:
    t = np.arange(0.0, duration_s, 1.0 / fs)
    time_us = (t * 1e6).astype('int64')
    plx = np.zeros_like(t)
    ply = amp * np.sin(2.0 * np.pi * TARGET_HZ * t)
    plz = np.zeros_like(t)
    sw = np.ones_like(t, dtype=int)
    real_freq = np.full_like(t, TARGET_HZ)
    real_phase = np.zeros_like(t)

    df = pd.DataFrame({
        'TimeUS': time_us,
        'PLX': plx,
        'PLY': ply,
        'PLZ': plz,
        'SW': sw,
        'RealFreq': real_freq,
        'RealPhase': real_phase,
    })
    df.to_csv(csv_path, index=False)


def compute_metrics(freq: np.ndarray, t: np.ndarray, sw: np.ndarray) -> Dict[str, float]:
    on_mask = sw == 1
    if not np.any(on_mask):
        on_mask = np.ones_like(sw, dtype=bool)

    f = freq[on_mask]
    tt = t[on_mask]
    if f.size < 2:
        return {"mean_hz": float('nan'), "final_hz": float('nan'), "mae_hz": float('nan')}

    return {
        "mean_hz": float(np.mean(f)),
        "final_hz": float(f[-1]),
        "mae_hz": float(np.mean(np.abs(f - TARGET_HZ))),
    }


def make_plot(csv_input: Path, result_csv: Path, out_png: Path, title: str) -> None:
    df_in = pd.read_csv(csv_input)
    if 'TimeUS' in df_in.columns:
        t = df_in['TimeUS'].to_numpy(dtype=float) / 1e6 - df_in['TimeUS'].iloc[0] / 1e6
    elif 'Time_s' in df_in.columns:
        t = df_in['Time_s'].to_numpy(dtype=float)
    else:
        raise ValueError('Neither TimeUS nor Time_s found')

    plx = df_in['PLX'].to_numpy(dtype=float)
    ply = df_in['PLY'].to_numpy(dtype=float)
    plz = df_in['PLZ'].to_numpy(dtype=float)

    df_out = pd.read_csv(result_csv)
    t_out = df_out['Time_s'].to_numpy(dtype=float)
    f_est = df_out['EstFreq_Hz'].to_numpy(dtype=float)
    sw = df_out['SW'].to_numpy(dtype=int)

    fig, (ax_top, ax_btm) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    ax_top.plot(t, plx - np.mean(plx), label='PLX', color='tab:red', linewidth=0.8)
    ax_top.plot(t, ply - np.mean(ply), label='PLY', color='tab:green', linewidth=0.8)
    ax_top.plot(t, plz - np.mean(plz), label='PLZ', color='tab:blue', linewidth=0.8)
    ax_top.set_ylabel('Payload (relative)')
    ax_top.grid(True, alpha=0.3)
    ax_top.legend(loc='upper right')

    ax_btm.plot(t_out, f_est, label='EstFreq_Hz', color='tab:orange')
    ax_btm.axhline(TARGET_HZ, color='k', linestyle='--', label=f'Target {TARGET_HZ:.2f}Hz')
    ax_btm.set_ylabel('Estimated frequency [Hz]')
    ax_btm.set_xlabel('Time [s]')
    ax_btm.grid(True, alpha=0.3)
    ax_btm.legend(loc='best')

    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description='Synthetic PLY injection test (Y-only)')
    parser.add_argument('--replay-bin', default='build/sitl/examples/EKF_CSV_Replay')
    parser.add_argument('--outdir', default='analysis/replay/results/diagnostics/synth_ply_045_2026-04-06')
    parser.add_argument('--duration', type=float, default=75.0)
    parser.add_argument('--fs', type=float, default=100.0)
    parser.add_argument('--amp', type=float, default=1.0)
    parser.add_argument('--qws', nargs='*', default=['1e-9', '1e-5', '1e-3'])
    args = parser.parse_args()

    outdir = Path(args.outdir)
    csv_dir = outdir / 'csv'
    runs_dir = outdir / 'runs'
    fig_dir = outdir / 'figures'
    ensure_dirs(csv_dir)
    ensure_dirs(runs_dir)
    ensure_dirs(fig_dir)

    csv_input = csv_dir / f'synth_ply_{int(args.amp*100)}_dur{int(args.duration)}.csv'
    write_synthetic_csv(csv_input, args.duration, args.fs, args.amp)

    replay_bin = Path(args.replay_bin)
    metrics_rows: List[Dict[str, object]] = []

    for q_w in args.qws:
        tag = f'synth_ply_amp{args.amp}_q{q_w}'
        run_out = runs_dir / f'q_{q_w}'
        ensure_dirs(run_out)
        cmd = [
            str(replay_bin),
            '--input', str(csv_input),
            '--outdir', str(run_out),
            '--tag', tag,
            '--sw-mode', 'log',
            '--ekf-reset-on-switch', '0',
            '--ekf-axis-mask', '2',  # Y-only
            '--ekf-axis-gate', '0',
            '--ekf-w-init-hz', '0.60',
            '--ekf-q-w', str(q_w),
            '--ekf-force-hold-max', '0.0',
            '--ekf-force-reject-min', '5.0',
        ]
        print('Running:', ' '.join(cmd))
        subprocess.run(cmd, check=True)

        result_csv = run_out / f'{tag}_result.csv'
        if not result_csv.exists():
            print('Result not found:', result_csv)
            continue

        df = pd.read_csv(result_csv)
        t_ref = df['Time_s'].to_numpy(dtype=float)
        f_est = df['EstFreq_Hz'].to_numpy(dtype=float)
        sw = df['SW'].to_numpy(dtype=int)

        met = compute_metrics(f_est, t_ref, sw)
        metrics_rows.append({'q_w': q_w, **met})

        out_png = fig_dir / f'{tag}_est.png'
        make_plot(csv_input, result_csv, out_png, f'Synthetic PLY {args.amp}N q_w={q_w}')

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_csv = outdir / 'synth_ply_metrics.csv'
    metrics_df.to_csv(metrics_csv, index=False)
    print('Wrote metrics:', metrics_csv)
    print('Figures:', fig_dir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
