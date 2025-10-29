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
    // @Description: Frequency of periodic disturbance for RLS estimation [Hz]
    // @Range: 0.1 10.0
    // @User: Advanced
    AP_GROUPINFO("DIST_FREQ", 4, AP_Observer, _disturbance_freq, 0.6f),
    
    // @Param: PRED_TIME
    // @DisplayName: Prediction Time
    // @Description: Time ahead for force prediction [seconds]
    // @Range: 0.0 0.5
    // @User: Advanced
    AP_GROUPINFO("PRED_TIME", 5, AP_Observer, _prediction_time, 0.01f),

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

void AP_Observer::rls_update(const Vector3f& x_input, const Vector3f& y_output) {
    if (!rls_initialized) {
        gcs().send_text(MAV_SEVERITY_WARNING, "RLS: not initialized!");
        return;
    }
    
    float lambda = constrain_value(_rls_forgetting_factor.get(), RLS_MIN_LAMBDA, RLS_MAX_LAMBDA);
    
    // 経過時間計算 [秒]
    float t = (AP_HAL::millis() - rls_start_time_ms) / 1000.0f;
    
    // 角周波数 ω = 2πf [rad/s]
    float omega = _disturbance_freq.get() * 2.0f * M_PI;
    
    // 入力ベクトル x[n] = [sin(ωt), cos(ωt), 1]
    float x_extended[RLS_PARAM_SIZE];
    x_extended[0] = sinf(omega * t);  // sin項
    x_extended[1] = cosf(omega * t);  // cos項
    x_extended[2] = 1.0f;             // 定常偏差項
    
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
            if (do_debug && axis == 0) {
                gcs().send_text(MAV_SEVERITY_WARNING, "RLS[%d]: denom=%.9f too small", axis, denominator);
            }
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
    
    // 加速度取得
    Vector3f accel = AP::ins().get_accel();
    
    // ペイロード力計算
    Vector3f payload;
    payload.x = UAV_mass * accel.x;
    payload.y = UAV_mass * accel.y;
    payload.z = UAV_mass * accel.z - thrust;

    // フィルタ適用
    _payload_filtered = _payload_filter.apply(payload);

    // RLS更新（時間ベースの周期外乱推定）
    // 入力は使わず、フィルタ後の力を直接出力として使用
    if (rls_initialized) {
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
    }

    // 既存の処理：RLS予測外力を使用
    current_filtered_force = get_predicted_force();  // Δt秒後の予測外力
    current_correction_quat = calculate_correction_from_force(current_filtered_force);
    last_update_ms = AP_HAL::millis();

    // デバッグメッセージ - RLS診断用（100回に1回に変更）
    if ((++counter % 100) == 0) {
        gcs().send_text(MAV_SEVERITY_INFO,
            "Observer: PL_FILT=%.3f,%.3f,%.3f",
            _payload_filtered.x, _payload_filtered.y, _payload_filtered.z
        );
        gcs().send_text(MAV_SEVERITY_INFO,
            "RLS_DIAG: init=%d samples=%lu ω=%.3f", 
            rls_initialized, (unsigned long)rls_sample_count,
            _omega_rad
        );
        // A (sin係数)
        gcs().send_text(MAV_SEVERITY_INFO,
            "RLS_A: %.3f,%.3f,%.3f",
            rls_theta[0][0], rls_theta[1][0], rls_theta[2][0]
        );
        // B (cos係数)
        gcs().send_text(MAV_SEVERITY_INFO,
            "RLS_B: %.3f,%.3f,%.3f",
            rls_theta[0][1], rls_theta[1][1], rls_theta[2][1]
        );
        // C (定常偏差)
        gcs().send_text(MAV_SEVERITY_INFO,
            "RLS_C: %.3f,%.3f,%.3f",
            rls_theta[0][2], rls_theta[1][2], rls_theta[2][2]
        );
        // 共分散行列の対角成分（パラメータの不確実性）
        gcs().send_text(MAV_SEVERITY_INFO,
            "RLS_P[0]: %.3f,%.3f,%.3f",
            rls_P[0][0][0], rls_P[0][1][1], rls_P[0][2][2]
        );
        // 予測外力
        Vector3f pred = get_predicted_force();
        gcs().send_text(MAV_SEVERITY_INFO,
            "PRED_F: %.3f,%.3f,%.3f dt=%.3f",
            pred.x, pred.y, pred.z, _prediction_time.get()
        );
    }
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
    
    // Δt秒後の位相 ω(t+Δt) [rad]
    float omega_t_dt = _omega_rad * (t + _prediction_time.get());
    
    // Δt秒後のsin/cos値を直接計算
    float sin_omega_t_dt = sinf(omega_t_dt);
    float cos_omega_t_dt = cosf(omega_t_dt);
    
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
