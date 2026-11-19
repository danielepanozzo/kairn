// Compile-time tests of the public interface: everything that is constexpr is evaluated in a
// static_assert, for double and float, and main() checks that the same expressions computed at run
// time, on operands the compiler cannot see, give the same limbs. Also: the types are regular value
// types, the unmarked operations exist exactly when gen/claims.json says their kernel is proved,
// and kairn::traits exports constants exactly for those.
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

    // Regular value types (the brief, "API for generic clients").
    static_assert(std::is_trivially_copyable_v<E1> && std::is_trivially_copyable_v<E2>);
    static_assert(std::is_standard_layout_v<E1> && std::is_standard_layout_v<E2>);
    static_assert(sizeof(E1) == sizeof(T) && sizeof(E2) == 2 * sizeof(T));
    static_assert(std::is_trivially_copyable_v<B1> && std::is_trivially_copyable_v<B2>);
    static_assert(std::is_standard_layout_v<B2> && sizeof(B2) == 3 * sizeof(T));
    static_assert(std::is_convertible_v<T, E2> && std::is_convertible_v<E1, E2>);
    static_assert(!std::is_convertible_v<E2, E1> && std::is_constructible_v<E1, E2>);

    // Construction.
    static constexpr E2 zero{};
    static_assert(zero.limb[0] == 0 && zero.limb[1] == 0);
    static constexpr T limbs[2] = {T(1), u / 2};
    static constexpr E2 x = E2::from_limbs(limbs);
    static_assert(x.limb[0] == 1 && x.limb[1] == u / 2 && kairn::is_normalized(x));
    static_assert(E2(E1(T(3))).limb[0] == 3 && E2(T(3)).limb[1] == 0);
    static_assert(E1(x).limb[0] == 1);
    static constexpr T inf = std::numeric_limits<T>::infinity();
    static constexpr T nan = std::numeric_limits<T>::quiet_NaN();
    static_assert(E2(inf).limb[1] == 0 && E2(-inf).limb[0] == -inf);
    static_assert(E2(nan).limb[0] != E2(nan).limb[0] && E2(nan).limb[1] != E2(nan).limb[1]);

    // Two limbs, proved operations without the marker.
    static constexpr E2 y = E2(T(3)) + x;   // 4 + u/2
    static_assert(y.limb[0] == 4 && y.limb[1] == u / 2);
    static_assert((x + T(2)).limb[0] == 3 && (T(2) + x).limb[1] == u / 2);
    static constexpr E2 acc = [] {
        E2 a = x;
        a += x;
        a += T(1);
        return a;
    }();
    static_assert(acc.limb[0] == 3 && acc.limb[1] == u);

    // Two limbs, the operations that need the marker today, all constexpr.
    static_assert((unverified(y) - x).limb[0] == 3 && (unverified(y) - x).limb[1] == 0);
    static_assert((y - unverified(T(4))).limb[0] == u / 2 && (T(5) - unverified(y)).limb[0] == 1);
    static_assert((-unverified(x)).limb[0] == -1 && kairn::abs(unverified(-unverified(x))).limb[1] == u / 2);
    static_assert(kairn::add_fast(unverified(x), x).limb[0] == 2);
    static_assert([] {
        E2 a = y;
        a -= unverified(x);
        a -= unverified(T(1));
        return a.limb[0] == 2 && a.limb[1] == 0;
    }());
    static_assert(unverified(x) < y && y > unverified(x) && !(unverified(y) < x));
    static_assert(unverified(x) <= x && unverified(x) >= x && unverified(x) == x && !(unverified(x) != x));
    static_assert(unverified(x) > T(1) && T(1) < unverified(x) && unverified(x) >= T(1) && !(unverified(x) <= T(1)));
    static_assert(T(2) > unverified(x) && T(2) >= unverified(x) && unverified(x) != T(1) && !(T(1) == unverified(x)));
    static_assert(unverified(E2(T(1))) == T(1));
    static_assert(kairn::to_nearest(unverified(x)) == 1 && kairn::to_down(unverified(x)) == 1);
    static_assert(kairn::to_up(unverified(x)) == 1 + 2 * u && kairn::abs_upper(unverified(-unverified(x))) == 1 + 2 * u);
    static_assert(kairn::sign(x) == 1 && kairn::sign(-unverified(x)) == -1 && kairn::sign(zero) == 0);
    static_assert(kairn::isfinite(x) && !kairn::isfinite(E2(inf)) && !kairn::is_normalized(E2(nan)));
    // (1, u) is normalized (1 + u is a tie, and 1 is even); (1, 2u) is not.
    static_assert(kairn::is_normalized(E2::from_limbs_unchecked(std::array<T, 2>{T(1), u}.data())));
    static_assert(!kairn::is_normalized(E2::from_limbs_unchecked(std::array<T, 2>{T(1), 2 * u}.data())));

    // Mixed numbers of limbs: the one-limb operand is widened.
    static_assert((x + E1(T(1))).limb[0] == 2 && (E1(T(1)) + x).limb[1] == u / 2);
    static_assert((unverified(x) - E1(T(1))).limb[0] == u / 2 && unverified(E1(T(1))) < x);

    // One limb: each operation is the operation of T.
    static constexpr E1 a{T(3)}, b{T(4)};
    static_assert((unverified(a) + b).limb[0] == 7 && (unverified(a) - b).limb[0] == -1);
    static_assert((unverified(a) * b).limb[0] == 12 && (a * unverified(T(2))).limb[0] == 6);
    static_assert((T(1) + unverified(E1(u))).limb[0] == 1);   // rounded, ties to even
    static_assert(kairn::add_fast(unverified(a), b).limb[0] == 7);
    static_assert(kairn::ldexp(unverified(a), -1).limb[0] == T(1.5) && kairn::half(unverified(b)).limb[0] == 2);
    static_assert([] {
        E1 c = a;
        c += unverified(b);
        c *= unverified(T(2));
        c -= unverified(E1(T(1)));
        return c.limb[0] == 13;
    }());
    static_assert((-a).limb[0] == -3 && kairn::abs(-a).limb[0] == 3 && a < b && b > a && a <= a && a != b);
    static_assert(a == T(3) && T(3) == a && a < T(4));
    static_assert(kairn::to_nearest(a) == 3 && kairn::to_down(a) == 3 && kairn::to_up(a) == 3 && kairn::abs_upper(-a) == 3);

    // Balls: construction, accessors, and the negation, the one constexpr kernel.
    static constexpr B2 p{x, u};
    static_assert(p.center().limb[1] == u / 2 && p.radius() == u && B2(T(2)).radius() == 0);
    static_assert((-unverified(p)).center().limb[0] == -1 && (-unverified(p)).radius() == u);
    static_assert((-unverified(B1(a))).center().limb[0] == -3);

    // The unmarked forms exist exactly when the kernel is proved.
    static_assert(can_add<E2, E2> == bounds::add_2_2<T>::proved && can_add<E2, T> == bounds::add_2_1<T>::proved);
    static_assert(can_sub<E2, E2> == bounds::sub_2_2<T>::proved && can_sub<E2, T> == bounds::sub_2_1<T>::proved);
    static_assert(can_sub<T, E2> == bounds::sub_1_2<T>::proved);
    static_assert(can_mul<E2, E2> == bounds::mul_2_2<T>::proved && can_mul<T, E2> == bounds::mul_2_1<T>::proved);
    static_assert(can_less<E2, E2> == bounds::lt_2_2<T>::proved && can_less<E2, T> == bounds::lt_2_1<T>::proved);
    static_assert(can_negate<E2> == bounds::neg_2<T>::proved && can_to_down<E2> == bounds::to_down_2<T>::proved);
    static_assert(can_add<E1, E1> == bounds::add_1_1<T>::proved && can_mul<E1, T> == bounds::mul_1_1<T>::proved);
    static_assert(can_add<B2, B2> == bounds::ball_add_2<T>::proved && can_mul<B1, T> == bounds::ball_scale_1<T>::proved);
    static_assert(can_negate<B2> == bounds::ball_neg_2<T>::proved);
    // Exact operations without a kernel need no marker.
    static_assert(can_negate<E1> && can_less<E1, E1> && can_to_down<E1>);
    // With the marker, everything exists.
    static_assert(can_sub<kairn::Unverified<E2>, E2> && can_less<T, kairn::Unverified<E2>> && can_negate<kairn::Unverified<B2>>);
    // A marked left operand of a compound assignment would modify a copy: it does not compile.
    static_assert(!requires(kairn::Unverified<E2> m, E2 e) { m += e; });

    // traits: constants for proved kernels only, and the values of gen/bounds.hpp.
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

// The constexpr operations computed at run time, from operands read through volatile objects.
template <class T>
void run_time() {
    using E2 = kairn::Expansion<T, 2>;
    using C = Checks<T>;
    volatile T v0 = C::x.limb[0], v1 = C::x.limb[1], v3 = T(3);
    const T l[2] = {v0, v1};
    const E2 x = E2::from_limbs(l);
    const E2 y = E2(T(v3)) + x;
    same("x + y", y.limb[1], C::y.limb[1]);
    same("y - x", (unverified(y) - x).limb[0], (unverified(C::y) - C::x).limb[0]);
    same("to_up", kairn::to_up(unverified(x)), kairn::to_up(unverified(C::x)));
    same("abs_upper", kairn::abs_upper(unverified(-unverified(x))), kairn::abs_upper(unverified(-unverified(C::x))));
    same("add_fast", kairn::add_fast(unverified(x), y).limb[1], kairn::add_fast(unverified(C::x), C::y).limb[1]);
    same("ldexp k = 1", kairn::ldexp(unverified(kairn::Expansion<T, 1>(T(v3))), -3).limb[0], T(0.375));
    // Outside the exponents of T, ldexp returns NaN (not a constant expression on Clang, whose
    // constant evaluator refuses arithmetic that produces a NaN).
    volatile int big = 4000;
    same("ldexp k = 1, n too large", kairn::ldexp(unverified(kairn::Expansion<T, 1>(T(v3))), big).limb[0],
         std::numeric_limits<T>::quiet_NaN());
    same("ldexp k = 2, n too small", kairn::ldexp(unverified(x), -big).limb[0], std::numeric_limits<T>::quiet_NaN());
}

}  // namespace

int main() {
    run_time<double>();
    run_time<float>();
    std::printf("%s\n", failures ? "FAILED" : "ok");
    return failures ? 1 : 0;
}
