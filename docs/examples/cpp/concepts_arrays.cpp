// The example of "Arrays" (docs/concepts/arrays.md): arrays of the program seen as views, a sum in
// both orders checked against the bound kairn::traits gives for its length, how that bound grows
// with the length, and an accumulator in parts. ctest builds and runs it (tests/api/CMakeLists.txt,
// api.example.concepts_arrays) and compares what it prints with concepts_arrays.txt, which the page
// shows; what it prints does not depend on the instruction set, the order of the lanes (whose
// results it checks and does not print) included. It checks each result itself and exits with 1 if
// one is not what the page says.
#include <kairn/batch.hpp>
#include <kairn/kairn.hpp>

#include <cstddef>
#include <cstdio>
#include <string>
#include <vector>

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
using Number = kairn::Expansion<double, 2>;

// A number of two limbs as "x0 + x1" or "x0 - |x1|".
std::string limbs(double x0, double x1) {
    return hex(x0) + (x1 < 0 ? " - " + hex(-x1) : " + " + hex(x1));
}

// The exact sum of x_i = 1 + i 2^-52, i = 0 .. n - 1: n + 2^-52 n (n - 1) / 2, for n = 1000 the two
// limbs 1000 + 975 2^-43 and 300 2^-52 (499 500 = 975 * 512 + 300).
const double exact0 = 1000 + 975 * 0x1p-43, exact1 = 300 * 0x1p-52;

// |s - exact| <= unit * exact, the bound of a sum of positive terms, for s of one limb or two. The
// differences are exact (Sterbenz), and the comparison is made on them with the bound rounded down.
bool within(double s0, double s1, double unit) {
    const Number error = (Number(s0 - exact0) + (s1 - exact1));
    const double e = kairn::abs_upper(error);  // an upper bound of |s - exact| as a double
    return e <= kairn::mul_down(unit, exact0);
}

}  // namespace

int main() {
    // --8<-- [start:views]
    // The program's own arrays: n numbers of two limbs, x_i = 1 + i 2^-52, as an array of leading
    // limbs and an array of second limbs (zero here). A view sees them; it owns and copies nothing.
    const std::size_t n = 1000;
    std::vector<double> hi(n), lo(n, 0.0);
    for (std::size_t i = 0; i < n; ++i) hi[i] = 1 + double(i) * 0x1p-52;
    const kairn::SoAView<const double, 1> one(hi.data(), n);            // n numbers of one limb
    const kairn::SoAView<const double, 2> two(hi.data(), lo.data(), n);  // the same, of two limbs
    // --8<-- [end:views]

    // --8<-- [start:sum]
    const kairn::Reduction<kairn::Expansion<double, 1>> s1 = kairn::sum(one);        // the lanes' order
    const kairn::Reduction<Number> s2 = kairn::sum(two, kairn::sequential);          // element after element
    // With b = traits<X>::sum(n): |s - sum of x_i| <= b.unit * sum of |x_i|, in either order.
    const kairn::Bound<double> b1 = kairn::traits<double>::sum(n);
    const kairn::Bound<double> b2 = kairn::traits<Number>::sum(n);
    // --8<-- [end:sum]
    const kairn::Reduction<kairn::Expansion<double, 1>> s1_seq = kairn::sum(one, kairn::sequential);
    const kairn::Reduction<Number> s2_lanes = kairn::sum(two);
    std::printf("the exact sum:                %s\n", limbs(exact0, exact1).c_str());
    std::printf("one limb, sequential order:   %s, bound %s of the magnitudes\n", hex(s1_seq.value.limb[0]).c_str(),
                hex(b1.unit).c_str());
    std::printf("two limbs, sequential order:  %s, bound %s of the magnitudes\n",
                limbs(s2.value.limb[0], s2.value.limb[1]).c_str(), hex(b2.unit).c_str());
    std::printf("each order within its bound:  %s\n",
                within(s1.value.limb[0], 0, b1.unit) && within(s1_seq.value.limb[0], 0, b1.unit) &&
                        within(s2.value.limb[0], s2.value.limb[1], b2.unit) &&
                        within(s2_lanes.value.limb[0], s2_lanes.value.limb[1], b2.unit)
                    ? "yes"
                    : "no");
    check(s1.finite && s2.finite && s1_seq.finite && s2_lanes.finite, "the sums are finite");
    check(within(s1.value.limb[0], 0, b1.unit) && within(s1_seq.value.limb[0], 0, b1.unit), "one limb, both orders");
    check(within(s2.value.limb[0], s2.value.limb[1], b2.unit) &&
              within(s2_lanes.value.limb[0], s2_lanes.value.limb[1], b2.unit),
          "two limbs, both orders");

    // --8<-- [start:growth]
    // The bound grows with the length; beyond about n e = 1/4 none is given (+infinity).
    const std::size_t lengths[] = {2, 1000, std::size_t(1) << 20, std::size_t(1) << 40, std::size_t(1) << 60};
    const char* names[] = {"2", "1000", "2^20", "2^40", "2^60"};
    for (int j = 0; j < 5; ++j) {
        std::printf("n = %-5s  double: %-24s  Expansion<double, 2>: %s\n", names[j],
                    hex(kairn::traits<double>::sum(lengths[j]).unit).c_str(),
                    hex(kairn::traits<Number>::sum(lengths[j]).unit).c_str());
    }
    // --8<-- [end:growth]
    check(kairn::traits<double>::sum(std::size_t(1) << 60).unit > 1e308, "no bound for 2^60 terms of one limb");

    // --8<-- [start:accumulator]
    // The same sum in four parts, as four threads would compute it, merged at the end.
    kairn::Accumulator<double, 2> part[4];
    for (std::size_t i = 0; i < n; ++i) part[i % 4].add(hi[i]);
    kairn::Accumulator<double, 2> total = part[0];
    for (int j = 1; j < 4; ++j) total.merge(part[j]);
    const kairn::Ball<double, 2> ball = total.ball();  // center the sum, radius error_bound()
    // --8<-- [end:accumulator]
    std::printf("\naccumulator, four parts:      %s, radius %s\n",
                limbs(ball.center().limb[0], ball.center().limb[1]).c_str(), hex(ball.radius()).c_str());
    std::printf("its ball contains the exact sum: %s\n", ball.contains(Number(exact0) + exact1) ? "yes" : "no");
    check(total.count() == n && ball.contains(Number(exact0) + exact1), "the ball contains the exact sum");
    return failures == 0 ? 0 : 1;
}
