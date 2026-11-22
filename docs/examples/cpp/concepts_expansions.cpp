// The example of "Numbers of several limbs" (docs/concepts/expansions.md): 1 + 2^-60 as two
// doubles, what normalized means, and what the operators return at overflow and for infinities and
// NaN. ctest builds and runs it (tests/api/CMakeLists.txt, api.example.concepts_expansions) and
// compares what it prints with concepts_expansions.txt, which the page shows; it also checks each
// result itself and exits with 1 if one is not what the page says.
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

const char* yes(bool b) { return b ? "yes" : "no"; }

}  // namespace

int main() {
    using concepts::hex;

    // --8<-- [start:limbs]
    using Number = kairn::Expansion<double, 2>;

    // 1 + 2^-60 needs 61 significant bits; a double has 53, so the sum of two doubles rounds it to 1.
    const double tiny = 0x1p-60;
    const double rounded = 1.0 + tiny;    // 1
    const Number x = Number(1.0) + tiny;  // limbs 1 and 2^-60: the value 1 + 2^-60, exactly
    // --8<-- [end:limbs]
    std::printf("1 + 2^-60 as a double:    %s\n", hex(rounded).c_str());
    std::printf("1 + 2^-60 as two limbs:   %s + %s\n", hex(x.limb[0]).c_str(), hex(x.limb[1]).c_str());
    check(rounded == 1.0, "the double sum rounds to 1");
    check(x.limb[0] == 1.0 && x.limb[1] == tiny, "the two limbs are 1 and 2^-60");
    check(kairn::to_nearest(x) == 1.0, "the leading limb is the value rounded to nearest");

    // --8<-- [start:normalized]
    // 1 + 2^-53 lies halfway between 1 and the next double, 1 + 2^-52, and ties round to 1.
    // Two pairs of doubles have that value; only the first has its value rounded as leading limb.
    const double first[2] = {1.0, 0x1p-53};
    const double second[2] = {1.0 + 0x1p-52, -0x1p-53};
    const bool first_ok = kairn::is_normalized(Number::from_limbs_unchecked(first));    // true
    const bool second_ok = kairn::is_normalized(Number::from_limbs_unchecked(second));  // false
    // --8<-- [end:normalized]
    std::printf("(1, 2^-53) normalized:            %s\n", yes(first_ok));
    std::printf("(1 + 2^-52, -2^-53) normalized:   %s\n", yes(second_ok));
    check(first_ok && !second_ok, "only the first pair is normalized");

    // --8<-- [start:special]
    const Number big(0x1p1023);
    const Number sum = big + big;                      // 2^1024 overflows: (+inf, 0)
    const Number nan = sum - sum;                      // inf - inf: (NaN, NaN)
    const Number core = kairn::finite::add(big, big);  // the core alone: a leading limb that is not finite
    // --8<-- [end:special]
    std::printf("2^1023 + 2^1023:                  %s + %s\n", hex(sum.limb[0]).c_str(), hex(sum.limb[1]).c_str());
    std::printf("(inf, 0) - (inf, 0):              %s + %s\n", hex(nan.limb[0]).c_str(), hex(nan.limb[1]).c_str());
    std::printf("finite::add(2^1023, 2^1023) is finite: %s\n", yes(kairn::isfinite(core)));
    check(sum.limb[0] == std::numeric_limits<double>::infinity() && sum.limb[1] == 0, "the overflow is (+inf, 0)");
    check(nan.limb[0] != nan.limb[0] && nan.limb[1] != nan.limb[1], "inf - inf is (NaN, NaN)");
    check(!kairn::isfinite(core), "the core's result is not finite");
    return failures == 0 ? 0 : 1;
}
