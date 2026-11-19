(* The operations of the IEEE model: what one operation of the kernel descriptions is over
   Flocq's type binary_float prec emax. Written by hand; nothing in this file is a proof.
   The kernels themselves are generated (proofs/gen/IeeeModel.v), each as a function of
   these operations; the facts about single operations are in IeeeOps.v.

   What it is. proofs/gen/Model.v defines each kernel over the real numbers, in a format
   with no largest number. The IEEE model defines the same kernels over binary_float prec
   emax: the finite numbers of the format with signed zeros, the two infinities, and NaN,
   with Flocq's definitions of the IEEE 754 operations, overflow included. Rounding is to
   nearest, ties to even (mode_NE).

   The format. binary_float prec emax is the IEEE format with precision prec whose
   numbers are below 2^emax in magnitude: the largest one is
   Omega = 2^emax - 2^(emax - prec), and the smallest positive one is 2^emin with
   emin = 3 - emax - prec. Flocq fixes this relation between the two ends of the range,
   as IEEE 754 does. binary64 is prec = 53, emax = 1024; binary32 is prec = 24,
   emax = 128. Flocq requires 0 < prec < emax. So, of the toy formats (p, qmin, qmax) of
   the test tools, this model covers those with qmin + qmax = 3 - 2 p.

   NaN. Which NaN an operation returns (its sign and payload) is not specified here:
   Flocq's operations take it as a function of the operands, and these functions are
   variables of the section below, hence parameters of every definition that uses them
   (the generated file declares the same variables in the same order). The NaN that
   `const nan` denotes is one more such variable. No statement depends on them. They are
   not axioms.

   Correspondence with the kernel descriptions (gen/kernels), one operation each:
     add a b      Bplus          a + b
     sub a b      Bminus         a - b
     neg a        Bopp           - a
     abs a        Babs           |a|
     fma a b c    Bfma           fma(a, b, c)
     fms a b c    Bfma, Bopp     fma(a, b, -c)
     prod a b     Bfma           fma(a, b, +0.0)
     times_inf t  Bmult          t * (+infinity), a multiplication of the format (not a
                                 fused operation): a NaN for a NaN or a zero t, and for
                                 any other t the infinity of the sign of t
     lt le eq     Bltb Bleb Beqb a mask is a bool; a comparison with a NaN is false
     and or not   andb orb negb
     select m a b                if m then a else b
     succ a       Bsucc          the next number above a: +infinity above the largest
                                 number, the smallest positive number above either zero,
                                 the largest negative number above -infinity
     pred a       Bpred          the next number below a
     guard a      Bplus          a + (+0): the value of a; a zero comes out as +0, an
                                 infinity is unchanged, a NaN stays a NaN
     0            pzero          +0
     const inf    pinf           +infinity
     const nan    cnan           a NaN
     const up(EXPR)
                  const_of       the number of the format whose value is the constant
                                 of the same name in the real model (proofs/gen/Model.v)
   The names are those of the generated files, which apply these operations to the
   variables of their own section. *)
From Stdlib Require Import Reals ZArith.
From Flocq Require Import Core Binary.

Section IeeeOperations.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.

(* The NaN returned by each operation, as a function of its operands. *)
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_opp : float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.
Variable nan_mult : float -> float -> nan_of.
(* The NaN that `const nan` denotes. *)
Variable nan_const : nan_of.

(** * The operations *)

Definition pzero : float := B754_zero prec emax false.
Definition pinf : float := B754_infinity prec emax false.
Definition cnan : float := proj1_sig nan_const.

Definition add (a b : float) : float :=
  Bplus prec emax prec_gt_0_ prec_lt_emax_ nan_plus BinarySingleNaN.mode_NE a b.
Definition sub (a b : float) : float :=
  Bminus prec emax prec_gt_0_ prec_lt_emax_ nan_minus BinarySingleNaN.mode_NE a b.
Definition neg (a : float) : float :=
  Bopp prec emax nan_opp a.
Definition fma (a b c : float) : float :=
  Bfma prec emax prec_gt_0_ prec_lt_emax_ nan_fma BinarySingleNaN.mode_NE a b c.
Definition fms (a b c : float) : float := fma a b (neg c).
Definition prod (a b : float) : float := fma a b pzero.
Definition times_inf (t : float) : float :=
  Bmult prec emax prec_gt_0_ prec_lt_emax_ nan_mult BinarySingleNaN.mode_NE t pinf.
Definition abs (a : float) : float :=
  Babs prec emax nan_abs a.
Definition lt (a b : float) : bool :=
  @BinarySingleNaN.Bltb prec emax (B2BSN prec emax a) (B2BSN prec emax b).
Definition le (a b : float) : bool :=
  @BinarySingleNaN.Bleb prec emax (B2BSN prec emax a) (B2BSN prec emax b).
Definition eq (a b : float) : bool :=
  @BinarySingleNaN.Beqb prec emax (B2BSN prec emax a) (B2BSN prec emax b).
Definition succ (a : float) : float :=
  Bsucc prec emax prec_gt_0_ prec_lt_emax_ a.
Definition pred (a : float) : float :=
  Bpred prec emax prec_gt_0_ prec_lt_emax_ a.
Definition guard (a : float) : float := add a pzero.

(* The number of the format whose value is r, for a real number r that is one (r is a
   number of the format with no largest number, and below 2^emax in magnitude); for any
   other r, some number. The constants of the Ball kernels are given this way, from their
   definitions in the real model (proofs/gen/Model.v). *)
Definition const_of (r : R) : float :=
  binary_normalize prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_NE
    (Ztrunc (scaled_mantissa radix2 (FLT_exp (3 - emax - prec) prec) r))
    (cexp radix2 (FLT_exp (3 - emax - prec) prec) r) false.

End IeeeOperations.
