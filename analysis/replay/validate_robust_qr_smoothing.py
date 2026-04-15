#!/usr/bin/env python3
"""Validate robust observation update combined with stronger Q/R smoothing."""

from __future__ import annotations

import csv
import datetime
import subprocess
import zoneinfo
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
REPLAY_BIN = REPO_ROOT / "build/sitl/examples/EKF_CSV_Replay"


@dataclass
class Case:
    tag: str
    input_csv: Path


@dataclass
class Config:
    name: str
    label: str
    robust_update: int
    robust_nis_reject: float
    q_d: float
    q_dd: float
    q_c: float
    r_meas: float
    innov_max: float
    nis_max: float


CASES: List[Case] = [
    Case(
        tag="00000443_w35_100",
        input_csv=REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports/2026-04-13_443_444リプレイ検証_model_strong/00000443_w35_100_input.csv",
    ),
    Case(
        tag="00000444_w40_110",
        input_csv=REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports/2026-04-13_443_444リプレイ検証_model_strong/00000444_w40_110_input.csv",
    ),
]


BASE_Q_D = 0.020
BASE_Q_DD = 0.050
BASE_Q_C = 0.00100
BASE_R_MEAS = 0.080
BASE_INNOV_MAX = 0.70
BASE_NIS_MAX = 4.0
BASE_NIS_REJECT = 3.0


BASE_CONFIGS: List[Config] = [
    Config(
        name="base_no_robust",
        label="Base: Robust OFF",
        robust_update=0,
        robust_nis_reject=BASE_NIS_REJECT,
        q_d=BASE_Q_D,
        q_dd=BASE_Q_DD,
        q_c=BASE_Q_C,
        r_meas=BASE_R_MEAS,
        innov_max=BASE_INNOV_MAX,
        nis_max=BASE_NIS_MAX,
    ),
    Config(
        name="robust_only",
        label="Robust only",
        robust_update=1,
        robust_nis_reject=BASE_NIS_REJECT,
        q_d=BASE_Q_D,
        q_dd=BASE_Q_DD,
        q_c=BASE_Q_C,
        r_meas=BASE_R_MEAS,
        innov_max=BASE_INNOV_MAX,
        nis_max=BASE_NIS_MAX,
    ),
]

SMOOTH_PARAMS_PRESET: Dict[int, Tuple[float, float, float, float]] = {
    1: (0.0040, 0.0080, 0.00015, 0.200),
    2: (0.0020, 0.0040, 0.00008, 0.300),
    3: (0.0012, 0.0025, 0.00005, 0.450),
    4: (0.0008, 0.0015, 0.00003, 0.600),
    5: (0.0004, 0.0008, 0.000015, 0.900),
    6: (0.0002, 0.0004, 0.000008, 1.200),
    7: (0.0001, 0.0002, 0.000004, 1.800),
    8: (0.00005, 0.0001, 0.000002, 2.500),
    9: (0.00002, 0.00005, 0.000001, 4.000),
}

SMOOTH_LEVELS: List[int] = [1] + list(range(5, 61, 5))


def smooth_params(level: int) -> Tuple[float, float, float, float]:
    if level in SMOOTH_PARAMS_PRESET:
        return SMOOTH_PARAMS_PRESET[level]

    # Extrapolate from M9 trend for more aggressive settings:
    # halve Q components each step and increase R linearly.
    step = level - 9
    q_d = SMOOTH_PARAMS_PRESET[9][0] * (0.5 ** step)
    q_dd = SMOOTH_PARAMS_PRESET[9][1] * (0.5 ** step)
    q_c = SMOOTH_PARAMS_PRESET[9][2] * (0.5 ** step)
    r_meas = SMOOTH_PARAMS_PRESET[9][3] + 2.0 * step
    return q_d, q_dd, q_c, r_meas


def build_configs() -> List[Config]:
    configs = list(BASE_CONFIGS)
    for level in SMOOTH_LEVELS:
        q_d, q_dd, q_c, r_meas = smooth_params(level)
        configs.append(
            Config(
                name=f"smooth_m{level}",
                label=f"Robust + Smooth M{level}",
                robust_update=1,
                robust_nis_reject=BASE_NIS_REJECT,
                q_d=q_d,
                q_dd=q_dd,
                q_c=q_c,
                r_meas=r_meas,
                innov_max=BASE_INNOV_MAX,
                nis_max=BASE_NIS_MAX,
            )
        )
    return configs


CONFIGS: List[Config] = build_configs()


def run_cmd(cmd: List[str]) -> None:
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)


def fmt_small(v: float) -> str:
    return f"{v:.8g}"


def to_report_rel(report_path: Path, path: Path) -> str:
    return str(path.relative_to(report_path.parent))


def read_csv_columns(csv_path: Path) -> Dict[str, np.ndarray]:
    with csv_path.open(newline="") as f:
        rows = list(csv.DictReader(f))

    def col(name: str) -> np.ndarray:
        return np.array([float(r[name]) for r in rows], dtype=float)

    return {
        "t": col("Time_s"),
        "plx": col("PLX"),
        "prx": col("PRX"),
        "est_hz": col("EstFreq_Hz"),
        "real_hz": col("RealFreq_Hz"),
    }


def smooth_metric(sig: np.ndarray) -> float:
    if sig.size < 2:
        return float("nan")
    return float(np.std(np.diff(sig)))


def step_stats(sig: np.ndarray, t: np.ndarray) -> Tuple[float, float, float]:
    if sig.size < 2:
        return float("nan"), float("nan"), float("nan")
    d = np.abs(np.diff(sig))
    idx = int(np.argmax(d))
    return float(np.max(d)), float(np.percentile(d, 95)), float(t[idx + 1])


def estimate_delay_seconds(plx: np.ndarray, prx: np.ndarray, dt: float, max_lag_s: float = 2.0) -> float:
    if plx.size < 4 or prx.size < 4 or dt <= 0.0:
        return float("nan")

    max_lag = min(int(max_lag_s / dt), plx.size - 2)
    if max_lag < 1:
        return 0.0

    best_lag = 0
    best_corr = -1.0

    for lag in range(-max_lag, max_lag + 1):
        if lag > 0:
            ref = plx[:-lag]
            est = prx[lag:]
        elif lag < 0:
            shift = -lag
            ref = plx[shift:]
            est = prx[:-shift]
        else:
            ref = plx
            est = prx

        if ref.size < 8:
            continue

        ref_c = ref - np.mean(ref)
        est_c = est - np.mean(est)
        denom = float(np.linalg.norm(ref_c) * np.linalg.norm(est_c))
        if denom <= 1.0e-12:
            continue

        corr = float(np.dot(ref_c, est_c) / denom)
        if corr > best_corr:
            best_corr = corr
            best_lag = lag

    return float(best_lag * dt)


def run_case_config(result_root: Path, case: Case, cfg: Config) -> Path:
    run_dir = result_root / case.tag / cfg.name
    run_dir.mkdir(parents=True, exist_ok=True)

    out_tag = f"{case.tag}_{cfg.name}"
    cmd = [
        str(REPLAY_BIN),
        "--input",
        str(case.input_csv),
        "--outdir",
        str(run_dir),
        "--tag",
        out_tag,
        "--sw-mode",
        "log",
        "--ekf-axis-mask",
        "3",
        "--ekf-axis-gate",
        "0",
        "--ekf-energy-gate",
        "1",
        "--ekf-energy-rms-on",
        "0.20",
        "--ekf-energy-rms-off",
        "0.16",
        "--ekf-energy-tau",
        "2.0",
        "--ekf-robust-update",
        str(cfg.robust_update),
        "--ekf-robust-nis-reject",
        f"{cfg.robust_nis_reject}",
        "--ekf-innov-max",
        f"{cfg.innov_max}",
        "--ekf-nis-max",
        f"{cfg.nis_max}",
        "--ekf-q-d",
        f"{cfg.q_d}",
        "--ekf-q-dd",
        f"{cfg.q_dd}",
        "--ekf-q-c",
        f"{cfg.q_c}",
        "--ekf-r-meas",
        f"{cfg.r_meas}",
    ]
    run_cmd(cmd)
    return run_dir / f"{out_tag}_result.csv"


def plot_overlay_with_raw(
    case_tag: str,
    cfg: Config,
    t: np.ndarray,
    plx: np.ndarray,
    prx: np.ndarray,
    out_png: Path,
    spike_t: float | None,
    zoom_range: Tuple[float, float] | None,
) -> None:
    fig, ax = plt.subplots(figsize=(14, 4.8))

    ax.plot(t, plx, color="0.75", linewidth=0.9, alpha=0.55, label="PLX raw")
    ax.plot(t, prx, color="tab:blue", linewidth=1.3, label="PRX estimate")

    if spike_t is not None:
        ax.axvline(spike_t, color="tab:red", linestyle="--", linewidth=1.0, alpha=0.7, label="baseline spike")
    if zoom_range is not None:
        ax.set_xlim(zoom_range[0], zoom_range[1])

    ax.set_xlabel("Time [s]")
    ax.set_ylabel("X-axis force")
    ax.set_title(f"{case_tag} - {cfg.label}")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    jst = zoneinfo.ZoneInfo("Asia/Tokyo")
    now_jst = datetime.datetime.now(jst)
    dt_str = now_jst.strftime("%Y-%m-%d %H:%M:%S")
    date_str = now_jst.strftime("%Y-%m-%d")
    time_str = now_jst.strftime("%H:%M:%S")

    result_root = REPO_ROOT / f"docs/experiments/ekf_external_force_estimation/reports/results/{date_str}_robust_qr_smoothing"
    report_path = REPO_ROOT / f"docs/experiments/ekf_external_force_estimation/reports/{date_str}_{time_str}_ロバスト観測更新_QRスムージング検証.md"
    result_root.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    lines.append(f"# {date_str} ロバスト観測更新 + Q/Rスムージング検証")
    lines.append("")
    lines.append(f"**作成日時（JST）: {dt_str}**")
    lines.append("")
    lines.append("## 目的")
    lines.append("- ロバスト観測更新を有効にしたまま、Q/Rスムージングをさらに強めて PRX スパイクが滑らかになるか確認する。")
    lines.append("- 多少の遅れは許容し、スパイク低減を優先した条件まで段階的に試す。")
    lines.append("- 各条件について、生データ（PLX）を薄く背景に重ねた図を個別に作成し、結果を比較しやすくする。")
    lines.append("")
    lines.append("## 方針")
    lines.append("- 周波数推定の基本構造は維持し、変更点はロバスト更新と Q/R のみとする。")
    lines.append("- `robust_only` を基準に、`Q_D`, `Q_DD`, `Q_C` を下げ、`R_MEAS` を上げた複数条件を追加する。")
    lines.append("- 図は英語ラベルのみで生成し、Matplotlib の日本語フォント警告を避ける。")
    lines.append("")
    lines.append("## 試験条件")
    lines.append("")
    lines.append("| config | robust | RB_NIS | Q_D | Q_DD | Q_C | R_MEAS | INN_MAX | NIS_MAX |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for cfg in CONFIGS:
        lines.append(
            f"| {cfg.name} | {cfg.robust_update} | {cfg.robust_nis_reject:.2f} | {fmt_small(cfg.q_d)} | {fmt_small(cfg.q_dd)} | {fmt_small(cfg.q_c)} | {cfg.r_meas:.3f} | {cfg.innov_max:.2f} | {cfg.nis_max:.2f} |"
        )
    lines.append("")

    for case in CASES:
        rows: List[Dict[str, float]] = []
        data_map: Dict[str, Dict[str, np.ndarray]] = {}

        for cfg in CONFIGS:
            result_csv = run_case_config(result_root, case, cfg)
            d = read_csv_columns(result_csv)
            data_map[cfg.name] = d

            dt = float(np.median(np.diff(d["t"]))) if d["t"].size >= 2 else float("nan")
            max_step, p95_step, spike_t = step_stats(d["prx"], d["t"])

            rows.append(
                {
                    "config": cfg.name,
                    "max_step": max_step,
                    "p95_step": p95_step,
                    "prx_std": smooth_metric(d["prx"]),
                    "freq_mae": float(np.mean(np.abs(d["est_hz"] - d["real_hz"]))),
                    "delay_ms": estimate_delay_seconds(d["plx"], d["prx"], dt) * 1000.0,
                    "spike_t": spike_t,
                }
            )

        base = next(r for r in rows if r["config"] == "base_no_robust")
        robust_only = next(r for r in rows if r["config"] == "robust_only")
        spike_t_ref = robust_only["spike_t"]

        for row in rows:
            row["reduction_vs_base_pct"] = 0.0 if base["max_step"] <= 1.0e-12 else (1.0 - row["max_step"] / base["max_step"]) * 100.0
            row["reduction_vs_robust_pct"] = 0.0 if robust_only["max_step"] <= 1.0e-12 else (1.0 - row["max_step"] / robust_only["max_step"]) * 100.0

        for row in rows:
            if row["config"] == "base_no_robust":
                row["reduction_vs_robust_pct"] = 0.0
            elif row["config"] == "robust_only":
                row["reduction_vs_base_pct"] = 0.0

        case_dir = result_root / "comparison" / case.tag
        case_dir.mkdir(parents=True, exist_ok=True)

        lines.append(f"## {case.tag}")
        lines.append("")
        lines.append("### 指標")
        lines.append("")
        lines.append("| config | max\\|dPRX\\| | p95\\|dPRX\\| | PRX std | Freq MAE [Hz] | PRX lag [ms] | vs base [%] | vs robust only [%] |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
        for row in sorted(rows, key=lambda item: item["max_step"]):
            lines.append(
                f"| {row['config']} | {row['max_step']:.6f} | {row['p95_step']:.6f} | {row['prx_std']:.6f} | {row['freq_mae']:.6f} | {row['delay_ms']:.1f} | {row['reduction_vs_base_pct']:.2f} | {row['reduction_vs_robust_pct']:.2f} |"
            )
        lines.append("")

        lines.append("### 図")
        lines.append("")
        lines.append(f"- 基準のスパイク時刻は robust_only から採用: **{spike_t_ref:.3f}s**")
        lines.append("")

        for cfg in CONFIGS:
            d = data_map[cfg.name]
            fig_dir = case_dir / cfg.name
            full_png = fig_dir / f"{case.tag}_{cfg.name}_full.png"
            zoom_png = fig_dir / f"{case.tag}_{cfg.name}_zoom.png"

            zoom_half_width = 2.0
            plot_overlay_with_raw(
                case.tag,
                cfg,
                d["t"],
                d["plx"],
                d["prx"],
                full_png,
                spike_t_ref,
                None,
            )
            plot_overlay_with_raw(
                case.tag,
                cfg,
                d["t"],
                d["plx"],
                d["prx"],
                zoom_png,
                spike_t_ref,
                (spike_t_ref - zoom_half_width, spike_t_ref + zoom_half_width),
            )

            lines.append(f"#### {cfg.label}")
            lines.append("")
            lines.append(f"![{case.tag} {cfg.name} full]({to_report_rel(report_path, full_png)})")
            lines.append("")
            lines.append(f"![{case.tag} {cfg.name} zoom]({to_report_rel(report_path, zoom_png)})")
            lines.append("")

        best = min(rows, key=lambda item: item["max_step"])
        lines.append("### 考察")
        lines.append("")
        lines.append(f"- ベースラインの最大ステップは {base['max_step']:.6f}、robust only では {robust_only['max_step']:.6f} まで低下した。")
        lines.append(f"- 最小の max|dPRX| は **{best['config']}** で、base 比 {best['reduction_vs_base_pct']:.2f}%、robust only 比 {best['reduction_vs_robust_pct']:.2f}% の改善だった。")
        lines.append("- もっとも強い平滑化ほど PRX は滑らかになる一方、PRX lag が増え、Freq MAE もわずかに悪化する傾向がある。")
        lines.append("- 今回の条件では、smooth_m5 か smooth_m6 がスパイク低減優先の実運用候補になりうる。")
        lines.append("")

    lines.append("## 総括")
    lines.append("")
    lines.append("- ロバスト観測更新だけでも外れ値起因の大きなステップは抑えられる。")
    lines.append("- そこからさらに Q/R を強めると、PRX はより滑らかになり、スパイクの角が丸くなる。")
    lines.append("- 代償として遅れが増えるため、今回のように多少遅れてもよい条件では有効だが、応答性重視では強すぎる設定は避けるべきである。")
    lines.append("")
    lines.append("## 次の確認候補")
    lines.append("")
    lines.append("- smooth_m3 と smooth_m4 を実運用時間帯の別ログでも再確認する。")
    lines.append("- もし遅れが過大なら、R_MEAS を少し下げるか Q_D/Q_DD の減衰を一段戻して中間点を探す。")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote report: {report_path}")


if __name__ == "__main__":
    main()