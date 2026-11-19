// An indicative scale: MPFR at 106 bits (mpfr_add, mpfr_mul, round to nearest) on the operands of
// the other benchmarks, converted once beforehand. Built when bench/CMakeLists.txt finds MPFR and
// GMP already installed; otherwise the table is empty. MPFR is not like for like: it handles any
// precision and exponent range, allocates nothing here, and rounds correctly.
#include "bench.hpp"

using kairn_bench::ChainArgs;
using kairn_bench::Entry;

#if defined(KAIRN_BENCH_MPFR)

#include <mpfr.h>

#include <vector>

namespace {

constexpr mpfr_prec_t kPrec = 106;

struct Numbers {
    std::vector<__mpfr_struct> v;
    void init(int n) {
        v.resize(n);
        for (auto& x : v) mpfr_init2(&x, kPrec);
    }
    mpfr_ptr operator[](int i) { return &v[i]; }
};

int n_tp = 0;
int n_chain = 0;
Numbers X, Y, Z;              // throughput operands and results
Numbers CX, CF, CC;           // summands, factors, Horner coefficients
__mpfr_struct S, H, start;    // the chain's value, the Horner argument, the start
bool have_chain = false;

void set2(mpfr_ptr r, double a0, double a1) {
    mpfr_set_d(r, a0, MPFR_RNDN);
    mpfr_add_d(r, r, a1, MPFR_RNDN);
}

void to2(mpfr_srcptr r, double* r0, double* r1) {
    __mpfr_struct t;
    mpfr_init2(&t, kPrec);
    *r0 = mpfr_get_d(r, MPFR_RNDN);
    mpfr_sub_d(&t, r, *r0, MPFR_RNDN);
    *r1 = mpfr_get_d(&t, MPFR_RNDN);
    mpfr_clear(&t);
}

}  // namespace

extern "C" KB_NOINLINE void kb_mtp_add(int n, const double*, const double*, const double*, const double*,
                                       const double*, const double*, double*, double*, double*) {
    for (int i = 0; i < n; ++i) mpfr_add(Z[i], X[i], Y[i], MPFR_RNDN);
}
extern "C" KB_NOINLINE void kb_mtp_mul(int n, const double*, const double*, const double*, const double*,
                                       const double*, const double*, double*, double*, double*) {
    for (int i = 0; i < n; ++i) mpfr_mul(Z[i], X[i], Y[i], MPFR_RNDN);
}
extern "C" KB_NOINLINE void kb_msum(const ChainArgs* a) {
    mpfr_set(&S, &start, MPFR_RNDN);
    for (int i = 0; i < a->n; ++i) mpfr_add(&S, &S, CX[i], MPFR_RNDN);
}
extern "C" KB_NOINLINE void kb_mprod(const ChainArgs* a) {
    mpfr_set_d(&S, 1.0, MPFR_RNDN);
    for (int i = 0; i < a->n; ++i) mpfr_mul(&S, &S, CF[i], MPFR_RNDN);
}
extern "C" KB_NOINLINE void kb_mhorner(const ChainArgs* a) {
    mpfr_set(&S, &start, MPFR_RNDN);
    for (int i = 0; i < a->n; ++i) {
        mpfr_mul(&S, &S, &H, MPFR_RNDN);
        mpfr_add(&S, &S, CC[i], MPFR_RNDN);
    }
}

namespace kairn_bench {

const char* const mpfr_version_text = MPFR_VERSION_STRING;

// The product chain starts at 1, the others at the chain's start (0 in the driver).
const Entry mpfr_entries[] = {
    {"mpfr/tp/add_2_2/mpfr", 1, kb_mtp_add, nullptr, nullptr, 0},
    {"mpfr/tp/mul_2_2/mpfr", 1, kb_mtp_mul, nullptr, nullptr, 0},
    {"mpfr/sum/add_2_2/mpfr", 1, nullptr, kb_msum, nullptr, 0},
    {"mpfr/prod/mul_2_2/mpfr", 1, nullptr, kb_mprod, nullptr, 0},
    {"mpfr/horner/mul_2_2+add_2_2/mpfr", 1, nullptr, kb_mhorner, nullptr, 0},
    {nullptr, 0, nullptr, nullptr, nullptr, 0},
};

void mpfr_setup(int n, const double* x0, const double* x1, const double* y0, const double* y1, const ChainArgs* c) {
    if (n_tp == 0) {
        X.init(n);
        Y.init(n);
        Z.init(n);
        n_tp = n;
    }
    for (int i = 0; i < n; ++i) {
        set2(X[i], x0[i], x1[i]);
        set2(Y[i], y0[i], y1[i]);
    }
    if (!have_chain) {
        CX.init(c->n);
        CF.init(c->n);
        CC.init(c->n);
        mpfr_init2(&S, kPrec);
        mpfr_init2(&H, kPrec);
        mpfr_init2(&start, kPrec);
        n_chain = c->n;
        have_chain = true;
    }
    for (int i = 0; i < c->n; ++i) {
        set2(CX[i], c->x0[i], c->x1[i]);
        set2(CF[i], c->f0[i], c->f1[i]);
        set2(CC[i], c->c0[i], c->c1[i]);
    }
    set2(&H, c->h0, c->h1);
    set2(&start, c->s0, c->s1);
}

void mpfr_result(int i, double* r0, double* r1) {
    if (i < 0)
        to2(&S, r0, r1);
    else
        to2(Z[i], r0, r1);
}

}  // namespace kairn_bench

#else

namespace kairn_bench {
const char* const mpfr_version_text = "";
const Entry mpfr_entries[] = {{nullptr, 0, nullptr, nullptr, nullptr, 0}};
void mpfr_setup(int, const double*, const double*, const double*, const double*, const ChainArgs*) {}
void mpfr_result(int, double* r0, double* r1) { *r0 = *r1 = 0.0; }
}  // namespace kairn_bench

#endif
