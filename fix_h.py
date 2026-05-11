import re

with open("libraries/AP_Observer/AP_Observer.h", "r") as f:
    text = f.read()

# Delete lines containing any AP_Float definition
vars_to_delete = [
    "_correction_gain", "_filter_cutoff_freq", "_max_correction_angle",
    "_ekf_q_d", "_ekf_q_d_dot", "_ekf_q_c", "_ekf_q_omega",
    "_ekf_r_meas", "_ekf_omega_init", "_ekf_omega_min", "_ekf_omega_max",
    "_ekf_innov_max", "_ekf_nis_max", "_out_fade_th", "_out_fade_dly",
    "_out_fade_in_t", "_out_fade_out_t", "_prediction_time"
]

lines = text.split("\n")
cleaned_lines = []
for line in lines:
    if "AP_Float" in line and any(v in line for v in vars_to_delete):
        continue
    cleaned_lines.append(line)

new_code = """
    // --- AP_Param variables (must match var_info order exactly) ---
    AP_Float _correction_gain;
    AP_Float _filter_cutoff_freq;
    AP_Float _ekf_q_d;
    AP_Float _ekf_q_d_dot;
    AP_Float _ekf_q_c;
    AP_Float _ekf_q_omega;
    AP_Float _ekf_r_meas;
    AP_Float _ekf_omega_init;
    AP_Float _ekf_omega_min;
    AP_Float _ekf_omega_max;
    AP_Float _prediction_time;
    AP_Float _max_correction_angle;
    AP_Float _ekf_innov_max;
    AP_Float _ekf_nis_max;
    AP_Float _out_fade_th;
    AP_Float _out_fade_dly;
    AP_Float _out_fade_in_t;
    AP_Float _out_fade_out_t;
    // -------------------------------------------------------------
"""

# insert after private:
for i, line in enumerate(cleaned_lines):
    if "private:" in line and "public:" not in line:
        cleaned_lines.insert(i+1, new_code)
        break

with open("libraries/AP_Observer/AP_Observer.h", "w") as f:
    f.write("\n".join(cleaned_lines))

