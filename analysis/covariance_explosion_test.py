#!/usr/bin/env python3
"""
Test: predict-only フェーズでの共分散無限増加リスク検証

シナリオ1: predict-only が 1000ステップ連続 → その後観測更新
シナリオ2: predict-only が 10000ステップ連続 → その後観測更新

共分散 P[0][0]（振幅の不確実性）がどう増加し、
Kalman ゲイン K[0] が どの程度サイズになるかを検証
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

# EKF パラメータ（AP_Observer から引用）
state_size = 4  # [d, d_dot, c, omega]
dt = 0.01  # サンプル時間

# 初期状態
omega = 2.0 * np.pi * 0.45  # 0.45 Hz → rad/s
d_init = 0.1
d_dot_init = 0.0
c_init = 0.0
x = np.array([d_init, d_dot_init, c_init, omega])

# 初期共分散
P_init = np.diag([0.01, 0.01, 0.01, 1e-6])
P = P_init.copy()

# プロセスノイズ分散
q_d = 1e-6
q_ddot = 1e-6
q_c = 1e-6
q_omega = 0.0  # SW OFF またはエネルギーゲート OFF 時

# 測定ノイズ
R = 0.01

# 検証用配列
num_steps = 2000
P00_history = []
K0_history = []
innov_history = []
x0_history = []

# シミュレーション
for step in range(num_steps):
    # 状態遷移（EKF 予測ステップ）
    F = np.array([
        [1.0, dt, 0.0, 0.0],
        [-dt * omega**2, 1.0, 0.0, -2.0 * dt * omega * x[0]],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]
    ])
    
    # 予測状態
    x_pred = F @ x
    x_pred[3] = omega  # 周波数固定（hold_omega）
    
    # 共分散の予測進化
    Q = np.diag([q_d, q_ddot, q_c, q_omega])
    P_pred = F @ P @ F.T + Q
    
    # フェーズ判定
    if step < 1000:
        # フェーズ1: predict-only が 1000 ステップ連続
        # （SW OFF またはエネルギーゲート OFF）
        phase = "predict-only (1000 steps)"
        x = x_pred
        P = P_pred
        
    elif step < 1050:
        # フェーズ2: 観測更新に戻る（50ステップだけ）
        phase = "observation update"
        x = x_pred
        P = P_pred
        
        # 管測値（ノイズ加算）
        y_true = x_pred[0] + x_pred[2]
        measurement = y_true + np.random.randn() * 0.05
        
        # 観測行列 H = [1 0 1 0]（d + c を観測）
        H = np.array([1.0, 0.0, 1.0, 0.0])
        PHt = (P @ H).reshape(-1, 1)
        
        # 観測更新
        innov = measurement - (x_pred[0] + x_pred[2])
        S = (H @ P_pred @ H.T + R).item()
        K = PHt / (S + 1e-10)
        
        # 状態更新
        x = x_pred + K.flatten() * innov
        x[3] = omega  # 周波数は固定
        
        # 共分散更新
        I_KH = np.eye(state_size) - K @ H.reshape(1, -1)
        P = I_KH @ P_pred
        
        K0_history.append(K[0].item())
        innov_history.append(innov)
        
    else:
        # フェーズ3: predict-only がさらに 950 ステップ
        phase = "predict-only (again 950 steps)"
        x = x_pred
        P = P_pred
    
    # 記録
    P00_history.append(P[0, 0])
    x0_history.append(x[0])
    
    if step % 200 == 0:
        print(f"Step {step:4d} ({phase:25s}): P[0,0]={P[0,0]:10.4f}, "
              f"x[0]={x[0]:8.4f}, K[0]={K0_history[-1] if K0_history else 0.0:8.4f}")

# グラフ化
fig, axes = plt.subplots(3, 1, figsize=(12, 10))

axes[0].plot(P00_history, label='P[0,0] (振幅の分散)', linewidth=2)
axes[0].axvline(x=1000, color='r', linestyle='--', label='predict-only → observation')
axes[0].axvline(x=1050, color='orange', linestyle='--', label='observation → predict-only')
axes[0].set_ylabel('P[0,0] (分散)', fontsize=11)
axes[0].set_xlabel('ステップ数')
axes[0].set_title('predict-only フェーズでの共分散爆発リスク検証', fontsize=12, fontweight='bold')
axes[0].grid(True, alpha=0.3)
axes[0].legend()

axes[1].plot(x0_history, label='推定振幅 x[0]', linewidth=2)
axes[1].axvline(x=1000, color='r', linestyle='--')
axes[1].axvline(x=1050, color='orange', linestyle='--')
axes[1].set_ylabel('推定振幅 x[0]', fontsize=11)
axes[1].set_xlabel('ステップ数')
axes[1].grid(True, alpha=0.3)
axes[1].legend()

if K0_history:
    axes[2].plot(range(1000, 1050), K0_history, marker='o', label='Kalman Gain K[0]', linewidth=2)
    axes[2].axhline(y=0.99, color='r', linestyle='--', label='危険閾値 (0.99)')
    axes[2].set_ylabel('Kalman Gain K[0]', fontsize=11)
    axes[2].set_xlabel('ステップ数')
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

plt.tight_layout()
plt.savefig('/home/memoto/Ardupilot-UmemotoLab/analysis/covariance_explosion_test_results.png', dpi=150)
print(f"\n✓ Results saved to: analysis/covariance_explosion_test_results.png")

# 統計情報
print(f"\n=== 統計情報 ===")
print(f"初期 P[0,0]:      {P00_history[0]:10.6f}")
print(f"predict-only後:   {P00_history[999]:10.6f}")
print(f"最大 P[0,0]:      {max(P00_history):10.6f}")
print(f"P[0,0] 増加率:    {max(P00_history) / P00_history[0]:8.1f}倍")
if K0_history:
    print(f"\n観測更新時のK[0]:")
    print(f"  最小値: {min(K0_history):8.4f}")
    print(f"  最大値: {max(K0_history):8.4f}")
    print(f"  平均値: {np.mean(K0_history):8.4f}")
