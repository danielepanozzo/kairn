#!/bin/sh
# run_boundary.sh OUTDIR INCLUDE TESTS CXX [EXTRA_FLAGS]: the four boundary tests of the library
# (TESTS is tests/api of a tree: boundary.cpp, boundary_packed.cpp, boundary_batch.cpp,
# boundary_ball_vector.cpp) built against the headers in INCLUDE as the test suite builds
# api.boundary.*: -O2 with NDEBUG, under each contraction setting, in the native and the scalar form
# of Packed, run with --expect none --factor none (every form agrees with the rounded product).
# One line per build: pass, or fail with the lines of the forms that differ. For a candidate repair
# of the guard, and as a control with the headers as they are.
out=$1; inc=$2; tests=$3; cxx=$4; extra=${5:-}
mkdir -p "$out"
for t in boundary boundary_packed boundary_batch boundary_ball_vector; do
  for form in native scalar; do
    fopt=""
    [ $form = scalar ] && fopt="-DKAIRN_PACKED_FORM=KAIRN_PACKED_FORM_SCALAR"
    for c in default off on fast; do
      copt=""
      [ $c = default ] || copt="-ffp-contract=$c"
      exe="$out/bt-$$"
      if ! $cxx -std=c++20 -O2 -DNDEBUG $copt $fopt $extra -I"$inc" -o "$exe" "$tests/$t.cpp" > "$exe.log" 2>&1; then
        echo "$cxx $extra $t $form $c: does not compile"; head -5 "$exe.log"; continue
      fi
      "$exe" --expect none --factor none > "$exe.log" 2>&1
      st=$?
      if [ $st -eq 0 ]; then
        echo "$cxx $extra $t $form $c: pass"
      else
        echo "$cxx $extra $t $form $c: FAIL ($st)"
        grep -v 'differs in *0 ' "$exe.log" | grep 'differs in' | head -20
      fi
      rm -f "$exe" "$exe.log"
    done
  done
done
