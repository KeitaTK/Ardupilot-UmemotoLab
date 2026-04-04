#!/usr/bin/env python3
"""
Generate figures for REPLAY_VALIDATION section 8 results.
Visualizes:
1. Scenario comparison (baseline_reset_log, noreset_log, noreset_always_on, best_gate)
2. Gate parameter scan results
3. Metrics comparison (MAE, std, mean)
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import pandas as pd

# Load diagnostic summary
summary_path = Path('analysis/replay/results/diagnostics/diagnostic_summary.json')
with open(summary_path, 'r') as f:
    data = json.load(f)

sgv = data.get('switch_gate_validation_00000444', {})
scenarios = sgv.get('scenarios', {})
gate_scan = sgv.get('gate_scan', [])
best_gate = sgv.get('best_gate_always_on', {})

# ============================================================
# Figure 1: Metrics Comparison (MAE, std, mean)
# ============================================================
print("Generating Figure 1: Metrics Comparison...")

scenario_names = []
mae_values = []
std_values = []
mean_values = []
colors_list = []
color_map = {
    'baseline_reset_log': '#FF6B6B',  # Red
    'noreset_log': '#4ECDC4',         # Teal
    'noreset_always_on': '#FFE66D',   # Yellow
    'best_gate_always_on': '#95E1D3'  # Mint
}

for scenario_key, scenario_data in scenarios.items():
    # scenario_data is the metric dict directly
    mae = scenario_data.get('mae_vs_target_hz', 0)
    std = scenario_data.get('std_hz', 0)
    mean = scenario_data.get('mean_hz', 0)
    
    scenario_names.append(scenario_key)
    mae_values.append(mae)
    std_values.append(std)
    mean_values.append(mean)
    colors_list.append(color_map.get(scenario_key, '#999999'))

# Add best_gate if exists
if best_gate:
    mae = best_gate.get('mae_vs_target_hz', 0)
    std = best_gate.get('std_hz', 0)
    mean = best_gate.get('mean_hz', 0)
    
    scenario_names.append('best_gate_always_on')
    mae_values.append(mae)
    std_values.append(std)
    mean_values.append(mean)
    colors_list.append(color_map.get('best_gate_always_on', '#95E1D3'))

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle('Scenario Metrics Comparison (00000444)', fontsize=14, fontweight='bold')

x_pos = np.arange(len(scenario_names))
width = 0.6

# MAE (Mean Absolute Error)
ax = axes[0]
bars = ax.bar(x_pos, mae_values, width, color=colors_list, alpha=0.8, edgecolor='black')
ax.set_ylabel('MAE (Hz)', fontsize=11, fontweight='bold')
ax.set_title('Mean Absolute Error vs 0.45Hz', fontsize=11, fontweight='bold')
ax.set_xticks(x_pos)
ax.set_xticklabels(scenario_names, rotation=45, ha='right', fontsize=9)
ax.grid(axis='y', alpha=0.3)
for i, (bar, val) in enumerate(zip(bars, mae_values)):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005, 
            f'{val:.4f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

# Standard Deviation
ax = axes[1]
bars = ax.bar(x_pos, std_values, width, color=colors_list, alpha=0.8, edgecolor='black')
ax.set_ylabel('Std Dev (Hz)', fontsize=11, fontweight='bold')
ax.set_title('Frequency Stability (Std Dev)', fontsize=11, fontweight='bold')
ax.set_xticks(x_pos)
ax.set_xticklabels(scenario_names, rotation=45, ha='right', fontsize=9)
ax.grid(axis='y', alpha=0.3)
for i, (bar, val) in enumerate(zip(bars, std_values)):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005, 
            f'{val:.4f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

# Mean Frequency
ax = axes[2]
target_line = 0.45
ax.axhline(y=target_line, color='red', linestyle='--', linewidth=2, label='Target (0.45Hz)', zorder=1)
bars = ax.bar(x_pos, mean_values, width, color=colors_list, alpha=0.8, edgecolor='black', zorder=2)
ax.set_ylabel('Mean Frequency (Hz)', fontsize=11, fontweight='bold')
ax.set_title('Mean Estimated Frequency (ON interval)', fontsize=11, fontweight='bold')
ax.set_xticks(x_pos)
ax.set_xticklabels(scenario_names, rotation=45, ha='right', fontsize=9)
ax.legend(loc='upper left', fontsize=10)
ax.grid(axis='y', alpha=0.3)
for i, (bar, val) in enumerate(zip(bars, mean_values)):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
            f'{val:.4f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig('analysis/replay/results/diagnostics/section8_metrics_comparison.png', dpi=150, bbox_inches='tight')
print("  Saved: section8_metrics_comparison.png")
plt.close()

# ============================================================
# Figure 2: Gate Scan Results (Parameter Space)
# ============================================================
print("Generating Figure 2: Gate Scan Results...")

if gate_scan:
    scan_df = []
    for combo in gate_scan:
        params = combo.get('params', {})
        metric = combo.get('metric', {})
        scan_df.append({
            'amp_min': params.get('amp_min', 0),
            'amp_max': params.get('amp_max', 0),
            'innov_max': params.get('innov_max', 0),
            'nis_max': params.get('nis_max', 0),
            'mae': metric.get('mae_vs_target_hz', 0),
            'tag': combo.get('tag', '')
        })
    
    df = pd.DataFrame(scan_df)
    df = df.sort_values('mae').reset_index(drop=True)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Axis Gate Parameter Scan Results (always-on, 5 combinations)', 
                 fontsize=14, fontweight='bold')
    
    # Plot 1: amp_min vs MAE
    ax = axes[0, 0]
    scatter = ax.scatter(df['amp_min'], df['mae'], s=100, c=df['mae'], cmap='RdYlGn_r', 
                         edgecolor='black', linewidth=1.5, alpha=0.7)
    ax.set_xlabel('amp_min (N)', fontsize=11, fontweight='bold')
    ax.set_ylabel('MAE vs 0.45Hz (Hz)', fontsize=11, fontweight='bold')
    ax.set_title('Amplitude Min Threshold Effect', fontsize=11)
    ax.grid(True, alpha=0.3)
    for i, row in df.iterrows():
        ax.annotate(f"#{i}", (row['amp_min'], row['mae']), fontsize=8, ha='center')
    plt.colorbar(scatter, ax=ax, label='MAE (Hz)')
    
    # Plot 2: amp_max vs MAE
    ax = axes[0, 1]
    scatter = ax.scatter(df['amp_max'], df['mae'], s=100, c=df['mae'], cmap='RdYlGn_r', 
                         edgecolor='black', linewidth=1.5, alpha=0.7)
    ax.set_xlabel('amp_max (N)', fontsize=11, fontweight='bold')
    ax.set_ylabel('MAE vs 0.45Hz (Hz)', fontsize=11, fontweight='bold')
    ax.set_title('Amplitude Max Threshold Effect', fontsize=11)
    ax.grid(True, alpha=0.3)
    for i, row in df.iterrows():
        ax.annotate(f"#{i}", (row['amp_max'], row['mae']), fontsize=8, ha='center')
    plt.colorbar(scatter, ax=ax, label='MAE (Hz)')
    
    # Plot 3: innov_max vs MAE
    ax = axes[1, 0]
    scatter = ax.scatter(df['innov_max'], df['mae'], s=100, c=df['mae'], cmap='RdYlGn_r', 
                         edgecolor='black', linewidth=1.5, alpha=0.7)
    ax.set_xlabel('innov_max (N)', fontsize=11, fontweight='bold')
    ax.set_ylabel('MAE vs 0.45Hz (Hz)', fontsize=11, fontweight='bold')
    ax.set_title('Innovation Max Threshold Effect', fontsize=11)
    ax.grid(True, alpha=0.3)
    for i, row in df.iterrows():
        ax.annotate(f"#{i}", (row['innov_max'], row['mae']), fontsize=8, ha='center')
    plt.colorbar(scatter, ax=ax, label='MAE (Hz)')
    
    # Plot 4: nis_max vs MAE
    ax = axes[1, 1]
    scatter = ax.scatter(df['nis_max'], df['mae'], s=100, c=df['mae'], cmap='RdYlGn_r', 
                         edgecolor='black', linewidth=1.5, alpha=0.7)
    ax.set_xlabel('nis_max', fontsize=11, fontweight='bold')
    ax.set_ylabel('MAE vs 0.45Hz (Hz)', fontsize=11, fontweight='bold')
    ax.set_title('NIS Max Threshold Effect', fontsize=11)
    ax.grid(True, alpha=0.3)
    for i, row in df.iterrows():
        ax.annotate(f"#{i}", (row['nis_max'], row['mae']), fontsize=8, ha='center')
    plt.colorbar(scatter, ax=ax, label='MAE (Hz)')
    
    plt.tight_layout()
    plt.savefig('analysis/replay/results/diagnostics/section8_gate_scan_parameters.png', dpi=150, bbox_inches='tight')
    print("  Saved: section8_gate_scan_parameters.png")
    plt.close()
    
    # Print scan results table
    print("\n  Gate Scan Results (sorted by MAE):")
    print("  " + "="*80)
    for i, row in df.iterrows():
        print(f"  #{i}: amp_min={row['amp_min']:.2f} amp_max={row['amp_max']:.2f} " + 
              f"innov_max={row['innov_max']:.2f} nis_max={row['nis_max']:.1f} → MAE={row['mae']:.4f}Hz")
    print("  " + "="*80)

# ============================================================
# Figure 3: Scenario Comparison with Improvement Factor
# ============================================================
print("Generating Figure 3: Improvement Analysis...")

fig, ax = plt.subplots(figsize=(12, 6))

# Baseline MAE (reset=1, gate=0)
baseline_mae = mae_values[0] if mae_values else 0.1831
mae_improvements = [(baseline_mae - mae) / baseline_mae * 100 for mae in mae_values]

bars = ax.barh(scenario_names, mae_improvements, color=colors_list, alpha=0.8, edgecolor='black', linewidth=1.5)
ax.set_xlabel('Improvement vs Baseline (%) ↓ Lower is Better', fontsize=12, fontweight='bold')
ax.set_title('Relative Performance vs baseline_reset_log (reset=1, gate=0)', fontsize=13, fontweight='bold')
ax.axvline(x=0, color='red', linestyle='--', linewidth=2, label='No improvement')
ax.grid(axis='x', alpha=0.3)

# Add value labels
for i, (bar, val) in enumerate(zip(bars, mae_improvements)):
    # Show both improvement % and absolute MAE
    mae_val = mae_values[i]
    if val > 0:
        label_text = f'+{val:.1f}% ({mae_val:.4f}Hz)'
        ax.text(val + 2, bar.get_y() + bar.get_height()/2, label_text, 
                va='center', fontsize=10, fontweight='bold', color='green')
    else:
        label_text = f'{val:.1f}% ({mae_val:.4f}Hz)'
        ax.text(val - 2, bar.get_y() + bar.get_height()/2, label_text, 
                va='center', fontsize=10, fontweight='bold', color='red', ha='right')

plt.tight_layout()
plt.savefig('analysis/replay/results/diagnostics/section8_improvement_analysis.png', dpi=150, bbox_inches='tight')
print("  Saved: section8_improvement_analysis.png")
plt.close()

# ============================================================
# Figure 4: Scenario Details Table
# ============================================================
print("Generating Figure 4: Scenario Details Table...")

fig, ax = plt.subplots(figsize=(14, 6))
ax.axis('tight')
ax.axis('off')

# Prepare table data
table_data = []
table_data.append(['Scenario', 'Reset?', 'Gate?', 'Mode', 'Mean (Hz)', 'Std (Hz)', 'MAE (Hz)'])

for scenario_key, scenario_data in scenarios.items():
    mode = 'log' if 'log' in scenario_key else 'always-on'
    reset_str = 'Yes(1)' if 'reset_log' in scenario_key else 'No(0)'
    gate_str = 'Yes(1)' if 'gate' in scenario_key else 'No(0)'
    
    # scenario_data is the metric dict directly
    mean_freq = scenario_data.get('mean_hz', 0)
    std_freq = scenario_data.get('std_hz', 0)
    mae_freq = scenario_data.get('mae_vs_target_hz', 0)
    
    table_data.append([
        scenario_key,
        reset_str,
        gate_str,
        mode,
        f'{mean_freq:.4f}',
        f'{std_freq:.4f}',
        f'{mae_freq:.4f}'
    ])

# Add best_gate row
if best_gate:
    mean_freq = best_gate.get('mean_hz', 0)
    std_freq = best_gate.get('std_hz', 0)
    mae_freq = best_gate.get('mae_vs_target_hz', 0)
    
    gate_desc = f"Gate(opt)"
    table_data.append([
        'best_gate_always_on',
        'No(0)',
        gate_desc,
        'always-on',
        f'{mean_freq:.4f}',
        f'{std_freq:.4f}',
        f'{mae_freq:.4f}'
    ])

# Create table
table = ax.table(cellText=table_data, cellLoc='center', loc='center',
                colWidths=[0.2, 0.12, 0.12, 0.12, 0.13, 0.13, 0.13])
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 2.2)

# Style header row
for i in range(len(table_data[0])):
    cell = table[(0, i)]
    cell.set_facecolor('#4ECDC4')
    cell.set_text_props(weight='bold', color='white')

# Highlight best MAE row
best_mae_idx = mae_values.index(min(mae_values)) + 1 if mae_values else 1
for i in range(len(table_data[0])):
    cell = table[(best_mae_idx, i)]
    cell.set_facecolor('#FFE66D')
    cell.set_text_props(weight='bold')

plt.title('Scenario Metrics Summary Table', fontsize=13, fontweight='bold', pad=20)
plt.savefig('analysis/replay/results/diagnostics/section8_metrics_table.png', dpi=150, bbox_inches='tight')
print("  Saved: section8_metrics_table.png")
plt.close()

print("\n✓ All section 8 figures generated successfully!")
print("\nGenerated files:")
print("  - section8_metrics_comparison.png")
print("  - section8_gate_scan_parameters.png")
print("  - section8_improvement_analysis.png")
print("  - section8_metrics_table.png")
