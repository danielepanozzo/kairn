// The functions on arrays of the experimental two-limb interval rounded upward
// (experiments/upward2/include/kairn/experimental/upward2_arrays.hpp; bench/x2_data.hpp), backend
// x2a: add, sub, mul on four plain arrays (uh, ul, nh, nl) of kN elements, X2 and Y2, time per
// element. EXPERIMENTAL, NOT VERIFIED. Requires the options of docs/concepts/upward.md (GCC and Clang
// -frounding-math): compiled with the option of the target kairn::upward and the flags of packed
// code; each function holds its own scope, called here from code that rounds to nearest. The
// arrays are placed as up_data.hpp says. The reference of each: the same function on copies of its
// operands read through volatile objects.
#include <kairn/experimental/upward2_arrays.hpp>

#include <cstring>
#include <string>
#include <vector>

#include "up_data.hpp"
#include "x2_data.hpp"

namespace {

namespace x2 = kairn_bench::x2;
namespace up = kairn_bench::up;
namespace u2 = kairn::experimental::upward2;
using kairn_bench::m2::Entry;
using kairn_bench::m2::kN;

struct ArrData {
    up::Placed a{kN * sizeof(double)}, b{kN * sizeof(double)};
    double* x[4] = {a.at<double>(0), a.at<double>(1), a.at<double>(2), a.at<double>(3)};   // uh ul nh nl
    double* y[4] = {a.at<double>(4), a.at<double>(5), a.at<double>(6), a.at<double>(7)};
    double* z[4] = {a.at<double>(8), a.at<double>(9), a.at<double>(10), b.at<double>(9)};
};
ArrData* g = nullptr;

u2::View<const double> cv(double* const* p) { return {p[0], p[1], p[2], p[3], std::size_t(kN)}; }
u2::View<double> mv(double* const* p) { return {p[0], p[1], p[2], p[3], std::size_t(kN)}; }

void fill_one(const double* d, double* const* p, int i) {
    const kairn::Interval<double, 2> k = kairn::Interval<double, 2>::from_limbs(d);   // before the scope
    kairn::upward::Scope scope;
    const u2::Interval v = u2::from_interval(k);
    double q[4];
    v.to_limbs(q);   // uh, nh, ul, nl
    p[0][i] = q[0];
    p[1][i] = q[2];
    p[2][i] = q[1];
    p[3][i] = q[3];
}
void fill() {
    if (!g) g = new ArrData();
    const x2::Ops& o = x2::ops();
    for (int i = 0; i < kN; ++i) {
        fill_one(o.x + 4 * i, g->x, i);
        fill_one(o.y + 4 * i, g->y, i);
    }
}
void clear() {
    for (double* p : g->z) std::memset(p, 0xff, kN * sizeof(double));
}
// (l0, l1, h0, h1) of element i of four arrays: -(nh + nl) and uh + ul, exactly.
void put(double* const* p, int i, double* o) {
    o[0] = -p[2][i];
    o[1] = -p[3][i];
    o[2] = p[0][i];
    o[3] = p[1][i];
}
int read(const char*, double* out) {
    for (int i = 0; i < kN; ++i) put(g->z, i, out + 4 * i);
    return kN;
}
int reference(const char* name, double* out) {
    std::vector<double> buf(12 * kN);
    double* xs[4];
    double* ys[4];
    double* zs[4];
    for (int k = 0; k < 4; ++k) {
        xs[k] = buf.data() + k * kN;
        ys[k] = buf.data() + (4 + k) * kN;
        zs[k] = buf.data() + (8 + k) * kN;
        const volatile double* vx = g->x[k];
        const volatile double* vy = g->y[k];
        for (int i = 0; i < kN; ++i) {
            xs[k][i] = vx[i];
            ys[k][i] = vy[i];
        }
    }
    const std::string n = name;
    if (n.find("interval_add_2") != std::string::npos) u2::add(mv(zs), cv(xs), cv(ys));
    else if (n.find("interval_sub_2") != std::string::npos) u2::sub(mv(zs), cv(xs), cv(ys));
    else u2::mul(mv(zs), cv(xs), cv(ys));
    for (int i = 0; i < kN; ++i) put(zs, i, out + 4 * i);
    return kN;
}

x2::Unit unit{"x2a", fill, clear, read, reference, nullptr, nullptr};
[[maybe_unused]] const bool unit_registered = (unit.next = x2::units, x2::units = &unit, true);

}  // namespace

extern "C" KB_NOINLINE void kb_x2a_tp_interval_add_2__native(void*) { u2::add(mv(g->z), cv(g->x), cv(g->y)); }
extern "C" KB_NOINLINE void kb_x2a_tp_interval_sub_2__native(void*) { u2::sub(mv(g->z), cv(g->x), cv(g->y)); }
extern "C" KB_NOINLINE void kb_x2a_tp_interval_mul_2__native(void*) { u2::mul(mv(g->z), cv(g->x), cv(g->y)); }

namespace {
const Entry table[] = {
    {"x2a/tp/interval_add_2/native", kb_x2a_tp_interval_add_2__native, 64, 1, kN, 0, 0, x2::check},
    {"x2a/tp/interval_sub_2/native", kb_x2a_tp_interval_sub_2__native, 64, 1, kN, 0, 0, x2::check},
    {"x2a/tp/interval_mul_2/native", kb_x2a_tp_interval_mul_2__native, 64, 1, kN, 0, 0, x2::check},
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
kairn_bench::m2::TableLink link{table, nullptr};
[[maybe_unused]] const bool registered =
    (link.next = kairn_bench::m2::m2_extra_tables, kairn_bench::m2::m2_extra_tables = &link, true);
}  // namespace
