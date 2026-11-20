(* A fold in two models: from the model with overflow to the model without.

   A fold has a model over the real numbers, in which nothing overflows, and the bounds of
   Summation.v are about that model. The same loop over floating-point numbers, where an
   operation may overflow and an operand may be an infinity or a NaN, is another function
   of the same shape, fold_seq or fold_lanes of another step. This file relates the two,
   for any two steps that are related as the kernels of Kairn are, and contains no
   floating-point number: like Folds.v it is about lists only.

   Setting. The second model has states of a type A and elements of a type B, the first
   states of A' and elements of B'; va and vb take a state and an element of the second
   model to their values in the first. Of a state of the second model two things are
   said:
       live s    the state is finite (for Kairn: its leading limb is finite);
       good s    what a finite state satisfies (every limb finite, the pair normalized).
   and of an element two things:
       elt e     what is assumed of every element (for two limbs, that it is canonical);
       fin e     what a finite result shows of it (it is finite, and valid).

   Hypotheses on the step, each a fact about one application of a kernel:
       step_dead   live (step s e) -> live s
                   a state that is not finite stays not finite;
       step_live   good s -> elt e -> live (step s e) ->
                   good (step s e) /\ fin e /\ va (step s e) = step' (va s) (vb e)
                   from a good state, a finite result means a finite element, a good
                   result, and the value that the first model computes.
   And the same two on the combination of the lane order: combine_dead, for both
   operands, and combine_live.

   What is proved. From a good zero state and elements that satisfy elt, if the result of
   the fold is live, then
   - it is good, every element satisfies fin, and its value is the fold of the first
     model on the values of the elements: fold_seq_transfer, fold_lanes_transfer, the
     second for every number of lanes;
   - in the sequential order every state the loop went through is good, and is the state
     of the first model at that point: fold_seq_transfer_prefix.
   The contrapositive is the statement of the flag of a fold: an element that is not
   finite, or an overflow anywhere, leaves a final state that is not live.

   Why the hypotheses have this form. step_dead is the non-finite cone of the kernels:
   the leading limb of the state reaches the leading limb of the next state through
   operations that keep a NaN and an infinity not finite. It is asked of the state only:
   that an element which is not finite gives a result which is not finite is part of
   step_live, where the element is known to be canonical. step_live is the bridge of
   Milestone 1 for one kernel, which needs finite operands; the induction supplies them,
   going backward from the final state with step_dead and then forward with step_live. *)
From Stdlib Require Import List Arith Lia Permutation.
From Kairn Require Import Folds.
Import ListNotations.

(* A property of every element of the image of a list, read on the list. *)
Lemma Forall_map_inv :
  forall (C D : Type) (f : C -> D) (P : D -> Prop) (l : list C),
  Forall P (map f l) -> Forall (fun x => P (f x)) l.
Proof.
intros C D f P. induction l as [|x r IH]; cbn [map]; intros H.
- constructor.
- constructor. exact (Forall_inv H). apply IH. exact (Forall_inv_tail H).
Qed.

Section Transfer.
Variables A B A' B' : Type.
Variable step : A -> B -> A.
Variable step' : A' -> B' -> A'.
Variable va : A -> A'.
Variable vb : B -> B'.
Variable live good : A -> Prop.
Variable elt fin : B -> Prop.

Hypothesis step_dead : forall (s : A) (e : B), live (step s e) -> live s.
Hypothesis step_live :
  forall (s : A) (e : B), good s -> elt e -> live (step s e) ->
  good (step s e) /\ fin e /\ va (step s e) = step' (va s) (vb e).

(** * The sequential order *)

(* A live state at the end: the state the elements were folded into was live. *)
Lemma fold_left_dead :
  forall (xs : list B) (s : A), live (fold_left step xs s) -> live s.
Proof.
induction xs as [|x r IH]; intros s H; cbn [fold_left] in H.
- exact H.
- apply step_dead with x. now apply IH.
Qed.

Lemma fold_left_transfer :
  forall (xs : list B) (s : A), good s -> Forall elt xs -> live (fold_left step xs s) ->
  good (fold_left step xs s) /\ Forall fin xs /\
  va (fold_left step xs s) = fold_left step' (map vb xs) (va s).
Proof.
induction xs as [|x r IH]; intros s Gs Hx Hl; cbn [fold_left map] in *.
- split. exact Gs. split. constructor. reflexivity.
- pose proof (fold_left_dead r (step s x) Hl) as L1.
  destruct (step_live s x Gs (Forall_inv Hx) L1) as [G1 [F1 E1]].
  destruct (IH (step s x) G1 (Forall_inv_tail Hx) Hl) as [G2 [F2 E2]].
  split. exact G2. split. constructor; assumption.
  rewrite E2, E1. reflexivity.
Qed.

(* The sequential order: a live result is good, every element is finite, and the value is
   the fold of the first model. *)
Theorem fold_seq_transfer :
  forall (zero : A) (xs : list B), good zero -> Forall elt xs ->
  live (fold_seq step zero xs) ->
  good (fold_seq step zero xs) /\ Forall fin xs /\
  va (fold_seq step zero xs) = fold_seq step' (va zero) (map vb xs).
Proof. intros zero xs Gz Hx Hl. unfold fold_seq in *. now apply fold_left_transfer. Qed.

(* Every state the sequential loop went through: the state after the first k elements is
   good, and is the state of the first model after its first k elements. *)
Theorem fold_seq_transfer_prefix :
  forall (zero : A) (xs : list B) (k : nat), good zero -> Forall elt xs ->
  live (fold_seq step zero xs) ->
  good (fold_seq step zero (firstn k xs)) /\
  va (fold_seq step zero (firstn k xs)) = fold_seq step' (va zero) (map vb (firstn k xs)).
Proof.
intros zero xs k Gz Hx Hl.
rewrite <- (firstn_skipn k xs) in Hx, Hl.
apply Forall_app in Hx. destruct Hx as [Hp _].
unfold fold_seq in Hl. rewrite fold_left_app in Hl.
pose proof (fold_left_dead _ _ Hl) as L.
destruct (fold_seq_transfer zero (firstn k xs) Gz Hp L) as [G [_ E]].
split; assumption.
Qed.

(** * The lane order *)

Variable combine : A -> A -> A.
Variable combine' : A' -> A' -> A'.

Hypothesis combine_dead : forall a b : A, live (combine a b) -> live a /\ live b.
Hypothesis combine_live :
  forall a b : A, good a -> good b -> live (combine a b) ->
  good (combine a b) /\ va (combine a b) = combine' (va a) (va b).

(* A live combination: every state combined was live. *)
Lemma combine_all_live :
  forall (ss : list A) (s0 : A), live (fold_left combine ss s0) -> live s0 /\ Forall live ss.
Proof.
induction ss as [|s r IH]; intros s0 H; cbn [fold_left] in H.
- split. exact H. constructor.
- destruct (IH _ H) as [H1 H2]. destruct (combine_dead _ _ H1) as [L0 L1].
  split. exact L0. constructor; assumption.
Qed.

Lemma combine_transfer :
  forall (ss : list A) (s0 : A), good s0 -> Forall good ss ->
  live (fold_left combine ss s0) ->
  good (fold_left combine ss s0) /\
  va (fold_left combine ss s0) = fold_left combine' (map va ss) (va s0).
Proof.
induction ss as [|s r IH]; intros s0 G0 Gs H; cbn [fold_left map] in *.
- split. exact G0. reflexivity.
- destruct (combine_all_live r _ H) as [L _].
  destruct (combine_live s0 s G0 (Forall_inv Gs) L) as [G1 E1].
  destruct (IH _ G1 (Forall_inv_tail Gs) H) as [G2 E2].
  split. exact G2. rewrite E2, E1. reflexivity.
Qed.

Lemma combine_lanes_live :
  forall (zero : A) (ss : list A), live (combine_lanes combine zero ss) -> Forall live ss.
Proof.
intros zero [|s0 r] H; unfold combine_lanes in H; cbn [hd tl] in H.
- constructor.
- destruct (combine_all_live r s0 H) as [L0 Lr]. constructor; assumption.
Qed.

Lemma combine_lanes_transfer :
  forall (zero : A) (ss : list A), good zero -> Forall good ss ->
  live (combine_lanes combine zero ss) ->
  good (combine_lanes combine zero ss) /\
  va (combine_lanes combine zero ss) = combine_lanes combine' (va zero) (map va ss).
Proof.
intros zero [|s0 r] Gz Gs H; unfold combine_lanes in *; cbn [hd tl map] in *.
- split. exact Gz. reflexivity.
- exact (combine_transfer r s0 (Forall_inv Gs) (Forall_inv_tail Gs) H).
Qed.

(* Every lane, folded on its own from the zero state. *)
Lemma lanes_transfer :
  forall (zero : A) (ls : list (list B)), good zero -> Forall (Forall elt) ls ->
  Forall (fun l => live (fold_seq step zero l)) ls ->
  Forall (fun l => good (fold_seq step zero l)) ls /\ Forall (Forall fin) ls /\
  map va (map (fold_seq step zero) ls) = map (fold_seq step' (va zero)) (map (map vb) ls).
Proof.
intros zero ls Gz. induction ls as [|l r IH]; intros He Hl; cbn [map].
- split. constructor. split. constructor. reflexivity.
- destruct (fold_seq_transfer zero l Gz (Forall_inv He) (Forall_inv Hl)) as [G [F E]].
  destruct (IH (Forall_inv_tail He) (Forall_inv_tail Hl)) as [Gr [Fr Er]].
  split. constructor; assumption. split. constructor; assumption.
  rewrite E, Er. reflexivity.
Qed.

Lemma Forall_permutation :
  forall (C : Type) (P : C -> Prop) (l1 l2 : list C),
  Permutation l1 l2 -> Forall P l1 -> Forall P l2.
Proof.
intros C P l1 l2 Hp H. apply Forall_forall. intros x Hx.
apply (proj1 (Forall_forall P l1) H).
apply Permutation_in with (1 := Permutation_sym Hp). exact Hx.
Qed.

(* The lane order, for every number of lanes: a live result is good, every element is
   finite, and the value is the lane order of the first model with the same lanes. *)
Theorem fold_lanes_transfer :
  forall (zero : A) (W : nat) (xs : list B), good zero -> Forall elt xs ->
  live (fold_lanes step combine zero W xs) ->
  good (fold_lanes step combine zero W xs) /\ Forall fin xs /\
  va (fold_lanes step combine zero W xs) = fold_lanes step' combine' (va zero) W (map vb xs).
Proof.
intros zero W xs Gz Hx Hl.
unfold fold_lanes in Hl |- *.
rewrite length_map, firstn_map, skipn_map, deal_map.
set (b := (W * (length xs / W))%nat) in *.
assert (Hsplit : Forall elt (firstn b xs) /\ Forall elt (skipn b xs)).
{ apply Forall_app. now rewrite firstn_skipn. }
destruct Hsplit as [Hpre Hrest].
assert (Hls : Forall (Forall elt) (deal W (firstn b xs))).
{ unfold deal. apply Forall_map. apply Forall_forall. intros j _. now apply lane_Forall. }
pose proof (fold_left_dead _ _ Hl) as Lc.
pose proof (Forall_map_inv _ _ _ _ _ (combine_lanes_live zero _ Lc)) as Ls.
destruct (lanes_transfer zero _ Gz Hls Ls) as [Gls [Fls Els]].
assert (Gss : Forall good (map (fold_seq step zero) (deal W (firstn b xs))))
  by (apply Forall_map; exact Gls).
destruct (combine_lanes_transfer zero _ Gz Gss Lc) as [Gc Ec].
destruct (fold_left_transfer _ _ Gc Hrest Hl) as [Gf [Frest Ef]].
assert (Fpre : Forall fin (firstn b xs)).
{ destruct (Nat.eq_dec W 0) as [W0|W0].
  - replace (firstn b xs) with (@nil B). constructor.
    unfold b. rewrite W0. reflexivity.
  - apply Forall_permutation with (concat (deal W (firstn b xs))).
    + apply deal_perm. lia.
    + apply Forall_concat. exact Fls. }
split. exact Gf. split.
- rewrite <- (firstn_skipn b xs). apply Forall_app. split; assumption.
- rewrite Ef, Ec, Els. reflexivity.
Qed.

End Transfer.
