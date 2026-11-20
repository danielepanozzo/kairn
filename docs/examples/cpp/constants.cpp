// Constants from fractions: kairn::rational and kairn::integer. Built and run by ctest
// (tests/api/CMakeLists.txt, api.example.constants), which fails if it does not print what it
// checks; the "Getting started" page shows its section.
#include <kairn/kairn.hpp>

#include <cstdio>

int main(int argc, char**) {
    int failures = 0;
    auto check = [&](bool ok, const char* what) {
        std::printf("%s %s\n", ok ? "ok    " : "FAILED", what);
        failures += ok ? 0 : 1;
    };

    // --8<-- [start:rational]
    using Number = kairn::Expansion<double, 2>;

    // 1/10 is not a double, nor the sum of two: rational gives the nearest pair, a bound of its
    // error that is a double, and whether it is exact, in a constant expression.
    constexpr kairn::Constant<Number> tenth = kairn::rational<Number>(1, 10);
    static_assert(!tenth.exact && tenth.error < 0x1p-110);

    // A ball of center tenth.value and radius tenth.error contains 1/10 itself.
    constexpr kairn::Ball<double, 2> one_tenth(tenth.value, tenth.error);

    // At run time, the same bits, whatever the rounding mode: a division of two integers.
    const long long n = 9 + argc;  // 10 when the program has no arguments
    const kairn::Constant<Number> also_tenth = kairn::rational<Number>(1, n);

    // 2^53 + 1 is not a double, and is the pair (2^53, 1) exactly.
    constexpr kairn::Constant<Number> big = kairn::integer<Number>(9007199254740993);
    static_assert(big.exact && big.value.limb[0] == 0x1p53 && big.value.limb[1] == 1.0);
    // --8<-- [end:rational]

    std::printf("1/10: %a + %a, error at most %a\n", tenth.value.limb[0], tenth.value.limb[1], tenth.error);
    check(tenth.value.limb[0] == 0x1.999999999999ap-4 && tenth.value.limb[1] == -0x1.999999999999ap-58,
          "1/10 is the nearest pair of doubles");
    check(also_tenth.value.limb[0] == tenth.value.limb[0] && also_tenth.value.limb[1] == tenth.value.limb[1] &&
              also_tenth.error == tenth.error,
          "the same at run time");
    check(one_tenth.is_finite() && one_tenth.radius() == tenth.error, "the ball of 1/10 is finite");
    check(kairn::is_rational_result(also_tenth, 1, n), "the result satisfies its specification");
    return failures == 0 ? 0 : 1;
}
