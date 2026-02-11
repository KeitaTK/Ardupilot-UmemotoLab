# AP_Observer - RLS外乱推定ライブラリ 技術資料

**最終更新日**: 2026年2月11日（実装状況に合わせて更新）

---

## 目次

1. [概要](#1-概要)
2. [クイックスタート](#2-クイックスタート)
3. [システムアーキテクチャ](#3-システムアーキテクチャ)
4. [外力推定の基礎理論](#4-外力推定の基礎理論)
5. [RLS推定アルゴリズム](#5-rls推定アルゴリズム)
6. [パラメータ設定](#6-パラメータ設定)
7. [実装詳細](#7-実装詳細)
8. [ログとデバッグ](#8-ログとデバッグ)
9. [オートテスト](#9-オートテスト)
10. [トラブルシューティング](#10-トラブルシューティング)

---

## 1. 概要

AP_Observerは、ドローンに作用する外部からの周期的な外力（例: クレーン吊り下げペイロードの揺れ）をリアルタイムで推定し、機体の姿勢制御にフィードバック補償することで制振を行うライブラリです。

### 主な機能

1. **外力推定**: IMUの加速度とモータ推力から外乱ベクトルを算出
2. **RLS推定**: Recursive Least Squaresアルゴリズムにより、外乱を正弦波モデル ($A\sin(\omega t) + B\cos(\omega t) + C$) で同定
3. **予測制御**: 推定モデルを用いて数ミリ秒先（遅延補償分）の外力を予測
4. **姿勢補正**: 予測外力を打ち消すような姿勢角（ロール・ピッチ）補正量を生成

### 主な特徴

- **固定周波数推定**: 外乱周波数はパラメータ `OBS_DIST_FREQ` で設定（周波数推定機能は実装予定）
- **軽量実装**: 100 Hzで動作可能な計算量、スタック配列のみ使用
- **数値安定性**: 各種閾値・クランプにより安定した動作を保証
- **ログ記録**: SDカードに詳細なパラメータ推定値をリアルタイム記録

---

## 2. クイックスタート

### 基本的な使い方

1. パラメータ `OBS_DIST_FREQ` で外乱の周波数 [Hz] を設定
   - 典型例: ケーブル吊り下げペイロード → 0.6 Hz
   - 振り子周期: $f = \frac{1}{2\pi}\sqrt{\frac{g}{L}}$ （$L$: ケーブル長）

2. パラメータ `OBS_TEST_INJECT=1` を設定して既知信号で検証（SITL時）
   - テスト信号周波数: `OBS_TEST_FREQ` [Hz] 
   - テスト信号振幅: `OBS_TEST_AMP` [N]

3. 通常運用時は `OBS_TEST_INJECT=0` でIM U/推力から自動推定

### 調整のポイント

| 目的 | パラメータ | 調整方向 |
|------|-----------|---------|
| 収束を速める | `OBS_RLS_LAMBDA` | 小さくする（0.95等） |
| 収束を速める | `OBS_RLS_COV_INIT` | 大きくする（500等） |
| 予測精度向上 | `OBS_PRED_TIME` | 実際の制御遅延に合わせる |
| 補正を強める | `OBS_CORR_GAIN` | 大きくする（0.01等） |

---

## 3. システムアーキテクチャ

```
IMU (加速度) + Motors (推力)
       ↓
   外力計算: F = m·a - Thrust
       ↓
   RLS推定: F(t) = A·sin(ωt) + B·cos(ωt) + C
       ↓
   外力予測: F(t+Δt)
       ↓
   姿勢補正: Roll/Pitch Offset
       ↓
   AC_AttitudeControl
```

**特徴**:
- 各軸（X, Y, Z）独立に推定
- 周波数は固定値（オンライン調整なし）
- 予測時間 Δt で制御遅延を補償

---

## 4. 外力推定の基礎理論

### 4.1 外力の定義

ドローンに作用する外力 $\mathbf{F}_{\text{payload}}$ は、運動方程式から導かれます：

$$
\mathbf{F}_{\text{payload}} = m \mathbf{a} - \mathbf{F}_{\text{thrust}}
$$

ここで：
- $m = 1.4$ kg：ドローンの質量
- $\mathbf{a}$：IMUで計測される加速度ベクトル [m/s²]
- $\mathbf{F}_{\text{thrust}}$：モータの推力ベクトル [N]

### 4.2 推力の計算

モータスロットル値 $\theta$ (0.0~1.0の正規化値) から推力を計算：

$$
F_{\text{thrust}} = -(k_{\text{scale}} \cdot \theta + k_{\text{offset}}) \cdot g
$$

**実装の定数** ([AP_Observer.cpp](AP_Observer.cpp)):
```cpp
static constexpr float THRUST_SCALE = 6.3157f;    // k_scale
static constexpr float THRUST_OFFSET = -0.9995f;  // k_offset
static constexpr float g = 9.7985f;               // 重力加速度
static constexpr float UAV_mass = 1.4f;           // 機体質量
```

### 4.3 フィルタの扱い

**注意**: 現在の実装ではローパスフィルタは**無効化**されており、生データを直接使用しています。

実装コード ([AP_Observer.cpp](AP_Observer.cpp) line 326-329):
```cpp
// フィルタ適用（無効化）
// _payload_filtered = _payload_filter.apply(payload);
_payload_filtered = payload; // フィルタなしで生データを使用
```

**理由**: 
- RLSアルゴリズム自体が統計的ノイズ抑制機能を持つため、事前フィルタは不要
- フィルタによる位相遅れが推定精度に悪影響（周波数推定機能実装時に重要）
- 生データ使用により、予測制御の精度が向上

---

## 5. RLS推定アルゴリズム

### 5.1 周期外乱のモデル化

各軸 $i \in \{x, y, z\}$ の外力を以下の正弦波モデルで近似します：

$$
F_i(t) = A_i \sin(\omega t) + B_i \cos(\omega t) + C_i
$$

ここで：
- $A_i, B_i$：sin/cos項の係数（振幅と位相を表現）
- $C_i$：定常偏差（DC成分）
- $\omega = 2\pi f$：角周波数 [rad/s]
- $f$：外乱周波数 [Hz]（パラメータ $`OBS_DIST_FREQ`$ で設定）

**モデルの妥当性**:
- 吊り下げペイロードの振り子運動は単一周波数の正弦波で良好に近似可能
- 2係数 $A, B$ により任意位相の正弦波を表現: $R\sin(\omega t + \phi) = A\sin(\omega t) + B\cos(\omega t)$

### 5.2 RLS（再帰的最小二乗法）

時刻 $n$ における観測値 $y(n)$ に対し、パラメータベクトル $\boldsymbol{\theta}$ を逐次更新します。

**最小化問題** (忘却係数付き):
$$
\min_{\boldsymbol{\theta}} \sum_{k=1}^{n} \lambda^{n-k} |y(k) - \mathbf{x}^T(k) \boldsymbol{\theta}|^2
$$

- $\lambda$ (0.9 ~ 0.9999): 忘却係数。$\lambda$ が1に近いほど過去のデータを重視
- $\mathbf{x}(t)$: 回帰ベクトル $[sin(\omega t), \cos(\omega t), 1]^T$

#### 実装上の更新式 ([AP_Observer.cpp](AP_Observer.cpp) line 147-243)

**1. パラメータベクトル** (軸ごと):
$$
\boldsymbol{\theta}_i = \begin{bmatrix} A_i \\ B_i \\ C_i \end{bmatrix}
$$

**2. 回帰ベクトル**:
$$
\mathbf{x}(t) = \begin{bmatrix} \sin(\omega t) \\ \cos(\omega t) \\ 1 \end{bmatrix}
$$

**3. 予測値**:
$$
\hat{y}_i(n) = \mathbf{x}^T(n) \boldsymbol{\theta}_i(n-1)
$$

**4. 予測誤差**:
$$
e_i(n) = y_i(n) - \hat{y}_i(n)
$$

**5. ゲインベクトル**:
$$
\mathbf{K}_i(n) = \frac{\mathbf{P}_i(n-1) \mathbf{x}(n)}{\lambda + \mathbf{x}^T(n) \mathbf{P}_i(n-1) \mathbf{x}(n)}
$$

**6. パラメータ更新**:
$$
\boldsymbol{\theta}_i(n) = \boldsymbol{\theta}_i(n-1) + \mathbf{K}_i(n) e_i(n)
$$

**7. 共分散行列更新**:
$$
\mathbf{P}_i(n) = \frac{1}{\lambda} \left( \mathbf{P}_i(n-1) - \mathbf{K}_i(n) \mathbf{x}^T(n) \mathbf{P}_i(n-1) \right)
$$

### 5.3 初期化 ([AP_Observer.cpp](AP_Observer.cpp) line 115-133)

**パラメータ初期値**:
$$
\boldsymbol{\theta}_i(0) = \begin{bmatrix} 0 \\ 0 \\ 0 \end{bmatrix}
$$
RLSアルゴリズムは初期値に依存せず収束するため、ゼロ初期化で問題なし。

**共分散行列初期値** (対角行列):
$$
\mathbf{P}_i(0) = \begin{bmatrix} 
P_0 & 0 & 0 \\
0 & P_0 & 0 \\
0 & 0 & P_0
\end{bmatrix}, \quad P_0 = `OBS_RLS_COV_INIT` (デフォルト 100.0)
$$

初期共分散を大きめ（100.0）に設定することで、初期学習速度を速める。

### 5.4 数値安定性対策

**分母のゼロ除算チェック** ([AP_Observer.cpp](AP_Observer.cpp) line 199-206):
分母 $|\lambda + \mathbf{x}^T \mathbf{P} \mathbf{x}| < 10^{-12}$ の場合、その回の更新をスキップ。

**共分散行列のクランプ** ([AP_Observer.cpp](AP_Observer.cpp) line 216-220):
$$
P_{i,jk}(n) \in [0.001, 1000.0]
$$
- 下限 0.001: 過信を防止
- 上限 1000.0: 発散防止

### 5.5 参考値：時定数

忘却係数 $\lambda = 0.98$ の無効時定数：
$$
\tau_{\text{eff}} = \frac{1}{1 - \lambda} = 50 \text{ samples}
$$

100 Hz サンプリング時：$\tau = 0.5$ 秒

外乱周波数 0.6 Hz（周期 1.67 秒）に対して、半周期で適応可能。

---

## 6. パラメータ設定

### 6.1 パラメータテーブル

| パラメータ名 | 変数名 | デフォルト | 範囲 | 単位 | 説明 |
|----------|--------|----------|------|------|------|
| `OBS_CORR_GAIN` | `_correction_gain` | 0.004 | 0.0-1.0 | - | 姿勢補正ゲイン |
| `OBS_DIST_FREQ` | `_disturbance_freq` | 0.6 | 0.35-0.91 | Hz | 外乱の周波数（固定値） |
| `OBS_PRED_TIME` | `_prediction_time` | 0.01 | 0.0-0.5 | s | 予測時間（遅延補償） |
| `OBS_FILT_CUTOFF` | `_filter_cutoff_freq` | 20.0 | 1.0-100.0 | Hz | ローパスフィルタ（現在無効） |
| `OBS_RLS_LAMBDA` | `_rls_forgetting_factor` | 0.98 | 0.9-0.9999 | - | RLS忘却係数 |
| `OBS_RLS_COV_INIT` | `_rls_initial_covariance` | 100.0 | 0.001-1000 | - | RLS初期共分散 |
| `OBS_TEST_INJECT` | `_test_force_inject_enable` | 0 | 0/1 | - | テスト信号注入 |
| `OBS_TEST_FREQ` | `_test_force_freq` | 0.7 | 0.35-0.91 | Hz | テスト信号周波数 |
| `OBS_TEST_AMP` | `_test_force_amp` | 1.0 | 0.0-10.0 | N | テスト信号振幅 |
| `OBS_MAX_CORR_ANG` | `_max_correction_angle` | 0.5 | 0.0-1.0 | rad | 補正角度最大値 |

### 6.2 内部定数

| 定数名 | 値 | 説明 |
|--------|-----|------|
| `RLS_PARAM_SIZE` | 3 | RLSパラメータ数（A, B, C） |
| `RLS_NUM_AXES` | 3 | 軸数（x, y, z） |
| `RLS_MIN_LAMBDA` | 0.9 | 忘却係数最小値 |
| `RLS_MAX_LAMBDA` | 0.9999 | 忘却係数最大値 |
| `RLS_MIN_COVARIANCE` | 0.001 | 共分散最小値 |
| `RLS_MAX_COVARIANCE` | 1000.0 | 共分散最大値 |
| `FORCE_THRESHOLD` | 0.0 | 補正判定閾値（常に補正） |
| `TIMEOUT_MS` | 500 | 補正の有効期限 |

---

## 7. 実装詳細

### 7.1 予測外力の計算 ([AP_Observer.cpp](AP_Observer.cpp) line 410-433)

時刻 $t$ から $\Delta t$ 秒後の外力を予測：

$$
F_i(t + \Delta t) = A_i \sin(\omega(t + \Delta t)) + B_i \cos(\omega(t + \Delta t)) + C_i
$$

実装コード:
```cpp
Vector3f AP_Observer::get_predicted_force() const {
    if (!rls_initialized) {
        return _payload_filtered;
    }
    
    float t = (get_current_time_ms() - rls_start_time_ms) / 1000.0f;
    const float omega_t_dt = _omega_rad * (t + _prediction_time.get());
    float sin_omega_t_dt = sinf(omega_t_dt);
    float cos_omega_t_dt = cosf(omega_t_dt);
    
    Vector3f predicted;
    for (uint8_t axis = 0; axis < RLS_NUM_AXES; axis++) {
        float A = rls_theta[axis][0];
        float B = rls_theta[axis][1];
        float C = rls_theta[axis][2];
        float force = A * sin_omega_t_dt + B * cos_omega_t_dt + C;
        // ... assign to predicted.x/y/z
    }
    return predicted;
}
```

### 7.2 姿勢補正の計算 ([AP_Observer.cpp](AP_Observer.cpp) line 375-408)

**補正角の計算** (オイラー角形式):

$$
\text{Roll}_{\text{corr}} = \frac{F_y \cdot k_{\text{corr}}}{m}, \quad \text{Pitch}_{\text{corr}} = -\frac{F_x \cdot k_{\text{corr}}}{m}
$$

実装:
```cpp
Vector3f AP_Observer::calculate_correction_euler_from_force(const Vector3f& force) const {
    float mag = force.length();
    if (mag < FORCE_THRESHOLD) {
        return Vector3f(0, 0, 0);
    }
    
    float correction_gain = _correction_gain.get();
    float roll  =  force.y * correction_gain / UAV_mass;
    float pitch = -force.x * correction_gain / UAV_mass;
    
    float max_angle = _max_correction_angle.get();
    roll = constrain_value(roll, -max_angle, max_angle);
    pitch = constrain_value(pitch, -max_angle, max_angle);
    
    return Vector3f(roll, pitch, 0.0f);  // ヨーは常に0
}
```

**重要**:
- X軸外力 → ピッチ補正（負号あり）
- Y軸外力 → ロール補正
- **ヨー角は常に0**（オペレーターの方位指令を保持）

### 7.3 更新タイミング ([AP_Observer.cpp](AP_Observer.cpp))

- **RLS更新**: 毎ループ (100 Hz想定) - `update()` 内で実施 [line 334]
- **キャッシュ更新**: パラメータ変更検出時 [line 347-352]
- **ログ記録**: 毎ループ (100 Hz) - `Write_Observer_Log()` [line 454-475]

### 7.4 離陸検知 ([AP_Observer.cpp](AP_Observer.cpp) line 450-454)

```cpp
bool AP_Observer::is_taking_off() {
    AP_Motors* motors = AP::motors();
    if (!motors) {
        return false;
    }
    return motors->armed();  // モータアーム = 離陸とみなす
}
```

RLS更新は **離陸後のみ** 実施 [line 339-341]

---

## 8. ログとデバッグ

### 8.1 SDカードログ形式

**ログタグ**: `OBSV`

**記録頻度**: 毎ループ (100 Hz)

**実装** ([AP_Observer.cpp](AP_Observer.cpp) line 454-475):
```cpp
void AP_Observer::Write_Observer_Log() {
#if HAL_LOGGING_ENABLED
    logger->Write("OBSV", "TimeUS,PLX,PLY,PLZ,AX,AY,BX,BY,CX,CY",
                  "s---------", "F---------",
                  "Qfffffffff",
                  AP_HAL::micros64(),
                  _payload_filtered.x,
                  _payload_filtered.y,
                  _payload_filtered.z,
                  rls_theta[0][0],      // sin係数 X軸
                  rls_theta[1][0],      // sin係数 Y軸
                  rls_theta[0][1],      // cos係数 X軸
                  rls_theta[1][1],      // cos係数 Y軸
                  rls_theta[0][2],      // 定常偏差 X軸
                  rls_theta[1][2]);     // 定常偏差 Y軸
#endif
}
```

### 8.2 ログフィールド一覧

| フィールド | 単位 | 説明 |
|-----------|------|------|
| `TimeUS` | μs | タイムスタンプ |
| `PLX`, `PLY`, `PLZ` | N | 計算された外力（フィルタなし） |
| `AX`, `AY` | - | RLS推定値 sin係数 (X, Y軸) |
| `BX`, `BY` | - | RLS推定値 cos係数 (X, Y軸) |
| `CX`, `CY` | N | RLS推定値 定常偏差 (X, Y軸) |

### 8.3 デバッグ出力 ([AP_Observer.cpp](AP_Observer.cpp) line 225-238)

**RLS更新時の出力** (100回に1回):
- 時間経過、角周波数、sin/cos値
- 観測値、予測値、予測誤差
- 推定パラメータ A, B, C

現在はコメントアウト（本番運用用）。

---

## 9. オートテスト

以下のSILTテストで動作検証可能です。

```bash
cd /home/memoto/Ardupilot-UmemotoLab

# ビルド
./waf -j$(nproc) copter

# テスト実行
timeout 600 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.TestRLSBasicEstimation
timeout 600 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.ArmFeatures
```

### テスト内容

**TestRLSBasicEstimation**:
- 既知外力（通常 10 N, 0.6 Hz）を注入
- RLSパラメータが収束することを確認
- 推定振幅が注入値の 50% 以上であれば合格

---

## 10. トラブルシューティング

### RLS推定値が安定しない

**確認事項**:
- 外乱の振幅が十分にあるか確認（`OBSV.PLX`, `OBSV.PLY` > 1.0 N を目安）
- ノイズが多い場合、`OBS_RLS_LAMBDA` を大きく（0.99等）して平滑化

### 姿勢補正が効かない

**確認事項**:
- `OBS_CORR_GAIN` が小さすぎないか（デフォルト 0.004 から 0.01 に増加してみる）
- 予測外力 `get_predicted_force()` が計算されているか確認

### ログに記録されない

**確認事項**:
- `LOG_BITMASK` で適切なログレベルが設定されているか
- SDカード容量が十分にあるか
- `HAL_LOGGING_ENABLED` が有効か（通常は有効）

### パラメータが反映されない

**確認事項**:
- 飛行中にパラメータ変更は反映されません
- 再起動後に有効になります
- GCSで `OBS_*` パラメータ確認

---

## 今後の拡張計画（実装予定）

- ✅ 固定周波数RLS推定
- ✅ 予測制御と遅延補償
- ⏳ **周波数推定と自動追従** (位相バッファ、線形回帰による周波数更新)
- ⏳ RCスイッチによる周波数推定ON/OFF制御
- ⏳ 複数周波数対応
- ⏳ FFT/AR モデルによる周波数自動検出

---

## 参考文献

- Ljung, L. (1999). *System Identification: Theory for the User*. Prentice Hall.
- Åström, K. J., & Wittenmark, B. (2013). *Adaptive Control* (2nd ed.). Dover Publications.
- Haykin, S. (2002). *Adaptive Filter Theory* (4th ed.). Prentice Hall.

---

**License**: GPLv3  
**Maintainer**: Umemoto Lab  
**最終更新**: 2026年2月11日
