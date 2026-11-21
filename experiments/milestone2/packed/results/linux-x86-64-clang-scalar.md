Machine: Linux x86-64, AMD EPYC 7452 (Zen 2), one logical CPU pinned, its SMT sibling idle
Compiler: Ubuntu clang version 18.1.3 (1ubuntu1); -std=c++20 -O2 -DNDEBUG -ffp-contract=off -mfma
KAIRN_PACKED_FORM 2; 11 samples, median (spread: median over minimum)

| T | k | W | n | bytes | plain T, ns/elem | Expansion loop, ns/elem | Packed loop, ns/elem | Expansion / Packed | agreement |
|---|---|---|---|---|---|---|---|---|---|
| double | 1 | 1 | 512 | 0.00819 MB | 0.859 (1.01) | 0.854 (1.00) | 0.907 (1.01) | 0.94 | 0.0e+00 |
| double | 2 | 1 | 512 | 0.0164 MB | 0.856 (1.00) | 10.306 (1.00) | 10.386 (1.00) | 0.99 | 0.0e+00 |
| float | 1 | 1 | 512 | 0.0041 MB | 0.861 (1.00) | 0.863 (1.01) | 0.938 (1.00) | 0.92 | 0.0e+00 |
| float | 2 | 1 | 512 | 0.00819 MB | 0.861 (1.00) | 12.842 (1.01) | 12.808 (1.00) | 1.00 | 0.0e+00 |
| double | 1 | 1 | 8388608 | 134 MB | 1.004 (1.00) | 1.011 (1.01) | 1.077 (1.01) | 0.94 | 0.0e+00 |
| double | 2 | 1 | 8388608 | 268 MB | 1.285 (1.02) | 10.667 (1.01) | 10.850 (1.00) | 0.98 | 0.0e+00 |
| float | 1 | 1 | 8388608 | 67.1 MB | 0.954 (1.01) | 0.957 (1.02) | 1.022 (1.01) | 0.94 | 0.0e+00 |
| float | 2 | 1 | 8388608 | 134 MB | 0.947 (1.02) | 12.920 (1.00) | 12.922 (1.00) | 1.00 | 0.0e+00 |

largest spread: 1.019
