(* The three error-free transformations: two_sum, fast_two_sum, two_prod.

   Sources. TwoSum and Fast2Sum with gradual underflow are in Flocq (Pff2Flocq.v), for a
   format whose minimum exponent is at most 0; the transfer lemmas remove that
   restriction. The exactness of TwoProd above 2^(2 prec - 1) eta is Flocq's
   mult_error_FLT. The bound eta/2 on the defect of TwoProd for small products is new
   here; with constant 1 instead of 1/2 it is known for every rounding (HJZRT23). *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core Plus_error Mult_error Relative Pff2Flocq.
From Kairn Require Import ModelDraft SpecDraft Format Transfer.
Open Scope R_scope.

(* The tie rule "to even" is symmetric: this is what makes RN (- x) = - RN x. *)
Lemma tie_even_sym : forall n : Z, tie_even n = negb (tie_even (- (n + 1))).
Proof.
intros n. unfold tie_even.
now rewrite Bool.negb_involutive, Z.even_opp, Z.add_1_r, Z.even_succ, Z.negb_even.
Qed.

Lemma RN_opp : forall emin prec x, RN emin prec (- x) = - RN emin prec x.
Proof. intros emin prec x. rewrite 2!RN_eq. apply round_NE_opp. Qed.

Section EFT.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).

(** * TwoSum *)

(* For all a, b in F: s = RN (a + b) and s + e = a + b exactly (Knuth; Flocq's
   TwoSum_correct). No condition on emin. *)
Lemma two_sum_exact :
  (2 <= prec)%Z ->
  forall a b, format a -> format b ->
  fst (two_sum emin prec tie_even a b) = rnd (a + b) /\
  fst (two_sum emin prec tie_even a b) + snd (two_sum emin prec tie_even a b) = a + b.
Proof.
intros Hp a b Fa Fb. split. reflexivity.
assert (He : (Z.min emin 0 <= emin)%Z) by lia.
rewrite (two_sum_emin emin (Z.min emin 0) prec He tie_even a b Fa Fb).
unfold two_sum. cbv zeta. simpl fst. simpl snd.
apply TwoSum_correct; try lia; auto using tie_even_sym;
  now apply format_emin_le with emin.
Qed.

(** * Fast2Sum *)

(* For a, b in F with |a| >= |b|: s = RN (a + b) and s + e = a + b exactly (Dekker;
   Flocq's Fast2Sum_correct, which is stated for e = RN (b + RN (a - s))). *)
Lemma fast_two_sum_exact :
  (2 <= prec)%Z ->
  forall a b, format a -> format b -> Rabs b <= Rabs a ->
  fst (fast_two_sum emin prec tie_even a b) = rnd (a + b) /\
  fst (fast_two_sum emin prec tie_even a b) + snd (fast_two_sum emin prec tie_even a b) = a + b.
Proof.
intros Hp a b Fa Fb Hab. split. reflexivity.
assert (He : (Z.min emin 0 <= emin)%Z) by lia.
rewrite (fast_two_sum_emin emin (Z.min emin 0) prec He tie_even a b Fa Fb).
unfold fast_two_sum. cbv zeta. simpl fst. simpl snd.
match goal with |- context [round _ _ _ (?s - a)] =>
  replace (s - a) with (- (a - s)) by ring end.
rewrite (round_N_opp_sym (Z.min emin 0) prec tie_even tie_even_sym).
match goal with |- context [b - - ?X] => replace (b - - X) with (b + X) by ring end.
apply Fast2Sum_correct; try lia; auto using tie_even_sym;
  now apply format_emin_le with emin.
Qed.

(** * TwoProd *)

(* The defect of TwoProd. For a and b with prec significant bits (not necessarily
   multiples of eta: the format without underflow), p = RN (a b) and e = RN (a b - p)
   satisfy |p + e - a b| <= eta / 2.
   Proof: r = a b - p is the rounding error of the product. If the product is in the
   normal range then r has at most prec significant bits, so either r is a number of F
   and e = r, or |r| is below the normal range, where rounding moves a number by at most
   eta/2. If the product is below the normal range then |r| <= eta/2 and the same
   applies. *)
Lemma two_prod_defect :
  forall choice a b,
  generic_format radix2 (FLX_exp prec) a -> generic_format radix2 (FLX_exp prec) b ->
  let p := round radix2 fexp (Znearest choice) (a * b) in
  let e := round radix2 fexp (Znearest choice) (a * b - p) in
  Rabs (p + e - a * b) <= / 2 * pow2 emin.
Proof.
intros choice a b Fa Fb p e.
set (r := a * b - p).
replace (p + e - a * b) with (e - r) by (unfold r; ring).
unfold e. fold r.
assert (Hsmall : Rabs r < pow2 (emin + prec) ->
  Rabs (round radix2 fexp (Znearest choice) r - r) <= / 2 * pow2 emin).
{ intros Hr. rewrite <- (ulp_FLT_small radix2 emin prec r Hr).
  apply error_le_half_ulp; auto with typeclass_instances. }
destruct (Rle_or_lt (pow2 (emin + prec - 1)) (Rabs (a * b))) as [Hab|Hab].
- (* the product is in the normal range *)
  assert (Fr : generic_format radix2 (FLX_exp prec) r).
  { unfold r, p. rewrite round_FLT_FLX by exact Hab.
    replace (a * b - round radix2 (FLX_exp prec) (Znearest choice) (a * b))
      with (- (round radix2 (FLX_exp prec) (Znearest choice) (a * b) - a * b)) by ring.
    apply generic_format_opp. apply mult_error_FLX; auto with typeclass_instances. }
  destruct (Rle_or_lt (pow2 (emin + prec - 1)) (Rabs r)) as [Hr|Hr].
  + rewrite round_generic; auto with typeclass_instances.
    * unfold Rminus. rewrite Rplus_opp_r, Rabs_R0.
      apply Rmult_le_pos. lra. apply bpow_ge_0.
    * now apply generic_format_FLT_FLX.
  + apply Hsmall. apply Rlt_trans with (1 := Hr). apply bpow_lt. lia.
- (* the product is below the normal range *)
  apply Hsmall.
  apply Rle_lt_trans with (/ 2 * pow2 emin).
  + unfold r. rewrite <- Rabs_Ropp, Ropp_minus_distr.
    rewrite <- (ulp_FLT_small radix2 emin prec (a * b)).
    * apply error_le_half_ulp; auto with typeclass_instances.
    * apply Rlt_trans with (1 := Hab). apply bpow_lt. lia.
  + apply Rlt_le_trans with (pow2 emin).
    * generalize (bpow_gt_0 radix2 emin). lra.
    * apply bpow_le. generalize prec_gt_0_. unfold Prec_gt_0. lia.
Qed.

(* TwoProd as emitted (the product is an FMA with a zero addend). *)
Lemma two_prod_exact :
  forall a b, format a -> format b ->
  let p := fst (two_prod emin prec tie_even a b) in
  let e := snd (two_prod emin prec tie_even a b) in
  p = rnd (a * b) /\
  Rabs (p + e - a * b) <= / 2 * pow2 emin /\
  (a * b = 0 \/ pow2 (2 * prec - 1) * pow2 emin <= Rabs (a * b) -> p + e = a * b).
Proof.
intros a b Fa Fb. unfold two_prod. cbv zeta. simpl fst. simpl snd.
rewrite Rplus_0_r. split; [reflexivity|split].
- apply (two_prod_defect tie_even a b); now apply generic_format_FLX_FLT with emin.
- intros H.
  assert (F : format (rnd (a * b) - a * b)).
  { apply mult_error_FLT; auto with typeclass_instances.
    intros Hn. destruct H as [H|H]. now elim Hn.
    rewrite <- bpow_plus in H. replace (emin + 2 * prec - 1)%Z with (2 * prec - 1 + emin)%Z by ring.
    exact H. }
  replace (a * b + - rnd (a * b)) with (- (rnd (a * b) - a * b)) by ring.
  rewrite (round_generic radix2 fexp (Znearest tie_even) (- (rnd (a * b) - a * b))).
  ring. now apply generic_format_opp.
Qed.

End EFT.

(** * The statements of SpecDraft.v *)

Theorem two_sum_correct : two_sum_spec.
Proof.
intros emin prec Hp a b Fa Fb.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
generalize (two_sum_exact emin prec Hp a b Fa Fb).
destruct (two_sum emin prec tie_even a b) as [s e]. exact (fun H => H).
Qed.

Theorem fast_two_sum_correct : fast_two_sum_spec.
Proof.
intros emin prec Hp a b Fa Fb Hab.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
generalize (fast_two_sum_exact emin prec Hp a b Fa Fb Hab).
assert (Fs : fmt emin prec (fst (fast_two_sum emin prec tie_even a b))).
{ apply generic_format_round; auto with typeclass_instances. }
assert (Fe : fmt emin prec (snd (fast_two_sum emin prec tie_even a b))).
{ apply generic_format_round; auto with typeclass_instances. }
destruct (fast_two_sum emin prec tie_even a b) as [s e]. simpl fst in *. simpl snd in *.
intros [Hs He]. repeat split; trivial.
rewrite He. exact Hs.
Qed.

Theorem two_prod_correct : two_prod_spec.
Proof.
intros emin prec Hp a b Fa Fb.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
generalize (two_prod_exact emin prec a b Fa Fb).
destruct (two_prod emin prec tie_even a b) as [p e]. cbn [fst snd].
intros [H1 [H2 H3]]. repeat split; trivial.
unfold eta. lra.
Qed.

(* Fast2Sum again, in the form used by the proofs of the 2-limb kernels. *)
Lemma fast_two_sum_norm :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall a b : R, fmt emin prec a -> fmt emin prec b -> Rabs b <= Rabs a ->
  normalized_2 emin prec (fst (fast_two_sum emin prec tie_even a b))
                         (snd (fast_two_sum emin prec tie_even a b)) /\
  fst (fast_two_sum emin prec tie_even a b) + snd (fast_two_sum emin prec tie_even a b) = a + b.
Proof.
intros emin prec Hp a b Fa Fb Hab.
generalize (fast_two_sum_correct emin prec Hp a b Fa Fb Hab).
destruct (fast_two_sum emin prec tie_even a b) as [s e]. cbn [fst snd].
intros [_ [H1 H2]]. now split.
Qed.
