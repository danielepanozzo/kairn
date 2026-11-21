Machine: Linux x86-64, AMD EPYC 7452 (Zen 2), one logical CPU pinned, its SMT sibling idle
Compiler: Ubuntu clang version 18.1.3 (1ubuntu1); -std=c++20 -O2 -DNDEBUG -ffp-contract=off -mavx2 -mfma
KAIRN_PACKED_FORM 4; 11 samples, median (spread: median over minimum)

| T | k | W | n | bytes | plain T, ns/elem | Expansion loop, ns/elem | Packed loop, ns/elem | Expansion / Packed | agreement |
|---|---|---|---|---|---|---|---|---|---|
| double | 1 | 4 | 512 | 0.00819 MB | 0.859 (1.00) | 0.858 (1.00) | - | - | - |
| double | 2 | 4 | 512 | 0.0164 MB | 0.857 (1.00) | 10.301 (1.00) | 2.883 (1.00) | 3.57 | 0.0e+00 |
| float | 1 | 8 | 512 | 0.0041 MB | 0.861 (1.00) | 0.864 (1.01) | - | - | - |
| float | 2 | 8 | 512 | 0.00819 MB | 0.860 (1.00) | 12.822 (1.00) | 1.602 (1.00) | 8.00 | 1.2e-14 |
| double | 1 | 4 | 8388608 | 134 MB | 1.037 (1.01) | 1.038 (1.01) | - | - | - |
| double | 2 | 4 | 8388608 | 268 MB | 1.251 (1.01) | 10.514 (1.00) | 3.210 (1.00) | 3.27 | 0.0e+00 |
| float | 1 | 8 | 8388608 | 67.1 MB | 0.963 (1.02) | 0.959 (1.01) | - | - | - |
| float | 2 | 8 | 8388608 | 134 MB | 0.933 (1.01) | 12.937 (1.00) | 1.519 (1.00) | 8.52 | 2.1e-10 |

largest spread: 1.020
