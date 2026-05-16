# Memory Bank Map

> **Purpose:** Index of all files in the memory bank. Read this first to find where specific information lives.

| File | Purpose | When to Read |
|------|---------|--------------|
| `memory-map.md` | This index — maps what lives where | Always first (with activeContext) |
| `activeContext.md` | Current focus, recent changes, next planned tasks | Always first (with memory-map) |
| `progress.md` | Task completion status, known issues, test results | When checking what's done / what's broken |
| `decisionLog.md` | Architecture decisions, design rationale, bug root causes | When asking "why is it this way?" |
| `systemStructure.md` | Directory layout, module dependencies, build targets | When adding modules or changing structure |
| `productContext.md` | Project goals, user-facing requirements, constraints | When unsure about core requirements |

## Quick Reference by Topic

- **Build / Compile:** `.clinerules` (build rules), `systemStructure.md` (targets)
- **Test workflow:** `.clinerules` (Lite→Medium→Pixhawk6C), `activeContext.md` (current test status)
- **Algorithm details:** `libraries/AP_Observer/README.md`, `decisionLog.md`
- **Code location:** `systemStructure.md`, `libraries/AP_Observer/AP_Observer.h`
- **Hardware targets:** Pixhawk6C (real), SITL (simulation)