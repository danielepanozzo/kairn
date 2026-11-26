(* The products of the round-up interval: what the seed and the maxima of the listings of
   upward_mul_1 and upward_mul_num_1 compute (docs/developer/design/upward.md, "The product",
   "Operations with a number" and "How they are to be proved").

   Notation: as in IeeeUpwardOps.v. A state is (u, n), the interval [-n, u]; for the operands
   x = (xu, xn) = [a, b] and y = (yu, yn) = [c, d], with a = -xval xn, b = xval xu,
   c = -xval yn, d = xval yu as extended real numbers. xmul is IEEE 754's product of extended
   real numbers, a NaN for 0 * infinity; xmul0 the product of interval arithmetic, in which
   0 * infinity = 0 (Rectangle.v); xmax and xmin the maximum and the minimum of Rectangle.v.

   The listing of the product. Each lane takes four candidates, each the product rounded up of
   two lanes or opposites of lanes: lane 0 the candidates of the upper bound bd, ac, ad, bc in
   this order, and lane 1 those of the negated lower bound -ad, -bc, -bd, -ac. The first
   candidate, the seed, has a NaN made +0; the other three are folded in by max_nl, in which a
   NaN candidate loses. Then:

     m1 = select(unord(q1, q1), 0, q1);  m2 = max_nl(q2, m1);  m3 = max_nl(q3, m2);
     m4 = max_nl(q4, m3).

   What is proved.
   - The greatest of the roundings is the rounding of the greatest: xru_xmax on extended real
     numbers, and max_nl_xru for every maximum with max_nl_ok.
   - fold4_floats and fold2_floats: what the lines above compute, on values, for every max_nl
     with max_nl_ok: the result is not a NaN, and it stands for xkeep v4 (xkeep v3 (xkeep v2
     (xseed v1))), where the vi are the values of the candidates, xseed makes a NaN 0 and
     xkeep v m is m when v is a NaN and the greater of v and m otherwise.
   - fold4_value and fold2_value, the heart of the product, on values only: if each candidate
     is xru (xmul P Q) for P and Q that are not NaN, and a candidate other than the seed that
     is 0 * infinity is matched by a candidate of the same lane at least 0 (the seed with its
     xmul0, or a candidate that is not a NaN) -- the condition fold_ok4, fold_ok2 -- then the
     fold has the value xru M, the rounding up of the greatest M of the four (two) products
     with 0 * infinity counted as 0.
   - fold_ok_mul_u, fold_ok_mul_n, fold_ok_mul_num_u, fold_ok_mul_num_n: the condition holds
     for the candidates of each lane of the two listings, whenever the operands are nonempty
     canonical states (and the number t finite): the case analysis of the design page, by
     cases on the lanes (a real number or +infinity) and on the signs.
   - upward_mul_lane_u, upward_mul_lane_n: for nonempty canonical operands and every max_nl
     with max_nl_ok, the lane 0 of the listing of upward_mul_1 before its last line stands for
     the rounding up of max(ac, ad, bc, bd), and the opposite of lane 1 for the rounding down
     of min(ac, ad, bc, bd), with 0 * infinity = 0: the bounds of the exact range of x * y
     (range_mul_upper, range_mul_lower of IeeeInterval1.v) rounded outward. Neither lane is a
     NaN.
   - upward_mul_num_lane_u, upward_mul_num_lane_n: the same for upward_mul_num_1 and a finite
     t, with the two candidates at and bt of each lane. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import IeeeBridge IeeeVocabulary IeeeOps IeeeExt IeeeDirected.
From Kairn Require Import Rectangle IeeeIntervalVocabulary IeeeInterval1.
From Kairn Require Import IeeeUpwardVocabulary IeeeUpwardMax IeeeUpwardOps.
From Kairn Require IeeeOperations IeeeUpwardOperations.
Open Scope R_scope.

(** * Extended real numbers *)

(* The value of a fold of candidates: a NaN candidate loses, and the seed has a NaN made 0. *)
Definition xkeep (v m : xreal) : xreal :=
  match v with
  | XNaN => m
  | _ => xmax v m
  end.

Definition xseed (v : xreal) : xreal :=
  match v with
  | XNaN => XFin 0
  | _ => v
  end.

(* M is the greatest of the values: one of them, and at least each. *)
Definition xgreatest4 (M v1 v2 v3 v4 : xreal) : Prop :=
  (M = v1 \/ M = v2 \/ M = v3 \/ M = v4) /\
  xle v1 M = true /\ xle v2 M = true /\ xle v3 M = true /\ xle v4 M = true.

Definition xgreatest2 (M v1 v2 : xreal) : Prop :=
  (M = v1 \/ M = v2) /\ xle v1 M = true /\ xle v2 M = true.

(* The condition on the candidates P * Q of a lane under which dropping the NaN candidates
   other than the seed gives the greatest of all with 0 * infinity counted as 0: when one of
   them is 0 * infinity, the seed's product with 0 * infinity = 0 is at least 0, or a candidate
   that is not a NaN is at least 0. *)
Definition xisnan (v : xreal) : bool :=
  match v with
  | XNaN => true
  | _ => false
  end.

Definition xkept_nonneg (P Q : xreal) : bool :=
  negb (xisnan (xmul P Q)) && xle (XFin 0) (xmul0 P Q).

Definition fold_ok4 (P1 Q1 P2 Q2 P3 Q3 P4 Q4 : xreal) : bool :=
  implb (xisnan (xmul P2 Q2) || xisnan (xmul P3 Q3) || xisnan (xmul P4 Q4))
        (xle (XFin 0) (xmul0 P1 Q1) ||
         xkept_nonneg P2 Q2 || xkept_nonneg P3 Q3 || xkept_nonneg P4 Q4).

Definition fold_ok2 (P1 Q1 P2 Q2 : xreal) : bool :=
  implb (xisnan (xmul P2 Q2)) (xle (XFin 0) (xmul0 P1 Q1) || xkept_nonneg P2 Q2).

Lemma xisnan_true : forall v : xreal, xisnan v = true <-> v = XNaN.
Proof. intros [|s|r]; cbn; split; intros H; trivial; discriminate. Qed.

Lemma xkeep_nan : forall m : xreal, xkeep XNaN m = m.
Proof. reflexivity. Qed.

Lemma xkeep_num : forall v m : xreal, v <> XNaN -> xkeep v m = xmax v m.
Proof. intros [|s|r] m H; [now elim H|reflexivity|reflexivity]. Qed.

Lemma xseed_num : forall v : xreal, v <> XNaN -> xseed v = v.
Proof. intros [|s|r] H; [now elim H|reflexivity|reflexivity]. Qed.

Lemma xmax_not_nan : forall v w : xreal, v <> XNaN -> w <> XNaN -> xmax v w <> XNaN.
Proof. intros v w Hv Hw. destruct (xmax_cases v w) as [E|E]; now rewrite E. Qed.

Lemma xmin_not_nan : forall v w : xreal, v <> XNaN -> w <> XNaN -> xmin v w <> XNaN.
Proof. intros v w Hv Hw. destruct (xmin_cases v w) as [E|E]; now rewrite E. Qed.

Lemma xopp_not_nan : forall v : xreal, v <> XNaN -> xopp v <> XNaN.
Proof. intros [|s|r] H; [now elim H|discriminate|discriminate]. Qed.

(* With 0 * infinity = 0 there is no NaN; IEEE 754's product of values that are not NaN is a
   NaN only for 0 * infinity, where xmul0 is 0, and is xmul0 otherwise. *)
Lemma xmul0_not_nan : forall P Q : xreal, P <> XNaN -> Q <> XNaN -> xmul0 P Q <> XNaN.
Proof. intros [|[|]|x] [|[|]|y]; upward_xcase. Qed.

Lemma xmul_cases0 :
  forall P Q : xreal, P <> XNaN -> Q <> XNaN ->
  (xmul P Q = XNaN /\ xmul0 P Q = XFin 0) \/ (xmul P Q <> XNaN /\ xmul P Q = xmul0 P Q).
Proof.
intros [|sp|x] [|sq|y] HP HQ; try congruence; cbn.
- right. split; [discriminate|reflexivity].
- destruct (Req_bool y 0); [left; split; reflexivity|right; split; [discriminate|reflexivity]].
- destruct (Req_bool x 0); [left; split; reflexivity|right; split; [discriminate|reflexivity]].
- right. split; [discriminate|reflexivity].
Qed.

(* The greatest of four values with an operation that keeps the order applied to each. *)
Lemma xgreatest4_xmax :
  forall v1 v2 v3 v4 : xreal,
  v1 <> XNaN -> v2 <> XNaN -> v3 <> XNaN -> v4 <> XNaN ->
  xgreatest4 (xmax (xmax v1 v2) (xmax v3 v4)) v1 v2 v3 v4.
Proof.
intros v1 v2 v3 v4 N1 N2 N3 N4. split.
- apply xmax4_cases.
- apply xmax4_ge_each; apply upward_xle_refl; assumption.
Qed.

(* The opposite of the least of four values is the greatest of their opposites. *)
Lemma xgreatest4_opp_xmin :
  forall v1 v2 v3 v4 : xreal,
  v1 <> XNaN -> v2 <> XNaN -> v3 <> XNaN -> v4 <> XNaN ->
  xgreatest4 (xopp (xmin (xmin v1 v2) (xmin v3 v4))) (xopp v1) (xopp v2) (xopp v3) (xopp v4).
Proof.
intros v1 v2 v3 v4 N1 N2 N3 N4. split.
- destruct (xmin4_cases v1 v2 v3 v4) as [E|[E|[E|E]]]; rewrite E; auto.
- destruct (xmin4_le_each v1 v2 v3 v4) as [L1 [L2 [L3 L4]]]; try (apply upward_xle_refl; assumption).
  repeat split; apply xle_opp; assumption.
Qed.

Lemma xgreatest2_xmax :
  forall v1 v2 : xreal, v1 <> XNaN -> v2 <> XNaN -> xgreatest2 (xmax v1 v2) v1 v2.
Proof.
intros v1 v2 N1 N2. split; [apply xmax_cases|].
split; [apply xmax_ge_l|apply xmax_ge_r]; apply upward_xle_refl; assumption.
Qed.

Section IeeeUpwardProduct.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_mult : float -> float -> nan_of.
Variable nan_opp : float -> nan_of.

Notation xv := (@xval prec emax).
Notation xru := (xru prec emax).
Notation xrd := (xrd prec emax).
Notation mul_ru := (IeeeUpwardOperations.mul_ru prec emax nan_mult).
Notation unord := (IeeeUpwardOperations.unord prec emax).
Notation max_nl_ok := (IeeeUpwardOperations.max_nl_ok prec emax).
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation pzero := (IeeeOperations.pzero prec emax).

(** * The greatest of the roundings is the rounding of the greatest *)

Lemma xru_not_nan : forall v : xreal, v <> XNaN -> xru v <> XNaN.
Proof. intros v H K. apply H. now apply (xru_nan prec emax). Qed.

Theorem xru_xmax :
  forall A B : xreal, A <> XNaN -> B <> XNaN -> xru (xmax A B) = xmax (xru A) (xru B).
Proof.
intros A B NA NB. unfold xmax at 1.
assert (RA := upward_xle_refl _ (xru_not_nan A NA)).
assert (RB := upward_xle_refl _ (xru_not_nan B NB)).
destruct (xlt A B) eqn:L.
- (* A < B: xru A <= xru B, so their maximum is xru B *)
  assert (M := xru_mono prec emax A B (upward_xlt_xle A B L)).
  unfold xmax. destruct (xlt (xru A) (xru B)) eqn:K; [reflexivity|].
  symmetry. exact (upward_xle_xlt_eq _ _ M K).
- (* B <= A: xru B <= xru A, and xru A < xru B is false *)
  assert (M := xru_mono prec emax B A (upward_xlt_false_xle B A NB NA L)).
  unfold xmax. destruct (xlt (xru A) (xru B)) eqn:K; [|reflexivity].
  exfalso. exact (upward_xle_xlt_false _ _ M K).
Qed.

(* The same for every maximum with the property max_nl_ok, on limbs whose values are the
   roundings up of A and B: its result is the rounding up of the greater. *)
Theorem max_nl_xru :
  forall m : float -> float -> float, max_nl_ok m ->
  forall (a b : float) (A B : xreal),
  ~ nan a -> ~ nan b -> A <> XNaN -> B <> XNaN ->
  xv a = xru A -> xv b = xru B -> xv (m a b) = xru (xmax A B).
Proof.
intros m Hm a b A B Na Nb NA NB Ea Eb.
rewrite (max_nl_xval prec emax m Hm a b Na Nb), Ea, Eb. symmetry. now apply xru_xmax.
Qed.

(** * What the seed and the maxima compute *)

Lemma unord_self : forall q : float, unord q q = is_nan prec emax q.
Proof. intros q. unfold IeeeUpwardOperations.unord. now destruct (is_nan prec emax q). Qed.

(* The seed: select(unord(q, q), 0, q). *)
Lemma seed_xval :
  forall q : float,
  ~ nan (if unord q q then pzero else q) /\
  xv (if unord q q then pzero else q) = xseed (xv q).
Proof.
intros q. rewrite unord_self. destruct (is_nan prec emax q) eqn:N.
- rewrite (proj2 (upward_xval_nan prec emax q) N).
  split; [intros K; discriminate K|reflexivity].
- assert (K : ~ nan q) by (unfold nan; rewrite N; discriminate).
  split; [exact K|]. symmetry. apply xseed_num. now apply upward_not_nan_xval.
Qed.

(* One step of the fold: max_nl(q, m) with m not a NaN. *)
Lemma step_xval :
  forall m : float -> float -> float, max_nl_ok m ->
  forall q r : float, ~ nan r -> ~ nan (m q r) /\ xv (m q r) = xkeep (xv q) (xv r).
Proof.
intros m Hm q r Nr. destruct (max_nl_xkeep prec emax m Hm q r Nr) as [N E].
split; [exact N|]. rewrite E.
destruct (is_nan prec emax q) eqn:Nq.
- now rewrite (proj2 (upward_xval_nan prec emax q) Nq).
- symmetry. apply xkeep_num. apply upward_not_nan_xval. unfold nan. rewrite Nq. discriminate.
Qed.

(* The seed and three maxima, for every max_nl with the property. *)
Theorem fold4_floats :
  forall m : float -> float -> float, max_nl_ok m ->
  forall q1 q2 q3 q4 : float,
  let m1 := if unord q1 q1 then pzero else q1 in
  let m4 := m q4 (m q3 (m q2 m1)) in
  ~ nan m4 /\ xv m4 = xkeep (xv q4) (xkeep (xv q3) (xkeep (xv q2) (xseed (xv q1)))).
Proof.
intros m Hm q1 q2 q3 q4 m1 m4.
destruct (seed_xval q1) as [N1 E1]. fold m1 in N1, E1.
destruct (step_xval m Hm q2 m1 N1) as [N2 E2].
destruct (step_xval m Hm q3 _ N2) as [N3 E3].
destruct (step_xval m Hm q4 _ N3) as [N4 E4].
split; [exact N4|]. unfold m4. rewrite E4, E3, E2, E1. reflexivity.
Qed.

(* The seed and one maximum. *)
Theorem fold2_floats :
  forall m : float -> float -> float, max_nl_ok m ->
  forall q1 q2 : float,
  let m1 := if unord q1 q1 then pzero else q1 in
  ~ nan (m q2 m1) /\ xv (m q2 m1) = xkeep (xv q2) (xseed (xv q1)).
Proof.
intros m Hm q1 q2 m1.
destruct (seed_xval q1) as [N1 E1]. fold m1 in N1, E1.
destruct (step_xval m Hm q2 m1 N1) as [N2 E2].
split; [exact N2|]. rewrite E2, E1. reflexivity.
Qed.

(** * The heart of the product, on values *)

(* The seed of candidates P * Q rounded up: with its NaN made 0, the rounding up of the product
   with 0 * infinity = 0. *)
Lemma xseed_step :
  forall P Q : xreal, P <> XNaN -> Q <> XNaN ->
  xseed (xru (xmul P Q)) = xru (xmul0 P Q) /\ xru (xmul0 P Q) <> XNaN.
Proof.
intros P Q HP HQ. split; [|apply xru_not_nan; now apply xmul0_not_nan].
destruct (xmul_cases0 P Q HP HQ) as [[E W]|[N E]].
- rewrite E, W, (xru_0 prec emax). reflexivity.
- rewrite E. apply xseed_num. apply xru_not_nan. now apply xmul0_not_nan.
Qed.

(* One step of the fold, with the candidate P * Q rounded up and a running maximum m that is
   not a NaN. *)
Lemma xkeep_step :
  forall P Q m : xreal, P <> XNaN -> Q <> XNaN -> m <> XNaN ->
  xkeep (xru (xmul P Q)) m <> XNaN /\
  xle m (xkeep (xru (xmul P Q)) m) = true /\
  (xmul P Q <> XNaN -> xle (xru (xmul0 P Q)) (xkeep (xru (xmul P Q)) m) = true) /\
  (xkeep (xru (xmul P Q)) m = m \/ xkeep (xru (xmul P Q)) m = xru (xmul0 P Q)).
Proof.
intros P Q m HP HQ Hm.
assert (Rm := upward_xle_refl m Hm).
destruct (xmul_cases0 P Q HP HQ) as [[E W]|[N E]].
- rewrite E. change (xru XNaN) with XNaN. rewrite xkeep_nan.
  split; [exact Hm|split; [exact Rm|split; [intros K; now elim K|now left]]].
- rewrite E. assert (Nw := xru_not_nan _ (xmul0_not_nan P Q HP HQ)).
  rewrite (xkeep_num _ m Nw). assert (Rw := upward_xle_refl _ Nw).
  split; [exact (xmax_not_nan _ _ Nw Hm)|].
  split; [exact (xmax_ge_r _ _ Rw Rm)|].
  split; [intros _; exact (xmax_ge_l _ _ Rw Rm)|].
  destruct (xmax_cases (xru (xmul0 P Q)) m) as [K|K]; rewrite K; auto.
Qed.

(* The heart of the product: four candidates P_i * Q_i rounded up, the first the seed. If the
   candidates satisfy fold_ok4, the fold has the value of the rounding up of the greatest of
   the four products with 0 * infinity = 0. *)
Theorem fold4_value :
  forall P1 Q1 P2 Q2 P3 Q3 P4 Q4 : xreal,
  P1 <> XNaN -> Q1 <> XNaN -> P2 <> XNaN -> Q2 <> XNaN ->
  P3 <> XNaN -> Q3 <> XNaN -> P4 <> XNaN -> Q4 <> XNaN ->
  fold_ok4 P1 Q1 P2 Q2 P3 Q3 P4 Q4 = true ->
  forall M : xreal,
  xgreatest4 M (xmul0 P1 Q1) (xmul0 P2 Q2) (xmul0 P3 Q3) (xmul0 P4 Q4) ->
  xkeep (xru (xmul P4 Q4)) (xkeep (xru (xmul P3 Q3)) (xkeep (xru (xmul P2 Q2))
    (xseed (xru (xmul P1 Q1))))) = xru M.
Proof.
intros P1 Q1 P2 Q2 P3 Q3 P4 Q4 HP1 HQ1 HP2 HQ2 HP3 HQ3 HP4 HQ4 Hok M HM.
destruct (xseed_step P1 Q1 HP1 HQ1) as [S1 N1]. rewrite S1.
destruct (xkeep_step P2 Q2 _ HP2 HQ2 N1) as [N2 [L2 [K2 C2]]].
revert N2 L2 K2 C2. generalize (xkeep (xru (xmul P2 Q2)) (xru (xmul0 P1 Q1))) as f2.
intros f2 N2 L2 K2 C2.
destruct (xkeep_step P3 Q3 _ HP3 HQ3 N2) as [N3 [L3 [K3 C3]]].
revert N3 L3 K3 C3. generalize (xkeep (xru (xmul P3 Q3)) f2) as f3.
intros f3 N3 L3 K3 C3.
destruct (xkeep_step P4 Q4 _ HP4 HQ4 N3) as [N4 [L4 [K4 C4]]].
revert N4 L4 K4 C4. generalize (xkeep (xru (xmul P4 Q4)) f3) as f4.
intros f4 N4 L4 K4 C4.
(* every candidate kept is at most f4, the seed included *)
assert (G1 : xle (xru (xmul0 P1 Q1)) f4 = true).
{ apply xle_trans with (1 := L2). apply xle_trans with (1 := L3). exact L4. }
assert (G2 : xmul P2 Q2 <> XNaN -> xle (xru (xmul0 P2 Q2)) f4 = true).
{ intros K. apply xle_trans with (1 := K2 K). apply xle_trans with (1 := L3). exact L4. }
assert (G3 : xmul P3 Q3 <> XNaN -> xle (xru (xmul0 P3 Q3)) f4 = true).
{ intros K. apply xle_trans with (1 := K3 K). exact L4. }
(* when a candidate is dropped, f4 is at least 0 *)
assert (Z : xmul P2 Q2 = XNaN \/ xmul P3 Q3 = XNaN \/ xmul P4 Q4 = XNaN ->
            xle (XFin 0) f4 = true).
{ intros D.
  assert (T : (xisnan (xmul P2 Q2) || xisnan (xmul P3 Q3) || xisnan (xmul P4 Q4))%bool = true).
  { destruct D as [D|[D|D]]; rewrite D; cbn; [reflexivity| |];
      now rewrite ?Bool.orb_true_r. }
  unfold fold_ok4 in Hok. rewrite T in Hok. cbn [implb] in Hok.
  assert (U : forall P Q : xreal, xle (XFin 0) (xmul0 P Q) = true ->
              xle (XFin 0) (xru (xmul0 P Q)) = true).
  { intros P Q H. rewrite <- (xru_0 prec emax). now apply (xru_mono prec emax). }
  assert (V : forall P Q : xreal, xkept_nonneg P Q = true ->
              xmul P Q <> XNaN /\ xle (XFin 0) (xru (xmul0 P Q)) = true).
  { intros P Q H. unfold xkept_nonneg in H. apply andb_true_iff in H. destruct H as [H1 H2].
    split; [|now apply U]. intros E. rewrite E in H1. discriminate H1. }
  apply orb_true_iff in Hok. destruct Hok as [Hok|Hok4].
  apply orb_true_iff in Hok. destruct Hok as [Hok|Hok3].
  apply orb_true_iff in Hok. destruct Hok as [Hok1|Hok2].
  - exact (xle_trans _ _ _ (U _ _ Hok1) G1).
  - destruct (V _ _ Hok2) as [K H]. exact (xle_trans _ _ _ H (G2 K)).
  - destruct (V _ _ Hok3) as [K H]. exact (xle_trans _ _ _ H (G3 K)).
  - destruct (V _ _ Hok4) as [K H]. exact (xle_trans _ _ _ H (K4 K)). }
(* f4 is the rounding of one of the four products *)
assert (Mem : f4 = xru (xmul0 P1 Q1) \/ f4 = xru (xmul0 P2 Q2) \/
              f4 = xru (xmul0 P3 Q3) \/ f4 = xru (xmul0 P4 Q4)).
{ destruct C4 as [E4|E4]; [|now right; right; right]. rewrite E4.
  destruct C3 as [E3|E3]; [|now right; right; left]. rewrite E3.
  destruct C2 as [E2|E2]; [now left|now right; left]. }
destruct HM as [HMm [H1 [H2 [H3 H4]]]].
apply xle_antisym.
- destruct Mem as [E|[E|[E|E]]]; rewrite E; apply (xru_mono prec emax); assumption.
- (* the rounding of M, one of the four, is at most f4 *)
  assert (Drop : forall P Q : xreal, P <> XNaN -> Q <> XNaN ->
                 (xmul P Q <> XNaN -> xle (xru (xmul0 P Q)) f4 = true) ->
                 (xmul P Q = XNaN -> xle (XFin 0) f4 = true) ->
                 xle (xru (xmul0 P Q)) f4 = true).
  { intros P Q HP HQ Kept Dropped.
    destruct (xmul_cases0 P Q HP HQ) as [[E W]|[E _]].
    - rewrite W, (xru_0 prec emax). exact (Dropped E).
    - exact (Kept E). }
  destruct HMm as [E|[E|[E|E]]]; rewrite E.
  + exact G1.
  + apply Drop; [assumption|assumption|exact G2|intros D; apply Z; now left].
  + apply Drop; [assumption|assumption|exact G3|intros D; apply Z; now right; left].
  + apply Drop; [assumption|assumption|exact K4|intros D; apply Z; now right; right].
Qed.

(* The same with the seed and one candidate. *)
Theorem fold2_value :
  forall P1 Q1 P2 Q2 : xreal,
  P1 <> XNaN -> Q1 <> XNaN -> P2 <> XNaN -> Q2 <> XNaN ->
  fold_ok2 P1 Q1 P2 Q2 = true ->
  forall M : xreal, xgreatest2 M (xmul0 P1 Q1) (xmul0 P2 Q2) ->
  xkeep (xru (xmul P2 Q2)) (xseed (xru (xmul P1 Q1))) = xru M.
Proof.
intros P1 Q1 P2 Q2 HP1 HQ1 HP2 HQ2 Hok M HM.
destruct (xseed_step P1 Q1 HP1 HQ1) as [S1 N1]. rewrite S1.
destruct (xkeep_step P2 Q2 _ HP2 HQ2 N1) as [N2 [L2 [K2 C2]]].
revert N2 L2 K2 C2. generalize (xkeep (xru (xmul P2 Q2)) (xru (xmul0 P1 Q1))) as f2.
intros f2 N2 L2 K2 C2.
destruct HM as [HMm [H1 H2]].
apply xle_antisym.
- destruct C2 as [E|E]; rewrite E; apply (xru_mono prec emax); assumption.
- destruct HMm as [E|E]; rewrite E; [exact L2|].
  destruct (xmul_cases0 P2 Q2 HP2 HQ2) as [[D W]|[D _]]; [|exact (K2 D)].
  rewrite W, (xru_0 prec emax).
  unfold fold_ok2 in Hok. rewrite D in Hok. cbn [xisnan implb] in Hok.
  apply orb_true_iff in Hok. destruct Hok as [Hok|Hok].
  + apply xle_trans with (2 := L2). rewrite <- (xru_0 prec emax).
    now apply (xru_mono prec emax).
  + unfold xkept_nonneg in Hok. rewrite D in Hok. discriminate Hok.
Qed.

(** * The case analysis: the candidates of each lane satisfy the condition *)

(* A lane value: a real number or +infinity, as the lanes of a nonempty canonical state. *)
Definition xlane (v : xreal) : Prop := v = XInf false \/ exists r : R, v = XFin r.

Lemma xlane_not_nan : forall v : xreal, xlane v -> v <> XNaN.
Proof. intros v [E|[r E]]; rewrite E; discriminate. Qed.

Lemma upward_nonempty_xlane :
  forall u n : float, upward_nonempty_1 u n -> xlane (xv u) /\ xlane (xv n).
Proof. intros u n H. exact (upward_nonempty_lane_values prec emax u n H). Qed.

(* The cases of the signs: every comparison of real numbers left in the goal, then a
   contradiction by arithmetic in the cases where the goal is false. *)
Local Ltac fold_ok_cases :=
  cbn in *;
  repeat match goal with H : Rle_bool _ _ = true |- _ => apply Rle_bool_inv in H end;
  unfold fold_ok4, fold_ok2, xkept_nonneg; cbn;
  try reflexivity;
  repeat (match goal with
          | |- context [Req_bool ?x ?y] => destruct (Req_bool_spec x y)
          | |- context [Rlt_bool ?x ?y] => destruct (Rlt_bool_spec x y)
          | |- context [Rle_bool ?x ?y] => destruct (Rle_bool_spec x y)
          end; cbn; try reflexivity);
  try (exfalso; lra); try (exfalso; nra); upward_neq; try (exfalso; subst; nra).

(* Lane 0 of upward_mul_1: the candidates of the upper bound in the order of the listing,
   bd (the seed), ac, ad, bc, with x = (U, N) = [-N, U] and y = (U', N') = [-N', U']. *)
Theorem fold_ok_mul_u :
  forall U N U' N' : xreal,
  xlane U -> xlane N -> xlane U' -> xlane N' ->
  xle (xopp N) U = true -> xle (xopp N') U' = true ->
  fold_ok4 U U' N N' N (xopp U') U (xopp N') = true.
Proof.
intros U N U' N' [->|[u ->]] [->|[n ->]] [->|[u' ->]] [->|[n' ->]] Hx Hy;
  fold_ok_cases.
Qed.

(* Lane 1 of upward_mul_1: the candidates of the negated lower bound, -ad (the seed), -bc,
   -bd, -ac. *)
Theorem fold_ok_mul_n :
  forall U N U' N' : xreal,
  xlane U -> xlane N -> xlane U' -> xlane N' ->
  xle (xopp N) U = true -> xle (xopp N') U' = true ->
  fold_ok4 N U' U N' U (xopp U') N (xopp N') = true.
Proof.
intros U N U' N' [->|[u ->]] [->|[n ->]] [->|[u' ->]] [->|[n' ->]] Hx Hy;
  fold_ok_cases.
Qed.

(* upward_mul_num_1 with a finite t: lane 0, bt (the seed) and at; lane 1, -at (the seed)
   and -bt. *)
Theorem fold_ok_mul_num_u :
  forall (U N : xreal) (t : R),
  xlane U -> xlane N -> xle (xopp N) U = true ->
  fold_ok2 U (XFin t) N (xopp (XFin t)) = true.
Proof.
intros U N t [->|[u ->]] [->|[n ->]] Hx; fold_ok_cases.
Qed.

Theorem fold_ok_mul_num_n :
  forall (U N : xreal) (t : R),
  xlane U -> xlane N -> xle (xopp N) U = true ->
  fold_ok2 N (XFin t) U (xopp (XFin t)) = true.
Proof.
intros U N t [->|[u ->]] [->|[n ->]] Hx; fold_ok_cases.
Qed.

(** * The two lanes of the listings *)

(* The four products of bounds of the lanes, with 0 * infinity = 0, as the candidates of the
   lanes see them: xmul0 of lanes and of their opposites. *)
Lemma xmul0_opp_opp : forall v w : xreal, xmul0 (xopp v) (xopp w) = xmul0 v w.
Proof. intros v w. rewrite xmul0_opp_l, xmul0_opp_r. apply xopp_involutive. Qed.

Section Lanes.
Variable m : float -> float -> float.
Hypothesis m_ok : max_nl_ok m.
Variables xu xn yu yn : float.
Hypothesis HX : upward_nonempty_1 xu xn.
Hypothesis HY : upward_nonempty_1 yu yn.

(* The bounds: x = [a, b], y = [c, d]. *)
Let a := xopp (xv xn).
Let b := xv xu.
Let c := xopp (xv yn).
Let d := xv yu.

Let LX := upward_nonempty_xlane xu xn HX.
Let LY := upward_nonempty_xlane yu yn HY.

Lemma lanes_not_nan :
  xv xu <> XNaN /\ xv xn <> XNaN /\ xv yu <> XNaN /\ xv yn <> XNaN /\
  xopp (xv yu) <> XNaN /\ xopp (xv yn) <> XNaN.
Proof.
destruct LX as [Lu Ln]. destruct LY as [Mu Mn].
repeat split; try apply xopp_not_nan; apply xlane_not_nan; assumption.
Qed.

Lemma corners_not_nan :
  xmul0 a c <> XNaN /\ xmul0 a d <> XNaN /\ xmul0 b c <> XNaN /\ xmul0 b d <> XNaN.
Proof.
destruct lanes_not_nan as [N1 [N2 [N3 [N4 _]]]].
unfold a, b, c, d. repeat split; apply xmul0_not_nan; try apply xopp_not_nan; assumption.
Qed.

(* Lane 0 of upward_mul_1, the lines of the seed and the three maxima: the rounding up of the
   upper bound of the exact range, max(ac, ad, bc, bd) with 0 * infinity = 0. *)
Theorem upward_mul_lane_u :
  let q1 := mul_ru xu yu in
  let q2 := mul_ru xn yn in
  let q3 := mul_ru xn (neg yu) in
  let q4 := mul_ru xu (neg yn) in
  let m1 := if unord q1 q1 then pzero else q1 in
  let z := m q4 (m q3 (m q2 m1)) in
  ~ nan z /\
  xv z = xru (xmax (xmax (xmul0 a c) (xmul0 a d)) (xmax (xmul0 b c) (xmul0 b d))).
Proof.
intros q1 q2 q3 q4 m1 z.
destruct (fold4_floats m m_ok q1 q2 q3 q4) as [N E]. fold m1 z in N, E.
split; [exact N|]. rewrite E.
unfold q1, q2, q3, q4. rewrite 4!(mul_ru_xval prec emax), 2!(xval_neg prec emax).
destruct lanes_not_nan as [N1 [N2 [N3 [N4 [N5 N6]]]]].
destruct corners_not_nan as [C1 [C2 [C3 C4]]].
destruct LX as [Lu Ln]. destruct LY as [Mu Mn].
apply fold4_value; try assumption.
- apply fold_ok_mul_u; try assumption; [exact (proj1 HX)|exact (proj1 HY)].
- (* the greatest of bd, ac, ad, bc is that of ac, ad, bc, bd *)
  destruct (xgreatest4_xmax _ _ _ _ C1 C2 C3 C4) as [Mm [M1 [M2 [M3 M4]]]].
  assert (E2 : xmul0 (xv xn) (xv yn) = xmul0 a c)
    by (unfold a, c; now rewrite xmul0_opp_opp).
  assert (E3 : xmul0 (xv xn) (xopp (xv yu)) = xmul0 a d)
    by (unfold a, d; now rewrite xmul0_opp_l, xmul0_opp_r).
  rewrite E2, E3.
  change (xmul0 (xv xu) (xv yu)) with (xmul0 b d).
  change (xmul0 (xv xu) (xopp (xv yn))) with (xmul0 b c).
  split; [|tauto].
  destruct Mm as [K|[K|[K|K]]]; [right; left|right; right; left|right; right; right|left];
    exact K.
Qed.

(* Lane 1 of upward_mul_1: the opposite of the result is the rounding down of the lower bound
   of the exact range, min(ac, ad, bc, bd) with 0 * infinity = 0. *)
Theorem upward_mul_lane_n :
  let q1 := mul_ru xn yu in
  let q2 := mul_ru xu yn in
  let q3 := mul_ru xu (neg yu) in
  let q4 := mul_ru xn (neg yn) in
  let m1 := if unord q1 q1 then pzero else q1 in
  let z := m q4 (m q3 (m q2 m1)) in
  ~ nan z /\
  xopp (xv z) = xrd (xmin (xmin (xmul0 a c) (xmul0 a d)) (xmin (xmul0 b c) (xmul0 b d))).
Proof.
intros q1 q2 q3 q4 m1 z.
destruct (fold4_floats m m_ok q1 q2 q3 q4) as [N E]. fold m1 z in N, E.
split; [exact N|]. apply (upward_lane_lower prec emax). rewrite E.
unfold q1, q2, q3, q4. rewrite 4!(mul_ru_xval prec emax), 2!(xval_neg prec emax).
destruct lanes_not_nan as [N1 [N2 [N3 [N4 [N5 N6]]]]].
destruct corners_not_nan as [C1 [C2 [C3 C4]]].
destruct LX as [Lu Ln]. destruct LY as [Mu Mn].
apply fold4_value; try assumption.
- apply fold_ok_mul_n; try assumption; [exact (proj1 HX)|exact (proj1 HY)].
- (* the greatest of -ad, -bc, -bd, -ac is the opposite of the least of ac, ad, bc, bd *)
  destruct (xgreatest4_opp_xmin _ _ _ _ C1 C2 C3 C4) as [Mm [M1 [M2 [M3 M4]]]].
  assert (E1 : xmul0 (xv xn) (xv yu) = xopp (xmul0 a d))
    by (unfold a, d; now rewrite xmul0_opp_l, xopp_involutive).
  assert (E2 : xmul0 (xv xu) (xv yn) = xopp (xmul0 b c))
    by (unfold b, c; now rewrite xmul0_opp_r, xopp_involutive).
  assert (E3 : xmul0 (xv xu) (xopp (xv yu)) = xopp (xmul0 b d))
    by (unfold b, d; now rewrite xmul0_opp_r).
  assert (E4 : xmul0 (xv xn) (xopp (xv yn)) = xopp (xmul0 a c))
    by (unfold a, c; now rewrite xmul0_opp_opp, xmul0_opp_r).
  rewrite E1, E2, E3, E4.
  split; [|tauto].
  destruct Mm as [K|[K|[K|K]]]; [right; right; right|left|right; left|right; right; left];
    exact K.
Qed.

End Lanes.

Section NumberLanes.
Variable m : float -> float -> float.
Hypothesis m_ok : max_nl_ok m.
Variables xu xn t : float.
Hypothesis HX : upward_nonempty_1 xu xn.
Hypothesis Ht : finite t.

Let a := xopp (xv xn).
Let b := xv xu.
Let T := xv t.

Let LX := upward_nonempty_xlane xu xn HX.

Lemma number_value : T = XFin (val t).
Proof. exact (upward_xval_finite prec emax t Ht). Qed.

(* Lane 0 of upward_mul_num_1 for a finite t, the lines of the seed and the maximum: the
   rounding up of max(at, bt), with 0 * infinity = 0. *)
Theorem upward_mul_num_lane_u :
  let p1 := mul_ru xu t in
  let p2 := mul_ru xn (neg t) in
  let m1 := if unord p1 p1 then pzero else p1 in
  let z := m p2 m1 in
  ~ nan z /\ xv z = xru (xmax (xmul0 a T) (xmul0 b T)).
Proof.
intros p1 p2 m1 z.
destruct (fold2_floats m m_ok p1 p2) as [N E]. fold m1 z in N, E.
split; [exact N|]. rewrite E.
unfold p1, p2. rewrite 2!(mul_ru_xval prec emax), (xval_neg prec emax).
destruct LX as [Lu Ln]. fold T. rewrite number_value.
assert (Nu := xlane_not_nan _ Lu). assert (Nn := xlane_not_nan _ Ln).
assert (Nt : XFin (val t) <> XNaN) by discriminate.
assert (Nt' : xopp (XFin (val t)) <> XNaN) by discriminate.
assert (Ca : xmul0 a (XFin (val t)) <> XNaN)
  by (apply xmul0_not_nan; [apply xopp_not_nan|]; assumption).
assert (Cb : xmul0 b (XFin (val t)) <> XNaN) by (apply xmul0_not_nan; assumption).
apply fold2_value; try assumption.
- apply fold_ok_mul_num_u; try assumption. exact (proj1 HX).
- (* the greatest of bt, at *)
  assert (E2 : xmul0 (xv xn) (xopp (XFin (val t))) = xmul0 a (XFin (val t)))
    by (unfold a; now rewrite xmul0_opp_l, xmul0_opp_r).
  rewrite E2. change (xmul0 (xv xu) (XFin (val t))) with (xmul0 b (XFin (val t))).
  destruct (xgreatest2_xmax _ _ Ca Cb) as [Mm [M1 M2]].
  split; [destruct Mm as [K|K]; [right|left]; exact K|split; assumption].
Qed.

(* Lane 1 of upward_mul_num_1 for a finite t: the opposite of the result is the rounding down
   of min(at, bt). *)
Theorem upward_mul_num_lane_n :
  let p1 := mul_ru xn t in
  let p2 := mul_ru xu (neg t) in
  let m1 := if unord p1 p1 then pzero else p1 in
  let z := m p2 m1 in
  ~ nan z /\ xopp (xv z) = xrd (xmin (xmul0 a T) (xmul0 b T)).
Proof.
intros p1 p2 m1 z.
destruct (fold2_floats m m_ok p1 p2) as [N E]. fold m1 z in N, E.
split; [exact N|]. apply (upward_lane_lower prec emax). rewrite E.
unfold p1, p2. rewrite 2!(mul_ru_xval prec emax), (xval_neg prec emax).
destruct LX as [Lu Ln]. fold T. rewrite number_value.
assert (Nu := xlane_not_nan _ Lu). assert (Nn := xlane_not_nan _ Ln).
assert (Nt : XFin (val t) <> XNaN) by discriminate.
assert (Nt' : xopp (XFin (val t)) <> XNaN) by discriminate.
assert (Ca : xmul0 a (XFin (val t)) <> XNaN)
  by (apply xmul0_not_nan; [apply xopp_not_nan|]; assumption).
assert (Cb : xmul0 b (XFin (val t)) <> XNaN) by (apply xmul0_not_nan; assumption).
apply fold2_value; try assumption.
- apply fold_ok_mul_num_n; try assumption. exact (proj1 HX).
- (* the greatest of -at, -bt is the opposite of the least of at, bt *)
  assert (E1 : xmul0 (xv xn) (XFin (val t)) = xopp (xmul0 a (XFin (val t))))
    by (unfold a; now rewrite xmul0_opp_l, xopp_involutive).
  assert (E2 : xmul0 (xv xu) (xopp (XFin (val t))) = xopp (xmul0 b (XFin (val t))))
    by (unfold b; now rewrite xmul0_opp_r).
  rewrite E1, E2. unfold xmin.
  assert (Ra := upward_xle_refl _ Ca). assert (Rb := upward_xle_refl _ Cb).
  destruct (xlt (xmul0 b (XFin (val t))) (xmul0 a (XFin (val t)))) eqn:L.
  + split; [now right|]. split; [|apply upward_xle_refl; now apply xopp_not_nan].
    apply xle_opp. now apply upward_xlt_xle.
  + split; [now left|]. split; [apply upward_xle_refl; now apply xopp_not_nan|].
    apply xle_opp. now apply upward_xlt_false_xle.
Qed.

End NumberLanes.

End IeeeUpwardProduct.
