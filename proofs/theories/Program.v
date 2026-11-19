(* Straight-line programs: a kernel as a list of instructions.

   A kernel of the generator is a straight-line program: a sequence of operations, each
   of which defines one new value from values defined before it. Here such a program is
   data: a list of instructions whose operands are positions in the list of all values
   (the inputs first, then one value per instruction, in order).

   The same program can be run with any meaning of "one operation": over the real
   numbers with one rounding per operation (the model of proofs/gen/Model.v), or over
   IEEE 754 numbers with infinities and NaN (the IEEE model). Statements that relate the
   two models are then proved once, for every program, by induction on the list
   (IeeeBridge.v), instead of once per kernel.

   This file has no arithmetic in it. It contains:
   - the instructions, and running a program for a given meaning of the operations;
   - which values a given value depends on (its cone), computed backwards through the
     program, and the check that the cone of one value covers a whole program. This is
     the generator's rule "every value reaches output limb 0", in a form that Rocq
     evaluates. *)
From Stdlib Require Import List Arith Bool Lia.
Import ListNotations.

(** * Instructions *)

(* The operands are positions in the list of values. Each instruction is one rounding,
   except Ineg, which is exact.
     Iadd a b     RN(a + b)
     Isub a b     RN(a - b)
     Ineg a       - a
     Ifma a b c   RN(a b + c)
     Ifms a b c   RN(a b - c)
     Iprod a b    RN(a b), computed as a fused multiply-add with addend +0
     Iguard a     RN(a + 0): the guard of a value that enters from the program (rule R3) *)
Inductive instr : Set :=
  | Iadd (a b : nat)
  | Isub (a b : nat)
  | Ineg (a : nat)
  | Ifma (a b c : nat)
  | Ifms (a b c : nat)
  | Iprod (a b : nat)
  | Iguard (a : nat).

Definition operands (i : instr) : list nat :=
  match i with
  | Iadd a b | Isub a b | Iprod a b => [a; b]
  | Ineg a | Iguard a => [a]
  | Ifma a b c | Ifms a b c => [a; b; c]
  end.

(** * Running a program *)

Section Run.
Variable T : Type.
(* The meaning of one instruction, given the values defined so far. *)
Variable step : list T -> instr -> T.

(* The list of all values: the inputs e, then the value of each instruction. *)
Fixpoint run (p : list instr) (e : list T) : list T :=
  match p with
  | [] => e
  | i :: q => run q (e ++ [step e i])
  end.

Lemma run_app : forall p q e, run (p ++ q) e = run q (run p e).
Proof. induction p as [|i p IH]; intros q e; simpl; auto. Qed.

(* Running a program only appends values. *)
Lemma run_prefix : forall p e, exists t, run p e = e ++ t /\ length t = length p.
Proof.
induction p as [|i p IH]; intros e; simpl.
- exists []. split. now rewrite app_nil_r. reflexivity.
- destruct (IH (e ++ [step e i])) as [t [Ht Hl]].
  exists (step e i :: t). split.
  + rewrite Ht, <- app_assoc. reflexivity.
  + simpl. now rewrite Hl.
Qed.

Lemma run_length : forall p e, length (run p e) = length e + length p.
Proof.
intros p e. destruct (run_prefix p e) as [t [Ht Hl]].
now rewrite Ht, length_app, Hl.
Qed.

Lemma run_nth_old : forall p e k d, k < length e -> nth k (run p e) d = nth k e d.
Proof.
intros p e k d Hk. destruct (run_prefix p e) as [t [Ht _]].
rewrite Ht. now apply app_nth1.
Qed.

(* The value of the first instruction is at the position that follows the inputs. *)
Lemma run_nth_new : forall i q e d, nth (length e) (run (i :: q) e) d = step e i.
Proof.
intros i q e d. simpl. rewrite run_nth_old.
- apply nth_middle.
- rewrite length_app. simpl. lia.
Qed.

Lemma run_Forall_prefix : forall (P : T -> Prop) p e, Forall P (run p e) -> Forall P e.
Proof.
intros P p e H. destruct (run_prefix p e) as [t [Ht _]].
rewrite Ht in H. now apply Forall_app in H.
Qed.

End Run.

Arguments run {T} step p e.

(** * The cone of a value *)

(* A program is well formed after n inputs: every operand is defined before its use. *)
Fixpoint wf (p : list instr) (n : nat) : bool :=
  match p with
  | [] => true
  | i :: q => forallb (fun a => a <? n) (operands i) && wf q (S n)
  end.

Definition mem (k : nat) (s : list nat) : bool := existsb (Nat.eqb k) s.

Lemma mem_In : forall k s, mem k s = true <-> In k s.
Proof.
intros k s. unfold mem. rewrite existsb_exists. split.
- intros [x [Hx E]]. apply Nat.eqb_eq in E. now subst.
- intros H. exists k. split. exact H. apply Nat.eqb_refl.
Qed.

(* cone p n s: the positions that the positions in s depend on, in the program p whose
   first instruction defines position n. The program is read from its last instruction
   to its first: if the value of an instruction is in the set, its operands join it. *)
Fixpoint cone (p : list instr) (n : nat) (s : list nat) : list nat :=
  match p with
  | [] => s
  | i :: q => let s' := cone q (S n) s in
              if mem n s' then operands i ++ s' else s'
  end.

(* Every value defined by p is in the cone of position z. *)
Definition covers (p : list instr) (n : nat) (z : nat) : bool :=
  let c := cone p n [z] in forallb (fun k => mem k c) (seq n (length p)).

Lemma wf_app : forall p q n, wf (p ++ q) n = wf p n && wf q (n + length p).
Proof.
induction p as [|i p IH]; intros q n; simpl.
- now rewrite Nat.add_0_r.
- rewrite IH, <- andb_assoc. now rewrite Nat.add_succ_r.
Qed.
