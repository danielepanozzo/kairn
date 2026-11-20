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
   products in these orders are in Summation.v. *)
From Stdlib Require Import List Arith Lia Permutation.
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
