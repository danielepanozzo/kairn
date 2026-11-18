#!/bin/sh
# The contraction matrix on macOS arm64 (Apple clang, Homebrew GCC).
for c in off on fast; do ./run.sh "apple-clang arm64 -O2 -ffp-contract=$c" clang++ -std=c++20 -O2 -ffp-contract=$c; done
./run.sh "apple-clang arm64 -O0 -ffp-contract=fast" clang++ -std=c++20 -O0 -ffp-contract=fast
./run.sh "apple-clang arm64 -O3 -ffp-contract=fast -frounding-math" clang++ -std=c++20 -O3 -ffp-contract=fast -frounding-math
for c in off fast; do ./run.sh "gcc-16 arm64 -O2 -ffp-contract=$c" g++-16 -std=c++20 -O2 -ffp-contract=$c; done
./run.sh "gcc-16 arm64 -O3 -frounding-math (default contract=fast)" g++-16 -std=c++20 -O3 -frounding-math
