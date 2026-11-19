# Milestone 1: overflow, non-finite values, and the second-wave operations

The [architecture page](../architecture.md#kernels-of-the-first-wave) states the first-wave
kernels in a model where exponents are unbounded above. This page adds what Milestone 1 needs on
top: how overflow and non-finite values are treated, formally and in the code, and the remaining
operations. Notation is that of [Numbers](phase0/numbers.md).

**What is proved, and against what.** The statements of the
[second-wave kernels](#second-wave-kernels) and of the [Ball kernels](#ball-kernels) are proved
in the real model against the statements the generator prints, from the precision their tables
give. Every IEEE-model statement of this page is proved too: the full kernels, the kernels that
need no fix-up, the constructors, and the full Ball kernels with the second radius design. Those
proofs too are against what the generator prints: the IEEE model of every kernel
(`proofs/gen/IeeeModel.v`) and its statements (`proofs/gen/IeeeStatements.v`), from the same
kernel descriptions as the C++. Written by hand, and imported by the generated files, are only
the meaning of each operation in Flocq's terms (`proofs/theories/IeeeOperations.v`) and the
vocabulary of the statements (`IeeeVocabulary.v`). Every kernel of `gen/claims.json` is `proved`.
What is not proved is said where it applies: the conditions under which a Ball operation returns
a finite ball (B4), and thresholds sharper than the ones stated.

## Two formal models of one kernel

The generator prints each kernel twice for Rocq:

- **The real model.** Values are real numbers of the format, exponents are unbounded above, and
  each operation is "exact result, rounded". All error analysis is done here; it is the model of
  the first wave.
- **The IEEE model.** Values are Flocq's `binary_float`: finite numbers with signed zeros, the two
  infinities, and NaN, with Flocq's own definitions of the IEEE 754 operations (`Bplus`, `Bmult`,
  `Bfma`, the comparisons), overflow included. This is the model that matches the machine, and
  the final theorems are stated in it.

Why two: the error analysis in the literature and in Flocq's library is written over real
numbers, while only the IEEE model can say what happens at overflow or with an infinite operand.

## What is proved about an arithmetic kernel

Let $K$ be a kernel made only of additions, subtractions, opaque products, fused operations and
sign changes, ending with a `fast_two_sum` whose sum is output limb 0 (every first-wave
arithmetic kernel is), with finite normalized operands.

1. **Bridge.** If output limb 0 of the IEEE model is finite, then every intermediate value was
   finite, and the outputs are equal, as real numbers, to those of the real model.
   *Why it holds:* each of those operations returns a non-finite value when an operand is not
   finite, and the generator's cone rule guarantees that every value computed before output
   limb 0 reaches it. The two values computed after it, the tail of the final `fast_two_sum`,
   need a different argument: if the first of them overflowed, the second limb would be at least
   $2^{-p}$ times the overflow threshold, which a normalized result excludes; and the result is
   normalized by the real-model theorem.
2. **Correctness.** Therefore either $z_0$ is not finite, or $z$ is normalized and satisfies the
   bound of the real-model theorem. No finite wrong result can come out of an intermediate
   overflow.
3. **No spurious overflow.** Under a threshold that is part of the statement, every value is
   finite. This is a statement about the real model alone: it says that every value there is at
   most $\Omega$ in magnitude.

The bridge is proved once, for every such kernel: a kernel is also a list of instructions, the
cone is computed inside Rocq, and one theorem covers all lists that pass the check
(`proofs/theories/IeeeBridge.v`). Per kernel there remain two lemmas proved by computation and one
application of that theorem, which the generator can print. Statement 3 is a magnitude analysis
written per kernel.

| Kernel | Bridge and correctness | No spurious overflow, proved for | What exhaustive runs show |
|---|---|---|---|
| `add_2_2`, `sub_2_2`, `add_fast_2_2` | proved | leading limbs of both operands at most $2^{e_{\max}-2}$ (a quarter of the overflow threshold), whatever the result; or exact result at most $2^{e_{\max}-2}$, whatever the operands | smallest exact result at an overflow: 0.62 of the threshold at $p = 3$, 0.55 at $p = 4$ |
| `add_2_1`, `sub_2_1`, `sub_1_2` | proved | the same two conditions, with the one-limb operand in place of a leading limb | 0.67 at $p = 3$, 0.58 at $p = 4$ |
| `mul_2_2`, `mul_2_1`, `mul_pow2_2` | proved | exact product at most $2^{e_{\max}-1}$ in magnitude, whatever the operands | 0.90 for `mul_2_2` at $p = 4$; 0.86 to 0.93 for `mul_2_1`; 0.88 to 0.97 for `mul_pow2_2` |
| `two_sum`, `fast_two_sum`, `two_prod` | proved, in the form below | | |

Here $2^{e_{\max}}$ is the overflow threshold, just above $\Omega$. The last column is measured
by complete enumeration of small formats and is not proved: the proved thresholds are a quarter
of the overflow threshold for the additions and half of it for the products, and overflow was
first seen above 0.55 and 0.86. These theorems have generated statements as their types
(checked through `proofs/audit/HandAudit.v`, since the generated audit lists one theorem per
kernel). The kernels with comparisons, selects, `pred` or `succ`
do not fit the bridge: for them "a non-finite value stays non-finite" is false, and they have
statements of their own in the IEEE model ([below](#ieee-like-results)).

**The error-free transformations at the top of the range.** `fast_two_sum` and `two_prod` have a
finite error term whenever their first output is finite. `two_sum` does not: with Kairn's order of
operations its error term is finite exactly when the sum is finite and the second operation,
$\mathrm{RN}(s - a)$, does not overflow. That it suffices for the second operand to be below
$\Omega$ in magnitude is proved; exhaustive runs show that the failing pairs all have the second
operand equal to $\pm\Omega$. Any threshold below $\Omega$ on the leading limbs therefore keeps
this corner out of statement 3.

**Which formats.** Flocq's IEEE formats have $q_{\min} + q_{\max} = 3 - 2p$, as `binary32` and
`binary64` do. The IEEE-model theorems are for those formats, and toy formats used to test them
must have that shape.

## IEEE-like results

By decision [D5](phase0/decisions.md#d5-non-finite-results), `Expansion` arithmetic returns
canonical infinities and NaN the way `T` does, and the `kairn::finite::` variants skip that.

**Canonical values.** A 2-limb value is *canonical* when it is finite and normalized, or
$(\pm\infty, 0)$, or $(\mathrm{NaN}, \mathrm{NaN})$. The zero after an infinity may have either
sign. A one-limb value is any value of `T`.

**The full kernel.** Each arithmetic kernel $K$ of two limbs is a *finite core*. The generator
emits a second kernel `K_full`: the core followed by a fix-up made of one operation of `T` on the
leading limbs, two tests and selects. `0` is the literal zero, `const inf` is $+\infty$, and
`times_inf` multiplies by $+\infty$: a plain multiplication, exact, whose result is only compared
or selected, so that no fused operation is needed and the fix-up can be evaluated at compile time.

```
add_2_2_full(x, y) -> w
  (z0, z1) = add_2_2(x, y)       the finite core
  t  = add(x0, y0)               the same operation of T, on the leading limbs
  a  = abs(z0)
  f  = lt(a, const inf)          z0 is finite
  r0 = times_inf(t)              a NaN or a zero gives a NaN; any other t the infinity of its sign
  n  = eq(r0, r0)                r0 is not a NaN
  r1 = select(n, 0, r0)
  w0 = select(f, z0, r0)
  w1 = select(f, z1, r1)
```

The other full kernels differ in their first lines only. With a one-limb operand `a` that is
added or subtracted, the first line is `g = guard(a)` and `t` is computed from `g`
([values that enter from the program](#values-that-enter-from-the-program)); the core is called
with `a` and guards it itself, which compilers merge with the first guard. Where an input is
already named `a`, the temporary of the fix-up is named `az`.

| Full kernel | Core | `t` |
|---|---|---|
| `add_2_2_full`, `add_fast_2_2_full` | `add_2_2`, `add_fast_2_2` | `add(x0, y0)` |
| `sub_2_2_full` | `sub_2_2` | `sub(x0, y0)` |
| `add_2_1_full`, `sub_2_1_full`, `sub_1_2_full` | `add_2_1`, `sub_2_1`, `sub_1_2` | `add(x0, g)`, `sub(x0, g)`, `sub(g, y0)` |
| `mul_2_2_full`, `mul_2_1_full`, `mul_pow2_2_full` | `mul_2_2`, `mul_2_1`, `mul_pow2_2` | `prod(x0, y0)`, `prod(x0, a)`, `prod(x0, c)` |

`operator+` and the other operators of `Expansion<T, 2>` call the full kernels;
`kairn::finite::add` and its siblings call the cores.

**Statement of a full kernel, in the IEEE model.** The 2-limb operands are canonical; a one-limb
operand is any value of `T`, except the `c` of `mul_pow2_2_full`, which is required to be a
finite power of two (nothing is stated for another `c`).

- **F1.** $w$ is canonical.
- **F2.** If $w_0$ is finite, then every operand is finite and $w$ satisfies the statement of the
  core: it is normalized and within the bound.
- **F3.** If every operand is finite and the kernel's *finite when* condition holds, then $w_0$
  is finite. The conditions are those of [statement 3](#what-is-proved-about-an-arithmetic-kernel)
  of the core; a kernel without a proved condition has none yet.
- **F4.** If every operand is finite and $w_0$ is not, then $w = (\pm\infty, +0)$ with the sign
  of the exact result.
- **F5.** If an operand is not finite, then $w$ is the canonical form of $t$, the result of the
  operation of `T` on the leading limbs: $+\infty + 1 = +\infty$, $\infty - \infty = \mathrm{NaN}$,
  $0 \cdot \infty = \mathrm{NaN}$. An infinity is followed by $+0$; which NaN is returned is not
  specified.

*Why it holds.* `f` is true exactly when $z_0$ is finite. By the bridge, a finite $z_0$
means every value of the core was finite and equal to the real model's, which gives F2 for
finite operands; and an operand that is not finite makes $z_0$ not finite, because the leading
limb of every operand reaches $z_0$ through operations that keep a NaN and turn an infinity into
an infinity or a NaN. So with such an operand the result is built from $t$, which is then a NaN
or an infinity: F5. F4 needs one more fact: when a core overflows on finite operands, $t$ is not
zero and has the sign of the exact result. It follows from two facts proved about the cores: an
addition does not overflow when the exact result is at most $2^{e_{\max}-2}$ in magnitude, so at
an overflow the sum of the leading limbs has the sign of the exact result; and a product kernel
does not overflow when the leading product rounds to zero.

*Status.* F1 to F5 are proved for the nine full kernels, from the minimum precision of each
core, with the conditions of F3 given in the
[table above](#what-is-proved-about-an-arithmetic-kernel), stated on the exact values of the
operands (for the additions: both operands at most $2^{e_{\max}-2}$ in magnitude; for the
products: the exact product at most $2^{e_{\max}-1}$). They were first checked on every operand
of small formats, non-finite operands included.

**Kernels that need no fix-up.** Their listings already do the right thing on canonical
operands. What that is is stated and proved in the IEEE model directly, because they contain
comparisons, selects and steps to a neighbor, for which "a non-finite value stays non-finite" is
false.

| Kernels | On canonical operands |
|---|---|
| `neg_2`, `abs_2` | the result is canonical: the infinity with its sign changed or removed; a NaN stays a NaN |
| `lt`, `le`, `eq` (all forms) | the comparison of the two values as extended real numbers; false when an operand is a NaN, as for `T` |
| `to_nearest_2` | $x_0$ |
| `to_down_2`, `to_up_2`, `abs_upper_2` | for a finite $x$, the rounding in the sense of `T`, which is $\pm\infty$ when the neighbor of $\pm\Omega$ is needed; an infinite or NaN $x$ gives itself (its absolute value for `abs_upper_2`) |
| `radd`, `rmul` | for operands that are nonnegative, $+\infty$ or NaN: a NaN when an operand is a NaN or the product is $0 \cdot \infty$; otherwise a value not below the exact one, $+\infty$ on overflow |

**Emission.** Packed code is emitted as listed, with blends. For scalar code the generator may
emit the fix-up behind a branch on `f`; the two forms compute the same function. Measured
([benchmarks](../results/bench-milestone1.md)): as listed, the fix-up costs 19 to 58% of a packed
addition and 70 to 106% of a packed multiplication, above the 10 to 20% that D5 expected; behind
a branch it costs 0 to 6% in a chain of dependent scalar operations.

## Values that enter from the program

Rule [R3](../architecture.md#the-kernel-ir): a value of `T` that the program supplies passes
through `guard` (an addition of zero) before any kernel adds or subtracts it, because the program
may have computed it as a product that a contracting compiler would otherwise fuse into the
kernel. `guard(a)` has the value of `a`; a zero comes out positive, an infinity and a NaN stay
what they are.

**Kernels with a scalar operand.** `add_2_1` guards its one-limb operand in its first line; its
listing is otherwise unchanged:

```
add_2_1(x, a) -> z
  g        = guard(a)
  (sh, sl) = two_sum(x0, g)
  v        = x1 + sl
  (z0, z1) = fast_two_sum(sh, v)
```

`sub_2_1` and `sub_1_2` pass their one-limb operand (negated, for `sub_2_1`) to `add_2_1` and to
nothing else, so they are covered by its guard and do not change. The operands that kernels only
multiply or compare (`a` in `mul_2_1` and in the comparisons, `c` in `mul_pow2_2`, the scalar of
`ball_scale`) need no guard. The building blocks (`two_sum`, `fast_two_sum`, `two_prod`, `radd`,
`rmul`, `add_1_1`, `mul_1_1`) are not entry kernels and are not guarded: inside Kairn their
operands are never the program's products (R1).

**Constructors** are entry kernels too, so that no limb of an object is ever a value the compiler
can still fuse:

```
make_2(a) -> x                     make_2_limbs(h, l) -> x          ball_make_2(c, r) -> (cw, rw)
  x0 = guard(a)                      x0 = guard(h)                    g   = guard(r)
  n  = eq(x0, x0)                    x1 = guard(l)                    e   = le(0, g)
  x1 = select(n, 0, x0)                                               a   = abs(c0)
                                                                      f1  = lt(a, const inf)
                                                                      f2  = lt(g, const inf)
                                                                      f   = and(f1, f2)
                                                                      k0  = select(f, c0, 0)
                                                                      k1  = select(f, c1, 0)
                                                                      s   = select(f, g, const inf)
                                                                      cw0 = select(e, k0, const nan)
                                                                      cw1 = select(e, k1, const nan)
                                                                      rw  = select(e, s, const nan)
```

- `make_2(a)` is `Expansion<T, 2>` from a value of `T` or from a one-limb number: the result is
  canonical and has the value of `a`. Because of the guard, $-0$ gives $(+0, +0)$.
- `make_2_limbs(h, l)` is `from_limbs`: it requires $(h, l)$ to be canonical and returns limbs of
  the same values (a zero limb may change sign).
- `ball_make_2(c, r)` takes a canonical center (an object, `stored`) and a radius from the
  program. The result is canonical: the empty set when the radius is a NaN or negative,
  $-\infty$ included (`e` is then false); otherwise the whole line when the center is not finite
  (an infinity or a NaN) or the radius is $+\infty$; and otherwise the ball itself. `ball_make_1(c, r)` is the same with a one-limb center supplied by
  the program: its first lines are `g = guard(r)` and `c0 = guard(c)`, and it has no `k1` and
  no `cw1`. `const nan` is a quiet NaN.

*Status.* The four constructors are proved in the IEEE model, for every precision. So are the
two facts about the guard that the rest relies on: in the real model $\mathrm{RN}(a + 0) = a$ for
a number of the format; in the IEEE model the guard keeps finiteness and the value, turns a zero
into $+0$, and leaves an infinity or a NaN what it is. With its guard, `add_2_1` is 11
operations where the Phase 0 report counted 10.

## Second-wave kernels

For limb type $T$ and at most two limbs, in the notation of the
[first-wave listings](../architecture.md#kernels-of-the-first-wave): each line is one operation,
value names are normative, a 2-limb operand `x` is `(x0, x1)`, and a one-limb operand is `a`.
`pred` and `succ` are the neighbors in the format; `m`-values are masks. These listings are the
finite cores: what each returns for non-finite operands is added as in
[IEEE-like results](#ieee-like-results).

**Sign changes and subtraction.**

```
neg_2(x) -> z            abs_2(x) -> z                sub_2_2(x, y) -> z
  z0 = neg(x0)             m  = lt(x0, 0)               n0 = neg(y0)
  z1 = neg(x1)             n0 = neg(x0)                 n1 = neg(y1)
                           n1 = neg(x1)                 z  = add_2_2(x0, x1, n0, n1)
                           z0 = select(m, n0, x0)
                           z1 = select(m, n1, x1)     sub_2_1(x, a), sub_1_2(a, y): likewise,
                                                      through add_2_1
```

**Comparisons.** Limbs are compared in order.

```
lt_2_2(x, y) -> m                 le_2_2(x, y) -> m                 eq_2_2(x, y) -> m
  h = lt(x0, y0)                    h = lt(x0, y0)                    h = eq(x0, y0)
  e = eq(x0, y0)                    e = eq(x0, y0)                    l = eq(x1, y1)
  l = lt(x1, y1)                    l = le(x1, y1)                    m = and(h, l)
  t = and(e, l)                     t = and(e, l)
  m = or(h, t)                      m = or(h, t)
```

Against one limb `a`, the same with `(a, 0)` in place of the 2-limb operand:
`lt_2_1`, `le_2_1`, `eq_2_1`, `lt_1_2`, `le_1_2`.

**Conversions to one limb.**

```
to_nearest_2(x) -> t     to_down_2(x) -> t          to_up_2(x) -> t           abs_upper_2(x) -> t
  t = x0                   m = lt(x1, 0)              m = lt(0, x1)             (a0, a1) = abs_2(x)
                           p = pred(x0)               s = succ(x0)              t = to_up_2(a0, a1)
                           t = select(m, p, x0)       t = select(m, s, x0)
```

**Directed steps on one limb**, for radii.

```
radd(a, b) -> r          rmul(a, b) -> r
  s = add(a, b)            p = prod(a, b)
  r = succ(s)              r = succ(p)
```

**Scaling by a power of two.** `c` is a limb that is a power of two; `ldexp(x, n)` and `half(x)`
are this kernel with $c = 2^n$. When $2^n$ is not a number of the format, the public `ldexp` calls
the kernel in steps, each with a power of two of the format
([below](#scaling-beyond-the-powers-of-two-of-the-format)).

```
mul_pow2_2(x, c) -> z
  h = prod(x0, c)
  l = prod(x1, c)
  (z0, z1) = fast_two_sum(h, l)
```

All of these are proved in the real model, for every format with $p$ at least the value shown.

| Kernel | Requires | Statement | Holds for |
|---|---|---|---|
| `neg_2`, `abs_2` | $x$ normalized | $z$ normalized; $z = -x$, $z = \lvert x\rvert$ exactly | $p \ge 1$ |
| `sub_2_2`, `sub_2_1`, `sub_1_2` | operands normalized | that of the addition, for $x - y$ | $p \ge 3$ |
| `lt`, `le`, `eq` (all forms) | operands normalized | the mask is the truth of the comparison of the real values | $p \ge 1$ |
| `to_nearest_2` | $x$ normalized | $t = \mathrm{RN}(x)$ | $p \ge 1$ |
| `to_down_2`, `to_up_2` | $x$ normalized | $t$ is the largest number of the format $\le x$; the smallest $\ge x$ | $p \ge 1$ |
| `abs_upper_2` | $x$ normalized | $t$ is the smallest number of the format $\ge \lvert x\rvert$ | $p \ge 1$ |
| `radd`, `rmul` | $a \ge 0$, $b \ge 0$ | $r \ge a + b$, $r \ge ab$; and $r$ exceeds the exact value by at most $\tfrac32$ gaps, where a gap is $r - \mathrm{pred}(r)$ | $p \ge 2$ |
| `mul_pow2_2` | $x$ normalized, $c$ a power of two | $z$ normalized; $\lvert z - cx\rvert \le \eta$ | $p \ge 2$ |
| `add_1_1`, `mul_1_1` | — | $s = \mathrm{RN}(a + b)$ with $\lvert s - (a + b)\rvert \le \frac{u}{1 + u}\lvert a + b\rvert$; $p = \mathrm{RN}(ab)$ with $\lvert p - ab\rvert \le \frac{u}{1 + u}\lvert ab\rvert + \tfrac12\eta$ | $p \ge 1$ |

Notes on three rows:

- **`radd`, `rmul`.** The requirement of nonnegative operands is new: every use in the Ball
  kernels has it, and it gives $\tfrac32$ gaps, which tests reach exactly. For operands of any
  sign the excess reaches 2 gaps in tests (below a negative power of two the gap toward zero is
  half the gap away from it); that case is not claimed.
- **`mul_pow2_2`.** Also proved, as a hand-written statement because the claims cannot express
  its condition yet: $z = cx$ exactly when each of the two products is zero or at least
  $2^{p-1}\eta$ in magnitude (`mul_pow2_2_exact`).
- **`add_1_1`, `mul_1_1`** are the one-limb operations as kernels, so that the one-limb `Ball`
  takes its constants from a proved bound like the two-limb one.

Why comparing limbs in order is exact for two limbs: $x_0 = \mathrm{RN}(x)$ and rounding is
monotone, so $x < y$ gives $x_0 \le y_0$, and when $x_0 = y_0$ the order is that of $x_1$ and
$y_1$; conversely $x_0 < y_0$ excludes both $x > y$ and $x = y$. The same argument covers a
one-limb operand, which is its own rounding.

Why `mul_pow2_2` ends with `fast_two_sum`: when the second product is rounded in the subnormal
range it can land exactly half a gap from the first, and the pair is then no longer normalized.

### Scaling beyond the powers of two of the format

`ldexp(x, n)` is defined for every `int` $n$, but the powers of two of the format only run from
$\eta$ to $2^{e_{\max}-1}$ ($2^{-1074}$ to $2^{1023}$ for `double`). Outside that range the public
header calls the kernel several times, each time with a power of two of the format
(`detail::ldexp_steps` in `expansion.hpp`):

- **Up**, $2^n > 2^{e_{\max}-1}$: by $2^{e_{\max}-1}$ while the exponent that remains is larger
  than $e_{\max}-1$, then by the rest. Two calls reach $2^{2e_{\max}-2}$ only, and a subnormal
  $x$ can give a finite result up to $n = 2097$ for `double`, so three calls may be needed. From
  $n = 2098$ on (in general, $2^n \ge 2^{e_{\max}}/\eta$) every nonzero finite $x$ overflows, and
  $n$ is clamped there.
- **Down**, $2^n < \eta$: by $c_1 = 2^n/\eta$, then by $\eta$. Below $n = -2099$ for `double` (in
  general, $2^n \le \eta/2^{e_{\max}+1}$) every finite $x$ gives a result that rounds to zero, and
  $n$ is clamped there.

**Status: argued and tested, not machine-checked.** These steps are composed by hand in the
header, outside the generator, so no generated statement is about them. Each call satisfies the
proved statements of the kernel; in particular the result is canonical, and normalized when it is
finite. The two statements below are about the composition. They rest on the arguments given here
and on the oracle, which judges every step of the public `ldexp` against the claims of the kernel
(`api.oracle.mul_pow2_2_full.*`, form `ldexp_far`). Turning the composition into a generated
kernel with a proved statement is an open item.

*Up: the result is $2^n x$ exactly, or $(\pm\infty, 0)$ with the sign of $x$.* A limb times a
power of two $c \ge 1$ is a number of the format unless it overflows, so both products of a call
are exact. The pair of products is normalized because $x$ is: if $x_0$ is subnormal then $x_1 = 0$,
and otherwise scaling by $c$ maps the numbers of the format around $x_0$ to those around $c x_0$,
ties and parity included. So `fast_two_sum` returns the pair unchanged, and the call returns $cx$.
A call that overflows returns $(\pm\infty, 0)$ with the sign of $x$ (F4), and the calls after it
keep that value (F5).

*Down: $\lvert z - 2^n x\rvert \le \eta$, the bound of one call, for `float` and `double`.* Let
$h$ and $l$ be the two products of the first call and $y$ its result. A product of magnitude at
least $2^{p-1}\eta$, the smallest normal number, is exact; a smaller one is rounded, by at most
$\tfrac12\eta$, to a number of magnitude at most $2^{p-1}\eta$. `fast_two_sum` loses nothing
($y_0 + y_1 = h + l$) and $\lvert y_1\rvert \le \lvert l\rvert$.

- If both products are exact, $y = c_1 x$, and the second call is one call of the kernel on it:
  the claim of the kernel gives the bound.
- If only $l$ is rounded, then $\lvert y_1\rvert \le 2^{p-1}\eta$, so in the second call
  $\lvert y_1 \eta\rvert < \tfrac12\eta$ rounds to zero and $z = \mathrm{RN}(y_0\eta)$. The error
  is at most $\tfrac12\eta$ for that rounding, plus $\lvert y_1\rvert\eta$, plus $\eta$ times the
  $\tfrac12\eta$ lost in $l$: less than $\eta$.
- If $h$ is rounded too, then $\lvert y_0\rvert \le 2^p\eta$, both products of the second call
  round to zero, and $z = 0$, while $\lvert 2^n x\rvert = \eta\lvert c_1 x\rvert < \tfrac12\eta$.

The last two cases use $2^p\eta < \tfrac12$, which holds for `float` and `double`. For one limb the
same steps give $\mathrm{RN}(2^n x)$ exactly, what `std::ldexp` returns: scaling up is exact until
it overflows, and scaling down either leaves the first product exact or makes both paths round to
a zero of the sign of $x$.

## Ball kernels

A ball is a center of $k$ limbs and a radius of one limb. For $k = 1$ the center operation is one
operation of $T$; for $k = 2$ it is the kernel of the same name. `U` and `V` stand for the
constants `unit_computed` and `tiny_computed` of the center's kernel, rounded up to $T$ by the
generator from the proved bound ($V = 0$ for additions, and the line that adds it is then left
out).

```
ball_add_k(cx, rx, cy, ry) -> (cz, rz)      ball_mul_k(cx, rx, cy, ry) -> (cz, rz)
  cz = add(cx, cy)                            cz = mul(cx, cy)
  mz = abs_upper(cz)                          ax = abs_upper(cx)
  d  = rmul(const U, mz)                      ay = abs_upper(cy)
  r0 = radd(rx, ry)                           t1 = rmul(ax, ry)
  rz = radd(r0, d)                            t2 = rmul(ay, rx)
                                              t3 = rmul(rx, ry)
ball_scale_k(cx, rx, a) -> (cz, rz)           s1 = radd(t1, t2)
  cz = mul(cx, a)                             s2 = radd(s1, t3)
  aa = abs(a)                                 mz = abs_upper(cz)
  t1 = rmul(aa, rx)                           d0 = rmul(const U, mz)
  mz = abs_upper(cz)                          d  = radd(d0, const V)
  d0 = rmul(const U, mz)                      rz = radd(s2, d)
  d  = radd(d0, const V)
  rz = radd(t1, d)                          ball_neg_k, ball_sub_k: through neg and ball_add_k
```

**Statement (containment), in the real model, proved for all ten kernels.** For finite operands
with nonnegative radii, and for all real $x$, $y$ with $\lvert x - c_x\rvert \le r_x$ and
$\lvert y - c_y\rvert \le r_y$: $\lvert (x \circ y) - c_z\rvert \le r_z$; and for $k = 2$ the
center $c_z$ is normalized. It holds from $p = 1$ for `ball_neg_k`, $p = 2$ for the one-limb
kernels and `ball_scale_2`, $p = 3$ for `ball_add_2` and `ball_sub_2`, and $p = 4$ for
`ball_mul_2`.

In the formal model `U` and `V` are not opaque constants: they are defined as the proved bound
rounded up, and the proof uses only that they are numbers of the format, nonnegative, and at
least the exact quotient. That the literals in the C++ headers equal those definitions is checked
by the generator's tests and, independently, by the oracle, which judges containment on the
compiled code.

*Why it holds.* For the sum, $\lvert x + y - c_z\rvert \le r_x + r_y + \lvert c_x + c_y - c_z\rvert$.
The last term is the center kernel's error, at most $\mathrm{unit}\cdot\lvert c_x + c_y\rvert +
\mathrm{tiny}$ by its theorem, hence at most $U\lvert c_z\rvert + V$ (a bound relative to the
exact value turns into one relative to the computed value with $\mathrm{unit}/(1 - \mathrm{unit})$).
Every `radd` and `rmul` returns at least the exact sum or product. The product is the same with
$\lvert xy - c_x c_y\rvert \le \lvert c_x\rvert r_y + \lvert c_y\rvert r_x + r_x r_y$.

### The radius, second design

The [benchmarks](../results/bench-milestone1.md) show that the radius dominates a `Ball`
operation: `ball_mul_2` costs 13 to 20 times `mul_2_2` in packed code, because each of the eleven
steps to the next number up is about ten integer operations. The radius only has to be an upper
bound, so the second design evaluates it with ordinary operations rounded to nearest, on
nonnegative values, and inflates the result once at the end: three to five floating-point
operations, and no `succ`, no `select`, no `abs_upper`.

```
ball_add_k(cx, rx, cy, ry) -> (cz, rz)      ball_mul_k(cx, rx, cy, ry) -> (cz, rz)
  cz = add(cx, cy)                            cz = mul(cx, cy)
  az = abs(cz0)                               ax = abs(cx0)
  s  = add(rx, ry)                            ay = abs(cy0)
  t  = fma(az, const E, s)                    az = abs(cz0)
  rz = fma(t, const G, const H)               p  = prod(rx, ry)
                                              q  = fma(ay, rx, p)
ball_scale_k(cx, rx, a) -> (cz, rz)           w  = fma(ax, ry, q)
  cz = mul(cx, a)                             t  = fma(az, const E, w)
  aa = abs(a)                                 rz = fma(t, const G, const H)
  az = abs(cz0)
  p  = prod(aa, rx)                         ball_sub_k: neg, then ball_add_k, with its constants
  t  = fma(az, const E, p)
  rz = fma(t, const G, const H)
```

`E`, `G` and `H` are constants of the format, one set per kernel, each an exact expression
rounded up. With $\mathrm{rel}$ and $\mathrm{tiny}$ the two constants of the center kernel's
proved bound, $U_q = \mathrm{rel}/(1 - \mathrm{rel})$ and $V_q = \mathrm{tiny}/(1 - \mathrm{rel})$:

| Kernel | `E` | `G` | `H` | Proved from |
|---|---|---|---|---|
| `ball_add_1`, `ball_sub_1` | $U_q$ | $(1+u)^3$ | $(1+u)\bigl((1+u)^2\eta + \tfrac12\eta\bigr)$ | $p \ge 1$ |
| `ball_add_2`, `ball_sub_2` | $U_q(1+u)$ | $(1+u)^3$ | the same | $p \ge 3$ |
| `ball_scale_1` | $U_q$ | $(1+u)^3$ | $(1+u)\bigl((1+u)^2\eta + V_q + \tfrac12\eta\bigr)$ | $p \ge 1$ |
| `ball_scale_2` | $U_q(1+u)$ | $(1+u)^3$ | the same form | $p \ge 2$ |
| `ball_mul_1` | $U_q$ | $(1+u)^5$ | $(1+u)\bigl(2(1+u)^4\eta + V_q + \tfrac12\eta\bigr)$ | $p \ge 1$ |
| `ball_mul_2` | $U_q$ | $(1+u)^6$ | $(1+u)\bigl(2(1+u)^5\eta + V_q + \tfrac12\eta\bigr)$ | $p \ge 4$ |

`E` turns the center's error bound into a multiple of $\lvert c_{z0}\rvert$, `G` covers the
rounding of every operation before the last line (and, for two limbs, the difference between a
center and its leading limb), and `H` covers what underflow can lose and the absolute term of the
center's bound. The argument is the usual one for sums of nonnegative products: a rounded
operation returns at least its exact result divided by $1 + u$, less $\eta/2$ for a product. The
proofs use only that each constant is a number of the format, nonnegative, and at least its
expression.

*Status.* This is the design the generator emits: the first design above is kept on this page
for the record, and its kernels and proofs are gone. Containment is proved in the real model for
the eight cores, in the shape of the statement above (and the radius is a number of the format,
the center normalized for $k = 2$), against the generated statements
(`proofs/theories/Ball2.v`), after complete enumerations of small formats by the generator's
tests, by the proofs' author and, from this page alone, by the oracle found no failure.
Enumeration suggests the constants have slack that is not proved away: `G` one unit in the last place smaller still encloses, and
so does half of `H`; `H` cannot be dropped for products and scalings. `radd`, `rmul` and
`abs_upper_2` remain kernels of their own.

**Special states.** A ball value is *canonical* when it is a finite ball (center finite, and
normalized for $k = 2$; radius finite and nonnegative), or the whole line (center 0, radius
$+\infty$), or the empty set (every limb a NaN). The Ball kernels above are finite cores; the
public operations call `ball_*_k_full`, the core followed by a fix-up:

```
ball_add_2_full(cx, rx, cy, ry) -> (cw, rw)
  (cz0, cz1, rz) = ball_add_2(cx, rx, cy, ry)     the finite core
  q   = add(rx, ry)              a NaN exactly when a radius is a NaN: an operand is empty
  e   = eq(q, q)
  a   = abs(cz0)
  f1  = lt(a, const inf)         the center is finite
  f2  = lt(rz, const inf)        the radius is finite (false for a NaN)
  f   = and(f1, f2)
  c0  = select(f, cz0, 0)        otherwise the whole line
  c1  = select(f, cz1, 0)
  r   = select(f, rz, const inf)
  cw0 = select(e, c0, q)         an empty operand gives the empty set
  cw1 = select(e, c1, q)
  rw  = select(e, r, q)
```

`ball_sub_k_full` and `ball_mul_k_full` are the same after their cores; for $k = 1$ the center
is one limb, so there is no `c1` and no `cw1`; `ball_scale_k_full` has one ball operand, so there
is no `q` line and `rx` stands in its place (and the temporary `a` is named `az`, since `a` is the
scalar). `ball_neg_k` needs no fix-up.

**Statement of a full Ball kernel, in the IEEE model.** The ball operands are canonical; the
scalar of `ball_scale` is any value of `T`.

- **B1.** The result is canonical.
- **B2.** If an operand is empty, the result is empty; otherwise it is not.
- **B3.** If the result is a finite ball, then every operand is a finite ball, the scalar is
  finite, and the containment statement above holds. (The whole line contains everything, so
  containment holds in every case.)
- **B4.** If every operand is a finite ball and the kernel's *finite when* condition holds, the
  result is a finite ball. No condition is proved yet.
- **In every case** the result contains $x \circ y$ for all $x$ and $y$ in the operands, the
  whole line counting as containing everything. This is the statement a user of balls relies on.

*Why it holds.* With no empty operand, every radius is nonnegative or $+\infty$, so `q` is not a
NaN. Every value of a core of the second design reaches $c_{z0}$ or $r_z$ through additions,
products and fused operations, which keep a non-finite value non-finite; so a finite $c_{z0}$ and
a finite $r_z$ mean that every value was finite and equal to the real model's, and the real-model
containment applies. A whole-line operand makes $c_{z0}$ or $r_z$ not finite, and a product
$0 \cdot \infty$ on the way gives a NaN radius, which `f2` also rejects. That is the corner where
an exact zero ball meets the whole line: the radius formula computes a NaN, and the result is the
whole line, not the empty set. A scalar that is not finite gives the whole line.

*Status.* B1, B2, B3 and containment in every case are proved in the IEEE model for the eight
full Ball kernels with the cores of the second radius design, and for `ball_neg_k`: from $p = 2$
for one limb (the constants must stay below the overflow threshold) and from the precision of
the core for two limbs. B4 is not started.

The oracle can judge containment exactly: the exact range of $X \circ Y$ is an interval whose
endpoints are sums or products of the operands' endpoints, and it must lie in $[c_z - r_z,
c_z + r_z]$.
