(* Conversions of a 2-limb number to one limb: to_nearest_2, to_down_2, to_up_2,
   abs_upper_2.

   Notation: F is the format; for a number s of F, succ(s) and pred(s) are its neighbors
   in F, the next number above and the next below; RN, RD, RU are the roundings to
   nearest (ties to even), down and up. x = (x0, x1) is normalized: x0 = RN (x0 + x1).

   What is proved (the generated statements of proofs/gen/Statements.v), for every
   precision:
   - to_nearest_2: x0 = RN (x). This is the definition of normalized.
   - to_down_2: RD (x) is pred(x0) when x1 < 0, and x0 otherwise.
   - to_up_2:   RU (x) is succ(x0) when x1 > 0, and x0 otherwise.
   - abs_upper_2: to_up_2 applied to abs_2 (x) is RU (|x|).

   Why: since x0 is the number of F nearest to x, x lies strictly between pred(x0) and
   succ(x0) (lemma normalized_2_between: if x were at or beyond a neighbor, monotonicity
   of RN would put RN (x) at or beyond that neighbor). So x is in one of the two gaps next
   to x0, or equal to x0, and the sign of x1 = x - x0 says which. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Normalized Sign.
Open Scope R_scope.

Section Neighbors.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation succ := (succ radix2 fexp).
Notation pred := (pred radix2 fexp).

(* With gradual underflow every number of the format has a neighbor strictly above and
   one strictly below, zero included (its neighbors are eta and -eta). *)
Lemma succ_FLT_gt : forall s, s < succ s.
Proof.
intros s. destruct (Req_dec s 0) as [Zs|Zs].
- rewrite Zs, (succ_0 radix2 fexp), (ulp_FLT_0 radix2 emin prec). apply bpow_gt_0.
- exact (succ_gt_id radix2 fexp s Zs).
Qed.

Lemma pred_FLT_lt : forall s, pred s < s.
Proof.
intros s. destruct (Req_dec s 0) as [Zs|Zs].
- rewrite Zs, (pred_0 radix2 fexp), (ulp_FLT_0 radix2 emin prec).
  generalize (bpow_gt_0 radix2 emin). lra.
- exact (pred_lt_id radix2 fexp s Zs).
Qed.

Variables x0 x1 : R.
Hypothesis Hn : normalized_2 emin prec x0 x1.

Let F0 : format x0.
Proof. apply Hn. Qed.
Let Hx : x0 = round radix2 fexp (Znearest tie_even) (x0 + x1).
Proof. apply Hn. Qed.
Let Fp : format (pred x0).
Proof. apply generic_format_pred; auto with typeclass_instances. Qed.
Let Fs : format (succ x0).
Proof. apply generic_format_succ; auto with typeclass_instances. Qed.

(* The value of a normalized pair lies strictly between the neighbors of its leading
   limb. *)
Lemma normalized_2_between : pred x0 < x0 + x1 < succ x0.
Proof.
split.
- destruct (Rlt_or_le (pred x0) (x0 + x1)) as [H|H]; trivial.
  exfalso.
  generalize (round_le_generic radix2 fexp (Znearest tie_even) (x0 + x1) (pred x0) Fp H).
  rewrite <- Hx. generalize (pred_FLT_lt x0). lra.
- destruct (Rlt_or_le (x0 + x1) (succ x0)) as [H|H]; trivial.
  exfalso.
  generalize (round_ge_generic radix2 fexp (Znearest tie_even) (succ x0) (x0 + x1) Fs H).
  rewrite <- Hx. generalize (succ_FLT_gt x0). lra.
Qed.

(* Rounding down: the value is in the gap below x0 when x1 < 0, and in the gap above it,
   or equal to x0, otherwise. *)
Lemma to_down_2_eq :
  to_down_2 emin prec x0 x1 = round radix2 fexp Zfloor (x0 + x1).
Proof.
destruct normalized_2_between as [B1 B2].
unfold to_down_2. cbv zeta. symmetry.
destruct (Rlt_bool_spec x1 0) as [H|H].
- apply (round_DN_eq radix2 fexp (x0 + x1) (pred x0) Fp).
  rewrite (succ_pred radix2 fexp x0 F0). split; lra.
- apply (round_DN_eq radix2 fexp (x0 + x1) x0 F0). split; lra.
Qed.

(* Rounding up, likewise. *)
Lemma to_up_2_eq :
  to_up_2 emin prec x0 x1 = round radix2 fexp Zceil (x0 + x1).
Proof.
destruct normalized_2_between as [B1 B2].
unfold to_up_2. cbv zeta. symmetry.
destruct (Rlt_bool_spec 0 x1) as [H|H].
- apply (round_UP_eq radix2 fexp (x0 + x1) (succ x0) Fs).
  rewrite (pred_succ radix2 fexp x0 F0). split; lra.
- apply (round_UP_eq radix2 fexp (x0 + x1) x0 F0). split; lra.
Qed.

End Neighbors.

(** * The generated statements *)

Theorem to_nearest_2_correct : to_nearest_2_spec.
Proof.
intros emin prec Hp x0 x1 Hn t. unfold t, to_nearest_2. clear t. cbv zeta.
split; apply Hn.
Qed.

Theorem to_down_2_correct : to_down_2_spec.
Proof.
intros emin prec Hp x0 x1 Hn t. unfold t. clear t.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
assert (F0 : fmt emin prec x0) by apply Hn.
split.
- (* pred (x0) or x0 *)
  unfold to_down_2. cbv zeta. limb_format.
- unfold RD. exact (to_down_2_eq emin prec x0 x1 Hn).
Qed.

Theorem to_up_2_correct : to_up_2_spec.
Proof.
intros emin prec Hp x0 x1 Hn t. unfold t. clear t.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
assert (F0 : fmt emin prec x0) by apply Hn.
split.
- (* succ (x0) or x0 *)
  unfold to_up_2. cbv zeta. limb_format.
- unfold RU. exact (to_up_2_eq emin prec x0 x1 Hn).
Qed.

(* abs_2 returns a normalized pair of value |x|, which to_up_2 rounds up: the statement of
   to_up_2 for that pair. *)
Theorem abs_upper_2_correct : abs_upper_2_spec.
Proof.
intros emin prec Hp x0 x1 Hn t. unfold t, abs_upper_2. clear t.
generalize (abs_2_correct emin prec Hp x0 x1 Hn).
destruct (abs_2 x0 x1) as [a0 a1]. cbv beta iota zeta.
intros [Na Ha]. rewrite <- Ha.
exact (to_up_2_correct emin prec Hp a0 a1 Na).
Qed.
