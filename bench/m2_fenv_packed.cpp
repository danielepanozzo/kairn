// Measurement props: the classical directed rounding in packed code, the rounding mode changed once
// around a whole loop of packed operations (m2_fenv.cpp says how the compilers are made to honor
// it, and this file is compiled the same way, with AVX2 and FMA on x86-64). Backend m2p, variant
// fenv_loop, binary64, one array per limb; checked against the generated scalar kernel (m2s) before
// it is timed. Does not include Kairn: the register operations are spelled here.
#include <cfenv>

#include "m2_data.hpp"

#if defined(__clang__)
#pragma STDC FENV_ACCESS ON
#elif defined(_MSC_VER)
#pragma fenv_access(on)
#endif

using kairn_bench::m2::Entry;

#if (defined(__AVX2__) && defined(__FMA__)) || defined(__aarch64__)
#define KB_FPACKED 1

#if defined(__AVX2__)
#include <immintrin.h>
#else
#include <arm_neon.h>
#endif

namespace {
using kairn_bench::m2::kN;
using kairn_bench::m2::Raw;
using namespace kairn_bench::m2;   // the regions

#if defined(__AVX2__)
using V = __m256d;
constexpr int W = 4;
inline V load(const double* p) { return _mm256_loadu_pd(p); }
inline void store(double* p, V v) { _mm256_storeu_pd(p, v); }
inline V add(V a, V b) { return _mm256_add_pd(a, b); }
inline V mul(V a, V b) { return _mm256_mul_pd(a, b); }
inline V neg(V a) { return _mm256_xor_pd(a, _mm256_set1_pd(-0.0)); }
inline V max(V a, V b) { return _mm256_max_pd(a, b); }
#else
using V = float64x2_t;
constexpr int W = 2;
inline V load(const double* p) { return vld1q_f64(p); }
inline void store(double* p, V v) { vst1q_f64(p, v); }
inline V add(V a, V b) { return vaddq_f64(a, b); }
inline V mul(V a, V b) { return vmulq_f64(a, b); }
inline V neg(V a) { return vnegq_f64(a); }
inline V max(V a, V b) { return vmaxq_f64(a, b); }
#endif
inline V max4(V a, V b, V c, V d) { return max(max(a, b), max(c, d)); }
}  // namespace

#define KB_FPEACH(MODE, ...)                                                                       \
    std::fesetround(MODE);                                                                         \
    for (int i = 0; i < kN; i += W) {                                                              \
        __VA_ARGS__;                                                                               \
    }                                                                                              \
    std::fesetround(FE_TONEAREST);
#define L(A) load(&(A)[i])

#define KB_FPLIST(X)                                                                               \
    X(tp, add_down_1, 1, FE_DOWNWARD, store(&r.sout[0][i], add(L(r.xa), L(r.ya))))                \
    X(tp, mul_down_1, 1, FE_DOWNWARD, store(&r.sout[0][i], mul(L(r.xa), L(r.ya))))                \
    X(tp, interval_add_1, 2, FE_UPWARD, const V xl = L(r.sxi[0]); const V xu = L(r.sxi[1]);        \
      const V yl = L(r.syi[0]); const V yu = L(r.syi[1]);                                          \
      store(&r.sout[0][i], neg(add(neg(xl), neg(yl)))); store(&r.sout[1][i], add(xu, yu)))         \
    X(tp, interval_mul_1, 2, FE_UPWARD, const V xl = L(r.sxi[0]); const V xu = L(r.sxi[1]);        \
      const V yl = L(r.syi[0]); const V yu = L(r.syi[1]); const V nl = neg(xl); const V nu = neg(xu); \
      store(&r.sout[0][i], neg(max4(mul(nl, yl), mul(nl, yu), mul(nu, yl), mul(nu, yu))));         \
      store(&r.sout[1][i], max4(mul(xl, yl), mul(xl, yu), mul(xu, yl), mul(xu, yu))))

#define KB_FPDEF(KIND, KERNEL, OUTS, MODE, ...)                                                    \
    extern "C" KB_NOINLINE void kb_m2_p64_##KIND##_##KERNEL##__fenv_loop(void* kb_data) {                \
        Raw<double>& r = *static_cast<Raw<double>*>(kb_data);                                            \
        KB_FPEACH(MODE, __VA_ARGS__)                                                               \
    }
#define KB_FPROW(KIND, KERNEL, OUTS, MODE, ...)                                                    \
    {"m2p/" #KIND "/" #KERNEL "/fenv_loop", kb_m2_p64_##KIND##_##KERNEL##__fenv_loop, 64, W, kN, R_SOUT, OUTS * kN, nullptr},

KB_FPLIST(KB_FPDEF)

namespace kairn_bench::m2 {
const Entry m2_fenv_packed_entries[] = {
    KB_FPLIST(KB_FPROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
}  // namespace kairn_bench::m2

#else

namespace kairn_bench::m2 {
const Entry m2_fenv_packed_entries[] = {{nullptr, nullptr, 0, 0, 0, 0, 0, nullptr}};
}  // namespace kairn_bench::m2

#endif
