# リプレイ検証レポート - 簡潔版 (2026-04-04)

## 1. 問題と目的
- **問題**: EKF推定周波数が約72秒以降で急に大きくなり、SW ON時と同期している
- **目標周波数**: 0.45 Hz（ホバリング時の推定値として妥当な値）
- **本検証の目的**: 原因特定と改善実装の検証

## 2. 主要結果（グラフベース）

### 2.1 シナリオ別メトリクス比較
![Scenario Metrics Comparison](diagnostics/section8_metrics_comparison.png)

**キー発見:**
- **noreset_log（推奨）**: MAE = **0.0335 Hz** （目標比: -93% 誤差）
- **Baseline（旧）**: MAE = 0.1831 Hz （SW ON時に-0.134 Hzジャンプ）
- **Always-on**: MAE = 0.1229 Hz （SW ONなし、常時運用）

### 2.2 軸別周波数特性（Always-on 常時推定）
![Per-Axis Breakdown](diagnostics/always_on_axis_breakdown.png)

**軸別の周波数分布:**
- **X軸**: ~0.45 Hz（安定、目標値）
- **Y軸**: ~0.77 Hz（高め）
- **Z軸**: ~0.35 Hz（下限制約）
- **統合値**: ~0.57 Hz（軸間の分散を反映）

### 2.3 運用シナリオ別の周波数遷移
![Scenario Transitions](diagnostics/scenario_transition_comparison.png)

**4つの運用モード比較（50-140秒区間）:**
- **Baseline（赤）**: SW ON時に不連続ジャンプ +0.134 Hz
- **Noreset Log（緑）**: 平坦で安定、ジャンプなし
- **Always-on（橙破線）**: SW OFFなし、0.57 Hz で定常
- **Best Gate（紫破線）**: Always-on + ゲート適用、若干低下

---

## 3. Always-on 周波数推定の詳細分析

### 3.1 常時推定モードの特性
![Always-on Time Series](diagnostics/always_on_integrated_frequency.png)

**観測:**
- 平均周波数: 0.57 Hz （±0.08 Hz 変動幅）
- 目標 0.45 Hz との乖離: +0.12 Hz (27%)
- 変動が大きい理由: 軸間の高周波化（Y/Z軸が高め）

### 3.2 軸ゲートパラメータスキャン結果
![Gate Scan Effects](diagnostics/section8_gate_scan_parameters.png)

**5パターンのゲート条件を試験:**

| amp_min | amp_max | innov_max | nis_max | MAE (Hz) |
|---------|---------|-----------|---------|----------|
| 0.08    | 1.20    | 0.80      | 6.0     | **0.1540** |
| 0.10    | 1.00    | 0.70      | 4.0     | 0.1582   |
| 0.12    | 0.90    | 0.60      | 3.5     | 0.1610   |

**結論**: Always-on では単純な閾値選別では noreset_log に及ばない

### 3.3 改善効果の定量化
![Improvement Analysis](diagnostics/section8_improvement_analysis.png)

- **noreset_log**: Baseline比 **-82% 改善** （ジャンプ除去）
- **Best Gate always-on**: Baseline比 -16% 改善 （限定的）
- **推奨**: noreset_log運用

---

## 4. 実装内容と検証結果

### 4.1 追加実装した機能
1. **SW ON時リセット有無の選択** （パラメータ `OBS_EKF_SW_RST`）
   - 0: リセットなし → noreset_log 相当、大幅改善
   - 1: 従来通り（デフォルト互換）

2. **軸別統合ゲート** （パラメータ `OBS_EKF_AX_GAT`）
   - innovationおよびNIS閾値による軸選別
   - 信頼軸のみで周波数融合

### 4.2 ジャンプの原因
- **72秒ジャンプ**: `reset_frequency_estimation()` による実装起因の不連続
- **両ログで確認**: 00000443 (SW ON @ 57s)、00000444 (SW ON @ 72.59s)

### 4.3 Off時の周波数動き
- SW = OFF でも測定更新により推定値が変動
- 運用意図（OFF時は保持）とのズレあり

---

## 5. 推奨事項

| 項目 | 推奨 | 理由 |
|------|------|------|
| **レアル運用** | `OBS_EKF_SW_RST=0` | noreset_log で MAE 0.0335Hz、大幅改善 |
| **Always-on** | 要追加検討 | 現状 MAE 0.1229Hz、軸間整合性が課題 |
| **ゲート機能** | 補助的 | Always-on 改善効果は限定的（-16%） |

---

## 6. 実装確認（調査時点）

## 7. 今回実装した内容（追加）

### 4.1 追加実装した機能
1. **SW ON時リセット有無の選択** （パラメータ `OBS_EKF_SW_RST`）
   - 0: リセットなし → noreset_log 相当、大幅改善
   - 1: 従来通り（デフォルト互換）

2. **軸別統合ゲート** （パラメータ `OBS_EKF_AX_GAT`）
   - innovationおよびNIS閾値による軸選別
   - 信頼軸のみで周波数融合

### 4.2 AP_Observer実装における軸別周波数推定
- X軸: 安定して0.45Hz付近で推定
- Y軸: ON後に0.77Hzへ高周波化
- Z軸: 下限制約付近(0.35Hz)で圧迫
- 統合値: 軸間の分散を反映

### 4.3 Replay実行器への検証オプション
新規`EKF_CSV_Replay`オプション:
- `--sw-mode log|always-on|always-off`: 運用モード選択
- `--ekf-reset-on-switch 0|1`: リセット有無
- `--ekf-axis-gate 0|1`: ゲート機能有無
- `--ekf-amp-min`, `--ekf-amp-max`, `--ekf-innov-max`, `--ekf-nis-max`: 閾値群

---

## 5. 残課題と提案

1. **Always-on精度改善** （MAE 0.1229Hz）
   - 軸間周波数整合性を加えた信頼度設計が必要
   - 単純な|d|選別では十分でない

2. **SW=OFF時omega完全固定** （要望があれば実装）
   - 現在: OFF中も測定更新で値が動く
   - 要改善: OFF時は前回値を保持

3. **ログ・可観測性向上**
   - 軸別innovation/NIS/trustedフラグを追加
   - 閾値調整の高速化に対応

---

## 6. 参考: 軸別周波数の物理的解釈

| 運用モード | X軸 | Y軸 | Z軸 | 統合 | 評価 |
|----------|-----|-----|-----|-----|------|
| ON前(baseline) | 0.45 | 0.59 | 0.35 | 0.46 | ジャンプ前 |
| ON後(baseline) | 0.46 | 0.77 | 0.67 | 0.63 | ジャンプ後 |
| noreset_log | ~0.45 | ~0.48 | ~0.48 | **0.48** | ✓ 推奨 |
| Always-on | ~0.45 | ~0.77 | ~0.35 | **0.57** | 軸散乱大 |

---

## まとめ
- **結論**: SW ON時リセット無効化（`OBS_EKF_SW_RST=0`）により、72秒ジャンプは完全除去
- **精度向上**: Log運用で MAE **0.0335Hz** を実現（目標0.45Hz対比 -93%）
- **残懸案**: Always-on運用では軸間整合性が問題、さらなる検討が必要
