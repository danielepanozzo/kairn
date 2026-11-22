// Exact sums of floating-point numbers for the benchmark of Milestone 2 (bench/README.md, "Milestone
// 2", third part): the reference of the checks of the functions on arrays (m2_batch.cpp) and of the
// measurements of accuracy (m2_accuracy.cpp). Not part of the library, not verified; written for
// this harness only.
//
// Exact is a fixed-point number of 2240 bits, bit 0 of value 2^-1120: every double, subnormal or
// not, and every sum of up to 2^30 doubles below 2^1023 in magnitude is an integer of it. It holds 70
// signed digits of 32 bits in 64-bit words, carried lazily (every 2^28 additions and before a read),
// so that adding a double costs three additions of integers. A product x y is added exactly as its
// two parts p = RN(x y) and e = fma(x, y, -p), which is exact unless e underflows: the data of the
// harness keep products far from the subnormal range.
#pragma once

#include <cmath>
#include <cstdint>
#include <cstring>

namespace kairn_bench::exact {

class Exact {
    static constexpr int kDigits = 70;   // 32-bit digits: 2240 bits
    static constexpr int kBias = 1120;   // bit 0 is 2^-1120
    std::int64_t d_[kDigits] = {};
    long pending_ = 0;

    void carry() {
        for (int k = 0; k + 1 < kDigits; ++k) {
            const std::int64_t c = d_[k] >> 32;   // floor division by 2^32
            d_[k] -= c * (std::int64_t(1) << 32);
            d_[k + 1] += c;
        }
        pending_ = 0;
    }

public:
    void clear() {
        std::memset(d_, 0, sizeof d_);
        pending_ = 0;
    }
    // Adds v exactly (v finite).
    void add(double v) {
        if (v == 0) return;
        std::uint64_t b;
        std::memcpy(&b, &v, 8);
        const bool neg = (b >> 63) != 0;
        const int be = int((b >> 52) & 0x7ff);
        std::uint64_t m = b & 0x000fffffffffffffu;
        int e;   // the exponent of the last bit of m
        if (be == 0) {
            e = -1074;
        } else {
            m |= std::uint64_t(1) << 52;
            e = be - 1075;
        }
        const int pos = e + kBias;
        const int k = pos >> 5, s = pos & 31;
        // m << s has at most 53 + 31 = 84 bits: three digits, from the two halves of m (each shifted
        // half below 2^63), the middle digit below 2^33 (the lazy carry allows it).
        const std::uint64_t ml = (m & 0xffffffffu) << s, mh = (m >> 32) << s;
        const std::int64_t c0 = std::int64_t(ml & 0xffffffffu);
        const std::int64_t c1 = std::int64_t((ml >> 32) + (mh & 0xffffffffu));
        const std::int64_t c2 = std::int64_t(mh >> 32);
        if (neg) {
            d_[k] -= c0;
            d_[k + 1] -= c1;
            d_[k + 2] -= c2;
        } else {
            d_[k] += c0;
            d_[k + 1] += c1;
            d_[k + 2] += c2;
        }
        if (++pending_ >= (long(1) << 28)) carry();
    }
    void add(float v) { add(double(v)); }
    // Adds the product x y exactly (as p + e, p = RN(x y), e = fma(x, y, -p)).
    void add_product(double x, double y) {
        const double p = x * y;
        add(p);
        add(std::fma(x, y, -p));
    }
    void add_product(float x, float y) { add(double(x) * double(y)); }   // exact in double
    void add(Exact o) {
        o.carry();
        carry();
        for (int k = 0; k < kDigits; ++k) d_[k] += o.d_[k];
        ++pending_;
    }
    void negate() {
        for (int k = 0; k < kDigits; ++k) d_[k] = -d_[k];
    }
    // The value rounded to double (to within a relative 2^-60 or so: the three leading digits of
    // the magnitude, then one rounding): enough for an error measured to a few digits.
    double value() {
        carry();
        Exact t = *this;
        double sign = 1;
        if (t.d_[kDigits - 1] < 0) {
            t.negate();
            t.carry();
            sign = -1;
        }
        int top = kDigits - 1;
        while (top >= 0 && t.d_[top] == 0) --top;
        if (top < 0) return 0.0;
        long double v = 0;
        for (int k = top; k >= 0 && k >= top - 3; --k)
            v += std::ldexp(static_cast<long double>(t.d_[k]), 32 * k - kBias);
        return sign * double(v);
    }
    bool is_zero() {
        carry();
        for (int k = 0; k < kDigits; ++k)
            if (d_[k] != 0) return false;
        return true;
    }
};

}  // namespace kairn_bench::exact
