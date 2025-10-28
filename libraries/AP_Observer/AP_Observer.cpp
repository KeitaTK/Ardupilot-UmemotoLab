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
    AP_GROUPINFO("RLS_LAMBDA", 2, AP_Observer, _rls_forgetting_factor, 0.995f),
    
    // @Param: RLS_COV_INIT
    // @DisplayName: RLS Initial Covariance
    // @Description: Initial covariance value for RLS algorithm
    // @Range: 0.001 1000.0
    // @User: Advanced
    AP_GROUPINFO("RLS_COV_INIT", 3, AP_Observer, _rls_initial_covariance, 100.0f),

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

    // 初期化完了メッセージは一旦コメントアウト
    // gcs().send_text(MAV_SEVERITY_INFO, "AP_Observer: initialized with %.1fHz filter", _filter_cutoff_freq.get());
}

void AP_Observer::rls_init() {
    // パラメータの範囲チェックと制限
    float lambda = constrain_value(_rls_forgetting_factor.get(), RLS_MIN_LAMBDA, RLS_MAX_LAMBDA);
    float init_cov = constrain_value(_rls_initial_covariance.get(), RLS_MIN_COVARIANCE, RLS_MAX_COVARIANCE);
    
    // パラメータベクトル初期化
    rls_theta.zero();
    
    // 共分散行列の初期化（対角行列）
    for (uint8_t i = 0; i < RLS_PARAM_SIZE; i++) {
        for (uint8_t j = 0; j < RLS_PARAM_SIZE; j++) {
            if (i == j) {
                rls_P[i][j] = init_cov;  // 対角成分
            } else {
                rls_P[i][j] = 0.0f;      // 非対角成分
            }
        }
    }
    
    rls_sample_count = 0;
    rls_initialized = true;
}

void AP_Observer::rls_update(const Vector3f& x_input, const Vector3f& y_output) {
    if (!rls_initialized) {
        return;
    }
    
    float lambda = constrain_value(_rls_forgetting_factor.get(), RLS_MIN_LAMBDA, RLS_MAX_LAMBDA);
    
    // 各軸に対して独立にRLSを実行
    for (uint8_t axis = 0; axis < 3; axis++) {
        // 入力ベクトル x[n] (この場合は1次元)
        float x_n = 0.0f;
        float y_n = 0.0f;
        
        switch (axis) {
            case 0: // X軸
                x_n = x_input.x;
                y_n = y_output.x;
                break;
            case 1: // Y軸  
                x_n = x_input.y;
                y_n = y_output.y;
                break;
            case 2: // Z軸
                x_n = x_input.z;
                y_n = y_output.z;
                break;
        }
        
        // 入力が十分小さい場合はスキップ
        if (fabsf(x_n) < 1e-6f) {
            continue;
        }
        
        // 予測誤差計算: e[n] = y[n] - x[n]^T * θ[n-1]
        float theta_prev = 0.0f;
        switch (axis) {
            case 0: theta_prev = rls_theta.x; break;
            case 1: theta_prev = rls_theta.y; break;
            case 2: theta_prev = rls_theta.z; break;
        }
        
        float prediction_error = y_n - x_n * theta_prev;
        
        // ゲイン計算: K[n] = P[n-1] * x[n] / (λ + x[n]^T * P[n-1] * x[n])
        float P_prev = rls_P[axis][axis];
        float denominator = lambda + x_n * P_prev * x_n;
        
        // 数値安定性のチェック
        if (fabsf(denominator) < 1e-12f) {
            continue;
        }
        
        float gain = P_prev * x_n / denominator;
        
        // パラメータ更新: θ[n] = θ[n-1] + K[n] * e[n]
        float theta_new = theta_prev + gain * prediction_error;
        
        // 共分散行列更新: P[n] = (P[n-1] - K[n] * x[n]^T * P[n-1]) / λ
        float P_new = (P_prev - gain * x_n * P_prev) / lambda;
        
        // 共分散行列の数値安定性確保
        P_new = constrain_value(P_new, RLS_MIN_COVARIANCE, RLS_MAX_COVARIANCE);
        
        // 結果を保存
        switch (axis) {
            case 0: rls_theta.x = theta_new; break;
            case 1: rls_theta.y = theta_new; break;
            case 2: rls_theta.z = theta_new; break;
        }
        rls_P[axis][axis] = P_new;
    }
    
    rls_sample_count++;
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

    // RLS更新（加速度を入力、フィルタ後の力を出力として使用）
    if (rls_initialized) {
        rls_update(accel, _payload_filtered);
    }

    // 既存の処理
    current_filtered_force = _payload_filtered;
    current_correction_quat = calculate_correction_from_force(_payload_filtered);
    last_update_ms = AP_HAL::millis();

    // デバッグメッセージはコメントアウト
    // if ((++counter % 100) == 0) {
    //     gcs().send_text(MAV_SEVERITY_INFO,
    //         "PL_FILT=%.3f,%.3f,%.3f RLS_θ=%.3f,%.3f,%.3f",
    //         _payload_filtered.x, _payload_filtered.y, _payload_filtered.z,
    //         rls_theta.x, rls_theta.y, rls_theta.z
    //     );
    // }
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
