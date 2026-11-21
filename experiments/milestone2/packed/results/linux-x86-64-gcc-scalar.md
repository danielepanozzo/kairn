Machine: Linux x86-64, AMD EPYC 7452 (Zen 2), one logical CPU pinned, its SMT sibling idle
Compiler: g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0; -std=c++20 -O2 -DNDEBUG -ffp-contract=off -mfma
KAIRN_PACKED_FORM 2; 11 samples, median (spread: median over minimum)

| T | k | W | n | bytes | plain T, ns/elem | Expansion loop, ns/elem | Packed loop, ns/elem | Expansion / Packed | agreement |
|---|---|---|---|---|---|---|---|---|---|
| double | 1 | 1 | 512 | 0.00819 MB | 0.883 (1.01) | 0.875 (1.00) | 0.906 (1.02) | 0.97 | 0.0e+00 |
| double | 2 | 1 | 512 | 0.0164 MB | 0.881 (1.00) | 10.327 (1.00) | 10.399 (1.00) | 0.99 | 0.0e+00 |
| float | 1 | 1 | 512 | 0.0041 MB | 0.877 (1.00) | 0.882 (1.00) | 0.887 (1.00) | 0.99 | 0.0e+00 |
| float | 2 | 1 | 512 | 0.00819 MB | 0.877 (1.00) | 10.372 (1.00) | 10.430 (1.00) | 0.99 | 0.0e+00 |
| double | 1 | 1 | 8388608 | 134 MB | 1.157 (1.02) | 1.138 (1.02) | 1.158 (1.01) | 0.98 | 0.0e+00 |
| double | 2 | 1 | 8388608 | 268 MB | 1.431 (1.02) | 10.924 (1.00) | 10.838 (1.00) | 1.01 | 0.0e+00 |
| float | 1 | 1 | 8388608 | 67.1 MB | 0.982 (1.01) | 0.984 (1.00) | 0.990 (1.01) | 0.99 | 0.0e+00 |
| float | 2 | 1 | 8388608 | 134 MB | 0.966 (1.01) | 10.483 (1.00) | 10.512 (1.00) | 1.00 | 0.0e+00 |

largest spread: 1.024
