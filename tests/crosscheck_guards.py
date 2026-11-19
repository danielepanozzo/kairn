"""What a cross-check must have checked, beyond the oracle's verdict (tests/crosscheck.cmake).

    python3 tests/crosscheck_guards.py SUMMARY --kernel K --format F
        (--exhaustive [--restrict R1,R2,...] | --count N --seed S) [--claims FILE]

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

For a kernel of the extended domain (the non-finite layer, "domain": "extended" in its claims),
also when the run did not see what that layer is about:

- a random run's header lacks a stratum that the oracle's generator adds for the layer
  (oracle/README.md, "gen"): nonfinite for every kernel, zeroinf where the value or the set has
  a product, edge for extends, threshold where finite_when is not empty, ballstates, zerowhole
  and hugeradius for encloses, badradius for makes_ball;
- an entry of the kernel's own claims never saw one of its classes (EXTENDED_COUNTS below): for
  extends a finite result, an overflow on finite operands and a non-finite operand, and cases
  where every finite_when condition holds when the list is not empty; for encloses each of the
  finite ball, the whole line and the empty set as results (and cases where every finite_when
  condition holds when the list is not empty); for represents a finite, an infinite and a NaN
  value; for makes_ball each of the three given states; for the kinds the finite domain has,
  non-finite operands (and, for a comparison, both outcomes on them; for an upper bound, both a
  NaN and an infinity from them).

The claims are those the oracle judged against, the file its summary names (or --claims).
Otherwise it prints one line saying what was checked. Python's standard library only, and
nothing from the oracle but the format of its summary (oracle/README.md, "Statistics" and "The
extended domain").
"""
import argparse
import json
import sys

# The strata of every family of the oracle's generator (oracle/README.md, "gen").
COMMON_STRATA = ("uniform", "underflow", "overflow", "zero", "pow2", "extreme")

# The counts of the oracle's judge of the extended domain (oracle/README.md, "The extended
# domain"; oracle/kairn_oracle/extended.py) that must not be zero, by the kind of an entry of the
# kernel's own claims: the classes of results each statement is about.
EXTENDED_COUNTS = {
    "extends": ("class F2: finite operands, finite result",
                "class F4: finite operands, non-finite result",
                "class F5: a non-finite operand"),
    "encloses": ("result: finite ball", "result: whole line", "result: empty set"),
    "represents": ("value finite", "value infinite", "value NaN"),
    "makes_ball": ("given: finite ball", "given: whole line", "given: empty set"),
    "normalized": ("a non-finite operand",),
    "error": ("a non-finite operand",),
    "leading_rounded": ("a non-finite operand",),
    "predicate": ("a non-finite operand, true", "a non-finite operand, false"),
    "rounded": ("a non-finite operand",),
    "upper": ("value NaN (a NaN operand, or 0 * inf)", "output +inf on a non-finite operand"),
}
# Where finite_when is not empty: the cases where every condition holds, so that F3 or B4 was
# put to the test.
FINITE_WHEN_COUNTS = {
    "extends": "F3 applies: finite operands, every finite_when condition holds",
    "encloses": "B4 applies: finite operands, every finite_when condition holds",
}


def extended_strata(kernel):
    """The strata the oracle's generator adds for a kernel of the extended domain (gen3.py)."""
    ensures = kernel.get("ensures", [])
    kinds = {e.get("kind") for e in ensures}
    product = ("*" in (kernel.get("value") or "")
               or any(e.get("kind") == "extends" and e.get("lead") == "mul" for e in ensures)
               or any(e.get("kind") == "encloses" and "*" in (e.get("set") or "") for e in ensures))
    strata = ["nonfinite"]
    if product:
        strata.append("zeroinf")
    if "extends" in kinds:
        strata.append("edge")
    if any(e.get("finite_when") for e in ensures):
        strata.append("threshold")
    if "encloses" in kinds:
        strata += ["ballstates", "zerowhole", "hugeradius"]
    if "makes_ball" in kinds:
        strata.append("badradius")
    return strata


def kernel_claims(summary, a):
    """The kernel's entry in the claims the oracle judged against, or a reason why not."""
    path = getattr(a, "claims", None) or summary.get("claims")
    if not path:
        return None, "the oracle's summary names no claims file, and --claims is not given"
    try:
        with open(path, encoding="utf-8") as f:
            kernels = json.load(f)["kernels"]
    except (OSError, ValueError, KeyError, TypeError) as ex:
        return None, "cannot read the claims %s: %s" % (path, ex)
    for k in kernels:
        if k.get("name") == a.kernel:
            return k, None
    return None, "the claims %s have no kernel %s" % (path, a.kernel)


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
    kernel, why = kernel_claims(summary, a)
    if kernel is None:
        yield why
        return
    extended = kernel.get("domain", "finite") == "extended"
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
        if extended:
            for s in extended_strata(kernel):
                if s not in strata:
                    yield ("the oracle's generator lists the strata %s, without %s, which it "
                           "adds for %s in the extended domain" % (",".join(strata), s, a.kernel))

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
    merged = []
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
        merged.append(counts)
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
    if not extended:
        return

    # The extended domain: each entry of the kernel's own claims (the summary lists them first,
    # then those of the cores that extends applies) saw every class of its statement.
    own = kernel.get("ensures", [])
    if len(entries) < len(own) or any(entries[j]["kind"] != e.get("kind")
                                      for j, e in enumerate(own)):
        yield ("the summary's entries (%s) are not those of the claims of %s (%s)"
               % (", ".join(e["kind"] for e in entries), a.kernel,
                  ", ".join(str(e.get("kind")) for e in own)))
        return
    for j, e in enumerate(own):
        label, counts = entries[j]["label"], merged[j]
        for name in EXTENDED_COUNTS.get(e.get("kind"), ()):
            if not counts.get(name):
                yield ('the claim "%s" saw no case of "%s", so the extended domain was not '
                       'checked there' % (label, name))
        name = FINITE_WHEN_COUNTS.get(e.get("kind"))
        if name and e.get("finite_when") and not counts.get(name):
            yield ('the claim "%s" saw no case where every finite_when condition holds, so its '
                   'finite_when was not checked' % label)


# How describe() names the counts of EXTENDED_COUNTS and FINITE_WHEN_COUNTS.
SHORT = {
    "class F2: finite operands, finite result": "F2 finite",
    "class F4: finite operands, non-finite result": "F4 overflow",
    "class F5: a non-finite operand": "F5 non-finite operand",
    "result: finite ball": "finite ball",
    "result: whole line": "whole line",
    "result: empty set": "empty set",
    "given: finite ball": "given finite ball",
    "given: whole line": "given whole line",
    "given: empty set": "given empty set",
    "a non-finite operand": "non-finite operand",
    "a non-finite operand, true": "non-finite operand true",
    "a non-finite operand, false": "non-finite operand false",
    "value NaN (a NaN operand, or 0 * inf)": "NaN",
    "output +inf on a non-finite operand": "+inf from a non-finite operand",
    FINITE_WHEN_COUNTS["extends"]: "F3 applies",
    FINITE_WHEN_COUNTS["encloses"]: "B4 applies",
}


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
    text = "%d cases judged (%s)" % (judged, what)
    kernel, _ = kernel_claims(summary, a)
    if kernel and kernel.get("domain") == "extended":
        seen = []
        for j, e in enumerate(kernel.get("ensures", [])):
            names = list(EXTENDED_COUNTS.get(e.get("kind"), ()))
            if e.get("finite_when") and e.get("kind") in FINITE_WHEN_COUNTS:
                names.append(FINITE_WHEN_COUNTS[e["kind"]])
            for name in names:
                n = sum(k["stats"]["entries"][j].get("counts", {}).get(name, 0)
                        for k in summary["keys"])
                item = "%s %d" % (SHORT.get(name, name), n)
                if item not in seen:
                    seen.append(item)
        text += "; extended domain: " + ", ".join(seen)
    return text


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("summary")
    p.add_argument("--kernel", required=True)
    p.add_argument("--format", required=True)
    p.add_argument("--exhaustive", action="store_true")
    p.add_argument("--restrict", default="")
    p.add_argument("--count", type=int)
    p.add_argument("--seed")
    p.add_argument("--claims", help="the claims file (default: the one the summary names)")
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
