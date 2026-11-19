// A program compiled on purpose with flags that break Kairn but that the preprocessor cannot see
// (Clang defines no macro for -fassociative-math, -fno-signed-zeros or -freciprocal-math, and
// Apple clang none for -ffp-model=fast): kairn::self_test() must notice. Exits 0 when it does.
#include <kairn/kairn.hpp>

#include <cstdio>

int main() {
    const kairn::Status s = kairn::self_test();
    std::printf("self_test: %s%s%s\n", s.message(), s.kernel ? ": " : "", s.kernel ? s.kernel : "");
    if (s.ok()) {
        std::printf("FAILED: the self-test passed in a build whose flags break Kairn\n");
        return 1;
    }
    return 0;
}
