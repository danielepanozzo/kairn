(* mul_2_2: the product of two 2-limb numbers (JMP17 Algorithm 12, DWTimesDW3), with
   gradual underflow.

   Statement (mul_2_2_spec): for x and y normalized, in any format with gradual underflow
   and precision at least 4, the result z is normalized and
       |z - x y| <= 4 u^2 |x y| + 3/2 eta.

   Without underflow the bound 4 u^2 is MR22's (Muller and Rideau, ACM TOMS 48(1), 2022,
   lemma DWTimesDW12_correct, which assumes an exact TwoProd and precision at least 5).
   Their proof normalizes the operands to 1 <= x0, y0 < 2, which a format with a
   smallest number does not allow. What replaces it here: scaling x by 2^a and y by 2^b
   turns the format with smallest number eta into the one with smallest number
   2^(a+b) eta (Format.round_FLT_scale). So the theorem is proved for 1 <= x0, y0 < 2 and
   EVERY position of eta relative to 1, with operands that need not be multiples of eta.
   The proof then splits on that position. With u = 2^-prec:

     eta <= 2u^2        the product is far above the underflow threshold: TwoProd is
                        exact, MR22's analysis applies step by step, and only the
                        rounding of x1 y1 can lose up to eta/2 more than it does
                        without underflow;
     eta = 4u^2         a short direct count;
     8u^2 <= eta <= 2u  x1 y1 rounds to zero, three operations (the second FMA of
                        TwoProd and the two FMAs of the cross terms) lose at most eta/2
                        each, and the last sum is exact: this is where 3/2 comes from;
     eta >= 4u          every operation but the first product returns zero.

   The constant 3/2 is not attained but cannot be lowered: exhaustive enumeration on toy
   formats gives 1.325, 1.410, 1.466 for prec = 4, 5, 6, in the third case above.

   The analysis of the first case (section Regime1, and the lemma sum_le_3m2u) follows
   MR22's proof step by step; their development is under the MIT license, reproduced in
   third_party/mr22/LICENSE. No file of theirs is used by this one. *)
From Stdlib Require Import Reals ZArith Lia Lra Psatz.
From Flocq Require Import Core Plus_error Mult_error Relative.
From Kairn Require Import ModelDraft SpecDraft Format Transfer EFT.
Open Scope R_scope.

(** * Real-number lemmas *)

Lemma Rabs_mult_le : forall a b A B, Rabs a <= A -> Rabs b <= B -> Rabs (a * b) <= A * B.
Proof.
intros a b A B Ha Hb. rewrite Rabs_mult.
apply Rmult_le_compat; trivial; apply Rabs_pos.
Qed.

Lemma Rabs_plus_le : forall a b A B, Rabs a <= A -> Rabs b <= B -> Rabs (a + b) <= A + B.
Proof. intros a b A B Ha Hb. apply Rle_trans with (1 := Rabs_triang a b). lra. Qed.

Lemma Rabs_sum5_le :
  forall a b c d e A B C D E,
  Rabs a <= A -> Rabs b <= B -> Rabs c <= C -> Rabs d <= D -> Rabs e <= E ->
  Rabs (a + b + c + d + e) <= A + B + C + D + E.
Proof. intros. repeat apply Rabs_plus_le; assumption. Qed.

(* x0 (1 - u) y0 (1 - u) <= x y when the tails are at most u and the heads at least 1. *)
Lemma xy_lower :
  forall u x0 x1 y0 y1, 0 < u < 1 -> 1 <= x0 -> 1 <= y0 -> Rabs x1 <= u -> Rabs y1 <= u ->
  x0 * y0 * ((1 - u) * (1 - u)) <= (x0 + x1) * (y0 + y1).
Proof.
intros u x0 x1 y0 y1 Hu Hx Hy Hx1 Hy1.
apply Rabs_le_inv in Hx1. apply Rabs_le_inv in Hy1.
replace (x0 * y0 * ((1 - u) * (1 - u))) with ((x0 * (1 - u)) * (y0 * (1 - u))) by ring.
apply Rmult_le_compat; nra.
Qed.

(* If two numbers of [1, 2] have product at most 2, their sum is at most 3, and it is 3
   only when they are 1 and 2. (MR22, lemmas l5_2 and l5_20.) *)
Lemma sum_le_3 :
  forall a b, 1 <= a -> 1 <= b -> a * b <= 2 -> a + b <= 3.
Proof. intros a b Ha Hb H. nra. Qed.

Lemma sum_lt_3 :
  forall a b, 1 <= a < 2 -> 1 <= b < 2 -> a * b <= 2 -> a + b < 3.
Proof. intros a b Ha Hb H. nra. Qed.

(** * The kernel over an arbitrary rounding function, and its scaling *)

Definition g_mul_2_2 (rnd : R -> R) (x0 x1 y0 y1 : R) : R * R :=
  let ch := rnd (x0 * y0) in
  let cl1 := rnd (x0 * y0 - ch) in
  let tl0 := rnd (x1 * y1) in
  let tl1 := rnd (x0 * y1 + tl0) in
  let cl2 := rnd (x1 * y0 + tl1) in
  let cl3 := rnd (cl1 + cl2) in
  let s := rnd (ch + cl3) in
  let z := rnd (s - ch) in
  let e := rnd (cl3 - z) in
  (s, e).

Lemma mul_2_2_g :
  forall emin prec choice x0 x1 y0 y1,
  mul_2_2 emin prec choice x0 x1 y0 y1
  = g_mul_2_2 (round radix2 (FLT_exp emin prec) (Znearest choice)) x0 x1 y0 y1.
Proof.
intros. unfold mul_2_2, two_prod, fast_two_sum, g_mul_2_2. cbv zeta beta iota.
rewrite !Rplus_0_r. reflexivity.
Qed.

(* If a rounding rnd' commutes with the multiplication by c = a b, in the sense that
   rnd' (t c) = rnd t * c for all t, then running the kernel with rnd' on (x a, y b)
   gives c times the result of running it with rnd on (x, y). *)
Lemma g_mul_2_2_scale :
  forall (rnd rnd' : R -> R) (a b : R),
  (forall t, rnd' (t * (a * b)) = rnd t * (a * b)) ->
  forall x0 x1 y0 y1,
  g_mul_2_2 rnd' (x0 * a) (x1 * a) (y0 * b) (y1 * b)
  = (fst (g_mul_2_2 rnd x0 x1 y0 y1) * (a * b), snd (g_mul_2_2 rnd x0 x1 y0 y1) * (a * b)).
Proof.
intros rnd rnd' a b H x0 x1 y0 y1. unfold g_mul_2_2. cbv zeta. cbn [fst snd].
replace (x0 * a * (y0 * b)) with (x0 * y0 * (a * b)) by ring. rewrite H.
set (ch := rnd (x0 * y0)).
replace (x0 * y0 * (a * b) - ch * (a * b)) with ((x0 * y0 - ch) * (a * b)) by ring. rewrite H.
set (cl1 := rnd (x0 * y0 - ch)).
replace (x1 * a * (y1 * b)) with (x1 * y1 * (a * b)) by ring. rewrite H.
set (tl0 := rnd (x1 * y1)).
replace (x0 * a * (y1 * b) + tl0 * (a * b)) with ((x0 * y1 + tl0) * (a * b)) by ring. rewrite H.
set (tl1 := rnd (x0 * y1 + tl0)).
replace (x1 * a * (y0 * b) + tl1 * (a * b)) with ((x1 * y0 + tl1) * (a * b)) by ring. rewrite H.
set (cl2 := rnd (x1 * y0 + tl1)).
rewrite <- Rmult_plus_distr_r, H.
set (cl3 := rnd (cl1 + cl2)).
rewrite <- Rmult_plus_distr_r, H.
set (s := rnd (ch + cl3)).
rewrite <- Rmult_minus_distr_r, H.
set (z := rnd (s - ch)).
rewrite <- Rmult_minus_distr_r, H.
reflexivity.
Qed.

Lemma pair_eta : forall p : R * R, (let '(a, b) := p in (a, b)) = p.
Proof. now intros [a b]. Qed.

(* Two numbers with prec significant bits in [1, 2 - 2u] whose product is at most 2 have
   a sum of at most 3 - 2u: the sum is below 3 and is a multiple of 2u. (MR22, l5_2F.) *)
Lemma sum_le_3m2u :
  forall prec {prec_gt_0_ : Prec_gt_0 prec} a b,
  generic_format radix2 (FLX_exp prec) a -> generic_format radix2 (FLX_exp prec) b ->
  1 <= a <= 2 - 2 * pow2 (- prec) -> 1 <= b <= 2 - 2 * pow2 (- prec) -> a * b <= 2 ->
  a + b <= 3 - 2 * pow2 (- prec).
Proof.
intros prec Hp a b Fa Fb Ha Hb Hab.
assert (Hu : 0 < pow2 (- prec)) by apply bpow_gt_0.
assert (Hw : pow2 (0 - prec + 1) = 2 * pow2 (- prec)).
{ replace (0 - prec + 1)%Z with (1 + - prec)%Z by ring. now rewrite bpow_plus, pow2_1. }
destruct (FLX_multiple prec a 0 Fa) as [ma Ea]. { rewrite Rabs_pos_eq; simpl; lra. }
destruct (FLX_multiple prec b 0 Fb) as [mb Eb]. { rewrite Rabs_pos_eq; simpl; lra. }
rewrite Hw in Ea, Eb.
assert (E3 : 3 = IZR (3 * radix2 ^ (prec - 1)) * (2 * pow2 (- prec))).
{ rewrite mult_IZR, IZR_Zpower by (generalize Hp; unfold Prec_gt_0; lia).
  replace (prec - 1)%Z with (- (1 + - prec))%Z by ring.
  rewrite bpow_opp, bpow_plus, pow2_1. field. lra. }
assert (Hlt : a + b < 3) by (apply sum_lt_3; lra).
assert (Hm : (ma + mb < 3 * radix2 ^ (prec - 1))%Z).
{ apply lt_IZR. apply Rmult_lt_reg_r with (2 * pow2 (- prec)). lra.
  rewrite <- E3, plus_IZR, Rmult_plus_distr_r, <- Ea, <- Eb. exact Hlt. }
assert (Hm' : IZR (ma + mb) <= IZR (3 * radix2 ^ (prec - 1)) - 1).
{ rewrite <- minus_IZR. apply IZR_le. lia. }
rewrite Ea, Eb, <- Rmult_plus_distr_r, <- plus_IZR.
apply Rle_trans with ((IZR (3 * radix2 ^ (prec - 1)) - 1) * (2 * pow2 (- prec))).
- apply Rmult_le_compat_r. lra. exact Hm'.
- rewrite Rmult_minus_distr_r, <- E3. lra.
Qed.

(** * The scaled problem: 1 <= x0, y0 < 2, and eta anywhere *)

Section Core.
Variable emin prec : Z.
Hypothesis Hp : (4 <= prec)%Z.

Local Instance prec_pos : Prec_gt_0 prec.
Proof. unfold Prec_gt_0. lia. Qed.

Let u := pow2 (- prec).
Let eta := pow2 emin.
Notation rn := (RN emin prec).
Notation format := (generic_format radix2 (FLT_exp emin prec)).
Notation formatx := (generic_format radix2 (FLX_exp prec)).

(* The operands: leading limbs with prec significant bits in [1, 2 - 2u] (any exponent
   range: they need not be multiples of eta), and tails of magnitude at most u, which
   is all that the normalization of the operands is used for. *)
Variables x0 x1 y0 y1 : R.
Hypothesis Fx0 : formatx x0.
Hypothesis Fy0 : formatx y0.
Hypothesis Hx0 : 1 <= x0 <= 2 - 2 * u.
Hypothesis Hy0 : 1 <= y0 <= 2 - 2 * u.
Hypothesis Hx1 : Rabs x1 <= u.
Hypothesis Hy1 : Rabs y1 <= u.

(* The values of the kernel (the final fast_two_sum is treated as a whole). *)
Let ch := rn (x0 * y0).
Let cl1 := rn (x0 * y0 - ch).
Let tl0 := rn (x1 * y1).
Let tl1 := rn (x0 * y1 + tl0).
Let cl2 := rn (x1 * y0 + tl1).
Let cl3 := rn (cl1 + cl2).
Let xy := (x0 + x1) * (y0 + y1).

Let core_goal : Prop :=
  normalized_2 emin prec (fst (mul_2_2 emin prec tie_even x0 x1 y0 y1))
                         (snd (mul_2_2 emin prec tie_even x0 x1 y0 y1)) /\
  Rabs (fst (mul_2_2 emin prec tie_even x0 x1 y0 y1)
        + snd (mul_2_2 emin prec tie_even x0 x1 y0 y1) - xy)
  <= 4 * (u * u) * xy + 3 / 2 * eta.

(* u, eta and the powers of two that occur. *)
Let upos : 0 < u.
Proof. apply bpow_gt_0. Qed.
Let u16 : u <= / 16.
Proof. unfold u. change (/ 16) with (pow2 (-4)). apply bpow_le. lia. Qed.
Let etapos : 0 < eta.
Proof. apply bpow_gt_0. Qed.
Let P1 : pow2 (1 - prec) = 2 * u.
Proof. unfold u. replace (1 - prec)%Z with (1 + - prec)%Z by ring. now rewrite bpow_plus, pow2_1. Qed.
Let P2 : pow2 (2 - prec) = 4 * u.
Proof. unfold u. replace (2 - prec)%Z with (2 + - prec)%Z by ring. now rewrite bpow_plus, pow2_2. Qed.
Let P3 : pow2 (3 - prec) = 8 * u.
Proof. unfold u. replace (3 - prec)%Z with (3 + - prec)%Z by ring. now rewrite bpow_plus, pow2_3. Qed.
Let Q0 : pow2 (- prec - prec) = u * u.
Proof. unfold u. replace (- prec - prec)%Z with (- prec + - prec)%Z by ring. apply bpow_plus. Qed.
Let Q1 : pow2 (1 - prec - prec) = 2 * (u * u).
Proof. rewrite <- Q0. replace (1 - prec - prec)%Z with (1 + (- prec - prec))%Z by ring. now rewrite bpow_plus, pow2_1. Qed.
Let Q2 : pow2 (2 - prec - prec) = 4 * (u * u).
Proof. rewrite <- Q0. replace (2 - prec - prec)%Z with (2 + (- prec - prec))%Z by ring. now rewrite bpow_plus, pow2_2. Qed.
Let Q3 : pow2 (3 - prec - prec) = 8 * (u * u).
Proof. rewrite <- Q0. replace (3 - prec - prec)%Z with (3 + (- prec - prec))%Z by ring. now rewrite bpow_plus, pow2_3. Qed.
Let Q00 : pow2 (- prec - prec - prec) = u * u * u.
Proof. rewrite <- Q0. unfold u. replace (- prec - prec - prec)%Z with (- prec - prec + - prec)%Z by ring. apply bpow_plus. Qed.

(* One rounding. *)
Let err : forall t k B, Rabs t <= pow2 k -> pow2 (k - prec) <= 2 * B -> eta <= 2 * B ->
  Rabs (rn t - t) <= B.
Proof. intros t k B. apply (round_error_le emin prec tie_even). Qed.
Let Frn : forall t, format (rn t).
Proof. intros t. apply generic_format_round; auto with typeclass_instances. Qed.
Let mag_le : forall t k, Rabs t <= pow2 k -> Rabs (rn t) <= pow2 k.
Proof. intros t k H. exact (RN_abs_le_bpow emin prec t k H). Qed.
Let zero : forall t, Rabs t <= / 2 * eta -> rn t = 0.
Proof.
intros t Ht. apply (RN_small_zero emin prec). unfold eta in Ht.
replace (emin - 1)%Z with (-1 + emin)%Z by ring. now rewrite bpow_plus, pow2_m1.
Qed.

(* The exact partial products. *)
Let Hx1y1 : Rabs (x1 * y1) <= u * u.
Proof. now apply Rabs_mult_le. Qed.
Let Hx0y1 : Rabs (x0 * y1) <= (2 - 2 * u) * u.
Proof. apply Rabs_mult_le; trivial. rewrite Rabs_pos_eq; lra. Qed.
Let Hx1y0 : Rabs (x1 * y0) <= u * (2 - 2 * u).
Proof. apply Rabs_mult_le; trivial. rewrite Rabs_pos_eq; lra. Qed.
Let Hx0y0 : 1 <= x0 * y0 <= 4.
Proof. split; nra. Qed.
Let Hxy : x0 * y0 * ((1 - u) * (1 - u)) <= xy.
Proof. apply xy_lower; lra. Qed.
Let Hxy4 : / 4 <= xy.
Proof. apply Rle_trans with (2 := Hxy). nra. Qed.

(* The error of the kernel is the sum of the errors of its operations. *)
Let decomp :
  ch + cl3 - xy = (ch + cl1 - x0 * y0) + (tl0 - x1 * y1) + (tl1 - (x0 * y1 + tl0))
                  + (cl2 - (x1 * y0 + tl1)) + (cl3 - (cl1 + cl2)).
Proof. unfold xy. ring. Qed.

(* What remains to be shown in each case: the final fast_two_sum is applicable, and
   ch + cl3 is close enough to x y. *)
Lemma core_finish :
  forall B, Rabs cl3 <= Rabs ch -> Rabs (ch + cl3 - xy) <= B ->
  B <= 4 * (u * u) * xy + 3 / 2 * eta -> core_goal.
Proof.
intros B H1 H2 H3. unfold core_goal.
assert (E : mul_2_2 emin prec tie_even x0 x1 y0 y1 = fast_two_sum emin prec tie_even ch cl3).
{ unfold mul_2_2, two_prod. cbv zeta beta iota. rewrite !Rplus_0_r, pair_eta. reflexivity. }
rewrite E.
assert (Hp2 : (2 <= prec)%Z) by lia.
destruct (fast_two_sum_norm emin prec Hp2 ch cl3 (Frn _) (Frn _) H1) as [N S].
split. exact N. rewrite S. now apply Rle_trans with B.
Qed.

(* The leading product is at least 1 when 1 is a number of the format. *)
Lemma ch_ge_1 : (emin <= 0)%Z -> 1 <= Rabs ch.
Proof.
intros He. apply (round_abs_ge emin prec tie_even).
- change 1 with (pow2 0). apply generic_format_bpow. unfold FLT_exp. lia.
- rewrite Rabs_pos_eq; lra.
Qed.

(** ** eta >= 4u: only the leading product survives *)

Lemma regime4 : (2 - prec <= emin)%Z -> core_goal.
Proof.
intros He.
assert (Heta : 4 * u <= eta). { rewrite <- P2. apply bpow_le. exact He. }
assert (Hc : Rabs (ch - x0 * y0) <= / 2 * eta).
{ apply err with 2%Z. rewrite pow2_2, Rabs_pos_eq; lra. rewrite P2; lra. lra. }
assert (Z1 : cl1 = 0). { apply zero. rewrite <- Rabs_Ropp, Ropp_minus_distr. exact Hc. }
assert (Z0 : tl0 = 0). { apply zero. apply Rle_trans with (1 := Hx1y1). nra. }
assert (Zt : tl1 = 0).
{ unfold tl1. rewrite Z0, Rplus_0_r. apply zero. apply Rle_trans with (1 := Hx0y1). nra. }
assert (Z2 : cl2 = 0).
{ unfold cl2. rewrite Zt, Rplus_0_r. apply zero. apply Rle_trans with (1 := Hx1y0). nra. }
assert (Z3 : cl3 = 0).
{ unfold cl3. rewrite Z1, Z2, Rplus_0_r. apply round_0; auto with typeclass_instances. }
apply core_finish with (/ 2 * eta + ((2 - 2 * u) * u + u * (2 - 2 * u) + u * u)).
- rewrite Z3, Rabs_R0. apply Rabs_pos.
- rewrite Z3, Rplus_0_r.
  replace (ch - xy) with ((ch - x0 * y0) + (- (x0 * y1) + - (x1 * y0) + - (x1 * y1)))
    by (unfold xy; ring).
  apply Rabs_plus_le; trivial. repeat apply Rabs_plus_le; rewrite Rabs_Ropp; trivial.
- nra.
Qed.

(** ** 8u^2 <= eta <= 2u: three operations lose eta/2 each *)

Lemma regime3 : (3 - prec - prec <= emin)%Z -> (emin <= 1 - prec)%Z -> core_goal.
Proof.
intros He1 He2.
assert (Heta1 : 8 * (u * u) <= eta). { rewrite <- Q3. apply bpow_le. exact He1. }
assert (Heta2 : eta <= 2 * u). { rewrite <- P1. apply bpow_le. exact He2. }
assert (Z0 : tl0 = 0). { apply zero. apply Rle_trans with (1 := Hx1y1). lra. }
assert (E0 : Rabs (tl0 - x1 * y1) <= u * u).
{ rewrite Z0. unfold Rminus. rewrite Rplus_0_l, Rabs_Ropp. exact Hx1y1. }
assert (T1 : Rabs (x0 * y1 + tl0) <= pow2 (1 - prec)).
{ rewrite Z0, Rplus_0_r, P1. apply Rle_trans with (1 := Hx0y1). nra. }
assert (E1 : Rabs (tl1 - (x0 * y1 + tl0)) <= / 2 * eta).
{ apply err with (1 := T1). rewrite Q1; lra. lra. }
assert (M1 : Rabs tl1 <= 2 * u). { rewrite <- P1. apply mag_le. exact T1. }
assert (T2 : Rabs (x1 * y0 + tl1) <= pow2 (2 - prec)).
{ rewrite P2. apply Rle_trans with (u * (2 - 2 * u) + 2 * u). now apply Rabs_plus_le. nra. }
assert (E2 : Rabs (cl2 - (x1 * y0 + tl1)) <= / 2 * eta).
{ apply err with (1 := T2). rewrite Q2; lra. lra. }
assert (M2 : Rabs cl2 <= 4 * u). { rewrite <- P2. now apply mag_le. }
assert (Ec : Rabs (ch + cl1 - x0 * y0) <= / 2 * eta).
{ apply (two_prod_defect emin prec tie_even x0 y0 Fx0 Fy0). }
assert (Hc : Rabs (x0 * y0 - ch) <= pow2 (1 - prec)).
{ rewrite P1, <- Rabs_Ropp, Ropp_minus_distr.
  apply err with 2%Z. rewrite pow2_2, Rabs_pos_eq; lra. rewrite P2; lra. lra. }
assert (Mc : Rabs cl1 <= 2 * u). { rewrite <- P1. now apply mag_le. }
assert (F3 : format (cl1 + cl2)).
{ apply (FLT_format_plus_small radix2 emin prec); try apply Frn.
  apply Rle_trans with (pow2 (3 - prec)).
  - rewrite P3. apply Rle_trans with (2 * u + 4 * u). now apply Rabs_plus_le. lra.
  - apply bpow_le. lia. }
assert (E3 : cl3 = cl1 + cl2). { apply round_generic; auto with typeclass_instances. }
assert (C1 : 1 <= Rabs ch) by (apply ch_ge_1; lia).
apply core_finish with (/ 2 * eta + u * u + / 2 * eta + / 2 * eta + 0).
- rewrite E3. apply Rle_trans with (2 * u + 4 * u). now apply Rabs_plus_le. lra.
- rewrite decomp. apply Rabs_sum5_le; trivial.
  rewrite E3. unfold Rminus. rewrite Rplus_opp_r, Rabs_R0. lra.
- nra.
Qed.

(** ** eta = 4u^2 *)

Lemma regime2 : emin = (2 - prec - prec)%Z -> core_goal.
Proof.
intros He.
assert (Heta : eta = 4 * (u * u)). { unfold eta. rewrite He. exact Q2. }
assert (Z0 : tl0 = 0). { apply zero. apply Rle_trans with (1 := Hx1y1). nra. }
assert (E0 : Rabs (tl0 - x1 * y1) <= u * u).
{ rewrite Z0. unfold Rminus. rewrite Rplus_0_l, Rabs_Ropp. exact Hx1y1. }
assert (T1 : Rabs (x0 * y1 + tl0) <= pow2 (1 - prec)).
{ rewrite Z0, Rplus_0_r, P1. apply Rle_trans with (1 := Hx0y1). nra. }
assert (E1 : Rabs (tl1 - (x0 * y1 + tl0)) <= 2 * (u * u)).
{ apply err with (1 := T1). rewrite Q1; nra. nra. }
assert (M1 : Rabs tl1 <= 2 * u). { rewrite <- P1. apply mag_le. exact T1. }
assert (T2 : Rabs (x1 * y0 + tl1) <= pow2 (2 - prec)).
{ rewrite P2. apply Rle_trans with (u * (2 - 2 * u) + 2 * u). now apply Rabs_plus_le. nra. }
assert (E2 : Rabs (cl2 - (x1 * y0 + tl1)) <= 2 * (u * u)).
{ apply err with (1 := T2). rewrite Q2; lra. lra. }
assert (M2 : Rabs cl2 <= 4 * u). { rewrite <- P2. now apply mag_le. }
assert (Ec : Rabs (ch + cl1 - x0 * y0) <= / 2 * eta).
{ apply (two_prod_defect emin prec tie_even x0 y0 Fx0 Fy0). }
assert (Hc : Rabs (x0 * y0 - ch) <= pow2 (1 - prec)).
{ rewrite P1, <- Rabs_Ropp, Ropp_minus_distr.
  apply err with 2%Z. rewrite pow2_2, Rabs_pos_eq; lra. rewrite P2; lra. nra. }
assert (Mc : Rabs cl1 <= 2 * u). { rewrite <- P1. now apply mag_le. }
assert (C1 : 1 <= Rabs ch) by (apply ch_ge_1; lia).
assert (S3 : Rabs (cl1 + cl2) <= pow2 (3 - prec)).
{ rewrite P3. apply Rle_trans with (2 * u + 4 * u). now apply Rabs_plus_le. lra. }
assert (M3 : Rabs cl3 <= Rabs ch).
{ apply Rle_trans with (2 := C1). apply Rle_trans with (pow2 (3 - prec)).
  now apply mag_le. rewrite P3. lra. }
destruct (Rle_or_lt (x0 * y0) 2) as [H2|H2].
- (* x0 y0 <= 2: the last sum is exact *)
  assert (Hc' : Rabs (x0 * y0 - ch) <= pow2 (- prec)).
  { fold u. rewrite <- Rabs_Ropp, Ropp_minus_distr.
    apply err with 1%Z. rewrite pow2_1, Rabs_pos_eq; lra. rewrite P1; lra. nra. }
  assert (Mc' : Rabs cl1 <= u) by now apply mag_le.
  assert (S : x0 + y0 <= 3 - 2 * u) by exact (sum_le_3m2u prec x0 y0 Fx0 Fy0 Hx0 Hy0 H2).
  assert (T2' : Rabs (x1 * y0 + tl1) <= 3 * u).
  { replace (x1 * y0 + tl1)
      with ((x1 * y0 + x0 * y1) + (tl1 - (x0 * y1 + tl0)) + tl0) by ring.
    assert (M0 : Rabs tl0 <= 0) by (rewrite Z0, Rabs_R0; lra).
    apply Rle_trans with ((u * y0 + x0 * u) + 2 * (u * u) + 0).
    - repeat apply Rabs_plus_le; trivial; apply Rabs_mult_le; trivial;
        rewrite Rabs_pos_eq; lra.
    - nra. }
  assert (F3u : format (3 * u)).
  { unfold u. change 3 with (IZR 3). apply (format_multiple emin prec 3 (- prec)). lia.
    replace (- prec + prec)%Z with 0%Z by ring. simpl (pow2 0).
    rewrite Rabs_pos_eq; simpl; fold u; lra. }
  assert (M2' : Rabs cl2 <= 3 * u) by now apply (round_abs_le emin prec tie_even).
  assert (F3 : format (cl1 + cl2)).
  { apply (FLT_format_plus_small radix2 emin prec); try apply Frn.
    replace (prec + emin)%Z with (2 - prec)%Z by lia. rewrite P2.
    apply Rle_trans with (u + 3 * u). now apply Rabs_plus_le. lra. }
  assert (E3 : cl3 = cl1 + cl2). { apply round_generic; auto with typeclass_instances. }
  apply core_finish with (/ 2 * eta + u * u + 2 * (u * u) + 2 * (u * u) + 0); trivial.
  + rewrite decomp. apply Rabs_sum5_le; trivial.
    rewrite E3. unfold Rminus. rewrite Rplus_opp_r, Rabs_R0. lra.
  + nra.
- (* x0 y0 > 2: x y is large enough to pay for the last rounding *)
  assert (E3 : Rabs (cl3 - (cl1 + cl2)) <= 4 * (u * u)).
  { apply err with (1 := S3). rewrite Q3; lra. lra. }
  assert (Hxy5 : 5 / 4 <= xy). { apply Rle_trans with (2 := Hxy). nra. }
  apply core_finish with (/ 2 * eta + u * u + 2 * (u * u) + 2 * (u * u) + 4 * (u * u)); trivial.
  + rewrite decomp. now apply Rabs_sum5_le.
  + nra.
Qed.

(** ** eta <= 2u^2: TwoProd is exact, and MR22's analysis applies *)

Section Regime1.
Hypothesis He : (emin <= 1 - prec - prec)%Z.

Let Heta : eta <= 2 * (u * u).
Proof. rewrite <- Q1. apply bpow_le. exact He. Qed.

(* The leading limbs are numbers of the format, and their product is above the
   threshold 2^(2 prec - 1) eta of TwoProd: cl1 is exactly the error of ch. *)
Let Fx0' : format x0.
Proof.
apply generic_format_FLT_FLX; trivial.
apply Rle_trans with (pow2 0). apply bpow_le; lia. rewrite Rabs_pos_eq; simpl; lra.
Qed.
Let Fy0' : format y0.
Proof.
apply generic_format_FLT_FLX; trivial.
apply Rle_trans with (pow2 0). apply bpow_le; lia. rewrite Rabs_pos_eq; simpl; lra.
Qed.
Let Ecl1 : cl1 = x0 * y0 - ch.
Proof.
unfold cl1. apply round_generic; auto with typeclass_instances.
replace (x0 * y0 - ch) with (- (ch - x0 * y0)) by ring. apply generic_format_opp.
apply (mult_error_FLT radix2 emin prec (Znearest tie_even) x0 y0 Fx0' Fy0').
intros _. apply Rle_trans with (pow2 0). apply bpow_le; lia. rewrite Rabs_pos_eq; simpl; lra.
Qed.
Let Ec : Rabs (ch + cl1 - x0 * y0) <= 0.
Proof.
rewrite Ecl1. replace (ch + (x0 * y0 - ch) - x0 * y0) with 0 by ring. rewrite Rabs_R0. lra.
Qed.

(* The bounds that hold whatever x0 y0 is (those of MR22, plus eta/2 on tl0). *)
Let E0 : Rabs (tl0 - x1 * y1) <= / 2 * (u * u * u) + / 2 * eta.
Proof. apply err with (- prec - prec)%Z. now rewrite Q0. rewrite Q00; lra. nra. Qed.
Let M0 : Rabs tl0 <= u * u.
Proof. rewrite <- Q0. apply mag_le. now rewrite Q0. Qed.
Let T1 : Rabs (x0 * y1 + tl0) <= pow2 (1 - prec).
Proof.
rewrite P1. apply Rle_trans with ((2 - 2 * u) * u + u * u). now apply Rabs_plus_le. nra.
Qed.
Let E1 : Rabs (tl1 - (x0 * y1 + tl0)) <= u * u.
Proof. apply err with (1 := T1). rewrite Q1; lra. lra. Qed.
Let M1 : Rabs tl1 <= 2 * u.
Proof. rewrite <- P1. apply mag_le. exact T1. Qed.
Let T2 : Rabs (x1 * y0 + tl1) <= pow2 (2 - prec).
Proof.
rewrite P2. apply Rle_trans with (u * (2 - 2 * u) + 2 * u). now apply Rabs_plus_le. nra.
Qed.
Let E2 : Rabs (cl2 - (x1 * y0 + tl1)) <= 2 * (u * u).
Proof. apply err with (1 := T2). rewrite Q2; lra. nra. Qed.
Let M2 : Rabs cl2 <= 4 * u.
Proof. rewrite <- P2. now apply mag_le. Qed.
Let Hc : Rabs (x0 * y0 - ch) <= pow2 (1 - prec).
Proof.
rewrite P1, <- Rabs_Ropp, Ropp_minus_distr.
apply err with 2%Z. rewrite pow2_2, Rabs_pos_eq; lra. rewrite P2; lra. nra.
Qed.
Let Mc : Rabs cl1 <= 2 * u.
Proof. rewrite Ecl1, <- P1. exact Hc. Qed.
Let C1 : 1 <= Rabs ch.
Proof. apply ch_ge_1. lia. Qed.
Let S3 : Rabs (cl1 + cl2) <= pow2 (3 - prec).
Proof. rewrite P3. apply Rle_trans with (2 * u + 4 * u). now apply Rabs_plus_le. lra. Qed.
Let M3 : Rabs cl3 <= Rabs ch.
Proof.
apply Rle_trans with (2 := C1). apply Rle_trans with (pow2 (3 - prec)).
now apply mag_le. rewrite P3. lra.
Qed.

(* x0 y0 > 2: the plain sum of the bounds, 7u^2 + u^3/2, against x y >= 2 (1 - u)^2. *)
Lemma regime1_big : 2 < x0 * y0 -> core_goal.
Proof.
intros H2.
assert (E3 : Rabs (cl3 - (cl1 + cl2)) <= 4 * (u * u)).
{ apply err with (1 := S3). rewrite Q3; lra. nra. }
assert (Hxy2 : 2 * ((1 - u) * (1 - u)) <= xy). { apply Rle_trans with (2 := Hxy). nra. }
apply core_finish
  with (0 + (/ 2 * (u * u * u) + / 2 * eta) + u * u + 2 * (u * u) + 4 * (u * u)); trivial.
- rewrite decomp. now apply Rabs_sum5_le.
- assert (K1 : 0 <= (u * u) * (xy - 2 * ((1 - u) * (1 - u)))) by (apply Rmult_le_pos; nra).
  assert (K2 : 0 <= (u * u) * ((1 - 16 * u) * (1 - / 2 * u))).
  { apply Rmult_le_pos. nra. apply Rmult_le_pos; lra. }
  nra.
Qed.

(* x0 = 1 or y0 = 1: the leading product is exact, so cl1 = 0 and cl3 = cl2. *)
Lemma regime1_one : x0 = 1 \/ y0 = 1 -> core_goal.
Proof.
intros H1.
assert (Z1 : cl1 = 0).
{ rewrite Ecl1. unfold ch. destruct H1 as [H1|H1]; rewrite H1.
  - rewrite Rmult_1_l. replace (rn y0) with y0. ring.
    symmetry. apply round_generic; auto with typeclass_instances.
  - rewrite Rmult_1_r. replace (rn x0) with x0. ring.
    symmetry. apply round_generic; auto with typeclass_instances. }
assert (E3 : cl3 = cl2).
{ unfold cl3. rewrite Z1, Rplus_0_l. apply round_generic; auto with typeclass_instances.
  apply Frn. }
assert (E3' : Rabs (cl3 - (cl1 + cl2)) <= 0).
{ rewrite E3, Z1. replace (cl2 - (0 + cl2)) with 0 by ring. rewrite Rabs_R0. lra. }
assert (Hxy1 : (1 - u) * (1 - u) <= xy). { apply Rle_trans with (2 := Hxy). nra. }
apply core_finish with (0 + (/ 2 * (u * u * u) + / 2 * eta) + u * u + 2 * (u * u) + 0); trivial.
- rewrite decomp. now apply Rabs_sum5_le.
- assert (K1 : 0 <= (u * u) * (xy - (1 - u) * (1 - u))) by (apply Rmult_le_pos; nra).
  assert (K2 : 0 <= (u * u) * (1 - 17 / 2 * u)) by (apply Rmult_le_pos; nra).
  nra.
Qed.

(* 1 < x0, 1 < y0, x0 y0 <= 2: the case that needs MR22's finer analysis. *)
Lemma regime1_small : 1 < x0 -> 1 < y0 -> x0 * y0 <= 2 -> core_goal.
Proof.
intros Hx Hy H2.
assert (F1 : formatx 1).
{ change 1 with (pow2 0). apply generic_format_bpow. unfold FLX_exp. lia. }
assert (Hx' : 1 + 2 * u <= x0).
{ rewrite <- P1. replace (1 - prec)%Z with (- prec + 1)%Z by ring.
  rewrite <- (succ_FLX_1 radix2 prec). apply succ_le_lt; auto with typeclass_instances. }
assert (Hy' : 1 + 2 * u <= y0).
{ rewrite <- P1. replace (1 - prec)%Z with (- prec + 1)%Z by ring.
  rewrite <- (succ_FLX_1 radix2 prec). apply succ_le_lt; auto with typeclass_instances. }
assert (Hxyu : (1 + u) * (1 + u) <= xy).
{ unfold xy. generalize (Rabs_le_inv _ _ Hx1) (Rabs_le_inv _ _ Hy1). intros A B.
  apply Rmult_le_compat; lra. }
assert (Hc' : Rabs (x0 * y0 - ch) <= pow2 (- prec)).
{ fold u. rewrite <- Rabs_Ropp, Ropp_minus_distr.
  apply err with 1%Z. rewrite pow2_1, Rabs_pos_eq; lra. rewrite P1; lra. nra. }
assert (Mc' : Rabs cl1 <= u). { rewrite Ecl1. exact Hc'. }
assert (S : x0 + y0 <= 3 - 2 * u) by exact (sum_le_3m2u prec x0 y0 Fx0 Fy0 Hx0 Hy0 H2).
assert (T2' : Rabs (x1 * y0 + tl1) <= 3 * u).
{ replace (x1 * y0 + tl1)
    with ((x1 * y0 + x0 * y1) + (tl1 - (x0 * y1 + tl0)) + tl0) by ring.
  apply Rle_trans with ((u * y0 + x0 * u) + u * u + u * u).
  - repeat apply Rabs_plus_le; trivial; apply Rabs_mult_le; trivial;
      rewrite Rabs_pos_eq; lra.
  - nra. }
assert (F3u : format (3 * u)).
{ unfold u. change 3 with (IZR 3). apply (format_multiple emin prec 3 (- prec)). lia.
  replace (- prec + prec)%Z with 0%Z by ring. simpl (pow2 0).
  rewrite Rabs_pos_eq; simpl; fold u; lra. }
assert (M2' : Rabs cl2 <= 3 * u) by now apply (round_abs_le emin prec tie_even).
assert (S3' : Rabs (cl1 + cl2) <= pow2 (2 - prec)).
{ rewrite P2. apply Rle_trans with (u + 3 * u). now apply Rabs_plus_le. lra. }
destruct (Rlt_or_le (Rabs cl2) (2 * u)) as [Hlt|Hge].
- (* |cl2| < 2u: the rounding that gave cl2 was in the binade below 2u *)
  assert (T2'' : Rabs (x1 * y0 + tl1) <= pow2 (1 - prec)).
  { rewrite P1. destruct (Rle_or_lt (Rabs (x1 * y0 + tl1)) (2 * u)) as [H|H]; trivial.
    exfalso. apply (Rlt_irrefl (2 * u)). apply Rle_lt_trans with (2 := Hlt).
    apply (round_abs_ge emin prec tie_even).
    - rewrite <- P1. apply generic_format_bpow. unfold FLT_exp. lia.
    - lra. }
  assert (E2' : Rabs (cl2 - (x1 * y0 + tl1)) <= u * u).
  { apply err with (1 := T2''). rewrite Q1; lra. lra. }
  assert (E3 : Rabs (cl3 - (cl1 + cl2)) <= 2 * (u * u)).
  { apply err with (1 := S3'). rewrite Q2; lra. nra. }
  apply core_finish
    with (0 + (/ 2 * (u * u * u) + / 2 * eta) + u * u + u * u + 2 * (u * u)); trivial.
  + rewrite decomp. now apply Rabs_sum5_le.
  + assert (K1 : 0 <= (u * u) * (xy - (1 + u) * (1 + u))) by (apply Rmult_le_pos; nra).
    nra.
- (* |cl2| >= 2u: cl1 and cl2 are multiples of 4u^2, their sum is at most 4u, so it is a
     number of the format and the last sum is exact *)
  assert (F3 : format (cl1 + cl2)).
  { destruct (FLX_multiple prec x0 0 Fx0) as [mx Ex]. { rewrite Rabs_pos_eq; simpl; lra. }
    destruct (FLX_multiple prec y0 0 Fy0) as [my Ey]. { rewrite Rabs_pos_eq; simpl; lra. }
    destruct (FLX_multiple prec ch 0) as [mc Ec'].
    { apply generic_format_FLX_FLT with emin. apply Frn. }
    { simpl. exact C1. }
    destruct (FLX_multiple prec cl2 (1 - prec)) as [m2 Em2].
    { apply generic_format_FLX_FLT with emin. apply Frn. }
    { rewrite P1. exact Hge. }
    assert (V1 : pow2 (0 - prec + 1) = IZR (radix2 ^ (prec - 1)) * pow2 (1 - prec - prec + 1)).
    { rewrite IZR_Zpower by lia. rewrite <- bpow_plus. f_equal. ring. }
    assert (Vv : pow2 (0 - prec + 1) * pow2 (0 - prec + 1) = pow2 (1 - prec - prec + 1)).
    { rewrite <- bpow_plus. f_equal. ring. }
    set (v := pow2 (0 - prec + 1)) in *. set (w := pow2 (1 - prec - prec + 1)) in *.
    assert (E : cl1 + cl2 = IZR (mx * my - mc * radix2 ^ (prec - 1) + m2) * w).
    { rewrite Ecl1, Ec', Em2, Ex, Ey, plus_IZR, minus_IZR, 2!mult_IZR.
      replace (IZR mx * v * (IZR my * v)) with (IZR mx * IZR my * (v * v)) by ring.
      rewrite Vv, V1. ring. }
    rewrite E. apply (format_multiple emin prec). lia.
    fold w. rewrite <- E.
    replace (1 - prec - prec + 1 + prec)%Z with (2 - prec)%Z by ring. exact S3'. }
  assert (E3 : cl3 = cl1 + cl2). { apply round_generic; auto with typeclass_instances. }
  assert (E3' : Rabs (cl3 - (cl1 + cl2)) <= 0).
  { rewrite E3. unfold Rminus. rewrite Rplus_opp_r, Rabs_R0. lra. }
  apply core_finish with (0 + (/ 2 * (u * u * u) + / 2 * eta) + u * u + 2 * (u * u) + 0); trivial.
  + rewrite decomp. now apply Rabs_sum5_le.
  + assert (K1 : 0 <= (u * u) * (xy - (1 + u) * (1 + u))) by (apply Rmult_le_pos; nra).
    nra.
Qed.

Lemma regime1 : core_goal.
Proof.
destruct (Rlt_or_le 2 (x0 * y0)) as [H|H]. now apply regime1_big.
destruct (Req_dec x0 1) as [Hx|Hx]. apply regime1_one; now left.
destruct (Req_dec y0 1) as [Hy|Hy]. apply regime1_one; now right.
apply regime1_small; trivial; lra.
Qed.

End Regime1.

(* All positions of eta. *)
Theorem core : core_goal.
Proof.
destruct (Z_le_gt_dec emin (1 - prec - prec)) as [H1|H1]. now apply regime1.
destruct (Z.eq_dec emin (2 - prec - prec)) as [H2|H2]. now apply regime2.
destruct (Z_le_gt_dec emin (1 - prec)) as [H3|H3]. apply regime3; lia.
apply regime4; lia.
Qed.

End Core.

(** * From the scaled problem to all normalized operands *)

(* A signed power of two: the factor that brings a nonzero number into [1, 2). *)
Definition spow (a : R) (k : Z) : Prop := a = pow2 k \/ a = - pow2 k.

Lemma spow_abs : forall a k, spow a k -> Rabs a = pow2 k.
Proof.
intros a k [-> | ->]; [|rewrite Rabs_Ropp]; apply Rabs_pos_eq, bpow_ge_0.
Qed.

Lemma spow_mult : forall a b ka kb, spow a ka -> spow b kb -> spow (a * b) (ka + kb).
Proof.
intros a b ka kb [-> | ->] [-> | ->]; unfold spow; rewrite bpow_plus;
  [left|right|right|left]; ring.
Qed.

(* Rounding commutes with a signed power of two, if eta is moved accordingly. *)
Lemma RN_scale_spow :
  forall emin prec c k t, spow c k -> RN (emin + k) prec (t * c) = RN emin prec t * c.
Proof.
intros emin prec c k t [-> | ->].
- apply round_FLT_scale; auto with typeclass_instances.
- replace (t * - pow2 k) with (- (t * pow2 k)) by ring. rewrite RN_opp.
  unfold RN. rewrite round_FLT_scale; auto with typeclass_instances. ring.
Qed.

Section Scaling.
Variable prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Notation formatx := (generic_format radix2 (FLX_exp prec)).

Lemma formatx_scale : forall x k, formatx x -> formatx (x * pow2 k).
Proof.
intros x k Fx.
destruct (FLX_format_generic radix2 prec x Fx) as [f Hx Hm].
apply generic_format_FLX. exists (Float radix2 (Fnum f) (Fexp f + k)).
- rewrite Hx. unfold F2R. simpl. rewrite bpow_plus. ring.
- exact Hm.
Qed.

(* A number with prec significant bits in [1, 2) is at most 2 - 2u. *)
Lemma formatx_lt_2 : forall x, formatx x -> 1 <= x < 2 -> x <= 2 - 2 * pow2 (- prec).
Proof.
intros x Fx Hx.
assert (Hu : 0 < pow2 (- prec)) by apply bpow_gt_0.
assert (Hw : pow2 (0 - prec + 1) = 2 * pow2 (- prec)).
{ replace (0 - prec + 1)%Z with (1 + - prec)%Z by ring. now rewrite bpow_plus, pow2_1. }
destruct (FLX_multiple prec x 0 Fx) as [m Em]. { rewrite Rabs_pos_eq; simpl; lra. }
rewrite Hw in Em.
assert (E2 : 2 = IZR (radix2 ^ prec) * (2 * pow2 (- prec))).
{ rewrite IZR_Zpower by (generalize prec_gt_0_; unfold Prec_gt_0; lia).
  rewrite bpow_opp. field. apply Rgt_not_eq, bpow_gt_0. }
assert (Hm : (m < radix2 ^ prec)%Z).
{ apply lt_IZR. apply Rmult_lt_reg_r with (2 * pow2 (- prec)). lra. rewrite <- E2, <- Em. lra. }
assert (Hm' : IZR m <= IZR (radix2 ^ prec) - 1).
{ rewrite <- minus_IZR. apply IZR_le. lia. }
rewrite Em. apply Rle_trans with ((IZR (radix2 ^ prec) - 1) * (2 * pow2 (- prec))).
- apply Rmult_le_compat_r. lra. exact Hm'.
- rewrite Rmult_minus_distr_r, <- E2. lra.
Qed.

(* Every nonzero number with prec significant bits is brought into [1, 2 - 2u] by the
   signed power of two of exponent 1 - (its binary exponent). *)
Lemma scale_to_12 :
  forall x, formatx x -> x <> 0 ->
  exists a, spow a (1 - mag radix2 x) /\ 1 <= x * a <= 2 - 2 * pow2 (- prec).
Proof.
intros x Fx Zx.
destruct (mag radix2 x) as [e He]. simpl. specialize (He Zx).
assert (H12 : 1 <= Rabs x * pow2 (1 - e) < 2).
{ assert (H0 : 0 < pow2 (1 - e)) by apply bpow_gt_0.
  replace 1 with (pow2 (e - 1) * pow2 (1 - e)).
  2:{ rewrite <- bpow_plus. now replace (e - 1 + (1 - e))%Z with 0%Z by ring. }
  replace 2 with (pow2 e * pow2 (1 - e)).
  2:{ rewrite <- bpow_plus. now replace (e + (1 - e))%Z with 1%Z by ring. }
  split. apply Rmult_le_compat_r; lra. apply Rmult_lt_compat_r; lra. }
assert (F : formatx (Rabs x * pow2 (1 - e))).
{ apply formatx_scale. now apply generic_format_abs. }
generalize (formatx_lt_2 _ F H12). intros H2.
destruct (Rle_or_lt 0 x) as [Hx|Hx].
- exists (pow2 (1 - e)). split. now left. rewrite Rabs_pos_eq in H12, H2 by exact Hx. lra.
- exists (- pow2 (1 - e)). split. now right.
  rewrite Rabs_left in H12, H2 by exact Hx.
  replace (x * - pow2 (1 - e)) with (- x * pow2 (1 - e)) by ring. lra.
Qed.

(* The tail of a normalized pair is at most half a unit in the last place of its head. *)
Lemma normalized_tail_FLX :
  forall choice x0 x1, x0 = round radix2 (FLX_exp prec) (Znearest choice) (x0 + x1) -> x0 <> 0 ->
  Rabs x1 <= / 2 * pow2 (mag radix2 x0 - prec).
Proof.
intros choice x0 x1 H Zx.
replace x1 with (- (round radix2 (FLX_exp prec) (Znearest choice) (x0 + x1) - (x0 + x1)))
  by (rewrite <- H; ring).
rewrite Rabs_Ropp.
apply Rle_trans with (/ 2 * ulp radix2 (FLX_exp prec) (round radix2 (FLX_exp prec) (Znearest choice) (x0 + x1))).
- apply error_le_half_ulp_round; auto with typeclass_instances.
- rewrite <- H, ulp_neq_0 by exact Zx. unfold cexp, FLX_exp. lra.
Qed.

End Scaling.

Lemma g_mul_2_2_zero_l :
  forall (rnd : R -> R) y0 y1, rnd 0 = 0 -> g_mul_2_2 rnd 0 0 y0 y1 = (0, 0).
Proof.
intros rnd y0 y1 H0. unfold g_mul_2_2. cbv zeta.
repeat first [rewrite Rmult_0_l | rewrite Rminus_0_r | rewrite Rplus_0_r | rewrite H0].
reflexivity.
Qed.

Lemma g_mul_2_2_zero_r :
  forall (rnd : R -> R) x0 x1, rnd 0 = 0 -> g_mul_2_2 rnd x0 x1 0 0 = (0, 0).
Proof.
intros rnd x0 x1 H0. unfold g_mul_2_2. cbv zeta.
repeat first [rewrite Rmult_0_r | rewrite Rminus_0_r | rewrite Rplus_0_r | rewrite H0].
reflexivity.
Qed.

(** * The statement of SpecDraft.v *)

Theorem mul_2_2_correct : mul_2_2_spec.
Proof.
intros emin prec Hp x0 x1 y0 y1 [F0 [F1 Hx]] [G0 [G1 Hy]].
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 4%Z; lia).
unfold fmt in F0, F1, G0, G1.
assert (R0 : RN emin prec 0 = 0) by (apply round_0; auto with typeclass_instances).
assert (Hu2 : u prec ^ 2 = pow2 (- prec) * pow2 (- prec)) by (unfold u; ring).
assert (Hpos : forall v, 0 <= 4 * u prec ^ 2 * Rabs v + 3 / 2 * eta emin).
{ intros v. rewrite Hu2. unfold eta.
  generalize (bpow_gt_0 radix2 (- prec)) (bpow_gt_0 radix2 emin) (Rabs_pos v). nra. }
assert (Hzero : normalized_2 emin prec 0 0).
{ repeat split; try apply generic_format_0. now rewrite Rplus_0_l. }
(* a zero operand: every value of the kernel is zero *)
destruct (Req_dec x0 0) as [Zx|Zx].
{ assert (Zx1 : x1 = 0).
  { rewrite Zx, Rplus_0_l in Hx. unfold RN in Hx.
    rewrite round_generic in Hx; auto with typeclass_instances. }
  rewrite Zx, Zx1, mul_2_2_g, g_mul_2_2_zero_l by exact R0.
  split. exact Hzero.
  replace (0 + 0 - (0 + 0) * (y0 + y1)) with 0 by ring. rewrite Rabs_R0. apply Hpos. }
destruct (Req_dec y0 0) as [Zy|Zy].
{ assert (Zy1 : y1 = 0).
  { rewrite Zy, Rplus_0_l in Hy. unfold RN in Hy.
    rewrite round_generic in Hy; auto with typeclass_instances. }
  rewrite Zy, Zy1, mul_2_2_g, g_mul_2_2_zero_r by exact R0.
  split. exact Hzero.
  replace (0 + 0 - (x0 + x1) * (0 + 0)) with 0 by ring. rewrite Rabs_R0. apply Hpos. }
(* nonzero operands: scale both leading limbs into [1, 2) *)
assert (FX0 : generic_format radix2 (FLX_exp prec) x0) by now apply generic_format_FLX_FLT with emin.
assert (FY0 : generic_format radix2 (FLX_exp prec) y0) by now apply generic_format_FLX_FLT with emin.
destruct (scale_to_12 prec x0 FX0 Zx) as [a [Sa Ha]].
destruct (scale_to_12 prec y0 FY0 Zy) as [b [Sb Hb]].
set (ka := (1 - mag radix2 x0)%Z) in *. set (kb := (1 - mag radix2 y0)%Z) in *.
assert (Sc : spow (a * b) (ka + kb)) by now apply spow_mult.
assert (Hc : Rabs (a * b) = pow2 (ka + kb)) by now apply spow_abs.
assert (Hc0 : 0 < Rabs (a * b)) by (rewrite Hc; apply bpow_gt_0).
assert (Zc : a * b <> 0). { intros Z. rewrite Z, Rabs_R0 in Hc0. lra. }
(* the tails, scaled, are at most u *)
assert (Tx : Rabs (x1 * a) <= pow2 (- prec)).
{ rewrite Rabs_mult, (spow_abs a ka Sa).
  assert (Hn : x0 = round radix2 (FLX_exp prec) (Znearest tie_even) (x0 + x1)).
  { rewrite Hx at 1. unfold RN. apply round_plus_FLT_FLX; auto with typeclass_instances. }
  generalize (normalized_tail_FLX prec tie_even x0 x1 Hn Zx). intros H.
  apply Rle_trans with (/ 2 * pow2 (mag radix2 x0 - prec) * pow2 ka).
  - apply Rmult_le_compat_r. apply bpow_ge_0. exact H.
  - rewrite Rmult_assoc, <- bpow_plus. unfold ka.
    replace (mag radix2 x0 - prec + (1 - mag radix2 x0))%Z with (1 + - prec)%Z by ring.
    rewrite bpow_plus, pow2_1. lra. }
assert (Ty : Rabs (y1 * b) <= pow2 (- prec)).
{ rewrite Rabs_mult, (spow_abs b kb Sb).
  assert (Hn : y0 = round radix2 (FLX_exp prec) (Znearest tie_even) (y0 + y1)).
  { rewrite Hy at 1. unfold RN. apply round_plus_FLT_FLX; auto with typeclass_instances. }
  generalize (normalized_tail_FLX prec tie_even y0 y1 Hn Zy). intros H.
  apply Rle_trans with (/ 2 * pow2 (mag radix2 y0 - prec) * pow2 kb).
  - apply Rmult_le_compat_r. apply bpow_ge_0. exact H.
  - rewrite Rmult_assoc, <- bpow_plus. unfold kb.
    replace (mag radix2 y0 - prec + (1 - mag radix2 y0))%Z with (1 + - prec)%Z by ring.
    rewrite bpow_plus, pow2_1. lra. }
assert (FXa : generic_format radix2 (FLX_exp prec) (x0 * a)).
{ destruct Sa as [-> | ->]. now apply formatx_scale.
  replace (x0 * - pow2 ka) with (- (x0 * pow2 ka)) by ring.
  apply generic_format_opp. now apply formatx_scale. }
assert (FYb : generic_format radix2 (FLX_exp prec) (y0 * b)).
{ destruct Sb as [-> | ->]. now apply formatx_scale.
  replace (y0 * - pow2 kb) with (- (y0 * pow2 kb)) by ring.
  apply generic_format_opp. now apply formatx_scale. }
(* the scaled problem, in the format with smallest number 2^(ka + kb) eta *)
generalize (core (emin + (ka + kb)) prec Hp (x0 * a) (x1 * a) (y0 * b) (y1 * b) FXa FYb Ha Hb Tx Ty).
set (rnd := round radix2 (FLT_exp emin prec) (Znearest tie_even)).
rewrite (mul_2_2_g (emin + (ka + kb))).
rewrite (g_mul_2_2_scale rnd
           (round radix2 (FLT_exp (emin + (ka + kb)) prec) (Znearest tie_even)) a b)
  by (intros t; exact (RN_scale_spow emin prec (a * b) (ka + kb) t Sc)).
rewrite mul_2_2_g. fold rnd.
(* the limbs of the result are numbers of the format *)
assert (Fz : fmt emin prec (fst (g_mul_2_2 rnd x0 x1 y0 y1)) /\
             fmt emin prec (snd (g_mul_2_2 rnd x0 x1 y0 y1))).
{ unfold g_mul_2_2, rnd. cbv zeta. cbn [fst snd].
  split; apply generic_format_round; auto with typeclass_instances. }
destruct Fz as [Fz0 Fz1].
destruct (g_mul_2_2 rnd x0 x1 y0 y1) as [z0 z1]. cbn [fst snd] in *.
intros [[_ [_ N]] B]. split.
- (* normalized *)
  repeat split; trivial.
  apply Rmult_eq_reg_r with (a * b); trivial.
  rewrite N at 1. rewrite <- Rmult_plus_distr_r. now apply RN_scale_spow.
- (* the bound, divided by |a b| *)
  apply Rmult_le_reg_r with (Rabs (a * b)); trivial.
  rewrite <- Rabs_mult.
  replace ((z0 + z1 - (x0 + x1) * (y0 + y1)) * (a * b))
    with (z0 * (a * b) + z1 * (a * b) - (x0 * a + x1 * a) * (y0 * b + y1 * b)) by ring.
  apply Rle_trans with (1 := B).
  rewrite Hu2.
  replace ((4 * (pow2 (- prec) * pow2 (- prec)) * Rabs ((x0 + x1) * (y0 + y1))
            + 3 / 2 * eta emin) * Rabs (a * b))
    with (4 * (pow2 (- prec) * pow2 (- prec)) * (Rabs ((x0 + x1) * (y0 + y1)) * Rabs (a * b))
          + 3 / 2 * (eta emin * Rabs (a * b))) by ring.
  apply Rplus_le_compat.
  + apply Rmult_le_compat_l.
    * generalize (bpow_gt_0 radix2 (- prec)). nra.
    * rewrite <- Rabs_mult.
      replace ((x0 * a + x1 * a) * (y0 * b + y1 * b)) with ((x0 + x1) * (y0 + y1) * (a * b)) by ring.
      apply Rle_abs.
  + rewrite Hc. unfold eta. rewrite bpow_plus. lra.
Qed.
