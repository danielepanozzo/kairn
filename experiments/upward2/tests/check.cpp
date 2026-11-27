// The exact checks of the experimental two-limb interval rounded upward (experiments/upward2/
// README.md). EXPERIMENTAL, NOT VERIFIED, not part of the library. Requires the rounding mode upward
// set by kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang
// -frounding-math): every operation of the type below runs inside a Scope; the checks themselves
// run under rounding to nearest.
//
// For each class of operands (n pairs each, from a fixed seed, the same with every compiler) and
// each operation (+, -, the five forms of *, the square, x + t, x * t, -x, the conversions): the
// result must contain the exact range (exact arithmetic, exact.hpp), be canonical and
// upper-normalized (each pair (h, l) with l <= 0 and |l| below the gap under h; the product's
// maximum relies on it); the same operands through the default kairn::Interval<double, 2> are
// checked the same way (a check of the checker) and the excess of each bound over the exact one,
// relative, in units of u^2 = 2^-106, is printed for both. Then every pair of a list of special
// values: the result must contain the exact range in the extended reals (0 times infinity is 0),
// and is compared with Interval<double, 2>'s. Exit status 0 when nothing failed.
//
// Usage: x2-check [N per class (default 2000000)] [seed] [threads]
#include <kairn/experimental/upward2.hpp>
#include <kairn/kairn.hpp>

#include <algorithm>
#include <atomic>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <limits>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "exact.hpp"

namespace {

namespace u2 = kairn::experimental::upward2;
namespace d2 = kairn::experimental::upward2::detail;
using x2test::Exact;
using I2 = kairn::Interval<double, 2>;

constexpr double kInf = std::numeric_limits<double>::infinity();
constexpr double kMax = std::numeric_limits<double>::max();
constexpr double kU2 = 0x1p-106;

struct Rng {
    std::uint64_t s;
    std::uint64_t next() {
        std::uint64_t z = (s += 0x9e3779b97f4a7c15u);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9u;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebu;
        return z ^ (z >> 31);
    }
    double unit() { return double(next() >> 11) * 0x1p-53; }
    int range(int a, int b) { return a + int(next() % std::uint64_t(b - a + 1)); }
};

// --- Operands: the default form, (l0, l1, h0, h1), each bound normalized to nearest ------------------

struct P2 {
    double h, l;
};
P2 renorm(double a, double b) {   // |a| >= |b|, rounding to nearest
    const double s = a + b;
    return {s, b - (s - a)};
}
bool lt(P2 a, P2 b) { return a.h < b.h || (a.h == b.h && a.l < b.l); }
P2 number(Rng& g, int kmin, int kmax) {
    const double sign = (g.next() & 1) ? 1.0 : -1.0;
    const double m = 1.0 + g.unit();
    const int k = g.range(kmin, kmax);
    const double h = sign * std::ldexp(m, k);
    const int kind = g.range(0, 7);
    double l = h * (g.unit() - 0.5) * 0x1p-53;
    if (kind == 0) l = 0;
    if (kind == 1) l = std::ldexp(l, -g.range(1, 40));
    P2 p = renorm(h, l);
    if (!(std::fabs(p.h) <= kMax)) p = {std::copysign(kMax, h), 0.0};
    return {p.h, p.l + 0.0};
}
struct DI {
    double l0, l1, h0, h1;
};
DI put(P2 lo, P2 hi) {
    if (lt(hi, lo)) std::swap(lo, hi);
    return {lo.h + 0.0, lo.l + 0.0, hi.h + 0.0, hi.l + 0.0};
}
// Kinds: 0 narrow (half-width 2^-rel of the center), 1 two unrelated bounds, 2 around zero, 3 a
// point, 4 one bound zero, 5 [0, 0].
DI interval(Rng& g, int kind, int kmin, int kmax, int rel) {
    const P2 c = number(g, kmin, kmax);
    if (kind == 0) {
        const double w = std::fabs(c.h) * std::ldexp(0.5 + 0.5 * g.unit(), -rel);
        return put(renorm(c.h, c.l - w), renorm(c.h, c.l + w));
    }
    if (kind == 1) return put(c, number(g, kmin, kmax));
    if (kind == 2) {
        const P2 d = number(g, kmin, kmax);
        return put({-std::fabs(c.h), c.h < 0 ? c.l : -c.l}, {std::fabs(d.h), d.h < 0 ? -d.l : d.l});
    }
    if (kind == 3) return put(c, c);
    if (kind == 4) return put(c, {0.0, 0.0});
    return {0.0, 0.0, 0.0, 0.0};
}

// --- Bounds in the extended reals --------------------------------------------------------------------

// A bound: -inf, +inf, or the finite value h + l.
struct XV {
    int inf;   // -1, 0, +1
    double h, l;
};
XV xv(double h, double l) {
    if (h == kInf) return {1, 0, 0};
    if (h == -kInf) return {-1, 0, 0};
    return {0, h, l};
}
// The bounds of a result of the type, exactly: lower -(nh + nl), upper uh + ul.
struct Res {
    bool empty;
    XV lo, hi;
    double uh, nh, ul, nl;
};
Res res_of(const u2::Interval& z) {
    double p[4];
    z.to_limbs(p);
    Res r{};
    r.uh = p[0];
    r.nh = p[1];
    r.ul = p[2];
    r.nl = p[3];
    r.empty = p[0] != p[0] || p[1] != p[1];
    r.hi = xv(p[0], p[2]);
    r.lo = p[1] == kInf ? XV{-1, 0, 0} : XV{0, -p[1], -p[3]};
    return r;
}
Res res_of(const I2& z) {
    Res r{};
    const double l0 = z.lower().limb[0], l1 = z.lower().limb[1], h0 = z.upper().limb[0], h1 = z.upper().limb[1];
    r.empty = l0 == kInf && h0 == -kInf;
    r.lo = xv(l0, l1);
    r.hi = xv(h0, h1);
    return r;
}
Res res_of(const DI& x) { return res_of(I2::from_limbs(&x.l0)); }

// The sign of a - b, a and b bounds or exact values (exact values given as Exact, finite).
int cmp_xv(const XV& a, const XV& b, Exact& t) {
    if (a.inf || b.inf) return a.inf == b.inf ? 0 : (a.inf - b.inf > 0 ? 1 : -1);
    t.clear();
    t.add(a.h);
    t.add(a.l);
    t.sub(b.h);
    t.sub(b.l);
    return t.sign();
}

// A corner of a product: 0 (a zero factor), +-inf, or the exact product of two finite bounds.
struct Corner {
    int inf;    // -1, 0, +1 (0: finite or zero)
    bool zero;  // exactly zero
    double a0, a1, b0, b1;
};
int sgn(const XV& v) {
    if (v.inf) return v.inf;
    return v.h > 0 ? 1 : v.h < 0 ? -1 : (v.l > 0 ? 1 : v.l < 0 ? -1 : 0);
}
Corner corner(const XV& a, const XV& b) {
    const int sa = sgn(a), sb = sgn(b);
    if (sa == 0 || sb == 0) return {0, true, 0, 0, 0, 0};
    if (a.inf || b.inf) return {sa * sb, false, 0, 0, 0, 0};
    return {0, false, a.h, a.l, b.h, b.l};
}
// The sign of v - c for a bound v and a corner c; the value of v - c and of c (approximate).
int cmp_corner(const XV& v, const Corner& c, Exact& t, double* diff = nullptr, double* cval = nullptr) {
    if (v.inf || c.inf) {
        if (diff) *diff = 0;
        if (cval) *cval = 0;
        return v.inf == c.inf ? 0 : (v.inf - c.inf > 0 ? 1 : -1);
    }
    t.clear();
    if (!c.zero) {
        t.add_product(c.a0, c.b0);
        t.add_product(c.a0, c.b1);
        t.add_product(c.a1, c.b0);
        t.add_product(c.a1, c.b1);
    }
    if (cval) *cval = t.value();
    t.sub(v.h);
    t.sub(v.l);
    const int s = -t.sign();
    if (diff) *diff = -t.value();
    return s;
}

// --- The check of one result ---------------------------------------------------------------------------

enum Op { ADD, SUB, MUL_SEL2, MUL_EIGHT, MUL_TABLE, MUL_BRANCH, MUL_SEL4, SQR, ADD_NUM, MUL_NUM, NEG, CONV, ADD_LEAN, ADD_SLOPPY, N_OPS };
const char* const kOpName[N_OPS] = {"add", "sub", "mul.sel2", "mul.eight", "mul.table", "mul.branch", "mul.sel4",
                                    "sqr", "add_num", "mul_num", "neg", "conv", "add.lean", "add.sloppy"};

struct Verdict {
    bool ok = true;
    bool normalized = true;
    std::string why;
    // The excess of each bound over the exact one, and the exact bound (approximate), when both
    // are finite; flags when not measured.
    double ex[2] = {0, 0}, ref[2] = {0, 0};
    bool measured[2] = {false, false};
};

// Upper-normalized: l <= 0 and h + l > pred(h); a head +inf, +-MAX: l == 0; no head -inf, no NaN.
bool normalized_pair(double h, double l) {
    if (h != h || l != l || h == -kInf) return false;
    if (h == kInf || std::fabs(h) == kMax) return l == 0;
    if (l > 0) return false;
    if (h == 0) return l == 0;
    const double gap = h - std::nextafter(h, -kInf);   // exact
    return -l < gap;
}

// x op y (y unused for the unary ones; t the number of add_num and mul_num), the operands as the
// default form's bounds (exactly the values the type holds), z the result.
Verdict judge(Op op, const Res& x, const Res& y, double t, const Res& z, bool type_result, Exact& e) {
    Verdict v;
    const bool unary = op == SQR || op == NEG || op == CONV || op == ADD_NUM || op == MUL_NUM;
    const bool empty_in = x.empty || (!unary && y.empty);
    if (empty_in) {
        if (!z.empty) {
            v.ok = false;
            v.why = "an empty operand, a result that is not empty";
        }
        return v;
    }
    if (z.empty) {
        v.ok = false;
        v.why = "nonempty operands, an empty result";
        return v;
    }
    if (type_result) {
        v.normalized = normalized_pair(z.uh, z.ul) && normalized_pair(z.nh, z.nl);
        if (!v.normalized) v.why = "a pair of the result is not upper-normalized; ";
    }
    const XV ty = std::fabs(t) < kInf ? XV{0, t, 0.0} : XV{t > 0 ? 1 : -1, 0, 0};
    const bool t_whole = !(std::fabs(t) < kInf);   // Interval(t) is the whole line
    // Sums: compare z.lo with xl + yl, z.hi with xh + yh, in the extended reals.
    auto check_sum = [&](const XV& al, const XV& bl, const XV& ah, const XV& bh) {
        // lower
        for (int side = 0; side < 2; ++side) {
            const XV& a = side ? ah : al;
            const XV& b = side ? bh : bl;
            const XV& zb = side ? z.hi : z.lo;
            const int inf = a.inf ? a.inf : b.inf;   // never -inf + +inf for canonical operands
            if (inf) {
                if (zb.inf != inf) {
                    v.ok = false;
                    v.why += side ? "upper bound below an infinite upper bound; " : "lower bound above an infinite lower bound; ";
                }
                continue;
            }
            if (zb.inf) {
                if (zb.inf != (side ? 1 : -1)) {
                    v.ok = false;
                    v.why += "an infinite bound on the wrong side; ";
                }
                continue;
            }
            e.clear();
            e.add(a.h);
            e.add(a.l);
            e.add(b.h);
            e.add(b.l);
            const double refv = e.value();
            e.sub(zb.h);
            e.sub(zb.l);
            const int s = e.sign();   // exact - z
            const bool good = side ? s <= 0 : s >= 0;
            if (!good) {
                v.ok = false;
                v.why += side ? "upper bound below the exact one; " : "lower bound above the exact one; ";
            }
            v.ex[side] = std::fabs(e.value());
            v.ref[side] = refv;
            v.measured[side] = true;
        }
    };
    auto check_corners = [&](const std::vector<Corner>& cs) {
        // z.lo <= every corner, z.hi >= every corner; the excess over the extreme corner.
        for (int side = 0; side < 2; ++side) {
            const XV& zb = side ? z.hi : z.lo;
            double best = kInf, bestref = 0;
            bool finite_all = !zb.inf;
            for (const Corner& c : cs) {
                double diff = 0, cval = 0;
                const int s = cmp_corner(zb, c, e, &diff, &cval);   // sign of zb - c
                if (side ? s < 0 : s > 0) {
                    v.ok = false;
                    v.why += side ? "upper bound below a product of bounds; " : "lower bound above a product of bounds; ";
                }
                if (c.inf) finite_all = false;
                const double d = std::fabs(diff);
                if (d < best) {
                    best = d;
                    bestref = cval;
                }
            }
            if (finite_all) {
                v.ex[side] = best;
                v.ref[side] = bestref;
                v.measured[side] = true;
            }
        }
    };
    switch (op) {
    case ADD:
    case ADD_LEAN:
    case ADD_SLOPPY:
        check_sum(x.lo, y.lo, x.hi, y.hi);
        break;
    case SUB: {
        const XV nyl{-y.hi.inf, -y.hi.h, -y.hi.l}, nyh{-y.lo.inf, -y.lo.h, -y.lo.l};
        check_sum(x.lo, nyl, x.hi, nyh);
        break;
    }
    case ADD_NUM:
        if (t_whole) {
            if (!(z.lo.inf == -1 && z.hi.inf == 1)) {
                v.ok = false;
                v.why += "x + t for t not finite: not the whole line; ";
            }
        } else {
            check_sum(x.lo, ty, x.hi, ty);
        }
        break;
    case NEG:
        check_sum(XV{-x.hi.inf, -x.hi.h, -x.hi.l}, XV{0, 0, 0}, XV{-x.lo.inf, -x.lo.h, -x.lo.l}, XV{0, 0, 0});
        break;
    case CONV:
        check_sum(x.lo, XV{0, 0, 0}, x.hi, XV{0, 0, 0});
        break;
    case SQR: {
        // The range of t^2 over x: [lo^2, hi^2] (lo >= 0), [hi^2, lo^2] (hi <= 0), [0, max] otherwise.
        const int sl = sgn(x.lo), sh = sgn(x.hi);
        std::vector<Corner> lc, hc;
        if (sl >= 0) {
            lc = {corner(x.lo, x.lo)};
            hc = {corner(x.hi, x.hi)};
        } else if (sh <= 0) {
            lc = {corner(x.hi, x.hi)};
            hc = {corner(x.lo, x.lo)};
        } else {
            lc = {Corner{0, true, 0, 0, 0, 0}};
            hc = {corner(x.lo, x.lo), corner(x.hi, x.hi)};
        }
        // lower: z.lo <= the least value (the one corner of lc); upper: z.hi >= every corner of hc.
        double diff = 0, cval = 0;
        int s = cmp_corner(z.lo, lc[0], e, &diff, &cval);
        if (s > 0) {
            v.ok = false;
            v.why += "square: lower bound above the exact one; ";
        }
        if (!z.lo.inf && !lc[0].inf) {
            v.ex[0] = std::fabs(diff);
            v.ref[0] = cval;
            v.measured[0] = true;
        }
        double best = kInf, bestref = 0;
        bool fin = !z.hi.inf;
        for (const Corner& c : hc) {
            s = cmp_corner(z.hi, c, e, &diff, &cval);
            if (s < 0) {
                v.ok = false;
                v.why += "square: upper bound below the exact one; ";
            }
            if (c.inf) fin = false;
            if (std::fabs(diff) < best) {
                best = std::fabs(diff);
                bestref = cval;
            }
        }
        if (fin) {
            v.ex[1] = best;
            v.ref[1] = bestref;
            v.measured[1] = true;
        }
        break;
    }
    default: {   // the products
        std::vector<Corner> cs;
        if (op == MUL_NUM) {
            if (t_whole) {
                const XV w0{-1, 0, 0}, w1{1, 0, 0};
                cs = {corner(x.lo, w0), corner(x.lo, w1), corner(x.hi, w0), corner(x.hi, w1)};
            } else {
                cs = {corner(x.lo, ty), corner(x.hi, ty)};
            }
        } else {
            cs = {corner(x.lo, y.lo), corner(x.lo, y.hi), corner(x.hi, y.lo), corner(x.hi, y.hi)};
        }
        check_corners(cs);
        break;
    }
    }
    return v;
}

// --- The operations under test -------------------------------------------------------------------------

u2::Interval apply(Op op, const u2::Interval& x, const u2::Interval& y, double t) {
    kairn::upward::Scope scope;
    d2::R a = x.r_, b = y.r_;
    d2::pin(a);
    d2::bar(b);
    d2::R z;
    switch (op) {
    case ADD: z = d2::add_r(a, b); break;
    case ADD_LEAN: z = d2::add_r<d2::SumForm::lean>(a, b); break;
    case ADD_SLOPPY: z = d2::add_r<d2::SumForm::sloppy>(a, b); break;
    case SUB: z = d2::add_r(a, d2::neg_r(b)); break;
    case MUL_SEL2: z = d2::mul_sel2(a, b); break;
    case MUL_EIGHT: z = d2::mul_eight(a, b); break;
    case MUL_TABLE: z = d2::mul_table(a, b); break;
    case MUL_BRANCH: z = d2::mul_branch(a, b); break;
#if KAIRN_UPWARD2_AVX2
    case MUL_SEL4: z = d2::mul_sel4(a, b); break;
#endif
    case SQR: z = d2::sqr_r(a); break;
    case ADD_NUM: return x + t;
    case MUL_NUM: return x * t;
    case NEG: return -x;
    default: z = a; break;
    }
    d2::bar(z);
    return u2::Interval(z);
}
I2 apply_default(Op op, const I2& x, const I2& y, double t) {
    switch (op) {
    case ADD:
    case ADD_LEAN:
    case ADD_SLOPPY: return x + y;
    case SUB: return x - y;
    case SQR: return x * x;
    case ADD_NUM: return x + I2(t);
    case MUL_NUM: return x * I2(t);
    case NEG: return -x;
    case CONV: return x;
    default: return x * y;
    }
}
u2::Interval to_type(const DI& d) {
    kairn::upward::Scope scope;
    return u2::from_interval(I2::from_limbs(&d.l0));
}
// The default interval of the type's value, exactly (to_interval, under rounding to nearest).
I2 to_default(const u2::Interval& z) { return u2::to_interval(z); }

bool op_available([[maybe_unused]] Op op) {
#if KAIRN_UPWARD2_AVX2
    return true;
#else
    return op != MUL_SEL4;
#endif
}

// --- Statistics ------------------------------------------------------------------------------------------

struct Stat {
    long n = 0, bad = 0, unnormalized = 0, zero_ref = 0, exact = 0;
    std::vector<float> rel;
    std::string first_bad;
    void add(const Verdict& v, const char* what) {
        ++n;
        if (!v.ok) {
            ++bad;
            if (first_bad.empty()) first_bad = std::string(what) + ": " + v.why;
        }
        if (!v.normalized) {
            ++unnormalized;
            if (first_bad.empty()) first_bad = std::string(what) + ": " + v.why;
        }
        for (int s = 0; s < 2; ++s) {
            if (!v.measured[s]) continue;
            if (v.ex[s] == 0) ++exact;
            if (v.ref[s] == 0) ++zero_ref;
            else rel.push_back(float(v.ex[s] / std::fabs(v.ref[s]) / kU2));
        }
    }
    double q(double f) {
        if (rel.empty()) return 0;
        const std::size_t k = std::min(rel.size() - 1, std::size_t(f * double(rel.size())));
        std::nth_element(rel.begin(), rel.begin() + long(k), rel.end());
        return rel[k];
    }
    double mx() { return rel.empty() ? 0 : *std::max_element(rel.begin(), rel.end()); }
};

std::mutex out_mutex;
std::atomic<int> failures{0};

std::string hex(const DI& d) {
    char b[160];
    std::snprintf(b, sizeof b, "[%a %a, %a %a]", d.l0, d.l1, d.h0, d.h1);
    return b;
}

// One class: n cases of operands from make, every operation.
void run_class(const char* cls, long n, std::uint64_t seed, const std::function<void(Rng&, DI&, DI&, double&)>& make,
               const std::vector<Op>& ops, bool chained) {
    Rng g{seed};
    Exact e;
    std::vector<Stat> mine(N_OPS), dflt(N_OPS);
    std::vector<long> tighter(N_OPS), same(N_OPS), wider(N_OPS);
    for (long i = 0; i < n; ++i) {
        DI dx, dy;
        double t = 0;
        make(g, dx, dy, t);
        u2::Interval x = to_type(dx), y = to_type(dy);
        if (chained) {
            // Operands that are results of earlier operations of the type.
            const DI dw = interval(g, g.range(0, 4), -30, 30, g.range(20, 100));
            const u2::Interval w = to_type(dw);
            const int k = g.range(0, 3);
            x = k == 0 ? apply(ADD, x, w, 0) : k == 1 ? apply(MUL_TABLE, x, w, 0) : k == 2 ? apply(SUB, x, w, 0) : apply(SQR, x, w, 0);
            y = g.range(0, 1) ? apply(MUL_TABLE, y, x, 0) : apply(ADD, y, x, 0);
        }
        const Res rx = res_of(x), ry = res_of(y);
        // The conversion: x of the type encloses the default x.
        {
            const Res rd = res_of(dx);
            Verdict vc = judge(CONV, rd, rd, 0, rx, true, e);
            if (!chained) mine[CONV].add(vc, (std::string(cls) + " conv " + hex(dx)).c_str());
            // And back: to_interval gives the same bounds exactly.
            const Res back = res_of(to_default(x));
            Exact& t2 = e;
            const bool same_lo = (back.lo.inf == rx.lo.inf) && (rx.lo.inf || cmp_xv(back.lo, rx.lo, t2) == 0);
            const bool same_hi = (back.hi.inf == rx.hi.inf) && (rx.hi.inf || cmp_xv(back.hi, rx.hi, t2) == 0);
            if (!(same_lo && same_hi) && !rx.empty) {
                Verdict vb;
                vb.ok = false;
                vb.why = "to_interval does not give the same bounds";
                mine[CONV].add(vb, (std::string(cls) + " to_interval " + hex(dx)).c_str());
            }
        }
        const I2 kx = to_default(x), ky = to_default(y);
        for (Op op : ops) {
            if (!op_available(op)) continue;
            const u2::Interval z = apply(op, x, y, t);
            const Res rz = res_of(z);
            const Verdict v = judge(op, rx, ry, t, rz, true, e);
            if (!v.ok || !v.normalized) {
                std::lock_guard<std::mutex> lock(out_mutex);
                if (mine[op].bad + mine[op].unnormalized < 3) {
                    double o[4];
                    z.to_limbs(o);
                    double xa[4], ya[4];
                    x.to_limbs(xa);
                    y.to_limbs(ya);
                    std::printf("  INVALID %s %s: x=(%a %a | %a %a) y=(%a %a | %a %a) t=%a z=(%a %a | %a %a): %s\n", kOpName[op],
                                cls, xa[0], xa[1], xa[2], xa[3], ya[0], ya[1], ya[2], ya[3], t, o[0], o[1], o[2], o[3], v.why.c_str());
                }
            }
            mine[op].add(v, kOpName[op]);
            if (op == CONV) continue;
            const I2 kz = apply_default(op, kx, ky, t);
            Verdict vk = judge(op == SQR ? MUL_TABLE : op, res_of(kx), res_of(ky), t, res_of(kz), false, e);
            if (op == SQR) {
                // The default has no square: x * x encloses the square; judged as the product x x.
                vk = judge(MUL_TABLE, res_of(kx), res_of(kx), t, res_of(kz), false, e);
            }
            dflt[op].add(vk, "default");
            for (int s = 0; s < 2; ++s) {
                if (!v.measured[s] || !vk.measured[s]) continue;
                (v.ex[s] < vk.ex[s] ? tighter[op] : v.ex[s] == vk.ex[s] ? same[op] : wider[op])++;
            }
        }
    }
    std::lock_guard<std::mutex> lock(out_mutex);
    for (Op op : ops) {
        if (!op_available(op)) continue;
        Stat& s = mine[op];
        std::printf("%-11s %-40s type    n=%ld invalid=%ld unnormalized=%ld exact_bounds=%ld median=%.3g p99=%.3g max=%.3g (u^2) zero_ref=%ld\n",
                    kOpName[op], cls, s.n, s.bad, s.unnormalized, s.exact, s.q(0.5), s.q(0.99), s.mx(), s.zero_ref);
        if (!s.first_bad.empty()) std::printf("  first: %s\n", s.first_bad.c_str());
        if (s.bad || s.unnormalized) failures += 1;
        if (op == CONV) continue;
        Stat& k = dflt[op];
        std::printf("%-11s %-40s default n=%ld invalid=%ld median=%.3g p99=%.3g max=%.3g (u^2); per bound: type tighter %ld, equal %ld, wider %ld\n",
                    kOpName[op], cls, k.n, k.bad, k.q(0.5), k.q(0.99), k.mx(), tighter[op], same[op], wider[op]);
        if (k.bad) {
            std::printf("  THE CHECKER REJECTS A RESULT OF THE DEFAULT INTERVAL: the check is wrong (%s)\n", k.first_bad.c_str());
            failures += 1;
        }
    }
    std::fflush(stdout);
}

// --- Special values ----------------------------------------------------------------------------------

void run_special() {
    const double om = kMax, eta = std::numeric_limits<double>::denorm_min(), mn = std::numeric_limits<double>::min();
    const std::vector<DI> v = {
        {kInf, 0, -kInf, 0},            // empty
        {-kInf, 0, kInf, 0},            // the whole line
        {-kInf, 0, -3, 0x1p-55},
        {-kInf, 0, 0, 0},
        {-kInf, 0, 5, 0},
        {-kInf, 0, -om, 0},
        {2, -0x1p-54, kInf, 0},
        {0, 0, kInf, 0},
        {-7, 0, kInf, 0},
        {om, 0, kInf, 0},
        {0, 0, 0, 0},
        {-1, 0, 0, 0},
        {0, 0, 1, 0x1p-53},
        {1, 0, 1, 0},
        {-3, 0x1p-52, 2, -0x1p-53},
        {om, 0, om, 0},
        {-om, 0, -om, 0},
        {0x1p1023, 0, om, 0},
        {-om, 0, om, 0},
        {om, -0x1p969, om, 0},
        {0x1.8p1023, 0x1p969, 0x1.8p1023, 0x1p969},
        {0x1p600, 0x1p546, 0x1p601, 0},
        {-0x1p601, 0, -0x1p600, -0x1p546},
        {0x1p-600, 0, 0x1p-599, 0x1p-653},
        {eta, 0, eta, 0},
        {-eta, 0, eta, 0},
        {mn, 0, mn, eta},
        {-mn, -eta, 4 * eta, 0},
        {0x1p-1000, 0x1p-1060, 0x1p-999, 0},
        {1 + 0x1p-52, 0x1p-106, 1 + 0x1p-51, 0},
        {-2, 0, -2, 0},
        {0.5, 0, 3, 0},
    };
    const double ts[] = {0.0, -0.0, 1.0, -2.5, 0x1p-1074, 0x1p1000, -0x1p1000, om, kInf, -kInf, std::numeric_limits<double>::quiet_NaN()};
    Exact e;
    long pairs = 0, bad = 0, unnorm = 0;
    // Against Interval<double, 2>: the same bounds; a structural difference (a bound infinite in one
    // result and finite in the other, or one result empty), each listed; or a difference of finite
    // values only (the last bits of a bound), counted as tighter, wider or mixed, a few listed.
    long same = 0, structural = 0, f_tighter = 0, f_wider = 0, f_mixed = 0;
    std::vector<std::string> diffs, finite_examples;
    auto compare_with_default = [&](const char* name, const std::string& operands, const Res& rz, const Res& rk) {
        if (rz.empty || rk.empty) {
            if (rz.empty == rk.empty) ++same;
            else {
                ++structural;
                diffs.push_back(std::string(name) + " " + operands + ": one empty, the other not");
            }
            return;
        }
        const int lo = cmp_xv(rz.lo, rk.lo, e), hi = cmp_xv(rz.hi, rk.hi, e);
        if (lo == 0 && hi == 0) {
            ++same;
            return;
        }
        char b[360];
        auto txt = [](const XV& x) {
            char s[64];
            if (x.inf) std::snprintf(s, sizeof s, "%sinf", x.inf > 0 ? "+" : "-");
            else std::snprintf(s, sizeof s, "%a%+a", x.h, x.l);
            return std::string(s);
        };
        std::snprintf(b, sizeof b, "%s %s: type [%s, %s], default [%s, %s]", name, operands.c_str(), txt(rz.lo).c_str(), txt(rz.hi).c_str(),
                      txt(rk.lo).c_str(), txt(rk.hi).c_str());
        const char* how = lo >= 0 && hi <= 0 ? "type tighter" : lo <= 0 && hi >= 0 ? "type wider" : "mixed";
        if (rz.lo.inf != rk.lo.inf || rz.hi.inf != rk.hi.inf) {
            ++structural;
            diffs.push_back(std::string(how) + ": " + b);
            return;
        }
        (lo >= 0 && hi <= 0 ? f_tighter : lo <= 0 && hi >= 0 ? f_wider : f_mixed)++;
        if (finite_examples.size() < 6) finite_examples.push_back(std::string(how) + ": " + b);
    };
    const std::vector<Op> binary = {ADD, SUB, MUL_SEL2, MUL_EIGHT, MUL_TABLE, MUL_BRANCH, MUL_SEL4, ADD_LEAN, ADD_SLOPPY};
    for (const DI& dx : v) {
        const u2::Interval x = to_type(dx);
        const Res rx = res_of(x);
        const I2 kx = I2::from_limbs(&dx.l0);
        {   // the conversion
            ++pairs;
            const Verdict vc = judge(CONV, res_of(dx), res_of(dx), 0, rx, true, e);
            if (!vc.ok) ++bad;
            if (!vc.normalized) ++unnorm;
            if (!vc.ok || !vc.normalized) std::printf("  SPECIAL INVALID conv %s: %s\n", hex(dx).c_str(), vc.why.c_str());
            compare_with_default("conv", hex(dx), res_of(to_default(x)), res_of(kx));
        }
        for (Op op : {SQR, NEG}) {
            ++pairs;
            const u2::Interval z = apply(op, x, x, 0);
            const Verdict vz = judge(op, rx, rx, 0, res_of(z), true, e);
            if (!vz.ok) ++bad;
            if (!vz.normalized) ++unnorm;
            if (!vz.ok || !vz.normalized) std::printf("  SPECIAL INVALID %s %s: %s\n", kOpName[op], hex(dx).c_str(), vz.why.c_str());
            if (op == NEG) compare_with_default(kOpName[op], hex(dx), res_of(to_default(z)), res_of(-kx));
        }
        for (double t : ts) {
            for (Op op : {ADD_NUM, MUL_NUM}) {
                ++pairs;
                const u2::Interval z = apply(op, x, x, t);
                const Verdict vz = judge(op, rx, rx, t, res_of(z), true, e);
                if (!vz.ok) ++bad;
                if (!vz.normalized) ++unnorm;
                char tb[48];
                std::snprintf(tb, sizeof tb, " t=%a", t);
                if (!vz.ok || !vz.normalized)
                    std::printf("  SPECIAL INVALID %s %s%s: %s\n", kOpName[op], hex(dx).c_str(), tb, vz.why.c_str());
                compare_with_default(kOpName[op], hex(dx) + tb, res_of(to_default(z)), res_of(apply_default(op, kx, kx, t)));
            }
        }
        for (const DI& dy : v) {
            const u2::Interval y = to_type(dy);
            const Res ry = res_of(y);
            const I2 ky = I2::from_limbs(&dy.l0);
            for (Op op : binary) {
                if (!op_available(op)) continue;
                ++pairs;
                const u2::Interval z = apply(op, x, y, 0);
                const Verdict vz = judge(op, rx, ry, 0, res_of(z), true, e);
                if (!vz.ok) ++bad;
                if (!vz.normalized) ++unnorm;
                if (!vz.ok || !vz.normalized) {
                    double o[4];
                    z.to_limbs(o);
                    std::printf("  SPECIAL INVALID %s x=%s y=%s z=(%a %a | %a %a): %s\n", kOpName[op], hex(dx).c_str(), hex(dy).c_str(), o[0],
                                o[1], o[2], o[3], vz.why.c_str());
                }
                // Against the default on the operands as the default gives them (the conversion of
                // a bound MAX with a positive second limb differs, and is reported above).
                compare_with_default(kOpName[op], "x=" + hex(dx) + " y=" + hex(dy), res_of(to_default(z)),
                                     res_of(apply_default(op, kx, ky, 0)));
            }
        }
    }
    std::printf("special values: %ld cases, invalid=%ld, unnormalized=%ld; against Interval<double, 2>: same %ld, structural "
                "differences %ld (listed), finite values differing: type tighter %ld, type wider %ld, mixed %ld\n",
                pairs, bad, unnorm, same, structural, f_tighter, f_wider, f_mixed);
    for (const std::string& d : finite_examples) std::printf("  finite example, %s\n", d.c_str());
    std::sort(diffs.begin(), diffs.end());
    for (const std::string& d : diffs) std::printf("  STRUCTURAL %s\n", d.c_str());
    if (bad || unnorm) failures += 1;
}

}  // namespace

int main(int argc, char** argv) {
    const long n = argc > 1 ? std::atol(argv[1]) : 2000000;
    const std::uint64_t seed = argc > 2 ? std::strtoull(argv[2], nullptr, 0) : 20261127u;
    const int threads = argc > 3 ? std::atoi(argv[3]) : 8;
    std::printf("x2-check: n=%ld per class, seed=%llu, threads=%d, form %d (1 SSE, 2 NEON, 3 numbers), AVX2 %d, product form %d, flags: %s\n",
                n, static_cast<unsigned long long>(seed), threads, KAIRN_UPWARD2_FORM, KAIRN_UPWARD2_AVX2, KAIRN_UPWARD2_MUL,
#ifdef X2_FLAGS
                X2_FLAGS
#else
                "?"
#endif
    );
    const std::vector<Op> all = {ADD, SUB, MUL_SEL2, MUL_EIGHT, MUL_TABLE, MUL_BRANCH, MUL_SEL4, SQR,
                                 ADD_NUM, MUL_NUM, NEG, CONV, ADD_LEAN, ADD_SLOPPY};
    auto mix = [](Rng& g, int kmin, int kmax) { return interval(g, g.range(0, 4), kmin, kmax, g.range(20, 100)); };
    auto num = [](Rng& g, int kmin, int kmax) {
        const int k = g.range(0, 9);
        if (k == 0) return 0.0;
        if (k == 1) return std::ldexp(1.0, g.range(kmin, kmax));
        const P2 p = number(g, kmin, kmax);
        return p.h;
    };
    struct Cls {
        const char* name;
        std::function<void(Rng&, DI&, DI&, double&)> make;
        bool chained;
    };
    const std::vector<Cls> classes = {
        {"as the benchmark (narrow 2^-80, 2^+-8)", [&](Rng& g, DI& x, DI& y, double& t) {
             x = interval(g, 0, -8, 8, 80);
             y = interval(g, 0, -8, 8, 80);
             t = num(g, -8, 8);
         }, false},
        {"points, 2^+-60", [&](Rng& g, DI& x, DI& y, double& t) {
             x = interval(g, 3, -60, 60, 0);
             y = interval(g, 3, -60, 60, 0);
             t = num(g, -60, 60);
         }, false},
        {"narrow 2^-20..2^-100, 2^+-60", [&](Rng& g, DI& x, DI& y, double& t) {
             x = interval(g, 0, -60, 60, g.range(20, 100));
             y = interval(g, 0, -60, 60, g.range(20, 100));
             t = num(g, -60, 60);
         }, false},
        {"wide (unrelated bounds), 2^+-60", [&](Rng& g, DI& x, DI& y, double& t) {
             x = interval(g, 1, -60, 60, 0);
             y = interval(g, 1, -60, 60, 0);
             t = num(g, -60, 60);
         }, false},
        {"around zero, 2^+-60", [&](Rng& g, DI& x, DI& y, double& t) {
             x = interval(g, 2, -60, 60, 0);
             y = g.range(0, 1) ? interval(g, 2, -60, 60, 0) : mix(g, -60, 60);
             t = num(g, -60, 60);
         }, false},
        {"zeros (a bound 0, [0, 0])", [&](Rng& g, DI& x, DI& y, double& t) {
             x = interval(g, g.range(4, 5), -60, 60, 0);
             y = g.range(0, 1) ? interval(g, g.range(4, 5), -60, 60, 0) : mix(g, -60, 60);
             t = num(g, -60, 60);
         }, false},
        {"any kind, 2^+-500", [&](Rng& g, DI& x, DI& y, double& t) {
             x = mix(g, -500, 500);
             y = mix(g, -500, 500);
             t = num(g, -500, 500);
         }, false},
        {"tiny (second limbs underflow), 2^-1074..2^-900", [&](Rng& g, DI& x, DI& y, double& t) {
             x = mix(g, -1074, -900);
             y = g.range(0, 1) ? mix(g, -1074, -900) : mix(g, -200, 200);
             t = num(g, -600, 0);
         }, false},
        {"huge (near overflow), 2^900..2^1023", [&](Rng& g, DI& x, DI& y, double& t) {
             x = mix(g, 900, 1023);
             y = g.range(0, 1) ? mix(g, 900, 1023) : mix(g, -200, 200);
             t = num(g, 0, 600);
         }, false},
        {"cancellation (y near -x)", [&](Rng& g, DI& x, DI& y, double& t) {
             x = mix(g, -8, 8);
             const int j = g.range(30, 110);
             const double d = g.range(0, 3) == 0 ? 0.0 : (g.unit() - 0.5) * std::ldexp(std::fabs(x.h0) + std::fabs(x.l0), -j);
             y = put(renorm(-x.h0, -x.h1 + d), renorm(-x.l0, -x.l1 + d * g.unit()));
             t = -x.h0;
         }, false},
        {"results of earlier operations", [&](Rng& g, DI& x, DI& y, double& t) {
             x = mix(g, -30, 30);
             y = mix(g, -30, 30);
             t = num(g, -30, 30);
         }, true},
    };
    std::vector<std::thread> pool;
    std::atomic<std::size_t> next{0};
    for (int k = 0; k < threads; ++k) {
        pool.emplace_back([&]() {
            for (;;) {
                const std::size_t i = next++;
                if (i >= classes.size()) break;
                run_class(classes[i].name, n, seed + 100 * (i + 1), classes[i].make, all, classes[i].chained);
            }
        });
    }
    for (std::thread& t : pool) t.join();
    run_special();
    if (std::fegetround() != FE_TONEAREST) {
        std::printf("the rounding mode was left changed\n");
        failures += 1;
    }
    std::printf(failures ? "FAILED: %d\n" : "ok (%d failures)\n", failures.load());
    return failures ? 1 : 0;
}
