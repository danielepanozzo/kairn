(* Negative control for the audit: a false theorem closed with Admitted. The audit must
   reject this file twice: the text scan finds the word, and Print Assumptions reports the
   theorem as an axiom named after itself. This file is not part of the library. *)
From Stdlib Require Import Reals.
Open Scope R_scope.

Theorem wrong : forall x : R, x + 1 = x.
Proof.
Admitted.

Print Assumptions wrong.
