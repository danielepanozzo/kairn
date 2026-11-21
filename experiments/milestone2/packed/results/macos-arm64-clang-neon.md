Machine: macOS arm64, Apple M3 Max, performance cores (QoS user-interactive), no affinity
Compiler: Apple clang version 21.0.0 (clang-2100.4.1.1); -std=c++20 -O2 -DNDEBUG -ffp-contract=off 
KAIRN_PACKED_FORM 8; 11 samples, median (spread: median over minimum)

| T | k | W | n | bytes | plain T, ns/elem | Expansion loop, ns/elem | Packed loop, ns/elem | Expansion / Packed | agreement |
|---|---|---|---|---|---|---|---|---|---|
| double | 1 | 2 | 512 | 0.00819 MB | 0.596 (1.03) | 0.594 (1.03) | - | - | - |
| double | 2 | 2 | 512 | 0.0164 MB | 0.594 (1.00) | 8.209 (1.01) | 5.029 (1.00) | 1.63 | 0.0e+00 |
| float | 1 | 4 | 512 | 0.0041 MB | 0.558 (1.00) | 0.561 (1.00) | - | - | - |
| float | 2 | 4 | 512 | 0.00819 MB | 0.563 (1.02) | 8.214 (1.01) | 2.555 (1.00) | 3.22 | 8.3e-15 |
| double | 1 | 2 | 8388608 | 134 MB | 0.770 (1.00) | 0.769 (1.00) | - | - | - |
| double | 2 | 2 | 8388608 | 268 MB | 0.769 (1.00) | 8.261 (1.00) | 5.085 (1.01) | 1.62 | 0.0e+00 |
| float | 1 | 4 | 8388608 | 67.1 MB | 0.760 (1.00) | 0.760 (1.00) | - | - | - |
| float | 2 | 4 | 8388608 | 134 MB | 0.756 (1.00) | 8.256 (1.00) | 2.571 (1.00) | 3.21 | 3.0e-10 |

largest spread: 1.031
