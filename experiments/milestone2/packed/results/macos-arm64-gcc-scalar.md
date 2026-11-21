Machine: macOS arm64, Apple M3 Max, performance cores (QoS user-interactive), no affinity
Compiler: g++-16 (Homebrew GCC 16.2.0) 16.2.0; -std=c++20 -O2 -DNDEBUG -ffp-contract=off -DKAIRN_PACKED_FORM=KAIRN_PACKED_FORM_SCALAR
KAIRN_PACKED_FORM 2; 11 samples, median (spread: median over minimum)

| T | k | W | n | bytes | plain T, ns/elem | Expansion loop, ns/elem | Packed loop, ns/elem | Expansion / Packed | agreement |
|---|---|---|---|---|---|---|---|---|---|
| double | 1 | 1 | 512 | 0.00819 MB | 0.703 (1.02) | 0.710 (1.02) | 0.693 (1.01) | 1.02 | 0.0e+00 |
| double | 2 | 1 | 512 | 0.0164 MB | 0.689 (1.06) | 8.756 (1.07) | 8.966 (1.03) | 0.98 | 0.0e+00 |
| float | 1 | 1 | 512 | 0.0041 MB | 0.710 (1.05) | 0.714 (1.10) | 0.702 (1.02) | 1.02 | 0.0e+00 |
| float | 2 | 1 | 512 | 0.00819 MB | 0.722 (1.03) | 9.031 (1.02) | 9.142 (1.02) | 0.99 | 0.0e+00 |
| double | 1 | 1 | 8388608 | 134 MB | 0.821 (1.03) | 0.807 (1.03) | 0.824 (1.04) | 0.98 | 0.0e+00 |
| double | 2 | 1 | 8388608 | 268 MB | 0.729 (1.01) | 8.864 (1.07) | 8.853 (1.02) | 1.00 | 0.0e+00 |
| float | 1 | 1 | 8388608 | 67.1 MB | 0.802 (1.03) | 0.793 (1.03) | 0.768 (1.04) | 1.03 | 0.0e+00 |
| float | 2 | 1 | 8388608 | 134 MB | 0.761 (1.03) | 8.987 (1.02) | 8.920 (1.02) | 1.01 | 0.0e+00 |

largest spread: 1.102
