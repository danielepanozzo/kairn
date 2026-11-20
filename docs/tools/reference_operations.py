"""Which public operation of Kairn calls which kernel: the one table of the reference pages that
is written by hand. docs/tools/reference.py reads it; docs/tools/test_reference.py checks it
against gen/claims.json and against the comments of the public headers.

KERNELS has one entry per kernel of gen/claims.json, and each entry becomes one page,
docs/reference/KERNEL.md. An entry gives:

- group: where the page and its forms go in the index (GROUPS); a form can name another group;
- title: the page's name, in words;
- forms: the C++ expressions that reach the kernel. A form is the code as a client writes it,
  the type of each operand in order, and the type of the result. `T` is the limb type, float or
  double; `Expansion<T, 2>` is a number of two limbs, `Ball<T, 1>` a ball with a one-limb center.
  The header declaration of an operation whose comment names the kernel must be one of them
  (the test reads include/kairn/*.hpp); a form that reaches the kernel through an implicit
  conversion (a limb converted to a one-limb number, a point to a ball) has no declaration of
  its own, and says so in its note;
  A kernel with no forms is either a building block, part of other kernels, or an entry kernel
  (`entry: yes` in its description: today the finite cores of the Ball operations) that the
  public headers do not call yet; its page and the index say which. Give it forms only when a
  header calls it: the test fails on a form of a kernel that no header comment names. A function
  of `kairn::finite` is written `finite::add(x, y)`, a member function `X.name()`, with the object
  as its first operand;
- traits: the entries of kairn::traits whose constants come from this kernel's claims
  (traits<T> is also traits<float>, traits<double> and traits<Expansion<T, 1>>);
- note: optional, one sentence about the forms, shown under them.

EXACT lists the public operations that call no kernel: IEEE 754 operations on one limb,
construction and access, which only copy limbs, and the constants of include/kairn/rational.hpp,
which compute with integers. They appear in the index, not on pages of their own.

PAGES lists the pages of docs/reference/ written by hand for operations of EXACT that need more
than a line of the index: (group, title, file name without .md). reference.py puts each in the
nav after the kernel pages of its group, and neither writes nor removes it.

Nothing here is a number, a bound or a status: those come from gen/claims.json and the stored
results, and the reference pages print them from there.
"""

E1 = "Expansion<T, 1>"
E2 = "Expansion<T, 2>"
B1 = "Ball<T, 1>"
B2 = "Ball<T, 2>"
T = "T"

# The groups of the index, in order: (id, title, what the group is).
GROUPS = [
    ("construction", "Construction and access",
     "Making numbers and balls, and reading their parts."),
    ("arithmetic", "Arithmetic", "Sums, differences, products, negation and absolute value. The operators "
     "of two limbs return IEEE-like results: canonical infinities and NaN, as `T` does."),
    ("finite", "Arithmetic without the fix-up",
     "`kairn::finite::`: the finite cores of the operators of two limbs, without the fix-up that makes "
     "infinities and NaN canonical; for one limb, the operators themselves."),
    ("comparisons", "Comparisons", "Whether one value is below, at most, or equal to another."),
    ("conversions", "Conversions to one limb", "A two-limb number rounded to a value of `T`."),
    ("scaling", "Scaling by a power of two", "`ldexp` and `half`, of numbers and of balls; for a ball exact when "
     "nothing underflows, unlike the scaling `X * a` by a `T`, whose radius grows even when `a` is a power of two."),
    ("ball", "Ball operations", "Arithmetic on balls: the result contains every result on points of the operands; "
     "and the sign predicates of a ball, comparisons of its radius with its center."),
    ("blocks", "Building blocks on T",
     "Functions of `float` and `double` (`kairn/blocks.hpp`) for a program's own tests of exactness, its own "
     "radius arithmetic, and bounds rounded down or up without changing the rounding mode. Each is one call of "
     "its kernel, whose page says what it states. All are `constexpr` but `mul_down` and `mul_up`; all round, "
     "and so are preceded by the debug build's check of the rounding mode, but `next_up` and `next_down`, which "
     "are integer operations on the bit pattern and are checked for nothing. The note of each form on its page "
     "says what constant evaluation gives."),
    ("building-blocks", "Parts of other kernels",
     "Kernels that other kernels call, and that no public operation computes on its own."),
    ("arrays", "Sums and dot products of arrays",
     "The kernels of the loops over arrays (the folds of Milestone 2): their steps, the finish of their "
     "result, and the bounds of a sum and of a dot product as a function of the number of terms. The "
     "functions on arrays of the public headers come later."),
]


def form(code, *operands, result, group=None, note=None):
    """One C++ form: the code, the type of each operand, the type of the result."""
    return {"code": code, "operands": list(operands), "result": result, "group": group, "note": note}


def page(group, title, *forms, traits=(), note=None):
    return {"group": group, "title": title, "forms": list(forms), "traits": list(traits), "note": note}


ONE = "the limb of the `Expansion<T, 1>` operand is the limb $a$"
# The notes of the building blocks on T: whether constant evaluation has them, with what, and that
# they round.
SAME_BITS = "`constexpr`, with the same bits in constant evaluation; rounds"
SAME_VALUES = ("`constexpr`, with the same values in constant evaluation (a zero result can differ in sign); "
               "rounds")
GUARDED = "; the operands are guarded ([rule R3](../developer/architecture.md#the-kernel-ir))"
CONVERTED = "the limb is converted to `Expansion<T, 1>` first, exactly"
POINT = "the point is the ball of radius 0 its constructor makes"
CORE = "the finite core: no fix-up of infinities and NaN"
# The steps of ldexp beyond the powers of two of T are written in the header, not generated
# (deviation 17 of docs/developer/design/phase0/decisions.md): every page that shows such a form
# says so in these words.
COMPOSITION = ("argued and tested but not machine-checked "
               "([What holds today](../getting-started/guarantees.md#overflow-and-non-finite-values))")

KERNELS = {
    # --- Constructors ---------------------------------------------------------------------------
    "make_2": page(
        "construction", "A two-limb number from a value of T",
        form("Expansion<T, 2>(a)", T, result=E2, note="implicit"),
        form("Expansion<T, 2>(a)", E1, result=E2, note="implicit; " + ONE),
    ),
    "make_2_limbs": page(
        "construction", "A two-limb number from its limbs",
        form("from_limbs(p)", "T*", result=E2,
             note="`Expansion<T, 2>::from_limbs(p)`, with `p` pointing to the two limbs; checked when "
                  "`KAIRN_CHECKS` is 1"),
        form("from_limbs_unchecked(p)", "T*", result=E2, note="the same, never checked"),
        form("Expansion<T, 2>(r)", "SumAndError<T>", result=E2,
             note="explicit: the result `r` of `two_sum` or `fast_two_sum` as the pair (`r.sum`, `r.error`), "
                  "through `from_limbs_unchecked`; canonical, of value $a + b$ exactly, when both members are "
                  "finite, which a debug build checks ([`two_sum_entry`](two_sum_entry.md) says when)"),
    ),
    "ball_make_1": page(
        "construction", "A ball from a one-limb center and a radius",
        form("Ball<T, 1>(c, r)", E1, T, result=B1),
        form("Ball<T, 1>(c)", E1, result=B1, note="implicit: the point $c$, radius 0"),
        form("Ball<T, 1>(a)", T, result=B1, note="implicit: the point $a$, radius 0"),
        form("Ball<T, 1>(q)", "Constant<Expansion<T, 1>>", result=B1,
             note="explicit: center `q.value`, radius `q.error`, for `q` a result of `rational` or `integer`; "
                  "`constexpr`; does not round"),
    ),
    "ball_make_2": page(
        "construction", "A ball from a two-limb center and a radius",
        form("Ball<T, 2>(c, r)", E2, T, result=B2),
        form("Ball<T, 2>(c)", E2, result=B2, note="implicit: the point $c$, radius 0"),
        form("Ball<T, 2>(a)", T, result=B2,
             note="implicit: the point $a$, radius 0, with the center made by `make_2` first"),
        form("Ball<T, 2>(q)", "Constant<Expansion<T, 2>>", result=B2,
             note="explicit: center `q.value`, radius `q.error`, for `q` a result of `rational` or `integer`: "
                  "how to multiply a ball by $1/s$, `X * Ball<T, 2>(rational<Expansion<T, 2>>(1, s))`, until "
                  "Kairn has a division; `constexpr`; its check of the center rounds"),
    ),
    # --- One limb -----------------------------------------------------------------------------
    "add_1_1": page(
        "arithmetic", "Sum and difference, one limb",
        form("a + b", E1, E1, result=E1),
        form("a += b", E1, E1, result=E1),
        form("a + b", E1, T, result=E1, note=CONVERTED),
        form("a + b", T, E1, result=E1, note=CONVERTED),
        form("add_fast(a, b)", E1, E1, result=E1),
        form("a - b", E1, E1, result=E1, note="the sum $a + (-b)$: negating $b$ is exact"),
        form("a -= b", E1, E1, result=E1, note="the sum $a + (-b)$"),
        form("a - b", E1, T, result=E1, note="the sum $a + (-b)$; " + CONVERTED),
        form("a - b", T, E1, result=E1, note="the sum $a + (-b)$; " + CONVERTED),
        form("finite::add(a, b)", E1, E1, result=E1, group="finite", note="the operator itself"),
        form("finite::add(a, b)", E1, T, result=E1, group="finite"),
        form("finite::add(a, b)", T, E1, result=E1, group="finite"),
        form("finite::sub(a, b)", E1, E1, result=E1, group="finite", note="the sum $a + (-b)$"),
        form("finite::sub(a, b)", E1, T, result=E1, group="finite"),
        form("finite::sub(a, b)", T, E1, result=E1, group="finite"),
        form("finite::add_fast(a, b)", E1, E1, result=E1, group="finite"),
        traits=["traits<T>::add", "traits<T>::add_limb", "traits<T>::add_fast", "traits<T>::sub",
                "traits<T>::sub_limb"],
        note="The code is one addition of `T`; as for `T`, a compiler that contracts may fuse it "
             "with a product it sees ([One limb](../getting-started/guarantees.md#one-limb)).",
    ),
    "mul_1_1": page(
        "arithmetic", "Product, one limb",
        form("a * b", E1, E1, result=E1),
        form("a *= b", E1, E1, result=E1),
        form("a * b", E1, T, result=E1, note=CONVERTED),
        form("a * b", T, E1, result=E1, note=CONVERTED),
        form("ldexp(a, n)", E1, "int", result=E1, group="scaling",
             note="$b = 2^n$, for every `n`: when $2^n$ is not a number of `T`, two or three products by "
                  "powers of two of `T`, of which only one rounds; that their composition gives "
                  "$\\mathrm{RN}(2^n a)$, the result of `std::ldexp`, is " + COMPOSITION),
        form("half(a)", E1, result=E1, group="scaling", note="$b = 1/2$"),
        form("finite::mul(a, b)", E1, E1, result=E1, group="finite", note="the operator itself"),
        form("finite::mul(a, b)", E1, T, result=E1, group="finite"),
        form("finite::mul(a, b)", T, E1, result=E1, group="finite"),
        form("finite::ldexp(a, n)", E1, "int", result=E1, group="finite", note="`ldexp(a, n)` itself"),
        traits=["traits<T>::mul", "traits<T>::mul_limb", "traits<T>::ldexp"],
        note="The code is one product of `T`; as for `T`, a compiler that contracts may fuse it "
             "with an addition it sees ([One limb](../getting-started/guarantees.md#one-limb)).",
    ),
    # --- Two limbs: arithmetic, the full kernels -----------------------------------------------
    "add_2_2_full": page(
        "arithmetic", "Sum of two two-limb numbers",
        form("x + y", E2, E2, result=E2),
        form("x += y", E2, E2, result=E2),
    ),
    "add_2_1_full": page(
        "arithmetic", "Sum of a two-limb number and a limb",
        form("x + a", E2, T, result=E2),
        form("a + x", T, E2, result=E2),
        form("x += a", E2, T, result=E2),
        form("x + y", E2, E1, result=E2, note=ONE),
        form("y + x", E1, E2, result=E2, note=ONE),
        form("x += y", E2, E1, result=E2, note=ONE),
    ),
    "sub_2_2_full": page(
        "arithmetic", "Difference of two two-limb numbers",
        form("x - y", E2, E2, result=E2),
        form("x -= y", E2, E2, result=E2),
    ),
    "sub_2_1_full": page(
        "arithmetic", "A two-limb number minus a limb",
        form("x - a", E2, T, result=E2),
        form("x -= a", E2, T, result=E2),
        form("x - y", E2, E1, result=E2, note=ONE),
        form("x -= y", E2, E1, result=E2, note=ONE),
    ),
    "sub_1_2_full": page(
        "arithmetic", "A limb minus a two-limb number",
        form("a - y", T, E2, result=E2),
        form("x - y", E1, E2, result=E2, note="the limb of the `Expansion<T, 1>` operand is the limb $a$"),
    ),
    "mul_2_2_full": page(
        "arithmetic", "Product of two two-limb numbers",
        form("x * y", E2, E2, result=E2),
        form("x *= y", E2, E2, result=E2),
    ),
    "mul_2_1_full": page(
        "arithmetic", "Product of a two-limb number and a limb",
        form("x * a", E2, T, result=E2),
        form("a * x", T, E2, result=E2),
        form("x *= a", E2, T, result=E2),
        form("x * y", E2, E1, result=E2, note=ONE),
        form("y * x", E1, E2, result=E2, note=ONE),
        form("x *= y", E2, E1, result=E2, note=ONE),
    ),
    "add_fast_2_2_full": page(
        "arithmetic", "Fast sum of two two-limb numbers",
        form("add_fast(x, y)", E2, E2, result=E2),
    ),
    "neg_2": page(
        "arithmetic", "Negation, two limbs",
        form("-x", E2, result=E2),
    ),
    "abs_2": page(
        "arithmetic", "Absolute value, two limbs",
        form("abs(x)", E2, result=E2),
    ),
    # --- Two limbs: the finite cores, kairn::finite ---------------------------------------------
    "add_2_2": page(
        "finite", "Sum of two two-limb numbers, finite core",
        form("finite::add(x, y)", E2, E2, result=E2, note=CORE),
        traits=["traits<Expansion<T, 2>>::add"],
    ),
    "add_2_1": page(
        "finite", "Sum of a two-limb number and a limb, finite core",
        form("finite::add(x, a)", E2, T, result=E2, note=CORE),
        form("finite::add(a, x)", T, E2, result=E2),
        form("finite::add(x, y)", E2, E1, result=E2, note=ONE),
        form("finite::add(y, x)", E1, E2, result=E2, note=ONE),
        traits=["traits<Expansion<T, 2>>::add_limb"],
    ),
    "sub_2_2": page(
        "finite", "Difference of two two-limb numbers, finite core",
        form("finite::sub(x, y)", E2, E2, result=E2, note=CORE),
        traits=["traits<Expansion<T, 2>>::sub"],
    ),
    "sub_2_1": page(
        "finite", "A two-limb number minus a limb, finite core",
        form("finite::sub(x, a)", E2, T, result=E2, note=CORE),
        form("finite::sub(x, y)", E2, E1, result=E2, note=ONE),
        traits=["traits<Expansion<T, 2>>::sub_limb"],
    ),
    "sub_1_2": page(
        "finite", "A limb minus a two-limb number, finite core",
        form("finite::sub(a, y)", T, E2, result=E2, note=CORE),
        form("finite::sub(x, y)", E1, E2, result=E2, note="the limb of the `Expansion<T, 1>` operand is the limb $a$"),
        traits=["traits<Expansion<T, 2>>::sub_limb"],
    ),
    "mul_2_2": page(
        "finite", "Product of two two-limb numbers, finite core",
        form("finite::mul(x, y)", E2, E2, result=E2, note=CORE),
        traits=["traits<Expansion<T, 2>>::mul"],
    ),
    "mul_2_1": page(
        "finite", "Product of a two-limb number and a limb, finite core",
        form("finite::mul(x, a)", E2, T, result=E2, note=CORE),
        form("finite::mul(a, x)", T, E2, result=E2),
        form("finite::mul(x, y)", E2, E1, result=E2, note=ONE),
        form("finite::mul(y, x)", E1, E2, result=E2, note=ONE),
        traits=["traits<Expansion<T, 2>>::mul_limb"],
    ),
    "add_fast_2_2": page(
        "finite", "Fast sum of two two-limb numbers, finite core",
        form("finite::add_fast(x, y)", E2, E2, result=E2, note=CORE),
        traits=["traits<Expansion<T, 2>>::add_fast"],
    ),
    "mul_pow2_2": page(
        "finite", "Scaling a two-limb number by a power of two, finite core",
        form("finite::ldexp(x, n)", E2, "int", result=E2,
             note=CORE + "; $c = 2^n$, for every `n`: when $2^n$ is not a number of `T`, two or three calls, "
                         "as for `ldexp`, whose composition is " + COMPOSITION),
        traits=["traits<Expansion<T, 2>>::ldexp"],
    ),
    # --- Two limbs: comparisons ----------------------------------------------------------------
    "lt_2_2": page(
        "comparisons", "Less than, two two-limb numbers",
        form("x < y", E2, E2, result="bool"),
        form("y > x", E2, E2, result="bool"),
    ),
    "le_2_2": page(
        "comparisons", "At most, two two-limb numbers",
        form("x <= y", E2, E2, result="bool"),
        form("y >= x", E2, E2, result="bool"),
    ),
    "eq_2_2": page(
        "comparisons", "Equality, two two-limb numbers",
        form("x == y", E2, E2, result="bool"),
        form("x != y", E2, E2, result="bool", note="the negation of `x == y`"),
    ),
    "lt_2_1": page(
        "comparisons", "A two-limb number less than a limb",
        form("x < a", E2, T, result="bool"),
        form("a > x", T, E2, result="bool"),
        form("x < y", E2, E1, result="bool", note=ONE),
        form("y > x", E1, E2, result="bool", note=ONE),
        form("X.certainly_negative()", B2, result="bool", group="ball",
             note="whether every member of the ball is negative: $c < -r$, exactly; false for the empty set and "
                  "the whole line; `constexpr`; does not round"),
    ),
    "le_2_1": page(
        "comparisons", "A two-limb number at most a limb",
        form("x <= a", E2, T, result="bool"),
        form("a >= x", T, E2, result="bool"),
        form("x <= y", E2, E1, result="bool", note=ONE),
        form("y >= x", E1, E2, result="bool", note=ONE),
    ),
    "eq_2_1": page(
        "comparisons", "A two-limb number equal to a limb",
        form("x == a", E2, T, result="bool"),
        form("a == x", T, E2, result="bool"),
        form("x != a", E2, T, result="bool", note="the negation of `x == a`"),
        form("a != x", T, E2, result="bool", note="the negation of `a == x`"),
        form("x == y", E2, E1, result="bool", note=ONE),
        form("y == x", E1, E2, result="bool", note=ONE),
        form("x != y", E2, E1, result="bool", note="the negation of `x == y`; " + ONE),
        form("y != x", E1, E2, result="bool", note="the negation of `y == x`; " + ONE),
        form("X.certainly_zero()", B2, result="bool", group="ball",
             note="whether the ball is the point 0: $c = 0$, and $r = 0$ by a comparison of `T`; false for the "
                  "empty set and the whole line; `constexpr`; does not round"),
    ),
    "lt_1_2": page(
        "comparisons", "A limb less than a two-limb number",
        form("a < y", T, E2, result="bool"),
        form("y > a", E2, T, result="bool"),
        form("x < y", E1, E2, result="bool", note="the limb of the `Expansion<T, 1>` operand is the limb $a$"),
        form("y > x", E2, E1, result="bool", note="the limb of the `Expansion<T, 1>` operand is the limb $a$"),
        form("X.certainly_positive()", B2, result="bool", group="ball",
             note="whether every member of the ball is positive: $r < c$, exactly; false for the empty set and "
                  "the whole line; `constexpr`; does not round"),
    ),
    "le_1_2": page(
        "comparisons", "A limb at most a two-limb number",
        form("a <= y", T, E2, result="bool"),
        form("y >= a", E2, T, result="bool"),
        form("x <= y", E1, E2, result="bool", note="the limb of the `Expansion<T, 1>` operand is the limb $a$"),
        form("y >= x", E2, E1, result="bool", note="the limb of the `Expansion<T, 1>` operand is the limb $a$"),
    ),
    # --- Two limbs: conversions ----------------------------------------------------------------
    "to_nearest_2": page(
        "conversions", "Rounding to nearest",
        form("to_nearest(x)", E2, result=T),
        form("Expansion<T, 1>(x)", E2, result=E1, note="explicit: the leading limb"),
    ),
    "to_down_2": page(
        "conversions", "Rounding down",
        form("to_down(x)", E2, result=T),
    ),
    "to_up_2": page(
        "conversions", "Rounding up",
        form("to_up(x)", E2, result=T),
    ),
    "abs_upper_2": page(
        "conversions", "Upper bound of the magnitude",
        form("abs_upper(x)", E2, result=T),
    ),
    # --- Two limbs: scaling --------------------------------------------------------------------
    "mul_pow2_2_full": page(
        "scaling", "Scaling a two-limb number by a power of two",
        form("ldexp(x, n)", E2, "int", result=E2,
             note="$c = 2^n$, for every `n`: when $2^n$ is not a number of `T`, two or three calls, "
                  "whose composition is " + COMPOSITION),
        form("half(x)", E2, result=E2, note="$c = 1/2$"),
    ),
    # --- Balls ---------------------------------------------------------------------------------
    "ball_add_1_full": page(
        "ball", "Sum of balls, one-limb center",
        form("X + Y", B1, B1, result=B1),
        form("X += Y", B1, B1, result=B1),
        form("X + a", B1, T, result=B1, note=POINT),
        form("a + X", T, B1, result=B1, note=POINT),
        form("X + c", B1, E1, result=B1, note=POINT),
        form("c + X", E1, B1, result=B1, note=POINT),
        form("X += a", B1, T, result=B1, note=POINT),
        form("X += c", B1, E1, result=B1, note=POINT),
    ),
    "ball_add_2_full": page(
        "ball", "Sum of balls, two-limb center",
        form("X + Y", B2, B2, result=B2),
        form("X += Y", B2, B2, result=B2),
        form("X + a", B2, T, result=B2, note=POINT),
        form("a + X", T, B2, result=B2, note=POINT),
        form("X + c", B2, E2, result=B2, note=POINT),
        form("c + X", E2, B2, result=B2, note=POINT),
        form("X += a", B2, T, result=B2, note=POINT),
        form("X += c", B2, E2, result=B2, note=POINT),
    ),
    "ball_sub_1_full": page(
        "ball", "Difference of balls, one-limb center",
        form("X - Y", B1, B1, result=B1),
        form("X -= Y", B1, B1, result=B1),
        form("X - a", B1, T, result=B1, note=POINT),
        form("a - X", T, B1, result=B1, note=POINT),
        form("X - c", B1, E1, result=B1, note=POINT),
        form("c - X", E1, B1, result=B1, note=POINT),
        form("X -= a", B1, T, result=B1, note=POINT),
        form("X -= c", B1, E1, result=B1, note=POINT),
    ),
    "ball_sub_2_full": page(
        "ball", "Difference of balls, two-limb center",
        form("X - Y", B2, B2, result=B2),
        form("X -= Y", B2, B2, result=B2),
        form("X - a", B2, T, result=B2, note=POINT),
        form("a - X", T, B2, result=B2, note=POINT),
        form("X - c", B2, E2, result=B2, note=POINT),
        form("c - X", E2, B2, result=B2, note=POINT),
        form("X -= a", B2, T, result=B2, note=POINT),
        form("X -= c", B2, E2, result=B2, note=POINT),
    ),
    "ball_mul_1_full": page(
        "ball", "Product of balls, one-limb center",
        form("X * Y", B1, B1, result=B1),
        form("X *= Y", B1, B1, result=B1),
    ),
    "ball_mul_2_full": page(
        "ball", "Product of balls, two-limb center",
        form("X * Y", B2, B2, result=B2),
        form("X *= Y", B2, B2, result=B2),
        form("X * c", B2, E2, result=B2, note=POINT),
        form("c * X", E2, B2, result=B2, note=POINT),
    ),
    "ball_scale_1_full": page(
        "ball", "A ball times a limb, one-limb center",
        form("X * a", B1, T, result=B1),
        form("a * X", T, B1, result=B1),
        form("X *= a", B1, T, result=B1),
        form("X * c", B1, E1, result=B1, note="the limb of the `Expansion<T, 1>` operand is the scalar $a$"),
        form("c * X", E1, B1, result=B1, note="the limb of the `Expansion<T, 1>` operand is the scalar $a$"),
    ),
    "ball_scale_2_full": page(
        "ball", "A ball times a limb, two-limb center",
        form("X * a", B2, T, result=B2),
        form("a * X", T, B2, result=B2),
        form("X *= a", B2, T, result=B2),
    ),
    "ball_neg_1": page(
        "ball", "Negation of a ball, one-limb center",
        form("-X", B1, result=B1),
    ),
    "ball_neg_2": page(
        "ball", "Negation of a ball, two-limb center",
        form("-X", B2, result=B2),
    ),
    # --- The finite cores of the Ball operations: entry kernels no public operation calls yet ---
    "ball_add_1": page("ball", "Sum of balls, one-limb center, finite core"),
    "ball_add_2": page("ball", "Sum of balls, two-limb center, finite core"),
    "ball_sub_1": page("ball", "Difference of balls, one-limb center, finite core"),
    "ball_sub_2": page("ball", "Difference of balls, two-limb center, finite core"),
    "ball_mul_1": page("ball", "Product of balls, one-limb center, finite core"),
    "ball_mul_2": page("ball", "Product of balls, two-limb center, finite core"),
    "ball_scale_1": page("ball", "A ball times a limb, one-limb center, finite core"),
    "ball_scale_2": page("ball", "A ball times a limb, two-limb center, finite core"),
    # --- Milestone 2: the scaling of a ball by a power of two ----------------------------------
    "ball_mul_pow2_1": page("ball", "A ball times a power of two, one-limb center, finite core"),
    "ball_mul_pow2_2": page("ball", "A ball times a power of two, two-limb center, finite core"),
    "ball_mul_pow2_1_full": page(
        "ball", "A ball times a power of two, one-limb center",
        form("ldexp(X, n)", B1, "int", result=B1, group="scaling",
             note="$c = 2^n$, for every `n`: when $2^n$ is not a number of `T`, two or three calls, whose "
                  "composition is " + COMPOSITION + "; not `constexpr` yet"),
        form("half(X)", B1, result=B1, group="scaling", note="$c = 1/2$; not `constexpr` yet"),
    ),
    "ball_mul_pow2_2_full": page(
        "ball", "A ball times a power of two, two-limb center",
        form("ldexp(X, n)", B2, "int", result=B2, group="scaling",
             note="$c = 2^n$, for every `n`: when $2^n$ is not a number of `T`, two or three calls, whose "
                  "composition is " + COMPOSITION + "; not `constexpr` yet"),
        form("half(X)", B2, result=B2, group="scaling", note="$c = 1/2$; not `constexpr` yet"),
    ),
    # --- Milestone 2: the building blocks on T (kairn/blocks.hpp) ---------------------------------
    "two_sum_entry": page(
        "blocks", "TwoSum on values of the program",
        form("two_sum(a, b)", T, T, result="SumAndError<T>",
             note=SAME_VALUES + GUARDED + "; `r.sum` is $s$ and `r.error` is $e$; `Expansion<T, 2>(r)` is the "
                  "pair as a number, canonical when both are finite: for finite $a$, $b$ whose sum does not "
                  "overflow and $\\lvert b\\rvert < \\Omega$ (with $b = \\pm\\Omega$ the error term can be a NaN "
                  "although the sum is finite)"),
    ),
    "fast_two_sum_entry": page(
        "blocks", "Fast2Sum on values of the program",
        form("fast_two_sum(a, b)", T, T, result="SumAndError<T>",
             note=SAME_VALUES + GUARDED + "; requires $\\lvert a\\rvert \\ge \\lvert b\\rvert$, which a debug build "
                  "checks; without it the sum is still $\\mathrm{RN}(a + b)$ and the error term a number of `T`, "
                  "but their sum need not be $a + b$"),
    ),
    "two_prod": page(
        "blocks", "TwoProd: an exact product as two limbs",
        form("two_prod(a, b)", T, T, result="ProductAndError<T>",
             note="`constexpr`, through Dekker's product ([`two_prod_dekker`](two_prod_dekker.md)) in constant "
                  "evaluation: the same values when the product is exact, each its own error term below the "
                  "threshold; rounds; `r.product` is $p$ and `r.error` is $e$"),
    ),
    "next_up": page(
        "blocks", "The next number of T above a value",
        form("next_up(a)", T, result=T,
             note="`constexpr`, with the same bits in constant evaluation; does not round: an integer operation "
                  "on the bit pattern, checked for nothing"),
    ),
    "next_down": page(
        "blocks", "The next number of T below a value",
        form("next_down(a)", T, result=T,
             note="`constexpr`, with the same bits in constant evaluation; does not round: an integer operation "
                  "on the bit pattern, checked for nothing"),
    ),
    "radd_entry": page(
        "blocks", "An upper bound of a sum, for radii, on values of the program",
        form("radd(a, b)", T, T, result=T, note=SAME_BITS + GUARDED),
    ),
    "rmul": page(
        "blocks", "An upper bound of a product, for radii",
        form("rmul(a, b)", T, T, result=T,
             note=SAME_BITS + ": the plain product in constant evaluation, whose zero can have the other sign, "
                  "and the step after either zero is $\\eta$"),
    ),
    "add_down_entry": page(
        "blocks", "A sum of two limbs rounded down, on values of the program",
        form("add_down(a, b)", T, T, result=T,
             note=SAME_VALUES + ": computes under rounding to nearest what rounding down gives" + GUARDED),
    ),
    "add_up_entry": page(
        "blocks", "A sum of two limbs rounded up, on values of the program",
        form("add_up(a, b)", T, T, result=T,
             note=SAME_VALUES + ": computes under rounding to nearest what rounding up gives" + GUARDED),
    ),
    "sub_down_entry": page(
        "blocks", "A difference of two limbs rounded down, on values of the program",
        form("sub_down(a, b)", T, T, result=T,
             note=SAME_VALUES + ": computes under rounding to nearest what rounding down gives" + GUARDED),
    ),
    "sub_up_entry": page(
        "blocks", "A difference of two limbs rounded up, on values of the program",
        form("sub_up(a, b)", T, T, result=T,
             note=SAME_VALUES + ": computes under rounding to nearest what rounding up gives" + GUARDED),
    ),
    "mul_down_1": page(
        "blocks", "A lower bound of a product of two limbs",
        form("mul_down(a, b)", T, T, result=T,
             note="not `constexpr`: its statement is about the fused product, which constant evaluation does not "
                  "have ([Building blocks on T](../developer/design/milestone2.md#building-blocks-on-t)); rounds"),
    ),
    "mul_up_1": page(
        "blocks", "An upper bound of a product of two limbs",
        form("mul_up(a, b)", T, T, result=T,
             note="not `constexpr`: its statement is about the fused product, which constant evaluation does not "
                  "have ([Building blocks on T](../developer/design/milestone2.md#building-blocks-on-t)); rounds"),
    ),
    # --- Building blocks: no public form -------------------------------------------------------
    "two_sum": page("building-blocks", "TwoSum: an exact sum as two limbs"),
    "fast_two_sum": page("building-blocks", "Fast2Sum: an exact sum of ordered operands"),
    "two_prod_dekker": page("building-blocks", "Dekker's product: TwoProd without an FMA"),
    "split": page("building-blocks", "Veltkamp's split"),
    "radd": page("building-blocks", "An upper bound of a sum, for radii"),
    "two_sum_ord": page("building-blocks", "TwoSum by ordering: Fast2Sum of the operands ordered by magnitude"),
    "add_down_1": page("building-blocks", "A sum of two limbs rounded down"),
    "add_up_1": page("building-blocks", "A sum of two limbs rounded up"),
    "sub_down_1": page("building-blocks", "A difference of two limbs rounded down"),
    "sub_up_1": page("building-blocks", "A difference of two limbs rounded up"),
    # --- Milestone 2, the folds: the steps, the finishes, the exported bounds ---------------------
    "dot_step_1": page("arrays", "The step of a dot product of one limb: one fused multiply-add"),
    "dot_step_2": page("arrays", "The step of a dot product of two limbs"),
    "sum_entry_step_1": page("arrays", "The step of a sum of one limb, on an array of the program"),
    "sum_entry_step_2": page("arrays", "The step of a sum of two limbs, on an array of the program"),
    "sum_fast_entry_step_2": page("arrays", "The step of a sum of two limbs with the fast addition, on an array of "
                                            "the program"),
    "fold_finish_1": page("arrays", "The result of a fold of one limb: the state, or NaN"),
    "fold_finish_2": page("arrays", "The result of a fold of two limbs: the state, or NaN"),
    "bound_sum_1": page("arrays", "The bound of a sum of one limb, as a function of the number of additions"),
    "bound_sum_2": page("arrays", "The bound of a sum of two limbs, as a function of the number of additions"),
    "bound_dot_1": page("arrays", "The bound of a dot product of one limb, as a function of the number of terms"),
    "bound_dot_2": page("arrays", "The bound of a dot product of two limbs, as a function of the number of terms"),
}


def exact(group, does, *forms):
    return {"group": group, "does": does, "forms": list(forms)}


# Operations that call no kernel. `does` is what the header comment says the operation does.
EXACT = [
    exact("construction", "zero",
          form("Expansion<T, K>()", result="Expansion<T, K>")),
    exact("construction", "the value $a$",
          form("Expansion<T, 1>(a)", T, result=E1)),
    exact("construction", "the limb $p_0$: every value of `T` is a one-limb number",
          form("Expansion<T, 1>::from_limbs(p)", "const T*", result=E1),
          form("Expansion<T, 1>::from_limbs_unchecked(p)", "const T*", result=E1)),
    exact("construction", "the limbs, most significant first; a limb written directly must not be "
          "a product the compiler can see, and the pair written must be canonical",
          form("x.limb[i]", "Expansion<T, K>", result="T")),
    exact("construction", "the point 0: center 0, radius 0",
          form("Ball<T, K>()", result="Ball<T, K>")),
    exact("construction", "the whole line: center 0, radius $+\\infty$",
          form("Ball<T, K>::whole()", result="Ball<T, K>")),
    exact("construction", "the empty set: every limb a NaN",
          form("Ball<T, K>::empty()", result="Ball<T, K>")),
    exact("construction", "the center; 0 for the whole line, NaN limbs for the empty set",
          form("X.center()", "Ball<T, K>", result="Expansion<T, K>")),
    exact("construction", "the radius; $+\\infty$ for the whole line, a NaN for the empty set",
          form("X.radius()", "Ball<T, K>", result="T")),
    exact("construction", "whether it is a finite ball (its radius is finite)",
          form("X.is_finite()", "Ball<T, K>", result="bool")),
    exact("construction", "whether it is the whole line (its radius is $+\\infty$)",
          form("X.is_whole()", "Ball<T, K>", result="bool")),
    exact("construction", "whether it is the empty set (its radius is a NaN)",
          form("X.is_empty()", "Ball<T, K>", result="bool")),
    exact("construction", "$-1$, $0$ or $+1$, from the leading limb; $0$ for NaN",
          form("sign(x)", "Expansion<T, K>", result="int")),
    exact("construction", "whether the leading limb is finite",
          form("isfinite(x)", "Expansion<T, K>", result="bool")),
    exact("construction", "whether every limb is finite and, for two limbs, $x_0 + x_1$ rounds to $x_0$",
          form("is_normalized(x)", "Expansion<T, K>", result="bool")),
    exact("ball", "whether every member is positive: $r < c$, the comparison of `T`; false for the empty set and "
          "the whole line",
          form("X.certainly_positive()", B1, result="bool")),
    exact("ball", "whether every member is negative: $c < -r$, the comparison of `T`; false for the empty set and "
          "the whole line",
          form("X.certainly_negative()", B1, result="bool")),
    exact("ball", "whether the ball is the point 0: $c = 0$ and $r = 0$; false for the empty set and the whole line",
          form("X.certainly_zero()", B1, result="bool")),
    exact("arithmetic", "the IEEE 754 operation of `T`: exact",
          form("-x", E1, result=E1),
          form("abs(x)", E1, result=E1)),
    exact("comparisons", "the comparison of `T`: exact; false if an operand is NaN (true for `!=`)",
          form("x < y, x > y, x <= y, x >= y, x == y, x != y", E1, E1, result="bool")),
    exact("conversions", "$x$ itself, or $\\lvert x\\rvert$ for `abs_upper`",
          form("to_nearest(x), to_down(x), to_up(x), abs_upper(x)", E1, result=T)),
    exact("construction", "$q = \\mathrm{num}/\\mathrm{den}$ as `X`: $\\mathrm{RN}(q)$ for one limb, for two the "
          "normalized pair of value $\\mathrm{RN}(q) + \\mathrm{RN}(q - \\mathrm{RN}(q))$; the smallest error "
          "bound of `T` and whether it is exact. Integer arithmetic, in constant expressions too; specified "
          "exactly, not machine-checked ([Constants from fractions](rational.md))",
          form("rational<X>(num, den)", "long long", "long long", result="Constant<X>")),
    exact("construction", "`rational<X>(n, 1)` ([Constants from fractions](rational.md))",
          form("integer<X>(n)", "long long", result="Constant<X>")),
    exact("construction", "whether `c` is what `rational<X>(num, den)` returns, decided with multiplications and "
          "comparisons of integers ([the check](rational.md#the-check))",
          form("is_rational_result(c, num, den)", "Constant<X>", "long long", "long long", result="bool")),
]

PAGES = [
    ("construction", "Constants from fractions", "rational"),
]
