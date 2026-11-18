#!/usr/bin/env python3
"""scaling_mul.py VARIANT COMPILER [FLAGS...]: compile time of ONE multiplication-shaped network
for k = 2, 3, 4, 6, 8 limbs: k(k-1)/2 TwoProd + k plain products feeding 5k^2 - 15k + 13 TwoSum
gates (random wiring), with a time limit per compile. Written to isolate why MSVC did not finish
the 8-limb network of gen_synth.py. VARIANT selects how the products are written:
  stdfma   p = std::fma(a, b, 0.0); e = std::fma(a, b, -p)      (the opaque product, via <cmath>)
  intrin   the same with _mm_fmadd_sd / _mm_fmsub_sd              (x86 only)
  plain    p = a * b;                e = std::fma(a, b, -p)      (textbook: contractable)
"""
import os, random, subprocess, sys, time
variant, cc, flags = sys.argv[1], sys.argv[2], sys.argv[3:]
msvc = os.path.basename(cc).lower() in ("cl", "cl.exe")
LIMIT = 300
PRE = {"stdfma": "#include <cmath>\nstatic inline double P(double a, double b) { return std::fma(a, b, 0.0); }\nstatic inline double E(double a, double b, double p) { return std::fma(a, b, -p); }\n",
       "intrin": "#include <immintrin.h>\nstatic inline double P(double a, double b) { return _mm_cvtsd_f64(_mm_fmadd_sd(_mm_set_sd(a), _mm_set_sd(b), _mm_setzero_pd())); }\nstatic inline double E(double a, double b, double p) { return _mm_cvtsd_f64(_mm_fmsub_sd(_mm_set_sd(a), _mm_set_sd(b), _mm_set_sd(p))); }\n",
       "plain": "#include <cmath>\nstatic inline double P(double a, double b) { return a * b; }\nstatic inline double E(double a, double b, double p) { return std::fma(a, b, -p); }\n"}[variant]
for k in (2, 3, 4, 6, 8):
    random.seed(k)
    gates = 5 * k * k - 15 * k + 13
    w, lines = [], [PRE, "void net(const double *a, const double *b, double *out) {"]
    for i in range(k):
        for j in range(k - i):
            lines.append(f"    const double p{i}_{j} = P(a[{i}], b[{j}]);")
            w.append(f"p{i}_{j}")
            if i + j < k - 1:
                lines.append(f"    const double q{i}_{j} = E(a[{i}], b[{j}], p{i}_{j});")
                w.append(f"q{i}_{j}")
    for g in range(gates):
        i, j = random.sample(range(len(w)), 2)
        lines += [f"    const double s{g} = {w[i]} + {w[j]}, c{g} = s{g} - {w[i]};",
                  f"    const double e{g} = ({w[i]} - (s{g} - c{g})) + ({w[j]} - c{g});"]
        w[i], w[j] = f"s{g}", f"e{g}"
    lines += [f"    out[{i}] = {w[i]};" for i in range(k)] + ["}"]
    open("net.cpp", "w").write("\n".join(lines) + "\n")
    cmd = [cc] + flags + (["/nologo", "/c", "net.cpp", "/Fonet.obj"] if msvc else ["-c", "net.cpp", "-o", "net.o"])
    t = time.time()
    label = f"  k = {k}: {k * (k - 1) // 2:2d} TwoProd + {k} products + {gates:3d} gates"
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=LIMIT)
        print(f"{label}  {time.time() - t:8.2f} s{'' if r.returncode == 0 else '  FAILED ' + (r.stdout + r.stderr).strip().splitlines()[-1][:80]}", flush=True)
    except subprocess.TimeoutExpired:
        print(f"{label}  > {LIMIT} s (stopped)", flush=True)
        break
for f in ("net.cpp", "net.o", "net.obj"):
    if os.path.exists(f):
        os.remove(f)
