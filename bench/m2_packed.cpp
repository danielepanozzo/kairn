// The packed timed functions of Milestone 2 (bench/m2_data.hpp), backend m2p: the generated kernels
// of kairn/gen/avx2.hpp or neon.hpp, one number or interval or ball per lane, binary64 limbs, on one
// array per limb; each checked against the generated scalar kernel on the same arrays (backend m2s,
// in m2.cpp). Compiled with AVX2 and FMA on x86-64 (bench/CMakeLists.txt); without a packed backend
// its table is empty.
#include "m2_data.hpp"
#include "props_packed.hpp"

using kairn_bench::m2::Entry;

#if defined(KB_PACKED)

namespace {
namespace kg = kairn::gen;
namespace kp = kairn_bench::packed;
using kairn_bench::m2::kN;
using kairn_bench::m2::Raw;
using kp::load;
using kp::store;
using kp::V;
using kp::W;
using namespace kairn_bench::m2;   // the regions
}  // namespace

#define KB_PEACH(...)                                                                              \
    for (int i = 0; i < kN; i += W) {                                                              \
        __VA_ARGS__;                                                                               \
    }
#define L(A) load(&(A)[i])
// One output, two, three or four, stored to sout[0..3].
#define ST1 store(&r.sout[0][i], o0)
#define ST2 ST1; store(&r.sout[1][i], o1)
#define ST3 ST2; store(&r.sout[2][i], o2)
#define ST4 ST3; store(&r.sout[3][i], o3)

#define KB_PLIST(X)                                                                                \
    X(tp, add_down_1, kairn, 1, V o0; kg::add_down_1(L(r.xa), L(r.ya), o0); ST1)                   \
    X(tp, add_up_1, kairn, 1, V o0; kg::add_up_1(L(r.xa), L(r.ya), o0); ST1)                       \
    X(tp, mul_down_1, kairn, 1, V o0; kg::mul_down_1(L(r.xa), L(r.ya), o0); ST1)                   \
    X(tp, mul_up_1, kairn, 1, V o0; kg::mul_up_1(L(r.xa), L(r.ya), o0); ST1)                       \
    X(tp, next_up, kairn, 1, V o0; kg::next_up(L(r.xa), o0); ST1)                                  \
    X(tp, add, kairn, 1, V o0; kg::add_1_1(L(r.xa), L(r.ya), o0); ST1)                             \
    X(tp, add, plain, 1, V o0 = kp::add(L(r.xa), L(r.ya)); ST1)                                    \
    X(tp, mul, kairn, 1, V o0; kg::mul_1_1(L(r.xa), L(r.ya), o0); ST1)                             \
    X(tp, mul, plain, 1, V o0 = kp::mul(L(r.xa), L(r.ya)); ST1)                                    \
    X(tp, interval_add_1, kairn, 2,                                                                \
      V o0; V o1; kg::interval_add_1(L(r.sxi[0]), L(r.sxi[1]), L(r.syi[0]), L(r.syi[1]), o0, o1); ST2) \
    X(tp, interval_mul_1, kairn, 2,                                                                \
      V o0; V o1; kg::interval_mul_1(L(r.sxi[0]), L(r.sxi[1]), L(r.syi[0]), L(r.syi[1]), o0, o1); ST2) \
    X(tp, interval_add_2, kairn, 4, V o0; V o1; V o2; V o3;                                        \
      kg::interval_add_2(L(r.sxi2[0]), L(r.sxi2[1]), L(r.sxi2[2]), L(r.sxi2[3]), L(r.syi2[0]), L(r.syi2[1]), \
                         L(r.syi2[2]), L(r.syi2[3]), o0, o1, o2, o3); ST4)                         \
    X(tp, interval_mul_2, kairn, 4, V o0; V o1; V o2; V o3;                                        \
      kg::interval_mul_2(L(r.sxi2[0]), L(r.sxi2[1]), L(r.sxi2[2]), L(r.sxi2[3]), L(r.syi2[0]), L(r.syi2[1]), \
                         L(r.syi2[2]), L(r.syi2[3]), o0, o1, o2, o3); ST4)                         \
    X(tp, ball_add_1, kairn, 2,                                                                    \
      V o0; V o1; kg::ball_add_1_full(L(r.sxb1[0]), L(r.sxb1[1]), L(r.syb1[0]), L(r.syb1[1]), o0, o1); ST2) \
    X(tp, ball_mul_1, kairn, 2,                                                                    \
      V o0; V o1; kg::ball_mul_1_full(L(r.sxb1[0]), L(r.sxb1[1]), L(r.syb1[0]), L(r.syb1[1]), o0, o1); ST2) \
    X(tp, ball_add_2, kairn, 3, V o0; V o1; V o2;                                                  \
      kg::ball_add_2_full(L(r.sxb2[0]), L(r.sxb2[1]), L(r.sxb2[2]), L(r.syb2[0]), L(r.syb2[1]), L(r.syb2[2]), \
                          o0, o1, o2); ST3)                                                        \
    X(tp, ball_mul_2, kairn, 3, V o0; V o1; V o2;                                                  \
      kg::ball_mul_2_full(L(r.sxb2[0]), L(r.sxb2[1]), L(r.sxb2[2]), L(r.syb2[0]), L(r.syb2[1]), L(r.syb2[2]), \
                          o0, o1, o2); ST3)

#define KB_PDEF(KIND, KERNEL, VAR, OUTS, ...)                                                      \
    extern "C" KB_NOINLINE void kb_m2_p64_##KIND##_##KERNEL##__##VAR(void* kb_data) {                    \
        Raw<double>& r = *static_cast<Raw<double>*>(kb_data);                                            \
        KB_PEACH(__VA_ARGS__)                                                                      \
    }
#define KB_PROW(KIND, KERNEL, VAR, OUTS, ...)                                                      \
    {"m2p/" #KIND "/" #KERNEL "/" #VAR, kb_m2_p64_##KIND##_##KERNEL##__##VAR, 64, W, kN, R_SOUT, OUTS * kN, nullptr},

KB_PLIST(KB_PDEF)

namespace kairn_bench::m2 {
const char* const m2_packed_backend = kp::backend;
const Entry m2_packed_entries[] = {
    KB_PLIST(KB_PROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
}  // namespace kairn_bench::m2

#else

namespace kairn_bench::m2 {
const char* const m2_packed_backend = "none";
const Entry m2_packed_entries[] = {{nullptr, nullptr, 0, 0, 0, 0, 0, nullptr}};
}  // namespace kairn_bench::m2

#endif
