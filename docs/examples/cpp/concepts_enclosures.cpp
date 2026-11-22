// The examples of "Intervals, balls and ball vectors" (docs/concepts/enclosures.md): one sum in the
// four enclosure types, an algorithm written once over Interval and Ball, the one radius of a
// BallVector next to the radii of separate balls, and what X(a, b) and X::from_bounds(a, b) make of
// each type. ctest builds and runs it (tests/api/CMakeLists.txt,
// api.example.concepts_enclosures) and compares what it prints with concepts_enclosures.txt, which
// the page shows; it also checks each result itself and exits with 1 if one is not what the page
// says.
#include <kairn/ball_vector.hpp>
#include <kairn/kairn.hpp>

#include <array>
#include <cstdio>

#include "concepts_print.hpp"

namespace {

int failures = 0;

void check(bool ok, const char* what) {
    if (!ok) {
        std::printf("FAILED: %s\n", what);
        ++failures;
    }
}

using concepts::hex;

// --8<-- [start:generic]
// Written once for every enclosure type S: the set X of [lo, hi], a set that contains x (1 - x) for
// every x in X, and what it says about the sign of that function there.
template <class S>
void report(const char* name, double lo, double hi) {
    // S::from_bounds(lo, hi) is the one spelling for both types: [lo, hi] for an interval, a ball
    // that contains [lo, hi] for a ball. Not S(lo, hi): for a ball, that is center lo, radius hi.
    const S x = S::from_bounds(lo, hi);
    const S y = x * (S(1.0) - x);
    std::printf("  %-20s [%.6g, %.6g]  certainly positive: %s\n", name, y.template lower_as<double>(),
                y.template upper_as<double>(), y.certainly_positive() ? "yes" : "no");
}

void on(double lo, double hi) {
    std::printf("x (1 - x) on [%g, %g]:\n", lo, hi);
    report<kairn::Interval<double, 1>>("Interval<double, 1>", lo, hi);
    report<kairn::Ball<double, 1>>("Ball<double, 1>", lo, hi);
    report<kairn::Ball<double, 2>>("Ball<double, 2>", lo, hi);
}
// --8<-- [end:generic]

}  // namespace

int main() {
    // --8<-- [start:sum]
    // The set of the one number 1, plus the set of the one number 2^-60, in each type.
    using I1 = kairn::Interval<double, 1>;
    using I2 = kairn::Interval<double, 2>;
    using B1 = kairn::Ball<double, 1>;
    using B2 = kairn::Ball<double, 2>;
    const double tiny = 0x1p-60;
    const I1 i1 = I1(1.0) + I1(tiny);  // each bound rounded outward: [1, 1 + 2^-52]
    const B1 b1 = B1(1.0) + B1(tiny);  // the center rounded to nearest, 1; the radius covers the error
    const I2 i2 = I2(1.0) + I2(tiny);  // bounds of two limbs, each moved outward by a bound of its error
    const B2 b2 = B2(1.0) + B2(tiny);  // center 1 + 2^-60; the radius covers the bound of its error
    // --8<-- [end:sum]
    std::printf("{1} + {2^-60}:\n");
    std::printf("  Interval<double, 1>  [%s, %s]\n", hex(i1.lower().limb[0]).c_str(), hex(i1.upper().limb[0]).c_str());
    std::printf("  Ball<double, 1>      center %s, radius %s\n", hex(b1.center().limb[0]).c_str(),
                hex(b1.radius()).c_str());
    std::printf("  Interval<double, 2>  [%s + %s, %s + %s]\n", hex(i2.lower().limb[0]).c_str(),
                hex(i2.lower().limb[1]).c_str(), hex(i2.upper().limb[0]).c_str(), hex(i2.upper().limb[1]).c_str());
    std::printf("  Ball<double, 2>      center %s + %s, radius %s\n", hex(b2.center().limb[0]).c_str(),
                hex(b2.center().limb[1]).c_str(), hex(b2.radius()).c_str());
    check(i1.lower().limb[0] == 1.0 && i1.upper().limb[0] == 1.0 + 0x1p-52, "the interval of one limb");
    check(b1.center().limb[0] == 1.0 && b1.radius() >= tiny, "the ball of one limb contains 1 + 2^-60");
    check(b2.center().limb[0] == 1.0 && b2.center().limb[1] == tiny && b2.radius() > 0, "the ball of two limbs");
    check(i2.contains(kairn::Expansion<double, 2>(1.0) + tiny) && b2.contains(kairn::Expansion<double, 2>(1.0) + tiny),
          "both sets of two limbs contain 1 + 2^-60");

    std::printf("\n");
    on(0.25, 0.75);
    on(0.49, 0.51);
    check(kairn::Interval<double, 1>(0.25, 0.75).certainly_positive(), "the domain is positive");

    // --8<-- [start:vector]
    // Three values, each plus 2^-60: as one BallVector, with one radius, and as three Balls.
    const std::array<kairn::Expansion<double, 1>, 3> c = {1.0, 1000.0, 1e6};
    const std::array<kairn::Expansion<double, 1>, 3> d = {tiny, tiny, tiny};
    const kairn::BallVector<double, 1, 3> v = kairn::BallVector<double, 1, 3>(c, 0.0) +
                                              kairn::BallVector<double, 1, 3>(d, 0.0);
    // --8<-- [end:vector]
    std::printf("\n{1, 1000, 1e6} + {2^-60, 2^-60, 2^-60}:\n");
    std::printf("  BallVector<double, 1, 3>  one radius %s\n", hex(v.radius()).c_str());
    for (std::size_t i = 0; i < 3; ++i) {
        const B1 entry = B1(c[i]) + B1(tiny);
        std::printf("  Ball<double, 1>, entry %zu  radius %s\n", i, hex(entry.radius()).c_str());
        check(v.entry(i).contains(c[i].limb[0]), "each entry contains its center");
        check(v.radius() >= entry.radius(), "the one radius is at least each entry's");
    }

    // --8<-- [start:spelling]
    // X(a, b) is two different sets for the two types; X::from_bounds(a, b) is one spelling of both.
    const I1 interval(0.25, 0.75);                 // the interval [0.25, 0.75]
    const B1 ball(0.25, 0.75);                     // the ball of center 0.25 and radius 0.75
    const B1 ball1 = B1::from_bounds(0.25, 0.75);  // a ball that contains [0.25, 0.75]
    const B2 ball2 = B2::from_bounds(0.25, 0.75);  // the same; here its center is the exact midpoint
    // --8<-- [end:spelling]
    std::printf("\nX(0.25, 0.75) and X::from_bounds(0.25, 0.75):\n");
    std::printf("  Interval<double, 1>(0.25, 0.75)           [%g, %g]\n", interval.lower_as<double>(),
                interval.upper_as<double>());
    std::printf("  Ball<double, 1>(0.25, 0.75)               [%g, %g]\n", ball.lower_as<double>(),
                ball.upper_as<double>());
    std::printf("  Ball<double, 1>::from_bounds(0.25, 0.75)  center %g, radius %g: [%g, %g]\n",
                ball1.center().limb[0], ball1.radius(), ball1.lower_as<double>(), ball1.upper_as<double>());
    // (the second limb through hex, which prints a zero of either sign as 0)
    std::printf("  Ball<double, 2>::from_bounds(0.25, 0.75)  center %g + %s, radius %g\n", ball2.center().limb[0],
                hex(ball2.center().limb[1]).c_str(), ball2.radius());
    const I1 interval_named = I1::from_bounds(0.25, 0.75);
    check(interval_named.lower().limb[0] == interval.lower().limb[0] &&
              interval_named.upper().limb[0] == interval.upper().limb[0],
          "Interval::from_bounds(lo, hi) is Interval(lo, hi)");
    check(ball.lower_as<double>() == -0.5 && ball.upper_as<double>() == 1.0, "Ball(c, r) is center c, radius r");
    const B1 ball1_old = B1::from_interval(0.25, 0.75);
    check(ball1.center().limb[0] == ball1_old.center().limb[0] && ball1.radius() == ball1_old.radius(),
          "Ball::from_bounds(lo, hi) is Ball::from_interval(lo, hi)");
    check(ball1.lower_as<double>() <= 0.25 && ball1.upper_as<double>() >= 0.75, "the ball contains [lo, hi]");
    check(ball2.center().limb[0] == 0.5 && ball2.center().limb[1] == 0 && ball2.radius() == 0.25,
          "two limbs, halves exact: the exact midpoint and the smallest radius");
    return failures == 0 ? 0 : 1;
}
