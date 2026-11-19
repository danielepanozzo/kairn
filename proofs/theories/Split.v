(* split: Veltkamp's splitting of a number of the format into a high part and a low part.

   The kernel (proofs/gen/Model.v), for a in F, with s = ceil(prec / 2):
       g  = RN ((2^s + 1) a)        d  = RN (a - g)
       ah = RN (g + d)              al = RN (a - ah)

   What is proved here, for every format with gradual underflow, prec >= 4, every emin, and
   ties to even (split_parts, split_products; split_correct is item 1 alone, the generated
   statement split_spec of proofs/gen/Statements.v):
     1. ah + al = a exactly, and ah, al are numbers of F;
     2. ah is a rounded to nearest, ties to even, in the format of precision
        prec - s = floor(prec / 2) with the same eta; so ah has at most floor(prec / 2)
        significant bits;
     3. al has at most s - 1 = ceil(prec / 2) - 1 significant bits. (One bit less than the
        s bits a low part has in an arbitrary radix: in radix 2 the low part is at most half
        a unit in the last place of ah, and when it is exactly half it is a power of two.)
     4. Hence, for the parts of two numbers a and b of F, each of the four products
        ah bh, ah bl, al bh, al bl has at most prec significant bits: it is a number of F
        as soon as it is a multiple of eta. This is what Dekker's product needs from the
        splitting, and it is where radix 2 matters when prec is odd (2 s = prec + 1 bits
        would be one too many).
   Subnormal a: nothing special happens. Every intermediate value is a multiple of eta, so
   the four operations round exactly as they would without underflow (split_emin_le); if a
   has at most floor(prec / 2) significant bits, in particular if
   |a| < 2^floor(prec/2) eta, then ah = a and al = 0.

   Sources. Items 1 and 2 are Flocq's Veltkamp_tail and Veltkamp_Even (Pff2Flocq.v, after
   Boldo's formalization of Dekker 1971 and Veltkamp), which are stated for emin <= 0 and
   2 <= s <= prec - 2; scaling by a power of two (Format.round_FLT_scale) removes the
   condition on emin, and s <= prec - 2 is the reason for prec >= 4. Item 3 is derived here
   from item 2.

   Not proved: prec <= 3. Exhaustive runs on toy formats (prec 1 to 10, all numbers, both
   signs, subnormals included) find items 1 and 2 true for every prec >= 1, and item 3 for
   every prec >= 3. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core Pff2Flocq.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Normalized.
Open Scope R_scope.

(** * The exponent of the splitter *)

(* s = ceil(prec / 2): the splitter is 2^s + 1. Flocq writes it prec - floor(prec / 2). *)
Definition split_s (prec : Z) : Z := ((prec + 1) / 2)%Z.

Lemma split_s_div2 : forall prec : Z, split_s prec = (prec - Z.div2 prec)%Z.
Proof. intros prec. unfold split_s. rewrite Z.div2_div. Z.div_mod_to_equations. lia. Qed.

Lemma split_s_bounds : forall prec : Z, (4 <= prec)%Z ->
  (2 <= split_s prec <= prec - 2)%Z.
Proof. intros prec H. unfold split_s. Z.div_mod_to_equations. lia. Qed.

(* 2 s is prec or prec + 1. *)
Lemma split_s_double : forall prec : Z, (prec <= 2 * split_s prec <= prec + 1)%Z.
Proof. intros prec. unfold split_s. Z.div_mod_to_equations. lia. Qed.

Lemma split_s_pos : forall prec : Z, (0 <= prec)%Z -> (0 <= split_s prec)%Z.
Proof. intros prec H. generalize (split_s_double prec). lia. Qed.

Lemma splitter_eq : forall prec : Z, splitter prec = pow2 (split_s prec) + 1.
Proof. reflexivity. Qed.

(* The splitter is an integer. *)
Lemma splitter_IZR : forall prec : Z, (0 <= prec)%Z ->
  splitter prec = IZR (2 ^ split_s prec + 1).
Proof.
intros prec H. rewrite splitter_eq, plus_IZR.
rewrite (IZR_Zpower radix2). reflexivity. now apply split_s_pos.
Qed.

(** * Multiples of eta round alike in every format with a smaller eta *)

(* An integer multiple of a multiple of eta is a multiple of eta. *)
Lemma FIX_mult_IZR :
  forall emin (n : Z) x, generic_format radix2 (FIX_exp emin) x ->
  generic_format radix2 (FIX_exp emin) (IZR n * x).
Proof.
intros emin n x Fx.
destruct (FIX_format_generic _ _ _ Fx) as [[m e] Hx He]. simpl in He.
apply generic_format_FIX. exists (Float radix2 (n * m) emin); trivial.
rewrite Hx. unfold F2R. simpl. rewrite He, mult_IZR. ring.
Qed.

(* [T2'] A multiple of eta rounds to the same number in F and in the format with the same
   precision and a smaller eta: either it is below 2^(emin + prec), and then it is a number
   of both formats, or it is in the range where they coincide. (Format.round_plus_FLT_emin
   is the special case of a sum of two numbers of F.) *)
Lemma round_FIX_FLT_emin :
  forall emin emin' prec {prec_gt_0_ : Prec_gt_0 prec} (rz : R -> Z) {Hr : Valid_rnd rz} x,
  (emin' <= emin)%Z ->
  generic_format radix2 (FIX_exp emin) x ->
  round radix2 (FLT_exp emin prec) rz x = round radix2 (FLT_exp emin' prec) rz x.
Proof.
intros emin emin' prec Hp rz Hr x He Fx.
destruct (Rle_or_lt (pow2 (emin + prec - 1)) (Rabs x)) as [H|H].
- rewrite round_FLT_FLX by exact H. symmetry. apply round_FLT_FLX.
  apply Rle_trans with (2 := H). apply bpow_le. lia.
- assert (F : generic_format radix2 (FLT_exp emin prec) x).
  { apply generic_format_FLT_FIX; trivial.
    apply Rlt_le, Rlt_le_trans with (1 := H). apply bpow_le. lia. }
  rewrite 2!round_generic; trivial.
  now apply format_emin_le with emin.
Qed.

(* Flocq writes "x is an integer multiple of 2^c" as generic_format radix2 (FIX_exp c) x.
   Multiples of 2^c are closed under subtraction, are multiples of every smaller power of
   two, and multiply as expected. *)
Lemma FIX_format_minus :
  forall c x y, generic_format radix2 (FIX_exp c) x -> generic_format radix2 (FIX_exp c) y ->
  generic_format radix2 (FIX_exp c) (x - y).
Proof.
intros c x y Fx Fy.
destruct (FIX_format_generic _ _ _ Fx) as [[mx ex] Hx Hex]. simpl in Hex.
destruct (FIX_format_generic _ _ _ Fy) as [[my ey] Hy Hey]. simpl in Hey.
apply generic_format_FIX. exists (Float radix2 (mx - my) c); trivial.
rewrite Hx, Hy. unfold F2R. simpl. rewrite Hex, Hey, minus_IZR. ring.
Qed.

Lemma FIX_format_mult :
  forall c1 c2 x y,
  generic_format radix2 (FIX_exp c1) x -> generic_format radix2 (FIX_exp c2) y ->
  generic_format radix2 (FIX_exp (c1 + c2)) (x * y).
Proof.
intros c1 c2 x y Fx Fy.
destruct (FIX_format_generic _ _ _ Fx) as [[mx ex] Hx Hex]. simpl in Hex.
destruct (FIX_format_generic _ _ _ Fy) as [[my ey] Hy Hey]. simpl in Hey.
apply generic_format_FIX. exists (Float radix2 (mx * my) (c1 + c2)); trivial.
rewrite Hx, Hy. unfold F2R. simpl. rewrite Hex, Hey, mult_IZR, bpow_plus. ring.
Qed.

Lemma FIX_format_le :
  forall c c' x, (c' <= c)%Z ->
  generic_format radix2 (FIX_exp c) x -> generic_format radix2 (FIX_exp c') x.
Proof.
intros c c' x H. apply generic_inclusion_mag. intros _. unfold FIX_exp. exact H.
Qed.

(* A multiple of eta with at most prec significant bits is a number of F. *)
Lemma FLT_format_FLX_FIX :
  forall emin prec {prec_gt_0_ : Prec_gt_0 prec} x,
  generic_format radix2 (FLX_exp prec) x -> generic_format radix2 (FIX_exp emin) x ->
  generic_format radix2 (FLT_exp emin prec) x.
Proof.
intros emin prec Hp x Fx Fi.
destruct (Rle_or_lt (pow2 (emin + prec - 1)) (Rabs x)) as [H|H].
- now apply generic_format_FLT_FLX.
- apply generic_format_FLT_FIX; trivial.
  apply Rlt_le, Rlt_le_trans with (1 := H). apply bpow_le. lia.
Qed.

(* A number with at most prec significant bits is rounded, in F, with an error of at most
   eta / 2: either it is in the normal range, and then it is a number of F, or it is below,
   where the numbers of F are the multiples of eta. *)
Lemma round_FLX_error :
  forall emin prec {prec_gt_0_ : Prec_gt_0 prec} choice x,
  generic_format radix2 (FLX_exp prec) x ->
  Rabs (round radix2 (FLT_exp emin prec) (Znearest choice) x - x) <= pow2 (emin - 1).
Proof.
intros emin prec Hp choice x Fx.
destruct (Rle_or_lt (pow2 (emin + prec - 1)) (Rabs x)) as [H|H].
- rewrite round_generic; auto with typeclass_instances.
  + unfold Rminus. rewrite Rplus_opp_r, Rabs_R0. apply bpow_ge_0.
  + now apply generic_format_FLT_FLX.
- apply Rle_trans with (/ 2 * ulp radix2 (FLT_exp emin prec) x).
  + apply error_le_half_ulp; auto with typeclass_instances.
  + rewrite ulp_FLT_small; trivial.
    * change (/ 2) with (pow2 (-1)). rewrite <- bpow_plus. apply bpow_le. lia.
    * apply Rlt_trans with (1 := H). apply bpow_lt. lia.
Qed.

(** * The kernel: its form in Flocq's terms, scaling, change of eta *)

Section Split.
Variable emin prec : Z.
Variable choice : Z -> bool.
Notation rnd := (round radix2 (FLT_exp emin prec) (Znearest choice)).

(* The kernel written as in Flocq's Veltkamp section. *)
Lemma split_unfold :
  forall a,
  split emin prec choice a =
  (rnd (rnd (a - rnd (a * (pow2 (prec - Z.div2 prec) + 1)))
        + rnd (a * (pow2 (prec - Z.div2 prec) + 1))),
   rnd (a - rnd (rnd (a - rnd (a * (pow2 (prec - Z.div2 prec) + 1)))
                 + rnd (a * (pow2 (prec - Z.div2 prec) + 1))))).
Proof.
intros a. unfold split. cbv zeta. rewrite splitter_eq, split_s_div2.
set (C := pow2 (prec - Z.div2 prec) + 1).
replace (C * a + 0) with (a * C) by ring.
set (g := rnd (a * C)). now rewrite (Rplus_comm g).
Qed.

(* Both parts are numbers of F, being results of a rounding. *)
Lemma split_format :
  forall {prec_gt_0_ : Prec_gt_0 prec} a,
  generic_format radix2 (FLT_exp emin prec) (fst (split emin prec choice a)) /\
  generic_format radix2 (FLT_exp emin prec) (snd (split emin prec choice a)).
Proof.
intros Hp a. unfold split. cbv zeta. cbn [fst snd].
split; apply generic_format_round; auto with typeclass_instances.
Qed.

End Split.

(* The splitting commutes with scaling by a power of two (which moves eta). *)
Lemma split_scale :
  forall emin prec choice a k,
  split (emin + k) prec choice (a * pow2 k)
  = (fst (split emin prec choice a) * pow2 k, snd (split emin prec choice a) * pow2 k).
Proof.
intros emin prec choice a k. unfold split. cbv zeta. cbn [fst snd].
set (C := splitter prec).
replace (C * (a * pow2 k) + 0) with ((C * a + 0) * pow2 k) by ring.
rewrite round_FLT_scale by auto with typeclass_instances.
set (g := round radix2 (FLT_exp emin prec) (Znearest choice) (C * a + 0)).
rewrite <- Rmult_minus_distr_r, round_FLT_scale by auto with typeclass_instances.
set (d := round radix2 (FLT_exp emin prec) (Znearest choice) (a - g)).
rewrite <- Rmult_plus_distr_r, round_FLT_scale by auto with typeclass_instances.
set (ah := round radix2 (FLT_exp emin prec) (Znearest choice) (g + d)).
now rewrite <- Rmult_minus_distr_r, round_FLT_scale by auto with typeclass_instances.
Qed.

(* A number of F is split in the same way in every format with the same precision and a
   smaller eta: every intermediate value is a multiple of eta. *)
Lemma split_emin_le :
  forall emin emin' prec {prec_gt_0_ : Prec_gt_0 prec} choice a,
  (0 <= prec)%Z -> (emin' <= emin)%Z ->
  generic_format radix2 (FLT_exp emin prec) a ->
  split emin' prec choice a = split emin prec choice a.
Proof.
intros emin emin' prec Hp choice a Hp0 He Fa. unfold split. cbv zeta.
assert (Fr : forall x, generic_format radix2 (FLT_exp emin prec)
               (round radix2 (FLT_exp emin prec) (Znearest choice) x)).
{ intros x. apply generic_format_round; auto with typeclass_instances. }
assert (Eg : round radix2 (FLT_exp emin' prec) (Znearest choice) (splitter prec * a + 0)
           = round radix2 (FLT_exp emin prec) (Znearest choice) (splitter prec * a + 0)).
{ symmetry. apply round_FIX_FLT_emin; auto with typeclass_instances.
  rewrite Rplus_0_r, splitter_IZR by exact Hp0.
  apply FIX_mult_IZR. now apply generic_format_FIX_FLT with prec. }
rewrite Eg.
set (g := round radix2 (FLT_exp emin prec) (Znearest choice) (splitter prec * a + 0)).
assert (Fg : generic_format radix2 (FLT_exp emin prec) g) by apply Fr.
rewrite <- (round_minus_FLT_emin emin emin' prec (Znearest choice) a g He Fa Fg).
set (d := round radix2 (FLT_exp emin prec) (Znearest choice) (a - g)).
assert (Fd : generic_format radix2 (FLT_exp emin prec) d) by apply Fr.
rewrite <- (round_plus_FLT_emin emin emin' prec (Znearest choice) g d He Fg Fd).
set (ah := round radix2 (FLT_exp emin prec) (Znearest choice) (g + d)).
assert (Fh : generic_format radix2 (FLT_exp emin prec) ah) by apply Fr.
now rewrite <- (round_minus_FLT_emin emin emin' prec (Znearest choice) a ah He Fa Fh).
Qed.

(** * Numbers with few significant bits *)

(* Notation: FLX_exp q is Flocq's name for "at most q significant bits, any exponent". *)

(* A number with at most q bits has at most q' bits for every q' >= q. *)
Lemma FLX_format_le :
  forall q q' : Z, Prec_gt_0 q -> (q <= q')%Z ->
  forall x, generic_format radix2 (FLX_exp q) x -> generic_format radix2 (FLX_exp q') x.
Proof.
intros q q' Hq Hqq x Fx.
assert (Hq' : Prec_gt_0 q') by (unfold Prec_gt_0 in *; lia).
destruct (FLX_format_generic radix2 q x Fx) as [[m e] Hx Hm]. simpl in Hm.
rewrite Hx. apply generic_format_FLX. exists (Float radix2 m e); trivial. simpl.
apply Z.lt_le_trans with (1 := Hm). apply (Zpower_le radix2). exact Hqq.
Qed.

(* The product of a number with at most q1 bits and a number with at most q2 bits has at
   most q1 + q2 bits. *)
Lemma FLX_format_mult :
  forall q1 q2 : Z, Prec_gt_0 q1 -> Prec_gt_0 q2 ->
  forall x y, generic_format radix2 (FLX_exp q1) x -> generic_format radix2 (FLX_exp q2) y ->
  generic_format radix2 (FLX_exp (q1 + q2)) (x * y).
Proof.
intros q1 q2 H1 H2 x y Fx Fy.
assert (H12 : Prec_gt_0 (q1 + q2)) by (unfold Prec_gt_0 in *; lia).
destruct (FLX_format_generic radix2 q1 x Fx) as [[mx ex] Hx Hmx]. simpl in Hmx.
destruct (FLX_format_generic radix2 q2 y Fy) as [[my ey] Hy Hmy]. simpl in Hmy.
apply generic_format_FLX. exists (Float radix2 (mx * my) (ex + ey)).
- rewrite Hx, Hy. unfold F2R. simpl. rewrite mult_IZR, bpow_plus. ring.
- simpl. rewrite Z.abs_mul.
  change (Zpower radix2 (q1 + q2)) with (2 ^ (q1 + q2))%Z.
  change (Zpower radix2 q1) with (2 ^ q1)%Z in Hmx.
  change (Zpower radix2 q2) with (2 ^ q2)%Z in Hmy.
  unfold Prec_gt_0 in H1, H2. rewrite Z.pow_add_r by lia.
  apply Z.mul_lt_mono_nonneg; lia.
Qed.

(* An integer multiple k 2^c with |k| <= 2^q has at most q bits (q >= 1): either |k| < 2^q,
   or the number is a power of two. *)
Lemma FLX_format_multiple :
  forall q : Z, Prec_gt_0 q ->
  forall (k c : Z), (Z.abs k <= 2 ^ q)%Z ->
  generic_format radix2 (FLX_exp q) (IZR k * pow2 c).
Proof.
intros q Hq k c Hk.
destruct (Z_lt_le_dec (Z.abs k) (2 ^ q)) as [H|H].
- apply generic_format_FLX. now exists (Float radix2 k c).
- assert (E : Z.abs k = (2 ^ q)%Z) by lia.
  assert (Hq0 : (0 <= q)%Z) by (unfold Prec_gt_0 in Hq; lia).
  assert (Ep : Rabs (IZR k * pow2 c) = pow2 (q + c)).
  { rewrite Rabs_mult, <- abs_IZR, E, (Rabs_pos_eq (pow2 c)) by apply bpow_ge_0.
    rewrite (IZR_Zpower radix2) by exact Hq0. now rewrite bpow_plus. }
  apply generic_format_abs_inv. rewrite Ep.
  apply generic_format_bpow. unfold FLX_exp. unfold Prec_gt_0 in Hq. lia.
Qed.

(** * Correctness of the splitting *)

Section Correct.
Variable emin prec : Z.
Hypothesis Hp4 : (4 <= prec)%Z.

Local Instance split_prec_gt_0 : Prec_gt_0 prec.
Proof. unfold Prec_gt_0. lia. Qed.

Notation s := (split_s prec).
Notation format := (generic_format radix2 (FLT_exp emin prec)).
Notation rnd := (round radix2 (FLT_exp emin prec) (Znearest tie_even)).

Let Hs : (2 <= s <= prec - 2)%Z.
Proof. now apply split_s_bounds. Qed.

Local Instance split_prech_gt_0 : Prec_gt_0 (prec - s).
Proof. unfold Prec_gt_0. lia. Qed.

Variable a : R.
Hypothesis Fa : format a.

Notation ah := (fst (split emin prec tie_even a)).
Notation al := (snd (split emin prec tie_even a)).

(* Scaling that brings eta to at most 1, where Flocq's theorems are stated. *)
Let k : Z := Z.min 0 (- emin).

Let Fak : generic_format radix2 (FLT_exp (emin + k) prec) (a * pow2 k).
Proof.
rewrite <- (round_generic radix2 (FLT_exp emin prec) (Znearest tie_even) a Fa).
rewrite <- round_FLT_scale by auto with typeclass_instances.
apply generic_format_round; auto with typeclass_instances.
Qed.

(* 1. The splitting is exact (Flocq's Veltkamp_tail). *)
Lemma split_sum : ah + al = a.
Proof.
generalize (Veltkamp_tail radix2 (emin + k) prec tie_even (prec - Z.div2 prec)).
rewrite <- split_s_div2. intros V.
destruct (V ltac:(lia) ltac:(unfold k; lia) ltac:(lia) ltac:(lia) (a * pow2 k) Fak) as [E _].
generalize (split_unfold (emin + k) prec tie_even (a * pow2 k)).
rewrite split_scale, <- split_s_div2. intros U.
assert (U1 := f_equal fst U). assert (U2 := f_equal snd U). cbn [fst snd] in U1, U2.
rewrite <- U2, <- U1 in E.
apply Rmult_eq_reg_r with (pow2 k).
- rewrite E. ring.
- apply Rgt_not_eq, bpow_gt_0.
Qed.

(* 2. The high part is the rounding of a to nearest even on prec - s bits (Flocq's
   Veltkamp_Even). *)
Lemma split_high : ah = RN emin (prec - s) a.
Proof.
generalize (Veltkamp_Even radix2 (emin + k) prec tie_even (prec - Z.div2 prec)).
rewrite <- split_s_div2. intros V.
generalize (V ltac:(lia) ltac:(unfold k; lia) ltac:(lia) ltac:(lia) (a * pow2 k) Fak eq_refl).
clear V.
generalize (split_unfold (emin + k) prec tie_even (a * pow2 k)).
rewrite split_scale, <- split_s_div2. intros U.
assert (U1 := f_equal fst U). cbn [fst snd] in U1.
rewrite <- U1. rewrite round_FLT_scale by auto with typeclass_instances. intros E.
apply Rmult_eq_reg_r with (pow2 k). exact E.
apply Rgt_not_eq, bpow_gt_0.
Qed.

Lemma split_high_format : format ah.
Proof. apply (split_format emin prec tie_even a). Qed.

Lemma split_low_format : format al.
Proof. apply (split_format emin prec tie_even a). Qed.

(* The high part has at most prec - s = floor(prec / 2) significant bits. *)
Lemma split_high_bits : generic_format radix2 (FLX_exp (prec - s)) ah.
Proof.
rewrite split_high. apply generic_format_FLX_FLT with emin.
apply generic_format_round; auto with typeclass_instances.
Qed.

(* 3. The low part has at most s - 1 significant bits.
   Proof: if a itself has at most prec - s bits then ah = a and al = 0. Otherwise a = m 2^c
   with c the exponent of a in F, the unit in the last place of a in the format of
   precision prec - s is 2^(c' + s) with c' <= c, and ah is a multiple of it; so
   al = a - ah is a multiple of 2^c, of magnitude at most half that unit, 2^(c' + s - 1):
   al = j 2^c with |j| <= 2^(s - 1). *)
Lemma split_low_bits : generic_format radix2 (FLX_exp (s - 1)) al.
Proof.
assert (Hs1 : Prec_gt_0 (s - 1)) by (unfold Prec_gt_0; lia).
assert (El : al = a - ah) by (generalize split_sum; lra).
set (fexph := FLT_exp emin (prec - s)).
destruct (Req_dec a 0) as [Za|Za].
{ rewrite El, split_high, Za. unfold RN. rewrite round_0 by auto with typeclass_instances.
  rewrite Rminus_0_r. apply generic_format_0. }
(* the exponent of a in F, and in the format of precision prec - s *)
set (c := cexp radix2 (FLT_exp emin prec) a).
set (ch := cexp radix2 fexph a).
destruct (Z_le_gt_dec ch c) as [Hc|Hc].
- (* a has at most prec - s bits *)
  assert (Fh : generic_format radix2 fexph a).
  { rewrite Fa. apply generic_format_F2R. intros _. rewrite <- Fa. exact Hc. }
  rewrite El, split_high. unfold RN. fold fexph.
  rewrite (round_generic radix2 fexph (Znearest tie_even) a Fh).
  unfold Rminus. rewrite Rplus_opp_r. apply generic_format_0.
- (* a has more bits *)
  assert (Hch : ch = (mag radix2 a - prec + s)%Z).
  { unfold ch, c, cexp, fexph, FLT_exp in *. lia. }
  assert (Hcc : (mag radix2 a - prec <= c)%Z).
  { unfold c, cexp, FLT_exp. lia. }
  (* a and ah as multiples of 2^c *)
  set (m := Ztrunc (scaled_mantissa radix2 (FLT_exp emin prec) a)).
  assert (Ea : a = IZR m * pow2 c) by exact Fa.
  set (mh := Znearest tie_even (scaled_mantissa radix2 fexph a)).
  assert (Eh : ah = IZR (mh * 2 ^ (ch - c)) * pow2 c).
  { rewrite split_high. unfold RN, round, F2R. cbn [Fnum Fexp]. fold fexph. fold ch. fold mh.
    rewrite mult_IZR, (IZR_Zpower radix2) by lia.
    rewrite Rmult_assoc, <- bpow_plus. now replace (ch - c + c)%Z with ch by ring. }
  assert (Ej : al = IZR (m - mh * 2 ^ (ch - c)) * pow2 c).
  { rewrite El, minus_IZR, Rmult_minus_distr_r, <- Ea, <- Eh. reflexivity. }
  rewrite Ej. apply FLX_format_multiple; trivial.
  (* |al| <= half a unit in the last place of the shorter format *)
  assert (Hhalf : Rabs al <= / 2 * pow2 ch).
  { rewrite El, <- Rabs_Ropp, Ropp_minus_distr, split_high. unfold RN.
    apply Rle_trans with (/ 2 * ulp radix2 (FLT_exp emin (prec - s)) a).
    - apply error_le_half_ulp; auto with typeclass_instances.
    - rewrite ulp_neq_0 by exact Za. fold fexph. fold ch. lra. }
  apply le_IZR. rewrite abs_IZR.
  apply Rmult_le_reg_r with (pow2 c). apply bpow_gt_0.
  rewrite <- (Rabs_pos_eq (pow2 c)) at 1 by apply bpow_ge_0.
  rewrite <- Rabs_mult, <- Ej.
  apply Rle_trans with (1 := Hhalf).
  rewrite (IZR_Zpower radix2) by lia. rewrite <- bpow_plus.
  change (/ 2) with (pow2 (-1)). rewrite <- bpow_plus. apply bpow_le. lia.
Qed.

(** Magnitudes. For a <> 0, Flocq's mag a is the integer m with 2^(m-1) <= |a| < 2^m, so
    that a is a multiple of 2^(m - prec). *)

Lemma format_mag_gt_emin : a <> 0 -> (emin < mag radix2 a)%Z.
Proof.
intros Za. apply mag_gt_bpow.
destruct (Rle_or_lt (pow2 emin) (Rabs a)) as [H|H]; trivial.
elim Za. now apply (format_lt_eta emin prec).
Qed.

(* |ah| <= 2^m. *)
Lemma split_high_le : a <> 0 -> Rabs ah <= pow2 (mag radix2 a).
Proof.
intros Za. generalize (format_mag_gt_emin Za). intros Hm.
rewrite split_high. unfold RN.
apply abs_round_le_generic; auto with typeclass_instances.
- apply generic_format_bpow. unfold FLT_exp. lia.
- apply Rlt_le, bpow_mag_gt.
Qed.

(* ah is a multiple of 2^(m - prec + s). *)
Lemma split_high_FIX :
  a <> 0 -> generic_format radix2 (FIX_exp (mag radix2 a - prec + s)) ah.
Proof.
intros Za. generalize (format_mag_gt_emin Za). intros Hm.
assert (Fh : generic_format radix2 (FLT_exp emin (prec - s)) ah).
{ rewrite split_high. apply generic_format_round; auto with typeclass_instances. }
revert Fh. apply generic_inclusion_mag. intros Zh.
assert (mag radix2 a <= mag radix2 ah)%Z.
{ apply mag_ge_bpow. rewrite split_high. unfold RN.
  apply abs_round_ge_generic; auto with typeclass_instances.
  - apply generic_format_bpow. unfold FLT_exp. lia.
  - now apply bpow_mag_le. }
unfold FIX_exp, FLT_exp. lia.
Qed.

(* al is a multiple of 2^(m - prec). *)
Lemma split_low_FIX : a <> 0 -> generic_format radix2 (FIX_exp (mag radix2 a - prec)) al.
Proof.
intros Za.
assert (El : al = a - ah) by (generalize split_sum; lra).
rewrite El. apply FIX_format_minus.
- revert Fa. apply generic_inclusion_mag. intros _. unfold FIX_exp, FLT_exp. lia.
- generalize (split_high_FIX Za). apply FIX_format_le. lia.
Qed.

(* |al| <= 2^(m - prec + s - 1): half a unit in the last place of ah. *)
Lemma split_low_le : a <> 0 -> Rabs al <= pow2 (mag radix2 a - prec + s - 1).
Proof.
intros Za.
assert (El : al = a - ah) by (generalize split_sum; lra).
set (fexph := FLT_exp emin (prec - s)).
destruct (Z_le_gt_dec (cexp radix2 fexph a) (cexp radix2 (FLT_exp emin prec) a)) as [Hc|Hc].
- assert (Fh : generic_format radix2 fexph a).
  { rewrite Fa. apply generic_format_F2R. intros _. rewrite <- Fa. exact Hc. }
  rewrite El, split_high. unfold RN. fold fexph.
  rewrite (round_generic radix2 fexph (Znearest tie_even) a Fh).
  unfold Rminus. rewrite Rplus_opp_r, Rabs_R0. apply bpow_ge_0.
- rewrite El, <- Rabs_Ropp, Ropp_minus_distr, split_high. unfold RN.
  apply Rle_trans with (/ 2 * ulp radix2 (FLT_exp emin (prec - s)) a).
  + apply error_le_half_ulp; auto with typeclass_instances.
  + rewrite ulp_neq_0 by exact Za. change (/ 2) with (pow2 (-1)). rewrite <- bpow_plus.
    apply bpow_le. unfold cexp, fexph, FLT_exp in *. lia.
Qed.

End Correct.

(** * The statements *)

(* Everything about one splitting: items 1 to 3 of the header. *)
Definition split_parts_spec : Prop :=
  forall emin prec : Z, (4 <= prec)%Z ->
  forall a : R, fmt emin prec a ->
  let s := ((prec + 1) / 2)%Z in
  let ah := fst (split emin prec tie_even a) in
  let al := snd (split emin prec tie_even a) in
  ah + al = a /\
  fmt emin prec ah /\ fmt emin prec al /\
  ah = RN emin (prec - s) a /\
  generic_format radix2 (FLX_exp (prec - s)) ah /\
  generic_format radix2 (FLX_exp (s - 1)) al.

Theorem split_parts : split_parts_spec.
Proof.
intros emin prec Hp a Fa s ah al. unfold fmt in *.
repeat split.
- now apply split_sum.
- now apply split_high_format.
- now apply split_low_format.
- now apply split_high.
- now apply split_high_bits.
- now apply split_low_bits.
Qed.

(* Item 4: the four products of the parts of two numbers of F have at most prec
   significant bits each. *)
Definition split_products_spec : Prop :=
  forall emin prec : Z, (4 <= prec)%Z ->
  forall a b : R, fmt emin prec a -> fmt emin prec b ->
  let ah := fst (split emin prec tie_even a) in
  let al := snd (split emin prec tie_even a) in
  let bh := fst (split emin prec tie_even b) in
  let bl := snd (split emin prec tie_even b) in
  generic_format radix2 (FLX_exp prec) (ah * bh) /\
  generic_format radix2 (FLX_exp prec) (ah * bl) /\
  generic_format radix2 (FLX_exp prec) (al * bh) /\
  generic_format radix2 (FLX_exp prec) (al * bl).

Theorem split_products : split_products_spec.
Proof.
intros emin prec Hp a b Fa Fb ah al bh bl. unfold fmt in *.
generalize (split_s_bounds prec Hp). intros Hs.
assert (Hh : Prec_gt_0 (prec - split_s prec)) by (unfold Prec_gt_0; lia).
assert (Hl : Prec_gt_0 (split_s prec - 1)) by (unfold Prec_gt_0; lia).
generalize (split_s_double prec). intros H2.
assert (Fah := split_high_bits emin prec Hp a Fa).
assert (Fal := split_low_bits emin prec Hp a Fa).
assert (Fbh := split_high_bits emin prec Hp b Fb).
assert (Fbl := split_low_bits emin prec Hp b Fb).
repeat split.
- apply FLX_format_le with (prec - split_s prec + (prec - split_s prec))%Z.
  unfold Prec_gt_0; lia. lia. now apply FLX_format_mult.
- apply FLX_format_le with (prec - split_s prec + (split_s prec - 1))%Z.
  unfold Prec_gt_0; lia. lia. now apply FLX_format_mult.
- apply FLX_format_le with (split_s prec - 1 + (prec - split_s prec))%Z.
  unfold Prec_gt_0; lia. lia. now apply FLX_format_mult.
- apply FLX_format_le with (split_s prec - 1 + (split_s prec - 1))%Z.
  unfold Prec_gt_0; lia. lia. now apply FLX_format_mult.
Qed.

(* The generated statement: item 1. *)
Theorem split_correct : split_spec.
Proof.
intros emin prec Hp a Fa.
generalize (split_sum emin prec Hp a Fa).
destruct (split emin prec tie_even a) as [ah al]. exact (fun H => H).
Qed.
