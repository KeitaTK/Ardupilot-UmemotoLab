#!/usr/bin/env python3
"""Extended FFT / amplitude quantification for PLY/PLX on extracted windows.

Reads one or more extracted CSVs (from bin_to_replay_csv extraction) and
computes:
 - amplitude at target frequency by least-squares fit to sin/cos
 - band power in specified bands (e.g., 0.40-0.50 Hz and 0.10-1.00 Hz)

Produces a CSV summary and saves a figure per input file.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


TARGET_HZ = 0.45


def read_time_and_signal(csv_path: Path, col: str = 'PLY'):
    df = pd.read_csv(csv_path)
    if 'TimeUS' in df.columns:
        t = df['TimeUS'].to_numpy(dtype=float) / 1e6
        t = t - t[0]
    elif 'Time_s' in df.columns:
        t = df['Time_s'].to_numpy(dtype=float)
    else:
        raise ValueError('No time column (TimeUS/Time_s) in ' + str(csv_path))

    y = df[col].to_numpy(dtype=float)
    return t, y


def amplitude_at_freq(t: np.ndarray, y: np.ndarray, f0: float):
    # Fit y = a*sin(2pi f0 t) + b*cos(2pi f0 t) + c
    s = np.sin(2.0 * np.pi * f0 * t)
    c = np.cos(2.0 * np.pi * f0 * t)
    A = np.column_stack([s, c, np.ones_like(t)])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    a, b, offset = coef
    amp = np.sqrt(a * a + b * b)
    phase = np.arctan2(b, a)
    return float(amp), float(phase), float(offset)


def band_power(t: np.ndarray, y: np.ndarray, f_low: float, f_high: float):
    y_d = y - np.mean(y)
    n = y_d.size
    dt = np.mean(np.diff(t))
    freqs = np.fft.rfftfreq(n, dt)
    spec = np.fft.rfft(y_d)
    power = np.abs(spec) ** 2
    mask = (freqs >= f_low) & (freqs <= f_high)
    band_pow = float(np.sum(power[mask]))
    return band_pow, freqs, power


def plot_spectrum(csv_path: Path, out_png: Path, freqs: np.ndarray, power: np.ndarray, f0: float):
    fig, ax = plt.subplots(1, 1, figsize=(8, 4))
    ax.plot(freqs, power, label='power')
    ax.axvline(f0, color='r', linestyle='--', label=f'{f0} Hz')
    ax.set_xlim(0, 5.0)
    ax.set_xlabel('Frequency [Hz]')
    ax.set_ylabel('Power (arb)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.suptitle(str(csv_path.name))
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description='PLY/PLX FFT analysis')
    parser.add_argument('inputs', nargs='*', help='extracted CSV files to analyse')
    parser.add_argument('--outdir', default='analysis/replay/results/diagnostics/ply_fft_analysis_2026-04-06')
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if not args.inputs:
        # sensible defaults (from previous runs)
        base = Path('analysis/replay/results/diagnostics/fixed_060_qw_sweep_2026-04-06/csv')
        defaults = [
            base / '00000443_w35_100_extracted.csv',
            base / '00000443_w40_110_extracted.csv',
        ]
        inputs = [p for p in defaults if p.exists()]
    else:
        inputs = [Path(p) for p in args.inputs]

    rows = []
    for p in inputs:
        if not p.exists():
            print('Missing:', p)
            continue
        t_x, plx = read_time_and_signal(p, 'PLX')
        t_y, ply = read_time_and_signal(p, 'PLY')

        amp_x, ph_x, off_x = amplitude_at_freq(t_x, plx, TARGET_HZ)
        amp_y, ph_y, off_y = amplitude_at_freq(t_y, ply, TARGET_HZ)

        band_x, freqs_x, power_x = band_power(t_x, plx, 0.40, 0.50)
        band_y, freqs_y, power_y = band_power(t_y, ply, 0.40, 0.50)

        broad_x, _, _ = band_power(t_x, plx, 0.10, 1.00)
        broad_y, _, _ = band_power(t_y, ply, 0.10, 1.00)

        rows.append({
            'file': str(p),
            'amp_plx_0.45': amp_x,
            'amp_ply_0.45': amp_y,
            'band_plx_0.40_0.50': band_x,
            'band_ply_0.40_0.50': band_y,
            'broad_plx_0.10_1.00': broad_x,
            'broad_ply_0.10_1.00': broad_y,
            'band_ratio_plx_div_ply': float(band_x / band_y) if band_y > 0 else float('inf'),
        })

        # plot spectrum (from last band_power call since freqs are the same shape)
        out_png = outdir / (p.stem + '_spectrum.png')
        plot_spectrum(p, out_png, freqs_y, power_y, TARGET_HZ)

    df = pd.DataFrame(rows)
    summary_csv = outdir / 'ply_fft_summary.csv'
    df.to_csv(summary_csv, index=False)
    print('Wrote:', summary_csv)


if __name__ == '__main__':
    main()
