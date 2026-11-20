# Milestone 2 experiments

The numerical checks behind the
[Milestone 2 statements](../../docs/developer/design/milestone2.md). That page proposes kernels
and what each will guarantee; nothing of it is implemented or proved yet. Before a statement was
written there, its kernel was run on every operand of small number formats, or on samples where
there are too many, and the statement was judged in exact arithmetic. Nothing here is library
code, and nothing here is a proof: a run that finds no failure says that a statement is not
wrong on what was run.

## How it works

- `kernels/` holds the proposed kernels as descriptions in the generator's own format
  (`gen/README.md`): `ball_split_1` and `conv_radius`. They carry no claims: the claims of this
  milestone need vocabulary that the generator does not have yet. The radii `bv_add_radius_2` and
  `bv_scale_radius_2` that were proposed here are in `gen/kernels` now, with their forms of one limb
  and their claims (`batch.py` reads them from there), and so is the constructor of a BallVector,
  `bv_make_1.fold` and `bv_make_2.fold` with their kernels `bv_center_entry_1`, `bv_center_2`,
  `bv_make_radius` and `bv_make_finish`, whose listing the page does not give and which was proposed
  here (`ballvector.py` runs it from there; its output is the same). The 45 that the generator has now
  are in `gen/kernels`, with their claims, and only there: the nine of the first wave
  (`two_sum_ord`, the four directed sums, the two directed products and the two scalings of a ball
  by a power of two); three bound kernels of the folds' stage (`bound_sum_2`, `bound_dot_2`,
  `bound_dot_1`, whose constant of `tm` holds the smallest normal number, so that no constant is
  subnormal); the thirteen of the first kernels of the intervals (`mul_dir_1`, `interval_make_1`,
  `interval_neg_1`, `interval_add_1`, `interval_sub_1`, `interval_mul_1`, `add_ball_2_2`,
  `mul_ball_2_2`, `add_down_2_2`, `add_up_2_2`, `mul_dir_2_2`, `interval_add_2` and
  `ball_from_interval_2`); and four of the next stage (`mul_ext_2_2`, `interval_mul_2`,
  `interval_mid_rad_1` and `ball_to_interval_1`, as they were written here); and the eight of the
  accumulator (`acc_add_k`, `acc_mul_k`, `acc_merge_k`, and `acc_radius_k`, whose listing the page
  does not give and which was proposed here: `accumulator.py`); and the four radii of BallVector
  (`bv_add_radius_k`, `bv_scale_radius_k`), and the four kernels of its constructor. Three of those were written again there, with the same values, so that
  no fused result is negated, directly or through a select (a rule of the generator): the lower
  bounds of `mul_dir_2_2` and `add_down_2_2` are minus the rounding up of $d - z_1$ (for the sum,
  $dd - z_1$, with $dd$ the radius or zero), and the radius of `ball_from_interval_2` adds minus
  the lower half as a product of its own.
- `common.py` loads them together with the kernels of `gen/kernels`, taking a kernel from
  `gen/kernels` when it has one, and evaluates them with the
  generator's exact interpreter (`gen/kairn_gen/interp.py`), on any format `(p, qmin, qmax)`. It
  also has rounding down, up and to nearest, the neighbors and the normalization test written
  with Python's `fractions.Fraction`, independently of the interpreter; the scripts judge with
  these.
- Each script asserts its statements and prints a summary. A statement that fails stops the
  script with the operands.

The formats are toy formats, as in the generator's and the oracle's tests: precisions of 2 to 6
bits and a few exponents, most of them with the shape of `binary64`
($q_{\min} + q_{\max} = 3 - 2p$), which the theorems about overflow are for. Three scripts also
compute in `binary64` and `binary32` (`batch.py`, `rational.py`, `constants.py`).

## The scripts

| Script | Statements | Section of the page |
|---|---|---|
| `directed_1.py` | `add_down_1`, `add_up_1`, `sub_down_1`, `sub_up_1` are the exact directed roundings for all finite operands, and IEEE's sum otherwise; `mul_down_1`, `mul_up_1`, `mul_dir_1` are valid bounds, exact when the product is zero or at least $2^{2p-1}\eta$, at most one step beyond otherwise; the sign of the computed error of `two_prod`; what `two_sum` would do in place of `two_sum_ord` | Building blocks on T |
| `interval_1.py` | I1 to I5 for `interval_add_1`, `interval_sub_1`, `interval_mul_1`; `interval_make_1` on every pair of values: the interval, the whole line for a NaN bound, the empty set otherwise; `interval_neg_1` | Interval kernels, one limb |
| `directed_2.py` | `add_ball_2_2`, `mul_ball_2_2` return the ball kernels' values for radii zero; `add_down_2_2`, `add_up_2_2`, `mul_dir_2_2` return normalized pairs on the right side, within both forms of the tightness bound; a sum is computed as zero exactly when it is zero, and both its bounds are then zero; how often `Fast2Sum` without ordering is outside its requirement, and wrong | Bounds of two limbs |
| `interval_2.py` | I1 to I5 for `interval_add_2`, `interval_mul_2`; a bound of the exact range of a sum that is zero is returned as zero | Interval kernels, two limbs |
| `enclosure_1.py` | `interval_mid_rad_1`, `ball_to_interval_1`, `ball_split_1`; `ball_from_interval_2` on every pair of values, with the whole line for a NaN bound; the exact predicates of `Ball<T, 1>` | One enclosure interface |
| `enclosure_2.py` | midpoint and radius, ball to interval (a bound that is exactly zero included), and the certain test of a point, on two limbs | One enclosure interface |
| `scaling.py` | `ball_mul_pow2_1`, `ball_mul_pow2_2`: containment, and exactness where stated; `succ` and `pred` on every value; `prod` as an FMA and as a plain product | Scaling a ball by a power of two; Building blocks on T |
| `batch.py` | the summation theorem on sequential, lane and random trees; `dot` of two limbs; the fused dot product of one limb in the sequential order and in the lane order; `bound_sum_2`, `bound_dot_2`, `bound_dot_1`; the radii of the `BallVector` kernels; `conv_radius` and the product of polynomials; the accumulator's magnitude | Batch kernels; BallVector |
| `rational.py` | a model in integer arithmetic of `rational(num, den)`, the three-word method of the page's first version, equals the specification, limb for limb. It is not a test of the header, whose computation is another and which the oracle tests | Constants at compile time |
| `convert.py` | conversions between a wide and a narrow format, of numbers and of balls | Limbs of another type |
| `constants.py` | the constants $A$ and $B$ of the two-limb bounds in `binary64` and `binary32` | Bounds of two limbs |
| `ballvector.py` | the constructor of a BallVector proposed in `kernels/` (`bv_make_1`, `bv_make_2`): its result is canonical; it is the whole space exactly when the radius given is negative, a NaN or $+\infty$, or a center is not finite; otherwise the centers and the radius given; the same in every order | BallVector |
| `accumulator.py` | the kernels of the accumulator: the inequality the radius rests on, $\sum_i \lvert x_i y_i\rvert \le (1+u)^{n+2}(a + n\eta/2)$, after random sequences of `add`, `add_product` and `merge`; the proposed `acc_radius` above its claimed expression, and the chain error $\le$ radius with `bound_dot_k`; in the format itself, the sum of magnitudes $+\infty$ while the running sum is finite, and the radius's mask false for a sum of magnitudes that is not finite | The accumulator |
| `rules_report.py` | what the generator's rules say of the 47 proposed kernels (2 in `kernels/`, 45 in `gen/kernels`), and the operations of each after inlining | Experiments |

## Rerun

```
sh experiments/milestone2/run_all.sh
```

from the repository root, with Python 3 and nothing else. It takes about twenty minutes on one
core and writes the output of each script to `results/`. The outputs recorded there are those
of 2026-11-19 and 2026-11-20. The samples are drawn with a fixed seed, so a rerun prints the
same lines.

## What the runs changed

Three statements were changed by a run before the page was written:

- The bound of two limbs was to be renormalized by `Fast2Sum(z0, w)`. Its requirement
  $\lvert z_0\rvert \ge \lvert w\rvert$ fails for small $z_0$, and at three bits of precision the
  result is then not $z_0 + w$ in some cases; in those found it was a wider bound, never one on
  the wrong side (`directed_2.py`). The listing uses `two_sum_ord`.
- The second limb of `rational` was to be the rounding of what the first limb left. That pair is
  not always normalized (`rational.py`); the result is its renormalization.
- A conversion to a narrow format can overflow in its renormalization, when the first limb is
  the largest number of the format (`convert.py`).

And one consequence was found, which the page recorded as a question: as first decided, the sum
of two zero intervals of two limbs was not the zero interval (`interval_2.py`).

## What two decisions changed

Two questions of the page were decided on 2026-11-20, and the descriptions and the scripts were
revised with them.

- A NaN given as a bound gives the whole line, where the first version gave the empty set, as
  IEEE 1788 does: `interval_make_1` and `ball_from_interval_2`, judged on every pair of values
  by `interval_1.py` and `enclosure_1.py`. Reversed bounds, $[+\infty, +\infty]$ and
  $[-\infty, -\infty]$ still give the empty set.
- The directed sums of two limbs take the bound zero when the computed sum is zero:
  `add_down_2_2` and `add_up_2_2`. This is sound because the bound of `add_2_2` is relative, so
  the computed sum is zero exactly when the exact one is; `directed_2.py` asserts that on every
  sum it runs, operands in the underflow range included, and that both bounds are then zero.
  `interval_2.py` and `enclosure_2.py` check what follows for an interval sum and for the
  bounds of a ball. The product is left as it was: `directed_2.py` counts the products that are
  computed as zero and are not zero.

One more listing changed for a rule of the generator, which forbids a kernel to compute with a
subnormal constant in the hardware formats: `ball_from_interval_2` no longer adds $\eta$ to the
radius when a halving was rounded. It takes the number after $d = \mathrm{RU}(h_u - h_\ell)$,
which is at least $d + \eta$ and never more than the earlier result; `enclosure_1.py` asserts
containment and that value on every pair of values. The same rule changed the scalings of a
ball, whose descriptions and script (`scaling.py`) are with the generator. And a second rule,
that a kernel adds no value to itself (GCC rewrites `a + a` as `a * 2` and may fuse that product
into the next addition), changed the test of an exact halving of `ball_from_interval_2`: each
half is doubled back by `prod(h, const up(2))`, the same value as `add(h, h)` as an exact product.
A third rule, that no fused result is negated, directly or through a select, rewrote the lower
bounds of `mul_dir_2_2` and `add_down_2_2` with the same values (above), and refuses one proposal
of `kernels/` as it is written: `ball_split_1` negates `hs = select(fr, h, 0)`, whose first arm is
the product `h = prod(r, const 1/2)`. `rules_report.py` records the refusal; that listing waits
for the stage of the operations of `Ball`, where it is to be written again.

## What the proofs changed

The summation theorems of the page were proved in Rocq after these runs
(`proofs/theories/Folds.v`, `Summation.v`, `SummationKernels.v`). Nothing that had been run was
found false. The proof stated the dot product of one limb, whose step is one fused operation,
with its own bound, and `batch.py` gained that case, which no run had covered: the fused step in
the sequential order and in the lane order as `Folds.v` defines it, against the proved bound,
and the description `bound_dot_1`, against the two terms of that bound.

## What the runs had missed

A reading of the page's mathematics by a reviewer who was given the page, and not these scripts'
conclusions, found two statements that were false as first written. No run had caught them,
because the cases lay outside what the scripts ran; the scripts now run them.

- The conversion of two wide limbs to two narrow ones was stated with an underflow term of
  $\tfrac12\eta$. That holds only when $u_w \le u^2$, which the three pairs of formats of the
  first runs all satisfied. `convert.py` now has two pairs that do not; the term is
  $(1 + u_w)\tfrac12\eta$, and the script counts the cases beyond the first form (1 and 14).
- The comparisons of balls of one limb that are not strict (the "no" of `X < Y`) were to be
  `le_2_2` on two exact pairs. When both sums overflow, both pairs are $(+\infty, -\infty)$ and
  the comparison is true whatever the truth is. `enclosure_1.py` only ran the strict one; it now
  runs both, with the test of finiteness that the page adds, and counts the answers that would
  be wrong without it (79 of 36 100 in the smallest format).

The same reading corrected one remark, which `directed_1.py` now measures: the products whose
computed error is zero although the exact one is not have a rounded product of at most
$(1 - 2u)P$, not $(1 - u)P$.
