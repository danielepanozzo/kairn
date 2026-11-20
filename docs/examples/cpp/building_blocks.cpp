// The building blocks on T, the exact scaling of a ball, the ball of a constant and the sign
// predicates of a ball. Built and run by ctest (tests/api/CMakeLists.txt,
// api.example.building_blocks), which fails if it does not print what it checks; the "Getting
// started" page shows its sections.
// --8<-- [start:version]
#include <kairn/version.hpp>
#if !defined(KAIRN_VERSION_AT_LEAST)
#error "this program needs Kairn 0.2.0 or later"
#elif !KAIRN_VERSION_AT_LEAST(0, 2, 0)
#error "this program needs Kairn 0.2.0 or later"
#endif
// --8<-- [end:version]

#include <kairn/kairn.hpp>

#include <cstdio>

namespace {

int failures = 0;
void check(bool ok, const char* what) {
    std::printf("%s %s\n", ok ? "ok    " : "FAILED", what);
    failures += ok ? 0 : 1;
}

// --8<-- [start:exact]
// Whether a + b is a double: TwoSum gives the rounded sum and what the rounding left out.
bool sum_is_exact(double a, double b) {
    const kairn::SumAndError<double> r = kairn::two_sum(a, b);  // r.sum, r.error
    return r.error == 0;
}

// The exact sum of two doubles as a two-limb number: the pair is normalized, and the conversion
// is valid whenever both members are finite.
kairn::Expansion<double, 2> exact_sum(double a, double b) {
    return kairn::Expansion<double, 2>(kairn::two_sum(a, b));
}
// --8<-- [end:exact]

// --8<-- [start:radius]
// A program's own radius arithmetic, rounded upward without changing the rounding mode: a bound
// of |x y - cx cy| for x within rx of cx and y within ry of cy, |cx| ry + |cy| rx + rx ry.
double product_radius(double cx, double rx, double cy, double ry) {
    const double ax = cx < 0 ? -cx : cx, ay = cy < 0 ? -cy : cy;
    return kairn::radd(kairn::radd(kairn::rmul(ax, ry), kairn::rmul(ay, rx)), kairn::rmul(rx, ry));
}
// --8<-- [end:radius]

}  // namespace

int main() {
    const volatile double v_one = 1.0, v_tiny = 0x1p-60, v_third = 1.0 / 3.0, v_ten = 10.0;
    const double one = v_one, tiny = v_tiny;

    check(!sum_is_exact(one, tiny), "1 + 2^-60 is not a double");
    check(sum_is_exact(one, 0.5), "1 + 1/2 is a double");
    const kairn::Expansion<double, 2> s = exact_sum(one, tiny);
    check(s.limb[0] == 1 && s.limb[1] == 0x1p-60, "the exact sum 1 + 2^-60 as two limbs");

    // --8<-- [start:bounds]
    // Bounds of a sum and of a product, rounded down and up, under the default rounding mode.
    const double third = v_third, ten = v_ten;
    const double lo = kairn::add_down(third, ten), hi = kairn::add_up(third, ten);
    const double plo = kairn::mul_down(third, ten), phi = kairn::mul_up(third, ten);
    // lo <= third + ten <= hi, each the nearest double on its side; the same for the product.
    // --8<-- [end:bounds]
    std::printf("third + 10 in [%a, %a], third * 10 in [%a, %a]\n", lo, hi, plo, phi);
    check(lo < hi && kairn::next_up(lo) == hi, "the sum is between two neighbors");
    check(plo < phi && kairn::next_up(plo) == phi, "the product is between two neighbors");
    check(kairn::add_down(one, 0.5) == 1.5 && kairn::add_up(one, 0.5) == 1.5, "an exact sum is its own bound");

    const double r = product_radius(2.0, 0x1p-50, 3.0, 0x1p-50);
    check(r >= 5 * 0x1p-50, "the radius of a product covers |cx| ry + |cy| rx + rx ry");

    // --8<-- [start:scaling]
    using Ball = kairn::Ball<double, 2>;
    const Ball x(kairn::Expansion<double, 2>(3.0 * one), 0x1p-40);

    // half and ldexp multiply every member by a power of two, exactly when nothing underflows (each
    // limb of the center and the radius zero or above 2^-1022 after the scaling): center 3/2, radius
    // 2^-41, with nothing added; then center 3 2^-900, radius 2^-940.
    const Ball h = kairn::half(x);
    const Ball far = kairn::ldexp(x, -900);

    // X * 0.5 is the general scaling by a double, whose radius also covers a rounding.
    const Ball g = x * 0.5;
    // --8<-- [end:scaling]
    check(h.center().limb[0] == 1.5 && h.radius() == 0x1p-41, "half(X) is exact");
    check(far.center().limb[0] == 3 * 0x1p-900 && far.radius() == 0x1p-940, "ldexp(X, -900) is exact");
    check(kairn::ldexp(x, -1050).radius() == 0x1p-1073, "below 2^-1022 the radius grows by what is lost");
    check(g.radius() > 0x1p-41, "X * 0.5 has a larger radius");

    // --8<-- [start:rational]
    // A ball that contains 1/3: center and radius from kairn::rational, at compile time.
    constexpr Ball one_third(kairn::rational<kairn::Expansion<double, 2>>(1, 3));

    // X / 3, enclosed: X times the ball of 1/3, until Kairn has a division.
    const Ball y = x * one_third;
    // --8<-- [end:rational]
    std::printf("1/3 within %a of %a + %a\n", one_third.radius(), one_third.center().limb[0],
                one_third.center().limb[1]);
    check(one_third.radius() > 0 && one_third.radius() < 0x1p-105, "the ball of 1/3 is finite and tight");
    check(y.center().limb[0] == 1.0 && y.radius() > x.radius() / 3, "X / 3 contains 3 / 3 and keeps X's spread");

    // --8<-- [start:signs]
    // The sign of every member of a ball, decided exactly from its center and radius.
    const bool positive = y.certainly_positive();     // true: every member is above 0
    const bool negative = (-y).certainly_negative();  // true
    const bool zero = Ball().certainly_zero();        // true: the point 0
    const bool whole = Ball::whole().certainly_positive() || Ball::empty().certainly_positive();  // false
    // --8<-- [end:signs]
    check(positive && negative && zero && !whole, "the sign predicates");
    return failures == 0 ? 0 : 1;
}
