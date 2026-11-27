// The checks of the benchmark of the experimental two-limb interval rounded upward
// (bench/x2_data.hpp), made before anything is timed: ordinary code, compiled as m2.cpp and run
// under rounding to nearest. EXPERIMENTAL, NOT VERIFIED.
//
// Each function runs on cleared outputs, from rounding to nearest, and is refused if it leaves the
// C library's mode or the control register (rounding control, flush to zero) other than it found
// it; its results, read as (l0, l1, h0, h1), must equal bit for bit those of its unit's reference
// (the same computation by the same kernels on operands read through volatile objects) where the
// unit has one, and must contain, in exact arithmetic (experiments/upward2/tests/exact.hpp):
// - a loop of +, -, *: the exact range of each element's operation on the operands (as the default
//   form holds them); the square: the exact range of t^2;
// - a chain of sums: the exact range of the sum; a chain of products: step by step through the
//   unit's step (each step containing the exact range of its operands' product), the end equal to
//   the timed chain's bit for bit;
// - the determinant on points: its exact value; Horner on points: the exact value of the polynomial;
//   Horner on intervals: the exact values at both bounds of each argument (a necessary condition).
// For the determinant and Horner on points it prints the width of each result over the absolute
// exact value (median, largest), on the standard error ("x2 width: ..."), with the other counts
// ("x2 check: ...").
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
#include "x2_data.hpp"

namespace kairn_bench::x2 {

Unit* units = nullptr;

namespace {

using x2test::Exact;

Ops* g_ops = nullptr;

// A pair of a canonical bound negated: canonical again.
void neg_interval(const double* a, double* o) {
    const double t[4] = {-a[2], -a[3], -a[0], -a[1]};
    std::memcpy(o, t, sizeof t);
}

void make_ops() {
    const Raw<double>& r = *static_cast<const Raw<double>*>(m2::m2_data(64));
    Ops& o = *g_ops;
    std::memcpy(o.x, r.xi2, sizeof o.x);
    std::memcpy(o.y, r.yi2, sizeof o.y);
    std::memcpy(o.f, r.fi2, sizeof o.f);
    std::memcpy(o.h, r.hi2, sizeof o.h);
    for (int i = 0; i < kN; ++i) {
        const double* x = o.x + 4 * i;
        const double* y = o.y + 4 * i;
        // One sign: a negative interval negated.
        if (x[2] < 0) neg_interval(x, o.xp + 4 * i);
        else std::memcpy(o.xp + 4 * i, x, 4 * sizeof(double));
        if (y[2] < 0) neg_interval(y, o.yp + 4 * i);
        else std::memcpy(o.yp + 4 * i, y, 4 * sizeof(double));
        // Around zero: [-|lower of X[i]|, |upper of Y[i]|], [-|lower of Y[i]|, |upper of X[i + 1]|].
        const double* x1 = o.x + 4 * ((i + 1) % kN);
        auto around = [](const double* a, const double* b, double* z) {
            z[0] = -std::fabs(a[0]);
            z[1] = a[0] < 0 ? a[1] : -a[1];
            z[2] = std::fabs(b[2]);
            z[3] = b[2] < 0 ? -b[3] : b[3];
        };
        around(x, y, o.xz + 4 * i);
        around(y, x1, o.yz + 4 * i);
        o.px[i] = r.xi[2 * i];
        o.py[i] = r.yi[2 * i];
        o.pz[i] = r.fi[2 * i];
        o.ht[i] = r.ht[i];
    }
    for (int k = 0; k <= kDeg; ++k) o.hc[k] = r.hc[k];
    for (int j = 0; j < kRand; ++j) {
        std::uint64_t z = std::uint64_t(j) * 0x9e3779b97f4a7c15u;
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9u;
        z ^= z >> 31;
        const double* x = o.x + 4 * (j % kN);
        const double* y = o.y + 4 * ((7 * j + 3) % kN);
        if (z & 1) neg_interval(x, o.xr + 4 * j);
        else std::memcpy(o.xr + 4 * j, x, 4 * sizeof(double));
        if (z & 2) neg_interval(y, o.yr + 4 * j);
        else std::memcpy(o.yr + 4 * j, y, 4 * sizeof(double));
    }
}

// The rounding mode and flush to zero, as the default checks read them (up_check.cpp).
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

// sign(v - E) for a bound v = (v0, v1) and an exact value E.
int cmp(const double* v, const Exact& ex, Exact& t) {
    t = ex;
    t.sub(v[0]);
    t.sub(v[1]);
    return -t.sign();
}
// z (l0, l1, h0, h1) contains the exact value E.
bool contains(const double* z, const Exact& ex, Exact& t) { return cmp(z, ex, t) <= 0 && cmp(z + 2, ex, t) >= 0; }

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

// The exact value of the Horner polynomial at the two-limb point (x0, x1).
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

// The exact determinant of the points i, i + 1, i + 2, i + 3.
void det_exact(const Ops& o, int i, Exact& e) {
    const int a = i, b = (i + 1) % kN, c = (i + 2) % kN, d = (i + 3) % kN;
    double D[9][2];   // adx ady adz bdx bdy bdz cdx cdy cdz, each exactly s + e
    const int pt[3] = {a, b, c};
    for (int k = 0; k < 3; ++k) {
        two_sum(o.px[pt[k]], -o.px[d], D[3 * k][0], D[3 * k][1]);
        two_sum(o.py[pt[k]], -o.py[d], D[3 * k + 1][0], D[3 * k + 1][1]);
        two_sum(o.pz[pt[k]], -o.pz[d], D[3 * k + 2][0], D[3 * k + 2][1]);
    }
    e.clear();
    // adx (bdy cdz - bdz cdy) + bdx (cdy adz - cdz ady) + cdx (ady bdz - adz bdy)
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
        t.add(z[2]);
        t.add(z[3]);
        t.sub(z[0]);
        t.sub(z[1]);
        Exact v = ex;
        const double ev = std::fabs(v.value());
        if (ev > 0) w.push_back(t.value() / ev);
    }
    void print(const char* name) {
        if (w.empty()) return;
        std::sort(w.begin(), w.end());
        std::fprintf(stderr, "x2 width: %s: %zu results, width over |exact value|: median %.3g, largest %.3g (u = 2^-53: median %.3g u, largest %.3g u)\n",
                     name, w.size(), w[w.size() / 2], w.back(), w[w.size() / 2] / 0x1p-53, w.back() / 0x1p-53);
    }
};

}  // namespace

const Ops& ops() {
    if (!g_ops) {
        g_ops = new Ops();
        make_ops();
    }
    return *g_ops;
}

bool check(const Entry& e, char* why, std::size_t size) {
    const std::string name = e.name;
    const std::string backend = name.substr(0, name.find('/'));
    Unit* u = units;
    while (u && backend != u->backend) u = u->next;
    if (!u) {
        std::snprintf(why, size, "no unit for this backend");
        return false;
    }
    const Ops& o = ops();
    u->fill();
    const Control before = read_control();
    if (std::fegetround() != FE_TONEAREST) {
        std::snprintf(why, size, "the rounding mode was not to nearest before the call");
        return false;
    }
    u->clear();
    e.fn(nullptr);
    if (std::fegetround() != FE_TONEAREST || read_control() != before) {
        std::fesetround(FE_TONEAREST);
        std::snprintf(why, size, "the function left the rounding mode or the control register changed");
        return false;
    }
    std::vector<double> got(4 * kRand), ref(4 * kRand);
    const int n = u->read(e.name, got.data());
    bool bitwise = false;
    if (u->reference) {
        const int m = u->reference(e.name, ref.data());
        if (m != n || std::memcmp(got.data(), ref.data(), 4 * std::size_t(n) * sizeof(double)) != 0) {
            for (int i = 0; i < n; ++i)
                if (std::memcmp(&got[4 * i], &ref[4 * i], 4 * sizeof(double)) != 0) {
                    std::snprintf(why, size, "element %d differs from the reference through volatile operands: %a %a %a %a, %a %a %a %a", i,
                                  got[4 * i], got[4 * i + 1], got[4 * i + 2], got[4 * i + 3], ref[4 * i], ref[4 * i + 1], ref[4 * i + 2],
                                  ref[4 * i + 3]);
                    return false;
                }
            std::snprintf(why, size, "the reference gives %d results, the function %d", m, n);
            return false;
        }
        bitwise = true;
    }
    // KIND and KERNEL.
    const std::size_t s1 = name.find('/'), s2 = name.find('/', s1 + 1), s3 = name.find('/', s2 + 1);
    const std::string kind = name.substr(s1 + 1, s2 - s1 - 1), kernel = name.substr(s2 + 1, s3 - s2 - 1);
    Exact ex, t, p;
    Widths widths;
    auto fail = [&](int i, const char* what) {
        std::snprintf(why, size, "element %d does not contain %s: %a %a %a %a", i, what, got[4 * i], got[4 * i + 1], got[4 * i + 2],
                      got[4 * i + 3]);
        return false;
    };
    if (kind == "tp") {
        const int expected = kernel == "interval_mul_2rand" ? kRand : kN;
        if (n != expected) {
            std::snprintf(why, size, "%d results", n);
            return false;
        }
        for (int i = 0; i < n; ++i) {
            const double* z = &got[4 * i];
            const double *x = o.x + 4 * i, *y = o.y + 4 * i;
            if (kernel == "interval_mul_2pos") x = o.xp + 4 * i, y = o.yp + 4 * i;
            if (kernel == "interval_mul_2zero") x = o.xz + 4 * i, y = o.yz + 4 * i;
            if (kernel == "interval_mul_2rand") x = o.xr + 4 * i, y = o.yr + 4 * i;
            if (kernel == "interval_add_2" || kernel == "interval_sub_2") {
                const bool sub = kernel == "interval_sub_2";
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
                if (cmp(z + 2, ex, t) < 0) return fail(i, "the exact upper bound");
            } else if (kernel == "sqr_2") {
                // [t^2 over X]: the upper bound at least the square of each bound; the lower bound at
                // most 0 when X contains zero, else at most the square of the bound nearer zero.
                for (int a = 0; a < 4; a += 2) {
                    p.clear();
                    p.add_product(x[a], x[a]);
                    p.add_product(x[a], x[a + 1], false);
                    p.add_product(x[a + 1], x[a], false);
                    p.add_product(x[a + 1], x[a + 1]);
                    if (cmp(z + 2, p, t) < 0) return fail(i, "the square of a bound");
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
            } else if (kernel == "horner_i2") {
                for (int a = 0; a < 4; a += 2) {
                    horner_exact(o.hc, o.h[4 * i + a], o.h[4 * i + a + 1], ex);
                    if (!contains(z, ex, t)) return fail(i, "the polynomial at a bound of its argument");
                }
            } else if (kernel == "horner_pt") {
                horner_exact(o.hc, o.ht[i], 0.0, ex);
                if (!contains(z, ex, t)) return fail(i, "the polynomial's exact value");
                widths.add(z, ex, t);
            } else if (kernel == "det3pt") {
                det_exact(o, i, ex);
                if (!contains(z, ex, t)) return fail(i, "the exact determinant");
                widths.add(z, ex, t);
            } else {
                if (!contains_product(x, y, z, p, t)) return fail(i, "a product of bounds");
            }
        }
    } else if (kind == "sum") {
        Exact lo, hi;
        for (int i = 0; i < kN; ++i) {
            lo.add(o.x[4 * i]);
            lo.add(o.x[4 * i + 1]);
            hi.add(o.x[4 * i + 2]);
            hi.add(o.x[4 * i + 3]);
        }
        if (cmp(got.data(), lo, t) > 0 || cmp(got.data() + 2, hi, t) < 0) return fail(0, "the exact sum");
    } else if (kind == "prod") {
        if (!u->step) {
            std::snprintf(why, size, "a chain without a step function");
            return false;
        }
        double s[4] = {1, 0, 1, 0}, nx[4];
        for (int i = 0; i < kN; ++i) {
            u->step(e.name, s, i, nx);
            if (!contains_product(s, o.f + 4 * i, nx, p, t)) {
                std::snprintf(why, size, "step %d does not contain the exact product of its operands", i);
                return false;
            }
            std::memcpy(s, nx, sizeof s);
        }
        if (std::memcmp(s, got.data(), sizeof s) != 0) {
            std::snprintf(why, size, "the chain differs from its steps: %a %a %a %a against %a %a %a %a", got[0], got[1], got[2], got[3], s[0],
                          s[1], s[2], s[3]);
            return false;
        }
    } else if (kind == "lat") {
        for (int a = 0; a < 4; a += 2) {
            horner_exact(o.hc, o.h[4 * (kN - 1) + a], o.h[4 * (kN - 1) + a + 1], ex);
            if (!contains(got.data(), ex, t)) return fail(0, "the polynomial at a bound of the last argument");
        }
    } else {
        std::snprintf(why, size, "no check for this kind");
        return false;
    }
    std::fprintf(stderr, "x2 check: %s: %d results contain the exact values; %s\n", e.name, n,
                 bitwise ? "equal bit for bit to the reference through volatile operands" : "no reference of its own");
    widths.print(e.name);
    return true;
}

}  // namespace kairn_bench::x2
