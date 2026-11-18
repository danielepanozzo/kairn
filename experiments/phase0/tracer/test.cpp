// The generated C++ on random inputs, printed as hex floats for check.py (exact rationals).
#include <cstdint>
#include <cstdio>
#include <cstring>
#include "out/kernels.hpp"
static std::uint64_t state = 0x9E3779B97F4A7C15ull;
static std::uint64_t next() {
    std::uint64_t z = (state += 0x9E3779B97F4A7C15ull);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
    return z ^ (z >> 31);
}
static double rnd(int lo, int hi) {
    const double m = 1.0 + double(next() >> 12) * 0x1p-52;
    return std::ldexp(next() & 1 ? m : -m, lo + int(next() % std::uint64_t(hi - lo + 1)));
}
int main() {
    for (int i = 0; i < 20000; ++i) {
        // a third of the cases reach into the subnormal range
        const bool tiny = i % 3 == 0;
        volatile double a = tiny ? rnd(-1074, -1000) : rnd(-60, 60), b = tiny ? rnd(-1074, -1000) : rnd(-60, 60);
        double s, e;
        two_sum<double>(a, b, s, e);
        std::printf("two_sum %a %a %a %a\n", (double)a, (double)b, s, e);
        const double hi = std::fabs(a) >= std::fabs(b) ? a : b, lo = std::fabs(a) >= std::fabs(b) ? b : a;
        fast_two_sum<double>(hi, lo, s, e);
        std::printf("fast_two_sum %a %a %a %a\n", hi, lo, s, e);
        volatile double c = tiny ? rnd(-600, -400) : rnd(-60, 60), d = tiny ? rnd(-600, -400) : rnd(-60, 60);
        two_prod<double>(c, d, s, e);
        std::printf("two_prod %a %a %a %a\n", (double)c, (double)d, s, e);
    }
}
