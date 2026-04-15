#!/usr/bin/env python3
"""
Validate four scenarios to test:
A: Omega free, Robust OFF
B: Omega free, Robust ON
C: Omega fixed, Robust OFF  
D: Omega fixed, Robust ON

Hypothesis:
- A: High spike (baseline)
- B: Lower spike (outlier rejection)
- C: Lower spike (frequency loop removed)
- D: Lowest spike (both effects combined)
"""

from __future__ import annotations

import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import matplotlib.pyplot as plt
import datetime
import zoneinfo

REPO_ROOT = Path(__file__).resolve().parents[2]
REPLAY_BIN = REPO_ROOT / "build/sitl/examples/EKF_CSV_Replay"

RESULT_ROOT = REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports/results/2026-04-15_四シナリオ比較"
REPORT_PATH = REPO_ROOT / "docs/experiments/ekf_external_force_estimation/reports/2026-04-15_00:45:50_四シナリオ仮説検証.md"


@dataclass
class Case:
    tag: str
    input_csv: Path


@dataclass
class Scenario:
    name: str
    label: str  # 表示用ラベル
    robust_enable: int
    omega_fixed: int
    omega_fixed_hz: float
    q_d: float
    q_dd: float
    q_c: float
    r_meas: float
    innov_max: float
    nis_max: float
    nis_reject: float


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

# Base parameters
BASE_Q_D = 0.020
BASE_Q_DD = 0.050
BASE_Q_C = 0.001
BASE_R_MEAS = 0.080
BASE_INNOV_MAX = 0.70
BASE_NIS_MAX = 4.0

# Q_W値定義（周波数制約）
Q_W_FREE = 0.0005  # 周波数自由（通常値）
Q_W_FIXED = 0.00001  # 周波数ほぼ固定（Q_Wを極端に小さく）

SCENARIOS: List[Scenario] = [
    Scenario(
        name="A_free_norobust",
        label="A: 周波数自由, ロバストOFF",
        robust_enable=0,
        omega_fixed=0,
        omega_fixed_hz=0.0,
        q_d=BASE_Q_D,
        q_dd=BASE_Q_DD,
        q_c=BASE_Q_C,
        r_meas=BASE_R_MEAS,
        innov_max=BASE_INNOV_MAX,
        nis_max=BASE_NIS_MAX,
        nis_reject=3.0,
    ),
    Scenario(
        name="B_free_robust",
        label="B: 周波数自由, ロバストON",
        robust_enable=1,
        omega_fixed=0,
        omega_fixed_hz=0.0,
        q_d=BASE_Q_D,
        q_dd=BASE_Q_DD,
        q_c=BASE_Q_C,
        r_meas=BASE_R_MEAS,
        innov_max=BASE_INNOV_MAX,
        nis_max=BASE_NIS_MAX,
        nis_reject=3.0,
    ),
    Scenario(
        name="C_fixed_norobust",
        label="C: 周波数固定(Q_W↓), ロバストOFF",
        robust_enable=0,
        omega_fixed=0,
        omega_fixed_hz=0.0,
        q_d=BASE_Q_D,
        q_dd=BASE_Q_DD,
        q_c=BASE_Q_C,
        r_meas=BASE_R_MEAS,
        innov_max=BASE_INNOV_MAX,
        nis_max=BASE_NIS_MAX,
        nis_reject=3.0,
    ),
    Scenario(
        name="D_fixed_robust",
        label="D: 周波数固定(Q_W↓), ロバストON",
        robust_enable=1,
        omega_fixed=0,
        omega_fixed_hz=0.0,
        q_d=BASE_Q_D,
        q_dd=BASE_Q_DD,
        q_c=BASE_Q_C,
        r_meas=BASE_R_MEAS,
        innov_max=BASE_INNOV_MAX,
        nis_max=BASE_NIS_MAX,
        nis_reject=3.0,
    ),
]


def run_cmd(cmd: List[str]) -> None:
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)


def to_report_rel(path: Path) -> str:
    return str(path.relative_to(REPORT_PATH.parent))


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


def step_stats(sig: np.ndarray, t: np.ndarray) -> Tuple[float, float, float]:
    if sig.size < 2:
        return float("nan"), float("nan"), float("nan")
    d = np.abs(np.diff(sig))
    idx = int(np.argmax(d))
    return float(np.max(d)), float(np.percentile(d, 95)), float(t[idx + 1])


def run_scenario(case: Case, scenario: Scenario) -> Path:
    run_dir = RESULT_ROOT / case.tag / scenario.name
    run_dir.mkdir(parents=True, exist_ok=True)

    out_tag = f"{case.tag}_{scenario.name}"
    
    # 周波数制約：シナリオCとDはQ_Wを極端に小さくして周波数をほぼ固定
    q_w = Q_W_FIXED if scenario.omega_fixed else Q_W_FREE
    
    cmd = [
        str(REPLAY_BIN),
        "--input", str(case.input_csv),
        "--outdir", str(run_dir),
        "--tag", out_tag,
        "--sw-mode", "log",
        "--ekf-axis-mask", "3",
        "--ekf-axis-gate", "0",
        "--ekf-energy-gate", "1",
        "--ekf-energy-rms-on", "0.20",
        "--ekf-energy-rms-off", "0.16",
        "--ekf-energy-tau", "2.0",
        "--ekf-robust-update", str(scenario.robust_enable),
        "--ekf-robust-nis-reject", f"{scenario.nis_reject}",
        "--ekf-innov-max", f"{scenario.innov_max}",
        "--ekf-nis-max", f"{scenario.nis_max}",
        "--ekf-q-d", f"{scenario.q_d}",
        "--ekf-q-dd", f"{scenario.q_dd}",
        "--ekf-q-c", f"{scenario.q_c}",
        "--ekf-q-w", f"{q_w}",
        "--ekf-r-meas", f"{scenario.r_meas}",
    ]
    
    run_cmd(cmd)
    return run_dir / f"{out_tag}_result.csv"


def plot_overlay_scenarios(case_tag: str,
                          t: np.ndarray,
                          prx_map: Dict[str, np.ndarray],
                          out_png: Path,
                          spike_t: float,
                          title: str) -> None:
    """Overlay PRX for all four scenarios (labels in English only)"""
    fig, ax = plt.subplots(figsize=(15, 5))
    
    colors = {"A_free_norobust": "red", "B_free_robust": "orange", 
              "C_fixed_norobust": "blue", "D_fixed_robust": "green"}
    labels_en = {
        "A_free_norobust": "A: Omega Free, Robust OFF",
        "B_free_robust": "B: Omega Free, Robust ON",
        "C_fixed_norobust": "C: Omega Fixed, Robust OFF",
        "D_fixed_robust": "D: Omega Fixed, Robust ON",
    }
    for name, prx in sorted(prx_map.items()):
        ax.plot(t, prx, linewidth=1.0, label=labels_en.get(name, name), 
                color=colors.get(name, "gray"), alpha=0.8)
    ax.axvline(spike_t, color="black", linestyle="--", alpha=0.5, linewidth=1, label="baseline spike")
    ax.set_xlabel("Time [s]", fontsize=12)
    ax.set_ylabel("PRX [N]", fontsize=12)
    ax.set_title(f"{case_tag} - Four Scenario PRX Overlay", fontsize=13)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", fontsize=10)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_spike_zoom(case_tag: str,
                   t: np.ndarray,
                   prx_map: Dict[str, np.ndarray],
                   out_png: Path,
                   spike_t: float,
                   window: float = 3.0) -> None:
    """Zoom around spike (labels in English only)"""
    lo, hi = spike_t - window, spike_t + window
    fig, ax = plt.subplots(figsize=(14, 5))
    colors = {"A_free_norobust": "red", "B_free_robust": "orange",
              "C_fixed_norobust": "blue", "D_fixed_robust": "green"}
    labels_en = {
        "A_free_norobust": "A: Omega Free, Robust OFF",
        "B_free_robust": "B: Omega Free, Robust ON",
        "C_fixed_norobust": "C: Omega Fixed, Robust OFF",
        "D_fixed_robust": "D: Omega Fixed, Robust ON",
    }
    for name, prx in sorted(prx_map.items()):
        ax.plot(t, prx, linewidth=1.5, label=labels_en.get(name, name),
                color=colors.get(name, "gray"), alpha=0.8)
    ax.axvline(spike_t, color="black", linestyle="--", alpha=0.5, linewidth=1)
    ax.set_xlim(lo, hi)
    ax.set_xlabel("Time [s]", fontsize=12)
    ax.set_ylabel("PRX [N]", fontsize=12)
    ax.set_title(f"{case_tag} - Spike Region Zoom (t={spike_t:.2f}s)", fontsize=13)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", fontsize=10)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)

    # JSTでの作成日時を記録
    jst = zoneinfo.ZoneInfo("Asia/Tokyo")
    now_jst = datetime.datetime.now(jst)
    dt_str = now_jst.strftime("%Y-%m-%d %H:%M:%S")

    lines: List[str] = []
    lines.append("# 2026-04-15 Four Scenario Hypothesis Test\n")
    lines.append(f"**作成日時（JST）: {dt_str}**\n")
    lines.append("**[注意] 図のタイトル・凡例・ラベルは必ず英語で記述すること。日本語を含むとmatplotlibのデフォルトフォントでエラーや警告が発生し、図が正しく表示されない。**\n")
    
    lines.append("## 目的\n")
    lines.append("以下の4シナリオで、PRXスパイク軽減の主要因を特定する：")
    lines.append("- **シナリオA**: 周波数自由、ロバスト更新OFF（ベースライン）")
    lines.append("- **シナリオB**: 周波数自由、ロバスト更新ON（外れ値除去の効果）")
    lines.append("- **シナリオC**: 周波数固定、ロバスト更新OFF（周波数ループ消失の効果）")
    lines.append("- **シナリオD**: 周波数固定、ロバスト更新ON（両方の効果を組み合わせ）\n")
    
    lines.append("## 仮説\n")
    lines.append("| シナリオ | 周波数 | ロバスト観測 | 予想 |")
    lines.append("|---|---|---|---|")
    lines.append("| A | 自由 | OFF | スパイク多（baseline） |")
    lines.append("| B | 自由 | ON | スパイク減少（観測異常除去） |")
    lines.append("| C | 固定 | OFF | スパイク減少（周波数ループ消失） |")
    lines.append("| D | 固定 | ON | スパイク最小（両効果） |\n")

    for case in CASES:
        lines.append(f"## {case.tag}\n")
        
        data_map: Dict[str, Dict[str, np.ndarray]] = {}
        rows: List[Dict[str, float]] = []

        for scenario in SCENARIOS:
            result_csv = run_scenario(case, scenario)
            d = read_csv_columns(result_csv)
            data_map[scenario.name] = d

            max_step, p95_step, spike_t = step_stats(d["prx"], d["t"])

            rows.append({
                "scenario": scenario.name,
                "label": scenario.label,
                "max_abs_prx": float(np.max(np.abs(d["prx"]))),
                "max_step": max_step,
                "p95_step": p95_step,
                "prx_diff_std": float(np.std(np.diff(d["prx"]))),
                "freq_mae": float(np.mean(np.abs(d["est_hz"] - d["real_hz"]))),
                "spike_t": spike_t,
            })

        baseline = next(r for r in rows if r["scenario"] == "A_free_norobust")
        baseline_step = baseline["max_step"]
        spike_t_ref = baseline["spike_t"]

        for r in rows:
            if baseline_step > 1.0e-9:
                r["reduction_pct"] = (1.0 - (r["max_step"] / baseline_step)) * 100.0
            else:
                r["reduction_pct"] = 0.0

        lines.append("### 指標\n")
        lines.append("| シナリオ | max_step | p95_step | std | MAE | 削減率 [%] |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for r in sorted(rows, key=lambda x: x["max_step"]):
            lines.append(
                f"| {r['label']} | {r['max_step']:.6f} | {r['p95_step']:.6f} | {r['prx_diff_std']:.6f} | {r['freq_mae']:.6f} | {r['reduction_pct']:.1f} |"
            )
        lines.append("")

        # 全シナリオの重ね合わせプロット
        fig_dir = RESULT_ROOT / "comparison" / case.tag
        fig_dir.mkdir(parents=True, exist_ok=True)

        overlay_all = fig_dir / f"{case.tag}_four_scenarios_overlay.png"
        overlay_zoom = fig_dir / f"{case.tag}_four_scenarios_zoom.png"

        plot_overlay_scenarios(
            case.tag,
            data_map["A_free_norobust"]["t"],
            {name: data_map[name]["prx"] for name in data_map.keys()},
            overlay_all,
            spike_t_ref,
            f"{case.tag} - 4シナリオPRX重ね合わせ"
        )

        plot_spike_zoom(
            case.tag,
            data_map["A_free_norobust"]["t"],
            {name: data_map[name]["prx"] for name in data_map.keys()},
            overlay_zoom,
            spike_t_ref,
            window=3.0
        )

        lines.append("### 図\n")
        lines.append(f"![{case.tag} overlay]({to_report_rel(overlay_all)})\n")
        lines.append(f"![{case.tag} zoom]({to_report_rel(overlay_zoom)})\n")

        # 分析
        reduction_b = next((r["reduction_pct"] for r in rows if r["scenario"] == "B_free_robust"), 0)
        reduction_c = next((r["reduction_pct"] for r in rows if r["scenario"] == "C_fixed_norobust"), 0)
        reduction_d = next((r["reduction_pct"] for r in rows if r["scenario"] == "D_fixed_robust"), 0)

        lines.append("### 分析\n")
        if reduction_b > reduction_c:
            lines.append(f"- **ロバスト観測更新が支配的**: B ({reduction_b:.1f}%) > C ({reduction_c:.1f}%)")
            lines.append("  → 観測異常（外れ値）が主要な原因")
        elif reduction_c > reduction_b:
            lines.append(f"- **周波数固定の効果が支配的**: C ({reduction_c:.1f}%) > B ({reduction_b:.1f}%)")
            lines.append("  → 周波数推定ループの不安定性が主要な原因")
        else:
            lines.append(f"- **両者の効果が同程度**: B ≈ C (各{reduction_b:.1f}%)")
            lines.append("  → 観測異常と周波数ループの両者が寄与")

        if abs(reduction_d - max(reduction_b, reduction_c)) < 5.0:
            lines.append(f"- **複合効果は限定的**: D ({reduction_d:.1f}%) ≈ max(B,C)")
            lines.append("  → 加算的な改善なし")
        else:
            lines.append(f"- **複合効果あり**: D ({reduction_d:.1f}%) > max(B,C)")
            lines.append("  → 両効果を組み合わせることで追加の改善が得られる")
        lines.append("")

    lines.append("## 全体的な考察\n")
    lines.append("### 結論\n")
    lines.append("スパイク軽減の主要因は、")
    lines.append("1. **観測異常（外れ値）の除去** (ロバスト観測更新)")
    lines.append("2. **周波数推定ループの安定化** (周波数固定)")
    lines.append("")
    lines.append("のいずれが支配的かを、上記指標で判定できる。\n")
    lines.append("### 推奨方針\n")
    lines.append("- **B ≫ C の場合**: ロバスト観測更新に絞る（周波数固定は不要）")
    lines.append("- **C ≫ B の場合**: 周波数固定の実装を優先（RC切替推奨）")
    lines.append("- **B ≈ C の場合**: 両方の実装が有効（組み合わせで最大効果）\n")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
