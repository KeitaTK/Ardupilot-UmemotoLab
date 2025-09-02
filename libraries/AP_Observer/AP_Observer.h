#pragma once

#include <AP_Common/AP_Common.h>
#include <AP_Param/AP_Param.h>
#include <AP_Math/AP_Math.h>
#include <AP_InertialSensor/AP_InertialSensor.h>
#include <AP_Motors/AP_Motors.h>
#include <GCS_MAVLink/GCS.h>

class AP_Observer {
public:
    void init() const;
    void update();

    // ゲッター関数
    Quaternion get_correction_quaternion() const { return current_correction_quat; }

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

    // パラメータ定義テーブル
    static const struct AP_Param::GroupInfo var_info[];

private:
    uint32_t    counter;
    Vector3f    current_filtered_force;
    Quaternion  current_correction_quat;
    uint32_t    last_update_ms = 0;   // 最終補正計算時刻

    // 補正計算用
    Quaternion calculate_correction_from_force(const Vector3f& force) const;

    // パラメータ
    AP_Float    _correction_gain;

    // 定数
    static constexpr uint32_t TIMEOUT_MS            = 500;    // タイムアウト値を500msに設定
    static constexpr float    FORCE_THRESHOLD      = 0.2f;
    static constexpr float    MAX_CORRECTION_ANGLE = 0.5f;
    static constexpr float    g                    = 9.7985f;
    static constexpr float    THRUST_SCALE         = 6.3157f;
    static constexpr float    THRUST_OFFSET        = -0.9995f;
    static constexpr float    UAV_mass             = 1.4f;
};
