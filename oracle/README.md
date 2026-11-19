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
The selftest uses its own hand-written fixtures, `oracle/selftest/claims-wave1.json` and
`oracle/selftest/claims-wave2.json` (the kernels of [Milestone 1
statements](../docs/developer/design/milestone1.md)), so that it does not depend on the
generator.

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

The strata above are those of kernels whose value is `NAME op NAME` (or one input) and whose
claims use the first-wave kinds, which includes the subtractions.  The other kernels of the
second wave get their own generator (`gen2.py`): each input has a role (a normalized 2-limb
operand, a limb, a radius for `nonneg()`, a power of two for `power_of_two()`, a mask) and
each kernel a family from its claims, with the strata `uniform`, `underflow`, `overflow`,
`zero`, `pow2` and `extreme` as above, plus:

| Family | Kernels | Strata of its own |
|---|---|---|
| unary | `neg_2`, `abs_2`, conversions | `halfgap`: $x_1 = \pm\frac12$ gap of $x_0$ on either side, at powers of two too (where the gap below is half the gap above) |
| compare | `predicate` claims | `equal`; `lastplace` (operands that differ in the last place of the second limb only, or a one-limb operand against the same leading limb and the smallest tail); `leadequal`; `neighbor` ($y_0 = $ succ or pred of $x_0$); `straddle` (opposite signs near zero, zeros of both signs); `halfgap` |
| step | `upper` claims | `nonneg`; `tie` (sums $N2^E$ and products, factored by small primes, with $N$ odd at the rounding position, below and above powers of two and in the subnormal range); `close` |
| scale | a `power_of_two()` input | `into` and `outof` (scalings into and out of the subnormal range); `halfscaled` ($c x_1$ rounding to exactly half a gap of $c x_0$) |
| ball | `encloses` claims | `radii` (zero, $\eta$, subnormal, tiny, about an ulp of the center, comparable, much wider than the center, huge); `wide` (small centers, wide radii); `exact` (zero radii, inexact centers); `centerpow2` (centers whose sum or product is a power of two); `cancel` |

**Exhaustive mode** (`--exhaustive`) enumerates the product of the operand domains: every number
of the format for a 1-limb input (one zero), every normalized pair for a 2-limb input, 0 and 1
for a mask; `nonneg()` and `power_of_two()` remove the operands they exclude from the domain of
their input. Case $i$ is decoded from $i$ directly. A coupled requirement (`abs_ge`) is applied
by skipping the indices it excludes. Restrictions shrink a domain:

- `NAME.lead=LO:HI` keeps operands whose leading limb is in binades LO to HI
  ($2^{LO} \le |x_0| < 2^{HI+1}$; this excludes zero);
- `NAME.sign=+` or `-` keeps $x_0 \ge 0$ or $x_0 \le 0$;
- `NAME.in=V1/V2/...` keeps operands whose leading limb is one of the listed literals (radii
  of the Ball kernels, for example `rx.in=0x0p+0/0x1p-3/0x1p-1`).

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
3. **Requirements**: every input limb must be a finite number of the format and every mask
   input `0` or `1`, then every `requires` entry must hold (`normalized(x)`:
   $x_i = \mathrm{RN}(x_i + x_{i+1})$; `abs_ge(a, b)`: $|a| \ge |b|$ as values; `nonneg(r)`:
   $r \ge 0$; `power_of_two(c)`: $c = 2^n$ for an integer $n$, so positive). Otherwise the line
   is **invalid**: counted, shown, never passed.
4. **Non-finite results**: if output limb 0 is not finite, the line is **non-finite** and not
   judged. If limb 0 is finite but a lower limb is not, it is counted as non-finite too (column
   "in a lower limb only"): under this wave's hypothesis that no operation overflows such a case is
   outside every statement, but it shows up separately because the library invariant says it
   should not happen for k-number results. Either kind is also **suspicious** when every input
   limb, every input value and the exact value (for `encloses`, both ends of the set) are below
   $\Omega/4$. Suspicious cases are listed; they fail the run only with `--fail-on-suspicious`.
   A line is also non-finite, whatever its output, when a `rounded` entry's exact rounding in a
   range unbounded above exceeds $\Omega$, or an `upper` entry's smallest upper bound does
   (counted again as "with an exact result beyond Omega").
5. Every output limb must be a number of the format and every mask output `0` or `1`.
   Otherwise: **failure**.
6. Every `ensures` entry: `normalized` (the invariant on the named outputs), `leading_rounded`
   (output limb 0 equals $\mathrm{RN}(\text{value})$, signs of zero ignored), `error`
   ($|\text{output} - \text{value}| \le \mathrm{rel}\cdot\rho + \mathrm{abs}$, skipped when its
   `when` condition is false), and those of the second wave:
    - `rounded`: the output equals the value rounded to nearest (ties to even), down or up, with
      gradual underflow;
    - `upper`: $\text{value} \le o$ and $o - \text{value} \le \mathrm{gaps}\cdot(o -
      \mathrm{pred}(o))$, with pred in the format unbounded above (so the gap below $-\Omega$
      is $\mathrm{ulp}(\Omega)$);
    - `predicate`: the mask equals the truth of `rel` between the exact values of the two `args`;
    - `encloses`: the set is evaluated exactly at every corner of the box of the balls
      ($[c - r, c + r]$ with $c$ the exact sum of the center's limbs); because every ball occurs
      once in a set made of sums, differences, products, scalars and negations, the set is
      multilinear in the balls and its range is the interval between the smallest and the largest
      corner value. The smallest radius around the returned center that encloses it,
      $r_{\min} = \max(c_z - \mathrm{lo}, \mathrm{hi} - c_z)$, must be at most the returned
      radius. A ball with a negative radius is empty and the entry holds (counted as such).

   A line with any violated entry is a **failure**.

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

For the kinds of the second wave, the statistics that show a loose or a tight claim:

- `upper`: the largest excess $(o - \text{value})/(o - \mathrm{pred}(o))$ in gaps, over all
  cases and over the cases whose operands are all nonnegative, with the lines that attain them,
  and a histogram of the excess by quarters of a gap;
- `encloses`: the distribution of $r_z / r_{\min}$ (counts of ratio 1 and of $r_z/r_{\min} - 1$
  in $[2^k, 2^{k+1})$, and of $r_{\min} = 0$), its largest and smallest values, and the smallest
  slack $(r_z - r_{\min})/(r_z - \mathrm{pred}(r_z))$ in gaps of the radius: below 1, a radius one
  unit in the last place smaller would no longer enclose;
- `rounded`: counts of exact cases and of inexact ones (ties, for nearest; equal to or different
  from the rounding to nearest, for down and up), so that a conversion test that never steps is
  noticed;
- `predicate`: counts of true and false outcomes.

`--json FILE` writes all of this, with exact fractions as decimal strings; `check --merge A.json
B.json ...` merges summaries (counts add, maxima combine, coverage ranges unite).

### Claims as read

- `value` is an expression over the limb inputs: names, `+`, `-`, `*`, unary minus, `abs( )`
  and parentheses (a bare input name, as for `split`, is the identity). It may be absent or
  `null` when no entry uses it (comparisons, balls). It is compiled once per format into
  integer arithmetic at scales known in advance (a sum of limbs at scale $\eta$, a product of
  two at $\eta^2$), so that the exact value is still a Python integer.
- Inputs and outputs are limb groups or masks (`"type": "mask"`, one slot, `0` or `1`).
- `requires` is `normalized(NAME)`, `abs_ge(NAME, NAME)`, `nonneg(NAME)` or
  `power_of_two(NAME)`; `ensures` kinds are `normalized`, `error`, `leading_rounded`, `rounded`
  (`of` one 1-limb output, `mode`), `upper` (`of` one 1-limb output, `gaps` a rational),
  `predicate` (`of` one mask, `rel`, `args` two expressions over the inputs) and `encloses`
  (`center` and `radius` outputs, the radius of one limb; `balls` mapping each ball name to
  `{"center": INPUT, "radius": INPUT}` or `[INPUT, INPUT]`, the radius of one limb; `set` an
  expression over ball names and the other limb inputs, in which every ball occurs exactly once
  and `abs` does not, because only then are the corners of the box enough).
- `when` is `null`, `product_large`, or `limb_products_normal`: every product of a limb of one
  factor of the value by a limb of the other is zero or at least $2^{p-1}\eta$ in magnitude
  (the exactness condition of `mul_pow2_2`, which architecture.md's vocabulary cannot express;
  proposed as an addition).
- Anything else is never ignored. A kernel whose claims cannot be read (unknown vocabulary, a
  listed instance that disagrees with its `c` and `t`, a name listed twice) is set aside with the
  reason: the report starts with a CLAIMS ERROR line, its lines fail, and the run fails; the other
  kernels are still judged. A file that is not JSON or not schema 1 is an error (exit 2). Kernel
  fields outside the documented ones are reported as warnings. `check` with no input lines is a
  validation of a claims file.
- `of` names one output; a list of names, or `"s+e"`, concatenates outputs in that order, which is
  how a pair of 1-limb results `(s, e)` is read as one 2-limb number. Absent means all outputs.
- `instances` is a list with one object per `error` entry, in their order, each mapping a format
  to its `{rel, abs}` (the second-wave form; `[]` for a kernel without `error` entries). The
  first-wave form is still read: an object in which `instances[FORMAT]` is one `{rel, abs}`
  when the kernel has one `error` entry, otherwise a list in the order of the `error` entries;
  an `instances` object inside an `error` entry is accepted too.
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

`refrun` evaluates the first-wave kernels (and `split`), as written in architecture.md, and the
second-wave and Ball kernels, as written in milestone1.md, for any format. It avoids the
checker's code on purpose: its rounding is computed from the two neighbors of the exact
value (the checker shifts and inspects the dropped bits), `succ` and `pred` from the canonical
significand and exponent with IEEE's `nextUp` at the infinities (the checker uses bit lengths of
spacings), and where the format fits in binary64 it reads limbs with `float.fromhex` and prints
them with `float.hex`. `--list-variants` shows the injected errors.

The Ball kernels need the constants $U$ and $V$ of their center's kernel. `refrun` computes them
exactly, as architecture.md defines them ($\mathrm{unit}/(1-\mathrm{unit})$ and
$\mathrm{tiny}/(1-\mathrm{unit})$ rounded up to the format, with $\mathrm{unit} = c\,u^k$,
$\mathrm{tiny} = t\eta$), from the bounds of `add_2_2`, `mul_2_2` and `mul_2_1` in a claims file:
the first-wave fixture unless `--center-claims FILE` says otherwise. For one limb the center is
one operation, whose bound no claims entry states; `refrun` takes $|\mathrm{RN}(v) - v| \le
u|v| + t\eta$ with $t = 0$ for a sum and $t = \frac12$ for a product. `refrun --print-constants
FORMAT` prints them.

The variant `trace-mul-pow2` computes correct results and writes a comment before a line when
the pair $(h, l)$ of `mul_pow2_2` is not normalized before its final `fast_two_sum`.

The variant `trace-fast-two-sum` computes correct results and writes a comment before a line for
every `fast_two_sum` call whose first operand is smaller in magnitude than the second, saying
whether that operand is zero, whether the exponent form of the precondition holds, and whether the
call was still error-free.

`selftest/refrun.cpp` is a standalone C++ runner for binary64 and binary32, written from the same
pseudo-code. The selftest compiles it with the system compiler (`$CXX`, then `c++`, `clang++`,
`g++`, or `--cxx`) with `-std=c++17 -O2 -ffp-contract=off -fno-fast-math` (`/std:c++17 /O2
/fp:precise` for `cl` and `clang-cl`, untested so far), and skips the C++ tests with a message if
no compiler works. It has its own variants (`subnormal-flush` instead of
`subnormal-trunc`). Its `succ` and `pred` are `nextafter` toward the infinities, and it takes the
Ball constants on its command line (`--const binary64.mul_2_2.U=0x1.0000000000001p-104`, one per
format, center kernel and constant), which the selftest computes with the Python runner.

## selftest

```
python3 oracle/kairn-oracle selftest              # about 90 seconds
python3 oracle/kairn-oracle selftest --quick      # smaller samples, about 40 seconds
python3 oracle/selftest/mutants.py --jobs 6       # tests the selftest, about ten minutes
```

`mutants.py` copies the oracle into a temporary directory once per mutant, plants one deliberate
bug in the checker or the arithmetic (rounding ties away from zero, no gradual underflow,
requirements or normalization or membership of outputs not checked, a bound lenient by a factor
of two, the `when` condition ignored, ...; for the second wave, one per new check: a relation
or a direction misread, the gap taken on the wrong side of a power of two, the lower side of an
enclosure or the input radii or two of the four corners ignored, a requirement not checked,
`abs` or a minus dropped from expressions, instances read in the wrong order, a statistic
computed over the wrong cases, ...) and requires `selftest --quick` to fail on the copy.

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
| `expressions` | compiled value expressions against `Fraction` on random inputs; a malformed expression accepted |
| `rounding_directed` | rounding down and up, and the gap below a number, against a brute-force search on six toy formats, beyond $\Omega$ included |
| `claims_reading_wave2` | the second-wave fixture unreadable or inconsistent; the list and object forms of `instances` disagreeing; 27 malformed second-wave kernels not set aside |
| `gen_wave2` | an invalid generated case, a missing stratum, a comparison stream without both outcomes, a conversion stream that never steps, a correct runner flagged, case $i$ not reproducible |
| `exhaustive_wave2` | the new domains against brute-force counts, mask inputs read or written wrongly, the correct runner flagged on any case of 44 enumerations of tiny formats (the 2-limb balls on restricted radii, marked RESTRICTED) |
| `cxx_wave2` | the C++ runner flagged, or any of its second-wave results different from the Python runner's |
| `injected_wave2`, `injected_wave2_exhaustive` | an injected error not flagged where it belongs, or flagged in a kernel that does not use it |
| `judge_wave2` | a hand-written line judged otherwise than worked out by hand (masks, directions, gaps below powers of two, the corners of a product of balls, the requirements, beyond $\Omega$), or a statistic off |
| `scaled_gaps` | halved gaps passed, gaps times 1024 failed, or the largest excess in gaps moved with the claim |
| `merging_wave2` | the merge of second-wave summaries differs from the whole |

Injected errors (`refrun --list-variants`): one ulp off in the second limb in about 1 case in 256;
a result with the right value but not normalized; a product that drops a cross term; additions
that skip their last renormalization; rounding wrong only below $\lambda$; a `two_sum` whose error
term is wrong only when it should be zero; inputs altered to violate a requirement (must be
invalid, not passed); and the fixture with every bound halved (must fail) or multiplied by 1024
(must pass with ratios 1024 times smaller).

Second wave: comparisons wrong only when the first limbs are equal; `to_down_2` that forgets
its step when the second limb is negative, and one that steps by the gap on the wrong side of a
power of two; `radd` without its final step; `rmul` rounded to nearest only; Ball radii without
the center kernel's own error term, `ball_mul` without the product of the two radii; an `abs_2`
that negates only the first limb. A Ball radius one unit in the last place too small at a
power-of-two center (`ball-pow2-ulp`) is not an error with respect to the claim on the tiny
formats: the listing leaves more than one gap of slack in every case enumerated there, so the
radius one ulp smaller still encloses. The selftest demands that no verdict changes and that
the smallest slack the oracle reports drops by at least half a gap.
