#!/usr/bin/env python3
"""
Run replay with a fixed-frequency EKF (by setting initial omega and very small process noise),
then compare metrics against the existing EKF run.

Outputs:
- metrics CSV
- Markdown report
- result CSVs saved under runs/<tag>/
"""
import subprocess
import json
from pathlib import Path
import numpy as np
import pandas as pd
import math

REPLAY_BIN = Path("build/sitl/examples/RLS_CSV_Replay")
INPUTS = {
    "00000443": Path("analysis/replay/data/00000443.BIN"),
    "00000444": Path("analysis/replay/data/00000444.BIN"),
}
OUTBASE = Path("analysis/replay/results/diagnostics/single_freq_2026-04-05")
OUTBASE.mkdir(parents=True, exist_ok=True)
RUNS = OUTBASE / "runs"
RUNS.mkdir(parents=True, exist_ok=True)
TARGET_HZ = 0.45


def metrics(freq: np.ndarray, t: np.ndarray, sw: np.ndarray, target: float = TARGET_HZ) -> dict:
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


def run_fixed_replay(tag: str, input_path: Path, outdir: Path, freq_hz: float = TARGET_HZ) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    tagname = f"{tag}_fixedHz"
    cmd = [
        str(REPLAY_BIN),
        "--input",
        str(input_path),
        "--outdir",
        str(outdir),
        "--tag",
        tagname,
        "--sw-mode",
        "log",
        "--ekf-reset-on-switch",
        "0",
        "--ekf-force-hold-max",
        "1.5",
        "--ekf-force-reject-min",
        "5.0",
        "--ekf-axis-gate",
        "0",
        "--ekf-w-init-hz",
        f"{freq_hz}",
        "--ekf-q-w",
        "1e-9",
        "--ekf-r-meas",
        "0.08",
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    return outdir / f"{tagname}_result.csv"


def main():
    metrics_rows = []

    # existing original runs (from previous dual-component analysis)
    orig_base = Path("analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/runs")

    for tag, inp in INPUTS.items():
        run_outdir = RUNS / tag
        run_outdir.mkdir(parents=True, exist_ok=True)
        # run fixed-frequency replay
        result_fixed = run_fixed_replay(tag, inp, run_outdir)
        if not result_fixed.exists():
            print("Fixed replay result not found:", result_fixed)
            continue
        # original result path
        orig_result = orig_base / tag / f"{tag}_dual_eval_result.csv"
        if not orig_result.exists():
            print("Original result not found, skipping comparison for", tag)
            continue

        # read both
        df_orig = pd.read_csv(orig_result)
        df_fixed = pd.read_csv(result_fixed)
        t = df_orig["Time_s"].to_numpy(dtype=float)
        sw = df_orig["SW"].to_numpy(dtype=int)

        m_orig = metrics(df_orig["EstFreq_Hz"].to_numpy(dtype=float), t, sw)
        m_fixed = metrics(df_fixed["EstFreq_Hz"].to_numpy(dtype=float), t, sw)

        row_orig = {"log": tag, "method": "original_ekf", **m_orig}
        row_fixed = {"log": tag, "method": "fixed_ekf_0.45Hz", **m_fixed}
        metrics_rows.append(row_orig)
        metrics_rows.append(row_fixed)

        # Save per-run comparison csv
        out_compare = run_outdir / f"{tag}_fixed_vs_orig_summary.json"
        with out_compare.open("w") as f:
            json.dump({"original_metrics": m_orig, "fixed_metrics": m_fixed}, f, indent=2)

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_csv = OUTBASE / "single_freq_ekf_metrics.csv"
    metrics_df.to_csv(metrics_csv, index=False)

    # write short markdown report
    md = OUTBASE / "SINGLE_FREQ_EKF_REPORT_2026-04-05.md"
    with md.open("w") as f:
        f.write("# Single-frequency EKF Replay Comparison\n\n")
        f.write("Compared original EKF vs fixed-frequency EKF (init=0.45Hz, q_w=1e-9)\n\n")
        # Use CSV/text fallback to avoid optional dependencies (tabulate)
        f.write("```")
        f.write(metrics_df.to_string(index=False))
        f.write("```\n\n")
        f.write("---\nRecommendation: If fixed EKF improves stability (lower p95_step_hz and mae), consider integrating fixed-frequency option into runtime EKF or using very low process noise for frequency during steady flight.\n")

    print("Wrote:", metrics_csv)
    print("Wrote:", md)


if __name__ == '__main__':
    raise SystemExit(main())
