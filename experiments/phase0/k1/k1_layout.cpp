// Phase 0 experiment: which storage layout lets Expansion<T, 1> compile like plain T on MSVC?
// K1_LAYOUT: 0 = C array member `T limb[1]`, 1 = one scalar member, 2 = std::array<T, 1>.
// Same three function pairs as k1.cpp; compare.py reads the listing.
#include <array>
#include <cstddef>

#if defined(_MSC_VER) && !defined(__clang__)
#define NOINLINE __declspec(noinline)
#else
#define NOINLINE __attribute__((noinline))
#endif

struct E1 {
#if K1_LAYOUT == 0
    double limb[1] = {};
    constexpr double get() const { return limb[0]; }
#elif K1_LAYOUT == 1
    double limb0 = 0;
    constexpr double get() const { return limb0; }
#else
    std::array<double, 1> limb = {};
    constexpr double get() const { return limb[0]; }
#endif
    constexpr E1() = default;
#if K1_LAYOUT == 1
    constexpr E1(double x) : limb0(x) {}
#else
    constexpr E1(double x) : limb{x} {}
#endif
    friend constexpr E1 operator+(E1 a, E1 b) { return E1(a.get() + b.get()); }
    friend constexpr E1 operator*(E1 a, E1 b) { return E1(a.get() * b.get()); }
};

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
    return s.get();
}
NOINLINE double horner_plain(const std::array<double, 8> &c, double x) {
    double r = c[7];
    for (int i = 6; i >= 0; --i) r = r * x + c[i];
    return r;
}
NOINLINE double horner_k1(const std::array<E1, 8> &c, double x) {
    E1 r = c[7];
    for (int i = 6; i >= 0; --i) r = r * E1(x) + c[i];
    return r.get();
}
