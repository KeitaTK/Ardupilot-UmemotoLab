# Replay Validation Report (2026-04-04)

## Scope
- Objective: Verify whether AP_Observer replay can be executed now, and collect reproducible results.
- Branch: feature/ekf-migration-from-rls-only
- Workspace: /home/memoto/Ardupilot-UmemotoLab

## Executed Steps
1. Build check for replay example target.
2. Locate actual example binary path.
3. Run replay executable.
4. Collect summary metrics from generated result CSV files.
5. Verify whether input CSV files differ (hash check).

## Commands Used
- Build attempt (named target):
  - ./waf examples --targets=RLS_CSV_Replay
  - Result: failed (target name unresolved by waf in this repo state)
- Artifact discovery:
  - find build/sitl ...
  - Found runnable binary: build/sitl/examples/RLS_CSV_Replay
- Replay execution:
  - ./build/sitl/examples/RLS_CSV_Replay
  - Result: success

## Replay Execution Output (key lines)
- Read 12860 records from analysis/replay/data/00000434.csv.
- Running 00000434 (standard)...
- Finished: analysis/replay/results/00000434_result.csv
- Read 12860 records from analysis/replay/data/00000443.csv.
- Running 00000443 (standard)...
- Finished: analysis/replay/results/00000443_result.csv
- Read 12860 records from analysis/replay/data/00000444.csv.
- Running 00000444 (standard)...
- Finished: analysis/replay/results/00000444_result.csv

## Result File Summary
For each result CSV:
- samples: 12860
- duration: 129.340 s
- SW on samples: 5704 (44.4%)
- estimated frequency:
  - start: 0.5794 Hz
  - end: 0.5794 Hz
  - min: 0.4639 Hz
  - max: 0.5794 Hz
  - mean: 0.5276 Hz
  - median: 0.5794 Hz
  - tail mean (last 1000 samples): 0.5333 Hz

## Input Integrity Check
SHA-256 of replay inputs:
- analysis/replay/data/00000434.csv: 1d4765da5e9ac62e5b6547286886072523326664280ed2afa75d51d9bc9e8a74
- analysis/replay/data/00000443.csv: 1d4765da5e9ac62e5b6547286886072523326664280ed2afa75d51d9bc9e8a74
- analysis/replay/data/00000444.csv: 1d4765da5e9ac62e5b6547286886072523326664280ed2afa75d51d9bc9e8a74

Conclusion from hash check:
- All three replay input CSV files are byte-identical in current workspace.
- Therefore, identical replay outputs across 00000434/443/444 are expected.

## Feasibility Verdict
- Replay execution: PASS (runnable and reproducible)
- Data diversity for multi-log comparison: NOT READY (current three inputs are identical)

## Recommended Next Actions
1. Re-extract CSV from each source BIN separately to restore per-log differences.
2. Re-run replay and regenerate this report after unique inputs are prepared.
3. If needed, add plotting script in analysis/scripts and export comparison figures.
