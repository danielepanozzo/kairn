(* The kernels of the accumulator in the IEEE model (proofs/gen/IeeeModel.v): the generated
   statements K_ieee_spec of acc_add_1, acc_add_2, acc_mul_1, acc_mul_2, acc_merge_1 and
   acc_merge_2 (proofs/gen/IeeeStatements.v).

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
     Where b is +inf nothing is claimed. *)
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
