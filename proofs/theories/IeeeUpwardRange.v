(* The exact ranges of the arithmetic operations of the round-up interval on states, and what
   the statements of its arithmetic kernels share (docs/developer/design/upward.md,
   "Statements": I1 to I5).

   Notation: as in IeeeUpwardOps.v. A state (u, n) is the interval [-n, u]; its members are
   in_upward_1 u n, those of a number t of the program in_number_1 t (IeeeUpwardVocabulary.v);
   the exact range of an operation and its bounds are range_1, range_2, range_lower and
   range_upper of IeeeIntervalVocabulary.v.

   What is proved.
   - The bounds of the exact range on nonempty states, as extended real numbers, from the
     lemmas of IeeeInterval1.v on intervals of extended real numbers: x + y
     (upward_range_add), x - y (upward_range_sub), -x (upward_range_neg), x * y
     (upward_range_mul: the least and the greatest of the four products of bounds with
     0 * infinity = 0); x + t and x * t for a finite t (upward_range_add_num,
     upward_range_mul_num); and for a t that is infinite or a NaN, whose members are every
     real number (upward_range_add_whole: the whole line; upward_range_mul_whole: [0, 0] for
     x = [0, 0], the whole line otherwise); for bounded operands and a finite t these bounds
     are real numbers (upward_range_add_real and the others of that name).
   - upward_arith_facts: the five conclusions of an arithmetic statement, I1 the result is
     canonical, I2 it is empty exactly when an operand is, I3 it contains the exact range, I4
     its bounds are the bounds of the exact range rounded outward, I5 for bounded operands it
     is bounded exactly when the exact range is within Omega, from what a kernel computes: two
     NaN lanes when an operand is empty, and otherwise -n = xrd lo and u = xru hi for the
     bounds lo and hi of the exact range. upward_binary_facts and upward_number_facts are the
     same in the shapes of the statements of the kernels of two states and of a state and a
     number. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import IeeeBridge IeeeVocabulary IeeeOps IeeeExt IeeeDirected.
From Kairn Require Import Rectangle IeeeIntervalVocabulary IeeeInterval1.
From Kairn Require Import IeeeUpwardVocabulary IeeeUpwardMax IeeeUpwardOps.
Open Scope R_scope.

(** * Sets of real numbers *)

Lemma range_2_ext :
  forall (op : R -> R -> R) (X X' Y Y' : R -> Prop),
  (forall x : R, X x <-> X' x) -> (forall y : R, Y y <-> Y' y) ->
  forall z : R, range_2 op X Y z <-> range_2 op X' Y' z.
Proof.
intros op X X' Y Y' HX HY z.
split; intros [x [y [Hx [Hy E]]]]; exists x, y;
  (split; [now apply HX|split; [now apply HY|exact E]]).
Qed.

Lemma xmin_idem : forall v : xreal, xmin v v = v.
Proof. intros v. unfold xmin. now destruct (xlt v v). Qed.

Lemma xmax_idem : forall v : xreal, xmax v v = v.
Proof. intros v. unfold xmax. now destruct (xlt v v). Qed.

Section IeeeUpwardRange.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation xv := (@xval prec emax).
Notation Om := (Omega prec emax).

(** * The bounds of the exact ranges, on states *)

Theorem upward_range_add :
  forall xu xn yu yn : float,
  upward_nonempty_1 xu xn -> upward_nonempty_1 yu yn ->
  range_lower (range_2 (fun x y : R => x + y) (in_upward_1 xu xn) (in_upward_1 yu yn))
    (xadd (xopp (xv xn)) (xopp (xv yn))) /\
  range_upper (range_2 (fun x y : R => x + y) (in_upward_1 xu xn) (in_upward_1 yu yn))
    (xadd (xv xu) (xv yu)).
Proof.
intros xu xn yu yn HX HY. split.
- exact (range_add_lower (xopp (xv xn)) (xv xu) (xopp (xv yn)) (xv yu) HX HY).
- exact (range_add_upper (xopp (xv xn)) (xv xu) (xopp (xv yn)) (xv yu) HX HY).
Qed.

Theorem upward_range_sub :
  forall xu xn yu yn : float,
  upward_nonempty_1 xu xn -> upward_nonempty_1 yu yn ->
  range_lower (range_2 (fun x y : R => x - y) (in_upward_1 xu xn) (in_upward_1 yu yn))
    (xadd (xopp (xv xn)) (xopp (xv yu))) /\
  range_upper (range_2 (fun x y : R => x - y) (in_upward_1 xu xn) (in_upward_1 yu yn))
    (xadd (xv xu) (xv yn)).
Proof.
intros xu xn yu yn HX HY. split.
- exact (range_sub_lower (xopp (xv xn)) (xv xu) (xopp (xv yn)) (xv yu) HX HY).
- generalize (range_sub_upper (xopp (xv xn)) (xv xu) (xopp (xv yn)) (xv yu) HX HY).
  now rewrite xopp_involutive.
Qed.

Theorem upward_range_neg :
  forall xu xn : float,
  upward_nonempty_1 xu xn ->
  range_lower (range_1 (fun x : R => - x) (in_upward_1 xu xn)) (xopp (xv xu)) /\
  range_upper (range_1 (fun x : R => - x) (in_upward_1 xu xn)) (xv xn).
Proof.
intros xu xn HX. split.
- exact (range_neg_lower (xopp (xv xn)) (xv xu) HX).
- generalize (range_neg_upper (xopp (xv xn)) (xv xu) HX). now rewrite xopp_involutive.
Qed.

Theorem upward_range_mul :
  forall xu xn yu yn : float,
  upward_nonempty_1 xu xn -> upward_nonempty_1 yu yn ->
  let a := xopp (xv xn) in let b := xv xu in let c := xopp (xv yn) in let d := xv yu in
  range_lower (range_2 (fun x y : R => x * y) (in_upward_1 xu xn) (in_upward_1 yu yn))
    (xmin (xmin (xmul0 a c) (xmul0 a d)) (xmin (xmul0 b c) (xmul0 b d))) /\
  range_upper (range_2 (fun x y : R => x * y) (in_upward_1 xu xn) (in_upward_1 yu yn))
    (xmax (xmax (xmul0 a c) (xmul0 a d)) (xmax (xmul0 b c) (xmul0 b d))).
Proof.
intros xu xn yu yn HX HY a b c d. split.
- exact (range_mul_lower a b c d HX HY).
- exact (range_mul_upper a b c d HX HY).
Qed.

(* A finite number t is the interval [t, t]. *)
Lemma number_nonempty : forall t : float, finite t -> xnonempty (xv t) (xv t).
Proof.
intros t F. rewrite (upward_xval_finite prec emax t F).
split; [cbn; apply Rle_bool_true; apply Rle_refl|split; reflexivity].
Qed.

Lemma number_range_ext :
  forall (op : R -> R -> R) (X : R -> Prop) (t : float), finite t ->
  forall z : R, range_2 op X (xmember (xv t) (xv t)) z <-> range_2 op X (in_number_1 t) z.
Proof.
intros op X t F z. apply range_2_ext; [intros x; tauto|].
intros y. symmetry. exact (in_number_1_xmember prec emax t y F).
Qed.

Theorem upward_range_add_num :
  forall xu xn t : float,
  upward_nonempty_1 xu xn -> finite t ->
  range_lower (range_2 (fun x y : R => x + y) (in_upward_1 xu xn) (in_number_1 t))
    (xadd (xopp (xv xn)) (xv t)) /\
  range_upper (range_2 (fun x y : R => x + y) (in_upward_1 xu xn) (in_number_1 t))
    (xadd (xv xu) (xv t)).
Proof.
intros xu xn t HX F. assert (HT := number_nonempty t F). split.
- apply range_lower_ext with (1 := number_range_ext _ _ t F).
  exact (range_add_lower (xopp (xv xn)) (xv xu) (xv t) (xv t) HX HT).
- apply range_upper_ext with (1 := number_range_ext _ _ t F).
  exact (range_add_upper (xopp (xv xn)) (xv xu) (xv t) (xv t) HX HT).
Qed.

Theorem upward_range_mul_num :
  forall xu xn t : float,
  upward_nonempty_1 xu xn -> finite t ->
  let a := xopp (xv xn) in let b := xv xu in let T := xv t in
  range_lower (range_2 (fun x y : R => x * y) (in_upward_1 xu xn) (in_number_1 t))
    (xmin (xmul0 a T) (xmul0 b T)) /\
  range_upper (range_2 (fun x y : R => x * y) (in_upward_1 xu xn) (in_number_1 t))
    (xmax (xmul0 a T) (xmul0 b T)).
Proof.
intros xu xn t HX F a b T. assert (HT := number_nonempty t F). split.
- apply range_lower_ext with (1 := number_range_ext _ _ t F).
  generalize (range_mul_lower a b T T HX HT). now rewrite 2!xmin_idem.
- apply range_upper_ext with (1 := number_range_ext _ _ t F).
  generalize (range_mul_upper a b T T HX HT). now rewrite 2!xmax_idem.
Qed.

(* A number t that is infinite or a NaN stands for the whole line: x + t is the whole line. *)
Theorem upward_range_add_whole :
  forall xu xn t : float,
  upward_nonempty_1 xu xn -> ~ finite t ->
  range_lower (range_2 (fun x y : R => x + y) (in_upward_1 xu xn) (in_number_1 t)) (XInf true) /\
  range_upper (range_2 (fun x y : R => x + y) (in_upward_1 xu xn) (in_number_1 t)) (XInf false).
Proof.
intros xu xn t HX F. destruct (upward_nonempty_member prec emax xu xn HX) as [x0 Hx0].
split; split.
- intros z _. reflexivity.
- intros s _. exists (s - 1). split; [|lra].
  exists x0, (s - 1 - x0). split; [exact Hx0|split; [now apply in_number_1_not_finite|]].
  cbv beta. ring.
- intros z _. reflexivity.
- intros s _. exists (s + 1). split; [|lra].
  exists x0, (s + 1 - x0). split; [exact Hx0|split; [now apply in_number_1_not_finite|]].
  cbv beta. ring.
Qed.

(* A nonempty state other than [0, 0] has a member that is not zero. *)
Lemma upward_nonzero_member :
  forall u n : float, upward_nonempty_1 u n -> ~ (xv u = XFin 0 /\ xv n = XFin 0) ->
  exists x : R, in_upward_1 u n x /\ x <> 0.
Proof.
intros u n H Z. destruct (upward_nonempty_lane_values prec emax u n H) as [Lu Ln].
unfold in_upward_1. unfold upward_nonempty_1 in H.
destruct Lu as [Eu|[b Eu]].
- (* no upper bound: a member above 1 *)
  assert (K : xlt (XFin 1) (xv u) = true) by (rewrite Eu; reflexivity).
  destruct (xmember_approach_upper _ _ H 1 K) as [x [X1 X2]].
  exists x. split; [exact X1|lra].
- destruct (Req_dec b 0) as [Eb|Nb].
  + (* the upper bound 0: the lower bound is below 0 *)
    subst b. destruct Ln as [En|[c En]].
    * assert (K : xlt (xopp (xv n)) (XFin (- 1)) = true) by (rewrite En; reflexivity).
      destruct (xmember_approach_lower _ _ H (- 1) K) as [x [X1 X2]].
      exists x. split; [exact X1|lra].
    * assert (Nc : c <> 0) by (intros Ec; apply Z; split; [exact Eu|rewrite En, Ec; reflexivity]).
      exists (- c). split; [|lra].
      rewrite En in H |- *. cbn [xopp] in H |- *. now apply xmember_lower.
  + (* the upper bound itself *)
    exists b. split; [|exact Nb]. rewrite Eu in H |- *. now apply xmember_upper.
Qed.

(* x * t for a t that is infinite or a NaN: [0, 0] for x = [0, 0], the whole line otherwise. *)
Theorem upward_range_mul_whole :
  forall xu xn t : float,
  upward_nonempty_1 xu xn -> ~ finite t ->
  let A := range_2 (fun x y : R => x * y) (in_upward_1 xu xn) (in_number_1 t) in
  ((xv xu = XFin 0 /\ xv xn = XFin 0) -> range_lower A (XFin 0) /\ range_upper A (XFin 0)) /\
  (~ (xv xu = XFin 0 /\ xv xn = XFin 0) -> range_lower A (XInf true) /\ range_upper A (XInf false)).
Proof.
intros xu xn t HX F A. split.
- intros [Eu En].
  assert (Mem : forall z : R, A z -> z = 0).
  { intros z [x [y [Hx [_ E]]]]. rewrite in_upward_1_iff, Eu, En in Hx. cbv beta in E.
    destruct Hx as [H1 H2]. revert H1 H2. cbn [xle].
    destruct (Rle_bool_spec x 0); destruct (Rle_bool_spec (- x) 0); intros H1 H2;
      try discriminate. assert (x = 0) by lra. subst x. rewrite E. ring. }
  assert (Zm : A 0).
  { exists 0, 0. split; [|split; [now apply in_number_1_not_finite|cbv beta; ring]].
    rewrite in_upward_1_iff, Eu, En. cbn [xle].
    split; apply Rle_bool_true; lra. }
  split; split.
  + intros z Hz. rewrite (Mem z Hz). cbn. apply Rle_bool_true. lra.
  + intros s Hs. exists 0. split; [exact Zm|]. cbn in Hs. now apply Rlt_bool_inv.
  + intros z Hz. rewrite (Mem z Hz). cbn. apply Rle_bool_true. lra.
  + intros s Hs. exists 0. split; [exact Zm|]. cbn in Hs. now apply Rlt_bool_inv.
- intros Z. destruct (upward_nonzero_member xu xn HX Z) as [x0 [Hx0 N0]].
  split; split.
  + intros z _. reflexivity.
  + intros s _. exists (s - 1). split; [|lra].
    exists x0, ((s - 1) / x0). split; [exact Hx0|split; [now apply in_number_1_not_finite|]].
    cbv beta. field. exact N0.
  + intros z _. reflexivity.
  + intros s _. exists (s + 1). split; [|lra].
    exists x0, ((s + 1) / x0). split; [exact Hx0|split; [now apply in_number_1_not_finite|]].
    cbv beta. field. exact N0.
Qed.

(** * For bounded operands the bounds are real numbers *)

Lemma upward_bounded_values :
  forall u n : float, upward_bounded_1 u n -> xv u = XFin (val u) /\ xv n = XFin (val n).
Proof. intros u n [Fu Fn]. split; now apply upward_xval_finite. Qed.

Lemma xmin_real :
  forall v w : xreal, (exists r, v = XFin r) -> (exists r, w = XFin r) -> exists r, xmin v w = XFin r.
Proof. intros v w Hv Hw. destruct (xmin_cases v w) as [E|E]; now rewrite E. Qed.

Lemma xmax_real :
  forall v w : xreal, (exists r, v = XFin r) -> (exists r, w = XFin r) -> exists r, xmax v w = XFin r.
Proof. intros v w Hv Hw. destruct (xmax_cases v w) as [E|E]; now rewrite E. Qed.

Theorem upward_range_add_real :
  forall xu xn yu yn : float, upward_bounded_1 xu xn -> upward_bounded_1 yu yn ->
  (exists r : R, xadd (xopp (xv xn)) (xopp (xv yn)) = XFin r) /\
  (exists r : R, xadd (xv xu) (xv yu) = XFin r).
Proof.
intros xu xn yu yn BX BY.
destruct (upward_bounded_values xu xn BX) as [Eu En].
destruct (upward_bounded_values yu yn BY) as [Fu Fn].
rewrite Eu, En, Fu, Fn. split; eexists; reflexivity.
Qed.

Theorem upward_range_sub_real :
  forall xu xn yu yn : float, upward_bounded_1 xu xn -> upward_bounded_1 yu yn ->
  (exists r : R, xadd (xopp (xv xn)) (xopp (xv yu)) = XFin r) /\
  (exists r : R, xadd (xv xu) (xv yn) = XFin r).
Proof.
intros xu xn yu yn BX BY.
destruct (upward_bounded_values xu xn BX) as [Eu En].
destruct (upward_bounded_values yu yn BY) as [Fu Fn].
rewrite Eu, En, Fu, Fn. split; eexists; reflexivity.
Qed.

Theorem upward_range_mul_real :
  forall xu xn yu yn : float, upward_bounded_1 xu xn -> upward_bounded_1 yu yn ->
  let a := xopp (xv xn) in let b := xv xu in let c := xopp (xv yn) in let d := xv yu in
  (exists r : R, xmin (xmin (xmul0 a c) (xmul0 a d)) (xmin (xmul0 b c) (xmul0 b d)) = XFin r) /\
  (exists r : R, xmax (xmax (xmul0 a c) (xmul0 a d)) (xmax (xmul0 b c) (xmul0 b d)) = XFin r).
Proof.
intros xu xn yu yn BX BY a b c d.
destruct (upward_bounded_values xu xn BX) as [Eu En].
destruct (upward_bounded_values yu yn BY) as [Fu Fn].
unfold a, b, c, d. rewrite Eu, En, Fu, Fn. cbn [xopp xmul0].
split; repeat (apply xmin_real || apply xmax_real); eexists; reflexivity.
Qed.

Theorem upward_range_add_num_real :
  forall xu xn t : float, upward_bounded_1 xu xn -> finite t ->
  (exists r : R, xadd (xopp (xv xn)) (xv t) = XFin r) /\ (exists r : R, xadd (xv xu) (xv t) = XFin r).
Proof.
intros xu xn t BX Ft. destruct (upward_bounded_values xu xn BX) as [Eu En].
rewrite Eu, En, (upward_xval_finite prec emax t Ft). split; eexists; reflexivity.
Qed.

Theorem upward_range_mul_num_real :
  forall xu xn t : float, upward_bounded_1 xu xn -> finite t ->
  let a := xopp (xv xn) in let b := xv xu in let T := xv t in
  (exists r : R, xmin (xmul0 a T) (xmul0 b T) = XFin r) /\
  (exists r : R, xmax (xmul0 a T) (xmul0 b T) = XFin r).
Proof.
intros xu xn t BX Ft a b T. destruct (upward_bounded_values xu xn BX) as [Eu En].
unfold a, b, T. rewrite Eu, En, (upward_xval_finite prec emax t Ft). cbn [xopp xmul0].
split; repeat (apply xmin_real || apply xmax_real); eexists; reflexivity.
Qed.

(** * What the statements of the arithmetic kernels share *)

(* A canonical result from what the kernel computes. A is the exact range; E says that an
   operand is empty, N that the operands are nonempty (one or the other holds); B that the
   operands are bounded. When an operand is empty the range has no member and the result is
   the empty set; when the operands are nonempty the range has a member, lo and hi are its
   bounds, and the lanes of the result are -n = xrd lo and u = xru hi; bounded operands are
   nonempty and give real bounds. Then I1 to I5. *)
Theorem upward_arith_facts :
  forall (A : R -> Prop) (E N B : Prop) (zu zn : float) (lo hi : xreal),
  E \/ N ->
  (E -> forall z : R, ~ A z) ->
  (N -> exists z : R, A z) ->
  (E -> upward_empty_1 zu zn) ->
  (N -> range_lower A lo /\ range_upper A hi /\
        xopp (xv zn) = xrd prec emax lo /\ xv zu = xru prec emax hi) ->
  (B -> N /\ (exists r : R, lo = XFin r) /\ (exists r : R, hi = XFin r)) ->
  upward_1 zu zn /\
  (upward_empty_1 zu zn <-> E) /\
  (forall z : R, A z -> in_upward_1 zu zn z) /\
  (N -> forall lo' hi' : xreal, range_lower A lo' -> range_upper A hi' ->
        xopp (xv zn) = xrd prec emax lo' /\ xv zu = xru prec emax hi') /\
  (B -> (upward_bounded_1 zu zn <-> forall z : R, A z -> Rabs z <= omega prec emax)).
Proof.
intros A E N B zu zn lo hi EN EA NA EZ NZ BN.
(* I3 *)
assert (I3 : forall z : R, A z -> in_upward_1 zu zn z).
{ intros z Hz. destruct EN as [HE|HN]; [elim (EA HE z Hz)|].
  destruct (NZ HN) as [[L _] [[U _] [El Eu]]].
  unfold in_upward_1, xmember. rewrite El, Eu. split.
  - apply (xrd_below prec emax). now apply L.
  - apply (xru_above prec emax). now apply U. }
assert (NE : N -> upward_nonempty_1 zu zn).
{ intros HN. destruct (NA HN) as [z Hz]. exact (in_upward_nonempty prec emax zu zn z (I3 z Hz)). }
split; [|split; [|split; [exact I3|split]]].
- (* I1 *)
  destruct EN as [HE|HN]; [left; exact (EZ HE)|right; exact (NE HN)].
- (* I2 *)
  split; [|exact EZ].
  intros Z. destruct EN as [HE|HN]; [exact HE|].
  exfalso. exact (upward_empty_not_nonempty prec emax zu zn Z (NE HN)).
- (* I4 *)
  intros HN lo' hi' Hlo Hhi. destruct (NZ HN) as [L [U [El Eu]]].
  rewrite (range_lower_unique A lo' lo (NA HN) Hlo L), (range_upper_unique A hi' hi (NA HN) Hhi U).
  now split.
- (* I5 *)
  intros HB. destruct (BN HB) as [HN [[rl Elo] [rh Ehi]]].
  destruct (NZ HN) as [[L1 L2] [[U1 U2] [El Eu]]]. split.
  + intros [Fu Fn] z Hz. destruct (I3 z Hz) as [K1 K2].
    rewrite (upward_xval_finite prec emax zu Fu) in K2.
    rewrite (upward_xval_finite prec emax zn Fn) in K1. cbn [xopp xle] in K1, K2.
    apply Rle_bool_inv in K1. apply Rle_bool_inv in K2.
    generalize (b2r_Omega prec emax zu) (b2r_Omega prec emax zn). unfold val in *.
    intros P Q. change (omega prec emax) with Om. apply Rabs_le. lra.
  + intros W. change (omega prec emax) with Om in W. subst lo hi. split.
    * (* the upper lane: hi <= Omega *)
      assert (Fh : xfin (xru prec emax (XFin rh))).
      { apply (xru_fin prec emax). apply Rnot_lt_le. intros K.
        assert (T : xlt (XFin Om) (XFin rh) = true) by (cbn; now apply Rlt_bool_true).
        destruct (U2 Om T) as [z [Hz Lz]]. assert (Q := Rabs_le_inv _ _ (W z Hz)). lra. }
      rewrite <- Eu in Fh. destruct (xv zu) as [| |r] eqn:V; try contradiction.
      exact (proj1 (upward_xval_real prec emax zu r V)).
    * (* the lower lane: lo >= -Omega *)
      assert (Fl : xfin (xrd prec emax (XFin rl))).
      { apply (xrd_fin prec emax). apply Rnot_lt_le. intros K.
        assert (T : xlt (XFin rl) (XFin (- Om)) = true) by (cbn; now apply Rlt_bool_true).
        destruct (L2 (- Om) T) as [z [Hz Lz]]. assert (Q := Rabs_le_inv _ _ (W z Hz)). lra. }
      rewrite <- El in Fl. destruct (xv zn) as [| |r] eqn:V; cbn in Fl; try contradiction.
      exact (proj1 (upward_xval_real prec emax zn r V)).
Qed.

(* The shape of the statements of the kernels of two states: sum, difference, product. *)
Corollary upward_binary_facts :
  forall (op : R -> R -> R) (xu xn yu yn zu zn : float) (lo hi : xreal),
  upward_1 xu xn -> upward_1 yu yn ->
  (upward_empty_1 xu xn \/ upward_empty_1 yu yn -> upward_empty_1 zu zn) ->
  (upward_nonempty_1 xu xn -> upward_nonempty_1 yu yn ->
   range_lower (range_2 op (in_upward_1 xu xn) (in_upward_1 yu yn)) lo /\
   range_upper (range_2 op (in_upward_1 xu xn) (in_upward_1 yu yn)) hi /\
   xopp (xv zn) = xrd prec emax lo /\ xv zu = xru prec emax hi) ->
  (upward_bounded_1 xu xn -> upward_bounded_1 yu yn ->
   (exists r : R, lo = XFin r) /\ (exists r : R, hi = XFin r)) ->
  upward_1 zu zn /\
  (upward_empty_1 zu zn <-> upward_empty_1 xu xn \/ upward_empty_1 yu yn) /\
  (forall x y : R, in_upward_1 xu xn x -> in_upward_1 yu yn y -> in_upward_1 zu zn (op x y)) /\
  (upward_nonempty_1 xu xn -> upward_nonempty_1 yu yn ->
   forall lo' hi' : xreal,
   range_lower (range_2 op (in_upward_1 xu xn) (in_upward_1 yu yn)) lo' ->
   range_upper (range_2 op (in_upward_1 xu xn) (in_upward_1 yu yn)) hi' ->
   xopp (xv zn) = xrd prec emax lo' /\ xv zu = xru prec emax hi') /\
  (upward_bounded_1 xu xn -> upward_bounded_1 yu yn ->
   (upward_bounded_1 zu zn <->
    forall z : R, range_2 op (in_upward_1 xu xn) (in_upward_1 yu yn) z ->
    Rabs z <= omega prec emax)).
Proof.
intros op xu xn yu yn zu zn lo hi CX CY EZ NZ BF.
assert (EN : (upward_empty_1 xu xn \/ upward_empty_1 yu yn) \/
             (upward_nonempty_1 xu xn /\ upward_nonempty_1 yu yn)).
{ destruct CX as [EX|NX]; [left; now left|]. destruct CY as [EY|NY]; [left; now right|].
  right. now split. }
destruct (upward_arith_facts (range_2 op (in_upward_1 xu xn) (in_upward_1 yu yn))
            (upward_empty_1 xu xn \/ upward_empty_1 yu yn)
            (upward_nonempty_1 xu xn /\ upward_nonempty_1 yu yn)
            (upward_bounded_1 xu xn /\ upward_bounded_1 yu yn) zu zn lo hi EN)
  as [I1 [I2 [I3 [I4 I5]]]].
- intros [EX|EY] z [x [y [Hx [Hy _]]]].
  + exact (upward_empty_no_member prec emax xu xn x EX Hx).
  + exact (upward_empty_no_member prec emax yu yn y EY Hy).
- intros [NX NY]. destruct (upward_nonempty_member prec emax xu xn NX) as [x Hx].
  destruct (upward_nonempty_member prec emax yu yn NY) as [y Hy].
  exists (op x y), x, y. now split.
- exact EZ.
- intros [NX NY]. exact (NZ NX NY).
- intros [BX BY]. split; [split; now apply upward_bounded_nonempty|exact (BF BX BY)].
- split; [exact I1|split; [exact I2|split; [|split]]].
  + intros x y Hx Hy. apply I3. exists x, y. now split.
  + intros NX NY. exact (I4 (conj NX NY)).
  + intros BX BY. exact (I5 (conj BX BY)).
Qed.

(* The shape of the statements of the kernels of a state and a number: x + t, x * t. *)
Corollary upward_number_facts :
  forall (op : R -> R -> R) (xu xn t zu zn : float) (lo hi : xreal),
  upward_1 xu xn ->
  (upward_empty_1 xu xn -> upward_empty_1 zu zn) ->
  (upward_nonempty_1 xu xn ->
   range_lower (range_2 op (in_upward_1 xu xn) (in_number_1 t)) lo /\
   range_upper (range_2 op (in_upward_1 xu xn) (in_number_1 t)) hi /\
   xopp (xv zn) = xrd prec emax lo /\ xv zu = xru prec emax hi) ->
  (upward_bounded_1 xu xn -> finite t ->
   (exists r : R, lo = XFin r) /\ (exists r : R, hi = XFin r)) ->
  upward_1 zu zn /\
  (upward_empty_1 zu zn <-> upward_empty_1 xu xn) /\
  (forall x y : R, in_upward_1 xu xn x -> in_number_1 t y -> in_upward_1 zu zn (op x y)) /\
  (upward_nonempty_1 xu xn ->
   forall lo' hi' : xreal,
   range_lower (range_2 op (in_upward_1 xu xn) (in_number_1 t)) lo' ->
   range_upper (range_2 op (in_upward_1 xu xn) (in_number_1 t)) hi' ->
   xopp (xv zn) = xrd prec emax lo' /\ xv zu = xru prec emax hi') /\
  (upward_bounded_1 xu xn -> finite t ->
   (upward_bounded_1 zu zn <->
    forall z : R, range_2 op (in_upward_1 xu xn) (in_number_1 t) z ->
    Rabs z <= omega prec emax)).
Proof.
intros op xu xn t zu zn lo hi CX EZ NZ BF.
assert (EN : upward_empty_1 xu xn \/ upward_nonempty_1 xu xn) by exact CX.
destruct (upward_arith_facts (range_2 op (in_upward_1 xu xn) (in_number_1 t))
            (upward_empty_1 xu xn) (upward_nonempty_1 xu xn)
            (upward_bounded_1 xu xn /\ finite t) zu zn lo hi EN)
  as [I1 [I2 [I3 [I4 I5]]]].
- intros EX z [x [y [Hx _]]]. exact (upward_empty_no_member prec emax xu xn x EX Hx).
- intros NX. destruct (upward_nonempty_member prec emax xu xn NX) as [x Hx].
  exists (op x (val t)), x, (val t). split; [exact Hx|split; [apply in_number_1_member|reflexivity]].
- exact EZ.
- exact NZ.
- intros [BX Ft]. split; [now apply upward_bounded_nonempty|exact (BF BX Ft)].
- split; [exact I1|split; [exact I2|split; [|split; [exact I4|]]]].
  + intros x y Hx Hy. apply I3. exists x, y. now split.
  + intros BX Ft. exact (I5 (conj BX Ft)).
Qed.

End IeeeUpwardRange.
