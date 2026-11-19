"""brute: many `gen | RUNNER | check` pipelines in parallel, statistics merged.

The runner is any shell command.  `refrun[:VARIANT]` instead runs the reference runner
inside the worker process, with the same gen and check code on the same text lines, which
removes two pipes per case; it is what the exhaustive toy-format runs use.
"""

import concurrent.futures as cf
import itertools
import os
import subprocess
import sys
import tempfile
import time

from . import check as C
from .claims import load_claims, ClaimsError

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kairn-oracle")


def _gen_args(t):
    args = ["gen", t["kernel"], t["format"], "--claims", t["claims"], "--start", str(t["start"]),
            "--count", str(t["count"])]
    if t["exhaustive"]:
        args.append("--exhaustive")
        for r in t["restrict"]:
            args += ["--restrict", r]
    else:
        args += ["--seed", t["seed"]]
        if t["strata"]:
            args += ["--strata", t["strata"]]
    return args


def run_external(t):
    """One chunk through three processes; returns the summary as JSON data."""
    py = sys.executable
    out = os.path.join(t["workdir"], "chunk-%s-%s-%d.json" % (
        t["kernel"], t["format"].replace(":", "_"), t["start"]))
    chk = [py, SCRIPT, "check", "--claims", t["claims"], "--json", out, "--quiet",
           "--max-examples", str(t["max_examples"])]
    if t["ignore_min_precision"]:
        chk.append("--ignore-min-precision")
    g = subprocess.Popen([py, SCRIPT] + _gen_args(t), stdout=subprocess.PIPE)
    r = subprocess.Popen(t["runner"], shell=True, stdin=g.stdout, stdout=subprocess.PIPE)
    g.stdout.close()
    c = subprocess.Popen(chk, stdin=r.stdout)
    r.stdout.close()
    rc_c = c.wait()
    rc_r = r.wait()
    rc_g = g.wait()
    errors = []
    if rc_g != 0:
        errors.append("gen exited with %d" % rc_g)
    if rc_r != 0:
        errors.append("runner exited with %d" % rc_r)
    if rc_c not in (0, 1):
        errors.append("check exited with %d" % rc_c)
    try:
        data = C.load_summary(out, t["max_examples"]).to_json()
    except (OSError, ValueError) as ex:
        data = C.Summary().to_json()
        errors.append("no summary from check: %s" % ex)
    data["stream_errors"] = data.get("stream_errors", []) + [
        "%s %s chunk at %d: %s" % (t["kernel"], t["format"], t["start"], e) for e in errors]
    return data


def run_inprocess(t):
    from . import fmt as F
    from . import gen as G
    from . import refrun
    claims = load_claims(t["claims"])
    kernel = claims.get(t["kernel"])
    f = F.parse_format(t["format"])
    if t["exhaustive"]:
        g = G.ExhaustiveGen(kernel, f, t["restrict"])
    else:
        g = G.RandomGen(kernel, f, t["seed"], t["strata"].split(",") if t["strata"] else None)
    run = refrun.Runner(t["variant"], radius=t.get("radius") or "first")
    ck = C.Checker(claims, t["ignore_min_precision"], t["max_examples"])
    line = ck.line
    complete = run.complete
    for req in g.lines(t["start"], t["count"]):
        for done in complete(req):
            line(done)
    return ck.finish().to_json()


def main(a):
    claims_path = a.claims or os.path.join(os.path.dirname(os.path.dirname(SCRIPT)), "gen",
                                           "claims.json")
    try:
        claims = load_claims(claims_path)
    except ClaimsError as ex:
        print("kairn-oracle brute: %s" % ex, file=sys.stderr)
        return 2
    kernels = a.kernels.split(",")
    formats = a.formats.split(",")
    for k in kernels:
        if claims.get(k) is None:
            print("kairn-oracle brute: %s" % claims.broken.get(k, "no claims for %r" % k),
                  file=sys.stderr)
            return 2
    inproc = a.runner == "refrun" or a.runner.startswith("refrun:")
    variant = a.runner.split(":", 1)[1] if ":" in a.runner and inproc else "correct"
    if a.budget is None and a.cases is None and not a.exhaustive:
        print("kairn-oracle brute: give --budget, --cases or --exhaustive", file=sys.stderr)
        return 2
    workdir = a.workdir
    if not inproc:
        workdir = workdir or tempfile.mkdtemp(prefix="kairn-brute-")
        os.makedirs(workdir, exist_ok=True)
    base = {"claims": claims_path, "runner": a.runner, "variant": variant, "seed": a.seed,
            "strata": a.strata, "exhaustive": a.exhaustive, "restrict": a.restrict or [],
            "workdir": workdir, "max_examples": a.max_examples,
            "ignore_min_precision": a.ignore_min_precision, "radius": a.radius}

    def chunks():
        if a.exhaustive:
            from . import fmt as F
            from . import gen as G
            for k in kernels:
                for fname in formats:
                    total = G.ExhaustiveGen(claims.get(k), F.parse_format(fname),
                                            a.restrict or []).total
                    for s in range(0, total, a.chunk):
                        yield dict(base, kernel=k, format=fname, start=s,
                                   count=min(a.chunk, total - s))
            return
        pairs = [(k, f) for k in kernels for f in formats]
        limit = a.cases
        for c in itertools.count():
            s = c * a.chunk
            if limit is not None and s >= limit:
                return
            n = a.chunk if limit is None else min(a.chunk, limit - s)
            for k, f in pairs:
                yield dict(base, kernel=k, format=f, start=s, count=n)

    if a.exhaustive:
        # A restriction that does not fit a kernel or a format is a usage error, reported
        # before any chunk starts.
        from . import fmt as F
        from . import gen as G
        for k in kernels:
            for fname in formats:
                try:
                    G.ExhaustiveGen(claims.get(k), F.parse_format(fname), a.restrict or [])
                except (G.GenError, F.FormatError) as ex:
                    print("kairn-oracle brute: %s %s: %s" % (k, fname, ex), file=sys.stderr)
                    return 2
    run = run_inprocess if inproc else run_external
    Executor = cf.ProcessPoolExecutor if inproc else cf.ThreadPoolExecutor
    summary = C.Summary(a.max_examples)
    t0 = time.time()
    deadline = t0 + a.budget if a.budget is not None else None
    it = chunks()
    done_chunks = 0
    with Executor(max_workers=a.jobs) as ex:
        pending = set()

        def submit():
            if deadline is not None and time.time() >= deadline:
                return False
            t = next(it, None)
            if t is None:
                return False
            pending.add(ex.submit(run, t))
            return True

        for _ in range(a.jobs):
            if not submit():
                break
        while pending:
            fin, _ = cf.wait(pending, return_when=cf.FIRST_COMPLETED)
            for fu in fin:
                pending.discard(fu)
                summary.merge(C.Summary.from_json(fu.result(), a.max_examples))
                done_chunks += 1
                submit()
    wall = time.time() - t0
    if a.json:
        C.write_summary(summary, a.json)
    if not a.quiet:
        C.report(summary, far=a.far, fail_on_suspicious=a.fail_on_suspicious,
                 expect_valid=a.expect_valid, verbose=a.verbose)
        n = summary.totals()["cases"]
        print()
        print("brute: %d chunks, %d cases in %.1f s with %d jobs: %.0f cases/s, %.0f cases/s per job"
              % (done_chunks, n, wall, a.jobs, n / wall if wall else 0,
                 n / wall / a.jobs if wall else 0))
        if not a.workdir and not inproc:
            print("brute: chunk summaries in %s" % workdir)
    return 1 if summary.failed(a.fail_on_suspicious, a.expect_valid) else 0
