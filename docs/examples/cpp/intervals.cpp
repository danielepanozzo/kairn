// The range of a polynomial over an interval, with intervals and with balls: the program of the
// tutorial docs/tutorials/intervals.md, which shows its sections and its output. ctest builds it
// with the build's flags and under each contraction setting of the compiler
// (tests/api/CMakeLists.txt), runs it, and compares what it prints with intervals.txt; the program
// also checks its results itself and exits with 1 if one is wrong.
#include <kairn/kairn.hpp>

#include <cstdio>
#include <string>
#include <vector>

namespace {

int failures = 0;

void check(bool ok, const char* what) {
    if (!ok) {
        std::printf("FAILED: %s\n", what);
        ++failures;
    }
}

// --8<-- [start:types]
using I = kairn::Interval<double, 1>;  // bounds of one double each
using I2 = kairn::Interval<double, 2>;  // bounds of two limbs each
using B = kairn::Ball<double, 1>;      // a center of one double and a radius
using B2 = kairn::Ball<double, 2>;     // a center of two limbs and a radius
// --8<-- [end:types]

// An interval as text, [lower, upper], to ten digits.
std::string text(const I& x) {
    char buf[80];
    std::snprintf(buf, sizeof buf, "[%.10g, %.10g]", x.lower().limb[0], x.upper().limb[0]);
    return buf;
}
void print(const char* label, const I& x) { std::printf("  %-22s %s\n", label, text(x).c_str()); }

// --8<-- [start:polynomial]
// p(x) = x^2 - 2x, written three ways. For an interval or a ball X, each returns a set that
// contains p(x) for every x in X; an operand that is a number is written as the set of one point.
template <class X>
X expanded(const X& x) {
    return x * x - X(2.0) * x;
}
template <class X>
X factored(const X& x) {
    return x * (x - X(2.0));
}
template <class X>
X centered(const X& x) {
    const X d = x - X(1.0);
    return d * d - X(1.0);
}
// --8<-- [end:polynomial]

// --8<-- [start:pieces]
// The hull of f over the 2^depth pieces of X, each piece of a step split in two at its midpoint.
template <class F>
I over_pieces(const I& x, int depth, F f) {
    std::vector<I> pieces{x};
    for (int step = 0; step < depth; ++step) {
        std::vector<I> next;
        for (const I& piece : pieces) {
            const kairn::Split<I> halves = piece.split();
            next.push_back(halves.left);
            next.push_back(halves.right);
        }
        pieces = next;
    }
    I hull = I::empty();
    for (const I& piece : pieces) hull = hull.hull(f(piece));
    return hull;
}
// --8<-- [end:pieces]

// Whether the interval contains the range [-1, 0] of p over [0, 2].
bool contains_range(const I& z) { return z.lower().limb[0] <= -1 && z.upper().limb[0] >= 0; }

}  // namespace

int main() {
    // --8<-- [start:direct]
    const I x(0.0, 2.0);
    std::printf("p(x) = x^2 - 2x on X = [0, 2], whose range is [-1, 0]:\n");
    print("x*x - 2*x", expanded(x));
    print("x*(x - 2)", factored(x));
    print("(x - 1)*(x - 1) - 1", centered(x));
    // --8<-- [end:direct]
    check(contains_range(expanded(x)) && contains_range(factored(x)) && contains_range(centered(x)),
          "each form contains the range");
    check(expanded(x).lower().limb[0] == -4 && expanded(x).upper().limb[0] == 4, "x*x - 2*x is [-4, 4]");
    check(centered(x).lower().limb[0] == -2 && centered(x).upper().limb[0] == 0, "(x - 1)^2 - 1 is [-2, 0]");

    // --8<-- [start:split]
    std::printf("The hull over n pieces of X:\n");
    std::printf("  %-6s %-30s %s\n", "n", "x*x - 2*x", "(x - 1)*(x - 1) - 1");
    for (int depth : {0, 1, 2, 4, 6, 8, 10}) {
        const I e = over_pieces(x, depth, [](const I& p) { return expanded(p); });
        const I c = over_pieces(x, depth, [](const I& p) { return centered(p); });
        std::printf("  %-6d %-30s %s\n", 1 << depth, text(e).c_str(), text(c).c_str());
        check(contains_range(e) && contains_range(c), "the hull over the pieces contains the range");
        // On n pieces of width h = 2/n, x*x - 2*x gives [-1 - 2h, 2h]: the excess shrinks as h.
        const double h = 2.0 / (1 << depth);
        check(depth == 0 || (e.lower().limb[0] == -1 - 2 * h && e.upper().limb[0] == 2 * h), "[-1 - 2h, 2h]");
        check(depth == 0 || (c.lower().limb[0] == -1 && c.upper().limb[0] == 0), "the centered form is exact");
    }
    // --8<-- [end:split]

    // --8<-- [start:balls]
    // The same set as a ball: center 1, radius 1. The arithmetic of balls has the same dependency,
    // and its product covers the operands' radii by |cx| ry + |cy| rx + rx ry, more than intervals.
    const B b(x);
    std::printf("The same with Ball<double, 1>(X), center %g and radius %g:\n", b.center().limb[0], b.radius());
    print("x*x - 2*x", I(expanded(b)));
    print("(x - 1)*(x - 1) - 1", I(centered(b)));
    // --8<-- [end:balls]
    check(contains_range(I(expanded(b))) && contains_range(I(centered(b))), "the balls contain the range");
    check(I(expanded(b)).lower().limb[0] < -4, "the ball of x*x - 2*x is wider than its interval");

    // --8<-- [start:two_limbs]
    // Two limbs: each bound is within about 8 u^2 (sums) and 10 u^2 (products) of the exact one,
    // relative to it, plus about 2^-1021, but not the exact one: [0, 2] gives no exact bound.
    const I2 x2(0.0, 2.0);
    const I2 z2 = expanded(x2);
    const double below = (kairn::Expansion<double, 2>(-4.0) - z2.lower()).limb[0];
    const double above = (z2.upper() - kairn::Expansion<double, 2>(4.0)).limb[0];
    std::printf("With Interval<double, 2>, x*x - 2*x is [-4 - %.3g, 4 + %.3g]\n", below, above);
    // --8<-- [end:two_limbs]
    check(below > 0 && below < 1e-30 && above > 0 && above < 1e-30, "two limbs: just outside [-4, 4]");

    // --8<-- [start:narrow]
    // A narrow set: x = 1/10, which no double is. Its ball of two limbs, from kairn::rational, has
    // a radius of about 1e-34; its interval of one limb is the two doubles around 1/10.
    const B2 tenth(kairn::rational<kairn::Expansion<double, 2>>(1, 10));
    const I tenth1(B(kairn::rational<kairn::Expansion<double, 1>>(1, 10)));
    const B2 p2 = expanded(tenth);
    const I p1 = expanded(tenth1);
    std::printf("p(1/10) = -0.19:\n");
    std::printf("  Ball<double, 2>        center %.17g, radius %.2g\n", p2.center().limb[0], p2.radius());
    std::printf("  Interval<double, 1>    [%.17g, %.17g]\n", p1.lower().limb[0], p1.upper().limb[0]);
    // --8<-- [end:narrow]
    // Both contain -19/100: so does the ball, or the interval, of the constant -19/100, and the
    // difference of two sets that share a point contains 0.
    const B2 d2 = p2 - B2(kairn::rational<kairn::Expansion<double, 2>>(-19, 100));
    const I d1 = p1 - I(B(kairn::rational<kairn::Expansion<double, 1>>(-19, 100)));
    check(d2.lower_as<double>() <= 0 && d2.upper_as<double>() >= 0 && p2.radius() < 1e-30, "the ball of p(1/10)");
    check(d1.lower().limb[0] <= 0 && d1.upper().limb[0] >= 0, "the interval of p(1/10)");
    return failures ? 1 : 0;
}
