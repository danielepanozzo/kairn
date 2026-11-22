// The timed functions of the ball vectors (kairn/ball_vector.hpp) against arrays of balls
// (bench/m2_data.hpp; bench/README.md, "Milestone 2", third part), backend m2w, double limbs; and the
// widths that one radius costs (m2_bv_widths_json). Compiled with the flags of packed code, as
// m2_batch.cpp: the fast order of the operations is the lane order of the unit's form of Packed.
//
// Kernels: KERNEL_K_N, K the limbs (1, 2) and N the entries (4, 8, 16, 64): add, sub, scale (by a of
// T), axpy (a X + Y), conv (the product of two polynomials of N coefficients, 2N - 1 written), norm
// (norm_upper, an upper bound of every entry of every member). Each timed function applies the
// operation to M = 256 / N ball vectors (every operand in L1), the time per operation on a whole
// vector.
// Variants:
//   op      BallVector<double, K, N> and the free functions of ball_vector.hpp, the result written into
//           a BallVector (kairn::add(x, y, z)), default order
//   seq     the same with kairn::sequential
//   kairn   the generated loop that op calls (bv_add_k, ...), on arrays of the same values: the
//           reference of op and seq, and the operation without its check of the environment
//   balls   std::array<Ball<double, K>, N> and the operators of Ball, entry by entry (the product of
//           polynomials as each coefficient's sum of products, from its first; the bound as the
//           largest of max(upper_as, -lower_as))
// Checks before timing (check() below): op and seq against kairn, byte for byte; balls against op:
// the same centers byte for byte (add, sub, scale, axpy; the product of two limbs), within 4u of the
// sum of the magnitudes for the product of one limb (whose terms are fused in the loop and not in a
// Ball product), and the one radius against the entries' (equal to the largest for add, sub and
// scale, at least it for axpy, as ball_vector.md says; the bound of norm at least the balls').
#include <kairn/ball_vector.hpp>
#include <kairn/kairn.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <limits>
#include <string>
#include <vector>

#include "bench_util.hpp"
#include "m2_data.hpp"

namespace {

namespace kg = kairn::gen;
using kairn_bench::m2::Entry;
template <int K>
using E = kairn::Expansion<double, K>;
template <int K, std::size_t N>
using BV = kairn::BallVector<double, K, N>;
template <int K, std::size_t N>
using Balls = std::array<kairn::Ball<double, K>, N>;

#define KB_SI KAIRN_GEN_FORCEINLINE
#if KAIRN_PACKED_FORM != KAIRN_PACKED_FORM_SCALAR
#define KB_FAST(NAME) kg::NAME##_packed
#else
#define KB_FAST(NAME) kg::NAME##_seq
#endif

constexpr double kA = 0.6875;   // the scalar of scale and axpy, not a power of two

// The same values as plain arrays, for the generated loops.
template <int K, std::size_t N>
struct Raw {
    double c[K][N];
    double r;
};

template <int K, std::size_t N>
struct Set {
    static constexpr int M = int(256 / N);
    std::vector<BV<K, N>> x, y, z;
    std::vector<BV<K, 2 * N - 1>> zc;
    std::vector<Balls<K, N>> bx, by, bz;
    std::vector<Balls<K, 2 * N - 1>> bzc;
    std::vector<Raw<K, N>> rx, ry, rz;
    std::vector<Raw<K, 2 * N - 1>> rzc;
    double norm[256 / N] = {};
};

template <int K, std::size_t N>
Set<K, N>* g_set = nullptr;
template <int K, std::size_t N>
Set<K, N>& set_of() {
    return *g_set<K, N>;
}

// --- The operations -----------------------------------------------------------------------------

// The loops of the generated header on Raw, as ball_vector.hpp calls them.
template <bool Seq, int K, std::size_t N>
KB_SI void raw_add(const Raw<K, N>& x, const Raw<K, N>& y, Raw<K, N>& z, bool sub) {
    bool f = false;
    if constexpr (K == 1) {
        if (sub) {
            if constexpr (Seq) kg::bv_sub_1_seq(x.c[0], y.c[0], N, x.r, y.r, z.c[0], z.r, f);
            else KB_FAST(bv_sub_1)(x.c[0], y.c[0], N, x.r, y.r, z.c[0], z.r, f);
        } else {
            if constexpr (Seq) kg::bv_add_1_seq(x.c[0], y.c[0], N, x.r, y.r, z.c[0], z.r, f);
            else KB_FAST(bv_add_1)(x.c[0], y.c[0], N, x.r, y.r, z.c[0], z.r, f);
        }
    } else {
        if (sub) {
            if constexpr (Seq) kg::bv_sub_2_seq(x.c[0], x.c[1], y.c[0], y.c[1], N, x.r, y.r, z.c[0], z.c[1], z.r, f);
            else KB_FAST(bv_sub_2)(x.c[0], x.c[1], y.c[0], y.c[1], N, x.r, y.r, z.c[0], z.c[1], z.r, f);
        } else {
            if constexpr (Seq) kg::bv_add_2_seq(x.c[0], x.c[1], y.c[0], y.c[1], N, x.r, y.r, z.c[0], z.c[1], z.r, f);
            else KB_FAST(bv_add_2)(x.c[0], x.c[1], y.c[0], y.c[1], N, x.r, y.r, z.c[0], z.c[1], z.r, f);
        }
    }
}
template <int K, std::size_t N>
KB_SI void raw_scale(const Raw<K, N>& x, double a, Raw<K, N>& z) {
    bool f = false;
    if constexpr (K == 1) {
        KB_FAST(bv_scale_1)(x.c[0], N, x.r, a, z.c[0], z.r, f);
    } else {
        KB_FAST(bv_scale_2)(x.c[0], x.c[1], N, x.r, a, z.c[0], z.c[1], z.r, f);
    }
}

#define KB_BINOP(NAME, CALL, SUB)                                                                  \
    template <int K, std::size_t N> KB_SI void NAME##_op(Set<K, N>& d) {                           \
        for (int m = 0; m < Set<K, N>::M; ++m) kairn::CALL(d.x[m], d.y[m], d.z[m]);                \
    }                                                                                              \
    template <int K, std::size_t N> KB_SI void NAME##_seq(Set<K, N>& d) {                          \
        for (int m = 0; m < Set<K, N>::M; ++m) kairn::CALL(kairn::sequential, d.x[m], d.y[m], d.z[m]); \
    }                                                                                              \
    template <int K, std::size_t N> KB_SI void NAME##_kairn(Set<K, N>& d) {                        \
        for (int m = 0; m < Set<K, N>::M; ++m) raw_add<false>(d.rx[m], d.ry[m], d.rz[m], SUB);     \
    }
KB_BINOP(add, add, false)
KB_BINOP(sub, sub, true)
template <int K, std::size_t N> KB_SI void add_balls(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m)
        for (std::size_t i = 0; i < N; ++i) d.bz[m][i] = d.bx[m][i] + d.by[m][i];
}
template <int K, std::size_t N> KB_SI void sub_balls(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m)
        for (std::size_t i = 0; i < N; ++i) d.bz[m][i] = d.bx[m][i] - d.by[m][i];
}

template <int K, std::size_t N> KB_SI void scale_op(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m) kairn::scale(d.x[m], kA, d.z[m]);
}
template <int K, std::size_t N> KB_SI void scale_seq(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m) kairn::scale(kairn::sequential, d.x[m], kA, d.z[m]);
}
template <int K, std::size_t N> KB_SI void scale_kairn(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m) raw_scale(d.rx[m], kA, d.rz[m]);
}
template <int K, std::size_t N> KB_SI void scale_balls(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m)
        for (std::size_t i = 0; i < N; ++i) d.bz[m][i] = d.bx[m][i] * kA;
}

// axpy: the scaling into z, then the sum in place (ball_vector.hpp, "axpy of ball vectors").
template <int K, std::size_t N> KB_SI void axpy_op(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m) kairn::axpy(kA, d.x[m], d.y[m], d.z[m]);
}
template <int K, std::size_t N> KB_SI void axpy_seq(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m) kairn::axpy(kairn::sequential, kA, d.x[m], d.y[m], d.z[m]);
}
template <int K, std::size_t N> KB_SI void axpy_kairn(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m) {
        raw_scale(d.rx[m], kA, d.rz[m]);
        raw_add<false>(d.rz[m], d.ry[m], d.rz[m], false);
    }
}
template <int K, std::size_t N> KB_SI void axpy_balls(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m)
        for (std::size_t i = 0; i < N; ++i) d.bz[m][i] = d.bx[m][i] * kA + d.by[m][i];
}

// The product of polynomials (sequential only).
template <int K, std::size_t N> KB_SI void conv_op(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m) kairn::convolution(d.x[m], d.y[m], d.zc[m]);
}
template <int K, std::size_t N> KB_SI void conv_seq(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m) kairn::convolution(kairn::sequential, d.x[m], d.y[m], d.zc[m]);
}
template <int K, std::size_t N> KB_SI void conv_kairn(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m) {
        const Raw<K, N>&x = d.rx[m], &y = d.ry[m];
        Raw<K, 2 * N - 1>& z = d.rzc[m];
        bool f = false;
        if constexpr (K == 1) {
            kg::bv_conv_1_seq(x.c[0], N, y.c[0], N, x.r, y.r, z.c[0], z.r, f);
        } else {
            kg::bv_conv_2_seq(x.c[0], x.c[1], N, y.c[0], y.c[1], N, x.r, y.r, z.c[0], z.c[1], z.r, f);
        }
    }
}
template <int K, std::size_t N> KB_SI void conv_balls(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m)
        for (std::size_t j = 0; j < 2 * N - 1; ++j) {
            const std::size_t lo = j < N ? 0 : j - N + 1, hi = j < N ? j : N - 1;
            kairn::Ball<double, K> s = d.bx[m][lo] * d.by[m][j - lo];
            for (std::size_t i = lo + 1; i <= hi; ++i) s = s + d.bx[m][i] * d.by[m][j - i];
            d.bzc[m][j] = s;
        }
}

template <int K, std::size_t N> KB_SI void norm_op(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m) d.norm[m] = kairn::norm_upper(d.x[m]);
}
template <int K, std::size_t N> KB_SI void norm_seq(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m) d.norm[m] = kairn::norm_upper(kairn::sequential, d.x[m]);
}
template <int K, std::size_t N> KB_SI void norm_kairn(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m) {
        const Raw<K, N>& x = d.rx[m];
        double b = 0;
        bool ok = false;
        if constexpr (K == 1) {
            KB_FAST(norm_upper_1)(x.c[0], N, b, ok);
        } else {
            KB_FAST(norm_upper_2)(x.c[0], x.c[1], N, b, ok);
        }
        d.norm[m] = ok ? kairn::add_up(b, x.r) : std::numeric_limits<double>::infinity();
    }
}
template <int K, std::size_t N> KB_SI void norm_balls(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m) {
        double b = 0;
        for (std::size_t i = 0; i < N; ++i) {
            const kairn::Ball<double, K>& v = d.bx[m][i];
            b = std::max(b, std::max(v.template upper_as<double>(), -v.template lower_as<double>()));
        }
        d.norm[m] = b;
    }
}

}  // namespace

// --- The timed functions ------------------------------------------------------------------------

#define KB_WOPS(X, K, N)                                                                           \
    X(K, N, add, op) X(K, N, add, seq) X(K, N, add, kairn) X(K, N, add, balls)                     \
    X(K, N, sub, op) X(K, N, sub, seq) X(K, N, sub, kairn) X(K, N, sub, balls)                     \
    X(K, N, scale, op) X(K, N, scale, seq) X(K, N, scale, kairn) X(K, N, scale, balls)             \
    X(K, N, axpy, op) X(K, N, axpy, seq) X(K, N, axpy, kairn) X(K, N, axpy, balls)                 \
    X(K, N, conv, op) X(K, N, conv, seq) X(K, N, conv, kairn) X(K, N, conv, balls)                 \
    X(K, N, norm, op) X(K, N, norm, seq) X(K, N, norm, kairn) X(K, N, norm, balls)
#define KB_WLIST(X)                                                                                \
    KB_WOPS(X, 1, 4) KB_WOPS(X, 1, 8) KB_WOPS(X, 1, 16) KB_WOPS(X, 1, 64)                          \
    KB_WOPS(X, 2, 4) KB_WOPS(X, 2, 8) KB_WOPS(X, 2, 16) KB_WOPS(X, 2, 64)

#define KB_WDEF(K, N, KERNEL, VAR)                                                                 \
    extern "C" KB_NOINLINE void kb_m2_w64_tp_##KERNEL##_##K##_##N##__##VAR(void*) {                \
        KERNEL##_##VAR<K, N>(set_of<K, N>());                                                      \
    }
KB_WLIST(KB_WDEF)

namespace kairn_bench::m2w {
bool check(const kairn_bench::m2::Entry& e, char* why, std::size_t size);
}

#define KB_WROW(K, N, KERNEL, VAR)                                                                 \
    {"m2w/tp/" #KERNEL "_" #K "_" #N "/" #VAR, kb_m2_w64_tp_##KERNEL##_##K##_##N##__##VAR, 64, 1, int(256 / N), \
     K * 100 + N, 0, &kairn_bench::m2w::check},

namespace kairn_bench::m2 {
const Entry m2_bv_entries[] = {
    KB_WLIST(KB_WROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
}  // namespace kairn_bench::m2

// --- The data, the checks and the widths --------------------------------------------------------

namespace {

// Centers +-[1, 2) 2^k, k in [-8, 8] (two limbs: the second about u times the first), as m2.cpp.
template <int K>
E<K> center(kairn_bench::util::Rng& g) {
    const double s = g.sign();
    const double h = s * std::ldexp(1.0 + g.u01(), g.range(-8, 8));
    if constexpr (K == 1) {
        return E<1>(h);
    } else {
        const double l = h * g.sym() * 0x1p-53;
        double limbs[2];
        kg::fast_two_sum(h, l, limbs[0], limbs[1]);
        return E<2>::from_limbs(limbs);
    }
}

template <int K, std::size_t N>
void to_raw(const BV<K, N>& v, Raw<K, N>& r) {
    for (int j = 0; j < K; ++j)
        for (std::size_t i = 0; i < N; ++i) r.c[j][i] = v.limb(j)[i];
    r.r = v.radius();
}

template <int K, std::size_t N>
void make(std::uint64_t seed) {
    if (g_set<K, N>) return;
    Set<K, N>* d = new Set<K, N>();
    kairn_bench::util::Rng g{seed};
    const int M = Set<K, N>::M;
    d->x.resize(M);
    d->y.resize(M);
    d->z.resize(M);
    d->zc.resize(M);
    d->bx.resize(M);
    d->by.resize(M);
    d->bz.resize(M);
    d->bzc.resize(M);
    d->rx.resize(M);
    d->ry.resize(M);
    d->rz.resize(M);
    d->rzc.resize(M);
    for (int m = 0; m < M; ++m) {
        std::array<E<K>, N> cx, cy;
        for (std::size_t i = 0; i < N; ++i) {
            cx[i] = center<K>(g);
            cy[i] = center<K>(g);
        }
        // One radius for every entry, 2^-30 of the largest center's magnitude (2^8): the balls of
        // the same entries have the same radius, so that the balls' results are comparable entry by
        // entry with the ball vector's.
        const double r = 0x1p-22;
        d->x[m] = BV<K, N>(cx, r);
        d->y[m] = BV<K, N>(cy, r);
        for (std::size_t i = 0; i < N; ++i) {
            d->bx[m][i] = kairn::Ball<double, K>(cx[i], r);
            d->by[m][i] = kairn::Ball<double, K>(cy[i], r);
        }
        to_raw(d->x[m], d->rx[m]);
        to_raw(d->y[m], d->ry[m]);
    }
    g_set<K, N> = d;
}

void make_all() {
    make<1, 4>(301);
    make<1, 8>(302);
    make<1, 16>(303);
    make<1, 64>(304);
    make<2, 4>(305);
    make<2, 8>(306);
    make<2, 16>(307);
    make<2, 64>(308);
}

template <int K, std::size_t N>
void clear(Set<K, N>& d) {
    for (int m = 0; m < Set<K, N>::M; ++m) {
        std::memset(static_cast<void*>(&d.z[m]), 0xff, sizeof d.z[m]);
        std::memset(static_cast<void*>(&d.zc[m]), 0xff, sizeof d.zc[m]);
        std::memset(static_cast<void*>(&d.bz[m]), 0xff, sizeof d.bz[m]);
        std::memset(static_cast<void*>(&d.bzc[m]), 0xff, sizeof d.bzc[m]);
        std::memset(static_cast<void*>(&d.rz[m]), 0xff, sizeof d.rz[m]);
        std::memset(static_cast<void*>(&d.rzc[m]), 0xff, sizeof d.rzc[m]);
        d.norm[m] = std::numeric_limits<double>::quiet_NaN();
    }
}

// What a variant wrote: for every vector, the centers' limbs then the radius (balls: each ball's
// center limbs then its radius), and for norm the bounds.
template <int K, std::size_t N>
std::vector<double> read(Set<K, N>& d, const std::string& kernel, const std::string& var) {
    std::vector<double> v;
    const bool conv = kernel == "conv";
    for (int m = 0; m < Set<K, N>::M; ++m) {
        if (kernel == "norm") {
            v.push_back(d.norm[m]);
            continue;
        }
        const std::size_t n = conv ? 2 * N - 1 : N;
        if (var == "balls") {
            for (std::size_t i = 0; i < n; ++i) {
                const kairn::Ball<double, K>& b = conv ? d.bzc[m][i] : d.bz[m][i];
                for (int j = 0; j < K; ++j) v.push_back(b.center().limb[j]);
                v.push_back(b.radius());
            }
        } else if (var == "kairn") {
            for (int j = 0; j < K; ++j)
                for (std::size_t i = 0; i < n; ++i) v.push_back(conv ? d.rzc[m].c[j][i] : d.rz[m].c[j][i]);
            v.push_back(conv ? d.rzc[m].r : d.rz[m].r);
        } else {
            for (int j = 0; j < K; ++j)
                for (std::size_t i = 0; i < n; ++i) v.push_back(conv ? d.zc[m].limb(j)[i] : d.z[m].limb(j)[i]);
            v.push_back(conv ? d.zc[m].radius() : d.z[m].radius());
        }
    }
    return v;
}

const Entry* find_entry(const std::string& name) {
    for (const Entry* e = kairn_bench::m2::m2_bv_entries; e->name; ++e)
        if (name == e->name) return e;
    return nullptr;
}

template <int K, std::size_t N>
bool check_kn(const Entry& e, const std::string& kernel, const std::string& var, char* why, std::size_t size) {
    Set<K, N>& d = set_of<K, N>();
    const std::string stem = std::string(e.name).substr(0, std::string(e.name).rfind('/') + 1);
    auto run = [&](const Entry& f, const std::string& v) {
        clear(d);
        f.fn(nullptr);
        return read(d, kernel, v);
    };
    const std::vector<double> got = run(e, var);
    for (const double x : got)
        if (!std::isfinite(x)) {
            std::snprintf(why, size, "a value is not finite");
            return false;
        }
    if (var == "kairn") return true;   // the reference
    const Entry* ref = find_entry(stem + (var == "balls" ? "op" : "kairn"));
    if (!ref) {
        std::snprintf(why, size, "no reference");
        return false;
    }
    const std::vector<double> want = run(*ref, var == "balls" ? "op" : "kairn");
    if (var != "balls") {
        if (want.size() != got.size() || std::memcmp(want.data(), got.data(), got.size() * sizeof(double)) != 0) {
            std::snprintf(why, size, "not the reference's bytes");
            return false;
        }
        return true;
    }
    // balls against op: per vector, the centers and the one radius against the entries' radii.
    const bool conv = kernel == "conv";
    const std::size_t n = conv ? 2 * N - 1 : N;
    for (int m = 0; m < Set<K, N>::M; ++m) {
        if (kernel == "norm") {
            if (!(want[std::size_t(m)] >= got[std::size_t(m)])) {
                std::snprintf(why, size, "the ball vector's bound %a below the balls' %a", want[std::size_t(m)], got[std::size_t(m)]);
                return false;
            }
            continue;
        }
        const std::size_t bw = std::size_t(m) * (K * n + 1), bb = std::size_t(m) * (K + 1) * n;
        double rmax = 0;
        for (std::size_t i = 0; i < n; ++i) {
            rmax = std::max(rmax, got[bb + i * (K + 1) + K]);
            for (int j = 0; j < K; ++j) {
                const double cw = want[bw + std::size_t(j) * n + i], cb = got[bb + i * (K + 1) + std::size_t(j)];
                // The product of one limb: each term fused into the sum in the loop, rounded on its own
                // in a Ball product; centers below 2^9, products below 2^18, N terms.
                const bool close = conv && K == 1 ? std::fabs(cw - cb) <= 0x1p-53 * 8 * double(N) * 0x1p18 : cw == cb;
                if (!close) {
                    std::snprintf(why, size, "center %zu limb %d: ball %a, ball vector %a", i, j, cb, cw);
                    return false;
                }
            }
        }
        const double rv = want[bw + K * n];
        const bool equal = kernel == "add" || kernel == "sub" || kernel == "scale";
        if (conv) continue;   // the one radius of a product is not stated against the entries'
        if (equal ? rv != rmax : !(rv >= rmax)) {
            std::snprintf(why, size, "the one radius %a, the largest of the balls' %a", rv, rmax);
            return false;
        }
    }
    return true;
}

}  // namespace

namespace kairn_bench::m2w {

bool check(const kairn_bench::m2::Entry& e, char* why, std::size_t size) {
    make_all();
    const std::string name = e.name;   // m2w/tp/KERNEL_K_N/VAR
    const std::string tail = name.substr(7);
    const std::string kn = tail.substr(0, tail.find('/')), var = tail.substr(tail.find('/') + 1);
    const std::string kernel = kn.substr(0, kn.find('_'));
    switch (e.region) {
        case 104: return check_kn<1, 4>(e, kernel, var, why, size);
        case 108: return check_kn<1, 8>(e, kernel, var, why, size);
        case 116: return check_kn<1, 16>(e, kernel, var, why, size);
        case 164: return check_kn<1, 64>(e, kernel, var, why, size);
        case 204: return check_kn<2, 4>(e, kernel, var, why, size);
        case 208: return check_kn<2, 8>(e, kernel, var, why, size);
        case 216: return check_kn<2, 16>(e, kernel, var, why, size);
        default: return check_kn<2, 64>(e, kernel, var, why, size);
    }
}

}  // namespace kairn_bench::m2w

// --- What one radius costs in width -------------------------------------------------------------
// For each K and N, three sets of entries (radius 0, the same radius 2^-30 |c| for all, and radii
// spread over 2^-50 to 2^-20 of each center's magnitude), as one BallVector (whose radius is the
// largest) and as N Balls; then one operation, and chains of 10 and 100 operations: Horner-like,
// z = axpy(t, z, x) (t = 0.6875, X and Y in turn), and de Casteljau-like, z = half(z + shift(z)), the
// entries averaged with their neighbours (the shift a rotation, exact; an add and a half are two
// operations). The ball vector's radius against the largest and the median of the balls' radii.

namespace {

struct Width {
    double one, largest, median;
};

template <int K, std::size_t N>
BV<K, N> rotated(const BV<K, N>& v) {
    std::array<E<K>, N> c;
    for (std::size_t i = 0; i < N; ++i) c[i] = v.center((i + 1) % N);
    return BV<K, N>(c, v.radius());
}

template <int K, std::size_t L>
Width width_of(const BV<K, L>& v, const std::array<kairn::Ball<double, K>, L>& b) {
    std::vector<double> r(L);
    for (std::size_t i = 0; i < L; ++i) r[i] = b[i].radius();
    std::sort(r.begin(), r.end());
    const double med = L % 2 ? r[L / 2] : 0.5 * (r[L / 2 - 1] + r[L / 2]);
    return {v.radius(), r.back(), med};
}

std::string num(double a) {
    char buf[40];
    std::snprintf(buf, sizeof buf, "%.6g", a);
    return buf;
}
std::string wjson(const char* op, const Width& w) {
    return std::string("{\"op\": \"") + op + "\", \"one\": " + num(w.one) + ", \"largest\": " + num(w.largest) +
           ", \"median\": " + num(w.median) + "}";
}

template <int K, std::size_t N>
std::string widths_kn(int regime) {
    kairn_bench::util::Rng g{std::uint64_t(400 + 10 * K + regime) + N};
    std::array<E<K>, N> cx, cy;
    std::array<double, N> rx, ry;
    for (std::size_t i = 0; i < N; ++i) {
        cx[i] = center<K>(g);
        cy[i] = center<K>(g);
        const double ax = std::fabs(cx[i].limb[0]), ay = std::fabs(cy[i].limb[0]);
        if (regime == 0) {
            rx[i] = ry[i] = 0;
        } else if (regime == 1) {
            rx[i] = ry[i] = 0x1p-30 * 256;
        } else {
            rx[i] = ax * std::exp2(-50 + 30 * g.u01());
            ry[i] = ay * std::exp2(-50 + 30 * g.u01());
        }
    }
    Balls<K, N> bx, by;
    for (std::size_t i = 0; i < N; ++i) {
        bx[i] = kairn::Ball<double, K>(cx[i], rx[i]);
        by[i] = kairn::Ball<double, K>(cy[i], ry[i]);
    }
    const BV<K, N> x(cx, *std::max_element(rx.begin(), rx.end())), y(cy, *std::max_element(ry.begin(), ry.end()));
    std::string out = "{\"limbs\": " + std::to_string(K) + ", \"entries\": " + std::to_string(N) +
                      ", \"regime\": \"" + (regime == 0 ? "exact" : regime == 1 ? "same" : "spread") +
                      "\", \"bytes_ball_vector\": " + std::to_string(sizeof(BV<K, N>)) +
                      ", \"bytes_balls\": " + std::to_string(sizeof(Balls<K, N>)) + ", \"widths\": [";
    {
        Balls<K, N> b;
        BV<K, N> z;
        kairn::add(x, y, z);
        for (std::size_t i = 0; i < N; ++i) b[i] = bx[i] + by[i];
        out += wjson("add", width_of(z, b));
        kairn::sub(x, y, z);
        for (std::size_t i = 0; i < N; ++i) b[i] = bx[i] - by[i];
        out += ", " + wjson("sub", width_of(z, b));
        kairn::scale(x, kA, z);
        for (std::size_t i = 0; i < N; ++i) b[i] = bx[i] * kA;
        out += ", " + wjson("scale", width_of(z, b));
        kairn::axpy(kA, x, y, z);
        for (std::size_t i = 0; i < N; ++i) b[i] = bx[i] * kA + by[i];
        out += ", " + wjson("axpy", width_of(z, b));
        BV<K, 2 * N - 1> zc;
        Balls<K, 2 * N - 1> bc;
        kairn::convolution(x, y, zc);
        for (std::size_t j = 0; j < 2 * N - 1; ++j) {
            const std::size_t lo = j < N ? 0 : j - N + 1, hi = j < N ? j : N - 1;
            kairn::Ball<double, K> s = bx[lo] * by[j - lo];
            for (std::size_t i = lo + 1; i <= hi; ++i) s = s + bx[i] * by[j - i];
            bc[j] = s;
        }
        out += ", " + wjson("conv", width_of(zc, bc));
        double nb = 0;
        for (std::size_t i = 0; i < N; ++i)
            nb = std::max(nb, std::max(bx[i].template upper_as<double>(), -bx[i].template lower_as<double>()));
        out += ", {\"op\": \"norm\", \"one\": " + num(kairn::norm_upper(x)) + ", \"largest\": " + num(nb) +
               ", \"median\": " + num(nb) + "}";
    }
    for (int steps : {10, 100}) {
        BV<K, N> z = x;
        Balls<K, N> b = bx;
        for (int s = 0; s < steps; ++s) {
            const BV<K, N>& w = s % 2 ? y : x;
            const Balls<K, N>& bw = s % 2 ? by : bx;
            BV<K, N> t;
            kairn::axpy(kA, z, w, t);
            z = t;
            for (std::size_t i = 0; i < N; ++i) b[i] = b[i] * kA + bw[i];
        }
        out += ", " + wjson(steps == 10 ? "horner10" : "horner100", width_of(z, b));
    }
    for (int ops : {10, 100}) {
        BV<K, N> z = x;
        Balls<K, N> b = bx;
        for (int s = 0; s < ops / 2; ++s) {
            BV<K, N> t;
            kairn::add(z, rotated(z), t);
            kairn::half(t, z);
            Balls<K, N> nb;
            for (std::size_t i = 0; i < N; ++i) nb[i] = kairn::half(b[i] + b[(i + 1) % N]);
            b = nb;
        }
        out += ", " + wjson(ops == 10 ? "casteljau10" : "casteljau100", width_of(z, b));
    }
    return out + "]}";
}

}  // namespace

namespace kairn_bench::m2 {

std::string m2_bv_widths_json() {
    std::string out = "[";
    bool first = true;
    for (int regime = 0; regime < 3; ++regime)
        for (const std::string& s : {widths_kn<1, 4>(regime), widths_kn<1, 8>(regime), widths_kn<1, 16>(regime),
                                     widths_kn<1, 64>(regime), widths_kn<2, 4>(regime), widths_kn<2, 8>(regime),
                                     widths_kn<2, 16>(regime), widths_kn<2, 64>(regime)}) {
            out += (first ? "" : ", ") + s;
            first = false;
        }
    return out + "]";
}

}  // namespace kairn_bench::m2
