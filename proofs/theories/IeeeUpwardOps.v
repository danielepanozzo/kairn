(* The sum and the product rounded upward, add_ru and mul_ru of IeeeUpwardOperations.v, in the
   IEEE model on all values: finite numbers, signed zeros, infinities and NaN
   (docs/developer/design/upward.md, "The operations of the IR" and "How they are to be
   proved").

   Notation: T is the format of IeeeOperations.v; Omega its largest number; xval a the extended
   real number a limb stands for; xadd and xmul IEEE 754's sum and product on extended real
   numbers (a NaN for a NaN operand, for inf - inf and for 0 * inf); xrd and xru the roundings
   down and up in the format with overflow (IeeeVocabulary.v): beyond Omega, the number Omega on
   the side toward zero and the infinity on the other.

   What is proved, for all limbs a and b:
   - add_ru_xval, mul_ru_xval: the result stands for xru (xadd (xval a) (xval b)) and
     xru (xmul (xval a) (xval b)): for finite operands the exact sum or product rounded up in
     the format with overflow (+infinity above Omega, -Omega below -Omega, never -infinity),
     from Flocq's Bplus_correct and Bmult_correct with mode_UP and their overflow case
     (binary_overflow: +infinity upward, -Omega downward); otherwise IEEE 754's sum or product
     of the values, an infinity or a NaN;
   - add_ru_nan_cases, mul_ru_nan_cases: the result is a NaN exactly when an operand is a NaN,
     or the operands are the two infinities (the sum), or a zero and an infinity (the product);
   - add_ru_ninf, mul_ru_ninf: the result is -infinity exactly when IEEE 754's sum or product
     of the values is -infinity, so never for a sum whose operands are not -infinity
     (add_ru_not_ninf), and never for a product of finite operands (mul_ru_finite_not_ninf);
   - the lanes: a lane of a nonempty canonical state is neither a NaN nor -infinity
     (upward_lane, upward_nonempty_lane), and a sum of two such values is again one
     (add_ru_lane): no lane sum of nonempty canonical operands is inf - inf;
   - RU(-t) = -RD(t) in the vocabulary of the statements (xru_opp, xrd_opp, and RU_opp on the
     real model): a lane n whose value is the rounding up of -t reads as the lower bound
     -n = RD(t) (upward_lane_lower), so that the lane n = RU(-a - c) of a sum is the lower
     bound RD(a + c) (add_ru_lower), and a lane n = RU(-a * d) of a product the lower bound
     RD(a * d) (mul_ru_lower);
   - the other operations of the listings on canonical states: unord of two lanes is true
     exactly when a state is empty (unord_state, unord_states); `const nan` is a NaN
     (cnan_nan); abs stands for xabs (xval_abs); and the test of the whole line of
     upward_mul_num_1 (whole_mul_test): |u| + |n| rounded up is +0, and not above 0, for the
     state [0, 0], and above 0 for every other nonempty state.
   No hypothesis on the precision: every statement holds from precision 1. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import IeeeBridge IeeeVocabulary IeeeOps IeeeExt IeeeDirected.
From Kairn Require Import Rectangle IeeeIntervalVocabulary IeeeInterval1.
From Kairn Require Import IeeeUpwardVocabulary IeeeUpwardMax.
From Kairn Require IeeeOperations IeeeUpwardOperations.
Open Scope R_scope.

(** * Extended real numbers *)

(* A disequality of real numbers left by Req_bool_spec, contradicted by linear arithmetic. *)
Ltac upward_neq :=
  try (match goal with H : _ <> _ |- _ => solve [exfalso; apply H; lra] end).

(* Sign changes of IEEE 754's sum and product. *)
Lemma xadd_opp : forall v w : xreal, xadd (xopp v) (xopp w) = xopp (xadd v w).
Proof. intros [|[|]|x] [|[|]|y]; cbn; trivial. f_equal. ring. Qed.

Lemma xmul_opp_l : forall v w : xreal, xmul (xopp v) w = xopp (xmul v w).
Proof.
intros [|[|]|x] [|[|]|y]; upward_xcase; upward_neq; f_equal; ring.
Qed.

Lemma xmul_opp_r : forall v w : xreal, xmul v (xopp w) = xopp (xmul v w).
Proof.
intros [|[|]|x] [|[|]|y]; upward_xcase; upward_neq; f_equal; ring.
Qed.

Lemma xmul0_opp_l : forall v w : xreal, xmul0 (xopp v) w = xopp (xmul0 v w).
Proof.
intros [|[|]|x] [|[|]|y]; upward_xcase; upward_neq; f_equal; ring.
Qed.

Lemma xmul0_opp_r : forall v w : xreal, xmul0 v (xopp w) = xopp (xmul0 v w).
Proof.
intros [|[|]|x] [|[|]|y]; upward_xcase; upward_neq; f_equal; ring.
Qed.

(* When IEEE 754's sum or product is a NaN, and when it is -infinity. *)
Lemma xadd_nan_iff :
  forall v w : xreal,
  xadd v w = XNaN <-> v = XNaN \/ w = XNaN \/ (exists s : bool, v = XInf s /\ w = XInf (negb s)).
Proof.
intros [|[|]|x] [|[|]|y]; cbn; split; intros H; try discriminate; auto;
  try (destruct H as [H|[H|[s [H K]]]]; try discriminate; destruct s; discriminate).
- right. right. exists true. now split.
- right. right. exists false. now split.
Qed.

Lemma xmul_nan_iff :
  forall v w : xreal,
  xmul v w = XNaN <->
  v = XNaN \/ w = XNaN \/ (v = XFin 0 /\ exists s : bool, w = XInf s) \/
  ((exists s : bool, v = XInf s) /\ w = XFin 0).
Proof.
intros [|sv|x] [|sw|y]; cbn; try (split; intros; auto; fail).
- split; [intros H; discriminate H|]. intros [H|[H|[[H _]|[_ H]]]]; discriminate H.
- destruct (Req_bool_spec y 0) as [E|E].
  + subst y. split; [intros _; right; right; right; split; [now exists sv|reflexivity]|].
    intros _. reflexivity.
  + split; [intros H; discriminate H|]. intros [H|[H|[[H _]|[_ H]]]]; try discriminate H.
    elim E. now inversion H.
- destruct (Req_bool_spec x 0) as [E|E].
  + subst x. split; [intros _; right; right; left; split; [reflexivity|now exists sw]|].
    intros _. reflexivity.
  + split; [intros H; discriminate H|]. intros [H|[H|[[H _]|[_ H]]]]; try discriminate H.
    elim E. now inversion H.
- split; [intros H; discriminate H|]. intros [H|[H|[[_ [s H]]|[[s H] _]]]]; discriminate H.
Qed.

Lemma xadd_ninf : forall v w : xreal, xadd v w = XInf true -> v = XInf true \/ w = XInf true.
Proof. intros [|[|]|x] [|[|]|y]; cbn; intros H; try discriminate; auto. Qed.

(** * The rounding up in the format with overflow *)

Section IeeeUpwardOps.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_mult : float -> float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_const : nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation xv := (@xval prec emax).
Notation Om := (Omega prec emax).
Notation ninf := (infinity prec emax true).
Notation add_ru := (IeeeUpwardOperations.add_ru prec emax nan_plus).
Notation mul_ru := (IeeeUpwardOperations.mul_ru prec emax nan_mult).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

(* RU(-t) = -RD(t) and RD(-t) = -RU(t), in the format with no largest number and in the format
   with overflow. *)
Lemma RU_opp : forall t : R, RU emin prec (- t) = - RD emin prec t.
Proof. intros t. unfold RU, RD. apply round_UP_opp. Qed.

Lemma xrd_opp : forall v : xreal, xrd prec emax (xopp v) = xopp (xru prec emax v).
Proof. intros v. unfold xru. now rewrite xopp_involutive. Qed.

Lemma xru_opp : forall v : xreal, xru prec emax (xopp v) = xopp (xrd prec emax v).
Proof. intros v. unfold xru. now rewrite xopp_involutive. Qed.

(* A lane n whose value is the rounding up of -t: its opposite, the lower bound -n, is the
   rounding down of t. *)
Theorem upward_lane_lower :
  forall (n : float) (t : xreal),
  xv n = xru prec emax (xopp t) -> xopp (xv n) = xrd prec emax t.
Proof. intros n t E. rewrite E, xru_opp. apply xopp_involutive. Qed.

(* xru of a real number is never a NaN and never -infinity; xru leaves an infinity and a NaN
   as they are. *)
Lemma xru_nan : forall v : xreal, xru prec emax v = XNaN <-> v = XNaN.
Proof.
intros [|[|]|r]; split; intros H; try discriminate H; trivial.
revert H. rewrite (xru_real prec emax).
destruct (Rlt_bool (Omega prec emax) r); [intros H; discriminate H|].
destruct (Rlt_bool r (- Omega prec emax)); intros H; discriminate H.
Qed.

Lemma xru_ninf : forall v : xreal, xru prec emax v = XInf true <-> v = XInf true.
Proof.
intros [|[|]|r]; split; intros H; try discriminate H; trivial.
revert H. rewrite (xru_real prec emax).
destruct (Rlt_bool (Omega prec emax) r); [intros H; discriminate H|].
destruct (Rlt_bool r (- Omega prec emax)); intros H; discriminate H.
Qed.

Lemma xru_nonreal : forall v : xreal, (forall r : R, v <> XFin r) -> xru prec emax v = v.
Proof.
intros [|[|]|r] H; trivial. elim (H r). reflexivity.
Qed.

(** * The result of an operation rounded up *)

(* The largest mantissa, that of Omega in Flocq's overflow. *)
Lemma overflow_mantissa : IZR (Zpos (Z.to_pos (2 ^ prec - 1))) = bpow radix2 prec - 1.
Proof.
assert (P : (1 < 2 ^ prec)%Z) by (apply Z.pow_gt_1; lia).
rewrite Z2Pos.id by lia. rewrite minus_IZR.
change (2 ^ prec)%Z with (Zpower radix2 prec). rewrite IZR_Zpower by lia. reflexivity.
Qed.

(* A negative overflow rounded up is -Omega. *)
Lemma overflow_up_neg :
  forall z : float,
  B2FF prec emax z = binary_overflow prec emax BinarySingleNaN.mode_UP true ->
  xv z = XFin (- Om).
Proof.
intros [s|s|s pl H|s m e H] E; cbn in E; try discriminate E.
injection E. intros Ee Em Es. subst s m e.
unfold xval, val. cbn [is_finite B2R]. unfold F2R. cbn [Fnum Fexp]. f_equal.
change (cond_Zopp true (Zpos (Z.to_pos (2 ^ prec - 1))))
  with (- Zpos (Z.to_pos (2 ^ prec - 1)))%Z.
rewrite opp_IZR, overflow_mantissa. unfold Omega.
replace (bpow radix2 emax) with (bpow radix2 prec * bpow radix2 (emax - prec))
  by (rewrite <- bpow_plus; f_equal; ring).
ring.
Qed.

(* An overflowing rounding is of a nonzero number. *)
Lemma ru_overflow_nonzero :
  forall p : R, bpow radix2 emax <= Rabs (RU emin prec p) -> p <> 0.
Proof.
intros p H E. rewrite E in H. unfold RU in H.
rewrite round_0 in H by auto with typeclass_instances. rewrite Rabs_R0 in H.
generalize (bpow_gt_0 radix2 emax). lra.
Qed.

(* The value of a result that Flocq describes as the rounding up of a real number p: when that
   rounding is below 2^emax in magnitude, a finite number of that value; otherwise the overflow
   of the sign of p. It stands for xru p. *)
Lemma ru_result_xval :
  forall (p : R) (z : float),
  (Rabs (RU emin prec p) < bpow radix2 emax -> fin z /\ b2r z = RU emin prec p) ->
  (bpow radix2 emax <= Rabs (RU emin prec p) ->
   B2FF prec emax z = binary_overflow prec emax BinarySingleNaN.mode_UP (Rlt_bool p 0)) ->
  xv z = xru prec emax (XFin p).
Proof.
intros p z Hin Hout.
assert (P0 := Omega_gt_0 prec emax). assert (P1 := Omega_lt_top prec emax).
assert (Fr : format (RU emin prec p)).
{ unfold RU. apply generic_format_round; auto with typeclass_instances. }
destruct (round_UP_pt radix2 fexp p) as [_ [Ge Least]].
fold (RU emin prec p) in Ge, Least.
rewrite (xru_real prec emax p).
destruct (Rlt_le_dec (Rabs (RU emin prec p)) (bpow radix2 emax)) as [In|Out].
- destruct (Hin In) as [F E]. rewrite (xval_fin prec emax z F), E.
  assert (B : Rabs (RU emin prec p) <= Om) by (apply (inrange_le_Omega prec emax); assumption).
  apply Rabs_le_inv in B.
  rewrite (Rlt_bool_false Om p) by lra.
  destruct (Rlt_bool_spec p (- Om)) as [C|C]; cbv iota; [|reflexivity].
  f_equal. apply Rle_antisym; [|lra].
  apply Least; [apply generic_format_opp; apply (format_Omega prec emax)|lra].
- specialize (Hout Out). assert (N0 := ru_overflow_nonzero p Out).
  destruct (Rlt_le_dec p 0) as [Neg|Pos].
  + rewrite (Rlt_bool_true p 0 Neg) in Hout. rewrite (overflow_up_neg z Hout).
    rewrite (Rlt_bool_false Om p) by lra.
    assert (Rn : RU emin prec p <= 0) by (apply Least; [apply generic_format_0|lra]).
    rewrite Rabs_left1 in Out by exact Rn.
    rewrite Rlt_bool_true by lra. reflexivity.
  + rewrite (Rlt_bool_false p 0 Pos) in Hout.
    assert (Hz : z = B754_infinity prec emax false).
    { apply B2FF_inf_inv. rewrite Hout. reflexivity. }
    rewrite Hz.
    rewrite Rlt_bool_true; [reflexivity|].
    apply Rnot_le_lt. intros K.
    assert (L : RU emin prec p <= Om) by (apply Least; [apply (format_Omega prec emax)|exact K]).
    rewrite Rabs_pos_eq in Out by lra. lra.
Qed.

(* The sign of a product of two nonzero real numbers. *)
Lemma Rlt_bool_mult :
  forall x y : R, x <> 0 -> y <> 0 -> Rlt_bool (x * y) 0 = xorb (Rlt_bool x 0) (Rlt_bool y 0).
Proof.
intros x y Hx Hy.
destruct (Rlt_bool_spec x 0) as [A|A]; destruct (Rlt_bool_spec y 0) as [B|B]; cbn.
- apply Rlt_bool_false. nra.
- apply Rlt_bool_true. assert (0 < y) by (destruct B; [assumption|congruence]). nra.
- apply Rlt_bool_true. assert (0 < x) by (destruct A; [assumption|congruence]). nra.
- apply Rlt_bool_false. assert (0 < x) by (destruct A; [assumption|congruence]).
  assert (0 < y) by (destruct B; [assumption|congruence]). nra.
Qed.

(* The sign of a finite number that is not zero is that of its value. *)
Lemma sign_of_value : forall c : float, fin c -> b2r c <> 0 -> Bsign prec emax c = Rlt_bool (b2r c) 0.
Proof.
intros c Fc Nc. destruct (Rlt_bool_spec (b2r c) 0) as [L|L].
- now apply neg_sign.
- apply pos_sign. destruct L as [L|L]; [exact L|elim Nc; symmetry; exact L].
Qed.

(** ** The sum *)

Lemma add_ru_finite :
  forall a b : float, fin a -> fin b ->
  xv (add_ru a b) = xru prec emax (XFin (b2r a + b2r b)).
Proof.
intros a b Fa Fb.
generalize (Bplus_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus BinarySingleNaN.mode_UP
              a b Fa Fb).
change (Bplus prec emax prec_gt_0_ prec_lt_emax_ nan_plus BinarySingleNaN.mode_UP a b)
  with (add_ru a b).
change (round radix2 (SpecFloat.fexp prec emax)
          (BinarySingleNaN.round_mode BinarySingleNaN.mode_UP) (b2r a + b2r b))
  with (RU emin prec (b2r a + b2r b)).
intros H. apply ru_result_xval.
- intros In. rewrite (Rlt_bool_true _ _ In) in H. destruct H as [E [F _]]. now split.
- intros Out. rewrite (Rlt_bool_false _ _ Out) in H. destruct H as [E S].
  rewrite E. f_equal. assert (N0 := ru_overflow_nonzero _ Out).
  destruct (Rlt_bool_spec (b2r a + b2r b) 0) as [Neg|Pos].
  + destruct (Bsign prec emax a) eqn:Sa; [reflexivity|exfalso].
    assert (Sb : Bsign prec emax b = false) by congruence.
    generalize (sign_false_nonneg prec emax a Fa Sa) (sign_false_nonneg prec emax b Fb Sb). lra.
  + destruct (Bsign prec emax a) eqn:Sa; [exfalso|reflexivity].
    assert (Sb : Bsign prec emax b = true) by congruence.
    generalize (sign_true_nonpos prec emax a Fa Sa) (sign_true_nonpos prec emax b Fb Sb).
    intros A B. apply N0. lra.
Qed.

Lemma add_ru_nonfinite :
  forall a b : float,
  is_finite prec emax a = false \/ is_finite prec emax b = false ->
  xv (add_ru a b) = xadd (xv a) (xv b).
Proof.
intros [sa|sa|sa pa Ha|sa ma ea Ha] [sb|sb|sb pb Hb|sb mb eb Hb] [H|H];
  try discriminate H;
  repeat match goal with s : bool |- _ => destruct s end;
  reflexivity.
Qed.

(* The sum rounded up, for all operands: the rounding up, in the format with overflow, of
   IEEE 754's sum of the values. *)
Theorem add_ru_xval :
  forall a b : float, xv (add_ru a b) = xru prec emax (xadd (xv a) (xv b)).
Proof.
intros a b.
destruct (finite_dec prec emax a) as [Fa|Fa]; [destruct (finite_dec prec emax b) as [Fb|Fb]|].
- rewrite (xval_fin prec emax a Fa), (xval_fin prec emax b Fb). cbn [xadd].
  now apply add_ru_finite.
- rewrite (proj2 (xrd_xadd_nonfinite prec emax a b (or_intror Fb))).
  apply add_ru_nonfinite. now right.
- rewrite (proj2 (xrd_xadd_nonfinite prec emax a b (or_introl Fa))).
  apply add_ru_nonfinite. now left.
Qed.

(** ** The product *)

Lemma mul_ru_finite :
  forall a b : float, fin a -> fin b ->
  xv (mul_ru a b) = xru prec emax (XFin (b2r a * b2r b)).
Proof.
intros a b Fa Fb.
generalize (Bmult_correct prec emax prec_gt_0_ prec_lt_emax_ nan_mult BinarySingleNaN.mode_UP a b).
change (Bmult prec emax prec_gt_0_ prec_lt_emax_ nan_mult BinarySingleNaN.mode_UP a b)
  with (mul_ru a b).
change (round radix2 (SpecFloat.fexp prec emax)
          (BinarySingleNaN.round_mode BinarySingleNaN.mode_UP) (b2r a * b2r b))
  with (RU emin prec (b2r a * b2r b)).
intros H. apply ru_result_xval.
- intros In. rewrite (Rlt_bool_true _ _ In) in H. destruct H as [E [F _]].
  rewrite Fa, Fb in F. now split.
- intros Out. rewrite (Rlt_bool_false _ _ Out) in H. rewrite H. f_equal.
  assert (N0 := ru_overflow_nonzero _ Out).
  assert (Na : b2r a <> 0) by (intros E; apply N0; rewrite E; ring).
  assert (Nb : b2r b <> 0) by (intros E; apply N0; rewrite E; ring).
  rewrite (sign_of_value a Fa Na), (sign_of_value b Fb Nb).
  symmetry. now apply Rlt_bool_mult.
Qed.

(* A finite number that is not zero has a value that is not zero and has the sign of the
   number. *)
Lemma xval_finite_nonzero :
  forall (s : bool) (m : positive) (e : Z) (H : SpecFloat.bounded prec emax m e = true),
  exists r : R, xv (B754_finite prec emax s m e H) = XFin r /\
                Req_bool r 0 = false /\ Rlt_bool r 0 = s.
Proof.
intros s m e H. exists (b2r (B754_finite prec emax s m e H)).
split; [reflexivity|]. destruct s.
- generalize (finite_sign_neg prec emax m e H). intros L.
  split; [apply Req_bool_false; lra|now apply Rlt_bool_true].
- generalize (finite_sign_pos prec emax m e H). intros L.
  split; [apply Req_bool_false; lra|apply Rlt_bool_false; lra].
Qed.

Lemma xval_zero : forall s : bool, xv (B754_zero prec emax s) = XFin 0.
Proof. intros s. reflexivity. Qed.

Lemma xval_nan_constr : forall s pl H, xv (B754_nan prec emax s pl H) = XNaN.
Proof. intros s pl H. reflexivity. Qed.

Lemma mul_ru_nonfinite :
  forall a b : float,
  is_finite prec emax a = false \/ is_finite prec emax b = false ->
  xv (mul_ru a b) = xmul (xv a) (xv b).
Proof.
intros [sa|sa|sa pa Ha|sa ma ea Ha] [sb|sb|sb pb Hb|sb mb eb Hb] [H|H];
  try discriminate H;
  rewrite ?xval_zero, ?(xval_inf prec emax), ?xval_nan_constr;
  try (destruct (xval_finite_nonzero sa ma ea Ha) as [r [E [Hz Hs]]]; rewrite E);
  try (destruct (xval_finite_nonzero sb mb eb Hb) as [r [E [Hz Hs]]]; rewrite E);
  cbn [xmul]; rewrite ?Req_bool_0_0; try rewrite Hz; try rewrite Hs; reflexivity.
Qed.

(* IEEE 754's product with an operand that is not finite is an infinity or a NaN. *)
Lemma xmul_nonfinite :
  forall a b : float,
  is_finite prec emax a = false \/ is_finite prec emax b = false ->
  forall r : R, xmul (xv a) (xv b) <> XFin r.
Proof.
intros a b H r.
destruct (xval_cases prec emax a) as [[Fa Ea]|[[sa Ea]|Ea]];
destruct (xval_cases prec emax b) as [[Fb Eb]|[[sb Eb]|Eb]];
  rewrite Ea, Eb; try (exfalso; destruct H; congruence); cbn;
  repeat match goal with |- context [Req_bool ?x ?y] => destruct (Req_bool x y) end;
  discriminate.
Qed.

(* The product rounded up, for all operands: the rounding up, in the format with overflow, of
   IEEE 754's product of the values. *)
Theorem mul_ru_xval :
  forall a b : float, xv (mul_ru a b) = xru prec emax (xmul (xv a) (xv b)).
Proof.
intros a b.
destruct (finite_dec prec emax a) as [Fa|Fa]; [destruct (finite_dec prec emax b) as [Fb|Fb]|].
- rewrite (xval_fin prec emax a Fa), (xval_fin prec emax b Fb). cbn [xmul].
  now apply mul_ru_finite.
- rewrite (xru_nonreal _ (xmul_nonfinite a b (or_intror Fb))).
  apply mul_ru_nonfinite. now right.
- rewrite (xru_nonreal _ (xmul_nonfinite a b (or_introl Fa))).
  apply mul_ru_nonfinite. now left.
Qed.

(** ** The NaN cases *)

Lemma xval_zero_iff : forall a : float, xv a = XFin 0 <-> zero a.
Proof.
intros a. split.
- intros E. destruct (upward_xval_real prec emax a 0 E) as [F V].
  exact (zero_inv prec emax a F V).
- intros [s E]. subst a. reflexivity.
Qed.

Lemma xval_infinite_iff : forall a : float, (exists s, xv a = XInf s) <-> (exists s, a = infinity prec emax s).
Proof.
intros a. split; intros [s E]; exists s; now apply upward_xval_inf.
Qed.

(* The sum is a NaN exactly when an operand is, or the operands are the two infinities. *)
Theorem add_ru_nan_cases :
  forall a b : float,
  nan (add_ru a b) <->
  nan a \/ nan b \/ (exists s : bool, a = infinity prec emax s /\ b = infinity prec emax (negb s)).
Proof.
intros a b. rewrite <- (upward_xval_nan prec emax), add_ru_xval, xru_nan, xadd_nan_iff.
rewrite 2!(upward_xval_nan prec emax).
split; intros [H|[H|[s [H K]]]]; auto; right; right; exists s;
  split; now apply upward_xval_inf.
Qed.

(* The product is a NaN exactly when an operand is, or one is a zero and the other an
   infinity. *)
Theorem mul_ru_nan_cases :
  forall a b : float,
  nan (mul_ru a b) <->
  nan a \/ nan b \/ (zero a /\ exists s : bool, b = infinity prec emax s) \/
  ((exists s : bool, a = infinity prec emax s) /\ zero b).
Proof using prec_gt_0_ prec_lt_emax_ nan_mult.
intros a b. rewrite <- (upward_xval_nan prec emax), mul_ru_xval, xru_nan, xmul_nan_iff.
rewrite 2!(upward_xval_nan prec emax), 2!xval_zero_iff, 2!xval_infinite_iff.
split; intros H; exact H.
Qed.

(* A NaN operand gives a NaN. *)
Lemma add_ru_nan_l : forall a b : float, nan a -> nan (add_ru a b).
Proof. intros a b N. apply add_ru_nan_cases. now left. Qed.

Lemma add_ru_nan_r : forall a b : float, nan b -> nan (add_ru a b).
Proof. intros a b N. apply add_ru_nan_cases. now right; left. Qed.

Lemma mul_ru_nan_l : forall a b : float, nan a -> nan (mul_ru a b).
Proof. intros a b N. apply mul_ru_nan_cases. now left. Qed.

Lemma mul_ru_nan_r : forall a b : float, nan b -> nan (mul_ru a b).
Proof. intros a b N. apply mul_ru_nan_cases. now right; left. Qed.

(** ** -infinity *)

Theorem add_ru_ninf :
  forall a b : float, add_ru a b = ninf <-> xadd (xv a) (xv b) = XInf true.
Proof.
intros a b. rewrite <- (upward_xval_inf prec emax), add_ru_xval. apply xru_ninf.
Qed.

Theorem mul_ru_ninf :
  forall a b : float, mul_ru a b = ninf <-> xmul (xv a) (xv b) = XInf true.
Proof.
intros a b. rewrite <- (upward_xval_inf prec emax), mul_ru_xval. apply xru_ninf.
Qed.

(* A sum is never -infinity when no operand is. *)
Corollary add_ru_not_ninf : forall a b : float, a <> ninf -> b <> ninf -> add_ru a b <> ninf.
Proof using prec_gt_0_ prec_lt_emax_ nan_plus.
intros a b Ha Hb E. apply add_ru_ninf in E.
destruct (xadd_ninf _ _ E) as [K|K]; apply (upward_xval_inf prec emax) in K;
  first [exact (Ha K)|exact (Hb K)].
Qed.

(* A product of finite numbers is never -infinity: a negative overflow is -Omega. *)
Corollary mul_ru_finite_not_ninf : forall a b : float, fin a -> fin b -> mul_ru a b <> ninf.
Proof.
intros a b Fa Fb E. apply mul_ru_ninf in E.
rewrite (xval_fin prec emax a Fa), (xval_fin prec emax b Fb) in E. discriminate E.
Qed.

(** ** The lanes of canonical states *)

(* A lane of a nonempty canonical state: neither a NaN nor -infinity; a real number or
   +infinity. *)
Definition upward_lane (a : float) : Prop := ~ nan a /\ a <> ninf.

Lemma upward_nonempty_lane :
  forall u n : float, upward_nonempty_1 u n -> upward_lane u /\ upward_lane n.
Proof.
intros u n H. destruct (upward_nonempty_lanes prec emax u n H) as [Nu [Nn [Iu In]]].
split; split; assumption.
Qed.

Lemma upward_lane_xval :
  forall a : float, upward_lane a <-> xv a = XInf false \/ exists r : R, xv a = XFin r.
Proof.
intros a. unfold upward_lane. split.
- intros [N I]. destruct (upward_xval_cases prec emax a) as [[K _]|[[[|] [E V]]|[_ V]]].
  + now elim N.
  + now elim I.
  + now left.
  + right. now exists (val a).
- intros [E|[r E]]; split; intros K.
  + apply (upward_xval_nan prec emax) in K. congruence.
  + apply (upward_xval_inf prec emax) in K. congruence.
  + apply (upward_xval_nan prec emax) in K. congruence.
  + apply (upward_xval_inf prec emax) in K. congruence.
Qed.

(* The sum of two lanes is a lane: neither inf - inf nor -infinity. *)
Theorem add_ru_lane :
  forall a b : float, upward_lane a -> upward_lane b -> upward_lane (add_ru a b).
Proof.
intros a b Ha Hb. apply upward_lane_xval. rewrite add_ru_xval.
apply upward_lane_xval in Ha. apply upward_lane_xval in Hb.
destruct Ha as [Ea|[ra Ea]]; destruct Hb as [Eb|[rb Eb]]; rewrite Ea, Eb; cbn [xadd].
- now left.
- now left.
- now left.
- rewrite (xru_real prec emax).
  destruct (Rlt_bool _ _); [now left|]. destruct (Rlt_bool _ _); right; eexists; reflexivity.
Qed.

(* The four lane sums of two nonempty canonical states are lanes: in particular none of them
   is inf - inf, a NaN. *)
Corollary upward_add_lanes :
  forall xu xn yu yn : float,
  upward_nonempty_1 xu xn -> upward_nonempty_1 yu yn ->
  forall p q : float, (p = xu \/ p = xn) -> (q = yu \/ q = yn) -> upward_lane (add_ru p q).
Proof.
intros xu xn yu yn HX HY p q Hp Hq.
destruct (upward_nonempty_lane xu xn HX) as [Lu Ln].
destruct (upward_nonempty_lane yu yn HY) as [Mu Mn].
apply add_ru_lane; [destruct Hp as [E|E]|destruct Hq as [E|E]]; subst; assumption.
Qed.

(** ** The lower bound of a lane n *)

(* A lane n computed as add_ru of two values: its opposite is the rounding down of the sum of
   their opposites; the lane n = RU(-a - c) of a sum is the lower bound RD(a + c). *)
Theorem add_ru_lower :
  forall a b : float,
  xopp (xv (add_ru a b)) = xrd prec emax (xadd (xopp (xv a)) (xopp (xv b))).
Proof.
intros a b. apply upward_lane_lower. rewrite add_ru_xval, xadd_opp, xopp_involutive.
reflexivity.
Qed.

(* A lane n computed as mul_ru of p and q: its opposite is the rounding down of the product
   of -p and q; the lane n = RU(-a * d) is the lower bound RD(a * d). *)
Theorem mul_ru_lower :
  forall a b : float,
  xopp (xv (mul_ru a b)) = xrd prec emax (xmul (xopp (xv a)) (xv b)).
Proof.
intros a b. apply upward_lane_lower. rewrite mul_ru_xval, xmul_opp_l, xopp_involutive.
reflexivity.
Qed.

(** ** The other operations of the listings, on canonical states *)

Notation unord := (IeeeUpwardOperations.unord prec emax).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation flt := (IeeeOperations.lt prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation cnan := (IeeeOperations.cnan prec emax nan_const).

(* `const nan` is a NaN. *)
Lemma cnan_nan : nan cnan.
Proof. unfold IeeeOperations.cnan. exact (proj2_sig nan_const). Qed.

Lemma unord_nan_l : forall a b : float, nan a -> unord a b = true.
Proof. intros a b N. unfold nan in N. unfold IeeeUpwardOperations.unord. now rewrite N. Qed.

Lemma unord_nan_r : forall a b : float, nan b -> unord a b = true.
Proof.
intros a b N. unfold nan in N. unfold IeeeUpwardOperations.unord. rewrite N. apply orb_true_r.
Qed.

Lemma unord_not_nan : forall a b : float, ~ nan a -> ~ nan b -> unord a b = false.
Proof.
intros a b Na Nb. unfold IeeeUpwardOperations.unord.
now rewrite (upward_not_nan_false prec emax a Na), (upward_not_nan_false prec emax b Nb).
Qed.

(* The test of emptiness of the listings, on a canonical state: unord(u, u), unord(n, n). *)
Theorem unord_state :
  forall u n : float, upward_1 u n ->
  (unord u u = true <-> upward_empty_1 u n) /\ (unord n n = true <-> upward_empty_1 u n).
Proof.
intros u n [E|H].
- destruct E as [Nu Nn].
  split; split; intros _; try (split; assumption); apply unord_nan_l; assumption.
- destruct (upward_nonempty_lanes prec emax u n H) as [Nu [Nn _]].
  rewrite (unord_not_nan u u Nu Nu), (unord_not_nan n n Nn Nn).
  split; split; intros K; try discriminate K;
    exfalso; exact (upward_empty_not_nonempty prec emax u n K H).
Qed.

(* On two canonical states: unord(xu, yu) and unord(xn, yn) are true exactly when one of the
   states is empty. *)
Theorem unord_states :
  forall xu xn yu yn : float, upward_1 xu xn -> upward_1 yu yn ->
  (unord xu yu = true <-> upward_empty_1 xu xn \/ upward_empty_1 yu yn) /\
  (unord xn yn = true <-> upward_empty_1 xu xn \/ upward_empty_1 yu yn).
Proof.
intros xu xn yu yn CX CY. destruct CX as [EX|NX].
- assert (EX' := EX). destruct EX' as [Nu Nn].
  split; split; intros _; try (left; exact EX); apply unord_nan_l; assumption.
- destruct CY as [EY|NY].
  + assert (EY' := EY). destruct EY' as [Mu Mn].
    split; split; intros _; try (right; exact EY); apply unord_nan_r; assumption.
  + destruct (upward_nonempty_lanes prec emax xu xn NX) as [Nu [Nn _]].
    destruct (upward_nonempty_lanes prec emax yu yn NY) as [Mu [Mn _]].
    rewrite (unord_not_nan xu yu Nu Mu), (unord_not_nan xn yn Nn Mn).
    split; split; intros K; try discriminate K; exfalso; destruct K as [E|E];
      first [exact (upward_empty_not_nonempty prec emax _ _ E NX)
            |exact (upward_empty_not_nonempty prec emax _ _ E NY)].
Qed.

(* abs stands for the absolute value of the extended real number. *)
Lemma xval_abs : forall a : float, xv (fabs a) = xabs (xv a).
Proof.
intros a. destruct (finite_dec prec emax a) as [F|F].
- assert (F' : fin (fabs a)) by (rewrite (abs_finite prec emax nan_abs); exact F).
  rewrite (xval_fin prec emax _ F'), (xval_fin prec emax _ F). cbn [xabs]. f_equal.
  apply (abs_val prec emax nan_abs).
- destruct a as [s|s|s pl H|s m e H]; try discriminate F; reflexivity.
Qed.

(* The test of upward_mul_num_1 for a number t that is infinite or a NaN, on two lanes p and q
   of a nonempty state: s = add_ru(abs(p), abs(q)) is +0, and lt(0, s) is false, when both
   lanes are zeros (the state [0, 0]); otherwise lt(0, s) is true. *)
Theorem whole_mul_test :
  forall p q : float, upward_lane p -> upward_lane q ->
  ((xv p = XFin 0 /\ xv q = XFin 0) ->
   xv (add_ru (fabs p) (fabs q)) = XFin 0 /\ flt pzero (add_ru (fabs p) (fabs q)) = false) /\
  (~ (xv p = XFin 0 /\ xv q = XFin 0) -> flt pzero (add_ru (fabs p) (fabs q)) = true).
Proof.
intros p q Hp Hq. rewrite (lt_xval prec emax), add_ru_xval, 2!xval_abs, (xval_pzero prec emax).
apply upward_lane_xval in Hp. apply upward_lane_xval in Hq.
destruct Hp as [Vp|[x Vp]]; destruct Hq as [Vq|[y Vq]]; rewrite Vp, Vq; cbn [xabs xadd];
  try (split; [intros [K1 K2]; discriminate|intros _; reflexivity]).
split.
- intros [Ex Ey]. injection Ex. injection Ey. intros Ey' Ex'. subst x y.
  rewrite Rabs_R0, Rplus_0_r, (xru_0 prec emax). split; [reflexivity|].
  cbn. apply Rlt_bool_false. lra.
- intros Z.
  assert (P : 0 < Rabs x + Rabs y).
  { destruct (Req_dec x 0) as [Ex|Ex]; destruct (Req_dec y 0) as [Ey|Ey].
    - elim Z. subst x y. split; reflexivity.
    - generalize (Rabs_pos x) (Rabs_pos_lt y Ey). lra.
    - generalize (Rabs_pos_lt x Ex) (Rabs_pos y). lra.
    - generalize (Rabs_pos_lt x Ex) (Rabs_pos y). lra. }
  rewrite (xru_real prec emax). generalize (Omega_gt_0 prec emax). intros P0.
  destruct (Rlt_bool_spec Om (Rabs x + Rabs y)); [reflexivity|].
  rewrite Rlt_bool_false by lra. cbn [xlt]. apply Rlt_bool_true.
  destruct (round_UP_pt radix2 fexp (Rabs x + Rabs y)) as [_ [G _]]. unfold RU. lra.
Qed.

End IeeeUpwardOps.

Arguments upward_lane {prec emax} a.
