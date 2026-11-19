(* add_fast_2_2: the fast sum of two 2-limb numbers (JMP17 Algorithm 5, SloppyDWPlusDW),
   ending with Fast2Sum.

       (sh, sl) = two_sum(x0, y0)
       v        = RN(x1 + y1)
       w        = RN(sl + v)
       (z0, z1) = fast_two_sum(sh, w)

   Statement proved (add_fast_2_2_correct_c3): for x and y normalized, in any format with
   gradual underflow and precision at least 2, the result z is normalized and
       |z - (x + y)| <= 3 u^2 (|x| + |y|),
   with no underflow term. The bound is relative to |x| + |y|, not to |x + y|: when the
   operands have opposite signs and nearly cancel, the error relative to the sum is not
   bounded by any multiple of u^2. For operands of the same sign |x| + |y| = |x + y|, and
   the statement is the relative bound 3u^2 that JMP17 report for that case. The constant
   3 is approached from below by exhaustive runs on toy formats as the precision grows:
   the largest observed values are 1.03, 1.46, 2.02, 2.43, 2.69 at precisions 2 to 6, and
   2.84 in a restricted run at precision 7. (What the proof gives is slightly less than 3:
   (3 + 4u) / (1 + u)^2.)

   The proof is new; it has two parts, both in the format without underflow (the kernel
   only adds and subtracts, so with operands in the format with gradual underflow it
   computes the same values: Format.v, Transfer.v).

   1. The final Fast2Sum is error-free: z0 = RN(sh + w) and z0 + z1 = sh + w. Its usual
      hypothesis |w| <= |sh| is false for some operands (under 1% of them at precision 5),
      so the proof uses the weaker hypothesis of MR22's Fast2Sum theorem
      (F2Sum_correct_proof in third_party/mr22): sh is an integer multiple of the unit in
      the last place of w. Take |y0| <= |x0| (the kernel is symmetric).
      - If |x0 + y0| <= |y0|, the leading limbs cancel: x0 + y0 is a number of the format
        (Sterbenz), so sh = x0 + y0, sl = 0 and w = v. Both x0 and y0, hence sh, are
        integer multiples of ulp(y0), and |x0| <= 2 |y0| gives
        |v| <= ulp(x0)/2 + ulp(y0)/2 <= 2 ulp(y0), so the unit in the last place of v is
        at most ulp(y0). This is the case where |w| > |sh| can happen.
      - Otherwise |sh| >= |y0|, and |sl| <= ulp(sh)/2, |v| <= 3/2 ulp(sh), so that
        |sl + v| <= 2 ulp(sh) <= |sh| and |w| <= |sh|: the usual hypothesis holds.
      A pair returned by an error-free Fast2Sum is normalized, which gives the first
      half of the statement.
   2. The error is then w - (sl + x1 + y1): the two rounding errors of v and w. Each
      rounding to nearest moves t by at most u/(1 + u) |t|, the second limbs satisfy
      |x1| <= u |x|, and |sl| <= u (|x| + |y|); adding up gives
      u/(1 + u) * (3 + u/(1 + u)) * u (|x| + |y|) <= 3 u^2 (|x| + |y|). *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core Plus_error Relative Sterbenz.
From Double Require Import F2Sum DWPlus.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Transfer EFT.
Open Scope R_scope.

(** * The statements proved in this file *)

(* The generated statement add_fast_2_2_spec (proofs/gen/Statements.v) with its provisional
   constant 4, and the minimum precision 2 in place of the placeholder 1. *)
Definition add_fast_2_2_spec_draft : Prop :=
  forall emin prec : Z, (2 <= prec)%Z ->
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 ->
  normalized_2 emin prec y0 y1 ->
  let '(z0, z1) := add_fast_2_2 emin prec tie_even x0 x1 y0 y1 in
  normalized_2 emin prec z0 z1 /\
  Rabs ((z0 + z1) - ((x0 + x1) + (y0 + y1))) <= 4 * u prec ^ 2 * (Rabs (x0 + x1) + Rabs (y0 + y1)).

(* The same with the constant 3: the statement proposed for the kernel. *)
Definition add_fast_2_2_spec_c3 : Prop :=
  forall emin prec : Z, (2 <= prec)%Z ->
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 ->
  normalized_2 emin prec y0 y1 ->
  let '(z0, z1) := add_fast_2_2 emin prec tie_even x0 x1 y0 y1 in
  normalized_2 emin prec z0 z1 /\
  Rabs ((z0 + z1) - ((x0 + x1) + (y0 + y1))) <= 3 * u prec ^ 2 * (Rabs (x0 + x1) + Rabs (y0 + y1)).

(** * Real-number facts *)

(* Goals that are linear once the sign of every number under an absolute value is fixed. *)
Ltac split_abs :=
  unfold Rabs;
  repeat match goal with |- context [Rcase_abs ?x] => destruct (Rcase_abs x) end;
  intros; lra.

Lemma Rabs_le_sum : forall a b : R, Rabs a <= Rabs (a + b) + Rabs b.
Proof. intros a b. split_abs. Qed.

(* If adding b to a decreases the magnitude and leaves more than |b|, then b has the sign
   opposite to a and |b| < |a| / 2. *)
Lemma opposite_half :
  forall a b : R, Rabs b < Rabs (a + b) -> Rabs (a + b) < Rabs a -> 2 * Rabs b < Rabs a.
Proof. intros a b. split_abs. Qed.

Lemma pow2_double : forall e : Z, pow2 e = 2 * pow2 (e - 1).
Proof.
intros e. transitivity (pow2 (1 + (e - 1))). f_equal; ring.
now rewrite bpow_plus, pow2_1.
Qed.

(* The sum of the two rounding errors (d1 for v, d2 for w), given the bounds of each
   quantity in terms of M = |x| + |y|. Here r = u / (1 + u) bounds the relative error of
   one rounding, T = |x1 + y1|, s = |x0 + y0|, and sl is the magnitude of the error term
   of the first two_sum. *)
Lemma sloppy_arith :
  forall uu r M T d1 s sl d2 : R,
  0 < uu -> 0 <= r -> r * (1 + uu) = uu -> 0 <= M ->
  T <= uu * M -> d1 <= r * T ->
  s <= (1 + uu) * M -> sl <= r * s ->
  d2 <= r * (sl + (T + d1)) ->
  d1 + d2 <= 3 * uu ^ 2 * M.
Proof.
intros uu r M T d1 s sl d2 Hu Hr0 Hr HM HT Hd1 Hs Hsl Hd2.
assert (Hru : 0 <= r * uu) by (apply Rmult_le_pos; lra).
assert (Hr' : r + r * uu = uu) by (transitivity (r * (1 + uu)); [ring | exact Hr]).
assert (Hrr : r * r <= r * uu) by (apply Rmult_le_compat_l; lra).
assert (HuM : 0 <= uu * M) by (apply Rmult_le_pos; lra).
assert (H1 : d1 <= r * (uu * M)).
{ apply Rle_trans with (1 := Hd1). now apply Rmult_le_compat_l. }
assert (H2 : sl <= uu * M).
{ apply Rle_trans with (1 := Hsl). apply Rle_trans with (r * ((1 + uu) * M)).
  now apply Rmult_le_compat_l. rewrite <- Rmult_assoc, Hr. apply Rle_refl. }
assert (H3 : d2 <= r * (uu * M + (uu * M + r * (uu * M)))).
{ apply Rle_trans with (1 := Hd2). apply Rmult_le_compat_l; lra. }
apply Rle_trans with (r * (3 + r) * (uu * M)).
- replace (r * (3 + r) * (uu * M))
    with (r * (uu * M) + r * (uu * M + (uu * M + r * (uu * M)))) by ring.
  lra.
- replace (3 * uu ^ 2 * M) with (3 * uu * (uu * M)) by ring.
  apply Rmult_le_compat_r; trivial.
  replace (r * (3 + r)) with (3 * r + r * r) by ring.
  lra.
Qed.

(** * Without underflow *)

Section NoUnderflow.
Variable p : Z.
Hypothesis Hp2 : (2 <= p)%Z.

Let Hp : (1 < p)%Z.
Proof. lia. Qed.

Local Instance p_gt_0_fast : Prec_gt_0 p.
Proof. unfold Prec_gt_0. lia. Qed.

Notation rndx := (round radix2 (FLX_exp p) (Znearest tie_even)).
Notation formatx := (generic_format radix2 (FLX_exp p)).
Notation ulpx := (ulp radix2 (FLX_exp p)).
(* MR22's vocabulary: DW a b is "(a, b) is normalized" (a double-word number); F2S is
   Fast2Sum, and F2S_exact a b says that its second result is exactly a + b - RN(a + b). *)
Notation DW := (double_word p tie_even).
Notation F2S := (Fast2Sum p tie_even).
Notation F2S_exact := (Fast2Sum_correct p tie_even).

Let rndx_opp : forall x, rndx (- x) = - rndx x.
Proof. intros x. apply round_NE_opp. Qed.

Let two_le_3 : (radix2 <= 3)%Z.
Proof. simpl. lia. Qed.

Let two_le_pow : 2 <= pow2 (p - 1).
Proof. apply Rle_trans with (pow2 1). rewrite pow2_1. lra. apply bpow_le. lia. Qed.

Let Frndx : forall x, formatx (rndx x).
Proof. intros x. apply generic_format_round; auto with typeclass_instances. Qed.

(* Units in the last place, powers of two and their multiples. *)
Lemma ulpx_neq_0 : forall t, t <> 0 -> ulpx t = pow2 (mag radix2 t - p).
Proof. intros t Ht. rewrite ulp_neq_0 by exact Ht. reflexivity. Qed.

Lemma formatx_pow2 : forall e, formatx (pow2 e).
Proof. intros e. apply generic_format_bpow. unfold FLX_exp. lia. Qed.

(* 3 * 2^e has two significant bits. *)
Lemma formatx_3 : forall e, formatx (3 * pow2 e).
Proof.
intros e. apply generic_format_FLX. apply (FLX_spec radix2 p _ (Float radix2 3 e)).
- reflexivity.
- change (3 < 2 ^ p)%Z. apply Z.lt_le_trans with (2 ^ 2)%Z. reflexivity.
  apply Z.pow_le_mono_r; lia.
Qed.

(* A nonzero number of the format is at least 2^(p-1) units in its last place. *)
Lemma abs_ge_ulpx : forall t, t <> 0 -> pow2 (p - 1) * ulpx t <= Rabs t.
Proof.
intros t Ht. rewrite ulpx_neq_0 by exact Ht. rewrite <- bpow_plus.
replace (p - 1 + (mag radix2 t - p))%Z with (mag radix2 t - 1)%Z by ring.
now apply bpow_mag_le.
Qed.

(* Two consequences of normalization: the second limb is not larger than the first, and
   is zero when the first is. *)
Lemma DW_tail_le : forall a b, DW a b -> Rabs b <= Rabs a.
Proof.
intros a b H. generalize (@dw_ulp p Hp tie_even a b H). intros Hb.
destruct H as [[Fa Fb] _].
destruct (Req_dec a 0) as [Za|Za].
- rewrite Za, ulp_FLX_0 in Hb; auto with typeclass_instances.
  rewrite Za, Rabs_R0. lra.
- generalize (ulp_le_abs radix2 (FLX_exp p) a Za Fa). generalize (Rabs_pos b). lra.
Qed.

Lemma DW_zero : forall a b, DW a b -> a = 0 -> b = 0.
Proof.
intros a b H Za. generalize (DW_tail_le a b H). rewrite Za, Rabs_R0. intros Hb.
destruct (Req_dec b 0) as [Zb|Zb]; trivial.
generalize (Rabs_pos_lt b Zb). lra.
Qed.

(* Each rounding to nearest moves t by at most u / (1 + u) |t| (Flocq's
   relative_error_N_FLX'; the bound is due to Knuth, see also Jeannerod and Rump 2018). *)
Lemma rndx_error : forall t, Rabs (rndx t - t) <= pow2 (- p) / (1 + pow2 (- p)) * Rabs t.
Proof.
intros t.
assert (E : u_ro radix2 p = pow2 (- p)).
{ unfold u_ro. replace (- p + 1)%Z with (1 + - p)%Z by ring. rewrite bpow_plus, pow2_1. field. }
rewrite <- E. apply relative_error_N_FLX'. exact p_gt_0_fast.
Qed.

(* The second operand of the final Fast2Sum, as a function of the operands: w, with
   sh = RN(x0 + y0), sl = x0 + y0 - sh (the error term of two_sum) and v = RN(x1 + y1). *)
Definition sloppy_w (x0 x1 y0 y1 : R) : R :=
  rndx (x0 + y0 - rndx (x0 + y0) + rndx (x1 + y1)).

(** ** The final Fast2Sum is error-free *)

(* ... when |y0| <= |x0| *)
Lemma sloppy_F2S_ord :
  forall x0 x1 y0 y1, DW x0 x1 -> DW y0 y1 -> Rabs y0 <= Rabs x0 ->
  F2S_exact (rndx (x0 + y0)) (sloppy_w x0 x1 y0 y1).
Proof.
intros x0 x1 y0 y1 Dx Dy Hxy.
generalize (@dw_ulp p Hp tie_even x0 x1 Dx) (@dw_ulp p Hp tie_even y0 y1 Dy). intros Hx1 Hy1.
destruct (Dx) as [[Fx0 Fx1] _]. destruct (Dy) as [[Fy0 Fy1] _].
unfold sloppy_w.
set (v := rndx (x1 + y1)).
assert (Fv : formatx v) by (unfold v; apply Frndx).
destruct (Req_dec y0 0) as [Zy|Zy].
{ (* y = 0: the kernel computes Fast2Sum (x0, x1) *)
  assert (Zy1 : y1 = 0) by now apply DW_zero with y0.
  unfold v. rewrite Zy, Zy1, 2!Rplus_0_r.
  rewrite (round_generic radix2 (FLX_exp p) (Znearest tie_even) x0 Fx0).
  rewrite (round_generic radix2 (FLX_exp p) (Znearest tie_even) x1 Fx1).
  replace (x0 - x0 + x1) with x1 by ring.
  rewrite (round_generic radix2 (FLX_exp p) (Znearest tie_even) x1 Fx1).
  apply (F2Sum_correct_abs Hp rndx_opp two_le_3 Fx0 Fx1). now apply DW_tail_le. }
assert (Zx : x0 <> 0).
{ intros Z. rewrite Z, Rabs_R0 in Hxy. generalize (Rabs_pos_lt y0 Zy). lra. }
assert (Ux : ulpx x0 = pow2 (mag radix2 x0 - p)) by now apply ulpx_neq_0.
assert (Uy : ulpx y0 = pow2 (mag radix2 y0 - p)) by now apply ulpx_neq_0.
assert (Uyx : ulpx y0 <= ulpx x0) by (apply ulp_le; auto with typeclass_instances).
destruct (Rle_or_lt (Rabs (x0 + y0)) (Rabs y0)) as [HE|HN].
- (* The leading limbs cancel: x0 + y0 is a number of the format, sl = 0 and w = v. *)
  assert (Fs : formatx (x0 + y0)).
  { apply generic_format_plus_weak; auto with typeclass_instances.
    rewrite Rmin_right by exact Hxy. exact HE. }
  rewrite (round_generic radix2 (FLX_exp p) (Znearest tie_even) (x0 + y0) Fs).
  replace (x0 + y0 - (x0 + y0) + v) with v by ring.
  rewrite (round_generic radix2 (FLX_exp p) (Znearest tie_even) v Fv).
  destruct (Req_dec v 0) as [Zv|Zv].
  { rewrite Zv. unfold Fast2Sum_correct. rewrite (Fast2Sumf0 tie_even Fs). simpl. ring. }
  (* x0, y0 and their sum are integer multiples of 2^k, the unit in the last place of y0 *)
  set (k := (mag radix2 y0 - p)%Z).
  destruct (FLX_multiple p y0 (mag radix2 y0 - 1) Fy0) as [my Hmy].
  { now apply bpow_mag_le. }
  destruct (FLX_multiple p x0 (mag radix2 y0 - 1) Fx0) as [mx Hmx].
  { apply Rle_trans with (2 := Hxy). now apply bpow_mag_le. }
  replace (mag radix2 y0 - 1 - p + 1)%Z with k in Hmx, Hmy by (unfold k; ring).
  (* |x0| <= 2 |y0|, so ulp(x0) <= 2^(k+1) *)
  assert (Hmx0 : (mag radix2 x0 <= mag radix2 y0 + 1)%Z).
  { apply mag_le_bpow; trivial.
    apply Rle_lt_trans with (2 * Rabs y0).
    - generalize (Rabs_le_sum x0 y0). lra.
    - rewrite bpow_plus, pow2_1. generalize (bpow_mag_gt radix2 y0). lra. }
  (* |v| <= 2^(k+1), so the unit in the last place of v is at most 2^k *)
  assert (Hv : Rabs v <= pow2 (k + 1)).
  { unfold v. apply (abs_round_le_generic radix2 (FLX_exp p) (Znearest tie_even)).
    apply formatx_pow2.
    apply Rle_trans with (1 := Rabs_triang x1 y1).
    assert (ulpx x0 <= pow2 (k + 1)) by (rewrite Ux; apply bpow_le; unfold k; lia).
    assert (ulpx y0 <= pow2 (k + 1)) by (rewrite Uy; apply bpow_le; unfold k; lia).
    lra. }
  assert (Hmv : (mag radix2 v <= mag radix2 y0)%Z).
  { apply Z.le_trans with (k + 2)%Z; [|unfold k; lia].
    apply mag_le_bpow; trivial.
    apply Rle_lt_trans with (1 := Hv). apply bpow_lt. lia. }
  apply (F2Sum_correct_proof Hp rndx_opp two_le_3 Fs Fv).
  exists (Float radix2 (mx + my) k). split.
  + change (x0 + y0 = IZR (mx + my) * pow2 k).
    rewrite plus_IZR, Rmult_plus_distr_r, <- Hmx, <- Hmy. reflexivity.
  + change (mag radix2 v - p <= k)%Z. unfold k. lia.
- (* Otherwise |w| <= |sh|. *)
  set (sh := rndx (x0 + y0)).
  assert (Fsh : formatx sh) by apply Frndx.
  assert (Hshy : Rabs y0 <= Rabs sh).
  { unfold sh. apply (abs_round_ge_generic radix2 (FLX_exp p) (Znearest tie_even)).
    now apply generic_format_abs. now apply Rlt_le. }
  assert (Zsh : sh <> 0).
  { intros Z. rewrite Z, Rabs_R0 in Hshy. generalize (Rabs_pos_lt y0 Zy). lra. }
  set (U := ulpx sh).
  assert (HU : U = pow2 (mag radix2 sh - p)) by now apply ulpx_neq_0.
  assert (HU0 : 0 <= U) by apply ulp_ge_0.
  assert (Hsl : Rabs (x0 + y0 - sh) <= / 2 * U).
  { rewrite <- Rabs_Ropp, Ropp_minus_distr. unfold U, sh.
    apply error_le_half_ulp_round; auto with typeclass_instances. }
  assert (Hbig : 2 * U <= Rabs sh).
  { apply Rle_trans with (pow2 (p - 1) * U).
    - now apply Rmult_le_compat_r.
    - now apply abs_ge_ulpx. }
  (* it is enough that |v| <= 3/2 ulp(sh), since then |sl + v| <= 2 ulp(sh) <= |sh| *)
  assert (Hsuff : Rabs v <= 3 / 2 * U -> F2S_exact sh (rndx (x0 + y0 - sh + v))).
  { intros Hv. apply (F2Sum_correct_abs Hp rndx_opp two_le_3 Fsh). apply Frndx.
    apply (abs_round_le_generic radix2 (FLX_exp p) (Znearest tie_even)).
    now apply generic_format_abs.
    apply Rle_trans with (1 := Rabs_triang _ _). lra. }
  apply Hsuff.
  assert (F3 : formatx (3 / 2 * U)).
  { replace (3 / 2 * U) with (3 * pow2 (mag radix2 sh - p - 1)).
    apply formatx_3.
    rewrite HU, (pow2_double (mag radix2 sh - p)). field. }
  unfold v. apply (abs_round_le_generic radix2 (FLX_exp p) (Znearest tie_even)). exact F3.
  apply Rle_trans with (1 := Rabs_triang x1 y1).
  destruct (Rle_or_lt (Rabs x0) (Rabs sh)) as [H1|H2].
  + (* |x0| <= |sh|: both second limbs are at most ulp(sh)/2 *)
    assert (ulpx x0 <= U) by (unfold U; apply ulp_le; auto with typeclass_instances).
    lra.
  + (* |sh| < |x0|: then |y0| < |x0|/2, so |y1| <= ulp(x0)/4, and ulp(x0) <= 2 ulp(sh) *)
    assert (Hsx : Rabs (x0 + y0) < Rabs x0).
    { destruct (Rle_or_lt (Rabs x0) (Rabs (x0 + y0))) as [H|H]; trivial. exfalso.
      apply (Rlt_irrefl (Rabs x0)). apply Rle_lt_trans with (2 := H2).
      unfold sh. apply (abs_round_ge_generic radix2 (FLX_exp p) (Znearest tie_even)).
      now apply generic_format_abs. exact H. }
    assert (Hhalf : 2 * Rabs y0 < Rabs x0) by now apply opposite_half.
    assert (Hmy : (mag radix2 y0 <= mag radix2 x0 - 1)%Z).
    { apply mag_le_bpow; trivial.
      generalize (bpow_mag_gt radix2 x0). rewrite (pow2_double (mag radix2 x0)). lra. }
    assert (Hms : (mag radix2 x0 - 1 <= mag radix2 sh)%Z).
    { apply mag_ge_bpow.
      unfold sh. apply (abs_round_ge_generic radix2 (FLX_exp p) (Znearest tie_even)).
      apply formatx_pow2.
      generalize (bpow_mag_le radix2 x0 Zx). rewrite (pow2_double (mag radix2 x0 - 1)).
      generalize (Rabs_le_sum x0 y0). lra. }
    assert (Hy4 : ulpx y0 <= / 2 * ulpx x0).
    { rewrite Uy, Ux, (pow2_double (mag radix2 x0 - p)).
      replace (/ 2 * (2 * pow2 (mag radix2 x0 - p - 1))) with (pow2 (mag radix2 x0 - p - 1)) by field.
      apply bpow_le. lia. }
    assert (Hx2 : ulpx x0 <= 2 * U).
    { rewrite Ux, HU. replace (2 * pow2 (mag radix2 sh - p)) with (pow2 (mag radix2 sh - p + 1)).
      apply bpow_le. lia.
      rewrite (pow2_double (mag radix2 sh - p + 1)). f_equal. f_equal. ring. }
    lra.
Qed.

(* ... in general: the term is symmetric in x and y. *)
Lemma sloppy_F2S :
  forall x0 x1 y0 y1, DW x0 x1 -> DW y0 y1 ->
  F2S_exact (rndx (x0 + y0)) (sloppy_w x0 x1 y0 y1).
Proof.
intros x0 x1 y0 y1 Dx Dy.
destruct (Rle_or_lt (Rabs y0) (Rabs x0)) as [H|H].
- now apply sloppy_F2S_ord.
- generalize (sloppy_F2S_ord y0 y1 x0 x1 Dy Dx (Rlt_le _ _ H)).
  unfold sloppy_w. now rewrite (Rplus_comm y0 x0), (Rplus_comm y1 x1).
Qed.

(** ** The two rounding errors *)

(* |w - (sl + x1 + y1)| <= 3 u^2 (|x| + |y|): this is the error of the result once the
   final Fast2Sum is known to be error-free. *)
Lemma sloppy_error :
  forall x0 x1 y0 y1, DW x0 x1 -> DW y0 y1 ->
  Rabs (sloppy_w x0 x1 y0 y1 - (x0 + y0 - rndx (x0 + y0) + (x1 + y1)))
  <= 3 * pow2 (- p) ^ 2 * (Rabs (x0 + x1) + Rabs (y0 + y1)).
Proof.
intros x0 x1 y0 y1 [_ Hx] [_ Hy]. unfold sloppy_w.
set (uu := pow2 (- p)). set (r := uu / (1 + uu)).
assert (Hu : 0 < uu) by apply bpow_gt_0.
assert (Hr0 : 0 <= r).
{ unfold r. apply Rmult_le_pos. lra. apply Rlt_le, Rinv_0_lt_compat. lra. }
assert (Hr : r * (1 + uu) = uu) by (unfold r; field; lra).
assert (Hru : r <= uu).
{ assert (0 <= r * uu) by (apply Rmult_le_pos; lra). lra. }
assert (Herr : forall t, Rabs (rndx t - t) <= r * Rabs t) by apply rndx_error.
set (sl := x0 + y0 - rndx (x0 + y0)). set (T := x1 + y1). set (v := rndx T).
(* the second limbs: |x1| <= u |x| *)
assert (Htail : forall a b, a = rndx (a + b) -> Rabs b <= uu * Rabs (a + b)).
{ intros a b H.
  replace b with (- (rndx (a + b) - (a + b))) at 1 by (rewrite <- H; ring).
  rewrite Rabs_Ropp. apply Rle_trans with (1 := Herr _).
  apply Rmult_le_compat_r. apply Rabs_pos. exact Hru. }
generalize (Htail x0 x1 Hx) (Htail y0 y1 Hy). intros Hx1 Hy1.
set (M := Rabs (x0 + x1) + Rabs (y0 + y1)).
assert (HM : 0 <= M).
{ unfold M. generalize (Rabs_pos (x0 + x1)) (Rabs_pos (y0 + y1)). lra. }
assert (HT : Rabs T <= uu * M).
{ unfold T, M. apply Rle_trans with (1 := Rabs_triang x1 y1).
  rewrite Rmult_plus_distr_l. lra. }
assert (Hs : Rabs (x0 + y0) <= (1 + uu) * M).
{ apply Rle_trans with (Rabs (x0 + x1) + Rabs (y0 + y1) + (Rabs x1 + Rabs y1)).
  - clear. split_abs.
  - unfold M. rewrite Rmult_plus_distr_r, Rmult_1_l, Rmult_plus_distr_l. lra. }
assert (Hsl : Rabs sl <= r * Rabs (x0 + y0)).
{ unfold sl. rewrite <- Rabs_Ropp, Ropp_minus_distr. apply Herr. }
assert (Hd2 : Rabs (rndx (sl + v) - (sl + v)) <= r * (Rabs sl + (Rabs T + Rabs (v - T)))).
{ apply Rle_trans with (1 := Herr _). apply Rmult_le_compat_l; trivial.
  apply Rle_trans with (1 := Rabs_triang _ _).
  apply Rplus_le_compat_l.
  replace v with (T + (v - T)) at 1 by ring. apply Rabs_triang. }
replace (rndx (sl + v) - (sl + T)) with ((v - T) + (rndx (sl + v) - (sl + v))) by ring.
apply Rle_trans with (1 := Rabs_triang _ _).
apply (sloppy_arith uu r M (Rabs T) (Rabs (v - T)) (Rabs (x0 + y0)) (Rabs sl)); trivial.
exact (Herr T).
Qed.

End NoUnderflow.

(** * With gradual underflow *)

Section WithUnderflow.
Variable emin prec : Z.
Hypothesis Hp2 : (2 <= prec)%Z.

Local Instance prec_gt_0_fast : Prec_gt_0 prec.
Proof. unfold Prec_gt_0. lia. Qed.

Notation format := (generic_format radix2 (FLT_exp emin prec)).
Notation rnd := (round radix2 (FLT_exp emin prec) (Znearest tie_even)).
Notation rndx := (round radix2 (FLX_exp prec) (Znearest tie_even)).

(* With operands in the format, the kernel of the model computes the Fast2Sum, in the
   format without underflow, of sh = RN(x0 + y0) and of the term w defined above. *)
Lemma add_fast_2_2_term :
  forall x0 x1 y0 y1, format x0 -> format x1 -> format y0 -> format y1 ->
  add_fast_2_2 emin prec tie_even x0 x1 y0 y1
  = Fast2Sum prec tie_even (rndx (x0 + y0)) (sloppy_w prec x0 x1 y0 y1).
Proof.
intros x0 x1 y0 y1 F0 F1 G0 G1.
assert (Fsl : format (snd (two_sum emin prec tie_even x0 y0))).
{ unfold two_sum. cbv zeta. cbn [snd]. apply generic_format_round; auto with typeclass_instances. }
generalize (two_sum_exact emin prec Hp2 x0 y0 F0 G0) Fsl. clear Fsl.
unfold add_fast_2_2.
destruct (two_sum emin prec tie_even x0 y0) as [sh sl]. cbn [fst snd].
intros [Hsh Hsum] Fsl. cbv zeta.
assert (Fsh : format sh).
{ rewrite Hsh. apply generic_format_round; auto with typeclass_instances. }
assert (Fv : format (rnd (x1 + y1))) by (apply generic_format_round; auto with typeclass_instances).
assert (Ev : rnd (x1 + y1) = rndx (x1 + y1)) by (apply round_plus_FLT_FLX; auto with typeclass_instances).
assert (Ew : rnd (sl + rnd (x1 + y1)) = rndx (sl + rnd (x1 + y1))).
{ apply round_plus_FLT_FLX; auto with typeclass_instances. }
assert (Esh : sh = rndx (x0 + y0)).
{ rewrite Hsh. apply round_plus_FLT_FLX; auto with typeclass_instances. }
assert (Esl : sl = x0 + y0 - rndx (x0 + y0)) by (rewrite <- Esh; lra).
assert (Fw : format (rnd (sl + rnd (x1 + y1)))).
{ apply generic_format_round; auto with typeclass_instances. }
rewrite (fast_two_sum_FLX emin prec tie_even _ _ Fsh Fw).
rewrite Ew, Ev, Esl, Esh. reflexivity.
Qed.

End WithUnderflow.

(** * The statements *)

Theorem add_fast_2_2_correct_c3 : add_fast_2_2_spec_c3.
Proof.
intros emin prec Hp x0 x1 y0 y1 [F0 [F1 Hx]] [G0 [G1 Hy]].
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
assert (Hp1 : (1 < prec)%Z) by lia.
unfold fmt in F0, F1, G0, G1.
(* the operands are normalized in the format without underflow as well *)
assert (Dx : double_word prec tie_even x0 x1).
{ repeat split; try now apply generic_format_FLX_FLT with emin.
  rewrite Hx at 1. unfold RN. apply round_plus_FLT_FLX; auto with typeclass_instances. }
assert (Dy : double_word prec tie_even y0 y1).
{ repeat split; try now apply generic_format_FLX_FLT with emin.
  rewrite Hy at 1. unfold RN. apply round_plus_FLT_FLX; auto with typeclass_instances. }
(* the limbs of the result are numbers of the format *)
assert (Fz : fmt emin prec (fst (add_fast_2_2 emin prec tie_even x0 x1 y0 y1)) /\
             fmt emin prec (snd (add_fast_2_2 emin prec tie_even x0 x1 y0 y1))).
{ unfold add_fast_2_2, two_sum, fast_two_sum. cbv zeta beta iota. cbn [fst snd].
  split; apply generic_format_round; auto with typeclass_instances. }
(* the final Fast2Sum is error-free, hence returns a normalized pair *)
generalize (sloppy_F2S prec Hp x0 x1 y0 y1 Dx Dy). intros Hc.
generalize (F2Sum_correct_DW' Hp1 Hc) (sloppy_error prec Hp x0 x1 y0 y1 Dx Dy).
unfold Fast2Sum_correct in Hc. cbv zeta in Hc. revert Hc.
rewrite <- (add_fast_2_2_term emin prec Hp x0 x1 y0 y1 F0 F1 G0 G1).
destruct Fz as [Fz0 Fz1].
destruct (add_fast_2_2 emin prec tie_even x0 x1 y0 y1) as [z0 z1].
cbn [fst snd] in *.
intros Hc [_ Hz] Hb. split.
- repeat split; trivial.
  rewrite Hz at 1. unfold RN. symmetry. apply round_plus_FLT_FLX; auto with typeclass_instances.
- replace (z0 + z1 - (x0 + x1 + (y0 + y1)))
    with (sloppy_w prec x0 x1 y0 y1
          - (x0 + y0 - round radix2 (FLX_exp prec) (Znearest tie_even) (x0 + y0) + (x1 + y1)))
    by (rewrite Hc; ring).
  exact Hb.
Qed.

(* The generated statement with its provisional constant 4 follows. *)
Theorem add_fast_2_2_correct_draft : add_fast_2_2_spec_draft.
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny.
generalize (add_fast_2_2_correct_c3 emin prec Hp x0 x1 y0 y1 Nx Ny).
destruct (add_fast_2_2 emin prec tie_even x0 x1 y0 y1) as [z0 z1].
intros [Hn Hb]. split; trivial.
apply Rle_trans with (1 := Hb).
apply Rmult_le_compat_r.
- generalize (Rabs_pos (x0 + x1)) (Rabs_pos (y0 + y1)). lra.
- assert (0 <= u prec ^ 2) by (apply pow_le, bpow_ge_0). lra.
Qed.
