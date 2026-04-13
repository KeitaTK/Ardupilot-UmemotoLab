#!/usr/bin/env python3
"""Process replay results with time windows for analysis."""

import os
import subprocess
import sys

def run_windowed_analysis(
    input_csv: str,
    output_base_dir: str,
    tag: str,
    time_windows: list,  # List of (name, start_s, end_s) tuples
):
    """Process input CSV with multiple time windows."""
    
    # Ensure output directory exists
    os.makedirs(output_base_dir, exist_ok=True)
    
    for window_name, time_start, time_end in time_windows:
        windowed_csv = os.path.join(
            output_base_dir,
            f"{tag}_{window_name}_windowed.csv"
        )
        window_plot_dir = os.path.join(
            output_base_dir,
            f"{tag}_{window_name}_plots"
        )
        
        # Filter CSV by time window
        print(f"\n=== Processing {window_name} ({time_start}-{time_end}s) ===")
        filter_cmd = [
            "python3",
            "analysis/replay/filter_by_time_window.py",
            "--input", input_csv,
            "--output", windowed_csv,
            "--time-start", str(time_start),
            "--time-end", str(time_end),
        ]
        
        result = subprocess.run(filter_cmd, cwd="/home/memoto/Ardupilot-UmemotoLab")
        if result.returncode != 0:
            print(f"Failed to filter CSV for {window_name}")
            continue
        
        # Generate plots
        plot_cmd = [
            "python3",
            "analysis/replay/plot_replay_results.py",
            "--input", windowed_csv,
            "--outdir", window_plot_dir,
            "--title", f"{tag} {window_name}",
            "--ekf-q-w", "1e-9",
            "--ekf-w-init-hz", "0.6",
            "--ekf-axis-mask", "3",
            "--ekf-axis-gate", "0",
            "--ekf-reset-on-switch", "0",
            "--ekf-force-hold-max", "1.5",
            "--ekf-force-reject-min", "5.0",
            "--ekf-param", "sw_mode=log",
            "--ekf-param", "ekf_energy_gate=1",
            "--ekf-param", "ekf_energy_rms_on=0.20",
            "--ekf-param", "ekf_energy_rms_off=0.16",
            "--ekf-param", "ekf_energy_tau=2.0",
        ]
        
        result = subprocess.run(plot_cmd, cwd="/home/memoto/Ardupilot-UmemotoLab")
        if result.returncode != 0:
            print(f"Failed to generate plots for {window_name}")
            continue
        
        print(f"Successfully processed {window_name}")


if __name__ == "__main__":
    input_csv = "/home/memoto/Ardupilot-UmemotoLab/analysis/replay/results/runs/00000444_recheck_2026-04-08/00000444_recheck_result.csv"
    output_base = "/home/memoto/Ardupilot-UmemotoLab/analysis/replay/results/runs/00000444_recheck_2026-04-08"
    tag = "00000444_recheck"
    
    # Time windows: (name, start_s, end_s)
    windows = [
        ("w35_100", 35, 100),
        ("w40_110", 40, 110),
    ]
    
    run_windowed_analysis(input_csv, output_base, tag, windows)
