"""shrink: a failing case made simpler, with the same failure.

Given one line that a runner fails (a request or a completed line), the runner, and the claims,
`shrink` looks for a simpler case that the same runner fails in the same way: the same `ensures`
entry (in the extended domain, the same statement, F1 to F5 or B1 to B4), as judged by the
oracle's checker (search.Judge, search.failure_keys).

Simpler is measured by a tuple compared in order: the number of limbs that are not zero, the
number of significant bits of every limb (the bits between its leading and its trailing one), the
distance of every limb's exponent from zero, the number of negative limbs and of negative zeros.
Every step it takes makes the tuple smaller, so it ends; each round tries every one-step change
of the current case at once, in one runner process, and keeps the simplest that still fails:

- an operand replaced by zero (a power of two by 1), or by the power of two of its leading bit;
- a limb replaced by zero, its significand cut to its leading 1, 2, 3, 4, 6, 8, 12, 16, ... bits,
  its lowest set bit cleared, its sign made positive, a negative zero made positive;
- an operand, or every operand together (for a product, one factor up and the other down by the
  same power of two), scaled toward exponent zero: all the way, half way, or by one;

each repaired into the kernel's requirements as the search does (a pair renormalized, ...), and
dropped if it does not satisfy them. Then, unless --no-toy, it looks for the smallest toy format
in which the runner fails the same way: formats of precision from the kernel's min_precision up to
one less than the case's, with 2 to 16 exponents placed as binary64 places them
(qmin + qmax = 3 - 2p, and qmax >= 1 in the extended domain, where the statements are proved for
that shape), tried in the order of the size of their enumeration: the case itself rounded into the
format, then every case of the format (or --toy-cases random cases of every stratum, where there
are more). In the first format that fails, the simplest failing case is shrunk again. A runner that
does not run a toy format (a compiled one) leaves this step out, and the report says so.

Deterministic: the same line, runner and options give the same result.
"""

import json
import os
import sys

from . import fmt as F
from . import gen as G
from . import search as S
from .claims import load_claims, ClaimsError

TRUNCATIONS = (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48)
EXPONENT_COUNTS = (2, 4, 6, 8, 10, 12, 16)


class ShrinkError(ValueError):
    pass


def _bits(v):
    """Significant bits of a fixed value: from its leading to its trailing one."""
    if type(v) is not int or v == 0:
        return 0
    a = abs(v)
    return (a >> ((a & -a).bit_length() - 1)).bit_length()


class Case:
    """Operand limbs that may be infinite or NaN (the extended domain), with the checks of the
    kernel's own requirements: the finite view's for a kernel of the finite domain, the extended
    ones (gen3.valid_ext) otherwise."""

    def __init__(self, problem):
        self.pr = problem
        self.fmt = problem.fmt
        self.kernel = problem.kernel
        from . import gen6
        if gen6.family_of(self.kernel) is not None:
            # The interval kernels: their requirements (interval(), not_nan()) by gen6.valid6.
            self._valid = lambda vals: gen6.valid6(self.fmt, self.kernel, vals)
        elif self.kernel.extended:
            from . import gen3
            self._valid = lambda vals: gen3.valid_ext(self.fmt, self.kernel, vals)
        else:
            self._valid = lambda vals: G.valid(self.fmt, self.kernel, vals)

    def parse(self, line):
        pr = self.pr
        left = line.strip().partition(" -> ")[0].split()
        toks = [t for t in left[2:] if not t.startswith("#")]
        if len(toks) != sum(pr.limbs.values()):
            raise ShrinkError("%d limbs; %s takes %d" % (len(toks), pr.kernel.name,
                                                        sum(pr.limbs.values())))
        vals, negz, k = {}, set(), 0
        for n in pr.names:
            limbs = []
            for i in range(pr.limbs[n]):
                t = toks[k]
                k += 1
                if pr.roles[n] == "mask":
                    limbs.append(int(t == "1"))
                    continue
                try:
                    v = F.parse_limb(self.fmt, t)
                except F.LimbError as ex:
                    raise ShrinkError(str(ex))
                if v == F.OUTSIDE or (type(v) is int and not F.is_member(self.fmt, v)):
                    raise ShrinkError("%s is not a number of %s" % (t, self.fmt.name))
                if type(v) is str and not self.kernel.extended:
                    raise ShrinkError("%s: a kernel of the finite domain takes finite operands" % t)
                if v == 0 and t.startswith("-"):
                    negz.add((n, i))
                limbs.append(v)
            vals[n] = limbs
        if not self._valid(vals):
            raise ShrinkError("the operands do not satisfy the requirements of %s" % pr.kernel.name)
        return vals, negz

    def repair(self, vals, negz):
        """As Problem.repair, leaving a non-finite operand as it is."""
        pr = self.pr
        fmt = self.fmt
        for n in pr.names:
            v = vals[n]
            if any(t is None for t in v):
                return None
            if not all(type(t) is int for t in v):
                continue
            role = pr.roles[n]
            if role == "x2" and not F.normalized_limbs(fmt, v):
                s = S._round(fmt, v[0] + v[1])
                if s is None:
                    return None
                v = [s, v[0] + v[1] - s]
            elif role == "radius":
                v = [abs(v[0])]
            elif role == "pow2":
                a = abs(v[0])
                v = [1 << (a.bit_length() - 1) if a else S._pow2(fmt, 0)]
            vals[n] = v
        for big, small in pr.abs_ge:
            if abs(sum(vals[big])) < abs(sum(vals[small])):
                vals[big], vals[small] = vals[small], vals[big]
        S.repair_intervals(self.kernel, vals)
        if not self._valid(vals):
            return None
        return vals, frozenset((n, i) for n, i in negz if vals[n][i] == 0)

    def measure(self, vals, negz):
        fmt = self.fmt
        limbs = [v for n in self.pr.names if self.pr.roles[n] != "mask" for v in vals[n]]
        return (sum(1 for v in limbs if v != 0),
                sum(_bits(v) for v in limbs),
                sum(abs(fmt.binade(v)) for v in limbs if type(v) is int and v),
                sum(1 for v in limbs if type(v) is int and v < 0),
                len(negz))


def _toward_zero(e):
    """Exponent shifts that bring a binade e toward zero: all the way, half way, by one."""
    if e == 0:
        return []
    out = [-e]
    if abs(e) > 1:
        out.append(-(e // 2) if e > 0 else (-e) // 2)
        out.append(-1 if e > 0 else 1)
    return out


class Shrinker:
    def __init__(self, claims, runner, line, entry=None, evals=50000, toy=True, toy_cases=2000,
                 fail_on_suspicious=False):
        self.claims = claims
        self.runner = runner
        self.max_evals = evals
        self.toy = toy
        self.toy_cases = toy_cases
        self.fail_on_suspicious = fail_on_suspicious
        self.evals = 0
        left = line.strip().partition(" -> ")[0].split()
        if len(left) < 2:
            raise ShrinkError("not a line of the protocol: %r" % line)
        self.kernel = claims.get(left[0])
        if self.kernel is None:
            raise ShrinkError(claims.broken.get(left[0], "no claims for kernel %r" % left[0]))
        try:
            self.fmt = F.parse_format(left[1])
        except F.FormatError as ex:
            raise ShrinkError(str(ex))
        self.line = line
        self.entry = entry
        self.notes = []

    # -- running and judging -----------------------------------------------------------------

    def _setup(self, fmt):
        pr = S.Problem(self.kernel, fmt)
        return pr, Case(pr), S.Judge(self.claims, self.kernel, fmt, self.fail_on_suspicious)

    def _run(self, pr, judge, cands):
        """[(cand, verdict)] for the candidates ((vals, negz) pairs), in one runner process."""
        if not cands:
            return []
        reqs = [pr.text(v, nz, "shrink:%d" % (self.evals + i)) for i, (v, nz) in enumerate(cands)]
        done = self.runner.run(reqs)
        self.evals += len(reqs)
        return [(c, judge.judge(ln)) for c, ln in zip(cands, done)]

    def _fails(self, verdict):
        return verdict.failed and self.target in verdict.keys

    # -- one format ----------------------------------------------------------------------------

    def _steps(self, pr, case, vals, negz):
        """Every one-step simplification of the case, repaired (duplicates included)."""
        fmt = pr.fmt
        out = []

        def emit(mut):
            v = {n: list(x) for n, x in vals.items()}
            nz = set(negz)
            if mut(v, nz) is False:
                return
            r = case.repair(v, nz)
            if r is not None:
                out.append(r)

        for n in pr.names:
            role = pr.roles[n]
            if role == "mask":
                continue
            limbs = vals[n]

            def to_zero(v, nz, n=n, role=role):
                v[n] = [S._pow2(fmt, 0)] if role == "pow2" else [0] * len(v[n])
            emit(to_zero)
            if type(limbs[0]) is int and limbs[0]:
                def to_pow2(v, nz, n=n):
                    x0 = v[n][0]
                    v[n] = [(1 if x0 > 0 else -1) << (abs(x0).bit_length() - 1)] + [0] * (len(v[n]) - 1)
                emit(to_pow2)
                for d in _toward_zero(fmt.binade(limbs[0])):
                    def scale(v, nz, n=n, d=d, role=role):
                        if role == "pow2":
                            v[n] = [S._pow2(fmt, fmt.binade(v[n][0]) + d)]
                        else:
                            v[n] = [S._scale(fmt, t, d) for t in v[n]]
                    emit(scale)
            for i, x in enumerate(limbs):
                if type(x) is not int or x == 0:
                    continue

                def zero(v, nz, n=n, i=i):
                    v[n][i] = 0
                emit(zero)
                b = _bits(x)
                M, u = S._sig(fmt, x)
                nb = M.bit_length()
                for k in TRUNCATIONS:
                    if k >= b:
                        break

                    def cut(v, nz, n=n, i=i, k=k, M=M, u=u, nb=nb):
                        v[n][i] = S._sign(v[n][i]) * ((M >> (nb - k)) << (nb - k)) * u
                    emit(cut)

                def clear_low(v, nz, n=n, i=i):
                    a = abs(v[n][i])
                    v[n][i] = S._sign(v[n][i]) * (a & (a - 1))
                emit(clear_low)
                if x < 0:
                    def positive(v, nz, n=n, i=i):
                        v[n][i] = -v[n][i]
                    emit(positive)
                if i > 0:
                    # A second limb alone toward exponent zero (the operand is renormalized).
                    for d in _toward_zero(fmt.binade(x)):
                        def shift_tail(v, nz, n=n, i=i, d=d):
                            v[n][i] = S._scale(fmt, v[n][i], d)
                        emit(shift_tail)
        for z in sorted(negz):
            def unsign(v, nz, z=z):
                nz.discard(z)
            emit(unsign)
        # Every operand together, toward exponent zero; for a product, a factor up and the
        # other down.
        vs = [n for n in pr.values if type(vals[n][0]) is int and vals[n][0]]
        pw = [n for n in pr.names if pr.roles[n] == "pow2"]
        if vs:
            top = max(vs, key=lambda n: abs(vals[n][0]))
            for d in _toward_zero(fmt.binade(vals[top][0])):
                def scale_all(v, nz, d=d):
                    for n in pr.names:
                        if pr.roles[n] in ("x2", "limb", "radius") and all(type(t) is int for t in v[n]):
                            v[n] = [S._scale(fmt, t, d) for t in v[n]]
                emit(scale_all)
        if pr.op == "*" or pw:
            factors = [n for n in vs + pw]
            for a in factors:
                for b in factors:
                    if a == b:
                        continue
                    for d in _toward_zero(fmt.binade(vals[a][0])):
                        def trade(v, nz, a=a, b=b, d=d):
                            for n, dd in ((a, d), (b, -d)):
                                if pr.roles[n] == "pow2":
                                    v[n] = [S._pow2(fmt, fmt.binade(v[n][0]) + dd)]
                                else:
                                    v[n] = [S._scale(fmt, t, dd) for t in v[n]]
                                    for r, c in pr.center_of.items():
                                        if c == n:
                                            v[r] = [S._scale(fmt, t, dd) for t in v[r]]
                        emit(trade)
        return out

    def _greedy(self, pr, case, judge, vals, negz):
        """Rounds of one-step simplifications, each keeping the simplest that still fails."""
        cur = (vals, frozenset(negz))
        m = case.measure(*cur)
        rounds = 0
        seen = {pr.text(*cur)}
        while self.evals < self.max_evals:
            cands = []
            for c in self._steps(pr, case, *cur):
                t = pr.text(*c)
                cm = case.measure(*c)
                if cm < m and t not in seen:
                    seen.add(t)
                    cands.append((cm, t, c))
            if not cands:
                break
            cands.sort(key=lambda x: (x[0], x[1]))
            cands = cands[:max(1, self.max_evals - self.evals)]
            res = self._run(pr, judge, [c for _, _, c in cands])
            ok = [(cm, t, c, v) for (cm, t, c), (_, v) in zip(cands, res) if self._fails(v)]
            if not ok:
                break
            m, _, cur, verdict = ok[0]
            self.last = verdict
            rounds += 1
        return cur, m, rounds

    # -- toy formats ---------------------------------------------------------------------------

    def _size(self, f):
        """The size of the enumeration of a toy format: exact where it is small (the domains are
        built), an estimate from below otherwise (counted per binade, without building them)."""
        k = self.kernel
        pos = (1 << (f.p - 1)) - 1 + (f.qmax - f.qmin + 1) * (1 << (f.p - 1))
        est = 1
        for n, l in k.inputs:
            role = self.pr.roles[n]
            if role == "mask":
                est *= 2
            elif role == "pow2":
                est *= f.emax - f.qmin + 1
            elif l == 2:
                # A leading limb with every tail below half its ulp: at least the leading limbs
                # times the numbers below the smallest normal number.
                est *= (2 * pos + 1) * (1 << (f.p - 1))
            else:
                est *= (pos + 1) if role == "radius" else (2 * pos + 1)
        if est > 8 * self.toy_cases:
            return est
        try:
            return G.ExhaustiveGen(k, f).total
        except G.GenError:
            return None

    def _toy_formats(self):
        k = self.kernel
        out = []
        for p in range(max(k.min_precision, 1), min(self.fmt.p - 1, 11) + 1):
            for ne in EXPONENT_COUNTS:
                qmin = (4 - 2 * p - ne) // 2
                qmax = qmin + ne - 1
                if k.extended and qmax < 1:
                    continue
                f = F.parse_format("fp:%d:%d:%d" % (p, qmin, qmax))
                total = self._size(f)
                if total is not None:
                    out.append((min(total, self.toy_cases), total, p, f))
        out.sort(key=lambda t: (t[0], t[2], t[3].qmax))
        return [(f, total) for _, total, _, f in out]

    def _rounded(self, toy, vals):
        """The case in a toy format, each limb rounded to it (None beyond its Omega)."""
        out = {}
        for n, limbs in vals.items():
            out[n] = []
            for v in limbs:
                if type(v) is int and self.pr.roles[n] != "mask":
                    v = F.rn(toy, v, self.fmt.qmin)
                    v = v if type(v) is int else None
                out[n].append(v)
        return out

    def _relative(self, toy, vals):
        """The case in a toy format with its shape kept: each leading limb's significand rounded
        to the toy precision at the same exponent (or the nearest the toy format has), and each
        second limb at the same place relative to the ulp of its leading limb (so that half an
        ulp stays half an ulp)."""
        fmt = self.fmt
        out = {}
        for n, limbs in vals.items():
            if self.pr.roles[n] == "mask" or not all(type(v) is int for v in limbs) or not limbs[0]:
                out[n] = list(limbs)
                continue
            e = fmt.binade(limbs[0])
            d = max(toy.emin_normal, min(toy.emax, e)) - e
            row = []
            for i, v in enumerate(limbs):
                shift = d + (fmt.p - toy.p if i else 0)
                r = F.rn(toy, v, fmt.qmin + shift) if v else 0
                row.append(r if type(r) is int else None)
            out[n] = row
        return out

    def _toy(self, vals, negz):
        """(format, how it was searched, the simplest failing case there) or None."""
        tried = 0
        runs = 0
        for toy, total in self._toy_formats():
            if self.evals >= self.max_evals:
                self.notes.append("the case budget ran out after %d toy formats" % tried)
                return None
            tried += 1
            pr, case, judge = self._setup(toy)
            cands = []
            for proj in (self._rounded(toy, vals), self._relative(toy, vals)):
                r = case.repair(proj, negz)
                if r is not None:
                    cands.append(r)
            if total <= self.toy_cases:
                g = G.ExhaustiveGen(self.kernel, toy)
                how = "every case of its enumeration (%d)" % total
                lines = g.lines(0, total)
            else:
                g = G.RandomGen(self.kernel, toy, "shrink")
                how = "%d random cases of every stratum (its enumeration is larger)" % (
                    self.toy_cases)
                lines = g.lines(0, self.toy_cases)
            for ln in lines:
                if ln.startswith("#"):
                    continue
                try:
                    cands.append(case.parse(ln))
                except ShrinkError:
                    continue
            budget = self.max_evals - self.evals
            cands = cands[:budget]
            fails = []
            try:
                for i in range(0, len(cands), 4096):
                    for c, v in self._run(pr, judge, cands[i:i + 4096]):
                        if self._fails(v):
                            fails.append((case.measure(*c), pr.text(*c), c))
                runs += 1
            except S.RunnerError as ex:
                if runs == 0 and tried >= 3:
                    self.notes.append("the runner ran none of the first three toy formats (%s: "
                                      "%s); no toy format tried further" % (toy.name, ex))
                    return None
                if runs:
                    self.notes.append("%s: %s" % (toy.name, ex))
                continue
            if fails:
                fails.sort(key=lambda x: (x[0], x[1]))
                return toy, how, fails[0][2]
        self.notes.append("no toy format tried (%d) fails the same way" % tried)
        return None

    # -- the whole -----------------------------------------------------------------------------

    def run(self):
        self.pr, self.case, self.judgeobj = self._setup(self.fmt)
        pr, case, judge = self.pr, self.case, self.judgeobj
        vals, negz = case.parse(self.line)
        (_, v0), = self._run(pr, judge, [(vals, negz)])
        if not v0.failed:
            raise ShrinkError("%s passes this line: there is nothing to shrink" % self.runner.text)
        self.keys = v0.keys
        if self.entry is not None:
            if self.entry not in v0.keys:
                raise ShrinkError("the line does not fail %r; it fails: %s" % (
                    self.entry, "; ".join(v0.keys)))
            self.target = self.entry
        else:
            self.target = v0.keys[0]
        self.first = v0
        self.last = v0
        self.m0 = case.measure(vals, frozenset(negz))
        (self.same, self.m1, self.rounds) = self._greedy(pr, case, judge, vals, negz)
        self.same_verdict = self.last
        self.toy_result = None
        if self.toy:
            found = self._toy(*self.same)
            if found is not None:
                toy, how, c = found
                tpr, tcase, tjudge = self._setup(toy)
                (_, vt), = self._run(tpr, tjudge, [c])
                self.last = vt
                cur, m, rounds = self._greedy(tpr, tcase, tjudge, *c)
                self.toy_result = {"format": toy.name, "how": how, "case": cur, "measure": m,
                                   "rounds": rounds, "verdict": self.last, "problem": tpr}
        return self

    def result(self):
        pr = self.pr
        out = {"kernel": self.kernel.name, "format": self.fmt.name, "runner": self.runner.text,
               "line": self.line.partition(" -> ")[0], "failed": self.keys, "kept": self.target,
               "measure": list(self.m0),
               "same_format": {"line": self.same_verdict.line, "request": pr.text(*self.same),
                               "measure": list(self.m1), "rounds": self.rounds},
               "toy": None, "evals": self.evals, "notes": self.notes}
        final = out["same_format"]
        if self.toy_result is not None:
            t = self.toy_result
            out["toy"] = {"format": t["format"], "searched": t["how"], "line": t["verdict"].line,
                          "request": t["problem"].text(*t["case"]), "measure": list(t["measure"]),
                          "rounds": t["rounds"]}
            final = out["toy"]
        out["result"] = final["request"]
        out["completed"] = final["line"]
        out["reproduce"] = S.reproduce(final["request"], self.runner, self.claims.path,
                                       self.fail_on_suspicious)
        return out


def print_result(r, out=sys.stdout):
    w = lambda s="": print(s, file=out)
    w("kairn-oracle shrink: %s %s through %s" % (r["kernel"], r["format"], r["runner"]))
    w("  the line:     %s" % r["line"])
    w("  it fails:     %s" % "; ".join(r["failed"]))
    w("  kept:         %s" % r["kept"])
    s = r["same_format"]
    w("  in %s, after %d rounds: %s" % (r["format"], s["rounds"], s["request"]))
    w("    measure (limbs not zero, significant bits, exponents, negative limbs, negative zeros): "
      "%s, was %s" % (tuple(s["measure"]), tuple(r["measure"])))
    if r["toy"]:
        t = r["toy"]
        w("  the smallest toy format tried that fails the same way: %s (searched: %s)" % (
            t["format"], t["searched"]))
        w("    after %d rounds there: %s" % (t["rounds"], t["request"]))
        w("    measure %s" % (tuple(t["measure"]),))
    for n in r["notes"]:
        w("  note: %s" % n)
    w("  shrunk: %s" % r["result"])
    w("      -> %s" % r["completed"].partition(" -> ")[2])
    w("  to run it again: %s" % r["reproduce"])
    w("  %d cases run" % r["evals"])


def main(a):
    claims_path = a.claims or os.path.join(S.REPO_DIR, "gen", "claims.json")
    try:
        claims = load_claims(claims_path)
    except ClaimsError as ex:
        print("kairn-oracle shrink: %s" % ex, file=sys.stderr)
        return 2
    line = sys.stdin.readline() if a.line == "-" else a.line
    try:
        runner = S.Runner(a.runner, a.radius)
        sh = Shrinker(claims, runner, line, a.entry, a.evals, not a.no_toy, a.toy_cases,
                      a.fail_on_suspicious)
        r = sh.run().result()
    except (ShrinkError, S.SearchError, S.RunnerError) as ex:
        print("kairn-oracle shrink: %s" % ex, file=sys.stderr)
        return 2
    print_result(r)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(r, fh, indent=1)
            fh.write("\n")
    return 0
