# AP_Observer - 外乱推定システム (EKF: Robust + Smooth M30)

最終更新日: 2026-04-15

## 1. 目的と現状

AP_Observer は、機体座標系で観測される外力をオンライン推定し、予測外力に基づく姿勢補正へ接続するライブラリです。

現行の推定器コアは EKF ベースです。運用上の推奨プロファイルは Robust + Smooth M30 で、外れ値抑制を優先しながら低振幅領域のスパイクを抑える構成になっています。

- 本番接続先: ArduCopter から observer.init と observer.update を呼び出し
- 出力: 予測外力 get_predicted_force、姿勢補正 get_correction_euler
- ログ: OBSV

## 2. 状態定義とモデル

各軸を独立な 1D EKF として更新します。軸インデックスは X, Y, Z の 3軸です。

状態ベクトル:

$$
\mathbf{x}_k = [d_k,\ \dot d_k,\ c_k,\ \omega_k]^T
$$

- $d_k$: 周期外乱成分
- $\dot d_k$: その時間微分
- $c_k$: DCオフセット
- $\omega_k$: 角周波数 [rad/s]

観測量:

$$
z_k = d_k + c_k + v_k
$$

観測行列:

$$
\mathbf{H} = [1,\ 0,\ 1,\ 0]
$$

## 3. 離散時間状態遷移

サンプル間隔を $\Delta t$ とすると、予測モデルは次です。

$$
d_{k+1} = d_k + \Delta t\,\dot d_k
$$

$$
\dot d_{k+1} = \dot d_k - \Delta t\,\omega_k^2 d_k
$$

$$
c_{k+1} = c_k,\quad \omega_{k+1} = \omega_k
$$

ヤコビアン:

$$
\mathbf{F}_k =
\begin{bmatrix}
1 & \Delta t & 0 & 0 \\
-\Delta t\,\omega^2 & 1 & 0 & -2\Delta t\,\omega d \\
0 & 0 & 1 & 0 \\
0 & 0 & 0 & 1
\end{bmatrix}
$$

予測:

$$
\hat{\mathbf{x}}_{k|k-1} = f(\hat{\mathbf{x}}_{k-1|k-1})
$$

$$
\mathbf{P}_{k|k-1} = \mathbf{F}_k\mathbf{P}_{k-1|k-1}\mathbf{F}_k^T + \mathbf{Q}_k
$$

## 4. Hold / Reject ロジック

現行実装は、推定の暴れを避けるために観測更新の挙動を条件分岐させます。

### 4.1 条件定義

$$
F_{abs} = |z_k|
$$

- force_hold: $F_{abs} \le F_{hold}$
- switch_hold: 周波数推定SWがOFF かつ EKF_SW_HOLD=1
- energy_hold: エネルギーゲートが非信頼
- hold_omega: force_hold または switch_hold または energy_hold
- predict_only_hold: switch_hold のみ
- force_reject: $F_{abs} \ge F_{reject}$

### 4.2 観測値ゼロ注入

低振幅または低エネルギーでは観測をゼロへ寄せます。

$$
\text{if }(force\_hold \lor energy\_hold),\quad z_k \leftarrow 0
$$

### 4.3 omega のプロセスノイズ制御

周波数状態のプロセスノイズは、SW状態と hold/reject に応じて切り替えます。

$$
q_{\omega,base} =
\begin{cases}
q_\omega & (freq\_est\_active=1)\\
0 & (freq\_est\_active=0)
\end{cases}
$$

$$
q_\omega^{eff} =
\begin{cases}
q_{\omega,base} & (active \land \neg hold\_omega \land \neg force\_reject)\\
\max(q_{\omega,base},10^{-6}) & (active \land (hold\_omega \lor force\_reject))\\
0 & (\neg active)
\end{cases}
$$

## 5. Robust 観測更新

イノベーション:

$$
r_k = z_k - \hat z_{k|k-1},\quad \hat z_{k|k-1} = \hat d_{k|k-1} + \hat c_{k|k-1}
$$

$$
S_k = \mathbf{H}\mathbf{P}_{k|k-1}\mathbf{H}^T + R_{eff}
$$

$$
\mathrm{NIS}_k = \frac{r_k^2}{S_k}
$$

Robust ON 時の処理:

- クリップ:

$$
r_k^{clip} = \mathrm{clip}(r_k, -INN_{max}, +INN_{max})
$$

- NIS が閾値超過時は観測ノイズを膨張:

$$
R_{eff} = R \cdot \frac{\mathrm{NIS}_k}{NIS_{max}} \quad (\mathrm{NIS}_k > NIS_{max})
$$

- 強外れ値は更新拒否:

$$
\mathrm{reject} \iff \mathrm{NIS}_k > NIS_{max} \cdot RB_{nis}
$$

拒否でなければ通常のカルマン更新:

$$
\mathbf{K}_k = \frac{\mathbf{P}_{k|k-1}\mathbf{H}^T}{S_k}
$$

hold_omega 条件では $K_\omega=0$ とし、更新後も $\omega$ を前値へ戻します。

$$
\hat{\mathbf{x}}_{k|k} = \hat{\mathbf{x}}_{k|k-1} + \mathbf{K}_k r_k^{use}
$$

## 6. 軸統合による周波数推定

各軸の $\omega_i$ から fused 周波数を作ります。

信頼軸条件:

- 軸マスク EKF_AX_MASK に含まれる
- force_reject 条件を満たさない
- EKF_EN_GAT=1 のとき energy trusted
- $|innovation| \le INN_{max}$
- $NIS \le NIS_{max}$

統合式:

$$
\omega_{fused} = \frac{1}{N}\sum_{i \in trusted}\omega_i,\quad
f_{est} = \frac{\omega_{fused}}{2\pi}
$$

trusted 軸が無い場合は前回の推定周波数を維持します。

## 7. 予測外力

制御へ渡す予測外力は、PRED_TIME 先の一次予測を使います。

$$
d_{pred} = d + PRED\_TIME\cdot\dot d
$$

$$
F_{pred} = d_{pred} + c
$$

これを各軸で計算して PRX, PRY, PRZ として利用します。

## 8. Robust + Smooth M30 プロファイル

以下は検証済みの M30 推奨値です。

| 項目 | 値 |
|---|---:|
| EKF_RB_EN | 1 |
| EKF_RB_NIS | 3.0 |
| EKF_INN_MAX | 0.70 |
| EKF_NIS_MAX | 4.0 |
| EKF_EN_GAT | 1 |
| EKF_EN_ON | 0.20 |
| EKF_EN_OFF | 0.16 |
| EKF_EN_TAU | 2.0 |
| EKF_AX_MASK | 3 |
| EKF_Q_D | 9.5367432e-12 |
| EKF_Q_DD | 2.3841858e-11 |
| EKF_Q_C | 4.7683716e-13 |
| EKF_R_MEAS | 46.0 |

補足:

- M30 はスパイク抑制優先の強平滑プロファイルです。
- ファームウェアの AP_Param デフォルト値は M30 に合わせて初期化されています。
- 実験再現は [analysis/replay/run_robust_smooth_m30_concat_direct_replay.py](analysis/replay/run_robust_smooth_m30_concat_direct_replay.py) を使用します。

## 9. ログ仕様 (OBSV)

OBSV の主要フィールド:

- TimeUS: タイムスタンプ [us]
- PLX, PLY, PLZ: 観測外力
- DX, DY, DZ: 状態 d
- VX, VY, VZ: 状態 d_dot
- CX, CY, CZ: 状態 c
- F: fused 推定周波数 [Hz]
- SW: 推定スイッチ状態

## 10. 命名統一状況

公開 API と replay 実行器は EKF ベースの命名へ統一済みです。

- API: get_harmonic_sin_coeff, get_harmonic_cos_coeff, get_dc_offset, force_frequency_estimation_update
- replay: EKF_CSV_Replay
