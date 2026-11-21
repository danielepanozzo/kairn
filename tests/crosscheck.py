"""One cross-check in one process: the oracle's requests, every runner on them, the oracle's verdict
on each distinct output and, for the kernels' runners, the guards (docs/developer/testing.md,
"Cross-checks").

    python3 tests/crosscheck.py compiled --kernel K --format F --summary FILE
        (--seed S --count N | --exhaustive [--restrict R1,R2,...]) [--fail-on-suspicious]
        (--runner LABEL EXECUTABLE)... [--interp] [--refrun] [--claims FILE]
        [--orders O1,O2,...] [--max-length L]
        [(--packed-runner LABEL EXECUTABLE)... --packed-lanes W [--packed-count N]]
    python3 tests/crosscheck.py api --kernel K --format F --seed S --count N --summary-dir DIR
        (--runner LABEL EXECUTABLE)... [--first-form LABEL]... [--same-as LABEL OTHER]...
        [--claims FILE]

Each output is that of the pipeline

    python3 oracle/kairn-oracle gen K F ... | RUNNER | python3 oracle/kairn-oracle check ...

with the oracle's gen and check run in this process, through the oracle's own command line
(oracle/kairn_oracle/cli.py, main: the same code, options and exit status as the commands
above), and each runner in a process of its own, which sees nothing but the requests. Python's
standard library, the oracle (oracle/kairn_oracle) and the guards (tests/crosscheck_guards.py);
nothing of the generator's code (gen/), whose interpreter --interp runs as a process.

The requests are generated once, into WORK/requests.txt, with the bytes the oracle's gen writes
to a file (on Windows, lines that end with CR LF), and every runner reads that file on its
standard input, in turn. Every output is judged, but an output identical byte for byte to one
judged before is not judged again: the oracle's verdict and summary depend on nothing but the
lines it reads and the claims, so the verdict of the first is that of every runner that wrote the
same bytes, and the report says which runners share it. The oracle reads each output as its
standard input would read the same bytes (the encoding and newlines of a process of this Python).

compiled, the tests crosscheck.compiled.K.F of the quick tier and full.crosscheck.compiled.K.F of
the full tier: the runners of the generated kernels (gen/tests/runner.cpp, packed_runner.cpp),
each named by its LABEL; --interp adds the generator's interpreter (python3 gen/kairn-gen interp)
as one more, labelled interp, and --refrun the oracle's reference runner (python3
oracle/kairn-oracle refrun), labelled refrun, which tests/test_crosscheck_guards.py runs for
rational_1 and rational_2. K is a kernel of gen/claims.json or one of these two,
kairn::rational<X>(num, den), which the oracle knows without claims (oracle/README.md,
"rational"): the same pipeline and guards, with no enumeration. K may also be a fold of the list
"folds" (architecture.md, "Folds"), whose requests carry arrays: --orders and --max-length go to
the oracle's gen and to the guards; the packed runners (--packed-runner) complete only the lane
order of their register, so they run on a stream of their own, gen --orders lanes:W with W of
--packed-lanes (and --packed-count cases), judged and guarded as the first. WORK is SUMMARY's name, without
its extension, with .work; the summary of each output judged is written next to SUMMARY, as
SUMMARY's name with the label of the first runner that wrote that output (check --json). The
test fails if a runner fails, if the
oracle fails an output (any violated claim or broken stream, an invalid case, which is one whose
operands are outside the kernel's requirements and is not judged: check --expect-valid; and with
--fail-on-suspicious a suspicious non-finite result), or if the guards fail its summary: the run
did not check what it set out to check (tests/crosscheck_guards.py). An enumeration
(--exhaustive) is supported as crosscheck.cmake supports it, though the tests run the interpreter's
enumerations through crosscheck.cmake.

api, the tests api.oracle.K.F, full.api.oracle.K.F and full.api.flags.oracle.K.F: the runners of
the public interface (tests/api/runner.cpp), each with every form it maps to the kernel
(RUNNER --forms K), or with its first form only for a runner named by --first-form, each form a
run of RUNNER --form FORM named LABEL.FORM; check always with --expect-valid and
--fail-on-suspicious. WORK is
DIR/K.F.work, and the summary of each output judged DIR/K.F.LABEL.FORM.json. The test fails if a
runner maps no form to the kernel, if a run fails (a form that computes only some lines of its
kernel fails when it computed none), if the oracle fails an output, if it judged no case of an
output, if an output has no case of a stratum the generator's header announced, or if a summary
exceeds the guards' bound (crosscheck_guards.SUMMARY_BYTES); and, for each
--same-as LABEL OTHER, if a form of runner LABEL wrote other bytes than the same form of runner
OTHER (the settings of KAIRN_ENCLOSURE_CODE, which must compute the same bits).

--claims FILE, in both modes: the claims the oracle's gen and check read (and the guards, through
the summary), gen/claims.json by default (tests/CMakeLists.txt, KAIRN_ORACLE_CLAIMS).

The oracle's report is printed for every output judged. On a failure, the test says which runner
and form failed and how, prints the command that reruns one case by hand from the tag of its line
(#STRATUM:INDEX, #exhaustive:INDEX), keeps WORK with the requests and the outputs that failed, and
exits with 1. On a pass it removes WORK and exits with 0.
"""
import argparse
import hashlib
import io
import json
import locale
import os
import shlex
import shutil
import subprocess
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ORACLE = os.path.join(REPO, "oracle", "kairn-oracle")
INTERP = [sys.executable, os.path.join(REPO, "gen", "kairn-gen"), "interp"]
REFRUN = [sys.executable, ORACLE, "refrun"]

# The oracle runs from the source tree; nothing may write caches into it (oracle/kairn-oracle).
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(REPO, "oracle"))
sys.path.insert(0, HERE)
from kairn_oracle import cli as oracle_cli  # noqa: E402
# Imported now, so that the report of check, whose default output is the sys.stdout of the moment
# the module is imported, goes to this process's standard output.
from kairn_oracle import check as _oracle_check  # noqa: E402,F401
import crosscheck_guards  # noqa: E402


def shell(words):
    """WORDS as a command line to paste into this platform's shell."""
    return subprocess.list2cmdline(words) if os.name == "nt" else shlex.join(words)


def say(text):
    print("-- " + text, flush=True)


# --- The oracle, in this process ----------------------------------------------------------------

def stdio_codec():
    """The encoding and error handler of the standard input and output of a Python process when
    they are files or pipes, as Python chooses them: PYTHONIOENCODING, then UTF-8 mode, then the
    locale's encoding."""
    encoding, _, errors = os.environ.get("PYTHONIOENCODING", "").partition(":")
    if not encoding:
        encoding = locale.getpreferredencoding(False)
    if not errors:
        c_locale = os.name != "nt" and locale.setlocale(locale.LC_CTYPE) in ("C", "POSIX")
        errors = "surrogateescape" if sys.flags.utf8_mode or c_locale else "strict"
    return encoding, errors


def as_stdin(data):
    """The bytes DATA as the standard input of a Python process would read them: decoded with
    stdio_codec(), lines ending at LF, and on Windows, whose standard input translates them, at
    CR LF and CR too."""
    encoding, errors = stdio_codec()
    return io.TextIOWrapper(io.BytesIO(data), encoding=encoding, errors=errors,
                            newline=None if os.name == "nt" else "\n")


def exit_status(code):
    """The exit status of a Python process that ends with sys.exit(CODE)."""
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    print(code, file=sys.stderr)
    return 1


def oracle(argv, stdin=None, capture=False):
    """python3 oracle/kairn-oracle ARGV, in this process: its exit status, and with CAPTURE what
    it wrote to its standard output. STDIN, if given, is its standard input. What it writes to its
    standard error, and its report (check), go to this process's."""
    saved = sys.stdin, sys.stdout
    out = io.StringIO() if capture else None
    sys.stdout.flush()
    try:
        if stdin is not None:
            sys.stdin = stdin
        if capture:
            sys.stdout = out
        try:
            status = exit_status(oracle_cli.main(list(argv)))
        except SystemExit as ex:
            status = exit_status(ex.code)
        except Exception:           # as an uncaught exception ends the process: a traceback, 1
            traceback.print_exc()
            status = 1
    finally:
        sys.stdin, sys.stdout = saved
    sys.stdout.flush()
    sys.stderr.flush()
    return status, (out.getvalue() if capture else None)


def generate(argv, work, name="requests.txt"):
    """The oracle's gen ARGV into WORK/NAME, as its standard output would have written them to
    that file: (exit status, the file's path)."""
    status, text = oracle(argv, capture=True)
    requests = os.path.join(work, name)
    encoding, errors = stdio_codec()
    with open(requests, "w", encoding=encoding, errors=errors) as f:    # newlines: os.linesep
        f.write(text)
    return status, requests


def judge(argv, output):
    """The oracle's check ARGV on the bytes OUTPUT, read as its standard input: its exit status."""
    status, _ = oracle(argv, stdin=as_stdin(output))
    return status


# --- The runners ----------------------------------------------------------------------------------

def run_all(runs, requests):
    """Each run (NAME, COMMAND) on the file REQUESTS as its standard input, in turn, its standard
    output read through a pipe and its standard error passed on: [(NAME, STATUS, OUTPUT, FIRST)].
    STATUS is the exit status (or why it could not start), FIRST the name of the first run whose
    output is the same, byte for byte (NAME itself if there is none before it, or if it failed).

    Through a pipe, because writing the output to a file as the runner goes was the slow part on
    the Windows machine of docs/developer/testing.md: a file as the scalar runner's standard output
    cost 0.09 to 0.1 seconds per run on 2 000 requests there, against 0.02 through a pipe."""
    first_of = {}
    done = []
    for name, command in runs:
        sys.stdout.flush()
        try:
            with open(requests, "rb") as stdin:
                p = subprocess.run(command, stdin=stdin, stdout=subprocess.PIPE, cwd=REPO)
            status, output = p.returncode, p.stdout
        except OSError as ex:
            status, output = "cannot start: %s" % ex, b""
        first = name
        if status == 0:
            first = first_of.setdefault(hashlib.sha256(output).hexdigest(), name)
        done.append((name, status, output, first))
    return done


def keep(work, name, output):
    with open(os.path.join(work, name + ".txt"), "wb") as f:
        f.write(output)


def fresh(directory):
    shutil.rmtree(directory, ignore_errors=True)
    os.makedirs(directory, exist_ok=True)


def remove(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


# --- The kernels' runners -----------------------------------------------------------------------

def guards(summary, argv):
    """The guards on a summary the oracle passed (tests/crosscheck_guards.py SUMMARY ARGV), in this
    process: (passed, what they print)."""
    try:
        a = crosscheck_guards.parser().parse_args([summary] + argv)
        status, lines = crosscheck_guards.run(a)
    except SystemExit as ex:
        status, lines = exit_status(ex.code) or 1, ["the guards' arguments were refused"]
    except Exception:
        status, lines = 1, [traceback.format_exc().strip()]
    return status == 0, "\n".join(lines).strip()


def compiled(a):
    kernel, fmt = a.kernel, a.format
    summary = os.path.abspath(a.summary)
    summary_dir = os.path.dirname(summary)
    base = os.path.splitext(os.path.basename(summary))[0]
    work = os.path.join(summary_dir, base + ".work")
    fresh(work)

    # The streams: the runners given by --runner (and --interp, --refrun) on the requests asked
    # for; for a fold, the packed runners (--packed-runner) on requests of their one order,
    # lanes:W of their register (--packed-lanes), which is all they complete.
    streams = []
    runs = [(label, [exe]) for label, exe in a.runner or []]
    if a.interp:
        runs.append(("interp", INTERP))
    if a.refrun:
        runs.append(("refrun", REFRUN))
    if runs:
        streams.append(("requests", a.orders, a.count, runs))
    if a.packed_runner:
        if not a.packed_lanes:
            print("crosscheck.py: --packed-runner needs --packed-lanes W", file=sys.stderr)
            return 2
        streams.append(("requests-packed", "lanes:%s" % a.packed_lanes,
                        a.packed_count or a.count,
                        [(label, [exe]) for label, exe in a.packed_runner]))
    if not streams:
        print("crosscheck.py: no runner (--runner LABEL EXECUTABLE, --interp, --refrun, "
              "--packed-runner LABEL EXECUTABLE)", file=sys.stderr)
        return 2
    failed = []
    reports = []
    for name, orders, count, runs in streams:
        failed += compiled_stream(a, name, orders, count, runs, summary_dir, base, work, reports)
    if failed:
        print("cross-check of %s %s failed for:\n%s\nThe requests and the outputs that failed are "
              "in %s" % (kernel, fmt, "\n".join(failed), work), flush=True)
        return 1
    for text in reports:
        say(text)
    shutil.rmtree(work, ignore_errors=True)
    return 0


def compiled_stream(a, name, orders, count, runs, summary_dir, base, work, reports):
    """One stream of requests through its runners: the texts of the failures (and, on a pass, what
    was checked, appended to reports)."""
    kernel, fmt = a.kernel, a.format
    claims = ["--claims", a.claims] if a.claims else []
    gen = ["gen", kernel, fmt] + claims
    guard_args = ["--kernel", kernel, "--format", fmt]
    if a.exhaustive:
        gen.append("--exhaustive")
        guard_args.append("--exhaustive")
        if a.restrict:
            for r in a.restrict.split(","):
                gen += ["--restrict", r]
            guard_args += ["--restrict", a.restrict]
    else:
        gen += ["--seed", a.seed]
        guard_args += ["--seed", a.seed, "--count", count]
    # A fold's requests: its orders and its maximum length, which the guards check too.
    if orders:
        gen += ["--orders", orders]
        guard_args += ["--orders", orders]
    if a.max_length is not None:
        gen += ["--max-length", a.max_length]
        guard_args += ["--max-length", a.max_length]
    one = gen + ["--start", "INDEX", "--count", "1"]
    if not a.exhaustive:
        gen += ["--count", count]
    check = (["check", "--expect-valid"] + (["--fail-on-suspicious"] if a.fail_on_suspicious else [])
             + claims)
    python_oracle = [sys.executable, ORACLE]

    status, requests = generate(gen, work, name + ".txt")
    if status != 0:
        print("cross-check of %s %s: the request generator failed (%s): %s"
              % (kernel, fmt, status, shell(python_oracle + gen)))
        return ["%s: the request generator failed" % name]

    command_of = dict(runs)
    failed = []             # one text per runner that failed
    failed_first = set()    # the runners whose output the oracle or the guards failed
    passed = []             # the runners whose output passed, each the first that wrote it
    sharing = {}            # such a runner -> the runners that wrote the same output
    report_of = {}
    for label, status, output, first in run_all(runs, requests):
        what = "cross-check of %s %s with %s" % (kernel, fmt, label)
        again = "  %s | %s | %s" % (shell(python_oracle + one), shell(command_of[label]),
                                    shell(python_oracle + check))
        if status != 0:
            say("%s: the runner failed (%s)" % (what, status))
            keep(work, label, output)
            failed.append("%s: the runner failed (%s); to run one case again:\n%s"
                          % (label, status, again))
            continue
        if first != label:
            # The same bytes as an output judged above: the same verdict.
            say("%s: the same output, byte for byte, as %s's, judged above" % (what, first))
            if first in failed_first:
                failed.append("%s: the same output as %s, which failed" % (label, first))
            sharing[first].append(label)
            continue
        sharing[label] = [label]
        summary_of = os.path.join(summary_dir, "%s.%s.json" % (base, label))
        remove(summary_of)
        say("== %s: the oracle's report" % what)
        status = judge(check + ["--json", summary_of], output)
        if status != 0:
            failed_first.add(label)
            keep(work, label, output)
            failed.append("%s: oracle check %s (0 is success); to run one case again, with INDEX "
                          "from its tag:\n%s" % (label, status, again))
            continue
        # A pass must have checked what it set out to check.
        ok, report = guards(summary_of, guard_args)
        if not ok:
            failed_first.add(label)
            keep(work, label, output)
            failed.append("%s: the oracle passed it, but it did not check what it set out to:\n%s"
                          % (label, report))
            continue
        passed.append(label)
        report_of[label] = report

    for label in passed:
        reports.append("cross-check of %s %s with %s: passed, %s"
                       % (kernel, fmt, ", ".join(sharing[label]), report_of[label]))
    return failed


# --- The public interface -------------------------------------------------------------------------

API_CHECK = ["check", "--expect-valid", "--fail-on-suspicious"]


def judge_api(output, summary, count, claims=()):
    """The verdict on one output of a form of the public interface: "" if it passed, the reason
    otherwise. Beyond the oracle's verdict, something was judged, in every stratum the generator
    announced."""
    remove(summary)
    status = judge(API_CHECK + list(claims) + ["--json", summary], output)
    if status != 0:
        return "oracle check %s; 0 is success" % status
    try:
        size = os.path.getsize(summary)
        if size > crosscheck_guards.SUMMARY_BYTES:
            return ("the oracle's summary %s is %d bytes, above the %d a summary may take"
                    % (summary, size, crosscheck_guards.SUMMARY_BYTES))
        with open(summary, encoding="utf-8") as f:
            s = json.load(f)
        strata = s["coverage"][0]["desc"]["strata"]
        judged = sum(k["stats"]["counts"]["judged"] for k in s["keys"])
        tags = [k["tag"] for k in s["keys"]]
    except (OSError, ValueError, KeyError, IndexError, TypeError) as ex:
        return ("the oracle's summary %s has no stream of the generator, or cannot be read "
                "(%s: %s)" % (summary, type(ex).__name__, ex))
    reasons = []
    if judged == 0:
        reasons.append("the oracle judged no case")
    for stratum in (strata.split(",") if strata else []):
        if stratum not in tags:
            reasons.append("no case of stratum %s in %s" % (stratum, count))
    return "; ".join(reasons)


def api(a):
    kernel, fmt = a.kernel, a.format
    summary_dir = os.path.abspath(a.summary_dir)
    work = os.path.join(summary_dir, "%s.%s.work" % (kernel, fmt))
    fresh(work)
    claims = ["--claims", a.claims] if a.claims else []
    gen = ["gen", kernel, fmt, "--seed", a.seed, "--count", a.count] + claims
    status, requests = generate(gen, work)
    if status != 0:
        print("the request generator failed (%s) for %s %s" % (status, kernel, fmt))
        return 1
    if not a.runner:
        print("crosscheck.py: no runner (--runner LABEL EXECUTABLE)", file=sys.stderr)
        return 2

    # Every form of every runner on the same requests, each named LABEL.FORM.
    runs = []
    what_of = {}
    for label, exe in a.runner:
        sys.stdout.flush()
        try:
            p = subprocess.run([exe, "--forms", kernel], stdout=subprocess.PIPE)
            status, text = p.returncode, p.stdout.decode("utf-8", "replace")
        except OSError as ex:
            status, text = "cannot start: %s" % ex, ""
        if status != 0:
            print("%s --forms %s failed: %s" % (exe, kernel, status))
            return 1
        text = text.replace("\r", "").strip()
        forms = text.split("\n") if text else []
        if not forms:
            print("no public operation of the API runner %s maps to %s" % (label, kernel))
            return 1
        if label in (a.first_form or []):
            forms = forms[:1]
        for form in forms:
            name = "%s.%s" % (label, form)
            what_of[name] = "%s, form %s" % (label, form)
            runs.append((name, [exe, "--form", form]))

    failed = []
    failure_of = {}
    n_judged = 0
    done = run_all(runs, requests)
    # --same-as LABEL OTHER: every form of LABEL wrote the same bytes as the same form of OTHER.
    first_of = {name: first for name, status, _, first in done if status == 0}
    n_same = 0
    for label, other in a.same_as or []:
        for name in [n for n, _ in runs if n.startswith(label + ".")]:
            twin = other + name[len(label):]
            if twin not in what_of:
                failed.append("%s: %s has no form %s" % (what_of[name], other, name[len(label) + 1:]))
            elif name in first_of and twin in first_of and first_of[name] != first_of[twin]:
                failed.append("%s: not the same bytes as %s" % (what_of[name], what_of[twin]))
            else:
                n_same += 1
    for name, status, output, first in done:
        what = what_of[name]
        if status != 0:
            say("== %s %s, %s: the runner failed (%s)" % (kernel, fmt, what, status))
            keep(work, name, output)
            failed.append("%s (runner %s; 0 is success)" % (what, status))
            continue
        if first != name:
            # The same bytes as an output judged above: the same verdict.
            say("== %s %s, %s: the same output, byte for byte, as %s, judged above"
                % (kernel, fmt, what, what_of[first]))
            if failure_of[first]:
                failed.append("%s (the same output as %s: %s)" % (what, what_of[first],
                                                                    failure_of[first]))
            continue
        n_judged += 1
        say("== %s %s, %s" % (kernel, fmt, what))
        summary = os.path.join(summary_dir, "%s.%s.%s.json" % (kernel, fmt, name))
        failure = judge_api(output, summary, a.count, claims)
        failure_of[name] = failure
        if failure:
            keep(work, name, output)
            failed.append("%s (%s)" % (what, failure))

    if failed:
        one = [sys.executable, ORACLE, "gen", kernel, fmt, "--seed", a.seed, "--start", "INDEX",
               "--count", "1"] + claims
        print("the public interface failed the claims of %s %s in:\n  %s\n"
              "To rerun case INDEX of form F: %s | RUNNER --form F | %s\n"
              "with RUNNER one of:%s\n"
              "The requests and the outputs that failed are in %s"
              % (kernel, fmt, "\n  ".join(failed), shell(one),
                 shell([sys.executable, ORACLE] + API_CHECK + claims),
                 "".join("\n  %s: %s" % (label, exe) for label, exe in a.runner), work), flush=True)
        return 1
    shutil.rmtree(work, ignore_errors=True)
    say("%s %s: %d forms of the public interface passed (distinct outputs judged: %d)%s"
        % (kernel, fmt, len(runs), n_judged,
           "; %d forms the same bytes as their twins (--same-as)" % n_same if a.same_as else ""))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="crosscheck.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("compiled", help="the runners of the generated kernels")
    c.add_argument("--kernel", required=True)
    c.add_argument("--format", required=True)
    c.add_argument("--summary", required=True,
                   help="the summary's path, after which the others are named")
    c.add_argument("--seed")
    c.add_argument("--count")
    c.add_argument("--exhaustive", action="store_true")
    c.add_argument("--restrict", default="",
                   help="R1,R2,...: the oracle's restrictions, with --exhaustive")
    c.add_argument("--fail-on-suspicious", action="store_true")
    c.add_argument("--runner", nargs=2, action="append", metavar=("LABEL", "EXECUTABLE"))
    c.add_argument("--interp", action="store_true",
                   help="the generator's interpreter as a runner too")
    c.add_argument("--refrun", action="store_true",
                   help="the oracle's reference runner as a runner too (for rational_K: a test of "
                        "the driver and the guards)")
    c.add_argument("--orders", help="a fold: the orders of the requests (gen --orders)")
    c.add_argument("--max-length", help="a fold: the largest length (gen --max-length)")
    c.add_argument("--packed-runner", nargs=2, action="append", metavar=("LABEL", "EXECUTABLE"),
                   help="a fold: a runner of the packed form, which completes the lane order of "
                        "its register only, on requests of their own in that order")
    c.add_argument("--packed-lanes", help="a fold: W, the lanes of the packed runners' register")
    c.add_argument("--packed-count", help="a fold: the cases of the packed runners (default "
                                          "--count)")
    c.add_argument("--claims", help="the claims file of the oracle (default gen/claims.json)")
    p = sub.add_parser("api", help="the runners of the public interface, with their forms")
    p.add_argument("--kernel", required=True)
    p.add_argument("--format", required=True)
    p.add_argument("--seed", required=True)
    p.add_argument("--count", required=True)
    p.add_argument("--summary-dir", required=True)
    p.add_argument("--runner", nargs=2, action="append", metavar=("LABEL", "EXECUTABLE"))
    p.add_argument("--first-form", action="append", metavar="LABEL",
                   help="a runner that runs the kernel's first form only")
    p.add_argument("--same-as", nargs=2, action="append", metavar=("LABEL", "OTHER"),
                   help="every form of runner LABEL must write the same bytes as the same form of "
                        "runner OTHER")
    p.add_argument("--claims", help="the claims file of the oracle (default gen/claims.json)")
    a = ap.parse_args(argv)
    if a.mode == "compiled":
        if not a.exhaustive and (a.seed is None or a.count is None):
            ap.error("a random run needs --seed and --count")
        return compiled(a)
    return api(a)


if __name__ == "__main__":
    sys.exit(main())
