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
    
    // @Param: RLS_LAMBDA
    // @DisplayName: RLS Forgetting Factor
    // @Description: Forgetting factor for Recursive Least Squares parameter estimation
    // @Range: 0.9 0.9999
    // @User: Advanced
    AP_GROUPINFO("RLS_LAMBDA", 2, AP_Observer, _rls_forgetting_factor, 0.98f),
    
    // @Param: RLS_COV_INIT
    // @DisplayName: RLS Initial Covariance
    // @Description: Initial covariance value for RLS algorithm
    // @Range: 0.001 1000.0
    // @User: Advanced
    AP_GROUPINFO("RLS_COV_INIT", 3, AP_Observer, _rls_initial_covariance, 100.0f),

    // @Param: EKF_Q_D
    // @DisplayName: EKF Process Noise D
    // @Description: Process noise variance for disturbance state d
    // @Range: 0.0 100.0
    // @User: Advanced
    AP_GROUPINFO("EKF_Q_D", 4, AP_Observer, _ekf_q_d, 0.02f),

    // @Param: EKF_Q_DD
    // @DisplayName: EKF Process Noise DDot
    // @Description: Process noise variance for disturbance velocity state d_dot
    // @Range: 0.0 100.0
    // @User: Advanced
    AP_GROUPINFO("EKF_Q_DD", 5, AP_Observer, _ekf_q_d_dot, 0.05f),

    // @Param: EKF_Q_C
    // @DisplayName: EKF Process Noise Offset
    // @Description: Process noise variance for DC offset state c
    // @Range: 0.0 100.0
    // @User: Advanced
    AP_GROUPINFO("EKF_Q_C", 6, AP_Observer, _ekf_q_c, 0.001f),

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
    AP_GROUPINFO("EKF_R_MEAS", 8, AP_Observer, _ekf_r_meas, 0.08f),

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
    
    // @Param: DIST_FREQ
    // @DisplayName: Disturbance Frequency
    // @Description: Frequency of periodic disturbance for RLS estimation [Hz]. Constrained to 0.35-0.91Hz (pendulum length 0.3-2.0m)
    // @Range: 0.35 0.91
    // @User: Advanced
    AP_GROUPINFO("DIST_FREQ", 12, AP_Observer, _disturbance_freq, 0.6f),
    
    // @Param: PRED_TIME
    // @DisplayName: Prediction Time
    // @Description: Time ahead for force prediction [seconds]
    // @Range: 0.0 0.5
    // @User: Advanced
    AP_GROUPINFO("PRED_TIME", 13, AP_Observer, _prediction_time, 0.01f),
    
    // @Param: PHASE_CORR
    // @DisplayName: Phase Correction Enable
    // @Description: Enable or disable phase correction for disturbance frequency
    // @Values: 0:Disabled,1:Enabled
    // @User: Advanced
    AP_GROUPINFO("PHASE_CORR", 14, AP_Observer, _phase_correction_enabled, 1),
    
    // @Param: PHASE_THRESH
    // @DisplayName: Phase Correction Threshold
    // @Description: Threshold for applying phase correction [rad]. Correction is only applied if error exceeds this value.
    // @Range: 0.0 5.0
    // @User: Advanced
    AP_GROUPINFO("PHASE_THRESH", 15, AP_Observer, _phase_correction_threshold, 0.0f),
    
    // @Param: TEST_INJECT
    // @DisplayName: Test Force Injection Enable
    // @Description: Enable test mode to inject known sinusoidal force for RLS validation
    // @Values: 0:Disabled,1:Enabled
    // @User: Advanced
    AP_GROUPINFO("TEST_INJECT", 16, AP_Observer, _test_force_inject_enable, 0),
    
    // @Param: TEST_FREQ
    // @DisplayName: Test Force Frequency
    // @Description: Frequency of injected test force [Hz]
    // @Range: 0.35 0.91
    // @User: Advanced
    AP_GROUPINFO("TEST_FREQ", 17, AP_Observer, _test_force_freq, 0.7f),
    
    // @Param: TEST_AMP
    // @DisplayName: Test Force Amplitude
    // @Description: Amplitude of injected test force [N]
    // @Range: 0.0 10.0
    // @User: Advanced
    AP_GROUPINFO("TEST_AMP", 18, AP_Observer, _test_force_amp, 1.0f),
    
    // @Param: MAX_CORR_ANG
    // @DisplayName: Maximum Correction Angle
    // @Description: Maximum attitude correction angle for roll and pitch [rad]
    // @Range: 0.0 1.0
    // @User: Advanced
    AP_GROUPINFO("MAX_CORR_ANG", 19, AP_Observer, _max_correction_angle, 0.5f),

    // @Param: FREQ_WIN
    // @DisplayName: Zero-Cross Window Length
    // @Description: Window length for zero-cross frequency estimation [s]
    // @Range: 1.0 30.0
    // @User: Advanced
    AP_GROUPINFO("FREQ_WIN", 20, AP_Observer, _freq_est_window_sec, 10.0f),

    // @Param: EKF_AX_GAT
    // @DisplayName: EKF Axis Gate Enable
    // @Description: Enable legacy axis selection gate for frequency fusion using |d|, innovation and NIS thresholds
    // @Values: 0:Disabled,1:Enabled
    // @User: Advanced
    AP_GROUPINFO("EKF_AX_GAT", 21, AP_Observer, _ekf_axis_gate_enable, 0),

    // @Param: EKF_AMP_MIN
    // @DisplayName: EKF Axis Amplitude Minimum
    // @Description: Minimum |d| threshold for including axis in fused frequency update
    // @Range: 0.0 5.0
    // @User: Advanced
    AP_GROUPINFO("EKF_AMP_MIN", 22, AP_Observer, _ekf_amp_min, 0.08f),

    // @Param: EKF_AMP_MAX
    // @DisplayName: EKF Axis Amplitude Maximum
    // @Description: Maximum |d| threshold for including axis in fused frequency update
    // @Range: 0.1 20.0
    // @User: Advanced
    AP_GROUPINFO("EKF_AMP_MAX", 23, AP_Observer, _ekf_amp_max, 1.20f),

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
    AP_GROUPINFO("EKF_FHOLD", 30, AP_Observer, _ekf_force_hold_max, 0.0f),

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
    
    // 位相補正初期化
    phase_correction_init();

    // 離陸検知フラグ初期化
    _has_taken_off = false;
    
    // 周波数推定制御初期化（RC Aux Function方式）
    _freq_estimation_switch_state = false;  // 初期状態はOFF
    _freq_estimation_active = false;
    _freq_estimation_prev_switch = false;
    _freq_estimation_result = _disturbance_freq.get();
    zero_cross_reset_state();

    // 初期化完了メッセージは一旦コメントアウト
    // gcs().send_text(MAV_SEVERITY_INFO, "AP_Observer: initialized with %.1fHz filter", _filter_cutoff_freq.get());
}

void AP_Observer::ekf_init() {
    const float init_cov = constrain_value(_rls_initial_covariance.get(), RLS_MIN_COVARIANCE, RLS_MAX_COVARIANCE);
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
        ekf_axis_trusted[axis] = 1U;
        ekf_axis_energy_trusted[axis] = 0U;

        for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
            for (uint8_t j = 0; j < EKF_STATE_SIZE; j++) {
                ekf_P[axis][i][j] = (i == j) ? init_cov : 0.0f;
            }
        }
    }

    ekf_sample_count = 0;
    ekf_start_time_ms = get_current_time_ms();
    phase_correction = 0.0f;
    estimated_frequency = init_omega / (2.0f * M_PI);
    ekf_initialized = true;
}

void AP_Observer::reset_frequency_estimation() {
    // 周波数推定のみをリセット（EKF本体は再初期化）
#if HAL_GCS_ENABLED
    gcs().send_text(MAV_SEVERITY_INFO, "AP_Observer: Resetting frequency estimation only");
#endif

    ekf_init();
    phase_correction = 0.0f;
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

    if (_ekf_axis_gate_enable.get() == 0) {
        return true;
    }

    const float amp = ekf_axis_amp[axis];
    const float amp_min = MAX(0.0f, _ekf_amp_min.get());
    const float amp_max = MAX(amp_min + 1.0e-3f, _ekf_amp_max.get());
    const float innov_abs = fabsf(ekf_axis_innovation[axis]);
    const float innov_max = MAX(1.0e-3f, _ekf_innov_max.get());
    const float nis = ekf_axis_nis[axis];
    const float nis_max = MAX(1.0e-3f, _ekf_nis_max.get());

    return (amp >= amp_min) &&
           (amp <= amp_max) &&
           (innov_abs <= innov_max) &&
           (nis <= nis_max);
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

    float omega_sum = 0.0f;
    uint8_t trusted_count = 0;
    for (uint8_t axis = 0; axis < EKF_NUM_AXES; axis++) {
        if (!is_axis_enabled_in_fusion(axis)) {
            ekf_axis_trusted[axis] = 0U;
            continue;
        }
        const float omega_axis = constrain_value(ekf_state[axis][3], _ekf_omega_min.get(), _ekf_omega_max.get());
        ekf_axis_amp[axis] = fabsf(ekf_state[axis][0]);
        const bool trusted = is_axis_frequency_trusted(axis);
        ekf_axis_trusted[axis] = trusted ? 1U : 0U;
        if (trusted) {
            omega_sum += omega_axis;
            trusted_count++;
        }
    }

    if (trusted_count > 0U) {
        estimated_frequency = (omega_sum / trusted_count) / (2.0f * M_PI);
    } else {
        estimated_frequency = _freq_estimation_result;
    }
    _freq_estimation_result = estimated_frequency;
    update_prediction_cache();
    ekf_sample_count++;
}

void AP_Observer::ekf_update_axis(uint8_t axis, float measurement, float dt) {
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
    const bool force_hold_omega = force_abs <= force_hold_max;
    const bool force_reject = force_abs >= force_reject_min;
    const bool switch_hold_omega = (!_freq_estimation_active && _ekf_hold_omega_when_off.get() != 0);
    const bool energy_hold_omega = !energy_gate_enabled;
    const bool hold_omega = force_hold_omega || switch_hold_omega || energy_hold_omega;

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

    if (hold_omega) {
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
        return;
    }

    const float y_pred = x_pred[0] + x_pred[2];
    const float innov = measurement - y_pred;
    float R = _ekf_r_meas.get();
    if (R < 1.0e-6f) {
        R = 1.0e-6f;
    }

    float PHt[EKF_STATE_SIZE];
    for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
        PHt[i] = P_pred[i][0] + P_pred[i][2];
    }

    const float S = PHt[0] + PHt[2] + R;
    if (!isfinite(S) || fabsf(S) < 1.0e-6f) {
        ekf_axis_innovation[axis] = innov;
        ekf_axis_nis[axis] = _ekf_nis_max.get() + 1.0f;
        ekf_axis_amp[axis] = fabsf(x[0]);
        ekf_axis_trusted[axis] = 0U;
        return;
    }
    const float nis = (S > 1.0e-6f) ? ((innov * innov) / S) : (_ekf_nis_max.get() + 1.0f);

    float K[EKF_STATE_SIZE];
    for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
        K[i] = PHt[i] / S;
    }

    if (hold_omega) {
        K[3] = 0.0f;
    }

    for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
        x[i] = x_pred[i] + K[i] * innov;
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

    x[3] = constrain_value(x[3], _ekf_omega_min.get(), _ekf_omega_max.get());
    ekf_axis_innovation[axis] = innov;
    ekf_axis_nis[axis] = nis;
    ekf_axis_amp[axis] = fabsf(x[0]);

#if HAL_GCS_ENABLED
    if ((ekf_sample_count % 100U) == 0U && axis == 0) {
        gcs().send_text(MAV_SEVERITY_INFO,
            "EKF[%d]: y=%.3f pred=%.3f err=%.3f f=%.3f",
            axis, measurement, y_pred, innov, (double)(x[3] / (2.0f * M_PI)));
    }
#endif
}

void AP_Observer::update_prediction_cache() {
    const float omega = constrain_value(estimated_frequency * 2.0f * M_PI, _ekf_omega_min.get(), _ekf_omega_max.get());
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
    
    // テスト用外力注入モード（推力とIMUから計算された結果として扱う）
    if (_test_force_inject_enable.get() == 1) {
        // 既知の正弦波外力をpayloadに直接代入
        // テスト注入はシステム起動時刻から計算（RLS開始前でも動作する）
        static uint32_t test_start_time_ms = 0;
        static bool test_announced = false;
        
        if (test_start_time_ms == 0) {
            test_start_time_ms = get_current_time_ms();
        }
        
        float t = (get_current_time_ms() - test_start_time_ms) * 0.001f;
        float test_omega = _test_force_freq.get() * 2.0f * M_PI;  // [rad/s]
        float amplitude = _test_force_amp.get();                   // 毎回取得
        
        payload.x = amplitude * sinf(test_omega * t);
        payload.y = amplitude * sinf(test_omega * t + M_PI / 2.0f);  // 90度位相差
        payload.z = 0.0f;  // Z軸は0
        
        // デバッグ: 初回と10回後に振幅を確認
        static uint16_t call_count = 0;
        call_count++;
        if (!test_announced || call_count == 1000) {
#if HAL_GCS_ENABLED
            gcs().send_text(MAV_SEVERITY_INFO, 
                "AP_Observer: Test inject count=%u, amp=%.2fN, PLX=%.3fN",
                call_count, amplitude, payload.x
            );
#endif
            test_announced = true;
        }
    }

    // フィルタ適用（無効化）
    // _payload_filtered = _payload_filter.apply(payload);
    _payload_filtered = payload; // フィルタなしで生データを使用

    // 離陸検知
    if (!_has_taken_off && is_taking_off()) {
        _has_taken_off = true;
#if HAL_GCS_ENABLED
        gcs().send_text(MAV_SEVERITY_INFO, "AP_Observer: Takeoff detected, starting RLS");
#endif
    }
    
    const bool current_switch = _freq_estimation_switch_state;

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
    
    // デバッグメッセージ - 簡潔な形式（10回に1回）- コメントアウト
// #if HAL_GCS_ENABLED
//     if ((++counter % 10) == 0) {
//         // 経過時間 [秒]
//         float t = (get_current_time_ms() - rls_start_time_ms) / 1000.0f;
//         
//         // タイムスタンプ付き元の外力
//         gcs().send_text(MAV_SEVERITY_INFO,
//             "t=%.2f PL: %.3f %.3f %.3f",
//             t, _payload_filtered.x, _payload_filtered.y, _payload_filtered.z
//         );
//         
//         // RLS推定パラメータ（XY軸のみ）
//         #if HAL_GCS_ENABLED
//         gcs().send_text(MAV_SEVERITY_INFO,
//             "A: %.3f %.3f",
//             rls_theta[0][0], rls_theta[1][0]
//         );
//         #endif
//         #if HAL_GCS_ENABLED
//         gcs().send_text(MAV_SEVERITY_INFO,
//             "B: %.3f %.3f",
//             rls_theta[0][1], rls_theta[1][1]
//         );
//         #endif
//         #if HAL_GCS_ENABLED
//         gcs().send_text(MAV_SEVERITY_INFO,
//             "C: %.3f %.3f",
//             rls_theta[0][2], rls_theta[1][2]
//         );
//         #endif
//         
//         // 予測外力
//         Vector3f pred = get_predicted_force();
//         #if HAL_GCS_ENABLED
//         gcs().send_text(MAV_SEVERITY_INFO,
//             "PRED: %.3f %.3f %.3f",
//             pred.x, pred.y, pred.z
//         );
//         #endif
//         
//         // 共分散行列（コメントアウト）
//         // gcs().send_text(MAV_SEVERITY_INFO,
//         //     "P[0]: %.3f %.3f %.3f",
//         //     rls_P[0][0][0], rls_P[0][1][1], rls_P[0][2][2]
//         // );
//         
//         // RLS診断情報（コメントアウト）
//         // gcs().send_text(MAV_SEVERITY_INFO,
//         //     "RLS: init=%d samples=%lu ω=%.3f", 
//         //     rls_initialized, (unsigned long)rls_sample_count, _omega_rad
//         // );
//     }
// #endif
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

// EKFパラメータの互換ゲッター関数
Vector3f AP_Observer::get_rls_sin_coeff() const {
    return Vector3f(ekf_state[0][0], ekf_state[1][0], ekf_state[2][0]);
}

Vector3f AP_Observer::get_rls_cos_coeff() const {
    return Vector3f(ekf_state[0][1], ekf_state[1][1], ekf_state[2][1]);
}

Vector3f AP_Observer::get_rls_bias() const {
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

// 位相補正初期化
void AP_Observer::phase_correction_init() {
    phase_correction = 0.0f;
    estimated_frequency = _ekf_omega_init.get() / (2.0f * M_PI);
    // 注：_freq_estimation_switch_stateはRC Aux Functionが管理するため、ここでは変更しない

    // EKF state helper variablesもリセット
    for (uint8_t axis = 0; axis < EKF_NUM_AXES; axis++) {
        ab_phase_unwrapped[axis] = 0.0f;
        ab_phase_prev_wrapped[axis] = 0.0f;
        ab_phase_initialized[axis] = false;
        ab_amp[axis] = 0.0f;
    }
    
}


void AP_Observer::zero_cross_start() {
    const float max_window_sec = (float)ZERO_CROSS_MAX_SAMPLES / ZERO_CROSS_SAMPLE_RATE_HZ;
    const float window_sec = constrain_value(_freq_est_window_sec.get(), 1.0f, max_window_sec);
    uint16_t window_samples = (uint16_t)(window_sec * ZERO_CROSS_SAMPLE_RATE_HZ + 0.5f);

    if (window_samples < 2) {
        window_samples = 2;
    }
    if (window_samples > ZERO_CROSS_MAX_SAMPLES) {
        window_samples = ZERO_CROSS_MAX_SAMPLES;
    }

    _zc_window_samples = window_samples;
    _zc_sample_count = 0;
    _zc_decimation_counter = 0;
    _zc_window_active = true;
    _zc_prev_input = 0.0f;
    _zc_hp_state = 0.0f;
    _zc_lp_state = 0.0f;
}

void AP_Observer::zero_cross_stop() {
    _zc_window_active = false;
}

void AP_Observer::zero_cross_reset_state() {
    _zc_window_active = false;
    _zc_window_samples = 0;
    _zc_sample_count = 0;
    _zc_decimation_counter = 0;
    _zc_prev_input = 0.0f;
    _zc_hp_state = 0.0f;
    _zc_lp_state = 0.0f;
}

float AP_Observer::zero_cross_filter(float input) {
    const float dt = 1.0f / ZERO_CROSS_SAMPLE_RATE_HZ;
    const float rc_hp = 1.0f / (2.0f * M_PI * ZERO_CROSS_LOW_CUT_HZ);
    const float alpha_hp = rc_hp / (rc_hp + dt);
    const float hp = alpha_hp * (_zc_hp_state + input - _zc_prev_input);
    _zc_prev_input = input;
    _zc_hp_state = hp;

    const float rc_lp = 1.0f / (2.0f * M_PI * ZERO_CROSS_HIGH_CUT_HZ);
    const float alpha_lp = dt / (rc_lp + dt);
    _zc_lp_state = _zc_lp_state + alpha_lp * (hp - _zc_lp_state);

    return _zc_lp_state;
}

bool AP_Observer::zero_cross_compute_frequency(float &freq_out, uint16_t &crossings_out) const {
    crossings_out = 0;
    if (_zc_sample_count < 2) {
        freq_out = 0.0f;
        return false;
    }

    float sum = 0.0f;
    for (uint16_t i = 0; i < _zc_sample_count; i++) {
        sum += _zc_samples[i];
    }
    const float mean = sum / (float)_zc_sample_count;

    int16_t last_cross = -1;
    float interval_sum = 0.0f;
    for (uint16_t i = 1; i < _zc_sample_count; i++) {
        const float prev = _zc_samples[i - 1] - mean;
        const float curr = _zc_samples[i] - mean;
        const bool crossed = ((prev >= 0.0f && curr < 0.0f) || (prev < 0.0f && curr >= 0.0f));
        if (crossed) {
            if (last_cross >= 0) {
                interval_sum += (float)(i - last_cross);
            }
            last_cross = (int16_t)i;
            crossings_out++;
        }
    }

    if (crossings_out < 2) {
        freq_out = 0.0f;
        return false;
    }

    const float mean_interval_samples = interval_sum / (float)(crossings_out - 1);
    if (mean_interval_samples <= 0.0f) {
        freq_out = 0.0f;
        return false;
    }

    const float period_s = 2.0f * mean_interval_samples / ZERO_CROSS_SAMPLE_RATE_HZ;
    if (period_s <= 0.0f) {
        freq_out = 0.0f;
        return false;
    }

    freq_out = 1.0f / period_s;
    return true;
}

void AP_Observer::zero_cross_update(float sample) {
    if (!_zc_window_active) {
        return;
    }

    if ((++_zc_decimation_counter % ZERO_CROSS_DECIMATION) != 0U) {
        return;
    }

    const float filtered = zero_cross_filter(sample);
    if (_zc_sample_count < _zc_window_samples && _zc_sample_count < ZERO_CROSS_MAX_SAMPLES) {
        _zc_samples[_zc_sample_count++] = filtered;
    }

    if (_zc_sample_count < _zc_window_samples) {
        return;
    }

    float freq = 0.0f;
    uint16_t crossings = 0;
    const bool ok = zero_cross_compute_frequency(freq, crossings);

    if (ok && check_frequency_range(freq)) {
        estimated_frequency = freq;
        _freq_estimation_result = estimated_frequency;
        update_prediction_cache();
#if HAL_GCS_ENABLED
        gcs().send_text(MAV_SEVERITY_INFO,
            "ZeroCross: f=%.3fHz crossings=%u",
            (double)estimated_frequency, (unsigned)crossings
        );
#endif
    } else {
#if HAL_GCS_ENABLED
        gcs().send_text(MAV_SEVERITY_WARNING,
            "ZeroCross: invalid f=%.3fHz crossings=%u",
            (double)freq, (unsigned)crossings
        );
#endif
    }

    _zc_window_active = false;
    _freq_estimation_active = false;
}

// 周波数範囲チェック（振り子長0.3m~2.0mに対応）
bool AP_Observer::check_frequency_range(float freq) {
    return (freq >= FREQ_MIN && freq <= FREQ_MAX);
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
void AP_Observer::force_rls_update(const Vector3f& payload) {
    _payload_filtered = payload;
    
    if (ekf_initialized) {
        ekf_update(_payload_filtered, 0.01f);
    }

}

void AP_Observer::set_params_for_replay(float freq, float bw, float gain) {
    _disturbance_freq.set(freq);
    _filter_cutoff_freq.set(bw);
    _correction_gain.set(gain);

    // Force EKF params (workaround for AP_Param failure in replay)
    _rls_forgetting_factor.set(0.99f);
    _rls_initial_covariance.set(100.0f);
    _phase_correction_enabled.set(1);

    // ここで推定周波数も初期化
    estimated_frequency = freq;

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

void AP_Observer::set_ekf_q_w_for_replay(float q_w) {
    _ekf_q_omega.set(q_w);
}

void AP_Observer::set_ekf_r_meas_for_replay(float r_meas) {
    _ekf_r_meas.set(r_meas);
}

void AP_Observer::set_ekf_axis_gate_for_replay(bool enabled,
                                               float amp_min,
                                               float amp_max,
                                               float innov_max,
                                               float nis_max) {
    _ekf_axis_gate_enable.set(enabled ? 1 : 0);
    _ekf_amp_min.set(MAX(0.0f, amp_min));
    _ekf_amp_max.set(MAX(_ekf_amp_min.get() + 1.0e-3f, amp_max));
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
#endif

bool AP_Observer::is_axis_enabled_in_fusion(uint8_t axis) const {
    if (axis >= EKF_NUM_AXES) {
        return false;
    }

    const uint8_t mask = (uint8_t)MAX(0, _ekf_axis_mask.get());
    return (mask & (1U << axis)) != 0U;
}
