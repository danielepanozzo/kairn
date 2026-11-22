#!/usr/bin/env python3
"""The loops over arrays of a brute-force run, by the length of their arrays.

    python3 tests/brute/lengths.py --runner PATH --seed SEED --cases N --out FILE [--jobs J]
        [--folds LIST] [--formats binary64,binary32] [--machine NAME]

The oracle keeps the largest error over its bound of a fold over every array it judged, and the
count of arrays per length, but not the largest error per length. This runs again the first N
random arrays of the scalar stream of each fold and format of a run (seed SEED, from case 0, the
fold's largest length as the compiled part has it: brute.fold_length), through one runner
(`interp` for the generator's interpreter), sorts the completed lines by the oracle's length class
(kairn_oracle.folds.length_class: the length of the arrays, for a convolution the terms of its
coefficients, the shorter of the two lengths), and has the oracle judge each class apart. The
cases are those of the run: case i depends on the fold, the format, the seed, the orders and the
largest length alone. FILE gets, per fold, format and class, the lines, the oracle's counts and
each entry's statistics (as brute.py collect keeps them), with the line that attains each.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brute  # noqa: E402

sys.path.insert(0, os.path.join(brute.REPO, "oracle"))
from kairn_oracle import folds as oracle_folds  # noqa: E402


def length_of(line):
    """The oracle's length class of a request or completed line of a fold."""
    w = line.split()
    if w[0] in CONV:
        return oracle_folds.length_class(min(int(w[3]), int(w[4])))
    return oracle_folds.length_class(int(w[3]))


CONV = set()


def split(text):
    """(header lines, {class: [lines]}) of a runner's output: the generator's header kept for every
    class, its trailer dropped (each class gets its own)."""
    head, groups = [], {}
    for line in text.splitlines(keepends=True):
        if line.startswith("#"):
            if "event=begin" in line:
                head.append(line)
            continue
        if line.strip():
            groups.setdefault(length_of(line), []).append(line)
    return head, groups


def judge(head, lines, fold, fmt):
    """The oracle's check of one class of lines, as collect keeps it."""
    trailer = "# kairn-oracle gen event=end lines=%d\n" % len(lines)
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        cmd = [brute.PY, brute.ORACLE, "check", "--json", path, "--quiet"]
        if brute.fails_on_suspicious(fold, fmt):
            cmd.append("--fail-on-suspicious")
        p = subprocess.run(cmd, input="".join(head + lines) + trailer, capture_output=True,
                           text=True, cwd=brute.REPO)
        s = brute.read_json(path)
    finally:
        os.remove(path)
    keys = [k for k in s["keys"] if (k["kernel"], k["format"]) == (fold, fmt)]
    why, examples, _ = brute.summary_problems(s, brute.fails_on_suspicious(fold, fmt))
    return {"lines": len(lines), "counts": brute.key_counts(keys),
            "entries": brute.entry_stats(keys, keys[0]["stats"]["p"]) if keys else [],
            "problems": why, "examples": examples, "check_status": p.returncode}


def one(fold, fmt, a):
    gen = [brute.PY, brute.ORACLE, "gen", fold, fmt, "--seed", a.seed, "--start", "0",
           "--count", str(a.cases), "--max-length", str(brute.fold_length(fold))]
    req = subprocess.run(gen, capture_output=True, text=True, cwd=brute.REPO, check=True).stdout
    runner = [brute.PY, brute.KAIRN_GEN, "interp"] if a.runner == "interp" else [a.runner]
    out = subprocess.run(runner, input=req, capture_output=True, text=True, cwd=brute.REPO)
    if out.returncode != 0:
        return fold, fmt, {"error": "runner exited with %d: %s" % (out.returncode, out.stderr[-500:])}
    head, groups = split(out.stdout)
    res = {c: judge(head, groups[c], fold, fmt) for c in sorted(groups, key=class_key)}
    return fold, fmt, res


def class_key(c):
    """Length classes in order: 'length 3' < 'length 18 to 64' < 'length above 4096'."""
    nums = [int(t) for t in c.split() if t.isdigit()]
    return (nums[0] + (1 if "above" in c else 0)) if nums else 1 << 30


GROUPS = [("0 to 1", 0, 1), ("2 to 17", 2, 17), ("18 to 64", 18, 64), ("65 to 256", 65, 256),
          ("257 to 1 024", 257, 1024), ("1 025 to 4 096", 1025, 4096)]


def class_range(c):
    """(lo, hi) of a length class of the oracle."""
    nums = [int(t) for t in c.split() if t.isdigit()]
    if "above" in c:
        return nums[0] + 1, 1 << 62
    return (nums[0], nums[-1]) if nums else (0, 0)


def table(doc):
    """Markdown: per loop and format, the statistic of its first claim that has one (as report
    reads it: brute.entry_headlines), the closest over each group of lengths, and the lines."""
    out = ["| Loop | Format | Quantity | " + " | ".join("length " + g[0] for g in GROUPS) + " | Arrays |",
           "|---|---|---|" + "---|" * (len(GROUPS) + 1)]
    for fold in sorted(doc["folds"]):
        for fmt, res in sorted(doc["folds"][fold].items()):
            if res.get("error"):
                out.append("| `%s` | `%s` | %s |" % (fold, fmt, res["error"]))
                continue
            # Every claim with a statistic in some class, in the order of the claims; for each,
            # the statistics of the class that holds the most of them.
            heads = {}
            for c in res.values():
                for e in c["entries"]:
                    h = brute.entry_headlines(e)
                    if len(h) > len(heads.get(e["label"], [])):
                        heads[e["label"]] = h
            order = [e["label"] for c in res.values() for e in c["entries"]]
            for label in sorted(heads, key=order.index):
                for _, title, field, name, sign in heads[label]:
                    rows_of(out, res, fold, fmt, label, title, field, name, sign)
    return "\n".join(out)


def rows_of(out, res, fold, fmt, label, title, field, name, sign):
    """One row of the table: the closest value of one statistic over each group of lengths."""
    cells = []
    for _, lo, hi in GROUPS:
        best = None
        for c, r in res.items():
            a, b = class_range(c)
            if b < lo or a > hi:
                continue
            e = next((x for x in r["entries"] if x["label"] == label), None)
            v = e and brute.col_value(e, field, name)
            if v and (best is None or
                      sign * (brute.decimal.Decimal(v[0]) - brute.decimal.Decimal(best[0])) > 0):
                best = v
        cells.append(brute.short(best[0]) if best else "-")
    out.append("| `%s` | `%s` | %s | %s | %s |" % (
        fold, fmt, title, " | ".join(cells), brute.fmt_int(sum(r["lines"] for r in res.values()))))


def main(argv=None):
    if argv is None and len(sys.argv) > 2 and sys.argv[1] == "table":
        print(table(brute.read_json(sys.argv[2])))
        return 0
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--runner", required=True, help="a runner of the line protocol, or interp")
    ap.add_argument("--seed", required=True)
    ap.add_argument("--cases", type=int, required=True, help="arrays per fold and format, from case 0")
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--folds", help="comma-separated (default: every fold the oracle judges)")
    ap.add_argument("--formats", default="binary64,binary32")
    ap.add_argument("--machine", default="")
    a = ap.parse_args(argv)
    folds = brute.load_folds()
    CONV.update(f["name"] for f in folds if f.get("conv") or f.get("bv_conv"))
    names = [f["name"] for f in folds]
    if a.folds:
        want = a.folds.split(",")
        unknown = [n for n in want if n not in names]
        if unknown:
            sys.exit("lengths: not folds of the claims: %s" % ", ".join(unknown))
        names = want
    tasks = [(n, f) for n in names for f in a.formats.split(",")]
    out = {"kairn_brute_lengths": 1, "seed": a.seed, "cases": a.cases, "machine": a.machine,
           "runner": os.path.basename(a.runner), "driver_sha256": brute.file_sha256(brute.__file__),
           "folds": {}}
    with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        for fold, fmt, res in ex.map(lambda t: one(t[0], t[1], a), tasks):
            out["folds"].setdefault(fold, {})[fmt] = res
            bad = res.get("error") or any(c["problems"] for c in res.values())
            brute.log("%s %s: %s" % (fold, fmt, "PROBLEM" if bad else "%d classes" % len(res)))
    brute.write_json(a.out, out, compact=True)
    bad = [(f, m) for f, ms in out["folds"].items() for m, r in ms.items()
           if r.get("error") or any(c["problems"] for c in r.values())]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
