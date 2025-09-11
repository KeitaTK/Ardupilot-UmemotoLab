#include "AP_Observer.h"
#include <AP_AHRS/AP_AHRS.h>


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
    // current_correction_quat = Quaternion(1,0,0,0);
    last_update_ms = 0;
    _payload_filtered = Vector3f();
    filter_initialized = true;


    gcs().send_text(MAV_SEVERITY_INFO, "AP_Observer: initialized with %.1fHz filter", _filter_cutoff_freq.get());
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
    // current_correction_quat = calculate_correction_from_force(_payload_filtered); // クオータニオン補正は無効化
    correction_position = calculate_correction_position(_payload_filtered); // 補正位置を生成


    // 補正位置を100回に一回デバックメッセージで送信
    if ((++counter % 100) == 0) {
        gcs().send_text(MAV_SEVERITY_INFO,
                         "OBS_pos=%.6f,%.6f,%.6f",
                         correction_position.x,
                         correction_position.y,
                         correction_position.z);
    }


    last_update_ms = AP_HAL::millis();
}


// 補正クオータニオンを計算
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



// 補正位置を計算
Vector3f AP_Observer::calculate_correction_position(const Vector3f& force) const {
    float gain = _correction_gain.get();
    float x = constrain_value(force.x * gain, -MAX_CORRECTION_POS, MAX_CORRECTION_POS);
    float y = constrain_value(force.y * gain, -MAX_CORRECTION_POS, MAX_CORRECTION_POS);
    
    // 機体座標系ベクトルを作成（前後・左右のみ、上下は0）
    Vector3f body_vec(x, y, 0.0f);
    
    // body_to_earth()を使用してNED座標系に変換
    return AP::ahrs().body_to_earth(body_vec);
}
