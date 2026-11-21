// What a benchmark driver needs besides the timed functions: the description of the machine and of
// the build, pinning, the load of the machine, a seeded generator, and the timing of a function in
// samples (bench/README.md). Used by m2_main.cpp; main.cpp, the driver of Milestone 1, keeps its own
// copies of the same functions, so that its measurements stay reproducible as they were made.
#pragma once

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <string>
#include <vector>

#if defined(_WIN32)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
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

namespace kairn_bench::util {

struct Rng {
    std::uint64_t s;
    std::uint64_t next() {   // splitmix64, as in main.cpp and api.cpp
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

inline std::string cpu_brand() {
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

inline std::string compiler() {
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

inline std::string os_name() {
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

inline std::string arch() {
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
inline std::string pin(int cpu) {
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

// The 1-, 5- and 15-minute load averages of the machine, or -1 where the system has none.
inline void load_average(double out[3]) {
    out[0] = out[1] = out[2] = -1.0;
#if defined(__APPLE__) || defined(__linux__)
    double l[3];
    if (getloadavg(l, 3) == 3) {
        out[0] = l[0];
        out[1] = l[1];
        out[2] = l[2];
    }
#endif
}

inline std::string today() {
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

inline std::string esc(const std::string& s) {
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

inline std::string num(double a) {
    char buf[64];
    std::snprintf(buf, sizeof buf, "%.4g", a);
    return buf;
}

inline double quantile(std::vector<double> v, double q) {
    std::sort(v.begin(), v.end());
    const double pos = q * double(v.size() - 1);
    const std::size_t i = std::size_t(pos);
    const double frac = pos - double(i);
    return i + 1 < v.size() ? v[i] * (1 - frac) + v[i + 1] * frac : v[i];
}

// The timing of one function, as main.cpp times: calibrated to samples of about sample_ns, then one
// sample per round over all functions, so that a disturbance spreads over all of them.
using Clock = std::chrono::steady_clock;

template <class Call>
double time_calls(Call&& call, long calls) {
    const auto t0 = Clock::now();
    for (long c = 0; c < calls; ++c) call();
    return std::chrono::duration<double, std::nano>(Clock::now() - t0).count();
}

template <class Call>
long calibrate(Call&& call, double sample_ns) {
    long calls = 1;
    double t = time_calls(call, calls);
    while (t < 0.25 * sample_ns) {
        calls *= 2;
        t = time_calls(call, calls);
    }
    calls = std::max(1L, long(double(calls) * sample_ns / t));
    time_calls(call, calls);   // one more warm-up sample, discarded
    return calls;
}

inline bool write_file(const std::string& path, const std::string& text) {
    FILE* fp = nullptr;
#if defined(_MSC_VER)
    if (fopen_s(&fp, path.c_str(), "w") != 0) fp = nullptr;
#else
    fp = std::fopen(path.c_str(), "w");
#endif
    return fp && std::fputs(text.c_str(), fp) >= 0 && std::fclose(fp) == 0;
}

}  // namespace kairn_bench::util
