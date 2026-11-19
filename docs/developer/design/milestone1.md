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

## Second-wave operations

For limb type $T$ and at most two limbs. `pred` and `succ` are the neighbors in the format.

| Operation | Definition | Target statement |
|---|---|---|
| `sub_2_2`, `sub_2_1` | the addition with the second operand negated | that of the addition |
| `neg_2`, `abs_2` | sign change of both limbs; `abs_2` changes them when $x_0 < 0$ | exact; the result is normalized |
| `lt`, `le`, `eq` on two 2-limb numbers, and against one limb | limbs compared in order | equal to the comparison of the real values |
| `to_nearest_2` | $x_0$ | $= \mathrm{RN}(x)$ |
| `to_down_2`, `to_up_2` | $x_0$, or $\mathrm{pred}(x_0)$ when $x_1 < 0$; symmetric | the largest number of the format $\le x$; the smallest $\ge x$ |
| `abs_upper_2` | `to_up_2` of `abs_2` | the smallest number of the format $\ge \lvert x\rvert$ |
| `next_up`, `next_down` | $\mathrm{succ}$, $\mathrm{pred}$ | exact; $\mathrm{succ}(\Omega) = +\infty$ |
| `radd(a, b)`, `rmul(a, b)` for $a, b \ge 0$ | $\mathrm{succ}(\mathrm{RN}(a + b))$, $\mathrm{succ}(\mathrm{RN}(ab))$ | at least the exact sum or product, and at most 1.5 ulps of the result above it |
| `ldexp_2(x, n)` | each limb scaled by $2^n$, then renormalized | exact when no limb becomes subnormal; always $\lvert z - 2^n x\rvert \le \eta$ |

Why comparing limbs in order is exact for two limbs: $x_0 = \mathrm{RN}(x)$ and rounding is
monotone, so $x < y$ gives $x_0 \le y_0$, and when $x_0 = y_0$ the order is that of $x_1$ and
$y_1$; conversely $x_0 < y_0$ excludes both $x > y$ and $x = y$.

**Ball operations**, for centers of one and two limbs: addition, subtraction, multiplication,
multiplication by an exact scalar, negation. The center is the round-to-nearest kernel on the
centers. The radius is the formula of the
[Ball table](phase0/operations.md#ball), evaluated with `radd` and `rmul`, in which the kernel's
own error enters as `unit_computed` times `abs_upper` of the new center, plus `tiny_computed`.
Statement: for all $x \in X$ and $y \in Y$, $x \circ y \in Z$. A center that is not finite gives
the whole line ($r = +\infty$, $c = 0$).

Each of these is a kernel in the generator like any other, with selects where a choice is needed,
so its proof is about the same code that ships.
