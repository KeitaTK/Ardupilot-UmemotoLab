# 複数軸周波数推定の統合方法に関する詳細分析と提案

**日付:** 2026-04-15  
**対象:** AP_Observer内部のX/Y軸周波数推定統合  
**背景:** 振り子運動はX/Y両軸で同じ周波数のため、推定結果を統合して使いたい

---

## 1. 現状確認

### 1.1 現在の実装

AP_Observer.cpp（L347-365）では既に**単純平均統合**が実装されています：

```cpp
float omega_sum = 0.0f;
uint8_t trusted_count = 0;
for (uint8_t axis = 0; axis < EKF_NUM_AXES; axis++) {
    if (!is_axis_enabled_in_fusion(axis)) continue;
    
    const float omega_axis = constrain_value(ekf_state[axis][3], 
                                             _ekf_omega_min, _ekf_omega_max);
    ekf_axis_amp[axis] = fabsf(ekf_state[axis][0]);
    
    const bool trusted = is_axis_frequency_trusted(axis);
    ekf_axis_trusted[axis] = trusted ? 1U : 0U;
    
    if (trusted) {
        omega_sum += omega_axis;
        trusted_count++;
    }
}

if (trusted_count > 0U) {
    estimated_frequency = (omega_sum / trusted_count) / (2.0f * M_PI);
} else {
    estimated_frequency = _freq_estimation_result;  // ホールド
}
```

**特徴:**
- 信頼度フラグ `ekf_axis_trusted[axis]` でフィルタリング（バイナリ判定）
- 信頼できる軸のみの単純平均
- Z軸も含まれる（ただし通常はX/Yのみが信頼される）

### 1.2 信頼度判定ロジック

`is_axis_frequency_trusted(axis)` 関数で以下をチェック：

```
✓ innovation_abs = |measurement - predicted| <= EKF_INNOV_MAX
✓ NIS = (innovation²) / S <= NIS_MAX
✓ エネルギーゲートが有効（RMS > RMS_ON）
✓ 力振幅が範囲内（force_hold_max ≤ |f| < force_reject_min）
✓ 軸マスク有効（EKF_AXIS_MASK ビット確認）
```

**現状の問題:**
- `ekf_axis_trusted` は **バイナリ（0 or 1）** なので、「微妙に信頼度が低い」軸も 0 で切り落とされる
- 複数軸が同等に「未信頼」の場合、推定値がホールドされて推定精度が低下

### 1.3 利用可能な信頼度指標

現在計算されているが、統合に使われていない：
- `ekf_axis_innovation[axis]` - 生イノベーション値 [N]
- `ekf_axis_nis[axis]` - 正規化イノベーション二乗
- `ekf_axis_energy_power[axis]` - エネルギー推定値
- 予測共分散 `P[3][3]` - omega推定の不確実性（現在未ログ）

---

## 2. 統合アルゴリズムの比較分析

### 方法①：現在の実装 - バイナリ信頼度フラグ + 単純平均

**式:**
$$\hat{\omega} = \frac{1}{N_{\text{trusted}}} \sum_{i \in \text{trusted}} \omega_i$$

**メリット:**
- ✅ 実装済み・実証済み
- ✅ 計算が軽い
- ✅ 外れ値を完全に排除

**デメリット:**
- ❌ 信頼度がグラデーションでなくバイナリ
- ❌ 信頼度が僅かに足りない軸の情報を完全に無視
- ❌ 全軸が「未信頼」の場合、前フレーム値をホールド（推定が止まる）

**推奨用途:**
- 外れ値が明確に分離している場合
- 軸数が十分多い（≥5軸）場合
- リアルタイム性重視

---

### 方法②：NIS加重平均 - イノベーション正規化に基づく重み付け

**背景（EKF理論）:**
- NIS（正規化イノベーション二乗）は $\chi^2$ 分布に従う
- NISが低い → 測定値が予測に一致 → 信頼度高
- NISが高い → 外れ値の可能性 → 信頼度低

**式:**
$$w_i = \max(0, 1 - \frac{\text{NIS}_i}{\text{NIS}_{\max}})$$
$$\hat{\omega} = \frac{\sum_i w_i \cdot \omega_i}{\sum_i w_i}$$

**具体例（NIS_MAX=4.0）:**
| 軸 | NIS | 重み | omega |
|----|-----|------|-------|
| X  | 1.5 | 0.625 | 3.7 rad/s |
| Y  | 3.2 | 0.200 | 3.6 rad/s |
| Z  | 5.0 | 0.000 | 3.5 rad/s |
| **結果** | **-** | **-** | **3.68 rad/s** |

**メリット:**
- ✅ 信頼度がグラデーション（連続値）
- ✅ 微妙に信頼度が低い軸も活用
- ✅ 全軸未信頼の場合も「最も信頼度が高い軸」の値を返す
- ✅ EKF理論に根拠がある（統計的な妥当性）

**デメリット:**
- ❌ 外れ値に対していくらか影響を受ける（0には完全に落ちない）
- ❌ パラメータ調整が必要（NIS_MAX閾値の設定）

**推奨用途:**
- **現在の要件に合致！** X/Yが両方信頼度高い振り子の場合
- ノイズが穏やかで外れ値が少ない環境

---

### 方法③：確率加重平均 - 予測共分散ベース

**背景（カルマンフィルタ理論）:**
- 各軸の pushupapproximation confidence = `1 / P[3][3]`（omega推定の逆分散）
- 分散が小さい軸 → 推定が確定的 → 信頼度高

**式:**
$$w_i = \frac{1/P_i^2}{\sum_j 1/P_j^2}$$
$$\hat{\omega} = \sum_i w_i \cdot \omega_i$$

**メリット:**
- ✅ カルマンフィルタの統計的枠組みで正当性強い
- ✅ 推定不確実性を直接反映
- ✅ 外れ値（NISが高い）と自然に結びつく

**デメリット:**
- ❌ `ekf_P[axis][3][3]` を現在ログしていない
- ❌ 実装コスト（P行列へのアクセス必要）
- ❌ P行列が数値不安定な場合がある

**推奨用途:**
- EKFの内部状態をフル活用したい場合
- 学術的な厳密性が重要な場合

---

### 方法④：イノベーション加重平均 - 測定残差ベース

**背景:**
- イノベーション（測定値と予測値の差）が小さい → 測定値が信頼できる可能性高
- イノベーションの分布：$\mathcal{N}(0, S)$（S = イノベーション共分散）

**式:**
$$w_i = \max(0, 1 - \frac{|\text{innov}_i|}{\text{INNOV}_{\max}})^2$$
$$\hat{\omega} = \frac{\sum_i w_i \cdot \omega_i}{\sum_i w_i}$$

**メリット:**
- ✅ 実装簡単（既に `ekf_axis_innovation` を計算）
- ✅ 観測値の矛盾度を直接反映
- ✅ リアルタイム環境で高速

**デメリット:**
- ❌ NISよりも統計的根拠が弱い（分散情報を無視）
- ❌ ノイズが大きい測定システムでは不安定

**推奨用途:**
- 計算リソースが限定的な環境
- イノベーション閾値が既に十分に調整されている

---

### 方法⑤：Kalmanフィルタベース統合 - 複数モデル融合

**背景:**
各軸をセンサと見立て、さらに上位のカルマンフィルタで統合

**構造:**
```
[EKF軸X] ──ω_X──┐
[EKF軸Y] ──ω_Y──┤  [融合EKF]  ──→  ω_fused
[EKF軸Z] ──ω_Z──┘
        + 信頼度
```

**式:**
```
測定値（複数軸のω）をベクトル観測として扱う
z = [1, 1, 1] · ω + v  （v：測定ノイズ）
カルマンゲイン Kに基づいて各軸の寄与度を決定
```

**メリット:**
- ✅ 最も統計的に厳密
- ✅ 複数軸の相関を活用可能
- ✅ 時間変動する信頼度が自然に処理される

**デメリット:**
- ❌ 実装が複雑（追加のEKFインスタンス必要）
- ❌ パラメータが増える（測定ノイズRなど）
- ❌ 計算量増加
- ❌ 現在の「各軸独立」設計に大規模な改修必要

**推奨用途:**
- 長期プロジェクトで完全な推定最適化を目指す場合
- センサ数が5軸以上ある場合

---

## 3. 推奨実装戦略

### 段階① - 短期（即座に実装可能）
**推奨：方法② - NIS加重平均**

理由：
1. 利用可能な指標（`ekf_axis_nis[axis]`）を活用
2. 既存の値判定ロジックを拡張するだけ
3. 統計的な妥当性がある
4. X/Yが同振幅の振り子運動に適している

実装例：
```cpp
// 現在の単純平均（L347-365）を以下に変更
float omega_sum = 0.0f;
float weight_sum = 0.0f;
for (uint8_t axis = 0; axis < EKF_NUM_AXES; axis++) {
    if (!is_axis_enabled_in_fusion(axis)) continue;
    
    const float omega_axis = constrain_value(ekf_state[axis][3], ...);
    
    // NIS加重計算
    const float nis = ekf_axis_nis[axis];
    const float nis_max = MAX(1.0e-3f, _ekf_nis_max.get());
    const float weight = MAX(0.0f, 1.0f - (nis / nis_max));  // NIS>NIS_MAX なら weight=0
    
    omega_sum += weight * omega_axis;
    weight_sum += weight;
    
    ekf_axis_trusted[axis] = (weight > 0.5f) ? 1U : 0U;  // ログ用フラグ
}

if (weight_sum > 1.0e-6f) {
    estimated_frequency = (omega_sum / weight_sum) / (2.0f * M_PI);
} else {
    estimated_frequency = _freq_estimation_result;  // ホールド
}
```

**コスト:** 10-15行追加  
**リスク:** 低（既存値のみ使用）  
**テスト:** リプレイで収束改善を確認可能

---

### 段階② - 中期（1-2ヶ月）
**推奨：方法②の拡張 - 複合加重**

両方使用：
```
w_i = w_nis(i) × w_innov(i) × w_energy(i)
```

より柔軟に信頼度を反映：
```cpp
const float w_nis = MAX(0.0f, 1.0f - nis / nis_max);
const float innov_abs = fabsf(ekf_axis_innovation[axis]);
const float innov_max = MAX(1.0e-3f, _ekf_innov_max.get());
const float w_innov = MAX(0.0f, 1.0f - innov_abs / innov_max);
const float w_energy = ekf_axis_energy_trusted[axis] ? 1.0f : 0.5f;

weight[axis] = w_nis * w_innov * w_energy;
```

**メリット:** より複合的な信頼度評価  
**テスト:** ノイズが強い環境で検証

---

### 段階③ - 長期（3-6ヶ月）
**検討：方法⑤ - Kalmanフィルタベース統合**

完全な推定最適化を目指す場合：
- `ekf_state[axis][3]` をセンサ観測と見立てる
- 共分散情報をフル活用
- X/Y/Z間の相関構造を破壊しない独立性を維持

**推奨：まずは段階①②で効果検証してから検討**

---

## 4. リプレイでの検証方法

### 4.1 メトリクス追加（plot_replay_results.py）

リプレイは replay 専用の比較に限定する。実機飛行の前半レポートでは PRX/PRY を使わず、OBSV の実測列 `PLX/PLY` と EKF 状態 `DX/DY`、周波数 `F/FX/FY` を分離して扱う。

前半の軸対応は以下に固定する。
- `PLX` / `PLY`: EKF に入る前の実機外力入力
- `DX` / `DY`: EKF 内部の force state
- `F`: 融合周波数
- `FX` / `FY`: 軸別周波数

replay では必要に応じて `PRX/PRY` を使うが、これは再構成値であり実機 OBSV の force state ではない。

```python
# 複数軸のFrequencyデータを統合評価
freq_x = df['EstFreq_X_Hz']  # X軸周波数
freq_y = df['EstFreq_Y_Hz']  # Y軸周波数
freq_fused = df['EstFreq_Hz']  # 統合結果

metrics = {
    'freq_x_mae': MAE(freq_x - target_hz),
    'freq_y_mae': MAE(freq_y - target_hz),
    'freq_fused_mae': MAE(freq_fused - target_hz),
    'freq_x_std': np.std(freq_x),
    'freq_y_std': np.std(freq_y),
    'freq_fused_std': np.std(freq_fused),
    'freq_correlation_xy': np.corrcoef(freq_x, freq_y),
}
```

### 4.2 内部ログ追加（AP_Observer::log）

```cpp
// OBSV ログに以下を追加
// PLX/PLY                          - EKF に入る前の実機外力入力
// DX/DY                            - EKF の force state
// F                                - 融合周波数
// FX/FY                            - 軸別周波数
// NOTE: これらは前半の実機レポートで使用し、PRX/PRY は replay 専用にする。
```

### 4.3 比較実験

同じリプレイデータに対して：
1. 現在（単純平均）
2. NIS加重平均
3. 複合加重（段階②）

をそれぞれ実行し、メトリクスで比較

**期待される改善：**
- MAE（平均絶対誤差）低下 5-15%
- STD（安定性）向上 10-20%

---

## 5. 制度上の注意点

### 5.1 振り子理論の再確認

「X軸とY軸は同じ周波数」という仮定が本当に成立するか：
- ✓ 理想的な球形ロータ → 同一
- ✗ アンバランス質量がある → 周波数分離の可能性
- ✗ 機体フレームに非等方性がある → 周波数分離の可能性

**推奨:** リプレイデータで freq_x と freq_y の乖離度を確認すること

```python
# correlation
corr = np.corrcoef(df['EstFreq_X'], df['EstFreq_Y'])[0, 1]
# もし corr < 0.95 であれば、統合の仮定を再検討
```

### 5.2 Z軸の扱い

現実装では Z軸も含まれる。Z軸と XY の周波数が異なる場合：
- Z軸の重みを落とす可能性がある
- Z軸を完全に除外する（`_ekf_axis_mask` で制御）

**推奨:** XY統合は明示的にX/Y軸のみに限定

```cpp
// 周波数統合
for (uint8_t axis = 0; axis < 2; axis++) {  // Z軸(2)を除外
    ...
}
```

---

## 6. 決定マトリックス

| 方法 | 実装難度 | 計算量 | 統計根拠 | 外れ値耐性 | 推奨度 |
|------|--------|-------|--------|----------|-------|
| ① 単純平均 | ⭐ | ⭐ | ⭐ | ⭐⭐⭐ | ✓ (現状) |
| ② NIS加重 | ⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ | **🔴 推奨** |
| ③ 共分散加重 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | 🟡 長期 |
| ④ イノベーション加重 | ⭐⭐ | ⭐ | ⭐⭐ | ⭐ | 🟢 簡単 |
| ⑤ Kalman融合 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 🟡 視野に |

---

## 7. 次のステップ

1. **段階①実装**（1-2日）
   - [x] 分析完了
   - [ ] コード実装（AP_Observer.cpp L347-365）
   - [ ] テスト（リプレイ）
   - [ ] ドキュメント更新

2. **段階②検討**（リプレイ結果を見てから）
   - 改善効果が有意ならば複合加重へ
   - 改善がないなら他方法検討

3. **段階③視野に**（EKF全体改修時の将来検討）
   - `ekf_P[axis][3][3]` アクセスのコスト検討
   - Kalmanベース統合の必要性評価

---

## 参考資料

### EKF理論
- Welch, G., & Bishop, G. (2006). "An Introduction to the Kalman Filter"
- 正規化イノベーション (NIS) 分布：$\chi^2(1)$ 分布

### 複数センサ融合
- Bar-Shalom, Y., Li, X.-R., & Kirubarajan, T. (2001). "Estimation with Applications to Tracking and Navigation"
- Distributed/Decentralized Kalman Filtering: センサが複数で独立した場合の融合法

### 本プロジェクト関連
- [libraries/AP_Observer/README.md](../libraries/AP_Observer/README.md) - EKF詳細実装
- [.github/AUTOTEST_SPECIFICATION.md](.github/AUTOTEST_SPECIFICATION.md) - テスト仕様
- [analysis/replay/](analysis/replay/) - リプレイ検証スクリプト

