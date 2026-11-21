Machine: macOS arm64, Apple M3 Max, performance cores (QoS user-interactive), no affinity
Compiler: g++-16 (Homebrew GCC 16.2.0) 16.2.0; -std=c++20 -O2 -DNDEBUG -ffp-contract=off -DKAIRN_PACKED_FORM=KAIRN_PACKED_FORM_SCALAR
KAIRN_PACKED_FORM 2; 11 samples, median (spread: median over minimum)

| T | k | W | n | bytes | plain T, ns/elem | Expansion loop, ns/elem | Packed loop, ns/elem | Expansion / Packed | agreement |
|---|---|---|---|---|---|---|---|---|---|
| double | 1 | 1 | 512 | 0.00819 MB | 0.648 (1.00) | 0.647 (1.00) | - | - | - |
| double | 2 | 1 | 512 | 0.0164 MB | 0.647 (1.00) | 8.259 (1.00) | 8.302 (1.01) | 0.99 | 0.0e+00 |
| float | 1 | 1 | 512 | 0.0041 MB | 0.648 (1.00) | 0.648 (1.00) | - | - | - |
| float | 2 | 1 | 512 | 0.00819 MB | 0.648 (1.00) | 8.289 (1.00) | 8.332 (1.00) | 0.99 | 0.0e+00 |
| double | 1 | 1 | 8388608 | 134 MB | 0.750 (1.01) | 0.745 (1.02) | - | - | - |
| double | 2 | 1 | 8388608 | 268 MB | 0.752 (1.02) | 8.410 (1.01) | 8.334 (1.00) | 1.01 | 0.0e+00 |
| float | 1 | 1 | 8388608 | 67.1 MB | 0.749 (1.03) | 0.753 (1.01) | - | - | - |
| float | 2 | 1 | 8388608 | 134 MB | 0.751 (1.02) | 8.373 (1.00) | 8.442 (1.01) | 0.99 | 0.0e+00 |

largest spread: 1.032
