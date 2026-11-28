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

   What is proved, for every precision prec >= 1 and every emin (items 1 to 5; item 6 needs
   prec >= 6):
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
   5. two_sum_nonpos_exact: for a, b <= 0 in F, s + t = a + b exactly (the error of a sum
      rounded toward zero of two numbers of the same sign is a number of F).
   6. add_r_excess (the brief's stretch goal), for prec >= 6 and upper-normalized inputs
      of F, with x + y the exact sum, u = 2^-prec and eta = 2^emin:
        zh + zl - (x + y) <= 64 u^2 |x + y| + 16 eta.
      The constant is not sharp (the checks measured at most 6 u^2); the proof bounds each
      rounding by one step of the format and splits on Sterbenz's lemma twice: either the
      heads' sum is exact (then the first, second and third errors vanish), or the heads
      do not cancel (|xh| + |yh| <= 3 |xh + yh|).

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

(** * The arithmetic of the excess bound (statement 4), on real numbers only *)

(* Here u stands for 2^-prec and eta for 2^emin; the products are written out so that
   lra sees only linear combinations of monomials. The meaning of the variables is given
   at add_r_excess below. All cases: the excess is at most 6 eta + 2 u (a1 + ... + a6),
   which is bounded in terms of X = |xh + yh| and L = |xl + yl|. *)
Lemma excess_master_arith :
  forall u eta X L a1 a2 a3 a4 a5 a6 sg om : R,
  0 < u -> u <= / 64 -> 0 <= eta -> 0 <= X -> 0 <= L ->
  0 <= a1 -> 0 <= a2 -> 0 <= a3 -> 0 <= a4 -> 0 <= a5 -> 0 <= a6 -> 0 <= sg -> 0 <= om ->
  a1 <= eta + 2 * u * X -> a2 <= eta + 2 * u * L -> a3 <= a1 + L ->
  sg <= X + a1 + a3 -> a4 <= eta + 2 * u * sg -> a5 <= a2 + a4 ->
  om <= sg + a4 + a5 -> a6 <= eta + 2 * u * om ->
  6 * eta + 2 * u * (a1 + a2 + a3 + a4 + a5 + a6) <= 22 * (u * u) * X + 3 * u * L + 7 * eta.
Proof.
intros u eta X L a1 a2 a3 a4 a5 a6 sg om Hu Hu64 He HX HL H1 H2 H3 H4 H5 H6 Hsg Hom
  B1 B2 B3 B4 B5 B6 B7 B8.
assert (U0 : 0 <= u) by lra.
assert (UU : 0 <= u * u) by (apply Rmult_le_pos; lra).
assert (PX : u * X <= / 64 * X) by (apply Rmult_le_compat_r; lra).
assert (PL : u * L <= / 64 * L) by (apply Rmult_le_compat_r; lra).
assert (Psg : u * sg <= / 64 * sg) by (apply Rmult_le_compat_r; lra).
assert (Pe : u * eta <= / 64 * eta) by (apply Rmult_le_compat_r; lra).
assert (SG : sg <= 17 / 16 * X + L + 2 * eta) by lra.
assert (A4 : a4 <= eta + / 32 * sg) by lra.
assert (OM : om <= 17 / 16 * sg + 3 * eta + / 32 * L) by lra.
assert (Q1 : u * a1 <= u * (eta + 2 * u * X)) by (apply Rmult_le_compat_l; lra).
assert (Q2 : u * a2 <= u * (eta + 2 * u * L)) by (apply Rmult_le_compat_l; lra).
assert (Q3 : u * a3 <= u * (a1 + L)) by (apply Rmult_le_compat_l; lra).
assert (Q4 : u * a4 <= u * (eta + 2 * u * sg)) by (apply Rmult_le_compat_l; lra).
assert (Q5 : u * a5 <= u * (a2 + a4)) by (apply Rmult_le_compat_l; lra).
assert (Q6 : u * a6 <= u * (eta + 2 * u * om)) by (apply Rmult_le_compat_l; lra).
assert (R1 : u * u * sg <= u * u * (17 / 16 * X + L + 2 * eta)) by (apply Rmult_le_compat_l; lra).
assert (R2 : u * u * om <= u * u * (17 / 16 * sg + 3 * eta + / 32 * L))
  by (apply Rmult_le_compat_l; lra).
assert (S1 : u * u * L <= / 64 * (u * L)).
{ replace (u * u * L) with (u * (u * L)) by ring. apply Rmult_le_compat_r; [|lra].
  apply Rmult_le_pos; lra. }
assert (S2 : u * u * eta <= / 64 * (u * eta)).
{ replace (u * u * eta) with (u * (u * eta)) by ring. apply Rmult_le_compat_r; [|lra].
  apply Rmult_le_pos; lra. }
assert (N1 : 0 <= u * u * X) by (apply Rmult_le_pos; lra).
assert (N2 : 0 <= u * L) by (apply Rmult_le_pos; lra).
assert (N3 : 0 <= u * eta) by (apply Rmult_le_pos; lra).
assert (N4 : 0 <= u * u * eta) by (apply Rmult_le_pos; lra).
assert (N5 : 0 <= u * u * L) by (apply Rmult_le_pos; lra).
assert (N6 : 0 <= u * u * sg) by (apply Rmult_le_pos; lra).
lra.
Qed.

(* The case |xh| + |yh| <= 3 |xh + yh|: then L <= 4 eta + 9 u X, and X <= S + L for
   S = |x + y|. *)
Lemma excess_big_arith :
  forall u eta X L S E : R,
  0 < u -> u <= / 64 -> 0 <= eta -> 0 <= X -> 0 <= L -> 0 <= S ->
  E <= 22 * (u * u) * X + 3 * u * L + 7 * eta ->
  L <= 4 * eta + 9 * u * X -> X <= S + L ->
  E <= 64 * (u * u) * S + 16 * eta.
Proof.
intros u eta X L S E Hu Hu64 He HX HL HS HE HLX HXS.
assert (UU : 0 <= u * u) by (apply Rmult_le_pos; lra).
assert (Q1 : u * L <= u * (4 * eta + 9 * u * X)) by (apply Rmult_le_compat_l; lra).
assert (Q2 : u * u * X <= u * u * (S + 4 * eta + 9 * u * X)) by (apply Rmult_le_compat_l; lra).
assert (S1 : u * (u * u * X) <= / 64 * (u * u * X)).
{ apply Rmult_le_compat_r; [apply Rmult_le_pos; lra | lra]. }
assert (Pe : u * eta <= / 64 * eta) by (apply Rmult_le_compat_r; lra).
assert (S2 : u * u * eta <= / 64 * (u * eta)).
{ replace (u * u * eta) with (u * (u * eta)) by ring. apply Rmult_le_compat_r; [|lra].
  apply Rmult_le_pos; lra. }
assert (N1 : 0 <= u * u * X) by (apply Rmult_le_pos; lra).
assert (N2 : 0 <= u * u * S) by (apply Rmult_le_pos; lra).
assert (N3 : 0 <= u * eta) by (apply Rmult_le_pos; lra).
assert (N4 : 0 <= u * u * eta) by (apply Rmult_le_pos; lra).
lra.
Qed.

(* The case where xh + yh is exact and s + t is not, with P = |s + t| and F = |f|. *)
Lemma excess_exact_heads_arith :
  forall u eta P F S a4 a5 om a6 E : R,
  0 < u -> u <= / 64 -> 0 <= eta -> 0 <= P -> 0 <= F -> 0 <= S ->
  0 <= a4 -> 0 <= a5 -> 0 <= om -> 0 <= a6 ->
  a4 <= eta + 2 * u * P -> F <= eta + 2 * u * (3 * P + F) -> a5 <= F + a4 ->
  om <= P + a4 + a5 -> a6 <= eta + 2 * u * om ->
  E <= 3 * eta + 2 * u * (a4 + a5 + a6) -> P <= S + F ->
  E <= 64 * (u * u) * S + 16 * eta.
Proof.
intros u eta P F S a4 a5 om a6 E Hu Hu64 He HP HF HS H4 H5 H6 H7 B4 BF B5 B6 B7 HE HPS.
assert (UU : 0 <= u * u) by (apply Rmult_le_pos; lra).
assert (PP : u * P <= / 64 * P) by (apply Rmult_le_compat_r; lra).
assert (PF : u * F <= / 64 * F) by (apply Rmult_le_compat_r; lra).
assert (Pe : u * eta <= / 64 * eta) by (apply Rmult_le_compat_r; lra).
assert (Pom : u * om <= / 64 * om) by (apply Rmult_le_compat_r; lra).
assert (F1 : 31 / 32 * F <= eta + 6 * u * P) by lra.
assert (OM : om <= 2 * P + 5 * eta) by lra.
assert (Q4 : u * a4 <= u * (eta + 2 * u * P)) by (apply Rmult_le_compat_l; lra).
assert (Q5 : u * a5 <= u * (F + a4)) by (apply Rmult_le_compat_l; lra).
assert (QF : u * (31 / 32 * F) <= u * (eta + 6 * u * P)) by (apply Rmult_le_compat_l; lra).
assert (Q6 : u * a6 <= u * (eta + 2 * u * om)) by (apply Rmult_le_compat_l; lra).
assert (Qom : u * u * om <= u * u * (P + a4 + a5)) by (apply Rmult_le_compat_l; lra).
assert (Qa4 : u * u * a4 <= u * u * (eta + 2 * u * P)) by (apply Rmult_le_compat_l; lra).
assert (Qa5 : u * u * a5 <= u * u * (F + a4)) by (apply Rmult_le_compat_l; lra).
assert (QF2 : u * u * (31 / 32 * F) <= u * u * (eta + 6 * u * P))
  by (apply Rmult_le_compat_l; lra).
assert (QP : u * u * P <= u * u * (S + F)) by (apply Rmult_le_compat_l; lra).
assert (T1 : u * (u * u * P) <= / 64 * (u * u * P)).
{ apply Rmult_le_compat_r; [apply Rmult_le_pos; lra | lra]. }
assert (T2 : u * u * eta <= / 64 * (u * eta)).
{ replace (u * u * eta) with (u * (u * eta)) by ring. apply Rmult_le_compat_r; [|lra].
  apply Rmult_le_pos; lra. }
assert (T3 : u * (u * u * eta) <= / 64 * (u * u * eta)).
{ apply Rmult_le_compat_r; [apply Rmult_le_pos; lra | lra]. }
assert (N1 : 0 <= u * u * P) by (apply Rmult_le_pos; lra).
assert (N2 : 0 <= u * u * S) by (apply Rmult_le_pos; lra).
assert (N3 : 0 <= u * eta) by (apply Rmult_le_pos; lra).
assert (N4 : 0 <= u * u * eta) by (apply Rmult_le_pos; lra).
assert (N5 : 0 <= u * u * F) by (apply Rmult_le_pos; lra).
assert (N6 : 0 <= u * F) by (apply Rmult_le_pos; lra).
assert (N7 : 0 <= u * u * a4) by (apply Rmult_le_pos; lra).
assert (N8 : 0 <= u * u * a5) by (apply Rmult_le_pos; lra).
assert (N9 : 0 <= u * (u * u * P)) by (apply Rmult_le_pos; lra).
lra.
Qed.

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

(** * Stretch: the excess of the sum kernel over the exact sum *)

Notation u := (bpow radix2 (- prec)).
Notation eta := (bpow radix2 emin).

(* The gap of the format at z is at most max(eta, 2 u |z|) (the library's
   Directed2.ulp_le_max, repeated here so that this file needs only Format.v). *)
Lemma ulp_le_max : forall z, ulp radix2 fexp z <= Rmax eta (2 * u * Rabs z).
Proof.
intros z. destruct (Rle_or_lt (bpow radix2 (emin + prec - 1)) (Rabs z)) as [H|H].
- apply Rle_trans with (2 := Rmax_r _ _).
  apply Rle_trans with (Rabs z * bpow radix2 (1 - prec)); [now apply ulp_FLT_le|].
  right. replace (1 - prec)%Z with (1 + - prec)%Z by ring.
  rewrite bpow_plus, pow2_1. ring.
- apply Rle_trans with (2 := Rmax_l _ _). right.
  apply ulp_FLT_small; auto with typeclass_instances.
  apply Rlt_le_trans with (1 := H). apply bpow_le. lia.
Qed.

(* Rounding up moves z by at most eta + 2 u |z|. *)
Lemma gap_bound : forall z, 0 <= RU z - z <= eta + 2 * u * Rabs z.
Proof.
intros z. assert (G : z <= RU z) by apply RU_ge. split; [lra|].
generalize (error_le_ulp radix2 fexp Zceil z). intros E.
rewrite Rabs_pos_eq in E by lra.
assert (P : 0 <= 2 * u * Rabs z).
{ apply Rmult_le_pos; [generalize (bpow_gt_0 radix2 (- prec)); lra | apply Rabs_pos]. }
assert (P' : 0 < eta) by apply bpow_gt_0.
generalize (ulp_le_max z). unfold Rmax. destruct (Rle_dec eta (2 * u * Rabs z)); lra.
Qed.

Lemma RU_of_nonpos : forall z, z <= 0 -> z <= RU z <= 0.
Proof. intros z H. split; [apply RU_ge | apply RU_nonpos; exact H]. Qed.

Lemma two_sum_spec : forall a b s t, format a -> format b -> two_sum a b = (s, t) ->
  s = RU (a + b) /\ t = RU (a + b - s).
Proof.
intros a b s t Fa Fb E.
generalize (two_sum_fst a b) (two_sum_error a b Fa Fb). rewrite E. cbn [fst snd].
intros H1 H2. split; assumption.
Qed.

Lemma two_sum_nonpos_spec : forall a b s t, format a -> format b -> a <= 0 -> b <= 0 ->
  two_sum_nonpos a b = (s, t) -> s = RU (a + b) /\ t = RU (a + b - s).
Proof.
intros a b s t Fa Fb Ha Hb E.
generalize (two_sum_nonpos_fst a b) (two_sum_nonpos_error a b Fa Fb Ha Hb). rewrite E.
cbn [fst snd]. intros H1 H2. split; assumption.
Qed.

(* A sum of two numbers of F is exact (Sterbenz), or it does not cancel much. *)
Lemma sum_exact_or_big : forall a b, format a -> format b ->
  format (a + b) \/ Rabs a + Rabs b <= 3 * Rabs (a + b).
Proof.
intros a b Fa Fb.
destruct (Rle_or_lt 0 a) as [Ha|Ha]; destruct (Rle_or_lt 0 b) as [Hb|Hb].
- right. rewrite 3!Rabs_pos_eq by lra. lra.
- destruct (Rle_or_lt a (2 * - b)) as [H1|H1];
    [destruct (Rle_or_lt (- b) (2 * a)) as [H2|H2]|].
  + left. replace (a + b) with (a - - b) by ring. apply sterbenz; auto with typeclass_instances.
    * now apply generic_format_opp.
    * lra.
  + right. rewrite (Rabs_pos_eq a), (Rabs_left b), (Rabs_left (a + b)) by lra. lra.
  + right. rewrite (Rabs_pos_eq a), (Rabs_left b), (Rabs_pos_eq (a + b)) by lra. lra.
- destruct (Rle_or_lt b (2 * - a)) as [H1|H1];
    [destruct (Rle_or_lt (- a) (2 * b)) as [H2|H2]|].
  + left. replace (a + b) with (b - - a) by ring. apply sterbenz; auto with typeclass_instances.
    * now apply generic_format_opp.
    * lra.
  + right. rewrite (Rabs_left a), (Rabs_pos_eq b), (Rabs_left (a + b)) by lra. lra.
  + right. rewrite (Rabs_left a), (Rabs_pos_eq b), (Rabs_pos_eq (a + b)) by lra. lra.
- right. rewrite 3!Rabs_left by lra. lra.
Qed.

(* For a, b <= 0 the error of RU(a + b) is a number of F: RU rounds toward zero there,
   and the error is a multiple of the spacing at b no larger than |b|. *)
Lemma nonpos_error_exact_aux : forall a b, format a -> format b -> a <= 0 -> b <= 0 ->
  Rabs b <= Rabs a -> format (a + b - RU (a + b)).
Proof.
intros a b Fa Fb Ha Hb Hab.
destruct (Req_dec b 0) as [Zb|Zb].
{ subst b. rewrite Rplus_0_r, (RU_id a Fa). replace (a - a) with 0 by ring.
  apply generic_format_0. }
assert (Ht1 : RU (a + b) <= a) by (apply RU_least; [exact Fa | lra]).
assert (Ht2 : a + b <= RU (a + b)) by apply RU_ge.
assert (Mb : (mag radix2 b <= mag radix2 a)%Z) by (apply mag_le_abs; assumption).
assert (Mt : (mag radix2 b <= mag radix2 (RU (a + b)))%Z).
{ apply mag_le_abs; [exact Zb|]. rewrite (Rabs_left1 (RU (a + b))) by lra.
  rewrite (Rabs_left1 a) in Hab by lra. lra. }
assert (Ka : (cexp radix2 fexp b <= cexp radix2 fexp a)%Z) by (unfold cexp, FLT_exp; lia).
assert (Kt : (cexp radix2 fexp b <= cexp radix2 fexp (RU (a + b)))%Z)
  by (unfold cexp; apply monotone_exp; [auto with typeclass_instances | exact Mt]).
destruct (ex_shift radix2 fexp b (cexp radix2 fexp b) Fb (Z.le_refl _)) as [mb Hmb].
destruct (ex_shift radix2 fexp a (cexp radix2 fexp b) Fa Ka) as [ma Hma].
destruct (ex_shift radix2 fexp (RU (a + b)) (cexp radix2 fexp b) (RU_fmt _) Kt) as [mt Hmt].
assert (E : a + b - RU (a + b) = IZR (ma + mb - mt) * bpow radix2 (cexp radix2 fexp b)).
{ rewrite minus_IZR, plus_IZR, Rmult_minus_distr_r, Rmult_plus_distr_r, <- Hma, <- Hmb, <- Hmt.
  reflexivity. }
rewrite E. apply (format_multiple emin prec).
- unfold cexp. unfold FLT_exp. apply Z.le_max_r.
- rewrite <- E. rewrite Rabs_left1 by lra.
  apply Rle_trans with (Rabs b). { rewrite (Rabs_left1 b) by lra. lra. }
  apply Rlt_le, Rlt_le_trans with (1 := bpow_mag_gt radix2 b). apply bpow_le.
  unfold cexp, FLT_exp. lia.
Qed.

Lemma nonpos_error_exact : forall a b, format a -> format b -> a <= 0 -> b <= 0 ->
  format (a + b - RU (a + b)).
Proof.
intros a b Fa Fb Ha Hb.
destruct (Rle_or_lt (Rabs b) (Rabs a)) as [H|H].
- now apply nonpos_error_exact_aux.
- rewrite (Rplus_comm a b). apply nonpos_error_exact_aux; trivial. lra.
Qed.

(* So the second limbs' two-sum of the kernel is exact: t + f = xl + yl. *)
Theorem two_sum_nonpos_exact : forall a b, format a -> format b -> a <= 0 -> b <= 0 ->
  fst (two_sum_nonpos a b) + snd (two_sum_nonpos a b) = a + b.
Proof.
intros a b Fa Fb Ha Hb.
rewrite (two_sum_nonpos_error a b Fa Fb Ha Hb), two_sum_nonpos_fst.
rewrite (RU_id (a + b - RU (a + b))) by now apply nonpos_error_exact. ring.
Qed.

(* The second limb of an upper-normalized pair: l <= 0 and |l| <= 2 eta + 3 u |h|. *)
Lemma tail_bound : forall h l, format h -> upper_normalized h l -> u <= / 64 ->
  l <= 0 /\ - l <= 2 * eta + 3 * u * Rabs h.
Proof.
intros h l Fh N Hu.
destruct (proj1 (upper_normalized_iff h l Fh) N) as [Hl _].
split; [exact Hl|].
destruct (gap_bound (h + l)) as [_ G].
unfold upper_normalized in N. rewrite <- N in G.
assert (A : Rabs (h + l) <= Rabs h + - l).
{ generalize (Rabs_triang h l). rewrite (Rabs_left1 l) by exact Hl. lra. }
assert (U0 : 0 < u) by apply bpow_gt_0.
assert (P1 : u * Rabs (h + l) <= u * (Rabs h + - l)) by (apply Rmult_le_compat_l; lra).
assert (P2 : u * - l <= / 64 * - l) by (apply Rmult_le_compat_r; lra).
assert (P3 : 0 <= u * Rabs h) by (apply Rmult_le_pos; [lra | apply Rabs_pos]).
assert (P4 : 0 < eta) by apply bpow_gt_0.
lra.
Qed.

Lemma abs_le_of : forall a d, 0 <= d -> Rabs (a + d) <= Rabs a + d.
Proof. intros a d Hd. generalize (Rabs_triang a d). rewrite (Rabs_pos_eq d) by exact Hd. lra. Qed.

(* Statement 4 of the brief: for precision at least 6 and upper-normalized inputs, the
   excess of the kernel over the exact sum x + y is at most 64 u^2 |x + y| + 16 eta,
   u = 2^-prec, eta = 2^emin (the term for underflow). The constant is not sharp (the
   checks measured at most 6 u^2): every rounding is bounded by one step of its result,
   and the cases are those of Sterbenz's lemma, without the finer analysis of the
   published proofs for rounding to nearest. *)
Theorem add_r_excess : (6 <= prec)%Z -> forall xh xl yh yl,
  format xh -> format xl -> format yh -> format yl ->
  upper_normalized xh xl -> upper_normalized yh yl ->
  fst (add_r xh xl yh yl) + snd (add_r xh xl yh yl) - ((xh + xl) + (yh + yl))
  <= 64 * (u * u) * Rabs ((xh + xl) + (yh + yl)) + 16 * eta.
Proof.
intros Hp xh xl yh yl Fxh Fxl Fyh Fyl Nx Ny.
assert (Hu : 0 < u) by apply bpow_gt_0.
assert (Hu64 : u <= / 64).
{ apply Rle_trans with (bpow radix2 (-6)); [apply bpow_le; lia | right; reflexivity]. }
assert (Heta : 0 < eta) by apply bpow_gt_0.
destruct (tail_bound xh xl Fxh Nx Hu64) as [Lx Tx].
destruct (tail_bound yh yl Fyh Ny Hu64) as [Ly Ty].
replace ((xh + xl) + (yh + yl)) with ((xh + yh) + (xl + yl)) by ring.
unfold add_r.
destruct (two_sum xh yh) as [s e] eqn:E1. cbv beta iota zeta.
destruct (two_sum_spec xh yh s e Fxh Fyh E1) as [Hs He].
destruct (two_sum_nonpos xl yl) as [t f] eqn:E2. cbv beta iota zeta.
destruct (two_sum_nonpos_spec xl yl t f Fxl Fyl Lx Ly E2) as [Ht Hf].
assert (Fs : format s) by (rewrite Hs; apply RU_fmt).
assert (Ft : format t) by (rewrite Ht; apply RU_fmt).
assert (Fc : format (add_up e t)) by (unfold add_up; apply RU_fmt).
destruct (two_sum s (add_up e t)) as [v g] eqn:E3. cbv beta iota zeta.
destruct (two_sum_spec s (add_up e t) v g Fs Fc E3) as [Hv Hg].
assert (Fv : format v) by (rewrite Hv; apply RU_fmt).
assert (Fw : format (add_up f g)) by (unfold add_up; apply RU_fmt).
destruct (two_sum v (add_up f g)) as [zh zl] eqn:E4. cbn [fst snd].
destruct (two_sum_spec v (add_up f g) zh zl Fv Fw E4) as [Hzh Hzl].
unfold add_up in *.
(* the gaps of the ten roundings *)
destruct (gap_bound (xh + yh)) as [G1a G1b]. rewrite <- Hs in G1a, G1b.
destruct (gap_bound (xl + yl)) as [G2a G2b]. rewrite <- Ht in G2a, G2b.
destruct (gap_bound (xh + yh - s)) as [G3a G3b]. rewrite <- He in G3a, G3b.
destruct (gap_bound (xl + yl - t)) as [G4a G4b]. rewrite <- Hf in G4a, G4b.
destruct (gap_bound (e + t)) as [G5a G5b].
destruct (gap_bound (s + RU (e + t))) as [G6a G6b]. rewrite <- Hv in G6a, G6b.
destruct (gap_bound (s + RU (e + t) - v)) as [G7a G7b]. rewrite <- Hg in G7a, G7b.
destruct (gap_bound (f + g)) as [G8a G8b].
destruct (gap_bound (v + RU (f + g))) as [G9a G9b]. rewrite <- Hzh in G9a, G9b.
destruct (gap_bound (v + RU (f + g) - zh)) as [G0a G0b]. rewrite <- Hzl in G0a, G0b.
(* the signs of the second limbs *)
assert (Se : xh + yh - s <= e <= 0) by (rewrite He; apply RU_of_nonpos; lra).
assert (St : xl + yl <= t <= 0) by (rewrite Ht; apply RU_of_nonpos; lra).
assert (Sc : e + t <= RU (e + t) <= 0) by (apply RU_of_nonpos; lra).
assert (Sg : s + RU (e + t) - v <= g <= 0) by (rewrite Hg; apply RU_of_nonpos; lra).
assert (Sf : xl + yl - t <= f <= 0) by (rewrite Hf; apply RU_of_nonpos; lra).
assert (Sw : f + g <= RU (f + g) <= 0) by (apply RU_of_nonpos; lra).
destruct Se as [Se1 Se2]. destruct St as [St1 St2]. destruct Sc as [Sc1 Sc2].
destruct Sg as [Sg1 Sg2]. destruct Sf as [Sf1 Sf2]. destruct Sw as [Sw1 Sw2].
set (c := RU (e + t)) in *. set (w := RU (f + g)) in *.
set (X := xh + yh) in *. set (Lo := xl + yl) in *.
assert (HLo : Lo <= 0) by (unfold Lo; lra).
rewrite (Rabs_left1 (X - s)) in G3b by lra.
rewrite (Rabs_left1 (Lo - t)) in G4b by lra.
rewrite (Rabs_left1 (e + t)) in G5b by lra.
rewrite (Rabs_left1 (s + c - v)) in G7b by lra.
rewrite (Rabs_left1 (f + g)) in G8b by lra.
rewrite (Rabs_left1 (v + w - zh)) in G0b by lra.
assert (AS : Rabs s <= Rabs X + (s - X)).
{ generalize (abs_le_of X (s - X)). replace (X + (s - X)) with s by ring. intros K.
  apply K. lra. }
assert (AV : Rabs v <= Rabs (s + c) + (v - (s + c))).
{ generalize (abs_le_of (s + c) (v - (s + c))). replace (s + c + (v - (s + c))) with v by ring.
  intros K. apply K. lra. }
assert (ASC : Rabs (s + c) <= Rabs s + - c).
{ generalize (Rabs_triang s c). rewrite (Rabs_left1 c) by lra. lra. }
assert (AVW : Rabs (v + w) <= Rabs v + - w).
{ generalize (Rabs_triang v w). rewrite (Rabs_left1 w) by lra. lra. }
assert (ALo : Rabs Lo = - Lo) by (apply Rabs_left1; lra).
assert (AXS : Rabs X <= Rabs (X + Lo) + - Lo).
{ generalize (abs_le_of (X + Lo) (- Lo)). replace (X + Lo + - Lo) with X by ring. intros K.
  apply K. lra. }
destruct (sum_exact_or_big xh yh Fxh Fyh) as [FX|BX].
- (* xh + yh is exact: s = X, e = 0, c = t, and t + f = Lo exactly *)
  change (format X) in FX.
  assert (Es : s = X) by (rewrite Hs; apply RU_id; exact FX).
  assert (Ee : e = 0).
  { rewrite He, Es. replace (X - X) with 0 by ring. apply round_0; auto with typeclass_instances. }
  assert (Ec : c = t).
  { unfold c. rewrite Ee, Rplus_0_l. apply RU_id. exact Ft. }
  assert (Ef : f = Lo - t).
  { rewrite Hf, Ht. apply RU_id. change (format (xl + yl - RU (xl + yl))).
    apply nonpos_error_exact; assumption. }
  clearbody c. subst c.
  destruct (sum_exact_or_big s t Fs Ft) as [Fst|Bst].
  + (* s + t is exact too: v = s + t, g = 0, w = f, and v + w = x + y *)
    assert (Ev : v = s + t) by (rewrite Hv; apply RU_id; exact Fst).
    assert (Eg : g = 0).
    { rewrite Hg, Ev. replace (s + t - (s + t)) with 0 by ring.
      apply round_0; auto with typeclass_instances. }
    assert (Ew : w = f).
    { unfold w. rewrite Eg, Rplus_0_r. apply RU_id. rewrite Hf. apply RU_fmt. }
    assert (EVW : v + w = X + Lo) by (rewrite Ev, Ew, Ef, Es; ring).
    rewrite EVW in G9b, G0b.
    assert (Q : u * (zh - (X + Lo)) <= u * (eta + 2 * u * Rabs (X + Lo)))
      by (apply Rmult_le_compat_l; lra).
    assert (Pe : u * eta <= / 64 * eta) by (apply Rmult_le_compat_r; lra).
    assert (N1 : 0 <= u * u * Rabs (X + Lo))
      by (apply Rmult_le_pos; [apply Rmult_le_pos; lra | apply Rabs_pos]).
    rewrite EVW in G0a. lra.
  + (* s + t does not cancel much *)
    rewrite Es in Bst.
    assert (ALt : Rabs Lo <= 3 * Rabs (X + t) + - f).
    { replace Lo with (t + f) by (rewrite Ef; ring).
      generalize (Rabs_triang t f). rewrite (Rabs_left1 f) by lra.
      generalize (Rabs_pos X). lra. }
    assert (APS : Rabs (X + t) <= Rabs (X + Lo) + - f).
    { generalize (abs_le_of (X + Lo) (- f)). replace (X + Lo + - f) with (X + t) by (rewrite Ef; ring).
      intros K. apply K. lra. }
    rewrite Es in *.
    apply (excess_exact_heads_arith u eta (Rabs (X + t)) (- f) (Rabs (X + Lo))
             (v - (X + t)) (- (f + g)) (Rabs (v + w)) (zh - (v + w))).
    * exact Hu.
    * exact Hu64.
    * lra.
    * apply Rabs_pos.
    * lra.
    * apply Rabs_pos.
    * lra.
    * lra.
    * apply Rabs_pos.
    * lra.
    * exact G6b.
    * assert (K : u * Rabs Lo <= u * (3 * Rabs (X + t) + - f)) by (apply Rmult_le_compat_l; lra).
      lra.
    * lra.
    * lra.
    * exact G9b.
    * assert (Z1 : e - (X - X) = 0) by (rewrite Ee; ring).
      assert (Z2 : f - (Lo - t) = 0) by (rewrite Ef; ring).
      lra.
    * exact APS.
- (* |xh| + |yh| <= 3 |xh + yh| *)
  change (Rabs xh + Rabs yh <= 3 * Rabs X) in BX.
  assert (BL : Rabs Lo <= 4 * eta + 9 * u * Rabs X).
  { assert (K : u * (Rabs xh + Rabs yh) <= u * (3 * Rabs X)) by (apply Rmult_le_compat_l; lra).
    rewrite ALo. unfold Lo. lra. }
  apply (excess_big_arith u eta (Rabs X) (Rabs Lo) (Rabs (X + Lo))).
  + exact Hu.
  + exact Hu64.
  + lra.
  + apply Rabs_pos.
  + apply Rabs_pos.
  + apply Rabs_pos.
  + apply Rle_trans with (6 * eta + 2 * u * ((s - X) + (t - Lo) + - (e + t) + (v - (s + c))
                                           + - (f + g) + (zh - (v + w)))).
    * lra.
    * apply (excess_master_arith u eta (Rabs X) (Rabs Lo) _ _ _ _ _ _ (Rabs (s + c)) (Rabs (v + w)));
        try lra; try apply Rabs_pos.
  + exact BL.
  + lra.
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
Print Assumptions two_sum_nonpos_exact.
Print Assumptions add_r_excess.
