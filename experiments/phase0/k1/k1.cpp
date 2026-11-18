// Phase 0 experiment: does Expansion<T, 1> cost what plain T costs? Each pair of functions is
// the same code on double and on Expansion<double, 1>; compare.py checks that the compiler
// emits the same instructions for both (after removing labels and symbol names).
#include <array>
#include <cstddef>
#include "../constexpr/proto.hpp"
using E1 = proto::Expansion<double, 1>;

#if defined(_MSC_VER) && !defined(__clang__)
#define NOINLINE __declspec(noinline)
#else
#define NOINLINE __attribute__((noinline))
#endif

NOINLINE void axpy_plain(double a, const double *x, double *y, std::size_t n) {
    for (std::size_t i = 0; i < n; ++i) y[i] = a * x[i] + y[i];
}
NOINLINE void axpy_k1(E1 a, const E1 *x, E1 *y, std::size_t n) {
    for (std::size_t i = 0; i < n; ++i) y[i] = a * x[i] + y[i];
}
NOINLINE double dot_plain(const double *x, const double *y, std::size_t n) {
    double s = 0;
    for (std::size_t i = 0; i < n; ++i) s = s + x[i] * y[i];
    return s;
}
NOINLINE double dot_k1(const E1 *x, const E1 *y, std::size_t n) {
    E1 s;
    for (std::size_t i = 0; i < n; ++i) s = s + x[i] * y[i];
    return s.limb[0];
}
NOINLINE double horner_plain(const std::array<double, 8> &c, double x) {
    double r = c[7];
    for (int i = 6; i >= 0; --i) r = r * x + c[i];
    return r;
}
NOINLINE double horner_k1(const std::array<E1, 8> &c, double x) {
    E1 r = c[7];
    for (int i = 6; i >= 0; --i) r = r * E1(x) + c[i];
    return r.limb[0];
}
