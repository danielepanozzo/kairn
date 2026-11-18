// Phase 0 experiment: what makes MSVC add a /GS security cookie to functions that only hold an
// Expansion<double, 1>? GS_VARIANT: 0 = class template with `T limb[1]` and friend operators
// returning by braced list (as proto.hpp); 1 = the same, operators return Expansion(x);
// 2 = the same as 0 with a scalar member instead of the array.
#include <cstddef>
#if defined(_MSC_VER) && !defined(__clang__)
#define NOINLINE __declspec(noinline)
#else
#define NOINLINE __attribute__((noinline))
#endif
template <class T, int K> struct Expansion;
template <class T> struct Expansion<T, 1> {
#if GS_VARIANT == 2
    T limb0 = {};
    constexpr Expansion() = default;
    constexpr Expansion(T x) : limb0{x} {}
    constexpr T get() const { return limb0; }
#else
    T limb[1] = {};
    constexpr Expansion() = default;
    constexpr Expansion(T x) : limb{x} {}
    constexpr T get() const { return limb[0]; }
#endif
#if GS_VARIANT == 1
    friend constexpr Expansion operator+(Expansion a, Expansion b) { return Expansion(a.get() + b.get()); }
    friend constexpr Expansion operator*(Expansion a, Expansion b) { return Expansion(a.get() * b.get()); }
#else
    friend constexpr Expansion operator+(Expansion a, Expansion b) { return {a.get() + b.get()}; }
    friend constexpr Expansion operator*(Expansion a, Expansion b) { return {a.get() * b.get()}; }
#endif
};
using E1 = Expansion<double, 1>;
NOINLINE double dot_plain(const double *x, const double *y, std::size_t n) {
    double s = 0;
    for (std::size_t i = 0; i < n; ++i) s = s + x[i] * y[i];
    return s;
}
NOINLINE double dot_k1(const E1 *x, const E1 *y, std::size_t n) {
    E1 s;
    for (std::size_t i = 0; i < n; ++i) s = s + x[i] * y[i];
    return s.get();
}
