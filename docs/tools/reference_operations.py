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
  (`entry: yes` in its description: today the finite cores of the Ball operations, and the
  steps of the folds over arrays that the program fills) that the public headers do not call
  yet; its page and the index say which. Give it forms only when a
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
I1 = "Interval<T, 1>"
I2 = "Interval<T, 2>"
T = "T"
P1 = "Packed<T, 1>"
P2 = "Packed<T, 2>"
PK = "Packed<T, K>"
# The views of the functions on arrays (kairn/batch.hpp): read, and written; and their results.
V1 = "SoAView<const T, 1>"
V2 = "SoAView<const T, 2>"
W1 = "SoAView<T, 1>"
W2 = "SoAView<T, 2>"
R1 = "Reduction<Expansion<T, 1>>"
R2 = "Reduction<Expansion<T, 2>>"
SEQ = "Sequential"
A1 = "Accumulator<T, 1>"
A2 = "Accumulator<T, 2>"
# The accumulator (kairn/accumulator.hpp): what each operation does to its state.
ACC = "one more term; the bound of the whole history is `A.error_bound()` ([Accumulator](accumulator.md))"

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
     "and the interface a ball shares with an interval ([One enclosure interface](enclosure.md)): its bounds, the "
     "member and subset tests, the signs, the three-valued comparisons, the hull, the intersection, the split and "
     "the conversions. Of one limb the predicates are exact, and the comparisons exact when the sum of the radii "
     "is at most the largest finite number of `T`; of two they are certain but the signs, which are exact."),
    ("intervals", "Interval operations",
     "`Interval<T, k>` (`kairn/interval.hpp`): its constructors, the arithmetic of intervals of numbers of `T` and "
     "of two limbs, whose result contains every result on members of the operands, unbounded and empty intervals "
     "included, the hull, the intersection, the midpoint, the radius and the split, the conversions between an "
     "interval and a ball, and the predicates, the three-valued comparisons and the relations of IEEE 1788 "
     "([One enclosure interface](enclosure.md)), each exact. The arithmetic is not `constexpr` (its code is where "
     "`KAIRN_ENCLOSURE_CODE` puts it), nor the midpoint, the radius and the conversions of two limbs; the rest is, "
     "and of it only the midpoint, the radius, the split and the conversions round."),
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
     "The kernels of the loops over arrays (the folds of Milestone 2) that `kairn/batch.hpp` calls: the steps "
     "of the sums and dot products, the finish of their result, the kernels of `norm_upper`, and the bounds of "
     "a sum and of a dot product as a function of the number of terms, and the kernels of the accumulator "
     "(`kairn/accumulator.hpp`). Each function on arrays calls a loop made of these, whose claims are those of "
     "the whole array ([Functions on arrays](batch.md)); a step's page states what one step claims; what is "
     "proved of an accumulator's history is on [The accumulator](accumulator.md). The operations of a ball "
     "vector ([Ball vectors](ball_vector.md)) call the steps of the dot products, their bound and the finishes "
     "in the product of polynomials, and the folds of maxima in every loop."),
    ("packed", "Vector loops: Packed and the containers",
     "`Packed<T, k>` (`kairn/packed.hpp`) holds W numbers in registers; its operations are those of `Expansion` "
     "that have a kernel, under the same names, each the packed form of that kernel, with its statement in every "
     "lane ([Packed numbers in registers](packed.md)). `SoA<T, k>` and its views (`kairn/soa.hpp`) hold numbers as "
     "one array per limb and compute nothing ([Arrays of numbers](soa.md)). `kairn/kairn.hpp` includes neither."),
    ("maps", "Operations on arrays, entry by entry",
     "The steps of the maps of Milestone 2 (z = x + y, x - y, a x + y, x a, x c entry by entry): each is the "
     "operation of one entry, on an array the program supplies where it says so, and every element a map of "
     "`kairn/batch.hpp` writes satisfies its claims ([Functions on arrays](batch.md)). The steps of the maps on "
     "stored arrays have no caller there. The operations of a ball vector call the difference of one limb and "
     "the steps of the scaling."),
    ("ball-vectors", "Ball vectors: N centers and one radius",
     "`BallVector<T, k, N>` and `BallVectorView<T, k>` (`kairn/ball_vector.hpp`, "
     "[Ball vectors](ball_vector.md)): each operation is one generated loop over the arrays of the centers, "
     "and the kernels here are parts of those loops: the radius of the result, from the largest magnitude "
     "of a center (the radius lines of the entrywise Ball operation), the guards and the finish of the "
     "constructor, the scaling by a power of two with its mask of exactness, the radius of the product of "
     "polynomials. `kairn/kairn.hpp` does not include the header."),
]

# The loops over arrays (the folds of gen/claims.json) that public operations call, each with those
# operations. The kernels a loop's description names (gen/kernels/LOOP.fold: its step, records,
# combinations, radius, bound, finish or check, and those of the folds it names as its centers or
# coefficients) are parts of it: their pages say which loop, and which operations call it, in place
# of "not yet called". tests/api/coverage.cmake checks the same loops against the runner of the
# public interface.
BV_OPS = "of `BallVector<T, %s, N>` and `BallVectorView<T, %s>` ([Ball vectors](ball_vector.md))"
LOOPS = {
    "bv_make_1": "the constructors " + BV_OPS % (1, 1),
    "bv_make_2_entry": "the constructors " + BV_OPS % (2, 2),
    "bv_neg_1": "`-x` and `neg(x, z)` " + BV_OPS % (1, 1),
    "bv_neg_2": "`-x` and `neg(x, z)` " + BV_OPS % (2, 2),
    "bv_add_1": "`x + y`, `x += y`, `add(x, y, z)` and `axpy` " + BV_OPS % (1, 1),
    "bv_add_2": "`x + y`, `x += y`, `add(x, y, z)` and `axpy` " + BV_OPS % (2, 2),
    "bv_sub_1": "`x - y`, `x -= y` and `sub(x, y, z)` " + BV_OPS % (1, 1),
    "bv_sub_2": "`x - y`, `x -= y` and `sub(x, y, z)` " + BV_OPS % (2, 2),
    "bv_scale_1": "`x * a`, `a * x`, `x *= a`, `scale(x, a, z)` and `axpy` " + BV_OPS % (1, 1),
    "bv_scale_2_entry": "`x * a`, `a * x`, `x *= a`, `scale(x, a, z)` and `axpy` " + BV_OPS % (2, 2),
    "bv_mul_pow2_1": "`ldexp` and `half` " + BV_OPS % (1, 1),
    "bv_mul_pow2_2": "`ldexp` and `half` " + BV_OPS % (2, 2),
    "bv_conv_1": "`convolution`, the product of polynomials, " + BV_OPS % (1, 1),
    "bv_conv_2": "`convolution`, the product of polynomials, " + BV_OPS % (2, 2),
    "norm_upper_1": "`norm_upper` of `SoAView<const T, 1>` ([Functions on arrays](batch.md)) and " + BV_OPS % (1, 1),
    "norm_upper_2": "`norm_upper` of `SoAView<const T, 2>` ([Functions on arrays](batch.md)) and " + BV_OPS % (2, 2),
}


def form(code, *operands, result, group=None, note=None):
    """One C++ form: the code, the type of each operand, the type of the result."""
    return {"code": code, "operands": list(operands), "result": result, "group": group, "note": note}


def page(group, title, *forms, traits=(), note=None):
    return {"group": group, "title": title, "forms": list(forms), "traits": list(traits), "note": note}


ONE = "the limb of the `Expansion<T, 1>` operand is the limb $a$"
# The functions on arrays reach the step of their loop for every element: the page of the step says
# what each step claims; the function's claims, those of its loop, are on [Functions on
# arrays](batch.md).
STEP = "the step of the loop the function calls, once per element; not `constexpr`; rounds"
STEP_ORDER = STEP + "; in the lane order of the build, or, with `kairn::sequential`, in the sequential order"
# The notes of the building blocks on T: whether constant evaluation has them, with what, and that
# they round.
SAME_BITS = "`constexpr`, with the same bits in constant evaluation; rounds"
SAME_VALUES = ("`constexpr`, with the same values in constant evaluation (a zero result can differ in sign); "
               "rounds")
GUARDED = "; the operands are guarded ([rule R3](../developer/architecture.md#the-kernel-ir))"
CONVERTED = "the limb is converted to `Expansion<T, 1>` first, exactly"
POINT = "the point is the ball of radius 0 its constructor makes"
# The notes of the interval operations: whether constant evaluation has them, and whether they round.
NOT_CONSTEXPR_INTERVAL = "rounds; not `constexpr`: its code is where `KAIRN_ENCLOSURE_CODE` puts it"
EXACT_INTERVAL = "`constexpr`; does not round"
ROUNDS_CONSTEXPR = "`constexpr`; rounds, and is preceded by the debug build's check of the rounding mode"
TO_TWO_LIMBS = "each value of `T` converted to `Expansion<T, 2>` first, exactly (`make_2`)"
CORE = "the finite core: no fix-up of infinities and NaN"
# The scaling of a two-limb number by a power of two in constant evaluation: its kernels compute only
# opaque products, which constant evaluation computes as plain products with the same values.
SCALING_CONSTEXPR = ("`constexpr`, the steps included, with the same values in constant evaluation "
                     "([the rule of the product](../developer/architecture.md#the-kernel-ir)); rounds")
# The constructors of an interval and of a ball from their limbs, which pass each limb through the
# guard of make_2 or make_2_limbs ([One enclosure interface](enclosure.md#limbs)).
FROM_LIMBS = ("`%s::from_limbs(p)`, `p` pointing to the limbs as they were read (the bounds' or the center's, "
              "then the radius); the limbs of a canonical set, checked when `KAIRN_CHECKS` is 1; the round trip "
              "gives every limb back but the sign of a zero and the payload of a NaN "
              "([One enclosure interface](enclosure.md#limbs))")
# The constructors from two bounds that an interval and a ball share by name (Interval(a, b) is
# [a, b], Ball(a, b) the ball of center a and radius b: from_bounds is the one spelling of both).
FROM_BOUNDS_INTERVAL = ("`Interval<T, %s>::from_bounds(lo, hi)`, the same set as `Interval(lo, hi)`, under the name "
                        "`Ball` has too ([One enclosure interface](enclosure.md#the-interface))")
FROM_BOUNDS_BALL = ("`Ball<T, %s>::from_bounds(lo, hi)`, the same ball as `from_interval(lo, hi)`, under the name "
                    "`Interval` has too ([One enclosure interface](enclosure.md#the-interface)); the bounds are "
                    "guarded ([rule R3](../developer/architecture.md#the-kernel-ir))")
# The notes of the enclosure interface of stage B2 ([One enclosure interface](enclosure.md)).
ROUNDS = "rounds, and is preceded by the debug build's check of the rounding mode; not `constexpr`"
WHOLE = "IEEE 1788 calls it `isEntire`; the name is `Ball`'s"
MEMBER_EXACT = "as a `Trit`: yes or no, never unknown"
OPPOSITE = "the answer of `equal(X, Y)` with yes and no exchanged"
POINT_TWO = ("the point made a number of two limbs by `make_2` first, exactly: a composition of two proved "
             "kernels, not machine-checked as one statement")
MIDRAD_TWICE = "computes the whole kernel, as the other does: `X.mid_rad()` gives both from one call"
SPLIT_POINT = "they meet at a point of $X$, which is not claimed to be the midpoint"
HULL_NOTE = "contains both, not claimed the smallest; with an empty operand, the other as it is"
INTERSECTION_NOTE = ("contains the common members, not claimed the smallest nor inside either; with the whole line "
                     "as an operand, the other as it is")
BALL_SPLIT = "covers $[c - r, c]$ and $[c, c + r]$; the parts are not claimed inside $X$, nor smaller than $X$"
# The products that guard their operands, which are factors of a fused operation (rule R3).
FACTORS = "; the operands are guarded, as factors of a fused operation ([rule R3](../developer/architecture.md#the-kernel-ir))"
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
        form("from_limbs(p)", "T*", result=I1, note=FROM_LIMBS % "Interval<T, 1>" + "; each bound through `make_2`, "
             "of which the leading limb is kept, the bound itself; `constexpr`; checks the rounding mode "
             "for one limb and for two"),
        form("from_limbs(p)", "T*", result="Ball<T, K>", note=FROM_LIMBS % "Ball<T, K>" + "; the radius, and a center "
             "of one limb, through `make_2`, of which the leading limb is kept, the value itself; `constexpr`; checks "
             "the rounding mode for one limb and for two"),
    ),
    "make_2_limbs": page(
        "construction", "A two-limb number from its limbs",
        form("from_limbs(p)", "T*", result=E2,
             note="`Expansion<T, 2>::from_limbs(p)`, with `p` pointing to the two limbs; checked when "
                  "`KAIRN_CHECKS` is 1"),
        form("from_limbs_unchecked(p)", "T*", result=E2, note="the same, never checked"),
        form("from_limbs(p)", "T*", result=I2, note=FROM_LIMBS % "Interval<T, 2>" + "; each bound through "
             "`make_2_limbs`; `constexpr`; rounds (the test of a canonical bound), and is preceded by the debug "
             "build's check of the rounding mode"),
        form("from_limbs(p)", "T*", result=B2, note=FROM_LIMBS % "Ball<T, 2>" + "; the center through `make_2_limbs`, "
             "the radius through `make_2`; `constexpr`; rounds (the test of a canonical center), and is preceded by "
             "the debug build's check of the rounding mode"),
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
    "mul_2_1_full_entry": page(
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
    "mul_2_1_entry": page(
        "finite", "Product of a two-limb number and a limb, finite core",
        form("finite::mul(x, a)", E2, T, result=E2, note=CORE + FACTORS),
        form("finite::mul(a, x)", T, E2, result=E2),
        form("finite::mul(x, y)", E2, E1, result=E2, note=ONE),
        form("finite::mul(y, x)", E1, E2, result=E2, note=ONE),
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
                         "as for `ldexp`, whose composition is " + COMPOSITION + "; " + SCALING_CONSTEXPR),
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
    ),
    "lt_1_2": page(
        "comparisons", "A limb less than a two-limb number",
        form("a < y", T, E2, result="bool"),
        form("y > a", E2, T, result="bool"),
        form("x < y", E1, E2, result="bool", note="the limb of the `Expansion<T, 1>` operand is the limb $a$"),
        form("y > x", E2, E1, result="bool", note="the limb of the `Expansion<T, 1>` operand is the limb $a$"),
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
        form("X.lower_as<T>()", I2, result=T, group="intervals",
             note="the lower bound of an interval of two limbs, rounded down: $x$ is the bound; " + EXACT_INTERVAL),
    ),
    "to_up_2": page(
        "conversions", "Rounding up",
        form("to_up(x)", E2, result=T),
        form("X.upper_as<T>()", I2, result=T, group="intervals",
             note="the upper bound of an interval of two limbs, rounded up: $x$ is the bound; " + EXACT_INTERVAL),
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
                  "whose composition is " + COMPOSITION + "; " + SCALING_CONSTEXPR),
        form("half(x)", E2, result=E2, note="$c = 1/2$; " + SCALING_CONSTEXPR),
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
    "ball_scale_2_full_entry": page(
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
    "ball_scale_2_full": page("building-blocks", "A ball times a limb, two-limb center, its factor unguarded"),
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
    "two_prod_entry": page(
        "blocks", "TwoProd on values of the program",
        form("two_prod(a, b)", T, T, result="ProductAndError<T>",
             note="`constexpr`, through Dekker's product ([`two_prod_dekker`](two_prod_dekker.md)) in constant "
                  "evaluation; not a constant expression on finite operands on which an operation of Dekker's "
                  "product overflows (a program that needs one does not compile; the message names "
                  "`two_prod_overflows_in_constant_evaluation`, or with GCC the operation): it is one when "
                  "$\\lvert a\\rvert, \\lvert b\\rvert \\le 2^{996}$ and $\\lvert ab\\rvert \\le 2^{1023}$ "
                  "($2^{115}$ and $2^{127}$ for `float`), a sufficient condition, not an exact one; where it is "
                  "one, the same values when the product is exact, each its own error term below the threshold; "
                  "rounds; `r.product` is $p$ and `r.error` is $e$" + FACTORS),
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
    "mul_down_entry": page(
        "blocks", "A lower bound of a product of two limbs, on values of the program",
        form("mul_down(a, b)", T, T, result=T,
             note="not `constexpr`: its statement is about the fused product, which constant evaluation does not "
                  "have ([Building blocks on T](../developer/design/milestone2.md#building-blocks-on-t)); rounds"
                  + FACTORS),
    ),
    "mul_up_entry": page(
        "blocks", "An upper bound of a product of two limbs, on values of the program",
        form("mul_up(a, b)", T, T, result=T,
             note="not `constexpr`: its statement is about the fused product, which constant evaluation does not "
                  "have ([Building blocks on T](../developer/design/milestone2.md#building-blocks-on-t)); rounds"
                  + FACTORS),
    ),
    # --- Milestone 2, wave 2: the interval kernels (kairn/interval.hpp) --------------------------
    "interval_make_1": page(
        "intervals", "An interval from two limbs",
        form("Interval<T, 1>(lo, hi)", E1, E1, result=I1, note="implicit for one operand; " + EXACT_INTERVAL),
        form("Interval<T, 1>(lo, hi)", T, T, result=I1,
             note="each limb converted to `Expansion<T, 1>` first, exactly; " + EXACT_INTERVAL),
        form("Interval<T, 1>(a)", T, result=I1, note="implicit; $l_o = h_i = a$; " + EXACT_INTERVAL),
        form("Interval<T, 1>(a)", E1, result=I1, note="implicit; $l_o = h_i = a$; " + EXACT_INTERVAL),
        form("from_bounds(lo, hi)", T, T, result=I1, note=FROM_BOUNDS_INTERVAL % "1" + "; " + EXACT_INTERVAL),
        form("from_bounds(lo, hi)", E1, E1, result=I1, note=FROM_BOUNDS_INTERVAL % "1" + "; " + EXACT_INTERVAL),
    ),
    "interval_neg_1": page(
        "intervals", "The negation of an interval, one-limb bounds",
        form("-X", I1, result=I1, note=EXACT_INTERVAL),
    ),
    "interval_add_1": page(
        "intervals", "Sum of intervals, one-limb bounds",
        form("X + Y", I1, I1, result=I1, note=NOT_CONSTEXPR_INTERVAL),
        form("X += Y", I1, I1, result=I1, note=NOT_CONSTEXPR_INTERVAL),
    ),
    "interval_sub_1": page(
        "intervals", "Difference of intervals, one-limb bounds",
        form("X - Y", I1, I1, result=I1, note=NOT_CONSTEXPR_INTERVAL),
        form("X -= Y", I1, I1, result=I1, note=NOT_CONSTEXPR_INTERVAL),
    ),
    "interval_mul_1": page(
        "intervals", "Product of intervals, one-limb bounds",
        form("X * Y", I1, I1, result=I1, note=NOT_CONSTEXPR_INTERVAL),
        form("X *= Y", I1, I1, result=I1, note=NOT_CONSTEXPR_INTERVAL),
    ),
    "interval_add_2": page(
        "intervals", "Sum of intervals, two-limb bounds",
        form("X + Y", I2, I2, result=I2, note=NOT_CONSTEXPR_INTERVAL),
        form("X += Y", I2, I2, result=I2, note=NOT_CONSTEXPR_INTERVAL),
    ),
    "ball_lower_as_1": page(
        "ball", "The lower bound of a ball as a limb, one-limb center",
        form("X.lower_as<T>()", B1, result=T, note=ROUNDS_CONSTEXPR),
        form("X.lower()", B1, result=E1, note="the same value as a one-limb number; " + ROUNDS_CONSTEXPR),
    ),
    "ball_upper_as_1": page(
        "ball", "The upper bound of a ball as a limb, one-limb center",
        form("X.upper_as<T>()", B1, result=T, note=ROUNDS_CONSTEXPR),
        form("X.upper()", B1, result=E1, note="the same value as a one-limb number; " + ROUNDS_CONSTEXPR),
    ),
    "ball_lower_as_2": page(
        "ball", "A lower bound of a ball as a limb, two-limb center",
        form("X.lower_as<T>()", B2, result=T, note=ROUNDS_CONSTEXPR),
    ),
    "ball_upper_as_2": page(
        "ball", "An upper bound of a ball as a limb, two-limb center",
        form("X.upper_as<T>()", B2, result=T, note=ROUNDS_CONSTEXPR),
    ),
    "ball_from_interval_2": page(
        "ball", "A ball with a two-limb center from an interval given as two values of T",
        form("from_interval(lo, hi)", T, T, result=B2,
             note="`Ball<T, 2>::from_interval(lo, hi)`; the bounds are guarded "
                  "([rule R3](../developer/architecture.md#the-kernel-ir)); " + ROUNDS_CONSTEXPR),
        form("from_bounds(lo, hi)", T, T, result=B2, note=FROM_BOUNDS_BALL % "2" + "; " + ROUNDS_CONSTEXPR),
    ),
    "ball_narrow_2_1": page(
        "ball", "A ball with a two-limb center as one with a one-limb center",
        form("Ball<T, 1>(X)", B2, result=B1, note="explicit; " + ROUNDS_CONSTEXPR),
    ),
    # Stage B1: the interval kernels of two limbs, and the set operations, conversions and split of
    # the enclosure interface.
    "interval_neg_2": page(
        "intervals", "The negation of an interval, two-limb bounds",
        form("-X", I2, result=I2, note=EXACT_INTERVAL),
    ),
    "interval_sub_2": page(
        "intervals", "Difference of intervals, two-limb bounds",
        form("X - Y", I2, I2, result=I2, note=NOT_CONSTEXPR_INTERVAL),
        form("X -= Y", I2, I2, result=I2, note=NOT_CONSTEXPR_INTERVAL),
    ),
    "interval_make_2": page(
        "intervals", "An interval from two two-limb numbers",
        form("Interval<T, 2>(lo, hi)", E2, E2, result=I2, note="implicit for one operand; " + EXACT_INTERVAL),
        form("Interval<T, 2>(lo, hi)", T, T, result=I2, note=TO_TWO_LIMBS + "; " + EXACT_INTERVAL),
        form("Interval<T, 2>(a)", T, result=I2, note="implicit; $l_o = h_i = a$, " + TO_TWO_LIMBS + "; " + EXACT_INTERVAL),
        form("Interval<T, 2>(a)", E2, result=I2, note="implicit; $l_o = h_i = a$; " + EXACT_INTERVAL),
        form("from_bounds(lo, hi)", E2, E2, result=I2, note=FROM_BOUNDS_INTERVAL % "2" + "; " + EXACT_INTERVAL),
        form("from_bounds(lo, hi)", T, T, result=I2,
             note=FROM_BOUNDS_INTERVAL % "2" + "; " + TO_TWO_LIMBS + "; " + EXACT_INTERVAL),
    ),
    "interval_mul_2": page(
        "intervals", "Product of intervals, two-limb bounds",
        form("X * Y", I2, I2, result=I2,
             note=NOT_CONSTEXPR_INTERVAL + "; the kernel is an ordinary inline function in every setting, which the "
                  "compiler may call rather than inline"),
        form("X *= Y", I2, I2, result=I2, note=NOT_CONSTEXPR_INTERVAL),
    ),
    "interval_hull_1": page(
        "intervals", "The hull of two intervals, one-limb bounds",
        form("X.hull(Y)", I1, I1, result=I1, note=EXACT_INTERVAL),
    ),
    "interval_intersection_1": page(
        "intervals", "The intersection of two intervals, one-limb bounds",
        form("X.intersection(Y)", I1, I1, result=I1, note=EXACT_INTERVAL),
    ),
    "interval_hull_2": page(
        "intervals", "The hull of two intervals, two-limb bounds",
        form("X.hull(Y)", I2, I2, result=I2, note=EXACT_INTERVAL),
    ),
    "interval_intersection_2": page(
        "intervals", "The intersection of two intervals, two-limb bounds",
        form("X.intersection(Y)", I2, I2, result=I2, note=EXACT_INTERVAL),
    ),
    "interval_mid_rad_1": page(
        "intervals", "The midpoint and radius of an interval, one-limb bounds",
        form("X.midpoint()", I1, result=E1, note="$m$; " + MIDRAD_TWICE + "; " + ROUNDS_CONSTEXPR),
        form("X.radius()", I1, result=T, note="$r$; " + MIDRAD_TWICE + "; " + ROUNDS_CONSTEXPR),
        form("X.mid_rad()", I1, result="MidRad<T, 1>", note="$m$ and $r$ from one call; " + ROUNDS_CONSTEXPR),
    ),
    "interval_to_ball_1": page(
        "intervals", "A ball that contains an interval, one-limb bounds",
        form("Ball<T, 1>(X)", I1, result=B1, note="explicit; " + ROUNDS_CONSTEXPR),
    ),
    "interval_split_1": page(
        "intervals", "An interval split at its midpoint, one-limb bounds",
        form("X.split()", I1, result="Split<Interval<T, 1>>",
             note="`left` is $[a_l, a_u]$ and `right` is $[b_l, b_u]$; " + SPLIT_POINT + "; " + ROUNDS_CONSTEXPR),
    ),
    "ball_to_interval_1": page(
        "ball", "The smallest interval that contains a ball, one-limb center",
        form("Interval<T, 1>(X)", B1, result=I1, group="intervals", note="explicit; " + ROUNDS_CONSTEXPR),
    ),
    # Stage B2: the predicates, the three-valued comparisons and the relations of IEEE 1788 of an
    # interval (subset is interval_subset_k), public since the enclosure interface was completed in
    # kairn/interval.hpp and kairn/ball.hpp ([One enclosure interface](enclosure.md)).
    "interval_empty_1": page("intervals", "Whether an interval is empty, one-limb bounds",
                             form("X.is_empty()", I1, result="bool", note=EXACT_INTERVAL)),
    "interval_entire_1": page("intervals", "Whether an interval is the whole line, one-limb bounds",
                              form("X.is_whole()", I1, result="bool", note=WHOLE + "; " + EXACT_INTERVAL)),
    "interval_contains_1": page(
        "intervals", "Whether a point is a member of an interval, one-limb bounds",
        form("X.contains(t)", I1, T, result="bool", note=EXACT_INTERVAL),
        form("X.contains(t)", I1, E1, result="bool", note=EXACT_INTERVAL),
        form("member(t, X)", T, I1, result="Trit", note=MEMBER_EXACT + "; " + EXACT_INTERVAL),
        form("member(t, X)", E1, I1, result="Trit", note=MEMBER_EXACT + "; " + EXACT_INTERVAL)),
    "interval_subset_1": page(
        "intervals", "Whether an interval is a subset of another, one-limb bounds",
        form("Y.contains(X)", I1, I1, result="bool", note="whether $Y \\supseteq X$; " + EXACT_INTERVAL),
        form("ieee1788::subset(X, Y)", I1, I1, result="bool", note="the relation subset of IEEE 1788; " + EXACT_INTERVAL)),
    "interval_positive_1": page("intervals", "Whether every member of an interval is positive, one-limb bounds",
                                form("X.certainly_positive()", I1, result="bool", note=EXACT_INTERVAL)),
    "interval_negative_1": page("intervals", "Whether every member of an interval is negative, one-limb bounds",
                                form("X.certainly_negative()", I1, result="bool", note=EXACT_INTERVAL)),
    "interval_zero_1": page("intervals", "Whether an interval is [0, 0], one-limb bounds",
                            form("X.certainly_zero()", I1, result="bool", note=EXACT_INTERVAL)),
    "interval_less_1": page(
        "intervals", "The three-valued X < Y of intervals, one-limb bounds",
        form("less(X, Y)", I1, I1, result="Trit", note=EXACT_INTERVAL),
        form("greater(Y, X)", I1, I1, result="Trit", note="the operands exchanged; " + EXACT_INTERVAL)),
    "interval_less_equal_1": page(
        "intervals", "The three-valued X <= Y of intervals, one-limb bounds",
        form("less_equal(X, Y)", I1, I1, result="Trit", note=EXACT_INTERVAL),
        form("greater_equal(Y, X)", I1, I1, result="Trit", note="the operands exchanged; " + EXACT_INTERVAL)),
    "interval_equal_1": page(
        "intervals", "The three-valued X = Y of intervals, one-limb bounds",
        form("equal(X, Y)", I1, I1, result="Trit", note=EXACT_INTERVAL),
        form("not_equal(X, Y)", I1, I1, result="Trit", note=OPPOSITE + "; " + EXACT_INTERVAL)),
    "interval_rel_equal_1": page("intervals", "The relation equal of IEEE 1788, one-limb bounds",
                                 form("ieee1788::equal(X, Y)", I1, I1, result="bool", note=EXACT_INTERVAL)),
    "interval_rel_interior_1": page("intervals", "The relation interior of IEEE 1788, one-limb bounds",
                                    form("ieee1788::interior(X, Y)", I1, I1, result="bool", note=EXACT_INTERVAL)),
    "interval_rel_disjoint_1": page("intervals", "The relation disjoint of IEEE 1788, one-limb bounds",
                                    form("ieee1788::disjoint(X, Y)", I1, I1, result="bool", note=EXACT_INTERVAL)),
    "interval_empty_2": page("intervals", "Whether an interval is empty, two-limb bounds",
                             form("X.is_empty()", I2, result="bool", note=EXACT_INTERVAL)),
    "interval_entire_2": page("intervals", "Whether an interval is the whole line, two-limb bounds",
                              form("X.is_whole()", I2, result="bool", note=WHOLE + "; " + EXACT_INTERVAL)),
    "interval_contains_2": page(
        "intervals", "Whether a point is a member of an interval, two-limb bounds",
        form("X.contains(t)", I2, E2, result="bool", note=EXACT_INTERVAL),
        form("X.contains(t)", I2, T, result="bool", note=POINT_TWO + "; " + EXACT_INTERVAL),
        form("member(t, X)", E2, I2, result="Trit", note=MEMBER_EXACT + "; " + EXACT_INTERVAL),
        form("member(t, X)", T, I2, result="Trit", note=MEMBER_EXACT + "; " + POINT_TWO + "; " + EXACT_INTERVAL)),
    "interval_subset_2": page(
        "intervals", "Whether an interval is a subset of another, two-limb bounds",
        form("Y.contains(X)", I2, I2, result="bool", note="whether $Y \\supseteq X$; " + EXACT_INTERVAL),
        form("ieee1788::subset(X, Y)", I2, I2, result="bool", note="the relation subset of IEEE 1788; " + EXACT_INTERVAL)),
    "interval_positive_2": page("intervals", "Whether every member of an interval is positive, two-limb bounds",
                                form("X.certainly_positive()", I2, result="bool", note=EXACT_INTERVAL)),
    "interval_negative_2": page("intervals", "Whether every member of an interval is negative, two-limb bounds",
                                form("X.certainly_negative()", I2, result="bool", note=EXACT_INTERVAL)),
    "interval_zero_2": page("intervals", "Whether an interval is [0, 0], two-limb bounds",
                            form("X.certainly_zero()", I2, result="bool", note=EXACT_INTERVAL)),
    "interval_less_2": page(
        "intervals", "The three-valued X < Y of intervals, two-limb bounds",
        form("less(X, Y)", I2, I2, result="Trit", note=EXACT_INTERVAL),
        form("greater(Y, X)", I2, I2, result="Trit", note="the operands exchanged; " + EXACT_INTERVAL)),
    "interval_less_equal_2": page(
        "intervals", "The three-valued X <= Y of intervals, two-limb bounds",
        form("less_equal(X, Y)", I2, I2, result="Trit", note=EXACT_INTERVAL),
        form("greater_equal(Y, X)", I2, I2, result="Trit", note="the operands exchanged; " + EXACT_INTERVAL)),
    "interval_equal_2": page(
        "intervals", "The three-valued X = Y of intervals, two-limb bounds",
        form("equal(X, Y)", I2, I2, result="Trit", note=EXACT_INTERVAL),
        form("not_equal(X, Y)", I2, I2, result="Trit", note=OPPOSITE + "; " + EXACT_INTERVAL)),
    "interval_rel_equal_2": page("intervals", "The relation equal of IEEE 1788, two-limb bounds",
                                 form("ieee1788::equal(X, Y)", I2, I2, result="bool", note=EXACT_INTERVAL)),
    "interval_rel_interior_2": page("intervals", "The relation interior of IEEE 1788, two-limb bounds",
                                    form("ieee1788::interior(X, Y)", I2, I2, result="bool", note=EXACT_INTERVAL)),
    "interval_rel_disjoint_2": page("intervals", "The relation disjoint of IEEE 1788, two-limb bounds",
                                    form("ieee1788::disjoint(X, Y)", I2, I2, result="bool", note=EXACT_INTERVAL)),
    # The conversions of two limbs, the ball from an interval of one limb, and the hull and the
    # intersection of balls of two limbs.
    "interval_mid_rad_2": page(
        "intervals", "The midpoint and radius of an interval, two-limb bounds",
        form("X.midpoint()", I2, result=E2, note="$m$; " + MIDRAD_TWICE + "; " + ROUNDS),
        form("X.radius()", I2, result=T, note="$r$; " + MIDRAD_TWICE + "; " + ROUNDS),
        form("X.mid_rad()", I2, result="MidRad<T, 2>", note="$m$ and $r$ from one call; " + ROUNDS)),
    "interval_to_ball_2": page("intervals", "A ball that contains an interval, two-limb bounds",
                               form("Ball<T, 2>(X)", I2, result=B2, note="explicit; " + ROUNDS)),
    "interval_split_2": page(
        "intervals", "An interval split at its midpoint, two-limb bounds",
        form("X.split()", I2, result="Split<Interval<T, 2>>",
             note="`left` is $[a_l, a_u]$ and `right` is $[b_l, b_u]$; " + SPLIT_POINT + "; " + ROUNDS_CONSTEXPR)),
    "ball_to_interval_2": page(
        "ball", "An interval that contains a ball, two-limb center",
        form("Interval<T, 2>(X)", B2, result=I2, group="intervals", note="explicit; " + ROUNDS),
        form("X.lower()", B2, result=E2, note="$z_l$; the kernel computes both bounds; " + ROUNDS),
        form("X.upper()", B2, result=E2, note="$z_u$; the kernel computes both bounds; " + ROUNDS)),
    "ball_from_interval_1": page(
        "ball", "A ball with a one-limb center from an interval given as two values of T",
        form("from_interval(lo, hi)", T, T, result=B1,
             note="`Ball<T, 1>::from_interval(lo, hi)`, the ball of `Interval<T, 1>(lo, hi)` in one kernel; the "
                  "bounds are guarded ([rule R3](../developer/architecture.md#the-kernel-ir)); " + ROUNDS_CONSTEXPR),
        form("from_bounds(lo, hi)", T, T, result=B1, note=FROM_BOUNDS_BALL % "1" + "; " + ROUNDS_CONSTEXPR),
        form("from_bounds(lo, hi)", E1, E1, result=B1, note=FROM_BOUNDS_BALL % "1" + "; " + ROUNDS_CONSTEXPR)),
    "ball_hull_2": page("ball", "A ball that contains two balls, two-limb center",
                        form("X.hull(Y)", B2, B2, result=B2, note=HULL_NOTE + "; " + ROUNDS)),
    "ball_intersection_2": page("ball", "A ball that contains the intersection of two balls, two-limb center",
                                form("X.intersection(Y)", B2, B2, result=B2, note=INTERSECTION_NOTE + "; " + ROUNDS)),
    # The set operations of a ball.
    "ball_hull_1": page("ball", "A ball that contains two balls, one-limb center",
                        form("X.hull(Y)", B1, B1, result=B1, note=HULL_NOTE + "; " + ROUNDS_CONSTEXPR)),
    "ball_intersection_1": page("ball", "A ball that contains the intersection of two balls, one-limb center",
                                form("X.intersection(Y)", B1, B1, result=B1, note=INTERSECTION_NOTE + "; " + ROUNDS_CONSTEXPR)),
    "ball_split_1": page("ball", "Two balls that cover a ball, one-limb center",
                         form("X.split()", B1, result="Split<Ball<T, 1>>", note=BALL_SPLIT + "; " + ROUNDS)),
    "ball_split_2": page("ball", "Two balls that cover a ball, two-limb center",
                         form("X.split()", B2, result="Split<Ball<T, 2>>", note=BALL_SPLIT + "; " + ROUNDS)),
    # The predicates and the three-valued comparisons of a ball.
    "ball_contains_point_1": page(
        "ball", "Whether a point is a member of a ball, one-limb center",
        form("X.contains(t)", B1, T, result="bool", note=ROUNDS_CONSTEXPR),
        form("X.contains(t)", B1, E1, result="bool", note=ROUNDS_CONSTEXPR),
        form("member(t, X)", T, B1, result="Trit", note=MEMBER_EXACT + "; " + ROUNDS_CONSTEXPR),
        form("member(t, X)", E1, B1, result="Trit", note=MEMBER_EXACT + "; " + ROUNDS_CONSTEXPR)),
    "ball_contains_ball_1": page("ball", "Whether a ball contains another, one-limb center",
                                 form("X.contains(Y)", B1, B1, result="bool",
                                      note="whether $X \\supseteq Y$; " + ROUNDS_CONSTEXPR)),
    "ball_positive_1": page("ball", "Whether every member of a ball is positive, one-limb center",
                            form("X.certainly_positive()", B1, result="bool", note=EXACT_INTERVAL)),
    "ball_negative_1": page("ball", "Whether every member of a ball is negative, one-limb center",
                            form("X.certainly_negative()", B1, result="bool", note=EXACT_INTERVAL)),
    "ball_zero_1": page("ball", "Whether a ball is the point 0, one-limb center",
                        form("X.certainly_zero()", B1, result="bool", note=EXACT_INTERVAL)),
    "ball_less_1": page(
        "ball", "The three-valued X < Y of balls, one-limb center",
        form("less(X, Y)", B1, B1, result="Trit", note=ROUNDS_CONSTEXPR),
        form("greater(Y, X)", B1, B1, result="Trit", note="the operands exchanged; " + ROUNDS_CONSTEXPR)),
    "ball_less_equal_1": page(
        "ball", "The three-valued X <= Y of balls, one-limb center",
        form("less_equal(X, Y)", B1, B1, result="Trit", note=ROUNDS_CONSTEXPR),
        form("greater_equal(Y, X)", B1, B1, result="Trit", note="the operands exchanged; " + ROUNDS_CONSTEXPR)),
    "ball_equal_1": page(
        "ball", "The three-valued X = Y of balls, one-limb center",
        form("equal(X, Y)", B1, B1, result="Trit", note=ROUNDS_CONSTEXPR),
        form("not_equal(X, Y)", B1, B1, result="Trit", note=OPPOSITE + "; " + ROUNDS_CONSTEXPR)),
    "ball_contains_point_2": page(
        "ball", "Whether a point is a member of a ball, two-limb center",
        form("member(t, X)", E2, B2, result="Trit", note="yes, no or unknown; " + ROUNDS),
        form("member(t, X)", T, B2, result="Trit", note="yes, no or unknown; " + POINT_TWO + "; " + ROUNDS),
        form("X.contains(t)", B2, E2, result="bool", note="$\\mathit{yes}$; " + ROUNDS),
        form("X.contains(t)", B2, T, result="bool", note="$\\mathit{yes}$; " + POINT_TWO + "; " + ROUNDS)),
    "ball_contains_ball_2": page("ball", "Whether a ball contains another, two-limb center",
                                 form("X.contains(Y)", B2, B2, result="bool", note="whether $X \\supseteq Y$; " + ROUNDS)),
    "ball_positive_2": page("ball", "Whether every member of a ball is positive, two-limb center",
                            form("X.certainly_positive()", B2, result="bool", note=EXACT_INTERVAL)),
    "ball_negative_2": page("ball", "Whether every member of a ball is negative, two-limb center",
                            form("X.certainly_negative()", B2, result="bool", note=EXACT_INTERVAL)),
    "ball_zero_2": page("ball", "Whether a ball is the point 0, two-limb center",
                        form("X.certainly_zero()", B2, result="bool", note=EXACT_INTERVAL)),
    "ball_less_2": page(
        "ball", "The three-valued X < Y of balls, two-limb center",
        form("less(X, Y)", B2, B2, result="Trit", note=ROUNDS),
        form("greater(Y, X)", B2, B2, result="Trit", note="the operands exchanged; " + ROUNDS)),
    "ball_less_equal_2": page(
        "ball", "The three-valued X <= Y of balls, two-limb center",
        form("less_equal(X, Y)", B2, B2, result="Trit", note=ROUNDS),
        form("greater_equal(Y, X)", B2, B2, result="Trit", note="the operands exchanged; " + ROUNDS)),
    "ball_equal_2": page(
        "ball", "The three-valued X = Y of balls, two-limb center",
        form("equal(X, Y)", B2, B2, result="Trit", note=ROUNDS),
        form("not_equal(X, Y)", B2, B2, result="Trit", note=OPPOSITE + "; " + ROUNDS)),
    # The building blocks of the intervals: parts of the interval kernels.
    "mul_dir_1": page("building-blocks", "Both directed products of two limbs, a zero factor giving zero"),
    "add_ball_2_2": page("building-blocks", "A sum of two-limb numbers with a bound of its error"),
    "mul_ball_2_2": page("building-blocks", "A product of two-limb numbers with a bound of its error"),
    "add_down_2_2": page("building-blocks", "A lower bound of a sum of two-limb numbers"),
    "add_up_2_2": page("building-blocks", "An upper bound of a sum of two-limb numbers"),
    "sub_down_2_2": page("building-blocks", "A lower bound of a difference of two-limb numbers"),
    "sub_up_2_2": page("building-blocks", "An upper bound of a difference of two-limb numbers"),
    "mul_dir_2_2": page("building-blocks", "Two bounds of a product of two-limb numbers"),
    "mul_ext_2_2": page("building-blocks", "Two bounds of a product of two bounds of intervals, two limbs"),
    # --- Building blocks: no public form -------------------------------------------------------
    "two_sum": page("building-blocks", "TwoSum: an exact sum as two limbs"),
    "two_prod": page("building-blocks", "TwoProd: an exact product as two limbs"),
    "mul_down_1": page("building-blocks", "A lower bound of a product of two limbs"),
    "mul_up_1": page("building-blocks", "An upper bound of a product of two limbs"),
    # traits<Expansion<T, 2>>::mul_limb is the bound of mul_2_1 (traits.hpp), which mul_2_1_entry claims too.
    "mul_2_1": page("building-blocks", "Product of a two-limb number and a limb",
                    traits=["traits<Expansion<T, 2>>::mul_limb"]),
    "mul_2_1_full": page("building-blocks", "Product of a two-limb number and a limb, with IEEE-like results"),
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
    "dot_step_1": page("arrays", "The step of a dot product of one limb, on stored arrays: one fused multiply-add"),
    "dot_entry_step_1": page("arrays", "The step of a dot product of one limb, on arrays of the program: one fused "
                             "multiply-add of the guarded elements",
                             form("dot(x, y)", V1, V1, result=R1, note=STEP_ORDER + " (loop `dot_1_entry`; each "
                                  "factor guarded, rule R3 on the factors of a fused operation)"),
                             form("dot(sequential, x, y)", SEQ, V1, V1, result=R1),
                             form("conv(x, y, z)", V1, V1, W1, result="bool", note="each coefficient a sequential "
                                  "`dot_1_entry` (loop `conv_1_entry`; each factor guarded)")),
    "dot_step_2": page("arrays", "The step of a dot product of two limbs, on stored arrays (the centers of `bv_conv_2`)"),
    "dot_entry_step_2": page("arrays", "The step of a dot product of two limbs, on arrays of the program: the "
                             "product and the sum of the guarded elements",
                             form("dot(x, y)", V2, V2, result=R2, note=STEP_ORDER + " (loop `dot_2_entry`; every "
                                  "limb of each factor guarded, rule R3 on the factors of a fused operation)"),
                             form("dot(sequential, x, y)", SEQ, V2, V2, result=R2),
                             form("conv(x, y, z)", V2, V2, W2, result="bool", note="each coefficient a sequential "
                                  "`dot_2_entry` (loop `conv_2_entry`; every limb of each factor guarded)")),
    "sum_entry_step_1": page("arrays", "The step of a sum of one limb, on an array of the program",
                             form("sum(x)", V1, result=R1, note=STEP_ORDER + " (loop `sum_1_entry`)"),
                             form("sum(sequential, x)", SEQ, V1, result=R1),
                             form("sum_fast(x)", V1, result=R1, note="for one limb, `sum(x)`")),
    "sum_entry_step_2": page("arrays", "The step of a sum of two limbs, on an array of the program",
                             form("sum(x)", V2, result=R2, note=STEP_ORDER + " (loop `sum_2_entry`)"),
                             form("sum(sequential, x)", SEQ, V2, result=R2)),
    "sum_fast_entry_step_2": page("arrays", "The step of a sum of two limbs with the fast addition, on an array of "
                                            "the program",
                                  form("sum_fast(x)", V2, result=R2, note=STEP_ORDER + " (loop `sum_fast_2_entry`)"),
                                  form("sum_fast(sequential, x)", SEQ, V2, result=R2)),
    "fold_finish_1": page("arrays", "The result of a fold of one limb: the state, or NaN",
                          form("A.sum()", A1, result=R1, note="the running sum of an accumulator, canonical; "
                               "the finish of the loops of `kairn/batch.hpp` too")),
    "fold_finish_2": page("arrays", "The result of a fold of two limbs: the state, or NaN",
                          form("A.sum()", A2, result=R2, note="the running sum of an accumulator, canonical; "
                               "the finish of the loops of `kairn/batch.hpp` too")),
    "bound_sum_1": page("arrays", "The bound of a sum of one limb, as a function of the number of additions",
                        form("traits<T>::sum(n)", "std::size_t", result="Bound<T>",
                             note="$m = n - 1$ (0 for $n = 0$), a count of `T` rounded up; `unit` is $g$"),
                        form("traits<T>::sum_height(h)", "std::size_t", result="Bound<T>", note="$m = h$")),
    "bound_sum_2": page("arrays", "The bound of a sum of two limbs, as a function of the number of additions",
                        form("traits<Expansion<T, 2>>::sum(n)", "std::size_t", result="Bound<T>",
                             note="$m = n - 1$ (0 for $n = 0$), a count of `T` rounded up; `unit` is $g$"),
                        form("traits<Expansion<T, 2>>::sum_height(h)", "std::size_t", result="Bound<T>",
                             note="$m = h$")),
    "bound_dot_1": page("arrays", "The bound of a dot product of one limb, as a function of the number of terms",
                        form("traits<T>::dot(n)", "std::size_t", result="Bound<T>",
                             note="$m = n$, a count of `T` rounded up; `unit` is $g$, `tiny` is $t$")),
    "bound_dot_2": page("arrays", "The bound of a dot product of two limbs, as a function of the number of terms",
                        form("traits<Expansion<T, 2>>::dot(n)", "std::size_t", result="Bound<T>",
                             note="$m = n$, a count of `T` rounded up; `unit` is $g$, `tiny` is $t$")),
    "sub_1_1": page("maps", "The difference of two numbers of one limb, rounded to nearest"),
    "add_entry_step_1": page("maps", "x + y of one limb, on arrays of the program",
                             form("add(x, y, z)", V1, V1, W1, result="bool", note=STEP + " (loop `add_1_entry`)")),
    "sub_entry_step_1": page("maps", "x - y of one limb, on arrays of the program",
                             form("sub(x, y, z)", V1, V1, W1, result="bool", note=STEP + " (loop `sub_1_entry`)")),
    "add_entry_step_2": page("maps", "x + y of two limbs, on arrays of the program",
                             form("add(x, y, z)", V2, V2, W2, result="bool", note=STEP + " (loop `add_2_entry`)")),
    "sub_entry_step_2": page("maps", "x - y of two limbs, on arrays of the program",
                             form("sub(x, y, z)", V2, V2, W2, result="bool", note=STEP + " (loop `sub_2_entry`)")),
    "scale_step_1": page("maps", "x a of one limb, a of T",
                         form("scale(x, a, z)", V1, T, W1, result="bool", note=STEP + " (loop `scale_1`)")),
    "scale_step_2": page("maps", "x a of two limbs, a of T, on a stored array and scalar"),
    "scale_entry_step_2": page("maps", "x a of two limbs, a of T, on the guarded limbs and scalar",
                               form("scale(x, a, z)", V2, T, W2, result="bool", note=STEP + " (loop `scale_2_entry`; the "
                                    "limbs of each element and a guarded, rule R3 on the factors of a fused "
                                    "operation)")),
    "mul_pow2_step_1": page("maps", "x c of one limb, c a power of two",
                            form("mul_pow2(x, c, z)", V1, T, W1, result="bool", note=STEP + " (loop `mul_pow2_map_1`)")),
    "mul_pow2_step_2": page("maps", "x c of two limbs, c a power of two",
                            form("mul_pow2(x, c, z)", V2, T, W2, result="bool", note=STEP + " (loop `mul_pow2_map_2`)")),
    "axpy_step_1": page("maps", "a x + y of one limb, y stored"),
    "axpy_entry_step_1": page("maps", "a x + y of one limb, y of the program",
                              form("axpy(a, x, y, z)", T, V1, V1, W1, result="bool", note=STEP + " (loop `axpy_1_entry`)"),
                              traits=["traits<T>::axpy"]),
    "axpy_step_2": page("maps", "a x + y of two limbs, a, x and y stored"),
    "axpy_entry_step_2": page("maps", "a x + y of two limbs, a, x and y of the program, every limb guarded",
                              form("axpy(a, x, y, z)", E2, V2, V2, W2, result="bool", note=STEP + " (loop `axpy_2_entry`; "
                                   "every limb of a, x and y guarded, rule R3 and its factors of a fused operation)"),
                              traits=["traits<Expansion<T, 2>>::axpy"]),
    "axpy_step_2_1": page("maps", "a x + y of two limbs, a of T, a, x and y stored"),
    "axpy_entry_step_2_1": page("maps", "a x + y of two limbs, a of T, a, x and y of the program, guarded",
                                form("axpy(a, x, y, z)", T, V2, V2, W2, result="bool",
                                     note=STEP + " (loop `axpy_2_1_entry`; a and every limb of x and y guarded, "
                                     "rule R3 and its factors of a fused operation)"),
                                traits=["traits<Expansion<T, 2>>::axpy_limb"]),
    # --- Milestone 2, the folds of maxima (norm_upper_k) ---------------------------------------------
    "norm_combine": page("arrays", "The larger of two magnitudes, and the and of two masks"),
    "norm_step_1": page("arrays", "The step of the largest magnitude of an array of one limb"),
    "norm_step_2": page("arrays", "The step of the largest magnitude of an array of two limbs: its leading limb"),
    "norm_finish_1": page("arrays", "The result of a fold of maxima of one limb: the maximum, or NaN"),
    "norm_finish_2": page("arrays", "The result of a fold of maxima of two limbs: one step above the maximum, or NaN"),
    # --- Milestone 2, the accumulator ----------------------------------------------------------------
    "acc_add_1": page("arrays", "An accumulator of one limb: add a number of the program",
                      form("A.add(x)", A1, E1, result="void", note=ACC),
                      form("A.add(a)", A1, T, result="void")),
    "acc_add_2": page("arrays", "An accumulator of two limbs: add a number of the program",
                      form("A.add(x)", A2, E2, result="void", note=ACC),
                      form("A.add(a)", A2, T, result="void", note=TO_TWO_LIMBS)),
    "acc_mul_1": page("arrays", "An accumulator of one limb: add a product (its factors unguarded; "
                      "`add_product` calls `acc_mul_entry_1`)"),
    "acc_mul_entry_1": page("arrays", "An accumulator of one limb: add a product of the guarded factors",
                            form("A.add_product(x, y)", A1, E1, E1, result="void", note=ACC + "; not `constexpr`; "
                                 "each factor guarded (rule R3 on the factors of a fused operation)"),
                            form("A.add_product(a, b)", A1, T, T, result="void")),
    "acc_mul_2": page("arrays", "An accumulator of two limbs: add a product (its factors unguarded; "
                      "`add_product` calls `acc_mul_entry_2`)"),
    "acc_mul_entry_2": page("arrays", "An accumulator of two limbs: add a product of the guarded factors",
                            form("A.add_product(x, y)", A2, E2, E2, result="void", note=ACC + "; not `constexpr`; "
                                 "each limb of each factor guarded (rule R3 on the factors of a fused "
                                 "operation)"),
                            form("A.add_product(a, b)", A2, T, T, result="void", note=TO_TWO_LIMBS)),
    "acc_merge_1": page("arrays", "Two accumulators of one limb into one",
                        form("A.merge(B)", A1, A1, result="void", note="a node of the summation tree; the counts "
                             "added")),
    "acc_merge_2": page("arrays", "Two accumulators of two limbs into one",
                        form("A.merge(B)", A2, A2, result="void", note="a node of the summation tree; the counts "
                             "added")),
    "acc_radius_1": page("arrays", "The radius of an accumulator of one limb",
                         form("A.error_bound()", A1, result=T, note="with $(g, t)$ = `bound_dot_1` of the count "
                              "as a number of `T` rounded up, $+\\infty$ where a mask is false or a value is not "
                              "finite; not `constexpr`"),
                         form("A.ball()", A1, result=B1, note="the whole line where `error_bound()` is $+\\infty$")),
    "acc_radius_2": page("arrays", "The radius of an accumulator of two limbs",
                         form("A.error_bound()", A2, result=T, note="with $(g, t)$ = `bound_dot_2` of the count "
                              "as a number of `T` rounded up, $+\\infty$ where a mask is false or a value is not "
                              "finite; not `constexpr`"),
                         form("A.ball()", A2, result=B2, note="the whole line where `error_bound()` is $+\\infty$")),
    # --- Milestone 2, BallVector ---------------------------------------------------------------------
    "bv_add_radius_1": page("ball-vectors", "The radius of the sum or the difference of two BallVectors of one limb"),
    "bv_add_radius_2": page("ball-vectors", "The radius of the sum or the difference of two BallVectors of two limbs"),
    "bv_scale_radius_1": page("ball-vectors", "The radius of a BallVector of one limb times a number of T"),
    "bv_scale_radius_2": page("ball-vectors", "The radius of a BallVector of two limbs times a number of T"),
    "bv_scale_radius_entry_2": page("ball-vectors", "The radius of a BallVector of two limbs times a number of T, "
                                    "the number guarded"),
    "bv_center_entry_1": page("ball-vectors", "A center of one limb given to the constructor of a BallVector"),
    "bv_center_2": page("ball-vectors", "A center of two limbs given to the constructor of a BallVector"),
    "bv_center_entry_2": page("ball-vectors", "A center of two limbs given to the constructor of a BallVector, "
                              "each limb guarded"),
    "bv_scale_step_2": page("ball-vectors", "A center of two limbs times a number of T, the number guarded"),
    "bv_make_radius": page("ball-vectors", "The radius given to the constructor of a BallVector"),
    "bv_make_finish": page("ball-vectors", "The result of the constructor of a BallVector: the radius given, or NaN"),
    "neg_1": page("ball-vectors", "The negation of a number of T, the step of the negation of a BallVector"),
    "bv_neg_radius": page("ball-vectors", "The radius of the negation of a BallVector: the radius given"),
    "bv_mul_pow2_step_1": page("ball-vectors", "A center of one limb times a power of two, and whether it is exact"),
    "bv_mul_pow2_step_2": page("ball-vectors", "A center of two limbs times a power of two, and whether it is exact"),
    "bv_mul_pow2_radius": page("ball-vectors", "The radius of a BallVector times a power of two: exact when nothing "
                                               "underflows"),
    "conv_radius": page("ball-vectors", "The radius of the product of two polynomials whose coefficients are BallVectors"),
    "bv_conv_finish": page("ball-vectors", "The result of the product of two BallVectors: the radius, or NaN"),
}


def exact(group, does, *forms, kernel="none"):
    return {"group": group, "does": does, "forms": list(forms), "kernel": kernel}


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
    exact("construction", "the midpoint of the interface Ball shares with Interval: the center",
          form("X.midpoint()", "Ball<T, K>", result="Expansion<T, K>")),
    exact("intervals", "the point 0: $[0, 0]$",
          form("Interval<T, K>()", result="Interval<T, K>")),
    exact("intervals", "the empty set: $(+\\infty, -\\infty)$",
          form("Interval<T, K>::empty()", result="Interval<T, K>")),
    exact("intervals", "the whole line: $[-\\infty, +\\infty]$",
          form("Interval<T, K>::whole()", result="Interval<T, K>")),
    exact("intervals", "whether it is a nonempty bounded interval (both bounds finite, tested on the bit "
          "patterns of their leading limbs): false for the empty set, the whole line and the half-lines, "
          "the meaning of a ball's `is_finite()`",
          form("X.is_finite()", "Interval<T, K>", result="bool")),
    exact("intervals", "the stored bounds; $+\\infty$ and $-\\infty$ for the empty set",
          form("X.lower(), X.upper()", "Interval<T, K>", result="Expansion<T, K>"),
          form("X.lower_as<T>(), X.upper_as<T>()", I1, result=T)),
    exact("construction", "$-1$, $0$ or $+1$, from the leading limb; $0$ for NaN",
          form("sign(x)", "Expansion<T, K>", result="int")),
    exact("construction", "whether the leading limb is finite",
          form("isfinite(x)", "Expansion<T, K>", result="bool")),
    exact("construction", "whether every limb is finite and, for two limbs, $x_0 + x_1$ rounds to $x_0$",
          form("is_normalized(x)", "Expansion<T, K>", result="bool")),
    exact("ball", "the center and the radius together, for code written for intervals and balls alike",
          form("X.mid_rad()", "Ball<T, K>", result="MidRad<T, K>")),
    exact("ball", "whether a three-valued answer is yes, and whether it is not no ([One enclosure "
          "interface](enclosure.md#three-valued-answers))",
          form("certainly(t), possibly(t)", "Trit", result="bool")),
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
    # Packed (kairn/packed.hpp) and the containers (kairn/soa.hpp): the kernels are those of the
    # operations of Expansion of the same name, in every lane; their pages are the forms' pages.
    exact("packed", "in each lane, the operation of `Expansion<T, 2>` of the same name, with its statement; a "
          "`Packed<T, 1>` operand is the limb of the mixed forms",
          form("x + y, x - y, x * y, x += y, x -= y, x *= y, -x, abs(x), add_fast(x, y), ldexp(x, n), half(x)",
               P2, P2, result=P2),
          form("x + a, a + x, x - a, a - x, x * a, a * x", P2, P1, result=P2),
          kernel="that of `Expansion` ([Packed](packed.md#the-operations))"),
    exact("packed", "in each lane, the comparison of `Expansion`: a mask of W truth values",
          form("x < y, x > y, x <= y, x >= y, x == y, x != y", PK, PK, result="PackedMask<T>"),
          kernel="that of `Expansion`, or none for one limb"),
    exact("packed", "in each lane, the conversion of `Expansion<T, 2>` to one limb",
          form("to_nearest(x), to_down(x), to_up(x), abs_upper(x), Packed<T, 1>(x)", P2, result=P1),
          kernel="that of `Expansion`"),
    exact("packed", "in each lane, the function of `kairn::finite` of the same name: the core, without the fix-up",
          form("finite::add, finite::sub, finite::mul, finite::add_fast, finite::ldexp", P2, PK, result=P2),
          kernel="that of `Expansion`"),
    exact("packed", "one limb: the exact operations of `T`, as for `Expansion<T, 1>`; no arithmetic, whose "
          "kernels are not entry kernels ([Packed](packed.md#the-operations))",
          form("-x, abs(x), x < y, x == y, to_nearest(x), to_down(x), to_up(x), abs_upper(x)", P1, P1, result=P1)),
    exact("packed", "moves: zero, one number in every lane, a lane read or written, a select by a mask; limbs "
          "copied, nothing computed",
          form("Packed<T, K>(), Packed<T, K>::broadcast(x), p.lane(i), p.set_lane(i, x), select(m, a, b)", PK,
               result=PK)),
    exact("packed", "whether every lane, some lane, or lane i of a mask is true; and, or and not, lane by lane "
          "(`&`, the bar, `!`)",
          form("all(m), any(m), m.lane(i), m & n, !m", "PackedMask<T>", result="bool")),
    exact("packed", "W numbers from arrays, or into them, unaligned; a two-limb load is `from_limbs` in each lane "
          "(guarded, and checked with `KAIRN_CHECKS`); the tail with `load_partial` and `store_partial`",
          form("Packed<T, 2>::load(x0, x1), p.store(x0, x1), load_partial(x0, x1, n, fill)", "const T*", "const T*",
               result=P2),
          kernel="`make_2_limbs` (a load), or none"),
    exact("packed", "element i of an array of numbers, read as `from_limbs` (checked with `KAIRN_CHECKS`) or "
          "written (limbs copied); W of them as a `Packed` ([Arrays of numbers](soa.md))",
          form("v[i], v.get(i), v.set(i, x), v.load(i), v.store(i, p)", "SoAView<T, K>", "std::size_t",
               result="Expansion<T, K>"),
          kernel="`make_2_limbs` (a read), or none"),
]

PAGES = [
    ("construction", "Constants from fractions", "rational"),
    ("intervals", "One enclosure interface: intervals and balls", "enclosure"),
    ("packed", "Packed numbers in registers", "packed"),
    ("packed", "Arrays of numbers: SoA and its views", "soa"),
    ("arrays", "Functions on arrays", "batch"),
    ("arrays", "The accumulator", "accumulator"),
    ("ball-vectors", "Ball vectors: BallVector and its views", "ball_vector"),
]

# BallVector (kairn/ball_vector.hpp): each operation is a loop over arrays, not a kernel, whose parts
# are the kernels of the group (LOOPS above); the rows of the index name the loop.
BVK = "BallVector<T, K, N>"
BVV = "BallVectorView<T, K>"
EXACT += [
    exact("ball-vectors", "the ball vector of the centers and the radius given; the whole space when the radius "
          "is negative, a NaN or +inf, or a center is not finite ([Ball vectors](ball_vector.md#construction))",
          form("BallVector<T, K, N>(c, r)", "std::array<Expansion<T, K>, N>", T, result=BVK),
          form("BallVectorView<T, K>(c, r)", "SoAView<T, K>", "T&", result=BVV),
          kernel="the loop `bv_make_k`"),
    exact("ball-vectors", "the point 0, the whole space, a copy of a view, the views; the radius, a center, entry "
          "i as a `Ball` (a copy); limbs copied, nothing computed",
          form("BallVector<T, K, N>(), whole(), x.view(), x.radius(), x.center(i), x.entry(i)", BVK, result=BVK)),
    exact("ball-vectors", "exactly the negated set ([Ball vectors](ball_vector.md#the-operations))",
          form("-x, neg(x, z)", BVK, result=BVK), kernel="the loop `bv_neg_k`"),
    exact("ball-vectors", "an enclosure of every sum or difference of members, entry by entry",
          form("x + y, x - y, x += y, x -= y, add(x, y, z), sub(x, y, z)", BVK, BVK, result=BVK),
          kernel="the loops `bv_add_k`, `bv_sub_k`"),
    exact("ball-vectors", "an enclosure of every member times a",
          form("x * a, a * x, x *= a, scale(x, a, z)", BVK, T, result=BVK), kernel="the loop `bv_scale_k`"),
    exact("ball-vectors", "every member times 2^n, exactly when nothing underflows",
          form("ldexp(x, n), half(x), ldexp(x, n, z), half(x, z)", BVK, "int", result=BVK),
          kernel="the loop `bv_mul_pow2_k`, two or three calls beyond the powers of two of `T`"),
    exact("ball-vectors", "an enclosure of every a x + y: a composition of two loops made in the header",
          form("axpy(a, x, y), axpy(a, x, y, z)", T, BVK, BVK, result=BVK),
          kernel="the loops `bv_scale_k`, then `bv_add_k`"),
    exact("ball-vectors", "an enclosure of every coefficient of the product of members as polynomials, of "
          "N + M - 1 coefficients", form("convolution(x, y), convolution(x, y, z)", BVK, "BallVector<T, K, M>",
                                         result="BallVector<T, K, N + M - 1>"), kernel="the loop `bv_conv_k`"),
    exact("ball-vectors", "an upper bound of the magnitude of every entry of every member: a composition made in "
          "the header", form("norm_upper(x)", BVK, result=T), kernel="the loop `norm_upper_k`, then `add_up_entry`"),
]
