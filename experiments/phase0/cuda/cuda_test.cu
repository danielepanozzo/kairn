// Phase 0 experiment: the prototype's host/device/constexpr functions under nvcc, and what the
// device does to a double-word product written with plain operators.
//
//   1. proto.hpp compiles as `__host__ __device__ constexpr` WITHOUT --expt-relaxed-constexpr,
//      and a constexpr value computed by the front end equals the device's run-time value.
//   2. The device result of the intrinsic-based product equals the host result bit for bit.
//   3. The "textbook" product (plain * and +) is contracted by nvcc's default -fmad=true.
//   4. Gradual underflow on the device: TwoSum and TwoProd on subnormal floats.
//   5. Directed-rounding intrinsics agree with round-to-nearest + error term + next float.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include "../constexpr/proto.hpp"

using proto::Expansion;
using proto::pair;
typedef Expansion<double, 2> dd;
typedef Expansion<float, 2> ff;

// Textbook double-word product with plain operators (device version of contraction.cpp).
template <class T> __host__ __device__ inline Expansion<T, 2> mul_textbook(Expansion<T, 2> x, Expansion<T, 2> y) {
    const T p = x.limb[0] * y.limb[0];
    const T e = proto::fma_rt(x.limb[0], y.limb[0], -p);
    const T t0 = x.limb[1] * y.limb[1];
    const T t1 = proto::fma_rt(x.limb[0], y.limb[1], t0);
    const T t2 = proto::fma_rt(x.limb[1], y.limb[0], t1);
    const T c = e + t2;
    const T s = p + c;
    const T z = s - p;
    const T l = c - z;
    return {s, l};
}

constexpr dd third{0x1.5555555555555p-2, 0x1.5555555555555p-56};
constexpr dd c_horner = proto::horner3(dd(1.0), third, third, third);
constexpr pair<double> c_prod = proto::two_prod(0x1.123456789abcdp+3, 0x1.fedcba9876543p-7);

__global__ void k_mul(const dd *x, const dd *y, dd *z_intr, dd *z_text, int n) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    z_intr[i] = x[i] * y[i];
    z_text[i] = mul_textbook(x[i], y[i]);
}
__global__ void k_mulf(const ff *x, const ff *y, ff *z_intr, ff *z_text, int n) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    z_intr[i] = x[i] * y[i];
    z_text[i] = mul_textbook(x[i], y[i]);
}
// out[0..1]: device horner3 on run-time copies of the constexpr inputs; out[2..3]: device two_prod.
__global__ void k_const(const double *in, double *out) {
    const dd t{in[0], in[1]};
    const dd h = proto::horner3(dd(in[2]), t, t, t);
    const pair<double> p = proto::two_prod(in[3], in[4]);
    constexpr dd on_device = proto::horner3(dd(1.0), third, third, third);  // constant evaluation in device code
    out[0] = h.limb[0]; out[1] = h.limb[1]; out[2] = p.hi; out[3] = p.lo;
    out[4] = on_device.limb[0]; out[5] = on_device.limb[1];
}
// Subnormal floats: out = {TwoSum(a,b).hi, .lo, TwoProd(c,d).hi, .lo, a*0.5f, min_subnormal/2 + min_subnormal}
__global__ void k_subnormal(const float *in, float *out) {
    const pair<float> s = proto::two_sum(in[0], in[1]);
    const pair<float> p = proto::two_prod(in[2], in[3]);
    out[0] = s.hi; out[1] = s.lo; out[2] = p.hi; out[3] = p.lo;
    out[4] = __fmul_rn(in[0], 0.5f);
    out[5] = __fadd_rn(in[4], in[4]);
}
// Directed rounding: count disagreements between __dadd_ru/__dadd_rd/__dmul_ru/__dmul_rd and the
// round-to-nearest emulation (error term from TwoSum / TwoProd decides whether to step outward).
// The next double above / below a finite x, by stepping the bit pattern. Not nextafter(): with
// -std=c++20 and libstdc++ 13 the name resolves to a constexpr *host* function, which nvcc
// refuses in device code without --expt-relaxed-constexpr.
__device__ inline double next_up(double x) {
    if (x == 0.0) return __longlong_as_double(1);
    const long long b = __double_as_longlong(x);
    return __longlong_as_double(x > 0.0 ? b + 1 : b - 1);
}
__device__ inline double next_dn(double x) { return -next_up(-x); }
__global__ void k_directed(const double *a, const double *b, int *bad, int n) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    const pair<double> s = proto::two_sum(a[i], b[i]);
    const pair<double> p = proto::two_prod(a[i], b[i]);
    int k = 0;
    k += (s.lo > 0 ? next_up(s.hi) : s.hi) != __dadd_ru(a[i], b[i]);
    k += (s.lo < 0 ? next_dn(s.hi) : s.hi) != __dadd_rd(a[i], b[i]);
    k += (p.lo > 0 ? next_up(p.hi) : p.hi) != __dmul_ru(a[i], b[i]);
    k += (p.lo < 0 ? next_dn(p.hi) : p.hi) != __dmul_rd(a[i], b[i]);
    bad[i] = k;
}

static unsigned long long state = 0x9E3779B97F4A7C15ull;
static unsigned long long next() {
    unsigned long long z = (state += 0x9E3779B97F4A7C15ull);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
    return z ^ (z >> 31);
}
static double unit() { return 1.0 + double(next() >> 12) * 0x1p-52; }
template <class T> static Expansion<T, 2> random_dw() {
    const int p = sizeof(T) == 8 ? 53 : 24, e = int(next() % 40) - 20;
    volatile T hi = T(std::ldexp(unit(), e)), lo = T(std::ldexp(unit() - 1.5, e - p + 1));
    volatile T s = hi + lo, z = s - hi, l = lo - z;
    return {s, l};
}
template <class T> static T *to_device(const std::vector<T> &v) {
    T *d;
    cudaMalloc(&d, v.size() * sizeof(T));
    cudaMemcpy(d, v.data(), v.size() * sizeof(T), cudaMemcpyHostToDevice);
    return d;
}
template <class T> static std::vector<T> to_host(const T *d, size_t n) {
    std::vector<T> v(n);
    cudaMemcpy(v.data(), d, n * sizeof(T), cudaMemcpyDeviceToHost);
    return v;
}
template <class T, class K> static void product_test(const char *name, K kernel) {
    typedef Expansion<T, 2> X;
    const int n = 1 << 20;
    std::vector<X> x(n), y(n);
    for (int i = 0; i < n; ++i) x[i] = random_dw<T>(), y[i] = random_dw<T>();
    X *dx = to_device(x), *dy = to_device(y), *di, *dt;
    cudaMalloc(&di, n * sizeof(X));
    cudaMalloc(&dt, n * sizeof(X));
    kernel<<<n / 256, 256>>>(dx, dy, di, dt, n);
    const std::vector<X> zi = to_host(di, n), zt = to_host(dt, n);
    int bad_intr = 0, bad_text = 0;
    for (int i = 0; i < n; ++i) {
        const X h = x[i] * y[i];  // host: std::fma path
        bad_intr += std::memcmp(&h, &zi[i], sizeof(X)) != 0;
        bad_text += std::memcmp(&h, &zt[i], sizeof(X)) != 0;
    }
    std::printf("%s product, %d cases: device(intrinsics) != host: %d   device(textbook, plain * and +) != host: %d\n",
                name, n, bad_intr, bad_text);
}

int main() {
    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, 0);
    std::printf("device: %s (compute capability %d.%d)\n", prop.name, prop.major, prop.minor);

    const std::vector<double> in = {0x1.5555555555555p-2, 0x1.5555555555555p-56, 1.0, 0x1.123456789abcdp+3, 0x1.fedcba9876543p-7};
    double *din = to_device(in), *dout;
    cudaMalloc(&dout, 6 * sizeof(double));
    k_const<<<1, 1>>>(din, dout);
    const std::vector<double> out = to_host(dout, 6);
    std::printf("constexpr (front end)  horner %a %a   two_prod %a %a\n", c_horner.limb[0], c_horner.limb[1], c_prod.hi, c_prod.lo);
    std::printf("device run time        horner %a %a   two_prod %a %a\n", out[0], out[1], out[2], out[3]);
    std::printf("constexpr inside device code      %a %a\n", out[4], out[5]);
    std::printf("two_prod: constexpr == device: %s\n", out[2] == c_prod.hi && out[3] == c_prod.lo ? "yes" : "NO");

    product_test<double>("double-double", k_mul);
    product_test<float>("float-float", k_mulf);

    // 0x1.8p-140f + 0x1.4p-146f is exact in subnormals; 0x1.000002p-80f * 0x1.000002p-60f underflows.
    const std::vector<float> fin = {0x1.8p-140f, 0x1.4p-146f, 0x1.000002p-80f, 0x1.000002p-60f, 0x1p-149f};
    float *dfin = to_device(fin), *dfout;
    cudaMalloc(&dfout, 6 * sizeof(float));
    k_subnormal<<<1, 1>>>(dfin, dfout);
    const std::vector<float> fo = to_host(dfout, 6);
    volatile float a = fin[0], b = fin[1], c = fin[2], d = fin[3], m = fin[4];
    const pair<float> hs = proto::two_sum<float>(a, b), hp = proto::two_prod<float>(c, d);
    std::printf("subnormal float  device: two_sum %a %a  two_prod %a %a  half %a  2*min %a\n", fo[0], fo[1], fo[2], fo[3], fo[4], fo[5]);
    std::printf("subnormal float  host:   two_sum %a %a  two_prod %a %a  half %a  2*min %a\n", hs.hi, hs.lo, hp.hi, hp.lo, a * 0.5f, m + m);

    const int n = 1 << 20;
    std::vector<double> va(n), vb(n);
    for (int i = 0; i < n; ++i) {
        va[i] = std::ldexp(unit(), int(next() % 60) - 30) * (next() & 1 ? -1 : 1);
        vb[i] = std::ldexp(unit(), int(next() % 60) - 30) * (next() & 1 ? -1 : 1);
    }
    double *da = to_device(va), *db = to_device(vb);
    int *dbad;
    cudaMalloc(&dbad, n * sizeof(int));
    k_directed<<<n / 256, 256>>>(da, db, dbad, n);
    const std::vector<int> bad = to_host(dbad, n);
    long total = 0;
    for (int i = 0; i < n; ++i) total += bad[i];
    std::printf("directed rounding: %d pairs x 4 operations, disagreements between intrinsics and RN emulation: %ld\n", n, total);
    return 0;
}
