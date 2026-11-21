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
//   42-47  the containers (soa.hpp): writing through a view of const limbs (an element, set,
//          store), a view of mutable limbs from a view of const ones and from a const SoA, and an
//          element of a view of const limbs assigned from another; each control does the same
//          through a mutable view, or makes the view of const limbs
//   48-51  Packed (packed.hpp): an operation with a number or a T operand (no packed form takes
//          one), the narrowing of two limbs to one written as an implicit conversion, and an
//          operation of two limb types; each control writes what compiles instead
//   53     the arithmetic of Packed<T, 1>, which there is none of (its kernels are not entry
//          kernels); the control negates, and adds a Packed<T, 1> to a Packed<T, 2>
//   52     nothing but including packed.hpp and soa.hpp, with -DKAIRN_PACKED_FORM= a value that
//          is not a form, or a form the target does not have (the generated header's #error)
//   70-81  the enclosure interface (headers-pred): a Trit as a bool, in a condition and in an
//          initialization (a three-valued answer converts to no bool: the controls write
//          kairn::certainly and kairn::possibly); a comparison operator of intervals and of balls
//          (there is none: the controls call the three-valued functions); a comparison of intervals
//          of one and of two limbs, and of an interval and a ball; an interval's contains of a
//          ball, and of an interval of the other number of limbs; a relation of IEEE 1788 of balls
//          (there is none: the control is contains); the implicit conversions between Interval<T,
//          2> and Ball<T, 2> (each widens the set); the hull of balls of one and of two limbs; each
//          control writes what compiles instead
//   82-88  an UNVERIFIED comparison, subset test, hull of balls, relation of IEEE 1788, ball from
//          an interval of two T, member test and conversion of two limbs, written without the
//          marker, against headers in which every kernel is unverified (as 1-14)
//   89-92  one kernel of a member test UNVERIFIED and every other proved (interval_contains_1,
//          interval_contains_2, ball_contains_point_1, ball_contains_point_2): contains(t) of a
//          point of T must not compile through the set of the point, contains(Interval(t)), whose
//          kernel is another and whose answer differs on an infinite point; the control marks t
//   29-31  an UNVERIFIED building block (two_sum, next_up) and the scaling of a ball by a power of
//          two (half), written without the marker, against headers in which every kernel is
//          marked unverified (as 1-14)
//   93-96  kairn::two_prod in a constant expression on finite operands where an operation of
//          Dekker's product, which constant evaluation runs, overflows (blocks.hpp): the partial
//          product ah bh while the product is finite (93 double, 94 float: 0x1.fffffffffffffp+511
//          squared, whose run-time error term is 0x1p+918), and the product itself, with no NaN
//          on the way (95, 96: the error term is the opposite infinity); each control is the
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
// The headers that kairn.hpp does not include, in the cases about them only: each case is compiled
// twice, and they would add their cost to every one.
#if KAIRN_TEST_CASE >= 42 && KAIRN_TEST_CASE <= 53
#include <kairn/packed.hpp>
#include <kairn/soa.hpp>
#endif

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
#elif (KAIRN_TEST_CASE >= 42 && KAIRN_TEST_CASE <= 51) || KAIRN_TEST_CASE == 53
    double h[4] = {1, 2, 3, 4}, l[4] = {0, 0, 0, 0};
    const kairn::SoAView<double, 2> mv(h, l, 4);
    [[maybe_unused]] const kairn::SoAView<const double, 2> cv = mv;
    using P1 = kairn::Packed<double, 1>;
    using P2 = kairn::Packed<double, 2>;
    [[maybe_unused]] const P2 px = P2::load(h, l);
    [[maybe_unused]] const P1 pa = P1::load(h);
#if KAIRN_TEST_CASE == 42
#if defined(KAIRN_TEST_CONTROL)
    mv[0] = E2(kairn::unverified(2.0));
#else
    cv[0] = E2(kairn::unverified(2.0));
#endif
#elif KAIRN_TEST_CASE == 43
#if defined(KAIRN_TEST_CONTROL)
    mv.set(1, E2(kairn::unverified(2.0)));
#else
    cv.set(1, E2(kairn::unverified(2.0)));
#endif
#elif KAIRN_TEST_CASE == 44
#if defined(KAIRN_TEST_CONTROL)
    mv.store(0, px);
#else
    cv.store(0, px);
#endif
#elif KAIRN_TEST_CASE == 45
#if defined(KAIRN_TEST_CONTROL)
    const kairn::SoAView<const double, 2> w = mv;
#else
    const kairn::SoAView<double, 2> w = cv;
#endif
    sink = double(w.size());
#elif KAIRN_TEST_CASE == 46
    const kairn::SoA<double, 2> owned(4);
#if defined(KAIRN_TEST_CONTROL)
    const kairn::SoAView<const double, 2> w = owned;
#else
    const kairn::SoAView<double, 2> w = owned;
#endif
    sink = double(w.size());
#elif KAIRN_TEST_CASE == 47
#if defined(KAIRN_TEST_CONTROL)
    mv[0] = mv[1];
#else
    cv[0] = cv[1];
#endif
#elif KAIRN_TEST_CASE == 48
#if defined(KAIRN_TEST_CONTROL)
    sink = (px + P2::broadcast(x)).lane(0).limb[0];
#else
    sink = (px + x).lane(0).limb[0];
#endif
#elif KAIRN_TEST_CASE == 49
#if defined(KAIRN_TEST_CONTROL)
    sink = (px * P1::broadcast(E1(2.0))).lane(0).limb[0];
#else
    sink = (px * 2.0).lane(0).limb[0];
#endif
#elif KAIRN_TEST_CASE == 50
#if defined(KAIRN_TEST_CONTROL)
    const P1 z(px);
#else
    const P1 z = px;
#endif
    sink = z.lane(0).limb[0];
#elif KAIRN_TEST_CASE == 53
#if defined(KAIRN_TEST_CONTROL)
    sink = (-pa).lane(0).limb[0] + (P2(pa) + pa).lane(0).limb[0];
#else
    sink = (pa + pa).lane(0).limb[0];
#endif
#elif KAIRN_TEST_CASE == 51
    const kairn::Packed<float, 2> pf;
#if defined(KAIRN_TEST_CONTROL)
    sink = (px + px).lane(0).limb[0] + double((pf + pf).lane(0).limb[0]);
#else
    sink = (px + pf).lane(0).limb[0];
#endif
#endif
// The enclosure interface of stage B2 (headers-pred): cases 70 to 81 against the headers as they
// are, 82 to 88 against the copy in which every kernel is unverified, 89 to 92 against a copy in
// which one kernel is.
#elif KAIRN_TEST_CASE == 70
#if defined(KAIRN_TEST_CONTROL)
    if (kairn::certainly(kairn::less(i, i))) sink = 1;
#else
    if (kairn::less(i, i)) sink = 1;
#endif
#elif KAIRN_TEST_CASE == 71
#if defined(KAIRN_TEST_CONTROL)
    const bool c = kairn::possibly(kairn::less(o, o));
#else
    const bool c = kairn::less(o, o);
#endif
    sink = c;
#elif KAIRN_TEST_CASE == 72
#if defined(KAIRN_TEST_CONTROL)
    sink = kairn::certainly(kairn::less(i, i));
#else
    sink = i < i;
#endif
#elif KAIRN_TEST_CASE == 73
#if defined(KAIRN_TEST_CONTROL)
    sink = kairn::certainly(kairn::equal(p, q));
#else
    sink = p == q;
#endif
#elif KAIRN_TEST_CASE == 74
#if defined(KAIRN_TEST_CONTROL)
    sink = int(kairn::less(j, j));
#else
    sink = int(kairn::less(i, j));
#endif
#elif KAIRN_TEST_CASE == 75
#if defined(KAIRN_TEST_CONTROL)
    sink = int(kairn::less(i, I1(o)));
#else
    sink = int(kairn::less(i, o));
#endif
#elif KAIRN_TEST_CASE == 76
#if defined(KAIRN_TEST_CONTROL)
    sink = i.contains(I1(o));
#else
    sink = i.contains(o);
#endif
#elif KAIRN_TEST_CASE == 77
#if defined(KAIRN_TEST_CONTROL)
    sink = o.contains(o);
#else
    sink = kairn::ieee1788::subset(o, o);
#endif
#elif KAIRN_TEST_CASE == 78
#if defined(KAIRN_TEST_CONTROL)
    const B2 z(j);
#else
    const B2 z = j;
#endif
    sink = z.radius();
#elif KAIRN_TEST_CASE == 79
#if defined(KAIRN_TEST_CONTROL)
    const I2 z(p);
#else
    const I2 z = p;
#endif
    sink = z.lower().limb[0];
#elif KAIRN_TEST_CASE == 80
#if defined(KAIRN_TEST_CONTROL)
    sink = o.hull(B1(p)).radius();
#else
    sink = o.hull(p).radius();
#endif
#elif KAIRN_TEST_CASE == 81
#if defined(KAIRN_TEST_CONTROL)
    sink = j.contains(j);
#else
    sink = i.contains(j);
#endif
#elif KAIRN_TEST_CASE == 82
    sink = int(kairn::less(MARK(i), i));
#elif KAIRN_TEST_CASE == 83
    sink = i.contains(MARK(i));
#elif KAIRN_TEST_CASE == 84
    sink = p.hull(MARK(q)).radius();
#elif KAIRN_TEST_CASE == 85
    sink = kairn::ieee1788::disjoint(MARK(i), i);
#elif KAIRN_TEST_CASE == 86
    sink = B1::from_interval(MARK(s), s).radius();
#elif KAIRN_TEST_CASE == 87
    sink = int(kairn::member(MARK(s), o));
#elif KAIRN_TEST_CASE == 88
    sink = B2(MARK(j)).radius();
#elif KAIRN_TEST_CASE == 89 || KAIRN_TEST_CASE == 90
    sink = i.contains(MARK(s)) + j.contains(MARK(s));
#elif KAIRN_TEST_CASE == 91 || KAIRN_TEST_CASE == 92
    sink = o.contains(MARK(s)) + p.contains(MARK(s));
#elif KAIRN_TEST_CASE == 93
#if defined(KAIRN_TEST_CONTROL)
    constexpr kairn::ProductAndError<double> z = kairn::two_prod(0x1.ffffffbffffffp+511, 0x1.ffffffbffffffp+511);
    static_assert(z.product == 0x1.ffffff7ffffffp+1023 && z.error == -0x1.fffffeffffffep+969);
#else
    constexpr kairn::ProductAndError<double> z = kairn::two_prod(0x1.fffffffffffffp+511, 0x1.fffffffffffffp+511);
#endif
    sink = z.error;
#elif KAIRN_TEST_CASE == 94
#if defined(KAIRN_TEST_CONTROL)
    constexpr kairn::ProductAndError<float> z = kairn::two_prod(0x1.ffeffep+63f, 0x1.ffeffep+63f);
    static_assert(z.product == 0x1.ffdffcp+127f && z.error == 0x1.004004p+102f);
#else
    constexpr kairn::ProductAndError<float> z = kairn::two_prod(0x1.fffffep+63f, 0x1.fffffep+63f);
#endif
    sink = z.error;
#elif KAIRN_TEST_CASE == 95
#if defined(KAIRN_TEST_CONTROL)
    constexpr kairn::ProductAndError<double> z = kairn::two_prod(0x1.b07b6cd0ef55p+511, 0x1.2f11b5230d0c3p+512);
    static_assert(z.product == 0x1.fffffffffffffp+1023 && z.error == 0x1.34eafe2d76fcp+969);
#else
    constexpr kairn::ProductAndError<double> z = kairn::two_prod(0x1.b07b6cd0ef55p+511, 0x1.2f11b5230d0c4p+512);
#endif
    sink = z.error;
#elif KAIRN_TEST_CASE == 96
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
