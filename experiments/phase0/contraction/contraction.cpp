// Phase 0 experiment E1: what FMA contraction does to a double-double product.
//
// Each variant computes the same double-double product z = x*y (DWTimesDW3 of Joldes, Muller,
// Popescu 2017: TwoProd on the high parts, two FMAs for the cross terms, Fast2Sum). They differ
// only in how the high product p = RN(xh*yh) is written:
//
//   reference   every intermediate goes through a volatile, so no contraction is possible
//   textbook    p = xh * yh                      (a plain product that later feeds p + e, s - p)
//   opaque      p = fma(xh, yh, +0.0)            (an FMA result: nothing left to contract)
//   scoped      textbook + the compiler's scoped "contract off" switch, in an inline helper
//               called from a function without the switch (the shape header-only code has)
//   scopeddirect  the same switch, directly in the function that is compiled out of line
//   simd        textbook written with AVX2 / NEON intrinsics (lane 0 is reported)
//   simdopaque  opaque written with AVX2 / NEON intrinsics
//   opaqueintrin  opaque with the scalar FMA intrinsic instead of std::fma (x86 only)
//
// The program prints one line per (variant, case) in hex floats; check.py recomputes the exact
// product with rationals and reports, per variant, how many results differ from the reference
// bit for bit, the largest relative error in units of u^2 = 2^-106, and how many results break
// |zl| <= ulp(zh)/2.
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#if defined(_MSC_VER) && !defined(__clang__)
#define NOINLINE __declspec(noinline)
#else
#define NOINLINE __attribute__((noinline))
#endif

#if defined(__AVX2__)
#include <immintrin.h>
#elif defined(__aarch64__) || defined(_M_ARM64)
#include <arm_neon.h>
#endif

struct dd {
    double hi, lo;
};

NOINLINE dd mul_reference(dd x, dd y) {
    volatile double p = x.hi * y.hi;
    volatile double e = std::fma(x.hi, y.hi, -p);
    volatile double t0 = x.lo * y.lo;
    volatile double t1 = std::fma(x.hi, y.lo, t0);
    volatile double t2 = std::fma(x.lo, y.hi, t1);
    volatile double c = e + t2;
    volatile double s = p + c;
    volatile double z = s - p;
    volatile double l = c - z;
    return {s, l};
}

NOINLINE dd mul_textbook(dd x, dd y) {
    const double p = x.hi * y.hi;
    const double e = std::fma(x.hi, y.hi, -p);
    const double t0 = x.lo * y.lo;
    const double t1 = std::fma(x.hi, y.lo, t0);
    const double t2 = std::fma(x.lo, y.hi, t1);
    const double c = e + t2;
    const double s = p + c;
    const double z = s - p;
    const double l = c - z;
    return {s, l};
}

NOINLINE dd mul_opaque(dd x, dd y) {
    const double p = std::fma(x.hi, y.hi, 0.0);
    const double e = std::fma(x.hi, y.hi, -p);
    const double t0 = std::fma(x.lo, y.lo, 0.0);
    const double t1 = std::fma(x.hi, y.lo, t0);
    const double t2 = std::fma(x.lo, y.hi, t1);
    const double c = e + t2;
    const double s = p + c;
    const double z = s - p;
    const double l = c - z;
    return {s, l};
}

NOINLINE dd mul_simd(dd x, dd y) {
#if defined(__AVX2__)
    const __m256d xh = _mm256_set1_pd(x.hi), xl = _mm256_set1_pd(x.lo);
    const __m256d yh = _mm256_set1_pd(y.hi), yl = _mm256_set1_pd(y.lo);
    const __m256d p = _mm256_mul_pd(xh, yh);
    const __m256d e = _mm256_fmsub_pd(xh, yh, p);
    const __m256d t0 = _mm256_mul_pd(xl, yl);
    const __m256d t1 = _mm256_fmadd_pd(xh, yl, t0);
    const __m256d t2 = _mm256_fmadd_pd(xl, yh, t1);
    const __m256d c = _mm256_add_pd(e, t2);
    const __m256d s = _mm256_add_pd(p, c);
    const __m256d z = _mm256_sub_pd(s, p);
    const __m256d l = _mm256_sub_pd(c, z);
    return {_mm256_cvtsd_f64(s), _mm256_cvtsd_f64(l)};
#elif defined(__aarch64__) || defined(_M_ARM64)
    const float64x2_t xh = vdupq_n_f64(x.hi), xl = vdupq_n_f64(x.lo);
    const float64x2_t yh = vdupq_n_f64(y.hi), yl = vdupq_n_f64(y.lo);
    const float64x2_t p = vmulq_f64(xh, yh);
    const float64x2_t e = vfmaq_f64(vnegq_f64(p), xh, yh);
    const float64x2_t t0 = vmulq_f64(xl, yl);
    const float64x2_t t1 = vfmaq_f64(t0, xh, yl);
    const float64x2_t t2 = vfmaq_f64(t1, xl, yh);
    const float64x2_t c = vaddq_f64(e, t2);
    const float64x2_t s = vaddq_f64(p, c);
    const float64x2_t z = vsubq_f64(s, p);
    const float64x2_t l = vsubq_f64(c, z);
    return {vgetq_lane_f64(s, 0), vgetq_lane_f64(l, 0)};
#else
    return mul_reference(x, y);
#endif
}

// The SIMD product with p written as an FMA with a zero addend, and the scalar one written with
// the scalar FMA intrinsic (x86: what std::fma compiles to when the compiler inlines it).
NOINLINE dd mul_simdopaque(dd x, dd y) {
#if defined(__AVX2__)
    const __m256d xh = _mm256_set1_pd(x.hi), xl = _mm256_set1_pd(x.lo);
    const __m256d yh = _mm256_set1_pd(y.hi), yl = _mm256_set1_pd(y.lo);
    const __m256d zero = _mm256_setzero_pd();
    const __m256d p = _mm256_fmadd_pd(xh, yh, zero);
    const __m256d e = _mm256_fmsub_pd(xh, yh, p);
    const __m256d t0 = _mm256_fmadd_pd(xl, yl, zero);
    const __m256d t1 = _mm256_fmadd_pd(xh, yl, t0);
    const __m256d t2 = _mm256_fmadd_pd(xl, yh, t1);
    const __m256d c = _mm256_add_pd(e, t2);
    const __m256d s = _mm256_add_pd(p, c);
    const __m256d z = _mm256_sub_pd(s, p);
    const __m256d l = _mm256_sub_pd(c, z);
    return {_mm256_cvtsd_f64(s), _mm256_cvtsd_f64(l)};
#elif defined(__aarch64__) || defined(_M_ARM64)
    const float64x2_t xh = vdupq_n_f64(x.hi), xl = vdupq_n_f64(x.lo);
    const float64x2_t yh = vdupq_n_f64(y.hi), yl = vdupq_n_f64(y.lo);
    const float64x2_t zero = vdupq_n_f64(0.0);
    const float64x2_t p = vfmaq_f64(zero, xh, yh);
    const float64x2_t e = vfmaq_f64(vnegq_f64(p), xh, yh);
    const float64x2_t t0 = vfmaq_f64(zero, xl, yl);
    const float64x2_t t1 = vfmaq_f64(t0, xh, yl);
    const float64x2_t t2 = vfmaq_f64(t1, xl, yh);
    const float64x2_t c = vaddq_f64(e, t2);
    const float64x2_t s = vaddq_f64(p, c);
    const float64x2_t z = vsubq_f64(s, p);
    const float64x2_t l = vsubq_f64(c, z);
    return {vgetq_lane_f64(s, 0), vgetq_lane_f64(l, 0)};
#else
    return mul_reference(x, y);
#endif
}

#if defined(__AVX2__)
static inline double fma_sd(double a, double b, double c) {
    return _mm_cvtsd_f64(_mm_fmadd_sd(_mm_set_sd(a), _mm_set_sd(b), _mm_set_sd(c)));
}
#else
static inline double fma_sd(double a, double b, double c) { return std::fma(a, b, c); }
#endif
NOINLINE dd mul_opaqueintrin(dd x, dd y) {
    const double p = fma_sd(x.hi, y.hi, 0.0);
    const double e = fma_sd(x.hi, y.hi, -p);
    const double t0 = fma_sd(x.lo, y.lo, 0.0);
    const double t1 = fma_sd(x.hi, y.lo, t0);
    const double t2 = fma_sd(x.lo, y.hi, t1);
    const double c = e + t2;
    const double s = p + c;
    const double z = s - p;
    const double l = c - z;
    return {s, l};
}

// The scoped switches come last, so that they cannot leak into the variants above (MSVC's
// fp_contract pragma has no push/pop). mul_scoped, compiled without the switch, calls an inline
// helper that carries it: the shape header-only code has (the client's function inlines Kairn's).
#if defined(__GNUC__) && !defined(__clang__)
#define SCOPED_ATTR __attribute__((optimize("fp-contract=off")))
#else
#define SCOPED_ATTR
#endif
inline dd mul_scoped_inner(dd x, dd y);
NOINLINE dd mul_scoped(dd x, dd y) { return mul_scoped_inner(x, y); }

#if defined(_MSC_VER) && !defined(__clang__)
#pragma fp_contract(off)
#endif
SCOPED_ATTR inline dd mul_scoped_inner(dd x, dd y) {
#if defined(__clang__)
#pragma clang fp contract(off)
#endif
    const double p = x.hi * y.hi;
    const double e = std::fma(x.hi, y.hi, -p);
    const double t0 = x.lo * y.lo;
    const double t1 = std::fma(x.hi, y.lo, t0);
    const double t2 = std::fma(x.lo, y.hi, t1);
    const double c = e + t2;
    const double s = p + c;
    const double z = s - p;
    const double l = c - z;
    return {s, l};
}
SCOPED_ATTR NOINLINE dd mul_scopeddirect(dd x, dd y) {
#if defined(__clang__)
#pragma clang fp contract(off)
#endif
    const double p = x.hi * y.hi;
    const double e = std::fma(x.hi, y.hi, -p);
    const double t0 = x.lo * y.lo;
    const double t1 = std::fma(x.hi, y.lo, t0);
    const double t2 = std::fma(x.lo, y.hi, t1);
    const double c = e + t2;
    const double s = p + c;
    const double z = s - p;
    const double l = c - z;
    return {s, l};
}

// SplitMix64: deterministic, seeded.
static std::uint64_t state = 0x9E3779B97F4A7C15ull;
static std::uint64_t next() {
    std::uint64_t z = (state += 0x9E3779B97F4A7C15ull);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
    return z ^ (z >> 31);
}
static double from_bits(std::uint64_t b) {
    double d;
    std::memcpy(&d, &b, 8);
    return d;
}
// A normalized double-double with hi in [2^-60, 2^60): a random 53-bit significand and a random
// lower word of at most half an ulp, then one Fast2Sum (through volatiles) so hi = RN(hi + lo).
static dd random_dd() {
    const std::uint64_t m = next(), n = next(), r = next();
    const int e = int(r % 120) - 60;
    const double hi0 = std::ldexp(from_bits((m >> 12) | 0x3FF0000000000000ull), e);
    const double lo0 = std::ldexp(from_bits((n >> 12) | 0x3FF0000000000000ull) - 1.5, e - 52);
    volatile double s = hi0 + lo0;
    volatile double z = s - hi0;
    volatile double l = lo0 - z;
    return {(r >> 20) & 1 ? -s : s, (r >> 20) & 1 ? -l : l};
}

int main(int argc, char **argv) {
    const int cases = argc > 1 ? std::atoi(argv[1]) : 20000;
    typedef dd (*fn)(dd, dd);
    const fn variants[] = {mul_reference, mul_textbook,   mul_opaque,     mul_opaqueintrin,
                           mul_simd,      mul_simdopaque, mul_scoped,     mul_scopeddirect};
    const char *names[] = {"reference", "textbook",   "opaque", "opaqueintrin",
                           "simd",      "simdopaque", "scoped", "scopeddirect"};
    for (int i = 0; i < cases; ++i) {
        const dd x = random_dd(), y = random_dd();
        for (int v = 0; v < 8; ++v) {
            const dd z = variants[v](x, y);
            std::printf("%s %a %a %a %a %a %a\n", names[v], x.hi, x.lo, y.hi, y.lo, z.hi, z.lo);
        }
    }
    return 0;
}
