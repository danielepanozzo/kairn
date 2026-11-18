(* Negative control for the audit: a theorem that is false and "proved" with Admitted. *)
From Stdlib Require Import Reals.
Open Scope R_scope.
Theorem wrong : forall x : R, x + 1 = x.
Proof.
Admitted.
Print Assumptions wrong.
