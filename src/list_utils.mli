(** List utility functions. *)

val take : int -> 'a list -> 'a list
(** [take n lst] returns the first [n] elements of [lst], or all elements if
    [lst] has fewer than [n]. *)
