// The exact checks of the experimental four-limb interval rounded upward (experiments/upward4/
// README.md). EXPERIMENTAL, NOT VERIFIED, not part of the library. Requires the rounding mode upward
// set by kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang
// -frounding-math): every operation of the type below runs inside a Scope; the checks themselves run
// under rounding to nearest.
//
// For each class of operands (n pairs each, from a fixed seed, the same with every compiler) and each
// operation (+ in both forms, -, the four forms of *, the square, x + t, x * t, -x, the conversions,
// the bounds as numbers, the predicates, the width, the functions on arrays): the result must contain
// the exact range (exact arithmetic, ../../upward2/tests/exact.hpp) and satisfy the invariant (each
// adjacent pair of limbs (a, b) with b <= 0 and |b| below the gap under a; zero later limbs after a
// first limb +inf or +-MAX); the excess of each bound over the exact one, relative, in units of u^4 =
// 2^-212, is printed (median, 99th percentile, largest), with the calls of the cold paths and, per
// operation, the share of its results that took one ("cold=", counted with KAIRN_UPWARD4_COUNT). Then every
// pair of a list of special values, against the exact range in the extended reals (0 times infinity is
// 0), and the answers compared with the two-limb experiment's (which follow Interval<double, 2>'s).
// Exit status 0 when nothing failed.
//
// Usage: x4-check [N per class (default 2000000)] [seed] [threads]
#include <kairn/experimental/upward4.hpp>
#include <kairn/experimental/upward4_forms.hpp>
#if __has_include(<kairn/experimental/upward4_arrays.hpp>)
#include <kairn/experimental/upward4_arrays.hpp>
#define X4_ARRAYS 1
#else
#define X4_ARRAYS 0
#endif
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

#include "../../upward2/tests/exact.hpp"

namespace {

namespace u4 = kairn::experimental::upward4;
namespace d4 = kairn::experimental::upward4::detail;
namespace u2 = kairn::experimental::upward2;
using x2test::Exact;
using I2 = kairn::Interval<double, 2>;
using U1 = kairn::upward::Interval<double>;

constexpr double kInf = std::numeric_limits<double>::infinity();
constexpr double kMax = std::numeric_limits<double>::max();
constexpr double kNaN = std::numeric_limits<double>::quiet_NaN();
constexpr double kU4 = 0x1p-212;

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

// --- Quadruples and intervals as stored ---------------------------------------------------------------

struct Q4 {
    double a[4];
};
// The stored state: u = the upper quadruple (lane 0), n = the negated lower one (lane 1).
struct I4 {
    Q4 u, n;
};
I4 state(const u4::Interval& x) {
    double p[8];
    x.to_limbs(p);
    return I4{{{p[0], p[2], p[4], p[6]}}, {{p[1], p[3], p[5], p[7]}}};
}
u4::Interval of_state(const I4& s) {
    const double p[8] = {s.u.a[0], s.n.a[0], s.u.a[1], s.n.a[1], s.u.a[2], s.n.a[2], s.u.a[3], s.n.a[3]};
    return u4::Interval::from_limbs(p);
}
void add_q(Exact& e, const Q4& q, bool negate = false) {
    for (int i = 0; i < 4; ++i) e.add(negate ? -q.a[i] : q.a[i]);
}

// The invariant of one quadruple (finite, below MAX: each pair (a, b) with b <= 0 and a + b > pred(a);
// a head +inf or +-MAX: zero later limbs; no NaN, no -inf).
bool normalized_pair(double h, double l) {
    if (h != h || l != l || h == -kInf || std::fabs(l) == kInf) return false;
    if (l > 0) return false;
    if (h == 0) return l == 0;
    const double gap = h - std::nextafter(h, -kInf);   // exact
    return -l < gap;
}
bool normalized_q(const Q4& q) {
    if (q.a[0] != q.a[0] || q.a[0] == -kInf) return false;
    if (q.a[0] == kInf || std::fabs(q.a[0]) == kMax) return q.a[1] == 0 && q.a[2] == 0 && q.a[3] == 0;
    return normalized_pair(q.a[0], q.a[1]) && normalized_pair(q.a[1], q.a[2]) && normalized_pair(q.a[2], q.a[3]);
}
bool is_empty_state(const I4& s) { return s.u.a[0] != s.u.a[0]; }
bool canonical(const I4& s) {
    if (s.u.a[0] != s.u.a[0] || s.n.a[0] != s.n.a[0]) return s.u.a[0] != s.u.a[0] && s.n.a[0] != s.n.a[0];
    if (!normalized_q(s.u) || !normalized_q(s.n)) return false;
    if (s.u.a[0] == kInf || s.n.a[0] == kInf) return true;
    Exact e;   // -N <= U
    add_q(e, s.u);
    add_q(e, s.n);
    return e.sign() >= 0;
}

// --- Operands ------------------------------------------------------------------------------------------

// A normalized quadruple: a0 of magnitude 2^[kmin, kmax], each later limb -f gap(a_i) with f in [0, 1)
// by the shape: 0 random, 1 a gap (f = r 2^-g, g up to 150), 2 near a full gap (f = 1 - r 2^-g), 3
// truncated (the limbs from a random place on zero), 4 a mixture per limb.
Q4 number4(Rng& g, int kmin, int kmax, int shape) {
    Q4 q{};
    const double sign = (g.next() & 1) ? 1.0 : -1.0;
    q.a[0] = sign * std::ldexp(1.0 + g.unit(), g.range(kmin, kmax));
    if (!(std::fabs(q.a[0]) <= kMax)) q.a[0] = sign * kMax;
    if (std::fabs(q.a[0]) == kMax) return q;
    const int stop = shape == 3 ? g.range(1, 4) : 4;
    for (int i = 0; i + 1 < 4; ++i) {
        if (i + 1 >= stop || q.a[i] == 0) break;
        const int sh = shape == 4 ? g.range(0, 2) : shape == 3 ? 0 : shape;
        double f = g.unit();
        if (sh == 1) f = std::ldexp(f, -g.range(1, 150));
        if (sh == 2) f = 1.0 - std::ldexp(f, -g.range(1, 52));
        const double gap = q.a[i] - std::nextafter(q.a[i], -kInf);
        double l = -(f * gap);
        if (!normalized_pair(q.a[i], l)) l = 0.0;
        q.a[i + 1] = l + 0.0;
    }
    return q;
}
Exact val(const Q4& q) {
    Exact e;
    add_q(e, q);
    return e;
}
Q4 up4(const Exact& v) {
    Q4 q;
    x2test::upper4(v, q.a);
    return q;
}
// The interval [lo, hi] (exact values, lo <= hi) as stored: U = upper4(hi), N = upper4(-lo).
I4 make(const Exact& lo, const Exact& hi) {
    Exact m = lo;
    m.mul(-1.0);
    return I4{up4(hi), up4(m)};
}
// Kinds: 0 narrow (half-width 2^-rel of the center), 1 two unrelated bounds, 2 around zero, 3 a point,
// 4 one bound zero, 5 [0, 0].
I4 interval4(Rng& g, int kind, int kmin, int kmax, int rel, int shape) {
    const Q4 c = number4(g, kmin, kmax, shape);
    Exact cv = val(c);
    if (kind == 0) {
        const double w = std::fabs(c.a[0]) * std::ldexp(0.5 + 0.5 * g.unit(), -rel);
        Exact lo = cv, hi = cv;
        lo.sub(w);
        hi.add(w);
        return make(lo, hi);
    }
    if (kind == 1) {
        Exact dv = val(number4(g, kmin, kmax, shape));
        Exact t = dv;
        t.add(cv, true);
        return t.sign() >= 0 ? make(cv, dv) : make(dv, cv);
    }
    if (kind == 2) {
        Exact dv = val(number4(g, kmin, kmax, shape));
        if (cv.sign() > 0) cv.mul(-1.0);
        if (dv.sign() < 0) dv.mul(-1.0);
        return make(cv, dv);
    }
    if (kind == 3) return make(cv, cv);
    if (kind == 4) {
        Exact z;
        return cv.sign() >= 0 ? make(z, cv) : make(cv, z);
    }
    Exact z;
    return make(z, z);
}

// --- Bounds in the extended reals ------------------------------------------------------------------------

// A bound: -inf, +inf, or the finite value of q (negated for a lower bound).
struct XV {
    int inf;   // -1, 0, +1
    Q4 q;      // the value is q.a[0] + ... + q.a[3]
};
struct Res {
    bool empty;
    XV lo, hi;
};
Res res_of(const I4& s) {
    Res r{};
    r.empty = is_empty_state(s);
    if (s.u.a[0] == kInf) r.hi = {1, {}};
    else r.hi = {0, s.u};
    if (s.n.a[0] == kInf) r.lo = {-1, {}};
    else r.lo = {0, {{-s.n.a[0], -s.n.a[1], -s.n.a[2], -s.n.a[3]}}};
    return r;
}
XV negx(const XV& v) { return {-v.inf, {{-v.q.a[0], -v.q.a[1], -v.q.a[2], -v.q.a[3]}}}; }
int sgn(const XV& v) {
    if (v.inf) return v.inf;
    return val(v.q).sign();
}

struct Verdict {
    bool ok = true;
    bool normalized = true;
    std::string why;
    double ex[2] = {0, 0}, ref[2] = {0, 0};
    bool measured[2] = {false, false};
};

enum Op { ADD, ADD_SLOPPY, SUB, MUL_BRANCH, MUL_TABLE, MUL_SEL2, MUL_SEL4, SQR, ADD_NUM, MUL_NUM, NEG, CONV_I2, TO_I2, TO_U2, FROM_U2,
          TO_U1, FROM_U1, BOUNDS, ARR_ADD, ARR_SUB, ARR_MUL, N_OPS };
const char* const kOpName[N_OPS] = {"add", "add.sloppy", "sub", "mul.branch", "mul.table", "mul.sel2", "mul.sel4", "sqr", "add_num",
                                    "mul_num", "neg", "from_i2", "to_i2", "to_u2", "from_u2", "to_u1", "from_u1", "bounds",
                                    "arrays.add", "arrays.sub", "arrays.mul"};
Op judged(Op op) { return op == ARR_ADD ? ADD : op == ARR_SUB ? SUB : op == ARR_MUL ? MUL_BRANCH : op; }

// A product of two bounds (extended reals; 0 times an infinity is 0), compared with a bound v: the sign
// of v - corner, and |v - corner| and the corner's value (approximate) when both are finite.
int cmp_corner(const XV& v, const XV& a, const XV& b, Exact& t, double* diff, double* cval, bool* finite) {
    const int sa = sgn(a), sb = sgn(b);
    *finite = false;
    if (sa == 0 || sb == 0) {   // the corner is 0
        if (v.inf) return v.inf;
        *finite = true;
        t.clear();
        add_q(t, v.q);
        *cval = 0;
        *diff = t.value();
        return t.sign();
    }
    if (a.inf || b.inf) {
        const int ci = sa * sb;
        return v.inf == ci ? 0 : (v.inf - ci > 0 ? 1 : -1);
    }
    if (v.inf) return v.inf;
    t.clear();
    for (int i = 0; i < 4; ++i)
        for (int j = 0; j < 4; ++j) t.add_product(a.q.a[i], b.q.a[j]);
    *cval = t.value();
    for (int i = 0; i < 4; ++i) t.sub(v.q.a[i]);
    *finite = true;
    *diff = -t.value();
    return -t.sign();
}

Verdict judge(Op op, const Res& x, const Res& y, double t, const Res& z, bool type_result, const I4* zs, Exact& e) {
    Verdict v;
    const bool unary = op == SQR || op == NEG || op >= CONV_I2 || op == ADD_NUM || op == MUL_NUM;
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
    if (type_result && zs) {
        v.normalized = canonical(*zs);
        if (!v.normalized) v.why = "the result is not canonical (a quadruple not normalized, or crossed bounds); ";
    }
    const XV ty = std::fabs(t) < kInf ? XV{0, {{t, 0, 0, 0}}} : XV{t > 0 ? 1 : -1, {}};
    const bool t_whole = !(std::fabs(t) < kInf);
    const XV zero{0, {}};
    auto check_sum = [&](const XV& al, const XV& bl, const XV& ah, const XV& bh) {
        for (int side = 0; side < 2; ++side) {
            const XV& a = side ? ah : al;
            const XV& b = side ? bh : bl;
            const XV& zb = side ? z.hi : z.lo;
            const int inf = a.inf ? a.inf : b.inf;
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
            add_q(e, a.q);
            add_q(e, b.q);
            const double refv = e.value();
            add_q(e, zb.q, true);
            const int s = e.sign();   // exact - z
            if (!(side ? s <= 0 : s >= 0)) {
                v.ok = false;
                v.why += side ? "upper bound below the exact one; " : "lower bound above the exact one; ";
            }
            v.ex[side] = std::fabs(e.value());
            v.ref[side] = refv;
            v.measured[side] = true;
        }
    };
    // z.lo <= every corner of cl, z.hi >= every corner of ch; the excess over the extreme corner.
    auto check_corners = [&](const std::vector<std::pair<XV, XV>>& cl, const std::vector<std::pair<XV, XV>>& ch) {
        for (int side = 0; side < 2; ++side) {
            const XV& zb = side ? z.hi : z.lo;
            double best = kInf, bestref = 0;
            bool fin = !zb.inf;
            for (const auto& c : side ? ch : cl) {
                double diff = 0, cval = 0;
                bool finite = false;
                const int s = cmp_corner(zb, c.first, c.second, e, &diff, &cval, &finite);
                if (side ? s < 0 : s > 0) {
                    v.ok = false;
                    v.why += side ? "upper bound below a product of bounds; " : "lower bound above a product of bounds; ";
                }
                if (!finite) fin = false;
                if (std::fabs(diff) < best) {
                    best = std::fabs(diff);
                    bestref = cval;
                }
            }
            if (fin) {
                v.ex[side] = best;
                v.ref[side] = bestref;
                v.measured[side] = true;
            }
        }
    };
    switch (op) {
    case ADD:
    case ADD_SLOPPY: check_sum(x.lo, y.lo, x.hi, y.hi); break;
    case SUB: check_sum(x.lo, negx(y.hi), x.hi, negx(y.lo)); break;
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
    case NEG: check_sum(negx(x.hi), zero, negx(x.lo), zero); break;
    case SQR: {
        const int sl = sgn(x.lo), sh = sgn(x.hi);
        if (sl >= 0) check_corners({{x.lo, x.lo}}, {{x.hi, x.hi}});
        else if (sh <= 0) check_corners({{x.hi, x.hi}}, {{x.lo, x.lo}});
        else check_corners({{zero, zero}}, {{x.lo, x.lo}, {x.hi, x.hi}});
        break;
    }
    case MUL_NUM:
        if (t_whole) {
            const XV w0{-1, {}}, w1{1, {}};
            const std::vector<std::pair<XV, XV>> cs = {{x.lo, w0}, {x.lo, w1}, {x.hi, w0}, {x.hi, w1}};
            check_corners(cs, cs);
        } else {
            const std::vector<std::pair<XV, XV>> cs = {{x.lo, ty}, {x.hi, ty}};
            check_corners(cs, cs);
        }
        break;
    default:
        if (op >= CONV_I2 && op <= BOUNDS) {
            check_sum(x.lo, zero, x.hi, zero);
        } else {
            const std::vector<std::pair<XV, XV>> cs = {{x.lo, y.lo}, {x.lo, y.hi}, {x.hi, y.lo}, {x.hi, y.hi}};
            check_corners(cs, cs);
        }
        break;
    }
    return v;
}

// --- The operations under test -----------------------------------------------------------------------------

bool op_available([[maybe_unused]] Op op) {
#if KAIRN_UPWARD2_AVX2
    return true;
#else
    return op != MUL_SEL4;
#endif
}

u4::Interval apply(Op op, const u4::Interval& x, const u4::Interval& y, double t) {
    kairn::upward::Scope scope;
    d4::R4 a = x.r_, b = y.r_;
    d4::pin(a);
    d4::bar(b);
    d4::R4 z;
    switch (op) {
    case ADD: z = d4::add_accurate_r(a, b); break;
    case ADD_SLOPPY: z = d4::add_sloppy_r(a, b); break;
    case SUB: return x - y;
    case MUL_BRANCH: z = d4::mul_branch(a, b); break;
    case MUL_TABLE: z = d4::mul_table(a, b); break;
    case MUL_SEL2: z = d4::mul_sel2(a, b); break;
#if KAIRN_UPWARD2_AVX2
    case MUL_SEL4: z = d4::mul_sel4(a, b); break;
#endif
    case SQR: return u4::sqr(x);
    case ADD_NUM: return x + t;
    case MUL_NUM: return x * t;
    case NEG: return -x;
    default: z = a; break;
    }
    d4::bar(z);
    return u4::Interval(z);
}

// The functions on arrays on n pairs of operands: z[k] = x[k] op y[k].
void apply_arrays(Op op, const std::vector<u4::Interval>& x, const std::vector<u4::Interval>& y, std::vector<u4::Interval>& z) {
#if !X4_ARRAYS
    (void)op;
    z.clear();
    (void)x;
    (void)y;
#else
    const std::size_t n = x.size();
    std::vector<double> a(24 * n);
    auto view = [&](int k) {
        u4::View<double> v;
        for (int i = 0; i < 4; ++i) {
            v.u[i] = &a[(8 * k + i) * n];
            v.n[i] = &a[(8 * k + 4 + i) * n];
        }
        v.size = n;
        return v;
    };
    const u4::View<double> vx = view(0), vy = view(1), vz = view(2);
    for (std::size_t i = 0; i < n; ++i) {
        const I4 p = state(x[i]), q = state(y[i]);
        for (int k = 0; k < 4; ++k) {
            vx.u[k][i] = p.u.a[k], vx.n[k][i] = p.n.a[k];
            vy.u[k][i] = q.u.a[k], vy.n[k][i] = q.n.a[k];
        }
    }
    auto cview = [](const u4::View<double>& v) {
        u4::View<const double> c;
        for (int i = 0; i < 4; ++i) c.u[i] = v.u[i], c.n[i] = v.n[i];
        c.size = v.size;
        return c;
    };
    if (op == ARR_ADD) u4::add(vz, cview(vx), cview(vy));
    else if (op == ARR_SUB) u4::sub(vz, cview(vx), cview(vy));
    else u4::mul(vz, cview(vx), cview(vy));
    z.resize(n);
    for (std::size_t i = 0; i < n; ++i) {
        I4 s;
        for (int k = 0; k < 4; ++k) s.u.a[k] = vz.u[k][i], s.n.a[k] = vz.n[k][i];
        z[i] = of_state(s);
    }
#endif
}

// --- Statistics ------------------------------------------------------------------------------------------

double worst_of(const Verdict& v) {
    double w = -1;
    for (int s = 0; s < 2; ++s)
        if (v.measured[s] && v.ref[s] != 0) w = std::max(w, v.ex[s] / std::fabs(v.ref[s]) / kU4);
    return w;
}

struct Stat {
    long n = 0, bad = 0, unnormalized = 0, zero_ref = 0, exact = 0;
    long cold = 0;   // results that took a cold path (counted with KAIRN_UPWARD4_COUNT)
    std::vector<float> rel;
    std::string first_bad;
    double worst = -1;
    std::string worst_case;
    void add(const Verdict& v, const std::string& what) {
        ++n;
        if (!v.ok) {
            ++bad;
            if (first_bad.empty()) first_bad = what + ": " + v.why;
        }
        if (!v.normalized) {
            ++unnormalized;
            if (first_bad.empty()) first_bad = what + ": " + v.why;
        }
        for (int s = 0; s < 2; ++s) {
            if (!v.measured[s]) continue;
            if (v.ex[s] == 0) ++exact;
            if (v.ref[s] == 0) ++zero_ref;
            else rel.push_back(float(std::min(1e30, v.ex[s] / std::fabs(v.ref[s]) / kU4)));
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

std::string hex(const I4& s) {
    char b[400];
    std::snprintf(b, sizeof b, "U(%a %a %a %a) N(%a %a %a %a)", s.u.a[0], s.u.a[1], s.u.a[2], s.u.a[3], s.n.a[0], s.n.a[1], s.n.a[2], s.n.a[3]);
    return b;
}

// The default two-limb interval of a stored state, containing it (each bound rounded outward to two
// limbs, nearest-normalized), for the checks of from_interval; and back.
I2 default_of(const I4& s, bool& exact) {
    exact = false;
    if (is_empty_state(s)) return I2::empty();
    auto bound = [&](const Q4& q, bool upper, double& h0, double& h1) {
        // upper: the least canonical pair >= q's value; lower (q negated): the greatest <= -value.
        if (q.a[0] == kInf) {
            h0 = upper ? kInf : -kInf;
            h1 = 0;
            return;
        }
        Exact v = val(q);
        if (!upper) v.mul(-1.0);
        // two limbs to nearest: h0 = RN(v) approximately, then h1 = the rest rounded outward.
        h0 = v.value();
        Exact r = v;
        r.sub(h0);
        double l = r.value();
        // move l outward until h0 + l is on the right side of v
        Exact t;
        for (int it = 0; it < 4; ++it) {
            t = v;
            t.sub(h0);
            t.sub(l);
            const int sg = t.sign();   // v - (h0 + l)
            if (upper ? sg <= 0 : sg >= 0) break;
            l = std::nextafter(l, upper ? kInf : -kInf);
        }
        const double ss = h0 + l;   // renormalize to nearest (exact Fast2Sum, |h0| >= |l|)
        h1 = l - (ss - h0);
        h0 = ss;
    };
    double l0, l1, h0, h1;
    bound(s.u, true, h0, h1);
    bound(s.n, false, l0, l1);
    const double p[4] = {l0, l1 + 0.0, h0, h1 + 0.0};
    return I2::from_limbs(p);
}
I4 state_of_default(const I2& k) {
    I4 s;
    const double l0 = k.lower().limb[0], l1 = k.lower().limb[1], h0 = k.upper().limb[0], h1 = k.upper().limb[1];
    if (l0 == kInf && h0 == -kInf) return I4{{{kNaN, kNaN, kNaN, kNaN}}, {{kNaN, kNaN, kNaN, kNaN}}};
    s.u = h0 == kInf ? Q4{{kInf, 0, 0, 0}} : Q4{{h0, h1, 0, 0}};
    s.n = l0 == -kInf ? Q4{{kInf, 0, 0, 0}} : Q4{{-l0, -l1, 0, 0}};
    return s;   // not normalized: only its values are used
}

bool same_values(const I4& a, const I4& b) {
    for (int i = 0; i < 4; ++i)
        if (!(a.u.a[i] == b.u.a[i]) || !(a.n.a[i] == b.n.a[i])) return false;
    return true;
}

// The conversions and the members, for one interval x of the type: each result must contain x
// (as a set), and the members must be the tight answers.
void check_members(const u4::Interval& x, const I4& xs, Stat* st, Exact& e, const std::string& cls) {
    const Res rx = res_of(xs);
    auto put = [&](Op op, const Verdict& v) { st[op].add(v, cls + " " + kOpName[op] + " " + hex(xs)); };
    // From the default interval: the default interval of x's bounds (rounded outward), converted.
    {
        bool exact = false;
        const I2 k = default_of(xs, exact);
        u4::Interval z;
        {
            kairn::upward::Scope scope;
            z = u4::from_interval(k);
        }
        const I4 zs = state(z);
        put(CONV_I2, judge(CONV_I2, res_of(state_of_default(k)), rx, 0, res_of(zs), true, &zs, e));
        // To the default interval, under rounding to nearest: canonical, and containing x.
        const I2 back = u4::to_interval(x);
        Verdict vb;
        kairn::Expansion<double, 2> lo = back.lower(), hi = back.upper();
        if (!rx.empty && !kairn::detail::canonical_interval(lo, hi)) {
            vb.ok = false;
            vb.why = "to_interval: not canonical";
        } else {
            vb = judge(TO_I2, rx, rx, 0, res_of(state_of_default(back)), false, nullptr, e);
        }
        put(TO_I2, vb);
    }
    // To and from the two-limb round-up type, and the one-limb one.
    {
        const u2::Interval w = u4::to_upward2(x);
        double p[4];
        w.to_limbs(p);
        I4 ws{{{p[0], p[2], 0, 0}}, {{p[1], p[3], 0, 0}}};
        if (rx.empty) ws = I4{{{kNaN, kNaN, kNaN, kNaN}}, {{kNaN, kNaN, kNaN, kNaN}}};
        put(TO_U2, judge(TO_U2, rx, rx, 0, res_of(ws), true, &ws, e));
        const u4::Interval b = u4::from_upward2(w);
        const I4 bs = state(b);
        Verdict vf = judge(FROM_U2, res_of(ws), rx, 0, res_of(bs), true, &bs, e);
        if (!rx.empty && !same_values(bs, ws)) {
            vf.ok = false;
            vf.why += "from_upward2 is not exact; ";
        }
        put(FROM_U2, vf);
        const U1 o = u4::to_upward1(x);
        double q[2];
        o.to_limbs(q);
        I4 os{{{q[0], 0, 0, 0}}, {{q[1], 0, 0, 0}}};
        if (rx.empty) os = I4{{{kNaN, kNaN, kNaN, kNaN}}, {{kNaN, kNaN, kNaN, kNaN}}};
        put(TO_U1, judge(TO_U1, rx, rx, 0, res_of(os), true, &os, e));
        const I4 fs = state(u4::from_upward1(o));
        Verdict vo = judge(FROM_U1, res_of(os), rx, 0, res_of(fs), true, &fs, e);
        if (!rx.empty && !same_values(fs, os)) {
            vo.ok = false;
            vo.why += "from_upward1 is not exact; ";
        }
        put(FROM_U1, vo);
    }
    // The bounds as numbers (tight: the greatest number <= lo, the least >= hi), the predicates, the
    // width (>= hi - lo, and its excess in units of its last place), for x of the type.
    {
        Verdict v;
        if (!rx.empty) {
            auto tight = [&](double b, const XV& bound, bool upper) {
                if (bound.inf) return b == (bound.inf > 0 ? kInf : -kInf);
                e.clear();
                add_q(e, bound.q);
                e.sub(b);
                const int s = e.sign();   // bound - b
                if (upper ? s > 0 : s < 0) return false;
                const double nb = std::nextafter(b, upper ? -kInf : kInf);
                e.clear();
                add_q(e, bound.q);
                e.sub(nb);
                const int s2 = e.sign();
                return upper ? s2 > 0 : s2 < 0;   // the next number inward is on the wrong side
            };
            if (!tight(x.lower(), rx.lo, false)) v.why += "lower() is not the greatest number below the lower bound; ";
            if (!tight(x.upper(), rx.hi, true)) v.why += "upper() is not the least number above the upper bound; ";
            const int sl = sgn(rx.lo), sh = sgn(rx.hi);
            if (x.certainly_positive() != (sl > 0)) v.why += "certainly_positive; ";
            if (x.certainly_negative() != (sh < 0)) v.why += "certainly_negative; ";
            if (x.contains_zero() != (sl <= 0 && sh >= 0)) v.why += "contains_zero; ";
            double w, r;
            {
                kairn::upward::Scope scope;
                w = u4::width(x);
                r = u4::radius(x);
            }
            if (rx.lo.inf || rx.hi.inf) {
                if (w != kInf || r != kInf) v.why += "width or radius of an unbounded interval not +inf; ";
            } else {
                e.clear();
                add_q(e, rx.hi.q);
                add_q(e, rx.lo.q, true);
                Exact half = e;
                half.mul(0.5);
                const double ruw = x2test::ru(e), rur = x2test::ru(half);
                if (!(w >= ruw)) v.why += "width below the exact width; ";
                if (!(r >= rur)) v.why += "radius below the exact radius; ";
                if (w > std::nextafter(ruw, kInf)) v.why += "width more than one number above RU(width); ";
            }
        } else if (x.certainly_positive() || x.certainly_negative() || x.contains_zero()) {
            v.why += "a predicate true of the empty set; ";
        }
        if (!v.why.empty()) v.ok = false;
        put(BOUNDS, v);
    }
}

long g_dump = 0;

// The calls of the cold paths so far on this thread (every cause), to count the results that took one.
long cold_calls() {
#if KAIRN_UPWARD4_COUNT
    return d4::cold_count[0] + d4::cold_count[1] + d4::cold_count[2];
#else
    return 0;
#endif
}

// The exact paths (the accumulator of the cold paths) against the best upper quadruple of the exact
// value (x2test::upper4): the sum and the product of two quadruples, one lane. "equal": the same limbs;
// "above": an upper bound above the best one (allowed: the parts of terms below 2^-1080 are rounded up
// term by term); "below" or not an upper bound: a bug.
struct ExactStat {
    long n = 0, equal = 0, above = 0, bad = 0;
    std::string first_bad;
};
void check_exact_paths(const I4& sx, const I4& sy, ExactStat& es, Exact& e) {
    if (is_empty_state(sx) || is_empty_state(sy)) return;
    for (int lane = 0; lane < 2; ++lane) {
        const Q4& a = lane ? sx.n : sx.u;
        const Q4& b = lane ? sy.n : sy.u;
        if (std::fabs(a.a[0]) == kInf || std::fabs(b.a[0]) == kInf) continue;
        for (int op = 0; op < 2; ++op) {
            d4::Q qa, qb, z;
            std::memcpy(qa.a, a.a, sizeof qa.a);
            std::memcpy(qb.a, b.a, sizeof qb.a);
            e.clear();
            if (op == 0) {
                {
                    kairn::upward::Scope scope;
                    z = d4::ssum(qa, qb);
                }
                add_q(e, a);
                add_q(e, b);
            } else {
                if (!(std::fabs(a.a[0] * b.a[0]) < kMax)) continue;
                {
                    kairn::upward::Scope scope;
                    z = d4::sprod(qa, qb);
                }
                for (int i = 0; i < 4; ++i)
                    for (int j = 0; j < 4; ++j) e.add_product(a.a[i], b.a[j]);
            }
            Q4 best;
            x2test::upper4(e, best.a);
            ++es.n;
            Q4 zz;
            std::memcpy(zz.a, z.a, sizeof zz.a);
            if (zz.a[0] == kInf) {   // an upper bound of anything: the best one where the sum overflows
                (best.a[0] == kInf ? es.equal : es.above)++;
                continue;
            }
            Exact d = e;   // z - exact >= 0
            add_q(d, zz, true);
            const int up = -d.sign();
            bool same = true;
            for (int i = 0; i < 4; ++i) same = same && zz.a[i] == best.a[i];
            Exact db;
            add_q(db, zz);
            add_q(db, best, true);
            if (up < 0 || db.sign() < 0 || !normalized_q(zz)) {
                ++es.bad;
                if (es.first_bad.empty()) {
                    char b2[600];
                    std::snprintf(b2, sizeof b2, "%s of (%a %a %a %a) (%a %a %a %a): (%a %a %a %a), best (%a %a %a %a)", op ? "product" : "sum",
                                  a.a[0], a.a[1], a.a[2], a.a[3], b.a[0], b.a[1], b.a[2], b.a[3], zz.a[0], zz.a[1], zz.a[2], zz.a[3],
                                  best.a[0], best.a[1], best.a[2], best.a[3]);
                    es.first_bad = b2;
                }
            } else if (same) {
                ++es.equal;
            } else {
                ++es.above;
            }
        }
    }
}

// One class: n cases of operands from make, every operation.
void run_class(const char* cls, long n, std::uint64_t seed, const std::function<void(Rng&, I4&, I4&, double&)>& make_ops,
               const std::vector<Op>& ops, bool chained) {
    Rng g{seed};
    Exact e;
    std::vector<Stat> mine(N_OPS);
    ExactStat es;
    std::vector<u4::Interval> cx, cy;
#if KAIRN_UPWARD4_COUNT
    for (long& c : d4::cold_count) c = 0;
#endif
    long ops_run = 0;
    for (long i = 0; i < n; ++i) {
        I4 sx, sy;
        double t = 0;
        make_ops(g, sx, sy, t);
        u4::Interval x = of_state(sx), y = of_state(sy);
        if (chained) {
            const I4 sw = interval4(g, g.range(0, 4), -30, 30, g.range(20, 200), g.range(0, 4));
            const u4::Interval w = of_state(sw);
            const int k = g.range(0, 3);
            x = k == 0 ? apply(ADD, x, w, 0) : k == 1 ? apply(MUL_BRANCH, x, w, 0) : k == 2 ? apply(SUB, x, w, 0) : apply(SQR, x, w, 0);
            y = g.range(0, 1) ? apply(MUL_BRANCH, y, x, 0) : apply(ADD, y, x, 0);
            sx = state(x);
            sy = state(y);
        }
        const Res rx = res_of(sx), ry = res_of(sy);
        if (!canonical(sx) || !canonical(sy)) {
            std::lock_guard<std::mutex> lock(out_mutex);
            std::printf("  OPERAND NOT CANONICAL %s: %s / %s\n", cls, hex(sx).c_str(), hex(sy).c_str());
            failures += 1;
            continue;
        }
        if ((i & 3) == 0) check_members(x, sx, mine.data(), e, cls);
        if ((i & 15) == 0) check_exact_paths(sx, sy, es, e);
        cx.push_back(x);
        cy.push_back(y);
        for (Op op : ops) {
            if (!op_available(op) || op >= CONV_I2) continue;
            const long cold_before = cold_calls();
            const u4::Interval z = apply(op, x, y, t);
            if (cold_calls() != cold_before) ++mine[op].cold;
            ++ops_run;
            const I4 zs = state(z);
            const Verdict v = judge(op, rx, ry, t, res_of(zs), true, &zs, e);
            if (!v.ok || !v.normalized) {
                std::lock_guard<std::mutex> lock(out_mutex);
                if (mine[op].bad + mine[op].unnormalized < 3)
                    std::printf("  INVALID %s %s: x=%s y=%s t=%a z=%s: %s\n", kOpName[op], cls, hex(sx).c_str(), hex(sy).c_str(), t,
                                hex(zs).c_str(), v.why.c_str());
            }
            mine[op].add(v, kOpName[op]);
            const double w = worst_of(v);
            if (w > mine[op].worst) {
                mine[op].worst = w;
                char tb[48];
                std::snprintf(tb, sizeof tb, " t=%a", t);
                mine[op].worst_case = "x=" + hex(sx) + " y=" + hex(sy) + tb + " z=" + hex(zs);
            }
        }
        if (cx.size() == 256 || i == n - 1) {
            for (Op op : {ARR_ADD, ARR_SUB, ARR_MUL}) {
                std::vector<u4::Interval> cz;
                const long cold_before = cold_calls();
                apply_arrays(op, cx, cy, cz);
                mine[op].cold += cold_calls() - cold_before;   // the elements that took a cold path
                for (std::size_t k = 0; k < cz.size(); ++k) {
                    const I4 zs = state(cz[k]);
                    const Verdict v = judge(judged(op), res_of(state(cx[k])), res_of(state(cy[k])), 0, res_of(zs), true, &zs, e);
                    if (!v.ok || !v.normalized) {
                        std::lock_guard<std::mutex> lock(out_mutex);
                        if (mine[op].bad + mine[op].unnormalized < 3)
                            std::printf("  INVALID %s %s: x=%s y=%s z=%s: %s\n", kOpName[op], cls, hex(state(cx[k])).c_str(),
                                        hex(state(cy[k])).c_str(), hex(zs).c_str(), v.why.c_str());
                    }
                    mine[op].add(v, kOpName[op]);
                }
            }
            cx.clear();
            cy.clear();
        }
    }
    std::lock_guard<std::mutex> lock(out_mutex);
    for (int o = 0; o < N_OPS; ++o) {
        const Op op = Op(o);
        if (!op_available(op)) continue;
        Stat& s = mine[op];
        if (s.n == 0) continue;
        const long over = long(std::count_if(s.rel.begin(), s.rel.end(), [](float r) { return r > 1000.f; }));
        std::printf("%-11s %-44s n=%ld invalid=%ld unnormalized=%ld exact_bounds=%ld median=%.3g p99=%.3g max=%.3g (u^4) above_1000=%ld zero_ref=%ld "
                    "cold=%ld (%.3g%%)\n",
                    kOpName[op], cls, s.n, s.bad, s.unnormalized, s.exact, s.q(0.5), s.q(0.99), s.mx(), over, s.zero_ref, s.cold,
                    100.0 * double(s.cold) / double(s.n));
        if (!s.first_bad.empty()) std::printf("  first: %s\n", s.first_bad.c_str());
        if (s.worst > 1e4 && op < CONV_I2) std::printf("  largest (%.3g u^4): %s\n", s.worst, s.worst_case.c_str());
        if (s.bad || s.unnormalized) failures += 1;
    }
#if KAIRN_UPWARD4_COUNT
    std::printf("cold paths %-44s per %ld operations (and the members' widths): sum %ld, product %ld, with a number or square %ld\n", cls,
                ops_run, d4::cold_count[0], d4::cold_count[1], d4::cold_count[2]);
#endif
    std::printf("exact paths %-44s n=%ld equal to the best quadruple %ld, above it %ld, wrong %ld\n", cls, es.n, es.equal, es.above, es.bad);
    if (!es.first_bad.empty()) std::printf("  first wrong: %s\n", es.first_bad.c_str());
    if (es.bad) failures += 1;
    std::fflush(stdout);
}

// --- Special values ----------------------------------------------------------------------------------

void run_special() {
    const double om = kMax, eta = std::numeric_limits<double>::denorm_min(), mn = std::numeric_limits<double>::min();
    // The two-limb experiment's list (as default intervals (l0, l1, h0, h1)), converted by from_interval,
    // and quadruples of four limbs.
    struct DI {
        double l0, l1, h0, h1;
    };
    const std::vector<DI> v2 = {
        {kInf, 0, -kInf, 0}, {-kInf, 0, kInf, 0}, {-kInf, 0, -3, 0x1p-55}, {-kInf, 0, 0, 0}, {-kInf, 0, 5, 0}, {-kInf, 0, -om, 0},
        {2, -0x1p-54, kInf, 0}, {0, 0, kInf, 0}, {-7, 0, kInf, 0}, {om, 0, kInf, 0}, {0, 0, 0, 0}, {-1, 0, 0, 0}, {0, 0, 1, 0x1p-53},
        {1, 0, 1, 0}, {-3, 0x1p-52, 2, -0x1p-53}, {om, 0, om, 0}, {-om, 0, -om, 0}, {0x1p1023, 0, om, 0}, {-om, 0, om, 0},
        {om, -0x1p969, om, 0}, {0x1.8p1023, 0x1p969, 0x1.8p1023, 0x1p969}, {0x1p600, 0x1p546, 0x1p601, 0},
        {-0x1p601, 0, -0x1p600, -0x1p546}, {0x1p-600, 0, 0x1p-599, 0x1p-653}, {eta, 0, eta, 0}, {-eta, 0, eta, 0},
        {mn, 0, mn + eta, 0}, {-(mn + eta), 0, 4 * eta, 0}, {0x1p-1000, 0x1p-1060, 0x1p-999, 0}, {1 + 0x1p-52, 0x1p-106, 1 + 0x1p-51, 0},
        {-2, 0, -2, 0}, {0.5, 0, 3, 0}};
    std::vector<u4::Interval> v;
    for (const DI& d : v2) {
        const I2 k = I2::from_limbs(&d.l0);
        kairn::upward::Scope scope;
        v.push_back(u4::from_interval(k));
    }
    // Four-limb ones: full quadruples, near-full tails (carries), a tail of subnormal limbs, near MAX.
    const Q4 one4{{1.0, -0x1.fffffffffffffp-54, -0x1.fffffffffffffp-107, -0x1.fffffffffffffp-160}};
    const Q4 m4{{-1.0, -0x1.8p-53, -0x1p-106, 0}};
    const Q4 t4{{0x1p-1000, -0x1.8p-1054, 0, 0}};
    const Q4 h4{{0x1.ffffffffffffep1023, -0x1p970, -0x1p916, -0x1p862}};
    auto neg_up = [](const Q4& q) { return up4([&] { Exact e = val(q); e.mul(-1.0); return e; }()); };
    v.push_back(of_state(I4{one4, neg_up(one4)}));
    v.push_back(of_state(I4{one4, one4}));   // [-1 + tail, 1 - tail]
    v.push_back(of_state(I4{neg_up(m4), m4}));
    v.push_back(of_state(I4{t4, neg_up(t4)}));
    v.push_back(of_state(I4{h4, h4}));
    v.push_back(of_state(I4{Q4{{kInf, 0, 0, 0}}, h4}));
    const double ts[] = {0.0, -0.0, 1.0, -2.5, 0x1p-1074, 0x1p1000, -0x1p1000, om, kInf, -kInf, kNaN};
    Exact e;
    long pairs = 0, bad = 0, unnorm = 0, same = 0, differ = 0;
    std::vector<std::string> diffs;
    auto record = [&](const char* name, const std::string& operands, const Verdict& vz) {
        ++pairs;
        if (!vz.ok) ++bad;
        if (!vz.normalized) ++unnorm;
        if (!vz.ok || !vz.normalized) std::printf("  SPECIAL INVALID %s %s: %s\n", name, operands.c_str(), vz.why.c_str());
    };
    // Against the two-limb type on the same operands (its answers follow Interval<double, 2>'s): the
    // structure (empty, which bounds are infinite) must be the same; the finite bounds are not compared.
    auto structure = [](const I4& s) {
        if (is_empty_state(s)) return std::string("empty");
        return std::string(s.n.a[0] == kInf ? "-inf" : "fin") + "," + (s.u.a[0] == kInf ? "+inf" : "fin");
    };
    auto compare2 = [&](const char* name, const std::string& operands, const I4& zs, const u2::Interval& w) {
        double p[4];
        w.to_limbs(p);
        const I4 ws{{{p[0], p[2], 0, 0}}, {{p[1], p[3], 0, 0}}};
        if (structure(zs) == structure(ws)) ++same;
        else {
            ++differ;
            diffs.push_back(std::string(name) + " " + operands + ": four limbs " + structure(zs) + ", two limbs " + structure(ws));
        }
    };
    const std::vector<Op> binary = {ADD, ADD_SLOPPY, SUB, MUL_BRANCH, MUL_TABLE, MUL_SEL2, MUL_SEL4};
    Stat dummy[N_OPS];
    for (std::size_t i = 0; i < v.size(); ++i) {
        const u4::Interval& x = v[i];
        const I4 sx = state(x);
        const Res rx = res_of(sx);
        const std::string hx = hex(sx);
        if (!canonical(sx)) {
            std::printf("  SPECIAL OPERAND NOT CANONICAL %s\n", hx.c_str());
            ++bad;
        }
        check_members(x, sx, dummy, e, "special");
        const u2::Interval x2 = u4::to_upward2(x);
        for (Op op : {SQR, NEG}) {
            const u4::Interval z = apply(op, x, x, 0);
            const I4 zs = state(z);
            record(kOpName[op], hx, judge(op, rx, rx, 0, res_of(zs), true, &zs, e));
            kairn::upward::Scope scope;
            compare2(kOpName[op], hx, zs, op == SQR ? u2::sqr(x2) : -x2);
        }
        for (double t : ts) {
            for (Op op : {ADD_NUM, MUL_NUM}) {
                const u4::Interval z = apply(op, x, x, t);
                const I4 zs = state(z);
                char tb[48];
                std::snprintf(tb, sizeof tb, " t=%a", t);
                record(kOpName[op], hx + tb, judge(op, rx, rx, t, res_of(zs), true, &zs, e));
                kairn::upward::Scope scope;
                compare2(kOpName[op], hx + tb, zs, op == ADD_NUM ? x2 + t : x2 * t);
            }
        }
        for (std::size_t j = 0; j < v.size(); ++j) {
            const u4::Interval& y = v[j];
            const I4 sy = state(y);
            const Res ry = res_of(sy);
            const u2::Interval y2 = u4::to_upward2(y);
            for (Op op : binary) {
                if (!op_available(op)) continue;
                const u4::Interval z = apply(op, x, y, 0);
                const I4 zs = state(z);
                record(kOpName[op], "x=" + hx + " y=" + hex(sy), judge(op, rx, ry, 0, res_of(zs), true, &zs, e));
                kairn::upward::Scope scope;
                compare2(kOpName[op], "x=" + hx + " y=" + hex(sy), zs, op <= ADD_SLOPPY ? x2 + y2 : op == SUB ? x2 - y2 : x2 * y2);
            }
        }
    }
    for (int o = 0; o < N_OPS; ++o)
        if (dummy[o].bad || dummy[o].unnormalized) {
            std::printf("  SPECIAL MEMBER INVALID %s: %s\n", kOpName[o], dummy[o].first_bad.c_str());
            ++bad;
        }
    {   // Every pair through the functions on arrays, in one call each.
        std::vector<u4::Interval> ax, ay, az;
        for (const auto& a : v)
            for (const auto& b : v) {
                ax.push_back(a);
                ay.push_back(b);
            }
        for (Op op : {ARR_ADD, ARR_SUB, ARR_MUL}) {
            apply_arrays(op, ax, ay, az);
            for (std::size_t k = 0; k < az.size(); ++k) {
                const I4 zs = state(az[k]);
                record(kOpName[op], hex(state(ax[k])) + " " + hex(state(ay[k])),
                       judge(judged(op), res_of(state(ax[k])), res_of(state(ay[k])), 0, res_of(zs), true, &zs, e));
            }
        }
    }
    std::printf("special values: %zu intervals, %ld cases, invalid=%ld, unnormalized=%ld; against the two-limb type: same structure %ld, "
                "different %ld (listed)\n",
                v.size(), pairs, bad, unnorm, same, differ);
    std::sort(diffs.begin(), diffs.end());
    for (const std::string& d : diffs) std::printf("  STRUCTURE %s\n", d.c_str());
    if (bad || unnorm) failures += 1;
}

}  // namespace

int main(int argc, char** argv) {
    const long n = argc > 1 ? std::atol(argv[1]) : 2000000;
    const std::uint64_t seed = argc > 2 ? std::strtoull(argv[2], nullptr, 0) : 20261127u;
    const int threads = argc > 3 ? std::atoi(argv[3]) : 8;
    g_dump = argc > 4 ? std::atol(argv[4]) : 0;
    std::printf("x4-check: n=%ld per class, seed=%llu, threads=%d, form %d (1 SSE, 2 NEON, 3 numbers), AVX2 %d, sum %d (1 accurate, 2 sloppy), "
                "KAIRN_CHECKS %d, flags: %s\n",
                n, static_cast<unsigned long long>(seed), threads, KAIRN_UPWARD2_FORM, KAIRN_UPWARD2_AVX2, KAIRN_UPWARD4_SUM, KAIRN_CHECKS,
#ifdef X4_FLAGS
                X4_FLAGS
#else
                "?"
#endif
    );
    std::vector<Op> all = {ADD, ADD_SLOPPY, SUB, MUL_BRANCH, MUL_TABLE, MUL_SEL2, MUL_SEL4, SQR, ADD_NUM, MUL_NUM, NEG};
    if (const char* only = std::getenv("X4_OPS")) {   // a comma-separated list of operations, for debugging
        std::vector<Op> keep;
        for (Op op : all)
            if (std::strstr(only, kOpName[op])) keep.push_back(op);
        all = keep;
    }
    auto mix = [](Rng& g, int kmin, int kmax) { return interval4(g, g.range(0, 4), kmin, kmax, g.range(20, 200), g.range(0, 4)); };
    auto num = [](Rng& g, int kmin, int kmax) {
        const int k = g.range(0, 9);
        if (k == 0) return 0.0;
        if (k == 1) return std::ldexp(1.0, g.range(kmin, kmax));
        return number4(g, kmin, kmax, 0).a[0];
    };
    // The benchmark's operands: two-limb intervals of half-width 2^-80, converted exactly.
    auto bench_like = [](Rng& g) {
        const Q4 c = number4(g, -8, 8, 0);
        Exact cv;
        cv.add(c.a[0]);
        cv.add(c.a[1]);
        const double w = std::fabs(c.a[0]) * std::ldexp(0.5 + 0.5 * g.unit(), -80);
        Exact lo = cv, hi = cv;
        lo.sub(w);
        hi.add(w);
        return make(lo, hi);
    };
    struct Cls {
        const char* name;
        std::function<void(Rng&, I4&, I4&, double&)> make;
        bool chained;
    };
    const std::vector<Cls> classes = {
        {"as the benchmark (two limbs, 2^-80, 2^+-8)", [&](Rng& g, I4& x, I4& y, double& t) {
             x = bench_like(g);
             y = bench_like(g);
             t = num(g, -8, 8);
         }, false},
        {"points, 2^+-60", [&](Rng& g, I4& x, I4& y, double& t) {
             x = interval4(g, 3, -60, 60, 0, 0);
             y = interval4(g, 3, -60, 60, 0, 0);
             t = num(g, -60, 60);
         }, false},
        {"narrow 2^-20..2^-200, 2^+-60", [&](Rng& g, I4& x, I4& y, double& t) {
             x = interval4(g, 0, -60, 60, g.range(20, 200), 0);
             y = interval4(g, 0, -60, 60, g.range(20, 200), 0);
             t = num(g, -60, 60);
         }, false},
        {"wide (unrelated bounds), 2^+-60", [&](Rng& g, I4& x, I4& y, double& t) {
             x = interval4(g, 1, -60, 60, 0, 0);
             y = interval4(g, 1, -60, 60, 0, 0);
             t = num(g, -60, 60);
         }, false},
        {"around zero, 2^+-60", [&](Rng& g, I4& x, I4& y, double& t) {
             x = interval4(g, 2, -60, 60, 0, 0);
             y = g.range(0, 1) ? interval4(g, 2, -60, 60, 0, 0) : mix(g, -60, 60);
             t = num(g, -60, 60);
         }, false},
        {"zeros (a bound 0, [0, 0])", [&](Rng& g, I4& x, I4& y, double& t) {
             x = interval4(g, g.range(4, 5), -60, 60, 0, 0);
             y = g.range(0, 1) ? interval4(g, g.range(4, 5), -60, 60, 0, 0) : mix(g, -60, 60);
             t = num(g, -60, 60);
         }, false},
        {"any kind, 2^+-500", [&](Rng& g, I4& x, I4& y, double& t) {
             x = mix(g, -500, 500);
             y = mix(g, -500, 500);
             t = num(g, -500, 500);
         }, false},
        {"tiny (later limbs underflow), 2^-1074..2^-800", [&](Rng& g, I4& x, I4& y, double& t) {
             x = mix(g, -1074, -800);
             y = g.range(0, 1) ? mix(g, -1074, -800) : mix(g, -200, 200);
             t = num(g, -600, 0);
         }, false},
        {"huge (near overflow), 2^900..2^1023", [&](Rng& g, I4& x, I4& y, double& t) {
             x = mix(g, 900, 1023);
             y = g.range(0, 1) ? mix(g, 900, 1023) : mix(g, -200, 200);
             t = num(g, 0, 600);
         }, false},
        {"cancellation (y near -x, 30..210 bits)", [&](Rng& g, I4& x, I4& y, double& t) {
             x = mix(g, -8, 8);
             // y: -x moved by a relative 2^-j, its bounds made from x's exactly.
             const Res r = res_of(x);
             const int j = g.range(30, 210);
             Exact lo, hi;
             add_q(lo, r.hi.q, true);   // -hi
             add_q(hi, r.lo.q, true);   // -lo
             const double d = g.range(0, 3) == 0 ? 0.0 : (g.unit() - 0.5) * std::ldexp(std::fabs(x.u.a[0]) + std::fabs(x.n.a[0]), -j);
             lo.add(d);
             hi.add(d);
             hi.add(std::fabs(d) * g.unit());
             y = make(lo, hi);
             t = -x.u.a[0];
         }, false},
        {"limbs with gaps (a later limb far below), 2^+-60", [&](Rng& g, I4& x, I4& y, double& t) {
             x = interval4(g, g.range(0, 3), -60, 60, g.range(20, 200), g.range(1, 4));
             y = interval4(g, g.range(0, 3), -60, 60, g.range(20, 200), g.range(1, 4));
             t = num(g, -60, 60);
         }, false},
        {"magnitudes apart (y up to 2^-300 of x)", [&](Rng& g, I4& x, I4& y, double& t) {
             const int k = g.range(-30, 30), d = g.range(0, 300);
             x = interval4(g, g.range(0, 3), k, k, g.range(20, 200), g.range(0, 4));
             y = interval4(g, g.range(0, 3), k - d, k - d, g.range(20, 200), g.range(0, 4));
             if (g.next() & 1) std::swap(x, y);
             t = std::ldexp(1.0 + g.unit(), k - d) * ((g.next() & 1) ? 1 : -1);
         }, false},
        {"results of earlier operations", [&](Rng& g, I4& x, I4& y, double& t) {
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
