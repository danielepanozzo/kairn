# How to read a reference page

Every operation of Kairn is computed by one *kernel*: a short generated function, such as `add_2_2`
for the sum `x + y` of two two-limb numbers. The [reference](index.md) has one page per kernel.
The pages are generated from the files that the library, the proofs and the tests are built from
(`gen/claims.json`, the kernel descriptions under `gen/kernels/`, and the stored brute-force
results), so that a page cannot say something those files do not. This page explains what each
part of a page means.

## Notation

The notation is that of [Numbers](../developer/design/phase0/numbers.md#notation).

| Symbol | Meaning |
|---|---|
| $p$ | the precision of the limb type `T`: 53 bits for `double`, 24 for `float` |
| $u = 2^{-p}$ | the unit roundoff: $2^{-53}$ for `double`, $2^{-24}$ for `float` |
| $\eta$ | the smallest positive number of `T`, a subnormal: $2^{-1074}$ for `double`, $2^{-149}$ for `float` |
| $\mathrm{RN}(t)$ | $t$ rounded to the nearest number of `T`, ties to even |
| $\mathrm{RD}(t)$, $\mathrm{RU}(t)$ | the largest number of `T` not above $t$; the smallest not below $t$ |
| $\mathrm{pred}(r)$ | the number of `T` just below $r$; $r - \mathrm{pred}(r)$ is a *gap* |
| $x = x_0 + x_1$ | a two-limb number stands for the exact sum of its limbs |
| normalized | $x_0 = \mathrm{RN}(x_0 + x_1)$: the second limb is at most half a unit in the last place of the first, so $x_0$ is $x$ rounded to nearest |

A formula's error bound has the shape $c\,u^k\,\lvert v\rvert + t\,\eta$, with $v$ the exact
value: $c\,u^k$ is relative to the result (with $k = 2$ for two limbs, so about $10^{-32}$ for
`double`), and $t\,\eta$ is an absolute term that only matters when the result is near the
underflow range.

For infinite and NaN operands
([IEEE-like results](../developer/design/milestone1.md#ieee-like-results)):

| Term | Meaning |
|---|---|
| canonical | of a two-limb number: finite and normalized, or $(\pm\infty, \pm 0)$, or $(\mathrm{NaN}, \mathrm{NaN})$; of a ball: a finite ball, the whole line (center 0, radius $+\infty$), or the empty set (every limb a NaN) |
| $\Omega$ | the largest finite number of `T` |
| $2^{e_{\max}}$ | the overflow threshold of `T`, just above $\Omega$: $2^{1024}$ for `double`, $2^{128}$ for `float` |

## Three kinds of kernel

- Most kernels have a statement about **finite operands** only, proved over the real numbers.
- Some also have a statement about operands that may be **infinite or NaN**, read in the IEEE model
  (comparisons, conversions, negation and absolute value, the radius steps). Their page gives the
  statement on finite operands first, then a section "Infinite and NaN operands" with its own
  requirements and its own status line.
- The **full kernels** (`add_2_2_full` and the like) and the **constructors** (`make_2`,
  `ball_make_2` and the like) have only the statement in the IEEE model. A full kernel runs its
  *core*, the kernel of the same name without `_full`, and then turns overflow and infinite or NaN
  operands into the result `T` would give. Its statement has five parts, F1 to F5, printed with the
  core's bound and the kernel's own conditions; a full Ball kernel has four, B1 to B4, about the
  three states of a ball. The operators and constructors of the public headers call these kernels.

## The parts of a page

**What it computes.** The exact value the result stands for, as a formula of the operands. For an
arithmetic kernel the result approximates it; for a comparison it is a truth value; for a
conversion, a rounding; for a ball, the set of every result the operation can have on points of the
operands.

**C++.** The expressions that reach the kernel, with the type of each operand: `T` is `float` or
`double`, `Expansion<T, 2>` a number of two limbs, `Ball<T, 1>` a ball whose center has one limb.
A form marked as converted reaches the kernel through an exact conversion of an operand (a limb to
a one-limb number, a one-limb number to two limbs, a point to a ball of radius 0). A building
block has no form: it is a step of other kernels. A kernel that the public headers may call but do
not call yet says "not yet called by the public headers".

**Requires.** What the operands must satisfy for the guarantee to apply. On finite operands, every
operand is finite. Every operation of Kairn returns normalized numbers when the leading limb of its
result is finite, so the requirement that an operand be normalized can fail only for a number whose
limbs the program gave: `from_limbs` in a build without checks, `from_limbs_unchecked`, or `limb[]`
written directly. In a build with `KAIRN_CHECKS` (the default without `NDEBUG`), every operator
and function of `kairn::` checks that its two-limb operands are canonical (finite and normalized,
or an infinity or a NaN in canonical form), every function of `kairn::finite::` that they are
normalized or have a leading limb that is not finite, and the program stops if one fails. A
statement about infinite and NaN operands requires canonical operands instead, and a one-limb
operand it does not constrain may be any value of `T`.

**Guarantees.** The statement, then its constants. For a bound, the table gives $c\,u^k$ and
$t\,\eta$ for `double` and `float`, exactly and approximately, and the constants that
`kairn::traits` exports: the same numbers rounded up to `T`, and the bound relative to the computed
value instead of the exact one (what a running error analysis needs). Last, the smallest precision
for which the statement is proved.

**Status.** *Proved*, with the theorem's name and its file, and the audit file that prints the
axioms its proof depends on; or *UNVERIFIED*, marked at the top of the page (below). Each
statement has its own status, as `gen/claims.json` gives it (`status`, and `ieee_status` for the
statement about infinite and NaN operands); a page never derives one from anything else.

**Axioms.** The axioms a proof may depend on: the four that the audit allows, from
`proofs/audit/allowed_axioms.txt`. Which of them a given theorem depends on is known only by running
Rocq, so the page does not list them; it points to the artifact of the CI that keeps what the
audit printed ([Proofs](../proofs/index.md)).

**Source.** Where the algorithm comes from and under which license, as the kernel's description
gives them. The references are on the [References](../developer/design/phase0/references.md) page.

**Listing.** The kernel as the generator reads it: one operation of `T` per line, each rounded to
nearest. The C++ and the formal model are both printed from it.

**Measured.** What the stored brute-force runs of the kernel's code found, campaign by campaign,
explained [below](#what-the-measured-numbers-are).

**Not claimed.** What the statements do not cover. For a kernel with a statement about finite
operands only: operands that are infinite or NaN, and results that overflow; the page names the
full kernel that states them, if there is one, and
[What holds today](../getting-started/guarantees.md#overflow-and-non-finite-values) says what the
library does now.

## What "proved" means

The generator prints, from the same kernel description as the C++, a model of the kernel for the
proof assistant Rocq (`proofs/gen/Model.v`) and the statement of the kernel's claims
(`proofs/gen/Statements.v`, one `K_spec` per kernel `K`). A kernel is *proved* when Rocq accepts a
hand-written theorem `K_correct` whose type is exactly `K_spec`, and the audit of `make -C proofs`
finds that its proof uses no axiom beyond the four allowed. The [Proofs](../proofs/index.md) page
says how to check this yourself.

The statement is about real numbers: it holds for every binary floating-point format whose
precision is at least the minimum shown, with any exponent range, rounding to nearest with ties to
even, and gradual underflow, with exponents unbounded above, so that nothing overflows. For
`double` and `float` it is therefore the guarantee whenever no operation inside the kernel
overflows. What is proved when one does is a separate, smaller set of theorems, listed per
operation in [What holds today](../getting-started/guarantees.md#the-operations).

A proof does not show that the statement is the one you want: read it, on the page or in
`Statements.v`. Nor does it cover the steps from the description to the machine: that the C++ the
generator prints computes what the model says, that the compiler keeps it that way, and that the
hardware rounds as IEEE 754 says. The tests are for those
([Testing](../developer/testing.md)), and `kairn::self_test()` checks the last two in your own
program.

An **UNVERIFIED** kernel has a statement but no checked proof. Its page says so at the top, its
guarantee is called a target, an operation that calls it compiles only with the marker
`kairn::unverified` on an operand, and `kairn::traits` exports no constants for it
([What holds today](../getting-started/guarantees.md#proved-and-unverified)).

The statements about infinite and NaN operands are read in Flocq's model of IEEE 754, with signed
zeros, infinities, NaN and overflow; the generator prints them into
`proofs/gen/IeeeStatements.v`, and the [index](index.md) says how many `gen/claims.json` marks
proved. Proofs against statements written
by hand are described on the [Proofs](../proofs/index.md#what-is-proved-and-in-which-model) page;
a reference page reports only the status of the claims.

## What the measured numbers are

The brute-force tier runs by hand on the test machines before each milestone report, a
*campaign*, and its summaries are stored under `results/`, one directory per campaign
(`results/milestone1/brute/`, `results/milestone2/brute/`). A program that shares no code with
the library or the generator, the *oracle*, judges every result in exact rational arithmetic
against the kernel's claims. A page shows every stored run of the kernel's code as it is now,
campaign by campaign, and their total when there are several:

- **compiled**: the C++ kernel, built with every compiler of the machines, scalar and packed code,
  under every contraction setting, on random operands of `binary64` (`double`) and `binary32`
  (`float`), drawn to include the hard cases (cancellation, ties, underflow, overflow);
- **toy formats**: the generator's exact interpreter on *every* operand of small formats, such as
  `fp:5:-3:2`, a format of 5 bits of precision
  ([Number formats](../developer/architecture.md#number-formats) explains the name).

A run counts only if it ran the code the kernel has now. The code of a kernel is its generated
C++: its functions in `include/kairn/gen/scalar.hpp`, `avx2.hpp` and `neon.hpp`, into which the
generator inlines every kernel it calls, and the functions of the generated headers that they
call (such as `abs_bits`), with comments, blank lines and indentation left out. For every commit
that a stored run names, `results/brute-code.json` keeps the SHA-256 of that code for every kernel,
written from the repository's history by `docs/tools/brute_code.py`; the page compares it with the
code of the tree it is written from. A kernel whose code changed shows only the runs of its new code
and names those it does not count; one whose code no stored run ran says so. A change of the claims
alone does not change the code: such a run is shown, the page says that it judged other claims, and
the total leaves it out. Which claims a run judged is decided the same way: the same file keeps the
SHA-256 of the kernel's entry of `gen/claims.json` at the run's commit, without the fields that say
where a claim comes from, which theorem proves it, whether that is proved and how many operations the
code has. The total adds the random cases of the compiled runs; an enumeration of a
toy domain (a format, and the operands it is restricted to) that an earlier run of the same code
enumerated judged the same operands again, and counts once.

The columns:

- **Cases judged**: for a statement on finite operands, the cases whose result has a finite leading
  limb. When it does not, the statement says nothing, so those cases are counted and not judged.
  When the page says that the runs judged the kernel in the extended domain, the cases with
  infinite and NaN operands and results are judged too. A kernel no run has judged says so.
- **Failed**: cases that violate a claim, or whose operands violate the requirements.
- **Largest error / bound**: over the judged cases, the largest $\lvert\text{error}\rvert$ divided
  by the bound the claim allows for that case; 1 is the bound itself. For a claim that the result is
  exact, "0 (exact)".
- **Bound attained**: whether some case reached the bound exactly (a ratio of exactly 1), in which
  case no smaller constant can be proved for that format.
- **Smallest slack of the radius** (balls): how far the returned radius is above the smallest radius
  that would contain the exact set, in units in the last place of the radius.

What they are not: a proof, or an estimate of how loose a bound is. Random operands find the worst
case of a bound only by luck, so a largest ratio of 0.75 says that no case beyond 0.75 was drawn,
not that none exists; the proof is what covers every case. The measurements test what the proofs
do not cover: the generated code, the compilers and the hardware. The complete results, with the
cases that attain each extreme, are in the report of each campaign:
[Brute force, Milestone 1](../developer/results/brute-milestone1.md) and
[Brute force, Milestone 2](../developer/results/brute-milestone2.md).

## How the pages are made

`python3 docs/tools/reference.py` writes the pages and the Reference part of the navigation;
`--check` fails when a committed page differs from what it would write, and runs in CI. The one
table written by hand, which public operation calls which kernel, is
`docs/tools/reference_operations.py` ([Documentation](../developer/documentation.md#reference-pages)).
