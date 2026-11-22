// The example of "Values, threads and constant expressions" (docs/concepts/values.md): the types as
// plain values, moved through a program's own storage as bytes; what a constant expression computes;
// and two_prod, whose error term at compile time can differ from the one at run time below a
// threshold. ctest builds and runs it (tests/api/CMakeLists.txt, api.example.concepts_values) and
// compares what it prints with concepts_values.txt, which the page shows; it also checks each result
// itself and exits with 1 if one is not what the page says.
#include <kairn/kairn.hpp>

#include <array>
#include <cstdio>
#include <cstring>
#include <type_traits>

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

}  // namespace

int main() {
    // --8<-- [start:values]
    using Number = kairn::Expansion<double, 2>;
    using B2 = kairn::Ball<double, 2>;
    using I2 = kairn::Interval<double, 2>;
    // Plain values: copied as bytes, no heap memory, the size of their limbs.
    static_assert(std::is_trivially_copyable_v<Number> && std::is_standard_layout_v<Number>);
    static_assert(std::is_trivially_copyable_v<B2> && std::is_standard_layout_v<B2>);
    static_assert(std::is_trivially_copyable_v<I2> && std::is_standard_layout_v<I2>);
    static_assert(sizeof(Number) == 2 * sizeof(double) && sizeof(B2) == 3 * sizeof(double) &&
                  sizeof(I2) == 4 * sizeof(double));

    // Through a buffer of the program's own, as a message or a device buffer would carry them.
    const std::array<B2, 2> balls = {B2(Number(1.0) + 0x1p-60, 0x1p-80), B2::whole()};
    unsigned char bytes[sizeof balls];
    std::memcpy(bytes, &balls, sizeof balls);
    std::array<B2, 2> back;
    std::memcpy(&back, bytes, sizeof back);
    // --8<-- [end:values]
    const bool same = back[0].center().limb[0] == balls[0].center().limb[0] &&
                      back[0].center().limb[1] == balls[0].center().limb[1] &&
                      back[0].radius() == balls[0].radius() && back[1].is_whole();
    std::printf("a ball through bytes:  center %s + %s, radius %s; the whole line stays whole: %s\n",
                hex(back[0].center().limb[0]).c_str(), hex(back[0].center().limb[1]).c_str(),
                hex(back[0].radius()).c_str(), back[1].is_whole() ? "yes" : "no");
    check(same, "the balls come back as they went");
    check(Number().limb[0] == 0 && B2().radius() == 0 && I2().upper().limb[0] == 0, "default construction is zero");

    // --8<-- [start:limbs]
    // A set rebuilt from the limbs read out of it, as a program that stores the limbs itself does:
    // for a ball of two limbs, the center's two limbs, then the radius.
    const std::array<B2, 3> sets = {balls[0], B2::whole(), B2::empty()};
    double stored[3][3];
    for (int s = 0; s < 3; ++s) {
        stored[s][0] = sets[s].center().limb[0];
        stored[s][1] = sets[s].center().limb[1];
        stored[s][2] = sets[s].radius();
    }
    const B2 finite_again = B2::from_limbs(stored[0]);  // the same ball, limb for limb
    const B2 whole_again = B2::from_limbs(stored[1]);   // the whole line
    const B2 empty_again = B2::from_limbs(stored[2]);   // the empty set
    // Not the constructor: Ball(c, r) of the NaN center and the NaN radius of the empty set is the
    // whole line.
    const B2 from_parts = B2(Number::from_limbs(stored[2]), stored[2][2]);
    // --8<-- [end:limbs]
    const bool same_limbs = finite_again.center().limb[0] == stored[0][0] &&
                            finite_again.center().limb[1] == stored[0][1] && finite_again.radius() == stored[0][2];
    std::printf("from_limbs of the limbs read: the same ball: %s; the whole line: %s; the empty set: %s\n",
                same_limbs ? "yes" : "no", whole_again.is_whole() ? "yes" : "no", empty_again.is_empty() ? "yes" : "no");
    std::printf("Ball(c, r) of the empty set's parts: the whole line: %s\n", from_parts.is_whole() ? "yes" : "no");
    check(same_limbs && whole_again.is_whole() && empty_again.is_empty(), "the round trip of from_limbs");
    check(from_parts.is_whole(), "Ball(c, r) of a NaN center is the whole line");

    // --8<-- [start:constexpr]
    // Computed by the compiler: a sum of two limbs, its scaling by 2^3, a constant from a fraction,
    // a ball made of it.
    constexpr Number x = Number(1.0) + 0x1p-60;
    constexpr Number eight_x = kairn::ldexp(x, 3);
    constexpr kairn::Constant<Number> third = kairn::rational<Number>(1, 3);
    constexpr B2 ball_of_third = B2(third);
    static_assert(x.limb[0] == 1.0 && x.limb[1] == 0x1p-60);
    static_assert(eight_x.limb[0] == 8.0 && eight_x.limb[1] == 0x1p-57);
    static_assert(!third.exact && ball_of_third.radius() == third.error);
    // --8<-- [end:constexpr]
    std::printf("constexpr 1 + 2^-60:   %s + %s\n", hex(x.limb[0]).c_str(), hex(x.limb[1]).c_str());
    std::printf("constexpr 1/3:         %s + %s, within %s\n", hex(third.value.limb[0]).c_str(),
                hex(third.value.limb[1]).c_str(), hex(third.error).c_str());

    // --8<-- [start:two_prod]
    // two_prod(a, b): the product rounded and its error term. At run time an FMA computes the error;
    // in constant evaluation, Dekker's product. Above 2^-969 both are exact, so the same values.
    constexpr double a = 1 + 0x1p-30, b = 1 - 0x1p-29;
    constexpr kairn::ProductAndError<double> at_compile_time = kairn::two_prod(a, b);
    volatile double va = a, vb = b;
    const kairn::ProductAndError<double> at_run_time = kairn::two_prod(double(va), double(vb));

    // Below it, each error term is within its own bound of the exact one: eta / 2 at run time,
    // 13 eta / 8 in constant evaluation; they can differ, by at most 2 eta.
    constexpr double c = 0x1.0d10f94242dd5p+0, d = 0x1.c41b28b15075cp-1000;
    constexpr kairn::ProductAndError<double> low_compile = kairn::two_prod(c, d);
    volatile double vc = c, vd = d;
    const kairn::ProductAndError<double> low_run = kairn::two_prod(double(vc), double(vd));
    // --8<-- [end:two_prod]
    const bool above = at_compile_time.product == at_run_time.product && at_compile_time.error == at_run_time.error;
    const double gap = low_run.error - low_compile.error;
    const double eta = 0x1p-1074;
    const bool below = low_compile.product == low_run.product && gap <= 2 * eta && -gap <= 2 * eta;
    std::printf("two_prod above 2^-969: product %s, error %s, the same at compile time and at run time: %s\n",
                hex(at_run_time.product).c_str(), hex(at_run_time.error).c_str(), above ? "yes" : "no");
    std::printf("two_prod below 2^-969: the same product, error terms within 2 eta: %s\n", below ? "yes" : "no");
    // Which of the two error terms each compiler gives is not part of the output, which ctest compares
    // on every platform: the statement is only that each is within its bound.
    std::fprintf(stderr, "below 2^-969: error at run time %s, at compile time %s\n", hex(low_run.error).c_str(),
                 hex(low_compile.error).c_str());
    check(above, "above the threshold the two executions agree");
    check(below, "below the threshold the products agree and the error terms are within 2 eta");
    return failures == 0 ? 0 : 1;
}
