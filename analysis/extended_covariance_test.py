#!/usr/bin/env python3
"""
Extended Test: predict-only が **非常に長く** 続く場合のリスク検証

シナリオ：
- predict-only が 100,000 ステップ（約16分）連続
- その後観測更新に戻る
- さらに長期的な共分散成長を検証
"""

import numpy as np
import matplotlib.pyplot as plt

state_size = 4
dt = 0.01
omega = 2.0 * np.pi * 0.45

# 初期状態
x = np.array([0.1, 0.0, 0.0, omega])
P = np.diag([0.01, 0.01, 0.01, 1e-6])

# パラメータ
q_d = 1e-6
q_ddot = 1e-6
q_c = 1e-6
q_omega = 0.0
R = 0.01

# より長いシミュレーション
num_steps = 3000
predict_only_duration = 2000  # 長い predict-only フェーズ

P00_history = []
P11_history = []
K0_history = []

for step in range(num_steps):
    # 状態遷移
    F = np.array([
        [1.0, dt, 0.0, 0.0],
        [-dt * omega**2, 1.0, 0.0, -2.0 * dt * omega * x[0]],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]
    ])
    
    x_pred = F @ x
    x_pred[3] = omega
    
    Q = np.diag([q_d, q_ddot, q_c, q_omega])
    P_pred = F @ P @ F.T + Q
    
    if step < predict_only_duration:
        # predict-only: 観測更新なし
        x = x_pred
        P = P_pred
    else:
        # 観測更新フェーズ
        x = x_pred
        P = P_pred
        
        # 観測値（ノイズ加算）
        y_true = x_pred[0] + x_pred[2]
        measurement = y_true + np.random.randn() * 0.05
        
        # 観測更新
        H = np.array([1.0, 0.0, 1.0, 0.0])
        PHt = (P @ H).reshape(-1, 1)
        innov = measurement - (x_pred[0] + x_pred[2])
        S = (H @ P_pred @ H.T + R).item()
        K = PHt / (S + 1e-10)
        
        # 状態更新
        x = x_pred + K.flatten() * innov
        x[3] = omega
        
        # 共分散更新（Joseph form）
        I_KH = np.eye(state_size) - K @ H.reshape(1, -1)
        P = I_KH @ P_pred
        
        K0_history.append(K[0].item())
    
    P00_history.append(P[0, 0])
    P11_history.append(P[1, 1])
    
    if step % 500 == 0:
        status = "predict-only" if step < predict_only_duration else "observation"
        print(f"Step {step:5d} ({status:15s}): P[0,0]={P[0,0]:12.6f}, "
              f"P[1,1]={P[1,1]:12.6f}, K[0]={K0_history[-1] if K0_history else 0.0:8.4f}")

# 統計情報
print(f"\n=== 詳細統計 ===")
print(f"predict-only フェーズ (0-{predict_only_duration-1} ステップ):")
print(f"  初期 P[0,0]:      {P00_history[0]:12.6f}")
print(f"  最終 P[0,0]:      {P00_history[predict_only_duration-1]:12.6f}")
print(f"  増加率:           {P00_history[predict_only_duration-1] / P00_history[0]:8.2f}倍")
print(f"  最大 P[0,0]:      {max(P00_history[:predict_only_duration]):12.6f}")

print(f"\n観測更新フェーズ ({predict_only_duration}-{num_steps-1} ステップ):")
if K0_history:
    print(f"  Kalman Gain K[0]:")  
    print(f"    最小値: {min(K0_history):8.4f}")
    print(f"    最大値: {max(K0_history):8.4f}")
    print(f"    平均値: {np.mean(K0_history):8.4f}")
    print(f"    危険値 (K > 0.5) 発生回数: {sum(1 for k in K0_history if k > 0.5)}")

# グラフ化
fig, axes = plt.subplots(2, 1, figsize=(14, 10))

# P[0,0] の時間進化
axes[0].semilogy(P00_history, linewidth=2, label='P[0,0] (log scale)')
axes[0].axvline(x=predict_only_duration, color='r', linestyle='--', linewidth=2, 
                label=f'predict-only → observation (step {predict_only_duration})')
axes[0].set_ylabel('P[0,0] (分散)', fontsize=11)
axes[0].set_xlabel('ステップ数')
axes[0].set_title(f'Extended Test: predict-only {predict_only_duration} steps + observation', 
                  fontsize=12, fontweight='bold')
axes[0].grid(True, which='both', alpha=0.3)
axes[0].legend(fontsize=10)

# P[1,1] の時間進化
axes[1].semilogy(P11_history, linewidth=2, label='P[1,1] (velocity variance)')
axes[1].axvline(x=predict_only_duration, color='r', linestyle='--', linewidth=2)
axes[1].axhline(y=1.0, color='orange', linestyle=':', label='警告閾値 (1.0)')
axes[1].set_ylabel('P[1,1] (分散)', fontsize=11)
axes[1].set_xlabel('ステップ数')
axes[1].grid(True, which='both', alpha=0.3)
axes[1].legend(fontsize=10)

plt.tight_layout()
plt.savefig('/home/memoto/Ardupilot-UmemotoLab/analysis/extended_covariance_test_results.png', dpi=150)
print(f"\n✓ Results saved to: analysis/extended_covariance_test_results.png")

# 増加率の詳細分析
print(f"\n=== 増加率分析（predict-only フェーズ） ===")
segment_size = 200
for i in range(0, predict_only_duration, segment_size):
    end = min(i + segment_size, predict_only_duration)
    if i < len(P00_history):
        ratio = P00_history[end-1] / (P00_history[i] + 1e-10)
        print(f"  Segment {i:5d}-{end:5d}: P[0,0] 増加率 = {ratio:6.3f}倍")
