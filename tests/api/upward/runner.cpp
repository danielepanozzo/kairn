// A runner of the line protocol (docs/developer/architecture.md, "The line protocol") that computes
// every result of the kernels of the round-up interval through the public interface of
// <kairn/upward.hpp>, so that the oracle judges what a client calls: the constructors, operators,
// members and functions of kairn::upward::Interval<T> and the functions on arrays, not the
// generated kernels. Requires the rounding mode upward set by kairn::upward::Scope and the options
// of docs/concepts/upward.md (GCC and Clang -frounding-math, MSVC /fp:strict): built with
// kairn::upward. The tests api.oracle.upward_K.F (tests/api/upward/CMakeLists.txt).
//
//   runner [--form NAME]   request lines on standard input, completed lines on standard output
//   runner --forms KERNEL  the forms that must satisfy KERNEL's claims, one per line
//   runner --list          every kernel that some form maps to (api.oracle.coverage)
//   runner --self-test     kairn::upward::self_test() as built here: exit 0 if it passes
//
// A state is its two lanes as stored, (u, n) = (b, -a) of [a, b], the empty set nan nan
// (design page, "Claims and the oracle"); every operand is built through
// Interval<T>::from_limbs, every result read through to_limbs (or, for the conversion to the
// default type, its bounds), so that what reaches the operation is what a client would have. A
// form uses an operation without kairn::unverified when gen/upward.hpp says that its kernel is
// proved, as a client would, and with the marker otherwise, so that the runner follows the proofs
// as they land; the forms named marked always write the marker.
//
// The runner holds a kairn::upward::Scope around the evaluation of each line, the numbers parsed
// before it and printed after it, through memory. The forms of the functions on arrays (named
// arrays and arrays_inplace) hold the stream until its end and complete its lines in blocks of 17
// of one format, each line an element of the views, so that the registers of the array form
// (AVX2: 4 double, 8 float; NEON: 2 and 4) and the elements after them both compute lines, and a
// line shares its registers with other lines: arrays calls the function where the mode is to
// nearest, so that its own scope sets it, arrays_inplace inside a Scope with the view written the
// first view read. A function on arrays with a number takes one number for the whole view: there
// each line's number is given to a call on the block, and the line's element is kept.
//
// One form computes its own operation on some lines only: the interval of a point, Interval(a),
// which upward_make_1 gives on a line whose two bounds are one value; on the other lines it
// computes Interval(lo, hi), and it fails at the end of a stream of at least 1000 lines in which it
// computed none.
//
// binary64 requests run on double, binary32 requests on float; a mask is 0 or 1. KAIRN_CHECKS is
// off, as in tests/api/runner.cpp, unless the build defines KAIRN_TEST_CHECKS (the runner of the
// checked build, which must then report nothing: every operand the oracle gives is canonical).
#if !defined(KAIRN_TEST_CHECKS)
#define KAIRN_CHECKS 0
#endif
#include <kairn/upward.hpp>
#if defined(KAIRN_TEST_CHECKS) && KAIRN_CHECKS != 1
#error "built with KAIRN_TEST_CHECKS, the runner must have KAIRN_CHECKS 1: build it without NDEBUG"
#endif

#include "../no_crash_reports.hpp"

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

namespace {

template <class T>
using I = kairn::upward::Interval<T>;
template <class T>
using D = kairn::Interval<T, 1>;
namespace up = kairn::upward;

// The operand as a client writes it: itself if the kernel is proved, marked otherwise.
#define PROVED(KERNEL) kairn::gen::upward::bounds::KERNEL<T>::proved
#define AS(KERNEL, x)                             \
    [&] {                                         \
        if constexpr (PROVED(KERNEL)) return (x); \
        else return kairn::unverified(x);         \
    }()
// The same for t - X, a composition of two kernels: unmarked when both are proved.
#define AS_BOTH(K1, K2, x)                                   \
    [&] {                                                    \
        if constexpr (PROVED(K1) && PROVED(K2)) return (x);  \
        else return kairn::unverified(x);                    \
    }()

constexpr int max_limbs = 6;

// Operands and results.
template <class T>
I<T> iv(const T* in) {
    return I<T>::from_limbs(in);
}
template <class T>
void put(T* out, const I<T>& z) {
    z.to_limbs(out);
}
template <class T>
void put(T* out, const D<T>& z) {
    out[0] = z.lower().limb[0];
    out[1] = z.upper().limb[0];
}
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
        std::fprintf(stderr, "runner: kairn::upward::member answered unknown, which an exact claim excludes\n");
        std::exit(2);
    }
    return t == kairn::Trit::yes;
}
template <class T>
bool same_value(T a, T b) {
    return a == b ? std::signbit(a) == std::signbit(b) : (a != a && b != b);
}

// How often the conditional form computed its own operation.
long reached = 0;

// One form of one line: a function template, instantiated for double and float in the table below.
#define FORM(NAME, ...)                                                                           \
    template <class T>                                                                            \
    void NAME([[maybe_unused]] const T* in, [[maybe_unused]] T* out, [[maybe_unused]] bool* mo) { \
        __VA_ARGS__;                                                                              \
    }

// The arithmetic. x - (-t) and -((-t) - x) are x + t, exactly (the negations are exact), so they
// ask for the rounded sum the claims of upward_add_num_1 are about, through the compositions x - t
// and t - x of the header.
FORM(add_plus, put(out, AS(upward_add_1, iv(in)) + iv(in + 2)))
FORM(add_plus_assign, I<T> x = iv(in); x += AS(upward_add_1, iv(in + 2)); put(out, x))
FORM(add_marked, put(out, kairn::unverified(iv(in)) + iv(in + 2)))
FORM(add_marked_assign, I<T> x = iv(in); x += kairn::unverified(iv(in + 2)); put(out, x))
FORM(sub_minus, put(out, AS(upward_sub_1, iv(in)) - iv(in + 2)))
FORM(sub_minus_assign, I<T> x = iv(in); x -= AS(upward_sub_1, iv(in + 2)); put(out, x))
FORM(sub_marked, put(out, iv(in) - kairn::unverified(iv(in + 2))))
FORM(sub_marked_assign, I<T> x = iv(in); x -= kairn::unverified(iv(in + 2)); put(out, x))
FORM(mul_times, put(out, AS(upward_mul_1, iv(in)) * iv(in + 2)))
FORM(mul_times_assign, I<T> x = iv(in); x *= AS(upward_mul_1, iv(in + 2)); put(out, x))
FORM(mul_marked, put(out, kairn::unverified(iv(in)) * iv(in + 2)))
FORM(mul_marked_assign, I<T> x = iv(in); x *= kairn::unverified(iv(in + 2)); put(out, x))
FORM(neg_negate, put(out, -AS(upward_neg_1, iv(in))))
FORM(neg_marked, put(out, -kairn::unverified(iv(in))))
FORM(add_num_plus, put(out, AS(upward_add_num_1, iv(in)) + in[2]))
FORM(add_num_number_plus, put(out, in[2] + AS(upward_add_num_1, iv(in))))
FORM(add_num_plus_assign, I<T> x = iv(in); x += AS(upward_add_num_1, in[2]); put(out, x))
FORM(add_num_minus, put(out, AS(upward_add_num_1, iv(in)) - T(-in[2])))
FORM(add_num_minus_assign, I<T> x = iv(in); x -= AS(upward_add_num_1, T(-in[2])); put(out, x))
FORM(add_num_number_minus, const I<T> d = T(-in[2]) - AS_BOTH(upward_add_num_1, upward_neg_1, iv(in));
     put(out, -AS(upward_neg_1, d)))
FORM(add_num_marked, put(out, kairn::unverified(iv(in)) + in[2]))
FORM(add_num_marked_number, put(out, iv(in) + kairn::unverified(in[2])))
FORM(mul_num_times, put(out, AS(upward_mul_num_1, iv(in)) * in[2]))
FORM(mul_num_number_times, put(out, in[2] * AS(upward_mul_num_1, iv(in))))
FORM(mul_num_times_assign, I<T> x = iv(in); x *= AS(upward_mul_num_1, in[2]); put(out, x))
FORM(mul_num_marked, put(out, kairn::unverified(iv(in)) * in[2]))
FORM(mul_num_marked_number, put(out, iv(in) * kairn::unverified(in[2])))

// The exact operations.
FORM(hull_hull, put(out, iv(in).hull(AS(upward_hull_1, iv(in + 2)))))
FORM(hull_marked, put(out, iv(in).hull(kairn::unverified(iv(in + 2)))))
FORM(intersection_intersection, put(out, iv(in).intersection(AS(upward_intersection_1, iv(in + 2)))))
FORM(intersection_marked, put(out, iv(in).intersection(kairn::unverified(iv(in + 2)))))
FORM(make_constructor, put(out, I<T>(AS(upward_make_1, in[0]), in[1])))
FORM(make_from_bounds, put(out, I<T>::from_bounds(AS(upward_make_1, in[0]), in[1])))
FORM(make_marked, put(out, I<T>(kairn::unverified(in[0]), in[1])))
FORM(make_from_bounds_marked, put(out, I<T>::from_bounds(kairn::unverified(in[0]), in[1])))
// The interval of a point: on a line whose bounds are one value (the same bits, or two NaN).
template <class T>
bool one_value(const T* in) {
    return same_value(in[0], in[1]) || (in[0] != in[0] && in[1] != in[1]);
}
FORM(make_point, if (!one_value(in)) { put(out, I<T>(AS(upward_make_1, in[0]), in[1])); return; } ++reached;
     put(out, I<T>(AS(upward_make_1, in[0]))))
FORM(from_interval_convert, put(out, I<T>(AS(upward_from_interval_1, D<T>::from_bounds(in[0], in[1])))))
FORM(from_interval_marked, put(out, I<T>(kairn::unverified(D<T>::from_bounds(in[0], in[1])))))
FORM(to_interval_to_interval, put(out, AS(upward_to_interval_1, iv(in)).to_interval()))
FORM(to_interval_marked, put(out, kairn::unverified(iv(in)).to_interval()))
FORM(to_interval_bounds, const I<T> x = iv(in); out[0] = AS(upward_to_interval_1, x).lower();
     out[1] = AS(upward_to_interval_1, x).upper())
FORM(to_interval_bounds_marked, const I<T> x = iv(in); out[0] = kairn::unverified(x).lower();
     out[1] = kairn::unverified(x).upper())
FORM(empty_is_empty, mo[0] = AS(upward_empty_1, iv(in)).is_empty())
FORM(empty_marked, mo[0] = kairn::unverified(iv(in)).is_empty())
FORM(entire_is_whole, mo[0] = AS(upward_entire_1, iv(in)).is_whole())
FORM(entire_marked, mo[0] = kairn::unverified(iv(in)).is_whole())
FORM(positive_certainly_positive, mo[0] = AS(upward_positive_1, iv(in)).certainly_positive())
FORM(positive_marked, mo[0] = kairn::unverified(iv(in)).certainly_positive())
FORM(negative_certainly_negative, mo[0] = AS(upward_negative_1, iv(in)).certainly_negative())
FORM(negative_marked, mo[0] = kairn::unverified(iv(in)).certainly_negative())
FORM(zero_certainly_zero, mo[0] = AS(upward_zero_1, iv(in)).certainly_zero())
FORM(zero_marked, mo[0] = kairn::unverified(iv(in)).certainly_zero())
FORM(contains_contains, mo[0] = iv(in).contains(AS(upward_contains_1, in[2])))
FORM(contains_marked, mo[0] = iv(in).contains(kairn::unverified(in[2])))
FORM(contains_member, mo[0] = known_yes(up::member(AS(upward_contains_1, in[2]), iv(in))))
FORM(contains_member_marked, mo[0] = known_yes(up::member(in[2], kairn::unverified(iv(in)))))
// upward_subset_1(x, y): x a subset of y, which is y.contains(x).
FORM(subset_contains, mo[0] = iv(in + 2).contains(AS(upward_subset_1, iv(in))))
FORM(subset_contains_marked, mo[0] = iv(in + 2).contains(kairn::unverified(iv(in))))
FORM(subset_ieee1788_subset, mo[0] = up::ieee1788::subset(AS(upward_subset_1, iv(in)), iv(in + 2)))
FORM(subset_ieee1788_marked, mo[0] = up::ieee1788::subset(iv(in), kairn::unverified(iv(in + 2))))
FORM(less_less, put_trit(mo, up::less(AS(upward_less_1, iv(in)), iv(in + 2))))
FORM(less_greater, put_trit(mo, up::greater(iv(in + 2), AS(upward_less_1, iv(in)))))
FORM(less_marked, put_trit(mo, up::less(iv(in), kairn::unverified(iv(in + 2)))))
FORM(less_equal_less_equal, put_trit(mo, up::less_equal(AS(upward_less_equal_1, iv(in)), iv(in + 2))))
FORM(less_equal_greater_equal, put_trit(mo, up::greater_equal(iv(in + 2), AS(upward_less_equal_1, iv(in)))))
FORM(less_equal_marked, put_trit(mo, up::less_equal(kairn::unverified(iv(in)), iv(in + 2))))
FORM(equal_equal, put_trit(mo, up::equal(AS(upward_equal_1, iv(in)), iv(in + 2))))
FORM(equal_not_equal, put_opposite(mo, up::not_equal(AS(upward_equal_1, iv(in)), iv(in + 2))))
FORM(equal_marked, put_trit(mo, up::equal(iv(in), kairn::unverified(iv(in + 2)))))
FORM(rel_equal_ieee1788_equal, mo[0] = up::ieee1788::equal(AS(upward_rel_equal_1, iv(in)), iv(in + 2)))
FORM(rel_equal_marked, mo[0] = up::ieee1788::equal(kairn::unverified(iv(in)), iv(in + 2)))
FORM(rel_interior_ieee1788_interior, mo[0] = up::ieee1788::interior(AS(upward_rel_interior_1, iv(in)), iv(in + 2)))
FORM(rel_interior_marked, mo[0] = up::ieee1788::interior(iv(in), kairn::unverified(iv(in + 2))))
FORM(rel_disjoint_ieee1788_disjoint, mo[0] = up::ieee1788::disjoint(AS(upward_rel_disjoint_1, iv(in)), iv(in + 2)))
FORM(rel_disjoint_marked, mo[0] = up::ieee1788::disjoint(kairn::unverified(iv(in)), iv(in + 2)))
#undef FORM

struct Form {
    const char* kernel;
    const char* name;
    const char* in_kinds;  // one letter per input value: l a limb
    const char* out_kinds; // l a limb, m a mask
    bool conditional;      // computes its own operation on some lines only
    void (*binary64)(const double*, double*, bool*);
    void (*binary32)(const float*, float*, bool*);
};
#define ROW(KERNEL, SHORT, NAME, IN, OUT) {#KERNEL, #NAME, IN, OUT, false, SHORT##_##NAME<double>, SHORT##_##NAME<float>},
#define SOME(KERNEL, SHORT, NAME, IN, OUT) {#KERNEL, #NAME, IN, OUT, true, SHORT##_##NAME<double>, SHORT##_##NAME<float>},

// The first form of each kernel is its canonical one.
const Form forms[] = {
    ROW(upward_add_1, add, plus, "llll", "ll")
    ROW(upward_add_1, add, plus_assign, "llll", "ll")
    ROW(upward_add_1, add, marked, "llll", "ll")
    ROW(upward_add_1, add, marked_assign, "llll", "ll")
    ROW(upward_sub_1, sub, minus, "llll", "ll")
    ROW(upward_sub_1, sub, minus_assign, "llll", "ll")
    ROW(upward_sub_1, sub, marked, "llll", "ll")
    ROW(upward_sub_1, sub, marked_assign, "llll", "ll")
    ROW(upward_mul_1, mul, times, "llll", "ll")
    ROW(upward_mul_1, mul, times_assign, "llll", "ll")
    ROW(upward_mul_1, mul, marked, "llll", "ll")
    ROW(upward_mul_1, mul, marked_assign, "llll", "ll")
    ROW(upward_neg_1, neg, negate, "ll", "ll")
    ROW(upward_neg_1, neg, marked, "ll", "ll")
    ROW(upward_add_num_1, add_num, plus, "lll", "ll")
    ROW(upward_add_num_1, add_num, number_plus, "lll", "ll")
    ROW(upward_add_num_1, add_num, plus_assign, "lll", "ll")
    ROW(upward_add_num_1, add_num, minus, "lll", "ll")
    ROW(upward_add_num_1, add_num, minus_assign, "lll", "ll")
    ROW(upward_add_num_1, add_num, number_minus, "lll", "ll")
    ROW(upward_add_num_1, add_num, marked, "lll", "ll")
    ROW(upward_add_num_1, add_num, marked_number, "lll", "ll")
    ROW(upward_mul_num_1, mul_num, times, "lll", "ll")
    ROW(upward_mul_num_1, mul_num, number_times, "lll", "ll")
    ROW(upward_mul_num_1, mul_num, times_assign, "lll", "ll")
    ROW(upward_mul_num_1, mul_num, marked, "lll", "ll")
    ROW(upward_mul_num_1, mul_num, marked_number, "lll", "ll")
    ROW(upward_hull_1, hull, hull, "llll", "ll")
    ROW(upward_hull_1, hull, marked, "llll", "ll")
    ROW(upward_intersection_1, intersection, intersection, "llll", "ll")
    ROW(upward_intersection_1, intersection, marked, "llll", "ll")
    ROW(upward_make_1, make, constructor, "ll", "ll")
    ROW(upward_make_1, make, from_bounds, "ll", "ll")
    ROW(upward_make_1, make, marked, "ll", "ll")
    ROW(upward_make_1, make, from_bounds_marked, "ll", "ll")
    SOME(upward_make_1, make, point, "ll", "ll")
    ROW(upward_from_interval_1, from_interval, convert, "ll", "ll")
    ROW(upward_from_interval_1, from_interval, marked, "ll", "ll")
    ROW(upward_to_interval_1, to_interval, to_interval, "ll", "ll")
    ROW(upward_to_interval_1, to_interval, marked, "ll", "ll")
    ROW(upward_to_interval_1, to_interval, bounds, "ll", "ll")
    ROW(upward_to_interval_1, to_interval, bounds_marked, "ll", "ll")
    ROW(upward_empty_1, empty, is_empty, "ll", "m")
    ROW(upward_empty_1, empty, marked, "ll", "m")
    ROW(upward_entire_1, entire, is_whole, "ll", "m")
    ROW(upward_entire_1, entire, marked, "ll", "m")
    ROW(upward_positive_1, positive, certainly_positive, "ll", "m")
    ROW(upward_positive_1, positive, marked, "ll", "m")
    ROW(upward_negative_1, negative, certainly_negative, "ll", "m")
    ROW(upward_negative_1, negative, marked, "ll", "m")
    ROW(upward_zero_1, zero, certainly_zero, "ll", "m")
    ROW(upward_zero_1, zero, marked, "ll", "m")
    ROW(upward_contains_1, contains, contains, "lll", "m")
    ROW(upward_contains_1, contains, marked, "lll", "m")
    ROW(upward_contains_1, contains, member, "lll", "m")
    ROW(upward_contains_1, contains, member_marked, "lll", "m")
    ROW(upward_subset_1, subset, contains, "llll", "m")
    ROW(upward_subset_1, subset, contains_marked, "llll", "m")
    ROW(upward_subset_1, subset, ieee1788_subset, "llll", "m")
    ROW(upward_subset_1, subset, ieee1788_marked, "llll", "m")
    ROW(upward_less_1, less, less, "llll", "mm")
    ROW(upward_less_1, less, greater, "llll", "mm")
    ROW(upward_less_1, less, marked, "llll", "mm")
    ROW(upward_less_equal_1, less_equal, less_equal, "llll", "mm")
    ROW(upward_less_equal_1, less_equal, greater_equal, "llll", "mm")
    ROW(upward_less_equal_1, less_equal, marked, "llll", "mm")
    ROW(upward_equal_1, equal, equal, "llll", "mm")
    ROW(upward_equal_1, equal, not_equal, "llll", "mm")
    ROW(upward_equal_1, equal, marked, "llll", "mm")
    ROW(upward_rel_equal_1, rel_equal, ieee1788_equal, "llll", "m")
    ROW(upward_rel_equal_1, rel_equal, marked, "llll", "m")
    ROW(upward_rel_interior_1, rel_interior, ieee1788_interior, "llll", "m")
    ROW(upward_rel_interior_1, rel_interior, marked, "llll", "m")
    ROW(upward_rel_disjoint_1, rel_disjoint, ieee1788_disjoint, "llll", "m")
    ROW(upward_rel_disjoint_1, rel_disjoint, marked, "llll", "m")
};
#undef ROW
#undef SOME

// --- The forms of the functions on arrays -----------------------------------------------------------

constexpr std::size_t block = 17;

// A block of lines of one format: the inputs of each line (in[i]) and where its outputs go.
template <class T>
struct Block {
    std::size_t n = 0;
    const T* in[block] = {};
    T* out[block] = {};
};

enum class Array { add, sub, mul, neg, add_number, mul_number };

// The views of the block's first (and second) operand, element i the state of line i.
template <class T>
struct Operands {
    T xu[block] = {}, xn[block] = {}, yu[block] = {}, yn[block] = {};
    explicit Operands(const Block<T>& b) {
        for (std::size_t i = 0; i < b.n; ++i) {
            xu[i] = b.in[i][0];
            xn[i] = b.in[i][1];
            yu[i] = b.in[i][2];
            yn[i] = b.in[i][3];
        }
    }
};

// z = op(x, y) or op(x) through the public function, with the marker when the kernel is not proved.
template <class T>
void call(Array op, up::View<T> z, up::View<const T> x, up::View<const T> y, T t) {
    switch (op) {
    case Array::add:
        up::add(z, AS(upward_add_1, x), y);
        break;
    case Array::sub:
        up::sub(z, AS(upward_sub_1, x), y);
        break;
    case Array::mul:
        up::mul(z, AS(upward_mul_1, x), y);
        break;
    case Array::neg:
        up::neg(z, AS(upward_neg_1, x));
        break;
    case Array::add_number:
        up::add(z, AS(upward_add_num_1, x), t);
        break;
    case Array::mul_number:
        up::mul(z, AS(upward_mul_num_1, x), t);
        break;
    }
}

// arrays: from code that rounds to nearest; arrays_inplace: inside a Scope, z the first view read.
template <class T>
void complete_block(Array op, bool inplace, const Block<T>& b) {
    const Operands<T> v(b);
    const std::size_t n = b.n;
    const up::View<const T> y(v.yu, v.yn, n);
    T zu[block] = {}, zn[block] = {};
    const auto run = [&](T t) {
        if (inplace) {
            std::memcpy(zu, v.xu, sizeof zu);
            std::memcpy(zn, v.xn, sizeof zn);
            const up::View<T> z(zu, zn, n);
            up::Scope s;
            call<T>(op, z, z, y, t);
        } else {
            call<T>(op, up::View<T>(zu, zn, n), up::View<const T>(v.xu, v.xn, n), y, t);
        }
    };
    if (op == Array::add_number || op == Array::mul_number) {
        // One number per call: line i's number, and line i's element.
        for (std::size_t i = 0; i < n; ++i) {
            run(b.in[i][2]);
            b.out[i][0] = zu[i];
            b.out[i][1] = zn[i];
        }
    } else {
        run(T(0));
        for (std::size_t i = 0; i < n; ++i) {
            b.out[i][0] = zu[i];
            b.out[i][1] = zn[i];
        }
    }
}

struct ArrayForm {
    const char* kernel;
    const char* name;
    const char* in_kinds;
    Array op;
    bool inplace;
};
const ArrayForm array_forms[] = {
    {"upward_add_1", "arrays", "llll", Array::add, false},
    {"upward_add_1", "arrays_inplace", "llll", Array::add, true},
    {"upward_sub_1", "arrays", "llll", Array::sub, false},
    {"upward_sub_1", "arrays_inplace", "llll", Array::sub, true},
    {"upward_mul_1", "arrays", "llll", Array::mul, false},
    {"upward_mul_1", "arrays_inplace", "llll", Array::mul, true},
    {"upward_neg_1", "arrays", "ll", Array::neg, false},
    {"upward_neg_1", "arrays_inplace", "ll", Array::neg, true},
    {"upward_add_num_1", "arrays", "lll", Array::add_number, false},
    {"upward_add_num_1", "arrays_inplace", "lll", Array::add_number, true},
    {"upward_mul_num_1", "arrays", "lll", Array::mul_number, false},
    {"upward_mul_num_1", "arrays_inplace", "lll", Array::mul_number, true},
};

// --- The protocol -----------------------------------------------------------------------------------

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

// One line of the stream, held until its end.
struct Line {
    std::string text;
    bool request = false;
    bool binary64 = true;
    const char* out_kinds = "";
    double in64[max_limbs] = {};
    float in32[max_limbs] = {};
    double out64[max_limbs] = {};
    float out32[max_limbs] = {};
    bool mo[max_limbs] = {};
};

int usage() {
    std::fprintf(stderr, "usage: runner [--form NAME] | --forms KERNEL | --list | --self-test\n");
    return 2;
}

// kairn::upward::self_test() as built here.
int self_test() {
    const kairn::Status s = up::self_test();
    std::printf("kairn::upward::self_test: %s%s%s\nlimitation: %s\nKAIRN_CHECKS: %d\n", s.message(),
                s.kernel ? ": " : "", s.kernel ? s.kernel : "", s.limitation ? s.limitation : "none", KAIRN_CHECKS);
    return s.ok() ? 0 : 1;
}

}  // namespace

int main(int argc, char** argv) {
    kairn_test::no_crash_reports();
    if (argc == 2 && std::strcmp(argv[1], "--self-test") == 0) return self_test();
    if (argc == 3 && std::strcmp(argv[1], "--forms") == 0) {
        for (const Form& f : forms)
            if (std::strcmp(f.kernel, argv[2]) == 0) std::printf("%s\n", f.name);
        for (const ArrayForm& f : array_forms)
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
    const char* form_name = nullptr;
    if (argc == 3 && std::strcmp(argv[1], "--form") == 0) {
        form_name = argv[2];
    } else if (argc != 1) {
        return usage();
    }

    std::ios::sync_with_stdio(false);
    std::vector<Line> lines;
    std::string text;
    std::vector<std::string> fields;
    const Form* conditional = nullptr;
    const ArrayForm* array_form = nullptr;
    long requests = 0;
    while (std::getline(std::cin, text)) {
        ++lineno;
        if (!text.empty() && text.back() == '\r') text.pop_back();
        lines.emplace_back();
        Line& line = lines.back();
        line.text = text;
        if (text.empty() || text[0] == '#') continue;
        fields.clear();
        for (std::size_t start = 0;;) {
            const std::size_t space = text.find(' ', start);
            fields.push_back(text.substr(start, space - start));
            if (fields.back().empty()) fail("fields are separated by single spaces");
            if (space == std::string::npos) break;
            start = space + 1;
        }
        if (fields.back()[0] == '#') fields.pop_back();  // the tag
        if (fields.size() < 2) fail("expected KERNEL FORMAT LIMB ... [#TAG]");
        const Form* k = nullptr;
        const ArrayForm* a = nullptr;
        for (const Form& f : forms) {
            if (fields[0] != f.kernel) continue;
            if (form_name ? std::strcmp(form_name, f.name) == 0 : k == nullptr) k = &f;
        }
        if (!k && form_name)
            for (const ArrayForm& f : array_forms)
                if (fields[0] == f.kernel && std::strcmp(form_name, f.name) == 0) a = &f;
        if (!k && !a)
            fail("no public operation maps to " + fields[0] + (form_name ? std::string(" as form ") + form_name : ""));
        if (a) {
            if (array_form && array_form != a) fail("a stream of a form of the functions on arrays has one kernel");
            array_form = a;
        }
        const char* in_kinds = k ? k->in_kinds : a->in_kinds;
        const int inputs = int(std::strlen(in_kinds));
        if (int(fields.size()) - 2 != inputs) fail(fields[0] + " takes " + std::to_string(inputs) + " limbs");
        if (fields[1] != "binary64" && fields[1] != "binary32")
            fail("this runner knows binary64 and binary32, not " + fields[1]);
        line.request = true;
        line.binary64 = fields[1] == "binary64";
        line.out_kinds = k ? k->out_kinds : "ll";
        for (int i = 0; i < inputs; ++i) {
            const double v = parse(fields[2 + i]);
            line.in64[i] = v;
            if (!line.binary64) {
                const double top = std::numeric_limits<float>::max();
                if (v == v && v - v == 0 && (v > top || v < -top)) fail(fields[2 + i] + " is not a binary32 number");
                line.in32[i] = static_cast<float>(v);
                if (static_cast<double>(line.in32[i]) != v && v == v) fail(fields[2 + i] + " is not a binary32 number");
            }
        }
        ++requests;
        if (k) {
            if (k->conditional) conditional = k;
            // The evaluation, inside a scope; the numbers cross it through memory.
            up::Scope s;
            if (line.binary64) {
                k->binary64(line.in64, line.out64, line.mo);
            } else {
                k->binary32(line.in32, line.out32, line.mo);
            }
        }
    }
    // The lines of a form of the functions on arrays, in blocks of each format, in their order.
    if (array_form) {
        Block<double> b64;
        Block<float> b32;
        const auto flush64 = [&] {
            if (b64.n) complete_block<double>(array_form->op, array_form->inplace, b64);
            b64 = Block<double>{};
        };
        const auto flush32 = [&] {
            if (b32.n) complete_block<float>(array_form->op, array_form->inplace, b32);
            b32 = Block<float>{};
        };
        for (Line& line : lines) {
            if (!line.request) continue;
            if (line.binary64) {
                b64.in[b64.n] = line.in64;
                b64.out[b64.n] = line.out64;
                if (++b64.n == block) flush64();
            } else {
                b32.in[b32.n] = line.in32;
                b32.out[b32.n] = line.out32;
                if (++b32.n == block) flush32();
            }
        }
        flush64();
        flush32();
    }
    std::string out;
    for (const Line& line : lines) {
        out = line.text;
        if (line.request) {
            out += " ->";
            const int outputs = int(std::strlen(line.out_kinds));
            for (int i = 0; i < outputs; ++i) {
                out += ' ';
                if (line.out_kinds[i] == 'm') out += line.mo[i] ? '1' : '0';
                else put_limb(line.binary64 ? line.out64[i] : static_cast<double>(line.out32[i]), out);
            }
        }
        out += '\n';
        std::fwrite(out.data(), 1, out.size(), stdout);
    }
    if (conditional) {
        std::fprintf(stderr, "runner: form %s of %s computed its own operation on %ld of %ld lines\n", conditional->name,
                     conditional->kernel, reached, requests);
        if (requests >= 1000 && reached == 0) {
            std::fprintf(stderr, "runner: form %s of %s computed its own operation on none of %ld lines\n",
                         conditional->name, conditional->kernel, requests);
            return 3;
        }
    }
    return 0;
}
