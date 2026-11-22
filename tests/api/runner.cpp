// A runner of the line protocol (docs/developer/architecture.md, "The line protocol") that computes
// every result through Kairn's public interface, so that the oracle judges what a client calls:
// the constructors, operators and functions of Expansion and Ball, not the generated kernels.
//
//   runner [--form NAME]      request lines on standard input, completed lines on standard output
//   runner --forms KERNEL     the forms that must satisfy KERNEL's claims, one per line
//   runner --list             every kernel that some form maps to
//   runner --internal         the building blocks: kernels that are parts of other kernels
//   runner --not-public       entry kernels that no public operation calls yet, each with why
//   runner --packed-list      every kernel that some packed form maps to
//   runner --fold-list        every fold (gen/claims.json, "folds") that some form of the
//                             functions on arrays maps to (runner_arrays.hpp)
//   runner --folds-not-public the folds that no public function calls, each with why
//   runner --self-test        kairn::self_test() and kairn::environment_ok() as built here: exit
//                             0 if both pass (the tests of the flag sets, tests/api/flags/)
//
// The requests of the loops over arrays (folds, maps, convolutions, folds of maxima) are completed
// at once through the functions of kairn/batch.hpp, on views of the line's arrays
// (runner_arrays.hpp, which says how a form chooses its order and computes in place).
//
// The packed forms (named packed_NAME, listed after a kernel's scalar forms) compute through
// Packed<T, k> (kairn/packed.hpp) and the views of kairn/soa.hpp, in whichever form this build
// compiles (AVX2, NEON, or one lane): the stream is held until its end, and each line is
// completed in one lane of a register whose other lanes hold other lines, drawn so that registers
// mix the oracle's strata and every lane position takes its share of lines ("The packed forms",
// below). A packed form also fails at the end of a stream of at least 1000 lines that left a lane
// position without a line, or whose non-finite operands or results never shared a register with
// finite ones. Built with KAIRN_TEST_PACKED_ONLY, the runner lists only its packed forms
// (tests/api/CMakeLists.txt builds one so for AVX2 where the build's flags do not give it).
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
// of radius zero, the conversion of a SumAndError to a two-limb number a finite error term, the
// interval of a point a line whose two bounds are one value, the bounds of an interval of two limbs
// as numbers of T a line of to_down_2 or to_up_2 whose operand is not a NaN, and the member test
// of a point of T in an interval or a ball of two limbs a line whose point is a value of T (its
// second limb zero, or the NaN pair), and the limbs given to Interval::from_limbs and
// Ball::from_limbs a line whose value can be a bound, a center or a radius of a canonical
// interval or ball (not a NaN bound, not an infinite center, not a negative radius). On the other
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
#include <kairn/accumulator.hpp>
#include <kairn/kairn.hpp>
#include <kairn/packed.hpp>
#include <kairn/soa.hpp>
#include <kairn/ball_vector.hpp>
#if defined(KAIRN_TEST_CHECKS) && KAIRN_CHECKS != 1
#error "built with KAIRN_TEST_CHECKS, the runner must have KAIRN_CHECKS 1: build it without NDEBUG"
#endif

#include "no_crash_reports.hpp"
// The functions on arrays (kairn/batch.hpp): the requests of the loops over arrays, completed
// through them.
#include "runner_arrays.hpp"

#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <string>
#include <type_traits>
#include <utility>
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
template <class T>
using I1 = kairn::Interval<T, 1>;
template <class T>
using I2 = kairn::Interval<T, 2>;
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
// A ball operand with the line's limbs as they are, for the forms whose claim compares limbs, the
// sign of a zero included: the hull and the intersection of balls return an operand as it is
// (ball_set, architecture.md). The constructor's guard makes a zero center or radius +0, so these
// forms take the canonical ball the line gives through the constructor that keeps a kernel's
// result: a program has such balls from the operations (the negation of the whole line has the
// center -0), and the kernel is judged on every canonical ball the claim covers, a radius -0
// included, which no public operation returns.
template <class T>
B1<T> ball1_as_is(const T* in) {
    return B1<T>(kairn::detail::kernel_result, E1<T>(in[0]), in[1]);
}
template <class T>
B2<T> ball2_as_is(const T* in) {
    E2<T> c;
    c.limb[0] = in[0];
    c.limb[1] = in[1];
    return B2<T>(kairn::detail::kernel_result, c, in[2]);
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
// An interval operand from the limbs the oracle gives, a canonical interval, lower bound first,
// through the public constructor from two bounds: the empty set (+inf, -inf) is reversed bounds,
// which the constructor makes the empty set. A result: its bounds, the lower one first.
template <class T>
I1<T> iv1(const T* in) {
    return I1<T>(AS(interval_make_1, in[0]), in[1]);
}
template <class T>
I2<T> iv2(const T* in) {
    return I2<T>(AS(interval_make_2, two(in)), two(in + 2));
}
template <class T, int K>
void put(T* out, const kairn::Interval<T, K>& z) {
    put(out, z.lower());
    put(out + K, z.upper());
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
FORM(two_prod_entry_two_prod, put_pair(out, kairn::two_prod(AS(two_prod_entry, in[0]), in[1])))
FORM(two_prod_entry_marked, put_pair(out, kairn::two_prod(kairn::unverified(in[0]), in[1])))
FORM(next_up_next_up, out[0] = kairn::next_up(AS(next_up, in[0])))
FORM(next_up_marked, out[0] = kairn::next_up(kairn::unverified(in[0])))
FORM(next_down_next_down, out[0] = kairn::next_down(AS(next_down, in[0])))
FORM(next_down_marked, out[0] = kairn::next_down(kairn::unverified(in[0])))
// The bounds as functions of the length (traits.hpp): through kairn::traits<X>::sum_height(h),
// sum(n) and dot(n), on the lines whose count m is an integer that a std::size_t holds (h = m,
// n = m + 1 for sum, n = m for dot), the result's unit (and tiny) as g (and t), and the mask true
// exactly when the unit is finite, as the function gives it (+inf where the kernel's mask is
// false). A count that no program can give as a length (a fraction, or 2^64 and more, which the
// oracle draws to reach the limit of the kernel) is completed by the kernel itself, so that the
// stream is whole; each form computes its own operation on the integer lines, and fails if a stream
// of 1000 lines reached none.
template <class T>
bool as_length(T m, std::size_t& n) {
    if (!(m >= T(0)) || !(T(0x1p64) > m) || std::floor(m) != m) return false;
    const std::uint64_t v = static_cast<std::uint64_t>(m);
    if (v >= std::uint64_t(std::numeric_limits<std::size_t>::max())) return false;
    n = static_cast<std::size_t>(v);
    return true;
}
template <class T, int K>
using traits_k = std::conditional_t<K == 1, kairn::traits<T>, kairn::traits<E2<T>>>;
// Which: 0 sum_height(h), 1 sum(n), 2 dot(n).
template <class T, int K, int Which>
void length_bound(const T* in, T* out, bool* mo) {
    std::size_t n = 0;
    if (!as_length(in[0], n)) {
        if constexpr (Which == 2) {
            if constexpr (K == 1) kairn::gen::bound_dot_1(in[0], out[0], out[1], mo[2]);
            else kairn::gen::bound_dot_2(in[0], out[0], out[1], mo[2]);
        } else {
            if constexpr (K == 1) kairn::gen::bound_sum_1(in[0], out[0], mo[1]);
            else kairn::gen::bound_sum_2(in[0], out[0], mo[1]);
        }
        return;
    }
    ++reached;
    if constexpr (Which == 2) {
        const kairn::Bound<T> b = traits_k<T, K>::dot(n);
        out[0] = b.unit;
        out[1] = b.tiny;
        mo[2] = std::isfinite(b.unit);
    } else {
        const kairn::Bound<T> b = Which == 0 ? traits_k<T, K>::sum_height(n) : traits_k<T, K>::sum(n + 1);
        out[0] = b.unit;
        mo[1] = std::isfinite(b.unit);
    }
}
FORM(bound_sum_1_traits_sum_height, length_bound<T, 1, 0>(in, out, mo))
FORM(bound_sum_1_traits_sum, length_bound<T, 1, 1>(in, out, mo))
FORM(bound_sum_2_traits_sum_height, length_bound<T, 2, 0>(in, out, mo))
FORM(bound_sum_2_traits_sum, length_bound<T, 2, 1>(in, out, mo))
FORM(bound_dot_1_traits_dot, length_bound<T, 1, 2>(in, out, mo))
FORM(bound_dot_2_traits_dot, length_bound<T, 2, 2>(in, out, mo))
// The accumulator (accumulator.hpp): the state of the line made with Accumulator::from_state, then
// add, add_product or merge, and the state read back (running_sum(), magnitudes()), the kernel's
// outputs t and b. The other accumulator of a merge is made the same way.
template <class T, int K>
kairn::Accumulator<T, K> acc_of(const T* in) {
    if constexpr (K == 1) return kairn::Accumulator<T, 1>::from_state(E1<T>(in[0]), in[1], 0);
    else return kairn::Accumulator<T, 2>::from_state(two(in), in[2], 0);
}
template <class T, int K>
void put_acc(T* out, const kairn::Accumulator<T, K>& acc) {
    put(out, acc.running_sum());
    out[K] = acc.magnitudes();
}
template <class T, int K>
auto number_k(const T* in) {
    if constexpr (K == 1) return one(in);
    else return two(in);
}
FORM(acc_add_1_add, auto acc = acc_of<T, 1>(in); acc.add(number_k<T, 1>(in + 2)); put_acc(out, acc))
FORM(acc_add_1_add_limb, auto acc = acc_of<T, 1>(in); acc.add(in[2]); put_acc(out, acc))
FORM(acc_add_2_add, auto acc = acc_of<T, 2>(in); acc.add(number_k<T, 2>(in + 3)); put_acc(out, acc))
FORM(acc_mul_entry_1_add_product, auto acc = acc_of<T, 1>(in); acc.add_product(number_k<T, 1>(in + 2), number_k<T, 1>(in + 3));
     put_acc(out, acc))
FORM(acc_mul_entry_1_add_product_limbs, auto acc = acc_of<T, 1>(in); acc.add_product(in[2], in[3]); put_acc(out, acc))
FORM(acc_mul_entry_2_add_product, auto acc = acc_of<T, 2>(in); acc.add_product(number_k<T, 2>(in + 3), number_k<T, 2>(in + 5));
     put_acc(out, acc))
FORM(acc_merge_1_merge, auto acc = acc_of<T, 1>(in); acc.merge(acc_of<T, 1>(in + 2)); put_acc(out, acc))
FORM(acc_merge_2_merge, auto acc = acc_of<T, 2>(in); acc.merge(acc_of<T, 2>(in + 3)); put_acc(out, acc))
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
FORM(mul_down_entry_mul_down, out[0] = kairn::mul_down(AS(mul_down_entry, in[0]), in[1]))
FORM(mul_down_entry_marked, out[0] = kairn::mul_down(kairn::unverified(in[0]), in[1]))
FORM(mul_up_entry_mul_up, out[0] = kairn::mul_up(AS(mul_up_entry, in[0]), in[1]))
FORM(mul_up_entry_marked, out[0] = kairn::mul_up(kairn::unverified(in[0]), in[1]))

// Two limbs: construction.
FORM(make_2_from_limb, put(out, E2<T>(AS(make_2, in[0]))))
FORM(make_2_from_one, put(out, E2<T>(AS(make_2, one(in)))))
FORM(make_2_marked, put(out, E2<T>(kairn::unverified(in[0]))))
FORM(make_2_limbs_from_limbs, put(out, E2<T>::from_limbs(in)))
FORM(make_2_limbs_from_limbs_unchecked, put(out, E2<T>::from_limbs_unchecked(in)))
// The limbs of an interval and of a ball given to Interval::from_limbs and Ball::from_limbs, which
// pass each limb through the guard of make_2 (a value of T, of which they keep the leading limb) or
// of make_2_limbs (a pair), and read back through lower(), upper(), center() and radius(): the
// line's value, or pair, in each position where a canonical interval or ball can hold it, beside
// limbs that make one (a finite bound beside an infinite one, so that every value but a NaN is a
// bound; a finite center with radius 0, a NaN center with a NaN radius, the empty ball; a radius
// that is not negative beside the center 0, or a NaN beside a NaN center). make_2's second limb,
// which these functions do not keep, is completed as make_2's listing gives it: 0 after a number or
// an infinity, the leading limb itself after a NaN. The plain constructor on the other lines.
template <class T>
void put_lead(T* out, T x0) {
    out[0] = x0;
    out[1] = x0 == x0 ? T(0) : x0;
}
FORM(make_2_interval_from_limbs_lower, if (in[0] != in[0]) { put(out, E2<T>(in[0])); return; } ++reached;
     const T inf = std::numeric_limits<T>::infinity(); const T l[2] = {in[0], in[0] == inf ? -inf : inf};
     put_lead(out, I1<T>::from_limbs(l).lower().limb[0]))
FORM(make_2_interval_from_limbs_upper, if (in[0] != in[0]) { put(out, E2<T>(in[0])); return; } ++reached;
     const T inf = std::numeric_limits<T>::infinity(); const T l[2] = {in[0] == -inf ? inf : -inf, in[0]};
     put_lead(out, I1<T>::from_limbs(l).upper().limb[0]))
FORM(make_2_ball_from_limbs_center, if (in[0] == in[0] && !std::isfinite(in[0])) { put(out, E2<T>(in[0])); return; }
     ++reached; const T l[2] = {in[0], in[0] == in[0] ? T(0) : in[0]};
     put_lead(out, B1<T>::from_limbs(l).center().limb[0]))
FORM(make_2_ball_from_limbs_radius_1, if (in[0] < 0) { put(out, E2<T>(in[0])); return; } ++reached;
     const T l[2] = {in[0] == in[0] ? T(0) : in[0], in[0]}; put_lead(out, B1<T>::from_limbs(l).radius()))
FORM(make_2_ball_from_limbs_radius_2, if (in[0] < 0) { put(out, E2<T>(in[0])); return; } ++reached;
     const T c = in[0] == in[0] ? T(0) : in[0]; const T l[3] = {c, c, in[0]}; put_lead(out, B2<T>::from_limbs(l).radius()))
FORM(make_2_limbs_interval_from_limbs_lower, if (in[0] != in[0]) { put(out, E2<T>::from_limbs(in)); return; } ++reached;
     const T inf = std::numeric_limits<T>::infinity(); const T l[4] = {in[0], in[1], in[0] == inf ? -inf : inf, T(0)};
     put(out, I2<T>::from_limbs(l).lower()))
FORM(make_2_limbs_interval_from_limbs_upper, if (in[0] != in[0]) { put(out, E2<T>::from_limbs(in)); return; } ++reached;
     const T inf = std::numeric_limits<T>::infinity(); const T l[4] = {in[0] == -inf ? inf : -inf, T(0), in[0], in[1]};
     put(out, I2<T>::from_limbs(l).upper()))
FORM(make_2_limbs_ball_from_limbs_center,
     if (in[0] == in[0] && !std::isfinite(in[0])) { put(out, E2<T>::from_limbs(in)); return; } ++reached;
     const T l[3] = {in[0], in[1], in[0] == in[0] ? T(0) : in[0]}; put(out, B2<T>::from_limbs(l).center()))

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
FORM(mul_2_1_full_entry_times, put(out, AS(mul_2_1_full_entry, two(in)) * in[2]))
FORM(mul_2_1_full_entry_limb_times, put(out, in[2] * AS(mul_2_1_full_entry, two(in))))
FORM(mul_2_1_full_entry_times_assign, E2<T> x = two(in); x *= AS(mul_2_1_full_entry, in[2]); put(out, x))
FORM(mul_2_1_full_entry_times_one, put(out, AS(mul_2_1_full_entry, two(in)) * one(in + 2)))
FORM(mul_2_1_full_entry_one_times, put(out, one(in + 2) * AS(mul_2_1_full_entry, two(in))))
FORM(mul_2_1_full_entry_times_assign_one, E2<T> x = two(in); x *= AS(mul_2_1_full_entry, one(in + 2)); put(out, x))
FORM(mul_2_1_full_entry_marked, put(out, kairn::unverified(two(in)) * in[2]))
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
FORM(mul_2_1_entry_finite_mul, put(out, finite::mul(AS(mul_2_1_entry, two(in)), in[2])))
FORM(mul_2_1_entry_finite_limb_mul, put(out, finite::mul(in[2], AS(mul_2_1_entry, two(in)))))
FORM(mul_2_1_entry_finite_mul_one, put(out, finite::mul(AS(mul_2_1_entry, two(in)), one(in + 2))))
FORM(mul_2_1_entry_finite_one_mul, put(out, finite::mul(one(in + 2), AS(mul_2_1_entry, two(in)))))
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
#define BALL_FORMS(K, BALL, SCALE)                                                                                        \
    FORM(ball_add_##K##_full_plus, put(out, AS(ball_add_##K##_full, BALL(in)) + BALL(in + K + 1)))                 \
    FORM(ball_add_##K##_full_plus_assign, auto x = BALL(in); x += AS(ball_add_##K##_full, BALL(in + K + 1)); put(out, x)) \
    FORM(ball_add_##K##_full_marked, put(out, BALL(in) + kairn::unverified(BALL(in + K + 1))))                    \
    FORM(ball_sub_##K##_full_minus, put(out, AS(ball_sub_##K##_full, BALL(in)) - BALL(in + K + 1)))                \
    FORM(ball_sub_##K##_full_minus_assign, auto x = BALL(in); x -= AS(ball_sub_##K##_full, BALL(in + K + 1)); put(out, x)) \
    FORM(ball_sub_##K##_full_marked, put(out, BALL(in) - kairn::unverified(BALL(in + K + 1))))                    \
    FORM(ball_mul_##K##_full_times, put(out, AS(ball_mul_##K##_full, BALL(in)) * BALL(in + K + 1)))                \
    FORM(ball_mul_##K##_full_times_assign, auto x = BALL(in); x *= AS(ball_mul_##K##_full, BALL(in + K + 1)); put(out, x)) \
    FORM(ball_mul_##K##_full_marked, put(out, BALL(in) * kairn::unverified(BALL(in + K + 1))))                    \
    FORM(SCALE##_scale, put(out, AS(SCALE, BALL(in)) * in[K + 1]))                                               \
    FORM(SCALE##_scale_rev, put(out, in[K + 1] * AS(SCALE, BALL(in))))                                           \
    FORM(SCALE##_scale_assign, auto x = BALL(in); x *= AS(SCALE, in[K + 1]); put(out, x))                         \
    FORM(SCALE##_marked, put(out, kairn::unverified(BALL(in)) * in[K + 1]))                                       \
    FORM(ball_neg_##K##_negate, put(out, -AS(ball_neg_##K, BALL(in))))                                             \
    FORM(ball_neg_##K##_marked, put(out, -kairn::unverified(BALL(in))))
// The scaling of a ball of two limbs calls ball_scale_2_full_entry, which guards a first (rule R3,
// the factors of a fused operation).
BALL_FORMS(1, ball1, ball_scale_1_full)
BALL_FORMS(2, ball2, ball_scale_2_full_entry)

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

// Intervals: construction. From two values of T, from two numbers of one or two limbs, and, on the
// lines whose two bounds are one value (the same bits, or two NaN), from that point; for two limbs
// from two values of T on the lines whose bounds are such values (a second limb zero, or the NaN
// pair), converted to two limbs first. The plain constructor of two bounds otherwise.
template <class T>
bool same_value(T a, T b) {
    return (a == b && std::signbit(a) == std::signbit(b)) || (a != a && b != b);
}
template <class T>
bool a_limb(const T* x) {
    return x[1] == 0 || x[0] != x[0];
}
FORM(interval_make_1_bounds, put(out, I1<T>(AS(interval_make_1, in[0]), in[1])))
FORM(interval_make_1_bounds_one, put(out, I1<T>(AS(interval_make_1, one(in)), one(in + 1))))
FORM(interval_make_1_marked, put(out, I1<T>(kairn::unverified(in[0]), in[1])))
FORM(interval_make_1_point, if (!same_value(in[0], in[1])) { put(out, I1<T>(in[0], in[1])); return; } ++reached;
     put(out, I1<T>(AS(interval_make_1, in[0]))))
FORM(interval_make_1_point_one, if (!same_value(in[0], in[1])) { put(out, I1<T>(in[0], in[1])); return; } ++reached;
     put(out, I1<T>(AS(interval_make_1, one(in)))))
FORM(interval_make_2_bounds, put(out, I2<T>(AS(interval_make_2, two(in)), two(in + 2))))
FORM(interval_make_2_marked, put(out, I2<T>(kairn::unverified(two(in)), two(in + 2))))
FORM(interval_make_2_point,
     if (!same_value(in[0], in[2]) || !same_value(in[1], in[3])) { put(out, I2<T>(two(in), two(in + 2))); return; }
     ++reached; put(out, I2<T>(AS(interval_make_2, two(in)))))
FORM(interval_make_2_point_limb,
     if (!same_value(in[0], in[2]) || !same_value(in[1], in[3]) || !a_limb(in)) { put(out, I2<T>(two(in), two(in + 2))); return; }
     ++reached; put(out, I2<T>(AS(interval_make_2, in[0]))))
FORM(interval_make_2_limbs, if (!a_limb(in) || !a_limb(in + 2)) { put(out, I2<T>(two(in), two(in + 2))); return; } ++reached;
     put(out, I2<T>(AS(interval_make_2, in[0]), in[2])))
// The same through Interval::from_bounds, the spelling an interval shares with a ball: of two values
// of T, of two numbers of K limbs, marked; for two limbs from two values of T on the lines whose
// bounds are such values, as interval_make_2_limbs.
FORM(interval_make_1_from_bounds, put(out, I1<T>::from_bounds(AS(interval_make_1, in[0]), in[1])))
FORM(interval_make_1_from_bounds_one, put(out, I1<T>::from_bounds(AS(interval_make_1, one(in)), one(in + 1))))
FORM(interval_make_1_from_bounds_marked, put(out, I1<T>::from_bounds(kairn::unverified(in[0]), in[1])))
FORM(interval_make_2_from_bounds, put(out, I2<T>::from_bounds(AS(interval_make_2, two(in)), two(in + 2))))
FORM(interval_make_2_from_bounds_marked, put(out, I2<T>::from_bounds(kairn::unverified(two(in)), two(in + 2))))
FORM(interval_make_2_from_bounds_limbs,
     if (!a_limb(in) || !a_limb(in + 2)) { put(out, I2<T>(two(in), two(in + 2))); return; } ++reached;
     put(out, I2<T>::from_bounds(AS(interval_make_2, in[0]), in[2])))

// Intervals: arithmetic, the hull and the intersection.
#define INTERVAL_FORMS(K, IV)                                                                                       \
    FORM(interval_neg_##K##_negate, put(out, -AS(interval_neg_##K, IV(in))))                                         \
    FORM(interval_neg_##K##_marked, put(out, -kairn::unverified(IV(in))))                                            \
    FORM(interval_add_##K##_plus, put(out, AS(interval_add_##K, IV(in)) + IV(in + 2 * K)))                           \
    FORM(interval_add_##K##_plus_assign, auto x = IV(in); x += AS(interval_add_##K, IV(in + 2 * K)); put(out, x))    \
    FORM(interval_add_##K##_marked, put(out, IV(in) + kairn::unverified(IV(in + 2 * K))))                            \
    FORM(interval_sub_##K##_minus, put(out, AS(interval_sub_##K, IV(in)) - IV(in + 2 * K)))                          \
    FORM(interval_sub_##K##_minus_assign, auto x = IV(in); x -= AS(interval_sub_##K, IV(in + 2 * K)); put(out, x))   \
    FORM(interval_sub_##K##_marked, put(out, kairn::unverified(IV(in)) - IV(in + 2 * K)))                            \
    FORM(interval_mul_##K##_times, put(out, AS(interval_mul_##K, IV(in)) * IV(in + 2 * K)))                          \
    FORM(interval_mul_##K##_times_assign, auto x = IV(in); x *= AS(interval_mul_##K, IV(in + 2 * K)); put(out, x))   \
    FORM(interval_mul_##K##_marked, put(out, IV(in) * kairn::unverified(IV(in + 2 * K))))                            \
    FORM(interval_hull_##K##_hull, put(out, IV(in).hull(AS(interval_hull_##K, IV(in + 2 * K)))))                    \
    FORM(interval_hull_##K##_marked, put(out, IV(in).hull(kairn::unverified(IV(in + 2 * K)))))                       \
    FORM(interval_intersection_##K##_intersection,                                                                   \
         put(out, IV(in).intersection(AS(interval_intersection_##K, IV(in + 2 * K)))))                               \
    FORM(interval_intersection_##K##_marked, put(out, IV(in).intersection(kairn::unverified(IV(in + 2 * K)))))
INTERVAL_FORMS(1, iv1)
INTERVAL_FORMS(2, iv2)

// Intervals of one limb: the midpoint and the radius (one kernel for both), the split, and the
// conversions between an interval and a ball.
FORM(interval_mid_rad_1_midpoint_radius, const I1<T> x = iv1(in); out[0] = x.midpoint().limb[0]; out[1] = x.radius())
FORM(interval_split_1_split, const kairn::Split<I1<T>> s = iv1(in).split(); put(out, s.left); put(out + 2, s.right))
FORM(interval_to_ball_1_to_ball, put(out, B1<T>(AS(interval_to_ball_1, iv1(in)))))
FORM(interval_to_ball_1_marked, put(out, B1<T>(kairn::unverified(iv1(in)))))
FORM(ball_to_interval_1_to_interval, put(out, I1<T>(AS(ball_to_interval_1, ball1(in)))))
FORM(ball_to_interval_1_marked, put(out, I1<T>(kairn::unverified(ball1(in)))))
// The bounds of an interval of two limbs as numbers of T, which are to_down_2 and to_up_2 of the
// bound: on a line of to_down_2 whose x is not a NaN, the interval [x, +inf]; for x = +inf, which
// [+inf, +inf] would make the whole line (decided on 2026-11-20), the empty set made from the
// reversed bounds [+inf, -inf], whose lower bound is +inf. [-inf, x] for to_up_2, and for
// x = -inf the same empty set, whose upper bound is -inf. The rounding otherwise.
FORM(to_down_2_interval_lower_as, if (in[0] != in[0]) { out[0] = kairn::to_down(two(in)); return; } ++reached;
     const T inf = std::numeric_limits<T>::infinity();
     out[0] = (in[0] == inf ? I2<T>(two(in), E2<T>(-inf)) : I2<T>(two(in), E2<T>(inf))).template lower_as<T>())
FORM(to_up_2_interval_upper_as, if (in[0] != in[0]) { out[0] = kairn::to_up(two(in)); return; } ++reached;
     const T inf = std::numeric_limits<T>::infinity();
     out[0] = (in[0] == -inf ? I2<T>(E2<T>(inf), two(in)) : I2<T>(E2<T>(-inf), two(in))).template upper_as<T>())

// Balls: the functions of the interface they share with intervals.
FORM(ball_from_interval_2_from_interval, put(out, B2<T>::from_interval(AS(ball_from_interval_2, in[0]), in[1])))
FORM(ball_from_interval_2_marked, put(out, B2<T>::from_interval(kairn::unverified(in[0]), in[1])))
FORM(ball_from_interval_2_from_bounds, put(out, B2<T>::from_bounds(AS(ball_from_interval_2, in[0]), in[1])))
FORM(ball_from_interval_2_from_bounds_marked, put(out, B2<T>::from_bounds(kairn::unverified(in[0]), in[1])))
FORM(ball_lower_as_1_lower_as, out[0] = ball1(in).template lower_as<T>())
FORM(ball_lower_as_1_lower, out[0] = ball1(in).lower().limb[0])
FORM(ball_upper_as_1_upper_as, out[0] = ball1(in).template upper_as<T>())
FORM(ball_upper_as_1_upper, out[0] = ball1(in).upper().limb[0])
FORM(ball_lower_as_2_lower_as, out[0] = ball2(in).template lower_as<T>())
FORM(ball_upper_as_2_upper_as, out[0] = ball2(in).template upper_as<T>())
FORM(ball_narrow_2_1_narrow, put(out, B1<T>(AS(ball_narrow_2_1, ball2(in)))))
FORM(ball_narrow_2_1_marked, put(out, B1<T>(kairn::unverified(ball2(in)))))

// --- The enclosure interface of stage B2 (headers-pred) -------------------------------------------
//
// The predicates, the member and subset tests, the three-valued comparisons and the relations of
// IEEE 1788 of intervals and of balls, the set operations of a ball, and the midpoint, radius,
// split and conversions of two limbs (milestone2.md, "One enclosure interface"). A Trit is printed
// as the two masks of its kernel, yes then no; not_equal, whose answer is that of the kernel's
// equal with yes and no exchanged, is printed exchanged back. kairn::member on a kernel of one exact
// mask (an interval, a ball of one limb) prints the mask's yes, and stops the runner if it ever
// answers unknown, which its claim excludes. contains(t) of a ball of two limbs is the yes of its
// kernel, printed with the no of kairn::member, the other public answer of the same kernel. The
// forms whose point is a value of T of two limbs compute their own operation on the lines whose
// point is one (a_limb), and the form with a point of two limbs otherwise.
void put_trit(bool* mo, kairn::Trit t) {
    mo[0] = t == kairn::Trit::yes;
    mo[1] = t == kairn::Trit::no;
}
void put_opposite(bool* mo, kairn::Trit t) {
    mo[0] = t == kairn::Trit::no;
    mo[1] = t == kairn::Trit::yes;
}
bool known_yes(kairn::Trit t) {
    if (t == kairn::Trit::unknown) {
        std::fflush(stdout);
        std::fprintf(stderr, "runner: kairn::member answered unknown, which an exact claim excludes\n");
        std::exit(2);
    }
    return t == kairn::Trit::yes;
}
#define ENCLOSURE_INTERVAL_FORMS(K, IV)                                                                              \
    FORM(interval_empty_##K##_is_empty, mo[0] = IV(in).is_empty())                                                   \
    FORM(interval_entire_##K##_is_whole, mo[0] = IV(in).is_whole())                                                  \
    FORM(interval_subset_##K##_contains, mo[0] = IV(in + 2 * K).contains(AS(interval_subset_##K, IV(in))))           \
    FORM(interval_subset_##K##_contains_marked, mo[0] = IV(in + 2 * K).contains(kairn::unverified(IV(in))))          \
    FORM(interval_subset_##K##_ieee1788_subset,                                                                      \
         mo[0] = kairn::ieee1788::subset(AS(interval_subset_##K, IV(in)), IV(in + 2 * K)))                           \
    FORM(interval_subset_##K##_ieee1788_marked, mo[0] = kairn::ieee1788::subset(IV(in), kairn::unverified(IV(in + 2 * K)))) \
    FORM(interval_positive_##K##_certainly_positive, mo[0] = IV(in).certainly_positive())                            \
    FORM(interval_negative_##K##_certainly_negative, mo[0] = IV(in).certainly_negative())                            \
    FORM(interval_zero_##K##_certainly_zero, mo[0] = IV(in).certainly_zero())                                        \
    FORM(interval_less_##K##_less, put_trit(mo, kairn::less(AS(interval_less_##K, IV(in)), IV(in + 2 * K))))       \
    FORM(interval_less_##K##_greater, put_trit(mo, kairn::greater(IV(in + 2 * K), AS(interval_less_##K, IV(in))))) \
    FORM(interval_less_##K##_marked, put_trit(mo, kairn::less(IV(in), kairn::unverified(IV(in + 2 * K)))))         \
    FORM(interval_less_equal_##K##_less_equal,                                                                       \
         put_trit(mo, kairn::less_equal(AS(interval_less_equal_##K, IV(in)), IV(in + 2 * K))))                     \
    FORM(interval_less_equal_##K##_greater_equal,                                                                    \
         put_trit(mo, kairn::greater_equal(IV(in + 2 * K), AS(interval_less_equal_##K, IV(in)))))                  \
    FORM(interval_less_equal_##K##_marked, put_trit(mo, kairn::less_equal(kairn::unverified(IV(in)), IV(in + 2 * K)))) \
    FORM(interval_equal_##K##_equal, put_trit(mo, kairn::equal(AS(interval_equal_##K, IV(in)), IV(in + 2 * K))))  \
    FORM(interval_equal_##K##_not_equal,                                                                             \
         put_opposite(mo, kairn::not_equal(AS(interval_equal_##K, IV(in)), IV(in + 2 * K))))                       \
    FORM(interval_equal_##K##_marked, put_trit(mo, kairn::equal(IV(in), kairn::unverified(IV(in + 2 * K)))))       \
    FORM(interval_rel_equal_##K##_ieee1788_equal,                                                                    \
         mo[0] = kairn::ieee1788::equal(AS(interval_rel_equal_##K, IV(in)), IV(in + 2 * K)))                         \
    FORM(interval_rel_equal_##K##_marked, mo[0] = kairn::ieee1788::equal(kairn::unverified(IV(in)), IV(in + 2 * K)))  \
    FORM(interval_rel_interior_##K##_ieee1788_interior,                                                              \
         mo[0] = kairn::ieee1788::interior(AS(interval_rel_interior_##K, IV(in)), IV(in + 2 * K)))                   \
    FORM(interval_rel_interior_##K##_marked,                                                                         \
         mo[0] = kairn::ieee1788::interior(IV(in), kairn::unverified(IV(in + 2 * K))))                               \
    FORM(interval_rel_disjoint_##K##_ieee1788_disjoint,                                                              \
         mo[0] = kairn::ieee1788::disjoint(AS(interval_rel_disjoint_##K, IV(in)), IV(in + 2 * K)))                   \
    FORM(interval_rel_disjoint_##K##_marked,                                                                         \
         mo[0] = kairn::ieee1788::disjoint(kairn::unverified(IV(in)), IV(in + 2 * K)))
ENCLOSURE_INTERVAL_FORMS(1, iv1)
ENCLOSURE_INTERVAL_FORMS(2, iv2)
// The member test: a point of one limb, (xl, xu, t); of two, (xl0, xl1, xu0, xu1, t0, t1).
FORM(interval_contains_1_contains, mo[0] = iv1(in).contains(in[2]))
FORM(interval_contains_1_contains_one, mo[0] = iv1(in).contains(one(in + 2)))
FORM(interval_contains_1_contains_marked, mo[0] = iv1(in).contains(kairn::unverified(in[2])))
FORM(interval_contains_1_member, mo[0] = known_yes(kairn::member(in[2], iv1(in))))
FORM(interval_contains_1_member_marked, mo[0] = known_yes(kairn::member(kairn::unverified(one(in + 2)), iv1(in))))
FORM(interval_contains_2_contains, mo[0] = iv2(in).contains(two(in + 4)))
FORM(interval_contains_2_contains_marked, mo[0] = iv2(in).contains(kairn::unverified(two(in + 4))))
FORM(interval_contains_2_member, mo[0] = known_yes(kairn::member(two(in + 4), iv2(in))))
FORM(interval_contains_2_contains_limb, if (!a_limb(in + 4)) { mo[0] = iv2(in).contains(two(in + 4)); return; } ++reached;
     mo[0] = iv2(in).contains(in[4]))
FORM(interval_contains_2_member_limb, if (!a_limb(in + 4)) { mo[0] = iv2(in).contains(two(in + 4)); return; } ++reached;
     mo[0] = known_yes(kairn::member(in[4], iv2(in))))
// The midpoint and the radius together, and the split and the conversions of two limbs.
FORM(interval_mid_rad_1_mid_rad, const kairn::MidRad<T, 1> m = iv1(in).mid_rad(); put(out, m.midpoint); out[1] = m.radius)
FORM(interval_mid_rad_2_midpoint_radius, const I2<T> x = iv2(in); put(out, x.midpoint()); out[2] = x.radius())
FORM(interval_mid_rad_2_mid_rad, const kairn::MidRad<T, 2> m = iv2(in).mid_rad(); put(out, m.midpoint); out[2] = m.radius)
FORM(interval_split_2_split, const kairn::Split<I2<T>> s = iv2(in).split(); put(out, s.left); put(out + 4, s.right))
FORM(interval_to_ball_2_to_ball, put(out, B2<T>(AS(interval_to_ball_2, iv2(in)))))
FORM(interval_to_ball_2_marked, put(out, B2<T>(kairn::unverified(iv2(in)))))
FORM(ball_to_interval_2_to_interval, put(out, I2<T>(AS(ball_to_interval_2, ball2(in)))))
FORM(ball_to_interval_2_marked, put(out, I2<T>(kairn::unverified(ball2(in)))))
FORM(ball_to_interval_2_lower_upper, const B2<T> x = ball2(in); put(out, x.lower()); put(out + 2, x.upper()))
FORM(ball_from_interval_1_from_interval, put(out, B1<T>::from_interval(AS(ball_from_interval_1, in[0]), in[1])))
FORM(ball_from_interval_1_marked, put(out, B1<T>::from_interval(kairn::unverified(in[0]), in[1])))
FORM(ball_from_interval_1_from_bounds, put(out, B1<T>::from_bounds(AS(ball_from_interval_1, in[0]), in[1])))
FORM(ball_from_interval_1_from_bounds_one, put(out, B1<T>::from_bounds(AS(ball_from_interval_1, one(in)), one(in + 1))))
FORM(ball_from_interval_1_from_bounds_marked, put(out, B1<T>::from_bounds(kairn::unverified(in[0]), in[1])))
// Balls: the subset test, the signs, the comparisons and the set operations. Two balls are
// (center limbs, radius) twice.
#define ENCLOSURE_BALL_FORMS(K, BALL, AS_IS)                                                                                \
    FORM(ball_contains_ball_##K##_contains, mo[0] = BALL(in).contains(AS(ball_contains_ball_##K, BALL(in + K + 1)))) \
    FORM(ball_contains_ball_##K##_marked, mo[0] = BALL(in).contains(kairn::unverified(BALL(in + K + 1))))            \
    FORM(ball_positive_##K##_certainly_positive, mo[0] = BALL(in).certainly_positive())                              \
    FORM(ball_negative_##K##_certainly_negative, mo[0] = BALL(in).certainly_negative())                              \
    FORM(ball_zero_##K##_certainly_zero, mo[0] = BALL(in).certainly_zero())                                          \
    FORM(ball_less_##K##_less, put_trit(mo, kairn::less(AS(ball_less_##K, BALL(in)), BALL(in + K + 1))))           \
    FORM(ball_less_##K##_greater, put_trit(mo, kairn::greater(BALL(in + K + 1), AS(ball_less_##K, BALL(in)))))     \
    FORM(ball_less_##K##_marked, put_trit(mo, kairn::less(BALL(in), kairn::unverified(BALL(in + K + 1)))))         \
    FORM(ball_less_equal_##K##_less_equal,                                                                           \
         put_trit(mo, kairn::less_equal(AS(ball_less_equal_##K, BALL(in)), BALL(in + K + 1))))                     \
    FORM(ball_less_equal_##K##_greater_equal,                                                                        \
         put_trit(mo, kairn::greater_equal(BALL(in + K + 1), AS(ball_less_equal_##K, BALL(in)))))                  \
    FORM(ball_less_equal_##K##_marked, put_trit(mo, kairn::less_equal(kairn::unverified(BALL(in)), BALL(in + K + 1)))) \
    FORM(ball_equal_##K##_equal, put_trit(mo, kairn::equal(AS(ball_equal_##K, BALL(in)), BALL(in + K + 1))))       \
    FORM(ball_equal_##K##_not_equal, put_opposite(mo, kairn::not_equal(AS(ball_equal_##K, BALL(in)), BALL(in + K + 1)))) \
    FORM(ball_equal_##K##_marked, put_trit(mo, kairn::equal(BALL(in), kairn::unverified(BALL(in + K + 1)))))       \
    FORM(ball_hull_##K##_hull, put(out, AS_IS(in).hull(AS(ball_hull_##K, AS_IS(in + K + 1)))))                      \
    FORM(ball_hull_##K##_marked, put(out, AS_IS(in).hull(kairn::unverified(AS_IS(in + K + 1)))))                    \
    FORM(ball_intersection_##K##_intersection, put(out, AS_IS(in).intersection(AS(ball_intersection_##K, AS_IS(in + K + 1))))) \
    FORM(ball_intersection_##K##_marked, put(out, AS_IS(in).intersection(kairn::unverified(AS_IS(in + K + 1)))))       \
    FORM(ball_split_##K##_split, const auto s = BALL(in).split(); put(out, s.left); put(out + K + 1, s.right))
ENCLOSURE_BALL_FORMS(1, ball1, ball1_as_is)
ENCLOSURE_BALL_FORMS(2, ball2, ball2_as_is)
// The member test of a ball: (c, r, t) for one limb, (c0, c1, r, t0, t1) for two.
FORM(ball_contains_point_1_contains, mo[0] = ball1(in).contains(in[2]))
FORM(ball_contains_point_1_contains_one, mo[0] = ball1(in).contains(one(in + 2)))
FORM(ball_contains_point_1_contains_marked, mo[0] = ball1(in).contains(kairn::unverified(in[2])))
FORM(ball_contains_point_1_member, mo[0] = known_yes(kairn::member(in[2], ball1(in))))
FORM(ball_contains_point_1_member_marked, mo[0] = known_yes(kairn::member(one(in + 2), kairn::unverified(ball1(in)))))
FORM(ball_contains_point_2_member, put_trit(mo, kairn::member(two(in + 3), ball2(in))))
FORM(ball_contains_point_2_contains, const B2<T> x = ball2(in); mo[0] = x.contains(two(in + 3));
     mo[1] = kairn::member(two(in + 3), x) == kairn::Trit::no)
FORM(ball_contains_point_2_contains_marked, const B2<T> x = ball2(in); mo[0] = x.contains(kairn::unverified(two(in + 3)));
     mo[1] = kairn::member(kairn::unverified(two(in + 3)), x) == kairn::Trit::no)
FORM(ball_contains_point_2_member_limb, if (!a_limb(in + 3)) { put_trit(mo, kairn::member(two(in + 3), ball2(in))); return; }
     ++reached; put_trit(mo, kairn::member(in[3], ball2(in))))
FORM(ball_contains_point_2_contains_limb, const B2<T> x = ball2(in);
     if (!a_limb(in + 3)) { put_trit(mo, kairn::member(two(in + 3), x)); return; } ++reached;
     mo[0] = x.contains(in[3]); mo[1] = kairn::member(in[3], x) == kairn::Trit::no)
// --- The end of the enclosure interface of stage B2 ------------------------------------------------

// --- The packed forms ---------------------------------------------------------------------------
//
// The operations of Packed<T, k> (kairn/packed.hpp) and the reads of kairn/soa.hpp, one lane per
// line: the main loop gives a packed form W consecutive lines of one format (W the lanes of the
// limb type, fewer at the end of the stream or before a comment), lane (j + b) mod W to the j-th
// line of the b-th batch, so that every line meets every lane position in turn and shares its
// register with the lines beside it, a NaN or an overflow with finite numbers. A lane without a
// line computes a copy of the first line of the batch, and its results are not written. Each
// operand is loaded from arrays as a program loads it (Packed::load, which is from_limbs in each
// lane). A form is the packed counterpart of the scalar form of the same name, named
// packed_NAME; on the lines that a conditional form cannot compute (see the top of the file), it
// computes, in that lane, the plain operation, packed too.
template <class T>
using PK1 = kairn::Packed<T, 1>;
template <class T>
using PK2 = kairn::Packed<T, 2>;
template <class T>
inline constexpr int lanes_of = kairn::Packed<T, 1>::lanes;
template <class T>
struct Lanes {
    const T* in[lanes_of<T>];   // the inputs of the line of each lane
    T* out[lanes_of<T>];
    bool* mo[lanes_of<T>];
};

// Operands: the limbs at k of every lane, loaded.
template <class T>
PK1<T> pone(const Lanes<T>& b, int k) {
    T a[lanes_of<T>];
    for (int i = 0; i < lanes_of<T>; ++i) a[i] = b.in[i][k];
    return PK1<T>::load(a);
}
template <class T>
PK2<T> ptwo(const Lanes<T>& b, int k) {
    T h[lanes_of<T>], l[lanes_of<T>];
    for (int i = 0; i < lanes_of<T>; ++i) {
        h[i] = b.in[i][k];
        l[i] = b.in[i][k + 1];
    }
    return PK2<T>::load(h, l);
}
// Results: stored into arrays, then into the outputs of each lane.
template <class T>
void pput(const Lanes<T>& b, const PK1<T>& z) {
    T a[lanes_of<T>];
    z.store(a);
    for (int i = 0; i < lanes_of<T>; ++i) b.out[i][0] = a[i];
}
template <class T>
void pput(const Lanes<T>& b, const PK2<T>& z) {
    T h[lanes_of<T>], l[lanes_of<T>];
    z.store(h, l);
    for (int i = 0; i < lanes_of<T>; ++i) {
        b.out[i][0] = h[i];
        b.out[i][1] = l[i];
    }
}
template <class T>
void pmask(const Lanes<T>& b, const kairn::PackedMask<T>& m) {
    for (int i = 0; i < lanes_of<T>; ++i) b.mo[i][0] = m.lane(i);
}
// Lane i of a result into the outputs of lane i only.
template <class T, int K>
void put_lane(const Lanes<T>& b, int i, const kairn::Packed<T, K>& z) {
    put(b.out[i], z.lane(i));
}

// One packed form, compiled only where its kernel is proved: Packed has no marked operations.
#define PFORM(NAME, KERNEL, ...)                                                    \
    template <class T>                                                              \
    void packed_##KERNEL##_##NAME([[maybe_unused]] const Lanes<T>& b) {            \
        if constexpr (PROVED(KERNEL)) {                                             \
            __VA_ARGS__;                                                            \
        } else {                                                                    \
            std::abort();                                                           \
        }                                                                           \
    }

// Two limbs: construction, from a one-limb number, and the loads; the reads of a view.
PFORM(from_one, make_2, pput(b, PK2<T>(pone(b, 0))))
PFORM(load, make_2_limbs, pput(b, ptwo(b, 0)))
template <class T>
void packed_load_unchecked(const Lanes<T>& b) {
    T h[lanes_of<T>], l[lanes_of<T>];
    for (int i = 0; i < lanes_of<T>; ++i) {
        h[i] = b.in[i][0];
        l[i] = b.in[i][1];
    }
    pput(b, PK2<T>::load_unchecked(h, l));
}
PFORM(load_unchecked, make_2_limbs, packed_load_unchecked<T>(b))
PFORM(from_limbs, make_2_limbs, const PK2<T> x = ptwo(b, 0); pput(b, PK2<T>::from_limbs(x.limb[0], x.limb[1])))
// Through views of the line's limbs as arrays: element i of the view read as a number (the proxy
// converted), and the W elements loaded as a Packed; and, from the second lane on, the tail rule:
// load_partial of the last lanes - 1 elements, which reads exactly those.
template <class T, int Mode>
void packed_soa(const Lanes<T>& b) {
    T h[lanes_of<T>], l[lanes_of<T>];
    for (int i = 0; i < lanes_of<T>; ++i) {
        h[i] = b.in[i][0];
        l[i] = b.in[i][1];
    }
    const kairn::SoAView<const T, 2> v(h, l, std::size_t(lanes_of<T>));
    if constexpr (Mode == 0) {
        for (int i = 0; i < lanes_of<T>; ++i) put(b.out[i], E2<T>(v[std::size_t(i)]));
    } else if constexpr (Mode == 1) {
        pput(b, v.load(0));
    } else {
        // Lane 0 from load, the others from load_partial at 1 of the rest; lane 0 of that is
        // element 1.
        const PK2<T> head = v.load(0);
        const PK2<T> tail = v.load_partial(1, lanes_of<T> - 1);
        put_lane(b, 0, head);
        for (int i = 1; i < lanes_of<T>; ++i) put(b.out[i], tail.lane(i - 1));
    }
}
PFORM(soa_get, make_2_limbs, packed_soa<T, 0>(b))
PFORM(soa_load, make_2_limbs, packed_soa<T, 1>(b))
PFORM(soa_load_partial, make_2_limbs, packed_soa<T, 2>(b))

// Two limbs: arithmetic, the full kernels.
PFORM(plus, add_2_2_full, pput(b, ptwo(b, 0) + ptwo(b, 2)))
PFORM(plus_assign, add_2_2_full, PK2<T> x = ptwo(b, 0); x += ptwo(b, 2); pput(b, x))
PFORM(plus, add_2_1_full, pput(b, ptwo(b, 0) + pone(b, 2)))
PFORM(limb_plus, add_2_1_full, pput(b, pone(b, 2) + ptwo(b, 0)))
PFORM(plus_assign, add_2_1_full, PK2<T> x = ptwo(b, 0); x += pone(b, 2); pput(b, x))
PFORM(minus, sub_2_2_full, pput(b, ptwo(b, 0) - ptwo(b, 2)))
PFORM(minus_assign, sub_2_2_full, PK2<T> x = ptwo(b, 0); x -= ptwo(b, 2); pput(b, x))
PFORM(minus, sub_2_1_full, pput(b, ptwo(b, 0) - pone(b, 2)))
PFORM(minus_assign, sub_2_1_full, PK2<T> x = ptwo(b, 0); x -= pone(b, 2); pput(b, x))
PFORM(minus, sub_1_2_full, pput(b, pone(b, 0) - ptwo(b, 1)))
PFORM(times, mul_2_2_full, pput(b, ptwo(b, 0) * ptwo(b, 2)))
PFORM(times_assign, mul_2_2_full, PK2<T> x = ptwo(b, 0); x *= ptwo(b, 2); pput(b, x))
PFORM(times, mul_2_1_full_entry, pput(b, ptwo(b, 0) * pone(b, 2)))
PFORM(limb_times, mul_2_1_full_entry, pput(b, pone(b, 2) * ptwo(b, 0)))
PFORM(times_assign, mul_2_1_full_entry, PK2<T> x = ptwo(b, 0); x *= pone(b, 2); pput(b, x))
PFORM(add_fast, add_fast_2_2_full, pput(b, kairn::add_fast(ptwo(b, 0), ptwo(b, 2))))
// ldexp(x, ilogb(c)) with each lane's c in turn; half and the steps of ldexp where the scalar
// forms compute them, ldexp in the other lanes.
template <class T, bool Finite>
void packed_ldexp_2(const Lanes<T>& b) {
    const PK2<T> x = ptwo(b, 0);
    for (int i = 0; i < lanes_of<T>; ++i) {
        if constexpr (Finite) put_lane(b, i, finite::ldexp(x, std::ilogb(b.in[i][2])));
        else put_lane(b, i, kairn::ldexp(x, std::ilogb(b.in[i][2])));
    }
}
PFORM(ldexp, mul_pow2_2_full, packed_ldexp_2<T, false>(b))
template <class T>
void packed_half_2(const Lanes<T>& b) {
    const PK2<T> x = ptwo(b, 0);
    T h[lanes_of<T>], l[lanes_of<T>];
    bool use[lanes_of<T>];
    for (int i = 0; i < lanes_of<T>; ++i) {
        T y[2];
        use[i] = std::isfinite(b.in[i][0]) && exact_scale(b.in[i], 2, std::ilogb(b.in[i][2]) + 1, y);
        h[i] = use[i] ? y[0] : b.in[i][0];
        l[i] = use[i] ? y[1] : b.in[i][1];
    }
    const PK2<T> z = kairn::half(PK2<T>::load(h, l));
    for (int i = 0; i < lanes_of<T>; ++i) {
        if (!use[i]) {
            put_lane(b, i, kairn::ldexp(x, std::ilogb(b.in[i][2])));
            continue;
        }
        ++reached;
        put_lane(b, i, z);
    }
}
PFORM(half, mul_pow2_2_full, packed_half_2<T>(b))
template <class T, bool Finite>
void packed_ldexp_far_2(const Lanes<T>& b) {
    const PK2<T> x = ptwo(b, 0);
    T h[lanes_of<T>], l[lanes_of<T>];
    int n[lanes_of<T>] = {};
    bool use[lanes_of<T>];
    for (int i = 0; i < lanes_of<T>; ++i) {
        T y[2];
        use[i] = (Finite || std::isfinite(b.in[i][0])) && far_split(b.in[i], 2, std::ilogb(b.in[i][2]), y, n[i]);
        h[i] = use[i] ? y[0] : b.in[i][0];
        l[i] = use[i] ? y[1] : b.in[i][1];
    }
    const PK2<T> yy = PK2<T>::load(h, l);
    for (int i = 0; i < lanes_of<T>; ++i) {
        const int m = std::ilogb(b.in[i][2]);
        if (!use[i]) {
            if constexpr (Finite) put_lane(b, i, finite::ldexp(x, m));
            else put_lane(b, i, kairn::ldexp(x, m));
            continue;
        }
        ++reached;
        if constexpr (Finite) put_lane(b, i, finite::ldexp(yy, n[i]));
        else put_lane(b, i, kairn::ldexp(yy, n[i]));
    }
}
PFORM(ldexp_far, mul_pow2_2_full, packed_ldexp_far_2<T, false>(b))

// Two limbs: the finite cores.
PFORM(finite_add, add_2_2, pput(b, finite::add(ptwo(b, 0), ptwo(b, 2))))
PFORM(finite_add, add_2_1, pput(b, finite::add(ptwo(b, 0), pone(b, 2))))
PFORM(finite_limb_add, add_2_1, pput(b, finite::add(pone(b, 2), ptwo(b, 0))))
PFORM(finite_sub, sub_2_2, pput(b, finite::sub(ptwo(b, 0), ptwo(b, 2))))
PFORM(finite_sub, sub_2_1, pput(b, finite::sub(ptwo(b, 0), pone(b, 2))))
PFORM(finite_sub, sub_1_2, pput(b, finite::sub(pone(b, 0), ptwo(b, 1))))
PFORM(finite_mul, mul_2_2, pput(b, finite::mul(ptwo(b, 0), ptwo(b, 2))))
PFORM(finite_mul, mul_2_1_entry, pput(b, finite::mul(ptwo(b, 0), pone(b, 2))))
PFORM(finite_limb_mul, mul_2_1_entry, pput(b, finite::mul(pone(b, 2), ptwo(b, 0))))
PFORM(finite_add_fast, add_fast_2_2, pput(b, finite::add_fast(ptwo(b, 0), ptwo(b, 2))))
PFORM(finite_ldexp, mul_pow2_2, packed_ldexp_2<T, true>(b))
PFORM(finite_ldexp_far, mul_pow2_2, packed_ldexp_far_2<T, true>(b))

// Two limbs: negation, absolute value, comparisons (and a select on one), conversions to T.
PFORM(negate, neg_2, pput(b, -ptwo(b, 0)))
PFORM(abs, abs_2, pput(b, kairn::abs(ptwo(b, 0))))
PFORM(less, lt_2_2, pmask(b, ptwo(b, 0) < ptwo(b, 2)))
PFORM(greater, lt_2_2, pmask(b, ptwo(b, 2) > ptwo(b, 0)))
// The comparison through select: 1 where it holds, 0 elsewhere, read back as the mask.
template <class T>
void packed_select(const Lanes<T>& b) {
    const PK1<T> z = kairn::select(ptwo(b, 0) < ptwo(b, 2), PK1<T>::broadcast(E1<T>(T(1))), PK1<T>());
    for (int i = 0; i < lanes_of<T>; ++i) b.mo[i][0] = z.lane(i).limb[0] == T(1);
}
PFORM(select, lt_2_2, packed_select<T>(b))
PFORM(less_equal, le_2_2, pmask(b, ptwo(b, 0) <= ptwo(b, 2)))
PFORM(greater_equal, le_2_2, pmask(b, ptwo(b, 2) >= ptwo(b, 0)))
PFORM(equal, eq_2_2, pmask(b, ptwo(b, 0) == ptwo(b, 2)))
PFORM(not_unequal, eq_2_2, pmask(b, !(ptwo(b, 0) != ptwo(b, 2))))
PFORM(less, lt_2_1, pmask(b, ptwo(b, 0) < pone(b, 2)))
PFORM(greater, lt_2_1, pmask(b, pone(b, 2) > ptwo(b, 0)))
PFORM(less_equal, le_2_1, pmask(b, ptwo(b, 0) <= pone(b, 2)))
PFORM(greater_equal, le_2_1, pmask(b, pone(b, 2) >= ptwo(b, 0)))
PFORM(equal, eq_2_1, pmask(b, ptwo(b, 0) == pone(b, 2)))
PFORM(equal_rev, eq_2_1, pmask(b, pone(b, 2) == ptwo(b, 0)))
PFORM(not_unequal, eq_2_1, pmask(b, !(ptwo(b, 0) != pone(b, 2))))
PFORM(not_unequal_rev, eq_2_1, pmask(b, !(pone(b, 2) != ptwo(b, 0))))
PFORM(less, lt_1_2, pmask(b, pone(b, 0) < ptwo(b, 1)))
PFORM(greater, lt_1_2, pmask(b, ptwo(b, 1) > pone(b, 0)))
PFORM(less_equal, le_1_2, pmask(b, pone(b, 0) <= ptwo(b, 1)))
PFORM(greater_equal, le_1_2, pmask(b, ptwo(b, 1) >= pone(b, 0)))
PFORM(to_nearest, to_nearest_2, pput(b, kairn::to_nearest(ptwo(b, 0))))
PFORM(narrow, to_nearest_2, pput(b, PK1<T>(ptwo(b, 0))))
PFORM(to_down, to_down_2, pput(b, kairn::to_down(ptwo(b, 0))))
PFORM(to_up, to_up_2, pput(b, kairn::to_up(ptwo(b, 0))))
PFORM(abs_upper, abs_upper_2, pput(b, kairn::abs_upper(ptwo(b, 0))))
#undef PFORM

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
#define BALL_ROWS(K, SCALE, IN, OUT, IN_SCALE, IN_NEG)     \
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
    ROW(SCALE, scale, IN_SCALE, OUT)                     \
    ROW(SCALE, scale_rev, IN_SCALE, OUT)                 \
    ROW(SCALE, scale_assign, IN_SCALE, OUT)              \
    ROW(SCALE, marked, IN_SCALE, OUT)                    \
    ROW(ball_neg_##K, negate, IN_NEG, OUT)               \
    ROW(ball_neg_##K, marked, IN_NEG, OUT)
// One interval is ONE limbs (K a bound), two are TWO.
#define INTERVAL_ROWS(K, ONE, TWO)                                 \
    ROW(interval_neg_##K, negate, ONE, ONE)                        \
    ROW(interval_neg_##K, marked, ONE, ONE)                        \
    ROW(interval_add_##K, plus, TWO, ONE)                          \
    ROW(interval_add_##K, plus_assign, TWO, ONE)                   \
    ROW(interval_add_##K, marked, TWO, ONE)                        \
    ROW(interval_sub_##K, minus, TWO, ONE)                         \
    ROW(interval_sub_##K, minus_assign, TWO, ONE)                  \
    ROW(interval_sub_##K, marked, TWO, ONE)                        \
    ROW(interval_mul_##K, times, TWO, ONE)                         \
    ROW(interval_mul_##K, times_assign, TWO, ONE)                  \
    ROW(interval_mul_##K, marked, TWO, ONE)                        \
    ROW(interval_hull_##K, hull, TWO, ONE)                         \
    ROW(interval_hull_##K, marked, TWO, ONE)                       \
    ROW(interval_intersection_##K, intersection, TWO, ONE)         \
    ROW(interval_intersection_##K, marked, TWO, ONE)
// The enclosure interface of stage B2: one interval is ONE limbs, two are TWO; one ball is ONE limbs,
// two are TWO (and the two parts of a split).
#define ENCLOSURE_INTERVAL_ROWS(K, ONE, TWO)                   \
    ROW(interval_empty_##K, is_empty, ONE, "m")                \
    ROW(interval_entire_##K, is_whole, ONE, "m")               \
    ROW(interval_subset_##K, contains, TWO, "m")               \
    ROW(interval_subset_##K, contains_marked, TWO, "m")        \
    ROW(interval_subset_##K, ieee1788_subset, TWO, "m")        \
    ROW(interval_subset_##K, ieee1788_marked, TWO, "m")        \
    ROW(interval_positive_##K, certainly_positive, ONE, "m")   \
    ROW(interval_negative_##K, certainly_negative, ONE, "m")   \
    ROW(interval_zero_##K, certainly_zero, ONE, "m")           \
    ROW(interval_less_##K, less, TWO, "mm")                    \
    ROW(interval_less_##K, greater, TWO, "mm")                 \
    ROW(interval_less_##K, marked, TWO, "mm")                  \
    ROW(interval_less_equal_##K, less_equal, TWO, "mm")        \
    ROW(interval_less_equal_##K, greater_equal, TWO, "mm")     \
    ROW(interval_less_equal_##K, marked, TWO, "mm")            \
    ROW(interval_equal_##K, equal, TWO, "mm")                  \
    ROW(interval_equal_##K, not_equal, TWO, "mm")              \
    ROW(interval_equal_##K, marked, TWO, "mm")                 \
    ROW(interval_rel_equal_##K, ieee1788_equal, TWO, "m")      \
    ROW(interval_rel_equal_##K, marked, TWO, "m")              \
    ROW(interval_rel_interior_##K, ieee1788_interior, TWO, "m") \
    ROW(interval_rel_interior_##K, marked, TWO, "m")           \
    ROW(interval_rel_disjoint_##K, ieee1788_disjoint, TWO, "m") \
    ROW(interval_rel_disjoint_##K, marked, TWO, "m")
#define ENCLOSURE_BALL_ROWS(K, ONE, TWO, PARTS)                \
    ROW(ball_contains_ball_##K, contains, TWO, "m")            \
    ROW(ball_contains_ball_##K, marked, TWO, "m")              \
    ROW(ball_positive_##K, certainly_positive, ONE, "m")       \
    ROW(ball_negative_##K, certainly_negative, ONE, "m")       \
    ROW(ball_zero_##K, certainly_zero, ONE, "m")               \
    ROW(ball_less_##K, less, TWO, "mm")                        \
    ROW(ball_less_##K, greater, TWO, "mm")                     \
    ROW(ball_less_##K, marked, TWO, "mm")                      \
    ROW(ball_less_equal_##K, less_equal, TWO, "mm")            \
    ROW(ball_less_equal_##K, greater_equal, TWO, "mm")         \
    ROW(ball_less_equal_##K, marked, TWO, "mm")                \
    ROW(ball_equal_##K, equal, TWO, "mm")                      \
    ROW(ball_equal_##K, not_equal, TWO, "mm")                  \
    ROW(ball_equal_##K, marked, TWO, "mm")                     \
    ROW(ball_hull_##K, hull, TWO, ONE)                         \
    ROW(ball_hull_##K, marked, TWO, ONE)                       \
    ROW(ball_intersection_##K, intersection, TWO, ONE)         \
    ROW(ball_intersection_##K, marked, TWO, ONE)               \
    ROW(ball_split_##K, split, ONE, PARTS)

// The first form of each kernel is its canonical one.
const Form forms[] = {
    ROW(two_sum_entry, two_sum, "ll", "ll")
    ROW(two_sum_entry, marked, "ll", "ll")
    SOME(two_sum_entry, to_expansion, "ll", "ll")
    ROW(fast_two_sum_entry, fast_two_sum, "ll", "ll")
    ROW(fast_two_sum_entry, marked, "ll", "ll")
    SOME(fast_two_sum_entry, to_expansion, "ll", "ll")
    ROW(two_prod_entry, two_prod, "ll", "ll")
    ROW(two_prod_entry, marked, "ll", "ll")
    ROW(next_up, next_up, "l", "l")
    ROW(next_up, marked, "l", "l")
    ROW(next_down, next_down, "l", "l")
    ROW(next_down, marked, "l", "l")
    ROW(radd_entry, radd, "ll", "l")
    ROW(radd_entry, marked, "ll", "l")
    ROW(rmul, rmul, "ll", "l")
    ROW(rmul, marked, "ll", "l")
    SOME(bound_sum_1, traits_sum_height, "l", "lm")
    SOME(bound_sum_1, traits_sum, "l", "lm")
    SOME(bound_sum_2, traits_sum_height, "l", "lm")
    SOME(bound_sum_2, traits_sum, "l", "lm")
    SOME(bound_dot_1, traits_dot, "l", "llm")
    SOME(bound_dot_2, traits_dot, "l", "llm")
    ROW(acc_add_1, add, "lll", "ll")
    ROW(acc_add_1, add_limb, "lll", "ll")
    ROW(acc_add_2, add, "lllll", "lll")
    ROW(acc_mul_entry_1, add_product, "llll", "ll")
    ROW(acc_mul_entry_1, add_product_limbs, "llll", "ll")
    ROW(acc_mul_entry_2, add_product, "lllllll", "lll")
    ROW(acc_merge_1, merge, "llll", "ll")
    ROW(acc_merge_2, merge, "llllll", "lll")
    ROW(add_down_entry, add_down, "ll", "l")
    ROW(add_down_entry, marked, "ll", "l")
    ROW(add_up_entry, add_up, "ll", "l")
    ROW(add_up_entry, marked, "ll", "l")
    ROW(sub_down_entry, sub_down, "ll", "l")
    ROW(sub_down_entry, marked, "ll", "l")
    ROW(sub_up_entry, sub_up, "ll", "l")
    ROW(sub_up_entry, marked, "ll", "l")
    ROW(mul_down_entry, mul_down, "ll", "l")
    ROW(mul_down_entry, marked, "ll", "l")
    ROW(mul_up_entry, mul_up, "ll", "l")
    ROW(mul_up_entry, marked, "ll", "l")
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
    SOME(make_2, interval_from_limbs_lower, "l", "ll")
    SOME(make_2, interval_from_limbs_upper, "l", "ll")
    SOME(make_2, ball_from_limbs_center, "l", "ll")
    SOME(make_2, ball_from_limbs_radius_1, "l", "ll")
    SOME(make_2, ball_from_limbs_radius_2, "l", "ll")
    SOME(make_2_limbs, interval_from_limbs_lower, "ll", "ll")
    SOME(make_2_limbs, interval_from_limbs_upper, "ll", "ll")
    SOME(make_2_limbs, ball_from_limbs_center, "ll", "ll")
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
    ROW(mul_2_1_full_entry, times, "lll", "ll")
    ROW(mul_2_1_full_entry, limb_times, "lll", "ll")
    ROW(mul_2_1_full_entry, times_assign, "lll", "ll")
    ROW(mul_2_1_full_entry, times_one, "lll", "ll")
    ROW(mul_2_1_full_entry, one_times, "lll", "ll")
    ROW(mul_2_1_full_entry, times_assign_one, "lll", "ll")
    ROW(mul_2_1_full_entry, marked, "lll", "ll")
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
    ROW(mul_2_1_entry, finite_mul, "lll", "ll")
    ROW(mul_2_1_entry, finite_limb_mul, "lll", "ll")
    ROW(mul_2_1_entry, finite_mul_one, "lll", "ll")
    ROW(mul_2_1_entry, finite_one_mul, "lll", "ll")
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
    ROW(lt_1_2, less, "lll", "m")
    ROW(lt_1_2, greater, "lll", "m")
    ROW(lt_1_2, less_one, "lll", "m")
    ROW(lt_1_2, greater_one, "lll", "m")
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
    BALL_ROWS(1, ball_scale_1_full, "llll", "ll", "lll", "ll")
    BALL_ROWS(2, ball_scale_2_full_entry, "llllll", "lll", "llll", "lll")
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
    ROW(interval_make_1, bounds, "ll", "ll")
    ROW(interval_make_1, bounds_one, "ll", "ll")
    ROW(interval_make_1, marked, "ll", "ll")
    SOME(interval_make_1, point, "ll", "ll")
    SOME(interval_make_1, point_one, "ll", "ll")
    ROW(interval_make_2, bounds, "llll", "llll")
    ROW(interval_make_2, marked, "llll", "llll")
    SOME(interval_make_2, point, "llll", "llll")
    SOME(interval_make_2, point_limb, "llll", "llll")
    SOME(interval_make_2, limbs, "llll", "llll")
    ROW(interval_make_1, from_bounds, "ll", "ll")
    ROW(interval_make_1, from_bounds_one, "ll", "ll")
    ROW(interval_make_1, from_bounds_marked, "ll", "ll")
    ROW(interval_make_2, from_bounds, "llll", "llll")
    ROW(interval_make_2, from_bounds_marked, "llll", "llll")
    SOME(interval_make_2, from_bounds_limbs, "llll", "llll")
    INTERVAL_ROWS(1, "ll", "llll")
    INTERVAL_ROWS(2, "llll", "llllllll")
    ROW(interval_mid_rad_1, midpoint_radius, "ll", "ll")
    ROW(interval_split_1, split, "ll", "llll")
    ROW(interval_to_ball_1, to_ball, "ll", "ll")
    ROW(interval_to_ball_1, marked, "ll", "ll")
    ROW(ball_to_interval_1, to_interval, "ll", "ll")
    ROW(ball_to_interval_1, marked, "ll", "ll")
    SOME(to_down_2, interval_lower_as, "ll", "l")
    SOME(to_up_2, interval_upper_as, "ll", "l")
    ROW(ball_from_interval_2, from_interval, "ll", "lll")
    ROW(ball_from_interval_2, marked, "ll", "lll")
    ROW(ball_from_interval_2, from_bounds, "ll", "lll")
    ROW(ball_from_interval_2, from_bounds_marked, "ll", "lll")
    ROW(ball_lower_as_1, lower_as, "ll", "l")
    ROW(ball_lower_as_1, lower, "ll", "l")
    ROW(ball_upper_as_1, upper_as, "ll", "l")
    ROW(ball_upper_as_1, upper, "ll", "l")
    ROW(ball_lower_as_2, lower_as, "lll", "l")
    ROW(ball_upper_as_2, upper_as, "lll", "l")
    ROW(ball_narrow_2_1, narrow, "lll", "ll")
    ROW(ball_narrow_2_1, marked, "lll", "ll")
    // The enclosure interface of stage B2 (headers-pred).
    ENCLOSURE_INTERVAL_ROWS(1, "ll", "llll")
    ENCLOSURE_INTERVAL_ROWS(2, "llll", "llllllll")
    ROW(interval_contains_1, contains, "lll", "m")
    ROW(interval_contains_1, contains_one, "lll", "m")
    ROW(interval_contains_1, contains_marked, "lll", "m")
    ROW(interval_contains_1, member, "lll", "m")
    ROW(interval_contains_1, member_marked, "lll", "m")
    ROW(interval_contains_2, contains, "llllll", "m")
    ROW(interval_contains_2, contains_marked, "llllll", "m")
    ROW(interval_contains_2, member, "llllll", "m")
    SOME(interval_contains_2, contains_limb, "llllll", "m")
    SOME(interval_contains_2, member_limb, "llllll", "m")
    ROW(interval_mid_rad_1, mid_rad, "ll", "ll")
    ROW(interval_mid_rad_2, midpoint_radius, "llll", "lll")
    ROW(interval_mid_rad_2, mid_rad, "llll", "lll")
    ROW(interval_split_2, split, "llll", "llllllll")
    ROW(interval_to_ball_2, to_ball, "llll", "lll")
    ROW(interval_to_ball_2, marked, "llll", "lll")
    ROW(ball_to_interval_2, to_interval, "lll", "llll")
    ROW(ball_to_interval_2, marked, "lll", "llll")
    ROW(ball_to_interval_2, lower_upper, "lll", "llll")
    ROW(ball_from_interval_1, from_interval, "ll", "ll")
    ROW(ball_from_interval_1, marked, "ll", "ll")
    ROW(ball_from_interval_1, from_bounds, "ll", "ll")
    ROW(ball_from_interval_1, from_bounds_one, "ll", "ll")
    ROW(ball_from_interval_1, from_bounds_marked, "ll", "ll")
    ENCLOSURE_BALL_ROWS(1, "ll", "llll", "llll")
    ENCLOSURE_BALL_ROWS(2, "lll", "llllll", "llllll")
    ROW(ball_contains_point_1, contains, "lll", "m")
    ROW(ball_contains_point_1, contains_one, "lll", "m")
    ROW(ball_contains_point_1, contains_marked, "lll", "m")
    ROW(ball_contains_point_1, member, "lll", "m")
    ROW(ball_contains_point_1, member_marked, "lll", "m")
    ROW(ball_contains_point_2, member, "lllll", "mm")
    ROW(ball_contains_point_2, contains, "lllll", "mm")
    ROW(ball_contains_point_2, contains_marked, "lllll", "mm")
    SOME(ball_contains_point_2, member_limb, "lllll", "mm")
    SOME(ball_contains_point_2, contains_limb, "lllll", "mm")
};

// The packed forms: each kernel's after its scalar ones, so that a kernel's first form stays the
// scalar one (the debug build's runner runs that one only). A runner built with
// KAIRN_TEST_PACKED_ONLY lists these alone (the runner of the AVX2 form where the build's flags do
// not have it, tests/api/CMakeLists.txt).
struct PackedForm {
    const char* kernel;
    const char* name;
    const char* in_kinds;
    const char* out_kinds;
    bool conditional;
    void (*binary64)(const Lanes<double>&);
    void (*binary32)(const Lanes<float>&);
};
#define PROW(KERNEL, NAME, IN, OUT) \
    {#KERNEL, "packed_" #NAME, IN, OUT, false, packed_##KERNEL##_##NAME<double>, packed_##KERNEL##_##NAME<float>},
#define PSOME(KERNEL, NAME, IN, OUT) \
    {#KERNEL, "packed_" #NAME, IN, OUT, true, packed_##KERNEL##_##NAME<double>, packed_##KERNEL##_##NAME<float>},
const PackedForm packed_forms[] = {
    PROW(make_2, from_one, "l", "ll")
    PROW(make_2_limbs, load, "ll", "ll")
    PROW(make_2_limbs, load_unchecked, "ll", "ll")
    PROW(make_2_limbs, from_limbs, "ll", "ll")
    PROW(make_2_limbs, soa_get, "ll", "ll")
    PROW(make_2_limbs, soa_load, "ll", "ll")
    PROW(make_2_limbs, soa_load_partial, "ll", "ll")
    PROW(add_2_2_full, plus, "llll", "ll")
    PROW(add_2_2_full, plus_assign, "llll", "ll")
    PROW(add_2_1_full, plus, "lll", "ll")
    PROW(add_2_1_full, limb_plus, "lll", "ll")
    PROW(add_2_1_full, plus_assign, "lll", "ll")
    PROW(sub_2_2_full, minus, "llll", "ll")
    PROW(sub_2_2_full, minus_assign, "llll", "ll")
    PROW(sub_2_1_full, minus, "lll", "ll")
    PROW(sub_2_1_full, minus_assign, "lll", "ll")
    PROW(sub_1_2_full, minus, "lll", "ll")
    PROW(mul_2_2_full, times, "llll", "ll")
    PROW(mul_2_2_full, times_assign, "llll", "ll")
    PROW(mul_2_1_full_entry, times, "lll", "ll")
    PROW(mul_2_1_full_entry, limb_times, "lll", "ll")
    PROW(mul_2_1_full_entry, times_assign, "lll", "ll")
    PROW(add_fast_2_2_full, add_fast, "llll", "ll")
    PROW(mul_pow2_2_full, ldexp, "lll", "ll")
    PSOME(mul_pow2_2_full, half, "lll", "ll")
    PSOME(mul_pow2_2_full, ldexp_far, "lll", "ll")
    PROW(add_2_2, finite_add, "llll", "ll")
    PROW(add_2_1, finite_add, "lll", "ll")
    PROW(add_2_1, finite_limb_add, "lll", "ll")
    PROW(sub_2_2, finite_sub, "llll", "ll")
    PROW(sub_2_1, finite_sub, "lll", "ll")
    PROW(sub_1_2, finite_sub, "lll", "ll")
    PROW(mul_2_2, finite_mul, "llll", "ll")
    PROW(mul_2_1_entry, finite_mul, "lll", "ll")
    PROW(mul_2_1_entry, finite_limb_mul, "lll", "ll")
    PROW(add_fast_2_2, finite_add_fast, "llll", "ll")
    PROW(mul_pow2_2, finite_ldexp, "lll", "ll")
    PSOME(mul_pow2_2, finite_ldexp_far, "lll", "ll")
    PROW(neg_2, negate, "ll", "ll")
    PROW(abs_2, abs, "ll", "ll")
    PROW(lt_2_2, less, "llll", "m")
    PROW(lt_2_2, greater, "llll", "m")
    PROW(lt_2_2, select, "llll", "m")
    PROW(le_2_2, less_equal, "llll", "m")
    PROW(le_2_2, greater_equal, "llll", "m")
    PROW(eq_2_2, equal, "llll", "m")
    PROW(eq_2_2, not_unequal, "llll", "m")
    PROW(lt_2_1, less, "lll", "m")
    PROW(lt_2_1, greater, "lll", "m")
    PROW(le_2_1, less_equal, "lll", "m")
    PROW(le_2_1, greater_equal, "lll", "m")
    PROW(eq_2_1, equal, "lll", "m")
    PROW(eq_2_1, equal_rev, "lll", "m")
    PROW(eq_2_1, not_unequal, "lll", "m")
    PROW(eq_2_1, not_unequal_rev, "lll", "m")
    PROW(lt_1_2, less, "lll", "m")
    PROW(lt_1_2, greater, "lll", "m")
    PROW(le_1_2, less_equal, "lll", "m")
    PROW(le_1_2, greater_equal, "lll", "m")
    PROW(to_nearest_2, to_nearest, "ll", "l")
    PROW(to_nearest_2, narrow, "ll", "l")
    PROW(to_down_2, to_down, "ll", "l")
    PROW(to_up_2, to_up, "ll", "l")
    PROW(abs_upper_2, abs_upper, "ll", "l")
};
#undef PROW
#undef PSOME

// Kernels that are parts of other kernels and that no public operation calls on its own. Every
// kernel of gen/claims.json is mapped above, listed here, or listed below (coverage.cmake).
const char* const internal[] = {
    "two_sum", "fast_two_sum",               // building blocks of the kernels above
    "split", "two_prod_dekker",              // the constant-evaluation variant of two_prod and two_prod_entry
    // The products that the public operations call through their entry forms, which guard the
    // operands first (rule R3, the factors of a fused operation): two_prod (two_prod_entry, and inside
    // the products of two limbs), mul_down_1 and mul_up_1 (mul_down_entry, mul_up_entry), mul_2_1
    // (mul_2_1_entry, and inside the scalings) and mul_2_1_full (mul_2_1_full_entry).
    "two_prod", "mul_down_1", "mul_up_1", "mul_2_1", "mul_2_1_full",
    // And the products of the accumulator, which add_product reaches through acc_mul_entry_1 and
    // acc_mul_entry_2, which guard the factors first.
    "acc_mul_1", "acc_mul_2",
    // And the scaling of a ball of two limbs, core and full form, which the operators reach through
    // ball_scale_2_full_entry, which guards the scalar first.
    "ball_scale_2", "ball_scale_2_full",
    "radd",                                  // radius arithmetic of the first Ball design
    "two_sum_ord",                           // Milestone 2: building blocks of the directed sums
    "add_down_1", "add_up_1", "sub_down_1", "sub_up_1",
    // Milestone 2, building blocks of the interval kernels: the directed products of one limb, the
    // bounds of two limbs of a sum and of a product, and the product of two bounds of two limbs.
    "mul_dir_1", "add_ball_2_2", "mul_ball_2_2", "add_down_2_2", "add_up_2_2", "sub_down_2_2", "sub_up_2_2",
    "mul_dir_2_2", "mul_ext_2_2",
    // Milestone 2, the parts of the loops over arrays of kairn/batch.hpp that are not entry kernels:
    // the finish of the folds and maps, and the kernels of the folds of maxima (norm_upper_k), which
    // the public functions reach inside their loops, judged as api.oracle.FOLD.FORMAT.
    "fold_finish_1", "fold_finish_2", "norm_combine", "norm_step_1", "norm_step_2", "norm_finish_1",
    "norm_finish_2",
    // The radius of an accumulator (accumulator.hpp): Accumulator::error_bound() calls it on the
    // (g, t) that bound_dot_k gives for the count, never on given ones, so no form computes the
    // kernel on a line's own (g, t); the composition is judged end to end in exact arithmetic
    // (api.arrays.exact.accumulator).
    "acc_radius_1", "acc_radius_2",
};
// Entry kernels (entry: yes in gen/kernels) that no public operation calls yet, and why.
struct NotPublic {
    const char* kernel;
    const char* why;
};
const char* const ball_core = "the finite core of a Ball operation: the operators call the full kernel, and "
                              "kairn::finite has no Ball forms (decision D5 names the Expansion arithmetic)";
const char* const fold_step = "the step of a loop over arrays of the program (kairn/batch.hpp): the public "
                              "function calls the loop, not the step on its own, and the oracle judges the "
                              "loop's claims through it (api.oracle.FOLD.FORMAT)";
const NotPublic not_public[] = {
    {"ball_add_1", ball_core}, {"ball_sub_1", ball_core}, {"ball_mul_1", ball_core}, {"ball_scale_1", ball_core},
    {"ball_add_2", ball_core}, {"ball_sub_2", ball_core}, {"ball_mul_2", ball_core},
    {"ball_mul_pow2_1", ball_core}, {"ball_mul_pow2_2", ball_core},
    {"sum_entry_step_1", fold_step}, {"sum_entry_step_2", fold_step}, {"sum_fast_entry_step_2", fold_step},
    {"dot_entry_step_1", fold_step}, {"add_entry_step_1", fold_step}, {"add_entry_step_2", fold_step},
    {"sub_entry_step_1", fold_step}, {"sub_entry_step_2", fold_step}, {"scale_entry_step_2", fold_step},
    {"mul_pow2_step_1", fold_step},
    {"mul_pow2_step_2", fold_step}, {"axpy_entry_step_1", fold_step}, {"axpy_entry_step_2_1", fold_step},
    {"axpy_entry_step_2", fold_step}, {"dot_entry_step_2", fold_step},
};
// The interval kernels of Milestone 2 are reached by the forms of Interval (interval.hpp) and of
// the functions of a Ball of the enclosure interface (ball.hpp), and so are the 53 kernels of the
// enclosure interface of stage B2 (predicates, comparisons, relations of IEEE 1788, set operations
// of a ball, conversions of two limbs); their building blocks are in `internal` above. The kernels
// of the loops over arrays that kairn/batch.hpp calls are in the two lists above, but the steps of
// the scalings and of the dot products that the loops of kairn/ball_vector.hpp call (scale_step_k,
// dot_step_k: dot_step_1, the step of dot_1 on stored arrays, is the coefficients' step of
// bv_conv_1, while kairn::dot and kairn::conv of one limb call dot_1_entry and conv_1_entry), and
// the other parts of those loops, which are on its list of loop parts (runner_ball_vector.hpp,
// loop_parts). Those that no public operation calls (the steps of the maps on stored arrays) are in
// none of these lists (KAIRN_NOT_PUBLIC_YET of tests/CMakeLists.txt, coverage.cmake).

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

// The loops of kairn/ball_vector.hpp: their forms (the lines of a loop name the loop, not a kernel),
// and the kernels that are parts of them (runner_ball_vector.hpp).
#include "runner_ball_vector.hpp"

int usage() {
    std::fprintf(stderr,
                 "usage: runner [--form NAME] | --forms KERNEL | --list | --packed-list | --internal | --not-public | "
                 "--fold-list | --folds-not-public | --loops | --loop-parts | --self-test\n");
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

// The stream of a packed form, held until its end: each request line is completed in a register
// with W - 1 others (see "The packed forms" above). The lines of one kernel's form and one format
// (a stream may have lines of several kernels with a form of that name, as the regression cases
// do) are put in an order drawn by a fixed pseudo-random sequence, the same on every platform, and
// fill the registers W at a time, in that order: the oracle writes its strata in a fixed pattern,
// which consecutive or strided lines would follow, so that a NaN might never share a register with
// a finite number, nor a stratum take every lane position. A lane without a line (in the last
// register) computes a copy of the register's first line, and its results are not written.
struct Pending {
    std::string line;
    const PackedForm* form = nullptr;  // none for a comment
    bool binary64 = true;
    double in64[max_limbs] = {};
    float in32[max_limbs] = {};
    bool nonfinite = false;      // an input limb that is an infinity or a NaN
    double res[max_limbs] = {};  // the results, float ones converted exactly
    bool mo[max_limbs] = {};
};
// What one packed form computed.
struct Stats {
    const PackedForm* form = nullptr;
    int width = 1;
    long registers = 0, lines = 0;
    long per_lane[16] = {};
    long nonfinite_in = 0, nonfinite_out = 0;  // lines with a non-finite input, output
    long mixed_in = 0, mixed_out = 0;          // registers mixing finite and non-finite lines
};
struct Batches {
    std::vector<Pending> entries;
    std::vector<Stats> stats;
    bool active = false;  // the stream is that of a packed form

    template <class T>
    void complete(const PackedForm* form, const std::vector<std::size_t>& index, Stats& st) {
        constexpr int w = lanes_of<T>;
        st.width = w;
        // The order: Fisher-Yates with SplitMix64, seeded once per group.
        std::vector<std::size_t> order = index;
        std::uint64_t state = 0x6b6169726e;
        for (std::size_t i = order.size(); i > 1; --i) {
            std::uint64_t z = (state += 0x9e3779b97f4a7c15u);
            z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9u;
            z = (z ^ (z >> 27)) * 0x94d049bb133111ebu;
            z ^= z >> 31;
            std::swap(order[i - 1], order[std::size_t(z % i)]);
        }
        const std::size_t n = order.size(), rows = (n + w - 1) / w;
        const int outputs = int(std::strlen(form->out_kinds));
        for (std::size_t r = 0; r < rows; ++r) {
            Pending* at[w];
            T res[w][max_limbs] = {};
            bool mo[w][max_limbs] = {};
            Lanes<T> b{};
            for (int l = 0; l < w; ++l) {
                const std::size_t t = r * std::size_t(w) + std::size_t(l);
                at[l] = t < n ? &entries[order[t]] : nullptr;
                const Pending& p = at[l] ? *at[l] : entries[order[r * std::size_t(w)]];
                if constexpr (sizeof(T) == 8) {
                    b.in[l] = p.in64;
                } else {
                    b.in[l] = p.in32;
                }
                b.out[l] = res[l];
                b.mo[l] = mo[l];
            }
            if constexpr (sizeof(T) == 8) {
                form->binary64(b);
            } else {
                form->binary32(b);
            }
            ++st.registers;
            bool finite_in = false, other_in = false, finite_out = false, other_out = false;
            for (int l = 0; l < w; ++l) {
                Pending* p = at[l];
                if (!p) continue;
                ++st.per_lane[l];
                ++st.lines;
                bool nonfinite = false;
                for (int i = 0; i < outputs; ++i) {
                    p->res[i] = static_cast<double>(res[l][i]);
                    p->mo[i] = mo[l][i];
                    if (form->out_kinds[i] != 'm') nonfinite = nonfinite || !std::isfinite(p->res[i]);
                }
                (p->nonfinite ? other_in : finite_in) = true;
                (nonfinite ? other_out : finite_out) = true;
                st.nonfinite_in += p->nonfinite;
                st.nonfinite_out += nonfinite;
            }
            st.mixed_in += finite_in && other_in;
            st.mixed_out += finite_out && other_out;
        }
    }
    // Completes every line and writes the stream, in its order.
    void finish() {
        if (!active) return;
        // Not named forms: MSVC's C4459 reports a local that hides the table of that name.
        std::vector<const PackedForm*> used;
        for (const Pending& p : entries) {
            bool known = !p.form;
            for (const PackedForm* f : used) known = known || f == p.form;
            if (!known) used.push_back(p.form);
        }
        for (const PackedForm* f : used) {
            stats.push_back(Stats{});
            Stats& st = stats.back();
            st.form = f;
            for (bool b64 : {true, false}) {
                std::vector<std::size_t> index;
                for (std::size_t e = 0; e < entries.size(); ++e)
                    if (entries[e].form == f && entries[e].binary64 == b64) index.push_back(e);
                if (index.empty()) continue;
                if (b64) {
                    complete<double>(f, index, st);
                } else {
                    complete<float>(f, index, st);
                }
            }
        }
        std::string out;
        for (const Pending& p : entries) {
            out = p.line;
            if (p.form) {
                out += " ->";
                const int outputs = int(std::strlen(p.form->out_kinds));
                for (int i = 0; i < outputs; ++i) {
                    out += ' ';
                    if (p.form->out_kinds[i] == 'm') out += p.mo[i] ? '1' : '0';
                    else put_limb(p.res[i], out);
                }
            }
            out += '\n';
            std::fwrite(out.data(), 1, out.size(), stdout);
        }
    }
    // What each packed form computed, on the standard error; false if a stream, long enough, left
    // a lane position without a line, or had non-finite operands or results that never shared a
    // register with finite ones: the batching did not do what it is for.
    bool report() const {
        bool ok = true;
        for (const Stats& st : stats) {
            std::string per;
            bool every_lane = true;
            for (int l = 0; l < st.width; ++l) {
                per += (l ? " " : "") + std::to_string(st.per_lane[l]);
                every_lane = every_lane && st.per_lane[l] > 0;
            }
            std::fprintf(stderr,
                         "runner: packed form %s of %s: %ld lines in %ld registers of %d lanes; lines per lane: %s; "
                         "registers with finite and non-finite operands: %ld (lines with a non-finite operand: "
                         "%ld), results: %ld (%ld)\n",
                         st.form->name, st.form->kernel, st.lines, st.registers, st.width, per.c_str(), st.mixed_in,
                         st.nonfinite_in, st.mixed_out, st.nonfinite_out);
            if (st.width == 1 || st.lines < 1000) continue;
            const bool mixed = (st.nonfinite_in == 0 || st.nonfinite_in == st.lines || st.mixed_in > 0) &&
                               (st.nonfinite_out == 0 || st.nonfinite_out == st.lines || st.mixed_out > 0);
            if (!every_lane || !mixed) {
                std::fprintf(stderr, "runner: packed form %s of %s: %s\n", st.form->name, st.form->kernel,
                             !every_lane ? "a lane position computed no line"
                                         : "no register mixed finite and non-finite lines");
                ok = false;
            }
        }
        return ok;
    }
};

}  // namespace

int main(int argc, char** argv) {
    kairn_test::no_crash_reports();
    const char* form_name = nullptr;
    if (argc == 2 && std::strcmp(argv[1], "--self-test") == 0) return self_test();
    if (argc == 3 && std::strcmp(argv[1], "--forms") == 0) {
#if !defined(KAIRN_TEST_PACKED_ONLY)
        for (const Form& f : forms)
            if (std::strcmp(f.kernel, argv[2]) == 0) std::printf("%s\n", f.name);
#endif
        for (const PackedForm& f : packed_forms)
            if (std::strcmp(f.kernel, argv[2]) == 0) std::printf("%s\n", f.name);
        for (const ArrayForm& f : array_forms)
            if (array_form_listed(f) && std::strcmp(f.fold, argv[2]) == 0) std::printf("%s\n", f.name);
        // The forms of a loop of kairn/ball_vector.hpp; in the runner of the packed forms alone,
        // those of the fast order, which compute with its packed loops.
        for (const bv_forms::FoldForm& f : bv_forms::fold_forms) {
#if defined(KAIRN_TEST_PACKED_ONLY)
            if (!f.fast) continue;
#endif
            if (std::strcmp(f.loop, argv[2]) == 0) std::printf("%s\n", f.name);
        }
        return 0;
    }
    if (argc == 2 && std::strcmp(argv[1], "--fold-list") == 0) {
        std::vector<std::string> seen;
        for (const ArrayForm& f : array_forms) {
            bool known = !array_form_listed(f);
            for (const std::string& s : seen) known = known || s == f.fold;
            if (!known) {
                seen.push_back(f.fold);
                std::printf("%s\n", f.fold);
            }
        }
        return 0;
    }
    // The loops that some form maps to, and the kernels that are parts of them (kernel, a tab, the
    // loop): api.oracle.coverage checks both against gen/claims.json and gen/kernels.
    if (argc == 2 && std::strcmp(argv[1], "--loops") == 0) {
        std::vector<std::string> seen;
        for (const bv_forms::FoldForm& f : bv_forms::fold_forms) {
            bool known = false;
            for (const std::string& s : seen) known = known || s == f.loop;
            if (!known) {
                seen.push_back(f.loop);
                std::printf("%s\n", f.loop);
            }
        }
        return 0;
    }
    if (argc == 2 && std::strcmp(argv[1], "--folds-not-public") == 0) {
        for (const FoldNotPublic& k : folds_not_public) std::printf("%s\t%s\n", k.fold, k.why);
        return 0;
    }
    if (argc == 2 && std::strcmp(argv[1], "--loop-parts") == 0) {
        for (const bv_forms::LoopPart& p : bv_forms::loop_parts) std::printf("%s\t%s\n", p.kernel, p.loop);
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
    if (argc == 2 && std::strcmp(argv[1], "--packed-list") == 0) {
        std::vector<std::string> seen;
        for (const PackedForm& f : packed_forms) {
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
    const PackedForm* packed_conditional = nullptr;
    const bv_forms::FoldForm* fold_conditional = nullptr;
    Batches batch;
    while (std::getline(std::cin, line)) {
        ++lineno;
        if (!line.empty() && line.back() == '\r') line.pop_back();
        out = line;
        if (line.empty() || line[0] == '#') {
            if (batch.active) {
                Pending p;
                p.line = line;
                batch.entries.push_back(p);
                continue;
            }
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
        // A loop over arrays: completed at once, through the function of kairn/batch.hpp.
        const ArrayForm* af = nullptr;
        for (const ArrayForm& f : array_forms) {
            if (!array_form_listed(f) || fields[0] != f.fold) continue;
            if (form_name ? std::strcmp(form_name, f.name) == 0 : af == nullptr) af = &f;
        }
        if (af) {
            if (batch.active) fail("a packed form's stream has lines of packed forms only");
            ++lines;
            if (fields[1] != "binary64" && fields[1] != "binary32")
                fail("this runner knows binary64 and binary32, not " + fields[1]);
            out += " ->";
            const std::string why = fields[1] == "binary64"
                                        ? complete_array_line<double>(*af, fields, out, parse, put_limb)
                                        : complete_array_line<float>(*af, fields, out, parse, put_limb);
            if (!why.empty()) fail(why);
            out += '\n';
            std::fwrite(out.data(), 1, out.size(), stdout);
            continue;
        }
        // A line of a loop of kairn/ball_vector.hpp: completed now, by its form.
        const bv_forms::FoldForm* fk = nullptr;
        for (const bv_forms::FoldForm& f : bv_forms::fold_forms) {
            if (fields[0] != f.loop) continue;
            if (form_name ? std::strcmp(form_name, f.name) == 0 : fk == nullptr) fk = &f;
        }
        if (fk) {
            if (batch.active) fail("a packed form's stream has lines of packed forms only");
            ++lines;
            if (fk->conditional) fold_conditional = fk;
            if (fields[1] == "binary64") {
                bv_forms::complete<double>(*fk, fields, out, fk->binary64);
            } else if (fields[1] == "binary32") {
                bv_forms::complete<float>(*fk, fields, out, fk->binary32);
            } else {
                fail("this runner knows binary64 and binary32, not " + fields[1]);
            }
            out += '\n';
            std::fwrite(out.data(), 1, out.size(), stdout);
            continue;
        }
        const Form* k = nullptr;
        const PackedForm* pk = nullptr;
        for (const Form& f : forms) {
            if (fields[0] != f.kernel) continue;
            if (form_name ? std::strcmp(form_name, f.name) == 0 : k == nullptr) k = &f;
        }
        if (!k && form_name)
            for (const PackedForm& f : packed_forms)
                if (fields[0] == f.kernel && std::strcmp(form_name, f.name) == 0) pk = &f;
        if (!k && !pk)
            fail("no public operation maps to " + fields[0] + (form_name ? std::string(" as form ") + form_name : ""));
        ++lines;
        const char* in_kinds = k ? k->in_kinds : pk->in_kinds;
        const int inputs = int(std::strlen(in_kinds));
        if (int(fields.size()) - 2 != inputs) fail(fields[0] + " takes " + std::to_string(inputs) + " limbs");
        if (fields[1] != "binary64" && fields[1] != "binary32")
            fail("this runner knows binary64 and binary32, not " + fields[1]);
        const bool binary64 = fields[1] == "binary64";
        double in64[max_limbs] = {};
        float in32[max_limbs] = {};
        for (int i = 0; i < inputs; ++i) {
            const double v = parse(fields[2 + i]);
            in64[i] = v;
            if (!binary64) {
                const double top = std::numeric_limits<float>::max();
                if (v == v && v - v == 0 && (v > top || v < -top)) fail(fields[2 + i] + " is not a binary32 number");
                in32[i] = static_cast<float>(v);
                if (static_cast<double>(in32[i]) != v && v == v) fail(fields[2 + i] + " is not a binary32 number");
            }
        }
        if (pk || batch.active) {
            // A packed form: the line waits for the end of the stream (Batches).
            if (!pk) fail("a packed form's stream has lines of packed forms only");
            if (pk->conditional) packed_conditional = pk;
            batch.active = true;
            Pending p;
            p.line = line;
            p.form = pk;
            p.binary64 = binary64;
            for (int i = 0; i < inputs; ++i) {
                p.in64[i] = in64[i];
                p.in32[i] = in32[i];
                p.nonfinite = p.nonfinite || !std::isfinite(in64[i]);
            }
            batch.entries.push_back(p);
            continue;
        }
        if (k->conditional) conditional = k;
        const int outputs = int(std::strlen(k->out_kinds));
        bool mo[max_limbs] = {};
        out += " ->";
        if (binary64) {
            double res[max_limbs] = {};
            k->binary64(in64, res, mo);
            for (int i = 0; i < outputs; ++i) {
                out += ' ';
                if (k->out_kinds[i] == 'm') out += mo[i] ? '1' : '0';
                else put_limb(res[i], out);
            }
        } else {
            float res[max_limbs] = {};
            k->binary32(in32, res, mo);
            for (int i = 0; i < outputs; ++i) {
                out += ' ';
                if (k->out_kinds[i] == 'm') out += mo[i] ? '1' : '0';
                else put_limb(static_cast<double>(res[i]), out);
            }
        }
        out += '\n';
        std::fwrite(out.data(), 1, out.size(), stdout);
    }
    batch.finish();
    if (stopped > 0)
        std::fprintf(stderr, "runner: KAIRN_CHECKS stops a negative radius: Ball::empty() on %ld of %ld lines\n",
                     stopped, lines);
    const char* cond_name = conditional          ? conditional->name
                            : packed_conditional ? packed_conditional->name
                            : fold_conditional   ? fold_conditional->name
                                                 : nullptr;
    const char* cond_kernel = conditional          ? conditional->kernel
                              : packed_conditional ? packed_conditional->kernel
                              : fold_conditional   ? fold_conditional->loop
                                                   : nullptr;
    if (cond_name) {
        std::fprintf(stderr, "runner: form %s of %s computed its own operation on %ld of %ld lines\n", cond_name,
                     cond_kernel, reached, lines);
        if (lines >= 1000 && reached == 0) {
            std::fprintf(stderr, "runner: form %s of %s computed its own operation on none of %ld lines\n", cond_name,
                         cond_kernel, lines);
            return 3;
        }
    }
    if (!batch.report()) return 3;
    return 0;
}
