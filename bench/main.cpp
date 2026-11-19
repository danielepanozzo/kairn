// The benchmark driver (bench/README.md):
//
//   kairn-bench-O2 [--json FILE] [--machine TEXT] [--commit TEXT] [--date TEXT] [--cpu N]
//                  [--reps R] [--sample-ms MS] [--filter TEXT] [--check-only] [--list]
//
// 1. Makes the inputs: normalized 2-limb numbers of moderate magnitude, balls with small radii,
//    factors near 1, at run time from a fixed seed.
// 2. Checks every timed function against the generated kernel on those inputs: bit for bit for
//    the props and the packed code, within a tolerance for MPFR. It refuses to time anything if
//    one check fails.
// 3. Checks forms (a) and (b) of the full kernels against each other, and form (a) of packed code
//    against scalar code, on random and special operands (infinities, NaN, overflow).
// 4. Times every function: calibrates a sample of about --sample-ms, then takes --reps samples of
//    each, in rounds over all functions so that a disturbance spreads over all of them, and
//    reports the minimum, median and maximum time per operation.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <limits>
#include <map>
#include <new>
#include <string>
#include <vector>

#include <kairn/gen/scalar.hpp>

#include "bench.hpp"

#if defined(_WIN32)
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <intrin.h>
#elif defined(__APPLE__)
#include <pthread.h>
#include <sys/sysctl.h>
#elif defined(__linux__)
#include <sched.h>
#endif
#if (defined(__x86_64__) || defined(__i386__)) && !defined(_WIN32)
#include <cpuid.h>
#endif

#ifndef KAIRN_BENCH_FLAGS
#define KAIRN_BENCH_FLAGS "unknown"
#endif

namespace kb = kairn_bench;

namespace {

// --- Small tools --------------------------------------------------------------------------------

std::uint64_t bits(double a) {
    std::uint64_t b;
    std::memcpy(&b, &a, sizeof b);
    return b;
}
double from_bits(std::uint64_t b) {
    double a;
    std::memcpy(&a, &b, sizeof a);
    return a;
}

struct Rng {
    std::uint64_t s;
    std::uint64_t next() {   // splitmix64
        std::uint64_t z = (s += 0x9e3779b97f4a7c15u);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9u;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebu;
        return z ^ (z >> 31);
    }
    double u01() { return double(next() >> 11) * 0x1p-53; }   // [0, 1)
    double sym() { return 2.0 * u01() - 1.0; }                 // [-1, 1)
    int range(int lo, int hi) { return lo + int(next() % std::uint64_t(hi - lo + 1)); }
    double sign() { return (next() & 1) ? -1.0 : 1.0; }
};

// 64-byte aligned arrays, so that packed loads do not split cache lines.
struct Buf {
    double* p = nullptr;
    int n = 0;
    explicit Buf(int count = 0) { resize(count); }
    Buf(const Buf&) = delete;
    Buf& operator=(const Buf&) = delete;
    ~Buf() { ::operator delete[](p, std::align_val_t(64)); }
    void resize(int count) {
        ::operator delete[](p, std::align_val_t(64));
        n = count;
        p = static_cast<double*>(::operator new[](sizeof(double) * std::size_t(count < 8 ? 8 : count), std::align_val_t(64)));
        std::fill(p, p + (count < 8 ? 8 : count), 0.0);
    }
    double& operator[](int i) { return p[i]; }
};

// --- The machine and the build ------------------------------------------------------------------

std::string cpu_brand() {
#if defined(__APPLE__)
    char buf[256];
    std::size_t len = sizeof buf;
    if (sysctlbyname("machdep.cpu.brand_string", buf, &len, nullptr, 0) == 0) return std::string(buf);
    return "unknown";
#elif defined(_WIN32) || defined(__x86_64__) || defined(__i386__)
    unsigned int r[12] = {0};
    for (unsigned int k = 0; k < 3; ++k) {
#if defined(_WIN32)
        int q[4];
        __cpuid(q, int(0x80000002u + k));
        std::memcpy(r + 4 * k, q, sizeof q);
#else
        __get_cpuid(0x80000002u + k, &r[4 * k], &r[4 * k + 1], &r[4 * k + 2], &r[4 * k + 3]);
#endif
    }
    std::string s(reinterpret_cast<const char*>(r), sizeof r);
    s = s.c_str();
    while (!s.empty() && s.back() == ' ') s.pop_back();
    while (!s.empty() && s.front() == ' ') s.erase(s.begin());
    return s;
#else
    return "unknown";
#endif
}

std::string compiler() {
#if defined(__clang__) && defined(__apple_build_version__)
    return std::string("Apple clang ") + __clang_version__;
#elif defined(__clang__)
    return std::string("Clang ") + __clang_version__;
#elif defined(__GNUC__)
    return std::string("GCC ") + __VERSION__;
#elif defined(_MSC_VER)
    return "MSVC " + std::to_string(_MSC_FULL_VER / 10000000) + "." + std::to_string((_MSC_FULL_VER / 100000) % 100) +
           "." + std::to_string(_MSC_FULL_VER % 100000);
#else
    return "unknown";
#endif
}

std::string os_name() {
#if defined(_WIN32)
    return "Windows";
#elif defined(__APPLE__)
    return "macOS";
#elif defined(__linux__)
    return "Linux";
#else
    return "unknown";
#endif
}

std::string arch() {
#if defined(__x86_64__) || defined(_M_X64)
    return "x86-64";
#elif defined(__aarch64__) || defined(_M_ARM64)
    return "arm64";
#else
    return "unknown";
#endif
}

// Pins the thread to logical CPU cpu (Linux, Windows). macOS has no affinity: the thread asks for
// the user-interactive class, which the scheduler runs on performance cores.
std::string pin(int cpu) {
#if defined(__APPLE__)
    (void)cpu;
    return pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0) == 0 ? "not pinned (no affinity on macOS); QoS user-interactive"
                                                                              : "not pinned";
#elif defined(__linux__)
    if (cpu < 0) return "not pinned";
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    return sched_setaffinity(0, sizeof set, &set) == 0 ? "pinned to one logical CPU" : "pinning FAILED";
#elif defined(_WIN32)
    if (cpu < 0) return "not pinned";
    return SetThreadAffinityMask(GetCurrentThread(), DWORD_PTR(1) << cpu) != 0 ? "pinned to one logical CPU" : "pinning FAILED";
#else
    (void)cpu;
    return "not pinned";
#endif
}

// --- Inputs -------------------------------------------------------------------------------------

constexpr int kN = 256;   // elements per array: 9 arrays of 2 KB fit in any L1 here

// A normalized pair (h, l) with |h| in [2^kmin, 2^(kmax+1)) and |l| about 2^-53 |h|, renormalized
// by fast_two_sum so that h = RN(h + l) holds exactly.
void two_limb(Rng& r, int kmin, int kmax, double& h, double& l) {
    // One draw per statement: the order of evaluation inside an expression is unspecified, and
    // every compiler must see the same inputs.
    const double s = r.sign();
    const double m = 1.0 + r.u01();
    const double a = s * std::ldexp(m, r.range(kmin, kmax));
    const double b = a * r.sym() * 0x1p-53;
    kairn::gen::fast_two_sum(a, b, h, l);
}

struct Data {
    Buf x0{kN}, x1{kN}, xr{kN}, y0{kN}, y1{kN}, yr{kN};
    Buf f0{kN}, f1{kN}, fr{kN}, c0{kN}, c1{kN}, cr{kN};
    Buf z0{kN}, z1{kN}, zr{kN};
    Buf out0{16}, out1{16}, outr{16};
    double h0 = 0, h1 = 0, hr = 0;
    kb::ChainArgs sum{}, prod{}, horner{};

    explicit Data(std::uint64_t seed) {
        Rng r{seed};
        for (int i = 0; i < kN; ++i) {
            two_limb(r, -8, 8, x0[i], x1[i]);
            two_limb(r, -8, 8, y0[i], y1[i]);
            xr[i] = std::fabs(x0[i]) * 0x1p-80 * (0.5 + 0.5 * r.u01());
            yr[i] = std::fabs(y0[i]) * 0x1p-80 * (0.5 + 0.5 * r.u01());
            const double f = std::exp2(0.25 * r.sym());   // in [2^-1/4, 2^1/4): 256 of them stay in range
            kairn::gen::fast_two_sum(f, f * r.sym() * 0x1p-53, f0[i], f1[i]);
            fr[i] = f0[i] * 0x1p-80 * (0.5 + 0.5 * r.u01());
            two_limb(r, -2, 2, c0[i], c1[i]);
            cr[i] = std::fabs(c0[i]) * 0x1p-80 * (0.5 + 0.5 * r.u01());
        }
        const double h = 0.75 + 0.125 * r.u01();
        kairn::gen::fast_two_sum(h, h * r.sym() * 0x1p-53, h0, h1);
        hr = h0 * 0x1p-80;
        sum = chain(0.0);
        prod = chain(1.0);
        horner = chain(0.0);
    }
    kb::ChainArgs chain(double start) {
        kb::ChainArgs a{};
        a.n = kN;
        a.x0 = x0.p; a.x1 = x1.p; a.xr = xr.p;
        a.f0 = f0.p; a.f1 = f1.p; a.fr = fr.p;
        a.c0 = c0.p; a.c1 = c1.p; a.cr = cr.p;
        a.h0 = h0; a.h1 = h1; a.hr = hr;
        a.s0 = start; a.s1 = 0.0; a.sr = 0.0;
        a.out0 = out0.p; a.out1 = out1.p; a.outr = outr.p;
        return a;
    }
    const kb::ChainArgs& args_for(const std::string& kind) const {
        return kind == "sum" ? sum : kind == "prod" ? prod : horner;
    }
};

// --- The entries --------------------------------------------------------------------------------

struct Name {
    std::string backend, kind, kernel, variant;
};
Name split(const std::string& s) {
    Name n;
    std::string* part[4] = {&n.backend, &n.kind, &n.kernel, &n.variant};
    int k = 0;
    for (char ch : s) {
        if (ch == '/' && k < 3)
            ++k;
        else
            part[k]->push_back(ch);
    }
    return n;
}

std::vector<const kb::Entry*> all_entries() {
    std::vector<const kb::Entry*> v;
    for (const kb::Entry* t : {kb::scalar_entries, kb::packed_entries, kb::mpfr_entries})
        for (const kb::Entry* e = t; e->name; ++e) v.push_back(e);
    return v;
}

const kb::Entry* find(const std::vector<const kb::Entry*>& v, const std::string& name) {
    for (const kb::Entry* e : v)
        if (name == e->name) return e;
    return nullptr;
}

void run_tp(const kb::Entry& e, Data& d, int n = kN) {
    kb::TpFn volatile f = e.tp;
    f(n, d.x0.p, d.x1.p, d.xr.p, d.y0.p, d.y1.p, d.yr.p, d.z0.p, d.z1.p, d.zr.p);
}

// --- Checks on the benchmark inputs -------------------------------------------------------------

const double kSentinel = from_bits(0x7ff4dead0000beefu);

void fill_outputs(Data& d) {
    for (Buf* b : {&d.z0, &d.z1, &d.zr, &d.out0, &d.out1, &d.outr})
        std::fill(b->p, b->p + b->n, kSentinel);
}

std::string hex(double a) {
    char buf[64];
    std::snprintf(buf, sizeof buf, "%a", a);
    return buf;
}

// Every output limb bit for bit, against the scalar generated kernel. A packed chain is compared
// lane by lane with the scalar chain run on that lane's elements.
bool check_bits(const kb::Entry& e, const kb::Entry& ref, Data& d, std::string& why) {
    const Name nm = split(e.name);
    if (e.tp) {
        fill_outputs(d);
        run_tp(ref, d);
        std::vector<double> r0(d.z0.p, d.z0.p + kN), r1(d.z1.p, d.z1.p + kN), rr(d.zr.p, d.zr.p + kN);
        fill_outputs(d);
        run_tp(e, d);
        for (int i = 0; i < kN; ++i) {
            const double got[3] = {d.z0[i], d.z1[i], d.zr[i]}, want[3] = {r0[i], r1[i], rr[i]};
            for (int k = 0; k < 3; ++k)
                if (bits(got[k]) != bits(want[k])) {
                    why = "element " + std::to_string(i) + " limb " + std::to_string(k) + ": " + hex(got[k]) + " != " + hex(want[k]);
                    return false;
                }
        }
        return true;
    }
    const kb::ChainArgs& a = d.args_for(nm.kind);
    fill_outputs(d);
    e.chain(&a);
    const int w = e.lanes;
    std::vector<double> got0(d.out0.p, d.out0.p + w), got1(d.out1.p, d.out1.p + w), gotr(d.outr.p, d.outr.p + w);
    for (int j = 0; j < w; ++j) {
        // The elements j, j + w, ... of every stream, as one scalar chain.
        const int m = kN / w;
        std::vector<double> s[9];
        const double* src[9] = {a.x0, a.x1, a.xr, a.f0, a.f1, a.fr, a.c0, a.c1, a.cr};
        for (int k = 0; k < 9; ++k)
            for (int i = 0; i < m; ++i) s[k].push_back(src[k][i * w + j]);
        kb::ChainArgs b = a;
        b.n = m;
        b.x0 = s[0].data(); b.x1 = s[1].data(); b.xr = s[2].data();
        b.f0 = s[3].data(); b.f1 = s[4].data(); b.fr = s[5].data();
        b.c0 = s[6].data(); b.c1 = s[7].data(); b.cr = s[8].data();
        fill_outputs(d);
        ref.chain(&b);
        const double gl[3] = {got0[j], got1[j], gotr[j]}, wl[3] = {d.out0[0], d.out1[0], d.outr[0]};
        for (int k = 0; k < 3; ++k)
            if (bits(gl[k]) != bits(wl[k])) {
                why = "lane " + std::to_string(j) + " limb " + std::to_string(k) + ": " + hex(gl[k]) + " != " + hex(wl[k]);
                return false;
            }
    }
    return true;
}

// MPFR rounds the exact operation to 106 bits, Kairn to within a few units of 2^-104 (relative):
// the two agree to about 2^-100 for one operation, and to 2^-90 after a chain of 256.
bool check_mpfr(const kb::Entry& e, const kb::Entry& ref, Data& d, std::string& why) {
    const Name nm = split(e.name);
    auto close = [](double r0, double r1, double k0, double k1, double tol) {
        const double diff = (r0 - k0) + (r1 - k1);
        return std::fabs(diff) <= tol * std::fabs(k0);
    };
    if (e.tp) {
        fill_outputs(d);
        run_tp(ref, d);
        run_tp(e, d);
        for (int i = 0; i < kN; ++i) {
            double r0, r1;
            kb::mpfr_result(i, &r0, &r1);
            if (!close(r0, r1, d.z0[i], d.z1[i], 0x1p-100)) {
                why = "element " + std::to_string(i) + ": " + hex(r0) + " " + hex(r1) + " vs " + hex(d.z0[i]) + " " + hex(d.z1[i]);
                return false;
            }
        }
        return true;
    }
    const kb::ChainArgs& a = d.args_for(nm.kind);
    fill_outputs(d);
    ref.chain(&a);
    e.chain(&a);
    double r0, r1;
    kb::mpfr_result(-1, &r0, &r1);
    if (!close(r0, r1, d.out0[0], d.out1[0], 0x1p-90)) {
        why = "chain: " + hex(r0) + " " + hex(r1) + " vs " + hex(d.out0[0]) + " " + hex(d.out1[0]);
        return false;
    }
    return true;
}

// --- The forms of the full kernels on special operands ------------------------------------------

bool same(double a, double b) {   // the same bits, apart from NaN payloads and the sign of zeros
    if (a != a && b != b) return true;
    if (a == 0.0 && b == 0.0) return true;
    return bits(a) == bits(b);
}
bool finite(double a) { return std::fabs(a) < std::numeric_limits<double>::infinity(); }
bool normalized(double h, double l) { return finite(h) && finite(l) && h + l == h; }
bool canonical2(double h, double l) {
    return normalized(h, l) || (std::isinf(h) && l == 0.0) || (h != h && l != l);
}
bool canonical_ball(double c0, double c1, double r) {
    const bool finite_ball = normalized(c0, c1) && finite(r) && r >= 0.0;
    const bool line = c0 == 0.0 && c1 == 0.0 && r == std::numeric_limits<double>::infinity();
    const bool empty = c0 != c0 && c1 != c1 && r != r;
    return finite_ball || line || empty;
}
bool empty_ball(double c0, double c1, double r) { return c0 != c0 && c1 != c1 && r != r; }

struct FullCheck {
    std::string kernel;
    // variants_vs_a: the variants full_fabs and full_inl of the 2-limb kernels against form (a).
    int cases = 0, a_vs_b = 0, packed_vs_a = 0, variants_vs_a = 0, not_canonical = 0, spec = 0;
    int nonfinite_operand = 0, overflow = 0, finite_result = 0;
};

// Canonical 2-limb operands: special ones, then random ones over every binade, with large ones
// often enough that sums and products overflow.
struct Operand {
    double h, l, r;
};
std::vector<Operand> special_operands(bool ball) {
    const double inf = std::numeric_limits<double>::infinity(), nan = std::numeric_limits<double>::quiet_NaN();
    const double big = std::numeric_limits<double>::max();
    std::vector<Operand> c = {
        {0.0, 0.0, 0}, {-0.0, 0.0, 0}, {1.0, 0x1p-60, 0}, {-1.0, -0x1p-55, 0}, {3.0, -0x1p-52, 0},
        {big, 0x1p969, 0}, {-big, -0x1p969, 0}, {0x1p1023, 0x1p968, 0}, {-0x1p1023, 0x1p968, 0},
        {0x1.8p1023, -0x1p969, 0}, {0x1p1022, 0.0, 0}, {0x1p-1022, 0.0, 0}, {-0x1p-1074, 0.0, 0},
        {0x1p512, 0x1p458, 0}, {-0x1.fp511, 0.0, 0}};
    if (!ball) {
        for (double s : {1.0, -1.0}) {
            c.push_back({s * inf, 0.0, 0});
            c.push_back({s * inf, -0.0, 0});
        }
        c.push_back({nan, nan, 0});
        return c;
    }
    std::vector<Operand> b;
    for (const Operand& o : c)
        for (double r : {0.0, 0x1p-1074, std::fabs(o.h) * 0x1p-60, big}) b.push_back({o.h, o.l, r});
    b.push_back({0.0, 0.0, inf});   // the whole line
    b.push_back({nan, nan, nan});   // the empty set
    return b;
}
// large: the leading limb in [2^lo, 2^(hi+1)), near the threshold where the operation overflows.
Operand random_operand(Rng& r, bool ball, bool large, int lo, int hi) {
    double h;
    if (large) {
        const double s = r.sign();
        const double m = 1.0 + r.u01();
        h = s * std::ldexp(m, r.range(lo, hi));
    } else {
        const std::uint64_t e = std::uint64_t(r.range(0, 2046)), m = r.next() & 0xfffffffffffffu;
        h = from_bits((r.next() & 0x8000000000000000u) | (e << 52) | m);
    }
    double l = h * r.sym() * 0x1p-55;
    if (!(h + l == h)) l = 0.0;
    double rad = 0.0;
    if (ball) {
        const int kind = r.range(0, 9);
        if (kind == 0) {
            rad = 0.0;
        } else if (kind < 7) {
            const double m = r.u01();
            rad = std::fabs(h) * std::ldexp(m, -r.range(0, 120));
        } else {
            const double m = 1.0 + r.u01();
            rad = std::ldexp(m, r.range(-1074, 1023));
        }
        if (!finite(rad)) rad = std::numeric_limits<double>::max();
    }
    return {h, l, rad};
}

FullCheck check_full(const std::vector<const kb::Entry*>& entries, const std::string& kernel, std::uint64_t seed) {
    FullCheck fc;
    fc.kernel = kernel + "_full";
    const bool ball = kernel.rfind("ball_", 0) == 0;
    const bool is_mul = kernel.find("mul") != std::string::npos;
    const std::vector<Operand> sp = special_operands(ball);
    std::vector<Operand> xs, ys;
    for (const Operand& a : sp)
        for (const Operand& b : sp) {
            xs.push_back(a);
            ys.push_back(b);
        }
    Rng r{seed};
    while (xs.size() < 8192 || xs.size() % 8 != 0) {
        const int mode = r.range(0, 9);   // 0-1 one operand special, 2-4 both large, else both random
        const int lo = is_mul ? 505 : 1019, hi = is_mul ? 517 : 1023;
        Operand a = random_operand(r, ball, mode >= 2 && mode <= 4, lo, hi);
        Operand b = random_operand(r, ball, mode >= 2 && mode <= 4, lo, hi);
        if (mode == 0) a = sp[std::size_t(r.range(0, int(sp.size()) - 1))];
        if (mode == 1) b = sp[std::size_t(r.range(0, int(sp.size()) - 1))];
        xs.push_back(a);
        ys.push_back(b);
    }
    const int n = int(xs.size());
    Buf x0(n), x1(n), xr(n), y0(n), y1(n), yr(n);
    for (int i = 0; i < n; ++i) {
        x0[i] = xs[std::size_t(i)].h; x1[i] = xs[std::size_t(i)].l; xr[i] = xs[std::size_t(i)].r;
        y0[i] = ys[std::size_t(i)].h; y1[i] = ys[std::size_t(i)].l; yr[i] = ys[std::size_t(i)].r;
    }
    Buf a0(n), a1(n), ar(n), b0(n), b1(n), br(n), p0(n), p1(n), pr(n);
    auto run = [&](const char* name, Buf& o0, Buf& o1, Buf& orr) {
        const kb::Entry* e = find(entries, name);
        if (!e) return false;
        kb::TpFn volatile f = e->tp;
        f(n, x0.p, x1.p, xr.p, y0.p, y1.p, yr.p, o0.p, o1.p, orr.p);
        return true;
    };
    run(("scalar/tp/" + kernel + "/full_sel").c_str(), a0, a1, ar);
    run(("scalar/tp/" + kernel + "/full_br").c_str(), b0, b1, br);
    const bool packed = run(("packed/tp/" + kernel + "/full_sel").c_str(), p0, p1, pr);
    Buf v0(n), v1(n), vr(n), u0(n), u1(n), ur(n);
    const bool variants = run(("scalar/tp/" + kernel + "/full_fabs").c_str(), v0, v1, vr) &&
                          run(("scalar/tp/" + kernel + "/full_inl").c_str(), u0, u1, ur);
    fc.cases = n;
    for (int i = 0; i < n; ++i) {
        const bool ab = same(a0[i], b0[i]) && same(a1[i], b1[i]) && (!ball || same(ar[i], br[i]));
        const bool pa = !packed || (same(a0[i], p0[i]) && same(a1[i], p1[i]) && (!ball || same(ar[i], pr[i])));
        const bool va = !variants || (same(a0[i], v0[i]) && same(a1[i], v1[i]) && same(a0[i], u0[i]) && same(a1[i], u1[i]));
        fc.a_vs_b += !ab;
        fc.packed_vs_a += !pa;
        fc.variants_vs_a += !va;
        const bool operands_finite = finite(x0[i]) && finite(y0[i]) && (!ball || (finite(xr[i]) && finite(yr[i])));
        fc.nonfinite_operand += !operands_finite;
        if (!ball) {
            fc.not_canonical += !canonical2(a0[i], a1[i]);
            const double t = is_mul ? x0[i] * y0[i] : x0[i] + y0[i];
            bool ok = true;
            if (!operands_finite) {         // F5: the canonical form of t
                ok = t != t ? (a0[i] != a0[i] && a1[i] != a1[i]) : (bits(a0[i]) == bits(t) && a1[i] == 0.0);
            } else if (!finite(a0[i])) {    // F4: an infinity with the sign of the result, and 0
                ++fc.overflow;
                ok = std::isinf(a0[i]) && a1[i] == 0.0 && std::signbit(a0[i]) == std::signbit(t);
            } else {
                ++fc.finite_result;
            }
            fc.spec += !ok;
        } else {
            fc.not_canonical += !canonical_ball(a0[i], a1[i], ar[i]);
            const bool operand_empty = empty_ball(x0[i], x1[i], xr[i]) || empty_ball(y0[i], y1[i], yr[i]);
            fc.spec += operand_empty != empty_ball(a0[i], a1[i], ar[i]);   // B2
            if (normalized(a0[i], a1[i]) && finite(ar[i]))
                ++fc.finite_result;
            else if (operands_finite)
                ++fc.overflow;
        }
    }
    return fc;
}

// --- Timing -------------------------------------------------------------------------------------

using Clock = std::chrono::steady_clock;

struct Bench {
    const kb::Entry* e;
    const kb::ChainArgs* args;
    int ops;         // operations per call: elements for throughput, steps of the chain for latency
    long calls = 1;  // calls per sample
    std::vector<double> ns;
};

double time_calls(const Bench& b, Data& d) {
    const auto t0 = Clock::now();
    if (b.e->tp) {
        kb::TpFn volatile f = b.e->tp;
        for (long c = 0; c < b.calls; ++c) f(kN, d.x0.p, d.x1.p, d.xr.p, d.y0.p, d.y1.p, d.yr.p, d.z0.p, d.z1.p, d.zr.p);
    } else {
        kb::ChainFn volatile f = b.e->chain;
        for (long c = 0; c < b.calls; ++c) f(b.args);
    }
    return std::chrono::duration<double, std::nano>(Clock::now() - t0).count();
}

void calibrate(Bench& b, Data& d, double sample_ns) {
    b.calls = 1;
    double t = time_calls(b, d);
    while (t < 0.25 * sample_ns) {
        b.calls *= 2;
        t = time_calls(b, d);
    }
    b.calls = std::max(1L, long(double(b.calls) * sample_ns / t));
    time_calls(b, d);   // one more warm-up sample, discarded
}

double quantile(std::vector<double> v, double q) {
    std::sort(v.begin(), v.end());
    const double pos = q * double(v.size() - 1);
    const std::size_t i = std::size_t(pos);
    const double frac = pos - double(i);
    return i + 1 < v.size() ? v[i] * (1 - frac) + v[i + 1] * frac : v[i];
}

// --- Output -------------------------------------------------------------------------------------

std::string esc(const std::string& s) {
    std::string o;
    for (char ch : s) {
        if (ch == '"' || ch == '\\') o.push_back('\\');
        if (ch == '\n') {
            o += "\\n";
            continue;
        }
        o.push_back(ch);
    }
    return o;
}
std::string num(double a) {
    char buf[64];
    std::snprintf(buf, sizeof buf, "%.4g", a);
    return buf;
}

std::string today() {
    const std::time_t t = std::time(nullptr);
    char buf[32];
    std::tm tmv{};
#if defined(_WIN32)
    gmtime_s(&tmv, &t);
#else
    gmtime_r(&t, &tmv);
#endif
    std::strftime(buf, sizeof buf, "%Y-%m-%d", &tmv);
    return buf;
}

}  // namespace

int main(int argc, char** argv) {
    std::string json, machine, commit = "unknown", date = today(), filter;
    int cpu = -1, reps = 21;
    double sample_ms = 4.0;
    bool check_only = false, list = false;
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        auto value = [&]() -> std::string {
            if (i + 1 >= argc) {
                std::fprintf(stderr, "%s needs a value\n", a.c_str());
                std::exit(2);
            }
            return argv[++i];
        };
        if (a == "--json") json = value();
        else if (a == "--machine") machine = value();
        else if (a == "--commit") commit = value();
        else if (a == "--date") date = value();
        else if (a == "--cpu") cpu = std::atoi(value().c_str());
        else if (a == "--reps") reps = std::atoi(value().c_str());
        else if (a == "--sample-ms") sample_ms = std::atof(value().c_str());
        else if (a == "--filter") filter = value();
        else if (a == "--check-only") check_only = true;
        else if (a == "--list") list = true;
        else {
            std::fprintf(stderr, "unknown argument %s (see bench/README.md)\n", a.c_str());
            return 2;
        }
    }
    if (reps < 1) reps = 1;

    const std::vector<const kb::Entry*> entries = all_entries();
    if (list) {
        for (const kb::Entry* e : entries) std::printf("%s\n", e->name);
        return 0;
    }
    const std::string pinning = pin(cpu);
    std::fprintf(stderr, "kairn-bench: %s, %s, packed backend %s, %s\n", cpu_brand().c_str(), compiler().c_str(),
                 kb::packed_backend, pinning.c_str());

    Data d(1);
    kb::mpfr_setup(kN, d.x0.p, d.x1.p, d.y0.p, d.y1.p, &d.sum);

    // 2. Every timed function against the generated kernel, on the benchmark inputs.
    int compared = 0, failed = 0;
    for (const kb::Entry* e : entries) {
        const Name nm = split(e->name);
        const std::string ref_name = "scalar/" + nm.kind + "/" + nm.kernel + "/kairn";
        const kb::Entry* ref = find(entries, ref_name);
        if (!ref) {
            std::fprintf(stderr, "check: %s has no reference %s\n", e->name, ref_name.c_str());
            ++failed;
            continue;
        }
        if (ref == e) continue;
        std::string why;
        const bool ok = nm.backend == "mpfr" ? check_mpfr(*e, *ref, d, why) : check_bits(*e, *ref, d, why);
        ++compared;
        if (!ok) {
            ++failed;
            std::fprintf(stderr, "check FAILED: %s against %s: %s\n", e->name, ref_name.c_str(), why.c_str());
        }
    }
    std::fprintf(stderr, "checked %d functions against the generated kernels: %d failed\n", compared, failed);

    // 3. Forms (a) and (b) of the full kernels.
    std::vector<FullCheck> full;
    int full_failed = 0;
    std::uint64_t seed = 7;
    for (const char* k : {"add_2_2", "mul_2_2", "ball_add_2", "ball_mul_2"}) {
        full.push_back(check_full(entries, k, seed++));
        const FullCheck& f = full.back();
        std::fprintf(stderr,
                     "%s: %d cases (%d with a non-finite operand, %d overflowing, %d finite): (a) vs (b) %d "
                     "differ, packed (a) vs scalar (a) %d, variants vs (a) %d; %d not canonical, %d against "
                     "the statement\n",
                     f.kernel.c_str(), f.cases, f.nonfinite_operand, f.overflow, f.finite_result, f.a_vs_b,
                     f.packed_vs_a, f.variants_vs_a, f.not_canonical, f.spec);
        full_failed += f.a_vs_b + f.packed_vs_a + f.variants_vs_a + f.not_canonical + f.spec;
    }
    if (failed || full_failed) {
        std::fprintf(stderr, "refusing to time: a check failed\n");
        return 1;
    }
    if (check_only) return 0;

    // 4. Timing.
    std::vector<Bench> benches;
    for (const kb::Entry* e : entries) {
        if (!filter.empty() && std::string(e->name).find(filter) == std::string::npos) continue;
        const Name nm = split(e->name);
        Bench b{e, e->tp ? nullptr : &d.args_for(nm.kind), e->tp ? kN : kN / e->lanes, 1, {}};
        benches.push_back(b);
    }
    const double sample_ns = sample_ms * 1e6;
    {   // Bring the core to its working frequency.
        const auto t0 = Clock::now();
        Bench w = benches.front();
        w.calls = 64;
        while (Clock::now() - t0 < std::chrono::milliseconds(300)) time_calls(w, d);
    }
    for (Bench& b : benches) calibrate(b, d, sample_ns);
    for (int r = 0; r < reps; ++r)
        for (Bench& b : benches) b.ns.push_back(time_calls(b, d) / (double(b.calls) * b.ops));

    std::string out = "{\n  \"schema\": 1,\n";
    out += "  \"date\": \"" + esc(date) + "\",\n";
    out += "  \"commit\": \"" + esc(commit) + "\",\n";
    out += "  \"machine\": {\"description\": \"" + esc(machine) + "\", \"cpu\": \"" + esc(cpu_brand()) + "\", \"os\": \"" +
           os_name() + "\", \"arch\": \"" + arch() + "\", \"pinning\": \"" + esc(pinning) + "\"},\n";
    out += "  \"compiler\": \"" + esc(compiler()) + "\",\n";
    out += "  \"flags\": \"" + esc(KAIRN_BENCH_FLAGS) + "\",\n";
    out += "  \"packed_backend\": \"" + std::string(kb::packed_backend) + "\",\n";
    out += "  \"mpfr\": \"" + esc(kb::mpfr_version_text) + "\",\n";
    out += "  \"elements\": " + std::to_string(kN) + ", \"reps\": " + std::to_string(reps) + ", \"sample_ms\": " +
           num(sample_ms) + ",\n";
    out += "  \"checks\": {\"compared\": " + std::to_string(compared) + ", \"failed\": " + std::to_string(failed) +
           ", \"full_forms\": [";
    for (std::size_t i = 0; i < full.size(); ++i) {
        const FullCheck& f = full[i];
        out += std::string(i ? ", " : "") + "{\"kernel\": \"" + f.kernel + "\", \"cases\": " + std::to_string(f.cases) +
               ", \"nonfinite_operand\": " + std::to_string(f.nonfinite_operand) + ", \"overflow\": " +
               std::to_string(f.overflow) + ", \"finite\": " + std::to_string(f.finite_result) + ", \"a_vs_b\": " +
               std::to_string(f.a_vs_b) + ", \"packed_vs_a\": " + std::to_string(f.packed_vs_a) +
               ", \"variants_vs_a\": " + std::to_string(f.variants_vs_a) +
               ", \"not_canonical\": " + std::to_string(f.not_canonical) + ", \"against_statement\": " +
               std::to_string(f.spec) + "}";
    }
    out += "]},\n  \"results\": [\n";
    for (std::size_t i = 0; i < benches.size(); ++i) {
        const Bench& b = benches[i];
        const double mn = *std::min_element(b.ns.begin(), b.ns.end());
        const double md = quantile(b.ns, 0.5);
        const double mx = *std::max_element(b.ns.begin(), b.ns.end());
        out += "    {\"name\": \"" + std::string(b.e->name) + "\", \"lanes\": " + std::to_string(b.e->lanes) +
               ", \"ns_min\": " + num(mn) + ", \"ns_median\": " + num(md) + ", \"ns_max\": " + num(mx) + "}" +
               (i + 1 < benches.size() ? ",\n" : "\n");
        std::fprintf(stderr, "%-52s %9.3f %9.3f %9.3f ns\n", b.e->name, mn, md, mx);
    }
    out += "  ]\n}\n";
    if (!json.empty()) {
        FILE* fp = std::fopen(json.c_str(), "w");
        if (!fp || std::fputs(out.c_str(), fp) < 0 || std::fclose(fp) != 0) {
            std::fprintf(stderr, "cannot write %s\n", json.c_str());
            return 1;
        }
    } else {
        std::fputs(out.c_str(), stdout);
    }
    return 0;
}
