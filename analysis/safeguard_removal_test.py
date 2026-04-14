#!/usr/bin/env python3
"""
違反テスト: 安全策なしの EKF リプレイシミュレーション

現行実装の以下部分を除外した場合の挙動をシミュレート:
1. R *= 1000.0 (低振幅ノイズ拡大)
2. K[0,1,2] 制約 [-0.01, 0.01] (低振幅ゲイン制限)

既定パラメータで実行し、以下について可視化:
- 推定振幅の暴走判定
- 共分散の成長
- Kalman ゲイン K の大きさ
- 実測との乖離（RMSE）
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ========== 現行パラメータ（既定値） ==========
# from AP_Observer.cpp
dt = 0.01  # 100 Hz
omega_min = 2.1991
omega_max = 5.7180
omega_init = 3.7699
dt_min, dt_max = 0.001, 0.05

# Process noise
q_d = 0.02
q_ddot = 0.05
q_c = 0.001
q_omega = 0.0005

# Measurement noise
r_meas = 0.08

# Force thresholds
force_hold_max = 0.0
force_reject_min = 5.0

# Energy gate (defaults)
energy_gate_enabled = True
energy_rms_on = 0.20
energy_rms_off = 0.16

# EKF state size
state_size = 4  # [d, d_dot, c, omega]

# ========== Helper functions ==========

def discrete_state_transition(d, d_dot, c, omega, dt):
    """Simple harmonic oscillator forward Euler."""
    d_new = d + dt * d_dot
    d_dot_new = d_dot - dt * (omega**2) * d
    c_new = c
    omega_new = omega
    return np.array([d_new, d_dot_new, c_new, omega_new])

def ekf_predict(x, P, dt, q_d, q_ddot, q_c, q_omega):
    """EKF prediction step."""
    omega = x[3]
    F = np.array([
        [1.0, dt, 0.0, 0.0],
        [-dt * omega**2, 1.0, 0.0, -2.0 * dt * omega * x[0]],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]
    ])
    Q = np.diag([q_d, q_ddot, q_c, q_omega])
    x_pred = F @ x
    P_pred = F @ P @ F.T + Q
    return x_pred, P_pred, F

def ekf_update_normal(x_pred, P_pred, measurement, r_meas):
    """Normal EKF update (no safeguards)."""
    H = np.array([1.0, 0.0, 1.0, 0.0])
    innov = measurement - (x_pred[0] + x_pred[2])
    PHt = P_pred @ H
    S = H @ PHt + r_meas
    if not np.isfinite(S) or abs(S) < 1e-6:
        return x_pred, P_pred, 0.0, 0.0
    K = PHt / S
    nis = innov**2 / S if S > 1e-6 else 1e10
    x_new = x_pred + K * innov
    I_KH = np.eye(state_size) - np.outer(K, H)
    P_new = I_KH @ P_pred
    return x_new, P_new, innov, nis

def ekf_update_safeguarded(x_pred, P_pred, measurement, r_meas, force_hold_omega):
    """EKF update WITH safety measures."""
    H = np.array([1.0, 0.0, 1.0, 0.0])
    innov = measurement - (x_pred[0] + x_pred[2])
    
    # 対策1: R を拡大
    R_eff = r_meas
    if force_hold_omega:
        R_eff *= 1000.0
    
    PHt = P_pred @ H
    S = H @ PHt + R_eff
    if not np.isfinite(S) or abs(S) < 1e-6:
        return x_pred, P_pred, 0.0, 0.0, PHt[0] / (r_meas + 1e-10)
    
    K = PHt / S
    
    # 対策2: K を制約（低振幅時のみ）
    K_before_constraint = K.copy()
    if force_hold_omega:
        K[0] = np.clip(K[0], -0.01, 0.01)
        K[1] = np.clip(K[1], -0.01, 0.01)
        K[2] = np.clip(K[2], -0.01, 0.01)
    K[3] = 0.0  # omega 常に固定
    
    nis = innov**2 / S if S > 1e-6 else 1e10
    x_new = x_pred + K * innov
    x_new[3] = x_pred[3]  # omega は復帰（hold_omega なので同じ）
    
    I_KH = np.eye(state_size) - np.outer(K, H)
    P_new = I_KH @ P_pred
    return x_new, P_new, innov, nis, K[0]

# ========== Test Cases (simplified synthetic data) ==========

# Test profile: 0.45 Hz signal, variable amplitude
target_freq = 0.45  # Hz
omega_true = 2.0 * np.pi * target_freq

num_steps = 5000
amp_profile = np.zeros(num_steps)

# Phase 1: Normal amplitude (0-1000 steps)
amp_profile[0:1000] = 0.5

# Phase 2: Low amplitude / energy gate OFF (1000-2000 steps)
amp_profile[1000:2000] = 0.05

# Phase 3: Recovery to normal (2000-5000 steps)
amp_profile[2000:5000] = 0.5

# Generate noisy measurements
np.random.seed(42)
true_signal = np.zeros(num_steps)
measurement_noise = np.random.normal(0, np.sqrt(r_meas), num_steps)

for t in range(num_steps):
    true_signal[t] = amp_profile[t] * np.sin(omega_true * dt * t)

measurements = true_signal + measurement_noise

# ========== Simulation ==========

# Initialize states
x_normal = np.array([0.1, 0.0, 0.0, omega_init])
P_normal = np.diag([0.01, 0.01, 0.01, 1e-6])

x_safeguarded = x_normal.copy()
P_safeguarded = P_normal.copy()

# History
history_normal = {
    'x_d': [], 'x_d_dot': [], 'K0': [], 'P00': [], 'innov': [], 'nis': []
}
history_safeguarded = {
    'x_d': [], 'x_d_dot': [], 'K0': [], 'P00': [], 'innov': [], 'nis': []
}

for t in range(num_steps):
    force_abs = abs(measurements[t])
    force_hold_omega = force_abs <= force_hold_max
    
    # Predict
    x_pred_n, P_pred_n, _ = ekf_predict(x_normal, P_normal, dt, q_d, q_ddot, q_c, q_omega)
    x_pred_s, P_pred_s, _ = ekf_predict(x_safeguarded, P_safeguarded, dt, q_d, q_ddot, q_c, q_omega)
    
    # Update (with and without safeguards)
    x_new_n, P_new_n, innov_n, nis_n = ekf_update_normal(
        x_pred_n, P_pred_n, measurements[t], r_meas
    )
    
    x_new_s, P_new_s, innov_s, nis_s, K0_s_applied = ekf_update_safeguarded(
        x_pred_s, P_pred_s, measurements[t], r_meas, force_hold_omega
    )
    
    # Kalman gain snapshot for normal (without safeguards)
    H = np.array([1.0, 0.0, 1.0, 0.0])
    PHt_n = P_pred_n @ H
    S_n = H @ PHt_n + r_meas
    K0_n = PHt_n[0] / (S_n + 1e-10)
    
    # Store
    history_normal['x_d'].append(x_new_n[0])
    history_normal['x_d_dot'].append(x_new_n[1])
    history_normal['K0'].append(K0_n)
    history_normal['P00'].append(P_new_n[0, 0])
    history_normal['innov'].append(innov_n)
    history_normal['nis'].append(nis_n)
    
    history_safeguarded['x_d'].append(x_new_s[0])
    history_safeguarded['x_d_dot'].append(x_new_s[1])
    history_safeguarded['K0'].append(K0_s_applied)
    history_safeguarded['P00'].append(P_new_s[0, 0])
    history_safeguarded['innov'].append(innov_s)
    history_safeguarded['nis'].append(nis_s)
    
    # Update states
    x_normal = x_new_n
    P_normal = P_new_n
    x_safeguarded = x_new_s
    P_safeguarded = P_new_s

# ========== Plotting ==========

fig, axes = plt.subplots(3, 2, figsize=(15, 12))

t_steps = np.arange(num_steps) * dt

# Row 1: Estimated amplitude
axes[0, 0].plot(t_steps, true_signal, 'g-', linewidth=1, label='True signal', alpha=0.7)
axes[0, 0].plot(t_steps, history_normal['x_d'], 'r-', linewidth=2, label='Without safeguards')
axes[0, 0].axvspan(10, 20, alpha=0.2, color='orange', label='Low amplitude region')
axes[0, 0].set_ylabel('Amplitude d', fontsize=11)
axes[0, 0].set_title('Estimated Amplitude (WITHOUT safeguards)', fontweight='bold')
axes[0, 0].grid(True, alpha=0.3)
axes[0, 0].legend()

axes[0, 1].plot(t_steps, true_signal, 'g-', linewidth=1, label='True signal', alpha=0.7)
axes[0, 1].plot(t_steps, history_safeguarded['x_d'], 'b-', linewidth=2, label='WITH safeguards')
axes[0, 1].axvspan(10, 20, alpha=0.2, color='orange')
axes[0, 1].set_ylabel('Amplitude d', fontsize=11)
axes[0, 1].set_title('Estimated Amplitude (WITH safeguards)', fontweight='bold')
axes[0, 1].grid(True, alpha=0.3)
axes[0, 1].legend()

# Row 2: Kalman Gain K[0]
axes[1, 0].plot(t_steps, history_normal['K0'], 'r-', linewidth=1.5)
axes[1, 0].axhline(y=0.01, color='orange', linestyle='--', linewidth=2, label='Safety limit (±0.01)')
axes[1, 0].axhline(y=-0.01, color='orange', linestyle='--', linewidth=2)
axes[1, 0].axvspan(10, 20, alpha=0.2, color='orange')
axes[1, 0].set_ylabel('Kalman Gain K[0,d]', fontsize=11)
axes[1, 0].set_title('Gain WITHOUT safeguards (can spike)', fontweight='bold')
axes[1, 0].grid(True, alpha=0.3)
axes[1, 0].legend()
axes[1, 0].set_ylim([-0.5, 1.0])

axes[1, 1].plot(t_steps, history_safeguarded['K0'], 'b-', linewidth=1.5)
axes[1, 1].axhline(y=0.01, color='orange', linestyle='--', linewidth=2, label='Safety limit (±0.01)')
axes[1, 1].axhline(y=-0.01, color='orange', linestyle='--', linewidth=2)
axes[1, 1].axvspan(10, 20, alpha=0.2, color='orange')
axes[1, 1].set_ylabel('Kalman Gain K[0,d]', fontsize=11)
axes[1, 1].set_title('Gain WITH safeguards (clamped)', fontweight='bold')
axes[1, 1].grid(True, alpha=0.3)
axes[1, 1].legend()
axes[1, 1].set_ylim([-0.5, 1.0])

# Row 3: Covariance P[0,0]
axes[2, 0].semilogy(t_steps, history_normal['P00'], 'r-', linewidth=2, label='P[0,0]')
axes[2, 0].axvspan(10, 20, alpha=0.2, color='orange', label='Low amp region')
axes[2, 0].set_ylabel('P[0,0] (log)', fontsize=11)
axes[2, 0].set_xlabel('Time [s]', fontsize=11)
axes[2, 0].set_title('Covariance WITHOUT safeguards (grows)', fontweight='bold')
axes[2, 0].grid(True, which='both', alpha=0.3)
axes[2, 0].legend()

axes[2, 1].semilogy(t_steps, history_safeguarded['P00'], 'b-', linewidth=2, label='P[0,0]')
axes[2, 1].axvspan(10, 20, alpha=0.2, color='orange', label='Low amp region')
axes[2, 1].set_ylabel('P[0,0] (log)', fontsize=11)
axes[2, 1].set_xlabel('Time [s]', fontsize=11)
axes[2, 1].set_title('Covariance WITH safeguards (controlled)', fontweight='bold')
axes[2, 1].grid(True, which='both', alpha=0.3)
axes[2, 1].legend()

plt.tight_layout()
plt.savefig('/home/memoto/Ardupilot-UmemotoLab/analysis/safeguard_removal_test.png', dpi=150)
print("✓ Plot saved: analysis/safeguard_removal_test.png")

# ========== Summary statistics ==========

print("\n=== 統計比較（安全策なし vs あり） ===\n")

# Region 1: Normal
r1_slice = slice(0, 1000)
rmse_normal_r1 = np.sqrt(np.mean((np.array(history_normal['x_d'])[r1_slice] - true_signal[r1_slice])**2))
rmse_safe_r1 = np.sqrt(np.mean((np.array(history_safeguarded['x_d'])[r1_slice] - true_signal[r1_slice])**2))
print(f"Region 1 (0-10s, Normal amplitude):")
print(f"  Without safeguards: RMSE = {rmse_normal_r1:.4f}")
print(f"  With safeguards:    RMSE = {rmse_safe_r1:.4f}")
print(f"  Difference:         {rmse_normal_r1 - rmse_safe_r1:.4f}")

# Region 2: Low amplitude
r2_slice = slice(1000, 2000)
rmse_normal_r2 = np.sqrt(np.mean((np.array(history_normal['x_d'])[r2_slice] - true_signal[r2_slice])**2))
rmse_safe_r2 = np.sqrt(np.mean((np.array(history_safeguarded['x_d'])[r2_slice] - true_signal[r2_slice])**2))
max_amp_normal_r2 = np.max(np.abs(history_normal['x_d'])[r2_slice])
max_amp_safe_r2 = np.max(np.abs(history_safeguarded['x_d'])[r2_slice])
print(f"\nRegion 2 (10-20s, Low amplitude / Energy gate OFF):")
print(f"  Without safeguards: RMSE = {rmse_normal_r2:.4f}, Max |d| = {max_amp_normal_r2:.4f}")
print(f"  With safeguards:    RMSE = {rmse_safe_r2:.4f}, Max |d| = {max_amp_safe_r2:.4f}")
print(f"  RMSE degradation:   {rmse_normal_r2 - rmse_safe_r2:.4f}")
print(f"  ⚠️  Amplitude overshoot without safeguards: {max_amp_normal_r2 / 0.05 if 0.05 > 0 else float('inf'):.1f}x (true=0.05)")

# Region 3: Recovery
r3_slice = slice(2000, 5000)
rmse_normal_r3 = np.sqrt(np.mean((np.array(history_normal['x_d'])[r3_slice] - true_signal[r3_slice])**2))
rmse_safe_r3 = np.sqrt(np.mean((np.array(history_safeguarded['x_d'])[r3_slice] - true_signal[r3_slice])**2))
print(f"\nRegion 3 (20-50s, Recovery to normal amplitude):")
print(f"  Without safeguards: RMSE = {rmse_normal_r3:.4f}")
print(f"  With safeguards:    RMSE = {rmse_safe_r3:.4f}")
print(f"  Difference:         {rmse_normal_r3 - rmse_safe_r3:.4f}")

# Kalman gain statistics
max_K_normal = np.max(np.abs(history_normal['K0']))
max_K_safe = np.max(np.abs(history_safeguarded['K0']))
print(f"\nKalman Gain K[0] Peak:")
print(f"  Without safeguards: max K = {max_K_normal:.4f}")
print(f"  With safeguards:    max K = {max_K_safe:.4f}")
print(f"  Reduction:          {(1 - max_K_safe/max_K_normal)*100:.1f}%")

print("\n✓ Test completed.")
