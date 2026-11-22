// api.platform_macros: Kairn's headers after a platform header that defines common words as
// macros. <windows.h> defines min and max as function-like macros unless NOMINMAX is defined, and
// through its RPC headers `small` as `char`, `hyper` as `__int64`, `near` and `far` as nothing,
// and `interface` as `struct`; a program that includes it first, as most Windows programs do,
// must still be able to include Kairn. On Windows this includes the real header; on every
// platform it defines those macros itself, so the test runs everywhere. It compiles, uses the
// public operations and the self-test, and checks one result.
#if defined(_WIN32)
#include <windows.h>
#endif

#if !defined(min)
#define min(a, b) (((a) < (b)) ? (a) : (b))
#endif
#if !defined(max)
#define max(a, b) (((a) > (b)) ? (a) : (b))
#endif
#if !defined(small)
#define small char
#endif
#if !defined(hyper)
#define hyper long long
#endif
#if !defined(near)
#define near
#endif
#if !defined(far)
#define far
#endif
#if !defined(interface)
#define interface struct
#endif

#include <kairn/kairn.hpp>
#include <kairn/packed.hpp>
#include <kairn/soa.hpp>
#include <kairn/ball_vector.hpp>

#include <cstdio>

template <class T>
static int run() {
    using E1 = kairn::Expansion<T, 1>;
    using E2 = kairn::Expansion<T, 2>;
    using B1 = kairn::Ball<T, 1>;
    using B2 = kairn::Ball<T, 2>;
    const E2 x = E2(T(1)) + T(0.5);
    const E2 y = x * x - x;  // 1.5 * 1.5 - 1.5 = 0.75, exactly
    const E1 a = E1(T(3)) * E1(T(0.25));
    const E2 z = kairn::ldexp(x, 3);  // 12
    const B1 p = B1(E1(T(1)), T(0.5)) + B1(E1(T(2)), T(0.25));
    const B2 q = B2(x, T(0.125)) * B2(x, T(0));
    constexpr kairn::Constant<E2> third = kairn::rational<E2>(1, 3);
    volatile long long three = 3;
    const kairn::Constant<E2> third_at_run_time = kairn::rational<E2>(1, three);
    // The building blocks and the new operations of a ball, whose names are none of the macros'.
    const kairn::SumAndError<T> s = kairn::two_sum(T(1), T(0.5));
    const kairn::ProductAndError<T> pe = kairn::two_prod(T(3), T(0.25));
    const T bounds = kairn::add_down(T(1), T(0.5)) + kairn::add_up(T(1), T(0.5)) + kairn::sub_down(T(1), T(0.5)) +
                     kairn::sub_up(T(1), T(0.5)) + kairn::mul_down(T(3), T(0.25)) + kairn::mul_up(T(3), T(0.25));
    const bool radii = kairn::radd(T(1), T(0.5)) == kairn::next_up(T(1.5)) &&
                       kairn::rmul(T(3), T(0.25)) == kairn::next_up(T(0.75)) &&
                       kairn::next_down(kairn::next_up(T(2))) == T(2);
    const B2 h = kairn::half(B2(third));
    const B1 l = kairn::ldexp(B1(E1(T(3)), T(0.5)), -1);
    int failures = 0;
    if (s.sum != T(1.5) || s.error != 0 || E2(kairn::fast_two_sum(T(1), T(0.5))).limb[0] != T(1.5) ||
        pe.product != T(0.75) || pe.error != 0 || bounds != T(5.5) || !radii)
        ++failures;
    if (!h.certainly_positive() || h.certainly_negative() || l.center().limb[0] != T(1.5) || l.radius() != T(0.25) ||
        B1().certainly_zero() == false)
        ++failures;
    if (third_at_run_time.value.limb[0] != third.value.limb[0] || third_at_run_time.error != third.error ||
        third.exact || !kairn::is_rational_result(third, 1, 3) || !kairn::integer<E1>(-7).exact)
        ++failures;
    // Intervals, and the functions of a ball of the interface the two share.
    using I1 = kairn::Interval<T, 1>;
    using I2 = kairn::Interval<T, 2>;
    const I1 u = (I1(T(1), T(2)) + I1(T(3))) * I1(T(2)) - I1(T(1));  // [7, 9]
    const I2 w = I2(T(1), T(2)) * I2(T(3), T(4));                    // about [3, 8]
    const kairn::Split<I1> halves = u.split();
    if (u.lower().limb[0] != T(7) || u.upper().limb[0] != T(9) || u.midpoint().limb[0] != T(8) || u.radius() != T(1) ||
        halves.left.upper().limb[0] != T(8) || (-u).lower().limb[0] != T(-9) ||
        u.hull(I1(T(0))).lower().limb[0] != T(0) || u.intersection(I1(T(8), T(20))).lower().limb[0] != T(8))
        ++failures;
    if (!(w.template lower_as<T>() <= T(3)) || !(w.template upper_as<T>() >= T(8)) || B1(u).radius() != T(1) ||
        I1(B1(T(2), T(1))).upper().limb[0] != T(3) || kairn::Ball<T, 2>::from_interval(T(1), T(3)).radius() != T(1) ||
        B1(B2(T(3))).center().limb[0] != T(3) || B1(T(2), T(1)).template lower_as<T>() != T(1))
        ++failures;
    // Packed and an array of numbers, whose names are none of the macros' either.
    kairn::SoA<T, 2> arr(std::size_t(kairn::Packed<T, 2>::lanes), x);
    const kairn::Packed<T, 2> px = arr.load(0) * kairn::Packed<T, 1>::broadcast(E1(T(2)));
    arr.store(0, px);
    if (arr.get(0).limb[0] != T(3) || !kairn::all(px == kairn::Packed<T, 2>::broadcast(E2(T(3))))) ++failures;
    // Ball vectors, whose names are none of the macros' either.
    using BV = kairn::BallVector<T, 2, 3>;
    const BV bx({x, y, z}, T(0.5));
    const BV by = kairn::half(bx + bx) - kairn::axpy(T(2), bx, bx) * T(0.25);
    T cs[3] = {T(1), T(2), T(4)}, cr = T(0);
    const kairn::BallVectorView<T, 1> bv(kairn::SoAView<T, 1>(cs, 3), cr);
    kairn::ldexp(bv, -1, bv);
    if (!by.is_finite() || cs[2] != T(2) || cr != T(0) ||
        kairn::convolution(bx, BV::whole()).is_finite() || !(kairn::norm_upper(bx) >= T(12)))
        ++failures;
    if (y.limb[0] != T(0.75) || y.limb[1] != T(0)) ++failures;
    if (a.limb[0] != T(0.75)) ++failures;
    if (z.limb[0] != T(12) || z.limb[1] != T(0)) ++failures;
    if (!p.is_finite() || !(p.radius() >= T(0.75))) ++failures;
    if (!q.is_finite() || !(q.radius() >= T(0.1875))) ++failures;
    return failures;
}

int main() {
    int failures = run<double>() + run<float>();
    const kairn::Status status = kairn::self_test();
    if (!status) {
        std::printf("api.platform_macros: the self-test: %s\n", status.message());
        ++failures;
    }
    if (!kairn::environment_ok()) ++failures;
    std::printf("api.platform_macros: %s\n", failures ? "FAILED" : "ok");
    return failures ? 1 : 0;
}
