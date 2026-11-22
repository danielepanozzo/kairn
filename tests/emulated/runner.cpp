// The runner of the emulated kernels (gen/kernels.hpp): request lines on standard input, completed
// lines on standard output (docs/developer/architecture.md, "The line protocol"), in any format
// whose constants gen/kernels.hpp has (gen/kairn_gen/emulated.py, FORMATS: binary64, binary32 and
// formats of the statements of precision 8 to 11), the format of each request taken from its line.
//
//   runner [--ce] < requests > completed
//
// The same requests as the compiled runner of gen/tests/runner.cpp and the interpreter
// (python3 gen/kairn-gen interp): kernels, folds, maps (inplace=I included), ball vectors,
// convolutions and the products of two BallVectors, from the same table (runner_kernels.inc).
// --ce runs the path of constant evaluation, as the interpreter's --ce does: a kernel's
// constant-evaluation variant (two_prod's Dekker product), each prod a plain product, guard its
// operand, times_inf from comparisons; a kernel that has no such path, or a fold, is refused there.
// A request it cannot complete (a format whose constants it does not have, a limb that is not a
// number of the format, an unknown kernel) stops it with status 2 and the reason, after the lines
// before it.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

#include "gen/kernels.hpp"

namespace {

using kairn::emulated::Number;
using T = Number;

constexpr int max_limbs = 16;

struct Kernel {
    const char* name;
    const char* in_kinds;
    const char* out_kinds;
    void (*run)(const T* in, T* out, const bool* mi, bool* mo);
};
#define KAIRN_RUNNER_ARGS \
    [[maybe_unused]] const T* in, [[maybe_unused]] T* out, [[maybe_unused]] const bool* mi, [[maybe_unused]] bool* mo
#define KAIRN_RUNNER_KERNEL(NAME, IN, OUT, CALL) {#NAME, IN, OUT, [](KAIRN_RUNNER_ARGS) { CALL; }},
const Kernel kernels[] = {
#include "runner_kernels.inc"
};
#undef KAIRN_RUNNER_KERNEL

struct Fold {
    const char* name;
    const char* arrays;
    const char* out_kinds;
    void (*seq)(const T* const* in, std::size_t n, std::size_t lanes, T* out, bool* mo);
    void (*lanes)(const T* const* in, std::size_t n, std::size_t lanes, T* out, bool* mo);
};
#define KAIRN_RUNNER_FOLD_ARGS                                                                      \
    [[maybe_unused]] const T* const* in, [[maybe_unused]] std::size_t n, [[maybe_unused]] std::size_t lanes, \
        [[maybe_unused]] T* out, [[maybe_unused]] bool* mo
#define KAIRN_RUNNER_KERNEL(NAME, IN, OUT, CALL)
#define KAIRN_RUNNER_FOLD(NAME, ARRAYS, OUT, SEQ, LANES, PACKED) \
    {#NAME, ARRAYS, OUT, [](KAIRN_RUNNER_FOLD_ARGS) { SEQ; }, [](KAIRN_RUNNER_FOLD_ARGS) { LANES; }},
const Fold folds[] = {
#include "runner_kernels.inc"
    {nullptr, nullptr, nullptr, nullptr, nullptr},
};
#undef KAIRN_RUNNER_FOLD

struct Map {
    const char* name;
    const char* arrays;
    int scalars;
    int writes;
    int radius;     // 1 for a ball vector
    void (*seq)(const T* const* in, std::size_t n, std::size_t lanes, const T* sc, T* const* w, T* out, bool* mo);
    void (*lanes)(const T* const* in, std::size_t n, std::size_t lanes, const T* sc, T* const* w, T* out, bool* mo);
};
#define KAIRN_RUNNER_MAP_ARGS                                                                       \
    [[maybe_unused]] const T* const* in, [[maybe_unused]] std::size_t n, [[maybe_unused]] std::size_t lanes, \
        [[maybe_unused]] const T* sc, [[maybe_unused]] T* const* w, [[maybe_unused]] T* out, [[maybe_unused]] bool* mo
#define KAIRN_RUNNER_FOLD(NAME, ARRAYS, OUT, SEQ, LANES, PACKED)
#define KAIRN_RUNNER_MAP(NAME, ARRAYS, SCALARS, WRITES, SEQ, LANES, PACKED) \
    {#NAME, ARRAYS, SCALARS, WRITES, 0, [](KAIRN_RUNNER_MAP_ARGS) { SEQ; }, [](KAIRN_RUNNER_MAP_ARGS) { LANES; }},
#define KAIRN_RUNNER_BV(NAME, ARRAYS, SCALARS, WRITES, SEQ, LANES, PACKED) \
    {#NAME, ARRAYS, SCALARS, WRITES, 1, [](KAIRN_RUNNER_MAP_ARGS) { SEQ; }, [](KAIRN_RUNNER_MAP_ARGS) { LANES; }},
const Map maps[] = {
#include "runner_kernels.inc"
    {nullptr, nullptr, 0, 0, 0, nullptr, nullptr},
};
#undef KAIRN_RUNNER_BV
#undef KAIRN_RUNNER_MAP

struct Conv {
    const char* name;
    const char* arrays;
    int scalars;
    int writes;
    int radius;     // 1 for a product of ball vectors
    void (*seq)(const T* const* in, std::size_t nx, std::size_t ny, const T* sc, T* const* w, T* out, bool* mo);
};
#define KAIRN_RUNNER_CONV_ARGS                                                                      \
    [[maybe_unused]] const T* const* in, [[maybe_unused]] std::size_t nx, [[maybe_unused]] std::size_t ny, \
        [[maybe_unused]] const T* sc, [[maybe_unused]] T* const* w, [[maybe_unused]] T* out, [[maybe_unused]] bool* mo
#define KAIRN_RUNNER_MAP(NAME, ARRAYS, SCALARS, WRITES, SEQ, LANES, PACKED)
#define KAIRN_RUNNER_CONV(NAME, ARRAYS, WRITES, SEQ) {#NAME, ARRAYS, 0, WRITES, 0, [](KAIRN_RUNNER_CONV_ARGS) { SEQ; }},
#define KAIRN_RUNNER_BV_CONV(NAME, ARRAYS, SCALARS, WRITES, SEQ) \
    {#NAME, ARRAYS, SCALARS, WRITES, 1, [](KAIRN_RUNNER_CONV_ARGS) { SEQ; }},
const Conv convs[] = {
#include "runner_kernels.inc"
    {nullptr, nullptr, 0, 0, 0, nullptr},
};
#undef KAIRN_RUNNER_BV_CONV
#undef KAIRN_RUNNER_CONV

long lineno = 0;
bool consteval_path = false;

[[noreturn]] void fail(const std::string& why) {
    std::fflush(stdout);
    std::fprintf(stderr, "emulated runner: line %ld: %s\n", lineno, why.c_str());
    std::exit(2);
}

std::string current;    // the format of the last request

// The format of a request: switched to, with its constants, when it changes.
void use_format(const std::string& name) {
    if (name == current) return;
    namespace g = kairn::emulated::generated;
    kairn::emulated::Format f;
    if (name == "binary64") f = {53, -1074, 971};
    else if (name == "binary32") f = {24, -149, 104};
    else {
        char tail = 0;
        if (std::sscanf(name.c_str(), "fp:%d:%d:%d%c", &f.p, &f.qmin, &f.qmax, &tail) != 3)
            fail("not a format: " + name + " (binary64, binary32 or fp:P:QMIN:QMAX)");
    }
    const g::FormatConstants* table = nullptr;
    for (const auto& t : g::formats)
        if (t.p == f.p && t.qmin == f.qmin && t.qmax == f.qmax) table = &t;
    if (!table) {
        std::string known;
        for (const auto& t : g::formats) known += std::string(known.empty() ? "" : ", ") + t.name;
        fail("the emulated kernels have the constants of these formats only (gen/kairn_gen/emulated.py): " + known +
             "; not of " + name);
    }
    std::string why;
    if (!kairn::emulated::set_format(f, &why)) fail(name + ": " + why);
    T values[g::constant_count];
    bool defined[g::constant_count];
    for (int i = 0; i < g::constant_count; ++i) {
        defined[i] = table->values[i] != nullptr;
        if (defined[i] && !kairn::emulated::parse(table->values[i], values[i], &why))
            fail(std::string("constant ") + g::constant_names[i] + " in " + name + ": " + why);
    }
    kairn::emulated::set_constants(values, defined, g::constant_count);
    current = name;
}

T limb(const std::string& text) {
    T v;
    std::string why;
    if (!kairn::emulated::parse(text, v, &why)) fail(why + " (format " + current + ")");
    return v;
}

void put(T v, std::string& out) { out += kairn::emulated::to_text(v); }

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

void complete_fold(const Fold& f, const std::vector<std::string>& fields, std::string& out) {
    if (fields.size() < 4) fail(std::string("expected ") + f.name + " FORMAT ORDER N LIMB ... [#TAG]");
    std::size_t lanes = 0;
    const bool by_lanes = lane_order(fields[2], lanes);
    const std::size_t n = length(fields[3]);
    std::size_t arrays = 0;
    for (const char* a = f.arrays; *a; ++a) arrays += std::size_t(*a - '0');
    if (fields.size() - 4 != arrays * n)
        fail(std::string(f.name) + " of length " + fields[3] + " takes " + std::to_string(arrays * n) + " limbs");
    const int outputs = int(std::strlen(f.out_kinds));
    std::vector<T> data(arrays * n);
    for (std::size_t i = 0; i < data.size(); ++i) data[i] = limb(fields[4 + i]);
    std::vector<const T*> in(arrays);
    for (std::size_t l = 0; l < arrays; ++l) in[l] = data.data() + l * n;
    T res[max_limbs] = {};
    bool mo[max_limbs] = {};
    (by_lanes ? f.lanes : f.seq)(in.data(), n, lanes, res, mo);
    for (int i = 0; i < outputs; ++i) {
        out += ' ';
        if (f.out_kinds[i] == 'm') out += mo[i] ? '1' : '0';
        else put(res[i], out);
    }
}

long in_place(const Map& m, const std::vector<std::string>& fields, std::size_t& at) {
    const std::string head = "inplace=";
    if (fields.size() <= at || fields[at].compare(0, head.size(), head) != 0) return -1;
    const std::size_t i = length(fields[at].substr(head.size()));
    if (i >= std::strlen(m.arrays) || m.arrays[i] - '0' != m.writes)
        fail(fields[at] + ": not an array read with as many limbs as the array written");
    ++at;
    return long(i);
}

void complete_map(const Map& m, const std::vector<std::string>& fields, std::string& out) {
    if (fields.size() < 4) fail(std::string("expected ") + m.name + " FORMAT ORDER N SCALAR ... LIMB ... [#TAG]");
    std::size_t lanes = 0;
    const bool by_lanes = lane_order(fields[2], lanes);
    const std::size_t n = length(fields[3]);
    std::size_t arrays = 0;
    for (const char* a = m.arrays; *a; ++a) arrays += std::size_t(*a - '0');
    const std::size_t scalars = std::size_t(m.scalars);
    std::size_t at = 4;
    const long place = in_place(m, fields, at);
    if (fields.size() - at != scalars + arrays * n)
        fail(std::string(m.name) + " of length " + fields[3] + " takes " + std::to_string(scalars + arrays * n) + " limbs");
    std::vector<T> sc(scalars + 1), data(arrays * n + 1);
    for (std::size_t i = 0; i < scalars; ++i) sc[i] = limb(fields[at + i]);
    for (std::size_t i = 0; i < arrays * n; ++i) data[i] = limb(fields[at + scalars + i]);
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
    (by_lanes ? m.lanes : m.seq)(in.data(), n, lanes, sc.data(), w.data(), res, mo);
    for (int l = 0; l < m.writes; ++l)
        for (std::size_t i = 0; i < n; ++i) {
            out += ' ';
            put(w[std::size_t(l)][i], out);
        }
    if (m.radius) {
        out += ' ';
        put(res[0], out);
    }
    out += mo[0] ? " 1" : " 0";
}

void complete_conv(const Conv& c, const std::vector<std::string>& fields, std::string& out) {
    if (fields.size() < 5) fail(std::string("expected ") + c.name + " FORMAT seq N_X N_Y LIMB ... [#TAG]");
    std::size_t lanes = 0;
    if (lane_order(fields[2], lanes)) fail(std::string(c.name) + " has the sequential order only (seq)");
    const std::size_t nx = length(fields[3]), ny = length(fields[4]);
    if (std::strlen(c.arrays) != 2) fail("a convolution reads two arrays");
    const std::size_t lx = std::size_t(c.arrays[0] - '0'), ly = std::size_t(c.arrays[1] - '0');
    const std::size_t scalars = std::size_t(c.scalars);
    if (fields.size() - 5 != scalars + lx * nx + ly * ny)
        fail(std::string(c.name) + " of lengths " + fields[3] + " and " + fields[4] + " takes " +
             std::to_string(scalars + lx * nx + ly * ny) + " limbs");
    std::vector<T> sc(scalars + 1), data(lx * nx + ly * ny + 1);
    for (std::size_t i = 0; i < scalars; ++i) sc[i] = limb(fields[5 + i]);
    for (std::size_t i = 0; i + 5 + scalars < fields.size(); ++i) data[i] = limb(fields[5 + scalars + i]);
    std::vector<const T*> in(lx + ly + 1);
    for (std::size_t l = 0; l < lx; ++l) in[l] = data.data() + l * nx;
    for (std::size_t l = 0; l < ly; ++l) in[lx + l] = data.data() + lx * nx + l * ny;
    const std::size_t nz = nx == 0 || ny == 0 ? 0 : nx + ny - 1;
    std::vector<T> written(std::size_t(c.writes) * nz + 1);
    std::vector<T*> w(std::size_t(c.writes) + 1);
    for (int l = 0; l < c.writes; ++l) w[std::size_t(l)] = written.data() + std::size_t(l) * nz;
    bool mo[1] = {};
    T res[1] = {};
    c.seq(in.data(), nx, ny, sc.data(), w.data(), res, mo);
    for (std::size_t i = 0; i < std::size_t(c.writes) * nz; ++i) {
        out += ' ';
        put(written[i], out);
    }
    if (c.radius) {
        out += ' ';
        put(res[0], out);
    }
    out += mo[0] ? " 1" : " 0";
}

bool has_consteval_path(const char* name) {
    for (const char* const* k = kairn::emulated::generated::not_constexpr; *k; ++k)
        if (std::strcmp(*k, name) == 0) return false;
    return true;
}

// --ce-paths: each kernel that has a path of constant evaluation, and the kernel whose listing that
// path runs (itself, or its variant), one per line (tests/crosscheck.py, --emulated-ce).
int ce_paths() {
    for (const Kernel& k : kernels) {
        if (!has_consteval_path(k.name)) continue;
        const char* listing = k.name;
        for (const auto* v = kairn::emulated::generated::ce_variants; (*v)[0]; ++v)
            if (std::strcmp((*v)[0], k.name) == 0) listing = (*v)[1];
        std::printf("%s %s\n", k.name, listing);
    }
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--ce") == 0) {
            consteval_path = true;
        } else if (std::strcmp(argv[i], "--ce-paths") == 0) {
            return ce_paths();
        } else {
            std::fprintf(stderr, "usage: %s [--ce] < requests > completed\n       %s --ce-paths\n", argv[0],
                         argv[0]);
            return 2;
        }
    }
    kairn::emulated::set_constant_evaluation(consteval_path);
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
        use_format(fields[1]);
        const Conv* co = nullptr;
        for (const Conv* c = convs; c->name; ++c)
            if (fields[0] == c->name) co = c;
        const Map* ma = nullptr;
        for (const Map* c = maps; c->name; ++c)
            if (fields[0] == c->name) ma = c;
        const Fold* fo = nullptr;
        for (const Fold* c = folds; c->name; ++c)
            if (fields[0] == c->name) fo = c;
        if ((co || ma || fo) && consteval_path) fail(fields[0] + " is a fold, which has no path of constant evaluation");
        out += " ->";
        if (co) {
            complete_conv(*co, fields, out);
        } else if (ma) {
            complete_map(*ma, fields, out);
        } else if (fo) {
            complete_fold(*fo, fields, out);
        } else {
            const Kernel* k = nullptr;
            for (const Kernel& c : kernels)
                if (fields[0] == c.name) k = &c;
            if (!k) fail("unknown kernel " + fields[0]);
            if (consteval_path && !has_consteval_path(k->name))
                fail(fields[0] + " has no path of constant evaluation: a fused operation other than prod and no variant");
            const int inputs = int(std::strlen(k->in_kinds)), outputs = int(std::strlen(k->out_kinds));
            if (int(fields.size()) - 2 != inputs) fail(fields[0] + " takes " + std::to_string(inputs) + " limbs");
            if (inputs > max_limbs || outputs > max_limbs) fail("too many limbs for this runner");
            bool mi[max_limbs] = {}, mo[max_limbs] = {};
            T in[max_limbs] = {}, res[max_limbs] = {};
            for (int i = 0; i < inputs; ++i) {
                if (k->in_kinds[i] == 'm') {
                    if (fields[2 + i] != "0" && fields[2 + i] != "1") fail("not a mask: " + fields[2 + i]);
                    mi[i] = fields[2 + i] == "1";
                } else {
                    in[i] = limb(fields[2 + i]);
                }
            }
            k->run(in, res, mi, mo);
            for (int i = 0; i < outputs; ++i) {
                out += ' ';
                if (k->out_kinds[i] == 'm') out += mo[i] ? '1' : '0';
                else put(res[i], out);
            }
        }
        out += '\n';
        std::fwrite(out.data(), 1, out.size(), stdout);
    }
    return 0;
}
