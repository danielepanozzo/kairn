"""The regression cases (tests/regression/cases.txt) through every runner, judged by the oracle.

    python3 tests/regression/run.py CASES [--runner LABEL=COMMAND]... [--interp]
                                    [--api LABEL=EXECUTABLE]... [--claims FILE]

CASES is a file of request lines of the oracle's protocol (docs/developer/architecture.md, "The
line protocol"), each with comments above it that say where it came from; the rule for adding one
is at the top of that file. Each runner completes the lines it can run:

- a compiled runner of the generated kernels (--runner, gen/tests/runner.cpp or
  gen/tests/packed_runner.cpp): every line of binary64 and binary32;
- the generator's interpreter (--interp): every line, toy formats included;
- a runner of the public interface (--api, tests/api/runner.cpp): the lines of binary64 and
  binary32 of every kernel it maps a form to (`--list`), once per form of the kernel (`--forms`).

The oracle (oracle/kairn_oracle, in this process) judges every output, as the cross-checks do:
no claim violated, no invalid case, every line completed and in order, and no suspicious
non-finite result (`--fail-on-suspicious`) but for `split` and `two_prod_dekker`, whose product by
the splitter may overflow (tests/CMakeLists.txt, _intermediate_overflow). An output identical byte
for byte to one judged before has its verdict. It exits with 1 if anything fails, and prints the
command that reruns each failing line. Python's standard library only.
"""
import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(REPO, "oracle"))
from kairn_oracle import check as C  # noqa: E402
from kairn_oracle.claims import load_claims  # noqa: E402

INTERMEDIATE_OVERFLOW = ("split", "two_prod_dekker")
COMPILED_FORMATS = ("binary64", "binary32")


def read_cases(path):
    """The request lines of the file, in order (comments and blank lines left out)."""
    with open(path, "r", encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.lstrip().startswith("#")]


def run(command, lines):
    """(exit status, completed lines, standard error) of a runner on the lines."""
    data = ("\n".join(lines) + "\n").encode("utf-8")
    try:
        p = subprocess.run(command, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as ex:
        return 127, [], str(ex)
    out = [ln for ln in p.stdout.decode("utf-8", "replace").splitlines() if ln and ln[0] != "#"]
    return p.returncode, out, p.stderr.decode("utf-8", "replace").strip()


class Judge:
    def __init__(self, claims):
        self.claims = claims
        self.ck = C.Checker(claims, False, 1)
        self.verdicts = {}             # SHA-256 of an output -> (failures, counts, first label)
        self.judged_outputs = 0

    def judge(self, label, requests, status, out, err):
        """A list of failures (text) of one runner's output."""
        if status != 0:
            return ["%s: the runner exited with %d%s" % (label, status, ": " + err if err else "")]
        if len(out) != len(requests) or any(o.partition(" -> ")[0] != r
                                            for o, r in zip(out, requests)):
            return ["%s: %d completed lines for %d requests, or not in their order"
                    % (label, len(out), len(requests))]
        key = hashlib.sha256("\n".join(out).encode("utf-8")).hexdigest()
        if key in self.verdicts:
            fails, counts, first = self.verdicts[key]
            return ["%s (the same output as %s): %s" % (label, first, f) for f in fails]
        self.judged_outputs += 1
        fails = []
        counts = {"judged": 0, "nonfinite": 0}
        ck = self.ck
        for line in out:
            # One summary per line, so that each line has its verdict; the checker keeps its
            # compiled plans.
            ck.summary = C.Summary(1)
            ck.line(line)
            s = ck.finish()
            t = s.totals()
            counts["judged"] += t["judged"]
            counts["nonfinite"] += t["nonfinite"] + t["nonfinite_tail"]
            kernel = line.split(" ", 1)[0]
            why = []
            if t["failed"] or s.stream_errors or s.claims_errors:
                why += [w for st in s.keys.values() for _, w in st.examples["failure"]]
                why += s.stream_errors + s.claims_errors
            if t["invalid"]:
                why += ["invalid: " + w for st in s.keys.values() for _, w in st.examples["invalid"]]
            if t["suspicious"] and kernel not in INTERMEDIATE_OVERFLOW:
                why += ["suspicious: " + w for st in s.keys.values()
                        for _, w in st.examples["suspicious"]]
            if why or (t["failed"] + t["invalid"]):
                fails.append("%s\n      %s" % ("; ".join(why) or "failed", line))
        self.verdicts[key] = (fails, counts, label)
        return ["%s: %s" % (label, f) for f in fails]


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cases")
    ap.add_argument("--runner", action="append", default=[], metavar="LABEL=COMMAND",
                    help="a compiled runner of the generated kernels (binary64 and binary32)")
    ap.add_argument("--interp", action="store_true", help="the generator's interpreter")
    ap.add_argument("--api", action="append", default=[], metavar="LABEL=EXECUTABLE",
                    help="a runner of the public interface (tests/api/runner.cpp)")
    ap.add_argument("--claims", default=os.path.join(REPO, "gen", "claims.json"))
    a = ap.parse_args(argv)
    claims = load_claims(a.claims)
    if claims.errors():
        print("regression: FAIL: the claims cannot be read: %s" % "; ".join(claims.errors()))
        return 1
    cases = read_cases(a.cases)
    unknown = sorted({ln.split(" ", 1)[0] for ln in cases} - set(claims.kernels))
    if unknown:
        print("regression: kernels without claims: %s" % ", ".join(unknown))
        return 1
    compiled = [ln for ln in cases if ln.split(" ")[1] in COMPILED_FORMATS]
    judge = Judge(claims)
    failures = []
    report = []

    def one(label, command, lines):
        if not lines:
            return
        status, out, err = run(command, lines)
        f = judge.judge(label, lines, status, out, err)
        failures.extend(f)
        report.append("%-40s %4d lines%s" % (label, len(lines), "" if not f else ", FAILED"))

    for spec in a.runner:
        label, _, exe = spec.partition("=")
        one(label, [exe], compiled)
    if a.interp:
        one("interp", [sys.executable, os.path.join(REPO, "gen", "kairn-gen"), "interp"], cases)
    for spec in a.api:
        label, _, exe = spec.partition("=")
        status, listed, err = run([exe, "--list"], [])
        if status != 0:
            failures.append("%s --list: exited with %d %s" % (label, status, err))
            continue
        mapped = set(listed)
        by_kernel = {}
        for ln in compiled:
            k = ln.split(" ", 1)[0]
            if k in mapped:
                by_kernel.setdefault(k, []).append(ln)
        for k, lines in sorted(by_kernel.items()):
            status, forms, err = run([exe, "--forms", k], [])
            if status != 0 or not forms:
                failures.append("%s --forms %s: exited with %d %s" % (label, k, status, err))
                continue
            for form in forms:
                one("%s, %s, form %s" % (label, k, form), [exe, "--form", form], lines)
    n_api = sum(1 for r in report if ", form " in r)
    for r in report:
        if ", form " not in r or "FAILED" in r:
            print("regression: %s" % r)
    if n_api:
        print("regression: and %d forms of the public interface" % n_api)
    print("regression: %d cases (%d of binary64 and binary32), %d runs, %d distinct outputs "
          "judged" % (len(cases), len(compiled), len(report), judge.judged_outputs))
    if failures:
        print("regression: FAIL")
        for f in failures:
            print("  " + f)
        print("To rerun one line: echo 'LINE' | RUNNER | python3 oracle/kairn-oracle check "
              "--fail-on-suspicious (without the option for split and two_prod_dekker); for a "
              "form of the public interface, RUNNER --form FORM")
        return 1
    if not report:
        print("regression: FAIL: no runner ran a case")
        return 1
    print("regression: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
