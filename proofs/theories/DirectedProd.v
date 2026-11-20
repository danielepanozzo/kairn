(* Rounding a product down and up without a rounding mode, in the real model (no
   overflow): the error of a rounded product, the sign of the error term of two_prod, and
   the listings mul_down_1, mul_up_1 and mul_dir_1
   (docs/developer/design/milestone2.md, "Rounding a product down and up").

   Notation: F is the format (precision prec, gradual underflow, smallest positive number
   eta = 2^emin, no largest number); u = 2^-prec; RN, RD, RU are the roundings to nearest,
   down and up; pred and succ are the neighbors in F. P = eta / (2 u^2) = 2^(2 prec - 1) eta
   is the threshold of two_prod's statement; (1 - u) P is the number of F just below P.
   For numbers a, b of F: x = a b, p = RN(x), e = RN(x - p): the two lines of two_prod.

   1. THE ERROR OF A ROUNDED PRODUCT. Three statements; the second and the third follow
      from the first:
      - mult_error_format: if |a b| > (2^prec - 1)^2 eta / 2, which is (1 - u)^2 P, then
        the error of rounding a b is a number of F. For every direction of rounding and
        every precision. The threshold is the best possible on |a b| in a format that
        has the number 1/2 (emin <= -1): the product of (2^prec - 1) 2^emin and
        (2^prec - 1) 2^-1 is equal to it, is not a multiple of eta, and its rounding error
        is eta / 2 in magnitude, which is not in F. (This remark is not a theorem of this
        file; it was checked on every pair of numbers of six small formats.)
      - mult_error_format_pred: if |RN(a b)| >= (1 - u) P, the same conclusion, for
        rounding to nearest with any tie rule and prec >= 2 (mult_error_format_pred_even:
        with ties to even, from precision 1). This is the strongest statement on the
        rounded product: the example above rounds to (1 - 2 u) P, the number of F before.
      - mult_error_format_ge: if |round(a b)| >= P, the same, for every direction of
        rounding and every precision. This is the lemma the design page asks for; Flocq's
        mult_error_FLT has it under |a b| >= P, and the difference is a product just
        below P that rounds up to P.
      Why: a product that large cannot have factors a = Ma 2^ea, b = Mb 2^eb (integers
      |Ma|, |Mb| < 2^prec) with ea + eb < emin, so it is a multiple of eta
      (mult_multiple_eta); then so is the error, which has at most prec significant bits
      (Flocq's mult_error_FLX), and such a number is in F (mult_error_multiple).

   2. THE SIGN OF THE ERROR TERM, for every tie rule and every precision:
      - e is zero or has the sign of x - p (two_prod_error_sign): rounding is monotone;
      - e = x - p exactly when |p| >= P, hence when x = 0 or |x| >= P
        (two_prod_error_exact, two_prod_error_exact_large); also when |p| >= (1 - u) P,
        for prec >= 2 (two_prod_error_exact_pred);
      - e = 0 and x <> p force 0 < |x - p| <= eta / 2 (two_prod_error_zero), and then
        0 < |x| <= (1 - u)^2 P < P; with ties to even, e = 0 exactly when
        |x - p| <= eta / 2 (two_prod_error_zero_iff).

   3. THE LISTINGS mul_down_1 and mul_up_1, for all numbers a, b of F:
      - mul_down_1 a b <= a b <= mul_up_1 a b, always;
      - mul_down_1 a b = RD(a b) and mul_up_1 a b = RU(a b) when a b = 0 or |RN(a b)| >= P,
        in particular when |a b| >= P;
      - otherwise mul_down_1 a b is RD(a b) or the number of F before it, and mul_up_1 a b
        is RU(a b) or the number after it; the wider result happens only for a nonzero
        product with |RN(a b)| < P.
      mul_dir_1 returns the pair (mul_down_1, mul_up_1): in the real model a zero factor
      gives p = 0, which is the literal zero of its last two lines.
      The facts hold for every positive precision and every tie rule
      (mul_down_1_listing_facts, mul_up_1_listing_facts); the theorems in the shape of a
      generated statement are for ties to even from precision 2, as the page states them.

   The fallback of the design page (the test le(ap, P) and a statement for |a b| > P) is
   not needed: the lemma holds at the boundary.

   THE MODELS IN THIS FILE ARE WRITTEN BY HAND (section Listings). Each mirrors a listing
   of the design page, line by line, in the text the generator prints for such a listing.
   The generated Model.mul_down_1, Model.mul_up_1 and Model.mul_dir_1 replace them, and
   the generated constant up(eta/(2*u^2)) replaces const_P, whose body is the term the
   generator prints for that expression; the definitions are expected to be convertible,
   so that the theorems transfer by `exact`, or after `unfold`. (Checked once, outside the
   build, on the text the generator prints for the kernel descriptions of
   experiments/milestone2/kernels: each definition is equal to its model here by
   reflexivity.) *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Mult_error.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format EFT Convert.
Open Scope R_scope.

(** * The error of a rounded product *)

Section ProductError.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.

(* A number of the format is an integer multiple of eta. *)
Lemma format_multiple_eta : forall x, format x -> exists m : Z, x = IZR m * pow2 emin.
Proof.
intros x Fx.
destruct (FLT_format_generic radix2 emin prec x Fx) as [f Hx Hm Hf].
exists (Fnum f * Zpower radix2 (Fexp f - emin))%Z.
rewrite Hx. unfold F2R. rewrite mult_IZR, IZR_Zpower by lia.
rewrite Rmult_assoc, <- bpow_plus. apply f_equal. apply f_equal. ring.
Qed.

(* If the product of two numbers of the format is a multiple of eta, the error of its
   rounding, in any direction, is a number of the format. In the normal range the error
   has at most prec significant bits (Flocq's mult_error_FLX) and is a multiple of eta;
   below it, the product itself is a number of the format. *)
Lemma mult_error_multiple :
  forall (rz : R -> Z) {Hr : Valid_rnd rz} a b,
  format a -> format b ->
  (exists m : Z, a * b = IZR m * pow2 emin) ->
  format (round radix2 fexp rz (a * b) - a * b).
Proof.
intros rz Hr a b Fa Fb [m Hm].
destruct (Rle_or_lt (pow2 (emin + prec - 1)) (Rabs (a * b))) as [H|H].
- assert (Fr : format (round radix2 fexp rz (a * b))).
  { apply generic_format_round; auto with typeclass_instances. }
  destruct (format_multiple_eta _ Fr) as [n Hn].
  assert (E : round radix2 fexp rz (a * b) - a * b = IZR (n - m) * pow2 emin).
  { rewrite Hn, Hm, minus_IZR. ring. }
  assert (X : generic_format radix2 (FLX_exp prec) (round radix2 fexp rz (a * b) - a * b)).
  { rewrite round_FLT_FLX by exact H.
    apply mult_error_FLX; auto with typeclass_instances;
      now apply generic_format_FLX_FLT with emin. }
  destruct (Rle_or_lt (pow2 (emin + prec - 1))
              (Rabs (round radix2 fexp rz (a * b) - a * b))) as [K|K].
  + now apply generic_format_FLT_FLX.
  + rewrite E. apply (format_multiple emin prec (n - m) emin (Z.le_refl emin)).
    rewrite <- E. apply Rlt_le, Rlt_le_trans with (1 := K). apply bpow_le. lia.
- assert (F : format (a * b)).
  { rewrite Hm. apply (format_multiple emin prec m emin (Z.le_refl emin)).
    rewrite <- Hm. apply Rlt_le, Rlt_le_trans with (1 := H). apply bpow_le. lia. }
  rewrite (round_generic radix2 fexp rz (a * b) F).
  unfold Rminus. rewrite Rplus_opp_r. apply generic_format_0.
Qed.

(* Two numbers of the format whose product exceeds (2^prec - 1)^2 eta / 2 in magnitude
   have a product that is a multiple of eta. Write a = Ma 2^ea and b = Mb 2^eb with
   integers |Ma|, |Mb| <= 2^prec - 1 and ea, eb >= emin: if ea + eb < emin then
   |a b| <= (2^prec - 1)^2 2^(emin - 1). *)
Lemma mult_multiple_eta :
  forall a b, format a -> format b ->
  (pow2 prec - 1) ^ 2 * pow2 (emin - 1) < Rabs (a * b) ->
  exists m : Z, a * b = IZR m * pow2 emin.
Proof.
intros a b Fa Fb H.
destruct (FLT_format_generic radix2 emin prec a Fa) as [fa Ha Ma Ea].
destruct (FLT_format_generic radix2 emin prec b Fb) as [fb Hb Mb Eb].
assert (Bound : forall M : Z, (Z.abs M < Zpower radix2 prec)%Z -> Rabs (IZR M) <= pow2 prec - 1).
{ intros M HM. rewrite <- abs_IZR.
  apply Rle_trans with (IZR (Zpower radix2 prec - 1)).
  - apply IZR_le. lia.
  - rewrite minus_IZR, IZR_Zpower by lia. apply Rle_refl. }
destruct (Z_lt_le_dec (Fexp fa + Fexp fb) emin) as [L|L].
- exfalso. apply (Rlt_irrefl (Rabs (a * b))). apply Rle_lt_trans with (2 := H).
  rewrite Ha, Hb. unfold F2R.
  replace (IZR (Fnum fa) * pow2 (Fexp fa) * (IZR (Fnum fb) * pow2 (Fexp fb)))
    with (IZR (Fnum fa) * IZR (Fnum fb) * pow2 (Fexp fa + Fexp fb))
    by (rewrite bpow_plus; ring).
  rewrite 2!Rabs_mult, (Rabs_pos_eq (pow2 (Fexp fa + Fexp fb))) by apply bpow_ge_0.
  replace ((pow2 prec - 1) ^ 2) with ((pow2 prec - 1) * (pow2 prec - 1)) by ring.
  apply Rmult_le_compat.
  + apply Rmult_le_pos; apply Rabs_pos.
  + apply bpow_ge_0.
  + apply Rmult_le_compat; try apply Rabs_pos; now apply Bound.
  + apply bpow_le. lia.
- exists (Fnum fa * Fnum fb * Zpower radix2 (Fexp fa + Fexp fb - emin))%Z.
  rewrite Ha, Hb. unfold F2R. rewrite 2!mult_IZR, IZR_Zpower by lia.
  assert (E : pow2 (Fexp fa) * pow2 (Fexp fb) = pow2 (Fexp fa + Fexp fb - emin) * pow2 emin).
  { rewrite <- 2!bpow_plus. apply f_equal. ring. }
  transitivity (IZR (Fnum fa) * IZR (Fnum fb) * (pow2 (Fexp fa) * pow2 (Fexp fb))).
  ring. rewrite E. ring.
Qed.

(* The error of a rounded product, first form: if |a b| > (2^prec - 1)^2 eta / 2, the
   error of rounding a b, in any direction, is a number of the format. For every
   positive precision. *)
Theorem mult_error_format :
  forall (rz : R -> Z) {Hr : Valid_rnd rz} a b,
  format a -> format b ->
  (pow2 prec - 1) ^ 2 * pow2 (emin - 1) < Rabs (a * b) ->
  format (round radix2 fexp rz (a * b) - a * b).
Proof.
intros rz Hr a b Fa Fb H.
apply mult_error_multiple; trivial. now apply mult_multiple_eta.
Qed.

(** ** The thresholds, in terms of P and u *)

(* P = 2^(2 prec - 1) eta, with U = 2^prec and E = eta / 2: P = U U E. *)
Lemma P_UUE : pow2 (2 * prec - 1 + emin) = pow2 prec * pow2 prec * pow2 (emin - 1).
Proof. rewrite <- 2!bpow_plus. apply f_equal. ring. Qed.

Lemma UE_eq : pow2 (prec - 1 + emin) = pow2 prec * pow2 (emin - 1).
Proof. rewrite <- bpow_plus. apply f_equal. ring. Qed.

(* P is the product of the two factors in which the generated statements write it. *)
Lemma P_split : pow2 (2 * prec - 1) * pow2 emin = pow2 (2 * prec - 1 + emin).
Proof. now rewrite <- bpow_plus. Qed.

(* (2^prec - 1)^2 eta / 2 is (1 - u)^2 P. *)
Lemma threshold_eq :
  (pow2 prec - 1) ^ 2 * pow2 (emin - 1) = (1 - pow2 (- prec)) ^ 2 * pow2 (2 * prec - 1 + emin).
Proof.
rewrite P_UUE, bpow_opp. field. apply Rgt_not_eq, bpow_gt_0.
Qed.

(* (1 - u) P is (2^prec - 1) 2^(prec - 1) eta. *)
Lemma pred_P_eq :
  (1 - pow2 (- prec)) * pow2 (2 * prec - 1 + emin) = (pow2 prec - 1) * pow2 (prec - 1 + emin).
Proof.
rewrite P_UUE, UE_eq, bpow_opp. field. apply Rgt_not_eq, bpow_gt_0.
Qed.

Lemma U_ge_2 : 2 <= pow2 prec.
Proof. rewrite <- pow2_1. apply bpow_le. lia. Qed.

Lemma E_gt_0 : 0 < pow2 (emin - 1).
Proof. apply bpow_gt_0. Qed.

(* An integer multiple c 2^k of a power of two with 0 <= c <= 2^prec and k >= emin is
   a number of the format. *)
Lemma format_below_top :
  forall c k : Z, (emin <= k)%Z -> (0 <= c <= Zpower radix2 prec)%Z -> format (IZR c * pow2 k).
Proof.
intros c k Hk Hc. apply (format_multiple emin prec c k Hk).
rewrite Rabs_mult, (Rabs_pos_eq (pow2 k)) by apply bpow_ge_0.
rewrite Rabs_pos_eq by (apply IZR_le; lia).
rewrite (Zplus_comm k prec), bpow_plus.
apply Rmult_le_compat_r. apply bpow_ge_0.
rewrite <- IZR_Zpower by lia. apply IZR_le. lia.
Qed.

Lemma Zpower_prec_ge_2 : (2 <= Zpower radix2 prec)%Z.
Proof.
generalize (Zpower_le radix2 1 prec). change (Zpower radix2 1) with 2%Z. lia.
Qed.

(* (1 - u) P and (1 - 2 u) P, as (2^prec - 1) 2^(prec - 1) eta and
   (2^prec - 2) 2^(prec - 1) eta, are numbers of the format. *)
Lemma format_pred_P : format ((pow2 prec - 1) * pow2 (prec - 1 + emin)).
Proof.
replace (pow2 prec - 1) with (IZR (Zpower radix2 prec - 1))
  by (rewrite minus_IZR, IZR_Zpower by lia; reflexivity).
apply format_below_top. lia. generalize Zpower_prec_ge_2. lia.
Qed.

Lemma format_pred_pred_P : format ((pow2 prec - 2) * pow2 (prec - 1 + emin)).
Proof.
replace (pow2 prec - 2) with (IZR (Zpower radix2 prec - 2))
  by (rewrite minus_IZR, IZR_Zpower by lia; reflexivity).
apply format_below_top. lia. generalize Zpower_prec_ge_2. lia.
Qed.

(* The error of a rounded product, third form (the lemma of the design page): if the
   rounding of a b, in any direction, is at least P = 2^(2 prec - 1) eta in magnitude,
   its error is a number of the format. For every positive precision. If |a b| were at
   most (1 - u)^2 P it would be at most (1 - u) P, a number of the format, and so would
   its rounding. *)
Theorem mult_error_format_ge :
  forall (rz : R -> Z) {Hr : Valid_rnd rz} a b,
  format a -> format b ->
  pow2 (2 * prec - 1 + emin) <= Rabs (round radix2 fexp rz (a * b)) ->
  format (round radix2 fexp rz (a * b) - a * b).
Proof.
intros rz Hr a b Fa Fb H.
apply mult_error_format; trivial.
apply Rnot_le_lt. intros K.
assert (L : Rabs (round radix2 fexp rz (a * b)) <= (pow2 prec - 1) * pow2 (prec - 1 + emin)).
{ apply abs_round_le_generic; auto with typeclass_instances.
  - exact format_pred_P.
  - apply Rle_trans with (1 := K). rewrite UE_eq.
    generalize U_ge_2 E_gt_0. intros HU HE.
    assert (0 <= (pow2 prec - 1) * pow2 (emin - 1)) by (apply Rmult_le_pos; lra).
    nra. }
rewrite P_UUE in H. rewrite UE_eq in L.
generalize U_ge_2 E_gt_0. intros HU HE.
assert (0 < pow2 prec * pow2 (emin - 1)) by (apply Rmult_lt_0_compat; lra).
nra.
Qed.

(* The error of a rounded product, second form: for rounding to nearest, with any tie
   rule, and prec >= 2, the same conclusion from |RN(a b)| >= (1 - u) P, the number of
   the format just below P. If |a b| were at most (1 - u)^2 P, the number (1 - 2 u) P of
   the format would be nearer to it than (1 - u) P, so the rounding would stay below
   (1 - u) P. *)
Theorem mult_error_format_pred :
  (2 <= prec)%Z ->
  forall (choice : Z -> bool) a b,
  format a -> format b ->
  (1 - pow2 (- prec)) * pow2 (2 * prec - 1 + emin)
    <= Rabs (round radix2 fexp (Znearest choice) (a * b)) ->
  format (round radix2 fexp (Znearest choice) (a * b) - a * b).
Proof.
intros Hp2 choice a b Fa Fb H.
apply mult_error_format; auto with typeclass_instances.
apply Rnot_le_lt. intros K.
rewrite pred_P_eq, UE_eq in H.
generalize format_pred_pred_P. rewrite UE_eq. intros FQ.
assert (HU : 4 <= pow2 prec) by (rewrite <- pow2_2; apply bpow_le; lia).
generalize E_gt_0. intros HE.
revert H K FQ. generalize (a * b). intros x H K FQ.
set (U := pow2 prec) in *. set (E := pow2 (emin - 1)) in *.
set (r := round radix2 fexp (Znearest choice) x) in *.
destruct (round_N_pt radix2 fexp choice x) as [_ N]. fold r in N.
assert (UE : 0 < U * E) by (apply Rmult_lt_0_compat; lra).
assert (E2 : 0 < E * (U - 2)) by (apply Rmult_lt_0_compat; lra).
apply Rabs_le_inv in K.
assert (B : Rabs r < (U - 1) * (U * E)).
{ apply Rabs_lt. split.
  - destruct (Rle_or_lt (- ((U - 2) * (U * E))) x) as [C|C].
    + assert (- ((U - 2) * (U * E)) <= r).
      { apply round_ge_generic; auto with typeclass_instances. now apply generic_format_opp. }
      nra.
    + generalize (N (- ((U - 2) * (U * E))) (generic_format_opp _ _ _ FQ)).
      rewrite (Rabs_pos_eq (- ((U - 2) * (U * E)) - x)) by lra.
      intros N'. apply Rabs_le_inv in N'. nra.
  - destruct (Rle_or_lt x ((U - 2) * (U * E))) as [C|C].
    + assert (r <= (U - 2) * (U * E)).
      { apply round_le_generic; auto with typeclass_instances. }
      nra.
    + generalize (N ((U - 2) * (U * E)) FQ).
      rewrite (Rabs_left ((U - 2) * (U * E) - x)) by lra.
      intros N'. apply Rabs_le_inv in N'. nra. }
lra.
Qed.

(* With ties to even the second form holds from precision 1: there (1 - u) P is eta, and
   a product of magnitude at most eta / 2 rounds to zero. *)
Theorem mult_error_format_pred_even :
  forall a b, format a -> format b ->
  (1 - pow2 (- prec)) * pow2 (2 * prec - 1 + emin) <= Rabs (RN emin prec (a * b)) ->
  format (RN emin prec (a * b) - a * b).
Proof.
intros a b Fa Fb H.
destruct (Z_le_gt_dec 2 prec) as [Hp2|Hp2].
- now apply mult_error_format_pred.
- assert (Hp1 : prec = 1%Z) by lia.
  apply (mult_error_format (Znearest tie_even)); auto with typeclass_instances.
  apply Rnot_le_lt. intros K.
  rewrite pred_P_eq, UE_eq in H.
  assert (HU : pow2 prec = 2) by (rewrite Hp1; apply pow2_1).
  rewrite HU in H, K.
  rewrite (RN_small_zero emin prec (a * b)) in H by (apply Rle_trans with (1 := K); lra).
  rewrite Rabs_R0 in H. generalize E_gt_0. lra.
Qed.

End ProductError.

(** * The sign of the error term of two_prod *)

Section TwoProdSign.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Variable choice : Z -> bool.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest choice)).
Notation succ := (succ radix2 fexp).
Notation pred := (pred radix2 fexp).
Notation P := (pow2 (2 * prec - 1 + emin)).

(* The two lines of two_prod (the product is an FMA with a zero addend): p = RN(a b) and
   e = RN(a b - p). *)
Lemma two_prod_eq :
  forall a b, two_prod emin prec choice a b = (rnd (a * b), rnd (a * b - rnd (a * b))).
Proof. intros a b. unfold two_prod. cbv zeta. now rewrite Rplus_0_r. Qed.

(* The computed error is zero or has the sign of the exact error x - p: rounding is
   monotone and rounds 0 to 0. For every real x and p. *)
Lemma two_prod_error_sign :
  forall x p : R,
  (0 <= x - p -> 0 <= rnd (x - p)) /\ (x - p <= 0 -> rnd (x - p) <= 0).
Proof.
intros x p. split; intros H.
- apply round_ge_generic; auto with typeclass_instances. apply generic_format_0.
- apply round_le_generic; auto with typeclass_instances. apply generic_format_0.
Qed.

(* Hence a positive computed error means p < x, and a negative one x < p. *)
Lemma two_prod_error_pos : forall x p : R, 0 < rnd (x - p) -> p < x.
Proof.
intros x p H. destruct (two_prod_error_sign x p) as [_ S].
destruct (Rlt_or_le p x) as [K|K]; trivial. exfalso. assert (rnd (x - p) <= 0) by (apply S; lra). lra.
Qed.

Lemma two_prod_error_neg : forall x p : R, rnd (x - p) < 0 -> x < p.
Proof.
intros x p H. destruct (two_prod_error_sign x p) as [S _].
destruct (Rlt_or_le x p) as [K|K]; trivial. exfalso. assert (0 <= rnd (x - p)) by (apply S; lra). lra.
Qed.

Variables a b : R.
Hypothesis Fa : format a.
Hypothesis Fb : format b.

(* The computed error is the exact error when the rounded product is at least P in
   magnitude. *)
Lemma two_prod_error_exact :
  P <= Rabs (rnd (a * b)) -> rnd (a * b - rnd (a * b)) = a * b - rnd (a * b).
Proof.
intros H. apply round_generic; auto with typeclass_instances.
replace (a * b - rnd (a * b)) with (- (rnd (a * b) - a * b)) by ring.
apply generic_format_opp. apply mult_error_format_ge; auto with typeclass_instances.
Qed.

(* In particular when the product is zero or at least P in magnitude: this is the
   condition of two_prod's statement. *)
Lemma two_prod_error_exact_large :
  a * b = 0 \/ P <= Rabs (a * b) -> rnd (a * b - rnd (a * b)) = a * b - rnd (a * b).
Proof.
intros [H|H].
- rewrite H, round_0, Rminus_0_r, round_0; auto with typeclass_instances.
- apply two_prod_error_exact. apply round_abs_ge; trivial.
  apply generic_format_bpow. unfold FLT_exp. generalize prec_gt_0_. unfold Prec_gt_0. lia.
Qed.

(* And already when the rounded product is at least (1 - u) P, the number of the format
   just below P, for prec >= 2. *)
Lemma two_prod_error_exact_pred :
  (2 <= prec)%Z ->
  (1 - pow2 (- prec)) * P <= Rabs (rnd (a * b)) ->
  rnd (a * b - rnd (a * b)) = a * b - rnd (a * b).
Proof.
intros Hp2 H. apply round_generic; auto with typeclass_instances.
replace (a * b - rnd (a * b)) with (- (rnd (a * b) - a * b)) by ring.
apply generic_format_opp. now apply mult_error_format_pred.
Qed.

(* A computed error of zero with an inexact product: the exact error is at most eta / 2
   in magnitude (the defect of two_prod), the product is not zero and is at most
   (1 - u)^2 P in magnitude, hence below P. *)
Lemma two_prod_error_zero :
  rnd (a * b - rnd (a * b)) = 0 -> a * b <> rnd (a * b) ->
  0 < Rabs (a * b - rnd (a * b)) <= / 2 * pow2 emin /\
  0 < Rabs (a * b) <= (pow2 prec - 1) ^ 2 * pow2 (emin - 1) /\
  Rabs (a * b) < P.
Proof.
intros Ez Ne.
assert (D := two_prod_defect emin prec choice a b
               (generic_format_FLX_FLT radix2 emin prec a Fa)
               (generic_format_FLX_FLT radix2 emin prec b Fb)).
cbv zeta in D. rewrite Ez, Rplus_0_r, <- Rabs_Ropp, Ropp_minus_distr in D.
assert (L : Rabs (a * b) <= (pow2 prec - 1) ^ 2 * pow2 (emin - 1)).
{ destruct (Rle_or_lt (Rabs (a * b)) ((pow2 prec - 1) ^ 2 * pow2 (emin - 1))) as [L|L]; trivial.
  exfalso. apply Ne.
  assert (F : format (rnd (a * b) - a * b)) by (apply mult_error_format; auto with typeclass_instances).
  assert (F' : format (a * b - rnd (a * b))).
  { replace (a * b - rnd (a * b)) with (- (rnd (a * b) - a * b)) by ring. now apply generic_format_opp. }
  rewrite (round_generic radix2 fexp (Znearest choice) _ F') in Ez. lra. }
split; [|split].
- split; [|exact D]. apply Rabs_pos_lt. lra.
- split; [|exact L]. apply Rabs_pos_lt. intros Z. apply Ne.
  rewrite Z, round_0; auto with typeclass_instances.
- apply Rle_lt_trans with (1 := L). rewrite (P_UUE emin prec).
  generalize (U_ge_2 prec) (E_gt_0 emin). intros HU HE.
  assert (0 < pow2 prec * pow2 (emin - 1)) by (apply Rmult_lt_0_compat; lra).
  nra.
Qed.

End TwoProdSign.

(* With ties to even, the computed error is zero exactly when the exact error is at most
   eta / 2 in magnitude. *)
Lemma two_prod_error_zero_iff :
  forall emin prec {prec_gt_0_ : Prec_gt_0 prec} a b,
  generic_format radix2 (FLT_exp emin prec) a -> generic_format radix2 (FLT_exp emin prec) b ->
  (RN emin prec (a * b - RN emin prec (a * b)) = 0
   <-> Rabs (a * b - RN emin prec (a * b)) <= / 2 * pow2 emin).
Proof.
intros emin prec Hp a b Fa Fb. split.
- intros Ez.
  assert (D := two_prod_defect emin prec tie_even a b
                 (generic_format_FLX_FLT radix2 emin prec a Fa)
                 (generic_format_FLX_FLT radix2 emin prec b Fb)).
  cbv zeta in D. unfold RN in Ez. rewrite Ez, Rplus_0_r, <- Rabs_Ropp, Ropp_minus_distr in D.
  exact D.
- intros H. apply (RN_small_zero emin prec).
  replace (emin - 1)%Z with (-1 + emin)%Z by ring. rewrite bpow_plus, pow2_m1. exact H.
Qed.

(** * The listings, as the generator prints a kernel *)

Section Listings.
Variable emin prec : Z.
Variable choice : Z -> bool.

(* Hand-written copy of the constant `const up(eta/(2*u^2))` of the listings: the
   expression eta / (2 u^2) rounded up to the format, in the term the generator prints
   for it. The generated constant (named up_K_0 after the first kernel K that uses it)
   replaces it. Its value is P = 2^(2 prec - 1) eta (const_P_eq). *)
Definition const_P : R :=
  round radix2 (FLT_exp emin prec) Zceil (bpow radix2 emin / (2 * (bpow radix2 (- prec) ^ 2))).

(* Hand-written model of the listing mul_down_1; the generated Model.mul_down_1
   replaces it. *)
Definition mul_down_1_listing (a b : R) : R :=
  let '(p, e) := two_prod emin prec choice a b in
  let ap := Rabs p in
  let bd := Rlt_bool ap const_P in
  let ez := Req_bool e 0 in
  let un := andb bd ez in
  let n := Rlt_bool e 0 in
  let sd := orb n un in
  let pp := pred radix2 (FLT_exp emin prec) p in
  let d := if sd then pp else p in
  let za := Req_bool a 0 in
  let zb := Req_bool b 0 in
  let zz := orb za zb in
  let r := if zz then p else d in
  r.

(* Hand-written model of the listing mul_up_1; the generated Model.mul_up_1 replaces
   it. *)
Definition mul_up_1_listing (a b : R) : R :=
  let '(p, e) := two_prod emin prec choice a b in
  let ap := Rabs p in
  let bd := Rlt_bool ap const_P in
  let ez := Req_bool e 0 in
  let un := andb bd ez in
  let n := Rlt_bool 0 e in
  let su := orb n un in
  let sp := succ radix2 (FLT_exp emin prec) p in
  let v := if su then sp else p in
  let za := Req_bool a 0 in
  let zb := Req_bool b 0 in
  let zz := orb za zb in
  let r := if zz then p else v in
  r.

(* Hand-written model of the listing mul_dir_1 (both directed products from one
   two_prod, a zero factor giving the literal zero); the generated Model.mul_dir_1
   replaces it. *)
Definition mul_dir_1_listing (a b : R) : R * R :=
  let '(p, e) := two_prod emin prec choice a b in
  let ap := Rabs p in
  let bd := Rlt_bool ap const_P in
  let ez := Req_bool e 0 in
  let un := andb bd ez in
  let n := Rlt_bool e 0 in
  let sd := orb n un in
  let pp := pred radix2 (FLT_exp emin prec) p in
  let dz := if sd then pp else p in
  let q := Rlt_bool 0 e in
  let su := orb q un in
  let sp := succ radix2 (FLT_exp emin prec) p in
  let vz := if su then sp else p in
  let za := Req_bool a 0 in
  let zb := Req_bool b 0 in
  let zz := orb za zb in
  let d := if zz then 0 else dz in
  let v := if zz then 0 else vz in
  (d, v).

End Listings.

(* The constant of the listings is P = eta / (2 u^2) = 2^(2 prec - 1) eta, which is a
   number of the format: rounding it up changes nothing. For every positive precision. *)
Lemma const_P_eq :
  forall emin prec {prec_gt_0_ : Prec_gt_0 prec}, const_P emin prec = pow2 (2 * prec - 1 + emin).
Proof.
intros emin prec Hp. unfold const_P.
assert (Hp0 : (0 < prec)%Z) by exact Hp.
assert (E : pow2 emin / (2 * pow2 (- prec) ^ 2) = pow2 (2 * prec - 1 + emin)).
{ replace (2 * pow2 (- prec) ^ 2) with (pow2 (1 + (- prec + - prec))).
  - unfold Rdiv. rewrite <- bpow_opp, <- bpow_plus. apply f_equal. ring.
  - rewrite 2!bpow_plus, pow2_1. ring. }
rewrite E. apply round_generic; auto with typeclass_instances.
apply generic_format_bpow. unfold FLT_exp. lia.
Qed.

(** * The directed products *)

Section DirectedProduct.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Variable choice : Z -> bool.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest choice)).
Notation succ := (succ radix2 fexp).
Notation pred := (pred radix2 fexp).
Notation rd := (round radix2 fexp Zfloor).
Notation ru := (round radix2 fexp Zceil).
Notation P := (pow2 (2 * prec - 1 + emin)).

(* A real number lies strictly between the neighbors of its rounding to nearest. *)
Lemma rnd_between : forall x, pred (rnd x) < x < succ (rnd x).
Proof.
intros x.
assert (Fp : format (rnd x)) by (apply generic_format_round; auto with typeclass_instances).
split.
- destruct (Rlt_or_le (pred (rnd x)) x) as [H|H]; trivial. exfalso.
  assert (K : rnd x <= pred (rnd x)).
  { apply round_le_generic; auto with typeclass_instances.
    apply generic_format_pred; auto with typeclass_instances. }
  generalize (pred_FLT_lt emin prec (rnd x)). lra.
- destruct (Rlt_or_le x (succ (rnd x))) as [H|H]; trivial. exfalso.
  assert (K : succ (rnd x) <= rnd x).
  { apply round_ge_generic; auto with typeclass_instances.
    apply generic_format_succ; auto with typeclass_instances. }
  generalize (succ_FLT_gt emin prec (rnd x)). lra.
Qed.

(* So the rounding down is the rounding to nearest or the number before it, and the
   rounding up is the rounding to nearest or the number after it, according to the side
   on which x lies. *)
Lemma rd_cases : forall x, (x < rnd x -> rd x = pred (rnd x)) /\ (rnd x <= x -> rd x = rnd x).
Proof.
intros x. destruct (rnd_between x) as [B1 B2].
assert (Fp : format (rnd x)) by (apply generic_format_round; auto with typeclass_instances).
split; intros H.
- apply (round_DN_eq radix2 fexp x (pred (rnd x))).
  + apply generic_format_pred; auto with typeclass_instances.
  + rewrite (succ_pred radix2 fexp (rnd x) Fp). split; lra.
- apply (round_DN_eq radix2 fexp x (rnd x) Fp). split; lra.
Qed.

Lemma ru_cases : forall x, (rnd x < x -> ru x = succ (rnd x)) /\ (x <= rnd x -> ru x = rnd x).
Proof.
intros x. destruct (rnd_between x) as [B1 B2].
assert (Fp : format (rnd x)) by (apply generic_format_round; auto with typeclass_instances).
split; intros H.
- apply (round_UP_eq radix2 fexp x (succ (rnd x))).
  + apply generic_format_succ; auto with typeclass_instances.
  + rewrite (pred_succ radix2 fexp (rnd x) Fp). split; lra.
- apply (round_UP_eq radix2 fexp x (rnd x) Fp). split; lra.
Qed.

Variables a b : R.
Hypothesis Fa : format a.
Hypothesis Fb : format b.

(* Closes a goal "F r, r on the right side of x, r is the directed rounding or ..., and
   r is the directed rounding when ..." once r has been rewritten as that rounding. *)
Local Ltac close F :=
  split; [exact F|split; [lra|split; [left; reflexivity|intros _; reflexivity]]].

(* The step down of the listing (its lines n, sd, pp, d), on the two values p and e that
   two_prod returns: p, or pred(p) when e < 0 or when |p| < P and e = 0. It is a number
   of the format, at most a b; it is RD(a b), or the number before RD(a b), the latter
   only when |p| < P, e = 0 and p <= a b; and it is RD(a b) when |p| >= P. *)
Lemma step_down_facts :
  let x := a * b in
  let p := rnd x in
  let e := rnd (x - p) in
  let d := if orb (Rlt_bool e 0) (andb (Rlt_bool (Rabs p) P) (Req_bool e 0)) then pred p else p in
  format d /\ d <= x /\
  (d = rd x \/ (d = pred (rd x) /\ Rabs p < P /\ e = 0)) /\
  (P <= Rabs p -> d = rd x).
Proof.
intros x p e d.
assert (Fp : format p) by (apply generic_format_round; auto with typeclass_instances).
assert (Fpp : format (pred p)) by (apply generic_format_pred; auto with typeclass_instances).
destruct (rnd_between x) as [B1 B2]. fold p in B1, B2.
destruct (rd_cases x) as [D1 D2]. fold p in D1, D2.
destruct (two_prod_error_sign emin prec choice x p) as [S1 S2]. fold e in S1, S2.
generalize (two_prod_error_exact emin prec choice a b Fa Fb). fold x p e. intros X.
unfold d. clear d.
destruct (Rlt_bool_spec e 0) as [En|En]; cbn [orb].
- (* e < 0: x < p, and RD(x) = pred(p) *)
  assert (L : x < p) by (destruct (Rlt_or_le x p); trivial; exfalso; generalize (S1 ltac:(lra)); lra).
  rewrite (D1 L). close Fpp.
- destruct (Rlt_bool_spec (Rabs p) P) as [Bd|Bd]; destruct (Req_bool_spec e 0) as [Ez|Ez]; cbn [andb].
  + (* below P with a zero error: one step down, which may be one too many *)
    split; [exact Fpp|split; [lra|split]].
    * destruct (Rlt_or_le x p) as [L|L].
      -- left. now rewrite (D1 L).
      -- right. rewrite (D2 L). auto.
    * intros K. exfalso. lra.
  + (* a positive error: p < x, and RD(x) = p *)
    assert (L : p <= x) by (destruct (Rle_or_lt p x); trivial; exfalso; generalize (S2 ltac:(lra)); lra).
    rewrite (D2 L). close Fp.
  + (* at least P with a zero error: the product is exact *)
    assert (L : p <= x) by (generalize (X Bd); lra).
    rewrite (D2 L). close Fp.
  + assert (L : p <= x) by (destruct (Rle_or_lt p x); trivial; exfalso; generalize (S2 ltac:(lra)); lra).
    rewrite (D2 L). close Fp.
Qed.

(* The step up, likewise: p, or succ(p) when 0 < e or when |p| < P and e = 0. *)
Lemma step_up_facts :
  let x := a * b in
  let p := rnd x in
  let e := rnd (x - p) in
  let v := if orb (Rlt_bool 0 e) (andb (Rlt_bool (Rabs p) P) (Req_bool e 0)) then succ p else p in
  format v /\ x <= v /\
  (v = ru x \/ (v = succ (ru x) /\ Rabs p < P /\ e = 0)) /\
  (P <= Rabs p -> v = ru x).
Proof.
intros x p e v.
assert (Fp : format p) by (apply generic_format_round; auto with typeclass_instances).
assert (Fsp : format (succ p)) by (apply generic_format_succ; auto with typeclass_instances).
destruct (rnd_between x) as [B1 B2]. fold p in B1, B2.
destruct (ru_cases x) as [D1 D2]. fold p in D1, D2.
destruct (two_prod_error_sign emin prec choice x p) as [S1 S2]. fold e in S1, S2.
generalize (two_prod_error_exact emin prec choice a b Fa Fb). fold x p e. intros X.
unfold v. clear v.
destruct (Rlt_bool_spec 0 e) as [En|En]; cbn [orb].
- (* 0 < e: p < x, and RU(x) = succ(p) *)
  assert (L : p < x) by (destruct (Rlt_or_le p x); trivial; exfalso; generalize (S2 ltac:(lra)); lra).
  rewrite (D1 L). close Fsp.
- destruct (Rlt_bool_spec (Rabs p) P) as [Bd|Bd]; destruct (Req_bool_spec e 0) as [Ez|Ez]; cbn [andb].
  + split; [exact Fsp|split; [lra|split]].
    * destruct (Rlt_or_le p x) as [L|L].
      -- left. now rewrite (D1 L).
      -- right. rewrite (D2 L). auto.
    * intros K. exfalso. lra.
  + assert (L : x <= p) by (destruct (Rle_or_lt x p); trivial; exfalso; generalize (S1 ltac:(lra)); lra).
    rewrite (D2 L). close Fp.
  + assert (L : x <= p) by (generalize (X Bd); lra).
    rewrite (D2 L). close Fp.
  + assert (L : x <= p) by (destruct (Rle_or_lt x p); trivial; exfalso; generalize (S1 ltac:(lra)); lra).
    rewrite (D2 L). close Fp.
Qed.

(* mul_down_1: the result is a number of the format and is at most a b; it is RD(a b), or
   the number of the format before RD(a b), the latter only for a nonzero product whose
   rounding to nearest is below P in magnitude; and it is RD(a b) when a b = 0 or
   |RN(a b)| >= P. For every positive precision and every tie rule. *)
Theorem mul_down_1_listing_facts :
  let r := mul_down_1_listing emin prec choice a b in
  format r /\ r <= a * b /\
  (r = rd (a * b) \/ (r = pred (rd (a * b)) /\ a * b <> 0 /\ Rabs (rnd (a * b)) < P)) /\
  (a * b = 0 \/ P <= Rabs (rnd (a * b)) -> r = rd (a * b)).
Proof.
intros r. unfold r, mul_down_1_listing. clear r.
rewrite two_prod_eq, (const_P_eq emin prec). cbv beta iota zeta.
assert (Zero : a * b = 0 ->
  format (rnd (a * b)) /\ rnd (a * b) <= a * b /\
  (rnd (a * b) = rd (a * b) \/
   (rnd (a * b) = pred (rd (a * b)) /\ a * b <> 0 /\ Rabs (rnd (a * b)) < P)) /\
  (a * b = 0 \/ P <= Rabs (rnd (a * b)) -> rnd (a * b) = rd (a * b))).
{ intros Z. rewrite Z, 2!round_0; auto with typeclass_instances.
  split; [apply generic_format_0|split; [apply Rle_refl|split; auto]]. }
destruct (Req_bool_spec a 0) as [Za|Za]; cbn [orb].
{ apply Zero. rewrite Za. ring. }
destruct (Req_bool_spec b 0) as [Zb|Zb].
{ apply Zero. rewrite Zb. ring. }
destruct step_down_facts as [F [L [C X]]].
split; [exact F|split; [exact L|split]].
- destruct C as [C|[C [Bd _]]]; [now left|right].
  split; [exact C|split; [|exact Bd]].
  intros Z. destruct (Rmult_integral _ _ Z); contradiction.
- intros [Z|K]; [|now apply X].
  destruct (Rmult_integral _ _ Z); contradiction.
Qed.

(* mul_up_1: the result is a number of the format and is at least a b; it is RU(a b), or
   the number of the format after RU(a b), the latter only for a nonzero product whose
   rounding to nearest is below P in magnitude; and it is RU(a b) when a b = 0 or
   |RN(a b)| >= P. For every positive precision and every tie rule. *)
Theorem mul_up_1_listing_facts :
  let r := mul_up_1_listing emin prec choice a b in
  format r /\ a * b <= r /\
  (r = ru (a * b) \/ (r = succ (ru (a * b)) /\ a * b <> 0 /\ Rabs (rnd (a * b)) < P)) /\
  (a * b = 0 \/ P <= Rabs (rnd (a * b)) -> r = ru (a * b)).
Proof.
intros r. unfold r, mul_up_1_listing. clear r.
rewrite two_prod_eq, (const_P_eq emin prec). cbv beta iota zeta.
assert (Zero : a * b = 0 ->
  format (rnd (a * b)) /\ a * b <= rnd (a * b) /\
  (rnd (a * b) = ru (a * b) \/
   (rnd (a * b) = succ (ru (a * b)) /\ a * b <> 0 /\ Rabs (rnd (a * b)) < P)) /\
  (a * b = 0 \/ P <= Rabs (rnd (a * b)) -> rnd (a * b) = ru (a * b))).
{ intros Z. rewrite Z, 2!round_0; auto with typeclass_instances.
  split; [apply generic_format_0|split; [apply Rle_refl|split; auto]]. }
destruct (Req_bool_spec a 0) as [Za|Za]; cbn [orb].
{ apply Zero. rewrite Za. ring. }
destruct (Req_bool_spec b 0) as [Zb|Zb].
{ apply Zero. rewrite Zb. ring. }
destruct step_up_facts as [F [L [C X]]].
split; [exact F|split; [exact L|split]].
- destruct C as [C|[C [Bd _]]]; [now left|right].
  split; [exact C|split; [|exact Bd]].
  intros Z. destruct (Rmult_integral _ _ Z); contradiction.
- intros [Z|K]; [|now apply X].
  destruct (Rmult_integral _ _ Z); contradiction.
Qed.

End DirectedProduct.

(* mul_dir_1 returns the results of mul_down_1 and of mul_up_1: with a zero factor the
   rounded product p that those return is the zero that mul_dir_1 returns. For all real
   numbers a and b. *)
Lemma mul_dir_1_listing_eq :
  forall emin prec {prec_gt_0_ : Prec_gt_0 prec} choice a b,
  mul_dir_1_listing emin prec choice a b
  = (mul_down_1_listing emin prec choice a b, mul_up_1_listing emin prec choice a b).
Proof.
intros emin prec Hp choice a b.
unfold mul_dir_1_listing, mul_down_1_listing, mul_up_1_listing.
rewrite two_prod_eq. cbv beta iota zeta.
assert (Zero : a * b = 0 -> round radix2 (FLT_exp emin prec) (Znearest choice) (a * b) = 0).
{ intros Z. rewrite Z. apply round_0; auto with typeclass_instances. }
destruct (Req_bool_spec a 0) as [Za|Za]; cbn [orb].
{ rewrite Zero by (rewrite Za; ring). reflexivity. }
destruct (Req_bool_spec b 0) as [Zb|Zb].
{ rewrite Zero by (rewrite Zb; ring). reflexivity. }
reflexivity.
Qed.

(** * The statements, in the shape of a generated statement *)

(* mul_down_1, for numbers a, b of the format, ties to even, from precision 2 (as the
   design page states it; the facts above need only a positive precision): the result r
   is a number of the format; r <= a b; r is RD(a b) or the number of the format before
   it; and r = RD(a b) when a b = 0 or |a b| >= 2^(2 prec - 1) eta. *)
Theorem mul_down_1_listing_correct :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R,
  fmt emin prec a ->
  fmt emin prec b ->
  let r := mul_down_1_listing emin prec tie_even a b in
  fmt emin prec r /\
  r <= (a * b) /\
  (r = RD emin prec (a * b) \/ r = pred radix2 (FLT_exp emin prec) (RD emin prec (a * b))) /\
  (((a * b) = 0 \/ bpow radix2 (2 * prec - 1) * eta emin <= Rabs (a * b)) -> r = RD emin prec (a * b)).
Proof.
intros emin prec Hp a b Fa Fb r. unfold r. clear r.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
destruct (mul_down_1_listing_facts emin prec tie_even a b Fa Fb) as [F [L [C X]]].
split; [exact F|split; [exact L|split]].
- destruct C as [C|[C _]]; [now left|now right].
- intros [Z|K]; apply X; [now left|right].
  unfold eta in K. rewrite P_split in K.
  apply round_abs_ge; trivial.
  apply generic_format_bpow. unfold FLT_exp. lia.
Qed.

(* mul_up_1, likewise: the result r is a number of the format; a b <= r; r is RU(a b) or
   the number of the format after it; and r = RU(a b) when a b = 0 or
   |a b| >= 2^(2 prec - 1) eta. *)
Theorem mul_up_1_listing_correct :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R,
  fmt emin prec a ->
  fmt emin prec b ->
  let r := mul_up_1_listing emin prec tie_even a b in
  fmt emin prec r /\
  (a * b) <= r /\
  (r = RU emin prec (a * b) \/ r = succ radix2 (FLT_exp emin prec) (RU emin prec (a * b))) /\
  (((a * b) = 0 \/ bpow radix2 (2 * prec - 1) * eta emin <= Rabs (a * b)) -> r = RU emin prec (a * b)).
Proof.
intros emin prec Hp a b Fa Fb r. unfold r. clear r.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
destruct (mul_up_1_listing_facts emin prec tie_even a b Fa Fb) as [F [L [C X]]].
split; [exact F|split; [exact L|split]].
- destruct C as [C|[C _]]; [now left|now right].
- intros [Z|K]; apply X; [now left|right].
  unfold eta in K. rewrite P_split in K.
  apply round_abs_ge; trivial.
  apply generic_format_bpow. unfold FLT_exp. lia.
Qed.

(* mul_dir_1: its two outputs satisfy the statements of mul_down_1 and of mul_up_1. *)
Theorem mul_dir_1_listing_correct :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R,
  fmt emin prec a ->
  fmt emin prec b ->
  let '(d, v) := mul_dir_1_listing emin prec tie_even a b in
  fmt emin prec d /\
  fmt emin prec v /\
  d <= (a * b) /\
  (d = RD emin prec (a * b) \/ d = pred radix2 (FLT_exp emin prec) (RD emin prec (a * b))) /\
  (((a * b) = 0 \/ bpow radix2 (2 * prec - 1) * eta emin <= Rabs (a * b)) -> d = RD emin prec (a * b)) /\
  (a * b) <= v /\
  (v = RU emin prec (a * b) \/ v = succ radix2 (FLT_exp emin prec) (RU emin prec (a * b))) /\
  (((a * b) = 0 \/ bpow radix2 (2 * prec - 1) * eta emin <= Rabs (a * b)) -> v = RU emin prec (a * b)).
Proof.
intros emin prec Hp a b Fa Fb.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
rewrite (mul_dir_1_listing_eq emin prec).
destruct (mul_down_1_listing_correct emin prec Hp a b Fa Fb) as [F1 [L1 [C1 X1]]].
destruct (mul_up_1_listing_correct emin prec Hp a b Fa Fb) as [F2 [L2 [C2 X2]]].
exact (conj F1 (conj F2 (conj L1 (conj C1 (conj X1 (conj L2 (conj C2 X2))))))).
Qed.

(* The statements of the sign of the error term on the two outputs of two_prod, for
   numbers a, b of the format, ties to even, from precision 2: e is zero or has the
   sign of a b - p; e = a b - p when a b = 0 or |a b| >= 2^(2 prec - 1) eta; and e = 0
   with a b <> p forces 0 < |a b - p| <= eta / 2. *)
Theorem two_prod_sign :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R,
  fmt emin prec a ->
  fmt emin prec b ->
  let '(p, e) := two_prod emin prec tie_even a b in
  (0 <= (a * b) - p -> 0 <= e) /\
  ((a * b) - p <= 0 -> e <= 0) /\
  (((a * b) = 0 \/ bpow radix2 (2 * prec - 1) * eta emin <= Rabs (a * b)) -> e = (a * b) - p) /\
  (e = 0 -> (a * b) <> p -> 0 < Rabs ((a * b) - p) <= (1 / 2) * eta emin).
Proof.
intros emin prec Hp a b Fa Fb.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
rewrite two_prod_eq.
destruct (two_prod_error_sign emin prec tie_even (a * b)
            (round radix2 (FLT_exp emin prec) (Znearest tie_even) (a * b))) as [S1 S2].
split; [exact S1|split; [exact S2|split]].
- intros H. apply two_prod_error_exact_large; trivial.
  unfold eta in H. now rewrite P_split in H.
- intros Ez Ne. destruct (two_prod_error_zero emin prec tie_even a b Fa Fb Ez Ne) as [[H1 H2] _].
  unfold eta. lra.
Qed.
