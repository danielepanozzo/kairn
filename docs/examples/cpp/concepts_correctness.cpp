// The example of "What correct means here" (docs/concepts/correctness.md): an error bound as the
// claim states it and as kairn::traits exports it, one product checked against it in exact
// arithmetic, the ball that contains the product, the marker kairn::unverified, and how a program
// asks whether an operation is proved. ctest builds and runs it (tests/api/CMakeLists.txt,
// api.example.concepts_correctness) and compares what it prints with concepts_correctness.txt, which
// the page shows; it also checks each result itself and exits with 1 if one is not what the page
// says.
#include <kairn/batch.hpp>
#include <kairn/kairn.hpp>

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

// --8<-- [start:has_sum]
// Whether kairn::sum takes a view of type V: a function on arrays compiles only while the loop it
// calls is proved, so this is the loop's proof status, as a constant of the program.
template <class V>
constexpr bool has_sum = requires(V v) { kairn::sum(v); };
// --8<-- [end:has_sum]

}  // namespace

int main() {
    // --8<-- [start:bound]
    using Number = kairn::Expansion<double, 2>;

    // The proved bound of x * y, |z - xy| <= 4u^2 |xy| + (3/2) eta, as numbers of double rounded up.
    constexpr auto bound = kairn::traits<Number>::mul;
    static_assert(bound.verified && bound.reference == kairn::BoundForm::result);

    // x = (1 + 2^-30) + 2^-80 and y = (1 + 2^-40) + 2^-90, so that the exact product is a sum of
    // powers of two: 1 + 2^-30 + 2^-40 + 2^-70 + 2^-80 + 2^-90 + 2^-119 + 2^-170.
    const double xl[2] = {1 + 0x1p-30, 0x1p-80}, yl[2] = {1 + 0x1p-40, 0x1p-90};
    const Number x = Number::from_limbs(xl), y = Number::from_limbs(yl);
    const Number z = x * y;
    // --8<-- [end:bound]
    std::printf("the bound of x * y:     unit %s, tiny %s, relative to the exact result\n", hex(bound.unit).c_str(),
                hex(bound.tiny).c_str());
    std::printf("x * y:                  %s + %s\n", hex(z.limb[0]).c_str(), hex(z.limb[1]).c_str());
    // The leading limb and the second limb of z are the first three terms and the next four: the
    // error is the last term, 2^-170, which the product left out, far below the bound (above 2^-104,
    // since |xy| > 1).
    const bool known = z.limb[0] == 1 + 0x1p-30 + 0x1p-40 && z.limb[1] == 0x1p-70 + 0x1p-80 + 0x1p-90 + 0x1p-119;
    check(known, "x * y is the exact product but its last term");
    check(0x1p-170 <= bound.unit, "the error is within the bound");
    std::printf("x * y - xy:             %s, where the bound is at least %s\n", known ? hex(-0x1p-170).c_str() : "?",
                hex(bound.unit).c_str());

    // --8<-- [start:ball]
    // The same product as balls of radius 0: a ball that contains the exact product.
    const kairn::Ball<double, 2> b = kairn::Ball<double, 2>(x) * kairn::Ball<double, 2>(y);
    // --8<-- [end:ball]
    std::printf("the ball of x times y:  center %s + %s, radius %s\n", hex(b.center().limb[0]).c_str(),
                hex(b.center().limb[1]).c_str(), hex(b.radius()).c_str());
    check(b.center().limb[0] == z.limb[0] && b.center().limb[1] == z.limb[1], "the center is x * y");
    check(b.radius() >= 0x1p-170, "the radius covers the error 2^-170");

    // --8<-- [start:ask]
    // The marker is accepted on proved operations too, and gives the same result.
    const Number marked = kairn::unverified(x) * y;
    // The proof status of the loop of a sum of arrays of two limbs (has_sum, above).
    constexpr bool sum_proved = has_sum<kairn::SoAView<const double, 2>>;
    static_assert(sum_proved);
    // --8<-- [end:ask]
    std::printf("with the marker:        %s\n", marked.limb[0] == z.limb[0] && marked.limb[1] == z.limb[1] ? "the same bits"
                                                                                                       : "other bits");
    std::printf("has_sum, two limbs:     %s\n", sum_proved ? "yes" : "no");
    check(marked.limb[0] == z.limb[0] && marked.limb[1] == z.limb[1], "the marked product is the product");
    return failures == 0 ? 0 : 1;
}
