(* The kernels of the accumulator in the IEEE model (proofs/gen/IeeeModel.v): the generated
   statements K_ieee_spec of acc_add_1, acc_add_2, acc_mul_1, acc_mul_2, acc_merge_1,
   acc_merge_2, acc_radius_1 and acc_radius_2 (proofs/gen/IeeeStatements.v).

   Each statement is about finite operands that satisfy the kernel's requirements, and
   says what holds of each output group where its own leading limb is finite:
   - the running sum t (t0, t1): where t (t0) is finite, what the real-model statement
     says of it. For one limb t is one IEEE operation on finite operands, so a finite t
     is the rounding to nearest of the exact result (add_spec, fma_spec of IeeeBridge.v)
     and the bound is that of add_1_1_correct. For two limbs t is sum_entry_step_2
     (acc_add_2: add_2_2 on the guarded element), add_2_2 (acc_merge_2) or dot_step_2
     (acc_mul_2) of the IEEE model, whose own statements are proved (IeeeSteps.v,
     IeeeAdd22.v).
   - the sum of magnitudes b: where b is finite, the rounding to nearest of its value:
     b is one addition or one fused multiply-add of finite operands, the absolute value
     keeping a finite operand finite with the magnitude as value (abs_finite, abs_val of
     IeeeOps.v), and the guard keeping it with its value (guard_finite, guard_val).
     Where b is +inf nothing is claimed; the mask of acc_radius_k is then false.
   - the radius: where r is finite, the claims of the real model. A finite r means that
     every value the listing computes was finite (each of them reaches r through an
     addition or a fused operation, which a non-finite operand makes non-finite:
     fma_finite_inv, add_finite_inv), so each is the rounding of the exact result and the
     constants have the values of the real model (const_of_val below). The test of
     a - a against itself is true for a finite a, and d <= up(1) compares finite numbers:
     the mask is the real model's. So (r, ok) is the real model's (acc_radius_1_real),
     and acc_radius_1_correct (AccKernels.v) gives the claims. *)
From Stdlib Require Import Reals ZArith List Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format OneLimb Program IeeeBridge IeeeVocabulary IeeeOps IeeeSteps
  IeeeAdd22 AccKernels.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

Section IeeeAcc.
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
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation fma := (IeeeOperations.fma prec emax nan_fma).
Notation guard := (IeeeOperations.guard prec emax nan_plus).
Notation const_of := (IeeeOperations.const_of prec emax).

(* A constant of the format that is finite has the value it was made from. *)
Lemma const_of_val : forall r : R, format r -> fin (const_of r) -> b2r (const_of r) = r.
Proof.
intros r Fr F. unfold IeeeOperations.const_of in *.
generalize (binary_normalize_correct prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_NE
              (Ztrunc (scaled_mantissa radix2 fexp r)) (cexp radix2 fexp r) false).
assert (E : F2R (Float radix2 (Ztrunc (scaled_mantissa radix2 fexp r)) (cexp radix2 fexp r)) = r)
  by (symmetry; exact Fr).
rewrite E.
change (round radix2 (SpecFloat.fexp prec emax)
          (BinarySingleNaN.round_mode BinarySingleNaN.mode_NE) r) with (rnd r).
rewrite round_generic by (auto with typeclass_instances).
destruct (Rlt_bool_spec (Rabs r) (bpow radix2 emax)) as [H|H].
- intros [E1 _]. exact E1.
- intros E1. rewrite (overflow_NE prec emax) in E1. apply (B2FF_inf_inv prec emax) in E1.
  rewrite E1 in F. discriminate F.
Qed.

(* The magnitude of a finite number: finite, of value its absolute value. *)
Lemma abs_fin : forall x : float, fin x -> fin (fabs x).
Proof. intros x F. rewrite (abs_finite prec emax nan_abs). exact F. Qed.

Lemma guard_fin : forall x : float, fin x -> fin (guard x).
Proof. intros x F. rewrite (guard_finite prec emax nan_plus). exact F. Qed.

End IeeeAcc.

(** * The six state kernels *)

Theorem acc_add_1_ieee_correct : acc_add_1_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs Hp1 s a x Fs Fa Fx Ha.
unfold IeeeModel.acc_add_1. cbv beta iota zeta.
set (g := IeeeOperations.guard prec emax nan_plus x).
assert (Fg : finite g) by exact (guard_fin prec emax nan_plus x Fx).
assert (Vg : val g = val x) by exact (guard_val prec emax nan_plus x).
split.
- intros Ft.
  assert (E : val (IeeeOperations.add prec emax nan_plus s g) =
              RN (ieee_emin prec emax) prec (val s + val x)).
  { rewrite <- Vg. exact (proj2 (add_spec prec emax nan_plus s g Fs Fg) Ft). }
  rewrite E. split. reflexivity.
  destruct (add_1_1_correct (ieee_emin prec emax) prec Hp1 (val s) (val x)
              (b2r_format prec emax s) (b2r_format prec emax x)) as [_ [_ B]].
  exact B.
- intros Fb.
  assert (Fag : finite (IeeeOperations.abs prec emax nan_abs g))
    by exact (abs_fin prec emax nan_abs g Fg).
  generalize (proj2 (add_spec prec emax nan_plus a _ Fa Fag) Fb).
  unfold val in Vg |- *. rewrite (abs_val prec emax nan_abs g), Vg. intros E. exact E.
Qed.

Theorem acc_merge_1_ieee_correct : acc_merge_1_ieee_spec.
Proof.
intros prec emax Hp He nan_plus Hp1 s a v c Fs Fa Fv Fc Ha Hc.
unfold IeeeModel.acc_merge_1. cbv beta iota zeta.
split.
- intros Ft.
  assert (E : val (IeeeOperations.add prec emax nan_plus s v) =
              RN (ieee_emin prec emax) prec (val s + val v))
    by exact (proj2 (add_spec prec emax nan_plus s v Fs Fv) Ft).
  rewrite E. split. reflexivity.
  destruct (add_1_1_correct (ieee_emin prec emax) prec Hp1 (val s) (val v)
              (b2r_format prec emax s) (b2r_format prec emax v)) as [_ [_ B]].
  exact B.
- intros Fb. exact (proj2 (add_spec prec emax nan_plus a c Fa Fc) Fb).
Qed.

Theorem acc_mul_1_ieee_correct : acc_mul_1_ieee_spec.
Proof.
intros prec emax Hp He nan_abs nan_fma Hp1 s a x y Fs Fa Fx Fy Ha.
unfold IeeeModel.acc_mul_1. cbv beta iota zeta.
split.
- intros Ft. unfold val. rewrite (proj2 (fma_spec prec emax nan_fma x y s Fx Fy Fs) Ft).
  unfold RN. f_equal. ring.
- intros Fb.
  assert (Fax : finite (IeeeOperations.abs prec emax nan_abs x))
    by exact (abs_fin prec emax nan_abs x Fx).
  assert (Fay : finite (IeeeOperations.abs prec emax nan_abs y))
    by exact (abs_fin prec emax nan_abs y Fy).
  unfold val. rewrite (proj2 (fma_spec prec emax nan_fma _ _ a Fax Fay Fa) Fb).
  rewrite (abs_val prec emax nan_abs x), (abs_val prec emax nan_abs y).
  unfold RN. f_equal. ring.
Qed.

(* acc_mul_1 on x and y guarded (rule R3, the factors of a fused operation): the guard of a
   finite value is finite with the same value (guard_fin, guard_val). *)
Theorem acc_mul_entry_1_ieee_correct : acc_mul_entry_1_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma Hp1 s a x y Fs Fa Fx Fy Ha.
unfold IeeeModel.acc_mul_entry_1. cbv beta iota zeta.
set (gx := IeeeOperations.guard prec emax nan_plus x).
set (gy := IeeeOperations.guard prec emax nan_plus y).
assert (Fgx : finite gx) by exact (guard_fin prec emax nan_plus x Fx).
assert (Fgy : finite gy) by exact (guard_fin prec emax nan_plus y Fy).
assert (Vgx : val gx = val x) by exact (guard_val prec emax nan_plus x).
assert (Vgy : val gy = val y) by exact (guard_val prec emax nan_plus y).
unfold val in Vgx, Vgy.
split.
- intros Ft. unfold val. rewrite (proj2 (fma_spec prec emax nan_fma gx gy s Fgx Fgy Fs) Ft).
  rewrite Vgx, Vgy. unfold RN. f_equal. ring.
- intros Fb.
  assert (Fax : finite (IeeeOperations.abs prec emax nan_abs gx))
    by exact (abs_fin prec emax nan_abs gx Fgx).
  assert (Fay : finite (IeeeOperations.abs prec emax nan_abs gy))
    by exact (abs_fin prec emax nan_abs gy Fgy).
  unfold val. rewrite (proj2 (fma_spec prec emax nan_fma _ _ a Fax Fay Fa) Fb).
  rewrite (abs_val prec emax nan_abs gx), (abs_val prec emax nan_abs gy), Vgx, Vgy.
  unfold RN. f_equal. ring.
Qed.

Theorem acc_add_2_ieee_correct : acc_add_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs Hp3 s0 s1 a x0 x1 Fs0 Fs1 Fa Fx0 Fx1 Ns Nx Ha.
generalize (sum_entry_step_2_ieee_correct prec emax Hp He nan_plus nan_minus Hp3
              s0 s1 x0 x1 Fs0 Fs1 Fx0 Fx1 Ns Nx).
unfold IeeeModel.acc_add_2, IeeeModel.sum_entry_step_2. cbv zeta.
destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus s0 s1
            (IeeeOperations.guard prec emax nan_plus x0)
            (IeeeOperations.guard prec emax nan_plus x1)) as [t0 t1].
intros Ht. split. exact Ht.
intros Fb.
set (g := IeeeOperations.guard prec emax nan_plus x0) in *.
assert (Fg : finite g) by exact (guard_fin prec emax nan_plus x0 Fx0).
assert (Vg : val g = val x0) by exact (guard_val prec emax nan_plus x0).
assert (Fag : finite (IeeeOperations.abs prec emax nan_abs g))
  by exact (abs_fin prec emax nan_abs g Fg).
generalize (proj2 (add_spec prec emax nan_plus a _ Fa Fag) Fb).
unfold val in Vg |- *. rewrite (abs_val prec emax nan_abs g), Vg. intros E. exact E.
Qed.

Theorem acc_merge_2_ieee_correct : acc_merge_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus Hp3 s0 s1 a v0 v1 c Fs0 Fs1 Fa Fv0 Fv1 Fc Ns Nv Ha Hc.
generalize (add_2_2_ieee_correct prec emax Hp He nan_plus nan_minus Hp3
              s0 s1 v0 v1 Fs0 Fs1 Fv0 Fv1 Ns Nv).
unfold IeeeModel.acc_merge_2. cbv zeta.
destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus s0 s1 v0 v1) as [t0 t1].
intros Ht. split. exact Ht.
intros Fb. exact (proj2 (add_spec prec emax nan_plus a c Fa Fc) Fb).
Qed.

Theorem acc_mul_2_ieee_correct : acc_mul_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma Hp4
  s0 s1 a x0 x1 y0 y1 Fs0 Fs1 Fa Fx0 Fx1 Fy0 Fy1 Ns Nx Ny Ha.
generalize (dot_step_2_ieee_correct prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp4
              s0 s1 x0 x1 y0 y1 Fs0 Fs1 Fx0 Fx1 Fy0 Fy1 Ns Nx Ny).
unfold IeeeModel.acc_mul_2. cbv zeta.
destruct (IeeeModel.dot_step_2 prec emax nan_plus nan_minus nan_opp nan_fma s0 s1 x0 x1 y0 y1)
  as [t0 t1].
intros Ht. split. exact Ht.
intros Fb.
assert (Fax : finite (IeeeOperations.abs prec emax nan_abs x0))
  by exact (abs_fin prec emax nan_abs x0 Fx0).
assert (Fay : finite (IeeeOperations.abs prec emax nan_abs y0))
  by exact (abs_fin prec emax nan_abs y0 Fy0).
unfold val. rewrite (proj2 (fma_spec prec emax nan_fma _ _ a Fax Fay Fa) Fb).
rewrite (abs_val prec emax nan_abs x0), (abs_val prec emax nan_abs y0).
unfold RN. f_equal. ring.
Qed.

(** * The radius *)

Section IeeeRadius.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
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

(* One operation with a finite result: finite operands, and the rounded exact result. *)
Lemma fma_fin_val :
  forall x y z : float, fin (fma x y z) ->
  fin x /\ fin y /\ fin z /\ b2r (fma x y z) = rnd (b2r x * b2r y + b2r z).
Proof.
intros x y z F. destruct (fma_finite_inv prec emax nan_fma x y z F) as [Fx [Fy Fz]].
split; [exact Fx | split; [exact Fy | split; [exact Fz |]]].
exact (proj2 (fma_spec prec emax nan_fma x y z Fx Fy Fz) F).
Qed.

Lemma prod_fin_val :
  forall x y : float, fin (prod x y) -> fin x /\ fin y /\ b2r (prod x y) = rnd (b2r x * b2r y + 0).
Proof.
intros x y F. unfold IeeeOperations.prod in *.
destruct (fma_fin_val x y _ F) as [Fx [Fy [_ E]]].
split; [exact Fx | split; [exact Fy | exact E]].
Qed.

Lemma add_fin_val :
  forall x y : float, fin (add x y) -> fin x /\ fin y /\ b2r (add x y) = rnd (b2r x + b2r y).
Proof.
intros x y F. destruct (add_finite_inv prec emax nan_plus x y F) as [Fx Fy].
split; [exact Fx | split; [exact Fy |]].
exact (proj2 (add_spec prec emax nan_plus x y Fx Fy) F).
Qed.

(* A finite r: the listing of the IEEE model computes what the real model computes, mask
   included. *)
Lemma acc_radius_1_real :
  (2 <= prec)%Z ->
  forall a m g t : float, fin a -> fin m -> fin g -> fin t ->
  let '(r, ok) := IeeeModel.acc_radius_1 prec emax nan_plus nan_minus nan_fma a m g t in
  fin r ->
  (b2r r, ok) = acc_radius_1 (ieee_emin prec emax) prec tie_even (b2r a) (b2r m) (b2r g) (b2r t).
Proof.
intros Hp2 a m g t Fa Fm Fg Ft.
unfold IeeeModel.acc_radius_1, acc_radius_1, ieee_emin. cbv beta iota zeta.
set (C0i := IeeeModel.up_acc_radius_1_0 prec emax).
set (c2i := IeeeModel.up_bound_dot_1_2 prec emax).
set (Ni := IeeeModel.up_ball_mul_pow2_1_0 prec emax).
set (Ki := IeeeModel.up_acc_radius_1_3 prec emax).
set (Ci := IeeeModel.up_acc_radius_1_4 prec emax).
set (c6i := IeeeModel.up_bound_dot_1_6 prec emax).
set (q := prod m C0i).
set (d := prod q c2i).
set (w := fma q d q).
set (c := fma m Ni a).
set (e := fma c w c).
set (f := prod e g).
set (s := add f t).
set (z := sub a a).
intros Fr.
destruct (fma_fin_val s Ki Ci Fr) as [Fs [FK [FC Vr]]].
destruct (add_fin_val f t Fs) as [Ff [_ Vs]].
destruct (prod_fin_val e g Ff) as [Fe [_ Vf]].
destruct (fma_fin_val c w c Fe) as [Fc [Fw [_ Ve]]].
destruct (fma_fin_val q d q Fw) as [Fq [Fd [_ Vw]]].
destruct (fma_fin_val m Ni a Fc) as [_ [FN [_ Vc]]].
destruct (prod_fin_val m C0i Fq) as [_ [FC0 Vq]].
destruct (prod_fin_val q c2i Fd) as [_ [Fc2 Vd]].
change (add f t) with s in Vs. change (prod e g) with f in Vf. change (fma c w c) with e in Ve.
change (fma m Ni a) with c in Vc. change (fma q d q) with w in Vw. change (prod q c2i) with d in Vd.
change (prod m C0i) with q in Vq.
(* the constants *)
assert (VC0 : b2r C0i = up_acc_radius_1_0 emin prec).
{ apply (const_of_val prec emax). apply generic_format_round; auto with typeclass_instances.
  exact FC0. }
assert (Vc2 : b2r c2i = up_bound_dot_1_2 emin prec).
{ apply (const_of_val prec emax). apply generic_format_round; auto with typeclass_instances.
  exact Fc2. }
assert (VN : b2r Ni = up_ball_mul_pow2_1_0 emin prec).
{ apply (const_of_val prec emax). apply generic_format_round; auto with typeclass_instances.
  exact FN. }
assert (VK : b2r Ki = up_acc_radius_1_3 emin prec).
{ apply (const_of_val prec emax). apply generic_format_round; auto with typeclass_instances.
  exact FK. }
assert (VC : b2r Ci = up_acc_radius_1_4 emin prec).
{ apply (const_of_val prec emax). apply generic_format_round; auto with typeclass_instances.
  exact FC. }
assert (E6 : up_bound_dot_1_6 emin prec = 1).
{ destruct (c6_cases emin prec Hp2) as [[_ E]|[H _]]. exact E.
  exfalso. generalize prec_lt_emax_. unfold BinarySingleNaN.Prec_lt_emax. lia. }
assert (Fc6 : fin c6i /\ b2r c6i = 1).
{ unfold c6i, IeeeModel.up_bound_dot_1_6. rewrite E6.
  apply (const_of_spec prec emax). apply (format_1 prec emax). apply (le_1_inrange prec emax). lra. }
destruct Fc6 as [Fc6 Vc6].
(* the test of a finite a *)
assert (Fz : fin z /\ b2r z = rnd (b2r a - b2r a)).
{ destruct (sub_spec prec emax nan_minus a a Fa Fa) as [I E].
  assert (Fz : fin z).
  { apply I. rewrite Rminus_diag, round_0 by (auto with typeclass_instances). unfold inrange.
    rewrite Rabs_R0. apply bpow_gt_0. }
  split. exact Fz. exact (E Fz). }
destruct Fz as [Fz Vz].
rewrite (le_finite prec emax d c6i Fd Fc6), (eq_finite prec emax z z Fz Fz).
rewrite Vz, Vc6, <- E6.
rewrite Vr, Vs, Vf, Ve, Vc, Vw, Vd, Vq, VC0, Vc2, VN, VK, VC.
reflexivity.
Qed.

End IeeeRadius.

Theorem acc_radius_1_ieee_correct : acc_radius_1_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_fma Hp2 a m g t Fa Fm Fg Ft Ha Hm Hg Ht.
generalize (acc_radius_1_real prec emax nan_plus nan_minus nan_fma Hp2 a m g t Fa Fm Fg Ft).
generalize (acc_radius_1_correct (ieee_emin prec emax) prec Hp2 (val a) (val m) (val g) (val t)
              (b2r_format prec emax a) (b2r_format prec emax m) (b2r_format prec emax g)
              (b2r_format prec emax t) Ha Hm Hg Ht).
unfold val.
destruct (acc_radius_1 (ieee_emin prec emax) prec tie_even
            (B2R prec emax a) (B2R prec emax m) (B2R prec emax g) (B2R prec emax t))
  as [rr okr].
destruct (IeeeModel.acc_radius_1 prec emax nan_plus nan_minus nan_fma a m g t) as [r ok].
intros [_ [B M]] E Fr. specialize (E Fr). injection E. intros Eok Er.
rewrite Er, Eok. split. exact B. exact M.
Qed.

Theorem acc_radius_2_ieee_correct : acc_radius_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_fma Hp2 a m g t Fa Fm Fg Ft Ha Hm Hg Ht.
unfold IeeeModel.acc_radius_2.
generalize (acc_radius_1_ieee_correct prec emax Hp He nan_plus nan_minus nan_fma Hp2
              a m g t Fa Fm Fg Ft Ha Hm Hg Ht).
destruct (IeeeModel.acc_radius_1 prec emax nan_plus nan_minus nan_fma a m g t) as [r ok].
intros H. exact H.
Qed.
