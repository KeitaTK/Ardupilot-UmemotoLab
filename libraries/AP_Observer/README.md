# AP_Observer: 外力推定から補正角生成までの数理アルゴリズム

最終更新: 2026-04-18

## 1. 目的

本書は、AP_Observer の処理をプログラム実行順に従って、数式中心で記述する。
対象は「外乱力の観測量生成」から「EKFによる状態推定」「予測外力算出」「補正角・補正クォータニオン生成」までである。

実装上の分岐条件や安全化処理も、推定器の一部として明示する。

## 2. 記号定義

- サンプリング時刻: $k$
- サンプリング間隔: $\Delta t_k$
- 予測ホライズン: $\Delta p$
- 機体質量: $m$
- 重力加速度: $g$
- 正規化スロットル指令: $u_k$
- 推力モデル係数: $\alpha_T,\beta_T$
- 機体座標系加速度: $\mathbf{a}_k=[a_{x,k},a_{y,k},a_{z,k}]^\top$
- 観測外力: $\mathbf{z}_k=[z_{x,k},z_{y,k},z_{z,k}]^\top$
- 軸インデックス: $i\in\{x,y,z\}$

各軸EKF状態は

$$
\mathbf{x}_{i,k} =
\begin{bmatrix}
d_{i,k} \\
\dot d_{i,k} \\
c_{i,k} \\
\omega_{i,k}
\end{bmatrix},
\qquad
\mathbf{P}_{i,k}\in\mathbb{R}^{4\times 4}
$$

とする。

- $d$: 調和外乱成分
- $\dot d$: その時間微分
- $c$: 低周波/バイアス成分
- $\omega$: 角周波数

## 3. 観測外力の生成 (処理の先頭)

### 3.1 推力補償

推力は線形近似で

$$
T_k = -\left(\alpha_T u_k + \beta_T\right)g
$$

とし、機体加速度から外力観測量を

$$
z_{x,k}=m a_{x,k},\quad
z_{y,k}=m a_{y,k},\quad
z_{z,k}=m a_{z,k}-T_k
$$

として構成する。ここで $\mathbf{z}_k$ は「推定すべき外乱力」の観測値である。

### 3.2 更新ゲート

離陸フラグが真であり、かつ推定器初期化済みの場合にのみEKF更新を実行する。
周波数更新はスイッチ状態により有効/無効を切り替えるが、状態推定全体は安全側の分岐規則で継続可能とする。

## 4. 軸別EKFの状態方程式と観測方程式

### 4.1 非線形離散時間モデル

各軸の時間更新は

$$
d_{k+1}=d_k+\Delta t_k\dot d_k
$$
$$
\dot d_{k+1}=\dot d_k-\Delta t_k\omega_k^2 d_k
$$
$$
c_{k+1}=c_k,\qquad \omega_{k+1}=\omega_k
$$

で与える。観測モデルは

$$
z_k = d_k + c_k + v_k
$$

であり、

$$
\mathbf{H}=\begin{bmatrix}1&0&1&0\end{bmatrix}
$$

となる。

### 4.2 ヤコビアン

予測点 $(d_k,\dot d_k,c_k,\omega_k)$ 周りの状態ヤコビアンは

$$
\mathbf{F}_k=
\begin{bmatrix}
1 & \Delta t_k & 0 & 0 \\
-\Delta t_k\omega_k^2 & 1 & 0 & -2\Delta t_k\omega_k d_k \\
0 & 0 & 1 & 0 \\
0 & 0 & 0 & 1
\end{bmatrix}
$$

である。

### 4.3 標準EKF更新

標準形は

$$
\mathbf{x}_{k|k-1}=f(\mathbf{x}_{k-1|k-1}),\qquad
\mathbf{P}_{k|k-1}=\mathbf{F}_k\mathbf{P}_{k-1|k-1}\mathbf{F}_k^\top+\mathbf{Q}_k
$$

$$
r_k=z_k-h(\mathbf{x}_{k|k-1}),\quad
S_k=\mathbf{H}\mathbf{P}_{k|k-1}\mathbf{H}^\top+R_k
$$

$$
\mathbf{K}_k=\mathbf{P}_{k|k-1}\mathbf{H}^\top S_k^{-1}
$$

$$
\mathbf{x}_{k|k}=\mathbf{x}_{k|k-1}+\mathbf{K}_k r_k,
\quad
\mathbf{P}_{k|k}=(\mathbf{I}-\mathbf{K}_k\mathbf{H})\mathbf{P}_{k|k-1}
$$

である。実装では数値安定化のため共分散対称化

$$
\mathbf{P}_{k|k}\leftarrow\frac{1}{2}\left(\mathbf{P}_{k|k}+\mathbf{P}_{k|k}^\top\right)
$$

を行う。

## 5. ロバスト化分岐 (実装の本質)

本実装は標準EKFをそのまま適用せず、外乱振幅・エネルギー・スイッチ状態に応じた分岐を直列に適用する。

### 5.1 エネルギー信頼度ゲート

高速帯域出力と低速帯域出力の差を $r_k$ とし、エネルギー包絡を

$$
p_k = \alpha_k r_k^2 + (1-\alpha_k)p_{k-1},
\quad
\alpha_k = 1-e^{-\Delta t_k/\tau}
$$

で更新する。ヒステリシス閾値 $(\rho_{on},\rho_{off})$ により信頼フラグを更新し、信頼度が低い場合は周波数更新を凍結方向に誘導する。

### 5.2 振幅ベース保持・除外

観測振幅 $|z_k|$ に対し、保持閾値 $\zeta_h$ と除外閾値 $\zeta_r$ を用いて

- 保持条件: $|z_k|\le \zeta_h$
- 除外条件: $|z_k|\ge \zeta_r$

を定義する。保持時は角周波数更新を停止し、除外時は観測更新自体をスキップして予測値のみ採用する。

### 5.3 ゼロ注入

低振幅または低エネルギー時には観測値を

$$
z_k\leftarrow 0
$$

に置き換えて更新する。これは更新ゲインが過大化しやすい低SNR領域での過補正を抑えるためである。

### 5.4 Innovation clipping と NIS判定

イノベーションを

$$
r_k = z_k-h(\mathbf{x}_{k|k-1})
$$

とし、NISを

$$
\nu_k=\frac{r_k^2}{S_k}
$$

と定義する。

- $|r_k|$ は上限 $r_{max}$ でクリップ
- $\nu_k>\nu_{max}$ のとき $R_k$ を比例拡大
- $\nu_k>\gamma\nu_{max}$ のとき更新拒否 (predict-only)

とする。これにより外れ値での共分散破綻を抑制する。

### 5.5 周波数状態の凍結

保持条件成立時はカルマンゲインの周波数成分を

$$
K_{\omega}=0
$$

とし、更新後も

$$
\omega_{k|k}\leftarrow\omega_{k-1|k-1}
$$

を強制する。

## 6. XY軸の共有周波数融合

各軸は独立EKFであるが、周波数推定のみXYで弱結合させる。

### 6.1 融合重み

各軸重みは

$$
w_i = w_i^{\mathrm{nis}}\,w_i^{\mathrm{eng}}\,w_i^{\mathrm{amp}}\,w_i^{\mathrm{hold}}
$$

で定義し、たとえば

$$
w_i^{\mathrm{nis}}=\frac{1}{1+(\nu_i/\nu_{max})^2}
$$

を用いる。低信頼軸には追加減衰を与える。

### 6.2 共有角周波数

候補共有値 $\bar\omega$ は、信頼軸平均または重み付き平均から決定する。共有注入係数を $\beta\in[0,1]$ とすると、低信頼かつ凍結軸に対して

$$
\omega_i\leftarrow (1-\beta)\omega_i + \beta\bar\omega
$$

を適用する。強制モードでは直接置換

$$
\omega_i\leftarrow\bar\omega
$$

を用いる。

## 7. 予測外力の生成

補正に使用する外力は現在値ではなく、予測ホライズン $\Delta p$ 先で評価する。

$$
d_{k+\Delta p}\approx d_k+\Delta p\,\dot d_k
$$

$$
\hat f_{i,k+\Delta p}=d_{i,k+\Delta p}+c_{i,k}
$$

したがって予測外力ベクトルは

$$
\hat{\mathbf{f}}_{k+\Delta p}=
\begin{bmatrix}
\hat f_{x,k+\Delta p}\\
\hat f_{y,k+\Delta p}\\
\hat f_{z,k+\Delta p}
\end{bmatrix}
$$

である。

## 8. 補正角と補正クォータニオン

### 8.1 補正角

予測外力ノルム $\|\hat{\mathbf{f}}\|$ が閾値 $f_{min}$ 未満なら補正はゼロとする。

それ以外では、補正ゲイン $k_c$ を用いて

$$
\phi = \mathrm{sat}\!\left(\frac{k_c}{m}\hat f_y,\,\phi_{max}\right),
\qquad
	heta = \mathrm{sat}\!\left(-\frac{k_c}{m}\hat f_x,\,\theta_{max}\right),
\qquad
\psi=0
$$

とする。ここで $\mathrm{sat}(\cdot)$ は角度上限での飽和関数である。

### 8.2 クォータニオン化

得られたオイラー角 $(\phi,\theta,\psi)$ から補正クォータニオン $\mathbf{q}_c$ を生成し、正規化して出力する。

## 9. プログラム順アルゴリズム (要約)

1. センサ加速度とスロットルから $\mathbf{z}_k$ を構成
2. 離陸・スイッチ状態・$\Delta t_k$ を更新
3. 各軸でEKF予測
4. 保持/除外/ゼロ注入/ロバスト判定を適用
5. 許可された場合のみEKF観測更新
6. XY周波数融合と共有注入
7. $\Delta p$ 先の予測外力 $\hat{\mathbf{f}}_{k+\Delta p}$ を算出
8. 補正角 $(\phi,\theta,\psi)$ と補正クォータニオン $\mathbf{q}_c$ を生成
9. ログ出力

## 10. 実務上の解釈

- この推定器は、単純な「EKF一発更新」ではなく、運用上の異常値・低励振・スイッチ操作を含む条件分岐付き非線形推定器である。
- よってチューニングでは、$\mathbf{Q},R$ の調整に加え、保持閾値・除外閾値・NIS閾値・共有注入係数を同時に設計する必要がある。
- 発散回避の観点では、低SNR領域のゼロ注入、NISベース拒否、有限値チェック後の安全リセットが主要な安定化機構である。

## 11. 参考文献 (記法と構成の基準)

1. R. E. Kalman, "A New Approach to Linear Filtering and Prediction Problems," 1960.
2. EKF標準形式 (非線形状態方程式の一次線形化) に基づく記述。
3. 科学技術文書の一般構成 (目的・方法・アルゴリズム・解釈の分離) に準拠。

## 12. 補足Q&A (最小限)

Q. なぜ周波数をXYで共有するのか。  
A. 単軸で低励振・低信頼になった際、他軸の信頼情報を利用して周波数推定の破綻を防ぐためである。

Q. なぜ観測をゼロ注入するのか。  
A. 低振幅時に観測ノイズ主導の更新となることを防ぎ、状態の過大振動を抑えるためである。
