# kairn-oracle

The test oracle of Kairn: it decides, in exact arithmetic, whether results produced by any
runner satisfy the claims in `gen/claims.json`. It is Python 3, standard library only, and shares
no code with the generator or the library; it reads `gen/claims.json` as data and nothing else.
The contract it implements is [docs/developer/architecture.md](../docs/developer/architecture.md)
("Number formats", "Claims", "Claims of the second wave", "Claims of the non-finite layer", "The
line protocol").

Every verdict is decided with Python integers. A limb of a format with smallest subnormal
$\eta = 2^{q_{\min}}$ is stored as the integer $N$ with value $N\eta$; sums of limbs are integers
at the same scale and products are integers at scale $\eta^2$. No floating-point operation and no
`Fraction` takes part in a verdict.

```
python3 oracle/kairn-oracle gen KERNEL FORMAT [options]      request lines
python3 oracle/kairn-oracle check [FILES] [options]          verdict and statistics
python3 oracle/kairn-oracle brute --runner CMD ... [options] parallel gen | runner | check
python3 oracle/kairn-oracle search KERNELS FORMATS [options]  the cases closest to the claims
python3 oracle/kairn-oracle shrink 'LINE' [options]          a failing case made simpler
python3 oracle/kairn-oracle refrun [--variant V]             the reference runner (Python)
python3 oracle/kairn-oracle selftest [--quick]               the oracle's own tests
```

Claims are read from `gen/claims.json` of this repository unless `--claims FILE` says otherwise.
The selftest uses its own hand-written fixtures, `oracle/selftest/claims-wave1.json`,
`oracle/selftest/claims-wave2.json` (the kernels of [Milestone 1
statements](../docs/developer/design/milestone1.md)) and `oracle/selftest/claims-wave3.json`
(the non-finite layer: the full kernels with their cores, the full Ball kernels and `ball_neg_k`,
the constructors, the kernels that gain the extended domain, `neg_2` and `abs_2` with
`represents`, and `add_1_1` and `mul_1_1`), so that it does not depend on the generator.

## gen

```
kairn-oracle gen add_2_2 binary64 --seed 7 --start 0 --count 100000
kairn-oracle gen mul_2_2 fp:5:-10:5 --exhaustive --restrict x.lead=2:2 --restrict x.sign=+
kairn-oracle gen mul_2_2 fp:5:-10:5 --exhaustive --restrict x.lead=2:2 --total
```

Formats are `binary64`, `binary32` or `fp:P:QMIN:QMAX` with $P \ge 1$ (at precision 1 the numbers
are zero and the powers of two, and a tie rounds to the even integer significand at the exponent
of the value, as in Flocq: halfway between $2^k$ and $2^{k+1}$ goes to $2^{k+1}$, and $\eta/2$ to
zero). The kernel's inputs and requirements come
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
| step | `upper` claims | `nonneg`; `tie` (sums $N2^E$ and products, factored by small primes, with $N$ odd at the rounding position, below and above powers of two and in the subnormal range); `close`. An operand under `nonneg()` is drawn as in every stratum and then loses its sign |
| scale | a `power_of_two()` input | `into` and `outof` (scalings into and out of the subnormal range); `halfscaled` ($c x_1$ rounding to exactly half a gap of $c x_0$) |
| ball | `encloses` claims | `radii` (zero, $\eta$, subnormal, tiny, about an ulp of the center, comparable, much wider than the center, huge); `wide` (small centers, wide radii); `exact` (zero radii, inexact centers); `centerpow2` (centers whose sum or product is a power of two); `cancel` |

A kernel of the extended domain (`"domain": "extended"`, the non-finite layer) keeps the strata
of its family, drawn from a finite view of the kernel (`canonical(x)` read as `normalized(x)`,
`ball(c, r)` as a normalized center and `nonneg(r)`, the core's entries in place of `extends`),
and gets strata of its own, each coming round twice per cycle (`gen3.py`):

| Stratum | Kernels | Operands |
|---|---|---|
| `nonfinite` | all | a finite case of any stratum with a random nonempty set of operands replaced: $\pm\infty$ or NaN for a limb, $(\pm\infty, \pm 0)$ or (NaN, NaN) for a 2-limb operand, $+\infty$ or NaN under `nonneg()`, the whole line or the empty set for a ball (a power of two stays finite) |
| `zeroinf` | value or set with a product | one operand infinite (sometimes NaN, or a whole line), every other a zero of random sign, a ball the exact zero ball: the $0 \cdot \infty$ corners |
| `edge` | `extends` | finite operands at which the core may overflow: leading limbs in the top two binades with random signs (so cancelling and not), $\Omega$ as either operand; for products, products near the overflow threshold and $\Omega$ times about one; a power of two that brings the other operand to the threshold |
| `threshold` | a `finite_when` condition | operands at each condition $\lvert E\rvert \le 2^{q_{\max}+p+e}$: for a name, the threshold itself with a tail toward zero, or its predecessor; for a product, the second factor rounded down from the threshold over the first; a quarter of the cases just outside one condition |
| `ballstates` | `encloses` | each ball finite, the whole line or the empty set; scalars not finite a third of the time |
| `zerowhole` | `encloses` | an exact zero ball (or a ball centered at zero) against the whole line; a zero ball against a scalar that is not finite; the whole line against a zero scalar |
| `hugeradius` | `encloses` | finite balls with radii in the top binades |
| `badradius` | `makes_ball` | radii negative, $-\infty$, NaN, $+\infty$, zero, $\eta$, huge or ordinary; centers not finite a quarter of the time |

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

In the extended domain each domain includes the non-finite values of its operand: $+\infty$,
$-\infty$ and NaN for a one-limb operand; $(+\infty, 0)$, $(-\infty, 0)$ and (NaN, NaN) for a
canonical one; $+\infty$ and NaN under `nonneg()` (a power of two stays finite). A ball, its
center and radius together, is one operand: every canonical finite center with every finite
nonnegative radius, the whole line (center 0, radius $+\infty$) and the empty set. Restrictions
shrink the finite part of a domain only; the non-finite values are always enumerated.

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
   and not judged (`--ignore-min-precision` judges it anyway). The kernel's bounds are not even
   evaluated for such a format, since they need not exist there ($3/(1 - 4u)$ at $p = 2$).
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

### The extended domain

A kernel with `"domain": "extended"` is judged by `extended.py`, and every completed line of it
is judged: nothing is "non-finite, not judged". Steps 1 and 2 are as above; then:

3. **Requirements**: every input limb is a number of the format, $+\infty$, $-\infty$ or NaN
   (anything else is invalid); `canonical(x)`: finite and normalized, or $(\pm\infty, \pm 0)$, or
   every limb a NaN; `ball(c, r)`: a canonical finite center with a finite $r \ge 0$, or center 0
   and $r = +\infty$, or every limb a NaN; `nonneg(r)`: $r \ge 0$, $+\infty$ or NaN;
   `power_of_two(c)`: a finite power of two. A one-limb input with no requirement is any value.
   A line outside them is **invalid**, never passed.
4. Every output limb must be a number of the format, an infinity or a NaN, and every mask `0` or
   `1`; otherwise **failure**.
5. Every entry, in the extended reals (a finite value is an integer at a known scale; $\infty -
   \infty$ and $0 \cdot \infty$ are NaN, as in IEEE 754). Each statement that fails is counted
   under its name (`failed F4`, `failed B2`, ...), once per line:
    - `extends` (F1 to F5 of milestone1.md): **F1** the output is canonical; **F2** if $w_0$ is
      finite, every operand is finite and every entry of the core holds (the core's entries are
      judged as for the core itself, with statistics of their own, labelled `F2, core K: ...`);
      **F3** if every operand is finite and the `finite_when` list is not empty and every
      condition holds, $w_0$ is finite; **F4** if every operand is finite and $w_0$ is not, $w$ is
      $(\pm\infty, 0)$ with the sign of the exact value (a zero value has no such sign: failure);
      **F5** if an operand is not finite, $w$ is the canonical form of `lead` applied by IEEE 754
      to the leading limbs in input order. An empty `finite_when` claims nothing about when the
      result is finite.
    - `encloses` (B1 to B4): **B1** the result is a canonical ball; then **B2** it is empty
      exactly when a ball operand is empty (a NaN radius); **B3** if it is a finite ball, every
      ball operand is finite, every scalar of the set is finite, and the set is enclosed (as
      above); **B4** as F3, with a finite ball. The whole line contains everything.
    - `represents`: the output is canonical and is the value exactly ($\pm\infty$ as
      $(\pm\infty, 0)$, NaN as all NaN).
    - `makes_ball`: empty when the given radius is NaN or negative ($-\infty$ included);
      otherwise the whole line when the given center or radius is not finite; otherwise the
      given center and radius.
    - `normalized`, `error`, `leading_rounded`: the output is canonical; the rest applies when
      every operand and the output are finite.
    - `predicate`: the relation in the extended reals, false when either side is a NaN.
    - `rounded`: for finite operands the rounding with overflow (nearest: beyond the threshold;
      down: below $-\Omega$ gives $-\infty$, above $\Omega$ gives $\Omega$; up likewise); a
      non-finite operand gives the value itself in the extended reals ($\lvert-\infty\rvert$ for
      `abs_upper_2`).
    - `upper`: NaN exactly when the value is (a NaN operand, $0 \cdot \infty$); otherwise not
      below the value, and `gaps` applies when the output is finite.

   **Suspicious**, as in the finite layer, and a failure only with `--fail-on-suspicious`: a
   non-finite result of `extends`, `normalized`, `error` or `upper` on finite operands when every
   operand and the exact value are below $\Omega/4$; and a canonical result of `normalized` or
   `error` whose value is not the kernel's value in the extended reals when an operand is not
   finite (the claim says only "canonical" there). Neither is shown for outputs that a
   `represents` entry of the same kernel pins (`neg_2` and `abs_2` carry one): that entry judges
   them on every line. A whole line from finite operands is never suspicious: the first radius
   design's steps reach $+\infty$ far below $\Omega$ on small formats (at $p = 2$ a set within
   $\pm 1.25$ becomes the whole line with $\Omega = 6$). A Ball kernel of the extended domain
   need not be a full kernel: `ball_neg_k` carries the extended `encloses` itself.

Statistics of the extended domain, per entry: the classes (`class F2: finite operands, finite
result`, `class F4: finite operands, non-finite result`, `class F5: a non-finite operand`;
`result: finite ball`, `result: whole line`, `result: empty set`; `given: ...` for
`makes_ball`; `value finite / infinite / NaN` for `represents`), how often F3 and B4 applied,
and, to choose `finite_when` thresholds:

- for results that are not finite on finite operands, the smallest $\max\lvert\text{leading
  limb}\rvert / 2^{q_{\max}+p}$ and $\lvert\text{value}\rvert / 2^{q_{\max}+p}$ (for a ball also
  the largest end of the set over $2^{q_{\max}+p}$), with the lines that attain them;
- for finite results on finite operands, the largest of the same quotients;
- for `encloses` with a finite result, the slack statistics above.

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
- The non-finite layer: `domain` is `finite` (also when absent) or `extended`. In the extended
  domain `requires` adds `canonical(NAME)` (a 2-limb input) and `ball(CENTER, RADIUS)` (a
  one-limb radius, inputs in at most one ball) and refuses `normalized()` and `abs_ge()`; every
  input of two limbs must be canonical or a ball's center; every ball of an `encloses` set must
  have its `ball()` requirement; `finite_when` is required in `extends` and in `encloses`, a
  list of `{"abs_le": EXPR, "exp": E}` with EXPR over the limb inputs and E an integer. Outside
  the extended domain `canonical()`, `ball()`, `finite_when`, `extends`, `represents` and
  `makes_ball` are refused. `extends` names a `core` that must exist, be readable, be of the
  finite domain, have the same inputs (names and limbs), outputs of the same shape (matched by
  position), the kernel's requirements with `normalized` for `canonical`, the same value (as a
  polynomial in the inputs), the same `min_precision`, and entries of the kinds `normalized`,
  `error` and `leading_rounded` only; its `lead` (`add`, `sub` or `mul`) must be the value's
  operation on the two operands, in input order for a sum or a difference. `makes_ball` takes
  `center` and `radius` outputs and `from` with the given `center` and `radius` inputs.
  `ieee_status` (`proved` or `unverified`) and `ieee_theorem` (an object) are read for form and
  never used for a verdict; a kernel of the extended domain without `ieee_status`, or `proved`
  without `ieee_theorem`, gives a warning.
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
70 000 cases per second per job. For the kinds of the second wave, `check` reads 120 000 to
200 000 lines per second for `rounded`, `upper` and `predicate`, and 45 000 to 80 000 for
`encloses` (`ball_mul_2` is the slowest); in-process `brute` on the Ball kernels of toy formats
runs at about 26 000 cases per second per job.

## search

```
kairn-oracle search mul_2_2 binary64                         # the interpreter, 20 000 cases
kairn-oracle search all binary64,binary32 --jobs 6 --json out.json \
    --fail-on-suspicious --suspicious-ok split,two_prod_dekker
kairn-oracle search mul_2_2 binary64 --runner build/tests/kairn-gen-runner
kairn-oracle search mul_2_1 binary64 --claims oracle/selftest/claims-wave1.json \
    --runner refrun:mul-drop-cross                           # a planted fault
```

An adversarial search, for each kernel and format given (`all`: every kernel with an `error`,
`upper`, `encloses` or `extends` entry), for the cases that bring the kernel closest to its claims,
or past them. It runs the kernel through a runner (`--runner`: `interp`, the generator's
interpreter, by default; `refrun[:VARIANT]`, the reference runner in this process; any command
of the line protocol, a compiled runner for example) and judges every completed line with the
checker of `check`, whose statistics of one line give the quantities the claims bound:

| Entry | Quantity | Made |
|---|---|---|
| `error` | the error over the bound it is allowed, and the observed constant $\lvert\text{err}\rvert/(u^k\rho)$ where $u^k\rho \ge 2^p\eta$ | large |
| `upper` | the excess over the exact value, in gaps of the result | large |
| `encloses` | the slack of the radius over the smallest enclosing radius, in gaps of the radius | small (below zero: not enclosed) |

A kernel of the extended domain is searched on finite operands, where `extends` applies the
entries of its core (F2); those are its quantities, and every other statement is judged on every
line as `check` judges it.

**How it searches.** Each quantity keeps an elite of the 16 best cases found (`--elite`), at most
a quarter of them descending from one seed. A generation (`--batch`, 256 cases, one runner
process) is made of children of elites, each with one to three moves: a bit of a significand
flipped (the low bits more often), a limb moved by a few units in the last place, given an
extreme significand (a power of two, all ones, and their neighbors) or another exponent, or
negated; the second limb of a pair moved to an extreme of the normalization invariant (half an
ulp of the first toward an even first limb, a quarter below a power of two, the largest value
below half an ulp, $\pm\eta$, zero); operands swapped or taken from another elite; a second operand
that nearly cancels the first (for a product, a second limb whose cross term nearly cancels the
other's); a limb set to an odd multiple of half an ulp of another (a tie); the case scaled toward
the underflow threshold, the overflow threshold or the bottom of the normal range (for a
product, one factor); a radius set as the ball strata set one; a zero given the other sign; an
operand drawn afresh; and one child in sixteen a fresh case of a stratum. Every child is then
repaired into the kernel's requirements (a pair that is no longer normalized becomes the TwoSum
of its limbs, a radius its magnitude, a power of two that of its leading bit, operands under
`abs_ge` are ordered) and kept only if the generator's own test of the requirements passes, so
that every line written is in the kernel's domain (a search that wrote one outside would stop
with an error). The first generation is the seeds: the case lines of `--seeds FILE` (a text file
of lines or any JSON summary), and by default the attaining lines of the summaries under
`results/*/brute/` and the lines of `tests/regression/cases.txt` (`--no-default-seeds` leaves
them out); the cases of the literature in `kairn_oracle/tight.py`, transcribed exactly from the
papers that give them, with the page (`--no-literature`); and eight cases of every stratum of the
kernel's family. Seeds count toward the budget (`--evals`, 20 000 cases per kernel and format).

The search is deterministic: its choices come from a keyed hash of the seed (`--seed`), kernel,
format and generation, so the same runner gives the same search, and the interpreter and the
compiled runners, which write the same bits, give the same search. A line it reports is an
ordinary completed line, which `check` judges alike. A failure (any failing entry; a suspicious
result with `--fail-on-suspicious`, but for the kernels of `--suspicious-ok`) stops the search
of that kernel and format at the end of the batch; the first three failing lines are printed with
the command that runs each again and the command that shrinks it. The exit status is 1 on any
failure. `--json FILE` writes, per kernel and format and per quantity, the best value as an exact
fraction, its line, where it came from (which seed it descends from), and the best value of the
seeds alone. With the interpreter it runs about 2 300 cases per second per process, with a
compiled runner about 13 000 (Apple M3 Max); `--jobs N` runs kernel and format pairs at once.

**What it found** (Milestone 1, 20 000 cases per kernel and format, seed 0, on the Mac; the
table is in [Testing](../docs/developer/testing.md#the-adversarial-search)). No claim was
violated. Against the extremes of the brute-force runs (13.8 billion results), over the 116
quantities of the 47 kernels in `binary64` and `binary32` that are not exact claims: with every
seed, closer to the claim on 86 and the same on 30; from the strata alone, without the
brute-force lines and the literature, closer on 66, the same on 20 and farther on 30. The
relative bound of the accurate sum (`add_2_2`, `sub_2_2` and the cores of their full kernels) is
attained to within $8.2 \cdot 10^{-16}$ in `binary64` and $4.4 \cdot 10^{-7}$ in `binary32`, by
the case with which [MR22](../docs/developer/design/phase0/references.md#mr22) show it
asymptotically optimal, where the brute-force runs had come to 0.67 to 0.75 of it; that of the
sums with one limb (`add_2_1`, `sub_2_1`, `sub_1_2`) to within $2.3 \cdot 10^{-16}$ and
$1.2 \cdot 10^{-7}$ (0.81 to 0.997 before); `mul_2_2` comes to $1 - 8.7 \cdot 10^{-9}$ of its
bound in `binary64` (0.977 before), with an observed constant of 3.99999996 against the claimed
4 (3.34 before): the search carried MR22's case, 3.997, further; and the form-A bound of
`add_fast_2_2` is attained to within $4.4 \cdot 10^{-7}$ in `binary32` (0.60 before), by a
search that started from a brute-force line, and from the strata alone for the core of
`add_fast_2_2_full`. It did not find every planted fault: a
fault of `tests/kernel_mutants.py` that breaks the radius of `ball_scale_2` only where the
correct kernel's slack is large (a zero input radius) went unseen in 100 000 cases, while the
full tier's 20 000 random ones met it once or twice.

## shrink

```
kairn-oracle shrink 'mul_2_2 binary64 -0x1.32404e4936d19p-538 ... #search:58' \
    --claims oracle/selftest/claims-wave1.json --runner refrun:mul-drop-cross
kairn-oracle shrink 'LINE' --runner build/tests/kairn-gen-runner     # no toy formats
```

Given one line that a runner fails (a request or a completed line; `-` reads it from standard
input) and that runner (`--runner`, as for `search`), `shrink` looks for a simpler case that the
same runner fails in the same way: the same `ensures` entry, and in the extended domain the same
statement (F1 to F5, B1 to B4), as judged by the checker. It lists what the line fails and keeps
the first (`--entry` chooses another). Simpler is a tuple compared in order: the limbs that are
not zero, the significant bits of every limb, the distance of every limb's exponent from zero,
the negative limbs, the negative zeros. Each round runs every one-step change of the current case
at once (an operand replaced by zero or by the power of two of its leading bit; a limb replaced
by zero, cut to its leading 1, 2, 3, 4, 6, 8, ... bits, its lowest set bit cleared, made
positive; a second limb moved toward exponent zero; an operand, or every operand together, or
for a product one factor up and the other down, scaled toward exponent zero; a negative zero made
positive), each repaired into the requirements as the search repairs, and keeps the simplest
that still fails. The tuple decreases at every step, so it ends; `--evals` (50 000) bounds the
cases it runs.

Then, unless `--no-toy`, it looks for the smallest toy format in which the runner fails the same
way: precisions from the kernel's `min_precision` up to one less than the case's, 2 to 16
exponents placed as in `binary64` ($q_{\min} + q_{\max} = 3 - 2p$; in the extended domain also
$q_{\max} \ge 1$, the shape of the IEEE-model statements), in the order of the size of their
enumeration. In each it runs the case rounded into the format, the case with each second limb kept
at the same place relative to the ulp of the first, and then every case of the format, or
`--toy-cases` random cases of every stratum (2 000) where there are more. In the first format
that fails it shrinks the simplest failing case again. A runner that runs none of the first three
toy formats (a compiled one: `binary64` and `binary32` only) leaves the step out, and the report
says so. It prints the shrunk line, its completed line and the command that runs it again;
`--json FILE` writes the same. Deterministic. A fault that depends on the text of a line rather
than its operands (the variant `ulp-rare`, which hashes the line, tag included) cannot be shrunk.

On the planted faults of the self-tests: `mul_2_2` with the cross term $x_0y_1$ dropped
(`mul-drop-cross`), from a `binary64` line of four limbs with 195 significant bits to
`mul_2_2 binary64 0x1p+0 0x0p+0 0x1p+0 0x1p-53` ($1 \cdot (1 + 2^{-53})$ loses $2^{-53}$) and to
`mul_2_2 fp:5:-5:-2 0x1.8p+0 0x0p+0 -0x1p+2 -0x1p-3`; through a compiled runner with a fault of
`tests/kernel_mutants.py` planted (the finiteness test of `add_fast_2_2_full` loosened), from the
line the search found to `add_fast_2_2_full binary64 -0x1.fffffffffffffp+1023 -0x1p+969 -0x1p+969
0x0p+0`, whose result $(-\infty, +\infty)$ is not canonical.

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

For the non-finite layer `refrun` runs, as listed in milestone1.md, the nine full arithmetic
kernels (the core, then the fix-up on the leading limbs, with `guard` on a scalar that is added
or subtracted), the eight full Ball kernels (the core, then the fix-up with `q`, the sum of the
input radii, or `rx` itself for `ball_scale`), and the constructors `make_2`, `make_2_limbs`,
`ball_make_1` and `ball_make_2`; the other kernels run on non-finite operands as listed. Its
arithmetic is IEEE's on every format: overflow to $\pm\infty$ at the format's own threshold,
NaN propagation, $0 \cdot \infty$ and $\infty - \infty$ are NaN, comparisons are false on a NaN,
`succ` of $\Omega$ is $+\infty$ and `succ` of $-\infty$ is $-\Omega$. The fix-up's
`times_inf(t)` is a NaN for a NaN or a zero and otherwise the infinity of the sign of $t$.

**The two radius designs.** `--radius first` (the default) runs the Ball cores with steps to the
next number up; `--radius second` runs milestone1.md's "The radius, second design": ordinary
operations on nonnegative values, then `fma(t, G, H)`. Its constants are computed exactly for
any format from the page's table and rounded up to the format ($+\infty$ beyond $\Omega$), from
the proved bound of the center kernel as the pages state it: $u/(1+u)$, with $\eta/2$ for a
product, for one limb (`add_1_1`, `mul_1_1`); `add_2_2`, `mul_2_2` and `mul_2_1` of
architecture.md for two. `refrun --print-constants FORMAT` prints them; `brute --radius second`
runs the in-process runner with them. The variants `ball2-no-E` and `ball2-no-H` drop a
constant (planted bugs); `ball2-G-pred` and `ball2-H-half` take $G$ one unit in the last place
smaller and half of $H$ rounded up, to measure the slack the page reports.

`selftest/refrun.cpp` is a standalone C++ runner for binary64 and binary32, written from the same
pseudo-code. The selftest compiles it with the system compiler (`$CXX`, then `c++`, `clang++`,
`g++`, or `--cxx`) with `-std=c++17 -O2 -ffp-contract=off -fno-fast-math` (`/std:c++17 /O2
/fp:precise` for `cl` and `clang-cl`, untested so far), and skips the C++ tests with a message if
no compiler works. It has its own variants (`subnormal-flush` instead of
`subnormal-trunc`). Its `succ` and `pred` are `nextafter` toward the infinities, and it takes the
Ball constants on its command line (`--const binary64.mul_2_2.U=0x1.0000000000001p-104`, one per
format, center kernel and constant; `--const binary64.ball_mul_2.G=...` for the second design,
one per format, Ball kernel and constant), which the selftest computes with the Python runner.
`--radius second` selects the second design.

## selftest

```
python3 oracle/kairn-oracle selftest              # about two minutes
python3 oracle/kairn-oracle selftest --quick      # smaller samples, about 90 seconds
python3 oracle/selftest/mutants.py --jobs 6       # tests the selftest, about fifteen minutes
```

The exhaustive tests run one worker process per CPU; `--jobs N` (or `KAIRN_ORACLE_JOBS=N`)
caps them. The times are for an Apple M3 Max with `--jobs 6`. `--only NAMES` runs only the tests
named (comma-separated), `--skip NAMES` all but those; a name that is not a test's is an error.
ctest's quick tier runs `--quick` with `--skip` for the six enumerations of toy formats
(`correct_runner_toy_exhaustive`, `injected_exhaustive`, `exhaustive_wave2`,
`injected_wave2_exhaustive`, `exhaustive_wave3`, `injected_wave3_exhaustive`), three quarters of
the time, and its full tier `--only` those six (`tests/CMakeLists.txt`). Of the mutants below, the
quick tier's part catches all but one: `exhaustive: -inf left out of a one-limb domain`, which only
an enumeration can see (`exhaustive_wave3`).

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
| `claims_reading_wave3` | the fixture of the non-finite layer unreadable or its cores not linked; a domain written out as `finite` changing a summary; 48 malformed kernels of the layer not set aside (a core missing, unreadable, of the extended domain, with other inputs, input names, outputs, value, requirements or minimum precision; a lead that is not the value's operation; `finite_when` malformed or over unknown names; `canonical()` or `ball()` misplaced; constructors with bad fields; statuses of the wrong form) |
| `extended_arithmetic` | expressions in the extended reals against Python's IEEE floats and Fractions, infinities and NaN included; comparisons; `canonical` and the ball states against their definitions on every pair and triple of limbs of `fp:2:-2:1` |
| `gen_wave3` | an invalid generated case, a missing stratum, a class of a statement never reached (F2, F4 and F5 for every full kernel; finite, whole and empty results for every Ball kernel; each given state for the constructors; non-finite operands of both outcomes for the comparisons), a `threshold` stratum mostly outside its conditions, the correct runner flagged or suspicious, case $i$ not reproducible |
| `exhaustive_wave3` | the domains with their non-finite values against brute-force counts, restrictions that drop non-finite values, the correct runner flagged on any case of 37 enumerations of tiny formats (of the IEEE shape $q_{\min} + q_{\max} = 3 - 2p$, the 2-limb balls on restricted radii) |
| `cxx_wave3` | the C++ runner flagged, or any of its results on the layer different from the Python runner's |
| `injected_wave3`, `injected_wave3_exhaustive` | a planted bug of the layer not caught in the statement where it belongs, caught in another, or flagged in a kernel that does not use it |
| `judge_wave3` | one of 144 hand-written lines judged otherwise than worked out by hand (each failure in its statement), or a class count or an overflow position off |
| `merging_wave3` | the merge of summaries of the layer differs from the whole |
| `radius_second` | a constant $E$, $G$ or $H$ of the second radius design other than worked out by hand from the page's table (binary64 and a $p = 3$ format), `ball_sub_k` with other constants than `ball_add_k`, either radius design flagged on the same streams |
| `precision_one` | at precision 1: rounding (ties by the definition), directed rounding, neighbors, membership or normalized pairs different from brute force; a kernel proved from precision 1 invalid, flagged or unjudged at random or on every operand; a format below a kernel's minimum precision setting the kernel aside |
| `search_finds_planted` | the search, through the reference runner with each of eight planted faults (an error term, a dropped cross term, a rounding below $\lambda$, a skipped renormalization, a step left out, a radius without a term, an infinity of the wrong sign, a radius without $E$), not failing within 2 000 cases, failing another entry than the fault's, or reporting a line that the checker, on its own, passes |
| `search_correct_runner` | the search failing the correct runner on seven kernels of every kind it measures; a quantity it reports other than the checker's for the reported line; the same seed giving two searches, or two seeds the same |
| `search_moves_valid` | a child of the search's moves, once repaired, outside the requirements of its kernel (pairs, radii, powers of two, `abs_ge`, balls) |
| `shrink_planted` | a shrunk line of four planted faults that the checker passes, that fails another entry, that is not simpler, or that two runs disagree on; no toy format found where the fault exists in one; a line that passes shrunk at all |

The Ball kernels of the non-finite layer run with the second radius design in these tests (the
design their IEEE-model statements are proved with); the second wave's tests run the first.

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

The non-finite layer, each planted bug with the statement that must catch it (and no other):

| Variant | Kernels | Caught in |
|---|---|---|
| `full-no-fixup`: the core's raw output | full kernels | F4 and F5 (F1, F2 allowed) |
| `full-overflow-sign`: the infinity of the wrong sign on overflow | full kernels | F4 |
| `full-overflow-nan`: (NaN, NaN) where an infinity is due | full kernels | F4 |
| `full-overflow-finite`: $(\pm\Omega, 0)$ when the core overflowed | full kernels | F2 (the core's error entry) |
| `full-spurious-overflow`: an infinity whenever $\lvert t\rvert \ge 2^{q_{\max}+p-3}$ | `add_2_2_full`, `mul_2_2_full` | F3; suspicious, not failed, in the kernels that claim no condition |
| `full-inf-tail-nan`, `full-inf-tail-eta`: a NaN or nonzero tail after an infinity | full kernels | F1 (F4, F5 allowed) |
| `full-nan-one-limb`: (NaN, 0) | full kernels | F1 (F5 allowed) |
| `full-nan-to-zero`: (0, 0) for a NaN result | full kernels | F2 and F5 |
| `ball-full-swap`: the empty set and the whole line swapped | full Ball kernels | B2 |
| `ball-full-zero-inf-empty`: `q` from the computed radius, so $0 \cdot \infty$ gives the empty set | products and scalings of balls | B2 |
| `ball-full-finite-whole`: a finite center kept with the radius $\Omega$ | full Ball kernels | B3 |
| `make-negative-radius`, `make-nan-radius`: the radius tested for NaN only, or not at all | `ball_make_1`, `ball_make_2` | `makes_ball` |
| `make2-inf-nan-tail`: `make_2` of an infinity with a NaN tail | `make_2` | `represents` |
| `ball2-no-E`: the second design without $E$ | one-limb full Ball kernels; $G$ rounded up has room for the missing term at low precision (a 2-limb center at $p = 4$; `ball_mul_1` on every case of `fp:2:-2:1` and `fp:3:-3:0`), so the exhaustive test takes `ball_mul_1` at `fp:3:-4:1` | B3 |
| `ball2-no-H`: the second design without $H$ | products and scalings of balls | B3 |
