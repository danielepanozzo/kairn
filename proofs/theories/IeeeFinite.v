(* No overflow below a threshold, in the IEEE model, for the kernels other than add_2_2
   and mul_2_2 (whose statements of this kind are in IeeeAdd22.v and IeeeMul22.v): the
   third statement of each kernel in proofs/gen/IeeeStatements.v.

     additions and subtractions (add_2_2, add_fast_2_2, add_2_1, sub_2_2, sub_2_1,
     sub_1_2): every value is finite when the leading limbs of both operands are at most
     2^(emax - 2) in magnitude (K_ieee_finite), and also when the exact result is at most
     2^(emax - 2) in magnitude, whatever the operands (K_ieee_finite_result).

     products (mul_2_1, mul_pow2_2): every value is finite when the exact product is at
     most 2^(emax - 1) in magnitude (K_ieee_finite).

   The work is in IeeeRange.v, which bounds every value of the real model under these
   conditions; here the simulation of IeeeBridge.v (a run of the IEEE model is finite
   exactly when the run of the real model stays in range) turns the bounds into
   finiteness. A subtraction is the addition of the opposite: its leading limb is finite
   by the addition's bounds, and then its bridge says that every value is. *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized EFT Program IeeeBridge IeeeEFT IeeeAdd22 IeeeMul22
  IeeeMore IeeeSub IeeeVocabulary IeeeOps IeeeRange IeeeFull.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Import ListNotations.
Open Scope R_scope.

Section IeeeFinite.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_opp : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation inrange := (inrange emax).
Notation stB := (stepB prec emax nan_plus nan_minus nan_opp nan_fma).
Notation runB := (run stB).
Notation runR := (runR emin prec tie_even).
Notation d0 := (d0 prec emax).
Notation finite_all := (Forall (fun x : float => fin x)).
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation Q := (bpow radix2 (emax - 2)).

(* A run that stays in range: every value is finite, the two outputs among them. *)
Lemma finite_run :
  forall (p : list instr) (e : list float) (i j : nat),
  finite_all e -> Forall inrange (runR p (map b2r e)) ->
  finite_all (runB p e) /\ fin (nth i (runB p e) d0) /\ fin (nth j (runB p e) d0).
Proof.
intros p e i j Fe R.
assert (F : finite_all (runB p e)).
{ apply (run_sim prec emax nan_plus nan_minus nan_opp nan_fma p e Fe). exact R. }
split; [exact F|split; now apply (nth_fin prec emax)].
Qed.

(** * The additions and the products *)

Lemma add_2_2_finite_of_range :
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  Forall inrange (runR IeeeModel.add_2_2_prog [b2r x0; b2r x1; b2r y0; b2r y1]) ->
  finite_all (runB IeeeModel.add_2_2_prog [x0; x1; y0; y1]) /\
  let '(z0, z1) := IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  fin z0 /\ fin z1.
Proof.
intros x0 x1 y0 y1 F0 F1 G0 G1 R.
assert (Fe : finite_all [x0; x1; y0; y1]) by (repeat constructor; assumption).
rewrite (add_2_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
exact (finite_run IeeeModel.add_2_2_prog _ 21 23 Fe R).
Qed.

Lemma add_fast_2_2_finite_of_range :
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  Forall inrange (runR IeeeModel.add_fast_2_2_prog [b2r x0; b2r x1; b2r y0; b2r y1]) ->
  finite_all (runB IeeeModel.add_fast_2_2_prog [x0; x1; y0; y1]) /\
  let '(z0, z1) := IeeeModel.add_fast_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  fin z0 /\ fin z1.
Proof.
intros x0 x1 y0 y1 F0 F1 G0 G1 R.
assert (Fe : finite_all [x0; x1; y0; y1]) by (repeat constructor; assumption).
rewrite (add_fast_2_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
exact (finite_run IeeeModel.add_fast_2_2_prog _ 12 14 Fe R).
Qed.

Lemma add_2_1_finite_of_range :
  forall x0 x1 a : float, fin x0 -> fin x1 -> fin a ->
  Forall inrange (runR IeeeModel.add_2_1_prog [b2r x0; b2r x1; b2r a]) ->
  finite_all (runB IeeeModel.add_2_1_prog [x0; x1; a]) /\
  let '(z0, z1) := IeeeModel.add_2_1 prec emax nan_plus nan_minus x0 x1 a in
  fin z0 /\ fin z1.
Proof.
intros x0 x1 a F0 F1 Fa R.
assert (Fe : finite_all [x0; x1; a]) by (repeat constructor; assumption).
rewrite (add_2_1_runB prec emax nan_plus nan_minus nan_opp nan_fma).
exact (finite_run IeeeModel.add_2_1_prog _ 11 13 Fe R).
Qed.

Lemma mul_2_1_finite_of_range :
  forall x0 x1 a : float, fin x0 -> fin x1 -> fin a ->
  Forall inrange (runR IeeeModel.mul_2_1_prog [b2r x0; b2r x1; b2r a]) ->
  finite_all (runB IeeeModel.mul_2_1_prog [x0; x1; a]) /\
  let '(z0, z1) := IeeeModel.mul_2_1 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 a in
  fin z0 /\ fin z1.
Proof.
intros x0 x1 a F0 F1 Fa R.
assert (Fe : finite_all [x0; x1; a]) by (repeat constructor; assumption).
rewrite (mul_2_1_runB prec emax nan_plus nan_minus nan_opp nan_fma).
exact (finite_run IeeeModel.mul_2_1_prog _ 6 8 Fe R).
Qed.

Lemma mul_pow2_2_finite_of_range :
  forall x0 x1 c : float, fin x0 -> fin x1 -> fin c ->
  Forall inrange (runR IeeeModel.mul_pow2_2_prog [b2r x0; b2r x1; b2r c]) ->
  finite_all (runB IeeeModel.mul_pow2_2_prog [x0; x1; c]) /\
  let '(z0, z1) := IeeeModel.mul_pow2_2 prec emax nan_plus nan_minus nan_fma x0 x1 c in
  fin z0 /\ fin z1.
Proof.
intros x0 x1 c F0 F1 Fc R.
assert (Fe : finite_all [x0; x1; c]) by (repeat constructor; assumption).
rewrite (mul_pow2_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
exact (finite_run IeeeModel.mul_pow2_2_prog _ 5 7 Fe R).
Qed.

(** * The subtractions *)

Lemma neg_normalized :
  forall y0 y1 : float, normalized_2 emin prec (b2r y0) (b2r y1) ->
  normalized_2 emin prec (b2r (neg y0)) (b2r (neg y1)).
Proof.
intros y0 y1 N. rewrite 2!(neg_val prec emax nan_opp). now apply normalized_2_opp.
Qed.

Lemma sub_2_2_finite_of_range :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  Forall inrange (runR IeeeModel.add_2_2_prog [b2r x0; b2r x1; b2r (neg y0); b2r (neg y1)]) ->
  finite_all (runB IeeeModel.sub_2_2_prog [x0; x1; y0; y1]) /\
  let '(z0, z1) := IeeeModel.sub_2_2 prec emax nan_plus nan_minus nan_opp x0 x1 y0 y1 in
  fin z0 /\ fin z1.
Proof.
intros Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny R.
assert (G0' : fin (neg y0)) by now rewrite (neg_fin prec emax nan_opp).
assert (G1' : fin (neg y1)) by now rewrite (neg_fin prec emax nan_opp).
generalize (sub_2_2_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_opp nan_fma Hp
              x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny)
           (add_2_2_finite_of_range x0 x1 (neg y0) (neg y1) F0 F1 G0' G1' R).
rewrite (sub_2_2_eq prec emax nan_plus nan_minus nan_opp).
destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 (neg y0) (neg y1)) as [z0 z1].
intros B [_ [Fz _]]. destruct (B Fz) as [A [Fz1 _]].
split; [exact A|split; assumption].
Qed.

Lemma sub_2_1_finite_of_range :
  (3 <= prec)%Z ->
  forall x0 x1 a : float, fin x0 -> fin x1 -> fin a ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  Forall inrange (runR IeeeModel.add_2_1_prog [b2r x0; b2r x1; b2r (neg a)]) ->
  finite_all (runB IeeeModel.sub_2_1_prog [x0; x1; a]) /\
  let '(z0, z1) := IeeeModel.sub_2_1 prec emax nan_plus nan_minus nan_opp x0 x1 a in
  fin z0 /\ fin z1.
Proof.
intros Hp x0 x1 a F0 F1 Fa Nx R.
assert (Fa' : fin (neg a)) by now rewrite (neg_fin prec emax nan_opp).
generalize (sub_2_1_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_opp nan_fma Hp
              x0 x1 a F0 F1 Fa Nx)
           (add_2_1_finite_of_range x0 x1 (neg a) F0 F1 Fa' R).
rewrite (sub_2_1_eq prec emax nan_plus nan_minus nan_opp).
destruct (IeeeModel.add_2_1 prec emax nan_plus nan_minus x0 x1 (neg a)) as [z0 z1].
intros B [_ [Fz _]]. destruct (B Fz) as [A [Fz1 _]].
split; [exact A|split; assumption].
Qed.

Lemma sub_1_2_finite_of_range :
  (3 <= prec)%Z ->
  forall a y0 y1 : float, fin a -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r y0) (b2r y1) ->
  Forall inrange (runR IeeeModel.add_2_1_prog [b2r (neg y0); b2r (neg y1); b2r a]) ->
  finite_all (runB IeeeModel.sub_1_2_prog [a; y0; y1]) /\
  let '(z0, z1) := IeeeModel.sub_1_2 prec emax nan_plus nan_minus nan_opp a y0 y1 in
  fin z0 /\ fin z1.
Proof.
intros Hp a y0 y1 Fa G0 G1 Ny R.
assert (G0' : fin (neg y0)) by now rewrite (neg_fin prec emax nan_opp).
assert (G1' : fin (neg y1)) by now rewrite (neg_fin prec emax nan_opp).
generalize (sub_1_2_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus nan_opp nan_fma Hp
              a y0 y1 Fa G0 G1 Ny)
           (add_2_1_finite_of_range (neg y0) (neg y1) a G0' G1' Fa R).
rewrite (sub_1_2_eq prec emax nan_plus nan_minus nan_opp).
destruct (IeeeModel.add_2_1 prec emax nan_plus nan_minus (neg y0) (neg y1) a) as [z0 z1].
intros B [_ [Fz _]]. destruct (B Fz) as [A [Fz1 _]].
split; [exact A|split; assumption].
Qed.

End IeeeFinite.

(** * The statements of proofs/gen/IeeeStatements.v *)

Theorem add_2_2_ieee_finite_result : add_2_2_ieee_finite_result_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hs.
exact (add_2_2_finite_of_range prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 y0 y1
         F0 F1 G0 G1 (add_2_2_range_sum prec emax Hp3 x0 x1 y0 y1 Nx Ny Hs)).
Qed.

Theorem add_fast_2_2_ieee_finite : add_fast_2_2_ieee_finite_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny
  Hx Hy.
exact (add_fast_2_2_finite_of_range prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 y0 y1
         F0 F1 G0 G1 (add_fast_2_2_range prec emax Hp2 x0 x1 y0 y1 Nx Ny Hx Hy)).
Qed.

Theorem add_fast_2_2_ieee_finite_result : add_fast_2_2_ieee_finite_result_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hs.
exact (add_fast_2_2_finite_of_range prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 y0 y1
         F0 F1 G0 G1 (add_fast_2_2_range_sum prec emax Hp2 x0 x1 y0 y1 Nx Ny Hs)).
Qed.

Theorem sub_2_2_ieee_finite : sub_2_2_ieee_finite_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny
  Hx Hy.
apply (sub_2_2_finite_of_range prec emax nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 y0 y1
         F0 F1 G0 G1 Nx Ny).
apply (add_2_2_range prec emax Hp3 x0 x1); trivial.
- now apply neg_normalized.
- rewrite (neg_val prec emax nan_opp), Rabs_Ropp. exact Hy.
Qed.

Theorem sub_2_2_ieee_finite_result : sub_2_2_ieee_finite_result_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hs.
apply (sub_2_2_finite_of_range prec emax nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 y0 y1
         F0 F1 G0 G1 Nx Ny).
apply (add_2_2_range_sum prec emax Hp3 x0 x1); trivial.
- now apply neg_normalized.
- rewrite 2!(neg_val prec emax nan_opp).
  replace (B2R prec emax x0 + B2R prec emax x1 + (- B2R prec emax y0 + - B2R prec emax y1))
    with (B2R prec emax x0 + B2R prec emax x1 - (B2R prec emax y0 + B2R prec emax y1)) by ring.
  exact Hs.
Qed.

Theorem add_2_1_ieee_finite : add_2_1_ieee_finite_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 a F0 F1 Fa Nx Hx Ha.
exact (add_2_1_finite_of_range prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 a
         F0 F1 Fa (add_2_1_range prec emax Hp3 x0 x1 a Nx Hx Ha)).
Qed.

Theorem add_2_1_ieee_finite_result : add_2_1_ieee_finite_result_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 a F0 F1 Fa Nx Hs.
exact (add_2_1_finite_of_range prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 a
         F0 F1 Fa (add_2_1_range_sum prec emax Hp3 x0 x1 a Nx Hs)).
Qed.

Theorem sub_2_1_ieee_finite : sub_2_1_ieee_finite_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 a F0 F1 Fa Nx Hx Ha.
apply (sub_2_1_finite_of_range prec emax nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 a
         F0 F1 Fa Nx).
apply (add_2_1_range prec emax Hp3 x0 x1); trivial.
rewrite (neg_val prec emax nan_opp), Rabs_Ropp. exact Ha.
Qed.

Theorem sub_2_1_ieee_finite_result : sub_2_1_ieee_finite_result_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 a F0 F1 Fa Nx Hs.
apply (sub_2_1_finite_of_range prec emax nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 a
         F0 F1 Fa Nx).
apply (add_2_1_range_sum prec emax Hp3 x0 x1); trivial.
rewrite (neg_val prec emax nan_opp). exact Hs.
Qed.

Theorem sub_1_2_ieee_finite : sub_1_2_ieee_finite_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp3 a y0 y1 Fa G0 G1 Ny Ha Hy.
apply (sub_1_2_finite_of_range prec emax nan_plus nan_minus nan_opp nan_fma Hp3 a y0 y1
         Fa G0 G1 Ny).
apply (add_2_1_range prec emax Hp3); trivial.
- now apply neg_normalized.
- rewrite (neg_val prec emax nan_opp), Rabs_Ropp. exact Hy.
Qed.

Theorem sub_1_2_ieee_finite_result : sub_1_2_ieee_finite_result_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp3 a y0 y1 Fa G0 G1 Ny Hs.
apply (sub_1_2_finite_of_range prec emax nan_plus nan_minus nan_opp nan_fma Hp3 a y0 y1
         Fa G0 G1 Ny).
apply (add_2_1_range_sum prec emax Hp3); trivial.
- now apply neg_normalized.
- rewrite 2!(neg_val prec emax nan_opp).
  replace (- B2R prec emax y0 + - B2R prec emax y1 + B2R prec emax a)
    with (B2R prec emax a - (B2R prec emax y0 + B2R prec emax y1)) by ring.
  exact Hs.
Qed.

Theorem mul_2_1_ieee_finite : mul_2_1_ieee_finite_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 a F0 F1 Fa Nx Hs.
exact (mul_2_1_finite_of_range prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 a
         F0 F1 Fa (mul_2_1_range prec emax Hp2 x0 x1 a Nx Hs)).
Qed.

(* mul_pow2_2 for any finite scalar: the threshold does not need c to be a power of two.
   This statement is written by hand; the generated one, below, has the kernel's
   requirement on c as one more hypothesis and follows from it. *)
Definition mul_pow2_2_ieee_finite_any_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp : nan1 prec emax) (nan_fma : nan3 prec emax),
  (2 <= prec)%Z ->
  forall x0 x1 c : binary_float prec emax,
  finite x0 -> finite x1 -> finite c ->
  normalized_2 (ieee_emin prec emax) prec (val x0) (val x1) ->
  Rabs ((val x0 + val x1) * val c) <= bpow radix2 (emax - 1) ->
  Forall finite (run (stepB prec emax nan_plus nan_minus nan_opp nan_fma)
                     IeeeModel.mul_pow2_2_prog [x0; x1; c]) /\
  let '(z0, z1) := IeeeModel.mul_pow2_2 prec emax nan_plus nan_minus nan_fma x0 x1 c in
  finite z0 /\ finite z1.

Theorem mul_pow2_2_ieee_finite_any : mul_pow2_2_ieee_finite_any_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 c F0 F1 Fc Nx Hs.
exact (mul_pow2_2_finite_of_range prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 c
         F0 F1 Fc (mul_pow2_2_range prec emax Hp2 x0 x1 c Nx Hs)).
Qed.

Theorem mul_pow2_2_ieee_finite : mul_pow2_2_ieee_finite_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 c F0 F1 Fc Nx _ Hs.
exact (mul_pow2_2_ieee_finite_any prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp2
         x0 x1 c F0 F1 Fc Nx Hs).
Qed.
