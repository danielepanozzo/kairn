#!/usr/bin/env python3
"""scaling.py COMPILER [FLAGS...]: compile time of ONE straight-line network of N TwoSum gates on
16 wires (random wiring), for growing N, with a time limit per compile. Written after MSVC failed
to finish a 213-gate network in 24 CPU-minutes. Each gate is 6 floating-point operations.
N = 6, 16, 31 are the sizes of the published 2-, 3- and 4-limb additions; 141 and 213 are the
extrapolated 8-limb addition and multiplication."""
import os, random, subprocess, sys, time
cc, flags = sys.argv[1], sys.argv[2:]
msvc = os.path.basename(cc).lower() in ("cl", "cl.exe")
LIMIT = 300
for n in (6, 16, 31, 48, 64, 96, 141, 213):
    random.seed(n)
    w = [f"a[{i}]" for i in range(16)]
    lines = ["void net(const double *a, double *out) {"]
    for g in range(n):
        i, j = random.sample(range(16), 2)
        lines += [f"    const double s{g} = {w[i]} + {w[j]}, b{g} = s{g} - {w[i]};",
                  f"    const double e{g} = ({w[i]} - (s{g} - b{g})) + ({w[j]} - b{g});"]
        w[i], w[j] = f"s{g}", f"e{g}"
    lines += [f"    out[{i}] = {w[i]};" for i in range(8)] + ["}"]
    open("net.cpp", "w").write("\n".join(lines) + "\n")
    cmd = [cc] + flags + (["/nologo", "/c", "net.cpp", "/Fonet.obj"] if msvc else ["-c", "net.cpp", "-o", "net.o"])
    t = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=LIMIT)
        print(f"  {n:4d} gates ({6 * n:5d} flops)  {time.time() - t:8.2f} s{'' if r.returncode == 0 else '  FAILED'}", flush=True)
    except subprocess.TimeoutExpired:
        print(f"  {n:4d} gates ({6 * n:5d} flops)  > {LIMIT} s (stopped)", flush=True)
        break
for f in ("net.cpp", "net.o", "net.obj"):
    if os.path.exists(f):
        os.remove(f)
