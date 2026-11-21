(* What a user of the accumulator relies on: after any history of additions, products and
   merges, the radius that the header computes bounds the error of the running sum.

   docs/developer/design/milestone2.md, "The accumulator". An accumulator of k limbs holds
   a running k-number s, a running sum a in T of the magnitudes of the leading limbs of
   what was added, and a count n. Its operations are kernels, proved in AccKernels.v:

       acc.add(x)              (s, a) <- acc_add_k (s, a, x)          n <- n + 1
       acc.add_product(x, y)   (s, a) <- acc_mul_entry_1 (s, a, x, y) n <- n + 1   (one limb)
                               (s, a) <- acc_mul_2 (s, a, x, y)       n <- n + 1   (two limbs)
       acc.merge(other)        (s, a) <- acc_merge_k (s, a, s', a')   n <- n + n'
       acc.error_bound()       (g, t, ok) = bound_dot_k (m),  (r, ok') = acc_radius_k (a, m, g, t)

   with m the count n as a number of T. A history is a tree: a merge takes the history of
   the other accumulator, which may itself contain merges. This file states the guarantee
   for such a history in the real model (every value a number of the format, nothing
   overflows), and proves it.

   Definitions.
   - hist E: the history of an accumulator, Hnil (a new one), Hadd h x, Hmul h x y,
     Hmerge h h'. E is R for one limb and R * R (the two limbs) for two.
   - count h: the number of terms, 1 for each add and add_product, the sum on a merge.
   - terms v h: the exact terms, in the order of the history: v x for an add, v x * v y for
     a product, those of both histories for a merge; v is the value of an element (x
     itself for one limb, x0 + x1 for two). The exact sum is sumR (terms v h).
   - leads l h: the magnitudes the kernels add to a: |x0| for an add, |x0| |y0| for a
     product (l the leading limb: x itself for one limb, x0 for two).
   - run1 h, run2 h: the state (s, a), (s0, s1, a) after the history, the kernels of the
     real model applied in its order, from the state of a new accumulator, every limb 0.

   What is proved, for a history whose elements are numbers of the format (one limb) or
   normalized pairs (two limbs), with u = 2^-prec, eta = 2^emin:

   (A1) acc_1_mags, acc_2_mags. The sum of the magnitudes the kernels add is bounded by a:
            sumR (leads h) <= (1 + u)^n (a + n eta / 2).
        For one limb the magnitudes are those of the terms; for two limbs the magnitude of
        each exact term is at most (1 + u)^2 times its leading magnitude (|x| <= (1 + u) |x0|
        for a normalized pair), so
            sum |terms| <= (1 + u)^(n+2) (a + n eta / 2)          (acc_2_terms_mags)
        which is the inequality of the design page. Each kernel rounds a nonnegative sum to
        nearest once: a sum of two numbers of the format loses at most a factor 1 + u, the
        fused |x0| |y0| + a also eta / 2; on a merge of two histories with n1, n2 >= 1 terms,
        max(n1, n2) + 1 <= n1 + n2. A history without a term has a = 0 and nothing to bound.
   (A3) acc_1_error, acc_2_error. The error of the running sum, in the form of the statement
        of dot_k for n terms, whatever the shape of the tree:
            one limb:  |s - sum terms| <= ((1 + e)^n - 1) sum |terms| + (1 + e)^(n-1) n eta/2,
                       e = u / (1 + u);
            two limbs: |s - sum terms| <= ((1 + 4 u^2) (1 + e)^(n-1) - 1) sum |terms|
                                          + (1 + e)^(n-1) n (3/2) eta,   e = 3 u^2 / (1 - 4 u).
        The history is mapped to a tree of Summation.v (tree1, tree2): an add is a node with
        the element as a leaf, a merge a node of the two trees, and a history without a term
        no tree at all, adding to the zero state being exact for two limbs (add_2_2_zero_l,
        add_2_2_zero_r) and for one limb with an operand of the format; the state is the value
        of the tree (tree1_facts, tree2_facts). For two limbs the leaves are the elements and
        the products mul_2_2 (x, y), within 4 u^2 |x y| + 3/2 eta of the exact products, and
        the height is at most n - 1 (tree_sum_approx, height_le_leaves). For one limb a product
        is one fused operation of the state and the exact product: a leaf x y, with the zero
        state as a leaf when the accumulator had no term; the absolute error eta / 2 is
        charged to each exact product, and the height is at most n (tree_sum_weighted).
   (A3') acc_1_chain, acc_2_chain. With (g, t, ok) = bound_dot_k (m) and
        (r, ok') = acc_radius_k (a, m, g, t), for m a number of the format that is 0 or at
        least 1 and at least n, if ok and ok' then
            |s - sum terms| <= g sum |terms| + t <= r.
        The first inequality is (A3) and the statement of bound_dot_k (dot_1_use, dot_2_use of
        FoldGuarantee.v). The second is (A1), (1 + u)^n <= 1 + m u + 2 m^2 u^2 for n <= m and
        m u <= 1/2 (gamma_le_real, div_one_minus_le), which ok' gives, and the bound on r of
        acc_radius_k (acc_radius_1_facts, AccKernels.v).
   The final theorems, acc_1_bound and acc_2_bound: |s - sum terms| <= r.

   What is assumed: precision at least 2 (one limb) or 4 (two limbs); a format that contains
   1/2 (eta <= 1/2, which bound_dot_k requires); every element of the history a number of
   the format, every pair normalized; m a number of the format, 0 or at least 1, and at least
   the count. The count is a natural number here. The IEEE model (overflow, infinities,
   NaN) is IeeeAccumulator.v: there the same holds when the running sum and the radius are
   finite and both masks true. Not covered: the count as a machine integer and its
   conversion to T, and that the C++ header calls the kernels in this way. *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Guard OneLimb Add22 Mul22 Ball2 Folds Summation SummationKernels
  BoundKernels FoldGuarantee StepKernels AccKernels.
Import ListNotations.
Open Scope R_scope.

(** * Histories *)

Inductive hist (E : Type) : Type :=
| Hnil : hist E
| Hadd : hist E -> E -> hist E
| Hmul : hist E -> E -> E -> hist E
| Hmerge : hist E -> hist E -> hist E.

Arguments Hnil {E}.
Arguments Hadd {E} h x.
Arguments Hmul {E} h x y.
Arguments Hmerge {E} h1 h2.

Section Histories.
Variable E : Type.

(* The number of terms. *)
Fixpoint count (h : hist E) : nat :=
  match h with
  | Hnil => O
  | Hadd h _ => S (count h)
  | Hmul h _ _ => S (count h)
  | Hmerge h1 h2 => (count h1 + count h2)%nat
  end.

(* Every element satisfies P. *)
Fixpoint elems (P : E -> Prop) (h : hist E) : Prop :=
  match h with
  | Hnil => True
  | Hadd h x => elems P h /\ P x
  | Hmul h x y => elems P h /\ P x /\ P y
  | Hmerge h1 h2 => elems P h1 /\ elems P h2
  end.

(* The exact terms, with v the value of an element. *)
Fixpoint terms (v : E -> R) (h : hist E) : list R :=
  match h with
  | Hnil => []
  | Hadd h x => terms v h ++ [v x]
  | Hmul h x y => terms v h ++ [v x * v y]
  | Hmerge h1 h2 => terms v h1 ++ terms v h2
  end.

(* The magnitudes that the kernels add to the running sum of magnitudes, with l the leading
   limb of an element. *)
Fixpoint leads (l : E -> R) (h : hist E) : list R :=
  match h with
  | Hnil => []
  | Hadd h x => leads l h ++ [Rabs (l x)]
  | Hmul h x y => leads l h ++ [Rabs (l x) * Rabs (l y)]
  | Hmerge h1 h2 => leads l h1 ++ leads l h2
  end.

Lemma terms_length : forall (v : E -> R) (h : hist E), length (terms v h) = count h.
Proof.
intros v. induction h as [|h IH x|h IH x y|h1 IH1 h2 IH2]; cbn [terms count];
  rewrite ?length_app; cbn [length]; lia.
Qed.

Lemma count_0_terms : forall (v : E -> R) (h : hist E), count h = O -> terms v h = [].
Proof.
intros v h H. destruct (terms v h) as [|r l] eqn:E0. reflexivity.
generalize (terms_length v h). rewrite E0. cbn [length]. lia.
Qed.

Lemma sumR_leads_ge_0 : forall (l : E -> R) (h : hist E), 0 <= sumR (leads l h).
Proof.
intros l. induction h as [|h IH x|h IH x y|h1 IH1 h2 IH2]; cbn [leads sumR].
- lra.
- rewrite sumR_app. cbn [sumR]. generalize (Rabs_pos (l x)). lra.
- rewrite sumR_app. cbn [sumR].
  generalize (Rmult_le_pos _ _ (Rabs_pos (l x)) (Rabs_pos (l y))). lra.
- rewrite sumR_app. lra.
Qed.

End Histories.

Arguments count {E} h.
Arguments elems {E} P h.
Arguments terms {E} v h.
Arguments leads {E} l h.

(* (1 + u)^n, as a function of a count of terms, from the closed form that a count m >= n
   with m u <= 1/2 gives: (1 + u)^n <= 1 + m u + 2 m^2 u^2. *)
Lemma acc_pow_le_poly :
  forall (uu : R) (n : nat) (m : R), 0 <= uu -> INR n <= m -> m * uu <= / 2 ->
  (1 + uu) ^ n <= 1 + m * uu + 2 * m ^ 2 * uu ^ 2.
Proof.
intros uu n m Hu Hn Hm.
assert (Hm0 : 0 <= m) by (generalize (pos_INR n); lra).
generalize (gamma_le_real uu n m Hu Hn Hm). intros G.
assert (Hx : 0 <= m * uu <= / 2) by (split; [apply Rmult_le_pos | ]; lra).
generalize (div_one_minus_le (m * uu) Hx). intros D.
replace (2 * m ^ 2 * uu ^ 2) with (2 * (m * uu) * (m * uu)) by ring. nra.
Qed.

(** * One limb *)

Section One.
Variable emin prec : Z.
Hypothesis Hp1 : (1 <= prec)%Z.

Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation F := (fmt emin prec).
Notation rnd := (round radix2 (FLT_exp emin prec) (Znearest tie_even)).
Notation uu := (u prec).
Notation ee := (eta emin).
Notation add1 := (add_1_1 emin prec tie_even).
Notation id1 := (fun x : R => x).

(* The state after a history: the running sum and the running sum of magnitudes. *)
Fixpoint run1 (h : hist R) : R * R :=
  match h with
  | Hnil => (0, 0)
  | Hadd h x => let '(s, a) := run1 h in acc_add_1 emin prec tie_even s a x
  | Hmul h x y => let '(s, a) := run1 h in acc_mul_entry_1 emin prec tie_even s a x y
  | Hmerge h1 h2 =>
      let '(s, a) := run1 h1 in let '(v, c) := run1 h2 in acc_merge_1 emin prec tie_even s a v c
  end.

Let u0 : 0 < uu.
Proof. apply bpow_gt_0. Qed.
Let e0 : 0 < ee.
Proof. apply bpow_gt_0. Qed.

Lemma acc_fmt_0 : F 0.
Proof. apply generic_format_0. Qed.

Lemma acc_rnd_id : forall x : R, F x -> RN emin prec x = x.
Proof. intros x Fx. apply round_generic; auto with typeclass_instances. Qed.

(* (A1), with what every state is: a number of the format and a nonnegative one. *)
Theorem acc_1_mags :
  forall h : hist R, elems F h ->
  let '(s, a) := run1 h in
  F s /\ F a /\ 0 <= a /\ (count h = O -> s = 0 /\ a = 0) /\
  sumR (leads id1 h) <= (1 + uu) ^ count h * (a + INR (count h) * (ee / 2)).
Proof.
induction h as [|h IH x|h IH x y|h1 IH1 h2 IH2]; cbn [elems run1 count leads].
- intros _. split. exact acc_fmt_0. split. exact acc_fmt_0. split. lra. split. intros _. lra.
  cbn [sumR pow INR]. lra.
- intros [Vh Fx]. specialize (IH Vh). destruct (run1 h) as [s a].
  destruct IH as [Fs [Fa [Ha [_ IA]]]].
  generalize (acc_add_1_correct emin prec Hp1 s a x Fs Fa Fx Ha).
  destruct (acc_add_1 emin prec tie_even s a x) as [t b].
  intros [Ft [Fb [_ [_ Eb]]]].
  assert (Lb : a + Rabs x <= (1 + uu) * b).
  { rewrite Eb. apply (rnd_sum_lower emin prec). exact Fa. apply generic_format_abs. exact Fx.
    generalize (Rabs_pos x). lra. }
  assert (Hb : 0 <= b).
  { rewrite Eb. apply (rnd_ge_0 emin prec). generalize (Rabs_pos x). lra. }
  split. exact Ft. split. exact Fb. split. exact Hb. split. intros H; discriminate H.
  rewrite sumR_app, S_INR. cbn [sumR].
  set (n := count h) in *. set (p := (1 + uu) ^ n) in *.
  assert (P1 : 1 <= p) by (apply pow_R1_Rle; lra).
  assert (K : p * (a + INR n * (ee / 2)) + Rabs x <= p * (a + Rabs x + INR n * (ee / 2))).
  { generalize (Rabs_pos x). nra. }
  assert (K2 : p * (a + Rabs x + INR n * (ee / 2)) <= p * ((1 + uu) * b + INR n * (ee / 2)))
    by (apply Rmult_le_compat_l; lra).
  assert (N0 : 0 <= INR n * (ee / 2)) by (apply Rmult_le_pos; [apply pos_INR | lra]).
  assert (K3 : p * ((1 + uu) * b + INR n * (ee / 2)) <= (1 + uu) * p * (b + (INR n + 1) * (ee / 2))).
  { assert (0 <= p * (uu * (INR n * (ee / 2)))) by (apply Rmult_le_pos; [lra | apply Rmult_le_pos; lra]).
    assert (0 <= (1 + uu) * p * (ee / 2)) by (apply Rmult_le_pos; [apply Rmult_le_pos | ]; lra).
    nra. }
  simpl pow. fold p. lra.
- intros [Vh [Fx Fy]]. specialize (IH Vh). destruct (run1 h) as [s a].
  destruct IH as [Fs [Fa [Ha [_ IA]]]].
  generalize (acc_mul_entry_1_correct emin prec Hp1 s a x y Fs Fa Fx Fy Ha).
  destruct (acc_mul_entry_1 emin prec tie_even s a x y) as [t b].
  intros [Ft [Fb [_ Eb]]].
  assert (Pxy : 0 <= Rabs x * Rabs y) by (apply Rmult_le_pos; apply Rabs_pos).
  assert (Lb : a + Rabs x * Rabs y <= (1 + uu) * (b + ee / 2)).
  { rewrite Eb. apply (rnd_lower emin prec). lra. }
  assert (Hb : 0 <= b).
  { rewrite Eb. apply (rnd_ge_0 emin prec). lra. }
  split. exact Ft. split. exact Fb. split. exact Hb. split. intros H; discriminate H.
  rewrite sumR_app, S_INR. cbn [sumR].
  set (n := count h) in *. set (p := (1 + uu) ^ n) in *.
  assert (P1 : 1 <= p) by (apply pow_R1_Rle; lra).
  assert (K : p * (a + INR n * (ee / 2)) + Rabs x * Rabs y <=
              p * (a + Rabs x * Rabs y + INR n * (ee / 2))) by nra.
  assert (K2 : p * (a + Rabs x * Rabs y + INR n * (ee / 2)) <=
               p * ((1 + uu) * (b + ee / 2) + INR n * (ee / 2)))
    by (apply Rmult_le_compat_l; lra).
  assert (N0 : 0 <= INR n * (ee / 2)) by (apply Rmult_le_pos; [apply pos_INR | lra]).
  assert (K3 : p * ((1 + uu) * (b + ee / 2) + INR n * (ee / 2)) <=
               (1 + uu) * p * (b + (INR n + 1) * (ee / 2))).
  { assert (0 <= p * (uu * (INR n * (ee / 2)))) by (apply Rmult_le_pos; [lra | apply Rmult_le_pos; lra]).
    nra. }
  simpl pow. fold p. lra.
- intros [V1 V2]. specialize (IH1 V1). specialize (IH2 V2).
  destruct (run1 h1) as [s a]. destruct (run1 h2) as [v c].
  destruct IH1 as [Fs [Fa [Ha [Z1 I1]]]]. destruct IH2 as [Fv [Fc [Hc [Z2 I2]]]].
  generalize (acc_merge_1_correct emin prec Hp1 s a v c Fs Fa Fv Fc Ha Hc).
  destruct (acc_merge_1 emin prec tie_even s a v c) as [t b].
  intros [Ft [Fb [Et [_ Eb]]]].
  assert (Lb : a + c <= (1 + uu) * b).
  { rewrite Eb. apply (rnd_sum_lower emin prec); assumption || lra. }
  assert (Hb : 0 <= b) by (rewrite Eb; apply (rnd_ge_0 emin prec); lra).
  split. exact Ft. split. exact Fb. split. exact Hb.
  rewrite sumR_app.
  set (n1 := count h1) in *. set (n2 := count h2) in *.
  destruct (Nat.eq_dec n1 O) as [N1|N1].
  + destruct (Z1 N1) as [Es Ea]. subst s a.
    assert (Eb2 : b = c) by (rewrite Eb, Rplus_0_l; apply acc_rnd_id; exact Fc).
    assert (Et2 : t = v) by (rewrite Et, Rplus_0_l; apply acc_rnd_id; exact Fv).
    rewrite N1 in I1 |- *. cbn [pow INR] in I1. rewrite Nat.add_0_l.
    split. intros H. destruct (Z2 H) as [E1 E2]. split; congruence.
    rewrite Eb2. lra.
  + destruct (Nat.eq_dec n2 O) as [N2|N2].
    * destruct (Z2 N2) as [Es Ea]. subst v c.
      assert (Eb2 : b = a) by (rewrite Eb, Rplus_0_r; apply acc_rnd_id; exact Fa).
      assert (Et2 : t = s) by (rewrite Et, Rplus_0_r; apply acc_rnd_id; exact Fs).
      rewrite N2 in I2 |- *. cbn [pow INR] in I2. rewrite Nat.add_0_r.
      split. intros H. lia.
      rewrite Eb2. lra.
    * split. intros H. lia.
      set (M := Nat.max n1 n2).
      assert (H1 : 1 <= 1 + uu) by lra.
      assert (P1 : (1 + uu) ^ n1 <= (1 + uu) ^ M) by (apply Rle_pow; [lra | apply Nat.le_max_l]).
      assert (P2 : (1 + uu) ^ n2 <= (1 + uu) ^ M) by (apply Rle_pow; [lra | apply Nat.le_max_r]).
      assert (PM : (1 + uu) * (1 + uu) ^ M <= (1 + uu) ^ (n1 + n2)).
      { rewrite tech_pow_Rmult. apply Rle_pow. lra. unfold M. lia. }
      assert (N10 : 0 <= INR n1 * (ee / 2)) by (apply Rmult_le_pos; [apply pos_INR | lra]).
      assert (N20 : 0 <= INR n2 * (ee / 2)) by (apply Rmult_le_pos; [apply pos_INR | lra]).
      assert (K1 : (1 + uu) ^ n1 * (a + INR n1 * (ee / 2)) <= (1 + uu) ^ M * (a + INR n1 * (ee / 2)))
        by (apply Rmult_le_compat_r; lra).
      assert (K2 : (1 + uu) ^ n2 * (c + INR n2 * (ee / 2)) <= (1 + uu) ^ M * (c + INR n2 * (ee / 2)))
        by (apply Rmult_le_compat_r; lra).
      assert (PM0 : 0 <= (1 + uu) ^ M) by (apply pow_le; lra).
      assert (K3 : (1 + uu) ^ M * (a + c + INR (n1 + n2) * (ee / 2)) <=
                   (1 + uu) ^ M * ((1 + uu) * b + INR (n1 + n2) * (ee / 2)))
        by (apply Rmult_le_compat_l; lra).
      assert (N0 : 0 <= INR (n1 + n2) * (ee / 2)) by (apply Rmult_le_pos; [apply pos_INR | lra]).
      assert (K4 : (1 + uu) ^ M * ((1 + uu) * b + INR (n1 + n2) * (ee / 2)) <=
                   (1 + uu) * (1 + uu) ^ M * (b + INR (n1 + n2) * (ee / 2))).
      { assert (0 <= (1 + uu) ^ M * (uu * (INR (n1 + n2) * (ee / 2))))
          by (apply Rmult_le_pos; [lra | apply Rmult_le_pos; lra]).
        nra. }
      assert (K5 : (1 + uu) * (1 + uu) ^ M * (b + INR (n1 + n2) * (ee / 2)) <=
                   (1 + uu) ^ (n1 + n2) * (b + INR (n1 + n2) * (ee / 2)))
        by (apply Rmult_le_compat_r; [lra | exact PM]).
      rewrite plus_INR in K3, K4, K5 |- *.
      nra.
Qed.

(* The magnitudes the kernels of one limb add are those of the terms. *)
Lemma leads_1 : forall h : hist R, sumR (leads id1 h) = sumabs (terms id1 h).
Proof.
induction h as [|h IH x|h IH x y|h1 IH1 h2 IH2]; cbn [leads terms].
- reflexivity.
- rewrite sumR_app, sumabs_app, IH. unfold sumabs. cbn [map sumR]. lra.
- rewrite sumR_app, sumabs_app, IH. unfold sumabs. cbn [map sumR]. rewrite Rabs_mult. lra.
- rewrite sumR_app, sumabs_app, IH1, IH2. reflexivity.
Qed.

(* The tree of the history: the additions and the fused steps are nodes of add_1_1, the
   zero state a leaf where a product was added to an accumulator with no term. *)
Fixpoint tree1 (h : hist R) : option (tree R) :=
  match h with
  | Hnil => None
  | Hadd h x =>
      Some (match tree1 h with None => Leaf x | Some T => Node T (Leaf x) end)
  | Hmul h x y =>
      Some (Node (match tree1 h with None => Leaf 0 | Some T => T end) (Leaf (x * y)))
  | Hmerge h1 h2 =>
      match tree1 h1, tree1 h2 with
      | None, o => o
      | o, None => o
      | Some T1, Some T2 => Some (Node T1 T2)
      end
  end.

Notation w1 := (weight_1 emin prec).

Lemma acc_w1_0 : w1 0 = 0.
Proof. apply weight_1_fmt. exact Hp1. exact acc_fmt_0. Qed.

Lemma acc_sumabs_one : forall r : R, sumabs [r] = Rabs r.
Proof. intros r. unfold sumabs. cbn [map sumR]. ring. Qed.

(* The state is the value of the tree, whose leaves have the sum and the sum of magnitudes
   of the terms, cost at most n eta / 2, and whose height is at most n. *)
Lemma tree1_facts :
  forall h : hist R, elems F h ->
  match tree1 h with
  | None => fst (run1 h) = 0 /\ count h = O
  | Some T =>
      fst (run1 h) = eval add1 T /\
      sumR (leaves T) = sumR (terms id1 h) /\
      sumabs (leaves T) = sumabs (terms id1 h) /\
      sumR (map w1 (leaves T)) <= INR (count h) * (ee / 2) /\
      (height T <= count h)%nat /\ (1 <= count h)%nat
  end.
Proof.
induction h as [|h IH x|h IH x y|h1 IH1 h2 IH2]; intros V.
- cbn [tree1 run1 count fst]. split; reflexivity.
- cbn [elems] in V. destruct V as [Vh Fx]. specialize (IH Vh).
  generalize (acc_1_mags h Vh). intros M.
  cbn [tree1 run1 terms count].
  destruct (run1 h) as [s a]. destruct M as [Fs [Fa [Ha _]]].
  generalize (acc_add_1_correct emin prec Hp1 s a x Fs Fa Fx Ha).
  destruct (acc_add_1 emin prec tie_even s a x) as [t b]. intros [_ [_ [Et _]]].
  cbn [fst] in IH |- *. rewrite S_INR.
  assert (Wx : w1 x = 0) by (apply weight_1_fmt; assumption).
  destruct (tree1 h) as [T|].
  + destruct IH as [Es [S1 [S2 [W [Hh C1]]]]].
    cbn [eval leaves height]. rewrite map_app, !sumR_app, !sumabs_app, S1, S2.
    split. rewrite Et, Es. reflexivity.
    split. reflexivity. split. reflexivity.
    split. cbn [map sumR]. rewrite Wx. lra.
    split; lia.
  + destruct IH as [Es C0]. rewrite (count_0_terms R id1 h C0), C0.
    cbn [eval leaves height app map sumR INR]. rewrite acc_sumabs_one.
    split. rewrite Et, Es, Rplus_0_l. apply acc_rnd_id. exact Fx.
    split. reflexivity. split. reflexivity.
    split. rewrite Wx. lra.
    split; lia.
- cbn [elems] in V. destruct V as [Vh [Fx Fy]]. specialize (IH Vh).
  generalize (acc_1_mags h Vh). intros M.
  cbn [tree1 run1 terms count].
  destruct (run1 h) as [s a]. destruct M as [Fs [Fa [Ha _]]].
  generalize (acc_mul_entry_1_correct emin prec Hp1 s a x y Fs Fa Fx Fy Ha).
  destruct (acc_mul_entry_1 emin prec tie_even s a x y) as [t b]. intros [_ [_ [Et _]]].
  cbn [fst] in IH |- *. rewrite S_INR.
  generalize (weight_1_bounds emin prec (x * y)). intros Wxy.
  destruct (tree1 h) as [T|].
  + destruct IH as [Es [S1 [S2 [W [Hh C1]]]]].
    cbn [eval leaves height]. rewrite map_app, !sumR_app, !sumabs_app, S1, S2.
    split. rewrite Et, Es. unfold add_1_1, RN. cbv zeta. reflexivity.
    split. reflexivity. split. reflexivity.
    split. cbn [map sumR]. lra.
    split; lia.
  + destruct IH as [Es C0]. rewrite (count_0_terms R id1 h C0), C0.
    cbn [eval leaves height app map sumR INR].
    split. rewrite Et, Es. unfold add_1_1, RN. cbv zeta. reflexivity.
    split. ring. split. unfold sumabs. cbn [map sumR]. rewrite Rabs_R0. ring.
    split. rewrite acc_w1_0. lra.
    split; lia.
- cbn [elems] in V. destruct V as [V1 V2]. specialize (IH1 V1). specialize (IH2 V2).
  generalize (acc_1_mags h1 V1) (acc_1_mags h2 V2). intros M1 M2.
  cbn [tree1 run1 terms count].
  destruct (run1 h1) as [s a]. destruct (run1 h2) as [v c].
  destruct M1 as [Fs [Fa [Ha _]]]. destruct M2 as [Fv [Fc [Hc _]]].
  generalize (acc_merge_1_correct emin prec Hp1 s a v c Fs Fa Fv Fc Ha Hc).
  destruct (acc_merge_1 emin prec tie_even s a v c) as [t b]. intros [_ [_ [Et _]]].
  cbn [fst] in IH1, IH2 |- *. rewrite plus_INR.
  destruct (tree1 h1) as [T1|]; destruct (tree1 h2) as [T2|]; cbv beta iota.
  + destruct IH1 as [E1 [S11 [S12 [W1 [H1 C1]]]]]. destruct IH2 as [E2 [S21 [S22 [W2 [H2 C2]]]]].
    cbn [eval leaves height]. rewrite map_app, !sumR_app, !sumabs_app, S11, S12, S21, S22.
    split. rewrite Et, E1, E2. unfold add_1_1, RN. cbv zeta. reflexivity.
    split. reflexivity. split. reflexivity.
    split. lra.
    split; lia.
  + destruct IH1 as [E1 [S11 [S12 [W1 [H1 C1]]]]]. destruct IH2 as [E2 C2].
    rewrite (count_0_terms R id1 h2 C2), C2, app_nil_r, Nat.add_0_r. cbn [INR].
    split. rewrite Et, E2, Rplus_0_r, <- E1. apply acc_rnd_id. exact Fs.
    split. exact S11. split. exact S12.
    split. lra.
    split; lia.
  + destruct IH1 as [E1 C1]. destruct IH2 as [E2 [S21 [S22 [W2 [H2 C2]]]]].
    rewrite (count_0_terms R id1 h1 C1), C1, app_nil_l, Nat.add_0_l. cbn [INR].
    split. rewrite Et, E1, Rplus_0_l, <- E2. apply acc_rnd_id. exact Fv.
    split. exact S21. split. exact S22.
    split. lra.
    split; lia.
  + destruct IH1 as [E1 C1]. destruct IH2 as [E2 C2].
    split. rewrite Et, E1, E2, Rplus_0_l. apply round_0; auto with typeclass_instances.
    lia.
Qed.

(* (A3) for one limb: the statement of dot_1 for n terms, in any tree of merges. *)
Theorem acc_1_error :
  forall h : hist R, elems F h ->
  Rabs (fst (run1 h) - sumR (terms id1 h)) <=
    ((1 + uu / (1 + uu)) ^ count h - 1) * sumabs (terms id1 h) +
    (1 + uu / (1 + uu)) ^ (count h - 1) * (INR (count h) * (ee / 2)).
Proof.
intros h V. generalize (tree1_facts h V).
set (e := uu / (1 + uu)).
assert (He : 0 <= e) by apply eps_1_ge_0.
assert (H1 : 1 <= 1 + e) by lra.
destruct (tree1 h) as [T|].
- intros [Es [S1 [S2 [W [Hh C1]]]]].
  assert (Hall : Forall (fun _ : R => True) (leaves T)).
  { apply Forall_forall. intros r _. exact I. }
  destruct (tree_sum_weighted R (fun x : R => x) (fun _ : R => True) add1 e w1 He
              (fused_add_weighted emin prec Hp1) T Hall) as [_ [B _]].
  rewrite map_id in B. rewrite <- Es, S1, S2 in B.
  set (n := count h) in *.
  assert (P1 : (1 + e) ^ height T <= (1 + e) ^ n) by (apply Rle_pow; [exact H1 | exact Hh]).
  assert (P2 : (1 + e) ^ (height T - 1) <= (1 + e) ^ (n - 1)) by (apply Rle_pow; [exact H1 | lia]).
  assert (Q : 0 <= (1 + e) ^ (height T - 1)) by (apply pow_le; lra).
  assert (A0 : 0 <= sumabs (terms id1 h)) by apply sumabs_ge_0.
  assert (W0 : 0 <= sumR (map w1 (leaves T))).
  { apply (sumR_map_ge_0 R (fun _ => True)). intros r _. exact (proj1 (weight_1_bounds emin prec r)).
    exact Hall. }
  assert (N0 : 0 <= INR n * (ee / 2)) by (apply Rmult_le_pos; [apply pos_INR | lra]).
  assert (K1 : ((1 + e) ^ height T - 1) * sumabs (terms id1 h) <= ((1 + e) ^ n - 1) * sumabs (terms id1 h))
    by (apply Rmult_le_compat_r; lra).
  assert (K2 : (1 + e) ^ (height T - 1) * sumR (map w1 (leaves T)) <=
               (1 + e) ^ (n - 1) * (INR n * (ee / 2))).
  { apply Rmult_le_compat; assumption. }
  lra.
- intros [Es C0]. rewrite Es, (count_0_terms R id1 h C0), C0.
  cbn [sumR pow INR]. unfold sumabs. cbn [map sumR]. rewrite Rminus_0_r, Rabs_R0. lra.
Qed.

End One.

(** * One limb: the guarantee *)

(* (A3') |s - sum terms| <= g sum |terms| + t <= r. *)
Theorem acc_1_chain :
  forall emin prec : Z, (2 <= prec)%Z -> eta emin <= / 2 ->
  forall h : hist R, elems (fmt emin prec) h ->
  forall m g t r : R, fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (count h) <= m ->
  bound_dot_1 emin prec tie_even m = (g, t, true) ->
  acc_radius_1 emin prec tie_even (snd (run1 emin prec h)) m g t = (r, true) ->
  Rabs (fst (run1 emin prec h) - sumR (terms (fun x => x) h)) <=
    g * sumabs (terms (fun x => x) h) + t /\
  g * sumabs (terms (fun x => x) h) + t <= r.
Proof.
intros emin prec Hp2 Hh h V m g t r Fm Hm Hn Hb Hr.
assert (Hp1 : (1 <= prec)%Z) by lia.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
generalize (bound_dot_1_facts emin prec Hp1 m Fm Hm Hh). rewrite Hb. cbv beta iota.
intros [Fg [Ft [Hg0 Hok]]]. destruct (Hok eq_refl) as [_ [_ Ht]].
assert (Hm0 : 0 <= m) by (destruct Hm; lra).
assert (Ht0 : 0 <= t).
{ apply Rle_trans with (2 := Ht). apply Rmult_le_pos. apply Rmult_le_pos. exact Hm0.
  assert (0 <= eta emin) by (unfold eta; apply bpow_ge_0). lra. lra. }
split.
- apply (dot_1_use emin prec Hp1 Hh m g t (count h)); try assumption.
  apply sumabs_ge_0. apply acc_1_error; assumption.
- generalize (acc_1_mags emin prec Hp1 h V). rewrite leads_1.
  generalize (acc_radius_1_facts emin prec Hp2).
  destruct (run1 emin prec h) as [s a]. cbn [fst snd] in Hr |- *.
  intros R1 [_ [Fa [Ha [_ A1]]]].
  generalize (R1 a m g t Fa Fm Fg Ft Ha Hm Hg0 Ht0). rewrite Hr. intros [_ [Br Mr]].
  specialize (Mr eq_refl).
  set (uu := u prec) in *. set (ee := eta emin) in *.
  set (n := count h) in *. set (A := sumabs (terms (fun x => x) h)) in *.
  assert (U0 : 0 <= uu) by (unfold uu, u; apply bpow_ge_0).
  assert (E0 : 0 <= ee) by (unfold ee, eta; apply bpow_ge_0).
  assert (P : (1 + uu) ^ n <= 1 + m * uu + 2 * m ^ 2 * uu ^ 2) by (apply acc_pow_le_poly; assumption).
  assert (X1 : a + INR n * (ee / 2) <= a + m * ee / 2).
  { assert (K : INR n * (ee / 2) <= m * (ee / 2)) by (apply Rmult_le_compat_r; lra). lra. }
  assert (Pn : 1 <= (1 + uu) ^ n) by (apply pow_R1_Rle; lra).
  assert (X0 : 0 <= a + INR n * (ee / 2)).
  { assert (0 <= INR n * (ee / 2)) by (apply Rmult_le_pos; [apply pos_INR | lra]). lra. }
  assert (K1 : A <= (1 + m * uu + 2 * m ^ 2 * uu ^ 2) * (a + m * ee / 2)).
  { apply Rle_trans with (1 := A1). apply Rmult_le_compat; lra. }
  assert (Q : 1 <= (1 + uu) ^ 2) by (apply pow_R1_Rle; lra).
  assert (A0 : 0 <= A) by (unfold A; apply sumabs_ge_0).
  assert (Q0 : 0 <= (1 + m * uu + 2 * m ^ 2 * uu ^ 2) * (a + m * ee / 2)) by lra.
  assert (K2 : A <= (1 + uu) ^ 2 * ((1 + m * uu + 2 * m ^ 2 * uu ^ 2) * (a + m * ee / 2))).
  { assert (K : 1 * ((1 + m * uu + 2 * m ^ 2 * uu ^ 2) * (a + m * ee / 2)) <=
                (1 + uu) ^ 2 * ((1 + m * uu + 2 * m ^ 2 * uu ^ 2) * (a + m * ee / 2)))
      by (apply Rmult_le_compat_r; lra).
    lra. }
  assert (K3 : g * A <= g * ((1 + uu) ^ 2 * ((1 + m * uu + 2 * m ^ 2 * uu ^ 2) * (a + m * ee / 2))))
    by (apply Rmult_le_compat_l; assumption).
  replace (g * (1 + uu) ^ 2 * (1 + m * uu + 2 * m ^ 2 * uu ^ 2) * (a + m * ee / 2))
    with (g * ((1 + uu) ^ 2 * ((1 + m * uu + 2 * m ^ 2 * uu ^ 2) * (a + m * ee / 2)))) in Br by ring.
  lra.
Qed.

(* What a user of an accumulator of one limb relies on: after any history of add,
   add_product and merge on numbers of the format, the radius of error_bound() bounds the
   error of the running sum against the exact sum of the terms. *)
Theorem acc_1_bound :
  forall emin prec : Z, (2 <= prec)%Z -> eta emin <= / 2 ->
  forall h : hist R, elems (fmt emin prec) h ->
  forall m g t r : R, fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (count h) <= m ->
  bound_dot_1 emin prec tie_even m = (g, t, true) ->
  acc_radius_1 emin prec tie_even (snd (run1 emin prec h)) m g t = (r, true) ->
  Rabs (fst (run1 emin prec h) - sumR (terms (fun x => x) h)) <= r.
Proof.
intros emin prec Hp2 Hh h V m g t r Fm Hm Hn Hb Hr.
destruct (acc_1_chain emin prec Hp2 Hh h V m g t r Fm Hm Hn Hb Hr) as [K1 K2]. lra.
Qed.

(** * Two limbs *)

Section Two.
Variable emin prec : Z.
Hypothesis Hp4 : (4 <= prec)%Z.

Let Hp3 : (3 <= prec)%Z.
Proof. lia. Qed.
Let Hp1 : (1 <= prec)%Z.
Proof. lia. Qed.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation F := (fmt emin prec).
Notation N2 := (norm2 emin prec).
Notation rnd := (round radix2 (FLT_exp emin prec) (Znearest tie_even)).
Notation uu := (u prec).
Notation ee := (eta emin).

(* The state after a history: the running pair and the running sum of magnitudes. *)
Fixpoint run2 (h : hist (R * R)) : R * R * R :=
  match h with
  | Hnil => (0, 0, 0)
  | Hadd h x =>
      let '(s0, s1, a) := run2 h in acc_add_2 emin prec tie_even s0 s1 a (fst x) (snd x)
  | Hmul h x y =>
      let '(s0, s1, a) := run2 h in
      acc_mul_2 emin prec tie_even s0 s1 a (fst x) (snd x) (fst y) (snd y)
  | Hmerge h1 h2 =>
      let '(s0, s1, a) := run2 h1 in let '(v0, v1, c) := run2 h2 in
      acc_merge_2 emin prec tie_even s0 s1 a v0 v1 c
  end.

Let u0 : 0 < uu.
Proof. apply bpow_gt_0. Qed.
Let e0 : 0 < ee.
Proof. apply bpow_gt_0. Qed.

Lemma acc_fmt_0_2 : F 0.
Proof. apply generic_format_0. Qed.

(* The kernels of the model, as functions of the pairs. *)
Lemma acc_add_2_eq :
  forall s0 s1 a x0 x1 : R, F x0 -> F x1 ->
  acc_add_2 emin prec tie_even s0 s1 a x0 x1 =
  (fst (add_2_2 emin prec tie_even s0 s1 x0 x1), snd (add_2_2 emin prec tie_even s0 s1 x0 x1),
   RN emin prec (a + Rabs x0)).
Proof.
intros s0 s1 a x0 x1 acc_fmt_0 F1. unfold acc_add_2. cbv zeta.
rewrite (guard_real_any emin prec tie_even x0 acc_fmt_0), (guard_real_any emin prec tie_even x1 F1).
destruct (add_2_2 emin prec tie_even s0 s1 x0 x1). reflexivity.
Qed.

Lemma acc_mul_2_eq :
  forall s0 s1 a x0 x1 y0 y1 : R,
  acc_mul_2 emin prec tie_even s0 s1 a x0 x1 y0 y1 =
  (fst (add22 emin prec (s0, s1) (mul22 emin prec (x0, x1) (y0, y1))),
   snd (add22 emin prec (s0, s1) (mul22 emin prec (x0, x1) (y0, y1))),
   RN emin prec (a + Rabs x0 * Rabs y0)).
Proof.
intros. unfold acc_mul_2, Model.dot_step_2, add22, mul22. cbv zeta. cbn [fst snd].
destruct (mul_2_2 emin prec tie_even x0 x1 y0 y1) as [p0 p1]. cbn [fst snd].
destruct (add_2_2 emin prec tie_even s0 s1 p0 p1) as [t0 t1]. unfold RN. cbn [fst snd].
rewrite (Rplus_comm a (Rabs x0 * Rabs y0)). reflexivity.
Qed.

Lemma acc_merge_2_eq :
  forall s0 s1 a v0 v1 c : R,
  acc_merge_2 emin prec tie_even s0 s1 a v0 v1 c =
  (fst (add_2_2 emin prec tie_even s0 s1 v0 v1), snd (add_2_2 emin prec tie_even s0 s1 v0 v1),
   RN emin prec (a + c)).
Proof.
intros. unfold acc_merge_2. cbv zeta. destruct (add_2_2 emin prec tie_even s0 s1 v0 v1).
reflexivity.
Qed.

Lemma acc_rnd_id_2 : forall x : R, F x -> RN emin prec x = x.
Proof. intros x Fx. apply round_generic; auto with typeclass_instances. Qed.

Lemma acc_norm2_fmt : forall x : R * R, N2 x -> F (fst x) /\ F (snd x).
Proof. intros x [A [B _]]. split; assumption. Qed.

(* (A1) for two limbs, with what every state is: a normalized pair, and a nonnegative
   number of the format for the sum of magnitudes. *)
Theorem acc_2_mags :
  forall h : hist (R * R), elems N2 h ->
  let '(s0, s1, a) := run2 h in
  normalized_2 emin prec s0 s1 /\ F a /\ 0 <= a /\
  (count h = O -> s0 = 0 /\ s1 = 0 /\ a = 0) /\
  sumR (leads fst h) <= (1 + uu) ^ count h * (a + INR (count h) * (ee / 2)).
Proof.
induction h as [|h IH x|h IH x y|h1 IH1 h2 IH2]; cbn [elems run2 count leads].
- intros _. split. exact (zero_pair_normalized emin prec).
  split. exact acc_fmt_0_2. split. lra. split. intros _. lra.
  cbn [sumR pow INR]. lra.
- intros [Vh Nx]. specialize (IH Vh). destruct (run2 h) as [[s0 s1] a].
  destruct IH as [Ns [Fa [Ha [_ IA]]]].
  destruct x as [x0 x1]. cbn [fst snd] in *.
  generalize (acc_add_2_correct emin prec Hp3 s0 s1 a x0 x1 Ns Fa Nx Ha).
  destruct (acc_add_2 emin prec tie_even s0 s1 a x0 x1) as [[t0 t1] b].
  intros [Fb [Nt [_ Eb]]].
  destruct Nx as [Fx0 [Fx1 _]].
  assert (Lb : a + Rabs x0 <= (1 + uu) * b).
  { rewrite Eb. apply (rnd_sum_lower emin prec). exact Fa. apply generic_format_abs. exact Fx0.
    generalize (Rabs_pos x0). lra. }
  assert (Hb : 0 <= b).
  { rewrite Eb. apply (rnd_ge_0 emin prec). generalize (Rabs_pos x0). lra. }
  split. exact Nt. split. exact Fb. split. exact Hb. split. intros H; discriminate H.
  rewrite sumR_app, S_INR. cbn [sumR].
  set (n := count h) in *. set (p := (1 + uu) ^ n) in *.
  assert (P1 : 1 <= p) by (apply pow_R1_Rle; lra).
  assert (K : p * (a + INR n * (ee / 2)) + Rabs x0 <= p * (a + Rabs x0 + INR n * (ee / 2))).
  { generalize (Rabs_pos x0). nra. }
  assert (K2 : p * (a + Rabs x0 + INR n * (ee / 2)) <= p * ((1 + uu) * b + INR n * (ee / 2)))
    by (apply Rmult_le_compat_l; lra).
  assert (N0 : 0 <= INR n * (ee / 2)) by (apply Rmult_le_pos; [apply pos_INR | lra]).
  assert (K3 : p * ((1 + uu) * b + INR n * (ee / 2)) <= (1 + uu) * p * (b + (INR n + 1) * (ee / 2))).
  { assert (0 <= p * (uu * (INR n * (ee / 2)))) by (apply Rmult_le_pos; [lra | apply Rmult_le_pos; lra]).
    assert (0 <= (1 + uu) * p * (ee / 2)) by (apply Rmult_le_pos; [apply Rmult_le_pos | ]; lra).
    nra. }
  simpl pow. fold p. lra.
- intros [Vh [Nx Ny]]. specialize (IH Vh). destruct (run2 h) as [[s0 s1] a].
  destruct IH as [Ns [Fa [Ha [_ IA]]]].
  destruct x as [x0 x1]. destruct y as [y0 y1]. cbn [fst snd] in *.
  generalize (acc_mul_2_correct emin prec Hp4 s0 s1 a x0 x1 y0 y1 Ns Fa Nx Ny Ha).
  destruct (acc_mul_2 emin prec tie_even s0 s1 a x0 x1 y0 y1) as [[t0 t1] b].
  intros [Fb [Nt [_ Eb]]].
  assert (Pxy : 0 <= Rabs x0 * Rabs y0) by (apply Rmult_le_pos; apply Rabs_pos).
  assert (Lb : a + Rabs x0 * Rabs y0 <= (1 + uu) * (b + ee / 2)).
  { rewrite Eb. apply (rnd_lower emin prec). lra. }
  assert (Hb : 0 <= b).
  { rewrite Eb. apply (rnd_ge_0 emin prec). lra. }
  split. exact Nt. split. exact Fb. split. exact Hb. split. intros H; discriminate H.
  rewrite sumR_app, S_INR. cbn [sumR].
  set (n := count h) in *. set (p := (1 + uu) ^ n) in *.
  assert (P1 : 1 <= p) by (apply pow_R1_Rle; lra).
  assert (K : p * (a + INR n * (ee / 2)) + Rabs x0 * Rabs y0 <=
              p * (a + Rabs x0 * Rabs y0 + INR n * (ee / 2))) by nra.
  assert (K2 : p * (a + Rabs x0 * Rabs y0 + INR n * (ee / 2)) <=
               p * ((1 + uu) * (b + ee / 2) + INR n * (ee / 2)))
    by (apply Rmult_le_compat_l; lra).
  assert (N0 : 0 <= INR n * (ee / 2)) by (apply Rmult_le_pos; [apply pos_INR | lra]).
  assert (K3 : p * ((1 + uu) * (b + ee / 2) + INR n * (ee / 2)) <=
               (1 + uu) * p * (b + (INR n + 1) * (ee / 2))).
  { assert (0 <= p * (uu * (INR n * (ee / 2)))) by (apply Rmult_le_pos; [lra | apply Rmult_le_pos; lra]).
    nra. }
  simpl pow. fold p. lra.
- intros [V1 V2]. specialize (IH1 V1). specialize (IH2 V2).
  destruct (run2 h1) as [[s0 s1] a]. destruct (run2 h2) as [[v0 v1] c].
  destruct IH1 as [Ns [Fa [Ha [Z1 I1]]]]. destruct IH2 as [Nv [Fc [Hc [Z2 I2]]]].
  generalize (acc_merge_2_correct emin prec Hp3 s0 s1 a v0 v1 c Ns Fa Nv Fc Ha Hc).
  rewrite (acc_merge_2_eq s0 s1 a v0 v1 c). intros [Fb [Nt [_ Eb]]].
  set (b := RN emin prec (a + c)) in *.
  assert (Lb : a + c <= (1 + uu) * b).
  { unfold b. apply (rnd_sum_lower emin prec); assumption || lra. }
  assert (Hb : 0 <= b) by (unfold b; apply (rnd_ge_0 emin prec); lra).
  split. exact Nt. split. exact Fb. split. exact Hb.
  rewrite sumR_app.
  set (n1 := count h1) in *. set (n2 := count h2) in *.
  destruct (Nat.eq_dec n1 O) as [N1|N1].
  + destruct (Z1 N1) as [E0 [E1 Ea]]. subst s0 s1 a.
    assert (Eb2 : b = c) by (unfold b; rewrite Rplus_0_l; apply acc_rnd_id_2; exact Fc).
    rewrite N1 in I1 |- *. cbn [pow INR] in I1. rewrite Nat.add_0_l.
    split.
    * intros H. destruct (Z2 H) as [E2 [E3 E4]]. subst v0 v1.
      rewrite (add_2_2_zero_l emin prec 0 0 (zero_pair_normalized emin prec)). cbn [fst snd].
      split. reflexivity. split. reflexivity. rewrite Eb2. exact E4.
    * rewrite Eb2. lra.
  + destruct (Nat.eq_dec n2 O) as [N2|N2].
    * destruct (Z2 N2) as [E0 [E1 Ea]]. subst v0 v1 c.
      assert (Eb2 : b = a) by (unfold b; rewrite Rplus_0_r; apply acc_rnd_id_2; exact Fa).
      rewrite N2 in I2 |- *. cbn [pow INR] in I2. rewrite Nat.add_0_r.
      split. intros H. lia.
      rewrite Eb2. lra.
    * split. intros H. lia.
      set (M := Nat.max n1 n2).
      assert (P1 : (1 + uu) ^ n1 <= (1 + uu) ^ M) by (apply Rle_pow; [lra | apply Nat.le_max_l]).
      assert (P2 : (1 + uu) ^ n2 <= (1 + uu) ^ M) by (apply Rle_pow; [lra | apply Nat.le_max_r]).
      assert (PM : (1 + uu) * (1 + uu) ^ M <= (1 + uu) ^ (n1 + n2)).
      { rewrite tech_pow_Rmult. apply Rle_pow. lra. unfold M. lia. }
      assert (N10 : 0 <= INR n1 * (ee / 2)) by (apply Rmult_le_pos; [apply pos_INR | lra]).
      assert (N20 : 0 <= INR n2 * (ee / 2)) by (apply Rmult_le_pos; [apply pos_INR | lra]).
      assert (K1 : (1 + uu) ^ n1 * (a + INR n1 * (ee / 2)) <= (1 + uu) ^ M * (a + INR n1 * (ee / 2)))
        by (apply Rmult_le_compat_r; lra).
      assert (K2 : (1 + uu) ^ n2 * (c + INR n2 * (ee / 2)) <= (1 + uu) ^ M * (c + INR n2 * (ee / 2)))
        by (apply Rmult_le_compat_r; lra).
      assert (PM0 : 0 <= (1 + uu) ^ M) by (apply pow_le; lra).
      assert (K3 : (1 + uu) ^ M * (a + c + INR (n1 + n2) * (ee / 2)) <=
                   (1 + uu) ^ M * ((1 + uu) * b + INR (n1 + n2) * (ee / 2)))
        by (apply Rmult_le_compat_l; lra).
      assert (N0 : 0 <= INR (n1 + n2) * (ee / 2)) by (apply Rmult_le_pos; [apply pos_INR | lra]).
      assert (K4 : (1 + uu) ^ M * ((1 + uu) * b + INR (n1 + n2) * (ee / 2)) <=
                   (1 + uu) * (1 + uu) ^ M * (b + INR (n1 + n2) * (ee / 2))).
      { assert (0 <= (1 + uu) ^ M * (uu * (INR (n1 + n2) * (ee / 2))))
          by (apply Rmult_le_pos; [lra | apply Rmult_le_pos; lra]).
        nra. }
      assert (K5 : (1 + uu) * (1 + uu) ^ M * (b + INR (n1 + n2) * (ee / 2)) <=
                   (1 + uu) ^ (n1 + n2) * (b + INR (n1 + n2) * (ee / 2)))
        by (apply Rmult_le_compat_r; [lra | exact PM]).
      rewrite plus_INR in K3, K4, K5 |- *.
      nra.
Qed.

(* The exact terms, from the leading limbs: |x| <= (1 + u) |x0| for a normalized pair. *)
Lemma acc_2_terms_leads :
  forall h : hist (R * R), elems N2 h ->
  sumabs (terms val2 h) <= (1 + uu) ^ 2 * sumR (leads fst h).
Proof.
assert (Q1 : 1 <= 1 + uu) by lra.
induction h as [|h IH x|h IH x y|h1 IH1 h2 IH2]; cbn [elems terms leads].
- intros _. unfold sumabs. cbn [map sumR]. lra.
- intros [Vh Nx]. specialize (IH Vh). rewrite sumabs_app, sumR_app, acc_sumabs_one. cbn [sumR].
  destruct x as [x0 x1]. cbn [fst snd] in *. change (val2 (x0, x1)) with (x0 + x1).
  generalize (normalized_2_abs_le emin prec x0 x1 Nx). intros A.
  assert (K : (1 + uu) * Rabs x0 <= (1 + uu) ^ 2 * Rabs x0).
  { apply Rmult_le_compat_r. apply Rabs_pos. replace ((1 + uu) ^ 2) with ((1 + uu) * (1 + uu)) by ring.
    nra. }
  rewrite Rplus_0_r, Rmult_plus_distr_l. lra.
- intros [Vh [Nx Ny]]. specialize (IH Vh). rewrite sumabs_app, sumR_app, acc_sumabs_one. cbn [sumR].
  destruct x as [x0 x1]. destruct y as [y0 y1]. cbn [fst snd] in *.
  change (val2 (x0, x1)) with (x0 + x1). change (val2 (y0, y1)) with (y0 + y1).
  generalize (normalized_2_abs_le emin prec x0 x1 Nx) (normalized_2_abs_le emin prec y0 y1 Ny).
  intros A B. rewrite Rabs_mult.
  assert (K : Rabs (x0 + x1) * Rabs (y0 + y1) <= ((1 + uu) * Rabs x0) * ((1 + uu) * Rabs y0))
    by (apply Rmult_le_compat; try apply Rabs_pos; assumption).
  replace (((1 + uu) * Rabs x0) * ((1 + uu) * Rabs y0)) with ((1 + uu) ^ 2 * (Rabs x0 * Rabs y0))
    in K by ring.
  rewrite Rplus_0_r, Rmult_plus_distr_l. lra.
- intros [V1 V2]. rewrite sumabs_app, sumR_app. specialize (IH1 V1). specialize (IH2 V2). rewrite Rmult_plus_distr_l. lra.
Qed.

(* The inequality of the design page: sum |x_i y_i| <= (1 + u)^(n+2) (a + n eta / 2). *)
Theorem acc_2_terms_mags :
  forall h : hist (R * R), elems N2 h ->
  sumabs (terms val2 h) <= (1 + uu) ^ (count h + 2) * (snd (run2 h) + INR (count h) * (ee / 2)).
Proof.
intros h V. generalize (acc_2_terms_leads h V) (acc_2_mags h V).
destruct (run2 h) as [[s0 s1] a]. cbn [snd]. intros L [_ [_ [Ha [_ A1]]]].
rewrite pow_add.
assert (Q : 0 <= (1 + uu) ^ 2) by (apply pow_le; lra).
assert (K : (1 + uu) ^ 2 * sumR (leads fst h) <=
            (1 + uu) ^ 2 * ((1 + uu) ^ count h * (a + INR (count h) * (ee / 2))))
  by (apply Rmult_le_compat_l; assumption).
replace ((1 + uu) ^ count h * (1 + uu) ^ 2 * (a + INR (count h) * (ee / 2)))
  with ((1 + uu) ^ 2 * ((1 + uu) ^ count h * (a + INR (count h) * (ee / 2)))) by ring.
lra.
Qed.

(* The tree of the history: the additions are nodes of add_2_2, its leaves the elements
   added and the products mul_2_2 (x, y). *)
Fixpoint tree2 (h : hist (R * R)) : option (tree (R * R)) :=
  match h with
  | Hnil => None
  | Hadd h x =>
      Some (match tree2 h with None => Leaf x | Some T => Node T (Leaf x) end)
  | Hmul h x y =>
      Some (match tree2 h with
            | None => Leaf (mul22 emin prec x y)
            | Some T => Node T (Leaf (mul22 emin prec x y))
            end)
  | Hmerge h1 h2 =>
      match tree2 h1, tree2 h2 with
      | None, o => o
      | o, None => o
      | Some T1, Some T2 => Some (Node T1 T2)
      end
  end.

Notation approx := (fun p r => Rabs (val2 p - r) <= 4 * uu ^ 2 * Rabs r + 3 / 2 * ee).

Lemma acc_approx_exact : forall x : R * R, approx x (val2 x).
Proof.
intros x. cbv beta. rewrite Rminus_diag, Rabs_R0.
assert (0 <= 4 * uu ^ 2 * Rabs (val2 x)).
{ apply Rmult_le_pos. apply Rmult_le_pos. lra. apply pow_le; lra. apply Rabs_pos. }
lra.
Qed.

Lemma acc_pair_eta : forall p : R * R, (fst p, snd p) = p.
Proof. intros [a b]. reflexivity. Qed.

(* The running pair is the value of the tree, whose leaves are normalized and approximate
   the terms. *)
Lemma tree2_facts :
  forall h : hist (R * R), elems N2 h ->
  match tree2 h with
  | None => fst (run2 h) = (0, 0) /\ count h = O
  | Some T =>
      fst (run2 h) = eval (add22 emin prec) T /\
      Forall N2 (leaves T) /\ Forall2 approx (leaves T) (terms val2 h)
  end.
Proof.
induction h as [|h IH x|h IH x y|h1 IH1 h2 IH2]; intros V.
- cbn [tree2 run2 count fst]. split; reflexivity.
- cbn [elems] in V. destruct V as [Vh Nx]. specialize (IH Vh).
  generalize (acc_2_mags h Vh). intros M.
  cbn [tree2 run2 terms count].
  destruct (run2 h) as [[s0 s1] a]. destruct M as [Ns _].
  destruct (acc_norm2_fmt x Nx) as [Fx0 Fx1].
  rewrite (acc_add_2_eq s0 s1 a (fst x) (snd x) Fx0 Fx1). cbn [fst] in IH |- *.
  rewrite acc_pair_eta.
  destruct (tree2 h) as [T|].
  + destruct IH as [Es [L A]].
    cbn [eval leaves]. split. rewrite <- Es. reflexivity.
    split. apply Forall_app. split. exact L. constructor. exact Nx. constructor.
    apply Forall2_app. exact A. constructor. apply acc_approx_exact. constructor.
  + destruct IH as [Es C0]. injection Es. intros E1 E0. subst s0 s1.
    rewrite (count_0_terms (R * R) val2 h C0).
    cbn [eval leaves app].
    split. destruct x as [x0 x1]. exact (add_2_2_zero_l emin prec x0 x1 Nx).
    split. constructor. exact Nx. constructor.
    constructor. apply acc_approx_exact. constructor.
- cbn [elems] in V. destruct V as [Vh [Nx Ny]]. specialize (IH Vh).
  generalize (acc_2_mags h Vh). intros M.
  cbn [tree2 run2 terms count].
  destruct (run2 h) as [[s0 s1] a]. destruct M as [Ns _].
  rewrite (acc_mul_2_eq s0 s1 a (fst x) (snd x) (fst y) (snd y)). cbn [fst] in IH |- *.
  rewrite acc_pair_eta, (acc_pair_eta x), (acc_pair_eta y).
  destruct (mul_2_2_leaf emin prec Hp4 x y Nx Ny) as [Np Ap].
  destruct (tree2 h) as [T|].
  + destruct IH as [Es [L A]].
    cbn [eval leaves]. split. rewrite <- Es. reflexivity.
    split. apply Forall_app. split. exact L. constructor. exact Np. constructor.
    apply Forall2_app. exact A. constructor. exact Ap. constructor.
  + destruct IH as [Es C0]. injection Es. intros E1 E0. subst s0 s1.
    rewrite (count_0_terms (R * R) val2 h C0).
    cbn [eval leaves app].
    split. unfold add22. cbn [fst snd]. destruct (mul22 emin prec x y) as [p0 p1].
      exact (add_2_2_zero_l emin prec p0 p1 Np).
    split. constructor. exact Np. constructor.
    constructor. exact Ap. constructor.
- cbn [elems] in V. destruct V as [V1 V2]. specialize (IH1 V1). specialize (IH2 V2).
  generalize (acc_2_mags h1 V1) (acc_2_mags h2 V2). intros M1 M2.
  cbn [tree2 run2 terms count].
  destruct (run2 h1) as [[s0 s1] a]. destruct (run2 h2) as [[v0 v1] c].
  destruct M1 as [Ns _]. destruct M2 as [Nv _].
  rewrite (acc_merge_2_eq s0 s1 a v0 v1 c). cbn [fst] in IH1, IH2 |- *.
  rewrite acc_pair_eta.
  destruct (tree2 h1) as [T1|]; destruct (tree2 h2) as [T2|]; cbv beta iota.
  + destruct IH1 as [E1 [L1 A1]]. destruct IH2 as [E2 [L2 A2]].
    cbn [eval leaves]. split. rewrite <- E1, <- E2. reflexivity.
    split. apply Forall_app. split; assumption.
    apply Forall2_app; assumption.
  + destruct IH1 as [E1 [L1 A1]]. destruct IH2 as [E2 C2]. injection E2. intros F1 acc_fmt_0.
    subst v0 v1. rewrite (count_0_terms (R * R) val2 h2 C2), app_nil_r.
    split. rewrite <- E1. exact (add_2_2_zero_r emin prec s0 s1 Ns).
    split; assumption.
  + destruct IH1 as [E1 C1]. destruct IH2 as [E2 [L2 A2]]. injection E1. intros F1 acc_fmt_0.
    subst s0 s1. rewrite (count_0_terms (R * R) val2 h1 C1), app_nil_l.
    split. rewrite <- E2. exact (add_2_2_zero_l emin prec v0 v1 Nv).
    split; assumption.
  + destruct IH1 as [E1 C1]. destruct IH2 as [E2 C2].
    injection E1. intros F1 acc_fmt_0. injection E2. intros G1 G0. subst s0 s1 v0 v1.
    split. exact (add_2_2_zero_l emin prec 0 0 (zero_pair_normalized emin prec)).
    lia.
Qed.

(* (A3) for two limbs: the statement of dot_2 for n terms, in any tree of merges. *)
Theorem acc_2_error :
  forall h : hist (R * R), elems N2 h ->
  Rabs (val2 (fst (run2 h)) - sumR (terms val2 h)) <=
    ((1 + 4 * uu ^ 2) * (1 + 3 * uu ^ 2 / (1 - 4 * uu)) ^ (count h - 1) - 1) *
      sumabs (terms val2 h) +
    (1 + 3 * uu ^ 2 / (1 - 4 * uu)) ^ (count h - 1) * (INR (count h) * (3 / 2 * ee)).
Proof.
intros h V. generalize (tree2_facts h V).
set (e := 3 * uu ^ 2 / (1 - 4 * uu)).
assert (He : 0 <= e) by (apply eps_add_2_ge_0; exact Hp3).
assert (H1 : 1 <= 1 + e) by lra.
assert (Hx : 0 <= 4 * uu ^ 2) by (apply Rmult_le_pos; [lra | apply pow_le; lra]).
destruct (tree2 h) as [T|].
- intros [Es [L A]].
  generalize (tree_sum_approx (R * R) val2 N2 (add22 emin prec) e (4 * uu ^ 2) (3 / 2 * ee) He
                (add_2_2_adds emin prec Hp3) T (terms val2 h) L A).
  rewrite <- Es, (terms_length (R * R) val2 h). intros B.
  set (n := count h) in *.
  assert (Hh : (height T <= n - 1)%nat).
  { generalize (height_le_leaves (R * R) T). rewrite (Forall2_length A).
    rewrite (terms_length (R * R) val2 h). fold n. lia. }
  assert (P1 : (1 + e) ^ height T <= (1 + e) ^ (n - 1)) by (apply Rle_pow; [exact H1 | exact Hh]).
  assert (A0 : 0 <= sumabs (terms val2 h)) by apply sumabs_ge_0.
  assert (N0 : 0 <= INR n * (3 / 2 * ee)) by (apply Rmult_le_pos; [apply pos_INR | lra]).
  assert (K1 : ((1 + 4 * uu ^ 2) * (1 + e) ^ height T - 1) * sumabs (terms val2 h) <=
               ((1 + 4 * uu ^ 2) * (1 + e) ^ (n - 1) - 1) * sumabs (terms val2 h)).
  { apply Rmult_le_compat_r. exact A0.
    assert (K : (1 + 4 * uu ^ 2) * (1 + e) ^ height T <= (1 + 4 * uu ^ 2) * (1 + e) ^ (n - 1))
      by (apply Rmult_le_compat_l; lra).
    lra. }
  assert (K2 : (1 + e) ^ height T * (INR n * (3 / 2 * ee)) <= (1 + e) ^ (n - 1) * (INR n * (3 / 2 * ee)))
    by (apply Rmult_le_compat_r; assumption).
  lra.
- intros [Es C0]. rewrite Es, (count_0_terms (R * R) val2 h C0), C0.
  unfold val2. cbn [fst snd sumR pow INR]. unfold sumabs. cbn [map sumR].
  replace (0 + 0 - 0) with 0 by ring. rewrite Rabs_R0. lra.
Qed.

End Two.

(** * Two limbs: the guarantee *)

(* (A3') |s - sum terms| <= g sum |terms| + t <= r. *)
Theorem acc_2_chain :
  forall emin prec : Z, (4 <= prec)%Z -> eta emin <= / 2 ->
  forall h : hist (R * R), elems (norm2 emin prec) h ->
  forall m g t r : R, fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (count h) <= m ->
  bound_dot_2 emin prec tie_even m = (g, t, true) ->
  acc_radius_2 emin prec tie_even (snd (run2 emin prec h)) m g t = (r, true) ->
  Rabs (val2 (fst (run2 emin prec h)) - sumR (terms val2 h)) <= g * sumabs (terms val2 h) + t /\
  g * sumabs (terms val2 h) + t <= r.
Proof.
intros emin prec Hp4 Hh h V m g t r Fm Hm Hn Hb Hr.
assert (Hp2 : (2 <= prec)%Z) by lia.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 4%Z; lia).
generalize (bound_dot_2_facts emin prec Hp4 m Fm Hm Hh). rewrite Hb. cbv beta iota.
intros [Fg [Ft [Hg0 Hok]]]. destruct (Hok eq_refl) as [_ [_ Ht]].
assert (Hm0 : 0 <= m) by (destruct Hm; lra).
assert (Ht0 : 0 <= t).
{ apply Rle_trans with (2 := Ht). apply Rmult_le_pos. apply Rmult_le_pos. exact Hm0.
  assert (0 <= eta emin) by (unfold eta; apply bpow_ge_0). lra. lra. }
split.
- apply (dot_2_use emin prec Hp4 Hh m g t (count h)); try assumption.
  + apply sumabs_ge_0.
  + intros C0. rewrite (count_0_terms (R * R) val2 h C0). reflexivity.
  + apply acc_2_error; assumption.
- generalize (acc_2_terms_mags emin prec Hp4 h V) (acc_2_mags emin prec Hp4 h V).
  unfold acc_radius_2 in Hr.
  generalize (acc_radius_1_facts emin prec Hp2).
  destruct (run2 emin prec h) as [[s0 s1] a]. cbn [fst snd] in Hr |- *.
  intros R1 A1 [_ [Fa [Ha _]]].
  generalize (R1 a m g t Fa Fm Fg Ft Ha Hm Hg0 Ht0).
  destruct (acc_radius_1 emin prec tie_even a m g t) as [r' ok']. injection Hr. intros E1 E2.
  subst r' ok'. intros [_ [Br Mr]].
  specialize (Mr eq_refl).
  set (uu := u prec) in *. set (ee := eta emin) in *.
  set (n := count h) in *. set (A := sumabs (terms val2 h)) in *.
  assert (U0 : 0 <= uu) by (unfold uu, u; apply bpow_ge_0).
  assert (E0 : 0 <= ee) by (unfold ee, eta; apply bpow_ge_0).
  assert (P : (1 + uu) ^ n <= 1 + m * uu + 2 * m ^ 2 * uu ^ 2) by (apply acc_pow_le_poly; assumption).
  assert (X1 : a + INR n * (ee / 2) <= a + m * ee / 2).
  { assert (K : INR n * (ee / 2) <= m * (ee / 2)) by (apply Rmult_le_compat_r; lra). lra. }
  assert (Pn : 1 <= (1 + uu) ^ n) by (apply pow_R1_Rle; lra).
  assert (X0 : 0 <= a + INR n * (ee / 2)).
  { assert (0 <= INR n * (ee / 2)) by (apply Rmult_le_pos; [apply pos_INR | lra]). lra. }
  rewrite pow_add in A1.
  assert (Q0 : 0 <= (1 + uu) ^ 2) by (apply pow_le; lra).
  assert (K1 : (1 + uu) ^ n * (a + INR n * (ee / 2)) <=
               (1 + m * uu + 2 * m ^ 2 * uu ^ 2) * (a + m * ee / 2))
    by (apply Rmult_le_compat; lra).
  assert (K2 : A <= (1 + uu) ^ 2 * ((1 + m * uu + 2 * m ^ 2 * uu ^ 2) * (a + m * ee / 2))).
  { replace ((1 + uu) ^ n * (1 + uu) ^ 2 * (a + INR n * (ee / 2)))
      with ((1 + uu) ^ 2 * ((1 + uu) ^ n * (a + INR n * (ee / 2)))) in A1 by ring.
    assert (K : (1 + uu) ^ 2 * ((1 + uu) ^ n * (a + INR n * (ee / 2))) <=
                (1 + uu) ^ 2 * ((1 + m * uu + 2 * m ^ 2 * uu ^ 2) * (a + m * ee / 2)))
      by (apply Rmult_le_compat_l; assumption).
    lra. }
  assert (K3 : g * A <= g * ((1 + uu) ^ 2 * ((1 + m * uu + 2 * m ^ 2 * uu ^ 2) * (a + m * ee / 2))))
    by (apply Rmult_le_compat_l; assumption).
  replace (g * (1 + uu) ^ 2 * (1 + m * uu + 2 * m ^ 2 * uu ^ 2) * (a + m * ee / 2))
    with (g * ((1 + uu) ^ 2 * ((1 + m * uu + 2 * m ^ 2 * uu ^ 2) * (a + m * ee / 2)))) in Br by ring.
  lra.
Qed.

(* What a user of an accumulator of two limbs relies on: after any history of add,
   add_product and merge on normalized pairs, the radius of error_bound() bounds the error
   of the running pair against the exact sum of the terms. *)
Theorem acc_2_bound :
  forall emin prec : Z, (4 <= prec)%Z -> eta emin <= / 2 ->
  forall h : hist (R * R), elems (norm2 emin prec) h ->
  forall m g t r : R, fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (count h) <= m ->
  bound_dot_2 emin prec tie_even m = (g, t, true) ->
  acc_radius_2 emin prec tie_even (snd (run2 emin prec h)) m g t = (r, true) ->
  Rabs (val2 (fst (run2 emin prec h)) - sumR (terms val2 h)) <= r.
Proof.
intros emin prec Hp4 Hh h V m g t r Fm Hm Hn Hb Hr.
destruct (acc_2_chain emin prec Hp4 Hh h V m g t r Fm Hm Hn Hb Hr) as [K1 K2]. lra.
Qed.
