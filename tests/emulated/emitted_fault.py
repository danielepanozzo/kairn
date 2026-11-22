#!/usr/bin/env python3
"""A fault planted in the C++ printed for the emulated type, of the kind the emulated tier is for,
and the tier's verdict on it (docs/developer/testing.md, "The emulated formats").

    python3 tests/emulated/emitted_fault.py write DIR
    python3 tests/emulated/emitted_fault.py check --runner EXE [--claims FILE]

write: DIR/gen/kernels.hpp, a copy of tests/emulated/gen/kernels.hpp with the arms of one select of
mul_ext_2_2 swapped (the select of the inlined directed step wu of its leading limb), and beside it
copies of runner.cpp, number.hpp and prelude.hpp, from which CMake builds the runner of the fault
(kairn-emulated-runner-fault). The line must occur exactly once, or nothing is written.

check: the runner of the fault through tests/crosscheck.py (1) as a compiled runner, on the quick
tier's binary64 cases of mul_ext_2_2 (seed 0, 2 000 cases): the oracle passes it, since the claim is
an outward bound with room, and that cross-check, which compares nothing, passes; (2) as an emulated
runner beside the interpreter in fp:8:-14:1, on the same number of cases: the oracle passes it there
too, and the test fails on the first line where its bytes are not the interpreter's. This exits 0
when both happen as described, 1 otherwise.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
REPO = os.path.dirname(TESTS)

OLD = "    const kairn::emulated::Number c0_wu = c0_wu_n ? c0_wu_q : c0_wu_s;\n"
NEW = "    const kairn::emulated::Number c0_wu = c0_wu_n ? c0_wu_s : c0_wu_q;\n"


def write(d):
    with open(os.path.join(HERE, "gen", "kernels.hpp"), encoding="utf-8") as f:
        text = f.read()
    if text.count(OLD) != 1:
        sys.exit("emitted_fault.py: the line of the fault occurs %d times in gen/kernels.hpp, not once:\n%s"
                 % (text.count(OLD), OLD))
    os.makedirs(os.path.join(d, "gen"), exist_ok=True)
    for name in ("runner.cpp", "number.hpp", "prelude.hpp"):
        shutil.copyfile(os.path.join(HERE, name), os.path.join(d, name))
    with open(os.path.join(d, "gen", "kernels.hpp"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text.replace(OLD, NEW))
    return 0


def drive(args, d):
    p = subprocess.run([sys.executable, os.path.join(TESTS, "crosscheck.py"), "compiled", "--kernel", "mul_ext_2_2",
                        "--seed", "0", "--count", "2000", "--fail-on-suspicious"] + args
                       + ["--summary", os.path.join(d, "s.json")], capture_output=True, text=True, cwd=REPO)
    return p.returncode, p.stdout + p.stderr


def check(exe, claims):
    extra = ["--claims", claims] if claims else []
    failed = []
    with tempfile.TemporaryDirectory() as d:
        status, out = drive(["--format", "binary64", "--runner", "planted", exe] + extra, d)
        if status != 0:
            failed.append("the binary64 cross-check of the planted runner failed (%d), where it was to pass:\n%s"
                          % (status, out[-3000:]))
        else:
            print("binary64, the quick tier's cases, the planted runner as a compiled one: passed (the oracle "
                  "does not see the fault)")
        status, out = drive(["--format", "fp:8:-14:1", "--interp", "--emulated", "planted", exe] + extra, d)
        report = out.split("with planted: the oracle's report", 1)[-1]
        if status != 1 or "planted: other lines than interp's" not in out:
            failed.append("the emulated cross-check of the planted runner did not fail on its lines (%d):\n%s"
                          % (status, out[-3000:]))
        elif "kairn-oracle check: PASS" not in report.split("cross-check of", 1)[0]:
            failed.append("the oracle failed the planted runner's output in fp:8:-14:1: the test is to show the "
                          "comparison catching what the oracle passes\n%s" % out[-3000:])
        else:
            line = next(x for x in out.split("\n") if "other lines than interp's" in x)
            print("fp:8:-14:1, the planted runner beside the interpreter: the oracle passed it, and the "
                  "comparison failed it: " + line.strip()[3:])
    for f in failed:
        print("emitted_fault.py: " + f)
    print("emitted_fault.py: %s" % ("FAILED" if failed else "passed"))
    return 1 if failed else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("dir")
    c = sub.add_parser("check")
    c.add_argument("--runner", required=True)
    c.add_argument("--claims")
    a = ap.parse_args(argv)
    return write(a.dir) if a.cmd == "write" else check(a.runner, a.claims)


if __name__ == "__main__":
    sys.exit(main())
