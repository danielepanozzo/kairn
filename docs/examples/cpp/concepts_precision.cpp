// The example of "Precision and magnitude" (docs/concepts/precision.md): a second limb adds bits
// and not range; below a magnitude that depends on the type, a two-limb number has fewer bits; and
// the constants of the error bounds that kairn::traits exports for the four types. ctest builds and
// runs it (tests/api/CMakeLists.txt, api.example.concepts_precision) and compares what it prints with
// concepts_precision.txt, which the page shows; it also checks each result itself and exits with 1
// if one is not what the page says.
#include <kairn/kairn.hpp>

#include <cmath>
#include <cstdio>
#include <limits>

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

// --8<-- [start:table]
// The bits of X and the constants of the bounds of its sums and products, as kairn::traits exports
// them: |computed - exact| <= unit |exact| + tiny, unit and tiny rounded up to the limb type.
template <class X>
void row(const char* name) {
    using traits = kairn::traits<X>;
    static_assert(traits::add.verified && traits::mul.verified);
    std::printf("%-22s %3d bits   x + y: %-22s  x * y: %s, %s\n", name, traits::precision, hex(traits::add.unit).c_str(),
                hex(traits::mul.unit).c_str(), hex(traits::mul.tiny).c_str());
}
// --8<-- [end:table]

// The smallest magnitude from which X has all its bits, 2^(precision - 1) eta (eta the smallest
// subnormal number of its limb type), as Getting started computes it.
template <class X>
double full_precision_from() {
    using T = typename kairn::traits<X>::limb_type;
    return std::ldexp(double(std::numeric_limits<T>::denorm_min()), kairn::traits<X>::precision - 1);
}

}  // namespace

int main() {
    // --8<-- [start:range]
    using D2 = kairn::Expansion<double, 2>;
    using F2 = kairn::Expansion<float, 2>;

    // A second limb adds bits, not range: 2^200 is a double, and beyond the range of float, in one
    // limb or in two.
    const double d = 0x1p100 * 0x1p100;    // 2^200
    const F2 f = F2(0x1p100f) * 0x1p100f;  // overflows: (+inf, 0)

    // Below 2^-969 a two-limb double has fewer than 106 bits. 1 + 2^-60 scaled by 2^-30 keeps both
    // limbs; scaled by 2^-1030, its second limb would be 2^-1090, below the smallest double, 2^-1074.
    const D2 x = D2(1.0) + 0x1p-60;
    const D2 high = x * 0x1p-30;    // 2^-30 + 2^-90, exactly
    const D2 low = x * 0x1p-1030;   // 2^-1030: the 2^-1090 is lost
    // --8<-- [end:range]
    std::printf("2^100 * 2^100, double:                 %s\n", hex(d).c_str());
    std::printf("2^100 * 2^100, Expansion<float, 2>:    %s + %s\n", hex(f.limb[0]).c_str(), hex(f.limb[1]).c_str());
    std::printf("(1 + 2^-60) * 2^-30,   two limbs:      %s + %s\n", hex(high.limb[0]).c_str(), hex(high.limb[1]).c_str());
    std::printf("(1 + 2^-60) * 2^-1030, two limbs:      %s + %s\n", hex(low.limb[0]).c_str(), hex(low.limb[1]).c_str());
    check(d == 0x1p200, "2^200 is a double");
    check(f.limb[0] == std::numeric_limits<float>::infinity() && f.limb[1] == 0, "2^200 overflows float, two limbs");
    check(high.limb[0] == 0x1p-30 && high.limb[1] == 0x1p-90, "at 2^-30 both limbs are kept");
    check(low.limb[0] == 0x1p-1030 && low.limb[1] == 0, "at 2^-1030 the second limb is lost");
    // The error, 2^-1090, is below the absolute term of the bound of x * a, 2u^2 |x a| + eta: eta is
    // 2^-1074, which kairn::traits exports as the tiny of mul_limb.
    check(kairn::traits<D2>::mul_limb.tiny == 0x1p-1074, "the absolute term of x * a is eta");

    std::printf("\n");
    row<double>("double");
    row<kairn::Expansion<double, 2>>("Expansion<double, 2>");
    row<float>("float");
    row<kairn::Expansion<float, 2>>("Expansion<float, 2>");
    check(full_precision_from<double>() == 0x1p-1022 && full_precision_from<D2>() == 0x1p-969, "the thresholds of double");
    check(full_precision_from<float>() == 0x1p-126 && full_precision_from<F2>() == 0x1p-102, "the thresholds of float");
    return failures == 0 ? 0 : 1;
}
