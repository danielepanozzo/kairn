(* EXPERIMENTAL PROOF PROBE, not part of the library: the facts on which the sum of the
   experimental two-limb interval rounded upward rests
   (experiments/upward2/include/kairn/experimental/upward2.hpp, "the header" below).

   The model is the library's real-number model (proofs/theories/Format.v): numbers of the
   format F of precision prec, with gradual underflow below 2^emin and NO overflow (no largest
   number, no infinity, no NaN). RU is the rounding toward plus infinity of that format,
   Flocq's round radix2 (FLT_exp emin prec) Zceil. Every operation of the header is one
   rounding RU of the exact result (the rounding mode is upward); a negation is exact.

   Vocabulary (the brief's):
   - (h, l) is an upper pair of a real v when h + l >= v;
   - (h, l) is upper-normalized when h = RU(h + l); for h in F this is the same as
     l <= 0 and h + l > pred(h) (upper_normalized_iff).

   The definitions transcribe the header operation for operation, on one lane (every
   operation of a register of two lanes acts on each lane separately):
   - add_up, sub_up: add, sub (lines 118-119 for SSE, 162-163 NEON, 211-212 numbers);
   - Rmin, Rmax: vmin, vmax (lines 122-123, 166-167, 215-216: for numbers that are not
     NaN these are the minimum and the maximum, whatever operand order the instruction uses
     on equal operands, since equal reals are the same real);
   - two_sum: lines 319-325;   fast_two_sum: lines 330-334;   two_sum_nonpos: line 342;
   - add_r: lines 561-569, the sum kernel of the type (the form "accurate"), without its
     call of sum_specials (lines 557-560 and 567): that call changes the result only when
     a head is +inf or has magnitude at least the largest finite number, which the model,
     with no overflow, does not have;
   - add_lean: lines 197-205 of upward2_forms.hpp (the form "lean"), likewise;
   - add_num_lane: one lane of add_num_r, lines 578-591, for a finite number t (lane 0
     adds t, lane 1 adds -t), without its special cases (lines 584-589).

   What is proved, for every precision prec >= 1 and every emin (no other hypothesis):
   1. fast2sum_first_exact: for a, b in F with |b| <= |a| and ANY rounding o of Flocq
      (Valid_rnd: RU, RD, RZ, RN with any tie rule), o(a + b) - a is in F. This is the
      exactness of the first two operations of Fast2Sum in a directed mode; the header
      takes it from the literature. Gradual underflow is included.
   2. two_sum: s + t >= a + b for all reals a, b (two_sum_upper); for a, b in F,
      t = RU(a + b - s) (two_sum_error), and (s, t) is upper-normalized for every b in F
      and every real a (two_sum_normalized).
   3. fast_two_sum: s + t >= a + b always (fast_two_sum_upper); (s, t) is upper-normalized
      for every b in F and every real a, WITHOUT any order between a and b
      (fast_two_sum_normalized); with |b| <= |a|, t = RU(a + b - s) (fast_two_sum_error).
      two_sum_nonpos: the same with s = RU(a + b), and t = RU(a + b - s) for a, b <= 0.
   4. add_r (and add_lean): the result is an upper pair of (xh + xl) + (yh + yl) and is
      upper-normalized, for ALL real inputs (add_r_upper, add_r_normalized,
      add_lean_upper, add_lean_normalized); add_r_correct states it in the brief's words,
      for upper-normalized inputs of F.

   Why normalization needs no order of the operands (the point that the header's comments
   do not make): with s = RU(a + b) >= a + b, the number a - s is at most -b, which is in F,
   so RU(a - s) <= -b and then t = RU(RU(a - s) + b) <= RU(0) = 0; and every rounding up
   only increases, so t >= a + b - s. Hence s + t lies between a + b and s = RU(a + b),
   and so RU(s + t) = s. The exactness of a - s (item 1) is needed only for the equality
   t = RU(a + b - s), that is for t to be the SMALLEST upper bound of the error. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core Plus_error Mult_error Sterbenz.
From Kairn Require Import Format.
Open Scope R_scope.

Section Model.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation RU := (round radix2 fexp Zceil).
Notation pred := (pred radix2 fexp).

(** * The vocabulary of the brief *)

Definition upper_pair (v h l : R) : Prop := v <= h + l.
Definition upper_normalized (h l : R) : Prop := h = RU (h + l).

Definition add_up (a b : R) : R := RU (a + b).
Definition sub_up (a b : R) : R := RU (a - b).

(** * Rounding upward: the facts used below *)

Lemma RU_fmt : forall x, format (RU x).
Proof. intros x. apply generic_format_round; auto with typeclass_instances. Qed.

Lemma RU_ge : forall x, x <= RU x.
Proof. intros x. destruct (round_UP_pt radix2 fexp x) as [_ [H _]]. exact H. Qed.

(* RU(x) is the least number of F that is at least x. *)
Lemma RU_least : forall x g, format g -> x <= g -> RU x <= g.
Proof. intros x g Fg H. apply round_le_generic; auto with typeclass_instances. Qed.

Lemma RU_id : forall x, format x -> RU x = x.
Proof. intros x Fx. apply round_generic; auto with typeclass_instances. Qed.

Lemma RU_le : forall x y, x <= y -> RU x <= RU y.
Proof. intros x y H. apply round_le; auto with typeclass_instances. Qed.

Lemma RU_nonpos : forall x, x <= 0 -> RU x <= 0.
Proof. intros x H. apply RU_least; [apply generic_format_0 | exact H]. Qed.

(* Anything between x and RU(x) rounds up to RU(x). *)
Lemma RU_sandwich : forall x y, x <= y -> y <= RU x -> RU y = RU x.
Proof.
intros x y H1 H2. apply Rle_antisym.
- apply RU_least; [apply RU_fmt | exact H2].
- apply RU_le. exact H1.
Qed.

(* pred(h) < h for every h, zero included (the library's Convert.pred_FLT_lt, repeated here
   so that this file needs only Format.v). *)
Lemma pred_lt : forall h, pred h < h.
Proof.
intros h. destruct (Req_dec h 0) as [Zh|Zh].
- rewrite Zh, (pred_0 radix2 fexp), (ulp_FLT_0 radix2 emin prec).
  generalize (bpow_gt_0 radix2 emin). lra.
- exact (pred_lt_id radix2 fexp h Zh).
Qed.

(* The brief's reading of upper-normalized: l <= 0 and h + l > pred(h). *)
Theorem upper_normalized_iff : forall h l, format h ->
  upper_normalized h l <-> (l <= 0 /\ pred h < h + l).
Proof.
intros h l Fh. unfold upper_normalized. split.
- intros E. split.
  + generalize (RU_ge (h + l)). rewrite <- E. lra.
  + destruct (Rlt_or_le (pred h) (h + l)) as [H|H]; trivial. exfalso.
    assert (K : RU (h + l) <= pred h).
    { apply RU_least; [apply generic_format_pred; auto with typeclass_instances | exact H]. }
    rewrite <- E in K. generalize (pred_lt h). lra.
- intros [H1 H2]. symmetry. apply round_UP_eq; auto with typeclass_instances. split; lra.
Qed.

(* A pair whose second limb is between the error x - s of s = RU(x) and 0 is
   upper-normalized. *)
Lemma normalized_of_bounds : forall x s t,
  s = RU x -> x - s <= t -> t <= 0 -> upper_normalized s t.
Proof.
intros x s t Hs H1 H2. unfold upper_normalized.
rewrite (RU_sandwich x (s + t)); [exact Hs | lra | rewrite <- Hs; lra].
Qed.

(** * The first two operations of Fast2Sum are exact in every rounding mode *)

Section AnyRounding.
Variable rnd : R -> Z.
Context {valid_rnd_ : Valid_rnd rnd}.
Notation rd := (round radix2 fexp rnd).

(* The case a > 0. Three cases: b >= 0 (then a <= rd(a + b) <= 2a); b < 0 with
   |b| >= a/2 (Sterbenz: a + b is exact); b < 0 with |b| < a/2 (then a + b is exact when
   it is below 2^(emin + prec), and otherwise a is normal, a/2 is in F and
   a/2 <= rd(a + b) <= a). In the first and the last case, rd(a + b) - a is a sum of two
   numbers of F whose magnitude is at most the power of two below the smaller of their
   magnitudes, which Flocq's generic_format_plus says is exact. *)
Lemma fast2sum_first_exact_pos :
  forall a b, format a -> format b -> 0 < a -> Rabs b <= a ->
  format (rd (a + b) - a).
Proof.
intros a b Fa Fb Ha Hab.
assert (Fma : format (- a)) by now apply generic_format_opp.
assert (Ma : Rabs a < bpow radix2 (mag radix2 a)) by apply bpow_mag_gt.
rewrite Rabs_pos_eq in Ma by lra.
assert (Frd : format (rd (a + b))) by (apply generic_format_round; auto with typeclass_instances).
destruct (Rle_or_lt 0 b) as [Hb|Hb].
- (* b >= 0: a <= a + b <= 2 a *)
  rewrite Rabs_pos_eq in Hab by exact Hb.
  assert (F2 : format (a * bpow radix2 1)).
  { apply mult_bpow_pos_exact_FLT; [exact Fa | lia]. }
  rewrite pow2_1 in F2.
  assert (L : a <= rd (a + b)).
  { apply round_ge_generic; auto with typeclass_instances. lra. }
  assert (U : rd (a + b) <= a * 2).
  { apply round_le_generic; auto with typeclass_instances. lra. }
  unfold Rminus. apply generic_format_plus; auto with typeclass_instances.
  rewrite mag_opp.
  assert (M : (mag radix2 a <= mag radix2 (rd (a + b)))%Z) by (apply mag_le; lra).
  rewrite Z.min_r by exact M.
  rewrite Rabs_pos_eq by lra. lra.
- (* b < 0 *)
  rewrite Rabs_left in Hab by exact Hb.
  destruct (Rle_or_lt a (2 * - b)) as [Hs|Hs].
  + (* Sterbenz: a + b is exact *)
    assert (Fs : format (a + b)).
    { replace (a + b) with (a - - b) by ring. apply sterbenz; auto with typeclass_instances.
      - now apply generic_format_opp.
      - lra. }
    rewrite round_generic by auto with typeclass_instances.
    replace (a + b - a) with b by ring. exact Fb.
  + destruct (Rle_or_lt (a + b) (bpow radix2 (prec + emin))) as [Hsm|Hbig].
    * (* a + b is below 2^(emin + prec): exact *)
      assert (Fs : format (a + b)).
      { apply FLT_format_plus_small; trivial. rewrite Rabs_pos_eq by lra. exact Hsm. }
      rewrite round_generic by auto with typeclass_instances.
      replace (a + b - a) with b by ring. exact Fb.
    * (* a is normal, so a / 2 is in F, and a / 2 < a + b < a *)
      assert (Mg : (prec + emin + 1 <= mag radix2 a)%Z).
      { apply mag_ge_bpow. replace (prec + emin + 1 - 1)%Z with (prec + emin)%Z by ring.
        rewrite Rabs_pos_eq by lra. lra. }
      assert (Fh : format (a * bpow radix2 (-1))).
      { apply mult_bpow_exact_FLT; [exact Fa | lia]. }
      assert (Mh : (mag radix2 (a * bpow radix2 (-1)) = mag radix2 a + -1 :> Z)%Z).
      { apply mag_mult_bpow. lra. }
      rewrite pow2_m1 in Fh, Mh.
      assert (L : a * / 2 <= rd (a + b)).
      { apply round_ge_generic; auto with typeclass_instances. lra. }
      assert (U : rd (a + b) <= a).
      { apply round_le_generic; auto with typeclass_instances. lra. }
      assert (M : (mag radix2 a - 1 <= mag radix2 (rd (a + b)))%Z).
      { assert (M' : (mag radix2 (a * / 2) <= mag radix2 (rd (a + b)))%Z).
        { apply mag_le; lra. }
        lia. }
      unfold Rminus. apply generic_format_plus; auto with typeclass_instances.
      rewrite mag_opp.
      apply Rle_trans with (bpow radix2 (mag radix2 a - 1)).
      -- rewrite Rabs_left1 by lra.
         replace (mag radix2 a - 1)%Z with (mag radix2 a + -1)%Z by ring.
         rewrite bpow_plus, pow2_m1. lra.
      -- apply bpow_le. lia.
Qed.

End AnyRounding.

(* The fact the header takes from the literature, for every rounding of Flocq (in
   particular RU, and RD, which is what a negative a amounts to under RU): if a and b are
   numbers of F with |b| <= |a|, then o(a + b) - a is a number of F. Underflow included,
   every precision. *)
Theorem fast2sum_first_exact (rnd : R -> Z) {Hr : Valid_rnd rnd} :
  forall a b, format a -> format b -> Rabs b <= Rabs a ->
  format (round radix2 fexp rnd (a + b) - a).
Proof.
intros a b Fa Fb Hab.
destruct (Rtotal_order a 0) as [Ha|[Ha|Ha]].
- replace (a + b) with (- (- a + - b)) by ring. rewrite round_opp.
  replace (- round radix2 fexp (Zrnd_opp rnd) (- a + - b) - a)
    with (- (round radix2 fexp (Zrnd_opp rnd) (- a + - b) - - a)) by ring.
  apply generic_format_opp. apply (fast2sum_first_exact_pos (Zrnd_opp rnd)).
  + now apply generic_format_opp.
  + now apply generic_format_opp.
  + lra.
  + rewrite Rabs_Ropp. rewrite (Rabs_left a) in Hab by exact Ha. exact Hab.
- subst a. rewrite Rabs_R0 in Hab.
  assert (Hb : b = 0).
  { destruct (Req_dec b 0) as [Hb|Hb]; trivial. generalize (Rabs_pos_lt b Hb). lra. }
  subst b. rewrite Rplus_0_r, round_0, Rminus_0_r by auto with typeclass_instances.
  apply generic_format_0.
- apply fast2sum_first_exact_pos; trivial. rewrite (Rabs_pos_eq a) in Hab by lra. exact Hab.
Qed.

(* So the second operation of Fast2Sum rounded up is exact. *)
Corollary sub_up_exact : forall a b, format a -> format b -> Rabs b <= Rabs a ->
  sub_up a (add_up a b) = a - add_up a b.
Proof.
intros a b Fa Fb H. unfold sub_up. apply RU_id.
replace (a - add_up a b) with (- (RU (a + b) - a)) by (unfold add_up; ring).
apply generic_format_opp. apply (fast2sum_first_exact Zceil); trivial.
Qed.

(** * The candidates of the error: always upper bounds of it, never positive *)

(* RU(RU(a - s) + b) >= a + b - s, for all reals. *)
Lemma candidate_ge : forall a b s, a + b - s <= add_up (sub_up a s) b.
Proof.
intros a b s. unfold add_up, sub_up.
generalize (RU_ge (a - s)) (RU_ge (RU (a - s) + b)). lra.
Qed.

(* RU(RU(a - s) + b) <= 0 whenever s >= a + b and b is in F: a - s <= -b, a number of F,
   so RU(a - s) <= -b. *)
Lemma candidate_nonpos : forall a b s, format b -> a + b <= s ->
  add_up (sub_up a s) b <= 0.
Proof.
intros a b s Fb H. unfold add_up. apply RU_nonpos.
assert (K : sub_up a s <= - b).
{ unfold sub_up. apply RU_least; [now apply generic_format_opp | lra]. }
lra.
Qed.

Lemma Rmin_format : forall x y, format x -> format y -> format (Rmin x y).
Proof. intros x y Fx Fy. unfold Rmin. destruct (Rle_dec x y); assumption. Qed.

(** * two_sum (header lines 319-325) *)

Definition two_sum (a b : R) : R * R :=
  let s := add_up a b in
  let t1 := add_up (sub_up a s) b in
  let t2 := add_up (sub_up b s) a in
  (s, Rmin t1 t2).

Lemma two_sum_fst : forall a b, fst (two_sum a b) = RU (a + b).
Proof. reflexivity. Qed.

Lemma two_sum_format : forall a b,
  format (fst (two_sum a b)) /\ format (snd (two_sum a b)).
Proof.
intros a b. unfold two_sum; cbn [fst snd]. unfold add_up. split.
- apply RU_fmt.
- apply Rmin_format; apply RU_fmt.
Qed.

Theorem two_sum_upper : forall a b,
  upper_pair (a + b) (fst (two_sum a b)) (snd (two_sum a b)).
Proof.
intros a b. unfold upper_pair, two_sum; cbn [fst snd].
generalize (candidate_ge a b (add_up a b)) (candidate_ge b a (add_up a b)). intros H1 H2.
assert (H : a + b - add_up a b <=
            Rmin (add_up (sub_up a (add_up a b)) b) (add_up (sub_up b (add_up a b)) a)).
{ apply Rmin_glb; lra. }
lra.
Qed.

Theorem two_sum_error : forall a b, format a -> format b ->
  snd (two_sum a b) = RU (a + b - fst (two_sum a b)).
Proof.
intros a b Fa Fb. unfold two_sum; cbn [fst snd].
set (s := add_up a b).
assert (G1 : RU (a + b - s) <= add_up (sub_up a s) b).
{ apply RU_least; [unfold add_up; apply RU_fmt | apply candidate_ge]. }
assert (G2 : RU (a + b - s) <= add_up (sub_up b s) a).
{ apply RU_least; [unfold add_up; apply RU_fmt | generalize (candidate_ge b a s); lra]. }
destruct (Rle_or_lt (Rabs b) (Rabs a)) as [H|H].
- assert (E : add_up (sub_up a s) b = RU (a + b - s)).
  { unfold s. rewrite sub_up_exact by trivial. unfold add_up at 1. f_equal. ring. }
  rewrite E. apply Rmin_left. exact G2.
- assert (E : add_up (sub_up b s) a = RU (a + b - s)).
  { assert (Es : s = add_up b a) by (unfold s, add_up; f_equal; ring).
    rewrite Es. rewrite sub_up_exact by (trivial || lra). unfold add_up at 1. f_equal. ring. }
  rewrite E. apply Rmin_right. exact G1.
Qed.

(* Normalized for every b in F: t <= t1 <= 0 (candidate_nonpos). Item 1 is not needed. *)
Theorem two_sum_normalized : forall a b, format b ->
  upper_normalized (fst (two_sum a b)) (snd (two_sum a b)).
Proof.
intros a b Fb.
apply normalized_of_bounds with (a + b).
- reflexivity.
- generalize (two_sum_upper a b). unfold upper_pair. lra.
- unfold two_sum; cbn [fst snd].
  apply Rle_trans with (add_up (sub_up a (add_up a b)) b).
  + apply Rmin_l.
  + apply candidate_nonpos; [exact Fb | unfold add_up; apply RU_ge].
Qed.

(** * fast_two_sum (header lines 330-334) and two_sum_nonpos (line 342) *)

Definition fast_two_sum (a b : R) : R * R :=
  let s := add_up a b in
  (s, add_up (sub_up a s) b).

Lemma fast_two_sum_fst : forall a b, fst (fast_two_sum a b) = RU (a + b).
Proof. reflexivity. Qed.

Lemma fast_two_sum_format : forall a b,
  format (fst (fast_two_sum a b)) /\ format (snd (fast_two_sum a b)).
Proof. intros a b. unfold fast_two_sum, add_up; cbn [fst snd]. split; apply RU_fmt. Qed.

Theorem fast_two_sum_upper : forall a b,
  upper_pair (a + b) (fst (fast_two_sum a b)) (snd (fast_two_sum a b)).
Proof.
intros a b. unfold upper_pair, fast_two_sum; cbn [fst snd].
generalize (candidate_ge a b (add_up a b)). lra.
Qed.

(* Upper-normalized for every real a and every b in F, in either order of magnitude. *)
Theorem fast_two_sum_normalized : forall a b, format b ->
  upper_normalized (fst (fast_two_sum a b)) (snd (fast_two_sum a b)).
Proof.
intros a b Fb. unfold fast_two_sum; cbn [fst snd].
apply normalized_of_bounds with (a + b).
- reflexivity.
- apply candidate_ge.
- apply candidate_nonpos; [exact Fb | unfold add_up; apply RU_ge].
Qed.

(* With |b| <= |a|, the second limb is the error rounded up, the least upper bound of it
   in F. *)
Theorem fast_two_sum_error : forall a b, format a -> format b -> Rabs b <= Rabs a ->
  snd (fast_two_sum a b) = RU (a + b - fst (fast_two_sum a b)).
Proof.
intros a b Fa Fb H. unfold fast_two_sum; cbn [fst snd].
rewrite sub_up_exact by trivial. unfold add_up at 1. f_equal. ring.
Qed.

Definition two_sum_nonpos (a b : R) : R * R := fast_two_sum (Rmin a b) (Rmax a b).

Lemma Rmin_Rmax_sum : forall a b, Rmin a b + Rmax a b = a + b.
Proof. intros a b. unfold Rmin, Rmax. destruct (Rle_dec a b); ring. Qed.

Lemma two_sum_nonpos_fst : forall a b, fst (two_sum_nonpos a b) = RU (a + b).
Proof.
intros a b. unfold two_sum_nonpos. rewrite fast_two_sum_fst. now rewrite Rmin_Rmax_sum.
Qed.

Lemma two_sum_nonpos_format : forall a b,
  format (fst (two_sum_nonpos a b)) /\ format (snd (two_sum_nonpos a b)).
Proof. intros a b. apply fast_two_sum_format. Qed.

Theorem two_sum_nonpos_upper : forall a b,
  upper_pair (a + b) (fst (two_sum_nonpos a b)) (snd (two_sum_nonpos a b)).
Proof.
intros a b. unfold two_sum_nonpos. rewrite <- (Rmin_Rmax_sum a b). apply fast_two_sum_upper.
Qed.

Theorem two_sum_nonpos_normalized : forall a b, format a -> format b ->
  upper_normalized (fst (two_sum_nonpos a b)) (snd (two_sum_nonpos a b)).
Proof.
intros a b Fa Fb. unfold two_sum_nonpos. apply fast_two_sum_normalized.
unfold Rmax. destruct (Rle_dec a b); assumption.
Qed.

Theorem two_sum_nonpos_error : forall a b, format a -> format b -> a <= 0 -> b <= 0 ->
  snd (two_sum_nonpos a b) = RU (a + b - fst (two_sum_nonpos a b)).
Proof.
intros a b Fa Fb Ha Hb. unfold two_sum_nonpos. rewrite <- (Rmin_Rmax_sum a b).
apply fast_two_sum_error.
- unfold Rmin. destruct (Rle_dec a b); assumption.
- unfold Rmax. destruct (Rle_dec a b); assumption.
- unfold Rmin, Rmax. destruct (Rle_dec a b) as [H|H].
  + rewrite 2!Rabs_left1 by lra. lra.
  + apply Rnot_le_lt in H. rewrite 2!Rabs_left1 by lra. lra.
Qed.

(** * The sum kernel of the type, the form "accurate" (header lines 561-569) *)

Definition add_r (xh xl yh yl : R) : R * R :=
  let '(s, e) := two_sum xh yh in
  let '(t, f) := two_sum_nonpos xl yl in
  let '(v, g) := two_sum s (add_up e t) in
  two_sum v (add_up f g).

(* An upper pair of the exact sum, for all real inputs: each line replaces a term by a
   number at least it. *)
Theorem add_r_upper : forall xh xl yh yl,
  upper_pair ((xh + xl) + (yh + yl)) (fst (add_r xh xl yh yl)) (snd (add_r xh xl yh yl)).
Proof.
intros xh xl yh yl. unfold add_r.
generalize (two_sum_upper xh yh). destruct (two_sum xh yh) as [s e].
unfold upper_pair; cbn [fst snd]. intros H1.
generalize (two_sum_nonpos_upper xl yl). destruct (two_sum_nonpos xl yl) as [t f].
unfold upper_pair; cbn [fst snd]. intros H2.
generalize (two_sum_upper s (add_up e t)). destruct (two_sum s (add_up e t)) as [v g].
unfold upper_pair; cbn [fst snd]. intros H3.
generalize (two_sum_upper v (add_up f g)). unfold upper_pair. intros H4.
generalize (RU_ge (e + t)) (RU_ge (f + g)). unfold add_up in *. lra.
Qed.

(* Upper-normalized for all real inputs: the last two-sum's second operand is a rounded
   number, so two_sum_normalized applies. *)
Theorem add_r_normalized : forall xh xl yh yl,
  upper_normalized (fst (add_r xh xl yh yl)) (snd (add_r xh xl yh yl)).
Proof.
intros xh xl yh yl. unfold add_r.
destruct (two_sum xh yh) as [s e]. destruct (two_sum_nonpos xl yl) as [t f].
destruct (two_sum s (add_up e t)) as [v g].
apply two_sum_normalized. unfold add_up. apply RU_fmt.
Qed.

Lemma add_r_format : forall xh xl yh yl,
  format (fst (add_r xh xl yh yl)) /\ format (snd (add_r xh xl yh yl)).
Proof.
intros xh xl yh yl. unfold add_r.
destruct (two_sum xh yh) as [s e]. destruct (two_sum_nonpos xl yl) as [t f].
destruct (two_sum s (add_up e t)) as [v g].
apply two_sum_format.
Qed.

(* Statement 3 of the brief, in its words: for two upper-normalized pairs of numbers of F,
   the result is a pair of numbers of F, an upper pair of the exact sum, and
   upper-normalized. (The hypotheses on the inputs are not used: add_r_upper and
   add_r_normalized hold for all real inputs.) *)
Theorem add_r_correct : forall xh xl yh yl,
  format xh -> format xl -> format yh -> format yl ->
  upper_normalized xh xl -> upper_normalized yh yl ->
  format (fst (add_r xh xl yh yl)) /\ format (snd (add_r xh xl yh yl)) /\
  upper_pair ((xh + xl) + (yh + yl)) (fst (add_r xh xl yh yl)) (snd (add_r xh xl yh yl)) /\
  upper_normalized (fst (add_r xh xl yh yl)) (snd (add_r xh xl yh yl)).
Proof.
intros xh xl yh yl _ _ _ _ _ _.
destruct (add_r_format xh xl yh yl) as [F1 F2].
split; [exact F1 | split; [exact F2 | split]].
- apply add_r_upper.
- apply add_r_normalized.
Qed.

(** * The form "lean" (upward2_forms.hpp lines 197-205) *)

Definition add_lean (xh xl yh yl : R) : R * R :=
  let '(s, e) := two_sum xh yh in
  let '(t, f) := two_sum_nonpos xl yl in
  let '(v, g) := fast_two_sum s (add_up e t) in
  fast_two_sum v (add_up f g).

Theorem add_lean_upper : forall xh xl yh yl,
  upper_pair ((xh + xl) + (yh + yl)) (fst (add_lean xh xl yh yl)) (snd (add_lean xh xl yh yl)).
Proof.
intros xh xl yh yl. unfold add_lean.
generalize (two_sum_upper xh yh). destruct (two_sum xh yh) as [s e].
unfold upper_pair; cbn [fst snd]. intros H1.
generalize (two_sum_nonpos_upper xl yl). destruct (two_sum_nonpos xl yl) as [t f].
unfold upper_pair; cbn [fst snd]. intros H2.
generalize (fast_two_sum_upper s (add_up e t)). destruct (fast_two_sum s (add_up e t)) as [v g].
unfold upper_pair; cbn [fst snd]. intros H3.
generalize (fast_two_sum_upper v (add_up f g)). unfold upper_pair. intros H4.
generalize (RU_ge (e + t)) (RU_ge (f + g)). unfold add_up in *. lra.
Qed.

(* The form "lean" keeps the normalization, for all real inputs (the header says this is
   only tested): fast_two_sum is upper-normalized in either order of its operands. *)
Theorem add_lean_normalized : forall xh xl yh yl,
  upper_normalized (fst (add_lean xh xl yh yl)) (snd (add_lean xh xl yh yl)).
Proof.
intros xh xl yh yl. unfold add_lean.
destruct (two_sum xh yh) as [s e]. destruct (two_sum_nonpos xl yl) as [t f].
destruct (fast_two_sum s (add_up e t)) as [v g].
apply fast_two_sum_normalized. unfold add_up. apply RU_fmt.
Qed.

(** * One lane of the sum with a number (header lines 578-591, t finite) *)

(* Lane 0 is add_num_lane uh ul t, lane 1 add_num_lane nh nl (- t). *)
Definition add_num_lane (h l t : R) : R * R :=
  let '(s, e) := two_sum h t in
  two_sum s (add_up e l).

Theorem add_num_lane_upper : forall h l t,
  upper_pair ((h + l) + t) (fst (add_num_lane h l t)) (snd (add_num_lane h l t)).
Proof.
intros h l t. unfold add_num_lane.
generalize (two_sum_upper h t). destruct (two_sum h t) as [s e].
unfold upper_pair; cbn [fst snd]. intros H1.
generalize (two_sum_upper s (add_up e l)). unfold upper_pair. intros H2.
generalize (RU_ge (e + l)). unfold add_up in *. lra.
Qed.

Theorem add_num_lane_normalized : forall h l t,
  upper_normalized (fst (add_num_lane h l t)) (snd (add_num_lane h l t)).
Proof.
intros h l t. unfold add_num_lane. destruct (two_sum h t) as [s e].
apply two_sum_normalized. unfold add_up. apply RU_fmt.
Qed.

End Model.

(* The assumptions of every main theorem: only the standard library's axioms of the real
   numbers (and of classical logic) may appear. *)
Print Assumptions upper_normalized_iff.
Print Assumptions fast2sum_first_exact.
Print Assumptions sub_up_exact.
Print Assumptions two_sum_upper.
Print Assumptions two_sum_error.
Print Assumptions two_sum_normalized.
Print Assumptions fast_two_sum_upper.
Print Assumptions fast_two_sum_normalized.
Print Assumptions fast_two_sum_error.
Print Assumptions two_sum_nonpos_upper.
Print Assumptions two_sum_nonpos_normalized.
Print Assumptions two_sum_nonpos_error.
Print Assumptions add_r_upper.
Print Assumptions add_r_normalized.
Print Assumptions add_r_correct.
Print Assumptions add_lean_upper.
Print Assumptions add_lean_normalized.
Print Assumptions add_num_lane_upper.
Print Assumptions add_num_lane_normalized.
