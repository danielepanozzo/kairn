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
- traits: the entries of kairn::traits whose constants come from this kernel's claims
  (traits<T> is also traits<float>, traits<double> and traits<Expansion<T, 1>>);
- note: optional, one sentence about the forms, shown under them.

EXACT lists the public operations that call no kernel: IEEE 754 operations on one limb, and
construction and access, which only copy limbs. They appear in the index, not on pages of
their own.

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
     "Making numbers and balls, and reading their parts. No kernel: these copy limbs."),
    ("arithmetic", "Arithmetic", "Sums, differences, products, negation and absolute value."),
    ("comparisons", "Comparisons", "Whether one value is below, at most, or equal to another."),
    ("conversions", "Conversions to one limb", "A two-limb number rounded to a value of `T`."),
    ("scaling", "Scaling by a power of two", "`ldexp` and `half`."),
    ("ball", "Ball operations", "Arithmetic on balls: the result contains every result on points of the operands."),
    ("building-blocks", "Building blocks",
     "Kernels that other kernels call, and that no public operation computes on its own."),
]


def form(code, *operands, result, group=None, note=None):
    """One C++ form: the code, the type of each operand, the type of the result."""
    return {"code": code, "operands": list(operands), "result": result, "group": group, "note": note}


def page(group, title, *forms, traits=(), note=None):
    return {"group": group, "title": title, "forms": list(forms), "traits": list(traits), "note": note}


WIDENED = "the `Expansion<T, 1>` operand is converted to two limbs first, exactly"
CONVERTED = "the limb is converted to `Expansion<T, 1>` first, exactly"
POINT = "the point is converted to a ball of radius 0 first"

KERNELS = {
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
             note="$b = 2^n$, for an `n` with $2^n$ a number of `T`; otherwise the result is NaN"),
        form("half(a)", E1, result=E1, group="scaling", note="$b = 1/2$"),
        traits=["traits<T>::mul", "traits<T>::mul_limb", "traits<T>::ldexp"],
        note="The code is one product of `T`; as for `T`, a compiler that contracts may fuse it "
             "with an addition it sees ([One limb](../getting-started/guarantees.md#one-limb)).",
    ),
    # --- Two limbs: arithmetic -----------------------------------------------------------------
    "add_2_2": page(
        "arithmetic", "Sum of two two-limb numbers",
        form("x + y", E2, E2, result=E2),
        form("x += y", E2, E2, result=E2),
        form("x + y", E2, E1, result=E2, note=WIDENED),
        form("x + y", E1, E2, result=E2, note=WIDENED),
        traits=["traits<Expansion<T, 2>>::add"],
    ),
    "add_2_1": page(
        "arithmetic", "Sum of a two-limb number and a limb",
        form("x + a", E2, T, result=E2),
        form("a + x", T, E2, result=E2),
        form("x += a", E2, T, result=E2),
        traits=["traits<Expansion<T, 2>>::add_limb"],
    ),
    "sub_2_2": page(
        "arithmetic", "Difference of two two-limb numbers",
        form("x - y", E2, E2, result=E2),
        form("x -= y", E2, E2, result=E2),
        form("x - y", E2, E1, result=E2, note=WIDENED),
        form("x - y", E1, E2, result=E2, note=WIDENED),
        traits=["traits<Expansion<T, 2>>::sub"],
    ),
    "sub_2_1": page(
        "arithmetic", "A two-limb number minus a limb",
        form("x - a", E2, T, result=E2),
        form("x -= a", E2, T, result=E2),
        traits=["traits<Expansion<T, 2>>::sub_limb"],
    ),
    "sub_1_2": page(
        "arithmetic", "A limb minus a two-limb number",
        form("a - y", T, E2, result=E2),
        traits=["traits<Expansion<T, 2>>::sub_limb"],
    ),
    "mul_2_2": page(
        "arithmetic", "Product of two two-limb numbers",
        form("x * y", E2, E2, result=E2),
        form("x *= y", E2, E2, result=E2),
        form("x * y", E2, E1, result=E2, note=WIDENED),
        form("x * y", E1, E2, result=E2, note=WIDENED),
        traits=["traits<Expansion<T, 2>>::mul"],
    ),
    "mul_2_1": page(
        "arithmetic", "Product of a two-limb number and a limb",
        form("x * a", E2, T, result=E2),
        form("a * x", T, E2, result=E2),
        form("x *= a", E2, T, result=E2),
        traits=["traits<Expansion<T, 2>>::mul_limb"],
    ),
    "add_fast_2_2": page(
        "arithmetic", "Fast sum of two two-limb numbers",
        form("add_fast(x, y)", E2, E2, result=E2),
        traits=["traits<Expansion<T, 2>>::add_fast"],
    ),
    "neg_2": page(
        "arithmetic", "Negation, two limbs",
        form("-x", E2, result=E2),
    ),
    "abs_2": page(
        "arithmetic", "Absolute value, two limbs",
        form("abs(x)", E2, result=E2),
    ),
    # --- Two limbs: comparisons ----------------------------------------------------------------
    "lt_2_2": page(
        "comparisons", "Less than, two two-limb numbers",
        form("x < y", E2, E2, result="bool"),
        form("y > x", E2, E2, result="bool"),
        form("x < y", E2, E1, result="bool", note=WIDENED),
        form("x < y", E1, E2, result="bool", note=WIDENED),
    ),
    "le_2_2": page(
        "comparisons", "At most, two two-limb numbers",
        form("x <= y", E2, E2, result="bool"),
        form("y >= x", E2, E2, result="bool"),
        form("x <= y", E2, E1, result="bool", note=WIDENED),
        form("x <= y", E1, E2, result="bool", note=WIDENED),
    ),
    "eq_2_2": page(
        "comparisons", "Equality, two two-limb numbers",
        form("x == y", E2, E2, result="bool"),
        form("x != y", E2, E2, result="bool", note="the negation of `x == y`"),
        form("x == y", E2, E1, result="bool", note=WIDENED),
        form("x == y", E1, E2, result="bool", note=WIDENED),
    ),
    "lt_2_1": page(
        "comparisons", "A two-limb number less than a limb",
        form("x < a", E2, T, result="bool"),
        form("a > x", T, E2, result="bool"),
    ),
    "le_2_1": page(
        "comparisons", "A two-limb number at most a limb",
        form("x <= a", E2, T, result="bool"),
        form("a >= x", T, E2, result="bool"),
    ),
    "eq_2_1": page(
        "comparisons", "A two-limb number equal to a limb",
        form("x == a", E2, T, result="bool"),
        form("a == x", T, E2, result="bool"),
        form("x != a", E2, T, result="bool", note="the negation of `x == a`"),
        form("a != x", T, E2, result="bool", note="the negation of `a == x`"),
    ),
    "lt_1_2": page(
        "comparisons", "A limb less than a two-limb number",
        form("a < y", T, E2, result="bool"),
        form("y > a", E2, T, result="bool"),
    ),
    "le_1_2": page(
        "comparisons", "A limb at most a two-limb number",
        form("a <= y", T, E2, result="bool"),
        form("y >= a", E2, T, result="bool"),
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
    "mul_pow2_2": page(
        "scaling", "Scaling a two-limb number by a power of two",
        form("ldexp(x, n)", E2, "int", result=E2,
             note="$c = 2^n$, for an `n` with $2^n$ a number of `T`; otherwise $c$ is NaN and nothing is claimed"),
        form("half(x)", E2, result=E2, note="$c = 1/2$"),
        traits=["traits<Expansion<T, 2>>::ldexp"],
    ),
    # --- Balls ---------------------------------------------------------------------------------
    "ball_add_1": page(
        "ball", "Sum of balls, one-limb center",
        form("X + Y", B1, B1, result=B1),
        form("X += Y", B1, B1, result=B1),
        form("X + y", B1, E1, result=B1, note=POINT),
        form("X + a", B1, T, result=B1, note=POINT),
        form("a + X", T, B1, result=B1, note=POINT),
    ),
    "ball_add_2": page(
        "ball", "Sum of balls, two-limb center",
        form("X + Y", B2, B2, result=B2),
        form("X += Y", B2, B2, result=B2),
        form("X + y", B2, E2, result=B2, note=POINT),
        form("X + a", B2, T, result=B2, note=POINT),
        form("a + X", T, B2, result=B2, note=POINT),
    ),
    "ball_sub_1": page(
        "ball", "Difference of balls, one-limb center",
        form("X - Y", B1, B1, result=B1),
        form("X -= Y", B1, B1, result=B1),
        form("X - y", B1, E1, result=B1, note=POINT),
        form("X - a", B1, T, result=B1, note=POINT),
        form("a - X", T, B1, result=B1, note=POINT),
    ),
    "ball_sub_2": page(
        "ball", "Difference of balls, two-limb center",
        form("X - Y", B2, B2, result=B2),
        form("X -= Y", B2, B2, result=B2),
        form("X - y", B2, E2, result=B2, note=POINT),
        form("X - a", B2, T, result=B2, note=POINT),
        form("a - X", T, B2, result=B2, note=POINT),
    ),
    "ball_mul_1": page(
        "ball", "Product of balls, one-limb center",
        form("X * Y", B1, B1, result=B1),
        form("X *= Y", B1, B1, result=B1),
        form("X * y", B1, E1, result=B1, note=POINT),
    ),
    "ball_mul_2": page(
        "ball", "Product of balls, two-limb center",
        form("X * Y", B2, B2, result=B2),
        form("X *= Y", B2, B2, result=B2),
        form("X * y", B2, E2, result=B2, note=POINT),
    ),
    "ball_scale_1": page(
        "ball", "A ball times a limb, one-limb center",
        form("X * a", B1, T, result=B1),
        form("a * X", T, B1, result=B1),
        form("X *= a", B1, T, result=B1),
    ),
    "ball_scale_2": page(
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
    # --- Building blocks: no public form -------------------------------------------------------
    "two_sum": page("building-blocks", "TwoSum: an exact sum as two limbs"),
    "fast_two_sum": page("building-blocks", "Fast2Sum: an exact sum of ordered operands"),
    "two_prod": page("building-blocks", "TwoProd: an exact product as two limbs"),
    "two_prod_dekker": page("building-blocks", "Dekker's product: TwoProd without an FMA"),
    "split": page("building-blocks", "Veltkamp's split"),
    "radd": page("building-blocks", "An upper bound of a sum, for radii"),
    "rmul": page("building-blocks", "An upper bound of a product, for radii"),
}


def exact(group, does, *forms):
    return {"group": group, "does": does, "forms": list(forms)}


# Operations that call no kernel. `does` is what the header comment says the operation does.
CANONICAL = ("the value $a$ exactly: $(a, 0)$, with a $-0$ made $+0$; for an infinite or NaN $a$, "
             "$(\\pm\\infty, 0)$ or $(\\mathrm{NaN}, \\mathrm{NaN})$")

EXACT = [
    exact("construction", "zero",
          form("Expansion<T, K>()", result="Expansion<T, K>")),
    exact("construction", CANONICAL,
          form("Expansion<T, 2>(a)", T, result=E2)),
    exact("construction", CANONICAL + ", where $a$ is the limb of the one-limb number",
          form("Expansion<T, 2>(a)", E1, result=E2)),
    exact("construction", "the value $a$",
          form("Expansion<T, 1>(a)", T, result=E1)),
    exact("construction", "the number with these limbs, which must form a normalized number; "
          "checked when `KAIRN_CHECKS` is 1",
          form("Expansion<T, K>::from_limbs(p)", "const T*", result="Expansion<T, K>")),
    exact("construction", "the same without the check: limbs that do not form a normalized number "
          "give results without any guarantee",
          form("Expansion<T, K>::from_limbs_unchecked(p)", "const T*", result="Expansion<T, K>")),
    exact("construction", "the limbs, most significant first; a limb written directly must not be "
          "a product the compiler can see",
          form("x.limb[i]", "Expansion<T, K>", result="T")),
    exact("construction", "the point 0: center 0, radius 0",
          form("Ball<T, K>()", result="Ball<T, K>")),
    exact("construction", "the point $a$: center $a$, radius 0",
          form("Ball<T, K>(a)", T, result="Ball<T, K>")),
    exact("construction", "the point $c$: center $c$, radius 0",
          form("Ball<T, K>(c)", "Expansion<T, K>", result="Ball<T, K>")),
    exact("construction", "the ball of center $c$ and radius $r$; requires a normalized $c$ and "
          "$r \\ge 0$, checked when `KAIRN_CHECKS` is 1",
          form("Ball<T, K>(c, r)", "Expansion<T, K>", T, result="Ball<T, K>")),
    exact("construction", "the center",
          form("X.center()", "Ball<T, K>", result="Expansion<T, K>")),
    exact("construction", "the radius",
          form("X.radius()", "Ball<T, K>", result="T")),
    exact("construction", "$-1$, $0$ or $+1$, from the leading limb; $0$ for NaN",
          form("sign(x)", "Expansion<T, K>", result="int")),
    exact("construction", "whether the leading limb is finite",
          form("isfinite(x)", "Expansion<T, K>", result="bool")),
    exact("construction", "whether every limb is finite and, for two limbs, $x_0 + x_1$ rounds to $x_0$",
          form("is_normalized(x)", "Expansion<T, K>", result="bool")),
    exact("arithmetic", "the IEEE 754 operation of `T`: exact",
          form("-x", E1, result=E1),
          form("abs(x)", E1, result=E1)),
    exact("comparisons", "the comparison of `T`: exact; false if an operand is NaN (true for `!=`)",
          form("x < y, x > y, x <= y, x >= y, x == y, x != y", E1, E1, result="bool")),
    exact("conversions", "$x$ itself, or $\\lvert x\\rvert$ for `abs_upper`",
          form("to_nearest(x), to_down(x), to_up(x), abs_upper(x)", E1, result=T)),
]
