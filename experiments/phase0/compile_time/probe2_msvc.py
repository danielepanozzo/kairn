#!/usr/bin/env python3
"""probe2_msvc.py [COMPILER FLAGS...]: which code shape makes the compiler slow on a 141-gate
network? The same gates are emitted in seven shapes, each compiled with a 30 s limit.
Default compiler: cl /O2."""
import os, random, subprocess, sys, time
cmdline = sys.argv[1:] or ["cl", "/nologo", "/std:c++20", "/EHsc", "/O2", "/arch:AVX2"]
msvc = os.path.basename(cmdline[0]).lower() in ("cl", "cl.exe")
N = 141
def gates(w, decl):
    random.seed(1)
    out = []
    for g in range(N):
        i, j = random.sample(range(16), 2)
        out += [f"    {decl} s{g} = {w[i]} + {w[j]}; {decl} c{g} = s{g} - {w[i]};",
                f"    {decl} e{g} = ({w[i]} - (s{g} - c{g})) + ({w[j]} - c{g});"]
        w[i], w[j] = f"s{g}", f"e{g}"
    return out
ptr = lambda: [f"a[{i}]" for i in range(8)] + [f"b[{i}]" for i in range(8)]
mem = lambda: [f"a.limb[{i}]" for i in range(8)] + [f"b.limb[{i}]" for i in range(8)]
def shape(name):
    if name == "A plain function, pointer operands":
        w = ptr(); body = gates(w, "const double")
        return ["void net(const double *a, const double *b, double *out) {"] + body + [f"    out[{i}] = {w[i]};" for i in range(8)] + ["}"]
    if name == "B template, pointer operands":
        w = ptr(); body = gates(w, "const T")
        return ["template <class T> void net(const T *a, const T *b, T *out) {"] + body + [f"    out[{i}] = {w[i]};" for i in range(8)] + ["}", "void use(const double *a, const double *b, double *o) { net<double>(a, b, o); }"]
    if name == "F template, pointer operands, locals declared T (not const T)":
        w = ptr(); body = gates(w, "T")
        return ["template <class T> void net(const T *a, const T *b, T *out) {"] + body + [f"    out[{i}] = {w[i]};" for i in range(8)] + ["}", "void use(const double *a, const double *b, double *o) { net<double>(a, b, o); }"]
    if name == "G template, pointer operands, locals declared const auto":
        w = ptr(); body = gates(w, "const auto")
        return ["template <class T> void net(const T *a, const T *b, T *out) {"] + body + [f"    out[{i}] = {w[i]};" for i in range(8)] + ["}", "void use(const double *a, const double *b, double *o) { net<double>(a, b, o); }"]
    if name == "C template, struct operands by reference, pointer result":
        w = mem(); body = gates(w, "const T")
        return ["template <class T> struct X8 { T limb[8]; };", "template <class T> void net(const X8<T> &a, const X8<T> &b, T *out) {"] + body + [f"    out[{i}] = {w[i]};" for i in range(8)] + ["}", "void use(const X8<double> &a, const X8<double> &b, double *o) { net(a, b, o); }"]
    if name == "D template, struct operands, struct returned by braces":
        w = mem(); body = gates(w, "const T")
        return ["template <class T> struct X8 { T limb[8]; };", "template <class T> X8<T> net(const X8<T> &a, const X8<T> &b) {"] + body + ["    return {{" + ", ".join(w[:8]) + "}};", "}", "X8<double> use(const X8<double> &a, const X8<double> &b) { return net(a, b); }"]
    if name == "E as D, two declarators per statement (gen_synth.py's style)":
        w = mem(); random.seed(1); body = []
        for g in range(N):
            i, j = random.sample(range(16), 2)
            body += [f"    const T s{g} = {w[i]} + {w[j]}, c{g} = s{g} - {w[i]};", f"    const T e{g} = ({w[i]} - (s{g} - c{g})) + ({w[j]} - c{g});"]
            w[i], w[j] = f"s{g}", f"e{g}"
        return ["template <class T> struct X8 { T limb[8]; };", "template <class T> X8<T> net(const X8<T> &a, const X8<T> &b) {"] + body + ["    return {{" + ", ".join(w[:8]) + "}};", "}", "X8<double> use(const X8<double> &a, const X8<double> &b) { return net(a, b); }"]
for name in ["A plain function, pointer operands", "B template, pointer operands", "F template, pointer operands, locals declared T (not const T)",
             "G template, pointer operands, locals declared const auto", "C template, struct operands by reference, pointer result",
             "D template, struct operands, struct returned by braces", "E as D, two declarators per statement (gen_synth.py's style)"]:
    open("shape.cpp", "w").write("\n".join(shape(name)) + "\n")
    cmd = cmdline + (["/c", "shape.cpp", "/Foshape.obj"] if msvc else ["-c", "shape.cpp", "-o", "shape.o"])
    t = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"  {name:62s} {time.time() - t:6.2f} s{'' if r.returncode == 0 else '  FAILED'}", flush=True)
    except subprocess.TimeoutExpired:
        print(f"  {name:62s} > 30 s (stopped)", flush=True)
for f in ("shape.cpp", "shape.o", "shape.obj"):
    if os.path.exists(f):
        os.remove(f)
