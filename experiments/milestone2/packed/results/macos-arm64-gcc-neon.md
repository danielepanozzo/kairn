Machine: macOS arm64, Apple M3 Max, performance cores (QoS user-interactive), no affinity
Compiler: g++-16 (Homebrew GCC 16.2.0) 16.2.0; -std=c++20 -O2 -DNDEBUG -ffp-contract=off 
KAIRN_PACKED_FORM 8; 11 samples, median (spread: median over minimum)

| T | k | W | n | bytes | plain T, ns/elem | Expansion loop, ns/elem | Packed loop, ns/elem | Expansion / Packed | agreement |
|---|---|---|---|---|---|---|---|---|---|
| double | 1 | 2 | 512 | 0.00819 MB | 0.648 (1.00) | 0.648 (1.00) | - | - | - |
| double | 2 | 2 | 512 | 0.0164 MB | 0.648 (1.00) | 8.296 (1.01) | 4.970 (1.00) | 1.67 | 0.0e+00 |
| float | 1 | 4 | 512 | 0.0041 MB | 0.649 (1.00) | 0.650 (1.00) | - | - | - |
| float | 2 | 4 | 512 | 0.00819 MB | 0.656 (1.02) | 8.295 (1.00) | 2.491 (1.00) | 3.33 | 8.3e-15 |
| double | 1 | 2 | 8388608 | 134 MB | 0.755 (1.02) | 0.753 (1.02) | - | - | - |
| double | 2 | 2 | 8388608 | 268 MB | 0.752 (1.02) | 8.372 (1.00) | 5.023 (1.00) | 1.67 | 0.0e+00 |
| float | 1 | 4 | 8388608 | 67.1 MB | 0.757 (1.03) | 0.749 (1.01) | - | - | - |
| float | 2 | 4 | 8388608 | 134 MB | 0.747 (1.02) | 8.368 (1.00) | 2.507 (1.00) | 3.34 | 3.0e-10 |

largest spread: 1.027
