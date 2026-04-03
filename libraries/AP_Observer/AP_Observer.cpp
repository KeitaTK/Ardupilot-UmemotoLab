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
    
    // @Param: DIST_FREQ
    // @DisplayName: Disturbance Frequency
    // @Description: Frequency of periodic disturbance for RLS estimation [Hz]. Constrained to 0.35-0.91Hz (pendulum length 0.3-2.0m)
    // @Range: 0.35 0.91
    // @User: Advanced
    AP_GROUPINFO("DIST_FREQ", 4, AP_Observer, _disturbance_freq, 0.6f),
    
    // @Param: PRED_TIME
    // @DisplayName: Prediction Time
    // @Description: Time ahead for force prediction [seconds]
    // @Range: 0.0 0.5
    // @User: Advanced
    AP_GROUPINFO("PRED_TIME", 5, AP_Observer, _prediction_time, 0.01f),
    
    // @Param: PHASE_CORR
    // @DisplayName: Phase Correction Enable
    // @Description: Enable or disable phase correction for disturbance frequency
    // @Values: 0:Disabled,1:Enabled
    // @User: Advanced
    AP_GROUPINFO("PHASE_CORR", 6, AP_Observer, _phase_correction_enabled, 1),
    
    // @Param: PHASE_THRESH
    // @DisplayName: Phase Correction Threshold
    // @Description: Threshold for applying phase correction [rad]. Correction is only applied if error exceeds this value.
    // @Range: 0.0 5.0
    // @User: Advanced
    AP_GROUPINFO("PHASE_THRESH", 7, AP_Observer, _phase_correction_threshold, 0.0f),
    
    // @Param: TEST_INJECT
    // @DisplayName: Test Force Injection Enable
    // @Description: Enable test mode to inject known sinusoidal force for RLS validation
    // @Values: 0:Disabled,1:Enabled
    // @User: Advanced
    AP_GROUPINFO("TEST_INJECT", 8, AP_Observer, _test_force_inject_enable, 0),
    
    // @Param: TEST_FREQ
    // @DisplayName: Test Force Frequency
    // @Description: Frequency of injected test force [Hz]
    // @Range: 0.35 0.91
    // @User: Advanced
    AP_GROUPINFO("TEST_FREQ", 9, AP_Observer, _test_force_freq, 0.7f),
    
    // @Param: TEST_AMP
    // @DisplayName: Test Force Amplitude
    // @Description: Amplitude of injected test force [N]
    // @Range: 0.0 10.0
    // @User: Advanced
    AP_GROUPINFO("TEST_AMP", 10, AP_Observer, _test_force_amp, 1.0f),
    
    // @Param: MAX_CORR_ANG
    // @DisplayName: Maximum Correction Angle
    // @Description: Maximum attitude correction angle for roll and pitch [rad]
    // @Range: 0.0 1.0
    // @User: Advanced
    AP_GROUPINFO("MAX_CORR_ANG", 11, AP_Observer, _max_correction_angle, 0.5f),

    // @Param: FREQ_WIN
    // @DisplayName: Zero-Cross Window Length
    // @Description: Window length for zero-cross frequency estimation [s]
    // @Range: 1.0 30.0
    // @User: Advanced
    AP_GROUPINFO("FREQ_WIN", 12, AP_Observer, _freq_est_window_sec, 10.0f),

    AP_GROUPEND
};

void AP_Observer::init() {
    // パラメータのデフォルト値設定
    AP_Param::setup_object_defaults(this, var_info);

    // フィルタ初期化
    float sample_freq = 100.0f; // サンプリング周波数 [Hz]
    _payload_filter.set_cutoff_frequency(sample_freq, _filter_cutoff_freq.get());

    // 基本変数初期化
    current_filtered_force = Vector3f();
    current_correction_quat = Quaternion(1, 0, 0, 0);
    last_update_ms = 0;
    _payload_filtered = Vector3f();
    filter_initialized = true;

    // RLS初期化
    rls_init();
    
    // 予測用キャッシュ初期化
    update_prediction_cache();
    
    // 位相補正初期化
    phase_correction_init();

    // A,B由来位相（観測位相）初期化
    for (uint8_t axis = 0; axis < RLS_NUM_AXES; axis++) {
        ab_phase_unwrapped[axis] = 0.0f;
        ab_phase_prev_wrapped[axis] = 0.0f;
        ab_phase_initialized[axis] = false;
        ab_amp[axis] = 0.0f;
    }
    
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

void AP_Observer::rls_init() {
    // パラメータの範囲チェックと制限
    float init_cov = constrain_value(_rls_initial_covariance.get(), RLS_MIN_COVARIANCE, RLS_MAX_COVARIANCE);
    
    // 全軸のパラメータベクトル初期化
    for (uint8_t axis = 0; axis < RLS_NUM_AXES; axis++) {
        for (uint8_t i = 0; i < RLS_PARAM_SIZE; i++) {
            rls_theta[axis][i] = 0.0f;
        }
    }
    
    // 全軸の共分散行列初期化（対角行列）
    for (uint8_t axis = 0; axis < RLS_NUM_AXES; axis++) {
        for (uint8_t i = 0; i < RLS_PARAM_SIZE; i++) {
            for (uint8_t j = 0; j < RLS_PARAM_SIZE; j++) {
                if (i == j) {
                    rls_P[axis][i][j] = init_cov;  // 対角成分
                } else {
                    rls_P[axis][i][j] = 0.0f;      // 非対角成分
                }
            }
        }
    }
    
    rls_sample_count = 0;
    rls_start_time_ms = get_current_time_ms();  // 開始時刻を記録
    
    // 位相補正・周波数推定用の変数を初期化
    phase_correction = 0.0f;
    
    rls_initialized = true;
}

void AP_Observer::reset_frequency_estimation() {
    // 周波数推定のみをリセット（RLSと位相補正は継続）
#if HAL_GCS_ENABLED
    gcs().send_text(MAV_SEVERITY_INFO, "AP_Observer: Resetting frequency estimation only");
#endif
    
    // 推定周波数を初期値にリセット（スイッチON時に初期化）
    // RLSパラメータや位相補正バッファは保持される -> 修正：位相バッファもリセットすべき
    estimated_frequency = _disturbance_freq.get();
    
    // 位相補正バッファのリセット
    phase_correction = 0.0f;

    // ゼロクロス推定状態のリセット
    zero_cross_reset_state();
    
#if HAL_GCS_ENABLED
    gcs().send_text(MAV_SEVERITY_INFO, "AP_Observer: Frequency reset to %.3fHz (RLS/Phase continue)", (double)estimated_frequency);
#endif
}

void AP_Observer::rls_update(const Vector3f& x_input, const Vector3f& y_output) {
    if (!rls_initialized) {
#if HAL_GCS_ENABLED
        gcs().send_text(MAV_SEVERITY_WARNING, "RLS: not initialized!");
#endif
        return;
    }
    
    float lambda = constrain_value(_rls_forgetting_factor.get(), RLS_MIN_LAMBDA, RLS_MAX_LAMBDA);
    
    // 経過時間計算 [秒]
    float t = (get_current_time_ms() - rls_start_time_ms) / 1000.0f;
    
    // 角周波数 ω = 2πf [rad/s]
    // 位相補正が有効な場合は推定された周波数を使用
    float freq_to_use = (_phase_correction_enabled.get() == 1) ? estimated_frequency : _disturbance_freq.get();
    float omega = freq_to_use * 2.0f * M_PI;
    
    // 時間ベース位相計算（RLS入力用、補正を適用）
    float phase = omega * t - phase_correction;
    
    // 入力ベクトル x[n] = [sin(phase), cos(phase), 1]
    float x_extended[RLS_PARAM_SIZE];
    x_extended[0] = sinf(phase);  // sin項（補正済み位相）
    x_extended[1] = cosf(phase);  // cos項（補正済み位相）
    x_extended[2] = 1.0f;         // 定常偏差項
    
    // デバッグ用
    static uint32_t debug_counter = 0;
    bool do_debug = (++debug_counter % 100) == 0;  // 100回に1回に変更
    
    // 各軸に対して独立にRLS実行
    for (uint8_t axis = 0; axis < RLS_NUM_AXES; axis++) {
        // 出力値 y[n]
        float y_n = 0.0f;
        switch (axis) {
            case 0: y_n = y_output.x; break;
            case 1: y_n = y_output.y; break;
            case 2: y_n = y_output.z; break;
        }
        
        // 予測値計算: y_pred = x^T * θ
        float y_pred = 0.0f;
        for (uint8_t i = 0; i < RLS_PARAM_SIZE; i++) {
            y_pred += x_extended[i] * rls_theta[axis][i];
        }
        
        // 予測誤差: e[n] = y[n] - y_pred
        float prediction_error = y_n - y_pred;
        
        // P * x を計算
        float P_x[RLS_PARAM_SIZE];
        for (uint8_t i = 0; i < RLS_PARAM_SIZE; i++) {
            P_x[i] = 0.0f;
            for (uint8_t j = 0; j < RLS_PARAM_SIZE; j++) {
                P_x[i] += rls_P[axis][i][j] * x_extended[j];
            }
        }
        
        // 分母計算: λ + x^T * P * x
        float denominator = lambda;
        for (uint8_t i = 0; i < RLS_PARAM_SIZE; i++) {
            denominator += x_extended[i] * P_x[i];
        }
        
        // 数値安定性チェック
        if (fabsf(denominator) < 1e-12f) {
#if HAL_GCS_ENABLED
            if (do_debug && axis == 0) {
                gcs().send_text(MAV_SEVERITY_WARNING, "RLS[%d]: denom=%.9f too small", axis, denominator);
            }
#endif
            continue;
        }
        
        // ゲインベクトル: K = P * x / denom
        float K[RLS_PARAM_SIZE];
        for (uint8_t i = 0; i < RLS_PARAM_SIZE; i++) {
            K[i] = P_x[i] / denominator;
        }
        
        // パラメータ更新: θ[n] = θ[n-1] + K * e
        for (uint8_t i = 0; i < RLS_PARAM_SIZE; i++) {
            rls_theta[axis][i] += K[i] * prediction_error;
        }
        
        // 共分散行列更新: P[n] = (P[n-1] - K * x^T * P[n-1]) / λ
        for (uint8_t i = 0; i < RLS_PARAM_SIZE; i++) {
            for (uint8_t j = 0; j < RLS_PARAM_SIZE; j++) {
                rls_P[axis][i][j] = (rls_P[axis][i][j] - K[i] * P_x[j]) / lambda;
                // 数値安定性確保
                rls_P[axis][i][j] = constrain_value(rls_P[axis][i][j], 
                                                      RLS_MIN_COVARIANCE, 
                                                      RLS_MAX_COVARIANCE);
            }
        }
        
        // デバッグ出力（X軸のみ）
#if HAL_GCS_ENABLED
        if (do_debug && axis == 0) {
            gcs().send_text(MAV_SEVERITY_INFO,
                "RLS[%d]: t=%.2fs ω=%.3f sin=%.3f cos=%.3f",
                axis, t, omega, x_extended[0], x_extended[1]
            );
            gcs().send_text(MAV_SEVERITY_INFO,
                "RLS[%d]: y=%.3f y_pred=%.3f err=%.3f",
                axis, y_n, y_pred, prediction_error
            );
            gcs().send_text(MAV_SEVERITY_INFO,
                "RLS[%d]: A=%.3f B=%.3f C=%.3f",
                axis, rls_theta[axis][0], rls_theta[axis][1], rls_theta[axis][2]
            );
        }
#endif
    }

    // --- A,B係数から観測位相を推定 ---
    // y = A*sin(phase) + B*cos(phase) = R*sin(phase + phi)
    // したがって phi = atan2(B, A)
    // 注意: 振幅が小さい場合は位相が不安定になるため、最小振幅でガードする。
    // 位相推定（unwrap）の初期化は緩めで良いが、周波数推定に使う位相バッファへ入れる値は
    // できるだけSNRの高い（振幅が十分大きい）サンプルに限定して外れ値を抑える。
    static constexpr float AB_PHASE_MIN_AMP_INIT = 1.0e-4f;  // unwrap初期化用 [N]

    for (uint8_t axis = 0; axis < RLS_NUM_AXES; axis++) {
        const float A = rls_theta[axis][0];
        const float B = rls_theta[axis][1];
        const float amp = sqrtf(A * A + B * B);
        ab_amp[axis] = amp;

        if (amp < AB_PHASE_MIN_AMP_INIT) {
            continue;
        }

        const float phi_wrapped = atan2f(B, A);
        if (!ab_phase_initialized[axis]) {
            ab_phase_prev_wrapped[axis] = phi_wrapped;
            ab_phase_unwrapped[axis] = phi_wrapped;
            ab_phase_initialized[axis] = true;
        } else {
            // ラップ角の差分を[-pi,pi]に収めてから連続位相へ積分
            float dphi = phi_wrapped - ab_phase_prev_wrapped[axis];
            if (dphi > M_PI) {
                dphi -= 2.0f * M_PI;
            } else if (dphi < -M_PI) {
                dphi += 2.0f * M_PI;
            }
            ab_phase_unwrapped[axis] += dphi;
            ab_phase_prev_wrapped[axis] = phi_wrapped;
        }
    }
    
    rls_sample_count++;
}

void AP_Observer::update_prediction_cache() {
    // ω = 2πf [rad/s]
    // 位相補正が有効な場合は推定された周波数を使用
    float freq_to_use = (_phase_correction_enabled.get() == 1) ? estimated_frequency : _disturbance_freq.get();
    _omega_rad = freq_to_use * 2.0f * M_PI;
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
    
        // 周波数推定制御（RC Aux Function方式）
        // RC8_OPTION=316 などでスイッチを割り当て
        // RC Aux Functionが既にデバウンス処理を行っているため、ここでは単純なエッジ検出のみ
        const bool current_switch = _freq_estimation_switch_state;

        // スイッチの立ち上がりエッジ検出（オフ→オン）
        if (current_switch && !_freq_estimation_prev_switch) {
        // 推定開始：推定周波数を初期値に戻してゼロクロス推定を開始
        _freq_estimation_active = true;
        reset_frequency_estimation();
        zero_cross_start();
        _freq_estimation_result = _disturbance_freq.get();
    #if HAL_GCS_ENABLED
        gcs().send_text(MAV_SEVERITY_INFO, "RLS Freq Est: ON (Reset to %.3fHz)", (double)estimated_frequency);
    #endif
        }
        // スイッチの立ち下がりエッジ検出（オン→オフ）
        else if (!current_switch && _freq_estimation_prev_switch) {
        // 推定終了：最後の推定値を保持して引き続き使用
        _freq_estimation_active = false;
        zero_cross_stop();
        _freq_estimation_result = estimated_frequency;
    #if HAL_GCS_ENABLED
        gcs().send_text(MAV_SEVERITY_INFO, "RLS Freq Est: OFF (Holding %.3fHz)", (double)estimated_frequency);
    #endif
        }

        _freq_estimation_prev_switch = current_switch;
    
    // RLS更新条件：
    // 1. RLSが初期化済み
    // 2. 離陸後である
    // 注意：テスト注入モード（OBS_TEST_INJECT）や周波数推定スイッチに関わらず、
    // 離陸後は常にRLS推定を実行する。これにより、実際の外乱を常時観測できる。
    bool should_update_rls = rls_initialized && _has_taken_off;
    
    if (should_update_rls) {
        Vector3f dummy_input;  // 使用しないダミー
        rls_update(dummy_input, _payload_filtered);
    }

    if (_freq_estimation_active && _zc_window_active) {
        zero_cross_update(_payload_filtered.x);
    }
    
    // パラメータ変更を検出してキャッシュ更新
    static float last_freq = 0.0f;
    static float last_pred_time = 0.0f;
    
    if (fabsf(_disturbance_freq.get() - last_freq) > 0.001f || 
        fabsf(_prediction_time.get() - last_pred_time) > 0.0001f) {
        update_prediction_cache();
        last_freq = _disturbance_freq.get();
        last_pred_time = _prediction_time.get();
        // パラメータ変更時はestimated_frequencyも更新
        estimated_frequency = _disturbance_freq.get();
    }
    
    // 既存の処理：RLS予測外力を使用
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

// RLSパラメータのゲッター関数
Vector3f AP_Observer::get_rls_sin_coeff() const {
    return Vector3f(rls_theta[0][0], rls_theta[1][0], rls_theta[2][0]);
}

Vector3f AP_Observer::get_rls_cos_coeff() const {
    return Vector3f(rls_theta[0][1], rls_theta[1][1], rls_theta[2][1]);
}

Vector3f AP_Observer::get_rls_bias() const {
    return Vector3f(rls_theta[0][2], rls_theta[1][2], rls_theta[2][2]);
}

Vector3f AP_Observer::get_predicted_force() const {
    if (!rls_initialized) {
        return _payload_filtered;  // 初期化前は通常の外力を返す
    }
    
    // 現在時刻 [秒]
    float t = (get_current_time_ms() - rls_start_time_ms) / 1000.0f;

    // Δt秒後の位相をA,B由来の観測位相から生成
    // モデル: F = A*sin(omega*t) + B*cos(omega*t) + C = R*sin(omega*t + phi) + C
    // ここで phi = atan2(B, A)。MATLABで扱っているのは phi_obs = atan2(-B, A) なので
    // phase_for_prediction = omega*(t+dt) - phi_obs とすると R*sin(phase_for_prediction) + C と等価。
    // （符号規約はこの等価性に基づき採用）
    // 注：X軸の観測位相（ab_phase_unwrapped[0]）を全軸の周波数推定に使用
    float sin_omega_t_dt = 0.0f;
    float cos_omega_t_dt = 0.0f;
    bool have_ab_phase = ab_phase_initialized[0];
    if (have_ab_phase) {
        const float phase_pred = _omega_rad * (t + _prediction_time.get()) - ab_phase_unwrapped[0];
        sin_omega_t_dt = sinf(phase_pred);
        cos_omega_t_dt = cosf(phase_pred);
    } else {
        // 初期化前は従来の時間位相にフォールバック
        const float omega_t_dt = _omega_rad * (t + _prediction_time.get()) - phase_correction;
        sin_omega_t_dt = sinf(omega_t_dt);
        cos_omega_t_dt = cosf(omega_t_dt);
    }
    
    // 各軸の予測外力計算: F_pred = A·sin(ω(t+Δt)) + B·cos(ω(t+Δt)) + C
    Vector3f predicted;
    for (uint8_t axis = 0; axis < RLS_NUM_AXES; axis++) {
        float A = rls_theta[axis][0];  // sin係数
        float B = rls_theta[axis][1];  // cos係数
        float C = rls_theta[axis][2];  // 定常偏差
        
        float force = A * sin_omega_t_dt + B * cos_omega_t_dt + C;
        
        switch (axis) {
            case 0: predicted.x = force; break;
            case 1: predicted.y = force; break;
            case 2: predicted.z = force; break;
        }
    }
    
    return predicted;
}

// 位相補正初期化
void AP_Observer::phase_correction_init() {
    phase_correction = 0.0f;
    estimated_frequency = _disturbance_freq.get();
    // 注：_freq_estimation_switch_stateはRC Aux Functionが管理するため、ここでは変更しない

    // A,B由来位相もリセット
    for (uint8_t axis = 0; axis < RLS_NUM_AXES; axis++) {
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

    // A,B由来位相（MATLAB相当）をログへ追加（X,Y両軸）
    float phi_obs_x = ab_phase_unwrapped[0];
    float phi_obs_y = ab_phase_unwrapped[1];
    
    // 周波数フィールド：位相補正ONなら推定値、OFFならパラメータ値
    float log_frequency = (_phase_correction_enabled == 1) ? estimated_frequency : _disturbance_freq.get();

    // ログメッセージをカスタムフォーマットで書き込み
    // OBSV: TimeUS, PLX, PLY, PLZ, AX, AY, BX, BY, CX, CY, F, P, X, Y, SW
    logger->Write("OBSV", "TimeUS,PLX,PLY,PLZ,AX,AY,BX,BY,CX,CY,F,P,X,Y,SW",
                  "s--------------", "F--------------",
                  "QfffffffffffffB",
                  AP_HAL::micros64(),
                  _payload_filtered.x,
                  _payload_filtered.y,
                  _payload_filtered.z,
                  rls_theta[0][0],      // sin係数 X軸
                  rls_theta[1][0],      // sin係数 Y軸
                  rls_theta[0][1],      // cos係数 X軸
                  rls_theta[1][1],      // cos係数 Y軸
                  rls_theta[0][2],      // 定常偏差 X軸
                  rls_theta[1][2],      // 定常偏差 Y軸
                  log_frequency,        // F: 周波数（位相補正ON=推定値、OFF=パラメータ値）
                  phase_correction,     // P: 位相補正
                  phi_obs_x,            // X: 観測位相X
                  phi_obs_y,            // Y: 観測位相Y
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
        reset_frequency_estimation();
        zero_cross_start();
        _freq_estimation_result = _disturbance_freq.get();
    } else if (!active && _freq_estimation_prev_switch) {
        zero_cross_stop();
        _freq_estimation_result = estimated_frequency;
    }

    _freq_estimation_active = active;
    _freq_estimation_switch_state = active;
    _freq_estimation_prev_switch = active;
}


#ifdef AP_OBSERVER_REPLAY_TEST
void AP_Observer::force_rls_update(const Vector3f& payload) {
    _payload_filtered = payload;
    
    if (rls_initialized) {
        Vector3f dummy_input;
        rls_update(dummy_input, _payload_filtered);
    }

    if (_freq_estimation_active && _zc_window_active) {
        zero_cross_update(_payload_filtered.x);
    }

}

void AP_Observer::set_params_for_replay(float freq, float bw, float gain) {
    _disturbance_freq.set(freq);
    _filter_cutoff_freq.set(bw);
    _correction_gain.set(gain);

    // Force RLS params (workaround for AP_Param failure in replay)
    _rls_forgetting_factor.set(0.99f);
    _rls_initial_covariance.set(100.0f);
    _phase_correction_enabled.set(1);

    // ここで推定周波数も初期化
    estimated_frequency = freq;

    // Ensure RLS re-init usage of new params
    update_prediction_cache();
    rls_init();
}
#endif
