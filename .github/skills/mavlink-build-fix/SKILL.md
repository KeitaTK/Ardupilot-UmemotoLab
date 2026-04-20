# MAVLink Build Fix Skill

## Overview
This skill resolves MAVLink submodule registration issues that can cause Pixhawk6C (and other hardware) builds to fail with `git submodule status` errors.

## When to Use
- Pixhawk6C build fails with `WafError: Command... git submodule status... returned 1`
- `modules/mavlink` directory is missing but Git metadata exists
- MAVLink definition files (`message_definitions/v1.0/all.xml`) need to be restored

## Root Cause
This issue occurs when:
1. `modules/mavlink` Git submodule is not registered in `.gitmodules`
2. The working directory (`modules/mavlink/`) is missing
3. Git metadata (`.git/modules/modules/mavlink/`) still exists from previous state
4. The `waf` build script expects `git submodule status` to succeed

## Solution Components
The fix includes three parts:

### 1. Restore `modules/mavlink` Working Tree
If `.git/modules/modules/mavlink/` exists but `modules/mavlink/` is missing:
```bash
cd /home/memoto/Ardupilot-UmemotoLab
mkdir -p modules/mavlink
git --git-dir=.git/modules/modules/mavlink -c core.worktree=$(pwd)/modules/mavlink checkout -f
```

### 2. Code Changes to Handle Non-Submodule Layout
Three build files have been updated to tolerate in-tree `mavlink/` or unregistered `modules/mavlink/`:

**`wscript` (lines 650-656, 756-768)**
- Conditionally register mavlink submodule only if `modules/mavlink/` exists
- Add `_mavlink_xml_source_path()` function to find `all.xml` from either `modules/mavlink` or `mavlink`
- Use dynamic XML path instead of hardcoded `modules/mavlink/message_definitions/v1.0/all.xml`

**`Tools/ardupilotwaf/mavgen.py` (lines 98-104)**
- Search for `modules/mavlink` or `mavlink` directory
- Fall back to repo root if neither found
- Avoid fatal error when XML definitions unavailable

**`Tools/ardupilotwaf/git_submodule.py` (lines 81-86)**
- Catch `WafError` when `git submodule status` fails
- Check if target directory exists as plain directory (not registered submodule)
- Skip update and continue if directory exists
- Raise error only if directory is truly missing

## Verification Command
After restoring `modules/mavlink`, run:
```bash
cd /home/memoto/Ardupilot-UmemotoLab
source venv/bin/activate
./waf distclean
./waf configure --board Pixhawk6C
./waf copter
```

Expected output:
- `'distclean' finished successfully`
- `'configure' finished successfully`
- Build completes with firmware files:
  - `build/Pixhawk6C/bin/arducopter`
  - `build/Pixhawk6C/bin/arducopter.apj`
  - `build/Pixhawk6C/bin/arducopter.bin`

## Files Modified
- `wscript`
- `Tools/ardupilotwaf/mavgen.py`
- `Tools/ardupilotwaf/git_submodule.py`
- `.github/CHANGELOG_DEVELOPMENT.md` (documentation)

## Related Issues
- Pixhawk6C clean hardware build fails during MAVLink generation phase
- Repository state where `.gitmodules` is missing `mavlink` entry but Git metadata exists
- Vendor/fork scenarios where modules are tracked as regular directories, not submodules
