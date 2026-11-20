// api.rational.constexpr: kairn::rational and kairn::integer (include/kairn/rational.hpp).
//
// - Constants: static_asserts of the limbs, the error and the flag of two dozen fractions and six
//   integers, for float and double, one and two limbs. The expected values were computed from the
//   specification with exact rationals (Python's fractions), by code that shares nothing with the
//   header: among them 1/3, 1/10, -1/3, 2^53 + 1 and 2^24 + 1 (ties for one limb), 1/s for large
//   s, -2^63 as either term, two fractions near the midpoint of two numbers of T (built as the
//   design page describes), where the normalized pair's leading limb is not RN(q), and two whose
//   second float limb and error are subnormal. Each is compared bit for bit.
// - The checker: kairn::is_rational_result accepts every result above and refuses each one changed
//   by one unit: a limb or the error moved to the next number of T up or down, the flag flipped.
// - What does not compile: rational of a type that is not a number of Kairn; den = 0 in a constant
//   expression is tested by api.reject.rational.denominator_zero.
// - Run time equals compile time: each fraction of a corpus, computed in a constant expression of
//   its own and at run time from operands the compiler cannot see, under each of the four rounding
//   modes, gives the same bits, which is_rational_result accepts; den = 0 at run time gives the
//   canonical NaN, +infinity and false.
//
// Built with the build's flags and with each flag set (tests/api/flags/): api.rational.constexpr,
// api.flags.debug.rational, full.api.flags.SET.rational. In the debug build KAIRN_CHECKS is 1, and
// kairn::rational, which does not round, must not check the environment: run under a directed
// rounding mode, it must not stop the program.
#include <kairn/kairn.hpp>

#include <array>
#include <bit>
#include <cfenv>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <type_traits>
#include <utility>

namespace {

using D1 = kairn::Expansion<double, 1>;
using D2 = kairn::Expansion<double, 2>;
using F1 = kairn::Expansion<float, 1>;
using F2 = kairn::Expansion<float, 2>;
constexpr long long min64 = std::numeric_limits<long long>::min();

template <class T>
using bits_t = std::conditional_t<sizeof(T) == 8, std::uint64_t, std::uint32_t>;
template <class T>
constexpr bits_t<T> bits(T x) {
    return std::bit_cast<bits_t<T>>(x);
}
template <class X>
using limb_t = typename kairn::traits<X>::limb_type;
template <class X>
constexpr int limbs_of = kairn::traits<X>::limbs;
// Limb i of a number: a float or a double is its own limb.
template <class X>
constexpr limb_t<X> limb(const X& x, [[maybe_unused]] int i) {
    if constexpr (std::is_floating_point_v<X>) {
        return x;
    } else {
        return x.limb[i];
    }
}

// Whether c has these limbs, this error and this flag, bit for bit.
template <class X>
constexpr bool is(const kairn::Constant<X>& c, std::array<limb_t<X>, limbs_of<X>> limbs, limb_t<X> error,
                  bool exact) {
    bool ok = bits(c.error) == bits(error) && c.exact == exact;
    for (int i = 0; i < limbs_of<X>; ++i) ok = ok && bits(limb(c.value, i)) == bits(limbs[std::size_t(i)]);
    return ok;
}

// --- Constants, computed from the specification with exact rationals ----------------------------
// double
// 1/3
static_assert(is<D1>(kairn::rational<D1>(1, 3), {0x1.5555555555555p-2}, 0x1.5555555555556p-56, false));
static_assert(is<D2>(kairn::rational<D2>(1, 3), {0x1.5555555555555p-2, 0x1.5555555555555p-56}, 0x1.5555555555556p-110, false));
// -1/3
static_assert(is<D1>(kairn::rational<D1>(-1, 3), {-0x1.5555555555555p-2}, 0x1.5555555555556p-56, false));
static_assert(is<D2>(kairn::rational<D2>(-1, 3), {-0x1.5555555555555p-2, -0x1.5555555555555p-56}, 0x1.5555555555556p-110, false));
// 1/10
static_assert(is<D1>(kairn::rational<D1>(1, 10), {0x1.999999999999ap-4}, 0x1.999999999999ap-58, false));
static_assert(is<D2>(kairn::rational<D2>(1, 10), {0x1.999999999999ap-4, -0x1.999999999999ap-58}, 0x1.999999999999ap-112, false));
// 2/3
static_assert(is<D1>(kairn::rational<D1>(2, 3), {0x1.5555555555555p-1}, 0x1.5555555555556p-55, false));
static_assert(is<D2>(kairn::rational<D2>(2, 3), {0x1.5555555555555p-1, 0x1.5555555555555p-55}, 0x1.5555555555556p-109, false));
// -7/10
static_assert(is<D1>(kairn::rational<D1>(-7, 10), {-0x1.6666666666666p-1}, 0x1.999999999999ap-55, false));
static_assert(is<D2>(kairn::rational<D2>(-7, 10), {-0x1.6666666666666p-1, -0x1.999999999999ap-55}, 0x1.999999999999ap-109, false));
// zero
static_assert(is<D1>(kairn::rational<D1>(0, 5), {0.0}, 0.0, true));
static_assert(is<D2>(kairn::rational<D2>(0, 5), {0.0, 0.0}, 0.0, true));
// exact
static_assert(is<D1>(kairn::rational<D1>(6, -3), {-0x1p+1}, 0.0, true));
static_assert(is<D2>(kairn::rational<D2>(6, -3), {-0x1p+1, 0.0}, 0.0, true));
// 2^53 + 1: a tie for one double limb
static_assert(is<D1>(kairn::rational<D1>(9007199254740993LL, 1), {0x1p+53}, 0x1p+0, false));
static_assert(is<D2>(kairn::rational<D2>(9007199254740993LL, 1), {0x1p+53, 0x1p+0}, 0.0, true));
// 2^24 + 1: a tie for one float limb
static_assert(is<D1>(kairn::rational<D1>(16777217, 1), {0x1.000001p+24}, 0.0, true));
static_assert(is<D2>(kairn::rational<D2>(16777217, 1), {0x1.000001p+24, 0.0}, 0.0, true));
// 1 / (2^53 - 1)
static_assert(is<D1>(kairn::rational<D1>(1, 9007199254740991LL), {0x1.0000000000001p-53}, 0x1.fffffffffffffp-107, false));
static_assert(is<D2>(kairn::rational<D2>(1, 9007199254740991LL), {0x1.0000000000001p-53, -0x1.fffffffffffffp-107}, 0x1.0000000000001p-212, false));
// 1 / (2^63 - 1)
static_assert(is<D1>(kairn::rational<D1>(1, 9223372036854775807LL), {0x1p-63}, 0x1.0000000000001p-126, false));
static_assert(is<D2>(kairn::rational<D2>(1, 9223372036854775807LL), {0x1p-63, 0x1p-126}, 0x1.0000000000001p-189, false));
// 1 / 1000000007
static_assert(is<D1>(kairn::rational<D1>(1, 1000000007), {0x1.12e0be6225452p-30}, 0x1.b840c1910570ep-89, false));
static_assert(is<D2>(kairn::rational<D2>(1, 1000000007), {0x1.12e0be6225452p-30, -0x1.b840c1910570dp-89}, 0x1.0275e49ddaca2p-143, false));
// -1 / 999999999999999989
static_assert(is<D1>(kairn::rational<D1>(-1, 999999999999999989LL), {-0x1.2725dd1d243acp-60}, 0x1.41e613d22c8f3p-114, false));
static_assert(is<D2>(kairn::rational<D2>(-1, 999999999999999989LL), {-0x1.2725dd1d243acp-60, 0x1.41e613d22c8f2p-114}, 0x1.c4a03d4d452f6p-169, false));
// -2^63 / 1
static_assert(is<D1>(kairn::rational<D1>(min64, 1), {-0x1p+63}, 0.0, true));
static_assert(is<D2>(kairn::rational<D2>(min64, 1), {-0x1p+63, 0.0}, 0.0, true));
// -2^63 / 3
static_assert(is<D1>(kairn::rational<D1>(min64, 3), {-0x1.5555555555555p+61}, 0x1.5555555555556p+7, false));
static_assert(is<D2>(kairn::rational<D2>(min64, 3), {-0x1.5555555555555p+61, -0x1.5555555555555p+7}, 0x1.5555555555556p-47, false));
// -2^63 / -2^63
static_assert(is<D1>(kairn::rational<D1>(min64, min64), {0x1p+0}, 0.0, true));
static_assert(is<D2>(kairn::rational<D2>(min64, min64), {0x1p+0, 0.0}, 0.0, true));
// 1 / -2^63
static_assert(is<D1>(kairn::rational<D1>(1, min64), {-0x1p-63}, 0.0, true));
static_assert(is<D2>(kairn::rational<D2>(1, min64), {-0x1p-63, 0.0}, 0.0, true));
// (2^63 - 1) / -2^63
static_assert(is<D1>(kairn::rational<D1>(9223372036854775807LL, min64), {-0x1p+0}, 0x1p-63, false));
static_assert(is<D2>(kairn::rational<D2>(9223372036854775807LL, min64), {-0x1p+0, 0x1p-63}, 0.0, true));
// -2^63 / (2^63 - 1)
static_assert(is<D1>(kairn::rational<D1>(min64, 9223372036854775807LL), {-0x1p+0}, 0x1.0000000000001p-63, false));
static_assert(is<D2>(kairn::rational<D2>(min64, 9223372036854775807LL), {-0x1p+0, -0x1p-63}, 0x1.0000000000001p-126, false));
// near a tie of double limbs
static_assert(is<D1>(kairn::rational<D1>(760870173599572325LL, 1255282706658693927LL), {0x1.365743570964bp-1}, 0x1p-54, false));
// k = 2: the leading limb is not RN(q)
static_assert(is<D2>(kairn::rational<D2>(760870173599572325LL, 1255282706658693927LL), {0x1.365743570964cp-1, -0x1p-54}, 0x1.d63fd1edd5695p-115, false));
// the same, negated
static_assert(is<D1>(kairn::rational<D1>(-760870173599572325LL, 1255282706658693927LL), {-0x1.365743570964bp-1}, 0x1p-54, false));
// k = 2: the leading limb is not RN(q)
static_assert(is<D2>(kairn::rational<D2>(-760870173599572325LL, 1255282706658693927LL), {-0x1.365743570964cp-1, 0x1p-54}, 0x1.d63fd1edd5695p-115, false));
// near a tie of float limbs
static_assert(is<D1>(kairn::rational<D1>(2556122234497469017LL, 3174268604348619699LL), {0x1.9c4b7bp-1}, 0x1.73ecf158292bep-87, false));
static_assert(is<D2>(kairn::rational<D2>(2556122234497469017LL, 3174268604348619699LL), {0x1.9c4b7bp-1, -0x1.73ecf158292bdp-87}, 0x1.9bd9af440b004p-142, false));
// q - RN(q) below the normal range of float
static_assert(is<D1>(kairn::rational<D1>(3709201, 6725971402761034045LL), {0x1.3673d6p-41}, 0x1.5f0dfaaa54d25p-127, false));
static_assert(is<D2>(kairn::rational<D2>(3709201, 6725971402761034045LL), {0x1.3673d6p-41, 0x1.5f0dfaaa54d24p-127}, 0x1.9b2041ee5a0acp-182, false));
// q - RN(q) below the normal range of float
static_assert(is<D1>(kairn::rational<D1>(3991677, 7115939552801341003LL), {0x1.3bc93ap-41}, 0x1.4bd0eb4bbdbc1p-127, false));
static_assert(is<D2>(kairn::rational<D2>(3991677, 7115939552801341003LL), {0x1.3bc93ap-41, 0x1.4bd0eb4bbdbc1p-127}, 0x1.eb0ccf70c26cep-181, false));
// integer(n), double
static_assert(is<D1>(kairn::integer<D1>(9007199254740993LL), {0x1p+53}, 0x1p+0, false));
static_assert(is<D2>(kairn::integer<D2>(9007199254740993LL), {0x1p+53, 0x1p+0}, 0.0, true));
static_assert(is<D1>(kairn::integer<D1>(-9007199254740995LL), {-0x1.0000000000002p+53}, 0x1p+0, false));
static_assert(is<D2>(kairn::integer<D2>(-9007199254740995LL), {-0x1.0000000000002p+53, 0x1p+0}, 0.0, true));
static_assert(is<D1>(kairn::integer<D1>(9223372036854775807LL), {0x1p+63}, 0x1p+0, false));
static_assert(is<D2>(kairn::integer<D2>(9223372036854775807LL), {0x1p+63, -0x1p+0}, 0.0, true));
static_assert(is<D1>(kairn::integer<D1>(min64), {-0x1p+63}, 0.0, true));
static_assert(is<D2>(kairn::integer<D2>(min64), {-0x1p+63, 0.0}, 0.0, true));
static_assert(is<D1>(kairn::integer<D1>(16777217), {0x1.000001p+24}, 0.0, true));
static_assert(is<D2>(kairn::integer<D2>(16777217), {0x1.000001p+24, 0.0}, 0.0, true));
static_assert(is<D1>(kairn::integer<D1>(50331651), {0x1.8000018p+25}, 0.0, true));
static_assert(is<D2>(kairn::integer<D2>(50331651), {0x1.8000018p+25, 0.0}, 0.0, true));
// float
// 1/3
static_assert(is<F1>(kairn::rational<F1>(1, 3), {0x1.555556p-2f}, 0x1.555556p-27f, false));
static_assert(is<F2>(kairn::rational<F2>(1, 3), {0x1.555556p-2f, -0x1.555556p-27f}, 0x1.555556p-52f, false));
// -1/3
static_assert(is<F1>(kairn::rational<F1>(-1, 3), {-0x1.555556p-2f}, 0x1.555556p-27f, false));
static_assert(is<F2>(kairn::rational<F2>(-1, 3), {-0x1.555556p-2f, 0x1.555556p-27f}, 0x1.555556p-52f, false));
// 1/10
static_assert(is<F1>(kairn::rational<F1>(1, 10), {0x1.99999ap-4f}, 0x1.99999ap-30f, false));
static_assert(is<F2>(kairn::rational<F2>(1, 10), {0x1.99999ap-4f, -0x1.99999ap-30f}, 0x1.99999ap-56f, false));
// 2/3
static_assert(is<F1>(kairn::rational<F1>(2, 3), {0x1.555556p-1f}, 0x1.555556p-26f, false));
static_assert(is<F2>(kairn::rational<F2>(2, 3), {0x1.555556p-1f, -0x1.555556p-26f}, 0x1.555556p-51f, false));
// -7/10
static_assert(is<F1>(kairn::rational<F1>(-7, 10), {-0x1.666666p-1f}, 0x1.99999ap-27f, false));
static_assert(is<F2>(kairn::rational<F2>(-7, 10), {-0x1.666666p-1f, -0x1.99999ap-27f}, 0x1.99999ap-53f, false));
// zero
static_assert(is<F1>(kairn::rational<F1>(0, 5), {0.0f}, 0.0f, true));
static_assert(is<F2>(kairn::rational<F2>(0, 5), {0.0f, 0.0f}, 0.0f, true));
// exact
static_assert(is<F1>(kairn::rational<F1>(6, -3), {-0x1p+1f}, 0.0f, true));
static_assert(is<F2>(kairn::rational<F2>(6, -3), {-0x1p+1f, 0.0f}, 0.0f, true));
// 2^53 + 1: a tie for one double limb
static_assert(is<F1>(kairn::rational<F1>(9007199254740993LL, 1), {0x1p+53f}, 0x1p+0f, false));
static_assert(is<F2>(kairn::rational<F2>(9007199254740993LL, 1), {0x1p+53f, 0x1p+0f}, 0.0f, true));
// 2^24 + 1: a tie for one float limb
static_assert(is<F1>(kairn::rational<F1>(16777217, 1), {0x1p+24f}, 0x1p+0f, false));
static_assert(is<F2>(kairn::rational<F2>(16777217, 1), {0x1p+24f, 0x1p+0f}, 0.0f, true));
// 1 / (2^53 - 1)
static_assert(is<F1>(kairn::rational<F1>(1, 9007199254740991LL), {0x1p-53f}, 0x1.000002p-106f, false));
// k = 2: the error is subnormal
static_assert(is<F2>(kairn::rational<F2>(1, 9007199254740991LL), {0x1p-53f, 0x1p-106f}, 0x1p-149f, false));
// 1 / (2^63 - 1)
static_assert(is<F1>(kairn::rational<F1>(1, 9223372036854775807LL), {0x1p-63f}, 0x1.000002p-126f, false));
// k = 2: the error is subnormal
static_assert(is<F2>(kairn::rational<F2>(1, 9223372036854775807LL), {0x1p-63f, 0x1p-126f}, 0x1p-149f, false));
// 1 / 1000000007
static_assert(is<F1>(kairn::rational<F1>(1, 1000000007), {0x1.12e0bep-30f}, 0x1.889516p-56f, false));
static_assert(is<F2>(kairn::rational<F2>(1, 1000000007), {0x1.12e0bep-30f, 0x1.889514p-56f}, 0x1.fc8f8p-82f, false));
// -1 / 999999999999999989
static_assert(is<F1>(kairn::rational<F1>(-1, 999999999999999989LL), {-0x1.2725dep-60f}, 0x1.c5b78cp-85f, false));
static_assert(is<F2>(kairn::rational<F2>(-1, 999999999999999989LL), {-0x1.2725dep-60f, 0x1.c5b78ap-85f}, 0x1.141e62p-110f, false));
// -2^63 / 1
static_assert(is<F1>(kairn::rational<F1>(min64, 1), {-0x1p+63f}, 0.0f, true));
static_assert(is<F2>(kairn::rational<F2>(min64, 1), {-0x1p+63f, 0.0f}, 0.0f, true));
// -2^63 / 3
static_assert(is<F1>(kairn::rational<F1>(min64, 3), {-0x1.555556p+61f}, 0x1.555556p+36f, false));
static_assert(is<F2>(kairn::rational<F2>(min64, 3), {-0x1.555556p+61f, 0x1.555556p+36f}, 0x1.555556p+11f, false));
// -2^63 / -2^63
static_assert(is<F1>(kairn::rational<F1>(min64, min64), {0x1p+0f}, 0.0f, true));
static_assert(is<F2>(kairn::rational<F2>(min64, min64), {0x1p+0f, 0.0f}, 0.0f, true));
// 1 / -2^63
static_assert(is<F1>(kairn::rational<F1>(1, min64), {-0x1p-63f}, 0.0f, true));
static_assert(is<F2>(kairn::rational<F2>(1, min64), {-0x1p-63f, 0.0f}, 0.0f, true));
// (2^63 - 1) / -2^63
static_assert(is<F1>(kairn::rational<F1>(9223372036854775807LL, min64), {-0x1p+0f}, 0x1p-63f, false));
static_assert(is<F2>(kairn::rational<F2>(9223372036854775807LL, min64), {-0x1p+0f, 0x1p-63f}, 0.0f, true));
// -2^63 / (2^63 - 1)
static_assert(is<F1>(kairn::rational<F1>(min64, 9223372036854775807LL), {-0x1p+0f}, 0x1.000002p-63f, false));
static_assert(is<F2>(kairn::rational<F2>(min64, 9223372036854775807LL), {-0x1p+0f, -0x1p-63f}, 0x1.000002p-126f, false));
// near a tie of double limbs
static_assert(is<F1>(kairn::rational<F1>(760870173599572325LL, 1255282706658693927LL), {0x1.365744p-1f}, 0x1.51ed38p-26f, false));
static_assert(is<F2>(kairn::rational<F2>(760870173599572325LL, 1255282706658693927LL), {0x1.365744p-1f, -0x1.51ed36p-26f}, 0x1.200002p-51f, false));
// the same, negated
static_assert(is<F1>(kairn::rational<F1>(-760870173599572325LL, 1255282706658693927LL), {-0x1.365744p-1f}, 0x1.51ed38p-26f, false));
static_assert(is<F2>(kairn::rational<F2>(-760870173599572325LL, 1255282706658693927LL), {-0x1.365744p-1f, 0x1.51ed36p-26f}, 0x1.200002p-51f, false));
// near a tie of float limbs
static_assert(is<F1>(kairn::rational<F1>(2556122234497469017LL, 3174268604348619699LL), {0x1.9c4b7ap-1f}, 0x1p-25f, false));
// k = 2: the leading limb is not RN(q)
static_assert(is<F2>(kairn::rational<F2>(2556122234497469017LL, 3174268604348619699LL), {0x1.9c4b7cp-1f, -0x1p-25f}, 0x1.73ecf2p-87f, false));
// q - RN(q) below the normal range of float
static_assert(is<F1>(kairn::rational<F1>(3709201, 6725971402761034045LL), {0x1.3673d6p-41f}, 0x1.5f0dfcp-127f, false));
// k = 2: the second limb is subnormal; the error is subnormal
static_assert(is<F2>(kairn::rational<F2>(3709201, 6725971402761034045LL), {0x1.3673d6p-41f, 0x1.5f0dfcp-127f}, 0x1p-149f, false));
// q - RN(q) below the normal range of float
static_assert(is<F1>(kairn::rational<F1>(3991677, 7115939552801341003LL), {0x1.3bc93ap-41f}, 0x1.4bd0ecp-127f, false));
// k = 2: the second limb is subnormal; the error is subnormal
static_assert(is<F2>(kairn::rational<F2>(3991677, 7115939552801341003LL), {0x1.3bc93ap-41f, 0x1.4bd0ecp-127f}, 0x1p-149f, false));
// integer(n), float
static_assert(is<F1>(kairn::integer<F1>(9007199254740993LL), {0x1p+53f}, 0x1p+0f, false));
static_assert(is<F2>(kairn::integer<F2>(9007199254740993LL), {0x1p+53f, 0x1p+0f}, 0.0f, true));
static_assert(is<F1>(kairn::integer<F1>(-9007199254740995LL), {-0x1p+53f}, 0x1.8p+1f, false));
static_assert(is<F2>(kairn::integer<F2>(-9007199254740995LL), {-0x1p+53f, -0x1.8p+1f}, 0.0f, true));
static_assert(is<F1>(kairn::integer<F1>(9223372036854775807LL), {0x1p+63f}, 0x1p+0f, false));
static_assert(is<F2>(kairn::integer<F2>(9223372036854775807LL), {0x1p+63f, -0x1p+0f}, 0.0f, true));
static_assert(is<F1>(kairn::integer<F1>(min64), {-0x1p+63f}, 0.0f, true));
static_assert(is<F2>(kairn::integer<F2>(min64), {-0x1p+63f, 0.0f}, 0.0f, true));
static_assert(is<F1>(kairn::integer<F1>(16777217), {0x1p+24f}, 0x1p+0f, false));
static_assert(is<F2>(kairn::integer<F2>(16777217), {0x1p+24f, 0x1p+0f}, 0.0f, true));
static_assert(is<F1>(kairn::integer<F1>(50331651), {0x1.800002p+25f}, 0x1p+0f, false));
static_assert(is<F2>(kairn::integer<F2>(50331651), {0x1.800002p+25f, -0x1p+0f}, 0.0f, true));

// --- The checker refuses every result changed by one unit ----------------------------------------
// Each change of each result is a constant of its own, so that no constant expression evaluates
// more than one result and two checks: compilers limit the steps of one evaluation (MSVC's
// /constexpr:steps), and the check takes a few thousand of Clang's.
constexpr long long changed[][2] = {{1, 3}, {-1, 3}, {1, 10}, {0, 5}, {6, -3}, {9007199254740993LL, 1},
                                    {16777217, 1}, {1, 9223372036854775807LL}, {min64, 3}, {min64, min64},
                                    {1, min64}, {760870173599572325LL, 1255282706658693927LL},
                                    {2556122234497469017LL, 3174268604348619699LL},
                                    {3709201, 6725971402761034045LL}};
constexpr std::size_t n_changed = sizeof changed / sizeof changed[0];
// The changes of a result of K limbs: 0, none (the result must be accepted); 1, the flag flipped;
// then for each limb and the error, the next number of T down and up.
template <class X>
constexpr int changes = 2 + 2 * (limbs_of<X> + 1);
// Whether the check accepts the result of fraction f, if change is 0, and refuses it changed so
// otherwise.
template <class X>
constexpr bool checked(std::size_t f, int change) {
    const long long num = changed[f][0], den = changed[f][1];
    kairn::Constant<X> c = kairn::rational<X>(num, den);
    if (change == 0) return kairn::is_rational_result(c, num, den);
    if (change == 1) {
        c.exact = !c.exact;
    } else {
        const int i = (change - 2) / 2;
        const bool up = (change - 2) % 2 == 1;
        auto& x = i < limbs_of<X> ? c.value.limb[i] : c.error;
        if (i == limbs_of<X> && !up && bits(x) == 0) return true;  // no error below 0
        // The next number of T up or down: the kernels next_up and next_down (Milestone 2).
        auto stepped = x;
        if (up) {
            kairn::gen::next_up(x, stepped);
        } else {
            kairn::gen::next_down(x, stepped);
        }
        x = stepped;
    }
    return !kairn::is_rational_result(c, num, den);
}
template <class X, std::size_t I>
constexpr bool checked_at = checked<X>(I / changes<X>, int(I % changes<X>));
template <class X, std::size_t... I>
constexpr bool all_checked(std::index_sequence<I...>) {
    return (checked_at<X, I> && ...);
}
static_assert(all_checked<D1>(std::make_index_sequence<n_changed * changes<D1>>{}));
static_assert(all_checked<D2>(std::make_index_sequence<n_changed * changes<D2>>{}));
static_assert(all_checked<F1>(std::make_index_sequence<n_changed * changes<F1>>{}));
static_assert(all_checked<F2>(std::make_index_sequence<n_changed * changes<F2>>{}));
// A pair with the right value that is not normalized: (a, b) of the near tie, not (a + 2b, -b).
static_assert(!kairn::is_rational_result(
    kairn::Constant<D2>{[] {
                            D2 x;
                            x.limb[0] = 0x1.365743570964bp-1;
                            x.limb[1] = 0x1p-54;
                            return x;
                        }(),
                        0x1.d63fd1edd5695p-115, false},
    760870173599572325LL, 1255282706658693927LL));

// --- Types --------------------------------------------------------------------------------------
template <class X>
concept has_rational = requires { kairn::rational<X>(1, 3); };
static_assert(has_rational<double> && has_rational<float> && has_rational<D1> && has_rational<F2>);
static_assert(!has_rational<int> && !has_rational<long double> && !has_rational<kairn::Ball<double, 2>>);
static_assert(std::is_same_v<decltype(kairn::Constant<D2>::error), double>);
static_assert(std::is_same_v<decltype(kairn::Constant<F1>::error), float>);
static_assert(std::is_same_v<decltype(kairn::rational<D2>(1, 3)), kairn::Constant<D2>>);
static_assert(kairn::rational<double>(1, 4).value == 0.25 && kairn::rational<double>(1, 4).exact);

// --- Run time equals compile time ----------------------------------------------------------------
struct Fraction {
    long long num, den;
};
constexpr Fraction corpus[] = {
    {1, 3}, {-1, 3},
    {1, 10}, {2, 3},
    {-7, 10}, {0, 5},
    {6, -3}, {9007199254740993LL, 1},
    {16777217, 1}, {1, 9007199254740991LL},
    {1, 9223372036854775807LL}, {1, 1000000007},
    {-1, 999999999999999989LL}, {min64, 1},
    {min64, 3}, {min64, min64},
    {1, min64}, {9223372036854775807LL, min64},
    {min64, 9223372036854775807LL}, {760870173599572325LL, 1255282706658693927LL},
    {-760870173599572325LL, 1255282706658693927LL}, {2556122234497469017LL, 3174268604348619699LL},
    {3709201, 6725971402761034045LL}, {3991677, 7115939552801341003LL},
    {-862280060757637446LL, 3993497635343103480LL}, {7281778456343657357LL, 4350864004918906512LL},
    {8050958075009231843LL, 2868443735580739439LL}, {4278153988157526564LL, -5534788108138765494LL},
    {-2861148947977069885LL, -3576668619877126060LL}, {-6531619639630994500LL, 8779549076251501745LL},
    {47417086816256638LL, 3936585805224154358LL}, {-8497077305356927975LL, -3992509401787200844LL},
    {-2660038147159716468LL, 1365473538643963655LL}, {-1044520759310650108LL, -4967695261527668735LL},
    {-7958623462356242113LL, -8013114349626227599LL}, {-4882808922567085269LL, -8968046448237592607LL},
    {2760982949130793962LL, -6038819192433366385LL}, {1062631002049625185LL, 3225625648255280195LL},
    {8029822571827587941LL, 8630498093163500405LL}, {-3015174669415186714LL, 42900375987541775LL},
    {1348583610930558300LL, -2831070788548562132LL}, {4878883284533584105LL, 4543113298446707213LL},
    {-5573305497119639126LL, -7824462157786775127LL}, {7526665243868108482LL, -66484281634516678LL},
    {-8658808424256693719LL, 5068572307495097049LL}, {-8806860286730182705LL, 2719127625402470805LL},
    {-1034557570898605101LL, 1638728709923729355LL}, {-4116265549309863932LL, 2267659230732506545LL},
    {-3037748178845325997LL, 8916092195545114682LL}, {6736085454704618608LL, 2685359850983870763LL},
    {1976951885205359469LL, -6172022057667335995LL}, {-5152152487467411492LL, 6783152862094555574LL},
    {-1776566165692599913LL, 4656396296409044647LL}, {-6459883916144430236LL, -8089499760024577475LL},
    {-77, -75}, {59, 41},
    {-91, 68}, {-40, 26},
    {-39, -13}, {-3, 82},
    {81, 69}, {55, 99},
    {27, -56}, {72, 38},
    {6, 11}, {-58, 7},
    {-92, 32}, {-41, -89},
    {65, 86}, {-35, 97},
    {-41, -13}, {-47, -48},
    {2, 48}, {-17, -37},
    {1, 1521506917257172951LL}, {1, 8621748307032423819LL},
    {-1, 388227713677258901LL}, {-1, 2657657578045014400LL},
    {-1, 6186267937297236498LL}, {1, 1258762310731744672LL},
    {-1, 4783431756399929391LL}, {1, 3498541893867582044LL},
    {1, 4083645193929240006LL}, {1, 6384155211612483127LL},
    {-6344745223813394804LL, 8427843477865901647LL}, {4689648073433325496LL, 7133267971364536847LL},
    {-4063030756851189223LL, 4478905162006096123LL}, {122103798352167548LL, 231949817254824895LL},
    {8455535810561380631LL, 8610488197430085247LL}, {-5866900151125826261LL, 8123055227332329911LL},
    {4207881791720744178LL, 8396608811715132941LL}, {5740561893677141207LL, 6085469554262144739LL},
    {-2690049746043769034LL, 5077164879093136521LL}, {-1978994324019494755LL, 3498579548421119379LL},
    {5105546490355087859LL, 6435714724088223747LL}, {-1944142246289092690LL, 3204247483196425023LL},
    {-259183498684964947LL, 302900817214050381LL}, {-5526195139465159159LL, 8649439639096143857LL},
    {7435670680273485520LL, 8019503784523374817LL}, {857902714356338687LL, 866228197597082079LL},
    {16384, -262144}, {35184372088832LL, 262144},
    {2147483648, -131072}, {1, -35184372088832LL},
};
constexpr std::size_t corpus_size = sizeof corpus / sizeof corpus[0];

// Each fraction of the corpus in a constant expression of its own.
template <class X, std::size_t I>
constexpr kairn::Constant<X> at_compile_time = kairn::rational<X>(corpus[I].num, corpus[I].den);
template <class X, std::size_t I>
constexpr kairn::Constant<X> integer_at_compile_time = kairn::integer<X>(corpus[I].num);
template <class X, std::size_t... I>
std::array<kairn::Constant<X>, corpus_size> table(std::index_sequence<I...>) {
    return {{at_compile_time<X, I>...}};
}
template <class X, std::size_t... I>
std::array<kairn::Constant<X>, corpus_size> integer_table(std::index_sequence<I...>) {
    return {{integer_at_compile_time<X, I>...}};
}

int failures = 0;

template <class X>
bool same_bits(const kairn::Constant<X>& a, const kairn::Constant<X>& b) {
    bool ok = bits(a.error) == bits(b.error) && a.exact == b.exact;
    for (int i = 0; i < limbs_of<X>; ++i) ok = ok && bits(limb(a.value, i)) == bits(limb(b.value, i));
    return ok;
}

template <class X>
void run_time(const char* type, const char* mode) {
    const auto expected = table<X>(std::make_index_sequence<corpus_size>{});
    const auto expected_integer = integer_table<X>(std::make_index_sequence<corpus_size>{});
    for (std::size_t i = 0; i < corpus_size; ++i) {
        volatile long long v_num = corpus[i].num, v_den = corpus[i].den;
        const long long num = v_num, den = v_den;
        const kairn::Constant<X> c = kairn::rational<X>(num, den);
        if (!same_bits(c, expected[i]) || !kairn::is_rational_result(c, num, den)) {
            std::printf("FAILED %s, %s: rational(%lld, %lld) differs at run time\n", type, mode, num, den);
            ++failures;
        }
        const kairn::Constant<X> n = kairn::integer<X>(num);
        if (!same_bits(n, expected_integer[i]) || !kairn::is_rational_result(n, num, 1)) {
            std::printf("FAILED %s, %s: integer(%lld) differs at run time\n", type, mode, num);
            ++failures;
        }
    }
    // den = 0: the canonical NaN, +infinity, false.
    volatile long long v_zero = 0;
    const kairn::Constant<X> z = kairn::rational<X>(-3, v_zero);
    bool nan = true;
    for (int i = 0; i < limbs_of<X>; ++i) nan = nan && limb(z.value, i) != limb(z.value, i);
    if (!nan || bits(z.error) != bits(std::numeric_limits<limb_t<X>>::infinity()) || z.exact ||
        !kairn::is_rational_result(z, -3, 0)) {
        std::printf("FAILED %s, %s: rational(-3, 0) is not (NaN, +inf, false)\n", type, mode);
        ++failures;
    }
}

}  // namespace

int main() {
    const struct {
        int mode;
        const char* name;
    } modes[] = {{FE_TONEAREST, "to nearest"},
                 {FE_UPWARD, "upward"},
                 {FE_DOWNWARD, "downward"},
                 {FE_TOWARDZERO, "toward zero"}};
    int ran = 0;
    for (const auto& m : modes) {
        if (std::fesetround(m.mode) != 0) {
            std::printf("skip  : rounding %s cannot be set here\n", m.name);
            continue;
        }
        // Under a directed mode the environment is not the default one; KAIRN_CHECKS, when it is 1,
        // would stop an operation that rounds, and must let kairn::rational through.
        const bool env = kairn::environment_ok();
        run_time<D1>("Expansion<double, 1>", m.name);
        run_time<D2>("Expansion<double, 2>", m.name);
        run_time<F1>("Expansion<float, 1>", m.name);
        run_time<F2>("Expansion<float, 2>", m.name);
        run_time<double>("double", m.name);
        run_time<float>("float", m.name);
        std::fesetround(FE_TONEAREST);
        std::printf("ok    : %zu fractions, rounding %s (environment_ok: %s), the same bits as in constant "
                    "expressions\n",
                    corpus_size, m.name, env ? "true" : "false");
        ++ran;
    }
    std::printf("KAIRN_CHECKS: %d, KAIRN_RATIONAL_CHECK: %d; %d rounding modes; %s\n", KAIRN_CHECKS,
                KAIRN_RATIONAL_CHECK, ran, failures ? "FAILED" : "ok");
    return failures == 0 && ran > 0 ? 0 : 1;
}
