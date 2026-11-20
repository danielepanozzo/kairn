(* Scaling a ball by a power of two, in the real model (no overflow): ball_mul_pow2_1 and
   ball_mul_pow2_2 (docs/developer/design/milestone2.md, "Scaling a ball by a power of
   two").

       ball_mul_pow2_1(cx, rx, c) -> (cz, rz)        with c = 2^n and N = eta / (2 u)
         cz = prod(cx, c)        rr = prod(rx, c)
         ec = N < |cz| or cx = 0                      the center is exact
         er = N < rr or rx = 0                        the radius is exact
         rz = rr if ec and er, else succ(succ(rr))

   ball_mul_pow2_2 scales the two limbs of the center as mul_pow2_2 does, and tests the
   limb that is rounded in the smallest binade: the second one, or the first when the
   second is zero.

   Notation: F is the format (precision prec, gradual underflow, smallest positive number
   eta = 2^emin, no largest number); u = 2^-prec; N = eta / (2 u) = 2^(emin + prec - 1) is
   the smallest normal number; RN is rounding to nearest, ties to even; succ(r) is the
   next number of F above r.

   What is proved (the generated statements of proofs/gen/Statements.v), for a center of
   F (a normalized pair, for two limbs), a radius rx >= 0 of F and c = 2^n, from
   precision 2:
   - the outputs are numbers of F (the center a normalized pair);
   - containment: for every x within rx of the center, x c is within rz of the result;
   - exactness: when each scaled limb of the center and the scaled radius is zero or
     above N in magnitude, every member of the result is c times a member of the operand:
     the result is the exact image of the ball.

   Why. A number of F times a power of two is a number of F when it is zero or at least
   N in magnitude, and is otherwise rounded with an error of at most eta / 2 (scale_exact,
   scale_error of MulPow2.v). The tests ec and er are true only when the products are
   exact: a rounded product above N comes from a product of at least N. Then the result
   is the ball of center c cx and radius c rx. Otherwise the center is within eta / 2 of
   c cx (eta, for two limbs) and rr within eta / 2 of c rx, and two steps above rr are at
   least 2 eta more than rr, since no two numbers of F are closer than eta
   (ball_pow2_radius). The hypothesis of exactness makes both tests true. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format EFT Normalized MulPow2.
Open Scope R_scope.

Section BallPow2.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation succ := (succ radix2 fexp).
Notation N := (pow2 (emin + prec - 1)).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.

(* The constant of the listings, eta / (2 u) rounded up, is N, a number of the format;
   and the threshold of the claims is the same number. *)
Lemma threshold_N : pow2 emin / (2 * pow2 (- prec)) = N.
Proof.
replace (2 * pow2 (- prec)) with (pow2 (1 + - prec)) by (rewrite bpow_plus, pow2_1; ring).
unfold Rdiv. rewrite <- bpow_opp, <- bpow_plus. apply f_equal. ring.
Qed.

Lemma format_N : format N.
Proof. apply generic_format_bpow. unfold FLT_exp. lia. Qed.

Lemma up_ball_mul_pow2_1_0_eq : up_ball_mul_pow2_1_0 emin prec = N.
Proof.
unfold up_ball_mul_pow2_1_0. rewrite threshold_N.
apply round_generic; auto with typeclass_instances. exact format_N.
Qed.

(* A rounded product above N in magnitude is exact, and the product is above N. *)
Lemma scale_exact_test :
  forall a n, format a -> N < Rabs (rnd (a * pow2 n)) ->
  rnd (a * pow2 n) = a * pow2 n /\ N < Rabs (a * pow2 n).
Proof.
intros a n Fa H.
assert (L : N <= Rabs (a * pow2 n)).
{ apply Rnot_lt_le. intros K.
  generalize (round_abs_le emin prec tie_even (a * pow2 n) N format_N (Rlt_le _ _ K)). lra. }
assert (E : rnd (a * pow2 n) = a * pow2 n).
{ apply (scale_exact emin prec a n Fa). now right. }
split; [exact E|]. now rewrite <- E.
Qed.

(* No two numbers of the format are closer than eta: two steps above r >= 0 are at
   least 2 eta more than r. *)
Lemma ulp_ge_eta : forall r, pow2 emin <= ulp radix2 fexp r.
Proof.
intros r. destruct (Req_dec r 0) as [Z|Z].
- rewrite Z, ulp_FLT_0; trivial. apply Rle_refl.
- rewrite ulp_neq_0 by exact Z. apply bpow_le. unfold cexp, FLT_exp. lia.
Qed.

Lemma two_steps : forall r, 0 <= r -> r + 2 * pow2 emin <= succ (succ r).
Proof.
intros r Hr.
assert (S1 : succ r = r + ulp radix2 fexp r) by now apply succ_eq_pos.
generalize (ulp_ge_eta r) (bpow_gt_0 radix2 emin). intros U1 P.
assert (S2 : succ (succ r) = succ r + ulp radix2 fexp (succ r)) by (apply succ_eq_pos; lra).
generalize (ulp_ge_eta (succ r)). lra.
Qed.

Lemma scale_back : forall t n, t * pow2 n * pow2 (- n) = t.
Proof.
intros t n. rewrite Rmult_assoc, <- bpow_plus. replace (n + - n)%Z with 0%Z by ring.
simpl. ring.
Qed.

(* The radius, and the two claims, for a center of exact value cxv whose scaled value Z
   is within 3/2 eta of c cxv, and exactly c cxv when its test ec is true. *)
Lemma ball_pow2_radius :
  forall (n : Z) (cxv rx Z : R) (ec : bool),
  format rx -> 0 <= rx ->
  Rabs (Z - cxv * pow2 n) <= 3 / 2 * pow2 emin ->
  (ec = true -> Z = cxv * pow2 n) ->
  let rr := rnd (rx * pow2 n) in
  let er := orb (Rlt_bool N rr) (Req_bool rx 0) in
  let rz := if andb ec er then rr else succ (succ rr) in
  format rz /\
  (forall x, Rabs (x - cxv) <= rx -> Rabs (x * pow2 n - Z) <= rz) /\
  (ec = true -> rx * pow2 n = 0 \/ N < Rabs (rx * pow2 n) ->
   forall s, Rabs (s - Z) <= rz -> exists x, Rabs (x - cxv) <= rx /\ s = x * pow2 n).
Proof.
intros n cxv rx Z ec Frx Prx HZ Hec rr er rz.
assert (C0 : 0 < pow2 n) by apply bpow_gt_0.
assert (Frr : format rr) by (apply generic_format_round; auto with typeclass_instances).
assert (Prr : 0 <= rr).
{ apply round_ge_generic; auto with typeclass_instances. apply generic_format_0.
  apply Rmult_le_pos; lra. }
assert (Dr : Rabs (rr - rx * pow2 n) <= / 2 * pow2 emin) by exact (scale_error emin prec rx n Frx).
assert (Er : er = true -> rr = rx * pow2 n).
{ unfold er. intros H. apply orb_true_iff in H. destruct H as [H|H].
  - destruct (Rlt_bool_spec N rr) as [K|K]; [|discriminate H].
    apply (scale_exact_test rx n Frx). fold rr. now rewrite Rabs_pos_eq.
  - destruct (Req_bool_spec rx 0) as [K|K]; [|discriminate H].
    apply (scale_exact emin prec rx n Frx). left. rewrite K. ring. }
generalize (two_steps rr Prr) (bpow_gt_0 radix2 emin). intros Step P.
split; [|split].
- unfold rz. destruct (andb ec er); trivial.
  apply generic_format_succ; auto with typeclass_instances.
  apply generic_format_succ; auto with typeclass_instances.
- intros x Hx.
  assert (Hx' : Rabs (x * pow2 n - cxv * pow2 n) <= rx * pow2 n).
  { replace (x * pow2 n - cxv * pow2 n) with ((x - cxv) * pow2 n) by ring.
    rewrite Rabs_mult, (Rabs_pos_eq (pow2 n)) by lra. apply Rmult_le_compat_r; lra. }
  unfold rz. destruct (andb ec er) eqn:Ex.
  + apply andb_true_iff in Ex. destruct Ex as [E1 E2]. rewrite (Hec E1), (Er E2). exact Hx'.
  + apply Rabs_le_inv in HZ, Dr, Hx'. apply Rabs_le. lra.
- intros E1 Hr s Hs.
  assert (E2 : er = true).
  { unfold er. apply orb_true_iff. destruct Hr as [Hr|Hr].
    - right. apply Req_bool_true. destruct (Rmult_integral _ _ Hr) as [K|K]; trivial. lra.
    - left. apply Rlt_bool_true.
      assert (E : rr = rx * pow2 n).
      { apply (scale_exact emin prec rx n Frx). right. now apply Rlt_le. }
      rewrite E. rewrite Rabs_pos_eq in Hr; trivial. apply Rmult_le_pos; lra. }
  unfold rz in Hs. rewrite E1, E2 in Hs. cbn [andb] in Hs. rewrite (Hec E1), (Er E2) in Hs.
  exists (s * pow2 (- n)). split.
  + replace (s * pow2 (- n) - cxv) with ((s - cxv * pow2 n) * pow2 (- n))
      by (rewrite Rmult_minus_distr_r, scale_back; reflexivity).
    rewrite Rabs_mult, (Rabs_pos_eq (pow2 (- n))) by apply bpow_ge_0.
    apply Rle_trans with (rx * pow2 n * pow2 (- n)).
    * apply Rmult_le_compat_r; [apply bpow_ge_0|exact Hs].
    * rewrite scale_back. apply Rle_refl.
  + rewrite Rmult_assoc, <- bpow_plus. replace (- n + n)%Z with 0%Z by ring. simpl. ring.
Qed.

End BallPow2.

(** * The generated statements *)

Theorem ball_mul_pow2_1_correct : ball_mul_pow2_1_spec.
Proof.
intros emin prec Hp cx rx c Fcx Frx Fc Prx [n Hc]. subst c.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
unfold ball_mul_pow2_1. cbv zeta. rewrite 2!Rplus_0_r, (up_ball_mul_pow2_1_0_eq emin prec).
unfold eta, u. rewrite (threshold_N emin prec).
set (cz := round radix2 (FLT_exp emin prec) (Znearest tie_even) (cx * pow2 n)).
set (ec := orb (Rlt_bool (pow2 (emin + prec - 1)) (Rabs cz)) (Req_bool cx 0)).
assert (Fcz : fmt emin prec cz) by (apply generic_format_round; auto with typeclass_instances).
assert (Dc : Rabs (cz - cx * pow2 n) <= / 2 * pow2 emin) by exact (scale_error emin prec cx n Fcx).
assert (Hec : ec = true -> cz = cx * pow2 n).
{ unfold ec. intros H. apply orb_true_iff in H. destruct H as [H|H].
  - destruct (Rlt_bool_spec (pow2 (emin + prec - 1)) (Rabs cz)) as [K|K]; [|discriminate H].
    apply (scale_exact_test emin prec cx n Fcx K).
  - destruct (Req_bool_spec cx 0) as [K|K]; [|discriminate H].
    apply (scale_exact emin prec cx n Fcx). left. rewrite K. ring. }
assert (HZ : Rabs (cz - cx * pow2 n) <= 3 / 2 * pow2 emin).
{ generalize (bpow_gt_0 radix2 emin). lra. }
generalize (ball_pow2_radius emin prec n cx rx cz ec Frx Prx HZ Hec). cbv zeta.
intros [Frz [Cont Exact]].
split; [exact Fcz|split; [exact Frz|split; [exact Cont|]]].
intros [Hcx Hrx]. apply Exact; trivial.
unfold ec. apply orb_true_iff. destruct Hcx as [Hcx|Hcx].
- right. apply Req_bool_true. destruct (Rmult_integral _ _ Hcx) as [K|K]; trivial.
  generalize (bpow_gt_0 radix2 n). lra.
- left. apply Rlt_bool_true.
  assert (E : cz = cx * pow2 n).
  { apply (scale_exact emin prec cx n Fcx). right. now apply Rlt_le. }
  now rewrite E.
Qed.

Theorem ball_mul_pow2_2_correct : ball_mul_pow2_2_spec.
Proof.
intros emin prec Hp cx0 cx1 rx c Hn Frx Fc Prx [n Hc]. subst c.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
assert (F0 : fmt emin prec cx0) by apply Hn.
assert (F1 : fmt emin prec cx1) by apply Hn.
unfold ball_mul_pow2_2. cbv zeta. rewrite 3!Rplus_0_r, (up_ball_mul_pow2_1_0_eq emin prec).
unfold eta, u. rewrite (threshold_N emin prec).
generalize (mul_pow2_2_facts emin prec Hp cx0 cx1 n Hn). cbv zeta. unfold RN.
set (h := round radix2 (FLT_exp emin prec) (Znearest tie_even) (cx0 * pow2 n)).
set (l := round radix2 (FLT_exp emin prec) (Znearest tie_even) (cx1 * pow2 n)).
destruct (fast_two_sum emin prec tie_even h l) as [cz0 cz1]. cbn [fst snd].
intros [Nz [Sz Bz]].
set (m := if Req_bool cx1 0 then h else l).
set (ec := orb (Rlt_bool (pow2 (emin + prec - 1)) (Rabs m)) (Req_bool cx0 0)).
assert (E0 : forall t, round radix2 (FLT_exp emin prec) (Znearest tie_even) (0 * pow2 t) = 0).
{ intros t. rewrite Rmult_0_l. apply round_0; auto with typeclass_instances. }
(* the tail of a normalized pair is at most its leading limb in magnitude *)
assert (T : Rabs cx1 <= Rabs cx0).
{ apply Rle_trans with (1 := normalized_2_tail_rel emin prec cx0 cx1 Hn).
  assert (u prec <= 1).
  { unfold u. change 1 with (pow2 0). apply bpow_le. lia. }
  generalize (Rabs_pos cx0). nra. }
assert (Hec : ec = true -> cz0 + cz1 = (cx0 + cx1) * pow2 n).
{ unfold ec. intros H. rewrite Sz, Rmult_plus_distr_r. apply orb_true_iff in H.
  destruct H as [H|H].
  - destruct (Rlt_bool_spec (pow2 (emin + prec - 1)) (Rabs m)) as [K|K]; [|discriminate H].
    unfold m in K. destruct (Req_bool_spec cx1 0) as [Z1|Z1].
    + destruct (scale_exact_test emin prec cx0 n F0 K) as [Eh _].
      unfold l. rewrite Z1, E0. unfold h in *. rewrite Eh. ring.
    + destruct (scale_exact_test emin prec cx1 n F1 K) as [El Kl].
      assert (Eh : h = cx0 * pow2 n).
      { apply (scale_exact emin prec cx0 n F0). right.
        apply Rle_trans with (Rabs (cx1 * pow2 n)); [now apply Rlt_le|].
        rewrite 2!Rabs_mult. apply Rmult_le_compat_r; [apply Rabs_pos|exact T]. }
      unfold l in *. rewrite El, Eh. ring.
  - destruct (Req_bool_spec cx0 0) as [Z0|Z0]; [|discriminate H].
    assert (Z1 : cx1 = 0) by exact (normalized_2_zero emin prec cx0 cx1 Hn Z0).
    unfold h, l. rewrite Z0, Z1, E0. ring. }
assert (HZ : Rabs (cz0 + cz1 - (cx0 + cx1) * pow2 n) <= 3 / 2 * pow2 emin).
{ generalize (bpow_gt_0 radix2 emin). lra. }
generalize (ball_pow2_radius emin prec n (cx0 + cx1) rx (cz0 + cz1) ec Frx Prx HZ Hec).
cbv zeta. intros [Frz [Cont Exact]].
split; [exact Frz|split; [exact Nz|split; [exact Cont|]]].
intros [Hc0 [Hc1 Hrx]]. apply Exact; trivial.
unfold ec. apply orb_true_iff. destruct Hc0 as [Hc0|Hc0].
- right. apply Req_bool_true. destruct (Rmult_integral _ _ Hc0) as [K|K]; trivial.
  generalize (bpow_gt_0 radix2 n). lra.
- left. apply Rlt_bool_true. unfold m.
  assert (Eh : h = cx0 * pow2 n).
  { apply (scale_exact emin prec cx0 n F0). right. now apply Rlt_le. }
  destruct (Req_bool_spec cx1 0) as [Z1|Z1].
  + now rewrite Eh.
  + destruct Hc1 as [Hc1|Hc1].
    * exfalso. destruct (Rmult_integral _ _ Hc1) as [K|K]; [contradiction|].
      generalize (bpow_gt_0 radix2 n). lra.
    * assert (El : l = cx1 * pow2 n).
      { apply (scale_exact emin prec cx1 n F1). right. now apply Rlt_le. }
      now rewrite El.
Qed.
