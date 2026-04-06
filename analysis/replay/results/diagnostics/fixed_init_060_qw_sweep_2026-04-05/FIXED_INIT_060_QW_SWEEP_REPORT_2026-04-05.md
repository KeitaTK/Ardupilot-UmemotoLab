# 0.60 Hz Initial Convergence Sweep

- initial frequency: 0.60 Hz
- target frequency: 0.45 Hz
- settle band: ±0.01 Hz for 5.0 s

## Ranked Results
     log          q_w  settle_time_s   mae_hz   std_hz  final_err_hz  p95_step_hz  max_step_hz
00000444 1.000000e-02            NaN 0.057017 0.012051        0.0563          0.0       0.1164
00000444 1.000000e-03            NaN 0.061597 0.011741        0.0611          0.0       0.1158
00000444 1.000000e-04            NaN 0.062071 0.011720        0.0616          0.0       0.1159
00000444 1.000000e-09            NaN 0.062071 0.011719        0.0616          0.0       0.1158
00000444 1.000000e-08            NaN 0.062071 0.011719        0.0616          0.0       0.1158
00000444 1.000000e-07            NaN 0.062071 0.011719        0.0616          0.0       0.1158
00000444 1.000000e-06            NaN 0.062071 0.011719        0.0616          0.0       0.1158
00000444 1.000000e-05            NaN 0.062169 0.011708        0.0617          0.0       0.1158
00000443 1.000000e-04            NaN 0.088963 0.023624        0.0257          0.0       0.2139
00000443 1.000000e-05            NaN 0.089237 0.024953        0.0342          0.0       0.2126
00000443 1.000000e-06            NaN 0.089263 0.025064        0.0349          0.0       0.2124
00000443 1.000000e-09            NaN 0.089263 0.025064        0.0349          0.0       0.2124
00000443 1.000000e-08            NaN 0.089263 0.025064        0.0349          0.0       0.2124
00000443 1.000000e-07            NaN 0.089263 0.025064        0.0349          0.0       0.2124
00000443 1.000000e-03            NaN 0.089771 0.013104        0.0517          0.0       0.2165
00000443 1.000000e-02            NaN 0.093996 0.017575        0.1714          0.0       0.1997

## Per-log Best
{
  "00000443": {
    "best_q_w": 0.0001,
    "best_settle_time_s": NaN,
    "best_mae_hz": 0.08896302083333335,
    "best_final_err_hz": 0.0257
  },
  "00000444": {
    "best_q_w": 0.01,
    "best_settle_time_s": NaN,
    "best_mae_hz": 0.05701659020003667,
    "best_final_err_hz": 0.05629999999999996
  }
}

## Interpretation
- Larger q_w values reduce the memory of the 0.60 Hz starting point.
- The best setting is the one that both enters the 0.45 Hz band quickly and keeps the final error small.
- If the best q_w still leaves a noticeable final bias, the filter is stable but not fast enough to forget its initial value.