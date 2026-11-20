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
// where a zero can differ in sign. Not yet: the products of two limbs, ldexp and half on two limbs
// and on balls, and the Ball arithmetic: their kernels have fused operations without a
// constant-evaluation variant, or their code is where KAIRN_ENCLOSURE_CODE puts it. mul_down and
// mul_up are not constexpr, by design (api.reject.not_constexpr.*); main() checks them at run time.
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
    static_assert(B2(x, inf).is_whole() && B2(x, nan).is_empty() && B1(a, nan).is_empty() && B1(T(1), T(0.5)).is_finite());
    static_assert(B2(E2(inf), T(1)).is_whole() && B2(E2(nan), T(1)).is_whole() && B2(E2(nan), nan).is_empty());
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
    same("Ball(x, nan) empty", T(B2(x, T(vnan)).is_empty()), T(1));
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
    std::printf("%s\n", failures ? "FAILED" : "ok");
    return failures ? 1 : 0;
}
