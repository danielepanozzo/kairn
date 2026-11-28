// The default two-limb enclosures of Kairn on the operands of the experimental two-limb interval
// rounded upward that the benchmark of Milestone 2 does not have (bench/x2_data.hpp), backend x2d:
// kairn::Interval<double, 2> (variant i2) and kairn::Ball<double, 2> (b2), through their public
// operators, on the determinant of points (tp/det3pt), the products of one sign
// (tp/interval_mul_2pos) and around zero (tp/interval_mul_2zero), Horner on points (tp/horner_pt).
// Ordinary code, compiled as m2.cpp, under rounding to nearest. The loops and chains of the
// benchmark's own operands are m2.cpp's (m2/tp/interval_add_2/op, m2/tp/ball_add_2/op, ...).
// Arrays of the types filled outside the timed functions, placed as up_data.hpp says.
#include <kairn/kairn.hpp>

#include <cstring>
#include <new>

#include "up_data.hpp"
#include "x2_data.hpp"

namespace {

namespace x2 = kairn_bench::x2;
namespace up = kairn_bench::up;
using kairn_bench::m2::Entry;
using kairn_bench::m2::kDeg;
using kairn_bench::m2::kN;
using I2 = kairn::Interval<double, 2>;
using B2 = kairn::Ball<double, 2>;

template <class V>
V* arr(const up::Placed& p, int k) {
    V* q = p.at<V>(k);
    for (int i = 0; i < kN; ++i) new (q + i) V();
    return q;
}
struct DefData {
    up::Placed a{kN * sizeof(I2)}, b{kN * sizeof(I2)};
    I2* xp = arr<I2>(a, 0);
    I2* yp = arr<I2>(a, 1);
    I2* xz = arr<I2>(a, 4);
    I2* yz = arr<I2>(a, 5);
    I2* zi = arr<I2>(a, 8);
    I2* zj = arr<I2>(a, 10);
    I2* px = arr<I2>(b, 0);
    I2* py = arr<I2>(b, 1);
    I2* pz = arr<I2>(b, 2);
    I2* ht = arr<I2>(b, 3);
    B2* bx = arr<B2>(b, 4);
    B2* by = arr<B2>(b, 5);
    B2* bz = arr<B2>(b, 6);
    B2* bt = arr<B2>(b, 7);
    B2* zb = arr<B2>(b, 8);
    I2* zk = arr<I2>(b, 10);
    B2* bxp = new B2[kN];
    B2* byp = new B2[kN];
    B2* bxz = new B2[kN];
    B2* byz = new B2[kN];
    B2* zbb = new B2[kN];
    I2 hc[kDeg + 1];
    B2 hcb[kDeg + 1];
};
DefData* g = nullptr;

// What a timed function reaches, in its locals (the repair of x2_type.cpp's Local, for the same
// reason).
struct Local {
    I2 *xp, *yp, *xz, *yz, *zi, *zj, *px, *py, *pz, *ht;
    B2 *bx, *by, *bz, *bt, *zb;
    I2* zk;
    B2 *bxp, *byp, *bxz, *byz, *zbb;
    const I2* hc;
    const B2* hcb;
};
Local local(DefData& d) {
    return {d.xp, d.yp, d.xz, d.yz, d.zi, d.zj, d.px, d.py, d.pz, d.ht, d.bx, d.by, d.bz, d.bt, d.zb,
            d.zk, d.bxp, d.byp, d.bxz, d.byz, d.zbb, d.hc, d.hcb};
}

void fill() {
    if (!g) g = new DefData();
    const x2::Ops& o = x2::ops();
    for (int i = 0; i < kN; ++i) {
        g->xp[i] = I2::from_limbs(o.xp + 4 * i);
        g->yp[i] = I2::from_limbs(o.yp + 4 * i);
        g->xz[i] = I2::from_limbs(o.xz + 4 * i);
        g->yz[i] = I2::from_limbs(o.yz + 4 * i);
        g->bxp[i] = B2(g->xp[i]);
        g->byp[i] = B2(g->yp[i]);
        g->bxz[i] = B2(g->xz[i]);
        g->byz[i] = B2(g->yz[i]);
        g->px[i] = I2(o.px[i]);
        g->py[i] = I2(o.py[i]);
        g->pz[i] = I2(o.pz[i]);
        g->ht[i] = I2(o.ht[i]);
        g->bx[i] = B2(o.px[i]);
        g->by[i] = B2(o.py[i]);
        g->bz[i] = B2(o.pz[i]);
        g->bt[i] = B2(o.ht[i]);
    }
    for (int k = 0; k <= kDeg; ++k) {
        g->hc[k] = I2(o.hc[k]);
        g->hcb[k] = B2(o.hc[k]);
    }
}
void clear() {
    for (I2* a : {g->zi, g->zj, g->zk}) std::memset(static_cast<void*>(a), 0xff, kN * sizeof(I2));
    for (B2* a : {g->zb, g->zbb}) std::memset(static_cast<void*>(a), 0xff, kN * sizeof(B2));
}
struct GI {
    const Local& d;
    const I2& x(int j) const { return d.px[j]; }
    const I2& y(int j) const { return d.py[j]; }
    const I2& z(int j) const { return d.pz[j]; }
};
struct GB {
    const Local& d;
    const B2& x(int j) const { return d.bx[j]; }
    const B2& y(int j) const { return d.by[j]; }
    const B2& z(int j) const { return d.bz[j]; }
};

}  // namespace

#define KB_EACH(...)                                                                               \
    for (int i = 0; i < kN; ++i) {                                                                 \
        __VA_ARGS__;                                                                               \
    }
#define KB_X2D_LIST(X)                                                                             \
    X(tp, det3pt, i2, const GI q{*g}; KB_EACH(g->zk[i] = x2::det3pt_at<I2>(q, i)))                \
    X(tp, det3pt, b2, const GB q{*g}; KB_EACH(g->zb[i] = x2::det3pt_at<B2>(q, i)))                \
    X(tp, interval_mul_2pos, i2, KB_EACH(g->zi[i] = g->xp[i] * g->yp[i]))                          \
    X(tp, interval_mul_2pos, b2, KB_EACH(g->zbb[i] = g->bxp[i] * g->byp[i]))                       \
    X(tp, interval_mul_2zero, i2, KB_EACH(g->zj[i] = g->xz[i] * g->yz[i]))                         \
    X(tp, interval_mul_2zero, b2, KB_EACH(g->zbb[i] = g->bxz[i] * g->byz[i]))                      \
    X(tp, horner_pt, i2, KB_EACH(g->zk[i] = x2::horner2(g->hc, g->ht[i])))                         \
    X(tp, horner_pt, b2, KB_EACH(g->zb[i] = x2::horner2(g->hcb, g->bt[i])))

#define KB_X2D_DEF(KIND, KERNEL, VAR, ...)                                                         \
    extern "C" KB_NOINLINE void kb_x2d_##KIND##_##KERNEL##__##VAR(void*) {                         \
        const Local lg = local(*g);                                                                \
        [[maybe_unused]] const Local* const g = &lg;                                               \
        __VA_ARGS__                                                                                \
    }
KB_X2D_LIST(KB_X2D_DEF)

namespace {

void put(const I2& v, double* o) {
    o[0] = v.lower().limb[0];
    o[1] = v.lower().limb[1];
    o[2] = v.upper().limb[0];
    o[3] = v.upper().limb[1];
}
void put(const B2& v, double* o) { put(I2(v), o); }

int read(const char* name, double* out) {
    const std::string n = name;
    const bool ball = n.size() > 3 && n.compare(n.size() - 3, 3, "/b2") == 0;
    for (int i = 0; i < kN; ++i) {
        if (n.find("/det3pt/") != std::string::npos || n.find("/horner_pt/") != std::string::npos) {
            if (ball) put(g->zb[i], out + 4 * i);
            else put(g->zk[i], out + 4 * i);
        } else if (ball) {
            put(g->zbb[i], out + 4 * i);
        } else {
            put(n.find("2pos") != std::string::npos ? g->zi[i] : g->zj[i], out + 4 * i);
        }
    }
    return kN;
}

x2::Unit unit{"x2d", fill, clear, read, nullptr, nullptr, nullptr};
[[maybe_unused]] const bool unit_registered = (unit.next = x2::units, x2::units = &unit, true);

#define KB_X2D_ROW(KIND, KERNEL, VAR, ...)                                                         \
    {"x2d/" #KIND "/" #KERNEL "/" #VAR, kb_x2d_##KIND##_##KERNEL##__##VAR, 64, 1, kN, 0, 0, x2::check},
const Entry table[] = {
    KB_X2D_LIST(KB_X2D_ROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
kairn_bench::m2::TableLink link{table, nullptr};
[[maybe_unused]] const bool registered =
    (link.next = kairn_bench::m2::m2_extra_tables, kairn_bench::m2::m2_extra_tables = &link, true);

}  // namespace
