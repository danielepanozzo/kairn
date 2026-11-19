// The timed functions of packed code: the generated kernels of kairn/gen/avx2.hpp or
// kairn/gen/neon.hpp (cores, variant kairn; full kernels with blends, variant full) and the props
// of props_packed.hpp, one number per lane, binary64 limbs. On x86-64 this file is compiled with
// AVX2 and FMA (bench/CMakeLists.txt); without a packed backend its table is empty.
#include "props_packed.hpp"

#include "bench.hpp"

using kairn_bench::ChainArgs;
using kairn_bench::Entry;

#if defined(KB_PACKED)

namespace kg = kairn::gen;
namespace kp = kairn_bench::packed;
using kp::V;
using kp::W;
using kp::load;
using kp::store;

#define KB_PTP(NAME, BODY)                                                                         \
    extern "C" KB_NOINLINE void NAME(                                                              \
        int n, [[maybe_unused]] const double* KB_RESTRICT x0, [[maybe_unused]] const double* KB_RESTRICT x1, \
        [[maybe_unused]] const double* KB_RESTRICT xr, [[maybe_unused]] const double* KB_RESTRICT y0, \
        [[maybe_unused]] const double* KB_RESTRICT y1, [[maybe_unused]] const double* KB_RESTRICT yr, \
        [[maybe_unused]] double* KB_RESTRICT z0, [[maybe_unused]] double* KB_RESTRICT z1,         \
        [[maybe_unused]] double* KB_RESTRICT zr) {                                                 \
        for (int i = 0; i < n; i += W) {                                                           \
            BODY;                                                                                  \
        }                                                                                          \
    }

#define KB_PTP11_1(NAME, EXPR) KB_PTP(NAME, store(z0 + i, EXPR(load(x0 + i), load(y0 + i))))
#define KB_PTP11_2(NAME, FN)                                                                       \
    KB_PTP(NAME, V a; V b; FN(load(x0 + i), load(y0 + i), a, b); store(z0 + i, a); store(z1 + i, b))
#define KB_PTP21(NAME, FN)                                                                         \
    KB_PTP(NAME, V a; V b; FN(load(x0 + i), load(x1 + i), load(y0 + i), a, b); store(z0 + i, a);    \
           store(z1 + i, b))
#define KB_PTP22(NAME, FN)                                                                         \
    KB_PTP(NAME, V a; V b; FN(load(x0 + i), load(x1 + i), load(y0 + i), load(y1 + i), a, b);         \
           store(z0 + i, a); store(z1 + i, b))
#define KB_PTP2(NAME, FN)                                                                          \
    KB_PTP(NAME, V a; V b; FN(load(x0 + i), load(x1 + i), a, b); store(z0 + i, a); store(z1 + i, b))
#define KB_PTPB2(NAME, FN)                                                                         \
    KB_PTP(NAME, V a; V b; V r;                                                                     \
           FN(load(x0 + i), load(x1 + i), load(xr + i), load(y0 + i), load(y1 + i), load(yr + i), a, b, r); \
           store(z0 + i, a); store(z1 + i, b); store(zr + i, r))
#define KB_PTPB2S(NAME, FN)                                                                        \
    KB_PTP(NAME, V a; V b; V r; FN(load(x0 + i), load(x1 + i), load(xr + i), load(y0 + i), a, b, r); \
           store(z0 + i, a); store(z1 + i, b); store(zr + i, r))
#define KB_PTPB2N(NAME, FN)                                                                        \
    KB_PTP(NAME, V a; V b; V r; FN(load(x0 + i), load(x1 + i), load(xr + i), a, b, r);               \
           store(z0 + i, a); store(z1 + i, b); store(zr + i, r))
#define KB_PTPB1(NAME, FN)                                                                         \
    KB_PTP(NAME, V a; V r; FN(load(x0 + i), load(xr + i), load(y0 + i), load(yr + i), a, r);         \
           store(z0 + i, a); store(zr + i, r))
#define KB_PTPB1S(NAME, FN)                                                                        \
    KB_PTP(NAME, V a; V r; FN(load(x0 + i), load(xr + i), load(y0 + i), a, r); store(z0 + i, a);     \
           store(zr + i, r))
#define KB_PTPB1N(NAME, FN)                                                                        \
    KB_PTP(NAME, V a; V r; FN(load(x0 + i), load(xr + i), a, r); store(z0 + i, a); store(zr + i, r))

namespace {
KAIRN_GEN_FORCEINLINE V kairn_add_1_1(V a, V b) { V s; kg::add_1_1(a, b, s); return s; }
KAIRN_GEN_FORCEINLINE V kairn_mul_1_1(V a, V b) { V p; kg::mul_1_1(a, b, p); return p; }
KAIRN_GEN_FORCEINLINE V plain_neg(V a, V) { return kp::neg(a); }
}  // namespace

KB_PTP11_2(kb_ptp_two_prod__kairn, kg::two_prod)
KB_PTP11_2(kb_ptp_two_prod__plain, kp::two_prod_plain)
KB_PTP21(kb_ptp_mul_2_1__kairn, kg::mul_2_1)
KB_PTP21(kb_ptp_mul_2_1__plain, kp::mul_2_1_plain)
KB_PTP21(kb_ptp_mul_2_1__full, kg::mul_2_1_full)
KB_PTP22(kb_ptp_mul_2_2__kairn, kg::mul_2_2)
KB_PTP22(kb_ptp_mul_2_2__plain, kp::mul_2_2_plain)
KB_PTP22(kb_ptp_mul_2_2__full, kg::mul_2_2_full)
KB_PTP22(kb_ptp_add_2_2__kairn, kg::add_2_2)
KB_PTP22(kb_ptp_add_2_2__full, kg::add_2_2_full)
KB_PTP21(kb_ptp_add_2_1__kairn, kg::add_2_1)
KB_PTP21(kb_ptp_add_2_1__full, kg::add_2_1_full)
KB_PTP22(kb_ptp_add_fast_2_2__kairn, kg::add_fast_2_2)
KB_PTP22(kb_ptp_add_fast_2_2__full, kg::add_fast_2_2_full)
KB_PTP2(kb_ptp_neg_2__kairn, kg::neg_2)
KB_PTPB2(kb_ptp_ball_add_2__kairn, kg::ball_add_2)
KB_PTPB2(kb_ptp_ball_add_2__full, kg::ball_add_2_full)
KB_PTPB2(kb_ptp_ball_mul_2__kairn, kg::ball_mul_2)
KB_PTPB2(kb_ptp_ball_mul_2__plain, kp::ball_mul_2_plain)
KB_PTPB2(kb_ptp_ball_mul_2__full, kg::ball_mul_2_full)
KB_PTPB2S(kb_ptp_ball_scale_2__kairn, kg::ball_scale_2)
KB_PTPB2S(kb_ptp_ball_scale_2__full, kg::ball_scale_2_full)
KB_PTPB2N(kb_ptp_ball_neg_2__kairn, kg::ball_neg_2)
KB_PTPB1(kb_ptp_ball_add_1__kairn, kg::ball_add_1)
KB_PTPB1(kb_ptp_ball_add_1__full, kg::ball_add_1_full)
KB_PTPB1(kb_ptp_ball_mul_1__kairn, kg::ball_mul_1)
KB_PTPB1(kb_ptp_ball_mul_1__full, kg::ball_mul_1_full)
KB_PTPB1S(kb_ptp_ball_scale_1__kairn, kg::ball_scale_1)
KB_PTPB1S(kb_ptp_ball_scale_1__full, kg::ball_scale_1_full)
KB_PTPB1N(kb_ptp_ball_neg_1__kairn, kg::ball_neg_1)
KB_PTP11_1(kb_ptp_add_1_1__kairn, kairn_add_1_1)
KB_PTP11_1(kb_ptp_mul_1_1__kairn, kairn_mul_1_1)
KB_PTP11_1(kb_ptp_mul_1_1__double, kp::mul)
KB_PTP11_1(kb_ptp_neg_1__kairn, plain_neg)

// --- Latency: W chains at once, one per lane ----------------------------------------------------

#define KB_PCHAIN(NAME, STEP)                                                                      \
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
        [[maybe_unused]] const V h0 = kp::set1(a->h0);                                             \
        [[maybe_unused]] const V h1 = kp::set1(a->h1);                                             \
        [[maybe_unused]] const V hr = kp::set1(a->hr);                                             \
        V p0 = kp::set1(a->s0), p1 = kp::set1(a->s1), pr = kp::set1(a->sr);                       \
        for (int i = 0; i < n; i += W) {                                                           \
            STEP;                                                                                  \
        }                                                                                          \
        store(a->out0, p0);                                                                        \
        store(a->out1, p1);                                                                        \
        store(a->outr, pr);                                                                        \
    }

#define KB_PSUM2(NAME, FN) KB_PCHAIN(NAME, FN(p0, p1, load(x0 + i), load(x1 + i), p0, p1))
#define KB_PSUM21(NAME, FN) KB_PCHAIN(NAME, FN(p0, p1, load(x0 + i), p0, p1))
#define KB_PPROD2(NAME, FN) KB_PCHAIN(NAME, FN(p0, p1, load(f0 + i), load(f1 + i), p0, p1))
#define KB_PPROD21(NAME, FN) KB_PCHAIN(NAME, FN(p0, p1, load(f0 + i), p0, p1))
#define KB_PHORNER2(NAME, MUL, ADD)                                                                \
    KB_PCHAIN(NAME, V t0; V t1; MUL(p0, p1, h0, h1, t0, t1); ADD(t0, t1, load(c0 + i), load(c1 + i), p0, p1))
#define KB_PSUMB2(NAME, FN) KB_PCHAIN(NAME, FN(p0, p1, pr, load(x0 + i), load(x1 + i), load(xr + i), p0, p1, pr))
#define KB_PPRODB2(NAME, FN) KB_PCHAIN(NAME, FN(p0, p1, pr, load(f0 + i), load(f1 + i), load(fr + i), p0, p1, pr))
#define KB_PSCALEB2(NAME, FN) KB_PCHAIN(NAME, FN(p0, p1, pr, load(f0 + i), p0, p1, pr))
#define KB_PHORNERB2(NAME, MUL, ADD)                                                               \
    KB_PCHAIN(NAME, V t0; V t1; V tr; MUL(p0, p1, pr, h0, h1, hr, t0, t1, tr);                     \
              ADD(t0, t1, tr, load(c0 + i), load(c1 + i), load(cr + i), p0, p1, pr))
#define KB_PSUMB1(NAME, FN) KB_PCHAIN(NAME, FN(p0, pr, load(x0 + i), load(xr + i), p0, pr))
#define KB_PPRODB1(NAME, FN) KB_PCHAIN(NAME, FN(p0, pr, load(f0 + i), load(fr + i), p0, pr))
#define KB_PSCALEB1(NAME, FN) KB_PCHAIN(NAME, FN(p0, pr, load(f0 + i), p0, pr))
#define KB_PHORNERB1(NAME, MUL, ADD)                                                               \
    KB_PCHAIN(NAME, V t0; V tr; MUL(p0, pr, h0, hr, t0, tr); ADD(t0, tr, load(c0 + i), load(cr + i), p0, pr))

KB_PSUM2(kb_psum_add_2_2__kairn, kg::add_2_2)
KB_PSUM2(kb_psum_add_2_2__full, kg::add_2_2_full)
KB_PSUM21(kb_psum_add_2_1__kairn, kg::add_2_1)
KB_PSUM21(kb_psum_add_2_1__full, kg::add_2_1_full)
KB_PSUMB2(kb_psum_ball_add_2__kairn, kg::ball_add_2)
KB_PSUMB2(kb_psum_ball_add_2__full, kg::ball_add_2_full)
KB_PSUMB1(kb_psum_ball_add_1__kairn, kg::ball_add_1)
KB_PSUMB1(kb_psum_ball_add_1__full, kg::ball_add_1_full)
KB_PCHAIN(kb_psum_add_1_1__kairn, kg::add_1_1(p0, load(x0 + i), p0))
KB_PPROD2(kb_pprod_mul_2_2__kairn, kg::mul_2_2)
KB_PPROD2(kb_pprod_mul_2_2__plain, kp::mul_2_2_plain)
KB_PPROD2(kb_pprod_mul_2_2__full, kg::mul_2_2_full)
KB_PPROD21(kb_pprod_mul_2_1__kairn, kg::mul_2_1)
KB_PPROD21(kb_pprod_mul_2_1__full, kg::mul_2_1_full)
KB_PPRODB2(kb_pprod_ball_mul_2__kairn, kg::ball_mul_2)
KB_PPRODB2(kb_pprod_ball_mul_2__plain, kp::ball_mul_2_plain)
KB_PPRODB2(kb_pprod_ball_mul_2__full, kg::ball_mul_2_full)
KB_PSCALEB2(kb_pprod_ball_scale_2__kairn, kg::ball_scale_2)
KB_PSCALEB2(kb_pprod_ball_scale_2__full, kg::ball_scale_2_full)
KB_PPRODB1(kb_pprod_ball_mul_1__kairn, kg::ball_mul_1)
KB_PPRODB1(kb_pprod_ball_mul_1__full, kg::ball_mul_1_full)
KB_PSCALEB1(kb_pprod_ball_scale_1__kairn, kg::ball_scale_1)
KB_PSCALEB1(kb_pprod_ball_scale_1__full, kg::ball_scale_1_full)
KB_PCHAIN(kb_pprod_mul_1_1__kairn, kg::mul_1_1(p0, load(f0 + i), p0))
KB_PCHAIN(kb_pprod_mul_1_1__double, p0 = kp::mul(p0, load(f0 + i)))
KB_PHORNER2(kb_phorner_2__kairn, kg::mul_2_2, kg::add_2_2)
KB_PHORNER2(kb_phorner_2__plain, kp::mul_2_2_plain, kg::add_2_2)
KB_PHORNER2(kb_phorner_2__full, kg::mul_2_2_full, kg::add_2_2_full)
KB_PHORNERB2(kb_phorner_ball_2__kairn, kg::ball_mul_2, kg::ball_add_2)
KB_PHORNERB2(kb_phorner_ball_2__plain, kp::ball_mul_2_plain, kg::ball_add_2)
KB_PHORNERB2(kb_phorner_ball_2__full, kg::ball_mul_2_full, kg::ball_add_2_full)
KB_PHORNERB1(kb_phorner_ball_1__kairn, kg::ball_mul_1, kg::ball_add_1)
KB_PHORNERB1(kb_phorner_ball_1__full, kg::ball_mul_1_full, kg::ball_add_1_full)

#define KB_T(NAME, FN) {NAME, W, FN, nullptr, nullptr, 0},
#define KB_C(NAME, FN) {NAME, W, nullptr, FN, nullptr, 0},

namespace kairn_bench {
const char* const packed_backend = kp::backend;
const Entry packed_entries[] = {
    KB_T("packed/tp/two_prod/kairn", kb_ptp_two_prod__kairn)
    KB_T("packed/tp/two_prod/plain", kb_ptp_two_prod__plain)
    KB_T("packed/tp/mul_2_1/kairn", kb_ptp_mul_2_1__kairn)
    KB_T("packed/tp/mul_2_1/plain", kb_ptp_mul_2_1__plain)
    KB_T("packed/tp/mul_2_1/full", kb_ptp_mul_2_1__full)
    KB_T("packed/tp/mul_2_2/kairn", kb_ptp_mul_2_2__kairn)
    KB_T("packed/tp/mul_2_2/plain", kb_ptp_mul_2_2__plain)
    KB_T("packed/tp/mul_2_2/full", kb_ptp_mul_2_2__full)
    KB_T("packed/tp/add_2_2/kairn", kb_ptp_add_2_2__kairn)
    KB_T("packed/tp/add_2_2/full", kb_ptp_add_2_2__full)
    KB_T("packed/tp/add_2_1/kairn", kb_ptp_add_2_1__kairn)
    KB_T("packed/tp/add_2_1/full", kb_ptp_add_2_1__full)
    KB_T("packed/tp/add_fast_2_2/kairn", kb_ptp_add_fast_2_2__kairn)
    KB_T("packed/tp/add_fast_2_2/full", kb_ptp_add_fast_2_2__full)
    KB_T("packed/tp/neg_2/kairn", kb_ptp_neg_2__kairn)
    KB_T("packed/tp/ball_add_2/kairn", kb_ptp_ball_add_2__kairn)
    KB_T("packed/tp/ball_add_2/full", kb_ptp_ball_add_2__full)
    KB_T("packed/tp/ball_mul_2/kairn", kb_ptp_ball_mul_2__kairn)
    KB_T("packed/tp/ball_mul_2/plain", kb_ptp_ball_mul_2__plain)
    KB_T("packed/tp/ball_mul_2/full", kb_ptp_ball_mul_2__full)
    KB_T("packed/tp/ball_scale_2/kairn", kb_ptp_ball_scale_2__kairn)
    KB_T("packed/tp/ball_scale_2/full", kb_ptp_ball_scale_2__full)
    KB_T("packed/tp/ball_neg_2/kairn", kb_ptp_ball_neg_2__kairn)
    KB_T("packed/tp/ball_add_1/kairn", kb_ptp_ball_add_1__kairn)
    KB_T("packed/tp/ball_add_1/full", kb_ptp_ball_add_1__full)
    KB_T("packed/tp/ball_mul_1/kairn", kb_ptp_ball_mul_1__kairn)
    KB_T("packed/tp/ball_mul_1/full", kb_ptp_ball_mul_1__full)
    KB_T("packed/tp/ball_scale_1/kairn", kb_ptp_ball_scale_1__kairn)
    KB_T("packed/tp/ball_scale_1/full", kb_ptp_ball_scale_1__full)
    KB_T("packed/tp/ball_neg_1/kairn", kb_ptp_ball_neg_1__kairn)
    KB_T("packed/tp/add_1_1/kairn", kb_ptp_add_1_1__kairn)
    KB_T("packed/tp/mul_1_1/kairn", kb_ptp_mul_1_1__kairn)
    KB_T("packed/tp/mul_1_1/double", kb_ptp_mul_1_1__double)
    KB_T("packed/tp/neg_1/kairn", kb_ptp_neg_1__kairn)

    KB_C("packed/sum/add_2_2/kairn", kb_psum_add_2_2__kairn)
    KB_C("packed/sum/add_2_2/full", kb_psum_add_2_2__full)
    KB_C("packed/sum/add_2_1/kairn", kb_psum_add_2_1__kairn)
    KB_C("packed/sum/add_2_1/full", kb_psum_add_2_1__full)
    KB_C("packed/sum/ball_add_2/kairn", kb_psum_ball_add_2__kairn)
    KB_C("packed/sum/ball_add_2/full", kb_psum_ball_add_2__full)
    KB_C("packed/sum/ball_add_1/kairn", kb_psum_ball_add_1__kairn)
    KB_C("packed/sum/ball_add_1/full", kb_psum_ball_add_1__full)
    KB_C("packed/sum/add_1_1/kairn", kb_psum_add_1_1__kairn)
    KB_C("packed/prod/mul_2_2/kairn", kb_pprod_mul_2_2__kairn)
    KB_C("packed/prod/mul_2_2/plain", kb_pprod_mul_2_2__plain)
    KB_C("packed/prod/mul_2_2/full", kb_pprod_mul_2_2__full)
    KB_C("packed/prod/mul_2_1/kairn", kb_pprod_mul_2_1__kairn)
    KB_C("packed/prod/mul_2_1/full", kb_pprod_mul_2_1__full)
    KB_C("packed/prod/ball_mul_2/kairn", kb_pprod_ball_mul_2__kairn)
    KB_C("packed/prod/ball_mul_2/plain", kb_pprod_ball_mul_2__plain)
    KB_C("packed/prod/ball_mul_2/full", kb_pprod_ball_mul_2__full)
    KB_C("packed/prod/ball_scale_2/kairn", kb_pprod_ball_scale_2__kairn)
    KB_C("packed/prod/ball_scale_2/full", kb_pprod_ball_scale_2__full)
    KB_C("packed/prod/ball_mul_1/kairn", kb_pprod_ball_mul_1__kairn)
    KB_C("packed/prod/ball_mul_1/full", kb_pprod_ball_mul_1__full)
    KB_C("packed/prod/ball_scale_1/kairn", kb_pprod_ball_scale_1__kairn)
    KB_C("packed/prod/ball_scale_1/full", kb_pprod_ball_scale_1__full)
    KB_C("packed/prod/mul_1_1/kairn", kb_pprod_mul_1_1__kairn)
    KB_C("packed/prod/mul_1_1/double", kb_pprod_mul_1_1__double)
    KB_C("packed/horner/mul_2_2+add_2_2/kairn", kb_phorner_2__kairn)
    KB_C("packed/horner/mul_2_2+add_2_2/plain", kb_phorner_2__plain)
    KB_C("packed/horner/mul_2_2+add_2_2/full", kb_phorner_2__full)
    KB_C("packed/horner/ball_mul_2+ball_add_2/kairn", kb_phorner_ball_2__kairn)
    KB_C("packed/horner/ball_mul_2+ball_add_2/plain", kb_phorner_ball_2__plain)
    KB_C("packed/horner/ball_mul_2+ball_add_2/full", kb_phorner_ball_2__full)
    KB_C("packed/horner/ball_mul_1+ball_add_1/kairn", kb_phorner_ball_1__kairn)
    KB_C("packed/horner/ball_mul_1+ball_add_1/full", kb_phorner_ball_1__full)
    {nullptr, 0, nullptr, nullptr, nullptr, 0},
};
}  // namespace kairn_bench

#else

namespace kairn_bench {
const char* const packed_backend = "none";
const Entry packed_entries[] = {{nullptr, 0, nullptr, nullptr, nullptr, 0}};
}  // namespace kairn_bench

#endif
