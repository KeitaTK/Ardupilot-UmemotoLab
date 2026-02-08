#!/usr/bin/env python3
"""
Test for AP_Observer parameter changes (OBS_MAX_CORR_ANG, OBS_FREQ_WIN)
Insert this test into arducopter.py
"""

def TestRLSParameterChange(self):
    '''Test OBS_MAX_CORR_ANG and OBS_FREQ_WIN parameter changes'''
    self.context_push()
    
    test_freq = 0.6
    test_amplitude = 10.0
    self.progress("Testing AP_Observer parameter changes: OBS_MAX_CORR_ANG and OBS_FREQ_WIN")
    
    # デフォルト値を確認
    default_max_corr = self.get_parameter('OBS_MAX_CORR_ANG')
    default_freq_win = self.get_parameter('OBS_FREQ_WIN')
    self.progress(f"Default OBS_MAX_CORR_ANG: {default_max_corr}")
    self.progress(f"Default OBS_FREQ_WIN: {default_freq_win}")
    
    # 期待されるデフォルト値
    if abs(default_max_corr - 0.5) > 0.001:
        raise NotAchievedException(f"OBS_MAX_CORR_ANG default should be 0.5, got {default_max_corr}")
    if abs(default_freq_win - 10.0) > 0.01:
        raise NotAchievedException(f"OBS_FREQ_WIN default should be 10.0, got {default_freq_win}")
    
    self.progress("✅ Default values correct")
    
    # Test 1: OBS_MAX_CORR_ANGを変更
    new_max_corr = 0.3
    self.progress(f"Test 1: Setting OBS_MAX_CORR_ANG to {new_max_corr}")
    self.set_parameter('OBS_MAX_CORR_ANG', new_max_corr)
    self.delay_sim_time(1)
    
    actual_max_corr = self.get_parameter('OBS_MAX_CORR_ANG')
    self.progress(f"OBS_MAX_CORR_ANG after change: {actual_max_corr}")
    if abs(actual_max_corr - new_max_corr) > 0.001:
        raise NotAchievedException(
            f"OBS_MAX_CORR_ANG not set correctly: expected {new_max_corr}, got {actual_max_corr}"
        )
    self.progress("✅ OBS_MAX_CORR_ANG change successful")

    # Test 2: OBS_FREQ_WINを変更
    new_freq_win = 12.5
    self.progress(f"Test 2: Setting OBS_FREQ_WIN to {new_freq_win}")
    self.set_parameter('OBS_FREQ_WIN', new_freq_win)
    self.delay_sim_time(1)

    actual_freq_win = self.get_parameter('OBS_FREQ_WIN')
    self.progress(f"OBS_FREQ_WIN after change: {actual_freq_win}")
    if abs(actual_freq_win - new_freq_win) > 0.01:
        raise NotAchievedException(
            f"OBS_FREQ_WIN not set correctly: expected {new_freq_win}, got {actual_freq_win}"
        )
    self.progress("✅ OBS_FREQ_WIN change successful")
    
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
    self.set_parameter('OBS_MAX_CORR_ANG', 0.5)
    self.set_parameter('OBS_FREQ_WIN', 10.0)
    
    self.progress("✅ ALL PARAMETER CHANGE TESTS PASSED")
    
    self.do_RTL()
    self.context_pop()
