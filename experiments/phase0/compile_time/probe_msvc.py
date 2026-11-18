#!/usr/bin/env python3
"""probe_msvc.py: which part of gen_synth.py's output makes cl /O2 run for more than 20 minutes?
Compiles variations of the 1-call-site client with a 60 s limit each."""
import re, subprocess, sys, time
subprocess.run([sys.executable, "gen_synth.py", "1"], capture_output=True)
hpp, cpp = open("synth.hpp").read(), open("client.cpp").read()
add_fn = hpp[hpp.index("template <class T> SYNTH_FN X8<T> add8"):hpp.index("template <class T> SYNTH_FN X8<T> mul8")]
def trial(label, header, client, flags):
    open("synth.hpp", "w").write(header)
    open("client.cpp", "w").write(client)
    t = time.time()
    try:
        r = subprocess.run(["cl", "/nologo", "/std:c++20", "/EHsc", "/arch:AVX2", "/DSYNTH_INLINE=0", "/c", "client.cpp", "/Foclient.obj"] + flags, capture_output=True, text=True, timeout=60)
        print(f"  {label:58s} {time.time() - t:7.2f} s{'' if r.returncode == 0 else '  FAILED'}", flush=True)
    except subprocess.TimeoutExpired:
        print(f"  {label:58s} > 60 s (stopped)", flush=True)
only_add = cpp.replace("s = add8(s, mul8(x[0], y[0]));", "s = add8(x[0], y[0]);")
only_mul = cpp.replace("s = add8(s, mul8(x[0], y[0]));", "s = mul8(x[0], y[0]);")
trial("as generated, /O2", hpp, cpp, ["/O2"])
trial("as generated, /O1", hpp, cpp, ["/O1"])
trial("as generated, /Od", hpp, cpp, ["/Od"])
trial("only add8 (141 gates), /O2", hpp, only_add, ["/O2"])
trial("only mul8 (28 TwoProd + 8 products + 213 gates), /O2", hpp, only_mul, ["/O2"])
trial("only mul8, operands copied to locals first, /O2",
      hpp.replace("template <class T> SYNTH_FN X8<T> mul8(const X8<T> &a, const X8<T> &b) {", "template <class T> SYNTH_FN X8<T> mul8(X8<T> a, X8<T> b) {"), only_mul, ["/O2"])
trial("only mul8, /O2 /fp:strict", hpp, only_mul, ["/O2", "/fp:strict"])
