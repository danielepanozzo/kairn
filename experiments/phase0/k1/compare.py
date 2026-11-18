#!/usr/bin/env python3
"""compare.py LISTING.s: are the *_plain and *_k1 functions the same instructions?

Reads an assembly listing (GCC/Clang -S, or MSVC /Fa), keeps the instruction lines of each
function, and compares pairs: "identical" (same lines once labels are anonymized), "same
instructions" (the same multiset of mnemonics: only operand order, register choice or block
order differ), or DIFFERENT with the mnemonics that differ."""
import re, sys
from collections import Counter
text = open(sys.argv[1], errors="replace").read().splitlines()
funcs, cur = {}, None
for line in text:
    line = line.split(";")[0].rstrip() if "PROC" in text[0:1] or sys.argv[1].endswith(".asm") else line.split("//")[0].rstrip()
    m = re.match(r"^_?(?:_Z\w*?|\?)?(\w*?(axpy|dot|horner)_(plain|k1))\w*(?:@@\S*)?\s*(?::|PROC)", line)
    if m:
        cur = m.group(2) + "_" + m.group(3)
        funcs[cur] = []
        continue
    if re.match(r"^\S+\s+ENDP", line) or re.match(r"^\s*\.cfi_endproc", line):
        cur = None
    if cur is None or not line.strip():
        continue
    s = line.strip()
    if s.startswith(".") and not s.endswith(":"):
        continue  # assembler directive
    if re.match(r"^[.\w$@?]+:$", s) or s.startswith("$LN") or s.startswith("$LL"):
        s = "<label>:"
    s = re.sub(r"\.?L[A-Za-z_]*\d+\b|\$L[LN]\d+@\w+|Ltmp\d+|LBB\d+_\d+", "<label>", s)
    s = re.sub(r"\b\w*(axpy|dot|horner)_(plain|k1)\w*", "<self>", s)
    s = re.sub(r"\s+", " ", s)
    funcs[cur].append(s)
ok = True
for name in ("axpy", "dot", "horner"):
    a, b = funcs.get(name + "_plain"), funcs.get(name + "_k1")
    if a is None or b is None:
        print(f"  {name}: functions not found"); ok = False; continue
    ia = [x for x in a if x != "<label>:"]
    ib = [x for x in b if x != "<label>:"]
    ma, mb = Counter(x.split()[0] for x in ia), Counter(x.split()[0] for x in ib)
    if ia == ib:
        verdict = "identical"
    elif ma == mb:
        verdict = "same instructions"
    else:
        ok = False
        only_a, only_b = ma - mb, mb - ma
        verdict = "DIFFERENT: plain has " + (", ".join(f"{n} {m}" for m, n in sorted(only_a.items())) or "nothing") + \
                  " more; k1 has " + (", ".join(f"{n} {m}" for m, n in sorted(only_b.items())) or "nothing") + " more"
    print(f"  {name:7s} plain: {len(ia):3d} instructions   k1: {len(ib):3d} instructions   {verdict}")
sys.exit(0 if ok else 1)
