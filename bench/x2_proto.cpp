// The earlier scalar prototype (bench/x2_proto.hpp) on the operands of bench/x2_data.hpp, backend
// x2p, variant proto: a measurement prop, NOT VERIFIED. Requires the rounding mode upward: each
// timed function sets it with std::fesetround around its loop or chain and resets it after, in a
// unit compiled as m2_fenv.cpp (-frounding-math; FENV_ACCESS with Clang), without a Kairn header.
// The loads of a loop come after the call that sets the mode and its stores before the call that
// resets it. Arrays of the prototype's own storage, filled outside the timed functions.
#include <cfenv>
#include <cmath>
#include <cstring>
#include <string>

#include "up_data.hpp"
#include "x2_data.hpp"
#include "x2_proto.hpp"

#if defined(__clang__)
#pragma STDC FENV_ACCESS ON
#endif

namespace {

namespace x2 = kairn_bench::x2;
namespace u2 = kairn_bench::up2;
using kairn_bench::m2::Entry;
using kairn_bench::m2::kDeg;
using kairn_bench::m2::kN;

struct V2 {
    u2::Ival v;
};
KB_UP2_INLINE V2 operator+(const V2& a, const V2& b) { return {u2::iadd(a.v, b.v)}; }
KB_UP2_INLINE V2 operator-(const V2& a, const V2& b) { return {u2::isub(a.v, b.v)}; }
KB_UP2_INLINE V2 operator*(const V2& a, const V2& b) { return {u2::imul(a.v, b.v)}; }

V2 point(double t) {
    const double p[4] = {t, 0.0, t, 0.0};
    return {u2::load(p)};
}
struct ProtoData {
    V2 x[kN], y[kN], f[kN], h[kN], xp[kN], yp[kN], xz[kN], yz[kN], px[kN], py[kN], pz[kN], ht[kN];
    V2 z[kN];
    V2 hc[kDeg + 1];
    V2 s;
};
ProtoData* g = nullptr;

void fill() {
    if (!g) g = new ProtoData();
    const x2::Ops& o = x2::ops();
    for (int i = 0; i < kN; ++i) {
        g->x[i] = {u2::load(o.x + 4 * i)};
        g->y[i] = {u2::load(o.y + 4 * i)};
        g->f[i] = {u2::load(o.f + 4 * i)};
        g->h[i] = {u2::load(o.h + 4 * i)};
        g->xp[i] = {u2::load(o.xp + 4 * i)};
        g->yp[i] = {u2::load(o.yp + 4 * i)};
        g->xz[i] = {u2::load(o.xz + 4 * i)};
        g->yz[i] = {u2::load(o.yz + 4 * i)};
        g->px[i] = point(o.px[i]);
        g->py[i] = point(o.py[i]);
        g->pz[i] = point(o.pz[i]);
        g->ht[i] = point(o.ht[i]);
    }
    for (int k = 0; k <= kDeg; ++k) g->hc[k] = point(o.hc[k]);
}
void clear() {
    std::memset(static_cast<void*>(g->z), 0xff, sizeof g->z);
    std::memset(static_cast<void*>(&g->s), 0xff, sizeof g->s);
}
KB_UP2_INLINE V2 arg(const V2& h, double z) {
    V2 a = h;
    a.v.nl.h += z;
    a.v.hu.h += z;
    return a;
}
struct G3 {
    const ProtoData& d;
    const V2& x(int j) const { return d.px[j]; }
    const V2& y(int j) const { return d.py[j]; }
    const V2& z(int j) const { return d.pz[j]; }
};

}  // namespace

#define KB_EACH(...)                                                                               \
    for (int i = 0; i < kN; ++i) {                                                                 \
        __VA_ARGS__;                                                                               \
    }
#define KB_X2P_LIST(X)                                                                             \
    X(tp, interval_add_2, KB_EACH(g->z[i] = g->x[i] + g->y[i]))                                    \
    X(tp, interval_sub_2, KB_EACH(g->z[i] = g->x[i] - g->y[i]))                                    \
    X(tp, interval_mul_2, KB_EACH(g->z[i] = g->x[i] * g->y[i]))                                    \
    X(tp, interval_mul_2pos, KB_EACH(g->z[i] = g->xp[i] * g->yp[i]))                               \
    X(tp, interval_mul_2zero, KB_EACH(g->z[i] = g->xz[i] * g->yz[i]))                              \
    X(sum, interval_add_2, V2 s = point(0.0); KB_EACH(s = s + g->x[i]) g->s = s;)                  \
    X(prod, interval_mul_2, V2 p = point(1.0); KB_EACH(p = p * g->f[i]) g->s = p;)                 \
    X(tp, horner_i2, KB_EACH(g->z[i] = x2::horner2(g->hc, g->h[i])))                               \
    X(lat, horner_i2, double zz = 0; V2 p = point(0.0);                                            \
      KB_EACH(p = x2::horner2(g->hc, arg(g->h[i], zz)); zz = p.v.hu.h * 0.0) g->s = p;)            \
    X(tp, horner_pt, KB_EACH(g->z[i] = x2::horner2(g->hc, g->ht[i])))                              \
    X(tp, det3pt, const G3 q{*g}; KB_EACH(g->z[i] = x2::det3pt_at<V2>(q, i)))

#define KB_X2P_DEF(KIND, KERNEL, ...)                                                              \
    extern "C" KB_NOINLINE void kb_x2p_##KIND##_##KERNEL##__proto(void*) {                         \
        std::fesetround(FE_UPWARD);                                                                \
        __VA_ARGS__                                                                                \
        std::fesetround(FE_TONEAREST);                                                             \
    }
KB_X2P_LIST(KB_X2P_DEF)

namespace {

V2 vread(const V2& a) {
    const volatile double* q = reinterpret_cast<const volatile double*>(&a);
    return {{{q[0], q[1]}, {q[2], q[3]}}};
}
struct VG3 {
    const ProtoData& d;
    V2 x(int j) const { return vread(d.px[j]); }
    V2 y(int j) const { return vread(d.py[j]); }
    V2 z(int j) const { return vread(d.pz[j]); }
};

int read(const char* name, double* out) {
    const std::string n = name;
    if (n.find("/tp/") == std::string::npos) {
        u2::store(g->s.v, out);
        return 1;
    }
    for (int i = 0; i < kN; ++i) u2::store(g->z[i].v, out + 4 * i);
    return kN;
}
int reference(const char* name, double* out) {
    const std::string n = name;
    std::fesetround(FE_UPWARD);
    int count = kN;
    if (n.find("/tp/") != std::string::npos) {
        const VG3 q{*g};
        for (int i = 0; i < kN; ++i) {
            V2 r;
            if (n.find("interval_add_2") != std::string::npos) r = vread(g->x[i]) + vread(g->y[i]);
            else if (n.find("interval_sub_2") != std::string::npos) r = vread(g->x[i]) - vread(g->y[i]);
            else if (n.find("interval_mul_2pos") != std::string::npos) r = vread(g->xp[i]) * vread(g->yp[i]);
            else if (n.find("interval_mul_2zero") != std::string::npos) r = vread(g->xz[i]) * vread(g->yz[i]);
            else if (n.find("interval_mul_2") != std::string::npos) r = vread(g->x[i]) * vread(g->y[i]);
            else if (n.find("horner_i2") != std::string::npos) r = x2::horner2(g->hc, vread(g->h[i]));
            else if (n.find("horner_pt") != std::string::npos) r = x2::horner2(g->hc, vread(g->ht[i]));
            else r = x2::det3pt_at<V2>(q, i);
            u2::store(r.v, out + 4 * i);
        }
    } else {
        V2 s = point(n.find("/prod/") != std::string::npos ? 1.0 : 0.0);
        double zz = 0;
        for (int i = 0; i < kN; ++i) {
            if (n.find("/sum/") != std::string::npos) s = s + vread(g->x[i]);
            else if (n.find("/prod/") != std::string::npos) s = s * vread(g->f[i]);
            else {
                s = x2::horner2(g->hc, arg(vread(g->h[i]), zz));
                zz = s.v.hu.h * 0.0;
            }
        }
        u2::store(s.v, out);
        count = 1;
    }
    std::fesetround(FE_TONEAREST);
    return count;
}
void step(const char* name, const double* before, int k, double* after) {
    const std::string n = name;
    std::fesetround(FE_UPWARD);
    const V2 s{u2::load(before)};
    const V2 r = n.find("/sum/") != std::string::npos ? s + vread(g->x[k]) : s * vread(g->f[k]);
    u2::store(r.v, after);   // before the reset: a store is not moved past the call
    std::fesetround(FE_TONEAREST);
}

x2::Unit unit{"x2p", fill, clear, read, reference, step, nullptr};
[[maybe_unused]] const bool unit_registered = (unit.next = x2::units, x2::units = &unit, true);

#define KB_X2P_ROW(KIND, KERNEL, ...)                                                              \
    {"x2p/" #KIND "/" #KERNEL "/proto", kb_x2p_##KIND##_##KERNEL##__proto, 64, 1, kN, 0, 0, x2::check},
const Entry table[] = {
    KB_X2P_LIST(KB_X2P_ROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
kairn_bench::m2::TableLink link{table, nullptr};
[[maybe_unused]] const bool registered =
    (link.next = kairn_bench::m2::m2_extra_tables, kairn_bench::m2::m2_extra_tables = &link, true);

}  // namespace
