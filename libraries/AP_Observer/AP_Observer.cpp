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
    
    // @Param: LAMBDA
    // @DisplayName: RLS Forgetting Factor
    // @Description: Recursive least squares forgetting factor (0.9-1.0)
    // @Range: 0.9 1.0
    // @User: Advanced
    AP_GROUPINFO("LAMBDA", 2, AP_Observer, _lambda_forget, 0.95f),
    
    // @Param: RLS_FREQ
    // @DisplayName: RLS Estimation Frequency
    // @Description: Frequency of periodic disturbance to estimate [Hz]
    // @Range: 0.1 10.0
    // @User: Advanced
    AP_GROUPINFO("RLS_FREQ", 3, AP_Observer, _rls_frequency, 1.0f),
    
    // @Param: PRED_TIME
    // @DisplayName: Prediction Time Horizon
    // @Description: Time ahead to predict external forces [ms]
    // @Range: 10.0 500.0
    // @User: Advanced
    AP_GROUPINFO("PRED_TIME", 4, AP_Observer, _prediction_time_ms, 100.0f),

    // @Param: DEBUG_INTERVAL
    // @DisplayName: Observer Debug Output Interval
    // @Description: Interval for debug message output (cycles)
    // @Range: 1 1000
    // @User: Advanced
    AP_GROUPINFO("DEBUG_INTERVAL", 5, AP_Observer, _debug_output_interval, 10.0f),
    AP_GROUPEND
};

void AP_Observer::init() {
    AP_Param::setup_object_defaults(this, var_info);

    float sample_freq = 100.0f;
    _payload_filter.set_cutoff_frequency(sample_freq, _filter_cutoff_freq.get());

    // 基本変数初期化
    current_filtered_force = Vector3f();
    current_correction_quat = Quaternion(1,0,0,0);
    last_update_ms = 0;
    _payload_filtered = Vector3f();
    filter_initialized = true;

    // RLS初期化
    init_rls();

    gcs().send_text(MAV_SEVERITY_INFO, 
        "AP_Observer: initialized with %.1fHz filter, RLS freq=%.2f, pred=%.1fms", 
        _filter_cutoff_freq.get(), _rls_frequency.get(), _prediction_time_ms.get());
}

void AP_Observer::init_rls() {
    // P行列を単位行列×大きな値で初期化
    P_matrix.identity();
    P_matrix *= INITIAL_P_VALUE;
    
    // パラメータベクトルをゼロ初期化
    theta_x = Vector3f(0.0f, 0.0f, 0.0f);  // [A_x, B_x, C_x]
    theta_y = Vector3f(0.0f, 0.0f, 0.0f);  // [A_y, B_y, C_y]  
    theta_z = Vector3f(0.0f, 0.0f, 0.0f);  // [A_z, B_z, C_z]
    
    rls_predicted_force = Vector3f();
    rls_current_force = Vector3f();
    rls_initialized = false;
    data_count = 0;
    rls_start_time_ms = AP_HAL::millis();
    
    gcs().send_text(MAV_SEVERITY_INFO, "RLS: Cold start initialization");
}

void AP_Observer::update() {
    AP_Motors* motors = AP::motors();
    if (!motors) {
        gcs().send_text(MAV_SEVERITY_INFO, "AP_Observer: motors nullptr");
        return;
    }

    // 外力計算（既存コード）
    float throttle = motors->get_throttle_out();
    float thrust   = -(THRUST_SCALE * throttle + THRUST_OFFSET) * g;
    Vector3f accel = AP::ins().get_accel();
    Vector3f measured_force;
    measured_force.x = UAV_mass * accel.x;
    measured_force.y = UAV_mass * accel.y;
    measured_force.z = UAV_mass * accel.z - thrust;

    // 従来のフィルタ（常に動作）
    _payload_filtered = _payload_filter.apply(measured_force);

    // RLS処理
    if (!rls_initialized) {
        handle_cold_start(measured_force);
        current_filtered_force = _payload_filtered;  // フォールバック
    } else {
        update_rls(measured_force);
        // 予測値を姿勢補正に使用（先読み制御）[web:66][web:69]
        current_filtered_force = rls_predicted_force;
    }

    current_correction_quat = calculate_correction_from_force(current_filtered_force);
    last_update_ms = AP_HAL::millis();

    // デバッグ出力（外部設定可能な間隔）
    if ((++counter % (uint32_t)_debug_output_interval.get()) == 0) {
        uint32_t send_time_ms = AP_HAL::millis();
        if (rls_initialized) {
            gcs().send_text(MAV_SEVERITY_INFO,
                "RLS: F_curr=[%.3f,%.3f,%.3f] F_pred=[%.3f,%.3f,%.3f] Δt=%.1fms time=%lu",
                rls_current_force.x, rls_current_force.y, rls_current_force.z,
                rls_predicted_force.x, rls_predicted_force.y, rls_predicted_force.z,
                _prediction_time_ms.get(),
                send_time_ms);
        } else {
            gcs().send_text(MAV_SEVERITY_INFO,
                "RLS: Cold start %lu/%lu time=%lu", data_count, MIN_DATA_FOR_RLS, send_time_ms);
        }
    }
}

void AP_Observer::handle_cold_start(const Vector3f& measured_force) {
    data_count++;
    
    if (data_count >= MIN_DATA_FOR_RLS) {
        rls_initialized = true;
        gcs().send_text(MAV_SEVERITY_INFO, "RLS: Initialization complete after %lu samples", data_count);
    }
}

void AP_Observer::update_rls(const Vector3f& measured_force) {
    // 現在時刻計算
    uint32_t current_time_ms = AP_HAL::millis();
    float t_current = (current_time_ms - rls_start_time_ms) * 1e-3f;  // 現在時刻[s]
    float delta_t = _prediction_time_ms.get() * 1e-3f;               // 予測時間[s]
    
    // 現在時刻の入力ベクトル（学習用）
    Vector3f x_current = get_input_vector(t_current);
    
    // 未来時刻の入力ベクトル（予測用）
    Vector3f x_future = get_prediction_vector(t_current, delta_t);
    
    // 数値安定性チェック
    if (!check_matrix_stability()) {
        reset_rls_matrix();
        gcs().send_text(MAV_SEVERITY_WARNING, "RLS: Matrix reset due to instability");
        return;
    }
    
    // 各軸についてRLS更新（現在時刻のデータで学習）
    update_rls_axis(theta_x, x_current, measured_force.x);
    update_rls_axis(theta_y, x_current, measured_force.y);
    update_rls_axis(theta_z, x_current, measured_force.z);
    
    // 現在時刻の推定外力計算
    rls_current_force.x = theta_x.dot(x_current);
    rls_current_force.y = theta_y.dot(x_current);
    rls_current_force.z = theta_z.dot(x_current);
    
    // 未来時刻の予測外力計算（先読み制御用）[web:62][web:67]
    rls_predicted_force.x = theta_x.dot(x_future);
    rls_predicted_force.y = theta_y.dot(x_future);
    rls_predicted_force.z = theta_z.dot(x_future);
}

Vector3f AP_Observer::get_input_vector(float t) const {
    float omega = 2.0f * M_PI * _rls_frequency.get();
    return Vector3f(sinf(omega * t), cosf(omega * t), 1.0f);
}

Vector3f AP_Observer::get_prediction_vector(float t_current, float delta_t) const {
    float omega = 2.0f * M_PI * _rls_frequency.get();

    // 三角関数の加法定理を使用して効率的に計算 [web:71]
    // sin(ω(t+Δt)) = sin(ωt)cos(ωΔt) + cos(ωt)sin(ωΔt)
    // cos(ω(t+Δt)) = cos(ωt)cos(ωΔt) - sin(ωt)sin(ωΔt)
    
    float sin_wt = sinf(omega * t_current);
    float cos_wt = cosf(omega * t_current);
    float sin_wdt = sinf(omega * delta_t);
    float cos_wdt = cosf(omega * delta_t);
    
    float sin_future = sin_wt * cos_wdt + cos_wt * sin_wdt;
    float cos_future = cos_wt * cos_wdt - sin_wt * sin_wdt;
    
    return Vector3f(sin_future, cos_future, 1.0f);
}

void AP_Observer::update_rls_axis(Vector3f& theta, const Vector3f& x_vec, float y_measured) {
    float y_predicted = theta.dot(x_vec);
    float error = y_measured - y_predicted;
    
    Vector3f P_x = P_matrix * x_vec;
    float denominator = _lambda_forget.get() + x_vec.dot(P_x);
    
    if (denominator < MIN_DENOMINATOR) {
        return;
    }
    
    Vector3f gain = P_x / denominator;
    theta += gain * error;
    
    // 正しい外積計算 k * x^T
    Matrix3f K_xT;
    for (uint8_t i = 0; i < 3; i++) {
        for (uint8_t j = 0; j < 3; j++) {
            K_xT[i][j] = gain[i] * x_vec[j];
        }
    }
    Matrix3f K_xT_P = K_xT * P_matrix;
    P_matrix = (P_matrix - K_xT_P) / _lambda_forget.get();
}

bool AP_Observer::check_matrix_stability() {
    // P行列の対角成分をチェック（簡易版条件数）
    float max_diag = MAX(MAX(P_matrix[0][0], P_matrix[1][1]), P_matrix[2][2]);
    float min_diag = MIN(MIN(P_matrix[0][0], P_matrix[1][1]), P_matrix[2][2]);
    
    if (min_diag <= 0 || (max_diag / min_diag) > MAX_CONDITION_NUMBER) {
        return false;
    }
    return true;
}

void AP_Observer::reset_rls_matrix() {
    P_matrix.identity();
    P_matrix *= INITIAL_P_VALUE * 0.1f;  // 前回より小さい値で再初期化
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
