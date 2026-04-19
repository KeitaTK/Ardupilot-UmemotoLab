#define AP_OBSERVER_REPLAY_TEST 1
#include "AP_Observer.h"

#ifdef AP_OBSERVER_REPLAY_TEST
// Mock GCS to prevent segfaults in standalone test
class MockGCS {
public:
    void send_text(int severity, const char *fmt, ...) const {}
};
static MockGCS _mock_gcs;
// Force substitution of gcs() calls to use our mock
#define gcs() _mock_gcs
#endif

// パラメータテーブル定義
const AP_Param::GroupInfo AP_Observer::var_info[] = {
    // @Param: CORR_GAIN
    // @DisplayName: Observer Correction Gain
    // @Description: Gain for attitude correction based on external force estimation
    // @Range: 0.0 1.0
    // @User: Advanced
    AP_GROUPINFO("CORR_GAIN", 0, AP_Observer, _correction_gain, 0.004f),
    
    // @Param: FILT_CUTOFF
    // @DisplayName: Observer Filter Cutoff Frequency
    // @Description: Low-pass filter cutoff frequency [Hz]
    // @Range: 1.0 100.0
    // @User: Advanced
    AP_GROUPINFO("FILT_CUTOFF", 1, AP_Observer, _filter_cutoff_freq, 20.0f),
    
    // @Param: EKF_Q_D
    // @DisplayName: EKF Process Noise D
    // @Description: Process noise variance for disturbance state d
    // @Range: 0.0 100.0
    // @User: Advanced
    AP_GROUPINFO("EKF_Q_D", 4, AP_Observer, _ekf_q_d, 9.5367432e-12f),

    // @Param: EKF_Q_DD
    // @DisplayName: EKF Process Noise DDot
    // @Description: Process noise variance for disturbance velocity state d_dot
    // @Range: 0.0 100.0
    // @User: Advanced
    AP_GROUPINFO("EKF_Q_DD", 5, AP_Observer, _ekf_q_d_dot, 2.3841858e-11f),

    // @Param: EKF_Q_C
    // @DisplayName: EKF Process Noise Offset
    // @Description: Process noise variance for DC offset state c
    // @Range: 0.0 100.0
    // @User: Advanced
    AP_GROUPINFO("EKF_Q_C", 6, AP_Observer, _ekf_q_c, 4.7683716e-13f),

    // @Param: EKF_Q_W
    // @DisplayName: EKF Process Noise Omega
    // @Description: Process noise variance for frequency state omega
    // @Range: 0.0 100.0
    // @User: Advanced
    AP_GROUPINFO("EKF_Q_W", 7, AP_Observer, _ekf_q_omega, 0.0005f),

    // @Param: EKF_R_MEAS
    // @DisplayName: EKF Measurement Noise
    // @Description: Measurement noise variance for payload force observations
    // @Range: 0.0001 1000.0
    // @User: Advanced
    AP_GROUPINFO("EKF_R_MEAS", 8, AP_Observer, _ekf_r_meas, 46.0f),

    // @Param: EKF_W_INIT
    // @DisplayName: EKF Initial Omega
    // @Description: Initial angular frequency [rad/s]
    // @Range: 1.0 20.0
    // @User: Advanced
    AP_GROUPINFO("EKF_W_INIT", 9, AP_Observer, _ekf_omega_init, 3.7699f),

    // @Param: EKF_W_MIN
    // @DisplayName: EKF Minimum Omega
    // @Description: Minimum angular frequency [rad/s]
    // @Range: 1.0 20.0
    // @User: Advanced
    AP_GROUPINFO("EKF_W_MIN", 10, AP_Observer, _ekf_omega_min, 2.1991f),

    // @Param: EKF_W_MAX
    // @DisplayName: EKF Maximum Omega
    // @Description: Maximum angular frequency [rad/s]
    // @Range: 1.0 20.0
    // @User: Advanced
    AP_GROUPINFO("EKF_W_MAX", 11, AP_Observer, _ekf_omega_max, 5.7180f),
    
    // @Param: PRED_TIME
    // @DisplayName: Prediction Time
    // @Description: Time ahead for force prediction [seconds]
    // @Range: 0.0 0.5
    // @User: Advanced
    AP_GROUPINFO("PRED_TIME", 13, AP_Observer, _prediction_time, 0.01f),
    
    // @Param: MAX_CORR_ANG
    // @DisplayName: Maximum Correction Angle
    // @Description: Maximum attitude correction angle for roll and pitch [rad]
    // @Range: 0.0 1.0
    // @User: Advanced
    AP_GROUPINFO("MAX_CORR_ANG", 19, AP_Observer, _max_correction_angle, 0.5f),

    // @Param: EKF_INN_MAX
    // @DisplayName: EKF Innovation Maximum
    // @Description: Maximum absolute innovation for including axis in fused frequency update [N]
    // @Range: 0.01 20.0
    // @User: Advanced
    AP_GROUPINFO("EKF_INN_MAX", 24, AP_Observer, _ekf_innov_max, 0.70f),

    // @Param: EKF_NIS_MAX
    // @DisplayName: EKF NIS Maximum
    // @Description: Maximum normalized innovation squared for including axis in fused frequency update
    // @Range: 0.1 100.0
    // @User: Advanced
    AP_GROUPINFO("EKF_NIS_MAX", 25, AP_Observer, _ekf_nis_max, 4.0f),

    // @Param: EKF_EN_GAT
    // @DisplayName: EKF Energy Gate Enable
    // @Description: Enable RMS-based axis gating for frequency fusion
    // @Values: 0:Disabled,1:Enabled
    // @User: Advanced
    AP_GROUPINFO("EKF_EN_GAT", 26, AP_Observer, _ekf_energy_gate_enable, 1),

    // @Param: EKF_EN_ON
    // @DisplayName: EKF Energy Gate On Threshold
    // @Description: RMS threshold for enabling an axis in fused frequency update [N]
    // @Range: 0.0 5.0
    // @User: Advanced
    AP_GROUPINFO("EKF_EN_ON", 27, AP_Observer, _ekf_energy_rms_on, 0.20f),

    // @Param: EKF_EN_OFF
    // @DisplayName: EKF Energy Gate Off Threshold
    // @Description: RMS threshold for disabling an axis in fused frequency update [N]
    // @Range: 0.0 5.0
    // @User: Advanced
    AP_GROUPINFO("EKF_EN_OFF", 28, AP_Observer, _ekf_energy_rms_off, 0.16f),

    // @Param: EKF_EN_TAU
    // @DisplayName: EKF Energy Gate Time Constant
    // @Description: EMA time constant used to estimate RMS energy [s]
    // @Range: 0.1 20.0
    // @User: Advanced
    AP_GROUPINFO("EKF_EN_TAU", 29, AP_Observer, _ekf_energy_tau_sec, 2.0f),

    // @Param: EKF_FHOLD
    // @DisplayName: EKF Force Hold Threshold
    // @Description: Hold the previous omega estimate when |force| is at or below this threshold [N]
    // @Range: 0.0 20.0
    // @User: Advanced
    AP_GROUPINFO("EKF_FHOLD", 30, AP_Observer, _ekf_force_hold_max, 0.10f),

    // @Param: EKF_FREJ
    // @DisplayName: EKF Force Reject Threshold
    // @Description: Reject force samples from estimation when |force| is at or above this threshold [N]
    // @Range: 0.0 20.0
    // @User: Advanced
    AP_GROUPINFO("EKF_FREJ", 31, AP_Observer, _ekf_force_reject_min, 5.0f),

    // @Param: EKF_SW_RST
    // @DisplayName: EKF Reset On Switch Edge
    // @Description: Reset frequency estimator when switch toggles OFF->ON
    // @Values: 0:NoReset,1:Reset
    // @User: Advanced
    AP_GROUPINFO("EKF_SW_RST", 32, AP_Observer, _ekf_reset_on_switch, 0),

    // @Param: EKF_AX_MASK
    // @DisplayName: EKF Axis Fusion Mask
    // @Description: Bitmask for axes included in fused frequency estimate (bit0=X, bit1=Y, bit2=Z)
    // @Range: 0 7
    // @User: Advanced
    AP_GROUPINFO("EKF_AX_MASK", 33, AP_Observer, _ekf_axis_mask, 3),

    // @Param: EKF_SW_HOLD
    // @DisplayName: EKF Hold Omega When Switch Off
    // @Description: Hold omega state when frequency estimation switch is OFF
    // @Values: 0:Disabled,1:Enabled
    // @User: Advanced
    AP_GROUPINFO("EKF_SW_HOLD", 34, AP_Observer, _ekf_hold_omega_when_off, 0),

    // @Param: EKF_RB_EN
    // @DisplayName: EKF Robust Update Enable
    // @Description: Enable robust observation update (innovation clipping and outlier reject)
    // @Values: 0:Disabled,1:Enabled
    // @User: Advanced
    AP_GROUPINFO("EKF_RB_EN", 35, AP_Observer, _ekf_robust_update_enable, 1),

    // @Param: EKF_RB_NIS
    // @DisplayName: EKF Robust Reject NIS Scale
    // @Description: Reject observation update when NIS exceeds EKF_NIS_MAX multiplied by this scale
    // @Range: 1.0 20.0
    // @User: Advanced
    AP_GROUPINFO("EKF_RB_NIS", 36, AP_Observer, _ekf_robust_nis_reject_scale, 3.0f),

    // @Param: EKF_HOLD_W
    // @DisplayName: EKF Hold Weight for Frozen Axis
    // @Description: Fusion weight applied to an axis when omega update is held
    // @Range: 0.0 1.0
    // @User: Advanced
    AP_GROUPINFO("EKF_HOLD_W", 37, AP_Observer, _ekf_hold_weight, 0.05f),

    // @Param: EKF_SH_BETA
    // @DisplayName: EKF Shared Omega Blend Beta
    // @Description: Blend factor for injecting shared XY omega into each XY axis when not in hard mode
    // @Range: 0.0 1.0
    // @User: Advanced
    AP_GROUPINFO("EKF_SH_BETA", 38, AP_Observer, _ekf_shared_blend_beta, 0.0f),

    // @Param: EKF_SH_HWM
    // @DisplayName: EKF Shared Omega Hard-Mode Weight Min
    // @Description: Minimum total XY fusion weight required to enter hard shared-omega mode
    // @Range: 0.0 2.0
    // @User: Advanced
    AP_GROUPINFO("EKF_SH_HWM", 39, AP_Observer, _ekf_shared_hard_weight_min, 1.8f),

    // @Param: EKF_SW_GATE
    // @DisplayName: EKF Switch Gate Enable
    // @Description: Enable switch gating for frequency estimation (0=always on, 1=use switch)
    // @Values: 0:AlwaysOn,1:UseSwitch
    // @User: Advanced
    AP_GROUPINFO("EKF_SW_GATE", 41, AP_Observer, _ekf_switch_gate_enable, 1),

    // @Param: EKF_SH_NIS
    // @DisplayName: EKF Shared Omega Hard-Mode NIS Max
    // @Description: Maximum XY NIS for enabling hard shared-omega mode
    // @Range: 0.1 100.0
    // @User: Advanced
    AP_GROUPINFO("EKF_SH_NIS", 40, AP_Observer, _ekf_shared_hard_nis_max, 1.0f),

    AP_GROUPEND
};

void AP_Observer::init() {
    // パラメータのデフォルト値設定
    AP_Param::setup_object_defaults(this, var_info);

    // フィルタ初期化
    float sample_freq = 100.0f; // サンプリング周波数 [Hz]
    _payload_filter.set_cutoff_frequency(sample_freq, _filter_cutoff_freq.get());
    _energy_bandpass_fast.set_cutoff_frequency(sample_freq, 0.80f);
    _energy_bandpass_slow.set_cutoff_frequency(sample_freq, 0.25f);

    // 基本変数初期化
    current_filtered_force = Vector3f();
    current_correction_quat = Quaternion(1, 0, 0, 0);
    last_update_ms = 0;
    _payload_filtered = Vector3f();
    _energy_band_proxy = Vector3f();
    filter_initialized = true;

    // EKF初期化
    ekf_init();
    
    // 予測用キャッシュ初期化
    update_prediction_cache();
    
    // 離陸検知フラグ初期化
    _has_taken_off = false;
    
    // 周波数推定制御初期化（RC Aux Function方式）
    _freq_estimation_switch_state = false;  // 初期状態はOFF
    _freq_estimation_active = false;
    _freq_estimation_prev_switch = false;
    _freq_estimation_result = estimated_frequency;

    // 初期化完了メッセージは一旦コメントアウト
    // gcs().send_text(MAV_SEVERITY_INFO, "AP_Observer: initialized with %.1fHz filter", _filter_cutoff_freq.get());
}

void AP_Observer::ekf_init() {
    const float init_cov = EKF_INIT_COVARIANCE;
    const float init_omega = constrain_value(_ekf_omega_init.get(), _ekf_omega_min.get(), _ekf_omega_max.get());

    for (uint8_t axis = 0; axis < EKF_NUM_AXES; axis++) {
        ekf_state[axis][0] = 0.0f;
        ekf_state[axis][1] = 0.0f;
        ekf_state[axis][2] = 0.0f;
        ekf_state[axis][3] = init_omega;
        ekf_axis_innovation[axis] = 0.0f;
        ekf_axis_nis[axis] = 0.0f;
        ekf_axis_amp[axis] = 0.0f;
        ekf_axis_force_abs[axis] = 0.0f;
        ekf_axis_energy_power[axis] = 0.0f;
        ekf_axis_weight[axis] = 0.0f;
        ekf_axis_trusted[axis] = 1U;
        ekf_axis_energy_trusted[axis] = 0U;
        ekf_axis_omega_updated[axis] = 0U;
        ekf_axis_hold_omega[axis] = 0U;

        for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
            for (uint8_t j = 0; j < EKF_STATE_SIZE; j++) {
                ekf_P[axis][i][j] = (i == j) ? init_cov : 0.0f;
            }
        }
    }

    ekf_sample_count = 0;
    ekf_start_time_ms = get_current_time_ms();
    estimated_frequency = init_omega / (2.0f * M_PI);
    ekf_shared_omega_rad = init_omega;
    ekf_shared_weight_sum = 0.0f;
    ekf_shared_hard_mode = 0U;
    ekf_initialized = true;
}

void AP_Observer::reset_frequency_estimation() {
    // 周波数推定のみをリセット（EKF本体は再初期化）
#if HAL_GCS_ENABLED
    gcs().send_text(MAV_SEVERITY_INFO, "AP_Observer: Resetting frequency estimation only");
#endif

    ekf_init();
    estimated_frequency = _ekf_omega_init.get() / (2.0f * M_PI);
    _freq_estimation_result = estimated_frequency;
    
#if HAL_GCS_ENABLED
    gcs().send_text(MAV_SEVERITY_INFO, "AP_Observer: Frequency reset to %.3fHz (EKF)", (double)estimated_frequency);
#endif
}

bool AP_Observer::is_axis_frequency_trusted(uint8_t axis) const {
    if (axis >= EKF_NUM_AXES) {
        return false;
    }

    const float force_reject_min = MAX(0.0f, _ekf_force_reject_min.get());
    if (ekf_axis_force_abs[axis] >= force_reject_min) {
        return false;
    }

    if (_ekf_energy_gate_enable.get() != 0) {
        if (!ekf_axis_energy_trusted[axis]) {
            return false;
        }
    }

    const float innov_abs = fabsf(ekf_axis_innovation[axis]);
    const float innov_max = MAX(1.0e-3f, _ekf_innov_max.get());
    const float nis = ekf_axis_nis[axis];
    const float nis_max = MAX(1.0e-3f, _ekf_nis_max.get());

    return (innov_abs <= innov_max) &&
           (nis <= nis_max);
}

float AP_Observer::compute_axis_fusion_weight(uint8_t axis) const {
    // XYのみ周波数融合に使用し、Z軸は常に除外する。
    if (axis >= 2 || !is_axis_enabled_in_fusion(axis)) {
        return 0.0f;
    }

    const float hold_weight = constrain_value(_ekf_hold_weight.get(), 0.0f, 1.0f);

    const float nis_max = MAX(1.0e-3f, _ekf_nis_max.get());
    const float nis_norm = ekf_axis_nis[axis] / nis_max;
    float w_nis = 1.0f / (1.0f + nis_norm * nis_norm);
    if (!isfinite(w_nis)) {
        w_nis = 0.0f;
    }

    float w_energy = 1.0f;
    if (_ekf_energy_gate_enable.get() != 0 && !ekf_axis_energy_trusted[axis]) {
        w_energy = hold_weight;
    }

    const float hold_thr = MAX(0.0f, _ekf_force_hold_max.get());
    const float reject_thr = MAX(hold_thr + 1.0e-3f, _ekf_force_reject_min.get());
    const float force_abs = ekf_axis_force_abs[axis];
    float w_amp = 0.0f;
    if (force_abs >= reject_thr) {
        w_amp = 0.0f;
    } else if (force_abs <= hold_thr) {
        w_amp = hold_weight;
    } else {
        // hold閾値直上で滑らかに立ち上げ、十分な振幅で1.0へ飽和。
        const float ramp_den = MAX(hold_thr, 0.05f);
        w_amp = constrain_value((force_abs - hold_thr) / ramp_den, 0.0f, 1.0f);
    }

    const float w_hold = (ekf_axis_omega_updated[axis] != 0U) ? 1.0f : hold_weight;
    float w = w_nis * w_energy * w_amp * w_hold;
    if (!isfinite(w)) {
        w = 0.0f;
    }
    return constrain_value(w, 0.0f, 1.0f);
}

void AP_Observer::ekf_update(const Vector3f& y_output, float dt) {
    if (!ekf_initialized) {
#if HAL_GCS_ENABLED
        gcs().send_text(MAV_SEVERITY_WARNING, "EKF: not initialized!");
#endif
        return;
    }

    dt = constrain_value(dt, 0.001f, 0.05f);

    const Vector3f energy_fast = _energy_bandpass_fast.apply(y_output);
    const Vector3f energy_slow = _energy_bandpass_slow.apply(y_output);
    _energy_band_proxy = energy_fast - energy_slow;

    for (uint8_t axis = 0; axis < EKF_NUM_AXES; axis++) {
        float measurement = 0.0f;
        switch (axis) {
            case 0: measurement = y_output.x; break;
            case 1: measurement = y_output.y; break;
            case 2: measurement = y_output.z; break;
        }
        ekf_update_axis(axis, measurement, dt);
    }

    // XY共有周波数: NIS×Energy×Amplitude×Hold の複合重みで融合する。
    float weighted_omega_sum = 0.0f;
    float weight_sum = 0.0f;
    float trusted_omega_sum = 0.0f;
    uint8_t trusted_count = 0;
    float donor_weighted_omega_sum = 0.0f;
    float donor_weight_sum = 0.0f;
    uint8_t trusted_xy_count = 0;
    uint8_t updated_xy_count = 0;
    float max_nis_xy = 0.0f;
    constexpr float donor_weight_min = 0.10f;

    for (uint8_t axis = 0; axis < EKF_NUM_AXES; axis++) {
        ekf_axis_amp[axis] = fabsf(ekf_state[axis][0]);
        const bool trusted = is_axis_frequency_trusted(axis);
        ekf_axis_trusted[axis] = trusted ? 1U : 0U;
        ekf_axis_weight[axis] = 0.0f;

        if (axis >= 2) {
            // Z軸は周波数融合に使わない。
            continue;
        }
        if (!is_axis_enabled_in_fusion(axis)) {
            ekf_axis_trusted[axis] = 0U;
            continue;
        }

        const float omega_axis = constrain_value(ekf_state[axis][3], _ekf_omega_min.get(), _ekf_omega_max.get());

        if (trusted) {
            trusted_xy_count++;
            trusted_omega_sum += omega_axis;
            trusted_count++;
        }
        if (ekf_axis_omega_updated[axis] != 0U) {
            updated_xy_count++;
        }
        if (isfinite(ekf_axis_nis[axis])) {
            max_nis_xy = MAX(max_nis_xy, ekf_axis_nis[axis]);
        }

        float w_axis = compute_axis_fusion_weight(axis);
        if (!trusted) {
            w_axis *= constrain_value(_ekf_hold_weight.get(), 0.0f, 1.0f);
        }
        ekf_axis_weight[axis] = w_axis;
        weighted_omega_sum += w_axis * omega_axis;
        weight_sum += w_axis;
        if (trusted && (ekf_axis_omega_updated[axis] != 0U) && (w_axis >= donor_weight_min)) {
            donor_weighted_omega_sum += w_axis * omega_axis;
            donor_weight_sum += w_axis;
        }
    }

    const float beta = constrain_value(_ekf_shared_blend_beta.get(), 0.0f, 1.0f);
    const bool shared_injection_enabled = (beta > 0.0f);

    // 推定周波数は従来互換の trusted 平均を優先し、共有注入は別レイヤで扱う。
    if (trusted_count > 0U) {
        estimated_frequency = (trusted_omega_sum / trusted_count) / (2.0f * M_PI);
    } else {
        estimated_frequency = _freq_estimation_result;
    }

    // 既定(beta=0)では、従来の trusted 平均のみを使用して完全後方互換を維持する。
    if (!shared_injection_enabled) {
        ekf_shared_weight_sum = weight_sum;
        ekf_shared_hard_mode = 0U;
        ekf_shared_omega_rad = constrain_value(estimated_frequency * 2.0f * float(M_PI),
                                               _ekf_omega_min.get(), _ekf_omega_max.get());
        _freq_estimation_result = estimated_frequency;
        update_prediction_cache();
        ekf_sample_count++;
        return;
    }

    float omega_shared = constrain_value(estimated_frequency * 2.0f * float(M_PI),
                                         _ekf_omega_min.get(), _ekf_omega_max.get());
    if (!isfinite(omega_shared) || omega_shared <= 0.0f) {
        omega_shared = constrain_value(_freq_estimation_result * 2.0f * float(M_PI),
                                       _ekf_omega_min.get(), _ekf_omega_max.get());
    }

    const bool has_trusted_donor = (donor_weight_sum > 1.0e-6f);
    if (has_trusted_donor) {
        omega_shared = constrain_value(donor_weighted_omega_sum / donor_weight_sum,
                                       _ekf_omega_min.get(), _ekf_omega_max.get());
    } else if (weight_sum > 1.0e-6f) {
        omega_shared = constrain_value(weighted_omega_sum / weight_sum,
                                       _ekf_omega_min.get(), _ekf_omega_max.get());
    }

    ekf_shared_weight_sum = weight_sum;
    const float hard_weight_min = constrain_value(_ekf_shared_hard_weight_min.get(), 0.0f, 2.0f);
    const float hard_nis_max = MAX(1.0e-3f, _ekf_shared_hard_nis_max.get());
    const bool hard_mode = shared_injection_enabled &&
                           (weight_sum >= hard_weight_min) &&
                           (trusted_xy_count >= 2U) &&
                           (updated_xy_count >= 2U) &&
                           has_trusted_donor &&
                           (max_nis_xy <= hard_nis_max) &&
                           _freq_estimation_active;
    ekf_shared_hard_mode = hard_mode ? 1U : 0U;

    const bool allow_shared_injection = shared_injection_enabled && _freq_estimation_active && has_trusted_donor;
    for (uint8_t axis = 0; axis < 2; axis++) {
        if (!is_axis_enabled_in_fusion(axis)) {
            continue;
        }
        const bool low_conf_axis = (ekf_axis_trusted[axis] == 0U);
        const bool frozen_axis = (ekf_axis_omega_updated[axis] == 0U) || (ekf_axis_hold_omega[axis] != 0U);

        if (hard_mode) {
            // 高信頼時の強制置換は低信頼軸に限定し、良好軸は保持する。
            if (low_conf_axis && frozen_axis && allow_shared_injection) {
                ekf_state[axis][3] = omega_shared;
            }
        } else {
            // 通常ブレンドは低信頼かつ凍結中の軸のみに適用する。
            if (low_conf_axis && frozen_axis && allow_shared_injection) {
                const float blended = (1.0f - beta) * ekf_state[axis][3] + beta * omega_shared;
                ekf_state[axis][3] = constrain_value(blended, _ekf_omega_min.get(), _ekf_omega_max.get());
            }
        }
    }

    ekf_shared_omega_rad = omega_shared;
    // 公開推定周波数は従来互換の trusted 平均値を維持する。
    _freq_estimation_result = estimated_frequency;
    update_prediction_cache();
    ekf_sample_count++;
}

void AP_Observer::ekf_update_axis(uint8_t axis, float measurement, float dt) {
    // EKF 1軸更新: 予測 -> 条件分岐（predict-only / reject）-> 観測更新
    // 低振幅・低エネルギー領域では measurement を 0 に固定して発散を抑える。

    float* x = ekf_state[axis];
    float (*P)[EKF_STATE_SIZE] = ekf_P[axis];
    const float omega_prev = x[3];
    const float force_abs = fabsf(measurement);
    ekf_axis_force_abs[axis] = force_abs;

    const float energy_tau = MAX(0.1f, _ekf_energy_tau_sec.get());
    const float energy_alpha = constrain_value(1.0f - expf(-dt / energy_tau), 0.0f, 1.0f);
    const float energy_proxy = fabsf(_energy_band_proxy[axis]);
    const float energy_proxy_sq = energy_proxy * energy_proxy;
    if (ekf_sample_count == 0U || !isfinite(ekf_axis_energy_power[axis])) {
        ekf_axis_energy_power[axis] = energy_proxy_sq;
    } else {
        ekf_axis_energy_power[axis] = energy_alpha * energy_proxy_sq + (1.0f - energy_alpha) * ekf_axis_energy_power[axis];
    }

    bool energy_gate_enabled = false;
    if (_ekf_energy_gate_enable.get() != 0) {
        const float energy_on = MAX(0.0f, _ekf_energy_rms_on.get());
        const float energy_off = constrain_value(_ekf_energy_rms_off.get(), 0.0f, energy_on);
        const float power_on = energy_on * energy_on;
        const float power_off = energy_off * energy_off;
        if (ekf_axis_energy_trusted[axis] == 0U) {
            if (ekf_axis_energy_power[axis] >= power_on) {
                ekf_axis_energy_trusted[axis] = 1U;
            }
        } else if (ekf_axis_energy_power[axis] <= power_off) {
            ekf_axis_energy_trusted[axis] = 0U;
        }
        energy_gate_enabled = (ekf_axis_energy_trusted[axis] != 0U);
    } else {
        ekf_axis_energy_trusted[axis] = 1U;
        energy_gate_enabled = true;
    }

    const float force_hold_max = MAX(0.0f, _ekf_force_hold_max.get());
    const float force_reject_min = MAX(force_hold_max + 1.0e-3f, _ekf_force_reject_min.get());
    
    // 条件1: force_hold_omega - 低振幅時（omega固定）
    const bool force_hold_omega = force_abs <= force_hold_max;
    
    // 条件2: switch_hold_omega - スイッチ OFF 時（predict-only）
    const bool switch_hold_omega = (!_freq_estimation_active && _ekf_hold_omega_when_off.get() != 0);
    
    // 条件3: energy_hold_omega - エネルギーゲート OFF 時（predict-only）
    const bool energy_hold_omega = !energy_gate_enabled;
    
    // 統合判定
    const bool hold_omega = force_hold_omega || switch_hold_omega || energy_hold_omega;  // omega を固定
    ekf_axis_hold_omega[axis] = hold_omega ? 1U : 0U;
    ekf_axis_omega_updated[axis] = 0U;
    // ゼロ注入で収束させるため、predict-only はスイッチOFF時に限定する。
    const bool predict_only_hold = switch_hold_omega;  // 予測のみ（観測更新スキップ）
    
    // 追加判定: force_reject - 高振幅時の周波数推定拒否
    //   トリガ：|force| >= force_reject_min（例：5.0 N）
    //   非線形性や飽和による推定エラーを防ぐため、観測更新を完全に拒否
    const bool force_reject = force_abs >= force_reject_min;

    const float omega = constrain_value(x[3], _ekf_omega_min.get(), _ekf_omega_max.get());
    const float d = x[0];
    const float d_dot = x[1];
    const float c = x[2];

    float x_pred[EKF_STATE_SIZE];
    x_pred[0] = d + dt * d_dot;
    x_pred[1] = d_dot + dt * (-(omega * omega) * d);
    x_pred[2] = c;
    x_pred[3] = omega;

    x_pred[3] = constrain_value(x_pred[3], _ekf_omega_min.get(), _ekf_omega_max.get());

    float F[EKF_STATE_SIZE][EKF_STATE_SIZE] = {
        {1.0f, dt, 0.0f, 0.0f},
        {-dt * omega * omega, 1.0f, 0.0f, -2.0f * dt * omega * d},
        {0.0f, 0.0f, 1.0f, 0.0f},
        {0.0f, 0.0f, 0.0f, 1.0f}
    };

    float FP[EKF_STATE_SIZE][EKF_STATE_SIZE];
    for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
        for (uint8_t j = 0; j < EKF_STATE_SIZE; j++) {
            float sum = 0.0f;
            for (uint8_t k = 0; k < EKF_STATE_SIZE; k++) {
                sum += F[i][k] * P[k][j];
            }
            FP[i][j] = sum;
        }
    }

    float P_pred[EKF_STATE_SIZE][EKF_STATE_SIZE];
    for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
        for (uint8_t j = 0; j < EKF_STATE_SIZE; j++) {
            float sum = 0.0f;
            for (uint8_t k = 0; k < EKF_STATE_SIZE; k++) {
                sum += FP[i][k] * F[j][k];
            }
            P_pred[i][j] = sum;
        }
    }

    const float q_d = _ekf_q_d.get();
    const float q_ddot = _ekf_q_d_dot.get();
    const float q_c = _ekf_q_c.get();
    const float q_omega_base = _freq_estimation_active ? _ekf_q_omega.get() : 0.0f;
    const float q_omega = (_freq_estimation_active && !hold_omega && !force_reject)
        ? q_omega_base
        : ((_freq_estimation_active && (hold_omega || force_reject)) ? MAX(q_omega_base, 1.0e-6f) : 0.0f);
    P_pred[0][0] += q_d;
    P_pred[1][1] += q_ddot;
    P_pred[2][2] += q_c;
    P_pred[3][3] += q_omega;

    if (predict_only_hold) {
            // SW OFF またはエネルギーゲート OFF では観測更新を行わない。
        const float y_pred_hold = x_pred[0] + x_pred[2];
        const float innov_hold = measurement - y_pred_hold;
        for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
            x[i] = x_pred[i];
            for (uint8_t j = 0; j < EKF_STATE_SIZE; j++) {
                P[i][j] = P_pred[i][j];
            }
        }
        x[3] = omega_prev;
        ekf_axis_innovation[axis] = innov_hold;
        ekf_axis_nis[axis] = 0.0f;
        ekf_axis_amp[axis] = fabsf(x[0]);
        ekf_axis_omega_updated[axis] = 0U;
        return;
    }

    if (force_reject) {
        for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
            x[i] = x_pred[i];
            for (uint8_t j = 0; j < EKF_STATE_SIZE; j++) {
                P[i][j] = P_pred[i][j];
            }
        }
        x[3] = omega_prev;
        ekf_axis_innovation[axis] = 0.0f;
        ekf_axis_nis[axis] = _ekf_nis_max.get() + 1.0f;
        ekf_axis_amp[axis] = fabsf(x[0]);
        ekf_axis_omega_updated[axis] = 0U;
        return;
    }

    // 低振幅デッドバンドでは観測値をゼロ強制して更新の暴れを抑制する。
    if (force_hold_omega || energy_hold_omega) {
        measurement = 0.0f;
    }

    const float y_pred = x_pred[0] + x_pred[2];
    const float innov_raw = measurement - y_pred;
    float innov_used = innov_raw;
    float R = _ekf_r_meas.get();
    if (R < 1.0e-6f) {
        R = 1.0e-6f;
    }
    float R_eff = R;

    float PHt[EKF_STATE_SIZE];
    for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
        PHt[i] = P_pred[i][0] + P_pred[i][2];
    }

    float S = PHt[0] + PHt[2] + R_eff;
    if (!isfinite(S) || fabsf(S) < 1.0e-6f) {
        ekf_axis_innovation[axis] = innov_raw;
        ekf_axis_nis[axis] = _ekf_nis_max.get() + 1.0f;
        ekf_axis_amp[axis] = fabsf(x[0]);
        ekf_axis_trusted[axis] = 0U;
        return;
    }
    const float nis_raw = (S > 1.0e-6f) ? ((innov_raw * innov_raw) / S) : (_ekf_nis_max.get() + 1.0f);

    bool robust_reject = false;
    if (_ekf_robust_update_enable.get() != 0) {
        const float innov_max = MAX(1.0e-3f, _ekf_innov_max.get());
        const float nis_max = MAX(1.0e-3f, _ekf_nis_max.get());
        const float reject_nis_scale = MAX(1.0f, _ekf_robust_nis_reject_scale.get());

        innov_used = constrain_value(innov_used, -innov_max, innov_max);

        if (nis_raw > nis_max) {
            const float nis_ratio = constrain_value(nis_raw / nis_max, 1.0f, 50.0f);
            R_eff = R * nis_ratio;
            S = PHt[0] + PHt[2] + R_eff;
            if (!isfinite(S) || fabsf(S) < 1.0e-6f) {
                ekf_axis_innovation[axis] = innov_raw;
                ekf_axis_nis[axis] = nis_raw;
                ekf_axis_amp[axis] = fabsf(x[0]);
                ekf_axis_trusted[axis] = 0U;
                ekf_axis_omega_updated[axis] = 0U;
                return;
            }
        }

        robust_reject = (nis_raw > (nis_max * reject_nis_scale));
    }

    if (robust_reject) {
        for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
            x[i] = x_pred[i];
            for (uint8_t j = 0; j < EKF_STATE_SIZE; j++) {
                P[i][j] = P_pred[i][j];
            }
        }
        if (hold_omega) {
            x[3] = omega_prev;
        }
        ekf_axis_innovation[axis] = innov_raw;
        ekf_axis_nis[axis] = nis_raw;
        ekf_axis_amp[axis] = fabsf(x[0]);
        ekf_axis_omega_updated[axis] = 0U;
        return;
    }

    float K[EKF_STATE_SIZE];
    for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
        K[i] = PHt[i] / S;
    }

    if (hold_omega) {
        // hold 条件下では omega 更新を止める。
        K[3] = 0.0f;
    }
    
    ekf_axis_innovation[axis] = innov_raw;
    ekf_axis_nis[axis] = nis_raw;

    for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
        x[i] = x_pred[i] + K[i] * innov_used;
    }
    if (hold_omega) {
        x[3] = omega_prev;
    }

    float KH[EKF_STATE_SIZE][EKF_STATE_SIZE];
    for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
        for (uint8_t j = 0; j < EKF_STATE_SIZE; j++) {
            const float H_j = (j == 0 || j == 2) ? 1.0f : 0.0f;
            KH[i][j] = K[i] * H_j;
        }
    }

    float I_KH[EKF_STATE_SIZE][EKF_STATE_SIZE];
    for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
        for (uint8_t j = 0; j < EKF_STATE_SIZE; j++) {
            I_KH[i][j] = (i == j ? 1.0f : 0.0f) - KH[i][j];
        }
    }

    float P_new[EKF_STATE_SIZE][EKF_STATE_SIZE];
    for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
        for (uint8_t j = 0; j < EKF_STATE_SIZE; j++) {
            float sum = 0.0f;
            for (uint8_t k = 0; k < EKF_STATE_SIZE; k++) {
                sum += I_KH[i][k] * P_pred[k][j];
            }
            P_new[i][j] = sum;
        }
    }

    for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
        for (uint8_t j = 0; j < EKF_STATE_SIZE; j++) {
            P[i][j] = 0.5f * (P_new[i][j] + P_new[j][i]);
        }
    }

    if (hold_omega) {
        x[3] = omega_prev;
        for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
            P[3][i] = P_pred[3][i];
            P[i][3] = P_pred[i][3];
        }
    }

    bool finite_ok = true;
    for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
        finite_ok = finite_ok && isfinite(x[i]);
        for (uint8_t j = 0; j < EKF_STATE_SIZE; j++) {
            finite_ok = finite_ok && isfinite(P[i][j]);
        }
    }
    if (!finite_ok) {
        // [対策3] 非有限値（NaN/Inf）検出時の軸リセット
        // 数値計算による発散を検出したら、軸状態を安全値にリセット。
        // omega は前フレーム値を維持（周波数推定は継続）し、他の状態は 0 化。
        // この堅牢性対策により、局所的な演算エラーから回復。
        const float init_cov = EKF_INIT_COVARIANCE;
        x[0] = 0.0f;
        x[1] = 0.0f;
        x[2] = 0.0f;
        x[3] = constrain_value(omega_prev, _ekf_omega_min.get(), _ekf_omega_max.get());
        for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
            for (uint8_t j = 0; j < EKF_STATE_SIZE; j++) {
                P[i][j] = (i == j) ? init_cov : 0.0f;
            }
        }
        ekf_axis_innovation[axis] = 0.0f;
        ekf_axis_nis[axis] = _ekf_nis_max.get() + 1.0f;
        ekf_axis_amp[axis] = 0.0f;
        ekf_axis_omega_updated[axis] = 0U;
        return;
    }

    x[3] = constrain_value(x[3], _ekf_omega_min.get(), _ekf_omega_max.get());
    ekf_axis_innovation[axis] = innov_raw;
    ekf_axis_nis[axis] = nis_raw;
    ekf_axis_amp[axis] = fabsf(x[0]);
    ekf_axis_omega_updated[axis] = hold_omega ? 0U : 1U;

#if HAL_GCS_ENABLED
    if ((ekf_sample_count % 100U) == 0U && axis == 0) {
        gcs().send_text(MAV_SEVERITY_INFO,
            "EKF[%d]: y=%.3f pred=%.3f err=%.3f f=%.3f",
            axis, measurement, y_pred, innov_raw, (double)(x[3] / (2.0f * M_PI)));
    }
#endif
}

void AP_Observer::update_prediction_cache() {
    const float omega = constrain_value(estimated_frequency * 2.0f * float(M_PI), _ekf_omega_min.get(), _ekf_omega_max.get());
    _omega_rad = omega;
}

void AP_Observer::update() {
    // モータポインタの安全チェック
    AP_Motors* motors = AP::motors();
    if (!motors) {
        return;  // エラーメッセージは出さずに静かに終了
    }

    // スラスト計算
    float throttle = motors->get_throttle_out();
    float thrust = -(THRUST_SCALE * throttle + THRUST_OFFSET) * g;
    
    // ペイロード力計算
    Vector3f payload;
    Vector3f accel = AP::ins().get_accel();
    payload.x = UAV_mass * accel.x;
    payload.y = UAV_mass * accel.y;
    payload.z = UAV_mass * accel.z - thrust;
    
    // フィルタ適用（無効化）
    // _payload_filtered = _payload_filter.apply(payload);
    _payload_filtered = payload; // フィルタなしで生データを使用

    // 離陸検知
    if (!_has_taken_off && is_taking_off()) {
        _has_taken_off = true;
#if HAL_GCS_ENABLED
        gcs().send_text(MAV_SEVERITY_INFO, "AP_Observer: Takeoff detected, starting frequency estimation");
#endif
    }
    
    const bool current_switch = _freq_estimation_switch_state;
    const bool switch_gate_enabled = (_ekf_switch_gate_enable.get() != 0);

    if (!switch_gate_enabled) {
        _freq_estimation_active = true;
        _freq_estimation_prev_switch = true;
    } else {
        if (current_switch && !_freq_estimation_prev_switch) {
            _freq_estimation_active = true;
            if (_ekf_reset_on_switch.get() == 1) {
                reset_frequency_estimation();
#if HAL_GCS_ENABLED
                gcs().send_text(MAV_SEVERITY_INFO, "EKF Freq Est: ON (Reset to %.3fHz)", (double)estimated_frequency);
#endif
            } else {
                _freq_estimation_result = estimated_frequency;
#if HAL_GCS_ENABLED
                gcs().send_text(MAV_SEVERITY_INFO, "EKF Freq Est: ON (No reset, %.3fHz)", (double)estimated_frequency);
#endif
            }
        } else if (!current_switch && _freq_estimation_prev_switch) {
            _freq_estimation_active = false;
#if HAL_GCS_ENABLED
            gcs().send_text(MAV_SEVERITY_INFO, "EKF Freq Est: OFF (Holding %.3fHz)", (double)estimated_frequency);
#endif
        }
        _freq_estimation_prev_switch = current_switch;
    }

    const uint32_t now_ms = get_current_time_ms();
    float dt = 0.01f;
    if (last_update_ms != 0) {
        dt = 0.001f * (float)(now_ms - last_update_ms);
    }

    if (_has_taken_off && ekf_initialized) {
        ekf_update(_payload_filtered, dt);
    }
    
    update_prediction_cache();

    // EKF予測外力を使用
    current_filtered_force = get_predicted_force();  // Δt秒後の予測外力
    current_correction_quat = calculate_correction_from_force(current_filtered_force);
    current_correction_euler = calculate_correction_euler_from_force(current_filtered_force);
    last_update_ms = get_current_time_ms();

    // ログをSDカードに記録（毎回記録）
    Write_Observer_Log();
    
}
    
Quaternion AP_Observer::calculate_correction_from_force(const Vector3f& force) const {
    float mag = force.length();
    if (mag < FORCE_THRESHOLD) {
        return Quaternion(1, 0, 0, 0);
    }

    float correction_gain = _correction_gain.get();
    float roll  =  force.y * correction_gain / UAV_mass;
    float pitch = -force.x * correction_gain / UAV_mass;

    float max_angle = _max_correction_angle.get();
    roll = constrain_value(roll, -max_angle, max_angle);
    pitch = constrain_value(pitch, -max_angle, max_angle);

    Quaternion q;
    q.from_euler(roll, pitch, 0.0f);
    q.normalize();
    return q;
}

// オイラー角形式で補正値を計算（ヨー角は常に0）
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

    // ヨー角は常に0.0fに固定
    return Vector3f(roll, pitch, 0.0f);
}

Vector3f AP_Observer::get_harmonic_sin_coeff() const {
    return Vector3f(ekf_state[0][0], ekf_state[1][0], ekf_state[2][0]);
}

Vector3f AP_Observer::get_harmonic_cos_coeff() const {
    return Vector3f(ekf_state[0][1], ekf_state[1][1], ekf_state[2][1]);
}

Vector3f AP_Observer::get_dc_offset() const {
    return Vector3f(ekf_state[0][2], ekf_state[1][2], ekf_state[2][2]);
}

Vector3f AP_Observer::get_predicted_force() const {
    if (!ekf_initialized) {
        return _payload_filtered;  // 初期化前は通常の外力を返す
    }
    const float pred_dt = _prediction_time.get();
    Vector3f predicted;
    for (uint8_t axis = 0; axis < EKF_NUM_AXES; axis++) {
        const float* state = ekf_state[axis];
        const float omega = constrain_value(state[3], _ekf_omega_min.get(), _ekf_omega_max.get());
        const float d = state[0];
        const float d_dot = state[1];
        const float c = state[2];
        const float d_pred = d + pred_dt * d_dot;
        const float d_dot_pred = d_dot + pred_dt * (-(omega * omega) * d);
        const float force = d_pred + c;
        (void)d_dot_pred;

        if (axis == 0) {
            predicted.x = force;
        } else if (axis == 1) {
            predicted.y = force;
        } else {
            predicted.z = force;
        }
    }
    
    return predicted;
}

// 離陸検知（モーターアーム済み）
bool AP_Observer::is_taking_off() {
    AP_Motors* motors = AP::motors();
    if (!motors) {
        return false;
    }
    
    // モーターがアームされていれば離陸とみなす
    return motors->armed();
}

// ログをSDカードに記録
void AP_Observer::Write_Observer_Log() {
#if HAL_LOGGING_ENABLED
    AP_Logger *logger = AP_Logger::get_singleton();
    if (logger == nullptr) {
        return;
    }

    // ログメッセージをカスタムフォーマットで書き込み
    // OBSV: TimeUS, PLX, PLY, PLZ, DX, DY, DZ, VX, VY, VZ, CX, CY, CZ, F, SW
    logger->Write("OBSV", "TimeUS,PLX,PLY,PLZ,DX,DY,DZ,VX,VY,VZ,CX,CY,CZ,F,SW",
                  "s--------------", "F--------------",
                  "QfffffffffffffB",
                  AP_HAL::micros64(),
                  _payload_filtered.x,
                  _payload_filtered.y,
                  _payload_filtered.z,
                  ekf_state[0][0],      // d X軸
                  ekf_state[1][0],      // d Y軸
                  ekf_state[2][0],      // d Z軸
                  ekf_state[0][1],      // d_dot X軸
                  ekf_state[1][1],      // d_dot Y軸
                  ekf_state[2][1],      // d_dot Z軸
                  ekf_state[0][2],      // c X軸
                  ekf_state[1][2],      // c Y軸
                  ekf_state[2][2],      // c Z軸
                  estimated_frequency,
                  (uint8_t)(_freq_estimation_switch_state ? 1 : 0));  // SW: スイッチ状態
#endif
}

// RCスイッチ状態の設定（RC Aux Function経由で呼び出される）
// RC8_OPTION=316 を推奨（デフォルト設定）
void AP_Observer::set_freq_estimation_switch(bool enabled) {
    _freq_estimation_switch_state = enabled;
}

void AP_Observer::set_freq_estimation_active(bool active) {
    if (_ekf_switch_gate_enable.get() == 0) {
        active = true;
    }

    if (active && !_freq_estimation_prev_switch) {
        if (_ekf_reset_on_switch.get() == 1) {
            reset_frequency_estimation();
        } else {
            _freq_estimation_result = estimated_frequency;
        }
    } else if (!active && _freq_estimation_prev_switch) {
        _freq_estimation_result = estimated_frequency;
    }

    _freq_estimation_active = active;
    _freq_estimation_switch_state = active;
    _freq_estimation_prev_switch = active;
}


#ifdef AP_OBSERVER_REPLAY_TEST
void AP_Observer::force_frequency_estimation_update(const Vector3f& payload) {
    _payload_filtered = payload;
    
    if (ekf_initialized) {
        ekf_update(_payload_filtered, 0.01f);
    }

}

void AP_Observer::set_params_for_replay(float freq, float bw, float gain) {
    _filter_cutoff_freq.set(bw);
    _correction_gain.set(gain);

    // Reinitialize frequency state for replay runs.
    const float omega = constrain_value(freq * 2.0f * float(M_PI), _ekf_omega_min.get(), _ekf_omega_max.get());
    _ekf_omega_init.set(omega);
    estimated_frequency = omega / (2.0f * M_PI);

    // Ensure EKF re-init usage of new params
    update_prediction_cache();
    ekf_init();
}

void AP_Observer::set_ekf_w_init_hz_for_replay(float freq_hz) {
    const float omega = freq_hz * 2.0f * M_PI;
    _ekf_omega_init.set(omega);
    estimated_frequency = constrain_value(omega, _ekf_omega_min.get(), _ekf_omega_max.get()) / (2.0f * M_PI);
    update_prediction_cache();
    ekf_init();
}

void AP_Observer::set_ekf_process_noises_for_replay(float q_d,
                                                    float q_dd,
                                                    float q_c) {
    _ekf_q_d.set(MAX(0.0f, q_d));
    _ekf_q_d_dot.set(MAX(0.0f, q_dd));
    _ekf_q_c.set(MAX(0.0f, q_c));
}

void AP_Observer::set_ekf_q_w_for_replay(float q_w) {
    _ekf_q_omega.set(q_w);
}

void AP_Observer::set_ekf_r_meas_for_replay(float r_meas) {
    _ekf_r_meas.set(r_meas);
}

void AP_Observer::set_prediction_time_for_replay(float pred_time_sec) {
    _prediction_time.set(constrain_value(pred_time_sec, 0.0f, 0.5f));
}

void AP_Observer::set_ekf_innovation_limits_for_replay(float innov_max,
                                                       float nis_max) {
    _ekf_innov_max.set(MAX(1.0e-3f, innov_max));
    _ekf_nis_max.set(MAX(1.0e-3f, nis_max));
}

void AP_Observer::set_ekf_energy_gate_for_replay(bool enabled,
                                                 float rms_on,
                                                 float rms_off,
                                                 float tau_sec) {
    _ekf_energy_gate_enable.set(enabled ? 1 : 0);
    _ekf_energy_rms_on.set(MAX(0.0f, rms_on));
    _ekf_energy_rms_off.set(constrain_value(rms_off, 0.0f, _ekf_energy_rms_on.get()));
    _ekf_energy_tau_sec.set(MAX(0.1f, tau_sec));
}

void AP_Observer::set_ekf_force_thresholds_for_replay(float hold_max,
                                                      float reject_min) {
    _ekf_force_hold_max.set(MAX(0.0f, hold_max));
    _ekf_force_reject_min.set(MAX(_ekf_force_hold_max.get() + 1.0e-3f, reject_min));
}

void AP_Observer::set_ekf_reset_on_switch_for_replay(bool enabled) {
    _ekf_reset_on_switch.set(enabled ? 1 : 0);
}

void AP_Observer::set_ekf_axis_mask_for_replay(uint8_t mask) {
    _ekf_axis_mask.set((int8_t)mask);
}

void AP_Observer::set_ekf_hold_omega_when_off_for_replay(bool enabled) {
    _ekf_hold_omega_when_off.set(enabled ? 1 : 0);
}

void AP_Observer::set_ekf_switch_gate_enable_for_replay(bool enabled) {
    _ekf_switch_gate_enable.set(enabled ? 1 : 0);
}

void AP_Observer::set_ekf_shared_blend_beta_for_replay(float beta) {
    _ekf_shared_blend_beta.set(constrain_value(beta, 0.0f, 1.0f));
}

void AP_Observer::set_ekf_robust_update_for_replay(bool enabled,
                                                   float nis_reject_scale) {
    _ekf_robust_update_enable.set(enabled ? 1 : 0);
    _ekf_robust_nis_reject_scale.set(MAX(1.0f, nis_reject_scale));
}
#endif

bool AP_Observer::is_axis_enabled_in_fusion(uint8_t axis) const {
    if (axis >= EKF_NUM_AXES) {
        return false;
    }

    // 周波数融合はXYのみを対象とする（Z軸は除外）。
    if (axis >= 2U) {
        return false;
    }

    const uint8_t mask = (uint8_t)MAX(0, _ekf_axis_mask.get());
    return (mask & (1U << axis)) != 0U;
}
