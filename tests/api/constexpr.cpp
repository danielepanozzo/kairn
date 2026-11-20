// Compile-time tests of the public interface: everything that is constexpr is evaluated in a
// static_assert, for double and float, and main() checks that the same expressions computed at run
// time, on operands the compiler cannot see, give the same limbs. Also: the types are regular value
// types, the unmarked operations exist exactly when gen/claims.json says the kernel they call is
// proved, and kairn::traits exports constants exactly for those.
//
// What is constexpr: construction (make_2, make_2_limbs, ball_make_1, ball_make_2), the sums and
// differences of two limbs (the full kernels of the additions), negation and absolute value, the
// comparisons and conversions, everything of one limb, a ball's negation, states and constants.
// Not yet: the products of two limbs, ldexp and half on two limbs, and the Ball arithmetic, whose
// kernels have fused operations without a constant-evaluation variant.
//
// The comparisons are evaluated with NaN operands too: one compiler's constant evaluator takes
// a < b for true when an operand is a NaN, so every comparison that can run in constant evaluation
// is written b > a or b >= a, generated or not, and these asserts are what shows it.
#include <kairn/kairn.hpp>

#include <array>
#include <cstdio>
#include <limits>
#include <type_traits>

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

int failures = 0;

template <class T>
void same(const char* what, T run_time, T compile_time) {
    if (!(run_time == compile_time || (run_time != run_time && compile_time != compile_time))) {
        std::printf("differs at run time: %s (%a against %a)\n", what, double(run_time), double(compile_time));
        ++failures;
    }
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
    std::printf("%s\n", failures ? "FAILED" : "ok");
    return failures ? 1 : 0;
}
