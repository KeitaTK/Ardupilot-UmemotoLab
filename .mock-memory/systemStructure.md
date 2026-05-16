# System Structure

> **Purpose:** Directory layout, module dependencies, and build targets.

## Repository Root Directory Layout

```
Ardupilot-UmemotoLab/
├── .clinerules              # Custom instructions (build rules, test pipeline, scope management)
├── .clineignore             # Dynamic blacklist for scope management
├── .roomodes                # Custom Cline modes (observer-developer, docs-writer)
├── .mock-memory/            # Memory bank (this directory)
├── venv/                    # Unified Python virtual environment
├── libraries/
│   └── AP_Observer/         # ★ Core: EKF-based Harmonic Disturbance Observer
│       ├── AP_Observer.h    # Class declaration, parameter definitions, state variables
│       ├── AP_Observer.cpp  # EKF implementation, robustness gates, per-axis frequency estimation
│       └── README.md        # Mathematical documentation (LaTeX)
├── ArduCopter/              # ArduCopter vehicle code
├── Tools/                   # Build tools, autotest framework
├── build_pixhawk6c.sh       # Script: clean build for Pixhawk6C hardware
├── run_autotest_*.sh        # Scripts: Lite / Medium / Full test pipelines
└── run_ci_pipeline.sh       # Script: full CI pipeline (Lite→Medium→Pixhawk6C)
```

## Key Module: AP_Observer

### Files
| File | Role |
|------|------|
| `libraries/AP_Observer/AP_Observer.h` | Class declaration, parameter definitions (`EKF_*` prefix), state variables |
| `libraries/AP_Observer/AP_Observer.cpp` | EKF implementation, 3-stage robustness gates, independent per-axis frequency estimation |
| `libraries/AP_Observer/README.md` | Mathematical documentation (3-layer structure: theory textbook, implementation guide, design notes) |

### Algorithm
- 4-state EKF per axis (X, Y): [d, d_dot, c, ω]
- Z-axis EKF update skipped
- 3-stage robustness gate: Energy confidence → Amplitude-based → NIS check
- X/Y axes estimate frequency independently

## Build Targets

| Target | Board | Command |
|--------|-------|---------|
| SITL (dev) | sitl | `./waf configure --board sitl && ./waf build --target bin/arducopter` |
| Pixhawk6C (real) | Pixhawk6C | `./build_pixhawk6c.sh` (always clean build) |

## Test Pipeline

1. **Lite** — Observer 3 tests (~1-2 min) → `./run_autotest_lite.sh`
2. **Medium** — Observer + basic features (~2 min) → `./run_autotest_medium.sh`
3. **Pixhawk6C** — Clean build for real hardware → `./build_pixhawk6c.sh`
4. **Full** — Complete test suite (~15 min) → `./run_autotest_full.sh` (manual only)

## Coding Conventions

- Language: C++11/14 (ArduPilot standard)
- Comments: Japanese (document implementation intent)
- Math: LaTeX notation in README.md
- Parameter naming: `EKF_*` prefix
- Log messages: `OBSV` custom format