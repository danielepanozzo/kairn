// Short ball vectors of fixed length and the check of the environment at entry (bench/m2_data.hpp;
// bench/README.md, "Milestone 2", third part), backend m2x, double limbs: the operations a program
// applies to many small polynomials, BallVector<double, k, N> for N = 3, 7, 13, 18 and 80, k = 1, 2.
// Compiled with the flags of packed code, as m2_bv.cpp. With kairn-bench-m2-nocheck-LEVEL, the same
// program against a copy of the headers without the check (bench/entry_check.py), the difference is
// what the check costs these operations, the read of the control register and whatever the compiler
// does differently with it.
//
// Kernels: OP_k_N, OP one of
//   add     kairn::add(x, y, z), z a BallVector
//   addop   z = x + y, the operator, which returns a BallVector
//   sub     kairn::sub(x, y, z)
//   scale   kairn::scale(x, a, z), a = 0.6875
//   half    kairn::half(x, z)
//   make    z = BallVector(c, r), the constructor from an std::array of centers and a radius
// KIND tp: the operation on M = min(256, max(8, 1024 / N)) vectors of operands of their own, the time
// per operation; KIND lat: a chain of 256 operations, each on the result of the one before (add: + y
// and + (-y) in turn; sub: - y and - (-y); scale: by a and by 1/a; half: half and ldexp by 2; make:
// the radius of each vector the radius of the one made before), the time per operation.
// Variants: op (the public operation) and kairn (the generated loop it calls, called directly on
// arrays of the same values: the reference, and the operation without the check). Every function is
// checked before it is timed against the generated loops, byte for byte.
#include <kairn/ball_vector.hpp>
#include <kairn/kairn.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstring>
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

#define KB_SI KAIRN_GEN_FORCEINLINE
#if KAIRN_PACKED_FORM != KAIRN_PACKED_FORM_SCALAR
#define KB_FAST(NAME) kg::NAME##_packed
#else
#define KB_FAST(NAME) kg::NAME##_seq
#endif

constexpr double kA = 0.6875;
constexpr int kSteps = 256;

template <std::size_t N>
constexpr int vectors() {
    return int(std::min<std::size_t>(256, std::max<std::size_t>(8, 1024 / N)));
}

template <int K, std::size_t N>
struct Raw {
    double c[K][N];
    double r;
};

template <int K, std::size_t N>
struct SSet {
    static constexpr int M = vectors<N>();
    std::vector<BV<K, N>> x, y, w, z;            // operands, -y, results
    std::vector<std::array<E<K>, N>> c;          // centers for the constructor
    std::vector<double> r;                        // radii for the constructor
    std::vector<Raw<K, N>> rx, ry, rw, rz;        // the same values, for the generated loops
    BV<K, N> chain;                               // the end of a chain
    Raw<K, N> rchain;
};

template <int K, std::size_t N>
SSet<K, N>* g_sset = nullptr;
template <int K, std::size_t N>
SSet<K, N>& sset() {
    return *g_sset<K, N>;
}

// The generated loops on Raw, as ball_vector.hpp calls them (the fast order; the constructor's loop
// in the sequential order in every build).
template <int K, std::size_t N>
KB_SI void raw_add(const Raw<K, N>& x, const Raw<K, N>& y, Raw<K, N>& z, bool sub) {
    const double rx = x.r, ry = y.r;
    bool f = false;
    if constexpr (K == 1) {
        if (sub) KB_FAST(bv_sub_1)(x.c[0], y.c[0], N, rx, ry, z.c[0], z.r, f);
        else KB_FAST(bv_add_1)(x.c[0], y.c[0], N, rx, ry, z.c[0], z.r, f);
    } else {
        if (sub) KB_FAST(bv_sub_2)(x.c[0], x.c[1], y.c[0], y.c[1], N, rx, ry, z.c[0], z.c[1], z.r, f);
        else KB_FAST(bv_add_2)(x.c[0], x.c[1], y.c[0], y.c[1], N, rx, ry, z.c[0], z.c[1], z.r, f);
    }
}
template <int K, std::size_t N>
KB_SI void raw_scale(const Raw<K, N>& x, double a, Raw<K, N>& z) {
    const double rx = x.r;
    bool f = false;
    if constexpr (K == 1) {
        KB_FAST(bv_scale_1)(x.c[0], N, rx, a, z.c[0], z.r, f);
    } else {
        KB_FAST(bv_scale_2)(x.c[0], x.c[1], N, rx, a, z.c[0], z.c[1], z.r, f);
    }
}
template <int K, std::size_t N>
KB_SI void raw_pow2(const Raw<K, N>& x, double c, Raw<K, N>& z) {
    const double rx = x.r;
    bool f = false;
    if constexpr (K == 1) {
        KB_FAST(bv_mul_pow2_1)(x.c[0], N, rx, c, z.c[0], z.r, f);
    } else {
        KB_FAST(bv_mul_pow2_2)(x.c[0], x.c[1], N, rx, c, z.c[0], z.c[1], z.r, f);
    }
}
template <int K, std::size_t N>
KB_SI void raw_make(const std::array<E<K>, N>& c, double r, Raw<K, N>& z) {
    double in[K][N];
    for (int j = 0; j < K; ++j)
        for (std::size_t i = 0; i < N; ++i) in[j][i] = c[i].limb[j];
    bool f = false;
    if constexpr (K == 1) {
        kg::bv_make_1_seq(in[0], N, r, z.c[0], z.r, f);
    } else {
        kg::bv_make_2_seq(in[0], in[1], N, r, z.c[0], z.c[1], z.r, f);
    }
}

// tp: one operation per vector.
template <int K, std::size_t N> KB_SI void add_tp_op(SSet<K, N>& d) {
    for (int m = 0; m < d.M; ++m) kairn::add(d.x[m], d.y[m], d.z[m]);
}
template <int K, std::size_t N> KB_SI void add_tp_kairn(SSet<K, N>& d) {
    for (int m = 0; m < d.M; ++m) raw_add(d.rx[m], d.ry[m], d.rz[m], false);
}
template <int K, std::size_t N> KB_SI void addop_tp_op(SSet<K, N>& d) {
    for (int m = 0; m < d.M; ++m) d.z[m] = d.x[m] + d.y[m];
}
template <int K, std::size_t N> KB_SI void addop_tp_kairn(SSet<K, N>& d) { add_tp_kairn(d); }
template <int K, std::size_t N> KB_SI void sub_tp_op(SSet<K, N>& d) {
    for (int m = 0; m < d.M; ++m) kairn::sub(d.x[m], d.y[m], d.z[m]);
}
template <int K, std::size_t N> KB_SI void sub_tp_kairn(SSet<K, N>& d) {
    for (int m = 0; m < d.M; ++m) raw_add(d.rx[m], d.ry[m], d.rz[m], true);
}
template <int K, std::size_t N> KB_SI void scale_tp_op(SSet<K, N>& d) {
    for (int m = 0; m < d.M; ++m) kairn::scale(d.x[m], kA, d.z[m]);
}
template <int K, std::size_t N> KB_SI void scale_tp_kairn(SSet<K, N>& d) {
    for (int m = 0; m < d.M; ++m) raw_scale(d.rx[m], kA, d.rz[m]);
}
template <int K, std::size_t N> KB_SI void half_tp_op(SSet<K, N>& d) {
    for (int m = 0; m < d.M; ++m) kairn::half(d.x[m], d.z[m]);
}
template <int K, std::size_t N> KB_SI void half_tp_kairn(SSet<K, N>& d) {
    for (int m = 0; m < d.M; ++m) raw_pow2(d.rx[m], 0.5, d.rz[m]);
}
template <int K, std::size_t N> KB_SI void make_tp_op(SSet<K, N>& d) {
    for (int m = 0; m < d.M; ++m) d.z[m] = BV<K, N>(d.c[m], d.r[m]);
}
template <int K, std::size_t N> KB_SI void make_tp_kairn(SSet<K, N>& d) {
    for (int m = 0; m < d.M; ++m) raw_make(d.c[m], d.r[m], d.rz[m]);
}

// lat: 256 operations, each on the result of the one before.
template <int K, std::size_t N> KB_SI void add_lat_op(SSet<K, N>& d) {
    BV<K, N>& z = d.chain;
    z = d.x[0];
    for (int j = 0; j < kSteps; ++j) kairn::add(z, (j & 1) ? d.w[j % d.M] : d.y[j % d.M], z);
}
template <int K, std::size_t N> KB_SI void add_lat_kairn(SSet<K, N>& d) {
    Raw<K, N>& z = d.rchain;
    z = d.rx[0];
    for (int j = 0; j < kSteps; ++j) raw_add(z, (j & 1) ? d.rw[j % d.M] : d.ry[j % d.M], z, false);
}
template <int K, std::size_t N> KB_SI void addop_lat_op(SSet<K, N>& d) {
    BV<K, N>& z = d.chain;
    z = d.x[0];
    for (int j = 0; j < kSteps; ++j) z = z + ((j & 1) ? d.w[j % d.M] : d.y[j % d.M]);
}
template <int K, std::size_t N> KB_SI void addop_lat_kairn(SSet<K, N>& d) { add_lat_kairn(d); }
template <int K, std::size_t N> KB_SI void sub_lat_op(SSet<K, N>& d) {
    BV<K, N>& z = d.chain;
    z = d.x[0];
    for (int j = 0; j < kSteps; ++j) kairn::sub(z, (j & 1) ? d.w[j % d.M] : d.y[j % d.M], z);
}
template <int K, std::size_t N> KB_SI void sub_lat_kairn(SSet<K, N>& d) {
    Raw<K, N>& z = d.rchain;
    z = d.rx[0];
    for (int j = 0; j < kSteps; ++j) raw_add(z, (j & 1) ? d.rw[j % d.M] : d.ry[j % d.M], z, true);
}
template <int K, std::size_t N> KB_SI void scale_lat_op(SSet<K, N>& d) {
    BV<K, N>& z = d.chain;
    z = d.x[0];
    for (int j = 0; j < kSteps; ++j) kairn::scale(z, (j & 1) ? 1 / kA : kA, z);
}
template <int K, std::size_t N> KB_SI void scale_lat_kairn(SSet<K, N>& d) {
    Raw<K, N>& z = d.rchain;
    z = d.rx[0];
    for (int j = 0; j < kSteps; ++j) raw_scale(z, (j & 1) ? 1 / kA : kA, z);
}
template <int K, std::size_t N> KB_SI void half_lat_op(SSet<K, N>& d) {
    BV<K, N>& z = d.chain;
    z = d.x[0];
    for (int j = 0; j < kSteps; ++j) {
        if (j & 1) {
            kairn::ldexp(z, 1, z);
        } else {
            kairn::half(z, z);
        }
    }
}
template <int K, std::size_t N> KB_SI void half_lat_kairn(SSet<K, N>& d) {
    Raw<K, N>& z = d.rchain;
    z = d.rx[0];
    for (int j = 0; j < kSteps; ++j) raw_pow2(z, (j & 1) ? 2.0 : 0.5, z);
}
template <int K, std::size_t N> KB_SI void make_lat_op(SSet<K, N>& d) {
    BV<K, N>& z = d.chain;
    z = d.x[0];
    for (int j = 0; j < kSteps; ++j) z = BV<K, N>(d.c[j % d.M], z.radius());
}
template <int K, std::size_t N> KB_SI void make_lat_kairn(SSet<K, N>& d) {
    Raw<K, N>& z = d.rchain;
    z = d.rx[0];
    for (int j = 0; j < kSteps; ++j) raw_make(d.c[j % d.M], z.r, z);
}

}  // namespace

#if defined(KB_BVS_ONE)
// One operation of one size in a unit of its own (backend m2y; bench/CMakeLists.txt writes one such
// unit per operation, limb count and size), as a client's file holds a few: a compiler that has the
// whole unit to itself may inline the loop, which GCC does not do in the unit of every size (m2x),
// where it reaches its limit of the growth of a unit. The table registers itself with the driver.
#define KB_BACKEND "m2y"
#define KB_XLIST(X)                                                                                \
    X(KB_BVS_K, KB_BVS_N, KB_BVS_OP, tp, op) X(KB_BVS_K, KB_BVS_N, KB_BVS_OP, tp, kairn)            \
    X(KB_BVS_K, KB_BVS_N, KB_BVS_OP, lat, op) X(KB_BVS_K, KB_BVS_N, KB_BVS_OP, lat, kairn)
#else
#define KB_BACKEND "m2x"
#define KB_XOPS(X, K, N)                                                                           \
    X(K, N, add, tp, op) X(K, N, add, tp, kairn) X(K, N, addop, tp, op) X(K, N, sub, tp, op)       \
    X(K, N, sub, tp, kairn) X(K, N, scale, tp, op) X(K, N, scale, tp, kairn) X(K, N, half, tp, op) \
    X(K, N, half, tp, kairn) X(K, N, make, tp, op) X(K, N, make, tp, kairn)                        \
    X(K, N, add, lat, op) X(K, N, add, lat, kairn) X(K, N, addop, lat, op) X(K, N, sub, lat, op)   \
    X(K, N, sub, lat, kairn) X(K, N, scale, lat, op) X(K, N, scale, lat, kairn)                    \
    X(K, N, half, lat, op) X(K, N, half, lat, kairn) X(K, N, make, lat, op) X(K, N, make, lat, kairn)
#define KB_XLIST(X)                                                                                \
    KB_XOPS(X, 1, 3) KB_XOPS(X, 1, 7) KB_XOPS(X, 1, 13) KB_XOPS(X, 1, 18) KB_XOPS(X, 1, 80)        \
    KB_XOPS(X, 2, 3) KB_XOPS(X, 2, 7) KB_XOPS(X, 2, 13) KB_XOPS(X, 2, 18) KB_XOPS(X, 2, 80)
#endif

#if defined(KB_BVS_ONE)
#define KB_XNAME_(KIND, OP, K, N, VAR) kb_m2_y64_##KIND##_##OP##_##K##_##N##__##VAR
#else
#define KB_XNAME_(KIND, OP, K, N, VAR) kb_m2_x64_##KIND##_##OP##_##K##_##N##__##VAR
#endif
#define KB_XNAME(KIND, OP, K, N, VAR) KB_XNAME_(KIND, OP, K, N, VAR)
#define KB_XDEF_(K, N, OP, KIND, VAR)                                                              \
    extern "C" KB_NOINLINE void KB_XNAME(KIND, OP, K, N, VAR)(void*) { OP##_##KIND##_##VAR<K, N>(sset<K, N>()); }
#define KB_XDEF(K, N, OP, KIND, VAR) KB_XDEF_(K, N, OP, KIND, VAR)
KB_XLIST(KB_XDEF)

namespace {
bool check_one(const kairn_bench::m2::Entry& e, char* why, std::size_t size);
}

#define KB_XROW_(K, N, OP, KIND, VAR)                                                              \
    {KB_BACKEND "/" #KIND "/" #OP "_" #K "_" #N "/" #VAR, KB_XNAME(KIND, OP, K, N, VAR), 64, 1,     \
     std::string(#KIND) == "tp" ? vectors<N>() : kSteps, K * 1000 + N, 0, &check_one},
#define KB_XROW(K, N, OP, KIND, VAR) KB_XROW_(K, N, OP, KIND, VAR)

#if defined(KB_BVS_ONE)
namespace {
const Entry table_one[] = {
    KB_XLIST(KB_XROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
kairn_bench::m2::TableLink link_one{table_one, nullptr};
const bool registered_one = (link_one.next = kairn_bench::m2::m2_extra_tables,
                             kairn_bench::m2::m2_extra_tables = &link_one, true);
const Entry* own_table() {
    (void)registered_one;
    return table_one;
}
}  // namespace
#else
namespace kairn_bench::m2 {
const Entry m2_bvs_entries[] = {
    KB_XLIST(KB_XROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
}  // namespace kairn_bench::m2
namespace {
const Entry* own_table() { return kairn_bench::m2::m2_bvs_entries; }
}  // namespace
#endif

// --- The data and the checks --------------------------------------------------------------------

namespace {

template <int K>
E<K> center(kairn_bench::util::Rng& g) {
    const double s = g.sign();
    const double h = s * std::ldexp(1.0 + g.u01(), g.range(-8, 8));
    if constexpr (K == 1) {
        return E<1>(h);
    } else {
        double limbs[2];
        kg::fast_two_sum(h, h * g.sym() * 0x1p-53, limbs[0], limbs[1]);
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
    if (g_sset<K, N>) return;
    SSet<K, N>* d = new SSet<K, N>();
    kairn_bench::util::Rng g{seed};
    const int M = SSet<K, N>::M;
    d->x.resize(M);
    d->y.resize(M);
    d->w.resize(M);
    d->z.resize(M);
    d->c.resize(M);
    d->r.resize(M);
    d->rx.resize(M);
    d->ry.resize(M);
    d->rw.resize(M);
    d->rz.resize(M);
    for (int m = 0; m < M; ++m) {
        std::array<E<K>, N> cx, cy, cw;
        for (std::size_t i = 0; i < N; ++i) {
            cx[i] = center<K>(g);
            cy[i] = center<K>(g);
            cw[i] = -cy[i];
            d->c[m][i] = center<K>(g);
        }
        d->x[m] = BV<K, N>(cx, 0x1p-22);
        d->y[m] = BV<K, N>(cy, 0x1p-22);
        d->w[m] = BV<K, N>(cw, 0x1p-22);
        d->r[m] = 0x1p-22 * (1 + g.u01());
        to_raw(d->x[m], d->rx[m]);
        to_raw(d->y[m], d->ry[m]);
        to_raw(d->w[m], d->rw[m]);
    }
    g_sset<K, N> = d;
}

void make_all() {
#if defined(KB_BVS_ONE)
    make<KB_BVS_K, KB_BVS_N>(500 + 10 * KB_BVS_K + KB_BVS_N);
#else
    make<1, 3>(501);
    make<1, 7>(502);
    make<1, 13>(503);
    make<1, 18>(504);
    make<1, 80>(505);
    make<2, 3>(506);
    make<2, 7>(507);
    make<2, 13>(508);
    make<2, 18>(509);
    make<2, 80>(510);
#endif
}

template <int K, std::size_t N>
std::vector<double> read(SSet<K, N>& d, bool lat, bool raw) {
    std::vector<double> v;
    auto put = [&v](const BV<K, N>& b) {
        for (int j = 0; j < K; ++j) v.insert(v.end(), b.limb(j), b.limb(j) + N);
        v.push_back(b.radius());
    };
    auto putr = [&v](const Raw<K, N>& b) {
        for (int j = 0; j < K; ++j) v.insert(v.end(), b.c[j], b.c[j] + N);
        v.push_back(b.r);
    };
    if (lat) {
        if (raw) putr(d.rchain);
        else put(d.chain);
    } else {
        for (int m = 0; m < d.M; ++m) {
            if (raw) putr(d.rz[m]);
            else put(d.z[m]);
        }
    }
    return v;
}

template <int K, std::size_t N>
void clear(SSet<K, N>& d) {
    for (int m = 0; m < d.M; ++m) {
        std::memset(static_cast<void*>(&d.z[m]), 0xff, sizeof d.z[m]);
        std::memset(static_cast<void*>(&d.rz[m]), 0xff, sizeof d.rz[m]);
    }
    std::memset(static_cast<void*>(&d.chain), 0xff, sizeof d.chain);
    std::memset(static_cast<void*>(&d.rchain), 0xff, sizeof d.rchain);
}

const Entry* find_entry(const std::string& name) {
    for (const Entry* e = own_table(); e->name; ++e)
        if (name == e->name) return e;
    return nullptr;
}

template <int K, std::size_t N>
bool check_kn(const Entry& e, char* why, std::size_t size) {
    SSet<K, N>& d = sset<K, N>();
    const std::string name = e.name;   // m2x/KIND/OP_K_N/VAR
    const bool lat = name.find("/lat/") != std::string::npos;
    const bool raw = name.substr(name.rfind('/') + 1) == "kairn";
    clear(d);
    e.fn(nullptr);
    const std::vector<double> got = read(d, lat, raw);
    for (const double x : got)
        if (!std::isfinite(x)) {
            std::snprintf(why, size, "a value is not finite");
            return false;
        }
    if (raw) return true;   // the reference
    // The reference: the same kernel's kairn variant (addop's is add's).
    std::string stem = name.substr(0, name.rfind('/'));
#if !defined(KB_BVS_ONE)
    const std::size_t at = stem.find("/addop_");
    if (at != std::string::npos) stem.replace(at, 7, "/add_");
#endif
    const Entry* r = find_entry(stem + "/kairn");
    if (!r) {
        std::snprintf(why, size, "no reference %s/kairn", stem.c_str());
        return false;
    }
    clear(d);
    r->fn(nullptr);
    const std::vector<double> want = read(d, lat, true);
    if (want.size() != got.size() || std::memcmp(want.data(), got.data(), got.size() * sizeof(double)) != 0) {
        std::snprintf(why, size, "not the bytes of the generated loops");
        return false;
    }
    return true;
}

}  // namespace

namespace {

bool check_one(const kairn_bench::m2::Entry& e, char* why, std::size_t size) {
    make_all();
#if defined(KB_BVS_ONE)
    return check_kn<KB_BVS_K, KB_BVS_N>(e, why, size);
#else
    switch (e.region) {
        case 1003: return check_kn<1, 3>(e, why, size);
        case 1007: return check_kn<1, 7>(e, why, size);
        case 1013: return check_kn<1, 13>(e, why, size);
        case 1018: return check_kn<1, 18>(e, why, size);
        case 1080: return check_kn<1, 80>(e, why, size);
        case 2003: return check_kn<2, 3>(e, why, size);
        case 2007: return check_kn<2, 7>(e, why, size);
        case 2013: return check_kn<2, 13>(e, why, size);
        case 2018: return check_kn<2, 18>(e, why, size);
        default: return check_kn<2, 80>(e, why, size);
    }
#endif
}

}  // namespace
