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
#include <cstdio>
#include <cstdlib>
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
    int inputs, outputs;
    void (*binary64)(const double* in, double* out);
    void (*binary32)(const float* in, float* out);
};

// The same call text serves both limb types: overload resolution picks the kernel.
#define KAIRN_RUNNER_KERNEL(NAME, IN, OUT, CALL) \
    {#NAME, IN, OUT, [](const double* in, double* out) { CALL; }, [](const float* in, float* out) { CALL; }},
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
        if (int(fields.size()) - 2 != k->inputs) fail(fields[0] + " takes " + std::to_string(k->inputs) + " limbs");
        if (k->inputs > max_limbs || k->outputs > max_limbs) fail("too many limbs for this runner");
        out += " ->";
        if (fields[1] == "binary64") {
            double in[max_limbs], res[max_limbs];
            for (int i = 0; i < k->inputs; ++i) in[i] = parse(fields[2 + i]);
            k->binary64(in, res);
            for (int i = 0; i < k->outputs; ++i) {
                out += ' ';
                put(res[i], out);
            }
        } else if (fields[1] == "binary32") {
            float in[max_limbs], res[max_limbs];
            for (int i = 0; i < k->inputs; ++i) {
                const double v = parse(fields[2 + i]);
                const double top = std::numeric_limits<float>::max();
                // A finite double beyond the float range cannot even be converted (undefined).
                if (v == v && v - v == 0 && (v > top || v < -top)) fail(fields[2 + i] + " is not a binary32 number");
                in[i] = static_cast<float>(v);
                if (static_cast<double>(in[i]) != v && v == v) fail(fields[2 + i] + " is not a binary32 number");
            }
            k->binary32(in, res);
            for (int i = 0; i < k->outputs; ++i) {
                out += ' ';
                put(static_cast<double>(res[i]), out);
            }
        } else {
            fail("this runner knows binary64 and binary32, not " + fields[1]);
        }
        out += '\n';
        std::fwrite(out.data(), 1, out.size(), stdout);
    }
    return 0;
}
