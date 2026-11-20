// The cases that tests/api/checks.cpp and tests/api/checks_handler.cpp share: the operands, every
// public function of the headers, written as a program writes it, each with whether the checks of
// KAIRN_CHECKS check the rounding mode before it, and the states of the floating-point environment
// this target can set. A program that defines KAIRN_ENVIRONMENT_FAILURE does so before including
// this file.
#pragma once

#include <kairn/kairn.hpp>

#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <limits>
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
};
inline Operands o;

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
    // The ball of a constant of kairn::rational, two limbs: the test of a canonical center rounds.
    // The constant is integer arithmetic, made here under the state, which does not change it.
    {"ball2.constant", Kind::rounds,
     [](Bits& b) { put(b, B2(kairn::rational<E2>(1, static_cast<long long>(opaque(3.0))))); }},

    // The functions that do not round, each on its whole corpus, for double and float.
    {"e1.neg", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             for (auto a : c.one) put(out, -kairn::Expansion<decltype(a), 1>(a));
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
    // The conversion of a SumAndError to a two-limb number: its guards, a + 0, as from_limbs_unchecked
    // (the same values, zeros without their sign), and its check of the pair, which does not round.
    {"blocks.to_expansion", Kind::exact, [](Bits& b) {
         for_both(b, [](Bits& out, const auto& c) {
             using T = std::decay_t<decltype(c.one[0])>;
             for (const auto& r : c.sums) put_value(out, kairn::Expansion<T, 2>(r));
         });
     }},
    // The functions that do not round and have no check at all.
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
         });
     }},
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
