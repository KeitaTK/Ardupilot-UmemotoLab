# Single-frequency EKF Replay Comparison

Compared original EKF vs fixed-frequency EKF (init=0.45Hz / 0.60Hz, q_w=1e-9)

```     log           method  mean_hz   std_hz   mae_hz  p95_step_hz  max_step_hz  hf_ratio
00000443     original_ekf 0.587159 0.037720 0.137305      0.00133       0.2029  0.040745
00000443 fixed_ekf_0.45Hz 0.471365 0.014686 0.021375      0.00000       0.2113  0.000173
00000443 fixed_ekf_0.60Hz 0.556749 0.023594 0.107728      0.00000       0.1936  0.000114
00000444     original_ekf 0.603731 0.018978 0.153731      0.00080       0.0805  0.198492
00000444 fixed_ekf_0.45Hz 0.449890 0.000043 0.000110      0.00000       0.0001  0.000086
00000444 fixed_ekf_0.60Hz 0.548413 0.000079 0.098413      0.00000       0.0003  0.000074```

## Per-log summary

### 00000443
```json
{
  "original": {
    "mean_hz": 0.587158648989899,
    "std_hz": 0.03772032172989905,
    "mae_hz": 0.1373049558080808,
    "p95_step_hz": 0.0013299999999999694,
    "max_step_hz": 0.20290000000000008,
    "hf_ratio": 0.04074529944507031
  },
  "fixed_ekf_0.45Hz": {
    "mean_hz": 0.47136519886363626,
    "std_hz": 0.014686325476084668,
    "mae_hz": 0.021375078914141424,
    "p95_step_hz": 0.0,
    "max_step_hz": 0.2113,
    "hf_ratio": 0.0001732344017424487
  },
  "fixed_ekf_0.60Hz": {
    "mean_hz": 0.5567491792929294,
    "std_hz": 0.02359428611081431,
    "mae_hz": 0.10772752525252521,
    "p95_step_hz": 0.0,
    "max_step_hz": 0.1936,
    "hf_ratio": 0.00011428823599781318
  }
}
```

### 00000444
```json
{
  "original": {
    "mean_hz": 0.6037311800330336,
    "std_hz": 0.018977965667087357,
    "mae_hz": 0.15373118003303357,
    "p95_step_hz": 0.0007999999999999841,
    "max_step_hz": 0.08050000000000002,
    "hf_ratio": 0.19849207563147198
  },
  "fixed_ekf_0.45Hz": {
    "mean_hz": 0.4498900899247569,
    "std_hz": 4.3190895639210825e-05,
    "mae_hz": 0.00010991007524315467,
    "p95_step_hz": 0.0,
    "max_step_hz": 0.0001000000000000445,
    "hf_ratio": 8.567689384985726e-05
  },
  "fixed_ekf_0.60Hz": {
    "mean_hz": 0.5484134703615343,
    "std_hz": 7.914397429010108e-05,
    "mae_hz": 0.09841347036153422,
    "p95_step_hz": 0.0,
    "max_step_hz": 0.000300000000000078,
    "hf_ratio": 7.422104511567384e-05
  }
}
```

---
## Initial-frequency check
- `init=0.60Hz` with `q_w=1e-9` did not reliably converge to the 0.45Hz target.
- 00000443 settled around 0.557Hz and 00000444 around 0.548Hz, so the initial bias remained visible.
- In other words, the filter is stable, but this q_w is too small if you want the estimate to forget a 0.60Hz starting point quickly.
Recommendation: If fixed EKF improves stability (lower p95_step_hz and mae), consider integrating fixed-frequency option into runtime EKF or using very low process noise for frequency during steady flight.
