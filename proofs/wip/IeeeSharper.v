(* NOT PROVED. Statements about the IEEE model that exhaustive enumeration of toy formats
   supports and that are sharper than what theories/IeeeAdd22.v, theories/IeeeAdd22Top.v
   and theories/IeeeEFT.v prove. This file contains definitions only; what is missing is
   every proof. It is outside the default build and the audit.

   Enumeration: all finite normalized operands of the toy formats (prec, emin, emax) =
   (3, -6, 6), (4, -8, 7), (5, -10, 8) (the IEEE shape emin = 3 - emax - prec), and
   (4, -2, 9); no violation of either statement.

   A third statement was here and is now proved, in theories/IeeeAdd22Top.v
   (add_2_2_ieee_finite_half, with its statement add_2_2_ieee_finite_half_spec as it was
   written here): add_2_2 does not overflow when the leading limbs of both operands are
   below 2^(emax - 1) in magnitude, that is, at most Omega/2. The proved threshold was
   2^(emax - 2). This one is optimal: at |x0| = |y0| = 2^(emax - 1) the first sum
   overflows.

   1. add_2_2_ieee_finite_sum_spec: add_2_2 does not overflow when the exact sum is at
      most 2^(emax - 1) in magnitude, whatever the operands. The smallest exact sum
      with an overflow is 0.71, 0.59, 0.54 times Omega at precisions 3, 4, 5: it comes
      from the two_sum corner below (y0 = -+Omega) and tends to Omega/2 from above.
      (theories/IeeeRange.v proves it for an exact sum of at most 2^(emax - 2).)

   2. two_sum_overflow_spec: the exact set of operands for which two_sum returns a
      finite s and a non-finite e. theories/IeeeEFT.v proves that this happens exactly
      when RN(s - a) overflows, and that it cannot happen unless |b| = Omega. *)
From Stdlib Require Import Reals ZArith List.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Program IeeeBridge IeeeVocabulary.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Import ListNotations.
Open Scope R_scope.

Definition add_2_2_ieee_finite_sum_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax),
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : binary_float prec emax,
  finite x0 -> finite x1 -> finite y0 -> finite y1 ->
  normalized_2 (ieee_emin prec emax) prec (val x0) (val x1) ->
  normalized_2 (ieee_emin prec emax) prec (val y0) (val y1) ->
  Rabs ((val x0 + val x1) + (val y0 + val y1)) <= bpow radix2 (emax - 1) ->
  let '(z0, z1) := IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  finite z0 /\ finite z1.

Definition two_sum_overflow_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax),
  (2 <= prec)%Z ->
  forall a b : binary_float prec emax,
  finite a -> finite b ->
  let '(s, e) := IeeeModel.two_sum prec emax nan_plus nan_minus a b in
  (finite s /\ ~ finite e) <->
  (Rabs (val b) = omega prec emax /\ val a * val b < 0 /\
   exists j : Z, (1 <= j < 2 ^ (prec - 2))%Z /\
   Rabs (val a) = (2 * IZR j - 1 / 2) * bpow radix2 (emax - prec)).
