# Packed numbers in registers

`kairn::Packed<T, k>` holds $W$ numbers of $k$ limbs of type `T` in SIMD registers, limb $j$ of
all $W$ numbers in one register, for `T` = `float` or `double` and $k = 1$ or $2$. Its operations
are those of [`Expansion<T, k>`](index.md) that have a kernel, under the same names, computed by
the packed form of that kernel. `kairn::PackedMask<T>` holds the $W$ truth values that a
comparison returns. They are in `kairn/packed.hpp`, which `kairn/kairn.hpp` does not include
([below](#compile-time)).

**Status: each operation has, in each lane, the statement of the scalar operation of the same
name.** `Packed` has no arithmetic of its own. Each operation calls the packed form of the kernel
that the operation of `Expansion` calls; the generator writes the packed form from the same
description as the scalar kernel, and its tests compare the two lane by lane, bit for bit. So
lane $i$ of `x + y` is the number that `Expansion`'s `x + y` gives for lane $i$ of `x` and lane $i$
of `y`, with that operation's proved bound, its results for infinities and NaN, and its
requirement of canonical operands: the page of each kernel applies to each lane. Nothing is stated
across lanes: the $W$ operations are side by side, never combined.

```cpp
template <class T, int K> struct Packed {
    using limb_type = T;  using value_type = Expansion<T, K>;
    using register_type = /* __m256d, __m256, float64x2_t, float32x4_t, or T */;
    using mask_type = PackedMask<T>;
    static constexpr int limbs = K, lanes = /* W */;
    register_type limb[K];                         // public, most significant limb first
    Packed();                                      // zero in every lane
    static Packed broadcast(const Expansion<T, K>& x);
    static Packed load(const T* x0);               // K = 1
    static Packed load(const T* x0, const T* x1);  // K = 2: from_limbs in each lane
    static Packed load_unchecked(...);  static Packed load_partial(..., int count, fill);
    static Packed from_limbs(register_type...);  static Packed from_limbs_unchecked(register_type...);
    void store(T* x0[, T* x1]) const;  void store_partial(T* x0[, T* x1], int count) const;
    Expansion<T, K> lane(int i) const;  void set_lane(int i, const Expansion<T, K>& x);
};
template <class T> struct PackedMask { register_type bits; bool lane(int i) const; };
bool any(PackedMask<T>), all(PackedMask<T>);  PackedMask<T> m & m, m | m, !m;
Packed<T, K> select(PackedMask<T> m, Packed<T, K> a, Packed<T, K> b);
```

## The three forms

Which form a translation unit gets is decided by the instruction set it is compiled for, once, by
`KAIRN_PACKED_FORM`. There is no dispatch at run time.

| `KAIRN_PACKED_FORM` | When | $W$ for `double` | $W$ for `float` | The kernels |
|---|---|---|---|---|
| `KAIRN_PACKED_FORM_AVX2` | `__AVX2__` and `__FMA__` (MSVC: `/arch:AVX2`) | 4 | 8 | `kairn/gen/avx2.hpp` |
| `KAIRN_PACKED_FORM_NEON` | otherwise, on AArch64 | 2 | 4 | `kairn/gen/neon.hpp` |
| `KAIRN_PACKED_FORM_SCALAR` | otherwise | 1 | 1 | `kairn/gen/scalar.hpp`, the scalar kernels themselves |

A loop written with `Packed<T, k>` and `Packed<T, k>::lanes` compiles unchanged in the three. A
program may define `KAIRN_PACKED_FORM` to `KAIRN_PACKED_FORM_SCALAR` before including Kairn, to
get one lane anywhere; to one of the other two only where the target has it (otherwise the
generated header's `#error` says what is missing). On x86-64, `kairn::fma` adds `-mfma`, which
gives the scalar form: the AVX2 form needs `-mavx2 -mfma`, `-march=x86-64-v3` (or later), or
`/arch:AVX2`.

Each form is in an inline namespace of its own (`kairn::packed_avx2`, `kairn::packed_neon`,
`kairn::packed_scalar`), so that translation units compiled for different instruction sets can be
linked into one program: each has its own `Packed`, and a `Packed` of one form is not one of
another.

## The operations

Every operation is `noexcept` and forced inline. None is usable in constant evaluation.
`Packed<T, 1>` stands for a packed `T`: next to a `Packed<T, 2>` it is the limb operand of the
mixed forms (`x + a`, `a - x`, `x < a`), as a `T` or an `Expansion<T, 1>` is next to an
`Expansion<T, 2>`. No operation takes an `Expansion` or a `T` operand: a program broadcasts it
(`Packed<T, 2>::broadcast(e)`, `Packed<T, 1>::broadcast(Expansion<T, 1>(a))`). No operand
converts, so each form is gated on the kernel it calls; every kernel these call is proved today,
and an operation whose kernel is not proved does not compile (there is no `kairn::unverified`
form).

| Packed, $k = 2$ | In each lane, as | Kernel |
|---|---|---|
| `x + y`, `x += y` | `Expansion`'s `x + y` | [`add_2_2_full`](add_2_2_full.md) |
| `x + a`, `a + x`, `x += a` | `x + a` | [`add_2_1_full`](add_2_1_full.md) |
| `x - y`, `x -= y` | `x - y` | [`sub_2_2_full`](sub_2_2_full.md) |
| `x - a`, `x -= a` | `x - a` | [`sub_2_1_full`](sub_2_1_full.md) |
| `a - x` | `a - x` | [`sub_1_2_full`](sub_1_2_full.md) |
| `x * y`, `x *= y` | `x * y` | [`mul_2_2_full`](mul_2_2_full.md) |
| `x * a`, `a * x`, `x *= a` | `x * a` | [`mul_2_1_full`](mul_2_1_full.md) |
| `add_fast(x, y)` | `add_fast(x, y)` | [`add_fast_2_2_full`](add_fast_2_2_full.md) |
| `ldexp(x, n)`, `half(x)` | `ldexp(x, n)`, `half(x)`, with the same `n` in every lane | [`mul_pow2_2_full`](mul_pow2_2_full.md) |
| `-x`, `abs(x)` | `-x`, `abs(x)` | [`neg_2`](neg_2.md), [`abs_2`](abs_2.md) |
| `x < y`, `x > y`, `x <= y`, `x >= y`, `x == y`, `x != y` | the comparison | [`lt_2_2`](lt_2_2.md), [`le_2_2`](le_2_2.md), [`eq_2_2`](eq_2_2.md) |
| the same with `a` on either side | the comparison with a limb | [`lt_2_1`](lt_2_1.md), [`le_2_1`](le_2_1.md), [`eq_2_1`](eq_2_1.md), [`lt_1_2`](lt_1_2.md), [`le_1_2`](le_1_2.md) |
| `to_nearest(x)`, `Packed<T, 1>(x)` (explicit) | `to_nearest(x)`, `Expansion<T, 1>(x)` | [`to_nearest_2`](to_nearest_2.md) |
| `to_down(x)`, `to_up(x)`, `abs_upper(x)` | the same, a `Packed<T, 1>` | [`to_down_2`](to_down_2.md), [`to_up_2`](to_up_2.md), [`abs_upper_2`](abs_upper_2.md) |
| `Packed<T, 2>(a)` (implicit) | `Expansion<T, 2>(a)` | [`make_2`](make_2.md) |
| `load(x0, x1)`, `from_limbs(r0, r1)` | `Expansion<T, 2>::from_limbs` | [`make_2_limbs`](make_2_limbs.md) |
| `finite::add`, `sub`, `mul` (each form above), `add_fast`, `ldexp` | the functions of `kairn::finite` | the cores [`add_2_2`](add_2_2.md), [`add_2_1`](add_2_1.md), [`sub_2_2`](sub_2_2.md), [`sub_2_1`](sub_2_1.md), [`sub_1_2`](sub_1_2.md), [`mul_2_2`](mul_2_2.md), [`mul_2_1`](mul_2_1.md), [`add_fast_2_2`](add_fast_2_2.md), [`mul_pow2_2`](mul_pow2_2.md) |

The comparisons return a `PackedMask<T>`, whose lane $i$ is the comparison of lane $i$: as for
`Expansion`, false when an operand is a NaN, and true for `!=`. As for `Expansion`, the operators
return IEEE-like results (canonical infinities and NaN), and `kairn::finite` has the cores without
the fix-up; `ldexp` and `half` beyond the powers of two of `T` take the same steps as for a number,
a composition argued and tested but not machine-checked
([What holds today](../getting-started/guarantees.md#overflow-and-non-finite-values)).

**One limb.** `x + y`, `x - y` (which is `add_1_1` on `x` and $-y$, as for `Expansion<T, 1>`),
`x * y`, the compound forms, `add_fast`, `ldexp`, `half` and the functions of `kairn::finite` call
the packed forms of [`add_1_1`](add_1_1.md) and [`mul_1_1`](mul_1_1.md). Negation, `abs`, the six
comparisons and `to_nearest`, `to_down`, `to_up`, `abs_upper` are, as for `Expansion<T, 1>`, the
exact operations of `T`: a sign bit flipped or cleared, a comparison of lanes, the value itself.
They have no kernel; they are there because the operations of two limbs are, so that a loop over
$k$ reads the same for both.

One difference from `Expansion<T, 1>`, in the sign of a zero only. The product of one limb is the
kernel `mul_1_1`, whose code is the opaque product $\mathrm{fma}(a, b, +0)$, the same in its scalar
and packed forms; `Expansion<T, 1>`'s `x * y` is the product of `T`. They give the same value, but
where the product of `T` is $-0$ (as for $-1 \cdot 0$, or a negative product that underflows),
the kernel gives $+0$. So `x * y`, `x *= y`, `half`, `ldexp` and `finite::mul` of `Packed<T, 1>`
can give $+0$ where `Expansion<T, 1>` gives $-0$. Kairn gives the sign of a zero no meaning, and
the oracle does not judge it.

**Not here**, with the reason: `sign`, `isfinite` and `is_normalized` (no kernel computes them;
`is_normalized` of two limbs rounds); the marked forms of `kairn::unverified`; the building blocks
of `kairn/blocks.hpp`; `Ball` and `Interval` (no packed type); a sum or any other combination of
the lanes (a program writes it with `lane()` and the operators of `Expansion`, in the order it
chooses: [the tutorial](../tutorials/vector-loop.md) does).

## Moves, loads and stores

These copy limbs and compute nothing, but for the guard of the loads of two limbs.

- `Packed()` is zero in every lane; `broadcast(x)` is `x` in every lane, its limbs copied.
- `lane(i)` and `set_lane(i, x)` read and write lane $i$, $0 \le i < W$, as a number: its limbs,
  copied.
- `load(x0)` reads the $W$ numbers `x0[0]` to `x0[W - 1]`; `load(x0, x1)`, lane $i$ as
  `Expansion<T, 2>::from_limbs` of `x0[i]` and `x1[i]`: each limb guarded (an addition of $+0$,
  [rule R3](../developer/architecture.md#the-kernel-ir): the program may have written there a
  product that the compiler could still fuse), so a zero limb may change sign, and with
  `KAIRN_CHECKS` 1 each pair checked. `from_limbs(r0, r1)` is the same on registers;
  `load_unchecked` and `from_limbs_unchecked` the same without the check.
- `store(x0[, x1])` writes lane $i$ to `x0[i]` (and `x1[i]`), copied.
- No pointer needs any alignment: the loads and stores are unaligned.
- The tail of a loop: `load_partial(x0[, x1], count, fill)` reads only the first `count` elements,
  $0 \le$ `count` $\le W$, into lanes 0 to `count` $- 1$, as `load` reads them, and puts `fill`
  (zero by default) into the other lanes, read the same way; `store_partial(x0[, x1], count)`
  writes lanes 0 to `count` $- 1$ only. The views of [`kairn/soa.hpp`](soa.md) have the same, at
  an index.
- `limb[j]` is public, as `Expansion`'s limbs are: a register written directly must hold, in each
  lane, a canonical number, and no limb that is a product the compiler can see being computed.

`PackedMask<T>` has its register in `bits`, each lane every bit set (true) or every bit clear;
`lane(i)`, `any`, `all`, `&`, `|` and `!` read and combine them, and `select(m, a, b)` takes each
lane from `a` where `m` is true and from `b` where it is false: limbs moved, each lane exactly
the number it was.

## Checks

With `KAIRN_CHECKS` 1 (a build without `NDEBUG`,
[Troubleshooting](../getting-started/index.md#when-a-check-of-a-build-without-ndebug-fails)), each operation
checks the floating-point environment once, then every lane of every operand, exactly as the
operation of `Expansion` of the same name checks its one operand, with the same messages: a lane
that is not canonical stops the program with `kairn: an operand: is not canonical ...`. The loads
and `from_limbs` check each lane as `Expansion<T, 2>::from_limbs` does. The operations that do not
round for `Expansion` do not check the rounding mode here either (negation, `abs`, comparisons,
the conversions to one limb); the moves check nothing.

## Regular type

`Packed` and `PackedMask` are trivially copyable and standard-layout; `sizeof(Packed<T, k>)` is
$k$ registers. They hold no heap memory and have no state outside their registers, and nothing
in `kairn/packed.hpp` has global state.

## Compile time

Including `kairn/packed.hpp` parses the generated header of its form and the compiler's intrinsics
header. Measured for a file that includes `kairn/kairn.hpp` and has an empty `main`, compiled at
`-O2`, the median of seven compilations, and the same file including `kairn/packed.hpp` and
`kairn/soa.hpp` as well:

| Machine, compiler, form | `kairn/kairn.hpp` | and the two headers |
|---|---|---|
| Apple M3 Max, Apple clang 21, NEON | 0.106 s | 0.218 s |
| Apple M3 Max, GCC 16, NEON | 0.194 s | 0.428 s |
| AMD EPYC 7452, GCC 13, AVX2 (`-mavx2 -mfma`) | 0.318 s | 1.001 s |
| AMD EPYC 7452, Clang 18, AVX2 | 0.489 s | 1.216 s |
| the same four in the scalar form | | 0.01 to 0.04 s more than `kairn/kairn.hpp` |

In the forms with SIMD the two headers double or triple the cost of `kairn/kairn.hpp`, which
therefore does not include them: a program includes `kairn/packed.hpp` or `kairn/soa.hpp` itself.

## What is tested

- **Against the oracle, through the public interface.** The runner of the public interface
  (`tests/api/runner.cpp`) has a packed form for each of its forms that `Packed` or the views
  have: the oracle's request lines are completed one per lane, in registers whose other lanes hold
  other lines (a NaN beside a finite number, an overflow in one lane only), every lane position
  taking its share, and judged against the claims of the scalar kernel, in the quick and the full
  tier and with every flag set's runner. On x86-64 builds whose flags give the scalar form, a
  runner built for AVX2 runs the packed forms too.
- **Bit for bit against the scalar operations** (`tests/api/packed.cpp`): every operation above,
  `float` and `double`, one and two limbs, on every pair of a corpus of every kind of value, one
  pair per lane position in turn, in the form of the build, the scalar form and, where it applies,
  AVX2. Every limb of every lane equals the scalar result (a NaN compared as a NaN), but for the
  sign of a zero product of one limb, above.
- **The checks**, the compile-fail cases and the tutorial's loop in the three forms:
  [Testing](../developer/testing.md#packed-and-the-containers).
