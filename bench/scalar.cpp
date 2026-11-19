// The timed functions of scalar code on separate arrays of limbs: the generated kernels of
// kairn/gen/scalar.hpp (cores, variant kairn; full kernels, variant full) and the measurement
// props of props.hpp, binary64 limbs, as throughput loops and as dependent chains (bench.hpp).
// The compiler may vectorize the throughput loops; bench/asm_summary.py says whether it did. The
// full kernels are compiled as a client gets them: the fix-up behind a branch, inline or in a
// function of its own as kairn/gen/prelude.hpp chooses (KAIRN_GEN_FIXUP_CALL).
#include "props.hpp"

namespace kg = kairn::gen;
namespace tb = kairn_bench::textbook;
using kairn_bench::ChainArgs;
using kairn_bench::Entry;

// --- Throughput ---------------------------------------------------------------------------------

#define KB_TP(NAME, BODY)                                                                          \
    extern "C" KB_NOINLINE void NAME(                                                              \
        int n, [[maybe_unused]] const double* KB_RESTRICT x0, [[maybe_unused]] const double* KB_RESTRICT x1, \
        [[maybe_unused]] const double* KB_RESTRICT xr, [[maybe_unused]] const double* KB_RESTRICT y0, \
        [[maybe_unused]] const double* KB_RESTRICT y1, [[maybe_unused]] const double* KB_RESTRICT yr, \
        [[maybe_unused]] double* KB_RESTRICT z0, [[maybe_unused]] double* KB_RESTRICT z1,         \
        [[maybe_unused]] double* KB_RESTRICT zr) {                                                 \
        for (int i = 0; i < n; ++i) {                                                              \
            BODY;                                                                                  \
        }                                                                                          \
    }

// By shape: one limb and one limb to one limb (11_1) or two (11_2); two limbs and one (21); two
// and two (22); one operand of two limbs (2); balls of two limbs (B2), of one (B1), times one limb
// (B2S, B1S), alone (B2N).
#define KB_TP11_1(NAME, EXPR) KB_TP(NAME, z0[i] = EXPR(x0[i], y0[i]))
#define KB_TP11_2(NAME, FN) KB_TP(NAME, FN(x0[i], y0[i], z0[i], z1[i]))
#define KB_TP21(NAME, FN) KB_TP(NAME, FN(x0[i], x1[i], y0[i], z0[i], z1[i]))
#define KB_TP22(NAME, FN) KB_TP(NAME, FN(x0[i], x1[i], y0[i], y1[i], z0[i], z1[i]))
#define KB_TP2(NAME, FN) KB_TP(NAME, FN(x0[i], x1[i], z0[i], z1[i]))
#define KB_TPB2(NAME, FN) KB_TP(NAME, FN(x0[i], x1[i], xr[i], y0[i], y1[i], yr[i], z0[i], z1[i], zr[i]))
#define KB_TPB1(NAME, FN) KB_TP(NAME, FN(x0[i], xr[i], y0[i], yr[i], z0[i], zr[i]))
#define KB_TPB2S(NAME, FN) KB_TP(NAME, FN(x0[i], x1[i], xr[i], y0[i], z0[i], z1[i], zr[i]))
#define KB_TPB1S(NAME, FN) KB_TP(NAME, FN(x0[i], xr[i], y0[i], z0[i], zr[i]))
#define KB_TPB2N(NAME, FN) KB_TP(NAME, FN(x0[i], x1[i], xr[i], z0[i], z1[i], zr[i]))
#define KB_TPB1N(NAME, FN) KB_TP(NAME, FN(x0[i], xr[i], z0[i], zr[i]))

namespace {
KAIRN_GEN_FORCEINLINE double kairn_add_1_1(double a, double b) { double s; kg::add_1_1(a, b, s); return s; }
KAIRN_GEN_FORCEINLINE double kairn_mul_1_1(double a, double b) { double p; kg::mul_1_1(a, b, p); return p; }
KAIRN_GEN_FORCEINLINE double plain_add(double a, double b) { return a + b; }
KAIRN_GEN_FORCEINLINE double plain_mul(double a, double b) { return a * b; }
KAIRN_GEN_FORCEINLINE double plain_neg(double a, double) { return -a; }
}  // namespace

KB_TP11_2(kb_tp_two_prod__kairn, kg::two_prod)
KB_TP11_2(kb_tp_two_prod__plain, kairn_bench::two_prod_plain)
KB_TP21(kb_tp_mul_2_1__kairn, kg::mul_2_1)
KB_TP21(kb_tp_mul_2_1__plain, kairn_bench::mul_2_1_plain)
KB_TP21(kb_tp_mul_2_1__full, kg::mul_2_1_full)
KB_TP22(kb_tp_mul_2_2__kairn, kg::mul_2_2)
KB_TP22(kb_tp_mul_2_2__plain, kairn_bench::mul_2_2_plain)
KB_TP22(kb_tp_mul_2_2__textbook, tb::dw_times_dw3)
KB_TP22(kb_tp_mul_2_2__full, kg::mul_2_2_full)
KB_TP22(kb_tp_mul_2_2__full_sel, kairn_bench::mul_2_2_full_sel)
KB_TP22(kb_tp_add_2_2__kairn, kg::add_2_2)
KB_TP22(kb_tp_add_2_2__textbook, tb::accurate_dw_plus_dw)
KB_TP22(kb_tp_add_2_2__full, kg::add_2_2_full)
KB_TP22(kb_tp_add_2_2__full_sel, kairn_bench::add_2_2_full_sel)
KB_TP21(kb_tp_add_2_1__kairn, kg::add_2_1)
KB_TP21(kb_tp_add_2_1__full, kg::add_2_1_full)
KB_TP22(kb_tp_add_fast_2_2__kairn, kg::add_fast_2_2)
KB_TP22(kb_tp_add_fast_2_2__textbook, tb::sloppy_dw_plus_dw)
KB_TP22(kb_tp_add_fast_2_2__full, kg::add_fast_2_2_full)
KB_TP2(kb_tp_neg_2__kairn, kg::neg_2)
KB_TPB2(kb_tp_ball_add_2__kairn, kg::ball_add_2)
KB_TPB2(kb_tp_ball_add_2__full, kg::ball_add_2_full)
KB_TPB2(kb_tp_ball_add_2__full_sel, kairn_bench::ball_add_2_full_sel)
KB_TPB2(kb_tp_ball_mul_2__kairn, kg::ball_mul_2)
KB_TPB2(kb_tp_ball_mul_2__plain, kairn_bench::ball_mul_2_plain)
KB_TPB2(kb_tp_ball_mul_2__full, kg::ball_mul_2_full)
KB_TPB2(kb_tp_ball_mul_2__full_sel, kairn_bench::ball_mul_2_full_sel)
KB_TPB2S(kb_tp_ball_scale_2__kairn, kg::ball_scale_2)
KB_TPB2S(kb_tp_ball_scale_2__full, kg::ball_scale_2_full)
KB_TPB2N(kb_tp_ball_neg_2__kairn, kg::ball_neg_2)
KB_TPB1(kb_tp_ball_add_1__kairn, kg::ball_add_1)
KB_TPB1(kb_tp_ball_add_1__full, kg::ball_add_1_full)
KB_TPB1(kb_tp_ball_mul_1__kairn, kg::ball_mul_1)
KB_TPB1(kb_tp_ball_mul_1__full, kg::ball_mul_1_full)
KB_TPB1S(kb_tp_ball_scale_1__kairn, kg::ball_scale_1)
KB_TPB1S(kb_tp_ball_scale_1__full, kg::ball_scale_1_full)
KB_TPB1N(kb_tp_ball_neg_1__kairn, kg::ball_neg_1)
KB_TP11_1(kb_tp_add_1_1__kairn, kairn_add_1_1)
KB_TP11_1(kb_tp_add_1_1__double, plain_add)
KB_TP11_1(kb_tp_mul_1_1__kairn, kairn_mul_1_1)
KB_TP11_1(kb_tp_mul_1_1__double, plain_mul)
KB_TP11_1(kb_tp_neg_1__kairn, plain_neg)

// --- Latency ------------------------------------------------------------------------------------

#define KB_CHAIN(NAME, INIT, STEP, FINI)                                                           \
    extern "C" KB_NOINLINE void NAME(const ChainArgs* a) {                                         \
        const int n = a->n;                                                                        \
        [[maybe_unused]] const double* x0 = a->x0;                                                 \
        [[maybe_unused]] const double* x1 = a->x1;                                                 \
        [[maybe_unused]] const double* xr = a->xr;                                                 \
        [[maybe_unused]] const double* f0 = a->f0;                                                 \
        [[maybe_unused]] const double* f1 = a->f1;                                                 \
        [[maybe_unused]] const double* fr = a->fr;                                                 \
        [[maybe_unused]] const double* c0 = a->c0;                                                 \
        [[maybe_unused]] const double* c1 = a->c1;                                                 \
        [[maybe_unused]] const double* cr = a->cr;                                                 \
        [[maybe_unused]] const double h0 = a->h0;                                                  \
        [[maybe_unused]] const double h1 = a->h1;                                                  \
        [[maybe_unused]] const double hr = a->hr;                                                  \
        double p0 = a->s0, p1 = a->s1, pr = a->sr;                                                 \
        INIT;                                                                                      \
        for (int i = 0; i < n; ++i) {                                                              \
            STEP;                                                                                  \
        }                                                                                          \
        FINI;                                                                                      \
        a->out0[0] = p0;                                                                           \
        a->out1[0] = p1;                                                                           \
        a->outr[0] = pr;                                                                           \
    }

#define KB_SUM2(NAME, FN) KB_CHAIN(NAME, , FN(p0, p1, x0[i], x1[i], p0, p1), )
#define KB_SUM21(NAME, FN) KB_CHAIN(NAME, , FN(p0, p1, x0[i], p0, p1), )
#define KB_PROD2(NAME, FN) KB_CHAIN(NAME, , FN(p0, p1, f0[i], f1[i], p0, p1), )
#define KB_HORNER2(NAME, MUL, ADD)                                                                 \
    KB_CHAIN(NAME, , double t0; double t1; MUL(p0, p1, h0, h1, t0, t1); ADD(t0, t1, c0[i], c1[i], p0, p1), )
#define KB_SUMB2(NAME, FN) KB_CHAIN(NAME, , FN(p0, p1, pr, x0[i], x1[i], xr[i], p0, p1, pr), )
#define KB_PRODB2(NAME, FN) KB_CHAIN(NAME, , FN(p0, p1, pr, f0[i], f1[i], fr[i], p0, p1, pr), )
#define KB_SCALEB2(NAME, FN) KB_CHAIN(NAME, , FN(p0, p1, pr, f0[i], p0, p1, pr), )
#define KB_HORNERB2(NAME, MUL, ADD)                                                                \
    KB_CHAIN(NAME, , double t0; double t1; double tr; MUL(p0, p1, pr, h0, h1, hr, t0, t1, tr);     \
             ADD(t0, t1, tr, c0[i], c1[i], cr[i], p0, p1, pr), )
#define KB_SUMB1(NAME, FN) KB_CHAIN(NAME, , FN(p0, pr, x0[i], xr[i], p0, pr), )
#define KB_PRODB1(NAME, FN) KB_CHAIN(NAME, , FN(p0, pr, f0[i], fr[i], p0, pr), )
#define KB_SCALEB1(NAME, FN) KB_CHAIN(NAME, , FN(p0, pr, f0[i], p0, pr), )
#define KB_HORNERB1(NAME, MUL, ADD)                                                                \
    KB_CHAIN(NAME, , double t0; double tr; MUL(p0, pr, h0, hr, t0, tr); ADD(t0, tr, c0[i], cr[i], p0, pr), )

KB_SUM2(kb_sum_add_2_2__kairn, kg::add_2_2)
KB_SUM2(kb_sum_add_2_2__textbook, tb::accurate_dw_plus_dw)
KB_SUM2(kb_sum_add_2_2__full, kg::add_2_2_full)
KB_SUM2(kb_sum_add_2_2__full_sel, kairn_bench::add_2_2_full_sel)
KB_SUM21(kb_sum_add_2_1__kairn, kg::add_2_1)
KB_SUM21(kb_sum_add_2_1__full, kg::add_2_1_full)
KB_SUM2(kb_sum_add_fast_2_2__kairn, kg::add_fast_2_2)
KB_SUM2(kb_sum_add_fast_2_2__textbook, tb::sloppy_dw_plus_dw)
KB_SUM2(kb_sum_add_fast_2_2__full, kg::add_fast_2_2_full)
KB_SUMB2(kb_sum_ball_add_2__kairn, kg::ball_add_2)
KB_SUMB2(kb_sum_ball_add_2__full, kg::ball_add_2_full)
KB_SUMB2(kb_sum_ball_add_2__full_sel, kairn_bench::ball_add_2_full_sel)
KB_SUMB1(kb_sum_ball_add_1__kairn, kg::ball_add_1)
KB_SUMB1(kb_sum_ball_add_1__full, kg::ball_add_1_full)
KB_CHAIN(kb_sum_add_1_1__kairn, , kg::add_1_1(p0, x0[i], p0), )
KB_CHAIN(kb_sum_add_1_1__double, , p0 = p0 + x0[i], )

// two_prod: the chain runs through p; the error terms are summed on the side, off the chain.
KB_CHAIN(kb_prod_two_prod__kairn, double e = 0.0, double t; kg::two_prod(p0, f0[i], p0, t); e = e + t, p1 = e)
KB_CHAIN(kb_prod_two_prod__plain, double e = 0.0, double t; kairn_bench::two_prod_plain(p0, f0[i], p0, t); e = e + t, p1 = e)
KB_CHAIN(kb_prod_mul_2_1__kairn, , kg::mul_2_1(p0, p1, f0[i], p0, p1), )
KB_CHAIN(kb_prod_mul_2_1__plain, , kairn_bench::mul_2_1_plain(p0, p1, f0[i], p0, p1), )
KB_CHAIN(kb_prod_mul_2_1__full, , kg::mul_2_1_full(p0, p1, f0[i], p0, p1), )
KB_PROD2(kb_prod_mul_2_2__kairn, kg::mul_2_2)
KB_PROD2(kb_prod_mul_2_2__plain, kairn_bench::mul_2_2_plain)
KB_PROD2(kb_prod_mul_2_2__textbook, tb::dw_times_dw3)
KB_PROD2(kb_prod_mul_2_2__full, kg::mul_2_2_full)
KB_PROD2(kb_prod_mul_2_2__full_sel, kairn_bench::mul_2_2_full_sel)
KB_PRODB2(kb_prod_ball_mul_2__kairn, kg::ball_mul_2)
KB_PRODB2(kb_prod_ball_mul_2__plain, kairn_bench::ball_mul_2_plain)
KB_PRODB2(kb_prod_ball_mul_2__full, kg::ball_mul_2_full)
KB_PRODB2(kb_prod_ball_mul_2__full_sel, kairn_bench::ball_mul_2_full_sel)
KB_SCALEB2(kb_prod_ball_scale_2__kairn, kg::ball_scale_2)
KB_SCALEB2(kb_prod_ball_scale_2__full, kg::ball_scale_2_full)
KB_PRODB1(kb_prod_ball_mul_1__kairn, kg::ball_mul_1)
KB_PRODB1(kb_prod_ball_mul_1__full, kg::ball_mul_1_full)
KB_SCALEB1(kb_prod_ball_scale_1__kairn, kg::ball_scale_1)
KB_SCALEB1(kb_prod_ball_scale_1__full, kg::ball_scale_1_full)
KB_CHAIN(kb_prod_mul_1_1__kairn, , kg::mul_1_1(p0, f0[i], p0), )
KB_CHAIN(kb_prod_mul_1_1__double, , p0 = p0 * f0[i], )

KB_HORNER2(kb_horner_2__kairn, kg::mul_2_2, kg::add_2_2)
KB_HORNER2(kb_horner_2__plain, kairn_bench::mul_2_2_plain, kg::add_2_2)
KB_HORNER2(kb_horner_2__textbook, tb::dw_times_dw3, tb::accurate_dw_plus_dw)
KB_HORNER2(kb_horner_2__full, kg::mul_2_2_full, kg::add_2_2_full)
KB_HORNER2(kb_horner_2__full_sel, kairn_bench::mul_2_2_full_sel, kairn_bench::add_2_2_full_sel)
KB_HORNERB2(kb_horner_ball_2__kairn, kg::ball_mul_2, kg::ball_add_2)
KB_HORNERB2(kb_horner_ball_2__plain, kairn_bench::ball_mul_2_plain, kg::ball_add_2)
KB_HORNERB2(kb_horner_ball_2__full, kg::ball_mul_2_full, kg::ball_add_2_full)
KB_HORNERB2(kb_horner_ball_2__full_sel, kairn_bench::ball_mul_2_full_sel, kairn_bench::ball_add_2_full_sel)
KB_HORNERB1(kb_horner_ball_1__kairn, kg::ball_mul_1, kg::ball_add_1)
KB_HORNERB1(kb_horner_ball_1__full, kg::ball_mul_1_full, kg::ball_add_1_full)
KB_CHAIN(kb_horner_1__kairn, , double t; kg::mul_1_1(p0, h0, t); kg::add_1_1(t, c0[i], p0), )
KB_CHAIN(kb_horner_1__double, , p0 = p0 * h0 + c0[i], )

// --- The table ----------------------------------------------------------------------------------

#define KB_T(NAME, FN) {NAME, 1, FN, nullptr, nullptr, 0},
#define KB_C(NAME, FN) {NAME, 1, nullptr, FN, nullptr, 0},

namespace kairn_bench {
const Entry scalar_entries[] = {
    KB_T("scalar/tp/two_prod/kairn", kb_tp_two_prod__kairn)
    KB_T("scalar/tp/two_prod/plain", kb_tp_two_prod__plain)
    KB_T("scalar/tp/mul_2_1/kairn", kb_tp_mul_2_1__kairn)
    KB_T("scalar/tp/mul_2_1/plain", kb_tp_mul_2_1__plain)
    KB_T("scalar/tp/mul_2_1/full", kb_tp_mul_2_1__full)
    KB_T("scalar/tp/mul_2_2/kairn", kb_tp_mul_2_2__kairn)
    KB_T("scalar/tp/mul_2_2/plain", kb_tp_mul_2_2__plain)
    KB_T("scalar/tp/mul_2_2/textbook", kb_tp_mul_2_2__textbook)
    KB_T("scalar/tp/mul_2_2/full", kb_tp_mul_2_2__full)
    KB_T("scalar/tp/mul_2_2/full_sel", kb_tp_mul_2_2__full_sel)
    KB_T("scalar/tp/add_2_2/kairn", kb_tp_add_2_2__kairn)
    KB_T("scalar/tp/add_2_2/textbook", kb_tp_add_2_2__textbook)
    KB_T("scalar/tp/add_2_2/full", kb_tp_add_2_2__full)
    KB_T("scalar/tp/add_2_2/full_sel", kb_tp_add_2_2__full_sel)
    KB_T("scalar/tp/add_2_1/kairn", kb_tp_add_2_1__kairn)
    KB_T("scalar/tp/add_2_1/full", kb_tp_add_2_1__full)
    KB_T("scalar/tp/add_fast_2_2/kairn", kb_tp_add_fast_2_2__kairn)
    KB_T("scalar/tp/add_fast_2_2/textbook", kb_tp_add_fast_2_2__textbook)
    KB_T("scalar/tp/add_fast_2_2/full", kb_tp_add_fast_2_2__full)
    KB_T("scalar/tp/neg_2/kairn", kb_tp_neg_2__kairn)
    KB_T("scalar/tp/ball_add_2/kairn", kb_tp_ball_add_2__kairn)
    KB_T("scalar/tp/ball_add_2/full", kb_tp_ball_add_2__full)
    KB_T("scalar/tp/ball_add_2/full_sel", kb_tp_ball_add_2__full_sel)
    KB_T("scalar/tp/ball_mul_2/kairn", kb_tp_ball_mul_2__kairn)
    KB_T("scalar/tp/ball_mul_2/plain", kb_tp_ball_mul_2__plain)
    KB_T("scalar/tp/ball_mul_2/full", kb_tp_ball_mul_2__full)
    KB_T("scalar/tp/ball_mul_2/full_sel", kb_tp_ball_mul_2__full_sel)
    KB_T("scalar/tp/ball_scale_2/kairn", kb_tp_ball_scale_2__kairn)
    KB_T("scalar/tp/ball_scale_2/full", kb_tp_ball_scale_2__full)
    KB_T("scalar/tp/ball_neg_2/kairn", kb_tp_ball_neg_2__kairn)
    KB_T("scalar/tp/ball_add_1/kairn", kb_tp_ball_add_1__kairn)
    KB_T("scalar/tp/ball_add_1/full", kb_tp_ball_add_1__full)
    KB_T("scalar/tp/ball_mul_1/kairn", kb_tp_ball_mul_1__kairn)
    KB_T("scalar/tp/ball_mul_1/full", kb_tp_ball_mul_1__full)
    KB_T("scalar/tp/ball_scale_1/kairn", kb_tp_ball_scale_1__kairn)
    KB_T("scalar/tp/ball_scale_1/full", kb_tp_ball_scale_1__full)
    KB_T("scalar/tp/ball_neg_1/kairn", kb_tp_ball_neg_1__kairn)
    KB_T("scalar/tp/add_1_1/kairn", kb_tp_add_1_1__kairn)
    KB_T("scalar/tp/add_1_1/double", kb_tp_add_1_1__double)
    KB_T("scalar/tp/mul_1_1/kairn", kb_tp_mul_1_1__kairn)
    KB_T("scalar/tp/mul_1_1/double", kb_tp_mul_1_1__double)
    KB_T("scalar/tp/neg_1/kairn", kb_tp_neg_1__kairn)

    KB_C("scalar/sum/add_2_2/kairn", kb_sum_add_2_2__kairn)
    KB_C("scalar/sum/add_2_2/textbook", kb_sum_add_2_2__textbook)
    KB_C("scalar/sum/add_2_2/full", kb_sum_add_2_2__full)
    KB_C("scalar/sum/add_2_2/full_sel", kb_sum_add_2_2__full_sel)
    KB_C("scalar/sum/add_2_1/kairn", kb_sum_add_2_1__kairn)
    KB_C("scalar/sum/add_2_1/full", kb_sum_add_2_1__full)
    KB_C("scalar/sum/add_fast_2_2/kairn", kb_sum_add_fast_2_2__kairn)
    KB_C("scalar/sum/add_fast_2_2/textbook", kb_sum_add_fast_2_2__textbook)
    KB_C("scalar/sum/add_fast_2_2/full", kb_sum_add_fast_2_2__full)
    KB_C("scalar/sum/ball_add_2/kairn", kb_sum_ball_add_2__kairn)
    KB_C("scalar/sum/ball_add_2/full", kb_sum_ball_add_2__full)
    KB_C("scalar/sum/ball_add_2/full_sel", kb_sum_ball_add_2__full_sel)
    KB_C("scalar/sum/ball_add_1/kairn", kb_sum_ball_add_1__kairn)
    KB_C("scalar/sum/ball_add_1/full", kb_sum_ball_add_1__full)
    KB_C("scalar/sum/add_1_1/kairn", kb_sum_add_1_1__kairn)
    KB_C("scalar/sum/add_1_1/double", kb_sum_add_1_1__double)

    KB_C("scalar/prod/two_prod/kairn", kb_prod_two_prod__kairn)
    KB_C("scalar/prod/two_prod/plain", kb_prod_two_prod__plain)
    KB_C("scalar/prod/mul_2_1/kairn", kb_prod_mul_2_1__kairn)
    KB_C("scalar/prod/mul_2_1/plain", kb_prod_mul_2_1__plain)
    KB_C("scalar/prod/mul_2_1/full", kb_prod_mul_2_1__full)
    KB_C("scalar/prod/mul_2_2/kairn", kb_prod_mul_2_2__kairn)
    KB_C("scalar/prod/mul_2_2/plain", kb_prod_mul_2_2__plain)
    KB_C("scalar/prod/mul_2_2/textbook", kb_prod_mul_2_2__textbook)
    KB_C("scalar/prod/mul_2_2/full", kb_prod_mul_2_2__full)
    KB_C("scalar/prod/mul_2_2/full_sel", kb_prod_mul_2_2__full_sel)
    KB_C("scalar/prod/ball_mul_2/kairn", kb_prod_ball_mul_2__kairn)
    KB_C("scalar/prod/ball_mul_2/plain", kb_prod_ball_mul_2__plain)
    KB_C("scalar/prod/ball_mul_2/full", kb_prod_ball_mul_2__full)
    KB_C("scalar/prod/ball_mul_2/full_sel", kb_prod_ball_mul_2__full_sel)
    KB_C("scalar/prod/ball_scale_2/kairn", kb_prod_ball_scale_2__kairn)
    KB_C("scalar/prod/ball_scale_2/full", kb_prod_ball_scale_2__full)
    KB_C("scalar/prod/ball_mul_1/kairn", kb_prod_ball_mul_1__kairn)
    KB_C("scalar/prod/ball_mul_1/full", kb_prod_ball_mul_1__full)
    KB_C("scalar/prod/ball_scale_1/kairn", kb_prod_ball_scale_1__kairn)
    KB_C("scalar/prod/ball_scale_1/full", kb_prod_ball_scale_1__full)
    KB_C("scalar/prod/mul_1_1/kairn", kb_prod_mul_1_1__kairn)
    KB_C("scalar/prod/mul_1_1/double", kb_prod_mul_1_1__double)

    KB_C("scalar/horner/mul_2_2+add_2_2/kairn", kb_horner_2__kairn)
    KB_C("scalar/horner/mul_2_2+add_2_2/plain", kb_horner_2__plain)
    KB_C("scalar/horner/mul_2_2+add_2_2/textbook", kb_horner_2__textbook)
    KB_C("scalar/horner/mul_2_2+add_2_2/full", kb_horner_2__full)
    KB_C("scalar/horner/mul_2_2+add_2_2/full_sel", kb_horner_2__full_sel)
    KB_C("scalar/horner/ball_mul_2+ball_add_2/kairn", kb_horner_ball_2__kairn)
    KB_C("scalar/horner/ball_mul_2+ball_add_2/plain", kb_horner_ball_2__plain)
    KB_C("scalar/horner/ball_mul_2+ball_add_2/full", kb_horner_ball_2__full)
    KB_C("scalar/horner/ball_mul_2+ball_add_2/full_sel", kb_horner_ball_2__full_sel)
    KB_C("scalar/horner/ball_mul_1+ball_add_1/kairn", kb_horner_ball_1__kairn)
    KB_C("scalar/horner/ball_mul_1+ball_add_1/full", kb_horner_ball_1__full)
    KB_C("scalar/horner/mul_1_1+add_1_1/kairn", kb_horner_1__kairn)
    KB_C("scalar/horner/mul_1_1+add_1_1/double", kb_horner_1__double)
    {nullptr, 0, nullptr, nullptr, nullptr, 0},
};
}  // namespace kairn_bench
