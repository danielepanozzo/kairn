"""Command line of kairn-oracle."""

import argparse
import os
import sys

from . import fmt as F
from .claims import load_claims, ClaimsError

ORACLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(ORACLE_DIR)


def default_claims():
    return os.path.join(REPO_DIR, "gen", "claims.json")


def _claims(path):
    path = path or default_claims()
    try:
        return load_claims(path)
    except ClaimsError as ex:
        print("kairn-oracle: %s" % ex, file=sys.stderr)
        if not os.path.exists(path):
            print("kairn-oracle: pass --claims FILE (the selftest fixture is "
                  "oracle/selftest/claims-wave1.json)", file=sys.stderr)
        sys.exit(2)


def _format(name):
    try:
        return F.parse_format(name)
    except F.FormatError as ex:
        print("kairn-oracle: %s" % ex, file=sys.stderr)
        sys.exit(2)


def cmd_gen(a):
    from . import gen as G
    claims = _claims(a.claims)
    kernel = claims.get(a.kernel)
    if kernel is None:
        print("kairn-oracle gen: %s" % claims.broken.get(
            a.kernel, "no claims for kernel %r in %s" % (a.kernel, claims.path)), file=sys.stderr)
        return 2
    fmt = _format(a.format)
    try:
        if a.exhaustive:
            g = G.ExhaustiveGen(kernel, fmt, a.restrict or (), index_tags=not a.no_index)
            if a.total:
                print("%d enumeration indices for %s %s (restrictions: %s; coupled requirements "
                      "skipped: %s)" % (g.total, kernel.name, fmt.name, g.restrict_text,
                                        "abs_ge" if g.coupled else "none"))
                return 0
            count = g.total - a.start if a.count is None else a.count
            G.write_lines(g.lines(a.start, count))
        else:
            if a.restrict:
                print("kairn-oracle gen: --restrict applies to --exhaustive only", file=sys.stderr)
                return 2
            strata = a.strata.split(",") if a.strata else None
            g = G.RandomGen(kernel, fmt, a.seed, strata, index_tags=not a.no_index)
            G.write_lines(g.lines(a.start, 1000 if a.count is None else a.count))
    except G.GenError as ex:
        print("kairn-oracle gen: %s" % ex, file=sys.stderr)
        return 2
    except BrokenPipeError:
        _quiet_pipe()
        return 0
    sys.stdout.flush()
    return 0


def _quiet_pipe():
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
    except OSError:
        pass


def _open_inputs(files):
    if not files or files == ["-"]:
        yield sys.stdin
        return
    for f in files:
        if f == "-":
            yield sys.stdin
        else:
            with open(f, "r", encoding="utf-8") as fh:
                yield fh


def cmd_check(a):
    from . import check as C
    if a.merge:
        s = C.Summary(a.max_examples)
        for f in a.files:
            try:
                s.merge(C.load_summary(f, a.max_examples))
            except (OSError, ValueError, KeyError) as ex:
                print("kairn-oracle check: cannot read summary %s: %s" % (f, ex), file=sys.stderr)
                return 2
    else:
        claims = _claims(a.claims)
        ck = C.Checker(claims, a.ignore_min_precision, a.max_examples)
        try:
            for fh in ([] if a.claims_only else _open_inputs(a.files)):
                ck.feed(fh)
        except ClaimsError as ex:
            print("kairn-oracle check: %s" % ex, file=sys.stderr)
            return 2
        s = ck.finish()
    if a.json:
        C.write_summary(s, a.json)
    if not a.quiet:
        C.report(s, far=a.far, fail_on_suspicious=a.fail_on_suspicious,
                 expect_valid=a.expect_valid, verbose=a.verbose)
    return 1 if s.failed(a.fail_on_suspicious, a.expect_valid) else 0


def cmd_refrun(a):
    from . import refrun
    return refrun.main(a.rest)


def cmd_selftest(a):
    from . import selftest
    return selftest.main(a)


def cmd_brute(a):
    from . import brute
    return brute.main(a)


def cmd_search(a):
    from . import search
    return search.main(a)


def cmd_shrink(a):
    from . import shrink
    return shrink.main(a)


def add_runner_options(p):
    p.add_argument("--runner", default="interp",
                   help="the runner: 'interp' (the generator's interpreter, the default), "
                        "'refrun[:VARIANT]' (the oracle's reference runner, in this process), or "
                        "any shell command of the line protocol")
    p.add_argument("--radius", default="first", choices=("first", "second"),
                   help="with --runner refrun: the Ball cores' radius design (default first)")
    p.add_argument("--claims", help="claims file (default: gen/claims.json of this repository)")
    p.add_argument("--fail-on-suspicious", action="store_true",
                   help="a suspicious non-finite result is a failure, as in the cross-checks")


def add_check_options(p):
    p.add_argument("--max-examples", type=int, default=5,
                   help="failing, invalid and suspicious cases kept per key (default 5)")
    p.add_argument("--far", type=int, default=None,
                   help="observed constant (a) is taken over cases with u^k rho >= 2^FAR eta "
                        "(default: the precision p)")
    p.add_argument("--ignore-min-precision", action="store_true",
                   help="judge formats whose precision is below a kernel's min_precision")
    p.add_argument("--fail-on-suspicious", action="store_true",
                   help="count suspicious non-finite results as failures")
    p.add_argument("--expect-valid", action="store_true",
                   help="count invalid cases as failures (to test a generator)")
    p.add_argument("--verbose", action="store_true", help="print the profile of (a) by distance")
    p.add_argument("--quiet", action="store_true", help="no report, only the exit status")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["refrun"]:
        # argparse cannot hand options that start with -- to a subcommand untouched.
        from . import refrun
        return refrun.main(argv[1:])
    ap = argparse.ArgumentParser(prog="kairn-oracle",
                                 description="Kairn's test oracle: exact arithmetic, no code shared "
                                             "with the library or its generator.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gen", help="write request lines")
    g.add_argument("kernel")
    g.add_argument("format", help="binary64, binary32 or fp:P:QMIN:QMAX")
    g.add_argument("--claims", help="claims file (default: gen/claims.json of this repository)")
    g.add_argument("--seed", default="0")
    g.add_argument("--start", type=int, default=0, help="first case index (default 0)")
    g.add_argument("--count", type=int, default=None,
                   help="number of cases (random default 1000; exhaustive default all)")
    g.add_argument("--strata", help="comma-separated strata (default all)")
    g.add_argument("--exhaustive", action="store_true", help="enumerate every operand combination")
    g.add_argument("--restrict", action="append",
                   help="exhaustive only: NAME.lead=LO:HI or NAME.sign=+|- (repeatable)")
    g.add_argument("--total", action="store_true", help="exhaustive: print the size and stop")
    g.add_argument("--no-index", action="store_true", help="tags without the case index")
    g.set_defaults(func=cmd_gen)

    c = sub.add_parser("check", help="judge completed lines")
    c.add_argument("files", nargs="*", help="completed lines (default stdin); with --merge, summaries")
    c.add_argument("--claims")
    c.add_argument("--json", help="write a machine-readable summary to this file")
    c.add_argument("--merge", action="store_true", help="merge JSON summaries instead of reading lines")
    c.add_argument("--claims-only", action="store_true",
                   help="read no lines: only validate the claims file (exit 1 if a kernel is unreadable)")
    add_check_options(c)
    c.set_defaults(func=cmd_check)

    r = sub.add_parser("refrun", help="the reference runner (pure Python)", add_help=False)
    r.add_argument("rest", nargs=argparse.REMAINDER)
    r.set_defaults(func=cmd_refrun)

    s = sub.add_parser("selftest", help="the oracle's own tests")
    s.add_argument("--quick", action="store_true", help="smaller samples")
    s.add_argument("--keep", action="store_true", help="keep the work directory")
    s.add_argument("--workdir", help="where to build the C++ runner and write streams")
    s.add_argument("--cxx", help="C++ compiler (default: $CXX, then c++, clang++, g++)")
    s.add_argument("--only", help="comma-separated test names")
    s.add_argument("--skip", help="comma-separated test names to leave out")
    s.add_argument("--jobs", type=int, default=None,
                   help="worker processes of the exhaustive tests (default: $KAIRN_ORACLE_JOBS, "
                        "then the number of CPUs)")
    s.set_defaults(func=cmd_selftest)

    b = sub.add_parser("brute", help="run gen | RUNNER | check pipelines in parallel")
    b.add_argument("--runner", required=True,
                   help="shell command of the runner, or 'refrun[:VARIANT]' to run the reference "
                        "runner in-process")
    b.add_argument("--kernels", required=True, help="comma-separated")
    b.add_argument("--formats", required=True, help="comma-separated")
    b.add_argument("--claims")
    b.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    b.add_argument("--budget", type=float, help="seconds: no new chunk starts after this")
    b.add_argument("--cases", type=int, help="random cases per (kernel, format)")
    b.add_argument("--chunk", type=int, default=20000, help="cases per pipeline (default 20000)")
    b.add_argument("--seed", default="0")
    b.add_argument("--strata")
    b.add_argument("--exhaustive", action="store_true")
    b.add_argument("--restrict", action="append")
    b.add_argument("--radius", default="first", choices=("first", "second"),
                   help="with --runner refrun: the Ball cores' radius design (default first)")
    b.add_argument("--json", help="write the merged summary here")
    b.add_argument("--workdir", help="where chunk summaries go (default: a temporary directory)")
    add_check_options(b)
    b.set_defaults(func=cmd_brute)

    s = sub.add_parser("search", help="search for the cases closest to the claims, or past them")
    s.add_argument("kernels", help="comma-separated, or 'all': every kernel with an error, upper, "
                                   "encloses or extends entry")
    s.add_argument("formats", help="comma-separated")
    add_runner_options(s)
    s.add_argument("--seed", default="0")
    s.add_argument("--evals", type=int, default=20000,
                   help="cases run per kernel and format, seeds included (default 20000)")
    s.add_argument("--batch", type=int, default=256,
                   help="cases per generation and per runner process (default 256)")
    s.add_argument("--elite", type=int, default=16, help="cases kept per quantity (default 16)")
    s.add_argument("--seeds", action="append",
                   help="more seed lines: a text file of lines or a JSON summary (repeatable)")
    s.add_argument("--no-default-seeds", action="store_true",
                   help="without the lines of results/*/brute/ and tests/regression/cases.txt")
    s.add_argument("--no-literature", action="store_true",
                   help="without the cases of the literature (tight.py)")
    s.add_argument("--suspicious-ok", metavar="KERNELS",
                   help="with --fail-on-suspicious: kernels whose suspicious results are not "
                        "failures (the cross-checks exempt split,two_prod_dekker)")
    s.add_argument("--jobs", type=int, default=1, help="kernel and format pairs at once")
    s.add_argument("--json", help="write the results here")
    s.add_argument("--quiet", action="store_true",
                   help="only the last line, and the pairs that failed")
    s.set_defaults(func=cmd_search)

    k = sub.add_parser("shrink", help="shrink a failing case")
    k.add_argument("line", help="the failing line (a request or a completed line; '-' to read "
                                "it from standard input)")
    add_runner_options(k)
    k.add_argument("--entry", help="the failure to keep, as shrink lists them (default: the first)")
    k.add_argument("--evals", type=int, default=50000,
                   help="cases run at most, toy formats included (default 50000)")
    k.add_argument("--no-toy", action="store_true", help="do not look for a smaller format")
    k.add_argument("--toy-cases", type=int, default=2000,
                   help="random cases tried in a toy format whose enumeration is larger "
                        "(default 2000)")
    k.add_argument("--json", help="write the result here")
    k.set_defaults(func=cmd_shrink)

    a = ap.parse_args(argv)
    return a.func(a)
