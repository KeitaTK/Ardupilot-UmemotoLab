#pragma once

#include <AP_Common/AP_Common.h>
#include <AP_Param/AP_Param.h>
#include <AP_Math/AP_Math.h>
#include <AP_InertialSensor/AP_InertialSensor.h>
#include <AP_Motors/AP_Motors.h>
#include <GCS_MAVLink/GCS.h>
#include <Filter/LowPassFilter2p.h>

class AP_Observer {
public:
    void init();
    void update();

    // ゲッター関数
    Quaternion get_correction_quaternion() const { return current_correction_quat; }
    
    // RLS予測値を取得（現在時刻 + Δt先）
    Vector3f get_predicted_force() const { return rls_predicted_force; }
    
    // 現在時刻の推定値を取得
    Vector3f get_current_estimated_force() const { return rls_current_force; }
    
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

    // RLS状態取得
    bool is_rls_active() const { return rls_initialized; }

    // デバッグ出力間隔ゲッター
    uint32_t get_debug_output_interval() const { return _debug_output_interval.get(); }

    // パラメータ定義テーブル
    static const struct AP_Param::GroupInfo var_info[];

private:
    uint32_t    counter = 0;
    Vector3f    current_filtered_force = Vector3f();
    Quaternion  current_correction_quat = Quaternion(1,0,0,0);
    uint32_t    last_update_ms = 0;

    // 従来のローパスフィルタ（フォールバック用）
    LowPassFilter2pVector3f _payload_filter;
    Vector3f _payload_filtered = Vector3f();
    bool filter_initialized = false;

    // RLS関連のメンバ変数
    Matrix3f P_matrix;                      // 共分散行列 P[n]
    Vector3f theta_x, theta_y, theta_z;     // 各軸のパラメータベクトル [A, B, C]
    Vector3f rls_predicted_force;           // RLS予測外力（t + Δt時点）
    Vector3f rls_current_force;             // RLS推定外力（現在時刻）
    bool rls_initialized = false;           // RLS初期化完了フラグ
    uint32_t data_count = 0;                // 蓄積データ数
    uint32_t rls_start_time_ms = 0;         // RLS開始時刻
    
    // RLS用のヘルパー関数
    void init_rls();
    void update_rls(const Vector3f& measured_force);
    void handle_cold_start(const Vector3f& measured_force);
    Vector3f get_input_vector(float t) const;
    Vector3f get_prediction_vector(float t, float delta_t) const;  // 予測用入力ベクトル
    void update_rls_axis(Vector3f& theta, const Vector3f& x_vec, float y_measured);
    bool check_matrix_stability();
    void reset_rls_matrix();

    // 補正計算用
    Quaternion calculate_correction_from_force(const Vector3f& force) const;

    // パラメータ
    AP_Float    _correction_gain;
    AP_Float    _filter_cutoff_freq;
    AP_Float    _lambda_forget;             // 忘却係数
    AP_Float    _rls_frequency;             // 推定する周期性の周波数 [Hz]
    AP_Float    _prediction_time_ms;        // 予測時間 Δt [ms]
    AP_Float    _debug_output_interval;     // デバッグ出力間隔（外部設定可能、初期値10）

    // 定数
    static constexpr uint32_t TIMEOUT_MS               = 500;
    static constexpr uint32_t MIN_DATA_FOR_RLS         = 15;    // RLS開始に必要な最小データ数
    static constexpr float    FORCE_THRESHOLD          = 0.2f;
    static constexpr float    MAX_CORRECTION_ANGLE     = 0.5f;
    static constexpr float    g                        = 9.7985f;
    static constexpr float    THRUST_SCALE             = 6.3157f;
    static constexpr float    THRUST_OFFSET            = -0.9995f;
    static constexpr float    UAV_mass                 = 1.4f;
    static constexpr float    INITIAL_P_VALUE          = 1e4f;   // P行列の初期値
    static constexpr float    MIN_DENOMINATOR          = 1e-6f;  // 数値安定性のための最小値
    static constexpr float    MAX_CONDITION_NUMBER     = 1e8f;   // P行列の条件数上限
};
