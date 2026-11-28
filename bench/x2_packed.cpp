// Kairn's packed kernels of the default Interval<double, 2> (interval_add_2, interval_mul_2 of
// kairn/gen/avx2.hpp or neon.hpp, as m2_packed.cpp times them) on the operands X2, Y2 of
// bench/x2_data.hpp, one array per limb (l0, l1, h0, h1), placed as up_data.hpp says (m2_packed.cpp's
// arrays are not): backend x2k, variant packed, time per element, the comparison of the functions on
// arrays of the experimental two-limb interval rounded upward (x2_arrays.cpp). Ordinary code,
// compiled as packed code is (m2_packed.cpp), under rounding to nearest.
#include <cstring>

#include "props_packed.hpp"
#include "up_data.hpp"
#include "x2_data.hpp"

#if defined(KB_PACKED)

namespace {

namespace x2 = kairn_bench::x2;
namespace up = kairn_bench::up;
namespace kg = kairn::gen;
namespace kp = kairn_bench::packed;
using kairn_bench::m2::Entry;
using kairn_bench::m2::kN;
using kp::load;
using kp::store;
using kp::V;
using kp::W;

struct PkData {
    up::Placed a{kN * sizeof(double)}, b{kN * sizeof(double)};
    double* x[4] = {a.at<double>(0), a.at<double>(1), a.at<double>(2), a.at<double>(3)};   // l0 l1 h0 h1
    double* y[4] = {a.at<double>(4), a.at<double>(5), a.at<double>(6), a.at<double>(7)};
    double* z[4] = {a.at<double>(8), a.at<double>(9), a.at<double>(10), b.at<double>(9)};
};
PkData* g = nullptr;

void fill() {
    if (!g) g = new PkData();
    const x2::Ops& o = x2::ops();
    for (int i = 0; i < kN; ++i)
        for (int k = 0; k < 4; ++k) {
            g->x[k][i] = o.x[4 * i + k];
            g->y[k][i] = o.y[4 * i + k];
        }
}
void clear() {
    for (double* p : g->z) std::memset(p, 0xff, kN * sizeof(double));
}
int read(const char*, double* out) {
    for (int i = 0; i < kN; ++i)
        for (int k = 0; k < 4; ++k) out[4 * i + k] = g->z[k][i];
    return kN;
}

x2::Unit unit{"x2k", fill, clear, read, nullptr, nullptr, nullptr};
[[maybe_unused]] const bool unit_registered = (unit.next = x2::units, x2::units = &unit, true);

}  // namespace

// The arrays' pointers in the timed function's locals (the repair of x2_type.cpp's Local).
namespace {
struct PkLocal {
    double *x[4], *y[4], *z[4];
};
PkLocal pk_local() {
    PkLocal d;
    for (int k = 0; k < 4; ++k) d.x[k] = g->x[k], d.y[k] = g->y[k], d.z[k] = g->z[k];
    return d;
}
}  // namespace

#define L(A, K) load(&d.A[K][i])
extern "C" KB_NOINLINE void kb_x2k_tp_interval_add_2__packed(void*) {
    const PkLocal d = pk_local();
    for (int i = 0; i < kN; i += W) {
        V o0, o1, o2, o3;
        kg::interval_add_2(L(x, 0), L(x, 1), L(x, 2), L(x, 3), L(y, 0), L(y, 1), L(y, 2), L(y, 3), o0, o1, o2, o3);
        store(&d.z[0][i], o0);
        store(&d.z[1][i], o1);
        store(&d.z[2][i], o2);
        store(&d.z[3][i], o3);
    }
}
extern "C" KB_NOINLINE void kb_x2k_tp_interval_mul_2__packed(void*) {
    const PkLocal d = pk_local();
    for (int i = 0; i < kN; i += W) {
        V o0, o1, o2, o3;
        kg::interval_mul_2(L(x, 0), L(x, 1), L(x, 2), L(x, 3), L(y, 0), L(y, 1), L(y, 2), L(y, 3), o0, o1, o2, o3);
        store(&d.z[0][i], o0);
        store(&d.z[1][i], o1);
        store(&d.z[2][i], o2);
        store(&d.z[3][i], o3);
    }
}

namespace {
const Entry table[] = {
    {"x2k/tp/interval_add_2/packed", kb_x2k_tp_interval_add_2__packed, 64, W, kN, 0, 0, x2::check},
    {"x2k/tp/interval_mul_2/packed", kb_x2k_tp_interval_mul_2__packed, 64, W, kN, 0, 0, x2::check},
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
kairn_bench::m2::TableLink link{table, nullptr};
[[maybe_unused]] const bool registered =
    (link.next = kairn_bench::m2::m2_extra_tables, kairn_bench::m2::m2_extra_tables = &link, true);
}  // namespace

#endif
