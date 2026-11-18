#!/bin/sh
# macros.sh COMPILER [BASE FLAGS...]: which predefined macros reveal each floating-point flag.
cc="$1"; shift
pat='FAST_MATH|FINITE_MATH|ASSOCIATIVE|RECIPROCAL|SIGNED_ZEROS|TRAPPING|ROUNDING_MATH|__FMA__|FP_FAST_FMA |FLT_EVAL_METHOD__ |__ARM_FEATURE_FMA|__NO_MATH_ERRNO__|__SUPPORT_SNAN__'
for f in "" "-ffast-math" "-Ofast" "-funsafe-math-optimizations" "-fassociative-math -fno-signed-zeros -fno-trapping-math" "-fno-signed-zeros" "-freciprocal-math" "-ffinite-math-only" "-frounding-math" "-ffp-contract=fast" "-ffp-contract=off" "-ffp-model=fast" "-ffp-model=aggressive" "-ffp-model=strict"; do
  out=$(echo | "$cc" "$@" -std=c++20 $f -dM -E -x c++ - 2>/dev/null) || { printf '%-62s: (flag not accepted)\n' "$f"; continue; }
  printf '%-62s: ' "${f:-(none)}"; echo "$out" | grep -E "$pat" | sed 's/#define //' | sort | tr '\n' ';'; echo
done
