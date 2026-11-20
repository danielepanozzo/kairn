#!/bin/sh
# Runs every experiment of this directory and records its output under results/.
# From the repository root: sh experiments/milestone2/run_all.sh
# Needs Python 3 and nothing else; about twenty minutes on one core, most of it in directed_2.py
# and convert.py. Each script exits with a failed assertion if a statement does not hold.
set -e
here=$(dirname "$0")
mkdir -p "$here/results"
for s in constants rules_report rational batch accumulator ballvector bv_proposals bv_conv scaling enclosure_1 enclosure_2 \
         interval_2 interval_1 directed_1 convert directed_2; do
    echo "$s"
    python3 "$here/$s.py" > "$here/results/$s.txt" 2>&1
done
echo "all experiments ran; outputs in $here/results"
