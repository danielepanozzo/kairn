### Precision and full-precision range

| T | k | bits (k·p) | decimal digits | full precision for \|x\| ≥ (gradual underflow) | (subnormals flushed) | bits at \|x\| = 1e-30 (gradual) | (flushed) |
|---|---|---|---|---|---|---|---|
| double | 1 | 53 | 16.0 | 2^-1022 ≈ 2.2e-308 | 2^-1022 ≈ 2.2e-308 | 53 | 53 |
| double | 2 | 106 | 31.9 | 2^-968 ≈ 4.0e-292 | 2^-916 ≈ 1.8e-276 | 106 | 106 |
| double | 3 | 159 | 47.9 | 2^-915 ≈ 3.6e-276 | 2^-863 ≈ 1.6e-260 | 159 | 159 |
| double | 4 | 212 | 63.8 | 2^-862 ≈ 3.3e-260 | 2^-810 ≈ 1.5e-244 | 212 | 212 |
| double | 8 | 424 | 127.6 | 2^-650 ≈ 2.1e-196 | 2^-598 ≈ 9.6e-181 | 424 | 424 |
| float | 1 | 24 | 7.2 | 2^-126 ≈ 1.2e-38 | 2^-126 ≈ 1.2e-38 | 24 | 24 |
| float | 2 | 48 | 14.4 | 2^-101 ≈ 3.9e-31 | 2^-78 ≈ 3.3e-24 | 48 | 26 |
| float | 3 | 72 | 21.7 | 2^-77 ≈ 6.6e-24 | 2^-54 ≈ 5.6e-17 | 49 | 26 |
| float | 4 | 96 | 28.9 | 2^-53 ≈ 1.1e-16 | 2^-30 ≈ 9.3e-10 | 49 | 26 |

### Other thresholds

| T | u = 2^-p | smallest subnormal η | smallest normal λ | largest Ω | TwoProd error-free for ab = 0 or \|ab\| ≥ | limbs that fit above η at \|x\| = 1 |
|---|---|---|---|---|---|---|
| double | 2^-53 | 2^-1074 ≈ 4.9e-324 | 2^-1022 ≈ 2.2e-308 | (2 − 2^-52)·2^1023 ≈ 1.8e+308 | 2^-969 ≈ 2.0e-292 | 20.3 |
| float | 2^-24 | 2^-149 ≈ 1.4e-45 | 2^-126 ≈ 1.2e-38 | (2 − 2^-23)·2^127 ≈ 3.4e+38 | 2^-102 ≈ 2.0e-31 | 6.2 |

### Runtime k: largest useful k at a given magnitude (gradual underflow)

| T | \|x\| ≈ 1e+300 / 1e+30 | \|x\| = 1 | \|x\| ≈ 1e-10 | \|x\| ≈ 1e-100 / 1e-20 |
|---|---|---|---|---|
| double | 39 | 20 | 19 | 13 |
| float | 10 | 6 | 4 | 3 |
