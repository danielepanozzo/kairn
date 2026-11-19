"""What a cross-check must have checked, beyond the oracle's verdict (tests/crosscheck.cmake).

    python3 tests/crosscheck_guards.py SUMMARY --kernel K --format F
        (--exhaustive [--restrict R1,R2,...] | --count N --seed S)

SUMMARY is the oracle's summary of the run (check --json). The oracle has already passed the
run: no claim violated, no invalid case, no broken stream. This fails, with the reason, when the
run did not check what it set out to check:

- the stream is not the one asked for: one generator header, for this kernel, format and mode
  (and seed), whose indices were all seen, from 0 to the end;
- an exhaustive run did not cover its whole enumeration, or its domain is not the one asked for:
  every operand when no restriction is given, exactly the restrictions given otherwise;
- a random run has no case of a stratum that the oracle's generator lists in its header for this
  kernel (the strata of the kernel's family), or a case of a stratum it does not list, or the
  list lacks a stratum that every family has;
- no case was judged, or an ensures entry of the kernel applied to no judged case; a comparison
  (predicate) did not see both outcomes; a rounding to nearest saw only exact cases; a rounding
  down or up never differed from the rounding to nearest.

Otherwise it prints one line saying what was checked. Python's standard library only, and
nothing from the oracle but the format of its summary (oracle/README.md, "Statistics").
"""
import argparse
import json
import sys

# The strata of every family of the oracle's generator (oracle/README.md, "gen").
COMMON_STRATA = ("uniform", "underflow", "overflow", "zero", "pow2", "extreme")


def problems(summary, a):
    what = "%s %s" % (a.kernel, a.format)
    cov = summary.get("coverage", [])
    if len(cov) != 1:
        yield "the oracle saw %d generator headers, not one" % len(cov)
        return
    desc, ranges = cov[0]["desc"], cov[0]["ranges"]
    mode = "exhaustive" if a.exhaustive else "random"
    got = (desc.get("kernel"), desc.get("format"), desc.get("mode"))
    if got != (a.kernel, a.format, mode):
        yield "the stream is of %s %s in mode %s, not of %s in mode %s" % (got + (what, mode))
        return
    if a.exhaustive:
        total = int(desc.get("total", -1))
        restrict = a.restrict or "none"
        if ranges != [[0, total]]:
            yield "the enumeration of %d cases was not covered (indices seen: %s)" % (total, ranges)
        if desc.get("restrict") != restrict:
            yield ("the enumeration was over the domain restricted by %r, not by %r"
                   % (desc.get("restrict"), restrict))
        strata = ["exhaustive"]
    else:
        if desc.get("seed") != a.seed or ranges != [[0, a.count]]:
            yield ("the stream is indices %s of seed %s, not cases 0 to %d of seed %s"
                   % (ranges, desc.get("seed"), a.count, a.seed))
        strata = [s for s in desc.get("strata", "").split(",") if s]
        for s in COMMON_STRATA:
            if s not in strata:
                yield ("the oracle's generator lists the strata %s, without %s, which every "
                       "family of kernels has" % (",".join(strata), s))

    keys = [k for k in summary.get("keys", [])
            if (k["kernel"], k["format"]) == (a.kernel, a.format)]
    if len(keys) != len(summary.get("keys", [])):
        yield "the summary has lines of other kernels or formats"
    tags = {k["tag"] for k in keys}
    for s in strata:
        if s in tags:
            continue
        if a.exhaustive:
            yield "no line tagged exhaustive"
        else:
            yield ("no case of stratum %s in %d cases, although the oracle's generator lists it "
                   "for %s" % (s, a.count, a.kernel))
    for t in sorted(tags - set(strata)):
        yield "lines tagged %s, which the generator's header does not list" % t

    judged = sum(k["stats"]["counts"]["judged"] for k in keys)
    if judged == 0:
        yield ("the oracle passed it, but judged no case (every result non-finite or out of "
               "scope), so nothing was checked")
        return
    entries = keys[0]["stats"]["entries"]
    for j, e in enumerate(entries):
        applicable = 0
        counts = {}
        for k in keys:
            ke = k["stats"]["entries"][j]
            if ke["label"] != e["label"]:
                yield "the entries of the claims differ between tags"
                return
            applicable += ke["applicable"]
            for name, n in ke.get("counts", {}).items():
                counts[name] = counts.get(name, 0) + n
        label = e["label"]
        if applicable == 0:
            yield 'the claim "%s" applied to no judged case, so it was not checked' % label
        elif e["kind"] == "predicate":
            for outcome in ("true", "false"):
                if not counts.get(outcome):
                    yield ('the claim "%s" was never %s, so the comparison was not checked both '
                           'ways' % (label, outcome))
        elif e["kind"] == "rounded" and "nearest" in label:
            if not counts.get("inexact") and not counts.get("tie"):
                yield 'the claim "%s" saw only exact cases' % label
        elif e["kind"] == "rounded":
            if not counts.get("inexact, != RN"):
                yield ('the claim "%s" never differed from the rounding to nearest, so the '
                       'direction was not checked' % label)


def describe(summary, a):
    desc = summary["coverage"][0]["desc"]
    judged = sum(k["stats"]["counts"]["judged"] for k in summary["keys"])
    if a.exhaustive:
        if a.restrict:
            what = "every operand of a RESTRICTED domain (%s), %s cases" % (a.restrict, desc["total"])
        else:
            what = "every operand, %s cases" % desc["total"]
    else:
        what = "%d random cases, seed %s, strata %s" % (a.count, a.seed, desc["strata"])
    return "%d cases judged (%s)" % (judged, what)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("summary")
    p.add_argument("--kernel", required=True)
    p.add_argument("--format", required=True)
    p.add_argument("--exhaustive", action="store_true")
    p.add_argument("--restrict", default="")
    p.add_argument("--count", type=int)
    p.add_argument("--seed")
    a = p.parse_args()
    if not a.exhaustive and (a.count is None or a.seed is None):
        p.error("a random run needs --count and --seed")
    try:
        with open(a.summary, encoding="utf-8") as f:
            summary = json.load(f)
    except (OSError, ValueError) as ex:
        print("cannot read the oracle's summary %s: %s" % (a.summary, ex))
        return 1
    found = list(problems(summary, a))
    if found:
        for why in found:
            print(why)
        return 1
    print(describe(summary, a))
    return 0


if __name__ == "__main__":
    sys.exit(main())
