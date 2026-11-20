/// @file
/// kairn::rational and kairn::integer: a number of one or two limbs from a fraction of two 64-bit
/// integers, with a bound of the error it makes and whether it makes none, in constant expressions
/// and at run time (docs/reference/rational.md).
///
/// The result is specified exactly, bit for bit, and computed with integer operations only: no
/// floating-point operation is done, and each limb is assembled from its sign, significand and
/// exponent with std::bit_cast. So it is the same at compile time and at run time, under every
/// rounding mode and with every flag that config.hpp accepts, and a debug build does not check the
/// floating-point environment before it. This is integer code written by hand, not a generated
/// kernel: it has no generated model and no Rocq theorem. It is tested for equality against the
/// oracle, and every result computed in a constant expression is checked against the whole
/// specification by kairn::is_rational_result (KAIRN_RATIONAL_CHECK).
#pragma once

#include "config.hpp"
#include "expansion.hpp"
#include "traits.hpp"

#include <bit>
#include <cstdint>
#include <limits>
#include <type_traits>

/// @def KAIRN_RATIONAL_CHECK
/// 1 (the default) to check every result of kairn::rational and kairn::integer computed in a
/// constant expression against its whole specification, with kairn::is_rational_result, so that a
/// constant that would be wrong does not compile; 0 not to. At run time the same check is made when
/// KAIRN_CHECKS is 1, whatever this macro says, and a result that fails it prints a message and
/// calls std::abort(). Define it the same way in every translation unit of a program.
#if !defined(KAIRN_RATIONAL_CHECK)
#define KAIRN_RATIONAL_CHECK 1
#endif

KAIRN_GEN_PUSH_WARNINGS
namespace kairn {

/// The result of kairn::rational and kairn::integer: a number, a bound of its error, and whether it
/// is exact. X is float, double, Expansion<T, 1> or Expansion<T, 2>.
template <class X>
struct Constant {
    /// With q = num / den: for one limb, q rounded to nearest (ties to even, with gradual
    /// underflow); for two limbs, the normalized pair whose value is RN(q) + RN(q - RN(q)). For
    /// den = 0, at run time, the canonical NaN.
    X value{};
    /// The smallest number of the limb type that is at least |value - q|: zero exactly when value
    /// is q. For den = 0, at run time, +infinity.
    typename traits<X>::limb_type error{};
    /// Whether value is q exactly (error is zero). False for den = 0.
    bool exact = false;
};

namespace detail {

/// The number types that kairn::rational makes: float, double, and Expansion<T, K> for K = 1, 2.
template <class X>
inline constexpr bool is_number_v = limb<X>;
template <class T, int K>
inline constexpr bool is_number_v<Expansion<T, K>> = limb<T> && (K == 1 || K == 2);
/// Whether X is one of those types.
template <class X>
concept number = is_number_v<X>;

/// Called by kairn::rational in a constant expression whose denominator is zero, which makes the
/// expression invalid: the compiler's message names this function.
inline void rational_denominator_is_zero() noexcept {
    fail("rational", "the denominator is zero");
}
/// Called by kairn::rational in a constant expression whose result fails its own check
/// (KAIRN_RATIONAL_CHECK), which makes the expression invalid.
inline void rational_result_fails_its_specification() noexcept {
    fail("rational", "the result does not satisfy its specification (kairn::is_rational_result)");
}

// The computation of kairn::rational, and its checker. Integers only.
namespace fraction {

// The format of T as integers: a number of T is (-1)^s m 2^e with 0 <= m < 2^p and qmin <= e, and
// m >= 2^(p - 1) unless e = qmin (docs/developer/architecture.md, "Number formats").
template <class T>
struct format {
    static constexpr int p = std::numeric_limits<T>::digits;               // 53, 24
    static constexpr int qmin = pow2_min<T>;                               // -1074, -149
    static constexpr int bias = std::numeric_limits<T>::max_exponent - 1;  // 1023, 127
    static constexpr int width = int(sizeof(T)) * 8;                       // bits of the pattern
    using bits = std::conditional_t<sizeof(T) == 8, std::uint64_t, std::uint32_t>;
};

// A number as integers: (-1)^neg m 2^e.
struct parts {
    bool neg = false;
    std::uint64_t m = 0;
    int e = 0;
};

constexpr int width_of(std::uint64_t x) noexcept {
    return static_cast<int>(std::bit_width(x));
}

// |x| as an unsigned word: -2^63 included.
constexpr std::uint64_t magnitude(long long x) noexcept {
    const std::uint64_t u = static_cast<std::uint64_t>(x);
    return x < 0 ? std::uint64_t{0} - u : u;
}

// The number (-1)^neg m 2^e of T, from its bit pattern. m 2^e must be a number of T, with m below
// 2^(p + 1): a rounding up may leave m = 2^p, and the renormalization a significand below 2^(p - 1)
// with an exponent above qmin; both are first brought to the form of the format. Zero is +0.
template <class T>
constexpr T limb_of(parts x) noexcept {
    using F = format<T>;
    using U = typename F::bits;
    if (x.m == 0) return std::bit_cast<T>(U{0});
    while ((x.m >> F::p) != 0) {  // exact: only m = 2^p comes here
        x.m >>= 1;
        ++x.e;
    }
    while ((x.m >> (F::p - 1)) == 0 && x.e > F::qmin) {
        x.m <<= 1;
        --x.e;
    }
    U pattern = static_cast<U>(x.m);  // a subnormal number: m 2^qmin
    if ((x.m >> (F::p - 1)) != 0) {
        // A normal number: the leading bit is implicit, and the exponent of 1.f is e + p - 1.
        const U biased = static_cast<U>(x.e + F::p - 1 + F::bias);
        pattern = static_cast<U>((biased << (F::p - 1)) | (pattern & ((U{1} << (F::p - 1)) - 1)));
    }
    if (x.neg) pattern = static_cast<U>(pattern | (U{1} << (F::width - 1)));
    return std::bit_cast<T>(pattern);
}

// r / d 2^e_in = (m + rem / den) 2^e exactly, with 0 <= rem < den <= 2^63, the exponent
// e = max(qmin, floor(log2(r / d 2^e_in)) - p + 1), and m < 2^p: m is the quotient truncated to p
// bits, or to fewer in the subnormal range.
struct quotient {
    std::uint64_t m = 0;
    std::uint64_t rem = 0;
    std::uint64_t den = 0;
    int e = 0;
};

// The quotient above, for 0 < r < 2^64, 0 < d <= 2^63 and qmin <= e_in. Every integer is one 64-bit
// word: the remainder stays below the divisor, which is at most 2^63, so twice the remainder is
// below 2^64, and the quotient below 2^p. One division of words gives the integer part of r / d
// (zero unless this is the first limb), then each step one bit more, at most p + 1 steps after the
// leading zero bits are skipped.
template <int P, int QMIN>
constexpr quotient divide(std::uint64_t r, std::uint64_t d, int e_in) noexcept {
    const int wr = width_of(r), wd = width_of(d);
    int top = wr - wd;  // floor(log2(r / d)) is top or top - 1; |top| <= 63
    if (top >= 0 ? (d << top) > r : (r << -top) < d) --top;
    quotient q;
    q.e = e_in + top - (P - 1);
    if (QMIN > q.e) q.e = QMIN;
    int s = e_in - q.e;  // the quotient is that of r 2^s by d
    if (0 > s) {
        // Only when r / d >= 2^p: then d 2^-s <= r / 2^(p - 1) < 2^(65 - p).
        q.den = d << -s;
        q.m = r / q.den;
        q.rem = r % q.den;
        return q;
    }
    q.den = d;
    q.m = r / d;
    q.rem = r % d;
    if (q.m == 0) {
        // The leading zero bits of the quotient at once: rem 2^z < d.
        int z = wd - width_of(q.rem) - 1;
        if (z > s) z = s;
        if (z > 0) {
            q.rem <<= z;
            s -= z;
        }
    }
    for (; s > 0; --s) {
        q.rem <<= 1;
        q.m <<= 1;
        if (q.rem >= d) {
            q.rem -= d;
            q.m |= 1;
        }
    }
    return q;
}

// x = (m + rem / den) 2^e rounded to nearest, ties to even: the rounded significand (2^p when it
// carries), and |x - m 2^e| = res / den 2^e, with up when the rounded value is the larger.
struct rounded {
    std::uint64_t m = 0;
    std::uint64_t res = 0;
    bool up = false;
};
constexpr rounded nearest(const quotient& q) noexcept {
    const std::uint64_t rest = q.den - q.rem;
    if (q.rem > rest || (q.rem == rest && (q.m & 1) != 0)) return {q.m + 1, rest, true};
    return {q.m, q.rem, false};
}

// The smallest number of T not below res / den 2^e, for res < den <= 2^63.
template <class T>
constexpr parts above(std::uint64_t res, std::uint64_t den, int e) noexcept {
    using F = format<T>;
    if (res == 0) return {};
    const quotient q = divide<F::p, F::qmin>(res, den, e);
    return {false, q.rem != 0 ? q.m + 1 : q.m, q.e};
}

// num / den, den != 0: the K limbs, the error and whether it is exact, as integers.
template <int K>
struct result {
    parts limbs[K];
    parts error;
    bool exact = false;
};

// With q = num / den:
// - a = RN(q): one rounded division of |num| by |den|, whose remainder gives |q - a|.
// - K = 1: the error is |q - a| rounded up.
// - K = 2: b = RN(q - a), one rounded division of that remainder; the error is |q - a - b| rounded
//   up. The pair (a, b) is normalized, a = RN(a + b), except when |b| is exactly half the gap
//   between a and its neighbor on the side of b and a has an odd significand: a + b is then the
//   midpoint, which rounds to the neighbor, a + 2b. The normalized pair of the same value is then
//   (a + 2b, -b); its leading limb is not RN(q). (Since |q - a| is at most half that gap, which is
//   a number of T, |b| is too; below it, a + b rounds to a; at it, to the even one of a and its
//   neighbor, and neighbors have significands of opposite parities.)
template <class T, int K>
constexpr result<K> compute(long long num, long long den) noexcept {
    using F = format<T>;
    result<K> z;
    const bool neg = (num < 0) != (den < 0);
    const std::uint64_t n = magnitude(num), d = magnitude(den);
    if (n == 0) {
        z.exact = true;
        return z;
    }
    const quotient q0 = divide<F::p, F::qmin>(n, d, 0);
    const rounded a = nearest(q0);
    z.limbs[0] = {neg, a.m, q0.e};
    if constexpr (K == 1) {
        z.error = above<T>(a.res, q0.den, q0.e);
        z.exact = a.res == 0;
    } else {
        if (a.res == 0) {
            z.exact = true;
            return z;
        }
        // |q| - |a| = +-(res / den) 2^e of the first division: negative when a was rounded up.
        const quotient q1 = divide<F::p, F::qmin>(a.res, q0.den, q0.e);
        const rounded b = nearest(q1);
        const bool b_neg = a.up ? !neg : neg;
        z.error = above<T>(b.res, q1.den, q1.e);
        z.exact = b.res == 0;
        // b = 0 would need |q - a| <= 2^(qmin - 1); with these terms |q - a| >= 2^(e - 63) for the e
        // of the first division, at least 2^qmin for float.
        if (b.m == 0) return z;
        z.limbs[1] = {b_neg, b.m, q1.e};
        // An odd a.m is below 2^p, so the gap on either side of a is 2^e of the first division.
        const bool half_gap = (b.m & (b.m - 1)) == 0 && width_of(b.m) - 1 + q1.e == q0.e - 1;
        if (half_gap && (a.m & 1) != 0) {
            z.limbs[0].m = b_neg == neg ? a.m + 1 : a.m - 1;
            z.limbs[1].neg = !b_neg;
        }
    }
    return z;
}

// --- The checker ---------------------------------------------------------------------------------
//
// Whether a result is the one specified, decided with multiplications (by |den| and by powers of
// two), additions, subtractions and comparisons of integers, and no division. It reads the limbs
// and the error back from their bit patterns, and uses nothing of the computation above but format,
// parts, width_of and magnitude.

// An unsigned integer of W 64-bit words, least significant first. over records that a result did
// not fit, which makes the check fail: the integers of the check of a correct result have fewer
// than 118 bits (verify, below), and W is 3.
template <int W>
struct wide {
    std::uint64_t w[W] = {};
    bool over = false;
};
inline constexpr int checker_words = 3;
using wide_t = wide<checker_words>;

constexpr wide_t wide_of(std::uint64_t x) noexcept {
    wide_t a;
    a.w[0] = x;
    return a;
}
constexpr bool is_zero(const wide_t& a) noexcept {
    for (std::uint64_t word : a.w)
        if (word != 0) return false;
    return true;
}
constexpr int width_of(const wide_t& a) noexcept {
    for (int i = checker_words - 1; i >= 0; --i)
        if (a.w[i] != 0) return 64 * i + width_of(a.w[i]);
    return 0;
}
// The sign of a - b.
constexpr int compare(const wide_t& a, const wide_t& b) noexcept {
    for (int i = checker_words - 1; i >= 0; --i)
        if (a.w[i] != b.w[i]) return a.w[i] > b.w[i] ? 1 : -1;
    return 0;
}
// a 2^k for k >= 0, and a / 2^k (truncated) for k < 0.
constexpr wide_t shifted(const wide_t& a, int k) noexcept {
    if (k == 0 || is_zero(a)) return a;
    wide_t r;
    r.over = a.over;
    if (k > 0 && width_of(a) + k > 64 * checker_words) {
        r.over = true;
        return r;
    }
    const int up = k > 0 ? k : -k;
    const int words = up / 64, bits = up % 64;
    for (int i = 0; i < checker_words; ++i) {
        std::uint64_t v = 0;
        if (k > 0) {
            const int from = i - words;
            if (from >= 0) v = a.w[from] << bits;
            if (bits != 0 && from - 1 >= 0) v |= a.w[from - 1] >> (64 - bits);
        } else {
            const int from = i + words;
            if (from < checker_words) v = a.w[from] >> bits;
            if (bits != 0 && from + 1 < checker_words) v |= a.w[from + 1] << (64 - bits);
        }
        r.w[i] = v;
    }
    return r;
}
constexpr wide_t plus(const wide_t& a, const wide_t& b) noexcept {
    wide_t r;
    r.over = a.over || b.over;
    std::uint64_t carry = 0;
    for (int i = 0; i < checker_words; ++i) {
        const std::uint64_t s = a.w[i] + b.w[i];
        const std::uint64_t t = s + carry;
        carry = (s < a.w[i] ? 1u : 0u) + (t < s ? 1u : 0u);
        r.w[i] = t;
    }
    if (carry != 0) r.over = true;
    return r;
}
// a - b, for a >= b.
constexpr wide_t minus(const wide_t& a, const wide_t& b) noexcept {
    wide_t r;
    r.over = a.over || b.over;
    std::uint64_t borrow = 0;
    for (int i = 0; i < checker_words; ++i) {
        const std::uint64_t s = a.w[i] - b.w[i];
        const std::uint64_t t = s - borrow;
        borrow = (a.w[i] < b.w[i] ? 1u : 0u) + (s < borrow ? 1u : 0u);
        r.w[i] = t;
    }
    if (borrow != 0) r.over = true;
    return r;
}
// a d, each product of two words from their 32-bit halves.
constexpr wide_t times(const wide_t& a, std::uint64_t d) noexcept {
    wide_t r;
    r.over = a.over;
    const std::uint64_t d0 = d & 0xffffffffu, d1 = d >> 32;
    std::uint64_t carry = 0;
    for (int i = 0; i < checker_words; ++i) {
        const std::uint64_t a0 = a.w[i] & 0xffffffffu, a1 = a.w[i] >> 32;
        const std::uint64_t p00 = a0 * d0, p01 = a0 * d1, p10 = a1 * d0, p11 = a1 * d1;
        const std::uint64_t mid = (p00 >> 32) + (p01 & 0xffffffffu) + (p10 & 0xffffffffu);
        std::uint64_t lo = (p00 & 0xffffffffu) | (mid << 32);
        std::uint64_t hi = p11 + (p01 >> 32) + (p10 >> 32) + (mid >> 32);
        lo += carry;
        hi += lo < carry ? 1u : 0u;
        r.w[i] = lo;
        carry = hi;
    }
    if (carry != 0) r.over = true;
    return r;
}

// A signed integer: (-1)^neg mag.
struct signed_wide {
    bool neg = false;
    wide_t mag;
};
// a - b.
constexpr signed_wide difference(const signed_wide& a, const signed_wide& b) noexcept {
    if (a.neg != b.neg) return {a.neg, plus(a.mag, b.mag)};
    if (compare(a.mag, b.mag) >= 0) return {a.neg, minus(a.mag, b.mag)};
    return {!a.neg, minus(b.mag, a.mag)};
}

// v 2^e.
struct scaled {
    signed_wide v;
    int e = 0;
};
// y - x d exactly, at the exponent min(e of y, e of x).
constexpr scaled less(const scaled& y, const parts& x, std::uint64_t d) noexcept {
    if (x.m == 0) return y;
    const int e = y.e < x.e ? y.e : x.e;
    const signed_wide a{y.v.neg, shifted(y.v.mag, y.e - e)};
    const signed_wide b{x.neg, shifted(times(wide_of(x.m), d), x.e - e)};
    return {difference(a, b), e};
}
// The sign of a 2^ea - b 2^eb, for a, b >= 0: by their widths first, so that the shift that
// aligns them never overflows.
constexpr int compare_scaled(const wide_t& a, int ea, const wide_t& b, int eb) noexcept {
    const bool za = is_zero(a), zb = is_zero(b);
    if (za || zb) return za && zb ? 0 : (za ? -1 : 1);
    const int la = width_of(a) + ea, lb = width_of(b) + eb;
    if (la != lb) return la < lb ? -1 : 1;
    return ea >= eb ? compare(shifted(a, ea - eb), b) : compare(a, shifted(b, eb - ea));
}

// The parts of x, false if x is not finite.
template <class T>
constexpr bool decode(T x, parts& out) noexcept {
    using F = format<T>;
    using U = typename F::bits;
    const U pattern = std::bit_cast<U>(x);
    constexpr int field = F::width - F::p;  // the bits of the exponent: 11, 8
    const int biased = static_cast<int>((pattern >> (F::p - 1)) & ((U{1} << field) - 1));
    const std::uint64_t trailing = pattern & ((U{1} << (F::p - 1)) - 1);  // the stored significand
    out.neg = (pattern >> (F::width - 1)) != 0;
    if (biased == (1 << field) - 1) return false;
    if (biased == 0) {
        out.m = trailing;
        out.e = F::qmin;
    } else {
        out.m = trailing | (std::uint64_t{1} << (F::p - 1));
        out.e = biased - (F::p - 1) - F::bias;
    }
    return true;
}
// Whether x is a NaN.
template <class T>
constexpr bool is_nan(T x) noexcept {
    parts unused;
    using U = typename format<T>::bits;
    return !decode(x, unused) && (std::bit_cast<U>(x) & ((U{1} << (format<T>::p - 1)) - 1)) != 0;
}
// Whether x is +infinity.
template <class T>
constexpr bool is_plus_infinity(T x) noexcept {
    using U = typename format<T>::bits;
    return std::bit_cast<U>(x) == std::bit_cast<U>(std::numeric_limits<T>::infinity());
}

// The exponent of the gap between x and its neighbor away from zero (away) or toward zero.
template <class T>
constexpr int gap_exponent(const parts& x, bool away) noexcept {
    using F = format<T>;
    if (x.m == 0) return F::qmin;
    if (away || x.m != std::uint64_t{1} << (F::p - 1) || x.e == F::qmin) return x.e;
    return x.e - 1;  // a power of two above the subnormal range: the gap below is half as wide
}
// Whether x = RN(y / d), from r = y - x d: |r| / d below half the gap of x on the side of r, or
// equal to it with an even significand.
template <class T>
constexpr bool rounds_to(const parts& x, const scaled& r, std::uint64_t d) noexcept {
    if (r.v.mag.over) return false;
    if (is_zero(r.v.mag)) return true;
    const bool away = x.m == 0 || r.v.neg == x.neg;
    const int c = compare_scaled(r.v.mag, r.e, wide_of(d), gap_exponent<T>(x, away) - 1);
    return c < 0 || (c == 0 && (x.m & 1) == 0);
}
// Whether (hi, lo) is normalized: hi = RN(hi + lo).
template <class T>
constexpr bool is_normalized_pair(const parts& hi, const parts& lo) noexcept {
    if (lo.m == 0) return true;
    if (hi.m == 0) return false;
    const int c = compare_scaled(wide_of(lo.m), lo.e, wide_of(1), gap_exponent<T>(hi, lo.neg == hi.neg) - 1);
    return c < 0 || (c == 0 && (hi.m & 1) == 0);
}
// The parts of the number a 2^ea of T, false if it is not one.
template <class T>
constexpr bool parts_of(const signed_wide& a, int ea, parts& out) noexcept {
    using F = format<T>;
    if (a.mag.over) return false;
    out.neg = a.neg;
    if (is_zero(a.mag)) {
        out.m = 0;
        out.e = F::qmin;
        return true;
    }
    int e = ea + width_of(a.mag) - F::p;
    if (F::qmin > e) e = F::qmin;
    const wide_t m = shifted(a.mag, ea - e);
    if (e > ea && compare(shifted(m, e - ea), a.mag) != 0) return false;  // bits below 2^e
    if (m.over || width_of(m) > F::p) return false;
    out.m = m.w[0];
    out.e = e;
    return true;
}
// The number before x > 0.
template <class T>
constexpr parts before(const parts& x) noexcept {
    using F = format<T>;
    if (x.m != std::uint64_t{1} << (F::p - 1) || x.e == F::qmin) return {false, x.m - 1, x.e};
    return {false, (std::uint64_t{1} << F::p) - 1, x.e - 1};
}

// Whether limbs, error and exact are what kairn::rational must return for num / den:
// - den = 0: every limb a NaN, error +infinity, exact false;
// - otherwise, with q = num / den: the limbs and the error are finite, the error not negative;
//   K = 1: the limb is RN(q); K = 2: the pair is normalized and its value is RN(q) + RN(q - RN(q)),
//   which is checked for the pair (a, b) = (limb 0, limb 1), and, if that fails, for the pair
//   (limb 0 + 2 limb 1, -limb 1) from which the renormalization makes it; then, with
//   r = |value d - num| for d = |den| (num negated if den < 0): r <= error d, and if error > 0,
//   r > e' d for e' the number of T before error; and exact is r = 0.
// Each residual (q - limb 0, then q - value) is computed once, times d and scaled by a power of two
// so that it is an integer. For a correct result every integer has fewer than 118 bits: with e the
// exponent of the last bit of a limb x (x = m 2^e, m < 2^p), num 2^-e = |q| d 2^-e < 2^(p + 1) d for
// the leading limb, and the residual q - limb 0 after it, scaled to the exponent of limb 1, is below
// 2^p d in the same way; d <= 2^63. A wrong result can make larger ones; over then fails the check.
template <class T, int K>
constexpr bool verify(const T* limbs, T error, bool exact, long long num, long long den) noexcept {
    if (den == 0) {
        bool ok = !exact && is_plus_infinity(error);
        for (int i = 0; i < K; ++i) ok = ok && is_nan(limbs[i]);
        return ok;
    }
    parts l[K], err;
    for (int i = 0; i < K; ++i)
        if (!decode(limbs[i], l[i])) return false;
    if (!decode(error, err) || (err.neg && err.m != 0)) return false;
    const std::uint64_t d = magnitude(den);
    const scaled q{{(num < 0) != (den < 0), wide_of(magnitude(num))}, 0};
    scaled r = less(q, l[0], d);  // q - limb 0, times d
    if constexpr (K == 1) {
        if (!rounds_to<T>(l[0], r, d)) return false;
    } else {
        if (!is_normalized_pair<T>(l[0], l[1])) return false;
        const scaled r0 = r;
        r = less(r0, l[1], d);  // q - value, times d
        bool ok = rounds_to<T>(l[0], r0, d) && rounds_to<T>(l[1], r, d);
        if (!ok && l[1].m != 0) {
            // a = limb 0 + 2 limb 1 and b = -limb 1, whose residual q - a - b is r again.
            const int e = l[0].e < l[1].e + 1 ? l[0].e : l[1].e + 1;
            const signed_wide hi{l[0].neg, shifted(wide_of(l[0].m), l[0].e - e)};
            const signed_wide minus_two_lo{!l[1].neg, shifted(wide_of(l[1].m), l[1].e + 1 - e)};
            parts a;
            const parts b{!l[1].neg, l[1].m, l[1].e};
            ok = parts_of<T>(difference(hi, minus_two_lo), e, a) && rounds_to<T>(a, less(q, a, d), d) &&
                 rounds_to<T>(b, r, d);
        }
        if (!ok) return false;
    }
    const wide_t bound = times(wide_of(err.m), d);
    if (r.v.mag.over || bound.over) return false;
    if (exact != is_zero(r.v.mag)) return false;
    if (compare_scaled(r.v.mag, r.e, bound, err.e) > 0) return false;
    if (err.m != 0) {
        const parts e1 = before<T>(err);
        if (compare_scaled(r.v.mag, r.e, times(wide_of(e1.m), d), e1.e) <= 0) return false;
    }
    return true;
}

// The value of X from its limbs, written directly: they come from bit patterns, not from a
// product that the compiler could fuse, and they form a canonical pair.
template <class X, class T>
constexpr X number_of(T a, [[maybe_unused]] T b) noexcept {
    if constexpr (limb<X>) {
        return a;
    } else {
        X x;
        x.limb[0] = a;
        if constexpr (traits<X>::limbs == 2) x.limb[1] = b;
        return x;
    }
}
template <class X, class T>
constexpr T limb_at(const X& x, [[maybe_unused]] int i) noexcept {
    if constexpr (limb<X>) {
        return x;
    } else {
        return x.limb[i];
    }
}

}  // namespace fraction
}  // namespace detail

/// Whether c is exactly what kairn::rational<X>(num, den) must return: every limb, the error and
/// the flag, as the reference page of rational states them.
///
/// Decided in integer arithmetic, with multiplications (by |den| and by powers of two), additions
/// and comparisons only, from the bit patterns of the limbs and of the error: no division, no
/// floating-point operation, and nothing of the computation of kairn::rational but the description
/// of the format (its precision and exponents) and the magnitude of a term. For two limbs it
/// checks that the pair is normalized and that its value is RN(q) + RN(q - RN(q)) for q =
/// num / den, then that error is the smallest number of the limb type that is at least
/// |value - q|, and that exact says whether value is q. kairn::rational calls it on every result
/// computed in a constant expression (KAIRN_RATIONAL_CHECK) and, when KAIRN_CHECKS is 1, on every
/// result computed at run time. Usable in constant evaluation.
template <class X>
    requires detail::number<X>
constexpr bool is_rational_result(const Constant<X>& c, long long num, long long den) noexcept {
    using T = typename traits<X>::limb_type;
    constexpr int K = traits<X>::limbs;
    T limbs[K] = {};
    for (int i = 0; i < K; ++i) limbs[i] = detail::fraction::limb_at<X, T>(c.value, i);
    return detail::fraction::verify<T, K>(limbs, c.error, c.exact, num, den);
}

namespace detail::fraction {

// kairn::rational, below.
template <class X>
constexpr Constant<X> make(long long num, long long den) noexcept {
    using T = typename traits<X>::limb_type;
    constexpr int K = traits<X>::limbs;
    Constant<X> c;
    if (den == 0) {
        if (__builtin_is_constant_evaluated()) rational_denominator_is_zero();
        constexpr T nan = std::numeric_limits<T>::quiet_NaN();
        c.value = number_of<X, T>(nan, nan);
        c.error = std::numeric_limits<T>::infinity();
        return c;
    }
    const result<K> r = compute<T, K>(num, den);
    if constexpr (K == 1) {
        c.value = number_of<X, T>(limb_of<T>(r.limbs[0]), limb_of<T>(parts{}));
    } else {
        c.value = number_of<X, T>(limb_of<T>(r.limbs[0]), limb_of<T>(r.limbs[1]));
    }
    c.error = limb_of<T>(r.error);
    c.exact = r.exact;
    if (__builtin_is_constant_evaluated()) {
#if KAIRN_RATIONAL_CHECK
        if (!is_rational_result(c, num, den)) rational_result_fails_its_specification();
#endif
    } else {
#if KAIRN_CHECKS
        if (!is_rational_result(c, num, den))
            fail("rational", "the result does not satisfy its specification (kairn::is_rational_result)");
#endif
    }
    return c;
}

}  // namespace detail::fraction

/// num / den as a number of type X (float, double, Expansion<T, 1> or Expansion<T, 2>), with the
/// error it makes and whether it is exact; usable in constant expressions, where it is how a
/// program writes a constant such as 1/3 or 1/10 in one or two limbs, and at run time, where until
/// Kairn has a division it is how a program divides by an integer.
///
/// With q = num / den, for den != 0:
/// - one limb: value is q rounded to nearest, ties to even, with gradual underflow;
/// - two limbs: value is the normalized pair whose value is RN(q) + RN(q - RN(q)); there is exactly
///   one, and its leading limb is RN(q) except near a tie, where the two roundings sum to the
///   midpoint between RN(q) and its neighbor;
/// - error is the smallest number of the limb type that is at least |value - q|, and exact is true
///   exactly when value is q (error is zero). So |value - q| <= u/(1 + u) |q| for one limb and
///   <= u^2 |q| for two, u = 2^-p, with no term for underflow: |q| is zero or at least 2^-63.
///
/// Any two values of long long, -2^63 included. den = 0 in a constant expression does not compile:
/// the compiler's message names detail::rational_denominator_is_zero. At run time it gives the
/// canonical NaN (every limb a NaN), error +infinity and exact false.
///
/// Computed with integer operations only (one division with remainder per limb, a rounding up for
/// the error, all within 64-bit words), and the limbs assembled with std::bit_cast: the same bits at
/// compile time and at run time, under every rounding mode, and not checked against the
/// environment in a debug build. Specified exactly; tested for equality with an independent oracle;
/// not machine-checked: this is integer code written by hand, not a generated kernel. Every result
/// computed in a constant expression is checked against this whole statement by
/// kairn::is_rational_result, a check of multiplications and comparisons that shares with the
/// computation only the description of the format, and a result that failed it would not compile
/// (KAIRN_RATIONAL_CHECK); at run time the same check is made when KAIRN_CHECKS is 1.
template <class X>
    requires detail::number<X>
constexpr Constant<X> rational(long long num, long long den) noexcept {
    return detail::fraction::make<X>(num, den);
}

/// n as a number of type X: kairn::rational<X>(n, 1). Exact when n is a number of X: every n with
/// |n| <= 2^53 for double and 2^24 for float, and every n for Expansion<double, 2>; otherwise
/// rounded as kairn::rational says, with its error.
template <class X>
    requires detail::number<X>
constexpr Constant<X> integer(long long n) noexcept {
    return rational<X>(n, 1);
}

}  // namespace kairn
KAIRN_GEN_POP_WARNINGS
