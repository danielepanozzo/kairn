#!/bin/sh
# run.sh COMPILER FLAGS...: compile time and object size of client.cpp for the three inlining policies.
for calls in 1 16 64; do
  python3 gen_synth.py $calls | sed 's/^/# /'
  for mode in 0 1 2; do
    case $mode in 0) name="out of line (noinline) ";; 1) name="plain inline            ";; 2) name="forced inline           ";; esac
    start=$(python3 -c 'import time; print(time.time())')
    "$@" -DSYNTH_INLINE=$mode -c client.cpp -o client.o 2>/dev/null || { echo "  $name  FAILED"; continue; }
    python3 -c "import time, os, sys; print('  $name  %6.2f s   object %8d bytes' % (time.time() - $start, os.path.getsize('client.o')))"
  done
done
rm -f client.o
