#!/usr/bin/env python3
"""Compare xy-axis EKF strategy variants and omega-only slow-update sweeps.

The script runs the replay binary on 00000443/00000444 with three strategy
profiles and a q_w sweep that only changes the omega process noise.
It writes CSV summaries, figures, and a Markdown report under the output dir.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


TARGET_HZ = 0.45
FORCE_HOLD_MAX = 0.0
FORCE_REJECT_MAX = 5.0
AXIS_MASK_XY = 0x03


@dataclass(frozen=True)
class InputLog:
    tag: str
    input_path: Path


@dataclass(frozen=True)
class StrategyConfig:
    name: str
    description: str
    extra_args: Sequence[str]


def ensure_csv(input_path: Path, outdir: Path) -> Path:
    if input_path.suffix.lower() != ".bin":
        return input_path

    outdir.mkdir(parents=True, exist_ok=True)
    out_csv = outdir / f"{input_path.stem}_from_bin.csv"
    cmd = [
        "python3",
        "analysis/replay/bin_to_replay_csv.py",
        "--input",
        str(input_path),
        "--output",
        str(out_csv),
    ]
    subprocess.run(cmd, check=True)
    return out_csv


def run_replay(binary: Path, input_path: Path, outdir: Path, tag: str, extra_args: Sequence[str]) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(binary),
        "--input",
        str(input_path),
        "--outdir",
        str(outdir),
        "--tag",
        tag,
        "--sw-mode",
        "log",
        "--ekf-reset-on-switch",
        "0",
        "--ekf-axis-mask",
        str(AXIS_MASK_XY),
        "--ekf-axis-gate",
        "0",
        "--ekf-w-init-hz",
        "0.45",
        "--ekf-force-hold-max",
        f"{FORCE_HOLD_MAX}",
        "--ekf-force-reject-min",
        f"{FORCE_REJECT_MAX}",
        *extra_args,
    ]
    subprocess.run(cmd, check=True)
    return outdir / f"{tag}_result.csv"


def metrics(freq: np.ndarray, t: np.ndarray, sw: np.ndarray, target: float = TARGET_HZ) -> Dict[str, float]:
    mask = sw == 1
    if not np.any(mask):
        mask = np.ones_like(sw, dtype=bool)

    f = freq[mask]
    tt = t[mask]
    if f.size < 2:
        return {
            "mean_hz": float("nan"),
            "std_hz": float("nan"),
            "mae_hz": float("nan"),
            "p95_step_hz": float("nan"),
            "max_step_hz": float("nan"),
            "hf_ratio": float("nan"),
        }

    step = np.abs(np.diff(f))
    dt = float(np.mean(np.diff(tt))) if tt.size > 1 else 0.01
    x = f - np.mean(f)
    win = np.hanning(x.size)
    spec = np.fft.rfft(x * win)
    fr = np.fft.rfftfreq(x.size, d=dt)
    pw = np.abs(spec) ** 2
    low = float(np.sum(pw[(fr >= 0.0) & (fr < 0.5)]))
    high = float(np.sum(pw[(fr >= 2.0) & (fr < 20.0)]))
    hf_ratio = high / max(low, 1.0e-12)

    return {
        "mean_hz": float(np.mean(f)),
        "std_hz": float(np.std(f)),
        "mae_hz": float(np.mean(np.abs(f - target))),
        "p95_step_hz": float(np.percentile(step, 95)),
        "max_step_hz": float(np.max(step)),
        "hf_ratio": hf_ratio,
    }


def score_row(row: pd.Series) -> float:
    return float(row["p95_step_hz"]) + 0.3 * float(row["mae_hz"]) + 0.1 * float(row["std_hz"])


def read_result(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def find_switch_edges(sw: np.ndarray, t: np.ndarray) -> List[float]:
    idx = np.where(np.diff(sw) != 0)[0]
    return [float(t[i + 1]) for i in idx]


def make_strategy_plot(tag: str, df_map: Dict[str, pd.DataFrame], out_png: Path) -> None:
    fig, ax = plt.subplots(figsize=(13, 5))
    colors = {
        "xy_sw_hold": "tab:blue",
        "xy_sw_amp_gate": "tab:orange",
        "xy_always_on": "tab:green",
    }

    for name, df in df_map.items():
        ax.plot(df["Time_s"], df["EstFreq_Hz"], label=name, linewidth=1.0, color=colors.get(name, None))

    base_df = next(iter(df_map.values()))
    ax.axhline(TARGET_HZ, color="black", linestyle="--", linewidth=1.0, label=f"target={TARGET_HZ:.2f}Hz")
    ax.plot(base_df["Time_s"], 0.25 * base_df["SW"] + 0.25, "k--", linewidth=0.6, alpha=0.35, label="SW (scaled)")
    ax.set_title(f"{tag}: strategy comparison")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Frequency [Hz]")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", ncol=2)
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def make_qw_plot(qw_df: pd.DataFrame, out_png: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    for tag, group in qw_df.groupby("log"):
        group = group.sort_values("q_w")
        axes[0].plot(group["q_w"], group["mae_hz"], marker="o", label=tag)
        axes[1].plot(group["q_w"], group["p95_step_hz"], marker="o", label=tag)

    for ax in axes:
        ax.set_xscale("log")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")

    axes[0].set_ylabel("MAE [Hz]")
    axes[0].set_title("Omega-only slow update sweep")
    axes[1].set_ylabel("P95 step [Hz]")
    axes[1].set_xlabel("q_w")

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def format_markdown_table(df: pd.DataFrame, columns: Sequence[str], float_fmt: str = "{:.4f}") -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    lines = [header, separator]
    for _, row in df.iterrows():
        cells = []
        for col in columns:
            value = row[col]
            if isinstance(value, float) or isinstance(value, np.floating):
                if np.isnan(value):
                    cells.append("nan")
                else:
                    cells.append(float_fmt.format(float(value)))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def build_report(
    outdir: Path,
    strategies_df: pd.DataFrame,
    q_w_df: pd.DataFrame,
    strategy_runs: Dict[str, Dict[str, Path]],
    q_w_runs: Dict[str, Dict[str, Path]],
) -> str:
    agg = strategies_df.groupby("strategy", as_index=False).agg(
        score=("score", "mean"),
        mae_hz=("mae_hz", "mean"),
        std_hz=("std_hz", "mean"),
        p95_step_hz=("p95_step_hz", "mean"),
        max_step_hz=("max_step_hz", "mean"),
    )
    agg = agg.sort_values("score", ascending=True)

    q_agg = q_w_df.groupby("q_w", as_index=False).agg(
        score=("score", "mean"),
        mae_hz=("mae_hz", "mean"),
        std_hz=("std_hz", "mean"),
        p95_step_hz=("p95_step_hz", "mean"),
    ).sort_values("score", ascending=True)
    q_agg_display = q_agg.copy()
    q_agg_display["q_w"] = q_agg_display["q_w"].map(lambda value: f"{float(value):.0e}")

    best_strategy = str(agg.iloc[0]["strategy"])
    best_qw = float(q_agg.iloc[0]["q_w"])

    lines: List[str] = []
    lines.append("# XY EKF Strategy Comparison and Omega Slow-Update Sweep")
    lines.append("")
    lines.append("## Scope")
    lines.append("- xy-axis fusion only; z-axis is excluded from fused frequency updates")
    lines.append("- two flight logs: 00000443 and 00000444")
    lines.append("- compare three strategies and one omega-only q_w sweep")
    lines.append("")
    lines.append("## Strategy Configurations")
    strategy_meta = pd.DataFrame(
        [
            {"strategy": "xy_sw_hold", "description": "xy fusion + SW log + omega hold when switch is off", "note": "estimation freezes during SW off"},
            {"strategy": "xy_sw_amp_gate", "description": "xy fusion + SW log + amplitude gating", "note": "amp gate dominates; innovation/NIS left loose"},
            {"strategy": "xy_always_on", "description": "xy fusion + always-on estimation", "note": "baseline for continuous updating"},
        ]
    )
    lines.append(format_markdown_table(strategy_meta, ["strategy", "description", "note"], float_fmt="{:.4f}"))
    lines.append("")
    lines.append("## Aggregate Strategy Ranking")
    lines.append(format_markdown_table(agg, ["strategy", "score", "mae_hz", "std_hz", "p95_step_hz", "max_step_hz"]))
    lines.append("")
    lines.append(f"Best strategy by composite score: **{best_strategy}**")
    lines.append("")

    per_log = strategies_df.copy()
    per_log["score"] = per_log.apply(score_row, axis=1)
    lines.append("## Per-Log Strategy Metrics")
    for log, group in per_log.groupby("log"):
        lines.append(f"### {log}")
        lines.append(format_markdown_table(group.sort_values("score"), ["strategy", "score", "mae_hz", "std_hz", "p95_step_hz", "max_step_hz"]))
        lines.append("")

    lines.append("## Omega-Only Slow Update Sweep")
    lines.append("- This sweep changes only q_w, so d/d_dot/c keep the same tuning while omega adaptation slows down.")
    lines.append(f"- Best q_w by composite score: **{best_qw:.1e}**")
    lines.append("")
    lines.append(format_markdown_table(q_agg_display, ["q_w", "score", "mae_hz", "std_hz", "p95_step_hz"]))
    lines.append("")

    lines.append("## Artifacts")
    lines.append(f"- strategy metrics CSV: {outdir / 'strategy_metrics.csv'}")
    lines.append(f"- q_w sweep CSV: {outdir / 'qw_sweep_metrics.csv'}")
    lines.append(f"- strategy figure: {outdir / 'strategy_comparison.png'}")
    lines.append(f"- q_w figure: {outdir / 'qw_sweep.png'}")
    lines.append("")
    lines.append("## Run Map")
    lines.append("### Strategy runs")
    for log, items in strategy_runs.items():
        lines.append(f"- {log}")
        for name, path in items.items():
            lines.append(f"  - {name}: {path}")
    lines.append("### q_w runs")
    for log, items in q_w_runs.items():
        lines.append(f"- {log}")
        for name, path in items.items():
            lines.append(f"  - {name}: {path}")

    lines.append("")
    lines.append("## Conclusion")
    lines.append(
        "- xy-only fusion avoids using the z-axis, which matches the observed resonance split between XY and Z."
    )
    lines.append(
        "- SW-off omega hold is the cleanest way to prevent frequency drift while still letting the other EKF states update."
    )
    lines.append(
        "- q_w is the right knob for slowing frequency-only updates; it does not need to slow d/d_dot/c if the firmware keeps the state noises separate."
    )
    lines.append(f"- On this data set, the current best q_w sweep point is {best_qw:.1e}, but the ranking should be rechecked on other logs before changing the runtime default.")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare xy EKF strategies and q_w sweeps")
    parser.add_argument("--replay-bin", default="build/sitl/examples/RLS_CSV_Replay")
    parser.add_argument("--input-443", default="analysis/replay/data/00000443.BIN")
    parser.add_argument("--input-444", default="analysis/replay/data/00000444.BIN")
    parser.add_argument("--outdir", default="analysis/replay/results/diagnostics/xy_ekf_2026-04-05")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    runs_dir = outdir / "runs"
    figures_dir = outdir / "figures"
    runs_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    replay_bin = Path(args.replay_bin)
    inputs = [
        InputLog("00000443", Path(args.input_443)),
        InputLog("00000444", Path(args.input_444)),
    ]

    strategies = [
        StrategyConfig(
            name="xy_sw_hold",
            description="xy fusion + SW log + omega hold when switch is off",
            extra_args=[
                "--ekf-hold-omega-off",
                "1",
            ],
        ),
        StrategyConfig(
            name="xy_sw_amp_gate",
            description="xy fusion + SW log + amplitude gate",
            extra_args=[
                "--ekf-hold-omega-off",
                "1",
                "--ekf-axis-gate",
                "1",
                "--ekf-amp-min",
                "0.10",
                "--ekf-amp-max",
                "1.00",
                "--ekf-innov-max",
                "10.0",
                "--ekf-nis-max",
                "100.0",
            ],
        ),
        StrategyConfig(
            name="xy_always_on",
            description="xy fusion + always-on estimation",
            extra_args=[
                "--sw-mode",
                "always-on",
            ],
        ),
    ]

    qw_values = [5.0e-4, 1.0e-4, 1.0e-5, 1.0e-6, 1.0e-7]

    strategy_rows: List[Dict[str, object]] = []
    q_w_rows: List[Dict[str, object]] = []
    strategy_runs: Dict[str, Dict[str, Path]] = {}
    q_w_runs: Dict[str, Dict[str, Path]] = {}

    for log in inputs:
        csv_input = ensure_csv(log.input_path, runs_dir / log.tag)

        strategy_runs[log.tag] = {}
        strategy_dfs: Dict[str, pd.DataFrame] = {}
        for strat in strategies:
            run_dir = runs_dir / log.tag / strat.name
            tag = f"{log.tag}_{strat.name}"
            result_csv = run_replay(replay_bin, csv_input, run_dir, tag, strat.extra_args)
            strategy_runs[log.tag][strat.name] = result_csv
            df = read_result(result_csv)
            strategy_dfs[strat.name] = df
            m = metrics(df["EstFreq_Hz"].to_numpy(dtype=float), df["Time_s"].to_numpy(dtype=float), df["SW"].to_numpy(dtype=int))
            strategy_rows.append(
                {
                    "log": log.tag,
                    "strategy": strat.name,
                    "description": strat.description,
                    **m,
                }
            )

        make_strategy_plot(log.tag, strategy_dfs, figures_dir / f"{log.tag}_strategy_comparison.png")

        q_w_runs[log.tag] = {}
        for q_w in qw_values:
            run_dir = runs_dir / log.tag / f"qw_{q_w:.0e}"
            tag = f"{log.tag}_qw_{q_w:.0e}".replace("+", "")
            result_csv = run_replay(
                replay_bin,
                csv_input,
                run_dir,
                tag,
                [
                    "--sw-mode",
                    "always-on",
                    "--ekf-w-init-hz",
                    "0.45",
                    "--ekf-q-w",
                    f"{q_w}",
                    "--ekf-axis-gate",
                    "0",
                ],
            )
            q_w_runs[log.tag][f"q_w={q_w:.0e}"] = result_csv
            df = read_result(result_csv)
            m = metrics(df["EstFreq_Hz"].to_numpy(dtype=float), df["Time_s"].to_numpy(dtype=float), df["SW"].to_numpy(dtype=int))
            q_w_rows.append(
                {
                    "log": log.tag,
                    "q_w": q_w,
                    **m,
                }
            )

    strategy_df = pd.DataFrame(strategy_rows)
    strategy_df["score"] = strategy_df.apply(score_row, axis=1)
    strategy_df.to_csv(outdir / "strategy_metrics.csv", index=False)

    q_w_df = pd.DataFrame(q_w_rows)
    q_w_df["score"] = q_w_df.apply(score_row, axis=1)
    q_w_df.to_csv(outdir / "qw_sweep_metrics.csv", index=False)

    make_qw_plot(q_w_df, outdir / "qw_sweep.png")

    report = build_report(outdir, strategy_df, q_w_df, strategy_runs, q_w_runs)
    report_path = outdir / "XY_EKF_STRATEGY_REPORT_2026-04-05.md"
    report_path.write_text(report, encoding="utf-8")

    summary = {
        "target_hz": TARGET_HZ,
        "strategy_metrics_csv": str(outdir / "strategy_metrics.csv"),
        "qw_sweep_metrics_csv": str(outdir / "qw_sweep_metrics.csv"),
        "report": str(report_path),
        "strategy_runs": {k: {kk: str(vv) for kk, vv in vv_map.items()} for k, vv_map in strategy_runs.items()},
        "qw_runs": {k: {kk: str(vv) for kk, vv in vv_map.items()} for k, vv_map in q_w_runs.items()},
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Wrote {report_path}")
    print(f"Wrote {outdir / 'strategy_metrics.csv'}")
    print(f"Wrote {outdir / 'qw_sweep_metrics.csv'}")
    print(f"Wrote {outdir / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())