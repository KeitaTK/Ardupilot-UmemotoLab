#!/usr/bin/env python3
"""Plot current EKF energy-gate indicators for X/Y axes.

The implementation mirrors AP_Observer:
- band proxy = LPF(0.80Hz) - LPF(0.25Hz)
- power EMA with tau
- hysteresis gate with ON/OFF thresholds on RMS (power uses squared thresholds)
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SAMPLE_FREQ_HZ = 100.0
FAST_CUTOFF_HZ = 0.80
SLOW_CUTOFF_HZ = 0.25


@dataclass
class BiquadParams:
    cutoff_freq: float
    sample_freq: float
    a1: float
    a2: float
    b0: float
    b1: float
    b2: float


class DigitalBiquadFilter:
    def __init__(self, params: BiquadParams) -> None:
        self.params = params
        self.delay_1 = 0.0
        self.delay_2 = 0.0
        self.initialized = False

    @staticmethod
    def compute_params(sample_freq: float, cutoff_freq: float) -> BiquadParams:
        cutoff = min(cutoff_freq, sample_freq * 0.4)
        if cutoff <= 0.0:
            return BiquadParams(cutoff, sample_freq, 0.0, 0.0, 1.0, 0.0, 0.0)

        fr = sample_freq / cutoff
        ohm = math.tan(math.pi / fr)
        c = 1.0 + 2.0 * math.cos(math.pi / 4.0) * ohm + ohm * ohm

        b0 = ohm * ohm / c
        b1 = 2.0 * b0
        b2 = b0
        a1 = 2.0 * (ohm * ohm - 1.0) / c
        a2 = (1.0 - 2.0 * math.cos(math.pi / 4.0) * ohm + ohm * ohm) / c
        return BiquadParams(cutoff, sample_freq, a1, a2, b0, b1, b2)

    def reset(self, value: float) -> None:
        denom = 1.0 + self.params.a1 + self.params.a2
        base = value * (1.0 / denom) if abs(denom) > 1.0e-8 else value
        self.delay_1 = base
        self.delay_2 = base
        self.initialized = True

    def apply(self, sample: float) -> float:
        if self.params.cutoff_freq <= 0.0 or self.params.sample_freq <= 0.0:
            return sample

        if not self.initialized:
            self.reset(sample)

        d0 = sample - self.delay_1 * self.params.a1 - self.delay_2 * self.params.a2
        out = d0 * self.params.b0 + self.delay_1 * self.params.b1 + self.delay_2 * self.params.b2
        self.delay_2 = self.delay_1
        self.delay_1 = d0
        return out


def _time_s(df: pd.DataFrame) -> np.ndarray:
    if "TimeUS" in df.columns:
        t = df["TimeUS"].to_numpy(dtype=float) / 1.0e6
        return t - t[0]
    return df["Time_s"].to_numpy(dtype=float)


def compute_energy_indicator(
    df: pd.DataFrame,
    rms_on: float,
    rms_off: float,
    tau_sec: float,
) -> pd.DataFrame:
    t = _time_s(df)
    x = df["PLX"].to_numpy(dtype=float)
    y = df["PLY"].to_numpy(dtype=float)

    fx_fast = DigitalBiquadFilter(DigitalBiquadFilter.compute_params(SAMPLE_FREQ_HZ, FAST_CUTOFF_HZ))
    fx_slow = DigitalBiquadFilter(DigitalBiquadFilter.compute_params(SAMPLE_FREQ_HZ, SLOW_CUTOFF_HZ))
    fy_fast = DigitalBiquadFilter(DigitalBiquadFilter.compute_params(SAMPLE_FREQ_HZ, FAST_CUTOFF_HZ))
    fy_slow = DigitalBiquadFilter(DigitalBiquadFilter.compute_params(SAMPLE_FREQ_HZ, SLOW_CUTOFF_HZ))

    p_on = max(0.0, rms_on) ** 2
    p_off = max(0.0, min(rms_off, rms_on)) ** 2

    px = np.zeros_like(x)
    py = np.zeros_like(y)
    rms_x = np.zeros_like(x)
    rms_y = np.zeros_like(y)
    tr_x = np.zeros_like(x, dtype=int)
    tr_y = np.zeros_like(y, dtype=int)
    bp_x = np.zeros_like(x)
    bp_y = np.zeros_like(y)

    trusted_x = 0
    trusted_y = 0

    for i in range(len(t)):
        if i == 0:
            dt = 0.01
        else:
            dt = max(0.001, min(0.05, t[i] - t[i - 1]))

        alpha = 1.0 - math.exp(-dt / max(0.1, tau_sec))
        alpha = max(0.0, min(1.0, alpha))

        x_fast = fx_fast.apply(x[i])
        x_slow = fx_slow.apply(x[i])
        y_fast = fy_fast.apply(y[i])
        y_slow = fy_slow.apply(y[i])

        bp_x[i] = x_fast - x_slow
        bp_y[i] = y_fast - y_slow

        ex2 = abs(bp_x[i]) ** 2
        ey2 = abs(bp_y[i]) ** 2

        if i == 0 or not np.isfinite(px[i - 1]):
            px[i] = ex2
            py[i] = ey2
        else:
            px[i] = alpha * ex2 + (1.0 - alpha) * px[i - 1]
            py[i] = alpha * ey2 + (1.0 - alpha) * py[i - 1]

        if trusted_x == 0:
            if px[i] >= p_on:
                trusted_x = 1
        elif px[i] <= p_off:
            trusted_x = 0

        if trusted_y == 0:
            if py[i] >= p_on:
                trusted_y = 1
        elif py[i] <= p_off:
            trusted_y = 0

        tr_x[i] = trusted_x
        tr_y[i] = trusted_y
        rms_x[i] = math.sqrt(max(px[i], 0.0))
        rms_y[i] = math.sqrt(max(py[i], 0.0))

    return pd.DataFrame(
        {
            "Time_s": t,
            "PLX": x,
            "PLY": y,
            "PLZ": df["PLZ"].to_numpy(dtype=float),
            "SW": df["SW"].to_numpy(dtype=int) if "SW" in df.columns else np.zeros_like(x, dtype=int),
            "BandProxyX": bp_x,
            "BandProxyY": bp_y,
            "RMS_X": rms_x,
            "RMS_Y": rms_y,
            "Trust_X": tr_x,
            "Trust_Y": tr_y,
        }
    )


def plot_indicator(df: pd.DataFrame, out_png: Path, title: str, rms_on: float, rms_off: float) -> None:
    t = df["Time_s"].to_numpy(dtype=float)

    fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=True)

    axes[0].plot(t, df["PLX"], color="tab:red", linewidth=0.9, label="PLX")
    axes[0].plot(t, df["PLY"], color="tab:green", linewidth=0.9, label="PLY")
    axes[0].plot(t, df["PLZ"], color="tab:blue", linewidth=0.8, alpha=0.75, label="PLZ")
    axes[0].set_ylabel("Payload force [N]")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="upper right")

    axes[1].plot(t, df["RMS_X"], color="tab:orange", linewidth=1.0, label="X indicator (RMS)")
    axes[1].axhline(rms_on, color="black", linestyle="--", linewidth=1.0, label=f"ON={rms_on:.2f}")
    axes[1].axhline(rms_off, color="gray", linestyle=":", linewidth=1.0, label=f"OFF={rms_off:.2f}")
    axes[1].fill_between(t, 0, np.max(df["RMS_X"]) * 1.05 + 1e-6, where=df["Trust_X"] > 0, color="tab:orange", alpha=0.12)
    axes[1].set_ylabel("X indicator")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="upper right")

    axes[2].plot(t, df["RMS_Y"], color="tab:green", linewidth=1.0, label="Y indicator (RMS)")
    axes[2].axhline(rms_on, color="black", linestyle="--", linewidth=1.0, label=f"ON={rms_on:.2f}")
    axes[2].axhline(rms_off, color="gray", linestyle=":", linewidth=1.0, label=f"OFF={rms_off:.2f}")
    axes[2].fill_between(t, 0, np.max(df["RMS_Y"]) * 1.05 + 1e-6, where=df["Trust_Y"] > 0, color="tab:green", alpha=0.12)
    axes[2].set_ylabel("Y indicator")
    axes[2].set_xlabel("Time [s]")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(loc="upper right")

    fig.suptitle(title)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot EKF energy-gate indicator traces for X/Y")
    parser.add_argument(
        "--inputs",
        nargs="*",
        default=[
            "analysis/replay/results/diagnostics/xy_axis_retune_00000443_00000444_2026-04-07/csv/00000443_w35_100_extracted.csv",
            "analysis/replay/results/diagnostics/xy_axis_retune_00000443_00000444_2026-04-07/csv/00000443_w40_110_extracted.csv",
            "analysis/replay/results/diagnostics/xy_axis_retune_00000443_00000444_2026-04-07/csv/00000444_w35_100_extracted.csv",
            "analysis/replay/results/diagnostics/xy_axis_retune_00000443_00000444_2026-04-07/csv/00000444_w40_110_extracted.csv",
        ],
    )
    parser.add_argument(
        "--outdir",
        default="analysis/replay/results/diagnostics/energy_gate_indicator_xy_2026-04-07",
    )
    parser.add_argument("--rms-on", type=float, default=0.20)
    parser.add_argument("--rms-off", type=float, default=0.16)
    parser.add_argument("--tau", type=float, default=2.0)
    args = parser.parse_args()

    outdir = Path(args.outdir)
    fig_dir = outdir / "figures"
    csv_dir = outdir / "csv"
    outdir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)

    summary_rows: List[Dict[str, float]] = []

    for input_path in args.inputs:
        src = Path(input_path)
        df = pd.read_csv(src)
        ind = compute_energy_indicator(df, args.rms_on, args.rms_off, args.tau)

        tag = src.stem.replace("_extracted", "")
        out_csv = csv_dir / f"{tag}_indicator.csv"
        out_png = fig_dir / f"{tag}_indicator_xy.png"
        ind.to_csv(out_csv, index=False)

        plot_indicator(
            ind,
            out_png,
            f"{tag}: Payload force and EKF energy-gate indicators (X/Y)",
            args.rms_on,
            args.rms_off,
        )

        summary_rows.append(
            {
                "tag": tag,
                "x_trust_ratio": float(ind["Trust_X"].mean()),
                "y_trust_ratio": float(ind["Trust_Y"].mean()),
                "x_rms_mean": float(ind["RMS_X"].mean()),
                "y_rms_mean": float(ind["RMS_Y"].mean()),
            }
        )

    pd.DataFrame(summary_rows).to_csv(outdir / "indicator_summary.csv", index=False)
    print(f"Wrote: {outdir / 'indicator_summary.csv'}")
    print(f"Figures: {fig_dir}")
    print(f"Indicator CSVs: {csv_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
