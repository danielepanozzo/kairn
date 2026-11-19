// Two costs that kairn-bench does not measure (bench/README.md, "Other costs"): the checks of
// KAIRN_CHECKS, and MSVC's /GS stack cookie in functions that use Expansion<double, 1>.
//
//   kairn-bench-costs-O2 [--json FILE] [--machine TEXT] [--commit TEXT] [--date TEXT] [--cpu N]
//                        [--reps R] [--sample-ms MS] [--list]
//
// KAIRN_CHECKS must be defined the same way in every translation unit of a program (config.hpp),
// so each value is a program of its own, built from this one file: kairn-bench-costs-LEVEL with
// KAIRN_CHECKS 0 and kairn-bench-costs-checks-LEVEL with KAIRN_CHECKS 1, for the levels of
// kairn-bench and -O0 (/Od). The cookie is compared by building the same programs again with /GS-.
// Each program times the same functions, as kairn-bench does (bench.hpp): a non-inlined function
// called through a pointer, a loop of independent operations over arrays in L1 timed per
// operation, or a dependent chain timed per step; samples of about 4 ms, in rounds over all
// functions; the minimum, median and maximum over the samples. The functions:
//
// - env/loop: kairn::environment_ok() called once per element, the results counted;
// - add/loop, add/sum: x + y on Expansion<double, 2>, a loop and a running sum;
// - mul/loop, mul/prod: x * y on Expansion<double, 2>, a loop and a running product of factors
//   near 1;
// - k1/loop, k1/sum: x + y on Expansion<double, 1>, a loop and a running sum; k1/call: the same
//   loop, each addition a call of a non-inlined function (kc_k1_add), which is where a cookie
//   costs most; double/loop, double/call: the same two loops on double;
// - double/sum, fma/chain: one double addition, and one fused multiply-add s = fma(s, h, x[i]),
//   in a chain: the scale.
//
// Each records a checksum of its outputs, so that the programs can be compared: neither the checks
// nor the cookie change a result.
#include <kairn/kairn.hpp>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <limits>
#include <string>
#include <vector>

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

namespace {

using E1 = kairn::Expansion<double, 1>;
using E2 = kairn::Expansion<double, 2>;
constexpr int kN = 256;

struct Data {
    E2 x[kN], y[kN], f[kN];
    E1 x1[kN], y1[kN];
    double xa[kN], ya[kN];
    double h = 0;
    E2 p0;
    // Outputs.
    E2 z[kN];
    E1 z1[kN];
    double za[kN];
    E2 ze;
    E1 z1e;
    double zae = 0;
    long count = 0;
};
Data* g = nullptr;

}  // namespace

// --- The timed functions ------------------------------------------------------------------------
//
// Each is a non-inlined function with C linkage, so that its loop can be found in a disassembly.

extern "C" KB_NOINLINE void kc_env_loop(void* p) {
    Data& d = *static_cast<Data*>(p);
    long c = 0;
    for (int i = 0; i < kN; ++i) c += kairn::environment_ok() ? 1 : 0;
    d.count = c;
}
extern "C" KB_NOINLINE void kc_add_loop(void* p) {
    Data& d = *static_cast<Data*>(p);
    for (int i = 0; i < kN; ++i) d.z[i] = d.x[i] + d.y[i];
}
extern "C" KB_NOINLINE void kc_mul_loop(void* p) {
    Data& d = *static_cast<Data*>(p);
    for (int i = 0; i < kN; ++i) d.z[i] = d.x[i] * d.y[i];
}
extern "C" KB_NOINLINE void kc_add_sum(void* p) {
    Data& d = *static_cast<Data*>(p);
    E2 s{};
    for (int i = 0; i < kN; ++i) s = s + d.x[i];
    d.ze = s;
}
extern "C" KB_NOINLINE void kc_mul_prod(void* p) {
    Data& d = *static_cast<Data*>(p);
    E2 s = d.p0;
    for (int i = 0; i < kN; ++i) s = s * d.f[i];
    d.ze = s;
}
extern "C" KB_NOINLINE void kc_k1_loop(void* p) {
    Data& d = *static_cast<Data*>(p);
    for (int i = 0; i < kN; ++i) d.z1[i] = d.x1[i] + d.y1[i];
}
extern "C" KB_NOINLINE void kc_k1_sum(void* p) {
    Data& d = *static_cast<Data*>(p);
    E1 s{};
    for (int i = 0; i < kN; ++i) s = s + d.x1[i];
    d.z1e = s;
}
// One addition per call, as a small function a client does not inline; called through a pointer.
extern "C" KB_NOINLINE void kc_k1_add(const E1& x, const E1& y, E1* z) { *z = x + y; }
extern "C" KB_NOINLINE void kc_double_add(const double& x, const double& y, double* z) { *z = x + y; }
using K1Add = void (*)(const E1&, const E1&, E1*);
using DoubleAdd = void (*)(const double&, const double&, double*);
extern "C" KB_NOINLINE void kc_k1_call(void* p) {
    Data& d = *static_cast<Data*>(p);
    K1Add volatile f = kc_k1_add;
    const K1Add fn = f;
    for (int i = 0; i < kN; ++i) fn(d.x1[i], d.y1[i], &d.z1[i]);
}
extern "C" KB_NOINLINE void kc_double_call(void* p) {
    Data& d = *static_cast<Data*>(p);
    DoubleAdd volatile f = kc_double_add;
    const DoubleAdd fn = f;
    for (int i = 0; i < kN; ++i) fn(d.xa[i], d.ya[i], &d.za[i]);
}
extern "C" KB_NOINLINE void kc_double_loop(void* p) {
    Data& d = *static_cast<Data*>(p);
    for (int i = 0; i < kN; ++i) d.za[i] = d.xa[i] + d.ya[i];
}
extern "C" KB_NOINLINE void kc_double_sum(void* p) {
    Data& d = *static_cast<Data*>(p);
    double s = 0;
    for (int i = 0; i < kN; ++i) s = s + d.xa[i];
    d.zae = s;
}
extern "C" KB_NOINLINE void kc_fma_chain(void* p) {
    Data& d = *static_cast<Data*>(p);
    double s = 0;
    const double h = d.h;
    for (int i = 0; i < kN; ++i) s = kairn::gen::fma_rn(s, h, d.xa[i]);
    d.zae = s;
}

namespace {

using Fn = void (*)(void*);
struct Entry {
    const char* name;
    Fn fn;
};
const Entry entries[] = {
    {"env/loop", kc_env_loop},       {"add/loop", kc_add_loop},       {"mul/loop", kc_mul_loop},
    {"add/sum", kc_add_sum},         {"mul/prod", kc_mul_prod},       {"k1/loop", kc_k1_loop},
    {"k1/sum", kc_k1_sum},           {"k1/call", kc_k1_call},         {"double/loop", kc_double_loop},
    {"double/call", kc_double_call}, {"double/sum", kc_double_sum},   {"fma/chain", kc_fma_chain},
};

// --- Inputs, as api.cpp makes them --------------------------------------------------------------

struct Rng {
    std::uint64_t s;
    std::uint64_t next() {   // splitmix64
        std::uint64_t z = (s += 0x9e3779b97f4a7c15u);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9u;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebu;
        return z ^ (z >> 31);
    }
    double u01() { return double(next() >> 11) * 0x1p-53; }
    double sym() { return 2.0 * u01() - 1.0; }
    int range(int lo, int hi) { return lo + int(next() % std::uint64_t(hi - lo + 1)); }
    double sign() { return (next() & 1) ? -1.0 : 1.0; }
};

// A normalized pair with |h| in [2^kmin, 2^(kmax+1)) and |l| about 2^-53 |h|; or, for a factor, h
// in [2^-1/4, 2^1/4).
E2 number(Rng& r, int kmin, int kmax, bool factor) {
    double a;
    if (factor) {
        a = std::exp2(0.25 * r.sym());
    } else {
        const double s = r.sign();
        const double m = 1.0 + r.u01();
        a = s * std::ldexp(m, r.range(kmin, kmax));
    }
    const double v = r.sym();
    const double b = a * v * 0x1p-53;
    double limbs[2];
    kairn::gen::fast_two_sum(a, b, limbs[0], limbs[1]);
    return E2::from_limbs(limbs);
}

void fill(Data& d, std::uint64_t seed) {
    Rng r{seed};
    for (int i = 0; i < kN; ++i) {
        d.x[i] = number(r, -8, 8, false);
        d.y[i] = number(r, -8, 8, false);
        d.f[i] = number(r, 0, 0, true);
        d.xa[i] = d.x[i].limb[0];
        d.ya[i] = d.y[i].limb[0];
        d.x1[i] = E1(d.xa[i]);
        d.y1[i] = E1(d.ya[i]);
    }
    d.h = 0.75 + 0.125 * r.u01();
    d.p0 = number(r, 0, 0, true);
}

// FNV-1a over the bytes of the outputs, from z to the end of Data.
std::uint64_t checksum(const Data& d) {
    std::uint64_t hsh = 0xcbf29ce484222325u;
    const unsigned char* b = reinterpret_cast<const unsigned char*>(&d.z);
    const unsigned char* e = reinterpret_cast<const unsigned char*>(&d + 1);
    for (; b < e; ++b) hsh = (hsh ^ *b) * 0x100000001b3u;
    return hsh;
}
void clear(Data& d) {
    unsigned char* b = reinterpret_cast<unsigned char*>(&d.z);
    std::memset(b, 0xff, std::size_t(reinterpret_cast<unsigned char*>(&d + 1) - b));
}

// --- The machine and the build, as main.cpp records them ----------------------------------------

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

std::string esc(const std::string& s) {
    std::string o;
    for (char ch : s) {
        if (ch == '"' || ch == '\\') o.push_back('\\');
        o.push_back(ch);
    }
    return o;
}
std::string num(double a) {
    char buf[64];
    std::snprintf(buf, sizeof buf, "%.4g", a);
    return buf;
}

// --- Timing -------------------------------------------------------------------------------------

using Clock = std::chrono::steady_clock;

struct Bench {
    const Entry* e;
    long calls = 1;
    std::vector<double> ns;
};

double time_calls(const Bench& b) {
    Fn volatile f = b.e->fn;
    const auto t0 = Clock::now();
    for (long c = 0; c < b.calls; ++c) f(g);
    return std::chrono::duration<double, std::nano>(Clock::now() - t0).count();
}

void calibrate(Bench& b, double sample_ns) {
    b.calls = 1;
    double t = time_calls(b);
    while (t < 0.25 * sample_ns) {
        b.calls *= 2;
        t = time_calls(b);
    }
    b.calls = std::max(1L, long(double(b.calls) * sample_ns / t));
    time_calls(b);   // one more warm-up sample, discarded
}

double quantile(std::vector<double> v, double q) {
    std::sort(v.begin(), v.end());
    const double pos = q * double(v.size() - 1);
    const std::size_t i = std::size_t(pos);
    const double frac = pos - double(i);
    return i + 1 < v.size() ? v[i] * (1 - frac) + v[i + 1] * frac : v[i];
}

}  // namespace

int main(int argc, char** argv) {
    std::string json, machine, commit = "unknown", date = today();
    int cpu = -1, reps = 21;
    double sample_ms = 4.0;
    bool list = false;
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
        else if (a == "--list") list = true;
        else {
            std::fprintf(stderr, "unknown argument %s (see bench/README.md)\n", a.c_str());
            return 2;
        }
    }
    if (reps < 1) reps = 1;
    if (list) {
        for (const Entry& e : entries) std::printf("%s\n", e.name);
        return 0;
    }
    const std::string pinning = pin(cpu);
    std::fprintf(stderr, "kairn-bench-costs: KAIRN_CHECKS %d, %s, %s, %s\n", KAIRN_CHECKS, cpu_brand().c_str(),
                 compiler().c_str(), pinning.c_str());
    if (!kairn::environment_ok() || !kairn::self_test()) {
        std::fprintf(stderr, "the environment or the self-test fails: refusing to time\n");
        return 1;
    }
    g = new Data();
    fill(*g, 1);

    std::vector<Bench> benches;
    std::vector<std::uint64_t> sums;
    for (const Entry& e : entries) {
        clear(*g);
        e.fn(g);
        sums.push_back(checksum(*g));
        benches.push_back(Bench{&e, 1, {}});
    }
    const double sample_ns = sample_ms * 1e6;
    {   // Bring the core to its working frequency.
        const auto t0 = Clock::now();
        Bench w = benches[1];
        w.calls = 64;
        while (Clock::now() - t0 < std::chrono::milliseconds(300)) time_calls(w);
    }
    for (Bench& b : benches) calibrate(b, sample_ns);
    for (int r = 0; r < reps; ++r)
        for (Bench& b : benches) b.ns.push_back(time_calls(b) / (double(b.calls) * kN));

    std::string out = "{\n  \"schema\": 1,\n";
    out += "  \"date\": \"" + esc(date) + "\",\n";
    out += "  \"commit\": \"" + esc(commit) + "\",\n";
    out += "  \"machine\": {\"description\": \"" + esc(machine) + "\", \"cpu\": \"" + esc(cpu_brand()) +
           "\", \"pinning\": \"" + esc(pinning) + "\"},\n";
    out += "  \"compiler\": \"" + esc(compiler()) + "\",\n";
    out += "  \"flags\": \"" + esc(KAIRN_BENCH_FLAGS) + "\",\n";
    out += "  \"kairn_checks\": " + std::to_string(KAIRN_CHECKS) + ",\n";
    out += "  \"elements\": " + std::to_string(kN) + ", \"reps\": " + std::to_string(reps) + ", \"sample_ms\": " +
           num(sample_ms) + ",\n  \"results\": [\n";
    for (std::size_t i = 0; i < benches.size(); ++i) {
        const Bench& b = benches[i];
        const double mn = *std::min_element(b.ns.begin(), b.ns.end());
        const double md = quantile(b.ns, 0.5);
        const double mx = *std::max_element(b.ns.begin(), b.ns.end());
        char sum[32];
        std::snprintf(sum, sizeof sum, "%016llx", static_cast<unsigned long long>(sums[i]));
        out += "    {\"name\": \"" + std::string(b.e->name) + "\", \"ns_min\": " + num(mn) + ", \"ns_median\": " +
               num(md) + ", \"ns_max\": " + num(mx) + ", \"checksum\": \"" + sum + "\"}" +
               (i + 1 < benches.size() ? ",\n" : "\n");
        std::fprintf(stderr, "%-12s %9.3f %9.3f %9.3f ns  %s\n", b.e->name, mn, md, mx, sum);
    }
    out += "  ]\n}\n";
    if (!json.empty()) {
        FILE* fp = nullptr;
#if defined(_MSC_VER)
        if (fopen_s(&fp, json.c_str(), "w") != 0) fp = nullptr;
#else
        fp = std::fopen(json.c_str(), "w");
#endif
        if (!fp || std::fputs(out.c_str(), fp) < 0 || std::fclose(fp) != 0) {
            std::fprintf(stderr, "cannot write %s\n", json.c_str());
            return 1;
        }
    } else {
        std::fputs(out.c_str(), stdout);
    }
    return 0;
}
