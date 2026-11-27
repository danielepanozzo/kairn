#!/usr/bin/env python3
"""The kernels of the round-up interval on every case of the formats of the statements of precision
1 to 4, through the generator's interpreter in both forms of max_nl, judged by the oracle: the gate of
the generator's suite of docs/developer/design/upward.md ("Tests and CI"), in pieces that run side by
side, resume and merge (docs/developer/testing.md, "The round-up interval"). The kernels it judges
require the rounding mode upward set by kairn::upward::Scope and the options of
docs/concepts/upward.md (GCC and Clang -frounding-math, MSVC /fp:strict); this driver runs the
generator's interpreter and the oracle, which need neither.

    python3 tests/brute/upward.py plan [--precision 1-4] [--kernels K,...] [--piece LINES]
    python3 tests/brute/upward.py run --work WORK --jobs N [--precision 1-4] [--kernels K,...]
                                      [--piece LINES] [--cpus LIST] [--nice N]
                                      [--commit SHA --driver-commit SHA]
    python3 tests/brute/upward.py status --work WORK
    python3 tests/brute/upward.py collect --work WORK --out FILE

The cases are those of gen/tests/test_upward.py (inputs(): every canonical state of each pair
input, the zeros of both signs among them; every canonical default interval of upward_from_interval_1;
every value of a number), in the formats of the statements fp:P:QMIN:QMAX of test_upward's QUICK,
FULL and FOUR (precision 1 and 2, 2 and 3, 4), each kernel in each form of max_nl it computes
(--max sel, MAXPD's; --max nm, FMAXNM's on quiet NaNs). A piece is the cases whose first operand
is one of a range of the first group's (about --piece lines, default 2 000 000): its lines, completed
by the interpreter in a worker process (test_upward.oracle_lines, the text of `kairn-gen interp
--max FORM`), go to a process of the oracle's `check --fail-on-suspicious --expect-valid`, which
writes the piece's summary. --jobs counts busy processes, two a piece. 5.3 billion lines at
precision 1 to 4, 5.2 billion of them at precision 4.

`run` writes WORK/run.json (the arguments and the commits; a later run in WORK must have the same
plan), a summary and a record per piece under WORK/pieces/, the oracle's report of each piece that
fails and WORK/findings.jsonl, WORK/run.log, and WORK/status.txt, rewritten after every piece
(pieces and lines done, the rate, the time left). It starts only the pieces without a record, so
the same command resumes a run that was stopped; it stops its pieces on SIGINT, SIGTERM and SIGHUP
(but a signal ignored when it starts, SIGHUP under nohup), and on Linux they also die with it if it
is killed. `status` prints WORK/status.txt again, from the
records. `collect` checks that every piece of the plan passed and that the pieces of each kernel,
format and form cover every case once, merges their summaries with the oracle (`check --merge`),
requires the merged counts to be the cases of the plan, every case judged, none failed, invalid or
suspicious, and every claim applied, and writes one JSON file of counts (for results/: the
commands, the commits, per kernel, format and form the cases and the oracle's counts of each
claim). It exits 1 on any problem. Python's standard library; Linux and macOS.
"""
import argparse
import glob
import json
import math
import os
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ORACLE = os.path.join(REPO, "oracle", "kairn-oracle")
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.path.insert(0, os.path.join(REPO, "gen", "tests"))

# The code under test (the kernels, their claims, the interpreter, the oracle) and the driver; as
# tests/brute/brute.py records them.
CODE_PATHS = ("include", "gen", "proofs", "oracle")
DRIVER_PATHS = ("tests/brute", "gen/tests/test_upward.py")


def test_upward():
    import test_upward as T
    return T


def formats_of(precision):
    """The formats of the statements of the precisions asked for (`1-4`, `4`, `1,2`)."""
    T = test_upward()
    want = set()
    for part in precision.split(","):
        lo, _, hi = part.partition("-")
        want |= set(range(int(lo), int(hi or lo) + 1))
    return [f for f in T.QUICK + T.FULL + T.FOUR if int(f.split(":")[1]) in want]


def plan_of(a):
    T = test_upward()
    names = a.kernels.split(",") if a.kernels else T.NAMES
    unknown = sorted(set(names) - set(T.NAMES))
    if unknown:
        sys.exit("upward: not kernels of the round-up interval: %s" % ", ".join(unknown))
    return [list(j) for j in T.oracle_jobs(names, formats_of(a.precision), a.piece)]


def piece_name(job):
    name, fmt, form, lo, hi = job[:5]
    return "%s.%s.%s.%06d-%06d" % (name, fmt.replace(":", "_"), form, lo, hi)


def key_name(key):
    return "%s.%s.%s" % (key[0], key[1].replace(":", "_"), key[2])


def git_commit(paths):
    try:
        out = subprocess.run(["git", "-C", REPO, "log", "-1", "--format=%H", "--"] + list(paths),
                             capture_output=True, text=True, timeout=30)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log(work, text):
    line = "%s %s" % (now(), text)
    print(line, flush=True)
    with open(os.path.join(work, "run.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


# --- A piece, in a worker ------------------------------------------------------------------------

def _worker_init(nice):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    if sys.platform.startswith("linux"):
        test_upward()._die_with_parent()
    if nice:
        try:
            os.nice(nice)
        except OSError:
            pass


def one_piece(args):
    """Judge a piece; write its summary and its record. The record is written last, so a piece
    with a record is done."""
    work, job = args
    T = test_upward()
    base = os.path.join(work, "pieces", piece_name(job))
    t0 = time.time()
    n, status, report = T.oracle_piece(job, base + ".summary.json")
    rec = {"job": job, "lines": n, "status": status, "seconds": round(time.time() - t0, 1),
           "finished": now()}
    if status != 0 or n != job[5]:
        with open(base + ".report.txt", "w", encoding="utf-8") as f:
            f.write(report)
    write_json(base + ".done.json", rec)
    return rec


# --- plan, run, status, collect ------------------------------------------------------------------

def cmd_plan(a):
    plan = plan_of(a)
    keys = {}
    for j in plan:
        k = tuple(j[:3])
        p, n = keys.get(k, (0, 0))
        keys[k] = (p + 1, n + j[5])
    for (name, fmt, form), (p, n) in keys.items():
        print("%-24s %-11s --max %-3s %13s lines, %4d pieces" % (name, fmt, form, "{:,}".format(n), p))
    print("%d kernels, formats and forms; %d pieces; %s lines"
          % (len(keys), len(plan), "{:,}".format(sum(j[5] for j in plan))))


STOP = []


def _on_signal(signum, _frame):
    STOP.append(signum)


def records(work):
    out = {}
    for path in glob.glob(os.path.join(work, "pieces", "*.done.json")):
        rec = read_json(path)
        out[piece_name(rec["job"])] = rec
    return out


def write_status(work, plan, recs, started, rate_window):
    total = sum(j[5] for j in plan)
    done = sum(r["lines"] for r in recs.values())
    failed = [n for n, r in recs.items() if r["status"] != 0 or r["lines"] != r["job"][5]]
    lines = ["the round-up interval judged by the oracle: %d of %d pieces, %s of %s lines (%.1f%%), "
             "%d failed" % (len(recs), len(plan), "{:,}".format(done), "{:,}".format(total),
                            100.0 * done / max(1, total), len(failed))]
    if rate_window:
        t, n = rate_window[-1][0] - rate_window[0][0], rate_window[-1][1] - rate_window[0][1]
        if t > 0 and n > 0:
            rate = n / t
            left = (total - done) / rate
            lines.append("%.0f lines/s over the last %.0f minutes; about %.1f h left (until about %s)"
                         % (rate, t / 60, left / 3600, time.strftime(
                             "%Y-%m-%dT%H:%MZ", time.gmtime(time.time() + left))))
    lines.append("started %s; updated %s; pid %d" % (started, now(), os.getpid()))
    for n in failed[:20]:
        lines.append("FAILED: %s (pieces/%s.report.txt)" % (n, n))
    if len(recs) == len(plan):
        lines.append("every piece is done: python3 tests/brute/upward.py collect --work %s --out FILE" % work)
    tmp = os.path.join(work, "status.txt.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, os.path.join(work, "status.txt"))


def cmd_run(a):
    work = os.path.abspath(a.work)
    os.makedirs(os.path.join(work, "pieces"), exist_ok=True)
    if a.cpus and sys.platform.startswith("linux"):
        ids = set()
        for part in a.cpus.split(","):
            lo, _, hi = part.partition("-")
            ids |= set(range(int(lo), int(hi or lo) + 1))
        os.sched_setaffinity(0, ids)
    code = a.commit or git_commit(CODE_PATHS)
    driver = a.driver_commit or git_commit(DRIVER_PATHS)
    if not code or not driver:
        sys.exit("upward: no git history to name the commits of the code under test and of the "
                 "driver: give --commit and --driver-commit")
    plan = plan_of(a)
    spec = {"precision": a.precision, "kernels": a.kernels or "", "piece": a.piece}
    path = os.path.join(work, "run.json")
    if os.path.exists(path):
        old = read_json(path)
        if old["spec"] != spec:
            sys.exit("upward: %s holds a run of another plan (%s)" % (work, old["spec"]))
        if (old["commit"], old["driver_commit"]) != (code, driver):
            sys.exit("upward: %s holds a run of the commits %s and %s, not %s and %s"
                     % (work, old["commit"], old["driver_commit"], code, driver))
        run = old
    else:
        run = {"spec": spec, "commit": code, "driver_commit": driver, "started": now(),
               "pieces": len(plan), "lines": sum(j[5] for j in plan),
               "command": "python3 tests/brute/upward.py run --precision %s%s --piece %d --jobs %d"
               % (a.precision, " --kernels " + a.kernels if a.kernels else "", a.piece, a.jobs),
               "python": sys.version.split()[0], "logical_cpus": os.cpu_count(), "jobs": a.jobs}
        write_json(path, run)
    recs = records(work)
    todo = [j for j in plan if piece_name(j) not in recs]
    log(work, "%d pieces, %d done, %d to run, %d workers (two busy processes each)"
        % (len(plan), len(recs), len(todo), max(1, a.jobs // 2)))
    for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        # A signal ignored when the run starts (SIGHUP under nohup) stays ignored.
        if signal.getsignal(s) != signal.SIG_IGN:
            signal.signal(s, _on_signal)
    import multiprocessing as mp
    pool = mp.get_context("fork" if sys.platform.startswith("linux") else "spawn").Pool(
        max(1, a.jobs // 2), initializer=_worker_init, initargs=(a.nice,))
    window = [(time.time(), sum(r["lines"] for r in recs.values()))]
    started = run["started"]
    write_status(work, plan, recs, started, None)
    try:
        for rec in pool.imap_unordered(one_piece, [(work, j) for j in todo]):
            recs[piece_name(rec["job"])] = rec
            if rec["status"] != 0 or rec["lines"] != rec["job"][5]:
                with open(os.path.join(work, "findings.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec) + "\n")
                log(work, "FAILED: %s (pieces/%s.report.txt)" % (piece_name(rec["job"]),
                                                                   piece_name(rec["job"])))
            window.append((time.time(), sum(r["lines"] for r in recs.values())))
            while len(window) > 2 and window[-1][0] - window[0][0] > 600:
                window.pop(0)
            write_status(work, plan, recs, started, window)
            if STOP:
                break
    finally:
        if STOP:
            log(work, "stopped by signal %s: its pieces run again next time" % STOP[0])
            pool.terminate()
        else:
            pool.close()
        pool.join()
    write_status(work, plan, records(work), started, window)
    failed = [r for r in recs.values() if r["status"] != 0]
    log(work, "%d of %d pieces done, %d failed" % (len(recs), len(plan), len(failed)))
    return 2 if STOP else (1 if failed else 0)


def cmd_status(a):
    work = os.path.abspath(a.work)
    run = read_json(os.path.join(work, "run.json"))
    ns = argparse.Namespace(precision=run["spec"]["precision"], kernels=run["spec"]["kernels"],
                            piece=run["spec"]["piece"])
    write_status(work, plan_of(ns), records(work), run["started"], None)
    with open(os.path.join(work, "status.txt"), encoding="utf-8") as f:
        sys.stdout.write(f.read())


def cmd_collect(a):
    work = os.path.abspath(a.work)
    run = read_json(os.path.join(work, "run.json"))
    ns = argparse.Namespace(precision=run["spec"]["precision"], kernels=run["spec"]["kernels"],
                            piece=run["spec"]["piece"])
    plan = plan_of(ns)
    recs = records(work)
    T = test_upward()
    problems = []
    by_key = {}
    for j in plan:
        by_key.setdefault(tuple(j[:3]), []).append(j)
    merged_dir = os.path.join(work, "merged")
    os.makedirs(merged_dir, exist_ok=True)
    out_runs = []
    seconds = 0.0
    for key, jobs in by_key.items():
        name, fmt, form = key
        first, rest = T.cases_of(name, fmt)
        want = first * rest
        # The pieces cover the first group's cases once, in order.
        ranges = sorted((j[3], j[4]) for j in jobs)
        if ranges[0][0] != 0 or ranges[-1][1] != first or any(
                b[0] != c[1] for c, b in zip(ranges, ranges[1:])):
            problems.append("%s: the pieces do not cover the first operand's %d cases" % (key_name(key), first))
        missing = [piece_name(j) for j in jobs if piece_name(j) not in recs]
        bad = [piece_name(j) for j in jobs if piece_name(j) in recs and (
            recs[piece_name(j)]["status"] != 0 or recs[piece_name(j)]["lines"] != j[5])]
        if missing:
            problems.append("%s: %d pieces not run (%s, ...)" % (key_name(key), len(missing), missing[0]))
        if bad:
            problems.append("%s: %d pieces failed (%s, ...)" % (key_name(key), len(bad), bad[0]))
        if missing or bad:
            continue
        seconds += sum(recs[piece_name(j)]["seconds"] for j in jobs)
        files = [os.path.join(work, "pieces", piece_name(j) + ".summary.json") for j in jobs]
        merged = os.path.join(merged_dir, key_name(key) + ".json")
        r = subprocess.run([sys.executable, ORACLE, "check", "--merge", "--quiet", "--json", merged] + files,
                           capture_output=True, text=True)
        if r.returncode != 0:
            problems.append("%s: the oracle's merge exits with %d: %s" % (key_name(key), r.returncode,
                                                                          (r.stdout + r.stderr)[-2000:]))
            continue
        s = read_json(merged)
        counts, entries = {}, {}
        for k in s.get("keys", []):
            if (k["kernel"], k["format"]) != (name, fmt):
                problems.append("%s: a key of %s %s in the summary" % (key_name(key), k["kernel"], k["format"]))
                continue
            for c, v in k["stats"]["counts"].items():
                counts[c] = counts.get(c, 0) + v
            for e in k["stats"]["entries"]:
                d = entries.setdefault(e["label"], {"kind": e["kind"], "applicable": 0, "failures": 0,
                                                    "counts": {}})
                d["applicable"] += e["applicable"]
                d["failures"] += e["failures"]
                for c, v in (e.get("counts") or {}).items():
                    d["counts"][c] = d["counts"].get(c, 0) + v
        why = []
        if counts.get("cases") != want or counts.get("judged") != want:
            why.append("%s cases and %s judged, not the %d of the plan" % (counts.get("cases"), counts.get("judged"), want))
        for c in ("failed", "invalid", "suspicious", "out_of_scope"):
            if counts.get(c):
                why.append("%d %s" % (counts[c], c))
        for e in ("stream_errors", "claims_errors"):
            if s.get(e):
                why.append("%s: %s" % (e, s[e][:3]))
        for label, e in entries.items():
            if not e["applicable"]:
                why.append("the claim %r applied to no case" % label)
        if why:
            problems.append("%s: %s" % (key_name(key), "; ".join(why)))
        out_runs.append({"kernel": name, "format": fmt, "max": form, "first": first, "rest": rest,
                         "pieces": len(jobs), "counts": counts, "entries": entries})
    doc = {"what": "the kernels of the round-up interval on every case of the formats of the statements "
                   "of precision %s, through the generator's interpreter in each form of max_nl, judged by "
                   "the oracle (tests/brute/upward.py)" % run["spec"]["precision"],
           "command": run["command"], "collect": "python3 tests/brute/upward.py collect",
           "commit": run["commit"], "driver_commit": run["driver_commit"], "started": run["started"],
           "collected": now(), "pieces": len(plan), "lines": sum(j[5] for j in plan),
           "process_seconds": round(seconds), "problems": problems, "runs": out_runs}
    write_json(os.path.abspath(a.out), doc)
    for p in problems:
        print("PROBLEM: " + p)
    print("upward: %d kernels, formats and forms, %s lines, %d problems; %s"
          % (len(out_runs), "{:,}".format(sum(r["counts"].get("cases", 0) for r in out_runs)), len(problems), a.out))
    return 1 if problems else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def planned(p):
        p.add_argument("--precision", default="1-4", help="precisions of the formats (default 1-4)")
        p.add_argument("--kernels", help="comma-separated kernels (default all 24)")
        p.add_argument("--piece", type=int, default=2_000_000, help="lines per piece (about)")
    p = sub.add_parser("plan")
    planned(p)
    r = sub.add_parser("run")
    planned(r)
    r.add_argument("--work", required=True)
    r.add_argument("--jobs", type=int, default=os.cpu_count() or 2, help="busy processes, two a piece")
    r.add_argument("--cpus", help="Linux: the CPUs to run on (0-31,64-95)")
    r.add_argument("--nice", type=int, default=0)
    r.add_argument("--commit", help="the commit of the code under test (default: from git)")
    r.add_argument("--driver-commit", help="the commit of this driver (default: from git)")
    s = sub.add_parser("status")
    s.add_argument("--work", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--work", required=True)
    c.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    return {"plan": cmd_plan, "run": cmd_run, "status": cmd_status, "collect": cmd_collect}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main() or 0)
