# Ball vectors: BallVector and its views

`kairn/ball_vector.hpp` holds $N$ centers of $k$ limbs and **one** radius of type `T`: the set of
the vectors of $N$ reals each of whose entries is within the radius of its center
([Milestone 2, BallVector](../developer/design/milestone2.md#ballvector);
[Ball vectors](../developer/architecture.md#ball-vectors)):

- `kairn::BallVector<T, k, N>` owns its centers and its radius, inside the object;
- `kairn::BallVectorView<T, k>` sees the arrays of the centers, a length known at run time and a
  radius that someone else owns, a `BallVector` or the program; `kairn::BallVectorView<const T, k>`
  sees them read-only.

`T` is `float` or `double`, $k$ is 1 or 2, $N \ge 1$ (a view may have no entry). The centers are
stored as one array per limb, as the loops read them: limb $j$ of center $i$ is element $i$ of
array $j$, the layout of [`SoA`](soa.md). `kairn/kairn.hpp` does not include the header
([Compile time](#compile-time)); it includes `kairn/soa.hpp`, `kairn/packed.hpp`, `kairn/ball.hpp`,
`kairn/blocks.hpp` and `kairn/order.hpp`.

**A `BallVector` is not $N$ independent balls.** One radius bounds every entry, so it is as wide as
the widest entry needs, and every operation adds to it what the worst entry adds; in exchange an
operation costs one kernel per entry and a few operations for the radius, once. `entry(i)` is the
ball of center $i$ and the shared radius, a copy. [Getting started](../getting-started/index.md#ball-vectors)
says when to use one, and the [tutorial](../tutorials/ball-vectors.md) uses one for polynomials.

**Status: every operation is one generated loop, proved in Rocq in both of its orders, and judged
by the oracle through the public interface.** The header adds no arithmetic; two operations,
`axpy` and `norm_upper`, are compositions of two proved calls made in the header, and say so
([below](#compositions-made-in-the-header)).

```cpp
template <class T, int K, std::size_t N> class BallVector {
    BallVector();                                     // every center 0, the radius 0
    BallVector(const std::array<Expansion<T, K>, N>& c, T r);  // loop bv_make_1 or bv_make_2_entry
    BallVector(SoAView<const T, K> c, T r);           // the same from arrays, c.size() == N
    explicit BallVector(BallVectorView<const T, K> v);  // a copy, v.size() == N
    static BallVector whole();
    static std::size_t size();  T radius() const;  bool is_finite() const;  bool is_whole() const;
    Expansion<T, K> center(std::size_t i) const;  Ball<T, K> entry(std::size_t i) const;
    SoAView<const T, K> centers() const;  const T* limb(int j) const;
    BallVectorView<T, K> view();  BallVectorView<const T, K> view() const;   // and conversions
};
template <class T, int K> class BallVectorView {       // T may be const
    BallVectorView(SoAView<T, K> c, T& r);            // the program's arrays, made a ball vector in place
    BallVectorView(const BallVectorView<U, K>&);       // of U converts to one of const U
    std::size_t size() const;  bool empty() const;  // and the accessors of BallVector
    BallVectorView subview(std::size_t offset, std::size_t count) const;   // const limbs only
};
// Z is a BallVector (an lvalue, not const) or a view of mutable limbs; X, Y either, or const.
void neg(X, Z);  void add(X, Y, Z);  void sub(X, Y, Z);  void scale(X, T a, Z);
void ldexp(X, int n, Z);  void half(X, Z);  void axpy(T a, X, Y, Z);  void convolution(X, Y, Z);
T norm_upper(X);
// Each also with kairn::sequential first: neg(kairn::sequential, X, Z), ...
// On BallVector: -x, x + y, x - y, x * a, a * x, x += y, x -= y, x *= a, ldexp(x, n), half(x),
// axpy(a, x, y), convolution(x, y) of N + M - 1 coefficients; the same with kairn::sequential.
```

## The two states

A ball vector is **canonical** when it is a *finite ball vector* (every center finite, canonical for
two limbs; the radius finite and $r \ge 0$) or the **whole space** (every center zero, the radius
$+\infty$). There is no empty state ([question 7](../developer/design/milestone2.md#open-questions)):
no operation of a ball vector produces an empty set. `is_finite()` and `is_whole()` say which;
`BallVector::whole()` makes the second. Every operation returns the whole space when its result
cannot be a finite ball vector: an operand that is the whole space, a scalar that is not finite,
an overflow anywhere.

## Construction

`BallVector(c, r)`, `BallVector(SoAView, r)` and `BallVectorView(SoAView, r)` call the loop
`bv_make_1` or `bv_make_2_entry`, in the sequential order in every build (so that the class is the
same in every translation unit; the lane order computes the same bits). Each center is guarded,
each limb of it for two limbs, whether it comes from arrays or from `Expansion<T, 2>` objects of
the program (rule R3: the program may have written a product there); the radius is guarded. Two
limbs need canonical pairs, on which the guards are the identity as values. Proved, in the IEEE model,
for any radius and any centers (canonical pairs for two limbs), the claim `makes_ball_vector`:

- the result is canonical;
- it is the whole space exactly when the radius given is negative ($-\infty$ included), a NaN or
  $+\infty$, or the leading limb of a center is not finite;
- otherwise its centers and its radius are those given, as values (a zero may come back with the
  other sign).

`BallVectorView(c, r)` is how arrays of the program's become a ball vector: it makes them one in
place, writing the whole space into them where the values say so, and sees them. Its loop guards
each limb it reads, for one limb and for two, as `BallVector(SoAView<const T, 2>, r)`'s does, so a
product the program computed in the same function is rounded before it is a limb of the ball
vector (`api.boundary.ball_vector`); for two limbs the pairs must be canonical (a pair the program
computed that is not normalized is not covered). A program that
writes the arrays or the radius of a view afterwards must make the view again: nothing else
guards what it wrote, and with `KAIRN_CHECKS` 1 every operation checks that its operands are
canonical. The copy of a view, `BallVector(v)`, copies limbs and radius as they are. The default
`BallVector()` is the point 0 of $N$ entries.

## The operations

Each operation takes `BallVector`s and views alike, of one limb type and one number of limbs, and
writes its result into `z`, a `BallVector` or a view of mutable limbs. Where the types fix the
lengths they must agree (a product: $N + M - 1$), or the call does not compile; where a view is
given they are checked with `KAIRN_CHECKS` and not otherwise. What each loop claims, for canonical
operands, in Flocq's model of IEEE 754 with overflow (`encloses_entries`,
`encloses_coefficients`; [Ball vectors](../developer/architecture.md#ball-vectors)):

- **V1** the result is canonical;
- **V2** containment, in every case: for every member $x$ of $X$ and $y$ of $Y$, $f(x, y)$ is a
  member of the result, entry by entry; the whole space contains everything;
- **V3** if the result is finite, every operand and every scalar is, each center is the generated
  kernel's on its entry, and the radius is the loop's radius kernel at the largest magnitude $M$ of
  a center written (for the product, of the centers read);
- **V4** the result is finite when every operand and scalar is finite and the conditions below hold,
  for every length, 0 included. $2^{e_{\max}-2}$ is a quarter of the overflow threshold:
  $2^{1022}$ for `double`, $2^{126}$ for `float`.

| Operation | Loop | Centers | Radius | Finite (V4) when | In place |
|---|---|---|---|---|---|
| `-x`, `neg(x, z)` | `bv_neg_k` | `neg_k`, exact | $r_x$ | always: **exact**, the result is the negated set | `z` = `x` |
| `x + y`, `add(x, y, z)` | `bv_add_k` | `add_1_1`, `add_2_2` | `bv_add_radius_k`$(M, r_x, r_y)$ | $r_x + r_y$ and every $\lvert x_i + y_i\rvert + r_x + r_y$ within $2^{e_{\max}-2}$ | `z` = `x` or `y` |
| `x - y`, `sub(x, y, z)` | `bv_sub_k` | `sub_1_1`, `sub_2_2` | the same | the same with $x_i - y_i$ | `z` = `x` or `y` |
| `x * a`, `scale(x, a, z)` | `bv_scale_1`, `bv_scale_2_entry` | `scale_step_1`, `bv_scale_step_2` ($x\,a$; for two limbs on $a$ guarded, a factor of the fused operations of `mul_2_1`) | `bv_scale_radius_k`$(M, r_x, a)$ | $\lvert a\rvert r_x$ and every $(\lvert x_i\rvert + r_x)\lvert a\rvert$ within $2^{e_{\max}-2}$; an infinite or NaN $a$ gives the whole space | `z` = `x` |
| `ldexp(x, n, z)`, `half(x, z)` | `bv_mul_pow2_k`, $c = 2^n$ | `bv_mul_pow2_step_k`, with a mask of exactness | `bv_mul_pow2_radius`: $c\,r_x$ when every entry and the radius are scaled exactly, otherwise the second number after $\mathrm{RN}(c\,r_x)$ | $c\,r_x$ and every $(\lvert x_i\rvert + r_x)\,c$ within $2^{e_{\max}-2}$ | `z` = `x` |
| `convolution(x, y, z)` | `bv_conv_k`, sequential only | `conv_k` (each coefficient `dot_k` of its terms) | `conv_radius` | below | none: `z` overlaps neither |

**The scaling by a power of two is exact** when nothing underflows: when every limb of every center
of $2^n X$ and its radius is zero or above the smallest normal number in magnitude ($2^{-1022}$ for
`double`, $2^{-126}$ for `float`), the result is $2^n X$ itself, centers $2^n c_i$ and radius
$2^n r$, and nothing is added (`exact_when`, with the mask of exactness and-ed over the entries).
`half(x)` is one call with $c = \tfrac12$, the halving of a subdivision. `ldexp` calls the loop
once when $2^n$ is a number of `T`, two or three times otherwise
([below](#compositions-made-in-the-header)). `x * T(0.5)` is the general scaling, whose radius
grows even for a power of two.

**The product of polynomials.** `convolution(x, y, z)`: coefficient $j$ of $Z$ is
$\sum_i x_i y_{j-i}$, $X$ of $n_x$ coefficients and $Y$ of $n_y$, $Z$ of $n_x + n_y - 1$ (none when
a length is 0), in whatever basis the product is the convolution of the coefficients (the monomial
basis; for the Bernstein basis, the coefficients scaled by their binomials). V2 holds for the
products of *independent* members: each entry of $x$ and of $y$ ranges over its ball independently
of the others. With $M_a$, $M_b$ the largest magnitudes of the leading limbs of the operands'
centers, $m = \min(n_x, n_y)$ and $(g, t)$ the bound of a dot product of $m$ terms
(`bound_dot_k`), the radius is at least
$m\,((1+u)M_a r_y + (1+u)M_b r_x + r_x r_y) + g\,m\,(1+u)^2 M_a M_b + t$
([The product of polynomials](../developer/design/milestone2.md#the-product-of-polynomials)). It is
finite when both operands are finite and, with $n = \min(n_x, n_y)$:

- **a condition on the length**: $n\,(\mathrm{unit}(K) + \eta) \le \tfrac1{16}$ for one limb and
  $n\,(\mathrm{unit}(K) + \eta / (2u)) \le \tfrac1{16}$ for two, with $\mathrm{unit}(K)$ that of the
  product `mul_1_1` or `mul_2_2`: about $n \le 2^{49}$ for one limb of `double` and $2^{20}$ of
  `float`, $n \le 2^{100} - 1$ for two limbs of `double` and $2^{42} - 1$ of `float`; above it the
  bound of the dot product is not given and the product is the whole space whatever the values;
- $r_x r_y \le 2^{e_{\max}-2}$; every entry of $X$ has $(\lvert x_i\rvert + r_x)\,r_y$ and every
  entry of $Y$ $(\lvert y_k\rvert + r_y)\,r_x$ within $2^{e_{\max}-2}$; and every pair has
  $n\,(\lvert x_i\rvert + r_x)(\lvert y_k\rvert + r_y) \le 2^{e_{\max}-2}$.

The radius takes the largest centers of each operand for every coefficient: for coefficients of
comparable size, such as those of a polynomial in the Bernstein basis, that is the right order; for
coefficients that differ much in size it overestimates by up to the factor $m$. From precision 4
(every format of `T`).

**Claimed less than the design page asks.** The one radius of a sum, a difference, a scaling and a
scaling by a power of two (when not every entry is exact) *equals* the largest of the $N$ radii that
the entrywise `Ball` operations give: that is what the listings compute (each operation of the
radius lines is a rounding of a nondecreasing function of the largest magnitude), and what the tests
find in every case they compare (`api.ball_vector.*`), but it is not claimed. What is claimed of the
one radius is containment (V2), when it is finite (V4), and for the scaling by a power of two its
exactness.

## Compositions made in the header

Three operations are not one loop, and what holds of each is the statements of its calls,
composed. The compositions themselves are not machine-checked.

- **`axpy(a, x, y, z)`** $= aX + Y$: $S = X a$ (`scale`, loop `bv_scale_k`) written into `z`, then
  $S + Y$ (`add`, loop `bv_add_k`) into `z` in place
  ([axpy of ball vectors](../developer/architecture.md#axpy-of-ball-vectors)). Containment
  composes: for $x$ in entry $i$ of $X$ and $y$ in entry $i$ of $Y$, $a x$ is in entry $i$ of $S$,
  so $a x + y$ is in entry $i$ of $Z$. The result is canonical, the whole space propagates, and a
  finite $Z$ has finite $X$, $a$ and $Y$. When it is finite is the V4 of each loop in turn, the
  second on the computed $S$: it is not stated once of $X$, $Y$ and $a$. Its radius is at least the
  largest of the entrywise radii of a `Ball` axpy, and equal when one entry has both largest
  magnitudes (of the scaled centers and of the results); not claimed. `z` may be exactly `x`, not
  `y` (the scaling would overwrite `y` before the sum reads it), which `KAIRN_CHECKS` checks. The
  tests find `axpy` bit for bit the two calls in both orders, and the oracle judges `axpy(1, X, Y)`
  against the claims of `bv_add_k`, `axpy(-1, Y, X)` against those of `bv_sub_k` and `axpy(a, X, 0)`
  against those of `bv_scale_k`.
- **`norm_upper(x)`**, an upper bound $b$ of the magnitude of every entry of every member: $n$ =
  `norm_upper_k` of the centers (the fold of maxima, which claims $V \le n \le \mathrm{RU}(V)$ stepped
  up $s$ times, $V$ the largest magnitude of a center, $s = 0$ for one limb and $1$ for two, with a
  flag), then $b$ = `add_up(n, r)` ([`add_up_entry`](add_up_entry.md): $\mathrm{RU}(n + r)$), or
  $+\infty$ when the flag is false (two limbs, a leading limb of magnitude the largest finite
  number). Every member $x$ of entry $i$ has $\lvert x\rvert \le \lvert c_i\rvert + r \le V + r \le
  n + r \le b$; the inequality is the header's argument from the two claims, checked in exact terms
  on every case of `api.ball_vector.*`, and the oracle judges `norm_upper` of a ball vector of
  radius 0, which is $n$, against the claims of `norm_upper_k`. $+\infty$ for the whole space. The
  design page names `add_up_1`; the header calls the entry form, `add_up_1` on its operands guarded
  (each guard the identity on a value), because a public header calls only entry kernels.
- **`ldexp(x, n, z)` when $2^n$ is not a number of `T`** (for `double`, $n$ above 1023 or below
  $-1074$): two or three calls of the scaling by a power of two, as `ldexp` of a [`Ball`](ball_mul_pow2_2_full.md).
  Containment and exactness of each call give those of the whole. That the steps may stop at
  $n = \pm 2098$ or so for `double` is argued, not machine-checked: beyond, any ball vector but the
  point 0 becomes the whole space (above) or centers 0 and a radius of at least $2\eta$ (below).

## The two orders

Every loop but the product is generated in two orders ([Folds, the extension of the IR](../developer/design/milestone2.md#folds-the-extension-of-the-ir); the tag is in `kairn/order.hpp`):
the *sequential* order, entry after entry, and the *lane order* of $W$ lanes, which the packed code
of AVX2 ($W$ = 4 for `double`, 8 for `float`) and NEON (2 and 4) computes. Every function computes
in the **fast order** of the translation unit: the lane order of the register of
[`Packed`](packed.md) where it has more than one lane, the sequential order where it has one (no
AVX2 and no NEON, or `KAIRN_PACKED_FORM_SCALAR`). With **`kairn::sequential`** as its first argument,
`kairn::add(kairn::sequential, x, y, z)`, it computes in the sequential order in every build.

What differs between the two: nothing that is stated. The statements V1 to V4 are proved for the
sequential order and for the lane order of every $W$. And on this tree the bits do not differ
either: the state of each loop is a maximum and a conjunction, which do not depend on the order, and
each center is computed from its own entry; the tests compare the two orders bit for bit on every
operation and length, a zero center compared as a zero under MSVC, whose packed code drops the
guard's $+0$ ([Packed](packed.md)). That equality is not claimed. The functions of each form are in
the inline namespace of that form of `Packed`, so that translation units compiled for different
instruction sets link into one program; the class `BallVector` is the same in all.

## Views, in place and lengths

A view is $k$ pointers, a length and a pointer to the radius, trivially copyable. An operation
writing through a view writes its arrays and its radius. Constness is shallow, as for `std::span`:
a `const BallVectorView<double, 1>` is still written by an operation given it as `z`. A view of
`T` converts to a view of `const T`, not back, and a `BallVector` converts to its views; nothing
writes through a view of `const T`. `subview(offset, count)`, of a view of `const T` only, sees part
of the entries with the same radius, as the shifted operands of a subdivision need; a view of
mutable limbs has none, since an operation that wrote a part would change the radius of every entry.

**In place**: the array written may be exactly one of the arrays read (the same pointers), where the
table says so; otherwise it overlaps none of them. A partial overlap is not supported. `x += x` is
`add(x, x, x)`, supported. The radius of an operand is read before the loop writes the result's.

## Checks

**The environment, in every build.** Every operation on whole ball vectors is a batch entry: the
constructors from centers and a radius (of a `BallVector` and of a view), the negation, the sum,
the difference, the scalings, `ldexp`, `half`, `axpy`, the product of polynomials, `norm_upper`, and
the operators that call them. Before its loop each reads the floating-point environment once, as
`kairn::environment_ok()` does, with `KAIRN_CHECKS` 1 or 0, and if it is not the default one calls
`KAIRN_ENVIRONMENT_FAILURE` with the message of a debug build
(`kairn: the floating-point environment: the rounding mode is not to nearest ...`, or flush to
zero), which by default stops the program: the default environment is the precondition of each,
checked. The negation, a change of sign and a copy of the radius, leaves the rounding mode out;
every other operation reads it, the constructors of one limb among them (below). One read of the
control register per call.

With `KAIRN_CHECKS` 1 (a build without `NDEBUG`; [The checks of a debug build](../developer/testing.md#the-checks-of-a-debug-build)), after the environment:

- every operation that rounds (all but the negation) checks the floating-point environment, the
  rounding mode included, then that every operand is canonical, and stops the program with
  `kairn: a ball vector: is not canonical ...` if not; the negation, which does not round, checks the
  environment without the rounding mode, and its operand under rounding to nearest only for two
  limbs (the test of a canonical pair rounds);
- the constructors check the environment, the rounding mode included (for one limb the only
  rounded operations are the guards and the loop's $m - m$, whose values do not depend on the mode,
  but under rounding downward $m - m$ and so the radius are $-0$, and with one compiler, clang-cl,
  the constructor then returned the whole space: the result is not independent of the mode), report
  a negative radius as almost surely a mistake (`kairn: a ball vector: has a negative radius`), and
  for two limbs a center that is not canonical; a NaN or an infinite radius, which make the whole
  space, are accepted;
- operands of lengths that do not match (`kairn: ball vectors: of lengths that do not match ...`),
  `axpy` writing the arrays of `y`, and a product writing an array that it reads, stop the program.

With `KAIRN_CHECKS` 0 nothing but the environment is checked. The accessors, the whole space, the
views and the copy of a view, which copy limbs, check nothing.

## Regular type

`BallVector` is trivially copyable and standard-layout, of size $(kN + 1)$ `sizeof(T)`, with no heap
memory and no global state; usable in arrays and as a member. Every function is `noexcept` and
allocates nothing. `constexpr`: the default constructor, `whole()`, the accessors and the views;
not the constructors from centers nor any operation, since the generated loops are not
(`api.reject.ball_vector.not_constexpr`). No operation needs the marker `kairn::unverified`: every
loop this header calls is proved. The operations are ordinary inline functions in every setting of
`KAIRN_ENCLOSURE_CODE`: each calls one loop, itself an ordinary inline function whose end (the
radius and the finish) is never inlined.

## Compile time

Including `kairn/ball_vector.hpp` parses the generated packed header of its form, `kairn/packed.hpp`
and `kairn/soa.hpp`. Measured for a file that includes `kairn/kairn.hpp` and has an empty `main`,
compiled at `-O2`, the median of seven compilations interleaved:

| Machine, compiler, form | `kairn/kairn.hpp` | and `packed.hpp`, `soa.hpp` | and `ball_vector.hpp` | every operation used |
|---|---|---|---|---|
| Apple M3 Max, Apple clang 21, NEON | 0.156 s | 0.310 s | 0.460 s | 0.650 s |
| Apple M3 Max, GCC 16, NEON | 0.327 s | 0.692 s | 0.718 s | 1.176 s |
| AMD EPYC 7452, GCC 13, AVX2 (`-mavx2 -mfma`), under a load average of about 40 | 0.465 s | 1.290 s | 1.314 s | 1.964 s |
| AMD EPYC 7452, Clang 18, AVX2, the same | 0.680 s | 1.594 s | 1.658 s | 2.178 s |

The last column is a file that calls every operation of one and two limbs once (each loop
instantiated for `double`). Of what the header adds to `kairn/packed.hpp` and `kairn/soa.hpp` with
Apple clang, about 0.09 s is libc++'s `<array>`, which the constructor from an `std::array` needs.
`kairn/kairn.hpp`, which stays cheap to include, therefore does not include it, as it does not
include `kairn/packed.hpp` and `kairn/soa.hpp`: a program includes `kairn/ball_vector.hpp` itself.

## What is tested

- **Against the oracle, through the public interface.** Each of the sixteen loops this header calls
  (`bv_make_1` and `bv_make_2_entry`, `bv_neg_k`, `bv_add_k`, `bv_sub_k`, `bv_scale_1` and
  `bv_scale_2_entry`, `bv_mul_pow2_k`, `bv_conv_k`, `norm_upper_k`) has forms in the runner of the public interface
  (`tests/api/runner_ball_vector.hpp`): its request lines, with arrays of every length class (0, 1,
  below, at and above the lanes, up to 64 in the quick tier and 256 in the full tier, 64 for the
  product in both) and every stratum of the oracle (the whole space,
  overflow, the thresholds of V4, cancellation, subnormal numbers, zeros, exactness), are completed
  through the constructors, the functions on views, the operators of `BallVector` (on the lengths
  of the oracle's schedule up to 17), in place, and in both orders, and judged against the loop's
  claims, in the quick tier (`api.oracle.LOOP.FORMAT`) and the full tier, with every flag set's
  runner, and with the runner of the packed forms alone on x86-64 builds without AVX2.
- `tests/api/ball_vector.cpp` (`api.ball_vector.FORM`, in every form of `Packed` the build has): the
  types, the constructors on every class of radius and center, the two orders bit for bit, in place,
  the value forms against the views, each center and the one radius against the entrywise `Ball`
  operations, `axpy` bit for bit its two calls, the argument of `norm_upper` in exact terms, and the
  exact scaling by a power of two, the steps of `ldexp` included.
- The products of the program passed in (`api.boundary.ball_vector.*`), the checks of a debug build
  (`api.checks.*`), what must not compile (`api.reject.ball_vector.*`), the program's names
  (`api.shadow`) and the platform's macros (`api.platform_macros`), and the tutorial's program,
  checked in exact arithmetic (`api.example.ball_vectors.*`):
  [Testing](../developer/testing.md#ball-vectors).

## Not provided

An empty state; a radius per entry or weights (a program writes those on the functions on arrays
and its own radius theorem); the product of polynomials in the lane order; operations of a ball
vector with a `Ball` or a number, but the scaling by a `T`; a one-pass `axpy` (the generator has no
kernel for it: [axpy of ball vectors](../developer/architecture.md#axpy-of-ball-vectors)); dispatch
at run time; constant evaluation of any operation.
