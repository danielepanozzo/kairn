(* Bounds of two limbs, in the real model (no overflow): a 2-limb number that is certainly
   below, or above, the exact sum or product of two 2-limb numbers, and close to it
   (docs/developer/design/milestone2.md, "Interval kernels", "Bounds of two limbs").

       add_ball_2_2(x, y) -> (z, d)               mul_ball_2_2(x, y) -> (z, d)
         (z0, z1) = add_2_2(x0, x1, y0, y1)         (z0, z1) = mul_2_2(x0, x1, y0, y1)
         az       = abs(z0)                         az       = abs(z0)
         t        = prod(az, const E)               t        = prod(az, const E)
         d        = fma(t, const G, const H)        d        = fma(t, const G, const H)

       add_down_2_2(x, y) -> l                    add_up_2_2(x, y) -> h
         (z0, z1, d) = add_ball_2_2(x, y)           (z0, z1, d) = add_ball_2_2(x, y)
         zd          = eq(z0, 0)                    zd          = eq(z0, 0)
         dd          = select(zd, 0, d)             dd          = select(zd, 0, d)
         nz          = neg(z1)                      w           = add_up_1(z1, dd)
         t           = add_up_1(dd, nz)             (h0, h1)    = two_sum_ord(z0, w)
         w           = neg(t)
         (l0, l1)    = two_sum_ord(z0, w)

       mul_dir_2_2(x, y) -> (l, h)                sub_down_2_2(x, y), sub_up_2_2(x, y):
         (z0, z1, d) = mul_ball_2_2(x, y)           neg_2(y), then the sum
         nz          = neg(z1)
         t           = add_up_1(d, nz)
         wl          = neg(t)
         wu          = add_up_1(z1, d)
         (l0, l1)    = two_sum_ord(z0, wl)
         (h0, h1)    = two_sum_ord(z0, wu)

   Notation: F is the format (precision prec, gradual underflow, smallest positive number
   eta = 2^emin, no largest number); u = 2^-prec; RN, RD, RU are the roundings to nearest
   (ties to even), down and up; N = eta / (2 u) is the smallest normal number. x and y are
   normalized 2-limb numbers and v is the exact x + y, x - y or x y. E, G, H are the three
   constants of ball_add_2, and of ball_mul_2 for the product, as the format rounds them
   (proofs/gen/Model.v); rel and tiny are the two constants of the bound rel |v| + tiny of
   the center's kernel: 3 u^2 / (1 - 4 u) and 0 for add_2_2, 4 u^2 and (3/2) eta for
   mul_2_2.

   The kernels are the generated models of proofs/gen/Model.v, and the seven theorems
   K_correct establish their generated statements (proofs/gen/Statements.v):
   add_ball_2_2_correct, mul_ball_2_2_correct, add_down_2_2_correct, add_up_2_2_correct,
   sub_down_2_2_correct, sub_up_2_2_correct and mul_dir_2_2_correct.

   The second limb of a lower bound. The design page writes it w = sub_down_1(z1, b),
   which is RD(z1 - b), with b the bound subtracted (dd in the sums, d in the product).
   The listings above compute it as minus the rounding up of b - z1, in three lines,
   because the generator refuses the negation of a fused result, directly or through a
   select (gen/README.md, "The rules"), and sub_down_1 negates its second operand. The
   two are the same number: -RU(b - z1) = RD(z1 - b) (RD_as_opp_RU), so the three lines
   return what sub_down_1(z1, b) returns (sub_down_1_as_add_up_1), and everything below
   is stated of the generated listings.

   What is proved.

   1. add_ball_2_2 and mul_ball_2_2 (add_ball_2_2_correct, mul_ball_2_2_correct), from
      precision 3 and 4: d is a number of F, z is normalized, z has the error bound of
      add_2_2 or of mul_2_2, and |v - z| <= d. The listing is ball_add_2, or ball_mul_2,
      with radii zero (add_ball_2_2_eq, mul_ball_2_2_eq): the operations on the radii
      round zero. So the statements are ball_add_2_correct and ball_mul_2_correct, and
      add_2_2_correct, mul_2_2_correct.

   2. The directed sums and differences, with the rule of the zero sum, from precision 3
      (add_down_2_2_values, add_up_2_2_values; the same four facts for sub_down_2_2 and
      sub_up_2_2 in sub_down_2_2_values and sub_up_2_2_values), in the values of the
      kernel:
      - l and h are normalized, and l <= v <= h;
      - the computed sum z is zero exactly when v = 0, and then l = h = 0, limb by limb;
      - v - l <= 2 dd + max(eta, 2 u (u |z0| + dd)), and the same for h - v, where dd is
        the bound that the listing subtracts: d, or 0 when z0 = 0.
      And mul_dir_2_2, from precision 4, without the rule of the zero
      (mul_dir_2_2_values): the same with d in place of dd.

   3. The closed form (the `outward` claim), the first upper bound of a radius proved
      here: v - l <= A |v| + B and h - v <= A |v| + B, with

          A = (2 (1 + u)^3 G E + 2 u^2) (1 + rel) / (1 - u)
          B = 2 (1 + u)^2 (G eta / 2 + H) + eta + (2 (1 + u)^3 G E + 2 u^2) / (1 - u) tiny

      (outward_rel and outward_abs; add_down_2_2_outward and the four others state it
      with the constants of each kernel, add_outward_rel and the like: normalized, on its
      side of v, within A |v| + B of it, and equal to v when v = 0 for the sums and the
      differences. The generated statements print the same constants unfolded, so each
      K_correct is the theorem K_outward.)

   How the closed form is obtained. A rounding to nearest of x >= 0 is at most
   (1 + u) x + eta / 2 (rnd_upper), and at most (1 + u) x when x is at least the smallest
   normal number N (rnd_upper_normal). The inner rounding, t = RN(|z0| E), may be in the
   underflow range and pays the eta / 2. The outer one, d = RN(t G + H), does not: its
   argument is at least H, and H >= N because N is added to it before it is rounded up
   (consts_add, consts_mul). So

       d <= (1 + u)^2 G E |z0| + (1 + u) (G eta / 2 + H)                 (radius_upper)

   and this is what the displayed B assumes. Then |z0| <= |z| / (1 - u) for a normalized
   pair, |z| <= (1 + rel) |v| + tiny, and max(eta, c) <= eta + c (outward_closed). Nothing
   in it uses that the constants are close to their expressions: only E >= 0, G >= 0 and
   H >= N. *)
From Stdlib Require Import Reals ZArith Lia Lra Psatz.
From Flocq Require Import Core Relative.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Normalized Add22 Mul22 OneLimb Ball2 EFT Convert DirectedSum.
Open Scope R_scope.

(** * One rounding, from above, and the gap of a directed rounding *)

Section Rounding.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation uu := (u prec).

Let u0 : 0 < uu.
Proof. apply bpow_gt_0. Qed.
Let e0 : 0 < eta emin.
Proof. apply bpow_gt_0. Qed.

Lemma u_lt_1 : uu < 1.
Proof.
unfold u. change 1 with (bpow radix2 0). apply bpow_lt.
generalize prec_gt_0_. unfold Prec_gt_0. lia.
Qed.

(* A rounding to nearest of x >= 0 is at most (1 + u) x + eta / 2. *)
Lemma rnd_upper : forall x : R, 0 <= x -> rnd x <= (1 + uu) * x + eta emin / 2.
Proof.
intros x Hx.
destruct (relative_error_N_FLT'_ex radix2 emin prec prec_gt_0_ tie_even x)
  as [eps [et [He [Ht [_ Hr]]]]].
rewrite u_ro_eq in He. rewrite Hr.
apply Rabs_le_inv in He. apply Rabs_le_inv in Ht.
assert (D : uu / (1 + uu) <= uu).
{ apply Rmult_le_reg_r with (1 + uu); [lra|].
  unfold Rdiv. rewrite Rmult_assoc, Rinv_l by lra. nra. }
assert (K : x * eps <= x * uu) by (apply Rmult_le_compat_l; lra).
unfold eta. lra.
Qed.

(* In the normal range the rounding loses nothing absolute: for x at least the smallest
   normal number, RN(x) <= (1 + u) x. *)
Lemma rnd_upper_normal :
  forall x : R, bpow radix2 (emin + prec - 1) <= x -> rnd x <= (1 + uu) * x.
Proof.
intros x Hx.
assert (P : 0 < bpow radix2 (emin + prec - 1)) by apply bpow_gt_0.
assert (Hx' : bpow radix2 (emin + prec - 1) <= Rabs x) by (rewrite Rabs_pos_eq; lra).
generalize (relative_error_N_FLT radix2 emin prec prec_gt_0_ tie_even x Hx').
rewrite (Rabs_pos_eq x) by lra.
replace (/ 2 * bpow radix2 (- prec + 1)) with uu
  by (unfold u; rewrite bpow_plus, pow2_1; field).
intros K. apply Rabs_le_inv in K. lra.
Qed.

(* The gap of the format at t is at most max(eta, 2 u |t|). *)
Lemma ulp_le_max :
  forall t : R, ulp radix2 fexp t <= Rmax (eta emin) (2 * uu * Rabs t).
Proof.
intros t. destruct (Rle_or_lt (bpow radix2 (emin + prec - 1)) (Rabs t)) as [H|H].
- apply Rle_trans with (2 := Rmax_r _ _).
  apply Rle_trans with (Rabs t * bpow radix2 (1 - prec)); [now apply ulp_FLT_le|].
  right. unfold u. replace (1 - prec)%Z with (1 + - prec)%Z by ring.
  rewrite bpow_plus, pow2_1. ring.
- apply Rle_trans with (2 := Rmax_l _ _). right. unfold eta.
  apply ulp_FLT_small; auto with typeclass_instances.
  apply Rlt_le_trans with (1 := H). apply bpow_le. lia.
Qed.

(* A directed rounding is within the gap of the format: RD(t) <= t <= RU(t), each within
   max(eta, 2 u |t|) of t. *)
Lemma rd_gap :
  forall t : R, 0 <= t - RD emin prec t <= Rmax (eta emin) (2 * uu * Rabs t).
Proof.
intros t. unfold RD.
destruct (round_DN_pt radix2 fexp t) as [_ [L _]].
generalize (error_le_ulp radix2 fexp Zfloor t) (ulp_le_max t). intros E M.
apply Rabs_le_inv in E. lra.
Qed.

Lemma ru_gap :
  forall t : R, 0 <= RU emin prec t - t <= Rmax (eta emin) (2 * uu * Rabs t).
Proof.
intros t. unfold RU.
destruct (round_UP_pt radix2 fexp t) as [_ [L _]].
generalize (error_le_ulp radix2 fexp Zceil t) (ulp_le_max t). intros E M.
apply Rabs_le_inv in E. lra.
Qed.

(** * The closed form *)

(* The radius of add_ball_2_2 and of mul_ball_2_2, from above. With az >= 0 the magnitude
   of the leading limb, E >= 0, G >= 0 and H at least the smallest normal number:
   RN(RN(az E) G + H) <= (1 + u)^2 G E az + (1 + u) (G eta / 2 + H). The inner rounding
   pays eta / 2; the outer one is of a number that is at least H, in the normal range. *)
Lemma radius_upper :
  forall az E G H : R, 0 <= az -> 0 <= E -> 0 <= G ->
  bpow radix2 (emin + prec - 1) <= H ->
  rnd (rnd (az * E + 0) * G + H)
  <= (1 + uu) ^ 2 * G * E * az + (1 + uu) * (/ 2 * G * eta emin + H).
Proof.
intros az E G H Haz HE HG HH. rewrite Rplus_0_r.
assert (P0 : 0 <= az * E) by now apply Rmult_le_pos.
assert (T0 := rnd_ge_0 emin prec (az * E) P0).
assert (T1 := rnd_upper (az * E) P0).
set (t := rnd (az * E)) in *.
assert (TG : 0 <= t * G) by now apply Rmult_le_pos.
assert (S : bpow radix2 (emin + prec - 1) <= t * G + H) by lra.
apply Rle_trans with (1 := rnd_upper_normal _ S).
replace ((1 + uu) ^ 2 * G * E * az + (1 + uu) * (/ 2 * G * eta emin + H))
  with ((1 + uu) * (((1 + uu) * (az * E) + eta emin / 2) * G + H)) by (unfold Rdiv; ring).
apply Rmult_le_compat_l; [lra|].
assert (K : t * G <= ((1 + uu) * (az * E) + eta emin / 2) * G)
  by (apply Rmult_le_compat_r; assumption).
lra.
Qed.

(* The two constants of the closed form: the outward move is at most
   outward_rel |v| + outward_abs. E, G, H are the constants of the radius, and rel, tiny
   those of the bound rel |v| + tiny of the center's kernel. *)
Definition outward_rel (E G rel : R) : R :=
  (2 * (1 + uu) ^ 3 * G * E + 2 * uu ^ 2) * (1 + rel) / (1 - uu).

Definition outward_abs (E G H tiny : R) : R :=
  2 * (1 + uu) ^ 2 * (/ 2 * G * eta emin + H) + eta emin
  + (2 * (1 + uu) ^ 3 * G * E + 2 * uu ^ 2) / (1 - uu) * tiny.

(* From the values of the kernel to the exact value. z is the normalized result of the
   center's kernel, within rel |v| + tiny of v; d is the radius that the listing computes
   from z0, and b, with 0 <= b <= d, the bound that it subtracts or adds. Then the bound
   in the kernel's values, 2 b + max(eta, 2 u (u |z0| + b)), is at most
   outward_rel |v| + outward_abs. *)
Lemma outward_closed :
  forall z0 z1 v b d E G H rel tiny : R,
  normalized_2 emin prec z0 z1 ->
  0 <= rel -> 0 <= tiny -> 0 <= E -> 0 <= G ->
  bpow radix2 (emin + prec - 1) <= H ->
  Rabs ((z0 + z1) - v) <= rel * Rabs v + tiny ->
  d = rnd (rnd (Rabs z0 * E + 0) * G + H) ->
  0 <= b <= d ->
  2 * b + Rmax (eta emin) (2 * uu * (uu * Rabs z0 + b))
  <= outward_rel E G rel * Rabs v + outward_abs E G H tiny.
Proof.
intros z0 z1 v b d E G H rel tiny Nz Hrel Htiny HE HG HH Herr Hd Hb.
assert (U1 := u_lt_1).
assert (A0 : 0 <= Rabs z0) by apply Rabs_pos.
assert (V0 : 0 <= Rabs v) by apply Rabs_pos.
assert (D1 := radius_upper (Rabs z0) E G H A0 HE HG HH). rewrite <- Hd in D1.
remember ((1 + uu) ^ 2 * G * E * Rabs z0 + (1 + uu) * (/ 2 * G * eta emin + H)) as Dn eqn:EDn.
assert (X0 : 0 <= 2 * uu * (uu * Rabs z0 + b)).
{ apply Rmult_le_pos; [lra|]. generalize (Rmult_le_pos uu (Rabs z0) (Rlt_le _ _ u0) A0). lra. }
assert (M : Rmax (eta emin) (2 * uu * (uu * Rabs z0 + b))
            <= eta emin + 2 * uu * (uu * Rabs z0 + b)) by (apply Rmax_lub; lra).
(* the leading limb, from the exact value *)
assert (N1 := normalized_2_tail_rel emin prec z0 z1 Nz).
assert (N2 : (1 - uu) * Rabs z0 <= Rabs (z0 + z1)).
{ generalize (Rabs_triang (z0 + z1) (- z1)).
  replace (z0 + z1 + - z1) with z0 by ring. rewrite Rabs_Ropp. lra. }
assert (N3 : Rabs (z0 + z1) <= (1 + rel) * Rabs v + tiny).
{ generalize (Rabs_triang v (z0 + z1 - v)).
  replace (v + (z0 + z1 - v)) with (z0 + z1) by ring. lra. }
assert (N4 : Rabs z0 <= ((1 + rel) * Rabs v + tiny) / (1 - uu)).
{ apply Rmult_le_reg_r with (1 - uu); [lra|].
  unfold Rdiv. rewrite Rmult_assoc, Rinv_l by lra. lra. }
remember (2 * (1 + uu) ^ 3 * G * E + 2 * uu ^ 2) as C eqn:EC.
assert (C0 : 0 <= C).
{ rewrite EC. apply Rplus_le_le_0_compat.
  - apply Rmult_le_pos; [apply Rmult_le_pos; [apply Rmult_le_pos; [lra|]|exact HG]|exact HE].
    apply pow_le. lra.
  - apply Rmult_le_pos; [lra|]. apply pow_le. lra. }
assert (K1 : 2 * (1 + uu) * b <= 2 * (1 + uu) * Dn) by (apply Rmult_le_compat_l; lra).
assert (K2 : C * Rabs z0 <= C * (((1 + rel) * Rabs v + tiny) / (1 - uu)))
  by (apply Rmult_le_compat_l; assumption).
apply Rle_trans with (C * Rabs z0 + 2 * (1 + uu) ^ 2 * (/ 2 * G * eta emin + H) + eta emin).
- apply Rle_trans with (2 * (1 + uu) * Dn + 2 * uu ^ 2 * Rabs z0 + eta emin).
  + replace (2 * b + Rmax (eta emin) (2 * uu * (uu * Rabs z0 + b)))
      with (2 * (1 + uu) * b + 2 * uu ^ 2 * Rabs z0
            + (Rmax (eta emin) (2 * uu * (uu * Rabs z0 + b)) - 2 * uu * (uu * Rabs z0 + b)))
      by ring.
    lra.
  + right. rewrite EDn, EC. ring.
- apply Rle_trans
    with (C * (((1 + rel) * Rabs v + tiny) / (1 - uu))
          + 2 * (1 + uu) ^ 2 * (/ 2 * G * eta emin + H) + eta emin); [lra|].
  right. unfold outward_rel, outward_abs. rewrite <- EC. field. lra.
Qed.

End Rounding.

(** * The constants of the two radii *)

(* E and G are nonnegative, and H is at least the smallest normal number N, which is
   added to its expression before it is rounded up. *)
Lemma consts_add :
  forall emin prec : Z, (3 <= prec)%Z ->
  0 <= Model.up_ball_add_2_0 emin prec /\ 0 <= Model.up_ball_add_1_1 emin prec /\
  bpow radix2 (emin + prec - 1) <= Model.up_ball_add_1_2 emin prec.
Proof.
intros emin prec Hp.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
generalize (bpow_gt_0 radix2 (- prec)). fold (u prec). intros U0.
assert (Hrel := rel_add_2_2 prec Hp).
rewrite e_add_2_eq, g_add_2_eq, h_add_2_eq.
split; [|split].
- assert (P : 0 <= uq (rel_add_2 prec) * (1 + u prec))
    by (apply Rmult_le_pos; [now apply uq_ge_0|lra]).
  exact (proj1 (RU_ge emin prec _ P)).
- exact (proj1 (RU_ge emin prec _ (pow_ge_0' prec 3))).
- rewrite <- nrm_eq.
  replace ((1 + u prec) * ((1 + u prec) ^ 2 * eta emin + eta emin / 2))
    with (h2 emin prec 0) by (unfold h2; ring).
  exact (RU_plus_ge_r emin prec _ (nrm emin prec) (h2_ge_0 emin prec 0 (Rle_refl 0))).
Qed.

Lemma consts_mul :
  forall emin prec : Z, (4 <= prec)%Z ->
  0 <= Model.up_ball_mul_2_0 emin prec /\ 0 <= Model.up_ball_mul_2_1 emin prec /\
  bpow radix2 (emin + prec - 1) <= Model.up_ball_mul_2_2 emin prec.
Proof.
intros emin prec Hp.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 4%Z; lia).
assert (Hrel := rel_mul_2_2 prec Hp).
assert (Htiny : 0 <= 3 / 2 * eta emin) by (apply eta_ge_0; lra).
rewrite e_mul_2_eq, g_mul_2_eq, h_mul_2_eq.
split; [|split].
- exact (proj1 (RU_ge emin prec _ (uq_ge_0 _ Hrel))).
- exact (proj1 (RU_ge emin prec _ (pow_ge_0' prec 6))).
- rewrite <- nrm_eq.
  exact (RU_plus_ge_r emin prec _ (nrm emin prec)
           (h4_ge_0 emin prec 5 _ (vq_ge_0 _ _ Hrel Htiny))).
Qed.

(* The constants A and B of the closed form, for the sum and the difference, and for the
   product: outward_rel and outward_abs on the constants of each kernel. *)
Definition add_outward_rel (emin prec : Z) : R :=
  outward_rel prec (Model.up_ball_add_2_0 emin prec) (Model.up_ball_add_1_1 emin prec)
    (3 / (1 - 4 * u prec) * u prec ^ 2).

Definition add_outward_abs (emin prec : Z) : R :=
  outward_abs emin prec (Model.up_ball_add_2_0 emin prec) (Model.up_ball_add_1_1 emin prec)
    (Model.up_ball_add_1_2 emin prec) 0.

Definition mul_outward_rel (emin prec : Z) : R :=
  outward_rel prec (Model.up_ball_mul_2_0 emin prec) (Model.up_ball_mul_2_1 emin prec)
    (4 * u prec ^ 2).

Definition mul_outward_abs (emin prec : Z) : R :=
  outward_abs emin prec (Model.up_ball_mul_2_0 emin prec) (Model.up_ball_mul_2_1 emin prec)
    (Model.up_ball_mul_2_2 emin prec) (3 / 2 * eta emin).

(** * add_ball_2_2 and mul_ball_2_2 *)

(* The listing is ball_add_2 with radii zero: s = RN(0 + 0) = 0. For every tie rule. *)
Lemma add_ball_2_2_eq :
  forall (emin prec : Z) {prec_gt_0_ : Prec_gt_0 prec} (choice : Z -> bool) (x0 x1 y0 y1 : R),
  add_ball_2_2 emin prec choice x0 x1 y0 y1
  = ball_add_2 emin prec choice x0 x1 0 y0 y1 0.
Proof.
intros emin prec Hp choice x0 x1 y0 y1. unfold add_ball_2_2, ball_add_2.
destruct (add_2_2 emin prec choice x0 x1 y0 y1) as [z0 z1]. cbv zeta.
rewrite (Rplus_0_l 0). rewrite round_0; auto with typeclass_instances.
Qed.

(* The listing is ball_mul_2 with radii zero: p, q and w are roundings of zero. *)
Lemma mul_ball_2_2_eq :
  forall (emin prec : Z) {prec_gt_0_ : Prec_gt_0 prec} (choice : Z -> bool) (x0 x1 y0 y1 : R),
  mul_ball_2_2 emin prec choice x0 x1 y0 y1
  = ball_mul_2 emin prec choice x0 x1 0 y0 y1 0.
Proof.
intros emin prec Hp choice x0 x1 y0 y1. unfold mul_ball_2_2, ball_mul_2.
destruct (mul_2_2 emin prec choice x0 x1 y0 y1) as [z0 z1]. cbv zeta.
rewrite !Rmult_0_r, !Rplus_0_l. rewrite !round_0; auto with typeclass_instances.
Qed.

(* add_ball_2_2, for normalized x and y, from precision 3: d is a number of the format, z
   is normalized, z is within 3 u^2 / (1 - 4 u) |x + y| of x + y (the bound of add_2_2),
   and |x + y - z| <= d. *)
Theorem add_ball_2_2_correct : add_ball_2_2_spec.
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
assert (F0 : fmt emin prec 0) by apply generic_format_0.
rewrite (add_ball_2_2_eq emin prec).
generalize (ball_add_2_correct emin prec Hp x0 x1 0 y0 y1 0 Nx F0 Ny F0 (Rle_refl 0) (Rle_refl 0)).
generalize (add_2_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
unfold ball_add_2.
destruct (add_2_2 emin prec tie_even x0 x1 y0 y1) as [z0 z1]. cbv beta iota zeta.
intros [Nz Hb] [Fd [_ Henc]].
split; [exact Fd|split; [exact Nz|split; [exact Hb|]]].
apply Henc; unfold Rminus; rewrite Rplus_opp_r, Rabs_R0; apply Rle_refl.
Qed.

(* mul_ball_2_2, for normalized x and y, from precision 4: d is a number of the format, z
   is normalized, z is within 4 u^2 |x y| + (3/2) eta of x y (the bound of mul_2_2), and
   |x y - z| <= d. *)
Theorem mul_ball_2_2_correct : mul_ball_2_2_spec.
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 4%Z; lia).
assert (F0 : fmt emin prec 0) by apply generic_format_0.
rewrite (mul_ball_2_2_eq emin prec).
generalize (ball_mul_2_correct emin prec Hp x0 x1 0 y0 y1 0 Nx F0 Ny F0 (Rle_refl 0) (Rle_refl 0)).
generalize (mul_2_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
unfold ball_mul_2.
destruct (mul_2_2 emin prec tie_even x0 x1 y0 y1) as [z0 z1]. cbv beta iota zeta.
intros [Nz Hb] [Fd [_ Henc]].
split; [exact Fd|split; [exact Nz|split; [exact Hb|]]].
apply Henc; unfold Rminus; rewrite Rplus_opp_r, Rabs_R0; apply Rle_refl.
Qed.

(** * One outward step *)

(* The rounding down of z - b is minus the rounding up of b - z: the form in which the
   listings compute the second limb of a lower bound, so that no fused result is
   negated. *)
Lemma RD_as_opp_RU :
  forall (emin prec : Z) (z b : R), - RU emin prec (b + - z) = RD emin prec (z - b).
Proof.
intros emin prec z b. unfold RU, RD.
replace (z - b) with (- (b + - z)) by ring.
now rewrite round_DN_opp.
Qed.

(* So the three lines nz = neg(z); t = add_up_1(b, nz); w = neg(t) return what
   sub_down_1(z, b) of the design page returns, for numbers z and b of the format. From
   precision 2. *)
Lemma sub_down_1_as_add_up_1 :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall z b : R, fmt emin prec z -> fmt emin prec b ->
  - Model.add_up_1 emin prec tie_even b (- z) = Model.sub_down_1 emin prec tie_even z b.
Proof.
intros emin prec Hp z b Fz Fb.
destruct (add_up_1_correct emin prec Hp b (- z) Fb (generic_format_opp _ _ _ Fz)) as [_ E1].
destruct (sub_down_1_correct emin prec Hp z b Fz Fb) as [_ E2].
rewrite E1, E2. apply RD_as_opp_RU.
Qed.

(* The last lines of a directed sum or product, below. z is a normalized pair within b
   of v, and b a nonnegative number of the format. Then w = -RU(b - z1) = RD(z1 - b),
   the pair returned by two_sum_ord(z0, w) is normalized, its value is z0 + w exactly, it
   is at most v, and v exceeds it by at most 2 b + max(eta, 2 u (u |z0| + b)). *)
Lemma outward_down :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall z0 z1 b v : R,
  normalized_2 emin prec z0 z1 -> fmt emin prec b -> 0 <= b ->
  Rabs ((z0 + z1) - v) <= b ->
  let l := Model.two_sum_ord emin prec tie_even z0
             (- Model.add_up_1 emin prec tie_even b (- z1)) in
  normalized_2 emin prec (fst l) (snd l) /\
  fst l + snd l = z0 + RD emin prec (z1 - b) /\
  fst l + snd l <= v /\
  v - (fst l + snd l) <= 2 * b + Rmax (eta emin) (2 * u prec * (u prec * Rabs z0 + b)).
Proof.
intros emin prec Hp z0 z1 b v Nz Fb Hb Herr. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
generalize (bpow_gt_0 radix2 (- prec)). fold (u prec). intros U0.
assert (T := normalized_2_tail_rel emin prec z0 z1 Nz).
destruct Nz as [Fz0 [Fz1 _]].
destruct (add_up_1_correct emin prec Hp b (- z1) Fb (generic_format_opp _ _ _ Fz1))
  as [Ft Et].
assert (Fw : fmt emin prec (- Model.add_up_1 emin prec tie_even b (- z1)))
  by (apply generic_format_opp; exact Ft).
assert (Ew : - Model.add_up_1 emin prec tie_even b (- z1) = RD emin prec (z1 - b))
  by (rewrite Et; apply RD_as_opp_RU).
revert Fw Ew. generalize (- Model.add_up_1 emin prec tie_even b (- z1)). intros w Fw Ew.
destruct (two_sum_ord_facts emin prec Hp z0 w Fz0 Fw) as [_ [Es Nl]].
revert Es Nl. generalize (Model.two_sum_ord emin prec tie_even z0 w). intros l Es Nl.
assert (G := rd_gap emin prec (z1 - b)).
assert (A1 : Rabs (z1 - b) <= u prec * Rabs z0 + b).
{ unfold Rminus. apply Rle_trans with (1 := Rabs_triang _ _).
  rewrite Rabs_Ropp, (Rabs_pos_eq b) by exact Hb. lra. }
assert (M : Rmax (eta emin) (2 * u prec * Rabs (z1 - b))
            <= Rmax (eta emin) (2 * u prec * (u prec * Rabs z0 + b))).
{ apply Rmax_lub; [apply Rmax_l|].
  apply Rle_trans with (2 := Rmax_r _ _). apply Rmult_le_compat_l; [lra|exact A1]. }
apply Rabs_le_inv in Herr.
split; [exact Nl|split; [now rewrite Es, Ew|split]]; rewrite Es, Ew; lra.
Qed.

(* The same above: w = RU(z1 + b), and the pair is at least v. *)
Lemma outward_up :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall z0 z1 b v : R,
  normalized_2 emin prec z0 z1 -> fmt emin prec b -> 0 <= b ->
  Rabs ((z0 + z1) - v) <= b ->
  let h := Model.two_sum_ord emin prec tie_even z0 (Model.add_up_1 emin prec tie_even z1 b) in
  normalized_2 emin prec (fst h) (snd h) /\
  fst h + snd h = z0 + RU emin prec (z1 + b) /\
  v <= fst h + snd h /\
  (fst h + snd h) - v <= 2 * b + Rmax (eta emin) (2 * u prec * (u prec * Rabs z0 + b)).
Proof.
intros emin prec Hp z0 z1 b v Nz Fb Hb Herr. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
generalize (bpow_gt_0 radix2 (- prec)). fold (u prec). intros U0.
assert (T := normalized_2_tail_rel emin prec z0 z1 Nz).
destruct Nz as [Fz0 [Fz1 _]].
destruct (add_up_1_correct emin prec Hp z1 b Fz1 Fb) as [Fw Ew].
revert Fw Ew. generalize (Model.add_up_1 emin prec tie_even z1 b). intros w Fw Ew.
destruct (two_sum_ord_facts emin prec Hp z0 w Fz0 Fw) as [_ [Es Nl]].
revert Es Nl. generalize (Model.two_sum_ord emin prec tie_even z0 w). intros h Es Nl.
assert (G := ru_gap emin prec (z1 + b)).
assert (A1 : Rabs (z1 + b) <= u prec * Rabs z0 + b).
{ apply Rle_trans with (1 := Rabs_triang _ _). rewrite (Rabs_pos_eq b) by exact Hb. lra. }
assert (M : Rmax (eta emin) (2 * u prec * Rabs (z1 + b))
            <= Rmax (eta emin) (2 * u prec * (u prec * Rabs z0 + b))).
{ apply Rmax_lub; [apply Rmax_l|].
  apply Rle_trans with (2 := Rmax_r _ _). apply Rmult_le_compat_l; [lra|exact A1]. }
apply Rabs_le_inv in Herr.
split; [exact Nl|split; [now rewrite Es, Ew|split]]; rewrite Es, Ew; lra.
Qed.

(** * The rule of the zero sum *)

(* The bound of add_2_2 is relative, with no underflow term, and its constant is below 1:
   a normalized z within 3 u^2 / (1 - 4 u) |v| of v is zero exactly when v is zero. From
   precision 3. *)
Lemma add_2_2_zero_sum :
  forall emin prec : Z, (3 <= prec)%Z ->
  forall z0 z1 v : R,
  normalized_2 emin prec z0 z1 ->
  Rabs ((z0 + z1) - v) <= (3 / (1 - (4 * u prec))) * u prec ^ 2 * Rabs v ->
  (z0 = 0 <-> v = 0) /\ (z0 = 0 -> z1 = 0).
Proof.
intros emin prec Hp z0 z1 v Nz Hb.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
assert (Hrel := rel_add_2_2 prec Hp).
assert (Z1 : z0 = 0 -> z1 = 0) by exact (normalized_2_zero emin prec z0 z1 Nz).
split; [split|exact Z1].
- intros Z0. rewrite Z0, (Z1 Z0) in Hb.
  replace (0 + 0 - v) with (- v) in Hb by ring. rewrite Rabs_Ropp in Hb.
  destruct (Req_dec v 0) as [E|E]; trivial. exfalso.
  assert (P := Rabs_pos_lt v E).
  assert (Q : 3 / (1 - 4 * u prec) * u prec ^ 2 * Rabs v < 1 * Rabs v)
    by (apply Rmult_lt_compat_r; lra).
  lra.
- intros V0. rewrite V0, Rabs_R0, Rmult_0_r in Hb.
  unfold Rminus in Hb. rewrite Ropp_0, Rplus_0_r in Hb.
  apply (normalized_2_value_zero emin prec z0 z1 Nz).
  destruct (Req_dec (z0 + z1) 0) as [E|E]; trivial. exfalso.
  assert (P := Rabs_pos_lt _ E). lra.
Qed.

(** * The bound that the listings subtract and add *)

(* add_ball_2_2 followed by the two lines of the rule of the zero sum. z is normalized;
   dd, which is d or 0 when z0 = 0, is a nonnegative number of the format and bounds the
   error of z; z0 = 0 exactly when x + y = 0, and then z1 = 0 and dd = 0; and the bound
   in the kernel's values is at most the closed form. From precision 3. *)
Lemma add_ball_dd :
  forall emin prec : Z, (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 ->
  normalized_2 emin prec y0 y1 ->
  let v := (x0 + x1) + (y0 + y1) in
  let '(z0, z1, d) := add_ball_2_2 emin prec tie_even x0 x1 y0 y1 in
  let dd := if Req_bool z0 0 then 0 else d in
  normalized_2 emin prec z0 z1 /\
  fmt emin prec dd /\
  0 <= dd /\
  Rabs ((z0 + z1) - v) <= dd /\
  (z0 = 0 <-> v = 0) /\
  (z0 = 0 -> z1 = 0 /\ dd = 0) /\
  2 * dd + Rmax (eta emin) (2 * u prec * (u prec * Rabs z0 + dd))
  <= add_outward_rel emin prec * Rabs v + add_outward_abs emin prec.
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
generalize (add_ball_2_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
unfold add_ball_2_2.
destruct (add_2_2 emin prec tie_even x0 x1 y0 y1) as [z0 z1]. cbv beta iota zeta.
set (v := x0 + x1 + (y0 + y1)).
set (d := round radix2 (FLT_exp emin prec) (Znearest tie_even)
            (round radix2 (FLT_exp emin prec) (Znearest tie_even)
               (Rabs z0 * up_ball_add_2_0 emin prec + 0)
             * up_ball_add_1_1 emin prec + up_ball_add_1_2 emin prec)).
intros [Fd [Nz [Hb Henc]]].
destruct (add_2_2_zero_sum emin prec Hp z0 z1 v Nz Hb) as [Zero Z1].
assert (D0 : 0 <= d) by (apply Rle_trans with (2 := Henc); apply Rabs_pos).
assert (Henc' : Rabs (z0 + z1 - v) <= d) by (rewrite Rabs_minus_sym; exact Henc).
destruct (consts_add emin prec Hp) as [E0 [G0 HN]].
assert (Hrel := rel_add_2_2 prec Hp).
assert (Hb' : Rabs (z0 + z1 - v) <= 3 / (1 - 4 * u prec) * u prec ^ 2 * Rabs v + 0)
  by (rewrite Rplus_0_r; exact Hb).
unfold add_outward_rel, add_outward_abs.
destruct (Req_bool_spec z0 0) as [Z0|Z0]; cbv beta iota.
- (* the computed sum is zero: so is the exact one, and the bound is zero *)
  assert (V0 := proj1 Zero Z0). assert (Z1' := Z1 Z0).
  split; [exact Nz|split; [apply generic_format_0|split; [apply Rle_refl|split]]].
  + rewrite Z0, Z1', V0. replace (0 + 0 - 0) with 0 by ring. rewrite Rabs_R0. apply Rle_refl.
  + split; [exact Zero|split; [intros _; now split|]].
    exact (outward_closed emin prec z0 z1 v 0 d _ _ _ _ 0 Nz (proj1 Hrel) (Rle_refl 0)
             E0 G0 HN Hb' eq_refl (conj (Rle_refl 0) D0)).
- split; [exact Nz|split; [exact Fd|split; [exact D0|split; [exact Henc'|]]]].
  split; [exact Zero|split; [intros K; elim (Z0 K)|]].
  exact (outward_closed emin prec z0 z1 v d d _ _ _ _ 0 Nz (proj1 Hrel) (Rle_refl 0)
           E0 G0 HN Hb' eq_refl (conj D0 (Rle_refl d))).
Qed.

(* mul_ball_2_2: z is normalized, d is a nonnegative number of the format and bounds the
   error of z, and the bound in the kernel's values is at most the closed form. From
   precision 4. *)
Lemma mul_ball_d :
  forall emin prec : Z, (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 ->
  normalized_2 emin prec y0 y1 ->
  let v := (x0 + x1) * (y0 + y1) in
  let '(z0, z1, d) := mul_ball_2_2 emin prec tie_even x0 x1 y0 y1 in
  normalized_2 emin prec z0 z1 /\
  fmt emin prec d /\
  0 <= d /\
  Rabs ((z0 + z1) - v) <= d /\
  2 * d + Rmax (eta emin) (2 * u prec * (u prec * Rabs z0 + d))
  <= mul_outward_rel emin prec * Rabs v + mul_outward_abs emin prec.
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 4%Z; lia).
generalize (mul_ball_2_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
unfold mul_ball_2_2.
destruct (mul_2_2 emin prec tie_even x0 x1 y0 y1) as [z0 z1]. cbv beta iota zeta.
set (v := (x0 + x1) * (y0 + y1)).
set (d := round radix2 (FLT_exp emin prec) (Znearest tie_even)
            (round radix2 (FLT_exp emin prec) (Znearest tie_even)
               (Rabs z0 * up_ball_mul_2_0 emin prec + 0)
             * up_ball_mul_2_1 emin prec + up_ball_mul_2_2 emin prec)).
intros [Fd [Nz [Hb Henc]]].
assert (D0 : 0 <= d) by (apply Rle_trans with (2 := Henc); apply Rabs_pos).
assert (Henc' : Rabs (z0 + z1 - v) <= d) by (rewrite Rabs_minus_sym; exact Henc).
destruct (consts_mul emin prec Hp) as [E0 [G0 HN]].
assert (Hrel := rel_mul_2_2 prec Hp).
assert (Htiny : 0 <= 3 / 2 * eta emin) by (apply eta_ge_0; lra).
unfold mul_outward_rel, mul_outward_abs.
split; [exact Nz|split; [exact Fd|split; [exact D0|split; [exact Henc'|]]]].
exact (outward_closed emin prec z0 z1 v d d _ _ _ _ _ Nz (proj1 Hrel) Htiny
         E0 G0 HN Hb eq_refl (conj D0 (Rle_refl d))).
Qed.

(** * add_down_2_2 and add_up_2_2 *)

(* add_down_2_2 in the values of the kernel, for normalized x and y, from precision 3,
   with v = x + y, (z0, z1, d) the result of add_ball_2_2 and dd the bound that the
   listing subtracts (d, or 0 when z0 = 0): l is normalized; l <= v; the computed sum is
   zero exactly when v = 0, and then both limbs of l are zero; v - l is at most
   2 dd + max(eta, 2 u (u |z0| + dd)); and that bound is at most A |v| + B. *)
Theorem add_down_2_2_values :
  forall emin prec : Z, (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 ->
  normalized_2 emin prec y0 y1 ->
  let '(z0, z1, d) := add_ball_2_2 emin prec tie_even x0 x1 y0 y1 in
  let dd := if Req_bool z0 0 then 0 else d in
  let '(l0, l1) := add_down_2_2 emin prec tie_even x0 x1 y0 y1 in
  normalized_2 emin prec l0 l1 /\
  (l0 + l1) <= ((x0 + x1) + (y0 + y1)) /\
  (z0 = 0 <-> ((x0 + x1) + (y0 + y1)) = 0) /\
  (((x0 + x1) + (y0 + y1)) = 0 -> l0 = 0 /\ l1 = 0) /\
  ((x0 + x1) + (y0 + y1)) - (l0 + l1)
  <= 2 * dd + Rmax (eta emin) (2 * u prec * (u prec * Rabs z0 + dd)) /\
  2 * dd + Rmax (eta emin) (2 * u prec * (u prec * Rabs z0 + dd))
  <= add_outward_rel emin prec * Rabs ((x0 + x1) + (y0 + y1)) + add_outward_abs emin prec.
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
assert (Hp2 : (2 <= prec)%Z) by lia.
generalize (add_ball_dd emin prec Hp x0 x1 y0 y1 Nx Ny). cbv zeta.
unfold add_down_2_2.
destruct (add_ball_2_2 emin prec tie_even x0 x1 y0 y1) as [[z0 z1] d].
cbv beta iota zeta.
set (v := x0 + x1 + (y0 + y1)). set (dd := if Req_bool z0 0 then 0 else d).
intros [Nz [Fdd [D0 [Herr [Zero [Z1 Closed]]]]]].
generalize (outward_down emin prec Hp2 z0 z1 dd v Nz Fdd D0 Herr). cbv zeta.
destruct (two_sum_ord emin prec tie_even z0 (- add_up_1 emin prec tie_even dd (- z1))) as [l0 l1].
cbn [fst snd]. intros [Nl [El [Lv Tight]]].
split; [exact Nl|split; [exact Lv|split; [exact Zero|split; [|split; [exact Tight|exact Closed]]]]].
intros V0. destruct (Z1 (proj2 Zero V0)) as [Ez1 Edd].
rewrite (proj2 Zero V0), Ez1, Edd in El.
replace (0 - 0) with 0 in El by ring. unfold RD in El.
rewrite round_0, Rplus_0_r in El by auto with typeclass_instances.
assert (L0 := proj1 (normalized_2_value_zero emin prec l0 l1 Nl) El).
split; [exact L0|lra].
Qed.

(* add_up_2_2, likewise: h is normalized; v <= h; when v = 0 both limbs of h are zero;
   h - v is at most 2 dd + max(eta, 2 u (u |z0| + dd)), which is at most A |v| + B. *)
Theorem add_up_2_2_values :
  forall emin prec : Z, (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 ->
  normalized_2 emin prec y0 y1 ->
  let '(z0, z1, d) := add_ball_2_2 emin prec tie_even x0 x1 y0 y1 in
  let dd := if Req_bool z0 0 then 0 else d in
  let '(h0, h1) := add_up_2_2 emin prec tie_even x0 x1 y0 y1 in
  normalized_2 emin prec h0 h1 /\
  ((x0 + x1) + (y0 + y1)) <= (h0 + h1) /\
  (z0 = 0 <-> ((x0 + x1) + (y0 + y1)) = 0) /\
  (((x0 + x1) + (y0 + y1)) = 0 -> h0 = 0 /\ h1 = 0) /\
  (h0 + h1) - ((x0 + x1) + (y0 + y1))
  <= 2 * dd + Rmax (eta emin) (2 * u prec * (u prec * Rabs z0 + dd)) /\
  2 * dd + Rmax (eta emin) (2 * u prec * (u prec * Rabs z0 + dd))
  <= add_outward_rel emin prec * Rabs ((x0 + x1) + (y0 + y1)) + add_outward_abs emin prec.
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
assert (Hp2 : (2 <= prec)%Z) by lia.
generalize (add_ball_dd emin prec Hp x0 x1 y0 y1 Nx Ny). cbv zeta.
unfold add_up_2_2.
destruct (add_ball_2_2 emin prec tie_even x0 x1 y0 y1) as [[z0 z1] d].
cbv beta iota zeta.
set (v := x0 + x1 + (y0 + y1)). set (dd := if Req_bool z0 0 then 0 else d).
intros [Nz [Fdd [D0 [Herr [Zero [Z1 Closed]]]]]].
generalize (outward_up emin prec Hp2 z0 z1 dd v Nz Fdd D0 Herr). cbv zeta.
destruct (two_sum_ord emin prec tie_even z0 (add_up_1 emin prec tie_even z1 dd)) as [h0 h1].
cbn [fst snd]. intros [Nh [Eh [Lv Tight]]].
split; [exact Nh|split; [exact Lv|split; [exact Zero|split; [|split; [exact Tight|exact Closed]]]]].
intros V0. destruct (Z1 (proj2 Zero V0)) as [Ez1 Edd].
rewrite (proj2 Zero V0), Ez1, Edd in Eh.
replace (0 + 0) with 0 in Eh by ring. unfold RU in Eh.
rewrite round_0, Rplus_0_r in Eh by auto with typeclass_instances.
assert (H0 := proj1 (normalized_2_value_zero emin prec h0 h1 Nh) Eh).
split; [exact H0|lra].
Qed.

(* add_down_2_2, the `outward` claim with the constants A and B by name, for normalized
   x and y, from precision 3: l is normalized, l <= x + y, |l - (x + y)| <= A |x + y| + B,
   and l is x + y when x + y = 0. *)
Theorem add_down_2_2_outward :
  forall emin prec : Z, (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 ->
  normalized_2 emin prec y0 y1 ->
  let '(l0, l1) := add_down_2_2 emin prec tie_even x0 x1 y0 y1 in
  normalized_2 emin prec l0 l1 /\
  (l0 + l1) <= ((x0 + x1) + (y0 + y1)) /\
  Rabs ((l0 + l1) - ((x0 + x1) + (y0 + y1))) <= add_outward_rel emin prec * Rabs ((x0 + x1) + (y0 + y1)) + add_outward_abs emin prec /\
  (((x0 + x1) + (y0 + y1)) = 0 -> (l0 + l1) = ((x0 + x1) + (y0 + y1))).
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny.
generalize (add_down_2_2_values emin prec Hp x0 x1 y0 y1 Nx Ny).
destruct (add_ball_2_2 emin prec tie_even x0 x1 y0 y1) as [[z0 z1] d]. cbv zeta.
destruct (add_down_2_2 emin prec tie_even x0 x1 y0 y1) as [l0 l1].
intros [Nl [Lv [_ [Zr [Tight Closed]]]]].
split; [exact Nl|split; [exact Lv|split]].
- rewrite Rabs_left1 by lra. lra.
- intros V0. destruct (Zr V0) as [L0 L1]. rewrite L0, L1, V0. ring.
Qed.

(* add_up_2_2, likewise: h is normalized, x + y <= h, |h - (x + y)| <= A |x + y| + B, and
   h is x + y when x + y = 0. *)
Theorem add_up_2_2_outward :
  forall emin prec : Z, (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 ->
  normalized_2 emin prec y0 y1 ->
  let '(h0, h1) := add_up_2_2 emin prec tie_even x0 x1 y0 y1 in
  normalized_2 emin prec h0 h1 /\
  ((x0 + x1) + (y0 + y1)) <= (h0 + h1) /\
  Rabs ((h0 + h1) - ((x0 + x1) + (y0 + y1))) <= add_outward_rel emin prec * Rabs ((x0 + x1) + (y0 + y1)) + add_outward_abs emin prec /\
  (((x0 + x1) + (y0 + y1)) = 0 -> (h0 + h1) = ((x0 + x1) + (y0 + y1))).
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny.
generalize (add_up_2_2_values emin prec Hp x0 x1 y0 y1 Nx Ny).
destruct (add_ball_2_2 emin prec tie_even x0 x1 y0 y1) as [[z0 z1] d]. cbv zeta.
destruct (add_up_2_2 emin prec tie_even x0 x1 y0 y1) as [h0 h1].
intros [Nh [Lv [_ [Zr [Tight Closed]]]]].
split; [exact Nh|split; [exact Lv|split]].
- rewrite Rabs_pos_eq by lra. lra.
- intros V0. destruct (Zr V0) as [H0 H1]. rewrite H0, H1, V0. ring.
Qed.

(** * sub_down_2_2 and sub_up_2_2 *)

(* The differences are the sums on x and -y, the limbs of y negated by neg_2: the same
   facts, in the values of the kernel (the add_ball_2_2 of x and -y), with v = x - y.
   From precision 3. *)
Theorem sub_down_2_2_values :
  forall emin prec : Z, (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 ->
  normalized_2 emin prec y0 y1 ->
  let '(z0, z1, d) := add_ball_2_2 emin prec tie_even x0 x1 (- y0) (- y1) in
  let dd := if Req_bool z0 0 then 0 else d in
  let '(l0, l1) := sub_down_2_2 emin prec tie_even x0 x1 y0 y1 in
  normalized_2 emin prec l0 l1 /\
  (l0 + l1) <= ((x0 + x1) - (y0 + y1)) /\
  (z0 = 0 <-> ((x0 + x1) - (y0 + y1)) = 0) /\
  (((x0 + x1) - (y0 + y1)) = 0 -> l0 = 0 /\ l1 = 0) /\
  ((x0 + x1) - (y0 + y1)) - (l0 + l1)
  <= 2 * dd + Rmax (eta emin) (2 * u prec * (u prec * Rabs z0 + dd)) /\
  2 * dd + Rmax (eta emin) (2 * u prec * (u prec * Rabs z0 + dd))
  <= add_outward_rel emin prec * Rabs ((x0 + x1) - (y0 + y1)) + add_outward_abs emin prec.
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny.
generalize (add_down_2_2_values emin prec Hp x0 x1 (- y0) (- y1) Nx
              (normalized_2_opp emin prec y0 y1 Ny)).
unfold sub_down_2_2, neg_2. cbv beta iota zeta.
destruct (add_ball_2_2 emin prec tie_even x0 x1 (- y0) (- y1)) as [[z0 z1] d].
destruct (add_down_2_2 emin prec tie_even x0 x1 (- y0) (- y1)) as [l0 l1].
replace (x0 + x1 + (- y0 + - y1)) with (x0 + x1 - (y0 + y1)) by ring. trivial.
Qed.

Theorem sub_up_2_2_values :
  forall emin prec : Z, (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 ->
  normalized_2 emin prec y0 y1 ->
  let '(z0, z1, d) := add_ball_2_2 emin prec tie_even x0 x1 (- y0) (- y1) in
  let dd := if Req_bool z0 0 then 0 else d in
  let '(h0, h1) := sub_up_2_2 emin prec tie_even x0 x1 y0 y1 in
  normalized_2 emin prec h0 h1 /\
  ((x0 + x1) - (y0 + y1)) <= (h0 + h1) /\
  (z0 = 0 <-> ((x0 + x1) - (y0 + y1)) = 0) /\
  (((x0 + x1) - (y0 + y1)) = 0 -> h0 = 0 /\ h1 = 0) /\
  (h0 + h1) - ((x0 + x1) - (y0 + y1))
  <= 2 * dd + Rmax (eta emin) (2 * u prec * (u prec * Rabs z0 + dd)) /\
  2 * dd + Rmax (eta emin) (2 * u prec * (u prec * Rabs z0 + dd))
  <= add_outward_rel emin prec * Rabs ((x0 + x1) - (y0 + y1)) + add_outward_abs emin prec.
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny.
generalize (add_up_2_2_values emin prec Hp x0 x1 (- y0) (- y1) Nx
              (normalized_2_opp emin prec y0 y1 Ny)).
unfold sub_up_2_2, neg_2. cbv beta iota zeta.
destruct (add_ball_2_2 emin prec tie_even x0 x1 (- y0) (- y1)) as [[z0 z1] d].
destruct (add_up_2_2 emin prec tie_even x0 x1 (- y0) (- y1)) as [h0 h1].
replace (x0 + x1 + (- y0 + - y1)) with (x0 + x1 - (y0 + y1)) by ring. trivial.
Qed.

(* The differences, with the constants A and B by name. *)
Theorem sub_down_2_2_outward :
  forall emin prec : Z, (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 ->
  normalized_2 emin prec y0 y1 ->
  let '(l0, l1) := sub_down_2_2 emin prec tie_even x0 x1 y0 y1 in
  normalized_2 emin prec l0 l1 /\
  (l0 + l1) <= ((x0 + x1) - (y0 + y1)) /\
  Rabs ((l0 + l1) - ((x0 + x1) - (y0 + y1))) <= add_outward_rel emin prec * Rabs ((x0 + x1) - (y0 + y1)) + add_outward_abs emin prec /\
  (((x0 + x1) - (y0 + y1)) = 0 -> (l0 + l1) = ((x0 + x1) - (y0 + y1))).
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny.
generalize (add_down_2_2_outward emin prec Hp x0 x1 (- y0) (- y1) Nx
              (normalized_2_opp emin prec y0 y1 Ny)).
unfold sub_down_2_2, neg_2. cbv beta iota zeta.
destruct (add_down_2_2 emin prec tie_even x0 x1 (- y0) (- y1)) as [l0 l1].
replace (x0 + x1 + (- y0 + - y1)) with (x0 + x1 - (y0 + y1)) by ring. trivial.
Qed.

Theorem sub_up_2_2_outward :
  forall emin prec : Z, (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 ->
  normalized_2 emin prec y0 y1 ->
  let '(h0, h1) := sub_up_2_2 emin prec tie_even x0 x1 y0 y1 in
  normalized_2 emin prec h0 h1 /\
  ((x0 + x1) - (y0 + y1)) <= (h0 + h1) /\
  Rabs ((h0 + h1) - ((x0 + x1) - (y0 + y1))) <= add_outward_rel emin prec * Rabs ((x0 + x1) - (y0 + y1)) + add_outward_abs emin prec /\
  (((x0 + x1) - (y0 + y1)) = 0 -> (h0 + h1) = ((x0 + x1) - (y0 + y1))).
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny.
generalize (add_up_2_2_outward emin prec Hp x0 x1 (- y0) (- y1) Nx
              (normalized_2_opp emin prec y0 y1 Ny)).
unfold sub_up_2_2, neg_2. cbv beta iota zeta.
destruct (add_up_2_2 emin prec tie_even x0 x1 (- y0) (- y1)) as [h0 h1].
replace (x0 + x1 + (- y0 + - y1)) with (x0 + x1 - (y0 + y1)) by ring. trivial.
Qed.

(** * mul_dir_2_2 *)

(* mul_dir_2_2 in the values of the kernel, for normalized x and y, from precision 4,
   with v = x y and (z0, z1, d) the result of mul_ball_2_2: l and h are normalized;
   l <= v <= h; v - l and h - v are at most 2 d + max(eta, 2 u (u |z0| + d)); and that
   bound is at most A |v| + B. There is no rule of the zero: a product that is not zero
   can be computed as zero, and the bound stays. *)
Theorem mul_dir_2_2_values :
  forall emin prec : Z, (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 ->
  normalized_2 emin prec y0 y1 ->
  let '(z0, z1, d) := mul_ball_2_2 emin prec tie_even x0 x1 y0 y1 in
  let '(l0, l1, h0, h1) := mul_dir_2_2 emin prec tie_even x0 x1 y0 y1 in
  normalized_2 emin prec l0 l1 /\
  normalized_2 emin prec h0 h1 /\
  (l0 + l1) <= ((x0 + x1) * (y0 + y1)) /\
  ((x0 + x1) * (y0 + y1)) <= (h0 + h1) /\
  ((x0 + x1) * (y0 + y1)) - (l0 + l1)
  <= 2 * d + Rmax (eta emin) (2 * u prec * (u prec * Rabs z0 + d)) /\
  (h0 + h1) - ((x0 + x1) * (y0 + y1))
  <= 2 * d + Rmax (eta emin) (2 * u prec * (u prec * Rabs z0 + d)) /\
  2 * d + Rmax (eta emin) (2 * u prec * (u prec * Rabs z0 + d))
  <= mul_outward_rel emin prec * Rabs ((x0 + x1) * (y0 + y1)) + mul_outward_abs emin prec.
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 4%Z; lia).
assert (Hp2 : (2 <= prec)%Z) by lia.
generalize (mul_ball_d emin prec Hp x0 x1 y0 y1 Nx Ny). cbv zeta.
unfold mul_dir_2_2.
destruct (mul_ball_2_2 emin prec tie_even x0 x1 y0 y1) as [[z0 z1] d].
cbv beta iota zeta.
set (v := (x0 + x1) * (y0 + y1)).
intros [Nz [Fd [D0 [Herr Closed]]]].
generalize (outward_down emin prec Hp2 z0 z1 d v Nz Fd D0 Herr).
generalize (outward_up emin prec Hp2 z0 z1 d v Nz Fd D0 Herr). cbv zeta.
destruct (two_sum_ord emin prec tie_even z0 (- add_up_1 emin prec tie_even d (- z1))) as [l0 l1].
destruct (two_sum_ord emin prec tie_even z0 (add_up_1 emin prec tie_even z1 d)) as [h0 h1].
cbn [fst snd]. intros [Nh [_ [Hv TightH]]] [Nl [_ [Lv TightL]]].
exact (conj Nl (conj Nh (conj Lv (conj Hv (conj TightL (conj TightH Closed)))))).
Qed.

(* mul_dir_2_2, the `outward` claims with the constants A and B by name, for normalized
   x and y, from precision 4: l and h are normalized, l <= x y <= h, and each is within
   A |x y| + B of x y. *)
Theorem mul_dir_2_2_outward :
  forall emin prec : Z, (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 ->
  normalized_2 emin prec y0 y1 ->
  let '(l0, l1, h0, h1) := mul_dir_2_2 emin prec tie_even x0 x1 y0 y1 in
  normalized_2 emin prec l0 l1 /\
  normalized_2 emin prec h0 h1 /\
  (l0 + l1) <= ((x0 + x1) * (y0 + y1)) /\
  Rabs ((l0 + l1) - ((x0 + x1) * (y0 + y1))) <= mul_outward_rel emin prec * Rabs ((x0 + x1) * (y0 + y1)) + mul_outward_abs emin prec /\
  ((x0 + x1) * (y0 + y1)) <= (h0 + h1) /\
  Rabs ((h0 + h1) - ((x0 + x1) * (y0 + y1))) <= mul_outward_rel emin prec * Rabs ((x0 + x1) * (y0 + y1)) + mul_outward_abs emin prec.
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny.
generalize (mul_dir_2_2_values emin prec Hp x0 x1 y0 y1 Nx Ny).
destruct (mul_ball_2_2 emin prec tie_even x0 x1 y0 y1) as [[z0 z1] d].
destruct (mul_dir_2_2 emin prec tie_even x0 x1 y0 y1) as [[[l0 l1] h0] h1].
intros [Nl [Nh [Lv [Hv [TightL [TightH Closed]]]]]].
split; [exact Nl|split; [exact Nh|split; [exact Lv|split; [|split; [exact Hv|]]]]].
- rewrite Rabs_left1 by lra. lra.
- rewrite Rabs_pos_eq by lra. lra.
Qed.

(** * The generated statements *)

(* The generated statements of the five directed kernels print the constants A and B of
   the closed form unfolded (add_outward_rel and add_outward_abs, mul_outward_rel and
   mul_outward_abs, on the constants of proofs/gen/Model.v): each is the theorem
   K_outward above. *)
Theorem add_down_2_2_correct : add_down_2_2_spec.
Proof. exact add_down_2_2_outward. Qed.

Theorem add_up_2_2_correct : add_up_2_2_spec.
Proof. exact add_up_2_2_outward. Qed.

Theorem sub_down_2_2_correct : sub_down_2_2_spec.
Proof. exact sub_down_2_2_outward. Qed.

Theorem sub_up_2_2_correct : sub_up_2_2_spec.
Proof. exact sub_up_2_2_outward. Qed.

Theorem mul_dir_2_2_correct : mul_dir_2_2_spec.
Proof. exact mul_dir_2_2_outward. Qed.
