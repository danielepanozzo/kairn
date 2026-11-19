// Reference runner for binary64 (double) and binary32 (float), written directly from the
// pseudo-code of the first-wave kernels in docs/developer/architecture.md and of the
// second-wave and Ball kernels in docs/developer/design/milestone1.md, one rounding per
// statement.  It shares nothing with the library or its generator: its purpose is to test the
// oracle on hardware arithmetic.  It must be compiled without contraction
// (-ffp-contract=off), because a fused a*b+c would change what each statement computes.
//
// Usage: refrun [--variant NAME] [--radius first|second] [--const FORMAT.KERNEL.U=HEX ...]
//          < requests > completed
// Variants inject the errors that the oracle's selftest expects `check` to catch.  The Ball
// kernels need the constants U and V of their center's kernel (add, prod, add_2_2, mul_2_2,
// mul_2_1), rounded up to the format; they are computed exactly by the Python side
// (`kairn-oracle refrun --print-constants FORMAT`) and given here, because computing a
// rounded-up rational exactly is not something to do in the arithmetic under test.

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <map>
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
  cmp_lead_equal,
  down_no_neg_step,
  down_pow2_wrong_side,
  radd_no_step,
  rmul_nearest,
  ball_no_center_error,
  ball_no_rr,
  ball_pow2_ulp,
  abs_lead_only,
  // The non-finite layer.
  full_no_fixup,
  full_overflow_sign,
  full_overflow_nan,
  full_overflow_finite,
  full_spurious_overflow,
  full_inf_tail_nan,
  full_inf_tail_eta,
  full_nan_one_limb,
  full_nan_to_zero,
  ball_full_swap,
  ball_full_zero_inf_empty,
  ball_full_finite_whole,
  make_negative_radius,
  make_nan_radius,
  make2_inf_nan_tail,
  ball2_no_E,
  ball2_no_H,
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
    {"cmp-lead-equal", Variant::cmp_lead_equal},
    {"down-no-neg-step", Variant::down_no_neg_step},
    {"down-pow2-wrong-side", Variant::down_pow2_wrong_side},
    {"radd-no-step", Variant::radd_no_step},
    {"rmul-nearest", Variant::rmul_nearest},
    {"ball-no-center-error", Variant::ball_no_center_error},
    {"ball-no-rr", Variant::ball_no_rr},
    {"ball-pow2-ulp", Variant::ball_pow2_ulp},
    {"abs-lead-only", Variant::abs_lead_only},
    {"full-no-fixup", Variant::full_no_fixup},
    {"full-overflow-sign", Variant::full_overflow_sign},
    {"full-overflow-nan", Variant::full_overflow_nan},
    {"full-overflow-finite", Variant::full_overflow_finite},
    {"full-spurious-overflow", Variant::full_spurious_overflow},
    {"full-inf-tail-nan", Variant::full_inf_tail_nan},
    {"full-inf-tail-eta", Variant::full_inf_tail_eta},
    {"full-nan-one-limb", Variant::full_nan_one_limb},
    {"full-nan-to-zero", Variant::full_nan_to_zero},
    {"ball-full-swap", Variant::ball_full_swap},
    {"ball-full-zero-inf-empty", Variant::ball_full_zero_inf_empty},
    {"ball-full-finite-whole", Variant::ball_full_finite_whole},
    {"make-negative-radius", Variant::make_negative_radius},
    {"make-nan-radius", Variant::make_nan_radius},
    {"make2-inf-nan-tail", Variant::make2_inf_nan_tail},
    {"ball2-no-E", Variant::ball2_no_E},
    {"ball2-no-H", Variant::ball2_no_H},
};

Variant g_variant = Variant::correct;

// The constants of the Ball kernels, "FORMAT.KERNEL.U" -> value, from the command line.
std::map<std::string, double> g_consts;

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

// guard(a) = RN(a + 0): the value of a; a zero comes out positive (milestone1.md, "Values that
// enter from the program").
template <class T> T guard(T a) { return add(a, T(0)); }

template <class T>
void add_2_1(T x0, T x1, T a, T& z0, T& z1) {
  T sh, sl;
  T g = guard(a);
  two_sum(x0, g, sh, sl);
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

// ---------------------------------------------------------------------------------------------
// Second wave (milestone1.md).  succ and pred are the neighbours in the format, which is what
// nextafter toward the infinities returns.

template <class T> T succ(T a) { return std::nextafter(a, std::numeric_limits<T>::infinity()); }
template <class T> T pred(T a) { return std::nextafter(a, -std::numeric_limits<T>::infinity()); }

template <class T>
bool is_pow2(T a) {
  int e;
  return std::isfinite(a) && a != T(0) && std::frexp(std::fabs(a), &e) == T(0.5);
}

template <class T>
void abs_2(T x0, T x1, T& z0, T& z1) {
  bool m = x0 < T(0);
  T n0 = -x0;
  T n1 = g_variant == Variant::abs_lead_only ? x1 : -x1;
  z0 = m ? n0 : x0;
  z1 = m ? n1 : x1;
}

template <class T>
bool lt_2_2(T x0, T x1, T y0, T y1, bool strict) {
  bool h = x0 < y0;
  bool e = x0 == y0;
  // The injected error: when the first limbs are equal, lt and le swap tests.
  if (g_variant == Variant::cmp_lead_equal && e) strict = !strict;
  bool l = strict ? x1 < y1 : x1 <= y1;
  bool t = e && l;
  return h || t;
}

template <class T>
bool eq_2_2(T x0, T x1, T y0, T y1) {
  bool h = x0 == y0;
  bool l = x1 == y1;
  if (g_variant == Variant::cmp_lead_equal && h) l = true;
  return h && l;
}

template <class T>
T to_down_2(T x0, T x1) {
  bool m = x1 < T(0);
  T p = pred(x0);
  if (g_variant == Variant::down_no_neg_step) m = false;
  if (g_variant == Variant::down_pow2_wrong_side && is_pow2(x0)) {
    T s = succ(x0);
    if (std::isfinite(s)) p = x0 - (s - x0);
  }
  return m ? p : x0;
}

template <class T>
T to_up_2(T x0, T x1) {
  bool m = T(0) < x1;
  T s = succ(x0);
  return m ? s : x0;
}

template <class T>
T abs_upper_2(T x0, T x1) {
  T a0, a1;
  abs_2(x0, x1, a0, a1);
  return to_up_2(a0, a1);
}

template <class T>
T radd(T a, T b) {
  T s = add(a, b);
  return g_variant == Variant::radd_no_step ? s : succ(s);
}

template <class T>
T rmul(T a, T b) {
  T p = prod(a, b);
  return g_variant == Variant::rmul_nearest ? p : succ(p);
}

template <class T>
void mul_pow2_2(T x0, T x1, T c, T& z0, T& z1) {
  T h = prod(x0, c);
  T l = prod(x1, c);
  fast_two_sum(h, l, z0, z1);
}

template <class T> const char* format_name();
template <> const char* format_name<double>() { return "binary64"; }
template <> const char* format_name<float>() { return "binary32"; }

template <class T>
T constant(const char* center, const char* which) {
  std::string key = std::string(format_name<T>()) + "." + center + "." + which;
  auto it = g_consts.find(key);
  if (it == g_consts.end()) {
    std::fprintf(stderr, "refrun: constant %s not given (--const %s=HEX)\n", key.c_str(),
                 key.c_str());
    std::exit(2);
  }
  return static_cast<T>(it->second);
}

// A Ball: center limbs (k = 1 or 2) and a radius.
template <class T>
struct Ball {
  T c0, c1, r;
};

template <class T>
T ball_mag_upper(int k, T c0, T c1) {
  return k == 1 ? std::fabs(c0) : abs_upper_2(c0, c1);
}

template <class T>
T ball_radius(T c0, T rz) {
  if (g_variant == Variant::ball_pow2_ulp && is_pow2(c0) && std::isfinite(rz)) return pred(rz);
  return rz;
}

template <class T>
Ball<T> ball_add(int k, Ball<T> x, Ball<T> y) {
  const char* center = k == 1 ? "add" : "add_2_2";
  T U = constant<T>(center, "U");
  Ball<T> z;
  z.c1 = T(0);
  if (k == 1) z.c0 = add(x.c0, y.c0);
  else add_2_2(x.c0, x.c1, y.c0, y.c1, z.c0, z.c1);
  T mz = ball_mag_upper(k, z.c0, z.c1);
  T d = rmul(U, mz);
  T r0 = radd(x.r, y.r);
  T rz = g_variant == Variant::ball_no_center_error ? r0 : radd(r0, d);
  z.r = ball_radius(z.c0, rz);
  return z;
}

template <class T>
Ball<T> ball_mul(int k, Ball<T> x, Ball<T> y) {
  const char* center = k == 1 ? "prod" : "mul_2_2";
  T U = constant<T>(center, "U");
  T V = constant<T>(center, "V");
  Ball<T> z;
  z.c1 = T(0);
  if (k == 1) z.c0 = prod(x.c0, y.c0);
  else mul_2_2(x.c0, x.c1, y.c0, y.c1, z.c0, z.c1);
  T ax = ball_mag_upper(k, x.c0, x.c1);
  T ay = ball_mag_upper(k, y.c0, y.c1);
  T t1 = rmul(ax, y.r);
  T t2 = rmul(ay, x.r);
  T t3 = rmul(x.r, y.r);
  T s1 = radd(t1, t2);
  T s2 = g_variant == Variant::ball_no_rr ? s1 : radd(s1, t3);
  T mz = ball_mag_upper(k, z.c0, z.c1);
  T d0 = rmul(U, mz);
  T d = radd(d0, V);
  T rz = g_variant == Variant::ball_no_center_error ? s2 : radd(s2, d);
  z.r = ball_radius(z.c0, rz);
  return z;
}

template <class T>
Ball<T> ball_scale(int k, Ball<T> x, T a) {
  const char* center = k == 1 ? "prod" : "mul_2_1";
  T U = constant<T>(center, "U");
  T V = constant<T>(center, "V");
  Ball<T> z;
  z.c1 = T(0);
  if (k == 1) z.c0 = prod(x.c0, a);
  else mul_2_1(x.c0, x.c1, a, z.c0, z.c1);
  T aa = std::fabs(a);
  T t1 = rmul(aa, x.r);
  T mz = ball_mag_upper(k, z.c0, z.c1);
  T d0 = rmul(U, mz);
  T d = radd(d0, V);
  T rz = g_variant == Variant::ball_no_center_error ? t1 : radd(t1, d);
  z.r = ball_radius(z.c0, rz);
  return z;
}

// The second radius design (milestone1.md, "The radius, second design"): ordinary operations on
// nonnegative values, then one inflation by the kernel's constants E, G and H, which are given
// on the command line (--const binary64.ball_add_1.E=HEX ...) as the Python side computes them.
bool g_radius2 = false;

template <class T>
void radius_constants(const std::string& kname, T& E, T& G, T& H) {
  E = constant<T>(kname.c_str(), "E");
  G = constant<T>(kname.c_str(), "G");
  H = constant<T>(kname.c_str(), "H");
  if (g_variant == Variant::ball2_no_E) E = T(0);
  if (g_variant == Variant::ball2_no_H) H = T(0);
}

template <class T>
Ball<T> ball_add2(const std::string& kname, int k, Ball<T> x, Ball<T> y) {
  T E, G, H;
  radius_constants(kname, E, G, H);
  Ball<T> z;
  z.c1 = T(0);
  if (k == 1) z.c0 = add(x.c0, y.c0);
  else add_2_2(x.c0, x.c1, y.c0, y.c1, z.c0, z.c1);
  T az = std::fabs(z.c0);
  T s = add(x.r, y.r);
  T t = fma_(az, E, s);
  z.r = fma_(t, G, H);
  return z;
}

template <class T>
Ball<T> ball_mul2(const std::string& kname, int k, Ball<T> x, Ball<T> y) {
  T E, G, H;
  radius_constants(kname, E, G, H);
  Ball<T> z;
  z.c1 = T(0);
  if (k == 1) z.c0 = prod(x.c0, y.c0);
  else mul_2_2(x.c0, x.c1, y.c0, y.c1, z.c0, z.c1);
  T ax = std::fabs(x.c0);
  T ay = std::fabs(y.c0);
  T az = std::fabs(z.c0);
  T p = prod(x.r, y.r);
  T q = fma_(ay, x.r, p);
  T w = fma_(ax, y.r, q);
  T t = fma_(az, E, w);
  z.r = fma_(t, G, H);
  return z;
}

template <class T>
Ball<T> ball_scale2(const std::string& kname, int k, Ball<T> x, T a) {
  T E, G, H;
  radius_constants(kname, E, G, H);
  Ball<T> z;
  z.c1 = T(0);
  if (k == 1) z.c0 = prod(x.c0, a);
  else mul_2_1(x.c0, x.c1, a, z.c0, z.c1);
  T aa = std::fabs(a);
  T az = std::fabs(z.c0);
  T p = prod(aa, x.r);
  T t = fma_(az, E, p);
  z.r = fma_(t, G, H);
  return z;
}

// Runs a Ball kernel "ball_OP_K" on v; false when the name or the arity does not fit.
template <class T>
bool run_ball(const std::string& k, const std::vector<T>& v, std::vector<T>& out) {
  if (k.size() < 7 || k.compare(0, 5, "ball_") != 0) return false;
  int n = k.back() - '0';
  if ((n != 1 && n != 2) || k[k.size() - 2] != '_') return false;
  std::string op = k.substr(5, k.size() - 7);
  std::size_t per = static_cast<std::size_t>(n) + 1;
  auto ball = [&](std::size_t at) {
    Ball<T> b;
    b.c0 = v[at];
    b.c1 = n == 2 ? v[at + 1] : T(0);
    b.r = v[at + n];
    return b;
  };
  Ball<T> z;
  if ((op == "add" || op == "sub" || op == "mul") && v.size() == 2 * per) {
    Ball<T> x = ball(0), y = ball(per);
    if (op == "sub") {
      y.c0 = -y.c0;
      y.c1 = -y.c1;
    }
    if (g_radius2) z = op == "mul" ? ball_mul2(k, n, x, y) : ball_add2(k, n, x, y);
    else z = op == "mul" ? ball_mul(n, x, y) : ball_add(n, x, y);
  } else if (op == "neg" && v.size() == per) {
    z = ball(0);
    z.c0 = -z.c0;
    z.c1 = -z.c1;
  } else if (op == "scale" && v.size() == per + 1) {
    z = g_radius2 ? ball_scale2(k, n, ball(0), v[per]) : ball_scale(n, ball(0), v[per]);
  } else {
    return false;
  }
  out = {z.c0};
  if (n == 2) out.push_back(z.c1);
  out.push_back(z.r);
  return true;
}

// ---------------------------------------------------------------------------------------------
// The non-finite layer (milestone1.md, "IEEE-like results", "Values that enter from the program",
// "Ball kernels"): the core, then a fix-up on the leading limbs, as listed.

template <class T> T inf_() { return std::numeric_limits<T>::infinity(); }
template <class T> T qnan_() { return std::numeric_limits<T>::quiet_NaN(); }
// times_inf(a): a plain multiplication by +infinity, a NaN for a NaN or a zero.
template <class T> T times_inf(T a) { return a * inf_<T>(); }

// The fix-up of a full kernel: (z0, z1) from the core, t the operation of T on the leading limbs.
// fin (every operand finite) is read by the injected errors only.
template <class T>
void fixup(T z0, T z1, T t, bool fin, T& w0, T& w1) {
  if (g_variant == Variant::full_no_fixup) {
    w0 = z0;
    w1 = z1;
    return;
  }
  T a = std::fabs(z0);
  bool f = a < inf_<T>();          // z0 is finite
  T r0 = times_inf(t);             // a NaN or a zero gives a NaN; any other t the infinity of its sign
  bool n = r0 == r0;               // r0 is not a NaN
  T r1 = n ? T(0) : r0;
  if (g_variant == Variant::full_inf_tail_nan && n) r1 = qnan_<T>();
  else if (g_variant == Variant::full_inf_tail_eta && n) r1 = std::numeric_limits<T>::denorm_min();
  else if (g_variant == Variant::full_nan_one_limb && !n) r1 = T(0);
  if (!f && fin) {
    if (g_variant == Variant::full_overflow_sign) {
      r0 = -r0;
    } else if (g_variant == Variant::full_overflow_nan) {
      r0 = r1 = qnan_<T>();
    } else if (g_variant == Variant::full_overflow_finite) {
      r0 = r0 > T(0) ? std::numeric_limits<T>::max() : -std::numeric_limits<T>::max();
      r1 = T(0);
    }
  }
  if (g_variant == Variant::full_spurious_overflow && f && fin &&
      std::fabs(t) >= std::ldexp(T(1), std::numeric_limits<T>::max_exponent - 3)) {
    w0 = t > T(0) ? inf_<T>() : -inf_<T>();
    w1 = T(0);
    return;
  }
  w0 = f ? z0 : r0;
  w1 = f ? z1 : r1;
  if (g_variant == Variant::full_nan_to_zero && w0 != w0) {
    w0 = T(0);
    w1 = T(0);
  }
}

template <class T>
bool all_finite(const std::vector<T>& v) {
  for (T a : v)
    if (!std::isfinite(a)) return false;
  return true;
}

// The nine full arithmetic kernels.
template <class T>
bool run_full(const std::string& k, const std::vector<T>& v, T& w0, T& w1) {
  T z0, z1, t;
  if (k == "add_2_2_full" && v.size() == 4) {
    add_2_2(v[0], v[1], v[2], v[3], z0, z1);
    t = add(v[0], v[2]);
  } else if (k == "add_fast_2_2_full" && v.size() == 4) {
    add_fast_2_2(v[0], v[1], v[2], v[3], z0, z1);
    t = add(v[0], v[2]);
  } else if (k == "sub_2_2_full" && v.size() == 4) {
    add_2_2(v[0], v[1], -v[2], -v[3], z0, z1);
    t = sub(v[0], v[2]);
  } else if (k == "add_2_1_full" && v.size() == 3) {
    T g = guard(v[2]);
    add_2_1(v[0], v[1], v[2], z0, z1);
    t = add(v[0], g);
  } else if (k == "sub_2_1_full" && v.size() == 3) {
    T g = guard(v[2]);
    add_2_1(v[0], v[1], -v[2], z0, z1);
    t = sub(v[0], g);
  } else if (k == "sub_1_2_full" && v.size() == 3) {
    T g = guard(v[0]);
    add_2_1(-v[1], -v[2], v[0], z0, z1);
    t = sub(g, v[1]);
  } else if (k == "mul_2_2_full" && v.size() == 4) {
    mul_2_2(v[0], v[1], v[2], v[3], z0, z1);
    t = prod(v[0], v[2]);
  } else if (k == "mul_2_1_full" && v.size() == 3) {
    mul_2_1(v[0], v[1], v[2], z0, z1);
    t = prod(v[0], v[2]);
  } else if (k == "mul_pow2_2_full" && v.size() == 3) {
    mul_pow2_2(v[0], v[1], v[2], z0, z1);
    t = prod(v[0], v[2]);
  } else {
    return false;
  }
  fixup(z0, z1, t, all_finite(v), w0, w1);
  return true;
}

// The fix-up of a full Ball kernel: z from the core, q a NaN exactly when an operand is empty.
template <class T>
Ball<T> ball_fixup(Ball<T> z, T q) {
  if (g_variant == Variant::ball_full_zero_inf_empty) q = z.r;
  bool e = q == q;
  T a = std::fabs(z.c0);
  bool f1 = a < inf_<T>();         // the center is finite
  bool f2 = z.r < inf_<T>();       // the radius is finite (false for a NaN)
  bool f = f1 && f2;
  T c0 = f ? z.c0 : T(0);
  T c1 = f ? z.c1 : T(0);
  T r = f ? z.r : inf_<T>();
  if (g_variant == Variant::ball_full_finite_whole && f1 && !f2) {
    c0 = z.c0;
    c1 = z.c1;
    r = std::numeric_limits<T>::max();
  }
  Ball<T> w;
  if (g_variant == Variant::ball_full_swap && (!e || !f)) {
    w.c0 = w.c1 = !e ? T(0) : qnan_<T>();
    w.r = !e ? inf_<T>() : qnan_<T>();
    return w;
  }
  w.c0 = e ? c0 : q;
  w.c1 = e ? c1 : q;
  w.r = e ? r : q;
  return w;
}

// ball_OP_K_full: the core ball_OP_K, then the fix-up.
template <class T>
bool run_ball_full(const std::string& k, const std::vector<T>& v, std::vector<T>& out) {
  const std::string suffix = "_full";
  if (k.size() <= suffix.size() || k.compare(0, 5, "ball_") != 0 ||
      k.compare(k.size() - suffix.size(), suffix.size(), suffix) != 0)
    return false;
  const std::string core = k.substr(0, k.size() - suffix.size());
  std::vector<T> z;
  if (!run_ball(core, v, z)) return false;
  int n = core.back() - '0';
  bool scale = core.compare(5, 5, "scale") == 0;
  T q = scale ? v[n] : add(v[n], v[2 * n + 1]);
  Ball<T> b;
  b.c0 = z[0];
  b.c1 = n == 2 ? z[1] : T(0);
  b.r = z.back();
  Ball<T> w = ball_fixup(b, q);
  out = {w.c0};
  if (n == 2) out.push_back(w.c1);
  out.push_back(w.r);
  return true;
}

template <class T>
void make_2(T a, T& x0, T& x1) {
  x0 = guard(a);
  bool n = x0 == x0;
  x1 = n ? T(0) : x0;
  if (g_variant == Variant::make2_inf_nan_tail && n) x1 = sub(x0, x0);
}

// ball_make_k(c, r) with the center already guarded for k = 1.
template <class T>
std::vector<T> ball_make(int k, T c0, T c1, T r) {
  T g = guard(r);
  bool e = T(0) <= g;              // false for a NaN or a negative radius
  if (g_variant == Variant::make_negative_radius) e = g == g;
  else if (g_variant == Variant::make_nan_radius) e = true;
  T a = std::fabs(c0);
  bool f1 = a < inf_<T>();
  bool f2 = g < inf_<T>();
  bool f = f1 && f2;
  T k0 = f ? c0 : T(0);
  T k1 = f ? c1 : T(0);
  T s = f ? g : inf_<T>();
  std::vector<T> out = {e ? k0 : qnan_<T>()};
  if (k == 2) out.push_back(e ? k1 : qnan_<T>());
  out.push_back(e ? s : qnan_<T>());
  return out;
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

bool is_first_wave(const std::string& k) {
  return k == "two_sum" || k == "fast_two_sum" || k == "two_prod" || k == "two_prod_dekker" ||
         k == "split" || k == "add_2_2" || k == "add_2_1" || k == "mul_2_2" || k == "mul_2_1" ||
         k == "add_fast_2_2";
}

// The comparisons: (relation, form) -> mask, with (a, 0) in place of a one-limb operand.
template <class T>
bool run_compare(const std::string& k, const std::vector<T>& v, int& mask) {
  if (k.size() != 6 || k[2] != '_' || k[4] != '_') return false;
  std::string rel = k.substr(0, 2), form = k.substr(3);
  T x0, x1, y0, y1;
  if (form == "2_2" && v.size() == 4) {
    x0 = v[0]; x1 = v[1]; y0 = v[2]; y1 = v[3];
  } else if (form == "2_1" && v.size() == 3) {
    x0 = v[0]; x1 = v[1]; y0 = v[2]; y1 = T(0);
  } else if (form == "1_2" && v.size() == 3) {
    x0 = v[0]; x1 = T(0); y0 = v[1]; y1 = v[2];
  } else {
    return false;
  }
  if (rel == "lt") mask = lt_2_2(x0, x1, y0, y1, true);
  else if (rel == "le") mask = lt_2_2(x0, x1, y0, y1, false);
  else if (rel == "eq") mask = eq_2_2(x0, x1, y0, y1);
  else return false;
  return true;
}

// Fills out (limbs) or mask (0 or 1) for kernel k on the input limbs v.
template <class T>
bool run_kernel(const std::string& k, const std::vector<T>& v, std::vector<T>& out, int& mask) {
  T z0, z1;
  mask = -1;
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
  else if (k == "neg_2" && v.size() == 2) { z0 = -v[0]; z1 = -v[1]; }
  else if (k == "abs_2" && v.size() == 2) abs_2(v[0], v[1], z0, z1);
  else if (k == "sub_2_2" && v.size() == 4) add_2_2(v[0], v[1], -v[2], -v[3], z0, z1);
  else if (k == "sub_2_1" && v.size() == 3) add_2_1(v[0], v[1], -v[2], z0, z1);
  else if (k == "sub_1_2" && v.size() == 3) add_2_1(-v[1], -v[2], v[0], z0, z1);
  else if (k == "mul_pow2_2" && v.size() == 3) mul_pow2_2(v[0], v[1], v[2], z0, z1);
  else if (run_full(k, v, z0, z1)) {}
  else if (k == "make_2" && v.size() == 1) make_2(v[0], z0, z1);
  else if (k == "make_2_limbs" && v.size() == 2) { z0 = guard(v[0]); z1 = guard(v[1]); }
  else if (k == "ball_make_1" && v.size() == 2) { out = ball_make(1, guard(v[0]), T(0), v[1]); return true; }
  else if (k == "ball_make_2" && v.size() == 3) { out = ball_make(2, v[0], v[1], v[2]); return true; }
  else if (run_ball_full(k, v, out)) return true;
  else if (run_compare(k, v, mask)) return true;
  else if (run_ball(k, v, out)) return true;
  else {
    T t;
    if (k == "to_nearest_2" && v.size() == 2) t = v[0];
    else if (k == "to_down_2" && v.size() == 2) t = to_down_2(v[0], v[1]);
    else if (k == "to_up_2" && v.size() == 2) t = to_up_2(v[0], v[1]);
    else if (k == "abs_upper_2" && v.size() == 2) t = abs_upper_2(v[0], v[1]);
    else if (k == "add_1_1" && v.size() == 2) t = add(v[0], v[1]);
    else if (k == "mul_1_1" && v.size() == 2) t = prod(v[0], v[1]);
    else if (k == "radd" && v.size() == 2) t = radd(v[0], v[1]);
    else if (k == "rmul" && v.size() == 2) t = rmul(v[0], v[1]);
    else return false;
    out = {t};
    return true;
  }
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
  int mask;
  if (!run_kernel<T>(kernel, vals, out, mask)) return false;
  if (mask >= 0) {
    result = prefix + line + " -> " + (mask ? "1" : "0");
    return true;
  }
  const bool first = is_first_wave(kernel);
  if (g_variant == Variant::ulp_rare && first && fnv1a(line) % 256 == 0)
    out[1] = std::nextafter(out[1], std::numeric_limits<T>::infinity());
  if (g_variant == Variant::not_normalized && first && is_finite_nonzero(out[0]) &&
      std::isfinite(out[1])) {
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
    if (std::strcmp(argv[i], "--const") == 0 && i + 1 < argc) {
      std::string spec = argv[++i];
      std::size_t eq = spec.find('=');
      if (eq == std::string::npos) {
        std::fprintf(stderr, "refrun: --const wants FORMAT.KERNEL.U=HEX, got %s\n", spec.c_str());
        return 2;
      }
      g_consts[spec.substr(0, eq)] = std::strtod(spec.c_str() + eq + 1, nullptr);
    } else if (std::strcmp(argv[i], "--variant") == 0 && i + 1 < argc) {
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
    } else if (std::strcmp(argv[i], "--radius") == 0 && i + 1 < argc) {
      const char* design = argv[++i];
      if (std::strcmp(design, "first") == 0) {
        g_radius2 = false;
      } else if (std::strcmp(design, "second") == 0) {
        g_radius2 = true;
      } else {
        std::fprintf(stderr, "refrun: unknown radius design %s (first or second)\n", design);
        return 2;
      }
    } else {
      std::fprintf(stderr, "usage: refrun [--variant NAME] [--radius first|second] "
                           "[--const FORMAT.KERNEL.C=HEX ...]\n");
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
