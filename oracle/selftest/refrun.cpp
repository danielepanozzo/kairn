// Reference runner for binary64 (double) and binary32 (float), written directly from the
// pseudo-code of the first-wave kernels in docs/developer/architecture.md, one rounding per
// statement.  It shares nothing with the library or its generator: its purpose is to test the
// oracle on hardware arithmetic.  It must be compiled without contraction
// (-ffp-contract=off), because a fused a*b+c would change what each statement computes.
//
// Usage: refrun [--variant NAME] < requests > completed
// Variants inject the errors that the oracle's selftest expects `check` to catch.

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <string>
#include <vector>

namespace {

enum class Variant {
  correct,
  ulp_rare,
  not_normalized,
  mul_drop_cross,
  add_skip_renorm,
  subnormal_flush,
  two_sum_zero,
  corrupt_input,
  fast_end_two_sum,
};

struct VariantName {
  const char* name;
  Variant v;
};

const VariantName kVariants[] = {
    {"correct", Variant::correct},
    {"ulp-rare", Variant::ulp_rare},
    {"not-normalized", Variant::not_normalized},
    {"mul-drop-cross", Variant::mul_drop_cross},
    {"add-skip-renorm", Variant::add_skip_renorm},
    {"subnormal-flush", Variant::subnormal_flush},
    {"two-sum-zero", Variant::two_sum_zero},
    {"corrupt-input", Variant::corrupt_input},
    {"fast-end-two-sum", Variant::fast_end_two_sum},
};

Variant g_variant = Variant::correct;

std::uint32_t fnv1a(const std::string& s) {
  std::uint32_t h = 2166136261u;
  for (unsigned char c : s) {
    h ^= c;
    h *= 16777619u;
  }
  return h;
}

template <class T>
T flush(T r) {
  // Only the subnormal-flush variant changes anything: a subnormal result becomes zero.
  if (g_variant == Variant::subnormal_flush && r != T(0) &&
      std::fabs(r) < std::numeric_limits<T>::min())
    return std::copysign(T(0), r);
  return r;
}

template <class T> T add(T a, T b) { return flush<T>(a + b); }
template <class T> T sub(T a, T b) { return flush<T>(a - b); }
template <class T> T prod(T a, T b) { return flush<T>(std::fma(a, b, T(0))); }
template <class T> T fma_(T a, T b, T c) { return flush<T>(std::fma(a, b, c)); }
template <class T> T fms(T a, T b, T c) { return flush<T>(std::fma(a, b, -c)); }

template <class T>
T splitter() {
  // 2^ceil(p/2) + 1
  const int p = std::numeric_limits<T>::digits;
  return std::ldexp(T(1), (p + 1) / 2) + T(1);
}

template <class T>
void two_sum(T a, T b, T& s, T& e) {
  s = add(a, b);
  T bb = sub(s, a);
  T t0 = sub(s, bb);
  T t1 = sub(a, t0);
  T t2 = sub(b, bb);
  e = add(t1, t2);
  if (g_variant == Variant::two_sum_zero && e == T(0))
    e = std::numeric_limits<T>::denorm_min();
}

template <class T>
void fast_two_sum(T a, T b, T& s, T& e) {
  s = add(a, b);
  T z = sub(s, a);
  e = sub(b, z);
}

template <class T>
void two_prod(T a, T b, T& p, T& e) {
  p = prod(a, b);
  e = fms(a, b, p);
}

template <class T>
void split(T a, T& ah, T& al) {
  T g = prod(splitter<T>(), a);
  T d = sub(a, g);
  ah = add(g, d);
  al = sub(a, ah);
}

template <class T>
void two_prod_dekker(T a, T b, T& p, T& e) {
  T ah, al, bh, bl;
  split(a, ah, al);
  split(b, bh, bl);
  p = prod(a, b);
  T q0 = prod(ah, bh);
  T t1 = sub(q0, p);
  T q1 = prod(ah, bl);
  T t2 = add(t1, q1);
  T q2 = prod(al, bh);
  T t3 = add(t2, q2);
  T q3 = prod(al, bl);
  e = add(t3, q3);
}

template <class T>
void add_2_2(T x0, T x1, T y0, T y1, T& z0, T& z1) {
  T sh, sl, th, tl, vh, vl;
  two_sum(x0, y0, sh, sl);
  two_sum(x1, y1, th, tl);
  T c = add(sl, th);
  fast_two_sum(sh, c, vh, vl);
  T w = add(tl, vl);
  if (g_variant == Variant::add_skip_renorm) {
    z0 = vh;
    z1 = w;
    return;
  }
  fast_two_sum(vh, w, z0, z1);
}

template <class T>
void add_2_1(T x0, T x1, T a, T& z0, T& z1) {
  T sh, sl;
  two_sum(x0, a, sh, sl);
  T v = add(x1, sl);
  if (g_variant == Variant::add_skip_renorm) {
    z0 = sh;
    z1 = v;
    return;
  }
  fast_two_sum(sh, v, z0, z1);
}

template <class T>
void mul_2_2(T x0, T x1, T y0, T y1, T& z0, T& z1) {
  T ch, cl1;
  two_prod(x0, y0, ch, cl1);
  T tl0 = prod(x1, y1);
  T tl1 = g_variant == Variant::mul_drop_cross ? tl0 : fma_(x0, y1, tl0);
  T cl2 = fma_(x1, y0, tl1);
  T cl3 = add(cl1, cl2);
  fast_two_sum(ch, cl3, z0, z1);
}

template <class T>
void mul_2_1(T x0, T x1, T a, T& z0, T& z1) {
  T ch, cl1;
  two_prod(x0, a, ch, cl1);
  T cl3 = g_variant == Variant::mul_drop_cross ? cl1 : fma_(x1, a, cl1);
  fast_two_sum(ch, cl3, z0, z1);
}

template <class T>
void add_fast_2_2(T x0, T x1, T y0, T y1, T& z0, T& z1) {
  T sh, sl;
  two_sum(x0, y0, sh, sl);
  T v = add(x1, y1);
  T w = add(sl, v);
  if (g_variant == Variant::add_skip_renorm) {
    z0 = sh;
    z1 = w;
    return;
  }
  if (g_variant == Variant::fast_end_two_sum) {
    two_sum(sh, w, z0, z1);
    return;
  }
  fast_two_sum(sh, w, z0, z1);
}

std::vector<std::string> split_spaces(const std::string& s) {
  std::vector<std::string> out;
  std::size_t i = 0;
  while (i <= s.size()) {
    std::size_t j = s.find(' ', i);
    if (j == std::string::npos) j = s.size();
    out.push_back(s.substr(i, j - i));
    i = j + 1;
  }
  return out;
}

template <class T> T parse(const std::string& s);
template <> double parse<double>(const std::string& s) { return std::strtod(s.c_str(), nullptr); }
template <> float parse<float>(const std::string& s) { return std::strtof(s.c_str(), nullptr); }

template <class T>
std::string show(T v) {
  // The protocol spells the non-finite values inf, -inf and nan; %a does not everywhere (MSVC
  // prints a NaN as -nan(ind)).
  if (std::isnan(v)) return "nan";
  if (std::isinf(v)) return v < 0 ? "-inf" : "inf";
  char buf[64];
  std::snprintf(buf, sizeof buf, "%a", static_cast<double>(v));
  return buf;
}

template <class T>
bool is_finite_nonzero(T v) {
  return std::isfinite(v) && v != T(0);
}

// Alters the inputs so that a requirement fails: x1 = x0 for a 2-limb operand, swapped
// operands for fast_two_sum, an operand with one bit more than the format otherwise.
template <class T>
void corrupt(const std::string& kernel, std::vector<std::string>& args) {
  if (kernel == "add_2_2" || kernel == "add_2_1" || kernel == "mul_2_2" || kernel == "mul_2_1" ||
      kernel == "add_fast_2_2") {
    if (parse<T>(args[0]) == T(0)) args[0] = "0x1p+0";
    args[1] = args[0];
    return;
  }
  if (kernel == "fast_two_sum") {
    T a = parse<T>(args[0]), b = parse<T>(args[1]);
    if (std::fabs(a) != std::fabs(b)) {
      if (std::fabs(a) > std::fabs(b)) std::swap(args[0], args[1]);
      return;
    }
  }
  args[0] = std::numeric_limits<T>::digits == 53 ? "0x1.00000000000008p+0" : "0x1.000001p+0";
}

template <class T>
bool run_kernel(const std::string& k, const std::vector<T>& v, std::vector<T>& out) {
  T z0, z1;
  if (k == "two_sum" && v.size() == 2) two_sum(v[0], v[1], z0, z1);
  else if (k == "fast_two_sum" && v.size() == 2) fast_two_sum(v[0], v[1], z0, z1);
  else if (k == "two_prod" && v.size() == 2) two_prod(v[0], v[1], z0, z1);
  else if (k == "two_prod_dekker" && v.size() == 2) two_prod_dekker(v[0], v[1], z0, z1);
  else if (k == "split" && v.size() == 1) split(v[0], z0, z1);
  else if (k == "add_2_2" && v.size() == 4) add_2_2(v[0], v[1], v[2], v[3], z0, z1);
  else if (k == "add_2_1" && v.size() == 3) add_2_1(v[0], v[1], v[2], z0, z1);
  else if (k == "mul_2_2" && v.size() == 4) mul_2_2(v[0], v[1], v[2], v[3], z0, z1);
  else if (k == "mul_2_1" && v.size() == 3) mul_2_1(v[0], v[1], v[2], z0, z1);
  else if (k == "add_fast_2_2" && v.size() == 4) add_fast_2_2(v[0], v[1], v[2], v[3], z0, z1);
  else return false;
  out = {z0, z1};
  return true;
}

template <class T>
bool complete(std::string line, std::string& result) {
  std::vector<std::string> toks = split_spaces(line);
  std::string tag;
  if (toks.size() > 2 && !toks.back().empty() && toks.back()[0] == '#') {
    tag = toks.back();
    toks.pop_back();
  }
  const std::string kernel = toks[0];
  std::vector<std::string> args(toks.begin() + 2, toks.end());
  std::string prefix;
  if (g_variant == Variant::corrupt_input && fnv1a(line) % 64 == 0 && !args.empty()) {
    corrupt<T>(kernel, args);
    line = toks[0] + " " + toks[1];
    for (const auto& a : args) line += " " + a;
    if (!tag.empty()) line += " " + tag;
    prefix = "# refrun: corrupted input\n";
  }
  std::vector<T> vals;
  for (const auto& a : args) vals.push_back(parse<T>(a));
  std::vector<T> out;
  if (!run_kernel<T>(kernel, vals, out)) return false;
  if (g_variant == Variant::ulp_rare && fnv1a(line) % 256 == 0)
    out[1] = std::nextafter(out[1], std::numeric_limits<T>::infinity());
  if (g_variant == Variant::not_normalized && is_finite_nonzero(out[0]) && std::isfinite(out[1])) {
    // Move one ulp of z0 into z1 when that is exact: same value, broken invariant.
    T n = std::nextafter(out[0], std::numeric_limits<T>::infinity());
    T d = n - out[0];
    T z1 = out[1] - d;
    T s, e;
    two_sum(out[1], -d, s, e);
    if (std::isfinite(n) && e == T(0) && s == z1) out = {n, z1};
  }
  result = prefix + line + " ->";
  for (T v : out) result += " " + show(v);
  return true;
}

}  // namespace

int main(int argc, char** argv) {
  for (int i = 1; i < argc; ++i) {
    if (std::strcmp(argv[i], "--variant") == 0 && i + 1 < argc) {
      const char* name = argv[++i];
      bool found = false;
      for (const auto& v : kVariants)
        if (std::strcmp(v.name, name) == 0) {
          g_variant = v.v;
          found = true;
        }
      if (!found) {
        std::fprintf(stderr, "refrun: unknown variant %s\n", name);
        return 2;
      }
    } else {
      std::fprintf(stderr, "usage: refrun [--variant NAME]\n");
      return 2;
    }
  }
  std::string line;
  char buf[1 << 16];
  while (std::fgets(buf, sizeof buf, stdin)) {
    line = buf;
    while (!line.empty() && (line.back() == '\n' || line.back() == '\r')) line.pop_back();
    if (line.empty() || line[0] == '#') {
      std::printf("%s\n", line.c_str());
      continue;
    }
    std::vector<std::string> toks = split_spaces(line);
    std::string result;
    bool ok = false;
    if (toks.size() >= 2 && toks[1] == "binary64") ok = complete<double>(line, result);
    else if (toks.size() >= 2 && toks[1] == "binary32") ok = complete<float>(line, result);
    if (!ok) {
      std::fprintf(stderr, "refrun: cannot run: %s\n", line.c_str());
      return 1;
    }
    std::printf("%s\n", result.c_str());
  }
  return 0;
}
