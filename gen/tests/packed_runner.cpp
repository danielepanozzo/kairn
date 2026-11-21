// A runner for the packed kernels, kairn/gen/avx2.hpp or kairn/gen/neon.hpp, whichever the target
// has: the line protocol of runner.cpp, but the requests for one kernel and one format are
// evaluated W at a time, one per lane of a register of W lanes, so that special operands share a
// register with ordinary ones. The completed lines come out in the order of the requests. The
// generator's tests compare its output with the scalar runner's, line by line; the cross-checks
// have the oracle judge it (docs/developer/testing.md, "Packed kernels").
//
//   c++ -std=c++20 -mavx2 -mfma -I include -I gen/tests gen/tests/packed_runner.cpp -o packed
//   ./packed [--lanes permuted|consecutive] [--lane-seed N] [--lane-guard]
//            [--lane-report FILE] [--lane-plan FILE] < requests > completed
//
// It reads the same runner_kernels.inc as runner.cpp; -DKAIRN_RUNNER_HEADER='"x.hpp"' stands in
// for the generated header, as there, and -DKAIRN_RUNNER_TABLE='"t.inc"' for the table.
//
// Which request goes to which lane. A segment is a run of consecutive requests for one kernel and
// one format: a comment, an empty line, a fold, a map, a request of another kernel or format, or
// the end of the input ends it. The runner reads a whole segment of n requests, assigns them to
// n of the R W slots of R = ceil(n / W) registers, evaluates each register with one call of the
// packed kernel, and then prints the n completed lines in the order of the requests.
//
// - permuted (the default): the requests are grouped by kind (below), the kinds in the order they
//   first appear, and the requests of each kind shuffled; the groups, one after the other, fill
//   the slots register by register, so that a kind of c requests takes c consecutive slots and is
//   in every lane once c >= W; then the slots of each lane are shuffled among the registers, a
//   permutation of the R registers per lane, so that the lanes of one register hold kinds drawn
//   independently. The random numbers are SplitMix64 on 64-bit unsigned integers from --lane-seed
//   (default 0) and the number of the segment, an integer below m drawn by rejection, and
//   Fisher-Yates shuffles: integer arithmetic only, so the same requests and seed give the same
//   assignment with every compiler and on every target.
// - consecutive: request k goes to lane k mod W of register k / W, the assignment of this runner
//   until 2026-11-21. On the oracle's streams, whose strata take turns, it fills a register with
//   requests of one kind; that case is tested too.
//
// The slots no request takes, R W - n < W of them (at the end of the last register in the
// consecutive assignment, anywhere in the permuted one), are padding: they hold a copy of the first
// request of the segment whose limbs are all finite (of its first request if none is: a request
// the kernel accepts in any case), and their results are dropped.
//
// The kinds of a request: its stratum, the label of a tag #STRATUM:INDEX (none for another tag or
// none), and whether one of its limbs is not finite (inf, -inf or nan). A register mixes when it
// holds a request with a non-finite limb and one whose limbs are all finite (the padding not
// counted).
//
// The guard, on the permuted assignment (and on the consecutive one with --lane-guard): on a
// segment of at least guard_lines (256) requests, every kind of at least W requests was in every
// lane, and if at least guard_cases (16) requests have a non-finite limb and 16 have only finite
// ones, at least one register mixed them. If not, the runner prints the segment's lines, says why
// on standard error and exits with 3 (2 for a request it refuses, as runner.cpp).
//
// --lane-report FILE writes what each segment held as JSON: its kernel, format, lines, lanes,
// registers, padding, the registers that mixed, the requests of each kind in each lane, and the
// guard's verdict. --lane-plan FILE writes one line per slot, SEGMENT REGISTER LANE LINE, LINE the
// number of the request's line in the input or pad.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <string>
#include <utility>
#include <vector>

#ifndef KAIRN_RUNNER_HEADER
#if defined(__AVX2__)
#define KAIRN_RUNNER_HEADER "kairn/gen/avx2.hpp"
#else
#define KAIRN_RUNNER_HEADER "kairn/gen/neon.hpp"
#endif
#endif
#include KAIRN_RUNNER_HEADER
#ifndef KAIRN_RUNNER_TABLE
#define KAIRN_RUNNER_TABLE "runner_kernels.inc"
#endif

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
#include KAIRN_RUNNER_TABLE
};
#undef KAIRN_RUNNER_KERNEL
constexpr int max_limbs = 16;

// The folds: the lane order computed by the packed form, F_packed, with the lanes of the register
// of the limb type, the only order this runner computes (lanes:W with W = D::lanes or F::lanes).
struct Fold {
    const char* name;
    const char* arrays;     // the limbs of each array
    const char* out_kinds;
    void (*binary64)(const double* const* in, std::size_t n, double* out, bool* mo);
    void (*binary32)(const float* const* in, std::size_t n, float* out, bool* mo);
};
#define KAIRN_RUNNER_FOLD_ARGS(T) \
    [[maybe_unused]] const T* const* in, [[maybe_unused]] std::size_t n, [[maybe_unused]] T* out, [[maybe_unused]] bool* mo
#define KAIRN_RUNNER_KERNEL(NAME, IN, OUT, CALL)
#define KAIRN_RUNNER_FOLD(NAME, ARRAYS, OUT, SEQ, LANES, PACKED) \
    {#NAME, ARRAYS, OUT, [](KAIRN_RUNNER_FOLD_ARGS(double)) { PACKED; }, [](KAIRN_RUNNER_FOLD_ARGS(float)) { PACKED; }},
const Fold folds[] = {
#include KAIRN_RUNNER_TABLE
    {nullptr, nullptr, nullptr, nullptr, nullptr},
};
#undef KAIRN_RUNNER_FOLD

// The maps, by their packed form F_packed only, as the folds.
struct Map {
    const char* name;
    const char* arrays;
    int scalars;
    int writes;
    int radius;     // 1 for a ball vector, which returns its radius (out[0]) before the flag
    void (*binary64)(const double* const* in, std::size_t n, const double* sc, double* const* w, double* out, bool* mo);
    void (*binary32)(const float* const* in, std::size_t n, const float* sc, float* const* w, float* out, bool* mo);
};
#define KAIRN_RUNNER_MAP_ARGS(T)                                                                     \
    [[maybe_unused]] const T* const* in, [[maybe_unused]] std::size_t n, [[maybe_unused]] const T* sc, \
        [[maybe_unused]] T* const* w, [[maybe_unused]] T* out, [[maybe_unused]] bool* mo
#define KAIRN_RUNNER_FOLD(NAME, ARRAYS, OUT, SEQ, LANES, PACKED)
#define KAIRN_RUNNER_MAP(NAME, ARRAYS, SCALARS, WRITES, SEQ, LANES, PACKED) \
    {#NAME, ARRAYS, SCALARS, WRITES, 0, [](KAIRN_RUNNER_MAP_ARGS(double)) { PACKED; }, [](KAIRN_RUNNER_MAP_ARGS(float)) { PACKED; }},
#define KAIRN_RUNNER_BV(NAME, ARRAYS, SCALARS, WRITES, SEQ, LANES, PACKED) \
    {#NAME, ARRAYS, SCALARS, WRITES, 1, [](KAIRN_RUNNER_MAP_ARGS(double)) { PACKED; }, [](KAIRN_RUNNER_MAP_ARGS(float)) { PACKED; }},
const Map maps[] = {
#include KAIRN_RUNNER_TABLE
    {nullptr, nullptr, 0, 0, 0, nullptr, nullptr},
};
#undef KAIRN_RUNNER_BV

// The guard's thresholds (above).
constexpr std::size_t guard_lines = 256;
constexpr std::size_t guard_cases = 16;

struct Options {
    bool permuted = true;
    std::uint64_t seed = 0;
    bool guard_consecutive = false;
    std::string report, plan;
} options;

long lineno = 0;

struct Request {
    std::string line;
    std::vector<std::string> fields;
    long lineno = 0;
    std::string stratum;     // the label of its tag #STRATUM:INDEX, or empty
    bool nonfinite = false;  // a limb inf, -inf or nan
};
std::vector<Request> segment;   // requests for one kernel and one format, in their order
const Kernel* segment_kernel = nullptr;
bool segment_binary64 = true;
long segments = 0;              // the segments evaluated so far
std::vector<std::string> report_segments;   // the JSON of each, for --lane-report
std::string plan_text;                      // the lines of --lane-plan

void flush(bool guard = true);
void write_files();

[[noreturn]] void fail(const std::string& why) {
    static bool failing = false;
    if (!failing) {
        failing = true;
        flush(false);
    }
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

// SplitMix64 (Steele, Lea and Flood, 2014), an integer below m by rejection, Fisher-Yates.
struct Random {
    std::uint64_t state;
    std::uint64_t next() {
        std::uint64_t z = (state += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    std::size_t below(std::size_t m) {      // uniform on 0 .. m - 1, for m >= 1
        const std::uint64_t mm = m;
        const std::uint64_t low = (0 - mm) % mm;   // 2^64 mod m: the draws below it are refused
        for (;;) {
            const std::uint64_t r = next();
            if (r >= low) return std::size_t(r % mm);
        }
    }
    template <class V> void shuffle(V& v) {
        for (std::size_t i = v.size(); i > 1; --i) std::swap(v[i - 1], v[below(i)]);
    }
};

// The kinds of a segment, and what each lane held of each.
struct Kind {
    std::string stratum;
    bool nonfinite;
    std::size_t cases = 0;
    std::vector<std::size_t> lanes;
};

// The slots of the R W lanes of the segment's registers: the index of a request, or -1 (padding).
std::vector<long> assign(std::size_t lanes, const std::vector<int>& kind_of, std::size_t kinds) {
    const std::size_t n = kind_of.size(), registers = (n + lanes - 1) / lanes;
    std::vector<long> slots(registers * lanes, -1);
    if (!options.permuted) {
        for (std::size_t i = 0; i < n; ++i) slots[i] = long(i);
        return slots;
    }
    Random random{options.seed + 0x632be59bd9b4e019ULL * std::uint64_t(segments + 1)};
    std::vector<std::vector<long>> groups(kinds);
    for (std::size_t i = 0; i < n; ++i) groups[std::size_t(kind_of[i])].push_back(long(i));
    std::vector<long> order;
    order.reserve(slots.size());
    for (auto& g : groups) {
        random.shuffle(g);
        order.insert(order.end(), g.begin(), g.end());
    }
    order.resize(slots.size(), -1);
    std::vector<std::size_t> rows(registers);
    for (std::size_t lane = 0; lane < lanes; ++lane) {
        for (std::size_t r = 0; r < registers; ++r) rows[r] = r;
        random.shuffle(rows);
        for (std::size_t r = 0; r < registers; ++r) slots[r * lanes + lane] = order[rows[r] * lanes + lane];
    }
    return slots;
}

std::string json_string(const std::string& s) {
    std::string out = "\"";
    for (char c : s) {
        if (c == '"' || c == '\\') out += '\\';
        if (static_cast<unsigned char>(c) < 0x20) continue;
        out += c;
    }
    return out + "\"";
}

// The segment, its requests in the slots assign() gives them; then the completed lines in the
// order of the requests, the counts, and the guard.
template <class T, class Fn>
void evaluate(const Kernel& k, Fn fn, bool guard) {
    using P = Lanes<T>;
    using U = typename P::U;
    const std::size_t W = std::size_t(P::lanes), n = segment.size(), registers = (n + W - 1) / W;
    const int ni = int(std::strlen(k.in_kinds)), no = int(std::strlen(k.out_kinds));

    std::vector<Kind> kinds;
    std::vector<int> kind_of(n);
    for (std::size_t i = 0; i < n; ++i) {
        const Request& q = segment[i];
        std::size_t c = 0;
        while (c < kinds.size() && (kinds[c].stratum != q.stratum || kinds[c].nonfinite != q.nonfinite)) ++c;
        if (c == kinds.size()) kinds.push_back({q.stratum, q.nonfinite, 0, std::vector<std::size_t>(W, 0)});
        kind_of[i] = int(c);
        ++kinds[c].cases;
    }
    const std::vector<long> slots = assign(W, kind_of, kinds.size());
    long pad = -1;          // the request the padding copies
    for (std::size_t i = 0; i < n && pad < 0; ++i)
        if (!segment[i].nonfinite) pad = long(i);
    const std::size_t padding_from = pad < 0 ? 0 : std::size_t(pad);

    std::vector<std::string> results(n);
    std::size_t mixed = 0, mixed_strata = 0;
    for (std::size_t r = 0; r < registers; ++r) {
        typename P::V in[max_limbs] = {}, out[max_limbs] = {};
        typename P::M mi[max_limbs] = {}, mo[max_limbs] = {};
        T buf[P::lanes];
        U bits[P::lanes];
        for (int i = 0; i < ni; ++i) {
            for (std::size_t lane = 0; lane < W; ++lane) {
                const long s = slots[r * W + lane];
                const std::string& t = segment[s < 0 ? padding_from : std::size_t(s)].fields[std::size_t(2 + i)];
                if (k.in_kinds[i] == 'm') bits[lane] = t == "1" ? ~U(0) : U(0);
                else buf[lane] = static_cast<T>(parse(t));
            }
            if (k.in_kinds[i] == 'm') mi[i] = P::load_mask(bits);
            else in[i] = P::load(buf);
        }
        fn(in, out, mi, mo);
        for (int i = 0; i < no; ++i) {
            if (k.out_kinds[i] == 'm') P::store_mask(bits, mo[i]);
            else P::store(buf, out[i]);
            for (std::size_t lane = 0; lane < W; ++lane) {
                const long s = slots[r * W + lane];
                if (s < 0) continue;
                std::string& text = results[std::size_t(s)];
                text += ' ';
                if (k.out_kinds[i] == 'l') {
                    put(static_cast<double>(buf[lane]), text);
                } else if (bits[lane] == ~U(0) || bits[lane] == 0) {
                    text += bits[lane] ? '1' : '0';
                } else {
                    segment.clear();
                    fail(std::string(k.name) + ": output " + std::to_string(i) + " is not a lane mask");
                }
            }
        }
        // What the register held, the padding left out.
        bool finite = false, nonfinite = false;
        const std::string* stratum = nullptr;
        bool strata = false;
        for (std::size_t lane = 0; lane < W; ++lane) {
            const long s = slots[r * W + lane];
            if (s < 0) continue;
            const Request& q = segment[std::size_t(s)];
            (q.nonfinite ? nonfinite : finite) = true;
            if (stratum && *stratum != q.stratum) strata = true;
            stratum = &q.stratum;
            ++kinds[std::size_t(kind_of[std::size_t(s)])].lanes[lane];
            if (!options.plan.empty())
                plan_text += std::to_string(segments) + ' ' + std::to_string(r) + ' ' + std::to_string(lane) + ' ' +
                             std::to_string(q.lineno) + '\n';
        }
        if (!options.plan.empty())
            for (std::size_t lane = 0; lane < W; ++lane)
                if (slots[r * W + lane] < 0)
                    plan_text += std::to_string(segments) + ' ' + std::to_string(r) + ' ' + std::to_string(lane) + " pad\n";
        if (finite && nonfinite) ++mixed;
        if (strata) ++mixed_strata;
    }
    for (std::size_t i = 0; i < n; ++i) {
        const std::string text = segment[i].line + " ->" + results[i] + "\n";
        std::fwrite(text.data(), 1, text.size(), stdout);
    }

    // The guard.
    std::size_t with_nonfinite = 0;
    for (const Request& q : segment)
        if (q.nonfinite) ++with_nonfinite;
    const std::size_t with_finite = n - with_nonfinite;
    std::string verdict = "passed", why;
    if (!guard) {
        verdict = "not applied: the consecutive assignment";
    } else if (n < guard_lines) {
        verdict = "not applied: fewer than " + std::to_string(guard_lines) + " requests";
    } else {
        std::size_t missing = 0;
        std::string first;
        for (const Kind& c : kinds) {
            if (c.cases < W) continue;
            for (std::size_t lane = 0; lane < W; ++lane) {
                if (c.lanes[lane] != 0) continue;
                if (!missing++)
                    first = "no request of stratum " + (c.stratum.empty() ? std::string("(none)") : c.stratum) +
                            " with " + (c.nonfinite ? "a non-finite limb" : "finite limbs") + " (" +
                            std::to_string(c.cases) + " of them) was in lane " + std::to_string(lane);
            }
        }
        if (missing)
            why = first + (missing > 1 ? " (and " + std::to_string(missing - 1) + " more kinds and lanes)" : "");
        if (with_nonfinite >= guard_cases && with_finite >= guard_cases && mixed == 0)
            why += std::string(why.empty() ? "" : "; ") +
                   "no register held a request with a non-finite limb beside one with finite limbs (" +
                   std::to_string(with_nonfinite) + " and " + std::to_string(with_finite) + " requests)";
        if (!why.empty()) verdict = "failed: " + why;
    }

    if (!options.report.empty()) {
        std::string j = "{\"kernel\": " + json_string(k.name) + ", \"format\": \"" +
                        (sizeof(T) == sizeof(double) ? "binary64" : "binary32") + "\", \"first_line\": " +
                        std::to_string(segment.front().lineno) + ", \"requests\": " + std::to_string(n) +
                        ", \"lanes\": " + std::to_string(W) + ", \"registers\": " + std::to_string(registers) +
                        ", \"padding\": " + std::to_string(registers * W - n) + ", \"padding_line\": " +
                        (registers * W > n ? std::to_string(segment[padding_from].lineno) : std::string("null")) +
                        ", \"padding_finite\": " + (pad >= 0 ? "true" : "false") +
                        ", \"with_nonfinite\": " + std::to_string(with_nonfinite) +
                        ", \"with_finite\": " + std::to_string(with_finite) + ", \"mixed\": " + std::to_string(mixed) +
                        ", \"mixed_strata\": " + std::to_string(mixed_strata) + ", \"guard\": " + json_string(verdict) +
                        ", \"kinds\": [";
        for (std::size_t c = 0; c < kinds.size(); ++c) {
            j += std::string(c ? ", " : "") + "{\"stratum\": " + json_string(kinds[c].stratum) +
                 ", \"nonfinite\": " + (kinds[c].nonfinite ? "true" : "false") + ", \"requests\": " +
                 std::to_string(kinds[c].cases) + ", \"lanes\": [";
            for (std::size_t lane = 0; lane < W; ++lane)
                j += (lane ? ", " : "") + std::to_string(kinds[c].lanes[lane]);
            j += "]}";
        }
        report_segments.push_back(j + "]}");
    }
    ++segments;
    if (!why.empty()) {
        std::fflush(stdout);
        write_files();
        std::fprintf(stderr, "packed runner: lines %ld to %ld (%s %s, %zu lanes, the %s assignment): the lanes did not mix: %s\n",
                     segment.front().lineno, segment.back().lineno, k.name,
                     sizeof(T) == sizeof(double) ? "binary64" : "binary32", W,
                     options.permuted ? "permuted" : "consecutive", why.c_str());
        std::exit(3);
    }
}

void flush(bool guard) {
    if (segment.empty()) return;
    guard = guard && (options.permuted || options.guard_consecutive);
    if (segment_binary64) evaluate<double>(*segment_kernel, segment_kernel->binary64, guard);
    else evaluate<float>(*segment_kernel, segment_kernel->binary32, guard);
    segment.clear();
}

// A file of --lane-report or --lane-plan (std::ofstream: MSVC deprecates std::fopen).
void write_file(const std::string& path, const std::string& text) {
    std::ofstream f(path, std::ios::binary);
    f.write(text.data(), std::streamsize(text.size()));
    f.close();
    if (!f) {
        std::fprintf(stderr, "packed runner: cannot write %s\n", path.c_str());
        std::exit(2);
    }
}

void write_files() {
    if (!options.report.empty()) {
        std::string text = std::string("{\"runner\": \"packed\", \"assignment\": \"") +
                           (options.permuted ? "permuted" : "consecutive") + "\", \"seed\": " +
                           std::to_string(options.seed) + ", \"guard\": {\"applied\": " +
                           (options.permuted || options.guard_consecutive ? "true" : "false") +
                           ", \"lines\": " + std::to_string(guard_lines) + ", \"cases\": " + std::to_string(guard_cases) +
                           "}, \"segments\": [";
        for (std::size_t i = 0; i < report_segments.size(); ++i) text += (i ? ",\n  " : "\n  ") + report_segments[i];
        text += "]}\n";
        write_file(options.report, text);
    }
    if (!options.plan.empty()) write_file(options.plan, plan_text);
}

std::size_t decimal(const std::string& text, const char* what) {
    if (text.empty() || text.find_first_not_of("0123456789") != std::string::npos || (text[0] == '0' && text.size() > 1))
        fail(std::string("not ") + what + ": " + text);
    return std::stoull(text);
}

// A request of a fold, FOLD FORMAT lanes:W N LIMB..., computed at once (no segment).
template <class T>
void complete_fold(const Fold& f, const Request& r, void (*fn)(const T* const*, std::size_t, T*, bool*)) {
    const std::vector<std::string>& fields = r.fields;
    if (fields.size() < 4) fail(std::string("expected ") + f.name + " FORMAT ORDER N LIMB ... [#TAG]");
    const std::string head = "lanes:";
    if (fields[2].compare(0, head.size(), head) != 0 ||
        decimal(fields[2].substr(head.size()), "an order") != std::size_t(Lanes<T>::lanes))
        fail("the packed runner computes the lane order with the lanes of its register only, lanes:" +
             std::to_string(Lanes<T>::lanes) + " for this format, not " + fields[2]);
    const std::size_t n = decimal(fields[3], "a length");
    std::size_t arrays = 0;
    for (const char* a = f.arrays; *a; ++a) arrays += std::size_t(*a - '0');
    if (fields.size() - 4 != arrays * n)
        fail(std::string(f.name) + " of length " + fields[3] + " takes " + std::to_string(arrays * n) + " limbs");
    const int outputs = int(std::strlen(f.out_kinds));
    if (outputs > max_limbs) fail("too many outputs for this runner");
    std::vector<T> data(arrays * n);
    for (std::size_t i = 0; i < data.size(); ++i) {
        const double v = parse(fields[4 + i]);
        const double top = std::numeric_limits<float>::max();
        if (sizeof(T) == sizeof(float) && v == v && v - v == 0 && (v > top || v < -top))
            fail(fields[4 + i] + " is not a binary32 number");
        data[i] = static_cast<T>(v);
        if (v == v && static_cast<double>(data[i]) != v) fail(fields[4 + i] + " is not a binary32 number");
    }
    std::vector<const T*> in(arrays);
    for (std::size_t l = 0; l < arrays; ++l) in[l] = data.data() + l * n;
    T res[max_limbs] = {};
    bool mo[max_limbs] = {};
    fn(in.data(), n, res, mo);
    std::string text = r.line + " ->";
    for (int i = 0; i < outputs; ++i) {
        text += ' ';
        if (f.out_kinds[i] == 'm') text += mo[i] ? '1' : '0';
        else put(static_cast<double>(res[i]), text);
    }
    text += '\n';
    std::fwrite(text.data(), 1, text.size(), stdout);
}

// A limb of the format T, from its text.
template <class T>
T packed_limb(const std::string& text) {
    const double v = parse(text);
    const double top = std::numeric_limits<float>::max();
    if (sizeof(T) == sizeof(float) && v == v && v - v == 0 && (v > top || v < -top))
        fail(text + " is not a binary32 number");
    const T x = static_cast<T>(v);
    if (v == v && static_cast<double>(x) != v) fail(text + " is not a binary32 number");
    return x;
}

// In place: inplace=I after the length, I the index of an array read with as many limbs as the
// array written, whose buffers the runner passes as the array written (runner.cpp, in_place).
long in_place(const Map& m, const std::vector<std::string>& fields, std::size_t& at) {
    const std::string head = "inplace=";
    if (fields.size() <= at || fields[at].compare(0, head.size(), head) != 0) return -1;
    const std::size_t i = decimal(fields[at].substr(head.size()), "an array");
    if (i >= std::strlen(m.arrays) || m.arrays[i] - '0' != m.writes)
        fail(fields[at] + ": not an array read with as many limbs as the array written");
    ++at;
    return long(i);
}

// A request of a map, MAP FORMAT lanes:W N [inplace=I] SCALAR... LIMB..., computed at once.
template <class T>
void complete_map(const Map& m, const Request& r,
                  void (*fn)(const T* const*, std::size_t, const T*, T* const*, T*, bool*)) {
    const std::vector<std::string>& fields = r.fields;
    if (fields.size() < 4) fail(std::string("expected ") + m.name + " FORMAT ORDER N SCALAR ... LIMB ... [#TAG]");
    const std::string head = "lanes:";
    if (fields[2].compare(0, head.size(), head) != 0 ||
        decimal(fields[2].substr(head.size()), "an order") != std::size_t(Lanes<T>::lanes))
        fail("the packed runner computes the lane order with the lanes of its register only, lanes:" +
             std::to_string(Lanes<T>::lanes) + " for this format, not " + fields[2]);
    const std::size_t n = decimal(fields[3], "a length");
    std::size_t arrays = 0;
    for (const char* a = m.arrays; *a; ++a) arrays += std::size_t(*a - '0');
    const std::size_t scalars = std::size_t(m.scalars);
    std::size_t at = 4;
    const long place = in_place(m, fields, at);
    if (fields.size() - at != scalars + arrays * n)
        fail(std::string(m.name) + " of length " + fields[3] + " takes " + std::to_string(scalars + arrays * n) + " limbs");
    std::vector<T> sc(scalars + 1), data(arrays * n + 1);
    for (std::size_t i = 0; i < scalars; ++i) sc[i] = packed_limb<T>(fields[at + i]);
    for (std::size_t i = 0; i < arrays * n; ++i) data[i] = packed_limb<T>(fields[at + scalars + i]);
    std::vector<const T*> in(arrays + 1);
    for (std::size_t l = 0; l < arrays; ++l) in[l] = data.data() + l * n;
    std::vector<T> written(std::size_t(m.writes) * n + 1);
    std::vector<T*> w(std::size_t(m.writes) + 1);
    for (int l = 0; l < m.writes; ++l) w[std::size_t(l)] = written.data() + std::size_t(l) * n;
    if (place >= 0) {
        std::size_t first = 0;
        for (long a = 0; a < place; ++a) first += std::size_t(m.arrays[a] - '0');
        for (int l = 0; l < m.writes; ++l) w[std::size_t(l)] = data.data() + (first + std::size_t(l)) * n;
    }
    bool mo[1] = {};
    T res[1] = {};
    fn(in.data(), n, sc.data(), w.data(), res, mo);
    std::string text = r.line + " ->";
    for (int l = 0; l < m.writes; ++l)
        for (std::size_t i = 0; i < n; ++i) {
            text += ' ';
            put(static_cast<double>(w[std::size_t(l)][i]), text);
        }
    if (m.radius) {
        text += ' ';
        put(static_cast<double>(res[0]), text);
    }
    text += mo[0] ? " 1\n" : " 0\n";
    std::fwrite(text.data(), 1, text.size(), stdout);
}

[[noreturn]] void usage(const std::string& why) {
    std::fprintf(stderr,
                 "packed runner: %s\nusage: packed_runner [--lanes permuted|consecutive] [--lane-seed N] "
                 "[--lane-guard] [--lane-report FILE] [--lane-plan FILE]\n",
                 why.c_str());
    std::exit(2);
}

void options_from(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        const bool has_value = i + 1 < argc;
        if (a == "--lanes" && has_value) {
            const std::string v = argv[++i];
            if (v != "permuted" && v != "consecutive") usage("--lanes is permuted or consecutive, not " + v);
            options.permuted = v == "permuted";
        } else if (a == "--lane-seed" && has_value) {
            const std::string v = argv[++i];
            if (v.empty() || v.size() > 19 || v.find_first_not_of("0123456789") != std::string::npos)
                usage("--lane-seed is a decimal integer below 10^19, not " + v);
            options.seed = std::stoull(v);
        } else if (a == "--lane-guard") {
            options.guard_consecutive = true;
        } else if (a == "--lane-report" && has_value) {
            options.report = argv[++i];
        } else if (a == "--lane-plan" && has_value) {
            options.plan = argv[++i];
        } else {
            usage("unknown or incomplete option " + a);
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    std::ios::sync_with_stdio(false);
    options_from(argc, argv);
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
        Request r{line, {}, lineno, {}, false};
        for (std::size_t start = 0;;) {
            const std::size_t space = line.find(' ', start);
            r.fields.push_back(line.substr(start, space - start));
            if (r.fields.back().empty()) fail("fields are separated by single spaces");
            if (space == std::string::npos) break;
            start = space + 1;
        }
        if (r.fields.back()[0] == '#') {  // the tag
            const std::string& tag = r.fields.back();
            const std::size_t colon = tag.find(':');
            if (colon != std::string::npos) r.stratum = tag.substr(1, colon - 1);
            r.fields.pop_back();
        }
        if (r.fields.size() < 2) fail("expected KERNEL FORMAT LIMB ... [#TAG]");
        const Map* ma = nullptr;
        for (const Map* c = maps; c->name; ++c)
            if (r.fields[0] == c->name) ma = c;
        if (ma) {
            flush();
            if (r.fields[1] == "binary64") complete_map<double>(*ma, r, ma->binary64);
            else if (r.fields[1] == "binary32") complete_map<float>(*ma, r, ma->binary32);
            else fail("this runner knows binary64 and binary32, not " + r.fields[1]);
            continue;
        }
        const Fold* fo = nullptr;
        for (const Fold* c = folds; c->name; ++c)
            if (r.fields[0] == c->name) fo = c;
        if (fo) {
            flush();
            if (r.fields[1] == "binary64") complete_fold<double>(*fo, r, fo->binary64);
            else if (r.fields[1] == "binary32") complete_fold<float>(*fo, r, fo->binary32);
            else fail("this runner knows binary64 and binary32, not " + r.fields[1]);
            continue;
        }
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
            const std::string& t = r.fields[std::size_t(2 + i)];
            if (k->in_kinds[i] == 'm') {
                if (t != "0" && t != "1") fail("not a mask: " + t);
                continue;
            }
            const double v = parse(t);
            const double top = std::numeric_limits<float>::max();
            if (!binary64 && v == v && v - v == 0 && (v > top || v < -top)) fail(t + " is not a binary32 number");
            if (!binary64 && v == v && static_cast<double>(static_cast<float>(v)) != v) fail(t + " is not a binary32 number");
            if (!(v - v == 0)) r.nonfinite = true;
        }
        if (k != segment_kernel || binary64 != segment_binary64) flush();
        segment_kernel = k;
        segment_binary64 = binary64;
        segment.push_back(std::move(r));
    }
    flush();
    write_files();
    return 0;
}
