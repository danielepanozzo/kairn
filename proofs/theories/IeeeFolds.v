(* The folds in the IEEE model: the flag, and what a finite result means.

   The generator does not print the IEEE model of a fold yet. This file writes it by hand,
   for every fold of proofs/gen/FoldModel.v and both orders, from the generated IEEE
   models of the kernels (proofs/gen/IeeeModel.v) and the two orders of Folds.v, in the
   shape of the real model:

       F_step_ieee, F_combine_ieee      the IEEE models of the step and the combination,
                                        applied to the limbs of tuples
       F_seq_ieee xs                    finish (fold_seq F_step_ieee zero xs)
       F_lanes_ieee W xs                finish (fold_lanes F_step_ieee F_combine_ieee zero W xs)

   with the zero state +0 in every limb and the finish fold_finish_1 or fold_finish_2. It
   proves of each the statement of docs/developer/design/milestone2.md, "When something
   is not finite" (F_seq_ieee_correct, F_lanes_ieee_correct). For every list of elements
   (any values of the format, infinities and NaN included, for one limb; canonical pairs
   for two limbs), with (r, flag) the result:

   - if flag is true: every element is finite; the result is finite; its value is the
     result of the real model of the fold (proofs/gen/FoldModel.v) on the values of the
     elements; hence it is valid and within the bound of the real-model statement
     (FoldSums.v), which is restated here for those values; and, in the sequential
     order, the state after every element was finite;
   - if flag is false: every limb of the result is a NaN.
   The flag is true exactly when the leading limb of the final state is finite
   (IeeeFoldFinish.v). So an element that is not finite, or an overflow anywhere in the
   loop, gives the flag false: there is no finite wrong result.

   How. FoldTransfer.v reduces the statement to two facts about one application of the
   step (and of the combination), which this file proves for the kernels of the folds:

       dead    if the leading limb of the result is finite, so is that of the state
               (and of the element): the first limb of the result of add_2_2,
               add_fast_2_2 and mul_2_2 is a sum of sums, or of a product, of the
               leading limbs, and an IEEE addition or fused operation with an operand
               that is not finite is not finite (add_finite_inv, fma_finite_inv of
               IeeeBridge.v). Until now this was the generator's syntactic cone check;
       live    from a finite, valid state and a canonical element, a finite leading limb
               of the result gives: the element is finite, every limb of the result is
               finite, the result is valid, and its values are those of the real model
               of the kernel. This is the bridge of Milestone 1 (add_2_2_ieee_bridge,
               add_fast_2_2_ieee_bridge, mul_2_2_ieee_bridge; add_spec and fma_spec for
               one limb), with the real-model theorem of the kernel for validity.

   The steps: add_1_1, sum_entry_step_1, dot_step_1 (one limb); add_2_2, add_fast_2_2,
   sum_entry_step_2, sum_fast_entry_step_2, dot_step_2 (two limbs). An entry step guards
   its element first: the guard keeps the finiteness and the value of a limb (guard_finite,
   guard_val of IeeeOps.v), and in the real model it returns a number of the format
   unchanged (guard_real_any).

   Vocabulary of this file, for a pair x of limbs: vals2 x, the pair of the values;
   lead2 x, the leading limb is finite; good2 x, both limbs are finite and the pair is
   normalized; can2 x, the pair is canonical (canonical_2 of IeeeVocabulary.v). *)
From Stdlib Require Import Reals ZArith List Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements FoldModel FoldStatements.
From Kairn Require Import Format Guard Add22 AddFast22 Mul22 Program IeeeBridge IeeeVocabulary
  IeeeOps IeeeAdd22 IeeeMul22 IeeeMore Folds FoldTransfer Summation FoldSums IeeeFoldFinish.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Import ListNotations.
Open Scope R_scope.

(** * The real model: a pair matched and rebuilt, and the entry steps *)

Lemma pair_eta :
  forall (C D : Type) (p : C * D), (let '(a, b) := p in (a, b)) = p.
Proof. intros C D [a b]. reflexivity. Qed.

(* In the real model an entry step is its addition, on an element of the format. *)
Lemma sum_entry_step_1_real :
  forall (emin prec : Z) (s x : R), fmt emin prec x ->
  sum_entry_step_1 emin prec tie_even s x = add_1_1 emin prec tie_even s x.
Proof.
intros emin prec s x Fx. unfold sum_entry_step_1, add_1_1. cbv zeta.
now rewrite (guard_real_any emin prec tie_even x Fx).
Qed.

Lemma sum_entry_step_2_real :
  forall (emin prec : Z) (s0 s1 x0 x1 : R), fmt emin prec x0 -> fmt emin prec x1 ->
  sum_entry_step_2 emin prec tie_even s0 s1 x0 x1 = add_2_2 emin prec tie_even s0 s1 x0 x1.
Proof.
intros emin prec s0 s1 x0 x1 F0 F1. unfold sum_entry_step_2. cbv zeta.
rewrite (guard_real_any emin prec tie_even x0 F0), (guard_real_any emin prec tie_even x1 F1).
apply pair_eta.
Qed.

Lemma sum_fast_entry_step_2_real :
  forall (emin prec : Z) (s0 s1 x0 x1 : R), fmt emin prec x0 -> fmt emin prec x1 ->
  sum_fast_entry_step_2 emin prec tie_even s0 s1 x0 x1 =
  add_fast_2_2 emin prec tie_even s0 s1 x0 x1.
Proof.
intros emin prec s0 s1 x0 x1 F0 F1. unfold sum_fast_entry_step_2. cbv zeta.
rewrite (guard_real_any emin prec tie_even x0 F0), (guard_real_any emin prec tie_even x1 F1).
apply pair_eta.
Qed.

Section IeeeFolds.
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
Variable nan_const : nan_of.

Notation emin := (ieee_emin prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation guard := (IeeeOperations.guard prec emax nan_plus).

(* A value of the IEEE format is a number of the real format. *)
Lemma val_fmt : forall x : float, fmt emin prec (val x).
Proof. intros x. exact (b2r_format prec emax x). Qed.

(** * One limb: the steps *)

(* add_1_1: the step of sum_1 and the combination of every fold of one limb. *)
Lemma add_1_1_dead :
  forall a b : float, finite (IeeeModel.add_1_1 prec emax nan_plus a b) -> finite a /\ finite b.
Proof. intros a b H. exact (add_finite_inv prec emax nan_plus a b H). Qed.

Lemma add_1_1_live :
  forall a b : float, finite a -> finite b -> finite (IeeeModel.add_1_1 prec emax nan_plus a b) ->
  val (IeeeModel.add_1_1 prec emax nan_plus a b) = add_1_1 emin prec tie_even (val a) (val b).
Proof. intros a b Fa Fb F. exact (proj2 (add_spec prec emax nan_plus a b Fa Fb) F). Qed.

(* sum_entry_step_1: the addition of the guarded element. *)
Lemma sum_entry_step_1_dead :
  forall s x : float, finite (IeeeModel.sum_entry_step_1 prec emax nan_plus s x) ->
  finite s /\ finite x.
Proof.
intros s x H. destruct (add_finite_inv prec emax nan_plus s (guard x) H) as [Fs Fg].
split. exact Fs. rewrite (guard_finite prec emax nan_plus) in Fg. exact Fg.
Qed.

Lemma sum_entry_step_1_live :
  forall s x : float, finite s -> finite x ->
  finite (IeeeModel.sum_entry_step_1 prec emax nan_plus s x) ->
  val (IeeeModel.sum_entry_step_1 prec emax nan_plus s x) =
  sum_entry_step_1 emin prec tie_even (val s) (val x).
Proof.
intros s x Fs Fx F.
assert (Fg : finite (guard x)).
{ unfold finite. rewrite (guard_finite prec emax nan_plus). exact Fx. }
rewrite (sum_entry_step_1_real emin prec (val s) (val x) (val_fmt x)).
pose proof (add_1_1_live s (guard x) Fs Fg F) as E.
unfold val in E |- *. rewrite (guard_val prec emax nan_plus) in E. exact E.
Qed.

(* dot_step_1: one fused operation. *)
Lemma dot_step_1_dead :
  forall s x y : float, finite (IeeeModel.dot_step_1 prec emax nan_fma s x y) ->
  finite s /\ finite x /\ finite y.
Proof.
intros s x y H. destruct (fma_finite_inv prec emax nan_fma x y s H) as [Fx [Fy Fs]].
split. exact Fs. split; assumption.
Qed.

Lemma dot_step_1_live :
  forall s x y : float, finite s -> finite x -> finite y ->
  finite (IeeeModel.dot_step_1 prec emax nan_fma s x y) ->
  val (IeeeModel.dot_step_1 prec emax nan_fma s x y) =
  dot_step_1 emin prec tie_even (val s) (val x) (val y).
Proof. intros s x y Fs Fx Fy F. exact (proj2 (fma_spec prec emax nan_fma x y s Fx Fy Fs) F). Qed.

(** * Two limbs: the vocabulary *)

Definition vals2 (x : float * float) : R * R := (val (fst x), val (snd x)).
Definition lead2 (x : float * float) : Prop := finite (fst x).
Definition good2 (x : float * float) : Prop :=
  finite (fst x) /\ finite (snd x) /\ normalized_2 emin prec (val (fst x)) (val (snd x)).
Definition can2 (x : float * float) : Prop := canonical_2 (fst x) (snd x).
Definition zero2 : float * float := (pzero, pzero).

Lemma zero2_good : good2 zero2.
Proof.
unfold good2, zero2. cbn [fst snd]. split. reflexivity. split. reflexivity.
change (val pzero) with 0.
split. apply generic_format_0. split. apply generic_format_0.
unfold RN. rewrite Rplus_0_l. symmetry. apply round_0; auto with typeclass_instances.
Qed.

(* A canonical pair with a finite leading limb is finite and normalized. *)
Lemma can2_good : forall x : float * float, can2 x -> lead2 x -> good2 x.
Proof.
intros [x0 x1] C L. unfold can2, lead2, good2, finite in *. cbn [fst snd] in *.
destruct C as [[F0 [F1 N]]|[[[s E] _]|[N _]]].
- split. exact F0. split. exact F1. exact N.
- rewrite E in L. discriminate L.
- apply (nan_not_finite prec emax) in N. congruence.
Qed.

Lemma good2_fmt :
  forall x : float * float, fmt emin prec (val (fst x)) /\ fmt emin prec (val (snd x)).
Proof. intros x. split; apply val_fmt. Qed.

(* The values of good pairs are normalized pairs: the requirement of the real model. *)
Lemma good2_normalized :
  forall xs : list (float * float), Forall good2 xs ->
  Forall (fun x => normalized_2 emin prec (fst x) (snd x)) (map vals2 xs).
Proof.
intros xs H. induction H as [|x r [_ [_ N]] _ IH]; cbn [map]; constructor.
- exact N.
- exact IH.
Qed.

(* The guarded pair: as finite as the pair, with its values. *)
Definition guard2i (x : float * float) : float * float := (guard (fst x), guard (snd x)).

Lemma guard2i_lead : forall x : float * float, lead2 (guard2i x) -> lead2 x.
Proof.
intros [x0 x1]. unfold lead2, guard2i, finite. cbn [fst snd].
now rewrite (guard_finite prec emax nan_plus).
Qed.

Lemma guard2i_good : forall x : float * float, good2 x -> good2 (guard2i x).
Proof.
intros [x0 x1]. unfold good2, guard2i, finite, val. cbn [fst snd].
rewrite 2!(guard_finite prec emax nan_plus), 2!(guard_val prec emax nan_plus).
intros H. exact H.
Qed.

Lemma guard2i_vals : forall x : float * float, vals2 (guard2i x) = vals2 x.
Proof.
intros [x0 x1]. unfold vals2, guard2i, val. cbn [fst snd].
now rewrite 2!(guard_val prec emax nan_plus).
Qed.

(** * Two limbs: the additions and the product *)

Definition add22i (s x : float * float) : float * float :=
  IeeeModel.add_2_2 prec emax nan_plus nan_minus (fst s) (snd s) (fst x) (snd x).

Definition addfast22i (s x : float * float) : float * float :=
  IeeeModel.add_fast_2_2 prec emax nan_plus nan_minus (fst s) (snd s) (fst x) (snd x).

Definition mul22i (x y : float * float) : float * float :=
  IeeeModel.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma (fst x) (snd x) (fst y) (snd y).

(* The leading limb of each result is not finite unless both leading limbs are. *)
Lemma add22i_lead : forall s x : float * float, lead2 (add22i s x) -> lead2 s /\ lead2 x.
Proof.
intros [s0 s1] [x0 x1]. unfold lead2, add22i, finite. cbn [fst snd].
unfold IeeeModel.add_2_2, IeeeModel.two_sum, IeeeModel.fast_two_sum.
cbv beta iota zeta. cbn [fst].
intros H. apply (add_finite_inv prec emax nan_plus) in H. destruct H as [H _].
apply (add_finite_inv prec emax nan_plus) in H. destruct H as [H _].
exact (add_finite_inv prec emax nan_plus _ _ H).
Qed.

Lemma addfast22i_lead :
  forall s x : float * float, lead2 (addfast22i s x) -> lead2 s /\ lead2 x.
Proof.
intros [s0 s1] [x0 x1]. unfold lead2, addfast22i, finite. cbn [fst snd].
unfold IeeeModel.add_fast_2_2, IeeeModel.two_sum, IeeeModel.fast_two_sum.
cbv beta iota zeta. cbn [fst].
intros H. apply (add_finite_inv prec emax nan_plus) in H. destruct H as [H _].
exact (add_finite_inv prec emax nan_plus _ _ H).
Qed.

Lemma mul22i_lead : forall x y : float * float, lead2 (mul22i x y) -> lead2 x /\ lead2 y.
Proof.
intros [x0 x1] [y0 y1]. unfold lead2, mul22i, finite. cbn [fst snd].
unfold IeeeModel.mul_2_2, IeeeModel.two_prod, IeeeModel.fast_two_sum.
cbv beta iota zeta. cbn [fst].
intros H. apply (add_finite_inv prec emax nan_plus) in H. destruct H as [H _].
unfold IeeeOperations.prod in H.
destruct (fma_finite_inv prec emax nan_fma _ _ _ H) as [Fx [Fy _]].
split; assumption.
Qed.

(* On good operands, a finite leading limb: a good result with the values of the real
   model. *)
Lemma add22i_live :
  (3 <= prec)%Z ->
  forall s x : float * float, good2 s -> good2 x -> lead2 (add22i s x) ->
  good2 (add22i s x) /\
  vals2 (add22i s x) =
  add_2_2 emin prec tie_even (val (fst s)) (val (snd s)) (val (fst x)) (val (snd x)).
Proof.
intros Hp [s0 s1] [x0 x1] [Fs0 [Fs1 Ns]] [Fx0 [Fx1 Nx]].
unfold add22i, lead2, good2, vals2. cbn [fst snd] in *.
generalize (add_2_2_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              (fun a => nan_plus a a) (fun a b _ => nan_plus a b) Hp
              s0 s1 x0 x1 Fs0 Fs1 Fx0 Fx1 Ns Nx).
generalize (add_2_2_correct emin prec Hp (val s0) (val s1) (val x0) (val x1) Ns Nx).
destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus s0 s1 x0 x1) as [z0 z1].
cbn [fst snd]. intros Hr B L. destruct (B L) as [_ [Fz1 E]].
rewrite <- E in Hr. cbv beta iota in Hr. destruct Hr as [Nz _].
split. { split. exact L. split. exact Fz1. exact Nz. } exact E.
Qed.

Lemma addfast22i_live :
  (2 <= prec)%Z ->
  forall s x : float * float, good2 s -> good2 x -> lead2 (addfast22i s x) ->
  good2 (addfast22i s x) /\
  vals2 (addfast22i s x) =
  add_fast_2_2 emin prec tie_even (val (fst s)) (val (snd s)) (val (fst x)) (val (snd x)).
Proof.
intros Hp [s0 s1] [x0 x1] [Fs0 [Fs1 Ns]] [Fx0 [Fx1 Nx]].
unfold addfast22i, lead2, good2, vals2. cbn [fst snd] in *.
generalize (add_fast_2_2_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              (fun a => nan_plus a a) (fun a b _ => nan_plus a b) Hp
              s0 s1 x0 x1 Fs0 Fs1 Fx0 Fx1 Ns Nx).
generalize (add_fast_2_2_correct emin prec Hp (val s0) (val s1) (val x0) (val x1) Ns Nx).
destruct (IeeeModel.add_fast_2_2 prec emax nan_plus nan_minus s0 s1 x0 x1) as [z0 z1].
cbn [fst snd]. intros Hr B L. destruct (B L) as [_ [Fz1 E]].
rewrite <- E in Hr. cbv beta iota in Hr. destruct Hr as [Nz _].
split. { split. exact L. split. exact Fz1. exact Nz. } exact E.
Qed.

Lemma mul22i_live :
  (4 <= prec)%Z ->
  forall x y : float * float, good2 x -> good2 y -> lead2 (mul22i x y) ->
  good2 (mul22i x y) /\
  vals2 (mul22i x y) =
  mul_2_2 emin prec tie_even (val (fst x)) (val (snd x)) (val (fst y)) (val (snd y)).
Proof.
intros Hp [x0 x1] [y0 y1] [Fx0 [Fx1 Nx]] [Fy0 [Fy1 Ny]].
unfold mul22i, lead2, good2, vals2. cbn [fst snd] in *.
generalize (mul_2_2_ieee_bridge prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              nan_opp nan_fma Hp x0 x1 y0 y1 Fx0 Fx1 Fy0 Fy1 Nx Ny).
generalize (mul_2_2_correct emin prec Hp (val x0) (val x1) (val y0) (val y1) Nx Ny).
destruct (IeeeModel.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 y0 y1)
  as [z0 z1].
cbn [fst snd]. intros Hr B L. destruct (B L) as [_ [Fz1 E]].
rewrite <- E in Hr. cbv beta iota in Hr. destruct Hr as [Nz _].
split. { split. exact L. split. exact Fz1. exact Nz. } exact E.
Qed.

(** * The folds with their finish *)

Definition finish1 (s : float) : float * bool :=
  IeeeModel.fold_finish_1 prec emax nan_abs nan_const s.

Definition finish2 (s : float * float) : float * float * bool :=
  IeeeModel.fold_finish_2 prec emax nan_abs nan_const (fst s) (snd s).

Lemma finish1_spec :
  forall s : float,
  let '(r, flag) := finish1 s in
  (flag = true -> finite s /\ r = s) /\ (flag = false -> nan r).
Proof.
intros s. unfold finish1.
generalize (fold_finish_1_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const s).
destruct (IeeeModel.fold_finish_1 prec emax nan_abs nan_const s) as [r flag].
intros [H1 [H2 H3]]. split.
- intros E. split. now apply H1. now apply H2.
- exact H3.
Qed.

Lemma finish2_spec :
  forall s : float * float,
  let '(r0, r1, flag) := finish2 s in
  (flag = true -> lead2 s /\ (r0, r1) = s) /\ (flag = false -> nan r0 /\ nan r1).
Proof.
intros [s0 s1]. unfold finish2, lead2. cbn [fst snd].
generalize (fold_finish_2_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const s0 s1).
destruct (IeeeModel.fold_finish_2 prec emax nan_abs nan_const s0 s1) as [[r0 r1] flag].
intros [H1 [H2 H3]]. split.
- intros E. split. now apply H1. destruct (H2 E) as [E0 E1]. now rewrite E0, E1.
- exact H3.
Qed.

(* One limb, the sequential order. step' is the step of the real model, vb the values of
   an element, finb what a finite result shows of an element. *)
Theorem seq_1 :
  forall (B B' : Type) (step : float -> B -> float) (step' : R -> B' -> R)
         (vb : B -> B') (finb : B -> Prop),
  (forall (s : float) (e : B), finite (step s e) -> finite s) ->
  (forall (s : float) (e : B), finite s -> finite (step s e) ->
   finb e /\ val (step s e) = step' (val s) (vb e)) ->
  forall xs : list B,
  let '(r, flag) := finish1 (fold_seq step pzero xs) in
  (flag = true ->
   Forall finb xs /\ finite r /\ val r = fold_seq step' 0 (map vb xs) /\
   forall k : nat, finite (fold_seq step pzero (firstn k xs))) /\
  (flag = false -> nan r).
Proof.
intros B B' step step' vb finb Hdead Hlive xs.
generalize (finish1_spec (fold_seq step pzero xs)).
destruct (finish1 (fold_seq step pzero xs)) as [r flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [L Er]. rewrite Er.
assert (Hl : forall (s : float) (e : B), finite s -> True -> finite (step s e) ->
             finite (step s e) /\ finb e /\ val (step s e) = step' (val s) (vb e)).
{ intros s e Fs _ F. destruct (Hlive s e Fs F) as [Fe V]. split. exact F. split; assumption. }
assert (Ht : Forall (fun _ : B => True) xs) by (apply Forall_forall; intros; exact I).
destruct (fold_seq_transfer _ _ _ _ step step' (@val prec emax) vb (@finite prec emax)
            (@finite prec emax) (fun _ => True) finb Hdead Hl pzero xs eq_refl Ht L)
  as [G [F V]].
split. exact F. split. exact G. split. exact V.
intros k.
exact (proj1 (fold_seq_transfer_prefix _ _ _ _ step step' (@val prec emax) vb
                (@finite prec emax) (@finite prec emax) (fun _ => True) finb Hdead Hl
                pzero xs k eq_refl Ht L)).
Qed.

(* One limb, the lane order, for every number of lanes. *)
Theorem lanes_1 :
  forall (B B' : Type) (step : float -> B -> float) (step' : R -> B' -> R)
         (combine : float -> float -> float) (combine' : R -> R -> R)
         (vb : B -> B') (finb : B -> Prop),
  (forall (s : float) (e : B), finite (step s e) -> finite s) ->
  (forall (s : float) (e : B), finite s -> finite (step s e) ->
   finb e /\ val (step s e) = step' (val s) (vb e)) ->
  (forall a b : float, finite (combine a b) -> finite a /\ finite b) ->
  (forall a b : float, finite a -> finite b -> finite (combine a b) ->
   val (combine a b) = combine' (val a) (val b)) ->
  forall (W : nat) (xs : list B),
  let '(r, flag) := finish1 (fold_lanes step combine pzero W xs) in
  (flag = true ->
   Forall finb xs /\ finite r /\ val r = fold_lanes step' combine' 0 W (map vb xs)) /\
  (flag = false -> nan r).
Proof.
intros B B' step step' combine combine' vb finb Hdead Hlive Hcd Hcl W xs.
generalize (finish1_spec (fold_lanes step combine pzero W xs)).
destruct (finish1 (fold_lanes step combine pzero W xs)) as [r flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [L Er]. rewrite Er.
assert (Hl : forall (s : float) (e : B), finite s -> True -> finite (step s e) ->
             finite (step s e) /\ finb e /\ val (step s e) = step' (val s) (vb e)).
{ intros s e Fs _ F. destruct (Hlive s e Fs F) as [Fe V]. split. exact F. split; assumption. }
assert (Hc : forall a b : float, finite a -> finite b -> finite (combine a b) ->
             finite (combine a b) /\ val (combine a b) = combine' (val a) (val b)).
{ intros a b Fa Fb F. split. exact F. now apply Hcl. }
assert (Ht : Forall (fun _ : B => True) xs) by (apply Forall_forall; intros; exact I).
destruct (fold_lanes_transfer _ _ _ _ step step' (@val prec emax) vb (@finite prec emax)
            (@finite prec emax) (fun _ => True) finb Hdead Hl combine combine' Hcd Hc
            pzero W xs eq_refl Ht L) as [G [F V]].
split. exact F. split. exact G. exact V.
Qed.

(* Two limbs, the sequential order. elt is what is assumed of an element. *)
Theorem seq_2 :
  forall (B B' : Type) (step : float * float -> B -> float * float)
         (step' : R * R -> B' -> R * R) (vb : B -> B') (elt finb : B -> Prop),
  (forall (s : float * float) (e : B), lead2 (step s e) -> lead2 s) ->
  (forall (s : float * float) (e : B), good2 s -> elt e -> lead2 (step s e) ->
   good2 (step s e) /\ finb e /\ vals2 (step s e) = step' (vals2 s) (vb e)) ->
  forall xs : list B, Forall elt xs ->
  let '(r0, r1, flag) := finish2 (fold_seq step zero2 xs) in
  (flag = true ->
   Forall finb xs /\ good2 (r0, r1) /\ vals2 (r0, r1) = fold_seq step' (0, 0) (map vb xs) /\
   forall k : nat, good2 (fold_seq step zero2 (firstn k xs))) /\
  (flag = false -> nan r0 /\ nan r1).
Proof.
intros B B' step step' vb elt finb Hdead Hlive xs Hx.
generalize (finish2_spec (fold_seq step zero2 xs)).
destruct (finish2 (fold_seq step zero2 xs)) as [[r0 r1] flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [L Er]. rewrite Er.
destruct (fold_seq_transfer _ _ _ _ step step' vals2 vb lead2 good2 elt finb Hdead Hlive
            zero2 xs zero2_good Hx L) as [G [F V]].
split. exact F. split. exact G. split. exact V.
intros k.
exact (proj1 (fold_seq_transfer_prefix _ _ _ _ step step' vals2 vb lead2 good2 elt finb
                Hdead Hlive zero2 xs k zero2_good Hx L)).
Qed.

(* Two limbs, the lane order, for every number of lanes. *)
Theorem lanes_2 :
  forall (B B' : Type) (step : float * float -> B -> float * float)
         (step' : R * R -> B' -> R * R)
         (combine : float * float -> float * float -> float * float)
         (combine' : R * R -> R * R -> R * R) (vb : B -> B') (elt finb : B -> Prop),
  (forall (s : float * float) (e : B), lead2 (step s e) -> lead2 s) ->
  (forall (s : float * float) (e : B), good2 s -> elt e -> lead2 (step s e) ->
   good2 (step s e) /\ finb e /\ vals2 (step s e) = step' (vals2 s) (vb e)) ->
  (forall a b : float * float, lead2 (combine a b) -> lead2 a /\ lead2 b) ->
  (forall a b : float * float, good2 a -> good2 b -> lead2 (combine a b) ->
   good2 (combine a b) /\ vals2 (combine a b) = combine' (vals2 a) (vals2 b)) ->
  forall (W : nat) (xs : list B), Forall elt xs ->
  let '(r0, r1, flag) := finish2 (fold_lanes step combine zero2 W xs) in
  (flag = true ->
   Forall finb xs /\ good2 (r0, r1) /\
   vals2 (r0, r1) = fold_lanes step' combine' (0, 0) W (map vb xs)) /\
  (flag = false -> nan r0 /\ nan r1).
Proof.
intros B B' step step' combine combine' vb elt finb Hdead Hlive Hcd Hcl W xs Hx.
generalize (finish2_spec (fold_lanes step combine zero2 W xs)).
destruct (finish2 (fold_lanes step combine zero2 W xs)) as [[r0 r1] flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [L Er]. rewrite Er.
destruct (fold_lanes_transfer _ _ _ _ step step' vals2 vb lead2 good2 elt finb Hdead Hlive
            combine combine' Hcd Hcl zero2 W xs zero2_good Hx L) as [G [F V]].
split. exact F. split. exact G. exact V.
Qed.

(** * The steps of the folds, in the form that the theorems above take *)

(* One limb. *)
Lemma add_1_1_step_dead :
  forall s e : float, finite (IeeeModel.add_1_1 prec emax nan_plus s e) -> finite s.
Proof. intros s e H. exact (proj1 (add_1_1_dead s e H)). Qed.

Lemma add_1_1_step_live :
  forall s e : float, finite s -> finite (IeeeModel.add_1_1 prec emax nan_plus s e) ->
  finite e /\
  val (IeeeModel.add_1_1 prec emax nan_plus s e) = add_1_1 emin prec tie_even (val s) (val e).
Proof.
intros s e Fs F. destruct (add_1_1_dead s e F) as [_ Fe].
split. exact Fe. exact (add_1_1_live s e Fs Fe F).
Qed.

Lemma sum_entry_step_1_step_dead :
  forall s e : float, finite (IeeeModel.sum_entry_step_1 prec emax nan_plus s e) -> finite s.
Proof. intros s e H. exact (proj1 (sum_entry_step_1_dead s e H)). Qed.

Lemma sum_entry_step_1_step_live :
  forall s e : float, finite s -> finite (IeeeModel.sum_entry_step_1 prec emax nan_plus s e) ->
  finite e /\
  val (IeeeModel.sum_entry_step_1 prec emax nan_plus s e) =
  sum_entry_step_1 emin prec tie_even (val s) (val e).
Proof.
intros s e Fs F. destruct (sum_entry_step_1_dead s e F) as [_ Fe].
split. exact Fe. exact (sum_entry_step_1_live s e Fs Fe F).
Qed.

(* An element of dot_1: one number of each array. *)
Definition vals11 (xy : float * float) : R * R := (val (fst xy), val (snd xy)).
Definition fin11 (xy : float * float) : Prop := finite (fst xy) /\ finite (snd xy).

Lemma dot_step_1_step_dead :
  forall (s : float) (xy : float * float),
  finite (IeeeModel.dot_step_1 prec emax nan_fma s (fst xy) (snd xy)) -> finite s.
Proof. intros s xy H. exact (proj1 (dot_step_1_dead s (fst xy) (snd xy) H)). Qed.

Lemma dot_step_1_step_live :
  forall (s : float) (xy : float * float), finite s ->
  finite (IeeeModel.dot_step_1 prec emax nan_fma s (fst xy) (snd xy)) ->
  fin11 xy /\
  val (IeeeModel.dot_step_1 prec emax nan_fma s (fst xy) (snd xy)) =
  FoldModel.dot_1_step emin prec tie_even (val s) (vals11 xy).
Proof.
intros s xy Fs F. destruct (dot_step_1_dead s (fst xy) (snd xy) F) as [_ [Fx Fy]].
split. split; assumption. exact (dot_step_1_live s (fst xy) (snd xy) Fs Fx Fy F).
Qed.

(* The values of any elements of one limb are numbers of the format: the requirement of
   the real model. *)
Lemma vals_fmt : forall xs : list float, Forall (fun x => fmt emin prec x) (map val xs).
Proof.
intros xs. induction xs as [|x r IH]; cbn [map]; constructor.
- apply val_fmt.
- exact IH.
Qed.

Lemma vals11_fmt :
  forall xs : list (float * float),
  Forall (fun xy => fmt emin prec (fst xy) /\ fmt emin prec (snd xy)) (map vals11 xs).
Proof.
intros xs. induction xs as [|x r IH]; cbn [map]; constructor.
- unfold vals11. cbn [fst snd]. split; apply val_fmt.
- exact IH.
Qed.

(* Two limbs: a step that adds its element to the state, as it is (an array written through
   Kairn) or guarded first (an array of the program). addi is the IEEE addition and addr
   the real one. *)
Lemma stored_step_live :
  forall (addi : float * float -> float * float -> float * float)
         (addr : R -> R -> R -> R -> R * R),
  (forall s x : float * float, lead2 (addi s x) -> lead2 s /\ lead2 x) ->
  (forall s x : float * float, good2 s -> good2 x -> lead2 (addi s x) ->
   good2 (addi s x) /\
   vals2 (addi s x) = addr (val (fst s)) (val (snd s)) (val (fst x)) (val (snd x))) ->
  forall s x : float * float, good2 s -> can2 x -> lead2 (addi s x) ->
  good2 (addi s x) /\ good2 x /\
  vals2 (addi s x) = addr (val (fst s)) (val (snd s)) (val (fst x)) (val (snd x)).
Proof.
intros addi addr Hlead Hlive s x Gs Cx L.
destruct (Hlead s x L) as [_ Lx].
pose proof (can2_good x Cx Lx) as Gx.
destruct (Hlive s x Gs Gx L) as [G V].
split. exact G. split. exact Gx. exact V.
Qed.

Lemma entry_step_live :
  forall (addi : float * float -> float * float -> float * float)
         (addr : R -> R -> R -> R -> R * R),
  (forall s x : float * float, lead2 (addi s x) -> lead2 s /\ lead2 x) ->
  (forall s x : float * float, good2 s -> good2 x -> lead2 (addi s x) ->
   good2 (addi s x) /\
   vals2 (addi s x) = addr (val (fst s)) (val (snd s)) (val (fst x)) (val (snd x))) ->
  forall s x : float * float, good2 s -> can2 x -> lead2 (addi s (guard2i x)) ->
  good2 (addi s (guard2i x)) /\ good2 x /\
  vals2 (addi s (guard2i x)) = addr (val (fst s)) (val (snd s)) (val (fst x)) (val (snd x)).
Proof.
intros addi addr Hlead Hlive s x Gs Cx L.
destruct (Hlead _ _ L) as [_ Lg].
pose proof (can2_good x Cx (guard2i_lead x Lg)) as Gx.
destruct (Hlive s (guard2i x) Gs (guard2i_good x Gx) L) as [G V].
split. exact G. split. exact Gx.
rewrite V.
exact (f_equal (fun p : R * R => addr (val (fst s)) (val (snd s)) (fst p) (snd p))
         (guard2i_vals x)).
Qed.

(* sum_2 and sum_2_entry: add_2_2. *)
Definition sum_2_step_ieee (s x : float * float) : float * float :=
  IeeeModel.add_2_2 prec emax nan_plus nan_minus (fst s) (snd s) (fst x) (snd x).

Lemma sum_2_step_ieee_dead :
  forall s e : float * float, lead2 (sum_2_step_ieee s e) -> lead2 s.
Proof. intros s e H. exact (proj1 (add22i_lead s e H)). Qed.

Lemma sum_2_step_ieee_live :
  (3 <= prec)%Z ->
  forall s e : float * float, good2 s -> can2 e -> lead2 (sum_2_step_ieee s e) ->
  good2 (sum_2_step_ieee s e) /\ good2 e /\
  vals2 (sum_2_step_ieee s e) = FoldModel.sum_2_step emin prec tie_even (vals2 s) (vals2 e).
Proof.
intros Hp.
exact (stored_step_live add22i (add_2_2 emin prec tie_even) add22i_lead (add22i_live Hp)).
Qed.

Definition sum_2_entry_step_ieee (s x : float * float) : float * float :=
  IeeeModel.sum_entry_step_2 prec emax nan_plus nan_minus (fst s) (snd s) (fst x) (snd x).

Lemma sum_2_entry_step_ieee_eq :
  forall s x : float * float, sum_2_entry_step_ieee s x = add22i s (guard2i x).
Proof.
intros s x. unfold sum_2_entry_step_ieee, IeeeModel.sum_entry_step_2, add22i, guard2i.
cbv zeta. cbn [fst snd]. apply pair_eta.
Qed.

Lemma sum_2_entry_step_ieee_dead :
  forall s e : float * float, lead2 (sum_2_entry_step_ieee s e) -> lead2 s.
Proof.
intros s e. rewrite sum_2_entry_step_ieee_eq. intros H. exact (proj1 (add22i_lead _ _ H)).
Qed.

Lemma sum_2_entry_step_ieee_live :
  (3 <= prec)%Z ->
  forall s e : float * float, good2 s -> can2 e -> lead2 (sum_2_entry_step_ieee s e) ->
  good2 (sum_2_entry_step_ieee s e) /\ good2 e /\
  vals2 (sum_2_entry_step_ieee s e) =
  FoldModel.sum_2_entry_step emin prec tie_even (vals2 s) (vals2 e).
Proof.
intros Hp s e Gs Ce. rewrite sum_2_entry_step_ieee_eq. intros L.
destruct (entry_step_live add22i (add_2_2 emin prec tie_even) add22i_lead (add22i_live Hp)
            s e Gs Ce L) as [G [Ge V]].
split. exact G. split. exact Ge. rewrite V. symmetry.
exact (sum_entry_step_2_real emin prec (val (fst s)) (val (snd s)) (val (fst e)) (val (snd e))
         (val_fmt (fst e)) (val_fmt (snd e))).
Qed.

(* sum_fast_2 and sum_fast_2_entry: add_fast_2_2. *)
Definition sum_fast_2_step_ieee (s x : float * float) : float * float :=
  IeeeModel.add_fast_2_2 prec emax nan_plus nan_minus (fst s) (snd s) (fst x) (snd x).

Lemma sum_fast_2_step_ieee_dead :
  forall s e : float * float, lead2 (sum_fast_2_step_ieee s e) -> lead2 s.
Proof. intros s e H. exact (proj1 (addfast22i_lead s e H)). Qed.

Lemma sum_fast_2_step_ieee_live :
  (2 <= prec)%Z ->
  forall s e : float * float, good2 s -> can2 e -> lead2 (sum_fast_2_step_ieee s e) ->
  good2 (sum_fast_2_step_ieee s e) /\ good2 e /\
  vals2 (sum_fast_2_step_ieee s e) =
  FoldModel.sum_fast_2_step emin prec tie_even (vals2 s) (vals2 e).
Proof.
intros Hp.
exact (stored_step_live addfast22i (add_fast_2_2 emin prec tie_even) addfast22i_lead
         (addfast22i_live Hp)).
Qed.

Definition sum_fast_2_entry_step_ieee (s x : float * float) : float * float :=
  IeeeModel.sum_fast_entry_step_2 prec emax nan_plus nan_minus (fst s) (snd s) (fst x) (snd x).

Lemma sum_fast_2_entry_step_ieee_eq :
  forall s x : float * float, sum_fast_2_entry_step_ieee s x = addfast22i s (guard2i x).
Proof.
intros s x.
unfold sum_fast_2_entry_step_ieee, IeeeModel.sum_fast_entry_step_2, addfast22i, guard2i.
cbv zeta. cbn [fst snd]. apply pair_eta.
Qed.

Lemma sum_fast_2_entry_step_ieee_dead :
  forall s e : float * float, lead2 (sum_fast_2_entry_step_ieee s e) -> lead2 s.
Proof.
intros s e. rewrite sum_fast_2_entry_step_ieee_eq. intros H.
exact (proj1 (addfast22i_lead _ _ H)).
Qed.

Lemma sum_fast_2_entry_step_ieee_live :
  (2 <= prec)%Z ->
  forall s e : float * float, good2 s -> can2 e -> lead2 (sum_fast_2_entry_step_ieee s e) ->
  good2 (sum_fast_2_entry_step_ieee s e) /\ good2 e /\
  vals2 (sum_fast_2_entry_step_ieee s e) =
  FoldModel.sum_fast_2_entry_step emin prec tie_even (vals2 s) (vals2 e).
Proof.
intros Hp s e Gs Ce. rewrite sum_fast_2_entry_step_ieee_eq. intros L.
destruct (entry_step_live addfast22i (add_fast_2_2 emin prec tie_even) addfast22i_lead
            (addfast22i_live Hp) s e Gs Ce L) as [G [Ge V]].
split. exact G. split. exact Ge. rewrite V. symmetry.
exact (sum_fast_entry_step_2_real emin prec (val (fst s)) (val (snd s)) (val (fst e))
         (val (snd e)) (val_fmt (fst e)) (val_fmt (snd e))).
Qed.

(* dot_2: mul_2_2 then add_2_2. An element is a pair of pairs. *)
Definition vals22 (xy : (float * float) * (float * float)) : (R * R) * (R * R) :=
  (vals2 (fst xy), vals2 (snd xy)).
Definition can22 (xy : (float * float) * (float * float)) : Prop :=
  can2 (fst xy) /\ can2 (snd xy).
Definition good22 (xy : (float * float) * (float * float)) : Prop :=
  good2 (fst xy) /\ good2 (snd xy).

Lemma good22_normalized :
  forall xs : list ((float * float) * (float * float)), Forall good22 xs ->
  Forall (fun xy => normalized_2 emin prec (fst (fst xy)) (snd (fst xy)) /\
                    normalized_2 emin prec (fst (snd xy)) (snd (snd xy))) (map vals22 xs).
Proof.
intros xs H. induction H as [|x r [[_ [_ Nx]] [_ [_ Ny]]] _ IH]; cbn [map]; constructor.
- split; [exact Nx | exact Ny].
- exact IH.
Qed.

Definition dot_2_step_ieee (s : float * float) (xy : (float * float) * (float * float))
  : float * float :=
  IeeeModel.dot_step_2 prec emax nan_plus nan_minus nan_opp nan_fma (fst s) (snd s)
    (fst (fst xy)) (snd (fst xy)) (fst (snd xy)) (snd (snd xy)).

Lemma dot_2_step_ieee_eq :
  forall (s : float * float) (xy : (float * float) * (float * float)),
  dot_2_step_ieee s xy = add22i s (mul22i (fst xy) (snd xy)).
Proof.
intros s xy. unfold dot_2_step_ieee, IeeeModel.dot_step_2, add22i, mul22i.
destruct (IeeeModel.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma (fst (fst xy))
            (snd (fst xy)) (fst (snd xy)) (snd (snd xy))) as [p0 p1].
cbn [fst snd]. apply pair_eta.
Qed.

Lemma dot_2_step_ieee_dead :
  forall (s : float * float) (xy : (float * float) * (float * float)),
  lead2 (dot_2_step_ieee s xy) -> lead2 s.
Proof.
intros s xy. rewrite dot_2_step_ieee_eq. intros H. exact (proj1 (add22i_lead _ _ H)).
Qed.

Lemma dot_2_step_ieee_live :
  (4 <= prec)%Z ->
  forall (s : float * float) (xy : (float * float) * (float * float)),
  good2 s -> can22 xy -> lead2 (dot_2_step_ieee s xy) ->
  good2 (dot_2_step_ieee s xy) /\ good22 xy /\
  vals2 (dot_2_step_ieee s xy) = FoldModel.dot_2_step emin prec tie_even (vals2 s) (vals22 xy).
Proof.
intros Hp s [x y] Gs [Cx Cy]. cbn [fst snd] in Cx, Cy.
assert (Hp3 : (3 <= prec)%Z) by lia.
rewrite dot_2_step_ieee_eq. cbn [fst snd]. intros L.
destruct (add22i_lead _ _ L) as [_ Lp].
destruct (mul22i_lead _ _ Lp) as [Lx Ly].
pose proof (can2_good x Cx Lx) as Gx. pose proof (can2_good y Cy Ly) as Gy.
destruct (mul22i_live Hp x y Gx Gy Lp) as [Gp Ep].
destruct (add22i_live Hp3 s (mul22i x y) Gs Gp L) as [Gt Et].
split. exact Gt. split. { split; assumption. }
rewrite Et. unfold vals2 in Ep.
unfold FoldModel.dot_2_step, dot_step_2, vals22, vals2. cbn [fst snd].
rewrite <- Ep. cbv beta iota. symmetry. apply pair_eta.
Qed.

(** * The folds of one limb, with their finish *)

(* sum_1. *)
Definition sum_1_step_ieee (s : float) (x : float) : float :=
  IeeeModel.add_1_1 prec emax nan_plus s x.

Definition sum_1_combine_ieee (a b : float) : float := IeeeModel.add_1_1 prec emax nan_plus a b.

Definition sum_1_seq_ieee (xs : list (float)) : float * bool :=
  finish1 (fold_seq sum_1_step_ieee pzero xs).

Definition sum_1_lanes_ieee (W : nat) (xs : list (float)) : float * bool :=
  finish1 (fold_lanes sum_1_step_ieee sum_1_combine_ieee pzero W xs).

Theorem sum_1_seq_ieee_correct :
  (1 <= prec)%Z ->
  forall xs : list (float),
  let '(r, flag) := sum_1_seq_ieee xs in
  (flag = true ->
   Forall finite xs /\ finite r /\
   (forall k : nat, finite (fold_seq sum_1_step_ieee pzero (firstn k xs))) /\
   let vs := map val xs in
   let s := FoldModel.sum_1_seq emin prec tie_even vs in
   val r = s /\
   fmt emin prec s /\
   Rabs (s - sumR (map (fun x => x) vs)) <=
     ((1 + u prec / (1 + u prec)) ^ (length vs - 1) - 1) * sumabs (map (fun x => x) vs)) /\
  (flag = false -> nan r).
Proof.
intros Hp xs. unfold sum_1_seq_ieee.
generalize (seq_1 _ _ sum_1_step_ieee (FoldModel.sum_1_step emin prec tie_even)
              (@val prec emax) (@finite prec emax) add_1_1_step_dead add_1_1_step_live xs).
destruct (finish1 (fold_seq sum_1_step_ieee pzero xs)) as [r flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [Fx [Fr [V St]]].
split. exact Fx. split. exact Fr. split. exact St.
cbv zeta. split. exact V.
exact (sum_1_seq_correct emin prec Hp (map val xs) (vals_fmt xs)).
Qed.

Theorem sum_1_lanes_ieee_correct :
  (1 <= prec)%Z ->
  forall (W : nat) (xs : list (float)),
  let '(r, flag) := sum_1_lanes_ieee W xs in
  (flag = true ->
   Forall finite xs /\ finite r /\
   let vs := map val xs in
   let s := FoldModel.sum_1_lanes emin prec tie_even W vs in
   val r = s /\
   fmt emin prec s /\
   Rabs (s - sumR (map (fun x => x) vs)) <=
     ((1 + u prec / (1 + u prec)) ^ (length vs - 1) - 1) * sumabs (map (fun x => x) vs)) /\
  (flag = false -> nan r).
Proof.
intros Hp W xs. unfold sum_1_lanes_ieee.
generalize (lanes_1 _ _ sum_1_step_ieee (FoldModel.sum_1_step emin prec tie_even)
              sum_1_combine_ieee (FoldModel.sum_1_combine emin prec tie_even)
              (@val prec emax) (@finite prec emax) add_1_1_step_dead add_1_1_step_live
              add_1_1_dead add_1_1_live W xs).
destruct (finish1 (fold_lanes sum_1_step_ieee sum_1_combine_ieee pzero W xs)) as [r flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [Fx [Fr V]].
split. exact Fx. split. exact Fr.
cbv zeta. split. exact V.
exact (sum_1_lanes_correct emin prec Hp W (map val xs) (vals_fmt xs)).
Qed.

(* sum_1_entry. *)
Definition sum_1_entry_step_ieee (s : float) (x : float) : float :=
  IeeeModel.sum_entry_step_1 prec emax nan_plus s x.

Definition sum_1_entry_combine_ieee (a b : float) : float := IeeeModel.add_1_1 prec emax nan_plus a b.

Definition sum_1_entry_seq_ieee (xs : list (float)) : float * bool :=
  finish1 (fold_seq sum_1_entry_step_ieee pzero xs).

Definition sum_1_entry_lanes_ieee (W : nat) (xs : list (float)) : float * bool :=
  finish1 (fold_lanes sum_1_entry_step_ieee sum_1_entry_combine_ieee pzero W xs).

Theorem sum_1_entry_seq_ieee_correct :
  (1 <= prec)%Z ->
  forall xs : list (float),
  let '(r, flag) := sum_1_entry_seq_ieee xs in
  (flag = true ->
   Forall finite xs /\ finite r /\
   (forall k : nat, finite (fold_seq sum_1_entry_step_ieee pzero (firstn k xs))) /\
   let vs := map val xs in
   let s := FoldModel.sum_1_entry_seq emin prec tie_even vs in
   val r = s /\
   fmt emin prec s /\
   Rabs (s - sumR (map (fun x => x) vs)) <=
     ((1 + u prec / (1 + u prec)) ^ (length vs - 1) - 1) * sumabs (map (fun x => x) vs)) /\
  (flag = false -> nan r).
Proof.
intros Hp xs. unfold sum_1_entry_seq_ieee.
generalize (seq_1 _ _ sum_1_entry_step_ieee (FoldModel.sum_1_entry_step emin prec tie_even)
              (@val prec emax) (@finite prec emax) sum_entry_step_1_step_dead sum_entry_step_1_step_live xs).
destruct (finish1 (fold_seq sum_1_entry_step_ieee pzero xs)) as [r flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [Fx [Fr [V St]]].
split. exact Fx. split. exact Fr. split. exact St.
cbv zeta. split. exact V.
exact (sum_1_entry_seq_correct emin prec Hp (map val xs) (vals_fmt xs)).
Qed.

Theorem sum_1_entry_lanes_ieee_correct :
  (1 <= prec)%Z ->
  forall (W : nat) (xs : list (float)),
  let '(r, flag) := sum_1_entry_lanes_ieee W xs in
  (flag = true ->
   Forall finite xs /\ finite r /\
   let vs := map val xs in
   let s := FoldModel.sum_1_entry_lanes emin prec tie_even W vs in
   val r = s /\
   fmt emin prec s /\
   Rabs (s - sumR (map (fun x => x) vs)) <=
     ((1 + u prec / (1 + u prec)) ^ (length vs - 1) - 1) * sumabs (map (fun x => x) vs)) /\
  (flag = false -> nan r).
Proof.
intros Hp W xs. unfold sum_1_entry_lanes_ieee.
generalize (lanes_1 _ _ sum_1_entry_step_ieee (FoldModel.sum_1_entry_step emin prec tie_even)
              sum_1_entry_combine_ieee (FoldModel.sum_1_entry_combine emin prec tie_even)
              (@val prec emax) (@finite prec emax) sum_entry_step_1_step_dead sum_entry_step_1_step_live
              add_1_1_dead add_1_1_live W xs).
destruct (finish1 (fold_lanes sum_1_entry_step_ieee sum_1_entry_combine_ieee pzero W xs)) as [r flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [Fx [Fr V]].
split. exact Fx. split. exact Fr.
cbv zeta. split. exact V.
exact (sum_1_entry_lanes_correct emin prec Hp W (map val xs) (vals_fmt xs)).
Qed.

(* dot_1. *)
Definition dot_1_step_ieee (s : float) (xy : float * float) : float :=
  IeeeModel.dot_step_1 prec emax nan_fma s (fst xy) (snd xy).

Definition dot_1_combine_ieee (a b : float) : float := IeeeModel.add_1_1 prec emax nan_plus a b.

Definition dot_1_seq_ieee (xs : list (float * float)) : float * bool :=
  finish1 (fold_seq dot_1_step_ieee pzero xs).

Definition dot_1_lanes_ieee (W : nat) (xs : list (float * float)) : float * bool :=
  finish1 (fold_lanes dot_1_step_ieee dot_1_combine_ieee pzero W xs).

Theorem dot_1_seq_ieee_correct :
  (1 <= prec)%Z ->
  forall xs : list (float * float),
  let '(r, flag) := dot_1_seq_ieee xs in
  (flag = true ->
   Forall fin11 xs /\ finite r /\
   (forall k : nat, finite (fold_seq dot_1_step_ieee pzero (firstn k xs))) /\
   let vs := map vals11 xs in
   let s := FoldModel.dot_1_seq emin prec tie_even vs in
   val r = s /\
   fmt emin prec s /\
   Rabs (s - sumR (map (fun xy => fst xy * snd xy) vs)) <=
     ((1 + u prec / (1 + u prec)) ^ length vs - 1) * sumabs (map (fun xy => fst xy * snd xy) vs) +
     (1 + u prec / (1 + u prec)) ^ (length vs - 1) * (INR (length vs) * (eta emin / 2))) /\
  (flag = false -> nan r).
Proof.
intros Hp xs. unfold dot_1_seq_ieee.
generalize (seq_1 _ _ dot_1_step_ieee (FoldModel.dot_1_step emin prec tie_even)
              vals11 fin11 dot_step_1_step_dead dot_step_1_step_live xs).
destruct (finish1 (fold_seq dot_1_step_ieee pzero xs)) as [r flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [Fx [Fr [V St]]].
split. exact Fx. split. exact Fr. split. exact St.
cbv zeta. split. exact V.
exact (dot_1_seq_correct emin prec Hp (map vals11 xs) (vals11_fmt xs)).
Qed.

Theorem dot_1_lanes_ieee_correct :
  (1 <= prec)%Z ->
  forall (W : nat) (xs : list (float * float)),
  let '(r, flag) := dot_1_lanes_ieee W xs in
  (flag = true ->
   Forall fin11 xs /\ finite r /\
   let vs := map vals11 xs in
   let s := FoldModel.dot_1_lanes emin prec tie_even W vs in
   val r = s /\
   fmt emin prec s /\
   Rabs (s - sumR (map (fun xy => fst xy * snd xy) vs)) <=
     ((1 + u prec / (1 + u prec)) ^ length vs - 1) * sumabs (map (fun xy => fst xy * snd xy) vs) +
     (1 + u prec / (1 + u prec)) ^ (length vs - 1) * (INR (length vs) * (eta emin / 2))) /\
  (flag = false -> nan r).
Proof.
intros Hp W xs. unfold dot_1_lanes_ieee.
generalize (lanes_1 _ _ dot_1_step_ieee (FoldModel.dot_1_step emin prec tie_even)
              dot_1_combine_ieee (FoldModel.dot_1_combine emin prec tie_even)
              vals11 fin11 dot_step_1_step_dead dot_step_1_step_live
              add_1_1_dead add_1_1_live W xs).
destruct (finish1 (fold_lanes dot_1_step_ieee dot_1_combine_ieee pzero W xs)) as [r flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [Fx [Fr V]].
split. exact Fx. split. exact Fr.
cbv zeta. split. exact V.
exact (dot_1_lanes_correct emin prec Hp W (map vals11 xs) (vals11_fmt xs)).
Qed.

(** * The folds of two limbs, with their finish *)

(* sum_2. *)
Definition sum_2_seq_ieee (xs : list (float * float)) : float * float * bool :=
  finish2 (fold_seq sum_2_step_ieee zero2 xs).

Definition sum_2_combine_ieee (a b : float * float) : float * float :=
  IeeeModel.add_2_2 prec emax nan_plus nan_minus (fst a) (snd a) (fst b) (snd b).

Definition sum_2_lanes_ieee (W : nat) (xs : list (float * float)) : float * float * bool :=
  finish2 (fold_lanes sum_2_step_ieee sum_2_combine_ieee zero2 W xs).

Theorem sum_2_seq_ieee_correct :
  (3 <= prec)%Z ->
  forall xs : list (float * float), Forall can2 xs ->
  let '(r0, r1, flag) := sum_2_seq_ieee xs in
  (flag = true ->
   Forall good2 xs /\ finite r0 /\ finite r1 /\
   (forall k : nat, good2 (fold_seq sum_2_step_ieee zero2 (firstn k xs))) /\
   let vs := map vals2 xs in
   let s := FoldModel.sum_2_seq emin prec tie_even vs in
   (val r0, val r1) = s /\
   normalized_2 emin prec (fst s) (snd s) /\
   Rabs ((fst s + snd s) - sumR (map (fun x => fst x + snd x) vs)) <=
     ((1 + 3 * u prec ^ 2 / (1 - 4 * u prec)) ^ (length vs - 1) - 1) *
     sumabs (map (fun x => fst x + snd x) vs)) /\
  (flag = false -> nan r0 /\ nan r1).
Proof.
intros Hp xs Hx. unfold sum_2_seq_ieee.
generalize (seq_2 _ _ sum_2_step_ieee (FoldModel.sum_2_step emin prec tie_even)
              vals2 can2 good2
              sum_2_step_ieee_dead (sum_2_step_ieee_live Hp) xs Hx).
destruct (finish2 (fold_seq sum_2_step_ieee zero2 xs)) as [[r0 r1] flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [Fx [[F0 [F1 _]] [V St]]]. cbn [fst snd] in F0, F1.
split. exact Fx. split. exact F0. split. exact F1. split. exact St.
cbv zeta. split. exact V.
exact (sum_2_seq_correct emin prec Hp (map vals2 xs) (good2_normalized xs Fx)).
Qed.

Theorem sum_2_lanes_ieee_correct :
  (3 <= prec)%Z ->
  forall (W : nat) (xs : list (float * float)), Forall can2 xs ->
  let '(r0, r1, flag) := sum_2_lanes_ieee W xs in
  (flag = true ->
   Forall good2 xs /\ finite r0 /\ finite r1 /\
   let vs := map vals2 xs in
   let s := FoldModel.sum_2_lanes emin prec tie_even W vs in
   (val r0, val r1) = s /\
   normalized_2 emin prec (fst s) (snd s) /\
   Rabs ((fst s + snd s) - sumR (map (fun x => fst x + snd x) vs)) <=
     ((1 + 3 * u prec ^ 2 / (1 - 4 * u prec)) ^ (length vs - 1) - 1) *
     sumabs (map (fun x => fst x + snd x) vs)) /\
  (flag = false -> nan r0 /\ nan r1).
Proof.
intros Hp W xs Hx. unfold sum_2_lanes_ieee.
generalize (lanes_2 _ _ sum_2_step_ieee (FoldModel.sum_2_step emin prec tie_even)
              sum_2_combine_ieee (FoldModel.sum_2_combine emin prec tie_even)
              vals2 can2 good2
              sum_2_step_ieee_dead (sum_2_step_ieee_live Hp) add22i_lead (add22i_live Hp) W xs Hx).
destruct (finish2 (fold_lanes sum_2_step_ieee sum_2_combine_ieee zero2 W xs)) as [[r0 r1] flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [Fx [[F0 [F1 _]] V]]. cbn [fst snd] in F0, F1.
split. exact Fx. split. exact F0. split. exact F1.
cbv zeta. split. exact V.
exact (sum_2_lanes_correct emin prec Hp W (map vals2 xs) (good2_normalized xs Fx)).
Qed.

(* sum_2_entry. *)
Definition sum_2_entry_seq_ieee (xs : list (float * float)) : float * float * bool :=
  finish2 (fold_seq sum_2_entry_step_ieee zero2 xs).

Definition sum_2_entry_combine_ieee (a b : float * float) : float * float :=
  IeeeModel.add_2_2 prec emax nan_plus nan_minus (fst a) (snd a) (fst b) (snd b).

Definition sum_2_entry_lanes_ieee (W : nat) (xs : list (float * float)) : float * float * bool :=
  finish2 (fold_lanes sum_2_entry_step_ieee sum_2_entry_combine_ieee zero2 W xs).

Theorem sum_2_entry_seq_ieee_correct :
  (3 <= prec)%Z ->
  forall xs : list (float * float), Forall can2 xs ->
  let '(r0, r1, flag) := sum_2_entry_seq_ieee xs in
  (flag = true ->
   Forall good2 xs /\ finite r0 /\ finite r1 /\
   (forall k : nat, good2 (fold_seq sum_2_entry_step_ieee zero2 (firstn k xs))) /\
   let vs := map vals2 xs in
   let s := FoldModel.sum_2_entry_seq emin prec tie_even vs in
   (val r0, val r1) = s /\
   normalized_2 emin prec (fst s) (snd s) /\
   Rabs ((fst s + snd s) - sumR (map (fun x => fst x + snd x) vs)) <=
     ((1 + 3 * u prec ^ 2 / (1 - 4 * u prec)) ^ (length vs - 1) - 1) *
     sumabs (map (fun x => fst x + snd x) vs)) /\
  (flag = false -> nan r0 /\ nan r1).
Proof.
intros Hp xs Hx. unfold sum_2_entry_seq_ieee.
generalize (seq_2 _ _ sum_2_entry_step_ieee (FoldModel.sum_2_entry_step emin prec tie_even)
              vals2 can2 good2
              sum_2_entry_step_ieee_dead (sum_2_entry_step_ieee_live Hp) xs Hx).
destruct (finish2 (fold_seq sum_2_entry_step_ieee zero2 xs)) as [[r0 r1] flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [Fx [[F0 [F1 _]] [V St]]]. cbn [fst snd] in F0, F1.
split. exact Fx. split. exact F0. split. exact F1. split. exact St.
cbv zeta. split. exact V.
exact (sum_2_entry_seq_correct emin prec Hp (map vals2 xs) (good2_normalized xs Fx)).
Qed.

Theorem sum_2_entry_lanes_ieee_correct :
  (3 <= prec)%Z ->
  forall (W : nat) (xs : list (float * float)), Forall can2 xs ->
  let '(r0, r1, flag) := sum_2_entry_lanes_ieee W xs in
  (flag = true ->
   Forall good2 xs /\ finite r0 /\ finite r1 /\
   let vs := map vals2 xs in
   let s := FoldModel.sum_2_entry_lanes emin prec tie_even W vs in
   (val r0, val r1) = s /\
   normalized_2 emin prec (fst s) (snd s) /\
   Rabs ((fst s + snd s) - sumR (map (fun x => fst x + snd x) vs)) <=
     ((1 + 3 * u prec ^ 2 / (1 - 4 * u prec)) ^ (length vs - 1) - 1) *
     sumabs (map (fun x => fst x + snd x) vs)) /\
  (flag = false -> nan r0 /\ nan r1).
Proof.
intros Hp W xs Hx. unfold sum_2_entry_lanes_ieee.
generalize (lanes_2 _ _ sum_2_entry_step_ieee (FoldModel.sum_2_entry_step emin prec tie_even)
              sum_2_entry_combine_ieee (FoldModel.sum_2_entry_combine emin prec tie_even)
              vals2 can2 good2
              sum_2_entry_step_ieee_dead (sum_2_entry_step_ieee_live Hp) add22i_lead (add22i_live Hp) W xs Hx).
destruct (finish2 (fold_lanes sum_2_entry_step_ieee sum_2_entry_combine_ieee zero2 W xs)) as [[r0 r1] flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [Fx [[F0 [F1 _]] V]]. cbn [fst snd] in F0, F1.
split. exact Fx. split. exact F0. split. exact F1.
cbv zeta. split. exact V.
exact (sum_2_entry_lanes_correct emin prec Hp W (map vals2 xs) (good2_normalized xs Fx)).
Qed.

(* sum_fast_2. *)
Definition sum_fast_2_seq_ieee (xs : list (float * float)) : float * float * bool :=
  finish2 (fold_seq sum_fast_2_step_ieee zero2 xs).

Definition sum_fast_2_combine_ieee (a b : float * float) : float * float :=
  IeeeModel.add_fast_2_2 prec emax nan_plus nan_minus (fst a) (snd a) (fst b) (snd b).

Definition sum_fast_2_lanes_ieee (W : nat) (xs : list (float * float)) : float * float * bool :=
  finish2 (fold_lanes sum_fast_2_step_ieee sum_fast_2_combine_ieee zero2 W xs).

Theorem sum_fast_2_seq_ieee_correct :
  (2 <= prec)%Z ->
  forall xs : list (float * float), Forall can2 xs ->
  let '(r0, r1, flag) := sum_fast_2_seq_ieee xs in
  (flag = true ->
   Forall good2 xs /\ finite r0 /\ finite r1 /\
   (forall k : nat, good2 (fold_seq sum_fast_2_step_ieee zero2 (firstn k xs))) /\
   let vs := map vals2 xs in
   let s := FoldModel.sum_fast_2_seq emin prec tie_even vs in
   (val r0, val r1) = s /\
   normalized_2 emin prec (fst s) (snd s) /\
   Rabs ((fst s + snd s) - sumR (map (fun x => fst x + snd x) vs)) <=
     ((1 + 3 * u prec ^ 2) ^ (length vs - 1) - 1) *
     sumabs (map (fun x => fst x + snd x) vs)) /\
  (flag = false -> nan r0 /\ nan r1).
Proof.
intros Hp xs Hx. unfold sum_fast_2_seq_ieee.
generalize (seq_2 _ _ sum_fast_2_step_ieee (FoldModel.sum_fast_2_step emin prec tie_even)
              vals2 can2 good2
              sum_fast_2_step_ieee_dead (sum_fast_2_step_ieee_live Hp) xs Hx).
destruct (finish2 (fold_seq sum_fast_2_step_ieee zero2 xs)) as [[r0 r1] flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [Fx [[F0 [F1 _]] [V St]]]. cbn [fst snd] in F0, F1.
split. exact Fx. split. exact F0. split. exact F1. split. exact St.
cbv zeta. split. exact V.
exact (sum_fast_2_seq_correct emin prec Hp (map vals2 xs) (good2_normalized xs Fx)).
Qed.

Theorem sum_fast_2_lanes_ieee_correct :
  (2 <= prec)%Z ->
  forall (W : nat) (xs : list (float * float)), Forall can2 xs ->
  let '(r0, r1, flag) := sum_fast_2_lanes_ieee W xs in
  (flag = true ->
   Forall good2 xs /\ finite r0 /\ finite r1 /\
   let vs := map vals2 xs in
   let s := FoldModel.sum_fast_2_lanes emin prec tie_even W vs in
   (val r0, val r1) = s /\
   normalized_2 emin prec (fst s) (snd s) /\
   Rabs ((fst s + snd s) - sumR (map (fun x => fst x + snd x) vs)) <=
     ((1 + 3 * u prec ^ 2) ^ (length vs - 1) - 1) *
     sumabs (map (fun x => fst x + snd x) vs)) /\
  (flag = false -> nan r0 /\ nan r1).
Proof.
intros Hp W xs Hx. unfold sum_fast_2_lanes_ieee.
generalize (lanes_2 _ _ sum_fast_2_step_ieee (FoldModel.sum_fast_2_step emin prec tie_even)
              sum_fast_2_combine_ieee (FoldModel.sum_fast_2_combine emin prec tie_even)
              vals2 can2 good2
              sum_fast_2_step_ieee_dead (sum_fast_2_step_ieee_live Hp) addfast22i_lead (addfast22i_live Hp) W xs Hx).
destruct (finish2 (fold_lanes sum_fast_2_step_ieee sum_fast_2_combine_ieee zero2 W xs)) as [[r0 r1] flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [Fx [[F0 [F1 _]] V]]. cbn [fst snd] in F0, F1.
split. exact Fx. split. exact F0. split. exact F1.
cbv zeta. split. exact V.
exact (sum_fast_2_lanes_correct emin prec Hp W (map vals2 xs) (good2_normalized xs Fx)).
Qed.

(* sum_fast_2_entry. *)
Definition sum_fast_2_entry_seq_ieee (xs : list (float * float)) : float * float * bool :=
  finish2 (fold_seq sum_fast_2_entry_step_ieee zero2 xs).

Definition sum_fast_2_entry_combine_ieee (a b : float * float) : float * float :=
  IeeeModel.add_fast_2_2 prec emax nan_plus nan_minus (fst a) (snd a) (fst b) (snd b).

Definition sum_fast_2_entry_lanes_ieee (W : nat) (xs : list (float * float)) : float * float * bool :=
  finish2 (fold_lanes sum_fast_2_entry_step_ieee sum_fast_2_entry_combine_ieee zero2 W xs).

Theorem sum_fast_2_entry_seq_ieee_correct :
  (2 <= prec)%Z ->
  forall xs : list (float * float), Forall can2 xs ->
  let '(r0, r1, flag) := sum_fast_2_entry_seq_ieee xs in
  (flag = true ->
   Forall good2 xs /\ finite r0 /\ finite r1 /\
   (forall k : nat, good2 (fold_seq sum_fast_2_entry_step_ieee zero2 (firstn k xs))) /\
   let vs := map vals2 xs in
   let s := FoldModel.sum_fast_2_entry_seq emin prec tie_even vs in
   (val r0, val r1) = s /\
   normalized_2 emin prec (fst s) (snd s) /\
   Rabs ((fst s + snd s) - sumR (map (fun x => fst x + snd x) vs)) <=
     ((1 + 3 * u prec ^ 2) ^ (length vs - 1) - 1) *
     sumabs (map (fun x => fst x + snd x) vs)) /\
  (flag = false -> nan r0 /\ nan r1).
Proof.
intros Hp xs Hx. unfold sum_fast_2_entry_seq_ieee.
generalize (seq_2 _ _ sum_fast_2_entry_step_ieee (FoldModel.sum_fast_2_entry_step emin prec tie_even)
              vals2 can2 good2
              sum_fast_2_entry_step_ieee_dead (sum_fast_2_entry_step_ieee_live Hp) xs Hx).
destruct (finish2 (fold_seq sum_fast_2_entry_step_ieee zero2 xs)) as [[r0 r1] flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [Fx [[F0 [F1 _]] [V St]]]. cbn [fst snd] in F0, F1.
split. exact Fx. split. exact F0. split. exact F1. split. exact St.
cbv zeta. split. exact V.
exact (sum_fast_2_entry_seq_correct emin prec Hp (map vals2 xs) (good2_normalized xs Fx)).
Qed.

Theorem sum_fast_2_entry_lanes_ieee_correct :
  (2 <= prec)%Z ->
  forall (W : nat) (xs : list (float * float)), Forall can2 xs ->
  let '(r0, r1, flag) := sum_fast_2_entry_lanes_ieee W xs in
  (flag = true ->
   Forall good2 xs /\ finite r0 /\ finite r1 /\
   let vs := map vals2 xs in
   let s := FoldModel.sum_fast_2_entry_lanes emin prec tie_even W vs in
   (val r0, val r1) = s /\
   normalized_2 emin prec (fst s) (snd s) /\
   Rabs ((fst s + snd s) - sumR (map (fun x => fst x + snd x) vs)) <=
     ((1 + 3 * u prec ^ 2) ^ (length vs - 1) - 1) *
     sumabs (map (fun x => fst x + snd x) vs)) /\
  (flag = false -> nan r0 /\ nan r1).
Proof.
intros Hp W xs Hx. unfold sum_fast_2_entry_lanes_ieee.
generalize (lanes_2 _ _ sum_fast_2_entry_step_ieee (FoldModel.sum_fast_2_entry_step emin prec tie_even)
              sum_fast_2_entry_combine_ieee (FoldModel.sum_fast_2_entry_combine emin prec tie_even)
              vals2 can2 good2
              sum_fast_2_entry_step_ieee_dead (sum_fast_2_entry_step_ieee_live Hp) addfast22i_lead (addfast22i_live Hp) W xs Hx).
destruct (finish2 (fold_lanes sum_fast_2_entry_step_ieee sum_fast_2_entry_combine_ieee zero2 W xs)) as [[r0 r1] flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [Fx [[F0 [F1 _]] V]]. cbn [fst snd] in F0, F1.
split. exact Fx. split. exact F0. split. exact F1.
cbv zeta. split. exact V.
exact (sum_fast_2_entry_lanes_correct emin prec Hp W (map vals2 xs) (good2_normalized xs Fx)).
Qed.

(* dot_2. *)
Definition dot_2_seq_ieee (xs : list ((float * float) * (float * float))) : float * float * bool :=
  finish2 (fold_seq dot_2_step_ieee zero2 xs).

Definition dot_2_combine_ieee (a b : float * float) : float * float :=
  IeeeModel.add_2_2 prec emax nan_plus nan_minus (fst a) (snd a) (fst b) (snd b).

Definition dot_2_lanes_ieee (W : nat) (xs : list ((float * float) * (float * float))) : float * float * bool :=
  finish2 (fold_lanes dot_2_step_ieee dot_2_combine_ieee zero2 W xs).

Theorem dot_2_seq_ieee_correct :
  (4 <= prec)%Z ->
  forall xs : list ((float * float) * (float * float)), Forall can22 xs ->
  let '(r0, r1, flag) := dot_2_seq_ieee xs in
  (flag = true ->
   Forall good22 xs /\ finite r0 /\ finite r1 /\
   (forall k : nat, good2 (fold_seq dot_2_step_ieee zero2 (firstn k xs))) /\
   let vs := map vals22 xs in
   let s := FoldModel.dot_2_seq emin prec tie_even vs in
   (val r0, val r1) = s /\
   normalized_2 emin prec (fst s) (snd s) /\
   Rabs ((fst s + snd s) -
         sumR (map (fun xy => (fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy)))
                 vs)) <=
     ((1 + 4 * u prec ^ 2) * (1 + 3 * u prec ^ 2 / (1 - 4 * u prec)) ^ (length vs - 1) - 1) *
     sumabs (map (fun xy => (fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy)))
               vs) +
     (1 + 3 * u prec ^ 2 / (1 - 4 * u prec)) ^ (length vs - 1) *
     (INR (length vs) * (3 / 2 * eta emin))) /\
  (flag = false -> nan r0 /\ nan r1).
Proof.
intros Hp xs Hx. unfold dot_2_seq_ieee.
generalize (seq_2 _ _ dot_2_step_ieee (FoldModel.dot_2_step emin prec tie_even)
              vals22 can22 good22
              dot_2_step_ieee_dead (dot_2_step_ieee_live Hp) xs Hx).
destruct (finish2 (fold_seq dot_2_step_ieee zero2 xs)) as [[r0 r1] flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [Fx [[F0 [F1 _]] [V St]]]. cbn [fst snd] in F0, F1.
split. exact Fx. split. exact F0. split. exact F1. split. exact St.
cbv zeta. split. exact V.
exact (dot_2_seq_correct emin prec Hp (map vals22 xs) (good22_normalized xs Fx)).
Qed.

Theorem dot_2_lanes_ieee_correct :
  (4 <= prec)%Z ->
  forall (W : nat) (xs : list ((float * float) * (float * float))), Forall can22 xs ->
  let '(r0, r1, flag) := dot_2_lanes_ieee W xs in
  (flag = true ->
   Forall good22 xs /\ finite r0 /\ finite r1 /\
   let vs := map vals22 xs in
   let s := FoldModel.dot_2_lanes emin prec tie_even W vs in
   (val r0, val r1) = s /\
   normalized_2 emin prec (fst s) (snd s) /\
   Rabs ((fst s + snd s) -
         sumR (map (fun xy => (fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy)))
                 vs)) <=
     ((1 + 4 * u prec ^ 2) * (1 + 3 * u prec ^ 2 / (1 - 4 * u prec)) ^ (length vs - 1) - 1) *
     sumabs (map (fun xy => (fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy)))
               vs) +
     (1 + 3 * u prec ^ 2 / (1 - 4 * u prec)) ^ (length vs - 1) *
     (INR (length vs) * (3 / 2 * eta emin))) /\
  (flag = false -> nan r0 /\ nan r1).
Proof.
intros Hp W xs Hx. unfold dot_2_lanes_ieee.
assert (Hp3 : (3 <= prec)%Z) by lia.
generalize (lanes_2 _ _ dot_2_step_ieee (FoldModel.dot_2_step emin prec tie_even)
              dot_2_combine_ieee (FoldModel.dot_2_combine emin prec tie_even)
              vals22 can22 good22
              dot_2_step_ieee_dead (dot_2_step_ieee_live Hp) add22i_lead (add22i_live Hp3) W xs Hx).
destruct (finish2 (fold_lanes dot_2_step_ieee dot_2_combine_ieee zero2 W xs)) as [[r0 r1] flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [Fx [[F0 [F1 _]] V]]. cbn [fst snd] in F0, F1.
split. exact Fx. split. exact F0. split. exact F1.
cbv zeta. split. exact V.
exact (dot_2_lanes_correct emin prec Hp W (map vals22 xs) (good22_normalized xs Fx)).
Qed.

End IeeeFolds.
