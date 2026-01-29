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
    
    // RCスイッチ状態の設定（RC Aux Function経由で呼び出される）
    void set_freq_estimation_switch(bool enabled);
    
    // RCチャンネル読み取り（旧方式・互換性のため）
    bool read_freq_estimation_switch();

    // RLS関連のゲッター関数
    Vector3f get_rls_sin_coeff() const;      // A (sin係数)
    Vector3f get_rls_cos_coeff() const;      // B (cos係数)
    Vector3f get_rls_bias() const;           // C (定常偏差)
    Vector3f get_predicted_force() const;    // Δt秒後の予測外力
    bool is_rls_initialized() const { return rls_initialized; }
    
    // ログ記録関数
    void Write_Observer_Log();
    
    // RLS周波数推定のリセット（アーム時に呼び出し）
    void reset_frequency_estimation();

// #ifdef AP_OBSERVER_REPLAY_TEST
    // リプレイテスト用
    void set_replay_time_ms(uint32_t ms) { _test_current_ms = ms; _replay_active = true; }
    void set_freq_estimation_active(bool active) { _freq_estimation_active = active; }
    void force_rls_update(const Vector3f& payload);
    void set_params_for_replay(float freq, float bw, float gain);
    void set_freq_est_alpha(float alpha) { _freq_est_alpha.set(alpha); }
    float get_estimated_frequency() const { return estimated_frequency; }
    float get_phase_correction() const { return phase_correction; }
    // Add logic to get internal RLS state if needed
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

    uint32_t    counter = 0;
    Vector3f    current_filtered_force = Vector3f();
    Quaternion  current_correction_quat = Quaternion(1,0,0,0); // 単位クォータニオンで初期化
    Vector3f    current_correction_euler = Vector3f(0,0,0);    // オイラー角形式の補正値(Roll,Pitch,Yaw)
    uint32_t    last_update_ms = 0;   // 最終補正計算時刻

    // ローパスフィルタ
    LowPassFilter2pVector3f _payload_filter;
    Vector3f _payload_filtered = Vector3f();
    bool filter_initialized = false;

    // RLS (Recursive Least Squares) 関連
    static constexpr uint8_t RLS_PARAM_SIZE = 3;  // [A:sin係数, B:cos係数, C:定常偏差]
    static constexpr uint8_t RLS_NUM_AXES = 3;    // x, y, z軸
    
    // 各軸のRLSパラメータ [軸][パラメータ番号]
    // パラメータ: [0]=A(sin), [1]=B(cos), [2]=C(定常偏差)
    float rls_theta[RLS_NUM_AXES][RLS_PARAM_SIZE];
    
    // 各軸の共分散行列 [軸][行][列]
    float rls_P[RLS_NUM_AXES][RLS_PARAM_SIZE][RLS_PARAM_SIZE];
    
    bool rls_initialized = false;
    uint32_t rls_sample_count = 0;
    uint32_t rls_start_time_ms = 0;  // RLS開始時刻

    // RLS用のパラメータ
    AP_Float _rls_forgetting_factor;   // λ (忘却係数)
    AP_Float _rls_initial_covariance;  // 初期共分散値
    AP_Float _disturbance_freq;        // ω: 外乱周波数 [Hz]
    AP_Float _prediction_time;         // Δt: 予測時間 [秒]
    
    // テスト用パラメータ（外力注入）
    AP_Int8  _test_force_inject_enable;  // テスト用外力注入の有効/無効
    AP_Float _test_force_freq;           // テスト用外力の周波数 [Hz]
    AP_Float _test_force_amp;            // テスト用外力の振幅 [N]
    
    // 予測用キャッシュ変数（計算量削減）
    float _omega_rad;                  // ω [rad/s]
    
    // 位相補正用のパラメータ
    AP_Int8  _phase_correction_enabled;  // 位相補正の有効/無効
    AP_Float _phase_correction_threshold; // 位相補正を適用する閾値 [rad]
    
    // 周波数推定制御用（両方式サポート）
    AP_Int8  _freq_estimation_rc_channel;  // 旧方式：チャンネル番号指定（0=無効、1-16=RC1-RC16）
    volatile bool _freq_estimation_switch_state;     // 新方式：RC Aux Function経由
    bool _combined_freq_est_switch;         // 統合されたスイッチ状態（新方式 OR 旧方式）
    
    // 位相補正用の変数
    static constexpr uint8_t PHASE_BUFFER_SIZE = 60;   // 3.0s * 20Hz = 60 samples (データ3秒分)
    float phase_buffer[PHASE_BUFFER_SIZE];             // 位相データバッファ
    uint32_t phase_time_buffer_ms[PHASE_BUFFER_SIZE];  // 位相サンプルの時刻 [ms]
    uint8_t phase_buffer_index = 0;                    // リングバッファの次回書き込みインデックス
    uint8_t phase_buffer_count = 0;                    // バッファ内の有効データ数
    uint8_t phase_decimation_counter = 0;              // ダウンサンプリング用カウンタ
    uint8_t slope_estimation_trigger_counter = 0;      // 推定実行トリガー用カウンタ
    float phase_correction;                            // 累積位相補正量 [rad]
    float estimated_frequency;                         // 推定周波数 [Hz]（ログ用）

    // A,B係数から推定した観測位相（MATLAB相当）
    // phi_obs_axis = atan2(-B, A) をアンラップして連続化したもの
    float ab_phase_unwrapped[RLS_NUM_AXES];
    float ab_phase_prev_wrapped[RLS_NUM_AXES];
    bool  ab_phase_initialized[RLS_NUM_AXES];
    float ab_amp[RLS_NUM_AXES];
    
    // RLS関数
    void rls_init();
    void rls_update(const Vector3f& x_input, const Vector3f& y_output);
    void update_prediction_cache();  // 予測用キャッシュ更新
    
    // 位相補正関数
    void phase_correction_init();
    void phase_correction_update();
    float unwrap_phase(float prev, float curr);  // 位相アンラップ
    float linear_fit_slope(const float* buffer, uint8_t count);  // 最小二乗法で傾きを計算
    float linear_fit_slope_time(const float* phase, const uint32_t* time_ms, uint8_t count);  // 位相-時刻で傾きを計算[rad/s]
    
    // 既存の関数
    Quaternion calculate_correction_from_force(const Vector3f& force) const;
    Vector3f calculate_correction_euler_from_force(const Vector3f& force) const;
    float apply_lowpass_filter(float input, float& state, float dt, float cutoff_freq) const;

    // 揺れ制御のゲイン
    AP_Float    _correction_gain;
    // ローパスフィルタのカットオフ周波数 [Hz]（パラメータ化）
    AP_Float    _filter_cutoff_freq;
    
    // 周波数推定フィルタ係数
    AP_Float    _freq_est_alpha;
    
    // 補正角度の最大値
    AP_Float    _max_correction_angle;

    // 定数
    static constexpr uint32_t TIMEOUT_MS            = 500;
    static constexpr float    FORCE_THRESHOLD       = 0.0f;
    static constexpr float    g                     = 9.7985f;
    static constexpr float    THRUST_SCALE          = 6.3157f;
    static constexpr float    THRUST_OFFSET         = -0.9995f;
    static constexpr float    UAV_mass              = 1.4f;
    
    // RLS関連定数
    static constexpr float    RLS_MIN_LAMBDA        = 0.9f;
    static constexpr float    RLS_MAX_LAMBDA        = 0.9999f;
    static constexpr float    RLS_MIN_COVARIANCE    = 0.001f;
    static constexpr float    RLS_MAX_COVARIANCE    = 1000.0f;
    
    // 周波数範囲制限（振り子長0.3m~2.0mに対応）
    static constexpr float    FREQ_MIN              = 0.35f;  // 2.0m相当 [Hz]
    static constexpr float    FREQ_MAX              = 0.91f;  // 0.3m相当 [Hz]
    
    // 離陸検知用の変数
    bool _has_taken_off = false;  // 離陸済みフラグ
    
    // 周波数推定制御用の変数
    bool _freq_estimation_active = false;    // 現在推定中かどうか
    bool _freq_estimation_prev_switch = false; // 前回のスイッチ状態
    float _freq_estimation_result = 0.0f;    // 推定終了時の周波数結果 [Hz]
    
    // ヘルパー関数
    bool check_frequency_range(float freq);  // 周波数範囲チェック
    bool is_taking_off();  // 離陸検知
};
