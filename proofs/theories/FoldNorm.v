(* The folds of maxima in the real model: the largest magnitude of an array.

   norm_upper_1 and norm_upper_2 (docs/developer/architecture.md, "Folds of maxima") go
   through an array with a state of two parts, a number m, the largest magnitude so far,
   from 0, and a mask, from true. This file proves the generated statements of their
   kernels (proofs/gen/Statements.v),

       norm_combine_correct    the combination: the larger of two numbers
       norm_step_1_correct     the step of one limb: the larger of m and |x|
       norm_step_2_correct     the step of two limbs: the larger of m and |x0|

   and of the folds in both orders (proofs/gen/FoldStatements.v), the lane order for
   every number of lanes,

       norm_upper_1_seq_correct, norm_upper_1_lanes_correct
       norm_upper_2_seq_correct, norm_upper_2_lanes_correct.

   What the statements say. With V the largest magnitude of the elements, 0 for no
   element, and r the result the finish computes from the final state:
   - one limb: r is m, and  V <= r <= RU (V). Since V is one of the elements or 0, a
     number of the format, RU (V) is V: the result is the largest magnitude itself.
   - two limbs: an element is a normalized pair (x0, x1) of exact value x0 + x1, V is the
     largest |x0 + x1|, and r is succ (m), the number of the format next above the
     largest |x0|; and  V <= r <= succ (RU (V)): the result is at least the magnitude of
     every element, and at most one step above the smallest number of the format that is.

   How.
   - The combination is the maximum of real numbers on the first part and the and of
     the masks (maxc below), and the step is the combination of the state with a pair
     made of the element alone, (|x|, true) or (|x0|, true). A maximum and an and are
     associative and commutative on all states, and the zero state combined with itself
     is itself, so the lane order returns the state of the sequential order
     (fold_lanes_aci of Folds.v, with every state in the set): norm_upper_k_lanes_seq.
     The statements of the lane order are those of the sequential order.
   - The sequential order from (0, true) ends in (the largest of 0 and the |x| or |x0|,
     true): norm_upper_k_seq_value.
   - Two limbs. A normalized pair lies strictly between the neighbors of its leading
     limb (normalized_2_between of Convert.v), so |x0 + x1| < succ (|x0|), and succ is
     monotone: every element is below succ of the largest |x0|. Conversely x0 is
     RN (x0 + x1), and rounding to nearest does not cross a number of the format
     (abs_round_le_generic): |x0 + x1| <= V <= RU (V) gives |x0| <= RU (V), so the
     largest |x0| is at most RU (V) and its successor at most succ (RU (V)).

   What the statements do not say.
   - Nothing of the mask. In the real model no element is a NaN and the mask of the
     final state is true (norm_upper_k_seq_value); what it means is a statement of the
     IEEE model (IeeeFoldNorm.v).
   - That the two orders return the same state, which is more than the same bounds:
     norm_upper_k_lanes_seq.
   - What the result of two limbs is exactly: the successor of the largest |x0|, which
     is RU (V) or succ (RU (V)) (norm_upper_2_seq_value with the bounds). Both happen:
     for one element (x0, x1) with x0 > 0, it is RU (V) when x1 > 0 and succ (RU (V))
     when x1 <= 0. The result is never V itself, even when every x1 is 0: the first
     bound is strict (norm_upper_2_strict). *)
From Stdlib Require Import Reals ZArith List Lia Lra Bool.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements FoldModel FoldStatements.
From Kairn Require Import Format Convert Folds.
Import ListNotations.
Open Scope R_scope.

(** * The kernels *)

(* The selection after the comparison is the maximum. *)
Lemma lt_select_max : forall m n : R, (if Rlt_bool m n then n else m) = Rmax m n.
Proof.
intros m n. unfold Rmax.
destruct (Rlt_bool_spec m n) as [H|H]; destruct (Rle_dec m n) as [L|L]; lra.
Qed.

Lemma Rmax_fmt :
  forall (emin prec : Z) (m n : R),
  fmt emin prec m -> fmt emin prec n -> fmt emin prec (Rmax m n).
Proof. intros emin prec m n Fm Fn. unfold Rmax. destruct (Rle_dec m n); assumption. Qed.

Theorem norm_combine_correct : norm_combine_spec.
Proof.
intros emin prec Hp m n ok okn Fm Fn. unfold norm_combine. cbv beta iota zeta.
rewrite lt_select_max. split. now apply Rmax_fmt. reflexivity.
Qed.

Theorem norm_step_1_correct : norm_step_1_spec.
Proof.
intros emin prec Hp m x ok Fm Fx. unfold norm_step_1, norm_combine. cbv beta iota zeta.
rewrite lt_select_max. split; [|reflexivity].
apply Rmax_fmt. exact Fm. unfold fmt in *. now apply generic_format_abs.
Qed.

Theorem norm_step_2_correct : norm_step_2_spec.
Proof.
intros emin prec Hp m x0 x1 ok Fm [F0 _].
unfold norm_step_2, norm_step_1, norm_combine. cbv beta iota zeta.
rewrite lt_select_max. split; [|reflexivity].
apply Rmax_fmt. exact Fm. unfold fmt in *. now apply generic_format_abs.
Qed.

(** * The largest of 0 and the elements of a list *)

(* The generated statements write the largest magnitude as fold_right Rmax 0 of the list
   of the magnitudes: 0 for the empty list. *)
Local Notation maxl l := (fold_right Rmax 0 l).

Lemma maxl_nonneg : forall l : list R, 0 <= maxl l.
Proof.
induction l as [|a l IH]; cbn [fold_right].
- apply Rle_refl.
- apply Rle_trans with (1 := IH). apply Rmax_r.
Qed.

Lemma maxl_ge : forall (l : list R) (a : R), In a l -> a <= maxl l.
Proof.
induction l as [|b l IH]; intros a H; cbn [fold_right].
- destruct H.
- destruct H as [E|H].
  + rewrite E. apply Rmax_l.
  + apply Rle_trans with (1 := IH a H). apply Rmax_r.
Qed.

Lemma maxl_le :
  forall (l : list R) (b : R), 0 <= b -> Forall (fun a => a <= b) l -> maxl l <= b.
Proof.
intros l b Hb H. induction H as [|a l Ha _ IH]; cbn [fold_right].
- exact Hb.
- now apply Rmax_lub.
Qed.

Lemma maxl_lt :
  forall (l : list R) (b : R), 0 < b -> Forall (fun a => a < b) l -> maxl l < b.
Proof.
intros l b Hb H. induction H as [|a l Ha _ IH]; cbn [fold_right].
- exact Hb.
- now apply Rmax_lub_lt.
Qed.

Lemma maxl_fmt :
  forall (emin prec : Z) (l : list R), Forall (fmt emin prec) l -> fmt emin prec (maxl l).
Proof.
intros emin prec l H. induction H as [|a l Fa _ IH]; cbn [fold_right].
- apply generic_format_0.
- now apply Rmax_fmt.
Qed.

(** * The combination, on states *)

(* The maximum of the numbers and the and of the masks. *)
Definition maxc (a b : R * bool) : R * bool :=
  (Rmax (fst a) (fst b), andb (snd a) (snd b)).

Lemma maxc_comm : forall a b : R * bool, maxc a b = maxc b a.
Proof. intros a b. unfold maxc. now rewrite Rmax_comm, andb_comm. Qed.

Lemma maxc_assoc : forall a b c : R * bool, maxc (maxc a b) c = maxc a (maxc b c).
Proof.
intros a b c. unfold maxc. cbn [fst snd]. f_equal.
- symmetry. apply Rmax_assoc.
- symmetry. apply andb_assoc.
Qed.

Lemma maxc_zero : maxc (0, true) (0, true) = (0, true).
Proof. unfold maxc. cbn [fst snd andb]. now rewrite Rmax_left by apply Rle_refl. Qed.

(* A step that is the combination of the state with a pair made of the element: the lane
   order returns the state of the sequential order. *)
Lemma maxc_lanes_seq :
  forall (B : Type) (step : R * bool -> B -> R * bool)
         (combine : R * bool -> R * bool -> R * bool) (g : B -> R * bool),
  (forall (s : R * bool) (x : B), step s x = maxc s (g x)) ->
  (forall a b : R * bool, combine a b = maxc a b) ->
  forall (W : nat) (xs : list B),
  fold_lanes step combine (0, true) W xs = fold_seq step (0, true) xs.
Proof.
intros B step combine g Hs Hc W xs.
rewrite (fold_lanes_ext _ _ step (fun s x => maxc s (g x)) combine maxc (0, true) Hs Hc W xs).
rewrite (fold_seq_ext _ _ step (fun s x => maxc s (g x)) (0, true) Hs xs).
apply (fold_lanes_aci (R * bool) B (fun _ => True) maxc g (0, true)).
- exact I.
- intros a b _ _. exact I.
- intros a b _ _. apply maxc_comm.
- intros a b c _ _ _. apply maxc_assoc.
- exact maxc_zero.
- apply Forall_forall. intros x _. exact I.
Qed.

(* The sequential order of such a step, when the pair is (h x, true): the largest of the
   state and the h x, and the mask of the state. *)
Lemma maxc_fold_left :
  forall (B : Type) (step : R * bool -> B -> R * bool) (h : B -> R),
  (forall (s : R * bool) (x : B), step s x = maxc s (h x, true)) ->
  forall (xs : list B) (m : R) (ok : bool), 0 <= m ->
  fold_left step xs (m, ok) = (Rmax m (maxl (map h xs)), ok).
Proof.
intros B step h Hs. induction xs as [|x r IH]; intros m ok Hm; cbn [fold_left map fold_right].
- now rewrite Rmax_left by exact Hm.
- rewrite Hs. change (maxc (m, ok) (h x, true)) with (Rmax m (h x), andb ok true).
  rewrite andb_true_r, IH by (apply Rle_trans with (1 := Hm); apply Rmax_l).
  now rewrite <- Rmax_assoc.
Qed.

Lemma maxc_seq_value :
  forall (B : Type) (step : R * bool -> B -> R * bool) (h : B -> R),
  (forall (s : R * bool) (x : B), step s x = maxc s (h x, true)) ->
  forall xs : list B, fold_seq step (0, true) xs = (maxl (map h xs), true).
Proof.
intros B step h Hs xs. unfold fold_seq.
rewrite (maxc_fold_left B step h Hs xs 0 true (Rle_refl 0)).
now rewrite Rmax_right by apply maxl_nonneg.
Qed.

(** * The generated steps and combinations *)

Lemma norm_upper_1_combine_eq :
  forall a b : R * bool, norm_upper_1_combine a b = maxc a b.
Proof.
intros a b. unfold norm_upper_1_combine, norm_combine, maxc. cbv beta iota zeta.
now rewrite lt_select_max.
Qed.

Lemma norm_upper_1_step_eq :
  forall (s : R * bool) (x : R), norm_upper_1_step s x = maxc s (Rabs x, true).
Proof.
intros s x. unfold norm_upper_1_step, norm_step_1, norm_combine, maxc.
cbv beta iota zeta. cbn [fst snd].
now rewrite lt_select_max, (Req_bool_true _ _ (eq_refl (Rabs x))).
Qed.

Lemma norm_upper_2_combine_eq :
  forall a b : R * bool, norm_upper_2_combine a b = maxc a b.
Proof.
intros a b. unfold norm_upper_2_combine, norm_combine, maxc. cbv beta iota zeta.
now rewrite lt_select_max.
Qed.

Lemma norm_upper_2_step_eq :
  forall (s : R * bool) (x : R * R), norm_upper_2_step s x = maxc s (Rabs (fst x), true).
Proof.
intros s x. unfold norm_upper_2_step, norm_step_2, norm_step_1, norm_combine, maxc.
cbv beta iota zeta. cbn [fst snd].
now rewrite lt_select_max, (Req_bool_true _ _ (eq_refl (Rabs (fst x)))).
Qed.

(** * The two orders return the same state, and what it is *)

Theorem norm_upper_1_lanes_seq :
  forall (W : nat) (xs : list R), norm_upper_1_lanes W xs = norm_upper_1_seq xs.
Proof.
intros W xs. unfold norm_upper_1_lanes, norm_upper_1_seq.
exact (maxc_lanes_seq R norm_upper_1_step norm_upper_1_combine (fun x => (Rabs x, true))
         norm_upper_1_step_eq norm_upper_1_combine_eq W xs).
Qed.

Theorem norm_upper_2_lanes_seq :
  forall (W : nat) (xs : list (R * R)), norm_upper_2_lanes W xs = norm_upper_2_seq xs.
Proof.
intros W xs. unfold norm_upper_2_lanes, norm_upper_2_seq.
exact (maxc_lanes_seq (R * R) norm_upper_2_step norm_upper_2_combine
         (fun x => (Rabs (fst x), true)) norm_upper_2_step_eq norm_upper_2_combine_eq W xs).
Qed.

(* The final state: the largest magnitude (of the leading limbs, for two limbs), and the
   mask true. *)
Theorem norm_upper_1_seq_value :
  forall xs : list R, norm_upper_1_seq xs = (maxl (map (fun x => Rabs x) xs), true).
Proof.
intros xs. unfold norm_upper_1_seq.
exact (maxc_seq_value R norm_upper_1_step (fun x => Rabs x) norm_upper_1_step_eq xs).
Qed.

Theorem norm_upper_2_seq_value :
  forall xs : list (R * R),
  norm_upper_2_seq xs = (maxl (map (fun x => Rabs (fst x)) xs), true).
Proof.
intros xs. unfold norm_upper_2_seq.
exact (maxc_seq_value (R * R) norm_upper_2_step (fun x => Rabs (fst x)) norm_upper_2_step_eq xs).
Qed.

(** * A normalized pair and its leading limb *)

Section Pair.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).

(* The step to the next number of the format is monotone (Flocq's succ_le). *)
Lemma succ_mono :
  forall a b : R, format a -> format b -> a <= b -> succ radix2 fexp a <= succ radix2 fexp b.
Proof. intros a b Fa Fb H. apply succ_le; auto with typeclass_instances. Qed.

(* The magnitude of a normalized pair is below the successor of the magnitude of its
   leading limb. *)
Lemma normalized_2_abs_lt_succ :
  forall x0 x1 : R, normalized_2 emin prec x0 x1 ->
  Rabs (x0 + x1) < succ radix2 fexp (Rabs x0).
Proof.
intros x0 x1 Hn.
destruct (normalized_2_between emin prec x0 x1 Hn) as [B1 B2].
assert (F0 : format x0) by apply Hn.
apply Rabs_def1.
- apply Rlt_le_trans with (1 := B2).
  apply succ_mono. exact F0. now apply generic_format_abs. apply Rle_abs.
- apply Rle_lt_trans with (2 := B1). unfold pred. apply Ropp_le_contravar.
  apply succ_mono. now apply generic_format_opp. now apply generic_format_abs.
  rewrite <- Rabs_Ropp. apply Rle_abs.
Qed.

(* A number of the format that is at least the magnitude of a normalized pair is at
   least the magnitude of its leading limb. *)
Lemma normalized_2_lead_le :
  forall x0 x1 b : R, normalized_2 emin prec x0 x1 -> format b ->
  Rabs (x0 + x1) <= b -> Rabs x0 <= b.
Proof.
intros x0 x1 b [_ [_ E]] Fb H. rewrite E. unfold RN.
apply abs_round_le_generic; auto with typeclass_instances.
Qed.

(* The bound of the fold of two limbs, on the largest magnitudes: with m the largest
   |x0| and v the largest |x0 + x1|, succ (m) is a number of the format, at least v and
   at most succ (RU (v)). *)
Lemma norm_upper_2_bound :
  forall xs : list (R * R),
  Forall (fun x => normalized_2 emin prec (fst x) (snd x)) xs ->
  let m := maxl (map (fun x => Rabs (fst x)) xs) in
  let v := maxl (map (fun x => Rabs (fst x + snd x)) xs) in
  format m /\ v <= succ radix2 fexp m /\ m <= RU emin prec v.
Proof.
intros xs Hx m v.
assert (Fm : format m).
{ apply (maxl_fmt emin prec). apply Forall_map. revert Hx. apply Forall_impl.
  intros x [F0 _]. unfold fmt in *. now apply generic_format_abs. }
assert (Hm : 0 <= m) by apply maxl_nonneg.
assert (Hv : 0 <= v) by apply maxl_nonneg.
assert (Fu : format (RU emin prec v)).
{ apply generic_format_round; auto with typeclass_instances. }
assert (Hu : v <= RU emin prec v).
{ destruct (round_UP_pt radix2 fexp v) as [_ [H _]]. exact H. }
split. exact Fm. split.
- apply maxl_le.
  + apply Rle_trans with (1 := Hm). apply succ_ge_id.
  + apply Forall_map. apply Forall_forall. intros x Hin.
    pose proof (proj1 (Forall_forall _ xs) Hx x Hin) as Nx.
    apply Rle_trans with (succ radix2 fexp (Rabs (fst x))).
    * apply Rlt_le. now apply normalized_2_abs_lt_succ.
    * apply succ_mono.
      -- apply generic_format_abs. apply Nx.
      -- exact Fm.
      -- apply maxl_ge. exact (in_map (fun x => Rabs (fst x)) xs x Hin).
- apply maxl_le.
  + now apply Rle_trans with (1 := Hv).
  + apply Forall_map. apply Forall_forall. intros x Hin.
    pose proof (proj1 (Forall_forall _ xs) Hx x Hin) as Nx.
    apply (normalized_2_lead_le (fst x) (snd x) (RU emin prec v) Nx Fu).
    apply Rle_trans with (2 := Hu).
    apply maxl_ge. exact (in_map (fun x => Rabs (fst x + snd x)) xs x Hin).
Qed.

(* The first bound is strict: the successor of the largest |x0| is above the magnitude of
   every element, so the result of two limbs is never the largest magnitude itself. *)
Lemma norm_upper_2_strict :
  forall xs : list (R * R),
  Forall (fun x => normalized_2 emin prec (fst x) (snd x)) xs ->
  maxl (map (fun x => Rabs (fst x + snd x)) xs) <
  succ radix2 fexp (maxl (map (fun x => Rabs (fst x)) xs)).
Proof.
intros xs Hx.
destruct (norm_upper_2_bound xs Hx) as [Fm _].
apply maxl_lt.
- apply Rle_lt_trans with (1 := maxl_nonneg (map (fun x : R * R => Rabs (fst x)) xs)).
  exact (succ_FLT_gt emin prec _).
- apply Forall_map. apply Forall_forall. intros x Hin.
  pose proof (proj1 (Forall_forall _ xs) Hx x Hin) as Nx.
  apply Rlt_le_trans with (succ radix2 fexp (Rabs (fst x))).
  + now apply normalized_2_abs_lt_succ.
  + apply succ_mono.
    * apply generic_format_abs. apply Nx.
    * exact Fm.
    * apply maxl_ge. exact (in_map (fun x => Rabs (fst x)) xs x Hin).
Qed.

End Pair.

(** * The generated statements of the folds *)

Theorem norm_upper_1_seq_correct : norm_upper_1_seq_spec.
Proof.
intros emin prec Hp xs Hx. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
rewrite norm_upper_1_seq_value. cbn [fst].
assert (Fv : fmt emin prec (maxl (map (fun x => Rabs x) xs))).
{ apply maxl_fmt. apply Forall_map. revert Hx. apply Forall_impl.
  intros x Fx. unfold fmt in *. now apply generic_format_abs. }
split. exact Fv. split. apply Rle_refl.
unfold RU. rewrite round_generic; auto with typeclass_instances. apply Rle_refl.
Qed.

Theorem norm_upper_1_lanes_correct : norm_upper_1_lanes_spec.
Proof.
intros emin prec Hp W xs Hx. rewrite norm_upper_1_lanes_seq.
exact (norm_upper_1_seq_correct emin prec Hp xs Hx).
Qed.

Theorem norm_upper_2_seq_correct : norm_upper_2_seq_spec.
Proof.
intros emin prec Hp xs Hx. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
rewrite norm_upper_2_seq_value. cbn [fst].
destruct (norm_upper_2_bound emin prec xs Hx) as [Fm [H1 H2]].
split.
- apply generic_format_succ; auto with typeclass_instances.
- split. exact H1.
  apply (succ_mono emin prec). exact Fm.
  apply generic_format_round; auto with typeclass_instances. exact H2.
Qed.

Theorem norm_upper_2_lanes_correct : norm_upper_2_lanes_spec.
Proof.
intros emin prec Hp W xs Hx. rewrite norm_upper_2_lanes_seq.
exact (norm_upper_2_seq_correct emin prec Hp xs Hx).
Qed.
