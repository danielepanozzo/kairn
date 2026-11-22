// The example of "The floating-point environment" (docs/concepts/environment.md): the two checks a
// program makes at run time, and a product the program passes in, which the guard keeps rounded
// under every contraction setting. ctest builds and runs it with the build's flags and under each
// contraction setting (tests/api/CMakeLists.txt, api.example.concepts_environment) and compares what
// it prints with concepts_environment.txt, which the page shows; it also checks each result itself
// and exits with 1 if one is not what the page says.
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

}  // namespace

int main() {
    // --8<-- [start:checks]
    // Once at startup: what the compiler did with this file's flags, and the environment now.
    const kairn::Status status = kairn::self_test();
    if (!status) {
        std::fprintf(stderr, "kairn::self_test: %s\n", status.message());
        return 1;
    }
    // Before Kairn, after code that may have changed the rounding mode or flush to zero.
    const bool environment = kairn::environment_ok();
    // --8<-- [end:checks]
    std::printf("kairn::self_test():      %s\n", status.message());
    std::printf("kairn::environment_ok(): %s\n", environment ? "true" : "false");
    check(environment, "the environment is the default one");

    // --8<-- [start:guard]
    using Number = kairn::Expansion<double, 2>;
    // Operands the compiler cannot see: (1 + 2^-30)(1 - 2^-30) = 1 - 2^-60 exactly, which rounds to 1.
    volatile double va = 1 + 0x1p-30, vb = 1 - 0x1p-30;
    const double a = va, b = vb;
    // A product of the program passed straight into an operation of two limbs. A compiler that
    // contracts across statements could fuse it into the error-free sum inside the kernel; the
    // kernel's guard makes it the product rounded to double first, as written.
    const Number passed = Number(1.0) + a * b;
    // The same operation on the product rounded and stored, which nothing can fuse.
    volatile double stored = a * b;
    const Number rounded = Number(1.0) + double(stored);
    // --8<-- [end:guard]
    const bool same = passed.limb[0] == rounded.limb[0] && passed.limb[1] == rounded.limb[1];
    std::printf("1 + a * b:               %s + %s\n", hex(passed.limb[0]).c_str(), hex(passed.limb[1]).c_str());
    std::printf("1 + (a * b rounded):     %s + %s\n", hex(rounded.limb[0]).c_str(), hex(rounded.limb[1]).c_str());
    std::printf("the same bits:           %s\n", same ? "yes" : "no");
    check(same, "the product passed in is the rounded product");
    check(rounded.limb[0] == 2.0 && rounded.limb[1] == 0.0, "1 + RN(ab) = 1 + 1 = 2");
    return failures == 0 ? 0 : 1;
}
