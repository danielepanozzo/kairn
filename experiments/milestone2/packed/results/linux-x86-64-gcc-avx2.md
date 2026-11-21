Machine: Linux x86-64, AMD EPYC 7452 (Zen 2), one logical CPU pinned, its SMT sibling idle
Compiler: g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0; -std=c++20 -O2 -DNDEBUG -ffp-contract=off -mavx2 -mfma
KAIRN_PACKED_FORM 4; 11 samples, median (spread: median over minimum)

| T | k | W | n | bytes | plain T, ns/elem | Expansion loop, ns/elem | Packed loop, ns/elem | Expansion / Packed | agreement |
|---|---|---|---|---|---|---|---|---|---|
| double | 1 | 4 | 512 | 0.00819 MB | 0.882 (1.00) | 0.879 (1.00) | - | - | - |
| double | 2 | 4 | 512 | 0.0164 MB | 0.879 (1.00) | 10.337 (1.00) | 3.091 (1.00) | 3.34 | 0.0e+00 |
| float | 1 | 8 | 512 | 0.0041 MB | 0.877 (1.00) | 0.879 (1.01) | - | - | - |
| float | 2 | 8 | 512 | 0.00819 MB | 0.879 (1.01) | 10.385 (1.00) | 1.680 (1.00) | 6.18 | 6.2e-15 |
| double | 1 | 4 | 8388608 | 134 MB | 1.165 (1.01) | 1.164 (1.03) | - | - | - |
| double | 2 | 4 | 8388608 | 268 MB | 1.426 (1.03) | 10.676 (1.00) | 3.464 (1.01) | 3.08 | 0.0e+00 |
| float | 1 | 8 | 8388608 | 67.1 MB | 0.931 (1.00) | 0.938 (1.01) | - | - | - |
| float | 2 | 8 | 8388608 | 134 MB | 0.985 (1.01) | 10.446 (1.00) | 1.665 (1.01) | 6.27 | 3.3e-12 |

largest spread: 1.030
