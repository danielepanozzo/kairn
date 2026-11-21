Machine: Linux x86-64, AMD EPYC 7452 (Zen 2), one logical CPU pinned, its SMT sibling idle
Compiler: g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0; -std=c++20 -O2 -DNDEBUG -ffp-contract=off -mavx2 -mfma
KAIRN_PACKED_FORM 4; 11 samples, median (spread: median over minimum)

| T | k | W | n | bytes | plain T, ns/elem | Expansion loop, ns/elem | Packed loop, ns/elem | Expansion / Packed | agreement |
|---|---|---|---|---|---|---|---|---|---|
| double | 1 | 4 | 512 | 0.00819 MB | 0.877 (1.00) | 0.877 (1.00) | 0.227 (1.02) | 3.86 | 3.2e-16 |
| double | 2 | 4 | 512 | 0.0164 MB | 0.876 (1.00) | 10.346 (1.00) | 3.083 (1.00) | 3.36 | 0.0e+00 |
| float | 1 | 8 | 512 | 0.0041 MB | 0.878 (1.00) | 0.876 (1.00) | 0.116 (1.01) | 7.56 | 4.3e-07 |
| float | 2 | 8 | 512 | 0.00819 MB | 0.877 (1.00) | 10.360 (1.00) | 1.676 (1.00) | 6.18 | 6.2e-15 |
| double | 1 | 4 | 8388608 | 134 MB | 1.070 (1.02) | 1.080 (1.01) | 0.754 (1.01) | 1.43 | 2.0e-13 |
| double | 2 | 4 | 8388608 | 268 MB | 1.425 (1.03) | 10.831 (1.00) | 3.666 (1.03) | 2.95 | 0.0e+00 |
| float | 1 | 8 | 8388608 | 67.1 MB | 0.953 (1.00) | 0.953 (1.01) | 0.375 (1.00) | 2.54 | 3.2e-05 |
| float | 2 | 8 | 8388608 | 134 MB | 0.931 (1.00) | 10.364 (1.00) | 1.599 (1.00) | 6.48 | 3.3e-12 |

largest spread: 1.032
