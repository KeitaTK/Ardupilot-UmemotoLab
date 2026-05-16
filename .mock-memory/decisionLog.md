# Decision Log

> **Purpose:** Record architecture decisions, design rationale, and bug root causes.
> **Format:** Date, Decision, Rationale, Alternatives Considered.

---

## 2026-05-16 — Memory Bank Initialized

**Decision:** Create `.mock-memory/` memory bank following the Memory Bank Protocol.

**Rationale:** Enable consistent long-term development context across sessions. The protocol enforces lazy-loading on startup (`memory-map.md` + `activeContext.md` only) to avoid token waste, with on-demand loading of other files.

**Alternatives considered:**
- No memory bank → context lost between sessions.
- All files loaded on every startup → excessive token consumption.

---

## Existing Architecture Decisions (from `.clinerules` / README)

### State Vector Design
- 4-state EKF per axis: [d (position), d_dot (velocity), c (bias), ω (angular frequency)]
- Z-axis EKF update skipped (hard to separate from thrust variation)
- X/Y axes estimate frequency independently (no cross-axis frequency fusion)

### Robustness Gate (3-stage)
1. **Energy confidence gate** — long-term signal power evaluation, prevents zero-cross chattering
2. **Amplitude-based gate** — instantaneous physical quantity absolute value check, detects low/high amplitude anomalies
3. **NIS check** — statistical prediction divergence evaluation, adaptive R control

### Build Rules
- SITL: incremental build OK (`waf configure --board sitl && waf build --target bin/arducopter`)
- Pixhawk6C: always clean build (`waf distclean && waf configure --board Pixhawk6C && waf copter`)

### Test Pipeline
- Lite → Medium → Pixhawk6C (must pass in order)
- Full test (test.CopterTests2b) only for major changes (~15 min)