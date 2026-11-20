// api.platform_macros: Kairn's headers after a platform header that defines common words as
// macros. <windows.h> defines min and max as function-like macros unless NOMINMAX is defined, and
// through its RPC headers `small` as `char`, `hyper` as `__int64`, `near` and `far` as nothing,
// and `interface` as `struct`; a program that includes it first, as most Windows programs do,
// must still be able to include Kairn. On Windows this includes the real header; on every
// platform it defines those macros itself, so the test runs everywhere. It compiles, uses the
// public operations and the self-test, and checks one result.
#if defined(_WIN32)
#include <windows.h>
#endif

#if !defined(min)
#define min(a, b) (((a) < (b)) ? (a) : (b))
#endif
#if !defined(max)
#define max(a, b) (((a) > (b)) ? (a) : (b))
#endif
#if !defined(small)
#define small char
#endif
#if !defined(hyper)
#define hyper long long
#endif
#if !defined(near)
#define near
#endif
#if !defined(far)
#define far
#endif
#if !defined(interface)
#define interface struct
#endif

#include <kairn/kairn.hpp>

#include <cstdio>

template <class T>
static int run() {
    using E1 = kairn::Expansion<T, 1>;
    using E2 = kairn::Expansion<T, 2>;
    using B1 = kairn::Ball<T, 1>;
    using B2 = kairn::Ball<T, 2>;
    const E2 x = E2(T(1)) + T(0.5);
    const E2 y = x * x - x;  // 1.5 * 1.5 - 1.5 = 0.75, exactly
    const E1 a = E1(T(3)) * E1(T(0.25));
    const E2 z = kairn::ldexp(x, 3);  // 12
    const B1 p = B1(E1(T(1)), T(0.5)) + B1(E1(T(2)), T(0.25));
    const B2 q = B2(x, T(0.125)) * B2(x, T(0));
    int failures = 0;
    if (y.limb[0] != T(0.75) || y.limb[1] != T(0)) ++failures;
    if (a.limb[0] != T(0.75)) ++failures;
    if (z.limb[0] != T(12) || z.limb[1] != T(0)) ++failures;
    if (!p.is_finite() || !(p.radius() >= T(0.75))) ++failures;
    if (!q.is_finite() || !(q.radius() >= T(0.1875))) ++failures;
    return failures;
}

int main() {
    int failures = run<double>() + run<float>();
    const kairn::Status status = kairn::self_test();
    if (!status) {
        std::printf("api.platform_macros: the self-test: %s\n", status.message());
        ++failures;
    }
    if (!kairn::environment_ok()) ++failures;
    std::printf("api.platform_macros: %s\n", failures ? "FAILED" : "ok");
    return failures ? 1 : 0;
}
