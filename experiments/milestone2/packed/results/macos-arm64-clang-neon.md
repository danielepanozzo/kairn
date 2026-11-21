Machine: macOS arm64, Apple M3 Max, performance cores (QoS user-interactive), no affinity
Compiler: Apple clang version 21.0.0 (clang-2100.4.1.1); -std=c++20 -O2 -DNDEBUG -ffp-contract=off 
KAIRN_PACKED_FORM 8; 11 samples, median (spread: median over minimum)

| T | k | W | n | bytes | plain T, ns/elem | Expansion loop, ns/elem | Packed loop, ns/elem | Expansion / Packed | agreement |
|---|---|---|---|---|---|---|---|---|---|
| double | 1 | 2 | 512 | 0.00819 MB | 0.637 (1.01) | 0.643 (1.08) | 0.341 (1.02) | 1.89 | 2.0e-16 |
| double | 2 | 2 | 512 | 0.0164 MB | 0.638 (1.02) | 8.729 (1.01) | 5.328 (1.02) | 1.64 | 0.0e+00 |
| float | 1 | 4 | 512 | 0.0041 MB | 0.593 (1.01) | 0.594 (1.09) | 0.131 (1.01) | 4.54 | 1.1e-07 |
| float | 2 | 4 | 512 | 0.00819 MB | 0.545 (1.00) | 8.840 (1.01) | 2.782 (1.03) | 3.18 | 8.3e-15 |
| double | 1 | 2 | 8388608 | 134 MB | 0.792 (1.03) | 0.860 (1.04) | 0.385 (1.04) | 2.23 | 3.6e-14 |
| double | 2 | 2 | 8388608 | 268 MB | 0.815 (1.04) | 9.050 (1.02) | 5.522 (1.02) | 1.64 | 0.0e+00 |
| float | 1 | 4 | 8388608 | 67.1 MB | 0.856 (1.06) | 0.818 (1.06) | 0.191 (1.06) | 4.28 | 2.8e-05 |
| float | 2 | 4 | 8388608 | 134 MB | 0.824 (1.05) | 8.650 (1.07) | 2.740 (1.04) | 3.16 | 3.0e-10 |

largest spread: 1.093
