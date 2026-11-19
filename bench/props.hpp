// Measurement props for scalar code: kernels that are not part of the library, written only to
// be timed next to the generated ones (bench/README.md). None of them is verified, and none may be
// used outside bench/. Each exists because it is the baseline of a comparison; everything else
// the harness times is a generated kernel or a public operator.
//
// - *_plain: a generated core with every opaque product prod(a, b) = fma_rn(a, b, +0.0) written
//   as a plain a * b, the baseline of "what does the opaque product cost". Compiled with
//   -ffp-contract=off (MSVC: /fp:precise, which does not contract) it computes the same values as
//   the generated core on operands whose products are not zero.
// - *_full_sel: the full kernels of docs/developer/design/milestone1.md ("IEEE-like results",
//   "Ball kernels") as the listing stands, with every select computed: the form the generator
//   emitted for scalar code before it put the fix-up behind a branch, and still emits for packed
//   code (blends). The comparison point of the branch. The multiplication by +infinity is a plain
//   one, as the generator emits it (times_inf). The generated full kernels themselves are timed
//   as the variant full.
// - textbook::: double-word arithmetic written from the algorithm listings of Joldes, Muller and
//   Popescu, "Tight and rigorous error bounds for basic building blocks of double-word
//   arithmetic", ACM TOMS 44(2), 2017 (JMP17): 2Sum, Fast2Sum, Fast2Mult with an FMA,
//   DWPlusFP, SloppyDWPlusDW, AccurateDWPlusDW, DWTimesFP3, DWTimesDW3, with a plain
//   multiplication, no guard and no fix-up. This is what a library without Kairn's additions
//   computes, the baseline of the 1.2x budget; no library's code was used. Templates, for double
//   and float limbs.
#pragma once

#include <kairn/gen/scalar.hpp>

#include <cmath>
#include <limits>

#include "bench.hpp"

namespace kairn_bench {

using kairn::gen::abs_bits;
using kairn::gen::fma_rn;

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

// ball_mul_2 (second radius design), with its three opaque products plain: the two of the center
// and p = rx * ry of the radius. The constants U, E and H are those of ball_mul_2 for binary64
// (kairn/gen/scalar.hpp); the check against the generated kernel fails if they drift.
KAIRN_GEN_FORCEINLINE void ball_mul_2_plain(double cx0, double cx1, double rx, double cy0, double cy1, double ry,
                                            double& cz0_out, double& cz1_out, double& rz_out) noexcept {
    double cz0, cz1;
    mul_2_2_plain(cx0, cx1, cy0, cy1, cz0, cz1);
    const double ax = abs_bits(cx0);
    const double ay = abs_bits(cy0);
    const double az = abs_bits(cz0);
    const double p = rx * ry;
    const double q = fma_rn(ay, rx, p);
    const double w = fma_rn(ax, ry, q);
    const double t = fma_rn(az, 0x1.0000000000001p-104, w);
    const double rz = fma_rn(t, 0x1.0000000000004p+0, 0x1.0000000000005p-1022);
    cz0_out = cz0;
    cz1_out = cz1;
    rz_out = rz;
}

// --- The full kernels with selects (the listing) ------------------------------------------------

// add_2_2_full and mul_2_2_full of milestone1.md, "IEEE-like results": the core, then the fix-up
// with every select computed. t is the operation of the limb type on the leading limbs (x0 + y0
// or prod(x0, y0)); the compilers merge it with the core's own.
KAIRN_GEN_FORCEINLINE void fixup_sel(double z0, double z1, double t, double& w0_out, double& w1_out) noexcept {
    const double a = abs_bits(z0);
    const bool f = kInf > a;
    const double r0 = t * kInf;
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

// ball_add_2_full and ball_mul_2_full of milestone1.md, "Ball kernels": the core, then the
// fix-up, which is the same for both. q = rx + ry is a NaN exactly when a radius is a NaN.
KAIRN_GEN_FORCEINLINE void ball_fixup_sel(double cz0, double cz1, double rz, double rx, double ry,
                                          double& cw0_out, double& cw1_out, double& rw_out) noexcept {
    const double q = rx + ry;
    const bool e = q == q;
    const double a = abs_bits(cz0);
    const bool f1 = kInf > a;
    const bool f2 = kInf > rz;
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

// --- Textbook double-word arithmetic (JMP17) ----------------------------------------------------

namespace textbook {

// 2Sum (Knuth, Moller), as listed in JMP17.
template <class T>
KAIRN_GEN_FORCEINLINE void two_sum(T a, T b, T& s, T& t) noexcept {
    s = a + b;
    const T ap = s - b;
    const T bp = s - ap;
    const T da = a - ap;
    const T db = b - bp;
    t = da + db;
}

// Fast2Sum (Dekker), as listed in JMP17: requires |a| >= |b|, or a's exponent at least b's.
template <class T>
KAIRN_GEN_FORCEINLINE void fast_two_sum(T a, T b, T& s, T& t) noexcept {
    s = a + b;
    const T z = s - a;
    t = b - z;
}

// Fast2Mult with an FMA (2ProdFMA), as listed in JMP17.
template <class T>
KAIRN_GEN_FORCEINLINE void fast_two_mult(T a, T b, T& ph, T& pl) noexcept {
    ph = a * b;
    pl = fma_rn(a, b, -ph);
}

// JMP17 Algorithm 4, DWPlusFP.
template <class T>
KAIRN_GEN_FORCEINLINE void dw_plus_fp(T xh, T xl, T y, T& zh, T& zl) noexcept {
    T sh, sl;
    two_sum(xh, y, sh, sl);
    const T v = xl + sl;
    fast_two_sum(sh, v, zh, zl);
}

// JMP17 Algorithm 5, SloppyDWPlusDW.
template <class T>
KAIRN_GEN_FORCEINLINE void sloppy_dw_plus_dw(T xh, T xl, T yh, T yl, T& zh, T& zl) noexcept {
    T sh, sl;
    two_sum(xh, yh, sh, sl);
    const T v = xl + yl;
    const T w = sl + v;
    fast_two_sum(sh, w, zh, zl);
}

// JMP17 Algorithm 6, AccurateDWPlusDW.
template <class T>
KAIRN_GEN_FORCEINLINE void accurate_dw_plus_dw(T xh, T xl, T yh, T yl, T& zh, T& zl) noexcept {
    T sh, sl, th, tl, vh, vl;
    two_sum(xh, yh, sh, sl);
    two_sum(xl, yl, th, tl);
    const T c = sl + th;
    fast_two_sum(sh, c, vh, vl);
    const T w = tl + vl;
    fast_two_sum(vh, w, zh, zl);
}

// JMP17 Algorithm 9, DWTimesFP3.
template <class T>
KAIRN_GEN_FORCEINLINE void dw_times_fp3(T xh, T xl, T y, T& zh, T& zl) noexcept {
    T ch, cl1;
    fast_two_mult(xh, y, ch, cl1);
    const T cl3 = fma_rn(xl, y, cl1);
    fast_two_sum(ch, cl3, zh, zl);
}

// JMP17 Algorithm 12, DWTimesDW3.
template <class T>
KAIRN_GEN_FORCEINLINE void dw_times_dw3(T xh, T xl, T yh, T yl, T& zh, T& zl) noexcept {
    T ch, cl1;
    fast_two_mult(xh, yh, ch, cl1);
    const T tl0 = xl * yl;
    const T tl1 = fma_rn(xh, yl, tl0);
    const T cl2 = fma_rn(xl, yh, tl1);
    const T cl3 = cl1 + cl2;
    fast_two_sum(ch, cl3, zh, zl);
}

}  // namespace textbook

}  // namespace kairn_bench
