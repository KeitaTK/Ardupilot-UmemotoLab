#!/usr/bin/env python3
"""
Simplified visualization: Measurement vs EKF estimation
Compare current implementation (R×1000+K constraint) vs new measurement-zero strategy
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# EKF parameters
Q = np.diag([0.02, 0.05, 0.001, 0.0005])
R_base = 0.08
dt = 0.01
omega_true = 2.1991  # rad/s
force_threshold = 0.0

# Test scenario: 3 phases
def make_signal(t_array, amp_low=0.05, amp_normal=0.5):
    """Synthetic signal generation"""
    signal = np.zeros_like(t_array)
    for i, t in enumerate(t_array):
        if t < 10.0:
            amp = amp_normal
        elif t < 20.0:
            amp = amp_low
        else:
            amp = amp_normal
        signal[i] = amp * np.sin(omega_true * t)
    return signal

def state_transition(x, dt, omega):
    """Discrete state transition"""
    d, dd, c, w = x
    d_next = d + dd * dt
    dd_next = dd - omega**2 * d * dt
    c_next = c
    w_next = w
    return np.array([d_next, dd_next, c_next, w_next])

def ekf_predict(x, P, dt, omega, Q):
    """EKF prediction step"""
    x_pred = state_transition(x, dt, omega)
    F = np.array([
        [1.0, dt, 0.0, 0.0],
        [-omega**2 * dt, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]
    ])
    P_pred = F @ P @ F.T + Q
    return x_pred, P_pred

def ekf_update_current(x, P, z, R, force_hold):
    """Current implementation (R×1000 + K constraint)"""
    H = np.array([1.0, 0.0, 1.0, 0.0])
    y_pred = H @ x
    innov = z - y_pred
    
    if force_hold:
        R_eff = R * 1000.0
    else:
        R_eff = R
    
    S = H @ P @ H.T + R_eff
    if S < 1e-6:
        return x, P
    
    K = P @ H.T / S
    
    if force_hold:
        K[0] = np.clip(K[0], -0.01, 0.01)
        K[1] = np.clip(K[1], -0.01, 0.01)
        K[2] = np.clip(K[2], -0.01, 0.01)
    
    x_new = x + K * innov
    
    I_KH = np.eye(4) - np.outer(K, H)
    P_new = I_KH @ P @ I_KH.T + R_eff * np.outer(K, K)
    
    return x_new, P_new

def ekf_update_measurement_zero(x, P, z, R, force_hold):
    """New proposal: measurement zero forcing"""
    H = np.array([1.0, 0.0, 1.0, 0.0])
    y_pred = H @ x
    
    if force_hold:
        z_eff = 0.0
    else:
        z_eff = z
    
    innov = z_eff - y_pred
    S = H @ P @ H.T + R
    if S < 1e-6:
        return x, P
    
    K = P @ H.T / S
    x_new = x + K * innov
    
    I_KH = np.eye(4) - np.outer(K, H)
    P_new = I_KH @ P @ I_KH.T + R * np.outer(K, K)
    
    return x_new, P_new

# Run simulation
t_end = 50.0
dt = 0.01
t_array = np.arange(0, t_end + dt, dt)
n_steps = len(t_array)

signal_true = make_signal(t_array)
np.random.seed(42)
measurement = signal_true + np.random.normal(0, np.sqrt(R_base), n_steps)

x0 = np.array([0.0, 0.0, 0.0, omega_true])
P0 = np.eye(4) * 0.1

results = {}

for method_name, ekf_update_func in [
    ('current', ekf_update_current),
    ('measurement_zero', ekf_update_measurement_zero),
]:
    x = x0.copy()
    P = P0.copy()
    x_hist = np.zeros((n_steps, 4))
    
    for i in range(n_steps):
        t = t_array[i]
        force_hold = (t >= 10.0 and t < 20.0)
        
        x, P = ekf_predict(x, P, dt, omega_true, Q)
        z = measurement[i]
        x, P = ekf_update_func(x, P, z, R_base, force_hold)
        x_hist[i] = x
    
    results[method_name] = x_hist

# Create simplified figure
fig, axes = plt.subplots(2, 1, figsize=(14, 8))
fig.suptitle('Deadband Region: Measurement vs EKF Estimation', fontsize=14, fontweight='bold')

# Plot 1: Current implementation
ax = axes[0]
ax.plot(t_array, signal_true, 'k--', linewidth=2.5, label='True Signal', alpha=0.8, zorder=10)
ax.plot(t_array, measurement, 'gray', linewidth=1, alpha=0.5, label='Measurement (w/ noise)', zorder=5)
ax.plot(t_array, results['current'][:, 0], 'b-', linewidth=2, label='EKF Estimate (Current: R×1000+K constraint)', zorder=8)

# Mark deadband region
ax_rect1 = Rectangle((10, -0.8), 10, 1.6, alpha=0.15, color='orange')
ax.add_patch(ax_rect1)
ax.text(15, 0.65, 'Deadband\nRegion', fontsize=10, ha='center', fontweight='bold', alpha=0.6)

ax.set_ylabel('Displacement [N]', fontsize=11)
ax.set_title('Current Implementation: R×1000 + K Constraint', fontsize=12, fontweight='bold')
ax.legend(loc='upper right', fontsize=10)
ax.grid(True, alpha=0.3)
ax.set_xlim([0, 50])
ax.set_ylim([-0.8, 0.8])

# Plot 2: New measurement-zero strategy
ax = axes[1]
ax.plot(t_array, signal_true, 'k--', linewidth=2.5, label='True Signal', alpha=0.8, zorder=10)
ax.plot(t_array, measurement, 'gray', linewidth=1, alpha=0.5, label='Measurement (w/ noise)', zorder=5)
ax.plot(t_array, results['measurement_zero'][:, 0], 'g-', linewidth=2, label='EKF Estimate (New: Measurement = 0 in Deadband)', zorder=8)

# Mark deadband region
ax_rect2 = Rectangle((10, -0.8), 10, 1.6, alpha=0.15, color='orange')
ax.add_patch(ax_rect2)
ax.text(15, 0.65, 'Deadband\nRegion', fontsize=10, ha='center', fontweight='bold', alpha=0.6)

ax.set_xlabel('Time [s]', fontsize=11)
ax.set_ylabel('Displacement [N]', fontsize=11)
ax.set_title('New Strategy: Measurement Zero Forcing (z = 0.0 in Deadband)', fontsize=12, fontweight='bold')
ax.legend(loc='upper right', fontsize=10)
ax.grid(True, alpha=0.3)
ax.set_xlim([0, 50])
ax.set_ylim([-0.8, 0.8])

plt.tight_layout()
plt.savefig('/home/memoto/Ardupilot-UmemotoLab/analysis/deadband_measurement_zero_comparison_simplified.png', dpi=150, bbox_inches='tight')
print("✅ Simplified figure saved: analysis/deadband_measurement_zero_comparison_simplified.png")

# Print summary statistics
print("\n" + "="*70)
print("Performance Comparison (Deadband Region: 10-20s)")
print("="*70)

idx_start = int(10 / dt)
idx_end = int(20 / dt)
phase_slice = slice(idx_start, idx_end)

for method_name, label in [('current', 'Current (R×1000+K constraint)'), 
                            ('measurement_zero', 'New (Measurement = 0)')]:
    d_est = results[method_name][phase_slice, 0]
    d_true = signal_true[phase_slice]
    
    rmse = np.sqrt(np.mean((d_est - d_true)**2))
    max_error = np.max(np.abs(d_est - d_true))
    overshoot = np.max(np.abs(d_est)) / (np.max(np.abs(d_true)) + 1e-6)
    
    print(f"\n{label}:")
    print(f"  RMSE: {rmse:.4f}")
    print(f"  Max Error: {max_error:.4f}")
    print(f"  Overshoot Ratio: {overshoot:.2f}x")

# Improvement
rmse_current = np.sqrt(np.mean((results['current'][phase_slice, 0] - signal_true[phase_slice])**2))
rmse_zero = np.sqrt(np.mean((results['measurement_zero'][phase_slice, 0] - signal_true[phase_slice])**2))
improvement = (1 - rmse_zero / rmse_current) * 100

print(f"\nImprovement: {improvement:.1f}% RMSE reduction")
print("="*70)
