Machine: Linux x86-64, AMD EPYC 7452 (Zen 2), one logical CPU pinned, its SMT sibling idle
Compiler: g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0; -std=c++20 -O2 -DNDEBUG -ffp-contract=off -mfma
KAIRN_PACKED_FORM 2; 11 samples, median (spread: median over minimum)

| T | k | W | n | bytes | plain T, ns/elem | Expansion loop, ns/elem | Packed loop, ns/elem | Expansion / Packed | agreement |
|---|---|---|---|---|---|---|---|---|---|
| double | 1 | 1 | 512 | 0.00819 MB | 0.881 (1.01) | 0.875 (1.00) | - | - | - |
| double | 2 | 1 | 512 | 0.0164 MB | 0.873 (1.00) | 10.344 (1.00) | 10.362 (1.00) | 1.00 | 0.0e+00 |
| float | 1 | 1 | 512 | 0.0041 MB | 0.873 (1.00) | 0.874 (1.00) | - | - | - |
| float | 2 | 1 | 512 | 0.00819 MB | 0.879 (1.00) | 10.364 (1.00) | 10.368 (1.00) | 1.00 | 0.0e+00 |
| double | 1 | 1 | 8388608 | 134 MB | 1.081 (1.01) | 1.088 (1.02) | - | - | - |
| double | 2 | 1 | 8388608 | 268 MB | 1.421 (1.03) | 10.703 (1.00) | 10.731 (1.00) | 1.00 | 0.0e+00 |
| float | 1 | 1 | 8388608 | 67.1 MB | 0.955 (1.01) | 0.969 (1.02) | - | - | - |
| float | 2 | 1 | 8388608 | 134 MB | 0.943 (1.02) | 10.375 (1.00) | 10.418 (1.00) | 1.00 | 0.0e+00 |

largest spread: 1.034
