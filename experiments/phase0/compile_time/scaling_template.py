#!/usr/bin/env python3
"""scaling_template.py [COMPILER FLAGS...]: compile time of an N-gate network written as a
function TEMPLATE (`const T` locals), for growing N, 30 s limit. scaling.py is the same network
as a plain function. N = 6, 16, 31 are the published 2-, 3- and 4-limb additions."""
import os, random, subprocess, sys, time
cmdline = sys.argv[1:] or ["cl", "/nologo", "/std:c++20", "/EHsc", "/O2", "/arch:AVX2"]
msvc = os.path.basename(cmdline[0]).lower() in ("cl", "cl.exe")
for n in (4, 6, 8, 10, 12, 14, 16, 20, 24, 31, 48):
    random.seed(1)
    w = [f"a[{i}]" for i in range(8)] + [f"b[{i}]" for i in range(8)]
    lines = ["template <class T> void net(const T *a, const T *b, T *out) {"]
    for g in range(n):
        i, j = random.sample(range(16), 2)
        lines += [f"    const T s{g} = {w[i]} + {w[j]}; const T c{g} = s{g} - {w[i]};",
                  f"    const T e{g} = ({w[i]} - (s{g} - c{g})) + ({w[j]} - c{g});"]
        w[i], w[j] = f"s{g}", f"e{g}"
    lines += [f"    out[{i}] = {w[i]};" for i in range(8)] + ["}", "void use(const double *a, const double *b, double *o) { net<double>(a, b, o); }"]
    open("tmpl.cpp", "w").write("\n".join(lines) + "\n")
    cmd = cmdline + (["/c", "tmpl.cpp", "/Fotmpl.obj"] if msvc else ["-c", "tmpl.cpp", "-o", "tmpl.o"])
    t = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"  {n:3d} gates  {time.time() - t:7.2f} s{'' if r.returncode == 0 else '  FAILED'}", flush=True)
    except subprocess.TimeoutExpired:
        print(f"  {n:3d} gates  > 30 s (stopped)", flush=True)
        break
for f in ("tmpl.cpp", "tmpl.o", "tmpl.obj"):
    if os.path.exists(f):
        os.remove(f)
