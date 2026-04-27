#!/usr/bin/env python3
"""Backward-compatible wrapper for moved OBSV BIN->CSV extractor."""

import runpy
from pathlib import Path


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "ekf_eval" / "common" / "bin_to_obsv_csv.py"
    runpy.run_path(str(target), run_name="__main__")
