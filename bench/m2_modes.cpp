// kairn-bench-m2-modes (bench/README.md, "Milestone 2"): does arithmetic under a directed rounding mode
// run as fast as under rounding to nearest? A loop of additions and one of products over arrays in L1,
// each in a function of its own that the compiler may vectorize (restrict pointers), timed with the
// rounding mode set to each of the four modes before the call and reset after it. The functions are
// compiled as plain code, without -frounding-math and without FENV_ACCESS, so that the compiler emits
// for them what it emits for any loop; that they did compute under the mode set is checked: the results
// under downward and upward rounding must differ from those rounded to nearest on the inexact sums and
// products of the inputs, and lie on the right side of them. This is the speed a classical library
// reaches in a loop under one mode when its compiler emits the plain loop for it. Not part of the
// library; no Kairn header.
//
//   kairn-bench-m2-modes-LEVEL [--reps R] [--json FILE]
#include <cfenv>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "bench.hpp"   // KB_NOINLINE, KB_RESTRICT
#include "bench_util.hpp"

#ifndef KAIRN_BENCH_FLAGS
#define KAIRN_BENCH_FLAGS "unknown"
#endif

extern "C" KB_NOINLINE void kb_m2_modes_add(int n, const double* KB_RESTRICT x, const double* KB_RESTRICT y,
                                            double* KB_RESTRICT z) {
    for (int i = 0; i < n; ++i) z[i] = x[i] + y[i];
}
extern "C" KB_NOINLINE void kb_m2_modes_mul(int n, const double* KB_RESTRICT x, const double* KB_RESTRICT y,
                                            double* KB_RESTRICT z) {
    for (int i = 0; i < n; ++i) z[i] = x[i] * y[i];
}

int main(int argc, char** argv) {
    namespace u = kairn_bench::util;
    int reps = 31;
    std::string json;
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (a == "--reps" && i + 1 < argc) reps = std::atoi(argv[++i]);
        else if (a == "--json" && i + 1 < argc) json = argv[++i];
        else {
            std::fprintf(stderr, "usage: kairn-bench-m2-modes [--reps R] [--json FILE]\n");
            return 2;
        }
    }
    u::pin(-1);
    const int n = 256;
    std::vector<double> x(n), y(n), z(n), rn(n), rd(n), ru(n);
    u::Rng g{5};
    for (int i = 0; i < n; ++i) {   // inexact sums and products: y far below the last place of x
        x[i] = 1.0 + g.u01();
        y[i] = (1.0 + g.u01()) * 0x1p-60;
    }
    using Fn = void (*)(int, const double*, const double*, double*);
    const Fn fns[2] = {kb_m2_modes_add, kb_m2_modes_mul};
    const char* ops[2] = {"add", "mul"};
    const int modes[4] = {FE_TONEAREST, FE_DOWNWARD, FE_UPWARD, FE_TOWARDZERO};
    const char* names[4] = {"nearest", "downward", "upward", "towardzero"};
    // The check: the results of each mode, from the same functions.
    long wrong = 0, differ = 0;
    for (int op = 0; op < 2; ++op) {
        Fn volatile f = fns[op];
        f(n, x.data(), y.data(), rn.data());
        std::fesetround(FE_DOWNWARD);
        f(n, x.data(), y.data(), rd.data());
        std::fesetround(FE_UPWARD);
        f(n, x.data(), y.data(), ru.data());
        std::fesetround(FE_TONEAREST);
        for (int i = 0; i < n; ++i) {
            differ += (rd[i] != rn[i]) + (ru[i] != rn[i]);
            wrong += !(rd[i] <= rn[i] && rn[i] <= ru[i] && rd[i] < ru[i]);
        }
    }
    std::fprintf(stderr, "check: %ld of %d directed results differ from rounding to nearest, %ld wrong\n", differ,
                 4 * n, wrong);
    if (wrong) return 1;
    std::string out = "{\n  \"schema\": 1,\n  \"what\": \"kairn-bench-m2-modes\",\n  \"cpu\": \"" + u::esc(u::cpu_brand()) +
                      "\",\n  \"compiler\": \"" + u::esc(u::compiler()) + "\",\n  \"flags\": \"" + u::esc(KAIRN_BENCH_FLAGS) +
                      "\",\n  \"check\": {\"directed_results\": " + std::to_string(4 * n) + ", \"differ_from_nearest\": " +
                      std::to_string(differ) + ", \"wrong\": " + std::to_string(wrong) + "},\n  \"results\": [\n";
    bool first = true;
    for (int op = 0; op < 2; ++op)
        for (int m = 0; m < 4; ++m) {
            Fn volatile f = fns[op];
            auto call = [&]() { f(n, x.data(), y.data(), z.data()); };
            std::fesetround(modes[m]);
            const long calls = u::calibrate(call, 4e6);
            std::vector<double> ns;
            for (int r = 0; r < reps; ++r) ns.push_back(u::time_calls(call, calls) / (double(calls) * n));
            std::fesetround(FE_TONEAREST);
            const double mn = *std::min_element(ns.begin(), ns.end());
            std::fprintf(stderr, "%s %-10s %.4f ns per element\n", ops[op], names[m], mn);
            out += std::string(first ? "" : ",\n") + "    {\"op\": \"" + ops[op] + "\", \"mode\": \"" + names[m] +
                   "\", \"ns_min\": " + u::num(mn) + ", \"ns_median\": " + u::num(u::quantile(ns, 0.5)) + "}";
            first = false;
        }
    out += "\n  ]\n}\n";
    if (!json.empty() && !u::write_file(json, out)) return 1;
    if (json.empty()) std::fputs(out.c_str(), stdout);
    return 0;
}
