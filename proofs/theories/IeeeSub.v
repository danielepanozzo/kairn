(* sub_2_2, sub_2_1, sub_1_2 and mul_pow2_2 in the IEEE model (proofs/gen/IeeeModel.v), for finite
   operands that satisfy the requirements of the kernel.

   As in IeeeMore.v, for each of the four kernels K:

   1. Bridge (K_bridge, K_values). If output limb 0 is finite then every value of the
      kernel is finite and equal, as a real number, to that of the real model. The values
      computed before output limb 0 are in its cone, which is checked by computation; the
      tail of the final fast_two_sum is finite because the result of the real model is
      normalized (IeeeBridge.bridge_f2s, with K_correct).

   2. Correctness (K_values_correct). Hence, if z0 is finite: z1 is finite, z is
      normalized, and the bound of the real-model theorem holds.

   The subtractions negate an operand and call an addition; a sign change is exact and
   keeps a non-finite value non-finite, so their programs fit the same theorem. The
   programs of sub_2_1 and sub_1_2 guard the one-limb operand, as add_2_1 does, and the
   guard of a number of the format is that number (Guard.v).

   The statements, in the form of proofs/gen/IeeeStatements.v, are at the end of the file. *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Guard Normalized EFT Sign MulPow2 Program IeeeBridge
  IeeeVocabulary.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Import ListNotations.
Open Scope R_scope.

(** * The programs of proofs/gen/IeeeModel.v are the kernels of the real model *)

Lemma sub_2_2_runR :
  forall emin prec choice x0 x1 y0 y1,
  sub_2_2 emin prec choice x0 x1 y0 y1 =
  (nth 23 (runR emin prec choice IeeeModel.sub_2_2_prog [x0; x1; y0; y1]) 0,
   nth 25 (runR emin prec choice IeeeModel.sub_2_2_prog [x0; x1; y0; y1]) 0).
Proof.
intros. cbv [sub_2_2 add_2_2 two_sum fast_two_sum runR run stepR nth app
             IeeeModel.sub_2_2_prog].
reflexivity.
Qed.

Lemma sub_2_1_runR :
  forall emin prec choice x0 x1 a,
  generic_format radix2 (FLT_exp emin prec) a ->
  sub_2_1 emin prec choice x0 x1 a =
  (nth 12 (runR emin prec choice IeeeModel.sub_2_1_prog [x0; x1; a]) 0,
   nth 14 (runR emin prec choice IeeeModel.sub_2_1_prog [x0; x1; a]) 0).
Proof.
intros emin prec choice x0 x1 a Fa.
cbv [sub_2_1 add_2_1 two_sum fast_two_sum runR run stepR nth app IeeeModel.sub_2_1_prog].
rewrite ?(guard_real_any emin prec choice (- a) (generic_format_opp _ _ _ Fa)). reflexivity.
Qed.

Lemma sub_1_2_runR :
  forall emin prec choice a y0 y1,
  generic_format radix2 (FLT_exp emin prec) a ->
  sub_1_2 emin prec choice a y0 y1 =
  (nth 13 (runR emin prec choice IeeeModel.sub_1_2_prog [a; y0; y1]) 0,
   nth 15 (runR emin prec choice IeeeModel.sub_1_2_prog [a; y0; y1]) 0).
Proof.
intros emin prec choice a y0 y1 Fa.
cbv [sub_1_2 add_2_1 two_sum fast_two_sum runR run stepR nth app IeeeModel.sub_1_2_prog].
rewrite ?(guard_real_any emin prec choice a Fa). reflexivity.
Qed.

Lemma mul_pow2_2_runR :
  forall emin prec choice x0 x1 c,
  mul_pow2_2 emin prec choice x0 x1 c =
  (nth 5 (runR emin prec choice IeeeModel.mul_pow2_2_prog [x0; x1; c]) 0,
   nth 7 (runR emin prec choice IeeeModel.mul_pow2_2_prog [x0; x1; c]) 0).
Proof.
intros. cbv [mul_pow2_2 fast_two_sum runR run stepR nth app IeeeModel.mul_pow2_2_prog].
reflexivity.
Qed.

Section IeeeSub.
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

(** * sub_2_2 *)

Lemma sub_2_2_runB :
  forall x0 x1 y0 y1 : float,
  IeeeModel.sub_2_2 prec emax nan_plus nan_minus nan_opp x0 x1 y0 y1 =
  (nth 23 (runB IeeeModel.sub_2_2_prog [x0; x1; y0; y1]) d0,
   nth 25 (runB IeeeModel.sub_2_2_prog [x0; x1; y0; y1]) d0).
Proof.
intros. cbv [IeeeModel.sub_2_2 IeeeModel.add_2_2 IeeeModel.two_sum IeeeModel.fast_two_sum
             run stepB nth app IeeeModel.sub_2_2_prog].
reflexivity.
Qed.

Theorem sub_2_2_bridge :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  fin (nth 23 (runB IeeeModel.sub_2_2_prog [x0; x1; y0; y1]) d0) ->
  finite_all (runB IeeeModel.sub_2_2_prog [x0; x1; y0; y1]) /\
  map b2r (runB IeeeModel.sub_2_2_prog [x0; x1; y0; y1])
  = runR IeeeModel.sub_2_2_prog [b2r x0; b2r x1; b2r y0; b2r y1].
Proof.
intros Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.sub_2_2_prog (firstn 19 IeeeModel.sub_2_2_prog) 19%nat 22%nat
         [x0; x1; y0; y1] 23%nat); trivial.
- repeat constructor; assumption.
- generalize (sub_2_2_correct emin prec Hp3 (b2r x0) (b2r x1) (b2r y0) (b2r y1) Nx Ny).
  rewrite sub_2_2_runR. intros [N _]. exact N.
Qed.

Theorem sub_2_2_values :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.sub_2_2 prec emax nan_plus nan_minus nan_opp x0 x1 y0 y1 in
  fin z0 ->
  fin z1 /\
  (b2r z0, b2r z1) = sub_2_2 emin prec tie_even (b2r x0) (b2r x1) (b2r y0) (b2r y1).
Proof.
intros Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny. rewrite sub_2_2_runB. intros Hz.
destruct (sub_2_2_bridge Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hz) as [F M]. split.
- now apply nth_fin.
- rewrite sub_2_2_runR. f_equal; now apply sim_nth.
Qed.

Theorem sub_2_2_values_correct :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.sub_2_2 prec emax nan_plus nan_minus nan_opp x0 x1 y0 y1 in
  fin z0 ->
  fin z1 /\
  normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs ((b2r z0 + b2r z1) - ((b2r x0 + b2r x1) - (b2r y0 + b2r y1)))
  <= (3 / (1 - (4 * u prec))) * u prec ^ 2 * Rabs ((b2r x0 + b2r x1) - (b2r y0 + b2r y1)).
Proof.
intros Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
generalize (sub_2_2_values Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny)
           (sub_2_2_correct emin prec Hp3 (b2r x0) (b2r x1) (b2r y0) (b2r y1) Nx Ny).
destruct (IeeeModel.sub_2_2 prec emax nan_plus nan_minus nan_opp x0 x1 y0 y1) as [z0 z1].
intros B C Fz. destruct (B Fz) as [Fz1 E]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

(** * sub_2_1 *)

Lemma sub_2_1_runB :
  forall x0 x1 a : float,
  IeeeModel.sub_2_1 prec emax nan_plus nan_minus nan_opp x0 x1 a =
  (nth 12 (runB IeeeModel.sub_2_1_prog [x0; x1; a]) d0,
   nth 14 (runB IeeeModel.sub_2_1_prog [x0; x1; a]) d0).
Proof.
intros. cbv [IeeeModel.sub_2_1 IeeeModel.add_2_1 IeeeModel.two_sum IeeeModel.fast_two_sum
             run stepB nth app IeeeModel.sub_2_1_prog].
reflexivity.
Qed.

Theorem sub_2_1_bridge :
  (3 <= prec)%Z ->
  forall x0 x1 a : float, fin x0 -> fin x1 -> fin a ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  fin (nth 12 (runB IeeeModel.sub_2_1_prog [x0; x1; a]) d0) ->
  finite_all (runB IeeeModel.sub_2_1_prog [x0; x1; a]) /\
  map b2r (runB IeeeModel.sub_2_1_prog [x0; x1; a])
  = runR IeeeModel.sub_2_1_prog [b2r x0; b2r x1; b2r a].
Proof.
intros Hp3 x0 x1 a F0 F1 Fa Nx Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.sub_2_1_prog (firstn 9 IeeeModel.sub_2_1_prog) 5%nat 11%nat
         [x0; x1; a] 12%nat); trivial.
- repeat constructor; assumption.
- generalize (sub_2_1_correct emin prec Hp3 (b2r x0) (b2r x1) (b2r a) Nx
                (b2r_format prec emax a)).
  rewrite (sub_2_1_runR emin prec tie_even _ _ _ (b2r_format prec emax a)).
  intros [N _]. exact N.
Qed.

Theorem sub_2_1_values :
  (3 <= prec)%Z ->
  forall x0 x1 a : float, fin x0 -> fin x1 -> fin a ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  let '(z0, z1) := IeeeModel.sub_2_1 prec emax nan_plus nan_minus nan_opp x0 x1 a in
  fin z0 ->
  fin z1 /\
  (b2r z0, b2r z1) = sub_2_1 emin prec tie_even (b2r x0) (b2r x1) (b2r a).
Proof.
intros Hp3 x0 x1 a F0 F1 Fa Nx. rewrite sub_2_1_runB. intros Hz.
destruct (sub_2_1_bridge Hp3 x0 x1 a F0 F1 Fa Nx Hz) as [F M]. split.
- now apply nth_fin.
- rewrite (sub_2_1_runR emin prec tie_even _ _ _ (b2r_format prec emax a)).
  f_equal; now apply sim_nth.
Qed.

Theorem sub_2_1_values_correct :
  (3 <= prec)%Z ->
  forall x0 x1 a : float, fin x0 -> fin x1 -> fin a ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  let '(z0, z1) := IeeeModel.sub_2_1 prec emax nan_plus nan_minus nan_opp x0 x1 a in
  fin z0 ->
  fin z1 /\
  normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs ((b2r z0 + b2r z1) - ((b2r x0 + b2r x1) - b2r a))
  <= 2 * u prec ^ 2 * Rabs ((b2r x0 + b2r x1) - b2r a).
Proof.
intros Hp3 x0 x1 a F0 F1 Fa Nx.
generalize (sub_2_1_values Hp3 x0 x1 a F0 F1 Fa Nx)
           (sub_2_1_correct emin prec Hp3 (b2r x0) (b2r x1) (b2r a) Nx
              (b2r_format prec emax a)).
destruct (IeeeModel.sub_2_1 prec emax nan_plus nan_minus nan_opp x0 x1 a) as [z0 z1].
intros B C Fz. destruct (B Fz) as [Fz1 E]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

(** * sub_1_2 *)

Lemma sub_1_2_runB :
  forall a y0 y1 : float,
  IeeeModel.sub_1_2 prec emax nan_plus nan_minus nan_opp a y0 y1 =
  (nth 13 (runB IeeeModel.sub_1_2_prog [a; y0; y1]) d0,
   nth 15 (runB IeeeModel.sub_1_2_prog [a; y0; y1]) d0).
Proof.
intros. cbv [IeeeModel.sub_1_2 IeeeModel.add_2_1 IeeeModel.two_sum IeeeModel.fast_two_sum
             run stepB nth app IeeeModel.sub_1_2_prog].
reflexivity.
Qed.

Theorem sub_1_2_bridge :
  (3 <= prec)%Z ->
  forall a y0 y1 : float, fin a -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r y0) (b2r y1) ->
  fin (nth 13 (runB IeeeModel.sub_1_2_prog [a; y0; y1]) d0) ->
  finite_all (runB IeeeModel.sub_1_2_prog [a; y0; y1]) /\
  map b2r (runB IeeeModel.sub_1_2_prog [a; y0; y1])
  = runR IeeeModel.sub_1_2_prog [b2r a; b2r y0; b2r y1].
Proof.
intros Hp3 a y0 y1 Fa G0 G1 Ny Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.sub_1_2_prog (firstn 10 IeeeModel.sub_1_2_prog) 6%nat 12%nat
         [a; y0; y1] 13%nat); trivial.
- repeat constructor; assumption.
- generalize (sub_1_2_correct emin prec Hp3 (b2r a) (b2r y0) (b2r y1)
                (b2r_format prec emax a) Ny).
  rewrite (sub_1_2_runR emin prec tie_even _ _ _ (b2r_format prec emax a)).
  intros [N _]. exact N.
Qed.

Theorem sub_1_2_values :
  (3 <= prec)%Z ->
  forall a y0 y1 : float, fin a -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.sub_1_2 prec emax nan_plus nan_minus nan_opp a y0 y1 in
  fin z0 ->
  fin z1 /\
  (b2r z0, b2r z1) = sub_1_2 emin prec tie_even (b2r a) (b2r y0) (b2r y1).
Proof.
intros Hp3 a y0 y1 Fa G0 G1 Ny. rewrite sub_1_2_runB. intros Hz.
destruct (sub_1_2_bridge Hp3 a y0 y1 Fa G0 G1 Ny Hz) as [F M]. split.
- now apply nth_fin.
- rewrite (sub_1_2_runR emin prec tie_even _ _ _ (b2r_format prec emax a)).
  f_equal; now apply sim_nth.
Qed.

Theorem sub_1_2_values_correct :
  (3 <= prec)%Z ->
  forall a y0 y1 : float, fin a -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.sub_1_2 prec emax nan_plus nan_minus nan_opp a y0 y1 in
  fin z0 ->
  fin z1 /\
  normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs ((b2r z0 + b2r z1) - (b2r a - (b2r y0 + b2r y1)))
  <= 2 * u prec ^ 2 * Rabs (b2r a - (b2r y0 + b2r y1)).
Proof.
intros Hp3 a y0 y1 Fa G0 G1 Ny.
generalize (sub_1_2_values Hp3 a y0 y1 Fa G0 G1 Ny)
           (sub_1_2_correct emin prec Hp3 (b2r a) (b2r y0) (b2r y1)
              (b2r_format prec emax a) Ny).
destruct (IeeeModel.sub_1_2 prec emax nan_plus nan_minus nan_opp a y0 y1) as [z0 z1].
intros B C Fz. destruct (B Fz) as [Fz1 E]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

(** * mul_pow2_2 *)

Lemma mul_pow2_2_runB :
  forall x0 x1 c : float,
  IeeeModel.mul_pow2_2 prec emax nan_plus nan_minus nan_fma x0 x1 c =
  (nth 5 (runB IeeeModel.mul_pow2_2_prog [x0; x1; c]) d0,
   nth 7 (runB IeeeModel.mul_pow2_2_prog [x0; x1; c]) d0).
Proof.
intros. cbv [IeeeModel.mul_pow2_2 IeeeModel.fast_two_sum run stepB nth app
             IeeeModel.mul_pow2_2_prog].
reflexivity.
Qed.

Theorem mul_pow2_2_bridge :
  (2 <= prec)%Z ->
  forall x0 x1 c : float, fin x0 -> fin x1 -> fin c ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> (exists n : Z, b2r c = bpow radix2 n) ->
  fin (nth 5 (runB IeeeModel.mul_pow2_2_prog [x0; x1; c]) d0) ->
  finite_all (runB IeeeModel.mul_pow2_2_prog [x0; x1; c]) /\
  map b2r (runB IeeeModel.mul_pow2_2_prog [x0; x1; c])
  = runR IeeeModel.mul_pow2_2_prog [b2r x0; b2r x1; b2r c].
Proof.
intros Hp2 x0 x1 c F0 F1 Fc Nx Pc Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.mul_pow2_2_prog (firstn 2 IeeeModel.mul_pow2_2_prog) 3%nat 4%nat
         [x0; x1; c] 5%nat); trivial.
- repeat constructor; assumption.
- generalize (mul_pow2_2_correct emin prec Hp2 (b2r x0) (b2r x1) (b2r c) Nx
                (b2r_format prec emax c) Pc).
  rewrite mul_pow2_2_runR. intros [N _]. exact N.
Qed.

Theorem mul_pow2_2_values :
  (2 <= prec)%Z ->
  forall x0 x1 c : float, fin x0 -> fin x1 -> fin c ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> (exists n : Z, b2r c = bpow radix2 n) ->
  let '(z0, z1) := IeeeModel.mul_pow2_2 prec emax nan_plus nan_minus nan_fma x0 x1 c in
  fin z0 ->
  fin z1 /\
  (b2r z0, b2r z1) = mul_pow2_2 emin prec tie_even (b2r x0) (b2r x1) (b2r c).
Proof.
intros Hp2 x0 x1 c F0 F1 Fc Nx Pc. rewrite mul_pow2_2_runB. intros Hz.
destruct (mul_pow2_2_bridge Hp2 x0 x1 c F0 F1 Fc Nx Pc Hz) as [F M]. split.
- now apply nth_fin.
- rewrite mul_pow2_2_runR. f_equal; now apply sim_nth.
Qed.

Theorem mul_pow2_2_values_correct :
  (2 <= prec)%Z ->
  forall x0 x1 c : float, fin x0 -> fin x1 -> fin c ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> (exists n : Z, b2r c = bpow radix2 n) ->
  let '(z0, z1) := IeeeModel.mul_pow2_2 prec emax nan_plus nan_minus nan_fma x0 x1 c in
  fin z0 ->
  fin z1 /\
  normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs ((b2r z0 + b2r z1) - ((b2r x0 + b2r x1) * b2r c)) <= 1 * eta emin.
Proof.
intros Hp2 x0 x1 c F0 F1 Fc Nx Pc.
generalize (mul_pow2_2_values Hp2 x0 x1 c F0 F1 Fc Nx Pc)
           (mul_pow2_2_correct emin prec Hp2 (b2r x0) (b2r x1) (b2r c) Nx
              (b2r_format prec emax c) Pc).
destruct (IeeeModel.mul_pow2_2 prec emax nan_plus nan_minus nan_fma x0 x1 c) as [z0 z1].
intros B C Fz. destruct (B Fz) as [Fz1 E]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

End IeeeSub.

(** * The statements of proofs/gen/IeeeStatements.v *)

Theorem sub_2_2_ieee_bridge : sub_2_2_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
generalize (sub_2_2_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 y0 y1
              F0 F1 G0 G1 Nx Ny)
           (sub_2_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 y0 y1
              F0 F1 G0 G1 Nx Ny).
rewrite (sub_2_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem sub_2_2_ieee_correct : sub_2_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
exact (sub_2_2_values_correct prec emax nan_plus nan_minus nan_opp (fun x y _ => nan_plus x y)
         Hp3 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
Qed.

Theorem sub_2_1_ieee_bridge : sub_2_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 a F0 F1 Fa Nx.
generalize (sub_2_1_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 a F0 F1 Fa Nx)
           (sub_2_1_values prec emax nan_plus nan_minus nan_opp nan_fma Hp3 x0 x1 a F0 F1 Fa Nx).
rewrite (sub_2_1_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem sub_2_1_ieee_correct : sub_2_1_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp Hp3 x0 x1 a F0 F1 Fa Nx.
exact (sub_2_1_values_correct prec emax nan_plus nan_minus nan_opp (fun x y _ => nan_plus x y)
         Hp3 x0 x1 a F0 F1 Fa Nx).
Qed.

Theorem sub_1_2_ieee_bridge : sub_1_2_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp3 a y0 y1 Fa G0 G1 Ny.
generalize (sub_1_2_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp3 a y0 y1 Fa G0 G1 Ny)
           (sub_1_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp3 a y0 y1 Fa G0 G1 Ny).
rewrite (sub_1_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem sub_1_2_ieee_correct : sub_1_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp Hp3 a y0 y1 Fa G0 G1 Ny.
exact (sub_1_2_values_correct prec emax nan_plus nan_minus nan_opp (fun x y _ => nan_plus x y)
         Hp3 a y0 y1 Fa G0 G1 Ny).
Qed.

Theorem mul_pow2_2_ieee_bridge : mul_pow2_2_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 c F0 F1 Fc Nx Pc.
generalize (mul_pow2_2_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 c
              F0 F1 Fc Nx Pc)
           (mul_pow2_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp2 x0 x1 c
              F0 F1 Fc Nx Pc).
rewrite (mul_pow2_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem mul_pow2_2_ieee_correct : mul_pow2_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_fma Hp2 x0 x1 c F0 F1 Fc Nx Pc.
exact (mul_pow2_2_values_correct prec emax nan_plus nan_minus (fun x => nan_plus x x) nan_fma
         Hp2 x0 x1 c F0 F1 Fc Nx Pc).
Qed.
