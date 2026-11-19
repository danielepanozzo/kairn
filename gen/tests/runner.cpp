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
constexpr int max_limbs = 16;

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
