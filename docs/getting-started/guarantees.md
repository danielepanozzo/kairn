# What holds today

Kairn's public headers cover `Expansion<T, 1>`, `Expansion<T, 2>` and `Ball<T, 1>`, `Ball<T, 2>`
for `T` = `float` and `double`. This page says, for each operation, what is proved, what the
library returns at overflow and for infinite and NaN values, and what is not proved yet. It
describes the repository as `gen/claims.json` stands in this version; the compiler enforces the
current status on its own (below), so the code cannot fall behind it. The design is in the
[Phase 0 report](../developer/design/phase0/index.md) and the
[Milestone 1 statements](../developer/design/milestone1.md).

Notation, from [Numbers](../developer/design/phase0/numbers.md#notation): $u = 2^{-p}$ is the unit
roundoff of a limb ($2^{-53}$ for `double`, $2^{-24}$ for `float`), $\eta$ its smallest
subnormal number ($2^{-1074}$, $2^{-149}$), and $2^{e_{\max}}$ its overflow threshold ($2^{1024}$,
$2^{128}$). A two-limb number is *normalized* when its leading limb is the sum of the two rounded
to nearest, and *canonical* when it is finite and normalized, or $(\pm\infty, 0)$, or
$(\mathrm{NaN}, \mathrm{NaN})$. Every constructor and operation returns canonical numbers and
requires canonical operands; a one-limb number is any value of `T`.

## Proved, and UNVERIFIED

Every operation is computed by one generated kernel, and `gen/claims.json` says what that kernel
claims and whether its claims are **proved**: Rocq accepts a proof of the generated statement, and
the audit finds no axiom beyond the four allowed
([Architecture](../developer/architecture.md#the-formal-model)). Any other kernel is
**UNVERIFIED**: its statement is a target, tested by the oracle in exact arithmetic but not proved.

An UNVERIFIED operation compiles only when one of its operands carries the marker
`kairn::unverified(...)`: `kairn::unverified(x) - y`, `kairn::unverified(x) < y`,
`kairn::to_down(kairn::unverified(x))`, `x -= kairn::unverified(y)`,
`kairn::Expansion<double, 2>(kairn::unverified(a))`. The marker applies to the one operation it is
an operand of, and the result is an ordinary value, so each unproved step of a computation is
visible in the source. It may be put on a `float` or `double` operand too (it converts back to that
type), so that code generic over `T` and the k-numbers can be written once, and it is accepted on
proved operations as well, so that code written with it keeps compiling when a proof lands. A
marked left operand of `+=` does not compile: it would modify a copy. `from_limbs` has no marked
form, since its operand is a pointer.

Each operation is gated on the kernel it really calls, constructors and the narrowing to one limb
included, and no operation can compile through a conversion to another kernel: `x + a` with a
limb `a` is the form of `add_2_1_full`, never `x + Expansion(a)` with `add_2_2_full`, and a ball
times a `T` is the scaling, never a product with a point ball. The tests compile each such case
against a copy of the headers in which only that kernel is UNVERIFIED (`api.reject.*`).

Which kernels are proved is read from `include/kairn/gen/bounds.hpp`, which the generator writes
from `gen/claims.json`. When a proof is checked and the generator is rerun, the operation compiles
without the marker. `kairn::traits` exports error constants only for proved operations: the entry
of an UNVERIFIED one has `verified == false` and no constants to read, so that no client bound can
be built on a number that is only a target.

In this version every kernel of one and two limbs is proved, so no operation of these headers
needs the marker. It is how the operations still to come (three and four limbs, division, square
root) will ship before their proofs.

## The operations

Each kernel has a page in the [reference](../reference/index.md), generated from
`gen/claims.json`: its statement, the theorem and file that prove it, its constants for `float`
and `double`, and what the brute-force runs measured. In short, for canonical operands $x$, $y$
and a limb $a$, with $z$ the result. The second column is the claim of the kernel's finite core,
proved in the *real model*, where no operation overflows; it is what a result satisfies whenever
it is finite. The third column is proved in Flocq's model of IEEE 754, where operations overflow
and values may be infinite or NaN ([below](#overflow-and-non-finite-values)).

| Operation (kernel) | When the result is finite, proved in the real model | Infinities, NaN and overflow, proved in the IEEE model |
|---|---|---|
| `x + y` (`add_2_2_full`) | $z$ normalized, $\lvert z - (x + y)\rvert \le \frac{3u^2}{1 - 4u}\lvert x + y\rvert$ | F1 to F5; finite when $\lvert x\rvert, \lvert y\rvert \le 2^{e_{\max}-2}$ |
| `x * y` (`mul_2_2_full`) | $z$ normalized, $\lvert z - xy\rvert \le 4u^2\lvert xy\rvert + \tfrac32\eta$ | F1 to F5; finite when $\lvert xy\rvert \le 2^{e_{\max}-1}$ |
| `x + a`, `a + x` (`add_2_1_full`) | $z$ normalized, $\lvert z - (x + a)\rvert \le 2u^2\lvert x + a\rvert$ | F1 to F5; finite when $\lvert x\rvert, \lvert a\rvert \le 2^{e_{\max}-2}$ |
| `x * a`, `a * x` (`mul_2_1_full`) | $z$ normalized, $\lvert z - xa\rvert \le 2u^2\lvert xa\rvert + \eta$ | F1 to F5; finite when $\lvert xa\rvert \le 2^{e_{\max}-1}$ |
| `add_fast(x, y)` (`add_fast_2_2_full`) | $z$ normalized, $\lvert z - (x + y)\rvert \le 3u^2(\lvert x\rvert + \lvert y\rvert)$ | F1 to F5; finite as for `x + y` |
| `x - y`, `x - a`, `a - x` (`sub_2_2_full`, `sub_2_1_full`, `sub_1_2_full`) | those of `x + y` and `x + a` | F1 to F5; finite as for `x + y` and `x + a` |
| `ldexp(x, n)`, `half(x)` (`mul_pow2_2_full`) | $z$ normalized, $\lvert z - 2^n x\rvert \le \eta$ | F1 to F5; finite when $\lvert 2^n x\rvert \le 2^{e_{\max}-1}$ |
| `-x`, `abs(x)` (`neg_2`, `abs_2`) | exact, normalized | exact: the infinity with its sign changed or removed; NaN stays NaN |
| `<`, `<=`, `>`, `>=`, `==`, `!=` (`lt`, `le`, `eq` kernels) | the truth about the exact values | the truth in the extended reals; false with a NaN, as for `T` (`!=` true) |
| `to_nearest`, `to_down`, `to_up`, `abs_upper` (`to_nearest_2`, ...) | the exact rounding to `T` | the rounding with overflow ($\pm\infty$ beyond the largest finite `T`); an infinity or NaN gives itself |
| constructors (`make_2`, `make_2_limbs`, `ball_make_1`, `ball_make_2`) | | the value given, canonical; for a ball, below |
| one limb: `+`, `-`, `*`, `add_fast`, `ldexp`, `half` (`add_1_1`, `mul_1_1`) | one rounding to nearest: $\lvert z - v\rvert \le \frac{u}{1 + u}\lvert v\rvert$, plus $\tfrac12\eta$ for products | the IEEE 754 operation |
| one limb: `-x`, `abs`, comparisons, conversions | exact (no kernel) | the IEEE 754 operation |
| `Ball`: `+`, `-`, `*`, scaling by a `T`, `-X` (`ball_add_1_full`, ..., `ball_neg_2`) | containment: $x \circ y \in Z$ for all $x \in X$, $y \in Y$; for two limbs the center is normalized | B1 to B3: containment in every case, the empty set and the whole line included |
| `limb`, `sign`, `isfinite`, `is_normalized`, a ball's states | exact (no kernel) | |

A one-limb operand next to a two-limb one is its limb: `x + y` with `y` an `Expansion<T, 1>` is
`x + a`, through `add_2_1_full`. The claims hold for every precision from the kernel's minimum on
(at most 4), so for `float` and `double` alike. The constants of every row with an error bound,
rounded up to `T`, are in `kairn::traits<kairn::Expansion<T, 2>>` (`add`, `add_limb`, `add_fast`,
`sub`, `sub_limb`, `mul`, `mul_limb`, `ldexp`) and `kairn::traits<T>`: they are the bounds of the
cores, which a result satisfies whenever it is finite.

## Overflow and non-finite values

**Two-limb arithmetic returns IEEE-like results** (decision
[D5](../developer/design/phase0/decisions.md#d5-non-finite-results)): every operator calls a
*full kernel*, the finite core of the operation followed by a fix-up of one operation of `T` on
the leading limbs, two tests and selects
([IEEE-like results](../developer/design/milestone1.md#ieee-like-results)). For canonical
operands, with $w$ the result:

- **F1.** $w$ is canonical.
- **F2.** If $w_0$ is finite, every operand is finite and $w$ satisfies the claim of the core: no
  overflow inside the kernel can produce a finite wrong result.
- **F3.** If every operand is finite and the condition of the table holds, $w_0$ is finite.
- **F4.** If every operand is finite and $w_0$ is not, $w = (\pm\infty, 0)$ with the sign of the
  exact result.
- **F5.** If an operand is not finite, $w$ is the canonical form of the operation of `T` on the
  leading limbs: $+\infty + 1 = +\infty$, $\infty - \infty = \mathrm{NaN}$,
  $0 \cdot \infty = \mathrm{NaN}$; which NaN is not specified.

**`kairn::finite::`** is the opt-out: `add`, `sub`, `mul`, `add_fast` and `ldexp` on the same
operand types as the operators, calling the cores without the fix-up. Their contract is the
cores': either the leading limb of the result is not finite, or the result is normalized and
within its bound; which non-finite pattern comes out (it may be $(+\infty, \mathrm{NaN})$) is not
specified, and such a result is not canonical, so test it with `kairn::isfinite` before passing it
to an operator. For one limb they are the operators themselves.

**`ldexp(x, n)` is defined for every $n$.** When $2^n$ is a number of `T` it is one call of the
kernel, with the proved statements of the table. Otherwise ($n$ above 1023 or below $-1074$ for
`double`) the header calls the kernel two or three times, each time with a power of two of `T`.
The result is canonical, and normalized when it is finite; that much follows from the proved
statements of each call. Two more statements hold by an argument that is written out in the
design and tested through the oracle, but is **not machine-checked**
([Scaling beyond the powers of two of the format](../developer/design/milestone1.md#scaling-beyond-the-powers-of-two-of-the-format)):
scaling up, the result is $2^n x$ exactly or $(\pm\infty, 0)$ on overflow; scaling down,
$\lvert z - 2^n x\rvert \le \eta$, the bound of one call. For one limb, the same steps give
$\mathrm{RN}(2^n x)$, what `std::ldexp` returns.

**A `Ball` is in one of three states**, each a set of real numbers: a *finite ball*, the reals
within its radius of its center (center finite, radius finite and $\ge 0$); the *whole line*,
every real (center 0, radius $+\infty$); the *empty set* (every limb a NaN). `X.is_finite()`,
`X.is_whole()` and `X.is_empty()` say which, and `Ball<T, K>::whole()` and `Ball<T, K>::empty()`
make the last two. A constructor gives the empty set for a NaN or negative radius, and the whole
line for a center that is not finite or a radius of $+\infty$; in a build with `KAIRN_CHECKS`, a
negative radius is reported, since it is almost surely a mistake. Every Ball operation calls a
*full Ball kernel*, which proves, for canonical operands: **B1** the result is canonical; **B2**
it is empty exactly when an operand is empty; **B3** if it is a finite ball, every operand is a
finite ball, every scalar finite, and the result contains $x \circ y$ for every $x$, $y$ of the
operands. So in every case the result contains every $x \circ y$, the whole line counting as
containing everything ([Ball kernels](../developer/design/milestone1.md#ball-kernels)). A point
operand, a `T` or an `Expansion` of as many limbs, is the ball of radius 0 its constructor makes;
times a ball, a `T` (and for one limb, an `Expansion<T, 1>`) is the scaling, a kernel of its own.

**What is proved, and in which model.** Every error bound, normalization, exact comparison,
rounding and ball containment is proved in the real model, where nothing overflows; F1 to F5, B1
to B3, and what the comparisons, conversions and constructors return for infinities and NaN are
proved in Flocq's model of IEEE 754, against statements the generator prints from the same kernel
descriptions as the C++ ([Proofs](../proofs/index.md#what-is-proved-and-in-which-model); each
kernel's page in the [reference](../reference/index.md) gives its theorem).

**Not proved yet.** The two statements about `ldexp` when $2^n$ is not a number of `T`, above.
When the result of a Ball operation on finite balls is guaranteed to be a
finite ball rather than the whole line (B4): no such condition is proved, so a program cannot yet
rely on a finite ball coming out. And thresholds sharper than those of the table: exhaustive runs
on small formats first see an overflow at 0.55 of the overflow threshold or above for the
additions and 0.86 or above for the products, where the proved conditions are a quarter and a half
of it ([Milestone 1](../developer/design/milestone1.md#what-is-proved-about-an-arithmetic-kernel)).

**Cost.** The fix-up was measured
([Benchmarks](../developer/results/bench-milestone1.md#2-the-fix-up-for-non-finite-results)) at
19 to 58% of a packed addition and 70 to 106% of a packed product, and at 0 to 6% in a chain of
dependent scalar operations when it is emitted behind a branch. The generator emits the scalar
code in the select form of the listings for now, which costs more in a chain (up to 47% with
Apple clang, 76% with MSVC); emitting it behind a branch is a later step of the generator. The
full Ball kernels, measured with the first radius design, cost 4 to 39% over their cores in
throughput and up to 2.9 times in a chain, where their selects make the next center wait for the
radius.

## Products the program passes in

Kairn's kernels are written so that no compiler can fuse a product into one of their additions
(rules R1 and R2 of [Environment](../developer/design/phase0/environment.md#the-rule-no-product-feeds-an-addition)),
and the tests check that under every contraction setting. A product computed by the program
itself and passed in, as in `x + a * b`, needs one more step: a compiler that contracts across
statements (GCC's default for C++, `-ffp-contract=fast`, MSVC's `/fp:contract`) could otherwise
fuse `a * b` into the error-free sums inside the kernel, which would then not be error-free.
Without that step, the result was measured normalized and wrong by about $2^{-24}$ relative to
itself, on GCC 13 and 16 by default, on Apple clang with `-ffp-contract=fast`, and on MSVC with
`/fp:contract`.

So every value of type `T` that the program supplies passes through a *guard*, an addition of
$+0$, before any kernel adds it: rule R3 of the
[kernel IR](../developer/architecture.md#the-kernel-ir), which the generator enforces. A product
plus $+0$ is at most fused into one FMA that rounds the product, and its result is a sum, which
nothing later can fuse; a compiler that honors signed zeros cannot remove the addition. The guard
is in the kernels that receive such a value: `add_2_1` (and through it `sub_2_1`, `sub_1_2` and
their full kernels) on its limb operand, and the constructors `make_2`, `make_2_limbs`,
`ball_make_1` and `ball_make_2` on what they are given. A limb operand that a kernel only
multiplies or compares needs none (`x * a`, comparisons, the scaling of a ball, `ldexp`). Limbs
written directly into `limb[]` are not guarded: a limb written that way must not be a product the
compiler can see being computed; `from_limbs` is the way to build a number from computed values.

So the program may pass its own products to Kairn under every contraction setting. The test
`api.boundary.*` checks each guarded form with the product written in the call against the same
operation on the rounded product, bit for bit, under each contraction setting of the compiler, and
`api.boundary.unguarded.*` builds the same test against a copy of the headers with the guard taken
out of the generated kernels, and checks that the compilers above do fuse then. A guarded $-0$
enters as $+0$; Kairn leaves the sign of a zero unspecified anyway.

One-limb values themselves are not guarded: they behave like `T`, contraction included, so an
expression such as `p * q + r` on `Expansion<double, 1>` may be evaluated with one rounding where
the compiler contracts, exactly as for `double`.

The flag `-fno-signed-zeros` lets a compiler remove the guard and fold the opaque products of the
kernels back into plain ones. GCC rejects it at compile time (`config.hpp`); Clang defines no
macro for it, and with `-ffp-contract=fast` on AArch64 it breaks the two-limb products, which
`kairn::self_test()` reports. It is not supported.

## Constant evaluation

`constexpr`: the constructors, the sums and differences of two limbs (their full kernels, whose
fix-up evaluates at compile time), negation and absolute value, the comparisons and conversions,
every operation of one limb, a ball's negation, states and constants, and `kairn::finite::add`,
`sub` and `add_fast`. Not yet: the products of two limbs, `ldexp` and `half` on two limbs, and the
Ball arithmetic, whose kernels contain fused operations without a constant-evaluation variant.
The canonical infinities and NaN come out of the constructors at compile time
(`Expansion<double, 2>(INFINITY)` is $(+\infty, 0)$), and so do the states of a ball. GCC and
Clang refuse, at compile time, an operation that produces an infinity from finite operands or a
NaN, so an overflowing sum or an operation on an infinity is not a constant expression there,
though it is evaluated as stated at run time. In constant evaluation the guard is not applied
(nothing is fused there), so a $-0$ keeps its sign. One compiler's constant evaluator takes
`a < b` for true when an operand is a NaN: every comparison that can run at compile time, in the
generated kernels and in the headers, is written `b > a` or `b >= a`, and `api.constexpr` checks
the comparisons with NaN operands.

## One limb

`Expansion<T, 1>` is meant to cost what `T` costs. Measured by the test `api.k1.zero_cost`, which
compares the instructions emitted for three loops over `double` and over `Expansion<double, 1>`:
identical or fewer with GCC, and with Clang under `-ffp-contract=off` or `=fast`; under Clang's
default contraction a product followed by a sum is fused for `double` and not for
`Expansion<double, 1>` (decision
[D6](../developer/design/phase0/decisions.md#d6-one-limb-and-contraction-under-clang)), unless the
program defines `KAIRN_K1_CONTRACT`. MSVC does not vectorize a loop over the wrapper where it
vectorizes the loop over `double`.

## The environment

Every guarantee assumes rounding to nearest, no flush to zero, and compiler flags that do not
rewrite floating-point expressions ([Environment](../developer/design/phase0/environment.md)).
Including Kairn fails with `#error` under the flags a macro reveals (`-ffast-math`,
`-ffinite-math-only`, and on GCC `-fassociative-math`, `-fno-signed-zeros`, `-freciprocal-math`;
`/fp:fast` on MSVC). For the rest a program calls `kairn::self_test()` once at startup:

```cpp
--8<-- "docs/examples/cpp/first_steps.cpp:self_test"
```

`kairn::environment_ok()` reads the control register and says whether the rounding mode and
flush-to-zero are in their default state; Kairn never changes them. In a build without `NDEBUG`
(or with `KAIRN_CHECKS` defined to 1), every operation checks the environment and that its
operands are canonical, and stops the program with a message if not.
