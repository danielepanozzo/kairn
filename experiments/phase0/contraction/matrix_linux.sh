#!/bin/sh
# The contraction matrix on Linux x86-64 (GCC 13, Clang 18).
G="--gcc-install-dir=/usr/lib/gcc/x86_64-linux-gnu/13"
for c in off fast; do ./run.sh "gcc-13 x86-64 -O2 -mavx2 -mfma -ffp-contract=$c" g++ -std=c++20 -O2 -mavx2 -mfma -ffp-contract=$c; done
./run.sh "gcc-13 x86-64 -O0 -mavx2 -mfma (default contract=fast)" g++ -std=c++20 -O0 -mavx2 -mfma
./run.sh "gcc-13 x86-64 -O3 -march=native -frounding-math (default contract=fast)" g++ -std=c++20 -O3 -march=native -frounding-math
for c in off on fast; do ./run.sh "clang-18 x86-64 -O2 -mavx2 -mfma -ffp-contract=$c" clang++ $G -std=c++20 -O2 -mavx2 -mfma -ffp-contract=$c; done
./run.sh "clang-18 x86-64 -O3 -march=native -ffp-contract=fast -frounding-math" clang++ $G -std=c++20 -O3 -march=native -ffp-contract=fast -frounding-math
