// Which products of the program lose the guard of a kernel, with no Kairn header: the guard
// `x + 0` of rule R3 and a two-sum written out as the generated kernels write them, in scalar code
// and with the intrinsics of AVX2 or of AArch64's Advanced SIMD where the target has them.
//
// For each expression p(a, b) of the list below, a function that is not inlined computes p in
// place and passes it straight to two_sum(c, p): the guard of each operand (an addition of +0),
// then s = gc + gp and the error term. A second function receives p already rounded (stored and
// loaded through a volatile, in a function that is not inlined) and does the same. With c within a
// few units of -p the sum cancels: if the compiler drops the guard of p, which does not change its
// value when p cannot be -0, and contracts the product into the sum, the pair (s, e) is computed
// from the exact product and differs. The program prints, per form and expression, in how many of
// N cases the two pairs differ, and the first difference.
//
//   square_plain [N]        (default N = 20000)
//
// Build: any C++20 compiler; g++ or clang++ -std=c++20 -O2 [-ffp-contract=...] [-mavx2 -mfma];
// cl /std:c++20 /EHsc /O2 [/fp:precise | /fp:contract | /fp:fast] [/arch:AVX2]. See README.md.
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#if defined(_MSC_VER) && !defined(__clang__)
#define NOINLINE __declspec(noinline)
#define INLINE __forceinline
#else
#define NOINLINE __attribute__((noinline))
#define INLINE inline __attribute__((always_inline))
#endif

#if defined(__AVX2__)
#include <immintrin.h>
#define HAVE_AVX2 1
#else
#define HAVE_AVX2 0
#endif
#if defined(__aarch64__) || defined(_M_ARM64)
#include <arm_neon.h>
#define HAVE_NEON 1
#else
#define HAVE_NEON 0
#endif

namespace {

// --- The kernel: two_sum(c, p) on guarded operands, as gen/kernels/two_sum_entry.kernel -----------

template <class T>
INLINE void two_sum(T c, T p, T& s_out, T& e_out) {
    const T gc = c + T(0);
    const T gp = p + T(0);
    const T s = gc + gp;
    const T bb = s - gc;
    const T e = (gc - (s - bb)) + (gp - bb);
    s_out = s;
    e_out = e;
}

template <class T>
NOINLINE T rounded(T x) {
    volatile T v = x;
    return v;
}

// --- The expressions -------------------------------------------------------------------------
//
// Inputs per case: a, b in [1/2, 1) (signs as each expression says), ua, ub unsigned integers near
// 2^40 (so that their product is inexact), ia, ib signed. Each expression is p(in), with in the
// inputs of a case.
template <class T>
struct In {
    T a, b;        // in [1/2, 1)
    T sa, sb;      // a and b with random signs
    std::uint64_t ua, ub;
    std::int64_t ia, ib;
};

#define EXPR(NAME, ...)                       \
    template <class T>                        \
    INLINE T NAME(const In<T>& in) {          \
        [[maybe_unused]] const T a = in.a;    \
        [[maybe_unused]] const T b = in.b;    \
        __VA_ARGS__                           \
    }

EXPR(e_plain, return a * b;)                                      // a control: sign unknown
EXPR(e_square, return a * a;)                                     // never -0: (-0)(-0) is +0
EXPR(e_fabs, return std::fabs(in.sa) * std::fabs(in.sb);)        // both signs known positive
EXPR(e_if_pos, if (a > T(0) && b > T(0)) return a * b; return T(0);)  // a dominating condition
EXPR(e_const_fabs, return T(0.75) * std::fabs(in.sa);)           // a positive constant, a fabs
EXPR(e_const_if, if (a > T(0)) return T(0.75) * a; return T(0);)   // a constant, a condition
EXPR(e_unsigned, return T(in.ua) * T(in.ub);)                     // uitofp: never negative
EXPR(e_signed, return T(in.ia) * T(in.ib);)                       // sitofp: a control
EXPR(e_sqrt, return std::sqrt(a) * std::sqrt(b);)                // sqrt(-0) is -0: a control?
EXPR(e_squares, return (a * a) * (b * b);)                        // a product of two squares
EXPR(e_square_b, return (a * a) * in.sb;)                         // a control: b's sign unknown
EXPR(e_exp, return std::exp(a - T(1)) * std::exp(b - T(1));)      // exp is never negative
EXPR(e_pow2, return std::pow(a, T(2));)                            // pow(a, 2), which compilers make a * a
EXPR(e_diff_square, return (a - b) * (a - b);)                     // the square of a difference

template <class T>
using Expr = T (*)(const In<T>&);

#define FORM(NAME)                                                                       \
    template <class T>                                                                   \
    NOINLINE void NAME##_in_place(const In<T>& in, T c, T& s, T& e) {                    \
        two_sum(c, NAME<T>(in), s, e);                                                   \
    }                                                                                    \
    template <class T>                                                                   \
    NOINLINE void NAME##_given(T p, T c, T& s, T& e) {                                   \
        two_sum(c, p, s, e);                                                             \
    }                                                                                    \
    template <class T>                                                                   \
    NOINLINE T NAME##_value(const In<T>& in) {                                           \
        return rounded(NAME<T>(in));                                                     \
    }
FORM(e_plain)
FORM(e_square)
FORM(e_fabs)
FORM(e_if_pos)
FORM(e_const_fabs)
FORM(e_const_if)
FORM(e_unsigned)
FORM(e_signed)
FORM(e_sqrt)
FORM(e_squares)
FORM(e_square_b)
FORM(e_exp)
FORM(e_pow2)
FORM(e_diff_square)

template <class T>
struct Row {
    const char* name;
    void (*in_place)(const In<T>&, T, T&, T&);
    void (*given)(T, T, T&, T&);
    T (*value)(const In<T>&);
};
#define ROW(NAME, TEXT) {TEXT, &NAME##_in_place<T>, &NAME##_given<T>, &NAME##_value<T>}

std::uint64_t state = 0x9E3779B97F4A7C15ull;
std::uint64_t next() {
    state ^= state << 13;
    state ^= state >> 7;
    state ^= state << 17;
    return state;
}
template <class T>
T unit() {  // in [1/2, 1)
    if (sizeof(T) == 8) return T(0.5 + double(next() >> 11) * 0x1p-54);
    return T(0.5f + float(next() >> 40) * 0x1p-25f);
}
template <class T>
In<T> draw() {
    In<T> in;
    in.a = unit<T>();
    in.b = unit<T>();
    in.sa = next() & 1 ? in.a : -in.a;
    in.sb = next() & 1 ? in.b : -in.b;
    in.ua = (std::uint64_t(1) << 40) + (next() >> 25);
    in.ub = (std::uint64_t(1) << 40) + (next() >> 25);
    in.ia = std::int64_t(in.ua) * (next() & 1 ? 1 : -1);
    in.ib = std::int64_t(in.ub);
    return in;
}
template <class T>
bool same(T x, T y) {
    return std::memcmp(&x, &y, sizeof x) == 0;
}

template <class T>
long scalar(const char* type, long n) {
    const Row<T> rows[] = {
        ROW(e_plain, "a*b"),
        ROW(e_square, "a*a"),
        ROW(e_fabs, "fabs(a)*fabs(b)"),
        ROW(e_if_pos, "a*b if a > 0 && b > 0"),
        ROW(e_const_fabs, "0.75*fabs(a)"),
        ROW(e_const_if, "0.75*a if a > 0"),
        ROW(e_unsigned, "T(ua)*T(ub), unsigned"),
        ROW(e_signed, "T(ia)*T(ib), signed"),
        ROW(e_sqrt, "sqrt(a)*sqrt(b)"),
        ROW(e_squares, "(a*a)*(b*b)"),
        ROW(e_square_b, "(a*a)*b"),
        ROW(e_exp, "exp(a-1)*exp(b-1)"),
        ROW(e_pow2, "pow(a, 2)"),
        ROW(e_diff_square, "(a-b)*(a-b)"),
    };
    long total = 0;
    for (const Row<T>& r : rows) {
        long differ = 0;
        char first[256] = "";
        for (long i = 0; i < n; ++i) {
            const In<T> in = draw<T>();
            const T p = r.value(in);
            const T c = -p * (T(1) + T(i % 7) * (sizeof(T) == 8 ? T(0x1p-30) : T(0x1p-12)));
            T s1, e1, s2, e2;
            r.in_place(in, c, s1, e1);
            r.given(p, c, s2, e2);
            if (same(s1, s2) && same(e1, e2)) continue;
            if (!differ++)
                std::snprintf(first, sizeof first, "    first: p = %a, c = %a: in place (%a, %a), rounded first (%a, %a)\n",
                              double(p), double(c), double(s1), double(e1), double(s2), double(e2));
        }
        std::printf("  scalar %-6s %-24s differs in %6ld of %ld\n%s", type, r.name, differ, n, first);
        total += differ;
    }
    return total;
}

// --- Packed forms: the same with the intrinsics of the target ------------------------------------
#if HAVE_AVX2
struct V {
    using R = __m256d;
    static constexpr int W = 4;
    static INLINE R load(const double* p) { return _mm256_loadu_pd(p); }
    static INLINE void store(double* p, R x) { _mm256_storeu_pd(p, x); }
    static INLINE R add(R x, R y) { return _mm256_add_pd(x, y); }
    static INLINE R sub(R x, R y) { return _mm256_sub_pd(x, y); }
    static INLINE R mul(R x, R y) { return _mm256_mul_pd(x, y); }
    static INLINE R zero() { return _mm256_setzero_pd(); }
    static INLINE R abs(R x) { return _mm256_andnot_pd(_mm256_set1_pd(-0.0), x); }
    static INLINE R sqrt(R x) { return _mm256_sqrt_pd(x); }
    static INLINE R splat(double x) { return _mm256_set1_pd(x); }
};
const char* const packed_name = "avx2";
#elif HAVE_NEON
struct V {
    using R = float64x2_t;
    static constexpr int W = 2;
    static INLINE R load(const double* p) { return vld1q_f64(p); }
    static INLINE void store(double* p, R x) { vst1q_f64(p, x); }
    static INLINE R add(R x, R y) { return vaddq_f64(x, y); }
    static INLINE R sub(R x, R y) { return vsubq_f64(x, y); }
    static INLINE R mul(R x, R y) { return vmulq_f64(x, y); }
    static INLINE R zero() { return vdupq_n_f64(0.0); }
    static INLINE R abs(R x) { return vabsq_f64(x); }
    static INLINE R sqrt(R x) { return vsqrtq_f64(x); }
    static INLINE R splat(double x) { return vdupq_n_f64(x); }
};
const char* const packed_name = "neon";
#endif

#if HAVE_AVX2 || HAVE_NEON
INLINE void two_sum_v(V::R c, V::R p, V::R& s_out, V::R& e_out) {
    const V::R gc = V::add(c, V::zero());
    const V::R gp = V::add(p, V::zero());
    const V::R s = V::add(gc, gp);
    const V::R bb = V::sub(s, gc);
    const V::R e = V::add(V::sub(gc, V::sub(s, bb)), V::sub(gp, bb));
    s_out = s;
    e_out = e;
}
#define VEXPR(NAME, ...)                                                                       \
    INLINE V::R NAME(const double* a, const double* b, const double* sa, const double* sb) {   \
        [[maybe_unused]] const V::R A = V::load(a), B = V::load(b), SA = V::load(sa), SB = V::load(sb); \
        __VA_ARGS__                                                                            \
    }                                                                                          \
    NOINLINE void NAME##_in_place(const double* a, const double* b, const double* sa, const double* sb, \
                                  const double* c, double* s, double* e) {                     \
        V::R vs, ve;                                                                           \
        two_sum_v(V::load(c), NAME(a, b, sa, sb), vs, ve);                                     \
        V::store(s, vs);                                                                       \
        V::store(e, ve);                                                                       \
    }                                                                                          \
    NOINLINE void NAME##_value(const double* a, const double* b, const double* sa, const double* sb, \
                               double* p) {                                                    \
        V::store(p, NAME(a, b, sa, sb));                                                       \
    }
VEXPR(v_plain, return V::mul(A, B);)
VEXPR(v_square, return V::mul(A, A);)
VEXPR(v_fabs, return V::mul(V::abs(SA), V::abs(SB));)
VEXPR(v_const_fabs, return V::mul(V::splat(0.75), V::abs(SA));)
VEXPR(v_sqrt, return V::mul(V::sqrt(A), V::sqrt(B));)
VEXPR(v_squares, return V::mul(V::mul(A, A), V::mul(B, B));)
VEXPR(v_square_b, return V::mul(V::mul(A, A), SB);)
NOINLINE void given_v(const double* p, const double* c, double* s, double* e) {
    V::R vs, ve;
    two_sum_v(V::load(c), V::load(p), vs, ve);
    V::store(s, vs);
    V::store(e, ve);
}
struct VRow {
    const char* name;
    void (*in_place)(const double*, const double*, const double*, const double*, const double*, double*, double*);
    void (*value)(const double*, const double*, const double*, const double*, double*);
};
#define VROW(NAME, TEXT) {TEXT, &NAME##_in_place, &NAME##_value}

long packed(long n) {
    const VRow rows[] = {VROW(v_plain, "a*b"),          VROW(v_square, "a*a"),
                         VROW(v_fabs, "fabs(a)*fabs(b)"), VROW(v_const_fabs, "0.75*fabs(a)"),
                         VROW(v_sqrt, "sqrt(a)*sqrt(b)"), VROW(v_squares, "(a*a)*(b*b)"),
                         VROW(v_square_b, "(a*a)*b")};
    constexpr int W = V::W;
    long total = 0;
    for (const VRow& r : rows) {
        long differ = 0;
        char first[256] = "";
        for (long i = 0; i < n; ++i) {
            double a[W], b[W], sa[W], sb[W], p[W], c[W], s1[W], e1[W], s2[W], e2[W];
            for (int l = 0; l < W; ++l) {
                const In<double> in = draw<double>();
                a[l] = in.a;
                b[l] = in.b;
                sa[l] = in.sa;
                sb[l] = in.sb;
            }
            r.value(a, b, sa, sb, p);
            for (int l = 0; l < W; ++l) c[l] = -rounded(p[l]) * (1 + double((i + l) % 7) * 0x1p-30);
            r.in_place(a, b, sa, sb, c, s1, e1);
            given_v(p, c, s2, e2);
            bool d = false;
            for (int l = 0; l < W; ++l) {
                if (same(s1[l], s2[l]) && same(e1[l], e2[l])) continue;
                if (!d && !differ)
                    std::snprintf(first, sizeof first,
                                  "    first: p = %a, c = %a: in place (%a, %a), rounded first (%a, %a)\n", p[l], c[l],
                                  s1[l], e1[l], s2[l], e2[l]);
                d = true;
            }
            differ += d;
        }
        std::printf("  %s double %-24s differs in %6ld of %ld registers\n%s", packed_name, r.name, differ, n, first);
        total += differ;
    }
    return total;
}
#endif

}  // namespace

int main(int argc, char** argv) {
    const long n = argc > 1 ? std::atol(argv[1]) : 20000;
    long total = scalar<double>("double", n) + scalar<float>("float", n);
#if HAVE_AVX2 || HAVE_NEON
    total += packed(n);
#endif
    std::printf("%ld cases differ in all: %s\n", total,
                total ? "some product lost its guard and was fused into the sum" : "no product was fused");
    return 0;
}
