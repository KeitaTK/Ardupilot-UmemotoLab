#!/usr/bin/env python

'''
Run autotest repeatedly at different speedups to help find best default speedup

AP_FLAKE8_CLEAN
'''

import optparse
import os
import re
import subprocess
import time


class CheckAutoTestSpeedup(object):
    def __init__(
            self,
            build_target="build.Plane",
            test_target="test.QuadPlane",
            min_speedup=1,
            max_speedup=50,
            gdb=False,
            debug=False
    ):
        self.build_target = build_target
        self.test_target = test_target
        self.min_speedup = min_speedup
        self.max_speedup = max_speedup
        self.gdb = gdb
        self.debug = debug

    def progress(self, message):
        print("PROGRESS: %s" % (message,))

    def run_program(self, prefix, cmd_list):
        '''copied in from build_binaries.py'''
        '''run cmd_list, spewing and setting output in self'''
        self.progress("Running (%s)" % " ".join(cmd_list))
        p = subprocess.Popen(cmd_list,
                             stdin=None,
                             close_fds=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        self.program_output = ""
        while True:
            x = p.stdout.readline()
            if len(x) == 0:
                returncode = os.waitpid(p.pid, 0)
                if returncode:
                    break
                    # select not available on Windows... probably...
                time.sleep(0.1)
                continue
            if isinstance(x, bytes):
                x = x.decode('utf-8')
            self.program_output += x
            x = x.rstrip()
            print("%s: %s" % (prefix, x))
        if isinstance(returncode, tuple):
            (_, status) = returncode
        else:
            status = returncode
        if status != 0:
            self.progress("Process failed (%s)" % str(status))
            raise subprocess.CalledProcessError(
                status, cmd_list)

    def run(self):
        build_args = [
            "./Tools/autotest/autotest.py",
            "--no-clean",
            self.build_target
        ]
        if opts.debug:
            build_args.append("--debug")
        self.run_program("BUILD", build_args)
        f = open(os.path.join("/tmp/speedup.txt"), "w")

        # まず最大speedupで一回だけテスト
        results = {}
        max_speedup_passed = False
        self.progress(f"=== フェーズ1: 最大speedup={self.max_speedup}をテスト ===")
        try:
            self.progress(f"Checking speedup {self.max_speedup}")
            run_args = [
                "./Tools/autotest/autotest.py",
                "--no-clean",
                "--speedup", str(self.max_speedup),
                "--show-test-timings",
                self.test_target,
            ]
            if opts.gdb:
                run_args.append("--gdb")
            self.run_program(f"SPEEDUP-{self.max_speedup:03d}", run_args)
            for line in self.program_output.split("\n"):
                match = re.match(".*tests_total_time.*?([0-9.]+)s.*", line)
                if match is not None:
                    break
            results[self.max_speedup] = float(match.group(1)) if match else None
            prog = f"{self.max_speedup} {results[self.max_speedup]}"
            self.progress(prog)
            print(prog, file=f)
            f.flush()
            self.progress(f"=== 最大speedup {self.max_speedup} → PASS ===")
            self.progress(f"最大PASS speedup: {self.max_speedup}")
            print(f"最大PASS speedup: {self.max_speedup}")
            for (speedup, t) in sorted(results.items()):
                print(f"{speedup} {t}")
            max_speedup_passed = True
        except Exception as e:
            self.progress(f"=== 最大speedup {self.max_speedup} → FAIL ===")
            self.progress(f"speedup {self.max_speedup} FAILED")

        # 最大speedupがFAILなら二分探索で境界を探す
        if not max_speedup_passed:
            self.progress(f"=== フェーズ2: 最小speedup={self.min_speedup}をテスト ===")
            # まずmin_speedupでテストして、基準点が動作するか確認
            self.progress(f"Checking min speedup {self.min_speedup}")
            run_args = [
                "./Tools/autotest/autotest.py",
                "--no-clean",
                "--speedup", str(self.min_speedup),
                "--show-test-timings",
                self.test_target,
            ]
            if opts.gdb:
                run_args.append("--gdb")
            try:
                self.run_program(f"SPEEDUP-{self.min_speedup:03d}", run_args)
                for line in self.program_output.split("\n"):
                    match = re.match(".*tests_total_time.*?([0-9.]+)s.*", line)
                    if match is not None:
                        break
                results[self.min_speedup] = float(match.group(1)) if match else None
                prog = f"{self.min_speedup} PASS {results[self.min_speedup]}"
                self.progress(prog)
                self.progress(f"=== 最小speedup {self.min_speedup} → PASS ===")
                print(prog, file=f)
                f.flush()
            except Exception as e_min:
                # min_speedupでもFAILする場合はエラー
                self.progress(f"=== 最小speedup {self.min_speedup} → FAIL ===")
                self.progress(f"ERROR: speedup {self.min_speedup} FAILED")
                print(f"ERROR: Even minimum speedup {self.min_speedup} failed!", file=f)
                f.close()
                return
            
            self.progress(f"=== フェーズ3: 二分探索で境界を探す ===")
            # min_speedup=PASS、max_speedup=FAILなので、二分探索で境界を見つける
            max_pass = self.min_speedup  # min_speedupでPASSしたのは確認済み
            min_fail = self.max_speedup  # max_speedupでFAILしたのは確認済み
            self.progress(f"探索範囲: PASS={max_pass}, FAIL={min_fail}")
            
            # max_pass < min_fail の間を二分探索（PASSとFAILの境界を見つける）
            while max_pass + 1 < min_fail:
                mid = (max_pass + min_fail) // 2
                self.progress(f"Checking speedup {mid} (between {max_pass}=PASS and {min_fail}=FAIL)")
                run_args = [
                    "./Tools/autotest/autotest.py",
                    "--no-clean",
                    "--speedup", str(mid),
                    "--show-test-timings",
                    self.test_target,
                ]
                if opts.gdb:
                    run_args.append("--gdb")
                try:
                    self.run_program(f"SPEEDUP-{mid:03d}", run_args)
                    for line in self.program_output.split("\n"):
                        match = re.match(".*tests_total_time.*?([0-9.]+)s.*", line)
                        if match is not None:
                            break
                    results[mid] = float(match.group(1)) if match else None
                    prog = f"{mid} PASS {results[mid]}"
                    self.progress(prog)
                    self.progress(f"=== speedup {mid} → PASS ===")
                    print(prog, file=f)
                    f.flush()
                    max_pass = mid  # PASSしたので、max_passを更新
                    self.progress(f"更新: max_pass={max_pass}, min_fail={min_fail}")
                except Exception as e2:
                    self.progress(f"=== speedup {mid} → FAIL ===")
                    self.progress(f"speedup {mid} FAILED")
                    min_fail = mid  # FAILしたので、min_failを更新
                    self.progress(f"更新: max_pass={max_pass}, min_fail={min_fail}")
            
            # 探索完了
            self.progress(f"=== 探索完了 ===")
            self.progress(f"最大PASS speedup: {max_pass}")
            self.progress(f"最小FAIL speedup: {min_fail}")
            print(f"\n最大PASS speedup: {max_pass}")
            print(f"最小FAIL speedup: {min_fail}")
            print(f"結果詳細:")
            for (speedup, t) in sorted(results.items()):
                print(f"  speedup {speedup}: {t}s")


if __name__ == '__main__':
    parser = optparse.OptionParser(
        "check_autotest_speedup.py",
        epilog=""
        "e.g. ./Tools/autotest/check_autotest_speedup.py --max-speedup=40 --build-target=build.Sub --test-target=test.Sub"
    )
    parser.add_option("--debug",
                      default=False,
                      help='compile with debugging')
    parser.add_option("--gdb",
                      default=False,
                      help='run under gdb')
    parser.add_option("--max-speedup",
                      type=int,
                      default=50,
                      help='max speedup to test')
    parser.add_option("--min-speedup",
                      type=int,
                      default=1,
                      help='min speedup to test')
    parser.add_option("--build-target",
                      type='string',
                      default='build.Plane',
                      help='build target (e.g. build.Plane)')
    parser.add_option("--test-target",
                      type='string',
                      default='test.QuadPlane',
                      help='test target (e.g. test.QuadPlane)')

    opts, args = parser.parse_args()

    checker = CheckAutoTestSpeedup(
        gdb=opts.gdb,
        debug=opts.debug,
        max_speedup=opts.max_speedup,
        min_speedup=opts.min_speedup,
        build_target=opts.build_target,
        test_target=opts.test_target
    )

    checker.run()
