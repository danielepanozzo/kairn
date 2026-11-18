#!/bin/sh
# run.sh COMPILER FLAGS...: compile k1.cpp to assembly and compare the plain and k = 1 functions.
tmp="${TMPDIR:-/tmp}/kairn-k1.$$.s"
printf '== %s\n' "$*"
"$@" -S k1.cpp -o "$tmp" && ./compare.py "$tmp"
rm -f "$tmp"
