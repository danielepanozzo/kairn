Machine: macOS arm64, Apple M3 Max, performance cores (QoS user-interactive), no affinity
Compiler: Apple clang version 21.0.0 (clang-2100.4.1.1); -std=c++20 -O2 -DNDEBUG -ffp-contract=off -DKAIRN_PACKED_FORM=KAIRN_PACKED_FORM_SCALAR
KAIRN_PACKED_FORM 2; 11 samples, median (spread: median over minimum)

| T | k | W | n | bytes | plain T, ns/elem | Expansion loop, ns/elem | Packed loop, ns/elem | Expansion / Packed | agreement |
|---|---|---|---|---|---|---|---|---|---|
| double | 1 | 1 | 512 | 0.00819 MB | 0.598 (1.00) | 0.594 (1.00) | - | - | - |
| double | 2 | 1 | 512 | 0.0164 MB | 0.595 (1.00) | 8.219 (1.01) | 8.166 (1.00) | 1.01 | 0.0e+00 |
| float | 1 | 1 | 512 | 0.0041 MB | 0.558 (1.00) | 0.555 (1.00) | - | - | - |
| float | 2 | 1 | 512 | 0.00819 MB | 0.557 (1.00) | 8.186 (1.00) | 8.193 (1.00) | 1.00 | 0.0e+00 |
| double | 1 | 1 | 8388608 | 134 MB | 0.770 (1.00) | 0.770 (1.00) | - | - | - |
| double | 2 | 1 | 8388608 | 268 MB | 0.770 (1.00) | 8.249 (1.00) | 8.356 (1.01) | 0.99 | 0.0e+00 |
| float | 1 | 1 | 8388608 | 67.1 MB | 0.757 (1.00) | 0.761 (1.01) | - | - | - |
| float | 2 | 1 | 8388608 | 134 MB | 0.760 (1.00) | 8.255 (1.00) | 8.286 (1.00) | 1.00 | 0.0e+00 |

largest spread: 1.009
