import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys

def analyze_csv(filepath):
    try:
        df = pd.read_csv(filepath)
        print(f"Loaded {len(df)} rows.")
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return

    # Columns: TimeUS,PLX,PLY,PLZ,AX,AY,BX,BY,CX,CY,F,P,X,Y,SW
    # X is unwrapped phase.
    # TimeUS is micros.

    if 'X' not in df.columns or 'TimeUS' not in df.columns:
        print("Missing X or TimeUS columns.")
        return

    time_s = (df['TimeUS'] - df['TimeUS'].iloc[0]) * 1e-6
    phase = df['X']
    freq_est = df['F']
    switch = df['SW']

    # Calculate instantaneous slope of Phase
    # Phase = omega * t - P
    # But X in log is `ab_phase_unwrapped`.
    # Code: `phase_buffer[i] = ab_phase_unwrapped[0] - phase_correction`
    # The slope is calculated on `phase_buffer`.
    # Let's reconstruct `phase_buffer` equivalent.
    
    phase_correction = df['P']
    buffer_phase = phase - phase_correction
    
    # Calculate slope over 3s sliding window (approx 300 samples if 100Hz, but decimation used in code)
    # The log is 100Hz (roughly). Code decimates 1:5 -> 20Hz.
    # Buffer size 60 @ 20Hz = 3.0s.
    # We should take window of ~3 seconds.
    
    window_sec = 3.0
    slopes = []
    slope_times = []
    
    # Simple sliding window linear regression
    for i in range(0, len(df), 10): # Every 10 samples
        t_now = time_s.iloc[i]
        
        # Get samples in [t_now - window, t_now]
        mask = (time_s > t_now - window_sec) & (time_s <= t_now)
        subset = df[mask]
        
        if len(subset) < 20: # Need enough samples
            slopes.append(0)
            slope_times.append(t_now)
            continue
            
        # Linear fit of buffer_phase vs time
        sub_t = time_s[mask].values
        sub_p = buffer_phase[mask].values
        
        # Fit p = a*t + b -> a is slope [rad/s]
        # Use simple polyfit
        if len(sub_t) > 1:
            try:
                fit = np.polyfit(sub_t, sub_p, 1)
                slope_rad_s = fit[0]
                slopes.append(slope_rad_s)
            except:
                slopes.append(0)
        else:
            slopes.append(0)
        
        slope_times.append(t_now)

    slopes = np.array(slopes)
    delta_freq = slopes / (2 * np.pi)
    
    # Plot
    fig, ax = plt.subplots(4, 1, figsize=(10, 12), sharex=True)
    
    ax[0].plot(time_s, freq_est, label='F (Est Freq)')
    ax[0].set_ylabel('Freq [Hz]')
    ax[0].grid(True)
    ax[0].legend()
    
    ax[1].plot(time_s, phase, label='X (Obs Phase)')
    ax[1].plot(time_s, buffer_phase, label='Buffered (X-P)', linestyle='--')
    ax[1].set_ylabel('Phase [rad]')
    ax[1].grid(True)
    ax[1].legend()

    ax[2].plot(slope_times, delta_freq, label='Calc Delta Freq (Hz)', color='r')
    ax[2].set_ylabel('Delta Freq [Hz]')
    ax[2].grid(True)
    ax[2].legend()

    ax[3].plot(time_s, switch, label='Switch')
    ax[3].set_ylabel('SW')
    ax[3].set_xlabel('Time [s]')
    ax[3].grid(True)
    ax[3].legend()
    
    output_path = 'analysis/results/log_analysis.png'
    plt.savefig(output_path)
    print(f"Analysis plot saved to {output_path}")
    
    # Print some stats
    print(f"Mean Delta Freq: {np.mean(delta_freq):.4f} Hz")
    print(f"Max Delta Freq: {np.max(np.abs(delta_freq)):.4f} Hz")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_log.py <csv_file>")
    else:
        analyze_csv(sys.argv[1])
