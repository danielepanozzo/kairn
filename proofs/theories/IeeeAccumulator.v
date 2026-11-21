(* What a user of the accumulator relies on, in the IEEE model.

   Accumulator.v proves the guarantee in the real model: after any history (a tree of
   add, add_product and merge) of numbers of the format, |s - sum terms| <= r, with r the
   radius of error_bound(). This file runs the same history on Flocq's binary
   floating-point numbers, with the kernels of the IEEE model (proofs/gen/IeeeModel.v:
   overflow, infinities and NaN), from the state of a new accumulator (+0 in every limb),
   and proves, for one limb:

   - run1i_real: if every element is finite and the final s and a are finite, then every
     state on the way was finite and the final state has the values of the real model's
     run on the values of the elements. A non-finite operand of an addition or a fused
     operation makes its result non-finite (add_finite_inv, fma_finite_inv of IeeeBridge.v),
     so a finite result means finite operands, and then the IEEE result is the rounded
     exact result (add_spec, fma_spec).
   - bound_dot_1_real: if the t of bound_dot_1 is finite, so is every value it computes,
     and (g, t, ok) is the real model's; acc_radius_1_inputs: a finite r of acc_radius_1
     means finite g and t; acc_radius_1_ok_finite: a true mask of acc_radius_1 means a
     finite a, since a - a is a NaN for a = +inf or a NaN (the check A5 of
     experiments/milestone2/accumulator.py, as a theorem); and acc_radius_1_real
     (IeeeAccKernels.v): a finite r is the real model's.
   - acc_1_ieee_bound: if every element is finite, the final s and r are finite and both
     masks are true, then |s - sum terms| <= r: the real theorem acc_1_bound on the values.
     A format of the IEEE model contains 1/2 (emin <= -2), which bound_dot_1 requires.

   For two limbs the same (run2i_real, bound_dot_2_real, acc_2_ieee_bound), for elements
   whose two limbs are finite and whose values are a normalized pair, the leading limb of
   the final running sum finite: then its second limb is finite too. The sums of two limbs
   are add_2_2, sum_entry_step_2 and dot_step_2 of the IEEE model, whose leading limb is
   not finite unless that of the state is (add_2_2_lead, dot_step_2_lead), and which from
   finite normalized operands give the real model's values when their leading limb is
   finite (add_2_2_values of IeeeAdd22.v, sum_entry_step_2_values and dot_step_2_values of
   IeeeSteps.v); the states are normalized by acc_2_mags of the real run.

   What it does not say: anything when s or r is not finite, or a mask is false (the
   header then returns the whole line, which is not proved here). *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Guard Program IeeeBridge IeeeVocabulary IeeeOps IeeeAdd22 IeeeSteps
  IeeeFolds AccKernels IeeeAccKernels Summation SummationKernels Accumulator.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Import ListNotations.
Open Scope R_scope.

(** * A history of other elements *)

Fixpoint hmap {A B : Type} (f : A -> B) (h : hist A) : hist B :=
  match h with
  | Hnil => Hnil
  | Hadd h x => Hadd (hmap f h) (f x)
  | Hmul h x y => Hmul (hmap f h) (f x) (f y)
  | Hmerge h1 h2 => Hmerge (hmap f h1) (hmap f h2)
  end.

Lemma count_hmap : forall (A B : Type) (f : A -> B) (h : hist A), count (hmap f h) = count h.
Proof.
intros A B f. induction h as [|h IH x|h IH x y|h1 IH1 h2 IH2]; cbn [hmap count]; lia.
Qed.

Lemma terms_hmap :
  forall (A B : Type) (f : A -> B) (v : B -> R) (h : hist A),
  terms v (hmap f h) = terms (fun x => v (f x)) h.
Proof.
intros A B f v. induction h as [|h IH x|h IH x y|h1 IH1 h2 IH2]; cbn [hmap terms];
  congruence.
Qed.

Lemma elems_hmap :
  forall (A B : Type) (f : A -> B) (P : A -> Prop) (Q : B -> Prop),
  (forall x, P x -> Q (f x)) -> forall h : hist A, elems P h -> elems Q (hmap f h).
Proof.
intros A B f P Q H. induction h as [|h IH x|h IH x y|h1 IH1 h2 IH2]; cbn [hmap elems]; intros V.
- exact I.
- destruct V as [Vh Px]. split. exact (IH Vh). exact (H x Px).
- destruct V as [Vh [Px Py]]. split. exact (IH Vh). split; [exact (H x Px) | exact (H y Py)].
- destruct V as [V1 V2]. split; [exact (IH1 V1) | exact (IH2 V2)].
Qed.

Section IeeeOne.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation sub := (IeeeOperations.sub prec emax nan_minus).
Notation fma := (IeeeOperations.fma prec emax nan_fma).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation guard := (IeeeOperations.guard prec emax nan_plus).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation pzero := (IeeeOperations.pzero prec emax).

(* The state after a history, in the IEEE model. *)
Fixpoint run1i (h : hist float) : float * float :=
  match h with
  | Hnil => (pzero, pzero)
  | Hadd h x => let '(s, a) := run1i h in IeeeModel.acc_add_1 prec emax nan_plus nan_abs s a x
  | Hmul h x y =>
      let '(s, a) := run1i h in IeeeModel.acc_mul_entry_1 prec emax nan_plus nan_abs nan_fma s a x y
  | Hmerge h1 h2 =>
      let '(s, a) := run1i h1 in let '(v, c) := run1i h2 in
      IeeeModel.acc_merge_1 prec emax nan_plus s a v c
  end.

(* A finite final state: the real model's run on the values. *)
Lemma run1i_real :
  forall h : hist float, elems (fun x => fin x) h ->
  fin (fst (run1i h)) -> fin (snd (run1i h)) ->
  (b2r (fst (run1i h)), b2r (snd (run1i h))) = run1 (ieee_emin prec emax) prec (hmap b2r h).
Proof.
induction h as [|h IH x|h IH x y|h1 IH1 h2 IH2]; cbn [elems run1i hmap run1].
- intros _ _ _. reflexivity.
- intros [Vh Fx]. destruct (run1i h) as [s a]. cbn [fst snd] in IH.
  unfold IeeeModel.acc_add_1. cbv beta iota zeta. cbn [fst snd]. intros Ft Fb.
  destruct (add_finite_inv prec emax nan_plus _ _ Ft) as [Fs Fg].
  destruct (add_finite_inv prec emax nan_plus _ _ Fb) as [Fa Fag].
  rewrite <- (IH Vh Fs Fa). cbv beta iota.
  unfold acc_add_1, ieee_emin. cbv zeta.
  rewrite (guard_real_any _ prec tie_even (b2r x) (b2r_format prec emax x)).
  rewrite (proj2 (add_spec prec emax nan_plus s _ Fs Fg) Ft).
  rewrite (proj2 (add_spec prec emax nan_plus a _ Fa Fag) Fb).
  rewrite (abs_val prec emax nan_abs), (guard_val prec emax nan_plus). reflexivity.
- intros [Vh [Fx Fy]]. destruct (run1i h) as [s a]. cbn [fst snd] in IH.
  unfold IeeeModel.acc_mul_entry_1. cbv beta iota zeta. cbn [fst snd]. intros Ft Fb.
  destruct (fma_finite_inv prec emax nan_fma _ _ _ Ft) as [_ [_ Fs]].
  destruct (fma_finite_inv prec emax nan_fma _ _ _ Fb) as [Fax [Fay Fa]].
  rewrite <- (IH Vh Fs Fa). cbv beta iota.
  unfold acc_mul_entry_1, ieee_emin. cbv zeta.
  rewrite (guard_real_any _ prec tie_even (b2r x) (b2r_format prec emax x)).
  rewrite (guard_real_any _ prec tie_even (b2r y) (b2r_format prec emax y)).
  rewrite (proj2 (fma_spec prec emax nan_fma (guard x) (guard y) s
                    (guard_fin prec emax nan_plus x Fx) (guard_fin prec emax nan_plus y Fy) Fs) Ft).
  rewrite (proj2 (fma_spec prec emax nan_fma _ _ a Fax Fay Fa) Fb).
  rewrite !(abs_val prec emax nan_abs), !(guard_val prec emax nan_plus). reflexivity.
- intros [V1 V2]. destruct (run1i h1) as [s a]. destruct (run1i h2) as [v c].
  cbn [fst snd] in IH1, IH2.
  unfold IeeeModel.acc_merge_1. cbv beta iota zeta. cbn [fst snd]. intros Ft Fb.
  destruct (add_finite_inv prec emax nan_plus _ _ Ft) as [Fs Fv].
  destruct (add_finite_inv prec emax nan_plus _ _ Fb) as [Fa Fc].
  rewrite <- (IH1 V1 Fs Fa), <- (IH2 V2 Fv Fc). cbv beta iota.
  unfold acc_merge_1, ieee_emin. cbv zeta.
  rewrite (proj2 (add_spec prec emax nan_plus s v Fs Fv) Ft).
  rewrite (proj2 (add_spec prec emax nan_plus a c Fa Fc) Fb). reflexivity.
Qed.

(* The exported bound of a dot product of one limb: a finite t is the real model's. *)
Lemma bound_dot_1_real :
  (2 <= prec)%Z ->
  forall m : float, fin m ->
  let '(g, t, ok) := IeeeModel.bound_dot_1 prec emax nan_plus nan_fma m in
  fin t ->
  (b2r g, b2r t, ok) = bound_dot_1 (ieee_emin prec emax) prec tie_even (b2r m).
Proof.
intros Hp2 m Fm.
unfold IeeeModel.bound_dot_1, bound_dot_1, ieee_emin. cbv beta iota zeta.
set (c0 := IeeeModel.up_bound_dot_1_0 prec emax).
set (c1 := IeeeModel.up_bound_dot_1_1 prec emax).
set (c2 := IeeeModel.up_bound_dot_1_2 prec emax).
set (c3 := IeeeModel.up_bound_dot_1_3 prec emax).
set (c4 := IeeeModel.up_bound_dot_1_4 prec emax).
set (c5 := IeeeModel.up_bound_dot_1_5 prec emax).
set (c6 := IeeeModel.up_bound_dot_1_6 prec emax).
set (a := prod m c0).
set (aa := prod m c1).
set (d := prod a c2).
set (w := add d c3).
set (g := prod aa w).
set (tm := prod m c4).
set (wg := add g c3).
intros Ft.
destruct (prod_fin_val prec emax nan_fma tm wg Ft) as [Ftm [Fwg Vt]].
destruct (add_fin_val prec emax nan_plus g c3 Fwg) as [Fg [Fc3 Vwg]].
destruct (prod_fin_val prec emax nan_fma aa w Fg) as [Faa [Fw Vg]].
destruct (add_fin_val prec emax nan_plus d c3 Fw) as [Fd [_ Vw]].
destruct (prod_fin_val prec emax nan_fma a c2 Fd) as [Fa [Fc2 Vd]].
destruct (prod_fin_val prec emax nan_fma m c1 Faa) as [_ [Fc1 Vaa]].
destruct (prod_fin_val prec emax nan_fma m c0 Fa) as [_ [Fc0 Va]].
destruct (prod_fin_val prec emax nan_fma m c4 Ftm) as [_ [Fc4 Vtm]].
change (prod tm wg) with (prod tm wg) in Vt. change (add g c3) with wg in Vwg.
change (prod aa w) with g in Vg. change (add d c3) with w in Vw. change (prod a c2) with d in Vd.
change (prod m c1) with aa in Vaa. change (prod m c0) with a in Va. change (prod m c4) with tm in Vtm.
assert (K : forall r : R, format r -> fin (IeeeOperations.const_of prec emax r) ->
            b2r (IeeeOperations.const_of prec emax r) = r)
  by (intros r Fr F; exact (const_of_val prec emax r Fr F)).
assert (Vc0 : b2r c0 = up_bound_dot_1_0 emin prec)
  by (apply K; [apply generic_format_round; auto with typeclass_instances | exact Fc0]).
assert (Vc1 : b2r c1 = up_bound_dot_1_1 emin prec)
  by (apply K; [apply generic_format_round; auto with typeclass_instances | exact Fc1]).
assert (Vc2 : b2r c2 = up_bound_dot_1_2 emin prec)
  by (apply K; [apply generic_format_round; auto with typeclass_instances | exact Fc2]).
assert (Vc3 : b2r c3 = up_bound_dot_1_3 emin prec)
  by (apply K; [apply generic_format_round; auto with typeclass_instances | exact Fc3]).
assert (Vc4 : b2r c4 = up_bound_dot_1_4 emin prec)
  by (apply K; [apply generic_format_round; auto with typeclass_instances | exact Fc4]).
(* the two constants of the mask, up (1/4) and up (1), at most 1 *)
assert (L1 : 1 < bpow radix2 emax).
{ change 1 with (bpow radix2 0). apply bpow_lt. generalize prec_lt_emax_.
  unfold BinarySingleNaN.Prec_lt_emax. lia. }
assert (F1 : format 1) by exact (format_1 prec emax).
assert (Fc5 : fin c5 /\ b2r c5 = up_bound_dot_1_5 emin prec).
{ unfold c5, IeeeModel.up_bound_dot_1_5, up_bound_dot_1_5.
  destruct (const_of_RU prec emax (1 / 4) 1 ltac:(lra) ltac:(lra) F1 L1) as [F [E _]].
  split; assumption. }
assert (Fc6 : fin c6 /\ b2r c6 = up_bound_dot_1_6 emin prec).
{ unfold c6, IeeeModel.up_bound_dot_1_6, up_bound_dot_1_6.
  destruct (const_of_RU prec emax 1 1 ltac:(lra) ltac:(lra) F1 L1) as [F [E _]].
  split; assumption. }
destruct Fc5 as [Fc5 Vc5]. destruct Fc6 as [Fc6 Vc6].
rewrite (le_finite prec emax a c5 Fa Fc5), (le_finite prec emax g c6 Fg Fc6).
rewrite Vc5, Vc6, Vt, Vwg, Vg, Vw, Vd, Vaa, Va, Vtm, Vc0, Vc1, Vc2, Vc3, Vc4.
reflexivity.
Qed.

(* A finite radius was computed from finite g and t. *)
Lemma acc_radius_1_inputs :
  forall a m g t : float,
  fin (fst (IeeeModel.acc_radius_1 prec emax nan_plus nan_minus nan_fma a m g t)) ->
  fin g /\ fin t.
Proof.
intros a m g t. unfold IeeeModel.acc_radius_1. cbv beta iota zeta. cbn [fst]. intros Fr.
destruct (fma_finite_inv prec emax nan_fma _ _ _ Fr) as [Fs _].
destruct (add_finite_inv prec emax nan_plus _ _ Fs) as [Ff Ft].
unfold IeeeOperations.prod in Ff.
destruct (fma_finite_inv prec emax nan_fma _ _ _ Ff) as [_ [Fg _]].
split; assumption.
Qed.

(* a - a is a NaN when a is not finite. *)
Lemma sub_self_nan : forall a : float, is_finite prec emax a = false -> is_nan prec emax (sub a a) = true.
Proof.
intros [s|s|s pl Hpl|s m e He] F; try discriminate F.
- destruct s; reflexivity.
- reflexivity.
Qed.

(* A true mask means a finite sum of magnitudes. *)
Lemma acc_radius_1_ok_finite :
  forall a m g t : float,
  snd (IeeeModel.acc_radius_1 prec emax nan_plus nan_minus nan_fma a m g t) = true -> fin a.
Proof.
intros a m g t. unfold IeeeModel.acc_radius_1. cbv beta iota zeta. cbn [snd]. intros Hok.
apply andb_true_iff in Hok. destruct Hok as [_ Hz].
rewrite (eq_self prec emax) in Hz.
destruct (is_finite prec emax a) eqn:Fa. reflexivity.
rewrite (sub_self_nan a Fa) in Hz. discriminate Hz.
Qed.

(* A format of the IEEE model contains 1/2. *)
Lemma ieee_eta_half : (2 <= prec)%Z -> eta (ieee_emin prec emax) <= / 2.
Proof.
intros Hp2. unfold eta, ieee_emin. rewrite <- pow2_m1. apply bpow_le.
generalize prec_lt_emax_. unfold BinarySingleNaN.Prec_lt_emax. lia.
Qed.

(* What a user of an accumulator of one limb relies on, in the IEEE model: after any
   history of add, add_product and merge on finite numbers, if the running sum and the
   radius of error_bound() are finite and both masks true, the radius bounds the error. *)
Theorem acc_1_ieee_bound :
  (2 <= prec)%Z ->
  forall h : hist float, elems (fun x => fin x) h ->
  forall m g t r : float, fin m -> (b2r m = 0 \/ 1 <= b2r m) -> INR (count h) <= b2r m ->
  IeeeModel.bound_dot_1 prec emax nan_plus nan_fma m = (g, t, true) ->
  IeeeModel.acc_radius_1 prec emax nan_plus nan_minus nan_fma (snd (run1i h)) m g t = (r, true) ->
  fin (fst (run1i h)) -> fin r ->
  Rabs (b2r (fst (run1i h)) - sumR (terms b2r h)) <= b2r r.
Proof.
intros Hp2 h V m g t r Fm Hm Hn Hb Hr Fs Fr.
assert (Fa : fin (snd (run1i h))).
{ apply (acc_radius_1_ok_finite _ m g t). rewrite Hr. reflexivity. }
assert (Fgt : fin g /\ fin t).
{ apply (acc_radius_1_inputs (snd (run1i h)) m g t). rewrite Hr. exact Fr. }
destruct Fgt as [Fg Ft].
generalize (bound_dot_1_real Hp2 m Fm). rewrite Hb. intros Eb. specialize (Eb Ft).
generalize (acc_radius_1_real prec emax nan_plus nan_minus nan_fma Hp2 (snd (run1i h)) m g t Fa Fm Fg Ft).
rewrite Hr. intros Er. specialize (Er Fr).
generalize (run1i_real h V Fs Fa). intros Es.
assert (V' : elems (fmt (ieee_emin prec emax) prec) (hmap b2r h)).
{ apply (elems_hmap float R b2r (fun x => fin x)). intros x _. exact (b2r_format prec emax x).
  exact V. }
assert (Hn' : INR (count (hmap b2r h)) <= b2r m) by (rewrite count_hmap; exact Hn).
generalize (acc_1_bound (ieee_emin prec emax) prec Hp2 (ieee_eta_half Hp2) (hmap b2r h) V'
              (b2r m) (b2r g) (b2r t) (b2r r) (b2r_format prec emax m) Hm Hn' (eq_sym Eb)).
rewrite <- Es. cbn [fst snd]. rewrite terms_hmap. intros K. apply K. exact (eq_sym Er).
Qed.

End IeeeOne.

(** * Two limbs *)

Section IeeeTwo.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_opp : float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation fma := (IeeeOperations.fma prec emax nan_fma).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation pzero := (IeeeOperations.pzero prec emax).

(* The state after a history, in the IEEE model. *)
Fixpoint run2i (h : hist (float * float)) : float * float * float :=
  match h with
  | Hnil => (pzero, pzero, pzero)
  | Hadd h x =>
      let '(s0, s1, a) := run2i h in
      IeeeModel.acc_add_2 prec emax nan_plus nan_minus nan_abs s0 s1 a (fst x) (snd x)
  | Hmul h x y =>
      let '(s0, s1, a) := run2i h in
      IeeeModel.acc_mul_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma s0 s1 a
        (fst x) (snd x) (fst y) (snd y)
  | Hmerge h1 h2 =>
      let '(s0, s1, a) := run2i h1 in let '(v0, v1, c) := run2i h2 in
      IeeeModel.acc_merge_2 prec emax nan_plus nan_minus s0 s1 a v0 v1 c
  end.

(* The values of a pair, and a pair of finite limbs whose values are normalized. *)
Definition vals2i (x : float * float) : R * R := (b2r (fst x), b2r (snd x)).
Definition good2i (x : float * float) : Prop :=
  fin (fst x) /\ fin (snd x) /\ normalized_2 emin prec (b2r (fst x)) (b2r (snd x)).

(* The leading limb of a sum of two limbs is not finite unless both leading limbs are. *)
Lemma add_2_2_lead :
  forall s0 s1 x0 x1 : float,
  fin (fst (IeeeModel.add_2_2 prec emax nan_plus nan_minus s0 s1 x0 x1)) -> fin s0 /\ fin x0.
Proof.
intros s0 s1 x0 x1 H. unfold IeeeModel.add_2_2, IeeeModel.two_sum, IeeeModel.fast_two_sum in H.
cbv beta iota zeta in H. cbn [fst] in H.
apply (add_finite_inv prec emax nan_plus) in H. destruct H as [H _].
apply (add_finite_inv prec emax nan_plus) in H. destruct H as [H _].
exact (add_finite_inv prec emax nan_plus _ _ H).
Qed.

Lemma dot_step_2_lead :
  forall s0 s1 x0 x1 y0 y1 : float,
  fin (fst (IeeeModel.dot_step_2 prec emax nan_plus nan_minus nan_opp nan_fma s0 s1 x0 x1 y0 y1)) ->
  fin s0.
Proof.
intros s0 s1 x0 x1 y0 y1. unfold IeeeModel.dot_step_2. cbv zeta.
destruct (IeeeModel.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 y0 y1) as [p0 p1].
generalize (add_2_2_lead s0 s1 p0 p1).
destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus s0 s1 p0 p1) as [t0 t1].
cbn [fst]. intros L H. exact (proj1 (L H)).
Qed.

(* A finite final state: the real model's run on the values. *)
Lemma run2i_real :
  (4 <= prec)%Z ->
  forall h : hist (float * float), elems good2i h ->
  fin (fst (fst (run2i h))) -> fin (snd (run2i h)) ->
  fin (snd (fst (run2i h))) /\
  (b2r (fst (fst (run2i h))), b2r (snd (fst (run2i h))), b2r (snd (run2i h))) =
  run2 (ieee_emin prec emax) prec (hmap vals2i h).
Proof.
intros Hp4. assert (Hp3 : (3 <= prec)%Z) by lia.
assert (Hv : forall h, elems good2i h -> elems (norm2 (ieee_emin prec emax) prec) (hmap vals2i h)).
{ intros h. apply elems_hmap. intros x [_ [_ N]]. exact N. }
induction h as [|h IH x|h IH x y|h1 IH1 h2 IH2]; intros V; cbn [run2i hmap run2].
- intros _ _. split; reflexivity.
- destruct V as [Vh [Fx0 [Fx1 Nx]]].
  generalize (acc_2_mags (ieee_emin prec emax) prec Hp4 (hmap vals2i h) (Hv h Vh)).
  destruct (run2i h) as [[s0 s1] a]. cbn [fst snd] in IH.
  unfold IeeeModel.acc_add_2. cbv zeta.
  generalize (sum_entry_step_2_values prec emax nan_plus nan_minus
                (fun x => nan_plus x x) (fun x y _ => nan_plus x y) Hp3 s0 s1 (fst x) (snd x)).
  unfold IeeeModel.sum_entry_step_2. cbv zeta.
  generalize (add_2_2_lead s0 s1 (IeeeOperations.guard prec emax nan_plus (fst x))
                (IeeeOperations.guard prec emax nan_plus (snd x))).
  destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus s0 s1
              (IeeeOperations.guard prec emax nan_plus (fst x))
              (IeeeOperations.guard prec emax nan_plus (snd x))) as [t0 t1].
  cbn [fst snd]. intros L S M Ft0 Fb.
  destruct (L Ft0) as [Fs0 _].
  destruct (add_finite_inv prec emax nan_plus _ _ Fb) as [Fa Fag].
  destruct (IH Vh Fs0 Fa) as [Fs1 E].
  rewrite <- E in M |- *. cbv beta iota in M |- *. destruct M as [Ns _].
  destruct (S Fs0 Fs1 Fx0 Fx1 Ns Nx Ft0) as [Ft1 ES].
  rewrite (sum_entry_step_2_real _ prec _ _ _ _ (b2r_format prec emax _) (b2r_format prec emax _))
    in ES.
  split. exact Ft1.
  unfold vals2i. cbn [fst snd].
  unfold acc_add_2. cbv zeta. unfold ieee_emin in ES |- *.
  rewrite (guard_real_any _ prec tie_even _ (b2r_format prec emax (fst x))),
          (guard_real_any _ prec tie_even _ (b2r_format prec emax (snd x))).
  rewrite <- ES. cbv beta iota.
  rewrite (proj2 (add_spec prec emax nan_plus a _ Fa Fag) Fb).
  rewrite (abs_val prec emax nan_abs), (guard_val prec emax nan_plus). reflexivity.
- destruct V as [Vh [[Fx0 [Fx1 Nx]] [Fy0 [Fy1 Ny]]]].
  generalize (acc_2_mags (ieee_emin prec emax) prec Hp4 (hmap vals2i h) (Hv h Vh)).
  destruct (run2i h) as [[s0 s1] a]. cbn [fst snd] in IH.
  unfold IeeeModel.acc_mul_2. cbv zeta.
  generalize (dot_step_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp4
                s0 s1 (fst x) (snd x) (fst y) (snd y)).
  generalize (dot_step_2_lead s0 s1 (fst x) (snd x) (fst y) (snd y)).
  destruct (IeeeModel.dot_step_2 prec emax nan_plus nan_minus nan_opp nan_fma s0 s1
              (fst x) (snd x) (fst y) (snd y)) as [t0 t1].
  cbn [fst snd]. intros L S M Ft0 Fb.
  specialize (L Ft0) as Fs0.
  destruct (fma_finite_inv prec emax nan_fma _ _ _ Fb) as [Fax [Fay Fa]].
  destruct (IH Vh Fs0 Fa) as [Fs1 E].
  rewrite <- E in M |- *. cbv beta iota in M |- *. destruct M as [Ns _].
  destruct (S Fs0 Fs1 Fx0 Fx1 Fy0 Fy1 Ns Nx Ny Ft0) as [Ft1 ES].
  split. exact Ft1.
  unfold vals2i. cbn [fst snd].
  unfold acc_mul_2. cbv zeta.
  unfold ieee_emin in ES |- *. rewrite <- ES. cbv beta iota.
  rewrite (proj2 (fma_spec prec emax nan_fma _ _ a Fax Fay Fa) Fb).
  rewrite !(abs_val prec emax nan_abs). reflexivity.
- destruct V as [V1 V2].
  generalize (acc_2_mags (ieee_emin prec emax) prec Hp4 (hmap vals2i h1) (Hv h1 V1))
             (acc_2_mags (ieee_emin prec emax) prec Hp4 (hmap vals2i h2) (Hv h2 V2)).
  destruct (run2i h1) as [[s0 s1] a]. destruct (run2i h2) as [[v0 v1] c].
  cbn [fst snd] in IH1, IH2.
  unfold IeeeModel.acc_merge_2. cbv zeta.
  generalize (add_2_2_values prec emax nan_plus nan_minus
                (fun x => nan_plus x x) (fun x y _ => nan_plus x y) Hp3 s0 s1 v0 v1).
  generalize (add_2_2_lead s0 s1 v0 v1).
  destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus s0 s1 v0 v1) as [t0 t1].
  cbn [fst snd]. intros L S M1 M2 Ft0 Fb.
  destruct (L Ft0) as [Fs0 Fv0].
  destruct (add_finite_inv prec emax nan_plus _ _ Fb) as [Fa Fc].
  destruct (IH1 V1 Fs0 Fa) as [Fs1 E1]. destruct (IH2 V2 Fv0 Fc) as [Fv1 E2].
  rewrite <- E1 in M1 |- *. rewrite <- E2 in M2 |- *. cbv beta iota in M1, M2 |- *.
  destruct M1 as [Ns _]. destruct M2 as [Nv _].
  destruct (S Fs0 Fs1 Fv0 Fv1 Ns Nv Ft0) as [Ft1 ES].
  split. exact Ft1.
  unfold acc_merge_2. cbv zeta.
  unfold ieee_emin in ES |- *. rewrite <- ES. cbv beta iota.
  rewrite (proj2 (add_spec prec emax nan_plus a c Fa Fc) Fb). reflexivity.
Qed.

(* The exported bound of a dot product of two limbs: a finite t is the real model's. *)
Lemma bound_dot_2_real :
  (4 <= prec)%Z ->
  forall m : float, fin m ->
  let '(g, t, ok) := IeeeModel.bound_dot_2 prec emax nan_plus nan_fma m in
  fin t ->
  (b2r g, b2r t, ok) = bound_dot_2 (ieee_emin prec emax) prec tie_even (b2r m).
Proof.
intros Hp4 m Fm.
unfold IeeeModel.bound_dot_2, bound_dot_2, ieee_emin. cbv beta iota zeta.
set (c0 := IeeeModel.up_bound_dot_2_0 prec emax).
set (c1 := IeeeModel.up_bound_dot_2_1 prec emax).
set (c2 := IeeeModel.up_bound_dot_1_2 prec emax).
set (c3 := IeeeModel.up_bound_dot_1_3 prec emax).
set (c4 := IeeeModel.up_bound_dot_2_4 prec emax).
set (c5 := IeeeModel.up_bound_dot_1_5 prec emax).
set (c6 := IeeeModel.up_bound_dot_1_6 prec emax).
set (a := prod m c0).
set (aa := prod m c1).
set (d := prod a c2).
set (w := add d c3).
set (g := prod aa w).
set (tm := prod m c4).
set (wg := add g c3).
intros Ft.
destruct (prod_fin_val prec emax nan_fma tm wg Ft) as [Ftm [Fwg Vt]].
destruct (add_fin_val prec emax nan_plus g c3 Fwg) as [Fg [Fc3 Vwg]].
destruct (prod_fin_val prec emax nan_fma aa w Fg) as [Faa [Fw Vg]].
destruct (add_fin_val prec emax nan_plus d c3 Fw) as [Fd [_ Vw]].
destruct (prod_fin_val prec emax nan_fma a c2 Fd) as [Fa [Fc2 Vd]].
destruct (prod_fin_val prec emax nan_fma m c1 Faa) as [_ [Fc1 Vaa]].
destruct (prod_fin_val prec emax nan_fma m c0 Fa) as [_ [Fc0 Va]].
destruct (prod_fin_val prec emax nan_fma m c4 Ftm) as [_ [Fc4 Vtm]].
change (add g c3) with wg in Vwg.
change (prod aa w) with g in Vg. change (add d c3) with w in Vw. change (prod a c2) with d in Vd.
change (prod m c1) with aa in Vaa. change (prod m c0) with a in Va. change (prod m c4) with tm in Vtm.
assert (K : forall r : R, format r -> fin (IeeeOperations.const_of prec emax r) ->
            b2r (IeeeOperations.const_of prec emax r) = r)
  by (intros r Fr F; exact (const_of_val prec emax r Fr F)).
assert (Vc0 : b2r c0 = up_bound_dot_2_0 emin prec)
  by (apply K; [apply generic_format_round; auto with typeclass_instances | exact Fc0]).
assert (Vc1 : b2r c1 = up_bound_dot_2_1 emin prec)
  by (apply K; [apply generic_format_round; auto with typeclass_instances | exact Fc1]).
assert (Vc2 : b2r c2 = up_bound_dot_1_2 emin prec)
  by (apply K; [apply generic_format_round; auto with typeclass_instances | exact Fc2]).
assert (Vc3 : b2r c3 = up_bound_dot_1_3 emin prec)
  by (apply K; [apply generic_format_round; auto with typeclass_instances | exact Fc3]).
assert (Vc4 : b2r c4 = up_bound_dot_2_4 emin prec)
  by (apply K; [apply generic_format_round; auto with typeclass_instances | exact Fc4]).
assert (L1 : 1 < bpow radix2 emax).
{ change 1 with (bpow radix2 0). apply bpow_lt. generalize prec_lt_emax_.
  unfold BinarySingleNaN.Prec_lt_emax. lia. }
assert (F1 : format 1) by exact (format_1 prec emax).
assert (Fc5 : fin c5 /\ b2r c5 = up_bound_dot_1_5 emin prec).
{ unfold c5, IeeeModel.up_bound_dot_1_5, up_bound_dot_1_5.
  destruct (const_of_RU prec emax (1 / 4) 1 ltac:(lra) ltac:(lra) F1 L1) as [F [E _]].
  split; assumption. }
assert (Fc6 : fin c6 /\ b2r c6 = up_bound_dot_1_6 emin prec).
{ unfold c6, IeeeModel.up_bound_dot_1_6, up_bound_dot_1_6.
  destruct (const_of_RU prec emax 1 1 ltac:(lra) ltac:(lra) F1 L1) as [F [E _]].
  split; assumption. }
destruct Fc5 as [Fc5 Vc5]. destruct Fc6 as [Fc6 Vc6].
rewrite (le_finite prec emax a c5 Fa Fc5), (le_finite prec emax g c6 Fg Fc6).
rewrite Vc5, Vc6, Vt, Vwg, Vg, Vw, Vd, Vaa, Va, Vtm, Vc0, Vc1, Vc2, Vc3, Vc4.
reflexivity.
Qed.

(* What a user of an accumulator of two limbs relies on, in the IEEE model: after any
   history of add, add_product and merge on pairs of finite limbs whose values are
   normalized, if the leading limb of the running sum and the radius of error_bound() are
   finite and both masks true, the radius bounds the error. *)
Theorem acc_2_ieee_bound :
  (4 <= prec)%Z ->
  forall h : hist (float * float), elems good2i h ->
  forall m g t r : float, fin m -> (b2r m = 0 \/ 1 <= b2r m) -> INR (count h) <= b2r m ->
  IeeeModel.bound_dot_2 prec emax nan_plus nan_fma m = (g, t, true) ->
  IeeeModel.acc_radius_2 prec emax nan_plus nan_minus nan_fma (snd (run2i h)) m g t = (r, true) ->
  fin (fst (fst (run2i h))) -> fin r ->
  fin (snd (fst (run2i h))) /\
  Rabs (b2r (fst (fst (run2i h))) + b2r (snd (fst (run2i h))) -
        sumR (terms (fun x => b2r (fst x) + b2r (snd x)) h)) <= b2r r.
Proof.
intros Hp4 h V m g t r Fm Hm Hn Hb Hr Fs Fr.
assert (Hp2 : (2 <= prec)%Z) by lia.
assert (Hr1 : IeeeModel.acc_radius_1 prec emax nan_plus nan_minus nan_fma (snd (run2i h)) m g t =
              (r, true)).
{ unfold IeeeModel.acc_radius_2 in Hr.
  destruct (IeeeModel.acc_radius_1 prec emax nan_plus nan_minus nan_fma (snd (run2i h)) m g t).
  exact Hr. }
assert (Fa : fin (snd (run2i h))).
{ apply (acc_radius_1_ok_finite prec emax nan_plus nan_minus nan_fma _ m g t).
  rewrite Hr1. reflexivity. }
assert (Fgt : fin g /\ fin t).
{ apply (acc_radius_1_inputs prec emax nan_plus nan_minus nan_fma (snd (run2i h)) m g t).
  rewrite Hr1. exact Fr. }
destruct Fgt as [Fg Ft].
generalize (bound_dot_2_real Hp4 m Fm). rewrite Hb. intros Eb. specialize (Eb Ft).
generalize (acc_radius_1_real prec emax nan_plus nan_minus nan_fma Hp2 (snd (run2i h)) m g t
              Fa Fm Fg Ft).
rewrite Hr1. intros Er. specialize (Er Fr).
destruct (run2i_real Hp4 h V Fs Fa) as [Fs1 Es].
split. exact Fs1.
assert (V' : elems (norm2 (ieee_emin prec emax) prec) (hmap vals2i h)).
{ apply elems_hmap with (P := good2i). intros x [_ [_ N]]. exact N. exact V. }
assert (Hn' : INR (count (hmap vals2i h)) <= b2r m) by (rewrite count_hmap; exact Hn).
assert (Er2 : acc_radius_2 (ieee_emin prec emax) prec tie_even (b2r (snd (run2i h))) (b2r m)
                (b2r g) (b2r t) = (b2r r, true)).
{ unfold acc_radius_2. rewrite <- Er. reflexivity. }
generalize (acc_2_bound (ieee_emin prec emax) prec Hp4 (ieee_eta_half prec emax Hp2) (hmap vals2i h) V'
              (b2r m) (b2r g) (b2r t) (b2r r) (b2r_format prec emax m) Hm Hn' (eq_sym Eb)).
rewrite <- Es. cbn [fst snd]. rewrite terms_hmap. intros K. apply K. exact Er2.
Qed.

End IeeeTwo.
