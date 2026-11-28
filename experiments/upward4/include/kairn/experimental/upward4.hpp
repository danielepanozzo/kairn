/// @file
/// EXPERIMENTAL, NOT VERIFIED, not part of the library: no bound stated here is proved. A four-limb
/// ("quad double") interval computed under the rounding mode upward (experiments/upward4/README.md).
/// Requires the rounding mode upward set by kairn::upward::Scope and the options of
/// docs/concepts/upward.md (GCC and Clang -frounding-math), as kairn/upward.hpp does; MSVC is
/// refused below, and no Windows target was part of this experiment.
///
/// The interval [lo, hi] is kept as two *upper quadruples*: (u0, u1, u2, u3) with u0 + u1 + u2 + u3 >=
/// hi and (n0, n1, n2, n3) with n0 + n1 + n2 + n3 >= -lo, so that both bounds are rounded the same way
/// (RD(t) = -RU(-t)). The eight numbers sit in four registers of two lanes, R_i = (u_i, n_i), lane 0 the
/// upper bound and lane 1 the negated lower bound, as in kairn::upward::Interval<double> and the
/// two-limb experiment (kairn/experimental/upward2.hpp): one four-limb operation rounded up on the two
/// lanes computes both bounds. In memory: u0, n0, u1, n1, u2, n2, u3, n3. The *stored values* U and N
/// are the bounds: the interval is exactly [-N, U].
///
/// THE INVARIANT every operation restores (and every constructor makes), lane by lane, for a
/// quadruple (a0, a1, a2, a3) that is not +inf and not near the overflow threshold:
///
///     a_i = RU(a_i + a_{i+1})   for i = 0, 1, 2          ("upper-normalized", pair by pair)
///
/// that is a_{i+1} <= 0 and a_i + a_{i+1} > pred(a_i): each later limb is not positive and smaller in
/// magnitude than the gap below the limb before. It is the two-limb invariant on each adjacent pair.
/// It is equivalent to the stronger form a_i = RU(a_i + a_{i+1} + ... + a_3) for each i (each limb is
/// the value of itself and everything after it, rounded up). Why: by induction from the end, if
/// a_{i+1} = RU(T) for the exact tail T = a_{i+1} + ... + a_3, then T <= 0 iff a_{i+1} <= 0 (RU is
/// monotone and 0 is a number), and T > -g iff a_{i+1} > -g for the number -g = pred(a_i) - a_i (if
/// T > -g then RU(T) >= T > -g; if T <= -g then RU(T) <= -g): so a_i = RU(a_i + T) iff a_i = RU(a_i +
/// a_{i+1}). Consequences used below:
/// - a0 = RU(value): a0 <= 0 exactly when the value is, a0 < 0 exactly when it is (the value is a
///   sum of numbers, a multiple of the smallest subnormal), and a0 = 0 makes every limb 0;
/// - the order of the values of two quadruples is the lexicographic order of their limbs (if
///   a_i > b_i at the first difference, the tail values satisfy A_i > pred(a_i) >= b_i >= B_i);
/// - (a0, a1) is the tightest upper-normalized pair above the value (a1 = RU(a1 + a2 + a3)) and a0
///   the tightest number above it: the conversions to fewer limbs are truncations and lose nothing
///   that the narrower type can keep;
/// - |a1 + a2 + a3| < gap(a0) <= 2^-52 |a0| for a normal a0, and likewise for each tail.
///
/// States (as the two-limb experiment and Interval<double, 2>): the empty set has NaN first limbs in
/// both lanes (its later limbs are NaN or zero); the whole line is R0 = (+inf, +inf) with every later
/// limb 0; [a, +inf] has u0 = +inf, u1 = u2 = u3 = 0; [-inf, b] has n0 = +inf and zero later limbs. No
/// limb is -inf. A first limb +MAX or -MAX has zero later limbs; a first limb -MAX (an upper bound
/// -MAX, a lower bound +MAX) is a finite bound: under the mode upward a value below -MAX rounds to
/// -MAX, which is still an upper bound of it. A later limb is never infinite, NaN (but in the empty
/// set) or of magnitude MAX.
///
/// HOW THE INVARIANT IS RESTORED. Each operation's fast path computes four limbs by a fixed sequence of
/// two_sum / fast_two_sum steps rounded up (every step an upper bound, see below) and then TESTS, in
/// both lanes: the invariant itself on its result (RU(z_i + z_{i+1}) == z_i for i = 0, 1, 2 and |z0| <
/// MAX, a few instructions); that the few steps whose error could fail to be a number of the format
/// (two_sum_x below) had an exact error; for a sum, that the result is not far below the operands (a
/// cancellation of more than 48 bits); for a product, that its leading product is not near underflow.
/// Where a test fails (special values, overflow, a carry that the fixed sequence did not propagate, an
/// inexact error, a deep cancellation, an underflow: how often each happens is measured in the README),
/// the operation returns its cold path: an exact computation (the limbs, or the products of limbs, as
/// integers in a fixed-point accumulator) whose result is the best upper quadruple of the exact value,
/// and which handles every special value. So the invariant holds on every result by construction,
/// whatever the fixed sequences do; what is argued (and only tested) of the sequences is their
/// tightness and how rarely they leave the fast path.
///
/// THE RULE THAT MAKES EVERY RESULT AN UPPER BOUND: a term is never dropped, only rounded up. Every
/// operation is rounded up (the mode upward); a two_sum or fast_two_sum (s, t) has s + t >= a + b for
/// every pair of numbers; the error of a product, RU(a b - RU(a b)), computed by one fused operation,
/// is the exact error when nothing underflows and at least it in every case; a product term that is
/// not kept exactly is computed by fused operations rounded up (an upper bound of it, whatever its
/// sign); the only terms left out are errors of additions rounded up, which are not positive, so that
/// leaving them out is rounding up.
#pragma once

#if defined(_MSC_VER) && !defined(__clang__)
#error "kairn/experimental/upward4.hpp (EXPERIMENTAL) is not available with MSVC: its barriers need GNU inline assembly, and no MSVC build was part of the experiment (experiments/upward4/README.md)"
#endif

#include <kairn/experimental/upward2.hpp>
#include <kairn/kairn.hpp>
#include <kairn/upward.hpp>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>

// --- The forms ---------------------------------------------------------------------------------------
//
// The register layer is the two-limb experiment's (kairn/experimental/upward2.hpp), selected by
// KAIRN_UPWARD2_FORM: SSE (x86-64 with FMA, __m128d), NEON (AArch64, float64x2_t; every comparison an
// integer test of the bits), NUMBERS (two plain doubles per register, any target: the fallback, slow
// and right). An FMA is required: on x86-64 without -mfma the header falls back to NUMBERS, whose
// fused operation is std::fma (correctly rounded in every mode, slow where it is not an instruction).
//
// KAIRN_UPWARD4_SUM: the sum of the type, KAIRN_UPWARD4_SUM_ACCURATE (default) or
// KAIRN_UPWARD4_SUM_SLOPPY (experiments/upward4/README.md, "The sum"). KAIRN_UPWARD4_COUNT (0 by
// default): when 1, the cold paths count their calls in counters the checks read (not thread-safe:
// for the checks only).
#define KAIRN_UPWARD4_SUM_ACCURATE 1
#define KAIRN_UPWARD4_SUM_SLOPPY 2
#if !defined(KAIRN_UPWARD4_SUM)
#define KAIRN_UPWARD4_SUM KAIRN_UPWARD4_SUM_ACCURATE
#endif
#if !defined(KAIRN_UPWARD4_COUNT)
#define KAIRN_UPWARD4_COUNT 0
#endif

namespace kairn::experimental::upward4 {

namespace detail {

namespace u2d = ::kairn::experimental::upward2::detail;
using u2d::kInf;
using u2d::kMax;
using u2d::M;
using u2d::V;

/// The four registers of an interval, R_i = (u_i, n_i). A named type (external linkage), so that the
/// class below, which holds it, may be passed between files.
struct R4 {
    V r0, r1, r2, r3;
};

#if KAIRN_UPWARD4_COUNT
/// The calls of the cold paths, by cause (the checks print them): 0 the sum, 1 the product, 2 the
/// operations with a number and the square. One set per thread.
inline thread_local long cold_count[3] = {0, 0, 0};
#define KAIRN_UPWARD4_COUNTED(k) (++::kairn::experimental::upward4::detail::cold_count[k])
#else
#define KAIRN_UPWARD4_COUNTED(k) ((void)0)
#endif

// Every function below either rounds or depends on the options of the file: internal linkage, so
// that each file runs its own copy (docs/developer/design/upward.md, "Linkage").
namespace {

using u2d::add;
using u2d::any;
using u2d::bar;
using u2d::big;
using u2d::bits;
using u2d::blend;
using u2d::check_mode;
using u2d::clear;
using u2d::dup0;
using u2d::dup1;
using u2d::eq;
using u2d::flip;
using u2d::fmadd;
using u2d::isnan;
using u2d::lane0;
using u2d::lane1;
using u2d::le0;
using u2d::lt0;
using u2d::mall;
using u2d::mand;
using u2d::mdup0;
using u2d::mdup1;
using u2d::mlane1;
using u2d::mor;
using u2d::mswap;
using u2d::mul;
using u2d::nanify;
using u2d::neg;
using u2d::pin;
using u2d::sub;
using u2d::swap;
using u2d::vabs;
using u2d::vload;
using u2d::vmake;
using u2d::vmax;
using u2d::vmin;
using u2d::vset;
using u2d::vstore;
using u2d::vzero;

// The same operations on one number, for the cold paths (one lane at a time), rounded by the current
// mode (upward inside a Scope); fmadd is std::fma, one rounding.
KAIRN_FORCEINLINE double add(double a, double b) noexcept { return a + b; }
KAIRN_FORCEINLINE double sub(double a, double b) noexcept { return a - b; }
KAIRN_FORCEINLINE double mul(double a, double b) noexcept { return a * b; }
KAIRN_FORCEINLINE double fmadd(double a, double b, double c) noexcept { return std::fma(a, b, c); }
KAIRN_FORCEINLINE double vmin(double a, double b) noexcept { return b < a ? b : a; }
KAIRN_FORCEINLINE double vmax(double a, double b) noexcept { return a > b ? a : b; }
KAIRN_FORCEINLINE double neg(double a) noexcept { return -a; }

// --- The two building blocks of sums, under the mode upward ------------------------------------------
//
// The two-limb experiment's (upward2.hpp, where each has its reasons in full), as templates of this
// file so that they also run on one number (the cold paths) and on four lanes (the forms of AVX2):
// two_sum(a, b) -> (s, t) with s + t >= a + b for any numbers with no overflow, t = RU(a + b - s) (the
// smaller of the two orders of Fast2Sum's last two operations, one of which is exact by Boldo,
// Graillat and Muller 2017, relied on); fast_two_sum(a, b): s + t >= a + b and t <= 0 for any a, b (the
// proof probe of the two-limb experiment), t = RU(a + b - s) when |a| >= |b|; two_sum_nonpos(a, b) for
// a, b <= 0: fast_two_sum of (min, max), the smaller being the larger in magnitude. Each (s, t) is
// upper-normalized. The error of a sum rounded up is not always a number of the format (when the
// smaller operand is positive and more than 53 bits below the larger's last bit, t is its rounding up),
// and the branch-free 2Sum of six operations does not give an upper bound of it in general: neither
// is used.
template <class P>
KAIRN_FORCEINLINE void two_sum(P a, P b, P& s, P& t) noexcept {
    s = add(a, b);
    const P t1 = add(sub(a, s), b);
    const P t2 = add(sub(b, s), a);
    t = vmin(t1, t2);
}
template <class P>
KAIRN_FORCEINLINE void fast_two_sum(P a, P b, P& s, P& t) noexcept {
    s = add(a, b);
    t = add(sub(a, s), b);
}
template <class P>
KAIRN_FORCEINLINE void two_sum_nonpos(P a, P b, P& s, P& t) noexcept { fast_two_sum(vmin(a, b), vmax(a, b), s, t); }

// The barriers of a kernel (docs/developer/design/upward.md, "Barriers"), on each register.
KAIRN_FORCEINLINE void pin(R4& x) noexcept {
    pin(x.r0);
    pin(x.r1);
    pin(x.r2);
    pin(x.r3);
}
KAIRN_FORCEINLINE void bar(R4& x) noexcept {
    bar(x.r0);
    bar(x.r1);
    bar(x.r2);
    bar(x.r3);
}

// --- The test of the invariant ------------------------------------------------------------------------
//
// normal(z): both lanes of z satisfy the invariant with a first limb of magnitude below MAX (so not
// +inf, not NaN, not the overflow threshold): RU(z_i + z_{i+1}) equals z_i as a value for i = 0, 1, 2.
// RU(a + b) == a holds exactly when b <= 0 and a + b > pred(a) (if b > 0, RU(a + b) >= a + b > a), the
// definition of the invariant. On x86-64 and in the fallback an ordered equality (a +0 and a -0 count as
// equal); on AArch64, where Clang under strict floating point scalarizes vector comparisons of doubles,
// the difference RU(RU(a + b) - a) tested for a zero by its bits: it is +-0 exactly when RU(a + b) and
// a are equal as values (a nonzero difference of two numbers is at least the smallest subnormal in
// magnitude, and rounds to no zero; a NaN or an infinity gives a NaN).
#if KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_SSE
KAIRN_FORCEINLINE bool normal(const R4& z) noexcept {
    const M ok = mand(mand(eq(add(z.r0, z.r1), z.r0), eq(add(z.r1, z.r2), z.r1)),
                      mand(eq(add(z.r2, z.r3), z.r2), _mm_cmplt_pd(vabs(z.r0), _mm_set1_pd(kMax))));
    return bits(ok) == 3;
}
#elif KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_NEON
KAIRN_FORCEINLINE uint64x2_t ub(V a) noexcept { return vreinterpretq_u64_f64(a); }
KAIRN_FORCEINLINE bool normal(const R4& z) noexcept {
    const uint64x2_t d = vorrq_u64(vorrq_u64(ub(sub(add(z.r0, z.r1), z.r0)), ub(sub(add(z.r1, z.r2), z.r1))),
                                   ub(sub(add(z.r2, z.r3), z.r2)));
    const uint64x2_t zero = vceqzq_u64(vshlq_n_u64(d, 1));
    const uint64x2_t small = vcltq_u64(vandq_u64(ub(z.r0), vdupq_n_u64(0x7fffffffffffffffu)), vdupq_n_u64(0x7fefffffffffffffu));
    return vminvq_u32(vreinterpretq_u32_u64(vandq_u64(zero, small))) != 0;
}
#else
KAIRN_FORCEINLINE bool normal1(double a, double b, double c, double d) noexcept {
    return a + b == a && b + c == b && c + d == c && std::fabs(a) < kMax;
}
KAIRN_FORCEINLINE bool normal(const R4& z) noexcept {
    return normal1(z.r0.v0, z.r1.v0, z.r2.v0, z.r3.v0) && normal1(z.r0.v1, z.r1.v1, z.r2.v1, z.r3.v1);
}
#endif

// --- Masks of exactness -------------------------------------------------------------------------------
//
// ge_abs(a, b): |a| >= |b| per lane (on AArch64 a test of the bits without the sign, which orders
// numbers that are not NaN as their magnitudes); mblend(m, a, b): mask a where m, else b; all_set(m):
// every lane set; Mask<P>: the mask of a register P (two lanes, or four on AVX2); all_mask<P>(): a mask
// with every lane set.
#if KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_SSE
KAIRN_FORCEINLINE M ge_abs(V a, V b) noexcept { return _mm_cmpge_pd(vabs(a), vabs(b)); }
KAIRN_FORCEINLINE M mblend(M m, M a, M b) noexcept { return _mm_blendv_pd(b, a, m); }
KAIRN_FORCEINLINE bool all_set(M m) noexcept { return _mm_movemask_pd(m) == 3; }
KAIRN_FORCEINLINE M mornot(M a, M b) noexcept { return _mm_or_pd(a, _mm_xor_pd(b, mall())); }   // a | !b
KAIRN_FORCEINLINE M veq(V a, V b) noexcept { return _mm_cmpeq_pd(a, b); }                         // equal values
// |z| >= t (t >= 0), or z == 0
KAIRN_FORCEINLINE M not_small(V z, V t) noexcept { return _mm_or_pd(_mm_cmpge_pd(vabs(z), t), _mm_cmpeq_pd(z, _mm_setzero_pd())); }
#elif KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_NEON
KAIRN_FORCEINLINE M ge_abs(V a, V b) noexcept { return vcgeq_u64(u2d::abits(a), u2d::abits(b)); }
KAIRN_FORCEINLINE M mblend(M m, M a, M b) noexcept { return vbslq_u64(m, a, b); }
KAIRN_FORCEINLINE bool all_set(M m) noexcept { return vminvq_u32(vreinterpretq_u32_u64(m)) != 0; }
KAIRN_FORCEINLINE M mornot(M a, M b) noexcept { return vornq_u64(a, b); }
// Equal values (+0 and -0 equal): RU(a - b) is +-0 exactly then (a nonzero difference of two numbers
// does not round to zero), tested by its bits without the sign.
KAIRN_FORCEINLINE M veq(V a, V b) noexcept { return vceqzq_u64(vshlq_n_u64(vreinterpretq_u64_f64(sub(a, b)), 1)); }
KAIRN_FORCEINLINE M not_small(V z, V t) noexcept {
    const uint64x2_t az = u2d::abits(z);
    return vorrq_u64(vcgeq_u64(az, u2d::abits(t)), vceqzq_u64(az));
}
#else
KAIRN_FORCEINLINE M ge_abs(V a, V b) noexcept { return {std::fabs(a.v0) >= std::fabs(b.v0), std::fabs(a.v1) >= std::fabs(b.v1)}; }
KAIRN_FORCEINLINE M mblend(M m, M a, M b) noexcept { return {m.m0 ? a.m0 : b.m0, m.m1 ? a.m1 : b.m1}; }
KAIRN_FORCEINLINE bool all_set(M m) noexcept { return m.m0 && m.m1; }
KAIRN_FORCEINLINE M mornot(M a, M b) noexcept { return {a.m0 || !b.m0, a.m1 || !b.m1}; }
KAIRN_FORCEINLINE M veq(V a, V b) noexcept { return {a.v0 == b.v0, a.v1 == b.v1}; }
KAIRN_FORCEINLINE M not_small(V z, V t) noexcept {
    return {std::fabs(z.v0) >= t.v0 || z.v0 == 0, std::fabs(z.v1) >= t.v1 || z.v1 == 0};
}
#endif
template <class P>
struct Mask {
    using type = M;
};
// A number in every lane of a register P.
template <class P>
KAIRN_FORCEINLINE P bcast(double a) noexcept {
    if constexpr (sizeof(P) == sizeof(V)) return vset(a);
#if KAIRN_UPWARD2_AVX2
    else return u2d::vset4(a);
#endif
}
template <class P>
KAIRN_FORCEINLINE typename Mask<P>::type all_mask() noexcept {
    return mall();
}
#if KAIRN_UPWARD2_AVX2
using u2d::V4;
// GCC warns that the vector attribute of __m256d is ignored on a template argument (-Wignored-attributes);
// the specialization only names the type, so the warning is silenced here.
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wignored-attributes"
#endif
template <>
struct Mask<V4> {
    using type = V4;
};
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC diagnostic pop
#endif
template <>
KAIRN_FORCEINLINE V4 all_mask<V4>() noexcept {
    return _mm256_castsi256_pd(_mm256_set1_epi32(-1));
}
KAIRN_FORCEINLINE V4 ge_abs(V4 a, V4 b) noexcept { return _mm256_cmp_pd(vabs(a), vabs(b), _CMP_GE_OQ); }
KAIRN_FORCEINLINE V4 mblend(V4 m, V4 a, V4 b) noexcept { return _mm256_blendv_pd(b, a, m); }
KAIRN_FORCEINLINE bool all_set(V4 m) noexcept { return _mm256_movemask_pd(m) == 15; }
KAIRN_FORCEINLINE V4 mornot(V4 a, V4 b) noexcept { return _mm256_or_pd(a, _mm256_xor_pd(b, all_mask<V4>())); }
KAIRN_FORCEINLINE V4 not_small(V4 z, V4 t) noexcept {
    return _mm256_or_pd(_mm256_cmp_pd(vabs(z), t, _CMP_GE_OQ), _mm256_cmp_pd(z, _mm256_setzero_pd(), _CMP_EQ_OQ));
}
KAIRN_FORCEINLINE V4 veq(V4 a, V4 b) noexcept { return _mm256_cmp_pd(a, b, _CMP_EQ_OQ); }
#endif

// two_sum_x, fast_two_sum_x: two_sum and fast_two_sum that also clear the lanes of ok where the error
// t is not the exact error. The error of a sum rounded up is a number of the format unless the smaller
// operand is positive and far enough below the larger's last bit (then t is its rounding up, and as
// much as 2^-53 of it is lost, which at the heads of four limbs is far more than the last limb); the
// test: in the order whose first operand is the larger in magnitude, r = RU(a - s) is exact (the
// lemma of Boldo, Graillat and Muller), so t = RU(r + b) is the exact error iff RU(t - r) == b (if t >
// r + b, then t - r > b and its rounding up too). fast_two_sum_x needs |a| >= |b| (argued at its call)
// for its test to mean exactness. The fast paths take the exact cold path where ok is not set.
template <class P>
KAIRN_FORCEINLINE void two_sum_x(P a, P b, P& s, P& t, typename Mask<P>::type& ok) noexcept {
    s = add(a, b);
    const P ra = sub(a, s), rb = sub(b, s);
    const P ta = add(ra, b), tb = add(rb, a);
    t = vmin(ta, tb);
    ok = mand(ok, mblend(ge_abs(a, b), veq(sub(ta, ra), b), veq(sub(tb, rb), a)));
}
template <class P>
KAIRN_FORCEINLINE void fast_two_sum_x(P a, P b, P& s, P& t, typename Mask<P>::type& ok) noexcept {
    s = add(a, b);
    const P r = sub(a, s);
    t = add(r, b);
    ok = mand(ok, veq(sub(t, r), b));
}

// --- Renormalization: the fixed sequences ---------------------------------------------------------------
//
// A vector sum from the bottom (the VecSum of Ogita, Rump and Oishi, "Accurate sum and dot product",
// SIAM J. Sci. Comput. 2005, as Joldes, Marty, Muller and Popescu, "Arithmetic algorithms for extended
// precision using floating-point expansions", IEEE Trans. Computers 2016, use it in their
// renormalization), each step a two-sum rounded up, so that
// the head is the sum of everything rounded up step by step and the errors, all not positive, carry
// what each step rounded away. renorm_*: the vector sum, then the same on its errors, then on theirs:
// each limb is the head of a vector sum of what remains below the limbs before it. Every step is an
// upper bound (z0 + z1 + z2 + z3 >= c0 + ... for any numbers); the errors of the last step's sums of
// the lowest terms, not positive, are the only terms left out. Why the result is usually normalized
// (only tested, and tested at the end of every operation, see normal above): each head is RU of its
// exact remainder unless a rounding up at a lower step crossed a number, which needs a remainder
// within a few units of the lowest limb of a number; zeros between limbs (an exact step) are absorbed,
// since a vector sum of (0, 0, w) is (w, 0, 0).

// Four terms, c1, c2, c3 not positive (the sum): z0 + z1 + z2 + z3 >= c0 + c1 + c2 + c3.
template <class P>
KAIRN_FORCEINLINE void renorm4_sum(P c0, P c1, P c2, P c3, P& z0, P& z1, P& z2, P& z3) noexcept {
    P v, w1, w2, w3, k2, k3;
    two_sum_nonpos(c2, c3, v, w3);   // both not positive: the smaller is the larger in magnitude
    two_sum_nonpos(c1, v, v, w2);
    two_sum(c0, v, z0, w1);          // c0 of either sign, possibly smaller than v (cancellation)
    two_sum_nonpos(w2, w3, v, k3);   // errors: not positive
    two_sum_nonpos(w1, v, z1, k2);
    two_sum_nonpos(k2, k3, z2, z3);
}

// Five terms, c1..c4 not positive (the accurate sum): the same with one more step at the bottom of
// each vector sum, every error kept until the last limb, which is the sum of the last two rounded up.
// When the heads cancel, the result's first limb is far below c0 and the levels of the result are
// lower than the operands': an error of the operands' third level is then of the result's second, so
// no step above the last may round one away.
template <class P>
KAIRN_FORCEINLINE void renorm5_sum(P c0, P c1, P c2, P c3, P c4, P& z0, P& z1, P& z2, P& z3) noexcept {
    P v, w1, w2, w3, w4, k2, k3, k4, j3, j4;
    two_sum_nonpos(c3, c4, v, w4);
    two_sum_nonpos(c2, v, v, w3);
    two_sum_nonpos(c1, v, v, w2);
    two_sum(c0, v, z0, w1);
    two_sum_nonpos(w3, w4, v, k4);
    two_sum_nonpos(w2, v, v, k3);
    two_sum_nonpos(w1, v, z1, k2);
    two_sum_nonpos(k3, k4, v, j4);
    two_sum_nonpos(k2, v, z2, j3);
    z3 = add(j3, j4);
}

// Four terms of either sign with |c0| >= |c1 + c2 + c3| (the product, whose head is the product of the
// heads; c1 is level 1, c2 level 2, c3 level 3): z0 + z1 + z2 + z3 >= c0 + c1 + c2 + c3. The step of
// level 0 is a fast_two_sum, whose order |c0| >= |s1| holds for normalized operands whose head product is
// normal (|s1| is about 3 2^-52 |c0| at most); for any operands it is still an upper pair. The two upper
// steps are where an error that is not a number of the format would cost more than the last limb:
// - level 0 with level 1: fast_two_sum_x tests that its error w1 is exact (its second operand s1 is not
//   positive on the fast path of the case table, so it always is there; the forms that mix signs need it);
// - level 1 with level 2: s1 = RU(c1 + v). Its error is NOT a number of the format when v is positive
//   and far below the last place of c1: a product of bounds of the sign of the head has a positive
//   p1 q1 in level 2 (the square of the second limb, for the upper bound of a square), and where it
//   outweighs the level's errors, v > 0. The two-sum would then round the error up, losing as much as
//   2^-53 of it (2^-159 of the result, far more than the last limb), which an earlier version of this
//   function tested and sent to the exact cold path (0.7 to 2.7% of the squares and 0.04 to 1.3% of the
//   products of the checks' classes away from underflow and overflow took it, at a cost of hundreds of
//   nanoseconds each). Here the error is kept EXACTLY as two numbers instead:
//   r = RU(c1 - s1) is exact when |c1| >= |v| (the first two operations of Fast2Sum are exact in a
//   directed mode when the first operand is the larger: Boldo, Graillat and Muller 2017, relied on; the
//   order is tested, ge_abs, and holds on the fast path, level 2 being below level 1), so the error of
//   s1 is exactly r + v. Then (y, k) = fast_two_sum(r, v): when that error is a number (v not positive,
//   or not far below), y = RU(r + v) is it, RU(r - y) = -v exactly and k = 0; when it is not, v > 0 and
//   r <= -v (s1 >= c1 + v), so |r| >= |v| and RU(r - y) is exact (the same lemma), and k is the exact
//   error of y unless v is more than about 2^-53 below the step |r| (fast_two_sum_x tests it: then the
//   cold path). So y + k = r + v exactly on the fast path; y <= 0 (RU of the error of a sum rounded up,
//   which is not positive), k <= 0 (fast_two_sum's error, any operands).
// The rest, w1 + y + k + w3, has every term not positive. The vector sums of the version before on (w1, y,
// w3), y in place of the error of s1: (v', k3) of y with w3, (z1, k2) of w1 with v', each a
// two_sum_nonpos (exact errors); then k, below level 2, joins the last step: (z2, z3) = two_sum_nonpos(k2,
// RU(k3 + k)). So the path to z1 is as short as before (k is not on it: a dependent chain of products,
// Horner's, measured 3 to 10% slower on the Zen 2 when k was added to w3 first), and the results are those
// of the version before wherever its test passed (k = 0 there, RU(k3 + 0) = k3). The errors left out: the
// rounding of k3 + k (zero when k = 0; otherwise one rounding at the level of the last limb's last place),
// and the error of the level-2 with level-3 step (two_sum(c2, c3), rounded up), at the same level.
template <class P>
KAIRN_FORCEINLINE void renorm4_mul(P c0, P c1, P c2, P c3, P& z0, P& z1, P& z2, P& z3, typename Mask<P>::type& ok) noexcept {
    P v, w1, w3, y, k, k2, k3;
    two_sum(c2, c3, v, w3);
    const P s1 = add(c1, v);
    const P r = sub(c1, s1);   // exact: |c1| >= |v| (tested)
    ok = mand(ok, ge_abs(c1, v));
    fast_two_sum_x(r, v, y, k, ok);   // y + k = c1 + v - s1 (tested)
    fast_two_sum_x(c0, s1, z0, w1, ok);
    two_sum_nonpos(y, w3, v, k3);
    two_sum_nonpos(w1, v, z1, k2);
    two_sum_nonpos(k2, add(k3, k), z2, z3);
}

// --- The sum of two quadruples ----------------------------------------------------------------------------
//
// Lane by lane, x + y for normalized x, y (every x_i, y_i not positive for i >= 1). Level k is the
// magnitude of the k-th limbs (about 2^-53k of the heads). Both forms add the limbs of each level by a
// two-sum (the heads by two_sum, whose error is exact unless the smaller head is positive and more
// than 53 bits below the larger: then the error of a sum rounded up is not a number of the format, and
// t is its rounding up; the later limbs, not positive, by two_sum_nonpos), then gather each level with
// the errors of the level above, then renormalize. Both follow the shape of the "sloppy" addition of
// quad-double arithmetic (Hida, Li and Bailey 2001), with every two-sum replaced by one rounded up and
// every error that is dropped there either kept or, where not positive, rounded up instead. Every later
// limb and every error is not positive, so the only two-sum whose error may fail to be a number of the
// format is the heads' (a positive smaller head far below the larger: a sum with a much smaller
// positive number); it tests its exactness (two_sum_x), and the sum takes the exact cold path where it
// fails.
//
// "accurate" (the type's, KAIRN_UPWARD4_SUM_ACCURATE): every error is kept down to the fifth level, so
// that when the heads cancel (Sterbenz: then s0 and e0 are exact) the result keeps four limbs of its
// own magnitude; what is left out is below the fifth level of the operands.
//   (s_k, e_k) = two-sum(x_k, y_k), k = 0..3        s_k + e_k >= x_k + y_k
//   (t1, f1) = two-sum(s1, e0)                      level 1
//   (s0, t1) = two_sum(s0, t1)                      the head with level 1 (see below)
//   (u, g1) = two-sum(s2, e1); (t2, g2) = two-sum(u, f1)                        level 2
//   (u, h1) = two-sum(s3, e2); (u, h2) = two-sum(u, g1); (t3, h3) = two-sum(u, g2)    level 3
//   t4 = RU(e3 + RU(h1 + RU(h2 + h3)))              level 4, its errors (not positive) left out
//   z = renorm5_sum(s0, t1, t2, t3, t4)
// so z >= s0 + t1 + t2 + t3 + t4 >= ... >= x + y: each line replaces terms by numbers whose sum is at
// least theirs. Every t_k and every error is not positive (sums of numbers that are not positive, and
// errors of sums rounded up), which the two_sum_nonpos steps and renorm5_sum's need for their tightness.
// What is left out is below the fifth level of the larger operand; relative to the result it grows when
// the result is far smaller than the operands (a cancellation of more than one level), so a result
// whose first limb is below 2^-48 of the larger head (and not zero) takes the exact cold path: the sum is
// then within a few units of its own fourth limb's last place whatever the cancellation.
// The head is added to level 1 before the renormalization: when the heads cancel (a difference of
// close numbers, the width of a narrow interval), s0 and t1 are of the same magnitude and their sum
// far smaller, and the renormalization's vector sum, which meets them last, would leave errors of
// level 2 that are not below the gap of the new head (the test of the invariant then fails and the cold
// path renormalizes): added first (exactly, Sterbenz), the head is the small sum and everything below
// it is two levels lower.
template <class P>
KAIRN_FORCEINLINE void qadd_accurate(P x0, P x1, P x2, P x3, P y0, P y1, P y2, P y3, P& z0, P& z1, P& z2, P& z3,
                                     typename Mask<P>::type& ok) noexcept {
    P s0, e0, s1, e1, s2, e2, s3, e3;
    two_sum_x(x0, y0, s0, e0, ok);
    two_sum_nonpos(x1, y1, s1, e1);
    two_sum_nonpos(x2, y2, s2, e2);
    two_sum_nonpos(x3, y3, s3, e3);
    P t1, f1, u, g1, t2, g2, h1, h2, t3, h3;
    two_sum_nonpos(s1, e0, t1, f1);
    two_sum(s0, t1, s0, t1);
    two_sum_nonpos(s2, e1, u, g1);
    two_sum_nonpos(u, f1, t2, g2);
    two_sum_nonpos(s3, e2, u, h1);
    two_sum_nonpos(u, g1, u, h2);
    two_sum_nonpos(u, g2, t3, h3);
    const P t4 = add(e3, add(h1, add(h2, h3)));
    renorm5_sum(s0, t1, t2, t3, t4, z0, z1, z2, z3);
}

// "sloppy" (KAIRN_UPWARD4_SUM_SLOPPY): the fourth limbs' error and the errors of the third level's
// gathering, all not positive, left out (rounded up), as the sloppy addition leaves them out: the
// excess is then relative to |x| + |y| rather than to |x + y|, and grows when the heads cancel.
//   (s_k, e_k) = two-sum(x_k, y_k), k = 0..2;  s3 = RU(x3 + y3)
//   (t1, f1) = two-sum(s1, e0); (s0, t1) = two_sum(s0, t1); (u, g1) = two-sum(s2, e1);
//   (t2, g2) = two-sum(u, f1); t3 = RU(s3 + RU(e2 + RU(g1 + g2)))
//   z = renorm4_sum(s0, t1, t2, t3)
template <class P>
KAIRN_FORCEINLINE void qadd_sloppy(P x0, P x1, P x2, P x3, P y0, P y1, P y2, P y3, P& z0, P& z1, P& z2, P& z3,
                                   typename Mask<P>::type& ok) noexcept {
    P s0, e0, s1, e1, s2, e2;
    two_sum_x(x0, y0, s0, e0, ok);
    two_sum_nonpos(x1, y1, s1, e1);
    two_sum_nonpos(x2, y2, s2, e2);
    const P s3 = add(x3, y3);
    P t1, f1, u, g1, t2, g2;
    two_sum_nonpos(s1, e0, t1, f1);
    two_sum(s0, t1, s0, t1);
    two_sum_nonpos(s2, e1, u, g1);
    two_sum_nonpos(u, f1, t2, g2);
    const P t3 = add(s3, add(e2, add(g1, g2)));
    renorm4_sum(s0, t1, t2, t3, z0, z1, z2, z3);
}

// --- The product of two quadruples --------------------------------------------------------------------------
//
// Lane by lane, an upper quadruple of P Q for quadruples P = (p0..p3), Q = (q0..q3) of any signs (the
// operands are bounds or negated bounds: the product's case table negates an upper quadruple, whose
// value is a bound exactly, so its later limbs may be positive), each with |p_{i+1}| < gap(p_i), and
// the leading product p = RU(p0 q0), which the caller tests (the fast path holds only for |p| < MAX).
// The terms p_i q_j by level i + j, the shape of the accurate multiplication of quad-double arithmetic
// (Hida, Li and Bailey 2001), with every term that it drops as below its error bound computed instead,
// rounded up:
//   level 0: p = RU(p0 q0), e00 = RU(p0 q0 - p)                              exact when nothing underflows
//   level 1: m01, m10 = RU(p0 q1), RU(p1 q0), and their errors e01, e10      exact likewise
//   level 2: m02, m11, m20 and their errors e02, e11, e20                     exact likewise
//   level 3: c3 = RU(p0 q3 + RU(p1 q2 + RU(p2 q1 + RU(p3 q0))))              >= the sum of the four terms
//   level 4 to 6: c4 = RU(p1 q3 + RU(p2 q2 + RU(p3 q1 + RU(p2 q3 + RU(p3 q2 + RU(p3 q3))))))   >= the six
// (the error of a product is a number of the format when nothing underflows, and one fused operation
// rounded up gives it exactly; when it underflows, at least it; each fused operation rounded up is at
// least its exact value, whatever the signs: no term is left out). Then, every two-sum rounded up:
//   (t1, f1) = two_sum(m01, m10); (t1, f2) = two_sum(t1, e00)                       level 1
//   (u, g1) = two_sum(m02, m20); (u, g2) = two_sum(u, m11)                           level 2, of either sign
//   (k, h1), (k, h2), (k, h3) = two-sums of e01, e10, f1, f2 (all not positive)      level 2
//   (t2, g3) = two_sum(u, k)
//   t3 = RU of the sum of g1, g2, g3, h1, h2, h3, e02, e11, e20, c3, c4              level 3
//   z = renorm4_mul(p, t1, t2, t3)
// so z >= p + t1 + t2 + t3 >= P Q. Which steps can have an error that is not a number of the format
// (a smaller positive operand): the products of the case table pair operands whose tails have the same
// sign relative to their heads (an upper quadruple of a positive value, or the negation of one of a
// negative value, with one of the same kind), so that level 1 (p0 q1, p1 q0, e00) is never positive and
// its two-sums are exact; level 2's p1 q1 has the sign of the head, so the renormalization's step of
// level 1 with level 2 keeps its error exactly as two numbers, and its first step tests its exactness
// (renorm4_mul). With kMixed (the forms
// that compute every candidate, whose other pairs mix the signs) level 1's two-sums test theirs too.
// The fast path also needs |p| >= 2^-860 (or p = 0), so that no term down to the fourth level
// underflows: below, the errors of the products are not numbers of the format, and the exact cold
// path computes the product. The negation of p in e00 is exact (rule U3 of the design page is
// about negating a rounded result in place of the rounding of a negation; here the exact negation of p
// is what is meant, as in the two-limb pair_mul).
template <class P, bool kMixed = false>
KAIRN_FORCEINLINE void qmul(P a0, P a1, P a2, P a3, P b0, P b1, P b2, P b3, P& p, P& z0, P& z1, P& z2, P& z3,
                            typename Mask<P>::type& ok) noexcept {
    p = mul(a0, b0);
    const P e00 = fmadd(a0, b0, neg(p));
    const P m01 = mul(a0, b1), m10 = mul(a1, b0);
    const P e01 = fmadd(a0, b1, neg(m01)), e10 = fmadd(a1, b0, neg(m10));
    const P m02 = mul(a0, b2), m11 = mul(a1, b1), m20 = mul(a2, b0);
    const P e02 = fmadd(a0, b2, neg(m02)), e11 = fmadd(a1, b1, neg(m11)), e20 = fmadd(a2, b0, neg(m20));
    const P c3 = fmadd(a0, b3, fmadd(a1, b2, fmadd(a2, b1, mul(a3, b0))));
    const P c4 = fmadd(a1, b3, fmadd(a2, b2, fmadd(a3, b1, fmadd(a2, b3, fmadd(a3, b2, mul(a3, b3))))));
    P t1, f1, f2;
    if constexpr (kMixed) {
        two_sum_x(m01, m10, t1, f1, ok);
        two_sum_x(t1, e00, t1, f2, ok);
    } else {
        two_sum(m01, m10, t1, f1);
        two_sum(t1, e00, t1, f2);
    }
    P u, g1, g2, k, h1, h2, h3, t2, g3;
    two_sum(m02, m20, u, g1);
    two_sum(u, m11, u, g2);
    two_sum_nonpos(e01, e10, k, h1);
    two_sum_nonpos(k, f1, k, h2);
    two_sum_nonpos(k, f2, k, h3);
    two_sum(u, k, t2, g3);
    const P t3 = add(add(add(g1, g2), add(g3, h1)), add(add(h2, h3), add(add(e02, e11), add(e20, add(c3, c4)))));
    renorm4_mul(p, t1, t2, t3, z0, z1, z2, z3, ok);
    ok = mand(ok, not_small(p, bcast<P>(0x1p-860)));
}

// The square of a quadruple times a sign, lane by lane: A (s A) for A = (a0..a3) and B = s A, s = +-1 per
// lane (B given): the terms a_i b_j and a_j b_i are equal, so each pair is one product of a_i by 2 b_j
// (the doubling exact: no overflow on the fast path, whose leading product is below MAX), and the
// network of qmul has 14 products where it has 22 and fewer terms per level. The same reasons as qmul.
template <class P>
KAIRN_FORCEINLINE void qsqr(P a0, P a1, P a2, P a3, P b0, P b1, P b2, P b3, P& p, P& z0, P& z1, P& z2, P& z3,
                            typename Mask<P>::type& ok) noexcept {
    const P d1 = add(b1, b1), d2 = add(b2, b2), d3 = add(b3, b3);
    p = mul(a0, b0);
    const P e00 = fmadd(a0, b0, neg(p));
    const P m01 = mul(a0, d1);
    const P e01 = fmadd(a0, d1, neg(m01));
    const P m02 = mul(a0, d2), m11 = mul(a1, b1);
    const P e02 = fmadd(a0, d2, neg(m02)), e11 = fmadd(a1, b1, neg(m11));
    const P c3 = fmadd(a0, d3, mul(a1, d2));
    const P c4 = fmadd(a1, d3, fmadd(a2, b2, fmadd(a2, d3, mul(a3, b3))));
    P t1, f1;
    two_sum(m01, e00, t1, f1);
    P u, g1, k, h1, t2, g2;
    two_sum(m02, m11, u, g1);
    two_sum_nonpos(e01, f1, k, h1);
    two_sum(u, k, t2, g2);
    const P t3 = add(add(add(g1, g2), h1), add(add(e02, e11), add(c3, c4)));
    renorm4_mul(p, t1, t2, t3, z0, z1, z2, z3, ok);
    ok = mand(ok, not_small(p, bcast<P>(0x1p-860)));
}

// The greater of two quadruples, lane by lane: the lexicographic maximum of their limbs, which is the
// greater value when both are normalized (the order of the values is the lexicographic order of the
// limbs); the result is one of the two, exactly. Every later limb a candidate of the fast path can have
// is not positive (errors of sums rounded up, and sums of them), so where the result X is chosen at
// limb i (x_j = y_j before it, x_i > y_i), X's value is at least y's when X's tail from limb i is above
// pred(x_i), which X's own invariant gives: the callers test the result with normal(), so the choice is
// right whenever it is kept. Written with the maximum and equalities, not ordering comparisons (on
// AArch64 eq tests the bits: +0 and -0 count as different, and then either limb has value 0).
template <class P>
KAIRN_FORCEINLINE typename Mask<P>::type qmax(P a0, P a1, P a2, P a3, P b0, P b1, P b2, P b3, P& m0, P& m1, P& m2, P& m3) noexcept {
    const auto ge0 = eq(vmax(a0, b0), a0), ge1 = eq(vmax(a1, b1), a1), ge2 = eq(vmax(a2, b2), a2), ge3 = eq(vmax(a3, b3), a3);
    auto c = mand(ge2, mornot(ge3, eq(a2, b2)));   // a chosen from limb 2 on: a2 > b2, or a2 = b2 and a3 >= b3
    c = mand(ge1, mornot(c, eq(a1, b1)));
    c = mand(ge0, mornot(c, eq(a0, b0)));
    m0 = blend(c, a0, b0);
    m1 = blend(c, a1, b1);
    m2 = blend(c, a2, b2);
    m3 = blend(c, a3, b3);
    return c;   // the lanes where a was chosen
}

// --- The cold paths: exact, one lane at a time ------------------------------------------------------------
//
// A quadruple of one lane as four doubles.
struct Q {
    double a[4];
};
KAIRN_FORCEINLINE Q lane_of(const R4& x, int lane) noexcept {
    return lane ? Q{{lane1(x.r0), lane1(x.r1), lane1(x.r2), lane1(x.r3)}} : Q{{lane0(x.r0), lane0(x.r1), lane0(x.r2), lane0(x.r3)}};
}
KAIRN_FORCEINLINE R4 of_lanes(const Q& u, const Q& n) noexcept {
    return R4{vmake(u.a[0], n.a[0]), vmake(u.a[1], n.a[1]), vmake(u.a[2], n.a[2]), vmake(u.a[3], n.a[3])};
}

// Acc: an exact fixed-point accumulator, the integer sum of the terms m 2^k given to it (m an integer
// below 2^107: a significand of a double, or the product of two) in units of 2^lsb, held in 34 words
// of two's complement (2176 bits). Nothing here rounds: the integer additions are exact, a term's part
// below the unit 2^lsb is left out where the term is negative (rounding it up) and the term's integer
// rounded up by one unit where it is positive (rounding up, term by term), and the limbs taken out of
// it are rounded up. The unit is the
// lowest bit of every term, but not below 2^-1080 (a part below it changes nothing but the last limb's
// rounding up) and not so low that the terms' range does not fit. Used by the cold paths only: its
// results are the best upper quadruple of the sum it holds (each limb the exact rest below the limbs
// before it rounded up, the invariant in its strong form), at a cost of a few hundred instructions.
// Only the nw lowest words are used: as many as the terms' range needs (acc_init), so that a sum or a
// product of quadruples whose limbs have no wide gaps works on 4 to 8 words, not 34 (every loop over the
// words, the carries and borrows included, stops at nw; the value is held modulo 2^(64 nw) in two's
// complement, which holds it exactly since it fits, see acc_init).
struct Acc {
    static constexpr int kW = 34;
    std::uint64_t w[kW];
    int lsb;
    int nw;
};
// The integer significand and the exponent of its last bit of a finite nonzero double.
inline void split_double(double v, std::uint64_t& m, int& k, bool& negative) noexcept {
    std::uint64_t b;
    std::memcpy(&b, &v, 8);
    negative = (b >> 63) != 0;
    const int e = int((b >> 52) & 0x7ff);
    m = b & 0x000fffffffffffffu;
    if (e == 0) {
        k = -1074;
    } else {
        m |= std::uint64_t(1) << 52;
        k = e - 1075;
    }
}
using u128 = unsigned __int128;
inline int bitlen(u128 m) noexcept {
    const std::uint64_t hi = std::uint64_t(m >> 64), lo = std::uint64_t(m);
    return hi ? 128 - __builtin_clzll(hi) : lo ? 64 - __builtin_clzll(lo) : 0;
}
// One term: the integer m (< 2^107) times 2^k, negated where negative.
struct Term {
    u128 m;
    int k;
    bool negative;
};
// Adds (or subtracts) v << s (v < 2^128, s < 64) at word i and above, with the carry (or borrow), modulo
// 2^(64 nw).
inline void acc_add_at(Acc& a, int i, u128 v, int s, bool negative) noexcept {
    std::uint64_t part[3] = {std::uint64_t(v << s), std::uint64_t((v << s) >> 64), s ? std::uint64_t(v >> (128 - s)) : 0};
    if (s == 0) part[1] = std::uint64_t(v >> 64);
    std::uint64_t carry = 0;
    for (int j = 0; i + j < a.nw; ++j) {
        const std::uint64_t p = j < 3 ? part[j] : 0;
        if (j >= 3 && carry == 0) break;
        if (!negative) {
            const u128 t = u128(a.w[i + j]) + p + carry;
            a.w[i + j] = std::uint64_t(t);
            carry = std::uint64_t(t >> 64);
        } else {
            const u128 t = u128(a.w[i + j]) - p - carry;
            a.w[i + j] = std::uint64_t(t);
            carry = std::uint64_t(t >> 64) ? 1 : 0;
        }
    }
}
inline void acc_term(Acc& a, const Term& t) noexcept {
    if (t.m == 0) return;
    int off = t.k - a.lsb;
    u128 m = t.m;
    if (off < 0) {
        const int d = -off;
        const u128 below = d >= 128 ? m : (m & ((u128(1) << d) - 1));
        m = d >= 128 ? 0 : m >> d;
        if (below && !t.negative) m += 1;   // a positive term rounded up to the unit, term by term
        off = 0;
        if (m == 0) return;
    }
    acc_add_at(a, off / 64, m, off % 64, t.negative);
}
// The accumulator of a set of terms: its unit from their range, and its words: top + 8 - lsb bits, so
// that the top word keeps the sign and room for 2^7 carries (every term is below 2^top in magnitude, and
// there are at most 16 of them: the sum is below 2^(top + 4)).
inline void acc_init(Acc& a, const Term* t, int n) noexcept {
    int top = -1080, low = 4000;
    for (int i = 0; i < n; ++i) {
        if (t[i].m == 0) continue;
        top = std::max(top, t[i].k + bitlen(t[i].m));
        low = std::min(low, t[i].k);
    }
    int lsb = std::max(low, -1080);
    if (top + 8 - lsb > 64 * Acc::kW) lsb = top + 8 - 64 * Acc::kW;
    a.nw = std::max(1, std::min(Acc::kW, (top + 8 - lsb + 63) / 64));
    std::memset(a.w, 0, sizeof(std::uint64_t) * std::size_t(a.nw));
    a.lsb = lsb;
    for (int i = 0; i < n; ++i) acc_term(a, t[i]);
}
// The next limb: RU of the value held, taken out of it (the value becomes the rest, not positive).
// Respects the grid of the subnormal numbers (no bit below 2^-1074); a value above the largest finite
// number gives +inf, one below -MAX gives -MAX (RU of it).
inline double acc_limb(Acc& a) noexcept {
    const int nw = a.nw;
    const bool negative = (a.w[nw - 1] >> 63) != 0;
    std::uint64_t mag[Acc::kW];
    if (negative) {   // the magnitude: two's complement negation
        std::uint64_t c = 1;
        for (int i = 0; i < nw; ++i) {
            const u128 t = u128(~a.w[i]) + c;
            mag[i] = std::uint64_t(t);
            c = std::uint64_t(t >> 64);
        }
    } else {
        std::memcpy(mag, a.w, sizeof(std::uint64_t) * std::size_t(nw));
    }
    int tw = nw - 1;
    while (tw >= 0 && mag[tw] == 0) --tw;
    if (tw < 0) return 0.0;
    const int top = 64 * tw + 63 - __builtin_clzll(mag[tw]);
    const int jmin = -1074 - a.lsb;   // the bit of 2^-1074
    int lo = std::max(top - 52, jmin);
    std::uint64_t m = 0;
    bool rest = false;
    if (lo > top) {
        lo = jmin;   // a value below 2^-1074 in magnitude
        rest = true;
    } else if (lo < 0) {   // every bit of the value in the limb (the value is below 2^53 units)
        m = mag[0] << -lo;
    } else {
        const int w = lo / 64, sh = lo % 64;
        const u128 two = u128(mag[w]) | (w + 1 < nw ? u128(mag[w + 1]) << 64 : u128(0));
        m = std::uint64_t(two >> sh) & ((std::uint64_t(1) << (top - lo + 1)) - 1);   // top - lo + 1 <= 53 bits
        rest = (mag[w] & ((std::uint64_t(1) << sh) - 1)) != 0;
        for (int i = 0; i < w && !rest; ++i) rest = mag[i] != 0;
    }
    if (!negative && rest) ++m;   // rounding up the magnitude of a positive value; a negative one truncates
    if (m == 0) return 0.0;
    const int e = a.lsb + lo;   // >= -1074 (lo >= jmin)
    if (e > 1023) return negative ? -kMax : kInf;   // m 2^e > MAX (a product of special bounds)
    // m 2^e, exact unless above MAX: double(m) is exact (m <= 2^53), 2^e a number (normal, or subnormal
    // below 2^-1022), and the product of two numbers whose exact value is a number is exact in every
    // rounding mode (it is: its bits are on the grid of 2^-1074 and span at most 53 bits); above MAX
    // it is +inf, tested below. (std::ldexp gives the same, as a call of the C library.)
    const std::uint64_t pb = e >= -1022 ? std::uint64_t(e + 1023) << 52 : std::uint64_t(1) << (e + 1074);
    double p2;
    std::memcpy(&p2, &pb, 8);
    double z = double(m) * p2;
    if (negative) z = -z;
    if (!(std::fabs(z) <= kMax)) return negative ? -kMax : kInf;
    // the rest: the value minus the limb, exactly (a limb whose last bit is below the unit holds every
    // bit of the value: the rest is 0)
    if (lo >= 0) acc_add_at(a, lo / 64, u128(m), lo % 64, !negative);
    else std::memset(a.w, 0, sizeof(std::uint64_t) * std::size_t(nw));
    return z;
}
// The best upper quadruple of the value held: four limbs taken out in turn. A first limb +inf gives
// (+inf, 0, 0, 0), a first limb +-MAX zero later limbs (the rest is then not positive: rounded up).
inline Q acc_quad(Acc& a) noexcept {
    Q z;
    z.a[0] = acc_limb(a);
    if (z.a[0] == kInf || std::fabs(z.a[0]) == kMax) return Q{{z.a[0], 0.0, 0.0, 0.0}};
    for (int i = 1; i < 4; ++i) z.a[i] = acc_limb(a) + 0.0;
    return z;
}
inline void term_of(double v, Term& t) noexcept {
    if (v == 0) {
        t = Term{0, 0, false};
        return;
    }
    std::uint64_t m;
    split_double(v, m, t.k, t.negative);
    t.m = m;
}

// The sum for any canonical operands, one lane: an empty operand (NaN heads, both lanes) gives NaN; an
// operand +inf gives +inf; otherwise the eight limbs added exactly, the best upper quadruple of the sum.
inline Q ssum(const Q& x, const Q& y) noexcept {
    constexpr double nan = std::numeric_limits<double>::quiet_NaN();
    if (x.a[0] != x.a[0] || y.a[0] != y.a[0]) return Q{{nan, nan, nan, nan}};
    if (x.a[0] == kInf || y.a[0] == kInf) return Q{{kInf, 0.0, 0.0, 0.0}};
    Term t[8];
    for (int i = 0; i < 4; ++i) {
        term_of(x.a[i], t[i]);
        term_of(y.a[i], t[4 + i]);
    }
    Acc a;
    acc_init(a, t, 8);
    return acc_quad(a);
}

// The sum x + y for any canonical operands (the cold path of every sum).
KAIRN_DETAIL_COLD R4 add_special(R4 x, R4 y) noexcept {
    KAIRN_UPWARD4_COUNTED(0);
    pin(x);
    bar(y);
    R4 z = of_lanes(ssum(lane_of(x, 0), lane_of(y, 0)), ssum(lane_of(x, 1), lane_of(y, 1)));
    bar(z);
    return z;
}

// The best upper quadruple of the product of the values of two quadruples of finite limbs, one lane:
// the sixteen products of limbs, each exact as an integer.
inline Q sprod(const Q& x, const Q& y) noexcept {
    Term t[16];
    int n = 0;
    for (int i = 0; i < 4; ++i)
        for (int j = 0; j < 4; ++j) {
            Term a, b;
            term_of(x.a[i], a);
            term_of(y.a[j], b);
            t[n++] = Term{a.m * b.m, a.k + b.k, a.negative != b.negative};
        }
    Acc acc;
    acc_init(acc, t, 16);
    return acc_quad(acc);
}

// A candidate of a product of bounds, one lane, as Interval<double, 2> (mul_ext_2_2) answers it: P
// and Q are quadruples whose values are the factors exactly (a bound, or a negated bound: a head
// -inf stands for -inf); 0 times an infinity is 0; an infinite factor gives the IEEE product of the
// heads (+-inf, 0, 0, 0); otherwise the exact product, its best upper quadruple (an overflow upward
// gives +inf, a value below -MAX the first limb -MAX).
inline Q scand(const Q& x, const Q& y) noexcept {
    if (x.a[0] == 0 || y.a[0] == 0) return Q{{0.0, 0.0, 0.0, 0.0}};   // a value 0 (normalized: head 0)
    if (std::fabs(x.a[0]) == kInf || std::fabs(y.a[0]) == kInf) return Q{{x.a[0] * y.a[0], 0.0, 0.0, 0.0}};
    return sprod(x, y);
}
inline Q sneg(const Q& x) noexcept { return Q{{-x.a[0], -x.a[1], -x.a[2], -x.a[3]}}; }
// The greater of two candidates (normalized, or +-inf with zero later limbs): lexicographic.
inline Q sgreater(const Q& x, const Q& y) noexcept {
    for (int i = 0; i < 4; ++i) {
        if (x.a[i] > y.a[i]) return x;
        if (x.a[i] < y.a[i]) return y;
    }
    return x;
}

// The product for any canonical operands: the eight products of bounds (four per lane), each with its
// specials, the greatest per lane, and the empty set where an operand is empty. With x = (xu, xn) =
// (b, -a), y = (yu, yn) = (d, -c): the upper bound is max(b d, a c, a d, b c) = max(xu yu, xn yn,
// xn (-yu), xu (-yn)), and the negated lower bound -min(...) = max(xn yu, xu yn, xu (-yu), xn (-yn)).
KAIRN_DETAIL_COLD R4 mul_special(R4 x, R4 y) noexcept {
    KAIRN_UPWARD4_COUNTED(1);
    pin(x);
    bar(y);
    constexpr double nan = std::numeric_limits<double>::quiet_NaN();
    const Q xu = lane_of(x, 0), xn = lane_of(x, 1), yu = lane_of(y, 0), yn = lane_of(y, 1);
    R4 z;
    if (xu.a[0] != xu.a[0] || yu.a[0] != yu.a[0]) {
        const Q e{{nan, nan, nan, nan}};
        z = of_lanes(e, e);
    } else {
        const Q hi = sgreater(sgreater(scand(xu, yu), scand(xn, yn)), sgreater(scand(xn, sneg(yu)), scand(xu, sneg(yn))));
        const Q lo = sgreater(sgreater(scand(xn, yu), scand(xu, yn)), sgreater(scand(xu, sneg(yu)), scand(xn, sneg(yn))));
        z = of_lanes(hi, lo);
    }
    bar(z);
    return z;
}

// The product of the quadruples P and Q, lane by lane, exactly rounded up (the cold path of one product
// network whose fast path failed its tests on finite operands): each lane's best upper quadruple of
// its exact product, or mul_special(x, y) where a leading product is not finite or reaches MAX.
KAIRN_DETAIL_COLD R4 qmul_special(R4 p, R4 q, R4 x, R4 y) noexcept {
    KAIRN_UPWARD4_COUNTED(1);
    pin(p);
    bar(q);
    const Q p0 = lane_of(p, 0), p1 = lane_of(p, 1), q0 = lane_of(q, 0), q1 = lane_of(q, 1);
    const double h0 = p0.a[0] * q0.a[0], h1 = p1.a[0] * q1.a[0];
    if (!(std::fabs(h0) < kMax) || !(std::fabs(h1) < kMax)) return mul_special(x, y);
    R4 z = of_lanes(sprod(p0, q0), sprod(p1, q1));
    bar(z);
    return z;
}

// The greater of the products P Q and P' Q' lane by lane, each exactly rounded up (the cold path of the
// case where both operands contain zero): mul_special(x, y) where a leading product is not finite or
// reaches MAX.
KAIRN_DETAIL_COLD R4 qmul2_special(R4 p, R4 q, R4 p2, R4 q2, R4 x, R4 y) noexcept {
    KAIRN_UPWARD4_COUNTED(1);
    pin(p);
    bar(q);
    bar(p2);
    bar(q2);
    Q z[2];
    for (int lane = 0; lane < 2; ++lane) {
        const Q a = lane_of(p, lane), b = lane_of(q, lane), c = lane_of(p2, lane), d = lane_of(q2, lane);
        if (!(std::fabs(a.a[0] * b.a[0]) < kMax) || !(std::fabs(c.a[0] * d.a[0]) < kMax)) return mul_special(x, y);
        z[lane] = sgreater(sprod(a, b), sprod(c, d));
    }
    R4 r = of_lanes(z[0], z[1]);
    bar(r);
    return r;
}

// --- The product of intervals: the form "branch" ---------------------------------------------------------
//
// One candidate per lane chosen by branches on the signs of the bounds' first limbs (normalized: the
// sign of a first limb is the sign of the bound), two in the case where both operands contain zero in
// their interior; the case table of the two-limb experiment (upward2.hpp, kCases): P takes lane i of x
// (0 = xu = b, 1 = xn = -a), Q lane j of y (0 = yu = d, 1 = yn = -c), negated where s is set. The
// operands are moved by the same lanes<> on each of the four registers, and every case shares one
// product network. The fast path holds when every leading product computed is finite with |p| < MAX
// and the result passes normal(); otherwise (an empty or unbounded operand, 0 times an infinity, an
// overflow, a head +-MAX, a carry left by the fixed sequence) mul_special, right for every canonical
// operand. The forms measured against it are in upward4_forms.hpp.
using u2d::Case;
using u2d::kCases;

template <int P0, int P1>
KAIRN_FORCEINLINE V lanes(V a) noexcept {
    if constexpr (P0 == 0 && P1 == 1) return a;
    else if constexpr (P0 == 1 && P1 == 0) return swap(a);
    else if constexpr (P0 == 0) return dup0(a);
    else return dup1(a);
}
template <int P0, int P1>
KAIRN_FORCEINLINE R4 lanes4(const R4& a) noexcept {
    return R4{lanes<P0, P1>(a.r0), lanes<P0, P1>(a.r1), lanes<P0, P1>(a.r2), lanes<P0, P1>(a.r3)};
}
KAIRN_FORCEINLINE R4 flip4(M s, const R4& a) noexcept { return R4{flip(s, a.r0), flip(s, a.r1), flip(s, a.r2), flip(s, a.r3)}; }

// The operands of case K: P and Q.
template <int K>
KAIRN_FORCEINLINE void pick(const R4& x, const R4& y, R4& p, R4& q) noexcept {
    constexpr Case c = kCases[K];
    p = lanes4<c.p0, c.p1>(x);
    q = lanes4<c.q0, c.q1>(y);
    if constexpr (c.s0 || c.s1) {
        const M s = c.s0 && c.s1 ? mall() : c.s1 ? mlane1() : mswap(mlane1());
        q = flip4(s, q);
        bar(q);
    }
}

// One product network of P and Q on the fast path, or mul_special(x, y).
KAIRN_FORCEINLINE R4 mul_one(const R4& p, const R4& q, const R4& x, const R4& y) noexcept {
    V pr;
    R4 z;
    M ok = mall();
    qmul(p.r0, p.r1, p.r2, p.r3, q.r0, q.r1, q.r2, q.r3, pr, z.r0, z.r1, z.r2, z.r3, ok);
    if (!(all_set(ok) && normal(z)) || any(big(pr))) [[unlikely]]
        return qmul_special(p, q, x, y);
    return z;
}

// The two candidates of the case x ∋ 0, y ∋ 0: (xn, xn) (yn, yu) and (xu, xu) (yu, yn), the greater.
KAIRN_FORCEINLINE R4 mul_zero_zero(const R4& x, const R4& y) noexcept {
    const R4 pa = lanes4<1, 1>(x), qa = lanes4<1, 0>(y), pb = lanes4<0, 0>(x);
    V p1, p2;
    R4 a, b, z;
    M oka = mall(), okb = mall();
    qmul(pa.r0, pa.r1, pa.r2, pa.r3, qa.r0, qa.r1, qa.r2, qa.r3, p1, a.r0, a.r1, a.r2, a.r3, oka);
    qmul(pb.r0, pb.r1, pb.r2, pb.r3, y.r0, y.r1, y.r2, y.r3, p2, b.r0, b.r1, b.r2, b.r3, okb);
    // Only the chosen candidate's exactness matters: the other is an upper bound of a corner at most
    // the chosen one (an inexact one that came out above the exact one would have been chosen).
    const M ok = mblend(qmax(a.r0, a.r1, a.r2, a.r3, b.r0, b.r1, b.r2, b.r3, z.r0, z.r1, z.r2, z.r3), oka, okb);
    if (!(all_set(ok) && normal(z)) || any(mor(big(p1), big(p2)))) [[unlikely]]
        return qmul2_special(pa, qa, pb, y, x, y);
    return z;
}

KAIRN_FORCEINLINE R4 mul_branch(const R4& x, const R4& y) noexcept {
    const bool xn = lane0(x.r0) <= 0, xp = lane1(x.r0) <= 0;   // b <= 0, a >= 0
    const bool yn = lane0(y.r0) <= 0, yp = lane1(y.r0) <= 0;   // d <= 0, c >= 0
    R4 p, q;
    if (xp) {
        if (yp) pick<10>(x, y, p, q);
        else if (yn) pick<6>(x, y, p, q);
        else pick<2>(x, y, p, q);
    } else if (xn) {
        if (yp) pick<9>(x, y, p, q);
        else if (yn) pick<5>(x, y, p, q);
        else pick<1>(x, y, p, q);
    } else {
        if (yp) pick<8>(x, y, p, q);
        else if (yn) pick<4>(x, y, p, q);
        else return mul_zero_zero(x, y);
    }
    return mul_one(p, q, x, y);
}

// --- The kernels of the type ----------------------------------------------------------------------------------

KAIRN_FORCEINLINE R4 add_r(const R4& x, const R4& y) noexcept {
    R4 z;
    M ok = mall();
#if KAIRN_UPWARD4_SUM == KAIRN_UPWARD4_SUM_SLOPPY
    qadd_sloppy(x.r0, x.r1, x.r2, x.r3, y.r0, y.r1, y.r2, y.r3, z.r0, z.r1, z.r2, z.r3, ok);
#else
    qadd_accurate(x.r0, x.r1, x.r2, x.r3, y.r0, y.r1, y.r2, y.r3, z.r0, z.r1, z.r2, z.r3, ok);
#endif
    ok = mand(ok, not_small(z.r0, mul(vmax(vabs(x.r0), vabs(y.r0)), vset(0x1p-48))));
    if (!(all_set(ok) && normal(z))) [[unlikely]]
        return add_special(x, y);
    return z;
}

// -x: the two quadruples exchanged (exact).
KAIRN_FORCEINLINE R4 neg_r(const R4& x) noexcept { return R4{swap(x.r0), swap(x.r1), swap(x.r2), swap(x.r3)}; }

KAIRN_FORCEINLINE R4 make_r(double lo, double hi) noexcept;

// x + t for a number t: the sum with [t, t], whose quadruples are (t, 0, 0, 0) and (-t, 0, 0, 0): the
// accurate sum with y1 = y2 = y3 = 0, whose two-sums of the later limbs are then exact with zero
// errors: (s0, e0) = two_sum(x0, t); (t1, f1) = two_sum(x1, e0); (s0, t1) = two_sum(s0, t1); (t2, g)
// = two_sum(x2, f1); (t3, h) = two_sum(x3, g); renorm5_sum(s0, t1, t2, t3, h). The same reasons as the sum. A t that is infinite or a
// NaN is the whole line, as Interval(t) makes it: the cold path (the sum with Interval(t)) gives the
// whole line, or the empty set for an empty x.
KAIRN_DETAIL_COLD R4 add_num_special(R4 x, double t) noexcept;
KAIRN_FORCEINLINE R4 add_num_r(const R4& x, double t) noexcept {
    V tt = vmake(t, -t);
    bar(tt);
    V s0, e0, t1, f1, t2, g, t3, h;
    M ok = mall();
    two_sum_x(x.r0, tt, s0, e0, ok);
    two_sum_nonpos(x.r1, e0, t1, f1);
    two_sum(s0, t1, s0, t1);
    two_sum_nonpos(x.r2, f1, t2, g);
    two_sum_nonpos(x.r3, g, t3, h);
    R4 z;
    renorm5_sum(s0, t1, t2, t3, h, z.r0, z.r1, z.r2, z.r3);
    ok = mand(ok, not_small(z.r0, mul(vmax(vabs(x.r0), vabs(tt)), vset(0x1p-48))));
    if (!(all_set(ok) && normal(z)) || !(std::fabs(t) < kInf)) [[unlikely]]
        return add_num_special(x, t);
    return z;
}

// x * t for a number t: for t >= 0 the lanes are (xu t, xn t), for t < 0 (xn |t|, xu |t|): one product
// network by (|t|, 0, 0, 0), its terms with a later limb of Q zero left out (they are zero):
//   p = RU(p0 |t|), e0 = its error; m1 = RU(p1 |t|), e1; m2 = RU(p2 |t|), e2; c3 = RU(p3 |t|)
//   (t1, f1) = two_sum(m1, e0); (u, g1) = two_sum(m2, e1); (t2, g2) = two_sum(u, f1)
//   t3 = RU(c3 + RU(e2 + RU(g1 + g2)));  z = renorm4_mul(p, t1, t2, t3)
// The specials (an unbounded or empty x, an overflow, t infinite or a NaN, 0 times an infinity) and a
// result that fails normal() go to the product with Interval(t).
KAIRN_DETAIL_COLD R4 mul_num_special(R4 x, double t) noexcept;
KAIRN_FORCEINLINE R4 mul_num_r(const R4& x, double t) noexcept {
    const bool negative = t < 0;
    const R4 pr = negative ? neg_r(x) : x;
    V at = vset(std::fabs(t));
    bar(at);
    const V p = mul(pr.r0, at), e0 = fmadd(pr.r0, at, neg(p));
    const V m1 = mul(pr.r1, at), e1 = fmadd(pr.r1, at, neg(m1));
    const V m2 = mul(pr.r2, at), e2 = fmadd(pr.r2, at, neg(m2));
    const V c3 = mul(pr.r3, at);
    V t1, f1, u, g1, t2, g2;
    two_sum(m1, e0, t1, f1);
    two_sum(m2, e1, u, g1);
    two_sum(u, f1, t2, g2);
    const V t3 = add(c3, add(e2, add(g1, g2)));
    R4 z;
    M ok = mall();
    renorm4_mul(p, t1, t2, t3, z.r0, z.r1, z.r2, z.r3, ok);
    ok = mand(ok, not_small(p, vset(0x1p-860)));
    if (!(all_set(ok) && normal(z)) || any(big(p))) [[unlikely]]   // also every t that is infinite or a NaN
        return mul_num_special(x, t);
    return z;
}

// The square: x^2 = [min, max] of t^2 over x. Its upper bound is max(|a|, |b|)^2 = M M with M the
// greater of the quadruples xu and xn as values (max(b, -a) = max(|a|, |b|) for every nonempty
// interval; qmax gives an upper bound of the greater, the greater itself where the heads differ); its
// negated lower bound is -(a^2) = xn (-xn) when a >= 0, -(b^2) = xu (-xu) when b <= 0, and 0 when a < 0 <
// b. One square network of A = (M, m) by B = (M, -m). The specials go to the product x x, which encloses
// the square (looser where x contains zero).
// The case by branches on the signs of the first limbs, as the product's form "branch" (normalized: the
// sign of a first limb is the sign of the bound): a >= 0 (n0 <= 0): M = xu, m = xn, A = x; b <= 0
// (u0 <= 0): M = xn, m = xu, A = swap(x); a < 0 < b: m = 0 and M the greater of xu and xn, which, where
// the first limbs differ, is the one of the greater first limb (the order of normalized quadruples is the
// lexicographic order of their limbs), and where they are equal (a symmetric interval) qmax's. The version
// before this one computed qmax and the lanes by masks for every square (about 45 operations, 25 of them
// on the critical path); the one-sign cases now take one register move per limb.
KAIRN_DETAIL_COLD R4 sqr_special(R4 x) noexcept;
// The square network on A = (M, m) and B = (M, -m), or the cold path.
KAIRN_FORCEINLINE R4 sqr_of(const R4& a, const R4& x) noexcept {
    R4 b = flip4(mlane1(), a);
    bar(b);
    V p;
    R4 z;
    M ok = mall();
    qsqr(a.r0, a.r1, a.r2, a.r3, b.r0, b.r1, b.r2, b.r3, p, z.r0, z.r1, z.r2, z.r3, ok);
    if (!(all_set(ok) && normal(z)) || any(big(p))) [[unlikely]]
        return any(big(p)) ? sqr_special(x) : qmul_special(a, b, x, x);   // the exact square, lane by lane
    return z;
}
KAIRN_FORCEINLINE R4 sqr_r(const R4& x) noexcept {
    const M l1 = mlane1();
    const double u0 = lane0(x.r0), n0 = lane1(x.r0);
    R4 a;
    if (n0 <= 0) {
        a = x;
    } else if (u0 <= 0) {
        a = R4{swap(x.r0), swap(x.r1), swap(x.r2), swap(x.r3)};
    } else if (u0 != n0) {
        a = u0 > n0 ? R4{clear(l1, x.r0), clear(l1, x.r1), clear(l1, x.r2), clear(l1, x.r3)}
                    : R4{clear(l1, swap(x.r0)), clear(l1, swap(x.r1)), clear(l1, swap(x.r2)), clear(l1, swap(x.r3))};
    } else {   // u0 = n0 > 0 (the empty set, NaN heads, took the branch before: then the cold path)
        R4 mx;
        qmax(x.r0, x.r1, x.r2, x.r3, swap(x.r0), swap(x.r1), swap(x.r2), swap(x.r3), mx.r0, mx.r1, mx.r2, mx.r3);
        a = R4{clear(l1, mx.r0), clear(l1, mx.r1), clear(l1, mx.r2), clear(l1, mx.r3)};
    }
    return sqr_of(a, x);
}

// The product of the type: the form "branch".
KAIRN_FORCEINLINE R4 mul_r(const R4& x, const R4& y) noexcept { return mul_branch(x, y); }

// The interval of a pair of numbers, as kairn's interval_make_2 on (lo, 0), (hi, 0): [lo, hi] when
// lo <= hi, lo < +inf and hi > -inf; the empty set when hi < lo; the whole line otherwise (a NaN, or
// the same infinity twice). Exact: a negation and selections (-lo + 0.0: no first limb -0).
KAIRN_FORCEINLINE R4 make_r(double lo, double hi) noexcept {
    constexpr double nan = std::numeric_limits<double>::quiet_NaN();
    const V z = vzero();
    if (lo <= hi && lo < kInf && hi > -kInf) return R4{vmake(hi, -lo + 0.0), z, z, z};
    if (hi < lo) return R4{vset(nan), vset(nan), vset(nan), vset(nan)};
    return R4{vset(kInf), z, z, z};
}

KAIRN_DETAIL_COLD R4 add_num_special(R4 x, double t) noexcept {
    KAIRN_UPWARD4_COUNTED(2);
    KAIRN_DETAIL_UPWARD_BARRIER(t);
    return add_special(x, make_r(t, t));
}
KAIRN_DETAIL_COLD R4 mul_num_special(R4 x, double t) noexcept {
    KAIRN_UPWARD4_COUNTED(2);
    KAIRN_DETAIL_UPWARD_BARRIER(t);
    return mul_special(x, make_r(t, t));
}
KAIRN_DETAIL_COLD R4 sqr_special(R4 x) noexcept {
    KAIRN_UPWARD4_COUNTED(2);
    return mul_special(x, x);
}

// The exact peeling of one bound of the default two-limb type into an upper quadruple, one lane, under
// the mode upward: (h0, h1) with |h1| <= ulp(h0) / 2 (canonical) and finite. Each step takes the rest
// r + s (exactly the value not yet in the limbs, two numbers), its sum rounded up as the next limb z,
// and the new rest (b - z) + s' with b the larger of r and s in magnitude and s' the other: b - z is
// exact (the first two operations of Fast2Sum are exact in every rounding mode when |b| >= |s|:
// Boldo, Graillat and Muller 2017, relied on), so the rest stays exact, and is in (-gap(z), 0] since z
// is its rounding up: every limb is RU of the exact rest below the limbs before it, the invariant in
// its strong form. The fourth limb is the rest rounded up. Exact for every bound whose expansion needs
// four limbs or fewer (a gap of more than 106 bits between h0 and h1 with h1 of the wrong sign needs
// more: there the fourth limb rounds up).
KAIRN_FORCEINLINE Q peel(double h0, double h1) noexcept {
    double r = h0, s = h1, z[4];
    for (int i = 0; i < 3; ++i) {
        z[i] = r + s;
        const bool rb = std::fabs(r) >= std::fabs(s);
        const double b = rb ? r : s, sm = rb ? s : r;
        r = b - z[i];
        s = sm;
    }
    z[3] = r + s;
    return Q{{z[0], z[1], z[2], z[3]}};
}

}  // namespace
}  // namespace detail

/// The four-limb interval rounded upward (EXPERIMENTAL, NOT VERIFIED). Every operation that rounds
/// needs a kairn::upward::Scope around it; the members of the class are exact (constructors from
/// numbers, the limbs, the bounds as numbers, predicates), the same in every mode and under every
/// option.
class Interval {
public:
    /// [0, 0].
    Interval() noexcept : r_(detail::make_r(0.0, 0.0)) {}
    /// [t, t]; the whole line for an infinite t or a NaN (as kairn::Interval).
    explicit Interval(double t) noexcept : r_(detail::make_r(t, t)) {}
    /// [lo, hi]; the empty set when hi < lo; the whole line for a NaN or the same infinity twice.
    Interval(double lo, double hi) noexcept : r_(detail::make_r(lo, hi)) {}
    /// The empty set.
    static Interval empty() noexcept {
        const detail::V nan = detail::vset(std::numeric_limits<double>::quiet_NaN());
        return Interval(detail::R4{nan, nan, nan, nan});
    }
    /// The whole line.
    static Interval whole() noexcept { return Interval(detail::make_r(detail::kInf, detail::kInf)); }
    /// The interval of the stored numbers p[0..7] = (u0, n0, u1, n1, u2, n2, u3, n3): a canonical state
    /// as an operation returns it (not checked).
    static Interval from_limbs(const double* p) noexcept {
        return Interval(detail::R4{detail::vload(p), detail::vload(p + 2), detail::vload(p + 4), detail::vload(p + 6)});
    }
    /// Writes (u0, n0, u1, n1, u2, n2, u3, n3).
    void to_limbs(double* p) const noexcept {
        detail::vstore(p, r_.r0);
        detail::vstore(p + 2, r_.r1);
        detail::vstore(p + 4, r_.r2);
        detail::vstore(p + 6, r_.r3);
    }
    /// Limb i (0 to 3) of the upper quadruple (u_i) and of the negated lower one (n_i): the upper bound
    /// is exactly u0 + u1 + u2 + u3 and the lower bound exactly -(n0 + n1 + n2 + n3).
    double upper_limb(int i) const noexcept { return detail::lane0(reg(i)); }
    double neg_lower_limb(int i) const noexcept { return detail::lane1(reg(i)); }
    bool is_empty() const noexcept { return detail::lane0(r_.r0) != detail::lane0(r_.r0); }
    /// The lower bound rounded down to a number (-n0 = RD(lower bound): exact, the invariant makes n0
    /// the lower bound negated rounded up); -inf when unbounded below; +inf for the empty set (as
    /// kairn::Interval<double, 1>::lower()).
    double lower() const noexcept { return is_empty() ? detail::kInf : -detail::lane1(r_.r0); }
    /// The upper bound rounded up to a number (u0); +inf when unbounded above; -inf for the empty set.
    double upper() const noexcept { return is_empty() ? -detail::kInf : detail::lane0(r_.r0); }
    /// Every member is > 0 (n0 < 0: the invariant makes the sign of n0 that of the bound negated).
    bool certainly_positive() const noexcept { return detail::lane1(r_.r0) < 0; }
    /// Every member is < 0 (u0 < 0).
    bool certainly_negative() const noexcept { return detail::lane0(r_.r0) < 0; }
    /// Nonempty and 0 is a member (n0 >= 0 and u0 >= 0).
    bool contains_zero() const noexcept { return detail::lane1(r_.r0) >= 0 && detail::lane0(r_.r0) >= 0; }

    /// The registers (not part of an interface: for the kernels and the measurements).
    detail::R4 r_;
    explicit Interval(detail::R4 r) noexcept : r_(r) {}

private:
    detail::V reg(int i) const noexcept { return i == 0 ? r_.r0 : i == 1 ? r_.r1 : i == 2 ? r_.r2 : r_.r3; }
};

// --- The operations (internal linkage; each needs a kairn::upward::Scope) -----------------------------
//
// Forced inline, as the two-limb operations (their kernels are forced inline into them).

/// x + y.
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator+(const Interval& x, const Interval& y) noexcept {
    detail::check_mode();
    detail::R4 a = x.r_, b = y.r_;
    detail::pin(a);
    detail::bar(b);
    detail::R4 z = detail::add_r(a, b);
    detail::bar(z);
    return Interval(z);
}
/// x - y: x + (-y), -y the two quadruples of y exchanged.
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator-(const Interval& x, const Interval& y) noexcept {
    detail::check_mode();
    detail::R4 a = x.r_, b = y.r_;
    detail::pin(a);
    detail::bar(b);
    detail::R4 z = detail::add_r(a, detail::neg_r(b));
    detail::bar(z);
    return Interval(z);
}
/// -x (exact).
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator-(const Interval& x) noexcept { return Interval(detail::neg_r(x.r_)); }
/// x * y.
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator*(const Interval& x, const Interval& y) noexcept {
    detail::check_mode();
    detail::R4 a = x.r_, b = y.r_;
    detail::pin(a);
    detail::bar(b);
    detail::R4 z = detail::mul_r(a, b);
    detail::bar(z);
    return Interval(z);
}
/// x + t, t + x, x - t, t - x, x * t, t * x for a number t; an infinite t or a NaN is the whole line.
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator+(const Interval& x, double t) noexcept {
    detail::check_mode();
    detail::R4 a = x.r_;
    detail::pin(a);
    KAIRN_DETAIL_UPWARD_BARRIER(t);
    detail::R4 z = detail::add_num_r(a, t);
    detail::bar(z);
    return Interval(z);
}
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator+(double t, const Interval& x) noexcept { return x + t; }
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator-(const Interval& x, double t) noexcept { return x + (-t); }
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator-(double t, const Interval& x) noexcept { return (-x) + t; }
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator*(const Interval& x, double t) noexcept {
    detail::check_mode();
    detail::R4 a = x.r_;
    detail::pin(a);
    KAIRN_DETAIL_UPWARD_BARRIER(t);
    detail::R4 z = detail::mul_num_r(a, t);
    detail::bar(z);
    return Interval(z);
}
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator*(double t, const Interval& x) noexcept { return x * t; }
/// x^2 (the square, tighter than x * x where x contains zero).
[[maybe_unused]] static KAIRN_FORCEINLINE Interval sqr(const Interval& x) noexcept {
    detail::check_mode();
    detail::R4 a = x.r_;
    detail::pin(a);
    detail::R4 z = detail::sqr_r(a);
    detail::bar(z);
    return Interval(z);
}
[[maybe_unused]] static KAIRN_FORCEINLINE Interval& operator+=(Interval& x, const Interval& y) noexcept { return x = x + y; }
[[maybe_unused]] static KAIRN_FORCEINLINE Interval& operator-=(Interval& x, const Interval& y) noexcept { return x = x - y; }
[[maybe_unused]] static KAIRN_FORCEINLINE Interval& operator*=(Interval& x, const Interval& y) noexcept { return x = x * y; }

/// The width hi - lo rounded up to a number, under the mode upward (inside a Scope): the first limb of
/// the sum of the two quadruples, U + N, as the operator + computes it (RU of the width, or one number
/// above it, the checks found). The bounds of a narrow interval cancel: a width below 2^-48 of the
/// bounds takes the exact cold path of the sum (a few hundred instructions). +inf for an unbounded
/// interval; NaN for the empty set.
[[maybe_unused]] static KAIRN_FORCEINLINE double width(const Interval& x) noexcept {
    detail::check_mode();
    detail::R4 a = x.r_;
    detail::pin(a);
    detail::R4 z = detail::add_r(a, detail::neg_r(a));   // lane 0: U + N
    detail::bar(z);
    return detail::lane0(z.r0);
}
/// The radius (hi - lo) / 2 rounded up to a number, under the mode upward: width(x) * 0.5 rounded up.
[[maybe_unused]] static KAIRN_FORCEINLINE double radius(const Interval& x) noexcept {
    double w = width(x);
    KAIRN_DETAIL_UPWARD_BARRIER(w);
    double r = w * 0.5;
    KAIRN_DETAIL_UPWARD_BARRIER(r);
    return r;
}

/// From the two-limb round-up interval: (h, l, 0, 0) for each upper pair, exact (an upper-normalized
/// pair is a normalized quadruple with zero third and fourth limbs). Any rounding mode.
[[maybe_unused]] static KAIRN_FORCEINLINE Interval from_upward2(const ::kairn::experimental::upward2::Interval& x) noexcept {
    if (x.is_empty()) return Interval::empty();
    const detail::V z = detail::vzero();
    return Interval(detail::R4{x.r_.h, x.r_.l, z, z});
}
/// To the two-limb round-up interval: the first two limbs of each quadruple (an upper pair of it,
/// upper-normalized: a1 = RU(a1 + a2 + a3) >= the tail, and (a0, a1) is the invariant's first pair).
/// Exact moves; any rounding mode.
[[maybe_unused]] static KAIRN_FORCEINLINE ::kairn::experimental::upward2::Interval to_upward2(const Interval& x) noexcept {
    return ::kairn::experimental::upward2::Interval(::kairn::experimental::upward2::detail::R{x.r_.r0, x.r_.r1});
}
/// From kairn::upward::Interval<double>: (u, 0, 0, 0), (n, 0, 0, 0), exact. Any rounding mode.
[[maybe_unused]] static KAIRN_FORCEINLINE Interval from_upward1(const ::kairn::upward::Interval<double>& x) noexcept {
    double p[2];
    x.to_limbs(p);
    const double q[8] = {p[0], p[1], 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
    Interval r = Interval::from_limbs(q);
    if (p[0] != p[0]) return Interval::empty();
    return r;
}
/// To kairn::upward::Interval<double>: (u0, n0), the first limbs (u0 >= the upper bound, n0 >= the
/// negated lower bound, and the tightest such numbers). Exact moves; any rounding mode.
[[maybe_unused]] static KAIRN_FORCEINLINE ::kairn::upward::Interval<double> to_upward1(const Interval& x) noexcept {
    double p[2] = {detail::lane0(x.r_.r0), detail::lane1(x.r_.r0)};
    return ::kairn::upward::Interval<double>::from_limbs(p);
}
/// From the default Interval<double, 2>, under the mode upward (inside a Scope): the same set, each
/// bound peeled exactly into an upper quadruple (detail::peel: exact unless its expansion needs more
/// than four limbs). The empty set gives the empty set; an infinite bound (+inf, 0, 0, 0); a finite
/// bound whose upper quadruple overflows (MAX with a positive second limb) becomes +inf, the only upper
/// quadruple above it; a first limb +-MAX gets zero later limbs.
[[maybe_unused]] static KAIRN_FORCEINLINE Interval from_interval(const ::kairn::Interval<double, 2>& x) noexcept {
    detail::check_mode();
    double l0 = x.lower().limb[0], l1 = x.lower().limb[1], h0 = x.upper().limb[0], h1 = x.upper().limb[1];
    if (l0 == detail::kInf) return Interval::empty();
    KAIRN_DETAIL_UPWARD_BARRIER(l0);
    KAIRN_DETAIL_UPWARD_BARRIER(l1);
    KAIRN_DETAIL_UPWARD_BARRIER(h0);
    KAIRN_DETAIL_UPWARD_BARRIER(h1);
    auto bound = [](double a, double b) noexcept {
        if (std::fabs(a) == detail::kInf) return detail::Q{{detail::kInf, 0.0, 0.0, 0.0}};
        detail::Q q = detail::peel(a, b);
        if (q.a[0] == detail::kInf) return detail::Q{{detail::kInf, 0.0, 0.0, 0.0}};
        if (std::fabs(q.a[0]) == detail::kMax) return detail::Q{{q.a[0], 0.0, 0.0, 0.0}};
        return q;
    };
    const detail::Q u = bound(h0, h1), n = bound(-l0, -l1);
    detail::R4 z = detail::of_lanes(u, n);
    detail::bar(z);
    return Interval(z);
}
/// To the default Interval<double, 2>, UNDER ROUNDING TO NEAREST (outside a Scope, or inside a
/// kairn::upward::NearestScope): through the two-limb round-up interval (to_upward2, then its
/// to_interval: Fast2Sum rounded to nearest of each upper pair, exact), so the default interval's
/// bounds are the first two limbs' values, which contain the quadruples' (their later limbs are not
/// positive); the excess is that of the truncation, below 2^-104 of the bound.
[[maybe_unused]] static KAIRN_FORCEINLINE ::kairn::Interval<double, 2> to_interval(const Interval& x) noexcept {
    return ::kairn::experimental::upward2::to_interval(to_upward2(x));
}

}  // namespace kairn::experimental::upward4
