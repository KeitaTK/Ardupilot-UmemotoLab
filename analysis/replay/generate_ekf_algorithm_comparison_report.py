#!/usr/bin/env python3
"""Generate a detailed EKF algorithm comparison report from replay artifacts.

This script compares multiple EKF strategy outputs on common logs and writes:
- per-log plots (top: raw payload force + SW, bottom: estimated frequency)
- metrics CSV (per log x method)
- aggregate ranking CSV (method average)
- markdown report with findings and artifact paths
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


TARGET_HZ = 0.45


@dataclass(frozen=True)
class MethodSpec:
    name: str
    label: str
    color: str
    path_template: str


METHODS: List[MethodSpec] = [
    MethodSpec(
        name="baseline_3axis_logsw",
        label="Baseline EKF (3-axis, log SW)",
        color="tab:purple",
        path_template="analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/runs/{tag}/{tag}_dual_eval_result.csv",
    ),
    MethodSpec(
        name="xy_always_on",
        label="XY EKF always-on",
        color="tab:green",
        path_template="analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/{tag}/xy_always_on/{tag}_xy_always_on_result.csv",
    ),
    MethodSpec(
        name="xy_sw_hold",
        label="XY EKF SW-hold",
        color="tab:blue",
        path_template="analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/{tag}/xy_sw_hold/{tag}_xy_sw_hold_result.csv",
    ),
    MethodSpec(
        name="xy_sw_amp_gate",
        label="XY EKF SW+amp-gate",
        color="tab:orange",
        path_template="analysis/replay/results/diagnostics/xy_ekf_2026-04-05/runs/{tag}/xy_sw_amp_gate/{tag}_xy_sw_amp_gate_result.csv",
    ),
    MethodSpec(
        name="fixed_init_045",
        label="Fixed init 0.45Hz (q_w=1e-9)",
        color="tab:red",
        path_template="analysis/replay/results/diagnostics/single_freq_2026-04-05/runs/{tag}/{tag}_fixed_0p45Hz_result.csv",
    ),
    MethodSpec(
        name="fixed_init_060",
        label="Fixed init 0.60Hz (q_w=1e-9)",
        color="tab:brown",
        path_template="analysis/replay/results/diagnostics/single_freq_2026-04-05/runs/{tag}/{tag}_fixed_0p60Hz_result.csv",
    ),
]


def compute_metrics(freq: np.ndarray, time_s: np.ndarray, sw: np.ndarray) -> Dict[str, float]:
    on_mask = sw == 1
    if not np.any(on_mask):
        on_mask = np.ones_like(sw, dtype=bool)

    f = freq[on_mask]
    t = time_s[on_mask]
    if f.size < 2:
        return {
            "mean_hz": float("nan"),
            "std_hz": float("nan"),
            "mae_hz": float("nan"),
            "p95_step_hz": float("nan"),
            "max_step_hz": float("nan"),
            "hf_ratio": float("nan"),
            "start_hz": float("nan"),
            "final_hz": float("nan"),
            "final_abs_err_hz": float("nan"),
        }

    step = np.abs(np.diff(f))
    dt = float(np.mean(np.diff(t))) if t.size > 1 else 0.01

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
        "mae_hz": float(np.mean(np.abs(f - TARGET_HZ))),
        "p95_step_hz": float(np.percentile(step, 95)),
        "max_step_hz": float(np.max(step)),
        "hf_ratio": float(hf_ratio),
        "start_hz": float(f[0]),
        "final_hz": float(f[-1]),
        "final_abs_err_hz": float(abs(f[-1] - TARGET_HZ)),
    }


def composite_score(row: pd.Series) -> float:
    return (
        float(row["p95_step_hz"])
        + 0.30 * float(row["mae_hz"])
        + 0.10 * float(row["std_hz"])
        + 0.05 * float(row["final_abs_err_hz"])
    )


def md_table(df: pd.DataFrame, cols: List[str], float_fmt: str = "{:.4f}") -> str:
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    lines = [header, sep]
    for _, row in df.iterrows():
        cells = []
        for col in cols:
            val = row[col]
            if isinstance(val, (float, np.floating)):
                cells.append("nan" if np.isnan(val) else float_fmt.format(float(val)))
            else:
                cells.append(str(val))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def build_plot(
    tag: str,
    baseline_df: pd.DataFrame,
    traces: Dict[str, np.ndarray],
    method_specs: Dict[str, MethodSpec],
    out_png: Path,
) -> None:
    t = baseline_df["Time_s"].to_numpy(dtype=float)
    sw = baseline_df["SW"].to_numpy(dtype=int)

    plx = baseline_df["PLX"].to_numpy(dtype=float)
    ply = baseline_df["PLY"].to_numpy(dtype=float)
    plz = baseline_df["PLZ"].to_numpy(dtype=float)

    # Remove DC component to make oscillation behavior visible on one axis.
    plx_z = plx - np.mean(plx)
    ply_z = ply - np.mean(ply)
    plz_z = plz - np.mean(plz)

    fig, (ax_top, ax_bottom) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    ax_top.plot(t, plx_z, color="tab:red", linewidth=0.8, label="PLX (dc removed)")
    ax_top.plot(t, ply_z, color="tab:green", linewidth=0.8, label="PLY (dc removed)")
    ax_top.plot(t, plz_z, color="tab:blue", linewidth=0.8, alpha=0.85, label="PLZ (dc removed)")
    ax_top.set_ylabel("Payload force (relative)")
    ax_top.grid(True, alpha=0.3)
    ax_top.legend(loc="upper right", ncol=2)

    ax_sw = ax_top.twinx()
    ax_sw.plot(t, sw, "k--", linewidth=0.9, alpha=0.75, label="SW")
    ax_sw.set_ylabel("SW")
    ax_sw.set_ylim(-0.1, 1.1)

    for method_name, f in traces.items():
        spec = method_specs[method_name]
        ax_bottom.plot(t, f, linewidth=1.0, color=spec.color, label=spec.label)

    ax_bottom.axhline(TARGET_HZ, color="black", linestyle="--", linewidth=1.0, label=f"Target={TARGET_HZ:.2f}Hz")
    ax_bottom.set_title(f"{tag}: EKF frequency estimation comparison")
    ax_bottom.set_xlabel("Time [s]")
    ax_bottom.set_ylabel("Estimated frequency [Hz]")
    ax_bottom.grid(True, alpha=0.3)
    ax_bottom.legend(loc="best", ncol=2)

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate EKF algorithm comparison report")
    parser.add_argument(
        "--outdir",
        default="analysis/replay/results/diagnostics/ekf_algorithm_comparison_2026-04-06",
        help="Output directory for plots/csv/report",
    )
    parser.add_argument(
        "--tags",
        nargs="+",
        default=["00000443", "00000444"],
        help="Replay log tags to compare",
    )
    args = parser.parse_args()

    outdir = Path(args.outdir)
    fig_dir = outdir / "figures"
    outdir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    method_map = {m.name: m for m in METHODS}

    metrics_rows: List[Dict[str, object]] = []
    run_map: Dict[str, Dict[str, str]] = {}

    for tag in args.tags:
        run_map[tag] = {}

        loaded: Dict[str, pd.DataFrame] = {}
        for spec in METHODS:
            p = Path(spec.path_template.format(tag=tag))
            if not p.exists():
                raise FileNotFoundError(f"Missing input CSV for {spec.name}: {p}")
            loaded[spec.name] = pd.read_csv(p)
            run_map[tag][spec.name] = str(p)

        # Use baseline timeline as reference and interpolate other methods if needed.
        base_df = loaded["baseline_3axis_logsw"]
        t_ref = base_df["Time_s"].to_numpy(dtype=float)
        sw_ref = base_df["SW"].to_numpy(dtype=int)

        traces: Dict[str, np.ndarray] = {}
        for method_name, df in loaded.items():
            t_src = df["Time_s"].to_numpy(dtype=float)
            f_src = df["EstFreq_Hz"].to_numpy(dtype=float)
            if np.array_equal(t_ref, t_src):
                f_resampled = f_src
            else:
                f_resampled = np.interp(t_ref, t_src, f_src, left=f_src[0], right=f_src[-1])

            traces[method_name] = f_resampled

            met = compute_metrics(f_resampled, t_ref, sw_ref)
            metrics_rows.append(
                {
                    "log": tag,
                    "method": method_name,
                    "method_label": method_map[method_name].label,
                    **met,
                }
            )

        build_plot(
            tag=tag,
            baseline_df=base_df,
            traces=traces,
            method_specs=method_map,
            out_png=fig_dir / f"{tag}_ekf_algorithm_comparison.png",
        )

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df["score"] = metrics_df.apply(composite_score, axis=1)
    metrics_df = metrics_df.sort_values(["log", "score"], ascending=[True, True])
    metrics_csv = outdir / "ekf_algorithm_metrics.csv"
    metrics_df.to_csv(metrics_csv, index=False)

    agg_df = (
        metrics_df.groupby(["method", "method_label"], as_index=False)
        .agg(
            score=("score", "mean"),
            mae_hz=("mae_hz", "mean"),
            std_hz=("std_hz", "mean"),
            p95_step_hz=("p95_step_hz", "mean"),
            max_step_hz=("max_step_hz", "mean"),
            hf_ratio=("hf_ratio", "mean"),
            final_abs_err_hz=("final_abs_err_hz", "mean"),
        )
        .sort_values("score", ascending=True)
    )
    agg_csv = outdir / "ekf_algorithm_ranking.csv"
    agg_df.to_csv(agg_csv, index=False)

    best_method = str(agg_df.iloc[0]["method_label"])

    report_path = outdir / "EKF_ALGORITHM_COMPARISON_REPORT_2026-04-06.md"
    lines: List[str] = []
    lines.append("# EKFアルゴリズム比較レポート (2026-04-06)")
    lines.append("")
    lines.append("## 目的")
    lines.append("- 複数EKF実装方針の周波数推定結果を、同一ログ・同一時間軸で比較する。")
    lines.append("- 各ログで上段に生データの揺れとSW、下段に推定周波数を重ねて挙動差を評価する。")
    lines.append("")
    lines.append("## 比較対象")
    lines.append("- Baseline EKF (3軸融合, log SW)")
    lines.append("- XY EKF always-on")
    lines.append("- XY EKF SW-hold")
    lines.append("- XY EKF SW+amp-gate")
    lines.append("- Fixed init 0.45Hz (q_w=1e-9)")
    lines.append("- Fixed init 0.60Hz (q_w=1e-9)")
    lines.append("")
    lines.append("## 作図")
    for tag in args.tags:
        lines.append(f"- {tag}: figures/{tag}_ekf_algorithm_comparison.png")
    lines.append("")
    lines.append("## 評価指標")
    lines.append("- mean_hz, std_hz, mae_hz (target=0.45Hz)")
    lines.append("- p95_step_hz, max_step_hz (時間差分の滑らかさ)")
    lines.append("- hf_ratio (2-20Hz / 0-0.5Hz パワー比)")
    lines.append("- final_abs_err_hz")
    lines.append("- 合成スコア = p95_step + 0.30*MAE + 0.10*std + 0.05*final_abs_err")
    lines.append("")
    lines.append("## 総合ランキング (2ログ平均)")
    lines.append(md_table(agg_df, ["method_label", "score", "mae_hz", "std_hz", "p95_step_hz", "hf_ratio", "final_abs_err_hz"]))
    lines.append("")
    lines.append(f"最良方式: {best_method}")
    lines.append("")

    lines.append("## ログ別ランキング")
    for tag, group in metrics_df.groupby("log"):
        lines.append("")
        lines.append(f"### {tag}")
        lines.append(md_table(group.sort_values("score"), ["method_label", "score", "mae_hz", "std_hz", "p95_step_hz", "hf_ratio", "final_abs_err_hz"]))

    lines.append("")
    lines.append("## 方針検討に向けた所見")
    lines.append("- XY系はZ軸混入を避けるため、ログによってはBaselineより安定化しやすい。")
    lines.append("- SW-holdはSW OFF区間のドリフト抑制に有効だが、ON/OFF運用次第で追従性とのトレードオフが出る。")
    lines.append("- 固定初期値EKFは初期値依存性が明確で、0.60Hz初期はバイアス残留リスクが高い。")
    lines.append("- 実運用方針としては、XYベース + 低q_w + 必要に応じたSW-holdの組合せが現実的。")
    lines.append("")
    lines.append("## 出力ファイル")
    lines.append(f"- metrics CSV: {metrics_csv}")
    lines.append(f"- ranking CSV: {agg_csv}")
    lines.append(f"- report: {report_path}")

    report_path.write_text("\n".join(lines), encoding="utf-8")

    runmap_path = outdir / "input_run_map.csv"
    rows = []
    for tag, mp in run_map.items():
        for method_name, p in mp.items():
            rows.append({"log": tag, "method": method_name, "input_csv": p})
    pd.DataFrame(rows).to_csv(runmap_path, index=False)

    print(f"Wrote: {report_path}")
    print(f"Wrote: {metrics_csv}")
    print(f"Wrote: {agg_csv}")
    print(f"Wrote: {runmap_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
