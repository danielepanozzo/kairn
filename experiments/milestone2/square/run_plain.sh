#!/bin/sh
# run_plain.sh OUTDIR CXX [EXTRA_FLAGS]: square_plain.cpp with CXX at -O1, -O2 and -O3 under each
# contraction setting (the compiler's default, off, on, fast), with EXTRA_FLAGS (for example
# "-mavx2 -mfma"); one line per build that names each expression that differed, with its count.
# Writes OUTDIR/plain-CXX-FLAGS.txt (the full output of every build) and prints the summary.
out=$1; cxx=$2; extra=${3:-}
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$out"
tag=$(echo "$cxx $extra" | tr ' /=' '___')
log="$out/plain-$tag.txt"
: > "$log"
for lvl in -O1 -O2 -O3; do
  for c in default off on fast; do
    copt=""
    [ $c = default ] || copt="-ffp-contract=$c"
    exe="$out/square_plain-$$"
    if ! $cxx -std=c++20 $lvl $copt $extra -o "$exe" "$here/square_plain.cpp" >> "$log" 2>&1; then
      echo "$cxx $extra $lvl $c: does not compile"
      continue
    fi
    echo "== $cxx $extra $lvl $c" >> "$log"
    "$exe" 20000 > "$exe.out" 2>&1
    cat "$exe.out" >> "$log"
    echo "$cxx $extra $lvl $c: $(grep 'differs in' "$exe.out" | grep -v 'differs in      0' | sed 's/  */ /g; s/ differs in / /; s/ of 20000//' | tr '\n' ';')"
    rm -f "$exe" "$exe.out"
  done
done
