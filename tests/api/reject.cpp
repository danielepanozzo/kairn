// What must not compile. tests/api/compile_fail.cmake compiles this file once with
// KAIRN_TEST_CONTROL defined, which must succeed, and once without, which must fail with the
// expected message: the control differs only in the one thing the test is about.
//
// KAIRN_TEST_CASE selects the case:
//   0      nothing but including Kairn (for the tests of rejected compiler flags)
//   1-9    an UNVERIFIED operation written without kairn::unverified (the control adds it)
//   10     reading an error constant of an UNVERIFIED operation from kairn::traits (the control
//          reads only whether it is verified)
// Cases 1 to 10 are compiled against headers in which every kernel is marked unverified.
//   11     a non-normalized pair given to from_limbs in a constant expression, with KAIRN_CHECKS
//          (the control turns KAIRN_CHECKS off)
#if KAIRN_TEST_CASE == 11
#if defined(KAIRN_TEST_CONTROL)
#define KAIRN_CHECKS 0
#else
#define KAIRN_CHECKS 1
#endif
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
    [[maybe_unused]] E2 x(v), y(2 * v);
    [[maybe_unused]] E1 a(v), b(2 * v);
    [[maybe_unused]] B2 p(x, 0.5), q(y, 0.25);
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
#elif KAIRN_TEST_CASE == 11
    static constexpr double limbs[2] = {1.0, 0x1p-52};
    constexpr E2 z = E2::from_limbs(limbs);
    sink = z.limb[1];
#endif
    return sink == 12345 ? 1 : 0;
}
