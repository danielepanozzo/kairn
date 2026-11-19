# kairn-oracle

The test oracle of Kairn: it decides, in exact arithmetic, whether results produced by any
runner satisfy the claims in `gen/claims.json`. It is Python 3, standard library only, and shares
no code with the generator or the library; it reads `gen/claims.json` as data and nothing else.
The contract it implements is [docs/developer/architecture.md](../docs/developer/architecture.md)
("Number formats", "Claims", "The line protocol").

Every verdict is decided with Python integers. A limb of a format with smallest subnormal
$\eta = 2^{q_{\min}}$ is stored as the integer $N$ with value $N\eta$; sums of limbs are integers
at the same scale and products are integers at scale $\eta^2$. No floating-point operation and no
`Fraction` takes part in a verdict.

```
python3 oracle/kairn-oracle gen KERNEL FORMAT [options]      request lines
python3 oracle/kairn-oracle check [FILES] [options]          verdict and statistics
python3 oracle/kairn-oracle brute --runner CMD ... [options] parallel gen | runner | check
python3 oracle/kairn-oracle refrun [--variant V]             the reference runner (Python)
python3 oracle/kairn-oracle selftest [--quick]               the oracle's own tests
```

Claims are read from `gen/claims.json` of this repository unless `--claims FILE` says otherwise.
The selftest uses its own hand-written fixture, `oracle/selftest/claims-wave1.json`, so that it
does not depend on the generator.

## gen

```
kairn-oracle gen add_2_2 binary64 --seed 7 --start 0 --count 100000
kairn-oracle gen mul_2_2 fp:5:-10:5 --exhaustive --restrict x.lead=2:2 --restrict x.sign=+
kairn-oracle gen mul_2_2 fp:5:-10:5 --exhaustive --restrict x.lead=2:2 --total
```

Formats are `binary64`, `binary32` or `fp:P:QMIN:QMAX`. The kernel's inputs and requirements come
from the claims; every generated case satisfies them (the selftest checks this for every kernel
and stratum).

**Random mode** is counter-based: case $i$ depends only on (kernel, format, seed, strata) and $i$,
through a keyed BLAKE2 hash, so `--start i --count 1` regenerates case $i$ alone and a run can be
split anywhere. Strata take turns in a fixed schedule (`close`, `cancel` and `underflow` come round
more often); `--strata a,b` restricts it. Each line is tagged `#STRATUM:INDEX`.

| Stratum | Operands |
|---|---|
| `uniform` | random significands, leading exponents uniform over the whole range (for products, half of the cases have the product's exponent uniform instead) |
| `close` | exponents within $kp+2$ binades of each other, away from both ends of the range |
| `cancel` | sums: $y_0 = -x_0$ up to three ulps, and tails that nearly cancel too; products: $y_1$ chosen so that $x_0y_1$ nearly cancels $x_1y_0$ |
| `overflow` | leading limbs in the top binades, $\Omega$ itself, products near $\Omega$ |
| `underflow` | subnormal and low normal operands; products from below $\eta$ through $\lambda$ up past $2^{2p-1}\eta$ and $2^{3p-1}\eta$ |
| `pow2` | powers of two and significands with one to three bits; sums that land on ties |
| `extreme` | second limbs at the extremes of the invariant: $\pm\frac12\mathrm{ulp}(x_0)$ (toward an even $x_0$), $-\frac14\mathrm{ulp}$ below a power of two, the largest value below half an ulp, $\pm\eta$, tiny, zero; leading limbs $\pm\Omega$, $\lambda$, $\mathrm{pred}(\lambda)$, $\eta$ |
| `zero` | zero limbs, with random signs |

The second limb of a 2-limb operand is mostly within a few binades of half an ulp of the first
(where it carries a full second word) and otherwise anywhere below.

**Exhaustive mode** (`--exhaustive`) enumerates the product of the operand domains: every number
of the format for a 1-limb input (one zero), every normalized pair for a 2-limb input. Case $i$ is
decoded from $i$ directly. A coupled requirement (`abs_ge`) is applied by skipping the indices it
excludes. Restrictions shrink a domain:

- `NAME.lead=LO:HI` keeps operands whose leading limb is in binades LO to HI
  ($2^{LO} \le |x_0| < 2^{HI+1}$; this excludes zero);
- `NAME.sign=+` or `-` keeps $x_0 \ge 0$ or $x_0 \le 0$.

The generator writes a header and a trailer comment around its lines:

```
# kairn-oracle gen event=begin kernel=mul_2_2 format=fp:5:-10:5 mode=exhaustive total=... restrict=x.lead=2:2,x.sign=+ skip=none start=0 count=...
...
# kairn-oracle gen event=end lines=...
```

`check` turns them into the coverage statement of its report, which says COMPLETE only when the
indices seen cover the whole enumeration and nothing was restricted; otherwise it says "complete
over a RESTRICTED domain (...)" or "PARTIAL". It also counts the completed lines between header and
trailer: a runner that drops or adds lines, or stops early, is a stream error and fails the run.

## check

Reads completed lines (`KERNEL FORMAT LIMB... [#TAG] -> LIMB...`), from files or standard input.
For each line, in this order:

1. The kernel must have claims and the format must parse; the line must have the arrow and the
   right number of limbs on both sides. Otherwise: **failure**.
2. If the format's precision is below the kernel's `min_precision`, the line is **out of scope**
   and not judged (`--ignore-min-precision` judges it anyway).
3. **Requirements**: every input limb must be a finite number of the format, then every
   `requires` entry must hold (`normalized(x)`: $x_i = \mathrm{RN}(x_i + x_{i+1})$;
   `abs_ge(a, b)`: $|a| \ge |b|$ as values). Otherwise the line is **invalid**: counted, shown,
   never passed.
4. **Non-finite results**: if output limb 0 is not finite, the line is **non-finite** and not
   judged. If limb 0 is finite but a lower limb is not, it is counted as non-finite too (column
   "in a lower limb only"): under this wave's hypothesis that no operation overflows such a case is
   outside every statement, but it shows up separately because the library invariant says it
   should not happen for k-number results. Either kind is also **suspicious** when every input
   limb, every input value and the exact value are below $\Omega/4$. Suspicious cases are listed;
   they fail the run only with `--fail-on-suspicious`.
5. Every output limb must be a number of the format. Otherwise: **failure**.
6. Every `ensures` entry: `normalized` (the invariant on the named outputs), `leading_rounded`
   (output limb 0 equals $\mathrm{RN}(\text{value})$, signs of zero ignored), `error`
   ($|\text{output} - \text{value}| \le \mathrm{rel}\cdot\rho + \mathrm{abs}$, skipped when its
   `when` condition is false). A line with any violated entry is a **failure**.

The exit status is 0 when nothing failed; 1 on any failure, stream error or kernel whose claims
cannot be read; 2 on a usage error or a claims file that cannot be read at all. `--expect-valid`
also fails on invalid cases (to test a generator).

### Statistics

Per (kernel, format, tag) and aggregated per (kernel, format): cases, judged, failed, invalid,
non-finite, suspicious, out of scope, and the reasons. Per `ensures` entry: cases where it applied
and failures; for `error` entries:

- **largest error/allowed**: $\max |\text{err}| / (\mathrm{rel}\,\rho + \mathrm{abs})$, as an
  exact fraction and a decimal, with the line that attains it. A ratio near 1 means the bound is
  tight on the data; a small one that it is loose.
- **(a)** $\max |\text{err}| / (u^k \rho)$ over the cases that are far from the underflow range,
  meaning $u^k\rho \ge 2^{F}\eta$ with $F = p$ by default (`--far F`). With $\rho = |\text{value}|$
  (form R) or $|x| + |y|$ (form A) this is the observed $c$: it says whether $c$ is tight.
- **(b)** $\max (|\text{err}| - \mathrm{rel}\,\rho) / \eta$ over all cases: the smallest $t$ the
  data needs given the claimed $c$ (none when it is $\le 0$).
- The profile of (a) by distance $D = \lfloor \log_2(u^k\rho/\eta) \rfloor$ (`--verbose`), from
  which (a) for any other $F$ can be read.

`--json FILE` writes all of this, with exact fractions as decimal strings; `check --merge A.json
B.json ...` merges summaries (counts add, maxima combine, coverage ranges unite).

### Claims as read

- `value` is `NAME+NAME`, `NAME-NAME` or `NAME*NAME` over the inputs, or a bare input `NAME`
  (the outputs approximate that input, as for `split`; an addition to architecture.md's list);
  `requires` is `normalized(NAME)` or `abs_ge(NAME, NAME)`; `ensures` kinds are `normalized`,
  `error` and `leading_rounded`; `when` is `null` or `product_large`.
- Anything else is never ignored. A kernel whose claims cannot be read (unknown vocabulary, a
  listed instance that disagrees with its `c` and `t`, a name listed twice) is set aside with the
  reason: the report starts with a CLAIMS ERROR line, its lines fail, and the run fails; the other
  kernels are still judged. A file that is not JSON or not schema 1 is an error (exit 2). Kernel
  fields outside the documented ones are reported as warnings. `check` with no input lines is a
  validation of a claims file.
- `of` names one output; a list of names, or `"s+e"`, concatenates outputs in that order, which is
  how a pair of 1-limb results `(s, e)` is read as one 2-limb number. Absent means all outputs.
- `instances[FORMAT]` is one `{rel, abs}` object when the kernel has one `error` entry, otherwise a
  list in the order of the `error` entries; an `instances` object inside an `error` entry is
  accepted too.
- The verdict uses the listed instance. For a format that is not listed (toy formats), `rel` and
  `abs` are evaluated exactly from `c` (a rational expression in `u`: integers, `u`, `+ - * /`,
  `^` or `**`, parentheses), `k` and `t`, and the report says so. Where both exist they must
  agree.

## brute

```
kairn-oracle brute --runner "build/tests/kairn-runner --backend scalar" \
    --kernels add_2_2,mul_2_2 --formats binary64 --budget 3600 --jobs 16 --json out.json
kairn-oracle brute --runner refrun --kernels mul_2_2 --formats fp:4:-8:4 --exhaustive \
    --ignore-min-precision --json mul.json
```

Runs `gen | RUNNER | check` pipelines on chunks of `--chunk` cases (default 20000), `--jobs` at a
time, for a time budget (no chunk starts after it), a number of cases per (kernel, format), or the
whole exhaustive enumeration; then merges the chunk summaries and reports, with throughput. The
runner is any shell command. `--runner refrun[:VARIANT]` runs the reference runner inside each
worker process instead (same gen and check code on the same text lines, without the pipes);
the selftest checks that both ways give the same statistics.

Throughput, one process per stage on binary64 (Apple M3 Max): `gen` 70 000 to 160 000 cases
per second, `check` 60 000 to 140 000 lines per second depending on the kernel (`mul_2_2` is the
slowest). In-process `brute` on toy formats does gen, reference runner and check at 40 000 to
70 000 cases per second per job.

## refrun and the C++ runner

`refrun` evaluates the first-wave kernels (and `split`), as written in architecture.md, for any
format. It avoids the checker's code on purpose: its rounding is computed from the two neighbors of the exact
value (the checker shifts and inspects the dropped bits), and where the format fits in binary64 it
reads limbs with `float.fromhex` and prints them with `float.hex`. `--list-variants` shows the
injected errors.

The variant `trace-fast-two-sum` computes correct results and writes a comment before a line for
every `fast_two_sum` call whose first operand is smaller in magnitude than the second, saying
whether that operand is zero, whether the exponent form of the precondition holds, and whether the
call was still error-free.

`selftest/refrun.cpp` is a standalone C++ runner for binary64 and binary32, written from the same
pseudo-code. The selftest compiles it with the system compiler (`$CXX`, then `c++`, `clang++`,
`g++`, or `--cxx`) with `-std=c++17 -O2 -ffp-contract=off -fno-fast-math` (`/std:c++17 /O2
/fp:precise` for `cl` and `clang-cl`, untested so far), and skips the C++ tests with a message if
no compiler works. It has its own variants (`subnormal-flush` instead of
`subnormal-trunc`).

## selftest

```
python3 oracle/kairn-oracle selftest            # about 35 seconds
python3 oracle/kairn-oracle selftest --quick    # smaller samples, about 20 seconds
python3 oracle/selftest/mutants.py              # tests the selftest, about five minutes
```

`mutants.py` copies the oracle into a temporary directory once per mutant, plants one deliberate
bug in the checker or the arithmetic (rounding ties away from zero, no gradual underflow,
requirements or normalization or membership of outputs not checked, a bound lenient by a factor
of two, the `when` condition ignored, ...) and requires `selftest --quick` to fail on the copy.

| Test | What would make it fail |
|---|---|
| `literals`, `membership` | exact parsing and printing of literals, membership in a format |
| `exact_compare` | the checker's comparison of fractions against `Fraction` |
| `rounding_toy` | both rounding implementations against a brute-force nearest search, every multiple of $\eta/8$ over six toy formats, overflow included |
| `rounding_hardware` | binary64 rounding of sums, products and FMAs against the machine |
| `neighbors` | `succ`, `pred`, `ulp` against the sorted list of all numbers |
| `claims_reading` | the fixture's instances against its `c` and `t`; ten malformed kernels must be set aside without making the others unreadable; a bare input name as `value` (`split`) |
| `gen_counter_based` | case $i$ alone equals case $i$ of a run; seeds matter |
| `gen_valid` | every generated case of every kernel and stratum satisfies the requirements |
| `exhaustive_counts` | the enumeration of a tiny format against a brute-force count from the definition |
| `correct_runner_toy_exhaustive` | the correct runner flagged on any case of the enumerations |
| `cxx_agrees` | the C++ runner flagged, or any of its results different from the Python runner's |
| `injected_python`, `injected_cxx`, `injected_exhaustive` | an injected error not flagged in the entry where it belongs, or flagged in one where it does not |
| `scaled_bounds` | bounds halved must fail and bounds times 1024 must pass, with every largest ratio scaled by exactly the inverse factor |
| `check_robustness` | malformed, truncated or non-finite streams passed |
| `merging` | the merged summary of two halves differs from the summary of the whole |
| `brute_driver` | external and in-process pipelines disagree |

Injected errors (`refrun --list-variants`): one ulp off in the second limb in about 1 case in 256;
a result with the right value but not normalized; a product that drops a cross term; additions
that skip their last renormalization; rounding wrong only below $\lambda$; a `two_sum` whose error
term is wrong only when it should be zero; inputs altered to violate a requirement (must be
invalid, not passed); and the fixture with every bound halved (must fail) or multiplied by 1024
(must pass with ratios 1024 times smaller).
