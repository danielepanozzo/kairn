// A runner for the packed kernels, kairn/gen/avx2.hpp or kairn/gen/neon.hpp, whichever the target
// has: the line protocol of runner.cpp, but consecutive requests for one kernel and one format are
// evaluated together, one per lane, so that special operands share a register with ordinary ones.
// The generator's tests compare its output with the scalar runner's, line by line.
//
//   c++ -std=c++20 -mavx2 -mfma -I include -I gen/tests gen/tests/packed_runner.cpp -o packed
//
// It reads the same runner_kernels.inc as runner.cpp; -DKAIRN_RUNNER_HEADER='"x.hpp"' stands in
// for the generated header, as there.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

#ifndef KAIRN_RUNNER_HEADER
#if defined(__AVX2__)
#define KAIRN_RUNNER_HEADER "kairn/gen/avx2.hpp"
#else
#define KAIRN_RUNNER_HEADER "kairn/gen/neon.hpp"
#endif
#endif
#include KAIRN_RUNNER_HEADER

namespace {

// Registers of each limb type: load and store lanes, and masks as lane-wide integers.
#if defined(__AVX2__)
struct D {
    using V = __m256d;
    using M = __m256d;
    using U = std::uint64_t;
    static constexpr int lanes = 4;
    static V load(const double* p) { return _mm256_loadu_pd(p); }
    static void store(double* p, V v) { _mm256_storeu_pd(p, v); }
    static M load_mask(const U* p) { return _mm256_castsi256_pd(_mm256_loadu_si256(reinterpret_cast<const __m256i*>(p))); }
    static void store_mask(U* p, M m) { _mm256_storeu_si256(reinterpret_cast<__m256i*>(p), _mm256_castpd_si256(m)); }
};
struct F {
    using V = __m256;
    using M = __m256;
    using U = std::uint32_t;
    static constexpr int lanes = 8;
    static V load(const float* p) { return _mm256_loadu_ps(p); }
    static void store(float* p, V v) { _mm256_storeu_ps(p, v); }
    static M load_mask(const U* p) { return _mm256_castsi256_ps(_mm256_loadu_si256(reinterpret_cast<const __m256i*>(p))); }
    static void store_mask(U* p, M m) { _mm256_storeu_si256(reinterpret_cast<__m256i*>(p), _mm256_castps_si256(m)); }
};
#elif defined(__aarch64__)
struct D {
    using V = float64x2_t;
    using M = uint64x2_t;
    using U = std::uint64_t;
    static constexpr int lanes = 2;
    static V load(const double* p) { return vld1q_f64(p); }
    static void store(double* p, V v) { vst1q_f64(p, v); }
    static M load_mask(const U* p) { return vld1q_u64(p); }
    static void store_mask(U* p, M m) { vst1q_u64(p, m); }
};
struct F {
    using V = float32x4_t;
    using M = uint32x4_t;
    using U = std::uint32_t;
    static constexpr int lanes = 4;
    static V load(const float* p) { return vld1q_f32(p); }
    static void store(float* p, V v) { vst1q_f32(p, v); }
    static M load_mask(const U* p) { return vld1q_u32(p); }
    static void store_mask(U* p, M m) { vst1q_u32(p, m); }
};
#else
#error "packed_runner.cpp: no packed backend for this target"
#endif

struct Kernel {
    const char* name;
    const char* in_kinds;   // one letter per input value: l a limb, m a mask
    const char* out_kinds;
    void (*binary64)(const D::V* in, D::V* out, const D::M* mi, D::M* mo);
    void (*binary32)(const F::V* in, F::V* out, const F::M* mi, F::M* mo);
};

#define KAIRN_RUNNER_ARGS(P) \
    [[maybe_unused]] const P::V* in, [[maybe_unused]] P::V* out, [[maybe_unused]] const P::M* mi, [[maybe_unused]] P::M* mo
#define KAIRN_RUNNER_KERNEL(NAME, IN, OUT, CALL) \
    {#NAME, IN, OUT, [](KAIRN_RUNNER_ARGS(D)) { CALL; }, [](KAIRN_RUNNER_ARGS(F)) { CALL; }},
const Kernel kernels[] = {
#include "runner_kernels.inc"
};
constexpr int max_limbs = 16;

long lineno = 0;

struct Request {
    std::string line;
    std::vector<std::string> fields;
};
std::vector<Request> batch;   // requests for one kernel and one format, at most one per lane
const Kernel* batch_kernel = nullptr;
bool batch_binary64 = true;

void flush();

[[noreturn]] void fail(const std::string& why) {
    flush();
    std::fflush(stdout);
    std::fprintf(stderr, "packed runner: line %ld: %s\n", lineno, why.c_str());
    std::exit(2);
}

// A limb is a C99 hexadecimal literal, inf, -inf or nan; strtod alone would also take decimals.
double parse(const std::string& text) {
    if (text == "inf") return std::numeric_limits<double>::infinity();
    if (text == "-inf") return -std::numeric_limits<double>::infinity();
    if (text == "nan") return std::numeric_limits<double>::quiet_NaN();
    const std::size_t x = text.find_first_of("xX");
    if (x == std::string::npos || x == 0 || text[x - 1] != '0' || text.find_first_of("pP") == std::string::npos)
        fail("not a limb: " + text);
    char* end = nullptr;
    const double v = std::strtod(text.c_str(), &end);
    if (*end != '\0') fail("not a limb: " + text);
    return v;
}

void put(double v, std::string& out) {
    if (v != v) {
        out += "nan";
    } else if (v == std::numeric_limits<double>::infinity()) {
        out += "inf";
    } else if (v == -std::numeric_limits<double>::infinity()) {
        out += "-inf";
    } else {
        char buf[64];
        std::snprintf(buf, sizeof buf, "%a", v);
        out += buf;
    }
}

template <class T> struct Lanes;
template <> struct Lanes<double> : D {};
template <> struct Lanes<float> : F {};

// The batch, one request per lane; lanes past its end repeat its first request.
template <class T, class Fn>
void evaluate(const Kernel& k, Fn fn) {
    using P = Lanes<T>;
    using U = typename P::U;
    const int ni = int(std::strlen(k.in_kinds)), no = int(std::strlen(k.out_kinds));
    typename P::V in[max_limbs] = {}, out[max_limbs] = {};
    typename P::M mi[max_limbs] = {}, mo[max_limbs] = {};
    T buf[P::lanes];
    U bits[P::lanes];
    for (int i = 0; i < ni; ++i) {
        for (int lane = 0; lane < P::lanes; ++lane) {
            const std::string& t = batch[std::size_t(lane) < batch.size() ? lane : 0].fields[2 + i];
            if (k.in_kinds[i] == 'm') bits[lane] = t == "1" ? ~U(0) : U(0);
            else buf[lane] = static_cast<T>(parse(t));
        }
        if (k.in_kinds[i] == 'm') mi[i] = P::load_mask(bits);
        else in[i] = P::load(buf);
    }
    fn(in, out, mi, mo);
    std::vector<std::string> results(batch.size());
    for (int i = 0; i < no; ++i) {
        if (k.out_kinds[i] == 'm') P::store_mask(bits, mo[i]);
        else P::store(buf, out[i]);
        for (std::size_t lane = 0; lane < batch.size(); ++lane) {
            results[lane] += ' ';
            if (k.out_kinds[i] == 'l') {
                put(static_cast<double>(buf[lane]), results[lane]);
            } else if (bits[lane] == ~U(0) || bits[lane] == 0) {
                results[lane] += bits[lane] ? '1' : '0';
            } else {
                batch.clear();
                fail(std::string(k.name) + ": output " + std::to_string(i) + " is not a lane mask");
            }
        }
    }
    for (std::size_t lane = 0; lane < batch.size(); ++lane) {
        const std::string text = batch[lane].line + " ->" + results[lane] + "\n";
        std::fwrite(text.data(), 1, text.size(), stdout);
    }
}

void flush() {
    if (batch.empty()) return;
    if (batch_binary64) evaluate<double>(*batch_kernel, batch_kernel->binary64);
    else evaluate<float>(*batch_kernel, batch_kernel->binary32);
    batch.clear();
}

}  // namespace

int main() {
    std::ios::sync_with_stdio(false);
    std::string line;
    while (std::getline(std::cin, line)) {
        ++lineno;
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty() || line[0] == '#') {
            flush();
            const std::string text = line + "\n";
            std::fwrite(text.data(), 1, text.size(), stdout);
            continue;
        }
        Request r{line, {}};
        for (std::size_t start = 0;;) {
            const std::size_t space = line.find(' ', start);
            r.fields.push_back(line.substr(start, space - start));
            if (r.fields.back().empty()) fail("fields are separated by single spaces");
            if (space == std::string::npos) break;
            start = space + 1;
        }
        if (r.fields.back()[0] == '#') r.fields.pop_back();  // the tag
        if (r.fields.size() < 2) fail("expected KERNEL FORMAT LIMB ... [#TAG]");
        const Kernel* k = nullptr;
        for (const Kernel& c : kernels)
            if (r.fields[0] == c.name) k = &c;
        if (!k) fail("unknown kernel " + r.fields[0]);
        const int inputs = int(std::strlen(k->in_kinds));
        if (int(r.fields.size()) - 2 != inputs) fail(r.fields[0] + " takes " + std::to_string(inputs) + " limbs");
        if (inputs > max_limbs || int(std::strlen(k->out_kinds)) > max_limbs) fail("too many limbs for this runner");
        const bool binary64 = r.fields[1] == "binary64";
        if (!binary64 && r.fields[1] != "binary32") fail("this runner knows binary64 and binary32, not " + r.fields[1]);
        for (int i = 0; i < inputs; ++i) {
            const std::string& t = r.fields[2 + i];
            if (k->in_kinds[i] == 'm') {
                if (t != "0" && t != "1") fail("not a mask: " + t);
                continue;
            }
            const double v = parse(t);
            const double top = std::numeric_limits<float>::max();
            if (!binary64 && v == v && v - v == 0 && (v > top || v < -top)) fail(t + " is not a binary32 number");
            if (!binary64 && v == v && static_cast<double>(static_cast<float>(v)) != v) fail(t + " is not a binary32 number");
        }
        if (k != batch_kernel || binary64 != batch_binary64) flush();
        batch_kernel = k;
        batch_binary64 = binary64;
        batch.push_back(r);
        if (int(batch.size()) == (binary64 ? D::lanes : F::lanes)) flush();
    }
    flush();
    return 0;
}
