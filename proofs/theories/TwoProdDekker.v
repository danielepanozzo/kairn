(* two_prod_dekker: Dekker's product, the error-free product without a fused operation.

   The kernel (proofs/gen/Model.v), for a and b in F:
       (ah, al) = split a          (bh, bl) = split b
       p  = RN (a b)
       t1 = RN (RN (ah bh) - p)
       t2 = RN (t1 + RN (ah bl))
       t3 = RN (t2 + RN (al bh))
       e  = RN (t3 + RN (al bl))

   Statement proved (two_prod_dekker_correct, the generated two_prod_dekker_spec of
   proofs/gen/Statements.v), for every format with gradual
   underflow, prec >= 4, every emin, ties to even, exponents unbounded above:
       p and e are numbers of F;
       p = RN (a b);
       |p + e - a b| <= 13/8 eta;
       p + e = a b when a b = 0 or |a b| >= 2^(2 prec - 1) eta.

   Sources, and what is new.
   - Exactness above the threshold, and the bound 7/2 eta below it, are Flocq's theorem
     Dekker (Pff2Flocq.v; Boldo's formalization of Dekker 1971), stated for the same
     sequence of operations with eta < 1 (emin < 0). The condition on emin is removed here
     by scaling one operand by a power of two (two_prod_dekker_scale): the kernel run on
     (2^k a, b) in the format with smallest number 2^k eta returns 2^k times what it
     returns on (a, b) in F. This gives two_prod_dekker_exact.
   - The constant 13/8 is new here (section Tight). The 7/2 of the source charges eta/2 to
     each of the four partial products and to three of the sums. In fact, below the
     threshold, either the sums are all exact, and the defect is the sum of the rounding
     errors of the partial products: at most eta/2 each, and when ah bh is itself rounded
     al bl is below eta/8, hence 3/2 + 1/8; or only al bl is rounded and the defect is at
     most eta.

   The constant is the right one. Exhaustive runs (every pair of significands and every
   exponent of the product, prec 1 to 15, eta small enough for every underflow pattern to
   occur; checked against the enumeration of all pairs of numbers of whole toy formats for
   prec <= 6) give, for the largest |p + e - a b| / eta:
       prec   1    2    3     4       5        6       7       8       9      10
       max   1/2  7/8  9/8  41/32  185/128  369/256  1.5332  1.4736  1.5786  1.5513
       prec   11      12      13      14      15
       max   1.6017  1.5786  1.6133  1.6057  1.6191
   The worst cases have the three larger partial products each rounded by nearly eta/2 in
   the same direction: for prec = 13, a = 8001 * 2^14 eta and b = 8001 eta give errors
   -1/2, -127/256, -127/256 and -3969/32768 of eta. The exactness threshold is tight as
   well: the largest product observed with p + e <> a b approaches 2^(2 prec - 1) eta from
   below.

   Not proved: prec <= 3. The runs find the statement true there as well. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core Plus_error Pff2Flocq.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Split.
Open Scope R_scope.

(** * The kernel in Flocq's terms, and scaling *)

Section Unfold.
Variable emin prec : Z.
Variable choice : Z -> bool.
Notation rnd := (round radix2 (FLT_exp emin prec) (Znearest choice)).

(* The kernel as Flocq's Dekker section writes it, in terms of the two splittings. *)
Lemma two_prod_dekker_unfold :
  forall a b,
  let ah := fst (split emin prec choice a) in
  let al := snd (split emin prec choice a) in
  let bh := fst (split emin prec choice b) in
  let bl := snd (split emin prec choice b) in
  two_prod_dekker emin prec choice a b =
  (rnd (a * b),
   rnd (rnd (rnd (rnd (- rnd (a * b) + rnd (ah * bh)) + rnd (ah * bl)) + rnd (al * bh))
        + rnd (al * bl))).
Proof.
intros a b ah al bh bl. unfold two_prod_dekker.
subst ah al bh bl.
destruct (split emin prec choice a) as [ah al].
destruct (split emin prec choice b) as [bh bl].
cbv beta iota zeta. cbn [fst snd]. rewrite !Rplus_0_r.
now replace (rnd (ah * bh) - rnd (a * b)) with (- rnd (a * b) + rnd (ah * bh)) by ring.
Qed.

(* The first output is the rounded product. *)
Lemma two_prod_dekker_fst :
  forall a b, fst (two_prod_dekker emin prec choice a b) = rnd (a * b).
Proof. intros. now rewrite two_prod_dekker_unfold. Qed.

End Unfold.

(* Scaling the first operand by 2^k, k <= 0, and eta with it, scales both outputs: every
   product and every sum is scaled, and the second operand is split in the same way in
   the two formats. *)
Lemma two_prod_dekker_scale :
  forall emin prec {prec_gt_0_ : Prec_gt_0 prec} choice k a b,
  (k <= 0)%Z ->
  generic_format radix2 (FLT_exp emin prec) b ->
  two_prod_dekker (emin + k) prec choice (a * pow2 k) b
  = (fst (two_prod_dekker emin prec choice a b) * pow2 k,
     snd (two_prod_dekker emin prec choice a b) * pow2 k).
Proof.
intros emin prec Hp choice k a b Hk Fb.
assert (Hp0 : (0 <= prec)%Z) by (unfold Prec_gt_0 in Hp; lia).
unfold two_prod_dekker.
rewrite split_scale.
rewrite (split_emin_le emin (emin + k) prec choice b Hp0) by (trivial; lia).
destruct (split emin prec choice a) as [ah al].
destruct (split emin prec choice b) as [bh bl].
cbv beta iota zeta. cbn [fst snd].
replace (a * pow2 k * b + 0) with ((a * b + 0) * pow2 k) by ring.
rewrite round_FLT_scale by auto with typeclass_instances.
replace (ah * pow2 k * bh + 0) with ((ah * bh + 0) * pow2 k) by ring.
rewrite round_FLT_scale by auto with typeclass_instances.
rewrite <- Rmult_minus_distr_r, round_FLT_scale by auto with typeclass_instances.
replace (ah * pow2 k * bl + 0) with ((ah * bl + 0) * pow2 k) by ring.
rewrite round_FLT_scale by auto with typeclass_instances.
rewrite <- Rmult_plus_distr_r, round_FLT_scale by auto with typeclass_instances.
replace (al * pow2 k * bh + 0) with ((al * bh + 0) * pow2 k) by ring.
rewrite round_FLT_scale by auto with typeclass_instances.
rewrite <- Rmult_plus_distr_r, round_FLT_scale by auto with typeclass_instances.
replace (al * pow2 k * bl + 0) with ((al * bl + 0) * pow2 k) by ring.
rewrite round_FLT_scale by auto with typeclass_instances.
now rewrite <- Rmult_plus_distr_r, round_FLT_scale by auto with typeclass_instances.
Qed.

(** * Flocq's theorem, and its extension to every emin *)

(* eta < 1: Flocq's Dekker, for the kernel. *)
Lemma two_prod_dekker_small_eta :
  forall emin prec choice, (4 <= prec)%Z -> (emin < 0)%Z ->
  forall a b,
  generic_format radix2 (FLT_exp emin prec) a ->
  generic_format radix2 (FLT_exp emin prec) b ->
  (a * b = 0 \/ pow2 (emin + 2 * prec - 1) <= Rabs (a * b) ->
   a * b = fst (two_prod_dekker emin prec choice a b)
           + snd (two_prod_dekker emin prec choice a b)) /\
  Rabs (a * b - (fst (two_prod_dekker emin prec choice a b)
                 + snd (two_prod_dekker emin prec choice a b))) <= 7 / 2 * pow2 emin.
Proof.
intros emin prec choice Hp He a b Fa Fb.
rewrite two_prod_dekker_unfold. cbv zeta. cbn [fst snd]. rewrite 2!split_unfold. cbn [fst snd].
exact (Dekker radix2 emin prec choice Hp He a b Fa Fb (or_introl eq_refl)).
Qed.

(* Every emin. *)
Lemma two_prod_dekker_exact :
  forall emin prec, (4 <= prec)%Z ->
  forall a b,
  generic_format radix2 (FLT_exp emin prec) a ->
  generic_format radix2 (FLT_exp emin prec) b ->
  let p := fst (two_prod_dekker emin prec tie_even a b) in
  let e := snd (two_prod_dekker emin prec tie_even a b) in
  p = round radix2 (FLT_exp emin prec) (Znearest tie_even) (a * b) /\
  Rabs (p + e - a * b) <= 7 / 2 * pow2 emin /\
  (a * b = 0 \/ pow2 (2 * prec - 1) * pow2 emin <= Rabs (a * b) -> p + e = a * b).
Proof.
intros emin prec Hp a b Fa Fb p e.
assert (Hp0 : Prec_gt_0 prec) by (unfold Prec_gt_0; lia).
split. apply two_prod_dekker_fst.
(* scale a so that eta becomes less than 1 *)
set (k := Z.min 0 (- 1 - emin)).
assert (Hk : (k <= 0)%Z) by (unfold k; lia).
assert (He : (emin + k < 0)%Z) by (unfold k; lia).
assert (Fak : generic_format radix2 (FLT_exp (emin + k) prec) (a * pow2 k)).
{ rewrite <- (round_generic radix2 (FLT_exp emin prec) (Znearest tie_even) a Fa).
  rewrite <- round_FLT_scale by auto with typeclass_instances.
  apply generic_format_round; auto with typeclass_instances. }
assert (Fbk : generic_format radix2 (FLT_exp (emin + k) prec) b).
{ apply format_emin_le with emin; trivial. lia. }
destruct (two_prod_dekker_small_eta (emin + k) prec tie_even Hp He (a * pow2 k) b Fak Fbk)
  as [D1 D2].
rewrite (two_prod_dekker_scale emin prec tie_even k a b Hk Fb) in D1, D2.
cbn [fst snd] in D1, D2. fold p e in D1, D2.
assert (K0 : 0 < pow2 k) by apply bpow_gt_0.
split.
- replace (a * pow2 k * b - (p * pow2 k + e * pow2 k))
    with (- (p + e - a * b) * pow2 k) in D2 by ring.
  rewrite Rabs_mult, Rabs_Ropp, (Rabs_pos_eq (pow2 k)), bpow_plus in D2 by lra.
  apply Rmult_le_reg_r with (pow2 k). exact K0. lra.
- intros H.
  apply Rmult_eq_reg_r with (pow2 k); [|lra].
  rewrite Rmult_plus_distr_r, <- D1. ring.
  destruct H as [H|H].
  + left. replace (a * pow2 k * b) with (a * b * pow2 k) by ring. rewrite H. ring.
  + right.
    replace (a * pow2 k * b) with (a * b * pow2 k) by ring.
    rewrite Rabs_mult, (Rabs_pos_eq (pow2 k)) by lra.
    replace (emin + k + 2 * prec - 1)%Z with (2 * prec - 1 + emin + k)%Z by ring.
    rewrite 2!bpow_plus. now apply Rmult_le_compat_r; [lra|].
Qed.

(** * The defect is at most 13/8 eta *)

(* The product of two bounded numbers. *)
Lemma abs_mult_le_pow2 :
  forall x y e1 e2, Rabs x <= pow2 e1 -> Rabs y <= pow2 e2 -> Rabs (x * y) <= pow2 (e1 + e2).
Proof.
intros x y e1 e2 Hx Hy. rewrite Rabs_mult, bpow_plus.
apply Rmult_le_compat; trivial; apply Rabs_pos.
Qed.

(* Rounding to nearest moves a number by at most its own magnitude: 0 is a number of F. *)
Lemma round_error_le_abs :
  forall emin prec {prec_gt_0_ : Prec_gt_0 prec} choice x,
  Rabs (round radix2 (FLT_exp emin prec) (Znearest choice) x - x) <= Rabs x.
Proof.
intros emin prec Hp choice x.
destruct (round_N_pt radix2 (FLT_exp emin prec) choice x) as [_ H].
specialize (H 0 (generic_format_0 _ _)). now rewrite Rminus_0_l, Rabs_Ropp in H.
Qed.

(* Below the exactness threshold, for a and b nonzero. Write 2^(ma-1) <= |a| < 2^ma and
   2^(mb-1) <= |b| < 2^mb, so that a is a multiple of 2^ca, ca = ma - prec, and b of 2^cb,
   cb = mb - prec; and write P0 = ah bh, P1 = ah bl, P2 = al bh, P3 = al bl for the exact
   partial products, whose sum is a b. Each has at most prec significant bits
   (Split.split_products), so each is rounded with an error of at most eta/2. Two cases.

   Small products, ca + cb + s < emin (tight_small). Then |P1|, |P2| <= 2^(prec-2) eta,
   |P3| <= 2^(s-3) eta and |p - a b| <= 2^(prec-s-2) eta, so each of the four sums of the
   kernel is a sum of two numbers of F of magnitude at most 2^prec eta: it is exact. Hence
   p + e - a b is the sum of the four rounding errors of the partial products. Moreover
   either P0 is a multiple of eta, and is not rounded, or ca + cb + 2 s < emin and then
   |P3| <= eta/8, which bounds its rounding error. In both cases the sum is at most
   (3/2 + 1/8) eta.

   Large products, ca + cb + s >= emin (tight_large). Then P0, P1 and P2 are multiples of
   eta, hence numbers of F, and a b is in the normal range. So the kernel computes p, t1,
   t2 and t3 exactly as it would in a format F' with the same precision and an eta' so
   small that Flocq's theorem gives p + e' = a b there, where e' = RN' (t3 + P3). Only the
   last two operations differ: e = RN (t3 + RN P3). Since e' = a b - p is at most
   2^(prec-2) eta, x = t3 + P3 is at most 2^(prec-1) eta, so the last sum is exact in F and
   e - e' = (RN P3 - P3) + (x - RN' x), at most eta/2 + eta/2. *)
Section Tight.
Variable emin prec : Z.
Hypothesis Hp4 : (4 <= prec)%Z.

Local Instance tight_prec_gt_0 : Prec_gt_0 prec.
Proof. unfold Prec_gt_0. lia. Qed.

Notation s := (split_s prec).
Notation format := (generic_format radix2 (FLT_exp emin prec)).
Notation rnd := (round radix2 (FLT_exp emin prec) (Znearest tie_even)).

Variables a b : R.
Hypothesis Fa : format a.
Hypothesis Fb : format b.
Hypothesis Za : a <> 0.
Hypothesis Zb : b <> 0.

Let ah := fst (split emin prec tie_even a).
Let al := snd (split emin prec tie_even a).
Let bh := fst (split emin prec tie_even b).
Let bl := snd (split emin prec tie_even b).
Let ca := (mag radix2 a - prec)%Z.
Let cb := (mag radix2 b - prec)%Z.

Let Hs : (2 <= s <= prec - 2)%Z.
Proof. now apply split_s_bounds. Qed.

Let Esum : ah * bh + ah * bl + al * bh + al * bl = a * b.
Proof.
generalize (split_sum emin prec Hp4 a Fa) (split_sum emin prec Hp4 b Fb).
fold ah al bh bl. intros Ea Eb. rewrite <- Ea, <- Eb. ring.
Qed.

Let Fpi :
  generic_format radix2 (FLX_exp prec) (ah * bh) /\
  generic_format radix2 (FLX_exp prec) (ah * bl) /\
  generic_format radix2 (FLX_exp prec) (al * bh) /\
  generic_format radix2 (FLX_exp prec) (al * bl).
Proof. exact (split_products emin prec Hp4 a b Fa Fb). Qed.

Let Fr : forall x, format (rnd x).
Proof. intros x. apply generic_format_round; auto with typeclass_instances. Qed.

Lemma tight_small :
  (ca + cb + s < emin)%Z ->
  Rabs (fst (two_prod_dekker emin prec tie_even a b)
        + snd (two_prod_dekker emin prec tie_even a b) - a * b) <= 13 / 8 * pow2 emin.
Proof.
intros Hreg. unfold ca, cb in Hreg.
rewrite two_prod_dekker_unfold. cbv zeta. cbn [fst snd]. fold ah al bh bl.
generalize (split_high_le emin prec Hp4 a Fa Za) (split_low_le emin prec Hp4 a Fa Za)
           (split_high_le emin prec Hp4 b Fb Zb) (split_low_le emin prec Hp4 b Fb Zb).
fold ah al bh bl. intros Mah Mal Mbh Mbl.
(* everything is measured in units of U = 2^(prec - 5) eta *)
set (U := pow2 (emin + prec - 5)).
assert (U32 : pow2 (prec + emin) = 32 * U).
{ unfold U. replace (prec + emin)%Z with (5 + (emin + prec - 5))%Z by ring.
  rewrite bpow_plus. change (pow2 5) with 32. ring. }
assert (U8 : pow2 (emin + prec - 2) = 8 * U).
{ unfold U. replace (emin + prec - 2)%Z with (3 + (emin + prec - 5))%Z by ring.
  rewrite bpow_plus. change (pow2 3) with 8. ring. }
assert (U2 : pow2 (emin + prec - 4) = 2 * U).
{ unfold U. replace (emin + prec - 4)%Z with (1 + (emin + prec - 5))%Z by ring.
  rewrite bpow_plus. change (pow2 1) with 2. ring. }
assert (Hh : pow2 (emin - 1) <= U) by (apply bpow_le; lia).
assert (Hhalf : pow2 (emin - 1) = / 2 * pow2 emin).
{ replace (emin - 1)%Z with (-1 + emin)%Z by ring. rewrite bpow_plus. reflexivity. }
assert (U0 : 0 < U) by apply bpow_gt_0.
(* the partial products *)
assert (B1 : Rabs (ah * bl) <= 8 * U).
{ rewrite <- U8.
  apply Rle_trans with (pow2 (mag radix2 a + (mag radix2 b - prec + s - 1))).
  now apply abs_mult_le_pow2. apply bpow_le. lia. }
assert (B2 : Rabs (al * bh) <= 8 * U).
{ rewrite <- U8.
  apply Rle_trans with (pow2 (mag radix2 a - prec + s - 1 + mag radix2 b)).
  now apply abs_mult_le_pow2. apply bpow_le. lia. }
assert (B3 : Rabs (al * bl) <= U).
{ apply Rle_trans with (pow2 (mag radix2 a - prec + s - 1 + (mag radix2 b - prec + s - 1))).
  now apply abs_mult_le_pow2. apply bpow_le. lia. }
destruct Fpi as [G0 [G1 [G2 G3]]].
generalize (round_FLX_error emin prec tie_even _ G0) (round_FLX_error emin prec tie_even _ G1)
           (round_FLX_error emin prec tie_even _ G2) (round_FLX_error emin prec tie_even _ G3).
intros E0 E1 E2 E3.
assert (Ep : Rabs (rnd (a * b) - a * b) <= 2 * U).
{ rewrite <- U2.
  apply Rle_trans with (/ 2 * pow2 (Z.max (emin + 2 * prec - s - 1 - prec) emin)).
  - apply (round_error_bpow emin prec tie_even (a * b) (emin + 2 * prec - s - 1)).
    apply Rle_trans with (pow2 (mag radix2 a + mag radix2 b)).
    apply abs_mult_le_pow2; apply Rlt_le, bpow_mag_gt. apply bpow_le. lia.
  - rewrite Z.max_l by lia. change (/ 2) with (pow2 (-1)). rewrite <- bpow_plus.
    apply bpow_le. lia. }
(* either P0 is a multiple of eta, and then it is not rounded, or P3 is below eta / 8 *)
assert (Hcase : rnd (ah * bh) - ah * bh = 0
                \/ Rabs (rnd (al * bl) - al * bl) <= / 8 * pow2 emin).
{ destruct (Z_le_gt_dec emin (mag radix2 a - prec + s + (mag radix2 b - prec + s))) as [H|H].
  - left. rewrite round_generic; auto with typeclass_instances. ring.
    apply (FLT_format_FLX_FIX emin prec); trivial.
    apply FIX_format_le with (1 := H).
    apply FIX_format_mult; now apply split_high_FIX.
  - right. apply Rle_trans with (1 := round_error_le_abs emin prec tie_even _).
    apply Rle_trans with (pow2 (mag radix2 a - prec + s - 1 + (mag radix2 b - prec + s - 1))).
    now apply abs_mult_le_pow2.
    apply Rle_trans with (pow2 (-3 + emin)). apply bpow_le. lia.
    rewrite bpow_plus. change (pow2 (-3)) with (/ 8). lra. }
generalize Esum.
set (P0 := ah * bh) in *. set (P1 := ah * bl) in *. set (P2 := al * bh) in *.
set (P3 := al * bl) in *. set (P := a * b) in *.
set (p := rnd P) in *. set (q0 := rnd P0) in *. set (q1 := rnd P1) in *.
set (q2 := rnd P2) in *. set (q3 := rnd P3) in *.
intros Es.
apply Rabs_le_inv in B1, B2, B3, E0, E1, E2, E3, Ep.
(* the four sums are exact *)
assert (S1 : rnd (- p + q0) = - p + q0).
{ apply round_generic; auto with typeclass_instances.
  apply (FLT_format_plus_small radix2 emin prec).
  - apply generic_format_opp, Fr.
  - apply Fr.
  - rewrite U32. apply Rabs_le. lra. }
rewrite S1.
assert (S2 : rnd (- p + q0 + q1) = - p + q0 + q1).
{ apply round_generic; auto with typeclass_instances.
  apply (FLT_format_plus_small radix2 emin prec).
  - rewrite <- S1. apply Fr.
  - apply Fr.
  - rewrite U32. apply Rabs_le. lra. }
rewrite S2.
assert (S3 : rnd (- p + q0 + q1 + q2) = - p + q0 + q1 + q2).
{ apply round_generic; auto with typeclass_instances.
  apply (FLT_format_plus_small radix2 emin prec).
  - rewrite <- S2. apply Fr.
  - apply Fr.
  - rewrite U32. apply Rabs_le. lra. }
rewrite S3.
assert (S4 : rnd (- p + q0 + q1 + q2 + q3) = - p + q0 + q1 + q2 + q3).
{ apply round_generic; auto with typeclass_instances.
  apply (FLT_format_plus_small radix2 emin prec).
  - rewrite <- S3. apply Fr.
  - apply Fr.
  - rewrite U32. apply Rabs_le. lra. }
rewrite S4.
(* what is left is the sum of the four rounding errors *)
destruct Hcase as [Hc|Hc]; [|apply Rabs_le_inv in Hc]; apply Rabs_le; lra.
Qed.

Lemma tight_large :
  (emin <= ca + cb + s)%Z ->
  Rabs (a * b) < pow2 (2 * prec - 1 + emin) ->
  Rabs (fst (two_prod_dekker emin prec tie_even a b)
        + snd (two_prod_dekker emin prec tie_even a b) - a * b) <= pow2 emin.
Proof.
intros Hreg Hund. unfold ca, cb in Hreg.
(* the format with a smaller eta, where the product is above the exactness threshold *)
set (emin' := Z.min emin (mag radix2 a - prec + (mag radix2 b - prec) - 1)).
assert (He' : (emin' <= emin)%Z) by (unfold emin'; lia).
assert (Hp0 : (0 <= prec)%Z) by lia.
(* the partial products are numbers of F, the last one of F' *)
generalize (split_high_FIX emin prec Hp4 a Fa Za) (split_low_FIX emin prec Hp4 a Fa Za)
           (split_high_FIX emin prec Hp4 b Fb Zb) (split_low_FIX emin prec Hp4 b Fb Zb).
fold ah al bh bl. intros Iah Ial Ibh Ibl.
destruct Fpi as [G0 [G1 [G2 G3]]].
assert (F0 : format (ah * bh)).
{ apply (FLT_format_FLX_FIX emin prec); trivial.
  apply FIX_format_le with (mag radix2 a - prec + s + (mag radix2 b - prec + s))%Z. lia.
  now apply FIX_format_mult. }
assert (F1 : format (ah * bl)).
{ apply (FLT_format_FLX_FIX emin prec); trivial.
  apply FIX_format_le with (mag radix2 a - prec + s + (mag radix2 b - prec))%Z. lia.
  now apply FIX_format_mult. }
assert (F2 : format (al * bh)).
{ apply (FLT_format_FLX_FIX emin prec); trivial.
  apply FIX_format_le with (mag radix2 a - prec + (mag radix2 b - prec + s))%Z. lia.
  now apply FIX_format_mult. }
assert (F3' : generic_format radix2 (FLT_exp emin' prec) (al * bl)).
{ apply (FLT_format_FLX_FIX emin' prec); trivial.
  apply FIX_format_le with (mag radix2 a - prec + (mag radix2 b - prec))%Z.
  unfold emin'; lia. now apply FIX_format_mult. }
(* the product is in the normal range of F, and above the threshold of F' *)
assert (Hn : pow2 (mag radix2 a - 1 + (mag radix2 b - 1)) <= Rabs (a * b)).
{ rewrite Rabs_mult, bpow_plus.
  apply Rmult_le_compat; try apply bpow_ge_0; now apply bpow_mag_le. }
assert (Hn1 : pow2 (emin + prec - 1) <= Rabs (a * b)).
{ apply Rle_trans with (2 := Hn). apply bpow_le. lia. }
assert (Hn1' : pow2 (emin' + prec - 1) <= Rabs (a * b)).
{ apply Rle_trans with (2 := Hn1). apply bpow_le. lia. }
assert (Hn2 : pow2 (2 * prec - 1) * pow2 emin' <= Rabs (a * b)).
{ rewrite <- bpow_plus. apply Rle_trans with (2 := Hn). apply bpow_le. unfold emin'. lia. }
(* the kernel in F' is exact *)
generalize (two_prod_dekker_exact emin' prec Hp4 a b
              (format_emin_le emin prec emin' a He' Fa) (format_emin_le emin prec emin' b He' Fb)).
cbv zeta. intros [_ [_ Hex]]. specialize (Hex (or_intror Hn2)). revert Hex.
rewrite 2!two_prod_dekker_unfold. cbv zeta. cbn [fst snd].
rewrite (split_emin_le emin emin' prec tie_even a Hp0 He' Fa).
rewrite (split_emin_le emin emin' prec tie_even b Hp0 He' Fb).
fold ah al bh bl.
(* ... and computes the same p, t1, t2, t3 as in F *)
assert (Ep : round radix2 (FLT_exp emin' prec) (Znearest tie_even) (a * b) = rnd (a * b)).
{ rewrite 2!round_FLT_FLX; trivial. }
rewrite Ep. set (p := rnd (a * b)).
rewrite (round_generic radix2 (FLT_exp emin' prec) (Znearest tie_even) (ah * bh)
           (format_emin_le emin prec emin' _ He' F0)).
rewrite (round_generic radix2 (FLT_exp emin' prec) (Znearest tie_even) (ah * bl)
           (format_emin_le emin prec emin' _ He' F1)).
rewrite (round_generic radix2 (FLT_exp emin' prec) (Znearest tie_even) (al * bh)
           (format_emin_le emin prec emin' _ He' F2)).
rewrite (round_generic radix2 (FLT_exp emin' prec) (Znearest tie_even) (al * bl) F3').
rewrite (round_generic radix2 (FLT_exp emin prec) (Znearest tie_even) (ah * bh) F0).
rewrite (round_generic radix2 (FLT_exp emin prec) (Znearest tie_even) (ah * bl) F1).
rewrite (round_generic radix2 (FLT_exp emin prec) (Znearest tie_even) (al * bh) F2).
assert (Fp : format (- p)) by apply generic_format_opp, Fr.
rewrite <- (round_plus_FLT_emin emin emin' prec (Znearest tie_even) (- p) (ah * bh) He' Fp F0).
set (t1 := rnd (- p + ah * bh)).
rewrite <- (round_plus_FLT_emin emin emin' prec (Znearest tie_even) t1 (ah * bl) He' (Fr _) F1).
set (t2 := rnd (t1 + ah * bl)).
rewrite <- (round_plus_FLT_emin emin emin' prec (Znearest tie_even) t2 (al * bh) He' (Fr _) F2).
set (t3 := rnd (t2 + al * bh)).
set (x := t3 + al * bl). set (q3 := rnd (al * bl)).
intros Hex.
assert (Hr : round radix2 (FLT_exp emin' prec) (Znearest tie_even) x = a * b - p) by lra.
(* a b - p is at most half a unit in the last place of the product *)
assert (Hrb : Rabs (a * b - p) <= pow2 (emin + prec - 2)).
{ rewrite <- Rabs_Ropp, Ropp_minus_distr. unfold p.
  apply Rle_trans with (/ 2 * pow2 (Z.max (2 * prec - 1 + emin - prec) emin)).
  - apply (round_error_bpow emin prec tie_even (a * b) (2 * prec - 1 + emin)). now apply Rlt_le.
  - rewrite Z.max_l by lia. change (/ 2) with (pow2 (-1)). rewrite <- bpow_plus.
    apply bpow_le. lia. }
(* hence x = t3 + P3, which rounds to it in F', is at most 2^(prec - 1) eta *)
assert (Hx : Rabs x <= pow2 (emin + prec - 1)).
{ destruct (Rle_or_lt (Rabs x) (pow2 (emin + prec - 1))) as [H|H]; trivial. exfalso.
  assert (H' : pow2 (emin + prec - 1)
               <= Rabs (round radix2 (FLT_exp emin' prec) (Znearest tie_even) x)).
  { apply abs_round_ge_generic; auto with typeclass_instances.
    - apply generic_format_bpow. unfold FLT_exp. lia.
    - now apply Rlt_le. }
  rewrite Hr in H'.
  assert (pow2 (emin + prec - 2) < pow2 (emin + prec - 1)) by (apply bpow_lt; lia).
  lra. }
generalize (round_FLX_error emin prec tie_even _ G3). fold q3. intros E3.
assert (Hhalf : pow2 (emin - 1) = / 2 * pow2 emin).
{ replace (emin - 1)%Z with (-1 + emin)%Z by ring. rewrite bpow_plus. reflexivity. }
assert (Hhp : pow2 (prec + emin) = 2 * pow2 (emin + prec - 1)).
{ replace (prec + emin)%Z with (1 + (emin + prec - 1))%Z by ring.
  rewrite bpow_plus. change (pow2 1) with 2. ring. }
assert (Hle : pow2 (emin - 1) <= pow2 (emin + prec - 1)) by (apply bpow_le; lia).
(* so the last sum of the kernel is exact in F *)
assert (Sy : rnd (t3 + q3) = t3 + q3).
{ apply round_generic; auto with typeclass_instances.
  apply (FLT_format_plus_small radix2 emin prec).
  - apply Fr.
  - apply Fr.
  - replace (t3 + q3) with (x + (q3 - al * bl)) by (unfold x; ring).
    apply Rle_trans with (1 := Rabs_triang _ _). lra. }
rewrite Sy.
(* and x is rounded in F' with an error of at most eta/2 *)
assert (Ex : Rabs (round radix2 (FLT_exp emin' prec) (Znearest tie_even) x - x)
             <= pow2 (emin - 1)).
{ apply Rle_trans with (/ 2 * pow2 (Z.max (emin + prec - 1 - prec) emin')).
  - now apply (round_error_bpow emin' prec tie_even x (emin + prec - 1)).
  - change (/ 2) with (pow2 (-1)). rewrite <- bpow_plus. apply bpow_le. lia. }
replace (p + (t3 + q3) - a * b)
  with ((q3 - al * bl) - (round radix2 (FLT_exp emin' prec) (Znearest tie_even) x - x))
  by (rewrite Hr; unfold x; ring).
apply Rle_trans with (1 := Rabs_triang _ _). rewrite Rabs_Ropp. lra.
Qed.

End Tight.

(* All cases. *)
Lemma two_prod_dekker_defect :
  forall emin prec, (4 <= prec)%Z ->
  forall a b,
  generic_format radix2 (FLT_exp emin prec) a ->
  generic_format radix2 (FLT_exp emin prec) b ->
  Rabs (fst (two_prod_dekker emin prec tie_even a b)
        + snd (two_prod_dekker emin prec tie_even a b) - a * b) <= 13 / 8 * pow2 emin.
Proof.
intros emin prec Hp a b Fa Fb.
destruct (two_prod_dekker_exact emin prec Hp a b Fa Fb) as [_ [_ Hex]].
assert (H0 : 0 <= 13 / 8 * pow2 emin) by (generalize (bpow_ge_0 radix2 emin); lra).
assert (Hz : a * b = 0 \/ pow2 (2 * prec - 1) * pow2 emin <= Rabs (a * b) ->
  Rabs (fst (two_prod_dekker emin prec tie_even a b)
        + snd (two_prod_dekker emin prec tie_even a b) - a * b) <= 13 / 8 * pow2 emin).
{ intros H. rewrite (Hex H). unfold Rminus. now rewrite Rplus_opp_r, Rabs_R0. }
destruct (Req_dec a 0) as [Za|Za]. { apply Hz. left. rewrite Za. ring. }
destruct (Req_dec b 0) as [Zb|Zb]. { apply Hz. left. rewrite Zb. ring. }
destruct (Rle_or_lt (pow2 (2 * prec - 1) * pow2 emin) (Rabs (a * b))) as [H|H].
{ apply Hz. now right. }
destruct (Z_lt_le_dec (mag radix2 a - prec + (mag radix2 b - prec) + split_s prec) emin)
  as [Hreg|Hreg].
- now apply tight_small.
- apply Rle_trans with (pow2 emin).
  + apply tight_large; trivial. now rewrite bpow_plus.
  + generalize (bpow_ge_0 radix2 emin). lra.
Qed.

(** * The statement *)

Theorem two_prod_dekker_correct : two_prod_dekker_spec.
Proof.
intros emin prec Hp a b Fa Fb.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 4%Z; lia).
(* both outputs are results of a rounding *)
assert (Fp : fmt emin prec (fst (two_prod_dekker emin prec tie_even a b))).
{ rewrite two_prod_dekker_unfold. cbv zeta. cbn [fst snd]. limb_format. }
assert (Fe : fmt emin prec (snd (two_prod_dekker emin prec tie_even a b))).
{ rewrite two_prod_dekker_unfold. cbv zeta. cbn [fst snd]. limb_format. }
generalize (two_prod_dekker_exact emin prec Hp a b Fa Fb)
           (two_prod_dekker_defect emin prec Hp a b Fa Fb).
destruct (two_prod_dekker emin prec tie_even a b) as [p e]. cbn [fst snd] in *.
intros [H1 [_ H3]] H2. repeat split; trivial.
Qed.
