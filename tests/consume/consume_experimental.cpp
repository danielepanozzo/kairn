// The consumer checks' program of the experimental headers (tests/experimental/CMakeLists.txt,
// experimental.consume.*): EXPERIMENTAL, NOT VERIFIED, opt-in, like the headers, in which no bound
// is proved. It compiles only if linking kairn::upward and kairn::fma is enough to include every
// header of kairn/experimental/ in a file that defines KAIRN_EXPERIMENTAL_UNVERIFIED first, as
// docs/concepts/experimental.md says; it runs an operation of each type and of the two-limb
// functions on arrays, and fails unless each result contains the exact value (computed by hand
// below).
#define KAIRN_EXPERIMENTAL_UNVERIFIED
#include <kairn/experimental/upward2.hpp>
#include <kairn/experimental/upward2_arrays.hpp>
#include <kairn/experimental/upward4.hpp>
#if __has_include(<kairn/experimental/upward4_arrays.hpp>)
#include <kairn/experimental/upward4_arrays.hpp>
#define CONSUME_UPWARD4_ARRAYS 1
#else
#define CONSUME_UPWARD4_ARRAYS 0
#endif

#include <cstdio>

namespace u2 = kairn::experimental::upward2;
namespace u4 = kairn::experimental::upward4;

int main() {
    volatile double a = 1 + 0x1p-52;
    u2::Interval p2;
    u4::Interval p4;
    double uh[1], ul[1], nh[1], nl[1];
    {
        kairn::upward::Scope scope;
        // (1 + 2^-52)^2 = 1 + 2^-51 + 2^-104, which two limbs hold exactly.
        p2 = u2::Interval(a) * u2::Interval(a);
        // (1 + 2^-52)^3 - 1 - 3 2^-52 - 3 2^-104 = 2^-156, which four limbs hold exactly.
        p4 = u4::Interval(a) * u4::Interval(a) * u4::Interval(a) - 1.0 - 0x3p-52 - 0x3p-104;
        const double xu[1] = {1.0}, xz[1] = {0.0};   // the interval [1, 1]: (uh, ul) = (1, 0), (nh, nl) = (-1, 0)
        const double xn[1] = {-1.0};
        const u2::View<const double> x{xu, xz, xn, xz, 1};
        const u2::View<double> z{uh, ul, nh, nl, 1};
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
    if (!(uh[0] == 2 && ul[0] == 0 && nh[0] == -2 && nl[0] == 0)) {
        std::printf("upward2 arrays: [1, 1] + [1, 1] is not [2, 2]\n");
        ++failures;
    }
    if (failures == 0)
        std::printf("the experimental headers (NOT VERIFIED): upward2.hpp, upward2_arrays.hpp, upward4.hpp%s\n",
                    CONSUME_UPWARD4_ARRAYS ? ", upward4_arrays.hpp" : "");
    return failures == 0 ? 0 : 1;
}
