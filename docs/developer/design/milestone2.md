# Milestone 2 statements: intervals, the enclosure interface, batch kernels and BallVector

[Milestone 1](milestone1.md) gave numbers of one and two limbs their arithmetic, `Ball`, and a
defined behavior at overflow. Milestone 2 adds what a program needs to compute with sets and with
arrays: `Interval`, one interface shared by `Interval` and `Ball`, the building blocks as public
functions, constants built at compile time, sums and dot products over arrays with their bounds,
and `BallVector`. This page states what each of them will guarantee, before any of it is written.
It is the contract that the generator, the proofs, the oracle and the public headers of the
milestone are built against. Notation is that of [Numbers](phase0/numbers.md) and of
[Milestone 1 statements](milestone1.md); limbs are `float` and `double`, and $k$ is 1 or 2.

**What is proved, and what is not.** Nothing on this page is implemented, and nothing on it is
proved. Every statement is a *target*: something I believe provable with the lemmas that exist,
for the reason given next to it. Every listing was run through the generator's exact interpreter
and judged with exact rationals on every operand of small formats, or on samples where there are
too many; the scripts and their recorded output are in
[`experiments/milestone2/`](https://github.com/danielepanozzo/kairn/tree/main/experiments/milestone2),
and a number that comes from one of them names it. Such a run is evidence that a statement is not
wrong, never a proof of it. Where a point is not settled it is in the
[open questions](#open-questions).

How each section reads: two or three plain sentences on what is guaranteed and why it matters;
the exact statement; the kernel, in the operations of the
[IR](../architecture.md#the-kernel-ir); how it is to be proved and from which lemmas; what is
not claimed.

## In short

- **Rounding down and up without a rounding mode** is one listing per operation: the rounded
  result, the sign of its exact error, one step to the neighbor. Sums are the exact directed
  rounding for all finite operands; products are, except below $2^{2p-1}\eta$ ($2^{-969}$ for
  `double`), where the bound is valid and at most one number of the format wider.
- **`Interval<T, 1>`** returns the tightest interval of `T` for sums and differences, and for
  products outside that range. **`Interval<T, 2>`** returns bounds within about $8u^2$ (sums)
  and $10u^2$ (products) of the exact ones, relative to their magnitude, plus about $2^{-1021}$
  for `double`.
- **One departure from a decision taken at the start matters**: the bound of two limbs is not
  renormalized by `Fast2Sum` as it stands. Its requirement fails whenever the leading limb is
  below about the smallest normal number, zero included. At three bits of precision its result
  is then not the exact sum of its operands (in every case found the bound stayed valid and was
  only wider); from four bits on no failure was found, but no proved lemma covers those cases.
  The listing orders the two operands first
  ([below](#the-renormalization-and-why-it-is-not-fast2sum)).
- **Batch kernels** are folds of the proved kernels of Milestone 1 over arrays. One theorem
  covers every order of summation; the bound is exported as a function of $n$ that is itself a
  generated, proved kernel. `BallVector` is built on top of them.
- **Three things are not machine-checked by design** and are recorded as such: the integer code
  of `rational`, the compositions the headers make of proved kernels where this page says so,
  and the semantics of IEEE 1788, which are checked against public test cases and not against
  the standard's text.

## Decisions adopted and changed

The twelve decisions taken before this page was written are adopted. This table says where the
work changed one, or found a consequence that the decision did not state.

| Decision | State | What changed, or what follows from it |
|---|---|---|
| 1. Directed rounding on one limb | adopted | The operands of a sum are ordered by a kernel of its own, `two_sum_ord`. The underflow range of a product is recognized on the rounded product, and a zero factor on the operands. One lemma is needed beyond Flocq's: the error of a product whose rounding is at least $2^{2p-1}\eta$ is a number of the format |
| 2. `Interval<T, 1>` | adopted | A product costs eight steps to a neighbor; in packed code each is about ten integer operations |
| 3. `Interval<T, 2>` | **changed** | `Fast2Sum(z0, RD(z1 - d))` is replaced by `two_sum_ord`: the requirement of `Fast2Sum` does not hold when $\lvert z_0\rvert$ is below about the smallest normal number. The bound $d$ is the radius of the Milestone 1 ball with radii zero, bit for bit. Consequence found: the sum of two zero intervals is $[-H, H]$, not $[0, 0]$ ([question 2](#open-questions)) |
| 4. Statements in the IEEE model | adopted | For one limb, "bounded" has an exact condition, not only a sufficient one |
| 5. One enclosure interface | adopted | For `Ball<T, 2>` the tests of membership and the comparisons are *certain*, not exact: they never answer wrongly, and may decline to answer within a few $u^2$ of the boundary. `lower_as` of a `Ball<T, 2>` is a valid bound within two steps of `T`, not the exact rounding |
| 6. Three-valued comparisons | adopted | With an empty operand the answer is *unknown*; the relations of IEEE 1788 keep the standard's conventions |
| 7. Batch kernels | adopted | The theorem needs less than asked: an error relative to the operands of each addition suffices, so it also covers the fast addition. The exported bound is finite for $n\varepsilon \le \tfrac14$ and not for all $n\varepsilon < 1$, and avoids a division |
| 8. `BallVector` | adopted | The radius of a sum, a difference and a scaling *equals* the largest entrywise `Ball` radius. That of a convolution comes from the theorem of the dot product and is not compared with a ball-by-ball evaluation. A kernel whose operations are exact adds nothing to the radius. There is no empty state |
| 9. Public building blocks | adopted | A building block that adds its operands needs the guard of rule R3 once it is public, hence *entry* forms of seven of them. `rmul` and the scalings by a power of two become `constexpr` by a rule of the printer and one lemma, without variant kernels |
| 10. Constants at compile time | adopted | The second limb cannot be "the rounding of what the first left": that pair is not always normalized. The value is fixed uniquely all the same |
| 11. Limbs of another type | adopted | Needs kernels with two formats, which the IR does not have |
| 12. IEEE 1788 | adopted | The test cases of ITF1788 that came from libieeep1788 are under the Apache license and can be used; those from MPFI, FI_LIB and C-XSC are under the LGPL and are not copied |

## Notation and vocabulary

The notation of Milestone 1, and four more symbols.

- $N = \eta/(2u) = 2^{p-1}\eta$ is the smallest normal number: $2^{-1022}$ for `double`,
  $2^{-126}$ for `float`.
- $P = \eta/(2u^2) = 2^{2p-1}\eta$ is the threshold above which the error of a product is a
  number of the format ([`two_prod`](../architecture.md#kernels-of-the-first-wave)):
  $2^{-969}$ for `double`, $2^{-102}$ for `float`.
- $\mathrm{RD}(t)$ and $\mathrm{RU}(t)$ are the largest number of the format not above $t$ and
  the smallest not below it. *In the format with overflow*, which is the sense of every
  IEEE-model statement here, $\mathrm{RD}(t) = -\infty$ when $t < -\Omega$ and
  $\mathrm{RD}(t) = \Omega$ when $t > \Omega$, and symmetrically for $\mathrm{RU}$.
- A *step* is `succ` or `pred`: the next number of the format above or below.

The sign of a zero is never part of a statement, as before.

In the listings, `const 1/2`, `const eta`, `const N` and `const P` stand for `const up(1/2)`,
`const up(eta)`, `const up(eta/(2*u))` and `const up(eta/(2*u^2))`, which are exact, and
`const E`, `const G`, `const H` for the three constants of the ball kernel named next to the
listing. Where two short operations share a line, or a call is written inside another, it is to
save space: a description has one operation per line.

### Additions to the claims

The vocabulary of [`gen/claims.json`](../architecture.md#claims) grows as follows. Everything
that exists keeps its meaning.

| Addition | Fields | Meaning |
|---|---|---|
| `neighbor` | `of`, `side`: `up` or `down` | the output is the next number of the format above or below the operand, for every operand, as the [table](#next_up-and-next_down-on-every-input) gives it |
| `rounded`, with two operands, in the extended domain | as before | when an operand is infinite or a NaN, the output is `value` as IEEE 754 defines it on the operands |
| `rounded`, with `when` | `when`: `product_large` | the output is the directed rounding of `value` when the condition holds |
| `bound` | `of`, `side`: `below` or `above`, `steps` | the output is on that side of `value`, and at most `steps` steps of the format beyond its directed rounding; in the extended domain, with an infinite or NaN operand, the output is `value` as IEEE 754 defines it |
| `outward` | `of` (a 2-limb output), `side`, `rel`, `abs` | the output is on that side of `value`, and $\lvert\text{output} - \text{value}\rvert \le \mathrm{rel}\cdot\lvert\text{value}\rvert + \mathrm{abs}$ |
| `interval` (a requirement) | `interval(L, U)` | the two groups are the bounds of a canonical interval ([below](#values-of-an-interval)) |
| `encloses_interval` | `lower`, `upper`, `set`, `intervals`, `tight`, `bounded_when` | statements I1 to I5 of [Interval kernels](#interval-kernels): `set` is an expression over interval names, `intervals` gives each name its bounds, `tight` is `rounded` (with optional `steps` and `when`) or a pair `rel`, `abs`, and `bounded_when` is a list of conditions |
| `makes_interval` | `lower`, `upper`, `from` | the output is the canonical interval of the given bounds, or the empty set when they describe none |
| `certain` | `of` (a mask), `rel`, `args`, `exact_when` | when the mask is true the relation holds between the exact values; it is true whenever the relation holds and the condition `exact_when` does (always, when the condition is absent) |
| `trit` | `yes`, `no` (masks), `rel`, `sets` | `yes` implies that the relation holds for every member of the sets, `no` that it fails for every member; never both |
| `exact_when` on `error` | a condition | the error is zero when the condition holds (it is what `mul_pow2_2_exact` says today in a hand-written statement) |
| a condition `{"abs_le": EXPR, "omega": true}` | | $\lvert\mathrm{EXPR}\rvert \le \Omega$ |
| expressions of constants | `rel`, `abs` | the language of `const up(EXPR)`: `u`, `eta`, integers, `unit(K)`, `tiny(K)`, the four operations and integer powers, and now `up( )` inside an expression, so that a bound can name a constant as the format rounds it |
| `format` (a requirement) | `format(half)` | the statement is for formats that contain the number $\tfrac12$ ($\eta \le \tfrac12$); every format of the shape of `binary64` does |
| a fold | [below](#folds-the-extension-of-the-ir) | a step kernel applied along arrays, in a declared order |

`outward` needs constants "as the format rounds them" because a bound such as
$2(1+u)^3\,G\,E$ uses the constants $E$ and $G$ of a ball kernel, which are expressions rounded
up; in a format of three or four bits they are far from their expressions, and a claim written
with the expressions alone would be false there.

## Building blocks on T

These are the functions on plain `T` that the rest is made of, and that a program may call for
its own exactness tests and its own radius arithmetic. Two things change for the ones that
already exist: they become public, and the ones that a program uses for radii work in constant
expressions and give the same bits there as at run time.

| Public function | Kernel | Statement | `constexpr` | Rounds |
|---|---|---|---|---|
| `two_sum(a, b)` | `two_sum_entry` | $s = \mathrm{RN}(a + b)$, $s + e = a + b$ | yes | yes |
| `fast_two_sum(a, b)` | `fast_two_sum_entry` | the same, and $(s, e)$ normalized; requires $\lvert a\rvert \ge \lvert b\rvert$ | yes | yes |
| `two_prod(a, b)` | `two_prod` | $p = \mathrm{RN}(ab)$, $\lvert p + e - ab\rvert \le \tfrac12\eta$, exact when $ab = 0$ or $\lvert ab\rvert \ge P$ | yes (Dekker's product, with $\tfrac{13}{8}\eta$ for $\tfrac12\eta$) | yes |
| `next_up(a)`, `next_down(a)` | `next_up`, `next_down` | the neighbors, on every input ([table](#next_up-and-next_down-on-every-input)) | yes | no |
| `radd(a, b)` | `radd_entry` | for $a, b \ge 0$: $r \ge a + b$, at most $\tfrac32$ gaps above | yes | yes |
| `rmul(a, b)` | `rmul` | for $a, b \ge 0$: $r \ge ab$, at most $\tfrac32$ gaps above | **new** | yes |
| `add_down`, `add_up`, `sub_down`, `sub_up` | `add_down_entry`, ... | $\mathrm{RD}$ or $\mathrm{RU}$ of the exact result, for all finite operands | yes | yes |
| `mul_down`, `mul_up` | `mul_down_1`, `mul_up_1` | a bound on the right side; the exact rounding when $ab = 0$ or $\lvert ab\rvert \ge P$, at most one step beyond otherwise | not yet | yes |
| `abs_upper(x)`, `to_down(x)`, `to_up(x)`, `to_nearest(x)` | Milestone 1 | the exact rounding of a 2-limb $x$ to `T` | yes (today) | no |

"Rounds" says whether the result depends on the rounding mode; it is the subject of
[Functions that do not round](#functions-that-do-not-round). `mul_down` and `mul_up` contain
`two_prod`, whose variant for constant evaluation is Dekker's product. Below $P$ the error term
of that variant is not the one of the FMA: it is within $\tfrac{13}{8}\eta$ of the exact error
and can have the other sign, and the listings below trust the sign of a nonzero error term. So
`mul_down_1` and `mul_up_1` are stated for the FMA only, the generator must not evaluate them
through the variant of `two_prod`, and their constant evaluation is left for the milestone that
makes the two-limb products `constexpr`
([deviation 14](phase0/decisions.md#deviations-from-the-brief-flagged)).

**Outside the domain.** None of these functions traps or has undefined behavior, on any values
of `T`. What a statement does not cover is this:

| Function | Outside its domain |
|---|---|
| `two_sum` | $s$ is the sum of IEEE 754 in every case. $s + e = a + b$ needs a finite $s$ and $\lvert b\rvert < \Omega$: with $b = \pm\Omega$ the error term can be a NaN although $s$ is finite ([Milestone 1](milestone1.md#what-is-proved-about-an-arithmetic-kernel)). An infinite or NaN operand gives a NaN error term |
| `fast_two_sum` with $\lvert a\rvert < \lvert b\rvert$ | $s$ is still $\mathrm{RN}(a + b)$; $e$ is a number of the format, and $s + e$ need not be $a + b$ ([an example](#the-renormalization-and-why-it-is-not-fast2sum)). A debug build checks the requirement |
| `two_prod` | below $P$ the error term is rounded, as stated; a product that overflows gives $p = \pm\infty$ and the opposite infinity as $e$ |
| `radd`, `rmul` with a negative operand | the result is still not below the exact value; it can exceed it by 2 gaps instead of $\tfrac32$ (measured in Milestone 1, not claimed) |
| the directed sums and products, `next_up`, `next_down` | nothing is outside: the tables below cover infinities and NaN |

A weighted norm, such as the largest $\lvert m_i\rvert / s_i$ of a polynomial with scaled
coefficients, is not a kernel of Kairn. It is built from two entries of this table:
`abs_upper(x)`, an upper bound in `T` of $\lvert x\rvert$, and `rmul`, an upper bound of a
product of two such bounds. Both are `constexpr`.

### Values that enter from the program

A building block that is public is an *entry* kernel
([rule R3](../architecture.md#the-kernel-ir)): the program may pass it a product, and a
contracting compiler may then fuse that product into the first addition of the block. For
`two_sum(a * b, c)` this is not a loss of accuracy but a wrong result: the error term is computed
from a sum that no longer is $\mathrm{RN}(a + b)$. So the blocks that *add* an operand guard it,
in a kernel of their own, and the blocks that only multiply or compare their operands are entry
kernels as they are.

```
two_sum_entry(a, b) -> (s, e)        fast_two_sum_entry, radd_entry, add_down_entry,
  ga     = guard(a)                  add_up_entry, sub_down_entry, sub_up_entry: likewise,
  gb     = guard(b)                  both operands guarded, then the kernel of the same name
  (s, e) = two_sum(ga, gb)
```

`two_prod`, `rmul`, `mul_down_1`, `mul_up_1`, `next_up` and `next_down` need no guard: their
operands are factors of a product, operands of a comparison, or bit patterns. Inside Kairn the
unguarded kernels are called, as before.

*Statement.* That of the kernel called, since `guard(a)` has the value of `a`
([Milestone 1](milestone1.md#values-that-enter-from-the-program)). *Cost:* two additions.
*Not claimed:* the sign of a zero result, which the guard can change.

### next_up and next_down on every input

`next_up(a)` is the IR's `succ` and `next_down(a)` its `pred`: `nextUp` and `nextDown` of
IEEE 754, computed on the bit pattern, without a floating-point operation. They are written
out for every input because a program that has its own `nextUp` may have defined it otherwise
for negative numbers and for $-\infty$.

| `a` | `next_up(a)` | `next_down(a)` |
|---|---|---|
| a NaN | a NaN | a NaN |
| $+\infty$ | $+\infty$ | $\Omega$ |
| $\Omega$ | $+\infty$ | the number before $\Omega$ |
| positive, finite | the next number, away from zero | the previous number, toward zero |
| $\eta$ (the smallest positive number) | $2\eta$ | $+0$ |
| $+0$, $-0$ | $\eta$ | $-\eta$ |
| $-\eta$ | $-0$ | $-2\eta$ |
| negative, finite | the next number, *toward zero* | the previous number, away from zero |
| $-\Omega$ | the number after $-\Omega$ | $-\infty$ |
| $-\infty$ | $-\Omega$ | $-\infty$ |

Subnormal numbers are stepped like the others: below $2N$ every step is $\eta$. The rows where
another definition is most likely to differ are the negative ones: `next_up` of a negative
number moves *toward* zero (it is the next number in the order of the real line, not the next
in magnitude), and `next_up` of $-\infty$ is the finite number $-\Omega$, not $-\infty$. A step
that arrives at zero gives the zero of the sign it came from; as everywhere, that sign is not
part of the statement.

*Proof.* Flocq's `Bsucc_correct` and `Bpred_correct`, as Milestone 1 uses them for `to_up_2`
(`succ_finite`, `pred_finite`, `succ_pinf` in `IeeeOps.v`). *Checked:* `scaling.py`, every
value of four formats.

### Rounding a sum down and up

For any two finite numbers, `add_down_1` returns the largest number of the format that is at
most their exact sum, and `add_up_1` the smallest that is at least it. These are what a rounding
mode would give, obtained in round-to-nearest, and they are exact in every case: there is no
range of operands where the result is only "a valid bound".

```
two_sum_ord(a, b) -> (s, e)          add_down_1(a, b) -> r            add_up_1(a, b) -> r
  aa     = abs(a)                      (s, e) = two_sum_ord(a, b)       (s, e) = two_sum_ord(a, b)
  ab     = abs(b)                      n      = lt(e, 0)                n      = lt(0, e)
  m      = lt(aa, ab)                  p      = pred(s)                 q      = succ(s)
  h      = select(m, b, a)             r      = select(n, p, s)         r      = select(n, q, s)
  l      = select(m, a, b)
  (s, e) = fast_two_sum(h, l)        sub_down_1(a, b), sub_up_1(a, b): neg(b), then the sum
```

`two_sum_ord` is `Fast2Sum` on the operands ordered by magnitude
([Dekker's algorithm with its comparison](phase0/references.md#bgm17), the comparison as two
selects). The ordering is the reason it exists: `two_sum` computes an error term that is a NaN
when its second operand is $\pm\Omega$ although the sum is finite, the tests `e < 0` and `0 < e`
are then both false, and the "bound" returned is the rounded sum, which can be on the wrong
side. This is the decision of the
[log of 2026-11-18](phase0/decisions.md#decisions-log). Measured on every pair of operands of
nine small formats: with `two_sum` the bound is on the wrong side for 2 pairs at three bits of
precision, 6 at four and 14 at five; with `two_sum_ord`, never (`directed_1.py`).

**Statement in the real model** (no overflow), for numbers $a$, $b$ of the format, from $p = 2$.

- `two_sum_ord`: $s = \mathrm{RN}(a + b)$, $s + e = a + b$ exactly, and $(s, e)$ is normalized.
  No requirement.
- `add_down_1`: $r = \mathrm{RD}(a + b)$. `add_up_1`: $r = \mathrm{RU}(a + b)$. Likewise the
  differences. *The sign of the computed error is the sign of the exact error in every case*,
  because the computed error is the exact error.

**Statement in the IEEE model**, for any two values of `T`.

| Operands | `two_sum_ord` | `add_down_1` | `add_up_1` |
|---|---|---|---|
| finite, $\lvert\mathrm{RN}(a + b)\rvert \le \Omega$ | as in the real model; $e$ is finite | $\mathrm{RD}(a + b)$ | $\mathrm{RU}(a + b)$ |
| finite, the rounded sum overflows upward | $(+\infty, -\infty)$ | $\Omega$ | $+\infty$ |
| finite, the rounded sum overflows downward | $(-\infty, +\infty)$ | $-\infty$ | $-\Omega$ |
| one infinite, or two equal infinities | (that infinity, NaN) | that infinity | that infinity |
| $+\infty$ and $-\infty$, or a NaN | (NaN, NaN) | NaN | NaN |

The second and third rows are again the directed rounding in the format with overflow, so the
one sentence "the output is `value` rounded down" covers the first three rows. No fix-up is
needed: at an overflow the error term is the infinity of the *opposite* sign, which is exactly
what makes the test choose the right neighbor.

*Proof.* Real model: `fast_two_sum_correct` after a case split on the select, which gives its
requirement $\lvert h\rvert \ge \lvert l\rvert$; then, with $x = a + b$: if $e < 0$ then $s > x$,
so $s = \mathrm{RU}(x)$ and $x$ is not a number of the format, and
$\mathrm{pred}(\mathrm{RU}(x)) = \mathrm{RD}(x)$ (Flocq's `pred_UP_eq_DN`); otherwise $s \le x$
and a rounding to nearest that is at most $x$ is $\mathrm{RD}(x)$. This is the argument of
`to_down_2_eq` in `Convert.v`. IEEE model: `fast_two_sum_ieee_correct` (its error term is finite
whenever its sum is), `succ_finite` and `pred_finite`, and the three non-finite rows by cases on
the constructors, as in `IeeeExt.v`. *Smallest precision:* 2. *Risk: low*; the lemmas exist and
the listing is short.

*Not claimed:* the sign of a zero result ($a + (-a)$ rounded down is $-0$ under IEEE 754's
downward mode and $+0$ here).

### Rounding a product down and up

`mul_down_1` returns a number that is at most the exact product, and `mul_up_1` one that is at
least it; for all finite operands, always. Away from the underflow range, and for a product
that is exactly zero, it is the exact directed rounding. In the underflow range it can be one
number of the format wider than necessary, because there the error of a product is not always a
number of the format and its computed value can be zero when the true one is not.

```
mul_down_1(a, b) -> r                          mul_up_1(a, b) -> r
  (p, e) = two_prod(a, b)                        (p, e) = two_prod(a, b)
  ap     = abs(p)                                ap     = abs(p)
  bd     = lt(ap, const P)       below P         bd     = lt(ap, const P)
  ez     = eq(e, 0)                              ez     = eq(e, 0)
  un     = and(bd, ez)           undecided       un     = and(bd, ez)
  n      = lt(e, 0)                              n      = lt(0, e)
  sd     = or(n, un)                             su     = or(n, un)
  pp     = pred(p)                               sp     = succ(p)
  d      = select(sd, pp, p)                     v      = select(su, sp, p)
  za     = eq(a, 0)                              za     = eq(a, 0)
  zb     = eq(b, 0)                              zb     = eq(b, 0)
  zz     = or(za, zb)            a zero factor   zz     = or(za, zb)
  r      = select(zz, p, d)                      r      = select(zz, p, v)
```

`const P` is `const up(eta/(2*u^2))`, exact. The listing steps outward in two cases: the
computed error has the sign that says so, or the product is below $P$ and the computed error is
zero, which below $P$ proves nothing. A zero factor is recognized on the operands, not on the
product: $p = 0$ and $e = 0$ also come out of a nonzero product of at most $\tfrac12\eta$.

**When the sign of the computed error is the sign of the exact error.** Write
$\delta = ab - p$ for the exact error and $e = \mathrm{RN}(\delta)$ for the computed one
(`two_prod`'s second line is one rounding of $ab - p$). Rounding is monotone and
$\mathrm{RN}(0) = 0$, so *$e$ is zero or has the sign of $\delta$*, for all finite operands.
The two signs differ in exactly one situation: $e = 0$ and $\delta \ne 0$, which happens exactly
when $0 < \lvert\delta\rvert \le \tfrac12\eta$. That requires $ab$ not to be a multiple of
$\eta$, hence $0 < \lvert ab\rvert < P$. So the sign is right whenever $ab = 0$ or
$\lvert ab\rvert \ge P$, and whenever $e \ne 0$.

**Statement in the real model**, for numbers $a$, $b$ of the format, from $p = 2$.

- $\mathrm{mul\_down\_1}(a, b) \le ab \le \mathrm{mul\_up\_1}(a, b)$.
- If $ab = 0$ or $\lvert ab\rvert \ge P$: $\mathrm{mul\_down\_1}(a, b) = \mathrm{RD}(ab)$ and
  $\mathrm{mul\_up\_1}(a, b) = \mathrm{RU}(ab)$.
- Otherwise the results are $\mathrm{RD}(ab)$ or the number before it, and $\mathrm{RU}(ab)$ or
  the number after it.

**Statement in the IEEE model.** For finite operands the same, in the format with overflow: a
product that overflows upward gives $\Omega$ and $+\infty$, one that overflows downward
$-\infty$ and $-\Omega$ (the error term is again the opposite infinity). For an infinite or NaN
operand the result is the product of IEEE 754: the infinity of the product's sign, and a NaN for
$0 \cdot \infty$ and for a NaN operand.

*How wide the range is, measured.* In the seven formats of the shape of `binary64` of
`directed_1.py`, 31 to 49% of all pairs of operands have a nonzero product below $P$ (small
formats have few exponents), and of those 79 to 84% are one step wider than the exact rounding
at two bits of precision, 61 to 62% at three, 50 to 51% at four and 39% at five. Many are
products that are exact: below $P$ an exact product and an inexact one whose error rounds to
zero cannot be told apart by this listing. How low could the threshold be? The products whose
computed error is zero although the exact one is not have a rounded product of at most
$(1 - 2u)P$, in every format of the run and by the argument of the proof below; so the test
could stop one number of the format before $P$, and no lower. The listing keeps $P$, the
threshold of `two_prod`'s own statement. For `double` the range is below $2^{-969}$.

*Proof.* From the three facts of `two_prod_exact` (`EFT.v`): $p = \mathrm{RN}(ab)$, the defect
$\lvert p + e - ab\rvert \le \tfrac12\eta$, and exactness above $P$. The monotonicity of
rounding gives the sign statement (`round_le`, `round_0`). One lemma is new: *if
$\lvert\mathrm{RN}(ab)\rvert \ge P$ then $\mathrm{RN}(ab) - ab$ is a number of the format.*
Flocq's `mult_error_FLT` has it for $\lvert ab\rvert \ge P$; the case of a product just below
$P$ that rounds up to $P$ needs the exponents: the canonical exponents of $a$ and $b$ then sum
to at least $q_{\min}$ (were the sum $q_{\min} - 1$ or less, the product would be at most
$(1 - u)^2 P$, which rounds to at most $(1 - 2u)P$), so $ab$ is a multiple of $\eta$, and Kairn's
`format_multiple` and `FLX_multiple` (`Format.v`) conclude. IEEE model: `two_prod_ieee_correct`
(its error term is finite whenever its product is) and cases on the constructors. *Smallest
precision:* 2. *Risk: medium*, for the new lemma. Should it resist, the test `lt(ap, P)` becomes
`le(ap, P)`: the statement then says "$\lvert ab\rvert > P$" and needs Flocq's lemma only.

*Not claimed:* the exact rounding below $P$. It can be had by rescaling, as the `kv` library
does ([kv](phase0/references.md#kv)); see [question 6](#open-questions).

### The two executions of a product

The radius helpers must work in constant expressions, and give there the same bits as at run
time, so that a program can compute a table of radii at compile time and compare it with what a
device computes. `rmul` does not today, because its product is an FMA, which C++20 cannot
evaluate at compile time. No new kernel and no new real-model proof is needed to change that.

A product `prod(a, b)` has two executions: `fma(a, b, +0)` at run time, and the plain `a * b` in
constant evaluation, where nothing is contracted. As real numbers both are $\mathrm{RN}(ab)$, so
*the formal model of the real numbers is the same definition for both*, and every real-model
theorem holds for both without a word changed. As IEEE values they differ in one case only: when
the product is *exactly* zero and its sign negative, `a * b` is $-0$ and `fma(a, b, +0)` is
$(-0) + (+0) = +0$. A product that underflows to zero is the same in both (the exact sum
$ab + 0$ is not zero, so the result takes the sign of $ab$), and so are infinities; which NaN is
returned is unspecified in both.

- **`rmul(a, b)` is `succ(prod(a, b))`**, and `succ` of either zero is $\eta$. So the two
  executions give the same bits whenever the product is not a NaN (a NaN operand, or
  $0 \cdot \infty$, which is not a constant expression anyway), inside and outside the domain
  of the statement. *Checked:* `scaling.py`, every pair of values of four formats, signed
  zeros and infinities included: the two products differ on 38 to 286 pairs, all of them exact
  zeros of different signs, and `rmul` differs on none.
- **`mul_pow2_2` and the exact scaling of a ball** ([below](#scaling-a-ball-by-a-power-of-two))
  contain no fused operation but `prod`. Their two executions give the same values; a limb that
  is zero can differ in sign.
- **What it needs.** From the generator: a kernel whose only fused operations are `prod` is
  `constexpr`, and prints each `prod` as `a * b` under `__builtin_is_constant_evaluated()`, as it
  already does inside a constant-evaluation variant. From the proofs: one lemma in the IEEE
  model, *the plain product and the FMA with a zero addend are equal as extended real numbers,
  and equal as values unless the product is an exact zero*, and one remark, that no operation
  of the IR distinguishes the two zeros in its value (the IR has no division and no copy of a
  sign). The IEEE-model statements, which never mention the sign of a zero, then hold of both
  executions. This is a lemma and a printer rule, not the "variant kernels with proofs of their
  own" of [deviation 14](phase0/decisions.md#deviations-from-the-brief-flagged); those remain
  necessary for every kernel with an FMA whose addend is not zero: `two_prod` has one, and the
  two-limb products and the radius of a `Ball` operation need theirs.
- `next_up`, `next_down` and `radd` are `constexpr` today, with the same bits, which the
  generator's tests assert for every kernel without a fused operation.

*Risk: low.*

### Functions that do not round

A program that runs part of its code under a directed rounding mode switches to round-to-nearest
around Kairn, and a debug build of Kairn checks the mode before every operation. A function whose
result cannot depend on the mode needs neither. These are the ones:

| Functions | Why the mode cannot matter |
|---|---|
| `next_up`, `next_down` | integer operations on the bit pattern |
| `neg`, `abs` of a number; negation of an `Interval` or a `Ball` | a sign bit |
| `<`, `<=`, `==` and the other comparisons of numbers of one and two limbs, `sign`, `isfinite` | comparisons of limbs and tests of bit patterns |
| `to_nearest`, `to_down`, `to_up`, `abs_upper` of a 2-limb number | a limb, or a comparison, a step and a select |
| `lower`, `upper`, `lower_as`, `upper_as` of an `Interval` | stored bounds, or the row above |
| `center`, `radius` of a `Ball`; `midpoint` of a `Ball` | stored values |
| `is_empty`, `is_entire`, `is_finite`, `is_whole` | comparisons |
| `hull`, `intersection`, `contains`, the comparisons and the relations of 1788, on `Interval` | comparisons of bounds and selects |
| `certainly_positive`, `certainly_negative`, `certainly_zero` on `Interval` and on `Ball` | comparisons (for a ball, of the radius with the center) |
| `traits<X>::add` and the other constants | data |

And these *look* as if they did not round, and do:

| Function | What it computes |
|---|---|
| `is_normalized(x)`, and the check of a canonical operand in a debug build | an addition, compared with the leading limb: under a directed mode it accepts and refuses other pairs |
| a constructor from a `T` or from a number of one limb (`Expansion<T, 2>(a)`, `Ball(c, r)`, `Interval(lo, hi)`) | the guard, `a + 0`. Its value is `a` in every mode, so the object is the same number; only the sign of a zero depends on the mode. It may be exempt from the check, with that remark |
| `contains`, the comparisons, `hull`, `intersection`, `split` on a `Ball` | bounds $c \pm r$, computed |
| `midpoint`, `radius`, `split` of an `Interval`; every conversion between `Interval` and `Ball` | sums and halvings |
| `traits<X>::sum(n)`, `dot(n)` with a run-time $n$ | products and sums ([below](#the-bound-as-a-function-of-n)) |
| `rational(num, den)` | nothing: integer arithmetic only. It is exempt |

*Proposed:* the debug build's check stays on every function of the second table but the
constructors and `rational`, and is removed from the functions of the first. No statement
depends on this; it is a property of the headers, tested by running each exempt function under
the four rounding modes and comparing bits.

## Interval kernels

An interval is a set of real numbers given by two bounds. Every operation returns an interval
that contains the exact result for every choice of members of its operands, including operands
that reach to infinity, and returns the empty set exactly when an operand is empty. Unlike a
number, an interval has infinite bounds as ordinary values, so its kernels are stated in the
IEEE model from the start: there is no "finite core" at the level of an interval, only inside
it.

### Values of an interval

`Interval<T, k>` stores two k-numbers, `lower` and `upper`. A value is *canonical* when it is

- the **empty set**: `lower` $= +\infty$ and `upper` $= -\infty$ (for two limbs,
  $(+\infty, 0)$ and $(-\infty, 0)$); or
- a **nonempty interval** $[\ell, h]$: neither bound is a NaN, $\ell \le h$, $\ell < +\infty$,
  $h > -\infty$, and each bound is a number of the format or an infinity (for two limbs: a
  finite normalized pair, or $(\pm\infty, 0)$).

It is *bounded* when both bounds are finite. The members of an interval are real numbers:
$[1, +\infty]$ does not contain $+\infty$. There is no NaN interval, and a bound is never a NaN.
The empty set is stored as $(+\infty, -\infty)$ because the hull of two intervals is then the
smaller lower bound and the larger upper bound, with no test, and the intersection likewise.

**Constructor.** Bounds that the program supplies are guarded, as for a `Ball`.

```
interval_make_1(lo, hi) -> (zl, zu)
  gl = guard(lo)
  gu = guard(hi)
  ok = le(gl, gu)                false with a NaN
  nl = lt(gl, const inf)
  mi = neg(const inf)
  nu = lt(mi, gu)
  va = and(ok, nl)
  v  = and(va, nu)
  zl = select(v, gl, const inf)
  zu = select(v, gu, mi)
```

*Statement (`makes_interval`), in the IEEE model, for any two values of `T`:* the result is
canonical; it is $[lo, hi]$ when $lo \le hi$, $lo < +\infty$ and $hi > -\infty$, and the empty
set otherwise, that is when $lo > hi$, when a bound is a NaN, and for $[+\infty, +\infty]$ and
$[-\infty, -\infty]$. This is `numsToInterval` of IEEE 1788, which returns the empty set for an
invalid pair ([IEEE 1788](#ieee-1788)). `interval_make_2` takes two canonical 2-limb values
(objects, so no guard) and is the same listing on the comparisons of two limbs (`le_2_2`, and
the leading limbs for the tests against infinity). *Checked:* `interval_1.py`, every pair of
values of five formats, NaN and infinities included. *Risk: low.* Whether a NaN bound should
give the empty set is [question 1](#open-questions).

### What is stated of an interval kernel

For canonical operands $X$ and $Y$ and the result $Z$ of an operation $\circ$:

- **I1.** $Z$ is canonical.
- **I2.** $Z$ is empty exactly when an operand is.
- **I3. Containment.** For all real $x \in X$ and $y \in Y$: $x \circ y \in Z$. Unbounded
  operands are included.
- **I4. Tightness.** For nonempty operands, how far each bound of $Z$ is from the corresponding
  bound of the exact range $\{x \circ y\}$. Infinite bounds of the exact range are returned as
  such.
- **I5. Bounded when.** A condition on bounded operands under which $Z$ is bounded.

I1 to I3 are what a program relies on. I4 and I5 say that the kernel does not satisfy them by
returning the whole line.

### One limb

For one limb the bounds are computed by the directed primitives, so a sum or a difference is the
tightest interval of `T` that contains the exact range, always. A product is too, outside the
underflow range of [the directed product](#rounding-a-product-down-and-up).

```
interval_neg_1(xl, xu) -> (zl, zu)       interval_add_1(xl, xu, yl, yu) -> (zl, zu)
  zl = neg(xu)                             l  = add_down_1(xl, yl)
  zu = neg(xl)                             h  = add_up_1(xu, yu)
                                           nx = lt(xl, const inf)       X is not empty
interval_sub_1: the same as the sum,       ny = lt(yl, const inf)
  with l = sub_down_1(xl, yu)              ne = and(nx, ny)
  and  h = sub_up_1(xu, yl)                mi = neg(const inf)
                                           zl = select(ne, l, const inf)
                                           zu = select(ne, h, mi)
```

The product has no branch: the four products of bounds, each rounded down and up, then the least
of the four lower values and the greatest of the four upper ones. Scalar and packed code are the
same listing.

```
mul_dir_1(a, b) -> (d, v)                      interval_mul_1(xl, xu, yl, yu) -> (zl, zu)
  the lines of mul_down_1 and of mul_up_1        (d1, v1) = mul_dir_1(xl, yl)
  on one two_prod, down to                       (d2, v2) = mul_dir_1(xl, yu)
  dz = select(sd, pp, p)                         (d3, v3) = mul_dir_1(xu, yl)
  vz = select(su, sp, p)                         (d4, v4) = mul_dir_1(xu, yu)
  zz = or(za, zb)                                ma = lt(d2, d1);  da = select(ma, d2, d1)
  d  = select(zz, 0, dz)                         mb = lt(d4, d3);  db = select(mb, d4, d3)
  v  = select(zz, 0, vz)                         mc = lt(db, da);  l  = select(mc, db, da)
                                                 na = lt(v1, v2);  va = select(na, v2, v1)
                                                 nb = lt(v3, v4);  vb = select(nb, v4, v3)
                                                 nc = lt(va, vb);  h  = select(nc, vb, va)
                                                 the last five lines of interval_add_1
```

`mul_dir_1` differs from the public pair in one line: a zero factor gives the literal zero, not
the rounded product, so that $0 \cdot \infty = 0$. That is the rule of interval arithmetic for
the product of bounds: $[0, 0] \cdot X = [0, 0]$ for every nonempty $X$, and a bound $0$ of
$[0, +\infty]$ times a bound $+\infty$ contributes $0$, not a NaN
([Operations](phase0/operations.md#interval)). Two lines of a listing are written on one line
here to save space; each is still one operation.

**Statement, in the IEEE model, for canonical operands.**

- I1, I2, I3 as above, for the four kernels.
- **I4.** `interval_neg_1` is exact. For the sum and the difference, with $[lo, hi]$ the exact
  range: $z_\ell = \mathrm{RD}(lo)$ and $z_u = \mathrm{RU}(hi)$. For the product: the same when
  each of the four products of bounds is zero, infinite, or at least $P$ in magnitude; otherwise
  $z_\ell$ is $\mathrm{RD}(lo)$ or the number before it, and $z_u$ is $\mathrm{RU}(hi)$ or the
  number after it.
- **I5.** For bounded operands, $Z$ is bounded *exactly* when the exact range lies in
  $[-\Omega, \Omega]$.

*Checked:* `interval_1.py`: all 52 900 and 104 976 pairs of canonical intervals of two formats
of two bits, and samples of 61 000 to 146 000 pairs in three formats of three and four bits,
for the three operations; the exact range of a product is computed there without the rule
$0 \cdot \infty = 0$, by replacing an infinite bound with a number beyond every product of
interest.

*Proof.* I3 for the sum: $x \ge x_\ell$ and $y \ge y_\ell$ give
$x + y \ge x_\ell + y_\ell \ge z_\ell$ by the statement of `add_down_1`; a lower bound $-\infty$
gives $-\infty$. I3 for the product: for real $x \in [x_\ell, x_u]$ and $y \in [y_\ell, y_u]$,
$xy$ is between the least and the greatest of the four products of bounds, taken as extended
real numbers with $0 \cdot \infty = 0$. This is one lemma, proved twice over a linear function:
$xy \ge \min(x y_\ell, x y_u)$ because $t \mapsto xt$ is monotone, with the convention
covering $x = 0$, and each of those is at least the least of two products of bounds for the same
reason. Then the minimum of four lower bounds is a lower bound of the minimum: `lt` and `select`
compute a minimum of values that are not NaN, and none is, since no bound is a NaN and a zero
factor never meets an infinity. I4 is the statement of the primitives and the monotonicity of
$\mathrm{RD}$ and of a step. I5: a directed sum or product is infinite exactly when the exact
value is beyond $\Omega$ on its side; below $P$ a step never leaves the finite range.
I2 and the canonical form are the last selects. New lemmas: the extended product on a
rectangle; the IEEE-model statement of `mul_dir_1`. The rest is `IeeeExt.v`'s way with selects
and comparisons.

*Smallest precision:* 2. *Risk:* low for the sum, the difference and the negation; **medium**
for the product, for the number of cases of its IEEE-model proof (four candidates, each finite,
zero, or infinite).

*Cost.* After inlining (`rules_report.py`): a sum is 6 rounded operations, 2 steps and 20
comparisons, selects and sign operations; a product is 8 rounded operations, 8 steps and 78 of
the others. A step is about ten integer operations in packed code
([Milestone 1](milestone1.md#the-radius-second-design)), so the product is dominated by its
steps; choosing the least pair $(p, e)$ before stepping would need one step per bound and is
[question 15](#open-questions).

*Not claimed:* the tightest interval for a product whose bounds have products below $P$; the
sign of a zero bound (IEEE 1788 asks for $-0$ as a lower bound and $+0$ as an upper one).

### Bounds of two limbs

The bounds of an `Interval<T, 2>` are 2-limb numbers, and no rounding mode and no error-free
transformation gives "the largest 2-limb number below the exact sum". What is computed instead
is a 2-limb number that is certainly below the exact result and close to it: the result of the
round-to-nearest kernel, moved outward by a bound of that kernel's own error.

First, the kernel with its error bound. It is the Milestone 1 ball with radii zero:

```
add_ball_2_2(x, y) -> (z, d)                   mul_ball_2_2(x, y) -> (z, d)
  (z0, z1) = add_2_2(x0, x1, y0, y1)             (z0, z1) = mul_2_2(x0, x1, y0, y1)
  az       = abs(z0)                             az       = abs(z0)
  t        = prod(az, const E)                   t        = prod(az, const E)
  d        = fma(t, const G, const H)            d        = fma(t, const G, const H)
```

$E$, $G$ and $H$ are the three constants of `ball_add_2`, and of `ball_mul_2` for the product
([the radius, second design](milestone1.md#the-radius-second-design)); no constant is new.

*Statement, real model:* $z$ is normalized, and $\lvert z - (x \circ y)\rvert \le d$. In the
claims: `normalized z`, the `error` entry of the center's kernel, and `encloses z d x+y` with no
ball name, the operands being points. *Proof:* the model of `ball_add_2` with $r_x = r_y = 0$
*is* this listing: there $s = \mathrm{RN}(0 + 0) = 0$ and $t = \mathrm{RN}(a_z E + 0)$, which is
the definition of `prod`. For the product, $p$, $q$ and $w$ are roundings of zero. So the
statement is `ball_add_2_correct` and `ball_mul_2_correct` (`Ball2.v`) after two rewritings.
*Checked:* `directed_2.py` compares the three outputs with those of the ball kernels, bit for
bit, on every case it runs. *Smallest precision:* 3 and 4. *Risk: low.*

Then the bound itself:

```
add_down_2_2(x, y) -> l                        add_up_2_2(x, y) -> h
  (z0, z1, d) = add_ball_2_2(x0, x1, y0, y1)     (z0, z1, d) = add_ball_2_2(x0, x1, y0, y1)
  w           = sub_down_1(z1, d)                w           = add_up_1(z1, d)
  (l0, l1)    = two_sum_ord(z0, w)               (h0, h1)    = two_sum_ord(z0, w)

mul_dir_2_2(x, y) -> (l, h)                    sub_down_2_2(x, y), sub_up_2_2(x, y):
  (z0, z1, d) = mul_ball_2_2(x0, x1, y0, y1)     neg_2(y), then the sum
  wl          = sub_down_1(z1, d)
  wu          = add_up_1(z1, d)
  (l0, l1)    = two_sum_ord(z0, wl)
  (h0, h1)    = two_sum_ord(z0, wu)
```

**Statement, in the real model**, for normalized $x$ and $y$, with $v$ the exact $x + y$ or
$xy$; from $p = 3$ for the sums and $p = 4$ for the product.

- $l$ and $h$ are normalized.
- $l \le v \le h$.
- Tightness, in the values of the kernel:
  $v - l \le 2d + \max\bigl(\eta,\ 2u\,(u\lvert z_0\rvert + d)\bigr)$, and the same for $h - v$.
- Tightness, in the exact value (the `outward` claim): $v - l \le A\lvert v\rvert + B$ and
  $h - v \le A\lvert v\rvert + B$, with

$$A = \frac{\bigl(2(1+u)^3\,G\,E + 2u^2\bigr)(1 + \mathrm{rel})}{1 - u}, \qquad
B = 2(1+u)^2\bigl(\tfrac12 G\eta + H\bigr) + \eta + \frac{2(1+u)^3\,G\,E + 2u^2}{1 - u}\,\mathrm{tiny},$$

  where $\mathrm{rel}$ and $\mathrm{tiny}$ are the two constants of the center kernel's bound
  ($\tfrac{3u^2}{1-4u}$ and $0$; $4u^2$ and $\tfrac32\eta$).

**The tightness constant.** With $c$ the constant of the center's kernel (3 and 4), $E$ is about
$c\,u^2$ and $G$ about 1, so $A$ is about $(2c + 2)u^2$: the bound is moved by $d$, which is
about $c\,u^2\lvert v\rvert$, from a result that is itself up to $d$ off, and the directed
rounding of the second limb adds at most its gap, $2u \cdot u\lvert v\rvert$. Computed exactly
(`constants.py`):

| | $A$, `double` | $B$, `double` | $A$, `float` | $B$, `float` |
|---|---|---|---|---|
| sum, difference | $8.000000000000009\,u^2$ | $2.000000000000002\,N \approx 2^{-1021}$ | $8.0000049\,u^2$ | $\approx 2^{-125}$ |
| product | $10.000000000000012\,u^2$ | $2.000000000000003\,N \approx 2^{-1021}$ | $10.0000068\,u^2$ | $\approx 2^{-125}$ |

So the width constant is $2c + 2$, below the $2c + 3$ that Phase 0 set as a target
([Operations](phase0/operations.md#interval)). The absolute term is twice the smallest normal
number: it is the $N$ that Milestone 1 put into $H$ so that a radius is never subnormal. In a
format of few bits the constants are far from these: $E$ and $G$ are expressions rounded up, and
at four bits $A$ is $16.8\,u^2$ for the sum. Measured away from the underflow range
(`directed_2.py`): the largest $(v - l)/(u^2\lvert v\rvert)$ was 8.54 at four bits and 6.81 at
five for the sum (where $A/u^2$ is 16.8 and 11.3), 9.78 and 8.38 for the product (19.7 and
14.1); over 2.0 million cases, no gap exceeded 0.65 of the bound in the kernel's values, nor
0.61 of the closed form.

*Proof.* $\lvert z - v\rvert \le d$ is the statement of `add_ball_2_2`. `sub_down_1` gives
$w = \mathrm{RD}(z_1 - d)$, so $z_0 + w \le z_0 + z_1 - d \le v$. `two_sum_ord` loses nothing:
$l = z_0 + w$ exactly, and its result is normalized. For the tightness,
$v - l = (v - z) + (z_1 - w)$; the first part is at most $d$, and
$z_1 - w = d + (z_1 - d - w)$, where the last term is less than the gap of the format at
$z_1 - d$, at most $\max(\eta, 2u\lvert z_1 - d\rvert)$, and $\lvert z_1\rvert \le u\lvert
z_0\rvert$ (`normalized_2_tail_rel`). The closed form bounds $d$ from above by the same two
facts that Milestone 1 used from below: a rounding to nearest is at most $(1 + u)$ times its
argument plus $\tfrac12\eta$, and $\lvert z_0\rvert \le \lvert z\rvert/(1 - u)$. The
$\tfrac12\eta$ is counted for the inner rounding only: the outer one, of $tG + H$, is of a
number that is at least $H \ge N$, in the normal range, where a rounding loses nothing absolute;
this is what the displayed $B$ assumes. All of it is real arithmetic over lemmas that exist;
none of it depends on the format's constants being close to their expressions. *Risk: low* for
containment and normalization, **medium** for the closed form, which is the first *upper* bound
of a radius that Kairn proves.

### The renormalization, and why it is not Fast2Sum

The decision taken before this page was to end the listing with `Fast2Sum(z0, w)`. Its
requirement is $\lvert z_0\rvert \ge \lvert w\rvert$, and that fails when the leading limb is
small: then $z_1 = 0$ and $w = -d$, where $d \ge H > N$, so the requirement fails for
$z_0 = 0$ and for every $\lvert z_0\rvert$ up to about the smallest normal number. It failed in
1 839 of the 14 161 cases of the complete enumeration at three bits, and in thousands of cases
of every other run (`directed_2.py`).

Where it fails, `Fast2Sum` need not return the sum of its operands. At three bits of precision,
with $z_0 = -7\eta$, $z_1 = 0$ and $d = 8\eta$: $w = -8\eta$, and `Fast2Sum` computes
$s = \mathrm{RN}(-15\eta) = -16\eta$, then $\mathrm{RN}(s - z_0) = \mathrm{RN}(-9\eta) = -8\eta$,
then $e = w - (-8\eta) = 0$. The pair $(-16\eta, 0)$ is not $z_0 + w = -15\eta$: the bound is no
longer "the kernel's result moved by $d$", and the tightness statement is lost. 112 cases of
that enumeration are of this kind. In all of them the pair was on the safe side of $z_0 + w$,
so the bound was still a bound; nothing says that it must be. From four bits on no such case
was found, in 426 000 cases where the requirement fails; but the proved lemma does not apply to
them, and a proof for them would be a new theorem about `Fast2Sum` with a weaker hypothesis.

`two_sum_ord` costs two sign operations, a comparison and two selects more, has the proved
`Fast2Sum` inside with its requirement established by the selects, and keeps the property that
makes it preferable to `TwoSum` in the IEEE model: its error term is finite whenever its sum is.

### Two limbs

```
interval_add_2(xl, xu, yl, yu) -> (zl, zu)
  (l0, l1) = add_down_2_2(xl0, xl1, yl0, yl1)      the finite cores
  (h0, h1) = add_up_2_2(xu0, xu1, yu0, yu1)
  al  = abs(l0);  fl = lt(al, const inf)           the lower bound is finite
  ah  = abs(h0);  fh = lt(ah, const inf)
  mi  = neg(const inf)
  a0  = select(fl, l0, mi)                         otherwise -inf, which is always a bound
  a1  = select(fl, l1, 0)
  b0  = select(fh, h0, const inf)
  b1  = select(fh, h1, 0)
  nx  = lt(xl0, const inf);  ny = lt(yl0, const inf);  ne = and(nx, ny)
  zl0 = select(ne, a0, const inf)                  an empty operand gives the empty set
  zl1 = select(ne, a1, 0)
  zu0 = select(ne, b0, mi)
  zu1 = select(ne, b1, 0)
```

`interval_sub_2` is the same on `sub_down_2_2(xl, yu)` and `sub_up_2_2(xu, yl)`, and
`interval_neg_2` is `neg_2` of each bound, exchanged. A bound that the finite core does not
return as a finite number becomes the infinity on its side. That covers two situations with one
rule: an operand that is unbounded on that side, where the infinite bound is the exact one, and
an overflow inside the core on bounded operands, where it is a valid bound and no more.

The product needs more, because an infinite bound times a finite one is an infinity of a
definite sign, which the finite core does not compute, and because of $0 \cdot \infty$:

```
mul_ext_2_2(x, y) -> (l, h)          x, y canonical, not NaN
  (c0, c1, e0, e1) = mul_dir_2_2(x0, x1, y0, y1)
  t   = prod(x0, y0)                 the infinite product, with its sign, when an operand is infinite
  ax  = abs(x0);  fx = lt(ax, const inf)
  ay  = abs(y0);  fy = lt(ay, const inf);  fo = and(fx, fy)        both operands are finite
  zx  = eq(x0, 0);  zy = eq(y0, 0);  zz = or(zx, zy);  nz = not(zz)
  ac  = abs(c0);  fc = lt(ac, const inf)
  ae  = abs(e0);  fe = lt(ae, const inf)
  mi  = neg(const inf)
  p0  = select(fc, c0, mi);         p1 = select(fc, c1, 0)         finite operands
  q0  = select(fe, e0, const inf);  q1 = select(fe, e1, 0)
  r0  = select(fo, p0, t);          r1 = select(fo, p1, 0)         an infinite operand
  s0  = select(fo, q0, t);          s1 = select(fo, q1, 0)
  l0  = select(nz, r0, 0);          l1 = select(nz, r1, 0)         a zero operand
  h0  = select(nz, s0, 0);          h1 = select(nz, s1, 0)

interval_mul_2: four calls of mul_ext_2_2 on the pairs of bounds, as interval_mul_1; the least of
  the four lower values and the greatest of the four upper ones by lt_2_2 and two selects each;
  then the empty set as in interval_add_2
```

*Statement of `mul_ext_2_2`, IEEE model, for canonical $x$, $y$ that are not NaN:* $l$ and $h$
are canonical and not NaN, and $l \le x \cdot y \le h$ as extended real numbers with
$0 \cdot \infty = 0$. A zero operand gives $l = h = 0$; otherwise an infinite operand gives
$l = h$, the infinity of the product's sign; otherwise the statement of `mul_dir_2_2` when its
results are finite.

**Statement of the interval kernels of two limbs, IEEE model, canonical operands.**

- I1, I2, I3.
- **I4.** For bounded operands and a bounded result, with $[lo, hi]$ the exact range:
  $lo - z_\ell \le A\lvert lo\rvert + B$ and $z_u - hi \le A\lvert hi\rvert + B$, with the $A$
  and $B$ of the operation. For the product this uses that $v \mapsto v - A\lvert v\rvert - B$
  does not decrease, since $A < 1$: the least of four values each close to its product is close
  to the least product. An infinite bound of the exact range is returned as that infinity.
- **I5.** For bounded operands, $Z$ is bounded when no member of the exact range exceeds
  $2^{e_{\max}-2}$ in magnitude, a quarter of the overflow threshold.

*Checked:* `interval_2.py`, 12 000 to 39 000 pairs of nonempty intervals per operation and
format at three, four and five bits, a third of them with an unbounded operand. Measured there, not
claimed: the first unbounded result of bounded operands appeared at 0.62, 0.58 and 0.97 of the
threshold for the sum (the 0.55 to 0.62 that
[Milestone 1](milestone1.md#what-is-proved-about-an-arithmetic-kernel) measured for `add_2_2`),
and at 0.92 and 0.98 for the product.

*Proof.* If a bound of the result is finite, the leading limb returned by its core is finite;
every value of the core reaches that limb through additions, products and fused operations,
except inside `sub_down_1` and `two_sum_ord`, whose IEEE-model statements say that a finite
result has finite operands here ($d$ is nonnegative or $+\infty$, and $z_1 - \infty$ is not
finite). So $z_0$ and $d$ are finite, the bridge of `add_2_2` or `mul_2_2` applies, and the
real-model statement of the core holds: this is the argument of
[B3](milestone1.md#ball-kernels) for a ball. A bound that is not finite is replaced by the
infinity on its side. I5 is statement 3 of the center's kernel and a bound on the outward move,
as in [B4](milestone1.md#when-the-result-is-a-finite-ball). I3 for the product is the lemma of
one limb.

*Smallest precision:* 3 for the sum and the difference, 4 for the product. *Risk:* medium for
the sum, **high** for the product: it is the largest listing of the milestone (96 rounded
operations, 8 steps and 258 comparisons, selects and sign operations after inlining), and its
IEEE-model proof multiplies the cases of `mul_ext_2_2` by four.

*Not claimed.*

- That an exact result gives a degenerate interval. The outward move does not know that the
  center's kernel made no error: $[1, 1] + [1, 1]$ is not $[2, 2]$ but an interval of width
  $2d$ around 2. In particular $[0, 0] + [0, 0]$ is $[-H, H]$, with $H = N + 2\eta$; the
  product $[0, 0] \cdot X$ is exactly $[0, 0]$, by the rule of the zero operand. `interval_2.py`
  counts both. Making the sum of exact zeros exact is two lines and is
  [question 2](#open-questions).
- A finite bound at an overflow. With bounded operands whose sum or product overflows, the
  result is the whole line, where `Interval<T, 1>` returns $[\Omega, +\infty]$. Keeping the sign
  there needs a constant of the top of the range in the IR ([question 3](#open-questions)).
- That the cost is acceptable for anything but a comparison with `Ball`: a sum is 56 rounded
  operations where `ball_add_2` is 23. `Ball` is the cheap enclosure from two limbs on, as
  Phase 0 said.

## One enclosure interface

`Interval<T, k>` and `Ball<T, k>` answer the same questions, so that an algorithm can be written
once and run on either. Every answer is safe: a bound is on the right side, a set returned
contains what it should, and a predicate that says yes is right. For an `Interval`, and for a
`Ball` of one limb short of an overflow, the predicates are also exact; for a `Ball` of two
limbs they are safe and
can decline to answer very close to the boundary, because an exact answer would need the sum of
five limbs.

Kernels of this section are compositions of comparisons, selects and the kernels above. Their
names are `interval_NAME_k` and `ball_NAME_k`; the listings of the short ones are in the table.

| Function | `Interval<T, 1>` | `Interval<T, 2>` | `Ball<T, 1>` | `Ball<T, 2>` |
|---|---|---|---|---|
| `lower()`, `upper()`, k-numbers | the stored bounds | the stored bounds | the bounds of `ball_to_interval_1`: $\mathrm{RD}(c - r)$, $\mathrm{RU}(c + r)$ | the bounds of `ball_to_interval_2`: within $A\lvert v\rvert + B$ of $c \mp r$ |
| `lower_as<T>()`, `upper_as<T>()` | the stored bounds | `to_down_2`, `to_up_2`: the exact roundings | as `lower`, `upper` | `sub_down_1(to_down_2(c), r)`, `add_up_1(to_up_2(c), r)`: a bound, less than one gap of `T` at $c$ plus one at the result from $c \mp r$ |
| `midpoint()` | `interval_mid_rad_1` | `interval_mid_rad_2` | the center | the center |
| `radius()`, a `T` | `interval_mid_rad_1`: the smallest radius of `T` for that midpoint | `interval_mid_rad_2`: a radius for that midpoint | the radius | the radius |
| `contains(t)`, $t$ a `T` or a k-number | `le(xl, t)`, `le(t, xu)`, $t$ finite: exact | the same with `le_2_1`, `le_1_2`, `le_2_2`: exact | $\lvert t - c\rvert \le r$ by exact pairs: exact | certain |
| `contains(Y)`, $Y \subseteq X$ | `le(xl, yl)` and `le(yu, xu)`: exact | the same: exact | $\lvert c_y - c_x\rvert \le r_x - r_y$ by exact pairs: exact | certain |
| `certainly_positive()`, `certainly_negative()` | $0 < x_\ell < +\infty$; $-\infty < x_u < 0$ | the same on the leading limbs | `lt(r, c)`; `lt(c, neg(r))`: exact | `lt_1_2(r, c)`; `lt_2_1(c, neg(r))`: exact |
| `certainly_zero()` | $x_\ell = x_u = 0$ | the same | $c = 0$ and $r = 0$ | the same |
| `hull(Y)` | the smaller lower bound, the larger upper bound: exact | the same with `lt_2_2`: exact | `ball_hull_1`: contains both | `ball_hull_2` |
| `intersection(Y)` | the larger lower bound, the smaller upper bound, empty if they cross: exact | the same: exact | `ball_intersection_1`: contains $X \cap Y$ | `ball_intersection_2` |
| `split()` | $[x_\ell, m]$, $[m, x_u]$, $m$ the midpoint: their union is $X$ | the same | `ball_split_1`: two balls that cover $X$ | `ball_split_2` |
| `is_empty()`, `is_entire()` | $x_\ell = +\infty$; $x_\ell = -\infty$ and $x_u = +\infty$ | the same on the leading limbs | $r$ is a NaN; $r = +\infty$ | the same |
| to the other type | `interval_to_ball_1` | `interval_to_ball_2` | `ball_to_interval_1` | `ball_to_interval_2` |

The expressions in the two `Ball` columns are for finite balls. A kernel of a `Ball` first
selects the two special states, by the tests of `is_empty` and `is_entire`, to the values of
[the table below](#the-empty-set-and-the-whole-line): on its own `sub_down_1(c, r)` is a NaN
for the empty ball, and $r_x - r_y$ is a NaN for two whole lines. For an `Interval` the
comparisons of the stored bounds already give those values for `contains`, the hull and the
intersection, the empty set included; the signs and the three-valued comparisons add the test
of emptiness that their conditions show; `midpoint`, `radius` and `split` select the special
values, as the listing of `interval_mid_rad_1` does.

**Exact pairs.** For a ball of one limb the bounds $c \pm r$ are not numbers of `T`, but the
difference of two numbers of `T` is an exact normalized pair, by `two_sum_ord`, and pairs are
compared exactly by the kernels of Milestone 1. So $\lvert t - c\rvert \le r$ is
`le_2_1(abs_2(two_sum_ord(t, neg(c))), r)`, and $Y \subseteq X$ is
`le_2_2(abs_2(two_sum_ord(cy, neg(cx))), two_sum_ord(rx, neg(ry)))`. A difference that
overflows gives a false answer, which is then the right one: a distance beyond $\Omega$ exceeds
every radius. *Checked:* `enclosure_1.py`, every ball and every point of four formats, and
36 000 to 48 000 pairs of balls per format.

**Certain.** For a ball of two limbs, with $(z, e)$ = `add_ball_2_2(t, neg_2(c))`, so that
$\lvert (t - c) - z\rvert \le e$:

```
ball_contains_point_2(c, r, t) -> (yes, no)
  (z0, z1, e) = add_ball_2_2(t0, t1, neg(c0), neg(c1))
  hi  = radd(abs_upper_2(z0, z1), e)                 >= |t - c|
  lo  = sub_down_1(to_down_2(abs_2(z0, z1)), e)      <= |t - c|
  yes = le(hi, r)
  no  = lt(r, lo)
```

*Statement (`trit`):* `yes` implies $\lvert t - c\rvert \le r$, `no` implies
$\lvert t - c\rvert > r$, and they are never both true. `contains` returns `yes`. *Checked:*
`enclosure_2.py`: of 40 000 tests per format, 3 to 17% were undecided, in formats of three to
five bits where $e$ is large; with $e \approx 3u^2\lvert t - c\rvert + 2^{-1022}$ in `double`
the undecided band is that thin. *Not claimed:* an exact answer. It needs the sign of a sum of
five limbs, which is arithmetic of more than two limbs ([question 8](#open-questions)).

### Midpoint, radius and the conversions

```
interval_mid_rad_1(xl, xu) -> (m, r)
  om = pred(const inf);  mo = neg(om)                the largest finite number, and its opposite
  ml = lt(xl, mo);  l = select(ml, mo, xl)           the bounds, brought into [-Omega, Omega]
  mu = lt(om, xu);  h = select(mu, om, xu)
  hl = prod(l, const 1/2);  hu = prod(h, const 1/2)
  ma = add(hl, hu)
  ca = lt(ma, l);  mb = select(ca, l, ma)            moved into [l, h] if a halving underflowed
  cb = lt(h, mb);  mc = select(cb, h, mb)
  ra = sub_up_1(mc, l);  rb = sub_up_1(h, mc)
  rm = lt(ra, rb);  rc = select(rm, rb, ra)
  md = select(ml, mo, mc);  me = select(mu, om, md)  a half-line: the largest number of its sign
  bo = and(ml, mu);  mf = select(bo, 0, me)          the whole line: 0
  un = or(ml, mu);   rd = select(un, const inf, rc)
  ne = lt(xl, const inf)
  m  = select(ne, mf, const nan)
  r  = select(ne, rd, const nan)
```

*Statement, IEEE model, canonical $X$.* If $X = [\ell, h]$ is bounded: $\ell \le m \le h$;
$\lvert m - \tfrac{\ell + h}{2}\rvert \le u\,\lvert\tfrac{\ell + h}{2}\rvert + \eta$; and $r$ is
the smallest number of `T` with $[m - r, m + r] \supseteq X$. The whole line gives $(0, +\infty)$;
$[\ell, +\infty]$ gives $(\Omega, +\infty)$ and $[-\infty, h]$ gives $(-\Omega, +\infty)$; the
empty set gives two NaN. These are the values of `mid` and `rad` in IEEE 1788, as its public
test cases have them ([IEEE 1788](#ieee-1788)). The move into $[\ell, h]$ is not decoration:
for $[\eta, \eta]$ both halvings round to zero and the sum of the halves is $0$, outside the
interval. *Checked:* `enclosure_1.py`, every canonical interval of five formats. *Risk: low.*

For two limbs the same steps use kernels of two limbs: the halves by `mul_pow2_2`, their sum by
`add_2_2`, the moves into $[\ell, h]$ by `lt_2_2`, and each side of the radius by
`radd(to_up_2(z), e)` with $(z, e)$ = `add_ball_2_2` of the difference, which is nonnegative
because the bound of `add_2_2` is relative. *Statement:* $\ell \le m \le h$, $m$ normalized,
$\lvert m - \tfrac{\ell+h}{2}\rvert \le \tfrac{3u^2}{1-4u}\lvert\tfrac{\ell+h}{2}\rvert + 2\eta$,
and $[m - r, m + r] \supseteq X$; the smallest radius is not claimed. *Checked:*
`enclosure_2.py`. *Risk: medium* (a long listing; every step has its lemma).

**Interval to ball.** `interval_to_ball_k` is `interval_mid_rad_k` followed by two selects: an
unbounded interval becomes the whole line, whose center is 0 and not the $\pm\Omega$ of a
half-line; the empty set becomes the empty ball. *Statement:* the ball is canonical and contains
the interval; it is empty exactly when the interval is.

**Ball to interval.**

```
ball_to_interval_1(c, r) -> (zl, zu)             ball_to_interval_2(c, r) -> (zl, zu)
  l  = sub_down_1(c, r)                            nr       = neg(r)
  h  = add_up_1(c, r)                              (l0, l1) = add_down_2_2(c0, c1, nr, 0)
  ne = eq(r, r)            not the empty ball      (h0, h1) = add_up_2_2(c0, c1, r, 0)
  mi = neg(const inf)                              then the selects of interval_add_2, with
  zl = select(ne, l, const inf)                    ne = eq(r, r)
  zu = select(ne, h, mi)
```

*Statement:* the interval is canonical and contains the ball; it is empty exactly when the ball
is; the whole line gives $[-\infty, +\infty]$ (by the same operations: $0 - \infty$ rounded down
is $-\infty$). For one limb it is the *smallest* interval of `T` that contains the ball. For two
limbs each bound is within $A\lvert v\rvert + B$ of $c \mp r$, the constants of the sum.
*Checked:* `enclosure_1.py`, `enclosure_2.py`. *Risk: low.*

**A ball from an interval of two `T`.** A program that holds an interval of `double` can make a
ball of two limbs whose center is the exact midpoint: the sum of two numbers of `T` is an exact
pair.

```
ball_from_interval_2(lo, hi) -> (cw, rw)
  gl = guard(lo);  gu = guard(hi)                    values from the program (rule R3)
  hl = prod(gl, const 1/2);  hu = prod(gu, const 1/2)
  (c0, c1) = two_sum_ord(hl, hu)                     the exact sum of the halves
  d  = sub_up_1(hu, hl)                              RU(hi/2 - lo/2)
  bl = add(hl, hl);  bu = add(hu, hu)
  xl = eq(bl, gl);   xu = eq(bu, gu);  xx = and(xl, xu)     both halvings were exact
  da = add(d, const eta);  dn = succ(da)
  r  = select(xx, d, dn)
  ok = le(gl, gu);  nl = lt(gl, const inf);  mi = neg(const inf);  nu = lt(mi, gu)
  va = and(ok, nl);  v = and(va, nu)                 the pair describes an interval
  fl = lt(mi, gl);  fu = lt(gu, const inf);  f = and(fl, fu)     and a bounded one
  k0 = select(f, c0, 0);  k1 = select(f, c1, 0);  s = select(f, r, const inf)
  cw0 = select(v, k0, const nan);  cw1 = select(v, k1, const nan);  rw = select(v, s, const nan)
```

*Statement, IEEE model, any two values of `T`.* The result is a canonical ball.

- If $lo \le hi$ and both are finite: it contains $[lo, hi]$. When neither bound is an odd
  multiple of $\eta$ below $2N$ (so that halving is exact), the center is $\tfrac{lo + hi}{2}$
  exactly and the radius is $\mathrm{RU}\bigl(\tfrac{hi - lo}{2}\bigr)$, the smallest of `T` for
  that center. Otherwise the center is within $\eta$ of the midpoint and the radius is the
  number after $\mathrm{RN}(d + \eta)$, with $d$ the difference of the two rounded halves,
  rounded up. Halving first is what keeps $[\Omega, \Omega]$ from overflowing; the price is at
  the other end of the range.
- If $lo \le hi$ and a bound is infinite ($[-\infty, hi]$, $[lo, +\infty]$, $[-\infty, +\infty]$):
  the whole line. A ball cannot be a half-line.
- Otherwise, that is $lo > hi$, a NaN bound, $lo = +\infty$ or $hi = -\infty$: the empty set, as
  `Interval(lo, hi)` gives; the two routes agree. [Question 1](#open-questions) applies to both.

*Checked:* `enclosure_1.py`, every pair of values of five formats, NaN and infinities included.
*Proof:* `two_sum_ord`; `sub_up_1`; a halving is exact exactly when doubling it back gives the
operand, and is off by at most $\tfrac12\eta$ otherwise. *Risk: low.* `Ball<T, 1>` from two `T`
is `interval_make_1` followed by `interval_to_ball_1`.

### Hull, intersection and split of balls

- `ball_hull_k(X, Y)`: both balls to intervals, the hull of the intervals, back to a ball. If an
  operand is empty the other is returned as it is. *Statement:* the result is canonical and
  contains $X \cup Y$. Not claimed: the smallest such ball.
- `ball_intersection_k(X, Y)`: both to intervals, the intersection, back to a ball. If an operand
  is the whole line the other is returned as it is; if one is empty, the empty set.
  *Statement:* the result is canonical and contains $X \cap Y$; it is empty only if
  $X \cap Y$ is. Not claimed: that it is inside $X$ or $Y$ (the two outward conversions can
  make it stick out by a rounding), nor that it is empty whenever the balls are disjoint.
- `ball_split_k(X)`: two balls, the first containing $[c - r, c]$ and the second $[c, c + r]$.

```
ball_split_1(c, r) -> (ca, ra, cb, rb)
  h  = prod(r, const 1/2)
  g  = sub(r, h)                                   exact
  mg = lt(h, g);  q = select(mg, g, h)             max(h, r - h)
  fr = lt(r, const inf)                            a finite ball
  hs = select(fr, h, 0);  ws = select(fr, q, 0);  cs = select(fr, c, 0)
  nh = neg(hs)
  (a0, a1) = ball_add_1_full(cs, 0, nh, ws)        the point c plus the ball (-h, q)
  (b0, b1) = ball_add_1_full(cs, 0, hs, ws)
  ca = select(fr, a0, c);  ra = select(fr, a1, r)  the whole line and the empty set: twice, as they are
  cb = select(fr, b0, c);  rb = select(fr, b1, r)
```

*Statement:* four canonical values; for a finite ball, $[c - r, c] \subseteq (c_a, r_a)$ and
$[c, c + r] \subseteq (c_b, r_b)$; the whole line gives the whole line twice (a ball cannot be a
half-line, so splitting it makes no progress), the empty set the empty set twice. *Proof:* the
containment of `ball_add_k_full`, which is proved: the point $c$ plus the ball of center $-h$
and radius $q \ge \max(h, r - h)$ contains $[c - r, c]$. *Not claimed:* that the halves are
inside $X$, nor that their radii are close to $r/2$ when $r$ is near the underflow range: each
has the $H \approx N$ of a ball sum. *Checked:* `enclosure_1.py`.

### The empty set and the whole line

A program that has one special state, the whole space, and no empty set, has to map Kairn's
empty set to its own convention before a test. This is what every function of the interface
returns on the two special values, for `Interval` and for `Ball` alike unless said.

| Function | On the empty set | On the whole line |
|---|---|---|
| `lower()`, `upper()`, `lower_as`, `upper_as` | $+\infty$, $-\infty$ | $-\infty$, $+\infty$ |
| `midpoint()` | a NaN | $0$ |
| `radius()` | a NaN | $+\infty$ |
| `contains(t)` | false | true for a finite $t$; false for $t = \pm\infty$ or a NaN |
| `contains(Y)` | true exactly when $Y$ is empty | true |
| $Y$`.contains(X)` for this $X$ | true | true exactly when $Y$ is the whole line |
| `certainly_positive()`, `certainly_negative()`, `certainly_zero()` | false | false |
| `hull(Y)` | $Y$ | the whole line |
| `intersection(Y)` | the empty set | $Y$ |
| `split()` | the empty set, twice | `Interval`: $[-\infty, 0]$ and $[0, +\infty]$. `Ball`: the whole line, twice |
| `is_empty()`, `is_entire()` | true, false | false, true |
| the conversion to the other type | the empty set | the whole line |
| the three-valued comparisons | unknown | unknown |

Three choices in this table are conventions, not consequences. `certainly_positive` is false on
the empty set although "every member is positive" is vacuously true: a query about nothing
answers no, and `is_empty` is the query to make first. The three-valued comparisons answer
*unknown* for the same reason. And the relations of IEEE 1788, [below](#comparisons), keep the
standard's conventions, which are the vacuous ones. For a half-line $[\ell, +\infty]$, which
only an `Interval` can be: `midpoint` is $\Omega$, `radius` is $+\infty$, `split` gives
$[\ell, \Omega]$ and $[\Omega, +\infty]$, and the conversion to a ball gives the whole line.

### Comparisons

`less(X, Y)` and its five siblings return a `Trit`: *yes* when the relation holds for every
member of $X$ and every member of $Y$, *no* when it fails for every pair, *unknown* otherwise.
A kernel returns two masks.

| | yes | no |
|---|---|---|
| `less(X, Y)` | $x_u < y_\ell$ | $x_\ell \ge y_u$ |
| `less_equal(X, Y)` | $x_u \le y_\ell$ | $x_\ell > y_u$ |
| `greater`, `greater_equal` | those of $(Y, X)$ | |
| `equal(X, Y)` | $x_\ell = x_u = y_\ell = y_u$ | $x_u < y_\ell$ or $y_u < x_\ell$ |
| `not_equal(X, Y)` | the *no* of `equal` | the *yes* of `equal` |

Both masks are false when an operand is empty. *Statement (`trit`).* For intervals the masks are
exactly these comparisons of bounds, which are exact for one and two limbs
([Milestone 1](milestone1.md#second-wave-kernels)), so *unknown* is returned exactly when
neither holds. For a `Ball<T, 1>` the bounds are $c \pm r$ and the comparisons are made on exact
pairs: $x_u < y_\ell$ is $r_x + r_y < c_y - c_x$, that is
`lt_2_2(two_sum_ord(rx, ry), two_sum_ord(cy, neg(cx)))`. A comparison that is not strict (the
*no* of `less`, the *yes* of `less_equal`) is `le_2_2` on such pairs *and* a test that the sum
of the radii is finite: two sums that overflow are both the pair $(+\infty, -\infty)$, which
`le_2_2` calls equal, and without the test the mask is wrong (79 of the 36 100 pairs of balls
of the smallest format of `enclosure_1.py`). With the test, *yes* and *no* are always right,
and they are exact unless the sum of the radii and the difference of the centers both overflow;
then the answer is *unknown* (0 to 196 of the 36 000 to 48 000 pairs of a format). For a
`Ball<T, 2>` they are certain, with the difference of the centers by `add_ball_2_2`, bounded
below and above as in `ball_contains_point_2`, and the sum of the radii by `radd`.

**The relations of IEEE 1788** are separate functions on `Interval` that return `bool`, with the
standard's conventions for the empty set: `equal`, `subset`, `less`, `precedes`, `interior`,
`strict_less`, `strict_precedes`, `disjoint`. Two of these names are also those of three-valued
comparisons with another meaning (the standard's `less` is "every member of $X$ is at most some
member of $Y$, and every member of $Y$ at least some member of $X$"), so the relations live in
a namespace of their own, `kairn::rel`. Each is a few comparisons of bounds and, where the
storage of the empty set as $(+\infty, -\infty)$ does not already give the standard's answer
(`interior`, `strict_less`, `strict_precedes`, `disjoint`), a test of emptiness. They are exact.
With $e_x$ for "$X$ is empty":

| Relation | On the stored bounds |
|---|---|
| `equal(X, Y)` | $x_\ell = y_\ell$ and $x_u = y_u$ |
| `subset(X, Y)` | $y_\ell \le x_\ell$ and $x_u \le y_u$ |
| `less(X, Y)` | $x_\ell \le y_\ell$ and $x_u \le y_u$ |
| `precedes(X, Y)` | $x_u \le y_\ell$ |
| `interior(X, Y)` | $e_x$, or ($y_\ell < x_\ell$ or $y_\ell = x_\ell = -\infty$) and ($x_u < y_u$ or $x_u = y_u = +\infty$) |
| `strict_less(X, Y)` | $e_x$ and $e_y$, or neither and ($x_\ell < y_\ell$ or $x_\ell = y_\ell = -\infty$) and ($x_u < y_u$ or $x_u = y_u = +\infty$) |
| `strict_precedes(X, Y)` | $e_x$, or $e_y$, or $x_u < y_\ell$ |
| `disjoint(X, Y)` | $e_x$, or $e_y$, or $x_u < y_\ell$, or $y_u < x_\ell$ |

The first four need no test of emptiness: with the empty set stored as $(+\infty, -\infty)$ the
comparisons already give the standard's answers (two empty sets are `equal` and `less`; the
empty set is a `subset` of everything and `precedes` everything). `equal`, `subset`, `interior`
and `disjoint` are the four relations of IEEE Std 1788.1-2017, and the rows above agree with its
Tables 4.5 and 4.6 entry by entry, the empty operands included. `less`, `precedes`,
`strict_less` and `strict_precedes` are relations of the full standard, IEEE Std 1788-2015,
which the simplified one does not require; their rows are those of the drafts as I read them,
they agree with the public test cases quoted in [IEEE 1788](#ieee-1788), and they are to be
checked against all of those cases before they ship. The relations are not provided for `Ball`,
which has `contains`, the three-valued comparisons, and the conversion to an interval.

*Smallest precision of this section:* that of the kernels composed, at most 4. *IEEE model:*
every kernel of the interface is of the extended domain. *Risk:* low for `Interval` (comparisons
and selects), medium for `Ball<T, 2>` (many compositions, each to be stated).

## Scaling a ball by a power of two

`ldexp(X, n)` and `half(X)` on a `Ball` multiply every member by $2^n$. When nothing underflows
the result is exact: the center is scaled exactly, the radius is scaled exactly, and nothing is
added. An algorithm that halves a ball many times and counts on the halving being free of error,
such as a subdivision that defers its halvings, can rely on that. Near the underflow range the
ball stays a valid enclosure and the radius grows by what was lost.

```
ball_mul_pow2_2(cx, rx, c) -> (cz, rz)               c a positive power of two
  h          = prod(cx0, c)
  l          = prod(cx1, c)
  (cz0, cz1) = fast_two_sum(h, l)                    the center, as mul_pow2_2
  rr         = prod(rx, c)
  ze         = eq(cx1, 0)
  m          = select(ze, h, l)                      the scaled last nonzero limb
  am         = abs(m)
  bc         = lt(const N, am)
  zc         = eq(cx0, 0)
  ec         = or(bc, zc)                            the center was scaled exactly
  br         = lt(const N, rr)
  zr         = eq(rx, 0)
  er         = or(br, zr)                            the radius was scaled exactly
  ex         = and(ec, er)
  su         = succ(rr)
  sw         = add(su, const eta)
  rw         = succ(sw)
  rz         = select(ex, rr, rw)
```

`ball_mul_pow2_1` is the same with one product for the center. `const N` is
`const up(eta/(2*u))`.

**Statement, real model**, for a normalized $c_x$, $r_x \ge 0$ and $c$ a positive power of two
of the format; from $p = 2$.

- $c_z$ is normalized, and for every $x$ with $\lvert x - c_x\rvert \le r_x$:
  $\lvert c\,x - c_z\rvert \le r_z$.
- **Exact.** If the center is zero or its last nonzero limb times $c$ exceeds $N$ in magnitude,
  and the radius is zero or $c\,r_x$ exceeds $N$, then $c_z = c\,c_x$ and $r_z = c\,r_x$
  exactly: the result *is* $c\,X$. For `double`: `half(X)` is exact when the last nonzero limb
  of the center is above $2^{-1021}$ in magnitude and the radius is zero or above $2^{-1021}$.
- **Otherwise** $r_z$ is the number after $\mathrm{RN}(\mathrm{succ}(\mathrm{RN}(c\,r_x)) + \eta)$:
  at most two steps of the format above $\mathrm{RU}(c\,r_x + \eta)$. The $\eta$ is the bound of
  `mul_pow2_2` on what the center lost ([Milestone 1](milestone1.md#second-wave-kernels)); the
  first step covers a radius whose scaling was rounded.

**In the IEEE model**, `ball_mul_pow2_k_full` adds the fix-up of
[`ball_scale_k_full`](milestone1.md#ball-kernels): B1 to B4, with the whole line when the scaled
center or radius overflows, and a finite ball when $(\lvert c_x\rvert + r_x)\,c \le
2^{e_{\max}-2}$. `ldexp(X, n)` for a $2^n$ that is not a number of `T` calls the kernel two or
three times, as for a number
([Milestone 1](milestone1.md#scaling-beyond-the-powers-of-two-of-the-format)). For a ball the
composition needs no argument of its own: containment of each step gives containment of the
whole, and exactness of each step exactness of the whole.

*Proof.* The exactness of `mul_pow2_2` under these conditions is `mul_pow2_2_exact`
(`MulPow2.v`), with one step added: a rounded product *above* $N$ comes from an exact product
above $N$ (`round_abs_le`), hence from an exact scaling. When the second limb is not zero its
scaling being above $N$ makes the first limb's so, by `normalized_2_tail_rel`. The other branch
is `mul_pow2_2_correct`'s $\eta$ and the two steps, by `up_above` (`Directed.v`). *Checked:*
`scaling.py`, every center, radius and power of two of four formats: containment always, and
exactness in every case the statement says. *Smallest precision:* 2. *Risk: low.*

*`constexpr`:* yes, by [the rule of the product](#the-two-executions-of-a-product): the only
fused operations are `prod`. The two executions give the same values; a zero limb of the center
can differ in sign.

*Not claimed:* exactness below the stated thresholds even where the scaling happens to be exact
(a center of $4\eta$ halved is exact, and the radius grows all the same); a negative power of
two as `c`.

**Consequence for `BallVector`.** `bv_mul_pow2_k` is the same kernel along the entries, with
`ec` true only when it is for every entry. A `BallVector` kernel whose operations are exact adds
nothing to the radius. The rule of Phase 0, "the radius of a `BallVector` kernel is at least
the entrywise `Ball` radius", is to be read with the `Ball` operation of the same kind, here
`ball_mul_pow2_k`, which adds nothing either.

## Batch kernels

A batch kernel applies a proved kernel along arrays: a sum, a dot product, $a\,x + y$, the
product of two polynomials. Its result is within a bound that depends on the number of terms,
and the library exports that bound as a function, so that a program can use it in its own
analysis. The bound holds for whatever order the additions are made in; that is what lets one
theorem cover the scalar loop and the SIMD loop.

These kernels work on plain arrays of k-numbers, one array per limb. `BallVector` is built on
them, and so can be a set of vectors that Kairn does not have: a program whose polynomial is a
ball with weights (scaled coefficients, integer scales, one radius on the unscaled values) calls
the kernels on its centers and applies its own radius theorem, with Kairn's bounds in it.

In this milestone a batch kernel is a loop of the finite cores of Milestone 1, with one
canonicalization at the end. Nothing in the loop is new arithmetic.

### Folds, the extension of the IR

The IR describes straight-line kernels. A loop is described by one more kind of description,
and nothing else changes:

```
fold:      dot_2
arrays:    x = x0 x1,  y = y0 y1          the arrays read, one array per limb
state:     s = s0 s1                      the accumulator; it starts at zero
step:      s = dot_step_2(s, x, y)        a straight-line kernel: the state and one element of each array
combine:   s = add_2_2(s, s)              a straight-line kernel: two states into one
orders:    sequential, lanes
writes:    (none)                         arrays written, one element per step, for a map
finish:    (none)                         a straight-line kernel on the final state
```

- **The step** is an ordinary kernel, with its own listing, model and theorem:
  `dot_step_2(s, x, y)` is `p = mul_2_2(x, y); s = add_2_2(s, p)`.
- **The orders** are the two that are emitted. *Sequential:* the state after element $i$ is the
  step applied to the state after element $i - 1$. *Lanes*, for a width $W$: the first
  $W\lfloor n/W\rfloor$ elements are dealt to $W$ lanes, element $i$ to lane $i \bmod W$; each
  lane is folded sequentially from the zero state; the lane states are combined from lane 0
  upward, $((s_0 \oplus s_1) \oplus s_2) \oplus \dots$; the remaining elements are folded
  sequentially into the result. $W$ is the number of lanes of the packed type: 4 and 8 for AVX2,
  2 and 4 for NEON.
- **In Rocq** the model is a recursive function over lists: the sequential fold is `fold_left`
  of the step's model, and the lane order is that function applied to the lists that a
  function `deal W` returns, followed by `fold_left` of the combination. The statement
  quantifies over the lists and over $W$.
- **In C++** the sequential order is a loop over the scalar step, and the lane order a loop over
  the packed step followed by the combination of the lanes and a scalar loop on the remainder.
  The step is inlined in the loop; the loop itself is an ordinary function
  ([Inlining and compile time](#inlining-and-compile-time)).
- **A map** (`axpy`, the centers of a `BallVector` sum) has `writes`: the step also returns one
  element of each written array. The generator checks that a written element is computed from
  the elements read and not from the state, so that it does not depend on the order; the state
  of a map carries flags and maxima only, whose combination (`and`, a maximum) is exact,
  associative and commutative.
- **The interpreter, the line protocol and the oracle** gain arrays: a request gives the
  length, then the limbs; the oracle computes exact sums and judges the bound of the fold as it
  judges an `error` entry.

- **Arrays that the program fills.** [Rule R3](../architecture.md#the-kernel-ir) does not stop
  at an array: a program may store products into an array and pass it to `sum` in the same
  function, and a compiler that inlines the loop and forwards the stores can fuse those
  products into the kernel's first addition. So an array is declared `stored` (a container
  whose elements were written through Kairn, hence by kernels or guarded constructors) or
  `supplied` (a view of the program's own arrays), and for a `supplied` array rule R3 applies
  to the step: a limb that the step *adds* passes through `guard` first. `dot`, `scale` and the
  `x` of `axpy` only multiply their elements and need none; `sum`, and the `y` of `axpy`, need
  one addition per limb. For one limb this is a real cost, and [question 19](#open-questions).

*What the generator enforces on a fold:* the step and the combination pass every rule of a
kernel (R1 to R3 among them); the types of the state agree; the zero state is a fixed point of
the combination's value (`0 + 0 = 0`). *Risk:* **medium to high**, and it is generator work, not
proof work: a second printer path for loops in scalar and packed code, and arrays in the
interpreter and in both test tiers.

### Summation over any tree

Whatever the order, a sum of $n$ numbers computed by additions that are each accurate to a
relative $\varepsilon$ is accurate to about $(n - 1)\varepsilon$ times the sum of the
magnitudes. This is Higham's bound for summation
([Higham](phase0/references.md#higham), section 4.2 and Lemma 3.1), which he notes holds for
every ordering; it is stated here over trees so that the instances are computations, not
separate proofs.

**Statement.** Let values have a real number $\mathrm{val}(a)$, a notion of *valid*, and an
addition $\oplus$ such that for valid $a$ and $b$ the sum $a \oplus b$ is valid and

$$\lvert\mathrm{val}(a \oplus b) - (\mathrm{val}\,a + \mathrm{val}\,b)\rvert \le
\varepsilon\,(\lvert\mathrm{val}\,a\rvert + \lvert\mathrm{val}\,b\rvert).$$

Let $t$ be a binary tree whose leaves are valid values $x_1, \dots, x_n$, each node being
$\oplus$ of its two subtrees, and let $h$ be its height, the largest number of additions
between a leaf and the root. Then

$$\Bigl\lvert\mathrm{val}(t) - \sum_i \mathrm{val}\,x_i\Bigr\rvert \le
\bigl((1 + \varepsilon)^h - 1\bigr)\sum_i\lvert\mathrm{val}\,x_i\rvert
\le \gamma_h(\varepsilon)\sum_i\lvert\mathrm{val}\,x_i\rvert ,
\qquad \gamma_m(\varepsilon) = \frac{m\,\varepsilon}{1 - m\,\varepsilon},$$

the second inequality when $h\,\varepsilon < 1$. Every tree with $n$ leaves has
$h \le n - 1$, so $\gamma_{n-1}(\varepsilon)$ serves for every order.

**What it needs of the addition** is the displayed inequality and nothing else: no order, no
tie rule, no statement about underflow. It asks for an error relative to the *operands*, which
is weaker than an error relative to the exact sum, since
$\lvert a + b\rvert \le \lvert a\rvert + \lvert b\rvert$; so it applies to the fast addition as
well.

| Addition | Valid | $\varepsilon$ | From |
|---|---|---|---|
| `add_1_1` | a number of the format | $\dfrac{u}{1+u}$ | `add_1_1_correct`, $p \ge 1$ |
| `add_2_2` | a normalized pair | $\dfrac{3u^2}{1-4u}$ | `add_2_2_correct`, $p \ge 3$ |
| `add_fast_2_2` | a normalized pair | $3u^2$ | `add_fast_2_2_correct`, $p \ge 2$; its bound is already in this form |

**The orders emitted.** A fold starts from the zero state, and `add_2_2` with a zero operand
returns the other operand exactly (a lemma by computation; checked on the normalized pairs of
three formats, all of them or 4 000). So the zero state is not a leaf, and the heights are
$n - 1$ for the sequential
order and $\lfloor n/W\rfloor + (W - 1) + (n \bmod W) - 1$ for the lane order when $n \ge W$,
which is at most $n - 1$.

*Proof.* By induction on the tree, in real numbers: with $S$ the sum of the magnitudes of the
leaves of a subtree, its error is at most $((1+\varepsilon)^h - 1)S$ and its value at most
$(1+\varepsilon)^h S$ in magnitude; a node adds $\varepsilon$ times the magnitudes of its two
computed operands. Then $(1+\varepsilon)^h \le 1/(1 - h\varepsilon)$ by induction on $h$.
Nothing floating-point is in it; the instances are the three theorems of the table.
*Checked:* `batch.py`, sequential, lane and random trees of 2 to 14 terms with cancellation, at
four to six bits: the largest error was 1.000 of the bound for one limb (the bound is attained)
and 0.21 to 0.28 for two limbs. *Risk: low.*

### sum, dot, axpy, convolution

| Fold | Reads | Step, per element | Combination | Returns | Bound |
|---|---|---|---|---|---|
| `sum_k` | $x$ | $s \leftarrow s \oplus x$ | $\oplus$ | a k-number | `sum(n)` |
| `dot_k` | $x$, $y$ | $s \leftarrow s \oplus (x \otimes y)$; for one limb, `s = fma(x, y, s)` | $\oplus$ | a k-number | `dot(n)` |
| `axpy_k` | $x$, $y$, and a scalar $a$ | $z \leftarrow (x \otimes a) \oplus y$ | flags | the array $z$ | `axpy` |
| `add_k`, `sub_k`, `scale_k`, `mul_pow2_k` | | the scalar operation | flags | an array | that of the operation |
| `conv_k` | $a$ of length $n_a$, $b$ of length $n_b$ | coefficient $j$ is the `dot` of the $a_i$ and $b_{j-i}$, in increasing $i$ | flags | $n_a + n_b - 1$ coefficients | `dot(min(n_a, n_b))`, per coefficient |
| `norm_upper_k` | $x$ | $m \leftarrow \max(m, \lvert x_0\rvert)$ | $\max$ | `succ(m)` for two limbs, $m$ for one | exact, [below](#ballvector) |

$\oplus$ and $\otimes$ are `add_2_2` and `mul_2_2` (the finite cores), `mul_2_1` when the scalar
of `axpy` or `scale` is a `T`, and the operations of `T` for one limb.

**Statement of `sum_k`.** If every $x_i$ is valid and the result is finite, the result is valid
(normalized, for two limbs) and
$\lvert s - \sum_i x_i\rvert \le \gamma_{n-1}(\varepsilon_+)\sum_i\lvert x_i\rvert$. There is no
underflow term.

**Statement of `dot_k`.** With $\varepsilon_\times$ and $\tau$ the two constants of the
product's bound ($4u^2$ and $\tfrac32\eta$ for `mul_2_2`) and $h \le n - 1$ the height of the
order:

$$\Bigl\lvert s - \sum_i x_i y_i\Bigr\rvert \le
\bigl((1 + \varepsilon_\times)(1 + \varepsilon_+)^h - 1\bigr)\sum_i\lvert x_i y_i\rvert
+ (1 + \varepsilon_+)^h\,n\,\tau .$$

Each product is off by $\varepsilon_\times\lvert x_i y_i\rvert + \tau$, and the additions that
follow scale every term, the underflow terms included, by at most $(1 + \varepsilon_+)^h$. With
$\varepsilon = \max(\varepsilon_\times, \varepsilon_+)$ the first factor is at most
$\gamma_n(\varepsilon)$, which is the form of [Operations](phase0/operations.md#batch-kernels).
For one limb the step is one fused operation: one rounding where two limbs have a product and
then a sum. A term then passes through as many roundings as with two limbs, so the same form
holds with the same $h$, with $\varepsilon_\times = \varepsilon_+ = \tfrac{u}{1+u}$ and
$\tau = \tfrac12\eta$, and `bound_dot_1` covers it.

**Statement of `axpy_k`**, per entry, from the two kernels composed:
$\lvert z_i - (a x_i + y_i)\rvert \le \varepsilon_+\lvert a x_i + y_i\rvert +
(1 + \varepsilon_+)(\varepsilon_\times\lvert a x_i\rvert + \tau)$, exported in the form relative
to the operands, $\mathrm{unit}\cdot(\lvert a x_i\rvert + \lvert y_i\rvert) + \mathrm{tiny}$.

**Statement of `conv_k`.** Coefficient $j$ satisfies the statement of `dot` for its own terms;
the largest number of terms of a coefficient is $\min(n_a, n_b)$.

*Proof.* The tree theorem with the leaves $x_i \otimes y_i$, and the triangle inequality.
*Checked:* `batch.py`: 2 500 dot products per format in four orders, with operands down to the
underflow range, at most 0.72 of the bound. *Smallest precision:* that of the kernels: 3 for
the sums, 4 for the products of two limbs. *Risk: low* for the statements; the risk is the fold.

**When something is not finite.** The loop runs the finite cores, so
[D5](phase0/decisions.md#d5-non-finite-results) applies in its batch form: a result is finite
and within its bound, or it is not finite. For a fold of additions and products, a finite
leading limb of the final state means that every state before it was finite: the leading limb
of every operand of a core reaches the leading limb of its result through operations that keep
a NaN and turn an infinity into an infinity or a NaN, which is the cone rule; so the bridge of
Milestone 1 applies step by step. Every batch function returns its value with a flag:

- a function that returns a number returns the canonical NaN, $(\mathrm{NaN}, \mathrm{NaN})$, and
  `finite = false`, when the leading limb of the final state is not finite. Which infinity an
  IEEE sum of the operands would have given is not computed; this is the "not finite, which
  value is unspecified" of D5, made a definite value;
- a function that writes an array accumulates the test of each written leading limb in a mask
  of its state; when the mask is false at the end, a second pass makes every element that is
  not finite a canonical NaN, and `finite = false`. `norm_upper_k` carries such a mask too: a
  maximum computed by comparisons would otherwise lose a NaN.

In both cases an operand that is not finite, or any overflow, gives `finite = false`, and
`finite = true` means that every result is finite, valid, and within its bound.

### The bound as a function of n

A program that used to write $n\,u$ in its own error analysis cannot write $n \cdot 3u^2/(1-4u)$
exactly in floating point: Kairn's units are not powers of two. So the bound is a function,
`traits<X>::sum(n)` and `traits<X>::dot(n)`, whose result is a number of `T` that is certainly
at least the real bound. It is a generated kernel with a proved statement, like every other
bound in the library.

```
bound_sum_2(m) -> (g, ok)                          m: the number of additions on a path
  a  = prod(m, const up((1+u)*(unit(add_2_2)+eta/2)))       a  >= m eps
  aa = prod(m, const up((1+u)^2*(unit(add_2_2)+eta)))       aa >= (1+u)(m eps + eta/2)
  d  = add(a, a)                                            2a, exact
  w  = add(d, const up(1+2*u))                              >= 1 + 2a   (for a <= 1/2)
  g  = prod(aa, w)                                          >= m eps (1 + 2 m eps)
  ok = le(a, const up(1/4))

bound_dot_2(m) -> (g, t, ok)                       m: the number of terms
  the five lines of bound_sum_2, with unit(mul_2_2)
  tm = prod(m, const up((1+u)^2*(tiny(mul_2_2)+eta)))       >= (1+u)(m tiny + eta/2)
  wg = add(g, const up(1+2*u))                              >= 1 + g    (for g <= 1)
  t  = prod(tm, wg)                                         >= m tiny (1 + g)
  oa = le(a, const up(1/4));  ob = le(g, const up(1));  ok = and(oa, ob)
```

**Statement, real model**, for a number $m$ of the format that is zero or at least 1, in a
format that contains $\tfrac12$; from the precision of the kernel named.

- `bound_sum_2`: if `ok`, then $m\,\varepsilon_+ \le \tfrac12$ and
  $g \ge \gamma_m(\varepsilon_+)$.
- `bound_dot_2`: if `ok`, then $g \ge \gamma_m(\varepsilon_\times) \ge
  (1 + \varepsilon_\times)(1 + \varepsilon_+)^{m-1} - 1$ and
  $t \ge m\,\tau\,(1 + g) \ge (1 + \varepsilon_+)^{m-1}\,m\,\tau$: the two terms of the statement
  of `dot` for $m$ terms in any order. (It uses $\varepsilon_\times \ge \varepsilon_+$, which
  holds from $p = 4$.)

When `ok` is true is not part of the theorem; it is a fact about each format, computed from its
constants. In `binary64` and `binary32` it is true for every $m$ with
$m\,\varepsilon \le 0.24$, and in the toy formats of `batch.py` it was true up to
$m\,\varepsilon \le \tfrac15$.

The same two listings with the constants of `add_1_1` and `mul_1_1` are `bound_sum_1` and
`bound_dot_1`.

*Proof.* $\gamma_m(\varepsilon) \le m\varepsilon(1 + 2m\varepsilon)$ when
$m\varepsilon \le \tfrac12$, which avoids a division. A rounding to nearest of a nonnegative
product is at least the product divided by $1 + u$, less $\tfrac12\eta$ (`rnd_lower`, `Ball2.v`),
and each constant carries the factor and the term that this costs, using $m \ge 1$; a sum of
nonnegative numbers loses only the factor. $a \ge m\varepsilon$ makes the test on $a$ a test on
$m\varepsilon$. *Checked:* `batch.py`: for every count up to $2^{52}$ of a list in `binary64`
and up to $2^{23}$ in `binary32`, and in three toy formats, $g$ and $t$ are at least the exact
rationals; in `binary64` $g$ exceeds $\gamma_m$ by at most $8.7 \cdot 10^{-16}$ of it, in
`binary32` by $4.7 \cdot 10^{-7}$. For those counts $m\varepsilon$ is tiny; in general $g$ is
about $(1 + 2x)(1 - x)$ times $\gamma_m$ with $x = m\varepsilon$, which is $1.125$ at
$x = \tfrac14$. *Smallest precision:* 3 and 4. *Risk: low.*

**In the header.** `traits<X>::sum(n)` calls `bound_sum_k` with $m = n - 1$ converted to `T`,
and `dot(n)` calls `bound_dot_k` with $m = n$; a conversion that is not exact (possible for
`float` beyond $2^{24}$) is followed by one step up. When `ok` is false the bound is $+\infty$,
which claims nothing: for a `double` of two limbs that needs more than $2^{102}$ terms, for a
`float` of one limb more than about four million. The functions are `constexpr`, because the
kernels contain no fused operation but `prod`
([the two executions of a product](#the-two-executions-of-a-product)); in a constant expression
a false `ok` is a compile error with a message, which is the precondition "checked at compile
time when $n$ is a constant". `traits<X>::axpy` is a constant, like the bounds of Milestone 1.
A bound of the sum for a known height, `sum_height(h)`, is the same kernel and is offered for an
order that the program knows.

*Not claimed:* the smallest number of `T` above the real bound; a bound when
$n\varepsilon$ exceeds about $\tfrac14$, where it would be a third of the sum of magnitudes
anyway.
Computing it exactly in integer arithmetic instead is [question 4](#open-questions).

### The accumulator

`Accumulator<T, k>` is the state of `sum_k` and `dot_k` given to the program, for loops that
Kairn does not provide (a product of polynomials over several indices, for example). It holds
the running k-number $s$, a running sum $a$ in `T` of the magnitudes of the leading limbs of
what was added, and the count $n$.

| Operation | Kernel | Does |
|---|---|---|
| `acc.add(x)` | `acc_add_k` | $s \leftarrow s \oplus x$, `a = add(a, abs(x0))` |
| `acc.add_product(x, y)` | `acc_mul_k` | $s \leftarrow s \oplus (x \otimes y)$, `a = fma(abs(x0), abs(y0), a)` |
| `acc.merge(other)` | `acc_merge_k` | $s \leftarrow s \oplus s'$, `a = add(a, a')`, $n \leftarrow n + n'$ |
| `acc.sum()` | | $s$, canonical, with the flag |
| `acc.error_bound()` | `acc_radius_k`, `bound_dot_k` | a `T` that is at least the bound of `dot` for what was added |
| `acc.ball()` | the constructor of `Ball` | the ball of center $s$ and that radius: it contains the exact sum |

*Statement.* After any sequence of `add`, `add_product` and `merge` with valid operands, if $s$
is finite then $\lvert s - \Sigma\rvert \le$ `error_bound()`, where $\Sigma$ is the exact sum of
the numbers and products added. The order is whatever the program did; a merge is a node of the
tree. The radius is computed from $a$: the terms satisfy
$\sum_i\lvert x_i y_i\rvert \le (1+u)^{n+2}\,(a + \tfrac12 n\eta)$, by the leading limbs
($\lvert x\rvert \le (1+u)\lvert x_0\rvert$) and $n$ roundings of nonnegative values.
*Checked:* `batch.py` asserts that inequality on every dot product it runs. *Proof:* the tree
theorem and `chain_step` (`Ball2.v`); `acc_radius_k` has the form of
[`conv_radius`](#ballvector). *Risk: medium*: three kernels and a class, none of them hard.

*Not claimed, and left for later:* an accumulator that keeps unnormalized limbs and normalizes
once at the end (the "fused" loop of the [brief](brief.md)). Its statement would be that of
the cascaded summation of [ORO05](phase0/references.md#oro05), an error near
$\gamma_n(u)^2\sum\lvert x_i\rvert$ plus one rounding; I do not see its proof in the present
framework clearly enough to state it as a target ([question 12](#open-questions)).

## BallVector

A `BallVector` is $N$ centers and one radius: the set of vectors each of whose entries is within
the radius of its center. Every operation returns a `BallVector` that contains the exact result
for every member of its operands. It costs one kernel per entry and a few operations of `T` for
the radius, where $N$ balls would cost a radius per entry.

**Values.** `BallVector<T, k, N>` holds $N$ k-numbers and one `T`; `BallVectorView<T, k>` holds
pointers to the limb arrays of a run-time length and a reference to the radius. A value is
*canonical* when it is a finite ball (every center finite, and normalized for two limbs; the
radius finite and nonnegative) or the **whole space**: every center zero and the radius
$+\infty$. There is no empty state ([question 7](#open-questions)); a constructor given a
radius that is negative or a NaN, or a center that is not finite, returns the whole space.

**What is stated of a kernel**, in the IEEE model, for canonical operands:

- **V1.** The result is canonical.
- **V2. Containment**, in every case: for every member $x$ of $X$ and $y$ of $Y$,
  $f(x, y)$ is a member of $Z$. The whole space contains everything.
- **V3.** If the result is a finite ball, every operand is one, the centers are those of the
  fold on the centers, and the radius is the formula of the table.
- **V4.** The result is a finite ball when every operand is and no member of the exact result,
  entry by entry, exceeds a stated fraction of the overflow threshold in magnitude. For the
  sums, the differences, the scalings and `axpy` it is the fraction of the entrywise `Ball`
  operation ([B4](milestone1.md#when-the-result-is-a-finite-ball)). For the product of
  polynomials it is to be fixed by the proof: `conv_radius` has larger constants in formats of
  few bits, as `ball_mul_1` had.

Every kernel also returns the flag `finite`, true exactly when the result is a finite ball. When
it is false the centers are set to zero in a second pass.

| Kernel | Centers | Radius | Against the entrywise `Ball` operation |
|---|---|---|---|
| `bv_neg_k` | `neg` | $r_x$ | equal: exact |
| `bv_add_k`, `bv_sub_k` | `add_k`, `sub_k` | `bv_add_radius_k(M, rx, ry)`: the radius lines of `ball_add_k` with $M = \max_i\lvert c_{z,i,0}\rvert$ | **equal** to the largest of the $N$ radii of `ball_add_k` |
| `bv_scale_k`, by a `T` | `scale_k` | `bv_scale_radius_k(M, rx, a)`: the radius lines of `ball_scale_k` | **equal** to the largest of the $N$ radii |
| `bv_mul_pow2_k` | `mul_pow2_k` | [exact scaling](#scaling-a-ball-by-a-power-of-two), with `ec` over all entries | equal: $c\,r_x$ when every entry is exact |
| `bv_axpy_k` | `axpy_k` | `bv_add_radius_k(M, bv_scale_radius_k(M', rx, a), ry)` | at least the largest; equal when one entry has both maxima |
| `bv_conv_k`, the product of polynomials | `conv_k` | `conv_radius`, [below](#the-product-of-polynomials) | not compared |

`bv_norm_upper_k` returns a number and not a `BallVector`; it is after the table.

**Why the first rows are equalities.** The radius of `ball_add_k` is
$\mathrm{RN}(\mathrm{RN}(a_z E + \mathrm{RN}(r_x + r_y))\,G + H)$ with $a_z$ the magnitude of the
leading limb of the center. Every operation in it is a rounding of a nondecreasing function of
$a_z$, so the formula does not decrease when $a_z$ grows, and evaluating it once at the largest
$a_z$ gives the largest of the $N$ values. The fold on the centers carries that maximum in its
state; the radius is three operations at the end. No a priori bound is used and nothing is lost
in tightness. *Proof:* `ball_add_k_correct` at each entry, and the monotonicity of rounding
(`round_le`). For `bv_axpy_k` the two maxima, of the scaled centers and of the results, may be
attained at different entries, which is the only loss. *Checked:* `batch.py`, 1 500 vectors per
format: equality for the sum and the scaling in every case, and for `axpy` in 76 to 87% of them.

**`bv_norm_upper_k`** returns a number of `T` that is at least $\max_i\lvert c_i\rvert$. For one
limb it is that maximum. For two limbs it is `succ(M)`, with $M$ the largest magnitude of a
leading limb: a normalized pair is strictly between the neighbors of its leading limb
(`normalized_2_between`, `Convert.v`), and a step is monotone. It is at most one step above the
smallest such number of `T`. One step for the whole vector replaces one `abs_upper` per entry.
A norm with weights is the program's own loop, on `abs_upper` and `rmul`
([Building blocks](#building-blocks-on-t)).

### The product of polynomials

The coefficients of a product of polynomials are sums of products of coefficients, so the radius
has two parts: what the radii of the operands become, and the rounding of the centers. With
$m = \min(n_a, n_b)$ the largest number of terms of a coefficient, $M_a$ and $M_b$ the largest
magnitudes of the leading limbs of the centers, and $(g, t)$ = `bound_dot_k(m)`:

$$r_z \ \ge\ m\,\bigl((1+u)M_a\,r_y + (1+u)M_b\,r_x + r_x r_y\bigr)
\ +\ g\,m\,(1+u)^2 M_a M_b + t .$$

```
conv_radius(ma, mb, rx, ry, m, g, t) -> rz           all nonnegative, m >= 1, g <= 1
  p  = prod(rx, ry)
  q  = fma(mb, rx, p)
  w  = fma(ma, ry, q)
  ab = prod(ma, mb)
  e  = fma(ab, g, w)
  s  = fma(m, e, t)
  hm = prod(m, const up(4*(1+u)^8*eta+eta/(2*u)))
  rz = fma(s, const up((1+u)^7), hm)
```

*Statement:* $r_z$ is at least the right side of the displayed inequality, and `bv_conv_k`
satisfies V1 to V4 with it. *Why it is a radius:* for members $x$, $y$ of the operands,
coefficient $j$ of the exact product differs from the exact product of the centers by at most
$\sum_i(\lvert c_{a,i}\rvert r_y + \lvert c_{b,j-i}\rvert r_x + r_x r_y)$, at most $m$ terms,
and the computed center differs from the exact product of the centers by at most
$g\sum_i\lvert c_{a,i}\,c_{b,j-i}\rvert + t$ by the statement of `dot`.

**The a priori bound and what it costs.** The sums over the terms of a coefficient are replaced
by $m$ times the largest term: $m\,M_a$ for $\sum\lvert c_{a,i}\rvert$ and $m\,M_a M_b$ for
$\sum\lvert c_{a,i}\,c_{b,j-i}\rvert$. For coefficients of comparable size, such as those of a
polynomial in the Bernstein basis, that is the right order. For coefficients that decay it
overestimates by up to the factor $m$; the sum of the magnitudes, one more pass, would remove
most of it and is left out of this milestone. The radius is not obtained by following what $m$
ball products and $m - 1$ ball sums would return: that evaluation inflates at every step, and
this one once.

*Proof:* the statement of `dot`; the chain of roundings of nonnegative values of `radius_4`
(`Ball2.v`), one link longer, whence $(1+u)^7$; the constant of `hm` covers the $\tfrac12\eta$
that each of five roundings can lose, multiplied by $m$, and holds the $N$ that keeps a radius
normal. *Checked:* `batch.py`: `conv_radius` is at least its right side on every case, and
4 500 products of polynomials of up to four coefficients, at four to six bits, are contained,
the needed radius reaching 0.45 of the computed one. *Smallest precision:* 4 for two limbs.
*Risk: medium.*

*Not claimed:* a tight radius for polynomials whose coefficients differ much in size; a
`BallVector` with one radius per entry or with weights, which is not this type.

## Constants at compile time

`rational(num, den)` turns a fraction of two integers into a k-number, with a bound of the error
it made and a flag that says whether it made none. It works in constant expressions and at run
time, and gives the same result in both, because it uses no floating-point operation at all.
Until Kairn has a division, it is also how a program divides by an integer: `rational(1, s)`.

```cpp
template <class X> struct Constant { X value; typename traits<X>::limb_type error; bool exact; };
template <class X> constexpr Constant<X> rational(long long num, long long den);
template <class X> constexpr Constant<X> integer(long long n);     // rational(n, 1)
```

**Arguments.** Any two 64-bit signed integers, $-2^{63}$ included, with $den \ne 0$. In
particular every `rational(1, s)` with $s$ up to $2^{53}$ and beyond. Then $q = num/den$ is zero
or between $2^{-63}$ and $2^{63}$ in magnitude, so for `float` and `double` the value never
overflows and its first limb is never subnormal; the second limb of a `float` pair can be.

**Statement**, for `X` of limb type `T` and $k$ limbs:

- $k = 1$: `value` $= \mathrm{RN}(q)$.
- $k = 2$: `value` is the normalized pair whose value is
  $\mathrm{RN}(q) + \mathrm{RN}(q - \mathrm{RN}(q))$. There is exactly one: the leading limb of
  a normalized pair is the rounding of its value ([Numbers](phase0/numbers.md#a-k-number)).
- `error` is the smallest number of `T` that is at least $\lvert\mathrm{value} - q\rvert$.
- `exact` is true exactly when $\mathrm{value} = q$, that is when `error` is zero.
- Consequently $\lvert\mathrm{value} - q\rvert \le \tfrac{u}{1+u}\lvert q\rvert$ for one limb and
  $\le u^2\lvert q\rvert$ for two. No underflow term is needed with these arguments: where the
  second limb of a `float` pair is subnormal its error is at most $\tfrac12\eta = 2^{-150}$,
  and $u^2\lvert q\rvert$ is at least $2^{-111}$.
- $den = 0$: in a constant expression the call does not compile; at run time the result is the
  canonical NaN with `error` $= +\infty$ and `exact` false. A value beyond the range of `T`
  cannot occur with these argument types; a later wider argument type returns the canonical
  infinity with `error` $= +\infty$.

$\mathrm{RN}$ is the rounding of the format, ties to even, with gradual underflow.

**Why the second limb is not simply "the rounding of what is left".** The pair
$(\mathrm{RN}(q),\ \mathrm{RN}(q - \mathrm{RN}(q)))$ is not always normalized. When $q$ is very
close to the midpoint of two numbers of `T`, the remainder rounds to exactly half the gap, and
if the first limb is the neighbor with the odd significand the sum of the two limbs rounds to
the *other* neighbor. This happens with 64-bit operands: for a midpoint $A/2^j$ there are
denominators below $2^{63}$ with $num \cdot 2^j - A \cdot den = \pm 1$. In `rational.py`, 733 of
the 40 030 two-limb results in `binary64` (10 000 of them built that way) needed the pair
renormalized. The value does not change; its leading limb is then not $\mathrm{RN}(q)$.

**The computation.** Integer operations only: for each limb, one division with remainder of two
integers aligned so that the quotient has $p$ bits, a comparison of twice the remainder with the
divisor for the tie rule, then the exact sum of the two limbs as one integer, rounded once more
to renormalize. The widest integer is below $2^{180}$ for two `double` limbs (168 bits were
observed, 110 for `float`), so a fixed capacity of three 64-bit words is enough, without
`__int128`. The limbs are assembled from significand and exponent by `std::bit_cast`, so that not
even the final step is a floating-point operation, and the result cannot depend on a rounding
mode or on `-frounding-math`.

**What is machine-checked, and what is tested.** This is integer code written by hand in the
header, not a floating-point kernel, and the generator has no integer IR: there is no generated
model of it and no Rocq theorem about the C++. What can be said honestly:

- *Tested, and for equality.* The specification fixes every bit of the result, so the oracle,
  which computes with exact rationals and shares no code with the header, compares the limbs,
  the error and the flag for equality, not against a bound: every pair of small terms, random
  64-bit terms, powers of two and the extremes, and the near-ties constructed as above. A
  result one unit off anywhere is a failure. `rational.py` is this test against a model of the
  algorithm in Python: 80 060 results per limb type and 44 790 in three toy formats, all equal.
- *Not machine-checked.* That the C++ implements the specification for all $2^{128}$ pairs.
- *Could be machine-checked later:* a Rocq function over the integers that mirrors the
  algorithm, proved against the specification with Flocq; the link from that function to the
  C++ would still be by reading.
- *An option that shrinks what is trusted:* a checker, `value * den` compared with `num` within
  `error * den` in exact integers, which is multiplications and comparisons only, run inside
  the same constant evaluation and made a compile error on failure. It would not prove the
  rounding is the nearest, only that the stated error bound is true
  ([question 5](#open-questions)).

*Recorded as:* a numbered deviation next to
[deviation 17](phase0/decisions.md#deviations-from-the-brief-flagged) ("shipped code is
generated, and every bound is machine-checked"), and a line on the reference page of `rational`
that says "specified exactly; tested for equality with the oracle; not machine-checked".
*Risk: low to medium* (edge cases of integer code).

## Limbs of another type

A program that builds its data in `double` on the host and computes in `float` on a device
needs to move numbers and balls from one limb type to the other without losing the enclosure.
Going from `float` limbs to `double` limbs loses nothing. Going the other way rounds, and the
radius of a ball grows by a bound of that rounding, so that the narrow ball contains the wide
one.

Write $N$ for the narrow format and $W$ for the wide one; $u$ and $\eta$ are those of $N$,
$u_w$ is that of $W$. Every number of $N$ is a number of $W$.

| Conversion | How | Statement |
|---|---|---|
| wide, one limb, to narrow, two limbs | $f_0 = \mathrm{RN}_N(x)$; $r = x - f_0$, exact in $W$; $f_1 = \mathrm{RN}_N(r)$; `fast_two_sum` in $N$ | $z$ normalized; $\lvert x - z\rvert \le u^2\lvert x\rvert + \tfrac12\eta$ |
| wide, two limbs, to narrow, two limbs | $f_0 = \mathrm{RN}_N(x_0)$; $r = \mathrm{RN}_W((x_0 - f_0) + x_1)$; $f_1 = \mathrm{RN}_N(r)$; `fast_two_sum` in $N$ | $z$ normalized; $\lvert x - z\rvert \le \dfrac{(u + u_w)^2}{1 - u_w}\lvert x\rvert + (1 + u_w)\tfrac12\eta$ |
| wide to narrow, one limb | $\mathrm{RN}_N(x_0)$, then as `to_nearest` | the bound of one rounding, plus $u_w\lvert x\rvert$ for two wide limbs |
| narrow, two limbs, to wide, two limbs | `fast_two_sum` in $W$ of the two limbs | exact; normalized in $W$ |
| narrow, two limbs, to wide, one limb | one addition in $W$ | $\mathrm{RN}_W(x)$ |
| a ball, wide to narrow | the center as above; the radius rounded up to $N$, then grown by the bound of the center's conversion in its computed-value form, as a `Ball` radius of the second design | the narrow ball is canonical and contains the wide one |

A value beyond the range of $N$ gives the canonical infinity, and the ball the whole line, by a
fix-up as in the full kernels of Milestone 1: the steps above return a NaN there
($\infty - \infty$), and the result is $(\pm\infty, 0)$ with the sign of $x_0$ whenever $f_0$
or the renormalized first limb is not finite. That includes the case where $f_0$ is the largest
number of $N$ and the renormalization carries beyond it. For `double` to `float`,
$(u + u_w)^2/(1 - u_w)$ is $2^{-48}(1 + 4 \cdot 10^{-9})$.

The factor $1 + u_w$ on the underflow term of the second row is needed in general: when $x_0$
is half the smallest number of $N$, both limbs of the result are zero and the error is all of
$x$, which is $(1 + u_w)$ times $x_0$ at most. With $\tfrac12\eta$ alone the statement holds
when $u_w \le u^2$, as for `double` and `float`, and fails otherwise.

*Checked:* `convert.py`, on five pairs of toy formats, every normalized pair of the wide one or
60 000 of them: the largest error was 0.985 of the bound for one wide limb and 0.982 for two, and
every ball was contained. With $\tfrac12\eta$ alone the second row failed in 1 and 14 cases of
the two pairs of formats with $u_w > u^2$, and in none of the three with $u_w \le u^2$.

*Proof.* $x - \mathrm{RN}_N(x)$ is exact in $W$ because it is a difference of two nearby numbers
of $W$ (Sterbenz), or $x$ itself when the rounding is zero; then one rounding in $W$ and one in
$N$, each with the relative bound of Milestone 1's one-limb kernels, or an absolute
$\tfrac12\eta$ where the rounding in $N$ is in its subnormal range; `fast_two_sum`'s
requirement holds because the second limb is at most half the gap of the first.

*What it needs.* Kernels with two formats, which the IR does not have: two operations,
`narrow a` (a cast, rounded to nearest in $N$) and `widen a` (exact), a format on every value,
and a real model with two roundings and the hypothesis that $N$ is inside $W$. *Risk:*
**medium to high**, all of it in the generator; the statements are low risk. It is the item of
this milestone most easily moved to the next, with the device pass it serves.

## Packed type and containers

`Packed<T, k>` holds $W$ k-numbers, limb $i$ of all of them in one register; `SoA<T, k>` and
its views hold $N$ k-numbers as one array per limb, with element access through a proxy.
Neither has arithmetic of its own. The operations of `Packed` are the packed forms of the
kernels, which the generator already emits and tests lane by lane against the scalar form; the
statement is that of the scalar kernel in each lane. The containers move limbs. What this
milestone states about them is small: an element read from a container is the value written
(limbs are copied, never recomputed); a view does not own or allocate; and the unchecked
constructor from limbs keeps its precondition, a canonical value, which a debug build checks.
The folds above are the loops; the packed type is for the loops a program writes itself.

## Inlining and compile time

Kairn forces the inlining of every kernel of at most two limbs. That is a choice for speed. A
program in which thousands of ball operations are inlined into a few large functions pays for
it at compile time, and may prefer the kernels as ordinary functions. The rules allow that.

- **No guarantee needs inlining.** Rules R1 to R3 exist to make inlining *safe*: they describe
  what a compiler may fuse once a kernel's body is merged into its caller. A kernel that is
  called through a real call boundary receives its operands as rounded values in registers or
  memory, and a contraction cannot cross the call. The guard of rule R3, which concerns a value
  entering from the program, is then one addition that changes nothing; it must stay, because
  the same header may be inlined in another build, or by link-time optimization.
- **The object-code check already tests the out-of-line form**: it compiles one function per
  kernel and counts its fused instructions ([Testing](../testing.md#object-code)).
- **Where forced inlining matters for speed:** the kernels of one and two limbs called in a
  chain of dependent operations (a call costs more than a two-limb addition), and one limb,
  which must cost what `T` costs.
- **Where it does not:** the fix-up, which on one platform is already a function of its own;
  a batch kernel, which is a loop with the step inlined in it and is itself an ordinary inline
  function, emitted once per translation unit; and any `Ball` or `Interval` operation in code
  that is not on a critical path.

*Proposed:* one macro, set by the program before including Kairn, with three values.
*Inline* (the default): as today. *Outlined:* the kernels of the `Ball`, `Interval` and
`BallVector` operations are plain inline functions that the compiler is asked not to inline;
each is compiled once per translation unit that uses it, and stays usable in constant
expressions. *External:* those kernels are declared only, and one translation unit of the
program defines them, as [Library](phase0/library.md#inlining-and-compile-time) planned for
large numbers of limbs; an external kernel cannot be evaluated at compile time, because a
constant expression needs the body. The three forms compute the same values, since the body is
the same listing. Each is one more configuration for the test tiers and the object-code check.
Compile times of the three, on a unit with many ball operations, are part of the milestone's
report. The names are [question 13](#open-questions).

## IEEE 1788

The text of IEEE Std 1788.1-2017 was read against this page on 2026-11-20; the owner obtained
it. It is not public and is not in the repository, so what follows cites its clauses and does
not quote them. Until then the semantics came from the P1788 drafts and from implementations
([deviation 12](phase0/decisions.md#deviations-from-the-brief-flagged)). This section lists
the points where an implementation of the set-based model can differ, what Kairn does at each,
and what the standard says. Kairn is *modeled on* IEEE 1788.1 and is not a conforming
implementation: the standard requires decorations, text input and output, and operations that
Kairn does not have, and its one interval type has bounds of type `binary64`.

| Point | Kairn | IEEE Std 1788.1-2017 |
|---|---|---|
| The empty set and its bounds | stored $(+\infty, -\infty)$; `lower` and `upper` return these | the same: by convention the lower bound of the empty set is $+\infty$ and the upper $-\infty$ (3.2, Table 4.3), and that pair is its representation (7.1, 7.3) |
| Members | real numbers; $\pm\infty$ can be bounds and are never members | the same (4.2) |
| An operation on an empty operand | empty | the same: the range over an empty box is empty (4.4.4) |
| $[0, 0] \cdot X$ for nonempty $X$, unbounded included | $[0, 0]$ | the same (the example of 4.4.4) |
| The constructor from two numbers, $lo > hi$, $[+\infty, +\infty]$ or $[-\infty, -\infty]$ | the empty set, silently | the same value (6.7.5); the standard also signals an exception (6.1.4), and its decorated form returns "not an interval" |
| The constructor from two numbers, a NaN bound | the whole line ([question 1](#open-questions), decided by the owner) | **differs**: the call fails and returns the empty set (6.7.5) |
| The sign of a zero bound | unspecified | **differs**: a zero lower bound is returned as $-0$, every other zero as $+0$ (6.7.6, 7.3) |
| Tightness of $+$, $-$, $\times$ on one limb | tightest for sums and differences; for products tightest outside the range below $2^{2p-1}\eta$, and at most one number wider inside it | **differs** inside that range: the basic operations shall be *tightest* (6.5.2). Kairn's product there is within the standard's second mode, *accurate* (6.5.1): it is inside the tightest result widened by one number on each side |
| Two limbs; `float` bounds | bounds within about $8u^2$ and $10u^2$; the same statements as for `double` | not types of the standard, whose one type has `binary64` bounds (6.1.1) |
| An overflow on bounded operands | one limb: $[\Omega, +\infty]$; two limbs: the infinite bound on the side of the overflow, or the whole line | one limb: the same, it is the tightest interval of the type; two limbs: valid, not tight |
| `mid` | bounded: within one rounding and $\eta$ of the midpoint, inside the interval; whole line 0; half-line $\pm\Omega$; empty NaN | the special values are the same (6.7.6, 6.1.4). For a bounded interval the standard asks for the midpoint rounded to nearest and for a description of how that case is handled; Kairn's is that number unless a bound is an odd multiple of $\eta$, where it is within $\eta$ of it |
| `rad` | the smallest radius for *Kairn's* midpoint; $+\infty$ if unbounded; empty NaN | the same: the smallest number such that the returned midpoint, with it, covers the interval; NaN for the empty set (6.7.6) |
| Hull and intersection | exact; the hull with the empty set is the other operand, the intersection with it is empty | the same (4.5.4, 6.7.4) |
| `equal`, `subset`, `interior`, `disjoint` | on the stored bounds, as [above](#comparisons) | the same on nonempty operands (Table 4.5, with its rule that an infinite bound is strictly inside an equal infinite bound) and on empty ones (Table 4.6): compared entry by entry |
| `less`, `precedes`, `strict_less`, `strict_precedes` | as [above](#comparisons) | not in this standard: they are relations of the full IEEE Std 1788-2015, which Annex A lists as not required. Their definitions here are still those of the drafts and of the test cases below |
| `wid`, `mag`, `mig`; cancellative addition and subtraction | not in the interface of this milestone | required (4.5.3, 4.5.6): absent |
| Division, also by an interval containing zero; square root and the rest of the required functions; text | later milestones | required (Table 4.1, 6.8): absent for now. The standard's division by $[0, 0]$ is the empty set |
| Decorations, the "not an interval" value, exceptions | none | required (clause 5, 6.1.4): absent, by the brief |

What the reading changed on this page: the relations of the standard are four, not eight; the
standard has a name, *accurate*, for what Kairn's product is in the underflow range; and its
constructor returns the empty set for a NaN bound, which the owner then chose to depart from,
for the reason of [question 1](#open-questions). Nothing else on the page contradicted the
text.

**What can serve as a check.** ITF1788, the *Interval Test Framework for IEEE 1788*
([ITF1788](phase0/references.md#itf1788)), is a public collection of test cases for the
operations of the standard, written in a small language of its own, for bounds of type
`binary64`. Its framework is under the Apache License 2.0. Its cases carry the license of the
library they came from:

- `libieeep1788_elem.itl`, `libieeep1788_num.itl`, `libieeep1788_bool.itl`,
  `libieeep1788_set.itl` and the other `libieeep1788_*` files (from M. Nehmeier's libieeep1788,
  converted by O. Heimlich) are under the **Apache License 2.0**. They cover the sum and the
  product with empty and unbounded operands, `mid`, `rad`, the comparison relations, the hull
  and the intersection, which is the scope of this milestone. They can be used: converted to
  Kairn's line protocol by a script, stored with their copyright notice and a statement of the
  change, as the license asks, and cited.
- `mpfi.itl`, `fi_lib.itl` and `c-xsc.itl` (from GNU MPFI, FI_LIB and C-XSC) are under the
  **LGPL, version 2.1 or later**. Kairn's rule takes code and data only from MIT, BSD and Apache
  sources, so these are not copied into the repository. A developer may run them from a
  checkout of ITF1788 outside it.

The special values of this page were compared with those files where they are quoted:
`mid` of the empty set, of the whole line and of a half-line; `rad` of the same; the relations
of the empty set and of the whole line with themselves; `mul` of the whole line with $[0, 0]$.
A test case is evidence about the standard, not the standard: the cases were written by people
who took part in its drafting and are used by several implementations. For the four relations
that are not in IEEE Std 1788.1, they are the only check there is until someone reads the text
of the full standard.

*For `Interval<T, 1>` with `T = double`* the cases apply as they are, up to the two rows marked
"no" above. For `float` and for two limbs they give the special values and the conventions, not
the bounds.

## Every new kernel

The names follow Milestone 1: an operation, then the numbers of limbs of its operands; a prefix
for the type it serves; `_full` for a finite core with its fix-up; `_entry` for a building block
that guards its operands. "IEEE" says where the statement lives: *both* (a real-model statement
on finite operands and an IEEE-model one, as for `radd`), *only* (no real-model statement, as
for a full kernel), *core* (a finite core: the real-model statement, and the IEEE-model
statement that a finite result has it). $p$ is the smallest precision the statement is expected
from. `k` stands for 1 and 2.

| Kernel | Inputs, outputs | Requires | Ensures | Rests on | $p \ge$ | IEEE | Risk |
|---|---|---|---|---|---|---|---|
| `next_up`, `next_down` | $a \to r$ | — | `neighbor` up, down ([table](#next_up-and-next_down-on-every-input)) | `Bsucc_correct`, `IeeeOps.v` | 1 | both | low: one operation |
| `two_sum_ord` | $(a, b) \to (s, e)$ | — | `leading_rounded`; `error` with $c = 0$; `normalized` | `fast_two_sum_correct` | 2 | both | low: a select in front of a proved kernel |
| `add_down_1`, `add_up_1`, `sub_down_1`, `sub_up_1` | $(a, b) \to r$ | — | `rounded` down, up | `two_sum_ord`; `pred_UP_eq_DN` | 2 | both | low: the argument of `to_down_2` |
| `mul_down_1`, `mul_up_1` | $(a, b) \to r$ | — | `bound` with `steps` 1; `rounded` when `product_large` | `two_prod_exact`; one new lemma | 2 | both | medium: the lemma at the edge of the range |
| `mul_dir_1` | $(a, b) \to (d, v)$ | neither a NaN | the same two, and zero for a zero factor | as above | 2 | both | medium |
| `two_sum_entry`, `fast_two_sum_entry`, `radd_entry`, `add_down_entry`, `add_up_entry`, `sub_down_entry`, `sub_up_entry` | as the kernel called | as the kernel called | as the kernel called | `guard_ieee`, `Guard.v` | 2 | as called | low: two guards |
| `interval_make_k` | $(lo, hi) \to (z_\ell, z_u)$ | canonical bounds, for two limbs | `makes_interval` | the way of `IeeeMake.v` | 1 | only | low |
| `interval_neg_k` | $X \to Z$ | `interval` | `encloses_interval`, exact | — | 1 | only | low |
| `interval_add_1`, `interval_sub_1` | $(X, Y) \to Z$ | `interval` | `encloses_interval`, `tight` rounded, bounded exactly within $\Omega$ | `add_down_1`, `add_up_1` | 2 | only | low |
| `interval_mul_1` | $(X, Y) \to Z$ | `interval` | the same, with `steps` 1 unless `product_large` | `mul_dir_1`; the lemma of the rectangle | 2 | only | medium: many cases |
| `add_ball_2_2`, `mul_ball_2_2` | $(x, y) \to (z, d)$ | normalized | `normalized`; `error`; `encloses z d` | `ball_add_2_correct`, `ball_mul_2_correct` | 3, 4 | core | low: the ball with radii zero |
| `add_down_2_2`, `add_up_2_2`, `sub_down_2_2`, `sub_up_2_2` | $(x, y) \to l$ | normalized | `normalized`; `outward` with $A$, $B$ | the row above; `sub_down_1`; `two_sum_ord` | 3 | core | medium: the first upper bound of a radius |
| `mul_dir_2_2` | $(x, y) \to (l, h)$ | normalized | `normalized`; `outward`, both sides | the same | 4 | core | medium |
| `mul_ext_2_2` | $(x, y) \to (l, h)$ | canonical, not NaN | `bound` in extended real numbers, $0 \cdot \infty = 0$ | `mul_dir_2_2`; `IeeeFull.v`'s cases | 4 | only | medium |
| `interval_add_2`, `interval_sub_2` | $(X, Y) \to Z$ | `interval` | `encloses_interval`, `tight` $A$, $B$, bounded within a quarter | the cores; the bridge of `add_2_2` | 3 | only | medium |
| `interval_mul_2` | $(X, Y) \to Z$ | `interval` | the same | `mul_ext_2_2`; `lt_2_2_ieee_correct` | 4 | only | **high**: the largest listing and proof |
| `interval_hull_k`, `interval_intersection_k` | $(X, Y) \to Z$ | `interval` | `encloses_interval`, exact | `Compare.v`, `IeeeExt.v` | 1 | only | low |
| `interval_mid_rad_k`, `interval_to_ball_k`, `interval_split_k` | $X \to (m, r)$, a ball, two intervals | `interval` | [stated above](#midpoint-radius-and-the-conversions) | `sub_up_1`; `add_ball_2_2`, `radd`, `to_up_2`, `mul_pow2_2` | 2, 3 | only | low for one limb, medium for two |
| `interval_contains_k`, `interval_subset_k`, `interval_positive_k`, `interval_negative_k`, `interval_zero_k`, `interval_empty_k`, `interval_entire_k` | $\to$ a mask | `interval` | `predicate`, exact | `Compare.v` | 1 | only | low |
| `interval_less_k`, `interval_less_equal_k`, `interval_equal_k` | $(X, Y) \to$ (yes, no) | `interval` | `trit`, exact | `Compare.v` | 1 | only | low |
| the eight relations of IEEE 1788, `interval_rel_NAME_k` | $(X, Y) \to$ a mask | `interval` | `predicate` on the sets | `Compare.v` | 1 | only | low; the definitions are the risk, not the proofs |
| `ball_to_interval_k`, `ball_lower_k`, `ball_upper_k` | a ball $\to$ bounds | `ball` | `encloses_interval`; `rounded` for one limb | the directed sums | 2, 3 | only | low |
| `ball_from_interval_k` | $(lo, hi) \to$ a ball | — | [stated above](#midpoint-radius-and-the-conversions) | `two_sum_ord`, `sub_up_1` | 2 | only | low |
| `ball_contains_point_k`, `ball_contains_ball_k`, `ball_less_k`, `ball_less_equal_k`, `ball_equal_k`, `ball_positive_k`, `ball_negative_k`, `ball_zero_k` | $\to$ masks | `ball` | `predicate` for the signs; `certain` and `trit`, exact for one limb without overflow | `two_sum_ord`, `abs_2`, the comparisons; `add_ball_2_2` | 2, 3 | only | medium for two limbs |
| `ball_hull_k`, `ball_intersection_k`, `ball_split_k` | balls $\to$ balls | `ball` | `encloses`, of a union, an intersection, two halves | the conversions; `ball_add_k_full` | 2, 3 | only | medium: compositions |
| `ball_mul_pow2_k`, `ball_mul_pow2_k_full` | $(c_x, r_x, c) \to (c_z, r_z)$ | normalized, $r_x \ge 0$, $c$ a positive power of two | `normalized`; `encloses`; `exact_when` | `mul_pow2_2_exact`, `up_above` | 2 | core, only | low |
| `dot_step_k`, `axpy_step_k`, and the folds `sum_k`, `dot_k`, `axpy_k`, `add_k`, `sub_k`, `scale_k`, `mul_pow2_k`, `conv_k` | arrays $\to$ a number or arrays, and a flag | valid elements | the bound of the fold as a function of $n$; `normalized` | the tree theorem; the kernels of Milestone 1; the bridge, step by step | 3, 4 | core | low for the statements, **medium to high** for the fold in the generator |
| `bound_sum_k`, `bound_dot_k` | $m \to (g, ok)$, $(g, t, ok)$ | $m = 0$ or $m \ge 1$; `format(half)` | `upper`: $g \ge \gamma_m$, when `ok` | `rnd_lower` | 3, 4 | real model | low |
| `acc_add_k`, `acc_mul_k`, `acc_merge_k`, `acc_radius_k` | the state of an accumulator | valid | the bound of `dot` for what was added | the tree theorem; `chain_step` | 3, 4 | core | medium |
| `norm_upper_k`, `bv_norm_upper_k` | an array $\to r$ | valid | `upper`, at most one step above the smallest | `normalized_2_between` | 1 | core | low |
| `bv_neg_k`, `bv_add_k`, `bv_sub_k`, `bv_scale_k`, `bv_mul_pow2_k`, `bv_axpy_k`, with `bv_add_radius_k`, `bv_scale_radius_k` | ball vectors $\to$ a ball vector and a flag | canonical | V1 to V4 | the `Ball` theorems entry by entry; `round_le` | as `Ball` | only | medium: the fold, and the second pass |
| `bv_conv_k`, with `conv_radius` | two ball vectors $\to$ one | canonical | V1 to V4 | the statement of `dot`; `radius_4`'s chain | 4 | only | medium |
| `narrow_1_1`, `narrow_1_2`, `narrow_2_2`, `widen_2_1`, `widen_2_2`, `narrow_up`, `ball_narrow_k` | a number or ball of one limb type $\to$ of the other | normalized; $N$ inside $W$ | [stated above](#limbs-of-another-type) | Sterbenz; the one-limb bounds | 2 | both | medium to high: two formats in the IR |

That is roughly ninety kernels, counting each number of limbs and each direction, of which
roughly thirty have a listing that is not a composition of two others. `rational` is not among
them.

## Order of implementation

The first use of this milestone by the first client needs little of it: one `Ball<T, 2>` per
coefficient, which exists, with the public building blocks, `rational`, the exact scaling of a
ball by a power of two, and if possible the enclosure interface. `BallVector` and the batch
kernels serve a second step. The waves are ordered accordingly. Within a wave the lines run in
parallel; the letters are the tracks: **G** generator and claims, **P** proofs, **O** oracle,
**H** public headers, **T** tests, **D** documentation.

**Wave 1: what the first pull request needs.**

1. G: the additions to the claims for one-limb kernels (`rounded` with two operands, `bound`,
   `exact_when`); the rule that makes a kernel with no fused operation but `prod` `constexpr`;
   `_entry` kernels. O: judging those claims, non-finite operands included.
2. G, then P and H in parallel: `two_sum_ord`, the directed sums and products, `next_up`,
   `next_down`, the entry forms; `rmul` and `mul_pow2_2` in constant expressions with the lemma
   of the two products.
3. G, P, H: `ball_mul_pow2_k` and its full form; `ldexp` and `half` on `Ball`.
4. H, O, T, independent of everything else: `rational`, its corpus and the equality test.
5. H, P: the part of the interface of `Ball` that needs no interval: `lower_as`, `upper_as`,
   `contains`, the signs, the comparisons, `split`; the list of functions that do not round,
   and the debug build's check taken off them.
6. P, from the first day and depending on nothing: the tree theorem and the lemma on
   $\gamma$.

**Wave 2: intervals.** Depends on 1.1 and 1.2.

1. `Interval<T, 1>`: G, then P (the rectangle lemma is the long part), O (intervals with
   empty and unbounded operands; the cases converted from ITF1788), H.
2. In parallel with 2.1: the cores of two limbs, `add_ball_2_2` to `mul_dir_2_2`, with the
   `outward` claim and its closed form; P for the real model.
3. After 2.2: `interval_add_2`, `interval_sub_2`, then `mul_ext_2_2` and `interval_mul_2`.
4. After 2.1: the rest of the interface (conversions, hull, intersection, midpoint and radius,
   the relations of 1788), and `ball_from_interval_k`.

**Wave 3: folds.** Depends on wave 1 only, and can start with it; the generator is its critical
path.

1. G: the fold description, its Rocq model over lists, the scalar loop; arrays in the
   interpreter and the line protocol. O: exact sums and dot products. Then the lane order and
   the packed loops.
2. P: the statements of `sum_k`, `dot_k`, `axpy_k`, `conv_k` from the tree theorem;
   `bound_sum_k`, `bound_dot_k`. H: the functions on arrays, `traits<X>::sum(n)` and `dot(n)`.
3. H, P: the accumulator. H: `Packed`, `SoA` and the views as public types.

**Wave 4: BallVector.** Depends on wave 3 and on 1.3: the kernels, their radii, the flag and
the second pass; `conv_radius`; V1 to V4.

**Wave 5: closing.** The conversions between limb types (G first: two formats). D throughout,
and here the pages that the brief asks of the milestone: the concepts (intervals, balls,
`BallVector`, when to use which), a tutorial per new type, the reference pages. T: the
brute-force tier and the exhaustive tier on the new kernels, the three inlining modes, compile
times, benchmarks; the report.

**What is at risk of not fitting**, in the order I would give them up:

1. The conversions between limb types: they need a second format in the IR and serve a pass on
   a device that is the next milestone's.
2. The lane order of the folds in packed code, if the generator's work on loops runs long: the
   sequential order alone already gives the statements, the bounds and `BallVector`.
3. The proof of `interval_mul_2`. Its containment can be tested exhaustively on small formats
   long before it is proved; until then it carries the `UNVERIFIED` marker, as the brief
   allows, and decision [D8](phase0/decisions.md#d8-workload-priority) puts intervals of two
   limbs after balls.
4. The closed form of the tightness of two limbs (I4), if the first upper bound of a radius
   costs more than expected: containment and I5 do not depend on it.
5. `bv_conv_k`'s V4 and the accumulator's radius, which are the least reused.

## Open questions

Each with the options and what I recommend.

**State on 2026-11-20**, after the review of this page
([decisions log](phase0/decisions.md#decisions-log)):

- The recommendation is adopted for questions 2 to 4 and 6 to 19. For question 6 nothing is
  given up that was promised: [Operations](phase0/operations.md#interval) already claims the
  tightest product of one limb only outside the underflow range.
- Question 2 is settled as (b), which changes the listings of the directed sums of two limbs
  above; they, their statements and their experiments are revised in a later version of this
  page, before those kernels are written.
- Questions 1 and 5 were the owner's, since the first departs from IEEE 1788 and the second
  ships a function whose bound is not machine-checked. Both were decided on 2026-11-20 as
  recommended. Question 1, (b): a NaN bound gives the whole line, for `Interval(lo, hi)` and
  for the ball from an interval; the listings and statements above, written for (a), are
  revised with those of question 2. Question 5, (b): `rational` is specified exactly, tested
  for equality with the oracle, checks its own error bound in every constant evaluation, and
  is recorded as [deviation 22](phase0/decisions.md#deviations-from-the-brief-flagged).

1. **A NaN bound given to the constructor of an interval.** (a) The empty set, as IEEE 1788
   and as written above. (b) The whole line. A NaN usually means that something upstream
   failed, and the empty set is the one value that a verified computation must never produce by
   accident: an empty box is discarded, and a root with it. The standard signals an exception
   there, which Kairn cannot. Milestone 1 already made a `Ball` with a NaN *center* the whole
   line. *Recommended: (b)*, for `Interval(lo, hi)` and for the ball from an interval alike,
   keeping the empty set for $lo > hi$; it is one select more, and a deviation from 1788 to
   record. It is written as (a) above because (a) is the decision taken.
2. **The sum of exact zeros in two limbs.** (a) As decided: $[0, 0] + [0, 0] = [-H, H]$.
   (b) Two more lines in the directed sums, after `add_ball_2_2`:
   `zd = eq(z0, 0); dd = select(zd, 0, d)`, and `dd` in place of `d`. It is sound because the
   bound of `add_2_2` is relative: a computed sum of zero means the exact sum is zero. Then a
   sum whose result is zero is exactly zero, as for one limb, and `certainly_zero` can be true
   of a computed interval. *Recommended: (b)* for the sums; the products already have their
   zero rule.
3. **An overflow in a two-limb interval kernel.** (a) The infinite bound on that side, hence
   the whole line when both overflow. (b) Keep a finite bound of the right sign,
   $2^{e_{\max}-2}$, which the proved conditions of Milestone 1 justify; it needs a constant of
   the top of the range in the IR. *Recommended: (a) now*; (b) if a use for the sign at
   overflow appears.
4. **The exported bound as a function of $n$.** (a) A generated kernel in `T` arithmetic, as
   above: proved, valid up to about $n\varepsilon \le \tfrac14$, and above $\gamma$ by the
   factor $(1 + 2x)(1 - x)$ with $x = n\varepsilon$: a few $u$ when $x$ is small, an eighth at
   $x = \tfrac14$. (b) The
   exact $\gamma_{n-1}(\varepsilon)$ rounded up, computed with the integers of `rational`:
   the smallest number of `T`, valid for all $n\varepsilon < 1$, tested for equality, not
   machine-checked. *Recommended: (a)*: a bound that a program builds its own proof on should
   be on the proved side.
5. **How `rational` is recorded.** (a) A deviation and a test for equality. (b) The same, and
   the checker run in every constant evaluation. *Recommended: (b) if the checker's cost at
   compile time is small*, to be measured; (a) otherwise.
6. **Products below $2^{2p-1}\eta$.** (a) One number wider, as decided. (b) Rescale the
   operands by a power of two when the product is in that range, as `kv` does, and get the
   exact rounding everywhere; four to six more operations and two selects, and a proof by
   cases. *Recommended: (a)*; the range is below $10^{-291}$ for `double`.
7. **An empty state for `BallVector`.** (a) None: two states, as the first client has.
   (b) One, a NaN radius, as for `Ball`. *Recommended: (a)*: every batch kernel would carry a
   third state for a set that no operation of this milestone produces.
8. **Exact predicates for `Ball<T, 2>`.** (a) Certain, as above. (b) Exact, with the sign of a
   sum of five limbs by an exact expansion of fixed length. *Recommended: (a)*; (b) belongs
   with the arithmetic of four limbs.
9. **Predicates on the empty set.** (a) False and *unknown*, as above. (b) Vacuous truth, as
   the relations of the standard. *Recommended: (a)* for `certainly_*` and the three-valued
   comparisons, (b) only for the functions named after the standard's.
10. **The midpoint of a half-line.** (a) $\pm\Omega$, as the standard. (b) Something else in
    the interval. *Recommended: (a)*.
11. **The conversions between limb types.** (a) Generated, with two formats in the IR.
    (b) Written by hand in the header, argued and tested, as `ldexp`'s steps. *Recommended:
    (a)*, moved to the next milestone if it does not fit.
12. **An accumulator of unnormalized limbs.** Not stated. Options: leave it to a later
    milestone; or state the bound of cascaded summation as a target now and prove it with
    three and four limbs. *Recommended: later*, with a benchmark first of what it would save.
13. **The inlining macro**: its name and its three values, and whether "outlined" should be
    the default for `Interval<T, 2>`, whose product is several hundred operations.
    *Recommended:* the default stays "inline" for everything of at most two limbs but
    `interval_mul_2` and the folds, which are plain inline functions from the start.
14. **The entry forms.** (a) Seven guarded kernels, as above. (b) Document a precondition
    ("do not pass a product"). *Recommended: (a)*: rule R3 exists because (b) fails silently.
15. **The steps of `interval_mul_1`.** (a) Eight, as decided. (b) Choose the least and the
    greatest of the four pairs $(p, e)$ by the comparison of pairs, then one step each; the
    undecided case below $2^{2p-1}\eta$ has to be carried in the pair. *Recommended: (a) now*,
    (b) as an optimization with its own proof once a benchmark shows the steps dominate.
16. **`lower_as<U>` for a limb type `U` other than the enclosure's.** It needs the conversions
    of question 11; until then only `U = T`.
17. **The band test of the directed product**: `lt(ap, P)` with the new lemma, or `le(ap, P)`
    with Flocq's lemma only and a statement that excludes $\lvert ab\rvert = P$.
    *Recommended:* the first; the second is the fallback.
18. **The cases of ITF1788.** (a) Convert the Apache-licensed files and keep them in
    `tests/`, with their notices. (b) Do not store them; run them from a checkout.
    *Recommended: (a)*, for those files only.
19. **The guard on arrays of `T`.** A sum of one-limb numbers over an array the program filled
    is one addition per element, and the guard of rule R3 doubles it. (a) Guard, as for two
    limbs: the exported bound then holds of the values in the array whatever the compiler
    does. (b) Treat one limb as [D6](phase0/decisions.md#d6-one-limb-and-contraction-under-clang)
    does, like `T`: no guard, and a statement that allows a product of the program to be fused
    into the sum. *Recommended: (a)*, measured before it is final: in packed code the guard is
    one more addition per register, and a bound that a compiler setting can falsify is not one.

## Experiments

Everything is in
[`experiments/milestone2/`](https://github.com/danielepanozzo/kairn/tree/main/experiments/milestone2):
the proposed kernels as descriptions in the generator's format (`kernels/`), evaluated by the
generator's exact interpreter, and one script per group of statements, which judges them with
exact rationals. The recorded output of each script is in `results/`.

| Script | Judges | On |
|---|---|---|
| `directed_1.py` | the directed sums and products of one limb; `two_sum` in place of `two_sum_ord` | every pair of values of nine formats, 2 to 5 bits |
| `interval_1.py` | I1 to I5 for `Interval<T, 1>`, and its constructor | every pair of intervals of two formats; samples of three |
| `directed_2.py` | the bounds of two limbs: normalization, side, both forms of the tightness; `Fast2Sum` without ordering | 2.0 million cases, 3 to 6 bits |
| `interval_2.py` | I1 to I5 for `Interval<T, 2>` | 12 000 to 39 000 pairs per operation and format |
| `enclosure_1.py`, `enclosure_2.py` | midpoint and radius, the conversions, `split`, the ball from an interval, the exact and the certain predicates | every value of four or five formats; samples for two limbs |
| `scaling.py` | the exact scaling of a ball; `next_up` and `next_down` on every value; the two executions of a product | every case of four formats |
| `batch.py` | the tree theorem, `dot`, the bound kernels, the radii of `BallVector`, the product of polynomials | random cases at 4 to 6 bits; counts up to $2^{52}$ in `binary64` |
| `rational.py` | the integer algorithm of `rational` against its specification | 80 060 results per limb type; three toy formats |
| `convert.py` | the conversions between a wide and a narrow format | five pairs of toy formats |
| `constants.py` | $A$ and $B$ in `binary64` and `binary32` | exact |
| `rules_report.py` | the generator's own rules on the 32 descriptions | no refusal but the absence of claims |

The 32 descriptions pass single assignment, R1, R2, R3, the non-finite cone and the checks of
kinds and constants as the generator has them today; they carry no claims, since the claims
need the vocabulary this page adds. No statement of this page, as it stands, fails in any run.
Three were *changed* by a run before they were written here: the renormalization of the
two-limb bounds, the second limb of `rational`, and the conversion to a narrow format at the
top of its range.

Two more were false as first written and no run had caught them, because the cases lay outside
what the scripts ran. A separate reading of the mathematics of this page, made without the
scripts' conclusions, found them: the underflow term of the conversion of two wide limbs, which
was $\tfrac12\eta$ and holds only when $u_w \le u^2$; and the comparisons of balls of one limb
that are not strict, which were wrong when both sides overflow. Both are corrected above, and
`convert.py` and `enclosure_1.py` now run the cases that show them. The lesson for the
milestone is the one of Milestone 1: a statement is tested on formats chosen to break it, by
someone who did not write it, before anyone tries to prove it.
