# AP_Observer - RLS外乱推定と周波数追従システム 技術資料

**最終更新日**: 2026年1月29日 (パラメータ値更新: FREQ_ALPHA=0.15, PHASE_THRESH=0.0)

---


# AP_Observer - RLS外乱推定ライブラリ 技術資料

**最終更新日**: 2026年2月8日

---

## 目次

1. [概要](#1-概要)
2. [クイックスタート](#2-クイックスタート)
3. [システムアーキテクチャ](#3-システムアーキテクチャ)
4. [外力推定の基礎理論](#4-外力推定の基礎理論)
5. [RLS推定アルゴリズム](#5-rls推定アルゴリズム)
6. [パラメータ設定](#6-パラメータ設定)
7. [ログ仕様](#7-ログ仕様)
8. [オートテスト](#8-オートテスト)
9. [トラブルシューティング](#9-トラブルシューティング)

---

## 1. 概要

AP_Observerは、ドローンに作用する外部からの周期的な外力（例: クレーン吊り下げペイロードの揺れ）をリアルタイムで推定し、機体の姿勢制御にフィードバック補償することで制振を行うライブラリです。

### 主な機能
1.  **外力推定**: IMUの加速度とモータ推力から外乱ベクトルを算出
2.  **RLS推定**: Recursive Least Squaresアルゴリズムにより、外乱を正弦波モデル ($A\sin(\omega t) + B\cos(\omega t) + C$) で同定
3.  **予測制御**: 推定モデルを用いて数ミリ秒先（遅延補償分）の外力を予測
4.  **姿勢補正**: 予測外力を打ち消すような姿勢角（ロール・ピッチ）補正量を生成

---

## 2. クイックスタート

1. パラメータ `OBS_DIST_FREQ` で外乱周波数 [Hz] を設定
2. パラメータ `OBS_TEST_INJECT=1` で既知外力注入テストが可能
3. 通常運用時は `OBS_TEST_INJECT=0` でIMU/推力から外力推定

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
```

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

---

## 5. RLS推定アルゴリズム

外力 $F(t)$ を $A\sin(\omega t) + B\cos(\omega t) + C$ の形でRLS（再帰的最小二乗法）により推定します。

- 各軸（X, Y, Z）ごとに独立に推定
- パラメータ: $A$（sin係数）, $B$（cos係数）, $C$（定常偏差）
- 周波数 $\omega$ は `OBS_DIST_FREQ` で固定

---

## 6. パラメータ設定

| パラメータ         | 説明                                 | 既定値   |
|--------------------|--------------------------------------|----------|
| OBS_DIST_FREQ      | 推定する外乱の周波数 [Hz]            | 0.6      |
| OBS_TEST_INJECT    | 既知外力注入テスト (0:無効, 1:有効)  | 0        |
| OBS_TEST_FREQ      | テスト注入外力の周波数 [Hz]           | 0.7      |
| OBS_TEST_AMP       | テスト注入外力の振幅 [N]              | 1.0      |
| RLS_LAMBDA         | RLS忘却係数 (0.9-0.9999)              | 0.98     |
| RLS_COV_INIT       | RLS初期共分散                        | 100.0    |
| FILT_CUTOFF        | ローパスフィルタカットオフ [Hz]        | 20.0     |
| PRED_TIME          | 予測時間 [s]                          | 0.01     |
| MAX_CORR_ANG       | 姿勢補正の最大角 [rad]                | 0.5      |

---

## 7. ログ仕様

DataFlashログに `OBSV` メッセージとして記録されます。

| フィールド名 | 内容                  |
|--------------|-----------------------|
| TimeUS       | タイムスタンプ [us]   |
| PLX, PLY, PLZ| 推定外力 [N] (各軸)   |
| AX, AY       | RLS sin係数 (X, Y)    |
| BX, BY       | RLS cos係数 (X, Y)    |
| CX, CY       | RLS定常偏差 (X, Y)    |

---

## 8. オートテスト

`Tools/autotest/arducopter.py` の `TestRLSBasicEstimation` で自動検証されます。
- テスト内容: 既知外力（10N, 0.6Hz）を注入し、RLSが正しく推定できるかをログから判定
- 合格基準: 推定振幅が注入値の50%以上であれば合格

---

## 9. トラブルシューティング

- ログ構造エラー: DataFlashログのフィールド数・型が実装と一致しているか確認
- RLS推定値が0: 離陸検知・パラメータ反映・推力計算の不具合を確認

**補足**: 外力推定において、X軸方向の外力はピッチ角の補正に、Y軸方向の外力はロール角の補正にそれぞれ対応します。座標系の符号は、慣性座標系（NED: North-East-Down）と機体固定座標系（Body Frame）の変換規則に従っています。

### 4.4 フィルタの扱い

**注意**: 現在の実装ではローパスフィルタは無効化されており、生データを直接使用しています。

実装コード ([AP_Observer.cpp](AP_Observer.cpp) 267-275行目):
```cpp
Vector3f payload;
payload.x = UAV_mass * accel.x;
payload.y = UAV_mass * accel.y;
payload.z = UAV_mass * accel.z - thrust;

// フィルタ適用（無効化）
// _payload_filtered = _payload_filter.apply(payload);
_payload_filtered = payload; // フィルタなしで生データを使用
```

**理由**: RLSアルゴリズム自体が統計的なノイズ抑制機能を持つため、事前のローパスフィルタは不要と判断されました。また、フィルタによる位相遅れが周波数推定精度に悪影響を与える可能性があるため、生データをそのまま使用しています。

---

## 5. RLS推定アルゴリズム

### 5.1 周期外乱のモデル化

各軸 $i \in \{x, y, z\}$ の外力を以下の正弦波モデルで近似します：

$$
F_i(t) = A_i \sin(\omega t - \phi_{\text{corr}}) + B_i \cos(\omega t - \phi_{\text{corr}}) + C_i
$$

- $A_i, B_i$：sin/cos項の係数（振幅と位相を表現）
- $C_i$：定常偏差（DC成分、重力や機体姿勢の微小なオフセット）
- $\omega = 2\pi f$：推定中の角周波数 [rad/s]
- $f$：外乱周波数 [Hz]（初期値は `OBS_DIST_FREQ` パラメータ）
- $\phi_{\text{corr}}$：位相補正項（全軸共通、オンライン調整される）

この正弦波モデルは、吊り下げペイロードの振り子運動を単一周波数の正弦波で近似したものです。実際の振動は非線形性や減衰を含みますが、主要な周波数成分を捉えるにはこのモデルで十分な精度が得られます。$A$ と $B$ の2つの係数を用いることで、任意の位相の正弦波を表現できます（$R\sin(\omega t + \phi) = A\sin(\omega t) + B\cos(\omega t)$ の関係）。

### 5.2 RLS更新則

時刻 $n$ における観測値 $y(n)$ に対し、パラメータベクトル $\boldsymbol{\theta}$ を逐次更新します。

**最小化問題**:
$$
\min_{\boldsymbol{\theta}} \sum_{k=1}^{n} \lambda^{n-k} |y(k) - \mathbf{x}^T(k) \boldsymbol{\theta}|^2
$$

ここで $\lambda$ は忘却係数（0 < $\lambda$ ≤ 1）で、過去のデータの重みを指数的に減衰させます。$\lambda$ = 1の場合は通常の最小二乗法、$\lambda$ < 1の場合は過去のデータよりも新しいデータを重視します。

#### パラメータベクトル

軸ごとに推定するパラメータ：

$$
\boldsymbol{\theta}_i = \begin{bmatrix} A_i \\ B_i \\ C_i \end{bmatrix}
$$

#### 回帰ベクトル

時刻 $t$ における入力ベクトル：

$$
\mathbf{x}(t) = \begin{bmatrix} \sin(\omega t - \phi_{\text{corr}}) \\ \cos(\omega t - \phi_{\text{corr}}) \\ 1 \end{bmatrix}
$$

#### 実装上の更新式

**1. 予測値の計算**

$$
\hat{y}_i(n) = \mathbf{x}^T(n) \boldsymbol{\theta}_i(n-1)
$$

現在のパラメータ推定値を使って、観測値を予測します。

**2. 予測誤差**

$$
e_i(n) = y_i(n) - \hat{y}_i(n)
$$

観測値と予測値の差分を計算します。この誤差が大きいほど、パラメータの更新幅も大きくなります。

**3. ゲインベクトルの計算**

$$
\mathbf{K}_i(n) = \frac{\mathbf{P}_i(n-1) \mathbf{x}(n)}{\lambda + \mathbf{x}^T(n) \mathbf{P}_i(n-1) \mathbf{x}(n)}
$$

ここで：
- $\mathbf{P}_i$：共分散行列 ($3 \times 3$)。パラメータ推定の不確実性を表します。
- $\lambda$：忘却係数（過去のデータの重み）

ゲインベクトル $\mathbf{K}$ は、カルマンフィルタのカルマンゲインに相当し、誤差をどの程度パラメータ更新に反映させるかを決定します。

**4. パラメータ更新**

$$
\boldsymbol{\theta}_i(n) = \boldsymbol{\theta}_i(n-1) + \mathbf{K}_i(n) e_i(n)
$$

**5. 共分散行列更新**

$$
\mathbf{P}_i(n) = \frac{1}{\lambda} \left( \mathbf{P}_i(n-1) - \mathbf{K}_i(n) \mathbf{x}^T(n) \mathbf{P}_i(n-1) \right)
$$

共分散行列は、パラメータ推定の信頼度を表します。観測データが蓄積されるにつれて、$\mathbf{P}$ の値は小さくなり（不確実性が減少）、推定値が安定します。

### 5.3 初期化

**パラメータ初期値** ([AP_Observer.cpp](AP_Observer.cpp) 94-98行目):

$$
\boldsymbol{\theta}_i(0) = \begin{bmatrix} 0 \\ 0 \\ 0 \end{bmatrix}
$$

すべての係数をゼロで初期化します。RLSアルゴリズムは初期値に依存せず収束するため、特別な初期推定は不要です。

**共分散行列初期値** ([AP_Observer.cpp](AP_Observer.cpp) 104-112行目):

$$
\mathbf{P}_i(0) = \begin{bmatrix} 
P_0 & 0 & 0 \\
0 & P_0 & 0 \\
0 & 0 & P_0
\end{bmatrix}
$$

ここで $P_0$ は初期共分散値（パラメータ `OBS_RLS_COV_INIT`）。大きな値（例: 100.0）を設定することで、初期の不確実性が高いことを示し、初期の学習速度を速めます。

### 5.4 数値安定性の保証

RLSアルゴリズムは逐次計算を行うため、数値誤差の蓄積や異常値への対策が必要です。

**分母のゼロ除算チェック** ([AP_Observer.cpp](AP_Observer.cpp) 199-203行目):

$$
\text{if } \left| \lambda + \mathbf{x}^T \mathbf{P} \mathbf{x} \right| < 10^{-12}, \quad \text{skip update}
$$

分母が極めて小さい場合、数値的に不安定になるため、その回の更新をスキップします。

**共分散行列の範囲制限** ([AP_Observer.cpp](AP_Observer.cpp) 216-219行目):

$$
P_{i,jk}(n) \in [P_{\min}, P_{\max}]
$$

ここで：
- $P_{\min} = 0.001$（下限：推定値が過信されすぎることを防ぐ）
- $P_{\max} = 1000.0$（上限：発散を防ぐ）

共分散行列の各要素を上下限でクランプすることで、数値的な発散や縮退を防ぎます。

---

## 6. 周波数推定と位相補正


本システムの中核となる、外乱周波数の自動追従と位相ズレの解消ロジックについて解説します。この処理は **phase_correction_update()** 関数内で行われます。

### 6.1 位相の時間発展と周波数誤差

設定周波数 $f_{\text{set}}$ に基づく理論的な位相：

$$
\phi_{\text{theory}}(t) = \omega_{\text{set}} t = 2\pi f_{\text{set}} t
$$

実際の外乱周波数 $f_{\text{actual}}$ が設定値と異なる場合、時間とともに位相誤差が蓄積します：

$$
\phi_{\text{error}}(t) = 2\pi (f_{\text{actual}} - f_{\text{set}}) t
$$

この位相誤差が蓄積すると、RLS推定で得られる係数 $A, B$ の位相成分が徐々にズレていき、予測精度が低下します。本システムは、この位相ズレを検出して周波数を自動調整することで、真の外乱周波数に追従します。

### 6.2 位相バッファの目的

RLS係数 $A, B$ から、現在の観測信号の「相対的な位相」を計算できます：

$$ \phi_{\text{obs}} = \operatorname{atan2}(B, A) $$

これは、モデル基準信号 $\sin(\omega t)$ に対する進み/遅れを表します。理想的には、周波数が一致していれば $\phi_{\text{obs}}$ は一定値になりますが、周波数誤差があると時間とともに変化します。

バッファには、この観測位相とモデル位相の差分を記録します（概念的には）：

$$
\text{Buffer}[k] = \phi_{\text{obs}}(t_k) - (\omega_{\text{est}} t_k - \phi_{\text{corr}})
$$

実際の実装では、連続性を保つためにアンラップ処理（$\pm \pi$ ジャンプの補正）を行った値をバッファリングします。

**位相アンラップ**:

位相が $\pm \pi$ を超えてジャンプする場合の連続化処理 ([AP_Observer.cpp](AP_Observer.cpp) 708-718行目):

$$
\phi_{\text{unwrap}}(n) = \begin{cases}
\phi_{\text{raw}}(n) - 2\pi, & \text{if } \phi_{\text{raw}}(n) - \phi(n-1) > \pi \\
\phi_{\text{raw}}(n) + 2\pi, & \text{if } \phi_{\text{raw}}(n) - \phi(n-1) < -\pi \\
\phi_{\text{raw}}(n), & \text{otherwise}
\end{cases}
$$

### 6.3 線形回帰による周波数誤差推定

バッファに蓄積された位相データ（過去100サンプル程度、約1秒分）に対し、**時刻 $t$ に対する線形回帰**を行います。

$$
\text{slope} = \frac{d}{dt}(\text{PhaseDiff}) \approx \Delta\omega \quad [\text{rad/s}]
$$

実装コード ([AP_Observer.cpp](AP_Observer.cpp) `linear_fit_slope_time`) では、サンプリング周期の揺らぎを考慮し、インデックスではなく**実時刻(ms)**を用いて傾きを計算します。

**最小二乗法によるフィッティング**:

データ点 $(t_i, \phi_i)$ ($i = 0, 1, ..., N-1$) に対して：

$$
\text{slope} = \frac{N \sum_{i} t_i \phi_i - (\sum_{i} t_i)(\sum_{i} \phi_i)}{N \sum_{i} t_i^2 - (\sum_{i} t_i)^2}
$$

得られた傾きから周波数誤差を計算：

$$
\Delta f = \frac{\text{slope}}{2\pi} \quad [\text{Hz}]
$$

この $\Delta f$ が、現在の推定周波数と真の外乱周波数の誤差です。振動の周期がモデルより速ければ位相は進んでいくため、傾きは正になります。

### 6.4 周波数更新ロジック

スイッチ（RC Aux 316、または `OBS_FREQ_EST_CH` で指定したチャンネル）がONの間、推定周波数 `estimated_frequency` を更新します。

1. **瞬時推定値**: 
   $$f_{\text{target}} = f_{\text{current}} + \Delta f$$
   
2. **ローパスフィルタ**: 急激な変化を防ぐため、指数移動平均（EMA）で更新します。
   $$ f_{\text{new}} = f_{\text{old}} + \alpha (f_{\text{target}} - f_{\text{old}}), \quad \alpha=0.15 $$
   
   フィルタ係数 $\alpha = 0.15$ は、約6.7サンプル（0.33秒、20Hz動作時）の時定数に相当します。これにより、ノイズによる急激な周波数変動を抑制しつつ、真の周波数変化には十分追従できます。

### 6.5 位相バッファの補正 (Phase Buffer Correction Fix)

周波数を更新した際、過去のデータに対する「モデル位相」の定義が変わってしまいます。これを放置すると、次回の計算で誤った傾き（ウィンドアップ）が検出されるため、**バッファ内の過去データも更新後の周波数に合わせて補正**します。

**周波数変化量**:
$$ \Delta\omega_{\text{diff}} = 2\pi (f_{\text{new}} - f_{\text{old}}) $$

**バッファ補正式**:

現在時刻 $t_{curr}$ において位相の連続性を保つため、過去の時刻 $t_i$ におけるバッファ値 $B_{old}(t_i)$ を以下のように書き換えます：

$$
B_{new}(t_i) = B_{old}(t_i) + \Delta\omega_{\text{diff}} \cdot (t_{curr} - t_i)
$$

**導出の背景**:

周波数が変わると、過去の時刻 $t_i$ におけるモデル位相も変化します：
- 旧モデル: $\phi_{\text{model, old}}(t_i) = \omega_{\text{old}} \cdot t_i - \phi_{\text{corr}}$
- 新モデル: $\phi_{\text{model, new}}(t_i) = \omega_{\text{new}} \cdot t_i - \phi_{\text{corr}}'$

現在時刻 $t_{curr}$ での位相の連続性を保つため、$\phi_{\text{corr}}'$ を調整します：
$$\phi_{\text{corr}}' = \phi_{\text{corr}} + \Delta\omega_{\text{diff}} \cdot t_{curr}$$

これにより、過去の時刻 $t_i$ におけるモデル位相の変化量は：
$$\Delta\phi_{\text{model}}(t_i) = -\Delta\omega_{\text{diff}} \cdot (t_{curr} - t_i)$$

バッファ値は「観測位相 - モデル位相」なので、モデル位相が減少した分だけバッファ値を増やす必要があります：
$$B_{new}(t_i) = B_{old}(t_i) + \Delta\omega_{\text{diff}} \cdot (t_{curr} - t_i)$$

この補正により、周波数が収束した直後に傾きがゼロ（平坦）になり、安定した推定が可能になります。

### 6.6 位相ジャンプ補正

周波数推定とは別に、累積した位相誤差 `phase_error` が閾値（`OBS_PHASE_THRESH`、デフォルト = 0.0 rad）を超えた場合、即時補正（ジャンプ）を行います。

**注意**: デフォルト値が0.0のため、実質的には**閾値判定なしで常に補正**が適用されます。これは、Phase Buffer Correction Fixにより周波数推定が正確に行われるため、位相誤差が十分小さく抑えられることが前提となっています。

**位相補正の更新**:
$$ \phi_{\text{corr}} \leftarrow \phi_{\text{corr}} - \text{phase\_error} $$

**閾値判定**:
$$
\text{if } |\phi_{\text{error}}| \leq \phi_{\text{thresh}}, \quad \text{skip correction}
$$

バッファ期間全体での累積位相誤差：
$$
\phi_{\text{error}} = \text{slope}_{\text{error}} \times T_{\text{buffer}}
$$

ここで $T_{\text{buffer}}$ はバッファの時間長（約1秒）です。

**RLS係数の座標回転**:

位相補正を行うと、RLSフィルタの内部状態（係数 $A, B$）と位相補正が不整合を起こします。これを防ぐため、**係数の座標回転**を行います。

補正量 $d = \text{phase\_error}$ に対し：
$$ A' = A \cos(d) + B \sin(d) $$
$$ B' = B \cos(d) - A \sin(d) $$

**導出**:

位相補正前の信号モデル: $y = A\sin(\omega t - \phi) + B\cos(\omega t - \phi)$

位相補正後の位相: $\phi' = \phi - d$

新しい位相基準での係数 $A', B'$ を求めるため、三角関数の加法定理を用います：
$$\sin(\omega t - \phi') = \sin(\omega t - \phi + d)$$
$$= \sin(\omega t - \phi)\cos(d) + \cos(\omega t - \phi)\sin(d)$$

同様に：
$$\cos(\omega t - \phi') = \cos(\omega t - \phi)\cos(d) - \sin(\omega t - \phi)\sin(d)$$

これより、$y = A'\sin(\omega t - \phi') + B'\cos(\omega t - \phi')$ が元の信号 $y$ と一致するためには：
$$A' = A\cos(d) + B\sin(d)$$
$$B' = B\cos(d) - A\sin(d)$$

これにより、補正前後で予測される外力 $F(t) = A\sin(\dots) + B\cos(\dots)$ の値が連続になります。

---

## 7. パラメータ設定

| パラメータ名 | デフォルト | 範囲 | 説明 |
|------------|----------|------|------|
| `OBS_CORR_GAIN` | 0.004 | 0.0-1.0 | 姿勢補正ゲイン（大きいほど補正が強い） |
| `OBS_DIST_FREQ` | 0.6 | 0.35-0.91 | 外乱周波数の初期値 [Hz] |
| `OBS_PRED_TIME` | 0.01 | 0.0-0.5 | 予測時間（先読み時間） [秒] |
| `OBS_FREQ_EST_CH` | 8 | 0-16 | 周波数推定制御用RCチャンネル |


### 7.1 基本パラメータ

| パラメータ名 | 変数名 | デフォルト | 範囲 | 単位 | 説明 |
|------------|--------|----------|------|------|------|
| `OBS_CORR_GAIN` | `_correction_gain` | 0.004 | 0.0-1.0 | - | 姿勢補正ゲイン（大きいほど補正が強い） |
| `OBS_DIST_FREQ` | `_disturbance_freq` | 0.6 | 0.35-0.91 | Hz | 外乱周波数の初期値 |
| `OBS_PRED_TIME` | `_prediction_time` | 0.01 | 0.0-0.5 | s | 予測時間（先読み時間、遅延補償） |
| `OBS_FREQ_EST_CH` | - | 8 | 0-16 | - | 周波数推定制御用RCチャンネル |
| `OBS_FILT_CUTOFF` | `_filter_cutoff_freq` | 20.0 | 1.0-100.0 | Hz | ローパスフィルタのカットオフ周波数（現在は無効化） |

### 7.2 RLS推定アルゴリズム設定

| パラメータ名 | 変数名 | デフォルト | 範囲 | 説明 |
|------------|--------|----------|------|------|
| `OBS_RLS_LAMBDA` | `_rls_forgetting_factor` | 0.98 | 0.9-0.9999 | 忘却係数（1に近いほどノイズに強く、追従が遅い） |
| `OBS_RLS_COV_INIT` | `_rls_initial_covariance` | 100.0 | 0.001-1000 | 初期共分散値（大きいほど初期学習が速い） |
| `OBS_PHASE_CORR` | `_phase_correction_enabled` | 1 | 0/1 | 位相補正の有効/無効 |
| `OBS_PHASE_THRESH` | `_phase_correction_threshold` | 0.0 | 0.0-5.0 | 位相ジャンプ補正の閾値 [rad] |
| `OBS_FREQ_ALPHA` | `_freq_est_alpha` | 0.15 | 0.001-0.5 | 周波数推定フィルタ係数（指数移動平均） |
| `OBS_MAX_CORR_ANG` | `_max_correction_angle` | 0.5 | 0.0-1.0 | 補正角度の最大値 [rad] |

### 7.3 内部定数

| 定数名 | 値 | 説明 |
|--------|-----|------|
| `RLS_PARAM_SIZE` | 3 | RLSパラメータ数（A, B, C） |
| `RLS_NUM_AXES` | 3 | 軸数（x, y, z） |
| `RLS_MIN_LAMBDA` | 0.9 | 忘却係数の最小値 |
| `RLS_MAX_LAMBDA` | 0.9999 | 忘却係数の最大値 |
| `RLS_MIN_COVARIANCE` | 0.001 | 共分散の最小値 |
| `RLS_MAX_COVARIANCE` | 1000.0 | 共分散の最大値 |
| `PHASE_BUFFER_SIZE` | 60 | 位相バッファのサイズ（3秒分、20Hz動作時） |
| `FREQ_MIN` | 0.35 Hz | 周波数推定の下限（振り子長2.0m相当） |
| `FREQ_MAX` | 0.91 Hz | 周波数推定の上限（振り子長0.3m相当） |
| `FORCE_THRESHOLD` | 0.0 N | 外力の大きさに関わらず常に補正がかかる（閾値なし） |
| `UAV_mass` | 1.4 kg | ドローンの質量 |
| `g` | 9.7985 m/s² | 重力加速度 |

### 7.4 テスト・デバッグ設定

| パラメータ名 | デフォルト | 説明 |
|------------|----------|------|
| `OBS_TEST_INJECT` | 0 | 1でテスト信号を強制注入（SITL用） |
| `OBS_TEST_FREQ` | 0.7 | テスト信号の周波数 [Hz] |
| `OBS_TEST_AMP` | 1.0 | テスト信号の振幅 [N] |

### 7.5 パラメータ決定の根拠

#### 忘却係数 $\lambda = 0.98$

**意味**: 過去のデータへの重み付け。$\lambda$ が1に近いほど過去のデータを重視。

**有効時定数**:
$$
\tau_{\text{eff}} = \frac{1}{1 - \lambda} = \frac{1}{1 - 0.98} = 50 \text{ samples}
$$

100 Hzサンプリング時：$\tau_{\text{eff}} = 0.5$ 秒

**決定理由**:
- 外乱周波数が0.6 Hzの場合、1周期は約1.67秒
- 0.5秒の時定数により、半周期程度のデータで適応可能
- 急激な外乱変化に追従しつつ、ノイズの影響を抑制

#### 初期共分散 $P_0 = 100.0$

**意味**: パラメータの初期不確実性。大きいほど初期の学習速度が速い。

**決定理由**:
- 初期値が未知のため、大きな不確実性を設定
- RLS更新により自動的に収束するため、保守的な大きめの値
- 範囲 [0.001, 1000.0] の中間的な値で安定性と応答性のバランス

#### 外乱周波数 $f_{\text{set}} = 0.6$ Hz

**意味**: 想定される外乱の周波数。

**決定理由**:
- ケーブル吊り下げペイロードの典型的な振動周波数
- 振り子の固有周波数: $f = \frac{1}{2\pi}\sqrt{\frac{g}{L}}$
- ケーブル長 $L \approx 2.7$ m の場合: $f \approx 0.6$ Hz
- 位相補正により実際の周波数とのずれをオンライン調整

#### 予測時間 $\Delta t = 0.01$ s

**意味**: どれだけ先の外力を予測するか。

**決定理由**:
- 姿勢制御の遅延補償（センサ処理、通信、アクチュエータ遅延）
- 典型的な制御ループ遅延: 5~20 ms
- 10 msは最小限の先読みで、制御安定性を確保

#### 位相補正閾値 $\phi_{\text{thresh}} = 0.0$ rad

**意味**: この値以下の位相誤差は無視。デフォルトは0.0（閾値なし、常に補正を適用）。

**決定理由**:
- **デフォルト0.0**: 周波数推定が正確であれば位相誤差は十分小さく抑えられるため、閾値を設けずに常時補正を適用
- バッファ補正（Phase Buffer Correction Fix）により、周波数収束後の位相誤差は実質ゼロに近づくため、閾値判定は不要
- パラメータとして残しているのは、必要に応じてデッドバンドを設定できるようにするため（互換性・デバッグ用途）

計算例（参考）：
- 実周波数 $f_{\text{actual}} = 0.7$ Hz
- 設定周波数 $f_{\text{set}} = 0.6$ Hz
- バッファ60サンプル（3秒分）、20Hz動作時
- 傾き誤差：$(2\pi \times 0.7 - 2\pi \times 0.6) = 0.628$ rad/s
- 3秒での累積誤差：$0.628 \times 3.0 \approx 1.88$ rad

周波数推定が収束すれば、このような累積誤差は自動的に解消されます。

#### 補正ゲイン $k_{\text{corr}} = 0.004$

**意味**: 外力から姿勢補正角への変換ゲイン。

$$
\text{Roll} = \frac{F_y \cdot k_{\text{corr}}}{m}, \quad \text{Pitch} = -\frac{F_x \cdot k_{\text{corr}}}{m}
$$

**決定理由**:
- 例: $F_y = 1.4$ N（質量と同等）の場合
  - Roll補正 = $\frac{1.4 \times 0.004}{1.4} = 0.004$ rad ≈ 0.23°
- 小さな補正で徐々に外乱を打ち消す設計
- 過剰補正を避け、制御の安定性を優先

---

## 8. 実装詳細

### 8.1 予測外力の計算

時刻 $t$ から $\Delta t$ 秒後の外力予測 ([AP_Observer.cpp](AP_Observer.cpp) 630-670行目):

$$
F_i(t + \Delta t) = A_i \sin(\omega(t + \Delta t) - \phi_{\text{obs}}) + B_i \cos(\omega(t + \Delta t) - \phi_{\text{obs}}) + C_i
$$

実装では、X軸の観測位相 `ab_phase_unwrapped[0]` を全軸の予測に使用しています。これは、X軸とY軸の外力が同じ周波数で振動すると仮定しているためです（吊り下げペイロードの場合、これは妥当な仮定です）。

実装コード:
```cpp
float phase_pred = _omega_rad * (t + _prediction_time.get()) - ab_phase_unwrapped[0];
float sin_omega_t_dt = sinf(phase_pred);
float cos_omega_t_dt = cosf(phase_pred);

for (uint8_t axis = 0; axis < RLS_NUM_AXES; axis++) {
    float A = rls_theta[axis][0];
    float B = rls_theta[axis][1];
    float C = rls_theta[axis][2];
    
    float force = A * sin_omega_t_dt + B * cos_omega_t_dt + C;
    // ...
}
```

### 8.2 姿勢補正の計算

**補正値の計算**（オイラー角形式）

AP_Observerでは、外力から補正用のオイラー角（ロール、ピッチ）を計算します：

$$
\text{Roll}_{\text{corr}} = \frac{F_y \cdot k_{\text{corr}}}{m}, \quad \text{Pitch}_{\text{corr}} = -\frac{F_x \cdot k_{\text{corr}}}{m}
$$

注意：符号は座標系に依存。**ヨー角補正は常に0です**。

**角度制限**:
$$
\text{Roll}_{\text{corr}}, \text{Pitch}_{\text{corr}} \in [-0.5, 0.5] \text{ rad}
$$

**AC_AttitudeControlでの補正適用**

姿勢制御側（[AC_AttitudeControl](../AC_AttitudeControl/)）では、目標姿勢クォータニオンを一時変数にコピーし、オイラー角に変換後、補正値を**加算**します：

```cpp
// 一時変数にコピー（元の目標姿勢は変更しない）
Quaternion effective_target = _attitude_target;

// オイラー角形式の補正が設定されている場合のみ適用
if (!_external_correction_euler.is_zero()) {
    float roll_rad, pitch_rad, yaw_rad;
    effective_target.to_euler(roll_rad, pitch_rad, yaw_rad);
    
    // ロールとピッチのみに補正を加算（ヨーは絶対に触らない！）
    float corrected_roll  = roll_rad  + _external_correction_euler.x;
    float corrected_pitch = pitch_rad + _external_correction_euler.y;
    
    // 補正済みのクォータニオンに再変換
    effective_target.from_euler(corrected_roll, corrected_pitch, yaw_rad);
}
```

**重要なポイント**：
- 元の目標姿勢 `_attitude_target` は変更されません
- 一時変数 `effective_target` に補正を適用
- ヨー角は絶対に変更されません（オペレーターの方位指令を保持）
- クォータニオン積算ではなく、オイラー角での**加算**により補正

### 8.3 更新タイミング

- **RLS更新**: 毎ループ（100 Hz想定）
- **位相補正更新**: 20ループごと（約0.2秒ごと）
  - バッファが60サンプル（3秒分）溜まってから動作開始
  - スライディングウィンドウ方式で常時更新
- **デバッグ出力**: 10ループごと（GCS）※現在はコメントアウト
- **ログ記録**: **毎ループ**（SDカード、`Write_Observer_Log()`により全データを記録）

### 8.4 周波数推定スイッチの動作

- **ON (PWM > Center, 1700以上)**: 線形回帰に基づき `estimated_frequency` を常時更新します。同時に位相バッファ補正も行われます。
- **OFF (PWM < Center, 1700未満)**: 周波数更新を停止し、直前の推定値を保持(Hold)します。位相補正ロジックは保持された周波数に基づいて動作を継続します。

**エッジ検出**:
スイッチの状態遷移（OFF→ON、ON→OFF）を検出し、以下の処理を実行します：
- **OFF→ON**: RLS初期化、周波数を初期値にリセット、GCSメッセージ "RLS Freq Est: ON"
- **ON→OFF**: 推定周波数を保持、GCSメッセージ "RLS Freq Est: OFF (Holding ...Hz)"

### 8.5 安全機構

1. **周波数リミッタ**: 推定値が `FREQ_MIN` (0.35 Hz) ~ `FREQ_MAX` (0.91 Hz) を逸脱しないよう制限。
2. **スロープ制限**: 異常な位相変化（`> 1000 rad/s`）が検出された場合は更新をスキップ。
3. **ゼロ除算保護**: 線形回帰の分母がゼロに近い場合は計算を中止。
4. **共分散行列のクランプ**: $[0.001, 1000.0]$ の範囲内に制限。
5. **パラメータの範囲制限**: `constrain_value` 関数を使用して各パラメータを許容範囲内に制限。

### 8.6 数値安定性対策のまとめ

1. **分母のゼロ除算チェック**: $< 10^{-12}$
2. **共分散の範囲制限**: $[0.001, 1000.0]$
3. **パラメータの範囲制限**: `constrain_value`使用
4. **位相アンラップ**: $\pm \pi$ ジャンプを連続化
5. **忘却係数の範囲**: $[0.9, 0.9999]$

---

## 9. ログとデバッグ

### 9.1 SDカードログ形式

**ログタグ**: `OBSV`

**記録頻度**: **毎ループ**（100 Hz、update()関数の最後で`Write_Observer_Log()`が呼ばれる）

**フィールド** ([AP_Observer.cpp](AP_Observer.cpp) Write_Observer_Log()関数):

| フィールド | 単位 | 説明 |
|-----------|------|------|
| `TimeUS` | μs | タイムスタンプ（マイクロ秒） |
| `PLX` | N | 外力 X軸（フィルタなし生データ） |
| `PLY` | N | 外力 Y軸（フィルタなし生データ） |
| `PLZ` | N | 外力 Z軸（フィルタなし生データ） |
| `AX` | - | RLS sin係数 X軸 |
| `AY` | - | RLS sin係数 Y軸 |
| `BX` | - | RLS cos係数 X軸 |
| `BY` | - | RLS cos係数 Y軸 |
| `CX` | N | RLS 定常偏差 X軸 |
| `CY` | N | RLS 定常偏差 Y軸 |
| `PRX` | N | 予測外力 X軸 |
| `PRY` | N | 予測外力 Y軸 |
| `PRZ` | N | 予測外力 Z軸 |
| `ERR` | rad | 位相誤差（バッファ満杯時のみ計算） |
| `EST_FREQ` | Hz | 推定周波数（バッファ満杯時のみ計算） |
| `CORR` | rad | 累積位相補正量 |
| `SW` | - | **RCスイッチ状態 (0:OFF, 1:ON)** |

### 9.2 GCSデバッグメッセージ

**スイッチ切り替え時** ([AP_Observer.cpp](AP_Observer.cpp) update()関数):
- **"RLS Freq Est: ON (Reset to ...Hz)"**: スイッチON時、推定周波数を初期値にリセット。
- **"RLS Freq Est: OFF (Holding ...Hz)"**: スイッチOFF時、現在の推定値を保持。

**周波数更新時** ([AP_Observer.cpp](AP_Observer.cpp) phase_correction_update()関数):
- **"PhaseCorr: est=... df=... slope=..."**: 周波数更新時に変化量と現在の推定値を表示（間引き出力、毎回）。
  - `est`: 現在の推定周波数 [Hz]
  - `df`: 周波数変化量 [Hz]
  - `slope`: 位相勾配 [rad/s]

**周波数保持時**:
- **"PhaseCorr: f=... (HOLDING - no update)"**: スイッチOFF時、推定値を保持していることを表示（20回に1回）。

**位相補正適用時**:
- **"PhaseCorr: err=... est_freq=... corr=..."**: 位相ジャンプ補正を適用した場合。
  - `err`: 位相誤差 [rad]
  - `est_freq`: 推定周波数 [Hz]
  - `corr`: 累積補正量 [rad]
- **"PhaseCorr: err=... est_freq=... corr=... (no correction)"**: 閾値以下で補正不要の場合。

**警告メッセージ**:
- **"PhaseCorr: f=...Hz (df=...) OutOfRange (...-...)"**: 推定周波数が制限範囲を超えた場合の警告（10回に1回）。

### 9.3 ログデータの可視化

[analysis/scripts/](../../analysis/scripts/) ディレクトリに、ログデータを可視化するPythonスクリプトが用意されています。

```bash
# ログファイルの解析
cd analysis/scripts
python plot_observer_log.py /path/to/log/00000123.BIN
```

---

## 10. オートテスト


以下のSITLテストスクリプトで動作検証が可能です。

```bash
# ビルド
cd /home/memoto/Ardupilot-UmemotoLab
./waf copter

# 全テスト実行
timeout 600 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.TestRLSBasicEstimation
timeout 600 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.TestRLSRC8SwitchControl
timeout 600 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.TestRLSWindowedEstimation
```

### テスト内容

*   **TestRLSBasicEstimation**: 固定周波数（0.7 Hz）での基本動作確認
    *   テスト信号を注入し、RLSが正しくパラメータ推定できるか検証
    *   推定周波数が設定値に収束することを確認
    
*   **TestRLSRC8SwitchControl**: RCスイッチによる周波数推定ON/OFF動作の確認
    *   スイッチOFF→ON→OFFの遷移を再現
    *   周波数推定のリセット、学習、保持が正しく動作することを検証
    
*   **TestRLSWindowedEstimation**: 短時間ウィンドウでの学習動作確認
    *   10秒間のスイッチON期間で周波数を学習
    *   学習後にスイッチOFFで推定値を保持することを確認

---

## 11. トラブルシューティング

### 周波数が学習されない

**症状**: `OBSV.EST_FREQ` が初期値のまま変化しない。

**確認事項**:
*   スイッチが正しくONになっているか `OBSV.SW` ログで確認してください。
    *   `SW = 1` (ON) になっていれば、周波数推定は動作しています。
    *   `SW = 0` (OFF) の場合、スイッチのPWM値が閾値（1700）を超えていません。`RC8` (または設定したチャンネル) のPWM値を確認してください。
*   外乱の振幅が小さすぎる（< 1.0N）とノイズと判断され学習されません。
    *   `OBSV.PLX`, `OBSV.PLY` の値を確認してください。
*   位相バッファが十分に溜まっていない（20サンプル未満）。
    *   離陸後、少なくとも1秒間は待ってからスイッチをONにしてください。

### 推定値が暴れる

**症状**: `OBSV.EST_FREQ` が短時間で大きく変動する。

**対策**:
*   `OBS_RLS_LAMBDA` を大きく（0.99など）して平滑化を強めてください。
    *   忘却係数が小さいと、ノイズの影響を受けやすくなります。
*   外乱の周波数が急激に変化している可能性があります。
    *   吊り下げケーブルの長さが変化していないか確認してください。
*   周波数更新のフィルタ係数 `FREQ_EST_ALPHA` を小さく（0.005など）することも有効です。
    *   現在はコード内定数（0.01）ですが、必要に応じて変更可能です。

### 姿勢補正が効かない

**症状**: 外乱を受けても機体姿勢が補正されない。

**確認事項**:
*   `OBS_CORR_GAIN` が小さすぎる可能性があります。
    *   デフォルトの 0.004 から 0.008 程度に増やしてみてください。
*   予測外力 `OBSV.PRX`, `OBSV.PRY` が十分な大きさか確認してください。
    *   予測外力が小さい場合でも、常に補正がかかります（FORCE_THRESHOLD=0.0 N）。
*   姿勢制御側（AC_AttitudeControl）で補正が正しく適用されているか確認してください。

### ログに記録されない

**症状**: SDカードに `OBSV` ログが記録されない。

**確認事項**:
*   `LOG_BITMASK` パラメータで適切なログレベルが設定されているか確認してください。
*   SDカードの空き容量が十分にあるか確認してください。
*   コンパイル時に `HAL_LOGGING_ENABLED` が有効になっているか確認してください（通常は有効）。

### 周波数推定が範囲外エラー

**症状**: GCSに "PhaseCorr: f=...Hz OutOfRange" というメッセージが表示される。

**原因**:
*   推定周波数が `FREQ_MIN` (0.35 Hz) ~ `FREQ_MAX` (0.91 Hz) の範囲を超えています。
*   これは通常、位相データにノイズや異常値が含まれている場合に発生します。

**対策**:
*   外乱の振幅が十分にあるか（> 1.0N）確認してください。
*   ケーブル長が想定範囲内（0.3m ~ 2.0m）にあるか確認してください。
    *   振り子の周波数: $f = \frac{1}{2\pi}\sqrt{\frac{g}{L}}$
    *   $L = 0.3$ m → $f \approx 0.91$ Hz
    *   $L = 2.0$ m → $f \approx 0.35$ Hz
*   範囲外のメッセージが表示されても、周波数は制限範囲内にクランプされるため、システムは動作を継続します。

---

## まとめ

### システムの強み

1. **オンライン適応**: RLSにより外乱パラメータをリアルタイム学習
2. **周波数追従**: 位相補正により設定周波数と実周波数のずれを自動調整
3. **予測制御**: 遅延を補償した先読み制御
4. **数値安定性**: 各種閾値とクランプで安定した動作を保証
5. **軽量実装**: 100 Hzで動作可能な計算量

### 調整のポイント

| 目的 | 調整パラメータ | 方向 |
|------|---------------|------|
| 収束速度を上げる | `OBS_RLS_LAMBDA` | 小さくする（0.95など） |
| 収束速度を上げる | `OBS_RLS_COV_INIT` | 大きくする（500など） |
| 予測精度を上げる | `OBS_PRED_TIME` | 実際の遅延に合わせる |
| 周波数追従を敏感に | `OBS_PHASE_THRESH` | 小さくする（5.0など） |
| 補正を強める | `OBS_CORR_GAIN` | 大きくする（0.01など） |

### 今後の拡張可能性

- **複数周波数対応**: 基本波と高調波の同時推定
- **適応的忘却係数**: 外乱の変動に応じて $\lambda$ を調整
- **周波数自動推定**: FFTやARモデルによる周波数自動検出
- **非線形モデル**: 大振幅振動への対応

---

## 参考文献

- Ljung, L. (1999). *System Identification: Theory for the User*. Prentice Hall.
- Åström, K. J., & Wittenmark, B. (2013). *Adaptive Control* (2nd ed.). Dover Publications.
- Haykin, S. (2002). *Adaptive Filter Theory* (4th ed.). Prentice Hall.

---

**License**: GPLv3  
**Maintainer**: Umemoto Lab  
**最終更新**: 2026年1月29日
