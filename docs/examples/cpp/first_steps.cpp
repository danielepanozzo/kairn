// A first program with Kairn: two-limb numbers and a ball. Built and run by ctest
// (tests/api/CMakeLists.txt), which fails if it does not print what it checks; the "Getting
// started" page shows its sections.
// --8<-- [start:include]
#include <kairn/kairn.hpp>
// --8<-- [end:include]

#include <cstdio>

int main() {
    int failures = 0;
    auto check = [&](bool ok, const char* what) {
        std::printf("%s %s\n", ok ? "ok    " : "FAILED", what);
        failures += ok ? 0 : 1;
    };

    // --8<-- [start:self_test]
    const kairn::Status status = kairn::self_test();
    if (!status) {
        std::fprintf(stderr, "kairn::self_test: %s\n", status.message());
        return 1;
    }
    // --8<-- [end:self_test]

    // --8<-- [start:expansion]
    using Number = kairn::Expansion<double, 2>;

    // 1 + 2^-60 is not a double: the sum of two doubles rounds back to 1. Two limbs keep it.
    const double tiny = 0x1p-60;
    const double lost = 1.0 + tiny;          // 1
    const Number kept = Number(1.0) + tiny;  // limbs (1, 2^-60): the exact value

    // (1 + 2^-60)^2 = 1 + 2^-59 + 2^-120. The product keeps the first two terms; its error is
    // at most traits<Number>::mul.unit times the exact result, plus traits<Number>::mul.tiny.
    const Number square = kept * kept;
    constexpr auto bound = kairn::traits<Number>::mul;
    static_assert(bound.verified);
    // --8<-- [end:expansion]
    std::printf("lost: %a\nkept: %a + %a\nsquare: %a + %a\nbound of *: %a |exact| + %a\n", lost, kept.limb[0],
                kept.limb[1], square.limb[0], square.limb[1], bound.unit, bound.tiny);
    check(lost == 1.0 && kept.limb[0] == 1.0 && kept.limb[1] == tiny, "the sum keeps 2^-60");
    check(square.limb[0] == 1.0 && square.limb[1] == 0x1p-59, "the square is 1 + 2^-59, within its bound");

    // --8<-- [start:unverified]
    // Subtraction has no checked proof yet: it compiles only with the marker on an operand.
    const Number back = kairn::unverified(kept) - 1.0;  // 2^-60
    // --8<-- [end:unverified]
    check(back.limb[0] == tiny && back.limb[1] == 0.0, "(1 + 2^-60) - 1 is 2^-60");

    // --8<-- [start:ball]
    // A side of 3 known to within 1/8: the ball of center 3 and radius 1/8, [2.875, 3.125].
    const kairn::Ball<double, 2> side(Number(3.0), 0.125);
    // Every product x * y of two points of it lies in the result; Ball operations are not proved
    // yet, so the marker is needed here too.
    const auto area = kairn::unverified(side) * side;
    // --8<-- [end:ball]
    std::printf("area: center %a + %a, radius %a\n", area.center().limb[0], area.center().limb[1], area.radius());
    // The exact range is [2.875^2, 3.125^2] = [8.265625, 9.765625]; the radius is 2 * 3 / 8 + 1/64
    // plus a few units of rounding, so the ball is [9 - r, 9 + r] with r just above 0.765625.
    check(area.center().limb[0] == 9.0 && area.center().limb[1] == 0.0, "the center is 9");
    check(area.radius() >= 0.765625 && area.radius() - 0.765625 < 0x1p-40, "the radius covers the range, tightly");
    return failures == 0 ? 0 : 1;
}
