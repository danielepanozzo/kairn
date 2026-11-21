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
domain as `mul_down_bound_real`, and `mul_pow2_2` with an `exact_when` on its error) and
`oracle/selftest/claims-wave5.json` (the folds' stage of Milestone 2: the eight folds, their steps,
finishes and bounds, and the kernels whose bounds they name, frozen from the claims of
2026-11-20), `oracle/selftest/claims-wave6.json` (the 33 interval kernels of Milestone 2 and
`add_2_2` and `mul_2_2`, whose bounds their constants name, frozen from the claims of
2026-11-20) and `oracle/selftest/claims-wave7.json` (stage B: the eighteen maps and their
steps, the folds of maxima and their kernels, the convolutions, and the kernels and folds
they name, frozen from the claims of 2026-11-20) and `oracle/selftest/claims-enclosure.json`
(stage B2 of the enclosure interface: the 53 kernels of the predicates and comparisons of an
interval and a ball, the set operations of a ball and the conversions of two limbs, with
`ball_from_interval_2` and `add_2_2`, frozen from the claims of 2026-11-21), so that it does not
depend on the generator.

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
| `badradius` | `makes_ball` | each class of radius as often: negative, $-\infty$, NaN, $+\infty$, $+0$, $-0$, positive ($\eta$, huge or ordinary); centers not finite (an infinity or a NaN) half the time |

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

The kernels of the folds' stage of Milestone 2 ([Folds](#folds)) get families of their own too
(`gen5.py`), chosen from claims that no earlier kernel has, each with the common strata read for
its shape and strata of its own; the steps of the sums of supplied arrays (`sum_entry_step_k`,
`sum_fast_entry_step_2`) claim what `add_1_1`, `add_2_2` and `add_fast_2_2` claim and keep their
families:

| Family | Kernels | Strata of its own |
|---|---|---|
| `count` | a `count()` input: `bound_sum_k`, `bound_dot_k` | `integer` (integers from 1 to $2^p$, log-uniform: the counts of real arrays); `fraction` (counts that are not integers, which `count()` allows); `limit` ($m \cdot \mathrm{unit}(K)$ from 1/16 to 1, log-uniform, and the numbers next to $m \cdot \mathrm{unit}(K)$ = 1/5, 1/4, 1/2 and 1, with $\mathrm{unit}(K)$ from the claims of the kernel K the bound is for); `beyond` ($m \cdot \mathrm{unit}(K)$ from 1 to the largest count). The common strata: `zero` is $m = 0$ (either sign), `underflow` 1, its successor and small integers, `overflow` the top binades, `pow2` powers of two, `extreme` the numbers next to the limits |
| `dotstep` | a value `NAME + NAME * NAME`: `dot_step_1`, `dot_step_2` | `cancel` ($s$ within a few units of $-(xy)$ rounded to the format: the state cancels the product); `state` ($\lvert s\rvert$ $p$ to $2kp + 4$ binades above or below $\lvert xy\rvert$); `zerostate` ($s = 0$, the first step of a fold); `tie` ($xy$ exact and $s$ an odd multiple of half its unit: $s + xy$ a tie); `exactprod` (short significands) |
| `finish` | a `finite_or_nan` entry: `fold_finish_k` | `nonfinite` (the leading limb infinite or a NaN, any lower limb); `tails` (a finite leading limb with a lower limb that is not finite, or with a finite lower limb that does not normalize it: the state is passed on as it is) |

The interval kernels of Milestone 2 ([The kinds of the interval
kernels](#the-kinds-of-the-interval-kernels)) get families of their own (`gen6.py`), chosen from
their claims before every earlier family; `ball_narrow_2_1`, an `encloses` of a ball of the
extended domain, keeps the family of the non-finite layer. An interval is one operand: its two
bounds, drawn as two numbers of a stratum and sorted, or a special interval. Each family has the
common strata, read for its operands, and strata of its own, each coming round twice per cycle:

| Family | Kernels | Strata of its own |
|---|---|---|
| `ivop` | an `encloses_interval` entry: `interval_neg_k`, `interval_add_k`, `interval_sub_k`, `interval_mul_k` | `special` (each operand the empty set, the whole line, a half-line on either side, $[0, 0]$, a point or bounded, one of them special); `point` (points, bounds one step apart, $[0, 0]$, $[-\eta, \eta]$); sums and products: `threshold` (bounded operands whose range reaches the limit of `bounded_when`, $\Omega$ or $2^{q_{\max}+p+E}$, exactly or one unit inside or outside, on the upper or the lower side); sums: `cancel` (a bound of one operand within a step of minus a bound of the other; for two limbs the leading limbs cancelling and not the tails) and `zerosum` (a bound of the range exactly zero: `exact_when` true); products: `zeroinf` ($[0, 0]$ or a zero bound against an unbounded operand) and `aroundp` (products of bounds around $P = 2^{2p-1}\eta$, `product_large` both ways) |
| `ivset` | `interval_set`: the hulls and intersections | `special` (both empty an eighth of the time), `point` (equal intervals and points), `disjoint`, `touch` (one common point), `nested` |
| `ivmake` | `makes_interval`, `makes_ball` from an interval: `interval_make_k`, `ball_from_interval_2` | `nanbound` (a NaN bound, the other any value), `reversed` ($lo > hi$, $[+\infty, h]$, $[l, -\infty]$), `infinities` (each bound an infinity or a number: half-lines, the whole line, equal infinities), `point`; for the ball also `oddeta` (bounds odd multiples of $\eta$ below $2N$, whose halves are not numbers) and `top` (bounds at and next to $\pm\Omega$) |
| `ivmid` | `ball_of_interval`, `splits`: `interval_mid_rad_1`, `interval_to_ball_1`, `interval_split_1` | `special`, `point`, `step` (bounds one or two steps apart), `oddeta`, `top` ($[-\Omega, \Omega]$, $[\Omega, \Omega]$, $[\mathrm{pred}(\Omega), \Omega]$, ...) |
| `ballbound` | `set_bound`, `interval_of_ball`: `ball_lower_as_k`, `ball_upper_as_k`, `ball_to_interval_1` | `ballstates` (the whole line, the empty set), `radii` (radii of every size against the center), `cross` (a radius about $\lvert c\rvert$: $c - r$ small, zero or of the other sign), `beyond` ($c - r$ below $-\Omega$, $c + r$ above $\Omega$), `exactend` ($c \pm r$ a number of the format, or not) |
| `outward` | `outward`, or `encloses` with no ball: `add_ball_2_2`, `mul_ball_2_2`, `add_down_2_2` ... `mul_dir_2_2`, `mul_ext_2_2` | sums: `cancel`, `zerosum` ($x + y = 0$, $x - y = 0$ exactly), `close`, `apart`, `tiny` (values near the smallest normal number, where the absolute term is most of the bound); products: `close`, `tiny`, `aroundp`, `exactprod`; in the extended domain (`mul_ext_2_2`) also `nonfinite` (an infinite operand), `zeroinf` (a zero against an infinity) and `edge` (products near the overflow threshold) |
| `dirmul` | `bound` and `rounded` with `zero_factor`: `mul_dir_1` | the strata of `dirprod` on finite operands (`aroundp`, `tiny`, `exactprod`, `beyond`), and `nonfinite` (an infinite operand, the other finite, zero or infinite; never a NaN: `not_nan()`), `zeroinf`, `zerofactor` (a zero against any number) |

The exhaustive mode of a kernel with `interval()` or `not_nan()` (`gen6.IvExhaustiveGen`) takes
an interval as one operand, as a ball is one: the empty set and every pair $l \le h$ of bounds,
$l$ a number of the format (or a normalized pair) or $-\infty$ and $h$ a number or $+\infty$; a
restriction on the lower (upper) input keeps the finite lower (upper) bounds whose leading limb it
keeps, and the infinite bounds and the empty set are always enumerated. `not_nan()` leaves NaN out
of the domain of its input. Sizes are in [Testing](../docs/developer/testing.md#cross-checks).
The steps of the maps and the kernels of the folds of maxima of stage B ([Maps](#maps), [Folds of
maxima](#folds-of-maxima)) get two more families (`gen7.py`), and the finishes of the folds of
maxima one in `gen5.py`, chosen from claims that no earlier kernel has; the other steps of the
maps (`add_entry_step_k`, `sub_1_1`, `sub_entry_step_k`, `scale_step_k`, `mul_pow2_step_k`) claim
what `add_1_1`, `add_2_2`, `sub_2_2`, `mul_1_1`, `mul_2_1` and `mul_pow2_2` claim and keep their
families (the scale family of `gen2.py` has a branch of its own for a one-limb operand beside the
power of two, `mul_pow2_step_1`: the same strata, with `halfscaled` aiming the lowest bit of $x c$
at $\eta/2$, a tie of the subnormal range, or at $\eta/4$ and $\eta/8$, just off one):

| Family | Kernels | Strata of its own |
|---|---|---|
| `axpy` | a value `NAME * NAME + NAME`: the steps of axpy, `axpy_step_k`, `axpy_step_2_1` and their entry forms | `cancel` ($y$ within a few units of $-(a x)$ rounded to $y$'s limbs); `state` ($\lvert y\rvert$ $p$ to $2kp + 4$ binades from $\lvert a x\rvert$); `tie` ($a x$ exact and $y$ an odd multiple of half its unit); `exactprod` (short significands); `tight` (one limb: $a = 1 + 2uk$, $x = 1 - (2k - 1)u$, $y = (4j + 1)u$, scaled, of one sign: $a x = 1 + u - 2u^2k(2k-1)$ rounds down to 1 and $1 + (4j + 1)u$ is a tie that rounds down to the even $1 + 4ju$, so both roundings lose about $u$ the same way, $2u$ of the $2u$ the bound allows; two limbs: the literature's tight case of the product, MR22's of `mul_2_2` or JMP17's of `mul_2_1` (`tight.py`, $p = 53$), with $y = 0$ or tiny) |
| `maxof` | a `maximum` entry: `norm_combine`, `norm_step_k` | `equal` (the two arguments of one value, zeros of both signs among them); `neighbor` (one the number next to the other); `negative` (arguments of both signs: a state below zero, which the fold never has but the claim covers) |
| `maxfinish` | a `finite_or_nan` entry with `if` or `steps`: `norm_finish_k` | `nonfinite` (as `finish`); `top` ($\Omega$, its two predecessors, $-\Omega$: the step up to $+\infty$); `smallstep` (the zeros, $\pm\eta$, $\pm 2\eta$, $\pm\lambda$ and its neighbours: the steps from $-\eta$ to a zero and from a zero to $\eta$); the mask drawn at random |

In 2 000 cases of seed 0 the interpreter brings `axpy_step_1` and `axpy_entry_step_1` to $1 - O(u)$
of their bound of form T in `binary64` and `binary32`, `axpy_step_2` to 0.571 in `binary64` (MR22's
case of `mul_2_2`: its error $3.998u^2\lvert a x\rvert$ against the bound's $7u^2$; 0.25 to 0.55 in
`binary32`, where the literature has no case), `axpy_step_2_1` to 0.40 to 0.73, `mul_pow2_step_1`
to exactly 1 (an odd multiple of $\eta/2$ rounds by $\eta/2$, its whole bound).

What a generator of cases gives for `count(m)`: $m = 0$, and numbers of the format from 1 up, both
integers and others (the claim allows any $m \ge 1$; the header converts a number of terms, and a
conversion that is not exact steps up, so non-integers reach the kernel). Negative counts and
counts between 0 and 1 are outside the requirement: `check` reports them as invalid. A format
without $\tfrac12$ (`format(half)`: $q_{\min} \le -1$) is refused by `gen` for these kernels.

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
    - `makes_ball`: empty when the given radius is negative ($-\infty$ included), whatever the
      center; otherwise the whole line when the given radius is a NaN or $+\infty$ or the given
      center is not finite; otherwise the given center and radius (a radius $-0$ is $0$). A NaN
      radius gave the empty set until the owner's decision of 2026-11-20, which made it the
      whole line (architecture.md, `makes_ball`). Counted by the given state (`given: finite
      ball`, `whole line`, `empty set`) and by the class of the given radius (negative,
      `-inf`, `NaN`, `+inf`, `+0`, `-0`, positive, the sign of a zero read from the line's text)
      with a finite center and with one that is not (`given radius NaN, center not finite`),
      each of which the guards ask for (`-0` but in an enumeration, which has one zero).
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

### The kinds of the folds' stage

architecture.md, "Claims of Milestone 2" (the kernels of the folds' stage), read with milestone2.md,
"Batch kernels"; `check.py`, `extended.py` and `cexpr.py`. The folds themselves are in
[Folds](#folds).

- **`count(m)`** (a requirement of a one-limb input, the finite domain): $m = 0$ or $m \ge 1$,
  exactly; $-0$ is a zero. A line with $0 < m < 1$ or $m < 0$ is invalid.
- **`format(half)`** (a requirement that names no input): the format contains $\tfrac12$,
  $\eta \le \tfrac12$. In a format without it every line of the kernel is out of scope (counted
  as such, with the reason; `--ignore-min-precision` does not bring it in), as below the minimum
  precision: it is a condition on the format, not on the operands.
- **`error` of form `T`**: $\rho$ is the sum of the magnitudes of the terms of `value`, the
  operands of its outermost sums and differences (a unary minus kept with its term): for `s+x*y`,
  $\lvert s\rvert + \lvert xy\rvert$, each term at its own scale; otherwise as forms `R` and `A`.
- **`upper` with `value` and `if`** and **`holds`**: when the mask output named by `if` is 1, the
  output is at least the exact value of `value` (`upper`), or the relation holds between the exact
  values of the two `args` (`holds`); when it is 0 nothing is claimed, and the line counts
  `ok false: nothing claimed`. The expressions are those of `cexpr.py`: integers, `u`, `eta`, the
  limb inputs and one-limb outputs by name, `unit(K)` and `tiny(K)` (the `rel` and `abs` of kernel
  K's one `error` entry in the format: its listed instance in a named format, evaluated from `c`
  and `t` otherwise), `+ - * /`, parentheses and integer powers with a constant exponent, evaluated
  with Fractions; a division by zero where the mask is true is a failure (the stated value does
  not exist). A kernel's entries are all under a mask or none; such a kernel (the bounds) is judged
  on every line: an output named by an entry that is infinite or a NaN where the mask is true
  claims nothing in the finite domain, and the line is **suspicious** (the kernel said its bound
  holds and gave none); an output that is not a number of the format is a failure. There is no
  "non-finite, not judged" for these kernels: with the mask false, $g = +\infty$ for a huge count
  is no sign of anything.
- **`finite_or_nan`** (the extended domain): the mask `flag` is 1 exactly when limb 0 of `value`
  (an input, the state of a fold) is finite; the output is then the value limb for limb (a NaN
  matching a NaN, the sign of a zero free); otherwise every limb of the output is a NaN. A
  multi-limb input with neither `canonical()` nor `ball()`, refused in the extended domain
  otherwise, is read as any limbs when every entry of its kernel is `finite_or_nan`: a finite
  leading limb with a lower limb that is not finite, or a pair that is not normalized, is passed
  on as it is.

Statistics, per entry: for a bound kernel (a `count` input and entries naming one `unit(K)`), the
class of $x = m \cdot \mathrm{unit}(K)$ with the mask (`ok true, 0 < m*unit(mul_2_2) <= 1/5`, `1/5 <
... <= 1/4`, `1/4 < ... <= 1/2`, `1/2 < ... < 1`, `>= 1`, `= 0`), `m an integer` or not, the largest
$x$ where the mask is true and the smallest where it is false; for `upper` with a value, the
smallest and largest (output $-$ value)/value and the smallest excess over a positive stated
value in gaps of the output; for `holds`, `holds`; for `finite_or_nan`, the class of the value
(`value: finite leading limb, every limb finite`, `... a lower limb not finite`, `value: leading
limb infinite`, `value: leading limb NaN`). In 2 000 to 20 000 random counts per format and on
every count of `fp:12:-30:12`, the reference listing, the interpreter and the compiled kernels
give $g$ more than a gap above its stated value everywhere (at least 1.34 gaps, `bound_sum_2` in
`fp:12:-30:12`; 1.8 to 2.9 in `binary64` and `binary32`), and ok true up to $x$ just below 1/4
and false from there, in every format tried.

Readings chosen where the documents leave a choice:

- `count()` is read in the finite domain only, and `format(half)` as a condition of the format
  (out of scope), not of the operands (invalid).
- `upper` takes `gaps`, or `value` with `if`, or (the radius kernels of the ball vectors, [Ball
  vectors and the accumulator](#ball-vectors-and-the-accumulator)) `value` without `if`; `gaps`
  beside a value is refused. Entries under a mask are read only in a kernel of the finite domain
  whose every entry has one.
- The exponent of a power in these expressions must be a constant integer (no input names), and
  `u`, `eta`, `unit` and `tiny` may not be the name of an input or output.
- `finite_or_nan` compares limb for limb by value: a NaN for a NaN, the same infinity, numbers
  equal (zeros of either sign).

### The kinds of the interval kernels

architecture.md, "Claims of the interval kernels" and "Claims of the interval kernels: two limbs
and the enclosure interface", read with milestone2.md, "Interval kernels" and "One enclosure
interface" (`intervals.py`, hooked into `claims.py`, `check.py` and `extended.py`). A bound of an
interval is a number, an infinity, or part of the empty set's representation; the members of an
interval are real numbers ($[1, +\infty]$ does not contain $+\infty$); the sign of a zero bound is
never judged.

- **`interval(L, U)`** (the extended domain; L and U both of one limb or both of two): the empty
  set $(+\infty, -\infty)$ (for two limbs $(+\infty, \pm 0)$ and $(-\infty, \pm 0)$), or no NaN
  bound, $l \le h$ as extended reals, $l < +\infty$, $h > -\infty$, each bound a number of the
  format or an infinity (for two limbs canonical). A line outside it is invalid; the same test
  decides I1 of an output. **`not_nan(NAME)`**: a one-limb input, or a two-limb input that is also
  `canonical()`, whose leading limb is not a NaN.
- **The exact range** of a set over interval (or ball) names, each name once and no `abs`: interval
  arithmetic in the extended reals, a sum adding lower bounds and upper bounds, a negation
  exchanging them, a product the least and the greatest of the four products of bounds with
  $0 \cdot \infty = 0$; for a single-use expression this is the greatest lower bound and the least
  upper bound of the values over the members (a finite ball is $[c - r, c + r]$, the whole line
  $[-\infty, +\infty]$). Values are integers at the scale of the expression.
- **`encloses_interval`**, each statement counted under its name when it fails: **I1** the output
  is a canonical interval; **I2** it is empty exactly when an operand is; **I3** its lower bound is
  at most the range's greatest lower bound and its upper at least the least upper bound; **I4** by
  `tight`: `exact`, the bounds of the range; `rounded`, the range's bounds rounded down and up in
  the format with overflow (an infinite bound stays), within `steps` steps outward, and with
  `when: product_large` exactly the roundings when every product of a finite bound of $x$ and a
  finite bound of $y$ is zero or at least $2^{2p-1}\eta$; `outward`, for bounded operands and a
  bounded result $lo - z_\ell \le \mathrm{rel}\lvert lo\rvert + \mathrm{abs}$ and
  $z_u - hi \le \mathrm{rel}\lvert hi\rvert + \mathrm{abs}$, for bounded operands the bound of a
  side the range's own where every condition of that side's `exact_when` holds, and an infinite
  bound of the range that bound of the result; **I5** for bounded operands, every member within
  the limit of each `bounded_when` condition ($\lvert z\rvert \le \Omega$, or
  $\le 2^{q_{\max}+p+E}$; the members' largest magnitude is that of a bound of the range) makes
  the result bounded, and with `bounded_exactly` a result beyond it unbounded; **I6**
  (`zero_factor`) for nonempty operands, an operand $[0, 0]$ makes the result $[0, 0]$.
- **`outward`**, the finite domain: the output on its side of `value`,
  $\lvert\text{output} - \text{value}\rvert \le \mathrm{rel}\lvert\text{value}\rvert + \mathrm{abs}$,
  and the value itself where every condition of `exact_when` holds (`{"zero": EXPR}`: EXPR $= 0$,
  besides `zero_or_abs_gt` and `zero_or_abs_ge`); judged where the output's leading limb is finite.
  The extended domain (`mul_ext_2_2`): never a NaN; with `zero_factor` a zero operand (its leading
  limb zero) gives every limb zero; otherwise an infinite operand gives the infinity of the
  product of the leading limbs followed by zeros; with finite operands the output on its side as
  an extended real ($-\infty$ is always below, $+\infty$ always above), and a finite output within
  the bound, exact where `exact_when` holds. An infinite bound from operands and value below
  $\Omega/4$ is suspicious.
- **`encloses` with `"balls": {}`** (the finite domain only): the operands are points,
  $\lvert\text{set} - \text{center}\rvert \le$ radius: the judge of `encloses`, whose range is then
  the one value.
- **`makes_interval`**: the output canonical, and by the first case that applies (architecture.md,
  "The constructors on every pair of values"): the whole line when a given bound is a NaN,
  whatever the other, or when both are the same infinity, $[+\infty, +\infty]$ or
  $[-\infty, -\infty]$; the empty set when the bounds are reversed, $lo > hi$ (which includes
  $[+\infty, -\infty]$, $[+\infty, h]$ and $[l, -\infty]$); otherwise the interval of the given
  bounds. Two limbs: canonical inputs, a bound is a NaN or an infinity when its leading limb is one
  (a NaN bound is $(\mathrm{NaN}, \mathrm{NaN})$, an infinite one $(\pm\infty, \pm 0)$, so that
  $(+\infty, 0)$ and $(+\infty, -0)$ are the same infinity twice), and the values are compared (a
  normalized pair is unique for its value: $(1, 2^{-4})$ and $(1, 0)$ are reversed). The same
  infinity twice gave the empty set, as in IEEE 1788, until the owner's decision of 2026-11-20.
- **`makes_ball` from an interval** (`from` with `lower` and `upper`, one limb each), by the first
  case that applies: the whole line for a NaN bound, whatever the other, or for the same infinity
  twice (center zero, of either sign, radius $+\infty$); the empty set for reversed bounds; and
  for the other pairs, $lo \le hi$, a finite ball containing $[lo, hi]$ when both are finite (with
  every `midpoint_when` condition, `half_in_format`: the bound is even as a multiple of $\eta$, its
  center $(lo + hi)/2$ exactly and its radius $\mathrm{RU}((hi - lo)/2)$), the whole line when a
  bound is infinite. The same infinity twice gave the empty set until 2026-11-20.
- **`set_bound`**: $+\infty$ (`below`) or $-\infty$ (`above`) for an empty ball; otherwise at most
  (at least) the set's greatest lower (least upper) bound $t$, and with `tight` the rounding of $t$
  down (up) in the format with overflow, within `steps`. **`interval_of_ball`**: the output
  canonical, empty exactly when the ball is, containing the set, its bounds the roundings of the
  set's bounds, within `steps`.
- **`interval_set`**: exact; `union` the smaller lower and the larger upper bound of the nonempty
  operands, empty when both are; `intersection` the larger lower and the smaller upper bound,
  empty when an operand is or they cross.
- **`ball_of_interval`**: for a bounded $X = [\ell, h]$ and $m = (\ell + h)/2$: the center and
  radius finite (the center normalized), $\ell \le c \le h$,
  $\lvert c - m\rvert \le \mathrm{rel}\lvert m\rvert + \mathrm{abs}$, $[c - r, c + r] \supseteq X$,
  and with `smallest_radius` $r = \mathrm{RU}(\max(c - \ell, h - c))$ in the format with overflow.
  Otherwise `ieee1788`: $(0, +\infty)$ for the whole line, $(\Omega, +\infty)$ and
  $(-\Omega, +\infty)$ for the half-lines, two NaN for the empty set; `ball`: the whole line for an
  unbounded $X$ and the empty ball for the empty set. Each part counted under its name when it
  fails (`special`, `finite`, `center`, `midpoint`, `containment`, `smallest_radius`). With
  `ieee1788` the center of a bounded $X$ finite (and canonical) is claimed in the formats of the
  statements only, the ruling of 2026-11-21 ("The formats of V4", below).
- **`splits`**: both parts canonical; the empty set gives the empty set twice; otherwise the first
  part's lower bound is $X$'s, the second's upper bound $X$'s, and the first part's upper bound the
  second's lower bound, a member of $X$ (implied by the rest: both parts canonical). For a bounded
  $X$ the parts canonical and meeting at a point of $X$ are claimed in the formats of the
  statements only (the same ruling).
- **`zero_factor` on `bound` and `rounded`** (the extended domain, the value a product of two
  one-limb inputs): a zero operand gives a zero output, $0 \cdot \infty = 0$; otherwise as without
  the field.
- **The constants of a claim**, `rel` and `abs` of `outward`, of the outward `tight` and of
  `ball_of_interval`: integers, `u`, `eta`, `unit(K)`, `tiny(K)`, `+ - * /`, parentheses, integer
  powers (a constant integer exponent), and `up(EXPR)`, the smallest number of the format not below
  EXPR (computed as the format's rounding up of $\lceil \text{EXPR}/\eta\rceil$), evaluated exactly
  per format with Fractions; an `up( )` beyond $\Omega$, a division by zero or a negative constant
  in a format sets the kernel aside for that format (a CLAIMS ERROR), and `unit(K)`, `tiny(K)` must
  name a readable kernel with one `error` entry (`add_2_2`, `mul_2_2`), checked in `binary64` when
  the claims are read.
- **An entry about an output group other than the first** (the finite domain, an entry not under
  a mask; `mul_dir_2_2` alone): each entry holds where the leading limb of its own group is finite.
  An entry whose group is not finite claims nothing (counted, `the leading limb of its output is
  not finite: nothing claimed`); the line is judged when one entry is, and non-finite otherwise; a
  group that is not finite on operands and value below $\Omega/4$ makes the line suspicious.
  Kernels whose entries are under a mask (`bound_sum_k`, `bound_dot_k`) are read as before.

Readings chosen where the documents leave a choice, the stricter where they differ:

- I4 of an outward `tight` bounds the distance only when both bounds of the result are finite (the
  text says "a bounded $Z$"); the exactness of a side, for bounded operands, whether or not the
  result is bounded. A finite bound beside an infinite one is not judged; its distance is kept
  (`...: distance from the range bound / (rel*|bound| + abs), beside an infinite bound (not
  claimed)`), and comes to at most 0.50 of the bound in the runs so far, so the stricter reading,
  each finite bound measured, would hold on them too.
- The `abs_le` set of `bounded_when` must be the entry's own `set` (the same expression), or the
  claims are refused; for bounded operands the condition on every member is the condition on the
  largest magnitude of a bound of the range.
- `tight` `rounded` is refused for bounds of two limbs (a two-limb number has no rounding of its
  own), `when` without a set that is the product of two interval names, and `zero_factor` likewise.
- `outward` in the extended domain requires `not_nan()` of every operand of its value (the output
  is never a NaN); `zero_factor` there needs a value that is the product of two inputs.
- A field that is written only when it is so (`bounded_exactly`, `zero_factor`, `smallest_radius`)
  must be `true`; `midpoint_when` belongs to `makes_ball` from an interval only.
- `half_in_format(NAME)` of a finite bound is read as "an even multiple of $\eta$" (its half is a
  number of the format exactly then: halving keeps the significand's bits).

Statistics, per entry (the cross-checks' guards read them; `intervals.py` names them): for
`encloses_interval`, `operands: an empty operand`, `... nonempty, an unbounded operand`,
`operands: bounded`, `result: empty`, `bounded`, `unbounded`, `bounded operands, unbounded
result`, `bounded operands, bounded_when holds` and `fails` with the largest
$\max\lvert\text{member}\rvert$/limit where it holds and the smallest where it fails, `I6 applies:
...`; per side (`lower`, `upper`) `range bound a number of the format`, `not a number`,
`infinite`, `beyond Omega`, `zero`, `at the directed rounding`, `one step beyond ...`,
`product_large holds` and `does not hold (within the steps)`, `exact_when holds`, `exact_when
fails: COND`, and the largest distance from the range bound over $\mathrm{rel}\lvert
\text{bound}\rvert + \mathrm{abs}$ (also where the relative term is the larger); for `outward` the
same fraction of $\lvert\text{output} - \text{value}\rvert$, `value zero`, `output the value
exactly` or not, `absolute term larger than the relative term`, `exact_when holds` and fails, and
in the extended domain `a zero operand`, `an infinite operand, none zero`, `finite operands,
finite output` and `infinite output`; for the constructors the given states (`given: an interval`,
`a point`, `an unbounded interval`, `a NaN bound`, `reversed bounds`, `equal infinities`, by the
first case that applies, so that $[\mathrm{NaN}, +\infty]$ is a NaN bound), the cell of the table
of architecture.md's case analysis (`given lo R, hi C`, R one of `NaN`, `-inf`, `a`, `+inf` and C
one of `NaN`, `-inf`, `b`, `+inf`, `given lo a, hi b, a <= b` and `a > b` for two finite bounds:
17 cells), for two limbs `given reversed bounds, equal leading limbs` and `given the same
infinity, second limbs zeros of opposite signs` (the signs read from the line's text),
`midpoint_when holds` and `fails`); for `set_bound` and `interval_of_ball` `ball: empty`, `whole
line`, `finite` with the sides' classes; for `interval_set` `an operand empty`, `both operands
empty`, `nonempty operands, disjoint`, `touching (one common point)`, `overlapping`; for
`ball_of_interval` and `splits` the class of $X$ (`X: empty`, `whole line`, `half-line [l, +inf]`,
`half-line [-inf, h]`, `bounded`, `a point`, `a bound an odd multiple of eta below 2N`) and the
largest $\lvert c - m\rvert / (\mathrm{rel}\lvert m\rvert + \mathrm{abs})$, and in a format of no
statement `a finite center not claimed: a format of no statement (...)` (`a split at a point of X
not claimed: ...`) on every bounded $X$ and `bounded X, the center not finite (not claimed)`
(`bounded X, the point of split not finite (not claimed)`); for `zero_factor`
`zero_factor: a zero operand` and `a zero against an infinite operand`.

**What the reference implementation, the interpreter and the compiled kernels reach** (the
interpreter and the compiled kernels on the full tier's 20 000 random cases per format, with the
same maxima, the scalar and packed runners writing the same bytes in every cross-check; the
interpreter on the enumerations of the full tier; on the quick tier's 2 000 cases per format the
compiled kernels come to 0.60 to 0.67): the bounds of two limbs come to 0.62 to 0.70 of
$\mathrm{rel}\lvert v\rvert + \mathrm{abs}$ in `binary64` and `binary32` (`add_down_2_2` 0.648,
`mul_dir_2_2` 0.642, `mul_ext_2_2` 0.70, `interval_add_2` 0.625, `interval_mul_2` 0.641 in
`binary64`; `add_down_2_2` 0.685, `mul_dir_2_2` 0.695 and `interval_mul_2` 0.646 in `binary32`),
the relative term the larger part of the bound there, and 0.36 to 0.49 in the toy formats of the
enumerations, where the absolute term is (milestone2.md measured 0.61 to 0.65 at four and five
bits), 0.47 to 0.52 in the sampled formats. The midpoint of `interval_mid_rad_1` reaches its bound
$u\lvert m\rvert + \eta$ itself in `binary64` and `binary32` (an odd multiple of $\eta$ below
$2N$) and 0.97 of it at `fp:5:-9:2`; the error of `ball_lower_as_2` and `ball_upper_as_2` comes to
0.8 of $5u(\lvert c\rvert + r) + 3\eta$, that of `mul_ball_2_2` to 0.95, and the products of
`interval_mul_1` and `mul_dir_1` are one step beyond the directed rounding, all their `steps`
allow, on 22 000 to 35 000 lines a side.

### The kinds of the enclosure interface

architecture.md, "Claims of the enclosure interface: predicates and comparisons", "... the set
operations of a ball" and "... the conversions of two limbs", read with milestone2.md, "One
enclosure interface" and "IEEE 1788" (`enclosure.py` for the new kinds, `intervals.py` for the
fields added to its kinds; `genenc.py` and `gen6.py` generate their requests). The members of a
set are real numbers: between the bounds of an interval ($[1, +\infty]$ does not contain
$+\infty$), within the radius of a finite ball's center ($[c - r, c + r]$, $c$ the exact sum of
the center's limbs), every real number for the whole line, none for the empty set. A set is
written as the empty set or the pair of its greatest lower and least upper bound in the extended
reals, and every relation is decided on those bounds with integers (`enclosure.relation`):

| `rel` | holds (for every choice of members) | fails for every choice (`trit`) |
|---|---|---|
| `lt` | both nonempty, $U_a < L_b$ | both nonempty, $L_a \ge U_b$ |
| `le` | both nonempty, $U_a \le L_b$ | both nonempty, $L_a > U_b$ |
| `eq` | both nonempty, $L_a = U_a = L_b = U_b$ (the same point) | both nonempty, $U_a < L_b$ or $U_b < L_a$ |
| `member` | the point finite and $L \le t \le U$ | otherwise |
| `subset` | $X$ empty, or $Y$ nonempty, $L_y \le L_x$, $U_x \le U_y$ | |
| `equal` | both empty, or both nonempty with the same bounds | |
| `interior` | $X$ empty, or $Y$ nonempty, ($L_y = -\infty$ or $L_y < L_x$) and ($U_y = +\infty$ or $U_x < U_y$) | |
| `disjoint` | an operand empty, or $U_x < L_y$ or $U_y < L_x$ | |
| `empty`, `entire` | $X$ empty; $X$ the whole line | |

An infinite bound needs no case of its own: $U_a < L_b$ is false when $U_a = +\infty$ (the members
are unbounded above) and when $L_b = -\infty$. The argument `0` is the set $\{0\}$. The selftest
checks this reading against the definitions quantified over the members of sets of rationals
(`enc_relations`).

- **`certain`** (`of` a mask; `rel`, `args`; `intervals` or `balls`, the one or the other;
  `exact`, written only when true; `exact_when`, a nonempty list of
  `{"abs_le": EXPR, "omega": true}`, $\lvert\text{EXPR}\rvert \le \Omega$ on finite operands, EXPR
  over the limb inputs): **sound**, a true mask only where the relation holds, on every line; and
  exactly the relation (failing as **`exact`**, **`special`** or **`exact_when`**, by where the
  claim says so) with `exact` always, on a line with an operand that is not finite (the empty set
  or the whole line; a point that is not a finite number), and with `exact_when` where every
  operand is finite (a bounded interval, a finite ball, a finite point) and every condition holds.
- **`trit`** (`yes`, `no`: two masks; the same fields, `rel` one of `lt`, `le`, `eq`, `member`):
  **yes** only where the relation holds for every choice, **no** only where it fails for every
  choice, never **both**; and both exactly so where `certain` would be exact. A wrong answer where
  the relation neither holds nor fails fails `yes` or `no` alone: the exactness is about the
  answers due.
- **`ball_set`** (`center`, `radius`; `set` `union` or `intersection`; `balls`: two, of the
  center's limbs): the result a canonical ball (**canonical**) that contains every member of
  $X \cup Y$ ($X \cap Y$) (**containment**); for the union empty exactly when both operands are,
  for the intersection empty when an operand is (**empty**); and the operands **as they are**, in
  the corrected reading of architecture.md (the clause that gives X has the condition that X is not
  itself special): for the union, X empty gives Y as it is (**Y as it is**), and Y empty with X not
  empty gives X as it is (**X as it is**); for the intersection the same with the whole line. As
  it is: the limbs as the line writes them, the sign of a zero compared (the one place where it is,
  read from the text), a NaN matching a NaN. Nothing more: Z need not be the smallest ball, nor
  inside X or Y, nor empty for disjoint balls.
- **`ball_splits`** (`parts`: two balls; `from`: a ball): both canonical; the empty set gives the
  empty set twice (**empty set**), the whole line the whole line twice (**whole line**); for a
  finite ball, $[c - r, c]$ inside the first part (**first part**) and $[c, c + r]$ inside the
  second (**second part**); a part that is the whole line contains everything.
- **`ball_of_interval` with `finite_when`** (`interval_mid_rad_2`, `interval_to_ball_2`): for a
  bounded $X$, with `ieee1788` the center finite and normalized, between the bounds and within
  `rel`$\lvert m\rvert$ + `abs` of the midpoint on every line, the radius $+\infty$ or a finite
  radius that contains $X$, finite where every condition $\lvert\text{BOUND}\rvert \le
  2^{q_{\max}+p+E}$ holds (**finite_when**); with `ball` a canonical ball that contains $X$, and
  where every condition holds a finite one whose center is as without the field. With `ieee1788`
  and a center of two limbs the center is canonical on every line (**canonical**), the special
  values of 1788 as before. `finite_when` and `smallest_radius` together are refused (the radius
  may be $+\infty$, which is not the smallest). The clause of the conditions (with `ball`, the
  finite ball and its center) is claimed in the formats of the statements only ("The formats of
  V4", below, the ruling of 2026-11-21), and so is, with `ieee1788`, the center finite and
  canonical (the second ruling of that day).
- **`interval_of_ball` with bounds of two limbs** (`ball_to_interval_2`): `tight` must be the
  outward tightness (a rounded one is refused for two limbs), with `rel`, `abs` and `exact_when`
  by side; the result canonical, empty exactly when the ball is, containing the set
  (**containment**); for a finite ball and a bounded result each bound within
  `rel`$\lvert\text{bound}\rvert$ + `abs` of the set's on its side (**tight**); for a finite ball,
  a side whose conditions hold the set's bound exactly (**exact_when**), whether or not the result
  is bounded (the stricter reading, as for `encloses_interval`); and for a finite ball a result
  that is bounded where every member is within the limit of `bounded_when` (**bounded_when**, not
  exactly), in the formats of the statements only (the ruling of 2026-11-21). `bounded_when` is
  for bounds of two limbs only, of the form `{"abs_le": SET, "exp": E}`, SET the entry's own set.
- **`makes_ball` from an interval with `rel`, `abs` and `smallest_radius`**
  (`ball_from_interval_1`; `rel` and `abs` together, `smallest_radius` only with them): the table
  of the constructors as before, and for finite bounds $lo \le hi$ the center between them
  (**center**), within `rel`$\lvert m\rvert$ + `abs` of $m = (lo + hi)/2$ (**midpoint**), the
  radius $\mathrm{RU}(\max(c - lo, hi - c))$ (**smallest_radius**). `ball_from_interval_2` is
  judged as before (`midpoint_when`), and both follow the rule of 2026-11-20: the same infinity
  twice is the whole line.

Readings chosen where the documents leave a choice, the stricter where they differ:

- `exact` and `exact_when` on one entry are refused (with `exact` the claim is `m = true <-> R`
  alone); a set named in `intervals` or `balls` that is no argument is refused, and so is the same
  set twice; the argument `0` is the string `"0"` or the integer 0.
- The kinds belong to the extended domain (refused elsewhere; in the finite domain no
  `interval()` or `ball()` reads, so the sets never do either).
- A half-line is neither a special operand nor a finite one: a claim without `exact` says only
  that its answers are sound there. (Every claim over intervals is `exact`.)
- `ball_set` compares the operands as they are in the line's text, which writes every NaN as
  `nan`: two empty balls whose NaNs differ in sign or payload (the case the proofs found, which
  made the clause of X conditional) cannot be written in the line protocol, and their lines, both
  empty, are judged as NaN matching NaN; two whole lines whose centers are zeros of different
  signs can, and the generator writes them (`bothspecial`).

**What is not claimed, and so not judged.** An answer not given by a kernel whose claim is not
exact there (the predicates of two limbs of a ball, and the comparisons of one limb where
$r_x + r_y > \Omega$): architecture.md, "The band is not claimed". It is counted (`mask false
although the relation holds (not claimed)`, `unknown although the relation holds (not claimed)`,
`... fails for every choice ...`) and measured: the largest margin of such an answer (the distance
from the boundary of the relation: $\bigl\lvert\lvert t - c\rvert - r\bigr\rvert$ for `member`,
the gap between the balls for `lt` and `le`, $r_x - (\lvert c_y - c_x\rvert + r_y)$ for `subset`)
over the largest radius, over $u^2$ times the distance of the centers (`an answer not given:
largest margin / largest radius`, `... / (u^2 * distance)`), and in the units of architecture.md's
band, $2e + G$, with its estimate of $e$, the radius of `add_ball_2_2` inside the kernel, which no
output shows ($3u^2$ times the distance plus $2\lambda$; $G$ the gap of `T` at the larger of the
radius and the distance), where the distance and the radius are below $\Omega/4$ (above, $e$ or the
difference itself overflows and the band is the whole line). The cross-checks' guards hold that
largest margin to 4 units, the documentation's largest band, $2e + 4G \le 4(2e + G)$
(`tests/crosscheck_guards.py`, `ENC_BAND_LIMIT`): it measured 0.67 to 2.5 on 20 000 random cases of
`binary64`, `binary32` and `fp:4:-6:1` (architecture.md's experiment: 2.3) and 0.17 to 0.42 on the
enumerations of the toy formats. Away from the boundary the answers are given: of 20 000 random
cases of `ball_less_2` in `binary64`, the strata `uniform` and `pow2` left 1 unanswered of 2 223,
and the others are in the strata aimed at the boundary (`boundary`, `near`, `points`, `zero`) or
at overflow (`huge`, `overflow`). The yes of `ball_equal_2`
(both balls the same point) is not claimed exact, as its generated statement has it and
architecture.md says: an unknown there passes (a hand-written line has it).

Statistics, per entry (the cross-checks' guards read them; `enclosure.py` names them): for
`certain` and `trit` the relation (`the relation holds`, `does not hold`, `fails for every choice`,
`neither holds nor fails for every choice`), the answers (`mask true`, `mask false`, `answer yes`,
`no`, `unknown`), the class of each set (`x: empty`, `whole line`, `half-line`, `bounded`, `a point`
for an interval; `empty`, `whole line`, `finite`, `a point` for a ball) and of a point (`t: finite`,
`infinite`, `NaN`), `an operand not finite: exact (claimed)`, `every operand finite`, `exact_when
holds` and `exact_when fails: |EXPR| <= Omega`, and the answers not given above; for `ball_set` the
cell of the states (`X empty, Y finite`, ..., nine), `Y as it is (claimed)`, `X as it is (claimed)`,
the finite operands `disjoint`, `touching (one common point)`, `overlapping`, `one inside the
other`, `both the whole line, centers zeros of different signs in the line`, the result's state,
`result the whole line from finite operands` and the largest radius over the smallest one that
contains what is due; for `ball_splits` the state of X, `X: a point (radius 0)`, the states of the
parts and the largest part radius over $r/2$; for `finite_when` `finite_when holds`, `finite_when
fails: |xl| <= 2^(qmax+p-2)`, `bounded X, the radius +inf` (`... the whole line` for a ball), the
largest $\max\lvert\text{bound}\rvert/2^{q_{\max}+p}$ with a finite radius and the smallest with an
infinite one; for `interval_of_ball` of two limbs the ball's state, the result's, each side's
`exact_when` and distance over its bound, `bounded_when` both ways; for `makes_ball` with `rel`
the center the midpoint or not and the largest distance over its bound.

**Strata.** The predicates, comparisons and set operations of a ball have families of their own
(`genenc.py`), chosen from their claims before those of `gen6.py`; each has the common strata,
read for its operands, and strata of its own, coming round twice per cycle, by its operands (one
set or two, a point, one limb or two):

| Family | Kernels | Strata of its own |
|---|---|---|
| `ivpred` | `certain`, `trit` over intervals | `special` (an operand the empty set or the whole line, the other any), `nearzero` ($[0, 0]$, $[-\eta, 0]$, $[0, \eta]$, half-lines ending at zero, intervals about zero), and by shape: `point` (one interval: points and intervals one step wide), `member` (the point a bound, one step inside or outside, infinite, NaN), or `touch`, `equal` (the same interval, the same point, an equal bound, half-lines), `nested` (with equal ends, half-lines), `disjoint` (one step apart or more); `tails` (two limbs: bounds of equal leading limbs and other second limbs) |
| `ballpred` | `certain`, `trit` over balls | `ballstates` (an operand empty or the whole line; a point infinite or NaN), `nearzero` (one ball: $c = \pm r$ exactly and one unit off, $[0 \pm 0]$, $[0 \pm \eta]$), or `boundary` (exactly on the boundary of the relation: the point $c \pm r$, balls touching, one inside the other with an equal end, the same point) and `near` (one to three units of the last limb off it); `huge` (a radius in the top binades, centers of opposite signs near $\Omega$), `points` (zero radii), `wide` (two balls: radii much wider or narrower than the distance) |
| `ballset` | `ball_set` | `ballstates` (both special an eighth of the time), `bothspecial` (both empty, both the whole line with zeros of either sign, one of each), `disjoint`, `touch`, `nested`, `overlap`, `wide` (huge radii, centers near $\Omega$), `point` |
| `ballsplit` | `ball_splits` | `ballstates`, `radii` (zero, $\eta$, odd multiples of $\eta$, subnormal, $\Omega$ and its predecessor, wide), `top` (centers near $\pm\Omega$) |

The conversions of two limbs keep the families of `gen6.py` (`ivmid`, `ballbound`, `ivmake`) with
two strata more for the bounds of two limbs (an operation key of their own, so that the families'
other kernels keep their streams): `beyond` (a bound $(\pm\Omega, \pm t)$, beyond $\Omega$ three
times in four: half-lines, points, bounded intervals) and `threshold` (a bound at
$2^{q_{\max}+p-2}$, the limit of `finite_when`, or a neighbour or a small tail off it) for
`interval_mid_rad_2`, `interval_to_ball_2` and `interval_split_2`; `threshold` ($\lvert c\rvert +
r$ about $2^{q_{\max}+p-2}$) and `zeroend` ($c = \pm r$: an end exactly zero) for
`ball_to_interval_2`; `ball_from_interval_1` has the strata of `ball_from_interval_2`. `enc_strata`
checks that the cases of each stratum have what it is for.

**What the reference runner, the interpreter and the compiled kernels reach** (2 000 cases per
format of seed 0): the centers of two limbs come to 0.08 to 0.25 of $3u^2/(1-4u)\lvert m\rvert +
2\eta$ in `binary64` and `binary32` and 0.5 in `fp:4:-6:1` (no floor: the bound is not claimed
tight); the bounds of `ball_to_interval_2` to 0.43 to 0.51 of theirs; the center of
`ball_from_interval_1` to 0.4 to 0.85 of $u\lvert m\rvert + \eta$.

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
  which (a) for any other $F$ can be read. A summary keeps its records only (below, "The size of a
  summary"), which give (a) for every $F$: `--verbose` on merged summaries lists those.

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

#### The size of a summary

What a summary keeps is bounded by the claims and the format, whatever the number of lines or of
elements judged. Per key (kernel, format, stratum) it holds counters, the reasons of failures
with their counts (a map's name the element, so that a failing run has at most one per element
index and reason) and at most `--max-examples` examples of each kind (failure, invalid,
suspicious), each a whole line; per entry of the claims a fixed set of statistics: the largest
ratio and (b), each named maximum and minimum, each with one case; counts, whose names the claims
and the format fix (a histogram has a bin per binade at most); and the profile of (a), at most
one record per distance $D$, whose range the format fixes (in binary64 from about $-1\,180$, a
product of two subnormal numbers, to about $2\,045$: some 3 200 values; a few tens in a toy
format), each with one case. A case is a line of the kernel judged, except in two places:

- the statistics of a map's step (the entries `entries(z), step K: ...`) keep the line of the
  element that attains them, a completed line of the step spelled with the map's own tokens,
  `STEP FORMAT OPERAND... #MAP:STRATUM:INDEX:element:I -> OUTPUT...`, which runs again as a line
  of the step with the same verdict (`maps.ElementLine`), never the map's line, which holds
  thousands of limbs;
- the profile keeps its records (`check.EntryStats.profile_records`): the distances whose ratio
  is at least every ratio at a larger distance, with their cases. The largest ratio over
  $D \ge F$, and its case, is a record's for every $F$, and the records of a merge are those of
  the merge of the records, so that (a) for any $F$, here and in the brute-force driver
  (`tests/brute/brute.py`, `observed_c`), is what the whole profile gave; `profile_distances`
  lists every distance seen (an integer alone or a range `[lo, hi]`), so that a merge orders
  equal ratios as before. A summary read back holds the other distances without their ratios.
  Equal ratios are all records, so a profile whose ratios are all equal, that of an exact
  operation (every ratio 0), keeps every distance seen: up to the range of $D$, whatever the
  number of lines.

A fold's or a convolution's statistics keep the fold's line (one per statistic, not per
distance). The largest summaries of the full tier are those of exact operations in binary64,
whose profiles keep nearly every distance of their strata: 2.0 MB for `two_prod` and
`two_prod_dekker` (some 13 000 records), 2.1 to 2.7 MB for the map `mul_pow2_map_1` (10 strata,
up to 2 100 distances each, a step's line of 144 bytes per record). Every other one is below
1.2 MB, and those above 0.5 MB are likewise of operations exact on all or most of their cases
(`two_sum` and its forms, `split`, `neg_2`, `abs_2`, the scalings by a power of two, `scale_1`).
Before the two changes above a map's was up to 1.7 GB, 99% of it the profile's cases, each a
whole map line. The cross-checks fail a summary above 4 MiB (`tests/crosscheck_guards.py`,
`SUMMARY_BYTES`), 1.55 times the largest.

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
- The folds' stage of Milestone 2 ([above](#the-kinds-of-the-folds-stage)): the form `T` of
  `error`; `count(NAME)` (a one-limb input, the finite domain) and `format(half)` (no input; a
  property outside the vocabulary refused) in `requires`; `upper` with `value` and `if` in place
  of `gaps`, `holds` with `rel`, two `args` and `if`, every entry of the kernel under a mask
  output and in the finite domain; `unit(K)` and `tiny(K)` naming a kernel of the claims with one
  `error` entry, readable (a kernel naming one that is not is set aside with it);
  `finite_or_nan` with `of`, a mask `flag` and a value that is the name of an input of as many
  limbs, in the extended domain, where a multi-limb input without `canonical()` or `ball()` is
  read as any limbs when every entry of the kernel is `finite_or_nan`. The list `"folds"`, absent
  or a list, each fold read as [Folds](#folds) says, with the same strictness (a name of a kernel
  or of another fold, a field of a kind outside its vocabulary, a step, combination or finish that
  is not a kernel of the file, the lane order without a combination, heights for another set of
  orders, an instance other than its expression, a fold of the finite domain or without
  `finite_or_nan`: set aside with the reason, a CLAIMS ERROR as for a kernel); fields outside the
  documented ones are warnings.
- The interval kernels ([above](#the-kinds-of-the-interval-kernels)): `interval(L, U)` and
  `not_nan(NAME)` in `requires` (the extended domain; a two-limb `not_nan()` input must be
  `canonical()`, the bounds of an `interval()` of two limbs are canonical by it, and an input is in
  one interval or ball at most); the kinds `outward` (`of` one two-limb output, `side`, `rel`,
  `abs`, optional `exact_when` and `zero_factor`), `makes_interval`, `encloses_interval`
  (`lower`, `upper`, `set` over the names of `intervals`, `tight`, `bounded_when`, optional
  `bounded_exactly` and `zero_factor`), `set_bound`, `interval_set`, `ball_of_interval`,
  `interval_of_ball` and `splits` with their fields, the extended domain only but `outward`;
  `encloses` with `"balls": {}` in the finite domain only; `makes_ball` with `from` `lower` and
  `upper` (one limb each) and `midpoint_when`; `zero_factor` on `bound` and `rounded`. Anything
  else in these is refused, as everywhere.
- The enclosure interface ([above](#the-kinds-of-the-enclosure-interface)): `certain` (`of` a
  mask, `rel`, `args`, `intervals` or `balls`, `exact` or `exact_when`) and `trit` (`yes` and `no`,
  two masks, a `rel` of `lt`, `le`, `eq`, `member`), the extended domain only, each set of an
  `interval()` or a `ball()` requirement and an argument, the point of `member` a limb input
  outside the sets, of one limb or of two required `canonical()`; `ball_set` (`center`, `radius`,
  `set`, two `balls` of the center's limbs) and `ball_splits` (`parts`, two balls of the center's
  limbs, `from` a ball); `finite_when` of `ball_of_interval` (`[{"abs_le": BOUND, "exp": E}]`,
  BOUND an input of `from`), the outward `tight` and `bounded_when` of `interval_of_ball` with
  bounds of two limbs, `rel`, `abs` and `smallest_radius` of `makes_ball` from an interval. A
  reason names the kernel, the entry and the field, a constant's included.
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

## Folds

```
kairn-oracle gen dot_2 binary64 --seed 0 --count 300 --max-length 256
kairn-oracle gen sum_2 binary32 --seed 0 --count 200 --orders lanes:4      # a packed runner's
kairn-oracle gen sum_1 fp:3:-3:0 --exhaustive --max-length 3                # every array
```

A fold (architecture.md, "Folds") is a loop of kernels along arrays: `sum_1`, `sum_1_entry`,
`sum_2`, `sum_2_entry`, `sum_fast_2`, `sum_fast_2_entry`, `dot_1` and `dot_2` so far. Its claims
are in the list `"folds"` of `gen/claims.json` (`folds.py` reads them: arrays with their limbs
and roles, outputs, `value` over the arrays' names, `requires` (`canonical()` of every array of
two limbs), `ensures` of the kinds `normalized`, `fold_error` and `finite_or_nan`, `orders`,
`packed_lanes`, `step`, `combine`, `finish`, `min_precision`, `status`, `theorems`, `source`,
`instances`), and its lines carry arrays, as the oracle reads them:

```
FOLD FORMAT ORDER N LIMB ... [#TAG] -> RESULT ...
```

`ORDER` is `seq` or `lanes:W` (W in decimal, no leading zero, 0 and 1 included); `N` the number of
elements, in decimal without a leading zero; then, for each array in the order of `arrays` and
each of its limbs, most significant first, the N entries of that limb (an element is one entry of
every array); the results are the fold's outputs, the flag `0` or `1`. A malformed line, an order
the fold does not claim, or a wrong number of limbs or results, is a failure.

**Judging** (`folds.py`), every line, in the extended domain (the only reading architecture.md
gives a fold; a fold of the finite domain is refused as a claim):

1. Requirements: every input limb a number of the format, $\pm\infty$ or NaN, every element of a
   two-limb array canonical (finite and normalized, $(\pm\infty, 0)$ or all NaN); otherwise the
   line is **invalid**. A precision below `min_precision` is out of scope.
2. `finite_or_nan` (required, one per fold: it is what says when the others hold): the flag is 1
   exactly when limb 0 of the result is finite; when it is 0 every limb of the result is a NaN;
   when it is 1 every element and every limb of the result are finite.
3. With a true flag, finite elements and a finite result: `normalized` (the invariant on the
   result), and `fold_error`:
   $\lvert r - \sum_i v_i\rvert \le ((1 + \mathit{term})(1 + \varepsilon)^{h_r} - 1)\sum_i\lvert
   v_i\rvert + (1 + \varepsilon)^{h_a}\,n\,\tau$, with $v_i$ the exact value of element $i$
   (`value`: the sum of its limbs, the product of two for a dot product), $h_r$ and $h_a$ the
   heights `rel` and `abs` of the order of the line (`sequential` for `seq`, `lanes` for every
   `lanes:W`), `n` or `n-1` with $0 - 1 = 0$, and `eps`, `term`, `tau` evaluated exactly in the
   format (the listed instance in a named format, which must equal the evaluation).
4. A false flag with finite elements is not claimed either way, but counted: `near overflow`, or
   `far from overflow` when every node of every summation tree is certainly below an eighth of the
   overflow threshold, $(1 + \mathit{term})(1 + \varepsilon)^{h_r}\sum\lvert v_i\rvert + (1 +
   \varepsilon)^{h_a} n \tau \le 2^{q_{\max} + p - 3}$ (milestone2.md's bound of the value of a
   tree), which also makes the line **suspicious**: the cross-checks fail on it.

**Exact and fast.** The values of the elements are integers at the scale of `value` ($\eta$ or
$\eta^2$); the bound's powers are bracketed: $(1 + \varepsilon)^h$ between two integers at the scale
$2^P$, $P$ the bits of the denominators of `eps` and `term` plus 96 plus twice those of $h$, by
binary powering with every product rounded down for the lower end and up for the upper end
(`pow_bracket`), once per height in a plan. A line whose error is at most the lower end of the
bound passes, one above the upper end fails, and one in between (none in any run so far: the
count `decided with the exact powers` says) is decided with the exact powers, integers of
thousands of bits for long arrays. The largest ratio error/allowed is kept exactly (a new
maximum is computed with the exact powers; terms of more than 4096 bits are rounded down to a
multiple of $2^{-128}$). The bound costs about 16 µs per new height (the brackets) and well under
a microsecond per line after; what costs is reading the line: a 1 000-element `sum_1` line is
judged in about 1.6 ms, a 1 000-element `dot_2` line (4 000 literals, 2 000 tests of canonical
pairs) in about 10 ms, and `check` reads about 2 500 lines of `dot_2` per second at the quick
tier's lengths (48 elements on average) (Apple M3 Max, under a load of about 25).

**Statistics**, per entry: for `fold_error`, the largest error/allowed (also per order:
`error / allowed, order sequential`, `... lanes`), the length of the arrays (`length 0` to
`length 17`, then `length 18 to 64`, `65 to 256`, `257 to 1024`, `1025 to 4096`, `above 4096`),
the order (`order: sequential`, `order: lanes, W = 0` to `8`, `W = 9 to 64`, `W above 64`, and
`more lanes than elements (W > n >= 1)`), `cancellation: |sum| <= sum of magnitudes / 2`,
`heavy cancellation: |sum| <= u * sum of magnitudes`, `exact sum zero, an element not zero`,
`|exact sum| > Omega`, `result exact` or `inexact`, and where $\tau > 0$ `absolute term larger
than the relative term` and `error above the relative term alone` (the case would fail without
$\tau$); for `finite_or_nan`, `flag true`, `flag false: a non-finite element`, `flag false:
finite elements, near overflow`, `... far from overflow`, `flag false: finite elements, |exact
sum| <= Omega` (partial sums overflowed although the exact sum did not), with the lengths and
orders of every line. The cross-checks' guards read these.

**Requests** (`genfold.py`). Random mode is counter-based: case $i$ depends on the fold, the
format, the seed, the strata, the orders and the largest length (all in the header, `orders=`
and `maxlen=`). Each case has a stratum (the schedule `one cancel tight wide underflow sign cancel
overflow tight nonfinite zeros pow2 tail`), a length (by a schedule of 17 places: 0, 1, 2, 3, 4,
5, 7, 8, 9, 16, 17, the lengths around each lane count W - 1, W, W + 1, 2W, 2W + 1 for W = 2, 4,
8, and six random lengths from 18 to `--max-length`, log-uniform; 17 is prime, so over 17 turns
every stratum meets every length) and an order drawn from `--orders` (default `seq` twice,
`lanes:0`, `1`, `2`, `3`, `4`, `5`, `8` and `lanes:big`, a number of lanes above the length). The
strata, of the values $v_i$ (the products $x_i y_i$ of a dot product, split into factors):

| Stratum | Elements |
|---|---|
| `one` | two adjacent binades, random signs |
| `wide` | any binade from the smallest up to a sum that cannot overflow, random signs |
| `sign` | all of one sign |
| `cancel` | one element (one factor) chosen so that the exact sum is far smaller than the sum of magnitudes: the nearest number of one or two limbs to minus the sum of the others, or pairs $v, -v'$ a few units apart |
| `zeros` | zeros of both signs among the elements, every element zero a quarter of the time |
| `underflow` | subnormal and low normal values near one another; products from below $\eta$ to past $2^{2kp}\eta$, where $\tau$ is the larger part of the bound |
| `overflow` | large values of one sign then of the other (partial sums overflow, the exact sum does not), $\Omega$ and a quarter of its unit or less (the exact sum beyond $\Omega$ rounds to it), sums that overflow, products near $\Omega$ |
| `nonfinite` | one to three elements infinite or a NaN ($(\pm\infty, 0)$, (NaN, NaN) for two limbs); for a dot product also $0 \cdot \infty$ |
| `tight` | a first element and others of its sign just below half a unit of it (for two limbs, of its second limb): each addition drops one, and the error comes to the bound for one limb; for two limbs, half of the time the literature's tight cases of the step or the combination (`tight.py`: MR22's and JMP17's for `add_2_2`, JMP17's for `add_fast_2_2`, MR22's and JMP17's for `mul_2_2`) scaled into the format by a power of two |
| `pow2` | short significands at nearby exponents: exact sums and ties |
| `tail` | (two limbs) leading limbs that cancel in pairs, second limbs at the extremes of the invariant |

Exhaustive mode (`--exhaustive --max-length L`) enumerates every array of every length up to L,
each element any value of its domain (every number of the format, $\pm\infty$ and NaN for one
limb; every canonical pair for two), in every order that differs: `seq`, and `lanes:W` for W from
2 to the length. Sizes: `sum_1` at `fp:3:-3:0` up to 3 elements 225 835 cases, `sum_2` at
`fp:3:-4:1` up to 2 elements 363 379, `dot_1` at `fp:2:-1:0` up to 2 elements 77 029, `dot_2` at
`fp:4:-4:-1` one element 62 501 (two elements of `dot_2` are more than $10^8$ in any format of its
precision). A sum of pairs needs exponents: in a format of fewer binades than twice its
precision, `fp:3:-2:-1` (four binades) or `fp:4:-4:-1` (seven), every sum of up to three pairs is
a pair, exact, and a run there checks nothing of the bound (the guards fail it); in `fp:3:-4:1`
and `fp:3:-3:0` the reference comes to 0.19 of it.

**What the reference implementation reaches**, the largest error/allowed in 400 cases of seed 0
(the interpreter and `refrun` agree bit for bit): `sum_1` 1.00 of its bound in `binary64` and
`binary32` (0.76 to 0.97 in toy formats), `dot_1` 0.99 (0.83 to 0.88), `dot_2` 0.9995 in
`binary64` with MR22's case of `mul_2_2` (0.17 to 0.36 elsewhere), `sum_2` and `sum_2_entry` 0.17
to 0.33 (MR22's case of `add_2_2` gives 1/3: its error is $3u^2$ of $\lvert x + y\rvert$, a third
of $\lvert x\rvert + \lvert y\rvert$), `sum_fast_2` 0.15 to 0.26.

`brute`, `search` and `shrink` of the oracle do not run folds (`tests/brute/brute.py` does, with
the oracle's `gen` and `check`).

A fold with `writes` but neither `"map": true` nor `"conv": true` is refused (a CLAIMS ERROR):
a fold that writes arrays is a map or a convolution, below.

### Maps

```
kairn-oracle gen axpy_2 binary64 --seed 0 --count 100 --max-length 24
kairn-oracle gen add_1 fp:2:-1:0 --exhaustive --max-length 2          # every array and order
```

A map (architecture.md, "Maps") writes an array: written element $z_i$ is its step, a kernel of the
claims, on the scalars and element $i$ of each array read, in the order of `step_args`. `maps.py`
reads it (`"map": true` in the list `"folds"`): arrays and scalars with their limbs and roles, one
array written, one mask output (the flag), `value` over the arrays and scalars, `requires`
(`canonical()` of every group of two limbs, `power_of_two()` of a one-limb scalar, which in this
domain is a finite power of two), the two entries `entries` (`of` the written array, `kernel` the
step) and `finite_or_nan` (`of` the written array, `flag` the mask), `orders`, `packed_lanes`,
`step`, `step_args`, `check`, `min_precision`, `status`, `theorem`, `source`. The step must be a
readable kernel of the finite domain whose inputs are, limb for limb, the groups of `step_args` and
whose one output has the written array's limbs; the map's value must be the step's on those
groups (compared as polynomials at random integer points, as a full kernel's value with its
core's); every requirement of the step on what the map passes must be the map's (`normalized()` as
`canonical()`, `power_of_two()` as itself); the minimum precision at least the step's; `check` a
kernel of the shape of `fold_finish_k`. Anything else is a CLAIMS ERROR, and a map whose step
cannot be read is set aside with it.

**Lines**: `MAP FORMAT ORDER N SCALAR... LIMB... [#TAG] -> Z... MASK`, the limbs of the scalars in
the order of `scalars` between the length and the arrays, the arrays as a fold's; the result, for
each limb of the written array, most significant first, its N entries, then the flag.

**Judging** (`maps.py`), every line, in the extended domain:

1. The line's form (order, length, counts of limbs and results, an order the map claims), then the
   requirements: every limb a number of the format or not finite, every group of two limbs
   canonical, a power of two finite; otherwise **invalid**. Then the written limbs must be
   numbers of the format or not finite and the flag `0` or `1` (otherwise a failure).
2. Each written element $z_i$, with $x_i$ the step's operands (the scalars and element $i$):
    - leading limb finite: every operand must be finite (otherwise `entries` fails: a finite
      element from an operand that is not finite), and the step's verdict on $(x_i, z_i)$ is
      the one a line of the step would get, by the same code (`check.Checker.verdict`, the
      requirements first by `check.Checker.violated`): its failures are failures of `entries`,
      and the statistics of each entry of the step are kept in entries of their own, after the
      map's two (`entries(z), step K: ...`), with the element's line of the step as their cases
      ("The size of a summary"). Where the step's claims leave a finite result
      unclaimed in the finite domain, the map's reading does not: a finite element whose step's
      exact result rounds beyond $\Omega$ (`rounded` of a one-limb step), or with a lower limb that
      is not finite, fails `entries`;
    - leading limb not finite: every limb must be a NaN, the canonical NaN of the second pass
      (otherwise `finite_or_nan` fails); from finite operands it is an overflow, counted, and
      **suspicious** when the operands and the exact value are below $\Omega/4$ (the step's own
      test of a suspicious non-finite result), which the cross-checks fail.
3. The flag: 1 exactly when the leading limb of every written element is finite (so 1 for no
   element, whatever the scalars).

An element of a map costs what a line of its step costs (the step's verdict and statistics), far
more than an element of a fold: on the Mac under a load of about 80, 41 µs per element of `add_1`
and 76 of `axpy_2` (16 and 41 ms for lines of 384 and 542 elements on average), against 8 µs per
element of `norm_upper_2` and 26 µs per term of `conv_2`.

Statistics, per entry: for `entries` the length and order classes of a fold and, per element,
`element: finite operands, finite result`, `element: finite operands, not finite (an overflow)`,
`element: a non-finite operand`; for `finite_or_nan` `flag true`, `flag false: a non-finite
operand`, `flag false: finite operands, an overflow`; for the step's entries those of a kernel's
(the largest error/allowed of an `error` entry, the outcomes of `rounded`, ...).

**Requests** (`genmap.py`). Random mode is the folds' (counter-based, the 17 places of lengths,
the orders drawn per case, all in the header). The scalars are drawn once per case for its
stratum; the elements are aimed at the corners of the step, three in four at the stratum's and the
others at an ordinary one (`one`), so that the overflow stratum has finite elements beside those
that overflow and the flag and the second pass are put to the test. The step is read from the
map's value: a sum or a difference of two arrays (`add_k`, `sub_k` and their entry forms), an
array times a scalar (`scale_k`), times a power of two (`mul_pow2_map_k`), $a x + y$ (`axpy_k`):

| Stratum | Elements |
|---|---|
| `one` | operands in nearby binades, random signs |
| `wide` | operands anywhere a result cannot overflow |
| `cancel` | the result cancels: $y$ within a few units of $-x$ ($x$ for a difference), of $-(a x)$ for axpy; a scalar of one bit for a scaling |
| `tie` | results halfway between two numbers: sums $N 2^E$ with $N$ odd; for a scaling of one limb $a = 3 \cdot 2^k$ and $x = m 2^e$ with $3m$ odd of $p + 1$ bits; for axpy $a x$ exact and $y$ an odd multiple of half its unit; for two limbs second limbs at half a unit |
| `exact` | short significands: results that are numbers of the format |
| `overflow` | results beyond $\Omega$ from finite operands (the top binades of one sign, $\Omega$ and half its unit, a scalar that brings the products past $\Omega$), beside finite ones |
| `underflow` | results in the subnormal range (a power of two or a scalar that scales into it) |
| `zeros` | zeros of both signs, a zero scalar, results that are exactly zero |
| `nonfinite` | one to three elements with an operand infinite or a NaN; a scalar not finite a quarter of the time; $0 \cdot \infty$ |
| `tight` | the closest to the step's bound: sums $2^E + u 2^E$ (a tie, an error of $u/(1+u)$ of the sum: the whole bound) and for two limbs the literature's case of `add_2_2` or `sub_2_2`; products just below a midpoint ($a = 1 + 2u$, $x = 1 - u$) and for two limbs the literature's case of `mul_2_1` or `mul_2_2` with the scalar its factor; axpy as the family `axpy`; for a power of two, products that are odd multiples of $\eta/2$ |
| `tail` | (two limbs) leading limbs that cancel, second limbs at the extremes of the invariant |

Exhaustive mode enumerates every value of each scalar (every power of two for `power_of_two()`)
with every array up to `--max-length`, every order that differs. Sizes: `add_1` at `fp:2:-1:0`
up to 2 elements 77 029; `add_2` at `fp:3:-4:1` one element 181 477; `axpy_1` at `fp:3:-3:0` one
element 74 130, `axpy_2` at `fp:4:-3:-2` 262 208, `axpy_2_1` at `fp:3:-2:-1` 26 650; `scale_1` at
`fp:3:-3:0` up to 2 149 982, `scale_2` at `fp:2:-2:1` up to 2 149 314; `mul_pow2_map_1` at
`fp:4:-5:0` up to 2 234 963, `mul_pow2_map_2` at `fp:3:-3:0` up to 2 179 346 (two elements of a
map of pairs, or of axpy, are more than ten million arrays in any format of its precision).

What the compiled runners reach in the quick tier's 100 arrays per format, `binary64` and
`binary32` (the largest error/allowed of the step's error entry; the interpreter writes the same
bits): 1 for the steps of one limb (`add_1`, `sub_1`, `scale_1`, `mul_pow2_map_1` and the entry
forms: exactly 1 at a tie; axpy $1 - O(u)$), $1 - 8u$ for the sums of two limbs (MR22's case of
`add_2_2`, asymptotically optimal), 0.69 to 0.99 for `scale_2`, 0.50 to 0.57 for `mul_pow2_map_2`,
0.39 to 0.57 for `axpy_2` and its entry form, 0.57 to 0.74 for `axpy_2_1` and its entry form; in
the full tier's 1 000 arrays 0.61 to 0.71 for `axpy_2`, 0.77 to 0.80 for `axpy_2_1`, 0.75 for
`mul_pow2_map_2`, 0.98 to 0.99 for `scale_2`, and in its toy formats 0.44 to 1.

**In-place use** (architecture.md, "The line protocol": an array written may be exactly one of the
arrays read): a request `MAP FORMAT ORDER N inplace=I SCALAR... LIMB...`, the field after the
length, asks the runner to pass array I (counted from 0 among the arrays read, one of the limbs of
the array written) as the array written, the same storage. The operands are those of the request,
and the oracle judges the line as it judges the request without the field, element by element,
which is what in-place use must preserve (every element read whole before it is written), and
counts `in place: array I`; a field that names no array read of the limbs of the array written,
or is not a number written without leading zeros, makes the line malformed. `gen --inplace` (a
map's or a ball vector's random run) writes every request with the field, I in turn over the
arrays that can be written, the header `inplace=yes`, a stream of its own seed; a fold without an
in-place form refuses it. `tests/crosscheck.py --inplace` runs it through every runner as one more
stream (and for the packed runners one more), which the guards require to be in place, every
array of them seen (`in place: array I`); the reference runner reads the field and computes the
same values.

### Folds of maxima

```
kairn-oracle gen norm_upper_2 binary64 --seed 0 --count 100 --max-length 24
```

A fold of maxima (architecture.md, "Folds of maxima") is read by `folds.py` as a fold, with the
entry `upper` (`of` one one-limb output, `over: max`, `steps` an integer $S \ge 0$) in place of
`fold_error` (a fold with both is refused), and judged as a fold: requirements, the flag, then,
with a true flag, finite elements and a finite result, `upper`: with $V = \max_i v_i$ ($v_i$ the
exact value of element $i$, `abs(x)`: for two limbs $\lvert x_0 + x_1\rvert$; $V = 0$ for no
element), $V \le r$ and $r$ is $\mathrm{RU}(V)$ stepped up at most $S$ times, $\mathrm{RU}$ in the
format with overflow (a $V$ above $\Omega$ leaves no finite $r$). For one limb $r = V$.

**The flag with finite elements.** architecture.md: "the flag is true exactly when the result is
finite ...; a NaN or infinite element, or a result whose step up is infinite, gives the flag false
and a NaN". It leaves open whether a false flag from finite elements is a failure when the bound
has a finite top. The stricter reading is taken: with every element finite the flag may be false
only where $\mathrm{RU}(V)$ stepped up $S$ times is $+\infty$ ($V > \mathrm{pred}(\Omega)$ for two
limbs, never for one), which is the only false flag the listing gives ($m = \Omega$, whose step
up is $+\infty$); any other false flag from finite elements fails `finite_or_nan`. (Under the other
reading it would be suspicious only, as a fold's false flag far from overflow is, which the
cross-checks fail all the same.)

Statistics of `upper`: the length and order classes, `result at RU(V)`, `result 1 step above
RU(V)`, `V a number of the format` or not, `no element: V = 0`, `every element zero`, where the
largest is (`the largest at the first element`, `... at the last element`, `... at another
element`, `the largest attained more than once`), and the largest number of steps above
$\mathrm{RU}(V)$ (the fraction of the bound used: 1 of 1 for `norm_upper_2`); of `finite_or_nan`,
besides a fold's, `flag false: finite elements, the bound's top beyond Omega`.

Its kernels claim kinds of their own:

- **`maximum`** (`of` a one-limb output, `args` two expressions of the language of `value` in which
  `NAME[I]` is limb I of an input, as in `exact_when`), the finite domain: the output is the
  larger of the exact values of the two arguments. Counted: `first argument larger`, `second
  argument larger`, `arguments equal`, `arguments of both signs`. The mask outputs of
  `norm_combine` and the steps are claimed by nothing (the generator checks that they are the `and`
  of the masks); the fold's flag is what judges them.
- **`finite_or_nan` with `if` and `steps`** (`if` a mask input, `steps` an integer $\ge 1$, absent
  for none; a value of one limb): with $t$ the value stepped up $S$ times by IEEE 754's nextUp (a
  NaN stays a NaN, $+\infty$ stays, $-\infty$ goes to $-\Omega$, $\Omega$ to $+\infty$), the flag is
  true exactly when the mask is true and $t$ is finite, and the output is then $t$; otherwise
  every limb is a NaN. So `norm_finish_2` of $(-\infty, \text{true})$ is $-\Omega$ with a true flag,
  a state the fold never has (its maximum is a magnitude). Counted: `mask true`, `mask false`,
  `value finite, stepped up finite`, `value finite, stepped up +inf`, `value: NaN`, `value:
  infinite`.

**Requests** (`genmap.py`), as a fold's, with strata that place the largest magnitude: `one`,
`wide` (magnitudes in two adjacent binades, or anywhere), `ties` (the largest attained more than
once, with both signs and other tails), `position` (the largest first, last, at the end of a lane
or the start of the remainder), `zeros` (every element zero half of the time), `underflow`, `top`
($(\Omega, t)$ with $t < 0$, whose step up is $+\infty$; with $t > 0$, beyond $\Omega$; the
predecessor of $\Omega$ with half a unit above; $\Omega$ alone), `nonfinite` (an infinity or a NaN
anywhere, the last element a quarter of the time), `tail` (two limbs: the largest leading limb with
a tail of its sign, of the other, or zero). Exhaustive mode as a fold's: `norm_upper_1` at
`fp:3:-3:0` up to 3 elements 225 835, `norm_upper_2` at `fp:3:-4:1` up to 2 363 379.

### Convolutions

```
kairn-oracle gen conv_2 binary64 --seed 0 --count 100 --max-length 20
kairn-oracle gen conv_1 fp:2:-1:0 --exhaustive --max-length 2       # both lengths up to 2
```

A convolution (architecture.md, "Convolutions"; `"conv": true`) is read by `maps.py`: two arrays,
one written, one mask, `orders` the sequential one only, the two entries `coefficients` (`of` the
written array, `fold` the fold of the coefficients, which `coefficients` names too) and
`finite_or_nan`, `check`. The fold of the coefficients must be a readable fold of the list (a sum,
not a map, a convolution or a fold of maxima) with the sequential order and the convolution's
arrays, value and requirements; convolutions are read after the other folds, whatever the order
of the list.

**Lines**: `CONV FORMAT seq N_X N_Y LIMB... [#TAG] -> Z... MASK`, the limbs of the first array
($N_X$ entries each), then those of the second; the result $N_Z = N_X + N_Y - 1$ entries per limb
($0$ when a length is $0$), then the flag. Any order but `seq` fails.

**Judging**: requirements as a map's; then each coefficient $j$, with its terms $(x_i, y_{j-i})$ for
$i$ from $\max(0, j - n_y + 1)$ to $\min(j, n_x - 1)$, in increasing order, $m_j$ of them: leading
limb finite, every term must be finite and every limb of the coefficient finite (otherwise
`coefficients` fails), and the entries of the fold of the coefficients other than `finite_or_nan`
(`normalized`, `fold_error` with the heights of its sequential order and $n = m_j$) are judged on
the list of its terms by the code that judges a line of that fold (`folds.py`: its plan, `_Case`
and `_fold_error`), with their statistics in entries of their own (`coefficients(z), fold dot_2:
...`); leading limb not finite, the canonical NaN, and from finite terms suspicious when every
partial sum of the terms is below an eighth of the overflow threshold (the fold's test). The flag
is a map's.

Statistics of `coefficients`: `n_x = 0`, `= 1`, `= 2` or `above 2`, the same of $n_y$, `n_x = n_y`
or `n_x != n_y`, `terms at most ...` (the class of $\min(n_x, n_y)$), and per coefficient
`coefficient: finite terms, finite result`, `... not finite (an overflow)`, `coefficient: a
non-finite term`; the fold's entries count the number of terms of each coefficient as the length
of its array (`length 1`, `length 2`, ...).

**Requests**: two lengths by a schedule of 13 places that pairs 0 and 1 on either side with
other lengths and unequal lengths with each other ((0, 0), (0, s), (s, 0), (1, 1), (1, s), (s, 1),
(2, 3), (3, 2), (s, s), (1, r), (r, 1), (r, s), (s, r): s from 2 to 9, r random from 18 to the
largest); the strata of the dot products (genfold.py), with `cancel` making one coefficient cancel
and `tight` $y$ all ones and $x$ the tight case of a sum, so that every coefficient is a sum near
its bound (or $x$ all ones and $y$ the sum reversed; for two limbs, a quarter of the time, the
literature's case of `mul_2_2` as the first term). Exhaustive mode: both lengths up to
`--max-length`, every array: `conv_1` at `fp:2:-1:0` up to 2 and 2, 44 521; `conv_2` at
`fp:4:-4:-1` up to 1 and 1, 63 001.

What the compiled runners reach in the quick tier's 100 pairs per format: `conv_1` 0.95 to 0.98
of the bound of `dot_1`, `conv_2` 0.9995 in `binary64` (MR22's case of `mul_2_2`) and 0.48 in
`binary32`; in the full tier's 300, `conv_1` 0.99 to 1.00 and `conv_2` 0.71 in `binary32`.

## Ball vectors and the accumulator

architecture.md, "Ball vectors", "The accumulator" and "Claims of Milestone 2" (the forms their
kernels use); `bvec.py`, hooked into `claims.py`, `check.py` and `extended.py` as `intervals.py`
is; their requests `gen8.py`; their reference `refbv.py`, which `refrun` installs.

### Their kernels

The forms these kernels add to kinds that exist, each read as architecture.md writes it and
refused otherwise (a CLAIMS ERROR naming the kernel, the entry and the field):

- **`upper` with `value` and no `if`** (the radius kernels `bv_add_radius_k`, `bv_scale_radius_k`,
  `conv_radius`, `bv_mul_pow2_radius`), the finite domain: the output is at least the exact value
  of `value`, unconditionally, whether it is finite or the rounding overflowed to $+\infty$;
  nothing is said of how far above. `value` is the language of the bound kernels' values
  (`cexpr.py`) with **`abs(NAME)`** of an input, its exact magnitude. A kernel with such an entry
  has only such entries (or the claims are refused) and is judged on every line
  (`bvec.judge_radius`): a NaN or $-\infty$ output fails, $+\infty$ passes and is **suspicious**
  where every operand and the stated value are below $\Omega/4$, a finite output below the value
  fails. With **`unless: M`** (a mask input) the entry says nothing where M is true; with
  **`exact_when`** (`mask(NAME)`, `{"mask": M}`, a condition that M is true, beside the conditions
  of `error`, which an `exact_when` of masks alone may not do without) the output is the value
  exactly where every condition holds, and $+\infty$ there fails. `unless` and `exact_when` are
  refused beside `if` or `gaps`, and together.
- **`conv_radius`**, whose claim is of finite results by the owner's ruling of 2026-11-21
  (architecture.md, "Claims of the non-finite layer", "`upper` of a kernel of the finite domain
  with several operations"; `bvec.FINITE_RESULTS`: the claims file writes its entry as the other
  radius kernels', so the name comes from the ruling): a finite output is judged as above (at
  least the stated value), and one that is not finite claims only that it is $+\infty$ or a NaN.
  Either passes and is **counted** (`output not finite (+inf or a NaN): nothing more claimed`,
  with `output +inf` or `output a NaN`), from any operands, never suspicious; $-\infty$ fails, and
  so does a negative number (below the stated value, which is not negative).
- **`at_most(NAME, K)`**, a requirement of the finite domain: the one-limb input is at most the
  positive integer K; a line beyond is **invalid**, `gen` draws no operand beyond (`gen.valid`,
  `gen8.valid8`) and the enumeration's domain stops at K.
- **`exact_flag: M`** of an `error` entry with `exact_when` (the steps `bv_mul_pow2_step_k`): the
  mask output M is true exactly when every condition holds, judged where output limb 0 is finite,
  as the rest of the entry (`failed exact_flag`).
- **`finite_or_nan` with `nonneg: true`** (with `if`, without `steps`: `bv_make_finish`) and with
  **`if_all: [M1, M2, ...]`** (two masks or more, without `if`, `steps` or `nonneg`:
  `bv_conv_finish`), the extended domain: the flag is true exactly when every mask is true, the
  value is finite and, with `nonneg`, not below zero (either zero is not); the output is then the
  value, otherwise a NaN (`bvec.k_finish`).
- **`rounded` with `value: EXPR`** (the accumulator's sum of magnitudes, `acc_add_k`,
  `acc_mul_k`, `acc_merge_k`), the finite domain: the output is EXPR rounded to nearest, EXPR an
  expression of the inputs and their limbs `NAME[I]`. Such a kernel is judged entry by entry, each
  where the leading limb of its own output group is finite (`bvec.judge_acc`, the reading of
  architecture.md for an entry about a group other than the first): an entry whose group is not
  finite claims nothing (counted), and a finite group whose exact value rounds beyond $\Omega$
  fails, for the kernel's own value as for EXPR (a finite running sum beyond the range, a finite
  sum of magnitudes where it overflowed). The line is suspicious, as everywhere, where a group is
  not finite from operands and values below $\Omega/4$.

The copies and constructors (`bv_center_entry_1`, `neg_1`, `bv_neg_radius`, `bv_make_radius`:
`rounded` to nearest of an input or its negation; `bv_center_2`: the claims of `neg_2` with the
value `x`) and the radius of an accumulator (`acc_radius_k`: `upper` with `if` and `holds`) claim
kinds that exist and are judged as before. One reading changed for them, which no earlier kernel
reaches: an `upper` or `holds` entry under a mask whose output is not finite where the mask is
true is suspicious only where every input and the stated value are below $\Omega/4$ (the finite
layer's definition); `acc_radius_1` of a sum of magnitudes near $\Omega$ overflows inside, $c(1 + w)$,
and returns $+\infty$ with `ok` true from a small stated value.

**Requests** (`gen8.py`), before every earlier family; the copies keep the unary family of
`gen2.py`, `bv_center_2` that of the non-finite layer and the steps the scale family:

| Family | Kernels | Strata of its own |
|---|---|---|
| `radius` | every entry an `upper` with a value and no `if` | `huge` (the top binades: the radius overflows), `zeros` (most operands zero, the count zero), `mixed` (one operand $2^p$ to $2^{3p+4}$ above the others), `atnormal` ($r_x c$ exactly $N$, just below, just above, or zero; the mask both ways); for `conv_radius`, whose results that are not finite are judged no further, every stratum but `overflow` and half of `huge` scales the operands down together until the stated value, with `g` at its bound 1 and the count at least 1, is at most $\Omega/8$ ($\Omega/2$ in `huge`): no product of the listing overflows there, and the finite results are some 80 to 85 % of a run (`gen8._within`) |
| `acc` | a `rounded` entry with a value | `cancel` (the element within a few units of minus the running sum), `tie` and `exactprod` (short significands within two binades: ties and exact sums of magnitudes), `apart` ($a$ far above or below what is added), `atop` ($a$ in the top binades: the sum of magnitudes $+\infty$ beside a finite running sum, A4 of `accumulator.py`) |
| `accradius` | a `count()` under masks, no `unit( )` | `integer` (integers from 1 to $2^p$, $g$ and $t$ of the size of the bound of $m$ terms), `limit` ($m u$ within a quarter of $\tfrac12$), `beyond` ($m u$ above $\tfrac12$), `abig` ($a$ in the top binades); every stratum keeps the stated value below $\Omega/8$ |
| `bvfinish` | `finite_or_nan` with `nonneg` or `if_all` | `nonfinite`, `negative` ($-\eta$, $-\lambda$, $-\Omega$, random), `zeros` (either sign), `top` ($\Omega$, its predecessor), `masks` (a positive value, each mask both ways) |

**Statistics** (the guards read them): for `upper` with a value `output finite, at least the stated
value`, `output +inf`, `output the stated value exactly`, for `conv_radius` `output a NaN` and
`output not finite (+inf or a NaN): nothing more claimed` (the guards ask that finite results be
at least three quarters of those judged), `M true: nothing claimed`, `exact_when
holds`, `exact_when fails: COND` (`M true` for a mask), `exact_when holds, the stated value beyond
Omega: the equality not judged`, and the extremes of (output $-$ value)/value and of the excess
in gaps; for `exact_flag` `exact_flag true` and `false`; for the finishes `every mask true`, `a
mask false: M`, `value finite, below zero`, `value zero`, `value finite, above zero`, `value:
NaN`, `value: +inf`, `value: -inf`; for `rounded` with a value `exact`, `tie`, `inexact`, `the
exact value rounds beyond Omega` and, per group, `the leading limb of its output is not finite:
nothing claimed`.

Readings chosen where the documents leave a choice, the stricter where they differ:

- A NaN output of a radius kernel fails: "the output is at least the exact value of value,
  whether it is finite or the rounding has overflowed to $+\infty$" names those two outputs. Not
  of `conv_radius`, whose claim the ruling of 2026-11-21 makes one of finite results (above).
- The equality of `exact_when` on an `upper` entry where the stated value is beyond $\Omega$: no
  number of the format is that value, and in the finite domain an exact result beyond $\Omega$ is
  outside the statement, as everywhere: counted, not judged ($+\infty$ passes the bound).
- `nonneg` and `if_all` of a value of one limb only; `rounded` with a value and `when` together
  refused (the vocabulary gives them separately).

**Not judged, and why**: what the accumulator's design page states of a sequence of calls (A1,
$\sum_i\lvert x_i y_i\rvert \le (1+u)^{n+2}(a + \tfrac12 n\eta)$, and the chain A3 to the radius):
the claims are of single steps, each kernel's line judged alone; and `ok` false for $a = +\infty$
or a NaN, which the claims of `acc_radius_k`, of the finite domain, do not state (no finite
operand is $+\infty$). The masks the steps of a scaling and-ed into the fold's `ex` are judged by
`exact_flag`; how the fold uses them, by the fold's claims.

**Findings, and the ruling on them**: `conv_radius` returns a NaN where the product `prod(ma, mb)`
overflows and `g` (or `m`) is zero, an FMA of $0 \cdot \infty$ (`conv_radius binary64 0x1p+1000
0x1p+1000 0x0p+0 0x0p+0 0x0p+0 0x0p+0 0x0p+0 -> nan`, a stated value of 0, the interpreter and
`refrun` alike), and $+\infty$ from operands and a stated value far below $\Omega$ when $g$ is
small (`conv_radius binary64 0x1p+1000 0x1p+1000 0x0p+0 0x0p+0 0x1p+0 0x0.0000000000001p-1022
0x0p+0 -> inf`, a stated value of about $2^{926}$); in 400 random cases of each of three formats,
72 such lines, which failed or were suspicious, and the kernel stayed on the list of
tests/CMakeLists.txt. The owner's ruling of 2026-11-21 made its claim one of finite results (the
product of BallVectors turns a radius that is not finite into the whole space): both lines pass
now, counted, and `conv_radius` is cross-checked as the other radius kernels are.

The reference runner's variants of these kernels (`refrun --list-variants`, `bvr-*`, `bvs-*`,
`bvc-*`, `bvf-*`, `acc-*`) plant one fault each: the term of the largest magnitude left out, a
NaN for an overflow (a fault of every radius kernel but `conv_radius`, whose NaN the ruling
allows), the radius of a scaling grown where exact or not grown where `ex` is false,
`conv_radius` without its term in $g$, `conv_radius` with $-\infty$ where its result is a NaN and
$-\Omega$ where it is $+\infty$, the mask of a step inverted or always true, a negation that
does not negate, a constructor's radius zero, `bv_center_2` without its second limb, a finish that
ignores the sign or a mask, a sum of magnitudes signed or $\Omega$ at an overflow, the radius of an
accumulator with `ok` always true or without $t$.

### Their folds

The ball vectors (architecture.md, "Ball vectors", and "Claims of Milestone 2", the kinds
`encloses_entries`, `makes_ball_vector` and `encloses_coefficients`), read by `bvfolds.py` from a
fold with `"bv": true` or `"bv_conv": true` and judged by it (`folds.judge_line` hands it the
line); their requests `genbv.py`; their reference `refbv.py`. A request is a fold's (`BV FORMAT
ORDER N [inplace=I] SCALAR... LIMB... -> Z... R FLAG`, the scalars first, the radii among them,
each array's limbs column by column); a product's `BV_CONV FORMAT seq N_X N_Y RX RY LIMB... -> Z...
R FLAG`, $n_x + n_y - 1$ coefficients (none when a length is 0).

- **`encloses_entries`** (`bv_add_k`, `bv_sub_k`, `bv_scale_k`, `bv_neg_k`, `bv_mul_pow2_k`): an
  operand is a BallVector when its radius is finite and nonnegative with every center finite and
  normalized, or its radius $+\infty$ with every center zero (the whole space); any other operand
  makes the line **invalid**, as a scalar under `power_of_two( )` that is not a positive power of
  two. **V1**: the result is one of the two (`failed V1`). **The flag** is true exactly when the
  radius is finite. **V2**: where the result is finite, for every entry the set's range over the
  balls (exact, over the extended reals) is within the radius of the center written (`max(c - lo,
  hi - c) <= r`), and an unbounded range fails. **V3**: a finite result comes only from finite
  BallVectors and finite scalars; then each center written satisfies the step's claims on its
  entry (the step's own plan: `error`, `normalized`, `rounded`; the masks of a scaling's step
  through its `exact_flag`), and the radius those of the radius kernel at m, the largest magnitude
  of a leading limb written (+0 for no entry), the scalars and, for a scaling, the and of the
  step's masks: the readings of the brief and of the listings, which architecture.md's V3 states
  less of ("the radius is finite"). **V4**: where every operand is a finite BallVector, every
  scalar finite, and every condition of `radii_when` (on the scalars) and of `finite_when` (each
  entry) holds, the result is finite; claimed from `finite_from` (the precision; below it `V4 not
  claimed: below finite_from`) and judged only in the formats its statements quantify over (below).
  **Exactness**: where the operands and the result are finite and every condition of
  `exact_when` holds (always, for `[]`), every entry's ball is exactly the set's range (`c - r =
  lo` and `c + r = hi`); each failing condition is counted.
- **`makes_ball_vector`** (`bv_make_k`): the whole space exactly when the radius given is negative,
  a NaN or $\pm\infty$, or the leading limb of a center given is not finite; otherwise the centers
  and the radius given, as values (the sign of a zero is not part of the claim); `canonical(c)` of
  two limbs required (invalid otherwise).
- **`encloses_coefficients`** (`bv_conv_k`): V1, the flag and V2 as above, coefficient by
  coefficient, the set's range a sum over the terms of the coefficient; V3: a finite result only
  from finite operands, each coefficient the fold's centers on its terms (the convolution's
  `normalized` and `fold_error` judged as `conv_k`'s), and the radius at least `conv_radius`'s
  stated value at the maxima of the leading limbs, the count $\min(n_x, n_y)$ rounded up and the
  smallest $g$ and $t$ of the bound's claims; V4 where every condition of `count_when` holds,
  each an expression **evaluated with `n`** the count (`le(EXPR, K)`: EXPR $\le$ K), and
  `radii_when` and `finite_when` (per pair, per entry of either array with the other's radius,
  or once) hold.

**The formats of V4**, and of every clause that promises a finite result. The rule, by the
owner's ruling of 2026-11-21 (architecture.md, "Number formats", "The formats of the statements"),
in the same words in docs/developer/testing.md: *the generated statements quantify over the
formats of `binary_float` ($e_{\max} > p$, smallest exponent $3 - e_{\max} - p$; in this oracle's
terms $q_{\max} \ge 1$ and $q_{\min} = 3 - q_{\max} - 2p$); a clause that promises a finite result
(V4, `finite_when`, `radii_when`, `count_when`) is claimed there, and the oracle may also judge it
in a format with a wider subnormal range, where nothing is proved and a failure would be a finding
to report, not a violated claim; in any other toy format it is not claimed, and the oracle counts
that.*

- V4 of the ball vectors and of the products of two BallVectors, with their `finite_when`,
  `radii_when` and `count_when`, follows it (`bvfolds.v4_range`): judged where $q_{\max} \ge 1$
  and $q_{\min} \le 3 - q_{\max} - 2p$, a failure in a format of a wider subnormal range saying
  that it is a finding, not a violated claim (`bvfolds.v4_beyond`), and counted `V4 not claimed:
  a format of no statement (e_max <= p, or eta above binary_float's)` elsewhere.
- `finite_when` of `ball_of_interval` (`interval_mid_rad_2`, `interval_to_ball_2`) and
  `bounded_when` of `interval_of_ball` with bounds of two limbs (`ball_to_interval_2`), the
  conversions of two limbs of stage B2, follow it too (`intervals.statement_format`, which reads
  `bvfolds.v4_range` and `bvfolds.v4_beyond`): judged in the same formats, a failure in a format of
  a wider subnormal range saying that it is a finding, and counted `finite_when not claimed: a
  format of no statement (e_max <= p, or eta above binary_float's)` (`bounded_when not claimed:
  ...`) elsewhere, the conditions then not counted, which the guards ask a run in such a format to
  say; with `ball` the center, which is claimed with the clause, is not judged there either, and
  with `ieee1788` the center of 1788 is judged in every format (but its being finite, below). The
  formats of their cross-checks
  (`binary64`, `binary32`, `fp:3:-4:1`, `fp:4:-6:1`) are all of `binary_float`'s shape, so the
  rule changes no verdict there; the selftest's enumerations in `fp:3:-2:-1` ($q_{\max} < 1$)
  count the clause as not claimed, where it was judged (and passed) before, and so do six of the
  brute-force plan's enumerations of the three kernels (`fp:4:-4:-1`, `fp:4:-5:0`, `fp:5:-7:0`,
  `fp:6:-8:-1`): on five of them, judged through the interpreter by the oracle before the rule and
  after it, every line has the same verdict. 13 hand-judged lines (`enc_judge`) and seven mutants
  hold it.
- The midpoint of a bounded interval of `ball_of_interval` with `ieee1788` (`interval_mid_rad_1`,
  `interval_mid_rad_2`), a finite canonical number, and what `splits` claims of the parts that rest
  on it (`interval_split_1`, `interval_split_2`: each a canonical interval, the two meeting at a
  point of $X$), follow it too, by a second ruling of 2026-11-21: the sum of the two
  halves of two limbs is proved finite where $e_{\max} > p \ge 3$, and below that it can overflow
  and the midpoint is a NaN. Through `intervals.statement_format`, they are judged in the formats
  of the statements as before, a failure in a format of a wider subnormal range saying that it is
  a finding, and in any other format counted on every bounded $X$, `a finite center not claimed: a
  format of no statement (e_max <= p, or eta above binary_float's)` (`a split at a point of X not
  claimed: ...`), which the guards ask a run in such a format to say. There a center that is not
  finite (a limb a NaN or an infinity) is counted (`bounded X, the center not finite (not
  claimed)`) and judged by what does not rest on it, containment: no real number is within a
  finite radius of a center that is not finite, so the radius must be $+\infty$; and a point of
  split that is not finite is counted (`bounded X, the point of split not finite (not claimed)`)
  and judged by the rest of the clause: the first part's lower bound is $X$'s, the second's upper
  bound $X$'s, and the first part ends with the limbs the second begins with (a NaN matching a
  NaN). A finite center or point of split is judged as everywhere, and so is an unbounded or empty
  $X$. The brute-force plan's enumerations found the case: in `fp:4:-4:-1` and `fp:4:-5:0`
  ($q_{\max} < 1$) `interval_mid_rad_2` gives `nan nan inf` and `interval_split_2` the point of
  split `nan nan` on 12 of 31 124 and 60 of 493 520 lines, every one a bounded interval whose two
  leading limbs are both $-\Omega$ or both $\Omega$, a bound beyond it
  (`interval_mid_rad_2 fp:4:-4:-1 -0x1.ep+2 -0x1.8p-3 -0x1.ep+2 -0x1.8p-3 -> nan nan inf`): they
  failed before the ruling and pass, counted, after it. 34 hand-judged lines (`enc_judge`), a
  planted fault (`enc-mid2-nan`, below) and 14 mutants hold it.
- The `finite_when` of the Milestone 1 kernels (F3 of `extends`, B4 of `encloses`: the full
  kernels, the full Ball kernels, `ball_narrow_2_1`) and the `bounded_when` of the interval
  kernels (I5), clauses of the same sort, are judged in **every** format, those outside
  `binary_float`'s included: stricter than the rule. Thirteen of the 28 kernels judged with such a
  clause have the toy format of their full tier outside it (`add_2_1_full`, `sub_1_2_full`,
  `sub_2_1_full`, `mul_2_1_full` in `fp:4:-5:0`, `mul_pow2_2_full` in `fp:5:-7:0`,
  `mul_2_2_full` and `ball_mul_2_full` in `fp:4:-4:-1`, `ball_add_2_full`, `ball_sub_2_full`,
  `interval_add_2` and `interval_sub_2` in `fp:3:-2:-1`, `ball_scale_2_full` in `fp:3:-3:0`,
  `interval_mul_2` in `fp:4:-3:-2`), and `interval_add_1` and `interval_sub_1` their sampled
  format `fp:5:-7:0`; there the clause is judged and passes (F3 applies on 15 165 of the 62 500
  operands of `mul_2_2_full` in `fp:4:-4:-1`, B4 on 1 525 of the 122 500 of `ball_add_2_full` in
  `fp:3:-2:-1`, every one finite). To count those lines as not claimed would stop judging lines
  that pass today, so they are judged as before; a failure there would be a finding, not a
  violated claim.

Outside the formats of V4 it fails as written: in `fp:2:-1:0` ($e_{\max} = 1 < p$) the
constant `up((1+u)*((1+u)^2*eta+eta/2)+eta/(2*u))` of `bv_add_radius_1` is $3 = \Omega$ and
`bv_add_1 fp:2:-1:0 seq 0 0x1p-1 0x0p+0 -> inf 0` (the interpreter's line) is the whole space
from $r_x = \tfrac12$; in `fp:2:-1:1` (an $\eta$ of $\tfrac12$, twice binary_float's) `bv_add_1`,
`bv_sub_1`, `bv_scale_1` and `bv_scale_2` fail likewise (144 of 14 722 requests of one entry for
`bv_add_1`). These are not findings: no statement covers those formats.

**Requests** (`genbv.py`): the folds' random mode (the 17 places of lengths, the orders per case)
with strata of their own, in the header and as tags:

| Shape | Strata |
|---|---|
| ball vectors | `one`, `wide` (radii above the centers), `zeroradius`, `whole` (an operand, or both, the whole space), `overflow`, `threshold` (the largest value of a condition of `finite_when`, or `radii_when` with no entry, in (lim/4, lim] or just above), `cancel`, `underflow`, `zeros`, `nonfinite` (a scalar not a radius, infinite or a NaN; `bv_scale_k`), `exact` (`exact_when`: the limbs and the radius times $c$ at, just below and just above $N$, or zero), `tail` (two limbs: second limbs at the extremes of the invariant) |
| constructors | `one`, `badradius` (each class of the radius given: negative, $-\infty$, NaN, $+\infty$, $+0$, $-0$, positive), `badcenter` (a center infinite or a NaN), `zeros`, `overflow`, `underflow`, `tail` |
| products | the strata of a ball vector but `nonfinite` and `exact`, and `count` (the count at the edge of `count_when`, from one below to two above the largest count of which it holds, where that is within the largest length) |

`gen --exhaustive` enumerates every canonical BallVector of a tiny format up to a length (every
nonnegative radius with every finite entry, normalized pairs for two limbs, and the whole space),
every value of the other scalars (the positive powers of two under `power_of_two( )`, every value
and $\pm\infty$ and a NaN otherwise), every order that differs (`seq`, `lanes:W` for
$2 \le W \le n$); for a constructor every radius and center given (canonical pairs); for a product
both lengths up to the largest.

**Statistics** (the guards read them, on the fold's claim): `result: finite ball vector`, `result:
whole space`, `operands: a whole-space operand`, `operands: a scalar not finite`, `operands: finite
ball vectors, finite scalars`, `V4 applies`, `V4 applies, no entry`, `V4 not claimed: below
finite_from`, `V4 not claimed: a format of no statement (...)`, `exact: every condition holds`,
`exact_when fails: COND`, `in place: array I`, the lengths and orders of a fold; for a constructor
`given radius CLASS, centers finite` (and `not all finite`); for a product `n_x = 0`, `n_y = 1`,
`n_x != n_y` and the like, `count_when fails: EXPR <= K`, `V3: the radius at least conv_radius's
stated value`; the failures as `failed V1`, `flag`, `V2`, `V3`, `V4`, `exact`,
`makes_ball_vector`; the smallest slack of the radius in gaps and the largest ratio of the radius
to the smallest enclosing one. The step's and the radius kernel's entries follow the claim's, as
for a map.

**`count_when`**, evaluated as an expression in $n$ (`le(EXPR, K)` with $n = \min(n_x, n_y)$),
reads the claim as it stands: `bv_conv_2`'s condition was restated after the line's base,
$n(\mathrm{unit}(\mathtt{mul\_2\_2}) + \eta/(2u)) \le \tfrac1{16}$ in place of
$n(\mathrm{unit}(\mathtt{mul\_2\_2}) + \eta) \le \tfrac1{16}$, because the old form let the length
exceed the largest number in formats of a small exponent range. The fixture `claims-wave8.json`
has the claim as it stands, and `bv_folds_judge` judges its regression under both expressions in
`fp:8:-14:1`, precision 8 with $e_{\max} = 9$ ($q_{\max} = e_{\max} - p = 1$, $q_{\min} = 3 -
e_{\max} - p = -14$; the largest number is 510): with both operands of $n$ entries $(+0, +0)$ and
radii $+0$, $\mathrm{unit}(\mathtt{mul\_2\_2}) = 4u^2 = 2^{-14}$ and $\eta/(2u) = 2^{-7}$, so the
claim admits $n$ up to 7 and the old expression up to 512. The interpreter (`gen/kairn-gen interp`,
run on these requests) gives the whole space at 511 (the count 511 rounds up to 512, beyond 510,
and the bound of `dot` is not given) and at 512, the radius `0x1.18p+3` with the flag true at 510,
and `0x1.d8p-4` at 7, the largest length the claim admits (and `0x1.0ep-3` at 8). The whole space
at 511 fails V4 under the old expression and passes under the claim as it stands, whose condition
does not hold there; the finite results at 510 and 7 pass under both; a whole space at 7 fails
under both, at 8 and 510 under the old only. (The line's first form of this test was in
`fp:8:-15:2`, $e_{\max} = 10$, whose largest number is 1020: nothing overflows there, and the
interpreter's line at 511 is finite.) The stratum `count` reaches both sides of the edge in the
full tier's `fp:5:-12:5` (lengths to 64, the edge at 8; 15 under the old expression).

**Readings chosen**: the formats of V4 above; V3 beyond architecture.md's sentence, as the brief
asks; an operand that is not a BallVector, or a scalar not a power of two under `power_of_two( )`,
invalid (the requirements); `count_when` of a product evaluated at $\min(n_x, n_y)$, the fold's
`count`; the bound's $g$ and $t$ in `conv_radius`'s stated value the smallest its claims allow.

**Not judged**: V4's equality of the documents' real-model statements (`exists x_ ...` of an exact
ball vector) beyond the range: the IEEE statement under `finite r_` is what the lines show.

The reference runner's variants of the folds (`bv-*`, `bvc-*`) plant one fault each: the radius
at the largest magnitude $+0$, the whole space as zero centers and $\Omega$, the flag always true,
no second pass, the last center zero, two lanes swapped, a spurious whole space above
$2^{e_{\max} - 8}$, an exact radius one step up, a constructor that keeps a negative or a NaN
radius, a product without the last term of a coefficient or without $r_y$ in its radius, the
bound's mask false, a product's flag always true.

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
line as `check` judges it. The bounds of the folds' stage (an `upper` entry with a value of its
own) have the quantity "smallest excess over the stated value, in gaps", made small, and their
count is repaired into `count()` ($\lvert m\rvert$, and 1 for a magnitude below 1); the folds
themselves are not searched. Of the interval kernels, those with an `error` or an `encloses` entry
are searched (`add_ball_2_2`, `mul_ball_2_2`, `ball_lower_as_2`, `ball_upper_as_2`,
`ball_narrow_2_1`), from the strata of their families (`gen6.py`), a ball's radius repaired into
its magnitude and the reversed bounds of an `interval()` exchanged; the shrinker repairs the same
way and checks a case with `gen6.valid6`.

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

**The folds' stage.** `refrun` runs the eight folds of architecture.md, "Folds", in both orders as
defined there (the step from the zero state element after element; or the first $W\lfloor
n/W\rfloor$ elements dealt to $W$ lanes, each folded from the zero state, the lanes combined from
lane 0 upward, the remainder folded in; $W \le 1$ the sequential order), with the steps
`dot_step_1` (one FMA), `dot_step_2` (`mul_2_2` then `add_2_2`), `sum_entry_step_k` and
`sum_fast_entry_step_2` (the guarded operands, then the addition), the finishes (the state and a
true flag when its leading limb is finite, otherwise every limb a NaN and a false flag) and the
bounds `bound_sum_k` and `bound_dot_k` as milestone2.md's listing writes them, with the constants
`up( )` computed exactly from `unit(K)` and `tiny(K)` of the claims (`--bound-claims`, the
fixture by default). (The listing's `tm` constant is $2\eta$ for one limb, a subnormal number; the
generated kernel's $t$ is larger, as if its constant were at least the smallest normal number,
which milestone2.md asks of every listing: both satisfy the claim.) Its variants plant one fault
each: `fold-drop-last`, `fold-lanes-reverse` (the lanes combined from the last one down: other
bits, not an error), `fold-lanes-skip-lane`, `dot-single-product` (`dot_step_2` multiplies the
leading limbs only), `flag-true-nan`, `flag-false-finite`, `fold-not-normalized`, `bound-g-pred`
($g$ one number smaller when ok is true) and `bound-ok-beyond` (ok true for every count).

**The interval kernels.** `refrun` runs the 33 interval kernels of milestone2.md as listed there
("Interval kernels", "One enclosure interface"): `mul_dir_1` (the lines of the directed products
on one `two_prod`, a zero factor the literal zero), the intervals of one limb on the directed sums
and products and their selects, `interval_make_k`, `add_ball_2_2` and `mul_ball_2_2` (the center's
kernel and $d = \mathrm{RN}(\mathrm{RN}(\lvert z_0\rvert E) G + H)$ with the $E$, $G$, $H$ of
`ball_add_2` and `ball_mul_2` of the second radius design), the bounds of two limbs (the zero rule
of the sums, `sub_down_1` and `add_up_1` of the second limb, `two_sum_ord`), `mul_ext_2_2`, the
intervals of two limbs, the hulls and intersections, `interval_mid_rad_1`, `interval_to_ball_1`,
`ball_to_interval_1`, `interval_split_1`, `ball_from_interval_2`, the bounds of a ball, and
`ball_narrow_2_1`, which the page does not list: its leading limb as the center and the radius
`next_up(r + |c1|)` (the whole line when that is not finite). The constructors
(`interval_make_1`, `interval_make_2`, `ball_from_interval_2`) are the page's listings of the rule
of 2026-11-20: a pair that describes no interval is the empty set when it is reversed,
`rv = lt(gu, gl)` (for two limbs the comparison of two limbs, `lt_2_2`, written out), and the whole
line otherwise. Its variants plant one fault each (`refrun --list-variants`, `iv-...`):
`iv-sum-nearest`, `iv-empty-whole`, `iv-mul-zero-nan`, `iv-mul-step-large`, `iv-neg-not-swapped`,
`iv-make-nan-empty` (a NaN bound gives the empty set: the rule of IEEE 1788), `iv-make-inf-empty`
(the same infinity twice gives the empty set, $(+\infty, 0)$ with $(+\infty, -0)$ too: the rule
before 2026-11-20, and IEEE 1788's), `iv-make-reversed` (reversed bounds kept),
`iv-make-reversed-whole` (no test of reversed bounds: they give the whole line, $[+\infty, -\infty]$
and $[+\infty, 1]$ too), `iv2-make-reversed-lead` (`interval_make_2` tells reversed bounds by their
leading limbs, so $(1, 2^{-4})$ with $(1, 0)$ gives the whole line), `iv2-no-zero-rule`,
`iv2-wrong-side`, `iv2-wide` ($4d$: valid, not tight), `iv2-keep-nonfinite`,
`iv-mulext-inf-sign`, `iv-hull-as-intersection`, `iv-intersection-no-empty`, `iv-mid-no-move`,
`iv-mid-radius-small`, `iv-mid-radius-large`, `iv-tball-halfline`, `iv-split-gap`,
`iv-ballbound-nearest`, `iv-ballbound-empty-nan`, `iv-fromint-no-step`, `iv-fromint-nan-empty`,
`iv-fromint-inf-empty`, `iv-fromint-reversed-whole` (the three faults of the constructors of an
interval, in the ball from an interval), `iv-narrow-no-tail`, `iv-ball-no-term` ($d = H$: caught
in `binary64` and `binary32`; in a format of few exponents every error of a sum is below $H$) and
`iv-to-interval-nearest`. The C++ runner has no kernel of Milestone 2.
**Stage B.** `refrun` runs the steps of the maps as the claims' sources list them (`sub_1_1`, the
entry forms of the sums with both operands through `guard`, `axpy_step_1` as `mul_1_1` then
`add_1_1`, `axpy_step_2` as `mul_2_2` then `add_2_2`, `axpy_step_2_1` as `mul_2_1` then `add_2_2`,
their entry forms with $y$ through `guard`, `scale_step_k` as `mul_1_1` and `mul_2_1`,
`mul_pow2_step_1` as one rounding of the product, `mul_pow2_step_2` as `mul_pow2_2`), the kernels of
the folds of maxima as architecture.md lists them (`norm_combine` the maximum by a comparison,
`select(lt(m, n), n, m)`, false on a NaN, and the `and` of the masks; `norm_step_k` the combination
of the state with $\lvert x_0\rvert$ and the mask `eq(a, a)`; `norm_finish_k` the state's limb
stepped up $k - 1$ times by its own nextUp, with a true flag when the mask is true and that is
finite, otherwise a NaN and a false flag), the maps (the step on the scalars and each element,
the check `fold_finish_k`'s mask and-ed into the flag, and when it is false the second pass), the
folds of maxima as folds (their state $(+0, \text{true})$), and the convolutions (each coefficient
the fold of its coefficients, sequential, on its terms, unfinished, then the check and the second
pass). Its variants plant one fault each: `map-drop-last` (the last element left zero),
`map-no-second-pass`, `map-flag-true`, `map-lanes-swap` (in a lane order of two lanes or more the
elements of lanes 0 and 1 of each block written in each other's place), `max-step-small` (the
finish's result one step smaller), `max-nan-lost` (the step's mask always true), `max-two-steps`
(one step up more), `conv-drop-last-term`, `conv-neighbor-term` (coefficient $j \ge 1$ takes the
last term of coefficient $j - 1$ in place of its own), `conv-flag-true`. The steps of two limbs give
the canonical NaN by themselves wherever the result is not finite, so `map-no-second-pass`
changes nothing on the maps of two limbs but `mul_pow2_map_2`.

**The enclosure interface (stage B2).** `refrun` runs the 53 kernels of the predicates and
comparisons of an interval and a ball, the set operations of a ball and the conversions of two
limbs as their listings in `gen/kernels/` write them, on IEEE values, through the kernels they
call (`two_sum_ord`, `abs_2`, the comparisons of two limbs, `add_ball_2_2`, `radd`, `to_down_2`,
`to_up_2`, `mul_pow2_2`, `add_2_2`, `make_2`, `ball_add_k_full`, the directed sums of two limbs,
`ball_to_interval_1`, the hulls and intersections, `interval_to_ball_1`): an operand returned as
it is by a select is its token as the line wrote it, the sign of a zero kept. Its variants plant one
fault each (`refrun --list-variants`, 69 of them, `en-` for the predicates of an interval, `enb-`
and `enb2-` for those of a ball, `ens-` for the set operations of a ball, `enc-` for the
conversions): a relation read on the wrong side or strictness, an emptiness or infinity test left
out, the comparisons of two limbs on the leading limbs alone, a yes or a no where the relation
does not hold or fails, both answers, the special states answered wrong, the selects of the
operands as they are left out, swapped (`ens-int-swapped`: the reading before the correction),
or writing a zero as $+0$, a radius halved or one number smaller, the empty set or the whole line
of the parts of a split exchanged, the midpoint of two limbs not moved into $[l, h]$, a center of
the whole line that is not canonical, $\Omega$ where $+\infty$ is due, an infinite radius below the
limit of `finite_when`, an exact zero end off by $\eta$, infinite bounds below the limit of
`bounded_when`, the rules of the constructors before 2026-11-20, a center one number off, and
(`enc-mid2-nan`) the midpoint $(\mathrm{NaN}, \mathrm{NaN})$ of every bounded interval, with the
radius $+\infty$, and the point of split $(\mathrm{NaN}, \mathrm{NaN})$: what a format of no
statement may give, which `enc_planted` fails in every format of the statements, on every line of
a bounded interval, and counts as not claimed in `fp:4:-4:-1`.

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
python3 oracle/kairn-oracle selftest              # about eight minutes
python3 oracle/kairn-oracle selftest --quick      # smaller samples, about 90 seconds
python3 oracle/selftest/mutants.py --jobs 7 --fail-fast   # tests the selftest, 45 minutes
```

The exhaustive tests run one worker process per CPU; `--jobs N` (or `KAIRN_ORACLE_JOBS=N`)
caps them. The times: the whole selftest, 474 seconds on an Apple M3 Max with 8 workers
(`KAIRN_ORACLE_JOBS=8`) beside a build of the library, and the 234 mutants, 2 703 seconds on 14
hardware threads of the Linux machine with two workers each (`KAIRN_ORACLE_JOBS=2`), both on
2026-11-20; on the joined tree of 2026-11-21, which judges every claim of `gen/claims.json`, the
whole selftest (119 tests) 566 seconds on the M3 Max beside other jobs, and the 448 mutants,
3 580 seconds with `--jobs 16 --fail-fast` on the Linux machine with one worker each
(`KAIRN_ORACLE_JOBS=1`), every one caught; `--quick` earlier, on the M3 Max with `--jobs 6`. `--only NAMES` runs only the tests
named (comma-separated), `--skip NAMES` all but those, `--last NAMES` runs those after the others
and `--fail-fast` stops at the first failing test; a name that is not a test's is an error.
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
elsewhere; for the interval kernels, reversed bounds or the empty set misread, a requirement not
checked, a range without $0 \cdot \infty = 0$ or a negation not exchanging its bounds, a statement
of I2 to I6 not judged, a step more allowed, `product_large` ignored, a relative term doubled, the
absolute term left out, the zero condition always true, a zero factor or an infinity not judged,
the special values of 1788 exchanged, an output group judged only where the first is finite,
`up( )` read as its argument, a malformed claim accepted, a stratum aimed elsewhere; for the
constructors under the rule of 2026-11-20, a NaN radius read as the empty set, the center tested
before the radius, the class of the radius or the sign of a zero radius not counted, a center
never left finite by `badradius`; for the constructors of intervals and the ball from an interval
under the rule of 2026-11-20, a NaN bound or the same infinity twice read as the empty set (the
old rule), reversed bounds read as the whole line, bounds of two limbs compared by their leading
limbs, the same infinity classed as reversed bounds, a NaN bound tested after the same infinity,
an `infinities` stratum that never gives the same infinity twice, a cell of their table not
counted, counted with its bounds exchanged or with $a \le b$ and $a > b$ swapped, the zeros of
opposite signs or reversed bounds of equal leading limbs of two limbs not counted; for stage B, a finite element from an operand that is not finite or beyond $\Omega$
accepted, the second pass or the flag not checked, the step's verdict ignored or its arguments
reversed, a requirement of a map or a convolution not checked, a step's requirement or value not
compared, a coefficient without its last term or not judged, the lengths swapped, a convolution
read before its fold, a maximum below $V$ or a step above $\mathrm{RU}(V)$ more allowed, $V$ an
element's other than the largest, a false flag with a finite top accepted, `maximum` not compared,
reversed or its outcomes swapped, the mask, the steps or nextUp of $-\infty$ of a finish wrong,
`steps` 0 or an `if` naming an output accepted, a stratum without overflow, a tight case or an
empty polynomial; for the enclosure interface of stage B2, a reader check of `certain`, `trit`,
`ball_set`, `ball_splits` or of the fields new to the kinds that exist left out, a clause of each
judge not judged (soundness, exactness, the special states, `exact_when` and its condition read
as half of $\Omega$, both answers, the operands as they are and the clause of X also where X is
special, the sign of a zero, a NaN against a NaN, emptiness, containment, the parts of a split,
`finite_when` and its limit one binade off either way, the center of 1788 beyond the limit, the
canonical center, the tightness, `exact_when` and `bounded_when` of two limbs, the center, midpoint
and smallest radius of a ball from an interval; the formats of the statements not applied to
`finite_when` and `bounded_when` of two limbs, not counted, the conditions counted outside them, a
failure in a wider subnormal range not said to be a finding; the same rule for the midpoint of a
bounded interval of 1788 and the parts of a split not applied, applied in a format of the
statements too, not counted, a center or a point of split that is not finite not counted, a finite
radius about such a center accepted, the outer bounds of the parts or their common point about
such a point not judged, a failure in a wider subnormal range not said to be a finding), a
relation read on the wrong side,
with the wrong strictness or without its empty set or infinite bound, a set without its radius, a
count the guards read not counted, a stratum that does not reach what it is for) and requires
`selftest --quick` to fail on the copy. With
`--fail-fast` each copy's selftest stops at its first failing test and runs the longest tests
(`LONG` in `mutants.py`) last (`selftest --fail-fast --last NAMES`), so a mutant is caught in
seconds; a survivor still runs every test, and the tests listed are then the first that failed
only. The test of the side of a `bound` alone has no mutant: an
output on the wrong side is not reached by the steps outward from the directed rounding either,
and fails there; nor has the test that the split point of `splits` is a member of $X$, which
follows from both parts being canonical.

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
| `claims_reading_wave5` | the fixture of the folds' stage unreadable, or its new kinds read otherwise (form T, `count()`, `format(half)`, entries under a mask); 23 malformed kernels and 26 malformed folds not set aside (a form, a requirement or a format property outside the vocabulary, `count()` of an output or of two limbs, `upper` with `gaps` and `value` or without `if`, `if` naming a limb, `holds` with one argument or another relation, `unit()` of a missing kernel or of one without a single error entry, a power with a name in its exponent, an entry not under a mask beside entries that are, a bound in the extended domain, a finish in the finite domain or with a flag that is not a mask, a fold of the finite domain, without `canonical()`, with another order, a step that is not a kernel, the lane order without a combination, an unreadable value, no `finite_or_nan`, an error kind, `eps` zero or not positive in a format, `tau` negative, a name in `eps`, heights for another set of orders or of another height, a role, limbs, lanes or status out of their vocabulary, an instance other than its expression, a fold named as a kernel, a map that writes arrays); a kernel whose `unit()` names an unreadable one not set aside with it |
| `cexpr_exact` | an expression of the stage (powers, quotients, `unit()`, `tiny()`, names) other than Python's Fractions on 3 000 random ones (600 with `--quick`), a precedence of unary minus or `^` other than `-2^2 = -4`, `2^3^2 = 512`; a malformed expression read, a division by zero evaluated |
| `fold_brackets` | a bracket of $(1 + \varepsilon)^h$ that does not hold the exact power, or is wider than $2^{-64}$ of it, for 400 random $\varepsilon$ (to $2^{-110}$) and $h$ (to 5 000); the bound decided from integers other than from Fractions at the exact bound and one unit to either side |
| `fold_reference` | the reference runner failing a fold, or an invalid or suspicious case, on 500 arrays (260) of each fold in `binary64`, `binary32` and a toy format; a length class, an order, a flag outcome, heavy cancellation or (dot products) the term $\tau$ never met; a largest error/allowed below 1/2 (one limb) or 1/16 (two limbs) |
| `fold_planted` | a planted fault of the folds not caught in its entry (the last element left out: `fold_error`; the last lane left out of the combination: `fold_error`; single-limb products in `dot_2`: `fold_error`; a true flag on a NaN, a false flag on a finite result: `finite_or_nan`; a result not normalized: `normalized`), caught in another or in a fold it does not touch; the lanes combined from the last one down failing anything, or changing no bits |
| `fold_exhaustive` | the reference runner failing any array of tiny formats up to two or three elements (86 279 arrays; more without `--quick`), in every order that differs; a planted fault not caught there |
| `fold_judge` | one of 20 hand-written lines of folds judged otherwise than worked out by hand (the empty array, an error one unit beyond the bound of height $n - 1$, flags against results and elements, a false flag far from overflow suspicious, partial sums that overflow, elements not canonical or not numbers of the format, a result not normalized, the term $\tau$ of `dot_2`, `dot_1` around its rounding), a malformed line or an order the fold does not claim passed, a statistic of lengths, orders or cancellation off |
| `fold_scaled` | with `eps`, `term` and `tau` times 1 024 a fold failing or its largest ratio not 500 times smaller; with them divided by 4 the tight cases passing |
| `bound_kernels` | the reference runner (milestone2.md's listing) failing a bound kernel on random counts of `binary64`, `binary32` and `fp:12:-30:12` or on every count of `fp:8:-12:10`; a class of $m \cdot \mathrm{unit}(K)$ around the limit never met, ok false at or below 1/5, $g$ never within 8 gaps of its stated value; $g$ one number smaller failing other than at $m = 0$ (elsewhere the listing has more than a gap of slack), ok true beyond the limit not failing `holds`; one of 12 hand-written lines (`count()`, `format(half)`, nothing claimed with ok false, a non-finite $g$ with ok true suspicious, $g$ at and one number below $u$ for $m = 1$, `holds` beyond 1/2) judged otherwise |
| `stage_kernels` | the reference runner failing a step or a finish on random cases of three formats or a finish on every state of `fp:3:-3:0`; a class of `finite_or_nan` never met; the planted flags and single products not caught; one of 13 hand-written lines (finishes passing a state on limb for limb, form T between the bounds of forms R and T, `dot_step_1` rounding) judged otherwise |
| `gen_folds` | case $i$ alone not case $i$ of its run, a seed, the orders or the length not mattering, a length above the maximum, a stratum missing or not asked for, `lanes:big` not above the length, an invalid case, an enumeration's size other than the brute-force count, an order outside the vocabulary accepted |
| `merging_wave5` | the merge of summaries of folds and bound kernels differs from the whole |
| `claims_reading_wave6` | the fixture of the interval kernels unreadable, or its requirements, kinds and fields read otherwise (`interval()`, `not_nan()`, `tight`, `bounded_when`, `zero_factor`, `midpoint_when`, an `encloses` with no ball); 60 malformed kernels not set aside (requirements on one input, of bounds of other limbs, in the finite domain, missing, listed twice, a two-limb `not_nan()` without `canonical()`, an interval sharing a ball's input; `outward` with another side, of a one-limb output, a malformed `up( )`, a name in a constant, a missing kernel in `unit( )`, a fractional power, a negative constant, an empty or malformed `exact_when`, `zero_factor` in the finite domain or false, `abs` missing; `encloses_interval` with a name twice, `abs`, an input in the set, bounds that are not an `interval()`, an interval named like an input, an unknown `tight`, negative steps, `when` on a sum, `rounded` on two limbs, `bounded_when` over another set or malformed, `bounded_exactly` false, `zero_factor` on a sum, an output twice, a field missing, `exact_when` of an unknown side or as a list; the other kinds with a bound that is not a requirement, another side, a ball without `ball()`, an unknown `tight`, `set` or `special`, a name in a constant, `smallest_radius` not true, an output twice, `tight` missing, one part, `midpoint_when` on another input or empty; `zero_factor` not true or in the finite domain; balls `{}` in the extended domain, with and without the `finite_when` that domain asks of `encloses`); a constant's `unit( )` of an unreadable kernel not setting its kernels aside; `midpoint_when` on a ball from a center |
| `iv_constants` | the constants of a claim with `up( )` other than Python's Fractions with an `up( )` of their own (the smallest number of the format not below, by a walk over its numbers) on 1 500 random ones (300 with `--quick`), the precedence of `-` and `^`; a malformed constant read, an `up( )` beyond $\Omega$ evaluated; the `rel` and `abs` of the bounds of two limbs other than the closed forms $A$ and $B$ of milestone2.md built from the reference runner's own $E$, $G$, $H$ in five formats, and other than the page's table ($8.000000000000009u^2$, $2.000000000000002N$; $10.000000000000012u^2$, $2.000000000000003N$; $8.0000049u^2$, $10.0000068u^2$) |
| `iv_reference` | the reference runner failing an interval kernel, or an invalid or suspicious case, on 1 200 random cases (300) of each in `binary64`, `binary32` and `fp:4:-6:1`; an entry never applied; a class the guards ask for never reached in `binary64` or `binary32` (empty, unbounded and bounded operands and results, `bounded_when` both ways and within a factor 2 below its limit, a rounded bound inexact or exact or a step beyond, `product_large` both ways, `exact_when` holding, I6, a NaN bound, reversed bounds, equal infinities, the states of a ball, disjoint and touching intervals, both empty, every class of $X$, an odd bound, a zero against an infinity); a fraction of the bounds of two limbs or of the midpoint below 1/4 |
| `iv_exhaustive` | the reference runner failing any case of tiny formats (`fp:2:-2:1`, `fp:3:-2:-1`, `fp:4:-3:-2`; the product of two-limb intervals on a restricted domain), every line of the extended domain judged; a cell of the table of the constructors never met in the enumerations of the three (or, for `interval_make_2`, reversed bounds of equal leading limbs; zeros of opposite signs met in an enumeration, which has one zero); twelve planted faults not caught there, or caught in another entry (of the constructors: a NaN bound or the same infinity twice giving the empty set, reversed bounds the whole line, reversed bounds of two limbs told by their leading limbs) |
| `iv_planted` | a planted fault of the interval kernels not caught in the kernels and entries where it belongs (in `binary64`, `binary32` and `fp:4:-6:1`, `iv-ball-no-term` in the first two), caught in a kernel that does not use it, or seen as an invalid or suspicious case; a fault of the constructors not failing every line of its streams that it is about (`iv-make-inf-empty` and `iv-fromint-inf-empty` the same infinity twice, for `interval_make_2` also with second limbs that are zeros of opposite signs; `iv-make-nan-empty` and `iv-fromint-nan-empty` a NaN bound; `iv-make-reversed-whole` and `iv-fromint-reversed-whole` reversed bounds with an infinity, $[+\infty, -\infty]$, $[+\infty, h]$, $[l, -\infty]$; `iv2-make-reversed-lead` reversed bounds of equal leading limbs), or the streams without such lines in a format |
| `iv_judge` | one of 169 hand-written lines judged otherwise than worked out by hand (each failure in its statement: I1 to I6 (a negation one step wider than exact failing I4 alone), the parts of `ball_of_interval` and `interval_of_ball`, the kind otherwise; results at and one unit past the bounds of two limbs; the zero rule; $0 \cdot \infty$; the special values of 1788; the constructors on every kind of given bounds: a NaN, the same infinity twice, $(+\infty, 0)$ with $(+\infty, -0)$, reversed bounds infinite or of equal leading limbs, $[+0, -0]$), one of 8 lines outside the requirements not invalid; one of 24 lines of the constructors counted under another given state than worked out by hand; a line of each cell of the table of the constructors (architecture.md, "The constructors on every pair of values", written out in the test) for each of the three, 51 lines, judged otherwise than the table says or counting another cell, its wrong result passing; the classes of two limbs counted otherwise on 9 lines; an infinite lower bound of `mul_dir_2_2` beside a finite upper one not judging the upper, or not suspicious; both infinite not non-finite |
| `iv_gen` | case $i$ alone not case $i$ of its run, a seed not mattering, an invalid case, a stratum of the header without a case or a case of none, a common stratum missing, `oddeta` giving an odd multiple of $\eta$ below $2N$ in fewer than three quarters of its cases (`interval_mid_rad_1`, `ball_from_interval_2`), in every interval kernel in two formats; the enumeration of intervals other than every canonical interval of the definition, counted in three tiny formats; a restriction dropping the infinite bounds or the empty set |
| `iv_merging` | the merge of the summaries of two halves of streams of four interval kernels differs from the whole |
| `iv_scaled` | with `rel` and `abs` of the outward bounds times 1 024 a failure, or a largest fraction of the bound not exactly 1 024 times smaller; divided by 8 no failure |
| `claims_reading_wave7` | the fixture of stage B unreadable, a map, a convolution or a fold of maxima read as another; 11 malformed kernels and 29 malformed folds not set aside (a `maximum` with one argument, over a name or a mask that is not an input, a limb an input does not have, of a mask, with another field; `steps` 0 or a boolean, `if` naming an output or a limb, a finish of the finite domain; a map without `"map"`, of the finite domain, whose step is missing, whose `entries` names another kernel, whose `step_args` are another order or incomplete, whose value is not the step's, which lacks a requirement of the step or has one outside the vocabulary, writes one limb or nothing, has a flag of two limbs, an entry of the wrong flag or array, one entry, a check that is not a finish, a minimum precision below the step's, a power of two not required or required of an array; a convolution of a fold that is not a dot product's, with the lane order, a `coefficients` entry naming another fold, one array, another value, scalars; a fold of maxima `over` a sum, with negative steps, of the flag, with `fold_error` beside `upper`); a map whose step cannot be read not set aside with it, a convolution listed before its fold not read |
| `gen_shapes` | a family of the kernels' generator failing (other than refusing the kernel with a `GenError`) on any stratum of any kernel of the six fixtures, or of the same kernel with a two-limb input made one limb (192 kernels and variants): the test that would have caught the crash of the scale family on `mul_pow2_step_1`, which assumed a two-limb operand beside the power of two |
| `stage_b_kernels` | the reference runner failing a step of a map or a kernel of a fold of maxima, or an invalid or suspicious case, on random cases of `binary64`, `binary32` and `fp:5:-12:6`; a class of `maximum` (each argument larger, equal) or of the finishes (the mask both ways, a finite value stepped up to a finite one and, for `norm_finish_2`, to $+\infty$, a NaN, an infinity) never met; `axpy_step_1` and its entry form more than $10^{-6}$ below their bound, `axpy_step_2` and its entry form below 0.57 of it in `binary64`, `mul_pow2_step_1` below exactly 1 |
| `maps_reference` | the reference runner failing a map, a fold of maxima or a convolution, or an invalid or suspicious case, on 400 arrays (170 with `--quick`) of each in `binary64`, `binary32` and `fp:5:-12:6`; a class the guards ask for never met (elements of each kind, both flags, lengths and orders; the largest at each place, at and one step above $\mathrm{RU}(V)$, the bound's top beyond $\Omega$; coefficients of each kind, lengths 0 and 1 on each side, unequal lengths, coefficients of one and two terms, heavy cancellation); a step of one limb below 0.99 of its bound in `binary64` (0.3 for two limbs) |
| `maps_planted` | a planted fault of stage B not caught in its entry (an element dropped or swapped between lanes: `entries`; no second pass, a flag that lies, a lost NaN: `finite_or_nan`; a maximum one step too small or too large: `upper`; a coefficient that drops a term or takes its neighbour's: `coefficients`), caught in another, or in an object it does not touch |
| `maps_exhaustive` | the reference runner failing any array (and scalar) of tiny formats up to one to three elements, in every order that differs (4 142 arrays with `--quick`, more without), or a line not judged, or the coverage not complete; a planted fault not caught there; the size of the enumeration of `axpy_1` and of `conv_1` other than counted from the definition |
| `maps_judge` | one of 91 hand-written lines of stage B judged otherwise than worked out by hand (a written element off, a flag that lies both ways, a missing second pass, a finite element from a non-finite operand and from a sum that rounds beyond $\Omega$, the empty array with a NaN scalar, malformed lines, invalid scalars and elements; the maxima at, one and two steps above $\mathrm{RU}(V)$, a lost NaN, the bound's top beyond $\Omega$ and finite; the convolutions of architecture.md's examples, a coefficient off, $0 \cdot \infty$, lengths that do not match the limbs; `maximum`, the finishes on $\Omega$, $-\eta$, $-\infty$, a NaN and a false mask; the tight case of `axpy_step_1`) |
| `gen_maps` | case $i$ of a map, a fold of maxima or a convolution alone not case $i$ of its run, a seed or the largest length not mattering, a length above the largest, a stratum missing or not listed, an invalid case, an unknown stratum accepted, a convolution accepting the lane order |
| `merging_wave7` | the merge of summaries of stage B differs from the whole |
| `summary_bounds` | a statistic of a map's step keeping anything but the line of its element of the step (or one that does not pass when judged again), a summary of a map above 1 MB, a distance of the profile kept that is not a record; on 3 000 random profiles with many equal ratios, merged in order from summaries read back, (a) for some $F$ (value or case) or the merged summary differing between the records and every distance |
| `claims_reading_wave8` | the kernels of the fixture of the ball vectors and the accumulator (`claims-wave8.json`) unreadable or read otherwise (`unless`, `exact_when` with `mask`, `exact_flag`, `nonneg`, `if_all`, `at_most`, `rounded` with a value); 36 malformed kernels not set aside (gaps beside a value, an unknown name, `abs` of a sum, `unit( )` of a missing kernel, `unless` of a limb or an output, a radius kernel with an entry of another kind, the extended domain, `unless` beside `exact_when`, `exact_when` of masks alone, empty, over a limb, of a mask with another field, with a threshold 0, `unless` beside `if`; `at_most` of 0, of a name, twice, of no input; `exact_flag` of a limb or an input, without `exact_when`, on `rounded`; `nonneg` false, without `if`, with `steps`; `if_all` of one mask, twice the same, of a limb, beside `if` or `nonneg`; a value of `rounded` over a limb an input does not have, over an unknown name, malformed, beside `when`, not a string) |
| `bv_kernels_reference` | the reference runner failing a kernel of the family, or an invalid or suspicious case, on random cases of `binary64`, `binary32` and `fp:5:-12:6`, `conv_radius` included (its results that are not finite counted, by the ruling of 2026-11-21); a class the guards ask for never met; `conv_radius`'s finite results less than three quarters of a run |
| `bv_kernels_planted` | a planted fault of these kernels (`bvr-*`, `bvs-*`, `bvc-*`, `bvf-*`, `acc-*`) not caught in its entry, caught in another, or in a kernel it does not touch; a variant of `refbv.VARIANTS` without a test |
| `bv_kernels_exhaustive` | the reference runner failing any operand of tiny formats (13 kernels; 21 enumerations without `--quick`, `conv_radius` in `fp:2:-1:0`, where every result is $+\infty$ or a NaN, and in the full tier's restricted domain of `fp:3:-4:4`), the coverage not complete; the domain of `at_most(g, 1)` other than every number from 0 to 1; three planted faults not caught there |
| `bv_kernels_judge` | one of 88 hand-written lines judged otherwise than worked out by hand (a stated value met and missed by one unit, $+\infty$ passing and suspicious, a NaN, $-\infty$, `at_most` both ways, the exactness of the radius of a scaling and its `unless`, beyond $\Omega$, the mask of a step both ways, each cell of the finishes, the copies, a sum of magnitudes at a tie and at an overflow beside a finite running sum and the reverse, the radius of an accumulator under its mask, `conv_radius`'s results that are not finite: $+\infty$ and a NaN passing from any operands, $-\infty$ and a negative number failing) |
| `gen_wave8` | a kernel of the family given another family, case $i$ alone not case $i$ of its run, a seed that does not matter, an invalid case, a stratum of the header without a case |
| `gen_wave8_strata` | a stratum of `gen8.py` off its corner (an output $+\infty$ from `huge`, every operand zero from `zeros`, $r_x c = N$ from `atnormal`, operands $2^p$ apart from `mixed`; a sum of magnitudes $+\infty$ beside a finite running sum from `atop`, a cancellation, three quarters ties and exact sums from `tie` and `exactprod`, $a$ apart; the mask both ways at `limit`, false `beyond`, nine tenths integers up to $2^p$ from `integer`, $a$ in the top binades; each class of value of the finishes) |
| `merging_wave8` | the merge of the summaries of two halves of streams of the family's kernels differs from the whole |
| `claims_reading_bv_folds` | a fold of the ball vectors of the fixture unread, or one of 33 malformed folds not set aside alone with its reason (a kind, a requirement of a BallVector missing or shared, a condition not a list, an exponent, an expression, a name, a radius or step kernel not of the claims, two arrays written, the outputs, the limbs, the orders, the status, the minimum precision, a radius under `power_of_two`, a limb of `exact_when`, a threshold, `count_when`, a constructor's shape) |
| `bv_folds_reference` | the reference runner failing a ball vector, a constructor or a product, or an invalid or suspicious case, on random cases of `binary64`, `binary32` and a toy format, and in place; a class the guards ask for not met (both results, a whole-space operand, V4 with and without entries, exactness, each radius given, the lengths 0 and 1 of a product, every array in place) |
| `bv_folds_planted` | a planted fault of the folds (`bv-*`, `bvc-*`) not caught in its class (V1, the flag, V2, V3, V4, exact, `makes_ball_vector`), or caught in a fold it does not touch |
| `bv_folds_exhaustive` | the reference runner failing a request of the enumerations of tiny formats (six folds; twelve without `--quick`), an index seen twice or missed, a class of results or the lane orders missing, V4 judged outside its formats or not judged inside; a planted fault not caught there |
| `bv_folds_judge` | one of 74 hand-written lines judged otherwise than worked out by hand (the radius at, below and above its kernel's value, below the set, a center off the middle or not the step's, the flag, the whole space where V4 claims finite and beyond, of no entry, `radii_when`, below `finite_from`, outside the formats of V4, in a format of a wider subnormal range, where a failure says that it is a finding, the lanes, in place and a malformed `inplace=`, operands that are not BallVectors, the exactness of a negation and of a scaling, each case of a constructor, a product of one entry each, a non-canonical product); `count_when` evaluated otherwise than by hand under the claim as it stands and under its old expression (operands of 511, 512, 510, 8 and 7 entries $(+0, +0)$ in `fp:8:-14:1`, the interpreter's results and the whole space, and 511 entries against 1), or the fixture's `count_when` not the claim as it stands |
| `gen_bv_folds` | case $i$ of a fold of the ball vectors alone not case $i$ of its run, a seed that does not matter, an invalid case, the strata not those of the shape or without cases, `whole` without a radius $+\infty$, `zeroradius` without $+0$; in place, a request without `inplace=I` over every array that can be written, a product that does not refuse it; the stratum `count` not on both sides of `count_when` |
| `merging_bv_folds` | the merge of the summaries of two halves of streams of the folds differs from the whole |
| `maps_inplace` | a map's run in place without its header or its field over every array that can be written, failing through the reference runner, an array not counted in place; `inplace=` beyond the arrays, not a number or negative not malformed; a fold of maxima not refusing `--inplace` |
| `claims_reading_enc` | the fixture of the enclosure interface unreadable, or its kinds and fields read otherwise (`certain`, `trit`, the argument `0`, a point, `exact_when`, `ball_set`, `finite_when`, the outward `tight` and `bounded_when` of two limbs, `rel` and `abs` of `makes_ball`); 65 malformed kernels not set aside with a reason that names the kernel, the entry and the field, or making another kernel unreadable (an unknown field, `rel` or arity; a `rel` of `certain` in `trit`; an argument that is no set, `0` twice, the same set twice, a set that is no argument; `intervals` and `balls` together or neither; `exact` false, with `exact_when`; `exact_when` empty, without `omega` true, with `exp`, over an unknown name, malformed; `of` an input or a limb output; `yes` and `no` the same, `no` missing; a point inside a set or of two limbs without `canonical()`; the finite domain; a ball without its requirement; `ball_set` with another `set`, one ball, a radius or center that is no output of the right limbs; `ball_splits` with one part, an output twice, a malformed part, `from` without `ball()`, a center of other limbs; `finite_when` empty, not a list, over an output, with an exponent that is a string or a boolean, with `omega`, beside `smallest_radius`; `interval_of_ball` of two limbs rounded, with `steps`, without `abs`, with `exact_when` a list, `bounded_when` empty, over another set, with `omega` or a fractional exponent; `makes_ball` with `rel` and no `abs`, `smallest_radius` without them or false, a malformed constant); `rel` on a ball from a center; `ball_set` in the finite domain |
| `enc_relations` | `enclosure.relation` other than the definitions of architecture.md's table, quantified over the members, on every pair of 27 sets (the empty set, half-lines, the whole line, bounds in -2..2), every relation, and `member` of every point of -3..3, the infinities and NaN (5 508 relations) |
| `enc_reference` | the reference runner (the listings of gen/kernels/) failing a kernel of the family, or an invalid or suspicious case, on random streams of 1 500 cases (500 with `--quick`) of every kernel in `binary64`, `binary32` and `fp:4:-6:1`; a stratum of the header without a case; an entry never applied; a class the guards ask for never reached in `binary64` or `binary32` |
| `enc_exhaustive` | the reference runner failing any case of the enumerations of tiny formats of every kernel (two intervals or two balls of two limbs on a restricted domain: 70 enumerations, 1.5 million cases with `--quick`), a line not judged, a cell of the table of the constructors never met by `ball_from_interval_k`; 16 planted faults not caught there, caught in another entry, or, for a kernel whose claim fixes the output, not failing every line they change |
| `enc_planted` | a planted fault of the family (69: `refrun` variants `en-`, `enb-`, `ens-`, `enc-`) not caught in the kernels and entries where it belongs, in `binary64`, `binary32` and `fp:4:-6:1`, caught in a kernel that does not use it, seen as invalid or suspicious; a line it changes of a kernel whose claim fixes the output not failing; a line of the class it is about not failing (two whole lines of zeros of different signs, a zero passed through as it is, the whole line, a half-line, the empty set, an exact zero end, a NaN bound, the same infinity twice, reversed bounds, a bounded interval); the midpoint $(\mathrm{NaN}, \mathrm{NaN})$ of `enc-mid2-nan` failing, or not counted as not claimed on every line of a bounded interval, in `fp:4:-4:-1`, a format of no statement |
| `enc_judge` | one of 228 hand-written lines judged otherwise than worked out by hand, each failure in its statement (every cell of the table of `rel` and of the special states of the predicates of an interval and a ball, of the clauses of `ball_set` with the signs of zeros, of `ball_splits`, of the conversions of two limbs: the special values of 1788, a canonical center, `finite_when` at and beyond its limit, the center claimed beyond it, `exact_when`, the tightness, containment and `bounded_when` of two limbs, the center, midpoint and smallest radius of `ball_from_interval_1`); one of 10 lines outside the requirements not invalid; one of 13 lines of the formats of the statements judged otherwise (`finite_when` and `bounded_when` of two limbs failing in `fp:3:-4:1`, failing as a finding in `fp:3:-5:1`, counted as not claimed in `fp:3:-2:-1` with the conditions not counted and the center of 1788 still judged); one of 34 lines of the midpoint of a bounded interval with `ieee1788` and of `splits`, of one limb and of two, judged otherwise (a NaN midpoint or point of split failing in `fp:3:-4:1` and `binary64`, failing as a finding in `fp:3:-5:1`, passing, counted, in `fp:4:-4:-1`, `fp:4:-5:0` and `fp:3:-3:1`, the two lines of the brute-force plan's finding among them; there containment about a center that is not finite, the outer bounds of the parts and their common point still judged, and a finite center or point of split, a center not normalized and the special values of an unbounded interval as everywhere); a cell of the table of the constructors for `ball_from_interval_1` (17) passing its wrong result, failing its right one or counting another cell |
| `enc_gen` | case $i$ alone not case $i$ of its run, a seed not mattering, a stratum of the header without a case or a case of none, an invalid case, in every kernel of the family in two formats; no center $-0$ of the whole line in the streams of the set operations |
| `enc_strata` | a stratum of the family (or of the conversions of two limbs in `gen6.py`) whose cases do not have what it is for, in `binary64` and `fp:4:-6:1` (every case, or the fraction given: an operand special, intervals touching, nested, disjoint or with an equal bound, balls on the boundary of the relation, huge, of radius zero, both special, a center near $\Omega$, a bound beyond $\Omega$, at the limit of `finite_when` or `bounded_when`, an end exactly zero) |
| `enc_merging` | the merge of the summaries of two halves of streams of seven kernels of the family differs from the whole |

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
| `make-negative-radius`: the radius tested for NaN only, so a negative radius is kept (and a NaN radius gives the empty set) | `ball_make_1`, `ball_make_2` | `makes_ball`: `not canonical` (`whole line instead of empty set`, with a center not finite, and `empty set instead of whole line` allowed) |
| `make-nan-radius-empty`: the rule before 2026-11-20, a NaN radius gives the empty set | `ball_make_1`, `ball_make_2` | `makes_ball`: `empty set instead of whole line` |
| `make-nan-radius-finite`: the radius tested against $+\infty$ only, so a NaN radius beside a finite center gives that center and a NaN radius | `ball_make_1`, `ball_make_2` | `makes_ball`: `not canonical` |
| `make-negative-nan-center-whole`: the center tested before the radius, so a negative radius with a center that is not finite gives the whole line | `ball_make_1`, `ball_make_2` | `makes_ball`: `whole line instead of empty set` |
| `make2-inf-nan-tail`: `make_2` of an infinity with a NaN tail | `make_2` | `represents` |
| `ball2-no-E`: the second design without $E$ | one-limb full Ball kernels; $G$ rounded up has room for the missing term at low precision (a 2-limb center at $p = 4$; `ball_mul_1` on every case of `fp:2:-2:1` and `fp:3:-3:0`), so the exhaustive test takes `ball_mul_1` at `fp:3:-4:1` | B3 |
| `ball2-no-H`: the second design without $H$ | products and scalings of balls | B3 |
