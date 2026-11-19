(* DRAFT of the statements about the IEEE model, written by hand in the form the generator
   is meant to print, one definition per statement as in proofs/gen/Statements.v. Nothing
   in this file is a proof; the theorems are in IeeeEFT.v, IeeeAdd22.v and IeeeMul22.v.

   Every statement is for all precisions prec from the kernel's minimum on and all emax
   with prec < emax (Flocq's condition), for every choice of the NaN returned by each
   operation, with rounding to nearest, ties to even. The format is the IEEE format of
   IeeeDraft.v: its smallest positive number is 2^emin with emin = 3 - emax - prec, and
   the real-model vocabulary (fmt, RN, u, eta, normalized_2 of Statements.v) is used
   with that emin.

   For an arithmetic kernel K whose statement in the real model is

       requires(inputs) -> let outputs := K inputs in ensures(inputs, outputs)

   three statements are printed. Here val x is the real value of a finite x, and
   "finite" means: neither an infinity nor a NaN.

   K_ieee_bridge_spec     finite inputs -> requires(val inputs) ->
                          finite (output limb 0) ->
                          every value computed by K is finite, and
                          val outputs = (real model of K) (val inputs)

   K_ieee_spec            finite inputs -> requires(val inputs) ->
                          finite (output limb 0) ->
                          the other outputs are finite, and ensures(val inputs, val outputs)

   K_ieee_finite_spec     finite inputs -> requires(val inputs) -> threshold ->
                          every value computed by K is finite

   The second follows from the first and from the theorem of the real model. "Every value
   computed by K" is the list of values of K's straight-line program (IeeeDraft.v). The
   threshold is the only part that is specific to a kernel.

   The three error-free transformations have one statement each, of the second kind, to
   which two_sum adds the exact condition under which its error term is finite. *)
From Stdlib Require Import Reals ZArith List.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Program IeeeBridge.
From Kairn Require IeeeDraft.
Import ListNotations.
Open Scope R_scope.

Section IeeeVocabulary.
Variable prec emax : Z.

(* The smallest exponent of the IEEE format: its smallest positive number is 2^ieee_emin. *)
Definition ieee_emin : Z := (3 - emax - prec)%Z.

(* x is a finite number: neither an infinity nor a NaN. *)
Definition finite (x : binary_float prec emax) : Prop := is_finite prec emax x = true.

(* The real value of a finite x (and 0 for the others, which no statement uses). *)
Definition val (x : binary_float prec emax) : R := B2R prec emax x.

(* The largest finite number. *)
Definition omega : R := bpow radix2 emax - bpow radix2 (emax - prec).

(* The NaN an operation returns, as a function of its one, two or three operands. *)
Definition nan1 : Type :=
  binary_float prec emax -> {x : binary_float prec emax | is_nan prec emax x = true}.
Definition nan2 : Type :=
  binary_float prec emax -> binary_float prec emax ->
  {x : binary_float prec emax | is_nan prec emax x = true}.
Definition nan3 : Type :=
  binary_float prec emax -> binary_float prec emax -> binary_float prec emax ->
  {x : binary_float prec emax | is_nan prec emax x = true}.

End IeeeVocabulary.

Arguments finite {prec emax} x.
Arguments val {prec emax} x.

(** * Error-free transformations *)

(* fast_two_sum. Under its requirement, a finite s gives a finite e and the statement of
   the real model. *)
Definition fast_two_sum_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax),
  (2 <= prec)%Z ->
  forall a b : binary_float prec emax,
  finite a -> finite b ->
  Rabs (val b) <= Rabs (val a) ->
  let '(s, e) := IeeeDraft.fast_two_sum prec emax nan_plus nan_minus a b in
  finite s ->
  finite e /\
  val s = RN (ieee_emin prec emax) prec (val a + val b) /\
  (val s + val e) = (val a + val b) /\
  normalized_2 (ieee_emin prec emax) prec (val s) (val e).

(* two_prod. A finite p gives a finite e and the statement of the real model. *)
Definition two_prod_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_opp : nan1 prec emax) (nan_fma : nan3 prec emax),
  (2 <= prec)%Z ->
  forall a b : binary_float prec emax,
  finite a -> finite b ->
  let '(p, e) := IeeeDraft.two_prod prec emax nan_opp nan_fma a b in
  finite p ->
  finite e /\
  val p = RN (ieee_emin prec emax) prec (val a * val b) /\
  Rabs ((val p + val e) - (val a * val b)) <= (1 / 2) * eta (ieee_emin prec emax) /\
  (((val a * val b) = 0 \/
    bpow radix2 (2 * prec - 1) * eta (ieee_emin prec emax) <= Rabs (val a * val b)) ->
   (val p + val e) = (val a * val b)).

(* two_sum. A finite s is the rounded sum. The error term e is finite exactly when s is
   finite and the second operation, bb = RN(s - a), does not overflow; this holds in
   particular when b is not the largest number or its opposite. When e is finite, the
   sum of s and e is exact. *)
Definition two_sum_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax),
  (2 <= prec)%Z ->
  forall a b : binary_float prec emax,
  finite a -> finite b ->
  let '(s, e) := IeeeDraft.two_sum prec emax nan_plus nan_minus a b in
  (finite s -> val s = RN (ieee_emin prec emax) prec (val a + val b)) /\
  (finite e <->
   finite s /\ Rabs (RN (ieee_emin prec emax) prec (val s - val a)) < bpow radix2 emax) /\
  (finite s -> Rabs (val b) < omega prec emax -> finite e) /\
  (finite e -> (val s + val e) = (val a + val b)).

(** * add_2_2 *)

Definition add_2_2_ieee_bridge_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp : nan1 prec emax) (nan_fma : nan3 prec emax),
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : binary_float prec emax,
  finite x0 -> finite x1 -> finite y0 -> finite y1 ->
  normalized_2 (ieee_emin prec emax) prec (val x0) (val x1) ->
  normalized_2 (ieee_emin prec emax) prec (val y0) (val y1) ->
  let '(z0, z1) := IeeeDraft.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  finite z0 ->
  Forall finite (run (stepB prec emax nan_plus nan_minus nan_opp nan_fma)
                     IeeeDraft.add_2_2_prog [x0; x1; y0; y1]) /\
  finite z1 /\
  (val z0, val z1)
  = add_2_2 (ieee_emin prec emax) prec tie_even (val x0) (val x1) (val y0) (val y1).

Definition add_2_2_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax),
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : binary_float prec emax,
  finite x0 -> finite x1 -> finite y0 -> finite y1 ->
  normalized_2 (ieee_emin prec emax) prec (val x0) (val x1) ->
  normalized_2 (ieee_emin prec emax) prec (val y0) (val y1) ->
  let '(z0, z1) := IeeeDraft.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  finite z0 ->
  finite z1 /\
  normalized_2 (ieee_emin prec emax) prec (val z0) (val z1) /\
  Rabs ((val z0 + val z1) - ((val x0 + val x1) + (val y0 + val y1)))
  <= (3 / (1 - (4 * u prec))) * u prec ^ 2 * Rabs ((val x0 + val x1) + (val y0 + val y1)).

(* Threshold: the leading limbs of both operands are at most 2^(emax - 2). *)
Definition add_2_2_ieee_finite_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp : nan1 prec emax) (nan_fma : nan3 prec emax),
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : binary_float prec emax,
  finite x0 -> finite x1 -> finite y0 -> finite y1 ->
  normalized_2 (ieee_emin prec emax) prec (val x0) (val x1) ->
  normalized_2 (ieee_emin prec emax) prec (val y0) (val y1) ->
  Rabs (val x0) <= bpow radix2 (emax - 2) ->
  Rabs (val y0) <= bpow radix2 (emax - 2) ->
  Forall finite (run (stepB prec emax nan_plus nan_minus nan_opp nan_fma)
                     IeeeDraft.add_2_2_prog [x0; x1; y0; y1]) /\
  let '(z0, z1) := IeeeDraft.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  finite z0 /\ finite z1.

(** * mul_2_2 *)

Definition mul_2_2_ieee_bridge_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp : nan1 prec emax) (nan_fma : nan3 prec emax),
  (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : binary_float prec emax,
  finite x0 -> finite x1 -> finite y0 -> finite y1 ->
  normalized_2 (ieee_emin prec emax) prec (val x0) (val x1) ->
  normalized_2 (ieee_emin prec emax) prec (val y0) (val y1) ->
  let '(z0, z1) := IeeeDraft.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 y0 y1 in
  finite z0 ->
  Forall finite (run (stepB prec emax nan_plus nan_minus nan_opp nan_fma)
                     IeeeDraft.mul_2_2_prog [x0; x1; y0; y1]) /\
  finite z1 /\
  (val z0, val z1)
  = mul_2_2 (ieee_emin prec emax) prec tie_even (val x0) (val x1) (val y0) (val y1).

Definition mul_2_2_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp : nan1 prec emax) (nan_fma : nan3 prec emax),
  (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : binary_float prec emax,
  finite x0 -> finite x1 -> finite y0 -> finite y1 ->
  normalized_2 (ieee_emin prec emax) prec (val x0) (val x1) ->
  normalized_2 (ieee_emin prec emax) prec (val y0) (val y1) ->
  let '(z0, z1) := IeeeDraft.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 y0 y1 in
  finite z0 ->
  finite z1 /\
  normalized_2 (ieee_emin prec emax) prec (val z0) (val z1) /\
  Rabs ((val z0 + val z1) - ((val x0 + val x1) * (val y0 + val y1)))
  <= 4 * u prec ^ 2 * Rabs ((val x0 + val x1) * (val y0 + val y1))
     + (3 / 2) * eta (ieee_emin prec emax).

(* Threshold: the exact product is at most 2^(emax - 1) in magnitude. *)
Definition mul_2_2_ieee_finite_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp : nan1 prec emax) (nan_fma : nan3 prec emax),
  (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : binary_float prec emax,
  finite x0 -> finite x1 -> finite y0 -> finite y1 ->
  normalized_2 (ieee_emin prec emax) prec (val x0) (val x1) ->
  normalized_2 (ieee_emin prec emax) prec (val y0) (val y1) ->
  Rabs ((val x0 + val x1) * (val y0 + val y1)) <= bpow radix2 (emax - 1) ->
  Forall finite (run (stepB prec emax nan_plus nan_minus nan_opp nan_fma)
                     IeeeDraft.mul_2_2_prog [x0; x1; y0; y1]) /\
  let '(z0, z1) := IeeeDraft.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 y0 y1 in
  finite z0 /\ finite z1.
