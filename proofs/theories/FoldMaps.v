(* The maps: the generated statements of the eighteen loops that write an array
   (proofs/gen/FoldStatements.v), add_k, sub_k, axpy_k, axpy_2_1 and their _entry
   forms, scale_k and mul_pow2_map_k.

   proofs/gen/FoldModel.v states every map F as F_map xs = map F_step xs, the list of
   the elements written for the list xs of the elements read (one entry of every array
   read), with F_step the model of the step's kernel applied to the scalars and to the
   limbs of one element. The generated statement F_spec says, for every list whose
   elements satisfy the map's requirements (and scalars that satisfy theirs), entry by
   entry (Forall2), what the statement of the step concludes: the element written is
   valid and within the step's bound of the exact value for its own element.

   Each theorem here, F_correct : F_spec, is the theorem of the step on every element,
   through map_entries of Folds.v. The steps are proved in MapSteps.v, and add_1_1,
   add_2_2 and sub_2_2, the steps of add_1, add_2 and sub_2, in OneLimb.v, Add22.v and
   Sign.v.

   The description of each map names this file (theorem:, status: proved), and the
   generated audit (proofs/gen/Audit.v) checks F_correct against F_spec: a map has one
   statement, without an order, where a fold has one per order.

   What these statements do not say, because the real model of a map has none of it:
   - No order. A map of the library runs in the sequential order and in the lane order,
     and both are the one function map here: that an element written depends on its own
     element and on the scalars only is how the model is written, not a theorem.
   - No mask. The map returns the and of a test of every element written (its leading
     limb is finite) and, when that is false, rewrites the elements that are not finite
     as NaN. In the real model nothing overflows and every element is a number of the
     format, so there is nothing to state; what the mask means is a statement of the
     IEEE model, which is not generated yet.
   - No array. The model is a function from a list to a list. That the loop may write
     over one of the arrays it reads (in place) is a property of the generated C++, in
     which every element is read whole before it is written; nothing here is about
     it. *)
From Stdlib Require Import Reals ZArith List.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements FoldModel FoldStatements.
From Kairn Require Import Folds OneLimb Add22 Sign MapSteps.
Open Scope R_scope.

(** * Sums and differences *)

Theorem add_1_correct : add_1_spec.
Proof.
intros emin prec Hp xys H. unfold add_1_map. revert H. apply map_entries.
intros [a b] [Fa Fb].
exact (add_1_1_correct emin prec Hp a b Fa Fb).
Qed.

Theorem add_1_entry_correct : add_1_entry_spec.
Proof.
intros emin prec Hp xys H. unfold add_1_entry_map. revert H. apply map_entries.
intros [x y] [Fx Fy].
exact (add_entry_step_1_correct emin prec Hp x y Fx Fy).
Qed.

Theorem add_2_correct : add_2_spec.
Proof.
intros emin prec Hp xys H. unfold add_2_map. revert H. apply map_entries.
intros [[x0 x1] [y0 y1]] [Nx Ny].
exact (add_2_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
Qed.

Theorem add_2_entry_correct : add_2_entry_spec.
Proof.
intros emin prec Hp xys H. unfold add_2_entry_map. revert H. apply map_entries.
intros [[x0 x1] [y0 y1]] [Nx Ny].
exact (add_entry_step_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
Qed.

Theorem sub_1_correct : sub_1_spec.
Proof.
intros emin prec Hp xys H. unfold sub_1_map. revert H. apply map_entries.
intros [a b] [Fa Fb].
exact (sub_1_1_correct emin prec Hp a b Fa Fb).
Qed.

Theorem sub_1_entry_correct : sub_1_entry_spec.
Proof.
intros emin prec Hp xys H. unfold sub_1_entry_map. revert H. apply map_entries.
intros [x y] [Fx Fy].
exact (sub_entry_step_1_correct emin prec Hp x y Fx Fy).
Qed.

Theorem sub_2_correct : sub_2_spec.
Proof.
intros emin prec Hp xys H. unfold sub_2_map. revert H. apply map_entries.
intros [[x0 x1] [y0 y1]] [Nx Ny].
exact (sub_2_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
Qed.

Theorem sub_2_entry_correct : sub_2_entry_spec.
Proof.
intros emin prec Hp xys H. unfold sub_2_entry_map. revert H. apply map_entries.
intros [[x0 x1] [y0 y1]] [Nx Ny].
exact (sub_entry_step_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
Qed.

(** * axpy *)

Theorem axpy_1_correct : axpy_1_spec.
Proof.
intros emin prec Hp a xys Fa H. unfold axpy_1_map. revert H. apply map_entries.
intros [x y] [Fx Fy].
exact (axpy_step_1_correct emin prec Hp a x y Fa Fx Fy).
Qed.

Theorem axpy_1_entry_correct : axpy_1_entry_spec.
Proof.
intros emin prec Hp a xys Fa H. unfold axpy_1_entry_map. revert H. apply map_entries.
intros [x y] [Fx Fy].
exact (axpy_entry_step_1_correct emin prec Hp a x y Fa Fx Fy).
Qed.

Theorem axpy_2_correct : axpy_2_spec.
Proof.
intros emin prec Hp a0 a1 xys Na H. unfold axpy_2_map. revert H. apply map_entries.
intros [[x0 x1] [y0 y1]] [Nx Ny].
exact (axpy_step_2_correct emin prec Hp a0 a1 x0 x1 y0 y1 Na Nx Ny).
Qed.

Theorem axpy_2_entry_correct : axpy_2_entry_spec.
Proof.
intros emin prec Hp a0 a1 xys Na H. unfold axpy_2_entry_map. revert H. apply map_entries.
intros [[x0 x1] [y0 y1]] [Nx Ny].
exact (axpy_entry_step_2_correct emin prec Hp a0 a1 x0 x1 y0 y1 Na Nx Ny).
Qed.

Theorem axpy_2_1_correct : axpy_2_1_spec.
Proof.
intros emin prec Hp a xys Fa H. unfold axpy_2_1_map. revert H. apply map_entries.
intros [[x0 x1] [y0 y1]] [Nx Ny].
exact (axpy_step_2_1_correct emin prec Hp a x0 x1 y0 y1 Fa Nx Ny).
Qed.

Theorem axpy_2_1_entry_correct : axpy_2_1_entry_spec.
Proof.
intros emin prec Hp a xys Fa H. unfold axpy_2_1_entry_map. revert H. apply map_entries.
intros [[x0 x1] [y0 y1]] [Nx Ny].
exact (axpy_entry_step_2_1_correct emin prec Hp a x0 x1 y0 y1 Fa Nx Ny).
Qed.

(** * Scalings *)

Theorem scale_1_correct : scale_1_spec.
Proof.
intros emin prec Hp a xs Fa H. unfold scale_1_map. revert H. apply map_entries.
intros x Fx.
exact (scale_step_1_correct emin prec Hp x a Fx Fa).
Qed.

Theorem scale_2_correct : scale_2_spec.
Proof.
intros emin prec Hp a xs Fa H. unfold scale_2_map. revert H. apply map_entries.
intros [x0 x1] Nx.
exact (scale_step_2_correct emin prec Hp x0 x1 a Nx Fa).
Qed.

Theorem mul_pow2_map_1_correct : mul_pow2_map_1_spec.
Proof.
intros emin prec Hp c xs Fc Hc H. unfold mul_pow2_map_1_map. revert H. apply map_entries.
intros x Fx.
exact (mul_pow2_step_1_correct emin prec Hp x c Fx Fc Hc).
Qed.

Theorem mul_pow2_map_2_correct : mul_pow2_map_2_spec.
Proof.
intros emin prec Hp c xs Fc Hc H. unfold mul_pow2_map_2_map. revert H. apply map_entries.
intros [x0 x1] Nx.
exact (mul_pow2_step_2_correct emin prec Hp x0 x1 c Nx Fc Hc).
Qed.
