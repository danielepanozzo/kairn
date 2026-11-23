#!/bin/sh
# run_kairn.sh OUTDIR INCLUDE CXX [EXTRA_FLAGS]: square_kairn.cpp against the headers in INCLUDE,
# with CXX at -O1, -O2 and -O3 under each contraction setting (default, off, on, fast), with
# EXTRA_FLAGS and NDEBUG; each run judged by check.py. One line per build: the forms whose results
# differed (with the squares in place against rounded first), and of those the ones whose result
# violates the claim. Writes OUTDIR/kairn-TAG.txt (every output and verdict).
out=$1; inc=$2; cxx=$3; extra=${4:-}
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$out"
tag=$(echo "$cxx $extra" | tr ' /=' '___')
log="$out/kairn-$tag.txt"
: > "$log"
for lvl in -O1 -O2 -O3; do
  for c in default off on fast; do
    copt=""
    [ $c = default ] || copt="-ffp-contract=$c"
    exe="$out/square_kairn-$tag-$$"
    if ! $cxx -std=c++20 -DNDEBUG $lvl $copt $extra -I"$inc" -o "$exe" "$here/square_kairn.cpp" >> "$log" 2>&1; then
      echo "$cxx $extra $lvl $c: does not compile"
      continue
    fi
    "$exe" "${CASES:-4000}" > "$exe.out" 2>&1
    python3 "$here/check.py" < "$exe.out" > "$exe.check"
    echo "== $cxx $extra $lvl $c" >> "$log"
    grep -v '^CASE' "$exe.out" >> "$log"
    cat "$exe.check" >> "$log"
    # A form counts once, whatever the family of operands in which it differs or violates.
    differ=$(grep 'differs in' "$exe.out" | grep -v 'differs in     0' | awk '{sub(/\.[a-z]*$/, "", $1); print $1 "/" $2}' | uniq | tr '\n' ' ')
    bad=$(grep 'VIOLATES' "$exe.check" | awk '{sub(/\.[a-z]*$/, "", $1); print $1 "/" $2}' | uniq | tr '\n' ' ')
    echo "$cxx $extra $lvl $c: differ: ${differ:-none}; violate: ${bad:-none}"
    rm -f "$exe" "$exe.out" "$exe.check"
  done
done
