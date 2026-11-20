(* Summation over any tree, and the bounds of the two orders in which a batch kernel adds.

   Nothing in this file is floating-point arithmetic: it is real arithmetic about an
   addition of which only an error bound is known. The additions of Kairn that satisfy
   the hypothesis, and the sums and dot products made with them, are in
   SummationKernels.v; the two orders are defined in Folds.v.

   Setting. A value x of a type V has a real number val x, and may be valid. An addition
   op has relative error eps (the definition adds) when, for valid a and b, op a b is
   valid and
       |val (op a b) - (val a + val b)| <= eps (|val a| + |val b|).
   The error is relative to the operands and not to the exact sum. This asks less of the
   addition, since |a + b| <= |a| + |b|.

   What is proved.
   1. The tree theorem (tree_sum). A binary tree whose leaves are valid values x_1 .. x_n
      and whose nodes are op evaluates to a valid value s with
          |val s - sum val x_i| <= ((1 + eps)^h - 1) sum |val x_i|
          |val s|               <= (1 + eps)^h sum |val x_i|
      where h is the height of the tree, the largest number of additions between a leaf
      and the root. This is the bound of Higham for summation (Accuracy and Stability of
      Numerical Algorithms, 2nd ed., section 4.2), which holds for every order.
      The general form (tree_sum_general) lets every addition also commit an absolute
      error that depends on its operands. Two cases of it are stated: the same absolute
      error tau at every addition (tree_sum_tau), and an absolute error w a + w b that
      the operands bring, where the result of an addition brings none
      (tree_sum_weighted). The second is what the fused step of a one-limb dot product
      needs: there only an operand that is not a number of the format costs eta / 2, so
      the additions that combine partial sums cost nothing.
   2. The closed forms: (1 + eps)^h - 1 <= gamma_h(eps) = h eps / (1 - h eps) when
      h eps < 1 (pow_minus_1_le_gamma), x / (1 - x) <= x (1 + 2 x) for 0 <= x <= 1/2
      (div_one_minus_le), and a tree with n leaves has height at most n - 1
      (height_le_leaves).
   3. Leaves that are themselves approximate (tree_sum_approx): if leaf i is within
      eps_x |t_i| + tau of a real number t_i, the tree is within
          ((1 + eps_x) (1 + eps)^h - 1) sum |t_i| + (1 + eps)^h n tau
      of sum t_i. This is the dot product: the leaves are the rounded products.
   4. The two orders of Folds.v are trees. The sequential order of n elements has height
      n - 1, and the lane order of width W has height n / W + (W - 1) + n mod W - 1 for
      n >= W >= 1, which is at most n - 1 (fold_seq_tree, fold_lanes_tree). This is when
      adding to the zero state returns the value of the other operand, so that the zero
      state is not a leaf; fold_seq_tree_zero and fold_lanes_tree_zero are the same with
      the zero states as leaves, one addition higher.
   5. Hence the bounds of items 1 and 3 with h = n - 1 for both orders: fold_seq_sum and
      fold_lanes_sum, in closed form fold_seq_sum_gamma and fold_lanes_sum_gamma, with
      approximate terms fold_seq_sum_approx and fold_lanes_sum_approx, and with the zero
      state as a leaf and the absolute errors of item 1 fold_seq_weighted and
      fold_lanes_weighted. *)
From Stdlib Require Import Reals List Arith Lia Lra Permutation.
From Kairn Require Import Folds.
Import ListNotations.
Open Scope R_scope.

(** * Sums of a list of real numbers *)

(* The sum of a list. *)
Fixpoint sumR (l : list R) : R :=
  match l with
  | [] => 0
  | x :: r => x + sumR r
  end.

(* The sum of the magnitudes of its elements. *)
Definition sumabs (l : list R) : R := sumR (map Rabs l).
Arguments sumabs : simpl never.

Lemma sumR_app : forall l1 l2 : list R, sumR (l1 ++ l2) = sumR l1 + sumR l2.
Proof.
intros l1 l2. induction l1 as [|a l1 IH]; cbn [app sumR].
- ring.
- rewrite IH. ring.
Qed.

Lemma sumabs_cons : forall (x : R) (l : list R), sumabs (x :: l) = Rabs x + sumabs l.
Proof. reflexivity. Qed.

Lemma sumabs_app : forall l1 l2 : list R, sumabs (l1 ++ l2) = sumabs l1 + sumabs l2.
Proof. intros l1 l2. unfold sumabs. rewrite map_app. apply sumR_app. Qed.

Lemma sumabs_ge_0 : forall l : list R, 0 <= sumabs l.
Proof.
induction l as [|a l IH].
- unfold sumabs. cbn [map sumR]. lra.
- rewrite sumabs_cons. generalize (Rabs_pos a). lra.
Qed.

Lemma sumR_le_sumabs : forall l : list R, Rabs (sumR l) <= sumabs l.
Proof.
induction l as [|a l IH].
- unfold sumabs. cbn [map sumR]. rewrite Rabs_R0. lra.
- rewrite sumabs_cons. cbn [sumR]. apply Rle_trans with (1 := Rabs_triang _ _). lra.
Qed.

(* Both sums are those of any reordering of the list. *)
Lemma sumR_perm : forall l1 l2 : list R, Permutation l1 l2 -> sumR l1 = sumR l2.
Proof. intros l1 l2 H. induction H; cbn [sumR]; lra. Qed.

Lemma sumabs_perm : forall l1 l2 : list R, Permutation l1 l2 -> sumabs l1 = sumabs l2.
Proof. intros l1 l2 H. unfold sumabs. apply sumR_perm. now apply Permutation_map. Qed.

Lemma sumR_map_ge_0 :
  forall (A : Type) (P : A -> Prop) (f : A -> R) (l : list A),
  (forall a : A, P a -> 0 <= f a) -> Forall P l -> 0 <= sumR (map f l).
Proof.
intros A P f l Hf H. induction H as [|a l Ha _ IH]; cbn [map sumR].
- lra.
- generalize (Hf a Ha). lra.
Qed.

Lemma sumR_le_const :
  forall (c : R) (l : list R), Forall (fun r => r <= c) l -> sumR l <= INR (length l) * c.
Proof.
intros c l H. induction H as [|a l Ha _ IH].
- cbn [sumR length INR]. lra.
- cbn [sumR length]. rewrite S_INR. lra.
Qed.

(* Two facts about lists that the standard library states otherwise. *)
Lemma Forall_perm :
  forall (A : Type) (P : A -> Prop) (l1 l2 : list A),
  Permutation l1 l2 -> Forall P l1 -> Forall P l2.
Proof.
intros A P l1 l2 Hp H. apply Forall_forall. intros x Hx.
apply (proj1 (Forall_forall P l1) H). apply Permutation_in with (1 := Permutation_sym Hp).
exact Hx.
Qed.

Lemma Forall2_map_both :
  forall (A B C : Type) (P : B -> C -> Prop) (f : A -> B) (g : A -> C) (l : list A),
  Forall (fun a => P (f a) (g a)) l -> Forall2 P (map f l) (map g l).
Proof. intros A B C P f g l H. induction H; cbn [map]; constructor; assumption. Qed.

(** * Binary trees *)

Section Tree.
Variable V : Type.

(* A summation order: a leaf is one of the numbers added, a node is one addition. *)
Inductive tree : Type :=
| Leaf (x : V)
| Node (l r : tree).

Variable op : V -> V -> V.

(* What the tree computes. *)
Fixpoint eval (t : tree) : V :=
  match t with
  | Leaf x => x
  | Node l r => op (eval l) (eval r)
  end.

(* Its leaves, from left to right. *)
Fixpoint leaves (t : tree) : list V :=
  match t with
  | Leaf x => [x]
  | Node l r => leaves l ++ leaves r
  end.

(* Its height: the largest number of additions between a leaf and the root. *)
Fixpoint height (t : tree) : nat :=
  match t with
  | Leaf _ => O
  | Node l r => S (Nat.max (height l) (height r))
  end.

(* Its number of additions. *)
Fixpoint nodes (t : tree) : nat :=
  match t with
  | Leaf _ => O
  | Node l r => S (nodes l + nodes r)
  end.

(* A tree has one leaf more than it has additions. *)
Lemma leaves_length : forall t : tree, length (leaves t) = S (nodes t).
Proof.
induction t as [x|l IHl r IHr]; cbn [leaves nodes length].
- reflexivity.
- rewrite length_app, IHl, IHr. lia.
Qed.

Lemma height_le_nodes : forall t : tree, (height t <= nodes t)%nat.
Proof. induction t as [x|l IHl r IHr]; cbn [height nodes]; lia. Qed.

(* Every tree with n leaves has height at most n - 1. The sequential order attains it. *)
Theorem height_le_leaves : forall t : tree, (height t <= length (leaves t) - 1)%nat.
Proof. intros t. rewrite leaves_length. generalize (height_le_nodes t). lia. Qed.

End Tree.

Arguments Leaf {V} x.
Arguments Node {V} l r.
Arguments eval {V} op t.
Arguments leaves {V} t.
Arguments height {V} t.
Arguments nodes {V} t.

(** * The closed forms of the bound *)

(* gamma_m(e) = m e / (1 - m e), the usual closed form of (1 + e)^m - 1. *)
Definition gamma (m : nat) (e : R) : R := INR m * e / (1 - INR m * e).

Lemma pow_mult_le_1 :
  forall (e : R) (h : nat), 0 <= e -> (1 + e) ^ h * (1 - INR h * e) <= 1.
Proof.
intros e h He. induction h as [|h IH].
- cbn [pow INR]. lra.
- rewrite <- tech_pow_Rmult, S_INR.
  assert (Hp : 0 <= (1 + e) ^ h) by (apply pow_le; lra).
  assert (Hn : 0 <= INR h) by apply pos_INR.
  assert (Hq : 0 <= (1 + e) ^ h * ((INR h + 1) * (e * e))).
  { apply Rmult_le_pos. exact Hp. apply Rmult_le_pos. lra. apply Rmult_le_pos; exact He. }
  replace ((1 + e) * (1 + e) ^ h * (1 - (INR h + 1) * e))
    with ((1 + e) ^ h * (1 - INR h * e) - (1 + e) ^ h * ((INR h + 1) * (e * e))) by ring.
  lra.
Qed.

(* (1 + e)^h - 1 <= h e / (1 - h e) when h e < 1. *)
Theorem pow_minus_1_le_gamma :
  forall (e : R) (h : nat), 0 <= e -> INR h * e < 1 -> (1 + e) ^ h - 1 <= gamma h e.
Proof.
intros e h He Hh. unfold gamma.
generalize (pow_mult_le_1 e h He).
set (p := (1 + e) ^ h). set (x := INR h * e) in *. intros Hp.
apply Rmult_le_reg_r with (1 - x). lra.
unfold Rdiv. rewrite (Rmult_assoc x (/ (1 - x)) (1 - x)), Rinv_l by lra. lra.
Qed.

(* The same with a height that is only bounded: h <= m and m e < 1. *)
Lemma pow_gamma :
  forall (e : R) (h m : nat), 0 <= e -> (h <= m)%nat -> INR m * e < 1 ->
  (1 + e) ^ h - 1 <= gamma m e.
Proof.
intros e h m He Hhm Hm.
assert (K : (1 + e) ^ h <= (1 + e) ^ m) by (apply Rle_pow; [lra | exact Hhm]).
generalize (pow_minus_1_le_gamma e m He Hm). lra.
Qed.

(* x / (1 - x) <= x (1 + 2 x) for 0 <= x <= 1/2: a bound of gamma without a division. *)
Theorem div_one_minus_le :
  forall x : R, 0 <= x <= / 2 -> x / (1 - x) <= x * (1 + 2 * x).
Proof.
intros x [H0 H1].
apply Rmult_le_reg_r with (1 - x). lra.
unfold Rdiv. rewrite (Rmult_assoc x (/ (1 - x)) (1 - x)), Rinv_l by lra.
assert (K : 0 <= x * x * (1 - 2 * x)).
{ apply Rmult_le_pos. apply Rmult_le_pos; exact H0. lra. }
replace (x * (1 + 2 * x) * (1 - x)) with (x * 1 + x * x * (1 - 2 * x)) by ring.
lra.
Qed.

(* Hence gamma_m(e) <= m e (1 + 2 m e) when m e <= 1/2. *)
Corollary gamma_le_poly :
  forall (m : nat) (e : R), 0 <= INR m * e <= / 2 ->
  gamma m e <= INR m * e * (1 + 2 * (INR m * e)).
Proof. intros m e H. unfold gamma. now apply div_one_minus_le. Qed.

(* The factor of a sum whose leaves are approximate: (1 + ex) (1 + e)^h - 1 is at most
   gamma_m of the larger of ex and e, for h + 1 <= m. *)
Lemma prod_pow_gamma :
  forall (ex e : R) (h m : nat), 0 <= ex -> 0 <= e -> (S h <= m)%nat ->
  INR m * Rmax ex e < 1 ->
  (1 + ex) * (1 + e) ^ h - 1 <= gamma m (Rmax ex e).
Proof.
intros ex e h m Hex He Hhm Hm.
assert (M1 : ex <= Rmax ex e) by apply Rmax_l.
assert (M2 : e <= Rmax ex e) by apply Rmax_r.
assert (K : (1 + ex) * (1 + e) ^ h <= (1 + Rmax ex e) ^ S h).
{ rewrite <- tech_pow_Rmult. apply Rmult_le_compat.
  - lra.
  - apply pow_le. lra.
  - lra.
  - apply pow_incr. split; lra. }
generalize (pow_gamma (Rmax ex e) (S h) m (Rle_trans _ _ _ Hex M1) Hhm Hm). lra.
Qed.

(* From the bound with a power to the bound with gamma. *)
Lemma gamma_bound :
  forall (e : R) (h m : nat) (a c x : R),
  0 <= e -> (h <= m)%nat -> INR m * e < 1 -> 0 <= a ->
  x <= ((1 + e) ^ h - 1) * a + c -> x <= gamma m e * a + c.
Proof.
intros e h m a c x He Hhm Hm Ha Hx.
assert (K : ((1 + e) ^ h - 1) * a <= gamma m e * a).
{ apply Rmult_le_compat_r. exact Ha. now apply pow_gamma. }
lra.
Qed.

(* The same without a second term. *)
Lemma gamma_bound_0 :
  forall (e : R) (h m : nat) (a x : R),
  0 <= e -> (h <= m)%nat -> INR m * e < 1 -> 0 <= a ->
  x <= ((1 + e) ^ h - 1) * a -> x <= gamma m e * a.
Proof.
intros e h m a x He Hhm Hm Ha Hx.
generalize (gamma_bound e h m a 0 x He Hhm Hm Ha). lra.
Qed.

(* The same for a sum of n approximate terms, whose height is at most n - 1: the factor
   (1 + ex) (1 + e)^(n-1) - 1 is at most gamma_n of the larger of ex and e. For n = 0
   there is nothing to bound, the sum a of the magnitudes being zero. *)
Lemma approx_gamma_bound :
  forall (ex e : R) (n : nat) (a c x : R),
  0 <= ex -> 0 <= e -> INR n * Rmax ex e < 1 -> 0 <= a -> (n = 0%nat -> a = 0) ->
  x <= ((1 + ex) * (1 + e) ^ (n - 1) - 1) * a + c ->
  x <= gamma n (Rmax ex e) * a + c.
Proof.
intros ex e n a c x Hex He Hn Ha H0 Hx.
destruct n as [|n].
- rewrite (H0 eq_refl) in Hx |- *. lra.
- replace (S n - 1)%nat with n in Hx by lia.
  generalize (prod_pow_gamma ex e n (S n) Hex He (le_n _) Hn). intros G.
  assert (K : ((1 + ex) * (1 + e) ^ n - 1) * a <= gamma (S n) (Rmax ex e) * a).
  { apply Rmult_le_compat_r; assumption. }
  lra.
Qed.

(** * The tree theorem *)

(* One node, in real numbers. v is the computed sum of va and vb, which are within the
   bound of the theorem of the exact sums Sl and Sr of their leaves, whose magnitudes
   sum to Tl and Tr. pl, pr and p are the powers of 1 + e for the two subtrees and for
   the taller of them. *)
Lemma node_bound :
  forall e v va vb Sl Sr Tl Tr pl pr p Al Ar s : R,
  0 <= e -> 0 <= Tl -> 0 <= Tr -> pl <= p -> pr <= p ->
  Rabs Sl <= Tl -> Rabs Sr <= Tr ->
  Rabs (va - Sl) <= (pl - 1) * Tl + Al ->
  Rabs (vb - Sr) <= (pr - 1) * Tr + Ar ->
  Rabs (v - (va + vb)) <= e * (Rabs va + Rabs vb) + s ->
  Rabs (v - (Sl + Sr)) <= ((1 + e) * p - 1) * (Tl + Tr) + ((1 + e) * (Al + Ar) + s).
Proof.
intros e v va vb Sl Sr Tl Tr pl pr p Al Ar s He HTl HTr Hpl Hpr HSl HSr Ha Hb Hv.
assert (Ha' : Rabs (va - Sl) <= (p - 1) * Tl + Al).
{ apply Rle_trans with (1 := Ha). apply Rplus_le_compat_r.
  apply Rmult_le_compat_r. exact HTl. lra. }
assert (Hb' : Rabs (vb - Sr) <= (p - 1) * Tr + Ar).
{ apply Rle_trans with (1 := Hb). apply Rplus_le_compat_r.
  apply Rmult_le_compat_r. exact HTr. lra. }
assert (Ma : Rabs va <= p * Tl + Al).
{ generalize (Rabs_triang Sl (va - Sl)). replace (Sl + (va - Sl)) with va by ring. lra. }
assert (Mb : Rabs vb <= p * Tr + Ar).
{ generalize (Rabs_triang Sr (vb - Sr)). replace (Sr + (vb - Sr)) with vb by ring. lra. }
assert (Ea : e * Rabs va <= e * (p * Tl + Al)) by (apply Rmult_le_compat_l; assumption).
assert (Eb : e * Rabs vb <= e * (p * Tr + Ar)) by (apply Rmult_le_compat_l; assumption).
replace (v - (Sl + Sr)) with ((v - (va + vb)) + ((va - Sl) + (vb - Sr))) by ring.
apply Rle_trans with (1 := Rabs_triang _ _).
generalize (Rabs_triang (va - Sl) (vb - Sr)). lra.
Qed.

(* A bound on the error gives a bound on the magnitude. *)
Lemma abs_from_error :
  forall v sm t p a : R,
  Rabs sm <= t -> Rabs (v - sm) <= (p - 1) * t + a -> Rabs v <= p * t + a.
Proof.
intros v sm t p a Hs Hv.
generalize (Rabs_triang sm (v - sm)). replace (sm + (v - sm)) with v by ring. lra.
Qed.

Lemma Rabs_le_add : forall a b : R, Rabs a <= Rabs b + Rabs (a - b).
Proof.
intros a b. generalize (Rabs_triang b (a - b)).
replace (b + (a - b)) with a by ring. intros H. exact H.
Qed.

(* Leaves within ex |t| + tau of real numbers t: what it does to the two sums. *)
Lemma approx_combine :
  forall v sp ap st ta ex p n : R,
  1 <= p ->
  Rabs (v - sp) <= (p - 1) * ap ->
  Rabs (sp - st) <= ex * ta + n ->
  ap <= (1 + ex) * ta + n ->
  Rabs (v - st) <= ((1 + ex) * p - 1) * ta + p * n.
Proof.
intros v sp ap st ta ex p n Hp Hv Hs Ha.
assert (K : (p - 1) * ap <= (p - 1) * ((1 + ex) * ta + n)).
{ apply Rmult_le_compat_l. lra. exact Ha. }
replace (v - st) with ((v - sp) + (sp - st)) by ring.
apply Rle_trans with (1 := Rabs_triang _ _). lra.
Qed.

Section TreeSum.
Variable V : Type.
Variable val : V -> R.
Variable valid : V -> Prop.
Variable op : V -> V -> V.

(* The hypothesis on the addition: for valid operands the result is valid, and its
   error is at most eps times the sum of the magnitudes of the operands. *)
Definition adds (eps : R) : Prop :=
  forall a b : V, valid a -> valid b ->
  valid (op a b) /\
  Rabs (val (op a b) - (val a + val b)) <= eps * (Rabs (val a) + Rabs (val b)).

(* The same with an absolute error tau at every addition. *)
Definition adds_tau (eps tau : R) : Prop :=
  forall a b : V, valid a -> valid b ->
  valid (op a b) /\
  Rabs (val (op a b) - (val a + val b)) <= eps * (Rabs (val a) + Rabs (val b)) + tau.

(* The same with an absolute error that the operands bring: an operand x costs w x,
   which is not negative, and the result of an addition costs nothing when it is an
   operand in turn. *)
Definition adds_weighted (eps : R) (w : V -> R) : Prop :=
  (forall a : V, valid a -> 0 <= w a) /\
  forall a b : V, valid a -> valid b ->
  valid (op a b) /\ w (op a b) = 0 /\
  Rabs (val (op a b) - (val a + val b)) <= eps * (Rabs (val a) + Rabs (val b)) + (w a + w b).

(* The general form: an absolute error that is any function of the two operands. *)
Definition adds_slack (eps : R) (slack : V -> V -> R) : Prop :=
  forall a b : V, valid a -> valid b ->
  valid (op a b) /\
  Rabs (val (op a b) - (val a + val b)) <= eps * (Rabs (val a) + Rabs (val b)) + slack a b.

(* What the absolute errors of the nodes of a tree add up to: each is multiplied by
   1 + eps at every addition above it. *)
Fixpoint abs_term (eps : R) (slack : V -> V -> R) (t : tree V) : R :=
  match t with
  | Leaf _ => 0
  | Node l r =>
      (1 + eps) * (abs_term eps slack l + abs_term eps slack r) + slack (eval op l) (eval op r)
  end.

Lemma eval_valid :
  (forall a b : V, valid a -> valid b -> valid (op a b)) ->
  forall t : tree V, Forall valid (leaves t) -> valid (eval op t).
Proof.
intros Hop. induction t as [x|l IHl r IHr]; cbn [leaves eval]; intros Hv.
- exact (Forall_inv Hv).
- apply Forall_app in Hv. destruct Hv as [Hl Hr]. apply Hop; auto.
Qed.

(* The error bound of the general form. By induction on the tree: a node adds eps times
   the magnitudes of its two computed operands, which are within the bound of their own
   subtrees, and its own absolute error. *)
Lemma tree_sum_general_error :
  forall (eps : R) (slack : V -> V -> R),
  0 <= eps -> adds_slack eps slack ->
  forall t : tree V, Forall valid (leaves t) ->
  valid (eval op t) /\
  Rabs (val (eval op t) - sumR (map val (leaves t))) <=
    ((1 + eps) ^ height t - 1) * sumabs (map val (leaves t)) + abs_term eps slack t.
Proof.
intros eps slack He Hop.
induction t as [x|l IHl r IHr]; intros Hv.
- cbn [leaves] in Hv. split.
  + exact (Forall_inv Hv).
  + cbn [eval leaves height abs_term map sumR pow].
    replace (val x - (val x + 0)) with 0 by ring. rewrite Rabs_R0. lra.
- cbn [leaves] in Hv. apply Forall_app in Hv. destruct Hv as [Hl Hr].
  destruct (IHl Hl) as [Vl El]. destruct (IHr Hr) as [Vr Er].
  destruct (Hop _ _ Vl Vr) as [Vo Eo].
  split. exact Vo.
  cbn [eval leaves height abs_term].
  rewrite map_app, sumR_app, sumabs_app, <- tech_pow_Rmult.
  assert (H1 : 1 <= 1 + eps) by lra.
  apply node_bound with (va := val (eval op l)) (vb := val (eval op r))
    (pl := (1 + eps) ^ height l) (pr := (1 + eps) ^ height r).
  + exact He.
  + apply sumabs_ge_0.
  + apply sumabs_ge_0.
  + apply Rle_pow. exact H1. apply Nat.le_max_l.
  + apply Rle_pow. exact H1. apply Nat.le_max_r.
  + apply sumR_le_sumabs.
  + apply sumR_le_sumabs.
  + exact El.
  + exact Er.
  + exact Eo.
Qed.

(* The tree theorem in its general form: every addition may commit, beyond its relative
   error, an absolute error slack a b that depends on its operands a and b. For a tree t
   with valid leaves: the value of t is valid; it is within
       ((1 + eps)^h - 1) (sum of the magnitudes of the leaves) + abs_term t
   of the exact sum of the leaves, where h is the height of t and abs_term t is what the
   absolute errors of its nodes add up to; and its magnitude is at most (1 + eps)^h times
   the sum of the magnitudes, plus abs_term t. *)
Theorem tree_sum_general :
  forall (eps : R) (slack : V -> V -> R),
  0 <= eps -> adds_slack eps slack ->
  forall t : tree V, Forall valid (leaves t) ->
  valid (eval op t) /\
  Rabs (val (eval op t) - sumR (map val (leaves t))) <=
    ((1 + eps) ^ height t - 1) * sumabs (map val (leaves t)) + abs_term eps slack t /\
  Rabs (val (eval op t)) <=
    (1 + eps) ^ height t * sumabs (map val (leaves t)) + abs_term eps slack t.
Proof.
intros eps slack He Hop t Hv.
destruct (tree_sum_general_error eps slack He Hop t Hv) as [Vt Et].
split. exact Vt. split. exact Et.
exact (abs_from_error _ _ _ _ _ (sumR_le_sumabs _) Et).
Qed.

Lemma abs_term_0 : forall (eps : R) (t : tree V), abs_term eps (fun _ _ => 0) t = 0.
Proof.
intros eps. induction t as [x|l IHl r IHr]; cbn [abs_term].
- reflexivity.
- rewrite IHl, IHr. ring.
Qed.

(* The tree theorem. For an addition of relative error eps and a tree t with valid
   leaves: the value of t is valid, it is within ((1 + eps)^h - 1) times the sum of the
   magnitudes of the leaves of their exact sum, and its magnitude is at most
   (1 + eps)^h times that sum of magnitudes; h is the height of t. *)
Theorem tree_sum :
  forall eps : R, 0 <= eps -> adds eps ->
  forall t : tree V, Forall valid (leaves t) ->
  valid (eval op t) /\
  Rabs (val (eval op t) - sumR (map val (leaves t))) <=
    ((1 + eps) ^ height t - 1) * sumabs (map val (leaves t)) /\
  Rabs (val (eval op t)) <= (1 + eps) ^ height t * sumabs (map val (leaves t)).
Proof.
intros eps He Hop t Hv.
assert (Hs : adds_slack eps (fun _ _ => 0)).
{ intros a b Va Vb. destruct (Hop a b Va Vb) as [Vo Eo]. split. exact Vo. cbv beta. lra. }
destruct (tree_sum_general eps _ He Hs t Hv) as [Vt [Et Mt]].
rewrite abs_term_0, Rplus_0_r in Et, Mt.
split. exact Vt. split. exact Et. exact Mt.
Qed.

(* With the same absolute error tau at every addition, the absolute errors add up to
   at most (1 + eps)^(h-1) times tau times the number of additions. *)
Lemma abs_term_tau :
  forall eps tau : R, 0 <= eps -> 0 <= tau ->
  forall t : tree V,
  (1 + eps) * abs_term eps (fun _ _ => tau) t <= (1 + eps) ^ height t * (INR (nodes t) * tau).
Proof.
intros eps tau He Ht. induction t as [x|l IHl r IHr].
- cbn [abs_term height nodes pow INR]. lra.
- cbn [abs_term height nodes]. rewrite <- tech_pow_Rmult, S_INR, plus_INR.
  set (p := (1 + eps) ^ Nat.max (height l) (height r)).
  assert (H1 : 1 <= 1 + eps) by lra.
  assert (Hp1 : 1 <= p) by (apply pow_R1_Rle; exact H1).
  assert (Nl : 0 <= INR (nodes l) * tau) by (apply Rmult_le_pos; [apply pos_INR | exact Ht]).
  assert (Nr : 0 <= INR (nodes r) * tau) by (apply Rmult_le_pos; [apply pos_INR | exact Ht]).
  assert (Kl : (1 + eps) ^ height l * (INR (nodes l) * tau) <= p * (INR (nodes l) * tau)).
  { apply Rmult_le_compat_r. exact Nl. apply Rle_pow. exact H1. apply Nat.le_max_l. }
  assert (Kr : (1 + eps) ^ height r * (INR (nodes r) * tau) <= p * (INR (nodes r) * tau)).
  { apply Rmult_le_compat_r. exact Nr. apply Rle_pow. exact H1. apply Nat.le_max_r. }
  assert (Kt : 0 <= (p - 1) * tau) by (apply Rmult_le_pos; lra).
  replace ((1 + eps) * p * ((INR (nodes l) + INR (nodes r) + 1) * tau))
    with ((1 + eps) * (p * (INR (nodes l) * tau) + p * (INR (nodes r) * tau) + p * tau)) by ring.
  apply Rmult_le_compat_l. lra. lra.
Qed.

(* The tree theorem with an absolute error tau at every addition. The absolute term is
   (1 + eps)^(h-1) times tau times the number of additions of the tree, which is its
   number of leaves less one. With tau = 0 this is tree_sum. *)
Theorem tree_sum_tau :
  forall eps tau : R, 0 <= eps -> 0 <= tau -> adds_tau eps tau ->
  forall t : tree V, Forall valid (leaves t) ->
  valid (eval op t) /\
  Rabs (val (eval op t) - sumR (map val (leaves t))) <=
    ((1 + eps) ^ height t - 1) * sumabs (map val (leaves t)) +
    (1 + eps) ^ (height t - 1) * (INR (nodes t) * tau) /\
  Rabs (val (eval op t)) <=
    (1 + eps) ^ height t * sumabs (map val (leaves t)) +
    (1 + eps) ^ (height t - 1) * (INR (nodes t) * tau).
Proof.
intros eps tau He Ht Hop t Hv.
assert (Hs : adds_slack eps (fun _ _ => tau)) by exact Hop.
assert (A : abs_term eps (fun _ _ => tau) t <= (1 + eps) ^ (height t - 1) * (INR (nodes t) * tau)).
{ destruct t as [x|l r].
  - cbn [abs_term height nodes INR]. lra.
  - generalize (abs_term_tau eps tau He Ht (Node l r)).
    cbn [height].
    replace (S (Nat.max (height l) (height r)) - 1)%nat
      with (Nat.max (height l) (height r)) by lia.
    rewrite <- tech_pow_Rmult. intros K.
    apply Rmult_le_reg_l with (1 + eps). lra.
    apply Rle_trans with (1 := K). right. ring. }
destruct (tree_sum_general eps _ He Hs t Hv) as [Vt [Et Mt]].
split. exact Vt. split; lra.
Qed.

(* With an absolute error that the operands bring, the absolute errors add up to at
   most (1 + eps)^(h-1) times the sum of what the leaves bring. *)
Lemma abs_term_weighted :
  forall (eps : R) (w : V -> R), 0 <= eps -> adds_weighted eps w ->
  forall t : tree V, Forall valid (leaves t) ->
  (1 + eps) * abs_term eps (fun a b => w a + w b) t + w (eval op t) <=
  (1 + eps) ^ height t * sumR (map w (leaves t)).
Proof.
intros eps w He [Hw Hop].
assert (Hval : forall a b : V, valid a -> valid b -> valid (op a b)).
{ intros a b Va Vb. exact (proj1 (Hop a b Va Vb)). }
induction t as [x|l IHl r IHr]; intros Hv.
- cbn [abs_term eval height leaves map sumR pow]. lra.
- cbn [leaves] in Hv. apply Forall_app in Hv. destruct Hv as [Hl Hr].
  specialize (IHl Hl). specialize (IHr Hr).
  destruct (Hop _ _ (eval_valid Hval l Hl) (eval_valid Hval r Hr)) as [_ [W0 _]].
  cbn [abs_term eval height leaves]. rewrite W0, map_app, sumR_app, <- tech_pow_Rmult.
  set (p := (1 + eps) ^ Nat.max (height l) (height r)).
  assert (H1 : 1 <= 1 + eps) by lra.
  assert (Kl : (1 + eps) ^ height l * sumR (map w (leaves l)) <= p * sumR (map w (leaves l))).
  { apply Rmult_le_compat_r. apply (sumR_map_ge_0 _ valid); assumption.
    apply Rle_pow. exact H1. apply Nat.le_max_l. }
  assert (Kr : (1 + eps) ^ height r * sumR (map w (leaves r)) <= p * sumR (map w (leaves r))).
  { apply Rmult_le_compat_r. apply (sumR_map_ge_0 _ valid); assumption.
    apply Rle_pow. exact H1. apply Nat.le_max_r. }
  replace ((1 + eps) * p * (sumR (map w (leaves l)) + sumR (map w (leaves r))))
    with ((1 + eps) * (p * sumR (map w (leaves l)) + p * sumR (map w (leaves r)))) by ring.
  rewrite Rplus_0_r. apply Rmult_le_compat_l. lra. lra.
Qed.

(* The tree theorem with an absolute error that the operands bring. The absolute term
   is (1 + eps)^(h-1) times the sum of w over the leaves: an addition whose operands
   are both results of additions adds nothing to it. With w = 0 this is tree_sum. *)
Theorem tree_sum_weighted :
  forall (eps : R) (w : V -> R), 0 <= eps -> adds_weighted eps w ->
  forall t : tree V, Forall valid (leaves t) ->
  valid (eval op t) /\
  Rabs (val (eval op t) - sumR (map val (leaves t))) <=
    ((1 + eps) ^ height t - 1) * sumabs (map val (leaves t)) +
    (1 + eps) ^ (height t - 1) * sumR (map w (leaves t)) /\
  Rabs (val (eval op t)) <=
    (1 + eps) ^ height t * sumabs (map val (leaves t)) +
    (1 + eps) ^ (height t - 1) * sumR (map w (leaves t)).
Proof.
intros eps w He Hop t Hv.
assert (Hs : adds_slack eps (fun a b => w a + w b)).
{ intros a b Va Vb. destruct (proj2 Hop a b Va Vb) as [Vo [_ Eo]]. split; assumption. }
assert (A : abs_term eps (fun a b => w a + w b) t <=
            (1 + eps) ^ (height t - 1) * sumR (map w (leaves t))).
{ destruct t as [x|l r].
  - cbn [leaves] in Hv. cbn [abs_term height leaves map sumR].
    change (0 - 1)%nat with 0%nat. cbn [pow].
    generalize (proj1 Hop x (Forall_inv Hv)). lra.
  - cbn [leaves] in Hv. apply Forall_app in Hv. destruct Hv as [Hl Hr].
    generalize (abs_term_weighted eps w He Hop l Hl).
    generalize (abs_term_weighted eps w He Hop r Hr).
    cbn [abs_term height leaves]. rewrite map_app, sumR_app.
    replace (S (Nat.max (height l) (height r)) - 1)%nat
      with (Nat.max (height l) (height r)) by lia.
    set (p := (1 + eps) ^ Nat.max (height l) (height r)).
    assert (H1 : 1 <= 1 + eps) by lra.
    assert (Kl : (1 + eps) ^ height l * sumR (map w (leaves l)) <= p * sumR (map w (leaves l))).
    { apply Rmult_le_compat_r. apply (sumR_map_ge_0 _ valid). exact (proj1 Hop). exact Hl.
      apply Rle_pow. exact H1. apply Nat.le_max_l. }
    assert (Kr : (1 + eps) ^ height r * sumR (map w (leaves r)) <= p * sumR (map w (leaves r))).
    { apply Rmult_le_compat_r. apply (sumR_map_ge_0 _ valid). exact (proj1 Hop). exact Hr.
      apply Rle_pow. exact H1. apply Nat.le_max_r. }
    intros Ir Il. lra. }
destruct (tree_sum_general eps _ He Hs t Hv) as [Vt [Et Mt]].
split. exact Vt. split; lra.
Qed.

(** * Leaves that are approximate *)

(* If every element p of a list is within ex |t| + tau of a real number t, then the sum
   of the list is within ex sum |t| + n tau of the sum of those numbers, and the sum of
   its magnitudes is at most (1 + ex) sum |t| + n tau. *)
Lemma approx_sums :
  forall (ex tau : R) (ps : list V) (ts : list R),
  Forall2 (fun p t => Rabs (val p - t) <= ex * Rabs t + tau) ps ts ->
  Rabs (sumR (map val ps) - sumR ts) <= ex * sumabs ts + INR (length ts) * tau /\
  sumabs (map val ps) <= (1 + ex) * sumabs ts + INR (length ts) * tau.
Proof.
intros ex tau ps ts H. induction H as [|p t ps ts Hpt _ [IH1 IH2]].
- unfold sumabs. cbn [map sumR length INR]. rewrite Rminus_0_r, Rabs_R0. split; lra.
- cbn [map sumR length]. rewrite !sumabs_cons, S_INR. split.
  + replace (val p + sumR (map val ps) - (t + sumR ts))
      with ((val p - t) + (sumR (map val ps) - sumR ts)) by ring.
    apply Rle_trans with (1 := Rabs_triang _ _). lra.
  + generalize (Rabs_le_add (val p) t). lra.
Qed.

(* From a bound of a computed sum against its own operands to a bound against the
   numbers that the operands approximate. p stands for (1 + eps)^h. *)
Lemma approx_from_sum :
  forall (ex tau v : R) (ps : list V) (ts : list R) (p : R),
  1 <= p ->
  Forall2 (fun q t => Rabs (val q - t) <= ex * Rabs t + tau) ps ts ->
  Rabs (v - sumR (map val ps)) <= (p - 1) * sumabs (map val ps) ->
  Rabs (v - sumR ts) <= ((1 + ex) * p - 1) * sumabs ts + p * (INR (length ts) * tau).
Proof.
intros ex tau v ps ts p Hp Ha Hv.
destruct (approx_sums ex tau ps ts Ha) as [S1 S2].
exact (approx_combine _ _ _ _ _ _ _ _ Hp Hv S1 S2).
Qed.

(* The tree theorem for approximate leaves. If the leaves of t are valid and leaf i is
   within eps_x |t_i| + tau of a real number t_i, then the value of t is within
       ((1 + eps_x) (1 + eps)^h - 1) sum |t_i| + (1 + eps)^h n tau
   of the sum of the t_i, where n is their number. *)
Theorem tree_sum_approx :
  forall eps eps_x tau : R, 0 <= eps -> adds eps ->
  forall (t : tree V) (ts : list R),
  Forall valid (leaves t) ->
  Forall2 (fun p r => Rabs (val p - r) <= eps_x * Rabs r + tau) (leaves t) ts ->
  Rabs (val (eval op t) - sumR ts) <=
    ((1 + eps_x) * (1 + eps) ^ height t - 1) * sumabs ts +
    (1 + eps) ^ height t * (INR (length ts) * tau).
Proof.
intros eps eps_x tau He Hop t ts Hv Ha.
destruct (tree_sum eps He Hop t Hv) as [_ [Et _]].
apply approx_from_sum with (ps := leaves t).
- apply pow_R1_Rle. lra.
- exact Ha.
- exact Et.
Qed.

(* The same in closed form: the first factor is at most gamma_n of the larger of eps_x
   and eps, because a tree with n leaves has height at most n - 1. *)
Theorem tree_sum_approx_gamma :
  forall eps eps_x tau : R, 0 <= eps -> 0 <= eps_x -> adds eps ->
  forall (t : tree V) (ts : list R),
  Forall valid (leaves t) ->
  Forall2 (fun p r => Rabs (val p - r) <= eps_x * Rabs r + tau) (leaves t) ts ->
  INR (length ts) * Rmax eps_x eps < 1 ->
  Rabs (val (eval op t) - sumR ts) <=
    gamma (length ts) (Rmax eps_x eps) * sumabs ts +
    (1 + eps) ^ height t * (INR (length ts) * tau).
Proof.
intros eps eps_x tau He Hex Hop t ts Hv Ha Hn.
generalize (tree_sum_approx eps eps_x tau He Hop t ts Hv Ha).
assert (Hh : (S (height t) <= length ts)%nat).
{ rewrite <- (Forall2_length Ha), leaves_length. generalize (height_le_nodes _ t). lia. }
generalize (prod_pow_gamma eps_x eps (height t) (length ts) Hex He Hh Hn).
generalize (sumabs_ge_0 ts). intros HA HG HT.
assert (K : ((1 + eps_x) * (1 + eps) ^ height t - 1) * sumabs ts <=
            gamma (length ts) (Rmax eps_x eps) * sumabs ts).
{ apply Rmult_le_compat_r; assumption. }
lra.
Qed.

End TreeSum.

Arguments adds {V} val valid op eps.
Arguments adds_tau {V} val valid op eps tau.
Arguments adds_weighted {V} val valid op eps w.
Arguments adds_slack {V} val valid op eps slack.
Arguments abs_term {V} op eps slack t.

(** * The two orders are trees *)

(* The heights of the two orders are at most n - 1, for n elements. *)
Lemma lanes_height_le :
  forall n W : nat, (0 < W <= n)%nat -> (n / W + (W - 1) + n mod W - 1 <= n - 1)%nat.
Proof.
intros n W H.
assert (Q : (0 < n / W)%nat) by (apply Nat.div_str_pos; lia).
generalize (Nat.div_mod_eq n W). nia.
Qed.

Lemma lanes_height_zero_le :
  forall n W : nat, (0 < W <= n)%nat -> (n / W + (W - 1) + n mod W <= n)%nat.
Proof.
intros n W H.
assert (Q : (0 < n / W)%nat) by (apply Nat.div_str_pos; lia).
generalize (Nat.div_mod_eq n W). nia.
Qed.

Section Orders.
Variable V : Type.
Variable val : V -> R.
Variable valid : V -> Prop.
Variable op : V -> V -> V.
Variable zero : V.

(* s is the value of a tree with the leaves ls, from left to right, and the height h. *)
Definition is_tree (s : V) (ls : list V) (h : nat) : Prop :=
  exists t : tree V, eval op t = s /\ leaves t = ls /\ height t = h.

Lemma is_tree_leaf : forall x : V, is_tree x [x] 0.
Proof. intros x. exists (Leaf x). repeat split. Qed.

(* Adding the elements of a list one after the other puts one addition above the tree
   for each. *)
Lemma is_tree_fold :
  forall (xs : list V) (s : V) (ls : list V) (h : nat),
  is_tree s ls h -> is_tree (fold_left op xs s) (ls ++ xs) (h + length xs).
Proof.
induction xs as [|x r IH]; intros s ls h [t [He [Hl Hh]]].
- cbn [fold_left length]. rewrite app_nil_r, Nat.add_0_r. exists t. auto.
- cbn [fold_left length].
  replace (ls ++ x :: r) with ((ls ++ [x]) ++ r) by (rewrite <- app_assoc; reflexivity).
  replace (h + S (length r))%nat with (S h + length r)%nat by lia.
  apply IH. exists (Node t (Leaf x)). cbn [eval leaves height].
  rewrite He, Hl, Hh, Nat.max_0_r. auto.
Qed.

(* Combining trees of the same height h, from the first upward, with a tree at least
   as high: one addition above the first for each of the others. *)
Lemma is_tree_combine :
  forall (h : nat) (ss : list V) (lls : list (list V)),
  Forall2 (fun s l => is_tree s l h) ss lls ->
  forall (s0 : V) (l0 : list V) (h0 : nat),
  (h <= h0)%nat -> is_tree s0 l0 h0 ->
  is_tree (fold_left op ss s0) (l0 ++ concat lls) (h0 + length ss).
Proof.
intros h ss lls H.
induction H as [|s l ss lls [t [He [Hl Hh]]] _ IH]; intros s0 l0 h0 Hle [t0 [He0 [Hl0 Hh0]]].
- cbn [fold_left concat length]. rewrite app_nil_r, Nat.add_0_r. exists t0. auto.
- cbn [fold_left concat length]. rewrite app_assoc.
  replace (h0 + S (length ss))%nat with (S h0 + length ss)%nat by lia.
  apply IH. lia.
  exists (Node t0 t). cbn [eval leaves height].
  rewrite He0, He, Hl0, Hl, Hh0, Hh, Nat.max_l by exact Hle. auto.
Qed.

(* The sequential order from any state s: the state is a leaf, and each of the n
   elements is one addition above it. *)
Lemma fold_left_is_tree :
  forall (xs : list V) (s : V), is_tree (fold_left op xs s) (s :: xs) (length xs).
Proof. intros xs s. exact (is_tree_fold xs s [s] 0 (is_tree_leaf s)). Qed.

(* The lane order, given a tree for each lane: L l are the leaves of the tree of the
   lane l, and all those trees have the height hq. *)
Lemma fold_lanes_is_tree :
  forall (L : list V -> list V) (hq W : nat) (xs : list V),
  (0 < W)%nat ->
  Forall (fun l => is_tree (fold_seq op zero l) (L l) hq)
         (deal W (firstn (W * (length xs / W)) xs)) ->
  is_tree (fold_lanes op op zero W xs)
          (concat (map L (deal W (firstn (W * (length xs / W)) xs))) ++
           skipn (W * (length xs / W)) xs)
          (hq + (W - 1) + length (skipn (W * (length xs / W)) xs)).
Proof.
intros L hq W xs HW HL. unfold fold_lanes. revert HL.
generalize (deal_length _ W (firstn (W * (length xs / W)) xs)).
destruct (deal W (firstn (W * (length xs / W)) xs)) as [|l0 ls]; cbn [length]; intros Hlen HL.
- lia.
- apply is_tree_fold. unfold combine_lanes. cbn [map hd tl concat].
  replace (W - 1)%nat with (length (map (fold_seq op zero) ls)) by (rewrite length_map; lia).
  apply is_tree_combine with (h := hq).
  + apply Forall_inv_tail in HL. clear -HL.
    induction HL as [|l ls Hl _ IH]; cbn [map]; constructor; assumption.
  + lia.
  + exact (Forall_inv HL).
Qed.

(* The sequential order, with the zero state as a leaf: a tree whose leaves are zero
   and the n elements, of height n. This is the form for a step in which the first
   addition, to the zero state, is rounded like the others. *)
Theorem fold_seq_tree_zero :
  forall xs : list V,
  exists t : tree V,
    eval op t = fold_seq op zero xs /\ leaves t = zero :: xs /\ height t = length xs.
Proof. intros xs. exact (fold_left_is_tree xs zero). Qed.

(* The lane order, with the zero states as leaves: a tree whose leaves are W times zero
   and the n elements, of height n / W + (W - 1) + n mod W. *)
Theorem fold_lanes_tree_zero :
  forall (W : nat) (xs : list V), (0 < W)%nat ->
  exists t : tree V,
    eval op t = fold_lanes op op zero W xs /\
    Permutation (leaves t) (repeat zero W ++ xs) /\
    height t = (length xs / W + (W - 1) + length xs mod W)%nat.
Proof.
intros W xs HW.
pose proof (Nat.div_mod_eq (length xs) W) as Hdm.
assert (Hb : length (firstn (W * (length xs / W)) xs) = (W * (length xs / W))%nat).
{ rewrite length_firstn. lia. }
assert (HF : Forall (fun l => is_tree (fold_seq op zero l) (cons zero l) (length xs / W))
                    (deal W (firstn (W * (length xs / W)) xs))).
{ unfold deal. apply Forall_map. apply Forall_forall. intros j Hj. apply in_seq in Hj.
  pose proof (fold_left_is_tree (lane W j (firstn (W * (length xs / W)) xs)) zero) as T.
  rewrite (lane_length_full _ W (length xs / W) _ j) in T by (lia || exact Hb).
  exact T. }
destruct (fold_lanes_is_tree (cons zero) (length xs / W) W xs HW HF) as [t [He [Hl Hh]]].
exists t. split. exact He. split.
- rewrite Hl.
  apply Permutation_trans with
    ((repeat zero W ++ firstn (W * (length xs / W)) xs) ++ skipn (W * (length xs / W)) xs).
  + apply Permutation_app_tail.
    apply Permutation_trans with (1 := concat_cons_perm _ zero _).
    rewrite deal_length. apply Permutation_app_head. now apply deal_perm.
  + rewrite <- app_assoc, firstn_skipn. apply Permutation_refl.
- rewrite Hh, length_skipn. lia.
Qed.

(* When adding to the zero state returns the value of the other operand, the zero state
   need not be a leaf: the first addition of the loop, op zero x, is taken as the leaf.
   absorb l are the leaves of the sequential order of a list l that is not empty. *)
Definition absorb (l : list V) : list V :=
  match l with
  | [] => []
  | x :: r => op zero x :: r
  end.

Lemma fold_seq_absorb :
  forall l : list V, l <> [] -> is_tree (fold_seq op zero l) (absorb l) (length l - 1).
Proof.
intros l Hl. destruct l as [|x r]. congruence.
unfold fold_seq. cbn [fold_left absorb length].
replace (S (length r) - 1)%nat with (length r) by lia.
exact (is_tree_fold r (op zero x) [op zero x] 0 (is_tree_leaf (op zero x))).
Qed.

Section ZeroLeft.
Hypothesis zero_left :
  forall x : V, valid x -> valid (op zero x) /\ val (op zero x) = val x.

Lemma absorb_valid : forall l : list V, Forall valid l -> Forall valid (absorb l).
Proof.
intros l H. destruct H as [|x r Hx Hr]; cbn [absorb]; constructor.
- exact (proj1 (zero_left x Hx)).
- exact Hr.
Qed.

Lemma absorb_val : forall l : list V, Forall valid l -> map val (absorb l) = map val l.
Proof.
intros l H. destruct H as [|x r Hx Hr]; cbn [absorb map].
- reflexivity.
- now rewrite (proj2 (zero_left x Hx)).
Qed.

(* The sequential order of n >= 1 valid elements is a tree with valid leaves that have
   the values of the elements, in their order, and of height n - 1. *)
Theorem fold_seq_tree :
  forall xs : list V, xs <> [] -> Forall valid xs ->
  exists t : tree V,
    eval op t = fold_seq op zero xs /\ Forall valid (leaves t) /\
    map val (leaves t) = map val xs /\ height t = (length xs - 1)%nat.
Proof.
intros xs Hne Hv. destruct (fold_seq_absorb xs Hne) as [t [He [Hl Hh]]].
exists t. split. exact He. rewrite Hl. split. now apply absorb_valid.
split. now apply absorb_val. exact Hh.
Qed.

(* The lane order of n >= W >= 1 valid elements is a tree with valid leaves that have
   the values of the elements, each once, and of height n / W + (W - 1) + n mod W - 1:
   n / W - 1 additions in a lane, W - 1 to combine the lanes, n mod W for the rest. *)
Theorem fold_lanes_tree :
  forall (W : nat) (xs : list V), (0 < W <= length xs)%nat -> Forall valid xs ->
  exists t : tree V,
    eval op t = fold_lanes op op zero W xs /\ Forall valid (leaves t) /\
    Permutation (map val (leaves t)) (map val xs) /\
    height t = (length xs / W + (W - 1) + length xs mod W - 1)%nat.
Proof.
intros W xs [HW Hn] Hv.
pose proof (Nat.div_mod_eq (length xs) W) as Hdm.
assert (Hq : (0 < length xs / W)%nat) by (apply Nat.div_str_pos; lia).
assert (Hb : length (firstn (W * (length xs / W)) xs) = (W * (length xs / W))%nat).
{ rewrite length_firstn. lia. }
rewrite <- (firstn_skipn (W * (length xs / W)) xs) in Hv.
apply Forall_app in Hv. destruct Hv as [Hvb Hvr].
assert (Hlanes : Forall (fun l => length l = (length xs / W)%nat /\ Forall valid l)
                        (deal W (firstn (W * (length xs / W)) xs))).
{ unfold deal. apply Forall_map. apply Forall_forall. intros j Hj. apply in_seq in Hj.
  cbv beta. split.
  - apply lane_length_full. lia. exact Hb.
  - apply lane_Forall. exact Hvb. }
assert (HF : Forall (fun l => is_tree (fold_seq op zero l) (absorb l) (length xs / W - 1))
                    (deal W (firstn (W * (length xs / W)) xs))).
{ revert Hlanes. apply Forall_impl. intros l [Hll _].
  pose proof (fold_seq_absorb l) as T. rewrite Hll in T. apply T.
  intros E. rewrite E in Hll. cbn [length] in Hll. lia. }
destruct (fold_lanes_is_tree absorb (length xs / W - 1) W xs HW HF) as [t [He [Hl Hh]]].
exists t. split. exact He. rewrite Hl. split; [|split].
- apply Forall_app. split; [|exact Hvr].
  apply Forall_concat. apply Forall_map. revert Hlanes. apply Forall_impl.
  intros l [_ Hl']. now apply absorb_valid.
- assert (E : map val (concat (map absorb (deal W (firstn (W * (length xs / W)) xs)))) =
              map val (concat (deal W (firstn (W * (length xs / W)) xs)))).
  { rewrite !concat_map, map_map. f_equal. apply map_ext_in. intros l Hin.
    apply absorb_val. exact (proj2 (proj1 (Forall_forall _ _) Hlanes l Hin)). }
  rewrite map_app, E, <- map_app. apply Permutation_map.
  apply Permutation_trans with
    (firstn (W * (length xs / W)) xs ++ skipn (W * (length xs / W)) xs).
  + apply Permutation_app_tail. now apply deal_perm.
  + rewrite firstn_skipn. apply Permutation_refl.
- rewrite Hh, length_skipn. lia.
Qed.

End ZeroLeft.

(** * The bounds of the two orders *)

(* The zero state of a sum: it is valid, its value is zero, the addition leaves it
   fixed, and adding a valid x to it gives a result of the value of x. *)
Definition zero_identity : Prop :=
  valid zero /\ val zero = 0 /\ op zero zero = zero /\
  forall x : V, valid x -> val (op zero x) = val x.

Lemma zero_identity_left :
  forall eps : R, adds val valid op eps -> zero_identity ->
  forall x : V, valid x -> valid (op zero x) /\ val (op zero x) = val x.
Proof.
intros eps Hop [Z0 [_ [_ Z3]]] x Vx. split.
- exact (proj1 (Hop zero x Z0 Vx)).
- now apply Z3.
Qed.

(* The bound of tree_sum for a tree whose leaves have the values of a list, in any
   order, and whose height is at most h. *)
Lemma sum_of_tree :
  forall eps : R, 0 <= eps -> adds val valid op eps ->
  forall (t : tree V) (xs : list V) (h : nat),
  Forall valid (leaves t) -> Permutation (map val (leaves t)) (map val xs) ->
  (height t <= h)%nat ->
  valid (eval op t) /\
  Rabs (val (eval op t) - sumR (map val xs)) <= ((1 + eps) ^ h - 1) * sumabs (map val xs) /\
  Rabs (val (eval op t)) <= (1 + eps) ^ h * sumabs (map val xs).
Proof.
intros eps He Hop t xs h Hv Hp Hh.
destruct (tree_sum V val valid op eps He Hop t Hv) as [Vt [Et Mt]].
rewrite (sumR_perm _ _ Hp), (sumabs_perm _ _ Hp) in Et.
rewrite (sumabs_perm _ _ Hp) in Mt.
assert (HA := sumabs_ge_0 (map val xs)).
assert (K : (1 + eps) ^ height t * sumabs (map val xs) <= (1 + eps) ^ h * sumabs (map val xs)).
{ apply Rmult_le_compat_r. exact HA. apply Rle_pow. lra. exact Hh. }
split. exact Vt. split; lra.
Qed.

(* A sum in the sequential order. For n valid elements, the result s of the loop
   s <- op s x from the zero state is valid, within ((1 + eps)^(n-1) - 1) times the sum
   of the magnitudes of the exact sum, and at most (1 + eps)^(n-1) times that sum in
   magnitude. The empty list gives the zero state. *)
Theorem fold_seq_sum :
  forall eps : R, 0 <= eps -> adds val valid op eps -> zero_identity ->
  forall xs : list V, Forall valid xs ->
  let s := fold_seq op zero xs in
  valid s /\
  Rabs (val s - sumR (map val xs)) <= ((1 + eps) ^ (length xs - 1) - 1) * sumabs (map val xs) /\
  Rabs (val s) <= (1 + eps) ^ (length xs - 1) * sumabs (map val xs).
Proof.
intros eps He Hop Hzi xs Hv. cbv zeta.
destruct xs as [|x r].
- destruct Hzi as [Z0 [Z1 _]]. unfold fold_seq, sumabs. cbn [fold_left map sumR length].
  rewrite Z1, Rminus_0_r, Rabs_R0. split. exact Z0. split; lra.
- assert (Hne : x :: r <> []) by discriminate.
  destruct (fold_seq_tree (zero_identity_left eps Hop Hzi) (x :: r) Hne Hv)
    as [t [Et [Vt [Mt Ht]]]].
  rewrite <- Et. apply sum_of_tree; try assumption.
  + rewrite Mt. apply Permutation_refl.
  + lia.
Qed.

(* A sum in the lane order, with the exact height of the order, for n >= W >= 1. *)
Theorem fold_lanes_sum_height :
  forall eps : R, 0 <= eps -> adds val valid op eps -> zero_identity ->
  forall (W : nat) (xs : list V), (0 < W <= length xs)%nat -> Forall valid xs ->
  let s := fold_lanes op op zero W xs in
  let h := (length xs / W + (W - 1) + length xs mod W - 1)%nat in
  valid s /\
  Rabs (val s - sumR (map val xs)) <= ((1 + eps) ^ h - 1) * sumabs (map val xs) /\
  Rabs (val s) <= (1 + eps) ^ h * sumabs (map val xs).
Proof.
intros eps He Hop Hzi W xs HW Hv. cbv zeta.
destruct (fold_lanes_tree (zero_identity_left eps Hop Hzi) W xs HW Hv) as [t [Et [Vt [Pt Ht]]]].
rewrite <- Et, <- Ht. apply sum_of_tree; auto.
Qed.

(* A sum in the lane order, for every width and every list: the bound of the
   sequential order. For n >= W >= 1 the height of the order is at most n - 1; for
   n < W, and for W = 0, the lane order is the sequential order. *)
Theorem fold_lanes_sum :
  forall eps : R, 0 <= eps -> adds val valid op eps -> zero_identity ->
  forall (W : nat) (xs : list V), Forall valid xs ->
  let s := fold_lanes op op zero W xs in
  valid s /\
  Rabs (val s - sumR (map val xs)) <= ((1 + eps) ^ (length xs - 1) - 1) * sumabs (map val xs) /\
  Rabs (val s) <= (1 + eps) ^ (length xs - 1) * sumabs (map val xs).
Proof.
intros eps He Hop Hzi W xs Hv. cbv zeta.
destruct (Nat.eq_dec W 0) as [HW0|HW0].
- subst W. rewrite fold_lanes_0. exact (fold_seq_sum eps He Hop Hzi xs Hv).
- destruct (Nat.lt_ge_cases (length xs) W) as [Hlt|Hge].
  + rewrite (fold_lanes_short _ _ op op zero W xs (proj1 (proj2 (proj2 Hzi))) Hlt).
    exact (fold_seq_sum eps He Hop Hzi xs Hv).
  + assert (HW : (0 < W <= length xs)%nat) by lia.
    destruct (fold_lanes_tree (zero_identity_left eps Hop Hzi) W xs HW Hv)
      as [t [Et [Vt [Pt Ht]]]].
    rewrite <- Et. apply sum_of_tree; try assumption.
    rewrite Ht. apply lanes_height_le. lia.
Qed.

(* The same two bounds in closed form: within gamma_(n-1)(eps) times the sum of the
   magnitudes, when (n - 1) eps < 1. *)
Theorem fold_seq_sum_gamma :
  forall eps : R, 0 <= eps -> adds val valid op eps -> zero_identity ->
  forall xs : list V, Forall valid xs ->
  INR (length xs - 1) * eps < 1 ->
  let s := fold_seq op zero xs in
  valid s /\
  Rabs (val s - sumR (map val xs)) <= gamma (length xs - 1) eps * sumabs (map val xs).
Proof.
intros eps He Hop Hzi xs Hv Hn. cbv zeta.
destruct (fold_seq_sum eps He Hop Hzi xs Hv) as [Vs [Es _]].
split. exact Vs.
exact (gamma_bound_0 eps (length xs - 1) (length xs - 1) _ _ He (le_n _) Hn
         (sumabs_ge_0 (map val xs)) Es).
Qed.

(* The closed form in the lane order, for every width W. *)
Theorem fold_lanes_sum_gamma :
  forall eps : R, 0 <= eps -> adds val valid op eps -> zero_identity ->
  forall (W : nat) (xs : list V), Forall valid xs ->
  INR (length xs - 1) * eps < 1 ->
  let s := fold_lanes op op zero W xs in
  valid s /\
  Rabs (val s - sumR (map val xs)) <= gamma (length xs - 1) eps * sumabs (map val xs).
Proof.
intros eps He Hop Hzi W xs Hv Hn. cbv zeta.
destruct (fold_lanes_sum eps He Hop Hzi W xs Hv) as [Vs [Es _]].
split. exact Vs.
exact (gamma_bound_0 eps (length xs - 1) (length xs - 1) _ _ He (le_n _) Hn
         (sumabs_ge_0 (map val xs)) Es).
Qed.

(* A sum of approximate terms, in the sequential order: the dot product. The valid
   values ps are added; element i is within eps_x |t_i| + tau of a real number t_i.
   The result is within
       ((1 + eps_x) (1 + eps)^(n-1) - 1) sum |t_i| + (1 + eps)^(n-1) n tau
   of the sum of the t_i. *)
Theorem fold_seq_sum_approx :
  forall eps eps_x tau : R, 0 <= eps -> adds val valid op eps -> zero_identity ->
  forall (ps : list V) (ts : list R), Forall valid ps ->
  Forall2 (fun p r => Rabs (val p - r) <= eps_x * Rabs r + tau) ps ts ->
  let s := fold_seq op zero ps in
  valid s /\
  Rabs (val s - sumR ts) <=
    ((1 + eps_x) * (1 + eps) ^ (length ts - 1) - 1) * sumabs ts +
    (1 + eps) ^ (length ts - 1) * (INR (length ts) * tau).
Proof.
intros eps eps_x tau He Hop Hzi ps ts Hv Ha. cbv zeta.
destruct (fold_seq_sum eps He Hop Hzi ps Hv) as [Vs [Es _]].
split. exact Vs.
rewrite (Forall2_length Ha) in Es.
apply (approx_from_sum V val eps_x tau _ ps ts ((1 + eps) ^ (length ts - 1))).
- apply pow_R1_Rle. lra.
- exact Ha.
- exact Es.
Qed.

(* The same in the lane order, for every width. *)
Theorem fold_lanes_sum_approx :
  forall eps eps_x tau : R, 0 <= eps -> adds val valid op eps -> zero_identity ->
  forall (W : nat) (ps : list V) (ts : list R), Forall valid ps ->
  Forall2 (fun p r => Rabs (val p - r) <= eps_x * Rabs r + tau) ps ts ->
  let s := fold_lanes op op zero W ps in
  valid s /\
  Rabs (val s - sumR ts) <=
    ((1 + eps_x) * (1 + eps) ^ (length ts - 1) - 1) * sumabs ts +
    (1 + eps) ^ (length ts - 1) * (INR (length ts) * tau).
Proof.
intros eps eps_x tau He Hop Hzi W ps ts Hv Ha. cbv zeta.
destruct (fold_lanes_sum eps He Hop Hzi W ps Hv) as [Vs [Es _]].
split. exact Vs.
rewrite (Forall2_length Ha) in Es.
apply (approx_from_sum V val eps_x tau _ ps ts ((1 + eps) ^ (length ts - 1))).
- apply pow_R1_Rle. lra.
- exact Ha.
- exact Es.
Qed.

(* The sums of a function that is zero at the zero state do not see leaves that are
   the zero state. *)
Lemma sumR_map_zeros :
  forall (f : V -> R) (l xs : list V) (k : nat),
  f zero = 0 -> Permutation l (repeat zero k ++ xs) -> sumR (map f l) = sumR (map f xs).
Proof.
intros f l xs k Hf Hp.
rewrite (sumR_perm _ _ (Permutation_map f Hp)), map_app, sumR_app.
replace (sumR (map f (repeat zero k))) with 0. ring.
clear Hp. induction k as [|k IH]; cbn [repeat map sumR].
- reflexivity.
- rewrite Hf, <- IH. ring.
Qed.

(* The bound of tree_sum_weighted for a tree whose leaves are a list and some zero
   states, in any order, and whose height is at most h. *)
Lemma weighted_of_tree :
  forall (eps : R) (w : V -> R), 0 <= eps -> adds_weighted val valid op eps w ->
  valid zero -> val zero = 0 -> w zero = 0 ->
  forall (t : tree V) (xs : list V) (k h : nat),
  Forall valid xs -> Permutation (leaves t) (repeat zero k ++ xs) -> (height t <= h)%nat ->
  valid (eval op t) /\
  Rabs (val (eval op t) - sumR (map val xs)) <=
    ((1 + eps) ^ h - 1) * sumabs (map val xs) + (1 + eps) ^ (h - 1) * sumR (map w xs).
Proof.
intros eps w He Hop Z0 Z1 Zw t xs k h Hv Hp Hh.
assert (Hvt : Forall valid (leaves t)).
{ apply (Forall_perm _ _ _ _ (Permutation_sym Hp)). apply Forall_app. split; [|exact Hv].
  clear -Z0. induction k as [|k IH]; cbn [repeat]; constructor; auto. }
destruct (tree_sum_weighted V val valid op eps w He Hop t Hvt) as [Vt [Et _]].
assert (Ea : sumabs (map val (leaves t)) = sumabs (map val xs)).
{ unfold sumabs. rewrite !map_map.
  apply sumR_map_zeros with (f := fun x => Rabs (val x)) (k := k).
  rewrite Z1. apply Rabs_R0. exact Hp. }
rewrite (sumR_map_zeros val _ _ _ Z1 Hp), (sumR_map_zeros w _ _ _ Zw Hp), Ea in Et.
assert (HA := sumabs_ge_0 (map val xs)).
assert (HW : 0 <= sumR (map w xs)).
{ apply (sumR_map_ge_0 _ valid). exact (proj1 Hop). exact Hv. }
assert (K1 : (1 + eps) ^ height t * sumabs (map val xs) <= (1 + eps) ^ h * sumabs (map val xs)).
{ apply Rmult_le_compat_r. exact HA. apply Rle_pow. lra. exact Hh. }
assert (K2 : (1 + eps) ^ (height t - 1) * sumR (map w xs) <= (1 + eps) ^ (h - 1) * sumR (map w xs)).
{ apply Rmult_le_compat_r. exact HW. apply Rle_pow. lra. lia. }
split. exact Vt. lra.
Qed.

(* A sum in the sequential order when adding to the zero state is rounded like every
   other addition, and an operand x that is not the result of an addition costs an
   absolute error w x: the fused step of a one-limb dot product. The zero state is a
   leaf, so the height is n and not n - 1; the absolute term is (1 + eps)^(n-1) times
   the sum of w over the elements. *)
Theorem fold_seq_weighted :
  forall (eps : R) (w : V -> R), 0 <= eps -> adds_weighted val valid op eps w ->
  valid zero -> val zero = 0 -> w zero = 0 ->
  forall xs : list V, Forall valid xs ->
  let s := fold_seq op zero xs in
  valid s /\
  Rabs (val s - sumR (map val xs)) <=
    ((1 + eps) ^ length xs - 1) * sumabs (map val xs) +
    (1 + eps) ^ (length xs - 1) * sumR (map w xs).
Proof.
intros eps w He Hop Z0 Z1 Zw xs Hv. cbv zeta.
destruct (fold_seq_tree_zero xs) as [t [Et [Lt Ht]]].
rewrite <- Et.
apply (weighted_of_tree eps w He Hop Z0 Z1 Zw t xs 1 (length xs) Hv).
- rewrite Lt. apply Permutation_refl.
- lia.
Qed.

(* The same in the lane order, for every width, when the addition leaves the zero state
   fixed. The additions that combine the lanes add nothing to the absolute term. *)
Theorem fold_lanes_weighted :
  forall (eps : R) (w : V -> R), 0 <= eps -> adds_weighted val valid op eps w ->
  valid zero -> val zero = 0 -> w zero = 0 -> op zero zero = zero ->
  forall (W : nat) (xs : list V), Forall valid xs ->
  let s := fold_lanes op op zero W xs in
  valid s /\
  Rabs (val s - sumR (map val xs)) <=
    ((1 + eps) ^ length xs - 1) * sumabs (map val xs) +
    (1 + eps) ^ (length xs - 1) * sumR (map w xs).
Proof.
intros eps w He Hop Z0 Z1 Zw Zz W xs Hv. cbv zeta.
destruct (Nat.eq_dec W 0) as [HW0|HW0].
- subst W. rewrite fold_lanes_0. exact (fold_seq_weighted eps w He Hop Z0 Z1 Zw xs Hv).
- destruct (Nat.lt_ge_cases (length xs) W) as [Hlt|Hge].
  + rewrite (fold_lanes_short _ _ op op zero W xs Zz Hlt).
    exact (fold_seq_weighted eps w He Hop Z0 Z1 Zw xs Hv).
  + assert (HW : (0 < W)%nat) by lia.
    destruct (fold_lanes_tree_zero W xs HW) as [t [Et [Pt Ht]]].
    rewrite <- Et.
    apply (weighted_of_tree eps w He Hop Z0 Z1 Zw t xs W (length xs) Hv Pt).
    rewrite Ht. apply lanes_height_zero_le. lia.
Qed.

End Orders.

Arguments zero_identity {V} val valid op zero.
