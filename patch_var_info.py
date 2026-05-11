import re
with open("libraries/AP_Observer/AP_Observer.cpp", "r") as f:
    content = f.read()

# find AP_GROUPINFO for EKF_EN_GAT down to EKF_RB_NIS
pattern = r'(AP_GROUPINFO\("EKF_EN_GAT".*?EKF_RB_NIS.*?\)\,\n)'
replacement = """    AP_GROUPINFO("OUT_FADE_TH", 26, AP_Observer, _out_fade_th, 4.0f),
    // @Param: OUT_FADE_DLY
    // @DisplayName: Output fade out delay
    // @Description: Delay in seconds before output fade out starts
    // @Units: s
    // @User: Standard
    AP_GROUPINFO("OUT_FADE_DLY", 27, AP_Observer, _out_fade_dly, 2.0f),
    // @Param: OUT_FADE_IN_T
    // @DisplayName: Output fade in time constant
    // @Description: Time constant in seconds for fade in
    // @Units: s
    // @User: Standard
    AP_GROUPINFO("OUT_FADE_IN_T", 28, AP_Observer, _out_fade_in_t, 0.1f),
    // @Param: OUT_FADE_OUT_T
    // @DisplayName: Output fade out time constant
    // @Description: Time constant in seconds for fade out
    // @Units: s
    // @User: Standard
    AP_GROUPINFO("OUT_FADE_OUT_T", 29, AP_Observer, _out_fade_out_t, 1.0f),
"""

content = re.sub(pattern, replacement, content, flags=re.DOTALL)
with open("libraries/AP_Observer/AP_Observer.cpp", "w") as f:
    f.write(content)
