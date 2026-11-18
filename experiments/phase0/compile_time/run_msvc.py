#!/usr/bin/env python3
"""run_msvc.py: the same measurement as run.sh with cl (run inside a Visual Studio developer prompt)."""
import os, subprocess, sys, time
names = ["out of line (noinline) ", "plain inline            ", "forced inline           "]
for calls in (1, 16, 64):
    print("# " + subprocess.run([sys.executable, "gen_synth.py", str(calls)], capture_output=True, text=True).stdout.strip())
    for mode in (0, 1, 2):
        t = time.time()
        r = subprocess.run(["cl", "/nologo", "/std:c++20", "/EHsc", "/O2", "/arch:AVX2", f"/DSYNTH_INLINE={mode}", "/c", "client.cpp", "/Foclient.obj"], capture_output=True, text=True)
        if r.returncode:
            print(f"  {names[mode]}  FAILED: {r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ''}")
        else:
            print(f"  {names[mode]}  {time.time() - t:6.2f} s   object {os.path.getsize('client.obj'):8d} bytes")
