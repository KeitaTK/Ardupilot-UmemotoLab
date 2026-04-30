#pragma once

#include <AP_Common/AP_Common.h>
#include <AP_Param/AP_Param.h>
#include <AP_Math/AP_Math.h>
#include <AP_InertialSensor/AP_InertialSensor.h>
#include <AP_Motors/AP_Motors.h>
#include <GCS_MAVLink/GCS.h>
#include <Filter/LowPassFilter2p.h>
#include <AP_Logger/AP_Logger.h>
#include <RC_Channel/RC_Channel.h>

class AP_Observer {
public:
    void init();
    void update();

    // ゲッター関数
    Quaternion get_correction_quaternion() const { return current_correction_quat; }
    Vector3f get_correction_euler() const { return current_correction_euler; }

    // 補正が最後に計算された時刻を取得
    uint32_t get_last_update_ms() const { return last_update_ms; }

    // タイムアウト判定
    bool is_correction_valid() const {
        return (AP_HAL::millis() - last_update_ms) < TIMEOUT_MS;
    }

    // デバッグ用：最終更新からの経過時間を取得
    uint32_t get_update_age_ms() const {
        return AP_HAL::millis() - last_update_ms;
    }
    
    // 状態ゲッター関数
    Vector3f get_harmonic_sin_coeff() const;
    Vector3f get_harmonic_cos_coeff() const;
    Vector3f get_dc_offset() const;
    Vector3f get_predicted_force() const;    // Δt秒後の予測外力
    bool is_frequency_estimation_initialized() const { return ekf_initialized; }
    
    // ログ記録関数
    void Write_Observer_Log();
    
    // 周波数推定のリセット（アーム時に呼び出し）
    void reset_frequency_estimation();

// #ifdef AP_OBSERVER_REPLAY_TEST
    // リプレイテスト用
    void set_replay_time_ms(uint32_t ms) { _test_current_ms = ms; _replay_active = true; }
    void force_frequency_estimation_update(const Vector3f& payload);
    void set_params_for_replay(float freq, float bw, float gain);
    void set_ekf_w_init_hz_for_replay(float freq_hz);
    void set_ekf_process_noises_for_replay(float q_d,
                                           float q_dd,
                                           float q_c);
    void set_ekf_q_w_for_replay(float q_w);
    void set_ekf_r_meas_for_replay(float r_meas);
    void set_prediction_time_for_replay(float pred_time_sec);
    void set_ekf_innovation_limits_for_replay(float innov_max,
                                              float nis_max);
    void set_ekf_energy_gate_for_replay(bool enabled,
                                        float rms_on,
                                        float rms_off,
                                        float tau_sec);
    void set_ekf_robust_update_for_replay(bool enabled,
                                          float nis_reject_scale);
    float get_axis_estimated_frequency(uint8_t axis) const {
        if (axis >= EKF_NUM_AXES) {
            return 0.0f;  // Invalid axis
        }
        return ekf_state[axis][3] / (2.0f * M_PI);  // Convert rad/s to Hz
    }
    // Add logic to get internal EKF state if needed
// #endif

    // パラメータ定義テーブル
    static const struct AP_Param::GroupInfo var_info[];

private:
// #ifdef AP_OBSERVER_REPLAY_TEST
    uint32_t _test_current_ms = 0;
    bool _replay_active = false;
    uint32_t get_current_time_ms() const { return _replay_active ? _test_current_ms : AP_HAL::millis(); }
    uint64_t get_current_time_us() const { return _test_current_ms != 0 ? (uint64_t)_test_current_ms * 1000 : AP_HAL::micros64(); }
// #else
//    uint32_t get_current_time_ms() const { return AP_HAL::millis(); }
//    uint64_t get_current_time_us() const { return AP_HAL::micros64(); }
// #endif

    Vector3f    current_filtered_force = Vector3f();
    Quaternion  current_correction_quat = Quaternion(1,0,0,0); // 単位クォータニオンで初期化
    Vector3f    current_correction_euler = Vector3f(0,0,0);    // オイラー角形式の補正値(Roll,Pitch,Yaw)
    uint32_t    last_update_ms = 0;   // 最終補正計算時刻

    // ローパスフィルタ
    LowPassFilter2pVector3f _payload_filter;
    LowPassFilter2pVector3f _energy_bandpass_fast;
    LowPassFilter2pVector3f _energy_bandpass_slow;
    Vector3f _payload_filtered = Vector3f();
    Vector3f _energy_band_proxy = Vector3f();
    bool filter_initialized = false;

    // EKF (harmonic disturbance observer) state
    static constexpr uint8_t EKF_STATE_SIZE = 4;  // [d, d_dot, c, omega]
    static constexpr uint8_t EKF_NUM_AXES = 3;     // x, y, z
    static constexpr uint8_t OBS_NUM_AXES = EKF_NUM_AXES;

    // 各軸のEKF状態 [軸][状態番号]
    // 状態: [0]=d, [1]=d_dot, [2]=c, [3]=omega
    float ekf_state[EKF_NUM_AXES][EKF_STATE_SIZE];

    // 各軸の共分散行列 [軸][行][列]
    float ekf_P[EKF_NUM_AXES][EKF_STATE_SIZE][EKF_STATE_SIZE];

    bool ekf_initialized = false;
    uint32_t ekf_sample_count = 0;
    uint32_t ekf_start_time_ms = 0;

    float ekf_axis_innovation[OBS_NUM_AXES];
    float ekf_axis_nis[OBS_NUM_AXES];
    float ekf_axis_amp[OBS_NUM_AXES];
    float ekf_axis_force_abs[OBS_NUM_AXES];
    float ekf_axis_energy_power[OBS_NUM_AXES];
    uint8_t ekf_axis_energy_trusted[OBS_NUM_AXES];
    uint8_t ekf_axis_omega_updated[OBS_NUM_AXES];
    uint8_t ekf_axis_hold_omega[OBS_NUM_AXES];

    // EKF tuning parameters
    AP_Float _ekf_q_d;
    AP_Float _ekf_q_d_dot;
    AP_Float _ekf_q_c;
    AP_Float _ekf_q_omega;
    AP_Float _ekf_r_meas;
    AP_Float _ekf_omega_init;
    AP_Float _ekf_omega_min;
    AP_Float _ekf_omega_max;
    AP_Float _ekf_innov_max;
    AP_Float _ekf_nis_max;
    AP_Int8  _ekf_energy_gate_enable;
    AP_Float _ekf_energy_rms_on;
    AP_Float _ekf_energy_rms_off;
    AP_Float _ekf_energy_tau_sec;
    AP_Float _ekf_force_hold_max;
    AP_Float _ekf_force_reject_min;
    AP_Int8  _ekf_robust_update_enable;
    AP_Float _ekf_robust_nis_reject_scale;

    // Estimator parameters
    AP_Float _prediction_time;
    
    // 予測用キャッシュ変数（計算量削減）
    float _omega_rad;                  // ω [rad/s]

    // EKF関数
    void ekf_init();
    void ekf_update(const Vector3f& y_output, float dt);
    void ekf_update_axis(uint8_t axis, float measurement, float dt);
    bool is_axis_frequency_trusted(uint8_t axis) const;
    Vector3f predict_force_from_state(const float state[EKF_STATE_SIZE], float dt) const;
    void update_prediction_cache();  // 予測用キャッシュ更新
    
    // 既存の関数
    Quaternion calculate_correction_from_force(const Vector3f& force) const;
    Vector3f calculate_correction_euler_from_force(const Vector3f& force) const;
    float apply_lowpass_filter(float input, float& state, float dt, float cutoff_freq) const;

    // 揺れ制御のゲイン
    AP_Float    _correction_gain;
    // ローパスフィルタのカットオフ周波数 [Hz]（パラメータ化）
    AP_Float    _filter_cutoff_freq;
    
    // 補正角度の最大値
    AP_Float    _max_correction_angle;

    // 定数
    static constexpr uint32_t TIMEOUT_MS            = 500;
    static constexpr float    FORCE_THRESHOLD       = 0.0f;
    static constexpr float    g                     = 9.7985f;
    static constexpr float    THRUST_SCALE          = 6.3157f;
    static constexpr float    THRUST_OFFSET         = -0.9995f;
    static constexpr float    UAV_mass              = 1.4f;
    
    static constexpr float    EKF_INIT_COVARIANCE   = 10.0f;
    
    // 離陸検知用の変数
    bool _has_taken_off = false;  // 離陸済みフラグ

    // ヘルパー関数
    bool is_taking_off();  // 離陸検知
};
