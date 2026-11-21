// Measurement props: the classical way to round down and up, by changing the rounding mode
// (bench/m2_data.hpp). Not part of the library, not verified, not to be used outside bench/; each
// is the baseline of one comparison, and each is checked against Kairn's result, bit for bit, before
// it is timed (m2_main.cpp), on the benchmark's numbers and on a wide sample.
//
// Variants:
// - fenv: std::fesetround to downward or upward around one operation, and back to nearest after it;
//   an interval operation sets downward for its lower bound, upward for its upper bound, then
//   nearest. The product of intervals is the four products of bounds under each mode, and the least
//   of the four rounded down and the greatest of the four rounded up: the same listing as Kairn's
//   interval_mul_1, without branches, so that the two compute the same function and differ only in
//   how they round.
// - csr: the same, writing the control register directly (MXCSR on x86-64, FPCR on AArch64) with
//   values computed once: what a library that does not call fesetround can do.
// - fenv_loop: the mode changed once around a whole loop, or a whole chain. For a building block,
//   the mode of the block. For intervals, upward only, with the lower bound computed as the
//   negation of the upward rounding of the negated value, RD(t) = -RU(-t): what a classical interval
//   library does in a loop it wants vectorized.
//
// How the compilers are made to honor the mode: this file is compiled with -frounding-math (GCC,
// Clang; /fp:strict with MSVC), so that no operation is folded or moved on the assumption that
// rounding is to nearest; with Clang the pragma STDC FENV_ACCESS ON is in force for the whole file;
// and each operation that runs under a mode set around it has its operands and its result passed
// through KB_OPAQUE (an empty asm statement that the compiler must assume reads and changes the
// value), placed after the change of mode before the operation and before the change after it, so
// that the operation cannot be moved across either, and two operations on the same operands under
// two modes cannot be merged. The fenv_loop variants have no KB_OPAQUE inside the loop, so that the
// compiler may vectorize it: their loads come after the call that sets the mode and their stores
// before the call that resets it, which every compiler must respect for memory that a call may
// read or write.
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <limits>

#include "m2_data.hpp"

#if defined(__clang__)
#pragma STDC FENV_ACCESS ON
#elif defined(_MSC_VER)
#pragma fenv_access(on)
#endif

#if defined(__x86_64__) || defined(_M_X64)
#include <xmmintrin.h>
#endif

#if defined(_MSC_VER) && !defined(__clang__)
#define KB_INLINE __forceinline
#else
#define KB_INLINE inline __attribute__((always_inline))
#endif

namespace {

using kairn_bench::m2::Entry;
using kairn_bench::m2::kDeg;
using kairn_bench::m2::kN;
using kairn_bench::m2::Raw;
using namespace kairn_bench::m2;   // the regions

// --- The control register ------------------------------------------------------------------------

#if defined(__x86_64__) || defined(_M_X64)
// MXCSR: the rounding control is bits 13 and 14, 00 nearest, 01 down, 10 up.
struct Csr {
    unsigned nearest, down, up;
    Csr() {
        nearest = _mm_getcsr();
        down = (nearest & ~0x6000u) | 0x2000u;
        up = (nearest & ~0x6000u) | 0x4000u;
    }
};
KB_INLINE void csr_set(unsigned v) { _mm_setcsr(v); }
#elif defined(__aarch64__)
// FPCR: RMode is bits 22 and 23, 00 nearest, 01 toward +inf, 10 toward -inf.
struct Csr {
    std::uint64_t nearest, down, up;
    Csr() {
        std::uint64_t v;
        __asm__ volatile("mrs %0, fpcr" : "=r"(v));
        nearest = v;
        down = (v & ~(std::uint64_t(3) << 22)) | (std::uint64_t(2) << 22);
        up = (v & ~(std::uint64_t(3) << 22)) | (std::uint64_t(1) << 22);
    }
};
KB_INLINE void csr_set(std::uint64_t v) { __asm__ volatile("msr fpcr, %0" : : "r"(v) : "memory"); }
#else
// No direct access: the variant falls back on fesetround.
struct Csr {
    int nearest = FE_TONEAREST, down = FE_DOWNWARD, up = FE_UPWARD;
};
KB_INLINE void csr_set(int v) { std::fesetround(v); }
#endif

// The two ways to set a mode: M::set(down or up) and M::reset().
struct Fenv {
    KB_INLINE void down() const { std::fesetround(FE_DOWNWARD); }
    KB_INLINE void up() const { std::fesetround(FE_UPWARD); }
    KB_INLINE void reset() const { std::fesetround(FE_TONEAREST); }
};
struct Reg {
    Csr c;
    KB_INLINE void down() const { csr_set(c.down); }
    KB_INLINE void up() const { csr_set(c.up); }
    KB_INLINE void reset() const { csr_set(c.nearest); }
};

// --- One operation under a mode set around it -----------------------------------------------------

enum Op { ADD, SUB, MUL };

template <Op O, class T>
KB_INLINE T apply(T a, T b) {
    KB_OPAQUE(a);
    KB_OPAQUE(b);
    T r = O == ADD ? a + b : O == SUB ? a - b : a * b;
    KB_OPAQUE(r);
    return r;
}
template <Op O, class M, class T>
KB_INLINE T down(const M& m, T a, T b) {
    m.down();
    const T r = apply<O>(a, b);
    m.reset();
    return r;
}
template <Op O, class M, class T>
KB_INLINE T up(const M& m, T a, T b) {
    m.up();
    const T r = apply<O>(a, b);
    m.reset();
    return r;
}

// The least and the greatest of four values, as Kairn's kernels choose them.
template <class T>
KB_INLINE T min4(T a, T b, T c, T e) {
    const T p = b < a ? b : a;
    const T q = e < c ? e : c;
    return q < p ? q : p;
}
template <class T>
KB_INLINE T max4(T a, T b, T c, T e) {
    const T p = a < b ? b : a;
    const T q = c < e ? e : c;
    return p < q ? q : p;
}

// Interval operations, the mode set around each: down for the lower bound, up for the upper one.
template <class M, class T>
KB_INLINE void iadd(const M& m, T xl, T xu, T yl, T yu, T& zl, T& zu) {
    m.down();
    const T l = apply<ADD>(xl, yl);
    m.up();
    const T h = apply<ADD>(xu, yu);
    m.reset();
    zl = l;
    zu = h;
}
template <class M, class T>
KB_INLINE void isub(const M& m, T xl, T xu, T yl, T yu, T& zl, T& zu) {
    m.down();
    const T l = apply<SUB>(xl, yu);
    m.up();
    const T h = apply<SUB>(xu, yl);
    m.reset();
    zl = l;
    zu = h;
}
template <class M, class T>
KB_INLINE void imul(const M& m, T xl, T xu, T yl, T yu, T& zl, T& zu) {
    m.down();
    const T d1 = apply<MUL>(xl, yl), d2 = apply<MUL>(xl, yu), d3 = apply<MUL>(xu, yl), d4 = apply<MUL>(xu, yu);
    m.up();
    const T u1 = apply<MUL>(xl, yl), u2 = apply<MUL>(xl, yu), u3 = apply<MUL>(xu, yl), u4 = apply<MUL>(xu, yu);
    m.reset();
    zl = min4(d1, d2, d3, d4);
    zu = max4(u1, u2, u3, u4);
}

// Interval operations under upward rounding throughout (fenv_loop): RD(t) = -RU(-t).
template <class T>
KB_INLINE void iadd_up(T xl, T xu, T yl, T yu, T& zl, T& zu) {
    zl = -((-xl) + (-yl));
    zu = xu + yu;
}
template <class T>
KB_INLINE void isub_up(T xl, T xu, T yl, T yu, T& zl, T& zu) {
    zl = -(yu - xl);
    zu = xu - yl;
}
template <class T>
KB_INLINE void imul_up(T xl, T xu, T yl, T yu, T& zl, T& zu) {
    const T nl = -xl, nu = -xu;
    zl = -max4(nl * yl, nl * yu, nu * yl, nu * yu);
    zu = max4(xl * yl, xl * yu, xu * yl, xu * yu);
}

// Horner on an interval of one limb, c the coefficients from degree 0 up, each a point.
template <class M, class T>
KB_INLINE void horner(const M& m, const T* c, T xl, T xu, T& pl, T& pu) {
    pl = c[kDeg];
    pu = c[kDeg];
    for (int k = kDeg - 1; k >= 0; --k) {
        T ml, mu;
        imul(m, pl, pu, xl, xu, ml, mu);
        iadd(m, ml, mu, c[k], c[k], pl, pu);
    }
}
template <class T>
KB_INLINE void horner_up(const T* c, T xl, T xu, T& pl, T& pu) {
    pl = c[kDeg];
    pu = c[kDeg];
    for (int k = kDeg - 1; k >= 0; --k) {
        T ml, mu;
        imul_up(pl, pu, xl, xu, ml, mu);
        iadd_up(ml, mu, c[k], c[k], pl, pu);
    }
}

}  // namespace

// --- The timed functions ------------------------------------------------------------------------

#define KB_EACH(...)                                                                               \
    for (int i = 0; i < kN; ++i) {                                                                 \
        __VA_ARGS__;                                                                               \
    }
#define XL r.xi[2 * i]
#define XU r.xi[2 * i + 1]
#define YL r.yi[2 * i]
#define YU r.yi[2 * i + 1]
#define FL r.fi[2 * i]
#define FU r.fi[2 * i + 1]
#define OUT2 r.out[2 * i], r.out[2 * i + 1]

// Under one mode for the whole function: BODY between fesetround(MODE) and fesetround(nearest).
#define KB_UNDER(MODE, ...)                                                                        \
    std::fesetround(MODE);                                                                         \
    __VA_ARGS__ std::fesetround(FE_TONEAREST);

// The variants of a building block: one operation under a mode around it, with fesetround (fenv) or
// the register (csr), and the mode around the whole loop (fenv_loop).
#define KB_BLOCK(X, B, SUF, T, NAME, OP, DIR, MODE)                                                \
    X(B, SUF, T, tp, NAME, fenv, R_OUT, kN, const Fenv m; KB_EACH(r.out[i] = DIR<OP>(m, r.xa[i], r.ya[i]))) \
    X(B, SUF, T, tp, NAME, csr, R_OUT, kN, const Reg m; KB_EACH(r.out[i] = DIR<OP>(m, r.xa[i], r.ya[i]))) \
    X(B, SUF, T, tp, NAME, fenv_loop, R_OUT, kN,                                                    \
      KB_UNDER(MODE, KB_EACH(r.out[i] = OP == ADD ? r.xa[i] + r.ya[i] : OP == SUB ? r.xa[i] - r.ya[i] : r.xa[i] * r.ya[i])))
#define KB_BLOCK_CHAIN(X, B, SUF, T, KIND, NAME, OP, DIR, MODE, START, ARR)                        \
    X(B, SUF, T, KIND, NAME, fenv, R_COUT, 1, const Fenv m; T s = START; KB_EACH(s = DIR<OP>(m, s, r.ARR[i])) r.cout[0] = s;) \
    X(B, SUF, T, KIND, NAME, csr, R_COUT, 1, const Reg m; T s = START; KB_EACH(s = DIR<OP>(m, s, r.ARR[i])) r.cout[0] = s;) \
    X(B, SUF, T, KIND, NAME, fenv_loop, R_COUT, 1, T s = START;                                     \
      KB_UNDER(MODE, KB_EACH(s = OP == ADD ? s + r.ARR[i] : s * r.ARR[i]) r.cout[0] = s;))

// The variants of an interval operation: around each, and upward around the loop.
#define KB_IVAL(X, B, SUF, T, NAME, FN)                                                            \
    X(B, SUF, T, tp, NAME, fenv, R_OUT, 2 * kN, const Fenv m; KB_EACH(FN(m, XL, XU, YL, YU, OUT2))) \
    X(B, SUF, T, tp, NAME, csr, R_OUT, 2 * kN, const Reg m; KB_EACH(FN(m, XL, XU, YL, YU, OUT2)))  \
    X(B, SUF, T, tp, NAME, fenv_loop, R_OUT, 2 * kN, KB_UNDER(FE_UPWARD, KB_EACH(FN##_up(XL, XU, YL, YU, OUT2))))

#define KB_FLIST(X, B, SUF, T)                                                                     \
    KB_BLOCK(X, B, SUF, T, add_down, ADD, down, FE_DOWNWARD)                                       \
    KB_BLOCK(X, B, SUF, T, add_up, ADD, up, FE_UPWARD)                                             \
    KB_BLOCK(X, B, SUF, T, sub_down, SUB, down, FE_DOWNWARD)                                       \
    KB_BLOCK(X, B, SUF, T, sub_up, SUB, up, FE_UPWARD)                                             \
    KB_BLOCK(X, B, SUF, T, mul_down, MUL, down, FE_DOWNWARD)                                       \
    KB_BLOCK(X, B, SUF, T, mul_up, MUL, up, FE_UPWARD)                                             \
    KB_BLOCK_CHAIN(X, B, SUF, T, sum, add_down, ADD, down, FE_DOWNWARD, T(0), xa)                  \
    KB_BLOCK_CHAIN(X, B, SUF, T, sum, add_up, ADD, up, FE_UPWARD, T(0), xa)                        \
    KB_BLOCK_CHAIN(X, B, SUF, T, prod, mul_down, MUL, down, FE_DOWNWARD, T(1), fa)                 \
    KB_BLOCK_CHAIN(X, B, SUF, T, prod, mul_up, MUL, up, FE_UPWARD, T(1), fa)                       \
    KB_IVAL(X, B, SUF, T, interval_add_1, iadd)                                                    \
    KB_IVAL(X, B, SUF, T, interval_sub_1, isub)                                                    \
    KB_IVAL(X, B, SUF, T, interval_mul_1, imul)                                                    \
    X(B, SUF, T, sum, interval_add_1, fenv, R_COUT, 2, const Fenv m; T sl = 0, su = 0;             \
      KB_EACH(iadd(m, sl, su, XL, XU, sl, su)) r.cout[0] = sl; r.cout[1] = su;)                     \
    X(B, SUF, T, sum, interval_add_1, csr, R_COUT, 2, const Reg m; T sl = 0, su = 0;               \
      KB_EACH(iadd(m, sl, su, XL, XU, sl, su)) r.cout[0] = sl; r.cout[1] = su;)                     \
    X(B, SUF, T, sum, interval_add_1, fenv_loop, R_COUT, 2, T nl = 0, su = 0;                      \
      KB_UNDER(FE_UPWARD, KB_EACH(nl = nl + (-XL); su = su + XU) r.cout[0] = -nl; r.cout[1] = su;)) \
    X(B, SUF, T, prod, interval_mul_1, fenv, R_COUT, 2, const Fenv m; T pl = 1, pu = 1;            \
      KB_EACH(imul(m, pl, pu, FL, FU, pl, pu)) r.cout[0] = pl; r.cout[1] = pu;)                     \
    X(B, SUF, T, prod, interval_mul_1, csr, R_COUT, 2, const Reg m; T pl = 1, pu = 1;              \
      KB_EACH(imul(m, pl, pu, FL, FU, pl, pu)) r.cout[0] = pl; r.cout[1] = pu;)                     \
    X(B, SUF, T, prod, interval_mul_1, fenv_loop, R_COUT, 2, T pl = 1, pu = 1;                     \
      KB_UNDER(FE_UPWARD, KB_EACH(imul_up(pl, pu, FL, FU, pl, pu)) r.cout[0] = pl; r.cout[1] = pu;)) \
    X(B, SUF, T, tp, horner_i1, fenv, R_OUT, 2 * kN, const Fenv m;                                 \
      KB_EACH(horner(m, r.hc, r.hi1[2 * i], r.hi1[2 * i + 1], OUT2)))                              \
    X(B, SUF, T, tp, horner_i1, csr, R_OUT, 2 * kN, const Reg m;                                   \
      KB_EACH(horner(m, r.hc, r.hi1[2 * i], r.hi1[2 * i + 1], OUT2)))                              \
    X(B, SUF, T, tp, horner_i1, fenv_loop, R_OUT, 2 * kN,                                          \
      KB_UNDER(FE_UPWARD, KB_EACH(horner_up(r.hc, r.hi1[2 * i], r.hi1[2 * i + 1], OUT2))))         \
    X(B, SUF, T, lat, horner_i1, fenv, R_COUT, 2, const Fenv m; T z = 0, pl = 0, pu = 0;           \
      KB_EACH(horner(m, r.hc, r.hi1[2 * i] + z, r.hi1[2 * i + 1] + z, pl, pu); z = pl * T(0))      \
      r.cout[0] = pl; r.cout[1] = pu;)                                                             \
    X(B, SUF, T, lat, horner_i1, csr, R_COUT, 2, const Reg m; T z = 0, pl = 0, pu = 0;             \
      KB_EACH(horner(m, r.hc, r.hi1[2 * i] + z, r.hi1[2 * i + 1] + z, pl, pu); z = pl * T(0))      \
      r.cout[0] = pl; r.cout[1] = pu;)                                                             \
    X(B, SUF, T, lat, horner_i1, fenv_loop, R_COUT, 2, T z = 0, pl = 0, pu = 0;                    \
      KB_UNDER(FE_UPWARD, KB_EACH(horner_up(r.hc, r.hi1[2 * i] + z, r.hi1[2 * i + 1] + z, pl, pu); z = pl * T(0)) \
               r.cout[0] = pl; r.cout[1] = pu;))

#define KB_DEF(B, SUF, T, KIND, KERNEL, VAR, REGION, VALUES, ...)                                  \
    extern "C" KB_NOINLINE void kb_m2_##SUF##_##KIND##_##KERNEL##__##VAR(void* kb_data) {                \
        [[maybe_unused]] Raw<T>& r = *static_cast<Raw<T>*>(kb_data);                                     \
        __VA_ARGS__                                                                                \
    }
#define KB_ROW(B, SUF, T, KIND, KERNEL, VAR, REGION, VALUES, ...)                                  \
    {B "/" #KIND "/" #KERNEL "/" #VAR, kb_m2_##SUF##_##KIND##_##KERNEL##__##VAR, int(8 * sizeof(T)), 1, kN, REGION, VALUES, nullptr},

KB_FLIST(KB_DEF, "m2", 64, double)
KB_FLIST(KB_DEF, "m2f", 32, float)

namespace kairn_bench::m2 {

const Entry m2_fenv_entries[] = {
    KB_FLIST(KB_ROW, "m2", 64, double)
    KB_FLIST(KB_ROW, "m2f", 32, float)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};

template <class M, class T>
static void wide(const M& m, int op, int n, const T* a, const T* b, T* out) {
    for (int i = 0; i < n; ++i) {
        switch (op) {
            case 0: out[i] = down<ADD>(m, a[i], b[i]); break;
            case 1: out[i] = up<ADD>(m, a[i], b[i]); break;
            case 2: out[i] = down<SUB>(m, a[i], b[i]); break;
            case 3: out[i] = up<SUB>(m, a[i], b[i]); break;
            case 4: out[i] = down<MUL>(m, a[i], b[i]); break;
            default: out[i] = up<MUL>(m, a[i], b[i]); break;
        }
    }
}

void m2_wide_fenv(int bits, int op, int variant, int n, const void* a, const void* b, void* out) {
    const Fenv f;
    const Reg g;
    if (bits == 32) {
        auto* pa = static_cast<const float*>(a);
        auto* pb = static_cast<const float*>(b);
        auto* po = static_cast<float*>(out);
        if (variant == 0)
            wide(f, op, n, pa, pb, po);
        else
            wide(g, op, n, pa, pb, po);
    } else {
        auto* pa = static_cast<const double*>(a);
        auto* pb = static_cast<const double*>(b);
        auto* po = static_cast<double*>(out);
        if (variant == 0)
            wide(f, op, n, pa, pb, po);
        else
            wide(g, op, n, pa, pb, po);
    }
}

}  // namespace kairn_bench::m2
