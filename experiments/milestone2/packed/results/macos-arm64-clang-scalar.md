Machine: macOS arm64, Apple M3 Max, performance cores (QoS user-interactive), no affinity
Compiler: Apple clang version 21.0.0 (clang-2100.4.1.1); -std=c++20 -O2 -DNDEBUG -ffp-contract=off -DKAIRN_PACKED_FORM=KAIRN_PACKED_FORM_SCALAR
KAIRN_PACKED_FORM 2; 11 samples, median (spread: median over minimum)

| T | k | W | n | bytes | plain T, ns/elem | Expansion loop, ns/elem | Packed loop, ns/elem | Expansion / Packed | agreement |
|---|---|---|---|---|---|---|---|---|---|
| double | 1 | 1 | 512 | 0.00819 MB | 0.641 (1.04) | 0.633 (1.02) | 0.626 (1.02) | 1.01 | 0.0e+00 |
| double | 2 | 1 | 512 | 0.0164 MB | 0.619 (1.01) | 8.651 (1.02) | 8.727 (1.02) | 0.99 | 0.0e+00 |
| float | 1 | 1 | 512 | 0.0041 MB | 0.614 (1.02) | 0.607 (1.03) | 0.623 (1.03) | 0.97 | 0.0e+00 |
| float | 2 | 1 | 512 | 0.00819 MB | 0.603 (1.02) | 8.721 (1.07) | 8.774 (1.01) | 0.99 | 0.0e+00 |
| double | 1 | 1 | 8388608 | 134 MB | 0.854 (1.02) | 0.842 (1.02) | 0.859 (1.06) | 0.98 | 0.0e+00 |
| double | 2 | 1 | 8388608 | 268 MB | 0.840 (1.05) | 9.045 (1.04) | 9.131 (1.02) | 0.99 | 0.0e+00 |
| float | 1 | 1 | 8388608 | 67.1 MB | 0.826 (1.01) | 0.843 (1.04) | 0.754 (1.01) | 1.12 | 0.0e+00 |
| float | 2 | 1 | 8388608 | 134 MB | 0.748 (1.00) | 8.733 (1.01) | 8.707 (1.01) | 1.00 | 0.0e+00 |

largest spread: 1.071
