# Single-frequency EKF Replay Comparison

Compared original EKF vs fixed-frequency EKF (init=0.45Hz, q_w=1e-9)

```     log           method  mean_hz   std_hz   mae_hz  p95_step_hz  max_step_hz  hf_ratio
00000443     original_ekf 0.587159 0.037720 0.137305      0.00133       0.2029  0.040745
00000443 fixed_ekf_0.45Hz 0.477713 0.013547 0.027723      0.00000       0.2113  0.033400
00000444     original_ekf 0.603731 0.018978 0.153731      0.00080       0.0805  0.198492
00000444 fixed_ekf_0.45Hz 0.479857 0.005049 0.029871      0.00000       0.0309  4.505152```

---
Recommendation: If fixed EKF improves stability (lower p95_step_hz and mae), consider integrating fixed-frequency option into runtime EKF or using very low process noise for frequency during steady flight.
