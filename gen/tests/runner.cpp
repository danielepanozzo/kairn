// A minimal runner for the generated scalar kernels: request lines on standard input, completed
// lines on standard output (docs/developer/architecture.md, "The line protocol"). The generator's
// tests compare it with the interpreter; the library's test runner may start from it.
//
//   c++ -std=c++20 -I include -I gen/tests gen/tests/runner.cpp -o runner
//   ./runner < requests > completed
//
// It runs binary64 requests on double limbs and binary32 requests on float limbs. Another kernel
// header can stand in for the generated one (-DKAIRN_RUNNER_HEADER='"x.hpp"', with its own
// runner_kernels.inc earlier on the include path), which is how the tests run their own kernels.
// A mask, as an operand or a result, is 0 or 1.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

#ifndef KAIRN_RUNNER_HEADER
#define KAIRN_RUNNER_HEADER "kairn/gen/scalar.hpp"
#endif
#include KAIRN_RUNNER_HEADER

namespace {

struct Kernel {
    const char* name;
    const char* in_kinds;   // one letter per input value: l a limb, m a mask
    const char* out_kinds;
    void (*binary64)(const double* in, double* out, const bool* mi, bool* mo);
    void (*binary32)(const float* in, float* out, const bool* mi, bool* mo);
};

// The same call text serves both limb types: overload resolution picks the kernel. Limbs are
// in[i] and out[i], masks mi[i] and mo[i], i being the position among the inputs or outputs.
// Most kernels have no masks, or no limbs among their outputs: hence [[maybe_unused]].
#define KAIRN_RUNNER_ARGS(T) \
    [[maybe_unused]] const T* in, [[maybe_unused]] T* out, [[maybe_unused]] const bool* mi, [[maybe_unused]] bool* mo
#define KAIRN_RUNNER_KERNEL(NAME, IN, OUT, CALL) \
    {#NAME, IN, OUT, [](KAIRN_RUNNER_ARGS(double)) { CALL; }, [](KAIRN_RUNNER_ARGS(float)) { CALL; }},
const Kernel kernels[] = {
#include "runner_kernels.inc"
};
#undef KAIRN_RUNNER_KERNEL
constexpr int max_limbs = 16;

// The folds (docs/developer/architecture.md, "The line protocol", arrays): FOLD FORMAT ORDER N
// LIMB..., ORDER seq or lanes:W, then each limb array's N entries. The sequential order and the
// lane order with any number of lanes, from scalar.hpp.
struct Fold {
    const char* name;
    const char* arrays;     // the limbs of each array: "22" for two arrays of two limbs
    const char* out_kinds;
    void (*seq64)(const double* const* in, std::size_t n, std::size_t lanes, double* out, bool* mo);
    void (*lanes64)(const double* const* in, std::size_t n, std::size_t lanes, double* out, bool* mo);
    void (*seq32)(const float* const* in, std::size_t n, std::size_t lanes, float* out, bool* mo);
    void (*lanes32)(const float* const* in, std::size_t n, std::size_t lanes, float* out, bool* mo);
};
#define KAIRN_RUNNER_FOLD_ARGS(T)                                                                   \
    [[maybe_unused]] const T* const* in, [[maybe_unused]] std::size_t n, [[maybe_unused]] std::size_t lanes, \
        [[maybe_unused]] T* out, [[maybe_unused]] bool* mo
#define KAIRN_RUNNER_KERNEL(NAME, IN, OUT, CALL)
#define KAIRN_RUNNER_FOLD(NAME, ARRAYS, OUT, SEQ, LANES, PACKED)                                   \
    {#NAME, ARRAYS, OUT, [](KAIRN_RUNNER_FOLD_ARGS(double)) { SEQ; }, [](KAIRN_RUNNER_FOLD_ARGS(double)) { LANES; }, \
     [](KAIRN_RUNNER_FOLD_ARGS(float)) { SEQ; }, [](KAIRN_RUNNER_FOLD_ARGS(float)) { LANES; }},
const Fold folds[] = {
#include "runner_kernels.inc"
    {nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr},
};

long lineno = 0;

[[noreturn]] void fail(const std::string& why) {
    std::fflush(stdout);
    std::fprintf(stderr, "runner: line %ld: %s\n", lineno, why.c_str());
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
        out += "nan";  // the protocol has no signed NaN
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

// A binary32 limb: a binary64 literal that is a binary32 number.
float limb32(const std::string& text) {
    const double v = parse(text);
    const double top = std::numeric_limits<float>::max();
    // A finite double beyond the float range cannot even be converted (undefined).
    if (v == v && v - v == 0 && (v > top || v < -top)) fail(text + " is not a binary32 number");
    const float x = static_cast<float>(v);
    if (static_cast<double>(x) != v && v == v) fail(text + " is not a binary32 number");
    return x;
}

double limb(double, const std::string& text) { return parse(text); }
float limb(float, const std::string& text) { return limb32(text); }

// ORDER: seq, or lanes:W. Returns false for seq.
bool lane_order(const std::string& text, std::size_t& lanes) {
    if (text == "seq") return false;
    const std::string head = "lanes:";
    if (text.compare(0, head.size(), head) != 0 || text.size() == head.size() ||
        text.find_first_not_of("0123456789", head.size()) != std::string::npos ||
        (text[head.size()] == '0' && text.size() > head.size() + 1))
        fail("not an order: " + text + " (seq, or lanes:W)");
    lanes = std::stoull(text.substr(head.size()));
    return true;
}

std::size_t length(const std::string& text) {
    if (text.empty() || text.find_first_not_of("0123456789") != std::string::npos || (text[0] == '0' && text.size() > 1))
        fail("not a length: " + text);
    return std::stoull(text);
}

template <class T>
void complete_fold(const Fold& f, const std::vector<std::string>& fields, std::string& out,
                   void (*seq)(const T* const*, std::size_t, std::size_t, T*, bool*),
                   void (*lanes_fn)(const T* const*, std::size_t, std::size_t, T*, bool*)) {
    if (fields.size() < 4) fail(std::string("expected ") + f.name + " FORMAT ORDER N LIMB ... [#TAG]");
    std::size_t lanes = 0;
    const bool by_lanes = lane_order(fields[2], lanes);
    const std::size_t n = length(fields[3]);
    std::size_t arrays = 0;
    for (const char* a = f.arrays; *a; ++a) arrays += std::size_t(*a - '0');
    if (fields.size() - 4 != arrays * n) fail(std::string(f.name) + " of length " + fields[3] + " takes " +
                                              std::to_string(arrays * n) + " limbs");
    const int outputs = int(std::strlen(f.out_kinds));
    if (outputs > max_limbs) fail("too many outputs for this runner");
    std::vector<T> data(arrays * n);
    for (std::size_t i = 0; i < data.size(); ++i) data[i] = limb(T(), fields[4 + i]);
    std::vector<const T*> in(arrays);
    for (std::size_t l = 0; l < arrays; ++l) in[l] = data.data() + l * n;
    T res[max_limbs] = {};
    bool mo[max_limbs] = {};
    (by_lanes ? lanes_fn : seq)(in.data(), n, lanes, res, mo);
    for (int i = 0; i < outputs; ++i) {
        out += ' ';
        if (f.out_kinds[i] == 'm') out += mo[i] ? '1' : '0';
        else put(static_cast<double>(res[i]), out);
    }
}

}  // namespace

int main() {
    std::ios::sync_with_stdio(false);
    std::string line, out;
    std::vector<std::string> fields;
    while (std::getline(std::cin, line)) {
        ++lineno;
        if (!line.empty() && line.back() == '\r') line.pop_back();
        out = line;
        if (line.empty() || line[0] == '#') {
            out += '\n';
            std::fwrite(out.data(), 1, out.size(), stdout);
            continue;
        }
        fields.clear();
        for (std::size_t start = 0;;) {
            const std::size_t space = line.find(' ', start);
            fields.push_back(line.substr(start, space - start));
            if (fields.back().empty()) fail("fields are separated by single spaces");
            if (space == std::string::npos) break;
            start = space + 1;
        }
        if (fields.back()[0] == '#') fields.pop_back();  // the tag
        if (fields.size() < 2) fail("expected KERNEL FORMAT LIMB ... [#TAG]");
        const Fold* fo = nullptr;
        for (const Fold* c = folds; c->name; ++c)
            if (fields[0] == c->name) fo = c;
        if (fo) {
            out += " ->";
            if (fields[1] == "binary64") complete_fold<double>(*fo, fields, out, fo->seq64, fo->lanes64);
            else if (fields[1] == "binary32") complete_fold<float>(*fo, fields, out, fo->seq32, fo->lanes32);
            else fail("this runner knows binary64 and binary32, not " + fields[1]);
            out += '\n';
            std::fwrite(out.data(), 1, out.size(), stdout);
            continue;
        }
        const Kernel* k = nullptr;
        for (const Kernel& c : kernels)
            if (fields[0] == c.name) k = &c;
        if (!k) fail("unknown kernel " + fields[0]);
        const int inputs = int(std::strlen(k->in_kinds)), outputs = int(std::strlen(k->out_kinds));
        if (int(fields.size()) - 2 != inputs) fail(fields[0] + " takes " + std::to_string(inputs) + " limbs");
        if (inputs > max_limbs || outputs > max_limbs) fail("too many limbs for this runner");
        bool mi[max_limbs] = {}, mo[max_limbs] = {};
        for (int i = 0; i < inputs; ++i) {
            if (k->in_kinds[i] != 'm') continue;
            if (fields[2 + i] != "0" && fields[2 + i] != "1") fail("not a mask: " + fields[2 + i]);
            mi[i] = fields[2 + i] == "1";
        }
        out += " ->";
        if (fields[1] == "binary64") {
            double in[max_limbs] = {}, res[max_limbs] = {};
            for (int i = 0; i < inputs; ++i)
                if (k->in_kinds[i] == 'l') in[i] = parse(fields[2 + i]);
            k->binary64(in, res, mi, mo);
            for (int i = 0; i < outputs; ++i) {
                out += ' ';
                if (k->out_kinds[i] == 'm') out += mo[i] ? '1' : '0';
                else put(res[i], out);
            }
        } else if (fields[1] == "binary32") {
            float in[max_limbs] = {}, res[max_limbs] = {};
            for (int i = 0; i < inputs; ++i) {
                if (k->in_kinds[i] != 'l') continue;
                const double v = parse(fields[2 + i]);
                const double top = std::numeric_limits<float>::max();
                // A finite double beyond the float range cannot even be converted (undefined).
                if (v == v && v - v == 0 && (v > top || v < -top)) fail(fields[2 + i] + " is not a binary32 number");
                in[i] = static_cast<float>(v);
                if (static_cast<double>(in[i]) != v && v == v) fail(fields[2 + i] + " is not a binary32 number");
            }
            k->binary32(in, res, mi, mo);
            for (int i = 0; i < outputs; ++i) {
                out += ' ';
                if (k->out_kinds[i] == 'm') out += mo[i] ? '1' : '0';
                else put(static_cast<double>(res[i]), out);
            }
        } else {
            fail("this runner knows binary64 and binary32, not " + fields[1]);
        }
        out += '\n';
        std::fwrite(out.data(), 1, out.size(), stdout);
    }
    return 0;
}
