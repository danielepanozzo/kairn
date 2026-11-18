#!/bin/sh
# run.sh LABEL COMPILER FLAGS...: build contraction.cpp, count fused instructions, check results.
label="$1"; shift
tmp="${TMPDIR:-/tmp}/kairn-e1.$$"
if "$@" -o "$tmp" contraction.cpp 2>"$tmp.err"; then
  echo "== $label"; ./count_fma.sh "$tmp"; "$tmp" 20000 | python3 check.py
else
  echo "== $label: COMPILE FAILED"; head -5 "$tmp.err"
fi
rm -f "$tmp" "$tmp.err"
