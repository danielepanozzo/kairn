// Phase 0 measurement: arithmetic throughput of float vs double on the device, and of a
// float-float (2 x 24 bits) multiply-add against a plain double multiply-add. Compute-bound:
// each thread keeps 8 independent chains in registers and runs ITER fused multiply-adds per chain.
#include <chrono>
#include <cstdio>
#include "../constexpr/proto.hpp"
using proto::Expansion;

template <class T> __device__ inline T fma_dev(T a, T b, T c) {
    if constexpr (sizeof(T) == 8) return __fma_rn(a, b, c);
    else return __fmaf_rn(a, b, c);
}
template <class T> __global__ void k_fma(T *out, int iters) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    T a[8];
    for (int j = 0; j < 8; ++j) a[j] = T(1) + T(i % 97 + j) * T(1e-3);
    const T m = T(0.999), c = T(1e-3);
    for (int it = 0; it < iters; ++it)
        for (int j = 0; j < 8; ++j) a[j] = fma_dev(a[j], m, c);
    T s = 0;
    for (int j = 0; j < 8; ++j) s += a[j];
    out[i] = s;
}
// The same loop on double-word numbers: a = a * m + c with Expansion<T, 2> (prototype networks:
// DWTimesDW3 with FMAs, AccurateDWPlusDW).
template <class T> __global__ void k_dw(T *out, int iters) {
    typedef Expansion<T, 2> X;
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    X a[8];
    for (int j = 0; j < 8; ++j) a[j] = X(T(1) + T(i % 97 + j) * T(1e-3));
    const X m{T(0.999), T(1e-9)}, c{T(1e-3), T(1e-12)};
    for (int it = 0; it < iters; ++it)
        for (int j = 0; j < 8; ++j) a[j] = a[j] * m + c;
    T s = 0;
    for (int j = 0; j < 8; ++j) s += a[j].limb[0];
    out[i] = s;
}
template <class K, class T> static double run(K kernel, T *out, int n, int iters) {
    kernel<<<n / 256, 256>>>(out, 16);  // warm up
    cudaDeviceSynchronize();
    const auto t0 = std::chrono::steady_clock::now();
    kernel<<<n / 256, 256>>>(out, iters);
    cudaDeviceSynchronize();
    const double s = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    return double(n) * 8 * iters / s * 1e-9;  // 1e9 multiply-adds per second
}
int main() {
    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, 0);
    const int n = 1 << 20;
    float *of;
    double *od;
    cudaMalloc(&of, n * sizeof(float));
    cudaMalloc(&od, n * sizeof(double));
    const double f = run(k_fma<float>, of, n, 4096), d = run(k_fma<double>, od, n, 256);
    const double ff = run(k_dw<float>, of, n, 256), dd = run(k_dw<double>, od, n, 16);
    std::printf("%s (compute capability %d.%d), 1e9 a = a*m + c per second:\n", prop.name, prop.major, prop.minor);
    std::printf("  float                 %9.2f\n  double                %9.2f   float/double       = %.1f\n", f, d, f / d);
    std::printf("  Expansion<float, 2>   %9.2f   (46 bits)  vs double = %.2fx\n", ff, ff / d);
    std::printf("  Expansion<double, 2>  %9.2f   (104 bits) vs double = %.3fx,  vs Expansion<float, 2> = %.3fx\n", dd, dd / d, dd / ff);
    return 0;
}
