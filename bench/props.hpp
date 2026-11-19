// Measurement props for scalar code: kernels that are not part of the library, written only to
// be timed next to the generated ones (bench/README.md). None of them is verified, and none may be
// used outside bench/.
//
// - *_plain: a generated kernel with every opaque product prod(a, b) = fma_rn(a, b, +0.0) written
//   as a plain a * b. Compiled with -ffp-contract=off (MSVC: /fp:precise, which does not contract)
//   it computes the same values as the generated kernel on operands whose products are not zero.
// - *_full_sel, *_full_br: the full kernels of docs/developer/design/milestone1.md ("IEEE-like
//   results", "Ball kernels"), which the generator does not emit yet. _sel is the listing as it
//   stands, with selects written as the generator writes them (m ? a : b); _br branches on "the
//   result is finite" and does the fix-up in a function of its own, on the unlikely path. Two
//   variants of these, for the 2-limb kernels only, test explanations of the measurements:
//   _full_fabs is _full_sel with std::fabs in place of abs_bits, _full_inl is _full_br with the
//   fix-up inline.
// - textbook::: double-word addition and multiplication written from the algorithm listings of
//   Joldes, Muller and Popescu, "Tight and rigorous error bounds for basic building blocks of
//   double-word arithmetic", ACM TOMS 44(2), 2017 (JMP17): 2Sum, Fast2Sum, Fast2Mult with an FMA,
//   SloppyDWPlusDW, AccurateDWPlusDW, DWTimesDW3, with a plain multiplication and no fix-up. This
//   is what a library without Kairn's two additions computes; no library's code was used.
#pragma once

#include <kairn/gen/scalar.hpp>

#include <cmath>
#include <limits>

#include "bench.hpp"

namespace kairn_bench {

using kairn::gen::abs_bits;
using kairn::gen::fma_rn;
using kairn::gen::next_up;

inline constexpr double kInf = std::numeric_limits<double>::infinity();

// --- The opaque product written as a plain product ----------------------------------------------

// two_prod, with p = a * b.
KAIRN_GEN_FORCEINLINE void two_prod_plain(double a, double b, double& p_out, double& e_out) noexcept {
    const double p = a * b;
    const double e = fma_rn(a, b, -p);
    p_out = p;
    e_out = e;
}

// mul_2_1, with ch = x0 * a.
KAIRN_GEN_FORCEINLINE void mul_2_1_plain(double x0, double x1, double a, double& z0_out, double& z1_out) noexcept {
    const double ch = x0 * a;
    const double cl1 = fma_rn(x0, a, -ch);
    const double cl3 = fma_rn(x1, a, cl1);
    const double z0 = ch + cl3;
    const double z0_z = z0 - ch;
    const double z1 = cl3 - z0_z;
    z0_out = z0;
    z1_out = z1;
}

// mul_2_2, with ch = x0 * y0 and tl0 = x1 * y1.
KAIRN_GEN_FORCEINLINE void mul_2_2_plain(double x0, double x1, double y0, double y1, double& z0_out, double& z1_out) noexcept {
    const double ch = x0 * y0;
    const double cl1 = fma_rn(x0, y0, -ch);
    const double tl0 = x1 * y1;
    const double tl1 = fma_rn(x0, y1, tl0);
    const double cl2 = fma_rn(x1, y0, tl1);
    const double cl3 = cl1 + cl2;
    const double z0 = ch + cl3;
    const double z0_z = z0 - ch;
    const double z1 = cl3 - z0_z;
    z0_out = z0;
    z1_out = z1;
}

// ball_mul_2, with the six opaque products plain: the two of the center, the three of the radius
// (in rmul) and the one by the constant U.
KAIRN_GEN_FORCEINLINE void ball_mul_2_plain(double cx0, double cx1, double rx, double cy0, double cy1, double ry,
                                            double& cz0_out, double& cz1_out, double& rz_out) noexcept {
    double cz0, cz1, ax, ay, mz, s1, s2, d, rz;
    mul_2_2_plain(cx0, cx1, cy0, cy1, cz0, cz1);
    kairn::gen::abs_upper_2(cx0, cx1, ax);
    kairn::gen::abs_upper_2(cy0, cy1, ay);
    const double t1 = next_up(ax * ry);
    const double t2 = next_up(ay * rx);
    const double t3 = next_up(rx * ry);
    kairn::gen::radd(t1, t2, s1);
    kairn::gen::radd(s1, t3, s2);
    kairn::gen::abs_upper_2(cz0, cz1, mz);
    const double d0 = next_up(0x1.0000000000001p-104 * mz);   // U of ball_mul_2, binary64
    kairn::gen::radd(d0, 0x1p-1073, d);                         // V of ball_mul_2, binary64
    kairn::gen::radd(s2, d, rz);
    cz0_out = cz0;
    cz1_out = cz1;
    rz_out = rz;
}

// --- The full kernels, form (a): the listing, with selects --------------------------------------

// add_2_2_full and mul_2_2_full of milestone1.md, "IEEE-like results": the core, then the fix-up.
// T is the operation of the limb type on the leading limbs (add(x0, y0) or prod(x0, y0)); the
// compilers merge it with the core's own x0 + y0 or fma_rn(x0, y0, 0).
KAIRN_GEN_FORCEINLINE void fixup_sel(double z0, double z1, double t, double& w0_out, double& w1_out) noexcept {
    const double a = abs_bits(z0);
    const bool f = a < kInf;
    const double r0 = fma_rn(t, kInf, 0.0);
    const bool n = r0 == r0;
    const double r1 = n ? 0.0 : r0;
    const double w0 = f ? z0 : r0;
    const double w1 = f ? z1 : r1;
    w0_out = w0;
    w1_out = w1;
}

KAIRN_GEN_FORCEINLINE void add_2_2_full_sel(double x0, double x1, double y0, double y1, double& w0, double& w1) noexcept {
    double z0, z1;
    kairn::gen::add_2_2(x0, x1, y0, y1, z0, z1);
    const double t = x0 + y0;
    fixup_sel(z0, z1, t, w0, w1);
}

KAIRN_GEN_FORCEINLINE void mul_2_2_full_sel(double x0, double x1, double y0, double y1, double& w0, double& w1) noexcept {
    double z0, z1;
    kairn::gen::mul_2_2(x0, x1, y0, y1, z0, z1);
    const double t = fma_rn(x0, y0, 0.0);
    fixup_sel(z0, z1, t, w0, w1);
}

// A variant of form (a), not a listing of milestone1.md: |z0| from std::fabs instead of
// abs_bits. The same values; some compilers keep this test in floating-point registers, where
// abs_bits's integer AND sends z0 through a general-purpose register.
KAIRN_GEN_FORCEINLINE void fixup_sel_fabs(double z0, double z1, double t, double& w0_out, double& w1_out) noexcept {
    const double a = std::fabs(z0);
    const bool f = a < kInf;
    const double r0 = fma_rn(t, kInf, 0.0);
    const bool n = r0 == r0;
    const double r1 = n ? 0.0 : r0;
    const double w0 = f ? z0 : r0;
    const double w1 = f ? z1 : r1;
    w0_out = w0;
    w1_out = w1;
}

KAIRN_GEN_FORCEINLINE void add_2_2_full_fabs(double x0, double x1, double y0, double y1, double& w0, double& w1) noexcept {
    double z0, z1;
    kairn::gen::add_2_2(x0, x1, y0, y1, z0, z1);
    const double t = x0 + y0;
    fixup_sel_fabs(z0, z1, t, w0, w1);
}

KAIRN_GEN_FORCEINLINE void mul_2_2_full_fabs(double x0, double x1, double y0, double y1, double& w0, double& w1) noexcept {
    double z0, z1;
    kairn::gen::mul_2_2(x0, x1, y0, y1, z0, z1);
    const double t = fma_rn(x0, y0, 0.0);
    fixup_sel_fabs(z0, z1, t, w0, w1);
}

// --- The full kernels, form (b): a branch, and the fix-up out of line ---------------------------

struct Limbs2 {
    double l0, l1;
};

// The canonical form of t, which is not finite whenever this is called on canonical operands.
KB_NOINLINE KB_COLD inline Limbs2 canonical_of(double t) noexcept {
    const double r0 = fma_rn(t, kInf, 0.0);
    const bool n = r0 == r0;
    return {r0, n ? 0.0 : r0};
}
KB_NOINLINE KB_COLD inline Limbs2 add_fixup(double x0, double y0) noexcept { return canonical_of(x0 + y0); }
KB_NOINLINE KB_COLD inline Limbs2 mul_fixup(double x0, double y0) noexcept { return canonical_of(fma_rn(x0, y0, 0.0)); }

KAIRN_GEN_FORCEINLINE void add_2_2_full_br(double x0, double x1, double y0, double y1, double& w0, double& w1) noexcept {
    double z0, z1;
    kairn::gen::add_2_2(x0, x1, y0, y1, z0, z1);
    if (!(abs_bits(z0) < kInf)) [[unlikely]] {
        const Limbs2 r = add_fixup(x0, y0);
        w0 = r.l0;
        w1 = r.l1;
        return;
    }
    w0 = z0;
    w1 = z1;
}

KAIRN_GEN_FORCEINLINE void mul_2_2_full_br(double x0, double x1, double y0, double y1, double& w0, double& w1) noexcept {
    double z0, z1;
    kairn::gen::mul_2_2(x0, x1, y0, y1, z0, z1);
    if (!(abs_bits(z0) < kInf)) [[unlikely]] {
        const Limbs2 r = mul_fixup(x0, y0);
        w0 = r.l0;
        w1 = r.l1;
        return;
    }
    w0 = z0;
    w1 = z1;
}

// A variant of form (b), not a listing of milestone1.md: the same branch, with the fix-up inline
// on the unlikely path instead of in a function of its own, which a vectorizer can turn back
// into selects.
KAIRN_GEN_FORCEINLINE void canonical_inline(double t, double& w0, double& w1) noexcept {
    const double r0 = fma_rn(t, kInf, 0.0);
    const bool n = r0 == r0;
    w0 = r0;
    w1 = n ? 0.0 : r0;
}

KAIRN_GEN_FORCEINLINE void add_2_2_full_inl(double x0, double x1, double y0, double y1, double& w0, double& w1) noexcept {
    double z0, z1;
    kairn::gen::add_2_2(x0, x1, y0, y1, z0, z1);
    if (!(abs_bits(z0) < kInf)) [[unlikely]] {
        const double t = x0 + y0;
        canonical_inline(t, w0, w1);
        return;
    }
    w0 = z0;
    w1 = z1;
}

KAIRN_GEN_FORCEINLINE void mul_2_2_full_inl(double x0, double x1, double y0, double y1, double& w0, double& w1) noexcept {
    double z0, z1;
    kairn::gen::mul_2_2(x0, x1, y0, y1, z0, z1);
    if (!(abs_bits(z0) < kInf)) [[unlikely]] {
        const double t = fma_rn(x0, y0, 0.0);
        canonical_inline(t, w0, w1);
        return;
    }
    w0 = z0;
    w1 = z1;
}

// --- The full Ball kernels ----------------------------------------------------------------------

// ball_add_2_full and ball_mul_2_full of milestone1.md, "Ball kernels": the core, then the
// fix-up, which is the same for both. q = rx + ry is a NaN exactly when a radius is a NaN.
KAIRN_GEN_FORCEINLINE void ball_fixup_sel(double cz0, double cz1, double rz, double rx, double ry,
                                          double& cw0_out, double& cw1_out, double& rw_out) noexcept {
    const double q = rx + ry;
    const bool e = q == q;
    const double a = abs_bits(cz0);
    const bool f1 = a < kInf;
    const bool f2 = rz < kInf;
    const bool f = f1 & f2;
    const double c0 = f ? cz0 : 0.0;
    const double c1 = f ? cz1 : 0.0;
    const double r = f ? rz : kInf;
    const double cw0 = e ? c0 : q;
    const double cw1 = e ? c1 : q;
    const double rw = e ? r : q;
    cw0_out = cw0;
    cw1_out = cw1;
    rw_out = rw;
}

KAIRN_GEN_FORCEINLINE void ball_add_2_full_sel(double cx0, double cx1, double rx, double cy0, double cy1, double ry,
                                               double& cw0, double& cw1, double& rw) noexcept {
    double cz0, cz1, rz;
    kairn::gen::ball_add_2(cx0, cx1, rx, cy0, cy1, ry, cz0, cz1, rz);
    ball_fixup_sel(cz0, cz1, rz, rx, ry, cw0, cw1, rw);
}

KAIRN_GEN_FORCEINLINE void ball_mul_2_full_sel(double cx0, double cx1, double rx, double cy0, double cy1, double ry,
                                               double& cw0, double& cw1, double& rw) noexcept {
    double cz0, cz1, rz;
    kairn::gen::ball_mul_2(cx0, cx1, rx, cy0, cy1, ry, cz0, cz1, rz);
    ball_fixup_sel(cz0, cz1, rz, rx, ry, cw0, cw1, rw);
}

// Form (b). When the center and the radius are finite, q is not a NaN (a NaN radius makes the
// radius of the result a NaN), so the listing returns the core's result: the branch tests that
// alone, and the out-of-line path runs the whole listing.
struct Ball2 {
    double c0, c1, r;
};
KB_NOINLINE KB_COLD inline Ball2 ball_fixup(double cz0, double cz1, double rz, double rx, double ry) noexcept {
    Ball2 b;
    ball_fixup_sel(cz0, cz1, rz, rx, ry, b.c0, b.c1, b.r);
    return b;
}

KAIRN_GEN_FORCEINLINE void ball_add_2_full_br(double cx0, double cx1, double rx, double cy0, double cy1, double ry,
                                              double& cw0, double& cw1, double& rw) noexcept {
    double cz0, cz1, rz;
    kairn::gen::ball_add_2(cx0, cx1, rx, cy0, cy1, ry, cz0, cz1, rz);
    if (!((abs_bits(cz0) < kInf) & (rz < kInf))) [[unlikely]] {
        const Ball2 b = ball_fixup(cz0, cz1, rz, rx, ry);
        cw0 = b.c0;
        cw1 = b.c1;
        rw = b.r;
        return;
    }
    cw0 = cz0;
    cw1 = cz1;
    rw = rz;
}

KAIRN_GEN_FORCEINLINE void ball_mul_2_full_br(double cx0, double cx1, double rx, double cy0, double cy1, double ry,
                                              double& cw0, double& cw1, double& rw) noexcept {
    double cz0, cz1, rz;
    kairn::gen::ball_mul_2(cx0, cx1, rx, cy0, cy1, ry, cz0, cz1, rz);
    if (!((abs_bits(cz0) < kInf) & (rz < kInf))) [[unlikely]] {
        const Ball2 b = ball_fixup(cz0, cz1, rz, rx, ry);
        cw0 = b.c0;
        cw1 = b.c1;
        rw = b.r;
        return;
    }
    cw0 = cz0;
    cw1 = cz1;
    rw = rz;
}

// --- Textbook double-word arithmetic (JMP17) ----------------------------------------------------

namespace textbook {

// 2Sum (Knuth, Moller), as listed in JMP17.
KAIRN_GEN_FORCEINLINE void two_sum(double a, double b, double& s, double& t) noexcept {
    s = a + b;
    const double ap = s - b;
    const double bp = s - ap;
    const double da = a - ap;
    const double db = b - bp;
    t = da + db;
}

// Fast2Sum (Dekker), as listed in JMP17: requires |a| >= |b|, or a's exponent at least b's.
KAIRN_GEN_FORCEINLINE void fast_two_sum(double a, double b, double& s, double& t) noexcept {
    s = a + b;
    const double z = s - a;
    t = b - z;
}

// Fast2Mult with an FMA (2ProdFMA), as listed in JMP17.
KAIRN_GEN_FORCEINLINE void fast_two_mult(double a, double b, double& ph, double& pl) noexcept {
    ph = a * b;
    pl = fma_rn(a, b, -ph);
}

// JMP17 Algorithm 5, SloppyDWPlusDW.
KAIRN_GEN_FORCEINLINE void sloppy_dw_plus_dw(double xh, double xl, double yh, double yl, double& zh, double& zl) noexcept {
    double sh, sl;
    two_sum(xh, yh, sh, sl);
    const double v = xl + yl;
    const double w = sl + v;
    fast_two_sum(sh, w, zh, zl);
}

// JMP17 Algorithm 6, AccurateDWPlusDW.
KAIRN_GEN_FORCEINLINE void accurate_dw_plus_dw(double xh, double xl, double yh, double yl, double& zh, double& zl) noexcept {
    double sh, sl, th, tl, vh, vl;
    two_sum(xh, yh, sh, sl);
    two_sum(xl, yl, th, tl);
    const double c = sl + th;
    fast_two_sum(sh, c, vh, vl);
    const double w = tl + vl;
    fast_two_sum(vh, w, zh, zl);
}

// JMP17 Algorithm 12, DWTimesDW3.
KAIRN_GEN_FORCEINLINE void dw_times_dw3(double xh, double xl, double yh, double yl, double& zh, double& zl) noexcept {
    double ch, cl1;
    fast_two_mult(xh, yh, ch, cl1);
    const double tl0 = xl * yl;
    const double tl1 = fma_rn(xh, yl, tl0);
    const double cl2 = fma_rn(xl, yh, tl1);
    const double cl3 = cl1 + cl2;
    fast_two_sum(ch, cl3, zh, zl);
}

}  // namespace textbook

}  // namespace kairn_bench
