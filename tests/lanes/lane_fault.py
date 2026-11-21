"""The planted fault of the packed lanes: a test that the cross-checks see a fault that only a
register whose lanes hold different kinds of values can show (docs/developer/testing.md, "Packed
kernels").

    python3 tests/lanes/lane_fault.py --runner EXECUTABLE --format F --summary-dir DIR
                                      [--seed S] [--count N] [--claims FILE]

EXECUTABLE is gen/tests/packed_runner.cpp built with tests/lanes/lane_fault.hpp and its table
(kairn-gen-packed-runner-lane-fault): the packed mul_2_2_full whose special-value select reads the
mask of the neighboring lane. The test runs tests/crosscheck.py compiled on the oracle's random
requests of mul_2_2_full in F (seed 0, 6000 cases, as the quick tier's cross-checks), with this
runner as the only one, once with each assignment of lanes, and the runner once more by itself:

- consecutive: where no register of the consecutive assignment mixed a non-finite operand with
  finite ones (its report of the lanes says how many did), every lane's neighbor has operands of
  its kind and the fault changes no result: the cross-check must pass. That is the case of the
  oracle's stream at W = 2 and 4 (binary64 with NEON, binary64 with AVX2, binary32 with NEON);
  at W = 8 (binary32 with AVX2) a fifth of the registers mix, and the outcome is printed only.
- permuted: the cross-check must fail, by the oracle's verdict on the output (not by the runner,
  nor by the guards), with registers that mixed. The verdict is read from the oracle's summary of
  the output: cases that failed the claims of mul_2_2_full. The oracle's check exits with 1 also
  when it refuses the claims (a kernel whose claims it cannot read: the run fails, whatever the
  output); such a refusal is an error of this test, never the failure it expects, in either
  assignment.
- the consecutive assignment under the guard (--lane-guard), on the same requests: the runner
  must refuse it, with 3, as not mixed.

--claims FILE: the claims the oracle reads, in the cross-checks and in its requests of the guard's
run, gen/claims.json by default (tests/CMakeLists.txt, KAIRN_ORACLE_CLAIMS).

It prints each outcome and exits with 0 when all hold, 1 otherwise. The summaries and the
cross-checks' output are in DIR (lane_fault.F.*); the work directory that a failed cross-check
keeps is removed once the failure is the one expected.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CROSSCHECK = os.path.join(REPO, "tests", "crosscheck.py")
ORACLE = os.path.join(REPO, "oracle", "kairn-oracle")
KERNEL = "mul_2_2_full"


def crosscheck(a, assignment, log):
    """crosscheck.py compiled with the planted runner and ASSIGNMENT: (exit status, its output, the
    report of the lanes, the summary's base path, the oracle's outcome on the output)."""
    base = os.path.join(a.summary_dir, "lane_fault.%s.%s" % (a.format, assignment))
    label = "planted"
    command = [sys.executable, CROSSCHECK, "compiled", "--kernel", KERNEL, "--format", a.format,
               "--seed", a.seed, "--count", a.count, "--fail-on-suspicious",
               "--summary", base + ".json", "--packed-kernels", label, a.runner, assignment]
    if a.claims:
        command += ["--claims", a.claims]
    p = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=REPO)
    text = p.stdout.decode("utf-8", "replace")
    with open(log, "w", encoding="utf-8") as f:
        f.write(text)
    name = label if assignment == "permuted" else label + ".consecutive"
    report = None
    try:
        with open("%s.%s.lanes.json" % (base, name), encoding="utf-8") as f:
            report = json.load(f)["segments"][0]
    except (OSError, ValueError, KeyError, IndexError):
        pass
    return p.returncode, text, report, base, oracle_outcome("%s.%s.json" % (base, name))


def oracle_outcome(summary):
    """What the oracle said of an output, from the summary its check wrote (crosscheck.py writes it
    whether the check passed or not): ("refused", REASONS) when it refused the claims, which makes
    its check exit with 1 as a violated claim does, though nothing was judged of the output;
    ("failed", N) with the N cases that failed their claims; ("passed", 0); or ("unread", WHY)
    when there is no summary to read."""
    try:
        with open(summary, encoding="utf-8") as f:
            s = json.load(f)
        errors = s.get("claims_errors") or []
        failed = sum(k["stats"]["counts"]["failed"] for k in s["keys"])
    except (OSError, ValueError, KeyError, TypeError) as ex:
        return "unread", "%s: %s" % (type(ex).__name__, ex)
    if errors:
        return "refused", errors
    return ("failed", failed) if failed else ("passed", 0)


def refusal(outcome):
    """The text of a refusal of the claims, or None."""
    if outcome[0] != "refused":
        return None
    return "the oracle refused the claims (%s%s), an error of the test" % (
        outcome[1][0], " and %d more" % (len(outcome[1]) - 1) if len(outcome[1]) > 1 else "")


def verdict(text):
    """The oracle's count of the cases and the failures, from crosscheck.py's output."""
    return ["   " + line.strip() for line in text.splitlines()
            if re.match(r"^ +\d+ cases: ", line) or re.match(r"^ +\d+ +[A-Z]\w*: ", line)]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lane_fault.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--runner", required=True)
    ap.add_argument("--format", required=True, choices=("binary64", "binary32"))
    ap.add_argument("--summary-dir", required=True)
    ap.add_argument("--seed", default="0")
    ap.add_argument("--count", default="6000")
    ap.add_argument("--claims", help="the claims file of the oracle (default gen/claims.json)")
    a = ap.parse_args(argv)
    a.summary_dir = os.path.abspath(a.summary_dir)
    os.makedirs(a.summary_dir, exist_ok=True)
    wrong = []

    # The consecutive assignment.
    log = os.path.join(a.summary_dir, "lane_fault.%s.consecutive.log" % a.format)
    status, text, lanes, base, outcome = crosscheck(a, "consecutive", log)
    if not lanes:
        wrong.append("consecutive: no report of the lanes (exit %s); see %s" % (status, log))
    elif refusal(outcome):
        wrong.append("consecutive: %s (exit %d); see %s" % (refusal(outcome), status, log))
    else:
        w, mixed = lanes["lanes"], lanes["mixed"]
        print("consecutive, W = %d: %d of %d registers mixed a non-finite operand with finite ones; "
              "the cross-check %s (exit %d)" % (w, mixed, lanes["registers"],
                                                "passed" if status == 0 else "failed", status))
        if mixed == 0 and status != 0:
            wrong.append("consecutive: no register mixed, so the planted fault changes no result, "
                         "but the cross-check failed (exit %d); see %s" % (status, log))
        if status != 0:
            print("\n".join(verdict(text)))
            shutil.rmtree(base + ".work", ignore_errors=True)

    # The permuted assignment: the oracle must fail the output.
    log = os.path.join(a.summary_dir, "lane_fault.%s.permuted.log" % a.format)
    status, text, lanes, base, outcome = crosscheck(a, "permuted", log)
    # The oracle's verdict: its check failed the output (crosscheck.py's message) and its summary
    # has cases that failed, not a refusal of the claims.
    judged = "planted: oracle check 1 (0 is success)" in text and outcome[0] == "failed"
    if lanes:
        print("permuted, W = %d: %d of %d registers mixed a non-finite operand with finite ones "
              "(guard: %s); the cross-check %s (exit %d)%s" % (
                  lanes["lanes"], lanes["mixed"], lanes["registers"], lanes["guard"],
                  "passed" if status == 0 else "failed", status,
                  ", by the oracle's verdict" if judged else ""))
    if refusal(outcome):
        wrong.append("permuted: %s, not its verdict on the output (exit %s); see %s"
                     % (refusal(outcome), status, log))
    elif status != 1 or not judged or not lanes or lanes["mixed"] == 0:
        wrong.append("permuted: the cross-check must fail by the oracle's verdict on the output, "
                     "with registers that mixed (exit %s); see %s" % (status, log))
    else:
        print("\n".join(verdict(text)))
        shutil.rmtree(base + ".work", ignore_errors=True)

    # The guard on the consecutive assignment, the runner on its own.
    gen = subprocess.run([sys.executable, ORACLE, "gen", KERNEL, a.format, "--seed", a.seed,
                          "--count", a.count] + (["--claims", a.claims] if a.claims else []),
                         stdout=subprocess.PIPE, cwd=REPO)
    p = subprocess.run([a.runner, "--lanes", "consecutive", "--lane-guard"], input=gen.stdout,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    err = p.stderr.decode("utf-8", "replace").strip()
    print("consecutive under the guard: exit %d: %s" % (p.returncode, err))
    if gen.returncode != 0 or p.returncode != 3 or "the lanes did not mix" not in err:
        wrong.append("the guard must refuse the consecutive assignment with 3 (exit %d)" % p.returncode)

    if wrong:
        print("lane_fault: FAIL:\n  " + "\n  ".join(wrong))
        return 1
    print("lane_fault: the planted fault passes where no register mixes and fails where they do")
    return 0


if __name__ == "__main__":
    sys.exit(main())
