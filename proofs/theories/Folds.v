(* The two orders in which a batch kernel goes through an array, as functions on lists.

   A loop over arrays is described by a state, a step that takes the state and one
   element to the next state, and the state it starts from; a loop that keeps several
   partial results also has a combination of two states. This file defines the two
   orders in which Kairn emits such a loop:
   - fold_seq step zero xs, the sequential order;
   - fold_lanes step combine zero W xs, the order of a loop with W partial results, one
     per lane of a SIMD register, combined at the end.

   The file contains no real number and imports nothing of Kairn, so that a generated
   model of a loop can be stated with these two functions. What is proved here is about
   lists only: what the lanes of a list are, and how the two orders behave when the step
   is replaced by an equal one, when it is op after a function of the element, and with
   no lane, one lane, or fewer elements than lanes. The error bounds of sums and dot
   products in these orders are in Summation.v.

   A loop that writes an array (a map) is the last section: its model is map f xs, and
   the lemmas there relate that list to the list read entry by entry (Forall2), which is
   the form of a map's generated statement; and they show that the mask such a loop
   keeps, the and of a test of every element written, is the same in both orders. *)
From Stdlib Require Import List Arith Lia Permutation Bool.
Import ListNotations.

(** * The lanes of a list *)

Section Lanes.
Variable B : Type.

(* lane W j xs is the list of the elements of xs at the positions j, j + W, j + 2 W, ...
   (positions from 0): skip k elements, take one, and go on with k = W - 1. Element i of
   xs is thus in lane (i mod W), at position i / W. *)
Fixpoint lane (W k : nat) (xs : list B) : list B :=
  match xs with
  | [] => []
  | x :: r =>
      match k with
      | O => x :: lane W (W - 1) r
      | S k' => lane W k' r
      end
  end.

(* The W lanes of xs, lane 0 first. *)
Definition deal (W : nat) (xs : list B) : list (list B) :=
  map (fun j => lane W j xs) (seq 0 W).

(* What the definition means: element k of lane j is element j + k W of the list. *)
Lemma lane_nth :
  forall W : nat, (0 < W)%nat ->
  forall (xs : list B) (j k : nat) (d : B),
  nth k (lane W j xs) d = nth (j + k * W) xs d.
Proof.
intros W HW. induction xs as [|x r IH]; intros j k d.
- cbn [lane]. rewrite !nth_overflow by (cbn [length]; lia). reflexivity.
- destruct j as [|j]; cbn [lane].
  + destruct k as [|k].
    * reflexivity.
    * cbn [nth]. rewrite IH.
      replace (0 + S k * W)%nat with (S (W - 1 + k * W)) by lia.
      reflexivity.
  + rewrite IH. reflexivity.
Qed.

Lemma lane_length :
  forall W : nat, (0 < W)%nat ->
  forall (xs : list B) (j : nat), (j < W)%nat ->
  length (lane W j xs) = ((length xs + (W - 1 - j)) / W)%nat.
Proof.
intros W HW. induction xs as [|x r IH]; intros j Hj.
- cbn [lane length]. symmetry. apply Nat.div_small. lia.
- destruct j as [|j]; cbn [lane length].
  + rewrite IH by lia.
    replace (length r + (W - 1 - (W - 1)))%nat with (length r) by lia.
    replace (S (length r) + (W - 1 - 0))%nat with (length r + 1 * W)%nat by lia.
    rewrite Nat.div_add by lia. lia.
  + rewrite IH by lia.
    replace (S (length r) + (W - 1 - S j))%nat with (length r + (W - 1 - j))%nat by lia.
    reflexivity.
Qed.

(* A list of W q elements has W lanes of q elements. *)
Lemma lane_length_full :
  forall (W q : nat) (xs : list B) (j : nat),
  (j < W)%nat -> length xs = (W * q)%nat -> length (lane W j xs) = q.
Proof.
intros W q xs j Hj Hx.
rewrite lane_length by lia. rewrite Hx.
replace (W * q + (W - 1 - j))%nat with (q * W + (W - 1 - j))%nat by lia.
rewrite Nat.div_add_l by lia. rewrite Nat.div_small by lia. lia.
Qed.

Lemma lane_Forall :
  forall (P : B -> Prop) (W : nat) (xs : list B) (j : nat),
  Forall P xs -> Forall P (lane W j xs).
Proof.
intros P W. induction xs as [|x r IH]; intros j H.
- cbn [lane]. constructor.
- destruct j as [|j]; cbn [lane].
  + constructor. exact (Forall_inv H). apply IH. exact (Forall_inv_tail H).
  + apply IH. exact (Forall_inv_tail H).
Qed.

Lemma lane_1 : forall xs : list B, lane 1 0 xs = xs.
Proof.
induction xs as [|x r IH]; cbn [lane].
- reflexivity.
- change (1 - 1)%nat with 0%nat. now rewrite IH.
Qed.

Lemma deal_length : forall (W : nat) (xs : list B), length (deal W xs) = W.
Proof. intros W xs. unfold deal. now rewrite length_map, length_seq. Qed.

Lemma deal_nil : forall W : nat, concat (deal W []) = [].
Proof.
intros W. unfold deal. induction (seq 0 W) as [|j l IH]; cbn [map concat lane app].
- reflexivity.
- exact IH.
Qed.

Lemma deal_cons :
  forall (w : nat) (x : B) (r : list B),
  deal (S w) (x :: r) =
  (x :: lane (S w) w r) :: map (fun j => lane (S w) j r) (seq 0 w).
Proof.
intros w x r. unfold deal.
change (seq 0 (S w)) with (0%nat :: seq 1 w).
rewrite <- seq_shift. cbn [map]. rewrite map_map.
assert (E : lane (S w) 0 (x :: r) = x :: lane (S w) w r).
{ cbn [lane]. replace (S w - 1)%nat with w by lia. reflexivity. }
rewrite E. reflexivity.
Qed.

Lemma deal_last :
  forall (w : nat) (r : list B),
  deal (S w) r = map (fun j => lane (S w) j r) (seq 0 w) ++ [lane (S w) w r].
Proof. intros w r. unfold deal. rewrite seq_S, map_app. reflexivity. Qed.

(* The lanes hold every element of the list once. *)
Lemma deal_perm :
  forall (W : nat) (xs : list B), (0 < W)%nat -> Permutation (concat (deal W xs)) xs.
Proof.
intros W xs HW. destruct W as [|w]. lia. clear HW.
induction xs as [|x r IH].
- rewrite deal_nil. constructor.
- rewrite deal_cons. rewrite deal_last, concat_app in IH.
  cbn [concat] in IH |- *. rewrite app_nil_r in IH. cbn [app].
  apply perm_skip.
  apply Permutation_trans with (2 := IH). apply Permutation_app_comm.
Qed.

(* Lanes that all start with the same element: that element W times, and the lanes. *)
Lemma concat_cons_perm :
  forall (z : B) (ls : list (list B)),
  Permutation (concat (map (cons z) ls)) (repeat z (length ls) ++ concat ls).
Proof.
intros z. induction ls as [|l ls IH]; cbn [map concat length repeat app].
- constructor.
- apply perm_skip.
  apply Permutation_trans with (l ++ repeat z (length ls) ++ concat ls).
  + apply Permutation_app_head. exact IH.
  + apply Permutation_app_swap_app.
Qed.

End Lanes.

Arguments lane {B} W k xs.
Arguments deal {B} W xs.

Lemma lane_map :
  forall (B C : Type) (f : B -> C) (W : nat) (xs : list B) (j : nat),
  lane W j (map f xs) = map f (lane W j xs).
Proof.
intros B C f W. induction xs as [|x r IH]; intros j.
- reflexivity.
- destruct j as [|j]; cbn [map lane].
  + now rewrite IH.
  + apply IH.
Qed.

Lemma deal_map :
  forall (B C : Type) (f : B -> C) (W : nat) (xs : list B),
  deal W (map f xs) = map (map f) (deal W xs).
Proof.
intros B C f W xs. unfold deal. rewrite map_map. apply map_ext. intros j. apply lane_map.
Qed.

(** * The two orders *)

(* The state of a loop has a type A and an element a type B: an element is one entry of
   every array that the loop reads, a tuple of limbs, and nothing is assumed of it.

   Why this form. Both orders are written with fold_left, firstn, skipn and deal, each a
   structural recursion on a list, and one division of the length. So they compute: on a
   list written out, Compute shows the additions in their order, which is how the
   definition was compared with the description of the lane order; and a generated model
   only has to apply them to the model of its step. The lanes are lists of their own,
   each folded like the sequential order, because that is what the bounds use: a lane is
   a sequential sum. A definition closer to the emitted code, one vector of W states
   stepped block by block, would compute the same value and hide this. *)
Section Folds.
Variables A B : Type.
Variable step : A -> B -> A.
Variable combine : A -> A -> A.
Variable zero : A.

(* The sequential order: the state after element i is the step applied to the state
   after element i - 1, from the state zero. *)
Definition fold_seq (xs : list B) : A := fold_left step xs zero.

(* The states of the lanes into one, from lane 0 upward: ((s0 + s1) + s2) + ... *)
Definition combine_lanes (states : list A) : A :=
  fold_left combine (tl states) (hd zero states).

(* The lane order, for a width W. With n the length of xs: the first W (n / W) elements
   are dealt to W lanes, element i to lane (i mod W); each lane is folded sequentially
   from the state zero; the states of the lanes are combined from lane 0 upward; the
   remaining n mod W elements are folded sequentially into the result. For n < W no
   element is dealt and the W states combined are all zero. *)
Definition fold_lanes (W : nat) (xs : list B) : A :=
  fold_left step (skipn (W * (length xs / W)) xs)
    (combine_lanes (map fold_seq (deal W (firstn (W * (length xs / W)) xs)))).

(* Without a lane, and with one lane, the lane order is the sequential order. *)
Lemma fold_lanes_0 : forall xs : list B, fold_lanes 0 xs = fold_seq xs.
Proof. reflexivity. Qed.

Lemma fold_lanes_1 : forall xs : list B, fold_lanes 1 xs = fold_seq xs.
Proof.
intros xs. unfold fold_lanes, deal, combine_lanes.
rewrite Nat.div_1_r, Nat.mul_1_l, firstn_all, skipn_all.
cbn [seq map hd tl fold_left]. now rewrite lane_1.
Qed.

Lemma combine_zeros :
  combine zero zero = zero ->
  forall states : list A, Forall (fun s => s = zero) states -> combine_lanes states = zero.
Proof.
intros Hz states H. unfold combine_lanes. destruct H as [|s l Hs Hl]; cbn [hd tl].
- reflexivity.
- rewrite Hs. induction Hl as [|a l Ha _ IH]; cbn [fold_left].
  + reflexivity.
  + now rewrite Ha, Hz.
Qed.

(* With fewer elements than lanes, and a zero state that the combination leaves fixed,
   the lane order is the sequential order as well. *)
Lemma fold_lanes_short :
  forall (W : nat) (xs : list B),
  combine zero zero = zero -> (length xs < W)%nat ->
  fold_lanes W xs = fold_seq xs.
Proof.
intros W xs Hz Hn. unfold fold_lanes.
rewrite (Nat.div_small _ _ Hn), Nat.mul_0_r. cbn [firstn skipn].
rewrite combine_zeros. reflexivity. exact Hz.
unfold deal. rewrite map_map. apply Forall_forall. intros s Hs.
apply in_map_iff in Hs. destruct Hs as [j [Hj _]]. rewrite <- Hj. reflexivity.
Qed.

Lemma fold_left_inv :
  forall (P : A -> Prop), (forall (s : A) (e : B), P s -> P (step s e)) ->
  forall (xs : list B) (s : A), P s -> P (fold_left step xs s).
Proof.
intros P Hs. induction xs as [|x r IH]; intros s Ps; cbn [fold_left].
- exact Ps.
- apply IH. now apply Hs.
Qed.

(* A property of the state that the step and the combination keep holds of the result
   of both orders. *)
Lemma fold_seq_inv :
  forall (P : A -> Prop), P zero -> (forall (s : A) (e : B), P s -> P (step s e)) ->
  forall xs : list B, P (fold_seq xs).
Proof. intros P Pz Hs xs. unfold fold_seq. now apply fold_left_inv. Qed.

Lemma fold_lanes_inv :
  forall (P : A -> Prop), P zero -> (forall (s : A) (e : B), P s -> P (step s e)) ->
  (forall a b : A, P a -> P b -> P (combine a b)) ->
  forall (W : nat) (xs : list B), P (fold_lanes W xs).
Proof.
intros P Pz Hs Hc W xs. unfold fold_lanes. apply fold_left_inv. exact Hs.
unfold combine_lanes.
assert (H : Forall P (map fold_seq (deal W (firstn (W * (length xs / W)) xs)))).
{ apply Forall_map. apply Forall_forall. intros l _. now apply fold_seq_inv. }
destruct H as [|s l Ps Pl]; cbn [hd tl].
- exact Pz.
- revert s Ps. induction Pl as [|a l Pa _ IH]; intros s Ps; cbn [fold_left].
  + exact Ps.
  + apply IH. now apply Hc.
Qed.

End Folds.

Arguments fold_seq {A B} step zero xs.
Arguments combine_lanes {A} combine zero states.
Arguments fold_lanes {A B} step combine zero W xs.

Lemma fold_left_ext_eq :
  forall (A B : Type) (f g : A -> B -> A), (forall (a : A) (b : B), f a b = g a b) ->
  forall (l : list B) (a : A), fold_left f l a = fold_left g l a.
Proof.
intros A B f g H. induction l as [|x r IH]; intros a; cbn [fold_left].
- reflexivity.
- now rewrite H, IH.
Qed.

Lemma fold_left_map_eq :
  forall (A B C : Type) (f : A -> C -> A) (g : B -> C) (l : list B) (a : A),
  fold_left f (map g l) a = fold_left (fun s e => f s (g e)) l a.
Proof.
intros A B C f g. induction l as [|x r IH]; intros a; cbn [map fold_left].
- reflexivity.
- apply IH.
Qed.

(* Two steps that are equal on every state and element give the same loops. *)
Lemma fold_seq_ext :
  forall (A B : Type) (step step' : A -> B -> A) (zero : A),
  (forall (s : A) (e : B), step s e = step' s e) ->
  forall xs : list B, fold_seq step zero xs = fold_seq step' zero xs.
Proof. intros A B step step' zero H xs. unfold fold_seq. now apply fold_left_ext_eq. Qed.

Lemma fold_lanes_ext :
  forall (A B : Type) (step step' : A -> B -> A) (combine combine' : A -> A -> A) (zero : A),
  (forall (s : A) (e : B), step s e = step' s e) ->
  (forall a b : A, combine a b = combine' a b) ->
  forall (W : nat) (xs : list B),
  fold_lanes step combine zero W xs = fold_lanes step' combine' zero W xs.
Proof.
intros A B step step' combine combine' zero H Hc W xs. unfold fold_lanes.
rewrite (fold_left_ext_eq _ _ step step' H).
rewrite (map_ext _ _ (fold_seq_ext _ _ step step' zero H)).
unfold combine_lanes. now rewrite (fold_left_ext_eq _ _ combine combine' Hc).
Qed.

(* A step that first makes a value of each element, s <- op s (g e), is the loop of op
   over the list of those values. *)
Lemma fold_seq_map :
  forall (A B C : Type) (op : A -> C -> A) (g : B -> C) (zero : A) (xs : list B),
  fold_seq (fun s e => op s (g e)) zero xs = fold_seq op zero (map g xs).
Proof. intros A B C op g zero xs. unfold fold_seq. symmetry. apply fold_left_map_eq. Qed.

Lemma fold_lanes_map :
  forall (A B C : Type) (op : A -> C -> A) (combine : A -> A -> A) (g : B -> C) (zero : A)
         (W : nat) (xs : list B),
  fold_lanes (fun s e => op s (g e)) combine zero W xs = fold_lanes op combine zero W (map g xs).
Proof.
intros A B C op combine g zero W xs. unfold fold_lanes.
rewrite length_map, firstn_map, skipn_map, deal_map, map_map, fold_left_map_eq.
rewrite (map_ext _ _ (fold_seq_map _ _ _ op g zero)). reflexivity.
Qed.

(** * A loop that writes an array *)

(* A map writes one element for every element it reads: element i of the array written
   is a function f of element i of the arrays read (the scalars given once are part of
   f), and of nothing else, so it does not depend on the order in which the loop goes
   through the arrays. Its model is the list map f xs, with no state and no order
   (proofs/gen/FoldModel.v, F_map), and its statement relates the two lists entry by
   entry, with Forall2: Forall2 P xs (map f xs) says that the list written has the
   length of the list read and that P holds of element i of one and element i of the
   other, for every i (Forall2_map_nth below).

   The first lemma is that this follows from P x (f x) for every element x of the list
   read, and the second that it says no more. The third is the form in which a map's
   statement follows from its step's: if every element satisfies a requirement Q, and
   the step takes an element that satisfies Q to a result that P relates to it, then P
   relates every element to the one written for it. *)
Lemma Forall2_map_r :
  forall (A B : Type) (P : A -> B -> Prop) (f : A -> B) (xs : list A),
  Forall (fun x => P x (f x)) xs -> Forall2 P xs (map f xs).
Proof.
intros A B P f. induction xs as [|x r IH]; intros H; cbn [map].
- constructor.
- constructor. exact (Forall_inv H). apply IH. exact (Forall_inv_tail H).
Qed.

Lemma Forall2_map_r_inv :
  forall (A B : Type) (P : A -> B -> Prop) (f : A -> B) (xs : list A),
  Forall2 P xs (map f xs) -> Forall (fun x => P x (f x)) xs.
Proof.
intros A B P f. induction xs as [|x r IH]; cbn [map]; intros H.
- constructor.
- inversion H as [|a b l l' Hx Hr E1 E2]. subst. constructor. exact Hx. now apply IH.
Qed.

Lemma map_entries :
  forall (A B : Type) (Q : A -> Prop) (P : A -> B -> Prop) (f : A -> B),
  (forall x : A, Q x -> P x (f x)) ->
  forall xs : list A, Forall Q xs -> Forall2 P xs (map f xs).
Proof.
intros A B Q P f H xs Hx. apply Forall2_map_r.
revert Hx. apply Forall_impl. exact H.
Qed.

(* What the conclusion says, position by position. *)
Lemma Forall2_map_nth :
  forall (A B : Type) (P : A -> B -> Prop) (f : A -> B) (xs : list A),
  Forall2 P xs (map f xs) ->
  length (map f xs) = length xs /\
  forall (i : nat) (d : A) (e : B), (i < length xs)%nat -> P (nth i xs d) (nth i (map f xs) e).
Proof.
intros A B P f xs H. split. apply length_map.
apply Forall2_map_r_inv in H. revert H.
induction xs as [|x r IH]; intros H i d e Hi; cbn [length] in Hi.
- lia.
- destruct i as [|i]; cbn [map nth].
  + exact (Forall_inv H).
  + apply IH. exact (Forall_inv_tail H). lia.
Qed.

(** * The mask of a loop that writes an array *)

(* A map keeps one mask, true at the start. Its step ands into the mask a test t of the
   element just written, and the lane order combines the masks of the lanes by and. In
   both orders, and for every number of lanes, the result is the test of every element
   (forallb t): the mask does not depend on the order either. Nothing of the real model
   uses this (there a map has no mask); it is what a statement about the mask in the two
   orders rests on. *)
Lemma fold_left_and :
  forall (B : Type) (t : B -> bool) (xs : list B) (m : bool),
  fold_left (fun m x => andb m (t x)) xs m = andb m (forallb t xs).
Proof.
intros B t. induction xs as [|x r IH]; intros m; cbn [fold_left forallb].
- now rewrite andb_true_r.
- rewrite IH. now rewrite andb_assoc.
Qed.

Lemma fold_seq_and :
  forall (B : Type) (t : B -> bool) (xs : list B),
  fold_seq (fun m x => andb m (t x)) true xs = forallb t xs.
Proof. intros B t xs. unfold fold_seq. rewrite fold_left_and. reflexivity. Qed.

(* The masks of the lanes, each the image of its lane by g, combined from lane 0 upward. *)
Lemma combine_lanes_and :
  forall (C : Type) (g : C -> bool) (ls : list C),
  combine_lanes andb true (map g ls) = forallb g ls.
Proof.
intros C g ls. unfold combine_lanes. destruct ls as [|l ls]; cbn [map hd tl forallb].
- reflexivity.
- generalize (g l). induction ls as [|a ls IH]; intros m; cbn [map fold_left forallb].
  + now rewrite andb_true_r.
  + rewrite IH. now rewrite andb_assoc.
Qed.

Lemma forallb_concat_lanes :
  forall (B : Type) (t : B -> bool) (ls : list (list B)),
  forallb (forallb t) ls = forallb t (concat ls).
Proof.
intros B t. induction ls as [|l ls IH]; cbn [forallb concat].
- reflexivity.
- now rewrite forallb_app, IH.
Qed.

Lemma forallb_perm :
  forall (B : Type) (t : B -> bool) (l l' : list B),
  Permutation l l' -> forallb t l = forallb t l'.
Proof.
intros B t l l' H. induction H as [|x l l' H IH|x y l|l l' l'' H1 IH1 H2 IH2]; cbn [forallb].
- reflexivity.
- now rewrite IH.
- rewrite !andb_assoc. now rewrite (andb_comm (t y) (t x)).
- now rewrite IH1.
Qed.

Lemma fold_lanes_and :
  forall (B : Type) (t : B -> bool) (W : nat) (xs : list B),
  fold_lanes (fun m x => andb m (t x)) andb true W xs = forallb t xs.
Proof.
intros B t W xs. destruct W as [|w].
- rewrite fold_lanes_0. apply fold_seq_and.
- unfold fold_lanes. set (k := (S w * (length xs / S w))%nat).
  rewrite fold_left_and.
  rewrite (map_ext _ _ (fold_seq_and B t)).
  rewrite combine_lanes_and, forallb_concat_lanes.
  rewrite (forallb_perm B t _ _ (deal_perm B (S w) (firstn k xs) (Nat.lt_0_succ w))).
  rewrite <- forallb_app, firstn_skipn. reflexivity.
Qed.

(** * A combination that is associative and commutative *)

(* A fold of maxima: the step combines the state with something made of the element
   alone, s <- combine s (g x), and the combination is associative and commutative. Then
   the order in which the elements are combined does not matter, and the lane order
   returns the state of the sequential order, for every number of lanes and every list.

   The hypotheses, and why each is there.
   - The laws are asked on a set P of states only, which holds the zero state and is
     closed under the combination. In a model where the combination is associative and
     commutative on every state, P is everything (a maximum of real numbers). In a model
     where it is not (a maximum computed by a comparison of floating-point numbers is
     not commutative when an operand is a NaN, nor on the two zeros), P is the set the
     states of the loop stay in.
   - combine zero zero = zero: the W lanes all start from zero and the sequential order
     starts from it once, so the two differ by W - 1 combinations with it; with no
     element at all, the lane order returns the combination of W zero states. The zero
     state need not be an identity of the combination on P.
   - Of an element x: g x is in P, and on a state of P the step is the combination with
     g x. The step is given on its own and has to agree with the combination on the
     states of P only, so that g can be chosen. (A floating-point maximum that skips a
     NaN element and records it in a mask is, on every state the loop can be in, the
     combination with (|x|, true) for an x that is not a NaN and with (+0, false) for a
     NaN; the pair it combines the state with in its listing, (NaN, false), is not in
     P.)
   fold_lanes_aci is the case in which the step is the combination after g, as written.

   How. On P the combination of a list of states into a state s, fold_left combine l s,
   does not depend on the order of the list (combine_all_perm), and a state combined
   into the result is that state combined into the start (combine_all_shift). So the
   combination of the states of the lanes, each the combination of its own elements
   from zero, is the combination from zero of the lanes one after the other, each
   preceded by zero (combine_lanes_concat); that list is a permutation of W zeros
   followed by the elements dealt (concat_cons_perm, deal_perm); and the zeros combine
   to zero. *)
Section Order.
Variables A B : Type.
Variable P : A -> Prop.
Variable step : A -> B -> A.
Variable combine : A -> A -> A.
Variable g : B -> A.
Variable zero : A.

Hypothesis P_zero : P zero.
Hypothesis P_combine : forall a b : A, P a -> P b -> P (combine a b).
Hypothesis combine_comm : forall a b : A, P a -> P b -> combine a b = combine b a.
Hypothesis combine_assoc :
  forall a b c : A, P a -> P b -> P c -> combine (combine a b) c = combine a (combine b c).
Hypothesis zero_zero : combine zero zero = zero.

(* What is asked of an element. *)
Local Notation combined x := (P (g x) /\ forall s : A, P s -> step s x = combine s (g x)).

Lemma combine_all_P :
  forall (l : list A) (s : A), P s -> Forall P l -> P (fold_left combine l s).
Proof.
induction l as [|a l IH]; intros s Ps Hl; cbn [fold_left].
- exact Ps.
- apply IH.
  + apply P_combine. exact Ps. exact (Forall_inv Hl).
  + exact (Forall_inv_tail Hl).
Qed.

(* The combination of a list of states of P into a state of P does not depend on the
   order of the list. *)
Lemma combine_all_perm :
  forall l l' : list A, Permutation l l' -> Forall P l ->
  forall s : A, P s -> fold_left combine l s = fold_left combine l' s.
Proof.
intros l l' H.
induction H as [|x l l' H IH|x y l|l l' l'' H1 IH1 H2 IH2]; intros Hl s Ps; cbn [fold_left].
- reflexivity.
- apply IH. exact (Forall_inv_tail Hl). apply P_combine. exact Ps. exact (Forall_inv Hl).
- pose proof (Forall_inv Hl) as Py.
  pose proof (Forall_inv (Forall_inv_tail Hl)) as Px.
  rewrite (combine_assoc s y x Ps Py Px), (combine_comm y x Py Px).
  rewrite <- (combine_assoc s x y Ps Px Py). reflexivity.
- rewrite (IH1 Hl s Ps). apply IH2; [|exact Ps].
  apply Forall_forall. intros z Hz. apply (proj1 (Forall_forall P l) Hl).
  apply Permutation_in with (1 := Permutation_sym H1). exact Hz.
Qed.

(* A state combined into the result is that state combined into the start. *)
Lemma combine_all_shift :
  forall (l : list A) (s t : A), P s -> P t -> Forall P l ->
  combine s (fold_left combine l t) = fold_left combine l (combine s t).
Proof.
induction l as [|a l IH]; intros s t Ps Pt Hl; cbn [fold_left].
- reflexivity.
- rewrite (IH s (combine t a) Ps (P_combine t a Pt (Forall_inv Hl)) (Forall_inv_tail Hl)).
  rewrite (combine_assoc s t a Ps Pt (Forall_inv Hl)). reflexivity.
Qed.

Lemma combine_all_zeros :
  forall k : nat, fold_left combine (repeat zero k) zero = zero.
Proof.
induction k as [|k IH]; cbn [repeat fold_left].
- reflexivity.
- rewrite zero_zero. exact IH.
Qed.

(* From a state of P the loop of the step is the combination of the images of the
   elements, in their order. *)
Lemma fold_left_combined :
  forall (xs : list B) (s : A), P s -> Forall (fun x => combined x) xs ->
  fold_left step xs s = fold_left combine (map g xs) s.
Proof.
induction xs as [|x r IH]; intros s Ps H; cbn [map fold_left].
- reflexivity.
- destruct (Forall_inv H) as [Pg Hs]. rewrite (Hs s Ps).
  apply IH. now apply P_combine. exact (Forall_inv_tail H).
Qed.

Lemma combined_images :
  forall xs : list B, Forall (fun x => combined x) xs -> Forall P (map g xs).
Proof.
intros xs H. apply Forall_map. revert H. apply Forall_impl. intros x Hx. apply Hx.
Qed.

(* The sequential order is the combination, from zero, of the images of the elements. *)
Lemma fold_seq_combined :
  forall xs : list B, Forall (fun x => combined x) xs ->
  fold_seq step zero xs = fold_left combine (map g xs) zero.
Proof. intros xs H. unfold fold_seq. now apply fold_left_combined. Qed.

(* The states of lanes, each the combination of its list from zero, combined into t: the
   combination into t of the lists one after the other, each preceded by zero. *)
Lemma combine_lanes_concat :
  forall (ls : list (list A)) (t : A), P t -> Forall (Forall P) ls ->
  fold_left combine (map (fun l => fold_left combine l zero) ls) t =
  fold_left combine (concat (map (cons zero) ls)) t.
Proof.
induction ls as [|l ls IH]; intros t Pt H; cbn [map concat fold_left].
- reflexivity.
- pose proof (Forall_inv H) as Hl.
  rewrite (combine_all_shift l t zero Pt P_zero Hl).
  rewrite fold_left_app. cbn [fold_left].
  apply IH; [|exact (Forall_inv_tail H)].
  apply combine_all_P; [|exact Hl]. now apply P_combine.
Qed.

(* The combination of the states of the lanes, from lane 0 upward, when every lane is the
   combination from zero of a list of states of P: the combination from zero of all of
   them, in any order. *)
Lemma combine_lanes_all :
  forall (ls : list (list A)) (l : list A), Forall (Forall P) ls ->
  Permutation (concat ls) l ->
  combine_lanes combine zero (map (fun l => fold_left combine l zero) ls) =
  fold_left combine l zero.
Proof.
intros ls l H Hp.
assert (E : combine_lanes combine zero (map (fun l => fold_left combine l zero) ls) =
            fold_left combine (map (fun l => fold_left combine l zero) ls) zero).
{ unfold combine_lanes. destruct ls as [|l0 ls']; cbn [map hd tl fold_left].
  - reflexivity.
  - rewrite (combine_all_shift l0 zero zero P_zero P_zero (Forall_inv H)), zero_zero.
    reflexivity. }
rewrite E, (combine_lanes_concat ls zero P_zero H).
assert (Hz : Forall P (concat (map (cons zero) ls))).
{ apply Forall_concat. apply Forall_map. revert H. apply Forall_impl.
  intros l0 H0. now constructor. }
rewrite (combine_all_perm _ _ (concat_cons_perm A zero ls) Hz zero P_zero).
rewrite fold_left_app, combine_all_zeros.
apply combine_all_perm. exact Hp. now apply Forall_concat. exact P_zero.
Qed.

(* The lane order is the sequential order, for every number of lanes. *)
Theorem fold_lanes_aci_step :
  forall (W : nat) (xs : list B), Forall (fun x => combined x) xs ->
  fold_lanes step combine zero W xs = fold_seq step zero xs.
Proof.
intros W xs H. destruct W as [|w]. apply fold_lanes_0.
unfold fold_lanes.
set (b := (S w * (length xs / S w))%nat).
assert (Hsplit : Forall (fun x => combined x) (firstn b xs) /\
                 Forall (fun x => combined x) (skipn b xs)).
{ apply Forall_app. now rewrite firstn_skipn. }
destruct Hsplit as [Hpre Hrest].
assert (E1 : map (fold_seq step zero) (deal (S w) (firstn b xs)) =
             map (fun l => fold_left combine l zero) (deal (S w) (map g (firstn b xs)))).
{ rewrite deal_map, map_map. apply map_ext_in. intros l Hl.
  apply fold_seq_combined.
  unfold deal in Hl. apply in_map_iff in Hl. destruct Hl as [j [Ej _]]. rewrite <- Ej.
  now apply lane_Forall. }
assert (Pls : Forall (Forall P) (deal (S w) (map g (firstn b xs)))).
{ unfold deal. apply Forall_map. apply Forall_forall. intros j _.
  apply lane_Forall. now apply combined_images. }
rewrite E1.
rewrite (combine_lanes_all _ (map g (firstn b xs)) Pls
           (deal_perm A (S w) (map g (firstn b xs)) (Nat.lt_0_succ w))).
rewrite (fold_left_combined (skipn b xs) _
           (combine_all_P _ _ P_zero (combined_images _ Hpre)) Hrest).
rewrite <- fold_left_app, <- map_app, firstn_skipn.
symmetry. now apply fold_seq_combined.
Qed.

End Order.

(* The case in which the step is the combination after a function of the element. *)
Lemma fold_lanes_aci :
  forall (A B : Type) (P : A -> Prop) (combine : A -> A -> A) (g : B -> A) (zero : A),
  P zero ->
  (forall a b : A, P a -> P b -> P (combine a b)) ->
  (forall a b : A, P a -> P b -> combine a b = combine b a) ->
  (forall a b c : A, P a -> P b -> P c -> combine (combine a b) c = combine a (combine b c)) ->
  combine zero zero = zero ->
  forall (W : nat) (xs : list B), Forall (fun x => P (g x)) xs ->
  fold_lanes (fun s x => combine s (g x)) combine zero W xs =
  fold_seq (fun s x => combine s (g x)) zero xs.
Proof.
intros A B P combine g zero Pz Pc Hc Ha Hz W xs H.
apply (fold_lanes_aci_step A B P (fun s x => combine s (g x)) combine g zero Pz Pc Hc Ha Hz).
revert H. apply Forall_impl. intros x Px. split. exact Px. reflexivity.
Qed.
