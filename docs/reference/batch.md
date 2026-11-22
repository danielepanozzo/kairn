# Functions on arrays

`kairn/batch.hpp` has the sum and the dot product of arrays of numbers of $k$ limbs, the maps
that write an array element by element, the coefficients of the product of two polynomials, and
an upper bound of the largest magnitude of an array, for `T` `float` or `double` and $k$ 1 or 2.
Each function checks what the debug build checks and calls one loop of the generated headers: a
*fold* of the generator ([Folds](../developer/architecture.md#folds),
[Maps](../developer/architecture.md#maps)), made of proved kernels, whose statement is proved for
every length of array and every number of lanes, in the real model and in the IEEE model. The
header adds no arithmetic of its own. `kairn/kairn.hpp` does not include it.

```cpp
#include <kairn/batch.hpp>

// x, y: views of k arrays of limbs, kairn::SoAView<const T, k> (or of T); z: a view of T, written.
Reduction<Expansion<T, k>> sum(x);       sum(x, kairn::sequential);
Reduction<Expansion<T, k>> sum_fast(x);  sum_fast(x, kairn::sequential);
Reduction<Expansion<T, k>> dot(x, y);    dot(x, y, kairn::sequential);
bool add(x, y, z);                       // z = x + y, element by element
bool sub(x, y, z);                       // z = x - y
bool scale(x, a, z);                     // z = x a, a of T
bool mul_pow2(x, c, z);                  // z = x c, c a positive power of two of T
bool axpy(a, x, y, z);                   // z = a x + y, a of T, or (k = 2) a two-limb number
bool conv(x, y, z);                      // the coefficients of the product of two polynomials
Reduction<T> norm_upper(x);              // at least max |x_i|

template <class X> struct Reduction { X value; bool finite; };
```

## Arrays

An array is a view, [`SoAView<T, k>`](soa.md): one array of `T` per limb and a length. A
function reads views of `T` or of `const T` and writes a view of `T`; a view of `const T` given
where the function writes does not compile. A view of one limb is a plain array, so a program
that holds `const double* p` and a length `n` writes

```cpp
kairn::Reduction<kairn::Expansion<double, 1>> s = kairn::sum(kairn::SoAView<const double, 1>(p, n));
```

and for numbers of two limbs `kairn::SoAView<const double, 2>(hi, lo, n)`, the leading limbs
first. An `SoA` passes as `a.view()`. Every view of one call has the same limb type and the same
$k$: a dot product of an array of `double` and one of `float`, or of one and of two limbs, does
not compile. Nothing is allocated, and nothing throws.

**The arrays come from the program.** A program may fill an array with products in the same
function and pass it straight in; a compiler that inlines the loop could then fuse such a product
into the loop's first addition, and the sum would not be that of the numbers in the array
([rule R3](../developer/architecture.md#the-kernel-ir)). So every function calls the loop on
*supplied* arrays: the sums and the maps that add an element are the loops named `_entry`, whose
steps pass each limb they add through the guard $a + 0$ first. A product is fused only into an
addition, so a factor needs no guard, except where the compiler sees the *other* factor to be 1:
when one array of a dot product of one limb holds ones filled in the same function, Clang 18 on
x86-64 and Apple clang 21 with `-ffp-contract=fast` remove the multiplication, `fma(x, 1, s)`
becoming `x + s`, and fuse the program's product into that addition. So `dot` of one limb calls
the loop `dot_1_entry`, whose step guards both factors of its fused operation; `scale`,
`mul_pow2`, the `x` of `axpy`, `dot` of two limbs and `conv` only multiply their elements and are
called without a guard, and no compiler measured fuses into them with a factor it sees
([rule R3](../developer/architecture.md#the-kernel-ir), the factors of a fused operation). With the
guard taken out, GCC 16 at `-O3`, Apple clang 21 and Clang 18 with `-ffp-contract=fast` do fuse
such products into the sum of one limb and its difference, and Clang 18 and Apple clang 21 into the
dot product of one limb with a factor 1; with it, no form differs (`api.boundary.arrays.*`,
[Testing](../developer/testing.md#the-functions-on-arrays)).

## The order of a sum

The result of `sum`, `sum_fast` and `dot` depends on the order of their additions. One theorem
bounds every order by the same expression of the length
([Summation over any tree](../developer/design/milestone2.md#summation-over-any-tree)), so their
statement is the same in the two orders the loops are emitted in:

- **by default, the lane order** of the translation unit's form of [`Packed`](packed.md), the
  packed loop, the fast one: with $W$ lanes (4 of `double` and 8 of `float` with AVX2, 2 and 4
  with NEON, 1 in the scalar form), element $i$ goes to lane $i \bmod W$ of the first
  $W\lfloor n/W\rfloor$, each lane is summed from zero, the lanes are added from lane 0 upward,
  and the rest is added in order. Its bits depend on the instruction set the translation unit is
  compiled for (`KAIRN_PACKED_FORM`). With one lane, and with fewer elements than lanes, it is the
  sequential order;
- **`kairn::sequential`**: element after element, from zero. Its bits are the same on every
  platform and in every form; a program that wants the same result everywhere asks for it.

The maps write each element from the elements of the same index alone, so their results do not
depend on the order: they are the packed loop, whose elements are those of the scalar loop bit for
bit (a zero may differ in sign). `norm_upper` computes the same state in every order. `conv` has
the sequential order only.

## What each function states

$u$ is the unit roundoff of `T` ($2^{-53}$ for `double`, $2^{-24}$ for `float`) and $\eta$ its
smallest positive subnormal number. Each statement is that of the loop the function calls,
proved for every length $n$; the reference page of each loop's step, linked, has the step's own.

**`sum(x)`** (loops `sum_1_entry`, `sum_2_entry`; step [`sum_entry_step_1`](sum_entry_step_1.md),
[`sum_entry_step_2`](sum_entry_step_2.md)). When `finite`, `value` is finite, normalized for two
limbs, and

$$\Bigl\lvert \mathit{value} - \sum_i x_i\Bigr\rvert \le \bigl((1 + e)^{n-1} - 1\bigr)\sum_i\lvert x_i\rvert
\le \gamma_{n-1}(e)\sum_i\lvert x_i\rvert, \qquad \gamma_m(e) = \frac{m e}{1 - m e},$$

with $e = u/(1+u)$ for one limb and $e = 3u^2/(1-4u)$ for two, the second inequality when
$(n-1)e < 1$. No underflow term. **`sum_fast(x)`**: the same with the fast addition of two limbs
(loop `sum_fast_2_entry`, step [`sum_fast_entry_step_2`](sum_fast_entry_step_2.md)), $e = 3u^2$,
which is below the $e$ of `sum`; for one limb it is `sum`.

**`dot(x, y)`** (loops `dot_1_entry`, `dot_2`; step [`dot_entry_step_1`](dot_entry_step_1.md),
one fused multiply-add $s \leftarrow \mathrm{RN}(x_i y_i + s)$ of the guarded elements, and
[`dot_step_2`](dot_step_2.md)). When
`finite`, `value` is finite, normalized for two limbs, and

- one limb: $\lvert\mathit{value} - \sum x_i y_i\rvert \le ((1+e)^n - 1)\sum\lvert x_i y_i\rvert
  + (1+e)^{n-1}\,n\,\tfrac12\eta$, $e = u/(1+u)$;
- two limbs: $\lvert\mathit{value} - \sum x_i y_i\rvert \le ((1+4u^2)(1+e)^{n-1} - 1)\sum\lvert x_i
  y_i\rvert + (1+e)^{n-1}\,n\,\tfrac32\eta$, $e = 3u^2/(1-4u)$.

**The maps** claim, of every element written that is finite, what their step claims of one
element: `add` and `sub` (steps [`add_entry_step_1`](add_entry_step_1.md),
[`add_entry_step_2`](add_entry_step_2.md), [`sub_entry_step_1`](sub_entry_step_1.md),
[`sub_entry_step_2`](sub_entry_step_2.md)) the sum or difference rounded to nearest for one limb,
and for two a normalized result within $3u^2/(1-4u)$ of it, relative; `scale` (by `a` of `T`,
[`scale_step_1`](scale_step_1.md), [`scale_entry_step_2`](scale_entry_step_2.md), which guards the limbs
and `a`) the product rounded to
nearest, or within $2u^2\lvert x_i a\rvert + \eta$; `mul_pow2` (by `c` a positive power of two,
[`mul_pow2_step_1`](mul_pow2_step_1.md), [`mul_pow2_step_2`](mul_pow2_step_2.md)) the product,
exact but below the smallest normal number, within $\eta/2$ and $\eta$; `axpy` an error relative to
its two terms, $\lvert z_i - (a x_i + y_i)\rvert \le c\,u^k(\lvert a x_i\rvert + \lvert y_i\rvert) +
t\,\eta$, with $c = (2+3u)/(1+u)^2$, $t = \tfrac23$ for one limb
([`axpy_entry_step_1`](axpy_entry_step_1.md)), $c = 3(1+2u^2)/(1-4u) + 2$, $t = \tfrac54$ for two
limbs and `a` of `T` ([`axpy_entry_step_2_1`](axpy_entry_step_2_1.md)), and
$c = 3(1+4u^2)/(1-4u) + 4$, $t = 2$ for a two-limb `a`
([`axpy_entry_step_2`](axpy_entry_step_2.md)).

**`conv(x, y, z)`** (loops `conv_1_entry`, `conv_2`; the coefficients of one limb by `dot_1_entry`, which guards both factors) writes the $n_x + n_y - 1$ coefficients of the
product of the polynomials $x$ and $y$, none when either is empty: coefficient $j$ is `dot`, in its
sequential order, of the terms $(x_i, y_{j-i})$ in increasing $i$, and satisfies the statement of
`dot` for its own $m_j \le \min(n_x, n_y)$ terms.

**`norm_upper(x)`** (loops `norm_upper_1`, `norm_upper_2`; a fold of maxima of the kernels
[`norm_step_1`](norm_step_1.md), [`norm_step_2`](norm_step_2.md),
[`norm_combine`](norm_combine.md), [`norm_finish_1`](norm_finish_1.md),
[`norm_finish_2`](norm_finish_2.md)). With $V = \max_i\lvert x_i\rvert$, the exact magnitudes, and
$V = 0$ for no element: when `finite`, `value` is $V$ for one limb, and for two
$V \le \mathit{value} \le \mathrm{succ}(\mathrm{RU}(V))$, at most one step of `T` above the smallest
number of `T` not below $V$. So no element gives 0 for one limb and $\eta$ for two. It does not
round.

## The bound as a function of the length

Kairn's units are not powers of two, so a program that wrote $n u$ in its own analysis cannot
write $\gamma_{n-1}(3u^2/(1-4u))$ exactly in floating point. `kairn::traits<X>` gives the bound as
a number of `T` that is certainly at least it, computed by a generated, proved kernel
([`bound_sum_1`](bound_sum_1.md), [`bound_sum_2`](bound_sum_2.md), [`bound_dot_1`](bound_dot_1.md),
[`bound_dot_2`](bound_dot_2.md)), with `X` = `double`, `float` or `Expansion<T, k>`:

```cpp
using X = kairn::Expansion<double, 2>;
const kairn::Bound<double> s = kairn::traits<X>::sum(n);         // a sum of n numbers
const kairn::Bound<double> h = kairn::traits<X>::sum_height(h);  // a summation tree of height h
const kairn::Bound<double> d = kairn::traits<X>::dot(n);         // a dot product of n terms
kairn::traits<X>::axpy;  kairn::traits<X>::axpy_limb;            // one element of axpy (constants)
```

Each is a `Bound<T>` of `reference` `BoundForm::terms`. **What a program may write with them**,
for arrays of $n$ = `x.size()` elements whose `finite` is true, $x_i$ and $y_i$ the exact values
of the elements (for two limbs $x_{i,0} + x_{i,1}$):

- `r = kairn::sum(x)`, in either order, and `kairn::sum_fast(x)`, with `b = traits<X>::sum(n)`:
  $\lvert r.\mathit{value} - \sum_i x_i\rvert \le b.\mathit{unit}\,\sum_i \lvert x_i\rvert$, and
  `b.tiny` is 0. $b.\mathit{unit} \ge \gamma_{n-1}(e)$. The same bound holds for any sum of $n$
  numbers made by $n - 1$ additions of Kairn of `X` in any tree, and `sum_height(h)` for a tree of
  height $h$, $\gamma_h(e)$;
- `r = kairn::dot(x, y)`, in either order, with `b = traits<X>::dot(n)`:
  $\lvert r.\mathit{value} - \sum_i x_i y_i\rvert \le b.\mathit{unit}\,\sum_i \lvert x_i y_i\rvert +
  b.\mathit{tiny}$, where $b.\mathit{unit} \ge \gamma_n(e_\times)$ ($e_\times = u/(1+u)$ for one
  limb, $4u^2$ for two) and $b.\mathit{tiny} \ge n\,\tau\,(1 + b.\mathit{unit})$ ($\tau =
  \tfrac12\eta$, $\tfrac32\eta$): the two terms dominate those of the statement of `dot`;
- `kairn::conv(x, y, z)`: every coefficient, with `b = traits<X>::dot(min(x.size(), y.size()))`
  and the sum over its own terms;
- `kairn::axpy(a, x, y, z)`: every element, with `traits<X>::axpy_limb` (or `axpy` for a two-limb
  `a`; for one limb `traits<T>::axpy`): $\lvert z_i - (a x_i + y_i)\rvert \le \mathit{unit}\,(\lvert
  a x_i\rvert + \lvert y_i\rvert) + \mathit{tiny}$.

These are inequalities between real numbers. A program that evaluates the right side in floating
point rounds it up to keep it a bound: with `kairn::rmul` and `kairn::radd`
([Building blocks](index.md#building-blocks-on-t)), and an upper bound of $\sum_i\lvert x_i\rvert$
(for example `norm_upper(x)` times $n$, rounded up).

**Where no bound is given.** The kernels bound lengths up to about $n e \le \tfrac14$, where the
bound would be a third of the sum of magnitudes anyway: for one limb up to about $2^{51}$ terms of
`double` and $2^{22}$ of `float`; for two limbs of `float` about $2^{44}$; for two limbs of `double`
more than $2^{101}$, so every `std::size_t`. Beyond, `unit` and `tiny` are $+\infty$, which claims
nothing and cannot be mistaken for a bound: any expression of it is $+\infty$ or a NaN. The
functions are `constexpr`, with the same bits at compile time and at run time (the kernels have no
fused operation but products of nonnegative numbers), and in a constant expression a length beyond
is a compile error that names `no_bound_for_this_length`.

**The count.** The kernels take the count as a number of `T`. The header gives them the smallest
number of `T` not below it ($n - 1$ for `sum`, $n$ for `dot`, $h$ for `sum_height`), computed in
integers: exact up to $2^p$ ($2^{53}$ for `double`, $2^{24}$ for `float`), rounded up beyond, and
$2^{64}$ for the largest. Up, because what the kernels bound grows with the count, and their
statements ask of it only that it be a number of `T`, 0 or at least 1: a bound for a larger count
is a bound for $n$, and a conversion to nearest could give a smaller one. This conversion is the
header's and is not machine-checked; `tests/api/constexpr.cpp` checks it at and beyond $2^p$ and
`api.arrays.exact.bounds` checks every bound at those lengths, at every power of two and near the
largest `std::size_t` against $\gamma$ in exact rational arithmetic.

*Not claimed:* the smallest number of `T` at least the bound (`unit` exceeds $\gamma$ by a factor of
about $(1 + 2x)(1 - x)$, $x = n e$: a few $u$ for short arrays, an eighth at $x = \tfrac14$); a bound
beyond $n e$ about $\tfrac14$.

## When something is not finite

A function that returns a number returns `Reduction`: `value`, and `finite`, true exactly when
`value` is finite. When `finite` is false, `value` is the canonical NaN, every limb a NaN: an
element that is infinite or a NaN, or an overflow anywhere on the way, gives it, and which
infinity IEEE 754 would have given is not computed. A map returns `true` exactly when every
element written is finite; when it returns `false`, every element written that is not finite is
the canonical NaN, and the others are as computed. `finite = true` means that every result is
finite and within its bound. `norm_upper` is not finite, and its value a NaN, when an element is
not finite or the step up overflows.

## Arrays that alias

A map may write an array it reads, the same arrays exactly (`z.limb(j) == x.limb(j)` for every
limb, or the same with `y`): in place, since every element is read whole before it is written,
and nothing else reads it. `axpy(a, x, y, y)` is $y \leftarrow a x + y$. Otherwise the array
written overlaps no array read, and its limb arrays overlap each other nowhere; a partial overlap
is not supported. The coefficients `conv` writes overlap neither polynomial. The arrays read may
be the same: `add(x, x, z)`.

## Checks

With `KAIRN_CHECKS` 1 ([config.hpp](https://github.com/danielepanozzo/kairn/blob/main/include/kairn/config.hpp)),
every function but `norm_upper` checks the floating-point environment first, the rounding mode
included, then the lengths (`x` and `y` of `dot` and of the maps the length of `z`; `z` of
`conv` $n_x + n_y - 1$ coefficients), the arrays that alias, every element of two limbs
(canonical), and its scalar (`a` of `axpy` canonical; `c` of `mul_pow2` a positive power of two),
and stops the program with a message such as `kairn: dot: x and y have different lengths` on the
first that fails. The lengths and the aliasing are integer comparisons, checked even when a
program's `KAIRN_ENVIRONMENT_FAILURE` returns; the elements only in the default environment, since
the test of a canonical pair rounds. `norm_upper` does not round: its check leaves the rounding
mode out, and tests the elements only under rounding to nearest. Without the checks these are
requirements, and lengths that differ read or write outside the arrays.

## Constraints and constant evaluation

Each function compiles only while the kernels its loop is made of (its step or check, its
combination, its finish) are proved; `include/kairn/gen/bounds.hpp` exports their status, and has
no entry for a loop itself, whose status is in `gen/claims.json`. There is no marked form. None is
`constexpr`: the loops are not.

## Not provided

- A product of an array of two limbs by a two-limb scalar without an addition: no loop computes
  it. `axpy(a, x, y, z)` with `y` zero computes it, with the bound of `axpy`.
- The loops on *stored* arrays (`sum_1`, `sum_2`, `sum_fast_2`, `add_k`, `sub_k`, `axpy_k`), for a
  container whose elements only Kairn writes: no container of the library is such.
- An order of a given number of lanes other than the build's: `kairn::gen::F_lanes(..., W)` of
  the generated header computes it, and is not a public function.
- Allocation of the result: the program gives every array, the one written included.

## What is tested

The oracle judges every function through the public interface, against the claims of its loop
(`api.oracle.FOLD.FORMAT`, through `tests/api/runner_arrays.hpp`): random arrays of the oracle's
strata in both formats, of the lengths around the lanes, special values in every position, both
orders, and every map in place. `tests/api/batch.cpp` checks, in every form of `Packed`, that each
function calls its loop in the order it says, bit for bit against the generated loop, on lengths
0, 1, $W - 1$, $W$, $W + 1$, $2W - 1$, $2W$, $2W + 1$, $3W + 2$ and 97, that the flag and the
canonical NaN are as stated with an infinity or a NaN in every position and on overflow, and the
edges. `tests/api/boundary_batch.cpp` passes arrays filled with products; `api.checks.*` and
`api.reject.batch.*` test the checks and what must not compile
([Testing](../developer/testing.md#the-functions-on-arrays)).
