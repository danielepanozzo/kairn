// The consumer checks' program of the experimental headers (tests/experimental/CMakeLists.txt,
// experimental.consume.*): EXPERIMENTAL, NOT VERIFIED, opt-in, like the headers, in which no bound
// is proved. It compiles only if linking kairn::upward and kairn::fma is enough to include every
// header of kairn/experimental/ in a file that defines KAIRN_EXPERIMENTAL_UNVERIFIED first, as
// docs/concepts/experimental.md says, and the project compiles it with -Wall -Wextra -Wpedantic
// -Werror, as a client may; it runs an operation of each type and of the functions on arrays of two
// and of four limbs, and fails unless each result contains the exact value (computed by hand below)
// and the four-limb function on arrays gives the type's operator's result bit for bit.
#define KAIRN_EXPERIMENTAL_UNVERIFIED
#include <kairn/experimental/upward2.hpp>
#include <kairn/experimental/upward2_arrays.hpp>
#include <kairn/experimental/upward4.hpp>
#include <kairn/experimental/upward4_arrays.hpp>

#include <cstdio>
#include <cstring>

namespace u2 = kairn::experimental::upward2;
namespace u4 = kairn::experimental::upward4;

int main() {
    volatile double a = 1 + 0x1p-52;
    u2::Interval p2;
    u4::Interval p4;
    // Arrays of four elements, as wide as the widest register of the functions on arrays (AVX2), all
    // the same interval: GCC may warn (-Warray-bounds) of a vector loop that cannot run on arrays of
    // a known length below it.
    constexpr int kE = 4;
    double uh[kE], ul[kE], nh[kE], nl[kE];
    // Four-limb elements [a, a] in the eight arrays of upward4::View: u = (a, 0, 0, 0), n = (-a, 0, 0, 0).
    double au[kE], an[kE], zero[kE];
    for (int k = 0; k < kE; ++k) {
        au[k] = a;
        an[k] = -a;
        zero[k] = 0;
    }
    const u4::View<const double> x4{{au, zero, zero, zero}, {an, zero, zero, zero}, kE};
    double zu[4][kE], zn[4][kE];
    const u4::View<double> z4{{zu[0], zu[1], zu[2], zu[3]}, {zn[0], zn[1], zn[2], zn[3]}, kE};
    u4::mul(z4, x4, x4);   // holds its own scope: called here, where the mode is to nearest
    u4::Interval q4;
    {
        kairn::upward::Scope scope;
        q4 = u4::Interval(a) * u4::Interval(a);
        // (1 + 2^-52)^2 = 1 + 2^-51 + 2^-104, which two limbs hold exactly.
        p2 = u2::Interval(a) * u2::Interval(a);
        // (1 + 2^-52)^3 - 1 - 3 2^-52 - 3 2^-104 = 2^-156, which four limbs hold exactly.
        p4 = u4::Interval(a) * u4::Interval(a) * u4::Interval(a) - 1.0 - 0x3p-52 - 0x3p-104;
        // The interval [1, 1] in the four arrays of upward2::View: (uh, ul) = (1, 0), (nh, nl) = (-1, 0).
        double xu[kE], xn[kE];
        for (int k = 0; k < kE; ++k) {
            xu[k] = 1;
            xn[k] = -1;
        }
        const u2::View<const double> x{xu, zero, xn, zero, kE};
        const u2::View<double> z{uh, ul, nh, nl, kE};
        u2::add(z, x, x);   // [2, 2]
    }
    int failures = 0;
    if (!(p2.lower() <= 1 + 0x1p-51 && p2.upper() >= 1 + 0x1p-51 + 0x1p-52) || !p2.certainly_positive()) {
        std::printf("upward2: the square of 1 + 2^-52 is not contained\n");
        ++failures;
    }
    if (!(p4.lower() == 0x1p-156 && p4.upper() == 0x1p-156)) {
        std::printf("upward4: (1 + 2^-52)^3 - 1 - 3 2^-52 - 3 2^-104 is not [2^-156, 2^-156]: [%a, %a]\n",
                    p4.lower(), p4.upper());
        ++failures;
    }
    for (int k = 0; k < kE; ++k)
        if (!(uh[k] == 2 && ul[k] == 0 && nh[k] == -2 && nl[k] == 0)) {
            std::printf("upward2 arrays: [1, 1] + [1, 1] is not [2, 2] at %d\n", k);
            ++failures;
        }
    // The square of a = 1 + 2^-52 is 1 + 2^-51 + 2^-104: four limbs hold it, so both bounds are it,
    // the upper one as (1 + 2^-51 + 2^-52, -(2^-52 - 2^-104), 0, 0) and the lower one exactly.
    double op[8], ar[8];
    q4.to_limbs(op);
    for (int k = 0; k < kE; ++k) {
        for (int i = 0; i < 4; ++i) {
            ar[2 * i] = zu[i][k];
            ar[2 * i + 1] = zn[i][k];
        }
        if (std::memcmp(op, ar, sizeof op) != 0) {
            std::printf("upward4 arrays: mul differs from the operator's result at %d\n", k);
            ++failures;
        }
    }
    if (!(q4.lower() == 1 + 0x1p-51 && q4.upper() == 1 + 0x1p-51 + 0x1p-52 && op[2] == -(0x1p-52 - 0x1p-104) &&
          op[3] == -0x1p-104)) {
        std::printf("upward4: the square of 1 + 2^-52 is not held exactly\n");
        ++failures;
    }
    if (failures == 0)
        std::printf("the experimental headers (NOT VERIFIED): upward2.hpp, upward2_arrays.hpp, upward4.hpp, "
                    "upward4_arrays.hpp\n");
    return failures == 0 ? 0 : 1;
}
