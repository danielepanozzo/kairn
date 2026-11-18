#!/bin/sh
# run.sh COMPILER FLAGS...: build constexpr_test.cpp and run it; prints the verdict line.
tmp="${TMPDIR:-/tmp}/kairn-ce.$$"
printf '== %s\n' "$*"
if "$@" constexpr_test.cpp -o "$tmp" 2>"$tmp.err"; then "$tmp" | tail -2; else echo "   COMPILE FAILED"; grep -m4 -E "error" "$tmp.err" | sed 's/^/   /'; fi
rm -f "$tmp" "$tmp.err"
