# The round-up interval: its kernels

The kernels of the round-up interval are the family of the opt-in header `kairn/upward.hpp`, which
`kairn/kairn.hpp` does not include and which requires the rounding mode upward, set by
`kairn::upward::Scope`, and the options of [The round-up interval](../concepts/upward.md) (GCC and
Clang `-frounding-math`, MSVC `/fp:strict`). Each kernel has a page of its own, written by
`docs/tools/reference.py` from `gen/claims.json` like every other
([The round-up interval](index.md#the-round-up-interval) in the index lists them, with the status
of each). This page says what those pages mean where they differ from the pages of the default
interval kernels: how a state is stored, what their statements are about, in which model, and what
is assumed outside the proofs. The design is the
[design page of the round-up interval](../developer/design/upward.md).

## The stored pair

A state of the round-up interval is two numbers of `T`, the two lanes of one register: lane 0, first
in memory, the upper bound $u$, and lane 1 the lower bound negated, $n$. The interval $[a, b]$ is
the pair $(u, n) = (b, -a)$:

| State | $(u, n)$ | Members |
|---|---|---|
| the empty set | $(\mathrm{NaN}, \mathrm{NaN})$ | none |
| a nonempty interval $[a, b]$ | $(b, -a)$: neither lane a NaN, both in $(-\infty, +\infty]$, and $-n \le u$ | the real numbers $x$ with $a \le x \le b$ |
| among them the whole line | $(+\infty, +\infty)$ | every real number |
| $[a, +\infty]$, $a$ finite | $(+\infty, -a)$ | $x \ge a$ |
| $[-\infty, b]$, $b$ finite | $(b, +\infty)$ | $x \le b$ |

These are the *canonical* states. As for the default interval, the members are real numbers:
$[1, +\infty]$ does not contain $+\infty$. No lane of a canonical state is $-\infty$, and a NaN lane
is never alone; a pair with one NaN lane, a lane $-\infty$ or crossed lanes ($-n > u$) is not a
state, and nothing is stated about it ([States](../developer/design/upward.md#states)).

On a kernel's page a state is named by its pair: $X = [-x_n, x_u]$, stored as $(x_u, x_n)$, is the
input `x` of the description, whose lanes are the inputs `xu` and `xn`; the output $Z$ is
$(z_u, z_n)$. So a lower bound always appears negated, $-x_n$, and a result's lower bound is
$-z_n$.

## What the statements say

The statements are those of the default interval kernels of the same name, read on the state the
pair stands for (the requirement that an operand is a canonical state, I1 to I5 of the arithmetic,
the hull, the intersection, the constructor, the predicates and the comparisons). What differs:

- **Both lanes round upward.** I4 of a sum, a difference or a product says that the lower bound is
  the lower bound of the exact range rounded down, $-z_n = \mathrm{RD}(\ell)$, and the upper bound
  its upper bound rounded up, $z_u = \mathrm{RU}(h)$. Since $\mathrm{RD}(t) = -\mathrm{RU}(-t)$,
  that is $z_n = \mathrm{RU}(-\ell)$: both lanes are rounded in the direction that widens the
  interval, under the one mode.
- **The products are exactly rounded.** The I4 of the product, and of the product by a number, has
  no step of slack, where the default one-limb product may be one number of `T` wider when a
  product of bounds is nonzero and below $2^{2p-1}\eta$
  ([Differences from the default interval](../developer/design/upward.md#differences-from-the-default-interval)).
- **Operations with a number.** The sum and the product with a number $t$ of `T` range over the
  members of `Interval(t)`, written $\langle t\rangle$: $\{t\}$ for a finite $t$, every real number
  for an infinite $t$ or a NaN, as the default type makes `Interval(t)`. A number is never empty,
  and is a bounded operand of I5 when it is finite.
- **The conversions** to and from an interval of the default type state the same set: the result
  is canonical, empty exactly when the operand is, and has the same members, so the same bounds; the
  empty set is $(\mathrm{NaN}, \mathrm{NaN})$ here and $(+\infty, -\infty)$ in the default type.
- **The sign of a zero bound** is not claimed, as for every kernel: here it is unspecified, and it
  can differ from the default type's and between x86-64 and arm64.

The claims that say this are those of
[Claims of the round-up interval](../developer/architecture.md#claims-of-the-round-up-interval):
the requirement `upward(U, N)`, sets and outputs named by their stored pair `{"upper", "nlower"}`,
`numbers` and the kind `same_set`; every entry of the family carries `"rounding": "upward"`.

## The model

Every statement of the family is in the IEEE model only (Flocq's model of IEEE 754, with signed
zeros, infinities, NaN and overflow): a kernel of the family has no statement in the model of real
numbers. The generator prints each kernel as a function of Flocq's binary floating-point numbers
into `proofs/gen/UpwardModel.v` and its statement, `K_spec`, into `proofs/gen/UpwardStatements.v`,
in the vocabulary of `proofs/theories/IeeeUpwardVocabulary.v`; `proofs/gen/UpwardAudit.v` prints the
axioms of the theorem of every statement that the claims mark proved. A listing uses four operations
of its own ([The operations of the IR](../developer/design/upward.md#the-operations-of-the-ir)):

| Operation | Meaning | In the model |
|---|---|---|
| `add_ru a b` | IEEE 754's sum rounded upward, toward $+\infty$ | `Bplus` with `mode_UP` |
| `mul_ru a b` | IEEE 754's product rounded upward | `Bmult` with `mode_UP` |
| `unord a b` | whether $a$ or $b$ is a NaN | a test of each |
| `max_nl a b` | the greater of $a$ and $b$, and $b$ when $a$ is a NaN | any function with the property `max_nl_ok` |

The maximum is a property, not one function, because the two instructions that compute it in one
step, x86's `MAXPD` and arm64's `FMAXNM`, differ in the sign of a zero: a statement that uses it
holds for every maximum with the property, and both instructions have it
([The maximum](../developer/design/upward.md#the-maximum)). No operation of a listing rounds to
nearest. A line of two statements separated by ` | ` is a *pair line*: the two lanes of one
instruction, lane 0 on the left; the model, the statements and the claims read it as its two
statements ([The pair form](../developer/design/upward.md#the-pair-form)).

The kernel's page gives the status of its statement, from `gen/claims.json`, and names its theorem
and the audit file that prints the theorem's axioms when it is proved; the
[index](index.md#the-round-up-interval) marks every kernel that is not.

## What is assumed outside the proofs

A proof is about the model. That the compiled code computes what the model says is assumed: each
`add_ru` and `mul_ru` of a generated kernel runs as IEEE 754's operation rounded upward in the
format of `T`, on the values the listing names, and each `max_nl` as one of the two instructions on
quiet NaNs. That holds where the thread's rounding mode is upward with flush to zero and
denormals-are-zero off, which the header's scopes make so, and where the compiler emits the
operations as written inside the scope, which the options and the header's barriers make so (on
MSVC a barrier per scope, with a weaker assurance). It is the program's to arrange, as
[The round-up interval](../concepts/upward.md#what-the-program-guarantees) says, and
[What is not machine-checked](../concepts/correctness.md#what-is-not-machine-checked) lists it. The
kernels that do not round (the negation, the hull, the intersection, the constructor, the
conversions, the predicates and the comparisons) give the same result in every rounding mode; they
still assume no flush to zero, under which a comparison reads a subnormal number as zero.
