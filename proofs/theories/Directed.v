(* The directed steps on one limb: upper bounds of a sum and of a product, computed with
   one rounding to nearest and one step to the next number of the format.

       radd(a, b) = succ(RN(a + b))        rmul(a, b) = succ(RN(a b))

   for numbers a, b >= 0 of the format, where succ(s) is the smallest number of the format
   above s. They are what a ball's radius is computed with: the radius must never be
   rounded down.

   Notation: F is the format (precision prec, gradual underflow, smallest positive number
   eta = 2^emin, no largest number); u = 2^-prec; RN is rounding to nearest, ties to even;
   ulp(s) is the distance from s >= 0 to succ(s), so ulp(0) = eta, ulp(s) = eta for
   s < 2^(emin + prec), and at a power of two ulp(s) is the spacing ABOVE s. Write x for
   the exact sum or product, s = RN(x), r = succ(s).

   What is proved. The generated statements radd_spec and rmul_spec
   (proofs/gen/Statements.v; theorems radd_correct and rmul_correct) are items 2 and 3
   below in the words of the claim "upper": x <= r, and r - x <= (3/2) (r - pred(r)),
   where pred(r) is the largest number of F below r. Since r = succ(s), pred(r) is s, and
   the gap r - pred(r) is ulp(s). They are stated from precision 2 on, as the kernels'
   descriptions say, but the proof needs only a positive precision. All four items
   together are the theorems radd_facts and rmul_facts, for prec >= 2:
     1. r is a number of F;
     2. x < r, strictly; more precisely r - x >= ulp(s) / 2;
     3. r - x <= (3/2) ulp(s). This is the sharp constant: equality holds whenever x is
        halfway between two numbers of F and rounds up. It is stated with the ulp of
        s = RN(x); since ulp(s) <= ulp(r) it also holds with the ulp of the result r
        (lemma up_excess_ulp_result), which is the weaker statement when r is a power of
        two, because the spacing doubles there;
     4. r - x <= 3 u x + eta for the sum, and r - x <= 3 u x + (3/2) eta for the product.
        In fact the maximum of the two terms is enough, not their sum (radd_excess_max,
        rmul_excess_max): r - x <= 3 u x when x >= 2^(emin + prec - 1), and below that
        r - x = eta for the sum (which is then exact) and r - x <= (3/2) eta for the
        product.
   Items 1 to 3 hold for every precision and every tie rule. Item 4 needs prec >= 2: with
   prec = 1 (u = 1/2, the numbers of F are 0 and the powers of two) and a = 8 eta,
   b = 4 eta, the sum 12 eta is halfway between 8 eta and 16 eta and rounds to 16 eta,
   whose successor is 32 eta: the excess 20 eta is more than 3 u x + eta = 19 eta.
   The constant 3 is the best integer; for prec >= 3 the sharp one is 3 / (1 + u)
   (lemma up_excess_rel_sharp), reached at prec = 3 and approached from below for larger
   precisions. The terms eta and (3/2) eta are sharp: a = b = 0 gives r = eta, and a
   product just above eta / 2 rounds to eta and gives r = 2 eta.

   The model has no largest number. In a format with one, the successor of the largest
   number is +infinity, which is still an upper bound.

   The proofs are elementary: s is within half a unit in the last place of x, and it is at
   least as close to x as the power of two below x. *)
From Stdlib Require Import Reals ZArith Lia Lra Psatz.
From Flocq Require Import Core Plus_error.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format.
Open Scope R_scope.

(** * Two inequalities between real numbers *)

(* Here B is the power of two at or below x, u B is half the spacing of F above B, and s
   is a number within u B of x that is at least as close to x as B is. *)
Lemma excess_arith_same_binade :
  forall u B x s : R,
  0 < u -> 0 < B -> B <= x ->
  s - x <= u * B -> s - x <= x - B ->
  s + 2 * u * B - x <= 3 * u * x.
Proof.
intros u B x s Hu HB Hx H1 H2.
assert (H0 : 0 <= u * (x - B)) by (apply Rmult_le_pos; lra).
destruct (Rle_or_lt (u * B) (x - B)) as [H|H]; nra.
Qed.

(* Here x is just below the power of two 2 B and rounds up to it; the spacing above 2 B
   is 4 u B. *)
Lemma excess_arith_next_binade :
  forall u B x : R,
  0 < u -> 3 * u <= 1 -> 0 < B ->
  2 * B - x <= u * B ->
  2 * B + 4 * u * B - x <= 3 * u * x.
Proof.
intros u B x Hu Hu3 HB H.
assert (H0 : 0 <= u * (x - (2 * B - u * B))) by (apply Rmult_le_pos; lra).
assert (H1 : 0 <= u * B * (1 - 3 * u)).
{ apply Rmult_le_pos; [apply Rmult_le_pos|]; lra. }
nra.
Qed.

(* The same two with the sharp constant 3 / (1 + u), written without a division. *)
Lemma excess_arith_same_binade_sharp :
  forall u B x s : R,
  0 < u -> 2 * u <= 1 -> 0 < B -> B <= x ->
  s - x <= u * B -> s - x <= x - B ->
  (s + 2 * u * B - x) * (1 + u) <= 3 * u * x.
Proof.
intros u B x s Hu Hu2 HB Hx H1 H2.
destruct (Rle_or_lt (u * B) (x - B)) as [H|H].
- assert (H0 : 0 <= u * (x - B - u * B)) by (apply Rmult_le_pos; lra).
  assert (H3 : (s + 2 * u * B - x) * (1 + u) <= 3 * (u * B) * (1 + u)).
  { apply Rmult_le_compat_r; lra. }
  nra.
- assert (H0 : 0 <= (u * B - (x - B)) * (1 - 2 * u)) by (apply Rmult_le_pos; lra).
  assert (H3 : (s + 2 * u * B - x) * (1 + u) <= (x - B + 2 * (u * B)) * (1 + u)).
  { apply Rmult_le_compat_r; lra. }
  nra.
Qed.

Lemma excess_arith_next_binade_sharp :
  forall u B x : R,
  0 < u -> 8 * u <= 1 -> 0 < B ->
  2 * B - x <= u * B ->
  (2 * B + 4 * u * B - x) * (1 + u) <= 3 * u * x.
Proof.
intros u B x Hu Hu8 HB H.
assert (H0 : 0 <= u * (x - (2 * B - u * B))) by (apply Rmult_le_pos; lra).
assert (H1 : 0 <= u * B * (1 - 8 * u)).
{ apply Rmult_le_pos; [apply Rmult_le_pos|]; lra. }
assert (H3 : (2 * B + 4 * u * B - x) * (1 + u) <= 5 * (u * B) * (1 + u)).
{ apply Rmult_le_compat_r; lra. }
nra.
Qed.

(** * The successor of a rounded nonnegative number *)

Section Step.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Variable choice : Z -> bool.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest choice)).
Notation ulp := (ulp radix2 fexp).
Notation succ := (succ radix2 fexp).
Notation pred := (pred radix2 fexp).

(* The spacing of the format is never zero: below 2^(emin + prec) it is eta. *)
Lemma ulp_FLT_gt_0 : forall x, 0 < ulp x.
Proof.
intros x. destruct (Req_dec x 0) as [Zx|Zx].
- rewrite Zx, ulp_FLT_0; trivial. apply bpow_gt_0.
- rewrite ulp_neq_0 by exact Zx. apply bpow_gt_0.
Qed.

Lemma rnd_ge_0 : forall x, 0 <= x -> 0 <= rnd x.
Proof.
intros x Hx. apply round_ge_generic; auto with typeclass_instances.
apply generic_format_0.
Qed.

(* 1. The result is a number of the format. *)
Lemma up_format : forall x, format (succ (rnd x)).
Proof.
intros x. apply generic_format_succ; auto with typeclass_instances.
apply generic_format_round; auto with typeclass_instances.
Qed.

(* For s >= 0 the successor is s + ulp(s): this is the definition of ulp. *)
Lemma up_eq : forall x, 0 <= x -> succ (rnd x) = rnd x + ulp (rnd x).
Proof. intros x Hx. apply succ_eq_pos. now apply rnd_ge_0. Qed.

(* 2 and 3. The result exceeds x by at least half and at most three halves of the
   spacing above s = RN(x): s is within half that spacing of x. *)
Lemma up_excess_ulp :
  forall x, 0 <= x ->
  / 2 * ulp (rnd x) <= succ (rnd x) - x <= 3 / 2 * ulp (rnd x).
Proof.
intros x Hx. rewrite up_eq by exact Hx.
assert (H : Rabs (rnd x - x) <= / 2 * ulp (rnd x)).
{ apply error_le_half_ulp_round; auto with typeclass_instances. }
apply Rabs_le_inv in H. lra.
Qed.

Lemma up_above : forall x, 0 <= x -> x < succ (rnd x).
Proof.
intros x Hx. generalize (up_excess_ulp x Hx) (ulp_FLT_gt_0 (rnd x)). lra.
Qed.

(* The gap below the result, r - pred(r), is the spacing above s: the largest number of
   the format below succ(s) is s itself. *)
Lemma up_gap : forall x, 0 <= x -> succ (rnd x) - pred (succ (rnd x)) = ulp (rnd x).
Proof.
intros x Hx.
assert (Fs : format (rnd x)) by (apply generic_format_round; auto with typeclass_instances).
rewrite (pred_succ radix2 fexp (rnd x) Fs), up_eq by exact Hx. ring.
Qed.

(* 2 and 3 in the words of the claim "upper": the result is at least x, and exceeds it by
   at most 3/2 of the gap below the result. *)
Lemma up_upper :
  forall x, 0 <= x ->
  x <= succ (rnd x) /\ succ (rnd x) - x <= 3 / 2 * (succ (rnd x) - pred (succ (rnd x))).
Proof.
intros x Hx. split.
- apply Rlt_le. now apply up_above.
- rewrite up_gap by exact Hx. apply (up_excess_ulp x Hx).
Qed.

(* The result is not negative. *)
Lemma up_ge_0 : forall x, 0 <= x -> 0 <= succ (rnd x).
Proof. intros x Hx. apply Rlt_le, Rle_lt_trans with (1 := Hx). now apply up_above. Qed.

(* 3, with the spacing above the result instead: weaker when the result is a power of
   two. *)
Lemma up_excess_ulp_result :
  forall x, 0 <= x -> succ (rnd x) - x <= 3 / 2 * ulp (succ (rnd x)).
Proof.
intros x Hx. apply Rle_trans with (1 := proj2 (up_excess_ulp x Hx)).
apply Rmult_le_compat_l. lra.
apply ulp_le_pos; auto with typeclass_instances.
- now apply rnd_ge_0.
- rewrite up_eq by exact Hx. generalize (ulp_FLT_gt_0 (rnd x)). lra.
Qed.

(* What the proofs of item 4 use, for x in the normal range: with 2^(e-1) <= x < 2^e and
   B = 2^(e-1), the rounding s of x lies between B and 2 B, is within u B of x, and is at
   least as close to x as B is; the spacing above s is 2 u B if s < 2 B and 4 u B if
   s = 2 B. *)
Lemma up_normal_facts :
  forall x, pow2 (emin + prec - 1) <= x ->
  exists B : R,
  0 < B /\ B <= x /\
  rnd x - x <= pow2 (- prec) * B /\
  rnd x - x <= x - B /\
  ((rnd x < 2 * B /\ ulp (rnd x) = 2 * pow2 (- prec) * B) \/
   (rnd x = 2 * B /\ ulp (rnd x) = 4 * pow2 (- prec) * B)).
Proof.
intros x Hx.
assert (Hp : (0 < prec)%Z) by exact prec_gt_0_.
assert (Hx0 : 0 < x) by (apply Rlt_le_trans with (2 := Hx); apply bpow_gt_0).
destruct (mag radix2 x) as [e He].
specialize (He (Rgt_not_eq _ _ Hx0)). rewrite Rabs_pos_eq in He by lra.
destruct He as [He1 He2].
assert (Hex : (emin + prec <= e)%Z).
{ assert (emin + prec - 1 < e)%Z by (apply (lt_bpow radix2); lra). lia. }
exists (pow2 (e - 1)).
assert (HB0 : 0 < pow2 (e - 1)) by apply bpow_gt_0.
assert (HU : pow2 (e - prec) = 2 * pow2 (- prec) * pow2 (e - 1)).
{ replace (e - prec)%Z with (1 + - prec + (e - 1))%Z by ring.
  now rewrite 2!bpow_plus, pow2_1. }
assert (HU2 : pow2 (e + 1 - prec) = 4 * pow2 (- prec) * pow2 (e - 1)).
{ replace (e + 1 - prec)%Z with (2 + - prec + (e - 1))%Z by ring.
  now rewrite 2!bpow_plus, pow2_2. }
assert (HB2 : pow2 e = 2 * pow2 (e - 1)).
{ replace e with (1 + (e - 1))%Z at 1 by ring. now rewrite bpow_plus, pow2_1. }
assert (FB : format (pow2 (e - 1))).
{ apply generic_format_bpow. unfold FLT_exp. lia. }
assert (FB2 : format (pow2 e)).
{ apply generic_format_bpow. unfold FLT_exp. lia. }
assert (Hs1 : pow2 (e - 1) <= rnd x).
{ apply round_ge_generic; auto with typeclass_instances. }
assert (Hs2 : rnd x <= pow2 e).
{ apply round_le_generic; auto with typeclass_instances. lra. }
assert (Hux : ulp x = pow2 (e - prec)).
{ rewrite ulp_neq_0 by lra. unfold cexp.
  rewrite (mag_unique_pos radix2 x e) by (split; assumption).
  unfold FLT_exp. f_equal. lia. }
assert (Hs3 : Rabs (rnd x - x) <= / 2 * ulp x).
{ apply error_le_half_ulp; auto with typeclass_instances. }
rewrite Hux, HU in Hs3.
assert (Hs4 : Rabs (rnd x - x) <= Rabs (pow2 (e - 1) - x)).
{ destruct (round_N_pt radix2 fexp choice x) as [_ HN]. now apply HN. }
rewrite (Rabs_left1 (pow2 (e - 1) - x)) in Hs4 by lra.
generalize (Rle_abs (rnd x - x)). intros Habs.
repeat split; try lra.
destruct Hs2 as [Hlt|Heq].
- left. split. lra.
  rewrite ulp_neq_0 by lra. unfold cexp.
  rewrite (mag_unique_pos radix2 (rnd x) e) by (split; assumption).
  rewrite <- HU. unfold FLT_exp. f_equal. lia.
- right. split. lra.
  rewrite Heq, ulp_bpow, <- HU2. unfold FLT_exp. f_equal. lia.
Qed.

(* 4, in the normal range: the excess is at most 3 u x. *)
Lemma up_excess_rel :
  (2 <= prec)%Z ->
  forall x, pow2 (emin + prec - 1) <= x ->
  succ (rnd x) - x <= 3 * pow2 (- prec) * x.
Proof.
intros Hp x Hx.
assert (Hx0 : 0 <= x) by (apply Rle_trans with (2 := Hx); apply bpow_ge_0).
assert (Hu0 : 0 < pow2 (- prec)) by apply bpow_gt_0.
assert (Hu4 : pow2 (- prec) <= / 4).
{ change (/ 4) with (pow2 (-2)). apply bpow_le. lia. }
rewrite up_eq by exact Hx0.
destruct (up_normal_facts x Hx) as [B [HB0 [HBx [H1 [H2 [[H3 H4]|[H3 H4]]]]]]]; rewrite H4.
- now apply excess_arith_same_binade.
- rewrite H3. apply excess_arith_next_binade; lra.
Qed.

(* The same with the sharp constant: (r - x) (1 + u) <= 3 u x, for prec >= 3. *)
Lemma up_excess_rel_sharp :
  (3 <= prec)%Z ->
  forall x, pow2 (emin + prec - 1) <= x ->
  (succ (rnd x) - x) * (1 + pow2 (- prec)) <= 3 * pow2 (- prec) * x.
Proof.
intros Hp x Hx.
assert (Hx0 : 0 <= x) by (apply Rle_trans with (2 := Hx); apply bpow_ge_0).
assert (Hu0 : 0 < pow2 (- prec)) by apply bpow_gt_0.
assert (Hu8 : pow2 (- prec) <= / 8).
{ change (/ 8) with (pow2 (-3)). apply bpow_le. lia. }
rewrite up_eq by exact Hx0.
destruct (up_normal_facts x Hx) as [B [HB0 [HBx [H1 [H2 [[H3 H4]|[H3 H4]]]]]]]; rewrite H4.
- apply excess_arith_same_binade_sharp; lra.
- rewrite H3. apply excess_arith_next_binade_sharp; lra.
Qed.

(* 4, below the normal range: the spacing is eta there, so the excess is at most
   (3/2) eta. *)
Lemma up_excess_small :
  forall x, 0 <= x -> x < pow2 (emin + prec - 1) ->
  succ (rnd x) - x <= 3 / 2 * pow2 emin.
Proof.
intros x Hx0 Hx.
assert (Hp : (0 < prec)%Z) by exact prec_gt_0_.
assert (Hs : rnd x <= pow2 (emin + prec - 1)).
{ apply round_le_generic; auto with typeclass_instances.
  - apply generic_format_bpow. unfold FLT_exp. lia.
  - lra. }
assert (Hu : ulp (rnd x) = pow2 emin).
{ apply ulp_FLT_small; trivial.
  rewrite Rabs_pos_eq by now apply rnd_ge_0.
  apply Rle_lt_trans with (1 := Hs). apply bpow_lt. lia. }
generalize (up_excess_ulp x Hx0). rewrite Hu. lra.
Qed.

(* 4, for a sum of two numbers of the format below 2^(emin + prec): the sum is itself a
   number of the format, so the excess is exactly eta. *)
Lemma up_excess_plus_small :
  forall a b, format a -> format b -> 0 <= a + b -> a + b < pow2 (emin + prec) ->
  succ (rnd (a + b)) - (a + b) = pow2 emin.
Proof.
intros a b Fa Fb H0 H.
assert (F : format (a + b)).
{ apply FLT_format_plus_small; trivial.
  rewrite Rabs_pos_eq by exact H0. rewrite Z.add_comm. lra. }
rewrite round_generic; auto with typeclass_instances.
rewrite succ_eq_pos by exact H0. rewrite ulp_FLT_small; trivial. ring.
now rewrite Rabs_pos_eq.
Qed.

(* 4, everywhere: the larger of the relative and the absolute term is enough. *)
Lemma up_excess_max :
  (2 <= prec)%Z ->
  forall x, 0 <= x ->
  succ (rnd x) - x <= Rmax (3 * pow2 (- prec) * x) (3 / 2 * pow2 emin).
Proof.
intros Hp x Hx0. destruct (Rle_or_lt (pow2 (emin + prec - 1)) x) as [H|H].
- apply Rle_trans with (2 := Rmax_l _ _). now apply up_excess_rel.
- apply Rle_trans with (2 := Rmax_r _ _). now apply up_excess_small.
Qed.

Lemma up_excess_plus_max :
  (2 <= prec)%Z ->
  forall a b, format a -> format b -> 0 <= a + b ->
  succ (rnd (a + b)) - (a + b) <= Rmax (3 * pow2 (- prec) * (a + b)) (pow2 emin).
Proof.
intros Hp a b Fa Fb H0. destruct (Rle_or_lt (pow2 (emin + prec - 1)) (a + b)) as [H|H].
- apply Rle_trans with (2 := Rmax_l _ _). now apply up_excess_rel.
- apply Rle_trans with (2 := Rmax_r _ _). right.
  apply up_excess_plus_small; trivial.
  apply Rlt_trans with (1 := H). apply bpow_lt. lia.
Qed.

End Step.

(** * The two kernels *)

Section Kernel_lemmas.
Variable emin prec : Z.
Variable choice : Z -> bool.

Lemma radd_eq : forall a b,
  radd emin prec choice a b
  = succ radix2 (FLT_exp emin prec) (round radix2 (FLT_exp emin prec) (Znearest choice) (a + b)).
Proof. reflexivity. Qed.

Lemma rmul_eq : forall a b,
  rmul emin prec choice a b
  = succ radix2 (FLT_exp emin prec) (round radix2 (FLT_exp emin prec) (Znearest choice) (a * b)).
Proof. intros a b. unfold rmul. cbv zeta. now rewrite Rplus_0_r. Qed.

End Kernel_lemmas.

(* The stronger form of item 4, for any tie rule: the maximum of the two terms. *)
Theorem radd_excess_max :
  forall emin prec choice, (2 <= prec)%Z ->
  forall a b : R, fmt emin prec a -> fmt emin prec b -> 0 <= a -> 0 <= b ->
  radd emin prec choice a b - (a + b) <= Rmax (3 * u prec * (a + b)) (eta emin).
Proof.
intros emin prec choice Hp a b Fa Fb Ha Hb.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
rewrite radd_eq. apply up_excess_plus_max; trivial. lra.
Qed.

Theorem rmul_excess_max :
  forall emin prec choice, (2 <= prec)%Z ->
  forall a b : R, 0 <= a -> 0 <= b ->
  rmul emin prec choice a b - a * b <= Rmax (3 * u prec * (a * b)) (3 / 2 * eta emin).
Proof.
intros emin prec choice Hp a b Ha Hb.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
rewrite rmul_eq. apply up_excess_max; trivial. now apply Rmult_le_pos.
Qed.

(* The sharp relative constant in the normal range, for prec >= 3 and any tie rule:
   (r - x) (1 + u) <= 3 u x, that is r - x <= 3 u / (1 + u) x. *)
Theorem radd_excess_sharp :
  forall emin prec choice, (3 <= prec)%Z ->
  forall a b : R, bpow radix2 (emin + prec - 1) <= a + b ->
  (radd emin prec choice a b - (a + b)) * (1 + u prec) <= 3 * u prec * (a + b).
Proof.
intros emin prec choice Hp a b H.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
rewrite radd_eq. now apply up_excess_rel_sharp.
Qed.

Theorem rmul_excess_sharp :
  forall emin prec choice, (3 <= prec)%Z ->
  forall a b : R, bpow radix2 (emin + prec - 1) <= a * b ->
  (rmul emin prec choice a b - a * b) * (1 + u prec) <= 3 * u prec * (a * b).
Proof.
intros emin prec choice Hp a b H.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
rewrite rmul_eq. now apply up_excess_rel_sharp.
Qed.

(* The excess in units of the spacing above the result r itself. *)
Theorem radd_excess_ulp_result :
  forall emin prec choice, (1 <= prec)%Z ->
  forall a b : R, 0 <= a -> 0 <= b ->
  radd emin prec choice a b - (a + b)
  <= 3 / 2 * ulp radix2 (FLT_exp emin prec) (radd emin prec choice a b).
Proof.
intros emin prec choice Hp a b Ha Hb.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
rewrite radd_eq. apply up_excess_ulp_result; trivial. lra.
Qed.

Theorem rmul_excess_ulp_result :
  forall emin prec choice, (1 <= prec)%Z ->
  forall a b : R, 0 <= a -> 0 <= b ->
  rmul emin prec choice a b - a * b
  <= 3 / 2 * ulp radix2 (FLT_exp emin prec) (rmul emin prec choice a b).
Proof.
intros emin prec choice Hp a b Ha Hb.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
rewrite rmul_eq. apply up_excess_ulp_result; trivial. now apply Rmult_le_pos.
Qed.

(** * The generated statements *)

Theorem radd_correct : radd_spec.
Proof.
intros emin prec Hp a b Fa Fb Ha Hb r. unfold r. clear r.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
rewrite radd_eq. apply up_upper; trivial. lra.
Qed.

Theorem rmul_correct : rmul_spec.
Proof.
intros emin prec Hp a b Fa Fb Ha Hb r. unfold r. clear r.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
rewrite rmul_eq. apply up_upper; trivial. now apply Rmult_le_pos.
Qed.

(** * The four items of the header together *)

(* The result is a number of the format, strictly above the exact value, within
   (3/2) ulp(RN(x)) of it, and within 3 u x + eta of it (3 u x + (3/2) eta for the
   product). These statements are written by hand; the audit of proofs/audit/HandAudit.v
   covers them. *)
Definition radd_facts_spec : Prop :=
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R,
  fmt emin prec a ->
  fmt emin prec b ->
  0 <= a ->
  0 <= b ->
  let r := radd emin prec tie_even a b in
  fmt emin prec r /\
  (a + b) < r /\
  r - (a + b) <= (3 / 2) * ulp radix2 (FLT_exp emin prec) (RN emin prec (a + b)) /\
  r - (a + b) <= 3 * u prec * (a + b) + 1 * eta emin.

Definition rmul_facts_spec : Prop :=
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R,
  fmt emin prec a ->
  fmt emin prec b ->
  0 <= a ->
  0 <= b ->
  let r := rmul emin prec tie_even a b in
  fmt emin prec r /\
  (a * b) < r /\
  r - (a * b) <= (3 / 2) * ulp radix2 (FLT_exp emin prec) (RN emin prec (a * b)) /\
  r - (a * b) <= 3 * u prec * (a * b) + (3 / 2) * eta emin.

Theorem radd_facts : radd_facts_spec.
Proof.
intros emin prec Hp a b Fa Fb Ha Hb r. unfold r. clear r.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
assert (Hx : 0 <= a + b) by lra.
split; [|split; [|split]].
- rewrite radd_eq. apply up_format; trivial.
- rewrite radd_eq. now apply up_above.
- rewrite radd_eq. now apply up_excess_ulp.
- apply Rle_trans with (1 := radd_excess_max emin prec tie_even Hp a b Fa Fb Ha Hb).
  assert (0 <= 3 * u prec * (a + b)).
  { apply Rmult_le_pos; trivial. apply Rmult_le_pos. lra. apply bpow_ge_0. }
  assert (0 <= eta emin) by apply bpow_ge_0.
  apply Rmax_lub; lra.
Qed.

Theorem rmul_facts : rmul_facts_spec.
Proof.
intros emin prec Hp a b Fa Fb Ha Hb r. unfold r. clear r.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
assert (Hx : 0 <= a * b) by now apply Rmult_le_pos.
split; [|split; [|split]].
- rewrite rmul_eq. apply up_format; trivial.
- rewrite rmul_eq. now apply up_above.
- rewrite rmul_eq. now apply up_excess_ulp.
- apply Rle_trans with (1 := rmul_excess_max emin prec tie_even Hp a b Ha Hb).
  assert (0 <= 3 * u prec * (a * b)).
  { apply Rmult_le_pos; trivial. apply Rmult_le_pos. lra. apply bpow_ge_0. }
  assert (0 <= eta emin) by apply bpow_ge_0.
  apply Rmax_lub; lra.
Qed.
