Machine: Linux x86-64, AMD EPYC 7452 (Zen 2), one logical CPU pinned, its SMT sibling idle
Compiler: Ubuntu clang version 18.1.3 (1ubuntu1); -std=c++20 -O2 -DNDEBUG -ffp-contract=off -mavx2 -mfma
KAIRN_PACKED_FORM 4; 11 samples, median (spread: median over minimum)

| T | k | W | n | bytes | plain T, ns/elem | Expansion loop, ns/elem | Packed loop, ns/elem | Expansion / Packed | agreement |
|---|---|---|---|---|---|---|---|---|---|
| double | 1 | 4 | 512 | 0.00819 MB | 0.864 (1.01) | 0.859 (1.00) | 0.203 (1.00) | 4.24 | 2.0e-16 |
| double | 2 | 4 | 512 | 0.0164 MB | 0.858 (1.00) | 10.305 (1.00) | 2.890 (1.00) | 3.57 | 0.0e+00 |
| float | 1 | 8 | 512 | 0.0041 MB | 0.861 (1.00) | 0.862 (1.00) | 0.098 (1.01) | 8.80 | 2.1e-07 |
| float | 2 | 8 | 512 | 0.00819 MB | 0.860 (1.01) | 12.834 (1.00) | 1.613 (1.00) | 7.96 | 1.2e-14 |
| double | 1 | 4 | 8388608 | 134 MB | 1.069 (1.00) | 1.073 (1.01) | 0.768 (1.01) | 1.40 | 1.9e-16 |
| double | 2 | 4 | 8388608 | 268 MB | 1.285 (1.02) | 10.595 (1.01) | 3.224 (1.01) | 3.29 | 0.0e+00 |
| float | 1 | 8 | 8388608 | 67.1 MB | 0.936 (1.01) | 0.931 (1.01) | 0.380 (1.01) | 2.45 | 3.5e-05 |
| float | 2 | 8 | 8388608 | 134 MB | 0.991 (1.01) | 12.948 (1.00) | 1.564 (1.01) | 8.28 | 2.1e-10 |

largest spread: 1.021
