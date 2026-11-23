# The accumulator

`kairn::Accumulator<T, k>` is the state of a sum or a dot product given to the program, for a loop
that Kairn does not provide: a product of polynomials over several indices, a sum computed in
parallel and merged, terms that come one at a time. It holds the running sum $s$, a number of $k$
limbs; the running sum $a$, in `T`, of the magnitudes of the leading limbs of what was added; and
the count $n$ of terms. At the end it gives the sum, a radius that bounds its error whatever the
order of the additions, and the ball of the two. `kairn/accumulator.hpp`, which `kairn/kairn.hpp`
includes.

```cpp
kairn::Accumulator<double, 2> acc;          // empty: no term, every limb +0
acc.add(x);                                  // a number, or a double
acc.add_product(x, y);                       // a product of two numbers, or of two doubles
acc.merge(other);                            // another accumulator: a node of the summation tree
kairn::Reduction<kairn::Expansion<double, 2>> s = acc.sum();   // the sum, canonical, and finite
double r = acc.error_bound();                // |s - exact sum| <= r, or +inf
kairn::Ball<double, 2> b = acc.ball();       // the ball of center s and radius r: it contains it
acc.count();  acc.magnitudes();  acc.running_sum();            // the state, and from_state(s, a, n)
```

## What each operation does

Each operation that changes the state is one generated, proved kernel:

| Operation | Kernel | Does |
|---|---|---|
| `add(x)` | [`acc_add_1`](acc_add_1.md), [`acc_add_2`](acc_add_2.md) | $s \leftarrow s + x$ (`add_1_1`, `add_2_2`, on $x$ guarded), $a \leftarrow \mathrm{RN}(a + \lvert x_0\rvert)$ |
| `add_product(x, y)` | [`acc_mul_entry_1`](acc_mul_entry_1.md), [`acc_mul_entry_2`](acc_mul_entry_2.md) | $s \leftarrow s + x y$ (one fused operation of $x$ and $y$ guarded for one limb; `mul_2_2` then `add_2_2` on the guarded limbs for two), $a \leftarrow \mathrm{RN}(\lvert x_0\rvert\lvert y_0\rvert + a)$ |
| `merge(other)` | [`acc_merge_1`](acc_merge_1.md), [`acc_merge_2`](acc_merge_2.md) | $s \leftarrow s + s'$, $a \leftarrow \mathrm{RN}(a + a')$, $n \leftarrow n + n'$ |
| `error_bound()` | [`bound_dot_1`](bound_dot_1.md), [`bound_dot_2`](bound_dot_2.md), then [`acc_radius_1`](acc_radius_1.md), [`acc_radius_2`](acc_radius_2.md) | the radius $r$ from $a$ and the count |
| `sum()` | [`fold_finish_1`](fold_finish_1.md), [`fold_finish_2`](fold_finish_2.md) | $s$, or the canonical NaN, with whether it is finite |
| `ball()` | `Ball(s, r)` ([`ball_make_1`](ball_make_1.md)); for two limbs [`ball_make_2`](ball_make_2.md), with the checks of `Ball(s, r)`: $s$ is the kernels' output, whose limbs are not guarded again | center $s$, radius $r$; the whole line where $r$ is $+\infty$ |

A value `add` takes passes through the guard first ([rule R3](../developer/architecture.md#the-kernel-ir)),
so a product the program computes and adds, `acc.add(a * b)`, is the product rounded; the factors
of `add_product` are guarded too (below), every limb of both.
`merge(acc)` merges an accumulator with itself.

## What is proved

For **every history** of `add`, `add_product` and `merge`, a merge being a node of the summation
tree and the other accumulator's history a subtree, whose elements are finite numbers (normalized
pairs for two limbs): if the running sum $s$ is finite and the masks of the two kernels of the
radius are true, then

$$\Bigl\lvert s - \Sigma\Bigr\rvert \le g\sum_i\lvert x_i y_i\rvert + t \le r,$$

with $\Sigma$ the exact sum of the numbers and products added, $(g, t)$ = `bound_dot_k` of a count
$m$ of `T` that is 0 or at least 1 and at least the number of terms, and $r$ = `acc_radius_k`
$(a, m, g, t)$. The order is whatever the program did. The first inequality is the bound of a dot
product of $n$ terms in any tree; the second rests on
$\sum_i\lvert x_i y_i\rvert \le (1 + u)^{n+2}(a + \tfrac12 n\eta)$ (the exponent $n$ for one limb),
the sum of magnitudes being rounded $n$ times. Proved in the real model and in the IEEE model
(`proofs/theories/Accumulator.v`, `IeeeAccumulator.v`, `AccKernels.v`, `IeeeAccKernels.v`).

The radius is given up to a count of terms that depends on `T` and not on the precision of the
sum, since the magnitudes are summed in `T`: with one limb for fewer than $2^{22}$ terms of `float`
and $2^{51}$ of `double` (while $m u < \tfrac14$, $u$ the unit roundoff of `T`: where the mask of
`bound_dot_1` is true), and with two limbs for fewer than $2^{23}$ and $2^{52}$ (while
$m u < \tfrac12$: the mask of `acc_radius_2`). Beyond, `error_bound()` is $+\infty$. (Corrected on
2026-11-22: this paragraph gave $m u \le \tfrac12$ and the first pair of counts for both.)

## What the header adds, which is not machine-checked

- **The count**, a `std::uint64_t`: +1 per `add` and `add_product`, the sum on a merge, exact up to
  $2^{64} - 2$. A count that would reach $2^{64} - 1$ stays there, and that value means "too many to
  count": `error_bound()` is $+\infty$. The theorem asks for a count at least $n$, which a
  saturated one may not be.
- **Its conversion to `T`**: the smallest number of `T` not below $n$ (the conversion of
  [the bounds as functions of the length](batch.md#the-bound-as-a-function-of-the-length)),
  rounded up because the theorem asks for $m \ge n$. Wherever a radius is given ($m u \le \tfrac12$)
  the count is below $2^p$ and the conversion is exact.
- **What is returned when a mask is false or a value is not finite**: `error_bound()` is
  $+\infty$, and `ball()` the whole line, whenever the count saturated, the mask of `bound_dot_k`
  or of `acc_radius_k` is false (a sum of magnitudes that overflowed, which `acc_radius_k` tests,
  or a count beyond the lengths bounded), the running sum is not finite, or the radius is not.
  Never a finite radius that the theorem does not give. A term that is not finite (an infinity, a
  NaN, an infinity times zero) makes the running sum not finite, and it stays so: the kernels keep
  a NaN and turn an infinity into an infinity or a NaN, so no later history gives a finite $s$.
  `sum()` then has `finite` false.
- **That the header calls the kernels in this way**, the run of the theorem.

These are tested (below), not proved.

## The state

`running_sum()` (the running sum as the kernels left it: when its leading limb is not finite it
need not be canonical; `sum()` is the canonical form), `magnitudes()` and `count()` read the state,
and `Accumulator::from_state(s, a, n)` makes an accumulator of a state, so that a program can move
accumulators through its own storage (a buffer of a device, a message between processes) and merge
them there. The guarantee of `error_bound()` is that of the history of the accumulator the state
was read from: a state that no history produced has none. Everything it is given passes through
the guard $a + 0$ first, since the kernels of `add`, `add_product` and `merge` add to it, as the
limbs of `Ball::from_limbs` do: the magnitudes and the limb of a running sum of one limb through
[`make_2`](make_2.md), of which it keeps the leading limb, and a running sum of two limbs through
[`make_2_limbs`](make_2_limbs.md) (since 0.3.1; 0.3.0 copied it as it was, the limbs of an
`Expansion<T, 2>` being public, which a program can write). That the state is the one given is
argued from the claims of those two kernels, not machine-checked as one statement. A product the
program passes in is the product rounded (without the guard, GCC 13 at its default setting, Clang 18
and Apple clang 21 with `-ffp-contract=fast` were measured fusing one given as the magnitudes or as
a running sum of one limb into the next `add`; none was seen to fuse one written into a limb of a
running sum of two limbs, `api.boundary.arrays.*`). A state saved and restored keeps its values: every
limb comes back bit for bit but a $-0$, which comes back $+0$ (the guard computes $-0 + 0$, $+0$
when rounding to nearest; with MSVC it may stay $-0$: the compiler removes the addition of zero
where it packs two guards; the value is unchanged), and a NaN, which comes back a NaN; in constant evaluation the guard is not
applied, and every limb comes back bit for bit. With `KAIRN_CHECKS`, `from_state` requires a
canonical sum and magnitudes that are not negative.

## A product by a factor the compiler knows to be 1

`add_product(x, y)` only multiplies its operands. A product is fused only into an addition, but a
compiler that sees one factor to be 1 removes the multiplication, `fma(x, 1, s)` becoming `x + s`,
and fuses a product of the program passed as the other into that addition: Apple clang 21 with
`-ffp-contract=fast` did so in `add_product(a * b, 1)` of one limb, and Clang 18 on x86-64 and Apple
clang 21 in the dot product of one limb ([Functions on arrays](batch.md#arrays)). So
`add_product` of one limb calls `acc_mul_entry_1`, which guards both factors, and that of two limbs
`acc_mul_entry_2`, which guards every limb of both (rule R3, the factors of a fused operation; no
compiler was measured to fuse such a product there, and the rule asks the guard all the same). A
program that adds a product of its own writes `acc.add(a * b)`, which guards, or
`acc.add_product(a, b)`, which takes the exact product.

## Checks and constant evaluation

The accumulator is no batch entry: `add` and `add_product` take one term and `merge` one
accumulator, as a scalar operation does, so they check the environment in a debug build only, as
the operations of `Expansion` do (the functions on arrays of [batch.md](batch.md#checks) check it in
every build). With `KAIRN_CHECKS` 1, `add`, `add_product`, `merge`, `error_bound` and `ball` check the
floating-point environment, the rounding mode included, then that a two-limb operand is canonical;
`from_state` rounds only in its guards, whose values do not depend on the rounding mode, checks the
environment without the rounding mode, and then its state;
`sum()`, `count()`, `magnitudes()` and `running_sum()` check nothing. The constructor, `add`,
`merge`, `sum`, the accessors and `from_state` are `constexpr`; `add_product`, `error_bound` and
`ball` are not, since `acc_mul_k` and `acc_radius_k` have fused multiply-adds without a variant
for constant evaluation. An accumulator is trivially copyable and holds no heap memory.

## Not provided

An accumulator that keeps limbs unnormalized and normalizes once at the end (the cascaded
summation of [question 12](../developer/design/milestone2.md#open-questions)); the merge of
accumulators of different limb types or numbers of limbs (it does not compile).

## What is tested

The oracle judges `add`, `add_product` and `merge` against their kernels' claims through
`from_state` and the accessors (`api.oracle.acc_add_k.F`, `acc_mul_k`, `acc_merge_k`); the radius
kernel, which the header calls only on the $(g, t)$ of `bound_dot_k`, is cross-checked on its own.
`api.arrays.exact.accumulator` runs random trees of `add`, `add_product` and `merge`, empty
accumulators merged, counts around and beyond $2^p$ (a history merged with itself), a saturated
count, overflows of the running sum and of the sum of magnitudes, and terms that are not finite,
and checks each in exact rational arithmetic: $\lvert s - \Sigma\rvert \le r$ wherever $r$ is
finite, $+\infty$ and the whole line wherever the theorem gives nothing, and a finite radius where
it should have one. `api.accumulator` checks constant evaluation, the merges, `from_state` and the
edges; `api.checks.*`, `api.reject.accumulator.*` and `api.reject.not_constexpr.*` the checks and
what must not compile ([Testing](../developer/testing.md#the-functions-on-arrays)).
