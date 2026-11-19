// Choosing the limb type T and the number of limbs k: the precision kairn::traits gives each type,
// the magnitude from which a type has all of it, and a product that loses its last bit below that
// magnitude. Built and run by ctest (tests/api/CMakeLists.txt), which fails if a check fails; the
// "Getting started" page shows its sections, and its table of precisions has the numbers checked
// here.
#include <kairn/kairn.hpp>

#include <cmath>
#include <cstdio>
#include <limits>

namespace {

int failures = 0;

void check(bool ok, const char* what) {
    std::printf("%s %s\n", ok ? "ok    " : "FAILED", what);
    failures += ok ? 0 : 1;
}

// --8<-- [start:threshold]
// The smallest magnitude from which X has all its bits: 2^(precision - 1) times the smallest
// subnormal number of its limb type. Below it, one bit is lost per binade.
template <class X>
typename kairn::traits<X>::limb_type full_precision_from() {
    using T = typename kairn::traits<X>::limb_type;
    return std::ldexp(std::numeric_limits<T>::denorm_min(), kairn::traits<X>::precision - 1);
}
// --8<-- [end:threshold]

}  // namespace

int main() {
    // The table of the page: bits, and the magnitude from which a type has them all.
    // --8<-- [start:alias]
    using Real = kairn::Expansion<double, 2>;  // 106 bits, for magnitudes from about 2e-292 up
    static_assert(kairn::traits<Real>::precision == 106);
    // --8<-- [end:alias]
    using D1 = kairn::Expansion<double, 1>;
    using F1 = kairn::Expansion<float, 1>;
    static_assert(kairn::traits<D1>::precision == 53 && kairn::traits<double>::precision == 53);
    static_assert(kairn::traits<F1>::precision == 24 && kairn::traits<float>::precision == 24);
    check(full_precision_from<D1>() == 0x1p-1022 && full_precision_from<D1>() == std::numeric_limits<double>::min(),
          "Expansion<double, 1>: all 53 bits from 2^-1022, the smallest normal double");
    check(full_precision_from<Real>() == 0x1p-969, "Expansion<double, 2>: all 106 bits from 2^-969");
    check(full_precision_from<F1>() == 0x1p-126f && full_precision_from<F1>() == std::numeric_limits<float>::min(),
          "Expansion<float, 1>: all 24 bits from 2^-126, the smallest normal float");

    // --8<-- [start:below]
    using F2 = kairn::Expansion<float, 2>;
    // a^2 = 1 + 2^-22 + 2^-46 needs 47 bits. Expansion<float, 2> keeps them all at 2^-4, but
    // not at 2^-104, below 2^-102: there its last term, 2^-150, is below the smallest float.
    const float a = 1 + 0x1p-23f;
    const F2 high = F2(a) * (0x1p-4f * a);    // (2^-4 + 2^-26) + 2^-50, exactly
    const F2 low = F2(a) * (0x1p-104f * a);   // (2^-104 + 2^-126) + 0: 2^-150 is lost
    // --8<-- [end:below]
    static_assert(kairn::traits<F2>::precision == 48);
    check(full_precision_from<F2>() == 0x1p-102f, "Expansion<float, 2>: all 48 bits from 2^-102");
    std::printf("high: %a + %a\nlow: %a + %a\n", double(high.limb[0]), double(high.limb[1]), double(low.limb[0]),
                double(low.limb[1]));
    check(high.limb[0] == 0x1p-4f + 0x1p-26f && high.limb[1] == 0x1p-50f, "at 2^-4 the product is exact");
    check(low.limb[0] == 0x1p-104f + 0x1p-126f && low.limb[1] == 0.0f,
          "at 2^-104 it loses 2^-150, within the bound of mul_2_1: 2u^2 |exact| + eta");
    return failures == 0 ? 0 : 1;
}
