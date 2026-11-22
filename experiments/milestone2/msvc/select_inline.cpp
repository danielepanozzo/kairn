// MSVC 19.52 x64 at /O2 returns wrong values from an inlined function that selects three of its
// by-value struct parameters and returns them in a struct holding an array.
// cl /std:c++20 /O2 select_inline.cpp: prints "0 0 102" (wrong); /O1, /Od, /DNOINLINE: "100 101 102".
// No Kairn header is included. See README.md beside this file.
#include <cstdint>
#include <cstdio>

struct N {
    std::uint64_t m = 0;
    int q = 0;
};
struct result {
    N limb[3];
};

#ifdef NOINLINE
__declspec(noinline)
#endif
inline result fix(N cx0, N cx1, N rx, N cy0, N cy1, N ry, N r, N c0, N c1, bool nx, bool ny) {
    const N ca0 = ny ? c0 : cx0;
    const N ca1 = ny ? c1 : cx1;
    const N ra = ny ? r : rx;
    const N cz0 = nx ? ca0 : cy0;
    const N cz1 = nx ? ca1 : cy1;
    const N rz = nx ? ra : ry;
    return {{cz0, cz1, rz}};
}

inline void kernel(N cx0, N cx1, N rx, N cy0, N cy1, N ry, N& cz0_out, N& cz1_out, N& rz_out) {
    const bool nx = rx.m != 0;
    const bool ny = ry.m != 7;
    if (nx & ny) {
        cz0_out = cy0;
        cz1_out = cy1;
        rz_out = rx;
    } else {
        const result fixed_ = fix(cx0, cx1, rx, cy0, cy1, ry, rx, cy0, cy1, nx, ny);
        cz0_out = fixed_.limb[0];
        cz1_out = fixed_.limb[1];
        rz_out = fixed_.limb[2];
    }
}

using Run = void (*)(const N* in, N* out);
const Run runs[] = {[](const N* in, N* out) { kernel(in[0], in[1], in[2], in[3], in[4], in[5], out[0], out[1], out[2]); }};

int main(int argc, char**) {
    N in[6];
    for (int i = 0; i < 6; ++i) in[i].m = static_cast<std::uint64_t>(99 + i + argc);
    in[5].m = 7;  // nx true, ny false: the result is (cx0, cx1, rx) = (100, 101, 102)
    N out[3];
    runs[argc - 1](in, out);
    std::printf("%llu %llu %llu\n", static_cast<unsigned long long>(out[0].m),
                static_cast<unsigned long long>(out[1].m), static_cast<unsigned long long>(out[2].m));
    return out[0].m == 100 && out[1].m == 101 && out[2].m == 102 ? 0 : 1;
}
