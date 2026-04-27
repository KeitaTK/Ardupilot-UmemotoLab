#!/usr/bin/env python3
"""Backward-compatible wrapper for moved replay plotting/report script."""

import runpy
from pathlib import Path


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "ekf_eval" / "replay" / "plot_replay_results.py"
    runpy.run_path(str(target), run_name="__main__")
