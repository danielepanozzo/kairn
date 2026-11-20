// A runner of kairn::rational for the oracle (docs/developer/testing.md, "Constants from
// integers"): request lines on standard input, completed lines on standard output.
//
//   request     rational_K FORMAT NUM DEN [#TAG]
//   completed   rational_K FORMAT NUM DEN [#TAG] -> LIMB ... ERROR EXACT
//
// K is 1 or 2, FORMAT binary64 (double limbs) or binary32 (float limbs), NUM and DEN decimal
// signed 64-bit integers (DEN may be 0). The runner computes kairn::rational<Expansion<T, K>>(NUM,
// DEN) at run time and writes the request unchanged, then " -> ", the K limbs of the value, the
// error, and 0 or 1 for exact, separated by single spaces; limbs are written as tests/api/runner.cpp
// writes them (C99 hexadecimal, inf, -inf, nan). Empty lines and lines that start with # are copied
// as they are.
//
// Each result is also given to kairn::is_rational_result, the check that kairn::rational makes in
// constant evaluation: the runner fails, naming the line, if it refuses a result, so that the test
// also runs the checker on every case the oracle sends. Built with KAIRN_TEST_CHECKS (the debug
// build of tests/api/flags/), KAIRN_CHECKS keeps its default, 1, and kairn::rational makes that
// check itself.
#if !defined(KAIRN_TEST_CHECKS)
#define KAIRN_CHECKS 0
#endif
#include <kairn/kairn.hpp>
#if defined(KAIRN_TEST_CHECKS) && KAIRN_CHECKS != 1
#error "built with KAIRN_TEST_CHECKS, the runner must have KAIRN_CHECKS 1: build it without NDEBUG"
#endif

#include "no_crash_reports.hpp"

#include <charconv>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
#include <system_error>
#include <vector>

namespace {

long lineno = 0;

[[noreturn]] void fail(const std::string& why) {
    std::fflush(stdout);
    std::fprintf(stderr, "rational runner: line %ld: %s\n", lineno, why.c_str());
    std::exit(2);
}

// A decimal signed 64-bit integer, all of the text: -9223372036854775808 to 9223372036854775807.
long long parse(const std::string& text) {
    long long v = 0;
    const char* end = text.data() + text.size();
    const auto [ptr, ec] = std::from_chars(text.data(), end, v);
    if (ec != std::errc() || ptr != end || text.empty()) fail("not a signed 64-bit integer: " + text);
    return v;
}

// As tests/api/runner.cpp writes a limb.
void put_limb(double v, std::string& out) {
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

template <class T, int K>
void complete(long long num, long long den, std::string& out) {
    using X = kairn::Expansion<T, K>;
    const kairn::Constant<X> c = kairn::rational<X>(num, den);
    if (!kairn::is_rational_result(c, num, den)) fail("kairn::is_rational_result refuses the result");
    for (int i = 0; i < K; ++i) {
        out += ' ';
        put_limb(static_cast<double>(c.value.limb[i]), out);
    }
    out += ' ';
    put_limb(static_cast<double>(c.error), out);
    out += c.exact ? " 1" : " 0";
}

}  // namespace

int main(int argc, char**) {
    kairn_test::no_crash_reports();
    if (argc != 1) {
        std::fprintf(stderr, "usage: rational_runner < requests > completed\n");
        return 2;
    }
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
        if (fields.size() != 4) fail("expected rational_K FORMAT NUM DEN [#TAG]");
        const long long num = parse(fields[2]), den = parse(fields[3]);
        out += " ->";
        const std::string& kind = fields[0];
        const std::string& format = fields[1];
        if (kind != "rational_1" && kind != "rational_2") fail("not rational_1 or rational_2: " + kind);
        const bool two = kind == "rational_2";
        if (format == "binary64") {
            if (two) complete<double, 2>(num, den, out);
            else complete<double, 1>(num, den, out);
        } else if (format == "binary32") {
            if (two) complete<float, 2>(num, den, out);
            else complete<float, 1>(num, den, out);
        } else {
            fail("this runner knows binary64 and binary32, not " + format);
        }
        out += '\n';
        std::fwrite(out.data(), 1, out.size(), stdout);
    }
    return 0;
}
