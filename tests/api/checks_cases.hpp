// The cases that tests/api/checks.cpp and tests/api/checks_handler.cpp share: the operands, every
// public function of the headers, written as a program writes it, each with whether the checks of
// KAIRN_CHECKS check the rounding mode before it, and the states of the floating-point environment
// this target can set. A program that defines KAIRN_ENVIRONMENT_FAILURE does so before including
// this file.
#pragma once

#include <kairn/accumulator.hpp>
#include <kairn/batch.hpp>
#include <kairn/kairn.hpp>
#include <kairn/packed.hpp>
#include <kairn/soa.hpp>
#include <kairn/ball_vector.hpp>

#include <array>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <type_traits>
#include <vector>

#if defined(__x86_64__) || defined(_M_X64)
#include <xmmintrin.h>
#endif

namespace kairn_test {

using E1 = kairn::Expansion<double, 1>;
using E2 = kairn::Expansion<double, 2>;
using F2 = kairn::Expansion<float, 2>;
using B1 = kairn::Ball<double, 1>;
using B2 = kairn::Ball<double, 2>;
using I1 = kairn::Interval<double, 1>;
using I2 = kairn::Interval<double, 2>;
using kairn::unverified;

// Operands read from volatile objects, so that nothing is computed before the program asks. The
// two-limb ones are canonical pairs whose test, x0 + x1 == x0, is false under a directed rounding
// mode: (1.5, 2^-60) under rounding upward, (2.25, -2^-58) under rounding downward and toward
// zero.
inline volatile double v_a = 1.5, v_b = 0x1p-60, v_c = 2.25, v_d = -0x1p-58, v_r = 0x1p-20;
inline volatile float v_fa = 1.5f, v_fb = 0x1p-30f;
inline volatile double sink = 0;
inline constexpr double infinity = std::numeric_limits<double>::infinity();
inline constexpr double not_a_number = std::numeric_limits<double>::quiet_NaN();

inline E2 pair(double h, double l) {
    const double limbs[2] = {h, l};
    return E2::from_limbs(limbs);
}
// A pair whose limbs are written directly: the only way to make one that is not canonical, or a
// canonical one with a limb -0, which the constructors' guard makes +0.
template <class T = double>
inline kairn::Expansion<T, 2> raw(T h, T l) {
    kairn::Expansion<T, 2> x;
    x.limb[0] = h;
    x.limb[1] = l;
    return x;
}
// The operands of the operations, made in the default environment before any state is set, so
// that each operation below is what meets the state; the constructors meet it in cases of their
// own.
struct Operands {
    E2 x, y;
    F2 fx;
    B1 p, q;
    B2 bp, bq;
    I1 ix, iy;
    I2 jx, jy;
};
inline Operands o;
// Ball vectors (kairn/ball_vector.hpp) of five entries: the centers 1.5, 2.25 and the two-limb
// operands above, the radius 2^-20.
using BV1 = kairn::BallVector<double, 1, 5>;
using BV2 = kairn::BallVector<double, 2, 5>;
inline BV1 bv1x, bv1y;
inline BV2 bv2x, bv2y;

// The corpus of the functions that do not round, for one limb type: values of one limb (zeros of
// both signs, subnormal numbers, the smallest normal number, ordinary numbers, the largest finite
// number, the infinities, NaN), canonical pairs (zeros of both signs in each limb, a subnormal
// leading limb, a subnormal tail, ties of the test of a canonical pair, tails above and below the
// largest finite number, the infinities with a zero of either sign, NaN), radii, and canonical
// balls of one and two limbs, the whole line and the empty set among them. Made at run time from
// volatile objects, in the default environment, so that no function under test is evaluated
// before the program asks.
template <class T>
struct Corpus {
    std::vector<T> one, radii;
    std::vector<kairn::Expansion<T, 2>> two;
    std::vector<kairn::Ball<T, 1>> balls1;
    std::vector<kairn::Ball<T, 2>> balls2;
    // The results of two_sum on every pair of finite values of one, and on two NaN: what converts
    // to Expansion<T, 2>.
    std::vector<kairn::SumAndError<T>> sums;
    // Canonical intervals: those that the constructors make of the pairs of values of one, and of
    // two (a NaN bound gives the whole line, reversed ones the empty set), each once.
    std::vector<kairn::Interval<T, 1>> intervals1;
    std::vector<kairn::Interval<T, 2>> intervals2;
    // Ball vectors of five entries: five consecutive values of one (with wrap-around) with each
    // radius, and five consecutive finite pairs of two with each radius, as the constructor makes
    // them (the whole space of a radius +inf or a NaN, or of a center that is not finite).
    std::vector<kairn::BallVector<T, 1, 5>> bvs1;
    std::vector<kairn::BallVector<T, 2, 5>> bvs2;
};
template <class T>
inline T opaque(T x) {
    volatile T v = x;
    return v;
}
template <class T>
inline Corpus<T> make_corpus() {
    using L = std::numeric_limits<T>;
    const T eta = opaque(L::denorm_min()), lambda = opaque((L::min)()), big = opaque((L::max)());
    const T inf = opaque(L::infinity()), nan = opaque(L::quiet_NaN()), u = opaque(L::epsilon() / 2);
    const T sub = lambda * T(0.75);                               // a subnormal number of two bits
    const T top = std::ldexp(T(1), L::max_exponent - L::digits - 2);  // a quarter of the gap at big
    const T one = opaque(T(1));
    Corpus<T> c;
    c.one = {T(0), -T(0), eta, -eta, sub, -sub, lambda, -lambda, one, -one, T(1.5), T(-2.25), big, -big, inf, -inf, nan};
    c.radii = {T(0), -T(0), eta, sub, u, one, big, inf, nan};
    c.two = {raw<T>(0, 0), raw<T>(-T(0), -T(0)), raw<T>(0, -T(0)), raw<T>(-T(0), 0), raw<T>(eta, 0),
             raw<T>(-eta, -T(0)), raw<T>(lambda, 0), raw<T>(one, eta), raw<T>(one, -eta), raw<T>(-one, eta),
             raw<T>(one, u), raw<T>(one, -u / 2), raw<T>(-one, u / 2), raw<T>(T(1.5), u / 128),
             raw<T>(T(2.25), -u / 32), raw<T>(T(-1.5), -u / 128), raw<T>(big, top), raw<T>(big, -top),
             raw<T>(-big, top), raw<T>(inf, 0), raw<T>(-inf, 0), raw<T>(inf, -T(0)), raw<T>(nan, nan)};
    const T finite_radii[] = {T(0), eta, u, one, big};
    for (T center : {T(0), eta, lambda, T(1.5), T(-2.25), big, -big})
        for (T r : finite_radii) c.balls1.push_back(kairn::Ball<T, 1>(unverified(kairn::Expansion<T, 1>(center)), r));
    // A center -0, which the constructor's guard would make +0.
    c.balls1.push_back(kairn::Ball<T, 1>(kairn::detail::kernel_result, kairn::Expansion<T, 1>(-T(0)), one));
    c.balls1.push_back(kairn::Ball<T, 1>::whole());
    c.balls1.push_back(kairn::Ball<T, 1>::empty());
    for (const auto& center : c.two)
        if (kairn::isfinite(center))
            for (T r : finite_radii) c.balls2.push_back(kairn::Ball<T, 2>(unverified(center), r));
    c.balls2.push_back(kairn::Ball<T, 2>::whole());
    c.balls2.push_back(kairn::Ball<T, 2>::empty());
    for (T a : c.one)
        for (T b : c.one) {
            if (!std::isfinite(a) || !std::isfinite(b)) continue;
            const kairn::SumAndError<T> r = kairn::two_sum(a, b);
            if (std::isfinite(r.sum) && std::isfinite(r.error)) c.sums.push_back(r);
        }
    c.sums.push_back(kairn::two_sum(nan, nan));
    // The intervals: every pair of bounds of the corpus that is not a NaN and that the constructor
    // does not make the empty set (it keeps their bounds as they are, but the same infinity twice,
    // which it makes the whole line), then the empty set and the whole line once each.
    for (T lo : c.one)
        for (T hi : c.one) {
            if (lo != lo || hi != hi) continue;
            const kairn::Interval<T, 1> x(unverified(lo), hi);
            if (x.lower().limb[0] != inf) c.intervals1.push_back(x);
        }
    c.intervals1.push_back(kairn::Interval<T, 1>::empty());
    c.intervals1.push_back(kairn::Interval<T, 1>::whole());
    for (const auto& lo : c.two)
        for (const auto& hi : c.two) {
            if (lo.limb[0] != lo.limb[0] || hi.limb[0] != hi.limb[0]) continue;
            const kairn::Interval<T, 2> x(unverified(lo), hi);
            if (x.lower().limb[0] != inf) c.intervals2.push_back(x);
        }
    c.intervals2.push_back(kairn::Interval<T, 2>::empty());
    c.intervals2.push_back(kairn::Interval<T, 2>::whole());
    std::vector<kairn::Expansion<T, 2>> pairs;
    for (const auto& x : c.two)
        if (kairn::isfinite(x)) pairs.push_back(x);
    for (std::size_t k = 0; k < c.one.size(); ++k)
        for (T r : c.radii) {
            std::array<kairn::Expansion<T, 1>, 5> one5;
            for (std::size_t i = 0; i < 5; ++i) one5[i] = kairn::Expansion<T, 1>(c.one[(k + i) % c.one.size()]);
            c.bvs1.push_back(kairn::BallVector<T, 1, 5>(one5, r));
        }
    for (std::size_t k = 0; k < pairs.size(); ++k)
        for (T r : c.radii) {
            std::array<kairn::Expansion<T, 2>, 5> two5;
            for (std::size_t i = 0; i < 5; ++i) two5[i] = pairs[(k + i) % pairs.size()];
            c.bvs2.push_back(kairn::BallVector<T, 2, 5>(two5, r));
        }
    return c;
}
inline Corpus<double> corpus_d;
inline Corpus<float> corpus_f;

inline void make_operands() {
    const float limbs[2] = {v_fa, v_fb};
    o.x = pair(v_a, v_b);
    o.y = pair(v_c, v_d);
    o.fx = F2::from_limbs(limbs);
    o.p = B1(unverified(E1(v_a)), v_r);
    o.q = B1(unverified(E1(v_c)), v_r);
    o.bp = B2(unverified(o.x), v_r);
    o.bq = B2(unverified(o.y), v_r);
    o.ix = I1(unverified(double(v_b)), v_a);
    o.iy = I1(unverified(double(v_a)), v_c);
    o.jx = I2(unverified(o.y), o.y);
    o.jy = I2(unverified(o.x), o.y);
    bv1x = BV1({E1(v_a), E1(v_c), E1(-v_a), E1(v_b), E1(v_c)}, v_r);
    bv1y = BV1({E1(v_c), E1(v_a), E1(v_d), E1(v_a), E1(-v_c)}, v_r);
    bv2x = BV2({o.x, o.y, o.x, o.y, o.x}, v_r);
    bv2y = BV2({o.y, o.x, o.y, o.x, o.y}, v_r);
    corpus_d = make_corpus<double>();
    corpus_f = make_corpus<float>();
}
template <class T>
inline const Corpus<T>& corpus() {
    if constexpr (sizeof(T) == 8) {
        return corpus_d;
    } else {
        return corpus_f;
    }
}

// The results of a function, as bit patterns: what must be the same under every rounding mode.
using Bits = std::vector<std::uint64_t>;
template <class T>
inline void put(Bits& out, T x) {
    if constexpr (sizeof(T) == 8) {
        out.push_back(std::bit_cast<std::uint64_t>(x));
    } else {
        out.push_back(std::bit_cast<std::uint32_t>(x));
    }
}
inline void put(Bits& out, bool b) { out.push_back(b ? 1 : 0); }
template <class T>
inline void put(Bits& out, const kairn::SumAndError<T>& r) {
    put(out, r.sum);
    put(out, r.error);
}
template <class T>
inline void put(Bits& out, const kairn::ProductAndError<T>& r) {
    put(out, r.product);
    put(out, r.error);
}
inline void put(Bits& out, int i) { out.push_back(std::uint64_t(std::int64_t(i))); }
template <class T, int K>
inline void put(Bits& out, const kairn::Expansion<T, K>& x) {
    for (int i = 0; i < K; ++i) put(out, x.limb[i]);
}
template <class T, int K>
inline void put(Bits& out, const kairn::Ball<T, K>& b) {
    put(out, b.center());
    put(out, b.radius());
}
template <class T, int K>
inline void put(Bits& out, const kairn::Interval<T, K>& x) {
    put(out, x.lower());
    put(out, x.upper());
}
template <class X>
inline void put(Bits& out, const kairn::Split<X>& s) {
    put(out, s.left);
    put(out, s.right);
}
template <class T, int K, std::size_t N>
inline void put(Bits& out, const kairn::BallVector<T, K, N>& x) {
    for (std::size_t i = 0; i < N; ++i) put(out, x.center(i));
    put(out, x.radius());
}
template <class T, int K>
inline void put(Bits& out, const kairn::BallVectorView<T, K>& x) {
    for (std::size_t i = 0; i < x.size(); ++i) put(out, x.center(i));
    put(out, x.radius());
}
// The value, a zero without its sign: what a constructor must keep under every rounding mode (its
// guard, a + 0, gives -0 + 0 = -0 when rounding downward and +0 otherwise). Decided on the bit
// pattern of a copy read back from memory, never as x == 0 ? 0 : x in floating point: that rule
// runs under the directed mode, and a compiler that assumes rounding to nearest, as /fp:precise
// lets MSVC, may drop it where x is a guard's a + 0, which is never -0 to nearest, or compute it
// as x + 0, which keeps a -0 when rounding downward. With MSVC 19.51 at /O2 (the hosted runner of
// 2026-11-20) the results of a -0 given to a constructor differed between rounding downward and to
// nearest after that rule, and only there: the rule did not normalize the guard's -0 (MSVC 19.52
// compiles it as a comparison and a blend, which do).
template <class T>
inline void put_value(Bits& out, T x) {
    using U = std::conditional_t<sizeof(T) == 8, std::uint64_t, std::uint32_t>;
    const U u = std::bit_cast<U>(opaque(x));
    out.push_back(U(u << 1) == 0 ? 0 : u);  // every bit but the sign zero: either zero, as +0
}
template <class T, int K>
inline void put_value(Bits& out, const kairn::Expansion<T, K>& x) {
    for (int i = 0; i < K; ++i) put_value(out, x.limb[i]);
}
template <class T, int K>
inline void put_value(Bits& out, const kairn::Ball<T, K>& b) {
    put_value(out, b.center());
    put_value(out, b.radius());
}
template <class T, int K>
inline void put_value(Bits& out, const kairn::Interval<T, K>& x) {
    put_value(out, x.lower());
    put_value(out, x.upper());
}
template <class X>
inline void put_value_bv(Bits& out, const X& x) {
    for (std::size_t i = 0; i < x.size(); ++i) put_value(out, x.center(i));
    put_value(out, x.radius());
}

// Packed numbers (kairn/packed.hpp): the results of every lane, and the values of a corpus W at a
// time, the last register filled with the first value.
template <class T, int K>
inline void put(Bits& out, const kairn::Packed<T, K>& p) {
    for (int i = 0; i < kairn::Packed<T, K>::lanes; ++i) put(out, p.lane(i));
}
template <class T>
inline void put(Bits& out, const kairn::PackedMask<T>& m) {
    for (int i = 0; i < kairn::PackedMask<T>::lanes; ++i) put(out, m.lane(i));
}
template <class T, int K>
inline void put_value(Bits& out, const kairn::Packed<T, K>& p) {
    for (int i = 0; i < kairn::Packed<T, K>::lanes; ++i) put_value(out, p.lane(i));
}
template <class T>
inline std::vector<kairn::Packed<T, 1>> pack(const std::vector<T>& values) {
    constexpr int w = kairn::Packed<T, 1>::lanes;
    std::vector<kairn::Packed<T, 1>> r;
    for (std::size_t i = 0; i < values.size(); i += w) {
        kairn::Packed<T, 1> p;
        for (int l = 0; l < w; ++l)
            p.set_lane(l, kairn::Expansion<T, 1>(i + std::size_t(l) < values.size() ? values[i + std::size_t(l)] : values[0]));
        r.push_back(p);
    }
    return r;
}
template <class T>
inline std::vector<kairn::Packed<T, 2>> pack(const std::vector<kairn::Expansion<T, 2>>& values) {
    constexpr int w = kairn::Packed<T, 2>::lanes;
    std::vector<kairn::Packed<T, 2>> r;
    for (std::size_t i = 0; i < values.size(); i += w) {
        kairn::Packed<T, 2> p;
        for (int l = 0; l < w; ++l) p.set_lane(l, i + std::size_t(l) < values.size() ? values[i + std::size_t(l)] : values[0]);
        r.push_back(p);
    }
    return r;
}
using P1 = kairn::Packed<double, 1>;
using P2 = kairn::Packed<double, 2>;
// The limbs of a two-limb number in every element of two arrays, for the loads and the views.
struct Arrays {
    double h[16], l[16];
    explicit Arrays(const E2& x) {
        for (int i = 0; i < 16; ++i) {
            h[i] = x.limb[0];
            l[i] = x.limb[1];
        }
    }
};

// The six comparisons of a pair of operands.
template <class X, class Y>
inline void compare(Bits& out, const X& x, const Y& y) {
    put(out, x < y);
    put(out, x > y);
    put(out, x <= y);
    put(out, x >= y);
    put(out, x == y);
    put(out, x != y);
}

// For each limb type, f(corpus): the function that does not round on its whole corpus.
template <class F>
inline void for_both(Bits& out, F f) {
    f(out, corpus<double>());
    f(out, corpus<float>());
}

// Every public function, written as a program writes it, with kairn::unverified on the first
// operand where an operation needs the marker while its kernel is unverified (it changes nothing
// else). What the checks of KAIRN_CHECKS do before each (config.hpp):
// - rounds: the function rounds; the environment is checked, the rounding mode included. Each is
//   run on the operands above, and must stop the program under every state of the environment.
// - exact: the function does not round; the rest of the environment is checked, not the rounding
//   mode. Each is run on the whole corpus, and must give the same bits under every rounding mode as
//   to nearest (the constructors: the same values, zeros without their sign), without a report,
//   and stop the program under flush to zero.
// - unchecked: the function does not round, and has no check at all, as before the checks of the
//   rounding mode were left out for the others: run as the exact ones under the rounding modes,
//   and not under flush to zero, where nothing checks it.
// One entry per form that reaches a function of its own in kairn::detail, and per public name.
enum class Kind { rounds, exact, unchecked };
struct Operation {
    const char* name;
    Kind kind;
    void (*run)(Bits& out);
};
inline const Operation operations[] = {
    // One limb, the arithmetic.
    {"e1.add", Kind::rounds, [](Bits& b) { put(b, unverified(E1(v_a)) + E1(v_c)); }},
    {"e1.sub", Kind::rounds, [](Bits& b) { put(b, unverified(E1(v_a)) - E1(v_c)); }},
    {"e1.mul", Kind::rounds, [](Bits& b) { put(b, unverified(E1(v_a)) * E1(v_c)); }},
    {"e1.add_assign", Kind::rounds, [](Bits& b) {
         E1 z(v_a);
         z += unverified(E1(v_c));
         put(b, z);
     }},
    {"e1.add_fast", Kind::rounds, [](Bits& b) { put(b, kairn::add_fast(unverified(E1(v_a)), E1(v_c))); }},
    {"e1.ldexp", Kind::rounds, [](Bits& b) { put(b, kairn::ldexp(unverified(E1(v_a)), 3)); }},
    {"e1.half", Kind::rounds, [](Bits& b) { put(b, kairn::half(unverified(E1(v_a)))); }},
    // Two limbs, the arithmetic.
    {"e2.add", Kind::rounds, [](Bits& b) { put(b, unverified(o.x) + o.y); }},
    {"e2.add_limb", Kind::rounds, [](Bits& b) { put(b, unverified(o.x) + double(v_c)); }},
    {"e2.limb_add", Kind::rounds, [](Bits& b) { put(b, unverified(double(v_c)) + o.x); }},
    {"e2.add_one_limb", Kind::rounds, [](Bits& b) { put(b, unverified(o.x) + E1(v_c)); }},
    {"e2.sub", Kind::rounds, [](Bits& b) { put(b, unverified(o.x) - o.y); }},
    {"e2.sub_limb", Kind::rounds, [](Bits& b) { put(b, unverified(o.x) - double(v_c)); }},
    {"e2.limb_sub", Kind::rounds, [](Bits& b) { put(b, unverified(double(v_c)) - o.x); }},
    {"e2.mul", Kind::rounds, [](Bits& b) { put(b, unverified(o.x) * o.y); }},
    {"e2.mul_limb", Kind::rounds, [](Bits& b) { put(b, unverified(o.x) * double(v_c)); }},
    {"e2.limb_mul", Kind::rounds, [](Bits& b) { put(b, unverified(double(v_c)) * o.x); }},
    {"e2.add_assign", Kind::rounds, [](Bits& b) {
         E2 z = o.x;
         z += unverified(o.y);
         put(b, z);
     }},
    {"e2.sub_assign", Kind::rounds, [](Bits& b) {
         E2 z = o.x;
         z -= unverified(double(v_c));
         put(b, z);
     }},
    {"e2.mul_assign", Kind::rounds, [](Bits& b) {
         E2 z = o.x;
         z *= unverified(o.y);
         put(b, z);
     }},
    {"e2.add_fast", Kind::rounds, [](Bits& b) { put(b, kairn::add_fast(unverified(o.x), o.y)); }},
    {"e2.ldexp", Kind::rounds, [](Bits& b) { put(b, kairn::ldexp(unverified(o.x), -5)); }},
    {"e2.half", Kind::rounds, [](Bits& b) { put(b, kairn::half(unverified(o.x))); }},
    {"e2.is_normalized", Kind::rounds, [](Bits& b) { put(b, kairn::is_normalized(o.x)); }},
    {"f2.add", Kind::rounds, [](Bits& b) { put(b, unverified(o.fx) + o.fx); }},
    // The finite cores.
    {"finite.add", Kind::rounds, [](Bits& b) { put(b, kairn::finite::add(unverified(o.x), o.y)); }},
    {"finite.add_limb", Kind::rounds, [](Bits& b) { put(b, kairn::finite::add(unverified(o.x), double(v_c))); }},
    {"finite.sub", Kind::rounds, [](Bits& b) { put(b, kairn::finite::sub(unverified(o.x), o.y)); }},
    {"finite.sub_limb", Kind::rounds, [](Bits& b) { put(b, kairn::finite::sub(unverified(o.x), double(v_c))); }},
    {"finite.limb_sub", Kind::rounds, [](Bits& b) { put(b, kairn::finite::sub(unverified(double(v_c)), o.x)); }},
    {"finite.mul", Kind::rounds, [](Bits& b) { put(b, kairn::finite::mul(unverified(o.x), o.y)); }},
    {"finite.mul_limb", Kind::rounds, [](Bits& b) { put(b, kairn::finite::mul(unverified(o.x), double(v_c))); }},
    {"finite.add_fast", Kind::rounds, [](Bits& b) { put(b, kairn::finite::add_fast(unverified(o.x), o.y)); }},
    {"finite.ldexp", Kind::rounds, [](Bits& b) { put(b, kairn::finite::ldexp(unverified(o.x), 7)); }},
    {"finite.e1_add", Kind::rounds, [](Bits& b) { put(b, kairn::finite::add(unverified(E1(v_a)), E1(v_c))); }},
    // Balls, the arithmetic.
    {"ball1.add", Kind::rounds, [](Bits& b) { put(b, unverified(o.p) + o.q); }},
    {"ball1.sub", Kind::rounds, [](Bits& b) { put(b, unverified(o.p) - o.q); }},
    {"ball1.mul", Kind::rounds, [](Bits& b) { put(b, unverified(o.p) * o.q); }},
    {"ball1.scale", Kind::rounds, [](Bits& b) { put(b, unverified(o.p) * double(v_c)); }},
    {"ball1.scale_one_limb", Kind::rounds, [](Bits& b) { put(b, unverified(o.p) * E1(v_c)); }},
    {"ball1.add_point", Kind::rounds, [](Bits& b) { put(b, unverified(o.p) + double(v_c)); }},
    {"ball2.add", Kind::rounds, [](Bits& b) { put(b, unverified(o.bp) + o.bq); }},
    {"ball2.sub", Kind::rounds, [](Bits& b) { put(b, unverified(o.bp) - o.bq); }},
    {"ball2.mul", Kind::rounds, [](Bits& b) { put(b, unverified(o.bp) * o.bq); }},
    {"ball2.scale", Kind::rounds, [](Bits& b) { put(b, unverified(o.bp) * double(v_c)); }},
    {"ball2.sub_point", Kind::rounds, [](Bits& b) { put(b, unverified(o.bp) - double(v_c)); }},
    {"ball2.point_sub", Kind::rounds, [](Bits& b) { put(b, unverified(double(v_c)) - o.bp); }},
    {"ball2.add_center", Kind::rounds, [](Bits& b) { put(b, unverified(o.bp) + o.y); }},
    {"ball2.mul_center", Kind::rounds, [](Bits& b) { put(b, unverified(o.bp) * o.y); }},
    {"ball2.mul_assign", Kind::rounds, [](Bits& b) {
         B2 z = o.bp;
         z *= unverified(o.bq);
         put(b, z);
     }},
    {"ball1.ldexp", Kind::rounds, [](Bits& b) { put(b, kairn::ldexp(unverified(o.p), -3)); }},
    {"ball1.half", Kind::rounds, [](Bits& b) { put(b, kairn::half(unverified(o.p))); }},
    {"ball2.ldexp", Kind::rounds, [](Bits& b) { put(b, kairn::ldexp(unverified(o.bp), 2000)); }},
    {"ball2.half", Kind::rounds, [](Bits& b) { put(b, kairn::half(unverified(o.bp))); }},
    // The building blocks that round (kairn/blocks.hpp), on the operands above.
    {"blocks.two_sum", Kind::rounds, [](Bits& b) { put(b, kairn::two_sum(unverified(double(v_a)), double(v_b))); }},
    {"blocks.fast_two_sum", Kind::rounds,
     [](Bits& b) { put(b, kairn::fast_two_sum(unverified(double(v_a)), double(v_b))); }},
    {"blocks.two_prod", Kind::rounds, [](Bits& b) { put(b, kairn::two_prod(unverified(double(v_a)), double(v_c))); }},
    {"blocks.radd", Kind::rounds, [](Bits& b) { put(b, kairn::radd(unverified(double(v_a)), double(v_b))); }},
    {"blocks.rmul", Kind::rounds, [](Bits& b) { put(b, kairn::rmul(unverified(double(v_a)), double(v_r))); }},
    {"blocks.add_down", Kind::rounds, [](Bits& b) { put(b, kairn::add_down(unverified(double(v_a)), double(v_b))); }},
    {"blocks.add_up", Kind::rounds, [](Bits& b) { put(b, kairn::add_up(unverified(double(v_a)), double(v_b))); }},
    {"blocks.sub_down", Kind::rounds, [](Bits& b) { put(b, kairn::sub_down(unverified(double(v_a)), double(v_b))); }},
    {"blocks.sub_up", Kind::rounds, [](Bits& b) { put(b, kairn::sub_up(unverified(double(v_a)), double(v_b))); }},
    {"blocks.mul_down", Kind::rounds, [](Bits& b) { put(b, kairn::mul_down(unverified(double(v_a)), double(v_r))); }},
    {"blocks.mul_up", Kind::rounds, [](Bits& b) { put(b, kairn::mul_up(unverified(double(v_a)), double(v_r))); }},
    {"blocks.float_add_up", Kind::rounds, [](Bits& b) { put(b, kairn::add_up(unverified(float(v_fa)), float(v_fb))); }},
    // The constructors that check what they are given, on the canonical pairs above, and whose
    // checks round: a canonical pair, a canonical center of two limbs.
    {"from_limbs.upward", Kind::rounds, [](Bits& b) { put(b, pair(v_a, v_b)); }},
    {"from_limbs.downward", Kind::rounds, [](Bits& b) { put(b, pair(v_c, v_d)); }},
    {"ball2.make", Kind::rounds, [](Bits& b) { put(b, B2(unverified(o.x), v_r)); }},
    {"ball2.make_downward", Kind::rounds, [](Bits& b) { put(b, B2(unverified(o.y), v_r)); }},
    {"ball2.center", Kind::rounds, [](Bits& b) { put(b, B2(unverified(o.y))); }},
    // from_limbs of an interval and of a ball of two limbs: the test of a canonical bound or center
    // rounds.
    {"interval2.from_limbs", Kind::rounds, [](Bits& b) {
         const double l[4] = {o.jy.lower().limb[0], o.jy.lower().limb[1], o.jy.upper().limb[0], o.jy.upper().limb[1]};
         put(b, I2::from_limbs(l));
     }},
    {"ball2.from_limbs", Kind::rounds, [](Bits& b) {
         const double l[3] = {o.bp.center().limb[0], o.bp.center().limb[1], o.bp.radius()};
         put(b, B2::from_limbs(l));
     }},
    // The ball of a constant of kairn::rational, two limbs: the test of a canonical center rounds.
    // The constant is integer arithmetic, made here under the state, which does not change it.
    {"ball2.constant", Kind::rounds,
     [](Bits& b) { put(b, B2(kairn::rational<E2>(1, static_cast<long long>(opaque(3.0))))); }},
    // Intervals, the arithmetic (interval.hpp, interval_operations.hpp).
    {"interval1.add", Kind::rounds, [](Bits& b) { put(b, unverified(o.ix) + o.iy); }},
    {"interval1.sub", Kind::rounds, [](Bits& b) { put(b, unverified(o.ix) - o.iy); }},
    {"interval1.mul", Kind::rounds, [](Bits& b) { put(b, unverified(o.ix) * o.iy); }},
    {"interval1.add_assign", Kind::rounds, [](Bits& b) {
         I1 z = o.ix;
         z += unverified(o.iy);
         put(b, z);
     }},
    {"interval2.add", Kind::rounds, [](Bits& b) { put(b, unverified(o.jx) + o.jy); }},
    {"interval2.sub", Kind::rounds, [](Bits& b) { put(b, unverified(o.jx) - o.jy); }},
    {"interval2.mul", Kind::rounds, [](Bits& b) { put(b, unverified(o.jx) * o.jy); }},
    {"interval2.mul_assign", Kind::rounds, [](Bits& b) {
         I2 z = o.jx;
         z *= unverified(o.jy);
         put(b, z);
     }},
    // The functions of the interface that Ball and Interval share that compute bounds or centers
    // (milestone2.md, "Functions that do not round", its second table).
    {"interval1.midpoint", Kind::rounds, [](Bits& b) { put(b, o.ix.midpoint()); }},
    {"interval1.radius", Kind::rounds, [](Bits& b) { put(b, o.ix.radius()); }},
    {"interval1.split", Kind::rounds, [](Bits& b) { put(b, o.ix.split()); }},
    {"interval1.to_ball", Kind::rounds, [](Bits& b) { put(b, B1(unverified(o.ix))); }},
    {"ball1.to_interval", Kind::rounds, [](Bits& b) { put(b, I1(unverified(o.p))); }},
    {"ball2.from_interval", Kind::rounds, [](Bits& b) { put(b, B2::from_interval(unverified(double(v_b)), v_a)); }},
    // from_bounds, the name of from_interval that a ball shares with an interval: the same kernels.
    {"ball2.from_bounds", Kind::rounds, [](Bits& b) { put(b, B2::from_bounds(unverified(double(v_b)), v_a)); }},
    {"ball1.from_bounds", Kind::rounds, [](Bits& b) { put(b, B1::from_bounds(double(v_b), v_a)); }},
    {"ball1.from_bounds_one", Kind::rounds, [](Bits& b) { put(b, B1::from_bounds(unverified(E1(v_b)), E1(v_a))); }},
    {"ball1.lower_as", Kind::rounds, [](Bits& b) { put(b, o.p.lower_as<double>()); }},
    {"ball1.upper_as", Kind::rounds, [](Bits& b) { put(b, o.p.upper_as<double>()); }},
    {"ball1.lower", Kind::rounds, [](Bits& b) { put(b, o.p.lower()); }},
    {"ball1.upper", Kind::rounds, [](Bits& b) { put(b, o.p.upper()); }},
    {"ball2.lower_as", Kind::rounds, [](Bits& b) { put(b, o.bp.lower_as<double>()); }},
    {"ball2.upper_as", Kind::rounds, [](Bits& b) { put(b, o.bp.upper_as<double>()); }},
    {"ball2.narrow", Kind::rounds, [](Bits& b) { put(b, B1(unverified(o.bp))); }},

    // Packed (kairn/packed.hpp) and the containers (kairn/soa.hpp), one of each form of check: each
    // operation checks the environment once, then every lane (the same code for every operation
    // of a kind, packed.hpp); the loads and the reads of an element are from_limbs.
    {"packed2.add", Kind::rounds, [](Bits& b) { put(b, P2::broadcast(o.x) + P2::broadcast(o.y)); }},
    {"packed2.limb_sub", Kind::rounds, [](Bits& b) { put(b, P1::broadcast(E1(v_c)) - P2::broadcast(o.x)); }},
    {"packed2.mul_limb", Kind::rounds, [](Bits& b) { put(b, P2::broadcast(o.x) * P1::broadcast(E1(v_c))); }},
    {"packed2.ldexp", Kind::rounds, [](Bits& b) { put(b, kairn::ldexp(P2::broadcast(o.x), -2000)); }},
    {"packed2.finite_add", Kind::rounds, [](Bits& b) { put(b, kairn::finite::add(P2::broadcast(o.x), P2::broadcast(o.y))); }},
    {"packedf.add", Kind::rounds, [](Bits& b) {
         using F = kairn::Packed<float, 2>;
         put(b, F::broadcast(o.fx) + F::broadcast(o.fx));
     }},
    {"packed2.load", Kind::rounds, [](Bits& b) {
         const Arrays a(o.y);
         put(b, P2::load(a.h, a.l));
     }},
    {"packed2.from_limbs", Kind::rounds, [](Bits& b) {
         const P2 x = P2::broadcast(o.x);
         put(b, P2::from_limbs(x.limb[0], x.limb[1]));
     }},
    {"soa.get", Kind::rounds, [](Bits& b) {
         Arrays a(o.x);
         put(b, kairn::SoAView<const double, 2>(a.h, a.l, 16).get(3));
     }},
    {"soa.element", Kind::rounds, [](Bits& b) {
         Arrays a(o.y);
         put(b, E2(kairn::SoAView<double, 2>(a.h, a.l, 16)[5]));
     }},
    {"soa.load", Kind::rounds, [](Bits& b) {
         Arrays a(o.x);
         put(b, kairn::SoAView<const double, 2>(a.h, a.l, 16).load(1));
     }},

    // The functions on arrays (kairn/batch.hpp), on arrays of the operands above: each checks the
    // environment once, then the lengths, the arrays that alias and every element.
    {"batch.sum", Kind::rounds, [](Bits& b) {
         const Arrays a(o.x);
         put(b, kairn::sum(kairn::SoAView<const double, 2>(a.h, a.l, 16)).value);
     }},
    {"batch.sum_sequential", Kind::rounds, [](Bits& b) {
         const Arrays a(o.y);
         put(b, kairn::sum(kairn::sequential, kairn::SoAView<const double, 2>(a.h, a.l, 16)).value);
     }},
    {"batch.sum_one_limb", Kind::rounds, [](Bits& b) {
         const Arrays a(o.x);
         put(b, kairn::sum(kairn::SoAView<const double, 1>(a.h, 16)).value);
     }},
    {"batch.sum_fast", Kind::rounds, [](Bits& b) {
         const Arrays a(o.x);
         put(b, kairn::sum_fast(kairn::SoAView<const double, 2>(a.h, a.l, 16)).value);
     }},
    {"batch.sum_fast_sequential", Kind::rounds, [](Bits& b) {
         const Arrays a(o.x);
         put(b, kairn::sum_fast(kairn::sequential, kairn::SoAView<const double, 2>(a.h, a.l, 16)).value);
     }},
    {"batch.dot", Kind::rounds, [](Bits& b) {
         const Arrays a(o.x), c(o.y);
         put(b, kairn::dot(kairn::SoAView<const double, 2>(a.h, a.l, 16), kairn::SoAView<const double, 2>(c.h, c.l, 16)).value);
     }},
    {"batch.dot_sequential", Kind::rounds, [](Bits& b) {
         const Arrays a(o.x), c(o.y);
         put(b, kairn::dot(kairn::sequential, kairn::SoAView<const double, 2>(a.h, a.l, 16),
                           kairn::SoAView<const double, 2>(c.h, c.l, 16)).value);
     }},
    {"batch.add", Kind::rounds, [](Bits& b) {
         const Arrays a(o.x), c(o.y);
         Arrays z(o.x);
         put(b, kairn::add(kairn::SoAView<const double, 2>(a.h, a.l, 16), kairn::SoAView<const double, 2>(c.h, c.l, 16),
                           kairn::SoAView<double, 2>(z.h, z.l, 16)));
         put(b, z.h[3]);
     }},
    {"batch.sub_in_place", Kind::rounds, [](Bits& b) {
         Arrays a(o.x);
         const Arrays c(o.y);
         const kairn::SoAView<double, 2> x(a.h, a.l, 16);
         put(b, kairn::sub(x, kairn::SoAView<const double, 2>(c.h, c.l, 16), x));
         put(b, a.h[5]);
     }},
    {"batch.scale", Kind::rounds, [](Bits& b) {
         Arrays a(o.x);
         const kairn::SoAView<double, 2> x(a.h, a.l, 16);
         put(b, kairn::scale(x, double(v_c), x));
     }},
    {"batch.mul_pow2", Kind::rounds, [](Bits& b) {
         Arrays a(o.x);
         const kairn::SoAView<double, 2> x(a.h, a.l, 16);
         put(b, kairn::mul_pow2(x, 0.25, x));
     }},
    {"batch.axpy", Kind::rounds, [](Bits& b) {
         const Arrays a(o.x);
         Arrays c(o.y);
         const kairn::SoAView<double, 2> y(c.h, c.l, 16);
         put(b, kairn::axpy(double(v_c), kairn::SoAView<const double, 2>(a.h, a.l, 16), y, y));
     }},
    {"batch.axpy_two_limbs", Kind::rounds, [](Bits& b) {
         const Arrays a(o.x);
         Arrays c(o.y);
         const kairn::SoAView<double, 2> y(c.h, c.l, 16);
         put(b, kairn::axpy(o.x, kairn::SoAView<const double, 2>(a.h, a.l, 16), y, y));
     }},
    {"batch.conv", Kind::rounds, [](Bits& b) {
         const Arrays a(o.x), c(o.y);
         double h[31], l[31];
         put(b, kairn::conv(kairn::SoAView<const double, 2>(a.h, a.l, 16), kairn::SoAView<const double, 2>(c.h, c.l, 16),
                            kairn::SoAView<double, 2>(h, l, 31)));
         put(b, h[7]);
     }},

    // The accumulator (kairn/accumulator.hpp): its operations that round, on the operands above.
    {"acc.add", Kind::rounds, [](Bits& b) {
         kairn::Accumulator<double, 2> a;
         a.add(o.x);
         put(b, a.running_sum());
     }},
    {"acc.add_limb", Kind::rounds, [](Bits& b) {
         kairn::Accumulator<double, 2> a;
         a.add(double(v_c));
         put(b, a.magnitudes());
     }},
    {"acc.add_one_limb", Kind::rounds, [](Bits& b) {
         kairn::Accumulator<double, 1> a;
         a.add(double(v_c));
         put(b, a.magnitudes());
     }},
    {"acc.add_product", Kind::rounds, [](Bits& b) {
         kairn::Accumulator<double, 2> a;
         a.add_product(o.x, o.y);
         put(b, a.running_sum());
     }},
    {"acc.add_product_limbs", Kind::rounds, [](Bits& b) {
         kairn::Accumulator<double, 1> a;
         a.add_product(double(v_a), double(v_c));
         put(b, a.running_sum());
     }},
    {"acc.merge", Kind::rounds, [](Bits& b) {
         const kairn::Accumulator<double, 2> a = kairn::Accumulator<double, 2>::from_state(o.x, 1.5, 3);
         kairn::Accumulator<double, 2> c = kairn::Accumulator<double, 2>::from_state(o.y, 2.25, 4);
         c.merge(a);
         put(b, c.running_sum());
     }},
    {"acc.error_bound", Kind::rounds, [](Bits& b) {
         put(b, kairn::Accumulator<double, 2>::from_state(o.x, 1.5, 3).error_bound());
     }},
    {"acc.ball", Kind::rounds, [](Bits& b) {
         put(b, kairn::Accumulator<double, 1>::from_state(E1(v_a), 1.5, 3).ball());
     }},
    // and those that do not round: from_state, on the corpus (canonical pairs and magnitudes, among
    // them +0, -0, subnormal numbers, the infinities and NaN); the accessors, checked for nothing.
    {"acc.from_state", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = typename std::decay_t<decltype(c.one)>::value_type;
             for (const auto& x : c.two)
                 for (const T& r : c.radii) {
                     const auto a = kairn::Accumulator<T, 2>::from_state(x, r, 5);
                     put(out, a.running_sum());
                     put(out, a.magnitudes());
                 }
         });
     }},
    {"acc.sum", Kind::unchecked, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = typename std::decay_t<decltype(c.one)>::value_type;
             for (const auto& x : c.two) {
                 const kairn::Accumulator<T, 2> a = kairn::Accumulator<T, 2>::from_state(x, T(1), 2);
                 put(out, a.sum().value);
                 put(out, a.sum().finite);
                 put(out, int(a.count()));
             }
         });
     }},

    // The functions that do not round, each on its whole corpus, for double and float.
    {"e1.neg", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (auto a : c.one) put(out, -kairn::Expansion<decltype(a), 1>(a));
         });
     }},
    {"batch.norm_upper", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = typename std::decay_t<decltype(c.one)>::value_type;
             for (const T& a : c.one) put(out, kairn::norm_upper(kairn::SoAView<const T, 1>(&a, 1)).value);
             const kairn::Reduction<T> r1 = kairn::norm_upper(kairn::SoAView<const T, 1>(c.one.data(), c.one.size()));
             put(out, r1.value);
             put(out, r1.finite);
             std::vector<T> h, l;
             for (const auto& x : c.two) {
                 h.push_back(x.limb[0]);
                 l.push_back(x.limb[1]);
                 const kairn::Reduction<T> e = kairn::norm_upper(kairn::SoAView<const T, 2>(&x.limb[0], &x.limb[1], 1));
                 put(out, e.value);
                 put(out, e.finite);
             }
             put(out, kairn::norm_upper(kairn::SoAView<const T, 2>(h.data(), l.data(), h.size())).value);
         });
     }},
    {"e1.abs", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (auto a : c.one) put(out, kairn::abs(kairn::Expansion<decltype(a), 1>(a)));
         });
     }},
    {"e1.compare", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using X = kairn::Expansion<std::decay_t<decltype(c.one[0])>, 1>;
             for (auto a : c.one)
                 for (auto d : c.one) compare(out, X(a), X(d));
         });
     }},
    {"e1.conversions", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (auto a : c.one) {
                 const kairn::Expansion<decltype(a), 1> x(a);
                 put(out, kairn::to_nearest(x));
                 put(out, kairn::to_down(x));
                 put(out, kairn::to_up(x));
                 put(out, kairn::abs_upper(x));
             }
         });
     }},
    {"e2.neg", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.two) put(out, -unverified(x));
         });
     }},
    {"e2.abs", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.two) put(out, kairn::abs(unverified(x)));
         });
     }},
    {"e2.compare", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.two)
                 for (const auto& y : c.two) compare(out, unverified(x), y);
         });
     }},
    {"e2.compare_limb", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.two)
                 for (auto a : c.one) compare(out, unverified(x), a);
         });
     }},
    {"e2.limb_compare", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (auto a : c.one)
                 for (const auto& y : c.two) compare(out, unverified(a), y);
         });
     }},
    {"e2.compare_one_limb", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using X = kairn::Expansion<std::decay_t<decltype(c.one[0])>, 1>;
             for (const auto& x : c.two)
                 for (auto a : c.one) {
                     compare(out, unverified(x), X(a));
                     compare(out, X(a), unverified(x));
                 }
         });
     }},
    {"e2.conversions", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.two) {
                 put(out, kairn::to_nearest(unverified(x)));
                 put(out, kairn::to_down(unverified(x)));
                 put(out, kairn::to_up(unverified(x)));
                 put(out, kairn::abs_upper(unverified(x)));
             }
         });
     }},
    {"e2.narrow", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using X = kairn::Expansion<std::decay_t<decltype(c.one[0])>, 1>;
             for (const auto& x : c.two) put(out, X(unverified(x)));
         });
     }},
    {"ball1.neg", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.balls1) put(out, -unverified(x));
         });
     }},
    {"ball2.neg", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.balls2) put(out, -unverified(x));
         });
     }},
    // The constructors whose only rounded operation is the guard a + 0: the same values, zeros
    // without their sign.
    {"ball1.point", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using X = kairn::Ball<std::decay_t<decltype(c.one[0])>, 1>;
             for (auto a : c.one) put_value(out, X(unverified(a)));
         });
     }},
    {"ball1.center", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             for (auto a : c.one) put_value(out, kairn::Ball<T, 1>(unverified(kairn::Expansion<T, 1>(a))));
         });
     }},
    {"ball1.make", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             for (auto a : c.one)
                 for (auto r : c.radii) put_value(out, kairn::Ball<T, 1>(unverified(kairn::Expansion<T, 1>(a)), r));
         });
     }},
    {"ball2.point", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using X = kairn::Ball<std::decay_t<decltype(c.one[0])>, 2>;
             for (auto a : c.one) put_value(out, X(unverified(a)));
         });
     }},
    // The ball of a constant, one limb: its center and radius given to the constructor, as any
    // Constant of the corpus's values and radii, and a constant of kairn::rational.
    {"ball1.constant", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             using X = kairn::Expansion<T, 1>;
             for (auto a : c.one)
                 for (auto r : c.radii) put_value(out, kairn::Ball<T, 1>(kairn::Constant<X>{X(a), r, false}));
             put_value(out, kairn::Ball<T, 1>(kairn::rational<X>(1, static_cast<long long>(opaque(3.0)))));
         });
     }},
    // The sign predicates of a ball: comparisons of the radius with the center.
    {"ball1.certainly", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.balls1) {
                 put(out, x.certainly_positive());
                 put(out, x.certainly_negative());
                 put(out, x.certainly_zero());
             }
         });
     }},
    {"ball2.certainly", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.balls2) {
                 put(out, x.certainly_positive());
                 put(out, x.certainly_negative());
                 put(out, x.certainly_zero());
             }
         });
     }},
    // Intervals: the negation, the hull and the intersection (comparisons and selects), and the
    // bounds of two limbs as numbers of T (to_down and to_up of a bound).
    {"interval1.neg", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.intervals1) put(out, -unverified(x));
         });
     }},
    {"interval2.neg", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.intervals2) put(out, -unverified(x));
         });
     }},
    {"interval1.hull_intersection", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.intervals1)
                 for (const auto& y : c.intervals1) {
                     put(out, x.hull(unverified(y)));
                     put(out, x.intersection(unverified(y)));
                 }
         });
     }},
    {"interval2.hull_intersection", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.intervals2)
                 for (const auto& y : c.intervals2) {
                     put(out, x.hull(unverified(y)));
                     put(out, x.intersection(unverified(y)));
                 }
         });
     }},
    {"interval2.lower_upper_as", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             for (const auto& x : c.intervals2) {
                 put(out, x.template lower_as<T>());
                 put(out, x.template upper_as<T>());
             }
         });
     }},
    // The constructors of an interval: of one limb, and of two from a T, whose only rounded
    // operations are the guards (the same values, zeros without their sign); of two limbs from
    // numbers of two limbs, comparisons and selects (the same bits).
    {"interval1.make", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             using X = kairn::Interval<T, 1>;
             for (auto lo : c.one) {
                 put_value(out, X(unverified(lo)));
                 for (auto hi : c.one) {
                     put_value(out, X(unverified(lo), hi));
                     put_value(out, X(unverified(kairn::Expansion<T, 1>(lo)), kairn::Expansion<T, 1>(hi)));
                 }
             }
         });
     }},
    {"interval2.make", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             using X = kairn::Interval<T, 2>;
             for (auto lo : c.one) {
                 put_value(out, X(unverified(lo)));
                 for (auto hi : c.one) put_value(out, X(unverified(lo), hi));
             }
             for (const auto& lo : c.two) {
                 put(out, X(unverified(lo)));
                 for (const auto& hi : c.two) put(out, X(unverified(lo), hi));
             }
         });
     }},
    // from_limbs of an interval and of a ball of one limb: the guards, and a test of the limbs that
    // does not round, but the guards' zeros depend on the rounding mode, which is checked; on every
    // interval and ball of the corpus.
    {"interval1.from_limbs", Kind::rounds, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             for (const auto& x : c.intervals1) {
                 const T l[2] = {x.lower().limb[0], x.upper().limb[0]};
                 put_value(out, kairn::Interval<T, 1>::from_limbs(l));
             }
         });
     }},
    {"ball1.from_limbs", Kind::rounds, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             for (const auto& x : c.balls1) {
                 const T l[2] = {x.center().limb[0], x.radius()};
                 put_value(out, kairn::Ball<T, 1>::from_limbs(l));
             }
         });
     }},
    // from_bounds, the constructors from two bounds under the name an interval shares with a ball:
    // the same kernels, the same values and bits.
    {"interval1.from_bounds", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             using X = kairn::Interval<T, 1>;
             for (auto lo : c.one)
                 for (auto hi : c.one) {
                     put_value(out, X::from_bounds(lo, hi));
                     put_value(out, X::from_bounds(unverified(kairn::Expansion<T, 1>(lo)), kairn::Expansion<T, 1>(hi)));
                 }
         });
     }},
    {"interval2.from_bounds", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             using X = kairn::Interval<T, 2>;
             for (auto lo : c.one)
                 for (auto hi : c.one) put_value(out, X::from_bounds(unverified(lo), hi));
             for (const auto& lo : c.two)
                 for (const auto& hi : c.two) put(out, X::from_bounds(lo, hi));
         });
     }},
    // The conversion of a SumAndError to a two-limb number: its guards, a + 0, as from_limbs_unchecked
    // (the same values, zeros without their sign), and its check of the pair, which does not round.
    {"blocks.to_expansion", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             for (const auto& r : c.sums) put_value(out, kairn::Expansion<T, 2>(r));
         });
     }},
    // Packed: the functions that do not round, on the corpus W values at a time.
    {"packed1.neg_abs", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : pack(c.one)) {
                 put(out, -x);
                 put(out, kairn::abs(x));
             }
         });
     }},
    {"packed1.compare", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             const auto ps = pack(c.one);
             for (const auto& x : ps)
                 for (const auto& y : ps) compare(out, x, y);
         });
     }},
    {"packed1.conversions", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : pack(c.one)) {
                 put(out, kairn::to_nearest(x));
                 put(out, kairn::to_down(x));
                 put(out, kairn::to_up(x));
                 put(out, kairn::abs_upper(x));
             }
         });
     }},
    {"packed2.neg_abs", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : pack(c.two)) {
                 put(out, -x);
                 put(out, kairn::abs(x));
             }
         });
     }},
    {"packed2.compare", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             const auto ps = pack(c.two);
             for (const auto& x : ps)
                 for (const auto& y : ps) compare(out, x, y);
         });
     }},
    {"packed2.compare_limb", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             const auto ps = pack(c.two);
             const auto qs = pack(c.one);
             for (const auto& x : ps)
                 for (const auto& a : qs) {
                     compare(out, x, a);
                     compare(out, a, x);
                 }
         });
     }},
    {"packed2.conversions", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : pack(c.two)) {
                 put(out, kairn::to_nearest(x));
                 put(out, kairn::to_down(x));
                 put(out, kairn::to_up(x));
                 put(out, kairn::abs_upper(x));
                 put(out, kairn::Packed<typename std::decay_t<decltype(x)>::limb_type, 1>(x));
             }
         });
     }},
    // Ball vectors (kairn/ball_vector.hpp): the functions that round, each the loop it calls (or the
    // composition), with the checks of the environment and of every operand; the construction of
    // two limbs, whose test of a canonical center rounds.
    {"bv1.add", Kind::rounds, [](Bits& b) { put(b, bv1x + bv1y); }},
    {"bv1.add_sequential", Kind::rounds, [](Bits& b) {
         BV1 z;
         kairn::add(kairn::sequential, bv1x, bv1y, z);
         put(b, z);
     }},
    {"bv2.sub", Kind::rounds, [](Bits& b) { put(b, bv2x - bv2y); }},
    {"bv2.scale", Kind::rounds, [](Bits& b) { put(b, bv2x * double(v_c)); }},
    {"bv1.ldexp", Kind::rounds, [](Bits& b) { put(b, kairn::ldexp(bv1x, -3)); }},
    {"bv2.half", Kind::rounds, [](Bits& b) { put(b, kairn::half(bv2x)); }},
    {"bv2.axpy", Kind::rounds, [](Bits& b) { put(b, kairn::axpy(double(v_c), bv2x, bv2y)); }},
    {"bv1.convolution", Kind::rounds, [](Bits& b) { put(b, kairn::convolution(bv1x, bv1y)); }},
    {"bv2.norm_upper", Kind::rounds, [](Bits& b) { put(b, kairn::norm_upper(bv2x)); }},
    {"bv2.make", Kind::rounds, [](Bits& b) { put(b, BV2({o.y, o.x, o.y, o.x, o.y}, v_r)); }},
    {"bv2.view_make", Kind::rounds, [](Bits& b) {
         Arrays a(o.x);
         double r = v_r;
         put(b, kairn::BallVectorView<double, 2>(kairn::SoAView<double, 2>(a.h, a.l, 16), r));
     }},

    // Ball vectors: the functions that do not round, each on ball vectors of the corpus: the
    // negation (sign bits, a copy of the radius, and the fold of maxima, which compares), the same
    // bits. The constructors of one limb were here too (their only rounded operations are the guards
    // a + 0 and the loop's m - m, the same values under every mode) until clang-cl returned the
    // whole space for one of these vectors under rounding downward, where m - m and so the radius
    // are -0 (2026-11-21): they are of the kind that rounds, and a build with the checks stops them.
    {"bv1.neg", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.bvs1) put(out, -x);
         });
     }},
    {"bv2.neg", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.bvs2) {
                 auto z = x;
                 kairn::neg(kairn::sequential, x, z);
                 put(out, z);
                 put(out, -x);
             }
         });
     }},
    {"bv1.make", Kind::rounds, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             for (std::size_t k = 0; k < c.one.size(); ++k)
                 for (auto r : c.radii) {
                     std::array<kairn::Expansion<T, 1>, 5> one5;
                     for (std::size_t i = 0; i < 5; ++i) one5[i] = kairn::Expansion<T, 1>(c.one[(k + i) % c.one.size()]);
                     put_value_bv(out, kairn::BallVector<T, 1, 5>(one5, r));
                     T limbs[5];
                     for (std::size_t i = 0; i < 5; ++i) limbs[i] = c.one[(k + i) % c.one.size()];
                     T radius = r;
                     put_value_bv(out, kairn::BallVectorView<T, 1>(kairn::SoAView<T, 1>(limbs, 5), radius));
                 }
         });
     }},

    // The functions that do not round and have no check at all.
    // Ball vectors: the accessors, the whole space, the views and the copy of a view.
    {"bv.access", Kind::unchecked, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             const auto w = kairn::BallVector<T, 2, 5>::whole();
             put(out, w);
             put(out, w.entry(3));
             const kairn::BallVectorView<const T, 2> v = w;
             put(out, kairn::BallVector<T, 2, 5>(v));
             put(out, v.is_finite());
             put(out, v.center(1));
             put(out, kairn::BallVector<T, 1, 3>().entry(2));
         });
     }},
    // Packed and the views: the constructor from one limb (its guards, as Expansion<T, 2>(a)), the
    // loads without the check, and the moves (broadcast, lane, set_lane, select, store), and the
    // writes of a view, which copy limbs.
    {"packed.moves", Kind::unchecked, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             using Q1 = kairn::Packed<T, 1>;
             using Q2 = kairn::Packed<T, 2>;
             const auto ps = pack(c.two);
             for (const auto& a : pack(c.one)) {
                 put_value(out, Q2(a));
                 T h[16];
                 a.store(h);
                 put(out, Q1::load(h));
                 put(out, Q1::load_unchecked(h));
             }
             for (const auto& x : ps) {
                 T h[16], l[16];
                 x.store(h, l);
                 put_value(out, Q2::load_unchecked(h, l));
                 put_value(out, Q2::from_limbs_unchecked(x.limb[0], x.limb[1]));
                 put(out, Q2::broadcast(x.lane(0)));
                 Q2 y = x;
                 y.set_lane(Q2::lanes - 1, x.lane(0));
                 put(out, y);
                 put(out, kairn::select(x < ps[0], x, ps[0]));
                 kairn::SoAView<T, 2> v(h, l, std::size_t(Q2::lanes));
                 v.set(0, x.lane(Q2::lanes - 1));
                 v[Q2::lanes - 1] = x.lane(0);
                 v.store_partial(0, y, 1);
                 put(out, h[0]);
                 put(out, l[0]);
             }
         });
     }},
    {"e2.make", Kind::unchecked, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             for (auto a : c.one) {
                 put_value(out, kairn::Expansion<T, 2>(unverified(a)));
                 put_value(out, kairn::Expansion<T, 2>(unverified(kairn::Expansion<T, 1>(a))));
             }
         });
     }},
    {"e2.from_limbs_unchecked", Kind::unchecked, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             for (const auto& x : c.two) put_value(out, kairn::Expansion<T, 2>::from_limbs_unchecked(x.limb));
         });
     }},
    // The neighbors of a number: integer operations on the bit pattern, checked for nothing.
    {"blocks.next", Kind::unchecked, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (auto a : c.one) {
                 put(out, kairn::next_up(a));
                 put(out, kairn::next_down(a));
                 put(out, kairn::next_up(unverified(a)));
             }
         });
     }},
    {"e1.make", Kind::unchecked, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using X = kairn::Expansion<std::decay_t<decltype(c.one[0])>, 1>;
             for (const auto& a : c.one) {
                 put(out, X(a));
                 put(out, X::from_limbs(&a));
                 put(out, X::from_limbs_unchecked(&a));
             }
         });
     }},
    {"sign_isfinite", Kind::unchecked, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using X = kairn::Expansion<std::decay_t<decltype(c.one[0])>, 1>;
             for (auto a : c.one) {
                 put(out, kairn::sign(X(a)));
                 put(out, kairn::isfinite(X(a)));
                 put(out, kairn::is_normalized(X(a)));
             }
             for (const auto& x : c.two) {
                 put(out, kairn::sign(x));
                 put(out, kairn::isfinite(x));
             }
         });
     }},
    {"ball.accessors", Kind::unchecked, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             auto look = [&out](const auto& x) {
                 put(out, x.center());
                 put(out, x.radius());
                 put(out, x.is_finite());
                 put(out, x.is_whole());
                 put(out, x.is_empty());
             };
             for (const auto& x : c.balls1) look(x);
             for (const auto& x : c.balls2) look(x);
             using T = std::decay_t<decltype(c.one[0])>;
             look(kairn::Ball<T, 1>::empty());
             look(kairn::Ball<T, 1>::whole());
             look(kairn::Ball<T, 2>::empty());
             look(kairn::Ball<T, 2>::whole());
             look(kairn::Ball<T, 2>());
             for (const auto& x : c.balls1) put(out, x.midpoint());
             for (const auto& x : c.balls2) put(out, x.midpoint());
         });
     }},
    {"interval.accessors", Kind::unchecked, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             for (const auto& x : c.intervals1) {
                 put(out, x.lower());
                 put(out, x.upper());
                 put(out, x.template lower_as<T>());
                 put(out, x.template upper_as<T>());
                 put(out, x.is_finite());
             }
             for (const auto& x : c.intervals2) {
                 put(out, x.lower());
                 put(out, x.upper());
                 put(out, x.is_finite());
             }
             put(out, kairn::Interval<T, 1>());
             put(out, kairn::Interval<T, 2>::empty());
             put(out, kairn::Interval<T, 2>::whole());
             put(out, kairn::Interval<T, 1>::empty());
         });
     }},
    // --- The enclosure interface of stage B2 (headers-pred) -----------------------------------
    // Intervals: the predicates, the member and subset tests, the three-valued comparisons and the
    // relations of IEEE 1788, comparisons and selects that do not round, on the whole corpus.
    {"interval1.predicates", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             for (const auto& x : c.intervals1) {
                 put(out, x.is_empty());
                 put(out, x.is_whole());
                 put(out, x.certainly_positive());
                 put(out, x.certainly_negative());
                 put(out, x.certainly_zero());
                 for (T t : c.one) {
                     put(out, x.contains(t));
                     put(out, x.contains(kairn::Expansion<T, 1>(t)));
                     put(out, int(kairn::member(t, x)));
                 }
             }
         });
     }},
    {"interval2.predicates", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             for (const auto& x : c.intervals2) {
                 put(out, x.is_empty());
                 put(out, x.is_whole());
                 put(out, x.certainly_positive());
                 put(out, x.certainly_negative());
                 put(out, x.certainly_zero());
                 for (T t : c.one) put(out, x.contains(t));  // through make_2, whose guard keeps the value
                 for (const auto& t : c.two) {
                     put(out, x.contains(t));
                     put(out, int(kairn::member(t, x)));
                 }
             }
         });
     }},
    {"interval1.compare", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.intervals1)
                 for (const auto& y : c.intervals1) {
                     put(out, x.contains(unverified(y)));
                     put(out, int(kairn::less(unverified(x), y)));
                     put(out, int(kairn::less_equal(x, y)));
                     put(out, int(kairn::equal(x, y)));
                     put(out, int(kairn::greater(x, y)));
                     put(out, int(kairn::not_equal(x, y)));
                     put(out, kairn::ieee1788::equal(x, y));
                     put(out, kairn::ieee1788::subset(x, y));
                     put(out, kairn::ieee1788::interior(x, y));
                     put(out, kairn::ieee1788::disjoint(x, y));
                 }
         });
     }},
    {"interval2.compare", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.intervals2)
                 for (const auto& y : c.intervals2) {
                     put(out, x.contains(y));
                     put(out, int(kairn::less(x, unverified(y))));
                     put(out, int(kairn::less_equal(x, y)));
                     put(out, int(kairn::equal(x, y)));
                     put(out, int(kairn::greater_equal(x, y)));
                     put(out, kairn::ieee1788::equal(x, y));
                     put(out, kairn::ieee1788::subset(x, y));
                     put(out, kairn::ieee1788::interior(x, y));
                     put(out, kairn::ieee1788::disjoint(x, y));
                 }
         });
     }},
    // What rounds: the midpoint and radius together of one limb; for two limbs the midpoint, the
    // radius, the split and the conversions; of a ball the member and subset tests, the
    // comparisons, the hull, the intersection, the split, the bounds of two limbs and the ball from
    // an interval of two T. Each checks the environment, the rounding mode included.
    {"interval1.mid_rad", Kind::rounds, [](Bits& b) {
         const kairn::MidRad<double, 1> m = o.ix.mid_rad();
         put(b, m.midpoint);
         put(b, m.radius);
     }},
    {"interval2.midpoint", Kind::rounds, [](Bits& b) { put(b, o.jy.midpoint()); }},
    {"interval2.radius", Kind::rounds, [](Bits& b) { put(b, o.jy.radius()); }},
    {"interval2.mid_rad", Kind::rounds, [](Bits& b) { put(b, o.jy.mid_rad().radius); }},
    {"interval2.split", Kind::rounds, [](Bits& b) { put(b, o.jy.split()); }},
    {"interval2.to_ball", Kind::rounds, [](Bits& b) { put(b, B2(unverified(o.jy))); }},
    {"ball2.to_interval", Kind::rounds, [](Bits& b) { put(b, I2(unverified(o.bp))); }},
    {"ball2.lower", Kind::rounds, [](Bits& b) { put(b, o.bp.lower()); }},
    {"ball2.upper", Kind::rounds, [](Bits& b) { put(b, o.bp.upper()); }},
    {"ball1.from_interval", Kind::rounds, [](Bits& b) { put(b, B1::from_interval(unverified(double(v_b)), v_a)); }},
    {"ball1.contains", Kind::rounds, [](Bits& b) { put(b, o.p.contains(double(v_c))); }},
    {"ball1.contains_one", Kind::rounds, [](Bits& b) { put(b, o.p.contains(E1(v_c))); }},
    {"ball1.member", Kind::rounds, [](Bits& b) { put(b, int(kairn::member(double(v_c), o.p))); }},
    {"ball1.contains_ball", Kind::rounds, [](Bits& b) { put(b, o.p.contains(unverified(o.q))); }},
    {"ball2.contains", Kind::rounds, [](Bits& b) { put(b, o.bp.contains(double(v_c))); }},
    {"ball2.contains_two", Kind::rounds, [](Bits& b) { put(b, o.bp.contains(o.y)); }},
    {"ball2.member", Kind::rounds, [](Bits& b) { put(b, int(kairn::member(o.y, o.bp))); }},
    {"ball2.contains_ball", Kind::rounds, [](Bits& b) { put(b, o.bp.contains(o.bq)); }},
    {"ball1.less", Kind::rounds, [](Bits& b) { put(b, int(kairn::less(unverified(o.p), o.q))); }},
    {"ball1.less_equal", Kind::rounds, [](Bits& b) { put(b, int(kairn::less_equal(o.p, o.q))); }},
    {"ball1.equal", Kind::rounds, [](Bits& b) { put(b, int(kairn::equal(o.p, o.q))); }},
    {"ball2.less", Kind::rounds, [](Bits& b) { put(b, int(kairn::less(o.bp, unverified(o.bq)))); }},
    {"ball2.less_equal", Kind::rounds, [](Bits& b) { put(b, int(kairn::greater_equal(o.bp, o.bq))); }},
    {"ball2.equal", Kind::rounds, [](Bits& b) { put(b, int(kairn::not_equal(o.bp, o.bq))); }},
    {"ball1.hull", Kind::rounds, [](Bits& b) { put(b, o.p.hull(unverified(o.q))); }},
    {"ball1.intersection", Kind::rounds, [](Bits& b) { put(b, o.p.intersection(o.q)); }},
    {"ball1.split", Kind::rounds, [](Bits& b) { put(b, o.p.split()); }},
    {"ball2.hull", Kind::rounds, [](Bits& b) { put(b, o.bp.hull(o.bq)); }},
    {"ball2.intersection", Kind::rounds, [](Bits& b) { put(b, o.bp.intersection(unverified(o.bq))); }},
    {"ball2.split", Kind::rounds, [](Bits& b) { put(b, o.bp.split()); }},
    // What reads stored values or a Trit, and checks nothing.
    {"enclosure.unchecked", Kind::unchecked, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (const auto& x : c.balls1) {
                 put(out, x.mid_rad().midpoint);
                 put(out, x.mid_rad().radius);
             }
             for (const auto& x : c.balls2) put(out, x.mid_rad().midpoint);
         });
         for (kairn::Trit t : {kairn::Trit::no, kairn::Trit::unknown, kairn::Trit::yes}) {
             put(b, kairn::certainly(t));
             put(b, kairn::possibly(t));
         }
     }},
    // --- The end of the enclosure interface of stage B2 -------------------------------------
    {"traits", Kind::unchecked, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             using X = kairn::traits<kairn::Expansion<T, 2>>;
             for (const auto& e : {X::add, X::add_limb, X::sub, X::sub_limb, X::mul, X::mul_limb, X::ldexp}) {
                 put(out, e.unit);
                 put(out, e.tiny);
                 put(out, e.unit_computed);
                 put(out, e.tiny_computed);
             }
             put(out, kairn::traits<T>::mul.unit);
             put(out, X::add_fast.unit);
             put(out, X::precision);
         });
     }},
    {"rational", Kind::unchecked, [](Bits& b) {
         const long long fractions[][2] = {{1, 3}, {-1, 10}, {2, 7}, {0, 5}, {1LL << 62, 3}, {-7, -9}};
         for (const auto& q : fractions) {
             const long long n = opaque(q[0]), d = opaque(q[1]);
             const auto x2 = kairn::rational<E2>(n, d);
             const auto x1 = kairn::rational<double>(n, d);
             const auto f2 = kairn::rational<F2>(n, d);
             put(b, x2.value);
             put(b, x2.error);
             put(b, x2.exact);
             put(b, x1.value);
             put(b, f2.value);
         }
     }},
};

// The states of the environment: set() changes it, restore() puts back what was found, reason is
// what Kairn's message says of it, and rounding whether it is a rounding mode.
struct State {
    const char* name;
    bool (*set)();
    void (*restore)();
    const char* reason;
    bool rounding;
};
inline int saved_round = FE_TONEAREST;
inline bool set_round(int mode) {
    saved_round = std::fegetround();
    return std::fesetround(mode) == 0 && std::fegetround() == mode;
}
inline void restore_round() { std::fesetround(saved_round); }
#if defined(__x86_64__) || defined(_M_X64)
inline unsigned saved_csr = 0;
inline bool set_csr(unsigned bits) {
    saved_csr = _mm_getcsr();
    _mm_setcsr(saved_csr | bits);
    return (_mm_getcsr() & bits) == bits;
}
inline void restore_csr() { _mm_setcsr(saved_csr); }
#elif defined(__aarch64__)
inline std::uint64_t saved_fpcr = 0;
inline std::uint64_t read_fpcr() {
#if defined(__clang__)
    return __builtin_arm_rsr64("fpcr");
#else
    return __builtin_aarch64_get_fpcr64();
#endif
}
inline void write_fpcr(std::uint64_t v) {
#if defined(__clang__)
    __builtin_arm_wsr64("fpcr", v);
#else
    __builtin_aarch64_set_fpcr64(v);
#endif
}
inline bool set_fpcr(std::uint64_t bits) {
    saved_fpcr = read_fpcr();
    write_fpcr(saved_fpcr | bits);
    return (read_fpcr() & bits) == bits;
}
inline void restore_fpcr() { write_fpcr(saved_fpcr); }
#endif
inline const char* const not_to_nearest = "the rounding mode is not to nearest";
inline const State states[] = {
    {"upward", [] { return set_round(FE_UPWARD); }, restore_round, not_to_nearest, true},
    {"downward", [] { return set_round(FE_DOWNWARD); }, restore_round, not_to_nearest, true},
    {"toward-zero", [] { return set_round(FE_TOWARDZERO); }, restore_round, not_to_nearest, true},
#if defined(__x86_64__) || defined(_M_X64)
    {"ftz", [] { return set_csr(0x8000u); }, restore_csr, "flushed to zero", false},  // MXCSR.FTZ
    {"daz", [] { return set_csr(0x0040u); }, restore_csr, "read as zero", false},     // MXCSR.DAZ
#elif defined(__aarch64__)
    {"fz", [] { return set_fpcr(std::uint64_t{1} << 24); }, restore_fpcr, "flushed to zero", false},  // FPCR.FZ
#endif
};

// Whether the function is a batch entry (environment.hpp, check_batch_environment: the functions on
// arrays of batch.hpp, and the operations on whole ball vectors of ball_vector.hpp, their
// constructors included), whose check of the environment is made in every build: the operations
// named batch.* and bv1.*, bv2.* here (bv.access, which copies, is none).
inline bool batch_entry(const char* name) {
    return std::strncmp(name, "batch.", 6) == 0 || std::strncmp(name, "bv1.", 4) == 0 || std::strncmp(name, "bv2.", 4) == 0;
}
inline const char* kind_name(Kind k) {
    return k == Kind::rounds ? "rounds" : k == Kind::exact ? "exact" : "unchecked";
}

// The first index at which two results differ, or -1.
inline long first_difference(const Bits& a, const Bits& b) {
    if (a.size() != b.size()) return long(a.size() < b.size() ? a.size() : b.size());
    for (std::size_t i = 0; i < a.size(); ++i)
        if (a[i] != b[i]) return long(i);
    return -1;
}

}  // namespace kairn_test
