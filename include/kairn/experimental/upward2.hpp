/// @file
/// EXPERIMENTAL, NOT VERIFIED, not part of the library: no bound stated here is proved. A two-limb
/// ("double double") interval computed under the rounding mode upward, for measurement
/// (experiments/upward2/README.md). Requires the rounding mode upward set by kairn::upward::Scope
/// and the options of docs/concepts/upward.md (GCC and Clang -frounding-math), as
/// kairn/upward.hpp does; MSVC and Windows are not part of this experiment.
///
/// The interval [lo, hi] is kept as two *upper pairs*: (uh, ul) with uh + ul >= hi and (nh, nl) with
/// nh + nl >= -lo, so that both bounds are rounded the same way (RD(t) = -RU(-t)). The four numbers
/// sit in two registers of two lanes, H = (uh, nh) and L = (ul, nl), lane 0 the upper bound and lane
/// 1 the negated lower bound, as in kairn::upward::Interval<double>: one two-limb operation rounded up
/// on the two lanes computes both bounds. In memory: uh, nh, ul, nl.
///
/// The invariant every operation restores (and every constructor makes): each lane's pair (h, l) is
/// *upper-normalized*, h = RU(h + l), that is l <= 0 and h + l > pred(h) (the second limb is not
/// positive and smaller in magnitude than the gap below the first); a lane whose head is +inf, +MAX
/// or -MAX has l = 0. Consequences used below: the order of the values of two such pairs is the
/// lexicographic order of (h, l); h <= 0 exactly when the value is <= 0; h = 0 implies l = 0; and
/// |l| < ulp(h) <= 2^-52 |h| for a normal h.
///
/// States: the empty set has NaN heads in both lanes (its second limbs are NaN or zero); the whole
/// line is H = (+inf, +inf), L = (0, 0); [a, +inf] has uh = +inf, ul = 0; [-inf, b] has nh = +inf,
/// nl = 0. No head is -inf. A head -MAX (an upper bound -MAX, or a lower bound +MAX) is a finite
/// bound: under the mode upward a value below -MAX rounds to -MAX, which is still an upper bound of
/// it (see "Overflow" in the README for where this differs from Interval<double, 2>).
#pragma once

#if defined(_MSC_VER) && !defined(__clang__)
#error "kairn/experimental/upward2.hpp (EXPERIMENTAL) is not available with MSVC: its barriers need GNU inline assembly, and no MSVC build was part of the experiment (experiments/upward2/README.md)"
#endif

#include <kairn/upward.hpp>

#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>

// --- The forms --------------------------------------------------------------------------------------
//
// KAIRN_UPWARD2_FORM: SSE (x86-64 with FMA: two __m128d; the functions on arrays use 256-bit AVX2
// registers where the file has AVX2), NEON (AArch64: two float64x2_t), NUMBERS (four doubles, any
// target, and any target where it is forced: the fallback, which may be slow and must be right).
#define KAIRN_UPWARD2_FORM_SSE 1
#define KAIRN_UPWARD2_FORM_NEON 2
#define KAIRN_UPWARD2_FORM_NUMBERS 3
#if !defined(KAIRN_UPWARD2_FORM)
#if (defined(__x86_64__) || defined(_M_X64)) && defined(__FMA__)
#define KAIRN_UPWARD2_FORM KAIRN_UPWARD2_FORM_SSE
#elif defined(__aarch64__) && (defined(__GNUC__) || defined(__clang__))
#define KAIRN_UPWARD2_FORM KAIRN_UPWARD2_FORM_NEON
#else
#define KAIRN_UPWARD2_FORM KAIRN_UPWARD2_FORM_NUMBERS
#endif
#endif
#if KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_SSE
#if !(defined(__x86_64__) || defined(_M_X64)) || !defined(__FMA__)
#error "KAIRN_UPWARD2_FORM_SSE needs x86-64 with FMA"
#endif
#include <immintrin.h>
#elif KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_NEON
#if !defined(__aarch64__)
#error "KAIRN_UPWARD2_FORM_NEON is the form of AArch64"
#endif
#include <arm_neon.h>
#elif KAIRN_UPWARD2_FORM != KAIRN_UPWARD2_FORM_NUMBERS
#error "KAIRN_UPWARD2_FORM is KAIRN_UPWARD2_FORM_SSE, KAIRN_UPWARD2_FORM_NEON or KAIRN_UPWARD2_FORM_NUMBERS"
#endif
#if KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_SSE && defined(__AVX2__)
#define KAIRN_UPWARD2_AVX2 1
#else
#define KAIRN_UPWARD2_AVX2 0
#endif

namespace kairn::experimental::upward2 {

namespace detail {

// The register of two lanes and its mask, per form. Named types (external linkage), so that the
// class below, which holds them, may be passed between files.
#if KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_SSE
using V = __m128d;
using M = __m128d;
#elif KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_NEON
using V = float64x2_t;
using M = uint64x2_t;
#else
struct V {
    double v0, v1;
};
struct M {
    bool m0, m1;
};
#endif

// The four numbers of an interval: the heads H = (uh, nh) and the second limbs L = (ul, nl).
struct R {
    V h, l;
};

inline constexpr double kInf = std::numeric_limits<double>::infinity();
inline constexpr double kMax = std::numeric_limits<double>::max();

// Every function below either rounds or depends on the options of the file: internal linkage, so
// that each file runs its own copy (docs/developer/design/upward.md, "Linkage").
namespace {

// --- The operations of a register of two lanes ------------------------------------------------------
//
// add, sub, mul: rounded by the current mode (upward inside a Scope). fmadd(a, b, c): a b + c rounded
// once. vmin, vmax: the smaller or greater of two numbers that are not NaN. The comparisons give a
// mask per lane. On AArch64 every comparison is an integer test of the bits: Clang under strict
// floating point turns a vector comparison of doubles into scalar code (docs/developer/design/
// upward.md, "The printers"); the bit tests differ from the IEEE comparison only on the sign of a
// zero, noted where it is used.
#if KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_SSE
KAIRN_FORCEINLINE V vset(double a) noexcept { return _mm_set1_pd(a); }
KAIRN_FORCEINLINE V vmake(double a0, double a1) noexcept { return _mm_set_pd(a1, a0); }
KAIRN_FORCEINLINE V vzero() noexcept { return _mm_setzero_pd(); }
KAIRN_FORCEINLINE double lane0(V a) noexcept { return _mm_cvtsd_f64(a); }
KAIRN_FORCEINLINE double lane1(V a) noexcept { return _mm_cvtsd_f64(_mm_unpackhi_pd(a, a)); }
KAIRN_FORCEINLINE V add(V a, V b) noexcept { return _mm_add_pd(a, b); }
KAIRN_FORCEINLINE V sub(V a, V b) noexcept { return _mm_sub_pd(a, b); }
KAIRN_FORCEINLINE V mul(V a, V b) noexcept { return _mm_mul_pd(a, b); }
KAIRN_FORCEINLINE V fmadd(V a, V b, V c) noexcept { return _mm_fmadd_pd(a, b, c); }
KAIRN_FORCEINLINE V vmin(V a, V b) noexcept { return _mm_min_pd(a, b); }
KAIRN_FORCEINLINE V vmax(V a, V b) noexcept { return _mm_max_pd(a, b); }
KAIRN_FORCEINLINE V neg(V a) noexcept { return _mm_xor_pd(a, _mm_set1_pd(-0.0)); }
KAIRN_FORCEINLINE V vabs(V a) noexcept { return _mm_andnot_pd(_mm_set1_pd(-0.0), a); }
KAIRN_FORCEINLINE V swap(V a) noexcept { return _mm_shuffle_pd(a, a, 1); }
KAIRN_FORCEINLINE V dup0(V a) noexcept { return _mm_unpacklo_pd(a, a); }
KAIRN_FORCEINLINE V dup1(V a) noexcept { return _mm_unpackhi_pd(a, a); }
KAIRN_FORCEINLINE V blend(M m, V a, V b) noexcept { return _mm_blendv_pd(b, a, m); }   // a where m
KAIRN_FORCEINLINE V clear(M m, V a) noexcept { return _mm_andnot_pd(m, a); }           // +0 where m
KAIRN_FORCEINLINE V flip(M m, V a) noexcept { return _mm_xor_pd(a, _mm_and_pd(m, _mm_set1_pd(-0.0))); }   // -a where m
KAIRN_FORCEINLINE V nanify(M m, V a) noexcept { return _mm_or_pd(a, m); }               // a NaN where m
KAIRN_FORCEINLINE M mand(M a, M b) noexcept { return _mm_and_pd(a, b); }
KAIRN_FORCEINLINE M mor(M a, M b) noexcept { return _mm_or_pd(a, b); }
KAIRN_FORCEINLINE M mswap(M a) noexcept { return _mm_shuffle_pd(a, a, 1); }
KAIRN_FORCEINLINE M mdup0(M a) noexcept { return _mm_unpacklo_pd(a, a); }
KAIRN_FORCEINLINE M mdup1(M a) noexcept { return _mm_unpackhi_pd(a, a); }
KAIRN_FORCEINLINE M le0(V a) noexcept { return _mm_cmple_pd(a, _mm_setzero_pd()); }
KAIRN_FORCEINLINE M lt0(V a) noexcept { return _mm_cmplt_pd(a, _mm_setzero_pd()); }
KAIRN_FORCEINLINE M eq(V a, V b) noexcept { return _mm_cmpeq_pd(a, b); }
KAIRN_FORCEINLINE M isnan(V a) noexcept { return _mm_cmpunord_pd(a, a); }
KAIRN_FORCEINLINE M ispinf(V a) noexcept { return _mm_cmpeq_pd(a, _mm_set1_pd(kInf)); }
// NaN, an infinity, or |a| >= MAX.
KAIRN_FORCEINLINE M big(V a) noexcept { return _mm_cmpnlt_pd(vabs(a), _mm_set1_pd(kMax)); }
// NaN or an infinity.
KAIRN_FORCEINLINE M nonfinite(V a) noexcept { return _mm_cmpnlt_pd(vabs(a), _mm_set1_pd(kInf)); }
KAIRN_FORCEINLINE M mall() noexcept { return _mm_castsi128_pd(_mm_set1_epi32(-1)); }
KAIRN_FORCEINLINE M mlane1() noexcept { return _mm_castsi128_pd(_mm_set_epi64x(-1, 0)); }
KAIRN_FORCEINLINE int bits(M m) noexcept { return _mm_movemask_pd(m); }   // bit k: lane k
KAIRN_FORCEINLINE bool any(M m) noexcept { return _mm_movemask_pd(m) != 0; }
KAIRN_FORCEINLINE void bar(V& v) noexcept { KAIRN_DETAIL_UPWARD_BARRIER(v); }
KAIRN_FORCEINLINE void pin(V& v) noexcept { KAIRN_DETAIL_UPWARD_PIN(v); }
KAIRN_FORCEINLINE V vload(const double* p) noexcept { return _mm_loadu_pd(p); }
KAIRN_FORCEINLINE void vstore(double* p, V v) noexcept { _mm_storeu_pd(p, v); }
#elif KAIRN_UPWARD2_FORM == KAIRN_UPWARD2_FORM_NEON
KAIRN_FORCEINLINE uint64x2_t ubits(V a) noexcept { return vreinterpretq_u64_f64(a); }
KAIRN_FORCEINLINE V vset(double a) noexcept { return vdupq_n_f64(a); }
KAIRN_FORCEINLINE V vmake(double a0, double a1) noexcept { return vcombine_f64(vdup_n_f64(a0), vdup_n_f64(a1)); }
KAIRN_FORCEINLINE V vzero() noexcept { return vdupq_n_f64(0.0); }
KAIRN_FORCEINLINE double lane0(V a) noexcept { return vgetq_lane_f64(a, 0); }
KAIRN_FORCEINLINE double lane1(V a) noexcept { return vgetq_lane_f64(a, 1); }
KAIRN_FORCEINLINE V add(V a, V b) noexcept { return vaddq_f64(a, b); }
KAIRN_FORCEINLINE V sub(V a, V b) noexcept { return vsubq_f64(a, b); }
KAIRN_FORCEINLINE V mul(V a, V b) noexcept { return vmulq_f64(a, b); }
KAIRN_FORCEINLINE V fmadd(V a, V b, V c) noexcept { return vfmaq_f64(c, a, b); }
KAIRN_FORCEINLINE V vmin(V a, V b) noexcept { return vminq_f64(a, b); }
KAIRN_FORCEINLINE V vmax(V a, V b) noexcept { return vmaxq_f64(a, b); }
KAIRN_FORCEINLINE V neg(V a) noexcept { return vnegq_f64(a); }
KAIRN_FORCEINLINE V vabs(V a) noexcept { return vabsq_f64(a); }
KAIRN_FORCEINLINE V swap(V a) noexcept { return vextq_f64(a, a, 1); }
KAIRN_FORCEINLINE V dup0(V a) noexcept { return vdupq_laneq_f64(a, 0); }
KAIRN_FORCEINLINE V dup1(V a) noexcept { return vdupq_laneq_f64(a, 1); }
KAIRN_FORCEINLINE V blend(M m, V a, V b) noexcept { return vbslq_f64(m, a, b); }
KAIRN_FORCEINLINE V clear(M m, V a) noexcept { return vreinterpretq_f64_u64(vbicq_u64(ubits(a), m)); }
KAIRN_FORCEINLINE V flip(M m, V a) noexcept {
    return vreinterpretq_f64_u64(veorq_u64(ubits(a), vandq_u64(m, vdupq_n_u64(0x8000000000000000u))));
}
KAIRN_FORCEINLINE V nanify(M m, V a) noexcept { return vreinterpretq_f64_u64(vorrq_u64(ubits(a), m)); }
KAIRN_FORCEINLINE M mand(M a, M b) noexcept { return vandq_u64(a, b); }
KAIRN_FORCEINLINE M mor(M a, M b) noexcept { return vorrq_u64(a, b); }
KAIRN_FORCEINLINE M mswap(M a) noexcept { return vextq_u64(a, a, 1); }
KAIRN_FORCEINLINE M mdup0(M a) noexcept { return vdupq_laneq_u64(a, 0); }
KAIRN_FORCEINLINE M mdup1(M a) noexcept { return vdupq_laneq_u64(a, 1); }
// a <= 0: the sign bit set, or +0 (a NaN with the sign bit set too: only an empty operand has one).
KAIRN_FORCEINLINE M le0(V a) noexcept { return vclezq_s64(vreinterpretq_s64_f64(a)); }
// a < 0, except that -0 counts as negative: used only where both choices give the same values.
KAIRN_FORCEINLINE M lt0(V a) noexcept { return vcltzq_s64(vreinterpretq_s64_f64(a)); }
// The same bits (+0 and -0 differ: used only where either answer gives the same values).
KAIRN_FORCEINLINE M eq(V a, V b) noexcept { return vceqq_u64(ubits(a), ubits(b)); }
KAIRN_FORCEINLINE uint64x2_t abits(V a) noexcept { return vandq_u64(ubits(a), vdupq_n_u64(0x7fffffffffffffffu)); }
KAIRN_FORCEINLINE M isnan(V a) noexcept { return vcgtq_u64(abits(a), vdupq_n_u64(0x7ff0000000000000u)); }
KAIRN_FORCEINLINE M ispinf(V a) noexcept { return vceqq_u64(ubits(a), vdupq_n_u64(0x7ff0000000000000u)); }
KAIRN_FORCEINLINE M big(V a) noexcept { return vcgeq_u64(abits(a), vdupq_n_u64(0x7fefffffffffffffu)); }
KAIRN_FORCEINLINE M nonfinite(V a) noexcept { return vcgeq_u64(abits(a), vdupq_n_u64(0x7ff0000000000000u)); }
KAIRN_FORCEINLINE M mall() noexcept { return vdupq_n_u64(~std::uint64_t{0}); }
KAIRN_FORCEINLINE M mlane1() noexcept { return vcombine_u64(vcreate_u64(0), vcreate_u64(~std::uint64_t{0})); }
KAIRN_FORCEINLINE int bits(M m) noexcept {
    return int(vgetq_lane_u64(m, 0) & 1u) | int(vgetq_lane_u64(m, 1) & 2u);
}
KAIRN_FORCEINLINE bool any(M m) noexcept { return vmaxvq_u32(vreinterpretq_u32_u64(m)) != 0; }
KAIRN_FORCEINLINE void bar(V& v) noexcept { KAIRN_DETAIL_UPWARD_BARRIER(v); }
KAIRN_FORCEINLINE void pin(V& v) noexcept { KAIRN_DETAIL_UPWARD_PIN(v); }
KAIRN_FORCEINLINE V vload(const double* p) noexcept { return vld1q_f64(p); }
KAIRN_FORCEINLINE void vstore(double* p, V v) noexcept { vst1q_f64(p, v); }
#else
KAIRN_FORCEINLINE V vset(double a) noexcept { return {a, a}; }
KAIRN_FORCEINLINE V vmake(double a0, double a1) noexcept { return {a0, a1}; }
KAIRN_FORCEINLINE V vzero() noexcept { return {0.0, 0.0}; }
KAIRN_FORCEINLINE double lane0(V a) noexcept { return a.v0; }
KAIRN_FORCEINLINE double lane1(V a) noexcept { return a.v1; }
KAIRN_FORCEINLINE V add(V a, V b) noexcept { return {a.v0 + b.v0, a.v1 + b.v1}; }
KAIRN_FORCEINLINE V sub(V a, V b) noexcept { return {a.v0 - b.v0, a.v1 - b.v1}; }
KAIRN_FORCEINLINE V mul(V a, V b) noexcept { return {a.v0 * b.v0, a.v1 * b.v1}; }
KAIRN_FORCEINLINE V fmadd(V a, V b, V c) noexcept { return {std::fma(a.v0, b.v0, c.v0), std::fma(a.v1, b.v1, c.v1)}; }
KAIRN_FORCEINLINE V vmin(V a, V b) noexcept { return {b.v0 < a.v0 ? b.v0 : a.v0, b.v1 < a.v1 ? b.v1 : a.v1}; }
KAIRN_FORCEINLINE V vmax(V a, V b) noexcept { return {a.v0 > b.v0 ? a.v0 : b.v0, a.v1 > b.v1 ? a.v1 : b.v1}; }
KAIRN_FORCEINLINE V neg(V a) noexcept { return {-a.v0, -a.v1}; }
KAIRN_FORCEINLINE V vabs(V a) noexcept { return {std::fabs(a.v0), std::fabs(a.v1)}; }
KAIRN_FORCEINLINE V swap(V a) noexcept { return {a.v1, a.v0}; }
KAIRN_FORCEINLINE V dup0(V a) noexcept { return {a.v0, a.v0}; }
KAIRN_FORCEINLINE V dup1(V a) noexcept { return {a.v1, a.v1}; }
KAIRN_FORCEINLINE V blend(M m, V a, V b) noexcept { return {m.m0 ? a.v0 : b.v0, m.m1 ? a.v1 : b.v1}; }
KAIRN_FORCEINLINE V clear(M m, V a) noexcept { return {m.m0 ? 0.0 : a.v0, m.m1 ? 0.0 : a.v1}; }
KAIRN_FORCEINLINE V flip(M m, V a) noexcept { return {m.m0 ? -a.v0 : a.v0, m.m1 ? -a.v1 : a.v1}; }
KAIRN_FORCEINLINE V nanify(M m, V a) noexcept {
    constexpr double nan = std::numeric_limits<double>::quiet_NaN();
    return {m.m0 ? nan : a.v0, m.m1 ? nan : a.v1};
}
KAIRN_FORCEINLINE M mand(M a, M b) noexcept { return {a.m0 && b.m0, a.m1 && b.m1}; }
KAIRN_FORCEINLINE M mor(M a, M b) noexcept { return {a.m0 || b.m0, a.m1 || b.m1}; }
KAIRN_FORCEINLINE M mswap(M a) noexcept { return {a.m1, a.m0}; }
KAIRN_FORCEINLINE M mdup0(M a) noexcept { return {a.m0, a.m0}; }
KAIRN_FORCEINLINE M mdup1(M a) noexcept { return {a.m1, a.m1}; }
KAIRN_FORCEINLINE M le0(V a) noexcept { return {a.v0 <= 0, a.v1 <= 0}; }
KAIRN_FORCEINLINE M lt0(V a) noexcept { return {a.v0 < 0, a.v1 < 0}; }
KAIRN_FORCEINLINE M eq(V a, V b) noexcept { return {a.v0 == b.v0, a.v1 == b.v1}; }
KAIRN_FORCEINLINE M isnan(V a) noexcept { return {a.v0 != a.v0, a.v1 != a.v1}; }
KAIRN_FORCEINLINE M ispinf(V a) noexcept { return {a.v0 == kInf, a.v1 == kInf}; }
KAIRN_FORCEINLINE M big(V a) noexcept { return {!(std::fabs(a.v0) < kMax), !(std::fabs(a.v1) < kMax)}; }
KAIRN_FORCEINLINE M nonfinite(V a) noexcept { return {!(std::fabs(a.v0) < kInf), !(std::fabs(a.v1) < kInf)}; }
KAIRN_FORCEINLINE M mall() noexcept { return {true, true}; }
KAIRN_FORCEINLINE M mlane1() noexcept { return {false, true}; }
KAIRN_FORCEINLINE int bits(M m) noexcept { return int(m.m0) | (int(m.m1) << 1); }
KAIRN_FORCEINLINE bool any(M m) noexcept { return m.m0 || m.m1; }
KAIRN_FORCEINLINE void bar(V& v) noexcept {
    KAIRN_DETAIL_UPWARD_BARRIER(v.v0);
    KAIRN_DETAIL_UPWARD_BARRIER(v.v1);
}
KAIRN_FORCEINLINE void pin(V& v) noexcept {
    KAIRN_DETAIL_UPWARD_PIN(v.v0);
    KAIRN_DETAIL_UPWARD_PIN(v.v1);
}
KAIRN_FORCEINLINE V vload(const double* p) noexcept { return {p[0], p[1]}; }
KAIRN_FORCEINLINE void vstore(double* p, V v) noexcept {
    p[0] = v.v0;
    p[1] = v.v1;
}
#endif

#if KAIRN_UPWARD2_AVX2
// The same operations on four lanes (the functions on arrays: one element per lane).
using V4 = __m256d;
KAIRN_FORCEINLINE V4 vset4(double a) noexcept { return _mm256_set1_pd(a); }
KAIRN_FORCEINLINE V4 add(V4 a, V4 b) noexcept { return _mm256_add_pd(a, b); }
KAIRN_FORCEINLINE V4 sub(V4 a, V4 b) noexcept { return _mm256_sub_pd(a, b); }
KAIRN_FORCEINLINE V4 mul(V4 a, V4 b) noexcept { return _mm256_mul_pd(a, b); }
KAIRN_FORCEINLINE V4 fmadd(V4 a, V4 b, V4 c) noexcept { return _mm256_fmadd_pd(a, b, c); }
KAIRN_FORCEINLINE V4 vmin(V4 a, V4 b) noexcept { return _mm256_min_pd(a, b); }
KAIRN_FORCEINLINE V4 vmax(V4 a, V4 b) noexcept { return _mm256_max_pd(a, b); }
KAIRN_FORCEINLINE V4 neg(V4 a) noexcept { return _mm256_xor_pd(a, _mm256_set1_pd(-0.0)); }
KAIRN_FORCEINLINE V4 vabs(V4 a) noexcept { return _mm256_andnot_pd(_mm256_set1_pd(-0.0), a); }
KAIRN_FORCEINLINE V4 blend(V4 m, V4 a, V4 b) noexcept { return _mm256_blendv_pd(b, a, m); }
KAIRN_FORCEINLINE V4 clear(V4 m, V4 a) noexcept { return _mm256_andnot_pd(m, a); }
KAIRN_FORCEINLINE V4 flip(V4 m, V4 a) noexcept { return _mm256_xor_pd(a, _mm256_and_pd(m, _mm256_set1_pd(-0.0))); }
KAIRN_FORCEINLINE V4 mand(V4 a, V4 b) noexcept { return _mm256_and_pd(a, b); }
KAIRN_FORCEINLINE V4 mor(V4 a, V4 b) noexcept { return _mm256_or_pd(a, b); }
KAIRN_FORCEINLINE V4 le0(V4 a) noexcept { return _mm256_cmp_pd(a, _mm256_setzero_pd(), _CMP_LE_OQ); }
KAIRN_FORCEINLINE V4 lt0(V4 a) noexcept { return _mm256_cmp_pd(a, _mm256_setzero_pd(), _CMP_LT_OQ); }
KAIRN_FORCEINLINE V4 eq(V4 a, V4 b) noexcept { return _mm256_cmp_pd(a, b, _CMP_EQ_OQ); }
KAIRN_FORCEINLINE V4 ispinf(V4 a) noexcept { return _mm256_cmp_pd(a, _mm256_set1_pd(kInf), _CMP_EQ_OQ); }
KAIRN_FORCEINLINE V4 big(V4 a) noexcept { return _mm256_cmp_pd(vabs(a), _mm256_set1_pd(kMax), _CMP_NLT_UQ); }
KAIRN_FORCEINLINE bool any(V4 m) noexcept { return _mm256_movemask_pd(m) != 0; }
KAIRN_FORCEINLINE void bar(V4& v) noexcept { KAIRN_DETAIL_UPWARD_BARRIER(v); }
KAIRN_FORCEINLINE void pin(V4& v) noexcept { KAIRN_DETAIL_UPWARD_PIN(v); }
#endif

// The barriers of a kernel (docs/developer/design/upward.md, "Barriers"): on each register of its
// inputs, the first one pinned, and on each register of its result, so that nothing of the program
// is fused into it, folded at compile time, merged across a change of mode, or moved across a scope.
KAIRN_FORCEINLINE void pin(R& x) noexcept {
    pin(x.h);
    pin(x.l);
}
KAIRN_FORCEINLINE void bar(R& x) noexcept {
    bar(x.h);
    bar(x.l);
}

// The assertion of a checked build, as kairn/upward.hpp makes it before each operation that rounds.
KAIRN_FORCEINLINE void check_mode() noexcept { (void)::kairn::upward::detail::check_upward(); }

// --- The two building blocks of sums, under the mode upward ------------------------------------------

// two_sum(a, b) -> (s, t) with s + t >= a + b, for any numbers a, b with no overflow; t is the
// error a + b - s rounded up, so (s, t) is upper-normalized.
//
// Why: s = RU(a + b). For the operand of larger magnitude, say |a| >= |b|, s - a is exact (the
// first two operations of Fast2Sum are exact in every rounding mode when |a| >= |b|: Boldo,
// Graillat and Muller, "On the robustness of the 2Sum and Fast2Sum algorithms", ACM TOMS 2017;
// relied on, not reproved here), so t1 = RU(RU(a - s) + b) = RU(a + b - s). For the other order,
// RU(b - s) >= b - s and then t2 = RU(RU(b - s) + a) >= a + b - s: a rounding up only increases. So
// both are numbers >= the error a + b - s, one of them is RU(error), the least such number, and the
// smaller of the two is therefore RU(error) whichever operand is larger: no comparison of
// magnitudes is needed, and the result holds even if the lemma above failed (then only the
// normalization could be lost, never the bound). The error of a sum under a directed mode is not
// always a number of the format (t is its rounding up), and the branch-free 2Sum of six operations
// does not give an upper bound of it in general: neither is used.
// (These building blocks are templates on the register: V, or four lanes for the arrays.)
template <class P>
KAIRN_FORCEINLINE void two_sum(P a, P b, P& s, P& t) noexcept {
    s = add(a, b);
    const P t1 = add(sub(a, s), b);
    const P t2 = add(sub(b, s), a);
    t = vmin(t1, t2);
}

// fast_two_sum(a, b) -> (s, t) with s + t >= a + b for any a, b (t = RU(RU(a - s) + b), as t1
// above: always an upper bound of the error); t is RU(error) when |a| >= |b|, by the lemma above.
// Used only where |a| >= |b| is argued at the call.
template <class P>
KAIRN_FORCEINLINE void fast_two_sum(P a, P b, P& s, P& t) noexcept {
    s = add(a, b);
    t = add(sub(a, s), b);
}

// two_sum_nonpos(a, b): two_sum for operands that are not positive (the second limbs of
// upper-normalized pairs): the smaller of the two is then the larger in magnitude, so
// fast_two_sum(min, max) is exact by the same lemma, in five operations instead of six. For any
// operands it is still an upper pair of a + b (see fast_two_sum); only the exactness, the
// normalization of the result, depends on the signs.
template <class P>
KAIRN_FORCEINLINE void two_sum_nonpos(P a, P b, P& s, P& t) noexcept { fast_two_sum(vmin(a, b), vmax(a, b), s, t); }

// --- The product of two pairs -------------------------------------------------------------------------

// pair_mul(P, Q) -> p, (zh, zl): lane by lane, zh + zl >= (Ph + Pl)(Qh + Ql), with p = RU(Ph Qh) the
// leading product (the caller checks it: the fast path holds only for |p| < MAX).
//
// Why, lane by lane, when Ph, Qh, Pl, Ql are finite and |p| < MAX:
// - p = RU(Ph Qh);
// - e = RU(Ph Qh - p), one fused operation: the error of a product is a number of the format when
//   nothing underflows, so e is it exactly; when it underflows, the fused operation rounded up is
//   still at least it: e >= Ph Qh - p in every case;
// - c = RU(Ph Ql + RU(Pl Qh + RU(Pl Ql))) >= Ph Ql + Pl Qh + Pl Ql: each fused operation rounded up;
// - w = RU(e + c) >= e + c, so p + w >= Ph Qh + Ph Ql + Pl Qh + Pl Ql = P Q;
// - (zh, zl) = fast_two_sum(p, w): zh + zl >= p + w. Its order |p| >= |w| holds for operands that
//   are upper-normalized: |Pl| < 2^-52 |Ph| and |Ql| < 2^-52 |Qh| for normal heads, so |c| is about
//   3 2^-52 |p| at most, |e| <= ulp(p), and |w| < |p| / 2 when p is normal (with a margin of about
//   2^50); when p is subnormal every term is a multiple of the smallest subnormal and p + w, below
//   2^-1021 in magnitude, is computed exactly (then zl = 0). So (zh, zl) is upper-normalized, which
//   the lexicographic maximum of candidates (lexmax) needs.
// The negation of p is exact (rule U3 of the design page is about negating a rounded result in
// place of the rounding of a negation; here the exact negation of p is what is meant, and a fused
// a b - p is the same operation whatever instruction computes it).
template <class P>
KAIRN_FORCEINLINE void pair_mul(P ph, P pl, P qh, P ql, P& p, P& zh, P& zl) noexcept {
    p = mul(ph, qh);
    const P e = fmadd(ph, qh, neg(p));
    const P c = fmadd(ph, ql, fmadd(pl, qh, mul(pl, ql)));
    const P w = add(e, c);
    fast_two_sum(p, w, zh, zl);
}

// The greater of two upper-normalized pairs, lane by lane: their values are ordered as (h, l)
// lexicographically (an upper-normalized pair's value is in (pred(h), h]), so the result is one of
// the two pairs, exactly. Written with the maximum and an equality, not an ordering comparison (on
// AArch64 eq tests the bits, so heads +0 and -0 count as different: either pair then has value 0).
template <class P>
KAIRN_FORCEINLINE void lexmax(P ah, P al, P bh, P bl, P& mh, P& ml) noexcept {
    mh = vmax(ah, bh);
    const auto ea = eq(mh, ah), eb = eq(mh, bh);
    ml = blend(mand(ea, eb), vmax(al, bl), blend(ea, al, bl));
}

// --- The specials of a candidate product (the slow path) ---------------------------------------------
//
// A candidate of a product of bounds, as Interval<double, 2> (mul_ext_2_2) answers it: 0 times an
// infinity is 0; an infinite factor gives the IEEE product of the heads, (+-inf, 0); otherwise the
// pair of pair_mul, with a head that reaches +inf (an overflow upward) or +-MAX given a zero second
// limb ((h, 0) >= h + l since l <= 0; a head -MAX stands for a value <= -MAX, of which -MAX is an
// upper bound). p is NaN exactly for 0 times an infinity (or an empty operand, handled by the
// caller), +-inf exactly for an infinite factor or an overflow upward.
KAIRN_FORCEINLINE void special_candidate(V ph, V pl, V qh, V ql, V& zh, V& zl) noexcept {
    V p;
    pair_mul(ph, pl, qh, ql, p, zh, zl);
    const M nf = nonfinite(p);
    zh = blend(nf, clear(isnan(p), p), zh);
    zl = clear(mor(nf, big(zh)), zl);
}

// The product for any canonical operands: the eight products of bounds (four per lane, as the
// product of kairn::upward::Interval<double> pairs them), each with its specials, the greatest per
// lane, and the empty set where an operand is empty. With x = (xu, xn) = (b, -a), y = (d, -c):
//   Q1 = x       * dup0(y)   lanes (bd, -ad)
//   Q2 = swap(x) * dup1(y)   lanes (ac, -bc)
//   Q3 = swap(x) * dup0(-y)  lanes (ad, -bd)
//   Q4 = x       * dup1(-y)  lanes (bc, -ac)
// so lane 0 holds upper pairs of the four products and lane 1 upper pairs of their negations; the
// greatest of upper pairs of candidates is an upper pair of the greatest candidate.
KAIRN_DETAIL_COLD R mul_special(R x, R y) noexcept {
    V nyh = neg(y.h), nyl = neg(y.l);
    bar(nyh);
    bar(nyl);
    const V sxh = swap(x.h), sxl = swap(x.l);
    V h1, l1, h2, l2, h3, l3, h4, l4;
    special_candidate(x.h, x.l, dup0(y.h), dup0(y.l), h1, l1);
    special_candidate(sxh, sxl, dup1(y.h), dup1(y.l), h2, l2);
    special_candidate(sxh, sxl, dup0(nyh), dup0(nyl), h3, l3);
    special_candidate(x.h, x.l, dup1(nyh), dup1(nyl), h4, l4);
    V ah, al, bh, bl, zh, zl;
    lexmax(h1, l1, h2, l2, ah, al);
    lexmax(h3, l3, h4, l4, bh, bl);
    lexmax(ah, al, bh, bl, zh, zl);
    const M e = mor(isnan(x.h), isnan(y.h));   // canonical: both lanes of an empty set are NaN
    return R{nanify(e, zh), nanify(e, zl)};
}

// --- The product: the form "branch" -------------------------------------------------------------------
//
// One candidate per lane chosen by branches on the signs of the bounds (two in the case where both
// operands contain zero), computed by pair_mul on a fast path that checks that every leading product
// p computed is finite with |p| < MAX; otherwise (an empty or unbounded operand, 0 times an infinity,
// an overflow, a head +-MAX) it returns mul_special, which is right for every canonical operand. On
// the fast path every operand is finite and nothing overflows, so pair_mul's argument holds and the
// candidates are upper-normalized. The forms measured against it (eight candidates; two per lane by
// blends, in two or four lanes; one per lane by a table of permutations) are in upward2_forms.hpp,
// and the README gives their times: this one was the fastest but where the signs are random and the
// products independent, on Zen 2.

// Forms "table" and "branch": one candidate per lane, its operands chosen by the case of the signs,
// except when both operands contain zero in their interior (two per lane, as sel2 has them there).
// x's case: bit 0 b <= 0, bit 1 a >= 0 (both: x = [0, 0], taken as a >= 0); y's: bit 0 d <= 0, bit 1
// c >= 0 (both taken as c >= 0). Lane 0 computes the upper bound, lane 1 the negated lower one; P
// takes lane i of x (0 = xu = b, 1 = xn = -a), Q lane j of y (0 = yu = d, 1 = yn = -c), negated
// where s is set:
//   x >= 0, y >= 0: (b d, -a c) = (xu yu, xn (-yn))        P (0, 1) Q (0, 1) s (0, 1)
//   x >= 0, y <= 0: (a d, -b c) = (xn (-yu), xu yn)        P (1, 0) Q (0, 1) s (1, 0)
//   x >= 0, y ∋ 0:  (b d, -b c) = (xu yu, xu yn)           P (0, 0) Q (0, 1) s (0, 0)
//   x <= 0, y >= 0: (b c, -a d) = (xu (-yn), xn yu)        P (0, 1) Q (1, 0) s (1, 0)
//   x <= 0, y <= 0: (a c, -b d) = (xn yn, xu (-yu))        P (1, 0) Q (1, 0) s (0, 1)
//   x <= 0, y ∋ 0:  (a c, -a d) = (xn yn, xn yu)           P (1, 1) Q (1, 0) s (0, 0)
//   x ∋ 0, y >= 0:  (b d, -a d) = (xu yu, xn yu)           P (0, 1) Q (0, 0) s (0, 0)
//   x ∋ 0, y <= 0:  (a c, -b c) = (xn yn, xu yn)           P (1, 0) Q (1, 1) s (0, 0)
//   x ∋ 0, y ∋ 0:   max of (xn, xn) (yn, yu) and (xu, xu) (yu, yn)
// Each line is the classical case table of interval multiplication.
struct Case {
    int p0, p1, q0, q1, s0, s1;
};
inline constexpr Case kCases[16] = {
    // index xc + 4 yc
    {-1, -1, -1, -1, 0, 0},   // x ∋ 0, y ∋ 0: two candidates
    {1, 1, 1, 0, 0, 0},       // x <= 0, y ∋ 0
    {0, 0, 0, 1, 0, 0},       // x >= 0, y ∋ 0
    {0, 0, 0, 1, 0, 0},       // x = 0, y ∋ 0 (as x >= 0)
    {1, 0, 1, 1, 0, 0},       // x ∋ 0, y <= 0
    {1, 0, 1, 0, 0, 1},       // x <= 0, y <= 0
    {1, 0, 0, 1, 1, 0},       // x >= 0, y <= 0
    {1, 0, 0, 1, 1, 0},       // x = 0, y <= 0
    {0, 1, 0, 0, 0, 0},       // x ∋ 0, y >= 0
    {0, 1, 1, 0, 1, 0},       // x <= 0, y >= 0
    {0, 1, 0, 1, 0, 1},       // x >= 0, y >= 0
    {0, 1, 0, 1, 0, 1},       // x = 0, y >= 0
    {0, 1, 0, 0, 0, 0},       // x ∋ 0, y = 0 (as y >= 0)
    {0, 1, 1, 0, 1, 0},       // x <= 0, y = 0
    {0, 1, 0, 1, 0, 1},       // x >= 0, y = 0
    {0, 1, 0, 1, 0, 1},       // x = 0, y = 0
};

// The two candidates of the case x ∋ 0, y ∋ 0.
KAIRN_FORCEINLINE R mul_zero_zero(R x, R y) noexcept {
    V p1, p2, ah, al, bh, bl;
    pair_mul(dup1(x.h), dup1(x.l), swap(y.h), swap(y.l), p1, ah, al);
    pair_mul(dup0(x.h), dup0(x.l), y.h, y.l, p2, bh, bl);
    if (any(mor(big(p1), big(p2)))) [[unlikely]]
        return mul_special(x, y);
    R z;
    lexmax(ah, al, bh, bl, z.h, z.l);
    return z;
}

KAIRN_FORCEINLINE R mul_one(const R& p, const R& q, const R& x, const R& y) noexcept {
    V pr, zh, zl;
    pair_mul(p.h, p.l, q.h, q.l, pr, zh, zl);
    if (any(big(pr))) [[unlikely]]
        return mul_special(x, y);
    return R{zh, zl};
}

// Form "branch": the same cases by branches, each with its own fixed lane moves.
template <int P0, int P1>
KAIRN_FORCEINLINE V lanes(V a) noexcept {
    if constexpr (P0 == 0 && P1 == 1) return a;
    else if constexpr (P0 == 1 && P1 == 0) return swap(a);
    else if constexpr (P0 == 0) return dup0(a);
    else return dup1(a);
}
template <int K>
KAIRN_FORCEINLINE R mul_case(R x, R y) noexcept {
    constexpr Case c = kCases[K];
    const R p{lanes<c.p0, c.p1>(x.h), lanes<c.p0, c.p1>(x.l)};
    R q{lanes<c.q0, c.q1>(y.h), lanes<c.q0, c.q1>(y.l)};
    if constexpr (c.s0 || c.s1) {
        const M s = c.s0 && c.s1 ? mall() : c.s1 ? mlane1() : mswap(mlane1());
        q = R{flip(s, q.h), flip(s, q.l)};
        bar(q);
    }
    return mul_one(p, q, x, y);
}
KAIRN_FORCEINLINE R mul_branch(R x, R y) noexcept {
    const bool xn = lane0(x.h) <= 0, xp = lane1(x.h) <= 0;   // b <= 0, a >= 0
    const bool yn = lane0(y.h) <= 0, yp = lane1(y.h) <= 0;   // d <= 0, c >= 0
    if (xp) {
        if (yp) return mul_case<10>(x, y);
        if (yn) return mul_case<6>(x, y);
        return mul_case<2>(x, y);
    }
    if (xn) {
        if (yp) return mul_case<9>(x, y);
        if (yn) return mul_case<5>(x, y);
        return mul_case<1>(x, y);
    }
    if (yp) return mul_case<8>(x, y);
    if (yn) return mul_case<4>(x, y);
    return mul_zero_zero(x, y);
}

// --- The kernels of the type ---------------------------------------------------------------------------

// The sum, in the form "accurate" (the type's): the two-limb sum of Joldes, Muller and Popescu
// (2017, AccurateDWPlusDW) with every two-sum the two_sum above, lane by lane:
//   (s, e) = two_sum(xh, yh)   s + e >= xh + yh
//   (t, f) = two_sum(xl, yl)   t + f >= xl + yl
//   c = RU(e + t)              c >= e + t
//   (v, g) = two_sum(s, c)     v + g >= s + c
//   w = RU(f + g)              w >= f + g
//   (zh, zl) = two_sum(v, w)   zh + zl >= v + w
// so zh + zl >= v + f + g >= s + c + f >= s + e + t + f >= xh + yh + xl + yl: each line replaces a
// term by a number at least it, and the last two-sum makes the pair upper-normalized. The second
// limbs' two-sum is two_sum_nonpos (they are not positive). The two later two-sums are not Fast2Sum:
// when the heads cancel, |c| can exceed |s|, and the order needed for exactness is not argued here
// (the form "lean" of upward2_forms.hpp uses fast_two_sum there; it stays an upper bound, see
// fast_two_sum, but whether its result is always upper-normalized is not argued). The specials: a
// head sum s = +inf (an unbounded operand, or an overflow) makes the bound +inf (the steps after it
// compute inf - inf); a head that reaches +-MAX gets a zero second limb (see special_candidate); an
// empty operand's NaN propagates to the heads. (The first two two-sums as one two-sum on the four
// lanes of an AVX2 register was measured slower on Zen 2, and dropped.)
KAIRN_FORCEINLINE void sum_specials(V s, V& zh, V& zl) noexcept {
    zh = blend(ispinf(s), vset(kInf), zh);
    zl = clear(big(zh), zl);
}
KAIRN_FORCEINLINE R add_r(R x, R y) noexcept {
    V s, e, t, f, v, g, zh, zl;
    two_sum(x.h, y.h, s, e);
    two_sum_nonpos(x.l, y.l, t, f);
    two_sum(s, add(e, t), v, g);
    two_sum(v, add(f, g), zh, zl);
    sum_specials(s, zh, zl);
    return R{zh, zl};
}

// -x: the two pairs exchanged (exact).
KAIRN_FORCEINLINE R neg_r(R x) noexcept { return R{swap(x.h), swap(x.l)}; }

// x + t for a number t: the sum with [t, t], whose pairs are (t, 0) and (-t, 0): the second limbs'
// sum is xl itself, exactly, and its error zero, so the accurate sum loses its fourth line and last
// two-sum ((v, g) is already upper-normalized). A t that is infinite or a NaN is the whole line, as
// Interval(t) makes it: the result is the whole line, or the empty set for an empty x.
KAIRN_FORCEINLINE R add_num_r(R x, double t) noexcept {
    V tt = vmake(t, -t);
    bar(tt);
    V s, e, zh, zl;
    two_sum(x.h, tt, s, e);
    two_sum(s, add(e, x.l), zh, zl);
    zh = blend(ispinf(s), vset(kInf), zh);
    zl = clear(big(zh), zl);
    if (!(std::fabs(t) < kInf)) [[unlikely]] {
        zh = add(x.h, vset(kInf));   // +inf, or NaN for an empty x
        zl = vzero();
    }
    return R{zh, zl};
}

// x * t for a number t: for t >= 0 the lanes are (xu t, xn t), for t < 0 (xn |t|, xu |t|): one pair
// product by (|t|, 0), with its cross term Pl |t| only (Ql = 0). The specials (an unbounded or empty
// x, an overflow, t infinite or a NaN, 0 times an infinity) go to the product with Interval(t).
KAIRN_FORCEINLINE R mul_by_interval(R x, double t) noexcept;
KAIRN_FORCEINLINE R mul_num_r(R x, double t) noexcept {
    const bool negative = t < 0;
    const R pr = negative ? R{swap(x.h), swap(x.l)} : x;
    V at = vset(std::fabs(t));
    bar(at);
    // pair_mul with Ql = 0: c = RU(Pl |t|).
    const V p = mul(pr.h, at);
    const V e = fmadd(pr.h, at, neg(p));
    const V w = add(e, mul(pr.l, at));
    V zh, zl;
    fast_two_sum(p, w, zh, zl);
    if (any(big(p))) [[unlikely]]   // also every t that is infinite or a NaN, and 0 times an infinity
        return mul_by_interval(x, t);
    return R{zh, zl};
}

// The square: x^2 = [min, max] of t^2 over x. Its upper bound is max(|a|, |b|)^2 = M M with M the
// greater of the pairs xu and xn as values (max(b, -a) = max(|a|, |b|) for every nonempty
// interval); its negated lower bound is -(a^2) = xn (-xn) when a >= 0, -(b^2) = xu (-xu) when b <= 0,
// and 0 when a < 0 < b. One pair product of (M, m) by (M, -m). The specials go to the product x x,
// which encloses the square (looser where x contains zero).
KAIRN_FORCEINLINE R sqr_r(R x) noexcept {
    V mh, ml;
    lexmax(x.h, x.l, swap(x.h), swap(x.l), mh, ml);   // both lanes: max(xu, xn)
    const M xle = le0(x.h);                            // lanes: b <= 0, a >= 0
    // Lane 1 of m: xn where a >= 0, else xu where b <= 0, else 0.
    const M ap = mdup1(xle), bn = mdup0(xle);
    // Lane 1 of x.h is xn and lane 1 of swap(x.h) is xu.
    const V sh = blend(ap, x.h, swap(x.h)), sl = blend(ap, x.l, swap(x.l));
    const M keep = mor(ap, bn);
    const M lane1 = mlane1();
    // P = (M, m), Q = (M, -m).
    const V ph = blend(lane1, blend(keep, sh, vzero()), mh);
    const V pl = blend(lane1, blend(keep, sl, vzero()), ml);
    V qh = flip(lane1, ph), ql = flip(lane1, pl);
    bar(qh);
    bar(ql);
    V p, zh, zl;
    pair_mul(ph, pl, qh, ql, p, zh, zl);
    if (any(big(p))) [[unlikely]]
        return mul_special(x, x);
    return R{zh, zl};
}

// The product of the type: the form "branch".
KAIRN_FORCEINLINE R mul_r(R x, R y) noexcept { return mul_branch(x, y); }

// The interval of a pair of numbers, as kairn's interval_make_2 on (lo, 0), (hi, 0): [lo, hi] when
// lo <= hi, lo < +inf and hi > -inf; the empty set when hi < lo; the whole line otherwise (a NaN, or
// the same infinity twice). Exact: a negation and selections.
KAIRN_FORCEINLINE R make_r(double lo, double hi) noexcept {
    constexpr double nan = std::numeric_limits<double>::quiet_NaN();
    if (lo <= hi && lo < kInf && hi > -kInf) return R{vmake(hi, -lo), vzero()};
    if (hi < lo) return R{vset(nan), vset(nan)};
    return R{vset(kInf), vzero()};
}

// From the default Interval<double, 2>'s limbs (l0, l1, h0, h1), canonical (each bound normalized
// to nearest: |x1| <= ulp(x0) / 2), under the mode upward: H = (h0, -l0), L = (h1, -l1) are exact
// upper pairs of hi and -lo, and fast_two_sum(H, L) (|H| >= |L| lane by lane) makes them
// upper-normalized with S + T >= H + L; T is the exact error rounded up. Specials: the empty set
// (+inf, -inf) gives the empty set; an infinite bound gives (+inf, 0); a finite bound whose
// upper-normalized form overflows (MAX with a positive second limb) becomes +inf, the only
// upper-normalized upper bound of it; a head +-MAX gets a zero second limb.
KAIRN_FORCEINLINE R from_limbs_r(double l0, double l1, double h0, double h1) noexcept {
    if (l0 == kInf) {   // the empty set
        constexpr double nan = std::numeric_limits<double>::quiet_NaN();
        return R{vset(nan), vset(nan)};
    }
    V h = vmake(h0, -l0), l = vmake(h1, -l1);
    pin(h);
    bar(l);
    V s, t;
    fast_two_sum(h, l, s, t);
    t = clear(big(s), t);
    R z{s, t};
    bar(z);
    return z;
}

// To the default Interval<double, 2>'s limbs (l0, l1, h0, h1), UNDER ROUNDING TO NEAREST (outside a
// Scope or inside a NearestScope): Fast2Sum rounded to nearest of each upper-normalized pair (h, l),
// |h| >= |l|, is exact, s + t = h + l, with s = RN(h + l) and |t| <= ulp(s) / 2: the bounds are the
// values of the pairs exactly, normalized as the default type needs them; no containment is lost.
// The lower bound is the negation (exact) of the pair of the negated lower bound. A head +inf gives
// (+inf, 0); the empty set gives (+inf, 0, -inf, 0).
KAIRN_FORCEINLINE void to_limbs_rn(R x, double* o) noexcept {
    if (lane0(x.h) != lane0(x.h)) {
        o[0] = kInf;
        o[1] = 0.0;
        o[2] = -kInf;
        o[3] = 0.0;
        return;
    }
    pin(x);
    const V s = add(x.h, x.l);
    V t = sub(x.l, sub(s, x.h));
    t = clear(nonfinite(s), t);
    V tb = t, sb = s;
    bar(tb);
    bar(sb);
    o[0] = -lane1(sb);
    o[1] = -lane1(tb) + 0.0;   // no -0 second limb from a zero one
    o[2] = lane0(sb);
    o[3] = lane0(tb) + 0.0;
}

}  // namespace
}  // namespace detail

/// The two-limb interval rounded upward (EXPERIMENTAL, NOT VERIFIED). Every operation that rounds
/// needs a kairn::upward::Scope around it; the members of the class are exact (constructors from
/// numbers, the limbs, predicates), the same in every mode and under every option.
class Interval {
public:
    /// [0, 0].
    Interval() noexcept : r_(R0(0.0, 0.0)) {}
    /// [t, t]; the whole line for an infinite t or a NaN (as kairn::Interval).
    explicit Interval(double t) noexcept : r_(R0(t, t)) {}
    /// [lo, hi]; the empty set when hi < lo; the whole line for a NaN or the same infinity twice.
    Interval(double lo, double hi) noexcept : r_(R0(lo, hi)) {}
    /// The empty set.
    static Interval empty() noexcept {
        constexpr double nan = std::numeric_limits<double>::quiet_NaN();
        return Interval(nan, nan, nan, nan, 0);
    }
    /// The whole line.
    static Interval whole() noexcept { return Interval(detail::kInf, detail::kInf, 0.0, 0.0, 0); }
    /// The interval of the stored numbers p[0..3] = (uh, nh, ul, nl): a canonical state as an
    /// operation returns it (not checked).
    static Interval from_limbs(const double* p) noexcept { return Interval(p[0], p[1], p[2], p[3], 0); }
    /// Writes (uh, nh, ul, nl).
    void to_limbs(double* p) const noexcept {
        detail::vstore(p, r_.h);
        detail::vstore(p + 2, r_.l);
    }
    bool is_empty() const noexcept { return detail::lane0(r_.h) != detail::lane0(r_.h); }
    /// The lower bound rounded down to a number (-nh = RD(lower bound): exact, upper-normalization makes
    /// nh the negated lower bound rounded up); -inf when unbounded below; +inf for the empty set (as
    /// kairn::Interval<double, 1>::lower()).
    double lower() const noexcept { return is_empty() ? detail::kInf : -detail::lane1(r_.h); }
    /// The upper bound rounded up to a number (uh); +inf when unbounded above; -inf for the empty set.
    double upper() const noexcept { return is_empty() ? -detail::kInf : detail::lane0(r_.h); }
    /// Every member is > 0 (nh < 0: upper-normalization makes the sign of nh that of the negated bound).
    bool certainly_positive() const noexcept { return detail::lane1(r_.h) < 0; }
    /// Every member is < 0 (uh < 0).
    bool certainly_negative() const noexcept { return detail::lane0(r_.h) < 0; }
    /// Nonempty and 0 is a member (nh >= 0 and uh >= 0).
    bool contains_zero() const noexcept { return detail::lane1(r_.h) >= 0 && detail::lane0(r_.h) >= 0; }

    /// The registers (not part of an interface: for the kernels and the measurements).
    detail::R r_;
    explicit Interval(detail::R r) noexcept : r_(r) {}

private:
    Interval(double uh, double nh, double ul, double nl, int) noexcept {
        r_.h = detail::vmake(uh, nh);
        r_.l = detail::vmake(ul, nl);
    }
    static detail::R R0(double lo, double hi) noexcept {
        constexpr double nan = std::numeric_limits<double>::quiet_NaN();
        if (lo <= hi && lo < detail::kInf && hi > -detail::kInf)
            return detail::R{detail::vmake(hi, -lo + 0.0), detail::vmake(0.0, 0.0)};
        if (hi < lo) return detail::R{detail::vmake(nan, nan), detail::vmake(nan, nan)};
        return detail::R{detail::vmake(detail::kInf, detail::kInf), detail::vmake(0.0, 0.0)};
    }
};

// --- The operations (internal linkage; each needs a kairn::upward::Scope) -----------------------------
//
// Forced inline: GCC called the product otherwise (its kernels, forced inline into it, make it large).

/// x + y.
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator+(const Interval& x, const Interval& y) noexcept {
    detail::check_mode();
    detail::R a = x.r_, b = y.r_;
    detail::pin(a);
    detail::bar(b);
    detail::R z = detail::add_r(a, b);
    detail::bar(z);
    return Interval(z);
}
/// x - y: x + (-y), -y the two pairs of y exchanged.
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator-(const Interval& x, const Interval& y) noexcept {
    detail::check_mode();
    detail::R a = x.r_, b = y.r_;
    detail::pin(a);
    detail::bar(b);
    detail::R z = detail::add_r(a, detail::neg_r(b));
    detail::bar(z);
    return Interval(z);
}
/// -x (exact).
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator-(const Interval& x) noexcept { return Interval(detail::neg_r(x.r_)); }
/// x * y.
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator*(const Interval& x, const Interval& y) noexcept {
    detail::check_mode();
    detail::R a = x.r_, b = y.r_;
    detail::pin(a);
    detail::bar(b);
    detail::R z = detail::mul_r(a, b);
    detail::bar(z);
    return Interval(z);
}
/// x + t, t + x, x - t, t - x, x * t, t * x for a number t; an infinite t or a NaN is the whole line.
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator+(const Interval& x, double t) noexcept {
    detail::check_mode();
    detail::R a = x.r_;
    detail::pin(a);
    KAIRN_DETAIL_UPWARD_BARRIER(t);
    detail::R z = detail::add_num_r(a, t);
    detail::bar(z);
    return Interval(z);
}
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator+(double t, const Interval& x) noexcept { return x + t; }
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator-(const Interval& x, double t) noexcept { return x + (-t); }
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator-(double t, const Interval& x) noexcept { return (-x) + t; }
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator*(const Interval& x, double t) noexcept {
    detail::check_mode();
    detail::R a = x.r_;
    detail::pin(a);
    KAIRN_DETAIL_UPWARD_BARRIER(t);
    detail::R z = detail::mul_num_r(a, t);
    detail::bar(z);
    return Interval(z);
}
[[maybe_unused]] static KAIRN_FORCEINLINE Interval operator*(double t, const Interval& x) noexcept { return x * t; }
/// x^2 (the square, tighter than x * x where x contains zero).
[[maybe_unused]] static KAIRN_FORCEINLINE Interval sqr(const Interval& x) noexcept {
    detail::check_mode();
    detail::R a = x.r_;
    detail::pin(a);
    detail::R z = detail::sqr_r(a);
    detail::bar(z);
    return Interval(z);
}
[[maybe_unused]] static KAIRN_FORCEINLINE Interval& operator+=(Interval& x, const Interval& y) noexcept { return x = x + y; }
[[maybe_unused]] static KAIRN_FORCEINLINE Interval& operator-=(Interval& x, const Interval& y) noexcept { return x = x - y; }
[[maybe_unused]] static KAIRN_FORCEINLINE Interval& operator*=(Interval& x, const Interval& y) noexcept { return x = x * y; }

/// From the default Interval<double, 2>, under the mode upward (inside a Scope): the same set, its
/// bounds upper-normalized (see detail::from_limbs_r: a bound MAX with a positive second limb
/// becomes infinite, and a bound +-MAX loses its second limb).
[[maybe_unused]] static KAIRN_FORCEINLINE Interval from_interval(const ::kairn::Interval<double, 2>& x) noexcept {
    detail::check_mode();
    return Interval(detail::from_limbs_r(x.lower().limb[0], x.lower().limb[1], x.upper().limb[0],
                                         x.upper().limb[1]));
}
/// To the default Interval<double, 2>, UNDER ROUNDING TO NEAREST (outside a Scope, or inside a
/// kairn::upward::NearestScope): the same bounds exactly (see detail::to_limbs_rn).
[[maybe_unused]] static KAIRN_FORCEINLINE ::kairn::Interval<double, 2> to_interval(const Interval& x) noexcept {
    double o[4];
    detail::to_limbs_rn(x.r_, o);
    return ::kairn::Interval<double, 2>::from_limbs(o);
}

/// The width hi - lo rounded up to a number, under the mode upward (inside a Scope): the head of the
/// sum of the two pairs, U + N, by the type's sum (its head is the sum rounded up, the sum's excess
/// relative to the width itself, the accurate sum's property); +inf for an unbounded interval, NaN for
/// the empty set.
[[maybe_unused]] static KAIRN_FORCEINLINE double width(const Interval& x) noexcept {
    detail::check_mode();
    detail::R a = x.r_;
    detail::pin(a);
    detail::R z = detail::add_r(a, detail::neg_r(a));   // lane 0: U + N
    detail::bar(z);
    return detail::lane0(z.h);
}
/// The radius (hi - lo) / 2 rounded up to a number, under the mode upward: width(x) * 0.5 rounded up.
[[maybe_unused]] static KAIRN_FORCEINLINE double radius(const Interval& x) noexcept {
    double w = width(x);
    KAIRN_DETAIL_UPWARD_BARRIER(w);
    double r = w * 0.5;
    KAIRN_DETAIL_UPWARD_BARRIER(r);
    return r;
}
/// From kairn::upward::Interval<double>: (u, 0), (n, 0), exact. Any rounding mode.
[[maybe_unused]] static KAIRN_FORCEINLINE Interval from_upward1(const ::kairn::upward::Interval<double>& x) noexcept {
    double p[2];
    x.to_limbs(p);
    const double q[4] = {p[0], p[1], p[0] != p[0] ? p[0] : 0.0, p[1] != p[1] ? p[1] : 0.0};
    return Interval::from_limbs(q);
}
/// To kairn::upward::Interval<double>: (uh, nh), the heads (uh >= the upper bound, nh >= the negated
/// lower bound, and the tightest such numbers). Exact moves; any rounding mode.
[[maybe_unused]] static KAIRN_FORCEINLINE ::kairn::upward::Interval<double> to_upward1(const Interval& x) noexcept {
    double p[2] = {detail::lane0(x.r_.h), detail::lane1(x.r_.h)};
    return ::kairn::upward::Interval<double>::from_limbs(p);
}

namespace detail {
namespace {
KAIRN_FORCEINLINE R mul_by_interval(R x, double t) noexcept { return mul_special(x, Interval(t).r_); }
}  // namespace
}  // namespace detail

}  // namespace kairn::experimental::upward2
