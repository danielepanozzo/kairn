(* The scaling of a ball vector by a power of two in the real model: the generated
   statements of its kernels bv_mul_pow2_step_1, bv_mul_pow2_step_2 and bv_mul_pow2_radius
   (proofs/gen/Statements.v) and of the folds bv_mul_pow2_1 and bv_mul_pow2_2
   (proofs/gen/FoldStatements.v).

   With c = 2^n and N = eta / (2 u) = 2^(emin + prec - 1), the smallest normal number (the
   constant up(eta/(2*u)) of the listings is N itself, up_ball_mul_pow2_1_0_eq of
   BallPow2.v):
   - the steps are mul_pow2_step_1 (z = RN (x c)) and mul_pow2_2 on the center, with a mask
     e. For one limb e = (N < |z|) or (x = 0); for two, the same test of the scaled last
     nonzero limb, or x0 = 0. The mask is true exactly when every product of a limb is zero
     or above N in magnitude (step_mask_1, step_mask_2): a rounded product above N comes
     from a product above N (scale_exact_test), and a product above N is exact
     (scale_exact of MulPow2.v); a nonzero second limb of a normalized pair makes the first
     nonzero and larger.
   - the radius kernel is the radius lines of ball_mul_pow2_k with ex in place of one
     entry's mask, plus m - m, which is 0: rz = RN (c rx) when ex and the radius test hold,
     the second number above it otherwise (two_steps: at least 2 eta more). So rz >= c rx,
     rz = c rx under ex and the condition of the radius, and rz >= c rx + eta when ex is
     false.
   - the folds: the radius does not depend on m (radius_any_m). Entry by entry the center
     written is within eta / 2 (one limb) or eta (two limbs) of c x, and exactly c x when its
     mask is true; ex is the and of the masks. When ex is true every center is exact and
     rz >= c rx covers c times the operand's ball; when it is false rz >= c rx + eta covers
     the error. Under the conditions of exact_when every mask is true, so ex is, rz = c rx
     and every center is c x: the ball of the center written is c times the operand's ball
     (scale_back). *)
From Stdlib Require Import Reals ZArith List Bool Lia Lra Psatz.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements FoldModel FoldStatements.
From Kairn Require Import Format EFT Normalized Folds MulPow2 BallPow2.
Import ListNotations.
Open Scope R_scope.

Section BvPow2.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation succ := (succ radix2 fexp).
Notation N := (pow2 (emin + prec - 1)).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.

(* The condition of exact_when on a product, with c = 2^n. *)
Definition cond (t : R) : Prop := t = 0 \/ N < Rabs t.

Lemma cond_mul :
  forall x n, cond (x * pow2 n) <-> x = 0 \/ N < Rabs (x * pow2 n).
Proof.
intros x n. unfold cond. split; intros [H|H]; auto.
- left. destruct (Rmult_integral _ _ H) as [K|K]; trivial.
  generalize (bpow_gt_0 radix2 n). lra.
- left. rewrite H. ring.
Qed.

(* The mask of one product: N < |RN (x c)| or x = 0, exactly when the product is zero or
   above N; and then the rounding is exact. *)
Lemma step_mask_1 :
  forall x n, format x ->
  (orb (Rlt_bool N (Rabs (rnd (x * pow2 n)))) (Req_bool x 0) = true <-> cond (x * pow2 n)) /\
  (cond (x * pow2 n) -> rnd (x * pow2 n) = x * pow2 n).
Proof.
intros x n Fx.
assert (Ex : cond (x * pow2 n) -> rnd (x * pow2 n) = x * pow2 n).
{ intros [H|H]; apply (scale_exact emin prec x n Fx); [left; exact H|right; now apply Rlt_le]. }
split; [|exact Ex]. rewrite cond_mul. rewrite orb_true_iff. split.
- intros [H|H].
  + destruct (Rlt_bool_spec N (Rabs (rnd (x * pow2 n)))) as [K|K]; [|discriminate H].
    right. exact (proj2 (scale_exact_test emin prec x n Fx K)).
  + destruct (Req_bool_spec x 0) as [K|K]; [left; exact K|discriminate H].
- intros [H|H].
  + right. apply Req_bool_true. exact H.
  + left. apply Rlt_bool_true. rewrite (Ex (or_intror H)). exact H.
Qed.

(* The mask of a normalized pair: the test of the scaled last nonzero limb, or a zero
   center; exactly when both products are zero or above N. *)
Lemma step_mask_2 :
  forall x0 x1 n, normalized_2 emin prec x0 x1 ->
  let h := rnd (x0 * pow2 n) in
  let l := rnd (x1 * pow2 n) in
  orb (Rlt_bool N (Rabs (if Req_bool x1 0 then h else l))) (Req_bool x0 0) = true <->
  cond (x0 * pow2 n) /\ cond (x1 * pow2 n).
Proof.
intros x0 x1 n Hn h l.
assert (F0 : format x0) by apply Hn.
assert (F1 : format x1) by apply Hn.
assert (T : Rabs x1 <= Rabs x0).
{ apply Rle_trans with (1 := normalized_2_tail_rel emin prec x0 x1 Hn).
  assert (u prec <= 1).
  { unfold u. change 1 with (pow2 0). apply bpow_le. lia. }
  generalize (Rabs_pos x0). nra. }
assert (P : 0 < pow2 n) by apply bpow_gt_0.
destruct (step_mask_1 x0 n F0) as [M0 E0].
destruct (step_mask_1 x1 n F1) as [M1 E1].
fold h in M0, E0. fold l in M1, E1.
rewrite orb_true_iff. split.
- intros [H|H].
  + destruct (Req_bool_spec x1 0) as [Z1|Z1].
    * split.
      -- apply M0. rewrite H. reflexivity.
      -- left. rewrite Z1. ring.
    * destruct (Rlt_bool_spec N (Rabs l)) as [K|K]; [|discriminate H].
      assert (C1 : cond (x1 * pow2 n)) by (apply M1; reflexivity).
      split; [|exact C1].
      right. destruct C1 as [C1|C1].
      { exfalso. destruct (Rmult_integral _ _ C1) as [K'|K']; [contradiction|lra]. }
      apply Rlt_le_trans with (1 := C1). rewrite 2!Rabs_mult. apply Rmult_le_compat_r.
      apply Rabs_pos. exact T.
  + destruct (Req_bool_spec x0 0) as [Z0|Z0]; [|discriminate H].
    assert (Z1 : x1 = 0) by exact (normalized_2_zero emin prec x0 x1 Hn Z0).
    split; left; [rewrite Z0|rewrite Z1]; ring.
- intros [C0 C1].
  destruct (proj1 (cond_mul x0 n) C0) as [Z0|K0].
  + right. apply Req_bool_true. exact Z0.
  + left. destruct (Req_bool_spec x1 0) as [Z1|Z1].
    * apply Rlt_bool_true. cbv beta iota. rewrite (E0 C0). exact K0.
    * destruct (proj1 (cond_mul x1 n) C1) as [Z1'|K1]; [contradiction|].
      apply Rlt_bool_true. cbv beta iota. rewrite (E1 C1). exact K1.
Qed.

(* The radius lines, at any m: m - m is 0. *)
Lemma radius_any_m :
  forall m ex rx c,
  bv_mul_pow2_radius emin prec tie_even m ex rx c = bv_mul_pow2_radius emin prec tie_even 0 ex rx c.
Proof.
intros m ex rx c. unfold bv_mul_pow2_radius. cbv zeta.
replace (m - m) with (0 - 0) by ring. reflexivity.
Qed.

(* The radius kernel on c = 2^n. *)
Lemma radius_facts :
  forall m ex rx n, format rx -> 0 <= rx ->
  let rz := bv_mul_pow2_radius emin prec tie_even m ex rx (pow2 n) in
  format rz /\ rx * pow2 n <= rz /\
  (ex = true -> cond (rx * pow2 n) -> rz = rx * pow2 n) /\
  (ex = false -> rx * pow2 n + pow2 emin <= rz).
Proof.
intros m ex rx n Frx Prx rz. unfold rz. rewrite radius_any_m.
unfold bv_mul_pow2_radius. cbv zeta.
rewrite Rplus_0_r, (up_ball_mul_pow2_1_0_eq emin prec).
replace (0 - 0) with 0 by ring. rewrite round_0 by auto with typeclass_instances.
rewrite Rplus_0_r.
set (rr := rnd (rx * pow2 n)).
assert (P : 0 < pow2 n) by apply bpow_gt_0.
assert (Frr : format rr) by (apply generic_format_round; auto with typeclass_instances).
assert (Prr : 0 <= rr).
{ apply round_ge_generic; auto with typeclass_instances. apply generic_format_0. nra. }
destruct (step_mask_1 rx n Frx) as [Mr Er]. fold rr in Mr, Er.
rewrite (Rabs_pos_eq rr Prr) in Mr.
assert (Dr : Rabs (rr - rx * pow2 n) <= / 2 * pow2 emin) by exact (scale_error emin prec rx n Frx).
generalize (two_steps emin prec rr Prr) (bpow_gt_0 radix2 emin). intros Step Pe.
assert (Fs : format (succ (succ rr))).
{ apply generic_format_succ; auto with typeclass_instances.
  apply generic_format_succ; auto with typeclass_instances. }
assert (Ls : rx * pow2 n + pow2 emin <= succ (succ rr)).
{ apply Rabs_le_inv in Dr. lra. }
set (er := orb (Rlt_bool N rr) (Req_bool rx 0)) in *.
destruct (andb ex er) eqn:Q.
- apply andb_true_iff in Q. destruct Q as [Qx Qr].
  assert (E : rr = rx * pow2 n) by exact (Er (proj1 Mr Qr)).
  rewrite round_generic by (auto with typeclass_instances).
  split. exact Frr. split. lra. split. intros _ _. exact E. intros F. rewrite Qx in F. discriminate F.
- rewrite round_generic by (auto with typeclass_instances).
  split. exact Fs. split. lra. split.
  + intros Ex C. rewrite Ex, (proj2 Mr C) in Q. discriminate Q.
  + intros _. exact Ls.
Qed.

End BvPow2.

(** * The kernels *)

Theorem bv_mul_pow2_step_1_correct : bv_mul_pow2_step_1_spec.
Proof.
intros emin prec Hp x c Fx Fc [n Hc]. subst c.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
unfold bv_mul_pow2_step_1. cbv beta iota zeta.
rewrite Rplus_0_r, (up_ball_mul_pow2_1_0_eq emin prec).
unfold eta, u. rewrite (threshold_N emin prec).
destruct (step_mask_1 emin prec x n Fx) as [M E].
split. apply generic_format_round; auto with typeclass_instances.
split. reflexivity.
split. replace (1 / 2 * pow2 emin) with (/ 2 * pow2 emin) by field.
  exact (scale_error emin prec x n Fx).
split. exact E. exact M.
Qed.

Theorem bv_mul_pow2_step_2_correct : bv_mul_pow2_step_2_spec.
Proof.
intros emin prec Hp x0 x1 c Hn Fc [n Hc]. subst c.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
assert (F0 : fmt emin prec x0) by apply Hn.
assert (F1 : fmt emin prec x1) by apply Hn.
unfold bv_mul_pow2_step_2. cbv zeta. rewrite 2!Rplus_0_r, (up_ball_mul_pow2_1_0_eq emin prec).
unfold eta, u. rewrite (threshold_N emin prec).
generalize (mul_pow2_2_facts emin prec Hp x0 x1 n Hn) (step_mask_2 emin prec x0 x1 n Hn).
cbv zeta. unfold RN.
set (h := round radix2 (FLT_exp emin prec) (Znearest tie_even) (x0 * pow2 n)).
set (l := round radix2 (FLT_exp emin prec) (Znearest tie_even) (x1 * pow2 n)).
destruct (fast_two_sum emin prec tie_even h l) as [z0 z1]. cbn [fst snd].
intros [Nz [Sz Bz]] M. cbv beta iota.
split. exact Nz.
split. rewrite Rmult_1_l. exact Bz.
split; [|exact M].
intros [C0 C1]. rewrite Sz.
destruct (step_mask_1 emin prec x0 n F0) as [_ E0].
destruct (step_mask_1 emin prec x1 n F1) as [_ E1].
unfold h, l. rewrite (E0 C0), (E1 C1). ring.
Qed.

Theorem bv_mul_pow2_radius_correct : bv_mul_pow2_radius_spec.
Proof.
intros emin prec Hp m rx c ex Fm Frx Fc Pm Prx [n Hc]. subst c. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
destruct (radius_facts emin prec m ex rx n Frx Prx) as [F [L [E U]]].
unfold eta, u. rewrite (threshold_N emin prec).
split. exact F. split. exact L. split.
- intros [Ex C]. exact (E Ex C).
- exact U.
Qed.

(** * The folds *)

(* The ball of the exact center c x with radius c rx is c times the ball of x with radius rx. *)
Lemma pow2_ball_image :
  forall x rx v n, Rabs (v - x * pow2 n) <= rx * pow2 n ->
  exists x_, Rabs (x_ - x) <= rx /\ v = x_ * pow2 n.
Proof.
intros x rx v n H. exists (v * pow2 (- n)). split.
- replace (v * pow2 (- n) - x) with ((v - x * pow2 n) * pow2 (- n))
    by (rewrite Rmult_minus_distr_r, scale_back; reflexivity).
  rewrite Rabs_mult, (Rabs_pos_eq (pow2 (- n))) by apply bpow_ge_0.
  apply Rle_trans with (rx * pow2 n * pow2 (- n)).
  + apply Rmult_le_compat_r; [apply bpow_ge_0|exact H].
  + rewrite scale_back. apply Rle_refl.
- rewrite Rmult_assoc, <- bpow_plus. replace (- n + n)%Z with 0%Z by ring. simpl. ring.
Qed.

(* A member scaled, against a center within err of c x and exact under its mask: within the
   radius when the radius is at least c rx, with every mask true, or c rx + err otherwise. *)
Lemma pow2_member :
  forall (x z rx r err : R) (n : Z) (e ex : bool),
  0 <= rx -> Rabs (z - x * pow2 n) <= err ->
  (e = true -> z = x * pow2 n) -> (ex = true -> e = true) ->
  rx * pow2 n <= r -> (ex = false -> rx * pow2 n + err <= r) ->
  forall x_, Rabs (x_ - x) <= rx -> Rabs (x_ * pow2 n - z) <= r.
Proof.
intros x z rx r err n e ex Prx Dz Ez Ee Lr Ur x_ Hx.
assert (P : 0 < pow2 n) by apply bpow_gt_0.
assert (Hx' : Rabs (x_ * pow2 n - x * pow2 n) <= rx * pow2 n).
{ replace (x_ * pow2 n - x * pow2 n) with ((x_ - x) * pow2 n) by ring.
  rewrite Rabs_mult, (Rabs_pos_eq (pow2 n)) by lra. apply Rmult_le_compat_r; lra. }
destruct ex.
- rewrite (Ez (Ee eq_refl)). lra.
- specialize (Ur eq_refl). apply Rabs_le_inv in Dz, Hx'. apply Rabs_le. lra.
Qed.

Theorem bv_mul_pow2_1_correct : bv_mul_pow2_1_spec.
Proof.
intros emin prec Hp rx c xs Frx Prx Fc [n Hc] H. subst c. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
unfold bv_mul_pow2_1_radius.
set (ex := bv_mul_pow2_1_exact emin prec tie_even (pow2 n) xs).
set (m := fst _).
destruct (radius_facts emin prec m ex rx n Frx Prx) as [Fr [Lr [Er Ur]]].
set (r := bv_mul_pow2_radius emin prec tie_even m ex rx (pow2 n)) in *.
assert (Fe : forall x, In x xs ->
  let '(z, e) := bv_mul_pow2_step_1 emin prec tie_even x (pow2 n) in
  fmt emin prec z /\ Rabs (z - x * pow2 n) <= / 2 * pow2 emin /\
  (e = true -> z = x * pow2 n) /\ (e = true <-> cond emin prec (x * pow2 n)) /\
  (ex = true -> e = true)).
{ intros x Hin. pose proof (proj1 (Forall_forall _ xs) H x Hin) as Fx.
  assert (Ee : ex = true -> snd (bv_mul_pow2_step_1 emin prec tie_even x (pow2 n)) = true).
  { intros Ex. unfold ex, bv_mul_pow2_1_exact in Ex. rewrite forallb_forall in Ex.
    exact (Ex x Hin). }
  revert Ee. unfold bv_mul_pow2_step_1. cbv beta iota zeta. cbn [snd].
  rewrite Rplus_0_r, (up_ball_mul_pow2_1_0_eq emin prec). intros Ee.
  destruct (step_mask_1 emin prec x n Fx) as [M E].
  split. apply generic_format_round; auto with typeclass_instances.
  split. exact (scale_error emin prec x n Fx).
  split. intros T. exact (E (proj1 M T)).
  split. exact M. exact Ee. }
split. exact Fr. split.
- unfold bv_mul_pow2_1_map. apply Forall2_map_r. apply Forall_forall. intros x Hin.
  generalize (Fe x Hin). unfold bv_mul_pow2_1_step.
  destruct (bv_mul_pow2_step_1 emin prec tie_even x (pow2 n)) as [z e]. cbn [fst].
  intros [Fz [Dz [Ez [_ Ee]]]]. cbv zeta. split. exact Fz.
  apply (pow2_member x z rx r (/ 2 * pow2 emin) n e ex Prx Dz Ez Ee Lr).
  intros F. specialize (Ur F). generalize (bpow_gt_0 radix2 emin). lra.
- unfold eta, u. rewrite (threshold_N emin prec). intros Cr Cx.
  assert (Ex : ex = true).
  { unfold ex, bv_mul_pow2_1_exact. apply forallb_forall. intros x Hin.
    generalize (Fe x Hin). unfold bv_mul_pow2_1_step.
    destruct (bv_mul_pow2_step_1 emin prec tie_even x (pow2 n)) as [z e]. cbn [snd].
    intros [_ [_ [_ [M _]]]]. apply M. exact (proj1 (Forall_forall _ xs) Cx x Hin). }
  specialize (Er Ex Cr).
  unfold bv_mul_pow2_1_map. apply Forall2_map_r. apply Forall_forall. intros x Hin.
  generalize (Fe x Hin). unfold bv_mul_pow2_1_step.
  destruct (bv_mul_pow2_step_1 emin prec tie_even x (pow2 n)) as [z e]. cbn [fst].
  intros [_ [_ [Ez [_ Ee]]]]. cbv zeta. intros v_ Hv. rewrite (Ez (Ee Ex)), Er in Hv.
  exact (pow2_ball_image x rx v_ n Hv).
Qed.

Theorem bv_mul_pow2_2_correct : bv_mul_pow2_2_spec.
Proof.
intros emin prec Hp rx c xs Frx Prx Fc [n Hc] H. subst c. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
unfold bv_mul_pow2_2_radius.
set (ex := bv_mul_pow2_2_exact emin prec tie_even (pow2 n) xs).
set (m := fst _).
destruct (radius_facts emin prec m ex rx n Frx Prx) as [Fr [Lr [Er Ur]]].
set (r := bv_mul_pow2_radius emin prec tie_even m ex rx (pow2 n)) in *.
assert (Fe : forall x0 x1, In (x0, x1) xs ->
  let '(z0, z1, e) := bv_mul_pow2_step_2 emin prec tie_even x0 x1 (pow2 n) in
  normalized_2 emin prec z0 z1 /\ Rabs (z0 + z1 - (x0 + x1) * pow2 n) <= pow2 emin /\
  (e = true -> z0 + z1 = (x0 + x1) * pow2 n) /\
  (e = true <-> cond emin prec (x0 * pow2 n) /\ cond emin prec (x1 * pow2 n)) /\
  (ex = true -> e = true)).
{ intros x0 x1 Hin. pose proof (proj1 (Forall_forall _ xs) H (x0, x1) Hin) as Hn.
  cbn [fst snd] in Hn.
  assert (F0 : fmt emin prec x0) by apply Hn.
  assert (F1 : fmt emin prec x1) by apply Hn.
  assert (Ee : ex = true -> snd (bv_mul_pow2_step_2 emin prec tie_even x0 x1 (pow2 n)) = true).
  { intros Ex. unfold ex, bv_mul_pow2_2_exact in Ex. rewrite forallb_forall in Ex.
    exact (Ex (x0, x1) Hin). }
  revert Ee. unfold bv_mul_pow2_step_2. cbv zeta. rewrite 2!Rplus_0_r.
  generalize (mul_pow2_2_facts emin prec Hp x0 x1 n Hn) (step_mask_2 emin prec x0 x1 n Hn).
  cbv zeta. unfold RN.
  set (h := round radix2 (FLT_exp emin prec) (Znearest tie_even) (x0 * pow2 n)).
  set (l := round radix2 (FLT_exp emin prec) (Znearest tie_even) (x1 * pow2 n)).
  destruct (fast_two_sum emin prec tie_even h l) as [z0 z1]. cbn [fst snd].
  intros [Nz [Sz Bz]] M. cbv beta iota. rewrite (up_ball_mul_pow2_1_0_eq emin prec).
  intros Ee.
  split. exact Nz. split. exact Bz. split; [|split; [exact M|exact Ee]].
  intros T. destruct (proj1 M T) as [C0 C1]. rewrite Sz.
  destruct (step_mask_1 emin prec x0 n F0) as [_ E0].
  destruct (step_mask_1 emin prec x1 n F1) as [_ E1].
  unfold h, l. rewrite (E0 C0), (E1 C1). ring. }
split. exact Fr. split.
- unfold bv_mul_pow2_2_map. apply Forall2_map_r. apply Forall_forall. intros [x0 x1] Hin.
  generalize (Fe x0 x1 Hin). unfold bv_mul_pow2_2_step. cbn [fst snd].
  destruct (bv_mul_pow2_step_2 emin prec tie_even x0 x1 (pow2 n)) as [[z0 z1] e]. cbn [fst].
  intros [Nz [Dz [Ez [_ Ee]]]]. cbv beta iota. split. exact Nz.
  exact (pow2_member (x0 + x1) (z0 + z1) rx r (pow2 emin) n e ex Prx Dz Ez Ee Lr Ur).
- unfold eta, u. rewrite (threshold_N emin prec). intros Cr Cx.
  assert (Ex : ex = true).
  { unfold ex, bv_mul_pow2_2_exact. apply forallb_forall. intros [x0 x1] Hin.
    generalize (Fe x0 x1 Hin). unfold bv_mul_pow2_2_step. cbn [fst snd].
    destruct (bv_mul_pow2_step_2 emin prec tie_even x0 x1 (pow2 n)) as [[z0 z1] e]. cbn [snd].
    intros [_ [_ [_ [M _]]]]. apply M. exact (proj1 (Forall_forall _ xs) Cx (x0, x1) Hin). }
  specialize (Er Ex Cr).
  unfold bv_mul_pow2_2_map. apply Forall2_map_r. apply Forall_forall. intros [x0 x1] Hin.
  generalize (Fe x0 x1 Hin). unfold bv_mul_pow2_2_step. cbn [fst snd].
  destruct (bv_mul_pow2_step_2 emin prec tie_even x0 x1 (pow2 n)) as [[z0 z1] e]. cbn [fst].
  intros [_ [_ [Ez [_ Ee]]]]. cbv beta iota. intros v_ Hv. rewrite (Ez (Ee Ex)), Er in Hv.
  exact (pow2_ball_image (x0 + x1) rx v_ n Hv).
Qed.
