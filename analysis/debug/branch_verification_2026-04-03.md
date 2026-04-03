# Branch verification summary (2026-04-03)

## Environment
- Repository: KeitaTK/Ardupilot-UmemotoLab
- GH CLI: installed (`/usr/bin/gh`), but not authenticated (`gh auth status` fails)
- Python env used for tests: `venv`

## Candidate branches checked
- RLSobserver
- RLS_ZEROcross
- RLS-FFT
- RLS_only
- (Reference only) RLS_phase

## Results

### RLSobserver
- Autotest command:
  - `python Tools/autotest/autotest.py --no-clean --speedup=300 build.Copter test.Copter.TestRLSBasicEstimation`
- Result:
  - PASS (`build.Copter` passed, `test.Copter.TestRLSBasicEstimation` passed)
- Replay command:
  - `./waf --targets examples/RLS_CSV_Replay`
  - `./build/sitl/examples/RLS_CSV_Replay`
- Result:
  - PASS (build/run succeeded)
- Note:
  - `./waf examples` (build all examples) fails with linker errors (`undefined reference to copter`) in unrelated examples.

### RLS_ZEROcross
- Autotest command:
  - `python Tools/autotest/autotest.py --no-clean --speedup=300 build.Copter test.Copter.TestRLSBasicEstimation`
- Result:
  - PASS (`build.Copter` passed, `test.Copter.TestRLSBasicEstimation` passed)
- Replay command:
  - `./waf --targets examples/RLS_CSV_Replay`
  - `./build/sitl/examples/RLS_CSV_Replay`
- Result:
  - PASS (build/run succeeded)

### RLS-FFT
- Autotest command:
  - `python Tools/autotest/autotest.py --no-clean --speedup=300 build.Copter test.Copter.TestRLSBasicEstimation`
- Result:
  - TIMEOUT (exit 124); `build.Copter` was reached/passed but test did not complete within timeout
- Replay command:
  - `./waf --targets examples/RLS_CSV_Replay`
- Result:
  - FAIL
  - Compile error: `AP_Observer` has no member `set_params_for_replay`

### RLS_only
- Replay command:
  - `./waf --targets examples/RLS_CSV_Replay`
- Result:
  - FAIL (`Could not find a task generator for the name 'examples/RLS_CSV_Replay'`)
- Autotest command:
  - `python Tools/autotest/autotest.py --no-clean --speedup=300 build.Copter test.Copter.TestRLSBasicEstimation`
- Result:
  - FAIL (`Failed to find test TestRLSBasicEstimation on test.Copter`)

### RLS_phase (reference)
- `.github/AUTOTEST_SPECIFICATION.md` not found in this branch.
- Not selected as candidate for "real-data replay autotest" feature.

## Final judgement
- Most reliable branch for the requested feature set (RLS + real-data replay + runnable autotest): `RLS_ZEROcross`.
- Also runnable candidate: `RLSobserver`.
- Current checked-out branch at end of verification: `RLS_ZEROcross`.

## Note about temporary stash
- A temporary stash was created to avoid checkout conflicts caused by generated replay result files:
  - `stash@{0}: On RLS-FFT: temp: branch verification artifacts`
