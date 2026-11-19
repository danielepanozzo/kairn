(* The eight comparisons: lt_2_2, le_2_2, eq_2_2, and the forms against one limb lt_2_1,
   le_2_1, eq_2_1, lt_1_2, le_1_2.

   Each kernel compares the limbs in order, as one compares two words in a dictionary:
       x < y   is computed as   x0 < y0  or  (x0 = y0 and x1 < y1),
   and likewise for <= and =. What is proved (the generated statements of
   proofs/gen/Statements.v): for normalized operands the mask returned is the truth of the
   comparison of the exact values x0 + x1 and y0 + y1.

   Why it holds (Milestone 1 statements): x0 = RN (x0 + x1) and y0 = RN (y0 + y1), and
   rounding is monotone. So x0 < y0 excludes x >= y, which would give x0 >= y0: hence
   x0 < y0 implies x < y (lemma lead_lt). When x0 = y0 the order of x and y is that of x1
   and y1. A number a of the format is the pair (a, 0), which satisfies a = RN (a + 0).

   Only the equation x0 = RN (x0 + x1) is used of a normalized operand, and only the
   monotonicity of RN; the statements hold for every precision. *)
From Stdlib Require Import Reals ZArith Lia Lra Bool.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format.
Open Scope R_scope.

Section Order.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

(* What the comparisons use of an operand: its leading limb is the rounding of its value. *)
Definition lead (x0 x1 : R) : Prop := x0 = RN emin prec (x0 + x1).

Lemma lead_normalized : forall x0 x1, normalized_2 emin prec x0 x1 -> lead x0 x1.
Proof. intros x0 x1 Hn. apply Hn. Qed.

(* A number of the format, with a zero second limb. *)
Lemma lead_format : forall a, fmt emin prec a -> lead a 0.
Proof.
intros a Fa. unfold fmt in Fa. unfold lead, RN. rewrite Rplus_0_r. symmetry.
apply round_generic; auto with typeclass_instances.
Qed.

(* A smaller leading limb means a smaller value: rounding is monotone. *)
Lemma lead_lt :
  forall x0 x1 y0 y1, lead x0 x1 -> lead y0 y1 -> x0 < y0 -> x0 + x1 < y0 + y1.
Proof.
intros x0 x1 y0 y1 Hx Hy H.
destruct (Rlt_or_le (x0 + x1) (y0 + y1)) as [L|L]; trivial.
exfalso.
assert (M : RN emin prec (y0 + y1) <= RN emin prec (x0 + x1)).
{ unfold RN. apply round_le; auto with typeclass_instances. }
unfold lead in Hx, Hy. lra.
Qed.

(* The three comparisons, limbs in order. *)
Lemma lex_lt :
  forall x0 x1 y0 y1, lead x0 x1 -> lead y0 y1 ->
  orb (Rlt_bool x0 y0) (andb (Req_bool x0 y0) (Rlt_bool x1 y1))
  = Rlt_bool (x0 + x1) (y0 + y1).
Proof.
intros x0 x1 y0 y1 Hx Hy.
destruct (Rtotal_order x0 y0) as [H|[H|H]].
- generalize (lead_lt x0 x1 y0 y1 Hx Hy H). intros L.
  rewrite (Rlt_bool_true x0 y0 H), (Rlt_bool_true _ _ L). reflexivity.
- rewrite (Rlt_bool_false x0 y0) by lra. rewrite (Req_bool_true x0 y0 H).
  rewrite orb_false_l, andb_true_l.
  destruct (Rlt_bool_spec x1 y1) as [L|L]; symmetry.
  + apply Rlt_bool_true. lra.
  + apply Rlt_bool_false. lra.
- generalize (lead_lt y0 y1 x0 x1 Hy Hx H). intros L.
  rewrite (Rlt_bool_false x0 y0) by lra.
  rewrite (Req_bool_false x0 y0 (Rgt_not_eq x0 y0 H)).
  rewrite orb_false_l, andb_false_l. symmetry. apply Rlt_bool_false. lra.
Qed.

Lemma lex_le :
  forall x0 x1 y0 y1, lead x0 x1 -> lead y0 y1 ->
  orb (Rlt_bool x0 y0) (andb (Req_bool x0 y0) (Rle_bool x1 y1))
  = Rle_bool (x0 + x1) (y0 + y1).
Proof.
intros x0 x1 y0 y1 Hx Hy.
destruct (Rtotal_order x0 y0) as [H|[H|H]].
- generalize (lead_lt x0 x1 y0 y1 Hx Hy H). intros L.
  rewrite (Rlt_bool_true x0 y0 H), (Rle_bool_true _ _ (Rlt_le _ _ L)). reflexivity.
- rewrite (Rlt_bool_false x0 y0) by lra. rewrite (Req_bool_true x0 y0 H).
  rewrite orb_false_l, andb_true_l.
  destruct (Rle_bool_spec x1 y1) as [L|L]; symmetry.
  + apply Rle_bool_true. lra.
  + apply Rle_bool_false. lra.
- generalize (lead_lt y0 y1 x0 x1 Hy Hx H). intros L.
  rewrite (Rlt_bool_false x0 y0) by lra.
  rewrite (Req_bool_false x0 y0 (Rgt_not_eq x0 y0 H)).
  rewrite orb_false_l, andb_false_l. symmetry. apply Rle_bool_false. exact L.
Qed.

Lemma lex_eq :
  forall x0 x1 y0 y1, lead x0 x1 -> lead y0 y1 ->
  andb (Req_bool x0 y0) (Req_bool x1 y1) = Req_bool (x0 + x1) (y0 + y1).
Proof.
intros x0 x1 y0 y1 Hx Hy.
destruct (Rtotal_order x0 y0) as [H|[H|H]].
- generalize (lead_lt x0 x1 y0 y1 Hx Hy H). intros L.
  rewrite (Req_bool_false x0 y0 (Rlt_not_eq x0 y0 H)).
  rewrite (Req_bool_false _ _ (Rlt_not_eq _ _ L)). reflexivity.
- rewrite (Req_bool_true x0 y0 H), andb_true_l.
  destruct (Req_dec x1 y1) as [E|E].
  + rewrite (Req_bool_true x1 y1 E). symmetry. apply Req_bool_true. lra.
  + rewrite (Req_bool_false x1 y1 E). symmetry. apply Req_bool_false.
    intros E'. apply E. lra.
- generalize (lead_lt y0 y1 x0 x1 Hy Hx H). intros L.
  rewrite (Req_bool_false x0 y0 (Rgt_not_eq x0 y0 H)).
  rewrite (Req_bool_false _ _ (Rgt_not_eq _ _ L)). reflexivity.
Qed.

End Order.

(** * The generated statements: two 2-limb operands *)

Theorem lt_2_2_correct : lt_2_2_spec.
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny m. unfold m, lt_2_2. clear m. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
apply (lex_lt emin prec); now apply lead_normalized.
Qed.

Theorem le_2_2_correct : le_2_2_spec.
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny m. unfold m, le_2_2. clear m. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
apply (lex_le emin prec); now apply lead_normalized.
Qed.

Theorem eq_2_2_correct : eq_2_2_spec.
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny m. unfold m, eq_2_2. clear m. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
apply (lex_eq emin prec); now apply lead_normalized.
Qed.

(** * The generated statements: a 2-limb operand and a number of the format *)

(* The second operand is the pair (a, 0), whose value is a + 0 = a. *)
Theorem lt_2_1_correct : lt_2_1_spec.
Proof.
intros emin prec Hp x0 x1 a Nx Fa m. unfold m, lt_2_1. clear m. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
generalize (lex_lt emin prec x0 x1 a 0 (lead_normalized emin prec x0 x1 Nx)
              (lead_format emin prec a Fa)).
rewrite (Rplus_0_r a). exact (fun H => H).
Qed.

Theorem le_2_1_correct : le_2_1_spec.
Proof.
intros emin prec Hp x0 x1 a Nx Fa m. unfold m, le_2_1. clear m. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
generalize (lex_le emin prec x0 x1 a 0 (lead_normalized emin prec x0 x1 Nx)
              (lead_format emin prec a Fa)).
rewrite (Rplus_0_r a). exact (fun H => H).
Qed.

Theorem eq_2_1_correct : eq_2_1_spec.
Proof.
intros emin prec Hp x0 x1 a Nx Fa m. unfold m, eq_2_1. clear m. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
generalize (lex_eq emin prec x0 x1 a 0 (lead_normalized emin prec x0 x1 Nx)
              (lead_format emin prec a Fa)).
rewrite (Rplus_0_r a). exact (fun H => H).
Qed.

(* The first operand is the pair (a, 0). *)
Theorem lt_1_2_correct : lt_1_2_spec.
Proof.
intros emin prec Hp a y0 y1 Fa Ny m. unfold m, lt_1_2. clear m. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
generalize (lex_lt emin prec a 0 y0 y1 (lead_format emin prec a Fa)
              (lead_normalized emin prec y0 y1 Ny)).
rewrite (Rplus_0_r a). exact (fun H => H).
Qed.

Theorem le_1_2_correct : le_1_2_spec.
Proof.
intros emin prec Hp a y0 y1 Fa Ny m. unfold m, le_1_2. clear m. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
generalize (lex_le emin prec a 0 y0 y1 (lead_format emin prec a Fa)
              (lead_normalized emin prec y0 y1 Ny)).
rewrite (Rplus_0_r a). exact (fun H => H).
Qed.
