(** Side of an order and actions that can occur on an order. *)

type side = Bid | Ask [@@deriving show, eq, ord]

val sexp_of_side : side -> Sexplib0.Sexp.t
val side_of_sexp : Sexplib0.Sexp.t -> side

type action =
  | Add
  | Amend
  | Cancel
  | Execute
  | Replace of string
  | Control of string
[@@deriving show, eq, ord]

val sexp_of_action : action -> Sexplib0.Sexp.t
val action_of_sexp : Sexplib0.Sexp.t -> action
