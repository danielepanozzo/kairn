// What makes MSVC put a /GS stack cookie into functions that use Expansion<double, 1>
// (bench/gs_probe.py isolate; bench/README.md, "MSVC's stack cookie"). Each variant is a one-limb
// type V with + and *, compiled alone (GS_VARIANT=N) into the same four functions; gs_probe.py
// reports which of them read __security_cookie. The variants change one thing at a time from
// variant 1, which has the members and the operators of Expansion<T, 1> without Kairn:
//
// 0: Kairn's own Expansion<double, 1>
// 1: class template partial specialization X<T, 1>, T limb[1] = {}, constexpr constructors, hidden friend operators taking V by value
// 2: as 1, a plain struct instead of a template
// 3: as 1, the primary template X<T> instead of a partial specialization
// 4: as 1, the friends take const V&
// 5: as 1, free function templates instead of hidden friends, taking V by value
// 6: as 1, no default member initializer (T limb[1];)
// 7: as 1, a scalar member T limb0 = {} instead of the array
// 8: as 1, without the constructor from T (aggregate initialization)
// 9: as 1, the friends are function templates of the plain struct of 2 (a template, no class template)
// 10: as 6 and 4 together: no initializer, friends by reference
// 11: Kairn's Expansion<double, 2>, the leading limb only, for comparison
#include <cstddef>

#if defined(_MSC_VER) && !defined(__clang__)
#define GS_NOINLINE __declspec(noinline)
#else
#define GS_NOINLINE __attribute__((noinline))
#endif

#if GS_VARIANT == 0 || GS_VARIANT == 11
#include <kairn/kairn.hpp>
#endif

#if GS_VARIANT == 0
using V = kairn::Expansion<double, 1>;
inline double get(const V& x) { return x.limb[0]; }
#elif GS_VARIANT == 11
using V = kairn::Expansion<double, 2>;
inline double get(const V& x) { return x.limb[0]; }
#elif GS_VARIANT == 2
struct V {
    double limb[1] = {};
    constexpr V() noexcept = default;
    constexpr V(double x) noexcept : limb{x} {}
    friend V operator+(V x, V y) noexcept { return V(x.limb[0] + y.limb[0]); }
    friend V operator*(V x, V y) noexcept { return V(x.limb[0] * y.limb[0]); }
};
inline double get(const V& x) { return x.limb[0]; }
#elif GS_VARIANT == 9
struct V {
    double limb[1] = {};
    constexpr V() noexcept = default;
    constexpr V(double x) noexcept : limb{x} {}
};
template <class X>
X operator+(X x, X y) noexcept {
    return X(x.limb[0] + y.limb[0]);
}
template <class X>
X operator*(X x, X y) noexcept {
    return X(x.limb[0] * y.limb[0]);
}
inline double get(const V& x) { return x.limb[0]; }
#elif GS_VARIANT == 3
template <class T>
struct X {
    T limb[1] = {};
    constexpr X() noexcept = default;
    constexpr X(T x) noexcept : limb{x} {}
    friend X operator+(X x, X y) noexcept { return X(x.limb[0] + y.limb[0]); }
    friend X operator*(X x, X y) noexcept { return X(x.limb[0] * y.limb[0]); }
};
using V = X<double>;
inline double get(const V& x) { return x.limb[0]; }
#else
template <class T, int K>
struct X;
template <class T>
struct X<T, 1> {
#if GS_VARIANT == 6 || GS_VARIANT == 10
    T limb[1];
    constexpr X() noexcept : limb{} {}
#elif GS_VARIANT == 7
    T limb0 = {};
    constexpr X() noexcept = default;
#else
    T limb[1] = {};
#if GS_VARIANT != 8
    constexpr X() noexcept = default;
#endif
#endif
#if GS_VARIANT == 7
    constexpr X(T x) noexcept : limb0{x} {}
    T value() const noexcept { return limb0; }
#elif GS_VARIANT == 8
    T value() const noexcept { return limb[0]; }
#else
    constexpr X(T x) noexcept : limb{x} {}
    T value() const noexcept { return limb[0]; }
#endif
#if GS_VARIANT == 8
#define GS_MAKE(v) X{{v}}
#else
#define GS_MAKE(v) X(v)
#endif
#if GS_VARIANT == 4 || GS_VARIANT == 10
    friend X operator+(const X& x, const X& y) noexcept { return GS_MAKE(x.value() + y.value()); }
    friend X operator*(const X& x, const X& y) noexcept { return GS_MAKE(x.value() * y.value()); }
#elif GS_VARIANT != 5
    friend X operator+(X x, X y) noexcept { return GS_MAKE(x.value() + y.value()); }
    friend X operator*(X x, X y) noexcept { return GS_MAKE(x.value() * y.value()); }
#endif
};
#if GS_VARIANT == 5
template <class T>
X<T, 1> operator+(X<T, 1> x, X<T, 1> y) noexcept {
    return X<T, 1>(x.value() + y.value());
}
template <class T>
X<T, 1> operator*(X<T, 1> x, X<T, 1> y) noexcept {
    return X<T, 1>(x.value() * y.value());
}
#endif
using V = X<double, 1>;
inline double get(const V& x) { return x.value(); }
#endif

extern "C" GS_NOINLINE void gs_add(const V& x, const V& y, V* z) { *z = x + y; }
extern "C" GS_NOINLINE double gs_add_value(const V& x, const V& y) { return get(x + y); }
extern "C" GS_NOINLINE void gs_dot(const V* x, const V* y, std::size_t n, V* out) {
    V s{};
    for (std::size_t i = 0; i < n; ++i) s = s + x[i] * y[i];
    *out = s;
}
extern "C" GS_NOINLINE void gs_tp_add(const V* x, const V* y, V* z, std::size_t n) {
    for (std::size_t i = 0; i < n; ++i) z[i] = x[i] + y[i];
}
