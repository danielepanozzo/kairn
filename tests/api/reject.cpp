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
//   27-28  kairn::mul_down and kairn::mul_up in a constant expression, which they are not usable in
//          (blocks.hpp says why); the control computes the same at run time
//   32-37  intervals: an operation of intervals of one and of two limbs, an interval and a number
//          (no kernel takes one), the implicit conversions of a ball to an interval, of an
//          interval to a ball and of a ball of two limbs to one (each widens the set, so each is
//          explicit), and an interval of two limbs from one of one limb (no kernel converts); each
//          control writes what compiles instead (two intervals of one K, the interval of the
//          point, the explicit conversion, the bounds)
//   38     the sum of intervals in a constant expression, which it is not usable in (its code is
//          where KAIRN_ENCLOSURE_CODE puts it); the control computes the same at run time
//   39-41  an UNVERIFIED interval operation, constructor and conversion to a ball, written
//          without the marker, against headers in which every kernel is unverified (as 1-14)
//   29-31  an UNVERIFIED building block (two_sum, next_up) and the scaling of a ball by a power of
//          two (half), written without the marker, against headers in which every kernel is
//          marked unverified (as 1-14)
//   42-45  kairn::two_prod in a constant expression on finite operands where an operation of
//          Dekker's product, which constant evaluation runs, overflows (blocks.hpp): the partial
//          product ah bh while the product is finite (42 double, 43 float: 0x1.fffffffffffffp+511
//          squared, whose run-time error term is 0x1p+918), and the product itself, with no NaN
//          on the way (44, 45: the error term is the opposite infinity); each control is the
//          neighboring operand where it compiles, the largest square or the next number below b,
//          against the run-time result (api.constexpr checks the same bits at run time)
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
using B1 = kairn::Ball<double, 1>;
using B2 = kairn::Ball<double, 2>;
using I1 = kairn::Interval<double, 1>;
using I2 = kairn::Interval<double, 2>;

int main() {
    volatile double v = 1.5;
    // The operands are built with the marker, which every constructor accepts, so that they
    // compile against any fixture: only the case's own operation differs from the control.
    [[maybe_unused]] E2 x(kairn::unverified(double(v))), y(kairn::unverified(2 * v));
    [[maybe_unused]] E1 a(v), b(2 * v);
    [[maybe_unused]] B2 p(kairn::unverified(x), 0.5), q(kairn::unverified(y), 0.25);
    [[maybe_unused]] B1 o(kairn::unverified(a), 0.5);
    [[maybe_unused]] I1 i(kairn::unverified(double(v)), 2 * v);
    [[maybe_unused]] I2 j(kairn::unverified(x), y);
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
#elif KAIRN_TEST_CASE == 27
#if defined(KAIRN_TEST_CONTROL)
    const double z = kairn::mul_down(1.5, 3.0);
#else
    constexpr double z = kairn::mul_down(1.5, 3.0);
#endif
    sink = z;
#elif KAIRN_TEST_CASE == 28
#if defined(KAIRN_TEST_CONTROL)
    const double z = kairn::mul_up(1.5, 3.0);
#else
    constexpr double z = kairn::mul_up(1.5, 3.0);
#endif
    sink = z;
#elif KAIRN_TEST_CASE == 29
    sink = kairn::two_sum(MARK(s), s).sum;
#elif KAIRN_TEST_CASE == 30
    sink = kairn::next_up(MARK(s));
#elif KAIRN_TEST_CASE == 31
    sink = kairn::half(MARK(p)).radius();
#elif KAIRN_TEST_CASE == 32
#if defined(KAIRN_TEST_CONTROL)
    sink = (j + j).lower().limb[0];
#else
    sink = (i + j).lower().limb[0];
#endif
#elif KAIRN_TEST_CASE == 33
#if defined(KAIRN_TEST_CONTROL)
    sink = (i + I1(s)).lower().limb[0];
#else
    sink = (i + s).lower().limb[0];
#endif
#elif KAIRN_TEST_CASE == 34
#if defined(KAIRN_TEST_CONTROL)
    const I1 z(o);
#else
    const I1 z = o;
#endif
    sink = z.lower().limb[0];
#elif KAIRN_TEST_CASE == 35
#if defined(KAIRN_TEST_CONTROL)
    const B1 z(i);
#else
    const B1 z = i;
#endif
    sink = z.radius();
#elif KAIRN_TEST_CASE == 36
#if defined(KAIRN_TEST_CONTROL)
    const B1 z(p);
#else
    const B1 z = p;
#endif
    sink = z.radius();
#elif KAIRN_TEST_CASE == 37
#if defined(KAIRN_TEST_CONTROL)
    const I2 z(i.lower(), i.upper());
#else
    const I2 z(i);
#endif
    sink = z.lower().limb[0];
#elif KAIRN_TEST_CASE == 38
#if defined(KAIRN_TEST_CONTROL)
    const I1 z = I1(1.0, 2.0) + I1(3.0);
#else
    constexpr I1 z = I1(1.0, 2.0) + I1(3.0);
#endif
    sink = z.lower().limb[0];
#elif KAIRN_TEST_CASE == 39
    sink = (MARK(i) + i).lower().limb[0];
#elif KAIRN_TEST_CASE == 40
    sink = I1(MARK(s), s).lower().limb[0];
#elif KAIRN_TEST_CASE == 41
    sink = B1(MARK(i)).radius();
#elif KAIRN_TEST_CASE == 42
#if defined(KAIRN_TEST_CONTROL)
    constexpr kairn::ProductAndError<double> z = kairn::two_prod(0x1.ffffffbffffffp+511, 0x1.ffffffbffffffp+511);
    static_assert(z.product == 0x1.ffffff7ffffffp+1023 && z.error == -0x1.fffffeffffffep+969);
#else
    constexpr kairn::ProductAndError<double> z = kairn::two_prod(0x1.fffffffffffffp+511, 0x1.fffffffffffffp+511);
#endif
    sink = z.error;
#elif KAIRN_TEST_CASE == 43
#if defined(KAIRN_TEST_CONTROL)
    constexpr kairn::ProductAndError<float> z = kairn::two_prod(0x1.ffeffep+63f, 0x1.ffeffep+63f);
    static_assert(z.product == 0x1.ffdffcp+127f && z.error == 0x1.004004p+102f);
#else
    constexpr kairn::ProductAndError<float> z = kairn::two_prod(0x1.fffffep+63f, 0x1.fffffep+63f);
#endif
    sink = z.error;
#elif KAIRN_TEST_CASE == 44
#if defined(KAIRN_TEST_CONTROL)
    constexpr kairn::ProductAndError<double> z = kairn::two_prod(0x1.b07b6cd0ef55p+511, 0x1.2f11b5230d0c3p+512);
    static_assert(z.product == 0x1.fffffffffffffp+1023 && z.error == 0x1.34eafe2d76fcp+969);
#else
    constexpr kairn::ProductAndError<double> z = kairn::two_prod(0x1.b07b6cd0ef55p+511, 0x1.2f11b5230d0c4p+512);
#endif
    sink = z.error;
#elif KAIRN_TEST_CASE == 45
#if defined(KAIRN_TEST_CONTROL)
    constexpr kairn::ProductAndError<float> z = kairn::two_prod(0x1.5b8dap+63f, 0x1.7920bap+64f);
    static_assert(z.product == 0x1.fffffep+127f && z.error == 0x1.b1cc8p+102f);
#else
    constexpr kairn::ProductAndError<float> z = kairn::two_prod(0x1.5b8dap+63f, 0x1.7920bcp+64f);
#endif
    sink = z.error;
#endif
    return sink == 12345 ? 1 : 0;
}
