#!/usr/bin/env python3
"""Plot fixed-init 0.60Hz q_w sweep runs and generate a markdown report.

Usage:
  cd <repo-root>
  python analysis/replay/plot_fixed_init_060_runs.py
"""
from pathlib import Path
import json
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt


def main():
    repo_root = Path(__file__).resolve().parents[2]
    summary_path = repo_root / "analysis/replay/results/diagnostics/fixed_init_060_qw_sweep_2026-04-05/summary.json"
    if not summary_path.exists():
        print(f"summary.json not found at {summary_path}")
        sys.exit(1)

    with summary_path.open() as f:
        summary = json.load(f)

    out_base = repo_root / "analysis/replay/results/diagnostics/fixed_init_060_qw_sweep_2026-04-05"
    plots_dir = out_base / "plots"
    runs_plots_dir = plots_dir / "runs"
    plots_dir.mkdir(parents=True, exist_ok=True)
    runs_plots_dir.mkdir(parents=True, exist_ok=True)

    run_map = summary.get("run_map", {})
    generated = []

    for log, runs in run_map.items():
        # overlay plot per log
        plt.figure(figsize=(10, 4))
        legend_items = []
        for key, relpath in runs.items():
            csvp = repo_root / relpath
            if not csvp.exists():
                print(f"missing: {csvp}")
                continue
            df = pd.read_csv(csvp)
            if 'Time_s' not in df.columns or 'EstFreq_Hz' not in df.columns:
                print(f"unexpected columns in {csvp}, skipping")
                continue
            t = df['Time_s']
            est = df['EstFreq_Hz']
            # per-run plot
            stem = Path(relpath).stem
            run_img = runs_plots_dir / f"{stem}.png"
            plt.figure(figsize=(10, 3))
            plt.plot(t, est, lw=1)
            if 'RealFreq_Hz' in df.columns:
                plt.plot(t, df['RealFreq_Hz'], '--', lw=0.8, alpha=0.7)
            plt.xlabel('Time (s)')
            plt.ylabel('Estimated Frequency (Hz)')
            plt.title(f"{log} — {key}")
            plt.grid(alpha=0.3)
            plt.tight_layout()
            plt.savefig(run_img, dpi=150)
            plt.close()
            generated.append(run_img)

            # add to overlay
            plt.figure(1)
            plt.plot(t, est, lw=1, label=key)
            legend_items.append(key)

        # finalize overlay
        plt.xlabel('Time (s)')
        plt.ylabel('Estimated Frequency (Hz)')
        plt.title(f"{log} — q_w sweep overlay")
        if legend_items:
            plt.legend(fontsize='small', ncol=2)
        plt.grid(alpha=0.3)
        overlay_img = plots_dir / f"{log}_overlay_qw.png"
        plt.tight_layout()
        plt.savefig(overlay_img, dpi=150)
        plt.close()
        generated.append(overlay_img)

    # generate markdown report
    report_md = out_base / "FIXED_INIT_060_QW_SWEEP_PLOTS.md"
    with report_md.open('w') as f:
        f.write('# FIXED INIT 0.60Hz — q_w sweep: Frequency vs Time\n')
        f.write('\n')
        f.write('This report shows estimated frequency (EstFreq_Hz) vs time for each run in the q_w sweep.\n')
        f.write('\n')
        for img in sorted(generated):
            rel = img.relative_to(repo_root)
            f.write(f'## {img.stem}\n')
            f.write(f'![]({rel})\n\n')

        f.write('\n')
        f.write('Source summary: `analysis/replay/results/diagnostics/fixed_init_060_qw_sweep_2026-04-05/summary.json`\n')

    print(f"Generated {len(generated)} images and report: {report_md}")


if __name__ == '__main__':
    main()
