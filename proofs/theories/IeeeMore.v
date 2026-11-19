(* add_2_1, mul_2_1 and add_fast_2_2 in the IEEE model (IeeeDraft.v), for finite operands
   that satisfy the requirements of the kernel.

   For each of the three kernels K:

   1. Bridge (K_bridge, K_values). If output limb 0 is finite then every value of the
      kernel is finite and equal, as a real number, to that of the real model. The values
      computed before output limb 0 are in its cone, which is checked by computation; the
      last two, the tail of the final fast_two_sum, are finite because the result of the
      real model is normalized (IeeeBridge.bridge_f2s, with K_correct).

   2. Correctness (K_values_correct). Hence, if z0 is finite: z1 is finite, z is
      normalized, and the bound of the real-model theorem holds. An overflow inside the
      kernel never produces a finite wrong result.

   These are instances of the theorem of IeeeBridge.v that covers every straight-line
   program ending with a Fast2Sum; nothing here is specific to a kernel beyond its
   program and its theorem in the real model.

   Not here: the third statement, a threshold on the operands under which no value
   overflows. It is a magnitude analysis written per kernel, as in IeeeAdd22.v and
   IeeeMul22.v.

   The statements, in the form of IeeeStatementsDraft.v, are at the end of the file. *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Normalized EFT Add21 Mul21 AddFast22 Program IeeeBridge
  IeeeStatementsDraft.
From Kairn Require IeeeDraft.
Import ListNotations.
Open Scope R_scope.

(** * The programs of IeeeDraft.v are the kernels of the real model *)

Lemma add_2_1_runR :
  forall emin prec choice x0 x1 a,
  add_2_1 emin prec choice x0 x1 a =
  (nth 10 (runR emin prec choice IeeeDraft.add_2_1_prog [x0; x1; a]) 0,
   nth 12 (runR emin prec choice IeeeDraft.add_2_1_prog [x0; x1; a]) 0).
Proof.
intros. cbv [add_2_1 two_sum fast_two_sum runR run stepR nth app IeeeDraft.add_2_1_prog].
reflexivity.
Qed.

Lemma mul_2_1_runR :
  forall emin prec choice x0 x1 a,
  mul_2_1 emin prec choice x0 x1 a =
  (nth 6 (runR emin prec choice IeeeDraft.mul_2_1_prog [x0; x1; a]) 0,
   nth 8 (runR emin prec choice IeeeDraft.mul_2_1_prog [x0; x1; a]) 0).
Proof.
intros. cbv [mul_2_1 two_prod fast_two_sum runR run stepR nth app IeeeDraft.mul_2_1_prog].
reflexivity.
Qed.

Lemma add_fast_2_2_runR :
  forall emin prec choice x0 x1 y0 y1,
  add_fast_2_2 emin prec choice x0 x1 y0 y1 =
  (nth 12 (runR emin prec choice IeeeDraft.add_fast_2_2_prog [x0; x1; y0; y1]) 0,
   nth 14 (runR emin prec choice IeeeDraft.add_fast_2_2_prog [x0; x1; y0; y1]) 0).
Proof.
intros. cbv [add_fast_2_2 two_sum fast_two_sum runR run stepR nth app
             IeeeDraft.add_fast_2_2_prog].
reflexivity.
Qed.

Section IeeeMore.
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

(** * add_2_1 *)

(* The program is the kernel of the IEEE model. *)
Lemma add_2_1_runB :
  forall x0 x1 a : float,
  IeeeDraft.add_2_1 prec emax nan_plus nan_minus x0 x1 a =
  (nth 10 (runB IeeeDraft.add_2_1_prog [x0; x1; a]) d0,
   nth 12 (runB IeeeDraft.add_2_1_prog [x0; x1; a]) d0).
Proof.
intros. cbv [IeeeDraft.add_2_1 IeeeDraft.two_sum IeeeDraft.fast_two_sum run stepB nth app
             IeeeDraft.add_2_1_prog].
reflexivity.
Qed.

Theorem add_2_1_bridge :
  (3 <= prec)%Z ->
  forall x0 x1 a : float, fin x0 -> fin x1 -> fin a ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  fin (nth 10 (runB IeeeDraft.add_2_1_prog [x0; x1; a]) d0) ->
  finite_all (runB IeeeDraft.add_2_1_prog [x0; x1; a]) /\
  map b2r (runB IeeeDraft.add_2_1_prog [x0; x1; a])
  = runR IeeeDraft.add_2_1_prog [b2r x0; b2r x1; b2r a].
Proof.
intros Hp3 x0 x1 a F0 F1 Fa Nx Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeDraft.add_2_1_prog (firstn 7 IeeeDraft.add_2_1_prog) 3%nat 9%nat
         [x0; x1; a] 10%nat); trivial.
- repeat constructor; assumption.
- generalize (add_2_1_correct emin prec Hp3 (b2r x0) (b2r x1) (b2r a) Nx
                (b2r_format prec emax a)).
  rewrite add_2_1_runR. intros [N _]. exact N.
Qed.

Theorem add_2_1_values :
  (3 <= prec)%Z ->
  forall x0 x1 a : float, fin x0 -> fin x1 -> fin a ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  let '(z0, z1) := IeeeDraft.add_2_1 prec emax nan_plus nan_minus x0 x1 a in
  fin z0 ->
  fin z1 /\
  (b2r z0, b2r z1) = add_2_1 emin prec tie_even (b2r x0) (b2r x1) (b2r a).
Proof.
intros Hp3 x0 x1 a F0 F1 Fa Nx. rewrite add_2_1_runB. intros Hz.
destruct (add_2_1_bridge Hp3 x0 x1 a F0 F1 Fa Nx Hz) as [F M]. split.
- now apply nth_fin.
- rewrite add_2_1_runR. f_equal; now apply sim_nth.
Qed.

Theorem add_2_1_values_correct :
  (3 <= prec)%Z ->
  forall x0 x1 a : float, fin x0 -> fin x1 -> fin a ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  let '(z0, z1) := IeeeDraft.add_2_1 prec emax nan_plus nan_minus x0 x1 a in
  fin z0 ->
  fin z1 /\
  normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs ((b2r z0 + b2r z1) - ((b2r x0 + b2r x1) + b2r a))
  <= 2 * u prec ^ 2 * Rabs ((b2r x0 + b2r x1) + b2r a).
Proof.
intros Hp3 x0 x1 a F0 F1 Fa Nx.
generalize (add_2_1_values Hp3 x0 x1 a F0 F1 Fa Nx)
           (add_2_1_correct emin prec Hp3 (b2r x0) (b2r x1) (b2r a) Nx
              (b2r_format prec emax a)).
destruct (IeeeDraft.add_2_1 prec emax nan_plus nan_minus x0 x1 a) as [z0 z1].
intros B C Fz. destruct (B Fz) as [Fz1 E]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

(** * mul_2_1 *)

Lemma mul_2_1_runB :
  forall x0 x1 a : float,
  IeeeDraft.mul_2_1 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 a =
  (nth 6 (runB IeeeDraft.mul_2_1_prog [x0; x1; a]) d0,
   nth 8 (runB IeeeDraft.mul_2_1_prog [x0; x1; a]) d0).
Proof.
intros. cbv [IeeeDraft.mul_2_1 IeeeDraft.two_prod IeeeDraft.fast_two_sum run stepB nth app
             IeeeDraft.mul_2_1_prog].
reflexivity.
Qed.

Theorem mul_2_1_bridge :
  (2 <= prec)%Z ->
  forall x0 x1 a : float, fin x0 -> fin x1 -> fin a ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  fin (nth 6 (runB IeeeDraft.mul_2_1_prog [x0; x1; a]) d0) ->
  finite_all (runB IeeeDraft.mul_2_1_prog [x0; x1; a]) /\
  map b2r (runB IeeeDraft.mul_2_1_prog [x0; x1; a])
  = runR IeeeDraft.mul_2_1_prog [b2r x0; b2r x1; b2r a].
Proof.
intros Hp2 x0 x1 a F0 F1 Fa Nx Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeDraft.mul_2_1_prog (firstn 3 IeeeDraft.mul_2_1_prog) 3%nat 5%nat
         [x0; x1; a] 6%nat); trivial.
- repeat constructor; assumption.
- generalize (mul_2_1_correct emin prec Hp2 (b2r x0) (b2r x1) (b2r a) Nx
                (b2r_format prec emax a)).
  rewrite mul_2_1_runR. intros [N _]. exact N.
Qed.

Theorem mul_2_1_values :
  (2 <= prec)%Z ->
  forall x0 x1 a : float, fin x0 -> fin x1 -> fin a ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  let '(z0, z1) := IeeeDraft.mul_2_1 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 a in
  fin z0 ->
  fin z1 /\
  (b2r z0, b2r z1) = mul_2_1 emin prec tie_even (b2r x0) (b2r x1) (b2r a).
Proof.
intros Hp2 x0 x1 a F0 F1 Fa Nx. rewrite mul_2_1_runB. intros Hz.
destruct (mul_2_1_bridge Hp2 x0 x1 a F0 F1 Fa Nx Hz) as [F M]. split.
- now apply nth_fin.
- rewrite mul_2_1_runR. f_equal; now apply sim_nth.
Qed.

Theorem mul_2_1_values_correct :
  (2 <= prec)%Z ->
  forall x0 x1 a : float, fin x0 -> fin x1 -> fin a ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  let '(z0, z1) := IeeeDraft.mul_2_1 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 a in
  fin z0 ->
  fin z1 /\
  normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs ((b2r z0 + b2r z1) - ((b2r x0 + b2r x1) * b2r a))
  <= 2 * u prec ^ 2 * Rabs ((b2r x0 + b2r x1) * b2r a) + 1 * eta emin.
Proof.
intros Hp2 x0 x1 a F0 F1 Fa Nx.
generalize (mul_2_1_values Hp2 x0 x1 a F0 F1 Fa Nx)
           (mul_2_1_correct emin prec Hp2 (b2r x0) (b2r x1) (b2r a) Nx
              (b2r_format prec emax a)).
destruct (IeeeDraft.mul_2_1 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 a) as [z0 z1].
intros B C Fz. destruct (B Fz) as [Fz1 E]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

(** * add_fast_2_2 *)

Lemma add_fast_2_2_runB :
  forall x0 x1 y0 y1 : float,
  IeeeDraft.add_fast_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 =
  (nth 12 (runB IeeeDraft.add_fast_2_2_prog [x0; x1; y0; y1]) d0,
   nth 14 (runB IeeeDraft.add_fast_2_2_prog [x0; x1; y0; y1]) d0).
Proof.
intros. cbv [IeeeDraft.add_fast_2_2 IeeeDraft.two_sum IeeeDraft.fast_two_sum run stepB nth app
             IeeeDraft.add_fast_2_2_prog].
reflexivity.
Qed.

Theorem add_fast_2_2_bridge :
  (2 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  fin (nth 12 (runB IeeeDraft.add_fast_2_2_prog [x0; x1; y0; y1]) d0) ->
  finite_all (runB IeeeDraft.add_fast_2_2_prog [x0; x1; y0; y1]) /\
  map b2r (runB IeeeDraft.add_fast_2_2_prog [x0; x1; y0; y1])
  = runR IeeeDraft.add_fast_2_2_prog [b2r x0; b2r x1; b2r y0; b2r y1].
Proof.
intros Hp2 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeDraft.add_fast_2_2_prog (firstn 8 IeeeDraft.add_fast_2_2_prog) 4%nat 11%nat
         [x0; x1; y0; y1] 12%nat); trivial.
- repeat constructor; assumption.
- generalize (add_fast_2_2_correct emin prec Hp2 (b2r x0) (b2r x1) (b2r y0) (b2r y1) Nx Ny).
  rewrite add_fast_2_2_runR. intros [N _]. exact N.
Qed.

Theorem add_fast_2_2_values :
  (2 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeDraft.add_fast_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  fin z0 ->
  fin z1 /\
  (b2r z0, b2r z1) = add_fast_2_2 emin prec tie_even (b2r x0) (b2r x1) (b2r y0) (b2r y1).
Proof.
intros Hp2 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny. rewrite add_fast_2_2_runB. intros Hz.
destruct (add_fast_2_2_bridge Hp2 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hz) as [F M]. split.
- now apply nth_fin.
- rewrite add_fast_2_2_runR. f_equal; now apply sim_nth.
Qed.

Theorem add_fast_2_2_values_correct :
  (2 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeDraft.add_fast_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  fin z0 ->
  fin z1 /\
  normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs ((b2r z0 + b2r z1) - ((b2r x0 + b2r x1) + (b2r y0 + b2r y1)))
  <= 3 * u prec ^ 2 * (Rabs (b2r x0 + b2r x1) + Rabs (b2r y0 + b2r y1)).
Proof.
intros Hp2 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
generalize (add_fast_2_2_values Hp2 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny)
           (add_fast_2_2_correct emin prec Hp2 (b2r x0) (b2r x1) (b2r y0) (b2r y1) Nx Ny).
destruct (IeeeDraft.add_fast_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1) as [z0 z1].
intros B C Fz. destruct (B Fz) as [Fz1 E]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

End IeeeMore.

(** * The statements of IeeeStatementsDraft.v *)

Theorem add_2_1_ieee_bridge : add_2_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 a F0 F1 Fa Nx.
generalize (add_2_1_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 a
              F0 F1 Fa Nx)
           (add_2_1_values prec emax nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 a
              F0 F1 Fa Nx).
rewrite (add_2_1_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem add_2_1_ieee_correct : add_2_1_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus Hp3 x0 x1 a F0 F1 Fa Nx.
exact (add_2_1_values_correct prec emax nan_plus nan_minus
         (fun x => nan_plus x x) (fun x y _ => nan_plus x y) Hp3 x0 x1 a F0 F1 Fa Nx).
Qed.

Theorem mul_2_1_ieee_bridge : mul_2_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 a F0 F1 Fa Nx.
generalize (mul_2_1_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 a
              F0 F1 Fa Nx)
           (mul_2_1_values prec emax nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 a
              F0 F1 Fa Nx).
rewrite (mul_2_1_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem mul_2_1_ieee_correct : mul_2_1_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 a F0 F1 Fa Nx.
exact (mul_2_1_values_correct prec emax nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 a
         F0 F1 Fa Nx).
Qed.

Theorem add_fast_2_2_ieee_bridge : add_fast_2_2_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
generalize (add_fast_2_2_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 y0 y1
              F0 F1 G0 G1 Nx Ny)
           (add_fast_2_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 y0 y1
              F0 F1 G0 G1 Nx Ny).
rewrite (add_fast_2_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem add_fast_2_2_ieee_correct : add_fast_2_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus Hp2 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
exact (add_fast_2_2_values_correct prec emax nan_plus nan_minus
         (fun x => nan_plus x x) (fun x y _ => nan_plus x y) Hp2 x0 x1 y0 y1
         F0 F1 G0 G1 Nx Ny).
Qed.
