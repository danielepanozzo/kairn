(* The steps of the maps in the IEEE model (proofs/gen/IeeeModel.v): the generated
   statements K_ieee_bridge_spec of the sixteen steps add_1_1, sub_1_1, add_entry_step_k,
   sub_entry_step_k, scale_step_k, mul_pow2_step_k, axpy_step_1, axpy_entry_step_1,
   axpy_step_2, axpy_entry_step_2, axpy_step_2_1 and axpy_entry_step_2_1, K_ieee_spec of
   the eight of two limbs (proofs/gen/IeeeStatements.v), and K_ieee_lead_spec of those
   sixteen and of sub_2_2, the step of sub_2 (proofs/gen/IeeeFoldStatements.v).

   1. Bridge (K_ieee_bridge). For finite operands that satisfy the requirements of the
      kernel: if the leading limb of the result is finite then every value the kernel
      computes is finite, and the result is, as real numbers, that of the real model on
      the values of the operands.
      - One limb. Every value of the program is in the cone of the result, which is
        checked by computation (Program.covers): a finite result means that every value
        is finite (covers_sound of IeeeBridge.v), and then every value is that of the
        real model (run_sim). This is bridge_cone below. The program of axpy_step_1 is
        a product then a sum; that of an entry step guards its operands first (the
        guard, RN (x + 0), is an instruction of the program like any other).
      - Two limbs. The programs end with a Fast2Sum whose first result is the leading
        limb: the values computed before it are in its cone, again by computation, and
        the last two are finite because the result of the real model is normalized
        (bridge_f2s_prog of IeeeBridge.v, with K_correct of MapSteps.v), as for the
        steps of the folds (IeeeSteps.v) and the subtractions (IeeeSub.v). The steps of
        axpy are mul_2_2 or mul_2_1 followed by add_2_2: the tail of the Fast2Sum that
        ends the product is in the cone, since the second limb of the product is an
        operand of the sum.

   2. Correctness (K_ieee_correct), for the steps of two limbs: hence, if the leading
      limb of the result is finite, so is the second, the result is normalized, and the
      bound of the real-model theorem holds.

   3. The leading limb (K_ieee_lead), for any operands, with no requirement: if the
      leading limb of the result is finite, so is the leading limb of every operand
      named by the statement (the scalars included). The value at an input position is
      in the cone of the leading limb of the result, by computation, and a value in the
      cone of a finite value is finite (cone_sound of IeeeBridge.v, which assumes
      nothing of the inputs): lead_cone below. The second limbs are not in the
      statement: a finite leading limb of a canonical pair makes the second finite.

   Each program is the kernel of the generated model, and the real-model program the
   kernel of proofs/gen/Model.v: K_runB and K_runR, by computation, as in IeeeSteps.v. *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements IeeeFoldStatements.
From Kairn Require Import Format Guard Normalized Program IeeeBridge IeeeVocabulary IeeeOps
  MapSteps IeeeSub.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Import ListNotations.
Open Scope R_scope.

(** * The programs of proofs/gen/IeeeModel.v are the kernels of the real model *)

Lemma add_1_1_runR :
  forall emin prec choice a b,
  add_1_1 emin prec choice a b = nth 2 (runR emin prec choice IeeeModel.add_1_1_prog [a; b]) 0.
Proof. intros. cbv [add_1_1 runR run stepR nth app IeeeModel.add_1_1_prog]. reflexivity. Qed.

Lemma sub_1_1_runR :
  forall emin prec choice a b,
  sub_1_1 emin prec choice a b = nth 2 (runR emin prec choice IeeeModel.sub_1_1_prog [a; b]) 0.
Proof. intros. cbv [sub_1_1 runR run stepR nth app IeeeModel.sub_1_1_prog]. reflexivity. Qed.

Lemma add_entry_step_1_runR :
  forall emin prec choice x y,
  add_entry_step_1 emin prec choice x y =
  nth 4 (runR emin prec choice IeeeModel.add_entry_step_1_prog [x; y]) 0.
Proof.
intros. cbv [add_entry_step_1 add_1_1 runR run stepR nth app IeeeModel.add_entry_step_1_prog].
reflexivity.
Qed.

Lemma sub_entry_step_1_runR :
  forall emin prec choice x y,
  sub_entry_step_1 emin prec choice x y =
  nth 4 (runR emin prec choice IeeeModel.sub_entry_step_1_prog [x; y]) 0.
Proof.
intros. cbv [sub_entry_step_1 sub_1_1 runR run stepR nth app IeeeModel.sub_entry_step_1_prog].
reflexivity.
Qed.

Lemma scale_step_1_runR :
  forall emin prec choice x a,
  scale_step_1 emin prec choice x a =
  nth 2 (runR emin prec choice IeeeModel.scale_step_1_prog [x; a]) 0.
Proof.
intros. cbv [scale_step_1 mul_1_1 runR run stepR nth app IeeeModel.scale_step_1_prog].
reflexivity.
Qed.

Lemma mul_pow2_step_1_runR :
  forall emin prec choice x c,
  mul_pow2_step_1 emin prec choice x c =
  nth 2 (runR emin prec choice IeeeModel.mul_pow2_step_1_prog [x; c]) 0.
Proof.
intros. cbv [mul_pow2_step_1 runR run stepR nth app IeeeModel.mul_pow2_step_1_prog].
reflexivity.
Qed.

Lemma axpy_step_1_runR :
  forall emin prec choice a x y,
  axpy_step_1 emin prec choice a x y =
  nth 4 (runR emin prec choice IeeeModel.axpy_step_1_prog [a; x; y]) 0.
Proof.
intros. cbv [axpy_step_1 mul_1_1 add_1_1 runR run stepR nth app IeeeModel.axpy_step_1_prog].
reflexivity.
Qed.

Lemma axpy_entry_step_1_runR :
  forall emin prec choice a x y,
  axpy_entry_step_1 emin prec choice a x y =
  nth 5 (runR emin prec choice IeeeModel.axpy_entry_step_1_prog [a; x; y]) 0.
Proof.
intros.
cbv [axpy_entry_step_1 mul_1_1 add_1_1 runR run stepR nth app IeeeModel.axpy_entry_step_1_prog].
reflexivity.
Qed.

Lemma add_entry_step_2_runR :
  forall emin prec choice x0 x1 y0 y1,
  add_entry_step_2 emin prec choice x0 x1 y0 y1 =
  (nth 25 (runR emin prec choice IeeeModel.add_entry_step_2_prog [x0; x1; y0; y1]) 0,
   nth 27 (runR emin prec choice IeeeModel.add_entry_step_2_prog [x0; x1; y0; y1]) 0).
Proof.
intros. cbv [add_entry_step_2 add_2_2 two_sum fast_two_sum runR run stepR nth app
             IeeeModel.add_entry_step_2_prog].
reflexivity.
Qed.

Lemma sub_entry_step_2_runR :
  forall emin prec choice x0 x1 y0 y1,
  sub_entry_step_2 emin prec choice x0 x1 y0 y1 =
  (nth 27 (runR emin prec choice IeeeModel.sub_entry_step_2_prog [x0; x1; y0; y1]) 0,
   nth 29 (runR emin prec choice IeeeModel.sub_entry_step_2_prog [x0; x1; y0; y1]) 0).
Proof.
intros. cbv [sub_entry_step_2 sub_2_2 add_2_2 two_sum fast_two_sum runR run stepR nth app
             IeeeModel.sub_entry_step_2_prog].
reflexivity.
Qed.

Lemma scale_step_2_runR :
  forall emin prec choice x0 x1 a,
  scale_step_2 emin prec choice x0 x1 a =
  (nth 6 (runR emin prec choice IeeeModel.scale_step_2_prog [x0; x1; a]) 0,
   nth 8 (runR emin prec choice IeeeModel.scale_step_2_prog [x0; x1; a]) 0).
Proof.
intros. cbv [scale_step_2 mul_2_1 two_prod fast_two_sum runR run stepR nth app
             IeeeModel.scale_step_2_prog].
reflexivity.
Qed.

Lemma mul_pow2_step_2_runR :
  forall emin prec choice x0 x1 c,
  mul_pow2_step_2 emin prec choice x0 x1 c =
  (nth 5 (runR emin prec choice IeeeModel.mul_pow2_step_2_prog [x0; x1; c]) 0,
   nth 7 (runR emin prec choice IeeeModel.mul_pow2_step_2_prog [x0; x1; c]) 0).
Proof.
intros. cbv [mul_pow2_step_2 mul_pow2_2 fast_two_sum runR run stepR nth app
             IeeeModel.mul_pow2_step_2_prog].
reflexivity.
Qed.

Lemma axpy_step_2_runR :
  forall emin prec choice a0 a1 x0 x1 y0 y1,
  axpy_step_2 emin prec choice a0 a1 x0 x1 y0 y1 =
  (nth 32 (runR emin prec choice IeeeModel.axpy_step_2_prog [a0; a1; x0; x1; y0; y1]) 0,
   nth 34 (runR emin prec choice IeeeModel.axpy_step_2_prog [a0; a1; x0; x1; y0; y1]) 0).
Proof.
intros. cbv [axpy_step_2 mul_2_2 two_prod add_2_2 two_sum fast_two_sum runR run stepR nth app
             IeeeModel.axpy_step_2_prog].
reflexivity.
Qed.

Lemma axpy_entry_step_2_runR :
  forall emin prec choice a0 a1 x0 x1 y0 y1,
  axpy_entry_step_2 emin prec choice a0 a1 x0 x1 y0 y1 =
  (nth 34 (runR emin prec choice IeeeModel.axpy_entry_step_2_prog [a0; a1; x0; x1; y0; y1]) 0,
   nth 36 (runR emin prec choice IeeeModel.axpy_entry_step_2_prog [a0; a1; x0; x1; y0; y1]) 0).
Proof.
intros. cbv [axpy_entry_step_2 mul_2_2 two_prod add_2_2 two_sum fast_two_sum runR run stepR
             nth app IeeeModel.axpy_entry_step_2_prog].
reflexivity.
Qed.

Lemma axpy_step_2_1_runR :
  forall emin prec choice a x0 x1 y0 y1,
  axpy_step_2_1 emin prec choice a x0 x1 y0 y1 =
  (nth 28 (runR emin prec choice IeeeModel.axpy_step_2_1_prog [a; x0; x1; y0; y1]) 0,
   nth 30 (runR emin prec choice IeeeModel.axpy_step_2_1_prog [a; x0; x1; y0; y1]) 0).
Proof.
intros. cbv [axpy_step_2_1 mul_2_1 two_prod add_2_2 two_sum fast_two_sum runR run stepR nth app
             IeeeModel.axpy_step_2_1_prog].
reflexivity.
Qed.

Lemma axpy_entry_step_2_1_runR :
  forall emin prec choice a x0 x1 y0 y1,
  axpy_entry_step_2_1 emin prec choice a x0 x1 y0 y1 =
  (nth 30 (runR emin prec choice IeeeModel.axpy_entry_step_2_1_prog [a; x0; x1; y0; y1]) 0,
   nth 32 (runR emin prec choice IeeeModel.axpy_entry_step_2_1_prog [a; x0; x1; y0; y1]) 0).
Proof.
intros. cbv [axpy_entry_step_2_1 mul_2_1 two_prod add_2_2 two_sum fast_two_sum runR run stepR
             nth app IeeeModel.axpy_entry_step_2_1_prog].
reflexivity.
Qed.

Section IeeeMapSteps.
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

(** * Two facts about any program *)

(* A program covered by the cone of position z: a finite value at z means that every
   value is finite and that of the real model. *)
Lemma bridge_cone :
  forall p (e : list float) z,
  finite_all e -> wf p (length e) = true -> covers p (length e) z = true ->
  fin (nth z (runB p e) d0) ->
  finite_all (runB p e) /\ b2r (nth z (runB p e) d0) = nth z (runR p (map b2r e)) 0.
Proof.
intros p e z Fe Hwf Hc Hz.
assert (F : finite_all (runB p e)).
{ exact (covers_sound prec emax nan_plus nan_minus nan_opp nan_fma p e z Fe Hwf Hc Hz). }
split. exact F.
apply sim_nth. exact (proj2 (run_sim prec emax nan_plus nan_minus nan_opp nan_fma p e Fe) F).
Qed.

(* An input in the cone of a finite value is finite, whatever the other inputs are. *)
Lemma lead_cone :
  forall p (e : list float) z k,
  wf p (length e) = true -> mem k (cone p (length e) [z]) = true -> (k < length e)%nat ->
  fin (nth z (runB p e) d0) -> fin (nth k e d0).
Proof.
intros p e z k Hwf Hk Hl Hz.
assert (E : nth k (runB p e) d0 = nth k e d0) by (apply run_nth_old; exact Hl).
rewrite <- E.
apply (cone_sound prec emax nan_plus nan_minus nan_opp nan_fma p e [z] Hwf).
- intros j [<-|[]]. exact Hz.
- apply mem_In. exact Hk.
Qed.

(** * The programs are the kernels of the IEEE model *)

Lemma add_1_1_runB :
  forall a b : float,
  IeeeModel.add_1_1 prec emax nan_plus a b = nth 2 (runB IeeeModel.add_1_1_prog [a; b]) d0.
Proof. intros. cbv [IeeeModel.add_1_1 run stepB nth app IeeeModel.add_1_1_prog]. reflexivity. Qed.

Lemma sub_1_1_runB :
  forall a b : float,
  IeeeModel.sub_1_1 prec emax nan_minus a b = nth 2 (runB IeeeModel.sub_1_1_prog [a; b]) d0.
Proof. intros. cbv [IeeeModel.sub_1_1 run stepB nth app IeeeModel.sub_1_1_prog]. reflexivity. Qed.

Lemma add_entry_step_1_runB :
  forall x y : float,
  IeeeModel.add_entry_step_1 prec emax nan_plus x y =
  nth 4 (runB IeeeModel.add_entry_step_1_prog [x; y]) d0.
Proof.
intros. cbv [IeeeModel.add_entry_step_1 IeeeModel.add_1_1 run stepB nth app
             IeeeModel.add_entry_step_1_prog].
reflexivity.
Qed.

Lemma sub_entry_step_1_runB :
  forall x y : float,
  IeeeModel.sub_entry_step_1 prec emax nan_plus nan_minus x y =
  nth 4 (runB IeeeModel.sub_entry_step_1_prog [x; y]) d0.
Proof.
intros. cbv [IeeeModel.sub_entry_step_1 IeeeModel.sub_1_1 run stepB nth app
             IeeeModel.sub_entry_step_1_prog].
reflexivity.
Qed.

Lemma scale_step_1_runB :
  forall x a : float,
  IeeeModel.scale_step_1 prec emax nan_fma x a = nth 2 (runB IeeeModel.scale_step_1_prog [x; a]) d0.
Proof.
intros. cbv [IeeeModel.scale_step_1 IeeeModel.mul_1_1 run stepB nth app
             IeeeModel.scale_step_1_prog].
reflexivity.
Qed.

Lemma mul_pow2_step_1_runB :
  forall x c : float,
  IeeeModel.mul_pow2_step_1 prec emax nan_fma x c =
  nth 2 (runB IeeeModel.mul_pow2_step_1_prog [x; c]) d0.
Proof.
intros. cbv [IeeeModel.mul_pow2_step_1 run stepB nth app IeeeModel.mul_pow2_step_1_prog].
reflexivity.
Qed.

Lemma axpy_step_1_runB :
  forall a x y : float,
  IeeeModel.axpy_step_1 prec emax nan_plus nan_fma a x y =
  nth 4 (runB IeeeModel.axpy_step_1_prog [a; x; y]) d0.
Proof.
intros. cbv [IeeeModel.axpy_step_1 IeeeModel.mul_1_1 IeeeModel.add_1_1 run stepB nth app
             IeeeModel.axpy_step_1_prog].
reflexivity.
Qed.

Lemma axpy_entry_step_1_runB :
  forall a x y : float,
  IeeeModel.axpy_entry_step_1 prec emax nan_plus nan_fma a x y =
  nth 5 (runB IeeeModel.axpy_entry_step_1_prog [a; x; y]) d0.
Proof.
intros. cbv [IeeeModel.axpy_entry_step_1 IeeeModel.mul_1_1 IeeeModel.add_1_1 run stepB nth app
             IeeeModel.axpy_entry_step_1_prog].
reflexivity.
Qed.

Lemma add_entry_step_2_runB :
  forall x0 x1 y0 y1 : float,
  IeeeModel.add_entry_step_2 prec emax nan_plus nan_minus x0 x1 y0 y1 =
  (nth 25 (runB IeeeModel.add_entry_step_2_prog [x0; x1; y0; y1]) d0,
   nth 27 (runB IeeeModel.add_entry_step_2_prog [x0; x1; y0; y1]) d0).
Proof.
intros. cbv [IeeeModel.add_entry_step_2 IeeeModel.add_2_2 IeeeModel.two_sum
             IeeeModel.fast_two_sum run stepB nth app IeeeModel.add_entry_step_2_prog].
reflexivity.
Qed.

Lemma sub_entry_step_2_runB :
  forall x0 x1 y0 y1 : float,
  IeeeModel.sub_entry_step_2 prec emax nan_plus nan_minus nan_opp x0 x1 y0 y1 =
  (nth 27 (runB IeeeModel.sub_entry_step_2_prog [x0; x1; y0; y1]) d0,
   nth 29 (runB IeeeModel.sub_entry_step_2_prog [x0; x1; y0; y1]) d0).
Proof.
intros. cbv [IeeeModel.sub_entry_step_2 IeeeModel.sub_2_2 IeeeModel.add_2_2 IeeeModel.two_sum
             IeeeModel.fast_two_sum run stepB nth app IeeeModel.sub_entry_step_2_prog].
reflexivity.
Qed.

Lemma scale_step_2_runB :
  forall x0 x1 a : float,
  IeeeModel.scale_step_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 a =
  (nth 6 (runB IeeeModel.scale_step_2_prog [x0; x1; a]) d0,
   nth 8 (runB IeeeModel.scale_step_2_prog [x0; x1; a]) d0).
Proof.
intros. cbv [IeeeModel.scale_step_2 IeeeModel.mul_2_1 IeeeModel.two_prod IeeeModel.fast_two_sum
             run stepB nth app IeeeModel.scale_step_2_prog].
reflexivity.
Qed.

Lemma mul_pow2_step_2_runB :
  forall x0 x1 c : float,
  IeeeModel.mul_pow2_step_2 prec emax nan_plus nan_minus nan_fma x0 x1 c =
  (nth 5 (runB IeeeModel.mul_pow2_step_2_prog [x0; x1; c]) d0,
   nth 7 (runB IeeeModel.mul_pow2_step_2_prog [x0; x1; c]) d0).
Proof.
intros. cbv [IeeeModel.mul_pow2_step_2 IeeeModel.mul_pow2_2 IeeeModel.fast_two_sum
             run stepB nth app IeeeModel.mul_pow2_step_2_prog].
reflexivity.
Qed.

Lemma axpy_step_2_runB :
  forall a0 a1 x0 x1 y0 y1 : float,
  IeeeModel.axpy_step_2 prec emax nan_plus nan_minus nan_opp nan_fma a0 a1 x0 x1 y0 y1 =
  (nth 32 (runB IeeeModel.axpy_step_2_prog [a0; a1; x0; x1; y0; y1]) d0,
   nth 34 (runB IeeeModel.axpy_step_2_prog [a0; a1; x0; x1; y0; y1]) d0).
Proof.
intros. cbv [IeeeModel.axpy_step_2 IeeeModel.mul_2_2 IeeeModel.two_prod IeeeModel.add_2_2
             IeeeModel.two_sum IeeeModel.fast_two_sum run stepB nth app
             IeeeModel.axpy_step_2_prog].
reflexivity.
Qed.

Lemma axpy_entry_step_2_runB :
  forall a0 a1 x0 x1 y0 y1 : float,
  IeeeModel.axpy_entry_step_2 prec emax nan_plus nan_minus nan_opp nan_fma a0 a1 x0 x1 y0 y1 =
  (nth 34 (runB IeeeModel.axpy_entry_step_2_prog [a0; a1; x0; x1; y0; y1]) d0,
   nth 36 (runB IeeeModel.axpy_entry_step_2_prog [a0; a1; x0; x1; y0; y1]) d0).
Proof.
intros. cbv [IeeeModel.axpy_entry_step_2 IeeeModel.mul_2_2 IeeeModel.two_prod IeeeModel.add_2_2
             IeeeModel.two_sum IeeeModel.fast_two_sum run stepB nth app
             IeeeModel.axpy_entry_step_2_prog].
reflexivity.
Qed.

Lemma axpy_step_2_1_runB :
  forall a x0 x1 y0 y1 : float,
  IeeeModel.axpy_step_2_1 prec emax nan_plus nan_minus nan_opp nan_fma a x0 x1 y0 y1 =
  (nth 28 (runB IeeeModel.axpy_step_2_1_prog [a; x0; x1; y0; y1]) d0,
   nth 30 (runB IeeeModel.axpy_step_2_1_prog [a; x0; x1; y0; y1]) d0).
Proof.
intros. cbv [IeeeModel.axpy_step_2_1 IeeeModel.mul_2_1 IeeeModel.two_prod IeeeModel.add_2_2
             IeeeModel.two_sum IeeeModel.fast_two_sum run stepB nth app
             IeeeModel.axpy_step_2_1_prog].
reflexivity.
Qed.

Lemma axpy_entry_step_2_1_runB :
  forall a x0 x1 y0 y1 : float,
  IeeeModel.axpy_entry_step_2_1 prec emax nan_plus nan_minus nan_opp nan_fma a x0 x1 y0 y1 =
  (nth 30 (runB IeeeModel.axpy_entry_step_2_1_prog [a; x0; x1; y0; y1]) d0,
   nth 32 (runB IeeeModel.axpy_entry_step_2_1_prog [a; x0; x1; y0; y1]) d0).
Proof.
intros. cbv [IeeeModel.axpy_entry_step_2_1 IeeeModel.mul_2_1 IeeeModel.two_prod
             IeeeModel.add_2_2 IeeeModel.two_sum IeeeModel.fast_two_sum run stepB nth app
             IeeeModel.axpy_entry_step_2_1_prog].
reflexivity.
Qed.

(** * add_entry_step_2 *)

Theorem add_entry_step_2_bridge :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  fin (nth 25 (runB IeeeModel.add_entry_step_2_prog [x0; x1; y0; y1]) d0) ->
  finite_all (runB IeeeModel.add_entry_step_2_prog [x0; x1; y0; y1]) /\
  map b2r (runB IeeeModel.add_entry_step_2_prog [x0; x1; y0; y1]) = runR
    IeeeModel.add_entry_step_2_prog [b2r x0; b2r x1; b2r y0; b2r y1].
Proof.
intros Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.add_entry_step_2_prog (firstn 21 IeeeModel.add_entry_step_2_prog) 21%nat 24%nat
         [x0; x1; y0; y1] 25%nat); trivial.
- repeat constructor; assumption.
- generalize (add_entry_step_2_correct emin prec Hp (b2r x0) (b2r x1) (b2r y0) (b2r y1) Nx Ny).
  rewrite add_entry_step_2_runR. intros [N _]. exact N.
Qed.

Theorem add_entry_step_2_values :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.add_entry_step_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  fin z0 ->
  fin z1 /\ (b2r z0, b2r z1) = add_entry_step_2 emin prec tie_even (b2r x0) (b2r x1) (b2r y0)
    (b2r y1).
Proof.
intros Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny. rewrite add_entry_step_2_runB. intros Hz.
destruct (add_entry_step_2_bridge Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hz) as [F M]. split.
- now apply nth_fin.
- rewrite add_entry_step_2_runR. f_equal; now apply sim_nth.
Qed.

Theorem add_entry_step_2_values_correct :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.add_entry_step_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  fin z0 ->
  fin z1 /\ normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs ((b2r z0 + b2r z1) - ((b2r x0 + b2r x1) + (b2r y0 + b2r y1)))
  <= (3 / (1 - (4 * u prec))) * u prec ^ 2 * Rabs ((b2r x0 + b2r x1) + (b2r y0 + b2r y1)).
Proof.
intros Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
generalize (add_entry_step_2_values Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny)
           (add_entry_step_2_correct emin prec Hp (b2r x0) (b2r x1) (b2r y0) (b2r y1) Nx Ny).
destruct (IeeeModel.add_entry_step_2 prec emax nan_plus nan_minus x0 x1 y0 y1) as [z0 z1].
intros B C Fz. destruct (B Fz) as [Fz1 E]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

(** * sub_entry_step_2 *)

Theorem sub_entry_step_2_bridge :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  fin (nth 27 (runB IeeeModel.sub_entry_step_2_prog [x0; x1; y0; y1]) d0) ->
  finite_all (runB IeeeModel.sub_entry_step_2_prog [x0; x1; y0; y1]) /\
  map b2r (runB IeeeModel.sub_entry_step_2_prog [x0; x1; y0; y1]) = runR
    IeeeModel.sub_entry_step_2_prog [b2r x0; b2r x1; b2r y0; b2r y1].
Proof.
intros Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.sub_entry_step_2_prog (firstn 23 IeeeModel.sub_entry_step_2_prog) 23%nat 26%nat
         [x0; x1; y0; y1] 27%nat); trivial.
- repeat constructor; assumption.
- generalize (sub_entry_step_2_correct emin prec Hp (b2r x0) (b2r x1) (b2r y0) (b2r y1) Nx Ny).
  rewrite sub_entry_step_2_runR. intros [N _]. exact N.
Qed.

Theorem sub_entry_step_2_values :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.sub_entry_step_2 prec emax nan_plus nan_minus nan_opp x0 x1 y0 y1 in
  fin z0 ->
  fin z1 /\ (b2r z0, b2r z1) = sub_entry_step_2 emin prec tie_even (b2r x0) (b2r x1) (b2r y0)
    (b2r y1).
Proof.
intros Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny. rewrite sub_entry_step_2_runB. intros Hz.
destruct (sub_entry_step_2_bridge Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hz) as [F M]. split.
- now apply nth_fin.
- rewrite sub_entry_step_2_runR. f_equal; now apply sim_nth.
Qed.

Theorem sub_entry_step_2_values_correct :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.sub_entry_step_2 prec emax nan_plus nan_minus nan_opp x0 x1 y0 y1 in
  fin z0 ->
  fin z1 /\ normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs ((b2r z0 + b2r z1) - ((b2r x0 + b2r x1) - (b2r y0 + b2r y1)))
  <= (3 / (1 - (4 * u prec))) * u prec ^ 2 * Rabs ((b2r x0 + b2r x1) - (b2r y0 + b2r y1)).
Proof.
intros Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
generalize (sub_entry_step_2_values Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny)
           (sub_entry_step_2_correct emin prec Hp (b2r x0) (b2r x1) (b2r y0) (b2r y1) Nx Ny).
destruct (IeeeModel.sub_entry_step_2 prec emax nan_plus nan_minus nan_opp x0 x1 y0 y1) as [z0 z1].
intros B C Fz. destruct (B Fz) as [Fz1 E]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

(** * scale_step_2 *)

Theorem scale_step_2_bridge :
  (2 <= prec)%Z ->
  forall x0 x1 a : float, fin x0 -> fin x1 -> fin a ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  fin (nth 6 (runB IeeeModel.scale_step_2_prog [x0; x1; a]) d0) ->
  finite_all (runB IeeeModel.scale_step_2_prog [x0; x1; a]) /\
  map b2r (runB IeeeModel.scale_step_2_prog [x0; x1; a]) = runR IeeeModel.scale_step_2_prog
    [b2r x0; b2r x1; b2r a].
Proof.
intros Hp x0 x1 a F0 F1 Fa Nx Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.scale_step_2_prog (firstn 3 IeeeModel.scale_step_2_prog) 3%nat 5%nat
         [x0; x1; a] 6%nat); trivial.
- repeat constructor; assumption.
- generalize
    (scale_step_2_correct emin prec Hp (b2r x0) (b2r x1) (b2r a) Nx (b2r_format prec emax a)).
  rewrite scale_step_2_runR. intros [N _]. exact N.
Qed.

Theorem scale_step_2_values :
  (2 <= prec)%Z ->
  forall x0 x1 a : float, fin x0 -> fin x1 -> fin a ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  let '(z0, z1) := IeeeModel.scale_step_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 a in
  fin z0 ->
  fin z1 /\ (b2r z0, b2r z1) = scale_step_2 emin prec tie_even (b2r x0) (b2r x1) (b2r a).
Proof.
intros Hp x0 x1 a F0 F1 Fa Nx. rewrite scale_step_2_runB. intros Hz.
destruct (scale_step_2_bridge Hp x0 x1 a F0 F1 Fa Nx Hz) as [F M]. split.
- now apply nth_fin.
- rewrite scale_step_2_runR. f_equal; now apply sim_nth.
Qed.

Theorem scale_step_2_values_correct :
  (2 <= prec)%Z ->
  forall x0 x1 a : float, fin x0 -> fin x1 -> fin a ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  let '(z0, z1) := IeeeModel.scale_step_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 a in
  fin z0 ->
  fin z1 /\ normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs ((b2r z0 + b2r z1) - ((b2r x0 + b2r x1) * b2r a))
  <= 2 * u prec ^ 2 * Rabs ((b2r x0 + b2r x1) * b2r a) + 1 * eta emin.
Proof.
intros Hp x0 x1 a F0 F1 Fa Nx.
generalize (scale_step_2_values Hp x0 x1 a F0 F1 Fa Nx)
           (scale_step_2_correct emin prec Hp (b2r x0) (b2r x1) (b2r a) Nx
             (b2r_format prec emax a)).
destruct (IeeeModel.scale_step_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 a) as [z0 z1].
intros B C Fz. destruct (B Fz) as [Fz1 E]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

(** * mul_pow2_step_2 *)

Theorem mul_pow2_step_2_bridge :
  (2 <= prec)%Z ->
  forall x0 x1 c : float, fin x0 -> fin x1 -> fin c ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  (exists n : Z, b2r c = bpow radix2 n) ->
  fin (nth 5 (runB IeeeModel.mul_pow2_step_2_prog [x0; x1; c]) d0) ->
  finite_all (runB IeeeModel.mul_pow2_step_2_prog [x0; x1; c]) /\
  map b2r (runB IeeeModel.mul_pow2_step_2_prog [x0; x1; c]) = runR IeeeModel.mul_pow2_step_2_prog
    [b2r x0; b2r x1; b2r c].
Proof.
intros Hp x0 x1 c F0 F1 Fc Nx Pc Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.mul_pow2_step_2_prog (firstn 2 IeeeModel.mul_pow2_step_2_prog) 3%nat 4%nat
         [x0; x1; c] 5%nat); trivial.
- repeat constructor; assumption.
- generalize
    (mul_pow2_step_2_correct emin prec Hp (b2r x0) (b2r x1) (b2r c) Nx (b2r_format prec emax c) Pc).
  rewrite mul_pow2_step_2_runR. intros [N _]. exact N.
Qed.

Theorem mul_pow2_step_2_values :
  (2 <= prec)%Z ->
  forall x0 x1 c : float, fin x0 -> fin x1 -> fin c ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  (exists n : Z, b2r c = bpow radix2 n) ->
  let '(z0, z1) := IeeeModel.mul_pow2_step_2 prec emax nan_plus nan_minus nan_fma x0 x1 c in
  fin z0 ->
  fin z1 /\ (b2r z0, b2r z1) = mul_pow2_step_2 emin prec tie_even (b2r x0) (b2r x1) (b2r c).
Proof.
intros Hp x0 x1 c F0 F1 Fc Nx Pc. rewrite mul_pow2_step_2_runB. intros Hz.
destruct (mul_pow2_step_2_bridge Hp x0 x1 c F0 F1 Fc Nx Pc Hz) as [F M]. split.
- now apply nth_fin.
- rewrite mul_pow2_step_2_runR. f_equal; now apply sim_nth.
Qed.

Theorem mul_pow2_step_2_values_correct :
  (2 <= prec)%Z ->
  forall x0 x1 c : float, fin x0 -> fin x1 -> fin c ->
  normalized_2 emin prec (b2r x0) (b2r x1) ->
  (exists n : Z, b2r c = bpow radix2 n) ->
  let '(z0, z1) := IeeeModel.mul_pow2_step_2 prec emax nan_plus nan_minus nan_fma x0 x1 c in
  fin z0 ->
  fin z1 /\ normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs ((b2r z0 + b2r z1) - ((b2r x0 + b2r x1) * b2r c)) <= 1 * eta emin.
Proof.
intros Hp x0 x1 c F0 F1 Fc Nx Pc.
generalize (mul_pow2_step_2_values Hp x0 x1 c F0 F1 Fc Nx Pc)
           (mul_pow2_step_2_correct emin prec Hp (b2r x0) (b2r x1) (b2r c) Nx
             (b2r_format prec emax c) Pc).
destruct (IeeeModel.mul_pow2_step_2 prec emax nan_plus nan_minus nan_fma x0 x1 c) as [z0 z1].
intros B C Fz. destruct (B Fz) as [Fz1 E]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

(** * axpy_step_2 *)

Theorem axpy_step_2_bridge :
  (4 <= prec)%Z ->
  forall a0 a1 x0 x1 y0 y1 : float, fin a0 -> fin a1 -> fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r a0) (b2r a1) ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  fin (nth 32 (runB IeeeModel.axpy_step_2_prog [a0; a1; x0; x1; y0; y1]) d0) ->
  finite_all (runB IeeeModel.axpy_step_2_prog [a0; a1; x0; x1; y0; y1]) /\
  map b2r (runB IeeeModel.axpy_step_2_prog [a0; a1; x0; x1; y0; y1]) = runR
    IeeeModel.axpy_step_2_prog [b2r a0; b2r a1; b2r x0; b2r x1; b2r y0; b2r y1].
Proof.
intros Hp a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na Nx Ny Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.axpy_step_2_prog (firstn 26 IeeeModel.axpy_step_2_prog) 28%nat 31%nat
         [a0; a1; x0; x1; y0; y1] 32%nat); trivial.
- repeat constructor; assumption.
- generalize
    (axpy_step_2_correct emin prec Hp (b2r a0) (b2r a1) (b2r x0) (b2r x1) (b2r y0) (b2r y1) Na Nx
    Ny).
  rewrite axpy_step_2_runR. intros [N _]. exact N.
Qed.

Theorem axpy_step_2_values :
  (4 <= prec)%Z ->
  forall a0 a1 x0 x1 y0 y1 : float, fin a0 -> fin a1 -> fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r a0) (b2r a1) ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.axpy_step_2 prec emax nan_plus nan_minus nan_opp nan_fma a0 a1 x0 x1 y0
    y1 in
  fin z0 ->
  fin z1 /\ (b2r z0, b2r z1) = axpy_step_2 emin prec tie_even (b2r a0) (b2r a1) (b2r x0) (b2r x1)
    (b2r y0) (b2r y1).
Proof.
intros Hp a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na Nx Ny. rewrite axpy_step_2_runB. intros Hz.
destruct (axpy_step_2_bridge Hp a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na Nx Ny Hz) as [F M]. split.
- now apply nth_fin.
- rewrite axpy_step_2_runR. f_equal; now apply sim_nth.
Qed.

Theorem axpy_step_2_values_correct :
  (4 <= prec)%Z ->
  forall a0 a1 x0 x1 y0 y1 : float, fin a0 -> fin a1 -> fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r a0) (b2r a1) ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.axpy_step_2 prec emax nan_plus nan_minus nan_opp nan_fma a0 a1 x0 x1 y0
    y1 in
  fin z0 ->
  fin z1 /\ normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs ((b2r z0 + b2r z1) - (((b2r a0 + b2r a1) * (b2r x0 + b2r x1)) + (b2r y0 + b2r y1)))
  <= (((3 * (1 + ((4 * u prec) * u prec))) / (1 - (4 * u prec))) + 4) * u prec ^ 2 *
     (Rabs ((b2r a0 + b2r a1) * (b2r x0 + b2r x1)) + Rabs (b2r y0 + b2r y1)) + 2 * eta emin.
Proof.
intros Hp a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na Nx Ny.
generalize (axpy_step_2_values Hp a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na Nx Ny)
           (axpy_step_2_correct emin prec Hp (b2r a0) (b2r a1) (b2r x0) (b2r x1) (b2r y0) (b2r y1)
             Na Nx Ny).
destruct (IeeeModel.axpy_step_2 prec emax nan_plus nan_minus nan_opp nan_fma a0 a1 x0 x1 y0 y1) as
    [z0 z1].
intros B C Fz. destruct (B Fz) as [Fz1 E]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

(** * axpy_entry_step_2 *)

Theorem axpy_entry_step_2_bridge :
  (4 <= prec)%Z ->
  forall a0 a1 x0 x1 y0 y1 : float, fin a0 -> fin a1 -> fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r a0) (b2r a1) ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  fin (nth 34 (runB IeeeModel.axpy_entry_step_2_prog [a0; a1; x0; x1; y0; y1]) d0) ->
  finite_all (runB IeeeModel.axpy_entry_step_2_prog [a0; a1; x0; x1; y0; y1]) /\
  map b2r (runB IeeeModel.axpy_entry_step_2_prog [a0; a1; x0; x1; y0; y1]) = runR
    IeeeModel.axpy_entry_step_2_prog [b2r a0; b2r a1; b2r x0; b2r x1; b2r y0; b2r y1].
Proof.
intros Hp a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na Nx Ny Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.axpy_entry_step_2_prog (firstn 28 IeeeModel.axpy_entry_step_2_prog) 30%nat 33%nat
         [a0; a1; x0; x1; y0; y1] 34%nat); trivial.
- repeat constructor; assumption.
- generalize
    (axpy_entry_step_2_correct emin prec Hp (b2r a0) (b2r a1) (b2r x0) (b2r x1) (b2r y0) (b2r y1) Na
    Nx Ny).
  rewrite axpy_entry_step_2_runR. intros [N _]. exact N.
Qed.

Theorem axpy_entry_step_2_values :
  (4 <= prec)%Z ->
  forall a0 a1 x0 x1 y0 y1 : float, fin a0 -> fin a1 -> fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r a0) (b2r a1) ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.axpy_entry_step_2 prec emax nan_plus nan_minus nan_opp nan_fma a0 a1 x0
    x1 y0 y1 in
  fin z0 ->
  fin z1 /\ (b2r z0, b2r z1) = axpy_entry_step_2 emin prec tie_even (b2r a0) (b2r a1) (b2r x0)
    (b2r x1) (b2r y0) (b2r y1).
Proof.
intros Hp a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na Nx Ny. rewrite axpy_entry_step_2_runB. intros Hz.
destruct (axpy_entry_step_2_bridge Hp a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na Nx Ny Hz) as [F M].
    split.
- now apply nth_fin.
- rewrite axpy_entry_step_2_runR. f_equal; now apply sim_nth.
Qed.

Theorem axpy_entry_step_2_values_correct :
  (4 <= prec)%Z ->
  forall a0 a1 x0 x1 y0 y1 : float, fin a0 -> fin a1 -> fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r a0) (b2r a1) ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.axpy_entry_step_2 prec emax nan_plus nan_minus nan_opp nan_fma a0 a1 x0
    x1 y0 y1 in
  fin z0 ->
  fin z1 /\ normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs ((b2r z0 + b2r z1) - (((b2r a0 + b2r a1) * (b2r x0 + b2r x1)) + (b2r y0 + b2r y1)))
  <= (((3 * (1 + ((4 * u prec) * u prec))) / (1 - (4 * u prec))) + 4) * u prec ^ 2 *
     (Rabs ((b2r a0 + b2r a1) * (b2r x0 + b2r x1)) + Rabs (b2r y0 + b2r y1)) + 2 * eta emin.
Proof.
intros Hp a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na Nx Ny.
generalize (axpy_entry_step_2_values Hp a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na Nx Ny)
           (axpy_entry_step_2_correct emin prec Hp (b2r a0) (b2r a1) (b2r x0) (b2r x1) (b2r y0)
             (b2r y1) Na Nx Ny).
destruct (IeeeModel.axpy_entry_step_2 prec emax nan_plus nan_minus nan_opp nan_fma a0 a1 x0 x1 y0
    y1) as [z0 z1].
intros B C Fz. destruct (B Fz) as [Fz1 E]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

(** * axpy_step_2_1 *)

Theorem axpy_step_2_1_bridge :
  (3 <= prec)%Z ->
  forall a x0 x1 y0 y1 : float, fin a -> fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  fin (nth 28 (runB IeeeModel.axpy_step_2_1_prog [a; x0; x1; y0; y1]) d0) ->
  finite_all (runB IeeeModel.axpy_step_2_1_prog [a; x0; x1; y0; y1]) /\
  map b2r (runB IeeeModel.axpy_step_2_1_prog [a; x0; x1; y0; y1]) = runR
    IeeeModel.axpy_step_2_1_prog [b2r a; b2r x0; b2r x1; b2r y0; b2r y1].
Proof.
intros Hp a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.axpy_step_2_1_prog (firstn 23 IeeeModel.axpy_step_2_1_prog) 24%nat 27%nat
         [a; x0; x1; y0; y1] 28%nat); trivial.
- repeat constructor; assumption.
- generalize
    (axpy_step_2_1_correct emin prec Hp (b2r a) (b2r x0) (b2r x1) (b2r y0) (b2r y1)
    (b2r_format prec emax a) Nx Ny).
  rewrite axpy_step_2_1_runR. intros [N _]. exact N.
Qed.

Theorem axpy_step_2_1_values :
  (3 <= prec)%Z ->
  forall a x0 x1 y0 y1 : float, fin a -> fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.axpy_step_2_1 prec emax nan_plus nan_minus nan_opp nan_fma a x0 x1 y0
    y1 in
  fin z0 ->
  fin z1 /\ (b2r z0, b2r z1) = axpy_step_2_1 emin prec tie_even (b2r a) (b2r x0) (b2r x1) (b2r y0)
    (b2r y1).
Proof.
intros Hp a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny. rewrite axpy_step_2_1_runB. intros Hz.
destruct (axpy_step_2_1_bridge Hp a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny Hz) as [F M]. split.
- now apply nth_fin.
- rewrite axpy_step_2_1_runR. f_equal; now apply sim_nth.
Qed.

Theorem axpy_step_2_1_values_correct :
  (3 <= prec)%Z ->
  forall a x0 x1 y0 y1 : float, fin a -> fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.axpy_step_2_1 prec emax nan_plus nan_minus nan_opp nan_fma a x0 x1 y0
    y1 in
  fin z0 ->
  fin z1 /\ normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs ((b2r z0 + b2r z1) - ((b2r a * (b2r x0 + b2r x1)) + (b2r y0 + b2r y1)))
  <= (((3 * (1 + ((2 * u prec) * u prec))) / (1 - (4 * u prec))) + 2) * u prec ^ 2 *
     (Rabs (b2r a * (b2r x0 + b2r x1)) + Rabs (b2r y0 + b2r y1)) + (5 / 4) * eta emin.
Proof.
intros Hp a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny.
generalize (axpy_step_2_1_values Hp a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny)
           (axpy_step_2_1_correct emin prec Hp (b2r a) (b2r x0) (b2r x1) (b2r y0) (b2r y1)
             (b2r_format prec emax a) Nx Ny).
destruct (IeeeModel.axpy_step_2_1 prec emax nan_plus nan_minus nan_opp nan_fma a x0 x1 y0 y1) as
    [z0 z1].
intros B C Fz. destruct (B Fz) as [Fz1 E]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

(** * axpy_entry_step_2_1 *)

Theorem axpy_entry_step_2_1_bridge :
  (3 <= prec)%Z ->
  forall a x0 x1 y0 y1 : float, fin a -> fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  fin (nth 30 (runB IeeeModel.axpy_entry_step_2_1_prog [a; x0; x1; y0; y1]) d0) ->
  finite_all (runB IeeeModel.axpy_entry_step_2_1_prog [a; x0; x1; y0; y1]) /\
  map b2r (runB IeeeModel.axpy_entry_step_2_1_prog [a; x0; x1; y0; y1]) = runR
    IeeeModel.axpy_entry_step_2_1_prog [b2r a; b2r x0; b2r x1; b2r y0; b2r y1].
Proof.
intros Hp a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny Hz.
apply (bridge_f2s_prog prec emax nan_plus nan_minus nan_opp nan_fma
         IeeeModel.axpy_entry_step_2_1_prog (firstn 25 IeeeModel.axpy_entry_step_2_1_prog) 26%nat
           29%nat
         [a; x0; x1; y0; y1] 30%nat); trivial.
- repeat constructor; assumption.
- generalize
    (axpy_entry_step_2_1_correct emin prec Hp (b2r a) (b2r x0) (b2r x1) (b2r y0) (b2r y1)
    (b2r_format prec emax a) Nx Ny).
  rewrite axpy_entry_step_2_1_runR. intros [N _]. exact N.
Qed.

Theorem axpy_entry_step_2_1_values :
  (3 <= prec)%Z ->
  forall a x0 x1 y0 y1 : float, fin a -> fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.axpy_entry_step_2_1 prec emax nan_plus nan_minus nan_opp nan_fma a x0
    x1 y0 y1 in
  fin z0 ->
  fin z1 /\ (b2r z0, b2r z1) = axpy_entry_step_2_1 emin prec tie_even (b2r a) (b2r x0) (b2r x1)
    (b2r y0) (b2r y1).
Proof.
intros Hp a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny. rewrite axpy_entry_step_2_1_runB. intros Hz.
destruct (axpy_entry_step_2_1_bridge Hp a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny Hz) as [F M]. split.
- now apply nth_fin.
- rewrite axpy_entry_step_2_1_runR. f_equal; now apply sim_nth.
Qed.

Theorem axpy_entry_step_2_1_values_correct :
  (3 <= prec)%Z ->
  forall a x0 x1 y0 y1 : float, fin a -> fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1) := IeeeModel.axpy_entry_step_2_1 prec emax nan_plus nan_minus nan_opp nan_fma a x0
    x1 y0 y1 in
  fin z0 ->
  fin z1 /\ normalized_2 emin prec (b2r z0) (b2r z1) /\
  Rabs ((b2r z0 + b2r z1) - ((b2r a * (b2r x0 + b2r x1)) + (b2r y0 + b2r y1)))
  <= (((3 * (1 + ((2 * u prec) * u prec))) / (1 - (4 * u prec))) + 2) * u prec ^ 2 *
     (Rabs (b2r a * (b2r x0 + b2r x1)) + Rabs (b2r y0 + b2r y1)) + (5 / 4) * eta emin.
Proof.
intros Hp a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny.
generalize (axpy_entry_step_2_1_values Hp a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny)
           (axpy_entry_step_2_1_correct emin prec Hp (b2r a) (b2r x0) (b2r x1) (b2r y0) (b2r y1)
             (b2r_format prec emax a) Nx Ny).
destruct (IeeeModel.axpy_entry_step_2_1 prec emax nan_plus nan_minus nan_opp nan_fma a x0 x1 y0 y1)
    as [z0 z1].
intros B C Fz. destruct (B Fz) as [Fz1 E]. rewrite <- E in C. split. exact Fz1. exact C.
Qed.

End IeeeMapSteps.

(** * The generated statements: the bridges and the claims of the steps of two limbs *)

Theorem add_entry_step_2_ieee_bridge : add_entry_step_2_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp' x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
generalize
    (add_entry_step_2_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp' x0 x1 y0 y1 F0 F1 G0
    G1 Nx Ny)
           (add_entry_step_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp' x0 x1 y0 y1 F0
             F1 G0 G1 Nx Ny).
rewrite (add_entry_step_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem add_entry_step_2_ieee_correct : add_entry_step_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus Hp' x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
exact (add_entry_step_2_values_correct prec emax nan_plus nan_minus (fun x => nan_plus x x)
    (fun x y _ => nan_plus x y) Hp' x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
Qed.

Theorem sub_entry_step_2_ieee_bridge : sub_entry_step_2_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp' x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
generalize
    (sub_entry_step_2_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp' x0 x1 y0 y1 F0 F1 G0
    G1 Nx Ny)
           (sub_entry_step_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp' x0 x1 y0 y1 F0
             F1 G0 G1 Nx Ny).
rewrite (sub_entry_step_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem sub_entry_step_2_ieee_correct : sub_entry_step_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp Hp' x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
exact (sub_entry_step_2_values_correct prec emax nan_plus nan_minus nan_opp
    (fun x y _ => nan_plus x y) Hp' x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
Qed.

Theorem scale_step_2_ieee_bridge : scale_step_2_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp' x0 x1 a F0 F1 Fa Nx.
generalize
    (scale_step_2_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp' x0 x1 a F0 F1 Fa Nx)
           (scale_step_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp' x0 x1 a F0 F1 Fa
             Nx).
rewrite (scale_step_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem scale_step_2_ieee_correct : scale_step_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp' x0 x1 a F0 F1 Fa Nx.
exact (scale_step_2_values_correct prec emax nan_plus nan_minus nan_opp nan_fma Hp' x0 x1 a F0 F1 Fa
    Nx).
Qed.

Theorem mul_pow2_step_2_ieee_bridge : mul_pow2_step_2_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp' x0 x1 c F0 F1 Fc Nx Pc.
generalize
    (mul_pow2_step_2_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp' x0 x1 c F0 F1 Fc Nx Pc)
           (mul_pow2_step_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp' x0 x1 c F0 F1 Fc
             Nx Pc).
rewrite (mul_pow2_step_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem mul_pow2_step_2_ieee_correct : mul_pow2_step_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_fma Hp' x0 x1 c F0 F1 Fc Nx Pc.
exact (mul_pow2_step_2_values_correct prec emax nan_plus nan_minus (fun x => nan_plus x x) nan_fma
    Hp' x0 x1 c F0 F1 Fc Nx Pc).
Qed.

Theorem axpy_step_2_ieee_bridge : axpy_step_2_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp' a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na
    Nx Ny.
generalize
    (axpy_step_2_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp' a0 a1 x0 x1 y0 y1 A0 A1 F0
    F1 G0 G1 Na Nx Ny)
           (axpy_step_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp' a0 a1 x0 x1 y0 y1 A0
             A1 F0 F1 G0 G1 Na Nx Ny).
rewrite (axpy_step_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem axpy_step_2_ieee_correct : axpy_step_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp' a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na
    Nx Ny.
exact (axpy_step_2_values_correct prec emax nan_plus nan_minus nan_opp nan_fma Hp' a0 a1 x0 x1 y0 y1
    A0 A1 F0 F1 G0 G1 Na Nx Ny).
Qed.

Theorem axpy_entry_step_2_ieee_bridge : axpy_entry_step_2_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp' a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na
    Nx Ny.
generalize
    (axpy_entry_step_2_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp' a0 a1 x0 x1 y0 y1 A0
    A1 F0 F1 G0 G1 Na Nx Ny)
           (axpy_entry_step_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp' a0 a1 x0 x1 y0
             y1 A0 A1 F0 F1 G0 G1 Na Nx Ny).
rewrite (axpy_entry_step_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem axpy_entry_step_2_ieee_correct : axpy_entry_step_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp' a0 a1 x0 x1 y0 y1 A0 A1 F0 F1 G0 G1 Na
    Nx Ny.
exact (axpy_entry_step_2_values_correct prec emax nan_plus nan_minus nan_opp nan_fma Hp' a0 a1 x0 x1
    y0 y1 A0 A1 F0 F1 G0 G1 Na Nx Ny).
Qed.

Theorem axpy_step_2_1_ieee_bridge : axpy_step_2_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp' a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny.
generalize
    (axpy_step_2_1_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp' a x0 x1 y0 y1 Fa F0 F1 G0
    G1 Nx Ny)
           (axpy_step_2_1_values prec emax nan_plus nan_minus nan_opp nan_fma Hp' a x0 x1 y0 y1 Fa
             F0 F1 G0 G1 Nx Ny).
rewrite (axpy_step_2_1_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem axpy_step_2_1_ieee_correct : axpy_step_2_1_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp' a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny.
exact (axpy_step_2_1_values_correct prec emax nan_plus nan_minus nan_opp nan_fma Hp' a x0 x1 y0 y1
    Fa F0 F1 G0 G1 Nx Ny).
Qed.

Theorem axpy_entry_step_2_1_ieee_bridge : axpy_entry_step_2_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp' a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny.
generalize
    (axpy_entry_step_2_1_bridge prec emax nan_plus nan_minus nan_opp nan_fma Hp' a x0 x1 y0 y1 Fa F0
    F1 G0 G1 Nx Ny)
           (axpy_entry_step_2_1_values prec emax nan_plus nan_minus nan_opp nan_fma Hp' a x0 x1 y0
             y1 Fa F0 F1 G0 G1 Nx Ny).
rewrite (axpy_entry_step_2_1_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros B V Fz. destruct (B Fz) as [F _]. destruct (V Fz) as [Fz1 E].
split. exact F. split. exact Fz1. exact E.
Qed.

Theorem axpy_entry_step_2_1_ieee_correct : axpy_entry_step_2_1_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp' a x0 x1 y0 y1 Fa F0 F1 G0 G1 Nx Ny.
exact (axpy_entry_step_2_1_values_correct prec emax nan_plus nan_minus nan_opp nan_fma Hp' a x0 x1
    y0 y1 Fa F0 F1 G0 G1 Nx Ny).
Qed.

(** * The generated statements: the bridges of the steps of one limb *)

(* Every value of the program is in the cone of its result (bridge_cone). *)

Theorem add_1_1_ieee_bridge : add_1_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp1 a b Fa Fb. cbv zeta. intros Fz.
rewrite (add_1_1_runB prec emax nan_plus nan_minus nan_opp nan_fma) in Fz |- *.
rewrite add_1_1_runR.
apply (bridge_cone prec emax nan_plus nan_minus nan_opp nan_fma).
- repeat constructor; assumption.
- reflexivity.
- reflexivity.
- exact Fz.
Qed.

Theorem sub_1_1_ieee_bridge : sub_1_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp1 a b Fa Fb. cbv zeta. intros Fz.
rewrite (sub_1_1_runB prec emax nan_plus nan_minus nan_opp nan_fma) in Fz |- *.
rewrite sub_1_1_runR.
apply (bridge_cone prec emax nan_plus nan_minus nan_opp nan_fma).
- repeat constructor; assumption.
- reflexivity.
- reflexivity.
- exact Fz.
Qed.

Theorem add_entry_step_1_ieee_bridge : add_entry_step_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp1 x y Fx Fy. cbv zeta. intros Fz.
rewrite (add_entry_step_1_runB prec emax nan_plus nan_minus nan_opp nan_fma) in Fz |- *.
rewrite add_entry_step_1_runR.
apply (bridge_cone prec emax nan_plus nan_minus nan_opp nan_fma).
- repeat constructor; assumption.
- reflexivity.
- reflexivity.
- exact Fz.
Qed.

Theorem sub_entry_step_1_ieee_bridge : sub_entry_step_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp1 x y Fx Fy. cbv zeta. intros Fz.
rewrite (sub_entry_step_1_runB prec emax nan_plus nan_minus nan_opp nan_fma) in Fz |- *.
rewrite sub_entry_step_1_runR.
apply (bridge_cone prec emax nan_plus nan_minus nan_opp nan_fma).
- repeat constructor; assumption.
- reflexivity.
- reflexivity.
- exact Fz.
Qed.

Theorem scale_step_1_ieee_bridge : scale_step_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp1 x a Fx Fa. cbv zeta. intros Fz.
rewrite (scale_step_1_runB prec emax nan_plus nan_minus nan_opp nan_fma) in Fz |- *.
rewrite scale_step_1_runR.
apply (bridge_cone prec emax nan_plus nan_minus nan_opp nan_fma).
- repeat constructor; assumption.
- reflexivity.
- reflexivity.
- exact Fz.
Qed.

Theorem mul_pow2_step_1_ieee_bridge : mul_pow2_step_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp1 x c Fx Fc Pc. cbv zeta. intros Fz.
rewrite (mul_pow2_step_1_runB prec emax nan_plus nan_minus nan_opp nan_fma) in Fz |- *.
rewrite mul_pow2_step_1_runR.
apply (bridge_cone prec emax nan_plus nan_minus nan_opp nan_fma).
- repeat constructor; assumption.
- reflexivity.
- reflexivity.
- exact Fz.
Qed.

Theorem axpy_step_1_ieee_bridge : axpy_step_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp1 a x y Fa Fx Fy. cbv zeta. intros Fz.
rewrite (axpy_step_1_runB prec emax nan_plus nan_minus nan_opp nan_fma) in Fz |- *.
rewrite axpy_step_1_runR.
apply (bridge_cone prec emax nan_plus nan_minus nan_opp nan_fma).
- repeat constructor; assumption.
- reflexivity.
- reflexivity.
- exact Fz.
Qed.

Theorem axpy_entry_step_1_ieee_bridge : axpy_entry_step_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp1 a x y Fa Fx Fy. cbv zeta. intros Fz.
rewrite (axpy_entry_step_1_runB prec emax nan_plus nan_minus nan_opp nan_fma) in Fz |- *.
rewrite axpy_entry_step_1_runR.
apply (bridge_cone prec emax nan_plus nan_minus nan_opp nan_fma).
- repeat constructor; assumption.
- reflexivity.
- reflexivity.
- exact Fz.
Qed.


(** * The generated statements: the leading limb of each step *)

(* Each input named by the statement is in the cone of the leading limb of the result
   (lead_cone, for any operands). sub_2_2 is the step of sub_2; its program is that of
   IeeeSub.v. *)

Theorem add_entry_step_1_ieee_lead : add_entry_step_1_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_plus x y. cbv zeta. rewrite
    (add_entry_step_1_runB prec emax nan_plus nan_plus (fun x => nan_plus x x)
    (fun x y _ => nan_plus x y)).
intros Fz.
split.
- exact (lead_cone prec emax nan_plus nan_plus (fun x => nan_plus x x) (fun x y _ => nan_plus x y)
    IeeeModel.add_entry_step_1_prog [x; y] 4 0 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_plus (fun x => nan_plus x x) (fun x y _ => nan_plus x y)
    IeeeModel.add_entry_step_1_prog [x; y] 4 1 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
Qed.

Theorem axpy_entry_step_1_ieee_lead : axpy_entry_step_1_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_plus nan_fma a x y. cbv zeta. rewrite
    (axpy_entry_step_1_runB prec emax nan_plus nan_plus (fun x => nan_plus x x) nan_fma).
intros Fz.
split; [|split].
- exact (lead_cone prec emax nan_plus nan_plus (fun x => nan_plus x x) nan_fma
    IeeeModel.axpy_entry_step_1_prog [a; x; y] 5 0 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_plus (fun x => nan_plus x x) nan_fma
    IeeeModel.axpy_entry_step_1_prog [a; x; y] 5 1 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_plus (fun x => nan_plus x x) nan_fma
    IeeeModel.axpy_entry_step_1_prog [a; x; y] 5 2 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
Qed.

Theorem axpy_step_1_ieee_lead : axpy_step_1_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_plus nan_fma a x y. cbv zeta. rewrite
    (axpy_step_1_runB prec emax nan_plus nan_plus (fun x => nan_plus x x) nan_fma).
intros Fz.
split; [|split].
- exact (lead_cone prec emax nan_plus nan_plus (fun x => nan_plus x x) nan_fma
    IeeeModel.axpy_step_1_prog [a; x; y] 4 0 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_plus (fun x => nan_plus x x) nan_fma
    IeeeModel.axpy_step_1_prog [a; x; y] 4 1 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_plus (fun x => nan_plus x x) nan_fma
    IeeeModel.axpy_step_1_prog [a; x; y] 4 2 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
Qed.

Theorem mul_pow2_step_1_ieee_lead : mul_pow2_step_1_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_fma x c. cbv zeta. rewrite
    (mul_pow2_step_1_runB prec emax (fun x y => nan_fma x y x) (fun x y => nan_fma x y x)
    (fun x => nan_fma x x x) nan_fma).
intros Fz.
split.
- exact (lead_cone prec emax (fun x y => nan_fma x y x) (fun x y => nan_fma x y x)
    (fun x => nan_fma x x x) nan_fma IeeeModel.mul_pow2_step_1_prog [x; c] 2 0 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax (fun x y => nan_fma x y x) (fun x y => nan_fma x y x)
    (fun x => nan_fma x x x) nan_fma IeeeModel.mul_pow2_step_1_prog [x; c] 2 1 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
Qed.

Theorem scale_step_1_ieee_lead : scale_step_1_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_fma x a. cbv zeta. rewrite
    (scale_step_1_runB prec emax (fun x y => nan_fma x y x) (fun x y => nan_fma x y x)
    (fun x => nan_fma x x x) nan_fma).
intros Fz.
split.
- exact (lead_cone prec emax (fun x y => nan_fma x y x) (fun x y => nan_fma x y x)
    (fun x => nan_fma x x x) nan_fma IeeeModel.scale_step_1_prog [x; a] 2 0 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax (fun x y => nan_fma x y x) (fun x y => nan_fma x y x)
    (fun x => nan_fma x x x) nan_fma IeeeModel.scale_step_1_prog [x; a] 2 1 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
Qed.

Theorem sub_1_1_ieee_lead : sub_1_1_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_minus a b. cbv zeta. rewrite
    (sub_1_1_runB prec emax nan_minus nan_minus (fun x => nan_minus x x)
    (fun x y _ => nan_minus x y)).
intros Fz.
split.
- exact (lead_cone prec emax nan_minus nan_minus (fun x => nan_minus x x)
    (fun x y _ => nan_minus x y) IeeeModel.sub_1_1_prog [a; b] 2 0 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_minus nan_minus (fun x => nan_minus x x)
    (fun x y _ => nan_minus x y) IeeeModel.sub_1_1_prog [a; b] 2 1 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
Qed.

Theorem sub_entry_step_1_ieee_lead : sub_entry_step_1_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus x y. cbv zeta. rewrite
    (sub_entry_step_1_runB prec emax nan_plus nan_minus (fun x => nan_plus x x)
    (fun x y _ => nan_plus x y)).
intros Fz.
split.
- exact (lead_cone prec emax nan_plus nan_minus (fun x => nan_plus x x) (fun x y _ => nan_plus x y)
    IeeeModel.sub_entry_step_1_prog [x; y] 4 0 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_minus (fun x => nan_plus x x) (fun x y _ => nan_plus x y)
    IeeeModel.sub_entry_step_1_prog [x; y] 4 1 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
Qed.

Theorem add_entry_step_2_ieee_lead : add_entry_step_2_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus x0 x1 y0 y1. rewrite
    (add_entry_step_2_runB prec emax nan_plus nan_minus (fun x => nan_plus x x)
    (fun x y _ => nan_plus x y)).
intros Fz.
split.
- exact (lead_cone prec emax nan_plus nan_minus (fun x => nan_plus x x) (fun x y _ => nan_plus x y)
    IeeeModel.add_entry_step_2_prog [x0; x1; y0; y1] 25 0 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_minus (fun x => nan_plus x x) (fun x y _ => nan_plus x y)
    IeeeModel.add_entry_step_2_prog [x0; x1; y0; y1] 25 2 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
Qed.

Theorem axpy_entry_step_2_ieee_lead : axpy_entry_step_2_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma a0 a1 x0 x1 y0 y1. rewrite
    (axpy_entry_step_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros Fz.
split; [|split].
- exact (lead_cone prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.axpy_entry_step_2_prog
    [a0; a1; x0; x1; y0; y1] 34 0 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.axpy_entry_step_2_prog
    [a0; a1; x0; x1; y0; y1] 34 2 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.axpy_entry_step_2_prog
    [a0; a1; x0; x1; y0; y1] 34 4 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
Qed.

Theorem axpy_entry_step_2_1_ieee_lead : axpy_entry_step_2_1_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma a x0 x1 y0 y1. rewrite
    (axpy_entry_step_2_1_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros Fz.
split; [|split].
- exact (lead_cone prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.axpy_entry_step_2_1_prog
    [a; x0; x1; y0; y1] 30 0 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.axpy_entry_step_2_1_prog
    [a; x0; x1; y0; y1] 30 1 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.axpy_entry_step_2_1_prog
    [a; x0; x1; y0; y1] 30 3 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
Qed.

Theorem axpy_step_2_ieee_lead : axpy_step_2_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma a0 a1 x0 x1 y0 y1. rewrite
    (axpy_step_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros Fz.
split; [|split].
- exact (lead_cone prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.axpy_step_2_prog
    [a0; a1; x0; x1; y0; y1] 32 0 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.axpy_step_2_prog
    [a0; a1; x0; x1; y0; y1] 32 2 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.axpy_step_2_prog
    [a0; a1; x0; x1; y0; y1] 32 4 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
Qed.

Theorem axpy_step_2_1_ieee_lead : axpy_step_2_1_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma a x0 x1 y0 y1. rewrite
    (axpy_step_2_1_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros Fz.
split; [|split].
- exact (lead_cone prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.axpy_step_2_1_prog
    [a; x0; x1; y0; y1] 28 0 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.axpy_step_2_1_prog
    [a; x0; x1; y0; y1] 28 1 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.axpy_step_2_1_prog
    [a; x0; x1; y0; y1] 28 3 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
Qed.

Theorem mul_pow2_step_2_ieee_lead : mul_pow2_step_2_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_fma x0 x1 c. rewrite
    (mul_pow2_step_2_runB prec emax nan_plus nan_minus (fun x => nan_plus x x) nan_fma).
intros Fz.
split.
- exact (lead_cone prec emax nan_plus nan_minus (fun x => nan_plus x x) nan_fma
    IeeeModel.mul_pow2_step_2_prog [x0; x1; c] 5 0 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_minus (fun x => nan_plus x x) nan_fma
    IeeeModel.mul_pow2_step_2_prog [x0; x1; c] 5 2 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
Qed.

Theorem scale_step_2_ieee_lead : scale_step_2_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma x0 x1 a. rewrite
    (scale_step_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
intros Fz.
split.
- exact (lead_cone prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.scale_step_2_prog
    [x0; x1; a] 6 0 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.scale_step_2_prog
    [x0; x1; a] 6 2 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
Qed.

Theorem sub_2_2_ieee_lead : sub_2_2_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp x0 x1 y0 y1. rewrite
    (sub_2_2_runB prec emax nan_plus nan_minus nan_opp (fun x y _ => nan_plus x y)).
intros Fz.
split.
- exact (lead_cone prec emax nan_plus nan_minus nan_opp (fun x y _ => nan_plus x y)
    IeeeModel.sub_2_2_prog [x0; x1; y0; y1] 23 0 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_minus nan_opp (fun x y _ => nan_plus x y)
    IeeeModel.sub_2_2_prog [x0; x1; y0; y1] 23 2 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
Qed.

Theorem sub_entry_step_2_ieee_lead : sub_entry_step_2_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp x0 x1 y0 y1. rewrite
    (sub_entry_step_2_runB prec emax nan_plus nan_minus nan_opp (fun x y _ => nan_plus x y)).
intros Fz.
split.
- exact (lead_cone prec emax nan_plus nan_minus nan_opp (fun x y _ => nan_plus x y)
    IeeeModel.sub_entry_step_2_prog [x0; x1; y0; y1] 27 0 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
- exact (lead_cone prec emax nan_plus nan_minus nan_opp (fun x y _ => nan_plus x y)
    IeeeModel.sub_entry_step_2_prog [x0; x1; y0; y1] 27 2 eq_refl eq_refl
           ltac:(cbn [length]; lia) Fz).
Qed.
