(* The predicates and the three-valued comparisons of balls with a center of one limb, in the
   IEEE model, on all values (docs/developer/design/milestone2.md, "One enclosure interface",
   "Comparisons" and "Exact pairs"; docs/developer/architecture.md, "Claims of the enclosure
   interface: predicates and comparisons"): ball_contains_point_1, ball_contains_ball_1,
   ball_positive_1, ball_negative_1, ball_zero_1, ball_less_1, ball_less_equal_1 and
   ball_equal_1.

   Notation as in IeeeIntervalPredicates.v. A ball of one limb (c, r) is canonical: finite
   (c and r finite, r >= 0), the whole line ((+-0, +inf)) or the empty set ((NaN, NaN)), and
   its members are those of in_ball_1. X = (cx, rx) and Y = (cy, ry) are the operands.

   What is proved, for canonical operands. ball_contains_point_1, ball_contains_ball_1 and the
   three signs are exact: the mask is true exactly when the relation holds. The three
   comparisons are certain (an answer given is right) and exact on the special states and,
   for finite balls, whenever the sum of the radii is at most Omega: then yes is true exactly
   when the relation holds for every choice of members, and no exactly when it fails for every
   choice. When the sum of the radii overflows, both answers are false. From precision 2 for
   the kernels that make exact pairs (two_sum_ord), for every precision for the signs. The
   theorems K_correct at the end are the generated statements.

   The proofs. A canonical ball is an interval of extended real numbers, [c - r, c + r] for a
   finite ball, [-inf, +inf] for the whole line and the empty pair for the empty set
   (xlo_1, xhi_1, xball_1), so that every relation is one of IeeeIntervalPredicates.v on these
   bounds (xless, xequal, xsubset, ...). The kernels compare exact pairs: two_sum_ord of two
   finite numbers is either an exact canonical pair whose rounded sum is in range, or, when
   the rounded sum overflows, the pair of opposite infinities of the side of the sum
   (tso_pair). A comparison of an exact pair with any such pair is the comparison of the real
   numbers they stand for (pair_cmp, pair_cmp_r): an overflowed sum is beyond every sum whose
   rounding is in range, since rounding is monotone (overflow_order). The special states give
   NaN or an infinity with a NaN second limb, which the comparisons see as such. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized EFT DirectedSum IeeeBridge IeeeVocabulary IeeeOps IeeeExt.
From Kairn Require Import Rectangle IeeeDirected IeeeIntervalVocabulary IeeeInterval1 IeeeInterval2.
From Kairn Require Import IeeeIntervalExact IeeeIntervalPredicates.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

(** * Three-valued answers, from the cases *)

(* The statement of a three-valued comparison that is certain and exact on S and under F and C,
   from: the relation and its failure exclude each other, the answers are exact on S and under
   F and C, and otherwise they are exact or both false. *)
Lemma trit_from :
  forall (yes no : bool) (R N S F C : Prop),
  ~ (R /\ N) ->
  (S -> (yes = true <-> R) /\ (no = true <-> N)) ->
  (F -> C -> (yes = true <-> R) /\ (no = true <-> N)) ->
  ((yes = true <-> R) /\ (no = true <-> N)) \/ (yes = false /\ no = false) ->
  (yes = true -> R) /\ (no = true -> N) /\ ~ (yes = true /\ no = true) /\
  (S -> (yes = true <-> R) /\ (no = true <-> N)) /\
  (F -> C -> (yes = true <-> R) /\ (no = true <-> N)).
Proof.
intros yes no R N S F C RN HS HF [[Y M]|[Y M]].
- split; [apply Y|split; [apply M|split; [|split; assumption]]].
  intros [A B]. apply RN. split; [apply Y, A|apply M, B].
- subst yes no. split; [intros K; discriminate K|split; [intros K; discriminate K|]].
  split; [intros [K _]; discriminate K|split; assumption].
Qed.

(* Boolean equalities of comparisons of real numbers, by cases. *)
Ltac bools :=
  repeat match goal with
  | |- context [Rabs ?x] =>
      let H := fresh in
      destruct (Rcase_abs x) as [H|H]; [rewrite (Rabs_left x H)|rewrite (Rabs_right x H)]
  | |- context [Rlt_bool ?x ?y] => destruct (Rlt_bool_spec x y)
  | |- context [Rle_bool ?x ?y] => destruct (Rle_bool_spec x y)
  | |- context [Req_bool ?x ?y] => destruct (Req_bool_spec x y)
  end;
  cbn [andb orb negb]; try reflexivity;
  repeat match goal with H : ?x <> ?y |- _ => apply Rdichotomy in H; destruct H end;
  exfalso; lra.

Section BallPredicates1.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus nan_minus : float -> float -> nan_of.
Variable nan_opp nan_abs : float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation flt := (IeeeOperations.lt prec emax).
Notation fle := (IeeeOperations.le prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation ninf := (B754_infinity prec emax true).
Notation xv := (@xval prec emax).
Notation xv2 := (@xval_2 prec emax).
Notation Om := (Omega prec emax).
Notation inrange := (IeeeBridge.inrange emax).
Notation two_sum_ord := (IeeeModel.two_sum_ord prec emax nan_plus nan_minus nan_abs).
Notation lt_2_2 := (IeeeModel.lt_2_2 prec emax).
Notation le_2_2 := (IeeeModel.le_2_2 prec emax).
Notation le_2_1 := (IeeeModel.le_2_1 prec emax).
Notation abs_2 := (IeeeModel.abs_2 prec emax nan_opp).

Let Hp1 : (1 <= prec)%Z.
Proof. generalize prec_gt_0_. unfold Prec_gt_0. lia. Qed.

(** * A canonical ball as an interval of extended real numbers *)

Definition xlo_1 (c r : float) : xreal :=
  if is_finite prec emax r then XFin (b2r c - b2r r)
  else if is_nan prec emax r then XInf false else XInf true.

Definition xhi_1 (c r : float) : xreal :=
  if is_finite prec emax r then XFin (b2r c + b2r r)
  else if is_nan prec emax r then XInf true else XInf false.

Lemma xlohi_fin :
  forall c r : float, fin r -> xlo_1 c r = XFin (b2r c - b2r r) /\ xhi_1 c r = XFin (b2r c + b2r r).
Proof. intros c r F. unfold xlo_1, xhi_1. rewrite F. split; reflexivity. Qed.

Lemma xlohi_whole :
  forall c : float,
  xlo_1 c (infinity prec emax false) = XInf true /\ xhi_1 c (infinity prec emax false) = XInf false.
Proof. intros c. split; reflexivity. Qed.

Lemma xlohi_nan :
  forall c r : float, is_nan prec emax r = true -> xlo_1 c r = XInf false /\ xhi_1 c r = XInf true.
Proof.
intros c r N. unfold xlo_1, xhi_1. rewrite (nan_not_finite prec emax r N), N. split; reflexivity.
Qed.

(* The three states exclude each other. *)
Lemma ball_1_states :
  forall c r : float, ball_1 c r ->
  (ball_finite_1 c r /\ ~ ball_whole_1 c r /\ ~ ball_empty_1 c r) \/
  (ball_whole_1 c r /\ ~ ball_finite_1 c r /\ ~ ball_empty_1 c r) \/
  (ball_empty_1 c r /\ ~ ball_finite_1 c r /\ ~ ball_whole_1 c r).
Proof.
intros c r [F|[W|E]].
- left. split; [exact F|split].
  + intros [_ K]. destruct F as [_ [Fr _]]. rewrite K in Fr. discriminate Fr.
  + intros [K _]. destruct F as [Fc _]. unfold nan in K.
    rewrite (finite_not_nan prec emax c Fc) in K. discriminate K.
- right; left. split; [exact W|split].
  + intros [_ [Fr _]]. destruct W as [_ K]. rewrite K in Fr. discriminate Fr.
  + intros [_ K]. destruct W as [_ K']. rewrite K' in K. discriminate K.
- right; right. split; [exact E|split].
  + intros [Fc _]. destruct E as [K _]. unfold nan in K.
    rewrite (finite_not_nan prec emax c Fc) in K. discriminate K.
  + intros [[s K] _]. destruct E as [K' _]. rewrite K in K'. discriminate K'.
Qed.

(* A canonical ball is the interval [xlo_1, xhi_1] of extended real numbers: the same members,
   and empty exactly when that interval is. *)
Lemma xball_1 :
  forall c r : float, ball_1 c r ->
  xinterval (xlo_1 c r) (xhi_1 c r) /\
  (~ ball_empty_1 c r <-> xnonempty (xlo_1 c r) (xhi_1 c r)) /\
  (forall x : R, in_ball_1 c r x <-> xmember (xlo_1 c r) (xhi_1 c r) x).
Proof.
intros c r B. destruct (ball_1_states c r B) as [[F [NW NE]]|[[W [NF NE]]|[E [NF NW]]]].
- destruct F as [Fc [Fr Pr]]. destruct (xlohi_fin c r Fr) as [El Eh]. rewrite El, Eh.
  unfold val in Pr.
  assert (N : xnonempty (XFin (b2r c - b2r r)) (XFin (b2r c + b2r r))).
  { split; [cbn; apply Rle_bool_true; lra|split; reflexivity]. }
  split; [right; exact N|split; [split; intros _; [exact N|exact NE]|]].
  intros x. unfold in_ball_1, xmember. cbn [xle]. split.
  + intros [K|[_ K]]; [elim (NW K)|].
    apply Rabs_le_inv in K. unfold val in K. split; apply Rle_bool_true; lra.
  + intros [H K]. apply Rle_bool_inv in H. apply Rle_bool_inv in K. right.
    split; [exact (conj Fc (conj Fr Pr))|]. apply Rabs_le. unfold val. lra.
- destruct W as [Zc Er]. subst r. destruct (xlohi_whole c) as [El Eh]. rewrite El, Eh.
  assert (N : xnonempty (XInf true) (XInf false)) by (split; [reflexivity|split; reflexivity]).
  split; [right; exact N|split; [split; intros _; [exact N|exact NE]|]].
  intros x. split; [intros _; split; reflexivity|intros _; left; split; [exact Zc|reflexivity]].
- destruct E as [Nc Nr]. destruct (xlohi_nan c r Nr) as [El Eh]. rewrite El, Eh.
  split; [left; split; reflexivity|split].
  + split; [intros K; elim (K (conj Nc Nr))|intros [_ [K _]]; discriminate K].
  + intros x. split; [intros [K|[K _]]; [elim (NW K)|elim (NF K)]|intros K; elim (xmember_empty x K)].
Qed.

(* The statement of a relation of two balls, read on these intervals. *)
Lemma ball_pair_1 :
  forall cx rx cy ry : float, ball_1 cx rx -> ball_1 cy ry ->
  forall Rel : R -> R -> Prop,
  (~ ball_empty_1 cx rx /\ ~ ball_empty_1 cy ry /\
   (forall x y : R, in_ball_1 cx rx x -> in_ball_1 cy ry y -> Rel x y)) <->
  (xnonempty (xlo_1 cx rx) (xhi_1 cx rx) /\ xnonempty (xlo_1 cy ry) (xhi_1 cy ry) /\
   (forall x y : R, xmember (xlo_1 cx rx) (xhi_1 cx rx) x ->
    xmember (xlo_1 cy ry) (xhi_1 cy ry) y -> Rel x y)).
Proof.
intros cx rx cy ry BX BY Rel.
destruct (xball_1 cx rx BX) as [_ [NX MX]]. destruct (xball_1 cy ry BY) as [_ [NY MY]].
rewrite NX, NY. split; intros [A [B C]]; (split; [exact A|split; [exact B|]]);
  intros x y Hx Hy; apply C; first [apply MX|apply MY]; assumption.
Qed.

(** * The sum of two numbers as an exact pair, or its overflow *)

(* (s, e) is the exact pair of v, whose rounding is in range; or v overflows, and (s, e) is the
   infinity of the side of v followed by the opposite infinity. *)
Definition tso_pair (v : R) (s e : float) : Prop :=
  (fin s /\ canonical_2 s e /\ xv2 s e = XFin v /\ inrange (rnd v)) \/
  (exists sg : bool,
   s = B754_infinity prec emax sg /\ e = B754_infinity prec emax (negb sg) /\
   ~ inrange (rnd v) /\ (if sg then v < 0 else 0 < v)).

Lemma two_sum_ord_fst :
  forall a b : float,
  fst (two_sum_ord a b) = if flt (fabs a) (fabs b) then add b a else add a b.
Proof.
intros a b. unfold IeeeModel.two_sum_ord, IeeeModel.fast_two_sum. cbv zeta.
destruct (flt (fabs a) (fabs b)); reflexivity.
Qed.

Lemma tso_pair_of :
  (2 <= prec)%Z -> forall a b : float, fin a -> fin b ->
  tso_pair (b2r a + b2r b) (fst (two_sum_ord a b)) (snd (two_sum_ord a b)).
Proof.
intros Hp a b Fa Fb.
assert (L : fin (fst (two_sum_ord a b)) <-> inrange (rnd (b2r a + b2r b))).
{ rewrite two_sum_ord_fst. destruct (flt (fabs a) (fabs b)).
  - rewrite Rplus_comm. exact (proj1 (add_spec prec emax nan_plus b a Fb Fa)).
  - exact (proj1 (add_spec prec emax nan_plus a b Fa Fb)). }
revert L.
generalize (two_sum_ord_ieee_finite prec emax nan_plus nan_minus nan_abs Hp a b Fa Fb).
generalize (two_sum_ord_correct emin prec Hp (b2r a) (b2r b)
              (b2r_format prec emax a) (b2r_format prec emax b)).
destruct (two_sum_ord a b) as [s e]. cbn [fst snd].
destruct (Model.two_sum_ord emin prec tie_even (b2r a) (b2r b)) as [ms me].
intros [_ [Esum Nm]] [Hf Hn] L.
destruct (finite_dec prec emax s) as [Fs|Fs].
- destruct (Hf Fs) as [Fe E]. injection E as E1 E2. left.
  split; [exact Fs|split; [left; split; [exact Fs|split; [exact Fe|]]|split]].
  + unfold val. rewrite E1, E2. exact Nm.
  + unfold xval_2. rewrite Fs. unfold val. rewrite E1, E2, Esum. reflexivity.
  + exact (proj1 L Fs).
- destruct (Hn Fs) as [sg [Es [Ee S]]]. right. exists sg.
  split; [exact Es|split; [exact Ee|split]].
  + intros K. apply L in K. rewrite K in Fs. discriminate Fs.
  + generalize (Omega_gt_0 prec emax). destruct sg; simpl in S |- *; lra.
Qed.

(* A rounding in range below one that is not: the sum that overflows is beyond. *)
Lemma overflow_order :
  forall v w : R, inrange (rnd v) -> ~ inrange (rnd w) ->
  (0 < w -> v < w) /\ (w < 0 -> w < v).
Proof.
intros v w Hv Hw. unfold IeeeBridge.inrange in *. split; intros Pw.
- apply Rnot_le_lt. intros K. apply Hw.
  assert (M : rnd w <= rnd v) by (apply round_le; auto with typeclass_instances).
  assert (Z : 0 <= rnd w).
  { apply round_ge_generic; auto with typeclass_instances. apply generic_format_0. lra. }
  apply Rabs_lt_inv in Hv. rewrite Rabs_pos_eq by exact Z. lra.
- apply Rnot_le_lt. intros K. apply Hw.
  assert (M : rnd v <= rnd w) by (apply round_le; auto with typeclass_instances).
  assert (Z : rnd w <= 0).
  { apply round_le_generic; auto with typeclass_instances. apply generic_format_0. lra. }
  apply Rabs_lt_inv in Hv. rewrite Rabs_left1 by exact Z. lra.
Qed.

(* A sum whose rounding overflows is beyond Omega. *)
Lemma overflow_big : forall w : R, ~ inrange (rnd w) -> Om < Rabs w.
Proof.
intros w H. apply Rnot_le_lt. intros K. apply H. now apply (rnd_le_Omega prec emax).
Qed.

(* The exact pair of a value at most Omega in magnitude. *)
Lemma tso_pair_small :
  forall (v : R) (s e : float), tso_pair v s e -> Rabs v <= Om ->
  fin s /\ canonical_2 s e /\ xv2 s e = XFin v /\ inrange (rnd v).
Proof.
intros v s e [P|[sg [_ [_ [N _]]]]] H; [exact P|].
exfalso. apply N. now apply (rnd_le_Omega prec emax).
Qed.

Lemma xval_2_lead_fin : forall (x0 x1 : float) (v : R), xv2 x0 x1 = XFin v -> fin x0.
Proof.
intros x0 x1 v E. unfold xval_2 in E. destruct (is_finite prec emax x0) eqn:F; [reflexivity|].
destruct (is_nan prec emax x0); discriminate E.
Qed.

(* The comparisons of a 2-limb value with the limbs. *)
Lemma lt_2_2_xval :
  forall x0 x1 y0 y1 : float,
  lt_2_2 x0 x1 y0 y1 = orb (xlt (xv x0) (xv y0)) (andb (xeq (xv x0) (xv y0)) (xlt (xv x1) (xv y1))).
Proof. intros. unfold IeeeModel.lt_2_2. cbv zeta. now rewrite 2!lt_xval, eq_xval. Qed.

Lemma le_2_2_xval :
  forall x0 x1 y0 y1 : float,
  le_2_2 x0 x1 y0 y1 = orb (xlt (xv x0) (xv y0)) (andb (xeq (xv x0) (xv y0)) (xle (xv x1) (xv y1))).
Proof. intros. unfold IeeeModel.le_2_2. cbv zeta. now rewrite lt_xval, eq_xval, le_xval. Qed.

Lemma le_2_1_xval :
  forall x0 x1 a : float,
  le_2_1 x0 x1 a = orb (xlt (xv x0) (xv a)) (andb (xeq (xv x0) (xv a)) (xle (xv x1) (XFin 0))).
Proof. intros. unfold IeeeModel.le_2_1. cbv zeta. now rewrite lt_xval, eq_xval, le_xval. Qed.

(* An exact pair compared with any pair, and any pair compared with an exact pair. *)
Lemma pair_cmp :
  forall (v w : R) (s0 s1 d0 d1 : float),
  canonical_2 s0 s1 -> xv2 s0 s1 = XFin v -> inrange (rnd v) ->
  tso_pair w d0 d1 ->
  lt_2_2 s0 s1 d0 d1 = Rlt_bool v w /\ le_2_2 s0 s1 d0 d1 = Rle_bool v w.
Proof.
intros v w s0 s1 d0 d1 Cs Es Is [[Fd [Cd [Ed Id]]]|[sg [E0 [E1 [Nw Sw]]]]].
- rewrite (lt_2_2_ext prec emax Hp1 _ _ _ _ Cs Cd), (le_2_2_ext prec emax Hp1 _ _ _ _ Cs Cd).
  rewrite Es, Ed. split; reflexivity.
- subst d0 d1. destruct (overflow_order v w Is Nw) as [P N].
  rewrite lt_2_2_xval, le_2_2_xval, (xval_fin prec emax s0 (xval_2_lead_fin s0 s1 v Es)).
  destruct sg; cbn [xval is_finite is_nan Bsign xlt xeq andb orb negb].
  + split; symmetry; [apply Rlt_bool_false|apply Rle_bool_false]; specialize (N Sw); lra.
  + split; symmetry; [apply Rlt_bool_true|apply Rle_bool_true]; specialize (P Sw); lra.
Qed.

Lemma pair_cmp_r :
  forall (v w : R) (s0 s1 d0 d1 : float),
  canonical_2 s0 s1 -> xv2 s0 s1 = XFin v -> inrange (rnd v) ->
  tso_pair w d0 d1 ->
  lt_2_2 d0 d1 s0 s1 = Rlt_bool w v /\ le_2_2 d0 d1 s0 s1 = Rle_bool w v.
Proof.
intros v w s0 s1 d0 d1 Cs Es Is [[Fd [Cd [Ed Id]]]|[sg [E0 [E1 [Nw Sw]]]]].
- rewrite (lt_2_2_ext prec emax Hp1 _ _ _ _ Cd Cs), (le_2_2_ext prec emax Hp1 _ _ _ _ Cd Cs).
  rewrite Es, Ed. split; reflexivity.
- subst d0 d1. destruct (overflow_order v w Is Nw) as [P N].
  rewrite lt_2_2_xval, le_2_2_xval, (xval_fin prec emax s0 (xval_2_lead_fin s0 s1 v Es)).
  destruct sg; cbn [xval is_finite is_nan Bsign xlt xeq andb orb negb].
  + split; symmetry; [apply Rlt_bool_true|apply Rle_bool_true]; specialize (N Sw); lra.
  + split; symmetry; [apply Rlt_bool_false|apply Rle_bool_false]; specialize (P Sw); lra.
Qed.

(* The overflowed sum of two nonnegative numbers is below no pair. *)
Lemma pair_top :
  forall (w : R) (d0 d1 : float), tso_pair w d0 d1 ->
  lt_2_2 (B754_infinity prec emax false) (B754_infinity prec emax true) d0 d1 = false.
Proof.
intros w d0 d1 [[Fd _]|[sg [E0 [E1 _]]]].
- rewrite lt_2_2_xval, (xval_fin prec emax d0 Fd). reflexivity.
- subst d0 d1. rewrite lt_2_2_xval. destruct sg; reflexivity.
Qed.

Lemma rnd_abs : forall w : R, rnd (Rabs w) = Rabs (rnd w).
Proof.
intros w. destruct (Rcase_abs w) as [H|H].
- rewrite (Rabs_left w H). change (rnd (- w)) with (RN emin prec (- w)).
  rewrite RN_opp. unfold RN. rewrite Rabs_left1; [reflexivity|].
  apply round_le_generic; auto with typeclass_instances; [apply generic_format_0|lra].
- rewrite (Rabs_right w H). rewrite Rabs_right; [reflexivity|].
  apply Rle_ge. apply round_ge_generic; auto with typeclass_instances;
    [apply generic_format_0|lra].
Qed.

(* abs_2 of a pair is the pair of the magnitude. *)
Lemma abs_pair :
  forall (w : R) (d0 d1 : float), tso_pair w d0 d1 ->
  tso_pair (Rabs w) (fst (abs_2 d0 d1)) (snd (abs_2 d0 d1)).
Proof.
intros w d0 d1 [[Fd [Cd [Ed Id]]]|[sg [E0 [E1 [Nw Sw]]]]].
- generalize (abs_2_ext prec emax nan_opp Hp1 d0 d1 Cd).
  destruct (abs_2 d0 d1) as [a0 a1]. cbn [fst snd]. intros [Ca Ea].
  rewrite Ed in Ea. cbn [xabs] in Ea. left.
  split; [exact (xval_2_lead_fin a0 a1 _ Ea)|split; [exact Ca|split; [exact Ea|]]].
  unfold IeeeBridge.inrange in *. rewrite rnd_abs, Rabs_Rabsolu. exact Id.
- subst d0 d1. right. exists false.
  assert (A : abs_2 (B754_infinity prec emax sg) (B754_infinity prec emax (negb sg))
              = (B754_infinity prec emax false, B754_infinity prec emax true)).
  { unfold IeeeModel.abs_2. cbv zeta. rewrite lt_xval. destruct sg; reflexivity. }
  rewrite A. cbn [fst snd]. split; [reflexivity|split; [reflexivity|split]].
  + unfold IeeeBridge.inrange in *. rewrite rnd_abs, Rabs_Rabsolu. exact Nw.
  + change (0 < Rabs w). destruct sg; simpl in Sw;
      [rewrite Rabs_left by exact Sw|rewrite Rabs_right by lra]; lra.
Qed.

(* le_2_1 of a pair and a finite limb. *)
Lemma pair_le_2_1 :
  forall (w : R) (a0 a1 r : float), tso_pair w a0 a1 -> fin r ->
  le_2_1 a0 a1 r = Rle_bool w (b2r r).
Proof.
intros w a0 a1 r [[Fa [Ca [Ea Ia]]]|[sg [E0 [E1 [Nw Sw]]]]] Fr.
- rewrite (le_2_1_ext prec emax Hp1 _ _ _ Ca), Ea, (xval_fin prec emax r Fr). reflexivity.
- subst a0 a1. assert (B := overflow_big w Nw). assert (Q := b2r_Omega prec emax r).
  rewrite le_2_1_xval, (xval_fin prec emax r Fr).
  destruct sg; simpl in Sw; cbn [xval is_finite is_nan Bsign xlt xeq andb orb negb].
  + symmetry. apply Rle_bool_true. rewrite Rabs_left in B by exact Sw. lra.
  + symmetry. apply Rle_bool_false. rewrite Rabs_right in B by lra. lra.
Qed.

(** * Pairs led by a NaN or +infinity, followed by a NaN *)

Lemma xadd_nan_r : forall a : xreal, xadd a XNaN = XNaN.
Proof. intros [|[|]|x]; reflexivity. Qed.

Lemma xadd_inf_l :
  forall (s : bool) (y : xreal), xadd (XInf s) y = XNaN \/ exists s' : bool, xadd (XInf s) y = XInf s'.
Proof.
intros s [|s'|y]; cbn [xadd].
- left. reflexivity.
- destruct (Bool.eqb s s'); [right; exists s; reflexivity|left; reflexivity].
- right. exists s. reflexivity.
Qed.

Lemma xval_nonfin :
  forall a : float, xv a = XNaN \/ xv a = XInf false -> is_finite prec emax a = false.
Proof.
intros a H. unfold xval in H. destruct (is_finite prec emax a); [|reflexivity].
destruct H as [H|H]; discriminate H.
Qed.

(* abs_2 of a pair led by a NaN or an infinity and followed by a NaN. *)
Lemma abs_nonfin :
  forall d0 d1 : float, (xv d0 = XNaN \/ exists s : bool, xv d0 = XInf s) ->
  is_nan prec emax d1 = true ->
  (xv (fst (abs_2 d0 d1)) = XNaN \/ xv (fst (abs_2 d0 d1)) = XInf false) /\
  xv (snd (abs_2 d0 d1)) = XNaN.
Proof.
intros d0 d1 H N. unfold IeeeModel.abs_2. cbv zeta. rewrite lt_xval.
change (xv pzero) with (XFin 0).
assert (EN : xv d1 = XNaN) by exact (xval_nan prec emax d1 N).
destruct H as [E|[s E]]; rewrite E; cbn [xlt].
- cbn [fst snd]. split; [left; exact E|exact EN].
- destruct s; cbn [fst snd].
  + rewrite 2!(xval_neg prec emax nan_opp), E, EN. split; [right; reflexivity|reflexivity].
  + split; [right; exact E|exact EN].
Qed.

Lemma nonfin_lt_2_2 :
  forall s0 s1 d0 d1 : float, xv s0 = XNaN \/ xv s0 = XInf false -> xv s1 = XNaN ->
  lt_2_2 s0 s1 d0 d1 = false.
Proof.
intros s0 s1 d0 d1 [E|E] N; rewrite lt_2_2_xval, E, N; [reflexivity|].
destruct (xv d0) as [|[|]|x]; reflexivity.
Qed.

Lemma nonfin_le_2_2 :
  forall s0 s1 d0 d1 : float, xv s0 = XNaN \/ xv s0 = XInf false -> xv s1 = XNaN ->
  le_2_2 s0 s1 d0 d1 = false.
Proof.
intros s0 s1 d0 d1 [E|E] N; rewrite le_2_2_xval, E, N; [reflexivity|].
destruct (xv d0) as [|[|]|x]; reflexivity.
Qed.

Lemma nonfin_le_2_1 :
  forall a0 a1 r : float, xv a0 = XNaN \/ xv a0 = XInf false -> xv a1 = XNaN ->
  le_2_1 a0 a1 r = false.
Proof.
intros a0 a1 r [E|E] N; rewrite le_2_1_xval, E, N; [reflexivity|].
destruct (xv r) as [|[|]|x]; reflexivity.
Qed.

(* The exact pair of a sum with a zero operand. *)
Lemma tso_zero :
  (2 <= prec)%Z -> forall a b : float, fin a -> fin b -> (b2r a = 0 \/ b2r b = 0) ->
  fin (fst (two_sum_ord a b)) /\
  canonical_2 (fst (two_sum_ord a b)) (snd (two_sum_ord a b)) /\
  xv2 (fst (two_sum_ord a b)) (snd (two_sum_ord a b)) = XFin (b2r a + b2r b) /\
  inrange (rnd (b2r a + b2r b)).
Proof.
intros Hp a b Fa Fb Z. apply tso_pair_small; [exact (tso_pair_of Hp a b Fa Fb)|].
generalize (b2r_Omega prec emax a) (b2r_Omega prec emax b). intros A B.
destruct Z as [Z|Z]; rewrite Z; [rewrite Rplus_0_l|rewrite Rplus_0_r]; apply Rabs_le; lra.
Qed.

(** * The states of a ball by its radius *)

Lemma ball_1_fin_r : forall c r : float, ball_1 c r -> fin r -> ball_finite_1 c r.
Proof.
intros c r [F|[[_ E]|[_ N]]] Fr; [exact F| |]; exfalso.
- rewrite E in Fr. discriminate Fr.
- unfold nan in N. rewrite (finite_not_nan prec emax r Fr) in N. discriminate N.
Qed.

Lemma xlohi_cases :
  forall c r : float, ball_1 c r ->
  (fin r /\ xlo_1 c r = XFin (b2r c - b2r r) /\ xhi_1 c r = XFin (b2r c + b2r r)) \/
  (xlo_1 c r = XInf true /\ xhi_1 c r = XInf false) \/
  (xlo_1 c r = XInf false /\ xhi_1 c r = XInf true).
Proof.
intros c r [[_ [Fr _]]|[[_ Er]|[_ Nr]]].
- left. split; [exact Fr|exact (xlohi_fin c r Fr)].
- right; left. subst r. exact (xlohi_whole c).
- right; right. exact (xlohi_nan c r Nr).
Qed.

(* The radius of a canonical ball as an extended real number: nonnegative, +infinity or NaN. *)
Lemma radius_cases :
  forall c r : float, ball_1 c r ->
  (fin r /\ xv r = XFin (b2r r) /\ 0 <= b2r r) \/ xv r = XInf false \/ xv r = XNaN.
Proof.
intros c r [[_ [Fr Pr]]|[[_ Er]|[_ Nr]]].
- left. split; [exact Fr|split; [exact (xval_fin prec emax r Fr)|exact Pr]].
- right; left. subst r. reflexivity.
- right; right. exact (xval_nan prec emax r Nr).
Qed.

(* The sum of the radii, when one is not finite, is a NaN or +infinity followed by a NaN. *)
Lemma radii_special :
  forall cx rx cy ry : float, ball_1 cx rx -> ball_1 cy ry ->
  is_finite prec emax rx = false \/ is_finite prec emax ry = false ->
  (xv (fst (two_sum_ord rx ry)) = XNaN \/ xv (fst (two_sum_ord rx ry)) = XInf false) /\
  xv (snd (two_sum_ord rx ry)) = XNaN.
Proof.
intros cx rx cy ry BX BY H.
generalize (two_sum_ord_ieee_nonfinite prec emax nan_plus nan_minus nan_abs rx ry H).
destruct (two_sum_ord rx ry) as [s0 s1]. cbn [fst snd]. intros [Es Ns].
split; [|exact (xval_nan prec emax s1 Ns)]. rewrite Es.
destruct (radius_cases cx rx BX) as [[Fx [Ex _]]|[Ex|Ex]];
destruct (radius_cases cy ry BY) as [[Fy [Ey _]]|[Ey|Ey]]; rewrite Ex, Ey;
  try (left; reflexivity); try (right; reflexivity).
exfalso. destruct H as [K|K]; rewrite K in *; discriminate.
Qed.

(* The relations on the bounds of the balls are all false when a ball is not finite: the
   comparisons with the whole line or the empty set are unknown. *)
Lemma special_rels :
  forall cx rx cy ry : float, ball_1 cx rx -> ball_1 cy ry ->
  is_finite prec emax rx = false \/ is_finite prec emax ry = false ->
  let a := xlo_1 cx rx in let b := xhi_1 cx rx in let c := xlo_1 cy ry in let d := xhi_1 cy ry in
  let ne := andb (xlt a (XInf false)) (xlt c (XInf false)) in
  andb (xlt b c) ne = false /\ andb (xle d a) ne = false /\
  andb (xle b c) ne = false /\ andb (xlt d a) ne = false /\
  andb (andb (xeq a b) (xeq b c)) (xeq c d) = false /\ andb (orb (xlt b c) (xlt d a)) ne = false.
Proof.
intros cx rx cy ry BX BY H. cbv zeta.
destruct (xlohi_cases cx rx BX) as [[Fx [Ea Eb]]|[[Ea Eb]|[Ea Eb]]];
destruct (xlohi_cases cy ry BY) as [[Fy [Ec Ed]]|[[Ec Ed]|[Ec Ed]]]; rewrite Ea, Eb, Ec, Ed;
  try (exfalso; destruct H as [K|K]; rewrite K in *; discriminate);
  cbn [xlt xle xeq andb orb negb Bool.eqb]; rewrite ?andb_false_r; repeat split.
Qed.

(** * The kernels, as booleans of the bounds *)

Lemma ball_positive_1_bool :
  forall c r : float, ball_1 c r ->
  IeeeModel.ball_positive_1 prec emax c r
  = andb (xlt (XFin 0) (xlo_1 c r)) (xlt (xlo_1 c r) (XInf false)).
Proof.
intros c r B. unfold IeeeModel.ball_positive_1. cbv zeta. rewrite lt_xval.
destruct (ball_1_states c r B) as [[[Fc [Fr _]] _]|[[[[s Ec] Er] _]|[[Nc Nr] _]]].
- destruct (xlohi_fin c r Fr) as [El _].
  rewrite El, (xval_fin prec emax c Fc), (xval_fin prec emax r Fr). cbn [xlt]. bools.
- subst c r. reflexivity.
- rewrite (xval_nan prec emax r Nr). destruct (xlohi_nan c r Nr) as [El _]. rewrite El. reflexivity.
Qed.

Lemma ball_negative_1_bool :
  forall c r : float, ball_1 c r ->
  IeeeModel.ball_negative_1 prec emax nan_opp c r
  = andb (xlt (xhi_1 c r) (XFin 0)) (xlt (XInf true) (xhi_1 c r)).
Proof.
intros c r B. unfold IeeeModel.ball_negative_1. cbv zeta.
rewrite lt_xval, (xval_neg prec emax nan_opp).
destruct (ball_1_states c r B) as [[[Fc [Fr _]] _]|[[[[s Ec] Er] _]|[[Nc Nr] _]]].
- destruct (xlohi_fin c r Fr) as [_ Eh].
  rewrite Eh, (xval_fin prec emax c Fc), (xval_fin prec emax r Fr). cbn [xlt xopp]. bools.
- subst c r. reflexivity.
- rewrite (xval_nan prec emax c Nc). destruct (xlohi_nan c r Nr) as [_ Eh]. rewrite Eh.
  reflexivity.
Qed.

Lemma ball_zero_1_bool :
  forall c r : float, ball_1 c r ->
  IeeeModel.ball_zero_1 prec emax c r
  = andb (xeq (xlo_1 c r) (XFin 0)) (xeq (xhi_1 c r) (XFin 0)).
Proof.
intros c r B. unfold IeeeModel.ball_zero_1. cbv zeta. rewrite 2!eq_xval.
change (xv pzero) with (XFin 0).
destruct (ball_1_states c r B) as [[[Fc [Fr _]] _]|[[[[s Ec] Er] _]|[[Nc Nr] _]]].
- destruct (xlohi_fin c r Fr) as [El Eh].
  rewrite El, Eh, (xval_fin prec emax c Fc), (xval_fin prec emax r Fr). cbn [xeq]. bools.
- subst c r. rewrite andb_false_r. reflexivity.
- rewrite (xval_nan prec emax c Nc). destruct (xlohi_nan c r Nr) as [El Eh]. rewrite El, Eh.
  reflexivity.
Qed.

Lemma ball_contains_point_1_bool :
  (2 <= prec)%Z ->
  forall c r t : float, ball_1 c r ->
  IeeeModel.ball_contains_point_1 prec emax nan_plus nan_minus nan_opp nan_abs c r t
  = andb (andb (xle (xlo_1 c r) (xv t)) (xle (xv t) (xhi_1 c r))) (is_finite prec emax t).
Proof.
intros Hp c r t B. unfold IeeeModel.ball_contains_point_1. cbv zeta.
destruct (finite_dec prec emax t) as [Ft|Ft].
- assert (Fg : fin (IeeeOperations.guard prec emax nan_plus t))
    by (rewrite (guard_finite prec emax nan_plus); exact Ft).
  assert (Eg : b2r (IeeeOperations.guard prec emax nan_plus t) = b2r t)
    by apply (guard_val prec emax nan_plus).
  rewrite Ft, andb_true_r, (xval_fin prec emax t Ft).
  destruct (ball_1_states c r B) as [[[Fc [Fr Pr]] _]|[[[[s Ec] Er] _]|[[Nc Nr] _]]].
  + assert (Fnc : fin (neg c)) by (rewrite (IeeeExt.neg_finite prec emax nan_opp); exact Fc).
    generalize (tso_pair_of Hp _ (neg c) Fg Fnc).
    destruct (two_sum_ord (IeeeOperations.guard prec emax nan_plus t) (neg c)) as [d0 d1].
    cbn [fst snd]. rewrite Eg, (IeeeExt.neg_value prec emax nan_opp). intros PD.
    generalize (abs_pair _ _ _ PD). destruct (abs_2 d0 d1) as [a0 a1]. cbn [fst snd].
    intros PA. rewrite (pair_le_2_1 _ _ _ _ PA Fr).
    destruct (xlohi_fin c r Fr) as [El Eh]. rewrite El, Eh. cbn [xle]. bools.
  + subst c r.
    generalize (tso_zero Hp _ (neg (B754_zero prec emax s)) Fg eq_refl (or_intror eq_refl)).
    destruct (two_sum_ord (IeeeOperations.guard prec emax nan_plus t) (neg (B754_zero prec emax s)))
      as [d0 d1].
    cbn [fst snd]. intros [Fd [Cd [Ed _]]].
    generalize (abs_2_ext prec emax nan_opp Hp1 d0 d1 Cd). destruct (abs_2 d0 d1) as [a0 a1].
    intros [Ca Ea]. rewrite (le_2_1_ext prec emax Hp1 _ _ _ Ca), Ea, Ed.
    destruct (xlohi_whole (B754_zero prec emax s)) as [El Eh]. rewrite El, Eh. reflexivity.
  + assert (Fnc : is_finite prec emax (neg c) = false).
    { rewrite (IeeeExt.neg_finite prec emax nan_opp). exact (nan_not_finite prec emax c Nc). }
    generalize (two_sum_ord_ieee_nonfinite prec emax nan_plus nan_minus nan_abs
                  (IeeeOperations.guard prec emax nan_plus t) (neg c) (or_intror Fnc)).
    destruct (two_sum_ord (IeeeOperations.guard prec emax nan_plus t) (neg c)) as [d0 d1].
    intros [Ed Nd].
    rewrite (xval_neg prec emax nan_opp), (xval_nan prec emax c Nc) in Ed.
    cbn [xopp] in Ed. rewrite xadd_nan_r in Ed.
    generalize (abs_nonfin d0 d1 (or_introl Ed) Nd). destruct (abs_2 d0 d1) as [a0 a1].
    cbn [fst snd]. intros [E0 E1]. rewrite (nonfin_le_2_1 _ _ _ E0 E1).
    destruct (xlohi_nan c r Nr) as [El Eh]. rewrite El, Eh. reflexivity.
- rewrite Ft, andb_false_r.
  assert (Fg : is_finite prec emax (IeeeOperations.guard prec emax nan_plus t) = false)
    by (rewrite (guard_finite prec emax nan_plus); exact Ft).
  generalize (two_sum_ord_ieee_nonfinite prec emax nan_plus nan_minus nan_abs _ (neg c)
                (or_introl Fg)).
  destruct (two_sum_ord (IeeeOperations.guard prec emax nan_plus t) (neg c)) as [d0 d1].
  intros [Ed Nd].
  assert (H : xv d0 = XNaN \/ exists s : bool, xv d0 = XInf s).
  { rewrite Ed.
    destruct (xval_cases prec emax (IeeeOperations.guard prec emax nan_plus t))
      as [[K _]|[[s Es]|Es]]; [rewrite K in Fg; discriminate Fg| |]; rewrite Es.
    - apply xadd_inf_l.
    - left. reflexivity. }
  generalize (abs_nonfin d0 d1 H Nd). destruct (abs_2 d0 d1) as [a0 a1].
  cbn [fst snd]. intros [E0 E1]. exact (nonfin_le_2_1 _ _ _ E0 E1).
Qed.

Lemma ball_contains_ball_1_bool :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, ball_1 cx rx -> ball_1 cy ry ->
  IeeeModel.ball_contains_ball_1 prec emax nan_plus nan_minus nan_opp nan_abs cx rx cy ry
  = andb (xle (xlo_1 cx rx) (xlo_1 cy ry)) (xle (xhi_1 cy ry) (xhi_1 cx rx)).
Proof.
intros Hp cx rx cy ry BX BY. unfold IeeeModel.ball_contains_ball_1. cbv zeta.
destruct (ball_1_states cx rx BX) as [[FX [NWX NEX]]|[[WX [NFX NEX]]|[EX [NFX NWX]]]].
2: { (* X is the whole line *)
  destruct WX as [[sx Ecx] Erx]. subst cx rx.
  destruct (two_sum_ord cy (neg (B754_zero prec emax sx))) as [d0 d1].
  destruct (abs_2 d0 d1) as [a0 a1].
  destruct (two_sum_ord (infinity prec emax false) (neg ry)) as [g0 g1].
  rewrite eq_xval. change (xv (infinity prec emax false)) with (XInf false).
  change (xv pinf) with (XInf false). cbn [xeq Bool.eqb orb].
  destruct (xlohi_whole (B754_zero prec emax sx)) as [Ea Eb]. rewrite Ea, Eb.
  destruct (xlohi_cases cy ry BY) as [[_ [Ec Ed]]|[[Ec Ed]|[Ec Ed]]]; rewrite Ec, Ed;
    reflexivity. }
destruct (ball_1_states cy ry BY) as [[FY [NWY NEY]]|[[WY [NFY NEY]]|[EY [NFY NWY]]]].
3: { (* Y is the empty set *)
  destruct EY as [Ncy Nry].
  destruct (two_sum_ord cy (neg cx)) as [d0 d1]. destruct (abs_2 d0 d1) as [a0 a1].
  destruct (two_sum_ord rx (neg ry)) as [g0 g1].
  rewrite (eq_self prec emax ry), Nry. cbn [negb]. rewrite orb_true_r. cbn [orb].
  destruct (xlohi_nan cy ry Nry) as [Ec Ed]. rewrite Ec, Ed.
  destruct (xlohi_cases cx rx BX) as [[_ [Ea Eb]]|[[Ea Eb]|[Ea Eb]]]; rewrite Ea, Eb;
    reflexivity. }
3: { (* X is empty, Y is not *)
  destruct EX as [Ncx Nrx].
  assert (Fncx : is_finite prec emax (neg cx) = false).
  { rewrite (IeeeExt.neg_finite prec emax nan_opp). exact (nan_not_finite prec emax cx Ncx). }
  generalize (two_sum_ord_ieee_nonfinite prec emax nan_plus nan_minus nan_abs cy (neg cx)
                (or_intror Fncx)).
  destruct (two_sum_ord cy (neg cx)) as [d0 d1]. intros [Ed Nd].
  rewrite (xval_neg prec emax nan_opp), (xval_nan prec emax cx Ncx) in Ed.
  cbn [xopp] in Ed. rewrite xadd_nan_r in Ed.
  generalize (abs_nonfin d0 d1 (or_introl Ed) Nd). destruct (abs_2 d0 d1) as [a0 a1].
  cbn [fst snd]. intros [E0 E1].
  destruct (two_sum_ord rx (neg ry)) as [g0 g1].
  rewrite (nonfin_le_2_2 _ _ _ _ E0 E1), eq_xval, (eq_self prec emax ry), (xval_nan prec emax rx Nrx).
  destruct (xlohi_nan cx rx Nrx) as [Ea Eb]. rewrite Ea, Eb.
  destruct (ball_1_states cy ry BY) as [[[_ [Fry _]] _]|[[[_ Ery] _]|[[_ Nry] _]]].
  - rewrite (finite_not_nan prec emax ry Fry).
    destruct (xlohi_fin cy ry Fry) as [Ec Ed']. rewrite Ec, Ed'. reflexivity.
  - subst ry. destruct (xlohi_whole cy) as [Ec Ed']. rewrite Ec, Ed'. reflexivity.
  - rewrite Nry. destruct (xlohi_nan cy ry Nry) as [Ec Ed']. rewrite Ec, Ed'. reflexivity. }
2: { (* X finite, Y the whole line *)
  destruct FX as [Fcx [Frx Prx]]. destruct WY as [[sy Ecy] Ery]. subst cy ry.
  assert (Fncx : fin (neg cx)) by (rewrite (IeeeExt.neg_finite prec emax nan_opp); exact Fcx).
  generalize (tso_zero Hp (B754_zero prec emax sy) (neg cx) eq_refl Fncx (or_introl eq_refl)).
  destruct (two_sum_ord (B754_zero prec emax sy) (neg cx)) as [d0 d1]. cbn [fst snd].
  intros [Fd [Cd [Ed _]]].
  generalize (abs_2_ext prec emax nan_opp Hp1 d0 d1 Cd). destruct (abs_2 d0 d1) as [a0 a1].
  intros [Ca Ea]. rewrite Ed in Ea. cbn [xabs] in Ea.
  assert (Fa := xval_2_lead_fin a0 a1 _ Ea).
  generalize (two_sum_ord_ieee_nonfinite prec emax nan_plus nan_minus nan_abs rx
                (neg (infinity prec emax false)) (or_intror eq_refl)).
  destruct (two_sum_ord rx (neg (infinity prec emax false))) as [g0 g1]. intros [Eg Ng].
  rewrite (xval_fin prec emax rx Frx) in Eg. cbn in Eg.
  rewrite le_2_2_xval, Eg, (xval_fin prec emax a0 Fa), eq_xval, (xval_fin prec emax rx Frx).
  change (xv (infinity prec emax false)) with (XInf false). change (xv pinf) with (XInf false).
  cbn [xlt xeq andb orb negb].
  destruct (xlohi_fin cx rx Frx) as [Ea' Eb']. destruct (xlohi_whole (B754_zero prec emax sy)) as [Ec Ed'].
  rewrite Ea', Eb', Ec, Ed'. reflexivity. }
(* both finite *)
destruct FX as [Fcx [Frx Prx]]. destruct FY as [Fcy [Fry Pry]]. unfold val in Prx, Pry.
assert (Fncx : fin (neg cx)) by (rewrite (IeeeExt.neg_finite prec emax nan_opp); exact Fcx).
assert (Fnry : fin (neg ry)) by (rewrite (IeeeExt.neg_finite prec emax nan_opp); exact Fry).
generalize (tso_pair_of Hp cy (neg cx) Fcy Fncx).
destruct (two_sum_ord cy (neg cx)) as [d0 d1]. cbn [fst snd].
rewrite (IeeeExt.neg_value prec emax nan_opp). intros PD.
generalize (abs_pair _ _ _ PD). destruct (abs_2 d0 d1) as [a0 a1]. cbn [fst snd]. intros PA.
assert (Small : Rabs (b2r rx + b2r (neg ry)) <= Om).
{ rewrite (IeeeExt.neg_value prec emax nan_opp).
  generalize (b2r_Omega prec emax rx) (b2r_Omega prec emax ry). intros A B. apply Rabs_le. lra. }
generalize (tso_pair_small _ _ _ (tso_pair_of Hp rx (neg ry) Frx Fnry) Small).
destruct (two_sum_ord rx (neg ry)) as [g0 g1]. cbn [fst snd].
rewrite (IeeeExt.neg_value prec emax nan_opp). intros [Fg [Cg [Eg Ig]]].
rewrite (proj2 (pair_cmp_r _ _ _ _ _ _ Cg Eg Ig PA)).
rewrite eq_xval, (eq_self prec emax ry), (finite_not_nan prec emax ry Fry), (xval_fin prec emax rx Frx).
change (xv pinf) with (XInf false). cbn [xeq negb orb].
destruct (xlohi_fin cx rx Frx) as [Ea Eb]. destruct (xlohi_fin cy ry Fry) as [Ec Ed].
rewrite Ea, Eb, Ec, Ed. cbn [xle]. bools.
Qed.

(* A ball that is the empty set or the whole line has a radius that is not finite. *)
Lemma special_nonfin :
  forall cx rx cy ry : float,
  ball_empty_1 cx rx \/ ball_whole_1 cx rx \/ ball_empty_1 cy ry \/ ball_whole_1 cy ry ->
  is_finite prec emax rx = false \/ is_finite prec emax ry = false.
Proof.
intros cx rx cy ry [[_ N]|[[_ E]|[[_ N]|[_ E]]]].
- left. exact (nan_not_finite prec emax rx N).
- left. rewrite E. reflexivity.
- right. exact (nan_not_finite prec emax ry N).
- right. rewrite E. reflexivity.
Qed.

Lemma radii_cases :
  forall rx ry : float,
  (fin rx /\ fin ry) \/ (is_finite prec emax rx = false \/ is_finite prec emax ry = false).
Proof.
intros rx ry. destruct (finite_dec prec emax rx) as [A|A]; [destruct (finite_dec prec emax ry) as [B|B]|];
  [left; split|right; right|right; left]; assumption.
Qed.

Ltac finish_exact :=
  match goal with |- (_ -> ?A /\ ?B) /\ _ =>
    let Q := fresh "Q" in
    assert (Q : A /\ B) by (split; bools); split; [intros _; exact Q|left; exact Q] end.

(* The three comparisons: exact when a radius is not finite (the special states) and when the
   rounded sum of the radii is in range; otherwise both answers are false. *)
Lemma ball_less_1_bools :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, ball_1 cx rx -> ball_1 cy ry ->
  let a := xlo_1 cx rx in let b := xhi_1 cx rx in let c := xlo_1 cy ry in let d := xhi_1 cy ry in
  let ne := andb (xlt a (XInf false)) (xlt c (XInf false)) in
  let '(yes, no) := IeeeModel.ball_less_1 prec emax nan_plus nan_minus nan_opp nan_abs cx rx cy ry in
  ((is_finite prec emax rx = false \/ is_finite prec emax ry = false) \/
   inrange (rnd (b2r rx + b2r ry)) ->
   yes = andb (xlt b c) ne /\ no = andb (xle d a) ne) /\
  ((yes = andb (xlt b c) ne /\ no = andb (xle d a) ne) \/ (yes = false /\ no = false)).
Proof.
intros Hp cx rx cy ry BX BY. cbv zeta. unfold IeeeModel.ball_less_1. cbv zeta.
destruct (radii_cases rx ry) as [[Frx Fry]|H].
- destruct (ball_1_fin_r cx rx BX Frx) as [Fcx [_ Prx]].
  destruct (ball_1_fin_r cy ry BY Fry) as [Fcy [_ Pry]]. unfold val in Prx, Pry.
  assert (Fncx : fin (neg cx)) by (rewrite (IeeeExt.neg_finite prec emax nan_opp); exact Fcx).
  assert (Fncy : fin (neg cy)) by (rewrite (IeeeExt.neg_finite prec emax nan_opp); exact Fcy).
  generalize (tso_pair_of Hp rx ry Frx Fry).
  destruct (two_sum_ord rx ry) as [s0 s1]. cbn [fst snd]. intros PS.
  generalize (tso_pair_of Hp cy (neg cx) Fcy Fncx).
  destruct (two_sum_ord cy (neg cx)) as [d0 d1]. cbn [fst snd]. intros PD.
  generalize (tso_pair_of Hp cx (neg cy) Fcx Fncy).
  destruct (two_sum_ord cx (neg cy)) as [g0 g1]. cbn [fst snd]. intros PG.
  rewrite (IeeeExt.neg_value prec emax nan_opp) in PD, PG.
  destruct (xlohi_fin cx rx Frx) as [Ea Eb]. destruct (xlohi_fin cy ry Fry) as [Ec Ed].
  rewrite Ea, Eb, Ec, Ed, (lt_abs_pinf prec emax nan_abs). cbn [xlt xle].
  destruct PS as [[Fs [Cs [Es Is]]]|[sg [E0 [E1 [Ns Ss]]]]].
  + rewrite (proj1 (pair_cmp _ _ _ _ _ _ Cs Es Is PD)), (proj2 (pair_cmp _ _ _ _ _ _ Cs Es Is PG)), Fs.
    finish_exact.
  + destruct sg; simpl in Ss; [lra|]. subst s0 s1. cbn [negb is_finite].
    rewrite (pair_top _ _ _ PD), andb_false_r. split.
    * intros [[K|K]|K]; [rewrite K in Frx; discriminate Frx|rewrite K in Fry; discriminate Fry|].
      elim (Ns K).
    * right. split; reflexivity.
- generalize (radii_special cx rx cy ry BX BY H).
  destruct (two_sum_ord rx ry) as [s0 s1]. cbn [fst snd]. intros [Es Ns].
  destruct (two_sum_ord cy (neg cx)) as [d0 d1]. destruct (two_sum_ord cx (neg cy)) as [g0 g1].
  destruct (special_rels cx rx cy ry BX BY H) as [R1 [R2 _]]. cbv zeta in R1, R2.
  rewrite (nonfin_lt_2_2 _ _ _ _ Es Ns), (lt_abs_pinf prec emax nan_abs), (xval_nonfin s0 Es),
    andb_false_r, R1, R2.
  split; [intros _; split; reflexivity|left; split; reflexivity].
Qed.

Lemma ball_less_equal_1_bools :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, ball_1 cx rx -> ball_1 cy ry ->
  let a := xlo_1 cx rx in let b := xhi_1 cx rx in let c := xlo_1 cy ry in let d := xhi_1 cy ry in
  let ne := andb (xlt a (XInf false)) (xlt c (XInf false)) in
  let '(yes, no) :=
    IeeeModel.ball_less_equal_1 prec emax nan_plus nan_minus nan_opp nan_abs cx rx cy ry in
  ((is_finite prec emax rx = false \/ is_finite prec emax ry = false) \/
   inrange (rnd (b2r rx + b2r ry)) ->
   yes = andb (xle b c) ne /\ no = andb (xlt d a) ne) /\
  ((yes = andb (xle b c) ne /\ no = andb (xlt d a) ne) \/ (yes = false /\ no = false)).
Proof.
intros Hp cx rx cy ry BX BY. cbv zeta. unfold IeeeModel.ball_less_equal_1. cbv zeta.
destruct (radii_cases rx ry) as [[Frx Fry]|H].
- destruct (ball_1_fin_r cx rx BX Frx) as [Fcx [_ Prx]].
  destruct (ball_1_fin_r cy ry BY Fry) as [Fcy [_ Pry]]. unfold val in Prx, Pry.
  assert (Fncx : fin (neg cx)) by (rewrite (IeeeExt.neg_finite prec emax nan_opp); exact Fcx).
  assert (Fncy : fin (neg cy)) by (rewrite (IeeeExt.neg_finite prec emax nan_opp); exact Fcy).
  generalize (tso_pair_of Hp rx ry Frx Fry).
  destruct (two_sum_ord rx ry) as [s0 s1]. cbn [fst snd]. intros PS.
  generalize (tso_pair_of Hp cy (neg cx) Fcy Fncx).
  destruct (two_sum_ord cy (neg cx)) as [d0 d1]. cbn [fst snd]. intros PD.
  generalize (tso_pair_of Hp cx (neg cy) Fcx Fncy).
  destruct (two_sum_ord cx (neg cy)) as [g0 g1]. cbn [fst snd]. intros PG.
  rewrite (IeeeExt.neg_value prec emax nan_opp) in PD, PG.
  destruct (xlohi_fin cx rx Frx) as [Ea Eb]. destruct (xlohi_fin cy ry Fry) as [Ec Ed].
  rewrite Ea, Eb, Ec, Ed, (lt_abs_pinf prec emax nan_abs). cbn [xlt xle].
  destruct PS as [[Fs [Cs [Es Is]]]|[sg [E0 [E1 [Ns Ss]]]]].
  + rewrite (proj2 (pair_cmp _ _ _ _ _ _ Cs Es Is PD)), (proj1 (pair_cmp _ _ _ _ _ _ Cs Es Is PG)), Fs.
    finish_exact.
  + destruct sg; simpl in Ss; [lra|]. subst s0 s1. cbn [negb is_finite].
    rewrite (pair_top _ _ _ PG), andb_false_r. split.
    * intros [[K|K]|K]; [rewrite K in Frx; discriminate Frx|rewrite K in Fry; discriminate Fry|].
      elim (Ns K).
    * right. split; reflexivity.
- generalize (radii_special cx rx cy ry BX BY H).
  destruct (two_sum_ord rx ry) as [s0 s1]. cbn [fst snd]. intros [Es Ns].
  destruct (two_sum_ord cy (neg cx)) as [d0 d1]. destruct (two_sum_ord cx (neg cy)) as [g0 g1].
  destruct (special_rels cx rx cy ry BX BY H) as [_ [_ [R3 [R4 _]]]]. cbv zeta in R3, R4.
  rewrite (nonfin_lt_2_2 _ _ _ _ Es Ns), (lt_abs_pinf prec emax nan_abs), (xval_nonfin s0 Es),
    andb_false_r, R3, R4.
  split; [intros _; split; reflexivity|left; split; reflexivity].
Qed.

Lemma ball_equal_1_bools :
  (2 <= prec)%Z ->
  forall cx rx cy ry : float, ball_1 cx rx -> ball_1 cy ry ->
  let a := xlo_1 cx rx in let b := xhi_1 cx rx in let c := xlo_1 cy ry in let d := xhi_1 cy ry in
  let ne := andb (xlt a (XInf false)) (xlt c (XInf false)) in
  let '(yes, no) := IeeeModel.ball_equal_1 prec emax nan_plus nan_minus nan_opp nan_abs cx rx cy ry in
  ((is_finite prec emax rx = false \/ is_finite prec emax ry = false) \/
   inrange (rnd (b2r rx + b2r ry)) ->
   yes = andb (andb (xeq a b) (xeq b c)) (xeq c d) /\ no = andb (orb (xlt b c) (xlt d a)) ne) /\
  ((yes = andb (andb (xeq a b) (xeq b c)) (xeq c d) /\ no = andb (orb (xlt b c) (xlt d a)) ne) \/
   (yes = false /\ no = false)).
Proof.
intros Hp cx rx cy ry BX BY. cbv zeta. unfold IeeeModel.ball_equal_1. cbv zeta.
rewrite 3!eq_xval. change (xv pzero) with (XFin 0).
destruct (radii_cases rx ry) as [[Frx Fry]|H].
- destruct (ball_1_fin_r cx rx BX Frx) as [Fcx [_ Prx]].
  destruct (ball_1_fin_r cy ry BY Fry) as [Fcy [_ Pry]]. unfold val in Prx, Pry.
  assert (Fncx : fin (neg cx)) by (rewrite (IeeeExt.neg_finite prec emax nan_opp); exact Fcx).
  generalize (tso_pair_of Hp rx ry Frx Fry).
  destruct (two_sum_ord rx ry) as [s0 s1]. cbn [fst snd]. intros PS.
  generalize (tso_pair_of Hp cy (neg cx) Fcy Fncx).
  destruct (two_sum_ord cy (neg cx)) as [d0 d1]. cbn [fst snd].
  rewrite (IeeeExt.neg_value prec emax nan_opp). intros PD.
  generalize (abs_pair _ _ _ PD). destruct (abs_2 d0 d1) as [a0 a1]. cbn [fst snd]. intros PA.
  destruct (xlohi_fin cx rx Frx) as [Ea Eb]. destruct (xlohi_fin cy ry Fry) as [Ec Ed].
  rewrite Ea, Eb, Ec, Ed, (xval_fin prec emax rx Frx), (xval_fin prec emax ry Fry),
    (xval_fin prec emax cx Fcx), (xval_fin prec emax cy Fcy).
  cbn [xlt xle xeq].
  destruct PS as [[Fs [Cs [Es Is]]]|[sg [E0 [E1 [Ns Ss]]]]].
  + rewrite (proj1 (pair_cmp _ _ _ _ _ _ Cs Es Is PA)). finish_exact.
  + destruct sg; simpl in Ss; [lra|]. subst s0 s1. cbn [negb].
    rewrite (pair_top _ _ _ PA). split.
    * intros [[K|K]|K]; [rewrite K in Frx; discriminate Frx|rewrite K in Fry; discriminate Fry|].
      elim (Ns K).
    * right. split; [bools|reflexivity].
- generalize (radii_special cx rx cy ry BX BY H).
  destruct (two_sum_ord rx ry) as [s0 s1]. cbn [fst snd]. intros [Es Ns].
  destruct (two_sum_ord cy (neg cx)) as [d0 d1]. destruct (abs_2 d0 d1) as [a0 a1].
  destruct (special_rels cx rx cy ry BX BY H) as [_ [_ [_ [_ [R5 R6]]]]]. cbv zeta in R5, R6.
  rewrite (nonfin_lt_2_2 _ _ _ _ Es Ns), R5, R6.
  assert (Y : andb (andb (xeq (xv rx) (XFin 0)) (xeq (xv ry) (XFin 0))) (xeq (xv cx) (xv cy)) = false).
  { destruct (radius_cases cx rx BX) as [[Fx [Ex _]]|[Ex|Ex]];
    destruct (radius_cases cy ry BY) as [[Fy [Ey _]]|[Ey|Ey]]; rewrite Ex, Ey;
      try (exfalso; destruct H as [K|K]; rewrite K in *; discriminate);
      cbn [xeq andb]; rewrite ?andb_false_r; reflexivity. }
  rewrite Y. split; [intros _; split; reflexivity|left; split; reflexivity].
Qed.

End BallPredicates1.

(** * The generated statements *)

Theorem ball_positive_1_correct : ball_positive_1_spec.
Proof.
intros prec emax Hp0 He c r B. cbv zeta.
destruct (xball_1 prec emax c r B) as [I [NE M]].
rewrite (ball_positive_1_bool prec emax c r B), NE. setoid_rewrite M. exact (xpositive _ _ I).
Qed.

Theorem ball_negative_1_correct : ball_negative_1_spec.
Proof.
intros prec emax Hp0 He nan_opp c r B. cbv zeta.
destruct (xball_1 prec emax c r B) as [I [NE M]].
rewrite (ball_negative_1_bool prec emax nan_opp c r B), NE. setoid_rewrite M.
exact (xnegative _ _ I).
Qed.

Theorem ball_zero_1_correct : ball_zero_1_spec.
Proof.
intros prec emax Hp0 He c r B. cbv zeta.
destruct (xball_1 prec emax c r B) as [I [NE M]].
rewrite (ball_zero_1_bool prec emax c r B), NE. setoid_rewrite M. exact (xzero _ _).
Qed.

Theorem ball_contains_point_1_correct : ball_contains_point_1_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs Hp c r t B. cbv zeta.
destruct (xball_1 prec emax c r B) as [_ [_ M]].
rewrite (ball_contains_point_1_bool prec emax nan_plus nan_minus nan_opp nan_abs Hp c r t B), M.
exact (xcontains _ _ _ _ _ (xval_fin prec emax t)).
Qed.

Theorem ball_contains_ball_1_correct : ball_contains_ball_1_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs Hp cx rx cy ry BX BY. cbv zeta.
destruct (xball_1 prec emax cx rx BX) as [IX [_ MX]].
destruct (xball_1 prec emax cy ry BY) as [IY [_ MY]].
rewrite (ball_contains_ball_1_bool prec emax nan_plus nan_minus nan_opp nan_abs Hp cx rx cy ry BX BY).
setoid_rewrite MX. setoid_rewrite MY. exact (xsubset _ _ _ _ IY IX).
Qed.

(* The three comparisons: the relation and its failure, read on the bounds of the balls,
   exclude each other, since nonempty balls have members. *)
Ltac trit_tail HS HA LY LN :=
  apply trit_from;
  [ let A := fresh in let B := fresh in let NX := fresh in let NY := fresh in
    let x := fresh in let y := fresh in let Hx := fresh in let Hy := fresh in
    intros [A B]; apply LY in A; apply LN in B; destruct A as [NX [NY A]];
    destruct B as [_ [_ B]];
    destruct (xnonempty_member _ _ NX) as [x Hx]; destruct (xnonempty_member _ _ NY) as [y Hy];
    exact (B x y Hx Hy (A x y Hx Hy))
  | let S := fresh in let Y := fresh in let N := fresh in
    intros S; destruct (HS (or_introl (special_nonfin _ _ _ _ _ _ S))) as [Y N];
    rewrite Y, N; split; reflexivity
  | let FX := fresh in let C := fresh in let Y := fresh in let N := fresh in
    intros FX C; destruct (HS (or_intror (rnd_le_Omega _ _ _ C))) as [Y N];
    rewrite Y, N; split; reflexivity
  | let Y := fresh in let N := fresh in
    destruct HA as [[Y N]|[Y N]]; [left; rewrite Y, N; split; reflexivity|right; split; assumption] ].

Theorem ball_less_1_correct : ball_less_1_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs Hp cx rx cy ry BX BY.
destruct (xball_1 prec emax cx rx BX) as [IX _]. destruct (xball_1 prec emax cy ry BY) as [IY _].
assert (EY := ball_pair_1 prec emax cx rx cy ry BX BY (fun x y => x < y)).
assert (EN := ball_pair_1 prec emax cx rx cy ry BX BY (fun x y => ~ (x < y))).
cbv beta in EY, EN.
destruct (xless _ _ _ _ IX IY) as [LY LN].
generalize (ball_less_1_bools prec emax nan_plus nan_minus nan_opp nan_abs Hp cx rx cy ry BX BY).
cbv zeta.
destruct (IeeeModel.ball_less_1 prec emax nan_plus nan_minus nan_opp nan_abs cx rx cy ry)
  as [yes no].
intros [HS HA]. rewrite EY, EN, <- LY, <- LN.
trit_tail HS HA LY LN.
Qed.

Theorem ball_less_equal_1_correct : ball_less_equal_1_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs Hp cx rx cy ry BX BY.
destruct (xball_1 prec emax cx rx BX) as [IX _]. destruct (xball_1 prec emax cy ry BY) as [IY _].
assert (EY := ball_pair_1 prec emax cx rx cy ry BX BY (fun x y => x <= y)).
assert (EN := ball_pair_1 prec emax cx rx cy ry BX BY (fun x y => ~ (x <= y))).
cbv beta in EY, EN.
destruct (xless_equal _ _ _ _ IX IY) as [LY LN].
generalize (ball_less_equal_1_bools prec emax nan_plus nan_minus nan_opp nan_abs Hp cx rx cy ry BX BY).
cbv zeta.
destruct (IeeeModel.ball_less_equal_1 prec emax nan_plus nan_minus nan_opp nan_abs cx rx cy ry)
  as [yes no].
intros [HS HA]. rewrite EY, EN, <- LY, <- LN.
trit_tail HS HA LY LN.
Qed.

Theorem ball_equal_1_correct : ball_equal_1_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs Hp cx rx cy ry BX BY.
destruct (xball_1 prec emax cx rx BX) as [IX _]. destruct (xball_1 prec emax cy ry BY) as [IY _].
assert (EY := ball_pair_1 prec emax cx rx cy ry BX BY (fun x y => x = y)).
assert (EN := ball_pair_1 prec emax cx rx cy ry BX BY (fun x y => ~ (x = y))).
cbv beta in EY, EN.
destruct (xequal _ _ _ _ IX IY) as [LY LN].
generalize (ball_equal_1_bools prec emax nan_plus nan_minus nan_opp nan_abs Hp cx rx cy ry BX BY).
cbv zeta.
destruct (IeeeModel.ball_equal_1 prec emax nan_plus nan_minus nan_opp nan_abs cx rx cy ry)
  as [yes no].
intros [HS HA]. rewrite EY, EN, <- LY, <- LN.
trit_tail HS HA LY LN.
Qed.
