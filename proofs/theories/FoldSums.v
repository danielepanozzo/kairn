(* The folds of the sums and dot products: the generated statements, in both orders.

   proofs/gen/FoldModel.v states every fold F as fold_seq F_step zero xs and
   fold_lanes F_step F_combine zero W xs, with a step and a combination written from the
   models of their kernels, limb by limb. SummationKernels.v proves the bounds of the two
   orders for the steps add_1_1, add22, addfast22, dot_step_2 and dot_step_1 that it
   defines. This file connects the two: for every fold of proofs/gen/FoldStatements.v it
   shows that the generated step and combination are the ones those theorems name, and
   concludes the generated statement,

       F_seq_correct : F_seq_spec        F_lanes_correct : F_lanes_spec,

   the second for every number of lanes W.

   How each fold is connected.
   - sum_1, sum_2, sum_fast_2: the generated step is the addition itself (add_1_1,
     add_2_2, add_fast_2_2 applied to the limbs), so the statement is fold_seq_sum or
     fold_lanes_sum of Summation.v with the instances add_1_1_adds and add_1_1_zero,
     add_2_2_adds and add_2_2_zero, add_fast_2_2_adds and add_fast_2_2_zero. These are
     the theorems in the form with the power (1 + eps)^(n-1) - 1, which the generated
     statements use; sum_1_seq, sum_2_lanes and the others of SummationKernels.v are
     their corollaries in the form with gamma, under a hypothesis on n that the
     generated statements do not have.
   - sum_1_entry, sum_2_entry, sum_fast_2_entry: the step passes each limb of the
     element through the guard, RN (x + 0), before the addition. So the fold is the
     fold of the addition over the list of the guarded elements (fold_seq_map,
     fold_lanes_map), and that list is the list itself when every limb is a number of
     the format (guard_real_any): fold_seq_guarded and fold_lanes_guarded below.
   - dot_2: the generated step, mul_2_2 then add_2_2 on limbs, is dot_step_2 of
     SummationKernels.v on every state and element (dot_2_step_eq, a case analysis on
     the two pairs that the kernels return); then dot_2_seq and dot_2_lanes of that
     file, by fold_seq_ext and fold_lanes_ext.
   - dot_1: the generated step, RN (x y + s), is dot_step_1 of SummationKernels.v by
     definition; then dot_1_seq and dot_1_lanes of that file. The generated statement
     assumes that the elements are numbers of the format; the theorem does not use it.
   - dot_1_entry: the step guards both numbers of the element first, so the fold is that
     of dot_step_1 over the list of the guarded pairs, which is the list itself when they
     are numbers of the format (guard2_map_fmt); then as dot_1. Here the hypothesis on
     the elements is used.

   Names. SummationKernels.v was written before the generator had folds, and three of
   its names are now also names of generated definitions: dot_step_1 and dot_step_2
   (kernels of proofs/gen/Model.v) and sum_1_seq and the like (definitions of
   proofs/gen/FoldModel.v, theorems there). This file writes every such name with its
   module. *)
From Stdlib Require Import Reals ZArith List Lia Lra.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements FoldModel FoldStatements.
From Kairn Require Import Format Guard Folds Summation SummationKernels.
Import ListNotations.
Open Scope R_scope.

(** * A step that guards its element *)

(* If the step is op after a function g of the element, and g changes no element of the
   list, the fold of the step is the fold of op. *)
Lemma fold_seq_guarded :
  forall (A B : Type) (step op : A -> B -> A) (g : B -> B) (zero : A) (xs : list B),
  (forall (s : A) (e : B), step s e = op s (g e)) -> map g xs = xs ->
  fold_seq step zero xs = fold_seq op zero xs.
Proof.
intros A B step op g zero xs H Hg.
rewrite (fold_seq_ext A B step (fun s e => op s (g e)) zero H xs).
rewrite (fold_seq_map A B B op g zero xs). now rewrite Hg.
Qed.

Lemma fold_lanes_guarded :
  forall (A B : Type) (step op : A -> B -> A) (combine combine' : A -> A -> A) (g : B -> B)
         (zero : A) (W : nat) (xs : list B),
  (forall (s : A) (e : B), step s e = op s (g e)) ->
  (forall a b : A, combine a b = combine' a b) -> map g xs = xs ->
  fold_lanes step combine zero W xs = fold_lanes op combine' zero W xs.
Proof.
intros A B step op combine combine' g zero W xs H Hc Hg.
rewrite (fold_lanes_ext A B step (fun s e => op s (g e)) combine combine' zero H Hc W xs).
rewrite (fold_lanes_map A B B op combine' g zero W xs). now rewrite Hg.
Qed.

(* The guard of one limb and of the two limbs of a pair, as the generated steps apply it. *)
Definition guard1 (emin prec : Z) (x : R) : R := RN emin prec (x + 0).

Definition guard2 (emin prec : Z) (x : R * R) : R * R :=
  (RN emin prec (fst x + 0), RN emin prec (snd x + 0)).

(* It changes no number of the format, hence no list of them. *)
Lemma guard1_map :
  forall (emin prec : Z) (xs : list R),
  Forall (fmt emin prec) xs -> map (guard1 emin prec) xs = xs.
Proof.
intros emin prec xs H. induction H as [|x r Fx _ IH]; cbn [map].
- reflexivity.
- rewrite IH. unfold guard1, RN.
  now rewrite (guard_real_any emin prec tie_even x Fx).
Qed.

Lemma guard2_map :
  forall (emin prec : Z) (xs : list (R * R)),
  Forall (norm2 emin prec) xs -> map (guard2 emin prec) xs = xs.
Proof.
intros emin prec xs H. induction H as [|[x0 x1] r Nx _ IH]; cbn [map].
- reflexivity.
- destruct Nx as [F0 [F1 _]]. cbn [fst snd] in F0, F1.
  rewrite IH. unfold guard2, RN. cbn [fst snd].
  now rewrite (guard_real_any emin prec tie_even x0 F0), (guard_real_any emin prec tie_even x1 F1).
Qed.

(* The same of the pairs of an element of a dot product, each number of the format. *)
Lemma guard2_map_fmt :
  forall (emin prec : Z) (xs : list (R * R)),
  Forall (fun xy => fmt emin prec (fst xy) /\ fmt emin prec (snd xy)) xs ->
  map (guard2 emin prec) xs = xs.
Proof.
intros emin prec xs H. induction H as [|[x y] r [Fx Fy] _ IH]; cbn [map].
- reflexivity.
- cbn [fst snd] in Fx, Fy. rewrite IH. unfold guard2, RN. cbn [fst snd].
  now rewrite (guard_real_any emin prec tie_even x Fx), (guard_real_any emin prec tie_even y Fy).
Qed.

(** * The generated steps *)

(* sum_1_entry: the addition of the guarded element. *)
Lemma sum_1_entry_step_eq :
  forall (emin prec : Z) (s x : R),
  FoldModel.sum_1_entry_step emin prec tie_even s x =
  add_1_1 emin prec tie_even s (guard1 emin prec x).
Proof. reflexivity. Qed.

(* sum_2_entry and sum_fast_2_entry: the same on pairs. *)
Lemma sum_2_entry_step_eq :
  forall (emin prec : Z) (s x : R * R),
  FoldModel.sum_2_entry_step emin prec tie_even s x = add22 emin prec s (guard2 emin prec x).
Proof.
intros emin prec s x.
unfold FoldModel.sum_2_entry_step, Model.sum_entry_step_2, add22, guard2, RN.
cbv zeta. cbn [fst snd].
destruct (add_2_2 emin prec tie_even (fst s) (snd s) _ _) as [t0 t1]. reflexivity.
Qed.

Lemma sum_fast_2_entry_step_eq :
  forall (emin prec : Z) (s x : R * R),
  FoldModel.sum_fast_2_entry_step emin prec tie_even s x =
  addfast22 emin prec s (guard2 emin prec x).
Proof.
intros emin prec s x.
unfold FoldModel.sum_fast_2_entry_step, Model.sum_fast_entry_step_2, addfast22, guard2, RN.
cbv zeta. cbn [fst snd].
destruct (add_fast_2_2 emin prec tie_even (fst s) (snd s) _ _) as [t0 t1]. reflexivity.
Qed.

(* dot_1_entry: the fused step of SummationKernels.v on the guarded pair. *)
Lemma dot_1_entry_step_eq :
  forall (emin prec : Z) (s : R) (xy : R * R),
  FoldModel.dot_1_entry_step emin prec tie_even s xy =
  SummationKernels.dot_step_1 emin prec s (guard2 emin prec xy).
Proof. reflexivity. Qed.

(* dot_2: the step of SummationKernels.v, add22 of mul22. *)
Lemma dot_2_step_eq :
  forall (emin prec : Z) (s : R * R) (xy : (R * R) * (R * R)),
  FoldModel.dot_2_step emin prec tie_even s xy = SummationKernels.dot_step_2 emin prec s xy.
Proof.
intros emin prec s xy.
unfold FoldModel.dot_2_step, Model.dot_step_2, SummationKernels.dot_step_2, add22, mul22.
destruct (mul_2_2 emin prec tie_even (fst (fst xy)) (snd (fst xy)) (fst (snd xy)) (snd (snd xy)))
  as [p0 p1].
cbn [fst snd].
destruct (add_2_2 emin prec tie_even (fst s) (snd s) p0 p1) as [t0 t1]. reflexivity.
Qed.

(** * The folds are those of SummationKernels.v *)

Lemma sum_1_entry_seq_eq :
  forall (emin prec : Z) (xs : list R), Forall (fmt emin prec) xs ->
  FoldModel.sum_1_entry_seq emin prec tie_even xs = fold_seq (add_1_1 emin prec tie_even) 0 xs.
Proof.
intros emin prec xs Hv. unfold FoldModel.sum_1_entry_seq.
apply fold_seq_guarded with (g := guard1 emin prec).
- exact (sum_1_entry_step_eq emin prec).
- now apply guard1_map.
Qed.

Lemma sum_1_entry_lanes_eq :
  forall (emin prec : Z) (W : nat) (xs : list R), Forall (fmt emin prec) xs ->
  FoldModel.sum_1_entry_lanes emin prec tie_even W xs =
  fold_lanes (add_1_1 emin prec tie_even) (add_1_1 emin prec tie_even) 0 W xs.
Proof.
intros emin prec W xs Hv. unfold FoldModel.sum_1_entry_lanes.
apply fold_lanes_guarded with (g := guard1 emin prec).
- exact (sum_1_entry_step_eq emin prec).
- reflexivity.
- now apply guard1_map.
Qed.

Lemma sum_2_entry_seq_eq :
  forall (emin prec : Z) (xs : list (R * R)), Forall (norm2 emin prec) xs ->
  FoldModel.sum_2_entry_seq emin prec tie_even xs = fold_seq (add22 emin prec) (0, 0) xs.
Proof.
intros emin prec xs Hv. unfold FoldModel.sum_2_entry_seq.
apply fold_seq_guarded with (g := guard2 emin prec).
- exact (sum_2_entry_step_eq emin prec).
- now apply guard2_map.
Qed.

Lemma sum_2_entry_lanes_eq :
  forall (emin prec : Z) (W : nat) (xs : list (R * R)), Forall (norm2 emin prec) xs ->
  FoldModel.sum_2_entry_lanes emin prec tie_even W xs =
  fold_lanes (add22 emin prec) (add22 emin prec) (0, 0) W xs.
Proof.
intros emin prec W xs Hv. unfold FoldModel.sum_2_entry_lanes.
apply fold_lanes_guarded with (g := guard2 emin prec).
- exact (sum_2_entry_step_eq emin prec).
- reflexivity.
- now apply guard2_map.
Qed.

Lemma sum_fast_2_entry_seq_eq :
  forall (emin prec : Z) (xs : list (R * R)), Forall (norm2 emin prec) xs ->
  FoldModel.sum_fast_2_entry_seq emin prec tie_even xs = fold_seq (addfast22 emin prec) (0, 0) xs.
Proof.
intros emin prec xs Hv. unfold FoldModel.sum_fast_2_entry_seq.
apply fold_seq_guarded with (g := guard2 emin prec).
- exact (sum_fast_2_entry_step_eq emin prec).
- now apply guard2_map.
Qed.

Lemma sum_fast_2_entry_lanes_eq :
  forall (emin prec : Z) (W : nat) (xs : list (R * R)), Forall (norm2 emin prec) xs ->
  FoldModel.sum_fast_2_entry_lanes emin prec tie_even W xs =
  fold_lanes (addfast22 emin prec) (addfast22 emin prec) (0, 0) W xs.
Proof.
intros emin prec W xs Hv. unfold FoldModel.sum_fast_2_entry_lanes.
apply fold_lanes_guarded with (g := guard2 emin prec).
- exact (sum_fast_2_entry_step_eq emin prec).
- reflexivity.
- now apply guard2_map.
Qed.

Lemma dot_2_seq_eq :
  forall (emin prec : Z) (xys : list ((R * R) * (R * R))),
  FoldModel.dot_2_seq emin prec tie_even xys =
  fold_seq (SummationKernels.dot_step_2 emin prec) (0, 0) xys.
Proof.
intros emin prec xys. unfold FoldModel.dot_2_seq.
apply fold_seq_ext. exact (dot_2_step_eq emin prec).
Qed.

Lemma dot_2_lanes_eq :
  forall (emin prec : Z) (W : nat) (xys : list ((R * R) * (R * R))),
  FoldModel.dot_2_lanes emin prec tie_even W xys =
  fold_lanes (SummationKernels.dot_step_2 emin prec) (add22 emin prec) (0, 0) W xys.
Proof.
intros emin prec W xys. unfold FoldModel.dot_2_lanes.
apply fold_lanes_ext.
- exact (dot_2_step_eq emin prec).
- reflexivity.
Qed.

Lemma dot_1_entry_seq_eq :
  forall (emin prec : Z) (xys : list (R * R)),
  Forall (fun xy => fmt emin prec (fst xy) /\ fmt emin prec (snd xy)) xys ->
  FoldModel.dot_1_entry_seq emin prec tie_even xys =
  fold_seq (SummationKernels.dot_step_1 emin prec) 0 xys.
Proof.
intros emin prec xys Hv. unfold FoldModel.dot_1_entry_seq.
apply fold_seq_guarded with (g := guard2 emin prec).
- exact (dot_1_entry_step_eq emin prec).
- now apply guard2_map_fmt.
Qed.

Lemma dot_1_entry_lanes_eq :
  forall (emin prec : Z) (W : nat) (xys : list (R * R)),
  Forall (fun xy => fmt emin prec (fst xy) /\ fmt emin prec (snd xy)) xys ->
  FoldModel.dot_1_entry_lanes emin prec tie_even W xys =
  fold_lanes (SummationKernels.dot_step_1 emin prec) (add_1_1 emin prec tie_even) 0 W xys.
Proof.
intros emin prec W xys Hv. unfold FoldModel.dot_1_entry_lanes.
apply fold_lanes_guarded with (g := guard2 emin prec).
- exact (dot_1_entry_step_eq emin prec).
- reflexivity.
- now apply guard2_map_fmt.
Qed.

(** * One limb: the sums *)

(* sum_1: the generated step is add_1_1. *)
Theorem sum_1_seq_correct : sum_1_seq_spec.
Proof.
intros emin prec Hp xs Hv s. unfold s. clear s.
pose proof (fold_seq_sum _ _ _ _ _ _ (eps_1_ge_0 prec) (add_1_1_adds emin prec Hp)
              (add_1_1_zero emin prec Hp) xs Hv) as H.
cbv zeta in H. destruct H as [Fs [Es _]].
split. exact Fs. exact Es.
Qed.

Theorem sum_1_lanes_correct : sum_1_lanes_spec.
Proof.
intros emin prec Hp W xs Hv s. unfold s. clear s.
pose proof (fold_lanes_sum _ _ _ _ _ _ (eps_1_ge_0 prec) (add_1_1_adds emin prec Hp)
              (add_1_1_zero emin prec Hp) W xs Hv) as H.
cbv zeta in H. destruct H as [Fs [Es _]].
split. exact Fs. exact Es.
Qed.

(* sum_1_entry: the same sum, the guard changing no element. *)
Theorem sum_1_entry_seq_correct : sum_1_entry_seq_spec.
Proof.
intros emin prec Hp xs Hv s. unfold s. clear s.
rewrite (sum_1_entry_seq_eq emin prec xs Hv).
pose proof (fold_seq_sum _ _ _ _ _ _ (eps_1_ge_0 prec) (add_1_1_adds emin prec Hp)
              (add_1_1_zero emin prec Hp) xs Hv) as H.
cbv zeta in H. destruct H as [Fs [Es _]].
split. exact Fs. exact Es.
Qed.

Theorem sum_1_entry_lanes_correct : sum_1_entry_lanes_spec.
Proof.
intros emin prec Hp W xs Hv s. unfold s. clear s.
rewrite (sum_1_entry_lanes_eq emin prec W xs Hv).
pose proof (fold_lanes_sum _ _ _ _ _ _ (eps_1_ge_0 prec) (add_1_1_adds emin prec Hp)
              (add_1_1_zero emin prec Hp) W xs Hv) as H.
cbv zeta in H. destruct H as [Fs [Es _]].
split. exact Fs. exact Es.
Qed.

(** * Two limbs: the sums with add_2_2 *)

Theorem sum_2_seq_correct : sum_2_seq_spec.
Proof.
intros emin prec Hp xs Hv s. unfold s. clear s.
assert (Hp1 : (1 <= prec)%Z) by lia.
pose proof (fold_seq_sum _ _ _ _ _ _ (eps_add_2_ge_0 prec Hp) (add_2_2_adds emin prec Hp)
              (add_2_2_zero emin prec Hp1) xs Hv) as H.
cbv zeta in H. destruct H as [Ns [Es _]].
split. exact Ns. exact Es.
Qed.

Theorem sum_2_lanes_correct : sum_2_lanes_spec.
Proof.
intros emin prec Hp W xs Hv s. unfold s. clear s.
assert (Hp1 : (1 <= prec)%Z) by lia.
pose proof (fold_lanes_sum _ _ _ _ _ _ (eps_add_2_ge_0 prec Hp) (add_2_2_adds emin prec Hp)
              (add_2_2_zero emin prec Hp1) W xs Hv) as H.
cbv zeta in H. destruct H as [Ns [Es _]].
split. exact Ns. exact Es.
Qed.

Theorem sum_2_entry_seq_correct : sum_2_entry_seq_spec.
Proof.
intros emin prec Hp xs Hv s. unfold s. clear s.
assert (Hp1 : (1 <= prec)%Z) by lia.
rewrite (sum_2_entry_seq_eq emin prec xs Hv).
pose proof (fold_seq_sum _ _ _ _ _ _ (eps_add_2_ge_0 prec Hp) (add_2_2_adds emin prec Hp)
              (add_2_2_zero emin prec Hp1) xs Hv) as H.
cbv zeta in H. destruct H as [Ns [Es _]].
split. exact Ns. exact Es.
Qed.

Theorem sum_2_entry_lanes_correct : sum_2_entry_lanes_spec.
Proof.
intros emin prec Hp W xs Hv s. unfold s. clear s.
assert (Hp1 : (1 <= prec)%Z) by lia.
rewrite (sum_2_entry_lanes_eq emin prec W xs Hv).
pose proof (fold_lanes_sum _ _ _ _ _ _ (eps_add_2_ge_0 prec Hp) (add_2_2_adds emin prec Hp)
              (add_2_2_zero emin prec Hp1) W xs Hv) as H.
cbv zeta in H. destruct H as [Ns [Es _]].
split. exact Ns. exact Es.
Qed.

(** * Two limbs: the sums with add_fast_2_2 *)

Theorem sum_fast_2_seq_correct : sum_fast_2_seq_spec.
Proof.
intros emin prec Hp xs Hv s. unfold s. clear s.
assert (Hp1 : (1 <= prec)%Z) by lia.
assert (H3 : 0 <= 3) by lra.
pose proof (fold_seq_sum _ _ _ _ _ _ (eps_square_ge_0 3 prec H3) (add_fast_2_2_adds emin prec Hp)
              (add_fast_2_2_zero emin prec Hp1) xs Hv) as H.
cbv zeta in H. destruct H as [Ns [Es _]].
split. exact Ns. exact Es.
Qed.

Theorem sum_fast_2_lanes_correct : sum_fast_2_lanes_spec.
Proof.
intros emin prec Hp W xs Hv s. unfold s. clear s.
assert (Hp1 : (1 <= prec)%Z) by lia.
assert (H3 : 0 <= 3) by lra.
pose proof (fold_lanes_sum _ _ _ _ _ _ (eps_square_ge_0 3 prec H3) (add_fast_2_2_adds emin prec Hp)
              (add_fast_2_2_zero emin prec Hp1) W xs Hv) as H.
cbv zeta in H. destruct H as [Ns [Es _]].
split. exact Ns. exact Es.
Qed.

Theorem sum_fast_2_entry_seq_correct : sum_fast_2_entry_seq_spec.
Proof.
intros emin prec Hp xs Hv s. unfold s. clear s.
assert (Hp1 : (1 <= prec)%Z) by lia.
assert (H3 : 0 <= 3) by lra.
rewrite (sum_fast_2_entry_seq_eq emin prec xs Hv).
pose proof (fold_seq_sum _ _ _ _ _ _ (eps_square_ge_0 3 prec H3) (add_fast_2_2_adds emin prec Hp)
              (add_fast_2_2_zero emin prec Hp1) xs Hv) as H.
cbv zeta in H. destruct H as [Ns [Es _]].
split. exact Ns. exact Es.
Qed.

Theorem sum_fast_2_entry_lanes_correct : sum_fast_2_entry_lanes_spec.
Proof.
intros emin prec Hp W xs Hv s. unfold s. clear s.
assert (Hp1 : (1 <= prec)%Z) by lia.
assert (H3 : 0 <= 3) by lra.
rewrite (sum_fast_2_entry_lanes_eq emin prec W xs Hv).
pose proof (fold_lanes_sum _ _ _ _ _ _ (eps_square_ge_0 3 prec H3) (add_fast_2_2_adds emin prec Hp)
              (add_fast_2_2_zero emin prec Hp1) W xs Hv) as H.
cbv zeta in H. destruct H as [Ns [Es _]].
split. exact Ns. exact Es.
Qed.

(** * The dot products *)

(* dot_2: mul_2_2 then add_2_2. *)
Theorem dot_2_seq_correct : dot_2_seq_spec.
Proof.
intros emin prec Hp xys Hv s. unfold s. clear s.
rewrite (dot_2_seq_eq emin prec xys).
exact (SummationKernels.dot_2_seq emin prec Hp xys Hv).
Qed.

Theorem dot_2_lanes_correct : dot_2_lanes_spec.
Proof.
intros emin prec Hp W xys Hv s. unfold s. clear s.
rewrite (dot_2_lanes_eq emin prec W xys).
exact (SummationKernels.dot_2_lanes emin prec Hp W xys Hv).
Qed.

(* dot_1: the fused step. Nothing is used of the elements. *)
Theorem dot_1_seq_correct : dot_1_seq_spec.
Proof.
intros emin prec Hp xys _ s. unfold s. clear s.
exact (SummationKernels.dot_1_seq emin prec Hp xys).
Qed.

Theorem dot_1_lanes_correct : dot_1_lanes_spec.
Proof.
intros emin prec Hp W xys _ s. unfold s. clear s.
exact (SummationKernels.dot_1_lanes emin prec Hp W xys).
Qed.

(* dot_1_entry: the same fold, the guards changing no element of the format. *)
Theorem dot_1_entry_seq_correct : dot_1_entry_seq_spec.
Proof.
intros emin prec Hp xys Hv s. unfold s. clear s.
rewrite (dot_1_entry_seq_eq emin prec xys Hv).
exact (SummationKernels.dot_1_seq emin prec Hp xys).
Qed.

Theorem dot_1_entry_lanes_correct : dot_1_entry_lanes_spec.
Proof.
intros emin prec Hp W xys Hv s. unfold s. clear s.
rewrite (dot_1_entry_lanes_eq emin prec W xys Hv).
exact (SummationKernels.dot_1_lanes emin prec Hp W xys).
Qed.
