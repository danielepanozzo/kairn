// What tests/api/arrays_exact.py checks in exact rational arithmetic, written as lines of text:
//
//   arrays_exact bounds    the bounds as functions of the length (kairn::traits<X>::sum(n), dot(n)),
//                          for float and double, one and two limbs, at the lengths where the count
//                          given to the kernel is converted to T exactly and where it is rounded
//                          up (around 2^p, and beyond), at powers of two, near the largest
//                          std::size_t and at random lengths: one line per bound,
//                          "sum|dot K T n unit tiny", the limbs as C99 hexadecimal literals.
//
// Every value is printed as a double (a float converts exactly), so that the checker reads it with
// float.fromhex.
#include <kairn/kairn.hpp>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>
#include <type_traits>
#include <vector>

namespace {

void put(double v) {
    if (v != v) {
        std::printf(" nan");
    } else if (v == std::numeric_limits<double>::infinity()) {
        std::printf(" inf");
    } else {
        std::printf(" %a", v);
    }
}

// SplitMix64.
struct Random {
    std::uint64_t state;
    std::uint64_t next() {
        std::uint64_t z = (state += 0x9e3779b97f4a7c15u);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9u;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebu;
        return z ^ (z >> 31);
    }
};

template <class T, int K>
void bounds(const char* type, const std::vector<std::uint64_t>& lengths) {
    using X = std::conditional_t<K == 1, T, kairn::Expansion<T, 2>>;
    for (std::uint64_t n64 : lengths) {
        if (n64 > std::uint64_t(std::numeric_limits<std::size_t>::max())) continue;
        const std::size_t n = std::size_t(n64);
        const kairn::Bound<T> s = kairn::traits<X>::sum(n), d = kairn::traits<X>::dot(n);
        std::printf("sum %d %s %llu", K, type, static_cast<unsigned long long>(n64));
        put(double(s.unit));
        put(double(s.tiny));
        std::printf("\ndot %d %s %llu", K, type, static_cast<unsigned long long>(n64));
        put(double(d.unit));
        put(double(d.tiny));
        std::printf("\n");
    }
}

int run_bounds() {
    std::vector<std::uint64_t> lengths = {0, 1, 2, 3, 4, 5, 7, 8, 9, 1000, 1001};
    // Around 2^p, where the conversion of n - 1 and n to T starts to round, for both limb types,
    // and around a few multiples above.
    for (int p : {24, 53}) {
        for (int k = 0; k < 4; ++k) {
            const std::uint64_t base = (std::uint64_t{1} << (p + k)) * (k == 3 ? 3 : 1);
            for (std::uint64_t d = 0; d < 6; ++d) {
                lengths.push_back(base + d);
                lengths.push_back(base - d);
            }
        }
    }
    // Every power of two, and its neighbors.
    for (int e = 4; e < 64; ++e) {
        const std::uint64_t b = std::uint64_t{1} << e;
        lengths.push_back(b - 1);
        lengths.push_back(b);
        lengths.push_back(b + 1);
    }
    // The largest lengths, whose count rounds up to 2^64.
    for (std::uint64_t d = 0; d < 4; ++d) lengths.push_back(~std::uint64_t{0} - d);
    lengths.push_back(~std::uint64_t{0} - (std::uint64_t{1} << 11));
    lengths.push_back(~std::uint64_t{0} - (std::uint64_t{1} << 40));
    // Random lengths, log-uniform.
    Random r{0x6b61697266};
    for (int i = 0; i < 400; ++i) {
        const int e = int(r.next() % 64);
        lengths.push_back(r.next() >> (63 - e));
    }
    bounds<double, 1>("binary64", lengths);
    bounds<double, 2>("binary64", lengths);
    bounds<float, 1>("binary32", lengths);
    bounds<float, 2>("binary32", lengths);
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc == 2 && std::strcmp(argv[1], "bounds") == 0) return run_bounds();
    std::fprintf(stderr, "usage: arrays_exact bounds\n");
    return 2;
}
