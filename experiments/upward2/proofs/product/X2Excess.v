(* EXPERIMENTAL proof probe. Statement 4 of the product (stretch): a bound on the excess of
   pair_mul over the exact product. Model and definitions: X2Defs.v.

   Main theorem (Print Assumptions at the end of the file):
   - pair_mul_excess: for operands that are upper-normalized pairs or negations of such pairs
     (the operands the product passes), from precision 7, with P Q = (Ph + Pl) (Qh + Ql) the
     exact product, u = 2^-prec and eta = 2^emin:
       0 <= zh + zl - P Q <= 40 u^2 |P Q| + 8 eta.
   The constant is not sharp: the checks measured at most 16 u^2. The proof writes the excess as
   the sum of the errors of the six roundings that follow the leading product (the three of the
   cross terms, the error term e, w, and zl; the rounding of p cancels against e, and zh's is
   absorbed by zl, which is RU(p + w - zh) by pair_mul_tight), bounds each one by
   eta + 2 u |its argument|, and each argument by a multiple of Y = u |Ph Qh| plus a multiple of
   eta; then |Ph Qh| <= (64/63)^2 |P Q| since |Pl| <= 2 u |Ph| and |Ql| <= 2 u |Qh|. Every
   rounding is charged a full eta, so the term for underflow is crude too; in the normal range
   the error term e is exact and several of these eta vanish. *)
From Stdlib Require Import Reals ZArith Lia Lra Psatz Bool.
From Flocq Require Import Core.
From Kairn.Gen Require Import Statements.
From Kairn Require Import Format Directed2.
From KairnX2P Require Import X2Defs X2Order X2PairMul.
Open Scope R_scope.

Section Excess.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation ru := (RU emin prec).

Lemma u_nonneg : 0 <= u prec.
Proof. apply bpow_ge_0. Qed.

(* One rounding up: RU(y) - y <= eta + 2 u |y|. *)
Lemma ru_err_le : forall y, ru y - y <= eta emin + 2 * (u prec * Rabs y).
Proof.
intros y. generalize (ru_gap emin prec y). intros [_ G2].
assert (E : 0 <= eta emin) by apply bpow_ge_0.
assert (A : 0 <= u prec * Rabs y) by (apply Rmult_le_pos; [apply u_nonneg | apply Rabs_pos]).
apply Rle_trans with (1 := G2). unfold Rmax.
destruct (Rle_dec (eta emin) (2 * u prec * Rabs y)); lra.
Qed.

(* u times a linear bound. *)
Lemma u_lin2 :
  forall z a b A B, z <= a * A + b * B -> u prec * z <= a * (u prec * A) + b * (u prec * B).
Proof.
intros z a b A B H.
replace (a * (u prec * A) + b * (u prec * B)) with (u prec * (a * A + b * B)) by ring.
apply Rmult_le_compat_l; [apply u_nonneg | exact H].
Qed.

Lemma u_lin3 :
  forall z a b c A B C, z <= a * A + b * B + c * C ->
  u prec * z <= a * (u prec * A) + b * (u prec * B) + c * (u prec * C).
Proof.
intros z a b c A B C H.
replace (a * (u prec * A) + b * (u prec * B) + c * (u prec * C))
  with (u prec * (a * A + b * B + c * C)) by ring.
apply Rmult_le_compat_l; [apply u_nonneg | exact H].
Qed.

Theorem pair_mul_excess :
  (7 <= prec)%Z ->
  forall ph pl qh ql, up_or_neg emin prec ph pl -> up_or_neg emin prec qh ql ->
  let r := pair_mul emin prec ph pl qh ql in
  0 <= fst (snd r) + snd (snd r) - (ph + pl) * (qh + ql)
    <= 40 * (u prec * (u prec * Rabs ((ph + pl) * (qh + ql)))) + 8 * eta emin.
Proof.
intros Hp ph pl qh ql P Q. cbv zeta.
destruct (up_or_neg_facts emin prec ph pl P) as [Fph [Fpl Tp]].
destruct (up_or_neg_facts emin prec qh ql Q) as [Fqh [Fql Tq]].
unfold small_tail in Tp, Tq.
assert (Up := pair_mul_upper emin prec ph pl qh ql). cbv zeta in Up.
destruct (pair_mul_tight emin prec Hp ph pl qh ql P Q) as [Ezh Ezl]. cbv zeta in Ezh, Ezl.
set (R0 := pair_mul emin prec ph pl qh ql) in *.
set (p := fst R0) in *. set (zh := fst (snd R0)) in *. set (zl := snd (snd R0)) in *.
assert (Ep : p = ru (ph * qh)) by reflexivity.
set (r1 := ru (pl * ql)) in *.
set (r2 := ru (pl * qh + r1)) in *.
set (c := ru (ph * ql + r2)) in *.
set (e := ru (ph * qh + - p)) in *.
set (w := ru (e + c)) in *.
split; [lra|].
set (V := u prec * (u prec * Rabs ((ph + pl) * (qh + ql)))).
set (X := Rabs (ph * qh)).
set (Y := u prec * X).
set (W := u prec * Y).
set (Ue := u prec * eta emin).
assert (U := u_le_128 prec Hp).
assert (U0 := u_nonneg).
assert (E0 : 0 < eta emin) by apply bpow_gt_0.
assert (X0 : 0 <= X) by apply Rabs_pos.
assert (Ah : 0 <= Rabs ph) by apply Rabs_pos.
assert (Aq : 0 <= Rabs qh) by apply Rabs_pos.
assert (AX : X = Rabs ph * Rabs qh) by apply Rabs_mult.
assert (Y0 : 0 <= Y) by (unfold Y; apply Rmult_le_pos; lra).
assert (YX : Y <= / 128 * X) by (unfold Y; apply Rmult_le_compat_r; lra).
assert (YuX : u prec * X = Y) by reflexivity.
assert (W0 : 0 <= W) by (unfold W; apply Rmult_le_pos; lra).
assert (WY : W <= / 128 * Y) by (unfold W; apply Rmult_le_compat_r; lra).
assert (Ue0 : 0 <= Ue) by (unfold Ue; apply Rmult_le_pos; lra).
assert (UeE : Ue <= / 128 * eta emin) by (unfold Ue; apply Rmult_le_compat_r; lra).
(* the cross products, against Y *)
assert (C1 : Rabs (pl * qh) <= 2 * Y).
{ rewrite (Rabs_mult pl qh). unfold Y. rewrite AX.
  apply Rle_trans with (2 * u prec * Rabs ph * Rabs qh); [|right; ring].
  apply Rmult_le_compat_r; [exact Aq | exact Tp]. }
assert (C2 : Rabs (ph * ql) <= 2 * Y).
{ rewrite (Rabs_mult ph ql). unfold Y. rewrite AX.
  apply Rle_trans with (Rabs ph * (2 * u prec * Rabs qh)); [|right; ring].
  apply Rmult_le_compat_l; [exact Ah | exact Tq]. }
assert (C3 : Rabs (pl * ql) <= / 32 * Y).
{ rewrite (Rabs_mult pl ql). unfold Y. rewrite AX.
  apply Rle_trans with ((2 * u prec * Rabs ph) * (2 * u prec * Rabs qh)).
  { apply Rmult_le_compat; trivial; apply Rabs_pos. }
  replace (2 * u prec * Rabs ph * (2 * u prec * Rabs qh))
    with ((4 * u prec) * (u prec * (Rabs ph * Rabs qh))) by ring.
  apply Rmult_le_compat_r; [|lra].
  apply Rmult_le_pos; [lra | now apply Rmult_le_pos]. }
(* the leading product and its error term *)
assert (Gp : 0 <= p - ph * qh <= eta emin + 2 * Y).
{ generalize (ru_gap emin prec (ph * qh)). rewrite <- Ep. intros [G1 G2]. split; [exact G1|].
  apply Rle_trans with (1 := G2). unfold Rmax, Y, X.
  assert (0 <= u prec * Rabs (ph * qh)) by (apply Rmult_le_pos; [lra | apply Rabs_pos]).
  destruct (Rle_dec (eta emin) (2 * u prec * Rabs (ph * qh))); lra. }
assert (He : Rabs e <= eta emin + 2 * Y).
{ assert (L : ph * qh + - p <= e) by (unfold e; apply (ru_ge emin prec)).
  assert (R1 : e <= 0) by (unfold e; apply (ru_nonpos emin prec); lra).
  rewrite (Rabs_left1 e) by exact R1. lra. }
assert (Hx : Rabs (ph * qh + - p) <= 2 * Y + 1 * eta emin).
{ rewrite Rabs_left1 by lra. lra. }
assert (Hp1 : Rabs p <= X + eta emin + 2 * Y).
{ replace p with (ph * qh + (p - ph * qh)) by ring.
  apply Rle_trans with (1 := Rabs_triang _ _).
  rewrite (Rabs_pos_eq (p - ph * qh)) by lra. fold X. lra. }
(* the chain of the cross terms and w *)
assert (B1 := ru_abs_le emin prec Hp (pl * ql)). fold r1 in B1.
assert (B2 := ru_abs_le emin prec Hp (pl * qh + r1)). fold r2 in B2.
assert (B3 := ru_abs_le emin prec Hp (ph * ql + r2)). fold c in B3.
assert (B4 := ru_abs_le emin prec Hp (e + c)). fold w in B4.
assert (T2 := Rabs_triang (pl * qh) r1).
assert (T3 := Rabs_triang (ph * ql) r2).
assert (T4 := Rabs_triang e c).
assert (T5 := Rabs_triang p w).
assert (L4c : Rabs (pl * ql) <= / 32 * Y + 0 * eta emin) by lra.
assert (L4b : Rabs (pl * qh + r1) <= 21 / 10 * Y + 1 * eta emin) by lra.
assert (L4a : Rabs (ph * ql + r2) <= 42 / 10 * Y + 21 / 10 * eta emin) by lra.
assert (L2 : Rabs (e + c) <= 63 / 10 * Y + 42 / 10 * eta emin) by lra.
assert (Lpw : Rabs (p + w) <= 1 * X + 9 * Y + 7 * eta emin) by lra.
(* the six errors *)
assert (E4c : r1 - pl * ql <= eta emin + 2 * (u prec * Rabs (pl * ql)))
  by (unfold r1; apply ru_err_le).
assert (E4b : r2 - (pl * qh + r1) <= eta emin + 2 * (u prec * Rabs (pl * qh + r1)))
  by (unfold r2; apply ru_err_le).
assert (E4a : c - (ph * ql + r2) <= eta emin + 2 * (u prec * Rabs (ph * ql + r2)))
  by (unfold c; apply ru_err_le).
assert (E3 : e - (ph * qh + - p) <= eta emin + 2 * (u prec * Rabs (ph * qh + - p)))
  by (unfold e; apply ru_err_le).
assert (E2 : w - (e + c) <= eta emin + 2 * (u prec * Rabs (e + c)))
  by (unfold w; apply ru_err_le).
assert (Ed : zh - (p + w) <= eta emin + 2 * (u prec * Rabs (p + w)))
  by (rewrite Ezh; apply ru_err_le).
assert (Dz : 0 <= zh - (p + w)) by (rewrite Ezh; generalize (ru_ge emin prec (p + w)); lra).
assert (E1 : zl - (p + w - zh) <= eta emin + 2 * (u prec * Rabs (p + w - zh)))
  by (rewrite Ezl; apply ru_err_le).
(* u times each argument *)
assert (M4c : u prec * Rabs (pl * ql) <= / 32 * W + 0 * Ue) by (unfold W, Ue; apply u_lin2; lra).
assert (M4b : u prec * Rabs (pl * qh + r1) <= 21 / 10 * W + 1 * Ue)
  by (unfold W, Ue; apply u_lin2; lra).
assert (M4a : u prec * Rabs (ph * ql + r2) <= 42 / 10 * W + 21 / 10 * Ue)
  by (unfold W, Ue; apply u_lin2; lra).
assert (M3 : u prec * Rabs (ph * qh + - p) <= 2 * W + 1 * Ue)
  by (unfold W, Ue; apply u_lin2; lra).
assert (M2 : u prec * Rabs (e + c) <= 63 / 10 * W + 42 / 10 * Ue)
  by (unfold W, Ue; apply u_lin2; lra).
assert (Mpw : u prec * Rabs (p + w) <= 1 * (u prec * X) + 9 * W + 7 * Ue)
  by (unfold W, Ue; apply u_lin3; lra).
assert (Ld : Rabs (p + w - zh) <= 3 * Y + 2 * eta emin).
{ rewrite Rabs_minus_sym, Rabs_pos_eq by lra. lra. }
assert (M1 : u prec * Rabs (p + w - zh) <= 3 * W + 2 * Ue) by (unfold W, Ue; apply u_lin2; lra).
(* |Ph Qh| against the exact product *)
assert (P1 : 63 / 64 * Rabs ph <= Rabs (ph + pl)).
{ generalize (Rabs_triang_inv ph (- pl)). rewrite Rabs_Ropp.
  replace (ph - - pl) with (ph + pl) by ring.
  assert (2 * u prec * Rabs ph <= / 64 * Rabs ph) by (apply Rmult_le_compat_r; lra). lra. }
assert (P2 : 63 / 64 * Rabs qh <= Rabs (qh + ql)).
{ generalize (Rabs_triang_inv qh (- ql)). rewrite Rabs_Ropp.
  replace (qh - - ql) with (qh + ql) by ring.
  assert (2 * u prec * Rabs qh <= / 64 * Rabs qh) by (apply Rmult_le_compat_r; lra). lra. }
assert (XPQ : X <= 4096 / 3969 * Rabs ((ph + pl) * (qh + ql))).
{ rewrite Rabs_mult.
  assert (K : 63 / 64 * Rabs ph * (63 / 64 * Rabs qh) <= Rabs (ph + pl) * Rabs (qh + ql)).
  { apply Rmult_le_compat; trivial; apply Rmult_le_pos; lra. }
  rewrite AX. lra. }
assert (WV : W <= 4096 / 3969 * V).
{ unfold W, Y, V.
  replace (4096 / 3969 * (u prec * (u prec * Rabs ((ph + pl) * (qh + ql)))))
    with (u prec * (u prec * (4096 / 3969 * Rabs ((ph + pl) * (qh + ql))))) by ring.
  apply Rmult_le_compat_l; [lra|]. apply Rmult_le_compat_l; [lra|]. exact XPQ. }
fold V.
replace ((ph + pl) * (qh + ql)) with (ph * qh + ph * ql + pl * qh + pl * ql) by ring.
lra.
Qed.

End Excess.

Print Assumptions pair_mul_excess.
