# Concepts

These pages explain the ideas a program relies on when it uses Kairn: what a number of several limbs
is, how many digits it has and at which magnitudes, how intervals, balls and ball vectors differ,
what a guarantee says and how it is established, what the library needs of the floating-point
environment, what it promises of values, threads and constant expressions, and how its functions on
arrays bound their error. They are for a programmer who knows C++ and knows that floating point
rounds, and who is deciding whether and how to use the library; each page starts from a small
program, and states each guarantee with its conditions and a link to where it is proved. The
[reference](../reference/index.md) has the details of every operation.

Read them in this order:

1. [Numbers of several limbs](expansions.md): a floating-point expansion, the sum of two `double`s
   that holds $1 + 2^{-60}$; what *normalized* means and why every guarantee needs it; one limb and
   two; what the operators return at overflow and for infinities and NaN, and `kairn::finite::`.
2. [Precision and magnitude](precision.md): how many bits each of the four types has, from which
   magnitude, and up to which one its operations are claimed finite; the error bound of each
   operation as it is proved; `float` limbs or `double` limbs.
3. [Intervals, balls and ball vectors: which to use](enclosures.md): what each stores and
   guarantees, how their arithmetic differs, what they cost and how wide they come out, what is
   exact, what is only certain and what is not claimed, one radius for many centers, and an
   algorithm written once for both intervals and balls.
4. [What "correct" means here](correctness.md): containment, error bounds and tightness; how a
   guarantee is established, by a proof about the generated model and by an independent check of the
   compiled code; what is proved in which model; what is not machine-checked; what *unverified*
   means, and how a program asks.
5. [The floating-point environment](environment.md): rounding to nearest, no flush to zero, what a
   compiler's contraction and fast-math do and what Kairn does about them, and the three checks,
   `kairn::environment_ok()`, `kairn::self_test()` and `KAIRN_CHECKS`.
6. [Values, threads and constant expressions](values.md): the types as plain values, what is safe
   from several threads, and what can be computed at compile time.
7. [Arrays](arrays.md): the containers and views, the packed type, the functions on arrays and the
   accumulator, how the error of a sum or a dot product grows with its length, and the order of
   summation.

## What the library does not have yet

Kairn is in development ([Status](../index.md#status)), and these pages describe only what its
headers have today: numbers of one and two limbs of `float` or `double`, intervals, balls and ball
vectors around them, and functions on arrays of them, on the CPU. The rest is planned for later
milestones and does not exist yet: three and four limbs, eight limbs and a number of limbs chosen at
run time; division, square root and the elementary functions; decimal input and output; code for
GPUs (CUDA and Metal), and with it any comparison of `float` and `double` limbs on a GPU;
conversions between limb types; matrix products (`gemv`, `gemm`); AVX-512 and the choice of an
instruction set at run time; and the C interface for other languages
([Plan](../developer/design/phase0/plan.md#milestones) says which milestone brings each). The
pages do not describe them.
