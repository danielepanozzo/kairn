(* The four operations of the round-up interval in the IEEE model
   (docs/developer/design/upward.md, "The operations of the IR" and "The maximum"). Written by
   hand; nothing in this file is a proof. The kernels of the family are generated
   (proofs/gen/UpwardModel.v), each as a function of these operations and of those of
   IeeeOperations.v (neg, abs, lt, le, eq, pzero, pinf, cnan), which keep their meaning; the
   facts about the four operations are in IeeeUpwardMax.v and IeeeUpwardOps.v.

   The format is that of IeeeOperations.v: Flocq's binary_float prec emax, with signed zeros,
   the two infinities and NaN. The kernels of the family compute under the rounding mode
   upward: their sums and products are Flocq's Bplus and Bmult with mode_UP, overflow
   included, so a finite result above the largest number Omega is +infinity and one below
   -Omega is -Omega. As in IeeeOperations.v, which NaN an operation returns is a function of
   its operands given as a variable of the section (nan_plus, nan_mult), hence a parameter of
   every definition that uses it, and not an axiom.

   Correspondence with the kernel descriptions (gen/kernels/upward_*.kernel), one operation
   each:
     add_ru a b   Bplus, mode_UP   IEEE 754's sum rounded toward +infinity
     mul_ru a b   Bmult, mode_UP   IEEE 754's product rounded toward +infinity
     unord a b                     a mask: a or b is a NaN
     max_nl a b                    the greater of a and b, b when a is a NaN: not one function
                                   but any function with the property max_nl_ok below; the
                                   generated model takes it as a variable of its section, and
                                   every statement that uses it quantifies over every such
                                   function with the hypothesis max_nl_ok.

   The maximum. The two machine instructions that compute max_nl in one instruction differ in
   the sign of a zero, and so the IR operation is specified by a property:
     - max_sel a b, if b < a then a else b: x86's MAXPD a, b (_mm_max_pd(a, b)), which returns
       its second operand when either operand is a NaN and when both are zeros; also the C++
       a > b ? a : b of the two-number form;
     - max_num a b: arm64's FMAXNM (vmaxnmq_f64(a, b)), the pseudocode FPMaxNum on operands
       whose NaNs are quiet: when exactly one operand is a NaN, the other; on two zeros, +0
       unless both are -0 (the sign is the "and" of the signs); otherwise the greater, the
       second operand when they are equal. When both are NaN, FPMaxNum returns a NaN (the
       first operand with the default-NaN mode off, which this definition takes); max_nl_ok
       says nothing of that case. Every NaN of this model is taken as quiet: the operands of a
       max_nl are results of mul_ru or lanes of canonical states (rule U5 of the design page),
       whose NaNs are quiet; that a signaling NaN never reaches FMAXNM is outside the proofs.
   The property max_nl_ok is exactly the design page's: for every b that is not a NaN, the
   result is b when a is a NaN; otherwise it is a or b, and it is at least both as an extended
   real number. IeeeUpwardMax.v proves it of max_sel and of max_num. *)
From Stdlib Require Import Reals ZArith Bool.
From Flocq Require Import Core Binary.
From Kairn Require Import IeeeVocabulary.
From Kairn Require IeeeOperations.

Section IeeeUpwardOperations.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.

(* The NaN returned by each operation, as a function of its operands. *)
Variable nan_plus : float -> float -> nan_of.
Variable nan_mult : float -> float -> nan_of.

(** * The operations that round *)

Definition add_ru (a b : float) : float :=
  Bplus prec emax prec_gt_0_ prec_lt_emax_ nan_plus BinarySingleNaN.mode_UP a b.
Definition mul_ru (a b : float) : float :=
  Bmult prec emax prec_gt_0_ prec_lt_emax_ nan_mult BinarySingleNaN.mode_UP a b.

(** * The NaN test *)

Definition unord (a b : float) : bool := orb (is_nan prec emax a) (is_nan prec emax b).

(** * The maximum in which a NaN first operand loses *)

Definition max_nl_ok (m : float -> float -> float) : Prop :=
  forall a b : float, ~ nan b ->
  (nan a -> m a b = b) /\
  (~ nan a -> (m a b = a \/ m a b = b) /\
               xle (xval a) (xval (m a b)) = true /\ xle (xval b) (xval (m a b)) = true).

(* x86's MAXPD a, b: a when a > b, otherwise b. *)
Definition max_sel (a b : float) : float :=
  if IeeeOperations.lt prec emax b a then a else b.

(* arm64's FMAXNM a, b on quiet NaNs (FPMaxNum): a NaN operand loses to a number; two zeros
   give the zero whose sign is the "and" of the signs; otherwise the greater, b when neither
   is greater. *)
Definition max_num (a b : float) : float :=
  if is_nan prec emax a then (if is_nan prec emax b then a else b)
  else if is_nan prec emax b then a
  else match a, b with
       | B754_zero _ _ sa, B754_zero _ _ sb => B754_zero prec emax (andb sa sb)
       | _, _ => if IeeeOperations.lt prec emax b a then a else b
       end.

End IeeeUpwardOperations.
