#!/bin/sh
# count_fma.sh BINARY: fused multiply-add instructions per mul_* function (x86-64 or AArch64).
# The source asks for 3 (reference, textbook, scoped*, simd: one in TwoProd, two cross terms)
# or 5 (opaque*, simdopaque: the two plain products are FMAs with a zero addend).
if command -v objdump >/dev/null 2>&1 && objdump --version 2>/dev/null | grep -q GNU; then D="objdump -d --no-show-raw-insn"; else D="otool -tV"; fi
$D "$1" | awk '
  /^[0-9a-f]* *<[^>]*mul_[a-z]*/ || /^_?_Z[0-9]*mul_[a-z]*/ || /^__Z[0-9]*mul_/ { fn=$0; sub(/.*mul_/, "mul_", fn); sub(/[^a-z_].*/, "", fn); next }
  /^[0-9a-f]* *<|^_[A-Za-z_]/ { fn="" }
  fn != "" && /(vfn?m(add|sub)[0-9]*[sp][sd]|[ \t]fn?m(add|sub)[ \t]|[ \t]fml[as][. \t])/ { n[fn]++ }
  fn != "" { seen[fn]=1 }
  END { for (f in seen) printf "  %-22s fused instructions: %d\n", f, n[f]+0 }' | sort
