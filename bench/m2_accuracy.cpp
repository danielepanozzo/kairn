// kairn-bench-m2-accuracy-LEVEL (bench/README.md, "Milestone 2", third part): the error that the sums
// and dot products of kairn/batch.hpp and the accumulator make, against the condition number and
// against the bound the library states, next to the naive loop and the compensated one, on data of
// double whose condition is chosen; the exact results by m2_exact.hpp.
//
//   kairn-bench-m2-accuracy-O2 [--json FILE] [--machine TEXT] [--commit TEXT] [--date TEXT]
//
// The data. A dot product of n terms of chosen condition is made as Ogita, Rump and Oishi make it
// ("Accurate sum and dot product", SIAM J. Sci. Comput. 26(6), 2005, Algorithm 6.1, GenDot): the
// first half of the terms with random signs and exponents spread over [0, b/2], b = log2 of the
// condition; the second half with exponents falling linearly from b/2 to 0, each y_i chosen so that
// the dot product of the terms so far nearly cancels (from the exact dot product of the terms before
// it, rounded to double); then shuffled. A sum of n numbers is the 2 (n/2) parts p_i and e_i of the
// products of such a dot product (x_i y_i = p_i + e_i exactly, by an FMA), shuffled: the same
// condition. Besides, two regimes without cancellation by construction: the numbers uniform in
// [-1, 1] ("random") and in [1, 2) ("positive", condition 1).
//
// The methods. naive: the loop of double, s = s + x_i (dot: s = s + x_i * y_i, a product and a sum,
// contraction off). sum1, dot1: kairn::sum and kairn::dot of one limb, in the default (lane) order
// and with kairn::sequential (seq). sum2, dot2: the same of two limbs on the same data, the second
// limbs zero. textbook: Sum2 and Dot2 of Ogita, Rump and Oishi. acc1, acc2: an Accumulator of one or
// two limbs fed the numbers (add) or the pairs (add_product) in order, with its error_bound().
// The bounds: traits<Expansion<double, k>>::sum(n).unit times the sum of the magnitudes (dot: dot(n),
// unit times the sum of |x_i y_i| plus tiny), and the accumulators' error_bound(), each against the
// error actually made.
#include <kairn/accumulator.hpp>
#include <kairn/batch.hpp>
#include <kairn/kairn.hpp>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

#include "bench_util.hpp"
#include "m2_exact.hpp"
#include "props.hpp"

namespace {

namespace u = kairn_bench::util;
namespace tb = kairn_bench::textbook;
using kairn_bench::exact::Exact;
using V1 = kairn::SoAView<const double, 1>;
using V2 = kairn::SoAView<const double, 2>;

struct Data {
    std::vector<double> x, y;   // y empty for a sum
};

void shuffle(std::vector<double>& x, std::vector<double>* y, u::Rng& g) {
    for (std::size_t i = x.size(); i > 1; --i) {
        const std::size_t j = std::size_t(g.next() % i);
        std::swap(x[i - 1], x[j]);
        if (y) std::swap((*y)[i - 1], (*y)[j]);
    }
}

// GenDot of Ogita, Rump and Oishi (2005), the accurate dot product of the terms so far the exact one
// rounded to double.
Data gen_dot(std::size_t n, double cond, u::Rng& g) {
    const double b = std::log2(cond);
    const std::size_t n2 = (n + 1) / 2;
    Data d;
    d.x.resize(n);
    d.y.resize(n);
    for (std::size_t i = 0; i < n2; ++i) {
        int e = int(std::lround(g.u01() * b / 2));
        if (i == 0) e = int(std::lround(b / 2)) + 1;
        if (i == n2 - 1) e = 0;
        d.x[i] = g.sym() * std::ldexp(1.0, e);
        d.y[i] = g.sym() * std::ldexp(1.0, e);
    }
    Exact acc;
    for (std::size_t i = 0; i < n2; ++i) acc.add_product(d.x[i], d.y[i]);
    for (std::size_t i = n2; i < n; ++i) {
        const double t = n - n2 > 1 ? double(i - n2) / double(n - n2 - 1) : 0.0;
        const int e = int(std::lround(b / 2 * (1 - t)));
        double xi = 0;
        while (xi == 0) xi = g.sym() * std::ldexp(1.0, e);
        d.x[i] = xi;
        d.y[i] = (g.sym() * std::ldexp(1.0, e) - acc.value()) / xi;
        acc.add_product(d.x[i], d.y[i]);
    }
    shuffle(d.x, &d.y, g);
    return d;
}

Data gen_sum(std::size_t n, double cond, u::Rng& g) {
    const Data p = gen_dot(n / 2, cond, g);
    Data d;
    for (std::size_t i = 0; i < p.x.size(); ++i) {
        const double h = p.x[i] * p.y[i];
        d.x.push_back(h);
        d.x.push_back(std::fma(p.x[i], p.y[i], -h));
    }
    shuffle(d.x, nullptr, g);
    return d;
}

Data gen_plain(std::size_t n, bool dot, bool positive, u::Rng& g) {
    Data d;
    for (std::size_t i = 0; i < n; ++i) {
        d.x.push_back(positive ? 1 + g.u01() : g.sym());
        if (dot) d.y.push_back(positive ? 1 + g.u01() : g.sym());
    }
    return d;
}

struct Result {
    std::string method;
    double err = 0;     // |computed - exact|
    double bound = -1;  // the stated bound, or -1
};

double err_of(Exact x, double v0, double v1) {
    x.add(-v0);
    x.add(-v1);
    return std::fabs(x.value());
}

std::vector<Result> run(const Data& d, bool dot, Exact& exact, double& mags) {
    const std::size_t n = d.x.size();
    const double* x = d.x.data();
    const double* y = dot ? d.y.data() : nullptr;
    const std::vector<double> zero(n, 0.0);
    Exact m;
    exact.clear();
    for (std::size_t i = 0; i < n; ++i) {
        if (dot) {
            exact.add_product(x[i], y[i]);
            m.add(std::fabs(x[i] * y[i]));
        } else {
            exact.add(x[i]);
            m.add(std::fabs(x[i]));
        }
    }
    mags = m.value() * (1 + 0x1p-50);   // the sum of magnitudes, rounded up enough (|x y| rounded once)
    std::vector<Result> out;
    using X1 = kairn::traits<kairn::Expansion<double, 1>>;
    using X2 = kairn::traits<kairn::Expansion<double, 2>>;
    // naive
    {
        double s = 0;
        if (dot) {
            for (std::size_t i = 0; i < n; ++i) s = s + x[i] * y[i];
        } else {
            for (std::size_t i = 0; i < n; ++i) s = s + x[i];
        }
        out.push_back({"naive", err_of(exact, s, 0)});
    }
    // textbook: Sum2, Dot2
    {
        double p = 0, s = 0;
        if (dot) {
            tb::fast_two_mult(x[0], y[0], p, s);
            for (std::size_t i = 1; i < n; ++i) {
                double h, e, q;
                tb::fast_two_mult(x[i], y[i], h, e);
                tb::two_sum(p, h, p, q);
                s = s + (q + e);
            }
        } else {
            p = x[0];
            for (std::size_t i = 1; i < n; ++i) {
                double q;
                tb::two_sum(p, x[i], p, q);
                s = s + q;
            }
        }
        out.push_back({"textbook", err_of(exact, p + s, 0)});
    }
    const double b1 = dot ? double(X1::dot(n).unit) * mags + double(X1::dot(n).tiny) : double(X1::sum(n).unit) * mags;
    const double b2 = dot ? double(X2::dot(n).unit) * mags + double(X2::dot(n).tiny) : double(X2::sum(n).unit) * mags;
    for (int seq = 0; seq < 2; ++seq) {
        kairn::Reduction<kairn::Expansion<double, 1>> r1;
        kairn::Reduction<kairn::Expansion<double, 2>> r2;
        if (dot) {
            r1 = seq ? kairn::dot(kairn::sequential, V1(x, n), V1(y, n)) : kairn::dot(V1(x, n), V1(y, n));
            r2 = seq ? kairn::dot(kairn::sequential, V2(x, zero.data(), n), V2(y, zero.data(), n))
                     : kairn::dot(V2(x, zero.data(), n), V2(y, zero.data(), n));
        } else {
            r1 = seq ? kairn::sum(kairn::sequential, V1(x, n)) : kairn::sum(V1(x, n));
            r2 = seq ? kairn::sum(kairn::sequential, V2(x, zero.data(), n)) : kairn::sum(V2(x, zero.data(), n));
        }
        out.push_back({seq ? "k1seq" : "k1", err_of(exact, r1.value.limb[0], 0), b1});
        out.push_back({seq ? "k2seq" : "k2", err_of(exact, r2.value.limb[0], r2.value.limb[1]), b2});
    }
    {
        kairn::Accumulator<double, 1> a1;
        kairn::Accumulator<double, 2> a2;
        for (std::size_t i = 0; i < n; ++i) {
            if (dot) {
                a1.add_product(x[i], y[i]);
                a2.add_product(x[i], y[i]);
            } else {
                a1.add(x[i]);
                a2.add(x[i]);
            }
        }
        out.push_back({"acc1", err_of(exact, a1.sum().value.limb[0], 0), double(a1.error_bound())});
        out.push_back({"acc2", err_of(exact, a2.sum().value.limb[0], a2.sum().value.limb[1]), double(a2.error_bound())});
    }
    return out;
}

std::string num(double a) {
    char buf[40];
    std::snprintf(buf, sizeof buf, "%.4g", a);
    return buf;
}

}  // namespace

int main(int argc, char** argv) {
    std::string json, machine, commit = "unknown", date = u::today();
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (i + 1 >= argc) {
            std::fprintf(stderr, "%s needs a value\n", a.c_str());
            return 2;
        }
        if (a == "--json") json = argv[++i];
        else if (a == "--machine") machine = argv[++i];
        else if (a == "--commit") commit = argv[++i];
        else if (a == "--date") date = argv[++i];
        else {
            std::fprintf(stderr, "unknown argument %s\n", a.c_str());
            return 2;
        }
    }
    const std::size_t lengths[] = {10, 100, 1000, 10000, 100000, 1000000};
    // Regimes: random, positive, then GenDot of condition 10^4 to 10^40.
    std::vector<std::pair<std::string, double>> regimes = {{"random", 0}, {"positive", 0}};
    for (int k = 4; k <= 40; k += 4) regimes.push_back({"cond", std::pow(10.0, k)});
    u::Rng g{20261122};
    std::string out = "{\n  \"schema\": 1,\n  \"what\": \"kairn-bench-m2-accuracy\",\n  \"date\": \"" + u::esc(date) +
                      "\",\n  \"commit\": \"" + u::esc(commit) + "\",\n  \"machine\": {\"description\": \"" +
                      u::esc(machine) + "\", \"cpu\": \"" + u::esc(u::cpu_brand()) + "\", \"arch\": \"" + u::arch() +
                      "\"},\n  \"compiler\": \"" + u::esc(u::compiler()) + "\",\n  \"flags\": \"" +
#ifdef KAIRN_BENCH_FLAGS
                      u::esc(KAIRN_BENCH_FLAGS) +
#endif
                      "\",\n  \"lanes\": " + std::to_string(kairn::Packed<double, 1>::lanes) + ",\n  \"records\": [\n";
    bool first = true;
    long failures = 0;
    for (const bool dot : {false, true})
        for (const std::size_t n : lengths)
            for (const auto& [regime, cond] : regimes) {
                const int trials = n <= 1000 ? 20 : n <= 10000 ? 10 : 4;
                std::string rec = std::string("    {\"kind\": \"") + (dot ? "dot" : "sum") + "\", \"n\": " +
                                  std::to_string(n) + ", \"regime\": \"" + regime + "\", \"target\": " + num(cond) +
                                  ", \"trials\": [";
                for (int t = 0; t < trials; ++t) {
                    const Data d = regime == "cond" ? (dot ? gen_dot(n, cond, g) : gen_sum(n, cond, g))
                                                    : gen_plain(n, dot, regime == "positive", g);
                    Exact exact;
                    double mags = 0;
                    const std::vector<Result> rs = run(d, dot, exact, mags);
                    const double s = exact.value();
                    rec += std::string(t ? ", " : "") + "{\"n\": " + std::to_string(d.x.size()) + ", \"exact\": " +
                           num(s) + ", \"magnitudes\": " + num(mags) + ", \"cond\": " + num(mags / std::fabs(s)) +
                           ", \"err\": {";
                    for (std::size_t k = 0; k < rs.size(); ++k) {
                        rec += std::string(k ? ", " : "") + "\"" + rs[k].method + "\": " + num(rs[k].err);
                        if (rs[k].bound >= 0 && !(rs[k].err <= rs[k].bound)) {
                            ++failures;
                            std::fprintf(stderr, "BOUND FAILED: %s n %zu %s: err %g bound %g\n", rs[k].method.c_str(),
                                         n, regime.c_str(), rs[k].err, rs[k].bound);
                        }
                    }
                    rec += "}, \"bound\": {";
                    bool fb = true;
                    for (const Result& r : rs)
                        if (r.bound >= 0) {
                            rec += std::string(fb ? "" : ", ") + "\"" + r.method + "\": " + num(r.bound);
                            fb = false;
                        }
                    rec += "}}";
                }
                out += std::string(first ? "" : ",\n") + rec + "]}";
                first = false;
                std::fprintf(stderr, "%s n %zu %s %g\n", dot ? "dot" : "sum", n, regime.c_str(), cond);
            }
    out += "\n  ],\n  \"bound_failures\": " + std::to_string(failures) + "\n}\n";
    if (failures) {
        std::fprintf(stderr, "a stated bound was below the error made: %ld\n", failures);
        return 1;
    }
    if (!json.empty()) {
        if (!u::write_file(json, out)) return 1;
    } else {
        std::fputs(out.c_str(), stdout);
    }
    return 0;
}
