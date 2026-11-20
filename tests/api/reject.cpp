// What must not compile. tests/api/compile_fail.cmake compiles this file once with
// KAIRN_TEST_CONTROL defined, which must succeed, and once without, which must fail with the
// expected message: the control differs only in the one thing the test is about.
//
// KAIRN_TEST_CASE selects the case:
//   0      nothing but including Kairn (for the tests of rejected compiler flags)
//   1-9    an UNVERIFIED operation written without kairn::unverified (the control adds it)
//   10     reading an error constant of an UNVERIFIED operation from kairn::traits (the control
//          reads only whether it is verified)
//   12-14  an UNVERIFIED constructor: the narrowing to one limb, from a T, a ball from a center
// Cases 1 to 14 are compiled against headers in which every kernel is marked unverified.
//   20-26  one kernel UNVERIFIED and every other proved: the operation must not compile through a
//          conversion to another kernel (x + a through x + Expansion(a) and add_2_2_full, a ball
//          times a T through a point ball and ball_mul_2_full, a comparison with a limb through a
//          two-limb one); the control marks the operand
//   11     a pair that is not canonical given to from_limbs in a constant expression, with
//          KAIRN_CHECKS (the control turns KAIRN_CHECKS off)
//   15     the same for an operator given a pair that is not canonical, written into its limbs
//   16     the same for a Ball constructor given a negative radius
//   17     kairn::rational with a zero denominator in a constant expression (the control: 3)
//   18     kairn::rational in a constant expression, against a copy of the headers in which its
//          result is wrong (compile_fail.cmake, RATIONAL_FAULT_FIXTURE): its check refuses it (the
//          control turns KAIRN_RATIONAL_CHECK off)
#if KAIRN_TEST_CASE == 11 || KAIRN_TEST_CASE == 15 || KAIRN_TEST_CASE == 16
#if defined(KAIRN_TEST_CONTROL)
#define KAIRN_CHECKS 0
#else
#define KAIRN_CHECKS 1
#endif
#endif
#if KAIRN_TEST_CASE == 18 && defined(KAIRN_TEST_CONTROL)
#define KAIRN_RATIONAL_CHECK 0
#endif
#include <kairn/kairn.hpp>

#if defined(KAIRN_TEST_CONTROL)
#define MARK(x) kairn::unverified(x)
#else
#define MARK(x) (x)
#endif

using E1 = kairn::Expansion<double, 1>;
using E2 = kairn::Expansion<double, 2>;
using B2 = kairn::Ball<double, 2>;

int main() {
    volatile double v = 1.5;
    // The operands are built with the marker, which every constructor accepts, so that they
    // compile against any fixture: only the case's own operation differs from the control.
    [[maybe_unused]] E2 x(kairn::unverified(double(v))), y(kairn::unverified(2 * v));
    [[maybe_unused]] E1 a(v), b(2 * v);
    [[maybe_unused]] B2 p(kairn::unverified(x), 0.5), q(kairn::unverified(y), 0.25);
    [[maybe_unused]] double s = v;
    double sink = 0;
#if KAIRN_TEST_CASE == 1
    sink = (MARK(x) - y).limb[0];
#elif KAIRN_TEST_CASE == 2
    sink = MARK(x) < y;
#elif KAIRN_TEST_CASE == 3
    sink = (-MARK(x)).limb[0];
#elif KAIRN_TEST_CASE == 4
    sink = kairn::to_down(MARK(x));
#elif KAIRN_TEST_CASE == 5
    sink = (MARK(a) + b).limb[0];
#elif KAIRN_TEST_CASE == 6
    sink = (MARK(p) + q).radius();
#elif KAIRN_TEST_CASE == 7
    x -= MARK(y);
#elif KAIRN_TEST_CASE == 8
    sink = kairn::ldexp(MARK(x), 3).limb[0];
#elif KAIRN_TEST_CASE == 9
    sink = (MARK(p) * 2.0).radius();
#elif KAIRN_TEST_CASE == 10
#if defined(KAIRN_TEST_CONTROL)
    sink = kairn::traits<E2>::sub.verified ? 1 : 0;
#else
    sink = kairn::traits<E2>::sub.unit;
#endif
#elif KAIRN_TEST_CASE == 12
    sink = E1(MARK(x)).limb[0];
#elif KAIRN_TEST_CASE == 13
    sink = E2(MARK(s)).limb[0];
#elif KAIRN_TEST_CASE == 14
    sink = B2(MARK(x), 0.5).radius();
#elif KAIRN_TEST_CASE == 20
    sink = (x + MARK(s)).limb[0];
#elif KAIRN_TEST_CASE == 21
    sink = (x + MARK(a)).limb[0];
#elif KAIRN_TEST_CASE == 22
    sink = (MARK(s) - x).limb[0];
#elif KAIRN_TEST_CASE == 23
    sink = (x * MARK(s)).limb[0];
#elif KAIRN_TEST_CASE == 24
    sink = (p * MARK(s)).radius();
#elif KAIRN_TEST_CASE == 25
    sink = (p + MARK(s)).radius();
#elif KAIRN_TEST_CASE == 26
    sink = x < MARK(s);
#elif KAIRN_TEST_CASE == 11
    static constexpr double limbs[2] = {1.0, 0x1p-52};
    constexpr E2 z = E2::from_limbs(limbs);
    sink = z.limb[1];
#elif KAIRN_TEST_CASE == 15
    constexpr E2 z = [] {
        E2 w;
        w.limb[0] = 1.0;
        w.limb[1] = 0x1p-52;
        return kairn::unverified(w) + w;
    }();
    sink = z.limb[1];
#elif KAIRN_TEST_CASE == 16
    constexpr B2 z(kairn::unverified(E2(kairn::unverified(1.0))), -0.5);
    sink = z.radius();
#elif KAIRN_TEST_CASE == 17
#if defined(KAIRN_TEST_CONTROL)
    constexpr kairn::Constant<E2> z = kairn::rational<E2>(1, 3);
#else
    constexpr kairn::Constant<E2> z = kairn::rational<E2>(1, 0);
#endif
    sink = z.error;
#elif KAIRN_TEST_CASE == 18
    constexpr kairn::Constant<E2> z = kairn::rational<E2>(1, 3);
    sink = z.error;
#endif
    return sink == 12345 ? 1 : 0;
}
