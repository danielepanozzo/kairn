(* EXPERIMENTAL proof probe. Statement 3 of the product: the interval product of the form
   "branch" (mul_branch, upward2.hpp lines 519-535, with mul_case, mul_one, mul_zero_zero and the
   table kCases), its fast path, end to end, in the model of X2Defs.v (no overflow, so the test
   big(p) and mul_special are outside the model).

   Main theorems (Print Assumptions at the end of the file), for every positive precision and
   every emin (pair_mul_correct needs no condition; the invariant of the operands is what makes
   the tests of mul_branch on the heads read the signs of the bounds, upper_normalized_sign):
   - mul_branch_nonneg: both operands nonnegative (lower bounds >= 0, which mul_branch reads on
     the heads nh: upper_normalized_sign makes the test exact): the branch is mul_case<10>, the
     result's lane 0 is an upper pair of hi(x) hi(y), the exact upper bound of the product set,
     its lane 1 an upper pair of -(lo(x) lo(y)), the negated exact lower bound, and both are
     upper-normalized;
   - mul_branch_zero_zero: both operands contain zero in their interior: the two candidates of
     each lane and lexmax give upper pairs of max(lo(x) lo(y), hi(x) hi(y)) and of
     max(-(lo(x) hi(y)), -(hi(x) lo(y))), upper-normalized;
   - mul_branch_correct: every case of the branch: for canonical operands (both lanes
     upper-normalized), the result is canonical and contains t s for every t of x and s of y.
   Here hi(x) = uh + ul and lo(x) = -(nh + nl): the interval a register pair stands for. *)
From Stdlib Require Import Reals ZArith Lia Lra Psatz Bool.
From Flocq Require Import Core.
From Kairn.Gen Require Import Statements.
From KairnX2P Require Import X2Defs X2Order X2PairMul.
Open Scope R_scope.

(** * The real inequalities of the case table *)

(* With a <= t <= b and c <= s <= d: the classical bounds of t s for each case of the signs.
   Each one is two steps, t s <= (one bound) s <= (the product of bounds), and the same below. *)
Section Corners.
Variables a b c d t s : R.
Hypothesis Ht : a <= t <= b.
Hypothesis Hs : c <= s <= d.

Lemma corners_10 : 0 <= a -> 0 <= c -> t * s <= b * d /\ a * c <= t * s.
Proof.
intros Ha Hc.
assert (P1 : 0 <= (b - t) * s) by (apply Rmult_le_pos; lra).
assert (P2 : 0 <= b * (d - s)) by (apply Rmult_le_pos; lra).
assert (P3 : 0 <= (t - a) * s) by (apply Rmult_le_pos; lra).
assert (P4 : 0 <= a * (s - c)) by (apply Rmult_le_pos; lra).
split; lra.
Qed.

Lemma corners_6 : 0 <= a -> d <= 0 -> t * s <= a * d /\ b * c <= t * s.
Proof.
intros Ha Hd.
assert (P1 : 0 <= (t - a) * - s) by (apply Rmult_le_pos; lra).
assert (P2 : 0 <= a * (d - s)) by (apply Rmult_le_pos; lra).
assert (P3 : 0 <= (b - t) * - s) by (apply Rmult_le_pos; lra).
assert (P4 : 0 <= b * (s - c)) by (apply Rmult_le_pos; lra).
split; lra.
Qed.

Lemma corners_2 : 0 <= a -> c < 0 -> 0 < d -> t * s <= b * d /\ b * c <= t * s.
Proof.
intros Ha Hc Hd.
assert (P1 : 0 <= t * (d - s)) by (apply Rmult_le_pos; lra).
assert (P2 : 0 <= (b - t) * d) by (apply Rmult_le_pos; lra).
assert (P3 : 0 <= t * (s - c)) by (apply Rmult_le_pos; lra).
assert (P4 : 0 <= (b - t) * - c) by (apply Rmult_le_pos; lra).
split; lra.
Qed.

Lemma corners_9 : b <= 0 -> 0 <= c -> t * s <= b * c /\ a * d <= t * s.
Proof.
intros Hb Hc.
assert (P1 : 0 <= (b - t) * s) by (apply Rmult_le_pos; lra).
assert (P2 : 0 <= - b * (s - c)) by (apply Rmult_le_pos; lra).
assert (P3 : 0 <= (t - a) * s) by (apply Rmult_le_pos; lra).
assert (P4 : 0 <= - a * (d - s)) by (apply Rmult_le_pos; lra).
split; lra.
Qed.

Lemma corners_5 : b <= 0 -> d <= 0 -> t * s <= a * c /\ b * d <= t * s.
Proof.
intros Hb Hd.
assert (P1 : 0 <= (t - a) * - s) by (apply Rmult_le_pos; lra).
assert (P2 : 0 <= - a * (s - c)) by (apply Rmult_le_pos; lra).
assert (P3 : 0 <= (b - t) * - s) by (apply Rmult_le_pos; lra).
assert (P4 : 0 <= - b * (d - s)) by (apply Rmult_le_pos; lra).
split; lra.
Qed.

Lemma corners_1 : b <= 0 -> c < 0 -> 0 < d -> t * s <= a * c /\ a * d <= t * s.
Proof.
intros Hb Hc Hd.
assert (P1 : 0 <= - t * (s - c)) by (apply Rmult_le_pos; lra).
assert (P2 : 0 <= (t - a) * - c) by (apply Rmult_le_pos; lra).
assert (P3 : 0 <= - t * (d - s)) by (apply Rmult_le_pos; lra).
assert (P4 : 0 <= (t - a) * d) by (apply Rmult_le_pos; lra).
split; lra.
Qed.

Lemma corners_8 : a < 0 -> 0 < b -> 0 <= c -> t * s <= b * d /\ a * d <= t * s.
Proof.
intros Ha Hb Hc.
assert (P1 : 0 <= (b - t) * s) by (apply Rmult_le_pos; lra).
assert (P2 : 0 <= b * (d - s)) by (apply Rmult_le_pos; lra).
assert (P3 : 0 <= (t - a) * s) by (apply Rmult_le_pos; lra).
assert (P4 : 0 <= - a * (d - s)) by (apply Rmult_le_pos; lra).
split; lra.
Qed.

Lemma corners_4 : a < 0 -> 0 < b -> d <= 0 -> t * s <= a * c /\ b * c <= t * s.
Proof.
intros Ha Hb Hd.
assert (P1 : 0 <= (t - a) * - s) by (apply Rmult_le_pos; lra).
assert (P2 : 0 <= - a * (s - c)) by (apply Rmult_le_pos; lra).
assert (P3 : 0 <= (b - t) * - s) by (apply Rmult_le_pos; lra).
assert (P4 : 0 <= b * (s - c)) by (apply Rmult_le_pos; lra).
split; lra.
Qed.

Lemma corners_0 :
  a < 0 -> 0 < b -> c < 0 -> 0 < d ->
  t * s <= Rmax (a * c) (b * d) /\ - (t * s) <= Rmax (- (a * d)) (- (b * c)).
Proof.
intros Ha Hb Hc Hd.
assert (Q1 : 0 < b * d) by (apply Rmult_lt_0_compat; lra).
assert (Q2 : 0 < - a * d) by (apply Rmult_lt_0_compat; lra).
split.
- destruct (Rle_or_lt 0 t) as [T|T]; destruct (Rle_or_lt 0 s) as [S|S].
  + apply Rle_trans with (2 := Rmax_r _ _).
    assert (P1 : 0 <= (b - t) * s) by (apply Rmult_le_pos; lra).
    assert (P2 : 0 <= b * (d - s)) by (apply Rmult_le_pos; lra). lra.
  + apply Rle_trans with (2 := Rmax_r _ _).
    assert (P1 : 0 <= t * - s) by (apply Rmult_le_pos; lra). lra.
  + apply Rle_trans with (2 := Rmax_r _ _).
    assert (P1 : 0 <= - t * s) by (apply Rmult_le_pos; lra). lra.
  + apply Rle_trans with (2 := Rmax_l _ _).
    assert (P1 : 0 <= (t - a) * - s) by (apply Rmult_le_pos; lra).
    assert (P2 : 0 <= - a * (s - c)) by (apply Rmult_le_pos; lra). lra.
- destruct (Rle_or_lt 0 t) as [T|T]; destruct (Rle_or_lt 0 s) as [S|S].
  + apply Rle_trans with (2 := Rmax_l _ _).
    assert (P1 : 0 <= t * s) by (apply Rmult_le_pos; lra). lra.
  + apply Rle_trans with (2 := Rmax_r _ _).
    assert (P1 : 0 <= (b - t) * - s) by (apply Rmult_le_pos; lra).
    assert (P2 : 0 <= b * (s - c)) by (apply Rmult_le_pos; lra). lra.
  + apply Rle_trans with (2 := Rmax_l _ _).
    assert (P1 : 0 <= (t - a) * s) by (apply Rmult_le_pos; lra).
    assert (P2 : 0 <= - a * (d - s)) by (apply Rmult_le_pos; lra). lra.
  + apply Rle_trans with (2 := Rmax_l _ _).
    assert (P1 : 0 <= - t * - s) by (apply Rmult_le_pos; lra). lra.
Qed.

End Corners.

Section Branch.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

(* The register pair of an interval, from its four numbers. *)
Local Notation reg uh nh ul nl := (mkR (mkV uh nh) (mkV ul nl)).

(** * One candidate per lane, and the greater of two *)

(* mul_one: pair_mul on each lane, by pair_mul_correct (for all real inputs). *)
Lemma mul_one_correct :
  forall ph0 ph1 pl0 pl1 qh0 qh1 ql0 ql1,
  canonical emin prec (mul_one emin prec (reg ph0 ph1 pl0 pl1) (reg qh0 qh1 ql0 ql1)) /\
  (ph0 + pl0) * (qh0 + ql0) <= hi (mul_one emin prec (reg ph0 ph1 pl0 pl1) (reg qh0 qh1 ql0 ql1)) /\
  (ph1 + pl1) * (qh1 + ql1) <= nlo (mul_one emin prec (reg ph0 ph1 pl0 pl1) (reg qh0 qh1 ql0 ql1)).
Proof.
intros ph0 ph1 pl0 pl1 qh0 qh1 ql0 ql1.
destruct (pair_mul_correct emin prec ph0 pl0 qh0 ql0) as [U0 N0].
destruct (pair_mul_correct emin prec ph1 pl1 qh1 ql1) as [U1 N1].
unfold upper_pair in U0, U1.
unfold mul_one, pair_mul_v, canonical, hi, nlo. cbn [lane0 lane1 hreg lreg fst snd].
split; [split; [exact N0 | exact N1] | split; [exact U0 | exact U1]].
Qed.

(* lexmax on each lane, by lexmax_correct. *)
Lemma lexmax_v_correct :
  forall ah al bh bl : V,
  upper_normalized emin prec (lane0 ah) (lane0 al) ->
  upper_normalized emin prec (lane0 bh) (lane0 bl) ->
  upper_normalized emin prec (lane1 ah) (lane1 al) ->
  upper_normalized emin prec (lane1 bh) (lane1 bl) ->
  canonical emin prec (lexmax_v ah al bh bl) /\
  hi (lexmax_v ah al bh bl) = Rmax (lane0 ah + lane0 al) (lane0 bh + lane0 bl) /\
  nlo (lexmax_v ah al bh bl) = Rmax (lane1 ah + lane1 al) (lane1 bh + lane1 bl).
Proof.
intros ah al bh bl A0 B0 A1 B1.
destruct (lexmax_correct emin prec _ _ _ _ A0 B0) as [_ [V0 N0]].
destruct (lexmax_correct emin prec _ _ _ _ A1 B1) as [_ [V1 N1]].
unfold lexmax_v, canonical, hi, nlo. cbn [lane0 lane1 hreg lreg fst snd].
split; [split; [exact N0 | exact N1] | split; [exact V0 | exact V1]].
Qed.

(** * The cases of the branch, each one end to end *)

(* The result z of operands x and y is canonical and contains every t s, t in x, s in y. *)
Definition case_ok (z x y : Rg) : Prop :=
  canonical emin prec z /\ forall t s, mem x t -> mem y s -> mem z (t * s).

(* The facts of mul_one_correct for the mul_one of the goal; then t and s introduced. *)
Ltac case_facts :=
  match goal with
  | |- context [mul_one emin prec (reg ?a ?b ?c ?d) (reg ?e ?f ?g ?h)] =>
      destruct (mul_one_correct a b c d e f g h) as [Cz [H0 H1]]
  end;
  split; [match goal with Hc : canonical _ _ _ |- _ => exact Hc end|];
  intros t s [T1 T2] [S1 S2]; unfold mem;
  unfold hi, nlo in T1, T2, S1, S2; cbn [lane0 lane1 hreg lreg] in T1, T2, S1, S2.

(* Each case: the lanes that mul_case<K> passes to pair_mul (by computation of the table and
   of lanes, flip), then the classical bounds of the corners. The sign hypotheses are those
   that mul_branch establishes before calling mul_case<K>. *)
Lemma case_10 :
  forall xuh xnh xul xnl yuh ynh yul ynl,
  xnh + xnl <= 0 -> ynh + ynl <= 0 ->
  case_ok (mul_case emin prec 10 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
          (reg xuh xnh xul xnl) (reg yuh ynh yul ynl).
Proof.
intros xuh xnh xul xnl yuh ynh yul ynl Sx Sy. unfold case_ok.
change (mul_case emin prec 10 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
  with (mul_one emin prec (reg xuh xnh xul xnl) (reg yuh (- ynh) yul (- ynl))).
case_facts.
destruct (corners_10 (- (xnh + xnl)) (xuh + xul) (- (ynh + ynl)) (yuh + yul) t s
            (conj T1 T2) (conj S1 S2) ltac:(lra) ltac:(lra)) as [R1 R2].
split; lra.
Qed.

Lemma case_6 :
  forall xuh xnh xul xnl yuh ynh yul ynl,
  xnh + xnl <= 0 -> yuh + yul <= 0 ->
  case_ok (mul_case emin prec 6 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
          (reg xuh xnh xul xnl) (reg yuh ynh yul ynl).
Proof.
intros xuh xnh xul xnl yuh ynh yul ynl Sx Sy. unfold case_ok.
change (mul_case emin prec 6 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
  with (mul_one emin prec (reg xnh xuh xnl xul) (reg (- yuh) ynh (- yul) ynl)).
case_facts.
destruct (corners_6 (- (xnh + xnl)) (xuh + xul) (- (ynh + ynl)) (yuh + yul) t s
            (conj T1 T2) (conj S1 S2) ltac:(lra) ltac:(lra)) as [R1 R2].
split; lra.
Qed.

Lemma case_2 :
  forall xuh xnh xul xnl yuh ynh yul ynl,
  xnh + xnl <= 0 -> 0 < ynh + ynl -> 0 < yuh + yul ->
  case_ok (mul_case emin prec 2 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
          (reg xuh xnh xul xnl) (reg yuh ynh yul ynl).
Proof.
intros xuh xnh xul xnl yuh ynh yul ynl Sx Sy1 Sy2. unfold case_ok.
change (mul_case emin prec 2 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
  with (mul_one emin prec (reg xuh xuh xul xul) (reg yuh ynh yul ynl)).
case_facts.
destruct (corners_2 (- (xnh + xnl)) (xuh + xul) (- (ynh + ynl)) (yuh + yul) t s
            (conj T1 T2) (conj S1 S2) ltac:(lra) ltac:(lra) ltac:(lra)) as [R1 R2].
split; lra.
Qed.

Lemma case_9 :
  forall xuh xnh xul xnl yuh ynh yul ynl,
  xuh + xul <= 0 -> ynh + ynl <= 0 ->
  case_ok (mul_case emin prec 9 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
          (reg xuh xnh xul xnl) (reg yuh ynh yul ynl).
Proof.
intros xuh xnh xul xnl yuh ynh yul ynl Sx Sy. unfold case_ok.
change (mul_case emin prec 9 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
  with (mul_one emin prec (reg xuh xnh xul xnl) (reg (- ynh) yuh (- ynl) yul)).
case_facts.
destruct (corners_9 (- (xnh + xnl)) (xuh + xul) (- (ynh + ynl)) (yuh + yul) t s
            (conj T1 T2) (conj S1 S2) ltac:(lra) ltac:(lra)) as [R1 R2].
split; lra.
Qed.

Lemma case_5 :
  forall xuh xnh xul xnl yuh ynh yul ynl,
  xuh + xul <= 0 -> yuh + yul <= 0 ->
  case_ok (mul_case emin prec 5 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
          (reg xuh xnh xul xnl) (reg yuh ynh yul ynl).
Proof.
intros xuh xnh xul xnl yuh ynh yul ynl Sx Sy. unfold case_ok.
change (mul_case emin prec 5 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
  with (mul_one emin prec (reg xnh xuh xnl xul) (reg ynh (- yuh) ynl (- yul))).
case_facts.
destruct (corners_5 (- (xnh + xnl)) (xuh + xul) (- (ynh + ynl)) (yuh + yul) t s
            (conj T1 T2) (conj S1 S2) ltac:(lra) ltac:(lra)) as [R1 R2].
split; lra.
Qed.

Lemma case_1 :
  forall xuh xnh xul xnl yuh ynh yul ynl,
  xuh + xul <= 0 -> 0 < ynh + ynl -> 0 < yuh + yul ->
  case_ok (mul_case emin prec 1 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
          (reg xuh xnh xul xnl) (reg yuh ynh yul ynl).
Proof.
intros xuh xnh xul xnl yuh ynh yul ynl Sx Sy1 Sy2. unfold case_ok.
change (mul_case emin prec 1 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
  with (mul_one emin prec (reg xnh xnh xnl xnl) (reg ynh yuh ynl yul)).
case_facts.
destruct (corners_1 (- (xnh + xnl)) (xuh + xul) (- (ynh + ynl)) (yuh + yul) t s
            (conj T1 T2) (conj S1 S2) ltac:(lra) ltac:(lra) ltac:(lra)) as [R1 R2].
split; lra.
Qed.

Lemma case_8 :
  forall xuh xnh xul xnl yuh ynh yul ynl,
  0 < xnh + xnl -> 0 < xuh + xul -> ynh + ynl <= 0 ->
  case_ok (mul_case emin prec 8 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
          (reg xuh xnh xul xnl) (reg yuh ynh yul ynl).
Proof.
intros xuh xnh xul xnl yuh ynh yul ynl Sx1 Sx2 Sy. unfold case_ok.
change (mul_case emin prec 8 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
  with (mul_one emin prec (reg xuh xnh xul xnl) (reg yuh yuh yul yul)).
case_facts.
destruct (corners_8 (- (xnh + xnl)) (xuh + xul) (- (ynh + ynl)) (yuh + yul) t s
            (conj T1 T2) (conj S1 S2) ltac:(lra) ltac:(lra) ltac:(lra)) as [R1 R2].
split; lra.
Qed.

Lemma case_4 :
  forall xuh xnh xul xnl yuh ynh yul ynl,
  0 < xnh + xnl -> 0 < xuh + xul -> yuh + yul <= 0 ->
  case_ok (mul_case emin prec 4 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
          (reg xuh xnh xul xnl) (reg yuh ynh yul ynl).
Proof.
intros xuh xnh xul xnl yuh ynh yul ynl Sx1 Sx2 Sy. unfold case_ok.
change (mul_case emin prec 4 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
  with (mul_one emin prec (reg xnh xuh xnl xul) (reg ynh ynh ynl ynl)).
case_facts.
destruct (corners_4 (- (xnh + xnl)) (xuh + xul) (- (ynh + ynl)) (yuh + yul) t s
            (conj T1 T2) (conj S1 S2) ltac:(lra) ltac:(lra) ltac:(lra)) as [R1 R2].
split; lra.
Qed.

(* Both operands contain zero: two candidates per lane, the greater by lexmax. *)
Lemma mul_zero_zero_eq :
  forall xuh xnh xul xnl yuh ynh yul ynl,
  mul_zero_zero emin prec (reg xuh xnh xul xnl) (reg yuh ynh yul ynl) =
  lexmax_v (mkV (fst (snd (pair_mul emin prec xnh xnl ynh ynl)))
                (fst (snd (pair_mul emin prec xnh xnl yuh yul))))
           (mkV (snd (snd (pair_mul emin prec xnh xnl ynh ynl)))
                (snd (snd (pair_mul emin prec xnh xnl yuh yul))))
           (mkV (fst (snd (pair_mul emin prec xuh xul yuh yul)))
                (fst (snd (pair_mul emin prec xuh xul ynh ynl))))
           (mkV (snd (snd (pair_mul emin prec xuh xul yuh yul)))
                (snd (snd (pair_mul emin prec xuh xul ynh ynl)))).

Proof. reflexivity. Qed.

Lemma zero_zero_values :
  forall xuh xnh xul xnl yuh ynh yul ynl,
  canonical emin prec (mul_zero_zero emin prec (reg xuh xnh xul xnl) (reg yuh ynh yul ynl)) /\
  Rmax ((xnh + xnl) * (ynh + ynl)) ((xuh + xul) * (yuh + yul))
    <= hi (mul_zero_zero emin prec (reg xuh xnh xul xnl) (reg yuh ynh yul ynl)) /\
  Rmax ((xnh + xnl) * (yuh + yul)) ((xuh + xul) * (ynh + ynl))
    <= nlo (mul_zero_zero emin prec (reg xuh xnh xul xnl) (reg yuh ynh yul ynl)).
Proof.
intros xuh xnh xul xnl yuh ynh yul ynl.
rewrite mul_zero_zero_eq.
destruct (pair_mul_correct emin prec xnh xnl ynh ynl) as [Ua0 Na0].
destruct (pair_mul_correct emin prec xnh xnl yuh yul) as [Ua1 Na1].
destruct (pair_mul_correct emin prec xuh xul yuh yul) as [Ub0 Nb0].
destruct (pair_mul_correct emin prec xuh xul ynh ynl) as [Ub1 Nb1].
unfold upper_pair in Ua0, Ua1, Ub0, Ub1.
set (ra0 := pair_mul emin prec xnh xnl ynh ynl) in *.
set (ra1 := pair_mul emin prec xnh xnl yuh yul) in *.
set (rb0 := pair_mul emin prec xuh xul yuh yul) in *.
set (rb1 := pair_mul emin prec xuh xul ynh ynl) in *.
destruct (lexmax_v_correct (mkV (fst (snd ra0)) (fst (snd ra1))) (mkV (snd (snd ra0)) (snd (snd ra1)))
            (mkV (fst (snd rb0)) (fst (snd rb1))) (mkV (snd (snd rb0)) (snd (snd rb1)))
            Na0 Nb0 Na1 Nb1)
  as [C [V0 V1]].
split; [exact C|]. rewrite V0, V1. cbn [lane0 lane1].
split; apply Rmax_lub.
- apply Rle_trans with (1 := Ua0). apply Rmax_l.
- apply Rle_trans with (1 := Ub0). apply Rmax_r.
- apply Rle_trans with (1 := Ua1). apply Rmax_l.
- apply Rle_trans with (1 := Ub1). apply Rmax_r.
Qed.

Lemma case_0 :
  forall xuh xnh xul xnl yuh ynh yul ynl,
  0 < xnh + xnl -> 0 < xuh + xul -> 0 < ynh + ynl -> 0 < yuh + yul ->
  case_ok (mul_zero_zero emin prec (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
          (reg xuh xnh xul xnl) (reg yuh ynh yul ynl).
Proof.
intros xuh xnh xul xnl yuh ynh yul ynl Sx1 Sx2 Sy1 Sy2. unfold case_ok.
destruct (zero_zero_values xuh xnh xul xnl yuh ynh yul ynl) as [C [H0 H1]].
split; [exact C|].
intros t s [T1 T2] [S1 S2]; unfold mem.
unfold hi, nlo in T1, T2, S1, S2. cbn [lane0 lane1 hreg lreg] in T1, T2, S1, S2.
destruct (corners_0 (- (xnh + xnl)) (xuh + xul) (- (ynh + ynl)) (yuh + yul) t s
            (conj T1 T2) (conj S1 S2) ltac:(lra) ltac:(lra) ltac:(lra) ltac:(lra)) as [R1 R2].
replace (- (xnh + xnl) * - (ynh + ynl)) with ((xnh + xnl) * (ynh + ynl)) in R1 by ring.
replace (- (- (xnh + xnl) * (yuh + yul))) with ((xnh + xnl) * (yuh + yul)) in R2 by ring.
replace (- ((xuh + xul) * - (ynh + ynl))) with ((xuh + xul) * (ynh + ynl)) in R2 by ring.
split; lra.
Qed.

(** * Statement 3 *)

Lemma le0_true :
  forall h l, upper_normalized emin prec h l -> h + l <= 0 -> le0 h = true.
Proof.
intros h l N H. unfold le0. apply Rle_bool_true.
destruct (upper_normalized_sign emin prec _ _ N) as [[_ S] _]. now apply S.
Qed.

Lemma le0_false :
  forall h l, upper_normalized emin prec h l -> 0 < h + l -> le0 h = false.
Proof.
intros h l N H. unfold le0. apply Rle_bool_false.
destruct (Rlt_or_le 0 h) as [L|L]; trivial.
destruct (upper_normalized_sign emin prec _ _ N) as [[S _] _]. generalize (S L). lra.
Qed.

(* Both operands nonnegative (lower bounds -nlo >= 0): the probe's first case, in its words. *)
Theorem mul_branch_nonneg :
  forall x y : Rg, canonical emin prec x -> canonical emin prec y ->
  0 <= - nlo x -> 0 <= - nlo y ->
  mul_branch emin prec x y = mul_case emin prec 10 x y /\
  upper_pair (lane0 (hreg (mul_branch emin prec x y))) (lane0 (lreg (mul_branch emin prec x y)))
             (hi x * hi y) /\
  upper_pair (lane1 (hreg (mul_branch emin prec x y))) (lane1 (lreg (mul_branch emin prec x y)))
             (- ((- nlo x) * (- nlo y))) /\
  canonical emin prec (mul_branch emin prec x y).
Proof.
intros [[xuh xnh] [xul xnl]] [[yuh ynh] [yul ynl]] [Xu Xn] [Yu Yn] Lx Ly.
unfold hi, nlo in Lx, Ly. cbn [lane0 lane1 hreg lreg] in Xu, Xn, Yu, Yn, Lx, Ly.
assert (Ez : mul_branch emin prec (reg xuh xnh xul xnl) (reg yuh ynh yul ynl)
             = mul_case emin prec 10 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl)).
{ unfold mul_branch. cbn [lane0 lane1 hreg].
  rewrite (le0_true _ _ Xn), (le0_true _ _ Yn) by lra. reflexivity. }
rewrite Ez. split; [reflexivity|].
change (mul_case emin prec 10 (reg xuh xnh xul xnl) (reg yuh ynh yul ynl))
  with (mul_one emin prec (reg xuh xnh xul xnl) (reg yuh (- ynh) yul (- ynl))).
destruct (mul_one_correct xuh xnh xul xnl yuh (- ynh) yul (- ynl)) as [C [H0 H1]].
unfold hi, nlo in H0, H1 |- *. unfold upper_pair. cbn [lane0 lane1 hreg lreg fst snd].
split; [|split; [|exact C]].
- exact H0.
- replace (- (- (xnh + xnl) * - (ynh + ynl))) with ((xnh + xnl) * (- ynh + - ynl)) by ring.
  exact H1.
Qed.

(* Both operands contain zero in their interior: two candidates per lane and lexmax. *)
Theorem mul_branch_zero_zero :
  forall x y : Rg, canonical emin prec x -> canonical emin prec y ->
  - nlo x < 0 < hi x -> - nlo y < 0 < hi y ->
  mul_branch emin prec x y = mul_zero_zero emin prec x y /\
  upper_pair (lane0 (hreg (mul_branch emin prec x y))) (lane0 (lreg (mul_branch emin prec x y)))
             (Rmax ((- nlo x) * (- nlo y)) (hi x * hi y)) /\
  upper_pair (lane1 (hreg (mul_branch emin prec x y))) (lane1 (lreg (mul_branch emin prec x y)))
             (Rmax (- ((- nlo x) * hi y)) (- (hi x * (- nlo y)))) /\
  canonical emin prec (mul_branch emin prec x y).
Proof.
intros [[xuh xnh] [xul xnl]] [[yuh ynh] [yul ynl]] [Xu Xn] [Yu Yn] Lx Ly.
unfold hi, nlo in Lx, Ly. cbn [lane0 lane1 hreg lreg] in Xu, Xn, Yu, Yn, Lx, Ly.
assert (Ez : mul_branch emin prec (reg xuh xnh xul xnl) (reg yuh ynh yul ynl)
             = mul_zero_zero emin prec (reg xuh xnh xul xnl) (reg yuh ynh yul ynl)).
{ unfold mul_branch. cbn [lane0 lane1 hreg].
  rewrite (le0_false _ _ Xn), (le0_false _ _ Xu), (le0_false _ _ Yn), (le0_false _ _ Yu)
    by lra.
  reflexivity. }
rewrite Ez. split; [reflexivity|].
destruct (zero_zero_values xuh xnh xul xnl yuh ynh yul ynl) as [C [H0 H1]].
unfold hi, nlo in H0, H1 |- *. unfold upper_pair. cbn [lane0 lane1 hreg lreg fst snd].
split; [|split; [|exact C]].
- replace (- (xnh + xnl) * - (ynh + ynl)) with ((xnh + xnl) * (ynh + ynl)) by ring. exact H0.
- replace (- (- (xnh + xnl) * (yuh + yul))) with ((xnh + xnl) * (yuh + yul)) by ring.
  replace (- ((xuh + xul) * - (ynh + ynl))) with ((xuh + xul) * (ynh + ynl)) by ring.
  exact H1.
Qed.

(* Every case: containment and the invariant, for canonical operands (both lanes
   upper-normalized; the invariant is what makes the tests of mul_branch on the heads read the
   signs of the bounds). *)
Theorem mul_branch_correct :
  forall x y : Rg, canonical emin prec x -> canonical emin prec y ->
  canonical emin prec (mul_branch emin prec x y) /\
  forall t s, mem x t -> mem y s -> mem (mul_branch emin prec x y) (t * s).
Proof.
intros [[xuh xnh] [xul xnl]] [[yuh ynh] [yul ynl]] [Xu Xn] [Yu Yn].
cbn [lane0 lane1 hreg lreg fst snd] in Xu, Xn, Yu, Yn.
destruct (le0_upper_normalized emin prec _ _ Xu) as [XN1 XN0].
destruct (le0_upper_normalized emin prec _ _ Xn) as [XP1 XP0].
destruct (le0_upper_normalized emin prec _ _ Yu) as [YN1 YN0].
destruct (le0_upper_normalized emin prec _ _ Yn) as [YP1 YP0].
unfold mul_branch. cbn [lane0 lane1 hreg].
destruct (le0 xnh) eqn:EXP.
- specialize (XP1 eq_refl). destruct (le0 ynh) eqn:EYP.
  + exact (case_10 xuh xnh xul xnl yuh ynh yul ynl XP1 (YP1 eq_refl)).
  + specialize (YP0 eq_refl). destruct (le0 yuh) eqn:EYN.
    * exact (case_6 xuh xnh xul xnl yuh ynh yul ynl XP1 (YN1 eq_refl)).
    * exact (case_2 xuh xnh xul xnl yuh ynh yul ynl XP1 YP0 (YN0 eq_refl)).
- specialize (XP0 eq_refl). destruct (le0 xuh) eqn:EXN.
  + specialize (XN1 eq_refl). destruct (le0 ynh) eqn:EYP.
    * exact (case_9 xuh xnh xul xnl yuh ynh yul ynl XN1 (YP1 eq_refl)).
    * specialize (YP0 eq_refl). destruct (le0 yuh) eqn:EYN.
      -- exact (case_5 xuh xnh xul xnl yuh ynh yul ynl XN1 (YN1 eq_refl)).
      -- exact (case_1 xuh xnh xul xnl yuh ynh yul ynl XN1 YP0 (YN0 eq_refl)).
  + specialize (XN0 eq_refl). destruct (le0 ynh) eqn:EYP.
    * exact (case_8 xuh xnh xul xnl yuh ynh yul ynl XP0 XN0 (YP1 eq_refl)).
    * specialize (YP0 eq_refl). destruct (le0 yuh) eqn:EYN.
      -- exact (case_4 xuh xnh xul xnl yuh ynh yul ynl XP0 XN0 (YN1 eq_refl)).
      -- exact (case_0 xuh xnh xul xnl yuh ynh yul ynl XP0 XN0 YP0 (YN0 eq_refl)).
Qed.

End Branch.

Print Assumptions mul_branch_nonneg.
Print Assumptions mul_branch_zero_zero.
Print Assumptions mul_branch_correct.
