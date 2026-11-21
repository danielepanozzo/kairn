// The driver of the benchmark of Milestone 2 (bench/README.md, "Milestone 2"; bench/m2_data.hpp):
//
//   kairn-bench-m2-O2 [--json FILE] [--machine TEXT] [--commit TEXT] [--date TEXT] [--cpu N]
//                     [--reps R] [--sample-ms MS] [--filter A,B,...] [--wide N] [--check-only]
//                     [--list]
//
// 1. Makes the inputs from a fixed seed (m2_setup).
// 2. Checks every timed function against its reference, BACKEND/KIND/KERNEL/kairn (m2p against
//    m2s), byte for byte, or by its own check; counts, for each rounding-mode prop, how many of its
//    results differ from the result rounded to nearest (a prop that ignored the mode would have
//    returned those); and checks the props of the building blocks against Kairn's on a wide sample
//    of operands. It refuses to time anything if one check fails.
// 3. Measures the tightness of the Horner evaluation.
// 4. Times every function whose name contains one of the --filter texts (all without --filter):
//    calibrates a sample of about --sample-ms, then takes --reps samples of each, in rounds over all
//    functions, and reports the minimum, median and maximum time per operation.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <string>
#include <vector>

#include "bench_util.hpp"
#include "m2_data.hpp"

#ifndef KAIRN_BENCH_FLAGS
#define KAIRN_BENCH_FLAGS "unknown"
#endif
#ifndef KAIRN_BENCH_FENV_FLAGS
#define KAIRN_BENCH_FENV_FLAGS "unknown"
#endif
#ifndef KAIRN_BENCH_SETTING
#define KAIRN_BENCH_SETTING "inline"
#endif

namespace m2 = kairn_bench::m2;
namespace u = kairn_bench::util;

namespace {

struct Name {
    std::string backend, kind, kernel, variant;
};
Name split(const std::string& s) {
    Name n;
    std::string* part[4] = {&n.backend, &n.kind, &n.kernel, &n.variant};
    int k = 0;
    for (char ch : s) {
        if (ch == '/' && k < 3)
            ++k;
        else
            part[k]->push_back(ch);
    }
    return n;
}

std::vector<const m2::Entry*> all_entries() {
    std::vector<const m2::Entry*> v;
    for (const m2::Entry* t : {m2::m2_entries, m2::m2_fenv_entries, m2::m2_packed_entries, m2::m2_fenv_packed_entries})
        for (const m2::Entry* e = t; e->name; ++e) v.push_back(e);
    return v;
}
const m2::Entry* find(const std::vector<const m2::Entry*>& v, const std::string& name) {
    for (const m2::Entry* e : v)
        if (name == e->name) return e;
    return nullptr;
}

std::size_t value_size(const m2::Entry& e) { return e.bits == 32 ? sizeof(float) : sizeof(double); }

// Runs e on cleared outputs and returns the bytes of its values.
std::vector<unsigned char> run_and_read(const m2::Entry& e) {
    m2::m2_clear(e.bits);
    e.fn(m2::m2_data(e.bits));
    std::size_t bytes = 0;
    const unsigned char* p = m2::m2_region(e.bits, e.region, &bytes);
    const std::size_t n = std::size_t(e.values) * value_size(e);
    if (!p || n > bytes) return {};
    return std::vector<unsigned char>(p, p + n);
}

double value_at(const std::vector<unsigned char>& b, std::size_t i, int bits) {
    if (bits == 32) {
        float f;
        std::memcpy(&f, b.data() + 4 * i, 4);
        return f;
    }
    double d;
    std::memcpy(&d, b.data() + 8 * i, 8);
    return d;
}

bool check_against(const m2::Entry& e, const m2::Entry& ref, std::string& why) {
    if (e.values != ref.values || e.bits != ref.bits) {
        why = "not the same number of values as the reference";
        return false;
    }
    const std::vector<unsigned char> want = run_and_read(ref), got = run_and_read(e);
    if (want.empty() || got.size() != want.size()) {
        why = "no outputs";
        return false;
    }
    const std::size_t w = value_size(e);
    for (std::size_t i = 0; i < got.size(); i += w)
        if (std::memcmp(got.data() + i, want.data() + i, w) != 0) {
            char buf[160];
            std::snprintf(buf, sizeof buf, "value %zu: %a != %a", i / w, value_at(got, i / w, e.bits),
                          value_at(want, i / w, e.bits));
            why = buf;
            return false;
        }
    return true;
}

// The kernel of the same outputs rounded to nearest, for the props of directed rounding.
std::string nearest_of(const std::string& kernel) {
    if (kernel == "add_down" || kernel == "add_up") return "add";
    if (kernel == "sub_down" || kernel == "sub_up") return "sub";
    if (kernel == "mul_down" || kernel == "mul_up") return "mul";
    if (kernel == "interval_add_1") return "pair_add_1";
    if (kernel == "interval_sub_1") return "pair_sub_1";
    if (kernel == "interval_mul_1") return "plain4_mul_1";
    return "";
}

// --- The wide check of the props of the building blocks -----------------------------------------

struct Wide {
    int bits, op, variant;
    long compared = 0, equal = 0, zero_sign = 0, below_p_wider = 0, failed = 0, differ_from_nearest = 0;
};

template <class T>
T random_finite(u::Rng& g) {
    for (;;) {
        T a;
        if constexpr (sizeof(T) == 8) {
            const std::uint64_t b = g.next();
            std::memcpy(&a, &b, 8);
        } else {
            const std::uint32_t b = std::uint32_t(g.next());
            std::memcpy(&a, &b, 4);
        }
        if (std::isfinite(a)) return a;
    }
}

template <class T>
void wide_check(int n, std::vector<Wide>& out, std::string& log) {
    const int bits = int(8 * sizeof(T));
    // P = 2^(2p - 1) eta: below it the error of a product need not be a number of T, and Kairn's
    // product rounded down or up may be one number wider than the exact rounding.
    const T P = sizeof(T) == 8 ? T(0x1p-969) : T(0x1p-102);
    u::Rng g{bits == 64 ? 31 : 32};
    const std::size_t count = static_cast<std::size_t>(n);
    std::vector<T> a(count), b(count), k(count), rn(count), f(count);
    for (int op = 0; op < 6; ++op) {
        // Half the pairs over every finite value; half near each other (b = +-a 2^j (1 + small)), so
        // that the sums and products are inexact in their last places.
        for (int i = 0; i < n; ++i) {
            a[std::size_t(i)] = random_finite<T>(g);
            if (i & 1) {
                const double s = g.sign();
                const double m = 1.0 + g.sym() * 0x1p-20;
                const int j = g.range(-60, 60);
                const T v = T(double(a[std::size_t(i)]) * s * std::ldexp(m, j));
                b[std::size_t(i)] = std::isfinite(v) ? v : random_finite<T>(g);
            } else {
                b[std::size_t(i)] = random_finite<T>(g);
            }
        }
        m2::m2_wide_kairn(bits, op, n, a.data(), b.data(), k.data(), rn.data());
        for (int variant = 0; variant < 2; ++variant) {
            m2::m2_wide_fenv(bits, op, variant, n, a.data(), b.data(), f.data());
            Wide w{bits, op, variant};
            for (int i = 0; i < n; ++i) {
                const std::size_t j = std::size_t(i);
                ++w.compared;
                w.differ_from_nearest += !(k[j] == rn[j]);
                if (std::memcmp(&k[j], &f[j], sizeof(T)) == 0) {
                    ++w.equal;
                } else if (k[j] == 0 && f[j] == 0) {
                    ++w.zero_sign;   // the sign of a zero result, which Kairn does not claim
                } else if (op >= 4 && std::fabs(rn[j]) < P) {
                    // below P: Kairn's bound may be the number beyond the exact rounding, on its side
                    const T step = op == 4 ? std::nextafter(f[j], -std::numeric_limits<T>::infinity())
                                           : std::nextafter(f[j], std::numeric_limits<T>::infinity());
                    if (k[j] == step) {
                        ++w.below_p_wider;
                    } else {
                        ++w.failed;
                    }
                } else {
                    ++w.failed;
                    if (w.failed <= 3) {
                        char buf[200];
                        std::snprintf(buf, sizeof buf, "wide check FAILED: bits %d op %d variant %d: %a, %a: kairn %a, prop %a\n",
                                      bits, op, variant, double(a[j]), double(b[j]), double(k[j]), double(f[j]));
                        log += buf;
                    }
                }
            }
            out.push_back(w);
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    std::string json, machine, commit = "unknown", date = u::today(), filter;
    int cpu = -1, reps = 21, wide_n = 1 << 16;
    double sample_ms = 4.0;
    bool check_only = false, list = false;
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        auto value = [&]() -> std::string {
            if (i + 1 >= argc) {
                std::fprintf(stderr, "%s needs a value\n", a.c_str());
                std::exit(2);
            }
            return argv[++i];
        };
        if (a == "--json") json = value();
        else if (a == "--machine") machine = value();
        else if (a == "--commit") commit = value();
        else if (a == "--date") date = value();
        else if (a == "--cpu") cpu = std::atoi(value().c_str());
        else if (a == "--reps") reps = std::atoi(value().c_str());
        else if (a == "--sample-ms") sample_ms = std::atof(value().c_str());
        else if (a == "--filter") filter = value();
        else if (a == "--wide") wide_n = std::atoi(value().c_str());
        else if (a == "--check-only") check_only = true;
        else if (a == "--list") list = true;
        else {
            std::fprintf(stderr, "unknown argument %s (see bench/README.md)\n", a.c_str());
            return 2;
        }
    }
    if (reps < 1) reps = 1;
    std::vector<std::string> filters;
    for (std::size_t start = 0; !filter.empty() && start <= filter.size();) {
        const std::size_t comma = filter.find(',', start);
        filters.push_back(filter.substr(start, comma == std::string::npos ? std::string::npos : comma - start));
        if (comma == std::string::npos) break;
        start = comma + 1;
    }

    const std::vector<const m2::Entry*> entries = all_entries();
    if (list) {
        for (const m2::Entry* e : entries) std::printf("%s\n", e->name);
        return 0;
    }
    const std::string pinning = u::pin(cpu);
    std::fprintf(stderr, "kairn-bench-m2: %s, %s, packed backend %s, %s, setting %s\n", u::cpu_brand().c_str(),
                 u::compiler().c_str(), m2::m2_packed_backend, pinning.c_str(), KAIRN_BENCH_SETTING);
    m2::m2_setup(1);

    // 2. The checks.
    int compared = 0, failed = 0;
    std::string discrimination;
    for (const m2::Entry* e : entries) {
        std::string why;
        bool ok = true;
        const Name nm = split(e->name);
        if (e->check) {
            char buf[256] = {0};
            ok = e->check(*e, buf, sizeof buf);
            why = buf;
        } else {
            const std::string backend = nm.backend == "m2p" ? "m2s" : nm.backend;
            const std::string ref_name = backend + "/" + nm.kind + "/" + nm.kernel + "/kairn";
            const m2::Entry* ref = find(entries, ref_name);
            if (!ref) {
                ok = false;
                why = "no reference " + ref_name;
            } else if (ref == e) {
                continue;
            } else {
                ok = check_against(*e, *ref, why);
            }
        }
        ++compared;
        if (!ok) {
            ++failed;
            std::fprintf(stderr, "check FAILED: %s: %s\n", e->name, why.c_str());
            continue;
        }
        // A prop of directed rounding: how many of its values differ from those rounded to nearest.
        const std::string rn_kernel = nearest_of(nm.kernel);
        if (!rn_kernel.empty() && (nm.variant == "fenv" || nm.variant == "fenv_loop" || nm.variant == "csr")) {
            const m2::Entry* rn = find(entries, nm.backend + "/" + nm.kind + "/" + rn_kernel + "/kairn");
            if (rn && rn->values == e->values) {
                const std::vector<unsigned char> a = run_and_read(*e), b = run_and_read(*rn);
                const std::size_t w = value_size(*e);
                long differ = 0;
                for (std::size_t i = 0; i < a.size(); i += w) differ += std::memcmp(a.data() + i, b.data() + i, w) != 0;
                discrimination += std::string(discrimination.empty() ? "" : ", ") + "{\"name\": \"" + e->name +
                                  "\", \"values\": " + std::to_string(e->values) + ", \"differ_from_nearest\": " +
                                  std::to_string(differ) + "}";
            }
        }
    }
    std::fprintf(stderr, "checked %d functions against their references: %d failed\n", compared, failed);

    std::vector<Wide> wide;
    std::string wide_log;
    wide_check<double>(wide_n, wide, wide_log);
    wide_check<float>(wide_n, wide, wide_log);
    long wide_failed = 0, wide_compared = 0;
    for (const Wide& w : wide) {
        wide_failed += w.failed;
        wide_compared += w.compared;
    }
    std::fputs(wide_log.c_str(), stderr);
    std::fprintf(stderr, "wide check of the rounding-mode props: %ld results compared, %ld failed\n", wide_compared,
                 wide_failed);
    if (failed || wide_failed) {
        std::fprintf(stderr, "refusing to time: a check failed\n");
        return 1;
    }

    // 3. Tightness.
    const std::string tightness = m2::m2_tightness_json();
    if (check_only) {
        std::fprintf(stderr, "%s\n", tightness.c_str());
        return 0;
    }

    // 4. Timing.
    struct Bench {
        const m2::Entry* e;
        long calls = 1;
        std::vector<double> ns;
    };
    std::vector<Bench> benches;
    for (const m2::Entry* e : entries) {
        bool keep = filters.empty();
        for (const std::string& f : filters) keep = keep || std::string(e->name).find(f) != std::string::npos;
        if (keep) benches.push_back({e, 1, {}});
    }
    if (benches.empty()) {
        std::fprintf(stderr, "nothing to time\n");
        return 2;
    }
    double load_start[3], load_end[3];
    u::load_average(load_start);
    const double sample_ns = sample_ms * 1e6;
    auto call_of = [](const m2::Entry* e) {
        m2::Fn volatile f = e->fn;
        void* const data = m2::m2_data(e->bits);
        return [f, data]() { f(data); };
    };
    {   // Bring the core to its working frequency.
        const auto t0 = u::Clock::now();
        auto c = call_of(benches.front().e);
        while (u::Clock::now() - t0 < std::chrono::milliseconds(300)) u::time_calls(c, 64);
    }
    for (Bench& b : benches) b.calls = u::calibrate(call_of(b.e), sample_ns);
    for (int rep = 0; rep < reps; ++rep)
        for (Bench& b : benches) b.ns.push_back(u::time_calls(call_of(b.e), b.calls) / (double(b.calls) * b.e->ops));
    u::load_average(load_end);

    using u::esc;
    using u::num;
    std::string out = "{\n  \"schema\": 1,\n  \"what\": \"kairn-bench-m2\",\n";
    out += "  \"date\": \"" + esc(date) + "\",\n";
    out += "  \"commit\": \"" + esc(commit) + "\",\n";
    out += "  \"machine\": {\"description\": \"" + esc(machine) + "\", \"cpu\": \"" + esc(u::cpu_brand()) + "\", \"os\": \"" +
           u::os_name() + "\", \"arch\": \"" + u::arch() + "\", \"pinning\": \"" + esc(pinning) + "\"},\n";
    out += "  \"load_average\": {\"start\": [" + num(load_start[0]) + ", " + num(load_start[1]) + ", " + num(load_start[2]) +
           "], \"end\": [" + num(load_end[0]) + ", " + num(load_end[1]) + ", " + num(load_end[2]) + "]},\n";
    out += "  \"compiler\": \"" + esc(u::compiler()) + "\",\n";
    out += "  \"flags\": \"" + esc(KAIRN_BENCH_FLAGS) + "\",\n";
    out += "  \"fenv_flags\": \"" + esc(KAIRN_BENCH_FENV_FLAGS) + "\",\n";
    out += "  \"setting\": \"" + esc(KAIRN_BENCH_SETTING) + "\",\n";
    out += "  \"packed_backend\": \"" + std::string(m2::m2_packed_backend) + "\",\n";
    out += "  \"elements\": " + std::to_string(m2::kN) + ", \"reps\": " + std::to_string(reps) + ", \"sample_ms\": " +
           num(sample_ms) + ",\n";
    out += "  \"checks\": {\"compared\": " + std::to_string(compared) + ", \"failed\": " + std::to_string(failed) +
           ",\n    \"discrimination\": [" + discrimination + "],\n    \"wide\": [";
    for (std::size_t i = 0; i < wide.size(); ++i) {
        const Wide& w = wide[i];
        static const char* const ops[6] = {"add_down", "add_up", "sub_down", "sub_up", "mul_down", "mul_up"};
        out += std::string(i ? ", " : "") + "{\"bits\": " + std::to_string(w.bits) + ", \"op\": \"" + ops[w.op] +
               "\", \"variant\": \"" + (w.variant ? "csr" : "fenv") + "\", \"compared\": " + std::to_string(w.compared) +
               ", \"equal\": " + std::to_string(w.equal) + ", \"zero_sign\": " + std::to_string(w.zero_sign) +
               ", \"below_p_wider\": " + std::to_string(w.below_p_wider) + ", \"failed\": " + std::to_string(w.failed) +
               ", \"differ_from_nearest\": " + std::to_string(w.differ_from_nearest) + "}";
    }
    out += "]},\n  \"tightness\": " + tightness + ",\n  \"results\": [\n";
    for (std::size_t i = 0; i < benches.size(); ++i) {
        const Bench& b = benches[i];
        const double mn = *std::min_element(b.ns.begin(), b.ns.end());
        const double md = u::quantile(b.ns, 0.5);
        const double mx = *std::max_element(b.ns.begin(), b.ns.end());
        out += "    {\"name\": \"" + std::string(b.e->name) + "\", \"lanes\": " + std::to_string(b.e->lanes) +
               ", \"ns_min\": " + num(mn) + ", \"ns_median\": " + num(md) + ", \"ns_max\": " + num(mx) + "}" +
               (i + 1 < benches.size() ? ",\n" : "\n");
        std::fprintf(stderr, "%-52s %9.3f %9.3f %9.3f ns\n", b.e->name, mn, md, mx);
    }
    out += "  ]\n}\n";
    if (!json.empty()) {
        if (!u::write_file(json, out)) {
            std::fprintf(stderr, "cannot write %s\n", json.c_str());
            return 1;
        }
    } else {
        std::fputs(out.c_str(), stdout);
    }
    return 0;
}
