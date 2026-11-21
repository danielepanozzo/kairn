#!/usr/bin/env python3
"""rational_cost.py: what kairn::rational (include/kairn/rational.hpp) costs, at compile time and at
run time, with and without the check of its results in constant evaluation (KAIRN_RATIONAL_CHECK).

  rational_cost.py compile --cxx CXX [--msvc] [--flags "..."] [--reps R] [--counts 1,100,1000]
                           [--types e2[,e1]] [--cpu N] [--workdir DIR] [--json FILE]
      Compiles, R times in rounds, a translation unit that includes kairn/kairn.hpp and defines N
      constants rational<Expansion<double, 2>>(num, den) (e2; e1 for Expansion<double, 1>) with
      distinct random 64-bit terms (fixed seed), for each N of --counts, with KAIRN_RATIONAL_CHECK 0
      and 1, and the same unit with no constant; prints the median wall time of each and what the
      constants add per constant. --cpu pins the script and the compilers to one logical processor
      (Linux).
  rational_cost.py run --cxx CXX [--msvc] [--flags "..."] [--workdir DIR] [--json FILE]
      Builds and runs a program that times, per call, kairn::rational<X>(num, den) for X =
      Expansion<double, 1>, Expansion<double, 2>, Expansion<float, 1>, Expansion<float, 2> on 4096
      random fractions at run time, and kairn::is_rational_result on their results (the check that
      a build with KAIRN_CHECKS makes after every call); the minimum over 31 samples.

Compilations are -std=c++20 -O2 -c -DNDEBUG (MSVC: /std:c++20 /O2 /c /DNDEBUG /EHsc), with the FMA
option where the target needs one (--flags, for example "-mfma" on x86-64, "/arch:AVX2" with
MSVC). Every compilation has a timeout, and only the process this script started is terminated
on one. Run from the repository root; nothing is written outside --workdir (default
build-rational-cost/).
"""
import argparse
import json
import os
import random
import statistics
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIG = 2 ** 63


def fractions(n, seed=20261120):
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        num, den = rng.randrange(-BIG, BIG), rng.randrange(-BIG, BIG)
        if den != 0:
            out.append((num, den))
    return out


def literal(n):
    return "(-9223372036854775807LL - 1)" if n == -BIG else "%dLL" % n


def unit(n, typ="e2"):
    lines = ["#include <kairn/kairn.hpp>", "using X = kairn::Expansion<double, %d>;" % (2 if typ == "e2" else 1)]
    for i, (num, den) in enumerate(fractions(n)):
        lines.append("constexpr kairn::Constant<X> c%d = kairn::rational<X>(%s, %s);" % (i, literal(num), literal(den)))
    # One use, so that the unit has an object to emit.
    lines.append("double sum() { return %s; }" % (" + ".join("c%d.error" % i for i in range(min(n, 4))) or "0.0"))
    return "\n".join(lines) + "\n"


def compile_command(a, source, check):
    if a.msvc:
        return [a.cxx, "/nologo", "/std:c++20", "/O2", "/c", "/DNDEBUG", "/EHsc", "/I" + os.path.join(ROOT, "include"),
                "/DKAIRN_RATIONAL_CHECK=%d" % check] + a.flags.split() + ["/Fo" + source + ".obj", source]
    return [a.cxx, "-std=c++20", "-O2", "-c", "-DNDEBUG", "-I", os.path.join(ROOT, "include"),
            "-DKAIRN_RATIONAL_CHECK=%d" % check] + a.flags.split() + ["-o", source + ".o", source]


def timed(cmd, timeout):
    start = time.perf_counter()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise SystemExit("timeout: %s" % " ".join(cmd))
    if proc.returncode != 0:
        raise SystemExit("failed (%d): %s\n%s" % (proc.returncode, " ".join(cmd), out.decode(errors="replace")))
    return time.perf_counter() - start


def compile_times(a):
    os.makedirs(a.workdir, exist_ok=True)
    if a.cpu is not None and sys.platform.startswith("linux"):
        os.sched_setaffinity(0, {a.cpu})
    counts = [int(c) for c in a.counts.split(",")]
    types = a.types.split(",")
    jobs = [("none", "e2", 0)] + [(n, typ, check) for typ in types for n in counts for check in (0, 1)]
    sources = {}
    for typ in types:
        for n in [0] + counts:
            path = os.path.join(a.workdir, "rational_%s_%d.cpp" % (typ, n))
            with open(path, "w") as f:
                f.write(unit(n, typ))
            sources[(typ, n)] = path
    times = {(n, typ, check): [] for n, typ, check in jobs}
    for _ in range(a.reps):
        for n, typ, check in jobs:
            src = sources[(typ, 0 if n == "none" else n)]
            times[(n, typ, check)].append(timed(compile_command(a, src, check), a.timeout))
    base = statistics.median(times[("none", "e2", 0)])
    rows = []
    print("%-34s %10s %14s" % ("unit", "median s", "per constant"))
    print("%-34s %10.3f %14s" % ("include only", base, "-"))
    for typ in types:
        for n in counts:
            for check in (0, 1):
                med = statistics.median(times[(n, typ, check)])
                per = (med - base) / n * 1000
                rows.append({"type": typ, "constants": n, "check": check, "median_s": med, "per_constant_ms": per,
                             "samples": times[(n, typ, check)]})
                print("%-34s %10.3f %11.3f ms" % ("%s, %d constants, check %d" % (typ, n, check), med, per))
    version = subprocess.run([a.cxx, "--version"] + a.flags.split(), capture_output=True, text=True).stdout
    return {"compiler": a.cxx, "version": version.strip().splitlines()[0] if version.strip() else "",
            "flags": a.flags, "reps": a.reps, "cpu": a.cpu, "include_only_s": base,
            "include_only_samples": times[("none", "e2", 0)], "rows": rows}


RUN_SOURCE = r"""
#include <kairn/kairn.hpp>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <vector>

struct Fraction { long long num, den; };

template <class X>
std::uint64_t sink_of(const kairn::Constant<X>& c) {
    std::uint64_t s = c.exact;
    for (int i = 0; i < kairn::traits<X>::limbs; ++i) {
        const double v = c.value.limb[i];
        std::uint64_t b = 0;
        std::memcpy(&b, &v, sizeof b);
        s += b;
    }
    return s;
}

template <class X>
void time_one(const char* name, const std::vector<Fraction>& f) {
    std::vector<kairn::Constant<X>> out(f.size());
    double best_make = 1e9, best_check = 1e9;
    std::uint64_t sink = 0;
    for (int sample = 0; sample < 31; ++sample) {
        auto t0 = std::chrono::steady_clock::now();
        for (std::size_t i = 0; i < f.size(); ++i) out[i] = kairn::rational<X>(f[i].num, f[i].den);
        auto t1 = std::chrono::steady_clock::now();
        int ok = 0;
        for (std::size_t i = 0; i < f.size(); ++i) ok += kairn::is_rational_result(out[i], f[i].num, f[i].den);
        auto t2 = std::chrono::steady_clock::now();
        if (ok != int(f.size())) { std::printf("the check refused a result\n"); std::exit(1); }
        for (const auto& c : out) sink += sink_of(c);
        best_make = std::min(best_make, std::chrono::duration<double, std::nano>(t1 - t0).count() / f.size());
        best_check = std::min(best_check, std::chrono::duration<double, std::nano>(t2 - t1).count() / f.size());
    }
    std::printf("{\"type\": \"%s\", \"rational_ns\": %.1f, \"check_ns\": %.1f, \"sink\": %llu}\n", name, best_make,
                best_check, (unsigned long long)(sink & 0xff));
}

int main() {
    std::mt19937_64 rng(20261120);
    std::vector<Fraction> f(4096);
    for (auto& x : f) {
        do { x.num = (long long)rng(); x.den = (long long)rng(); } while (x.den == 0);
    }
    time_one<kairn::Expansion<double, 1>>("Expansion<double, 1>", f);
    time_one<kairn::Expansion<double, 2>>("Expansion<double, 2>", f);
    time_one<kairn::Expansion<float, 1>>("Expansion<float, 1>", f);
    time_one<kairn::Expansion<float, 2>>("Expansion<float, 2>", f);
    return 0;
}
"""


def run_times(a):
    os.makedirs(a.workdir, exist_ok=True)
    src = os.path.join(a.workdir, "rational_run.cpp")
    exe = os.path.join(a.workdir, "rational_run" + (".exe" if a.msvc else ""))
    with open(src, "w") as f:
        f.write(RUN_SOURCE)
    if a.msvc:
        cmd = [a.cxx, "/nologo", "/std:c++20", "/O2", "/DNDEBUG", "/EHsc", "/I" + os.path.join(ROOT, "include")] + \
            a.flags.split() + ["/Fe" + exe, "/Fo" + src + ".obj", src]
    else:
        cmd = [a.cxx, "-std=c++20", "-O2", "-DNDEBUG", "-I", os.path.join(ROOT, "include")] + a.flags.split() + \
            ["-o", exe, src]
    timed(cmd, a.timeout)
    done = subprocess.run([exe], stdout=subprocess.PIPE, timeout=a.timeout, check=True)
    rows = [json.loads(line) for line in done.stdout.decode().splitlines() if line.startswith("{")]
    print("%-22s %14s %20s" % ("type", "rational, ns", "is_rational_result, ns"))
    for r in rows:
        print("%-22s %14.1f %20.1f" % (r["type"], r["rational_ns"], r["check_ns"]))
    return {"compiler": a.cxx, "flags": a.flags, "rows": rows}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["compile", "run"])
    ap.add_argument("--cxx", required=True)
    ap.add_argument("--msvc", action="store_true")
    ap.add_argument("--flags", default="")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--counts", default="1,100,1000")
    ap.add_argument("--types", default="e2")
    ap.add_argument("--cpu", type=int)
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("--workdir", default="build-rational-cost")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    a.workdir = os.path.abspath(a.workdir)
    result = compile_times(a) if a.what == "compile" else run_times(a)
    if a.json:
        with open(a.json, "w") as f:
            json.dump(result, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
