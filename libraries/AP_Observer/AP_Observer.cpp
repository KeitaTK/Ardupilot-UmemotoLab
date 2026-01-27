#include "AP_Observer.h"

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

    // @Param: FREQ_EST_CH
    // @DisplayName: Frequency estimation RC channel
    // @Description: RC channel for frequency estimation control (0=disabled, use RC7_OPTION=316 instead). Legacy method for compatibility.
    // @Values: 0:Disabled,5:RC5,6:RC6,7:RC7,8:RC8,9:RC9,10:RC10,11:RC11,12:RC12,13:RC13,14:RC14,15:RC15,16:RC16
    // @User: Advanced
    AP_GROUPINFO("FREQ_EST_CH", 11, AP_Observer, _freq_estimation_rc_channel, 7),

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
    
    // 周波数推定制御初期化（両方式サポート）
    _freq_estimation_rc_channel.set(0);  // デフォルト無効
    _freq_estimation_switch_state = false;  // RC Aux Function経由で制御
    _freq_estimation_active = false;
    _freq_estimation_prev_switch = false;
    _freq_estimation_result = _disturbance_freq.get();
    _freq_estimation_switch_state = false;  // RC Aux Function経由で制御

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
    rls_start_time_ms = AP_HAL::millis();  // 開始時刻を記録
    rls_initialized = true;
}

void AP_Observer::reset_frequency_estimation() {
    // RLS周波数推定パラメータをリセット（閾値チェック無効化）
#if HAL_GCS_ENABLED
    gcs().send_text(MAV_SEVERITY_INFO, "AP_Observer: Resetting frequency estimation");
#endif
    
    // RLSパラメータと共分散行列の再初期化
    rls_init();
    
    // 位相補正の再初期化
    phase_correction_init();
    
#if HAL_GCS_ENABLED
    gcs().send_text(MAV_SEVERITY_INFO, "AP_Observer: Frequency estimation reset complete");
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
    float t = (AP_HAL::millis() - rls_start_time_ms) / 1000.0f;
    
    // 角周波数 ω = 2πf [rad/s]
    float omega = _disturbance_freq.get() * 2.0f * M_PI;
    
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
    static constexpr float AB_PHASE_MIN_AMP_BUF  = 1.0f;     // 位相バッファ投入用 [N]
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
    
    // 観測位相（X軸）を位相バッファに追加（位相補正/周波数推定用）
    // バッファには「観測位相 - phase_correction」を保存し、位相補正の動きに依存しない
    // 純粋な周波数差（Δω）を推定できるようにする。
    // 振幅が十分大きい場合のみバッファに追加（外れ値・ラップ誤判定を抑制）
    if (ab_phase_initialized[0] && (ab_amp[0] >= AB_PHASE_MIN_AMP_BUF)) {
        phase_buffer[phase_buffer_index] = ab_phase_unwrapped[0] - phase_correction;
        phase_time_buffer_ms[phase_buffer_index] = AP_HAL::millis();
        phase_buffer_index = (phase_buffer_index + 1) % PHASE_BUFFER_SIZE;
        if (phase_buffer_count < PHASE_BUFFER_SIZE) {
            phase_buffer_count++;
        }
    }
    
    rls_sample_count++;
}

void AP_Observer::update_prediction_cache() {
    // ω = 2πf [rad/s]
    _omega_rad = _disturbance_freq.get() * 2.0f * M_PI;
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
    if (_test_force_inject_enable == 1) {
        // 既知の正弦波外力をpayloadに直接代入
        // 時刻[秒]は実時間(=SITLのシミュレーション時刻)に基づいて計算する
        // counter*0.01 のような固定dt前提は、更新周期が変わると注入周波数がずれるため避ける。
        float t = (AP_HAL::millis() - rls_start_time_ms) * 0.001f;
        float test_omega = _test_force_freq.get() * 2.0f * M_PI;  // [rad/s]
        float amplitude = _test_force_amp.get();                   // [N]
        
        payload.x = amplitude * sinf(test_omega * t);
        payload.y = amplitude * sinf(test_omega * t + M_PI / 2.0f);  // 90度位相差
        payload.z = 0.0f;  // Z軸は0
        
        // 初回のみデバッグメッセージ
        static bool test_mode_announced = false;
        if (!test_mode_announced) {
#if HAL_GCS_ENABLED
            gcs().send_text(MAV_SEVERITY_INFO, 
                "AP_Observer: Test force injection enabled (%.2fHz, %.2fN)",
                _test_force_freq.get(), _test_force_amp.get()
            );
#endif
            test_mode_announced = true;
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
    
    // 周波数推定制御（両方式サポート）
    // 1. 新方式：RC Aux Function経由（RC9_OPTION=316など）
    // 2. 旧方式：OBS_FREQ_EST_CHパラメータで直接チャンネル指定
    bool current_switch = _freq_estimation_switch_state;  // 新方式
    
    // 旧方式もチェック（互換性のため）
    if (_freq_estimation_rc_channel.get() > 0) {
        current_switch = current_switch || read_freq_estimation_switch();
    }
    
    // スイッチの立ち上がりエッジ検出（オフ→オン）
    if (current_switch && !_freq_estimation_prev_switch) {
        // 推定開始：RLSと位相補正を初期値にリセット
        _freq_estimation_active = true;
        reset_frequency_estimation();
        _freq_estimation_result = _disturbance_freq.get();  // 初期設定周波数
#if HAL_GCS_ENABLED
        gcs().send_text(MAV_SEVERITY_INFO, "FreqEst: Started (init=%.3fHz)", _freq_estimation_result);
#endif
    }
    
    // スイッチの立ち下がりエッジ検出（オン→オフ）
    if (!current_switch && _freq_estimation_prev_switch) {
        // 推定終了：推定値を保持
        _freq_estimation_active = false;
        _freq_estimation_result = estimated_frequency;  // 推定終了時の周波数を保存
#if HAL_GCS_ENABLED
        gcs().send_text(MAV_SEVERITY_INFO, "FreqEst: Stopped (result=%.3fHz)", _freq_estimation_result);
#endif
    }
    
    _freq_estimation_prev_switch = current_switch;
    
    // RLS更新条件：
    // 1. 離陸後である
    // 2. かつ以下のいずれか：
    //    a. 推定がアクティブ（RC8スイッチオン）
    //    b. テストモード（OBS_TEST_INJECT=1）
    bool should_update_rls = rls_initialized && _has_taken_off && 
                             (_freq_estimation_active || _test_force_inject_enable.get() == 1);
    
    if (should_update_rls) {
        Vector3f dummy_input;  // 使用しないダミー
        rls_update(dummy_input, _payload_filtered);
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
    
    // 位相補正実行条件：
    // 1. 推定がアクティブ（RC8スイッチオン）
    // 2. または テストモード（OBS_TEST_INJECT=1）
    bool should_update_phase = _freq_estimation_active || _test_force_inject_enable.get() == 1;
    
    // 50回目のループで位相補正を実行
    if (should_update_phase && (counter % 50) == 49) {  // 0-indexed なので49回目=50回目
        phase_correction_update();
    }

    // 既存の処理：RLS予測外力を使用
    current_filtered_force = get_predicted_force();  // Δt秒後の予測外力
    current_correction_quat = calculate_correction_from_force(current_filtered_force);
    current_correction_euler = calculate_correction_euler_from_force(current_filtered_force);
    last_update_ms = AP_HAL::millis();

    // ログをSDカードに記録（毎回記録）
    Write_Observer_Log();
    
    // デバッグメッセージ - 簡潔な形式（10回に1回）
#if HAL_GCS_ENABLED
    if ((++counter % 10) == 0) {
        // 経過時間 [秒]
        float t = (AP_HAL::millis() - rls_start_time_ms) / 1000.0f;
        
        // タイムスタンプ付き元の外力
        gcs().send_text(MAV_SEVERITY_INFO,
            "t=%.2f PL: %.3f %.3f %.3f",
            t, _payload_filtered.x, _payload_filtered.y, _payload_filtered.z
        );
        
        // RLS推定パラメータ（XY軸のみ）
        #if HAL_GCS_ENABLED
        gcs().send_text(MAV_SEVERITY_INFO,
            "A: %.3f %.3f",
            rls_theta[0][0], rls_theta[1][0]
        );
        #endif
        #if HAL_GCS_ENABLED
        gcs().send_text(MAV_SEVERITY_INFO,
            "B: %.3f %.3f",
            rls_theta[0][1], rls_theta[1][1]
        );
        #endif
        #if HAL_GCS_ENABLED
        gcs().send_text(MAV_SEVERITY_INFO,
            "C: %.3f %.3f",
            rls_theta[0][2], rls_theta[1][2]
        );
        #endif
        
        // 予測外力
        Vector3f pred = get_predicted_force();
        #if HAL_GCS_ENABLED
        gcs().send_text(MAV_SEVERITY_INFO,
            "PRED: %.3f %.3f %.3f",
            pred.x, pred.y, pred.z
        );
        #endif
        
        // 共分散行列（コメントアウト）
        // gcs().send_text(MAV_SEVERITY_INFO,
        //     "P[0]: %.3f %.3f %.3f",
        //     rls_P[0][0][0], rls_P[0][1][1], rls_P[0][2][2]
        // );
        
        // RLS診断情報（コメントアウト）
        // gcs().send_text(MAV_SEVERITY_INFO,
        //     "RLS: init=%d samples=%lu ω=%.3f", 
        //     rls_initialized, (unsigned long)rls_sample_count, _omega_rad
        // );
    }
#endif
}
    
Quaternion AP_Observer::calculate_correction_from_force(const Vector3f& force) const {
    float mag = force.length();
    if (mag < FORCE_THRESHOLD) {
        return Quaternion(1, 0, 0, 0);
    }

    float correction_gain = _correction_gain.get();
    float roll  =  force.y * correction_gain / UAV_mass;
    float pitch = -force.x * correction_gain / UAV_mass;

    roll = constrain_value(roll, -MAX_CORRECTION_ANGLE, MAX_CORRECTION_ANGLE);
    pitch = constrain_value(pitch, -MAX_CORRECTION_ANGLE, MAX_CORRECTION_ANGLE);

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

    roll = constrain_value(roll, -MAX_CORRECTION_ANGLE, MAX_CORRECTION_ANGLE);
    pitch = constrain_value(pitch, -MAX_CORRECTION_ANGLE, MAX_CORRECTION_ANGLE);

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
    float t = (AP_HAL::millis() - rls_start_time_ms) / 1000.0f;

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
    phase_buffer_index = 0;
    phase_buffer_count = 0;
    phase_correction = 0.0f;
    estimated_frequency = _disturbance_freq.get();
    _freq_estimation_switch_state = false;  // 初期状態はOFF  // パラメータ値で初期化

    // A,B由来位相もリセット
    for (uint8_t axis = 0; axis < RLS_NUM_AXES; axis++) {
        ab_phase_unwrapped[axis] = 0.0f;
        ab_phase_prev_wrapped[axis] = 0.0f;
        ab_phase_initialized[axis] = false;
        ab_amp[axis] = 0.0f;
    }
    
    // バッファをゼロクリア
    for (uint8_t i = 0; i < PHASE_BUFFER_SIZE; i++) {
        phase_buffer[i] = 0.0f;
        phase_time_buffer_ms[i] = 0;
    }
}

// 位相アンラップ：前回の位相と現在の位相から連続な位相を返す
float AP_Observer::unwrap_phase(float prev, float curr) {
    float diff = curr - prev;
    
    // 位相が±πを超えてジャンプした場合を補正
    if (diff > M_PI) {
        curr -= 2.0f * M_PI;
    } else if (diff < -M_PI) {
        curr += 2.0f * M_PI;
    }
    
    return curr;
}

// 最小二乗法で傾きを計算
// buffer: 位相データ配列
// count: データ数
float AP_Observer::linear_fit_slope(const float* buffer, uint8_t count) {
    if (count < 2) {
        return 0.0f;
    }
    
    // x: 時間インデックス (0, 1, 2, ...)
    // y: 位相値
    float sum_x = 0.0f;
    float sum_y = 0.0f;
    float sum_xy = 0.0f;
    float sum_x2 = 0.0f;
    
    for (uint8_t i = 0; i < count; i++) {
        float x = (float)i;
        float y = buffer[i];
        sum_x += x;
        sum_y += y;
        sum_xy += x * y;
        sum_x2 += x * x;
    }
    
    // 傾き = (n*Σxy - Σx*Σy) / (n*Σx² - (Σx)²)
    float n = (float)count;
    float denominator = n * sum_x2 - sum_x * sum_x;
    
    if (fabsf(denominator) < 1e-9f) {
        return 0.0f;  // ゼロ除算回避
    }
    
    float slope = (n * sum_xy - sum_x * sum_y) / denominator;
    return slope;
}

// 位相-時刻の最小二乗で傾きを計算
// phase: 位相配列 [rad]
// time_ms: 時刻配列 [ms]
// return: 傾き [rad/s]
float AP_Observer::linear_fit_slope_time(const float* phase, const uint32_t* time_ms, uint8_t count)
{
    if (count < 2) {
        return 0.0f;
    }

    const uint32_t t0_ms = time_ms[0];
    float sum_t = 0.0f;
    float sum_p = 0.0f;
    float sum_tp = 0.0f;
    float sum_t2 = 0.0f;

    for (uint8_t i = 0; i < count; i++) {
        const float t = (time_ms[i] - t0_ms) * 0.001f;  // [s]
        const float p = phase[i];                       // [rad]
        sum_t += t;
        sum_p += p;
        sum_tp += t * p;
        sum_t2 += t * t;
    }

    const float n = (float)count;
    const float denominator = n * sum_t2 - sum_t * sum_t;
    if (fabsf(denominator) < 1.0e-9f) {
        return 0.0f;
    }

    // slope [rad/s]
    return (n * sum_tp - sum_t * sum_p) / denominator;
}

// 位相補正の更新（100ループごとに呼ばれる）
void AP_Observer::phase_correction_update() {
    // 位相補正が無効の場合は何もしない（最優先でチェック）
    if (_phase_correction_enabled.get() == 0) {
        return;  // 静かに終了（メッセージ不要）
    }
    
    // バッファが満杯でない場合は警告して終了
    if (phase_buffer_count < PHASE_BUFFER_SIZE) {
        // デバッグ：バッファ状態を間引いて出力（出力過多を避ける）
#if HAL_GCS_ENABLED
        static uint16_t buffer_msg_decim = 0;
        if ((++buffer_msg_decim % 10U) == 0U) {
            gcs().send_text(MAV_SEVERITY_INFO,
                "PhaseCorr: buffer %u/%u amp=%.3f init=%u",
                (unsigned)phase_buffer_count, (unsigned)PHASE_BUFFER_SIZE,
                (double)ab_amp[0], (unsigned)ab_phase_initialized[0]
            );
        }
#endif
        return;
    }
    
    // バッファを時系列順に再配置（リングバッファなので）
    float sorted_buffer[PHASE_BUFFER_SIZE];
    uint32_t sorted_time_ms[PHASE_BUFFER_SIZE];
    for (uint8_t i = 0; i < phase_buffer_count; i++) {
        uint8_t idx = (phase_buffer_index - phase_buffer_count + i + PHASE_BUFFER_SIZE) % PHASE_BUFFER_SIZE;
        sorted_buffer[i] = phase_buffer[idx];
        sorted_time_ms[i] = phase_time_buffer_ms[idx];
    }
    
    // 線形近似で傾きを計算（全サンプルを使用）
    // 時刻でフィットして [rad/s] を得ることで、更新周期の揺らぎやdt仮定に依存しない推定にする
    const float slope_rad_s = linear_fit_slope_time(sorted_buffer, sorted_time_ms, PHASE_BUFFER_SIZE);
    
    // 位相バッファは「A,B係数から推定した観測位相（=モデル位相に対する相対位相）」を格納している。
    // したがって slope_rad_s [rad/s] は「角周波数差 Δω」に相当し、Δf = Δω/(2π) となる。
    const float current_freq = _disturbance_freq.get();
    const float delta_freq_unclamped = slope_rad_s / (2.0f * M_PI);  // [Hz]
    // 位相の外れ値等でΔfが跳ねることがあるため、現実的な範囲に制限して安定化
    const float delta_freq = constrain_value(delta_freq_unclamped, -0.5f, 0.5f);
    const float estimated_freq = current_freq + delta_freq;   // [Hz]
    
    // 周波数範囲チェック：範囲外は警告のみ（リセット無効化）
    if (!check_frequency_range(estimated_freq)) {
#if HAL_GCS_ENABLED
        static uint16_t oor_msg_decim = 0;
        if ((++oor_msg_decim % 10U) == 0U) {
            gcs().send_text(MAV_SEVERITY_WARNING,
                "PhaseCorr: f=%.3fHz (df=%.3f) OutOfRange (%.2f-%.2f) slope=%.4f",
                (double)estimated_freq, (double)delta_freq,
                (double)FREQ_MIN, (double)FREQ_MAX, (double)slope_rad_s
            );
        }
#endif
        // 範囲外の場合も続行（リセットしない）
    }

    // ログ用周波数（レンジ内の推定値のみ採用）
    // 推定がパラメータ(OBS_DIST_FREQ)を勝手に書き換えないよう、ここでは内部推定値のみ更新する。
    static constexpr float FREQ_EST_ALPHA = 0.20f;  // 0..1, 大きいほど追従が速い
    estimated_frequency = estimated_frequency + FREQ_EST_ALPHA * (estimated_freq - estimated_frequency);

    // デバッグ：周波数推定が進んでいることを間引いて出力
#if HAL_GCS_ENABLED
    static uint16_t freq_msg_decim = 0;
    if ((++freq_msg_decim % 5U) == 0U) {
        gcs().send_text(MAV_SEVERITY_INFO,
            "PhaseCorr: f=%.3f est=%.3f (df=%.3f)",
            (double)current_freq, (double)estimated_frequency, (double)delta_freq
        );
    }
#endif
    
    // 位相誤差（相対位相の傾き=周波数差を位相ずれとして積算）
    // 周波数が一致していれば slope_rad_s ≈ 0 になるのが理想。
    const float slope_error = slope_rad_s;

    // バッファ期間全体での位相ずれを計算
    // phase_error [rad] = slope_error [rad/s] * buffer_duration [s]
    const float buffer_duration_s = (sorted_time_ms[PHASE_BUFFER_SIZE - 1] - sorted_time_ms[0]) * 0.001f;
    const float phase_error = slope_error * buffer_duration_s;
    
    // 閾値チェック：誤差が閾値以下なら補正しない
    if (fabsf(phase_error) <= _phase_correction_threshold.get()) {
        // デバッグメッセージ：補正不要だが、現在の累積補正量と推定周波数は送信
#if HAL_GCS_ENABLED
        gcs().send_text(MAV_SEVERITY_INFO,
            "PhaseCorr: err=%.4f est_freq=%.4f Hz corr=%.4f (no correction)",
            phase_error, estimated_freq, phase_correction
        );
#endif
        return;
    }
    
    // phase は omega*t - phase_correction を使用しているため、
    // 観測位相が進む(phase_error>0)場合は model を進める方向に補正する必要がある。
    // よって phase_correction は誤差と逆符号で更新する。
    phase_correction -= phase_error;
    
    // デバッグメッセージ：位相誤差と推定周波数を送信
#if HAL_GCS_ENABLED
    gcs().send_text(MAV_SEVERITY_INFO,
        "PhaseCorr: err=%.4f est_freq=%.4f Hz corr=%.4f",
        phase_error, estimated_freq, phase_correction
    );
#endif
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
                  (uint8_t)(_freq_estimation_switch_state ? 1 : 0));  // SW: RC Aux Functionスイッチ状態（0=オフ、1=オン）
#endif
}

// RCスイッチ状態の設定（RC Aux Function経由で呼び出される）
void AP_Observer::set_freq_estimation_switch(bool enabled) {
    _freq_estimation_switch_state = enabled;
    // デバッグ用GCSメッセージ（頻度制限なし、重要な動作確認のため）
    GCS_SEND_TEXT(MAV_SEVERITY_INFO, "AP_Observer: Freq Est Switch set to %s", enabled ? "ON" : "OFF");
}

// RCチャンネル読み取り（旧方式・互換性のため）
bool AP_Observer::read_freq_estimation_switch() {
    // FREQ_EST_CHパラメータが0なら無効
    int8_t rc_ch = _freq_estimation_rc_channel.get();
    if (rc_ch <= 0 || rc_ch > 16) {
        return false;
    }
    
    // RCチャンネルを取得
    RC_Channel *ch = rc().channel(rc_ch - 1);  // チャンネルは0-indexed
    if (ch == nullptr) {
        return false;
    }
    
    // PWM値を読み取り、閾値と比較（1700以上でON）
    uint16_t pwm = ch->get_radio_in();
    return (pwm >= 1700);
}

