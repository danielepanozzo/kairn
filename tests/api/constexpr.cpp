// Compile-time tests of the public interface: everything that is constexpr is evaluated in a
// static_assert, for double and float, and main() checks that the same expressions computed at run
// time, on operands the compiler cannot see, give the same limbs. Also: the types are regular value
// types, the unmarked operations exist exactly when gen/claims.json says the kernel they call is
// proved, and kairn::traits exports constants exactly for those.
//
// What is constexpr: construction (make_2, make_2_limbs, ball_make_1, ball_make_2, a ball from a
// constant of kairn::rational), the sums and differences of two limbs (the full kernels of the
// additions), negation and absolute value, the comparisons and conversions, everything of one
// limb, a ball's negation, states, sign predicates and constants, and the building blocks on T
// but mul_down and mul_up (blocks.hpp), each against values computed by hand, with the same bits at
// run time where milestone2.md says so ("The two executions of a product") and the same values
// where a zero can differ in sign; and of intervals (interval.hpp) the constructors, the states,
// the bounds, the negation, the hull, the intersection, the midpoint, the radius, the split and
// the conversions, and of a ball the functions of the interface it shares with intervals, the
// empty set and the whole line through each. Not yet: the products of two limbs, ldexp and half on
// two limbs and on balls, and the Ball and Interval arithmetic: their kernels have fused operations
// without a constant-evaluation variant, or their code is where KAIRN_ENCLOSURE_CODE puts it
// (main() checks the arithmetic of intervals at run time, against values computed by hand).
// mul_down and mul_up are not constexpr, by design (api.reject.not_constexpr.*); main() checks them
// at run time.
// Also: KAIRN_VERSION_AT_LEAST, in #if and in a constant expression.
//
// The comparisons are evaluated with NaN operands too: one compiler's constant evaluator takes
// a < b for true when an operand is a NaN, so every comparison that can run in constant evaluation
// is written b > a or b >= a, generated or not, and these asserts are what shows it.
#include <kairn/kairn.hpp>

#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <type_traits>

// The test of a version, as a program writes it (version.hpp).
#if !defined(KAIRN_VERSION_AT_LEAST)
#error "version.hpp defines no KAIRN_VERSION_AT_LEAST"
#elif !KAIRN_VERSION_AT_LEAST(0, 2, 0) || KAIRN_VERSION_AT_LEAST(0, 2, 1) || !KAIRN_VERSION_AT_LEAST(0, 1, 99)
#error "KAIRN_VERSION_AT_LEAST disagrees with version 0.2.0"
#endif
static_assert(KAIRN_VERSION == 200 && KAIRN_VERSION_AT_LEAST(0, 0, 0) && !KAIRN_VERSION_AT_LEAST(1, 0, 0));

// A program's own function with the name of a building block: Kairn's does not hide it, even with
// `using namespace kairn`, and a plain double finds no function of Kairn's by argument-dependent
// lookup (the requires-expressions of Blocks below).
namespace program {
constexpr double next_up(double x) { return x + 1; }
constexpr double call_with_kairn_used() {
    using namespace kairn;
    return next_up(1.0);
}
static_assert(call_with_kairn_used() == 2.0);
}  // namespace program

namespace {

namespace bounds = kairn::gen::bounds;
using kairn::unverified;

template <class X, class Y>
concept can_add = requires(X x, Y y) { x + y; };
template <class X, class Y>
concept can_sub = requires(X x, Y y) { x - y; };
template <class X, class Y>
concept can_mul = requires(X x, Y y) { x * y; };
template <class X, class Y>
concept can_less = requires(X x, Y y) { x < y; };
template <class X>
concept can_negate = requires(X x) { -x; };
template <class X>
concept can_to_down = requires(X x) { kairn::to_down(x); };
template <class B>
concept has_unit = requires { B::unit; };

template <class T>
struct Checks {
    using E1 = kairn::Expansion<T, 1>;
    using E2 = kairn::Expansion<T, 2>;
    using B1 = kairn::Ball<T, 1>;
    using B2 = kairn::Ball<T, 2>;
    static constexpr T u = std::numeric_limits<T>::epsilon() / 2;
    static constexpr T inf = std::numeric_limits<T>::infinity();
    static constexpr T nan = std::numeric_limits<T>::quiet_NaN();

    // Regular value types (the brief, "API for generic clients").
    static_assert(std::is_trivially_copyable_v<E1> && std::is_trivially_copyable_v<E2>);
    static_assert(std::is_standard_layout_v<E1> && std::is_standard_layout_v<E2>);
    static_assert(sizeof(E1) == sizeof(T) && sizeof(E2) == 2 * sizeof(T));
    static_assert(std::is_trivially_copyable_v<B1> && std::is_trivially_copyable_v<B2>);
    static_assert(std::is_standard_layout_v<B2> && sizeof(B2) == 3 * sizeof(T));
    static_assert(std::is_convertible_v<T, E2> && std::is_convertible_v<E1, E2>);
    static_assert(!std::is_convertible_v<E2, E1> && std::is_constructible_v<E1, E2>);
    static_assert(std::is_convertible_v<T, B2> && std::is_convertible_v<E2, B2> && std::is_convertible_v<E1, B1>);

    // Construction, and the canonical forms of infinities and NaN.
    static constexpr E2 zero{};
    static_assert(zero.limb[0] == 0 && zero.limb[1] == 0);
    static constexpr T limbs[2] = {T(1), u / 2};
    static constexpr E2 x = E2::from_limbs(limbs);
    static_assert(x.limb[0] == 1 && x.limb[1] == u / 2 && kairn::is_normalized(x));
    static_assert(E2(E1(T(3))).limb[0] == 3 && E2(T(3)).limb[1] == 0 && E2(unverified(T(3))).limb[0] == 3);
    static_assert(E1(x).limb[0] == 1 && E1(unverified(x)).limb[0] == 1);
    static_assert(E2(inf).limb[0] == inf && E2(inf).limb[1] == 0 && E2(-inf).limb[0] == -inf && E2(-inf).limb[1] == 0);
    static_assert(E2(nan).limb[0] != E2(nan).limb[0] && E2(nan).limb[1] != E2(nan).limb[1]);
    static_assert(E2(E1(-inf)).limb[0] == -inf && E2(E1(nan)).limb[1] != E2(E1(nan)).limb[1]);
    static constexpr T inf_limbs[2] = {inf, T(0)};
    static constexpr T nan_limbs[2] = {nan, nan};
    static_assert(E2::from_limbs(inf_limbs).limb[0] == inf && E2::from_limbs(inf_limbs).limb[1] == 0);
    static_assert(E2::from_limbs(nan_limbs).limb[0] != E2::from_limbs(nan_limbs).limb[0]);
    static_assert(!kairn::isfinite(E2(inf)) && !kairn::isfinite(E2(nan)) && !kairn::is_normalized(E2(nan)));
    static constexpr E2 einf = E2(inf), enan = E2(nan);

    // Two limbs: the sums and differences are the full kernels, constexpr.
    static constexpr E2 y = E2(T(3)) + x;  // 4 + u/2
    static_assert(y.limb[0] == 4 && y.limb[1] == u / 2);
    static_assert((x + T(2)).limb[0] == 3 && (T(2) + x).limb[1] == u / 2);
    static_assert((y - x).limb[0] == 3 && (y - x).limb[1] == 0);
    static_assert((y - T(4)).limb[0] == u / 2 && (T(5) - y).limb[0] == 1);
    static_assert(kairn::add_fast(x, x).limb[0] == 2);
    static constexpr E2 acc = [] {
        E2 a = x;
        a += x;
        a += T(1);
        a -= T(1);
        a += E1(T(1));
        a -= y;
        return a;
    }();
    static_assert(acc.limb[0] == -1 && acc.limb[1] == u / 2);
    // A sum that overflows is not a constant expression (GCC and Clang refuse an operation that
    // produces an infinity from finite operands, or a NaN): main() computes it at run time.
    static constexpr E2 big = E2(std::numeric_limits<T>::max());
    // The finite cores.
    static_assert(kairn::finite::add(x, x).limb[0] == 2 && kairn::finite::sub(y, T(4)).limb[0] == u / 2);
    static_assert(kairn::finite::add(x, E1(T(1))).limb[1] == u / 2 && kairn::finite::add_fast(x, x).limb[0] == 2);

    // Negation, absolute value, comparisons and conversions, on finite, infinite and NaN values.
    static_assert((-x).limb[0] == -1 && kairn::abs(-x).limb[1] == u / 2);
    static_assert((-E2(inf)).limb[0] == -inf && kairn::abs(E2(-inf)).limb[0] == inf && kairn::abs(E2(-inf)).limb[1] == 0);
    static_assert(x < y && y > x && !(y < x) && x <= x && x >= x && x == x && !(x != x));
    static_assert(x > T(1) && T(1) < x && x >= T(1) && !(x <= T(1)) && T(2) > x && T(2) >= x && x != T(1));
    static_assert(!(T(1) == x) && E2(T(1)) == T(1));
    static_assert(x > E1(T(1)) && E1(T(1)) < x && x >= E1(T(1)) && E1(T(2)) >= x && x != E1(T(1)) && !(E1(T(1)) == x));
    static_assert(E2(-inf) < x && x < E2(inf) && E2(inf) > T(0) && T(0) > E2(-inf) && E2(inf) == inf);
    static_assert(!(E2(nan) < x) && !(x < E2(nan)) && !(E2(nan) <= x) && !(x <= E2(nan)) && !(E2(nan) > x));
    static_assert(!(E2(nan) >= x) && !(E2(nan) == E2(nan)) && E2(nan) != E2(nan));
    static_assert(!(E2(nan) < T(1)) && !(T(1) < E2(nan)) && !(E2(nan) <= T(1)) && !(T(1) <= E2(nan)));
    static_assert(!(E2(nan) < E1(T(1))) && !(E1(T(1)) <= E2(nan)) && E2(nan) != T(1));
    static_assert(kairn::to_nearest(x) == 1 && kairn::to_down(x) == 1 && kairn::to_up(x) == 1 + 2 * u);
    static_assert(kairn::abs_upper(-x) == 1 + 2 * u && kairn::to_up(E2(inf)) == inf && kairn::to_down(E2(-inf)) == -inf);
    static_assert(kairn::abs_upper(E2(-inf)) == inf && kairn::to_nearest(E2(nan)) != kairn::to_nearest(E2(nan)));
    static_assert(kairn::sign(x) == 1 && kairn::sign(-x) == -1 && kairn::sign(zero) == 0 && kairn::sign(E2(nan)) == 0);
    // (1, u) is normalized (1 + u is a tie, and 1 is even); (1, 2u) is not.
    static_assert(kairn::is_normalized(E2::from_limbs_unchecked(std::array<T, 2>{T(1), u}.data())));
    static_assert(!kairn::is_normalized(E2::from_limbs_unchecked(std::array<T, 2>{T(1), 2 * u}.data())));

    // Mixed numbers of limbs: the one-limb operand is a limb of the _2_1 and _1_2 kernels.
    static_assert((x + E1(T(1))).limb[0] == 2 && (E1(T(1)) + x).limb[1] == u / 2);
    static_assert((x - E1(T(1))).limb[0] == u / 2 && (E1(T(2)) - x).limb[0] == 1 && E1(T(1)) < x);

    // The marked forms compile and compute the same.
    static_assert((unverified(y) - x).limb[0] == 3 && (y - unverified(T(4))).limb[0] == u / 2);
    static_assert((-unverified(x)).limb[0] == -1 && unverified(x) < y && kairn::to_up(unverified(x)) == 1 + 2 * u);
    static_assert(kairn::finite::add(unverified(x), x).limb[0] == 2);

    // One limb: each operation is the operation of T, comparisons with NaN included.
    static constexpr E1 a{T(3)}, b{T(4)};
    static_assert((a + b).limb[0] == 7 && (a - b).limb[0] == -1 && (a * b).limb[0] == 12 && (a * T(2)).limb[0] == 6);
    static_assert((T(1) + E1(u)).limb[0] == 1);  // rounded, ties to even
    static_assert(kairn::add_fast(a, b).limb[0] == 7 && kairn::finite::mul(a, T(2)).limb[0] == 6);
    static_assert(kairn::ldexp(a, -1).limb[0] == T(1.5) && kairn::half(b).limb[0] == 2);
    static_assert(kairn::ldexp(E1(T(1)), -1100).limb[0] == 0 && kairn::ldexp(E1(std::numeric_limits<T>::denorm_min()), 200).limb[0] > 0);
    static_assert([] {
        E1 c = a;
        c += b;
        c *= T(2);
        c -= E1(T(1));
        return c.limb[0] == 13;
    }());
    static_assert((-a).limb[0] == -3 && kairn::abs(-a).limb[0] == 3 && a < b && b > a && a <= a && a != b);
    static_assert(a == T(3) && T(3) == a && a < T(4));
    static_assert(!(E1(nan) < a) && !(a < E1(nan)) && !(E1(nan) <= a) && !(a <= E1(nan)) && !(E1(nan) > a));
    static_assert(!(E1(nan) >= a) && !(E1(nan) == E1(nan)) && E1(nan) != E1(nan) && !(E1(nan) < T(1)));
    static_assert(kairn::to_nearest(a) == 3 && kairn::to_down(a) == 3 && kairn::to_up(a) == 3 && kairn::abs_upper(-a) == 3);

    // Balls: construction, the three states, the constants, and the negation.
    static constexpr B2 p{x, u};
    static_assert(p.center().limb[1] == u / 2 && p.radius() == u && B2(T(2)).radius() == 0);
    static_assert(p.is_finite() && !p.is_whole() && !p.is_empty());
    static_assert(B2::whole().is_whole() && !B2::whole().is_finite() && B2::whole().center().limb[0] == 0);
    static_assert(B2::empty().is_empty() && !B2::empty().is_finite() && !B2::empty().is_whole());
    static_assert(B1::whole().radius() == inf && B1::empty().center().limb[0] != B1::empty().center().limb[0]);
    static_assert(B2(inf).is_whole() && B2(nan).is_whole() && B2(E2(-inf)).is_whole() && B1(-inf).is_whole());
    // A NaN radius gives the whole line (decided on 2026-11-20), a negative one the empty set.
    static_assert(B2(x, inf).is_whole() && B2(x, nan).is_whole() && B1(a, nan).is_whole() && B1(T(1), T(0.5)).is_finite());
    static_assert(B2(E2(inf), T(1)).is_whole() && B2(E2(nan), T(1)).is_whole() && B2(E2(nan), nan).is_whole());
#if !KAIRN_CHECKS
    static_assert(B2(x, -u).is_empty() && B1(a, -inf).is_empty());  // KAIRN_CHECKS reports a negative radius
#endif
    static_assert((-p).center().limb[0] == -1 && (-p).radius() == u && (-unverified(p)).radius() == u);
    static_assert((-B2::whole()).is_whole() && (-B2::empty()).is_empty() && (-B1(a)).center().limb[0] == -3);

    // The unmarked forms exist exactly when the kernel they call is proved.
    static_assert(can_add<E2, E2> == bounds::add_2_2_full<T>::proved && can_add<E2, T> == bounds::add_2_1_full<T>::proved);
    static_assert(can_add<E2, E1> == bounds::add_2_1_full<T>::proved && can_add<E1, E2> == bounds::add_2_1_full<T>::proved);
    static_assert(can_sub<E2, E2> == bounds::sub_2_2_full<T>::proved && can_sub<E2, T> == bounds::sub_2_1_full<T>::proved);
    static_assert(can_sub<T, E2> == bounds::sub_1_2_full<T>::proved && can_sub<E1, E2> == bounds::sub_1_2_full<T>::proved);
    static_assert(can_mul<E2, E2> == bounds::mul_2_2_full<T>::proved && can_mul<T, E2> == bounds::mul_2_1_full<T>::proved);
    static_assert(can_less<E2, E2> == bounds::lt_2_2<T>::proved && can_less<E2, T> == bounds::lt_2_1<T>::proved);
    static_assert(can_less<E2, E1> == bounds::lt_2_1<T>::proved && can_less<T, E2> == bounds::lt_1_2<T>::proved);
    static_assert(can_negate<E2> == bounds::neg_2<T>::proved && can_to_down<E2> == bounds::to_down_2<T>::proved);
    static_assert(can_add<E1, E1> == bounds::add_1_1<T>::proved && can_mul<E1, T> == bounds::mul_1_1<T>::proved);
    static_assert(can_add<B2, B2> == bounds::ball_add_2_full<T>::proved && can_mul<B1, T> == bounds::ball_scale_1_full<T>::proved);
    static_assert(can_add<B2, T> == (bounds::ball_add_2_full<T>::proved && bounds::ball_make_2<T>::proved && bounds::make_2<T>::proved));
    static_assert(can_mul<B2, E2> == (bounds::ball_mul_2_full<T>::proved && bounds::ball_make_2<T>::proved));
    static_assert(can_mul<B1, E1> == bounds::ball_scale_1_full<T>::proved && can_negate<B2> == bounds::ball_neg_2<T>::proved);
    static_assert(std::is_constructible_v<E2, T> == bounds::make_2<T>::proved);
    static_assert(std::is_constructible_v<E1, E2> == bounds::to_nearest_2<T>::proved);
    static_assert(std::is_constructible_v<B2, E2, T> == bounds::ball_make_2<T>::proved);
    // Exact operations without a kernel need no marker.
    static_assert(can_negate<E1> && can_less<E1, E1> && can_to_down<E1>);
    // With the marker, everything exists.
    static_assert(can_sub<kairn::Unverified<E2>, E2> && can_less<T, kairn::Unverified<E2>> && can_negate<kairn::Unverified<B2>>);
    // A marked left operand of a compound assignment would modify a copy: it does not compile.
    static_assert(!requires(kairn::Unverified<E2> m, E2 e) { m += e; });

    // traits: constants for proved kernels only, and the values of gen/bounds.hpp (the cores'
    // bounds, which the operators keep whenever their result is finite).
    using TR = kairn::traits<E2>;
    static_assert(TR::limbs == 2 && TR::precision == 2 * std::numeric_limits<T>::digits);
    static_assert(TR::add.verified == bounds::add_2_2<T>::proved && TR::sub.verified == bounds::sub_2_2<T>::proved);
    static_assert(has_unit<decltype(TR::mul)> == bounds::mul_2_2<T>::proved);
    static_assert(has_unit<decltype(TR::sub)> == bounds::sub_2_2<T>::proved);
    static_assert(TR::add.unit == bounds::add_2_2<T>::unit && TR::mul.tiny == bounds::mul_2_2<T>::tiny);
    static_assert(TR::mul_limb.unit_computed == bounds::mul_2_1<T>::unit_computed);
    static_assert(TR::add.reference == kairn::BoundForm::result);
    static_assert(kairn::traits<T>::limbs == 1 && kairn::traits<E1>::add.verified == bounds::add_1_1<T>::proved);
};

template struct Checks<double>;
template struct Checks<float>;

// The bit pattern of a value of T.
template <class T>
constexpr auto bits(T x) noexcept {
    if constexpr (sizeof(T) == 8) {
        return std::bit_cast<std::uint64_t>(x);
    } else {
        return std::bit_cast<std::uint32_t>(x);
    }
}

// A function of this name that no T converts to, so that the unqualified call below names a
// declaration for ordinary lookup, and only argument-dependent lookup could find another.
struct adl_probe {};
[[maybe_unused]] void next_up(adl_probe) {}
template <class X>
concept can_next_up_by_adl = requires(X x) { next_up(x); };
template <class X, class Y>
concept can_two_sum = requires(X x, Y y) { kairn::two_sum(x, y); };
template <class X>
concept can_next_up = requires(X x) { kairn::next_up(x); };

// The building blocks on T (blocks.hpp), the scaling, the predicates and the constant of a ball.
// Every expected value is written in terms of u = 2^-p, eta and Omega, computed by hand.
template <class T>
struct Blocks {
    using E1 = kairn::Expansion<T, 1>;
    using E2 = kairn::Expansion<T, 2>;
    using B1 = kairn::Ball<T, 1>;
    using B2 = kairn::Ball<T, 2>;
    using L = std::numeric_limits<T>;
    static constexpr T u = L::epsilon() / 2;  // 2^-p
    static constexpr T eta = L::denorm_min();
    static constexpr T omega = (L::max)();
    static constexpr T inf = L::infinity();
    static constexpr T nan = L::quiet_NaN();
    static constexpr T one = 1;
    // A power of two whose products with numbers near 1 are below 2^(2p-1) eta.
    static constexpr T tiny_scale = [] {
        if constexpr (sizeof(T) == 8) {
            return T(0x1p-1000);
        } else {
            return T(0x1p-120);
        }
    }();

    // The types: aggregates of two named members, the sum and the product rounded first.
    static_assert(std::is_aggregate_v<kairn::SumAndError<T>> && std::is_trivially_copyable_v<kairn::SumAndError<T>>);
    static_assert(std::is_aggregate_v<kairn::ProductAndError<T>> && sizeof(kairn::SumAndError<T>) == 2 * sizeof(T));
    static_assert(!std::is_convertible_v<kairn::SumAndError<T>, E2> && std::is_constructible_v<E2, kairn::SumAndError<T>>);
    static_assert(!std::is_constructible_v<E2, kairn::ProductAndError<T>>);
    static constexpr auto structured = [] {
        auto [s, e] = kairn::two_sum(one, u / 2);
        return s == 1 && e == u / 2;
    }();
    static_assert(structured);
    // Function templates of namespace kairn: not found for a T by argument-dependent lookup, and
    // with both operands of one type.
    static_assert(!can_next_up_by_adl<T> && can_next_up<T> && !can_next_up<int> && !can_next_up<E1>);
    static_assert(can_two_sum<T, T> && !can_two_sum<T, int> && can_two_sum<kairn::Unverified<T>, T>);
    static_assert(!can_two_sum<double, float> && !can_two_sum<E1, T>);
    static_assert(can_two_sum<T, T> == kairn::gen::bounds::two_sum_entry<T>::proved);

    // two_sum and fast_two_sum: RN(a + b) and the error, exact.
    static constexpr kairn::SumAndError<T> s1 = kairn::two_sum(one, u / 2);  // 1 + u/2 rounds to 1
    static_assert(s1.sum == 1 && s1.error == u / 2);
    static_assert(kairn::two_sum(u / 2, one).sum == 1 && kairn::two_sum(u / 2, one).error == u / 2);
    static_assert(kairn::two_sum(T(3), u).sum == 3 && kairn::two_sum(T(3), u).error == u);  // the gap at 3 is 4u
    static_assert(kairn::two_sum(T(3), 3 * u).sum == 3 + 4 * u && kairn::two_sum(T(3), 3 * u).error == -u);
    static_assert(kairn::two_sum(T(1.5), T(-1.5)).sum == 0 && kairn::two_sum(T(1.5), T(-1.5)).error == 0);
    static_assert(kairn::fast_two_sum(one, u / 2).sum == 1 && kairn::fast_two_sum(one, u / 2).error == u / 2);
    static_assert(kairn::fast_two_sum(T(4), T(-1)).sum == 3 && kairn::fast_two_sum(T(4), T(-1)).error == 0);
    static_assert(kairn::fast_two_sum(-one, -u / 2).sum == -1 && kairn::fast_two_sum(-one, -u / 2).error == -u / 2);
    static_assert(kairn::two_sum(kairn::unverified(one), u / 2).error == u / 2);
    static_assert(kairn::fast_two_sum(one, kairn::unverified(u / 2)).error == u / 2);
#if !KAIRN_CHECKS
    // Outside the requirement |a| >= |b| (a build with the checks stops it): RN(a + b) and a number
    // of T, but not the exact sum, which is 1 + u/4.
    static_assert(kairn::fast_two_sum(u / 4, one).sum == 1 && kairn::fast_two_sum(u / 4, one).error == 0);
#endif
    // The pair as a two-limb number: (1, u/2), normalized; the canonical NaN from two NaN.
    static constexpr E2 x = E2(kairn::two_sum(one, u / 2));
    static_assert(x.limb[0] == 1 && x.limb[1] == u / 2 && kairn::is_normalized(x));
    static_assert(E2(kairn::fast_two_sum(T(3), 3 * u)).limb[1] == -u);
    static constexpr kairn::SumAndError<T> nans{nan, nan};
    static_assert(E2(nans).limb[0] != E2(nans).limb[0] && E2(nans).limb[1] != E2(nans).limb[1]);

    // two_prod: in constant evaluation Dekker's product, exact above 2^(2p-1) eta.
    static constexpr kairn::ProductAndError<T> p1 = kairn::two_prod(1 + 2 * u, 1 - 2 * u);  // 1 - 4u^2
    static_assert(p1.product == 1 && p1.error == -4 * u * u);
    static constexpr kairn::ProductAndError<T> p2 = kairn::two_prod(1 + 2 * u, 1 + 2 * u);  // 1 + 4u + 4u^2
    static_assert(p2.product == 1 + 4 * u && p2.error == 4 * u * u);
    static_assert(kairn::two_prod(T(3), T(0.5)).product == T(1.5) && kairn::two_prod(T(3), T(0.5)).error == 0);
    static_assert(kairn::two_prod(kairn::unverified(T(0)), T(5)).product == 0);

    // next_up and next_down: every row of milestone2.md's table, on the bit pattern.
    static_assert(bits(kairn::next_up(one)) == bits(T(1 + 2 * u)) && bits(kairn::next_down(one)) == bits(T(1 - u)));
    static_assert(bits(kairn::next_up(T(0))) == bits(eta) && bits(kairn::next_up(-T(0))) == bits(eta));
    static_assert(bits(kairn::next_down(T(0))) == bits(-eta) && bits(kairn::next_down(-T(0))) == bits(-eta));
    static_assert(bits(kairn::next_up(-eta)) == bits(-T(0)) && bits(kairn::next_down(eta)) == bits(T(0)));
    static_assert(bits(kairn::next_up(eta)) == bits(T(2 * eta)) && bits(kairn::next_down(-eta)) == bits(T(-2 * eta)));
    static_assert(bits(kairn::next_up(omega)) == bits(inf) && bits(kairn::next_down(-omega)) == bits(-inf));
    static_assert(bits(kairn::next_up(inf)) == bits(inf) && bits(kairn::next_down(inf)) == bits(omega));
    static_assert(bits(kairn::next_up(-inf)) == bits(-omega) && bits(kairn::next_down(-inf)) == bits(-inf));
    static_assert(kairn::next_down(omega) == omega - omega * u && kairn::next_up(-omega) == -omega + omega * u);
    static_assert(bits(kairn::next_up(-one)) == bits(T(-1 + u)) && bits(kairn::next_down(-one)) == bits(T(-1 - 2 * u)));
    static_assert(kairn::next_up(nan) != kairn::next_up(nan) && kairn::next_down(nan) != kairn::next_down(nan));
    static_assert(kairn::next_up((L::min)()) == (L::min)() + eta && kairn::next_down((L::min)()) == (L::min)() - eta);
    static_assert(bits(kairn::next_up(kairn::unverified(one))) == bits(T(1 + 2 * u)));

    // radd and rmul: the number after the rounded result; the same bits at run time.
    static_assert(bits(kairn::radd(one, u / 2)) == bits(T(1 + 2 * u)) && bits(kairn::radd(T(0), T(0))) == bits(eta));
    static_assert(bits(kairn::radd(T(1.5), T(1.5))) == bits(T(3 + 4 * u)));
    static_assert(bits(kairn::rmul(T(1.5), T(2))) == bits(T(3 + 4 * u)) && bits(kairn::rmul(T(0), T(5))) == bits(eta));
    static_assert(bits(kairn::rmul(-T(0), T(5))) == bits(eta) && bits(kairn::rmul(eta, T(0.5))) == bits(eta));
    static_assert(bits(kairn::rmul(kairn::unverified(T(1.5)), T(2))) == bits(T(3 + 4 * u)));

    // The directed sums: the rounding down or up of the exact sum, to nearest.
    static_assert(kairn::add_down(one, u / 2) == 1 && kairn::add_up(one, u / 2) == 1 + 2 * u);
    static_assert(kairn::sub_down(one, u / 2) == 1 - u && kairn::sub_up(one, u / 2) == 1);
    static_assert(kairn::add_down(one, -u / 2) == 1 - u && kairn::add_up(-one, -u / 2) == -1);
    static_assert(kairn::add_down(T(1.5), T(2.25)) == T(3.75) && kairn::sub_up(T(1.5), T(2.25)) == T(-0.75));
    static_assert(kairn::add_down(one, -one) == 0 && kairn::sub_up(T(2), T(2)) == 0);
    static_assert(kairn::add_up(omega, -omega * u) == omega && kairn::add_down(omega, -omega * u) == omega - omega * u);
    static_assert(kairn::add_down(kairn::unverified(one), u / 2) == 1 && kairn::sub_up(one, kairn::unverified(u / 2)) == 1);

    // The ball of a constant: center the value, radius the error.
    static constexpr kairn::Constant<E2> third = kairn::rational<E2>(1, 3);
    static constexpr B2 t2{third};
    static_assert(t2.center().limb[0] == third.value.limb[0] && t2.center().limb[1] == third.value.limb[1]);
    static_assert(t2.radius() == third.error && t2.radius() > 0 && t2.is_finite());
    static constexpr kairn::Constant<E1> tenth = kairn::rational<E1>(1, 10);
    static_assert(B1(tenth).center().limb[0] == tenth.value.limb[0] && B1(tenth).radius() == tenth.error);
    static_assert(B2(kairn::integer<E2>(7)).radius() == 0 && B2(kairn::integer<E2>(7)).center().limb[0] == 7);
    static_assert(!std::is_convertible_v<kairn::Constant<E2>, B2> && std::is_constructible_v<B2, kairn::Constant<E2>>);
    static_assert(!std::is_constructible_v<B1, kairn::Constant<E2>> && !std::is_constructible_v<B2, kairn::Constant<T>>);

    // The sign predicates: the radius against the center, exactly; false on the empty set and the
    // whole line.
    static_assert(B1(T(2), T(1)).certainly_positive() && !B1(T(1), T(1)).certainly_positive());
    static_assert(B1(T(-2), T(1)).certainly_negative() && !B1(T(-1), T(1)).certainly_negative());
    static_assert(!B1(T(2), T(1)).certainly_negative() && !B1(T(-2), T(1)).certainly_positive());
    static_assert(B1().certainly_zero() && !B1(T(0), eta).certainly_zero() && !B1(eta).certainly_zero());
    static_assert(B1(eta).certainly_positive() && B1(-eta).certainly_negative() && !B1().certainly_positive());
    static constexpr T above[2] = {1, u / 2}, below[2] = {1, -u / 2};
    static constexpr E2 c_above = E2::from_limbs(above), c_below = E2::from_limbs(below);
    // 1 + u/2 - 1 > 0 and 1 - u/2 - 1 < 0: the second limb decides.
    static_assert(B2(c_above, one).certainly_positive() && !B2(c_below, one).certainly_positive());
    static_assert(B2(-c_above, one).certainly_negative() && !B2(-c_below, one).certainly_negative());
    static_assert(B2().certainly_zero() && !B2(E2(), eta).certainly_zero() && !B2(c_above, T(0)).certainly_zero());
    static_assert(!B1::empty().certainly_positive() && !B1::empty().certainly_negative() && !B1::empty().certainly_zero());
    static_assert(!B2::empty().certainly_positive() && !B2::empty().certainly_negative() && !B2::empty().certainly_zero());
    static_assert(!B1::whole().certainly_positive() && !B1::whole().certainly_negative() && !B1::whole().certainly_zero());
    static_assert(!B2::whole().certainly_positive() && !B2::whole().certainly_negative() && !B2::whole().certainly_zero());
    static_assert(!B2(E2(inf)).certainly_positive() && !B1(-inf).certainly_negative());
};

template struct Blocks<double>;
template struct Blocks<float>;

template <class X, class Y>
concept can_hull = requires(X x, Y y) { x.hull(y); };
template <class X>
concept can_midpoint = requires(X x) { x.midpoint(); };
template <class X>
concept can_split = requires(X x) { x.split(); };

// Intervals (interval.hpp) and the functions of a Ball of the interface the two share: every
// constexpr function, the empty set and the whole line through each, against values computed by
// hand; the types and the conversions that exist and those that do not.
template <class T>
struct Intervals {
    using E1 = kairn::Expansion<T, 1>;
    using E2 = kairn::Expansion<T, 2>;
    using B1 = kairn::Ball<T, 1>;
    using B2 = kairn::Ball<T, 2>;
    using I1 = kairn::Interval<T, 1>;
    using I2 = kairn::Interval<T, 2>;
    using L = std::numeric_limits<T>;
    static constexpr T u = L::epsilon() / 2;
    static constexpr T eta = L::denorm_min();
    static constexpr T omega = (L::max)();
    static constexpr T inf = L::infinity();
    static constexpr T nan = L::quiet_NaN();

    // The bounds of an interval of one limb, and whether it is the empty set or the whole line.
    static constexpr bool is(const I1& x, T l, T h) { return x.lower().limb[0] == l && x.upper().limb[0] == h; }
    static constexpr bool empty(const I1& x) { return is(x, inf, -inf); }
    static constexpr bool whole(const I1& x) { return is(x, -inf, inf); }
    static constexpr bool is(const I2& x, T l0, T l1, T h0, T h1) {
        return x.lower().limb[0] == l0 && x.lower().limb[1] == l1 && x.upper().limb[0] == h0 && x.upper().limb[1] == h1;
    }
    static constexpr bool empty(const I2& x) { return is(x, inf, 0, -inf, 0); }
    static constexpr bool whole(const I2& x) { return is(x, -inf, 0, inf, 0); }

    // Regular value types, of two bounds; the conversions that exist, and that none is implicit
    // but those of a point; no conversion between numbers of limbs.
    static_assert(std::is_trivially_copyable_v<I1> && std::is_trivially_copyable_v<I2>);
    static_assert(std::is_standard_layout_v<I1> && std::is_standard_layout_v<I2>);
    static_assert(sizeof(I1) == 2 * sizeof(T) && sizeof(I2) == 4 * sizeof(T));
    static_assert(std::is_convertible_v<T, I1> && std::is_convertible_v<E1, I1> && std::is_convertible_v<T, I2>);
    static_assert(std::is_convertible_v<E2, I2> && !std::is_constructible_v<I2, I1> && !std::is_constructible_v<I1, I2>);
    static_assert(std::is_constructible_v<I1, B1> && !std::is_convertible_v<B1, I1> && !std::is_constructible_v<I2, B2>);
    static_assert(std::is_constructible_v<B1, I1> && !std::is_convertible_v<I1, B1> && !std::is_constructible_v<B2, I2>);
    static_assert(std::is_constructible_v<B1, B2> && !std::is_convertible_v<B2, B1> && !std::is_constructible_v<B2, B1>);
    static_assert(!std::is_constructible_v<B1, I2> && !std::is_constructible_v<I1, B2>);
    // The operations exist exactly when the kernel they call is proved, between intervals of one
    // T and one number of limbs, and never with a number as an operand.
    static_assert(can_add<I1, I1> == bounds::interval_add_1<T>::proved && can_add<I2, I2> == bounds::interval_add_2<T>::proved);
    static_assert(can_sub<I1, I1> == bounds::interval_sub_1<T>::proved && can_mul<I2, I2> == bounds::interval_mul_2<T>::proved);
    static_assert(can_mul<I1, I1> == bounds::interval_mul_1<T>::proved && can_negate<I2> == bounds::interval_neg_2<T>::proved);
    static_assert(can_hull<I1, I1> == bounds::interval_hull_1<T>::proved && can_midpoint<I1> == bounds::interval_mid_rad_1<T>::proved);
    static_assert(can_split<I1> == bounds::interval_split_1<T>::proved && !can_midpoint<I2> && !can_split<I2>);
    static_assert(std::is_constructible_v<I1, T, T> == bounds::interval_make_1<T>::proved);
    static_assert(!can_add<I1, I2> && !can_add<I1, T> && !can_add<T, I1> && !can_mul<I2, E2> && !can_sub<I1, B1>);
    static_assert(!can_add<I1, kairn::Interval<float, 1>> || std::is_same_v<T, float>);
    static_assert(can_add<kairn::Unverified<I1>, I1> && can_negate<kairn::Unverified<I2>> && !can_add<kairn::Unverified<I1>, I2>);
    static_assert(can_midpoint<B1> && can_midpoint<B2>);

    // Construction: the point 0 by default; two bounds; a NaN bound the whole line; reversed
    // bounds and equal infinities the empty set; a point; the named states.
    static_assert(is(I1(), 0, 0) && is(I2(), 0, 0, 0, 0));
    static_assert(is(I1(T(1), T(2)), 1, 2) && is(I1(E1(T(-3)), E1(T(5))), -3, 5) && is(I1(unverified(T(1)), T(2)), 1, 2));
    static_assert(whole(I1(nan, T(1))) && whole(I1(T(1), nan)) && whole(I1(nan, nan)) && whole(I1(nan, -inf)));
    static_assert(whole(I1(inf, nan)) && whole(I1(-inf, inf)) && is(I1(-inf, T(1)), -inf, 1) && is(I1(T(1), inf), 1, inf));
    static_assert(empty(I1(T(2), T(1))) && empty(I1(inf, inf)) && empty(I1(-inf, -inf)) && empty(I1(inf, -inf)));
    static_assert(is(I1(T(3)), 3, 3) && whole(I1(nan)) && empty(I1(inf)) && empty(I1(-inf)) && is(I1(E1(T(3))), 3, 3));
    static_assert(empty(I1::empty()) && whole(I1::whole()) && empty(I2::empty()) && whole(I2::whole()));
    static constexpr T above[2] = {1, u / 2};
    static constexpr E2 x2 = E2::from_limbs(above);  // 1 + u/2
    static_assert(is(I2(x2, E2(T(2))), 1, u / 2, 2, 0) && is(I2(T(1), T(2)), 1, 0, 2, 0) && is(I2(x2), 1, u / 2, 1, u / 2));
    static_assert(whole(I2(E2(nan), x2)) && whole(I2(x2, E2(nan))) && whole(I2(nan)) && empty(I2(E2(T(2)), x2)));
    static_assert(empty(I2(inf)) && empty(I2(E2(-inf), E2(-inf))) && whole(I2(E2(-inf), E2(inf))) && is(I2(T(3)), 3, 0, 3, 0));
    static_assert(is(I2(unverified(x2), E2(T(2))), 1, u / 2, 2, 0) && is(I2(unverified(T(1)), T(2)), 1, 0, 2, 0));
    // The bounds as numbers of T: for two limbs rounded outward.
    static_assert(I1(T(1), T(2)).template lower_as<T>() == 1 && I1::empty().template upper_as<T>() == -inf);
    static_assert(I2(x2, x2).template lower_as<T>() == 1 && I2(x2, x2).template upper_as<T>() == 1 + 2 * u);
    static_assert(I2::empty().template lower_as<T>() == inf && I2::whole().template lower_as<T>() == -inf);
    static_assert(I2(-x2, -x2).template lower_as<T>() == -1 - 2 * u && I2(-x2, -x2).template upper_as<T>() == -1);

    // The negation, the hull and the intersection: exact.
    static_assert(is(-I1(T(1), T(2)), -2, -1) && empty(-I1::empty()) && whole(-I1::whole()) && is(-I1(T(1), inf), -inf, -1));
    static_assert(is(-I2(x2, E2(T(2))), -2, 0, -1, -u / 2) && empty(-I2::empty()) && whole(-I2::whole()));
    static_assert(is(-unverified(I1(T(1), T(2))), -2, -1));
    static_assert(is(I1(T(1), T(2)).hull(I1(T(3), T(4))), 1, 4) && is(I1(T(1), T(2)).hull(I1::empty()), 1, 2));
    static_assert(is(I1::empty().hull(I1(T(3), T(4))), 3, 4) && empty(I1::empty().hull(I1::empty())));
    static_assert(whole(I1::whole().hull(I1(T(3), T(4)))) && is(I1(T(1), T(2)).hull(unverified(I1(-inf, T(0)))), -inf, 2));
    static_assert(is(I1(T(1), T(3)).intersection(I1(T(2), T(4))), 2, 3) && empty(I1(T(1), T(2)).intersection(I1(T(3), T(4)))));
    static_assert(is(I1(T(1), T(2)).intersection(I1(T(2), T(4))), 2, 2) && empty(I1(T(1), T(2)).intersection(I1::empty())));
    static_assert(is(I1::whole().intersection(I1(T(3), T(4))), 3, 4) && whole(I1::whole().intersection(I1::whole())));
    static_assert(is(I2(T(1), T(3)).hull(I2(x2, E2(T(4)))), 1, 0, 4, 0) && is(I2(x2, E2(T(3))).intersection(I2(T(1), T(2))), 1, u / 2, 2, 0));
    static_assert(empty(I2(T(1), T(2)).intersection(I2(T(3), T(4)))) && empty(I2::empty().intersection(I2::whole())));
    static_assert(is(I2::empty().hull(I2(x2)), 1, u / 2, 1, u / 2) && whole(I2::whole().hull(I2::empty())));

    // The midpoint, the radius and the split: the values of mid and rad of IEEE 1788 on the
    // special states; for [eta, eta] the halves round to zero and the midpoint is moved back in.
    static_assert(I1(T(1), T(3)).midpoint().limb[0] == 2 && I1(T(1), T(3)).radius() == 1);
    static_assert(I1(T(1), T(2)).midpoint().limb[0] == T(1.5) && I1(T(1), T(2)).radius() == T(0.5));
    static_assert(I1::whole().midpoint().limb[0] == 0 && I1::whole().radius() == inf);
    static_assert(I1(T(1), inf).midpoint().limb[0] == omega && I1(-inf, T(1)).midpoint().limb[0] == -omega);
    static_assert(I1(T(1), inf).radius() == inf && I1(eta, eta).midpoint().limb[0] == eta && I1(eta, eta).radius() == 0);
    static_assert(I1(-omega, omega).midpoint().limb[0] == 0 && I1(-omega, omega).radius() == omega);
    static constexpr kairn::Split<I1> s13 = I1(T(1), T(3)).split();
    static_assert(is(s13.left, 1, 2) && is(s13.right, 2, 3));
    // On the empty set these listings compute a NaN before the select that returns their result
    // (inf + -inf), which GCC and Clang refuse in constant evaluation, as an overflowing sum: the
    // empty set is not a constant expression for the midpoint, the radius, the split and the
    // conversion to a ball. intervals_run_time checks them.
    // The whole line and a half-line: split at the listing's midpoint, 0 and Omega (only a point of
    // the interval is claimed).
    static_assert(is(I1::whole().split().left, -inf, 0) && is(I1::whole().split().right, 0, inf));
    static_assert(is(I1(T(1), inf).split().left, 1, omega) && is(I1(T(1), inf).split().right, omega, inf));

    // The conversions between an interval and a ball of one limb.
    static_assert(B1(I1(T(1), T(3))).center().limb[0] == 2 && B1(I1(T(1), T(3))).radius() == 1);
    static_assert(B1(I1(T(1), inf)).is_whole() && B1(I1::whole()).is_whole());
    static_assert(B1(unverified(I1(T(1), T(3)))).radius() == 1);
    // The empty set and the whole line are not constant expressions for the functions below, nor
    // an infinite or NaN bound for the ball from an interval of two T: their listings compute with
    // the NaN of the empty ball, or compute inf - inf on the way (c - r for the whole line, the sum
    // of two infinite halves), before the selects that return their results, and GCC and Clang
    // refuse such an operation in constant evaluation. intervals_run_time checks them.
    static_assert(is(I1(B1(T(2), T(1))), 1, 3) && is(I1(B1(T(5))), 5, 5));
    static_assert(is(I1(B1(T(1), u)), 1 - u, 1 + 2 * u) && is(I1(unverified(B1(T(2), T(1)))), 1, 3));
    // The ball of two limbs from an interval of two T: the exact midpoint when the halves are exact.
    static constexpr B2 f13 = B2::from_interval(T(1), T(1) + 2 * u);
    static_assert(f13.center().limb[0] == 1 && f13.center().limb[1] == u && f13.radius() == u);
    static_assert(B2::from_interval(T(1), T(3)).radius() == 1 && B2::from_interval(T(1), T(3)).center().limb[0] == 2);
    static_assert(B2::from_interval(T(2), T(1)).is_empty() && B2::from_interval(unverified(T(1)), T(3)).radius() == 1);
    // [eta, 3 eta]: the halves are not exact; the radius is the number after d, and covers.
    static_assert(B2::from_interval(eta, 3 * eta).radius() >= eta);

    // The bounds of a ball as numbers of T, its midpoint, and the narrowing to one limb.
    static_assert(B1(T(2), T(1)).template lower_as<T>() == 1 && B1(T(2), T(1)).template upper_as<T>() == 3);
    static_assert(B1(T(1), u).template lower_as<T>() == 1 - u && B1(T(1), u).template upper_as<T>() == 1 + 2 * u);
    static_assert(B1(T(2), T(1)).lower().limb[0] == 1 && B1(T(2), T(1)).upper().limb[0] == 3);
    // For two limbs the center is rounded to T first: c + r = 1 + 3u/2, RU(c + r) = 1 + 2u, but
    // RU(RU(c) + r) = RU(1 + 3u) = 1 + 4u, within the claim's 5 u (|c| + r) + 3 eta.
    static_assert(B2(x2, u).template lower_as<T>() == 1 - u && B2(x2, u).template upper_as<T>() == 1 + 4 * u);
    static_assert(B2(x2, u).midpoint().limb[1] == u / 2 && B1(T(2), T(1)).midpoint().limb[0] == 2);
    static_assert(B2::whole().midpoint().limb[0] == 0 && B1::empty().midpoint().limb[0] != B1::empty().midpoint().limb[0]);
    // The radius grows by radd(r, |c1|), the number after the rounded sum: eta for a point.
    static_assert(B1(B2(x2, T(0))).center().limb[0] == 1 && B1(B2(x2, T(0))).radius() > u / 2);
    static_assert(B1(B2(T(3))).center().limb[0] == 3 && B1(B2(T(3))).radius() == eta);
    static_assert(B1(unverified(B2(T(3)))).radius() == eta);
};

template struct Intervals<double>;
template struct Intervals<float>;

int failures = 0;

template <class T>
void same(const char* what, T run_time, T compile_time) {
    if (!(run_time == compile_time || (run_time != run_time && compile_time != compile_time))) {
        std::printf("differs at run time: %s (%a against %a)\n", what, double(run_time), double(compile_time));
        ++failures;
    }
}
// The same bits, compared as integers.
template <class T>
void same_bits(const char* what, T run_time, T compile_time) {
    if (bits(run_time) != bits(compile_time)) {
        std::printf("not the same bits at run time: %s (%a against %a)\n", what, double(run_time),
                    double(compile_time));
        ++failures;
    }
}
void expect(const char* what, bool ok) {
    if (!ok) {
        std::printf("FAILED at run time: %s\n", what);
        ++failures;
    }
}

// The building blocks at run time, on operands read through volatile objects, against the same
// expressions in constant evaluation: the same bits where milestone2.md says so, the same values
// otherwise; and mul_down, mul_up, ldexp and half of a ball, which are not constexpr, against
// values computed by hand.
template <class T>
void blocks_run_time() {
    using C = Blocks<T>;
    using E2 = kairn::Expansion<T, 2>;
    using B1 = kairn::Ball<T, 1>;
    using B2 = kairn::Ball<T, 2>;
    constexpr T u = C::u, eta = C::eta, omega = C::omega, inf = C::inf;
    volatile T v_one = 1, v_half_u = u / 2, v_three = 3, v_three_u = 3 * u, v_up = 1 + 2 * u, v_down = 1 - 2 * u;
    volatile T v_zero = 0, v_five = 5, v_eta = eta, v_omega = omega, v_inf = inf, v_nan = C::nan, v_r = T(0.25);
    const T one = v_one, half_u = v_half_u;
    {
        const auto r = kairn::two_sum(one, half_u);
        same("two_sum, sum", r.sum, C::s1.sum);
        same("two_sum, error", r.error, C::s1.error);
        const auto f = kairn::fast_two_sum(T(v_three), T(v_three_u));
        same("fast_two_sum", f.error, kairn::fast_two_sum(T(3), 3 * u).error);
        const E2 x = E2(r);
        same_bits("the conversion, first limb", x.limb[0], C::x.limb[0]);
        same_bits("the conversion, second limb", x.limb[1], C::x.limb[1]);
#if !KAIRN_CHECKS
        const auto outside = kairn::fast_two_sum(T(v_half_u / 2), one);
        same("fast_two_sum with |a| < |b|, sum", outside.sum, T(1));
        same("fast_two_sum with |a| < |b|, error", outside.error, T(0));
#endif
        // The corner of two_sum: b = Omega, a = -1.5 ulp(Omega): the sum is finite, the error a NaN.
        if constexpr (sizeof(T) == 8) {
            const auto c = kairn::two_sum(T(-1.5 * 0x1p971 * double(v_one)), T(v_omega));
            expect("two_sum's corner: the sum is Omega - ulp(Omega)", c.sum == omega - 0x1p971);
            expect("two_sum's corner: the error term is a NaN", c.error != c.error);
        }
        const auto n = kairn::two_sum(T(v_nan), one);
        expect("two_sum with a NaN: a NaN error term", n.sum != n.sum && n.error != n.error);
    }
    {
        // Above 2^(2p-1) eta both executions of two_prod are exact: the same values.
        const auto p = kairn::two_prod(T(v_up), T(v_down));
        same("two_prod, product", p.product, C::p1.product);
        same("two_prod, error", p.error, C::p1.error);
        // Below it, the FMA's error term and Dekker's are each within their bound of the exact one,
        // so within 17/8 eta of each other: at most 2 eta apart, being multiples of eta.
        constexpr T a = 1 + 2 * u, b = C::tiny_scale * (1 + 4 * u);
        constexpr kairn::ProductAndError<T> ce = kairn::two_prod(a, b);
        volatile T v_a = a, v_b = b;
        const auto rt = kairn::two_prod(T(v_a), T(v_b));
        same("two_prod below the threshold, product", rt.product, ce.product);
        const T d = rt.error - ce.error;
        expect("two_prod below the threshold: error terms within 2 eta", d <= 2 * eta && -d <= 2 * eta);
        const auto o = kairn::two_prod(T(v_omega), T(v_three));
        expect("two_prod that overflows: +inf and -inf", o.product == inf && o.error == -inf);
    }
    // next_up, next_down, radd, rmul: the same bits.
    same_bits("next_up(1)", kairn::next_up(one), kairn::next_up(T(1)));
    same_bits("next_down(1)", kairn::next_down(one), kairn::next_down(T(1)));
    same_bits("next_up(0)", kairn::next_up(T(v_zero)), kairn::next_up(T(0)));
    same_bits("next_down(0)", kairn::next_down(T(v_zero)), kairn::next_down(T(0)));
    same_bits("next_up(Omega)", kairn::next_up(T(v_omega)), kairn::next_up(omega));
    same_bits("next_down(-Omega)", kairn::next_down(-T(v_omega)), kairn::next_down(-omega));
    same_bits("next_up(-0)", kairn::next_up(-T(v_zero)), kairn::next_up(-T(0)));
    same_bits("next_up(-eta)", kairn::next_up(-T(v_eta)), kairn::next_up(-eta));
    same_bits("next_down(eta)", kairn::next_down(T(v_eta)), kairn::next_down(eta));
    same_bits("next_up(-inf)", kairn::next_up(-T(v_inf)), kairn::next_up(-inf));
    same_bits("next_down(inf)", kairn::next_down(T(v_inf)), kairn::next_down(inf));
    expect("next_up(NaN)", kairn::next_up(T(v_nan)) != kairn::next_up(T(v_nan)));
    same_bits("radd", kairn::radd(one, half_u), kairn::radd(T(1), u / 2));
    same_bits("radd(0, 0)", kairn::radd(T(v_zero), T(v_zero)), kairn::radd(T(0), T(0)));
    same_bits("rmul", kairn::rmul(T(1.5) * one, T(2) * one), kairn::rmul(T(1.5), T(2)));
    same_bits("rmul(-0, 5)", kairn::rmul(-T(v_zero), T(v_five)), kairn::rmul(-T(0), T(5)));
    same_bits("rmul(0, 5)", kairn::rmul(T(v_zero), T(v_five)), kairn::rmul(T(0), T(5)));
    same_bits("rmul(eta, 1/2)", kairn::rmul(T(v_eta), T(0.5) * one), kairn::rmul(eta, T(0.5)));
    expect("radd with +inf", kairn::radd(T(v_inf), one) == inf);
    expect("rmul of 0 and inf", kairn::rmul(T(v_zero), T(v_inf)) != kairn::rmul(T(v_zero), T(v_inf)));
    // The directed sums: the same values.
    same("add_down", kairn::add_down(one, half_u), kairn::add_down(T(1), u / 2));
    same("add_up", kairn::add_up(one, half_u), kairn::add_up(T(1), u / 2));
    same("sub_down", kairn::sub_down(one, half_u), kairn::sub_down(T(1), u / 2));
    same("sub_up", kairn::sub_up(one, half_u), kairn::sub_up(T(1), u / 2));
    same("add_down(1, -1)", kairn::add_down(one, -one), T(0));
    // At an overflow and on infinities, which constant evaluation refuses: computed by hand.
    expect("add_down(Omega, Omega) is Omega", kairn::add_down(T(v_omega), T(v_omega)) == omega);
    expect("add_up(Omega, Omega) is +inf", kairn::add_up(T(v_omega), T(v_omega)) == inf);
    expect("sub_down(-Omega, Omega) is -inf", kairn::sub_down(-T(v_omega), T(v_omega)) == -inf);
    expect("sub_up(-Omega, Omega) is -Omega", kairn::sub_up(-T(v_omega), T(v_omega)) == -omega);
    expect("add_down(inf, 1) is inf", kairn::add_down(T(v_inf), one) == inf);
    expect("add_up(inf, -inf) is a NaN", kairn::add_up(T(v_inf), -T(v_inf)) != kairn::add_up(T(v_inf), -T(v_inf)));
    // mul_down and mul_up, at run time only: (1 + 2u)(1 - 2u) = 1 - 4u^2.
    expect("mul_down((1 + 2u), (1 - 2u)) is 1 - u", kairn::mul_down(T(v_up), T(v_down)) == 1 - u);
    expect("mul_up((1 + 2u), (1 - 2u)) is 1", kairn::mul_up(T(v_up), T(v_down)) == 1);
    expect("mul_down(3, 1/2) is 3/2, exact", kairn::mul_down(T(v_three), T(0.5) * one) == T(1.5));
    expect("mul_up(3, 1/2) is 3/2, exact", kairn::mul_up(T(v_three), T(0.5) * one) == T(1.5));
    expect("mul_up(Omega, 3) is +inf", kairn::mul_up(T(v_omega), T(v_three)) == inf);
    expect("mul_down(Omega, 3) is Omega", kairn::mul_down(T(v_omega), T(v_three)) == omega);
    expect("mul_down(-Omega, 3) is -inf", kairn::mul_down(-T(v_omega), T(v_three)) == -inf);
    expect("mul_down(0, inf) is a NaN", kairn::mul_down(T(v_zero), T(v_inf)) != kairn::mul_down(T(v_zero), T(v_inf)));
    expect("mul_down with a marked operand", kairn::mul_down(kairn::unverified(T(v_three)), T(0.5) * one) == T(1.5));
    // eta/2, below the threshold: the bounds are RD(eta/2) = 0 or the number before it, and
    // RU(eta/2) = eta or the number after it. The listing steps outward, since the error term of
    // the product, rounded, is zero: -eta and eta.
    const T md = kairn::mul_down(T(v_eta), T(0.5) * one), mu = kairn::mul_up(T(v_eta), T(0.5) * one);
    expect("mul_down(eta, 1/2) is 0 or -eta", md == 0 || md == -eta);
    expect("mul_up(eta, 1/2) is eta or 2 eta", mu == eta || mu == 2 * eta);
    expect("mul_down(eta, 1/2) is -eta, as the listing steps", md == -eta);

    // ldexp and half of a ball: exact when nothing underflows, the radius grown otherwise; the
    // general scaling X * 1/2 grows the radius even for a power of two.
    const T three = v_three, r = v_r;
    const B1 p(three, r);
    const B1 hp = kairn::half(p);
    expect("half of (3, 1/4) is (3/2, 1/8), exactly", hp.center().limb[0] == T(1.5) && hp.radius() == T(0.125));
    const B1 lp = kairn::ldexp(p, -3);
    expect("ldexp((3, 1/4), -3) is (3/8, 1/32), exactly", lp.center().limb[0] == T(0.375) && lp.radius() == T(1) / 32);
    expect("(3, 1/4) * 1/2 has a larger radius than 1/8", (p * (T(0.5) * one)).radius() > T(0.125));
    const B2 q(E2(three), r);
    const B2 hq = kairn::half(q);
    expect("half of a ball of two limbs, exactly", hq.center().limb[0] == T(1.5) && hq.center().limb[1] == 0 &&
                                                        hq.radius() == T(0.125));
    expect("half with a marked operand", kairn::half(kairn::unverified(q)).radius() == T(0.125));
    expect("ldexp with a marked operand", kairn::ldexp(kairn::unverified(p), 2).radius() == 1);
    // Beyond the powers of two of T, in steps: up, exact until it overflows; down, to the point 0
    // with a radius of 2 eta; very far, the same.
    constexpr int far = std::numeric_limits<T>::max_exponent - std::numeric_limits<T>::min_exponent + 10;
    volatile int v_far = far, v_huge = 1 << 30;
    const B2 up = kairn::ldexp(kairn::ldexp(q, -int(v_far)), int(v_far));
    expect("ldexp down and back up beyond the range: the whole line or a finite ball", up.is_finite());
    const B2 big = kairn::ldexp(q, int(v_far));
    expect("ldexp far up is the whole line", big.is_whole());
    expect("ldexp very far up is the whole line", kairn::ldexp(q, int(v_huge)).is_whole());
    const B2 tiny = kairn::ldexp(q, -int(v_huge));
    expect("ldexp very far down is (0, 2 eta)", tiny.center().limb[0] == 0 && tiny.radius() == 2 * eta);
    expect("ldexp of the point 0, very far down, is the point 0", kairn::ldexp(B2(), -int(v_huge)).certainly_zero());
    expect("ldexp of the point 0, very far up, is the point 0", kairn::ldexp(B1(), int(v_huge)).certainly_zero());
    // Up in steps (2^steps is not a number of T), then down in one; down in two steps (2^-far2 is
    // not a number of T either), to values above N: exact.
    constexpr int steps = std::numeric_limits<T>::max_exponent + 5;
    const T small_c = std::ldexp(three, -10), small_r = std::ldexp(r, -10);
    const B1 s = kairn::ldexp(kairn::ldexp(B1(small_c, small_r), steps), -steps);
    expect("ldexp up in steps and down, exactly", s.center().limb[0] == small_c && s.radius() == small_r);
    constexpr int e_big = sizeof(T) == 8 ? 1000 : 100, far2 = sizeof(T) == 8 ? 1100 : 160;
    const T limbs[2] = {std::ldexp(three, e_big), std::ldexp(one, e_big - 60)};
    const B2 w(E2::from_limbs(limbs), std::ldexp(r, e_big));
    const B2 dw = kairn::ldexp(w, -far2);
    expect("ldexp down in two steps, exactly",
           dw.center().limb[0] == std::ldexp(three, e_big - far2) && dw.center().limb[1] == std::ldexp(one, e_big - 60 - far2) &&
               dw.radius() == std::ldexp(r, e_big - far2));
    const B1 sub = kairn::half(B1(T(v_eta), T(0)));
    expect("half of the point eta: the center rounded, the radius grown", sub.radius() >= eta / 2 && sub.radius() > 0);
    expect("half of the whole line", kairn::half(B1::whole()).is_whole());
    expect("half of the empty set", kairn::half(B2::empty()).is_empty());
    // The predicates at run time.
    expect("certainly_positive at run time", B2(E2(three), r).certainly_positive() && !B2(E2(three), three).certainly_positive());
    expect("certainly_negative at run time", B1(-three, r).certainly_negative() && !B1(three, r).certainly_negative());
    expect("certainly_zero at run time", B2(E2(T(v_zero)), T(v_zero)).certainly_zero());
    // The ball of a constant at run time.
    volatile long long v_den = 3;
    const B2 t = B2(kairn::rational<E2>(1, v_den));
    same_bits("the ball of 1/3, center", t.center().limb[1], C::t2.center().limb[1]);
    same_bits("the ball of 1/3, radius", t.radius(), C::t2.radius());
    volatile long long v_zero_den = 0;
    expect("the ball of 1/0 is the whole line", B2(kairn::rational<E2>(1, v_zero_den)).is_whole());
    expect("the ball of 1/0, one limb, is the whole line",
           B1(kairn::rational<kairn::Expansion<T, 1>>(1, v_zero_den)).is_whole());
}

// Intervals at run time: the constexpr functions on operands read through volatile objects give
// the values of constant evaluation (a zero can differ in sign: a guard, or a plain product there
// for a fused one here); and the arithmetic, which is not constexpr, against values computed by
// hand, the empty set, the whole line, overflow and the zero rules among them.
template <class T>
void intervals_run_time() {
    using C = Intervals<T>;
    using E2 = kairn::Expansion<T, 2>;
    using B1 = kairn::Ball<T, 1>;
    using B2 = kairn::Ball<T, 2>;
    using I1 = kairn::Interval<T, 1>;
    using I2 = kairn::Interval<T, 2>;
    constexpr T u = C::u, eta = C::eta, omega = C::omega, inf = C::inf;
    volatile T v_one = 1, v_two = 2, v_three = 3, v_four = 4, v_nan = C::nan, v_inf = inf, v_eta = eta,
               v_omega = omega, v_zero = 0, v_half_u = u / 2;
    const T one = v_one, two = v_two, three = v_three, four = v_four, nan = v_nan;
    // The constexpr functions.
    const I1 x(one, three);
    same("midpoint", x.midpoint().limb[0], I1(T(1), T(3)).midpoint().limb[0]);
    same("radius", x.radius(), I1(T(1), T(3)).radius());
    same("midpoint of [eta, eta]", I1(T(v_eta), T(v_eta)).midpoint().limb[0], eta);
    same("midpoint of [1, inf]", I1(one, T(v_inf)).midpoint().limb[0], omega);
    const T m_empty = I1(T(v_inf), -T(v_inf)).midpoint().limb[0];
    expect("midpoint of the empty set", m_empty != m_empty);
    expect("split", C::is(x.split().left, 1, 2) && C::is(x.split().right, 2, 3));
    expect("split of the whole line", C::is(I1(-T(v_inf), T(v_inf)).split().left, -inf, 0));
    expect("the constructor with a NaN bound", C::whole(I1(nan, one)) && C::whole(I2(E2(one), E2(nan))));
    expect("reversed bounds", C::empty(I1(two, one)) && C::empty(I2(two, one)) && C::empty(I1(T(v_inf))));
    expect("the hull", C::is(x.hull(I1(four, four)), 1, 4) && C::is(I1::empty().hull(x), 1, 3));
    expect("the intersection", C::is(x.intersection(I1(two, four)), 2, 3) && C::empty(x.intersection(I1(four, four))));
    expect("the negation", C::is(-x, -3, -1) && C::empty(-I1(two, one)));
    expect("a ball of an interval", B1(x).center().limb[0] == 2 && B1(x).radius() == 1 && B1(I1(one, T(v_inf))).is_whole());
    expect("the interval of a ball", C::is(I1(B1(two, one)), 1, 3) && C::empty(I1(B1::empty())));
    const B2 f = B2::from_interval(one, T(one + 2 * u));
    same_bits("from_interval, center", f.center().limb[1], C::f13.center().limb[1]);
    same_bits("from_interval, radius", f.radius(), C::f13.radius());
    same("from_interval([eta, 3 eta])", B2::from_interval(T(v_eta), T(3 * v_eta)).radius(),
         B2::from_interval(eta, 3 * eta).radius());
    expect("lower_as of a ball", B1(two, one).template lower_as<T>() == 1 && B2(E2(two), one).template upper_as<T>() == 3);
    same("the narrowing", B1(B2(E2(three), T(v_zero))).radius(), eta);
    expect("lower_as of an interval of two limbs", I2(E2(one), E2(two)).template upper_as<T>() == 2);
    // The special states, which are not constant expressions for these (Intervals says why).
    const I1 e1 = I1::empty();
    const T m_e = e1.midpoint().limb[0], r_e = e1.radius();
    expect("the midpoint and the radius of the empty set", m_e != m_e && r_e != r_e);
    expect("the split of the empty set", C::empty(e1.split().left) && C::empty(e1.split().right));
    expect("the ball of the empty set", B1(e1).is_empty() && B1(I1(T(v_inf), -T(v_inf))).is_empty());
    expect("the interval of the whole line and of the empty ball", C::whole(I1(B1::whole())) && C::empty(I1(B1::empty())));
    expect("from_interval with a NaN", B2::from_interval(nan, one).is_whole() && B2::from_interval(one, nan).is_whole());
    expect("from_interval of a half-line, of the whole line",
           B2::from_interval(one, T(v_inf)).is_whole() && B2::from_interval(-T(v_inf), T(v_inf)).is_whole());
    expect("from_interval of reversed bounds, of equal infinities", B2::from_interval(two, one).is_empty() &&
                                                                     B2::from_interval(T(v_inf), T(v_inf)).is_empty() &&
                                                                     B2::from_interval(-T(v_inf), -T(v_inf)).is_empty());
    expect("the bounds of the empty ball", B1::empty().template lower_as<T>() == inf && B1::empty().template upper_as<T>() == -inf &&
                                               B2::empty().template lower_as<T>() == inf &&
                                               B2::empty().template upper_as<T>() == -inf);
    expect("the bounds of the whole line", B1::whole().template lower_as<T>() == -inf && B1::whole().upper().limb[0] == inf &&
                                               B2::whole().template lower_as<T>() == -inf &&
                                               B2::whole().template upper_as<T>() == inf);
    expect("the narrowing of the empty set and of the whole line", B1(B2::empty()).is_empty() && B1(B2::whole()).is_whole());

    // One limb: the tightest interval of T for a sum and a difference.
    expect("[1, 2] + [3, 4]", C::is(I1(one, two) + I1(three, four), 4, 6));
    expect("[1, 2] - [3, 4]", C::is(I1(one, two) - I1(three, four), -3, -1));
    expect("[1, 2] * [3, 4]", C::is(I1(one, two) * I1(three, four), 3, 8));
    expect("[-1, 2] * [3, 4]", C::is(I1(-one, two) * I1(three, four), -4, 8));
    expect("[1, 1] + [u/2, u/2]: rounded outward", C::is(I1(one) + I1(T(v_half_u)), 1, 1 + 2 * u));
    expect("[1, 1] - [u/2, u/2]: rounded outward", C::is(I1(one) - I1(T(v_half_u)), 1 - u, 1));
    expect("[Omega, Omega] + [Omega, Omega]: [Omega, +inf]", C::is(I1(T(v_omega)) + I1(T(v_omega)), omega, inf));
    expect("[Omega, Omega] * [2, 2]: [Omega, +inf]", C::is(I1(T(v_omega)) * I1(two), omega, inf));
    expect("the empty set + X", C::empty(I1::empty() + x) && C::empty(x * I1::empty()) && C::empty(I1::empty() - I1::empty()));
    expect("the whole line + X", C::whole(I1::whole() + x) && C::whole(x * I1::whole()));
    expect("[0, 0] * the whole line is [0, 0]", C::is(I1(T(v_zero)) * I1::whole(), 0, 0));
    expect("[0, 0] * [1, +inf] is [0, 0]", C::is(I1(T(v_zero)) * I1(one, T(v_inf)), 0, 0));
    expect("[1, +inf] * [-1, 1] is the whole line", C::whole(I1(one, T(v_inf)) * I1(-one, one)));
    // eta * eta is below 2^(2p-1) eta: the bounds are RD and RU of eta^2 or one number beyond.
    const I1 tiny = I1(T(v_eta)) * I1(T(v_eta));
    expect("[eta, eta]^2", tiny.lower().limb[0] <= 0 && tiny.lower().limb[0] >= -eta && tiny.upper().limb[0] >= eta &&
                               tiny.upper().limb[0] <= 2 * eta);
    I1 acc = x;
    acc += I1(one);
    acc -= I1(two);
    acc *= I1(two);
    expect("compound assignments", C::is(acc, 0, 4));
    expect("marked operands", C::is(kairn::unverified(x) + x, 2, 6) && C::is(x - kairn::unverified(x), -2, 2));

    // Two limbs: an enclosure within about 8 u^2 (sums) and 10 u^2 (products) of the exact range,
    // not the tightest interval, but zero where the exact bound is zero.
    const I2 p{E2(one), E2(two)}, q{E2(three), E2(four)};
    const I2 s = p + q;
    expect("[1, 2] + [3, 4] contains [4, 6]", s.lower() <= E2(four) && s.upper() >= E2(T(6)));
    expect("... within 8.1 u^2 of it", E2(four) - s.lower() <= E2(T(8.1) * u * u * 4) &&
                                           s.upper() - E2(T(6)) <= E2(T(8.1) * u * u * 6));
    const I2 pr = p * q;
    expect("[1, 2] * [3, 4] contains [3, 8]", pr.lower() <= E2(three) && pr.upper() >= E2(T(8)));
    expect("... within 10.1 u^2 of it", E2(three) - pr.lower() <= E2(T(10.1) * u * u * 3) &&
                                            pr.upper() - E2(T(8)) <= E2(T(10.1) * u * u * 8));
    expect("[0, 0] + [0, 0] is [0, 0]", C::is(I2(T(v_zero)) + I2(T(v_zero)), 0, 0, 0, 0));
    expect("X - X is [0, 0] for a point X", C::is(I2(E2(three)) - I2(E2(three)), 0, 0, 0, 0));
    expect("[0, 0] * the whole line is [0, 0]", C::is(I2(T(v_zero)) * I2::whole(), 0, 0, 0, 0));
    expect("[1, 1] + [1, 1] is not [2, 2]", !C::is(I2(one) + I2(one), 2, 0, 2, 0));
    expect("the empty set and the whole line, two limbs", C::empty(I2::empty() * p) && C::whole(p + I2::whole()) &&
                                                               C::whole(I2::whole() * p) && C::empty(p - I2::empty()));
    expect("[1, +inf] * [-1, 1] is the whole line, two limbs", C::whole(I2(E2(one), E2(T(v_inf))) * I2(-one, one)));
    expect("[Omega, Omega] + [Omega, Omega]: an infinite upper bound", (I2(T(v_omega)) + I2(T(v_omega))).upper().limb[0] == inf);
    I2 acc2 = p;
    acc2 += q;
    acc2 -= q;
    acc2 *= I2(E2(two));
    expect("compound assignments, two limbs", acc2.lower() <= E2(two) && acc2.upper() >= E2(four));
    expect("marked operands, two limbs", (kairn::unverified(p) * q).upper() >= E2(T(8)));
}

// The constexpr operations computed at run time, from operands read through volatile objects, and
// the operations that are not constexpr on values whose results are known.
template <class T>
void run_time() {
    using E1 = kairn::Expansion<T, 1>;
    using E2 = kairn::Expansion<T, 2>;
    using B2 = kairn::Ball<T, 2>;
    using C = Checks<T>;
    constexpr T inf = std::numeric_limits<T>::infinity();
    volatile T v0 = C::x.limb[0], v1 = C::x.limb[1], v3 = T(3), vinf = inf, vnan = C::nan;
    const T l[2] = {v0, v1};
    const E2 x = E2::from_limbs(l);
    const E2 y = E2(T(v3)) + x;
    same("x + y", y.limb[1], C::y.limb[1]);
    same("y - x", (y - x).limb[0], (C::y - C::x).limb[0]);
    same("to_up", kairn::to_up(x), kairn::to_up(C::x));
    same("abs_upper", kairn::abs_upper(-x), kairn::abs_upper(-C::x));
    same("add_fast", kairn::add_fast(x, y).limb[1], kairn::add_fast(C::x, C::y).limb[1]);
    same("acc", (((x + x) + T(1) - T(1) + E1(T(1))) - y).limb[1], C::acc.limb[1]);
    same("E2(inf)", E2(T(vinf)).limb[1], C::einf.limb[1]);
    same("E2(nan)", E2(T(vnan)).limb[1], C::enan.limb[1]);
    volatile T vmax = std::numeric_limits<T>::max();
    same("big + big", (E2(T(vmax)) + C::big).limb[0], inf);
    same("big + big, second limb", (E2(T(vmax)) + C::big).limb[1], T(0));
    same("-big - big", (-E2(T(vmax)) - C::big).limb[0], -inf);
    same("x < E2(nan)", T(x < E2(T(vnan))), T(0));
    same("E1(nan) < a", T(E1(T(vnan)) < C::a), T(0));
    same("Ball(x, nan) whole", T(B2(x, T(vnan)).is_whole()), T(1));
    same("Ball(inf) whole", T(B2(T(vinf)).is_whole()), T(1));
    // ldexp is total: an infinity on overflow, zero below the range of T, the same in one or two
    // limbs.
    volatile int big = 4000;
    same("ldexp k = 1", kairn::ldexp(E1(T(v3)), -3).limb[0], T(0.375));
    same("ldexp k = 1, overflow", kairn::ldexp(E1(T(v3)), big).limb[0], inf);
    same("ldexp k = 1, underflow", kairn::ldexp(E1(T(v3)), -big).limb[0], T(0));
    same("ldexp k = 2, overflow", kairn::ldexp(x, big).limb[0], inf);
    same("ldexp k = 2, overflow, second limb", kairn::ldexp(x, big).limb[1], T(0));
    same("ldexp k = 2, underflow", kairn::ldexp(x, -big).limb[0], T(0));
    same("ldexp k = 2, NaN", kairn::ldexp(E2(T(vnan)), big).limb[1], C::nan);
}

}  // namespace

int main() {
    run_time<double>();
    run_time<float>();
    blocks_run_time<double>();
    blocks_run_time<float>();
    intervals_run_time<double>();
    intervals_run_time<float>();
    std::printf("%s\n", failures ? "FAILED" : "ok");
    return failures ? 1 : 0;
}
