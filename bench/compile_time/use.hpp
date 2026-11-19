// Every public operation of Expansion<T, 1>, Expansion<T, 2> and Ball<T, K>, once each, for the
// compile-time measurements (bench/compile_time.py, bench/README.md, "Compile time"). The list is
// the one of docs/reference/index.md: constructors and access, arithmetic and its compound
// assignments, kairn::finite::, comparisons, conversions to one limb, ldexp and half, and the Ball
// operations, with every order of operands that the reference lists.
//
// Each operation is a static member function of its own that the compiler may not inline, as a
// client's code is spread over many functions; an explicit instantiation of one of the structures
// below (use_e2.cpp, use_all.cpp) makes the compiler emit all of its members.
#pragma once

#include <kairn/kairn.hpp>

#if defined(_MSC_VER) && !defined(__clang__)
#define KCT_NOINLINE __declspec(noinline)
#else
#define KCT_NOINLINE __attribute__((noinline))
#endif

namespace kct {

using kairn::Ball;
using kairn::Expansion;
namespace finite = kairn::finite;

template <class T>
struct UseE1 {
    using E = Expansion<T, 1>;
    // Construction and access.
    static KCT_NOINLINE E zero() { return E(); }
    static KCT_NOINLINE E make(T a) { return E(a); }
    static KCT_NOINLINE E from_limbs(const T* p) { return E::from_limbs(p); }
    static KCT_NOINLINE E from_limbs_unchecked(const T* p) { return E::from_limbs_unchecked(p); }
    static KCT_NOINLINE T limb(const E& x) { return x.limb[0]; }
    static KCT_NOINLINE int sign(const E& x) { return kairn::sign(x); }
    static KCT_NOINLINE bool isfinite(const E& x) { return kairn::isfinite(x); }
    static KCT_NOINLINE bool is_normalized(const E& x) { return kairn::is_normalized(x); }
    // Arithmetic.
    static KCT_NOINLINE E add(E x, E y) { return x + y; }
    static KCT_NOINLINE void add_assign(E& x, E y) { x += y; }
    static KCT_NOINLINE E sub(E x, E y) { return x - y; }
    static KCT_NOINLINE void sub_assign(E& x, E y) { x -= y; }
    static KCT_NOINLINE E mul(E x, E y) { return x * y; }
    static KCT_NOINLINE void mul_assign(E& x, E y) { x *= y; }
    static KCT_NOINLINE E add_fast(E x, E y) { return kairn::add_fast(x, y); }
    static KCT_NOINLINE E neg(E x) { return -x; }
    static KCT_NOINLINE E abs(E x) { return kairn::abs(x); }
    static KCT_NOINLINE E ldexp(E x, int n) { return kairn::ldexp(x, n); }
    static KCT_NOINLINE E half(E x) { return kairn::half(x); }
    // Without the fix-up (for one limb, the operators themselves).
    static KCT_NOINLINE E finite_add(E x, E y) { return finite::add(x, y); }
    static KCT_NOINLINE E finite_sub(E x, E y) { return finite::sub(x, y); }
    static KCT_NOINLINE E finite_add_fast(E x, E y) { return finite::add_fast(x, y); }
    static KCT_NOINLINE E finite_mul(E x, E y) { return finite::mul(x, y); }
    static KCT_NOINLINE E finite_ldexp(E x, int n) { return finite::ldexp(x, n); }
    // Comparisons.
    static KCT_NOINLINE bool lt(E x, E y) { return x < y; }
    static KCT_NOINLINE bool gt(E x, E y) { return x > y; }
    static KCT_NOINLINE bool le(E x, E y) { return x <= y; }
    static KCT_NOINLINE bool ge(E x, E y) { return x >= y; }
    static KCT_NOINLINE bool eq(E x, E y) { return x == y; }
    static KCT_NOINLINE bool ne(E x, E y) { return x != y; }
    // Conversions to one limb.
    static KCT_NOINLINE T to_nearest(E x) { return kairn::to_nearest(x); }
    static KCT_NOINLINE T to_down(E x) { return kairn::to_down(x); }
    static KCT_NOINLINE T to_up(E x) { return kairn::to_up(x); }
    static KCT_NOINLINE T abs_upper(E x) { return kairn::abs_upper(x); }
};

template <class T>
struct UseE2 {
    using E = Expansion<T, 2>;
    using E1 = Expansion<T, 1>;
    // Construction and access.
    static KCT_NOINLINE E zero() { return E(); }
    static KCT_NOINLINE E make(T a) { return E(a); }
    static KCT_NOINLINE E make1(const E1& a) { return E(a); }
    static KCT_NOINLINE E from_limbs(const T* p) { return E::from_limbs(p); }
    static KCT_NOINLINE E from_limbs_unchecked(const T* p) { return E::from_limbs_unchecked(p); }
    static KCT_NOINLINE T limb(const E& x) { return x.limb[1]; }
    static KCT_NOINLINE int sign(const E& x) { return kairn::sign(x); }
    static KCT_NOINLINE bool isfinite(const E& x) { return kairn::isfinite(x); }
    static KCT_NOINLINE bool is_normalized(const E& x) { return kairn::is_normalized(x); }
    // Sums.
    static KCT_NOINLINE E add(const E& x, const E& y) { return x + y; }
    static KCT_NOINLINE void add_assign(E& x, const E& y) { x += y; }
    static KCT_NOINLINE E add_limb(const E& x, T a) { return x + a; }
    static KCT_NOINLINE E limb_add(T a, const E& x) { return a + x; }
    static KCT_NOINLINE void add_assign_limb(E& x, T a) { x += a; }
    static KCT_NOINLINE E add_one(const E& x, const E1& y) { return x + y; }
    static KCT_NOINLINE E one_add(const E1& y, const E& x) { return y + x; }
    static KCT_NOINLINE void add_assign_one(E& x, const E1& y) { x += y; }
    // Differences.
    static KCT_NOINLINE E sub(const E& x, const E& y) { return x - y; }
    static KCT_NOINLINE void sub_assign(E& x, const E& y) { x -= y; }
    static KCT_NOINLINE E sub_limb(const E& x, T a) { return x - a; }
    static KCT_NOINLINE E limb_sub(T a, const E& x) { return a - x; }
    static KCT_NOINLINE void sub_assign_limb(E& x, T a) { x -= a; }
    static KCT_NOINLINE E sub_one(const E& x, const E1& y) { return x - y; }
    static KCT_NOINLINE E one_sub(const E1& y, const E& x) { return y - x; }
    static KCT_NOINLINE void sub_assign_one(E& x, const E1& y) { x -= y; }
    // Products.
    static KCT_NOINLINE E mul(const E& x, const E& y) { return x * y; }
    static KCT_NOINLINE void mul_assign(E& x, const E& y) { x *= y; }
    static KCT_NOINLINE E mul_limb(const E& x, T a) { return x * a; }
    static KCT_NOINLINE E limb_mul(T a, const E& x) { return a * x; }
    static KCT_NOINLINE void mul_assign_limb(E& x, T a) { x *= a; }
    static KCT_NOINLINE E mul_one(const E& x, const E1& y) { return x * y; }
    static KCT_NOINLINE E one_mul(const E1& y, const E& x) { return y * x; }
    static KCT_NOINLINE void mul_assign_one(E& x, const E1& y) { x *= y; }
    // The rest of the arithmetic.
    static KCT_NOINLINE E add_fast(const E& x, const E& y) { return kairn::add_fast(x, y); }
    static KCT_NOINLINE E neg(const E& x) { return -x; }
    static KCT_NOINLINE E abs(const E& x) { return kairn::abs(x); }
    static KCT_NOINLINE E ldexp(const E& x, int n) { return kairn::ldexp(x, n); }
    static KCT_NOINLINE E half(const E& x) { return kairn::half(x); }
    // Without the fix-up.
    static KCT_NOINLINE E finite_add(const E& x, const E& y) { return finite::add(x, y); }
    static KCT_NOINLINE E finite_add_limb(const E& x, T a) { return finite::add(x, a); }
    static KCT_NOINLINE E finite_limb_add(T a, const E& x) { return finite::add(a, x); }
    static KCT_NOINLINE E finite_add_one(const E& x, const E1& y) { return finite::add(x, y); }
    static KCT_NOINLINE E finite_one_add(const E1& y, const E& x) { return finite::add(y, x); }
    static KCT_NOINLINE E finite_sub(const E& x, const E& y) { return finite::sub(x, y); }
    static KCT_NOINLINE E finite_sub_limb(const E& x, T a) { return finite::sub(x, a); }
    static KCT_NOINLINE E finite_limb_sub(T a, const E& x) { return finite::sub(a, x); }
    static KCT_NOINLINE E finite_sub_one(const E& x, const E1& y) { return finite::sub(x, y); }
    static KCT_NOINLINE E finite_one_sub(const E1& y, const E& x) { return finite::sub(y, x); }
    static KCT_NOINLINE E finite_mul(const E& x, const E& y) { return finite::mul(x, y); }
    static KCT_NOINLINE E finite_mul_limb(const E& x, T a) { return finite::mul(x, a); }
    static KCT_NOINLINE E finite_limb_mul(T a, const E& x) { return finite::mul(a, x); }
    static KCT_NOINLINE E finite_mul_one(const E& x, const E1& y) { return finite::mul(x, y); }
    static KCT_NOINLINE E finite_one_mul(const E1& y, const E& x) { return finite::mul(y, x); }
    static KCT_NOINLINE E finite_add_fast(const E& x, const E& y) { return finite::add_fast(x, y); }
    static KCT_NOINLINE E finite_ldexp(const E& x, int n) { return finite::ldexp(x, n); }
    // Comparisons: with another two-limb number, a limb on either side, a one-limb number on
    // either side.
    static KCT_NOINLINE bool lt(const E& x, const E& y) { return x < y; }
    static KCT_NOINLINE bool gt(const E& x, const E& y) { return x > y; }
    static KCT_NOINLINE bool le(const E& x, const E& y) { return x <= y; }
    static KCT_NOINLINE bool ge(const E& x, const E& y) { return x >= y; }
    static KCT_NOINLINE bool eq(const E& x, const E& y) { return x == y; }
    static KCT_NOINLINE bool ne(const E& x, const E& y) { return x != y; }
    static KCT_NOINLINE bool lt_limb(const E& x, T a) { return x < a; }
    static KCT_NOINLINE bool gt_limb(const E& x, T a) { return x > a; }
    static KCT_NOINLINE bool le_limb(const E& x, T a) { return x <= a; }
    static KCT_NOINLINE bool ge_limb(const E& x, T a) { return x >= a; }
    static KCT_NOINLINE bool eq_limb(const E& x, T a) { return x == a; }
    static KCT_NOINLINE bool ne_limb(const E& x, T a) { return x != a; }
    static KCT_NOINLINE bool limb_lt(T a, const E& x) { return a < x; }
    static KCT_NOINLINE bool limb_gt(T a, const E& x) { return a > x; }
    static KCT_NOINLINE bool limb_le(T a, const E& x) { return a <= x; }
    static KCT_NOINLINE bool limb_ge(T a, const E& x) { return a >= x; }
    static KCT_NOINLINE bool limb_eq(T a, const E& x) { return a == x; }
    static KCT_NOINLINE bool limb_ne(T a, const E& x) { return a != x; }
    static KCT_NOINLINE bool lt_one(const E& x, const E1& y) { return x < y; }
    static KCT_NOINLINE bool gt_one(const E& x, const E1& y) { return x > y; }
    static KCT_NOINLINE bool le_one(const E& x, const E1& y) { return x <= y; }
    static KCT_NOINLINE bool ge_one(const E& x, const E1& y) { return x >= y; }
    static KCT_NOINLINE bool eq_one(const E& x, const E1& y) { return x == y; }
    static KCT_NOINLINE bool ne_one(const E& x, const E1& y) { return x != y; }
    static KCT_NOINLINE bool one_lt(const E1& y, const E& x) { return y < x; }
    static KCT_NOINLINE bool one_gt(const E1& y, const E& x) { return y > x; }
    static KCT_NOINLINE bool one_le(const E1& y, const E& x) { return y <= x; }
    static KCT_NOINLINE bool one_ge(const E1& y, const E& x) { return y >= x; }
    static KCT_NOINLINE bool one_eq(const E1& y, const E& x) { return y == x; }
    static KCT_NOINLINE bool one_ne(const E1& y, const E& x) { return y != x; }
    // Conversions to one limb.
    static KCT_NOINLINE T to_nearest(const E& x) { return kairn::to_nearest(x); }
    static KCT_NOINLINE T to_down(const E& x) { return kairn::to_down(x); }
    static KCT_NOINLINE T to_up(const E& x) { return kairn::to_up(x); }
    static KCT_NOINLINE T abs_upper(const E& x) { return kairn::abs_upper(x); }
    static KCT_NOINLINE E1 to_one(const E& x) { return E1(x); }
};

template <class T, int K>
struct UseBall {
    using B = Ball<T, K>;
    using E = Expansion<T, K>;
    // Construction and access.
    static KCT_NOINLINE B zero() { return B(); }
    static KCT_NOINLINE B make(const E& c, T r) { return B(c, r); }
    static KCT_NOINLINE B point(const E& c) { return B(c); }
    static KCT_NOINLINE B point_limb(T a) { return B(a); }
    static KCT_NOINLINE B whole() { return B::whole(); }
    static KCT_NOINLINE B empty() { return B::empty(); }
    static KCT_NOINLINE E center(const B& x) { return x.center(); }
    static KCT_NOINLINE T radius(const B& x) { return x.radius(); }
    static KCT_NOINLINE bool is_finite(const B& x) { return x.is_finite(); }
    static KCT_NOINLINE bool is_whole(const B& x) { return x.is_whole(); }
    static KCT_NOINLINE bool is_empty(const B& x) { return x.is_empty(); }
    // Sums.
    static KCT_NOINLINE B add(const B& x, const B& y) { return x + y; }
    static KCT_NOINLINE void add_assign(B& x, const B& y) { x += y; }
    static KCT_NOINLINE B add_limb(const B& x, T a) { return x + a; }
    static KCT_NOINLINE B limb_add(T a, const B& x) { return a + x; }
    static KCT_NOINLINE B add_center(const B& x, const E& c) { return x + c; }
    static KCT_NOINLINE B center_add(const E& c, const B& x) { return c + x; }
    static KCT_NOINLINE void add_assign_limb(B& x, T a) { x += a; }
    static KCT_NOINLINE void add_assign_center(B& x, const E& c) { x += c; }
    // Differences.
    static KCT_NOINLINE B sub(const B& x, const B& y) { return x - y; }
    static KCT_NOINLINE void sub_assign(B& x, const B& y) { x -= y; }
    static KCT_NOINLINE B sub_limb(const B& x, T a) { return x - a; }
    static KCT_NOINLINE B limb_sub(T a, const B& x) { return a - x; }
    static KCT_NOINLINE B sub_center(const B& x, const E& c) { return x - c; }
    static KCT_NOINLINE B center_sub(const E& c, const B& x) { return c - x; }
    static KCT_NOINLINE void sub_assign_limb(B& x, T a) { x -= a; }
    static KCT_NOINLINE void sub_assign_center(B& x, const E& c) { x -= c; }
    // Products.
    static KCT_NOINLINE B mul(const B& x, const B& y) { return x * y; }
    static KCT_NOINLINE void mul_assign(B& x, const B& y) { x *= y; }
    static KCT_NOINLINE B mul_limb(const B& x, T a) { return x * a; }
    static KCT_NOINLINE B limb_mul(T a, const B& x) { return a * x; }
    static KCT_NOINLINE void mul_assign_limb(B& x, T a) { x *= a; }
    static KCT_NOINLINE B mul_center(const B& x, const E& c) { return x * c; }
    static KCT_NOINLINE B center_mul(const E& c, const B& x) { return c * x; }
    // Negation.
    static KCT_NOINLINE B neg(const B& x) { return -x; }
};

}  // namespace kct
