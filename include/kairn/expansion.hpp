/// @file
/// Expansion<T, 1> and Expansion<T, 2>: a value stored as the unevaluated sum of one or two limbs
/// of type T (float or double), and their operations.
///
/// Every operation forwards to one generated kernel (include/kairn/gen/scalar.hpp) whose claims
/// are in gen/claims.json; the comment of each operation names it. An operation whose kernel is
/// proved compiles as written; any other needs the kairn::unverified marker on one operand
/// (config.hpp). Which kernels are proved is read from include/kairn/gen/bounds.hpp, never written
/// here, so an operation loses the need for the marker when its proof is checked and the
/// generator is rerun. Each operation is gated on the kernel it calls, and the mixed forms (a
/// two-limb number with a limb or a one-limb number) are exact matches, so that an operation
/// whose kernel is not proved can never compile through a conversion to another kernel.
///
/// The arithmetic of two limbs returns IEEE-like results (decision D5): the operators call the
/// full kernels of docs/developer/design/milestone1.md ("IEEE-like results"), each a finite core
/// followed by a fix-up, so that every result is canonical, as T's results are. kairn::finite::
/// has the same operations on the cores alone, for code that knows its values stay finite.
#pragma once

#include "config.hpp"
#include "environment.hpp"
#include "gen/bounds.hpp"
#include "gen/scalar.hpp"

#include <bit>
#include <cstdint>
#include <limits>
#include <type_traits>

namespace kairn {

/// A k-number: the value limb[0] + ... + limb[K - 1], exactly, with limbs of type T (float or
/// double), most significant first. Defined for K = 1 and K = 2.
///
/// A one-limb number is any value of T. A two-limb number is *canonical* when it is finite and
/// normalized (each limb equal to the sum of itself and the next one rounded to nearest:
/// x0 + x1 == x0 in floating point), or (+inf, 0), (-inf, 0), or (NaN, NaN). Every constructor
/// and every operator returns canonical numbers, and requires canonical operands. See
/// docs/developer/design/phase0/numbers.md and docs/developer/design/milestone1.md.
template <class T, int K>
struct Expansion;

template <class T, int K>
class Ball;

namespace detail {

template <class X>
struct is_ball_t : std::false_type {};
template <class T, int K>
struct is_ball_t<Ball<T, K>> : std::true_type {};
template <class X>
struct is_ball_t<Unverified<X>> : is_ball_t<X> {};
/// Whether X is a Ball, marked or not.
template <class X>
concept ball = is_ball_t<std::remove_cvref_t<X>>::value;

/// Whether the limb x is finite, from its bit pattern (std::isfinite is not constexpr in C++20).
template <limb T>
KAIRN_FORCEINLINE constexpr bool finite(T x) noexcept {
    if constexpr (sizeof(T) == 8) {
        return (std::bit_cast<std::uint64_t>(x) & 0x7ff0000000000000u) != 0x7ff0000000000000u;
    } else {
        return (std::bit_cast<std::uint32_t>(x) & 0x7f800000u) != 0x7f800000u;
    }
}

// The exponents of the powers of two that are numbers of T: from that of the smallest subnormal
// (-1074 for double, -149 for float) to that of the largest power (1023, 127).
template <limb T>
inline constexpr int pow2_min = std::numeric_limits<T>::min_exponent - std::numeric_limits<T>::digits;
template <limb T>
inline constexpr int pow2_max = std::numeric_limits<T>::max_exponent - 1;

/// 2^n, for n from pow2_min<T> to pow2_max<T>, built from its bit pattern.
template <limb T>
KAIRN_FORCEINLINE constexpr T pow2(int n) noexcept {
    if constexpr (sizeof(T) == 8) {
        if (n >= -1022) return std::bit_cast<T>(std::uint64_t(n + 1023) << 52);
        return std::bit_cast<T>(std::uint64_t{1} << (n + 1074));
    } else {
        if (n >= -126) return std::bit_cast<T>(std::uint32_t(n + 127) << 23);
        return std::bit_cast<T>(std::uint32_t{1} << (n + 149));
    }
}

// Whether a two-limb number is canonical: finite and normalized, an infinity followed by a zero,
// or two NaN. Comparisons are written b > a and b >= a, never a < b or a <= b: one compiler's
// constant evaluator takes a < b for true when an operand is a NaN.
template <class T>
KAIRN_FORCEINLINE constexpr bool canonical(const Expansion<T, 2>& x) noexcept {
    const T x0 = x.limb[0], x1 = x.limb[1];
    if (finite(x0)) return finite(x1) && x0 + x1 == x0;
    if (x0 == x0) return x1 == 0;  // an infinity, then a zero of either sign
    return x1 != x1;               // two NaN
}
// Whether a two-limb number is admissible for the finite cores (kairn::finite::): normalized, or
// with a leading limb that is not finite (what a core may return after an overflow).
template <class T>
KAIRN_FORCEINLINE constexpr bool core_admissible(const Expansion<T, 2>& x) noexcept {
    return !finite(x.limb[0]) || (finite(x.limb[1]) && x.limb[0] + x.limb[1] == x.limb[0]);
}

template <limb T>
KAIRN_FORCEINLINE constexpr bool admissible(T) noexcept {
    return true;
}
template <class T>
KAIRN_FORCEINLINE constexpr bool admissible(const Expansion<T, 1>&) noexcept {
    return true;
}
template <class T>
KAIRN_FORCEINLINE constexpr bool admissible(const Expansion<T, 2>& x) noexcept {
    return canonical(x);
}

// The checks of KAIRN_CHECKS, once per operation: the environment, then canonical operands, which
// are not checked when the environment is not the default one and KAIRN_ENVIRONMENT_FAILURE
// returned (check_environment).
template <class... X>
KAIRN_FORCEINLINE constexpr void check([[maybe_unused]] const X&... x) noexcept {
#if KAIRN_CHECKS
    if (check_environment() && !(admissible(x) && ...))
        fail("an operand", "is not canonical (finite with x0 + x1 == x0, (+-inf, 0) or (NaN, NaN)), so no "
                           "guarantee applies to the result");
#endif
}
// The same for the finite cores, which accept what they may return themselves.
template <class T>
KAIRN_FORCEINLINE constexpr void check_core([[maybe_unused]] const Expansion<T, 2>& x) noexcept {
#if KAIRN_CHECKS
    if (check_environment() && !core_admissible(x))
        fail("an operand", "is not normalized (x0 + x1 is not x0), so no guarantee applies to the result");
#endif
}
template <class T>
KAIRN_FORCEINLINE constexpr void check_core(const Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    check_core(x);
    check_core(y);
}

// The operations, without their markers and constraints. Each calls one kernel; the public
// operators and functions below choose which may be called without kairn::unverified.

// k = 1: one IEEE 754 operation each. Under KAIRN_K1_CONTRACT Clang may fuse a product with a sum
// that uses it, as it does for plain T (config.hpp).
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> add(Expansion<T, 1> x, Expansion<T, 1> y) noexcept {
    KAIRN_DETAIL_K1_CONTRACT
    check(x, y);
    return Expansion<T, 1>(x.limb[0] + y.limb[0]);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> add(Expansion<T, 1> x, std::type_identity_t<T> a) noexcept {
    return add(x, Expansion<T, 1>(a));
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> add(std::type_identity_t<T> a, Expansion<T, 1> y) noexcept {
    return add(Expansion<T, 1>(a), y);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> sub(Expansion<T, 1> x, Expansion<T, 1> y) noexcept {
    KAIRN_DETAIL_K1_CONTRACT
    check(x, y);
    return Expansion<T, 1>(x.limb[0] - y.limb[0]);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> sub(Expansion<T, 1> x, std::type_identity_t<T> a) noexcept {
    return sub(x, Expansion<T, 1>(a));
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> sub(std::type_identity_t<T> a, Expansion<T, 1> y) noexcept {
    return sub(Expansion<T, 1>(a), y);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> mul(Expansion<T, 1> x, Expansion<T, 1> y) noexcept {
    KAIRN_DETAIL_K1_CONTRACT
    check(x, y);
    return Expansion<T, 1>(x.limb[0] * y.limb[0]);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> mul(Expansion<T, 1> x, std::type_identity_t<T> a) noexcept {
    return mul(x, Expansion<T, 1>(a));
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> mul(std::type_identity_t<T> a, Expansion<T, 1> y) noexcept {
    return mul(Expansion<T, 1>(a), y);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> neg(Expansion<T, 1> x) noexcept {
    check(x);
    return Expansion<T, 1>(-x.limb[0]);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> abs(Expansion<T, 1> x) noexcept {
    check(x);
    return Expansion<T, 1>(gen::abs_bits(x.limb[0]));
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> add_fast(Expansion<T, 1> x, Expansion<T, 1> y) noexcept {
    return add(x, y);
}
// a 2^n, rounded once. Beyond the powers of two of T, in steps: up, by 2^pow2_max as often as
// needed, then the rest (three steps above 2 pow2_max), each exact until one overflows; down, by
// 2^(n - pow2_min) and then by 2^pow2_min, where the first step is exact unless its result is
// subnormal, and then the second rounds it to zero, as one step would. Beyond the clamps every
// nonzero finite a overflows, or rounds to zero. This composition is written by hand: argued here
// and tested through the oracle, not machine-checked (deviation 17 of
// docs/developer/design/phase0/decisions.md).
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> ldexp(Expansion<T, 1> x, int n) noexcept {
    KAIRN_DETAIL_K1_CONTRACT
    check(x);
    constexpr int lo = pow2_min<T>, hi = pow2_max<T>;
    constexpr int up = hi + 1 - lo, down = lo - hi - 2;
    T a = x.limb[0];
    if (n > up) n = up;
    if (down > n) n = down;
    if (lo > n) {
        a = a * pow2<T>(n - lo);
        n = lo;
    }
    while (n > hi) {
        a = a * pow2<T>(hi);
        n -= hi;
    }
    return Expansion<T, 1>(a * pow2<T>(n));
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> half(Expansion<T, 1> x) noexcept {
    KAIRN_DETAIL_K1_CONTRACT
    check(x);
    return Expansion<T, 1>(x.limb[0] * T(0.5));
}
// b > a and b >= a, not a < b and a <= b: see canonical().
template <class T>
KAIRN_FORCEINLINE constexpr bool lt(Expansion<T, 1> x, Expansion<T, 1> y) noexcept {
    check(x, y);
    return y.limb[0] > x.limb[0];
}
template <class T>
KAIRN_FORCEINLINE constexpr bool le(Expansion<T, 1> x, Expansion<T, 1> y) noexcept {
    check(x, y);
    return y.limb[0] >= x.limb[0];
}
template <class T>
KAIRN_FORCEINLINE constexpr bool eq(Expansion<T, 1> x, Expansion<T, 1> y) noexcept {
    check(x, y);
    return x.limb[0] == y.limb[0];
}
template <class T>
KAIRN_FORCEINLINE constexpr T to_nearest(Expansion<T, 1> x) noexcept {
    check(x);
    return x.limb[0];
}
template <class T>
KAIRN_FORCEINLINE constexpr T to_down(Expansion<T, 1> x) noexcept {
    check(x);
    return x.limb[0];
}
template <class T>
KAIRN_FORCEINLINE constexpr T to_up(Expansion<T, 1> x) noexcept {
    check(x);
    return x.limb[0];
}
template <class T>
KAIRN_FORCEINLINE constexpr T abs_upper(Expansion<T, 1> x) noexcept {
    check(x);
    return gen::abs_bits(x.limb[0]);
}

// k = 2, construction: the constructor kernels guard the limbs they are given (rule R3), so that
// no limb of a number is a product the compiler can still fuse into the next operation.
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> make(std::type_identity_t<T> a) noexcept {
    Expansion<T, 2> x;
    gen::make_2(a, x.limb[0], x.limb[1]);
    return x;
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> make_limbs(std::type_identity_t<T> h, std::type_identity_t<T> l) noexcept {
    Expansion<T, 2> x;
    gen::make_2_limbs(h, l, x.limb[0], x.limb[1]);
    return x;
}

// k = 2, arithmetic: the full kernels. The one-limb operand of a sum or a difference is guarded
// by the kernel (add_2_1 guards it in its first line; sub_2_1 and sub_1_2 pass it to add_2_1);
// that of a product is only multiplied, which nothing can fuse.
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> add(Expansion<T, 2> x, Expansion<T, 2> y) noexcept {
    check(x, y);
    Expansion<T, 2> w;
    gen::add_2_2_full(x.limb[0], x.limb[1], y.limb[0], y.limb[1], w.limb[0], w.limb[1]);
    return w;
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> add(Expansion<T, 2> x, std::type_identity_t<T> a) noexcept {
    check(x);
    Expansion<T, 2> w;
    gen::add_2_1_full(x.limb[0], x.limb[1], a, w.limb[0], w.limb[1]);
    return w;
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> add(std::type_identity_t<T> a, Expansion<T, 2> y) noexcept {
    return add(y, a);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> add(Expansion<T, 2> x, Expansion<T, 1> y) noexcept {
    return add(x, y.limb[0]);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> add(Expansion<T, 1> x, Expansion<T, 2> y) noexcept {
    return add(y, x.limb[0]);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> sub(Expansion<T, 2> x, Expansion<T, 2> y) noexcept {
    check(x, y);
    Expansion<T, 2> w;
    gen::sub_2_2_full(x.limb[0], x.limb[1], y.limb[0], y.limb[1], w.limb[0], w.limb[1]);
    return w;
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> sub(Expansion<T, 2> x, std::type_identity_t<T> a) noexcept {
    check(x);
    Expansion<T, 2> w;
    gen::sub_2_1_full(x.limb[0], x.limb[1], a, w.limb[0], w.limb[1]);
    return w;
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> sub(std::type_identity_t<T> a, Expansion<T, 2> y) noexcept {
    check(y);
    Expansion<T, 2> w;
    gen::sub_1_2_full(a, y.limb[0], y.limb[1], w.limb[0], w.limb[1]);
    return w;
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> sub(Expansion<T, 2> x, Expansion<T, 1> y) noexcept {
    return sub(x, y.limb[0]);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> sub(Expansion<T, 1> x, Expansion<T, 2> y) noexcept {
    return sub(x.limb[0], y);
}
// Not constexpr: the products have fused operations and no constant-evaluation variant yet.
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> mul(Expansion<T, 2> x, Expansion<T, 2> y) noexcept {
    check(x, y);
    Expansion<T, 2> w;
    gen::mul_2_2_full(x.limb[0], x.limb[1], y.limb[0], y.limb[1], w.limb[0], w.limb[1]);
    return w;
}
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> mul(Expansion<T, 2> x, std::type_identity_t<T> a) noexcept {
    check(x);
    Expansion<T, 2> w;
    gen::mul_2_1_full(x.limb[0], x.limb[1], a, w.limb[0], w.limb[1]);
    return w;
}
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> mul(std::type_identity_t<T> a, Expansion<T, 2> y) noexcept {
    return mul(y, a);
}
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> mul(Expansion<T, 2> x, Expansion<T, 1> y) noexcept {
    return mul(x, y.limb[0]);
}
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> mul(Expansion<T, 1> x, Expansion<T, 2> y) noexcept {
    return mul(y, x.limb[0]);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> neg(Expansion<T, 2> x) noexcept {
    check(x);
    Expansion<T, 2> z;
    gen::neg_2(x.limb[0], x.limb[1], z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> abs(Expansion<T, 2> x) noexcept {
    check(x);
    Expansion<T, 2> z;
    gen::abs_2(x.limb[0], x.limb[1], z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> add_fast(Expansion<T, 2> x, Expansion<T, 2> y) noexcept {
    check(x, y);
    Expansion<T, 2> w;
    gen::add_fast_2_2_full(x.limb[0], x.limb[1], y.limb[0], y.limb[1], w.limb[0], w.limb[1]);
    return w;
}

// x 2^n through mul_pow2_2_full (Full) or the core mul_pow2_2, whose scalar must be a power of two
// of T. Beyond the powers of T, in steps. This composition is written by hand, so no generated
// statement is about it: what it returns is argued in milestone1.md, "Scaling beyond the powers
// of two of the format", and tested through the oracle, not machine-checked.
// - up: by 2^pow2_max as often as needed, then the rest. Scaling up is exact until it overflows,
//   and an infinity stays one, so only the last step decides, as one step would. Above
//   n = pow2_max + 1 - pow2_min (2098 for double) every nonzero finite x overflows, so n stops
//   there; up to it, three steps may be needed (two reach only 2^(2 pow2_max)).
// - down: by 2^(n - pow2_min), then by 2^pow2_min. A limb that the first step leaves normal is
//   scaled exactly; one it makes subnormal (it may lose bits there) is then below 2^pow2_min times
//   the smallest normal number, and the second step rounds it to zero. So the second step rounds
//   each limb at most once, by at most half a subnormal step, and the bound of one step, eta,
//   still holds. Below
//   n = pow2_min - pow2_max - 2 (-2099 for double) every finite x rounds to zero, so n stops there.
template <bool Full, class T>
KAIRN_FORCEINLINE Expansion<T, 2> scale2(Expansion<T, 2> x, T c) noexcept {
    Expansion<T, 2> z;
    if constexpr (Full) {
        gen::mul_pow2_2_full(x.limb[0], x.limb[1], c, z.limb[0], z.limb[1]);
    } else {
        gen::mul_pow2_2(x.limb[0], x.limb[1], c, z.limb[0], z.limb[1]);
    }
    return z;
}
template <bool Full, class T>
KAIRN_FORCEINLINE Expansion<T, 2> ldexp_steps(Expansion<T, 2> x, int n) noexcept {
    constexpr int lo = pow2_min<T>, hi = pow2_max<T>;
    constexpr int up = hi + 1 - lo, down = lo - hi - 2;
    if (n > up) n = up;
    if (down > n) n = down;
    if (lo > n) {
        x = scale2<Full>(x, pow2<T>(n - lo));
        n = lo;
    }
    while (n > hi) {
        x = scale2<Full>(x, pow2<T>(hi));
        n -= hi;
    }
    return scale2<Full>(x, pow2<T>(n));
}
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> ldexp(Expansion<T, 2> x, int n) noexcept {
    check(x);
    return ldexp_steps<true>(x, n);
}
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> half(Expansion<T, 2> x) noexcept {
    check(x);
    return scale2<true>(x, T(0.5));
}

// k = 2, comparisons and conversions: kernels that need no fix-up.
#define KAIRN_DETAIL_K2_COMPARE(NAME)                                                                    \
    template <class T>                                                                                   \
    KAIRN_FORCEINLINE constexpr bool NAME(Expansion<T, 2> x, Expansion<T, 2> y) noexcept {               \
        check(x, y);                                                                                     \
        bool m = false;                                                                                  \
        gen::NAME##_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], m);                                  \
        return m;                                                                                        \
    }                                                                                                    \
    template <class T>                                                                                   \
    KAIRN_FORCEINLINE constexpr bool NAME(Expansion<T, 2> x, std::type_identity_t<T> a) noexcept {       \
        check(x);                                                                                        \
        bool m = false; /* a is only compared: no guard */                                               \
        gen::NAME##_2_1(x.limb[0], x.limb[1], a, m);                                                     \
        return m;                                                                                        \
    }                                                                                                    \
    template <class T>                                                                                   \
    KAIRN_FORCEINLINE constexpr bool NAME(Expansion<T, 2> x, Expansion<T, 1> y) noexcept {               \
        return NAME(x, y.limb[0]);                                                                       \
    }
KAIRN_DETAIL_K2_COMPARE(lt)
KAIRN_DETAIL_K2_COMPARE(le)
KAIRN_DETAIL_K2_COMPARE(eq)
#undef KAIRN_DETAIL_K2_COMPARE
template <class T>
KAIRN_FORCEINLINE constexpr bool lt(std::type_identity_t<T> a, Expansion<T, 2> y) noexcept {
    check(y);
    bool m = false;
    gen::lt_1_2(a, y.limb[0], y.limb[1], m);
    return m;
}
template <class T>
KAIRN_FORCEINLINE constexpr bool le(std::type_identity_t<T> a, Expansion<T, 2> y) noexcept {
    check(y);
    bool m = false;
    gen::le_1_2(a, y.limb[0], y.limb[1], m);
    return m;
}
template <class T>
KAIRN_FORCEINLINE constexpr bool eq(std::type_identity_t<T> a, Expansion<T, 2> y) noexcept {
    return eq(y, a);
}
template <class T>
KAIRN_FORCEINLINE constexpr bool lt(Expansion<T, 1> x, Expansion<T, 2> y) noexcept {
    return lt(x.limb[0], y);
}
template <class T>
KAIRN_FORCEINLINE constexpr bool le(Expansion<T, 1> x, Expansion<T, 2> y) noexcept {
    return le(x.limb[0], y);
}
template <class T>
KAIRN_FORCEINLINE constexpr bool eq(Expansion<T, 1> x, Expansion<T, 2> y) noexcept {
    return eq(y, x.limb[0]);
}
template <class T>
KAIRN_FORCEINLINE constexpr T to_nearest(Expansion<T, 2> x) noexcept {
    check(x);
    T t = T(0);
    gen::to_nearest_2(x.limb[0], x.limb[1], t);
    return t;
}
template <class T>
KAIRN_FORCEINLINE constexpr T to_down(Expansion<T, 2> x) noexcept {
    check(x);
    T t = T(0);
    gen::to_down_2(x.limb[0], x.limb[1], t);
    return t;
}
template <class T>
KAIRN_FORCEINLINE constexpr T to_up(Expansion<T, 2> x) noexcept {
    check(x);
    T t = T(0);
    gen::to_up_2(x.limb[0], x.limb[1], t);
    return t;
}
template <class T>
KAIRN_FORCEINLINE constexpr T abs_upper(Expansion<T, 2> x) noexcept {
    check(x);
    T t = T(0);
    gen::abs_upper_2(x.limb[0], x.limb[1], t);
    return t;
}

// k = 2, the finite cores (kairn::finite::), without the fix-up.
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> core_add(Expansion<T, 2> x, Expansion<T, 2> y) noexcept {
    check_core(x, y);
    Expansion<T, 2> z;
    gen::add_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> core_add(Expansion<T, 2> x, std::type_identity_t<T> a) noexcept {
    check_core(x);
    Expansion<T, 2> z;
    gen::add_2_1(x.limb[0], x.limb[1], a, z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> core_sub(Expansion<T, 2> x, Expansion<T, 2> y) noexcept {
    check_core(x, y);
    Expansion<T, 2> z;
    gen::sub_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> core_sub(Expansion<T, 2> x, std::type_identity_t<T> a) noexcept {
    check_core(x);
    Expansion<T, 2> z;
    gen::sub_2_1(x.limb[0], x.limb[1], a, z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> core_sub(std::type_identity_t<T> a, Expansion<T, 2> y) noexcept {
    check_core(y);
    Expansion<T, 2> z;
    gen::sub_1_2(a, y.limb[0], y.limb[1], z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> core_mul(Expansion<T, 2> x, Expansion<T, 2> y) noexcept {
    check_core(x, y);
    Expansion<T, 2> z;
    gen::mul_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> core_mul(Expansion<T, 2> x, std::type_identity_t<T> a) noexcept {
    check_core(x);
    Expansion<T, 2> z;
    gen::mul_2_1(x.limb[0], x.limb[1], a, z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> core_add_fast(Expansion<T, 2> x, Expansion<T, 2> y) noexcept {
    check_core(x, y);
    Expansion<T, 2> z;
    gen::add_fast_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> core_ldexp(Expansion<T, 2> x, int n) noexcept {
    check_core(x);
    return ldexp_steps<false>(x, n);
}
// The other operand orders and types, as the operators have them.
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> core_add(std::type_identity_t<T> a, Expansion<T, 2> y) noexcept {
    return core_add(y, a);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> core_add(Expansion<T, 2> x, Expansion<T, 1> y) noexcept {
    return core_add(x, y.limb[0]);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> core_add(Expansion<T, 1> x, Expansion<T, 2> y) noexcept {
    return core_add(y, x.limb[0]);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> core_sub(Expansion<T, 2> x, Expansion<T, 1> y) noexcept {
    return core_sub(x, y.limb[0]);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> core_sub(Expansion<T, 1> x, Expansion<T, 2> y) noexcept {
    return core_sub(x.limb[0], y);
}
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> core_mul(std::type_identity_t<T> a, Expansion<T, 2> y) noexcept {
    return core_mul(y, a);
}
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> core_mul(Expansion<T, 2> x, Expansion<T, 1> y) noexcept {
    return core_mul(x, y.limb[0]);
}
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> core_mul(Expansion<T, 1> x, Expansion<T, 2> y) noexcept {
    return core_mul(y, x.limb[0]);
}
// One limb: the operations themselves.
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> core_add(Expansion<T, 1> x, Expansion<T, 1> y) noexcept {
    return add(x, y);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> core_add(Expansion<T, 1> x, std::type_identity_t<T> a) noexcept {
    return add(x, a);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> core_add(std::type_identity_t<T> a, Expansion<T, 1> y) noexcept {
    return add(a, y);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> core_sub(Expansion<T, 1> x, Expansion<T, 1> y) noexcept {
    return sub(x, y);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> core_sub(Expansion<T, 1> x, std::type_identity_t<T> a) noexcept {
    return sub(x, a);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> core_sub(std::type_identity_t<T> a, Expansion<T, 1> y) noexcept {
    return sub(a, y);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> core_mul(Expansion<T, 1> x, Expansion<T, 1> y) noexcept {
    return mul(x, y);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> core_mul(Expansion<T, 1> x, std::type_identity_t<T> a) noexcept {
    return mul(x, a);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> core_mul(std::type_identity_t<T> a, Expansion<T, 1> y) noexcept {
    return mul(a, y);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> core_add_fast(Expansion<T, 1> x, Expansion<T, 1> y) noexcept {
    return add(x, y);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> core_ldexp(Expansion<T, 1> x, int n) noexcept {
    return ldexp(x, n);
}

}  // namespace detail

/// One limb: the value is limb[0], and every operation is the IEEE 754 operation of T, which is
/// already IEEE-like: an infinity or a NaN comes out as T gives it.
///
/// It is meant to cost exactly what T costs (docs/developer/design/phase0/library.md, "One limb"):
/// operations are force-inlined and compute one operation of T each. Under Clang's default
/// contraction (-ffp-contract=on) a * b + c on T is one fused operation and on Expansion<T, 1> two
/// rounded ones, unless KAIRN_K1_CONTRACT is defined (config.hpp). A loop over Expansion<T, 1> is
/// not auto-vectorized by MSVC where the same loop over T is.
///
/// +, - and * have kernels, add_1_1 and mul_1_1, whose claim is one rounding to nearest:
/// |z - v| <= u/(1 + u) |v|, plus eta/2 for a product (v the exact result, u = 2^-p, eta the
/// smallest subnormal of T); as for every operation, they need kairn::unverified only while
/// gen/claims.json does not mark their kernel proved. Negation, abs, comparisons and the
/// conversions to T have no kernel: they are exact IEEE 754 operations and never need it.
///
/// One-limb values are not guarded: they behave like T, contraction included, so p * q + r may
/// be computed with one rounding where the compiler contracts, as for T (decision D6). They are
/// guarded where they enter a two-limb operation or a ball, by the kernel that receives them.
template <class T>
struct Expansion<T, 1> {
    static_assert(detail::limb<T>, "Expansion<T, k>: the limb type T is float or double");

    /// The limb, which is the value.
    T limb[1] = {};

    /// Zero.
    constexpr Expansion() noexcept = default;
    /// x, exactly. Implicit, as T converts to T.
    constexpr Expansion(T x) noexcept : limb{x} {}
    /// x rounded to nearest: its leading limb (kernel to_nearest_2), which for (+-inf, 0) is the
    /// infinity and for (NaN, NaN) a NaN. Explicit, because it loses the second limb.
    explicit constexpr Expansion(const Expansion<T, 2>& x) noexcept
        requires detail::proof_checked<gen::bounds::to_nearest_2<T>>
        : limb{detail::to_nearest(x)} {}
    /// The same with a marked operand: see kairn::Unverified.
    explicit constexpr Expansion(const Unverified<Expansion<T, 2>>& x) noexcept : limb{detail::to_nearest(x.value)} {}
    /// limbs[0]: every value of T is a one-limb number.
    static constexpr Expansion from_limbs(const T* limbs) noexcept { return Expansion(limbs[0]); }
    /// limbs[0].
    static constexpr Expansion from_limbs_unchecked(const T* limbs) noexcept { return Expansion(limbs[0]); }

    /// x + y, rounded to nearest (kernel add_1_1).
    friend KAIRN_FORCEINLINE constexpr Expansion operator+(const Expansion& x, const Expansion& y) noexcept
        requires detail::proof_checked<gen::bounds::add_1_1<T>>
    {
        return detail::add(x, y);
    }
    /// x - y, rounded to nearest (kernel add_1_1 on x and -y).
    friend KAIRN_FORCEINLINE constexpr Expansion operator-(const Expansion& x, const Expansion& y) noexcept
        requires detail::proof_checked<gen::bounds::add_1_1<T>>
    {
        return detail::sub(x, y);
    }
    /// x * y, rounded to nearest (kernel mul_1_1).
    friend KAIRN_FORCEINLINE constexpr Expansion operator*(const Expansion& x, const Expansion& y) noexcept
        requires detail::proof_checked<gen::bounds::mul_1_1<T>>
    {
        return detail::mul(x, y);
    }
    /// x = x + y (kernel add_1_1).
    friend KAIRN_FORCEINLINE constexpr Expansion& operator+=(Expansion& x, const Expansion& y) noexcept
        requires detail::proof_checked<gen::bounds::add_1_1<T>>
    {
        return x = detail::add(x, y);
    }
    /// x = x - y (kernel add_1_1).
    friend KAIRN_FORCEINLINE constexpr Expansion& operator-=(Expansion& x, const Expansion& y) noexcept
        requires detail::proof_checked<gen::bounds::add_1_1<T>>
    {
        return x = detail::sub(x, y);
    }
    /// x = x * y (kernel mul_1_1).
    friend KAIRN_FORCEINLINE constexpr Expansion& operator*=(Expansion& x, const Expansion& y) noexcept
        requires detail::proof_checked<gen::bounds::mul_1_1<T>>
    {
        return x = detail::mul(x, y);
    }
    /// -x, exactly.
    friend KAIRN_FORCEINLINE constexpr Expansion operator-(const Expansion& x) noexcept { return detail::neg(x); }
    /// Whether x < y, exactly: the comparison of T. False if either is NaN.
    friend KAIRN_FORCEINLINE constexpr bool operator<(const Expansion& x, const Expansion& y) noexcept {
        return detail::lt(x, y);
    }
    /// Whether x > y, exactly. False if either is NaN.
    friend KAIRN_FORCEINLINE constexpr bool operator>(const Expansion& x, const Expansion& y) noexcept {
        return detail::lt(y, x);
    }
    /// Whether x <= y, exactly. False if either is NaN.
    friend KAIRN_FORCEINLINE constexpr bool operator<=(const Expansion& x, const Expansion& y) noexcept {
        return detail::le(x, y);
    }
    /// Whether x >= y, exactly. False if either is NaN.
    friend KAIRN_FORCEINLINE constexpr bool operator>=(const Expansion& x, const Expansion& y) noexcept {
        return detail::le(y, x);
    }
    /// Whether x == y, exactly (+0 equals -0). False if either is NaN.
    friend KAIRN_FORCEINLINE constexpr bool operator==(const Expansion& x, const Expansion& y) noexcept {
        return detail::eq(x, y);
    }
    /// Whether x != y, exactly. True if either is NaN.
    friend KAIRN_FORCEINLINE constexpr bool operator!=(const Expansion& x, const Expansion& y) noexcept {
        return !detail::eq(x, y);
    }
};

/// Two limbs (a double-word number): the value is limb[0] + limb[1], exactly, and limb[1] is at
/// most half a unit in the last place of limb[0], so that limb[0] is the value rounded to nearest.
/// With double limbs that is 106 bits of precision for values above about 2^-969, fewer below
/// (docs/developer/design/phase0/numbers.md, "Precision depends on magnitude").
///
/// Values: a number is canonical (see Expansion) when it is finite and normalized, or
/// (+inf, 0), (-inf, 0), or (NaN, NaN). Constructors and operators return canonical numbers;
/// operators require canonical operands (checked when KAIRN_CHECKS is 1).
///
/// Arithmetic (+, -, *, add_fast, ldexp, half) is IEEE-like (decision D5): each operator calls a
/// full kernel, the finite core of the operation followed by a fix-up. Proved in Flocq's model of
/// IEEE 754, for canonical operands (statements F1 to F5 of docs/developer/design/milestone1.md,
/// "IEEE-like results"), with w the result:
/// - w is canonical;
/// - if w0 is finite, every operand is finite and w satisfies the claim of the core, as quoted
///   on each operator: normalized, and within its bound;
/// - if every operand is finite and the condition quoted on the operator holds, w0 is finite;
/// - if every operand is finite and w0 is not (an overflow), w is (+-inf, 0) with the sign of the
///   exact result;
/// - if an operand is not finite, w is the canonical form of T's operation on the leading limbs:
///   inf + 1 = inf, inf - inf = NaN, 0 * inf = NaN; which NaN is not specified.
/// u = 2^-p is the unit roundoff of T (2^-53 for double), eta its smallest subnormal number
/// (2^-1074), and 2^e_max its overflow threshold (2^1024 for double, 2^128 for float).
/// kairn::finite:: has the same operations without the fix-up.
///
/// Comparisons, negation, abs and the conversions to T call kernels that need no fix-up; what
/// they return for infinite and NaN operands is said on each.
///
/// A value of type T that the program passes in (to a constructor, to from_limbs, or as the limb
/// operand of x + a, x - a, a - x) passes through a guard, one addition of +0, inside the kernel
/// that receives it, before anything adds it (rule R3): otherwise a product the program computed,
/// as in x + a * b, could be fused into the kernel's error-free sums under contraction across
/// statements (GCC's default for C++, -ffp-contract=fast, MSVC's /fp:contract). The guard turns a
/// -0 into +0, whose sign Kairn leaves unspecified anyway. Limbs written directly into `limb` are
/// not guarded (see there).
template <class T>
struct Expansion<T, 2> {
    static_assert(detail::limb<T>, "Expansion<T, k>: the limb type T is float or double");

    /// The limbs, most significant first. Written directly, a limb must not be a product the
    /// compiler can see being computed (in the same function, even through a variable): under
    /// contraction it could be fused into the next operation's sums. from_limbs and the
    /// constructors guard what they are given; use them to build a number from computed values.
    /// The pair written must be canonical.
    T limb[2] = {};

    /// Zero.
    constexpr Expansion() noexcept = default;
    /// a, exactly (kernel make_2): (a, 0), with a -0 made +0; for an infinite a, (a, 0); for a
    /// NaN, (NaN, NaN).
    constexpr Expansion(T a) noexcept
        requires detail::proof_checked<gen::bounds::make_2<T>>
        : Expansion(detail::make<T>(a)) {}
    /// The same with a marked operand: see kairn::Unverified.
    explicit constexpr Expansion(Unverified<T> a) noexcept : Expansion(detail::make<T>(a.value)) {}
    /// a, exactly: the constructor from the limb of the one-limb number (kernel make_2).
    constexpr Expansion(const Expansion<T, 1>& a) noexcept
        requires detail::proof_checked<gen::bounds::make_2<T>>
        : Expansion(detail::make<T>(a.limb[0])) {}
    /// The same with a marked operand.
    explicit constexpr Expansion(const Unverified<Expansion<T, 1>>& a) noexcept
        : Expansion(detail::make<T>(a.value.limb[0])) {}
    /// The number with the limbs limbs[0], limbs[1] (kernel make_2_limbs), each guarded. They must
    /// form a canonical pair: finite and normalized (limbs[0] + limbs[1] rounded to nearest is
    /// limbs[0]), or an infinity and a zero, or two NaN; the result has the same limbs (a zero may
    /// change sign). Checked when KAIRN_CHECKS is 1, after the environment as for an operation
    /// (config.hpp); then a pair that is not canonical fails a constant expression, or prints a
    /// message and calls std::abort(). Not checked otherwise.
    static constexpr Expansion from_limbs(const T* limbs) noexcept
        requires detail::proof_checked<gen::bounds::make_2_limbs<T>>
    {
#if KAIRN_CHECKS
        if (detail::check_environment() && !detail::canonical(Expansion(limbs[0], limbs[1])))
            detail::fail("from_limbs", "the limbs are not a canonical pair (finite with x0 + x1 == x0, an "
                                       "infinity and a zero, or two NaN)");
#endif
        return detail::make_limbs<T>(limbs[0], limbs[1]);
    }
    /// The number with these two limbs (kernel make_2_limbs), each guarded, without the check. If
    /// they do not form a canonical pair, operations on it have no undefined behavior but give
    /// results with no guarantee.
    static constexpr Expansion from_limbs_unchecked(const T* limbs) noexcept
        requires detail::proof_checked<gen::bounds::make_2_limbs<T>>
    {
        return detail::make_limbs<T>(limbs[0], limbs[1]);
    }

private:
    // The two limbs as they are, for the check of from_limbs.
    constexpr Expansion(T h, T l) noexcept : limb{h, l} {}
};

/// The marked form of an Expansion operand: see kairn::Unverified.
template <class T, int K>
struct Unverified<Expansion<T, K>> {
    Expansion<T, K> value;  ///< The operand.
};

/// Marks x as an operand of an operation whose proof is not checked yet; see kairn::Unverified.
template <class T, int K>
KAIRN_FORCEINLINE constexpr Unverified<Expansion<T, K>> unverified(const Expansion<T, K>& x) noexcept {
    return {x};
}

// The operators of two limbs. They are function templates, not hidden friends, so that no operand
// converts: a T or a one-limb operand matches only the form written for it, and each form is
// gated on the kernel it calls, never compiled through another kernel.

/// x + y (kernel add_2_2_full: the core add_2_2, JMP17 Algorithm 6, and the fix-up).
///
/// Core: z normalized, |z - (x + y)| <= 3u^2/(1 - 4u) |x + y|, with no underflow term. Finite
/// when |x| and |y| are at most 2^(e_max - 2) (2^1022 for double, 2^126 for float).
template <class T>
    requires detail::proof_checked<gen::bounds::add_2_2_full<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> operator+(const Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    return detail::add(x, y);
}
/// x + a (kernel add_2_1_full: the core add_2_1, JMP17 Algorithm 4, and the fix-up).
///
/// Core: z normalized, |z - (x + a)| <= 2u^2 |x + a|. Finite when |x| and |a| are at most
/// 2^(e_max - 2).
template <class T>
    requires detail::proof_checked<gen::bounds::add_2_1_full<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> operator+(const Expansion<T, 2>& x, std::type_identity_t<T> a) noexcept {
    return detail::add(x, a);
}
/// a + x: the same operation and claim as x + a (kernel add_2_1_full).
template <class T>
    requires detail::proof_checked<gen::bounds::add_2_1_full<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> operator+(std::type_identity_t<T> a, const Expansion<T, 2>& x) noexcept {
    return detail::add(a, x);
}
/// x + y for a one-limb y: x + a with a its limb (kernel add_2_1_full).
template <class T>
    requires detail::proof_checked<gen::bounds::add_2_1_full<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> operator+(const Expansion<T, 2>& x, const Expansion<T, 1>& y) noexcept {
    return detail::add(x, y);
}
/// x + y for a one-limb x: a + y with a its limb (kernel add_2_1_full).
template <class T>
    requires detail::proof_checked<gen::bounds::add_2_1_full<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> operator+(const Expansion<T, 1>& x, const Expansion<T, 2>& y) noexcept {
    return detail::add(x, y);
}
/// x - y (kernel sub_2_2_full: the core sub_2_2, which is add_2_2 on x and -y, and the fix-up).
/// Core: as x + y, for x - y. Finite when |x| and |y| are at most 2^(e_max - 2).
template <class T>
    requires detail::proof_checked<gen::bounds::sub_2_2_full<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> operator-(const Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    return detail::sub(x, y);
}
/// x - a (kernel sub_2_1_full: the core sub_2_1, add_2_1 on x and -a, and the fix-up). Core: as
/// x + a, for x - a. Finite when |x| and |a| are at most 2^(e_max - 2).
template <class T>
    requires detail::proof_checked<gen::bounds::sub_2_1_full<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> operator-(const Expansion<T, 2>& x, std::type_identity_t<T> a) noexcept {
    return detail::sub(x, a);
}
/// a - x (kernel sub_1_2_full: the core sub_1_2, add_2_1 on -x and a, and the fix-up). Core: as
/// x + a, for a - x. Finite when |a| and |x| are at most 2^(e_max - 2).
template <class T>
    requires detail::proof_checked<gen::bounds::sub_1_2_full<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> operator-(std::type_identity_t<T> a, const Expansion<T, 2>& x) noexcept {
    return detail::sub(a, x);
}
/// x - y for a one-limb y: x - a with a its limb (kernel sub_2_1_full).
template <class T>
    requires detail::proof_checked<gen::bounds::sub_2_1_full<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> operator-(const Expansion<T, 2>& x, const Expansion<T, 1>& y) noexcept {
    return detail::sub(x, y);
}
/// x - y for a one-limb x: a - y with a its limb (kernel sub_1_2_full).
template <class T>
    requires detail::proof_checked<gen::bounds::sub_1_2_full<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> operator-(const Expansion<T, 1>& x, const Expansion<T, 2>& y) noexcept {
    return detail::sub(x, y);
}
/// x * y (kernel mul_2_2_full: the core mul_2_2, JMP17 Algorithm 12, and the fix-up). Not usable
/// in constant evaluation yet.
///
/// Core: z normalized, |z - xy| <= 4u^2 |xy| + (3/2) eta. Finite when |xy| is at most
/// 2^(e_max - 1) (2^1023 for double, 2^127 for float).
template <class T>
    requires detail::proof_checked<gen::bounds::mul_2_2_full<T>>
KAIRN_FORCEINLINE Expansion<T, 2> operator*(const Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    return detail::mul(x, y);
}
/// x * a (kernel mul_2_1_full: the core mul_2_1, JMP17 Algorithm 9, and the fix-up). Not usable in
/// constant evaluation yet.
///
/// Core: z normalized, |z - xa| <= 2u^2 |xa| + eta. Finite when |xa| is at most 2^(e_max - 1).
template <class T>
    requires detail::proof_checked<gen::bounds::mul_2_1_full<T>>
KAIRN_FORCEINLINE Expansion<T, 2> operator*(const Expansion<T, 2>& x, std::type_identity_t<T> a) noexcept {
    return detail::mul(x, a);
}
/// a * x: the same operation and claim as x * a (kernel mul_2_1_full).
template <class T>
    requires detail::proof_checked<gen::bounds::mul_2_1_full<T>>
KAIRN_FORCEINLINE Expansion<T, 2> operator*(std::type_identity_t<T> a, const Expansion<T, 2>& x) noexcept {
    return detail::mul(a, x);
}
/// x * y for a one-limb y: x * a with a its limb (kernel mul_2_1_full).
template <class T>
    requires detail::proof_checked<gen::bounds::mul_2_1_full<T>>
KAIRN_FORCEINLINE Expansion<T, 2> operator*(const Expansion<T, 2>& x, const Expansion<T, 1>& y) noexcept {
    return detail::mul(x, y);
}
/// x * y for a one-limb x: a * y with a its limb (kernel mul_2_1_full).
template <class T>
    requires detail::proof_checked<gen::bounds::mul_2_1_full<T>>
KAIRN_FORCEINLINE Expansion<T, 2> operator*(const Expansion<T, 1>& x, const Expansion<T, 2>& y) noexcept {
    return detail::mul(x, y);
}
/// x = x + y (kernel add_2_2_full).
template <class T>
    requires detail::proof_checked<gen::bounds::add_2_2_full<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2>& operator+=(Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    return x = detail::add(x, y);
}
/// x = x + a (kernel add_2_1_full).
template <class T>
    requires detail::proof_checked<gen::bounds::add_2_1_full<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2>& operator+=(Expansion<T, 2>& x, std::type_identity_t<T> a) noexcept {
    return x = detail::add(x, a);
}
/// x = x + y for a one-limb y (kernel add_2_1_full).
template <class T>
    requires detail::proof_checked<gen::bounds::add_2_1_full<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2>& operator+=(Expansion<T, 2>& x, const Expansion<T, 1>& y) noexcept {
    return x = detail::add(x, y);
}
/// x = x - y (kernel sub_2_2_full).
template <class T>
    requires detail::proof_checked<gen::bounds::sub_2_2_full<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2>& operator-=(Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    return x = detail::sub(x, y);
}
/// x = x - a (kernel sub_2_1_full).
template <class T>
    requires detail::proof_checked<gen::bounds::sub_2_1_full<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2>& operator-=(Expansion<T, 2>& x, std::type_identity_t<T> a) noexcept {
    return x = detail::sub(x, a);
}
/// x = x - y for a one-limb y (kernel sub_2_1_full).
template <class T>
    requires detail::proof_checked<gen::bounds::sub_2_1_full<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2>& operator-=(Expansion<T, 2>& x, const Expansion<T, 1>& y) noexcept {
    return x = detail::sub(x, y);
}
/// x = x * y (kernel mul_2_2_full).
template <class T>
    requires detail::proof_checked<gen::bounds::mul_2_2_full<T>>
KAIRN_FORCEINLINE Expansion<T, 2>& operator*=(Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    return x = detail::mul(x, y);
}
/// x = x * a (kernel mul_2_1_full).
template <class T>
    requires detail::proof_checked<gen::bounds::mul_2_1_full<T>>
KAIRN_FORCEINLINE Expansion<T, 2>& operator*=(Expansion<T, 2>& x, std::type_identity_t<T> a) noexcept {
    return x = detail::mul(x, a);
}
/// x = x * y for a one-limb y (kernel mul_2_1_full).
template <class T>
    requires detail::proof_checked<gen::bounds::mul_2_1_full<T>>
KAIRN_FORCEINLINE Expansion<T, 2>& operator*=(Expansion<T, 2>& x, const Expansion<T, 1>& y) noexcept {
    return x = detail::mul(x, y);
}
/// -x, limb by limb (kernel neg_2): exactly -x, normalized; for (+-inf, 0) the opposite
/// infinity, and a NaN for (NaN, NaN). No fix-up is needed.
template <class T>
    requires detail::proof_checked<gen::bounds::neg_2<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> operator-(const Expansion<T, 2>& x) noexcept {
    return detail::neg(x);
}

// Comparisons: the kernels lt, le and eq compare limbs in order. Proved for canonical operands,
// in the IEEE model: the truth about the two values as extended real numbers (-inf < every finite
// value < +inf), and false when an operand is a NaN, as for T; != is the negation of ==, so true
// with a NaN.

/// Whether x < y (kernel lt_2_2).
template <class T>
    requires detail::proof_checked<gen::bounds::lt_2_2<T>>
KAIRN_FORCEINLINE constexpr bool operator<(const Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    return detail::lt(x, y);
}
/// Whether x > y (kernel lt_2_2 on y, x).
template <class T>
    requires detail::proof_checked<gen::bounds::lt_2_2<T>>
KAIRN_FORCEINLINE constexpr bool operator>(const Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    return detail::lt(y, x);
}
/// Whether x <= y (kernel le_2_2).
template <class T>
    requires detail::proof_checked<gen::bounds::le_2_2<T>>
KAIRN_FORCEINLINE constexpr bool operator<=(const Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    return detail::le(x, y);
}
/// Whether x >= y (kernel le_2_2 on y, x).
template <class T>
    requires detail::proof_checked<gen::bounds::le_2_2<T>>
KAIRN_FORCEINLINE constexpr bool operator>=(const Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    return detail::le(y, x);
}
/// Whether x == y (kernel eq_2_2).
template <class T>
    requires detail::proof_checked<gen::bounds::eq_2_2<T>>
KAIRN_FORCEINLINE constexpr bool operator==(const Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    return detail::eq(x, y);
}
/// Whether x != y: not x == y (kernel eq_2_2).
template <class T>
    requires detail::proof_checked<gen::bounds::eq_2_2<T>>
KAIRN_FORCEINLINE constexpr bool operator!=(const Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    return !detail::eq(x, y);
}
/// Whether x < a (kernel lt_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::lt_2_1<T>>
KAIRN_FORCEINLINE constexpr bool operator<(const Expansion<T, 2>& x, std::type_identity_t<T> a) noexcept {
    return detail::lt(x, a);
}
/// Whether x > a: a < x (kernel lt_1_2).
template <class T>
    requires detail::proof_checked<gen::bounds::lt_1_2<T>>
KAIRN_FORCEINLINE constexpr bool operator>(const Expansion<T, 2>& x, std::type_identity_t<T> a) noexcept {
    return detail::lt(a, x);
}
/// Whether x <= a (kernel le_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::le_2_1<T>>
KAIRN_FORCEINLINE constexpr bool operator<=(const Expansion<T, 2>& x, std::type_identity_t<T> a) noexcept {
    return detail::le(x, a);
}
/// Whether x >= a: a <= x (kernel le_1_2).
template <class T>
    requires detail::proof_checked<gen::bounds::le_1_2<T>>
KAIRN_FORCEINLINE constexpr bool operator>=(const Expansion<T, 2>& x, std::type_identity_t<T> a) noexcept {
    return detail::le(a, x);
}
/// Whether x == a (kernel eq_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::eq_2_1<T>>
KAIRN_FORCEINLINE constexpr bool operator==(const Expansion<T, 2>& x, std::type_identity_t<T> a) noexcept {
    return detail::eq(x, a);
}
/// Whether x != a (kernel eq_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::eq_2_1<T>>
KAIRN_FORCEINLINE constexpr bool operator!=(const Expansion<T, 2>& x, std::type_identity_t<T> a) noexcept {
    return !detail::eq(x, a);
}
/// Whether a < x (kernel lt_1_2).
template <class T>
    requires detail::proof_checked<gen::bounds::lt_1_2<T>>
KAIRN_FORCEINLINE constexpr bool operator<(std::type_identity_t<T> a, const Expansion<T, 2>& x) noexcept {
    return detail::lt(a, x);
}
/// Whether a > x: x < a (kernel lt_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::lt_2_1<T>>
KAIRN_FORCEINLINE constexpr bool operator>(std::type_identity_t<T> a, const Expansion<T, 2>& x) noexcept {
    return detail::lt(x, a);
}
/// Whether a <= x (kernel le_1_2).
template <class T>
    requires detail::proof_checked<gen::bounds::le_1_2<T>>
KAIRN_FORCEINLINE constexpr bool operator<=(std::type_identity_t<T> a, const Expansion<T, 2>& x) noexcept {
    return detail::le(a, x);
}
/// Whether a >= x: x <= a (kernel le_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::le_2_1<T>>
KAIRN_FORCEINLINE constexpr bool operator>=(std::type_identity_t<T> a, const Expansion<T, 2>& x) noexcept {
    return detail::le(x, a);
}
/// Whether a == x (kernel eq_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::eq_2_1<T>>
KAIRN_FORCEINLINE constexpr bool operator==(std::type_identity_t<T> a, const Expansion<T, 2>& x) noexcept {
    return detail::eq(x, a);
}
/// Whether a != x (kernel eq_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::eq_2_1<T>>
KAIRN_FORCEINLINE constexpr bool operator!=(std::type_identity_t<T> a, const Expansion<T, 2>& x) noexcept {
    return !detail::eq(x, a);
}
/// Whether x < y for a one-limb y: x < a with a its limb (kernel lt_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::lt_2_1<T>>
KAIRN_FORCEINLINE constexpr bool operator<(const Expansion<T, 2>& x, const Expansion<T, 1>& y) noexcept {
    return detail::lt(x, y);
}
/// Whether x > y for a one-limb y (kernel lt_1_2).
template <class T>
    requires detail::proof_checked<gen::bounds::lt_1_2<T>>
KAIRN_FORCEINLINE constexpr bool operator>(const Expansion<T, 2>& x, const Expansion<T, 1>& y) noexcept {
    return detail::lt(y, x);
}
/// Whether x <= y for a one-limb y (kernel le_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::le_2_1<T>>
KAIRN_FORCEINLINE constexpr bool operator<=(const Expansion<T, 2>& x, const Expansion<T, 1>& y) noexcept {
    return detail::le(x, y);
}
/// Whether x >= y for a one-limb y (kernel le_1_2).
template <class T>
    requires detail::proof_checked<gen::bounds::le_1_2<T>>
KAIRN_FORCEINLINE constexpr bool operator>=(const Expansion<T, 2>& x, const Expansion<T, 1>& y) noexcept {
    return detail::le(y, x);
}
/// Whether x == y for a one-limb y (kernel eq_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::eq_2_1<T>>
KAIRN_FORCEINLINE constexpr bool operator==(const Expansion<T, 2>& x, const Expansion<T, 1>& y) noexcept {
    return detail::eq(x, y);
}
/// Whether x != y for a one-limb y (kernel eq_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::eq_2_1<T>>
KAIRN_FORCEINLINE constexpr bool operator!=(const Expansion<T, 2>& x, const Expansion<T, 1>& y) noexcept {
    return !detail::eq(x, y);
}
/// Whether x < y for a one-limb x: a < y with a its limb (kernel lt_1_2).
template <class T>
    requires detail::proof_checked<gen::bounds::lt_1_2<T>>
KAIRN_FORCEINLINE constexpr bool operator<(const Expansion<T, 1>& x, const Expansion<T, 2>& y) noexcept {
    return detail::lt(x, y);
}
/// Whether x > y for a one-limb x (kernel lt_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::lt_2_1<T>>
KAIRN_FORCEINLINE constexpr bool operator>(const Expansion<T, 1>& x, const Expansion<T, 2>& y) noexcept {
    return detail::lt(y, x);
}
/// Whether x <= y for a one-limb x (kernel le_1_2).
template <class T>
    requires detail::proof_checked<gen::bounds::le_1_2<T>>
KAIRN_FORCEINLINE constexpr bool operator<=(const Expansion<T, 1>& x, const Expansion<T, 2>& y) noexcept {
    return detail::le(x, y);
}
/// Whether x >= y for a one-limb x (kernel le_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::le_2_1<T>>
KAIRN_FORCEINLINE constexpr bool operator>=(const Expansion<T, 1>& x, const Expansion<T, 2>& y) noexcept {
    return detail::le(y, x);
}
/// Whether x == y for a one-limb x (kernel eq_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::eq_2_1<T>>
KAIRN_FORCEINLINE constexpr bool operator==(const Expansion<T, 1>& x, const Expansion<T, 2>& y) noexcept {
    return detail::eq(x, y);
}
/// Whether x != y for a one-limb x (kernel eq_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::eq_2_1<T>>
KAIRN_FORCEINLINE constexpr bool operator!=(const Expansion<T, 1>& x, const Expansion<T, 2>& y) noexcept {
    return !detail::eq(x, y);
}

// The operations with a marked operand. One template per operator covers every combination of a
// marked and an unmarked operand; it exists only where the operation does (the return type names
// it), and it is the only exact match for a marked operand, so it never competes with the
// operators above.
namespace detail {
template <class X, class Y>
concept marked_expansion_pair = (marked<X> || marked<Y>) && !ball<X> && !ball<Y>;
template <class X, class Y>
concept marked_expansion_rhs = marked<Y> && !marked<X> && !ball<X> && !ball<Y>;
}  // namespace detail

/// x + y with a marked operand: the same operation as without the marker, for any combination of
/// Expansion and T operands.
template <class X, class Y>
    requires detail::marked_expansion_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto operator+(const X& x, const Y& y) noexcept
    -> decltype(detail::add(detail::unmark(x), detail::unmark(y))) {
    return detail::add(detail::unmark(x), detail::unmark(y));
}
/// x - y with a marked operand.
template <class X, class Y>
    requires detail::marked_expansion_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto operator-(const X& x, const Y& y) noexcept
    -> decltype(detail::sub(detail::unmark(x), detail::unmark(y))) {
    return detail::sub(detail::unmark(x), detail::unmark(y));
}
/// x * y with a marked operand.
template <class X, class Y>
    requires detail::marked_expansion_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto operator*(const X& x, const Y& y) noexcept
    -> decltype(detail::mul(detail::unmark(x), detail::unmark(y))) {
    return detail::mul(detail::unmark(x), detail::unmark(y));
}
/// -x with a marked operand.
template <class X>
    requires detail::marked<X> && (!detail::ball<X>)
KAIRN_FORCEINLINE constexpr auto operator-(const X& x) noexcept -> decltype(detail::neg(detail::unmark(x))) {
    return detail::neg(detail::unmark(x));
}
/// x = x + y with a marked right operand. (A marked left operand would be a copy: not allowed.)
template <class X, class Y>
    requires detail::marked_expansion_rhs<X, Y>
KAIRN_FORCEINLINE constexpr auto operator+=(X& x, const Y& y) noexcept
    -> decltype(x = detail::add(x, detail::unmark(y))) {
    return x = detail::add(x, detail::unmark(y));
}
/// x = x - y with a marked right operand.
template <class X, class Y>
    requires detail::marked_expansion_rhs<X, Y>
KAIRN_FORCEINLINE constexpr auto operator-=(X& x, const Y& y) noexcept
    -> decltype(x = detail::sub(x, detail::unmark(y))) {
    return x = detail::sub(x, detail::unmark(y));
}
/// x = x * y with a marked right operand.
template <class X, class Y>
    requires detail::marked_expansion_rhs<X, Y>
KAIRN_FORCEINLINE constexpr auto operator*=(X& x, const Y& y) noexcept
    -> decltype(x = detail::mul(x, detail::unmark(y))) {
    return x = detail::mul(x, detail::unmark(y));
}
/// Whether x < y, with a marked operand.
template <class X, class Y>
    requires detail::marked_expansion_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto operator<(const X& x, const Y& y) noexcept
    -> decltype(detail::lt(detail::unmark(x), detail::unmark(y))) {
    return detail::lt(detail::unmark(x), detail::unmark(y));
}
/// Whether x > y, with a marked operand.
template <class X, class Y>
    requires detail::marked_expansion_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto operator>(const X& x, const Y& y) noexcept
    -> decltype(detail::lt(detail::unmark(y), detail::unmark(x))) {
    return detail::lt(detail::unmark(y), detail::unmark(x));
}
/// Whether x <= y, with a marked operand.
template <class X, class Y>
    requires detail::marked_expansion_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto operator<=(const X& x, const Y& y) noexcept
    -> decltype(detail::le(detail::unmark(x), detail::unmark(y))) {
    return detail::le(detail::unmark(x), detail::unmark(y));
}
/// Whether x >= y, with a marked operand.
template <class X, class Y>
    requires detail::marked_expansion_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto operator>=(const X& x, const Y& y) noexcept
    -> decltype(detail::le(detail::unmark(y), detail::unmark(x))) {
    return detail::le(detail::unmark(y), detail::unmark(x));
}
/// Whether x == y, with a marked operand.
template <class X, class Y>
    requires detail::marked_expansion_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto operator==(const X& x, const Y& y) noexcept
    -> decltype(detail::eq(detail::unmark(x), detail::unmark(y))) {
    return detail::eq(detail::unmark(x), detail::unmark(y));
}
/// Whether x != y, with a marked operand.
template <class X, class Y>
    requires detail::marked_expansion_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto operator!=(const X& x, const Y& y) noexcept
    -> decltype(!detail::eq(detail::unmark(x), detail::unmark(y))) {
    return !detail::eq(detail::unmark(x), detail::unmark(y));
}

// The named operations: a form for each number of limbs, constrained like the operators, and a
// form that takes a marked operand.

/// |x|, exactly. One limb: the IEEE 754 absolute value; no marker needed.
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> abs(const Expansion<T, 1>& x) noexcept {
    return detail::abs(x);
}
/// |x| (kernel abs_2): exactly |x|, normalized; +inf for (+-inf, 0), and a NaN for (NaN, NaN).
/// No fix-up is needed.
template <class T>
    requires detail::proof_checked<gen::bounds::abs_2<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> abs(const Expansion<T, 2>& x) noexcept {
    return detail::abs(x);
}
/// |x| with a marked operand.
template <class X>
    requires detail::marked<X>
KAIRN_FORCEINLINE constexpr auto abs(const X& x) noexcept -> decltype(detail::abs(detail::unmark(x))) {
    return detail::abs(detail::unmark(x));
}

/// The fast addition, for one limb: x + y (kernel add_1_1).
template <class T>
    requires detail::proof_checked<gen::bounds::add_1_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> add_fast(const Expansion<T, 1>& x, const Expansion<T, 1>& y) noexcept {
    return detail::add_fast(x, y);
}
/// The fast addition (kernel add_fast_2_2_full: the core add_fast_2_2, JMP17 Algorithm 5, and the
/// fix-up): about half the operations of x + y, with a weaker bound, relative to the operands
/// rather than to the result. Core: z normalized, |z - (x + y)| <= 3u^2 (|x| + |y|). It has no
/// relative bound when x and y nearly cancel, which is why x + y does not use it. Finite when |x|
/// and |y| are at most 2^(e_max - 2).
template <class T>
    requires detail::proof_checked<gen::bounds::add_fast_2_2_full<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> add_fast(const Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    return detail::add_fast(x, y);
}
/// The fast addition with a marked operand; both operands have the same number of limbs.
template <class X, class Y>
    requires detail::marked_expansion_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto add_fast(const X& x, const Y& y) noexcept
    -> decltype(detail::add_fast(detail::unmark(x), detail::unmark(y))) {
    return detail::add_fast(detail::unmark(x), detail::unmark(y));
}

/// x times 2^n, rounded once, for every n: RN(x 2^n), the result of std::ldexp. One limb (kernel
/// mul_1_1, with b = 2^n): one product when 2^n is a number of T. Otherwise two or three products
/// by powers of two of T, of which only one rounds: scaling up, each is exact until one overflows;
/// scaling down, the first is exact, or makes a value that the second rounds to zero either way.
/// That this composition returns RN(x 2^n) is argued and tested through the oracle, not
/// machine-checked.
template <class T>
    requires detail::proof_checked<gen::bounds::mul_1_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> ldexp(const Expansion<T, 1>& x, int n) noexcept {
    return detail::ldexp(x, n);
}
/// x times 2^n, for every n (kernel mul_pow2_2_full: the core mul_pow2_2 and the fix-up, with
/// c = 2^n). Not usable in constant evaluation yet.
///
/// Core: z normalized, |z - 2^n x| <= eta (and, proved as a hand-written statement, exactly 2^n x
/// when each limb's product is zero or at least 2^(p-1) eta in magnitude). Finite when |2^n x| is
/// at most 2^(e_max - 1). When 2^n is not a number of T (n above 1023 or below -1074 for double),
/// the kernel is called two or three times (detail::ldexp_steps). The result is then canonical, and
/// normalized when finite, by the proved statements of each call. Argued in the design and tested
/// through the oracle, but not machine-checked: up, every step is exact until one overflows, so
/// the result is 2^n x exactly or (+-inf, 0); down, |z - 2^n x| <= eta still holds.
template <class T>
    requires detail::proof_checked<gen::bounds::mul_pow2_2_full<T>>
KAIRN_FORCEINLINE Expansion<T, 2> ldexp(const Expansion<T, 2>& x, int n) noexcept {
    return detail::ldexp(x, n);
}
/// x times 2^n with a marked operand.
template <class X>
    requires detail::marked<X>
KAIRN_FORCEINLINE constexpr auto ldexp(const X& x, int n) noexcept -> decltype(detail::ldexp(detail::unmark(x), n)) {
    return detail::ldexp(detail::unmark(x), n);
}
/// x / 2, rounded once (kernel mul_1_1, with b = 1/2).
template <class T>
    requires detail::proof_checked<gen::bounds::mul_1_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> half(const Expansion<T, 1>& x) noexcept {
    return detail::half(x);
}
/// x / 2 (kernel mul_pow2_2_full, with c = 1/2): as ldexp(x, -1). Not usable in constant
/// evaluation yet.
template <class T>
    requires detail::proof_checked<gen::bounds::mul_pow2_2_full<T>>
KAIRN_FORCEINLINE Expansion<T, 2> half(const Expansion<T, 2>& x) noexcept {
    return detail::half(x);
}
/// x / 2 with a marked operand.
template <class X>
    requires detail::marked<X>
KAIRN_FORCEINLINE constexpr auto half(const X& x) noexcept -> decltype(detail::half(detail::unmark(x))) {
    return detail::half(detail::unmark(x));
}

/// x rounded to nearest, ties to even. One limb: x itself.
template <class T>
KAIRN_FORCEINLINE constexpr T to_nearest(const Expansion<T, 1>& x) noexcept {
    return detail::to_nearest(x);
}
/// x rounded to nearest, ties to even: the leading limb (kernel to_nearest_2). Proved for
/// canonical x: exactly that rounding for a finite x; the infinity for (+-inf, 0); a NaN for
/// (NaN, NaN).
template <class T>
    requires detail::proof_checked<gen::bounds::to_nearest_2<T>>
KAIRN_FORCEINLINE constexpr T to_nearest(const Expansion<T, 2>& x) noexcept {
    return detail::to_nearest(x);
}
/// to_nearest with a marked operand.
template <class X>
    requires detail::marked<X>
KAIRN_FORCEINLINE constexpr auto to_nearest(const X& x) noexcept -> decltype(detail::to_nearest(detail::unmark(x))) {
    return detail::to_nearest(detail::unmark(x));
}
/// The largest T not above x. One limb: x itself.
template <class T>
KAIRN_FORCEINLINE constexpr T to_down(const Expansion<T, 1>& x) noexcept {
    return detail::to_down(x);
}
/// The largest T not above x (kernel to_down_2). Proved for canonical x: exactly that number for a
/// finite x, which is -inf when x is below -Omega (the largest finite T) by less than its gap;
/// the infinity itself for (+-inf, 0); a NaN for (NaN, NaN).
template <class T>
    requires detail::proof_checked<gen::bounds::to_down_2<T>>
KAIRN_FORCEINLINE constexpr T to_down(const Expansion<T, 2>& x) noexcept {
    return detail::to_down(x);
}
/// to_down with a marked operand.
template <class X>
    requires detail::marked<X>
KAIRN_FORCEINLINE constexpr auto to_down(const X& x) noexcept -> decltype(detail::to_down(detail::unmark(x))) {
    return detail::to_down(detail::unmark(x));
}
/// The smallest T not below x. One limb: x itself.
template <class T>
KAIRN_FORCEINLINE constexpr T to_up(const Expansion<T, 1>& x) noexcept {
    return detail::to_up(x);
}
/// The smallest T not below x (kernel to_up_2). Proved for canonical x: exactly that number for a
/// finite x, which is +inf when x is above Omega; the infinity itself for (+-inf, 0); a NaN for
/// (NaN, NaN).
template <class T>
    requires detail::proof_checked<gen::bounds::to_up_2<T>>
KAIRN_FORCEINLINE constexpr T to_up(const Expansion<T, 2>& x) noexcept {
    return detail::to_up(x);
}
/// to_up with a marked operand.
template <class X>
    requires detail::marked<X>
KAIRN_FORCEINLINE constexpr auto to_up(const X& x) noexcept -> decltype(detail::to_up(detail::unmark(x))) {
    return detail::to_up(detail::unmark(x));
}
/// The smallest T not below |x|. One limb: |x| exactly.
template <class T>
KAIRN_FORCEINLINE constexpr T abs_upper(const Expansion<T, 1>& x) noexcept {
    return detail::abs_upper(x);
}
/// The smallest T not below |x| (kernel abs_upper_2). Proved for canonical x: exactly that number
/// for a finite x, which is +inf when |x| is above Omega; +inf for (+-inf, 0); a NaN for
/// (NaN, NaN).
template <class T>
    requires detail::proof_checked<gen::bounds::abs_upper_2<T>>
KAIRN_FORCEINLINE constexpr T abs_upper(const Expansion<T, 2>& x) noexcept {
    return detail::abs_upper(x);
}
/// abs_upper with a marked operand.
template <class X>
    requires detail::marked<X>
KAIRN_FORCEINLINE constexpr auto abs_upper(const X& x) noexcept -> decltype(detail::abs_upper(detail::unmark(x))) {
    return detail::abs_upper(detail::unmark(x));
}

/// -1, 0 or +1: the sign of the value, read from the leading limb, which for a canonical number
/// has the sign of the value and is zero exactly when the value is (a consequence of the
/// invariant, docs/developer/design/phase0/numbers.md; no kernel). 0 for NaN. The sign of a zero
/// is not reported.
template <class T, int K>
KAIRN_FORCEINLINE constexpr int sign(const Expansion<T, K>& x) noexcept {
    return (x.limb[0] > 0) - (0 > x.limb[0]);
}
/// Whether x is finite, from its leading limb alone: a canonical number is finite exactly when its
/// leading limb is.
template <class T, int K>
KAIRN_FORCEINLINE constexpr bool isfinite(const Expansion<T, K>& x) noexcept {
    return detail::finite(x.limb[0]);
}
/// Whether x is normalized: every limb finite and, for two limbs, x0 + x1 rounded to nearest is
/// x0. Exact; computed with one addition, so it assumes the default floating-point environment.
template <class T, int K>
KAIRN_FORCEINLINE constexpr bool is_normalized(const Expansion<T, K>& x) noexcept {
    if constexpr (K == 1) {
        return detail::finite(x.limb[0]);
    } else {
        return detail::finite(x.limb[0]) && detail::finite(x.limb[1]) && x.limb[0] + x.limb[1] == x.limb[0];
    }
}

/// The finite cores (decision D5): the arithmetic of the operators without the fix-up that makes
/// infinities and NaN canonical, for code that knows its values stay finite and wants the last
/// few operations back.
///
/// Contract, for each function, that of its core, proved in Flocq's model of IEEE 754 for
/// normalized operands: either the leading limb of the result is not finite, or the result is
/// normalized and within the bound quoted on the corresponding operator. Which non-finite pattern
/// comes out (it may be (inf, NaN)) is not specified, and such a result is not canonical: test it
/// with isfinite() before passing it to an operator, which requires canonical operands (checked
/// when KAIRN_CHECKS is 1). The functions themselves accept it and return a non-finite leading
/// limb again. For one limb, each function is the operator itself: there is no fix-up to skip.
namespace finite {

/// x + y, the core alone (kernel add_2_2): see operator+ for the bound.
template <class T>
    requires detail::proof_checked<gen::bounds::add_2_2<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> add(const Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    return detail::core_add(x, y);
}
/// x + a, the core alone (kernel add_2_1), which guards a.
template <class T>
    requires detail::proof_checked<gen::bounds::add_2_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> add(const Expansion<T, 2>& x, std::type_identity_t<T> a) noexcept {
    return detail::core_add(x, a);
}
/// a + x, the core alone (kernel add_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::add_2_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> add(std::type_identity_t<T> a, const Expansion<T, 2>& x) noexcept {
    return detail::core_add(x, a);
}
/// x + y for a one-limb y, the core alone (kernel add_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::add_2_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> add(const Expansion<T, 2>& x, const Expansion<T, 1>& y) noexcept {
    return detail::core_add(x, y.limb[0]);
}
/// x + y for a one-limb x, the core alone (kernel add_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::add_2_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> add(const Expansion<T, 1>& x, const Expansion<T, 2>& y) noexcept {
    return detail::core_add(y, x.limb[0]);
}
/// x - y, the core alone (kernel sub_2_2).
template <class T>
    requires detail::proof_checked<gen::bounds::sub_2_2<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> sub(const Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    return detail::core_sub(x, y);
}
/// x - a, the core alone (kernel sub_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::sub_2_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> sub(const Expansion<T, 2>& x, std::type_identity_t<T> a) noexcept {
    return detail::core_sub(x, a);
}
/// a - x, the core alone (kernel sub_1_2).
template <class T>
    requires detail::proof_checked<gen::bounds::sub_1_2<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> sub(std::type_identity_t<T> a, const Expansion<T, 2>& x) noexcept {
    return detail::core_sub(a, x);
}
/// x - y for a one-limb y, the core alone (kernel sub_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::sub_2_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> sub(const Expansion<T, 2>& x, const Expansion<T, 1>& y) noexcept {
    return detail::core_sub(x, y.limb[0]);
}
/// x - y for a one-limb x, the core alone (kernel sub_1_2).
template <class T>
    requires detail::proof_checked<gen::bounds::sub_1_2<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> sub(const Expansion<T, 1>& x, const Expansion<T, 2>& y) noexcept {
    return detail::core_sub(x.limb[0], y);
}
/// x * y, the core alone (kernel mul_2_2). Not usable in constant evaluation yet.
template <class T>
    requires detail::proof_checked<gen::bounds::mul_2_2<T>>
KAIRN_FORCEINLINE Expansion<T, 2> mul(const Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    return detail::core_mul(x, y);
}
/// x * a, the core alone (kernel mul_2_1). Not usable in constant evaluation yet.
template <class T>
    requires detail::proof_checked<gen::bounds::mul_2_1<T>>
KAIRN_FORCEINLINE Expansion<T, 2> mul(const Expansion<T, 2>& x, std::type_identity_t<T> a) noexcept {
    return detail::core_mul(x, a);
}
/// a * x, the core alone (kernel mul_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::mul_2_1<T>>
KAIRN_FORCEINLINE Expansion<T, 2> mul(std::type_identity_t<T> a, const Expansion<T, 2>& x) noexcept {
    return detail::core_mul(x, a);
}
/// x * y for a one-limb y, the core alone (kernel mul_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::mul_2_1<T>>
KAIRN_FORCEINLINE Expansion<T, 2> mul(const Expansion<T, 2>& x, const Expansion<T, 1>& y) noexcept {
    return detail::core_mul(x, y.limb[0]);
}
/// x * y for a one-limb x, the core alone (kernel mul_2_1).
template <class T>
    requires detail::proof_checked<gen::bounds::mul_2_1<T>>
KAIRN_FORCEINLINE Expansion<T, 2> mul(const Expansion<T, 1>& x, const Expansion<T, 2>& y) noexcept {
    return detail::core_mul(y, x.limb[0]);
}
/// The fast addition, the core alone (kernel add_fast_2_2).
template <class T>
    requires detail::proof_checked<gen::bounds::add_fast_2_2<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> add_fast(const Expansion<T, 2>& x, const Expansion<T, 2>& y) noexcept {
    return detail::core_add_fast(x, y);
}
/// x times 2^n, the core alone (kernel mul_pow2_2), in the same steps as kairn::ldexp when 2^n is
/// not a number of T. Not usable in constant evaluation yet.
template <class T>
    requires detail::proof_checked<gen::bounds::mul_pow2_2<T>>
KAIRN_FORCEINLINE Expansion<T, 2> ldexp(const Expansion<T, 2>& x, int n) noexcept {
    return detail::core_ldexp(x, n);
}

/// x + y for one limb: the operator (kernel add_1_1).
template <class T>
    requires detail::proof_checked<gen::bounds::add_1_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> add(const Expansion<T, 1>& x, const Expansion<T, 1>& y) noexcept {
    return detail::add(x, y);
}
/// x + a for one limb (kernel add_1_1).
template <class T>
    requires detail::proof_checked<gen::bounds::add_1_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> add(const Expansion<T, 1>& x, std::type_identity_t<T> a) noexcept {
    return detail::add(x, a);
}
/// a + x for one limb (kernel add_1_1).
template <class T>
    requires detail::proof_checked<gen::bounds::add_1_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> add(std::type_identity_t<T> a, const Expansion<T, 1>& x) noexcept {
    return detail::add(a, x);
}
/// x - y for one limb (kernel add_1_1 on x and -y).
template <class T>
    requires detail::proof_checked<gen::bounds::add_1_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> sub(const Expansion<T, 1>& x, const Expansion<T, 1>& y) noexcept {
    return detail::sub(x, y);
}
/// x - a for one limb (kernel add_1_1).
template <class T>
    requires detail::proof_checked<gen::bounds::add_1_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> sub(const Expansion<T, 1>& x, std::type_identity_t<T> a) noexcept {
    return detail::sub(x, a);
}
/// a - x for one limb (kernel add_1_1).
template <class T>
    requires detail::proof_checked<gen::bounds::add_1_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> sub(std::type_identity_t<T> a, const Expansion<T, 1>& x) noexcept {
    return detail::sub(a, x);
}
/// x * y for one limb (kernel mul_1_1).
template <class T>
    requires detail::proof_checked<gen::bounds::mul_1_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> mul(const Expansion<T, 1>& x, const Expansion<T, 1>& y) noexcept {
    return detail::mul(x, y);
}
/// x * a for one limb (kernel mul_1_1).
template <class T>
    requires detail::proof_checked<gen::bounds::mul_1_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> mul(const Expansion<T, 1>& x, std::type_identity_t<T> a) noexcept {
    return detail::mul(x, a);
}
/// a * x for one limb (kernel mul_1_1).
template <class T>
    requires detail::proof_checked<gen::bounds::mul_1_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> mul(std::type_identity_t<T> a, const Expansion<T, 1>& x) noexcept {
    return detail::mul(a, x);
}
/// The fast addition for one limb: x + y (kernel add_1_1).
template <class T>
    requires detail::proof_checked<gen::bounds::add_1_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> add_fast(const Expansion<T, 1>& x, const Expansion<T, 1>& y) noexcept {
    return detail::add(x, y);
}
/// x times 2^n for one limb: kairn::ldexp (kernel mul_1_1).
template <class T>
    requires detail::proof_checked<gen::bounds::mul_1_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> ldexp(const Expansion<T, 1>& x, int n) noexcept {
    return detail::ldexp(x, n);
}

/// x + y with a marked operand, for every combination above.
template <class X, class Y>
    requires kairn::detail::marked_expansion_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto add(const X& x, const Y& y) noexcept
    -> decltype(kairn::detail::core_add(kairn::detail::unmark(x), kairn::detail::unmark(y))) {
    return kairn::detail::core_add(kairn::detail::unmark(x), kairn::detail::unmark(y));
}
/// x - y with a marked operand.
template <class X, class Y>
    requires kairn::detail::marked_expansion_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto sub(const X& x, const Y& y) noexcept
    -> decltype(kairn::detail::core_sub(kairn::detail::unmark(x), kairn::detail::unmark(y))) {
    return kairn::detail::core_sub(kairn::detail::unmark(x), kairn::detail::unmark(y));
}
/// x * y with a marked operand.
template <class X, class Y>
    requires kairn::detail::marked_expansion_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto mul(const X& x, const Y& y) noexcept
    -> decltype(kairn::detail::core_mul(kairn::detail::unmark(x), kairn::detail::unmark(y))) {
    return kairn::detail::core_mul(kairn::detail::unmark(x), kairn::detail::unmark(y));
}
/// The fast addition with a marked operand.
template <class X, class Y>
    requires kairn::detail::marked_expansion_pair<X, Y>
KAIRN_FORCEINLINE constexpr auto add_fast(const X& x, const Y& y) noexcept
    -> decltype(kairn::detail::core_add_fast(kairn::detail::unmark(x), kairn::detail::unmark(y))) {
    return kairn::detail::core_add_fast(kairn::detail::unmark(x), kairn::detail::unmark(y));
}
/// x times 2^n with a marked operand.
template <class X>
    requires kairn::detail::marked<X>
KAIRN_FORCEINLINE constexpr auto ldexp(const X& x, int n) noexcept
    -> decltype(kairn::detail::core_ldexp(kairn::detail::unmark(x), n)) {
    return kairn::detail::core_ldexp(kairn::detail::unmark(x), n);
}

}  // namespace finite

}  // namespace kairn
