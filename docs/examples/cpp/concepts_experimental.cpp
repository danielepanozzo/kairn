// The example of "Experimental: two and four limbs rounded upward" (docs/concepts/experimental.md):
// EXPERIMENTAL, NOT VERIFIED, opt-in, like the two headers it includes, in which no bound is proved.
// It requires the rounding mode upward set by kairn::upward::Scope and the options of
// docs/concepts/upward.md (GCC and Clang -frounding-math), and is not built with MSVC, which the
// headers refuse. A sign that one and two limbs cannot decide and four can; the conversions from
// and to the default Interval<double, 2>; a four-limb function on arrays. ctest builds it with
// kairn::upward and kairn::fma and the
// build's flags (tests/experimental/CMakeLists.txt, experimental.example) and compares what it
// prints with concepts_experimental.txt, which the page shows; it also checks each result itself,
// against the exact values, and exits with 1 if one is not what the page says.

// --8<-- [start:opt_in]
// The opt-in, before the first experimental header: no bound of these headers is proved.
#define KAIRN_EXPERIMENTAL_UNVERIFIED
#include <kairn/experimental/upward2.hpp>
#include <kairn/experimental/upward4.hpp>
#include <kairn/experimental/upward4_arrays.hpp>
// --8<-- [end:opt_in]

#include <kairn/kairn.hpp>
#include <kairn/upward.hpp>

#include <cstdio>
#include <string>

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

template <class I>
std::string text(const I& x) {
    if (x.is_empty()) return "empty";
    std::string s = "[" + hex(x.lower()) + ", " + hex(x.upper()) + "]";
    if (x.certainly_positive()) return s + ", certainly positive";
    if (x.certainly_negative()) return s + ", certainly negative";
    return s + ", contains zero";
}

// --8<-- [start:sign]
namespace u2 = kairn::experimental::upward2;
namespace u4 = kairn::experimental::upward4;

// x^3 - (1 + 3 2^-52) - 3 2^-104 on an interval x: for x = [a, a], a = 1 + 2^-52, its exact value is
// 2^-156, which needs 157 bits. Every operation runs inside the caller's kairn::upward::Scope.
template <class I>
I cubic(const I& x) {
    return x * x * x - (1 + 0x3p-52) - 0x3p-104;
}
// --8<-- [end:sign]

}  // namespace

int main() {
    // --8<-- [start:sign_call]
    const double a = 1 + 0x1p-52;
    kairn::upward::Interval<double> r1;
    u2::Interval r2;
    u4::Interval r4;
    {
        kairn::upward::Scope up;
        r1 = cubic(kairn::upward::Interval<double>(a));   // one limb
        r2 = cubic(u2::Interval(a));                      // two limbs
        r4 = cubic(u4::Interval(a));                      // four limbs
    }
    // lower(), upper() and the predicates are exact: any rounding mode.
    std::printf("one limb:   %s\n", text(r1).c_str());
    std::printf("two limbs:  %s\n", text(r2).c_str());
    std::printf("four limbs: %s\n", text(r4).c_str());
    // --8<-- [end:sign_call]
    check(r1.contains(0.0) && r2.contains_zero(), "one and two limbs contain zero");
    check(r1.lower() <= 0x1p-156 && 0x1p-156 <= r1.upper(), "one limb contains 2^-156");
    check(r2.lower() <= 0x1p-156 && 0x1p-156 <= r2.upper(), "two limbs contain 2^-156");
    check(r4.certainly_positive() && r4.lower() == 0x1p-156 && r4.upper() == 0x1p-156,
          "four limbs give 2^-156 exactly");

    // --8<-- [start:convert]
    // From the default Interval<double, 2> under the mode upward, back under rounding to nearest.
    const kairn::Interval<double, 2> d = kairn::Interval<double, 2>::from_bounds(1.0, 3.0);
    u4::Interval y;
    double w = 0;
    {
        kairn::upward::Scope up;
        y = u4::from_interval(d);   // the same set, exactly
        y = u4::sqr(y) - y * 2.0;   // [1, 3]^2 - 2 [1, 3] = [1, 9] - [2, 6]
        w = u4::width(y);           // its width, rounded up
    }
    const kairn::Interval<double, 2> back = u4::to_interval(y);   // the first two limbs, exactly
    std::printf("y:          %s, width %s\n", text(y).c_str(), hex(w).c_str());
    std::printf("back:       [%s, %s]\n", hex(back.lower().limb[0]).c_str(), hex(back.upper().limb[0]).c_str());
    // --8<-- [end:convert]
    check(y.lower() == -5 && y.upper() == 7 && w == 12, "[1, 9] - [2, 6] is [-5, 7]");
    check(back.lower().limb[0] == -5 && back.upper().limb[0] == 7, "the conversion back keeps the bounds");

    // --8<-- [start:arrays]
    // [1, 1] and [-1, 2] in the eight plain arrays of a four-limb View: u[i][k] and n[i][k] are the
    // limb i of element k's upper bound and of its lower bound negated.
    double u[4][2] = {{1, 2}, {0, 0}, {0, 0}, {0, 0}}, n[4][2] = {{-1, 1}, {0, 0}, {0, 0}, {0, 0}};
    double zu[4][2], zn[4][2];
    const u4::View<const double> xs{{u[0], u[1], u[2], u[3]}, {n[0], n[1], n[2], n[3]}, 2};
    const u4::View<double> zs{{zu[0], zu[1], zu[2], zu[3]}, {zn[0], zn[1], zn[2], zn[3]}, 2};
    u4::mul(zs, xs, xs);   // element by element; it holds its own scope
    for (int k = 0; k < 2; ++k)
        std::printf("x[%d] * x[%d]: [%s, %s]\n", k, k, hex(-zn[0][k]).c_str(), hex(zu[0][k]).c_str());
    // --8<-- [end:arrays]
    check(zu[0][0] == 1 && zn[0][0] == -1 && zu[0][1] == 4 && zn[0][1] == 2, "[1, 1]^2 = [1, 1], [-1, 2]^2 = [-2, 4]");
    for (int i = 1; i < 4; ++i)
        check(zu[i][0] == 0 && zn[i][0] == 0 && zu[i][1] == 0 && zn[i][1] == 0, "the later limbs are zero");

    return failures == 0 ? 0 : 1;
}
