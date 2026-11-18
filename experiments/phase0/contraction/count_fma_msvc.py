#!/usr/bin/env python3
"""count_fma_msvc.py LISTING.asm: fused instructions per mul_* function in an MSVC /Fa listing."""
import re, sys
fn, counts = None, {}
for line in open(sys.argv[1], errors="replace"):
    m = re.match(r"^(\S*mul_[a-z_]+\S*)\s+PROC", line)
    if m:
        fn = re.search(r"mul_[a-z_]+", m.group(1)).group(0)
        counts.setdefault(fn, 0)
    elif re.match(r"^\S+\s+ENDP", line):
        fn = None
    elif fn and re.search(r"\bvfn?m(add|sub)\d*[sp][sd]\b", line):
        counts[fn] += 1
for f in sorted(counts):
    print(f"  {f:22s} fused instructions: {counts[f]}")
