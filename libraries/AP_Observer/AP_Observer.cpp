#include "AP_Observer.h"

// パラメータテーブル定義
const AP_Param::GroupInfo AP_Observer::var_info[] = {
    // @Param: CORR_GAIN
    // @DisplayName: Observer Correction Gain
    // @Description: Gain for attitude correction based on external force estimation
    // @Range: 0.0 100
    // @User: Advanced
    AP_GROUPINFO("CORR_GAIN",     0, AP_Observer, _correction_gain,   0.3f),

    // @Param: FORCE_FILT_FREQ
    // @DisplayName: Force Estimate Filter Cutoff Frequency
    // @Description: Low pass filter cutoff frequency for external force estimate
    // @Range: 0.1 50
    // @Units: Hz
    // @User: Advanced
    AP_GROUPINFO("FORCE_FILT_FREQ",1, AP_Observer, _force_filter_freq, 5.0f),

    AP_GROUPEND
};

void AP_Observer::init() {
    const float sample_rate_hz = 100.0f;  // 100Hzに変更
    const float cutoff_hz = _force_filter_freq.get();
    
    // パラメータ妥当性チェック
    if (cutoff_hz <= 0 || cutoff_hz > 50) {
        gcs().send_text(MAV_SEVERITY_WARNING, "AP_Observer: Invalid filter frequency");
        return;
    }
    
    _force_filter.set_cutoff_frequency(sample_rate_hz, cutoff_hz);
    gcs().send_text(MAV_SEVERITY_INFO, "AP_Observer: initialized");
}

void AP_Observer::update() {
    AP_Motors* motors = AP::motors();
    if (!motors) {
        gcs().send_text(MAV_SEVERITY_WARNING, "AP_Observer: motors nullptr");  // WARNINGに変更
        return;
    }

    // スロットル→推力→加速度→外力推定
    float throttle = motors->get_throttle_out();
    float thrust = -(THRUST_SCALE * throttle + THRUST_OFFSET) * g;
    Vector3f accel = AP::ins().get_accel();
    Vector3f payload;
    payload.x = UAV_mass * accel.x;
    payload.y = UAV_mass * accel.y;
    payload.z = UAV_mass * accel.z - thrust;

    // 外力推定値をローパスフィルタ
    current_filtered_force = _force_filter.apply(payload);

    // フィルタ後の外力でクオータニオン補正を計算
    current_correction_quat = calculate_correction_from_force(current_filtered_force);
    current_correction_quat.normalize();

    last_update_ms = AP_HAL::millis();
}

// 外力推定値からクオータニオン補正を生成
Quaternion AP_Observer::calculate_correction_from_force(const Vector3f& force) const {
    float mag = force.length();
    if (mag < FORCE_THRESHOLD) {
        return Quaternion(1, 0, 0, 0);
    }

    float correction_gain = _correction_gain.get();
    float roll  =  force.y * correction_gain / UAV_mass;
    float pitch = -force.x * correction_gain / UAV_mass;

    roll  = constrain_value(roll,  -MAX_CORRECTION_ANGLE, MAX_CORRECTION_ANGLE);
    pitch = constrain_value(pitch, -MAX_CORRECTION_ANGLE, MAX_CORRECTION_ANGLE);

    Quaternion q;
    q.from_euler(roll, pitch, 0.0f);
    return q;
}
