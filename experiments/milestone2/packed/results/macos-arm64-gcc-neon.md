Machine: macOS arm64, Apple M3 Max, performance cores (QoS user-interactive), no affinity
Compiler: g++-16 (Homebrew GCC 16.2.0) 16.2.0; -std=c++20 -O2 -DNDEBUG -ffp-contract=off 
KAIRN_PACKED_FORM 8; 11 samples, median (spread: median over minimum)

| T | k | W | n | bytes | plain T, ns/elem | Expansion loop, ns/elem | Packed loop, ns/elem | Expansion / Packed | agreement |
|---|---|---|---|---|---|---|---|---|---|
| double | 1 | 2 | 512 | 0.00819 MB | 0.704 (1.08) | 0.689 (1.01) | 0.298 (1.01) | 2.31 | 2.0e-16 |
| double | 2 | 2 | 512 | 0.0164 MB | 0.699 (1.02) | 8.771 (1.06) | 5.412 (1.01) | 1.62 | 0.0e+00 |
| float | 1 | 4 | 512 | 0.0041 MB | 0.703 (1.02) | 0.686 (1.02) | 0.137 (1.01) | 5.02 | 1.1e-07 |
| float | 2 | 4 | 512 | 0.00819 MB | 0.689 (1.02) | 8.990 (1.05) | 2.758 (1.05) | 3.26 | 8.3e-15 |
| double | 1 | 2 | 8388608 | 134 MB | 0.835 (1.03) | 0.848 (1.04) | 0.404 (1.02) | 2.10 | 3.6e-14 |
| double | 2 | 2 | 8388608 | 268 MB | 0.817 (1.09) | 9.096 (1.07) | 5.233 (1.06) | 1.74 | 0.0e+00 |
| float | 1 | 4 | 8388608 | 67.1 MB | 0.790 (1.03) | 0.798 (1.01) | 0.192 (1.01) | 4.16 | 2.8e-05 |
| float | 2 | 4 | 8388608 | 134 MB | 0.799 (1.02) | 8.877 (1.02) | 2.624 (1.04) | 3.38 | 3.0e-10 |

largest spread: 1.088
