// A runner of the kernels of the round-up interval on the line protocol (docs/developer/architecture.md,
// "The line protocol"; docs/developer/design/upward.md, "Claims and the oracle"): request lines on
// standard input, completed lines on standard output, a state its two lanes as stored,
// `upward_add_1 binary64 XU XN YU YN -> ZU ZN`. It requires the rounding mode upward set by
// kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math,
// MSVC /fp:strict), and holds a kairn::upward::Scope around each evaluation; the parsing and the
// printing run outside it, to nearest.
//
//   c++ -std=c++20 -frounding-math -I include -I gen/tests gen/tests/upward_runner.cpp -o runner
//   ./runner [--arrays] < requests > completed
//   ./runner --describe          the forms of this build, as "form SSE2 arrays AVX2 max sel"
//
// It runs the form of the kernels that include/kairn/gen/upward.hpp chooses for the build: one register
// (SSE2 on x86-64, NEON on arm64), or two numbers with -DKAIRN_UPWARD_FORM=KAIRN_UPWARD_FORM_NUMBERS;
// binary64 requests on double, binary32 on float. With --arrays, the requests of a kernel that has an
// array form (K_arrays) are completed through it, those of one kernel and format together, in chunks of
// the lengths of CHUNKS in turn (so that the loop of registers and the remainder after it both run,
// with every length of a remainder), every other chunk in place (the arrays written are the arrays of
// the first pair read); the requests of the other kernels as without --arrays. Built with
// -DKAIRN_UPWARD_RUNNER_ARRAYS, it runs so without the option (tests/CMakeLists.txt, which gives a
// runner none). The limbs printed are the interpreter's (kairn-gen interp): normalized hexadecimal
// literals, every NaN nan.
//
// Built with -DKAIRN_UPWARD_RUNNER_EMULATED (and linked with tests/emulated/number.cpp), it runs the
// kernels of tests/emulated/gen/upward.hpp on kairn::emulated::Number instead, on any format of the
// protocol (binary64, binary32, fp:P:QMIN:QMAX), max_nl in the form of --max sel (MAXPD's, the
// default) or --max nm (FMAXNM's on quiet NaNs): no mode, no scope, no array form.
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

#if defined(KAIRN_UPWARD_RUNNER_EMULATED)
#include "../../tests/emulated/gen/upward.hpp"
#else
#include "kairn/upward.hpp"
#include "kairn/gen/upward.hpp"
#endif

namespace {

#if defined(KAIRN_UPWARD_RUNNER_EMULATED)
using namespace kairn::emulated::upward;
using Number = kairn::emulated::Number;
#else
using namespace kairn::gen::upward;
#endif

long lineno = 0;

[[noreturn]] void fail(const std::string& why) {
    std::fflush(stdout);
    std::fprintf(stderr, "upward_runner: line %ld: %s\n", lineno, why.c_str());
    std::exit(2);
}

constexpr int max_limbs = 8;

template <class T>
struct Kernel {
    const char* name;
    const char* in_kinds;   // one letter per input value: l a limb, m a mask
    const char* out_kinds;
    void (*run)(const T* in, T* out, const bool* mi, bool* mo);
};

#define KAIRN_UPWARD_ARGS(T) \
    [[maybe_unused]] const T* in, [[maybe_unused]] T* out, [[maybe_unused]] const bool* mi, [[maybe_unused]] bool* mo

// The table of upward_kernels.inc for the limb type T, the call text the same for every type.
template <class T>
const std::vector<Kernel<T>>& kernels() {
    using P = pair<T>;
    static const std::vector<Kernel<T>> table = {
#define KAIRN_UPWARD_KERNEL(NAME, IN, OUT, ...) {#NAME, IN, OUT, [](KAIRN_UPWARD_ARGS(T)) { __VA_ARGS__ }},
#include "upward_kernels.inc"
#undef KAIRN_UPWARD_KERNEL
    };
    static_assert(sizeof(P) > 0);
    return table;
}

#if !defined(KAIRN_UPWARD_RUNNER_EMULATED)
template <class T>
struct Array {
    const char* name;
    int reads, numbers, writes;   // the arrays read (the lanes of the pairs), the numbers, the arrays written
    void (*run)(const T* const* a, const T* s, T* const* w, std::size_t n);
};

#define KAIRN_UPWARD_ARRAY_ARGS(T)                                                                    \
    [[maybe_unused]] const T* const* a, [[maybe_unused]] const T* s, [[maybe_unused]] T* const* w, \
        [[maybe_unused]] std::size_t n

template <class T>
const std::vector<Array<T>>& arrays() {
    static const std::vector<Array<T>> table = {
#define KAIRN_UPWARD_KERNEL(NAME, IN, OUT, ...)
#define KAIRN_UPWARD_ARRAY(NAME, READS, NUMBERS, WRITES, CALL) \
    {#NAME, READS, NUMBERS, WRITES, [](KAIRN_UPWARD_ARRAY_ARGS(T)) { CALL; }},
#include "upward_kernels.inc"
#undef KAIRN_UPWARD_ARRAY
#undef KAIRN_UPWARD_KERNEL
    };
    return table;
}

// The lengths of the chunks of an array run, in turn: every remainder of the AVX2 loop of floats
// (0 to 7) after zero, one and several registers, and longer runs.
constexpr std::size_t CHUNKS[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 23, 31, 64, 100};
#endif

// --- Limbs as text ----------------------------------------------------------------------------------

#if !defined(KAIRN_UPWARD_RUNNER_EMULATED)
// The interpreter's text of a finite nonzero value (-1)^s m 2^e: 0x1.HEXp+E with the fewest digits,
// or 0x1p+E.
std::string text_of(bool negative, std::uint64_t m, long e) {
    while ((m & 1) == 0) {
        m >>= 1;
        ++e;
    }
    int bits = 0;
    while ((m >> bits) > 1) ++bits;
    char buf[64];
    if (bits == 0) {
        std::snprintf(buf, sizeof buf, "0x1p%+ld", e);
    } else {
        const int digits = (bits + 3) / 4;
        const std::uint64_t frac = (m - (std::uint64_t{1} << bits)) << (4 * digits - bits);
        std::snprintf(buf, sizeof buf, "0x1.%0*llxp%+ld", digits, static_cast<unsigned long long>(frac), e + bits);
    }
    return std::string(negative ? "-" : "") + buf;
}

std::string text(double v) {
    std::uint64_t b;
    std::memcpy(&b, &v, sizeof b);
    const bool negative = (b >> 63) != 0;
    const std::uint64_t exp = (b >> 52) & 0x7ff, frac = b & 0xfffffffffffffu;
    if (exp == 0x7ff) return frac ? "nan" : negative ? "-inf" : "inf";
    if (exp == 0 && frac == 0) return negative ? "-0x0p+0" : "0x0p+0";
    if (exp == 0) return text_of(negative, frac, -1074);
    return text_of(negative, frac | (std::uint64_t{1} << 52), long(exp) - 1075);
}

std::string text(float v) {
    std::uint32_t b;
    std::memcpy(&b, &v, sizeof b);
    const bool negative = (b >> 31) != 0;
    const std::uint32_t exp = (b >> 23) & 0xff, frac = b & 0x7fffffu;
    if (exp == 0xff) return frac ? "nan" : negative ? "-inf" : "inf";
    if (exp == 0 && frac == 0) return negative ? "-0x0p+0" : "0x0p+0";
    if (exp == 0) return text_of(negative, frac, -149);
    return text_of(negative, frac | (std::uint32_t{1} << 23), long(exp) - 150);
}

// A limb is a C99 hexadecimal literal, inf, -inf or nan; strtod alone would also take decimals.
double parse64(const std::string& text) {
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

void parse_limb(const std::string& t, double& out) { out = parse64(t); }

void parse_limb(const std::string& t, float& out) {
    const double v = parse64(t);
    const double top = std::numeric_limits<float>::max();
    // A finite double beyond the float range cannot even be converted (undefined).
    if (v == v && v - v == 0 && (v > top || v < -top)) fail(t + " is not a binary32 number");
    out = static_cast<float>(v);
    if (static_cast<double>(out) != v && v == v) fail(t + " is not a binary32 number");
}

#else
void parse_limb(const std::string& t, Number& out) {
    std::string why;
    if (!kairn::emulated::parse(t, out, &why)) fail(why);
}
std::string text(Number v) { return kairn::emulated::to_text(v); }
#endif

// --- One request ------------------------------------------------------------------------------------

struct Request {
    std::size_t line;               // the index of its line
    std::vector<std::string> limbs; // the fields after KERNEL FORMAT, the tag left out
};

template <class T>
const Kernel<T>& find(const std::string& name) {
    for (const Kernel<T>& k : kernels<T>())
        if (name == k.name) return k;
    fail("unknown kernel " + name);
}

// The completion of one request by the kernel's function: " -> OUT ...".
template <class T>
std::string complete(const Kernel<T>& k, const std::vector<std::string>& fields) {
    const int inputs = int(std::strlen(k.in_kinds)), outputs = int(std::strlen(k.out_kinds));
    if (int(fields.size()) != inputs) fail(std::string(k.name) + " takes " + std::to_string(inputs) + " limbs");
    T in[max_limbs] = {}, res[max_limbs] = {};
    bool mi[max_limbs] = {}, mo[max_limbs] = {};
    for (int i = 0; i < inputs; ++i) {
        if (k.in_kinds[i] == 'm') {
            if (fields[i] != "0" && fields[i] != "1") fail("not a mask: " + fields[i]);
            mi[i] = fields[i] == "1";
        } else {
            parse_limb(fields[i], in[i]);
        }
    }
    {
#if !defined(KAIRN_UPWARD_RUNNER_EMULATED)
        kairn::upward::Scope scope;
#endif
        k.run(in, res, mi, mo);
    }
    std::string out = " ->";
    for (int i = 0; i < outputs; ++i) {
        out += ' ';
        out += k.out_kinds[i] == 'm' ? (mo[i] ? "1" : "0") : text(res[i]);
    }
    return out;
}

#if !defined(KAIRN_UPWARD_RUNNER_EMULATED)
// The completions of the requests of one kernel and format by its array form, in chunks.
template <class T>
void complete_arrays(const Array<T>& f, const std::vector<Request>& requests, std::vector<std::string>& outs) {
    const int width = f.reads + f.numbers;
    std::size_t start = 0, chunk = 0;
    while (start < requests.size()) {
        const std::size_t len = std::min(CHUNKS[chunk % (sizeof CHUNKS / sizeof CHUNKS[0])], requests.size() - start);
        // The requests of a chunk share their numbers: a chunk ends where they change.
        std::size_t n = 1;
        while (n < len && requests[start + n].limbs.size() == requests[start].limbs.size() &&
               [&] {
                   for (int j = f.reads; j < width; ++j)
                       if (requests[start + n].limbs[j] != requests[start].limbs[j]) return false;
                   return true;
               }())
            ++n;
        std::vector<std::vector<T>> a(f.reads, std::vector<T>(n)), w(f.writes, std::vector<T>(n));
        std::vector<T> s(f.numbers > 0 ? f.numbers : 1);
        for (std::size_t i = 0; i < n; ++i) {
            lineno = long(requests[start + i].line) + 1;
            const std::vector<std::string>& limbs = requests[start + i].limbs;
            if (int(limbs.size()) != width) fail(std::string(f.name) + " takes " + std::to_string(width) + " limbs");
            for (int j = 0; j < f.reads; ++j) parse_limb(limbs[j], a[j][i]);
            if (i == 0)
                for (int j = 0; j < f.numbers; ++j) parse_limb(limbs[f.reads + j], s[j]);
        }
        // In place every other chunk: the arrays written are those of the first pair read.
        const bool in_place = chunk % 2 == 1 && f.writes == 2;
        std::vector<const T*> ap(f.reads);
        std::vector<T*> wp(f.writes);
        for (int j = 0; j < f.reads; ++j) ap[j] = a[j].data();
        for (int j = 0; j < f.writes; ++j) wp[j] = in_place ? a[j].data() : w[j].data();
        {
            kairn::upward::Scope scope;
            f.run(ap.data(), s.data(), wp.data(), n);
        }
        for (std::size_t i = 0; i < n; ++i) {
            std::string& out = outs[requests[start + i].line];
            out += " ->";
            for (int j = 0; j < f.writes; ++j) out += ' ' + text(wp[j][i]);
        }
        start += n;
        ++chunk;
    }
}
#endif

std::vector<std::string> split(const std::string& line) {
    std::vector<std::string> fields;
    for (std::size_t start = 0;;) {
        const std::size_t space = line.find(' ', start);
        fields.push_back(line.substr(start, space - start));
        if (fields.back().empty()) fail("fields are separated by single spaces");
        if (space == std::string::npos) break;
        start = space + 1;
    }
    if (fields.back()[0] == '#') fields.pop_back();   // the tag
    if (fields.size() < 2) fail("expected KERNEL FORMAT LIMB ... [#TAG]");
    return fields;
}

}  // namespace

int main(int argc, char** argv) {
#if defined(KAIRN_UPWARD_RUNNER_ARRAYS)
    bool use_arrays = true;   // a build for the cross-checks, which give a runner no option
#else
    bool use_arrays = false;
#endif
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--describe") {
#if defined(KAIRN_UPWARD_RUNNER_EMULATED)
            std::printf("form EMULATED arrays NONE max %s\n", "option");
#else
            const char* form = KAIRN_UPWARD_FORM == KAIRN_UPWARD_FORM_SSE2   ? "SSE2"
                               : KAIRN_UPWARD_FORM == KAIRN_UPWARD_FORM_NEON ? "NEON"
                                                                             : "NUMBERS";
            const char* arr = KAIRN_UPWARD_ARRAYS == KAIRN_UPWARD_ARRAYS_AVX2   ? "AVX2"
                              : KAIRN_UPWARD_ARRAYS == KAIRN_UPWARD_ARRAYS_NEON ? "NEON"
                                                                                : "LOOP";
            std::printf("form %s arrays %s max %s\n", form, arr, KAIRN_UPWARD_MAX_NM ? "nm" : "sel");
#endif
            return 0;
        }
#if defined(KAIRN_UPWARD_RUNNER_EMULATED)
        if (arg == "--max" && i + 1 < argc) {
            const std::string form = argv[++i];
            if (form != "sel" && form != "nm") fail("--max sel or --max nm, not " + form);
            kairn::emulated::set_max_form(form == "nm" ? kairn::emulated::MaxForm::nm : kairn::emulated::MaxForm::sel);
            continue;
        }
#else
        if (arg == "--arrays") {
            use_arrays = true;
            continue;
        }
#endif
        std::fprintf(stderr, "upward_runner: unknown option %s\n", arg.c_str());
        return 2;
    }
    std::ios::sync_with_stdio(false);
    std::vector<std::string> lines, outs;
    for (std::string line; std::getline(std::cin, line);) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        lines.push_back(line);
    }
    outs = lines;
    // The requests that go to an array form, by kernel and format, in the order of their lines.
    struct Group {
        std::string kernel, format;
        std::vector<Request> requests;
    };
    std::vector<Group> groups;
    for (std::size_t i = 0; i < lines.size(); ++i) {
        lineno = long(i) + 1;
        const std::string& line = lines[i];
        if (line.empty() || line[0] == '#') continue;
        std::vector<std::string> fields = split(line);
        const std::string name = fields[0], format = fields[1];
        fields.erase(fields.begin(), fields.begin() + 2);
#if defined(KAIRN_UPWARD_RUNNER_EMULATED)
        kairn::emulated::Format f;
        std::string why;
        if (!kairn::emulated::parse_format(format, f)) fail("not a format: " + format);
        if (!kairn::emulated::set_format(f, &why)) fail(why);
        outs[i] += complete(find<Number>(name), fields);
        (void)use_arrays;
#else
        if (format != "binary64" && format != "binary32") fail("this runner knows binary64 and binary32, not " + format);
        bool array = false;
        if (use_arrays)
            for (const Array<double>& a : arrays<double>())
                if (name == a.name) array = true;
        if (array) {
            Group* g = nullptr;
            for (Group& h : groups)
                if (h.kernel == name && h.format == format) g = &h;
            if (!g) {
                groups.push_back({name, format, {}});
                g = &groups.back();
            }
            g->requests.push_back({i, fields});
            continue;
        }
        if (format == "binary64") outs[i] += complete(find<double>(name), fields);
        else outs[i] += complete(find<float>(name), fields);
#endif
    }
#if !defined(KAIRN_UPWARD_RUNNER_EMULATED)
    for (const Group& g : groups) {
        if (g.format == "binary64") {
            for (const Array<double>& a : arrays<double>())
                if (g.kernel == a.name) complete_arrays(a, g.requests, outs);
        } else {
            for (const Array<float>& a : arrays<float>())
                if (g.kernel == a.name) complete_arrays(a, g.requests, outs);
        }
    }
#endif
    for (const std::string& out : outs) {
        std::fwrite(out.data(), 1, out.size(), stdout);
        std::fputc('\n', stdout);
    }
    return 0;
}
