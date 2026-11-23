#!/bin/sh
# run_flags.sh OUTDIR INCLUDE CXX [EXTRA_FLAGS]: for each flag set that lets a compiler drop the
# guard without contraction being the cause (-fno-signed-zeros, -fassociative-math,
# -funsafe-math-optimizations, -ffast-math; each alone and with -ffp-contract=fast), at -O2:
# whether the headers refuse it, what kairn::self_test() says, and which forms of square_plain.cpp
# and square_kairn.cpp differ (and which violate their claim). One line per flag set.
out=$1; inc=$2; cxx=$3; extra=${4:-}
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$out"
tag=$(echo "$cxx $extra" | tr ' /=' '___')
for flags in "-fno-signed-zeros" "-fno-signed-zeros -ffp-contract=fast" "-fassociative-math" \
             "-fassociative-math -fno-signed-zeros -fno-trapping-math" "-funsafe-math-optimizations" \
             "-funsafe-math-optimizations -ffp-contract=fast" "-ffast-math"; do
  exe="$out/flags-$tag-$$"
  if $cxx -std=c++20 -O2 -DNDEBUG $flags $extra -I"$inc" -o "$exe" "$here/self_test.cpp" > "$exe.log" 2>&1; then
    headers="accepted"
    st=$("$exe")
  else
    headers="refused: $(grep -m1 -o '#error[^"]*"[^"]*"\|error: "[^"]*"\|Kairn does not work with [^:]*' "$exe.log" | head -1)"
    st="-"
  fi
  plain="does not compile"
  if $cxx -std=c++20 -O2 $flags $extra -o "$exe" "$here/square_plain.cpp" >> "$exe.log" 2>&1; then
    plain=$("$exe" 20000 | grep 'differs in' | grep -v 'differs in      0' | sed 's/  */ /g; s/ differs in / /; s/ of 20000//' | tr '\n' ';')
  fi
  kairn="-"
  if [ "$headers" = accepted ]; then
    if $cxx -std=c++20 -O2 -DNDEBUG $flags $extra -I"$inc" -o "$exe" "$here/square_kairn.cpp" >> "$exe.log" 2>&1; then
      "$exe" 4000 > "$exe.out"
      python3 "$here/check.py" < "$exe.out" > "$exe.check"
      kairn="differ: $(grep 'differs in' "$exe.out" | grep -v 'differs in     0' | awk '{sub(/\.[a-z]*$/, "", $1); print $1 "/" $2}' | uniq | tr '\n' ' '); violate: $(grep VIOLATES "$exe.check" | awk '{sub(/\.[a-z]*$/, "", $1); print $1 "/" $2}' | uniq | tr '\n' ' ')"
    else
      kairn="does not compile"
    fi
  fi
  echo "$cxx $extra [$flags]: headers $headers | $st | plain: ${plain:-none} | kairn: $kairn"
  rm -f "$exe" "$exe.log" "$exe.out" "$exe.check"
done
