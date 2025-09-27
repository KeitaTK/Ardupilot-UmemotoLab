#include "AP_Observer.h"

// パラメータテーブル定義
// 実際にpymavlinkから呼び出すときは接頭か自動生成される。
// 例えば、CORR_GAIN -> OBS_CORR_GAIN のように変換される。どんな名前かは調べる
const AP_Param::GroupInfo AP_Observer::var_info[] = {
    // @Param: CORR_GAIN
    // @DisplayName: Observer Correction Gain
    // @Description: Gain for attitude correction based on external force estimation
    // @Range: 0.0 1.0
    // @User: Advanced
    AP_GROUPINFO("CORR_GAIN", 0, AP_Observer, _correction_gain, 0.004f),
    // @Param: OBS_FILT_CUTOFF
    // @DisplayName: Observer Filter Cutoff Frequency
    // @Description: Low-pass filter cutoff frequency [Hz]
    // @Range: 1.0 100.0
    // @User: Advanced
    AP_GROUPINFO("FILT_CUTOFF", 1, AP_Observer, _filter_cutoff_freq, 20.0f),

    AP_GROUPEND
};

void AP_Observer::init(){
    AP_Param::setup_object_defaults(this, var_info);

    float sample_freq = 100.0f; // サンプリング周波数 [Hz]
    _payload_filter.set_cutoff_frequency(sample_freq, _filter_cutoff_freq.get());

    current_filtered_force = Vector3f();
    current_correction_quat = Quaternion(1,0,0,0);
    last_update_ms = 0;
    _payload_filtered = Vector3f();
    filter_initialized = true;
    
    // ログ記録用変数の初期化
    _last_log_ms = 0;

    gcs().send_text(MAV_SEVERITY_INFO, "AP_Observer: initialized with %.1fHz filter, logging enabled", 
                    _filter_cutoff_freq.get());
}

void AP_Observer::update() {
    AP_Motors* motors = AP::motors();
    if (!motors) {
        gcs().send_text(MAV_SEVERITY_INFO, "AP_Observer: motors nullptr");
        return;
    }

    float throttle = motors->get_throttle_out();
    float thrust   = -(THRUST_SCALE * throttle + THRUST_OFFSET) * g;
    Vector3f accel = AP::ins().get_accel();
    Vector3f payload;
    payload.x = UAV_mass * accel.x;
    payload.y = UAV_mass * accel.y;
    payload.z = UAV_mass * accel.z - thrust;

    // 固定カットオフでフィルタ適用
    _payload_filtered = _payload_filter.apply(payload);

    current_filtered_force = _payload_filtered;
    current_correction_quat = calculate_correction_from_force(_payload_filtered);
    last_update_ms = AP_HAL::millis();

    // フィルタ後の力をログに記録
    log_filtered_force();

    // // デバッグメッセージ：フィルタ後の値を出力
    // if ((++counter % 100) == 0) {
    //     gcs().send_text(MAV_SEVERITY_INFO,
    //         "PL_FILT=%.3f,%.3f,%.3f",
    //         _payload_filtered.x,
    //         _payload_filtered.y,
    //         _payload_filtered.z
    //     );
    // }
}

// ログ記録用の関数を追加
void AP_Observer::log_filtered_force() {
    uint32_t now_ms = AP_HAL::millis();
    if (now_ms - _last_log_ms < LOG_INTERVAL_MS) {
        return;  // 20ms間隔＝50Hz
    }
    _last_log_ms = now_ms;

    // メッセージ名: "FILT" (4文字以内)
    // フィールド: "Fx,Fy,Fz" (タイムスタンプは自動付加)
    // フォーマット: "fff" (float×3)
    AP::logger().Write("FILT",
                       "Fx,Fy,Fz",
                       "fff",
                       current_filtered_force.x,
                       current_filtered_force.y,
                       current_filtered_force.z);
}
    
Quaternion AP_Observer::calculate_correction_from_force(const Vector3f& force) const {
    float mag = force.length();
    if (mag < FORCE_THRESHOLD) {
        return Quaternion(1, 0, 0, 0);
    }

    float correction_gain = _correction_gain.get();
    float roll  =  force.y * correction_gain / UAV_mass;
    float pitch =  -force.x * correction_gain / UAV_mass;

    roll = constrain_value(roll, -MAX_CORRECTION_ANGLE, MAX_CORRECTION_ANGLE);
    pitch = constrain_value(pitch, -MAX_CORRECTION_ANGLE, MAX_CORRECTION_ANGLE);

    Quaternion q;
    q.from_euler(roll, pitch, 0.0f);
    q.normalize();
    return q;
}
