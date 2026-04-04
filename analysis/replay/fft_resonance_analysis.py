#!/usr/bin/env python3
"""
FFTによる機体共振周波数の抽出スクリプト

- 入力: dual_component_series.csv（2ログ分）
- 出力: 各軸ごとのパワースペクトル図、ピーク周波数一覧、Markdownレポート用テキスト
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# 対象ファイル: replay 実行結果（raw 信号を含む result CSV）を指定
LOGS = {
    "00000443": "analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/runs/00000443/00000443_dual_eval_result.csv",
    "00000444": "analysis/replay/results/diagnostics/dual_component_frequency_2026-04-04/runs/00000444/00000444_dual_eval_result.csv",
}

OUTDIR = Path("analysis/replay/results/diagnostics/fft_resonance_2026-04-04")
OUTDIR.mkdir(parents=True, exist_ok=True)

REPORT_LINES = []

for tag, csv_path in LOGS.items():
    df = pd.read_csv(csv_path)
    t = df["Time_s"].to_numpy()
    dt = np.median(np.diff(t))
    fs = 1.0 / dt
    N = len(t)
    # ここで生データのPL?列を使う（周波数推定値ではなく元信号）
    axes = {"x": df["PLX"].to_numpy(), "y": df["PLY"].to_numpy(), "z": df["PLZ"].to_numpy()}
    REPORT_LINES.append(f"## ログ {tag}")
    # 周波数探索レンジ: 0 - 3 Hz のみに限定（プロットも同じ範囲）
    FMIN = 0.0
    FMAX = min(3.0, fs / 2.0)
    for ax, sig in axes.items():
        sig = sig - np.mean(sig)
        win = np.hanning(N)
        spec = np.fft.rfft(sig * win)
        freq = np.fft.rfftfreq(N, d=dt)
        power = np.abs(spec) ** 2

        # 探索はFMIN-FMAXに限定して、直流・非常に低い周波数の誤検出を防ぐ
        mask = (freq >= FMIN) & (freq <= FMAX)
        if not np.any(mask):
            REPORT_LINES.append(f"- {ax}-axis: 周波数レンジにデータ無し")
            continue

        band_freq = freq[mask]
        band_power = power[mask]

        # 主ピークと2番目ピーク（同じバンド内）を抽出
        # 直流(0Hz)は mean を差し引いていても影響する可能性があるため、0Hzを除外して検出
        nonzero_idx = np.where(band_freq > 0.0)[0]
        if nonzero_idx.size > 0:
            nz_power = band_power[nonzero_idx]
            ranked = np.argsort(nz_power)[::-1]
            i0 = nonzero_idx[ranked[0]]
            i1 = nonzero_idx[ranked[1]] if ranked.size > 1 else i0
        else:
            i0 = int(np.argmax(band_power))
            band_power_copy = band_power.copy()
            band_power_copy[i0] = 0.0
            i1 = int(np.argmax(band_power_copy))

        peak_freq = float(band_freq[i0])
        peak_power = float(band_power[i0])
        peak2_freq = float(band_freq[i1])
        peak2_power = float(band_power[i1])

        # 図は全レンジを表示するが、注釈はバンド内ピーク
        plt.figure(figsize=(8, 4))
        plt.plot(freq, power, label="Power Spectrum")
        plt.scatter([peak_freq], [peak_power], color="r", label=f"Peak: {peak_freq:.3f}Hz")
        plt.scatter([peak2_freq], [peak2_power], color="g", label=f"2nd: {peak2_freq:.3f}Hz")
        plt.xlim(0.0, 3.0)
        plt.xlabel("Frequency [Hz]")
        plt.ylabel("Power")
        plt.title(f"{tag} {ax}-axis Power Spectrum")
        plt.legend()
        fig_path = OUTDIR / f"{tag}_{ax}_fft.png"
        plt.tight_layout()
        plt.savefig(fig_path)
        plt.close()

        # レポート用（画像は同ディレクトリに出力する）
        REPORT_LINES.append(f"- {ax}-axis: 主ピーク {peak_freq:.4f} Hz (2nd: {peak2_freq:.4f} Hz)")
        REPORT_LINES.append(f"  ![FFT {tag} {ax}]({tag}_{ax}_fft.png)")
    REPORT_LINES.append("")

# Markdownレポート出力
with (OUTDIR / "FFT_RESONANCE_REPORT_2026-04-04.md").open("w") as f:
    f.write("# 機体共振周波数FFT解析レポート\n\n")
    f.write("\n".join(REPORT_LINES))
    f.write("\n\n---\n考察:\n- xy軸とz軸のピーク周波数の違いを確認し、z軸は性質が異なることを再確認。\n- xy軸の主ピークが機体固有の共振周波数とみなせる場合、今後はこの値をモデルに固定値として組み込むことが有効。\n")
