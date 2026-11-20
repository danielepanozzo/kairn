# kairn-oracle

The test oracle of Kairn: it decides, in exact arithmetic, whether results produced by any
runner satisfy the claims in `gen/claims.json`, and whether the results of `kairn::rational` are
the ones its specification fixes ([rational](#rational)). It is Python 3, standard library only,
and shares no code with the generator or the library; it reads `gen/claims.json` as data and
nothing else. The contract it implements is
[docs/developer/architecture.md](../docs/developer/architecture.md) ("Number formats", "Claims",
"Claims of the second wave", "Claims of the non-finite layer", "Claims of Milestone 2", "The line
protocol").

Every verdict is decided with Python integers. A limb of a format with smallest subnormal
$\eta = 2^{q_{\min}}$ is stored as the integer $N$ with value $N\eta$; sums of limbs are integers
at the same scale and products are integers at scale $\eta^2$. No floating-point operation takes
part in a verdict, and no `Fraction` but in those of `rational_K`, whose answer is the rounding
of a fraction.

```
python3 oracle/kairn-oracle gen KERNEL FORMAT [options]      request lines
python3 oracle/kairn-oracle gen rational_K FORMAT [options]  requests of kairn::rational (K = 1, 2)
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
`represents`, and `add_1_1` and `mul_1_1`) and `oracle/selftest/claims-wave4.json` (the first
kernels of [Milestone 2](../docs/developer/design/milestone2.md): `next_up`, `next_down`,
`two_sum_ord`, the directed sums and products, the scalings of a ball by a power of two and their
full forms, the same claims of `neighbor` and of the products in the finite domain as
`next_up_real`, `next_down_real`, `mul_down_real` and `mul_up_real`, a `bound` alone in that
domain as `mul_down_bound_real`, and `mul_pow2_2` with an `exact_when` on its error), so that it does not depend on the generator.

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

The `threshold` stratum also aims at a condition $\lvert E \cdot c\rvert \le 2^{q_{\max}+p+e}$ with
$c$ a power of two and $E$ any expression ($(\lvert c_x\rvert + r_x)\,c$ of the scaling of a ball):
it takes the largest $c$ inside, or twice it.

The first kernels of [Milestone 2](../docs/developer/design/milestone2.md) ("Building blocks on T",
"Scaling a ball by a power of two") get families of their own (`gen4.py`), chosen from claims that
no earlier kernel has: `neighbor` for a `neighbor` entry, `dirprod` for a `bound` entry or a
directed `rounded` entry of a value `NAME * NAME`, `dirsum` for a directed `rounded` entry of
`NAME + NAME` or `NAME - NAME`, `ballpow2` for an `encloses` set that multiplies a ball by a
`power_of_two()` input. Each has the common strata, read for its shape (for the products:
`underflow` from below $\eta$ to past $P = 2^{2p-1}\eta$, `overflow` near and beyond the threshold,
`zero` a zero factor with zero, $\eta$, $\Omega$, $\lambda$, one or a random operand), and strata of
its own, which come round two or three times per cycle; a kernel of the extended domain gets
those of the non-finite layer on top. The first two waves, the non-finite layer and `two_sum_ord`,
`two_sum_entry`, `fast_two_sum_entry` and `radd_entry` (whose claims are of the earlier kinds)
keep their families and strata.

| Family | Kernels | Strata of its own |
|---|---|---|
| `neighbor` | `next_up`, `next_down` | `special` (zeros, $\pm\eta$, $\pm 2\eta$, $\pm 3\eta$, $\pm\lambda$ and its neighbours, $\pm 2\lambda$ and its predecessor, $\pm\Omega$ and its predecessor, $\pm 2^{e_{\max}}$, $\pm 1$); `binade` (powers of two of the whole range, subnormal ones included, and their two neighbours); `subnormal` ($\lambda$, $\mathrm{pred}(\lambda)$, $\mathrm{succ}(\lambda)$, $2\lambda$, $\mathrm{pred}(2\lambda)$, random subnormal numbers) |
| `dirsum` | `add_down_1`, `add_up_1`, `sub_down_1`, `sub_up_1` and their entry forms | `apart` (the smaller operand below half an ulp of the larger, around it, or far below); `cancel` ($b$ within three ulps of $-a$, of $a$ for a difference, at powers of two a third of the time); `exact` (short significands at nearby exponents: sums that are numbers of the format); `close` (exponents within $p + 2$); `beyond` (sums beyond $\pm\Omega$: top binades of one sign, $\Omega$ plus half its ulp, a quarter of it, $\eta$, its ulp); `omega` ($\pm\Omega$ with $\pm\Omega$, its predecessor, its ulp, a small, random, top or zero operand, in either position) |
| `dirprod` | `mul_down_1`, `mul_up_1` | `aroundp` (products exactly $P$, as powers of two; a factor $a$ and $b$ one of $\mathrm{RD}(P/a)$, its successor or two, its predecessor: just below and just above $P$, exact and inexact; and a product below $P$ whose rounding to nearest is $P$ when there is one); `tiny` (products of exactly $\eta/2$, $\eta$, $2\eta$, and around them: underflow to zero or to $\eta$); `exactprod` (short significands anywhere, the subnormal range included); `beyond` (products beyond $\pm\Omega$; $\Omega$ times one and its neighbours) |
| `ballpow2` | `ball_mul_pow2_1`, `ball_mul_pow2_2` and their full forms | `atnormal` ($c = 2^k$ and the scaled leading limb, second limb or radius exactly $\lambda$, its successor or predecessor before scaling); `sides` ($c$ = 1/4, 1/2, 1, 2, 4, or up to $2^{\pm p}$); `into` (centers and radii scaled into the subnormal range); `outof` (subnormal ones scaled out of it) |

In 6 000 cases of seed 0 in `binary64` (the quick tier's), `next_up` has 91 to 277 operands of each
special row of the table ($\pm\eta$, $\pm\Omega$, $\pm\infty$, NaN) and 520 zeros; `add_down_1` 505
sums above $\Omega$ and 547 below $-\Omega$; `mul_down_1` 678 results one step beyond the rounding
and 1 696 cases where `product_large` does not hold; `ball_mul_pow2_2` fails each of its three
conditions of exactness 1 252 to 1 849 times and holds them all 2 719 times.

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
Lines of `rational_1` and `rational_2` are judged as [rational](#rational) says. For each other
line, in this order:

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
   range unbounded above exceeds $\Omega$ (for a `rounded` entry with `when`, only where its
   condition holds), an `upper` entry's smallest upper bound does, a `bound` entry's directed
   rounding does, or a `neighbor` entry's operand is $\pm\Omega$ stepped outward, which has no next
   number in this domain (counted again as "with an exact result beyond Omega").
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

   and those of [Milestone 2](#the-kinds-of-milestone-2) (`neighbor`, `bound`, `rounded` with
   `when`, `exact_when` on `error` and `encloses`).

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

### The kinds of Milestone 2

architecture.md, "Claims of Milestone 2", read with milestone2.md, "Notation and vocabulary",
"Building blocks on T" and "Scaling a ball by a power of two" (`check.py` and `extended.py`, with
the helpers of `directed.py`). *Rounded down in the format with overflow*, $\mathrm{RD}$, is the
largest number not above the value, $\Omega$ above $\Omega$ and $-\infty$ below $-\Omega$;
$\mathrm{RU}$ symmetrically; a *step* is to the next number of the format above or below, and in the
extended domain a step outward from $\pm\Omega$ is the infinity and a step from an infinity is the
table's.

- **`neighbor`** (`of` one one-limb output, `side` `up` or `down`; `value` must be the name of a
  one-limb input). The expected output is the table of next_up and next_down, row by row: a NaN
  for a NaN, $+\infty$ up and $\Omega$ down from $+\infty$, $-\Omega$ up and $-\infty$ down from
  $-\infty$, $+\infty$ up from $\Omega$ and $-\infty$ down from $-\Omega$, and for any other
  finite number the smallest number above it or the largest below (so from either zero
  $\pm\eta$, and to a zero from $\mp\eta$, of either sign: the sign of a zero is not judged). The
  output must be exactly that value. In the finite domain the step outward from $\pm\Omega$ is not
  a number of the format, and the line is non-finite, not judged.
- **`rounded`, of a value of two operands** (`NAME op NAME`), in the extended domain: on finite
  operands the rounding in the format with overflow (for `down`, a value above $\Omega$ gives
  $\Omega$ and one below $-\Omega$ gives $-\infty$); with an infinite or NaN operand the value of
  IEEE 754, computed in the extended reals: a NaN for a NaN operand, $\infty - \infty$ and
  $0 \cdot \infty$, otherwise the infinity. This is the reading the non-finite layer already had
  for `rounded`; what is new is the statistics below.
- **`rounded` with `when: product_large`**: on finite operands, judged only when the value is zero
  or at least $2^{2p-1}\eta$ in magnitude, and then as `rounded` (in the format with overflow in the
  extended domain); otherwise nothing is claimed and the line counts for the entry as "does not
  hold". With an infinite or NaN operand, as without `when`.
- **`bound`** (`side` `below` or `above`, `steps` an integer $\ge 0$): `below` on finite
  operands: the output is not above the value, and stepping down from $\mathrm{RD}(\text{value})$
  reaches it within `steps` steps; `above` symmetrically from $\mathrm{RU}$. In the extended domain
  the rounding is in the format with overflow and the steps are those of that format (so a value
  below $-\Omega$ allows only $-\infty$ below it, and a value above $\Omega$ allows $\Omega$ or its
  predecessor for `steps: 1`); a NaN output on finite operands fails. With an infinite or NaN
  operand the output must be the value of IEEE 754, as for `rounded`. In the finite domain the
  format is unbounded above, and a directed rounding beyond $\pm\Omega$ makes the line non-finite.
- **`exact_when`** on `error` and on `encloses`: a list of conditions
  `{"zero_or_abs_gt": EXPR, "than": K}` (EXPR $= 0$ or $\lvert\mathrm{EXPR}\rvert > K$) or
  `zero_or_abs_ge` ($\ge K$), decided with integers: EXPR over the inputs and their limbs
  `NAME[I]` is an integer at a known scale, and K is evaluated exactly (`claims.eval_const`:
  integers, `u`, `eta`, `+ - * /`, parentheses, integer powers `^`, possibly negative; a unary
  minus binds less tightly than `^` and `^` groups to the right) for each format and must be
  positive there. On `error`, when every condition holds, the output limbs must sum to the value
  exactly, whether or not the entry's `when` holds; on `encloses`, when every condition holds, the
  output ball must be the set exactly: $c - r$ and $c + r$ its least and greatest values, besides
  containment. In the extended domain both apply when the operands and the output are finite (for
  a ball: a finite ball from finite operands, so that B1, B2 and B4 are judged as before and the
  exactness, counted as the statement `exact_when`, comes after B3). A failure of either is
  counted as `failed exact_when` in the entry, next to `failed containment` (`failed B3` in the
  extended domain) or `failed bound` for the other half of the entry.

Readings that the documents leave open, and the one taken:

- `exact_when` on an `error` entry that also has `when`: judged on its own, whether or not `when`
  holds (no claim has both; the formal reading "adds a conjunct" fits either).
- `exact_when` on `encloses` with an empty set (a negative input radius in the finite domain,
  which every `nonneg()` excludes): counted, not judged.
- A `rounded` entry with `when` on a rounding to nearest, and an empty `exact_when` list, are
  refused as claims (the vocabulary gives `when` to the directed roundings, and says that
  `exact_when` is absent when there is no condition); `"when": null` on `rounded` is read as no
  condition.
- The sign of a zero is never judged: `next_down(-eta)` may be $-0$ or $+0$, `add_down_1(1, -1)`
  either zero, a zero factor's product either zero.

Statistics, per entry: for `neighbor` the row of the operand (`row: a NaN`, `row: +inf`,
`row: Omega`, `row: positive finite`, `row: eta`, `row: zero`, `row: -eta`,
`row: negative finite`, `row: -Omega`, `row: -inf`; a positive or negative finite number is one
of no other row) and the steps where the spacing changes (`a step toward zero from a power of two
above the smallest normal number`, `a step between the subnormal and the normal range`); for a
`rounded` entry of two operands in the extended domain `overflow: value above Omega`,
`overflow: value below -Omega`, `a NaN operand`, `an infinite operand, no NaN operand` and
`value NaN from operands that are not NaN`, next to `exact`, `inexact, = RN` and
`inexact, != RN`; with `when`, `product_large holds` and `product_large does not hold (nothing
claimed)`; for `bound` `at the directed rounding`, `one step beyond the directed rounding`,
`K steps beyond ...`, `value a number of the format`, `value not a number of the format`, the
overflows and the classes of operands that are not finite; for `exact_when`, `exact_when holds`
and, for each condition that fails, `exact_when fails: ` followed by the condition (`cx[1]*c = 0
or |cx[1]*c| > eta/(2*u)`). The cross-checks' guards read these.

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
- Milestone 2: `neighbor` (`of` one 1-limb output, `side` `up` or `down`, the value the name of a
  one-limb input), `bound` (`of` one 1-limb output, `side` `below` or `above`, `steps` a JSON
  integer $\ge 0$, not a boolean), `when` on a directed `rounded` entry (`product_large` only, or
  absent or `null`), and `exact_when` on `error` and `encloses` (a nonempty list of conditions,
  each exactly one of `zero_or_abs_gt` and `zero_or_abs_ge` with `than`; EXPR in the language of
  `value` with `NAME[I]`, I below the input's limbs, which no other expression may use; K
  positive, checked in `binary64` when the claims are read and in every format a plan is made
  for, where a K that is not positive sets the kernel aside with a CLAIMS ERROR).
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

## rational

```
kairn-oracle gen rational_2 binary64 --seed 0 --count 6000
kairn-oracle gen rational_1 binary32 --seed 0 --start 1234 --count 1
kairn-oracle gen rational_2 fp:4:-6:4 --seed 0 --strata tie1,tail
```

`rational_1` and `rational_2` are `kairn::rational<X>(num, den)` for a type `X` of one limb and of
two (the specification is `docs/developer/design/milestone2.md`, "Constants at compile time").
They are not kernels of `gen/claims.json`: the specification fixes every bit of the result, so
the oracle computes the answer itself, in exact rationals (`Fraction`), and compares a runner's
for **equality** (`rational.py`). With $q = num/den$ and $\mathrm{RN}$ the rounding of the format
to nearest, ties to the even significand, with gradual underflow:

| Field | Expected |
|---|---|
| limb (`rational_1`) | $\mathrm{RN}(q)$ |
| limbs (`rational_2`) | the normalized pair $(z_0, z_1)$ whose value is $V = \mathrm{RN}(q) + \mathrm{RN}(q - \mathrm{RN}(q))$: $z_0 = \mathrm{RN}(V)$, $z_1 = V - z_0$ |
| error | the smallest number of the format not below $\lvert\text{value} - q\rvert$; zero when exact |
| exact | `1` exactly when $\text{value} = q$ |
| $den = 0$ | every limb NaN, error $+\infty$, exact `0` |

The pair is unique: a normalized pair has $z_0 = \mathrm{RN}(z_0 + z_1)$, so its leading limb is
the rounding of its value, $\mathrm{RN}(V)$, and its second limb is $V - \mathrm{RN}(V)$. That
pair exists, because $V$ is the exact sum of two numbers of the format and the error of rounding
such a sum is a number of the format. It is the naive pair $(\mathrm{RN}(q), \mathrm{RN}(q -
\mathrm{RN}(q)))$ except near a midpoint of two neighbours: when $q$ is just off the midpoint on
the side of the neighbour with the odd significand, $\mathrm{RN}(q)$ is that neighbour, the
remainder rounds to exactly half a gap, $V$ is the midpoint, and $\mathrm{RN}(V)$ is the even
neighbour. In `binary64`, $q = (2^{62} + 511)/(2^{62} - 1) = 1 + 2^{-53} + 2^{-115} + \cdots$
rounds to $1 + 2^{-52}$ with the remainder $-2^{-53}$, and the answer is $(1, 2^{-53})$ with
error $2^{-115}(1 + 2^{-52})$.

Terms are signed 64-bit integers, so $\lvert q\rvert$ is zero or between $2^{-63}$ and $2^{63}$:
in `binary64` and `binary32` the value never overflows. In a toy format it can, and the oracle
then expects the canonical infinity of the sign of $q$, $(\pm\infty, 0)$, with error $+\infty$ and
exact `0`, the page's rule for a wider argument type: when $\mathrm{RN}(q)$ overflows, and for
`rational_2` also when $\mathrm{RN}(q)$ is finite but $\mathrm{RN}(V)$ is not (no normalized pair
has the value $V$ then). A value that rounds to zero is zero, with the error rounded up (to $\eta$
at least).

**Lines.** A request is `rational_K FORMAT NUM DEN #STRATUM:INDEX`; the runner echoes it and
appends ` -> L0 [L1] ERROR EXACT`, the limbs and the error as hexadecimal literals (`nan`, `inf`,
`-inf` and their other spellings, as for the kernels), EXACT `0` or `1`. The generator writes a
header and a trailer as for the kernels (`mode=random`); there is no exhaustive mode (`gen
--exhaustive` is refused): the `small` stratum enumerates every pair of small terms instead.

**Strata**, counter-based as the kernels' random mode, by the schedule `small tie1 random tie2
pow2 tie1 exact tail small tie1 random tie2 extreme tie1 tail den0`, so that a run of $N$ cases
has $N/8$ cases of `small`, `random`, `tie2` and `tail`, $N/4$ of `tie1`, and $N/16$ of
`pow2`, `exact`, `extreme` and `den0` (750, 1 500 and 375 of 6 000):

| Stratum | Terms |
|---|---|
| `small` | every pair with $den \ne 0$, in order of $\max(\lvert num\rvert, \lvert den\rvert) = 1, 2, \dots$: a run of $N$ cases covers every pair with both terms up to 13 for $N = 6\,000$, 24 for $N = 20\,000$ |
| `random` | each term of a bit length uniform in 0 to 63 (1 to 63 for $den$), a random sign, $-2^{63}$ one time in 32, and an eighth of the cases over a common factor |
| `pow2` | $\pm(2^k + \delta)$, $0 \le k \le 63$, $\lvert\delta\rvert \le 3$, within the range; one term random a quarter of the time |
| `extreme` | first every pair of $-2^{63}$, $-2^{63} + 1$, $2^{63} - 1$, $2^{63} - 2$, $\pm 1$, $\pm 2$, $\pm 3$, $\pm 2^{62}$, $2^{53} + 1$, $-(2^{24} + 1)$, $2^{62} + 1$ (and 0 as a numerator): 240 cases; then one of them with a random term, $den = \pm 1$, $num = 0$ |
| `den0` | $den = 0$, the numerator zero, extreme or random |
| `exact` | $q = M\,2^E$ exactly, $M$ odd of at most $Kp$ bits (and 63; for `rational_2` sometimes a far power of two added), inside the format, over a common odd factor half of the time |
| `tie1` | near a midpoint $A/2^j$ of two neighbours: $num\,2^j - A\,den = t$, solved by the extended Euclidean algorithm, so that $q$ is $t/(den\,2^j)$ from the midpoint. Half the cases aim at a pair the naive way does not normalize: $t = \pm 1$ toward the neighbour with the odd significand and $den$ as large as the terms allow, in the binades where that makes the remainder round to exactly half a gap ($2^{-8}$ to $2^{7}$ in `binary64`, $2^{-37}$ to $2^{36}$ in `binary32`); the others $t$ from $-3$ to 3 ($t = 0$: an exact tie), either side, any binade; neighbours at powers of two and near the top of a binade among them. Where $2^j$ is too large for a denominator, the closest fraction on the side of $t$, from the continued fraction of the midpoint |
| `tie2` | near $a + m$, $a$ a number of the format and $m$ a midpoint of two neighbours just below half a unit of $a$ (or, a quarter of the time, a number there), of either sign: near a tie of the second rounding, or of the rounding up of the error. In `binary32` $num\,2^j - A\,den = t$ with $t$ from $-2$ to 2 ($t = 0$: an exact tie of the second rounding); in `binary64` the point has more bits than a term holds, and $q$ is the closest fraction on a side, in the binades $2^{-13}$ to $2^{12}$ where that is within $2^{-6}$ of a unit of the second limb |
| `tail` | the closest fraction to a number of the format, mostly in the lowest binades, so that $q$ is about $2^{-126}$ from it and the second limb of a `binary32` pair is often subnormal; a quarter of the cases exactly a number with few bits (second limb zero) |

**Judging**, line by line: the format must parse and the request have two terms (otherwise a
failure); each term must be a decimal integer from $-2^{63}$ to $2^{63} - 1$, or the line is
**invalid** (counted, shown, never passed); the line must have the arrow and $K + 2$ fields, every
limb and the error a number of the format or a non-finite literal, and EXACT `0` or `1` (otherwise
a failure). Then every field is compared with the expected one: limbs and error by value, so the
sign of a zero is free (the design pages never state it), an infinity only with the same infinity,
a NaN only with a NaN (of any sign). A line with any field different is a **failure**, counted in
the entry of that field (`limbs`, `error`, `exact`), and its example in the report shows what it
returned and what was expected. Every line is judged, NaN and infinities included: nothing is
"non-finite, not judged" and nothing is suspicious.

**Stream.** Besides the count of lines between header and trailer, which catches a dropped or
added line as for the kernels, every completed line under a header of `rational_K` must begin with
the request the generator wrote for its index, which `check` writes again from the header (kernel,
format, seed, strata): a line the runner changed, or lines dropped and repeated, or reordered,
are a stream error even when the count is right. A stream may mix kernels and `rational_K`, each
under its own header; their statistics are kept apart, by kernel, format and tag.

**Statistics**, per (kernel, format, tag) as for the kernels, with three entries: the limbs, the
error and the flag. The first counts the classes of the judged cases: `exact`, `inexact`,
`den = 0`, `first rounding a tie` ($q$ a midpoint), `second rounding a tie` (the remainder a
midpoint; `rational_2`), `naive pair not normalized` (`rational_2`), `second limb subnormal`
(`rational_2`), `value beyond the range` and `value zero, q not zero` (toy formats); the second
the errors that are zero, subnormal, normal and $+\infty$; the third the flags. The cross-checks'
guards read these (`tests/crosscheck_guards.py`). In 6 000 cases of seed 0, `rational_2` has
817 pairs that the naive way does not normalize in `binary64` and 1 087 in `binary32`, where 216
second limbs are subnormal and 75 cases are ties of the second rounding; there are no such ties in
`binary64`, where a fraction of 64-bit terms is never a midpoint of the second limb. `check` reads
about 30 000 lines of `rational_K` per second, the echo included.

`brute`, `search` and `shrink` do not run `rational_K`.

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
`add_fast_2_2_full`. A longer run, 1 000 000 cases per kernel and format through a compiled
runner, violated nothing either and brought `mul_2_2` to within $1.9 \cdot 10^{-15}$ of its bound
and `add_fast_2_2` to within $8.1 \cdot 10^{-16}$ of its, in `binary64`. It did not find every
planted fault: a
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

**rational_1 and rational_2.** `refrun` completes the requests of `kairn::rational` as well, from
the specification and not from the checker's code: its rounding to nearest takes the smallest
number of the format not below $\lvert x\rvert$ and the one before it and compares the distances
(the checker divides and inspects the remainder), and its pair is the one of the three candidates
$(z_0, V - z_0)$, $z_0 = \mathrm{RN}(q)$ or a neighbour, that its own addition leaves normalized.
Its variants plant one fault each: `rat-lead-ulp` and `rat-tail-ulp` (a limb one unit in the last
place too large in about one line in four), `rat-naive-pair`, `rat-error-small` and
`rat-error-large` (the error one number too small or too large), `rat-exact-flip`,
`rat-den0-finite` (zero limbs for $den = 0$), `rat-tie-away` and `rat-truncate` (in every rounding
to nearest, the renormalization's included: at an exact tie $V = q$ whichever neighbour the
first rounding took).

**Milestone 2.** `refrun` runs the kernels of milestone2.md's "Building blocks on T" and "Scaling a
ball by a power of two" as listed there, on IEEE values: `next_up` and `next_down` (its own
`nextUp`, from the canonical significand), `two_sum_ord` (Fast2Sum on the operands ordered by two
selects), `add_down_1`, `add_up_1`, `sub_down_1` and `sub_up_1` (the test of the sign of the error
term and a step), `mul_down_1` and `mul_up_1` (`two_prod`, the constant $P$ rounded up, the tests of
the listing), the entry forms (both operands through `guard`), `ball_mul_pow2_1` and
`ball_mul_pow2_2` (the products, `fast_two_sum`, the tests against $N$, two steps up when not
exact) and their full forms (the fix-up of `ball_scale`, with `q` the input radius); and the
fixture's `next_up_real`, `next_down_real`, `mul_down_real`, `mul_up_real` as the same code. Its
variants plant one fault each: `next-up-neg-away` (`next_up` of a negative number away from zero),
`next-up-ninf` ($-\infty$ for $-\infty$), `next-down-zero` ($-0$ for a zero), `dir-sum-nearest`
(the directed sums return the rounding to nearest), `dir-sum-overflow-inf` (the infinity of the
rounded sum at an overflow: $+\infty$ for rounding down above the range), `mul-bound-wrong-side`
(the products step the other way), `mul-bound-two-beyond` (two steps where they cannot decide),
`mul-large-step` (a step whenever the computed error is zero, above $P$ too), `pow2-radius-small`
(the radius one number smaller), `pow2-grow-exact` (two steps where the scaling is exact),
`pow2-zero-radius-grows` (a zero radius taken as not exact), `pow2-center-off` (the center one unit
off where the scaling is exact, the radius widened to keep the set enclosed) and
`pow2-scale-eta` (`mul_pow2_2` with $\eta$ more in its second limb where its products are exact,
within its bound of $\eta$).

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
python3 oracle/kairn-oracle selftest              # about three minutes
python3 oracle/kairn-oracle selftest --quick      # smaller samples, about 90 seconds
python3 oracle/selftest/mutants.py --jobs 6       # tests the selftest, about fifteen minutes
```

The exhaustive tests run one worker process per CPU; `--jobs N` (or `KAIRN_ORACLE_JOBS=N`)
caps them. The times are for an Apple M3 Max with `--jobs 6`. `--only NAMES` runs only the tests
named (comma-separated), `--skip NAMES` all but those; a name that is not a test's is an error.
ctest's full tier runs it in two parts: `--quick` with `--skip` for the six enumerations of toy
formats (`correct_runner_toy_exhaustive`, `injected_exhaustive`, `exhaustive_wave2`,
`injected_wave2_exhaustive`, `exhaustive_wave3`, `injected_wave3_exhaustive`) with the build's
compiler (`full.tools.kairn-oracle.selftest`), and `--only` those six, three quarters of the time
(`full.kairn-oracle.selftest`), which run in Python alone (`tests/full/CMakeLists.txt`). The
enumerations of Milestone 2 (`exhaustive_wave4`, `injected_wave4_exhaustive`) take under two
seconds with `--quick` and stay in the first part. Of the mutants below, the first part catches
all but one: `exhaustive: -inf left out of a one-limb domain`, which only an enumeration can see
(`exhaustive_wave3`).

`mutants.py` copies the oracle into a temporary directory once per mutant, plants one deliberate
bug in the checker or the arithmetic (rounding ties away from zero, no gradual underflow,
requirements or normalization or membership of outputs not checked, a bound lenient by a factor
of two, the `when` condition ignored, ...; for the second wave, one per new check: a relation
or a direction misread, the gap taken on the wrong side of a power of two, the lower side of an
enclosure or the input radii or two of the four corners ignored, a requirement not checked,
`abs` or a minus dropped from expressions, instances read in the wrong order, a statistic
computed over the wrong cases, ...; for `rational_K`, the naive pair expected, the error rounded
to nearest, ties away from zero, a binade misread, overflow at twice $\Omega$, the flag never 1,
zero limbs for $den = 0$, anything equal to a NaN, a field not compared, a term beyond 64 bits
accepted, the echo of requests not checked, near-ties never aimed at a pair to renormalize; for
the kinds of Milestone 2, up and down swapped, a row of the table changed, an output not compared,
a step more allowed, the steps of a bound taken toward the value, the rounding up above $\Omega$
kept finite, the condition of `when` ignored or its threshold halved, the classes of operands or
of overflows miscounted, `exact_when` not judged, a strict condition read as $\ge$, a zero that
does not satisfy a condition, a limb reference read as the leading limb, `eta` read as `u`, a
threshold that is not positive accepted, the value of `neighbor` not checked, a stratum aimed
elsewhere) and requires `selftest --quick` to fail on the copy. The test of the side of a `bound`
alone has no mutant: an output on the wrong side is not reached by the steps outward from the
directed rounding either, and fails there.

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
| `rational_rounding` | the rounding of rationals of the judge (to nearest and up, and whether a case is exact or a tie) or of the reference runner other than a brute-force search over every number of six toy formats (precision 1 included), on every multiple of $\eta/3$, $\eta/5$ and $\eta/7$, beyond the overflow threshold too |
| `rational_toy_brute` | an answer of `rational_1` or `rational_2` other than one from the definitions alone, for every pair of terms up to 24 (40 without `--quick`) in six toy formats: the pair found by enumerating every pair of numbers of the format and keeping the normalized ones, which must be exactly one for every finite value; a class (a renormalized pair, a tie of either rounding, overflow, underflow, a subnormal second limb) never met |
| `rational_hardware` | a `binary64` answer of the generator's streams other than CPython's correctly rounded division of integers with the machine's addition (Fast2Sum for the pair, `math.nextafter` for the error) |
| `rational_page_bounds` | on the generator's streams in `binary64` and `binary32`, a case beyond the consequences the design page states ($\lvert\text{value} - q\rvert \le \frac{u}{1+u}\lvert q\rvert$ for one limb, $\le u^2\lvert q\rvert$ for two, with no term for underflow), a subnormal leading limb, or an error that is zero when the flag is not 1 |
| `rational_judge` | one of 69 hand-written lines judged otherwise than worked out by hand: right answers in every spelling of a zero, a NaN or an infinity, wrong ones failing in their field alone (a limb one unit off, the naive pair, the error rounded to nearest or one step up, the flag, $den = 0$, a tie away from even, truncation, an overflow), malformed lines, invalid requests |
| `rational_gen` | a term outside the 64-bit range, a tag out of the schedule, $den = 0$ outside its stratum, case $i$ alone other than in its run, a seed that does not matter, a turn of the schedule without every stratum, the `small` stratum out of order or not covering its pairs, too few renormalized pairs (`binary64`, `binary32`), subnormal second limbs or ties of the second rounding (`binary32`) in their strata, `--strata` not obeyed, `gen` accepting an unknown stratum, format or kernel or `--exhaustive` |
| `rational_reference` | the reference runner flagged on a stream of either kernel in `binary64`, `binary32` or four toy formats; a dropped, repeated, dropped-and-repeated, altered or reordered line, or a missing trailer, not a stream error; a stream of `add_2_2` and `rational_2` together judged otherwise than each alone |
| `rational_injected` | a planted fault of the reference runner (`rat-*`) not failing in `binary64`, `binary32` and `fp:4:-6:4`, failing in another field than its own, or changing the kernel it does not apply to; the naive pair failing on other lines than those the judge counts as not normalized, and likewise for $den = 0$ and the error's faults |
| `rational_merging` | the merge of the summaries of two halves of rational streams differing from the whole; `check --json` and its exit status on a correct and a faulty runner, the report without the expected value of a failure |
| `claims_reading_wave4` | the fixture of Milestone 2 unreadable or its labels other than the claims say; 36 malformed kernels of the wave not set aside (a side or a number of steps of the wrong form, a field of another kind, the value of `neighbor` not an input's name, `when` on a rounding to nearest or outside its vocabulary, `exact_when` empty, not a list, on `rounded`, with two relations or none, with another field, over an unknown input or a limb the input does not have, a threshold that is negative, zero, a division by zero, over a name, a fractional power, unbalanced or null; a limb reference in a value or in `finite_when`); a threshold other than its exact value, or one positive in `binary64` but not in a toy format not setting the kernel aside for that format alone; a condition other than the same in Fractions, limb by limb, on random operands of three formats |
| `directed_arithmetic` | on every value of seven toy formats (precision 1 included), the neighbors of the table (infinities and NaN included), the row of each operand and the classes of its steps other than from their definitions; the directed roundings and the rounding to nearest in the format with overflow, and the overflow classes, other than a brute-force search on every multiple of $\eta/8$ to beyond twice $\Omega$; the steps of the format unbounded above other than the sorted list of its numbers |
| `gen_wave4` | an invalid generated case, a missing stratum or another family than the claims call for, the correct runner flagged or suspicious, a class the guards ask for never reached (every row of the table and both classes of steps, both outcomes of `when`, both overflows, a NaN and an infinite operand, an exact and an inexact rounding, a result at the rounding and one step beyond, each condition of `exact_when` failing and all holding) in `binary64`, `binary32` and `fp:5:-10:5`; a corner a stratum is for never reached (the special values, powers of two of both signs, $\lambda$ and the subnormal numbers; sums beyond each side, $\Omega$ in either position, exact and near cancellations, exact sums, an operand below half an ulp of the other; products exactly $P$, just below and just above it, below it and rounded to it, of $\eta/2$, $\eta$ and below $\eta/2$, beyond each side, a zero factor with $\Omega$; scaled leading limbs, second limbs and radii exactly $N$, just below and just above it, powers of two on both sides of 1); case $i$ not reproducible |
| `exhaustive_wave4` | the domains of the wave against brute-force counts; the correct runner flagged, a line of the extended domain not judged, or a class the guards ask for never reached, on any of 22 enumerations of tiny formats (32 without `--quick`), the neighbors at precision 1 and 2 among them |
| `injected_wave4`, `injected_wave4_exhaustive` | a planted fault of the wave (`refrun` variants above) not caught in the entry or statement where it belongs (`neighbor`; `rounded`; `bound`, with `rounded` allowed for a product on the wrong side; `rounded` alone for a product not exact above $P$; containment, with `exact_when` allowed, for a radius one number too small; `exact_when` alone for a radius grown or a center moved where the scaling is exact; the `exact_when` of `error` for `mul_pow2_2`), caught in another, or flagged in a kernel that does not use it, on `binary64`, `binary32` and `fp:4:-6:1`, and on every case of tiny formats |
| `judge_wave4` | one of 157 hand-written lines judged otherwise than worked out by hand (every row of the table, the planted faults of the wave written out, overflows on each side, the sign of zeros, the finite domain's non-finite cases, each failure in its entry or statement), or a count of rows, steps, overflows, operands, roundings or conditions off |
| `merging_wave4` | the merge of summaries of the wave differs from the whole |

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
