#!/usr/bin/env python3
"""audit.py OUTPUT ALLOWED: every axiom printed by `Print Assumptions` must be on the allow-list.

Reads the output of compiling Audit.v (one block per theorem: either "Closed under the global
context" or "Axioms:" followed by `name : type` entries) and exits non-zero if any axiom,
including the one an Admitted proof leaves behind, is not listed in ALLOWED."""
import re, sys
allowed = {l.strip() for l in open(sys.argv[2]) if l.strip() and not l.startswith("#")}
found, bad = set(), set()
for line in open(sys.argv[1]):
    m = re.match(r"^([A-Za-z_][\w.']*)\s*:", line)
    if m and m.group(1) != "Axioms":
        found.add(m.group(1))
for a in sorted(found):
    ok = a in allowed
    print(f"  {'allowed    ' if ok else 'NOT ALLOWED'}  {a}")
    if not ok:
        bad.add(a)
if not found:
    print("  (closed under the global context: no axioms)")
sys.exit(1 if bad else 0)
