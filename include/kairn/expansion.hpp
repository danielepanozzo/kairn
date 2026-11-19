// Expansion<T, 1> and Expansion<T, 2>: a value stored as the unevaluated sum of one or two limbs
// of type T (float or double), and their operations.
//
// Every operation forwards to one generated kernel (include/kairn/gen/scalar.hpp) whose claims
// are in gen/claims.json; the comment of each operation names it and quotes its claim. An
// operation whose kernel is proved compiles as written; any other needs the kairn::unverified
// marker on one operand (config.hpp). Which kernels are proved is read from
// include/kairn/gen/bounds.hpp, never written here, so an operation loses the need for the
// marker when its proof is checked and the generator is rerun.
//
// What holds for every arithmetic operation: the result is the finite core of the kernel. The
// layer that turns overflow and non-finite operands into canonical infinities and NaN (decision
// D5; the full kernels of docs/developer/design/milestone1.md, "IEEE-like results") is not
// generated yet, so a result whose leading limb is not finite may be any non-finite pattern, such
// as (inf, nan), and an operand with a non-finite limb gives a result about which nothing is
// claimed. docs/getting-started/guarantees.md has the table of what is proved.
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
/// Operations require their operands to be *normalized*: every limb finite, and each limb equal
/// to the sum of itself and the next one rounded to nearest (for two limbs, x0 + x1 == x0 in
/// floating point). Every constructor and every operation returns normalized numbers when their
/// leading limb is finite. See docs/developer/design/phase0/numbers.md.
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

/// 2^n exactly when it is a number of T (n from the exponent of the smallest subnormal to that of
/// the largest power of two); NaN otherwise.
template <limb T>
KAIRN_FORCEINLINE constexpr T pow2(int n) noexcept {
    if constexpr (sizeof(T) == 8) {
        if (n > 1023 || n < -1074) return std::numeric_limits<T>::quiet_NaN();
        if (n >= -1022) return std::bit_cast<T>(std::uint64_t(n + 1023) << 52);
        return std::bit_cast<T>(std::uint64_t{1} << (n + 1074));
    } else {
        if (n > 127 || n < -149) return std::numeric_limits<T>::quiet_NaN();
        if (n >= -126) return std::bit_cast<T>(std::uint32_t(n + 127) << 23);
        return std::bit_cast<T>(std::uint32_t{1} << (n + 149));
    }
}

// Whether an operand is one an operation accepts: normalized, or with a non-finite leading limb
// (what the finite cores return on overflow; nothing is claimed about the result then).
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
    return !finite(x.limb[0]) || (finite(x.limb[1]) && x.limb[0] + x.limb[1] == x.limb[0]);
}

// The checks of KAIRN_CHECKS, once per operation.
template <class... X>
KAIRN_FORCEINLINE constexpr void check([[maybe_unused]] const X&... x) noexcept {
#if KAIRN_CHECKS
    check_environment();
    if (!(admissible(x) && ...))
        fail("an operand", "is not normalized (x0 + x1 is not x0), so no guarantee applies to the result");
#endif
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
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> ldexp(Expansion<T, 1> x, int n) noexcept {
    KAIRN_DETAIL_K1_CONTRACT
    check(x);
    return Expansion<T, 1>(x.limb[0] * pow2<T>(n));
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> half(Expansion<T, 1> x) noexcept {
    KAIRN_DETAIL_K1_CONTRACT
    check(x);
    return Expansion<T, 1>(x.limb[0] * T(0.5));
}
template <class T>
KAIRN_FORCEINLINE constexpr bool lt(Expansion<T, 1> x, Expansion<T, 1> y) noexcept {
    check(x, y);
    return x.limb[0] < y.limb[0];
}
template <class T>
KAIRN_FORCEINLINE constexpr bool le(Expansion<T, 1> x, Expansion<T, 1> y) noexcept {
    check(x, y);
    return x.limb[0] <= y.limb[0];
}
template <class T>
KAIRN_FORCEINLINE constexpr bool eq(Expansion<T, 1> x, Expansion<T, 1> y) noexcept {
    check(x, y);
    return x.limb[0] == y.limb[0];
}
#define KAIRN_DETAIL_K1_COMPARE(NAME)                                                                    \
    template <class T>                                                                                   \
    KAIRN_FORCEINLINE constexpr bool NAME(Expansion<T, 1> x, std::type_identity_t<T> a) noexcept {       \
        return NAME(x, Expansion<T, 1>(a));                                                              \
    }                                                                                                    \
    template <class T>                                                                                   \
    KAIRN_FORCEINLINE constexpr bool NAME(std::type_identity_t<T> a, Expansion<T, 1> y) noexcept {       \
        return NAME(Expansion<T, 1>(a), y);                                                              \
    }
KAIRN_DETAIL_K1_COMPARE(lt)
KAIRN_DETAIL_K1_COMPARE(le)
KAIRN_DETAIL_K1_COMPARE(eq)
#undef KAIRN_DETAIL_K1_COMPARE
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

// k = 2: the generated kernels.
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> add(Expansion<T, 2> x, Expansion<T, 2> y) noexcept {
    check(x, y);
    Expansion<T, 2> z;
    gen::add_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> add(Expansion<T, 2> x, std::type_identity_t<T> a) noexcept {
    check(x);
    Expansion<T, 2> z;
    gen::add_2_1(x.limb[0], x.limb[1], a, z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> add(std::type_identity_t<T> a, Expansion<T, 2> y) noexcept {
    return add(y, a);
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> sub(Expansion<T, 2> x, Expansion<T, 2> y) noexcept {
    check(x, y);
    Expansion<T, 2> z;
    gen::sub_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> sub(Expansion<T, 2> x, std::type_identity_t<T> a) noexcept {
    check(x);
    Expansion<T, 2> z;
    gen::sub_2_1(x.limb[0], x.limb[1], a, z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE constexpr Expansion<T, 2> sub(std::type_identity_t<T> a, Expansion<T, 2> y) noexcept {
    check(y);
    Expansion<T, 2> z;
    gen::sub_1_2(a, y.limb[0], y.limb[1], z.limb[0], z.limb[1]);
    return z;
}
// Not constexpr: the products have fused operations and no constant-evaluation variant yet.
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> mul(Expansion<T, 2> x, Expansion<T, 2> y) noexcept {
    check(x, y);
    Expansion<T, 2> z;
    gen::mul_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> mul(Expansion<T, 2> x, std::type_identity_t<T> a) noexcept {
    check(x);
    Expansion<T, 2> z;
    gen::mul_2_1(x.limb[0], x.limb[1], a, z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> mul(std::type_identity_t<T> a, Expansion<T, 2> y) noexcept {
    return mul(y, a);
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
    Expansion<T, 2> z;
    gen::add_fast_2_2(x.limb[0], x.limb[1], y.limb[0], y.limb[1], z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> ldexp(Expansion<T, 2> x, int n) noexcept {
    check(x);
    Expansion<T, 2> z;
    gen::mul_pow2_2(x.limb[0], x.limb[1], pow2<T>(n), z.limb[0], z.limb[1]);
    return z;
}
template <class T>
KAIRN_FORCEINLINE Expansion<T, 2> half(Expansion<T, 2> x) noexcept {
    check(x);
    Expansion<T, 2> z;
    gen::mul_pow2_2(x.limb[0], x.limb[1], T(0.5), z.limb[0], z.limb[1]);
    return z;
}
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
        bool m = false;                                                                                  \
        gen::NAME##_2_1(x.limb[0], x.limb[1], a, m);                                                     \
        return m;                                                                                        \
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

// Mixed numbers of limbs: the one-limb operand is converted first, then the two-limb operation
// runs (docs/developer/design/phase0/operations.md, "Conversions and scaling").
#define KAIRN_DETAIL_MIXED(NAME, CONSTEXPR)                                                              \
    template <class T>                                                                                   \
    KAIRN_FORCEINLINE CONSTEXPR auto NAME(Expansion<T, 2> x, Expansion<T, 1> y) noexcept {               \
        return NAME(x, Expansion<T, 2>(y));                                                              \
    }                                                                                                    \
    template <class T>                                                                                   \
    KAIRN_FORCEINLINE CONSTEXPR auto NAME(Expansion<T, 1> x, Expansion<T, 2> y) noexcept {               \
        return NAME(Expansion<T, 2>(x), y);                                                              \
    }
KAIRN_DETAIL_MIXED(add, constexpr)
KAIRN_DETAIL_MIXED(sub, constexpr)
KAIRN_DETAIL_MIXED(mul, )
KAIRN_DETAIL_MIXED(lt, constexpr)
KAIRN_DETAIL_MIXED(le, constexpr)
KAIRN_DETAIL_MIXED(eq, constexpr)
#undef KAIRN_DETAIL_MIXED

}  // namespace detail

/// One limb: the value is limb[0], and every operation is the IEEE 754 operation of T.
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
template <class T>
struct Expansion<T, 1> {
    static_assert(detail::limb<T>, "Expansion<T, k>: the limb type T is float or double");

    /// The limb, which is the value.
    T limb[1] = {};

    /// Zero.
    constexpr Expansion() noexcept = default;
    /// x, exactly. Implicit, as T converts to T.
    constexpr Expansion(T x) noexcept : limb{x} {}
    /// The leading limb of x: truncation, which for a normalized x is x rounded to nearest (the
    /// claim of kernel to_nearest_2). Explicit, because it loses the second limb.
    explicit constexpr Expansion(const Expansion<T, 2>& x) noexcept : limb{x.limb[0]} {}
    /// limbs[0]: every finite T is a normalized one-limb number.
    static constexpr Expansion from_limbs(const T* limbs) noexcept { return Expansion(limbs[0]); }
    /// limbs[0].
    static constexpr Expansion from_limbs_unchecked(const T* limbs) noexcept { return Expansion(limbs[0]); }

    /// x + y, rounded to nearest (kernel add_1_1).
    friend KAIRN_FORCEINLINE constexpr Expansion operator+(Expansion x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::add_1_1<T>>
    {
        return detail::add(x, y);
    }
    /// x - y, rounded to nearest (kernel add_1_1 on x and -y).
    friend KAIRN_FORCEINLINE constexpr Expansion operator-(Expansion x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::add_1_1<T>>
    {
        return detail::sub(x, y);
    }
    /// x * y, rounded to nearest (kernel mul_1_1).
    friend KAIRN_FORCEINLINE constexpr Expansion operator*(Expansion x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::mul_1_1<T>>
    {
        return detail::mul(x, y);
    }
    /// x = x + y (kernel add_1_1).
    friend KAIRN_FORCEINLINE constexpr Expansion& operator+=(Expansion& x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::add_1_1<T>>
    {
        return x = detail::add(x, y);
    }
    /// x = x - y (kernel add_1_1).
    friend KAIRN_FORCEINLINE constexpr Expansion& operator-=(Expansion& x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::add_1_1<T>>
    {
        return x = detail::sub(x, y);
    }
    /// x = x * y (kernel mul_1_1).
    friend KAIRN_FORCEINLINE constexpr Expansion& operator*=(Expansion& x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::mul_1_1<T>>
    {
        return x = detail::mul(x, y);
    }
    /// -x, exactly.
    friend KAIRN_FORCEINLINE constexpr Expansion operator-(Expansion x) noexcept { return detail::neg(x); }
    /// Whether x < y, exactly: the comparison of T. False if either is NaN.
    friend KAIRN_FORCEINLINE constexpr bool operator<(Expansion x, Expansion y) noexcept { return detail::lt(x, y); }
    /// Whether x > y, exactly. False if either is NaN.
    friend KAIRN_FORCEINLINE constexpr bool operator>(Expansion x, Expansion y) noexcept { return detail::lt(y, x); }
    /// Whether x <= y, exactly. False if either is NaN.
    friend KAIRN_FORCEINLINE constexpr bool operator<=(Expansion x, Expansion y) noexcept { return detail::le(x, y); }
    /// Whether x >= y, exactly. False if either is NaN.
    friend KAIRN_FORCEINLINE constexpr bool operator>=(Expansion x, Expansion y) noexcept { return detail::le(y, x); }
    /// Whether x == y, exactly (+0 equals -0). False if either is NaN.
    friend KAIRN_FORCEINLINE constexpr bool operator==(Expansion x, Expansion y) noexcept { return detail::eq(x, y); }
    /// Whether x != y, exactly. True if either is NaN.
    friend KAIRN_FORCEINLINE constexpr bool operator!=(Expansion x, Expansion y) noexcept { return !detail::eq(x, y); }
};

/// Two limbs (a double-word number): the value is limb[0] + limb[1], exactly, and limb[1] is at
/// most half a unit in the last place of limb[0], so that limb[0] is the value rounded to nearest.
/// With double limbs that is 106 bits of precision for values above about 2^-969, fewer below
/// (docs/developer/design/phase0/numbers.md, "Precision depends on magnitude").
///
/// Each operation below names its kernel and quotes the kernel's claim from gen/claims.json, for
/// normalized operands (u = 2^-p is the unit roundoff of T, 2^-53 for double; eta is its smallest
/// subnormal number, 2^-1074 for double). A claim is a guarantee when its kernel is proved, which
/// is exactly when the operation compiles without kairn::unverified; the table of what is proved
/// is docs/getting-started/guarantees.md. Claims are stated in a model where no operation
/// overflows; what is proved when one does is said per operation.
///
/// Every arithmetic operation is the finite core of its kernel: the layer that returns canonical
/// infinities and NaN (decision D5) is not generated yet. When the leading limb of a result is
/// not finite the limbs may hold any non-finite pattern, and an operand with a non-finite limb
/// gives a result about which nothing is claimed.
///
/// Not covered by any guarantee today: a product computed by the program and passed to an
/// operation, as in x + a * b, under a contraction setting that fuses across statements (GCC's
/// default for C++, -ffp-contract=fast on AArch64 Clang, MSVC's /fp:contract). The compiler can
/// fuse that product into the kernel's error-free sums, which then are not error-free: measured,
/// a normalized result with a relative error near 2^-24, where the bound is near 2^-104. Rule R2
/// of the generator prevents this between Kairn's own kernels, not at the boundary with the
/// program's code. -ffp-contract=off or =on, /fp:precise and /fp:strict are not affected.
template <class T>
struct Expansion<T, 2> {
    static_assert(detail::limb<T>, "Expansion<T, k>: the limb type T is float or double");

    /// The limbs, most significant first.
    T limb[2] = {};

    /// Zero.
    constexpr Expansion() noexcept = default;
    /// x, exactly: (x, 0). For a non-finite x, the canonical forms (+inf, 0), (-inf, 0) and
    /// (NaN, NaN).
    constexpr Expansion(T x) noexcept : limb{x, x == x ? T(0) : x} {}
    /// x, exactly: (x0, 0), or a canonical non-finite form as above.
    constexpr Expansion(const Expansion<T, 1>& x) noexcept : Expansion(x.limb[0]) {}
    /// The number with these two limbs (limbs[0], limbs[1]). They must form a normalized number:
    /// limbs[0] + limbs[1] rounded to nearest is limbs[0]. Checked when KAIRN_CHECKS is 1, and
    /// then a violation fails a constant expression or calls the failure handler; not checked
    /// otherwise.
    static constexpr Expansion from_limbs(const T* limbs) noexcept {
        Expansion x = from_limbs_unchecked(limbs);
        detail::check(x);
        return x;
    }
    /// The number with these two limbs, unchecked. If they do not form a normalized number,
    /// operations on it have no undefined behavior but give results with no guarantee.
    static constexpr Expansion from_limbs_unchecked(const T* limbs) noexcept {
        Expansion x;
        x.limb[0] = limbs[0];
        x.limb[1] = limbs[1];
        return x;
    }

    /// x + y, the accurate addition (kernel add_2_2, JMP17 Algorithm 6).
    ///
    /// Claim: the result z is normalized and |z - (x + y)| <= 3u^2/(1 - 4u) |x + y|, with no
    /// underflow term. Proved also in Flocq's model of IEEE 754 with overflow (a statement written
    /// by hand, docs/developer/design/milestone1.md): either z0 is not finite, or z1 is finite and
    /// the claim holds; and z0 is finite when |x0| and |y0| are at most 2^1022 (double) or 2^126
    /// (float). Not yet: canonical infinities and NaN (decision D5).
    friend KAIRN_FORCEINLINE constexpr Expansion operator+(Expansion x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::add_2_2<T>>
    {
        return detail::add(x, y);
    }
    /// x + a (kernel add_2_1, JMP17 Algorithm 4).
    ///
    /// Claim: the result z is normalized and |z - (x + a)| <= 2u^2 |x + a|. Proved also in
    /// Flocq's model of IEEE 754 with overflow (hand-written statement): either z0 is not finite,
    /// or the claim holds. Not yet: a condition under which z0 is finite, and canonical
    /// infinities and NaN (D5).
    friend KAIRN_FORCEINLINE constexpr Expansion operator+(Expansion x, T a) noexcept
        requires detail::proof_checked<gen::bounds::add_2_1<T>>
    {
        return detail::add(x, a);
    }
    /// a + x: the same operation and claim as x + a.
    friend KAIRN_FORCEINLINE constexpr Expansion operator+(T a, Expansion x) noexcept
        requires detail::proof_checked<gen::bounds::add_2_1<T>>
    {
        return detail::add(a, x);
    }
    /// x - y (kernel sub_2_2: add_2_2 on x and -y). Claim: that of x + y, for x - y. In the IEEE
    /// model with overflow nothing is proved yet for this kernel.
    friend KAIRN_FORCEINLINE constexpr Expansion operator-(Expansion x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::sub_2_2<T>>
    {
        return detail::sub(x, y);
    }
    /// x - a (kernel sub_2_1). Claim: that of x + a, for x - a. In the IEEE model with overflow
    /// nothing is proved yet for this kernel.
    friend KAIRN_FORCEINLINE constexpr Expansion operator-(Expansion x, T a) noexcept
        requires detail::proof_checked<gen::bounds::sub_2_1<T>>
    {
        return detail::sub(x, a);
    }
    /// a - x (kernel sub_1_2). Claim: that of x + a, for a - x. In the IEEE model with overflow
    /// nothing is proved yet for this kernel.
    friend KAIRN_FORCEINLINE constexpr Expansion operator-(T a, Expansion x) noexcept
        requires detail::proof_checked<gen::bounds::sub_1_2<T>>
    {
        return detail::sub(a, x);
    }
    /// x * y (kernel mul_2_2, JMP17 Algorithm 12). Not usable in constant evaluation yet.
    ///
    /// Claim: the result z is normalized and |z - xy| <= 4u^2 |xy| + (3/2) eta. Proved also in
    /// Flocq's model of IEEE 754 with overflow (hand-written statement): either z0 is not finite,
    /// or the claim holds; and z0 is finite when |xy| is at most 2^1023 (double) or 2^127
    /// (float). Not yet: canonical infinities and NaN (D5).
    friend KAIRN_FORCEINLINE Expansion operator*(Expansion x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::mul_2_2<T>>
    {
        return detail::mul(x, y);
    }
    /// x * a (kernel mul_2_1, JMP17 Algorithm 9). Not usable in constant evaluation yet.
    ///
    /// Claim: the result z is normalized and |z - xa| <= 2u^2 |xa| + eta. Proved also in
    /// Flocq's model of IEEE 754 with overflow (hand-written statement): either z0 is not finite,
    /// or the claim holds. Not yet: a condition under which z0 is finite, and canonical
    /// infinities and NaN (D5).
    friend KAIRN_FORCEINLINE Expansion operator*(Expansion x, T a) noexcept
        requires detail::proof_checked<gen::bounds::mul_2_1<T>>
    {
        return detail::mul(x, a);
    }
    /// a * x: the same operation and claim as x * a.
    friend KAIRN_FORCEINLINE Expansion operator*(T a, Expansion x) noexcept
        requires detail::proof_checked<gen::bounds::mul_2_1<T>>
    {
        return detail::mul(a, x);
    }
    /// x = x + y: as x + y.
    friend KAIRN_FORCEINLINE constexpr Expansion& operator+=(Expansion& x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::add_2_2<T>>
    {
        return x = detail::add(x, y);
    }
    /// x = x + a: as x + a.
    friend KAIRN_FORCEINLINE constexpr Expansion& operator+=(Expansion& x, T a) noexcept
        requires detail::proof_checked<gen::bounds::add_2_1<T>>
    {
        return x = detail::add(x, a);
    }
    /// x = x - y: as x - y.
    friend KAIRN_FORCEINLINE constexpr Expansion& operator-=(Expansion& x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::sub_2_2<T>>
    {
        return x = detail::sub(x, y);
    }
    /// x = x - a: as x - a.
    friend KAIRN_FORCEINLINE constexpr Expansion& operator-=(Expansion& x, T a) noexcept
        requires detail::proof_checked<gen::bounds::sub_2_1<T>>
    {
        return x = detail::sub(x, a);
    }
    /// x = x * y: as x * y.
    friend KAIRN_FORCEINLINE Expansion& operator*=(Expansion& x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::mul_2_2<T>>
    {
        return x = detail::mul(x, y);
    }
    /// x = x * a: as x * a.
    friend KAIRN_FORCEINLINE Expansion& operator*=(Expansion& x, T a) noexcept
        requires detail::proof_checked<gen::bounds::mul_2_1<T>>
    {
        return x = detail::mul(x, a);
    }
    /// -x, limb by limb (kernel neg_2). Claim: exactly -x, normalized.
    friend KAIRN_FORCEINLINE constexpr Expansion operator-(Expansion x) noexcept
        requires detail::proof_checked<gen::bounds::neg_2<T>>
    {
        return detail::neg(x);
    }

    /// Whether x < y (kernel lt_2_2). Claim: the truth about the exact values, for normalized
    /// operands. With a NaN limb the result is false, as the comparisons of T are, but no claim
    /// covers non-finite operands yet. The same holds for every comparison below.
    friend KAIRN_FORCEINLINE constexpr bool operator<(Expansion x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::lt_2_2<T>>
    {
        return detail::lt(x, y);
    }
    /// Whether x > y (kernel lt_2_2 on y, x).
    friend KAIRN_FORCEINLINE constexpr bool operator>(Expansion x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::lt_2_2<T>>
    {
        return detail::lt(y, x);
    }
    /// Whether x <= y (kernel le_2_2).
    friend KAIRN_FORCEINLINE constexpr bool operator<=(Expansion x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::le_2_2<T>>
    {
        return detail::le(x, y);
    }
    /// Whether x >= y (kernel le_2_2 on y, x).
    friend KAIRN_FORCEINLINE constexpr bool operator>=(Expansion x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::le_2_2<T>>
    {
        return detail::le(y, x);
    }
    /// Whether x == y (kernel eq_2_2).
    friend KAIRN_FORCEINLINE constexpr bool operator==(Expansion x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::eq_2_2<T>>
    {
        return detail::eq(x, y);
    }
    /// Whether x != y: not x == y (kernel eq_2_2).
    friend KAIRN_FORCEINLINE constexpr bool operator!=(Expansion x, Expansion y) noexcept
        requires detail::proof_checked<gen::bounds::eq_2_2<T>>
    {
        return !detail::eq(x, y);
    }
    /// Whether x < a (kernel lt_2_1).
    friend KAIRN_FORCEINLINE constexpr bool operator<(Expansion x, T a) noexcept
        requires detail::proof_checked<gen::bounds::lt_2_1<T>>
    {
        return detail::lt(x, a);
    }
    /// Whether x > a: a < x (kernel lt_1_2).
    friend KAIRN_FORCEINLINE constexpr bool operator>(Expansion x, T a) noexcept
        requires detail::proof_checked<gen::bounds::lt_1_2<T>>
    {
        return detail::lt(a, x);
    }
    /// Whether x <= a (kernel le_2_1).
    friend KAIRN_FORCEINLINE constexpr bool operator<=(Expansion x, T a) noexcept
        requires detail::proof_checked<gen::bounds::le_2_1<T>>
    {
        return detail::le(x, a);
    }
    /// Whether x >= a: a <= x (kernel le_1_2).
    friend KAIRN_FORCEINLINE constexpr bool operator>=(Expansion x, T a) noexcept
        requires detail::proof_checked<gen::bounds::le_1_2<T>>
    {
        return detail::le(a, x);
    }
    /// Whether x == a (kernel eq_2_1).
    friend KAIRN_FORCEINLINE constexpr bool operator==(Expansion x, T a) noexcept
        requires detail::proof_checked<gen::bounds::eq_2_1<T>>
    {
        return detail::eq(x, a);
    }
    /// Whether x != a (kernel eq_2_1).
    friend KAIRN_FORCEINLINE constexpr bool operator!=(Expansion x, T a) noexcept
        requires detail::proof_checked<gen::bounds::eq_2_1<T>>
    {
        return !detail::eq(x, a);
    }
    /// Whether a < x (kernel lt_1_2).
    friend KAIRN_FORCEINLINE constexpr bool operator<(T a, Expansion x) noexcept
        requires detail::proof_checked<gen::bounds::lt_1_2<T>>
    {
        return detail::lt(a, x);
    }
    /// Whether a > x: x < a (kernel lt_2_1).
    friend KAIRN_FORCEINLINE constexpr bool operator>(T a, Expansion x) noexcept
        requires detail::proof_checked<gen::bounds::lt_2_1<T>>
    {
        return detail::lt(x, a);
    }
    /// Whether a <= x (kernel le_1_2).
    friend KAIRN_FORCEINLINE constexpr bool operator<=(T a, Expansion x) noexcept
        requires detail::proof_checked<gen::bounds::le_1_2<T>>
    {
        return detail::le(a, x);
    }
    /// Whether a >= x: x <= a (kernel le_2_1).
    friend KAIRN_FORCEINLINE constexpr bool operator>=(T a, Expansion x) noexcept
        requires detail::proof_checked<gen::bounds::le_2_1<T>>
    {
        return detail::le(x, a);
    }
    /// Whether a == x (kernel eq_2_1).
    friend KAIRN_FORCEINLINE constexpr bool operator==(T a, Expansion x) noexcept
        requires detail::proof_checked<gen::bounds::eq_2_1<T>>
    {
        return detail::eq(x, a);
    }
    /// Whether a != x (kernel eq_2_1).
    friend KAIRN_FORCEINLINE constexpr bool operator!=(T a, Expansion x) noexcept
        requires detail::proof_checked<gen::bounds::eq_2_1<T>>
    {
        return !detail::eq(x, a);
    }
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

// The operations with a marked operand. One template per operator covers every combination of a
// marked and an unmarked operand; it exists only where the operation does (the return type names
// it), so it never competes with the operators above, which take no marked operand.
namespace detail {
template <class X, class Y>
concept marked_expansion_pair = (marked<X> || marked<Y>) && !ball<X> && !ball<Y>;
template <class X, class Y>
concept marked_expansion_rhs = marked<Y> && !marked<X> && !ball<X> && !ball<Y>;
}  // namespace detail

/// x + y with a marked operand: the same operation as without the marker, for any combination of
/// Expansion and T operands (a one-limb operand with a two-limb one is widened first).
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
/// |x| (kernel abs_2). Claim: exactly |x|, normalized.
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
/// The fast addition (kernel add_fast_2_2, JMP17 Algorithm 5): about half the operations of
/// x + y, with a weaker bound, relative to the operands rather than to the result. Claim: a
/// normalized result with |z - (x + y)| <= 3u^2 (|x| + |y|). It has no relative bound when x and
/// y nearly cancel, which is why x + y does not use it. Proved also in Flocq's model of IEEE 754
/// with overflow (hand-written statement): either z0 is not finite, or the claim holds.
template <class T>
    requires detail::proof_checked<gen::bounds::add_fast_2_2<T>>
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

/// x times 2^n, for an n such that 2^n is a number of T (from -1074 to 1023 for double, -149 to
/// 127 for float); for any other n the result is NaN. One limb: one rounded product (kernel
/// mul_1_1), exact unless the result is subnormal.
template <class T>
    requires detail::proof_checked<gen::bounds::mul_1_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> ldexp(const Expansion<T, 1>& x, int n) noexcept {
    return detail::ldexp(x, n);
}
/// x times 2^n, for an n such that 2^n is a number of T (from -1074 to 1023 for double, -149 to
/// 127 for float); for any other n the result is NaN (the two-step scaling that would cover them
/// is not written yet). Kernel mul_pow2_2; claim: a normalized result within eta of 2^n x (and,
/// proved as a hand-written statement, exactly 2^n x when each limb's product is zero or at least
/// 2^(p-1) eta in magnitude). In the IEEE model with overflow nothing is proved yet for this
/// kernel. Not usable in constant evaluation yet.
template <class T>
    requires detail::proof_checked<gen::bounds::mul_pow2_2<T>>
KAIRN_FORCEINLINE Expansion<T, 2> ldexp(const Expansion<T, 2>& x, int n) noexcept {
    return detail::ldexp(x, n);
}
/// x times 2^n with a marked operand.
template <class X>
    requires detail::marked<X>
KAIRN_FORCEINLINE constexpr auto ldexp(const X& x, int n) noexcept -> decltype(detail::ldexp(detail::unmark(x), n)) {
    return detail::ldexp(detail::unmark(x), n);
}
/// x / 2: ldexp(x, -1) (kernel mul_1_1).
template <class T>
    requires detail::proof_checked<gen::bounds::mul_1_1<T>>
KAIRN_FORCEINLINE constexpr Expansion<T, 1> half(const Expansion<T, 1>& x) noexcept {
    return detail::half(x);
}
/// x / 2: ldexp(x, -1) (kernel mul_pow2_2). Not usable in constant evaluation yet.
template <class T>
    requires detail::proof_checked<gen::bounds::mul_pow2_2<T>>
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
/// x rounded to nearest, ties to even: the leading limb (kernel to_nearest_2). Claim: exactly
/// that rounding, for normalized x.
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
/// The largest T not above x (kernel to_down_2). Claim: exactly that number, for normalized x.
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
/// The smallest T not below x (kernel to_up_2). Claim: exactly that number, for normalized x.
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
/// The smallest T not below |x| (kernel abs_upper_2). Claim: exactly that number, for
/// normalized x.
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

/// -1, 0 or +1: the sign of the value, read from the leading limb, which for a normalized number
/// has the sign of the value and is zero exactly when the value is (a consequence of the
/// invariant, docs/developer/design/phase0/numbers.md; no kernel). 0 for NaN. The sign of a zero
/// is not reported.
template <class T, int K>
KAIRN_FORCEINLINE constexpr int sign(const Expansion<T, K>& x) noexcept {
    return (x.limb[0] > 0) - (x.limb[0] < 0);
}
/// Whether x is finite, from its leading limb alone: Kairn's operations keep a non-finite limb
/// visible in the leading one (docs/developer/design/phase0/numbers.md, "Non-finite values").
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

}  // namespace kairn
