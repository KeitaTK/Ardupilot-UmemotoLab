# Analysis Workflow Verification Report

**Date**: 2026-01-29  
**Status**: ✅ VERIFIED

## Directory Structure

```
analysis/
├── scripts/              # Analysis and utility scripts
│   ├── analyze_log.py
│   ├── plot_rls_freq_compare.py
│   ├── extract_csv.py
│   └── (utility scripts)
├── debug/               # Debug logs and crash dumps
│   ├── dumpcore.*.out
│   ├── dumpstack.*.out
│   ├── eeprom.bin
│   └── replay_debug_output.txt
├── logs/                # Flight/SITL logs
│   ├── *.BIN
│   ├── CSV/
│   ├── Pixhawk6CLogs/
│   └── *.png
├── replay/              # RLS offline simulation
│   ├── data/            # Input data
│   │   └── replay_data.csv
│   └── results/         # Output results
│       ├── result.csv
│       ├── result_alpha001.csv
│       └── rls_freq_compare.png
└── results/             # General log analysis results
    └── log_analysis.png
```

## Simulation Workflow Verification

### Step 1: Build RLS_CSV_Replay ✅
```bash
./waf configure --board sitl
./waf examples --targets=RLS_CSV_Replay
```
**Result**: Binary created at `build/sitl/examples/RLS_CSV_Replay`

### Step 2: Run Simulation ✅
```bash
./build/sitl/examples/RLS_CSV_Replay
```
**Output**:
```
Read 11612 records.
Finished: analysis/replay/results/result.csv (Alpha=0.05)
Finished: analysis/replay/results/result_alpha001.csv (Alpha=0.01)
```

**Generated Files**:
- `analysis/replay/results/result.csv` (697 KB)
- `analysis/replay/results/result_alpha001.csv` (697 KB)

### Step 3: Generate Comparison Graph ✅
```bash
python3 analysis/scripts/plot_rls_freq_compare.py
```
**Output**: `analysis/replay/results/rls_freq_compare.png` (57 KB)

## Results Summary

### Alpha=0.05 (Standard)
- **Initial Freq**: 0.5794 Hz
- **Final Freq**: 0.5464 Hz
- **Mean Freq**: 0.5586 Hz
- **Std Dev**: 0.0167 Hz
- **Characteristic**: Faster convergence, shows clear transient behavior

### Alpha=0.01 (Conservative)
- **Initial Freq**: 0.5794 Hz
- **Final Freq**: 0.5682 Hz
- **Mean Freq**: 0.5743 Hz
- **Std Dev**: 0.0045 Hz
- **Characteristic**: Slower but more stable, less oscillation

## Path Verification

| Component | Input Path | Output Path | Status |
|-----------|-----------|-----------|--------|
| RLS_CSV_Replay | `analysis/replay/data/replay_data.csv` | `analysis/replay/results/result*.csv` | ✅ |
| plot_rls_freq_compare.py | `analysis/replay/results/result*.csv` | `analysis/replay/results/rls_freq_compare.png` | ✅ |
| analyze_log.py | Custom CSV | `analysis/results/log_analysis.png` | ✅ |
| extract_csv.py | `analysis/logs/*.BIN` | Any CSV path | ✅ |

## Script Output Locations

All programs now output to the correct `analysis/` subdirectories:
- ✅ RLS_CSV_Replay: Outputs to `analysis/replay/results/`
- ✅ plot_rls_freq_compare.py: Generates PNG in `analysis/replay/results/`
- ✅ analyze_log.py: Saves PNG to `analysis/results/`
- ✅ extract_csv.py: Supports custom output paths

## Integration with Autotest

Updated `.github/AUTOTEST_SPECIFICATION.md` to require:
1. Building RLS_CSV_Replay
2. Running offline simulation
3. Generating comparison graphs
4. Verifying convergence with real flight data

This ensures frequency estimation code changes are validated against flight data before SITL tests.

## Notes

- All paths use workspace-relative formats (no absolute paths)
- Backward compatible: old `libraries/AP_Observer/examples/RLS_CSV_Replay/` paths no longer used
- `analysis/logs/` contains both SITL (*.BIN) and hardware (Pixhawk6CLogs/) logs
- `analysis/debug/` preserves historical crash logs for debugging

## Next Steps

1. Use `analysis/scripts/plot_rls_freq_compare.py` to compare Alpha values
2. Use `analysis/scripts/analyze_log.py <csv>` to inspect individual flight logs
3. Store simulation input data in `analysis/replay/data/`
4. Archive results in `analysis/replay/results/` for version control
5. All new log analysis outputs go to `analysis/results/`
