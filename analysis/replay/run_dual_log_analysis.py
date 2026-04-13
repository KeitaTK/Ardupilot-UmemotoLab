#!/usr/bin/env python3
"""Process dual-log analysis with different time windows for 443 and 444."""

import os
import subprocess
import sys

def run_windowed_analysis(
    log_id: str,
    input_csv: str,
    output_base_dir: str,
    time_windows: list,  # List of (name, start_s, end_s) tuples
):
    """Process input CSV with multiple time windows."""
    
    # Ensure output directory exists
    os.makedirs(output_base_dir, exist_ok=True)
    
    for window_name, time_start, time_end in time_windows:
        windowed_csv = os.path.join(
            output_base_dir,
            f"{log_id}__{window_name}_windowed.csv"
        )
        window_plot_dir = os.path.join(
            output_base_dir,
            f"{log_id}__{window_name}_plots"
        )
        
        # Filter CSV by time window
        print(f"\n=== Processing {log_id} {window_name} ({time_start}-{time_end}s) ===")
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
            print(f"Failed to filter CSV for {log_id} {window_name}")
            continue
        
        # Generate plots
        plot_cmd = [
            "python3",
            "analysis/replay/plot_replay_results.py",
            "--input", windowed_csv,
            "--outdir", window_plot_dir,
            "--title", f"{log_id} {window_name}",
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
            print(f"Failed to generate plots for {log_id} {window_name}")
            continue
        
        print(f"Successfully processed {log_id} {window_name}")


if __name__ == "__main__":
    # 443: w35_100
    # 444: w40_110
    
    # 443 の処理（既存のリプレイ結果CSVを使用）
    input_443 = "/home/memoto/Ardupilot-UmemotoLab/analysis/replay/results/runs/00000443/00000443_bin_result.csv"
    output_443 = "/home/memoto/Ardupilot-UmemotoLab/analysis/replay/results/runs/00000443_recheck_2026-04-13"
    windows_443 = [
        ("w35_100", 35, 100),
    ]
    
    # 444 の処理（w40_110がメイン）
    input_444 = "/home/memoto/Ardupilot-UmemotoLab/analysis/replay/results/runs/00000444_recheck_2026-04-08/00000444_recheck_result.csv"
    output_444 = "/home/memoto/Ardupilot-UmemotoLab/analysis/replay/results/runs/00000444_recheck_2026-04-13"
    windows_444 = [
        ("w40_110", 40, 110),
    ]
    
    print("Starting dual-log analysis for 443 and 444...")
    
    run_windowed_analysis("00000443_recheck", input_443, output_443, windows_443)
    run_windowed_analysis("00000444_recheck", input_444, output_444, windows_444)
    
    print("\n✅ Dual-log analysis complete!")
