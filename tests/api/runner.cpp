// A runner of the line protocol (docs/developer/architecture.md, "The line protocol") that computes
// every result through Kairn's public interface, so that the oracle judges what a client calls:
// the constructors, operators and functions of Expansion and Ball, not the generated kernels.
//
//   runner [--form NAME]      request lines on standard input, completed lines on standard output
//   runner --forms KERNEL     the forms that must satisfy KERNEL's claims, one per line
//   runner --list             every kernel that some form maps to
//   runner --internal         the building blocks: kernels that are parts of other kernels
//   runner --not-public       entry kernels that no public operation calls yet, each with why
//   runner --self-test        kairn::self_test() and kairn::environment_ok() as built here: exit
//                             0 if both pass (the tests of the flag sets, tests/api/flags/)
//
// Each public operation is mapped to the kernel it calls, whose claims it must satisfy; a kernel
// can have several forms (x + a and a + x, x += y, the marked and the unmarked operator). The
// kernels of the extended domain (the full kernels, the constructors, the comparisons and
// conversions) get infinite and NaN operands from the oracle, and balls that are empty or the
// whole line; every operand is built through the public constructors (from_limbs, Ball(c, r)), so
// that what reaches the operation is what a client would have. A form uses the operator without
// kairn::unverified when gen/claims.json says the kernel is proved, as a client would, and with
// the marker otherwise, so that the runner follows the proofs as they land.
//
// Some forms can compute only some lines of their kernel: ldexp needs a power of two among the
// operands of mul_1_1, half needs an operand it can halve back exactly, a point form needs a ball
// of radius zero, a sign predicate of a ball a line whose two operands are a ball's center and
// radius, the conversion of a SumAndError to a two-limb number a finite error term. On the other
// lines such a form computes the plain operation (written beside it), and it fails at the end of a
// stream of at least 1000 lines in which it computed none: a pass must mean that the form itself
// was judged.
//
// The scalings of a ball by a power of two, ball_mul_pow2_K_full, are reached through ldexp(X, n)
// with n = ilogb(c): every c of the oracle's cases is a positive power of two of T, so 2^n is c and
// ldexp calls the kernel once, on the line's own operands. Through half(Y), with Y = X 2^(n + 1)
// exactly where there is such a ball, and through ldexp(Y, n - k) with Y = X 2^k exactly and n - k
// beyond the powers of two of T (the steps), the form computes c X as well, and the line's claims,
// containment of c X and its exactness when c times each limb and the radius is zero or above N,
// are those of the scaling of Y it computes.
//
// binary64 requests run on double limbs, binary32 requests on float limbs; a mask is 0 or 1.
// KAIRN_CHECKS is off: the oracle sends what the checks would stop (negative radii given to a
// Ball constructor, which make an empty ball), and judges the result instead.
//
// Built with KAIRN_TEST_CHECKS defined (the debug build of tests/api/flags/), the runner leaves
// KAIRN_CHECKS to its default instead, which must then be 1, and every operation checks the
// environment and its operands as a debug build of a program does. On the lines whose radius the
// checks stop, the constructor's forms then compute Ball::empty(), which is the set the
// constructor makes of such a radius, without calling the constructor, and the runner counts them
// on its standard error; that the checks stop a negative radius is tested on its own
// (tests/api/checks.cpp). The operand of every other kernel is canonical, so nothing else changes.
#if !defined(KAIRN_TEST_CHECKS)
#define KAIRN_CHECKS 0
#endif
#include <kairn/kairn.hpp>
#if defined(KAIRN_TEST_CHECKS) && KAIRN_CHECKS != 1
#error "built with KAIRN_TEST_CHECKS, the runner must have KAIRN_CHECKS 1: build it without NDEBUG"
#endif

#include "no_crash_reports.hpp"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

namespace {

template <class T>
using E1 = kairn::Expansion<T, 1>;
template <class T>
using E2 = kairn::Expansion<T, 2>;
template <class T>
using B1 = kairn::Ball<T, 1>;
template <class T>
using B2 = kairn::Ball<T, 2>;
namespace bounds = kairn::gen::bounds;
namespace finite = kairn::finite;

// The operand as a client writes it: itself if the kernel is proved, marked otherwise.
#define PROVED(KERNEL) bounds::KERNEL<T>::proved
#define AS(KERNEL, x)                                                    \
    [&] {                                                                \
        if constexpr (PROVED(KERNEL)) return (x);                        \
        else return kairn::unverified(x);                                \
    }()

// Operands, from the limbs of a request, through the public constructors.
template <class T>
E1<T> one(const T* in) {
    return E1<T>(in[0]);
}
template <class T>
E2<T> two(const T* in) {
    if constexpr (PROVED(make_2_limbs)) {
        return E2<T>::from_limbs(in);
    } else {  // no public way to build it: the limbs as they are
        E2<T> x;
        x.limb[0] = in[0];
        x.limb[1] = in[1];
        return x;
    }
}
// A ball operand from the limbs the oracle gives, a canonical ball, whose empty set is every limb
// a NaN. The constructor makes the whole line of a NaN radius (it is a value from the program,
// and a NaN from the program never makes the empty set), so the empty operand is built as what
// it is; the forms of the constructors themselves, below, give it every radius.
template <class T>
B1<T> ball1(const T* in) {
    if (in[1] != in[1]) return B1<T>::empty();
    return B1<T>(AS(ball_make_1, one(in)), in[1]);
}
template <class T>
B2<T> ball2(const T* in) {
    if (in[2] != in[2]) return B2<T>::empty();
    return B2<T>(AS(ball_make_2, two(in)), in[2]);
}
// Results, into the limbs of the completed line.
template <class T>
void put(T* out, const E1<T>& z) {
    out[0] = z.limb[0];
}
template <class T>
void put(T* out, const E2<T>& z) {
    out[0] = z.limb[0];
    out[1] = z.limb[1];
}
template <class T, int K>
void put(T* out, const kairn::Ball<T, K>& z) {
    put(out, z.center());
    out[K] = z.radius();
}

// How often a conditional form computed its own operation (see the top of the file).
long reached = 0;

// x 2^k by T's own ldexp on each limb, independent of Kairn, when that is exact and gives a
// normalized pair: true and the result in y, or false.
template <class T>
bool exact_scale(const T* x, int limbs, int k, T* y) {
    for (int i = 0; i < limbs; ++i) {
        y[i] = std::ldexp(x[i], k);
        if (!std::isfinite(y[i]) || std::ldexp(y[i], -k) != x[i]) return false;
    }
    return limbs == 1 || y[0] + y[1] == y[0];
}
// For x and c = 2^m: y = x 2^k exactly, with m - k outside the exponents of the powers of two of
// T, so that ldexp(y, m - k) is x 2^m computed in steps; false if no such exact y is found.
template <class T>
bool far_split(const T* x, int limbs, int m, T* y, int& n) {
    constexpr int lo = std::numeric_limits<T>::min_exponent - std::numeric_limits<T>::digits;
    constexpr int hi = std::numeric_limits<T>::max_exponent - 1;
    for (int k : {m - hi - 1, m - lo + 1, m - hi - 1 - 2 * std::numeric_limits<T>::digits, m - lo + 1 + hi}) {
        if (exact_scale(x, limbs, k, y)) {
            n = m - k;
            return true;
        }
    }
    return false;
}
// b as +-2^m: true and m, or false.
template <class T>
bool power_of_two(T b, int& m) {
    if (!std::isfinite(b) || b == 0) return false;
    int e = 0;
    const T f = std::frexp(std::fabs(b), &e);
    m = e - 1;
    return f == T(0.5);
}

// One form: a function template, instantiated for double and float in the table below.
#define FORM(NAME, ...)                                                                             \
    template <class T>                                                                              \
    void NAME([[maybe_unused]] const T* in, [[maybe_unused]] T* out, [[maybe_unused]] bool* mo) {   \
        __VA_ARGS__;                                                                                \
    }

// One limb. -b and E1(-b) are exact, so x - (-b) asks for the rounded sum the claims of add_1_1
// are about.
FORM(add_1_1_plus, put(out, AS(add_1_1, one(in)) + one(in + 1)))
FORM(add_1_1_plus_limb, put(out, AS(add_1_1, one(in)) + in[1]))
FORM(add_1_1_limb_plus, put(out, in[0] + AS(add_1_1, one(in + 1))))
FORM(add_1_1_plus_assign, E1<T> x = one(in); x += AS(add_1_1, one(in + 1)); put(out, x))
FORM(add_1_1_minus, put(out, AS(add_1_1, one(in)) - E1<T>(-in[1])))
FORM(add_1_1_minus_assign, E1<T> x = one(in); x -= AS(add_1_1, E1<T>(-in[1])); put(out, x))
FORM(add_1_1_add_fast, put(out, kairn::add_fast(AS(add_1_1, one(in)), one(in + 1))))
FORM(add_1_1_marked, put(out, kairn::unverified(one(in)) + kairn::unverified(one(in + 1))))
FORM(add_1_1_finite_add, put(out, finite::add(AS(add_1_1, one(in)), one(in + 1))))
FORM(add_1_1_finite_add_limb, put(out, finite::add(AS(add_1_1, one(in)), in[1])))
FORM(add_1_1_finite_limb_add, put(out, finite::add(in[0], AS(add_1_1, one(in + 1)))))
FORM(add_1_1_finite_sub, put(out, finite::sub(AS(add_1_1, one(in)), E1<T>(-in[1]))))
FORM(add_1_1_finite_sub_limb, put(out, finite::sub(AS(add_1_1, one(in)), -in[1])))
FORM(add_1_1_finite_add_fast, put(out, finite::add_fast(AS(add_1_1, one(in)), one(in + 1))))
FORM(mul_1_1_times, put(out, AS(mul_1_1, one(in)) * one(in + 1)))
FORM(mul_1_1_times_limb, put(out, AS(mul_1_1, one(in)) * in[1]))
FORM(mul_1_1_limb_times, put(out, in[0] * AS(mul_1_1, one(in + 1))))
FORM(mul_1_1_times_assign, E1<T> x = one(in); x *= AS(mul_1_1, one(in + 1)); put(out, x))
FORM(mul_1_1_marked, put(out, kairn::unverified(one(in)) * kairn::unverified(one(in + 1))))
FORM(mul_1_1_finite_mul, put(out, finite::mul(AS(mul_1_1, one(in)), one(in + 1))))
FORM(mul_1_1_finite_mul_limb, put(out, finite::mul(AS(mul_1_1, one(in)), in[1])))
FORM(mul_1_1_finite_limb_mul, put(out, finite::mul(in[0], AS(mul_1_1, one(in + 1)))))
// ldexp, half and the steps of ldexp, on the lines whose b is +-2^m; the product otherwise.
FORM(mul_1_1_ldexp, int m = 0; if (!power_of_two(in[1], m)) { put(out, one(in) * one(in + 1)); return; } ++reached;
     const E1<T> z = kairn::ldexp(AS(mul_1_1, one(in)), m); put(out, in[1] > 0 ? z : -z))
FORM(mul_1_1_finite_ldexp, int m = 0; if (!power_of_two(in[1], m)) { put(out, one(in) * one(in + 1)); return; } ++reached;
     const E1<T> z = finite::ldexp(AS(mul_1_1, one(in)), m); put(out, in[1] > 0 ? z : -z))
FORM(mul_1_1_half, int m = 0; T y[1];
     if (!power_of_two(in[1], m) || !exact_scale(in, 1, m + 1, y)) { put(out, one(in) * one(in + 1)); return; } ++reached;
     const E1<T> z = kairn::half(AS(mul_1_1, one(y))); put(out, in[1] > 0 ? z : -z))
FORM(mul_1_1_ldexp_far, int m = 0, n = 0; T y[1];
     if (!power_of_two(in[1], m) || !far_split(in, 1, m, y, n)) { put(out, one(in) * one(in + 1)); return; } ++reached;
     const E1<T> z = kairn::ldexp(AS(mul_1_1, one(y)), n); put(out, in[1] > 0 ? z : -z))

// The building blocks on T (kairn/blocks.hpp): each the function itself, and with the marker.
template <class T>
void put_pair(T* out, const kairn::SumAndError<T>& r) {
    out[0] = r.sum;
    out[1] = r.error;
}
template <class T>
void put_pair(T* out, const kairn::ProductAndError<T>& r) {
    out[0] = r.product;
    out[1] = r.error;
}
// The conversion of a SumAndError to Expansion<T, 2>, on the lines where both members are finite
// (SumAndError says when it is valid); the members as they are otherwise.
template <class T>
void put_converted(T* out, const kairn::SumAndError<T>& r) {
    if (!std::isfinite(r.sum) || !std::isfinite(r.error)) {
        put_pair(out, r);
        return;
    }
    ++reached;
    put(out, E2<T>(r));
}
FORM(two_sum_entry_two_sum, put_pair(out, kairn::two_sum(AS(two_sum_entry, in[0]), in[1])))
FORM(two_sum_entry_marked, put_pair(out, kairn::two_sum(in[0], kairn::unverified(in[1]))))
FORM(two_sum_entry_to_expansion, put_converted(out, kairn::two_sum(AS(two_sum_entry, in[0]), in[1])))
FORM(fast_two_sum_entry_fast_two_sum, put_pair(out, kairn::fast_two_sum(AS(fast_two_sum_entry, in[0]), in[1])))
FORM(fast_two_sum_entry_marked, put_pair(out, kairn::fast_two_sum(kairn::unverified(in[0]), in[1])))
FORM(fast_two_sum_entry_to_expansion,
     put_converted(out, kairn::fast_two_sum(AS(fast_two_sum_entry, in[0]), in[1])))
FORM(two_prod_two_prod, put_pair(out, kairn::two_prod(AS(two_prod, in[0]), in[1])))
FORM(two_prod_marked, put_pair(out, kairn::two_prod(kairn::unverified(in[0]), in[1])))
FORM(next_up_next_up, out[0] = kairn::next_up(AS(next_up, in[0])))
FORM(next_up_marked, out[0] = kairn::next_up(kairn::unverified(in[0])))
FORM(next_down_next_down, out[0] = kairn::next_down(AS(next_down, in[0])))
FORM(next_down_marked, out[0] = kairn::next_down(kairn::unverified(in[0])))
FORM(radd_entry_radd, out[0] = kairn::radd(AS(radd_entry, in[0]), in[1]))
FORM(radd_entry_marked, out[0] = kairn::radd(in[0], kairn::unverified(in[1])))
FORM(rmul_rmul, out[0] = kairn::rmul(AS(rmul, in[0]), in[1]))
FORM(rmul_marked, out[0] = kairn::rmul(in[0], kairn::unverified(in[1])))
FORM(add_down_entry_add_down, out[0] = kairn::add_down(AS(add_down_entry, in[0]), in[1]))
FORM(add_down_entry_marked, out[0] = kairn::add_down(kairn::unverified(in[0]), in[1]))
FORM(add_up_entry_add_up, out[0] = kairn::add_up(AS(add_up_entry, in[0]), in[1]))
FORM(add_up_entry_marked, out[0] = kairn::add_up(kairn::unverified(in[0]), in[1]))
FORM(sub_down_entry_sub_down, out[0] = kairn::sub_down(AS(sub_down_entry, in[0]), in[1]))
FORM(sub_down_entry_marked, out[0] = kairn::sub_down(in[0], kairn::unverified(in[1])))
FORM(sub_up_entry_sub_up, out[0] = kairn::sub_up(AS(sub_up_entry, in[0]), in[1]))
FORM(sub_up_entry_marked, out[0] = kairn::sub_up(in[0], kairn::unverified(in[1])))
FORM(mul_down_1_mul_down, out[0] = kairn::mul_down(AS(mul_down_1, in[0]), in[1]))
FORM(mul_down_1_marked, out[0] = kairn::mul_down(kairn::unverified(in[0]), in[1]))
FORM(mul_up_1_mul_up, out[0] = kairn::mul_up(AS(mul_up_1, in[0]), in[1]))
FORM(mul_up_1_marked, out[0] = kairn::mul_up(kairn::unverified(in[0]), in[1]))

// Two limbs: construction.
FORM(make_2_from_limb, put(out, E2<T>(AS(make_2, in[0]))))
FORM(make_2_from_one, put(out, E2<T>(AS(make_2, one(in)))))
FORM(make_2_marked, put(out, E2<T>(kairn::unverified(in[0]))))
FORM(make_2_limbs_from_limbs, put(out, E2<T>::from_limbs(in)))
FORM(make_2_limbs_from_limbs_unchecked, put(out, E2<T>::from_limbs_unchecked(in)))

// Two limbs: arithmetic, the full kernels.
FORM(add_2_2_full_plus, put(out, AS(add_2_2_full, two(in)) + two(in + 2)))
FORM(add_2_2_full_plus_assign, E2<T> x = two(in); x += AS(add_2_2_full, two(in + 2)); put(out, x))
FORM(add_2_2_full_marked, put(out, two(in) + kairn::unverified(two(in + 2))))
FORM(add_2_1_full_plus, put(out, AS(add_2_1_full, two(in)) + in[2]))
FORM(add_2_1_full_limb_plus, put(out, in[2] + AS(add_2_1_full, two(in))))
FORM(add_2_1_full_plus_assign, E2<T> x = two(in); x += AS(add_2_1_full, in[2]); put(out, x))
FORM(add_2_1_full_plus_one, put(out, AS(add_2_1_full, two(in)) + one(in + 2)))
FORM(add_2_1_full_one_plus, put(out, one(in + 2) + AS(add_2_1_full, two(in))))
FORM(add_2_1_full_plus_assign_one, E2<T> x = two(in); x += AS(add_2_1_full, one(in + 2)); put(out, x))
FORM(add_2_1_full_marked, put(out, two(in) + kairn::unverified(in[2])))
FORM(sub_2_2_full_minus, put(out, AS(sub_2_2_full, two(in)) - two(in + 2)))
FORM(sub_2_2_full_minus_assign, E2<T> x = two(in); x -= AS(sub_2_2_full, two(in + 2)); put(out, x))
FORM(sub_2_2_full_marked, put(out, two(in) - kairn::unverified(two(in + 2))))
FORM(sub_2_1_full_minus, put(out, AS(sub_2_1_full, two(in)) - in[2]))
FORM(sub_2_1_full_minus_assign, E2<T> x = two(in); x -= AS(sub_2_1_full, in[2]); put(out, x))
FORM(sub_2_1_full_minus_one, put(out, AS(sub_2_1_full, two(in)) - one(in + 2)))
FORM(sub_2_1_full_minus_assign_one, E2<T> x = two(in); x -= AS(sub_2_1_full, one(in + 2)); put(out, x))
FORM(sub_2_1_full_marked, put(out, two(in) - kairn::unverified(in[2])))
FORM(sub_1_2_full_minus, put(out, in[0] - AS(sub_1_2_full, two(in + 1))))
FORM(sub_1_2_full_one_minus, put(out, one(in) - AS(sub_1_2_full, two(in + 1))))
FORM(sub_1_2_full_marked, put(out, kairn::unverified(in[0]) - two(in + 1)))
FORM(mul_2_2_full_times, put(out, AS(mul_2_2_full, two(in)) * two(in + 2)))
FORM(mul_2_2_full_times_assign, E2<T> x = two(in); x *= AS(mul_2_2_full, two(in + 2)); put(out, x))
FORM(mul_2_2_full_marked, put(out, two(in) * kairn::unverified(two(in + 2))))
FORM(mul_2_1_full_times, put(out, AS(mul_2_1_full, two(in)) * in[2]))
FORM(mul_2_1_full_limb_times, put(out, in[2] * AS(mul_2_1_full, two(in))))
FORM(mul_2_1_full_times_assign, E2<T> x = two(in); x *= AS(mul_2_1_full, in[2]); put(out, x))
FORM(mul_2_1_full_times_one, put(out, AS(mul_2_1_full, two(in)) * one(in + 2)))
FORM(mul_2_1_full_one_times, put(out, one(in + 2) * AS(mul_2_1_full, two(in))))
FORM(mul_2_1_full_times_assign_one, E2<T> x = two(in); x *= AS(mul_2_1_full, one(in + 2)); put(out, x))
FORM(mul_2_1_full_marked, put(out, kairn::unverified(two(in)) * in[2]))
FORM(add_fast_2_2_full_add_fast, put(out, kairn::add_fast(AS(add_fast_2_2_full, two(in)), two(in + 2))))
FORM(add_fast_2_2_full_marked, put(out, kairn::add_fast(two(in), kairn::unverified(two(in + 2)))))
// c is a positive power of two of T, 2^m with m = ilogb(c) (subnormal powers included).
FORM(mul_pow2_2_full_ldexp, put(out, kairn::ldexp(AS(mul_pow2_2_full, two(in)), std::ilogb(in[2]))))
FORM(mul_pow2_2_full_marked, put(out, kairn::ldexp(kairn::unverified(two(in)), std::ilogb(in[2]))))
// half(y) with y = x 2^(m + 1) exactly, where there is such a y; ldexp(x, m) otherwise. The same
// for the steps of ldexp, with y = x 2^k exactly and m - k beyond the powers of two of T.
FORM(mul_pow2_2_full_half, const int m = std::ilogb(in[2]); T y[2];
     if (!std::isfinite(in[0]) || !exact_scale(in, 2, m + 1, y)) { put(out, kairn::ldexp(two(in), m)); return; } ++reached;
     put(out, kairn::half(AS(mul_pow2_2_full, two(y)))))
FORM(mul_pow2_2_full_ldexp_far, int n = 0; T y[2];
     if (!std::isfinite(in[0]) || !far_split(in, 2, std::ilogb(in[2]), y, n)) { put(out, kairn::ldexp(two(in), std::ilogb(in[2]))); return; }
     ++reached; put(out, kairn::ldexp(AS(mul_pow2_2_full, two(y)), n)))

// Two limbs: the finite cores, kairn::finite::.
FORM(add_2_2_finite_add, put(out, finite::add(AS(add_2_2, two(in)), two(in + 2))))
FORM(add_2_2_marked, put(out, finite::add(two(in), kairn::unverified(two(in + 2)))))
FORM(add_2_1_finite_add, put(out, finite::add(AS(add_2_1, two(in)), in[2])))
FORM(add_2_1_finite_limb_add, put(out, finite::add(in[2], AS(add_2_1, two(in)))))
FORM(add_2_1_finite_add_one, put(out, finite::add(AS(add_2_1, two(in)), one(in + 2))))
FORM(add_2_1_finite_one_add, put(out, finite::add(one(in + 2), AS(add_2_1, two(in)))))
FORM(sub_2_2_finite_sub, put(out, finite::sub(AS(sub_2_2, two(in)), two(in + 2))))
FORM(sub_2_1_finite_sub, put(out, finite::sub(AS(sub_2_1, two(in)), in[2])))
FORM(sub_2_1_finite_sub_one, put(out, finite::sub(AS(sub_2_1, two(in)), one(in + 2))))
FORM(sub_1_2_finite_sub, put(out, finite::sub(in[0], AS(sub_1_2, two(in + 1)))))
FORM(sub_1_2_finite_one_sub, put(out, finite::sub(one(in), AS(sub_1_2, two(in + 1)))))
FORM(mul_2_2_finite_mul, put(out, finite::mul(AS(mul_2_2, two(in)), two(in + 2))))
FORM(mul_2_1_finite_mul, put(out, finite::mul(AS(mul_2_1, two(in)), in[2])))
FORM(mul_2_1_finite_limb_mul, put(out, finite::mul(in[2], AS(mul_2_1, two(in)))))
FORM(mul_2_1_finite_mul_one, put(out, finite::mul(AS(mul_2_1, two(in)), one(in + 2))))
FORM(mul_2_1_finite_one_mul, put(out, finite::mul(one(in + 2), AS(mul_2_1, two(in)))))
FORM(add_fast_2_2_finite_add_fast, put(out, finite::add_fast(AS(add_fast_2_2, two(in)), two(in + 2))))
FORM(mul_pow2_2_finite_ldexp, put(out, finite::ldexp(AS(mul_pow2_2, two(in)), std::ilogb(in[2]))))
FORM(mul_pow2_2_finite_ldexp_far, int n = 0; T y[2];
     if (!far_split(in, 2, std::ilogb(in[2]), y, n)) { put(out, finite::ldexp(two(in), std::ilogb(in[2]))); return; }
     ++reached; put(out, finite::ldexp(AS(mul_pow2_2, two(y)), n)))

// Two limbs: negation, absolute value.
FORM(neg_2_negate, put(out, -AS(neg_2, two(in))))
FORM(abs_2_abs, put(out, kairn::abs(AS(abs_2, two(in)))))

// Two limbs: comparisons. The reversed forms ask the same question with the operands swapped.
FORM(lt_2_2_less, mo[0] = AS(lt_2_2, two(in)) < two(in + 2))
FORM(lt_2_2_greater, mo[0] = two(in + 2) > AS(lt_2_2, two(in)))
FORM(le_2_2_less_equal, mo[0] = AS(le_2_2, two(in)) <= two(in + 2))
FORM(le_2_2_greater_equal, mo[0] = two(in + 2) >= AS(le_2_2, two(in)))
FORM(eq_2_2_equal, mo[0] = AS(eq_2_2, two(in)) == two(in + 2))
FORM(eq_2_2_not_unequal, mo[0] = !(two(in) != AS(eq_2_2, two(in + 2))))
FORM(lt_2_1_less, mo[0] = AS(lt_2_1, two(in)) < in[2])
FORM(lt_2_1_greater, mo[0] = in[2] > AS(lt_2_1, two(in)))
FORM(lt_2_1_less_one, mo[0] = AS(lt_2_1, two(in)) < one(in + 2))
FORM(lt_2_1_greater_one, mo[0] = one(in + 2) > AS(lt_2_1, two(in)))
FORM(le_2_1_less_equal, mo[0] = AS(le_2_1, two(in)) <= in[2])
FORM(le_2_1_greater_equal, mo[0] = in[2] >= AS(le_2_1, two(in)))
FORM(le_2_1_less_equal_one, mo[0] = AS(le_2_1, two(in)) <= one(in + 2))
FORM(le_2_1_greater_equal_one, mo[0] = one(in + 2) >= AS(le_2_1, two(in)))
FORM(eq_2_1_equal, mo[0] = AS(eq_2_1, two(in)) == in[2])
FORM(eq_2_1_equal_rev, mo[0] = in[2] == AS(eq_2_1, two(in)))
FORM(eq_2_1_not_unequal, mo[0] = !(AS(eq_2_1, two(in)) != in[2]))
FORM(eq_2_1_not_unequal_rev, mo[0] = !(in[2] != AS(eq_2_1, two(in))))
FORM(eq_2_1_equal_one, mo[0] = AS(eq_2_1, two(in)) == one(in + 2))
FORM(eq_2_1_equal_one_rev, mo[0] = one(in + 2) == AS(eq_2_1, two(in)))
FORM(eq_2_1_not_unequal_one, mo[0] = !(AS(eq_2_1, two(in)) != one(in + 2)))
FORM(eq_2_1_not_unequal_one_rev, mo[0] = !(one(in + 2) != AS(eq_2_1, two(in))))
FORM(lt_1_2_less, mo[0] = in[0] < AS(lt_1_2, two(in + 1)))
FORM(lt_1_2_greater, mo[0] = AS(lt_1_2, two(in + 1)) > in[0])
FORM(lt_1_2_less_one, mo[0] = one(in) < AS(lt_1_2, two(in + 1)))
FORM(lt_1_2_greater_one, mo[0] = AS(lt_1_2, two(in + 1)) > one(in))
FORM(le_1_2_less_equal, mo[0] = in[0] <= AS(le_1_2, two(in + 1)))
FORM(le_1_2_greater_equal, mo[0] = AS(le_1_2, two(in + 1)) >= in[0])
FORM(le_1_2_less_equal_one, mo[0] = one(in) <= AS(le_1_2, two(in + 1)))
FORM(le_1_2_greater_equal_one, mo[0] = AS(le_1_2, two(in + 1)) >= one(in))

// Two limbs: conversions to T. Narrowing keeps the leading limb, the claim of to_nearest_2.
FORM(to_nearest_2_to_nearest, out[0] = kairn::to_nearest(AS(to_nearest_2, two(in))))
FORM(to_nearest_2_narrow, out[0] = E1<T>(AS(to_nearest_2, two(in))).limb[0])
FORM(to_nearest_2_narrow_marked, out[0] = E1<T>(kairn::unverified(two(in))).limb[0])
FORM(to_down_2_to_down, out[0] = kairn::to_down(AS(to_down_2, two(in))))
FORM(to_up_2_to_up, out[0] = kairn::to_up(AS(to_up_2, two(in))))
FORM(abs_upper_2_abs_upper, out[0] = kairn::abs_upper(AS(abs_upper_2, two(in))))

// Balls: construction. The center and the radius as given (a negative radius makes the empty set,
// or, with KAIRN_CHECKS, stops the program: see the top of the file).
long stopped = 0;
template <class T>
bool stopped_by_checks([[maybe_unused]] T r) {
#if KAIRN_CHECKS
    if (0 > r) {
        ++stopped;
        return true;
    }
#endif
    return false;
}
FORM(ball_make_1_center_radius, if (stopped_by_checks(in[1])) { put(out, B1<T>::empty()); return; }
     put(out, B1<T>(AS(ball_make_1, one(in)), in[1])))
FORM(ball_make_1_limb_radius, if (stopped_by_checks(in[1])) { put(out, B1<T>::empty()); return; }
     put(out, B1<T>(in[0], in[1])))
FORM(ball_make_2_center_radius, if (stopped_by_checks(in[2])) { put(out, B2<T>::empty()); return; }
     put(out, B2<T>(AS(ball_make_2, two(in)), in[2])))
// The ball of a constant of kairn::rational, with the line's center as its value and its radius as
// its error: what the constructor makes of any Constant.
FORM(ball_make_1_constant, if (stopped_by_checks(in[1])) { put(out, B1<T>::empty()); return; }
     put(out, B1<T>(kairn::Constant<E1<T>>{one(in), in[1], false})))
FORM(ball_make_2_constant, if (stopped_by_checks(in[2])) { put(out, B2<T>::empty()); return; }
     put(out, B2<T>(kairn::Constant<E2<T>>{two(in), in[2], false})))

// Balls: arithmetic. Operands are (center limbs, radius); a scaling's last operand is a T. A point
// form takes the other ball of the line as a point when its radius is zero (and, for a point of
// type T with two limbs, its second limb too), and is the operation of balls otherwise.
#define BALL_FORMS(K, BALL)                                                                                          \
    FORM(ball_add_##K##_full_plus, put(out, AS(ball_add_##K##_full, BALL(in)) + BALL(in + K + 1)))                 \
    FORM(ball_add_##K##_full_plus_assign, auto x = BALL(in); x += AS(ball_add_##K##_full, BALL(in + K + 1)); put(out, x)) \
    FORM(ball_add_##K##_full_marked, put(out, BALL(in) + kairn::unverified(BALL(in + K + 1))))                    \
    FORM(ball_sub_##K##_full_minus, put(out, AS(ball_sub_##K##_full, BALL(in)) - BALL(in + K + 1)))                \
    FORM(ball_sub_##K##_full_minus_assign, auto x = BALL(in); x -= AS(ball_sub_##K##_full, BALL(in + K + 1)); put(out, x)) \
    FORM(ball_sub_##K##_full_marked, put(out, BALL(in) - kairn::unverified(BALL(in + K + 1))))                    \
    FORM(ball_mul_##K##_full_times, put(out, AS(ball_mul_##K##_full, BALL(in)) * BALL(in + K + 1)))                \
    FORM(ball_mul_##K##_full_times_assign, auto x = BALL(in); x *= AS(ball_mul_##K##_full, BALL(in + K + 1)); put(out, x)) \
    FORM(ball_mul_##K##_full_marked, put(out, BALL(in) * kairn::unverified(BALL(in + K + 1))))                    \
    FORM(ball_scale_##K##_full_scale, put(out, AS(ball_scale_##K##_full, BALL(in)) * in[K + 1]))                   \
    FORM(ball_scale_##K##_full_scale_rev, put(out, in[K + 1] * AS(ball_scale_##K##_full, BALL(in))))               \
    FORM(ball_scale_##K##_full_scale_assign, auto x = BALL(in); x *= AS(ball_scale_##K##_full, in[K + 1]); put(out, x)) \
    FORM(ball_scale_##K##_full_marked, put(out, kairn::unverified(BALL(in)) * in[K + 1]))                         \
    FORM(ball_neg_##K##_negate, put(out, -AS(ball_neg_##K, BALL(in))))                                             \
    FORM(ball_neg_##K##_marked, put(out, -kairn::unverified(BALL(in))))
BALL_FORMS(1, ball1)
BALL_FORMS(2, ball2)

// The scaling of a ball by a power of two c = 2^m: ldexp(X, m), its marked form, half(Y) with
// Y = X 2^(m + 1) exactly, and ldexp(Y, m - k) with Y = X 2^k exactly and m - k beyond the powers
// of two of T (see the top of the file). A ball scaled exactly: its center by exact_scale, and its
// radius, finite, scaled and back.
template <class T, int K>
bool exact_ball_scale(const T* x, int k, T* y) {
    if (!exact_scale(x, K, k, y)) return false;
    y[K] = std::ldexp(x[K], k);
    return std::isfinite(y[K]) && std::ldexp(y[K], -k) == x[K];
}
template <class T, int K>
bool far_ball_split(const T* x, int m, T* y, int& n) {
    constexpr int lo = std::numeric_limits<T>::min_exponent - std::numeric_limits<T>::digits;
    constexpr int hi = std::numeric_limits<T>::max_exponent - 1;
    for (int k : {m - hi - 1, m - lo + 1, m - hi - 1 - 2 * std::numeric_limits<T>::digits, m - lo + 1 + hi}) {
        if (exact_ball_scale<T, K>(x, k, y)) {
            n = m - k;
            return true;
        }
    }
    return false;
}
#define POW2_FORMS(K, BALL)                                                                                        \
    FORM(ball_mul_pow2_##K##_full_ldexp,                                                                           \
         put(out, kairn::ldexp(AS(ball_mul_pow2_##K##_full, BALL(in)), std::ilogb(in[K + 1]))))                    \
    FORM(ball_mul_pow2_##K##_full_marked, put(out, kairn::ldexp(kairn::unverified(BALL(in)), std::ilogb(in[K + 1])))) \
    FORM(ball_mul_pow2_##K##_full_half, const int m = std::ilogb(in[K + 1]); T y[K + 1];                          \
         if (!exact_ball_scale<T, K>(in, m + 1, y)) { put(out, kairn::ldexp(BALL(in), m)); return; } ++reached;    \
         put(out, kairn::half(AS(ball_mul_pow2_##K##_full, BALL(y)))))                                             \
    FORM(ball_mul_pow2_##K##_full_ldexp_far, int n = 0; T y[K + 1];                                                \
         if (!far_ball_split<T, K>(in, std::ilogb(in[K + 1]), y, n)) {                                             \
             put(out, kairn::ldexp(BALL(in), std::ilogb(in[K + 1])));                                              \
             return;                                                                                               \
         }                                                                                                         \
         ++reached; put(out, kairn::ldexp(AS(ball_mul_pow2_##K##_full, BALL(y)), n)))
POW2_FORMS(1, ball1)
POW2_FORMS(2, ball2)

// The sign predicates of a ball of two limbs, whose kernels are comparisons of the radius with the
// center: on a line of lt_1_2 (a, y), the ball of center y and radius a, when a is not negative
// and y is finite (a +inf or a NaN radius makes the whole line, and the comparison is then false
// too); on a line of lt_2_1 (x, a), the ball of center x and radius -a; on a line of
// eq_2_1 (x, a) whose a is zero, the ball of center x and radius 0. The comparison otherwise.
FORM(lt_1_2_certainly_positive, if (0 > in[0] || !std::isfinite(in[1])) { mo[0] = in[0] < two(in + 1); return; }
     ++reached; mo[0] = B2<T>(two(in + 1), in[0]).certainly_positive())
FORM(lt_2_1_certainly_negative, if (in[2] > 0 || !std::isfinite(in[0])) { mo[0] = two(in) < in[2]; return; }
     ++reached; mo[0] = B2<T>(two(in), -in[2]).certainly_negative())
FORM(eq_2_1_certainly_zero, if (in[2] != 0) { mo[0] = two(in) == in[2]; return; }
     ++reached; mo[0] = B2<T>(two(in), T(0)).certainly_zero())

// Points: the radius of the point's ball is zero, and for a point of type T with two limbs so is
// its second limb.
template <class T, int K>
bool point(const T* ball) {
    return ball[K] == 0 && (K == 1 || ball[1] == 0);
}
template <class T, int K>
bool center_point(const T* ball) {
    return ball[K] == 0;
}
template <class T, int K>
kairn::Expansion<T, K> center(const T* in) {
    if constexpr (K == 1) return one(in);
    else return two(in);
}
#define POINT_FORMS(K, BALL)                                                                                         \
    FORM(ball_add_##K##_full_plus_point, const T* y = in + K + 1;                                                    \
         if (!point<T, K>(y)) { put(out, BALL(in) + BALL(y)); return; } ++reached;                                   \
         put(out, AS(ball_add_##K##_full, BALL(in)) + y[0]))                                                          \
    FORM(ball_add_##K##_full_point_plus, if (!point<T, K>(in)) { put(out, BALL(in) + BALL(in + K + 1)); return; }    \
         ++reached; put(out, in[0] + AS(ball_add_##K##_full, BALL(in + K + 1))))                                     \
    FORM(ball_add_##K##_full_plus_center, const T* y = in + K + 1;                                                   \
         if (!center_point<T, K>(y)) { put(out, BALL(in) + BALL(y)); return; } ++reached;                            \
         put(out, AS(ball_add_##K##_full, BALL(in)) + center<T, K>(y)))                                               \
    FORM(ball_add_##K##_full_center_plus, if (!center_point<T, K>(in)) { put(out, BALL(in) + BALL(in + K + 1)); return; } \
         ++reached; put(out, center<T, K>(in) + AS(ball_add_##K##_full, BALL(in + K + 1))))                          \
    FORM(ball_add_##K##_full_plus_assign_point, const T* y = in + K + 1; auto x = BALL(in);                          \
         if (!point<T, K>(y)) { put(out, x + BALL(y)); return; } ++reached; x += AS(ball_add_##K##_full, y[0]); put(out, x)) \
    FORM(ball_add_##K##_full_plus_assign_center, const T* y = in + K + 1; auto x = BALL(in);                         \
         if (!center_point<T, K>(y)) { put(out, x + BALL(y)); return; } ++reached;                                   \
         x += AS(ball_add_##K##_full, (center<T, K>(y))); put(out, x))                                                \
    FORM(ball_sub_##K##_full_minus_point, const T* y = in + K + 1;                                                   \
         if (!point<T, K>(y)) { put(out, BALL(in) - BALL(y)); return; } ++reached;                                   \
         put(out, AS(ball_sub_##K##_full, BALL(in)) - y[0]))                                                          \
    FORM(ball_sub_##K##_full_point_minus, if (!point<T, K>(in)) { put(out, BALL(in) - BALL(in + K + 1)); return; }   \
         ++reached; put(out, in[0] - AS(ball_sub_##K##_full, BALL(in + K + 1))))                                     \
    FORM(ball_sub_##K##_full_minus_center, const T* y = in + K + 1;                                                  \
         if (!center_point<T, K>(y)) { put(out, BALL(in) - BALL(y)); return; } ++reached;                            \
         put(out, AS(ball_sub_##K##_full, BALL(in)) - center<T, K>(y)))                                               \
    FORM(ball_sub_##K##_full_center_minus, if (!center_point<T, K>(in)) { put(out, BALL(in) - BALL(in + K + 1)); return; } \
         ++reached; put(out, center<T, K>(in) - AS(ball_sub_##K##_full, BALL(in + K + 1))))                          \
    FORM(ball_sub_##K##_full_minus_assign_point, const T* y = in + K + 1; auto x = BALL(in);                         \
         if (!point<T, K>(y)) { put(out, x - BALL(y)); return; } ++reached; x -= AS(ball_sub_##K##_full, y[0]); put(out, x)) \
    FORM(ball_sub_##K##_full_minus_assign_center, const T* y = in + K + 1; auto x = BALL(in);                        \
         if (!center_point<T, K>(y)) { put(out, x - BALL(y)); return; } ++reached;                                   \
         x -= AS(ball_sub_##K##_full, (center<T, K>(y))); put(out, x))
POINT_FORMS(1, ball1)
POINT_FORMS(2, ball2)
// Products with a point: for two limbs, the ball of the point; for one limb, the scaling by it.
FORM(ball_mul_2_full_times_center, const T* y = in + 3;
     if (!center_point<T, 2>(y)) { put(out, ball2(in) * ball2(y)); return; } ++reached;
     put(out, AS(ball_mul_2_full, ball2(in)) * two(y)))
FORM(ball_mul_2_full_center_times, if (!center_point<T, 2>(in)) { put(out, ball2(in) * ball2(in + 3)); return; }
     ++reached; put(out, two(in) * AS(ball_mul_2_full, ball2(in + 3))))
FORM(ball_scale_1_full_scale_one, put(out, AS(ball_scale_1_full, ball1(in)) * one(in + 2)))
FORM(ball_scale_1_full_one_scale, put(out, one(in + 2) * AS(ball_scale_1_full, ball1(in))))

struct Form {
    const char* kernel;
    const char* name;
    const char* in_kinds;  // one letter per input value: l a limb, m a mask
    const char* out_kinds;
    bool conditional;      // computes its own operation on some lines only
    void (*binary64)(const double*, double*, bool*);
    void (*binary32)(const float*, float*, bool*);
};

#define ROW(KERNEL, NAME, IN, OUT) {#KERNEL, #NAME, IN, OUT, false, KERNEL##_##NAME<double>, KERNEL##_##NAME<float>},
#define SOME(KERNEL, NAME, IN, OUT) {#KERNEL, #NAME, IN, OUT, true, KERNEL##_##NAME<double>, KERNEL##_##NAME<float>},
#define BALL_ROWS(K, IN, OUT, IN_SCALE, IN_NEG)            \
    ROW(ball_add_##K##_full, plus, IN, OUT)              \
    ROW(ball_add_##K##_full, plus_assign, IN, OUT)       \
    ROW(ball_add_##K##_full, marked, IN, OUT)            \
    SOME(ball_add_##K##_full, plus_point, IN, OUT)       \
    SOME(ball_add_##K##_full, point_plus, IN, OUT)       \
    SOME(ball_add_##K##_full, plus_center, IN, OUT)      \
    SOME(ball_add_##K##_full, center_plus, IN, OUT)      \
    SOME(ball_add_##K##_full, plus_assign_point, IN, OUT) \
    SOME(ball_add_##K##_full, plus_assign_center, IN, OUT) \
    ROW(ball_sub_##K##_full, minus, IN, OUT)             \
    ROW(ball_sub_##K##_full, minus_assign, IN, OUT)      \
    ROW(ball_sub_##K##_full, marked, IN, OUT)            \
    SOME(ball_sub_##K##_full, minus_point, IN, OUT)      \
    SOME(ball_sub_##K##_full, point_minus, IN, OUT)      \
    SOME(ball_sub_##K##_full, minus_center, IN, OUT)     \
    SOME(ball_sub_##K##_full, center_minus, IN, OUT)     \
    SOME(ball_sub_##K##_full, minus_assign_point, IN, OUT) \
    SOME(ball_sub_##K##_full, minus_assign_center, IN, OUT) \
    ROW(ball_mul_##K##_full, times, IN, OUT)             \
    ROW(ball_mul_##K##_full, times_assign, IN, OUT)      \
    ROW(ball_mul_##K##_full, marked, IN, OUT)            \
    ROW(ball_scale_##K##_full, scale, IN_SCALE, OUT)     \
    ROW(ball_scale_##K##_full, scale_rev, IN_SCALE, OUT) \
    ROW(ball_scale_##K##_full, scale_assign, IN_SCALE, OUT) \
    ROW(ball_scale_##K##_full, marked, IN_SCALE, OUT)    \
    ROW(ball_neg_##K, negate, IN_NEG, OUT)               \
    ROW(ball_neg_##K, marked, IN_NEG, OUT)

// The first form of each kernel is its canonical one.
const Form forms[] = {
    ROW(two_sum_entry, two_sum, "ll", "ll")
    ROW(two_sum_entry, marked, "ll", "ll")
    SOME(two_sum_entry, to_expansion, "ll", "ll")
    ROW(fast_two_sum_entry, fast_two_sum, "ll", "ll")
    ROW(fast_two_sum_entry, marked, "ll", "ll")
    SOME(fast_two_sum_entry, to_expansion, "ll", "ll")
    ROW(two_prod, two_prod, "ll", "ll")
    ROW(two_prod, marked, "ll", "ll")
    ROW(next_up, next_up, "l", "l")
    ROW(next_up, marked, "l", "l")
    ROW(next_down, next_down, "l", "l")
    ROW(next_down, marked, "l", "l")
    ROW(radd_entry, radd, "ll", "l")
    ROW(radd_entry, marked, "ll", "l")
    ROW(rmul, rmul, "ll", "l")
    ROW(rmul, marked, "ll", "l")
    ROW(add_down_entry, add_down, "ll", "l")
    ROW(add_down_entry, marked, "ll", "l")
    ROW(add_up_entry, add_up, "ll", "l")
    ROW(add_up_entry, marked, "ll", "l")
    ROW(sub_down_entry, sub_down, "ll", "l")
    ROW(sub_down_entry, marked, "ll", "l")
    ROW(sub_up_entry, sub_up, "ll", "l")
    ROW(sub_up_entry, marked, "ll", "l")
    ROW(mul_down_1, mul_down, "ll", "l")
    ROW(mul_down_1, marked, "ll", "l")
    ROW(mul_up_1, mul_up, "ll", "l")
    ROW(mul_up_1, marked, "ll", "l")
    ROW(add_1_1, plus, "ll", "l")
    ROW(add_1_1, plus_limb, "ll", "l")
    ROW(add_1_1, limb_plus, "ll", "l")
    ROW(add_1_1, plus_assign, "ll", "l")
    ROW(add_1_1, minus, "ll", "l")
    ROW(add_1_1, minus_assign, "ll", "l")
    ROW(add_1_1, add_fast, "ll", "l")
    ROW(add_1_1, marked, "ll", "l")
    ROW(add_1_1, finite_add, "ll", "l")
    ROW(add_1_1, finite_add_limb, "ll", "l")
    ROW(add_1_1, finite_limb_add, "ll", "l")
    ROW(add_1_1, finite_sub, "ll", "l")
    ROW(add_1_1, finite_sub_limb, "ll", "l")
    ROW(add_1_1, finite_add_fast, "ll", "l")
    ROW(mul_1_1, times, "ll", "l")
    ROW(mul_1_1, times_limb, "ll", "l")
    ROW(mul_1_1, limb_times, "ll", "l")
    ROW(mul_1_1, times_assign, "ll", "l")
    ROW(mul_1_1, marked, "ll", "l")
    ROW(mul_1_1, finite_mul, "ll", "l")
    ROW(mul_1_1, finite_mul_limb, "ll", "l")
    ROW(mul_1_1, finite_limb_mul, "ll", "l")
    SOME(mul_1_1, ldexp, "ll", "l")
    SOME(mul_1_1, finite_ldexp, "ll", "l")
    SOME(mul_1_1, half, "ll", "l")
    SOME(mul_1_1, ldexp_far, "ll", "l")
    ROW(make_2, from_limb, "l", "ll")
    ROW(make_2, from_one, "l", "ll")
    ROW(make_2, marked, "l", "ll")
    ROW(make_2_limbs, from_limbs, "ll", "ll")
    ROW(make_2_limbs, from_limbs_unchecked, "ll", "ll")
    ROW(add_2_2_full, plus, "llll", "ll")
    ROW(add_2_2_full, plus_assign, "llll", "ll")
    ROW(add_2_2_full, marked, "llll", "ll")
    ROW(add_2_1_full, plus, "lll", "ll")
    ROW(add_2_1_full, limb_plus, "lll", "ll")
    ROW(add_2_1_full, plus_assign, "lll", "ll")
    ROW(add_2_1_full, plus_one, "lll", "ll")
    ROW(add_2_1_full, one_plus, "lll", "ll")
    ROW(add_2_1_full, plus_assign_one, "lll", "ll")
    ROW(add_2_1_full, marked, "lll", "ll")
    ROW(sub_2_2_full, minus, "llll", "ll")
    ROW(sub_2_2_full, minus_assign, "llll", "ll")
    ROW(sub_2_2_full, marked, "llll", "ll")
    ROW(sub_2_1_full, minus, "lll", "ll")
    ROW(sub_2_1_full, minus_assign, "lll", "ll")
    ROW(sub_2_1_full, minus_one, "lll", "ll")
    ROW(sub_2_1_full, minus_assign_one, "lll", "ll")
    ROW(sub_2_1_full, marked, "lll", "ll")
    ROW(sub_1_2_full, minus, "lll", "ll")
    ROW(sub_1_2_full, one_minus, "lll", "ll")
    ROW(sub_1_2_full, marked, "lll", "ll")
    ROW(mul_2_2_full, times, "llll", "ll")
    ROW(mul_2_2_full, times_assign, "llll", "ll")
    ROW(mul_2_2_full, marked, "llll", "ll")
    ROW(mul_2_1_full, times, "lll", "ll")
    ROW(mul_2_1_full, limb_times, "lll", "ll")
    ROW(mul_2_1_full, times_assign, "lll", "ll")
    ROW(mul_2_1_full, times_one, "lll", "ll")
    ROW(mul_2_1_full, one_times, "lll", "ll")
    ROW(mul_2_1_full, times_assign_one, "lll", "ll")
    ROW(mul_2_1_full, marked, "lll", "ll")
    ROW(add_fast_2_2_full, add_fast, "llll", "ll")
    ROW(add_fast_2_2_full, marked, "llll", "ll")
    ROW(mul_pow2_2_full, ldexp, "lll", "ll")
    ROW(mul_pow2_2_full, marked, "lll", "ll")
    SOME(mul_pow2_2_full, half, "lll", "ll")
    SOME(mul_pow2_2_full, ldexp_far, "lll", "ll")
    ROW(add_2_2, finite_add, "llll", "ll")
    ROW(add_2_2, marked, "llll", "ll")
    ROW(add_2_1, finite_add, "lll", "ll")
    ROW(add_2_1, finite_limb_add, "lll", "ll")
    ROW(add_2_1, finite_add_one, "lll", "ll")
    ROW(add_2_1, finite_one_add, "lll", "ll")
    ROW(sub_2_2, finite_sub, "llll", "ll")
    ROW(sub_2_1, finite_sub, "lll", "ll")
    ROW(sub_2_1, finite_sub_one, "lll", "ll")
    ROW(sub_1_2, finite_sub, "lll", "ll")
    ROW(sub_1_2, finite_one_sub, "lll", "ll")
    ROW(mul_2_2, finite_mul, "llll", "ll")
    ROW(mul_2_1, finite_mul, "lll", "ll")
    ROW(mul_2_1, finite_limb_mul, "lll", "ll")
    ROW(mul_2_1, finite_mul_one, "lll", "ll")
    ROW(mul_2_1, finite_one_mul, "lll", "ll")
    ROW(add_fast_2_2, finite_add_fast, "llll", "ll")
    ROW(mul_pow2_2, finite_ldexp, "lll", "ll")
    SOME(mul_pow2_2, finite_ldexp_far, "lll", "ll")
    ROW(neg_2, negate, "ll", "ll")
    ROW(abs_2, abs, "ll", "ll")
    ROW(lt_2_2, less, "llll", "m")
    ROW(lt_2_2, greater, "llll", "m")
    ROW(le_2_2, less_equal, "llll", "m")
    ROW(le_2_2, greater_equal, "llll", "m")
    ROW(eq_2_2, equal, "llll", "m")
    ROW(eq_2_2, not_unequal, "llll", "m")
    ROW(lt_2_1, less, "lll", "m")
    ROW(lt_2_1, greater, "lll", "m")
    ROW(lt_2_1, less_one, "lll", "m")
    ROW(lt_2_1, greater_one, "lll", "m")
    SOME(lt_2_1, certainly_negative, "lll", "m")
    ROW(le_2_1, less_equal, "lll", "m")
    ROW(le_2_1, greater_equal, "lll", "m")
    ROW(le_2_1, less_equal_one, "lll", "m")
    ROW(le_2_1, greater_equal_one, "lll", "m")
    ROW(eq_2_1, equal, "lll", "m")
    ROW(eq_2_1, equal_rev, "lll", "m")
    ROW(eq_2_1, not_unequal, "lll", "m")
    ROW(eq_2_1, not_unequal_rev, "lll", "m")
    ROW(eq_2_1, equal_one, "lll", "m")
    ROW(eq_2_1, equal_one_rev, "lll", "m")
    ROW(eq_2_1, not_unequal_one, "lll", "m")
    ROW(eq_2_1, not_unequal_one_rev, "lll", "m")
    SOME(eq_2_1, certainly_zero, "lll", "m")
    ROW(lt_1_2, less, "lll", "m")
    ROW(lt_1_2, greater, "lll", "m")
    ROW(lt_1_2, less_one, "lll", "m")
    ROW(lt_1_2, greater_one, "lll", "m")
    SOME(lt_1_2, certainly_positive, "lll", "m")
    ROW(le_1_2, less_equal, "lll", "m")
    ROW(le_1_2, greater_equal, "lll", "m")
    ROW(le_1_2, less_equal_one, "lll", "m")
    ROW(le_1_2, greater_equal_one, "lll", "m")
    ROW(to_nearest_2, to_nearest, "ll", "l")
    ROW(to_nearest_2, narrow, "ll", "l")
    ROW(to_nearest_2, narrow_marked, "ll", "l")
    ROW(to_down_2, to_down, "ll", "l")
    ROW(to_up_2, to_up, "ll", "l")
    ROW(abs_upper_2, abs_upper, "ll", "l")
    ROW(ball_make_1, center_radius, "ll", "ll")
    ROW(ball_make_1, limb_radius, "ll", "ll")
    ROW(ball_make_2, center_radius, "lll", "lll")
    ROW(ball_make_1, constant, "ll", "ll")
    ROW(ball_make_2, constant, "lll", "lll")
    BALL_ROWS(1, "llll", "ll", "lll", "ll")
    BALL_ROWS(2, "llllll", "lll", "llll", "lll")
    SOME(ball_mul_2_full, times_center, "llllll", "lll")
    SOME(ball_mul_2_full, center_times, "llllll", "lll")
    ROW(ball_scale_1_full, scale_one, "lll", "ll")
    ROW(ball_scale_1_full, one_scale, "lll", "ll")
    ROW(ball_mul_pow2_1_full, ldexp, "lll", "ll")
    ROW(ball_mul_pow2_1_full, marked, "lll", "ll")
    SOME(ball_mul_pow2_1_full, half, "lll", "ll")
    SOME(ball_mul_pow2_1_full, ldexp_far, "lll", "ll")
    ROW(ball_mul_pow2_2_full, ldexp, "llll", "lll")
    ROW(ball_mul_pow2_2_full, marked, "llll", "lll")
    SOME(ball_mul_pow2_2_full, half, "llll", "lll")
    SOME(ball_mul_pow2_2_full, ldexp_far, "llll", "lll")
};

// Kernels that are parts of other kernels and that no public operation calls on its own. Every
// kernel of gen/claims.json is mapped above, listed here, or listed below (coverage.cmake).
const char* const internal[] = {
    "two_sum", "fast_two_sum",               // building blocks of the kernels above
    "split", "two_prod_dekker",              // the constant-evaluation variant of two_prod
    "radd",                                  // radius arithmetic of the first Ball design
    "two_sum_ord",                           // Milestone 2: building blocks of the directed sums
    "add_down_1", "add_up_1", "sub_down_1", "sub_up_1",
};
// Entry kernels (entry: yes in gen/kernels) that no public operation calls yet, and why.
struct NotPublic {
    const char* kernel;
    const char* why;
};
const char* const ball_core = "the finite core of a Ball operation: the operators call the full kernel, and "
                              "kairn::finite has no Ball forms (decision D5 names the Expansion arithmetic)";
const NotPublic not_public[] = {
    {"ball_add_1", ball_core}, {"ball_sub_1", ball_core}, {"ball_mul_1", ball_core}, {"ball_scale_1", ball_core},
    {"ball_add_2", ball_core}, {"ball_sub_2", ball_core}, {"ball_mul_2", ball_core}, {"ball_scale_2", ball_core},
    {"ball_mul_pow2_1", ball_core}, {"ball_mul_pow2_2", ball_core},
};
// The interval kernels of Milestone 2 are in neither list: the oracle does not judge them yet
// (KAIRN_NOT_YET_CROSS_CHECKED of tests/CMakeLists.txt), and such a kernel is in none of these lists
// (coverage.cmake). When it reads them, mul_dir_1, the bounds of two limbs and mul_ext_2_2 are
// building blocks of the interval kernels; the other interval kernels are for the Interval types
// (milestone2.md, "Interval kernels"), and the bounds, conversions and narrowing of a Ball are
// functions of the enclosure interface (milestone2.md, "One enclosure interface"), which come
// with the public headers of the milestone.

constexpr int max_limbs = 16;
long lineno = 0;

[[noreturn]] void fail(const std::string& why) {
    std::fflush(stdout);
    std::fprintf(stderr, "runner: line %ld: %s\n", lineno, why.c_str());
    std::exit(2);
}

// A limb is a C99 hexadecimal literal, inf, -inf or nan; strtod alone would also take decimals.
double parse(const std::string& text) {
    if (text == "inf") return std::numeric_limits<double>::infinity();
    if (text == "-inf") return -std::numeric_limits<double>::infinity();
    if (text == "nan") return std::numeric_limits<double>::quiet_NaN();
    const std::size_t x = text.find_first_of("xX");
    if (x == std::string::npos || x == 0 || text[x - 1] != '0' || text.find_first_of("pP") == std::string::npos)
        fail("not a limb: " + text);
    char* end = nullptr;
    const double v = std::strtod(text.c_str(), &end);
    if (*end != '\0') fail("not a limb: " + text);
    return v;
}

void put_limb(double v, std::string& out) {
    if (v != v) {
        out += "nan";
    } else if (v == std::numeric_limits<double>::infinity()) {
        out += "inf";
    } else if (v == -std::numeric_limits<double>::infinity()) {
        out += "-inf";
    } else {
        char buf[64];
        std::snprintf(buf, sizeof buf, "%a", v);
        out += buf;
    }
}

int usage() {
    std::fprintf(stderr,
                 "usage: runner [--form NAME] | --forms KERNEL | --list | --internal | --not-public | --self-test\n");
    return 2;
}

// kairn::self_test() and kairn::environment_ok(), compiled with this runner's flags.
int self_test() {
    const kairn::Status s = kairn::self_test();
    const bool env = kairn::environment_ok();
    std::printf("self_test: %s%s%s\nenvironment_ok: %s\nKAIRN_CHECKS: %d\n", s.message(), s.kernel ? ": " : "",
                s.kernel ? s.kernel : "", env ? "true" : "false", KAIRN_CHECKS);
    return s.ok() && env ? 0 : 1;
}

}  // namespace

int main(int argc, char** argv) {
    kairn_test::no_crash_reports();
    const char* form_name = nullptr;
    if (argc == 2 && std::strcmp(argv[1], "--self-test") == 0) return self_test();
    if (argc == 3 && std::strcmp(argv[1], "--forms") == 0) {
        for (const Form& f : forms)
            if (std::strcmp(f.kernel, argv[2]) == 0) std::printf("%s\n", f.name);
        return 0;
    }
    if (argc == 2 && std::strcmp(argv[1], "--list") == 0) {
        std::vector<std::string> seen;
        for (const Form& f : forms) {
            bool known = false;
            for (const std::string& s : seen) known = known || s == f.kernel;
            if (!known) {
                seen.push_back(f.kernel);
                std::printf("%s\n", f.kernel);
            }
        }
        return 0;
    }
    if (argc == 2 && std::strcmp(argv[1], "--internal") == 0) {
        for (const char* k : internal) std::printf("%s\n", k);
        return 0;
    }
    if (argc == 2 && std::strcmp(argv[1], "--not-public") == 0) {
        for (const NotPublic& k : not_public) std::printf("%s\t%s\n", k.kernel, k.why);
        return 0;
    }
    if (argc == 3 && std::strcmp(argv[1], "--form") == 0) {
        form_name = argv[2];
    } else if (argc != 1) {
        return usage();
    }

    std::ios::sync_with_stdio(false);
    std::string line, out;
    std::vector<std::string> fields;
    long lines = 0;
    const Form* conditional = nullptr;
    while (std::getline(std::cin, line)) {
        ++lineno;
        if (!line.empty() && line.back() == '\r') line.pop_back();
        out = line;
        if (line.empty() || line[0] == '#') {
            out += '\n';
            std::fwrite(out.data(), 1, out.size(), stdout);
            continue;
        }
        fields.clear();
        for (std::size_t start = 0;;) {
            const std::size_t space = line.find(' ', start);
            fields.push_back(line.substr(start, space - start));
            if (fields.back().empty()) fail("fields are separated by single spaces");
            if (space == std::string::npos) break;
            start = space + 1;
        }
        if (fields.back()[0] == '#') fields.pop_back();  // the tag
        if (fields.size() < 2) fail("expected KERNEL FORMAT LIMB ... [#TAG]");
        const Form* k = nullptr;
        for (const Form& f : forms) {
            if (fields[0] != f.kernel) continue;
            if (form_name ? std::strcmp(form_name, f.name) == 0 : k == nullptr) k = &f;
        }
        if (!k) fail("no public operation maps to " + fields[0] + (form_name ? std::string(" as form ") + form_name : ""));
        if (k->conditional) conditional = k;
        ++lines;
        const int inputs = int(std::strlen(k->in_kinds)), outputs = int(std::strlen(k->out_kinds));
        if (int(fields.size()) - 2 != inputs) fail(fields[0] + " takes " + std::to_string(inputs) + " limbs");
        bool mo[max_limbs] = {};
        out += " ->";
        if (fields[1] == "binary64") {
            double in[max_limbs] = {}, res[max_limbs] = {};
            for (int i = 0; i < inputs; ++i) in[i] = parse(fields[2 + i]);
            k->binary64(in, res, mo);
            for (int i = 0; i < outputs; ++i) {
                out += ' ';
                if (k->out_kinds[i] == 'm') out += mo[i] ? '1' : '0';
                else put_limb(res[i], out);
            }
        } else if (fields[1] == "binary32") {
            float in[max_limbs] = {}, res[max_limbs] = {};
            for (int i = 0; i < inputs; ++i) {
                const double v = parse(fields[2 + i]);
                const double top = std::numeric_limits<float>::max();
                if (v == v && v - v == 0 && (v > top || v < -top)) fail(fields[2 + i] + " is not a binary32 number");
                in[i] = static_cast<float>(v);
                if (static_cast<double>(in[i]) != v && v == v) fail(fields[2 + i] + " is not a binary32 number");
            }
            k->binary32(in, res, mo);
            for (int i = 0; i < outputs; ++i) {
                out += ' ';
                if (k->out_kinds[i] == 'm') out += mo[i] ? '1' : '0';
                else put_limb(static_cast<double>(res[i]), out);
            }
        } else {
            fail("this runner knows binary64 and binary32, not " + fields[1]);
        }
        out += '\n';
        std::fwrite(out.data(), 1, out.size(), stdout);
    }
    if (stopped > 0)
        std::fprintf(stderr, "runner: KAIRN_CHECKS stops a negative radius: Ball::empty() on %ld of %ld lines\n",
                     stopped, lines);
    if (conditional) {
        std::fprintf(stderr, "runner: form %s of %s computed its own operation on %ld of %ld lines\n", conditional->name,
                     conditional->kernel, reached, lines);
        if (lines >= 1000 && reached == 0) {
            std::fprintf(stderr, "runner: form %s of %s computed its own operation on none of %ld lines\n",
                         conditional->name, conditional->kernel, lines);
            return 3;
        }
    }
    return 0;
}
