#!/usr/bin/env python3
"""
Test for AP_Observer parameter changes (OBS_FREQ_ALPHA, OBS_MAX_CORR_ANG)
Insert this test into arducopter.py
"""

def TestRLSParameterChange(self):
    '''Test OBS_FREQ_ALPHA and OBS_MAX_CORR_ANG parameter changes'''
    self.context_push()
    
    test_freq = 0.6
    test_amplitude = 10.0
    self.progress("Testing AP_Observer parameter changes: OBS_FREQ_ALPHA and OBS_MAX_CORR_ANG")
    
    # デフォルト値を確認
    default_freq_alpha = self.get_parameter('OBS_FREQ_ALPHA')
    default_max_corr = self.get_parameter('OBS_MAX_CORR_ANG')
    self.progress(f"Default OBS_FREQ_ALPHA: {default_freq_alpha}")
    self.progress(f"Default OBS_MAX_CORR_ANG: {default_max_corr}")
    
    # 期待されるデフォルト値
    if abs(default_freq_alpha - 0.15) > 0.001:
        raise NotAchievedException(f"OBS_FREQ_ALPHA default should be 0.15, got {default_freq_alpha}")
    if abs(default_max_corr - 0.5) > 0.001:
        raise NotAchievedException(f"OBS_MAX_CORR_ANG default should be 0.5, got {default_max_corr}")
    
    self.progress("✅ Default values correct")
    
    # Test 1: OBS_FREQ_ALPHAを変更
    new_freq_alpha = 0.1
    self.progress(f"Test 1: Setting OBS_FREQ_ALPHA to {new_freq_alpha}")
    self.set_parameter('OBS_FREQ_ALPHA', new_freq_alpha)
    self.delay_sim_time(1)
    
    actual_freq_alpha = self.get_parameter('OBS_FREQ_ALPHA')
    self.progress(f"OBS_FREQ_ALPHA after change: {actual_freq_alpha}")
    if abs(actual_freq_alpha - new_freq_alpha) > 0.001:
        raise NotAchievedException(
            f"OBS_FREQ_ALPHA not set correctly: expected {new_freq_alpha}, got {actual_freq_alpha}"
        )
    self.progress("✅ OBS_FREQ_ALPHA change successful")
    
    # Test 2: OBS_MAX_CORR_ANGを変更
    new_max_corr = 0.3
    self.progress(f"Test 2: Setting OBS_MAX_CORR_ANG to {new_max_corr}")
    self.set_parameter('OBS_MAX_CORR_ANG', new_max_corr)
    self.delay_sim_time(1)
    
    actual_max_corr = self.get_parameter('OBS_MAX_CORR_ANG')
    self.progress(f"OBS_MAX_CORR_ANG after change: {actual_max_corr}")
    if abs(actual_max_corr - new_max_corr) > 0.001:
        raise NotAchievedException(
            f"OBS_MAX_CORR_ANG not set correctly: expected {new_max_corr}, got {actual_max_corr}"
        )
    self.progress("✅ OBS_MAX_CORR_ANG change successful")
    
    # Test 3: 実際にRLSを動かして動作確認
    self.progress("Test 3: Running RLS with modified parameters")
    self.set_parameters({
        'OBS_DIST_FREQ': test_freq,
        'OBS_PHASE_CORR': 1,
        'OBS_TEST_INJECT': 1,
        'OBS_TEST_FREQ': test_freq,
        'OBS_TEST_AMP': test_amplitude,
        'LOG_DISARMED': 0,
    })
    
    self.reboot_sitl()
    
    # 再起動後もパラメータが保持されているか確認
    self.delay_sim_time(2)
    after_reboot_freq_alpha = self.get_parameter('OBS_FREQ_ALPHA')
    after_reboot_max_corr = self.get_parameter('OBS_MAX_CORR_ANG')
    
    self.progress(f"After reboot - OBS_FREQ_ALPHA: {after_reboot_freq_alpha}")
    self.progress(f"After reboot - OBS_MAX_CORR_ANG: {after_reboot_max_corr}")
    
    if abs(after_reboot_freq_alpha - new_freq_alpha) > 0.001:
        raise NotAchievedException(
            f"OBS_FREQ_ALPHA not preserved after reboot: expected {new_freq_alpha}, got {after_reboot_freq_alpha}"
        )
    if abs(after_reboot_max_corr - new_max_corr) > 0.001:
        raise NotAchievedException(
            f"OBS_MAX_CORR_ANG not preserved after reboot: expected {new_max_corr}, got {after_reboot_max_corr}"
        )
    
    self.progress("✅ Parameters preserved after reboot")
    
    # 離陸してRLSが正常に動作するか確認
    self.progress("Taking off to verify RLS operation with new parameters")
    self.takeoff(10, mode='ALT_HOLD')
    self.delay_sim_time(20)
    
    # ログからRLS係数を確認
    tstart = self.get_sim_time() - 10
    tend = self.get_sim_time()
    
    import numpy
    mlog = self.dfreader_for_current_onboard_log()
    rls_amplitudes = []
    
    while True:
        m = mlog.recv_match(
            type='OBSV',
            blocking=False,
            condition="OBSV.TimeUS>%u and OBSV.TimeUS<%u" % (tstart * 1.0e6, tend * 1.0e6))
        if m is None:
            break
        if hasattr(m, 'AX') and hasattr(m, 'BX'):
            amp = (m.AX**2 + m.BX**2)**0.5
            rls_amplitudes.append(amp)
    
    if len(rls_amplitudes) > 0:
        median_amp = numpy.median(numpy.asarray(rls_amplitudes))
        self.progress(f"RLS amplitude with new parameters: {median_amp:.3f}N")
        
        if median_amp < test_amplitude * 0.5:
            raise NotAchievedException(
                f"RLS amplitude too low with new parameters: got {median_amp:.3f}N, expected ~{test_amplitude}N"
            )
        self.progress("✅ RLS operating correctly with new parameters")
    else:
        raise NotAchievedException("No RLS data found in log")
    
    # デフォルト値に戻す
    self.progress("Restoring default parameter values")
    self.set_parameter('OBS_FREQ_ALPHA', 0.15)
    self.set_parameter('OBS_MAX_CORR_ANG', 0.5)
    
    self.progress("✅ ALL PARAMETER CHANGE TESTS PASSED")
    
    self.do_RTL()
    self.context_pop()
