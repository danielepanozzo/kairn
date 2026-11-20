// Does Expansion<double, 1> cost what double costs? Each pair of functions is the same code (one
// operation, or a loop) on double and on Expansion<double, 1>, written with Kairn's public
// interface; zero_cost.py compiles
// this file to assembly and compares the instructions of each pair
// (docs/developer/design/phase0/library.md, "One limb"; the Phase 0 version is
// experiments/phase0/k1/).
//
// One-limb + and * need the kairn::unverified marker while their kernels (add_1_1, mul_1_1) are
// unverified; plus() and times() use the operator alone once they are proved. Either way the
// marker is a wrapper that the compiler removes, which is part of what this measures.
#include <kairn/kairn.hpp>

#include <array>
#include <cstddef>

using E1 = kairn::Expansion<double, 1>;

#if defined(_MSC_VER) && !defined(__clang__)
#define NOINLINE __declspec(noinline)
#else
#define NOINLINE __attribute__((noinline))
#endif

template <class X, class Y>
KAIRN_FORCEINLINE auto plus(const X& x, const Y& y) {
    if constexpr (requires { x + y; }) {
        return x + y;
    } else {
        return kairn::unverified(x) + y;
    }
}
template <class X, class Y>
KAIRN_FORCEINLINE auto times(const X& x, const Y& y) {
    if constexpr (requires { x * y; }) {
        return x * y;
    } else {
        return kairn::unverified(x) * y;
    }
}

// One operation stored through a pointer, and a running sum: with MSVC these shapes got a /GS stack
// cookie while the one-limb operators took their operands by value, which zero_cost.py fails on.
// They call the operator directly, which needs add_1_1 proved: through plus() MSVC put no cookie
// in them even then.
NOINLINE void add_plain(const double& x, const double& y, double* z) { *z = x + y; }
NOINLINE void add_k1(const E1& x, const E1& y, E1* z) { *z = x + y; }
NOINLINE void sum_plain(const double* x, std::size_t n, double* out) {
    double s = 0;
    for (std::size_t i = 0; i < n; ++i) s = s + x[i];
    *out = s;
}
NOINLINE void sum_k1(const E1* x, std::size_t n, E1* out) {
    E1 s;
    for (std::size_t i = 0; i < n; ++i) s = s + x[i];
    *out = s;
}
NOINLINE void axpy_plain(double a, const double* x, double* y, std::size_t n) {
    for (std::size_t i = 0; i < n; ++i) y[i] = a * x[i] + y[i];
}
NOINLINE void axpy_k1(E1 a, const E1* x, E1* y, std::size_t n) {
    for (std::size_t i = 0; i < n; ++i) y[i] = plus(times(a, x[i]), y[i]);
}
NOINLINE double dot_plain(const double* x, const double* y, std::size_t n) {
    double s = 0;
    for (std::size_t i = 0; i < n; ++i) s = s + x[i] * y[i];
    return s;
}
NOINLINE double dot_k1(const E1* x, const E1* y, std::size_t n) {
    E1 s;
    for (std::size_t i = 0; i < n; ++i) s = plus(s, times(x[i], y[i]));
    return s.limb[0];
}
NOINLINE double horner_plain(const std::array<double, 8>& c, double x) {
    double r = c[7];
    for (int i = 6; i >= 0; --i) r = r * x + c[i];
    return r;
}
NOINLINE double horner_k1(const std::array<E1, 8>& c, double x) {
    E1 r = c[7];
    for (int i = 6; i >= 0; --i) r = plus(times(r, E1(x)), c[i]);
    return r.limb[0];
}
