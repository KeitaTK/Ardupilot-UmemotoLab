#!/usr/bin/env python3
"""
デッドバンド内で観測値を0に固定する提案の検証シミュレーション

3つのアプローチを比較：
1. 現行実装（R×1000 + K制約）
2. 安全策なし（baseline）
3. 観測値0強制案（新提案）
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# EKF パラメータ
Q = np.diag([0.02, 0.05, 0.001, 0.0005])
R_base = 0.08
dt = 0.01
omega_true = 2.1991  # rad/s (0.35 Hz)
force_threshold = 0.0  # N (always in deadband for low-amplitude)

# テストシナリオ：3フェーズ
# Phase 1 (0-10s):  振幅0.5N（通常）
# Phase 2 (10-20s): 振幅0.05N（低振幅 → デッドバンド）← テスト区間
# Phase 3 (20-50s): 振幅0.5N（復帰）

def make_signal(t_array, amp_low=0.05, amp_normal=0.5):
    """合成信号の生成"""
    signal = np.zeros_like(t_array)
    for i, t in enumerate(t_array):
        if t < 10.0:
            # Phase 1: 通常振幅
            amp = amp_normal
        elif t < 20.0:
            # Phase 2: 低振幅
            amp = amp_low
        else:
            # Phase 3: 復帰
            amp = amp_normal
        signal[i] = amp * np.sin(omega_true * t)
    return signal

def state_transition(x, dt, omega):
    """離散状態遷移 (前進Euler)"""
    d, dd, c, w = x
    d_next = d + dd * dt
    dd_next = dd - omega**2 * d * dt
    c_next = c
    w_next = w
    return np.array([d_next, dd_next, c_next, w_next])

def ekf_predict(x, P, dt, omega, Q):
    """EKF予測ステップ"""
    x_pred = state_transition(x, dt, omega)
    
    # ヤコビ行列 F
    F = np.array([
        [1.0, dt, 0.0, 0.0],
        [-omega**2 * dt, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]
    ])
    
    P_pred = F @ P @ F.T + Q
    return x_pred, P_pred

def ekf_update_current(x, P, z, R, force_hold):
    """現行実装（R×1000 + K制約）"""
    # 観測モデル: y = d + c
    H = np.array([1.0, 0.0, 1.0, 0.0])
    y_pred = H @ x
    innov = z - y_pred
    
    # 低振幅時：R を1000倍に
    if force_hold:
        R_eff = R * 1000.0
    else:
        R_eff = R
    
    S = H @ P @ H.T + R_eff
    if S < 1e-6:
        return x, P, innov, 0.0
    
    K = P @ H.T / S
    
    # ゲイン制約
    if force_hold:
        K[0] = np.clip(K[0], -0.01, 0.01)
        K[1] = np.clip(K[1], -0.01, 0.01)
        K[2] = np.clip(K[2], -0.01, 0.01)
    
    x_new = x + K * innov
    
    # ジョセフ型共分散更新
    I_KH = np.eye(4) - np.outer(K, H)
    P_new = I_KH @ P @ I_KH.T + R_eff * np.outer(K, K)
    
    return x_new, P_new, innov, K[0]

def ekf_update_no_safeguard(x, P, z, R, force_hold):
    """安全策なし（baseline）"""
    H = np.array([1.0, 0.0, 1.0, 0.0])
    y_pred = H @ x
    innov = z - y_pred
    
    S = H @ P @ H.T + R
    if S < 1e-6:
        return x, P, innov, 0.0
    
    K = P @ H.T / S
    x_new = x + K * innov
    
    I_KH = np.eye(4) - np.outer(K, H)
    P_new = I_KH @ P @ I_KH.T + R * np.outer(K, K)
    
    return x_new, P_new, innov, K[0]

def ekf_update_measurement_zero(x, P, z, R, force_hold):
    """観測値0強制案（新提案）"""
    H = np.array([1.0, 0.0, 1.0, 0.0])
    y_pred = H @ x
    
    # 低振幅時：観測値を0に固定
    if force_hold:
        z_eff = 0.0
    else:
        z_eff = z
    
    innov = z_eff - y_pred
    
    # R, K共に制約なし（デッドバンド案ではシンプル実装）
    S = H @ P @ H.T + R
    if S < 1e-6:
        return x, P, innov, 0.0
    
    K = P @ H.T / S
    x_new = x + K * innov
    
    I_KH = np.eye(4) - np.outer(K, H)
    P_new = I_KH @ P @ I_KH.T + R * np.outer(K, K)
    
    return x_new, P_new, innov, K[0]

# シミュレーション実行
t_end = 50.0
dt = 0.01
t_array = np.arange(0, t_end + dt, dt)
n_steps = len(t_array)

# 真値信号
signal_true = make_signal(t_array)
# ノイズを加えた観測値
np.random.seed(42)
measurement = signal_true + np.random.normal(0, np.sqrt(R_base), n_steps)

# 3つのアプローチを実行
x0 = np.array([0.0, 0.0, 0.0, omega_true])
P0 = np.eye(4) * 0.1

results = {}

for method_name, ekf_update_func in [
    ('current_safeguard', ekf_update_current),
    ('no_safeguard', ekf_update_no_safeguard),
    ('measurement_zero', ekf_update_measurement_zero),
]:
    x = x0.copy()
    P = P0.copy()
    
    x_hist = np.zeros((n_steps, 4))
    P_hist = np.zeros((n_steps, 4))
    K0_hist = np.zeros(n_steps)
    innov_hist = np.zeros(n_steps)
    
    for i in range(n_steps):
        t = t_array[i]
        force_hold = (t >= 10.0 and t < 20.0)  # Low-amplitude region
        
        # 予測
        x, P = ekf_predict(x, P, dt, omega_true, Q)
        
        # 観測更新
        z = measurement[i]
        x, P, innov, K0 = ekf_update_func(x, P, z, R_base, force_hold)
        
        x_hist[i] = x
        P_hist[i] = np.diag(P)
        K0_hist[i] = K0
        innov_hist[i] = innov
    
    results[method_name] = {
        'x_hist': x_hist,
        'P_hist': P_hist,
        'K0_hist': K0_hist,
        'innov_hist': innov_hist,
    }

# プロット
fig, axes = plt.subplots(3, 3, figsize=(16, 12))
fig.suptitle('デッドバンド内での観測値ゼロ強制案の検証', fontsize=14, fontweight='bold')

methods = ['current_safeguard', 'no_safeguard', 'measurement_zero']
colors = ['blue', 'red', 'green']
labels = ['現行実装\n(R×1000+K制約)', '安全策なし\n(baseline)', '観測値0強制案\n(新提案)']

# Row 1: 推定振幅
ax = axes[0, 0]
ax.plot(t_array, signal_true, 'k--', linewidth=2, label='真値', alpha=0.7)
ax_rect1 = Rectangle((10, -0.6), 10, 1.2, alpha=0.1, color='orange', label='デッドバンド')
ax.add_patch(ax_rect1)
for method, color, label in zip(methods, colors, labels):
    amp = results[method]['x_hist'][:, 0]
    ax.plot(t_array, amp, color=color, linewidth=1.5, label=label)
ax.set_ylabel('推定振幅 d [N]')
ax.set_title('推定振幅の時系列')
ax.legend(loc='upper right', fontsize=8)
ax.grid(True, alpha=0.3)
ax.set_xlim([0, 50])

# Row 1: Kalman ゲイン K[0]
ax = axes[0, 1]
ax_rect2 = Rectangle((10, -1), 10, 2, alpha=0.1, color='orange')
ax.add_patch(ax_rect2)
for method, color, label in zip(methods, colors, labels):
    K0 = results[method]['K0_hist']
    ax.plot(t_array, K0, color=color, linewidth=1.5, label=label)
ax.axhline(y=0.01, color='gray', linestyle='--', alpha=0.5, label='制約 +0.01')
ax.axhline(y=-0.01, color='gray', linestyle='--', alpha=0.5, label='制約 -0.01')
ax.set_ylabel('Kalman ゲイン K[0]')
ax.set_title('Kalman ゲイン K[0] の推移')
ax.legend(loc='upper right', fontsize=8)
ax.grid(True, alpha=0.3)
ax.set_xlim([0, 50])
ax.set_ylim([-0.5, 0.5])

# Row 1: 共分散 P[0,0] (対数スケール)
ax = axes[0, 2]
ax_rect3 = Rectangle((10, 1e-4), 10, 100, alpha=0.1, color='orange', transform=ax.get_xaxis_transform())
ax.set_yscale('log')
for method, color, label in zip(methods, colors, labels):
    P00 = results[method]['P_hist'][:, 0]
    ax.plot(t_array, P00, color=color, linewidth=1.5, label=label)
ax.set_ylabel('共分散 P[0,0] (log)')
ax.set_title('共分散 P[0,0] の推移')
ax.legend(loc='upper left', fontsize=8)
ax.grid(True, alpha=0.3, which='both')
ax.set_xlim([0, 50])

# Row 2: 各フェーズごとの統計（Phase 1）
phases = [(0, 10, 'Phase 1\n通常振幅(0.5N)'),
          (10, 20, 'Phase 2\n低振幅(0.05N)'),
          (20, 50, 'Phase 3\n復帰(0.5N)')]

for phase_idx, (t_start, t_end, title) in enumerate(phases):
    idx_start = int(t_start / dt)
    idx_end = int(t_end / dt)
    phase_slice = slice(idx_start, idx_end)
    
    ax = axes[1, phase_idx]
    
    # RMSE calculation
    rmse_values = []
    for method, color, label in zip(methods, colors, labels):
        d_est = results[method]['x_hist'][phase_slice, 0]
        d_true = signal_true[phase_slice]
        rmse = np.sqrt(np.mean((d_est - d_true)**2))
        rmse_values.append(rmse)
    
    x_pos = np.arange(len(methods))
    ax.bar(x_pos, rmse_values, color=colors, alpha=0.7)
    ax.set_xticks(x_pos)
    ax.set_xticklabels([label.split('\n')[0] for label in labels], fontsize=9)
    ax.set_ylabel('RMSE [N]')
    ax.set_title(f'{title}')
    ax.grid(True, alpha=0.3, axis='y')
    
    # データラベルを追加
    for i, (v, color) in enumerate(zip(rmse_values, colors)):
        ax.text(i, v + 0.01, f'{v:.4f}', ha='center', fontsize=9)

# Row 3: 振幅オーバーシュート率（Phase 2のみ）
idx_start = int(10 / dt)
idx_end = int(20 / dt)
phase_slice = slice(idx_start, idx_end)
d_true_phase2 = signal_true[phase_slice]
d_true_max = np.max(np.abs(d_true_phase2))

overshoot_values = []
for method, color, label in zip(methods, colors, labels):
    d_est = results[method]['x_hist'][phase_slice, 0]
    d_est_max = np.max(np.abs(d_est))
    overshoot = d_est_max / (d_true_max + 1e-6)
    overshoot_values.append(overshoot)

ax = axes[2, 0]
x_pos = np.arange(len(methods))
bars = ax.bar(x_pos, overshoot_values, color=colors, alpha=0.7)
ax.set_xticks(x_pos)
ax.set_xticklabels([label.split('\n')[0] for label in labels], fontsize=9)
ax.set_ylabel('オーバーシュート率（倍）')
ax.set_title('Phase 2: 振幅オーバーシュート率')
ax.axhline(y=1.0, color='black', linestyle='--', alpha=0.5, label='理想値')
ax.grid(True, alpha=0.3, axis='y')
for i, v in enumerate(overshoot_values):
    ax.text(i, v + 0.1, f'{v:.2f}×', ha='center', fontsize=9)

# K[0] ピーク値（Phase 1 vs Phase 2）
K0_phase1 = np.max(np.abs(results['current_safeguard']['K0_hist'][:int(10/dt)]))
K0_peak_values = []
for method in methods:
    K0_phase2_peak = np.max(np.abs(results[method]['K0_hist'][int(10/dt):int(20/dt)]))
    K0_peak_values.append(K0_phase2_peak)

ax = axes[2, 1]
x_pos = np.arange(len(methods))
bars = ax.bar(x_pos, K0_peak_values, color=colors, alpha=0.7)
ax.set_xticks(x_pos)
ax.set_xticklabels([label.split('\n')[0] for label in labels], fontsize=9)
ax.set_ylabel('K[0] 最大値')
ax.set_title('Phase 2: K[0] ピーク値')
ax.grid(True, alpha=0.3, axis='y')
for i, v in enumerate(K0_peak_values):
    ax.text(i, v + 0.01, f'{v:.4f}', ha='center', fontsize=9)

# 復帰速度：Phase 2 → Phase 3 での収束速度
ax = axes[2, 2]
phase3_start = int(20 / dt)
phase3_end = int(25 / dt)  # 最初の5秒のみ
phase3_slice = slice(phase3_start, phase3_end)
t_phase3 = t_array[phase3_slice]

for method, color, label in zip(methods, colors, labels):
    d_est = results[method]['x_hist'][phase3_slice, 0]
    d_true_phase3 = signal_true[phase3_slice]
    error = np.abs(d_est - d_true_phase3)
    ax.plot(t_phase3, error, color=color, linewidth=1.5, label=label, marker='o', markersize=3)

ax.set_xlabel('時刻 [s]')
ax.set_ylabel('推定誤差 |d_est - d_true| [N]')
ax.set_title('Phase 3: 復帰時の収束速度')
ax.legend(loc='upper right', fontsize=8)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('/home/memoto/Ardupilot-UmemotoLab/analysis/deadband_measurement_zero_test.png', dpi=150, bbox_inches='tight')
print("✅ グラフを保存: analysis/deadband_measurement_zero_test.png")

# 統計サマリー
print("\n" + "="*70)
print("デッドバンド観測値ゼロ強制案 - シミュレーション結果")
print("="*70)

for method_name, label in zip(methods, labels):
    print(f"\n【{label.replace(chr(10), ' ')}】")
    
    # Phase ごとの統計
    for t_start, t_end, phase_title in phases:
        idx_start = int(t_start / dt)
        idx_end = int(t_end / dt)
        phase_slice = slice(idx_start, idx_end)
        
        d_est = results[method_name]['x_hist'][phase_slice, 0]
        d_true = signal_true[phase_slice]
        
        rmse = np.sqrt(np.mean((d_est - d_true)**2))
        amp_est_max = np.max(np.abs(d_est))
        amp_true_max = np.max(np.abs(d_true))
        if amp_true_max > 1e-6:
            overshoot_ratio = amp_est_max / amp_true_max
        else:
            overshoot_ratio = 0.0
        
        print(f"  {phase_title}: RMSE={rmse:.4f}, 推定振幅max={amp_est_max:.4f}, " +
              f"オーバーシュート率={overshoot_ratio:.2f}×")
    
    # Phase 2 での K[0] ピーク
    K0_phase2 = results[method_name]['K0_hist'][int(10/dt):int(20/dt)]
    K0_peak = np.max(np.abs(K0_phase2))
    print(f"  Phase 2 ゲインピーク K[0]: {K0_peak:.6f}")

print("\n" + "="*70)
print("評価")
print("="*70)

# 現行実装との比較
rmse_current_phase2 = np.sqrt(np.mean((results['current_safeguard']['x_hist'][int(10/dt):int(20/dt), 0] - 
                                       signal_true[int(10/dt):int(20/dt)])**2))
rmse_zero_phase2 = np.sqrt(np.mean((results['measurement_zero']['x_hist'][int(10/dt):int(20/dt), 0] - 
                                     signal_true[int(10/dt):int(20/dt)])**2))
rmse_baseline_phase2 = np.sqrt(np.mean((results['no_safeguard']['x_hist'][int(10/dt):int(20/dt), 0] - 
                                        signal_true[int(10/dt):int(20/dt)])**2))

print(f"\nPhase 2 (低振幅デッドバンド) での性能:")
print(f"  現行実装 RMSE:       {rmse_current_phase2:.4f}")
print(f"  観測値ゼロ案 RMSE:   {rmse_zero_phase2:.4f}")
print(f"  安全策なし RMSE:     {rmse_baseline_phase2:.4f}")

if rmse_zero_phase2 < rmse_baseline_phase2:
    print(f"  ✓ 観測値ゼロ案は安全策なしより {(1 - rmse_zero_phase2/rmse_baseline_phase2)*100:.1f}% 改善")
else:
    print(f"  ✗ 観測値ゼロ案は安全策なしより {(rmse_zero_phase2/rmse_baseline_phase2 - 1)*100:.1f}% 悪化")

if rmse_zero_phase2 > rmse_current_phase2:
    diff = rmse_zero_phase2 - rmse_current_phase2
    pct = (diff / rmse_current_phase2) * 100
    print(f"  → 現行比 {pct:+.1f}% ({diff:+.4f})")
else:
    diff = rmse_current_phase2 - rmse_zero_phase2
    pct = (diff / rmse_current_phase2) * 100
    print(f"  → 現行より {pct:.1f}% 良好 ({-diff:.4f})")
