#!/usr/bin/env python3
"""The emulated kernels and the generator's interpreter print the same lines, byte for byte, on the
same requests of every kernel and fold (docs/developer/testing.md, "The emulated formats").

    python3 tests/emulated/same_lines.py --runner LABEL EXECUTABLE ... --format F
        --seed S --count N [--max-length L] [--claims FILE]
        (--upward-runner LABEL EXECUTABLE | --no-upward)

The two are implementations of the semantics of the kernel IR that share nothing: the C++ that the
generator prints for the emulated limb type (tests/emulated/gen/kernels.hpp), on the integer
arithmetic of tests/emulated/number.cpp, and the interpreter's evaluation of the IR
(python3 gen/kairn-gen interp), on its own. Every kernel and fold of the claims gets N requests of
format F from the oracle's generator (seed S; for a fold N arrays of up to L elements, and for a map
or a ball vector N requests in place too), all in one stream, which the interpreter and each
runner complete in one process each; then the kernels that have a path of constant evaluation
(RUNNER --ce-paths) the same with --ce. Any byte that differs fails the test, with the first line
of each kernel where it does: a fault of the printer of the C++ (a select's arm, a value inlined
from the wrong call, the fix-up branch), of the emulated arithmetic or of the interpreter. The
oracle does not judge these lines: the tests crosscheck.emulated.K do, kernel by kernel.

The kernels of the round-up interval ("rounding": "upward" in the claims; they require the rounding
mode upward set by kairn::upward::Scope and the options of docs/concepts/upward.md, GCC and Clang
-frounding-math, MSVC /fp:strict, in their compiled forms) are not in the emulated runners of the
other kernels: their emulated kernels (tests/emulated/gen/upward.hpp) have a runner of their own,
gen/tests/upward_runner.cpp built with KAIRN_UPWARD_RUNNER_EMULATED. With --upward-runner their
requests, in one stream of their own, are completed by the interpreter and by that runner in each
form of max_nl (--max sel, --max nm), the same bytes; with --no-upward they are left out, and the
run says so. One of the two is required when the claims have such kernels.

Python's standard library and the oracle (in this process, through tests/crosscheck.py); the
generator's interpreter as a process.
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
REPO = os.path.dirname(TESTS)
sys.dont_write_bytecode = True
sys.path.insert(0, TESTS)
import crosscheck  # noqa: E402
from kairn_oracle import cli as oracle_cli  # noqa: E402

# The oracle's command line reads the claims file on each command, four fifths of the time of a
# gen of a hundred requests; here hundreds of gens read the same file, which is read once.
_read_claims = oracle_cli._claims
_claims_read = {}


def _claims_once(path):
    if path not in _claims_read:
        _claims_read[path] = _read_claims(path)
    return _claims_read[path]


oracle_cli._claims = _claims_once


def generate(kernel, fmt, seed, count, claims, extra=()):
    status, text = crosscheck.oracle(["gen", kernel, fmt, "--seed", seed, "--count", str(count)]
                                     + claims + list(extra), capture=True)
    if status != 0:
        raise RuntimeError("the oracle's gen failed for %s %s (%s)" % (kernel, fmt, status))
    return text


def run(command, data):
    p = subprocess.run(command, input=data, stdout=subprocess.PIPE, cwd=REPO)
    return p.returncode, p.stdout


def compare(what, data, commands):
    """The texts of the differences among the outputs of COMMANDS ({label: command}) on DATA."""
    outs, failed = {}, []
    for label, command in commands.items():
        t0 = time.time()
        status, out = run(command, data)
        if status != 0:
            failed.append("%s: %s failed (%s)" % (what, label, status))
            continue
        outs[label] = out
        print("-- %s: %s, %.1f s" % (what, label, time.time() - t0), flush=True)
    labels = list(outs)
    for label in labels[1:]:
        if outs[label] == outs[labels[0]]:
            continue
        a = outs[labels[0]].decode("ascii", "replace").split("\n")
        b = outs[label].decode("ascii", "replace").split("\n")
        seen = set()
        for i in range(max(len(a), len(b))):
            x, y = (a[i] if i < len(a) else ""), (b[i] if i < len(b) else "")
            k = (x or y).split(" ")[0]
            if x != y and k not in seen:
                seen.add(k)
                failed.append("%s: %s and %s differ, first at line %d (%s):\n  %s: %s\n  %s: %s"
                              % (what, labels[0], label, i + 1, k, labels[0], x, label, y))
    return failed, labels


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--runner", nargs=2, action="append", required=True, metavar=("LABEL", "EXECUTABLE"))
    ap.add_argument("--format", required=True)
    ap.add_argument("--seed", required=True)
    ap.add_argument("--count", type=int, required=True)
    ap.add_argument("--max-length", default="16")
    ap.add_argument("--claims")
    up = ap.add_mutually_exclusive_group()
    up.add_argument("--upward-runner", nargs=2, metavar=("LABEL", "EXECUTABLE"),
                    help="the emulated runner of the round-up interval's kernels")
    up.add_argument("--no-upward", action="store_true", help="leave the round-up interval's kernels out")
    a = ap.parse_args(argv)
    claims_args = ["--claims", a.claims] if a.claims else []
    with open(a.claims or os.path.join(REPO, "gen", "claims.json"), encoding="utf-8") as f:
        claims = json.load(f)
    upward = [k["name"] for k in claims["kernels"] if k.get("rounding") == "upward"]
    if upward and not (a.upward_runner or a.no_upward):
        ap.error("the claims have %d kernels of the round-up interval: give --upward-runner or --no-upward"
                 % len(upward))
    kernels = [k["name"] for k in claims["kernels"] if k["name"] not in upward]
    folds = claims.get("folds", [])
    t0 = time.time()
    parts = {}
    for k in kernels:
        parts[k] = generate(k, a.format, a.seed, a.count, claims_args)
    for fd in folds:
        text = generate(fd["name"], a.format, a.seed, a.count, claims_args, ["--max-length", a.max_length])
        if fd.get("map") or fd.get("bv"):
            text += generate(fd["name"], a.format, a.seed, a.count, claims_args,
                             ["--max-length", a.max_length, "--inplace"])
        parts[fd["name"]] = text
    stream = "".join(parts.values()).encode("ascii")
    lines = sum(1 for line in stream.split(b"\n") if line and not line.startswith(b"#"))
    print("-- %d requests of %d kernels and %d folds in %s, generated in %.1f s"
          % (lines, len(kernels), len(folds), a.format, time.time() - t0), flush=True)
    commands = {"interp": crosscheck.INTERP}
    commands.update({label: [exe] for label, exe in a.runner})
    failed, labels = compare("the run-time path", stream, commands)
    paths = crosscheck.ce_paths(a.runner[0][1])
    ce = "".join(parts[k] for k in kernels if k in paths).encode("ascii")
    ce_lines = sum(1 for line in ce.split(b"\n") if line and not line.startswith(b"#"))
    commands = {"interp.ce": crosscheck.INTERP + ["--ce"]}
    commands.update({label + ".ce": [exe, "--ce"] for label, exe in a.runner})
    more, ce_labels = compare("the path of constant evaluation", ce, commands)
    failed += more
    up_text = ""
    if upward and a.upward_runner:
        label, exe = a.upward_runner
        up_stream = "".join(generate(k, a.format, a.seed, a.count, claims_args) for k in upward).encode("ascii")
        up_lines = sum(1 for line in up_stream.split(b"\n") if line and not line.startswith(b"#"))
        up_labels = []
        for form in ("sel", "nm"):
            more, got = compare("the round-up interval, --max %s" % form, up_stream,
                                {"interp --max %s" % form: crosscheck.INTERP + ["--max", form],
                                 "%s --max %s" % (label, form): [exe, "--max", form]})
            failed += more
            up_labels += got
        up_text = ("; the round-up interval's %d kernels, %d lines in each form of max_nl, the same bytes "
                   "from %s" % (len(upward), up_lines, ", ".join(up_labels)))
    elif upward:
        up_text = "; the round-up interval's %d kernels left out (--no-upward)" % len(upward)
    if failed:
        print("same_lines: FAILED, the emulated kernels and the interpreter differ:\n" + "\n".join(failed))
        return 1
    print("same_lines: passed: %d lines of %d kernels and %d folds, the same bytes from %s; on the path "
          "of constant evaluation %d lines of %d kernels, the same bytes from %s%s"
          % (lines, len(kernels), len(folds), ", ".join(labels), ce_lines,
             sum(1 for k in kernels if k in paths), ", ".join(ce_labels), up_text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
