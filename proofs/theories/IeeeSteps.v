(* The steps of the folds in the IEEE model (proofs/gen/IeeeModel.v), for finite operands
   that satisfy the requirements of the kernel: the generated statements
   K_ieee_bridge_spec of dot_step_1, dot_entry_step_1, sum_entry_step_1, dot_step_2,
   sum_entry_step_2 and sum_fast_entry_step_2, and K_ieee_spec of the last three
   (proofs/gen/IeeeStatements.v).

   1. Bridge (K_ieee_bridge). If the leading limb of the result is finite then every
      value the kernel computes is finite, and the result is, as real numbers, that of
      the real model on the values of the operands. For the steps of two limbs this is
      the theorem of IeeeBridge.v for a program that ends with a Fast2Sum, as for
      add_2_2 (IeeeAdd22.v): the values computed before the leading limb are in its
      cone, which is checked by computation, and the last two are finite because the
      result of the real model is normalized (K_correct, StepKernels.v). In dot_step_2
      the tail of the Fast2Sum that ends its product is in that cone too: the second
      limb of the product is an operand of the addition. For the steps of one limb the
      program is one operation, after the guard in an entry step, and the bridge is
      fma_spec or add_spec.

   2. Correctness (K_ieee_correct), for the steps of two limbs. Hence, if the leading
      limb of the result is finite, the second limb is finite, the result is
      normalized, and the bound of the real-model theorem holds: an overflow inside a
      step never produces a finite wrong result.

   An entry step guards each limb of its element first. The guard is an instruction of
   the program (Iguard), the addition of +0, so nothing here is specific to it. *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Guard Normalized StepKernels Program IeeeBridge IeeeVocabulary
  IeeeOps.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Import ListNotations.
Open Scope R_scope.

(** * The programs of proofs/gen/IeeeModel.v are the kernels of the real model *)

Lemma dot_step_2_runR :
  forall emin prec choice s0 s1 x0 x1 y0 y1,
  dot_step_2 emin prec choice s0 s1 x0 x1 y0 y1 =
  (nth 32 (runR emin prec choice IeeeModel.dot_step_2_prog [s0; s1; x0; x1; y0; y1]) 0,
   nth 34 (runR emin prec choice IeeeModel.dot_step_2_prog [s0; s1; x0; x1; y0; y1]) 0).
Proof.
intros. cbv [dot_step_2 mul_2_2 add_2_2 two_prod two_sum fast_two_sum runR run stepR nth app
             IeeeModel.dot_step_2_prog].
reflexivity.
Qed.

Lemma sum_entry_step_2_runR :
  forall emin prec choice s0 s1 x0 x1,
  sum_entry_step_2 emin prec choice s0 s1 x0 x1 =
  (nth 23 (runR emin prec choice IeeeModel.sum_entry_step_2_prog [s0; s1; x0; x1]) 0,
   nth 25 (runR emin prec choice IeeeModel.sum_entry_step_2_prog [s0; s1; x0; x1]) 0).
Proof.
intros. cbv [sum_entry_step_2 add_2_2 two_sum fast_two_sum runR run stepR nth app
             IeeeModel.sum_entry_step_2_prog].
reflexivity.
Qed.

Lemma sum_fast_entry_step_2_runR :
  forall emin prec choice s0 s1 x0 x1,
  sum_fast_entry_step_2 emin prec choice s0 s1 x0 x1 =
  (nth 14 (runR emin prec choice IeeeModel.sum_fast_entry_step_2_prog [s0; s1; x0; x1]) 0,
   nth 16 (runR emin prec choice IeeeModel.sum_fast_entry_step_2_prog [s0; s1; x0; x1]) 0).
Proof.
intros. cbv [sum_fast_entry_step_2 add_fast_2_2 two_sum fast_two_sum runR run stepR nth app
             IeeeModel.sum_fast_entry_step_2_prog].
reflexivity.
Qed.

Section IeeeSteps.
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
Notation stB := (stepB prec emax nan_plus nan_minus nan_opp nan_fma).
Notation runB := (run stB).
Notation runR := (runR emin prec tie_even).
Notation d0 := (d0 prec emax).
Notation finite_all := (Forall (fun x : float => fin x)).

(** * dot_step_2 *)

(* The program is the kernel of the IEEE model. *)
Lemma dot_step_2_runB :
  forall s0 s1 x0 x1 y0 y1 : float,
  IeeeModel.dot_step_2 prec emax nan_plus nan_minus nan_opp nan_fma s0 s1 x0 x1 y0 y1 =
  (nth 32 (runB IeeeModel.dot_step_2_prog [s0; s1; x0; x1; y0; y1]) d0,
   nth 34 (runB IeeeModel.dot_step_2_prog [s0; s1; x0; x1; y0; y1]) d0).
Proof.
intros. cbv [IeeeModel.dot_step_2 IeeeModel.mul_2_2 IeeeModel.add_2_2 IeeeModel.two_prod
             IeeeModel.two_sum IeeeModel.fast_two_sum run stepB nth app
             IeeeModel.dot_step_2_prog].
reflexivity.
Qed.

Theorem dot_step_2_bridge :
  (4 <= prec)%Z ->
  forall s0 s1 x0 x1 y0 y1 : float,
  fin s0 -> fin s1 -> fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r s0) (b2r s1) ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  normalized_2 emin prec (b2r y0) (b2r y1) ->
  fin (nth 32 (runB IeeeModel.dot_step_2_prog [s0; s1; x0; x1; y0; y1]) d0) ->
  finite_all (runB IeeeModel.dot_step_2_prog [s0; s1; x0; x1; y0; y1]) /\
  map b2r (runB IeeeModel.dot_step_2_prog [s0; s1; x0; x1; y0; y1])
  = runR IeeeModel.dot_step_2_prog [b2r s0; b2r s1; b2r x0; b2r x1; b2r y0; b2r y1].
Proof.
intros Hp4 s0 s1 x0 x1 y0 y1 Fs0 Fs1 Fx0 Fx1 Fy0 Fy1 Ns Nx Ny Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.dot_step_2_prog (firstn 26 IeeeModel.dot_step_2_prog) 28%nat 31%nat
         [s0; s1; x0; x1; y0; y1] 32%nat); trivial.
- repeat constructor; assumption.
- generalize (dot_step_2_correct emin prec Hp4 (b2r s0) (b2r s1) (b2r x0) (b2r x1) (b2r y0)
                (b2r y1) Ns Nx Ny).
  rewrite dot_step_2_runR. intros [N _]. exact N.
Qed.

Theorem dot_step_2_values :
  (4 <= prec)%Z ->
  forall s0 s1 x0 x1 y0 y1 : float,
  fin s0 -> fin s1 -> fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r s0) (b2r s1) ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(t0, t1) :=
    IeeeModel.dot_step_2 prec emax nan_plus nan_minus nan_opp nan_fma s0 s1 x0 x1 y0 y1 in
  fin t0 ->
  fin t1 /\
  (b2r t0, b2r t1) =
  dot_step_2 emin prec tie_even (b2r s0) (b2r s1) (b2r x0) (b2r x1) (b2r y0) (b2r y1).
Proof.
intros Hp4 s0 s1 x0 x1 y0 y1 Fs0 Fs1 Fx0 Fx1 Fy0 Fy1 Ns Nx Ny. rewrite dot_step_2_runB.
intros Hz.
destruct (dot_step_2_bridge Hp4 s0 s1 x0 x1 y0 y1 Fs0 Fs1 Fx0 Fx1 Fy0 Fy1 Ns Nx Ny Hz)
  as [F M].
split.
- now apply nth_fin.
- rewrite dot_step_2_runR. f_equal; now apply sim_nth.
Qed.

(** * sum_entry_step_2 *)

Lemma sum_entry_step_2_runB :
  forall s0 s1 x0 x1 : float,
  IeeeModel.sum_entry_step_2 prec emax nan_plus nan_minus s0 s1 x0 x1 =
  (nth 23 (runB IeeeModel.sum_entry_step_2_prog [s0; s1; x0; x1]) d0,
   nth 25 (runB IeeeModel.sum_entry_step_2_prog [s0; s1; x0; x1]) d0).
Proof.
intros. cbv [IeeeModel.sum_entry_step_2 IeeeModel.add_2_2 IeeeModel.two_sum
             IeeeModel.fast_two_sum run stepB nth app IeeeModel.sum_entry_step_2_prog].
reflexivity.
Qed.

Theorem sum_entry_step_2_bridge :
  (3 <= prec)%Z ->
  forall s0 s1 x0 x1 : float, fin s0 -> fin s1 -> fin x0 -> fin x1 ->
  normalized_2 emin prec (b2r s0) (b2r s1) -> normalized_2 emin prec (b2r x0) (b2r x1) ->
  fin (nth 23 (runB IeeeModel.sum_entry_step_2_prog [s0; s1; x0; x1]) d0) ->
  finite_all (runB IeeeModel.sum_entry_step_2_prog [s0; s1; x0; x1]) /\
  map b2r (runB IeeeModel.sum_entry_step_2_prog [s0; s1; x0; x1])
  = runR IeeeModel.sum_entry_step_2_prog [b2r s0; b2r s1; b2r x0; b2r x1].
Proof.
intros Hp3 s0 s1 x0 x1 Fs0 Fs1 Fx0 Fx1 Ns Nx Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.sum_entry_step_2_prog (firstn 19 IeeeModel.sum_entry_step_2_prog)
         19%nat 22%nat [s0; s1; x0; x1] 23%nat); trivial.
- repeat constructor; assumption.
- generalize (sum_entry_step_2_correct emin prec Hp3 (b2r s0) (b2r s1) (b2r x0) (b2r x1)
                Ns Nx).
  rewrite sum_entry_step_2_runR. intros [N _]. exact N.
Qed.

Theorem sum_entry_step_2_values :
  (3 <= prec)%Z ->
  forall s0 s1 x0 x1 : float, fin s0 -> fin s1 -> fin x0 -> fin x1 ->
  normalized_2 emin prec (b2r s0) (b2r s1) -> normalized_2 emin prec (b2r x0) (b2r x1) ->
  let '(t0, t1) := IeeeModel.sum_entry_step_2 prec emax nan_plus nan_minus s0 s1 x0 x1 in
  fin t0 ->
  fin t1 /\
  (b2r t0, b2r t1) = sum_entry_step_2 emin prec tie_even (b2r s0) (b2r s1) (b2r x0) (b2r x1).
Proof.
intros Hp3 s0 s1 x0 x1 Fs0 Fs1 Fx0 Fx1 Ns Nx. rewrite sum_entry_step_2_runB. intros Hz.
destruct (sum_entry_step_2_bridge Hp3 s0 s1 x0 x1 Fs0 Fs1 Fx0 Fx1 Ns Nx Hz) as [F M].
split.
- now apply nth_fin.
- rewrite sum_entry_step_2_runR. f_equal; now apply sim_nth.
Qed.

(** * sum_fast_entry_step_2 *)

Lemma sum_fast_entry_step_2_runB :
  forall s0 s1 x0 x1 : float,
  IeeeModel.sum_fast_entry_step_2 prec emax nan_plus nan_minus s0 s1 x0 x1 =
  (nth 14 (runB IeeeModel.sum_fast_entry_step_2_prog [s0; s1; x0; x1]) d0,
   nth 16 (runB IeeeModel.sum_fast_entry_step_2_prog [s0; s1; x0; x1]) d0).
Proof.
intros. cbv [IeeeModel.sum_fast_entry_step_2 IeeeModel.add_fast_2_2 IeeeModel.two_sum
             IeeeModel.fast_two_sum run stepB nth app IeeeModel.sum_fast_entry_step_2_prog].
reflexivity.
Qed.

Theorem sum_fast_entry_step_2_bridge :
  (2 <= prec)%Z ->
  forall s0 s1 x0 x1 : float, fin s0 -> fin s1 -> fin x0 -> fin x1 ->
  normalized_2 emin prec (b2r s0) (b2r s1) -> normalized_2 emin prec (b2r x0) (b2r x1) ->
  fin (nth 14 (runB IeeeModel.sum_fast_entry_step_2_prog [s0; s1; x0; x1]) d0) ->
  finite_all (runB IeeeModel.sum_fast_entry_step_2_prog [s0; s1; x0; x1]) /\
  map b2r (runB IeeeModel.sum_fast_entry_step_2_prog [s0; s1; x0; x1])
  = runR IeeeModel.sum_fast_entry_step_2_prog [b2r s0; b2r s1; b2r x0; b2r x1].
Proof.
intros Hp2 s0 s1 x0 x1 Fs0 Fs1 Fx0 Fx1 Ns Nx Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.sum_fast_entry_step_2_prog
         (firstn 10 IeeeModel.sum_fast_entry_step_2_prog) 6%nat 13%nat
         [s0; s1; x0; x1] 14%nat); trivial.
- repeat constructor; assumption.
- generalize (sum_fast_entry_step_2_correct emin prec Hp2 (b2r s0) (b2r s1) (b2r x0)
                (b2r x1) Ns Nx).
  rewrite sum_fast_entry_step_2_runR. intros [N _]. exact N.
Qed.

Theorem sum_fast_entry_step_2_values :
  (2 <= prec)%Z ->
  forall s0 s1 x0 x1 : float, fin s0 -> fin s1 -> fin x0 -> fin x1 ->
  normalized_2 emin prec (b2r s0) (b2r s1) -> normalized_2 emin prec (b2r x0) (b2r x1) ->
  let '(t0, t1) := IeeeModel.sum_fast_entry_step_2 prec emax nan_plus nan_minus s0 s1 x0 x1 in
  fin t0 ->
  fin t1 /\
  (b2r t0, b2r t1) =
  sum_fast_entry_step_2 emin prec tie_even (b2r s0) (b2r s1) (b2r x0) (b2r x1).
Proof.
intros Hp2 s0 s1 x0 x1 Fs0 Fs1 Fx0 Fx1 Ns Nx. rewrite sum_fast_entry_step_2_runB. intros Hz.
destruct (sum_fast_entry_step_2_bridge Hp2 s0 s1 x0 x1 Fs0 Fs1 Fx0 Fx1 Ns Nx Hz) as [F M].
split.
- now apply nth_fin.
- rewrite sum_fast_entry_step_2_runR. f_equal; now apply sim_nth.
Qed.

End IeeeSteps.

(** * The statements of proofs/gen/IeeeStatements.v *)

(* One limb: the program is one fused operation. *)
Theorem dot_step_1_ieee_bridge : dot_step_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp1 s x y Fs Fx Fy t Ft.
split.
- cbv [run stepB nth app IeeeModel.dot_step_1_prog].
  repeat constructor; first [assumption | exact Ft].
- exact (proj2 (fma_spec prec emax nan_fma x y s Fx Fy Fs) Ft).
Qed.

(* One limb: the guard, then one addition. The guard of a finite value is finite, with
   the same value (guard_finite, guard_val of IeeeOps.v), and in the real model it returns
   a number of the format unchanged (guard_real_any). *)
Theorem sum_entry_step_1_ieee_bridge : sum_entry_step_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp1 s x Fs Fx t Ft.
assert (Fg : finite (IeeeOperations.guard prec emax nan_plus x)).
{ unfold finite. rewrite (guard_finite prec emax nan_plus). exact Fx. }
split.
- cbv [run stepB nth app IeeeModel.sum_entry_step_1_prog].
  repeat constructor; first [assumption | exact Ft].
- unfold sum_entry_step_1. cbv zeta.
  rewrite (guard_real_any (ieee_emin prec emax) prec tie_even (val x) (b2r_format prec emax x)).
  generalize (proj2 (add_spec prec emax nan_plus s _ Fs Fg) Ft).
  rewrite (guard_val prec emax nan_plus). intros E. exact E.
Qed.

(* One limb: the guards of both factors, then one fused operation (rule R3, the factors of a
   fused operation). As for sum_entry_step_1, the guard of a finite value is finite with the
   same value, and in the real model it returns a number of the format unchanged. *)
Theorem dot_entry_step_1_ieee_bridge : dot_entry_step_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp1 s x y Fs Fx Fy t Ft.
assert (Gx : finite (IeeeOperations.guard prec emax nan_plus x)).
{ unfold finite. rewrite (guard_finite prec emax nan_plus). exact Fx. }
assert (Gy : finite (IeeeOperations.guard prec emax nan_plus y)).
{ unfold finite. rewrite (guard_finite prec emax nan_plus). exact Fy. }
split.
- cbv [run stepB nth app IeeeModel.dot_entry_step_1_prog].
  repeat constructor; first [assumption | exact Ft].
- unfold dot_entry_step_1. cbv zeta.
  rewrite (guard_real_any (ieee_emin prec emax) prec tie_even (val x) (b2r_format prec emax x)).
  rewrite (guard_real_any (ieee_emin prec emax) prec tie_even (val y) (b2r_format prec emax y)).
  generalize (proj2 (fma_spec prec emax nan_fma _ _ s Gx Gy Fs) Ft).
  rewrite !(guard_val prec emax nan_plus). intros E. exact E.
Qed.

Theorem dot_step_2_ieee_bridge : dot_step_2_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp4 s0 s1 x0 x1 y0 y1
  Fs0 Fs1 Fx0 Fx1 Fy0 Fy1 Ns Nx Ny.
generalize (dot_step_2_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp4
              s0 s1 x0 x1 y0 y1 Fs0 Fs1 Fx0 Fx1 Fy0 Fy1 Ns Nx Ny)
           (dot_step_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp4
              s0 s1 x0 x1 y0 y1 Fs0 Fs1 Fx0 Fx1 Fy0 Fy1 Ns Nx Ny).
rewrite (dot_step_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem dot_step_2_ieee_correct : dot_step_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp4 s0 s1 x0 x1 y0 y1
  Fs0 Fs1 Fx0 Fx1 Fy0 Fy1 Ns Nx Ny.
generalize (dot_step_2_ieee_bridge prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp4
              s0 s1 x0 x1 y0 y1 Fs0 Fs1 Fx0 Fx1 Fy0 Fy1 Ns Nx Ny)
           (dot_step_2_correct (ieee_emin prec emax) prec Hp4 (val s0) (val s1) (val x0)
              (val x1) (val y0) (val y1) Ns Nx Ny).
destruct (IeeeModel.dot_step_2 prec emax nan_plus nan_minus nan_opp nan_fma s0 s1 x0 x1 y0 y1)
  as [t0 t1].
intros B C Fz. destruct (B Fz) as [_ [Fz1 E]]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

Theorem sum_entry_step_2_ieee_bridge : sum_entry_step_2_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp3 s0 s1 x0 x1
  Fs0 Fs1 Fx0 Fx1 Ns Nx.
generalize (sum_entry_step_2_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp3
              s0 s1 x0 x1 Fs0 Fs1 Fx0 Fx1 Ns Nx)
           (sum_entry_step_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp3
              s0 s1 x0 x1 Fs0 Fs1 Fx0 Fx1 Ns Nx).
rewrite (sum_entry_step_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem sum_entry_step_2_ieee_correct : sum_entry_step_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus Hp3 s0 s1 x0 x1 Fs0 Fs1 Fx0 Fx1 Ns Nx.
generalize (sum_entry_step_2_ieee_bridge prec emax Hp He nan_plus nan_minus
              (fun x => nan_plus x x) (fun x y _ => nan_plus x y) Hp3
              s0 s1 x0 x1 Fs0 Fs1 Fx0 Fx1 Ns Nx)
           (sum_entry_step_2_correct (ieee_emin prec emax) prec Hp3 (val s0) (val s1)
              (val x0) (val x1) Ns Nx).
destruct (IeeeModel.sum_entry_step_2 prec emax nan_plus nan_minus s0 s1 x0 x1) as [t0 t1].
intros B C Fz. destruct (B Fz) as [_ [Fz1 E]]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

Theorem sum_fast_entry_step_2_ieee_bridge : sum_fast_entry_step_2_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp2 s0 s1 x0 x1
  Fs0 Fs1 Fx0 Fx1 Ns Nx.
generalize (sum_fast_entry_step_2_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp2
              s0 s1 x0 x1 Fs0 Fs1 Fx0 Fx1 Ns Nx)
           (sum_fast_entry_step_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp2
              s0 s1 x0 x1 Fs0 Fs1 Fx0 Fx1 Ns Nx).
rewrite (sum_fast_entry_step_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem sum_fast_entry_step_2_ieee_correct : sum_fast_entry_step_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus Hp2 s0 s1 x0 x1 Fs0 Fs1 Fx0 Fx1 Ns Nx.
generalize (sum_fast_entry_step_2_ieee_bridge prec emax Hp He nan_plus nan_minus
              (fun x => nan_plus x x) (fun x y _ => nan_plus x y) Hp2
              s0 s1 x0 x1 Fs0 Fs1 Fx0 Fx1 Ns Nx)
           (sum_fast_entry_step_2_correct (ieee_emin prec emax) prec Hp2 (val s0) (val s1)
              (val x0) (val x1) Ns Nx).
destruct (IeeeModel.sum_fast_entry_step_2 prec emax nan_plus nan_minus s0 s1 x0 x1)
  as [t0 t1].
intros B C Fz. destruct (B Fz) as [_ [Fz1 E]]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.
