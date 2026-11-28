// The checks of the benchmark of 1, 2 and 4 limbs (bench/x4_data.hpp), made before anything is timed:
// ordinary code, compiled as m2.cpp and run under rounding to nearest. EXPERIMENTAL, NOT VERIFIED.
//
// Each function runs on cleared outputs, from rounding to nearest, and is refused if it leaves the C
// library's mode or the control register (rounding control, flush to zero) other than it found it; its
// results, read as 8 numbers per element (the lower and the upper bound, each the exact sum of four),
// must equal bit for bit those of its unit's reference (the same kernels on operands read through
// volatile objects), and, for an enclosure, contain in exact arithmetic
// (experiments/upward2/tests/exact.hpp) on the two-limb operands of x2::ops() (which every type's
// operands contain):
// - a loop of +, -, * (each kind of operands): the exact range of each element's operation; the square:
//   the exact range of t^2;
// - a chain of sums: the exact range of the sum; a chain of products: step by step through the unit's
//   step (each step containing the exact range of its operands' product; a ball's state cannot be
//   rebuilt from its bounds, and its chain is checked against its reference only), the end equal to the
//   timed chain's bit for bit;
// - the determinant on points: its exact value; Horner on points: the exact value of the polynomial;
//   Horner on intervals: the exact values at both bounds of each argument (a necessary condition).
// For the determinant and Horner on points it prints the width of each result over the absolute exact
// value (median, largest) on the standard error ("x4 width: ..."), with the other counts ("x4 check: ...").
#include <algorithm>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#if defined(__x86_64__) || defined(_M_X64)
#include <xmmintrin.h>
#endif

#include "../experiments/upward2/tests/exact.hpp"
#include "x4_unit.hpp"

namespace kairn_bench::x4 {

Unit* units = nullptr;

namespace {

using x2test::Exact;

#if defined(__x86_64__) || defined(_M_X64)
using Control = unsigned int;
Control read_control() { return _mm_getcsr() & 0xE040u; }
#elif defined(__aarch64__) && defined(__GNUC__)
using Control = std::uint64_t;
Control read_control() {
    std::uint64_t v;
    __asm__ __volatile__("mrs %0, fpcr" : "=r"(v));
    return v & ((std::uint64_t(3) << 22) | (std::uint64_t(1) << 24) | std::uint64_t(3));
}
#else
using Control = int;
Control read_control() { return 0; }
#endif

// Exact two-sum under rounding to nearest (Knuth): a + b = s + e.
void two_sum(double a, double b, double& s, double& e) {
    s = a + b;
    const double bb = s - a;
    e = (a - (s - bb)) + (b - bb);
}
// sign(v - E) for a bound v of four numbers and an exact value E.
int cmp(const double* v, const Exact& ex, Exact& t) {
    t = ex;
    for (int i = 0; i < 4; ++i) t.sub(v[i]);
    return -t.sign();
}
// z (lower l0..l3, upper h0..h3) contains the exact value E.
bool contains(const double* z, const Exact& ex, Exact& t) { return cmp(z, ex, t) <= 0 && cmp(z + 4, ex, t) >= 0; }
// The four products of bounds of x and y (each (l0, l1, h0, h1)) contained in z.
bool contains_product(const double* x, const double* y, const double* z, Exact& p, Exact& t) {
    for (int a = 0; a < 4; a += 2)
        for (int b = 0; b < 4; b += 2) {
            p.clear();
            p.add_product(x[a], y[b]);
            p.add_product(x[a], y[b + 1]);
            p.add_product(x[a + 1], y[b]);
            p.add_product(x[a + 1], y[b + 1]);
            if (!contains(z, p, t)) return false;
        }
    return true;
}
// The same for a state s of 8 numbers (four per bound) and an interval y of two limbs.
bool contains_product8(const double* s, const double* y, const double* z, Exact& p, Exact& t) {
    for (int a = 0; a < 8; a += 4)
        for (int b = 0; b < 4; b += 2) {
            p.clear();
            for (int i = 0; i < 4; ++i) {
                p.add_product(s[a + i], y[b]);
                p.add_product(s[a + i], y[b + 1]);
            }
            if (!contains(z, p, t)) return false;
        }
    return true;
}
void horner_exact(const double* c, double x0, double x1, Exact& e) {
    e.clear();
    e.add(c[kDeg]);
    for (int k = kDeg - 1; k >= 0; --k) {
        Exact a = e, b = e;
        a.mul(x0);
        b.mul(x1);
        a.add(b);
        a.add(c[k]);
        e = a;
    }
}
void det_exact(const x2::Ops& o, int i, Exact& e) {
    const int a = i, b = (i + 1) % kN, c = (i + 2) % kN, d = (i + 3) % kN;
    double D[9][2];
    const int pt[3] = {a, b, c};
    for (int k = 0; k < 3; ++k) {
        two_sum(o.px[pt[k]], -o.px[d], D[3 * k][0], D[3 * k][1]);
        two_sum(o.py[pt[k]], -o.py[d], D[3 * k + 1][0], D[3 * k + 1][1]);
        two_sum(o.pz[pt[k]], -o.pz[d], D[3 * k + 2][0], D[3 * k + 2][1]);
    }
    e.clear();
    const int terms[6][4] = {{0, 4, 8, 0}, {0, 5, 7, 1}, {3, 7, 2, 0}, {3, 8, 1, 1}, {6, 1, 5, 0}, {6, 2, 4, 1}};
    for (const auto& tm : terms)
        for (int p = 0; p < 2; ++p)
            for (int q = 0; q < 2; ++q)
                for (int r = 0; r < 2; ++r) e.add_product3(D[tm[0]][p], D[tm[1]][q], D[tm[2]][r], tm[3] != 0);
}
struct Widths {
    std::vector<double> w;
    void add(const double* z, const Exact& ex, Exact& t) {
        t.clear();
        for (int i = 0; i < 4; ++i) {
            t.add(z[4 + i]);
            t.sub(z[i]);
        }
        Exact v = ex;
        const double ev = std::fabs(v.value());
        if (ev > 0) w.push_back(t.value() / ev);
    }
    void print(const char* name) {
        if (w.empty()) return;
        std::sort(w.begin(), w.end());
        std::fprintf(stderr, "x4 width: %s: %zu results, width over |exact value|: median %.3g, largest %.3g (u = 2^-53: median %.3g u, largest %.3g u)\n",
                     name, w.size(), w[w.size() / 2], w.back(), w[w.size() / 2] / 0x1p-53, w.back() / 0x1p-53);
    }
};

}  // namespace

bool check(const Entry& e, char* why, std::size_t size) {
    const std::string name = e.name;
    const std::string backend = name.substr(0, name.find('/'));
    Unit* u = units;
    while (u && backend != u->backend) u = u->next;
    if (!u) {
        std::snprintf(why, size, "no unit for this backend");
        return false;
    }
    // The unit of this backend and variant (the units of x4d hold one variant each).
    const x2::Ops& o = x2::ops();
    const Name nm = parse(e.name);
    std::vector<double> got(8 * kRand), ref(8 * kRand);
    Unit* found = nullptr;
    for (Unit* v = units; v && !found; v = v->next)
        if (backend == v->backend && (!v->variant || nm.variant == v->variant)) found = v;
    if (!found) {
        std::snprintf(why, size, "no unit for this backend and variant");
        return false;
    }
    found->fill();
    const Control before = read_control();
    if (std::fegetround() != FE_TONEAREST) {
        std::snprintf(why, size, "the rounding mode was not to nearest before the call");
        return false;
    }
    found->clear();
    e.fn(nullptr);
    if (std::fegetround() != FE_TONEAREST || read_control() != before) {
        std::fesetround(FE_TONEAREST);
        std::snprintf(why, size, "the function left the rounding mode or the control register changed");
        return false;
    }
    const int n = found->read(e.name, got.data());
    u = found;
    const int m = u->reference(e.name, ref.data());
    if (m != n || std::memcmp(got.data(), ref.data(), 8 * std::size_t(n) * sizeof(double)) != 0) {
        for (int i = 0; i < n; ++i)
            if (std::memcmp(&got[8 * i], &ref[8 * i], 8 * sizeof(double)) != 0) {
                std::snprintf(why, size, "element %d differs from the reference through volatile operands: lower %a %a, %a %a", i, got[8 * i],
                              got[8 * i + 1], ref[8 * i], ref[8 * i + 1]);
                return false;
            }
        std::snprintf(why, size, "the reference gives %d results, the function %d", m, n);
        return false;
    }
    if (!u->encloses) {
        std::fprintf(stderr, "x4 check: %s: %d results equal bit for bit to the reference through volatile operands (not an enclosure)\n", e.name, n);
        return true;
    }
    Exact ex, t, p;
    Widths widths;
    auto fail = [&](int i, const char* what) {
        std::snprintf(why, size, "element %d does not contain %s: lower %a %a, upper %a %a", i, what, got[8 * i], got[8 * i + 1], got[8 * i + 4],
                      got[8 * i + 5]);
        return false;
    };
    const int k = nm.kernel;
    bool stepped = false;
    if (k == K_SUM) {
        Exact lo, hi;
        for (int i = 0; i < kN; ++i) {
            lo.add(o.x[4 * i]);
            lo.add(o.x[4 * i + 1]);
            hi.add(o.x[4 * i + 2]);
            hi.add(o.x[4 * i + 3]);
        }
        if (cmp(got.data(), lo, t) > 0 || cmp(got.data() + 4, hi, t) < 0) return fail(0, "the exact sum");
    } else if (k == K_PROD || k == K_PRODRAND) {
        double s[8] = {1, 0, 0, 0, 1, 0, 0, 0}, nx[8];
        const bool rnd = k == K_PRODRAND;
        const double* fs = rnd ? o.fr : o.f;
        bool can = true;
        for (int i = 0; i < (rnd ? kRand : kN) && can; ++i) {
            if (!u->step || !u->step(e.name, s, i, nx)) {
                can = false;
                break;
            }
            if (!contains_product8(s, fs + 4 * i, nx, p, t)) {
                std::snprintf(why, size, "step %d does not contain the exact product of its operands", i);
                return false;
            }
            std::memcpy(s, nx, sizeof s);
        }
        if (can) {
            stepped = true;
            if (std::memcmp(s, got.data(), sizeof s) != 0) {
                std::snprintf(why, size, "the chain differs from its steps");
                return false;
            }
        }
    } else {
        for (int i = 0; i < n; ++i) {
            const double* z = &got[8 * i];
            const double *x = o.x + 4 * i, *y = o.y + 4 * i;
            if (k == K_MULPOS) x = o.xp + 4 * i, y = o.yp + 4 * i;
            if (k == K_MULZERO) x = o.xz + 4 * i, y = o.yz + 4 * i;
            if (k == K_MULRAND) x = o.xr + 4 * i, y = o.yr + 4 * i;
            if (k == K_ADD || k == K_SUB) {
                const bool sub = k == K_SUB;
                ex.clear();
                ex.add(x[0]);
                ex.add(x[1]);
                if (sub) {
                    ex.sub(y[2]);
                    ex.sub(y[3]);
                } else {
                    ex.add(y[0]);
                    ex.add(y[1]);
                }
                if (cmp(z, ex, t) > 0) return fail(i, "the exact lower bound");
                ex.clear();
                ex.add(x[2]);
                ex.add(x[3]);
                if (sub) {
                    ex.sub(y[0]);
                    ex.sub(y[1]);
                } else {
                    ex.add(y[2]);
                    ex.add(y[3]);
                }
                if (cmp(z + 4, ex, t) < 0) return fail(i, "the exact upper bound");
            } else if (k == K_SQR) {
                for (int a = 0; a < 4; a += 2) {
                    p.clear();
                    p.add_product(x[a], x[a]);
                    p.add_product(x[a], x[a + 1]);
                    p.add_product(x[a + 1], x[a]);
                    p.add_product(x[a + 1], x[a + 1]);
                    if (cmp(z + 4, p, t) < 0) return fail(i, "the square of a bound");
                }
                p.clear();
                const bool zero_in = x[0] <= 0 && x[2] >= 0;
                if (zero_in && cmp(z, p, t) > 0) return fail(i, "zero");
                if (!zero_in) {
                    const int a = x[0] > 0 ? 0 : 2;
                    p.add_product(x[a], x[a]);
                    p.add_product(x[a], x[a + 1]);
                    p.add_product(x[a + 1], x[a]);
                    p.add_product(x[a + 1], x[a + 1]);
                    if (cmp(z, p, t) > 0) return fail(i, "the least square");
                }
            } else if (k == K_HORNER_I) {
                for (int a = 0; a < 4; a += 2) {
                    horner_exact(o.hc, o.h[4 * i + a], o.h[4 * i + a + 1], ex);
                    if (!contains(z, ex, t)) return fail(i, "the polynomial at a bound of its argument");
                }
            } else if (k == K_HORNER_PT) {
                horner_exact(o.hc, o.ht[i], 0.0, ex);
                if (!contains(z, ex, t)) return fail(i, "the polynomial's exact value");
                widths.add(z, ex, t);
            } else if (k == K_DET) {
                det_exact(o, i, ex);
                if (!contains(z, ex, t)) return fail(i, "the exact determinant");
                widths.add(z, ex, t);
            } else {
                if (!contains_product(x, y, z, p, t)) return fail(i, "a product of bounds");
            }
        }
    }
    std::fprintf(stderr, "x4 check: %s: %d results contain the exact values%s; equal bit for bit to the reference through volatile operands\n", e.name, n,
                 (k == K_PROD || k == K_PRODRAND) ? (stepped ? " (step by step)" : " (a ball: not stepped)") : "");
    widths.print(e.name);
    return true;
}

}  // namespace kairn_bench::x4
