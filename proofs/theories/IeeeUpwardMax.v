(* The maximum of the round-up interval, max_nl (docs/developer/design/upward.md, "The
   maximum"): its two machine forms have the property max_nl_ok of IeeeUpwardOperations.v, and
   what every function with the property computes.

   What is proved, for all limbs, signed zeros, infinities and NaN included:
   - max_sel_ok: max_nl_ok max_sel, x86's MAXPD a, b (if b < a then a else b);
   - max_num_ok: max_nl_ok max_num, arm64's FMAXNM a, b (FPMaxNum on quiet NaNs);
   - for every m with max_nl_ok and every b that is not a NaN: m a b is not a NaN
     (max_nl_not_nan); it is b when a is a NaN (max_nl_nan); otherwise it stands for the
     greater of the two extended real numbers, xmax (xval a) (xval b) (max_nl_xval), where
     xmax is the maximum of Rectangle.v; and the two statements together (max_nl_xkeep).

   So a statement of a kernel that holds for every m with max_nl_ok holds for both machine
   forms: the one proved listing covers MAXPD and FMAXNM, which differ only in the sign of a
   zero result (MAXPD returns its second operand on two zeros, FMAXNM returns +0 unless both
   are -0), and the extended real number of a zero has no sign.

   The proofs. A comparison of limbs is the comparison of their extended real numbers
   (lt_xval, IeeeExt.v), and the rest is a case analysis of the extended real numbers. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import IeeeVocabulary IeeeExt Rectangle.
From Kairn Require Import IeeeUpwardVocabulary.
From Kairn Require IeeeOperations IeeeUpwardOperations.
Open Scope R_scope.

(** * The order of the extended real numbers, by cases *)

(* The comparisons of real numbers that xle, xlt and the like leave in the goal once the
   extended real numbers are given by cases (the facts to use are premises of the goal), then
   linear arithmetic. Used by the other IeeeUpward files. *)
Ltac upward_xcase :=
  cbn;
  repeat match goal with
  | |- context [Rle_bool ?x ?y] => destruct (Rle_bool_spec x y); cbn
  | |- context [Rlt_bool ?x ?y] => destruct (Rlt_bool_spec x y); cbn
  | |- context [Req_bool ?x ?y] => destruct (Req_bool_spec x y); cbn
  end;
  intros;
  repeat match goal with H : _ /\ _ |- _ => destruct H end;
  try discriminate; try congruence;
  repeat split;
  try reflexivity; try assumption; try lra; try (exfalso; lra).

Lemma upward_xle_refl : forall v : xreal, v <> XNaN -> xle v v = true.
Proof. intros [|[|]|r]; upward_xcase. Qed.

Lemma upward_xlt_xle : forall v w : xreal, xlt v w = true -> xle v w = true.
Proof. intros [|[|]|r] [|[|]|s]; upward_xcase. Qed.

(* Two values that are not NaN are in one order or the other. *)
Lemma upward_xlt_false_xle :
  forall v w : xreal, v <> XNaN -> w <> XNaN -> xlt w v = false -> xle v w = true.
Proof. intros [|[|]|r] [|[|]|s]; upward_xcase. Qed.

Lemma upward_xle_xlt_false : forall v w : xreal, xle w v = true -> xlt v w = true -> False.
Proof. intros [|[|]|r] [|[|]|s]; upward_xcase. Qed.

Lemma upward_xle_xlt_eq :
  forall v w : xreal, xle v w = true -> xlt v w = false -> v = w.
Proof.
intros [|[|]|r] [|[|]|s]; upward_xcase. f_equal. lra.
Qed.

Section IeeeUpwardMax.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation xv := (@xval prec emax).
Notation max_nl_ok := (IeeeUpwardOperations.max_nl_ok prec emax).
Notation max_sel := (IeeeUpwardOperations.max_sel prec emax).
Notation max_num := (IeeeUpwardOperations.max_num prec emax).

Lemma upward_nan_dec : forall a : float, nan a \/ ~ nan a.
Proof. intros a. unfold nan. destruct (is_nan prec emax a); [now left|right; discriminate]. Qed.

Lemma upward_not_nan_xval : forall a : float, ~ nan a -> xv a <> XNaN.
Proof. intros a N E. apply N. now apply upward_xval_nan. Qed.

Lemma upward_not_nan_false : forall a : float, ~ nan a -> is_nan prec emax a = false.
Proof. intros a N. unfold nan in N. destruct (is_nan prec emax a); [now elim N|reflexivity]. Qed.

(** * MAXPD *)

(* On two values that are not NaN, max_sel returns one of them, and it is at least both. *)
Lemma max_sel_props :
  forall a b : float, ~ nan a -> ~ nan b ->
  (max_sel a b = a \/ max_sel a b = b) /\
  xle (xv a) (xv (max_sel a b)) = true /\ xle (xv b) (xv (max_sel a b)) = true.
Proof.
intros a b Na Nb. unfold IeeeUpwardOperations.max_sel. rewrite lt_xval.
assert (Ka := upward_not_nan_xval a Na). assert (Kb := upward_not_nan_xval b Nb).
destruct (xlt (xv b) (xv a)) eqn:L.
- split; [now left|]. split.
  + exact (upward_xle_refl _ Ka).
  + exact (upward_xlt_xle _ _ L).
- split; [now right|]. split.
  + exact (upward_xlt_false_xle _ _ Ka Kb L).
  + exact (upward_xle_refl _ Kb).
Qed.

Theorem max_sel_ok : max_nl_ok max_sel.
Proof.
intros a b Nb. split.
- intros Na. unfold IeeeUpwardOperations.max_sel. rewrite lt_xval.
  rewrite (proj2 (upward_xval_nan prec emax a) Na).
  destruct (xv b) as [|[|]|r]; reflexivity.
- intros Na. exact (max_sel_props a b Na Nb).
Qed.

(** * FMAXNM *)

Lemma upward_zero_dec : forall x : float, zero x \/ ~ zero x.
Proof.
intros [s|s|s pl H|s m e H].
- left. now exists s.
- right. intros [s' E]. discriminate E.
- right. intros [s' E]. discriminate E.
- right. intros [s' E]. discriminate E.
Qed.

(* Unless both operands are zeros, FMAXNM and MAXPD agree on operands that are not NaN. *)
Lemma max_num_max_sel :
  forall a b : float, ~ nan a -> ~ nan b -> ~ (zero a /\ zero b) -> max_num a b = max_sel a b.
Proof.
intros a b Na Nb Z.
destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; destruct b as [sb|sb|sb pb Hb|sb mb eb Hb];
  try (exfalso; apply Na; exact eq_refl); try (exfalso; apply Nb; exact eq_refl);
  try reflexivity.
exfalso. apply Z. split; [now exists sa|now exists sb].
Qed.

(* Two zeros: the zero whose sign is the "and" of the signs, +0 unless both are -0. *)
Lemma max_num_zeros :
  forall sa sb : bool,
  max_num (B754_zero prec emax sa) (B754_zero prec emax sb) = B754_zero prec emax (andb sa sb).
Proof. intros sa sb. reflexivity. Qed.

Theorem max_num_ok : max_nl_ok max_num.
Proof.
intros a b Nb. split.
- intros Na. unfold nan in Na. unfold IeeeUpwardOperations.max_num.
  rewrite Na, (upward_not_nan_false b Nb). reflexivity.
- intros Na.
  destruct (upward_zero_dec a) as [[sa Ea]|Za]; [destruct (upward_zero_dec b) as [[sb Eb]|Zb]|].
  + subst a b. rewrite max_num_zeros. split.
    * destruct sa; [right|left]; reflexivity.
    * cbn. split; apply Rle_bool_true; apply Rle_refl.
  + rewrite max_num_max_sel by (try assumption; intros [_ K]; exact (Zb K)).
    exact (max_sel_props a b Na Nb).
  + rewrite max_num_max_sel by (try assumption; intros [K _]; exact (Za K)).
    exact (max_sel_props a b Na Nb).
Qed.

(** * What every maximum with the property computes *)

Section AnyMax.
Variable m : float -> float -> float.
Hypothesis m_ok : max_nl_ok m.

(* A NaN first operand loses. *)
Lemma max_nl_nan : forall a b : float, nan a -> ~ nan b -> m a b = b.
Proof. intros a b Na Nb. exact (proj1 (m_ok a b Nb) Na). Qed.

(* The result is not a NaN when the second operand is not one. *)
Lemma max_nl_not_nan : forall a b : float, ~ nan b -> ~ nan (m a b).
Proof.
intros a b Nb. destruct (m_ok a b Nb) as [H1 H2].
destruct (upward_nan_dec a) as [Na|Na].
- rewrite (H1 Na). exact Nb.
- destruct (H2 Na) as [[E|E] _]; rewrite E; assumption.
Qed.

(* On two values that are not NaN, the result stands for the greater of the two extended real
   numbers. *)
Lemma max_nl_xval :
  forall a b : float, ~ nan a -> ~ nan b -> xv (m a b) = xmax (xv a) (xv b).
Proof.
intros a b Na Nb. destruct (proj2 (m_ok a b Nb) Na) as [[E|E] [La Lb]];
  unfold xmax; destruct (xlt (xv a) (xv b)) eqn:L.
- rewrite E in Lb. exfalso. exact (upward_xle_xlt_false _ _ Lb L).
- now rewrite E.
- now rewrite E.
- rewrite E in La |- *. symmetry. exact (upward_xle_xlt_eq _ _ La L).
Qed.

(* Both cases in one statement, the form the folds of the products use: with b not a NaN, the
   result is not a NaN and stands for xval b when a is a NaN, and for the greater of the two
   otherwise. *)
Lemma max_nl_xkeep :
  forall a b : float, ~ nan b ->
  ~ nan (m a b) /\
  xv (m a b) = (if is_nan prec emax a then xv b else xmax (xv a) (xv b)).
Proof.
intros a b Nb. split; [exact (max_nl_not_nan a b Nb)|].
destruct (is_nan prec emax a) eqn:Na.
- now rewrite (max_nl_nan a b Na Nb).
- apply max_nl_xval; [|exact Nb]. unfold nan. now rewrite Na.
Qed.

End AnyMax.

End IeeeUpwardMax.
