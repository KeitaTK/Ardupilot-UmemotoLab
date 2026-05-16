# Product Context

> **Purpose:** Project goals, user-facing requirements, and constraints.

## Project Goal

Develop an **EKF-based Harmonic Disturbance Observer (AP_Observer)** for ArduPilot to estimate and compensate for external oscillatory forces (e.g., payload vibration) acting on the UAV.

## Why This Exists

- Payload oscillations (e.g., suspended loads, liquid sloshing) introduce unknown external forces
- Standard ArduPilot EKF (NavEKF2/3) treats these as process noise, degrading state estimation
- Harmonic Disturbance Observer explicitly models periodic disturbances as sinusoids with unknown frequency, amplitude, and phase
- Estimating disturbance forces enables feedforward compensation → improved position hold accuracy

## Target Users

- UAV operators carrying oscillatory payloads (spraying systems, crane drones, delivery drones with swinging loads)
- Researchers studying disturbance rejection in multirotor control

## Key Requirements

- Must run in real-time on Pixhawk6C (STM32H753, 480MHz Cortex-M7)
- Must coexist with standard ArduPilot EKF (NavEKF2/3)
- Must log disturbance estimates via existing OBSV logging infrastructure
- X/Y axes estimated independently; Z-axis deferred (thrust coupling)
- Robustness against sensor noise and non-harmonic transients via 3-stage gate

## Constraints

- C++11/14 (ArduPilot firmware standard)
- Real-time safe (no dynamic memory allocation in control loop)
- Parameter-driven configuration (`EKF_*` prefix)
- Follows ArduPilot flash-size constraints for Pixhawk6C