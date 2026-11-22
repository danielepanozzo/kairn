(* The convolutions: the coefficients of the product of two polynomials, in the real model.

   conv_1 and conv_2 (docs/developer/architecture.md, "Convolutions") write the
   coefficients of the product of two polynomials given by their coefficients, xs of
   n_x of them and ys of n_y. proofs/gen/FoldModel.v states the result as a list,

       F_conv xs ys = map (fun j => dot_k_seq (conv_terms xs ys j))
                          (seq 0 (conv_length (length xs) (length ys))),

   coefficient j being the dot product dot_k, in its sequential order, of the list
   conv_terms xs ys j; and the generated statement F_spec (proofs/gen/FoldStatements.v)
   says, coefficient by coefficient (Forall2 of the indices and the coefficients), what
   the statement of dot_k in the sequential order concludes for that list: the
   coefficient is valid and within the bound of the dot product of the sum of the
   products of its terms. This file proves

       conv_1_correct : conv_1_spec          conv_2_correct : conv_2_spec,

   each the theorem of the dot product (dot_k_seq_correct of FoldSums.v) on the terms of
   every coefficient, through Forall2_map_r of Folds.v; the terms of a coefficient
   satisfy the requirements of the dot product because the coefficients of the two
   polynomials do (conv_terms_Forall).

   What the statements do not say, and what is proved here about it.
   - What the terms are. A statement names the list conv_terms xs ys j and says nothing
     of it: that it is the list of the pairs (x_i, y_(j-i)) is a property of the
     definition of proofs/gen/FoldModel.v, written there with firstn, skipn, rev and
     combine. It is proved here: the list is exactly
         (x_i, y_(j-i))   for i = lo, lo + 1, ..., lo + m_j - 1,   lo = j - (n_y - 1),
     in increasing i (conv_terms_eq; conv_terms_nth for one term), a subtraction of
     natural numbers being 0 when it would be negative; with at least one y,
     m_j = min (j + 1, n_x) - lo (conv_terms_count), so that i goes from
     max (0, j - n_y + 1) to min (j, n_x - 1): the sum of the products of the terms is
     the coefficient of t^j of the product of the two polynomials as it is usually
     defined. No theorem here is about the product as a polynomial (its value at a
     point).
   - How many terms. Every coefficient has at least one term and at most
     min (n_x, n_y) (conv_terms_nonempty, conv_terms_length). The second is what lets a
     program bound every coefficient with one call of the bound kernel of the dot
     product, for a count of at least min (n_x, n_y): conv_1_bound and conv_2_bound,
     from dot_k_seq_bound of FoldGuarantee.v, in the form of a convolution's statement.
   - What the statements do say of the shape: Forall2 with the list of the indices
     gives the number of coefficients, conv_length n_x n_y, which is n_x + n_y - 1, and
     0 when a polynomial has no coefficient (Forall2_seq_nth reads a statement
     coefficient by coefficient).
   - No mask, no order, no array, as for a map (FoldMaps.v): the loop returns the and of
     a test of every coefficient written and rewrites those that are not finite as NaN,
     which is a statement of the IEEE model, not generated yet; the model has one
     order, the sequential one, the only one the library has; and that the array
     written must not overlap the arrays read is a requirement on the caller of the
     generated C++, about which nothing is proved. *)
From Stdlib Require Import Reals ZArith List Arith Lia.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements FoldModel FoldStatements.
From Kairn Require Import Folds Summation FoldSums FoldGuarantee.
Import ListNotations.
Open Scope R_scope.

(** * Lists: combine, firstn, skipn *)

Lemma combine_Forall :
  forall (A B : Type) (P : A -> Prop) (Q : B -> Prop) (l1 : list A) (l2 : list B),
  Forall P l1 -> Forall Q l2 -> Forall (fun ab => P (fst ab) /\ Q (snd ab)) (combine l1 l2).
Proof.
intros A B P Q l1 l2 H1. revert l2.
induction H1 as [|a l1 Pa _ IH]; intros l2 H2.
- constructor.
- destruct H2 as [|b l2 Qb H2]; cbn [combine].
  + constructor.
  + constructor. split; assumption. now apply IH.
Qed.

Lemma Forall_firstn_skipn :
  forall (A : Type) (P : A -> Prop) (n : nat) (l : list A),
  Forall P l -> Forall P (firstn n l) /\ Forall P (skipn n l).
Proof. intros A P n l H. apply Forall_app. now rewrite firstn_skipn. Qed.

(* An entry of combine, below its length. *)
Lemma combine_nth_lt :
  forall (A B : Type) (l1 : list A) (l2 : list B) (k : nat) (a : A) (b : B),
  (k < length (combine l1 l2))%nat ->
  nth k (combine l1 l2) (a, b) = (nth k l1 a, nth k l2 b).
Proof.
intros A B. induction l1 as [|x l1 IH]; intros l2 k a b H.
- cbn [combine length] in H. lia.
- destruct l2 as [|y l2]; cbn [combine length] in H.
  + lia.
  + destruct k as [|k]; cbn [combine nth].
    * reflexivity.
    * apply IH. lia.
Qed.

Lemma nth_firstn_lt :
  forall (A : Type) (n : nat) (l : list A) (i : nat) (d : A),
  (i < n)%nat -> nth i (firstn n l) d = nth i l d.
Proof.
intros A. induction n as [|n IH]; intros l i d H.
- lia.
- destruct l as [|x l]; cbn [firstn].
  + reflexivity.
  + destruct i as [|i]; cbn [nth].
    * reflexivity.
    * apply IH. lia.
Qed.

Lemma nth_skipn_add :
  forall (A : Type) (n : nat) (l : list A) (i : nat) (d : A),
  nth i (skipn n l) d = nth (n + i) l d.
Proof.
intros A. induction n as [|n IH]; intros l i d; cbn [skipn].
- reflexivity.
- destruct l as [|x l].
  + destruct i; reflexivity.
  + cbn [Nat.add nth]. apply IH.
Qed.

(* A statement in the form of a convolution's, Forall2 with a list of indices, read
   index by index. *)
Lemma Forall2_seq_nth :
  forall (C : Type) (P : nat -> C -> Prop) (n s : nat) (l : list C),
  Forall2 P (seq s n) l ->
  length l = n /\ forall (j : nat) (d : C), (j < n)%nat -> P (s + j)%nat (nth j l d).
Proof.
intros C P. induction n as [|n IH]; intros s l H; cbn [seq] in H.
- inversion H. split. reflexivity. intros j d Hj. lia.
- inversion H as [|a c la lc Hc Hr E1 E2]. subst.
  destruct (IH (S s) lc Hr) as [L N]. split.
  + cbn [length]. now rewrite L.
  + intros j d Hj. destruct j as [|j]; cbn [nth].
    * now rewrite Nat.add_0_r.
    * replace (s + S j)%nat with (S s + j)%nat by lia. apply N. lia.
Qed.

(** * The terms of a coefficient *)

(* The requirements of the coefficients of the two polynomials hold of every term. *)
Lemma conv_terms_Forall :
  forall (A B : Type) (P : A -> Prop) (Q : B -> Prop) (xs : list A) (ys : list B) (j : nat),
  Forall P xs -> Forall Q ys -> Forall (fun ab => P (fst ab) /\ Q (snd ab)) (conv_terms xs ys j).
Proof.
intros A B P Q xs ys j Hx Hy. unfold conv_terms. apply combine_Forall.
- apply Forall_firstn_skipn. now apply Forall_firstn_skipn.
- apply Forall_rev. now apply Forall_firstn_skipn.
Qed.

(* The number of terms, as the definition gives it. *)
Lemma conv_terms_length_eq :
  forall (A B : Type) (xs : list A) (ys : list B) (j : nat),
  length (conv_terms xs ys j) =
  Nat.min (Nat.min (S j) (length xs) - (j - (length ys - 1))) (Nat.min (S j) (length ys)).
Proof.
intros A B xs ys j. unfold conv_terms.
now rewrite length_combine, length_skipn, length_rev, !length_firstn.
Qed.

(* At most the number of coefficients of the shorter polynomial. *)
Lemma conv_terms_length :
  forall (A B : Type) (xs : list A) (ys : list B) (j : nat),
  (length (conv_terms xs ys j) <= Nat.min (length xs) (length ys))%nat.
Proof. intros A B xs ys j. rewrite conv_terms_length_eq. lia. Qed.

(* With at least one y: i goes from lo = j - (n_y - 1) to min (j, n_x - 1). *)
Lemma conv_terms_count :
  forall (A B : Type) (xs : list A) (ys : list B) (j : nat),
  (0 < length ys)%nat ->
  length (conv_terms xs ys j) = (Nat.min (S j) (length xs) - (j - (length ys - 1)))%nat.
Proof. intros A B xs ys j H. rewrite conv_terms_length_eq. lia. Qed.

(* Every coefficient of the product has at least one term. *)
Lemma conv_terms_nonempty :
  forall (A B : Type) (xs : list A) (ys : list B) (j : nat),
  (j < conv_length (length xs) (length ys))%nat -> (1 <= length (conv_terms xs ys j))%nat.
Proof.
intros A B xs ys j H. rewrite conv_terms_length_eq.
destruct xs as [|x xs]; destruct ys as [|y ys]; cbn [conv_length length] in H |- *; lia.
Qed.

(* Term k of coefficient j is (x_i, y_(j-i)) with i = lo + k. *)
Lemma conv_terms_nth :
  forall (A B : Type) (xs : list A) (ys : list B) (j k : nat) (a : A) (b : B),
  (k < length (conv_terms xs ys j))%nat ->
  nth k (conv_terms xs ys j) (a, b) =
  (nth (j - (length ys - 1) + k) xs a, nth (j - (j - (length ys - 1) + k)) ys b).
Proof.
intros A B xs ys j k a b H.
pose proof H as H'. rewrite conv_terms_length_eq in H'.
unfold conv_terms in H |- *. rewrite (combine_nth_lt _ _ _ _ k a b H). f_equal.
- rewrite nth_skipn_add. apply nth_firstn_lt. lia.
- rewrite rev_nth by (rewrite length_firstn; lia).
  rewrite length_firstn. rewrite nth_firstn_lt by lia. f_equal. lia.
Qed.

(* The terms of coefficient j are exactly the pairs (x_i, y_(j-i)), for the m_j
   consecutive i from lo on, in increasing order. *)
Theorem conv_terms_eq :
  forall (A B : Type) (xs : list A) (ys : list B) (j : nat) (a : A) (b : B),
  conv_terms xs ys j =
  map (fun i => (nth i xs a, nth (j - i) ys b))
      (seq (j - (length ys - 1)) (length (conv_terms xs ys j))).
Proof.
intros A B xs ys j a b.
apply nth_ext with (d := (a, b)) (d' := (nth 0 xs a, nth (j - 0) ys b)).
- now rewrite length_map, length_seq.
- intros k H.
  rewrite (map_nth (fun i => (nth i xs a, nth (j - i) ys b))).
  rewrite seq_nth by exact H. now apply conv_terms_nth.
Qed.

(** * The generated statements *)

Theorem conv_1_correct : conv_1_spec.
Proof.
intros emin prec Hp xs ys Hx Hy. unfold conv_1_conv. apply Forall2_map_r.
apply Forall_forall. intros j _.
exact (dot_1_seq_correct emin prec Hp (conv_terms xs ys j)
         (conv_terms_Forall _ _ _ _ xs ys j Hx Hy)).
Qed.

(* conv_1_entry: the coefficients by dot_1_entry, whose step guards both factors (rule R3, the
   factors of a fused operation): its theorem, on the terms, numbers of the format. *)
Theorem conv_1_entry_correct : conv_1_entry_spec.
Proof.
intros emin prec Hp xs ys Hx Hy. unfold conv_1_entry_conv. apply Forall2_map_r.
apply Forall_forall. intros j _.
exact (dot_1_entry_seq_correct emin prec Hp (conv_terms xs ys j)
         (conv_terms_Forall _ _ _ _ xs ys j Hx Hy)).
Qed.

Theorem conv_2_correct : conv_2_spec.
Proof.
intros emin prec Hp xs ys Hx Hy. unfold conv_2_conv. apply Forall2_map_r.
apply Forall_forall. intros j _.
exact (dot_2_seq_correct emin prec Hp (conv_terms xs ys j)
         (conv_terms_Forall _ _ _ _ xs ys j Hx Hy)).
Qed.

(** * One exported bound for every coefficient *)

(* The count of the bound kernel of the dot product: at least min (n_x, n_y) is at least
   the number of terms of every coefficient. *)
Lemma conv_terms_count_le :
  forall (A B : Type) (xs : list A) (ys : list B) (j : nat) (m : R),
  INR (Nat.min (length xs) (length ys)) <= m -> INR (length (conv_terms xs ys j)) <= m.
Proof.
intros A B xs ys j m H. apply Rle_trans with (2 := H). apply le_INR. apply conv_terms_length.
Qed.

(* If the bound kernel of the dot product, called with a count m that is at least
   min (n_x, n_y), answers ok, every coefficient is valid and within g times the sum of
   the magnitudes of the products of its terms, plus t. *)
Theorem conv_1_bound :
  forall emin prec : Z, (1 <= prec)%Z -> eta emin <= / 2 ->
  forall (xs ys : list R) (m g t : R),
  Forall (fun x => fmt emin prec x) xs ->
  Forall (fun y => fmt emin prec y) ys ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) ->
  INR (Nat.min (length xs) (length ys)) <= m ->
  bound_dot_1 emin prec tie_even m = (g, t, true) ->
  Forall2 (fun j s =>
    let xys := conv_terms xs ys j in
    fmt emin prec s /\
    Rabs (s - sumR (map (fun xy => fst xy * snd xy) xys)) <=
      g * sumabs (map (fun xy => fst xy * snd xy) xys) + t)
    (seq 0 (conv_length (length xs) (length ys))) (conv_1_conv emin prec tie_even xs ys).
Proof.
intros emin prec Hp Hh xs ys m g t Hx Hy Fm Hm Hn Hb. unfold conv_1_conv.
apply Forall2_map_r. apply Forall_forall. intros j _.
exact (dot_1_seq_bound emin prec Hp Hh (conv_terms xs ys j) m g t
         (conv_terms_Forall _ _ _ _ xs ys j Hx Hy) Fm Hm
         (conv_terms_count_le _ _ xs ys j m Hn) Hb).
Qed.

Theorem conv_2_bound :
  forall emin prec : Z, (4 <= prec)%Z -> eta emin <= / 2 ->
  forall (xs ys : list (R * R)) (m g t : R),
  Forall (fun x => normalized_2 emin prec (fst x) (snd x)) xs ->
  Forall (fun y => normalized_2 emin prec (fst y) (snd y)) ys ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) ->
  INR (Nat.min (length xs) (length ys)) <= m ->
  bound_dot_2 emin prec tie_even m = (g, t, true) ->
  Forall2 (fun j s =>
    let xys := conv_terms xs ys j in
    normalized_2 emin prec (fst s) (snd s) /\
    Rabs ((fst s + snd s) -
          sumR (map (fun xy => (fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy))) xys)) <=
      g * sumabs (map (fun xy => (fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy))) xys) + t)
    (seq 0 (conv_length (length xs) (length ys))) (conv_2_conv emin prec tie_even xs ys).
Proof.
intros emin prec Hp Hh xs ys m g t Hx Hy Fm Hm Hn Hb. unfold conv_2_conv.
apply Forall2_map_r. apply Forall_forall. intros j _.
exact (dot_2_seq_bound emin prec Hp Hh (conv_terms xs ys j) m g t
         (conv_terms_Forall _ _ _ _ xs ys j Hx Hy) Fm Hm
         (conv_terms_count_le _ _ xs ys j m Hn) Hb).
Qed.

(** * The generated statements of conv_terms *)

(* conv_terms_eq_spec, conv_terms_count_spec and conv_terms_length_spec
   (proofs/gen/FoldStatements.v) have the types of the lemmas above. *)
Theorem conv_terms_eq_correct : conv_terms_eq_spec.
Proof. exact conv_terms_eq. Qed.

Theorem conv_terms_count_correct : conv_terms_count_spec.
Proof. exact conv_terms_count. Qed.

Theorem conv_terms_length_correct : conv_terms_length_spec.
Proof. exact conv_terms_length. Qed.
