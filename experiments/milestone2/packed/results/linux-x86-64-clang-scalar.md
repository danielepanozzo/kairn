Machine: Linux x86-64, AMD EPYC 7452 (Zen 2), one logical CPU pinned, its SMT sibling idle
Compiler: Ubuntu clang version 18.1.3 (1ubuntu1); -std=c++20 -O2 -DNDEBUG -ffp-contract=off -mfma
KAIRN_PACKED_FORM 2; 11 samples, median (spread: median over minimum)

| T | k | W | n | bytes | plain T, ns/elem | Expansion loop, ns/elem | Packed loop, ns/elem | Expansion / Packed | agreement |
|---|---|---|---|---|---|---|---|---|---|
| double | 1 | 1 | 512 | 0.00819 MB | 0.862 (1.01) | 0.860 (1.01) | - | - | - |
| double | 2 | 1 | 512 | 0.0164 MB | 0.861 (1.01) | 10.311 (1.00) | 10.363 (1.00) | 1.00 | 0.0e+00 |
| float | 1 | 1 | 512 | 0.0041 MB | 0.861 (1.01) | 0.865 (1.00) | - | - | - |
| float | 2 | 1 | 512 | 0.00819 MB | 0.863 (1.00) | 12.807 (1.01) | 12.798 (1.00) | 1.00 | 0.0e+00 |
| double | 1 | 1 | 8388608 | 134 MB | 1.007 (1.01) | 1.004 (1.00) | - | - | - |
| double | 2 | 1 | 8388608 | 268 MB | 1.240 (1.01) | 10.578 (1.00) | 10.637 (1.00) | 0.99 | 0.0e+00 |
| float | 1 | 1 | 8388608 | 67.1 MB | 0.939 (1.01) | 0.941 (1.01) | - | - | - |
| float | 2 | 1 | 8388608 | 134 MB | 0.937 (1.01) | 12.911 (1.00) | 12.946 (1.00) | 1.00 | 0.0e+00 |

largest spread: 1.011
