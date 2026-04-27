#!/usr/bin/env python3
"""Evaluate replay result CSV and emit a concise markdown report."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


def compute_metrics(df: pd.DataFrame) -> dict:
    t = df["Time_s"].to_numpy(dtype=float)
    f = df["EstFreq_Hz"].to_numpy(dtype=float)
    sw = df["SW"].to_numpy(dtype=float) if "SW" in df.columns else np.zeros_like(f)

    step = np.abs(np.diff(f)) if f.size > 1 else np.array([])
    on = sw > 0.5
    if not np.any(on):
        on = np.ones_like(sw, dtype=bool)

    out = {
        "samples": int(f.size),
        "duration_s": float(t[-1] - t[0]) if t.size > 1 else 0.0,
        "sw_active_ratio": float(np.mean(sw > 0.5)) if sw.size else 0.0,
        "sw_transitions": int(np.count_nonzero(np.diff(sw.astype(int)) != 0)) if sw.size > 1 else 0,
        "freq_mean_hz": float(np.mean(f)) if f.size else float("nan"),
        "freq_std_hz": float(np.std(f)) if f.size else float("nan"),
        "freq_min_hz": float(np.min(f)) if f.size else float("nan"),
        "freq_max_hz": float(np.max(f)) if f.size else float("nan"),
        "freq_p95_step_hz": float(np.percentile(step, 95)) if step.size else float("nan"),
        "freq_mean_sw_on_hz": float(np.mean(f[on])) if np.any(on) else float("nan"),
    }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate replay result CSV")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--outdir", default="analysis/ekf_eval/replay/reports")
    args = parser.parse_args()

    input_csv = Path(args.input_csv)
    if not input_csv.exists():
        raise FileNotFoundError(f"Replay CSV not found: {input_csv}")

    df = pd.read_csv(input_csv)
    required = {"Time_s", "EstFreq_Hz"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Required columns missing: {sorted(missing)}")

    tag = input_csv.stem.replace("_result", "")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = Path(args.outdir) / f"{tag}_{ts}"
    outdir.mkdir(parents=True, exist_ok=True)

    metrics = compute_metrics(df)
    (outdir / "summary.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    md = []
    md.append(f"# Replay Evaluation Report: {tag}")
    md.append("")
    md.append("## Input")
    md.append(f"- Source CSV: {input_csv}")
    md.append("")
    md.append("## Metrics")
    for key, value in metrics.items():
        md.append(f"- {key}: {value}")

    report_path = outdir / "REPLAY_EVALUATION.md"
    report_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"Wrote {report_path}")
    print(f"Wrote {outdir / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
