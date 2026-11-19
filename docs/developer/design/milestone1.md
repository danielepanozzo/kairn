# Milestone 1: overflow, non-finite values, and the second-wave operations

The [architecture page](../architecture.md#kernels-of-the-first-wave) states the first-wave
kernels in a model where exponents are unbounded above. This page adds what Milestone 1 needs on
top: how overflow and non-finite values are treated, formally and in the code, and the remaining
operations. Notation is that of [Numbers](phase0/numbers.md).

**Everything here is a target.** Each statement is first tested on every operand of toy formats,
then proved; points still open are marked.

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
sign changes (every first-wave kernel is), with finite normalized operands.

1. **Bridge.** If output limb 0 of the IEEE model is finite, then every intermediate value was
   finite, and the outputs are equal, as real numbers, to those of the real model.
   *Why it holds:* each of those operations returns a non-finite value when an operand is not
   finite, and the generator's cone rule guarantees that every intermediate value reaches output
   limb 0. The proof is mechanical and is generated per kernel.
2. **Correctness.** Therefore either $z_0$ is not finite, or $z$ is normalized and satisfies the
   bound of the real-model theorem. No finite wrong result can come out of an intermediate
   overflow.
3. **No spurious overflow.** There is a threshold $\Omega_K$, a power-of-two fraction of $\Omega$
   that is part of the statement, such that if all operands and the exact result are at most
   $\Omega_K$ in magnitude then $z_0$ is finite. Target: $\Omega/4$ for the additions; for the
   products to be determined.

Open, to be settled by exhaustive testing on toy formats with a finite $q_{\max}$: the exact
conditions under which `two_sum`, in the operation order Kairn uses, returns a non-finite error
term although its sum is finite. Phase 0 found such a case for one operation order at an operand
equal to $\pm\Omega$; statement 3 has to be stated so that this corner is outside it.

## IEEE-like results

By decision [D5](phase0/decisions.md#d5-non-finite-results), `Expansion` arithmetic returns
canonical infinities and NaN the way `T` does, and the `kairn::finite::` variants skip that. The
default operation is the kernel followed by a fix-up made of one extra operation, one test and
selects:

```
z = K(x, y)
t = x0 op y0                 one operation of T on the leading limbs (the opaque product for *)
if z0 is finite:        return z
else if t is NaN:       return (NaN, ..., NaN)
else if t is infinite:  return (t, 0, ..., 0)
else:                   return (infinity with the sign of t, 0, ..., 0)
```

Statement, in the IEEE model:

- For finite normalized operands the result is either finite, normalized and within the bound, or
  a canonical infinity; it is finite whenever statement 3 applies. The infinity has the sign of
  the exact result (to be confirmed by the exhaustive tests for the case where the leading limbs
  cancel).
- With a non-finite operand, the result is the canonical form of what the same operation of `T`
  returns on the leading limbs: $+\infty + 1 = +\infty$, $\infty - \infty = \mathrm{NaN}$,
  $0 \cdot \infty = \mathrm{NaN}$.

The fix-up contains comparisons and selects, for which "non-finite in, non-finite out" is false,
so it is proved directly in the IEEE model.

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
are this kernel with $c = 2^n$ (two calls when $2^n$ is not a number of the format).

```
mul_pow2_2(x, c) -> z
  h = prod(x0, c)
  l = prod(x1, c)
  (z0, z1) = fast_two_sum(h, l)
```

| Kernel | Requires | Target statement |
|---|---|---|
| `neg_2`, `abs_2` | $x$ normalized | $z$ normalized; $z = -x$, $z = \lvert x\rvert$ exactly |
| `sub_2_2`, `sub_2_1`, `sub_1_2` | operands normalized | that of the addition, for $x - y$ |
| `lt`, `le`, `eq` (all forms) | operands normalized | the mask is the truth of the comparison of the real values |
| `to_nearest_2` | $x$ normalized | $t = \mathrm{RN}(x)$ |
| `to_down_2`, `to_up_2` | $x$ normalized | $t$ is the largest number of the format $\le x$; the smallest $\ge x$ |
| `abs_upper_2` | $x$ normalized | $t$ is the smallest number of the format $\ge \lvert x\rvert$ |
| `radd`, `rmul` | — | $r \ge a + b$, $r \ge ab$; and $r$ exceeds the exact value by at most $g$ gaps, where a gap is $r - \mathrm{pred}(r)$ and $g \le 2$ is to be determined ($3/2$ expected for nonnegative operands) |
| `mul_pow2_2` | $x$ normalized, $c$ a power of two | $z$ normalized; $\lvert z - cx\rvert \le \eta$; and $z = cx$ when each of the two products is zero or at least $2^{p-1}\eta$ in magnitude |

Why comparing limbs in order is exact for two limbs: $x_0 = \mathrm{RN}(x)$ and rounding is
monotone, so $x < y$ gives $x_0 \le y_0$, and when $x_0 = y_0$ the order is that of $x_1$ and
$y_1$; conversely $x_0 < y_0$ excludes both $x > y$ and $x = y$. The same argument covers a
one-limb operand, which is its own rounding.

Why `mul_pow2_2` ends with `fast_two_sum`: when the second product is rounded in the subnormal
range it can land exactly half a gap from the first, and the pair is then no longer normalized.

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

**Statement (containment), in the real model.** For finite operands with nonnegative radii, and
for all real $x$, $y$ with $\lvert x - c_x\rvert \le r_x$ and $\lvert y - c_y\rvert \le r_y$:
$\lvert (x \circ y) - c_z\rvert \le r_z$.

*Why it holds.* For the sum, $\lvert x + y - c_z\rvert \le r_x + r_y + \lvert c_x + c_y - c_z\rvert$.
The last term is the center kernel's error, at most $\mathrm{unit}\cdot\lvert c_x + c_y\rvert +
\mathrm{tiny}$ by its theorem, hence at most $U\lvert c_z\rvert + V$ (a bound relative to the
exact value turns into one relative to the computed value with $\mathrm{unit}/(1 - \mathrm{unit})$).
Every `radd` and `rmul` returns at least the exact sum or product. The product is the same with
$\lvert xy - c_x c_y\rvert \le \lvert c_x\rvert r_y + \lvert c_y\rvert r_x + r_x r_y$.

**Special states**, added with the non-finite layer: a radius that is NaN is the empty set and
makes the result empty; a center that is not finite, or an infinite radius, makes the result the
whole line ($r = +\infty$, $c = 0$). One corner needs care: with an exact zero ball and the whole
line, the radius formula computes $0 \cdot \infty$, which is NaN, and the result must be the
whole line, not the empty set.

The oracle can judge containment exactly: the exact range of $X \circ Y$ is an interval whose
endpoints are sums or products of the operands' endpoints, and it must lie in $[c_z - r_z,
c_z + r_z]$.
