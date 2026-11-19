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

## The parts of a page

**What it computes.** The exact value the result stands for, as a formula of the operands. For an
arithmetic kernel the result approximates it; for a comparison it is a truth value; for a
conversion, a rounding; for a ball, the set of every result the operation can have on points of the
operands.

**C++.** The expressions that reach the kernel, with the type of each operand: `T` is `float` or
`double`, `Expansion<T, 2>` a number of two limbs, `Ball<T, 1>` a ball whose center has one limb.
A form marked as converted reaches the kernel through an exact conversion of an operand (a limb to
a one-limb number, a one-limb number to two limbs, a point to a ball of radius 0). A building
block has no form: it is a step of other kernels.

**Requires.** What the operands must satisfy for the guarantee to apply. Every operand is finite.
Every operation of Kairn returns normalized numbers, so the requirement that an operand be
normalized can fail only for a number built with `from_limbs_unchecked` or by writing its limbs
directly. In a build with `KAIRN_CHECKS` (the default without `NDEBUG`), every operation checks it
and stops the program if it fails.

**Guarantees.** The statement, then its constants. For a bound, the table gives $c\,u^k$ and
$t\,\eta$ for `double` and `float`, exactly and approximately, and the constants that
`kairn::traits` exports: the same numbers rounded up to `T`, and the bound relative to the computed
value instead of the exact one (what a running error analysis needs). Last, the smallest precision
for which the statement is proved.

**Status.** *Proved*, with the theorem's name and its file; or *UNVERIFIED*, marked at the top of
the page (below).

**Source.** Where the algorithm comes from and under which license, as the kernel's description
gives them. The references are on the [References](../developer/design/phase0/references.md) page.

**Listing.** The kernel as the generator reads it: one operation of `T` per line, each rounded to
nearest. The C++ and the formal model are both printed from it.

**Measured.** What the latest brute-force runs found, explained [below](#what-the-measured-numbers-are).

**Not claimed.** What the statement does not cover. For every kernel today: operands that are
infinite or NaN, and results that overflow; [What holds today](../getting-started/guarantees.md#overflow-and-non-finite-values)
says what is known there.

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

An **UNVERIFIED** kernel has a statement that the oracle tests but no checked proof. Its page says
so at the top, its guarantee is called a target, an operation that calls it compiles only with the
marker `kairn::unverified` on an operand, and `kairn::traits` exports no constants for it
([What holds today](../getting-started/guarantees.md#proved-and-unverified)).

## What the measured numbers are

The brute-force tier runs by hand on the test machines, and its summaries are stored under
`results/`. A program that shares no code with the library or the generator, the *oracle*, judges
every result in exact rational arithmetic against the kernel's claims. A page shows the latest
runs:

- **compiled**: the C++ kernel, built with every compiler of the machines, scalar and packed code,
  under every contraction setting, on random operands of `binary64` (`double`) and `binary32`
  (`float`), drawn to include the hard cases (cancellation, ties, underflow, overflow);
- **toy formats**: the generator's exact interpreter on *every* operand of small formats, such as
  `fp:5:-3:2`, a format of 5 bits of precision
  ([Number formats](../developer/architecture.md#number-formats) explains the name).

The columns:

- **Cases judged**: the cases whose result has a finite leading limb. When it does not, the claims
  say nothing, so those cases are counted and not judged.
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
do not cover: the generated code, the compilers and the hardware. If the claims change after a run,
the page says that the run judged other claims. The complete results, with the cases that attain
each extreme, are in [Brute force, Milestone 1](../developer/results/brute-milestone1.md).

## How the pages are made

`python3 docs/tools/reference.py` writes the pages and the Reference part of the navigation;
`--check` fails when a committed page differs from what it would write, and runs in CI. The one
table written by hand, which public operation calls which kernel, is
`docs/tools/reference_operations.py` ([Documentation](../developer/documentation.md#reference-pages)).
