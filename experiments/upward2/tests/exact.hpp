// Exact arithmetic for the checks of the experimental two-limb interval rounded upward
// (experiments/upward2/README.md). EXPERIMENTAL, NOT VERIFIED, not part of the library; written for
// these checks only, compiled as ordinary code and run under rounding to nearest.
//
// Exact is a fixed-point number of 4480 bits, bit 0 of value 2^-2240: every double, every product of
// two doubles (from 2^-2148 to below 2^2048) and every sum of a few of them is an integer of it. It
// holds 140 signed digits of 32 bits in 64-bit words, carried lazily and with truncating division,
// so that every digit stays in (-2^32, 2^32) after a carry: the sign of the number is then the sign
// of its most significant nonzero digit, and only the digits that were touched need carrying or
// reading. Products are exact: the 53-bit significands are multiplied as integers.
#pragma once

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace x2test {

__extension__ using u128 = unsigned __int128;   // an extension of GCC and Clang: no -Wpedantic warning

class Exact {
    static constexpr int kDigits = 140;
    static constexpr int kBias = 2240;   // bit 0 is 2^-2240
    std::int64_t d_[kDigits];
    int lo_ = kDigits, hi_ = -1;   // the digits touched
    long pending_ = 0;

    static void split(double v, std::uint64_t& m, int& e, bool& neg) {
        std::uint64_t b;
        std::memcpy(&b, &v, 8);
        neg = (b >> 63) != 0;
        const int be = int((b >> 52) & 0x7ff);
        m = b & 0x000fffffffffffffu;
        if (be == 0) {
            e = -1074;
        } else {
            m |= std::uint64_t(1) << 52;
            e = be - 1075;
        }
    }
    void touch(int k) {
        if (k < lo_) lo_ = k;
        if (k > hi_) hi_ = k;
    }
    void put(int k, std::int64_t c, bool neg) {
        if (k >= kDigits) {
            if (c == 0) return;
            std::fprintf(stderr, "Exact: out of range\n");
            std::abort();
        }
        d_[k] += neg ? -c : c;
        touch(k);
    }

public:
    Exact() { std::memset(d_, 0, sizeof d_); }
    void clear() {
        for (int k = lo_; k <= hi_; ++k) d_[k] = 0;
        lo_ = kDigits;
        hi_ = -1;
        pending_ = 0;
    }
    // Adds (or subtracts) mag * 2^(bit - kBias), mag < 2^118.
    void add_bits(u128 mag, int bit, bool neg) {
        if (mag == 0) return;
        if (bit < 0) {
            std::fprintf(stderr, "Exact: below the range (bit %d)\n", bit);
            std::abort();
        }
        const int k = bit >> 5, s = bit & 31;
        const std::uint64_t lo = std::uint64_t(mag), hi = std::uint64_t(mag >> 64);
        const u128 a = u128(lo) << s;   // < 2^95: digits k, k + 1, k + 2
        const u128 b = u128(hi) << s;   // < 2^85 (hi < 2^54): digits k + 2, k + 3, k + 4
        put(k, std::int64_t(std::uint64_t(a) & 0xffffffffu), neg);
        put(k + 1, std::int64_t(std::uint64_t(a >> 32) & 0xffffffffu), neg);
        put(k + 2, std::int64_t(std::uint64_t(a >> 64) & 0xffffffffu) + std::int64_t(std::uint64_t(b) & 0xffffffffu), neg);
        put(k + 3, std::int64_t(std::uint64_t(b >> 32) & 0xffffffffu), neg);
        put(k + 4, std::int64_t(std::uint64_t(b >> 64) & 0xffffffffu), neg);
        if (++pending_ >= (long(1) << 27)) carry();
    }
    // Adds v exactly (v finite).
    void add(double v) {
        if (v == 0) return;
        std::uint64_t m;
        int e;
        bool neg;
        split(v, m, e, neg);
        add_bits(m, e + kBias, neg);
    }
    void sub(double v) { add(-v); }
    // Adds the product x y exactly (x, y finite).
    void add_product(double x, double y, bool negate = false) {
        if (x == 0 || y == 0) return;
        std::uint64_t mx, my;
        int ex, ey;
        bool nx, ny;
        split(x, mx, ex, nx);
        split(y, my, ey, ny);
        add_bits(u128(mx) * my, ex + ey + kBias, (nx != ny) != negate);
    }
    // Adds the product x y z exactly (finite; the product not below 2^-2240).
    void add_product3(double x, double y, double z, bool negate = false) {
        if (x == 0 || y == 0 || z == 0) return;
        std::uint64_t mx, my, mz;
        int ex, ey, ez;
        bool nx, ny, nz;
        split(x, mx, ex, nx);
        split(y, my, ey, ny);
        split(z, mz, ez, nz);
        const u128 p = u128(mx) * my;   // < 2^106
        const bool neg = ((nx != ny) != nz) != negate;
        const int bit = ex + ey + ez + kBias;
        add_bits(u128(std::uint64_t(p)) * mz, bit, neg);              // < 2^117
        add_bits(u128(std::uint64_t(p >> 64)) * mz, bit + 64, neg);   // < 2^96
    }
    void add(const Exact& o, bool negate = false) {
        Exact t = o;
        t.carry();
        for (int k = t.lo_; k <= t.hi_; ++k) {
            if (t.d_[k] == 0) continue;
            d_[k] += negate ? -t.d_[k] : t.d_[k];
            touch(k);
        }
        if (++pending_ >= (long(1) << 27)) carry();
    }
    // Every digit into (-2^32, 2^32), the carries truncated toward zero.
    void carry() {
        if (hi_ < 0) return;
        for (int k = lo_; k < kDigits - 1; ++k) {
            const std::int64_t c = d_[k] / (std::int64_t(1) << 32);
            if (c != 0) {
                d_[k] -= c * (std::int64_t(1) << 32);
                d_[k + 1] += c;
                touch(k + 1);
            } else if (k >= hi_) {
                break;
            }
        }
        pending_ = 0;
    }
    int sign() {
        carry();
        for (int k = hi_; k >= lo_; --k)
            if (d_[k] != 0) return d_[k] > 0 ? 1 : -1;
        return 0;
    }
    // Every digit of the sign of the number (borrows propagated upward), so that the leading digits
    // give its value: after carry() alone a positive number may have a leading digit 1 and negative
    // digits below it, and then its leading digits say little about it.
    void canon() {
        const int s = sign();
        if (s == 0) return;
        const std::int64_t base = std::int64_t(1) << 32;
        for (int k = lo_; k < hi_; ++k) {
            if (s > 0 && d_[k] < 0) {
                d_[k] += base;
                d_[k + 1] -= 1;
            } else if (s < 0 && d_[k] > 0) {
                d_[k] -= base;
                d_[k + 1] += 1;
            }
        }
    }
    // The value, to about 2^-60 relative (the leading digits), for reports.
    double value() {
        canon();
        int top = hi_;
        while (top >= lo_ && d_[top] == 0) --top;
        if (top < lo_) return 0.0;
        long double v = 0;
        for (int k = top; k >= lo_ && k >= top - 3; --k) v += std::ldexp(static_cast<long double>(d_[k]), 32 * k - kBias);
        return double(v);
    }
    // This number times v exactly (v finite; no bit of the result below 2^-2240).
    void mul(double v) {
        carry();
        Exact r;
        if (v != 0 && hi_ >= 0) {
            std::uint64_t m;
            int e;
            bool neg;
            split(v, m, e, neg);
            for (int k = lo_; k <= hi_; ++k) {
                const std::int64_t dk = d_[k];
                if (dk == 0) continue;
                const bool dneg = dk < 0;
                const u128 mag = u128(std::uint64_t(dneg ? -dk : dk)) * m;   // < 2^85
                r.add_bits(mag, 32 * k + e, dneg != neg);
            }
        }
        *this = r;
    }
};

// The least number of the format at least v, RU(v) (+inf above the largest finite number, -MAX below
// -MAX, -0 for a v in (-2^-1074, 0)): an approximation from value(), moved by exact comparisons until
// it is at least v and its predecessor is below v. For the checks of the four-limb experiment
// (experiments/upward4/tests), which make their operands and the best four-limb bounds with it.
inline double ru(const Exact& v0) {
    constexpr double inf = HUGE_VAL, mx = 1.7976931348623157e308;
    Exact v = v0, t;
    const int s = v.sign();
    if (s == 0) return 0.0;
    auto cmp = [&](double c) {   // sign(v - c), c finite
        t = v;
        t.sub(c);
        return t.sign();
    };
    double c = v.value();
    if (!(c < mx)) c = mx;
    if (!(c > -mx)) c = -mx;
    if (cmp(-mx) <= 0) return -mx;
    while (cmp(c) > 0) {
        if (c == mx) return inf;
        c = std::nextafter(c, inf);
    }
    for (;;) {
        const double p = std::nextafter(c, -inf);
        if (p < -mx || cmp(p) > 0) break;
        c = p;
    }
    return c;
}

// The best upper quadruple of v: z0 = RU(v), z1 = RU(v - z0), z2 = RU(v - z0 - z1), z3 = RU(v - z0 - z1
// - z2), each limb RU of the exact rest below the limbs before it (the invariant of the four-limb
// experiment in its strong form); (+inf, 0, 0, 0) above the largest finite number, and zero later
// limbs after a first limb +-MAX. Returns whether it is exact (z0 + z1 + z2 + z3 = v).
inline bool upper4(const Exact& v, double* z) {
    constexpr double mx = 1.7976931348623157e308;
    Exact r = v;
    for (int i = 0; i < 4; ++i) {
        z[i] = ru(r);
        if (i == 0 && (z[0] == HUGE_VAL || std::fabs(z[0]) == mx)) {
            z[1] = z[2] = z[3] = 0.0;
            return false;
        }
        r.sub(z[i]);
    }
    for (int i = 0; i < 4; ++i) z[i] += 0.0;   // no -0 limb
    return r.sign() == 0;
}

}  // namespace x2test
